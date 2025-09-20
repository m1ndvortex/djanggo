"""
Models for admin panel impersonation system.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import uuid

User = get_user_model()


class ImpersonationSession(models.Model):
    """
    Model to track all admin impersonation sessions for comprehensive audit logging.
    This model exists in the public schema for cross-tenant audit tracking.
    """
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('ended', _('Ended')),
        ('expired', _('Expired')),
        ('terminated', _('Terminated')),
    ]
    
    # Unique session identifier
    session_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        verbose_name=_('Session ID'),
        help_text=_('Unique identifier for this impersonation session')
    )
    
    # Admin user performing the impersonation
    admin_user_id = models.IntegerField(
        verbose_name=_('Admin User ID'),
        help_text=_('ID of the super admin performing impersonation')
    )
    admin_username = models.CharField(
        max_length=150,
        verbose_name=_('Admin Username'),
        help_text=_('Username of the super admin performing impersonation')
    )
    
    # Target user being impersonated
    target_user_id = models.IntegerField(
        verbose_name=_('Target User ID'),
        help_text=_('ID of the user being impersonated')
    )
    target_username = models.CharField(
        max_length=150,
        verbose_name=_('Target Username'),
        help_text=_('Username of the user being impersonated')
    )
    
    # Tenant information
    tenant_schema = models.CharField(
        max_length=100,
        verbose_name=_('Tenant Schema'),
        help_text=_('Schema name of the tenant where impersonation occurred')
    )
    tenant_domain = models.CharField(
        max_length=253,
        verbose_name=_('Tenant Domain'),
        help_text=_('Domain of the tenant where impersonation occurred')
    )
    
    # Session timing
    start_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Start Time'),
        help_text=_('When the impersonation session started')
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('End Time'),
        help_text=_('When the impersonation session ended')
    )
    
    # Session metadata
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name=_('Status')
    )
    
    ip_address = models.GenericIPAddressField(
        verbose_name=_('IP Address'),
        help_text=_('IP address from which impersonation was initiated')
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent'),
        help_text=_('Browser user agent string')
    )
    
    # Audit information
    reason = models.TextField(
        blank=True,
        verbose_name=_('Reason'),
        help_text=_('Reason for impersonation (optional)')
    )
    
    actions_performed = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Actions Performed'),
        help_text=_('List of actions performed during impersonation')
    )
    
    pages_visited = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Pages Visited'),
        help_text=_('List of pages visited during impersonation')
    )
    
    # Security flags
    is_suspicious = models.BooleanField(
        default=False,
        verbose_name=_('Is Suspicious'),
        help_text=_('Flag indicating if this session was flagged as suspicious')
    )
    
    security_notes = models.TextField(
        blank=True,
        verbose_name=_('Security Notes'),
        help_text=_('Additional security notes about this session')
    )
    
    class Meta:
        verbose_name = _('Impersonation Session')
        verbose_name_plural = _('Impersonation Sessions')
        db_table = 'admin_impersonation_session'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['admin_user_id', 'start_time']),
            models.Index(fields=['target_user_id', 'start_time']),
            models.Index(fields=['tenant_schema', 'start_time']),
            models.Index(fields=['status', 'start_time']),
            models.Index(fields=['session_id']),
        ]
    
    def __str__(self):
        return f"Impersonation: {self.admin_username} -> {self.target_username} ({self.status})"
    
    @property
    def duration(self):
        """Calculate session duration."""
        if self.end_time:
            return self.end_time - self.start_time
        if self.start_time:
            return timezone.now() - self.start_time
        return timezone.timedelta(0)
    
    @property
    def is_active(self):
        """Check if session is currently active."""
        return self.status == 'active' and not self.end_time
    
    @property
    def is_expired(self):
        """Check if session has expired (active for more than 4 hours)."""
        if self.is_active:
            max_duration = timezone.timedelta(hours=4)
            return self.duration > max_duration
        return False
    
    def end_session(self, reason='manual'):
        """End the impersonation session."""
        if self.is_active:
            self.end_time = timezone.now()
            self.status = 'ended'
            
            # Add end reason to security notes
            if self.security_notes:
                self.security_notes += f"\nSession ended: {reason}"
            else:
                self.security_notes = f"Session ended: {reason}"
            
            self.save(update_fields=['end_time', 'status', 'security_notes'])
    
    def terminate_session(self, reason='security'):
        """Terminate the session (forced end for security reasons)."""
        self.end_time = timezone.now()
        self.status = 'terminated'
        self.is_suspicious = True
        
        # Add termination reason to security notes
        if self.security_notes:
            self.security_notes += f"\nSession terminated: {reason}"
        else:
            self.security_notes = f"Session terminated: {reason}"
        
        self.save(update_fields=['end_time', 'status', 'is_suspicious', 'security_notes'])
    
    def add_action(self, action_type, description, url=None):
        """Add an action to the session log."""
        action = {
            'timestamp': timezone.now().isoformat(),
            'type': action_type,
            'description': description,
            'url': url,
        }
        
        self.actions_performed.append(action)
        if self.pk:  # Only save if object exists in database
            self.save(update_fields=['actions_performed'])
    
    def add_page_visit(self, url, title=None):
        """Add a page visit to the session log."""
        visit = {
            'timestamp': timezone.now().isoformat(),
            'url': url,
            'title': title,
        }
        
        self.pages_visited.append(visit)
        if self.pk:  # Only save if object exists in database
            self.save(update_fields=['pages_visited'])
    
    def flag_as_suspicious(self, reason):
        """Flag the session as suspicious."""
        self.is_suspicious = True
        
        if self.security_notes:
            self.security_notes += f"\nFlagged as suspicious: {reason}"
        else:
            self.security_notes = f"Flagged as suspicious: {reason}"
        
        if self.pk:  # Only save if object exists in database
            self.save(update_fields=['is_suspicious', 'security_notes'])
    
    def clean(self):
        """Validate the impersonation session."""
        super().clean()
        
        # Validate that admin and target users are different
        if self.admin_user_id == self.target_user_id:
            raise ValidationError(_('Admin user cannot impersonate themselves'))
        
        # Validate session timing
        if self.end_time and self.end_time <= self.start_time:
            raise ValidationError(_('End time must be after start time'))
    
    def save(self, *args, **kwargs):
        """Override save to perform additional validation and logging."""
        self.clean()
        
        # Auto-expire sessions that are too old
        if self.is_expired and self.status == 'active':
            self.status = 'expired'
            self.end_time = timezone.now()
        
        super().save(*args, **kwargs)
        
        # Log to audit system
        self._log_to_audit()
    
    def _log_to_audit(self):
        """Log impersonation session to audit system."""
        import logging
        
        logger = logging.getLogger('hijack_audit')
        
        log_data = {
            'session_id': str(self.session_id),
            'admin_user': self.admin_username,
            'target_user': self.target_username,
            'tenant_schema': self.tenant_schema,
            'tenant_domain': self.tenant_domain,
            'status': self.status,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration.total_seconds(),
            'ip_address': self.ip_address,
            'is_suspicious': self.is_suspicious,
            'actions_count': len(self.actions_performed),
            'pages_count': len(self.pages_visited),
        }
        
        logger.info(f"Impersonation session update: {log_data}")


class ImpersonationSessionManager(models.Manager):
    """Custom manager for ImpersonationSession with utility methods."""
    
    def active_sessions(self):
        """Get all active impersonation sessions."""
        return self.filter(status='active', end_time__isnull=True)
    
    def expired_sessions(self):
        """Get all expired sessions that should be terminated."""
        cutoff_time = timezone.now() - timezone.timedelta(hours=4)
        return self.filter(
            status='active',
            start_time__lt=cutoff_time,
            end_time__isnull=True
        )
    
    def sessions_by_admin(self, admin_user_id):
        """Get all sessions for a specific admin user."""
        return self.filter(admin_user_id=admin_user_id).order_by('-start_time')
    
    def sessions_by_tenant(self, tenant_schema):
        """Get all sessions for a specific tenant."""
        return self.filter(tenant_schema=tenant_schema).order_by('-start_time')
    
    def suspicious_sessions(self):
        """Get all sessions flagged as suspicious."""
        return self.filter(is_suspicious=True).order_by('-start_time')
    
    def cleanup_expired_sessions(self):
        """Cleanup expired sessions by marking them as expired."""
        expired_sessions = self.expired_sessions()
        count = expired_sessions.count()
        
        expired_sessions.update(
            status='expired',
            end_time=timezone.now(),
            security_notes=models.F('security_notes') + '\nAuto-expired due to timeout'
        )
        
        return count


# Add the custom manager to the model
ImpersonationSession.add_to_class('objects', ImpersonationSessionManager())