"""
Models for admin panel impersonation system and RBAC.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
import uuid


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
    
    # Custom manager
    objects = ImpersonationSessionManager()
    
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





class BackupJob(models.Model):
    """
    Model to track backup jobs and their status.
    """
    BACKUP_TYPES = [
        ('full_system', _('Full System Backup')),
        ('tenant_only', _('Single Tenant Backup')),
        ('configuration', _('Configuration Backup')),
        ('database_only', _('Database Only Backup')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('running', _('Running')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]
    
    FREQUENCY_CHOICES = [
        ('manual', _('Manual')),
        ('daily', _('Daily')),
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
    ]
    
    # Job identification
    job_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        verbose_name=_('Job ID'),
        help_text=_('Unique identifier for this backup job')
    )
    
    name = models.CharField(
        max_length=200,
        verbose_name=_('Backup Name'),
        help_text=_('Human-readable name for this backup')
    )
    
    backup_type = models.CharField(
        max_length=20,
        choices=BACKUP_TYPES,
        verbose_name=_('Backup Type')
    )
    
    # Scheduling
    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default='manual',
        verbose_name=_('Backup Frequency')
    )
    
    scheduled_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_('Scheduled Time'),
        help_text=_('Time of day for automatic backups')
    )
    
    next_run = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Next Scheduled Run')
    )
    
    # Status and timing
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Status')
    )
    
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Started At')
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Completed At')
    )
    
    # Backup details
    tenant_schema = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Tenant Schema'),
        help_text=_('Specific tenant schema for tenant-only backups')
    )
    
    file_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Backup File Path'),
        help_text=_('Path to the backup file in storage')
    )
    
    file_size_bytes = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name=_('File Size (Bytes)')
    )
    
    # Storage information
    storage_backends = models.JSONField(
        default=list,
        verbose_name=_('Storage Backends'),
        help_text=_('List of storage backends where backup is stored')
    )
    
    # Progress and logging
    progress_percentage = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Progress Percentage')
    )
    
    log_messages = models.JSONField(
        default=list,
        verbose_name=_('Log Messages'),
        help_text=_('Array of log messages from backup process')
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Error Message')
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        verbose_name=_('Backup Metadata'),
        help_text=_('Additional metadata about the backup')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Created By ID'),
        help_text=_('ID of the user who created this backup')
    )
    
    created_by_username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Created By Username'),
        help_text=_('Username of the user who created this backup')
    )
    
    class Meta:
        verbose_name = _('Backup Job')
        verbose_name_plural = _('Backup Jobs')
        db_table = 'admin_backup_job'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['backup_type', 'status']),
            models.Index(fields=['frequency', 'next_run']),
            models.Index(fields=['job_id']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    @property
    def duration(self):
        """Calculate backup duration."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return timezone.now() - self.started_at
        return timezone.timedelta(0)
    
    @property
    def is_running(self):
        """Check if backup is currently running."""
        return self.status == 'running'
    
    @property
    def is_completed(self):
        """Check if backup completed successfully."""
        return self.status == 'completed'
    
    @property
    def is_failed(self):
        """Check if backup failed."""
        return self.status == 'failed'
    
    @property
    def file_size_human(self):
        """Return human-readable file size."""
        if not self.file_size_bytes:
            return 'Unknown'
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if self.file_size_bytes < 1024.0:
                return f"{self.file_size_bytes:.1f} {unit}"
            self.file_size_bytes /= 1024.0
        return f"{self.file_size_bytes:.1f} PB"
    
    def add_log_message(self, level, message):
        """Add a log message to the backup job."""
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'level': level,
            'message': message
        }
        self.log_messages.append(log_entry)
        if self.pk:  # Only save if object exists in database
            self.save(update_fields=['log_messages'])
    
    def update_progress(self, percentage, message=None):
        """Update backup progress."""
        self.progress_percentage = min(100, max(0, percentage))
        if message:
            self.add_log_message('info', message)
        if self.pk:  # Only save if object exists in database
            self.save(update_fields=['progress_percentage'])
    
    def mark_as_running(self):
        """Mark backup as running."""
        self.status = 'running'
        self.started_at = timezone.now()
        self.progress_percentage = 0
        self.add_log_message('info', 'Backup job started')
        self.save(update_fields=['status', 'started_at', 'progress_percentage'])
    
    def mark_as_completed(self, file_path, file_size_bytes, storage_backends):
        """Mark backup as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.progress_percentage = 100
        self.file_path = file_path
        self.file_size_bytes = file_size_bytes
        self.storage_backends = storage_backends
        self.add_log_message('info', 'Backup job completed successfully')
        self.save(update_fields=[
            'status', 'completed_at', 'progress_percentage', 
            'file_path', 'file_size_bytes', 'storage_backends'
        ])
    
    def mark_as_failed(self, error_message):
        """Mark backup as failed."""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.add_log_message('error', f'Backup job failed: {error_message}')
        self.save(update_fields=['status', 'completed_at', 'error_message'])
    
    def calculate_next_run(self):
        """Calculate next run time based on frequency."""
        if self.frequency == 'manual':
            self.next_run = None
            return
        
        from datetime import timedelta
        
        base_time = timezone.now()
        if self.scheduled_time:
            # Set to scheduled time today or tomorrow
            base_time = base_time.replace(
                hour=self.scheduled_time.hour,
                minute=self.scheduled_time.minute,
                second=0,
                microsecond=0
            )
            if base_time <= timezone.now():
                base_time += timedelta(days=1)
        
        if self.frequency == 'daily':
            self.next_run = base_time
        elif self.frequency == 'weekly':
            # Next week same day
            days_ahead = 7 - base_time.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            self.next_run = base_time + timedelta(days=days_ahead)
        elif self.frequency == 'monthly':
            # Next month same day
            if base_time.month == 12:
                next_month = base_time.replace(year=base_time.year + 1, month=1)
            else:
                next_month = base_time.replace(month=base_time.month + 1)
            self.next_run = next_month
        
        if self.pk:  # Only save if object exists in database
            self.save(update_fields=['next_run'])


class BackupSchedule(models.Model):
    """
    Model to manage backup scheduling configuration.
    """
    name = models.CharField(
        max_length=200,
        verbose_name=_('Schedule Name')
    )
    
    backup_type = models.CharField(
        max_length=20,
        choices=BackupJob.BACKUP_TYPES,
        verbose_name=_('Backup Type')
    )
    
    frequency = models.CharField(
        max_length=20,
        choices=BackupJob.FREQUENCY_CHOICES,
        verbose_name=_('Frequency')
    )
    
    scheduled_time = models.TimeField(
        verbose_name=_('Scheduled Time')
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    
    # Retention settings
    retention_days = models.PositiveIntegerField(
        default=30,
        verbose_name=_('Retention Days'),
        help_text=_('Number of days to keep backups')
    )
    
    max_backups = models.PositiveIntegerField(
        default=10,
        verbose_name=_('Maximum Backups'),
        help_text=_('Maximum number of backups to keep')
    )
    
    # Notification settings
    notify_on_success = models.BooleanField(
        default=False,
        verbose_name=_('Notify on Success')
    )
    
    notify_on_failure = models.BooleanField(
        default=True,
        verbose_name=_('Notify on Failure')
    )
    
    notification_emails = models.JSONField(
        default=list,
        verbose_name=_('Notification Emails'),
        help_text=_('List of email addresses for notifications')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Created By ID'),
        help_text=_('ID of the user who created this schedule')
    )
    
    created_by_username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Created By Username'),
        help_text=_('Username of the user who created this schedule')
    )
    
    class Meta:
        verbose_name = _('Backup Schedule')
        verbose_name_plural = _('Backup Schedules')
        db_table = 'admin_backup_schedule'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"


class RestoreJob(models.Model):
    """
    Model to track restore operations.
    """
    RESTORE_TYPES = [
        ('full_system', _('Full System Restore')),
        ('single_tenant', _('Single Tenant Restore')),
        ('configuration', _('Configuration Restore')),
        ('snapshot_restore', _('Snapshot Restore')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('running', _('Running')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]
    
    # Job identification
    job_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        verbose_name=_('Job ID')
    )
    
    restore_type = models.CharField(
        max_length=20,
        choices=RESTORE_TYPES,
        verbose_name=_('Restore Type')
    )
    
    # Source backup
    source_backup = models.ForeignKey(
        BackupJob,
        on_delete=models.CASCADE,
        verbose_name=_('Source Backup')
    )
    
    # Target information
    target_tenant_schema = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Target Tenant Schema'),
        help_text=_('Target tenant schema for single tenant restore')
    )
    
    # Status and timing
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Status')
    )
    
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Started At')
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Completed At')
    )
    
    # Progress and logging
    progress_percentage = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Progress Percentage')
    )
    
    log_messages = models.JSONField(
        default=list,
        verbose_name=_('Log Messages')
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Error Message')
    )
    
    # Confirmation
    confirmation_token = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Confirmation Token'),
        help_text=_('Token required for dangerous restore operations')
    )
    
    confirmed_by_typing = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Confirmed by Typing'),
        help_text=_('Text that user typed to confirm restore')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Created By ID'),
        help_text=_('ID of the user who created this restore job')
    )
    
    created_by_username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Created By Username'),
        help_text=_('Username of the user who created this restore job')
    )
    
    class Meta:
        verbose_name = _('Restore Job')
        verbose_name_plural = _('Restore Jobs')
        db_table = 'admin_restore_job'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Restore {self.job_id} ({self.get_status_display()})"
    
    @property
    def duration(self):
        """Calculate restore duration."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return timezone.now() - self.started_at
        return timezone.timedelta(0)
    
    def add_log_message(self, level, message):
        """Add a log message to the restore job."""
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'level': level,
            'message': message
        }
        self.log_messages.append(log_entry)
        if self.pk:
            self.save(update_fields=['log_messages'])
    
    def update_progress(self, percentage, message=None):
        """Update restore progress."""
        self.progress_percentage = min(100, max(0, percentage))
        if message:
            self.add_log_message('info', message)
        if self.pk:
            self.save(update_fields=['progress_percentage'])
    
    def mark_as_running(self):
        """Mark restore as running."""
        self.status = 'running'
        self.started_at = timezone.now()
        self.progress_percentage = 0
        self.add_log_message('info', 'Restore job started')
        self.save(update_fields=['status', 'started_at', 'progress_percentage'])
    
    def mark_as_completed(self):
        """Mark restore as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.progress_percentage = 100
        self.add_log_message('info', 'Restore job completed successfully')
        self.save(update_fields=['status', 'completed_at', 'progress_percentage'])
    
    def mark_as_failed(self, error_message):
        """Mark restore as failed."""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.add_log_message('error', f'Restore job failed: {error_message}')
        self.save(update_fields=['status', 'completed_at', 'error_message'])


class SecurityPolicy(models.Model):
    """
    Model for storing security policy configurations.
    """
    POLICY_TYPES = [
        ('password', _('Password Policy')),
        ('session', _('Session Policy')),
        ('rate_limit', _('Rate Limiting Policy')),
        ('authentication', _('Authentication Policy')),
        ('access_control', _('Access Control Policy')),
    ]
    
    name = models.CharField(
        max_length=200,
        verbose_name=_('Policy Name'),
        help_text=_('Human-readable name for this security policy')
    )
    
    policy_type = models.CharField(
        max_length=50,
        choices=POLICY_TYPES,
        verbose_name=_('Policy Type')
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active'),
        help_text=_('Whether this policy is currently active')
    )
    
    configuration = models.JSONField(
        default=dict,
        verbose_name=_('Policy Configuration'),
        help_text=_('JSON configuration for the security policy')
    )
    
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Description of what this policy does')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Created By ID'),
        help_text=_('ID of the user who created this policy')
    )
    
    created_by_username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Created By Username'),
        help_text=_('Username of the user who created this policy')
    )
    
    updated_by_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Updated By ID'),
        help_text=_('ID of the user who last updated this policy')
    )
    
    updated_by_username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Updated By Username'),
        help_text=_('Username of the user who last updated this policy')
    )
    
    class Meta:
        verbose_name = _('Security Policy')
        verbose_name_plural = _('Security Policies')
        db_table = 'admin_security_policy'
        ordering = ['policy_type', 'name']
        unique_together = ['policy_type', 'name']
        indexes = [
            models.Index(fields=['policy_type', 'is_active']),
            models.Index(fields=['is_active', 'updated_at']),
        ]
    
    def __str__(self):
        return f"{self.get_policy_type_display()}: {self.name}"
    
    def clean(self):
        """Validate policy configuration based on type."""
        super().clean()
        
        if self.policy_type == 'password':
            self._validate_password_policy()
        elif self.policy_type == 'session':
            self._validate_session_policy()
        elif self.policy_type == 'rate_limit':
            self._validate_rate_limit_policy()
        elif self.policy_type == 'authentication':
            self._validate_authentication_policy()
    
    def _validate_password_policy(self):
        """Validate password policy configuration."""
        required_fields = ['min_length', 'require_uppercase', 'require_lowercase', 
                          'require_numbers', 'require_special_chars', 'max_age_days']
        
        for field in required_fields:
            if field not in self.configuration:
                raise ValidationError(f'Password policy missing required field: {field}')
        
        # Validate numeric fields
        if not isinstance(self.configuration.get('min_length'), int) or self.configuration['min_length'] < 1:
            raise ValidationError('Password min_length must be a positive integer')
        
        if not isinstance(self.configuration.get('max_age_days'), int) or self.configuration['max_age_days'] < 1:
            raise ValidationError('Password max_age_days must be a positive integer')
    
    def _validate_session_policy(self):
        """Validate session policy configuration."""
        required_fields = ['timeout_minutes', 'max_concurrent_sessions', 'require_reauth_for_sensitive']
        
        for field in required_fields:
            if field not in self.configuration:
                raise ValidationError(f'Session policy missing required field: {field}')
        
        # Validate numeric fields
        if not isinstance(self.configuration.get('timeout_minutes'), int) or self.configuration['timeout_minutes'] < 1:
            raise ValidationError('Session timeout_minutes must be a positive integer')
        
        if not isinstance(self.configuration.get('max_concurrent_sessions'), int) or self.configuration['max_concurrent_sessions'] < 1:
            raise ValidationError('Session max_concurrent_sessions must be a positive integer')
    
    def _validate_rate_limit_policy(self):
        """Validate rate limiting policy configuration."""
        required_fields = ['limits']
        
        for field in required_fields:
            if field not in self.configuration:
                raise ValidationError(f'Rate limit policy missing required field: {field}')
        
        # Validate limits structure
        limits = self.configuration.get('limits', {})
        if not isinstance(limits, dict):
            raise ValidationError('Rate limit policy limits must be a dictionary')
        
        for limit_type, config in limits.items():
            if not isinstance(config, dict):
                raise ValidationError(f'Rate limit config for {limit_type} must be a dictionary')
            
            if 'requests' not in config or 'window_minutes' not in config:
                raise ValidationError(f'Rate limit config for {limit_type} must have requests and window_minutes')
    
    def _validate_authentication_policy(self):
        """Validate authentication policy configuration."""
        required_fields = ['require_2fa', 'lockout_attempts', 'lockout_duration_minutes']
        
        for field in required_fields:
            if field not in self.configuration:
                raise ValidationError(f'Authentication policy missing required field: {field}')
    
    @classmethod
    def get_active_policy(cls, policy_type):
        """Get the active policy for a given type."""
        try:
            return cls.objects.filter(policy_type=policy_type, is_active=True).first()
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def get_password_policy(cls):
        """Get the active password policy configuration."""
        policy = cls.get_active_policy('password')
        if policy:
            return policy.configuration
        
        # Return default password policy
        return {
            'min_length': 8,
            'require_uppercase': True,
            'require_lowercase': True,
            'require_numbers': True,
            'require_special_chars': True,
            'max_age_days': 90,
            'prevent_reuse_count': 5,
            'special_chars': '!@#$%^&*()_+-=[]{}|;:,.<>?',
        }
    
    @classmethod
    def get_session_policy(cls):
        """Get the active session policy configuration."""
        policy = cls.get_active_policy('session')
        if policy:
            return policy.configuration
        
        # Return default session policy
        return {
            'timeout_minutes': 480,  # 8 hours
            'max_concurrent_sessions': 3,
            'require_reauth_for_sensitive': True,
            'extend_on_activity': True,
            'secure_cookies': True,
        }
    
    @classmethod
    def get_rate_limit_policy(cls):
        """Get the active rate limiting policy configuration."""
        policy = cls.get_active_policy('rate_limit')
        if policy:
            return policy.configuration
        
        # Return default rate limiting policy
        return {
            'limits': {
                'login': {'requests': 5, 'window_minutes': 60},
                'api_call': {'requests': 1000, 'window_minutes': 60},
                'password_reset': {'requests': 3, 'window_minutes': 60},
                '2fa_verify': {'requests': 10, 'window_minutes': 60},
                'data_export': {'requests': 10, 'window_minutes': 60},
            }
        }
    
    @classmethod
    def get_authentication_policy(cls):
        """Get the active authentication policy configuration."""
        policy = cls.get_active_policy('authentication')
        if policy:
            return policy.configuration
        
        # Return default authentication policy
        return {
            'require_2fa': False,
            'lockout_attempts': 5,
            'lockout_duration_minutes': 30,
            'password_reset_token_expiry_hours': 24,
            'remember_me_duration_days': 30,
        }


class SystemSetting(models.Model):
    """
    Model for storing system-wide configuration settings.
    """
    SETTING_TYPES = [
        ('string', _('String')),
        ('integer', _('Integer')),
        ('float', _('Float')),
        ('boolean', _('Boolean')),
        ('json', _('JSON')),
        ('text', _('Text')),
        ('email', _('Email')),
        ('url', _('URL')),
        ('password', _('Password')),
    ]
    
    CATEGORIES = [
        ('general', _('General')),
        ('security', _('Security')),
        ('authentication', _('Authentication')),
        ('notifications', _('Notifications')),
        ('backup', _('Backup')),
        ('integration', _('Integration')),
        ('performance', _('Performance')),
        ('localization', _('Localization')),
        ('ui', _('User Interface')),
        ('api', _('API')),
    ]
    
    # Setting identification
    key = models.CharField(
        max_length=200,
        unique=True,
        verbose_name=_('Setting Key'),
        help_text=_('Unique identifier for this setting')
    )
    
    name = models.CharField(
        max_length=200,
        verbose_name=_('Setting Name'),
        help_text=_('Human-readable name for this setting')
    )
    
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Detailed description of what this setting controls')
    )
    
    # Setting value and type
    value = models.TextField(
        blank=True,
        verbose_name=_('Value'),
        help_text=_('Current value of the setting')
    )
    
    default_value = models.TextField(
        blank=True,
        verbose_name=_('Default Value'),
        help_text=_('Default value for this setting')
    )
    
    setting_type = models.CharField(
        max_length=20,
        choices=SETTING_TYPES,
        default='string',
        verbose_name=_('Setting Type')
    )
    
    # Organization
    category = models.CharField(
        max_length=50,
        choices=CATEGORIES,
        default='general',
        verbose_name=_('Category')
    )
    
    section = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Section'),
        help_text=_('Sub-section within category for organization')
    )
    
    # Validation and constraints
    validation_rules = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Validation Rules'),
        help_text=_('JSON object containing validation rules')
    )
    
    choices = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Choices'),
        help_text=_('List of valid choices for this setting')
    )
    
    # Behavior flags
    is_sensitive = models.BooleanField(
        default=False,
        verbose_name=_('Is Sensitive'),
        help_text=_('Whether this setting contains sensitive information')
    )
    
    requires_restart = models.BooleanField(
        default=False,
        verbose_name=_('Requires Restart'),
        help_text=_('Whether changing this setting requires system restart')
    )
    
    is_readonly = models.BooleanField(
        default=False,
        verbose_name=_('Is Read Only'),
        help_text=_('Whether this setting can be modified through UI')
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active'),
        help_text=_('Whether this setting is currently active')
    )
    
    # Display options
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Display Order'),
        help_text=_('Order for displaying in UI')
    )
    
    help_text = models.TextField(
        blank=True,
        verbose_name=_('Help Text'),
        help_text=_('Help text to display in UI')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Created By ID'),
        help_text=_('ID of the user who created this setting')
    )
    
    created_by_username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Created By Username'),
        help_text=_('Username of the user who created this setting')
    )
    
    updated_by_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Updated By ID'),
        help_text=_('ID of the user who last updated this setting')
    )
    
    updated_by_username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Updated By Username'),
        help_text=_('Username of the user who last updated this setting')
    )
    
    class Meta:
        verbose_name = _('System Setting')
        verbose_name_plural = _('System Settings')
        db_table = 'admin_system_setting'
        ordering = ['category', 'section', 'display_order', 'name']
        indexes = [
            models.Index(fields=['key']),
            models.Index(fields=['category', 'section']),
            models.Index(fields=['is_active', 'category']),
            models.Index(fields=['setting_type', 'category']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.key})"
    
    def get_typed_value(self):
        """Return the setting value converted to its proper type."""
        if not self.value:
            return self.get_typed_default_value()
        
        try:
            if self.setting_type == 'boolean':
                return self.value.lower() in ('true', '1', 'yes', 'on')
            elif self.setting_type == 'integer':
                return int(self.value)
            elif self.setting_type == 'float':
                return float(self.value)
            elif self.setting_type == 'json':
                import json
                return json.loads(self.value)
            else:
                return self.value
        except (ValueError, TypeError) as e:
            return self.get_typed_default_value()
        except Exception as e:  # Catch JSON decode errors and other exceptions
            return self.get_typed_default_value()
    
    def get_typed_default_value(self):
        """Return the default value converted to its proper type."""
        if not self.default_value:
            return self._get_type_default()
        
        try:
            if self.setting_type == 'boolean':
                return self.default_value.lower() in ('true', '1', 'yes', 'on')
            elif self.setting_type == 'integer':
                return int(self.default_value)
            elif self.setting_type == 'float':
                return float(self.default_value)
            elif self.setting_type == 'json':
                import json
                return json.loads(self.default_value)
            else:
                return self.default_value
        except (ValueError, TypeError) as e:
            return self._get_type_default()
        except Exception as e:  # Catch JSON decode errors and other exceptions
            return self._get_type_default()
    
    def _get_type_default(self):
        """Get default value based on setting type."""
        defaults = {
            'string': '',
            'integer': 0,
            'float': 0.0,
            'boolean': False,
            'json': {},
            'text': '',
            'email': '',
            'url': '',
            'password': '',
        }
        return defaults.get(self.setting_type, '')
    
    def set_value(self, value, user=None):
        """Set the setting value with validation and audit logging."""
        old_value = self.value
        
        # Convert value to string for storage
        if self.setting_type == 'json':
            import json
            self.value = json.dumps(value, ensure_ascii=False)
        elif self.setting_type == 'boolean':
            self.value = 'true' if value else 'false'
        else:
            self.value = str(value)
        
        # Update audit fields
        if user:
            self.updated_by_id = user.id
            self.updated_by_username = user.username
        
        self.save()
        
        # Log the change
        self._log_change(old_value, self.value, user)
    
    def _log_change(self, old_value, new_value, user):
        """Log setting change to audit system."""
        try:
            from zargar.core.security_models import AuditLog
            
            AuditLog.log_action(
                action='configuration_change',
                user=user,
                content_object=self,
                old_values={'value': old_value},
                new_values={'value': new_value},
                details={
                    'setting_key': self.key,
                    'setting_name': self.name,
                    'category': self.category,
                    'requires_restart': self.requires_restart,
                }
            )
        except Exception as e:
            # If audit logging fails, log to standard logger but don't fail the operation
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to log setting change for {self.key}: {e}")
    
    def validate_value(self, value):
        """Validate a value against this setting's rules."""
        errors = []
        
        # Type validation
        try:
            if self.setting_type == 'integer':
                int(value)
            elif self.setting_type == 'float':
                float(value)
            elif self.setting_type == 'boolean':
                if str(value).lower() not in ('true', 'false', '1', '0', 'yes', 'no', 'on', 'off'):
                    errors.append(_('Invalid boolean value'))
            elif self.setting_type == 'json':
                import json
                json.loads(value)
            elif self.setting_type == 'email':
                from django.core.validators import validate_email
                validate_email(value)
            elif self.setting_type == 'url':
                from django.core.validators import URLValidator
                URLValidator()(value)
        except (ValueError, TypeError, ValidationError) as e:
            errors.append(str(e))
        
        # Choice validation
        if self.choices and value not in self.choices:
            errors.append(_('Value must be one of: {}').format(', '.join(self.choices)))
        
        # Custom validation rules
        if self.validation_rules:
            errors.extend(self._validate_custom_rules(value))
        
        return errors
    
    def _validate_custom_rules(self, value):
        """Validate value against custom validation rules."""
        errors = []
        rules = self.validation_rules
        
        if 'min_length' in rules:
            if len(str(value)) < rules['min_length']:
                errors.append(_('Value must be at least {} characters').format(rules['min_length']))
        
        if 'max_length' in rules:
            if len(str(value)) > rules['max_length']:
                errors.append(_('Value must be at most {} characters').format(rules['max_length']))
        
        if 'min_value' in rules and self.setting_type in ('integer', 'float'):
            try:
                if float(value) < rules['min_value']:
                    errors.append(_('Value must be at least {}').format(rules['min_value']))
            except (ValueError, TypeError):
                pass
        
        if 'max_value' in rules and self.setting_type in ('integer', 'float'):
            try:
                if float(value) > rules['max_value']:
                    errors.append(_('Value must be at most {}').format(rules['max_value']))
            except (ValueError, TypeError):
                pass
        
        if 'pattern' in rules:
            import re
            if not re.match(rules['pattern'], str(value)):
                errors.append(_('Value does not match required pattern'))
        
        return errors
    
    def reset_to_default(self, user=None):
        """Reset setting to its default value."""
        old_value = self.value
        self.value = self.default_value
        
        if user:
            self.updated_by_id = user.id
            self.updated_by_username = user.username
        
        self.save()
        
        # Log the reset
        self._log_change(old_value, self.value, user)


