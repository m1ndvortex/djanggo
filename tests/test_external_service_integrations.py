"""
Integration tests for external service integrations.
Tests Iranian gold price APIs, SMS services, and email services connectivity.
"""
import pytest
import requests
import json
from unittest.mock import patch, Mock, MagicMock
from decimal import Decimal
from datetime import datetime, timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from django.core.cache import cache
from django.core import mail
from django.conf import settings

from zargar.core.external_services import (
    IranianGoldPriceAPI,
    IranianSMSService,
    PersianEmailService,
    validate_all_external_services
)
from zargar.core.external_service_tasks import (
    update_iranian_gold_prices,
    send_persian_sms_task,
    send_persian_email_task,
    validate_all_external_services_task
)


class TestIranianGoldPriceAPI(TestCase):
    """Test Iranian gold price API integration."""
    
    def setUp(self):
        """Set up test data."""
        cache.clear()
    
    def tearDown(self):
        """Clean up after tests."""
        cache.clear()
    
    def test_get_current_gold_price_cache_hit(self):
        """Test getting gold price from cache."""
        # Set up cached data
        cached_data = {
            'price_per_gram': Decimal('3750000'),
            'karat': 18,
            'timestamp': timezone.now(),
            'source': 'tgju',
            'currency': 'TMN',
            'market': 'iranian'
        }
        cache.set(f"{IranianGoldPriceAPI.CACHE_KEY_PREFIX}_18", cached_data, 300)
        
        # Get price (should hit cache)
        result = IranianGoldPriceAPI.get_current_gold_price(18)
        
        self.assertEqual(result['price_per_gram'], Decimal('3750000'))
        self.assertEqual(result['source'], 'tgju')
        self.assertEqual(result['currency'], 'TMN')
        self.assertEqual(result['market'], 'iranian')
    
    @patch('requests.get')
    def test_get_current_gold_price_api_success(self, mock_get):
        """Test successful API call for gold price."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'p': 3800000}]  # TGJU format
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Get price (should call API)
        result = IranianGoldPriceAPI.get_current_gold_price(18)
        
        self.assertEqual(result['price_per_gram'], Decimal('3800000.00'))
        self.assertEqual(result['source'], 'tgju')
        self.assertEqual(result['currency'], 'TMN')
        self.assertFalse(result.get('is_fallback', False))
        
        # Verify API was called
        mock_get.assert_called()
    
    @patch('requests.get')
    def test_get_current_gold_price_api_failure_fallback(self, mock_get):
        """Test fallback when all APIs fail."""
        # Mock API failure
        mock_get.side_effect = requests.RequestException("API unavailable")
        
        # Get price (should use fallback)
        result = IranianGoldPriceAPI.get_current_gold_price(18)
        
        self.assertEqual(result['price_per_gram'], Decimal('3750000'))  # Fallback price
        self.assertEqual(result['source'], 'fallback')
        self.assertTrue(result.get('is_fallback', False))
    
    def test_get_current_gold_price_different_karats(self):
        """Test gold price calculation for different karats."""
        # Test supported karats
        for karat in [14, 18, 21, 22, 24]:
            result = IranianGoldPriceAPI.get_current_gold_price(karat)
            
            self.assertIsInstance(result['price_per_gram'], Decimal)
            self.assertEqual(result['karat'], karat)
            self.assertIn('timestamp', result)
            self.assertIn('source', result)
    
    def test_get_current_gold_price_invalid_karat(self):
        """Test error handling for invalid karat."""
        with self.assertRaises(ValueError):
            IranianGoldPriceAPI.get_current_gold_price(16)  # Unsupported karat
    
    @patch('requests.get')
    def test_validate_api_connectivity_all_healthy(self, mock_get):
        """Test API connectivity validation when all APIs are healthy."""
        # Mock successful responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_get.return_value = mock_response
        
        result = IranianGoldPriceAPI.validate_api_connectivity()
        
        self.assertEqual(result['total_apis'], len(IranianGoldPriceAPI.GOLD_PRICE_APIS))
        self.assertEqual(result['healthy_apis'], result['total_apis'])
        self.assertEqual(result['health_percentage'], 100.0)
        
        for api_name, api_status in result['api_status'].items():
            self.assertTrue(api_status['healthy'])
            self.assertEqual(api_status['status_code'], 200)
    
    @patch('requests.get')
    def test_validate_api_connectivity_some_unhealthy(self, mock_get):
        """Test API connectivity validation when some APIs are unhealthy."""
        # Mock mixed responses
        def side_effect(*args, **kwargs):
            if 'tgju' in args[0]:
                response = Mock()
                response.status_code = 200
                response.elapsed.total_seconds.return_value = 0.5
                return response
            else:
                raise requests.RequestException("Connection failed")
        
        mock_get.side_effect = side_effect
        
        result = IranianGoldPriceAPI.validate_api_connectivity()
        
        self.assertEqual(result['total_apis'], len(IranianGoldPriceAPI.GOLD_PRICE_APIS))
        self.assertLess(result['healthy_apis'], result['total_apis'])
        self.assertLess(result['health_percentage'], 100.0)
    
    def test_get_price_trend(self):
        """Test gold price trend generation."""
        trend_data = IranianGoldPriceAPI.get_price_trend(18, 7)
        
        self.assertEqual(len(trend_data), 7)
        
        for point in trend_data:
            self.assertIn('date', point)
            self.assertIn('price_per_gram', point)
            self.assertIsInstance(point['price_per_gram'], Decimal)
            self.assertEqual(point['karat'], 18)
            self.assertEqual(point['currency'], 'TMN')
            self.assertEqual(point['market'], 'iranian')
    
    def test_invalidate_cache(self):
        """Test cache invalidation."""
        # Set up cached data
        cache.set(f"{IranianGoldPriceAPI.CACHE_KEY_PREFIX}_18", {'test': 'data'}, 300)
        
        # Verify cache exists
        self.assertIsNotNone(cache.get(f"{IranianGoldPriceAPI.CACHE_KEY_PREFIX}_18"))
        
        # Invalidate specific karat
        IranianGoldPriceAPI.invalidate_cache(18)
        
        # Verify cache is cleared
        self.assertIsNone(cache.get(f"{IranianGoldPriceAPI.CACHE_KEY_PREFIX}_18"))
    
    def test_invalidate_all_cache(self):
        """Test invalidating all karat caches."""
        # Set up cached data for multiple karats
        for karat in [14, 18, 21, 22, 24]:
            cache.set(f"{IranianGoldPriceAPI.CACHE_KEY_PREFIX}_{karat}", {'test': 'data'}, 300)
        
        # Invalidate all caches
        IranianGoldPriceAPI.invalidate_cache()
        
        # Verify all caches are cleared
        for karat in [14, 18, 21, 22, 24]:
            self.assertIsNone(cache.get(f"{IranianGoldPriceAPI.CACHE_KEY_PREFIX}_{karat}"))


class TestIranianSMSService(TestCase):
    """Test Iranian SMS service integration."""
    
    def setUp(self):
        """Set up test data."""
        self.sms_service = IranianSMSService('kavenegar')
    
    def test_format_iranian_phone_valid_formats(self):
        """Test Iranian phone number formatting for valid formats."""
        test_cases = [
            ('09123456789', '09123456789'),  # Already correct
            ('9123456789', '09123456789'),   # Missing leading 0
            ('989123456789', '09123456789'), # International format
            ('98123456789', '09123456789'),  # International without +
            ('+989123456789', '09123456789'), # With + sign
            ('0912 345 6789', '09123456789'), # With spaces
            ('0912-345-6789', '09123456789'), # With dashes
        ]
        
        for input_phone, expected in test_cases:
            result = self.sms_service._format_iranian_phone(input_phone)
            self.assertEqual(result, expected, f"Failed for input: {input_phone}")
    
    def test_format_iranian_phone_invalid_formats(self):
        """Test Iranian phone number formatting for invalid formats."""
        invalid_phones = [
            '123456789',      # Too short
            '091234567890',   # Too long
            '08123456789',    # Wrong prefix
            'abcd1234567',    # Contains letters
            '',               # Empty string
            '1234',           # Way too short
        ]
        
        for invalid_phone in invalid_phones:
            result = self.sms_service._format_iranian_phone(invalid_phone)
            self.assertIsNone(result, f"Should be invalid: {invalid_phone}")
    
    @patch('requests.post')
    def test_send_sms_kavenegar_success(self, mock_post):
        """Test successful SMS sending via Kavenegar."""
        # Mock successful Kavenegar response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'return': {'status': 200, 'message': 'Success'},
            'entries': [{'messageid': '12345', 'cost': 100}]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.sms_service.send_sms('09123456789', 'تست پیامک')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['provider'], 'kavenegar')
        self.assertEqual(result['message_id'], '12345')
        self.assertEqual(result['status'], 'sent')
        
        # Verify API was called with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertIn('receptor', call_args[1]['json'])
        self.assertEqual(call_args[1]['json']['receptor'], '09123456789')
        self.assertEqual(call_args[1]['json']['message'], 'تست پیامک')
    
    @patch('requests.post')
    def test_send_sms_kavenegar_failure(self, mock_post):
        """Test SMS sending failure via Kavenegar."""
        # Mock failed Kavenegar response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'return': {'status': 400, 'message': 'Invalid parameters'}
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.sms_service.send_sms('09123456789', 'تست پیامک')
        
        self.assertFalse(result['success'])
        self.assertEqual(result['provider'], 'kavenegar')
        self.assertEqual(result['error'], 'Invalid parameters')
        self.assertEqual(result['error_code'], 400)
    
    @patch('requests.post')
    def test_send_sms_network_error(self, mock_post):
        """Test SMS sending with network error."""
        # Mock network error
        mock_post.side_effect = requests.RequestException("Network error")
        
        result = self.sms_service.send_sms('09123456789', 'تست پیامک')
        
        self.assertFalse(result['success'])
        self.assertEqual(result['provider'], 'kavenegar')
        self.assertIn('Network error', result['error'])
    
    def test_send_sms_invalid_phone(self):
        """Test SMS sending with invalid phone number."""
        result = self.sms_service.send_sms('invalid_phone', 'تست پیامک')
        
        self.assertFalse(result['success'])
        self.assertIn('Invalid Iranian phone number format', result['error'])
    
    def test_send_sms_message_too_long(self):
        """Test SMS sending with message too long."""
        long_message = 'ا' * 200  # 200 Persian characters
        
        result = self.sms_service.send_sms('09123456789', long_message)
        
        self.assertFalse(result['success'])
        self.assertIn('Message too long', result['error'])
    
    @patch('requests.post')
    def test_send_bulk_sms(self, mock_post):
        """Test bulk SMS sending."""
        # Mock successful responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'return': {'status': 200, 'message': 'Success'},
            'entries': [{'messageid': '12345', 'cost': 100}]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        recipients = [
            {
                'phone': '09123456789',
                'context': {'name': 'علی', 'amount': '1000000'}
            },
            {
                'phone': '09987654321',
                'context': {'name': 'فاطمه', 'amount': '2000000'}
            }
        ]
        
        template_message = 'سلام {name} عزیز، مبلغ {amount} تومان'
        
        result = self.sms_service.send_bulk_sms(recipients, template_message)
        
        self.assertEqual(result['total_recipients'], 2)
        self.assertEqual(result['successful_sends'], 2)
        self.assertEqual(result['failed_sends'], 0)
        self.assertEqual(result['provider'], 'kavenegar')
        
        # Verify correct number of API calls
        self.assertEqual(mock_post.call_count, 2)
    
    @override_settings(SMS_TEST_PHONE_NUMBER='09123456789')
    @patch('requests.post')
    def test_validate_provider_connectivity_with_test_phone(self, mock_post):
        """Test provider connectivity validation with test phone."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'return': {'status': 200, 'message': 'Success'},
            'entries': [{'messageid': '12345', 'cost': 100}]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = IranianSMSService.validate_provider_connectivity('kavenegar')
        
        self.assertEqual(result['provider'], 'kavenegar')
        self.assertTrue(result['healthy'])
        self.assertTrue(result['test_sent'])
        self.assertIsNone(result.get('error'))
    
    def test_validate_provider_connectivity_without_test_phone(self):
        """Test provider connectivity validation without test phone."""
        result = IranianSMSService.validate_provider_connectivity('kavenegar')
        
        self.assertEqual(result['provider'], 'kavenegar')
        self.assertTrue(result['healthy'])  # Assume healthy if configured
        self.assertFalse(result['test_sent'])
        self.assertIn('No test phone number configured', result['note'])


