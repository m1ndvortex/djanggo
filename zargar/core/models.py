"""
Core models for zargar project.
"""
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django_tenants.utils import get_tenant_model, connection
from django.core.exceptions import ValidationError
import threading
import pyotp
import qrcode
from io import BytesIO
import base64

# Thread-local storage for tenant context
_thread_locals = threading.local()


def get_current_tenant():
    """Get the current tenant from thread-local storage."""
    return getattr(_thread_locals, 'tenant', None)


def set_current_tenant(tenant):
    """Set the current tenant in thread-local storage."""
    _thread_locals.tenant = tenant


class TenantAwareQuerySet(models.QuerySet):
    """
    Custom QuerySet that automatically filters by current tenant schema.
    """
    
    def __init__(self, model=None, query=None, using=None, hints=None):
        super().__init__(model, query, using, hints)
        self._tenant_filtered = False
    
    def _clone(self):
        """Clone the queryset maintaining tenant filtering state."""
        clone = super()._clone()
        clone._tenant_filtered = self._tenant_filtered
        return clone
    
    def _filter_by_tenant(self):
        """Apply tenant filtering if not already applied."""
        if self._tenant_filtered:
            return self
        
        # Get current tenant from connection
        current_tenant = get_current_tenant()
        if current_tenant and hasattr(current_tenant, 'schema_name'):
            # For tenant-aware models, filtering is handled by django-tenants
            # at the database level through schema isolation
            pass
        
        clone = self._clone()
        clone._tenant_filtered = True
        return clone
    
    def all(self):
        """Return all objects with tenant filtering."""
        return self._filter_by_tenant()
    
    def filter(self, *args, **kwargs):
        """Filter objects with tenant awareness."""
        return super().filter(*args, **kwargs)._filter_by_tenant()
    
    def exclude(self, *args, **kwargs):
        """Exclude objects with tenant awareness."""
        return super().exclude(*args, **kwargs)._filter_by_tenant()


class TenantAwareManager(models.Manager):
    """
    Custom manager that provides tenant-aware querysets.
    """
    
    def get_queryset(self):
        """Return tenant-aware queryset."""
        return TenantAwareQuerySet(self.model, using=self._db)
    
    def create(self, **kwargs):
        """Create object with automatic tenant context."""
        # Add created_by if not provided and user is available
        if 'created_by' not in kwargs:
            current_user = getattr(_thread_locals, 'user', None)
            if current_user and current_user.is_authenticated:
                kwargs['created_by'] = current_user
        
        return super().create(**kwargs)
    
    def bulk_create(self, objs, **kwargs):
        """Bulk create with tenant awareness."""
        current_user = getattr(_thread_locals, 'user', None)
        
        # Set created_by for objects that don't have it
        if current_user and current_user.is_authenticated:
            for obj in objs:
                if hasattr(obj, 'created_by') and not obj.created_by:
                    obj.created_by = current_user
        
        return super().bulk_create(objs, **kwargs)


