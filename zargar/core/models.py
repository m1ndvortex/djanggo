"""
Core models for zargar project.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom User model with tenant awareness and Persian support.
    """
    ROLE_CHOICES = [
        ('owner', _('Owner')),
        ('accountant', _('Accountant')),
        ('salesperson', _('Salesperson')),
        ('super_admin', _('Super Admin')),
    ]
    
    THEME_CHOICES = [
        ('light', _('Light Mode')),
        ('dark', _('Dark Mode')),
    ]
    
    # Additional fields
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        verbose_name=_('Phone Number'),
        help_text=_('Persian phone number format: 09123456789')
    )
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='salesperson',
        verbose_name=_('Role')
    )
    
    # 2FA settings
    is_2fa_enabled = models.BooleanField(
        default=False,
        verbose_name=_('Two-Factor Authentication Enabled')
    )
    
    # Theme preference
    theme_preference = models.CharField(
        max_length=10,
        choices=THEME_CHOICES,
        default='light',
        verbose_name=_('Theme Preference')
    )
    
    # Persian name fields
    persian_first_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Persian First Name')
    )
    
    persian_last_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Persian Last Name')
    )
    
    # Tenant relationship (will be set by tenant-specific models)
    tenant_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Tenant ID'),
        help_text=_('Associated tenant schema name')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        db_table = 'core_user'
    
    def __str__(self):
        if self.persian_first_name and self.persian_last_name:
            return f"{self.persian_first_name} {self.persian_last_name}"
        return self.username
    
    @property
    def full_persian_name(self):
        """Return full Persian name if available."""
        if self.persian_first_name and self.persian_last_name:
            return f"{self.persian_first_name} {self.persian_last_name}"
        return self.get_full_name() or self.username
    
    @property
    def is_tenant_owner(self):
        """Check if user is a tenant owner."""
        return self.role == 'owner'
    
    @property
    def is_super_admin(self):
        """Check if user is a super admin."""
        return self.role == 'super_admin' or self.is_superuser
    
    def can_access_accounting(self):
        """Check if user can access accounting features."""
        return self.role in ['owner', 'accountant']
    
    def can_access_pos(self):
        """Check if user can access POS features."""
        return self.role in ['owner', 'salesperson', 'accountant']
    
    def can_manage_users(self):
        """Check if user can manage other users."""
        return self.role == 'owner'


class TenantAwareModel(models.Model):
    """
    Abstract base model for tenant-aware models.
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Created By')
    )
    
    class Meta:
        abstract = True


class SystemSettings(models.Model):
    """
    System-wide settings for the platform.
    """
    key = models.CharField(max_length=100, unique=True, verbose_name=_('Setting Key'))
    value = models.TextField(verbose_name=_('Setting Value'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('System Setting')
        verbose_name_plural = _('System Settings')
        db_table = 'core_system_settings'
    
    def __str__(self):
        return f"{self.key}: {self.value[:50]}"


class AuditLog(models.Model):
    """
    Audit log for tracking system activities.
    """
    ACTION_CHOICES = [
        ('create', _('Create')),
        ('update', _('Update')),
        ('delete', _('Delete')),
        ('login', _('Login')),
        ('logout', _('Logout')),
        ('tenant_created', _('Tenant Created')),
        ('tenant_suspended', _('Tenant Suspended')),
        ('impersonation_start', _('Impersonation Started')),
        ('impersonation_end', _('Impersonation Ended')),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('User')
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        verbose_name=_('Action')
    )
    model_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Model Name')
    )
    object_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Object ID')
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Details')
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
    tenant_schema = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Tenant Schema')
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('Timestamp'))
    
    class Meta:
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        db_table = 'core_audit_log'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"