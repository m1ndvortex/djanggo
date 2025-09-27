"""
Admin configuration for core models.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, SystemSettings, TOTPDevice
from .security_models import SecurityEvent, AuditLog, RateLimitAttempt, SuspiciousActivity

# Import security admin configurations
from .security_admin import (
    SecurityEventAdmin, AuditLogAdmin, RateLimitAttemptAdmin, 
    SuspiciousActivityAdmin
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin with Persian support and tenant awareness.
    """
    list_display = (
        'username', 'email', 'persian_first_name', 'persian_last_name',
        'role', 'is_2fa_enabled', 'theme_preference',
        'is_active', 'date_joined'
    )
    list_filter = (
        'role', 'is_2fa_enabled', 'theme_preference', 'is_active',
        'is_staff', 'is_superuser', 'date_joined'
    )
    search_fields = (
        'username', 'email', 'first_name', 'last_name',
        'persian_first_name', 'persian_last_name', 'phone_number'
    )
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        (_('Persian Information'), {
            'fields': ('persian_first_name', 'persian_last_name', 'phone_number')
        }),
        (_('Role & Permissions'), {
            'fields': ('role',)
        }),
        (_('Security & Preferences'), {
            'fields': ('is_2fa_enabled', 'theme_preference')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_('Persian Information'), {
            'fields': ('persian_first_name', 'persian_last_name', 'phone_number')
        }),
        (_('Role & Permissions'), {
            'fields': ('role',)
        }),
    )


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    """
    Admin for system settings.
    """
    list_display = ('key', 'value', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('key', 'value', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('key', 'value', 'description', 'is_active')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TOTPDevice)
class TOTPDeviceAdmin(admin.ModelAdmin):
    """Admin for TOTP devices."""
    
    list_display = ['user', 'is_confirmed', 'last_used_at', 'created_at']
    list_filter = ['is_confirmed', 'created_at', 'last_used_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['secret_key', 'backup_tokens', 'created_at', 'updated_at', 'last_used_at']
    
    fieldsets = (
        (_('Device Information'), {
            'fields': ('user', 'is_confirmed', 'last_used_at')
        }),
        (_('Security Details'), {
            'fields': ('secret_key', 'backup_tokens'),
            'classes': ('collapse',)
        }),
        (_('Audit Information'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def has_add_permission(self, request):
        """Disable manual creation of TOTP devices."""
        return False


# Security models are registered in security_admin.py
# This ensures they appear in the admin interface with proper configuration