class NotificationSetting(models.Model):
    """
    Model for storing notification configuration settings.
    """
    NOTIFICATION_TYPES = [
        ('email', _('Email')),
        ('sms', _('SMS')),
        ('push', _('Push Notification')),
        ('webhook', _('Webhook')),
        ('slack', _('Slack')),
        ('telegram', _('Telegram')),
    ]
    
    EVENT_TYPES = [
        ('security_alert', _('Security Alert')),
        ('backup_complete', _('Backup Complete')),
        ('backup_failed', _('Backup Failed')),
        ('system_error', _('System Error')),
        ('maintenance_start', _('Maintenance Start')),
        ('maintenance_end', _('Maintenance End')),
        ('tenant_created', _('Tenant Created')),
        ('tenant_suspended', _('Tenant Suspended')),
        ('payment_failed', _('Payment Failed')),
        ('storage_full', _('Storage Full')),
        ('performance_issue', _('Performance Issue')),
        ('integration_failure', _('Integration Failure')),
    ]
    
    PRIORITY_LEVELS = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    # Notification identification
    name = models.CharField(
        max_length=200,
        verbose_name=_('Notification Name'),
        help_text=_('Human-readable name for this notification setting')
    )
    
    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
        verbose_name=_('Event Type'),
        help_text=_('Type of event that triggers this notification')
    )
    
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        verbose_name=_('Notification Type'),
        help_text=_('Method of notification delivery')
    )
    
    # Targeting
    recipients = models.JSONField(
        default=list,
        verbose_name=_('Recipients'),
        help_text=_('List of recipients (emails, phone numbers, etc.)')
    )
    
    recipient_roles = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Recipient Roles'),
        help_text=_('List of user roles that should receive this notification')
    )
    
    # Conditions
    conditions = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Conditions'),
        help_text=_('Conditions that must be met for notification to be sent')
    )
    
    priority_threshold = models.CharField(
        max_length=20,
        choices=PRIORITY_LEVELS,
        default='medium',
        verbose_name=_('Priority Threshold'),
        help_text=_('Minimum priority level to trigger notification')
    )
    
    # Timing and throttling
    is_enabled = models.BooleanField(
        default=True,
        verbose_name=_('Is Enabled'),
        help_text=_('Whether this notification is currently active')
    )
    
    throttle_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Throttle Minutes'),
        help_text=_('Minimum minutes between notifications of same type (0 = no throttling)')
    )
    
    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_('Quiet Hours Start'),
        help_text=_('Start time for quiet hours (no notifications)')
    )
    
    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_('Quiet Hours End'),
        help_text=_('End time for quiet hours')
    )
    
    # Template and formatting
    subject_template = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Subject Template'),
        help_text=_('Template for notification subject/title')
    )
    
    message_template = models.TextField(
        blank=True,
        verbose_name=_('Message Template'),
        help_text=_('Template for notification message body')
    )
    
    template_variables = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Template Variables'),
        help_text=_('Available variables for use in templates')
    )
    
    # Delivery configuration
    delivery_config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Delivery Configuration'),
        help_text=_('Provider-specific configuration (SMTP settings, API keys, etc.)')
    )
    
    retry_attempts = models.PositiveIntegerField(
        default=3,
        verbose_name=_('Retry Attempts'),
        help_text=_('Number of times to retry failed deliveries')
    )
    
    retry_delay_minutes = models.PositiveIntegerField(
        default=5,
        verbose_name=_('Retry Delay Minutes'),
        help_text=_('Minutes to wait between retry attempts')
    )
    
    # Statistics
    total_sent = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total Sent'),
        help_text=_('Total number of notifications sent')
    )
    
    total_failed = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total Failed'),
        help_text=_('Total number of failed deliveries')
    )
    
    last_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last Sent At'),
        help_text=_('When this notification was last sent')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Created By ID'),
        help_text=_('ID of the user who created this notification setting')
    )
    
    created_by_username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Created By Username'),
        help_text=_('Username of the user who created this notification setting')
    )
    
    class Meta:
        verbose_name = _('Notification Setting')
        verbose_name_plural = _('Notification Settings')
        db_table = 'admin_notification_setting'
        ordering = ['event_type', 'notification_type', 'name']
        indexes = [
            models.Index(fields=['event_type', 'is_enabled']),
            models.Index(fields=['notification_type', 'is_enabled']),
            models.Index(fields=['is_enabled', 'priority_threshold']),
        ]
        unique_together = ['event_type', 'notification_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_event_type_display()} → {self.get_notification_type_display()})"
    
    def should_send_notification(self, priority='medium', event_data=None):
        """Check if notification should be sent based on conditions."""
        if not self.is_enabled:
            return False
        
        # Check priority threshold
        priority_order = ['low', 'medium', 'high', 'critical']
        if priority_order.index(priority) < priority_order.index(self.priority_threshold):
            return False
        
        # Check quiet hours
        if self.quiet_hours_start and self.quiet_hours_end:
            current_time = timezone.now().time()
            if self.quiet_hours_start <= current_time <= self.quiet_hours_end:
                return False
        
        # Check throttling
        if self.throttle_minutes > 0 and self.last_sent_at:
            time_since_last = timezone.now() - self.last_sent_at
            if time_since_last.total_seconds() < (self.throttle_minutes * 60):
                return False
        
        # Check custom conditions
        if self.conditions and event_data:
            if not self._evaluate_conditions(event_data):
                return False
        
        return True
    
    def _evaluate_conditions(self, event_data):
        """Evaluate custom conditions against event data."""
        for condition_key, condition_value in self.conditions.items():
            if condition_key not in event_data:
                return False
            
            event_value = event_data[condition_key]
            
            # Handle different condition types
            if isinstance(condition_value, dict):
                if 'equals' in condition_value and event_value != condition_value['equals']:
                    return False
                if 'contains' in condition_value and condition_value['contains'] not in str(event_value):
                    return False
                if 'greater_than' in condition_value and event_value <= condition_value['greater_than']:
                    return False
                if 'less_than' in condition_value and event_value >= condition_value['less_than']:
                    return False
            else:
                if event_value != condition_value:
                    return False
        
        return True
    
    def render_message(self, event_data=None):
        """Render notification message using template and event data."""
        context = {}
        context.update(self.template_variables)
        if event_data:
            context.update(event_data)
        
        # Simple template rendering (can be enhanced with Django templates)
        subject = self.subject_template
        message = self.message_template
        
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            subject = subject.replace(placeholder, str(value))
            message = message.replace(placeholder, str(value))
        
        return subject, message
    
    def record_sent(self):
        """Record that notification was sent successfully."""
        self.total_sent += 1
        self.last_sent_at = timezone.now()
        self.save(update_fields=['total_sent', 'last_sent_at'])
    
    def record_failed(self):
        """Record that notification delivery failed."""
        self.total_failed += 1
        self.save(update_fields=['total_failed'])


class SettingChangeHistory(models.Model):
    """
    Model to track history of setting changes for rollback functionality.
    """
    setting = models.ForeignKey(
        SystemSetting,
        on_delete=models.CASCADE,
        related_name='change_history',
        verbose_name=_('Setting')
    )
    
    old_value = models.TextField(
        blank=True,
        verbose_name=_('Old Value')
    )
    
    new_value = models.TextField(
        blank=True,
        verbose_name=_('New Value')
    )
    
    change_reason = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Change Reason'),
        help_text=_('Reason for the change')
    )
    
    # Audit fields
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Changed By ID')
    )
    
    changed_by_username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Changed By Username')
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP Address')
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )
    
    class Meta:
        verbose_name = _('Setting Change History')
        verbose_name_plural = _('Setting Change History')
        db_table = 'admin_setting_change_history'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['setting', 'changed_at']),
            models.Index(fields=['changed_by_id', 'changed_at']),
        ]
    
    def __str__(self):
        return f"{self.setting.name} changed at {self.changed_at}"