class TestPersianEmailService(TestCase):
    """Test Persian email service integration."""
    
    def setUp(self):
        """Set up test data."""
        self.email_service = PersianEmailService()
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_persian_email_success(self):
        """Test successful Persian email sending."""
        # Create test template files (mocked)
        with patch('django.template.loader.render_to_string') as mock_render:
            mock_render.side_effect = [
                '<html><body>سلام علی عزیز</body></html>',  # HTML template
                'سلام علی عزیز'  # Text template
            ]
            
            result = self.email_service.send_persian_email(
                recipient_email='test@example.com',
                subject='تست ایمیل فارسی',
                template_name='test_email',
                context={'name': 'علی'}
            )
            
            self.assertTrue(result['success'])
            self.assertEqual(result['recipient'], 'test@example.com')
            self.assertEqual(result['subject'], 'تست ایمیل فارسی')
            self.assertEqual(result['provider'], 'smtp')
            
            # Verify email was sent
            self.assertEqual(len(mail.outbox), 1)
            sent_email = mail.outbox[0]
            self.assertEqual(sent_email.subject, 'تست ایمیل فارسی')
            self.assertEqual(sent_email.to, ['test@example.com'])
    
    def test_send_persian_email_template_error(self):
        """Test Persian email sending with template error."""
        with patch('django.template.loader.render_to_string') as mock_render:
            mock_render.side_effect = Exception("Template not found")
            
            result = self.email_service.send_persian_email(
                recipient_email='test@example.com',
                subject='تست ایمیل فارسی',
                template_name='nonexistent_template',
                context={'name': 'علی'}
            )
            
            self.assertFalse(result['success'])
            self.assertEqual(result['recipient'], 'test@example.com')
            self.assertIn('Template not found', result['error'])
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_bulk_persian_emails(self):
        """Test bulk Persian email sending."""
        with patch('django.template.loader.render_to_string') as mock_render:
            mock_render.side_effect = lambda template, context: f"سلام {context.get('name', 'کاربر')} عزیز"
            
            recipients = [
                {
                    'email': 'ali@example.com',
                    'context': {'name': 'علی'}
                },
                {
                    'email': 'fateme@example.com',
                    'context': {'name': 'فاطمه'}
                }
            ]
            
            result = self.email_service.send_bulk_persian_emails(
                recipients=recipients,
                subject_template='سلام {name} عزیز',
                template_name='bulk_email',
                base_context={'shop_name': 'طلا و جواهرات زرگر'}
            )
            
            self.assertEqual(result['total_recipients'], 2)
            self.assertEqual(result['successful_sends'], 2)
            self.assertEqual(result['failed_sends'], 0)
            
            # Verify emails were sent
            self.assertEqual(len(mail.outbox), 2)
    
    @override_settings(EMAIL_TEST_RECIPIENT='test@example.com')
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_validate_email_connectivity_with_test_email(self):
        """Test email connectivity validation with test email."""
        with patch('django.template.loader.render_to_string') as mock_render:
            mock_render.side_effect = ['<html><body>تست</body></html>', 'تست']
            
            result = self.email_service.validate_email_connectivity()
            
            self.assertEqual(result['provider'], 'smtp')
            self.assertTrue(result['healthy'])
            self.assertTrue(result['test_sent'])
            self.assertIsNone(result.get('error'))
    
    def test_validate_email_connectivity_without_test_email(self):
        """Test email connectivity validation without test email."""
        result = self.email_service.validate_email_connectivity()
        
        self.assertEqual(result['provider'], 'smtp')
        self.assertTrue(result['healthy'])  # Assume healthy if configured
        self.assertFalse(result['test_sent'])
        self.assertIn('No test email address configured', result['note'])