class TenantAwareUserManager(UserManager):
    """
    Custom user manager that filters users by current tenant.
    """
    
    def get_queryset(self):
        """Filter users by current tenant schema."""
        queryset = super().get_queryset()
        
        # Super admins can see all users
        current_user = getattr(_thread_locals, 'user', None)
        if current_user and current_user.is_superuser:
            return queryset
        
        # Filter by tenant schema for regular users
        current_tenant = get_current_tenant()
        if current_tenant and hasattr(current_tenant, 'schema_name'):
            # In tenant schema, users are automatically isolated
            return queryset
        
        return queryset
    
    def create_user(self, username, email=None, password=None, **extra_fields):
        """Create user in current tenant schema."""
        # Users are automatically tenant-isolated by being in TENANT_APPS
        return super().create_user(username, email, password, **extra_fields)
    
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """Create superuser with current tenant schema."""
        # Superusers can access all tenants, so don't set tenant_schema
        extra_fields.setdefault('role', 'super_admin')
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model with tenant awareness and Persian support.
    This model exists in tenant schemas for perfect isolation.
    """
    ROLE_CHOICES = [
        ('owner', _('Owner')),
        ('accountant', _('Accountant')),
        ('salesperson', _('Salesperson')),
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
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Use custom manager
    objects = TenantAwareUserManager()
    
    # Override groups and user_permissions to avoid conflicts with SuperAdmin
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="tenant_user_set",
        related_query_name="tenant_user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="tenant_user_set",
        related_query_name="tenant_user",
    )
    
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
        """Check if user is a super admin (always False for tenant users)."""
        return False  # Tenant users are never super admins
    
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
    Abstract base model for tenant-aware models with comprehensive audit fields.
    
    This model provides:
    - Automatic tenant isolation through django-tenants schema separation
    - Audit fields (created_at, updated_at, created_by, updated_by)
    - Tenant-aware manager and queryset
    - Automatic user tracking for create/update operations
    """
    
    # Audit fields
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name=_('Created At'),
        help_text=_('Timestamp when the record was created')
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name=_('Updated At'),
        help_text=_('Timestamp when the record was last updated')
    )
    created_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        verbose_name=_('Created By'),
        help_text=_('User who created this record')
    )
    updated_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated',
        verbose_name=_('Updated By'),
        help_text=_('User who last updated this record')
    )
    
    # Use tenant-aware manager
    objects = TenantAwareManager()
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        """Override save to automatically set created_by and updated_by."""
        current_user = getattr(_thread_locals, 'user', None)
        
        if current_user and current_user.is_authenticated:
            if not self.pk:  # New object
                if not self.created_by:
                    self.created_by = current_user
            
            # Always update updated_by
            self.updated_by = current_user
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate tenant-specific business rules."""
        super().clean()
        
        # Add any tenant-specific validation here
        current_tenant = get_current_tenant()
        if not current_tenant and not getattr(self, '_skip_tenant_validation', False):
            # Allow skipping tenant validation for system operations
            pass
    
    @property
    def tenant_schema(self):
        """Get the current tenant schema name."""
        current_tenant = get_current_tenant()
        return current_tenant.schema_name if current_tenant else None
    
    def get_audit_info(self):
        """Get audit information for this record."""
        return {
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'created_by': self.created_by.username if self.created_by else None,
            'updated_by': self.updated_by.username if self.updated_by else None,
            'tenant_schema': self.tenant_schema,
        }


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


class TOTPDevice(TenantAwareModel):
    """
    TOTP device model for 2FA secret key storage.
    Each user can have one TOTP device for authenticator app enrollment.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='totp_device',
        verbose_name=_('User')
    )
    
    secret_key = models.CharField(
        max_length=32,
        verbose_name=_('Secret Key'),
        help_text=_('Base32 encoded secret key for TOTP generation')
    )
    
    is_confirmed = models.BooleanField(
        default=False,
        verbose_name=_('Is Confirmed'),
        help_text=_('Whether the device has been confirmed by successful verification')
    )
    
    backup_tokens = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Backup Tokens'),
        help_text=_('List of one-time backup tokens for emergency access')
    )
    
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last Used At'),
        help_text=_('Timestamp when the device was last used for verification')
    )
    
    class Meta:
        verbose_name = _('TOTP Device')
        verbose_name_plural = _('TOTP Devices')
        db_table = 'core_totp_device'
    
    def __str__(self):
        return f"TOTP Device for {self.user.username}"
    
    def save(self, *args, **kwargs):
        """Generate secret key if not provided."""
        if not self.secret_key:
            self.secret_key = pyotp.random_base32()
        
        # Generate backup tokens if not provided
        if not self.backup_tokens:
            self.backup_tokens = self.generate_backup_tokens()
        
        super().save(*args, **kwargs)
        
        # Update user's 2FA status
        if self.is_confirmed and not self.user.is_2fa_enabled:
            self.user.is_2fa_enabled = True
            self.user.save(update_fields=['is_2fa_enabled'])
        elif not self.is_confirmed and self.user.is_2fa_enabled:
            self.user.is_2fa_enabled = False
            self.user.save(update_fields=['is_2fa_enabled'])
    
    def delete(self, *args, **kwargs):
        """Disable 2FA when device is deleted."""
        user = self.user
        super().delete(*args, **kwargs)
        
        # Disable 2FA for user
        user.is_2fa_enabled = False
        user.save(update_fields=['is_2fa_enabled'])
    
    def generate_backup_tokens(self, count=10):
        """Generate backup tokens for emergency access."""
        import secrets
        import string
        
        tokens = []
        for _ in range(count):
            # Generate 8-character alphanumeric token
            token = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            tokens.append(token)
        
        return tokens
    
    def get_totp(self):
        """Get TOTP instance for this device."""
        return pyotp.TOTP(self.secret_key)
    
    def verify_token(self, token):
        """
        Verify a TOTP token or backup token.
        
        Args:
            token (str): The token to verify
            
        Returns:
            bool: True if token is valid, False otherwise
        """
        # First try TOTP verification
        totp = self.get_totp()
        if totp.verify(token, valid_window=1):  # Allow 30 seconds window
            self.last_used_at = timezone.now()
            self.save(update_fields=['last_used_at'])
            return True
        
        # Try backup tokens
        if token.upper() in self.backup_tokens:
            # Remove used backup token
            self.backup_tokens.remove(token.upper())
            self.last_used_at = timezone.now()
            self.save(update_fields=['backup_tokens', 'last_used_at'])
            return True
        
        return False
    
    def get_qr_code_url(self, issuer_name="ZARGAR Jewelry SaaS"):
        """
        Generate QR code URL for authenticator app enrollment.
        
        Args:
            issuer_name (str): Name of the service issuing the token
            
        Returns:
            str: QR code URL for TOTP setup
        """
        totp = self.get_totp()
        
        # Create provisioning URI
        provisioning_uri = totp.provisioning_uri(
            name=self.user.username,
            issuer_name=issuer_name
        )
        
        return provisioning_uri
    
    def get_qr_code_image(self, issuer_name="ZARGAR Jewelry SaaS"):
        """
        Generate QR code image as base64 string for display.
        
        Args:
            issuer_name (str): Name of the service issuing the token
            
        Returns:
            str: Base64 encoded QR code image
        """
        provisioning_uri = self.get_qr_code_url(issuer_name)
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def confirm_device(self, token):
        """
        Confirm the device with a valid TOTP token.
        
        Args:
            token (str): TOTP token to verify
            
        Returns:
            bool: True if confirmation successful, False otherwise
        """
        if not self.is_confirmed and self.verify_token(token):
            self.is_confirmed = True
            self.save(update_fields=['is_confirmed'])
            return True
        return False


# Import security models to make them available
from .security_models import SecurityEvent, AuditLog, RateLimitAttempt, SuspiciousActivity

# Import notification models to make them available
from .notification_models import (
    NotificationTemplate,
    NotificationSchedule,
    Notification,
    NotificationDeliveryLog,
    NotificationProvider
)

# Backup models are now in the system app (public schema)