class TenantSnapshot(models.Model):
    """
    Model to track temporary snapshots created before high-risk operations.
    """
    SNAPSHOT_TYPES = [
        ('pre_operation', _('Pre-Operation Snapshot')),
        ('manual', _('Manual Snapshot')),
        ('scheduled', _('Scheduled Snapshot')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('creating', _('Creating')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('expired', _('Expired')),
        ('deleted', _('Deleted')),
    ]
    
    # Snapshot identification
    snapshot_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        verbose_name=_('Snapshot ID')
    )
    
    name = models.CharField(
        max_length=200,
        verbose_name=_('Snapshot Name')
    )
    
    snapshot_type = models.CharField(
        max_length=20,
        choices=SNAPSHOT_TYPES,
        verbose_name=_('Snapshot Type')
    )
    
    # Target information
    tenant_schema = models.CharField(
        max_length=100,
        verbose_name=_('Tenant Schema'),
        help_text=_('Schema name of the tenant being snapshotted')
    )
    
    # Status and timing
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Status')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        verbose_name=_('Expires At'),
        help_text=_('When this snapshot expires and can be deleted')
    )
    
    # File information
    file_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Snapshot File Path')
    )
    
    file_size_bytes = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name=_('File Size (Bytes)')
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        verbose_name=_('Snapshot Metadata')
    )
    
    # Audit fields
    created_by_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Created By ID')
    )
    
    created_by_username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Created By Username')
    )
    
    class Meta:
        verbose_name = _('Tenant Snapshot')
        verbose_name_plural = _('Tenant Snapshots')
        db_table = 'admin_tenant_snapshot'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class SystemHealthMetric(models.Model):
    """
    Model to store system health metrics over time.
    """
    METRIC_TYPES = [
        ('cpu_usage', _('CPU Usage')),
        ('memory_usage', _('Memory Usage')),
        ('disk_usage', _('Disk Usage')),
        ('database_connections', _('Database Connections')),
        ('redis_memory', _('Redis Memory Usage')),
        ('celery_workers', _('Celery Workers')),
        ('response_time', _('Response Time')),
        ('error_rate', _('Error Rate')),
    ]
    
    # Metric identification
    metric_type = models.CharField(
        max_length=30,
        choices=METRIC_TYPES,
        verbose_name=_('Metric Type')
    )
    
    # Metric values
    value = models.FloatField(
        verbose_name=_('Metric Value'),
        help_text=_('Numeric value of the metric')
    )
    
    unit = models.CharField(
        max_length=20,
        verbose_name=_('Unit'),
        help_text=_('Unit of measurement (%, MB, ms, etc.)')
    )
    
    # Timing
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Timestamp')
    )
    
    # Additional context
    hostname = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Hostname'),
        help_text=_('Server hostname where metric was collected')
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Additional Metadata')
    )
    
    class Meta:
        verbose_name = _('System Health Metric')
        verbose_name_plural = _('System Health Metrics')
        db_table = 'admin_system_health_metric'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['metric_type', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_metric_type_display()}: {self.value}{self.unit} at {self.timestamp}"