class TestExternalServiceTasks(TestCase):
    """Test external service Celery tasks."""
    
    def setUp(self):
        """Set up test data."""
        cache.clear()
    
    def tearDown(self):
        """Clean up after tests."""
        cache.clear()
    
    @patch('zargar.core.external_services.IranianGoldPriceAPI.get_current_gold_price')
    def test_update_iranian_gold_prices_task_success(self, mock_get_price):
        """Test successful Iranian gold price update task."""
        # Mock successful price fetching
        def mock_price_response(karat):
            return {
                'price_per_gram': Decimal('3750000') * (karat / 18),
                'karat': karat,
                'timestamp': timezone.now(),
                'source': 'tgju',
                'currency': 'TMN',
                'market': 'iranian'
            }
        
        mock_get_price.side_effect = mock_price_response
        
        # Run the task
        result = update_iranian_gold_prices.apply()
        task_result = result.get()
        
        self.assertTrue(task_result['success'])
        self.assertEqual(len(task_result['results']['updated_karats']), 5)
        self.assertEqual(len(task_result['results']['failed_karats']), 0)
        self.assertTrue(task_result['results']['cache_invalidated'])
    
    @patch('zargar.core.external_services.IranianGoldPriceAPI.get_current_gold_price')
    def test_update_iranian_gold_prices_task_partial_failure(self, mock_get_price):
        """Test Iranian gold price update task with partial failures."""
        # Mock mixed responses
        def mock_price_response(karat):
            if karat in [14, 18]:
                return {
                    'price_per_gram': Decimal('3750000') * (karat / 18),
                    'karat': karat,
                    'timestamp': timezone.now(),
                    'source': 'tgju',
                    'currency': 'TMN',
                    'market': 'iranian'
                }
            else:
                return {
                    'price_per_gram': Decimal('3750000') * (karat / 18),
                    'karat': karat,
                    'timestamp': timezone.now(),
                    'source': 'fallback',
                    'currency': 'TMN',
                    'market': 'iranian',
                    'is_fallback': True
                }
        
        mock_get_price.side_effect = mock_price_response
        
        # Run the task
        result = update_iranian_gold_prices.apply()
        task_result = result.get()
        
        self.assertTrue(task_result['success'])
        self.assertEqual(len(task_result['results']['updated_karats']), 2)
        self.assertEqual(len(task_result['results']['failed_karats']), 3)
    
    @patch('zargar.core.external_services.IranianSMSService.send_sms')
    def test_send_persian_sms_task_success(self, mock_send_sms):
        """Test successful Persian SMS task."""
        # Mock successful SMS sending
        mock_send_sms.return_value = {
            'success': True,
            'provider': 'kavenegar',
            'message_id': '12345',
            'status': 'sent'
        }
        
        # Run the task
        result = send_persian_sms_task.apply(
            args=['09123456789', 'تست پیامک', 'kavenegar', 'normal']
        )
        task_result = result.get()
        
        self.assertTrue(task_result['success'])
        self.assertEqual(task_result['provider'], 'kavenegar')
        self.assertEqual(task_result['message_id'], '12345')
        
        # Verify SMS service was called
        mock_send_sms.assert_called_once_with('09123456789', 'تست پیامک', 'normal')
    
    @patch('zargar.core.external_services.PersianEmailService.send_persian_email')
    def test_send_persian_email_task_success(self, mock_send_email):
        """Test successful Persian email task."""
        # Mock successful email sending
        mock_send_email.return_value = {
            'success': True,
            'recipient': 'test@example.com',
            'subject': 'تست ایمیل',
            'provider': 'smtp',
            'sent_at': timezone.now().isoformat()
        }
        
        # Run the task
        result = send_persian_email_task.apply(
            args=[
                'test@example.com',
                'تست ایمیل',
                'test_template',
                {'name': 'علی'}
            ]
        )
        task_result = result.get()
        
        self.assertTrue(task_result['success'])
        self.assertEqual(task_result['recipient'], 'test@example.com')
        self.assertEqual(task_result['subject'], 'تست ایمیل')
        
        # Verify email service was called
        mock_send_email.assert_called_once_with(
            'test@example.com',
            'تست ایمیل',
            'test_template',
            {'name': 'علی'},
            None
        )
    
    @patch('zargar.core.external_services.validate_all_external_services')
    def test_validate_all_external_services_task(self, mock_validate):
        """Test external service validation task."""
        # Mock validation results
        mock_validate.return_value = {
            'timestamp': timezone.now().isoformat(),
            'services': {
                'gold_price_apis': {
                    'total_apis': 4,
                    'healthy_apis': 3,
                    'health_percentage': 75.0
                },
                'sms_providers': {
                    'kavenegar': {'healthy': True},
                    'melipayamak': {'healthy': False}
                },
                'email_service': {'healthy': True}
            }
        }
        
        # Run the task
        result = validate_all_external_services_task.apply()
        task_result = result.get()
        
        self.assertTrue(task_result['success'])
        self.assertIn('overall_health', task_result)
        self.assertIn('service_health', task_result)
        self.assertIn('detailed_results', task_result)
        
        # Verify validation function was called
        mock_validate.assert_called_once()


