"""
Admin configuration for core models.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, SystemSettings, AuditLog


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


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Admin for audit logs (read-only).
    """
    list_display = (
        'timestamp', 'user', 'action', 'model_name',
        'object_id', 'tenant_schema', 'ip_address'
    )
    list_filter = ('action', 'timestamp', 'tenant_schema')
    search_fields = ('user__username', 'action', 'model_name', 'object_id', 'ip_address')
    readonly_fields = (
        'user', 'action', 'model_name', 'object_id', 'details',
        'ip_address', 'user_agent', 'tenant_schema', 'timestamp'
    )
    ordering = ('-timestamp',)
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False