"""
Models for admin panel impersonation system.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
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