class TestExternalServiceIntegration(TestCase):
    """Integration tests for external services."""
    
    def test_validate_all_external_services_structure(self):
        """Test the structure of validate_all_external_services response."""
        result = validate_all_external_services()
        
        # Check top-level structure
        self.assertIn('timestamp', result)
        self.assertIn('services', result)
        
        # Check services structure
        services = result['services']
        self.assertIn('gold_price_apis', services)
        self.assertIn('sms_providers', services)
        self.assertIn('email_service', services)
        
        # Check gold price APIs structure
        gold_apis = services['gold_price_apis']
        self.assertIn('total_apis', gold_apis)
        self.assertIn('healthy_apis', gold_apis)
        self.assertIn('health_percentage', gold_apis)
        self.assertIn('api_status', gold_apis)
        
        # Check SMS providers structure
        sms_providers = services['sms_providers']
        for provider_name in IranianSMSService.SMS_PROVIDERS.keys():
            self.assertIn(provider_name, sms_providers)
            provider_status = sms_providers[provider_name]
            self.assertIn('provider', provider_status)
            self.assertIn('healthy', provider_status)
        
        # Check email service structure
        email_service = services['email_service']
        self.assertIn('provider', email_service)
        self.assertIn('healthy', email_service)
    
    @patch('requests.get')
    def test_iranian_gold_price_api_real_structure(self, mock_get):
        """Test Iranian gold price API with realistic response structure."""
        # Mock realistic TGJU API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {
                    'p': 3850000,  # Price in Toman
                    'h': 3900000,  # High
                    'l': 3800000,  # Low
                    'c': 25000,    # Change
                    'cp': 0.65     # Change percentage
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_response.elapsed.total_seconds.return_value = 0.8
        mock_get.return_value = mock_response
        
        # Test price fetching
        result = IranianGoldPriceAPI.get_current_gold_price(18)
        
        self.assertEqual(result['price_per_gram'], Decimal('3850000.00'))
        self.assertEqual(result['karat'], 18)
        self.assertEqual(result['source'], 'tgju')
        self.assertEqual(result['currency'], 'TMN')
        self.assertEqual(result['market'], 'iranian')
        self.assertFalse(result.get('is_fallback', False))
    
    def test_iranian_phone_number_edge_cases(self):
        """Test Iranian phone number formatting edge cases."""
        sms_service = IranianSMSService('kavenegar')
        
        # Test various input formats
        test_cases = [
            # (input, expected_output)
            ('۰۹۱۲۳۴۵۶۷۸۹', '09123456789'),  # Persian digits
            ('٠٩١٢٣٤٥٦٧٨٩', '09123456789'),  # Arabic digits
            ('0912.345.6789', '09123456789'),   # With dots
            ('(0912) 345-6789', '09123456789'), # With parentheses
            ('0912 345 67 89', '09123456789'),  # Multiple spaces
        ]
        
        for input_phone, expected in test_cases:
            result = sms_service._format_iranian_phone(input_phone)
            self.assertEqual(result, expected, f"Failed for input: {input_phone}")
    
    def test_persian_email_context_handling(self):
        """Test Persian email context variable handling."""
        email_service = PersianEmailService()
        
        # Test context with Persian text
        context = {
            'customer_name': 'محمد رضا احمدی',
            'shop_name': 'طلا و جواهرات زرگر',
            'amount': '۲,۵۰۰,۰۰۰',
            'date': '۱۴۰۳/۰۶/۱۵'
        }
        
        with patch('django.template.loader.render_to_string') as mock_render:
            mock_render.side_effect = [
                f'<html><body>سلام {context["customer_name"]} عزیز</body></html>',
                f'سلام {context["customer_name"]} عزیز'
            ]
            
            result = email_service.send_persian_email(
                recipient_email='test@example.com',
                subject=f'پیام از {context["shop_name"]}',
                template_name='persian_email',
                context=context
            )
            
            # Verify template was called with Persian context
            mock_render.assert_called()
            call_args = mock_render.call_args_list
            for call in call_args:
                template_context = call[0][1]  # Second argument is context
                self.assertEqual(template_context['customer_name'], 'محمد رضا احمدی')
                self.assertEqual(template_context['shop_name'], 'طلا و جواهرات زرگر')


if __name__ == '__main__':
    pytest.main([__file__])