class SystemHealthAlert(models.Model):
    """
    Model to track system health alerts and notifications.
    """
    SEVERITY_LEVELS = [
        ('info', _('Info')),
        ('warning', _('Warning')),
        ('error', _('Error')),
        ('critical', _('Critical')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('acknowledged', _('Acknowledged')),
        ('resolved', _('Resolved')),
        ('suppressed', _('Suppressed')),
    ]
    
    # Alert identification
    alert_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        verbose_name=_('Alert ID')
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name=_('Alert Title')
    )
    
    description = models.TextField(
        verbose_name=_('Alert Description')
    )
    
    # Alert classification
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_LEVELS,
        verbose_name=_('Severity Level')
    )
    
    category = models.CharField(
        max_length=50,
        verbose_name=_('Alert Category'),
        help_text=_('Category like database, redis, celery, etc.')
    )
    
    # Status and timing
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name=_('Status')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    
    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Acknowledged At')
    )
    
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Resolved At')
    )
    
    # Alert details
    source_metric = models.ForeignKey(
        SystemHealthMetric,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Source Metric'),
        help_text=_('Metric that triggered this alert')
    )
    
    threshold_value = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Threshold Value'),
        help_text=_('Threshold value that was exceeded')
    )
    
    current_value = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Current Value'),
        help_text=_('Current value when alert was triggered')
    )
    
    # Notification tracking
    notifications_sent = models.JSONField(
        default=list,
        verbose_name=_('Notifications Sent'),
        help_text=_('List of notifications sent for this alert')
    )
    
    # Resolution information
    acknowledged_by_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Acknowledged By ID')
    )
    
    acknowledged_by_username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Acknowledged By Username')
    )
    
    resolution_notes = models.TextField(
        blank=True,
        verbose_name=_('Resolution Notes')
    )
    
    class Meta:
        verbose_name = _('System Health Alert')
        verbose_name_plural = _('System Health Alerts')
        db_table = 'admin_system_health_alert'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'severity', 'created_at']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['alert_id']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_severity_display()})"
    
    def acknowledge(self, user_id, username, notes=''):
        """Acknowledge the alert."""
        self.status = 'acknowledged'
        self.acknowledged_at = timezone.now()
        self.acknowledged_by_id = user_id
        self.acknowledged_by_username = username
        if notes:
            self.resolution_notes = notes
        self.save(update_fields=[
            'status', 'acknowledged_at', 'acknowledged_by_id', 
            'acknowledged_by_username', 'resolution_notes'
        ])
    
    def resolve(self, user_id, username, notes=''):
        """Resolve the alert."""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.acknowledged_by_id = user_id
        self.acknowledged_by_username = username
        if notes:
            self.resolution_notes = notes
        self.save(update_fields=[
            'status', 'resolved_at', 'acknowledged_by_id', 
            'acknowledged_by_username', 'resolution_notes'
        ])
    
    def add_notification(self, notification_type, recipient, status='sent'):
        """Add a notification record."""
        notification = {
            'timestamp': timezone.now().isoformat(),
            'type': notification_type,
            'recipient': recipient,
            'status': status
        }
        self.notifications_sent.append(notification)
        if self.pk:
            self.save(update_fields=['notifications_sent'])


