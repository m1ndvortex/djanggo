"""
Celery tasks for notification system.
"""
import logging
from datetime import datetime, timedelta
from celery import shared_task
from django.utils import timezone
from django.db import transaction

from .notification_models import (
    NotificationTemplate, 
    NotificationSchedule, 
    Notification, 
    NotificationProvider
)
from .notification_services import PushNotificationSystem, NotificationScheduler
from zargar.customers.models import Customer
from zargar.gold_installments.models import GoldInstallmentContract

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_scheduled_notifications(self):
    """
    Process all scheduled notifications that are ready to send.
    This task should run every minute.
    """
    try:
        scheduler = NotificationScheduler()
        stats = scheduler.process_scheduled_notifications()
        
        logger.info(f"Processed scheduled notifications: {stats}")
        return {
            'success': True,
            'stats': stats,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing scheduled notifications: {str(e)}")
        
        # Retry with exponential backoff
        countdown = 2 ** self.request.retries
        raise self.retry(exc=e, countdown=countdown, max_retries=3)


@shared_task(bind=True, max_retries=3)
def process_recurring_schedules(self):
    """
    Process recurring notification schedules.
    This task should run every hour.
    """
    try:
        scheduler = NotificationScheduler()
        stats = scheduler.process_recurring_schedules()
        
        logger.info(f"Processed recurring schedules: {stats}")
        return {
            'success': True,
            'stats': stats,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing recurring schedules: {str(e)}")
        
        # Retry with exponential backoff
        countdown = 2 ** self.request.retries
        raise self.retry(exc=e, countdown=countdown, max_retries=3)


@shared_task(bind=True, max_retries=5)
def send_single_notification(self, notification_id):
    """
    Send a single notification.
    
    Args:
        notification_id: ID of the notification to send
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        system = PushNotificationSystem()
        
        success = system.send_notification(notification)
        
        return {
            'success': success,
            'notification_id': notification_id,
            'status': notification.status,
            'timestamp': timezone.now().isoformat()
        }
        
    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return {
            'success': False,
            'error': f"Notification {notification_id} not found"
        }
        
    except Exception as e:
        logger.error(f"Error sending notification {notification_id}: {str(e)}")
        
        # Retry with exponential backoff
        countdown = 2 ** self.request.retries
        raise self.retry(exc=e, countdown=countdown, max_retries=5)


@shared_task(bind=True)
def send_bulk_notifications_async(
    self, 
    template_type, 
    recipients, 
    context_template, 
    delivery_methods=None, 
    scheduled_at=None
):
    """
    Send bulk notifications asynchronously.
    
    Args:
        template_type: Type of notification template
        recipients: List of recipient dictionaries
        context_template: Base context for template rendering
        delivery_methods: List of delivery methods
        scheduled_at: When to send notifications (ISO format string)
    """
    try:
        # Parse scheduled_at if provided
        scheduled_datetime = None
        if scheduled_at:
            scheduled_datetime = datetime.fromisoformat(scheduled_at)
        
        system = PushNotificationSystem()
        stats = system.send_bulk_notifications(
            template_type=template_type,
            recipients=recipients,
            context_template=context_template,
            delivery_methods=delivery_methods,
            scheduled_at=scheduled_datetime
        )
        
        logger.info(f"Bulk notification stats: {stats}")
        return {
            'success': True,
            'stats': stats,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in bulk notification task: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task
def send_daily_payment_reminders():
    """
    Send daily payment reminders for overdue gold installment contracts.
    This task should run daily at 9:00 AM.
    """
    try:
        # Get overdue contracts
        overdue_contracts = GoldInstallmentContract.objects.filter(
            status='active'
        ).select_related('customer')
        
        # Filter contracts that are actually overdue
        # (This would need proper implementation based on payment schedule logic)
        
        recipients = []
        for contract in overdue_contracts:
            # Calculate overdue amount and days
            # This is a simplified example - implement proper calculation
            recipients.append({
                'type': 'customer',
                'id': contract.customer.id,
                'context': {
                    'customer_name': contract.customer.full_persian_name,
                    'contract_number': contract.contract_number,
                    'overdue_days': '5',  # Calculate actual overdue days
                    'amount': '2,500,000',  # Calculate actual overdue amount
                }
            })
        
        if recipients:
            system = PushNotificationSystem()
            stats = system.send_bulk_notifications(
                template_type='payment_overdue',
                recipients=recipients,
                context_template={
                    'shop_name': 'طلا و جواهرات زرگر',
                    'contact_phone': '021-12345678',
                },
                delivery_methods=['sms']
            )
            
            logger.info(f"Daily payment reminders sent: {stats}")
            return stats
        else:
            logger.info("No overdue contracts found for payment reminders")
            return {'created': 0, 'sent': 0, 'failed': 0}
            
    except Exception as e:
        logger.error(f"Error sending daily payment reminders: {str(e)}")
        return {'error': str(e)}


@shared_task
def send_birthday_greetings():
    """
    Send birthday greetings to customers.
    This task should run daily at 8:00 AM.
    """
    try:
        from django.utils import timezone
        import jdatetime
        
        # Get today's date in Shamsi calendar
        today_shamsi = jdatetime.date.today()
        
        # Find customers with birthdays today
        birthday_customers = Customer.objects.filter(
            is_active=True,
            birth_date_shamsi__contains=f"{today_shamsi.month:02d}/{today_shamsi.day:02d}"
        )
        
        recipients = []
        for customer in birthday_customers:
            recipients.append({
                'type': 'customer',
                'id': customer.id,
                'context': {
                    'customer_name': customer.full_persian_name,
                    'birth_date': customer.birth_date_shamsi,
                }
            })
        
        if recipients:
            system = PushNotificationSystem()
            stats = system.send_bulk_notifications(
                template_type='birthday_greeting',
                recipients=recipients,
                context_template={
                    'shop_name': 'طلا و جواهرات زرگر',
                    'special_offer': 'تخفیف ۱۰٪ ویژه تولد شما',
                },
                delivery_methods=['sms']
            )
            
            logger.info(f"Birthday greetings sent: {stats}")
            return stats
        else:
            logger.info("No customer birthdays today")
            return {'created': 0, 'sent': 0, 'failed': 0}
            
    except Exception as e:
        logger.error(f"Error sending birthday greetings: {str(e)}")
        return {'error': str(e)}


@shared_task
def send_appointment_reminders():
    """
    Send appointment reminders for next day appointments.
    This task should run daily at 6:00 PM.
    """
    try:
        # This is a placeholder - implement when appointment system is added
        # For now, we'll just log that the task ran
        
        logger.info("Appointment reminder task executed (no appointments system yet)")
        return {'created': 0, 'sent': 0, 'failed': 0}
        
    except Exception as e:
        logger.error(f"Error sending appointment reminders: {str(e)}")
        return {'error': str(e)}


@shared_task
def cleanup_old_notifications():
    """
    Clean up old notification records to prevent database bloat.
    This task should run weekly.
    """
    try:
        # Delete notifications older than 90 days
        cutoff_date = timezone.now() - timedelta(days=90)
        
        # Delete old notifications and their logs
        old_notifications = Notification.objects.filter(created_at__lt=cutoff_date)
        count = old_notifications.count()
        
        # Delete in batches to avoid memory issues
        batch_size = 1000
        deleted_total = 0
        
        while old_notifications.exists():
            batch_ids = list(old_notifications.values_list('id', flat=True)[:batch_size])
            Notification.objects.filter(id__in=batch_ids).delete()
            deleted_total += len(batch_ids)
        
        logger.info(f"Cleaned up {deleted_total} old notifications")
        return {
            'deleted_notifications': deleted_total,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old notifications: {str(e)}")
        return {'error': str(e)}


@shared_task
def update_notification_statistics():
    """
    Update notification provider statistics and performance metrics.
    This task should run hourly.
    """
    try:
        # Update provider statistics
        providers = NotificationProvider.objects.filter(is_active=True)
        
        for provider in providers:
            # Calculate recent success rates, costs, etc.
            # This is a placeholder for more complex statistics
            
            recent_notifications = Notification.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=1),
                delivery_method=provider.provider_type
            )
            
            sent_count = recent_notifications.filter(status='sent').count()
            delivered_count = recent_notifications.filter(status='delivered').count()
            failed_count = recent_notifications.filter(status='failed').count()
            
            if sent_count > 0:
                provider.update_statistics(
                    sent=sent_count,
                    delivered=delivered_count,
                    failed=failed_count
                )
        
        logger.info("Updated notification provider statistics")
        return {'providers_updated': providers.count()}
        
    except Exception as e:
        logger.error(f"Error updating notification statistics: {str(e)}")
        return {'error': str(e)}


# Convenience functions for common notification scenarios
@shared_task
def send_payment_reminder_task(customer_id, contract_number, amount, due_date):
    """Send payment reminder for a specific customer."""
    try:
        system = PushNotificationSystem()
        notifications = system.create_notification(
            template_type='payment_reminder',
            recipient_type='customer',
            recipient_id=customer_id,
            context={
                'customer_name': Customer.objects.get(id=customer_id).full_persian_name,
                'contract_number': contract_number,
                'amount': amount,
                'due_date': due_date,
            },
            delivery_methods=['sms']
        )
        
        # Send immediately
        sent_count = 0
        for notification in notifications:
            if system.send_notification(notification):
                sent_count += 1
        
        return {
            'success': True,
            'notifications_created': len(notifications),
            'notifications_sent': sent_count
        }
        
    except Exception as e:
        logger.error(f"Error sending payment reminder: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_special_offer_task(customer_ids, offer_title, offer_description, expiry_date):
    """Send special offer to multiple customers."""
    try:
        recipients = []
        for customer_id in customer_ids:
            try:
                customer = Customer.objects.get(id=customer_id)
                recipients.append({
                    'type': 'customer',
                    'id': customer_id,
                    'context': {
                        'customer_name': customer.full_persian_name,
                    }
                })
            except Customer.DoesNotExist:
                continue
        
        if recipients:
            system = PushNotificationSystem()
            stats = system.send_bulk_notifications(
                template_type='special_offer',
                recipients=recipients,
                context_template={
                    'offer_title': offer_title,
                    'offer_description': offer_description,
                    'expiry_date': expiry_date,
                },
                delivery_methods=['sms']
            )
            
            return {
                'success': True,
                'stats': stats
            }
        else:
            return {
                'success': False,
                'error': 'No valid customers found'
            }
            
    except Exception as e:
        logger.error(f"Error sending special offer: {str(e)}")
        return {'success': False, 'error': str(e)}