"""
Core models for zargar project.
"""
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_tenants.utils import get_tenant_model, connection
from django.core.exceptions import ValidationError
import threading

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