# RBAC Models for Super Admin Access Control

class SuperAdminPermission(models.Model):
    """
    Permission model for super admin role-based access control.
    Defines granular permissions for different sections of the super admin panel.
    """
    SECTION_CHOICES = [
        ('dashboard', _('Dashboard')),
        ('tenants', _('Tenant Management')),
        ('users', _('User Management')),
        ('billing', _('Billing & Subscriptions')),
        ('security', _('Security & Audit')),
        ('settings', _('System Settings')),
        ('backup', _('Backup Management')),
        ('monitoring', _('System Monitoring')),
        ('reports', _('Reports & Analytics')),
        ('integrations', _('Integrations & API')),
    ]
    
    ACTION_CHOICES = [
        ('view', _('View')),
        ('create', _('Create')),
        ('edit', _('Edit')),
        ('delete', _('Delete')),
        ('export', _('Export')),
        ('import', _('Import')),
        ('manage', _('Full Management')),
    ]
    
    # Permission identification
    codename = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Permission Codename'),
        help_text=_('Unique identifier for this permission (e.g., "tenants.view", "security.manage")')
    )
    
    name = models.CharField(
        max_length=255,
        verbose_name=_('Permission Name'),
        help_text=_('Human-readable permission name')
    )
    
    name_persian = models.CharField(
        max_length=255,
        verbose_name=_('Persian Permission Name'),
        help_text=_('Persian translation of permission name')
    )
    
    # Permission categorization
    section = models.CharField(
        max_length=50,
        choices=SECTION_CHOICES,
        verbose_name=_('Section'),
        help_text=_('Super admin panel section this permission applies to')
    )
    
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name=_('Action'),
        help_text=_('Type of action this permission allows')
    )
    
    # Permission details
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Detailed description of what this permission allows')
    )
    
    description_persian = models.TextField(
        blank=True,
        verbose_name=_('Persian Description'),
        help_text=_('Persian description of what this permission allows')
    )
    
    # Permission metadata
    is_dangerous = models.BooleanField(
        default=False,
        verbose_name=_('Is Dangerous'),
        help_text=_('Mark as dangerous permission requiring extra confirmation')
    )
    
    requires_2fa = models.BooleanField(
        default=False,
        verbose_name=_('Requires 2FA'),
        help_text=_('Requires two-factor authentication to use this permission')
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Created By ID'),
        help_text=_('ID of the super admin who created this permission')
    )
    
    created_by_username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Created By Username'),
        help_text=_('Username of the super admin who created this permission')
    )
    
    class Meta:
        verbose_name = _('Super Admin Permission')
        verbose_name_plural = _('Super Admin Permissions')
        db_table = 'admin_panel_super_admin_permission'
        ordering = ['section', 'action', 'name']
        indexes = [
            models.Index(fields=['codename']),
            models.Index(fields=['section', 'action']),
            models.Index(fields=['is_active']),
        ]
        unique_together = [['section', 'action', 'codename']]
    
    def __str__(self):
        return f"{self.name} ({self.codename})"
    
    @property
    def display_name(self):
        """Return Persian name if available, otherwise English name."""
        return self.name_persian or self.name
    
    @property
    def display_description(self):
        """Return Persian description if available, otherwise English description."""
        return self.description_persian or self.description
    
    def clean(self):
        """Validate permission data."""
        super().clean()
        
        # Ensure codename follows convention: section.action
        if '.' not in self.codename:
            raise ValidationError(_('Permission codename must follow format: section.action'))
        
        # Validate codename matches section and action
        parts = self.codename.split('.')
        if len(parts) != 2:
            raise ValidationError(_('Permission codename must have exactly one dot separator'))
        
        section_code, action_code = parts
        if section_code != self.section:
            raise ValidationError(_('Permission codename section must match selected section'))


