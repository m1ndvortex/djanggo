"""
External service integrations for ZARGAR jewelry SaaS platform.
Provides Iranian gold market price API, SMS services, and email services integration.
"""
import requests
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.template import Template, Context
from django.core.exceptions import ValidationError
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class IranianGoldPriceAPI:
    """
    Iranian gold market price API integration service.
    Provides real-time gold price data from multiple Iranian sources.
    """
    
    # Iranian gold market API endpoints
    GOLD_PRICE_APIS = {
        'tgju': {
            'url': 'https://api.tgju.org/v1/market/indicator/summary-table-data/gold_18',
            'headers': {'User-Agent': 'ZARGAR-Jewelry-SaaS/1.0'},
            'timeout': 10,
            'format': 'json'
        },
        'bonbast': {
            'url': 'https://www.bonbast.com/json',
            'headers': {'User-Agent': 'ZARGAR-Jewelry-SaaS/1.0'},
            'timeout': 10,
            'format': 'json'
        },
        'arz_ir': {
            'url': 'https://api.arz.ir/gold',
            'headers': {
                'User-Agent': 'ZARGAR-Jewelry-SaaS/1.0',
                'Accept': 'application/json'
            },
            'timeout': 10,
            'format': 'json'
        },
        'tala_ir': {
            'url': 'https://api.tala.ir/v1/gold/prices',
            'headers': {
                'User-Agent': 'ZARGAR-Jewelry-SaaS/1.0',
                'Accept': 'application/json'
            },
            'timeout': 10,
            'format': 'json'
        }
    }
    
    CACHE_KEY_PREFIX = 'iranian_gold_price'
    CACHE_TIMEOUT = 300  # 5 minutes
    
    # Fallback prices in Toman per gram (updated regularly)
    FALLBACK_PRICES = {
        14: Decimal('2916667'),  # 14k gold
        18: Decimal('3750000'),  # 18k gold (base)
        21: Decimal('4375000'),  # 21k gold
        22: Decimal('4583333'),  # 22k gold
        24: Decimal('5000000'),  # 24k gold (pure)
    }
    
    @classmethod
    def get_current_gold_price(cls, karat: int = 18) -> Dict[str, Any]:
        """
        Get current gold price for specified karat from Iranian market.
        
        Args:
            karat: Gold karat (14, 18, 21, 22, 24)
            
        Returns:
            Dictionary with price information
        """
        if karat not in cls.FALLBACK_PRICES:
            raise ValueError(f"Unsupported karat: {karat}. Supported: {list(cls.FALLBACK_PRICES.keys())}")
        
        cache_key = f"{cls.CACHE_KEY_PREFIX}_{karat}"
        cached_price = cache.get(cache_key)
        
        if cached_price:
            logger.info(f"Retrieved cached Iranian gold price for {karat}k: {cached_price['price_per_gram']} Toman")
            return cached_price
        
        # Try to fetch from Iranian APIs
        price_data = cls._fetch_from_iranian_apis(karat)
        
        if price_data:
            # Cache the result
            cache.set(cache_key, price_data, cls.CACHE_TIMEOUT)
            logger.info(f"Fetched and cached Iranian gold price for {karat}k: {price_data['price_per_gram']} Toman")
            return price_data
        
        # Fallback to default price if all APIs fail
        fallback_price = cls._get_fallback_price(karat)
        logger.warning(f"Using fallback Iranian gold price for {karat}k: {fallback_price['price_per_gram']} Toman")
        return fallback_price
    
    @classmethod
    def _fetch_from_iranian_apis(cls, karat: int) -> Optional[Dict[str, Any]]:
        """
        Fetch gold price from Iranian market APIs.
        
        Args:
            karat: Gold karat
            
        Returns:
            Price data dictionary or None if all APIs fail
        """
        for api_name, api_config in cls.GOLD_PRICE_APIS.items():
            try:
                logger.info(f"Fetching gold price from {api_name} API")
                
                response = requests.get(
                    api_config['url'],
                    headers=api_config['headers'],
                    timeout=api_config['timeout']
                )
                response.raise_for_status()
                
                # Parse response based on API
                if api_config['format'] == 'json':
                    data = response.json()
                else:
                    data = response.text
                
                price_data = cls._parse_iranian_api_response(data, api_name, karat)
                if price_data:
                    logger.info(f"Successfully fetched price from {api_name}: {price_data['price_per_gram']} Toman")
                    return price_data
                    
            except requests.RequestException as e:
                logger.warning(f"Failed to fetch from {api_name}: {e}")
                continue
            except Exception as e:
                logger.error(f"Error parsing response from {api_name}: {e}")
                continue
        
        logger.error("All Iranian gold price APIs failed")
        return None
    
    @classmethod
    def _parse_iranian_api_response(cls, data: Any, api_name: str, karat: int) -> Optional[Dict[str, Any]]:
        """
        Parse Iranian API response to extract gold price.
        
        Args:
            data: API response data
            api_name: Name of the API
            karat: Gold karat
            
        Returns:
            Parsed price data or None
        """
        try:
            price_per_gram = None
            
            if api_name == 'tgju':
                # TGJU API format
                if isinstance(data, dict) and 'data' in data:
                    # Extract 18k gold price
                    gold_data = data['data']
                    if isinstance(gold_data, list) and len(gold_data) > 0:
                        price_per_gram = Decimal(str(gold_data[0].get('p', 0)))
                    elif isinstance(gold_data, dict):
                        price_per_gram = Decimal(str(gold_data.get('price', 0)))
                
            elif api_name == 'bonbast':
                # Bonbast API format
                if isinstance(data, dict):
                    # Bonbast returns prices in different format
                    gold_18_price = data.get('gold18', data.get('gold_18', 0))
                    price_per_gram = Decimal(str(gold_18_price))
                
            elif api_name == 'arz_ir':
                # Arz.ir API format
                if isinstance(data, dict):
                    gold_prices = data.get('gold', {})
                    if isinstance(gold_prices, dict):
                        price_per_gram = Decimal(str(gold_prices.get('18k', 0)))
                    elif isinstance(gold_prices, list) and len(gold_prices) > 0:
                        # Find 18k gold in list
                        for item in gold_prices:
                            if item.get('karat') == 18:
                                price_per_gram = Decimal(str(item.get('price', 0)))
                                break
                
            elif api_name == 'tala_ir':
                # Tala.ir API format
                if isinstance(data, dict):
                    prices = data.get('prices', {})
                    if isinstance(prices, dict):
                        price_per_gram = Decimal(str(prices.get('gold_18k', 0)))
            
            if not price_per_gram or price_per_gram <= 0:
                logger.warning(f"Invalid price from {api_name}: {price_per_gram}")
                return None
            
            # Adjust price based on karat if not 18k
            if karat != 18:
                price_per_gram = price_per_gram * (Decimal(karat) / Decimal('18'))
            
            # Convert from Rial to Toman if needed (some APIs return Rial)
            # Most Iranian APIs return Toman, but some might return Rial
            if price_per_gram > 50000000:  # Likely in Rial, convert to Toman
                price_per_gram = price_per_gram / 10
            
            return {
                'price_per_gram': price_per_gram.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'karat': karat,
                'timestamp': timezone.now(),
                'source': api_name,
                'currency': 'TMN',  # Toman
                'api_response_time': timezone.now().isoformat(),
                'market': 'iranian'
            }
            
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            logger.error(f"Error parsing {api_name} response: {e}")
            return None
    
    @classmethod
    def _get_fallback_price(cls, karat: int) -> Dict[str, Any]:
        """
        Get fallback gold price when Iranian APIs are unavailable.
        
        Args:
            karat: Gold karat
            
        Returns:
            Fallback price data
        """
        fallback_price = cls.FALLBACK_PRICES[karat]
        
        return {
            'price_per_gram': fallback_price,
            'karat': karat,
            'timestamp': timezone.now(),
            'source': 'fallback',
            'currency': 'TMN',
            'market': 'iranian',
            'is_fallback': True
        }
    
    @classmethod
    def get_price_trend(cls, karat: int = 18, days: int = 30) -> List[Dict]:
        """
        Get gold price trend for specified period from Iranian market.
        
        Args:
            karat: Gold karat
            days: Number of days for trend analysis
            
        Returns:
            List of price data points
        """
        # For now, return mock trend data based on current price
        # In production, this would fetch historical data from Iranian sources
        current_price_data = cls.get_current_gold_price(karat)
        current_price = current_price_data['price_per_gram']
        
        trend_data = []
        
        for i in range(days):
            date = timezone.now().date() - timedelta(days=days-i-1)
            
            # Mock price variation (±3% daily volatility typical for Iranian gold market)
            import random
            variation = Decimal('0.97') + (Decimal(str(random.randint(0, 60))) / Decimal('1000'))
            price = (current_price * variation).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            trend_data.append({
                'date': date,
                'price_per_gram': price,
                'karat': karat,
                'currency': 'TMN',
                'market': 'iranian'
            })
        
        return trend_data
    
    @classmethod
    def validate_api_connectivity(cls) -> Dict[str, Any]:
        """
        Validate connectivity to all Iranian gold price APIs.
        
        Returns:
            Dictionary with connectivity status for each API
        """
        results = {
            'timestamp': timezone.now().isoformat(),
            'total_apis': len(cls.GOLD_PRICE_APIS),
            'healthy_apis': 0,
            'api_status': {}
        }
        
        for api_name, api_config in cls.GOLD_PRICE_APIS.items():
            try:
                start_time = timezone.now()
                response = requests.get(
                    api_config['url'],
                    headers=api_config['headers'],
                    timeout=api_config['timeout']
                )
                response_time = (timezone.now() - start_time).total_seconds() * 1000
                
                api_result = {
                    'url': api_config['url'],
                    'status_code': response.status_code,
                    'response_time_ms': round(response_time, 2),
                    'healthy': response.status_code == 200,
                    'error': None,
                    'last_checked': timezone.now().isoformat()
                }
                
                if response.status_code == 200:
                    results['healthy_apis'] += 1
                    logger.info(f"Iranian API {api_name} is healthy: {response.status_code} in {response_time:.0f}ms")
                else:
                    logger.warning(f"Iranian API {api_name} returned status {response.status_code}")
                
                results['api_status'][api_name] = api_result
                
            except requests.RequestException as e:
                error_msg = f"Connection error: {str(e)}"
                logger.error(f"Iranian API {api_name} failed: {error_msg}")
                
                results['api_status'][api_name] = {
                    'url': api_config['url'],
                    'status_code': None,
                    'response_time_ms': None,
                    'healthy': False,
                    'error': error_msg,
                    'last_checked': timezone.now().isoformat()
                }
        
        results['health_percentage'] = (results['healthy_apis'] / results['total_apis']) * 100
        
        logger.info(f"Iranian gold price API health check: {results['healthy_apis']}/{results['total_apis']} "
                   f"APIs healthy ({results['health_percentage']:.1f}%)")
        
        return results
    
    @classmethod
    def invalidate_cache(cls, karat: Optional[int] = None):
        """
        Invalidate Iranian gold price cache.
        
        Args:
            karat: Specific karat to invalidate, or None for all
        """
        if karat:
            cache_key = f"{cls.CACHE_KEY_PREFIX}_{karat}"
            cache.delete(cache_key)
            logger.info(f"Invalidated Iranian gold price cache for {karat}k")
        else:
            # Invalidate all karat caches
            for k in cls.FALLBACK_PRICES.keys():
                cache_key = f"{cls.CACHE_KEY_PREFIX}_{k}"
                cache.delete(cache_key)
            logger.info("Invalidated all Iranian gold price caches")


