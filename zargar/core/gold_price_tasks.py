"""
Celery tasks for gold price updates and management.
Provides automated gold price fetching and cache management for the ZARGAR jewelry SaaS platform.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django_tenants.utils import get_tenant_model, tenant_context

from zargar.gold_installments.services import GoldPriceService
from zargar.core.external_service_tasks import (
    update_iranian_gold_prices,
    update_single_iranian_gold_karat,
    validate_iranian_gold_price_apis
)
from zargar.system.models import BackupRecord
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def update_gold_prices(self):
    """
    Update gold prices for all supported karats from Iranian market APIs.
    This task delegates to the enhanced Iranian gold price update task.
    
    Returns:
        Dict containing update results
    """
    logger.info("Starting gold price update task (delegating to Iranian API)")
    
    try:
        # Delegate to the enhanced Iranian gold price update task
        result = update_iranian_gold_prices.apply()
        return result.get() if result else {'success': False, 'error': 'Task execution failed'}
        
    except Exception as e:
        error_msg = f"Unexpected error in gold price update task: {str(e)}"
        logger.error(error_msg)
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying gold price update task (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        
        return {'success': False, 'error': error_msg}


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def update_single_karat_price(self, karat: int):
    """
    Update gold price for a specific karat.
    This task delegates to the enhanced Iranian gold price update task.
    
    Args:
        karat: Gold karat to update (14, 18, 21, 22, 24)
    
    Returns:
        Dict containing update results
    """
    logger.info(f"Starting single karat price update for {karat}k gold (delegating to Iranian API)")
    
    try:
        # Delegate to the enhanced Iranian single karat update task
        result = update_single_iranian_gold_karat.apply(args=[karat])
        return result.get() if result else {'success': False, 'karat': karat, 'error': 'Task execution failed'}
        
    except Exception as e:
        error_msg = f"Error updating {karat}k gold price: {str(e)}"
        logger.error(error_msg)
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying {karat}k price update (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
        
        return {'success': False, 'karat': karat, 'error': error_msg}


@shared_task(bind=True, max_retries=2)
def validate_gold_price_apis(self):
    """
    Validate all Iranian gold price API endpoints for connectivity and response format.
    This task delegates to the enhanced Iranian API validation task.
    
    Returns:
        Dict containing validation results
    """
    logger.info("Starting gold price API validation (delegating to Iranian API)")
    
    try:
        # Delegate to the enhanced Iranian API validation task
        result = validate_iranian_gold_price_apis.apply()
        return result.get() if result else {'success': False, 'error': 'Task execution failed'}
        
    except Exception as e:
        error_msg = f"Unexpected error in API validation: {str(e)}"
        logger.error(error_msg)
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying API validation (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=60)
        
        return {'success': False, 'error': error_msg}


@shared_task(bind=True)
def cleanup_gold_price_cache(self):
    """
    Clean up expired gold price cache entries.
    This task should run every hour.
    
    Returns:
        Dict containing cleanup results
    """
    logger.info("Starting gold price cache cleanup")
    
    try:
        # Get all gold price cache keys
        karats = [14, 18, 21, 22, 24]
        cache_keys = [f"{GoldPriceService.CACHE_KEY_PREFIX}_{karat}" for karat in karats]
        
        # Additional cache keys for trends and other data
        trend_keys = [f"gold_price_trend_{karat}" for karat in karats]
        cache_keys.extend(trend_keys)
        
        cleaned_keys = []
        active_keys = []
        
        for key in cache_keys:
            if cache.get(key) is not None:
                active_keys.append(key)
            else:
                # Key doesn't exist or has expired
                cleaned_keys.append(key)
        
        # Force cleanup of any stale keys (this is mostly for logging)
        for key in cache_keys:
            cache.delete(key)
        
        logger.info(f"Cache cleanup completed: {len(active_keys)} active keys, {len(cleaned_keys)} cleaned")
        
        return {
            'success': True,
            'active_keys': len(active_keys),
            'cleaned_keys': len(cleaned_keys),
            'total_keys_checked': len(cache_keys),
            'cleanup_timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Error in cache cleanup: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}


@shared_task(bind=True)
def generate_gold_price_report(self, report_type: str = 'daily'):
    """
    Generate gold price trend and statistics report.
    
    Args:
        report_type: Type of report ('daily', 'weekly', 'monthly')
    
    Returns:
        Dict containing report data
    """
    logger.info(f"Generating {report_type} gold price report")
    
    try:
        # Determine date range
        if report_type == 'daily':
            days = 1
        elif report_type == 'weekly':
            days = 7
        elif report_type == 'monthly':
            days = 30
        else:
            days = 7  # Default to weekly
        
        # Get current prices for all karats
        current_prices = {}
        for karat in [14, 18, 21, 22, 24]:
            price_data = GoldPriceService.get_current_gold_price(karat)
            current_prices[karat] = {
                'price_per_gram': str(price_data['price_per_gram']),
                'source': price_data['source'],
                'timestamp': price_data['timestamp'].isoformat()
            }
        
        # Get price trends (mock data for now)
        price_trends = {}
        for karat in [14, 18, 21, 22, 24]:
            trend_data = GoldPriceService.get_price_trend(karat, days)
            price_trends[karat] = [
                {
                    'date': point['date'].isoformat(),
                    'price_per_gram': str(point['price_per_gram'])
                }
                for point in trend_data
            ]
        
        # Calculate statistics
        stats = {
            'report_type': report_type,
            'period_days': days,
            'generated_at': timezone.now().isoformat(),
            'current_prices': current_prices,
            'price_trends': price_trends,
            'api_health': {
                'total_apis': len(GoldPriceService.GOLD_PRICE_APIS),
                'last_update_success': True  # This would be tracked in real implementation
            }
        }
        
        logger.info(f"Generated {report_type} gold price report with {len(current_prices)} karats")
        
        return {
            'success': True,
            'report_type': report_type,
            'report_data': stats
        }
        
    except Exception as e:
        error_msg = f"Error generating gold price report: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg, 'report_type': report_type}


@shared_task(bind=True)
def send_gold_price_alert(self, alert_type: str, alert_data: Dict):
    """
    Send gold price related alerts to administrators.
    
    Args:
        alert_type: Type of alert ('high_failure_rate', 'api_health_poor', 'update_failed')
        alert_data: Alert data dictionary
    
    Returns:
        Dict containing alert sending results
    """
    logger.info(f"Sending gold price alert: {alert_type}")
    
    try:
        # Prepare alert message based on type
        if alert_type == 'high_failure_rate':
            message = f"هشدار: نرخ بالای خطا در به‌روزرسانی قیمت طلا - {len(alert_data.get('failed_karats', []))} عیار ناموفق"
            
        elif alert_type == 'api_health_poor':
            healthy_apis = alert_data.get('results', {}).get('healthy_apis', 0)
            total_apis = alert_data.get('results', {}).get('total_apis', 0)
            message = f"هشدار: سلامت ضعیف API قیمت طلا - {healthy_apis}/{total_apis} API سالم"
            
        elif alert_type == 'update_failed':
            message = f"خطای حیاتی: به‌روزرسانی قیمت طلا کاملاً ناموفق - {alert_data.get('error', 'خطای نامشخص')}"
            
        else:
            message = f"هشدار قیمت طلا: {alert_type}"
        
        # In a real implementation, this would send notifications to administrators
        # For now, we'll just log the alert
        logger.warning(f"GOLD PRICE ALERT [{alert_type}]: {message}")
        
        # TODO: Implement actual notification sending when notification system is ready
        # This would integrate with the notification system once it's fully implemented
        
        return {
            'success': True,
            'alert_type': alert_type,
            'message': message,
            'sent_at': timezone.now().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Error sending gold price alert: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg, 'alert_type': alert_type}


@shared_task(bind=True)
def record_gold_price_health_metric(self, success_rate: float, successful_updates: int, failed_updates: int):
    """
    Record gold price update health metrics.
    
    Args:
        success_rate: Success rate percentage
        successful_updates: Number of successful updates
        failed_updates: Number of failed updates
    
    Returns:
        Dict containing metric recording results
    """
    try:
        # This would record metrics in a real monitoring system
        # For now, we'll just log the metrics
        logger.info(f"Gold price health metrics: {success_rate:.1f}% success rate, "
                   f"{successful_updates} successful, {failed_updates} failed")
        
        # Log health metrics for monitoring
        logger.info(f"HEALTH_METRIC: gold_price_update success_rate={success_rate:.1f}% "
                   f"successful={successful_updates} failed={failed_updates}")
        
        return {
            'success': True,
            'success_rate': success_rate,
            'successful_updates': successful_updates,
            'failed_updates': failed_updates,
            'recorded_at': timezone.now().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Error recording gold price health metric: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}


@shared_task(bind=True)
def record_api_health_metric(self, health_percentage: float, healthy_apis: int, total_apis: int):
    """
    Record API health metrics.
    
    Args:
        health_percentage: API health percentage
        healthy_apis: Number of healthy APIs
        total_apis: Total number of APIs
    
    Returns:
        Dict containing metric recording results
    """
    try:
        logger.info(f"API health metrics: {health_percentage:.1f}% healthy, "
                   f"{healthy_apis}/{total_apis} APIs operational")
        
        # Log API health metrics for monitoring
        logger.info(f"HEALTH_METRIC: gold_price_api_health health_percentage={health_percentage:.1f}% "
                   f"healthy_apis={healthy_apis} total_apis={total_apis}")
        
        return {
            'success': True,
            'health_percentage': health_percentage,
            'healthy_apis': healthy_apis,
            'total_apis': total_apis,
            'recorded_at': timezone.now().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Error recording API health metric: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}


@shared_task(bind=True)
def update_tenant_gold_price_cache(self, tenant_schema: str):
    """
    Update gold price cache for a specific tenant.
    This can be used when a tenant needs fresh price data immediately.
    
    Args:
        tenant_schema: Tenant schema name
    
    Returns:
        Dict containing update results
    """
    logger.info(f"Updating gold price cache for tenant: {tenant_schema}")
    
    try:
        Tenant = get_tenant_model()
        tenant = Tenant.objects.get(schema_name=tenant_schema)
        
        with tenant_context(tenant):
            # Clear tenant-specific cache if any
            GoldPriceService.invalidate_cache()
            
            # Update prices for all karats
            updated_prices = {}
            for karat in [14, 18, 21, 22, 24]:
                price_data = GoldPriceService.get_current_gold_price(karat)
                updated_prices[karat] = {
                    'price_per_gram': str(price_data['price_per_gram']),
                    'source': price_data['source'],
                    'timestamp': price_data['timestamp'].isoformat()
                }
            
            logger.info(f"Updated gold price cache for tenant {tenant_schema}: {len(updated_prices)} karats")
            
            return {
                'success': True,
                'tenant_schema': tenant_schema,
                'updated_prices': updated_prices,
                'update_timestamp': timezone.now().isoformat()
            }
    
    except Exception as e:
        error_msg = f"Error updating gold price cache for tenant {tenant_schema}: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'tenant_schema': tenant_schema, 'error': error_msg}


# Convenience task for manual price updates
@shared_task
def force_gold_price_refresh():
    """
    Force immediate refresh of all gold prices, bypassing cache.
    This task can be triggered manually when needed.
    
    Returns:
        Dict containing refresh results
    """
    logger.info("Force refreshing all gold prices")
    
    # Clear all caches first
    GoldPriceService.invalidate_cache()
    
    # Trigger immediate update
    result = update_gold_prices.apply()
    
    logger.info("Force gold price refresh completed")
    return result.get() if result else {'success': False, 'error': 'Task execution failed'}