class SuperAdminRole(models.Model):
    """
    Role model for super admin role-based access control.
    Groups permissions together for easier management.
    """
    ROLE_TYPES = [
        ('system', _('System Role')),
        ('custom', _('Custom Role')),
    ]
    
    # Role identification
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Role Name'),
        help_text=_('Unique role name (e.g., "Security Manager", "Billing Admin")')
    )
    
    name_persian = models.CharField(
        max_length=100,
        verbose_name=_('Persian Role Name'),
        help_text=_('Persian translation of role name')
    )
    
    # Role details
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Detailed description of this role and its responsibilities')
    )
    
    description_persian = models.TextField(
        blank=True,
        verbose_name=_('Persian Description'),
        help_text=_('Persian description of this role and its responsibilities')
    )
    
    # Role type and permissions
    role_type = models.CharField(
        max_length=20,
        choices=ROLE_TYPES,
        default='custom',
        verbose_name=_('Role Type'),
        help_text=_('System roles cannot be deleted, custom roles can be modified')
    )
    
    permissions = models.ManyToManyField(
        SuperAdminPermission,
        blank=True,
        related_name='roles',
        verbose_name=_('Permissions'),
        help_text=_('Permissions granted to users with this role')
    )
    
    # Role hierarchy
    parent_role = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child_roles',
        verbose_name=_('Parent Role'),
        help_text=_('Parent role for permission inheritance')
    )
    
    # Role settings
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    
    is_default = models.BooleanField(
        default=False,
        verbose_name=_('Is Default Role'),
        help_text=_('Automatically assign this role to new super admins')
    )
    
    max_users = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Maximum Users'),
        help_text=_('Maximum number of users that can have this role (optional)')
    )
    
    # Security settings
    requires_2fa = models.BooleanField(
        default=False,
        verbose_name=_('Requires 2FA'),
        help_text=_('Users with this role must have 2FA enabled')
    )
    
    session_timeout_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Session Timeout (Minutes)'),
        help_text=_('Custom session timeout for users with this role')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Created By ID'),
        help_text=_('ID of the super admin who created this role')
    )
    
    created_by_username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Created By Username'),
        help_text=_('Username of the super admin who created this role')
    )
    
    class Meta:
        verbose_name = _('Super Admin Role')
        verbose_name_plural = _('Super Admin Roles')
        db_table = 'admin_panel_super_admin_role'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['role_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_default']),
        ]
    
    def __str__(self):
        return f"{self.name_persian or self.name}"
    
    @property
    def display_name(self):
        """Return Persian name if available, otherwise English name."""
        return self.name_persian or self.name
    
    @property
    def display_description(self):
        """Return Persian description if available, otherwise English description."""
        return self.description_persian or self.description
    
    @property
    def user_count(self):
        """Get number of users assigned to this role."""
        return self.user_roles.filter(is_active=True).count()
    
    @property
    def is_at_max_capacity(self):
        """Check if role has reached maximum user limit."""
        if not self.max_users:
            return False
        return self.user_count >= self.max_users
    
    def get_all_permissions(self):
        """Get all permissions including inherited from parent roles."""
        permissions = set(self.permissions.filter(is_active=True))
        
        # Add permissions from parent role
        if self.parent_role:
            permissions.update(self.parent_role.get_all_permissions())
        
        return permissions
    
    def has_permission(self, permission_codename):
        """Check if role has specific permission."""
        all_permissions = self.get_all_permissions()
        return any(perm.codename == permission_codename for perm in all_permissions)
    
    def get_sections_access(self):
        """Get list of sections this role can access."""
        all_permissions = self.get_all_permissions()
        return list(set(perm.section for perm in all_permissions))
    
    def clean(self):
        """Validate role data."""
        super().clean()
        
        # Prevent circular parent relationships
        if self.parent_role:
            current = self.parent_role
            while current:
                if current == self:
                    raise ValidationError(_('Role cannot be its own parent (circular reference)'))
                current = current.parent_role
        
        # Validate max users
        if self.max_users and self.max_users < 1:
            raise ValidationError(_('Maximum users must be at least 1'))
    
    def save(self, *args, **kwargs):
        """Override save to handle default role logic."""
        # If this is being set as default, unset other default roles
        if self.is_default:
            SuperAdminRole.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        
        super().save(*args, **kwargs)


class SuperAdminUserRole(models.Model):
    """
    Through model for many-to-many relationship between SuperAdmin users and roles.
    Provides additional metadata about role assignments.
    """
    # User and role relationship
    user_id = models.IntegerField(
        verbose_name=_('Super Admin User ID'),
        help_text=_('ID of the SuperAdmin user')
    )
    
    user_username = models.CharField(
        max_length=150,
        verbose_name=_('Username'),
        help_text=_('Username of the SuperAdmin user for easier querying')
    )
    
    role = models.ForeignKey(
        SuperAdminRole,
        on_delete=models.CASCADE,
        related_name='user_roles',
        verbose_name=_('Role')
    )
    
    # Assignment details
    assigned_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Assigned At')
    )
    
    assigned_by_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Assigned By ID'),
        help_text=_('ID of the super admin who assigned this role')
    )
    
    assigned_by_username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Assigned By Username'),
        help_text=_('Username of the super admin who assigned this role')
    )
    
    # Assignment status
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Expires At'),
        help_text=_('Optional expiration date for temporary role assignments')
    )
    
    # Assignment notes
    assignment_reason = models.TextField(
        blank=True,
        verbose_name=_('Assignment Reason'),
        help_text=_('Reason for assigning this role to the user')
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes'),
        help_text=_('Additional notes about this role assignment')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Super Admin User Role')
        verbose_name_plural = _('Super Admin User Roles')
        db_table = 'admin_panel_super_admin_user_role'
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['user_id', 'is_active']),
            models.Index(fields=['role', 'is_active']),
            models.Index(fields=['assigned_at']),
            models.Index(fields=['expires_at']),
        ]
        unique_together = [['user_id', 'role']]
    
    def __str__(self):
        return f"{self.user_username} -> {self.role.name}"
    
    @property
    def is_expired(self):
        """Check if role assignment has expired."""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def days_until_expiry(self):
        """Get number of days until role expires."""
        if not self.expires_at:
            return None
        
        delta = self.expires_at - timezone.now()
        return delta.days if delta.days > 0 else 0
    
    def extend_expiry(self, days):
        """Extend role expiry by specified number of days."""
        if self.expires_at:
            self.expires_at += timezone.timedelta(days=days)
        else:
            self.expires_at = timezone.now() + timezone.timedelta(days=days)
        self.save(update_fields=['expires_at'])
    
    def revoke(self, revoked_by_id=None, revoked_by_username='', reason=''):
        """Revoke the role assignment."""
        self.is_active = False
        if reason:
            if self.notes:
                self.notes += f"\nRevoked: {reason}"
            else:
                self.notes = f"Revoked: {reason}"
        
        self.save(update_fields=['is_active', 'notes'])
        
        # Log the revocation
        from zargar.admin_panel.models import RolePermissionAuditLog
        RolePermissionAuditLog.log_action(
            action='role_revoked',
            object_type='user_role',
            object_id=self.id,
            object_name=f"{self.user_username} -> {self.role.name}",
            performed_by_id=revoked_by_id or 0,
            performed_by_username=revoked_by_username,
            old_values={
                'user_id': self.user_id,
                'username': self.user_username,
                'role_name': self.role.name,
                'is_active': True
            },
            new_values={
                'is_active': False,
                'revocation_reason': reason
            }
        )
    
    def clean(self):
        """Validate role assignment."""
        super().clean()
        
        # Check if role is at maximum capacity
        if self.role.is_at_max_capacity and not self.pk:
            raise ValidationError(
                _('Role "{}" has reached maximum user capacity of {}').format(
                    self.role.name, self.role.max_users
                )
            )
        
        # Validate expiry date
        if self.expires_at and self.expires_at <= timezone.now():
            raise ValidationError(_('Expiry date must be in the future'))
    
    def save(self, *args, **kwargs):
        """Override save to handle automatic expiry."""
        # Auto-deactivate if expired
        if self.is_expired and self.is_active:
            self.is_active = False
        
        super().save(*args, **kwargs)


