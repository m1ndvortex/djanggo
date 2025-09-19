"""
Super Admin models for cross-tenant management.
These models exist in the shared schema and allow super admins to access all tenants.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class SuperAdmin(AbstractUser):
    """
    Super Admin model that exists in shared schema for cross-tenant access.
    This is separate from regular Users who are tenant-isolated.
    """
    
    # Additional fields for super admin
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        verbose_name=_('Phone Number')
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
    
    # Super admin specific fields
    can_create_tenants = models.BooleanField(
        default=True,
        verbose_name=_('Can Create Tenants')
    )
    
    can_suspend_tenants = models.BooleanField(
        default=True,
        verbose_name=_('Can Suspend Tenants')
    )
    
    can_access_all_data = models.BooleanField(
        default=True,
        verbose_name=_('Can Access All Tenant Data')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_tenant_access = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('Super Admin')
        verbose_name_plural = _('Super Admins')
        db_table = 'tenants_superadmin'
    
    # Override groups and user_permissions to avoid conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="superadmin_set",
        related_query_name="superadmin",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="superadmin_set",
        related_query_name="superadmin",
    )
    
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
    
    def record_tenant_access(self, tenant_schema):
        """Record when super admin accesses a tenant."""
        self.last_tenant_access = timezone.now()
        self.save(update_fields=['last_tenant_access'])
        
        # Create session record
        SuperAdminSession.objects.create(
            super_admin=self,
            tenant_schema=tenant_schema,
            access_time=timezone.now()
        )


class SuperAdminSession(models.Model):
    """
    Track super admin sessions across tenants for audit purposes.
    """
    super_admin = models.ForeignKey(
        SuperAdmin,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name=_('Super Admin')
    )
    
    tenant_schema = models.CharField(
        max_length=100,
        verbose_name=_('Tenant Schema')
    )
    
    session_key = models.CharField(
        max_length=40,
        blank=True,
        verbose_name=_('Session Key')
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
    
    access_time = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Access Time')
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active Session')
    )
    
    class Meta:
        verbose_name = _('Super Admin Session')
        verbose_name_plural = _('Super Admin Sessions')
        db_table = 'tenants_superadmin_session'
        ordering = ['-access_time']
        indexes = [
            models.Index(fields=['super_admin', 'tenant_schema']),
            models.Index(fields=['session_key']),
            models.Index(fields=['access_time']),
        ]
    
    def __str__(self):
        return f"{self.super_admin.username} -> {self.tenant_schema} at {self.access_time}"


class TenantAccessLog(models.Model):
    """
    Comprehensive audit log for tenant access and operations.
    """
    ACTION_CHOICES = [
        ('login', _('Login')),
        ('logout', _('Logout')),
        ('create', _('Create Record')),
        ('update', _('Update Record')),
        ('delete', _('Delete Record')),
        ('view', _('View Record')),
        ('export', _('Export Data')),
        ('import', _('Import Data')),
        ('tenant_switch', _('Switch Tenant')),
        ('impersonation_start', _('Start Impersonation')),
        ('impersonation_end', _('End Impersonation')),
    ]
    
    # User information (can be SuperAdmin or regular User)
    user_type = models.CharField(
        max_length=20,
        choices=[
            ('superadmin', _('Super Admin')),
            ('user', _('Regular User')),
        ],
        verbose_name=_('User Type')
    )
    
    user_id = models.PositiveIntegerField(
        verbose_name=_('User ID')
    )
    
    username = models.CharField(
        max_length=150,
        verbose_name=_('Username')
    )
    
    # Tenant information
    tenant_schema = models.CharField(
        max_length=100,
        verbose_name=_('Tenant Schema')
    )
    
    tenant_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Tenant Name')
    )
    
    # Action details
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
        verbose_name=_('Action Details')
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
    
    # Timing
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Timestamp')
    )
    
    duration_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Duration (ms)')
    )
    
    # Status
    success = models.BooleanField(
        default=True,
        verbose_name=_('Success')
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Error Message')
    )
    
    class Meta:
        verbose_name = _('Tenant Access Log')
        verbose_name_plural = _('Tenant Access Logs')
        db_table = 'tenants_access_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user_type', 'user_id']),
            models.Index(fields=['tenant_schema']),
            models.Index(fields=['action']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['success']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.user_type}) - {self.action} in {self.tenant_schema}"
    
    @classmethod
    def log_action(cls, user, tenant_schema, action, **kwargs):
        """
        Convenience method to log an action.
        """
        # Determine user type
        if hasattr(user, '_meta') and user._meta.model_name == 'superadmin':
            user_type = 'superadmin'
        else:
            user_type = 'user'
        
        # Get tenant name
        tenant_name = kwargs.get('tenant_name', '')
        if not tenant_name and tenant_schema != 'public':
            try:
                from zargar.tenants.models import Tenant
                tenant = Tenant.objects.filter(schema_name=tenant_schema).first()
                tenant_name = tenant.name if tenant else ''
            except:
                pass
        
        return cls.objects.create(
            user_type=user_type,
            user_id=user.id,
            username=user.username,
            tenant_schema=tenant_schema,
            tenant_name=tenant_name,
            action=action,
            model_name=kwargs.get('model_name', ''),
            object_id=kwargs.get('object_id', ''),
            details=kwargs.get('details', {}),
            ip_address=kwargs.get('ip_address'),
            user_agent=kwargs.get('user_agent', ''),
            request_path=kwargs.get('request_path', ''),
            request_method=kwargs.get('request_method', ''),
            duration_ms=kwargs.get('duration_ms'),
            success=kwargs.get('success', True),
            error_message=kwargs.get('error_message', ''),
        )