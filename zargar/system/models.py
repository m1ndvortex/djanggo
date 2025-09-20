"""
System-wide models for the ZARGAR jewelry SaaS platform.
These models exist in the public schema and track system-wide operations.
"""
import os
import hashlib
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django_tenants.utils import get_tenant_model


class BackupRecord(models.Model):
    """
    Model to track all backup operations across the system.
    This model exists in the public schema to track all tenant backups.
    """
    BACKUP_TYPE_CHOICES = [
        ('full_system', _('Full System Backup')),
        ('tenant_only', _('Single Tenant Backup')),
        ('configuration', _('Configuration Backup')),
        ('snapshot', _('Temporary Snapshot')),
    ]
    
    BACKUP_STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('corrupted', _('Corrupted')),
        ('expired', _('Expired')),
    ]
    
    BACKUP_FREQUENCY_CHOICES = [
        ('daily', _('Daily')),
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
        ('manual', _('Manual')),
        ('snapshot', _('Snapshot')),
    ]
    
    # Basic backup information
    backup_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Backup ID'),
        help_text=_('Unique identifier for this backup')
    )
    
    backup_type = models.CharField(
        max_length=20,
        choices=BACKUP_TYPE_CHOICES,
        verbose_name=_('Backup Type')
    )
    
    status = models.CharField(
        max_length=20,
        choices=BACKUP_STATUS_CHOICES,
        default='pending',
        verbose_name=_('Status')
    )
    
    frequency = models.CharField(
        max_length=20,
        choices=BACKUP_FREQUENCY_CHOICES,
        default='manual',
        verbose_name=_('Frequency')
    )
    
    # Tenant information (null for full system backups)
    tenant_schema = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Tenant Schema'),
        help_text=_('Schema name for tenant-specific backups')
    )
    
    tenant_domain = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Tenant Domain'),
        help_text=_('Domain name for tenant identification')
    )
    
    # Backup file information
    file_path = models.CharField(
        max_length=500,
        verbose_name=_('File Path'),
        help_text=_('Path to backup file in storage')
    )
    
    file_size = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name=_('File Size (bytes)'),
        help_text=_('Size of backup file in bytes')
    )
    
    # Encryption and integrity
    is_encrypted = models.BooleanField(
        default=True,
        verbose_name=_('Is Encrypted'),
        help_text=_('Whether the backup file is encrypted')
    )
    
    encryption_key_hash = models.CharField(
        max_length=128,
        blank=True,
        verbose_name=_('Encryption Key Hash'),
        help_text=_('SHA-256 hash of encryption key for verification')
    )
    
    file_hash = models.CharField(
        max_length=128,
        blank=True,
        verbose_name=_('File Hash'),
        help_text=_('SHA-256 hash of backup file for integrity verification')
    )
    
    # Storage information
    stored_in_primary = models.BooleanField(
        default=False,
        verbose_name=_('Stored in Primary Storage'),
        help_text=_('Whether backup is stored in Cloudflare R2')
    )
    
    stored_in_secondary = models.BooleanField(
        default=False,
        verbose_name=_('Stored in Secondary Storage'),
        help_text=_('Whether backup is stored in Backblaze B2')
    )
    
    # Timing information
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
    
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Expires At'),
        help_text=_('When this backup should be automatically deleted')
    )
    
    # Metadata and error information
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Metadata'),
        help_text=_('Additional backup metadata and statistics')
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Error Message'),
        help_text=_('Error details if backup failed')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Created By'),
        help_text=_('User or system that initiated the backup')
    )
    
    class Meta:
        verbose_name = _('Backup Record')
        verbose_name_plural = _('Backup Records')
        db_table = 'system_backup_record'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['backup_type', 'status']),
            models.Index(fields=['tenant_schema']),
            models.Index(fields=['created_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.backup_id} ({self.backup_type}) - {self.status}"
    
    @property
    def duration(self):
        """Calculate backup duration if completed."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def is_expired(self):
        """Check if backup has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def is_redundant(self):
        """Check if backup is stored redundantly."""
        return self.stored_in_primary and self.stored_in_secondary
    
    def mark_started(self):
        """Mark backup as started."""
        self.status = 'in_progress'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def mark_completed(self, file_size=None, file_hash=None):
        """Mark backup as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        
        if file_size:
            self.file_size = file_size
        
        if file_hash:
            self.file_hash = file_hash
        
        update_fields = ['status', 'completed_at']
        if file_size:
            update_fields.append('file_size')
        if file_hash:
            update_fields.append('file_hash')
        
        self.save(update_fields=update_fields)
    
    def mark_failed(self, error_message):
        """Mark backup as failed with error message."""
        self.status = 'failed'
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at'])
    
    def verify_integrity(self, file_content=None):
        """
        Verify backup file integrity using stored hash.
        
        Args:
            file_content (bytes): File content to verify, if None will download from storage
            
        Returns:
            bool: True if integrity check passes
        """
        if not self.file_hash:
            return False
        
        if file_content is None:
            # Download file content for verification
            from zargar.core.storage_utils import storage_manager
            file_content = storage_manager.download_backup_file(self.file_path)
            
            if file_content is None:
                return False
        
        # Calculate hash of current file content
        calculated_hash = hashlib.sha256(file_content).hexdigest()
        
        # Compare with stored hash
        return calculated_hash == self.file_hash
    
    def update_storage_status(self, primary_stored=None, secondary_stored=None):
        """Update storage status flags."""
        update_fields = []
        
        if primary_stored is not None:
            self.stored_in_primary = primary_stored
            update_fields.append('stored_in_primary')
        
        if secondary_stored is not None:
            self.stored_in_secondary = secondary_stored
            update_fields.append('stored_in_secondary')
        
        if update_fields:
            self.save(update_fields=update_fields)


class BackupSchedule(models.Model):
    """
    Model to manage backup schedules and automation.
    This model exists in the public schema to manage system-wide backup schedules.
    """
    SCHEDULE_TYPE_CHOICES = [
        ('full_system', _('Full System Backup')),
        ('tenant_only', _('Single Tenant Backup')),
        ('configuration', _('Configuration Backup')),
    ]
    
    FREQUENCY_CHOICES = [
        ('daily', _('Daily')),
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
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
    
    # Schedule configuration
    schedule_type = models.CharField(
        max_length=20,
        choices=SCHEDULE_TYPE_CHOICES,
        verbose_name=_('Schedule Type')
    )
    
    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        verbose_name=_('Frequency')
    )
    
    # Timing configuration
    hour = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(23)],
        default=3,
        verbose_name=_('Hour (24h format)'),
        help_text=_('Hour of day to run backup (0-23)')
    )
    
    minute = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(59)],
        default=0,
        verbose_name=_('Minute'),
        help_text=_('Minute of hour to run backup (0-59)')
    )
    
    # For weekly backups
    day_of_week = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        verbose_name=_('Day of Week'),
        help_text=_('Day of week for weekly backups (0=Monday, 6=Sunday)')
    )
    
    # For monthly backups
    day_of_month = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        verbose_name=_('Day of Month'),
        help_text=_('Day of month for monthly backups (1-31)')
    )
    
    # Tenant-specific schedules
    tenant_schema = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Tenant Schema'),
        help_text=_('Schema name for tenant-specific backup schedules')
    )
    
    # Retention policy
    retention_days = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        verbose_name=_('Retention Days'),
        help_text=_('Number of days to keep backups')
    )
    
    # Status and control
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    
    # Execution tracking
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
    
    last_backup_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Last Backup ID'),
        help_text=_('ID of the last backup created by this schedule')
    )
    
    # Statistics
    total_runs = models.IntegerField(
        default=0,
        verbose_name=_('Total Runs')
    )
    
    successful_runs = models.IntegerField(
        default=0,
        verbose_name=_('Successful Runs')
    )
    
    failed_runs = models.IntegerField(
        default=0,
        verbose_name=_('Failed Runs')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Backup Schedule')
        verbose_name_plural = _('Backup Schedules')
        db_table = 'system_backup_schedule'
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'next_run_at']),
            models.Index(fields=['schedule_type']),
            models.Index(fields=['tenant_schema']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.frequency})"
    
    @property
    def success_rate(self):
        """Calculate success rate percentage."""
        if self.total_runs == 0:
            return 0
        return (self.successful_runs / self.total_runs) * 100
    
    def calculate_next_run(self):
        """Calculate the next run time based on frequency and timing settings."""
        from datetime import datetime, timedelta
        import calendar
        
        now = timezone.now()
        
        if self.frequency == 'daily':
            # Next run is tomorrow at the specified time
            next_run = now.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
        
        elif self.frequency == 'weekly':
            # Next run is on the specified day of week at the specified time
            days_ahead = self.day_of_week - now.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            
            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
        
        elif self.frequency == 'monthly':
            # Next run is on the specified day of month at the specified time
            next_month = now.month + 1 if now.month < 12 else 1
            next_year = now.year if now.month < 12 else now.year + 1
            
            # Handle day of month that doesn't exist in target month
            max_day = calendar.monthrange(next_year, next_month)[1]
            target_day = min(self.day_of_month, max_day)
            
            next_run = now.replace(
                year=next_year,
                month=next_month,
                day=target_day,
                hour=self.hour,
                minute=self.minute,
                second=0,
                microsecond=0
            )
        
        else:
            next_run = None
        
        return next_run
    
    def update_next_run(self):
        """Update the next_run_at field."""
        self.next_run_at = self.calculate_next_run()
        self.save(update_fields=['next_run_at'])
    
    def record_run(self, success=True, backup_id=None):
        """Record a backup run execution."""
        self.total_runs += 1
        self.last_run_at = timezone.now()
        
        if success:
            self.successful_runs += 1
        else:
            self.failed_runs += 1
        
        if backup_id:
            self.last_backup_id = backup_id
        
        # Calculate next run
        self.update_next_run()
        
        update_fields = ['total_runs', 'last_run_at', 'next_run_at']
        if success:
            update_fields.append('successful_runs')
        else:
            update_fields.append('failed_runs')
        
        if backup_id:
            update_fields.append('last_backup_id')
        
        self.save(update_fields=update_fields)


class BackupIntegrityCheck(models.Model):
    """
    Model to track backup integrity verification operations.
    """
    CHECK_STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('in_progress', _('In Progress')),
        ('passed', _('Passed')),
        ('failed', _('Failed')),
        ('error', _('Error')),
    ]
    
    # Related backup
    backup_record = models.ForeignKey(
        BackupRecord,
        on_delete=models.CASCADE,
        related_name='integrity_checks',
        verbose_name=_('Backup Record')
    )
    
    # Check details
    check_type = models.CharField(
        max_length=50,
        default='hash_verification',
        verbose_name=_('Check Type'),
        help_text=_('Type of integrity check performed')
    )
    
    status = models.CharField(
        max_length=20,
        choices=CHECK_STATUS_CHOICES,
        default='pending',
        verbose_name=_('Status')
    )
    
    # Timing
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
    
    # Results
    expected_hash = models.CharField(
        max_length=128,
        blank=True,
        verbose_name=_('Expected Hash')
    )
    
    actual_hash = models.CharField(
        max_length=128,
        blank=True,
        verbose_name=_('Actual Hash')
    )
    
    file_size_verified = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name=_('File Size Verified')
    )
    
    # Error information
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Error Message')
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Check Metadata')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Backup Integrity Check')
        verbose_name_plural = _('Backup Integrity Checks')
        db_table = 'system_backup_integrity_check'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['backup_record', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Integrity Check for {self.backup_record.backup_id} - {self.status}"
    
    @property
    def duration(self):
        """Calculate check duration if completed."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    def mark_started(self):
        """Mark integrity check as started."""
        self.status = 'in_progress'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def mark_completed(self, passed=True, actual_hash=None, file_size=None):
        """Mark integrity check as completed."""
        self.status = 'passed' if passed else 'failed'
        self.completed_at = timezone.now()
        
        if actual_hash:
            self.actual_hash = actual_hash
        
        if file_size:
            self.file_size_verified = file_size
        
        update_fields = ['status', 'completed_at']
        if actual_hash:
            update_fields.append('actual_hash')
        if file_size:
            update_fields.append('file_size_verified')
        
        self.save(update_fields=update_fields)
    
    def mark_error(self, error_message):
        """Mark integrity check as error."""
        self.status = 'error'
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at'])