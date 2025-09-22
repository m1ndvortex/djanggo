"""
Push notification system services for zargar project.
"""
import logging
import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.template import Template, Context
from django.core.mail import send_mail
from django.db import transaction
from celery import shared_task

from .notification_models import (
    NotificationTemplate, 
    NotificationSchedule, 
    Notification, 
    NotificationDeliveryLog,
    NotificationProvider
)
from zargar.customers.models import Customer
from zargar.core.models import User

logger = logging.getLogger(__name__)


class PushNotificationSystem:
    """
    Main push notification system for managing all types of notifications.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_notification(
        self,
        template_type: str,
        recipient_type: str,
        recipient_id: int,
        context: Dict[str, Any],
        delivery_methods: List[str] = None,
        scheduled_at: datetime = None,
        priority: str = 'normal'
    ) -> List[Notification]:
        """
        Create notification(s) for a recipient.
        
        Args:
            template_type: Type of notification template
            recipient_type: Type of recipient (customer, user, etc.)
            recipient_id: ID of the recipient
            context: Context variables for template rendering
            delivery_methods: List of delivery methods (sms, email, etc.)
            scheduled_at: When to send the notification
            priority: Priority level (low, normal, high, urgent)
            
        Returns:
            List of created Notification objects
        """
        try:
            # Get template
            template = NotificationTemplate.get_default_template(template_type)
            if not template:
                self.logger.error(f"No template found for type: {template_type}")
                return []
            
            # Get recipient information
            recipient_info = self._get_recipient_info(recipient_type, recipient_id)
            if not recipient_info:
                self.logger.error(f"Recipient not found: {recipient_type}#{recipient_id}")
                return []
            
            # Determine delivery methods
            if not delivery_methods:
                delivery_methods = template.delivery_methods or ['sms']
            
            # Render template content
            rendered = template.render_content(context)
            
            # Create notifications for each delivery method
            notifications = []
            for method in delivery_methods:
                # Check if recipient has contact info for this method
                if not self._can_deliver_via_method(recipient_info, method):
                    self.logger.warning(
                        f"Cannot deliver via {method} to {recipient_type}#{recipient_id}"
                    )
                    continue
                
                notification = Notification.objects.create(
                    template=template,
                    recipient_type=recipient_type,
                    recipient_id=recipient_id,
                    recipient_name=recipient_info['name'],
                    recipient_phone=recipient_info.get('phone', ''),
                    recipient_email=recipient_info.get('email', ''),
                    title=rendered['title'],
                    content=rendered['content'],
                    delivery_method=method,
                    priority=priority,
                    scheduled_at=scheduled_at or timezone.now(),
                    context_data=context
                )
                notifications.append(notification)
                
                # Log creation
                NotificationDeliveryLog.objects.create(
                    notification=notification,
                    action='created',
                    success=True,
                    metadata={'context': context}
                )
            
            # Update template usage
            template.increment_usage()
            
            self.logger.info(
                f"Created {len(notifications)} notifications for {recipient_type}#{recipient_id}"
            )
            
            return notifications
            
        except Exception as e:
            self.logger.error(f"Error creating notification: {str(e)}")
            return []
    
    def send_notification(self, notification: Notification) -> bool:
        """
        Send a single notification.
        
        Args:
            notification: Notification object to send
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Check if notification is ready to send
            if not notification.is_ready_to_send:
                return False
            
            # Get provider for delivery method
            provider = NotificationProvider.get_default_provider(
                notification.delivery_method
            )
            if not provider:
                notification.mark_as_failed(
                    f"No provider configured for {notification.delivery_method}"
                )
                return False
            
            # Mark as sending
            notification.status = 'sending'
            notification.save(update_fields=['status'])
            
            # Log sending attempt
            NotificationDeliveryLog.objects.create(
                notification=notification,
                action='sending',
                provider_name=provider.name,
                success=True
            )
            
            # Send via appropriate method
            success = False
            if notification.delivery_method == 'sms':
                success = self._send_sms(notification, provider)
            elif notification.delivery_method == 'email':
                success = self._send_email(notification, provider)
            elif notification.delivery_method == 'push':
                success = self._send_push(notification, provider)
            elif notification.delivery_method == 'whatsapp':
                success = self._send_whatsapp(notification, provider)
            
            if success:
                notification.mark_as_sent()
                provider.update_statistics(sent=1)
                self.logger.info(f"Notification {notification.id} sent successfully")
            else:
                notification.mark_as_failed("Delivery failed")
                provider.update_statistics(failed=1)
                self.logger.error(f"Failed to send notification {notification.id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending notification {notification.id}: {str(e)}")
            notification.mark_as_failed(str(e))
            return False
    
    def send_bulk_notifications(
        self,
        template_type: str,
        recipients: List[Dict[str, Any]],
        context_template: Dict[str, Any],
        delivery_methods: List[str] = None,
        scheduled_at: datetime = None
    ) -> Dict[str, int]:
        """
        Send bulk notifications to multiple recipients.
        
        Args:
            template_type: Type of notification template
            recipients: List of recipient dictionaries
            context_template: Base context for template rendering
            delivery_methods: List of delivery methods
            scheduled_at: When to send notifications
            
        Returns:
            Dictionary with statistics (created, sent, failed)
        """
        stats = {'created': 0, 'sent': 0, 'failed': 0}
        
        try:
            for recipient in recipients:
                # Merge recipient-specific context
                context = {**context_template, **recipient.get('context', {})}
                
                # Create notifications
                notifications = self.create_notification(
                    template_type=template_type,
                    recipient_type=recipient['type'],
                    recipient_id=recipient['id'],
                    context=context,
                    delivery_methods=delivery_methods,
                    scheduled_at=scheduled_at
                )
                
                stats['created'] += len(notifications)
                
                # Send immediately if not scheduled
                if not scheduled_at or scheduled_at <= timezone.now():
                    for notification in notifications:
                        if self.send_notification(notification):
                            stats['sent'] += 1
                        else:
                            stats['failed'] += 1
            
            self.logger.info(f"Bulk notification stats: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Error in bulk notification: {str(e)}")
            return stats
    
    def _get_recipient_info(self, recipient_type: str, recipient_id: int) -> Optional[Dict]:
        """Get recipient contact information."""
        try:
            if recipient_type == 'customer':
                customer = Customer.objects.get(id=recipient_id)
                return {
                    'name': customer.full_persian_name,
                    'phone': customer.phone_number,
                    'email': customer.email,
                }
            elif recipient_type == 'user':
                user = User.objects.get(id=recipient_id)
                return {
                    'name': user.full_persian_name,
                    'phone': user.phone_number,
                    'email': user.email,
                }
            # Add other recipient types as needed
            
        except Exception as e:
            self.logger.error(f"Error getting recipient info: {str(e)}")
            return None
    
    def _can_deliver_via_method(self, recipient_info: Dict, method: str) -> bool:
        """Check if recipient can receive notifications via specified method."""
        if method == 'sms':
            return bool(recipient_info.get('phone'))
        elif method == 'email':
            return bool(recipient_info.get('email'))
        elif method in ['push', 'whatsapp']:
            return bool(recipient_info.get('phone'))
        return False
    
    def _send_sms(self, notification: Notification, provider: NotificationProvider) -> bool:
        """Send SMS notification via Iranian SMS provider."""
        try:
            # Iranian SMS providers typically use REST APIs
            # This is a generic implementation - adapt for specific providers
            
            payload = {
                'username': provider.api_key,
                'password': provider.api_secret,
                'to': notification.recipient_phone,
                'text': notification.content,
                'from': provider.settings.get('sender_number', '10008663')
            }
            
            response = requests.post(
                provider.api_endpoint,
                json=payload,
                timeout=30
            )
            
            # Log provider response
            NotificationDeliveryLog.objects.create(
                notification=notification,
                action='sent',
                provider_name=provider.name,
                provider_response=response.json() if response.content else {},
                success=response.status_code == 200,
                error_code=str(response.status_code) if response.status_code != 200 else '',
                error_message=response.text if response.status_code != 200 else ''
            )
            
            if response.status_code == 200:
                response_data = response.json()
                notification.provider_response = response_data
                notification.provider_message_id = response_data.get('message_id', '')
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"SMS sending error: {str(e)}")
            NotificationDeliveryLog.objects.create(
                notification=notification,
                action='failed',
                provider_name=provider.name,
                success=False,
                error_message=str(e)
            )
            return False
    
    def _send_email(self, notification: Notification, provider: NotificationProvider) -> bool:
        """Send email notification."""
        try:
            # Use Django's email system or provider API
            success = send_mail(
                subject=notification.title,
                message=notification.content,
                from_email=provider.settings.get('from_email', settings.DEFAULT_FROM_EMAIL),
                recipient_list=[notification.recipient_email],
                fail_silently=False
            )
            
            NotificationDeliveryLog.objects.create(
                notification=notification,
                action='sent' if success else 'failed',
                provider_name=provider.name,
                success=success
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Email sending error: {str(e)}")
            NotificationDeliveryLog.objects.create(
                notification=notification,
                action='failed',
                provider_name=provider.name,
                success=False,
                error_message=str(e)
            )
            return False
    
    def _send_push(self, notification: Notification, provider: NotificationProvider) -> bool:
        """Send push notification (placeholder for future implementation)."""
        # Implement push notification logic here
        # This could integrate with Firebase, OneSignal, etc.
        self.logger.info(f"Push notification not implemented yet: {notification.id}")
        return False
    
    def _send_whatsapp(self, notification: Notification, provider: NotificationProvider) -> bool:
        """Send WhatsApp notification (placeholder for future implementation)."""
        # Implement WhatsApp API integration here
        self.logger.info(f"WhatsApp notification not implemented yet: {notification.id}")
        return False


class NotificationScheduler:
    """
    Service for managing scheduled notifications.
    """
    
    def __init__(self):
        self.notification_system = PushNotificationSystem()
        self.logger = logging.getLogger(__name__)
    
    def process_scheduled_notifications(self) -> Dict[str, int]:
        """
        Process all scheduled notifications that are ready to send.
        
        Returns:
            Dictionary with processing statistics
        """
        stats = {'processed': 0, 'sent': 0, 'failed': 0, 'expired': 0}
        
        try:
            # Get notifications ready to send
            ready_notifications = Notification.objects.filter(
                status__in=['pending', 'queued'],
                scheduled_at__lte=timezone.now()
            ).exclude(
                expires_at__lt=timezone.now()
            )
            
            for notification in ready_notifications:
                stats['processed'] += 1
                
                # Check if expired
                if notification.is_expired:
                    notification.cancel("Expired")
                    stats['expired'] += 1
                    continue
                
                # Send notification
                if self.notification_system.send_notification(notification):
                    stats['sent'] += 1
                else:
                    stats['failed'] += 1
            
            self.logger.info(f"Scheduled notification processing stats: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Error processing scheduled notifications: {str(e)}")
            return stats
    
    def process_recurring_schedules(self) -> Dict[str, int]:
        """
        Process recurring notification schedules.
        
        Returns:
            Dictionary with processing statistics
        """
        stats = {'schedules_processed': 0, 'notifications_created': 0}
        
        try:
            # Get active recurring schedules that are due
            due_schedules = NotificationSchedule.objects.filter(
                status='active',
                schedule_type='recurring',
                next_run_at__lte=timezone.now()
            )
            
            for schedule in due_schedules:
                stats['schedules_processed'] += 1
                
                # Get recipients based on criteria
                recipients = self._get_schedule_recipients(schedule)
                
                # Create notifications for recipients
                for recipient in recipients:
                    notifications = self.notification_system.create_notification(
                        template_type=schedule.template.template_type,
                        recipient_type=recipient['type'],
                        recipient_id=recipient['id'],
                        context=recipient.get('context', {}),
                        delivery_methods=schedule.delivery_methods,
                        scheduled_at=timezone.now()
                    )
                    stats['notifications_created'] += len(notifications)
                
                # Update schedule statistics
                schedule.update_statistics(
                    sent=len(recipients),
                    delivered=0,  # Will be updated when notifications are actually sent
                    failed=0
                )
            
            self.logger.info(f"Recurring schedule processing stats: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Error processing recurring schedules: {str(e)}")
            return stats
    
    def _get_schedule_recipients(self, schedule: NotificationSchedule) -> List[Dict]:
        """
        Get recipients for a notification schedule based on target criteria.
        
        Args:
            schedule: NotificationSchedule object
            
        Returns:
            List of recipient dictionaries
        """
        recipients = []
        criteria = schedule.target_criteria
        
        try:
            # Example criteria processing
            if criteria.get('recipient_type') == 'customer':
                # Get customers based on criteria
                queryset = Customer.objects.all()
                
                # Apply filters based on criteria
                if criteria.get('customer_type'):
                    queryset = queryset.filter(customer_type=criteria['customer_type'])
                
                if criteria.get('is_vip') is not None:
                    queryset = queryset.filter(is_vip=criteria['is_vip'])
                
                if criteria.get('has_active_contracts'):
                    # Filter customers with active gold installment contracts
                    from zargar.gold_installments.models import GoldInstallmentContract
                    active_contract_customers = GoldInstallmentContract.objects.filter(
                        status='active'
                    ).values_list('customer_id', flat=True)
                    queryset = queryset.filter(id__in=active_contract_customers)
                
                # Convert to recipient format
                for customer in queryset:
                    recipients.append({
                        'type': 'customer',
                        'id': customer.id,
                        'context': {
                            'customer_name': customer.full_persian_name,
                            'phone_number': customer.phone_number,
                        }
                    })
            
            # Add other recipient types as needed
            
        except Exception as e:
            self.logger.error(f"Error getting schedule recipients: {str(e)}")
        
        return recipients


# Celery tasks for background processing
@shared_task
def process_scheduled_notifications():
    """Celery task to process scheduled notifications."""
    scheduler = NotificationScheduler()
    return scheduler.process_scheduled_notifications()


@shared_task
def process_recurring_schedules():
    """Celery task to process recurring notification schedules."""
    scheduler = NotificationScheduler()
    return scheduler.process_recurring_schedules()


@shared_task
def send_notification_task(notification_id):
    """Celery task to send a single notification."""
    try:
        notification = Notification.objects.get(id=notification_id)
        system = PushNotificationSystem()
        return system.send_notification(notification)
    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return False


@shared_task
def send_bulk_notifications_task(
    template_type,
    recipients,
    context_template,
    delivery_methods=None,
    scheduled_at=None
):
    """Celery task to send bulk notifications."""
    system = PushNotificationSystem()
    return system.send_bulk_notifications(
        template_type=template_type,
        recipients=recipients,
        context_template=context_template,
        delivery_methods=delivery_methods,
        scheduled_at=scheduled_at
    )


# Convenience functions for common notification types
def send_payment_reminder(customer_id: int, contract_number: str, amount: float, due_date: str):
    """Send payment reminder notification."""
    system = PushNotificationSystem()
    return system.create_notification(
        template_type='payment_reminder',
        recipient_type='customer',
        recipient_id=customer_id,
        context={
            'customer_name': Customer.objects.get(id=customer_id).full_persian_name,
            'contract_number': contract_number,
            'amount': amount,
            'due_date': due_date,
        },
        delivery_methods=['sms', 'email']
    )


def send_birthday_greeting(customer_id: int):
    """Send birthday greeting notification."""
    system = PushNotificationSystem()
    customer = Customer.objects.get(id=customer_id)
    return system.create_notification(
        template_type='birthday_greeting',
        recipient_type='customer',
        recipient_id=customer_id,
        context={
            'customer_name': customer.full_persian_name,
            'birth_date': customer.birth_date_shamsi,
        },
        delivery_methods=['sms']
    )


def send_appointment_reminder(customer_id: int, appointment_date: str, appointment_time: str):
    """Send appointment reminder notification."""
    system = PushNotificationSystem()
    return system.create_notification(
        template_type='appointment_reminder',
        recipient_type='customer',
        recipient_id=customer_id,
        context={
            'customer_name': Customer.objects.get(id=customer_id).full_persian_name,
            'appointment_date': appointment_date,
            'appointment_time': appointment_time,
        },
        delivery_methods=['sms']
    )


def send_special_offer(customer_ids: List[int], offer_title: str, offer_description: str, expiry_date: str):
    """Send special offer notification to multiple customers."""
    system = PushNotificationSystem()
    recipients = []
    
    for customer_id in customer_ids:
        customer = Customer.objects.get(id=customer_id)
        recipients.append({
            'type': 'customer',
            'id': customer_id,
            'context': {
                'customer_name': customer.full_persian_name,
            }
        })
    
    return system.send_bulk_notifications(
        template_type='special_offer',
        recipients=recipients,
        context_template={
            'offer_title': offer_title,
            'offer_description': offer_description,
            'expiry_date': expiry_date,
        },
        delivery_methods=['sms']
    )