class RolePermissionAuditLog(models.Model):
    """
    Audit log for role and permission changes.
    Tracks all modifications to roles and permissions for security compliance.
    """
    ACTION_CHOICES = [
        ('role_created', _('Role Created')),
        ('role_updated', _('Role Updated')),
        ('role_deleted', _('Role Deleted')),
        ('permission_created', _('Permission Created')),
        ('permission_updated', _('Permission Updated')),
        ('permission_deleted', _('Permission Deleted')),
        ('role_assigned', _('Role Assigned to User')),
        ('role_revoked', _('Role Revoked from User')),
        ('permission_granted', _('Permission Granted to Role')),
        ('permission_removed', _('Permission Removed from Role')),
    ]
    
    # Action details
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        verbose_name=_('Action')
    )
    
    # Target object information
    object_type = models.CharField(
        max_length=50,
        verbose_name=_('Object Type'),
        help_text=_('Type of object that was modified (role, permission, assignment)')
    )
    
    object_id = models.PositiveIntegerField(
        verbose_name=_('Object ID'),
        help_text=_('ID of the object that was modified')
    )
    
    object_name = models.CharField(
        max_length=200,
        verbose_name=_('Object Name'),
        help_text=_('Name of the object that was modified')
    )
    
    # User who performed the action
    performed_by_id = models.IntegerField(
        verbose_name=_('Performed By ID'),
        help_text=_('ID of the super admin who performed this action')
    )
    
    performed_by_username = models.CharField(
        max_length=150,
        verbose_name=_('Performed By Username'),
        help_text=_('Username of the super admin who performed this action')
    )
    
    # Change details
    old_values = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Old Values'),
        help_text=_('Previous values before the change')
    )
    
    new_values = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('New Values'),
        help_text=_('New values after the change')
    )
    
    # Additional context
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Additional Details'),
        help_text=_('Additional context about the change')
    )
    
    # Request information
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP Address')
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )
    
    # Timing
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Timestamp')
    )
    
    class Meta:
        verbose_name = _('Role Permission Audit Log')
        verbose_name_plural = _('Role Permission Audit Logs')
        db_table = 'admin_panel_role_permission_audit_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['object_type', 'object_id']),
            models.Index(fields=['performed_by_id', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.performed_by_username} - {self.get_action_display()} - {self.object_name}"
    
    @classmethod
    def log_action(cls, action, object_type, object_id, object_name, 
                   performed_by_id, performed_by_username, 
                   old_values=None, new_values=None, details=None,
                   ip_address=None, user_agent=''):
        """
        Convenience method to create audit log entries.
        """
        return cls.objects.create(
            action=action,
            object_type=object_type,
            object_id=object_id,
            object_name=object_name,
            performed_by_id=performed_by_id,
            performed_by_username=performed_by_username,
            old_values=old_values or {},
            new_values=new_values or {},
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )


class ExternalServiceConfiguration(models.Model):
    """
    Model for storing external service integration configurations.
    """
    SERVICE_TYPES = [
        ('gold_price_api', _('Gold Price API')),
        ('payment_gateway', _('Payment Gateway')),
        ('sms_service', _('SMS Service')),
        ('email_service', _('Email Service')),
        ('backup_storage', _('Backup Storage')),
        ('analytics_service', _('Analytics Service')),
        ('notification_service', _('Notification Service')),
        ('custom', _('Custom Service')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('inactive', _('Inactive')),
        ('testing', _('Testing')),
        ('error', _('Error')),
        ('maintenance', _('Maintenance')),
    ]
    
    AUTHENTICATION_TYPES = [
        ('api_key', _('API Key')),
        ('bearer_token', _('Bearer Token')),
        ('basic_auth', _('Basic Authentication')),
        ('oauth2', _('OAuth 2.0')),
        ('custom_header', _('Custom Header')),
        ('none', _('No Authentication')),
    ]
    
    # Service identification
    service_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        verbose_name=_('Service ID'),
        help_text=_('Unique identifier for this service configuration')
    )
    
    name = models.CharField(
        max_length=200,
        verbose_name=_('Service Name'),
        help_text=_('Human-readable name for this service')
    )
    
    service_type = models.CharField(
        max_length=50,
        choices=SERVICE_TYPES,
        verbose_name=_('Service Type')
    )
    
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Description of what this service does')
    )
    
    # Connection settings
    base_url = models.URLField(
        verbose_name=_('Base URL'),
        help_text=_('Base URL for the external service API')
    )
    
    timeout_seconds = models.PositiveIntegerField(
        default=30,
        verbose_name=_('Timeout (seconds)'),
        help_text=_('Request timeout in seconds')
    )
    
    max_retries = models.PositiveIntegerField(
        default=3,
        verbose_name=_('Max Retries'),
        help_text=_('Maximum number of retry attempts')
    )
    
    # Authentication
    authentication_type = models.CharField(
        max_length=20,
        choices=AUTHENTICATION_TYPES,
        default='api_key',
        verbose_name=_('Authentication Type')
    )
    
    api_key = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('API Key'),
        help_text=_('API key for authentication (encrypted)')
    )
    
    username = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Username'),
        help_text=_('Username for basic authentication')
    )
    
    password = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Password'),
        help_text=_('Password for basic authentication (encrypted)')
    )
    
    oauth_client_id = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('OAuth Client ID')
    )
    
    oauth_client_secret = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('OAuth Client Secret'),
        help_text=_('OAuth client secret (encrypted)')
    )
    
    custom_headers = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Custom Headers'),
        help_text=_('Additional headers to send with requests')
    )
    
    # Rate limiting
    rate_limit_requests = models.PositiveIntegerField(
        default=100,
        verbose_name=_('Rate Limit (requests)'),
        help_text=_('Maximum requests per time window')
    )
    
    rate_limit_window_seconds = models.PositiveIntegerField(
        default=3600,
        verbose_name=_('Rate Limit Window (seconds)'),
        help_text=_('Time window for rate limiting in seconds')
    )
    
    # Status and health
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='inactive',
        verbose_name=_('Status')
    )
    
    is_enabled = models.BooleanField(
        default=True,
        verbose_name=_('Is Enabled'),
        help_text=_('Whether this service is enabled for use')
    )
    
    last_health_check = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last Health Check')
    )
    
    health_check_interval_minutes = models.PositiveIntegerField(
        default=15,
        verbose_name=_('Health Check Interval (minutes)'),
        help_text=_('How often to check service health')
    )
    
    last_error_message = models.TextField(
        blank=True,
        verbose_name=_('Last Error Message')
    )
    
    last_error_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last Error Time')
    )
    
    # Statistics
    total_requests = models.BigIntegerField(
        default=0,
        verbose_name=_('Total Requests'),
        help_text=_('Total number of requests made to this service')
    )
    
    successful_requests = models.BigIntegerField(
        default=0,
        verbose_name=_('Successful Requests')
    )
    
    failed_requests = models.BigIntegerField(
        default=0,
        verbose_name=_('Failed Requests')
    )
    
    average_response_time_ms = models.FloatField(
        default=0.0,
        verbose_name=_('Average Response Time (ms)')
    )
    
    # Configuration
    configuration = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Service Configuration'),
        help_text=_('Service-specific configuration parameters')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Created By ID')
    )
    
    created_by_username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Created By Username')
    )
    
    class Meta:
        verbose_name = _('External Service Configuration')
        verbose_name_plural = _('External Service Configurations')
        db_table = 'admin_external_service_config'
        ordering = ['name']
        indexes = [
            models.Index(fields=['service_type', 'status']),
            models.Index(fields=['is_enabled', 'status']),
            models.Index(fields=['last_health_check']),
            models.Index(fields=['service_id']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_service_type_display()})"
    
    @property
    def is_healthy(self):
        """Check if service is healthy based on last health check."""
        if not self.last_health_check:
            return False
        
        # Consider service unhealthy if no check in 2x the interval
        max_age = timezone.timedelta(minutes=self.health_check_interval_minutes * 2)
        return timezone.now() - self.last_health_check < max_age
    
    @property
    def success_rate(self):
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def failure_rate(self):
        """Calculate failure rate percentage."""
        return 100.0 - self.success_rate
    
    def update_statistics(self, success=True, response_time_ms=None):
        """Update service statistics."""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        if response_time_ms is not None:
            # Update average response time using exponential moving average
            alpha = 0.1  # Smoothing factor
            if self.average_response_time_ms == 0:
                self.average_response_time_ms = response_time_ms
            else:
                self.average_response_time_ms = (
                    alpha * response_time_ms + 
                    (1 - alpha) * self.average_response_time_ms
                )
        
        self.save(update_fields=[
            'total_requests', 'successful_requests', 'failed_requests',
            'average_response_time_ms'
        ])
    
    def record_error(self, error_message):
        """Record an error for this service."""
        self.last_error_message = error_message
        self.last_error_time = timezone.now()
        self.status = 'error'
        self.save(update_fields=['last_error_message', 'last_error_time', 'status'])
    
    def mark_healthy(self):
        """Mark service as healthy after successful health check."""
        self.last_health_check = timezone.now()
        if self.status == 'error':
            self.status = 'active'
        self.save(update_fields=['last_health_check', 'status'])
    
    def get_masked_credentials(self):
        """Get credentials with sensitive data masked for display."""
        masked = {}
        if self.api_key:
            masked['api_key'] = f"{'*' * (len(self.api_key) - 4)}{self.api_key[-4:]}"
        if self.password:
            masked['password'] = '*' * 8
        if self.oauth_client_secret:
            masked['oauth_client_secret'] = f"{'*' * (len(self.oauth_client_secret) - 4)}{self.oauth_client_secret[-4:]}"
        return masked


