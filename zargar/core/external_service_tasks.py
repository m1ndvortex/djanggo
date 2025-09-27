"""
Celery tasks for external service integrations.
Provides background tasks for Iranian gold price updates, SMS sending, and email delivery.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django.conf import settings

from .external_services import (
    IranianGoldPriceAPI,
    IranianSMSService,
    PersianEmailService,
    validate_all_external_services
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def update_iranian_gold_prices(self):
    """
    Update gold prices from Iranian market APIs.
    This task should run every 5 minutes during market hours.
    
    Returns:
        Dict containing update results
    """
    logger.info("Starting Iranian gold price update task")
    
    try:
        # Supported gold karats
        karats = [14, 18, 21, 22, 24]
        results = {
            'updated_karats': [],
            'failed_karats': [],
            'total_processed': 0,
            'cache_invalidated': False,
            'timestamp': timezone.now().isoformat(),
            'market': 'iranian'
        }
        
        # Clear existing cache to force fresh API calls
        IranianGoldPriceAPI.invalidate_cache()
        results['cache_invalidated'] = True
        
        # Update prices for each karat
        for karat in karats:
            try:
                # Force fresh API call by invalidating cache first
                cache_key = f"{IranianGoldPriceAPI.CACHE_KEY_PREFIX}_{karat}"
                cache.delete(cache_key)
                
                # Fetch new price (this will cache it)
                price_data = IranianGoldPriceAPI.get_current_gold_price(karat)
                
                if price_data and not price_data.get('is_fallback', False):
                    results['updated_karats'].append({
                        'karat': karat,
                        'price_per_gram': str(price_data['price_per_gram']),
                        'source': price_data['source'],
                        'timestamp': price_data['timestamp'].isoformat(),
                        'currency': price_data['currency']
                    })
                    logger.info(f"Updated {karat}k Iranian gold price: {price_data['price_per_gram']} TMN from {price_data['source']}")
                else:
                    results['failed_karats'].append({
                        'karat': karat,
                        'reason': 'Iranian APIs unavailable, using fallback price',
                        'fallback_price': str(price_data['price_per_gram']) if price_data else 'N/A'
                    })
                    logger.warning(f"Failed to update {karat}k Iranian gold price, using fallback")
                
                results['total_processed'] += 1
                
            except Exception as e:
                error_msg = f"Error updating {karat}k Iranian gold price: {str(e)}"
                logger.error(error_msg)
                results['failed_karats'].append({
                    'karat': karat,
                    'reason': error_msg
                })
        
        # Record system health metric
        success_rate = len(results['updated_karats']) / len(karats) * 100
        record_iranian_gold_price_health_metric.apply_async(
            args=[success_rate, len(results['updated_karats']), len(results['failed_karats'])]
        )
        
        # Send alerts if too many failures
        if len(results['failed_karats']) >= 3:
            send_external_service_alert.apply_async(
                args=['iranian_gold_price_high_failure_rate', results]
            )
        
        logger.info(f"Iranian gold price update completed: {len(results['updated_karats'])} updated, "
                   f"{len(results['failed_karats'])} failed")
        
        return {
            'success': True,
            'results': results
        }
        
    except Exception as e:
        error_msg = f"Unexpected error in Iranian gold price update task: {str(e)}"
        logger.error(error_msg)
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying Iranian gold price update task (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        
        # Send critical alert if all retries failed
        send_external_service_alert.apply_async(
            args=['iranian_gold_price_update_failed', {'error': error_msg, 'retries_exhausted': True}]
        )
        
        return {'success': False, 'error': error_msg}


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def update_single_iranian_gold_karat(self, karat: int):
    """
    Update Iranian gold price for a specific karat.
    
    Args:
        karat: Gold karat to update (14, 18, 21, 22, 24)
    
    Returns:
        Dict containing update results
    """
    logger.info(f"Starting single Iranian gold karat price update for {karat}k")
    
    try:
        # Validate karat
        if karat not in [14, 18, 21, 22, 24]:
            raise ValueError(f"Unsupported karat: {karat}")
        
        # Clear cache for this karat
        cache_key = f"{IranianGoldPriceAPI.CACHE_KEY_PREFIX}_{karat}"
        cache.delete(cache_key)
        
        # Fetch new price
        price_data = IranianGoldPriceAPI.get_current_gold_price(karat)
        
        if price_data:
            logger.info(f"Updated {karat}k Iranian gold price: {price_data['price_per_gram']} TMN from {price_data['source']}")
            
            return {
                'success': True,
                'karat': karat,
                'price_per_gram': str(price_data['price_per_gram']),
                'source': price_data['source'],
                'timestamp': price_data['timestamp'].isoformat(),
                'is_fallback': price_data.get('is_fallback', False),
                'currency': price_data['currency'],
                'market': 'iranian'
            }
        else:
            error_msg = f"Failed to fetch Iranian price for {karat}k gold"
            logger.error(error_msg)
            return {
                'success': False,
                'karat': karat,
                'error': error_msg
            }
            
    except Exception as e:
        error_msg = f"Error updating {karat}k Iranian gold price: {str(e)}"
        logger.error(error_msg)
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying {karat}k Iranian price update (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
        
        return {'success': False, 'karat': karat, 'error': error_msg}


@shared_task(bind=True, max_retries=2)
def validate_iranian_gold_price_apis(self):
    """
    Validate all Iranian gold price API endpoints for connectivity and response format.
    This task should run every hour to monitor API health.
    
    Returns:
        Dict containing validation results
    """
    logger.info("Starting Iranian gold price API validation")
    
    try:
        results = IranianGoldPriceAPI.validate_api_connectivity()
        
        # Record health metric
        record_iranian_api_health_metric.apply_async(
            args=[results['health_percentage'], results['healthy_apis'], results['total_apis']]
        )
        
        # Send alert if API health is poor
        if results['health_percentage'] < 50:
            send_external_service_alert.apply_async(
                args=['iranian_gold_api_health_poor', results]
            )
        
        logger.info(f"Iranian API validation completed: {results['healthy_apis']}/{results['total_apis']} "
                   f"APIs healthy ({results['health_percentage']:.1f}%)")
        
        return {
            'success': True,
            'results': results
        }
        
    except Exception as e:
        error_msg = f"Unexpected error in Iranian API validation: {str(e)}"
        logger.error(error_msg)
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying Iranian API validation (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=60)
        
        return {'success': False, 'error': error_msg}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_persian_sms_task(self, phone_number: str, message: str, 
                         provider: str = 'kavenegar', message_type: str = 'normal'):
    """
    Send Persian SMS message via Iranian SMS provider.
    
    Args:
        phone_number: Recipient phone number
        message: Persian message text
        provider: SMS provider name
        message_type: Type of message ('normal', 'flash')
    
    Returns:
        Dict containing sending results
    """
    logger.info(f"Sending Persian SMS via {provider} to {phone_number}")
    
    try:
        sms_service = IranianSMSService(provider)
        result = sms_service.send_sms(phone_number, message, message_type)
        
        if result['success']:
            logger.info(f"Persian SMS sent successfully via {provider} to {phone_number}")
        else:
            logger.error(f"Persian SMS failed via {provider}: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        error_msg = f"Error sending Persian SMS via {provider}: {str(e)}"
        logger.error(error_msg)
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying Persian SMS send (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
        
        return {
            'success': False,
            'error': error_msg,
            'provider': provider,
            'phone_number': phone_number
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_bulk_persian_sms_task(self, recipients: List[Dict[str, Any]], 
                              template_message: str, provider: str = 'kavenegar'):
    """
    Send bulk Persian SMS messages.
    
    Args:
        recipients: List of recipient dictionaries with phone and context
        template_message: Message template with placeholders
        provider: SMS provider name
    
    Returns:
        Dict containing bulk sending results
    """
    logger.info(f"Sending bulk Persian SMS via {provider} to {len(recipients)} recipients")
    
    try:
        sms_service = IranianSMSService(provider)
        results = sms_service.send_bulk_sms(recipients, template_message)
        
        logger.info(f"Bulk Persian SMS completed via {provider}: {results['successful_sends']} sent, "
                   f"{results['failed_sends']} failed")
        
        return {
            'success': True,
            'results': results
        }
        
    except Exception as e:
        error_msg = f"Error sending bulk Persian SMS via {provider}: {str(e)}"
        logger.error(error_msg)
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying bulk Persian SMS send (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
        
        return {
            'success': False,
            'error': error_msg,
            'provider': provider,
            'total_recipients': len(recipients)
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_persian_email_task(self, recipient_email: str, subject: str, 
                           template_name: str, context: Dict[str, Any],
                           sender_email: Optional[str] = None):
    """
    Send Persian email with RTL template.
    
    Args:
        recipient_email: Recipient email address
        subject: Email subject in Persian
        template_name: Template name
        context: Template context variables
        sender_email: Sender email (optional)
    
    Returns:
        Dict containing sending results
    """
    logger.info(f"Sending Persian email to {recipient_email}")
    
    try:
        email_service = PersianEmailService()
        result = email_service.send_persian_email(
            recipient_email, subject, template_name, context, sender_email
        )
        
        if result['success']:
            logger.info(f"Persian email sent successfully to {recipient_email}")
        else:
            logger.error(f"Persian email failed: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        error_msg = f"Error sending Persian email: {str(e)}"
        logger.error(error_msg)
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying Persian email send (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
        
        return {
            'success': False,
            'error': error_msg,
            'recipient_email': recipient_email
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_bulk_persian_emails_task(self, recipients: List[Dict[str, Any]], 
                                 subject_template: str, template_name: str,
                                 base_context: Dict[str, Any]):
    """
    Send bulk Persian emails with personalization.
    
    Args:
        recipients: List of recipient dictionaries
        subject_template: Subject template with placeholders
        template_name: Email template name
        base_context: Base context for all emails
    
    Returns:
        Dict containing bulk sending results
    """
    logger.info(f"Sending bulk Persian emails to {len(recipients)} recipients")
    
    try:
        email_service = PersianEmailService()
        results = email_service.send_bulk_persian_emails(
            recipients, subject_template, template_name, base_context
        )
        
        logger.info(f"Bulk Persian email completed: {results['successful_sends']} sent, "
                   f"{results['failed_sends']} failed")
        
        return {
            'success': True,
            'results': results
        }
        
    except Exception as e:
        error_msg = f"Error sending bulk Persian emails: {str(e)}"
        logger.error(error_msg)
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying bulk Persian email send (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
        
        return {
            'success': False,
            'error': error_msg,
            'total_recipients': len(recipients)
        }


@shared_task(bind=True, max_retries=2)
def validate_all_external_services_task(self):
    """
    Validate connectivity to all external services.
    This task should run every hour to monitor service health.
    
    Returns:
        Dict containing validation results for all services
    """
    logger.info("Starting comprehensive external service validation")
    
    try:
        results = validate_all_external_services()
        
        # Analyze overall health
        service_health = {}
        total_services = 0
        healthy_services = 0
        
        # Check gold price APIs
        gold_api_health = results['services']['gold_price_apis']
        service_health['gold_price_apis'] = gold_api_health['health_percentage']
        total_services += 1
        if gold_api_health['health_percentage'] >= 50:
            healthy_services += 1
        
        # Check SMS providers
        sms_providers = results['services']['sms_providers']
        sms_healthy = sum(1 for provider in sms_providers.values() if provider['healthy'])
        sms_total = len(sms_providers)
        sms_health_percentage = (sms_healthy / sms_total * 100) if sms_total > 0 else 0
        service_health['sms_providers'] = sms_health_percentage
        total_services += 1
        if sms_health_percentage >= 50:
            healthy_services += 1
        
        # Check email service
        email_health = results['services']['email_service']
        service_health['email_service'] = 100 if email_health['healthy'] else 0
        total_services += 1
        if email_health['healthy']:
            healthy_services += 1
        
        # Calculate overall health
        overall_health = (healthy_services / total_services * 100) if total_services > 0 else 0
        
        # Record health metrics
        record_external_service_health_metric.apply_async(
            args=[overall_health, healthy_services, total_services, service_health]
        )
        
        # Send alerts if overall health is poor
        if overall_health < 70:
            send_external_service_alert.apply_async(
                args=['external_service_health_poor', {
                    'overall_health': overall_health,
                    'service_health': service_health,
                    'results': results
                }]
            )
        
        logger.info(f"External service validation completed: {healthy_services}/{total_services} "
                   f"services healthy ({overall_health:.1f}%)")
        
        return {
            'success': True,
            'overall_health': overall_health,
            'service_health': service_health,
            'detailed_results': results
        }
        
    except Exception as e:
        error_msg = f"Unexpected error in external service validation: {str(e)}"
        logger.error(error_msg)
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying external service validation (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=60)
        
        return {'success': False, 'error': error_msg}


@shared_task(bind=True)
def send_external_service_alert(self, alert_type: str, alert_data: Dict[str, Any]):
    """
    Send external service related alerts to administrators.
    
    Args:
        alert_type: Type of alert
        alert_data: Alert data dictionary
    
    Returns:
        Dict containing alert sending results
    """
    logger.info(f"Sending external service alert: {alert_type}")
    
    try:
        # Prepare alert message based on type
        if alert_type == 'iranian_gold_price_high_failure_rate':
            message = f"هشدار: نرخ بالای خطا در به‌روزرسانی قیمت طلای ایرانی - {len(alert_data.get('failed_karats', []))} عیار ناموفق"
            
        elif alert_type == 'iranian_gold_api_health_poor':
            healthy_apis = alert_data.get('results', {}).get('healthy_apis', 0)
            total_apis = alert_data.get('results', {}).get('total_apis', 0)
            message = f"هشدار: سلامت ضعیف API قیمت طلای ایرانی - {healthy_apis}/{total_apis} API سالم"
            
        elif alert_type == 'iranian_gold_price_update_failed':
            message = f"خطای حیاتی: به‌روزرسانی قیمت طلای ایرانی کاملاً ناموفق - {alert_data.get('error', 'خطای نامشخص')}"
            
        elif alert_type == 'external_service_health_poor':
            overall_health = alert_data.get('overall_health', 0)
            message = f"هشدار: سلامت ضعیف سرویس‌های خارجی - {overall_health:.1f}% سالم"
            
        else:
            message = f"هشدار سرویس خارجی: {alert_type}"
        
        # Log the alert
        logger.warning(f"EXTERNAL SERVICE ALERT [{alert_type}]: {message}")
        
        # TODO: Implement actual notification sending when notification system is ready
        # This would integrate with the notification system once it's fully implemented
        
        return {
            'success': True,
            'alert_type': alert_type,
            'message': message,
            'sent_at': timezone.now().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Error sending external service alert: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg, 'alert_type': alert_type}


@shared_task(bind=True)
def record_iranian_gold_price_health_metric(self, success_rate: float, 
                                           successful_updates: int, failed_updates: int):
    """
    Record Iranian gold price update health metrics.
    
    Args:
        success_rate: Success rate percentage
        successful_updates: Number of successful updates
        failed_updates: Number of failed updates
    
    Returns:
        Dict containing metric recording results
    """
    try:
        logger.info(f"Iranian gold price health metrics: {success_rate:.1f}% success rate, "
                   f"{successful_updates} successful, {failed_updates} failed")
        
        # Log health metrics for monitoring
        logger.info(f"HEALTH_METRIC: iranian_gold_price_update success_rate={success_rate:.1f}% "
                   f"successful={successful_updates} failed={failed_updates}")
        
        return {
            'success': True,
            'success_rate': success_rate,
            'successful_updates': successful_updates,
            'failed_updates': failed_updates,
            'recorded_at': timezone.now().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Error recording Iranian gold price health metric: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}


@shared_task(bind=True)
def record_iranian_api_health_metric(self, health_percentage: float, 
                                    healthy_apis: int, total_apis: int):
    """
    Record Iranian API health metrics.
    
    Args:
        health_percentage: API health percentage
        healthy_apis: Number of healthy APIs
        total_apis: Total number of APIs
    
    Returns:
        Dict containing metric recording results
    """
    try:
        logger.info(f"Iranian API health metrics: {health_percentage:.1f}% healthy, "
                   f"{healthy_apis}/{total_apis} APIs operational")
        
        # Log API health metrics for monitoring
        logger.info(f"HEALTH_METRIC: iranian_gold_price_api_health health_percentage={health_percentage:.1f}% "
                   f"healthy_apis={healthy_apis} total_apis={total_apis}")
        
        return {
            'success': True,
            'health_percentage': health_percentage,
            'healthy_apis': healthy_apis,
            'total_apis': total_apis,
            'recorded_at': timezone.now().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Error recording Iranian API health metric: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}


@shared_task(bind=True)
def record_external_service_health_metric(self, overall_health: float, 
                                         healthy_services: int, total_services: int,
                                         service_health: Dict[str, float]):
    """
    Record external service health metrics.
    
    Args:
        overall_health: Overall health percentage
        healthy_services: Number of healthy services
        total_services: Total number of services
        service_health: Health breakdown by service type
    
    Returns:
        Dict containing metric recording results
    """
    try:
        logger.info(f"External service health metrics: {overall_health:.1f}% overall health, "
                   f"{healthy_services}/{total_services} services healthy")
        
        # Log detailed health metrics for monitoring
        logger.info(f"HEALTH_METRIC: external_service_health overall_health={overall_health:.1f}% "
                   f"healthy_services={healthy_services} total_services={total_services}")
        
        for service_type, health in service_health.items():
            logger.info(f"HEALTH_METRIC: {service_type}_health health_percentage={health:.1f}%")
        
        return {
            'success': True,
            'overall_health': overall_health,
            'healthy_services': healthy_services,
            'total_services': total_services,
            'service_health': service_health,
            'recorded_at': timezone.now().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Error recording external service health metric: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}


# Convenience tasks for common external service operations
@shared_task
def force_iranian_gold_price_refresh():
    """
    Force immediate refresh of all Iranian gold prices, bypassing cache.
    This task can be triggered manually when needed.
    
    Returns:
        Dict containing refresh results
    """
    logger.info("Force refreshing all Iranian gold prices")
    
    # Clear all caches first
    IranianGoldPriceAPI.invalidate_cache()
    
    # Trigger immediate update
    result = update_iranian_gold_prices.apply()
    
    logger.info("Force Iranian gold price refresh completed")
    return result.get() if result else {'success': False, 'error': 'Task execution failed'}


@shared_task
def send_payment_reminder_sms(customer_phone: str, customer_name: str, 
                             contract_number: str, amount: str, due_date: str):
    """Send payment reminder SMS to customer."""
    message = f"""سلام {customer_name} عزیز
یادآوری پرداخت قسط طلای قرضی
شماره قرارداد: {contract_number}
مبلغ: {amount} تومان
سررسید: {due_date}
لطفاً در اسرع وقت اقدام فرمایید.
طلا و جواهرات زرگر"""
    
    return send_persian_sms_task.apply_async(args=[customer_phone, message])


@shared_task
def send_birthday_greeting_sms(customer_phone: str, customer_name: str):
    """Send birthday greeting SMS to customer."""
    message = f"""تولدت مبارک {customer_name} عزیز! 🎉
در این روز خاص، آرزوی سلامتی و شادی برایت داریم.
به مناسبت تولدت، تخفیف ویژه ۱۰٪ برای خرید طلا و جواهرات.
طلا و جواهرات زرگر"""
    
    return send_persian_sms_task.apply_async(args=[customer_phone, message])


@shared_task
def send_special_offer_sms(customer_phone: str, customer_name: str, 
                          offer_title: str, offer_description: str, expiry_date: str):
    """Send special offer SMS to customer."""
    message = f"""{customer_name} عزیز
{offer_title}
{offer_description}
اعتبار تا: {expiry_date}
طلا و جواهرات زرگر"""
    
    return send_persian_sms_task.apply_async(args=[customer_phone, message])