"""
Push notification system models for zargar project.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import RegexValidator
from zargar.core.models import TenantAwareModel
import json
import uuid


class NotificationTemplate(TenantAwareModel):
    """
    Persian notification templates for different types of notifications.
    """
    TEMPLATE_TYPES = [
        ('payment_reminder', _('Payment Reminder')),
        ('payment_overdue', _('Payment Overdue')),
        ('payment_confirmation', _('Payment Confirmation')),
        ('appointment_reminder', _('Appointment Reminder')),
        ('birthday_greeting', _('Birthday Greeting')),
        ('anniversary_greeting', _('Anniversary Greeting')),
        ('special_offer', _('Special Offer')),
        ('contract_expiry', _('Contract Expiry')),
        ('welcome_message', _('Welcome Message')),
        ('custom', _('Custom Template')),
    ]
    
    DELIVERY_METHODS = [
        ('sms', _('SMS')),
        ('email', _('Email')),
        ('push', _('Push Notification')),
        ('whatsapp', _('WhatsApp')),
    ]
    
    # Template identification
    name = models.CharField(
        max_length=200,
        verbose_name=_('Template Name')
    )
    template_type = models.CharField(
        max_length=30,
        choices=TEMPLATE_TYPES,
        verbose_name=_('Template Type')
    )
    
    # Template content
    title = models.CharField(
        max_length=200,
        verbose_name=_('Message Title'),
        help_text=_('Title for email/push notifications')
    )
    content = models.TextField(
        verbose_name=_('Message Content'),
        help_text=_('Persian message template with variables: {customer_name}, {amount}, {date}, etc.')
    )
    
    # Delivery settings
    delivery_methods = models.JSONField(
        default=list,
        verbose_name=_('Delivery Methods'),
        help_text=_('List of delivery methods: sms, email, push, whatsapp')
    )
    
    # Template variables
    available_variables = models.JSONField(
        default=dict,
        verbose_name=_('Available Variables'),
        help_text=_('Dictionary of available template variables and their descriptions')
    )
    
    # Status and settings
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name=_('Is Default Template'),
        help_text=_('Default template for this type')
    )
    
    # Usage statistics
    usage_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Usage Count')
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last Used At')
    )
    
    class Meta:
        verbose_name = _('Notification Template')
        verbose_name_plural = _('Notification Templates')
        unique_together = ['template_type', 'is_default']
        indexes = [
            models.Index(fields=['template_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_default']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
    
    def save(self, *args, **kwargs):
        """Ensure only one default template per type."""
        if self.is_default:
            # Remove default flag from other templates of same type
            NotificationTemplate.objects.filter(
                template_type=self.template_type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        
        super().save(*args, **kwargs)
    
    def render_content(self, context):
        """
        Render template content with provided context variables.
        
        Args:
            context (dict): Variables to substitute in template
            
        Returns:
            dict: Rendered title and content
        """
        rendered_title = self.title
        rendered_content = self.content
        
        # Replace variables in title and content
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            rendered_title = rendered_title.replace(placeholder, str(value))
            rendered_content = rendered_content.replace(placeholder, str(value))
        
        return {
            'title': rendered_title,
            'content': rendered_content
        }
    
    def increment_usage(self):
        """Increment usage count and update last used timestamp."""
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])
    
    @classmethod
    def get_default_template(cls, template_type):
        """Get default template for a specific type."""
        try:
            return cls.objects.get(template_type=template_type, is_default=True, is_active=True)
        except cls.DoesNotExist:
            # Return first active template of this type
            return cls.objects.filter(template_type=template_type, is_active=True).first()


class NotificationSchedule(TenantAwareModel):
    """
    Scheduled notifications for automated delivery.
    """
    SCHEDULE_TYPES = [
        ('one_time', _('One Time')),
        ('recurring', _('Recurring')),
        ('conditional', _('Conditional')),
    ]
    
    RECURRENCE_PATTERNS = [
        ('daily', _('Daily')),
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
        ('quarterly', _('Quarterly')),
        ('yearly', _('Yearly')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('paused', _('Paused')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    ]
    
    # Schedule identification
    name = models.CharField(
        max_length=200,
        verbose_name=_('Schedule Name')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    
    # Template and targeting
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name=_('Notification Template')
    )
    
    # Schedule settings
    schedule_type = models.CharField(
        max_length=20,
        choices=SCHEDULE_TYPES,
        default='one_time',
        verbose_name=_('Schedule Type')
    )
    
    # Timing
    start_date = models.DateTimeField(
        verbose_name=_('Start Date')
    )
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('End Date')
    )
    
    # Recurrence settings
    recurrence_pattern = models.CharField(
        max_length=20,
        choices=RECURRENCE_PATTERNS,
        blank=True,
        verbose_name=_('Recurrence Pattern')
    )
    recurrence_interval = models.PositiveIntegerField(
        default=1,
        verbose_name=_('Recurrence Interval'),
        help_text=_('Every X days/weeks/months')
    )
    
    # Targeting criteria
    target_criteria = models.JSONField(
        default=dict,
        verbose_name=_('Target Criteria'),
        help_text=_('JSON criteria for selecting recipients')
    )
    
    # Delivery settings
    delivery_methods = models.JSONField(
        default=list,
        verbose_name=_('Delivery Methods')
    )
    
    # Status and statistics
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name=_('Status')
    )
    
    total_sent = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total Sent')
    )
    total_delivered = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total Delivered')
    )
    total_failed = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total Failed')
    )
    
    last_run_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last Run At')
    )
    next_run_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Next Run At')
    )
    
    class Meta:
        verbose_name = _('Notification Schedule')
        verbose_name_plural = _('Notification Schedules')
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['next_run_at']),
            models.Index(fields=['schedule_type']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.template.name}"
    
    def calculate_next_run(self):
        """Calculate next run time based on recurrence pattern."""
        if self.schedule_type != 'recurring' or not self.recurrence_pattern:
            return None
        
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        base_time = self.last_run_at or self.start_date
        
        if self.recurrence_pattern == 'daily':
            return base_time + timedelta(days=self.recurrence_interval)
        elif self.recurrence_pattern == 'weekly':
            return base_time + timedelta(weeks=self.recurrence_interval)
        elif self.recurrence_pattern == 'monthly':
            return base_time + relativedelta(months=self.recurrence_interval)
        elif self.recurrence_pattern == 'quarterly':
            return base_time + relativedelta(months=3 * self.recurrence_interval)
        elif self.recurrence_pattern == 'yearly':
            return base_time + relativedelta(years=self.recurrence_interval)
        
        return None
    
    def update_statistics(self, sent=0, delivered=0, failed=0):
        """Update delivery statistics."""
        self.total_sent += sent
        self.total_delivered += delivered
        self.total_failed += failed
        self.last_run_at = timezone.now()
        
        # Calculate next run time
        if self.schedule_type == 'recurring':
            self.next_run_at = self.calculate_next_run()
        elif self.schedule_type == 'one_time':
            self.status = 'completed'
        
        self.save(update_fields=[
            'total_sent', 'total_delivered', 'total_failed',
            'last_run_at', 'next_run_at', 'status'
        ])


class Notification(TenantAwareModel):
    """
    Individual notification records for tracking delivery status.
    """
    DELIVERY_METHODS = [
        ('sms', _('SMS')),
        ('email', _('Email')),
        ('push', _('Push Notification')),
        ('whatsapp', _('WhatsApp')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('queued', _('Queued')),
        ('sending', _('Sending')),
        ('sent', _('Sent')),
        ('delivered', _('Delivered')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]
    
    PRIORITY_LEVELS = [
        ('low', _('Low')),
        ('normal', _('Normal')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    ]
    
    # Notification identification
    notification_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        verbose_name=_('Notification ID')
    )
    
    # Template and content
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name=_('Template Used')
    )
    schedule = models.ForeignKey(
        NotificationSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name=_('Schedule')
    )
    
    # Recipient information
    recipient_type = models.CharField(
        max_length=20,
        default='customer',
        verbose_name=_('Recipient Type'),
        help_text=_('customer, user, supplier, etc.')
    )
    recipient_id = models.PositiveIntegerField(
        verbose_name=_('Recipient ID')
    )
    recipient_name = models.CharField(
        max_length=200,
        verbose_name=_('Recipient Name')
    )
    recipient_phone = models.CharField(
        max_length=15,
        blank=True,
        verbose_name=_('Recipient Phone')
    )
    recipient_email = models.EmailField(
        blank=True,
        verbose_name=_('Recipient Email')
    )
    
    # Message content
    title = models.CharField(
        max_length=200,
        verbose_name=_('Message Title')
    )
    content = models.TextField(
        verbose_name=_('Message Content')
    )
    
    # Delivery settings
    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_METHODS,
        verbose_name=_('Delivery Method')
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_LEVELS,
        default='normal',
        verbose_name=_('Priority')
    )
    
    # Scheduling
    scheduled_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Scheduled At')
    )
    send_after = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Send After'),
        help_text=_('Do not send before this time')
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Expires At'),
        help_text=_('Do not send after this time')
    )
    
    # Status and tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Status')
    )
    
    # Delivery tracking
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Sent At')
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Delivered At')
    )
    failed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Failed At')
    )
    
    # Error handling
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Error Message')
    )
    retry_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Retry Count')
    )
    max_retries = models.PositiveIntegerField(
        default=3,
        verbose_name=_('Max Retries')
    )
    
    # Provider response
    provider_response = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Provider Response'),
        help_text=_('Response from SMS/Email provider')
    )
    provider_message_id = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Provider Message ID')
    )
    
    # Context data
    context_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Context Data'),
        help_text=_('Additional data used for template rendering')
    )
    
    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['delivery_method']),
            models.Index(fields=['scheduled_at']),
            models.Index(fields=['recipient_type', 'recipient_id']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return f"{self.title} -> {self.recipient_name} ({self.delivery_method})"
    
    @property
    def is_expired(self):
        """Check if notification has expired."""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def can_retry(self):
        """Check if notification can be retried."""
        return (self.status == 'failed' and 
                self.retry_count < self.max_retries and 
                not self.is_expired)
    
    @property
    def is_ready_to_send(self):
        """Check if notification is ready to be sent."""
        now = timezone.now()
        
        # Check basic conditions
        if self.status not in ['pending', 'queued']:
            return False
        
        if self.is_expired:
            return False
        
        # Check send_after constraint
        if self.send_after and now < self.send_after:
            return False
        
        # Check if scheduled time has arrived
        if now < self.scheduled_at:
            return False
        
        return True
    
    def mark_as_sent(self, provider_message_id=None, provider_response=None):
        """Mark notification as sent."""
        self.status = 'sent'
        self.sent_at = timezone.now()
        
        if provider_message_id:
            self.provider_message_id = provider_message_id
        
        if provider_response:
            self.provider_response = provider_response
        
        self.save(update_fields=[
            'status', 'sent_at', 'provider_message_id', 'provider_response'
        ])
    
    def mark_as_delivered(self, delivered_at=None):
        """Mark notification as delivered."""
        self.status = 'delivered'
        self.delivered_at = delivered_at or timezone.now()
        
        self.save(update_fields=['status', 'delivered_at'])
    
    def mark_as_failed(self, error_message, can_retry=True):
        """Mark notification as failed."""
        self.status = 'failed'
        self.failed_at = timezone.now()
        self.error_message = error_message
        
        if can_retry and self.can_retry:
            self.retry_count += 1
            # Reschedule for retry (exponential backoff)
            retry_delay = 2 ** self.retry_count  # 2, 4, 8 minutes
            self.scheduled_at = timezone.now() + timezone.timedelta(minutes=retry_delay)
            self.status = 'pending'  # Reset to pending for retry
        
        self.save(update_fields=[
            'status', 'failed_at', 'error_message', 'retry_count', 'scheduled_at'
        ])
    
    def cancel(self, reason=""):
        """Cancel the notification."""
        self.status = 'cancelled'
        if reason:
            self.error_message = f"Cancelled: {reason}"
        
        self.save(update_fields=['status', 'error_message'])


class NotificationDeliveryLog(TenantAwareModel):
    """
    Detailed delivery logs for notifications.
    """
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='delivery_logs',
        verbose_name=_('Notification')
    )
    
    # Log details
    action = models.CharField(
        max_length=50,
        verbose_name=_('Action'),
        help_text=_('queued, sent, delivered, failed, etc.')
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Timestamp')
    )
    
    # Provider details
    provider_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Provider Name')
    )
    provider_response = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Provider Response')
    )
    
    # Status and error information
    success = models.BooleanField(
        default=True,
        verbose_name=_('Success')
    )
    error_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Error Code')
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Error Message')
    )
    
    # Additional metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Metadata')
    )
    
    class Meta:
        verbose_name = _('Notification Delivery Log')
        verbose_name_plural = _('Notification Delivery Logs')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['notification']),
            models.Index(fields=['action']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['success']),
        ]
    
    def __str__(self):
        return f"{self.notification.title} - {self.action} at {self.timestamp}"


class NotificationProvider(TenantAwareModel):
    """
    Configuration for notification delivery providers (SMS, Email, etc.).
    """
    PROVIDER_TYPES = [
        ('sms', _('SMS Provider')),
        ('email', _('Email Provider')),
        ('push', _('Push Notification Provider')),
        ('whatsapp', _('WhatsApp Provider')),
    ]
    
    # Provider identification
    name = models.CharField(
        max_length=100,
        verbose_name=_('Provider Name')
    )
    provider_type = models.CharField(
        max_length=20,
        choices=PROVIDER_TYPES,
        verbose_name=_('Provider Type')
    )
    
    # Configuration
    api_endpoint = models.URLField(
        blank=True,
        verbose_name=_('API Endpoint')
    )
    api_key = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('API Key')
    )
    api_secret = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('API Secret')
    )
    
    # Additional settings
    settings = models.JSONField(
        default=dict,
        verbose_name=_('Provider Settings'),
        help_text=_('Additional provider-specific settings')
    )
    
    # Status and limits
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name=_('Is Default Provider')
    )
    
    # Rate limiting
    rate_limit_per_minute = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Rate Limit Per Minute')
    )
    rate_limit_per_hour = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Rate Limit Per Hour')
    )
    rate_limit_per_day = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Rate Limit Per Day')
    )
    
    # Usage statistics
    total_sent = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total Sent')
    )
    total_delivered = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total Delivered')
    )
    total_failed = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total Failed')
    )
    
    # Cost tracking
    cost_per_message = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name=_('Cost Per Message (Toman)')
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Total Cost (Toman)')
    )
    
    class Meta:
        verbose_name = _('Notification Provider')
        verbose_name_plural = _('Notification Providers')
        unique_together = ['provider_type', 'is_default']
        indexes = [
            models.Index(fields=['provider_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_default']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_provider_type_display()})"
    
    def save(self, *args, **kwargs):
        """Ensure only one default provider per type."""
        if self.is_default:
            # Remove default flag from other providers of same type
            NotificationProvider.objects.filter(
                provider_type=self.provider_type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        
        super().save(*args, **kwargs)
    
    def update_statistics(self, sent=0, delivered=0, failed=0, cost=0):
        """Update provider statistics."""
        self.total_sent += sent
        self.total_delivered += delivered
        self.total_failed += failed
        self.total_cost += cost
        
        self.save(update_fields=[
            'total_sent', 'total_delivered', 'total_failed', 'total_cost'
        ])
    
    @property
    def success_rate(self):
        """Calculate delivery success rate."""
        if self.total_sent == 0:
            return 0
        return (self.total_delivered / self.total_sent) * 100
    
    @classmethod
    def get_default_provider(cls, provider_type):
        """Get default provider for a specific type."""
        try:
            return cls.objects.get(
                provider_type=provider_type, 
                is_default=True, 
                is_active=True
            )
        except cls.DoesNotExist:
            # Return first active provider of this type
            return cls.objects.filter(
                provider_type=provider_type, 
                is_active=True
            ).first()


class MobileDevice(TenantAwareModel):
    """
    Mobile device registration for push notifications.
    """
    DEVICE_TYPES = [
        ('android', _('Android')),
        ('ios', _('iOS')),
    ]
    
    # Device identification
    user = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='mobile_devices',
        verbose_name=_('User')
    )
    device_id = models.CharField(
        max_length=100,
        verbose_name=_('Device ID'),
        help_text=_('Unique device identifier')
    )
    device_token = models.CharField(
        max_length=500,
        verbose_name=_('Device Token'),
        help_text=_('Push notification token')
    )
    
    # Device information
    device_type = models.CharField(
        max_length=20,
        choices=DEVICE_TYPES,
        default='android',
        verbose_name=_('Device Type')
    )
    device_model = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Device Model')
    )
    os_version = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('OS Version')
    )
    app_version = models.CharField(
        max_length=20,
        verbose_name=_('App Version')
    )
    
    # Localization settings
    timezone = models.CharField(
        max_length=50,
        default='Asia/Tehran',
        verbose_name=_('Timezone')
    )
    language = models.CharField(
        max_length=10,
        default='fa',
        verbose_name=_('Language')
    )
    
    # Notification preferences
    enable_push_notifications = models.BooleanField(
        default=True,
        verbose_name=_('Enable Push Notifications')
    )
    enable_payment_reminders = models.BooleanField(
        default=True,
        verbose_name=_('Enable Payment Reminders')
    )
    enable_appointment_reminders = models.BooleanField(
        default=True,
        verbose_name=_('Enable Appointment Reminders')
    )
    enable_promotions = models.BooleanField(
        default=False,
        verbose_name=_('Enable Promotions')
    )
    enable_system_notifications = models.BooleanField(
        default=True,
        verbose_name=_('Enable System Notifications')
    )
    
    # Status and tracking
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    last_active_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Last Active At')
    )
    registered_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Registered At')
    )
    unregistered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Unregistered At')
    )
    
    # Statistics
    notifications_sent = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Notifications Sent')
    )
    notifications_delivered = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Notifications Delivered')
    )
    notifications_failed = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Notifications Failed')
    )
    
    class Meta:
        verbose_name = _('Mobile Device')
        verbose_name_plural = _('Mobile Devices')
        unique_together = ['user', 'device_id']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['device_id']),
            models.Index(fields=['device_token']),
            models.Index(fields=['is_active']),
            models.Index(fields=['last_active_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.device_model} ({self.device_type})"
    
    def update_activity(self):
        """Update last active timestamp."""
        self.last_active_at = timezone.now()
        self.save(update_fields=['last_active_at'])
    
    def update_notification_stats(self, sent=0, delivered=0, failed=0):
        """Update notification statistics."""
        self.notifications_sent += sent
        self.notifications_delivered += delivered
        self.notifications_failed += failed
        
        self.save(update_fields=[
            'notifications_sent', 'notifications_delivered', 'notifications_failed'
        ])
    
    @property
    def notification_success_rate(self):
        """Calculate notification delivery success rate."""
        if self.notifications_sent == 0:
            return 0
        return (self.notifications_delivered / self.notifications_sent) * 100
    
    def can_receive_notification(self, notification_type):
        """Check if device can receive specific type of notification."""
        if not self.is_active or not self.enable_push_notifications:
            return False
        
        type_mapping = {
            'payment_reminder': self.enable_payment_reminders,
            'appointment_reminder': self.enable_appointment_reminders,
            'special_offer': self.enable_promotions,
            'system': self.enable_system_notifications,
        }
        
        return type_mapping.get(notification_type, True)