class APIRateLimitConfiguration(models.Model):
    """
    Model for configuring API rate limits for different endpoints and users.
    """
    LIMIT_TYPES = [
        ('global', _('Global Limit')),
        ('per_user', _('Per User Limit')),
        ('per_ip', _('Per IP Limit')),
        ('per_endpoint', _('Per Endpoint Limit')),
        ('per_tenant', _('Per Tenant Limit')),
    ]
    
    TIME_WINDOWS = [
        (60, _('Per Minute')),
        (3600, _('Per Hour')),
        (86400, _('Per Day')),
        (604800, _('Per Week')),
        (2592000, _('Per Month')),
    ]
    
    # Configuration identification
    config_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        verbose_name=_('Configuration ID')
    )
    
    name = models.CharField(
        max_length=200,
        verbose_name=_('Configuration Name'),
        help_text=_('Human-readable name for this rate limit configuration')
    )
    
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    
    # Rate limit settings
    limit_type = models.CharField(
        max_length=20,
        choices=LIMIT_TYPES,
        verbose_name=_('Limit Type')
    )
    
    endpoint_pattern = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Endpoint Pattern'),
        help_text=_('URL pattern to match (regex supported)')
    )
    
    requests_limit = models.PositiveIntegerField(
        verbose_name=_('Requests Limit'),
        help_text=_('Maximum number of requests allowed')
    )
    
    time_window_seconds = models.PositiveIntegerField(
        choices=TIME_WINDOWS,
        verbose_name=_('Time Window'),
        help_text=_('Time window for the rate limit')
    )
    
    # Enforcement settings
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    
    block_duration_seconds = models.PositiveIntegerField(
        default=3600,
        verbose_name=_('Block Duration (seconds)'),
        help_text=_('How long to block after limit exceeded')
    )
    
    warning_threshold_percentage = models.PositiveIntegerField(
        default=80,
        verbose_name=_('Warning Threshold (%)'),
        help_text=_('Percentage of limit to trigger warning')
    )
    
    # Response settings
    custom_error_message = models.TextField(
        blank=True,
        verbose_name=_('Custom Error Message'),
        help_text=_('Custom message to show when rate limit exceeded')
    )
    
    custom_headers = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Custom Headers'),
        help_text=_('Additional headers to include in rate limit responses')
    )
    
    # Exemptions
    exempt_user_ids = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Exempt User IDs'),
        help_text=_('List of user IDs exempt from this rate limit')
    )
    
    exempt_ip_addresses = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Exempt IP Addresses'),
        help_text=_('List of IP addresses exempt from this rate limit')
    )
    
    # Statistics
    total_requests_blocked = models.BigIntegerField(
        default=0,
        verbose_name=_('Total Requests Blocked')
    )
    
    total_warnings_issued = models.BigIntegerField(
        default=0,
        verbose_name=_('Total Warnings Issued')
    )
    
    last_triggered = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last Triggered')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Created By ID')
    )
    
    created_by_username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Created By Username')
    )
    
    class Meta:
        verbose_name = _('API Rate Limit Configuration')
        verbose_name_plural = _('API Rate Limit Configurations')
        db_table = 'admin_api_rate_limit_config'
        ordering = ['name']
        indexes = [
            models.Index(fields=['limit_type', 'is_active']),
            models.Index(fields=['endpoint_pattern']),
            models.Index(fields=['is_active', 'last_triggered']),
            models.Index(fields=['config_id']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.requests_limit}/{self.get_time_window_seconds_display()})"
    
    @property
    def time_window_display(self):
        """Get human-readable time window."""
        return dict(self.TIME_WINDOWS).get(self.time_window_seconds, f"{self.time_window_seconds}s")
    
    def is_exempt_user(self, user_id):
        """Check if user is exempt from this rate limit."""
        return user_id in self.exempt_user_ids
    
    def is_exempt_ip(self, ip_address):
        """Check if IP address is exempt from this rate limit."""
        return ip_address in self.exempt_ip_addresses
    
    def record_block(self):
        """Record that this rate limit blocked a request."""
        self.total_requests_blocked += 1
        self.last_triggered = timezone.now()
        self.save(update_fields=['total_requests_blocked', 'last_triggered'])
    
    def record_warning(self):
        """Record that this rate limit issued a warning."""
        self.total_warnings_issued += 1
        self.save(update_fields=['total_warnings_issued'])


class IntegrationHealthCheck(models.Model):
    """
    Model for storing integration health check results.
    """
    CHECK_TYPES = [
        ('connectivity', _('Connectivity Check')),
        ('authentication', _('Authentication Check')),
        ('functionality', _('Functionality Check')),
        ('performance', _('Performance Check')),
        ('data_integrity', _('Data Integrity Check')),
    ]
    
    STATUS_CHOICES = [
        ('healthy', _('Healthy')),
        ('warning', _('Warning')),
        ('critical', _('Critical')),
        ('unknown', _('Unknown')),
    ]
    
    # Check identification
    check_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        verbose_name=_('Check ID')
    )
    
    service = models.ForeignKey(
        ExternalServiceConfiguration,
        on_delete=models.CASCADE,
        related_name='health_checks',
        verbose_name=_('Service')
    )
    
    check_type = models.CharField(
        max_length=20,
        choices=CHECK_TYPES,
        verbose_name=_('Check Type')
    )
    
    # Check results
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name=_('Status')
    )
    
    response_time_ms = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Response Time (ms)')
    )
    
    success = models.BooleanField(
        verbose_name=_('Success'),
        help_text=_('Whether the health check was successful')
    )
    
    # Check details
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Check Details'),
        help_text=_('Detailed information about the health check')
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Error Message')
    )
    
    warnings = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Warnings'),
        help_text=_('List of warning messages from the health check')
    )
    
    # Metrics
    metrics = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Metrics'),
        help_text=_('Performance and other metrics from the health check')
    )
    
    # Timing
    checked_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Checked At')
    )
    
    next_check_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Next Check At')
    )
    
    class Meta:
        verbose_name = _('Integration Health Check')
        verbose_name_plural = _('Integration Health Checks')
        db_table = 'admin_integration_health_check'
        ordering = ['-checked_at']
        indexes = [
            models.Index(fields=['service', 'checked_at']),
            models.Index(fields=['status', 'checked_at']),
            models.Index(fields=['check_type', 'status']),
            models.Index(fields=['next_check_at']),
            models.Index(fields=['check_id']),
        ]
    
    def __str__(self):
        return f"{self.service.name} - {self.get_check_type_display()} ({self.get_status_display()})"
    
    @property
    def is_overdue(self):
        """Check if the next health check is overdue."""
        if not self.next_check_at:
            return False
        return timezone.now() > self.next_check_at
    
    def calculate_next_check(self):
        """Calculate when the next health check should run."""
        interval = timezone.timedelta(minutes=self.service.health_check_interval_minutes)
        self.next_check_at = self.checked_at + interval
        self.save(update_fields=['next_check_at'])