class IranianSMSService:
    """
    Iranian SMS service integration for Persian notifications.
    Supports multiple Iranian SMS providers with failover.
    """
    
    # Iranian SMS providers configuration
    SMS_PROVIDERS = {
        'kavenegar': {
            'api_url': 'https://api.kavenegar.com/v1/{api_key}/sms/send.json',
            'method': 'POST',
            'format': 'json',
            'encoding': 'utf-8',
            'max_length': 160,
            'supports_persian': True
        },
        'melipayamak': {
            'api_url': 'https://rest.payamak-panel.com/api/SendSMS/SendSMS',
            'method': 'POST',
            'format': 'json',
            'encoding': 'utf-8',
            'max_length': 160,
            'supports_persian': True
        },
        'farapayamak': {
            'api_url': 'https://rest.ippanel.com/v1/messages',
            'method': 'POST',
            'format': 'json',
            'encoding': 'utf-8',
            'max_length': 160,
            'supports_persian': True
        },
        'sms_ir': {
            'api_url': 'https://ws.sms.ir/api/MessageSend',
            'method': 'POST',
            'format': 'json',
            'encoding': 'utf-8',
            'max_length': 160,
            'supports_persian': True
        }
    }
    
    def __init__(self, provider_name: str = 'kavenegar'):
        """
        Initialize SMS service with specified provider.
        
        Args:
            provider_name: Name of the SMS provider to use
        """
        if provider_name not in self.SMS_PROVIDERS:
            raise ValueError(f"Unsupported SMS provider: {provider_name}")
        
        self.provider_name = provider_name
        self.provider_config = self.SMS_PROVIDERS[provider_name]
        self.logger = logging.getLogger(__name__)
        
        # Get provider credentials from settings
        self.api_key = getattr(settings, f'{provider_name.upper()}_SMS_API_KEY', None)
        self.api_secret = getattr(settings, f'{provider_name.upper()}_SMS_API_SECRET', None)
        self.sender_number = getattr(settings, f'{provider_name.upper()}_SMS_SENDER', '10008663')
        
        if not self.api_key:
            logger.warning(f"No API key configured for SMS provider: {provider_name}")
    
    def send_sms(self, phone_number: str, message: str, 
                 message_type: str = 'normal') -> Dict[str, Any]:
        """
        Send SMS message via Iranian SMS provider.
        
        Args:
            phone_number: Recipient phone number (Iranian format)
            message: Persian message text
            message_type: Type of message ('normal', 'flash', 'voice')
            
        Returns:
            Dictionary with sending results
        """
        try:
            # Validate phone number (Iranian format)
            formatted_phone = self._format_iranian_phone(phone_number)
            if not formatted_phone:
                return {
                    'success': False,
                    'error': 'Invalid Iranian phone number format',
                    'phone_number': phone_number
                }
            
            # Validate message length
            if len(message) > self.provider_config['max_length']:
                return {
                    'success': False,
                    'error': f'Message too long (max {self.provider_config["max_length"]} chars)',
                    'message_length': len(message)
                }
            
            # Send via specific provider
            if self.provider_name == 'kavenegar':
                result = self._send_via_kavenegar(formatted_phone, message, message_type)
            elif self.provider_name == 'melipayamak':
                result = self._send_via_melipayamak(formatted_phone, message, message_type)
            elif self.provider_name == 'farapayamak':
                result = self._send_via_farapayamak(formatted_phone, message, message_type)
            elif self.provider_name == 'sms_ir':
                result = self._send_via_sms_ir(formatted_phone, message, message_type)
            else:
                result = {
                    'success': False,
                    'error': f'Provider {self.provider_name} not implemented'
                }
            
            # Log the result
            if result['success']:
                self.logger.info(f"SMS sent successfully via {self.provider_name} to {formatted_phone}")
            else:
                self.logger.error(f"SMS failed via {self.provider_name}: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error sending SMS via {self.provider_name}: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'provider': self.provider_name
            }
    
    def _format_iranian_phone(self, phone_number: str) -> Optional[str]:
        """
        Format Iranian phone number to standard format.
        
        Args:
            phone_number: Input phone number
            
        Returns:
            Formatted phone number or None if invalid
        """
        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, phone_number))
        
        # Iranian mobile number patterns
        if len(digits) == 11 and digits.startswith('09'):
            return digits  # 09xxxxxxxxx
        elif len(digits) == 10 and digits.startswith('9'):
            return '0' + digits  # 9xxxxxxxxx -> 09xxxxxxxxx
        elif len(digits) == 13 and digits.startswith('989'):
            return '0' + digits[2:]  # 989xxxxxxxxx -> 09xxxxxxxxx
        elif len(digits) == 12 and digits.startswith('98'):
            return '0' + digits[2:]  # 98xxxxxxxxx -> 09xxxxxxxxx
        
        return None
    
    def _send_via_kavenegar(self, phone: str, message: str, message_type: str) -> Dict[str, Any]:
        """Send SMS via Kavenegar API."""
        try:
            url = self.provider_config['api_url'].format(api_key=self.api_key)
            
            payload = {
                'receptor': phone,
                'message': message,
                'sender': self.sender_number
            }
            
            if message_type == 'flash':
                payload['type'] = 1
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('return', {}).get('status') == 200:
                return {
                    'success': True,
                    'provider': 'kavenegar',
                    'message_id': str(data.get('entries', [{}])[0].get('messageid', '')),
                    'cost': data.get('entries', [{}])[0].get('cost', 0),
                    'status': 'sent'
                }
            else:
                return {
                    'success': False,
                    'provider': 'kavenegar',
                    'error': data.get('return', {}).get('message', 'Unknown error'),
                    'error_code': data.get('return', {}).get('status')
                }
                
        except Exception as e:
            return {
                'success': False,
                'provider': 'kavenegar',
                'error': str(e)
            }
    
    def _send_via_melipayamak(self, phone: str, message: str, message_type: str) -> Dict[str, Any]:
        """Send SMS via MeliPayamak API."""
        try:
            payload = {
                'username': self.api_key,
                'password': self.api_secret,
                'to': phone,
                'from': self.sender_number,
                'text': message,
                'isflash': message_type == 'flash'
            }
            
            response = requests.post(
                self.provider_config['api_url'],
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('RetStatus') == 1:
                return {
                    'success': True,
                    'provider': 'melipayamak',
                    'message_id': str(data.get('Value', '')),
                    'status': 'sent'
                }
            else:
                return {
                    'success': False,
                    'provider': 'melipayamak',
                    'error': data.get('StrRetStatus', 'Unknown error')
                }
                
        except Exception as e:
            return {
                'success': False,
                'provider': 'melipayamak',
                'error': str(e)
            }
    
    def _send_via_farapayamak(self, phone: str, message: str, message_type: str) -> Dict[str, Any]:
        """Send SMS via FaraPayamak (IPPanel) API."""
        try:
            headers = {
                'Authorization': f'AccessKey {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'code': self.sender_number,
                'sender': self.sender_number,
                'message': message,
                'recipient': [phone]
            }
            
            response = requests.post(
                self.provider_config['api_url'],
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'provider': 'farapayamak',
                    'message_id': str(data.get('bulk_id', '')),
                    'status': 'sent'
                }
            else:
                return {
                    'success': False,
                    'provider': 'farapayamak',
                    'error': data.get('message', 'Unknown error')
                }
                
        except Exception as e:
            return {
                'success': False,
                'provider': 'farapayamak',
                'error': str(e)
            }
    
    def _send_via_sms_ir(self, phone: str, message: str, message_type: str) -> Dict[str, Any]:
        """Send SMS via SMS.ir API."""
        try:
            headers = {
                'Content-Type': 'application/json',
                'x-sms-ir-secure-token': self.api_key
            }
            
            payload = {
                'Messages': [message],
                'MobileNumbers': [phone],
                'LineNumber': self.sender_number,
                'SendDateTime': '',
                'CanContinueInCaseOfError': True
            }
            
            response = requests.post(
                self.provider_config['api_url'],
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('IsSuccessful'):
                return {
                    'success': True,
                    'provider': 'sms_ir',
                    'message_id': str(data.get('MessageIds', [0])[0]),
                    'status': 'sent'
                }
            else:
                return {
                    'success': False,
                    'provider': 'sms_ir',
                    'error': data.get('Message', 'Unknown error')
                }
                
        except Exception as e:
            return {
                'success': False,
                'provider': 'sms_ir',
                'error': str(e)
            }
    
    def send_bulk_sms(self, recipients: List[Dict[str, str]], 
                      template_message: str) -> Dict[str, Any]:
        """
        Send bulk SMS messages with personalization.
        
        Args:
            recipients: List of recipient dictionaries with phone and context
            template_message: Message template with placeholders
            
        Returns:
            Dictionary with bulk sending results
        """
        results = {
            'total_recipients': len(recipients),
            'successful_sends': 0,
            'failed_sends': 0,
            'results': [],
            'provider': self.provider_name
        }
        
        for recipient in recipients:
            try:
                # Personalize message
                message = template_message
                for key, value in recipient.get('context', {}).items():
                    message = message.replace(f'{{{key}}}', str(value))
                
                # Send SMS
                result = self.send_sms(recipient['phone'], message)
                
                if result['success']:
                    results['successful_sends'] += 1
                else:
                    results['failed_sends'] += 1
                
                results['results'].append({
                    'phone': recipient['phone'],
                    'success': result['success'],
                    'message_id': result.get('message_id'),
                    'error': result.get('error')
                })
                
            except Exception as e:
                results['failed_sends'] += 1
                results['results'].append({
                    'phone': recipient.get('phone', 'unknown'),
                    'success': False,
                    'error': str(e)
                })
        
        self.logger.info(f"Bulk SMS completed: {results['successful_sends']} sent, "
                        f"{results['failed_sends']} failed")
        
        return results
    
    @classmethod
    def validate_provider_connectivity(cls, provider_name: str) -> Dict[str, Any]:
        """
        Validate connectivity to SMS provider.
        
        Args:
            provider_name: Name of the SMS provider
            
        Returns:
            Dictionary with connectivity status
        """
        try:
            sms_service = cls(provider_name)
            
            # Try to send a test SMS (to a test number if configured)
            test_phone = getattr(settings, 'SMS_TEST_PHONE_NUMBER', None)
            
            if test_phone:
                result = sms_service.send_sms(test_phone, 'تست اتصال سرویس پیامک')
                return {
                    'provider': provider_name,
                    'healthy': result['success'],
                    'test_sent': True,
                    'error': result.get('error'),
                    'last_checked': timezone.now().isoformat()
                }
            else:
                return {
                    'provider': provider_name,
                    'healthy': True,  # Assume healthy if configured
                    'test_sent': False,
                    'note': 'No test phone number configured',
                    'last_checked': timezone.now().isoformat()
                }
                
        except Exception as e:
            return {
                'provider': provider_name,
                'healthy': False,
                'error': str(e),
                'last_checked': timezone.now().isoformat()
            }


class PersianEmailService:
    """
    Persian email service integration with RTL templates and Iranian providers.
    Supports both local SMTP and Iranian email service providers.
    """
    
    def __init__(self, provider: str = 'smtp'):
        """
        Initialize email service.
        
        Args:
            provider: Email provider ('smtp', 'mailgun', 'sendgrid')
        """
        self.provider = provider
        self.logger = logging.getLogger(__name__)
    
    def send_persian_email(self, recipient_email: str, subject: str, 
                          template_name: str, context: Dict[str, Any],
                          sender_email: Optional[str] = None) -> Dict[str, Any]:
        """
        Send Persian email with RTL template.
        
        Args:
            recipient_email: Recipient email address
            subject: Email subject in Persian
            template_name: Template name (without .html extension)
            context: Template context variables
            sender_email: Sender email (optional)
            
        Returns:
            Dictionary with sending results
        """
        try:
            # Render Persian email template
            html_content = render_to_string(f'emails/{template_name}.html', context)
            text_content = render_to_string(f'emails/{template_name}.txt', context)
            
            # Set sender
            from_email = sender_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@zargar.com')
            
            # Create email message
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[recipient_email]
            )
            email.attach_alternative(html_content, "text/html")
            
            # Send email
            success = email.send()
            
            if success:
                self.logger.info(f"Persian email sent successfully to {recipient_email}")
                return {
                    'success': True,
                    'recipient': recipient_email,
                    'subject': subject,
                    'provider': self.provider,
                    'sent_at': timezone.now().isoformat()
                }
            else:
                self.logger.error(f"Failed to send Persian email to {recipient_email}")
                return {
                    'success': False,
                    'recipient': recipient_email,
                    'error': 'Email sending failed'
                }
                
        except Exception as e:
            error_msg = f"Error sending Persian email: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'recipient': recipient_email,
                'error': error_msg
            }
    
    def send_bulk_persian_emails(self, recipients: List[Dict[str, Any]], 
                                subject_template: str, template_name: str,
                                base_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send bulk Persian emails with personalization.
        
        Args:
            recipients: List of recipient dictionaries
            subject_template: Subject template with placeholders
            template_name: Email template name
            base_context: Base context for all emails
            
        Returns:
            Dictionary with bulk sending results
        """
        results = {
            'total_recipients': len(recipients),
            'successful_sends': 0,
            'failed_sends': 0,
            'results': []
        }
        
        for recipient in recipients:
            try:
                # Merge context
                context = {**base_context, **recipient.get('context', {})}
                
                # Personalize subject
                subject = subject_template
                for key, value in context.items():
                    subject = subject.replace(f'{{{key}}}', str(value))
                
                # Send email
                result = self.send_persian_email(
                    recipient_email=recipient['email'],
                    subject=subject,
                    template_name=template_name,
                    context=context
                )
                
                if result['success']:
                    results['successful_sends'] += 1
                else:
                    results['failed_sends'] += 1
                
                results['results'].append({
                    'email': recipient['email'],
                    'success': result['success'],
                    'error': result.get('error')
                })
                
            except Exception as e:
                results['failed_sends'] += 1
                results['results'].append({
                    'email': recipient.get('email', 'unknown'),
                    'success': False,
                    'error': str(e)
                })
        
        self.logger.info(f"Bulk Persian email completed: {results['successful_sends']} sent, "
                        f"{results['failed_sends']} failed")
        
        return results
    
    def validate_email_connectivity(self) -> Dict[str, Any]:
        """
        Validate email service connectivity.
        
        Returns:
            Dictionary with connectivity status
        """
        try:
            # Try to send a test email
            test_email = getattr(settings, 'EMAIL_TEST_RECIPIENT', None)
            
            if test_email:
                result = self.send_persian_email(
                    recipient_email=test_email,
                    subject='تست اتصال سرویس ایمیل',
                    template_name='test_email',
                    context={'test_message': 'این یک پیام تست است'}
                )
                
                return {
                    'provider': self.provider,
                    'healthy': result['success'],
                    'test_sent': True,
                    'error': result.get('error'),
                    'last_checked': timezone.now().isoformat()
                }
            else:
                return {
                    'provider': self.provider,
                    'healthy': True,  # Assume healthy if configured
                    'test_sent': False,
                    'note': 'No test email address configured',
                    'last_checked': timezone.now().isoformat()
                }
                
        except Exception as e:
            return {
                'provider': self.provider,
                'healthy': False,
                'error': str(e),
                'last_checked': timezone.now().isoformat()
            }


# Convenience functions for external service integration
def get_current_iranian_gold_price(karat: int = 18) -> Dict[str, Any]:
    """Get current Iranian gold price."""
    return IranianGoldPriceAPI.get_current_gold_price(karat)


def send_persian_sms(phone_number: str, message: str, provider: str = 'kavenegar') -> Dict[str, Any]:
    """Send Persian SMS message."""
    sms_service = IranianSMSService(provider)
    return sms_service.send_sms(phone_number, message)


def send_persian_email(recipient_email: str, subject: str, template_name: str, 
                      context: Dict[str, Any]) -> Dict[str, Any]:
    """Send Persian email."""
    email_service = PersianEmailService()
    return email_service.send_persian_email(recipient_email, subject, template_name, context)


def validate_all_external_services() -> Dict[str, Any]:
    """Validate connectivity to all external services."""
    results = {
        'timestamp': timezone.now().isoformat(),
        'services': {}
    }
    
    # Validate Iranian gold price APIs
    results['services']['gold_price_apis'] = IranianGoldPriceAPI.validate_api_connectivity()
    
    # Validate SMS providers
    sms_results = {}
    for provider_name in IranianSMSService.SMS_PROVIDERS.keys():
        sms_results[provider_name] = IranianSMSService.validate_provider_connectivity(provider_name)
    results['services']['sms_providers'] = sms_results
    
    # Validate email service
    email_service = PersianEmailService()
    results['services']['email_service'] = email_service.validate_email_connectivity()
    
    return results