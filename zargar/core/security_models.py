"""
Security and audit logging models for zargar project.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.cache import cache
from django.conf import settings
import json
import hashlib
from .models import TenantAwareModel, User


class SecurityEvent(TenantAwareModel):
    """
    Model for tracking security-related events and suspicious activities.
    """
    EVENT_TYPES = [
        ('login_success', _('Successful Login')),
        ('login_failed', _('Failed Login')),
        ('login_blocked', _('Login Blocked (Rate Limited)')),
        ('logout', _('Logout')),
        ('password_change', _('Password Change')),
        ('password_reset_request', _('Password Reset Request')),
        ('password_reset_complete', _('Password Reset Complete')),
        ('2fa_enabled', _('2FA Enabled')),
        ('2fa_disabled', _('2FA Disabled')),
        ('2fa_success', _('2FA Verification Success')),
        ('2fa_failed', _('2FA Verification Failed')),
        ('2fa_backup_used', _('2FA Backup Token Used')),
        ('account_locked', _('Account Locked')),
        ('account_unlocked', _('Account Unlocked')),
        ('suspicious_activity', _('Suspicious Activity Detected')),
        ('brute_force_attempt', _('Brute Force Attack Attempt')),
        ('unauthorized_access', _('Unauthorized Access Attempt')),
        ('privilege_escalation', _('Privilege Escalation Attempt')),
        ('data_export', _('Data Export')),
        ('bulk_operation', _('Bulk Operation')),
        ('admin_impersonation', _('Admin Impersonation')),
        ('api_rate_limit', _('API Rate Limit Exceeded')),
        ('csrf_failure', _('CSRF Token Failure')),
        ('session_hijack', _('Potential Session Hijacking')),
    ]
    
    SEVERITY_LEVELS = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
        verbose_name=_('Event Type')
    )
    
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_LEVELS,
        default='medium',
        verbose_name=_('Severity Level')
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_events',
        verbose_name=_('User')
    )
    
    username_attempted = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Username Attempted'),
        help_text=_('Username used in failed login attempts')
    )
    
    ip_address = models.GenericIPAddressField(
        verbose_name=_('IP Address')
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )
    
    session_key = models.CharField(
        max_length=40,
        blank=True,
        verbose_name=_('Session Key')
    )
    
    request_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Request Path')
    )
    
    request_method = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Request Method')
    )
    
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Event Details'),
        help_text=_('Additional details about the security event')
    )
    
    is_resolved = models.BooleanField(
        default=False,
        verbose_name=_('Is Resolved'),
        help_text=_('Whether this security event has been investigated and resolved')
    )
    
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_security_events',
        verbose_name=_('Resolved By')
    )
    
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Resolved At')
    )
    
    resolution_notes = models.TextField(
        blank=True,
        verbose_name=_('Resolution Notes')
    )
    
    class Meta:
        verbose_name = _('Security Event')
        verbose_name_plural = _('Security Events')
        db_table = 'core_security_event'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['user', 'event_type']),
            models.Index(fields=['severity', 'is_resolved']),
        ]
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.ip_address} - {self.created_at}"
    
    @classmethod
    def log_event(cls, event_type, request=None, user=None, username_attempted=None, 
                  severity='medium', details=None, **kwargs):
        """
        Convenience method to log security events.
        
        Args:
            event_type (str): Type of security event
            request (HttpRequest, optional): Django request object
            user (User, optional): User associated with the event
            username_attempted (str, optional): Username for failed login attempts
            severity (str): Severity level of the event
            details (dict, optional): Additional event details
            **kwargs: Additional fields to set on the event
        
        Returns:
            SecurityEvent: Created security event instance
        """
        event_data = {
            'event_type': event_type,
            'severity': severity,
            'user': user,
            'username_attempted': username_attempted or '',
            'details': details or {},
        }
        
        if request:
            event_data.update({
                'ip_address': cls._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'session_key': request.session.session_key or '',
                'request_path': request.path,
                'request_method': request.method,
            })
        
        # Add any additional kwargs
        event_data.update(kwargs)
        
        return cls.objects.create(**event_data)
    
    @staticmethod
    def _get_client_ip(request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def resolve(self, resolved_by, notes=''):
        """Mark this security event as resolved."""
        self.is_resolved = True
        self.resolved_by = resolved_by
        self.resolved_at = timezone.now()
        self.resolution_notes = notes
        self.save(update_fields=['is_resolved', 'resolved_by', 'resolved_at', 'resolution_notes'])
    
    def get_risk_score(self):
        """Calculate risk score based on event type and context."""
        base_scores = {
            'login_failed': 2,
            'login_blocked': 5,
            'brute_force_attempt': 8,
            'unauthorized_access': 7,
            'privilege_escalation': 9,
            'suspicious_activity': 6,
            'session_hijack': 8,
            'admin_impersonation': 5,
            'data_export': 4,
            'bulk_operation': 3,
        }
        
        score = base_scores.get(self.event_type, 1)
        
        # Adjust based on severity
        severity_multipliers = {
            'low': 0.5,
            'medium': 1.0,
            'high': 1.5,
            'critical': 2.0,
        }
        
        score *= severity_multipliers.get(self.severity, 1.0)
        
        return min(score, 10)  # Cap at 10


class AuditLog(TenantAwareModel):
    """
    Comprehensive audit log for tracking all user actions and system events.
    """
    ACTION_TYPES = [
        # CRUD Operations
        ('create', _('Create')),
        ('read', _('Read')),
        ('update', _('Update')),
        ('delete', _('Delete')),
        ('bulk_create', _('Bulk Create')),
        ('bulk_update', _('Bulk Update')),
        ('bulk_delete', _('Bulk Delete')),
        
        # Authentication
        ('login', _('Login')),
        ('logout', _('Logout')),
        ('password_change', _('Password Change')),
        ('password_reset', _('Password Reset')),
        
        # 2FA Operations
        ('2fa_setup', _('2FA Setup')),
        ('2fa_enable', _('2FA Enable')),
        ('2fa_disable', _('2FA Disable')),
        ('2fa_verify', _('2FA Verify')),
        ('backup_token_generate', _('Backup Token Generate')),
        ('backup_token_use', _('Backup Token Use')),
        
        # Admin Operations
        ('tenant_create', _('Tenant Create')),
        ('tenant_update', _('Tenant Update')),
        ('tenant_suspend', _('Tenant Suspend')),
        ('tenant_activate', _('Tenant Activate')),
        ('user_impersonate', _('User Impersonate')),
        ('impersonation_end', _('Impersonation End')),
        
        # Business Operations
        ('sale_create', _('Sale Create')),
        ('payment_process', _('Payment Process')),
        ('inventory_update', _('Inventory Update')),
        ('report_generate', _('Report Generate')),
        ('data_export', _('Data Export')),
        ('data_import', _('Data Import')),
        
        # System Operations
        ('backup_create', _('Backup Create')),
        ('backup_restore', _('Backup Restore')),
        ('system_maintenance', _('System Maintenance')),
        ('configuration_change', _('Configuration Change')),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name=_('User')
    )
    
    action = models.CharField(
        max_length=50,
        choices=ACTION_TYPES,
        verbose_name=_('Action')
    )
    
    # Generic foreign key to track any model
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Content Type')
    )
    object_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Object ID')
    )
    content_object = GenericForeignKey('content_type', 'object_id')
    
    model_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Model Name')
    )
    
    object_repr = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Object Representation')
    )
    
    # Change tracking
    changes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Changes'),
        help_text=_('JSON representation of field changes')
    )
    
    old_values = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Old Values'),
        help_text=_('Previous values before change')
    )
    
    new_values = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('New Values'),
        help_text=_('New values after change')
    )
    
    # Request context
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP Address')
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )
    
    session_key = models.CharField(
        max_length=40,
        blank=True,
        verbose_name=_('Session Key')
    )
    
    request_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Request Path')
    )
    
    request_method = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Request Method')
    )
    
    # Additional metadata
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Additional Details')
    )
    
    tenant_schema = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Tenant Schema')
    )
    
    # Integrity protection
    checksum = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_('Integrity Checksum'),
        help_text=_('SHA-256 checksum for tamper detection')
    )
    
    class Meta:
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        db_table = 'core_audit_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'action', 'created_at']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['tenant_schema', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.get_action_display()} - {self.created_at}"
    
    def save(self, *args, **kwargs):
        """Override save to generate integrity checksum."""
        if not self.checksum:
            self.checksum = self._generate_checksum()
        super().save(*args, **kwargs)
    
    def _generate_checksum(self):
        """Generate SHA-256 checksum for integrity verification."""
        data = {
            'user_id': self.user.id if self.user else None,
            'action': self.action,
            'model_name': self.model_name,
            'object_id': self.object_id,
            'changes': self.changes,
            'ip_address': str(self.ip_address) if self.ip_address else '',
            'timestamp': self.created_at.isoformat() if self.created_at else timezone.now().isoformat(),
        }
        
        data_string = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def verify_integrity(self):
        """Verify the integrity of this audit log entry."""
        expected_checksum = self._generate_checksum()
        return self.checksum == expected_checksum
    
    @classmethod
    def log_action(cls, action, user=None, content_object=None, request=None, 
                   changes=None, old_values=None, new_values=None, details=None, **kwargs):
        """
        Convenience method to create audit log entries.
        
        Args:
            action (str): Action being performed
            user (User, optional): User performing the action
            content_object (Model, optional): Object being acted upon
            request (HttpRequest, optional): Django request object
            changes (dict, optional): Field changes
            old_values (dict, optional): Previous values
            new_values (dict, optional): New values
            details (dict, optional): Additional details
            **kwargs: Additional fields to set
        
        Returns:
            AuditLog: Created audit log entry
        """
        log_data = {
            'action': action,
            'user': user,
            'changes': changes or {},
            'old_values': old_values or {},
            'new_values': new_values or {},
            'details': details or {},
        }
        
        # Set content object information
        if content_object:
            log_data.update({
                'content_object': content_object,
                'model_name': content_object._meta.model_name,
                'object_repr': str(content_object),
            })
        
        # Set request context
        if request:
            log_data.update({
                'ip_address': cls._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'session_key': request.session.session_key or '',
                'request_path': request.path,
                'request_method': request.method,
            })
        
        # Set tenant schema
        from .models import get_current_tenant
        current_tenant = get_current_tenant()
        if current_tenant:
            log_data['tenant_schema'] = current_tenant.schema_name
        
        # Add any additional kwargs
        log_data.update(kwargs)
        
        return cls.objects.create(**log_data)
    
    @staticmethod
    def _get_client_ip(request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip


class RateLimitAttempt(models.Model):
    """
    Model to track rate limiting attempts for various endpoints and actions.
    """
    LIMIT_TYPES = [
        ('login', _('Login Attempts')),
        ('api_call', _('API Call')),
        ('password_reset', _('Password Reset')),
        ('2fa_verify', _('2FA Verification')),
        ('data_export', _('Data Export')),
        ('bulk_operation', _('Bulk Operation')),
        ('search', _('Search Query')),
        ('report_generation', _('Report Generation')),
    ]
    
    identifier = models.CharField(
        max_length=200,
        verbose_name=_('Identifier'),
        help_text=_('IP address, user ID, or other identifier')
    )
    
    limit_type = models.CharField(
        max_length=50,
        choices=LIMIT_TYPES,
        verbose_name=_('Limit Type')
    )
    
    endpoint = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Endpoint'),
        help_text=_('API endpoint or view name')
    )
    
    attempts = models.PositiveIntegerField(
        default=1,
        verbose_name=_('Attempts')
    )
    
    window_start = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Window Start')
    )
    
    last_attempt = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Last Attempt')
    )
    
    is_blocked = models.BooleanField(
        default=False,
        verbose_name=_('Is Blocked')
    )
    
    blocked_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Blocked Until')
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )
    
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Details')
    )
    
    class Meta:
        verbose_name = _('Rate Limit Attempt')
        verbose_name_plural = _('Rate Limit Attempts')
        db_table = 'core_rate_limit_attempt'
        unique_together = ['identifier', 'limit_type', 'endpoint']
        indexes = [
            models.Index(fields=['identifier', 'limit_type']),
            models.Index(fields=['window_start', 'last_attempt']),
            models.Index(fields=['is_blocked', 'blocked_until']),
        ]
    
    def __str__(self):
        return f"{self.identifier} - {self.get_limit_type_display()} - {self.attempts} attempts"
    
    @classmethod
    def record_attempt(cls, identifier, limit_type, endpoint='', user_agent='', details=None):
        """
        Record a rate limit attempt.
        
        Args:
            identifier (str): Unique identifier (IP, user ID, etc.)
            limit_type (str): Type of rate limit
            endpoint (str): Endpoint being accessed
            user_agent (str): User agent string
            details (dict): Additional details
        
        Returns:
            tuple: (RateLimitAttempt instance, is_blocked)
        """
        now = timezone.now()
        
        # Get or create rate limit record
        attempt, created = cls.objects.get_or_create(
            identifier=identifier,
            limit_type=limit_type,
            endpoint=endpoint,
            defaults={
                'attempts': 1,
                'user_agent': user_agent,
                'details': details or {},
            }
        )
        
        if not created:
            # Check if we're in a new time window (1 hour)
            if now - attempt.window_start > timezone.timedelta(hours=1):
                # Reset counter for new window
                attempt.attempts = 1
                attempt.window_start = now
                attempt.is_blocked = False
                attempt.blocked_until = None
            else:
                # Increment attempts in current window
                attempt.attempts += 1
            
            attempt.user_agent = user_agent
            attempt.details.update(details or {})
            attempt.save()
        
        # Check if should be blocked
        is_blocked = attempt.should_be_blocked()
        if is_blocked and not attempt.is_blocked:
            attempt.block()
        
        return attempt, is_blocked
    
    def should_be_blocked(self):
        """Check if this identifier should be blocked based on attempts."""
        limits = {
            'login': 5,  # 5 failed login attempts per hour
            'api_call': 1000,  # 1000 API calls per hour
            'password_reset': 3,  # 3 password reset attempts per hour
            '2fa_verify': 10,  # 10 2FA verification attempts per hour
            'data_export': 10,  # 10 data exports per hour
            'bulk_operation': 5,  # 5 bulk operations per hour
            'search': 100,  # 100 search queries per hour
            'report_generation': 20,  # 20 report generations per hour
        }
        
        limit = limits.get(self.limit_type, 100)
        return self.attempts >= limit
    
    def block(self, duration_hours=1):
        """Block this identifier for specified duration."""
        self.is_blocked = True
        self.blocked_until = timezone.now() + timezone.timedelta(hours=duration_hours)
        self.save(update_fields=['is_blocked', 'blocked_until'])
        
        # Log security event
        SecurityEvent.log_event(
            event_type='login_blocked' if self.limit_type == 'login' else 'api_rate_limit',
            severity='high' if self.limit_type == 'login' else 'medium',
            details={
                'identifier': self.identifier,
                'limit_type': self.limit_type,
                'attempts': self.attempts,
                'blocked_until': self.blocked_until.isoformat(),
            }
        )
    
    def is_currently_blocked(self):
        """Check if this identifier is currently blocked."""
        if not self.is_blocked:
            return False
        
        if self.blocked_until and timezone.now() > self.blocked_until:
            # Block has expired, unblock
            self.is_blocked = False
            self.blocked_until = None
            self.save(update_fields=['is_blocked', 'blocked_until'])
            return False
        
        return True


class SuspiciousActivity(TenantAwareModel):
    """
    Model to track patterns of suspicious activity for advanced threat detection.
    """
    ACTIVITY_TYPES = [
        ('multiple_failed_logins', _('Multiple Failed Logins')),
        ('unusual_access_pattern', _('Unusual Access Pattern')),
        ('privilege_escalation', _('Privilege Escalation Attempt')),
        ('data_scraping', _('Data Scraping')),
        ('session_anomaly', _('Session Anomaly')),
        ('geographic_anomaly', _('Geographic Anomaly')),
        ('time_anomaly', _('Time-based Anomaly')),
        ('bulk_data_access', _('Bulk Data Access')),
        ('unauthorized_api_usage', _('Unauthorized API Usage')),
        ('suspicious_user_agent', _('Suspicious User Agent')),
    ]
    
    RISK_LEVELS = [
        ('low', _('Low Risk')),
        ('medium', _('Medium Risk')),
        ('high', _('High Risk')),
        ('critical', _('Critical Risk')),
    ]
    
    activity_type = models.CharField(
        max_length=50,
        choices=ACTIVITY_TYPES,
        verbose_name=_('Activity Type')
    )
    
    risk_level = models.CharField(
        max_length=20,
        choices=RISK_LEVELS,
        default='medium',
        verbose_name=_('Risk Level')
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suspicious_activities',
        verbose_name=_('User')
    )
    
    ip_address = models.GenericIPAddressField(
        verbose_name=_('IP Address')
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )
    
    session_key = models.CharField(
        max_length=40,
        blank=True,
        verbose_name=_('Session Key')
    )
    
    # Pattern detection data
    pattern_data = models.JSONField(
        default=dict,
        verbose_name=_('Pattern Data'),
        help_text=_('Data used for pattern detection and analysis')
    )
    
    confidence_score = models.FloatField(
        default=0.0,
        verbose_name=_('Confidence Score'),
        help_text=_('Confidence score (0.0 to 1.0) for this suspicious activity detection')
    )
    
    # Investigation status
    is_investigated = models.BooleanField(
        default=False,
        verbose_name=_('Is Investigated')
    )
    
    investigated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='investigated_activities',
        verbose_name=_('Investigated By')
    )
    
    investigated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Investigated At')
    )
    
    investigation_notes = models.TextField(
        blank=True,
        verbose_name=_('Investigation Notes')
    )
    
    is_false_positive = models.BooleanField(
        default=False,
        verbose_name=_('Is False Positive')
    )
    
    # Related security events
    related_events = models.ManyToManyField(
        SecurityEvent,
        blank=True,
        related_name='suspicious_activities',
        verbose_name=_('Related Security Events')
    )
    
    class Meta:
        verbose_name = _('Suspicious Activity')
        verbose_name_plural = _('Suspicious Activities')
        db_table = 'core_suspicious_activity'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['activity_type', 'risk_level']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['is_investigated', 'risk_level']),
        ]
    
    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.ip_address} - {self.get_risk_level_display()}"
    
    @classmethod
    def detect_and_create(cls, activity_type, user=None, ip_address=None, user_agent='', 
                         session_key='', pattern_data=None, confidence_score=0.0, **kwargs):
        """
        Detect and create suspicious activity record.
        
        Args:
            activity_type (str): Type of suspicious activity
            user (User, optional): User associated with the activity
            ip_address (str): IP address
            user_agent (str): User agent string
            session_key (str): Session key
            pattern_data (dict): Pattern detection data
            confidence_score (float): Confidence score (0.0 to 1.0)
            **kwargs: Additional fields
        
        Returns:
            SuspiciousActivity: Created suspicious activity instance
        """
        # Determine risk level based on activity type and confidence
        risk_level = cls._calculate_risk_level(activity_type, confidence_score)
        
        activity = cls.objects.create(
            activity_type=activity_type,
            risk_level=risk_level,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            session_key=session_key,
            pattern_data=pattern_data or {},
            confidence_score=confidence_score,
            **kwargs
        )
        
        # Create related security event
        SecurityEvent.log_event(
            event_type='suspicious_activity',
            user=user,
            severity=risk_level,
            ip_address=ip_address,
            user_agent=user_agent,
            session_key=session_key,
            details={
                'activity_type': activity_type,
                'confidence_score': confidence_score,
                'pattern_data': pattern_data or {},
                'suspicious_activity_id': activity.id,
            }
        )
        
        return activity
    
    @staticmethod
    def _calculate_risk_level(activity_type, confidence_score):
        """Calculate risk level based on activity type and confidence score."""
        base_risk = {
            'multiple_failed_logins': 'medium',
            'unusual_access_pattern': 'low',
            'privilege_escalation': 'critical',
            'data_scraping': 'high',
            'session_anomaly': 'medium',
            'geographic_anomaly': 'medium',
            'time_anomaly': 'low',
            'bulk_data_access': 'high',
            'unauthorized_api_usage': 'high',
            'suspicious_user_agent': 'low',
        }
        
        risk = base_risk.get(activity_type, 'medium')
        
        # Adjust based on confidence score
        if confidence_score >= 0.9:
            if risk == 'low':
                risk = 'medium'
            elif risk == 'medium':
                risk = 'high'
            elif risk == 'high':
                risk = 'critical'
        elif confidence_score <= 0.3:
            if risk == 'critical':
                risk = 'high'
            elif risk == 'high':
                risk = 'medium'
            elif risk == 'medium':
                risk = 'low'
        
        return risk
    
    def investigate(self, investigated_by, notes='', is_false_positive=False):
        """Mark this suspicious activity as investigated."""
        self.is_investigated = True
        self.investigated_by = investigated_by
        self.investigated_at = timezone.now()
        self.investigation_notes = notes
        self.is_false_positive = is_false_positive
        self.save(update_fields=[
            'is_investigated', 'investigated_by', 'investigated_at',
            'investigation_notes', 'is_false_positive'
        ])