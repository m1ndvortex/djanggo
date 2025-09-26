"""
RBAC Service for managing roles, permissions, and user assignments.
Provides business logic for role-based access control operations.
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.cache import cache
from typing import List, Dict, Optional, Set
import logging

from ..models import (
    SuperAdminRole, 
    SuperAdminPermission, 
    SuperAdminUserRole,
    RolePermissionAuditLog
)
from ..rbac import clear_user_permission_cache

logger = logging.getLogger(__name__)


class RBACService:
    """
    Service class for RBAC operations with comprehensive business logic.
    """
    
    @staticmethod
    def create_default_permissions():
        """
        Create default system permissions if they don't exist.
        Should be called during system initialization.
        """
        default_permissions = [
            # Dashboard permissions
            {
                'codename': 'dashboard.view',
                'name': 'View Dashboard',
                'name_persian': 'مشاهده داشبورد',
                'section': 'dashboard',
                'action': 'view',
                'description': 'View super admin dashboard and basic statistics',
                'description_persian': 'مشاهده داشبورد مدیر کل و آمار کلی'
            },
            
            # Tenant management permissions
            {
                'codename': 'tenants.view',
                'name': 'View Tenants',
                'name_persian': 'مشاهده مستأجران',
                'section': 'tenants',
                'action': 'view',
                'description': 'View tenant list and basic information',
                'description_persian': 'مشاهده لیست مستأجران و اطلاعات پایه'
            },
            {
                'codename': 'tenants.create',
                'name': 'Create Tenants',
                'name_persian': 'ایجاد مستأجر',
                'section': 'tenants',
                'action': 'create',
                'description': 'Create new tenant accounts',
                'description_persian': 'ایجاد حساب‌های مستأجر جدید'
            },
            {
                'codename': 'tenants.edit',
                'name': 'Edit Tenants',
                'name_persian': 'ویرایش مستأجران',
                'section': 'tenants',
                'action': 'edit',
                'description': 'Edit tenant information and settings',
                'description_persian': 'ویرایش اطلاعات و تنظیمات مستأجران'
            },
            {
                'codename': 'tenants.delete',
                'name': 'Delete Tenants',
                'name_persian': 'حذف مستأجران',
                'section': 'tenants',
                'action': 'delete',
                'description': 'Delete tenant accounts (dangerous operation)',
                'description_persian': 'حذف حساب‌های مستأجر (عملیات خطرناک)',
                'is_dangerous': True,
                'requires_2fa': True
            },
            {
                'codename': 'tenants.manage',
                'name': 'Manage Tenants',
                'name_persian': 'مدیریت مستأجران',
                'section': 'tenants',
                'action': 'manage',
                'description': 'Full tenant management including suspension and activation',
                'description_persian': 'مدیریت کامل مستأجران شامل تعلیق و فعال‌سازی'
            },
            
            # User management permissions
            {
                'codename': 'users.view',
                'name': 'View Users',
                'name_persian': 'مشاهده کاربران',
                'section': 'users',
                'action': 'view',
                'description': 'View user accounts across all tenants',
                'description_persian': 'مشاهده حساب‌های کاربری در تمام مستأجران'
            },
            {
                'codename': 'users.create',
                'name': 'Create Users',
                'name_persian': 'ایجاد کاربر',
                'section': 'users',
                'action': 'create',
                'description': 'Create new user accounts',
                'description_persian': 'ایجاد حساب‌های کاربری جدید'
            },
            {
                'codename': 'users.edit',
                'name': 'Edit Users',
                'name_persian': 'ویرایش کاربران',
                'section': 'users',
                'action': 'edit',
                'description': 'Edit user information and settings',
                'description_persian': 'ویرایش اطلاعات و تنظیمات کاربران'
            },
            {
                'codename': 'users.delete',
                'name': 'Delete Users',
                'name_persian': 'حذف کاربران',
                'section': 'users',
                'action': 'delete',
                'description': 'Delete user accounts (dangerous operation)',
                'description_persian': 'حذف حساب‌های کاربری (عملیات خطرناک)',
                'is_dangerous': True
            },
            {
                'codename': 'users.manage',
                'name': 'Manage Users',
                'name_persian': 'مدیریت کاربران',
                'section': 'users',
                'action': 'manage',
                'description': 'Full user management including impersonation',
                'description_persian': 'مدیریت کامل کاربران شامل جانشینی',
                'requires_2fa': True
            },
            
            # Billing permissions
            {
                'codename': 'billing.view',
                'name': 'View Billing',
                'name_persian': 'مشاهده صورتحساب',
                'section': 'billing',
                'action': 'view',
                'description': 'View billing information and invoices',
                'description_persian': 'مشاهده اطلاعات صورتحساب و فاکتورها'
            },
            {
                'codename': 'billing.create',
                'name': 'Create Billing',
                'name_persian': 'ایجاد صورتحساب',
                'section': 'billing',
                'action': 'create',
                'description': 'Create invoices and billing records',
                'description_persian': 'ایجاد فاکتور و سوابق صورتحساب'
            },
            {
                'codename': 'billing.manage',
                'name': 'Manage Billing',
                'name_persian': 'مدیریت صورتحساب',
                'section': 'billing',
                'action': 'manage',
                'description': 'Full billing management including subscriptions',
                'description_persian': 'مدیریت کامل صورتحساب شامل اشتراک‌ها'
            },
            
            # Security permissions
            {
                'codename': 'security.view',
                'name': 'View Security',
                'name_persian': 'مشاهده امنیت',
                'section': 'security',
                'action': 'view',
                'description': 'View security dashboard and audit logs',
                'description_persian': 'مشاهده داشبورد امنیت و لاگ‌های حسابرسی'
            },
            {
                'codename': 'security.manage',
                'name': 'Manage Security',
                'name_persian': 'مدیریت امنیت',
                'section': 'security',
                'action': 'manage',
                'description': 'Full security management including access control',
                'description_persian': 'مدیریت کامل امنیت شامل کنترل دسترسی',
                'requires_2fa': True
            },
            
            # Settings permissions
            {
                'codename': 'settings.view',
                'name': 'View Settings',
                'name_persian': 'مشاهده تنظیمات',
                'section': 'settings',
                'action': 'view',
                'description': 'View system settings and configuration',
                'description_persian': 'مشاهده تنظیمات سیستم و پیکربندی'
            },
            {
                'codename': 'settings.manage',
                'name': 'Manage Settings',
                'name_persian': 'مدیریت تنظیمات',
                'section': 'settings',
                'action': 'manage',
                'description': 'Full settings management including security policies',
                'description_persian': 'مدیریت کامل تنظیمات شامل سیاست‌های امنیتی',
                'is_dangerous': True,
                'requires_2fa': True
            },
            
            # Backup permissions
            {
                'codename': 'backup.view',
                'name': 'View Backups',
                'name_persian': 'مشاهده پشتیبان‌ها',
                'section': 'backup',
                'action': 'view',
                'description': 'View backup status and history',
                'description_persian': 'مشاهده وضعیت و تاریخچه پشتیبان‌ها'
            },
            {
                'codename': 'backup.create',
                'name': 'Create Backups',
                'name_persian': 'ایجاد پشتیبان',
                'section': 'backup',
                'action': 'create',
                'description': 'Create system and tenant backups',
                'description_persian': 'ایجاد پشتیبان سیستم و مستأجران'
            },
            {
                'codename': 'backup.manage',
                'name': 'Manage Backups',
                'name_persian': 'مدیریت پشتیبان‌ها',
                'section': 'backup',
                'action': 'manage',
                'description': 'Full backup management including restore operations',
                'description_persian': 'مدیریت کامل پشتیبان‌ها شامل عملیات بازیابی',
                'is_dangerous': True,
                'requires_2fa': True
            },
            
            # Monitoring permissions
            {
                'codename': 'monitoring.view',
                'name': 'View Monitoring',
                'name_persian': 'مشاهده نظارت',
                'section': 'monitoring',
                'action': 'view',
                'description': 'View system monitoring and health status',
                'description_persian': 'مشاهده نظارت سیستم و وضعیت سلامت'
            },
            
            # Reports permissions
            {
                'codename': 'reports.view',
                'name': 'View Reports',
                'name_persian': 'مشاهده گزارش‌ها',
                'section': 'reports',
                'action': 'view',
                'description': 'View system reports and analytics',
                'description_persian': 'مشاهده گزارش‌های سیستم و تحلیل‌ها'
            },
            {
                'codename': 'reports.export',
                'name': 'Export Reports',
                'name_persian': 'صادرات گزارش‌ها',
                'section': 'reports',
                'action': 'export',
                'description': 'Export reports and data',
                'description_persian': 'صادرات گزارش‌ها و داده‌ها'
            },
            
            # Integration permissions
            {
                'codename': 'integrations.view',
                'name': 'View Integrations',
                'name_persian': 'مشاهده یکپارچه‌سازی‌ها',
                'section': 'integrations',
                'action': 'view',
                'description': 'View integration settings and API configuration',
                'description_persian': 'مشاهده تنظیمات یکپارچه‌سازی و پیکربندی API'
            },
            {
                'codename': 'integrations.manage',
                'name': 'Manage Integrations',
                'name_persian': 'مدیریت یکپارچه‌سازی‌ها',
                'section': 'integrations',
                'action': 'manage',
                'description': 'Full integration management including API access',
                'description_persian': 'مدیریت کامل یکپارچه‌سازی‌ها شامل دسترسی API'
            },
        ]
        
        created_count = 0
        for perm_data in default_permissions:
            permission, created = SuperAdminPermission.objects.get_or_create(
                codename=perm_data['codename'],
                defaults=perm_data
            )
            if created:
                created_count += 1
                logger.info(f"Created default permission: {permission.codename}")
        
        logger.info(f"Created {created_count} default permissions")
        return created_count
    
    @staticmethod
    def create_default_roles():
        """
        Create default system roles if they don't exist.
        """
        default_roles = [
            {
                'name': 'Super Administrator',
                'name_persian': 'مدیر کل سیستم',
                'description': 'Full system access with all permissions',
                'description_persian': 'دسترسی کامل سیستم با تمام مجوزها',
                'role_type': 'system',
                'is_default': True,
                'requires_2fa': True,
                'permissions': ['*']  # All permissions
            },
            {
                'name': 'Tenant Manager',
                'name_persian': 'مدیر مستأجران',
                'description': 'Manage tenants and their basic settings',
                'description_persian': 'مدیریت مستأجران و تنظیمات پایه آن‌ها',
                'role_type': 'system',
                'permissions': [
                    'dashboard.view', 'tenants.view', 'tenants.create', 
                    'tenants.edit', 'users.view', 'users.create', 'users.edit'
                ]
            },
            {
                'name': 'Security Manager',
                'name_persian': 'مدیر امنیت',
                'description': 'Manage security settings and audit logs',
                'description_persian': 'مدیریت تنظیمات امنیت و لاگ‌های حسابرسی',
                'role_type': 'system',
                'requires_2fa': True,
                'permissions': [
                    'dashboard.view', 'security.view', 'security.manage',
                    'users.view', 'tenants.view'
                ]
            },
            {
                'name': 'Billing Manager',
                'name_persian': 'مدیر صورتحساب',
                'description': 'Manage billing, invoices, and subscriptions',
                'description_persian': 'مدیریت صورتحساب، فاکتورها و اشتراک‌ها',
                'role_type': 'system',
                'permissions': [
                    'dashboard.view', 'billing.view', 'billing.create', 
                    'billing.manage', 'tenants.view', 'reports.view'
                ]
            },
            {
                'name': 'System Monitor',
                'name_persian': 'ناظر سیستم',
                'description': 'Monitor system health and performance',
                'description_persian': 'نظارت بر سلامت و عملکرد سیستم',
                'role_type': 'system',
                'permissions': [
                    'dashboard.view', 'monitoring.view', 'reports.view',
                    'backup.view', 'tenants.view'
                ]
            },
            {
                'name': 'Read Only',
                'name_persian': 'فقط خواندنی',
                'description': 'View-only access to most sections',
                'description_persian': 'دسترسی فقط خواندنی به اکثر بخش‌ها',
                'role_type': 'system',
                'permissions': [
                    'dashboard.view', 'tenants.view', 'users.view',
                    'billing.view', 'security.view', 'monitoring.view',
                    'reports.view', 'backup.view'
                ]
            }
        ]
        
        created_count = 0
        for role_data in default_roles:
            permissions_list = role_data.pop('permissions', [])
            
            role, created = SuperAdminRole.objects.get_or_create(
                name=role_data['name'],
                defaults=role_data
            )
            
            if created:
                created_count += 1
                logger.info(f"Created default role: {role.name}")
                
                # Assign permissions
                if '*' in permissions_list:
                    # Assign all permissions
                    all_permissions = SuperAdminPermission.objects.filter(is_active=True)
                    role.permissions.set(all_permissions)
                else:
                    # Assign specific permissions
                    permissions = SuperAdminPermission.objects.filter(
                        codename__in=permissions_list,
                        is_active=True
                    )
                    role.permissions.set(permissions)
        
        logger.info(f"Created {created_count} default roles")
        return created_count
    
    @staticmethod
    @transaction.atomic
    def create_role(name, name_persian, description='', description_persian='',
                   permissions=None, created_by_id=None, created_by_username='',
                   **kwargs):
        """
        Create a new role with specified permissions.
        """
        try:
            # Create the role
            role = SuperAdminRole.objects.create(
                name=name,
                name_persian=name_persian,
                description=description,
                description_persian=description_persian,
                created_by_id=created_by_id,
                created_by_username=created_by_username,
                **kwargs
            )
            
            # Assign permissions if provided
            if permissions:
                permission_objects = SuperAdminPermission.objects.filter(
                    codename__in=permissions,
                    is_active=True
                )
                role.permissions.set(permission_objects)
            
            # Log the action
            RolePermissionAuditLog.log_action(
                action='role_created',
                object_type='role',
                object_id=role.id,
                object_name=role.name,
                performed_by_id=created_by_id or 0,
                performed_by_username=created_by_username,
                new_values={
                    'name': name,
                    'name_persian': name_persian,
                    'description': description,
                    'permissions': list(permissions) if permissions else []
                }
            )
            
            logger.info(f"Created role: {role.name} by {created_by_username}")
            return role
            
        except Exception as e:
            logger.error(f"Error creating role {name}: {e}")
            raise ValidationError(f"Failed to create role: {e}")
    
    @staticmethod
    @transaction.atomic
    def update_role(role_id, updated_by_id=None, updated_by_username='', **updates):
        """
        Update an existing role.
        """
        try:
            role = SuperAdminRole.objects.get(id=role_id)
            
            # Store old values for audit
            old_values = {
                'name': role.name,
                'name_persian': role.name_persian,
                'description': role.description,
                'permissions': list(role.permissions.values_list('codename', flat=True))
            }
            
            # Handle permissions separately
            permissions = updates.pop('permissions', None)
            
            # Update role fields
            for field, value in updates.items():
                if hasattr(role, field):
                    setattr(role, field, value)
            
            role.save()
            
            # Update permissions if provided
            if permissions is not None:
                permission_objects = SuperAdminPermission.objects.filter(
                    codename__in=permissions,
                    is_active=True
                )
                role.permissions.set(permission_objects)
            
            # Clear cache for all users with this role
            user_roles = SuperAdminUserRole.objects.filter(role=role, is_active=True)
            for user_role in user_roles:
                clear_user_permission_cache(user_role.user_id)
            
            # Log the action
            new_values = {
                'name': role.name,
                'name_persian': role.name_persian,
                'description': role.description,
                'permissions': list(role.permissions.values_list('codename', flat=True))
            }
            
            RolePermissionAuditLog.log_action(
                action='role_updated',
                object_type='role',
                object_id=role.id,
                object_name=role.name,
                performed_by_id=updated_by_id or 0,
                performed_by_username=updated_by_username,
                old_values=old_values,
                new_values=new_values
            )
            
            logger.info(f"Updated role: {role.name} by {updated_by_username}")
            return role
            
        except SuperAdminRole.DoesNotExist:
            raise ValidationError(f"Role with ID {role_id} not found")
        except Exception as e:
            logger.error(f"Error updating role {role_id}: {e}")
            raise ValidationError(f"Failed to update role: {e}")
    
    @staticmethod
    @transaction.atomic
    def delete_role(role_id, deleted_by_id=None, deleted_by_username=''):
        """
        Delete a role (only custom roles can be deleted).
        """
        try:
            role = SuperAdminRole.objects.get(id=role_id)
            
            # Prevent deletion of system roles
            if role.role_type == 'system':
                raise ValidationError(_("System roles cannot be deleted"))
            
            # Check if role has active users
            active_users = SuperAdminUserRole.objects.filter(
                role=role, 
                is_active=True
            ).count()
            
            if active_users > 0:
                raise ValidationError(
                    _("Cannot delete role with active users. Please reassign users first.")
                )
            
            # Store role info for audit
            role_info = {
                'name': role.name,
                'name_persian': role.name_persian,
                'permissions': list(role.permissions.values_list('codename', flat=True))
            }
            
            role_name = role.name
            role.delete()
            
            # Log the action
            RolePermissionAuditLog.log_action(
                action='role_deleted',
                object_type='role',
                object_id=role_id,
                object_name=role_name,
                performed_by_id=deleted_by_id or 0,
                performed_by_username=deleted_by_username,
                old_values=role_info
            )
            
            logger.info(f"Deleted role: {role_name} by {deleted_by_username}")
            return True
            
        except SuperAdminRole.DoesNotExist:
            raise ValidationError(f"Role with ID {role_id} not found")
        except Exception as e:
            logger.error(f"Error deleting role {role_id}: {e}")
            raise ValidationError(f"Failed to delete role: {e}")
    
    @staticmethod
    @transaction.atomic
    def assign_role_to_user(user_id, username, role_id, assigned_by_id=None, 
                           assigned_by_username='', expires_at=None, 
                           assignment_reason='', notes=''):
        """
        Assign a role to a user.
        """
        try:
            role = SuperAdminRole.objects.get(id=role_id, is_active=True)
            
            # Check if role is at capacity
            if role.is_at_max_capacity:
                raise ValidationError(
                    _("Role '{}' has reached maximum user capacity of {}").format(
                        role.name, role.max_users
                    )
                )
            
            # Create or update user role assignment
            user_role, created = SuperAdminUserRole.objects.get_or_create(
                user_id=user_id,
                role=role,
                defaults={
                    'user_username': username,
                    'assigned_by_id': assigned_by_id,
                    'assigned_by_username': assigned_by_username,
                    'expires_at': expires_at,
                    'assignment_reason': assignment_reason,
                    'notes': notes,
                    'is_active': True
                }
            )
            
            if not created and not user_role.is_active:
                # Reactivate existing assignment
                user_role.is_active = True
                user_role.assigned_at = timezone.now()
                user_role.assigned_by_id = assigned_by_id
                user_role.assigned_by_username = assigned_by_username
                user_role.expires_at = expires_at
                user_role.assignment_reason = assignment_reason
                user_role.notes = notes
                user_role.save()
            
            # Clear user permission cache
            clear_user_permission_cache(user_id)
            
            # Log the action
            RolePermissionAuditLog.log_action(
                action='role_assigned',
                object_type='user_role',
                object_id=user_role.id,
                object_name=f"{username} -> {role.name}",
                performed_by_id=assigned_by_id or 0,
                performed_by_username=assigned_by_username,
                new_values={
                    'user_id': user_id,
                    'username': username,
                    'role_name': role.name,
                    'expires_at': expires_at.isoformat() if expires_at else None,
                    'assignment_reason': assignment_reason
                }
            )
            
            logger.info(f"Assigned role {role.name} to user {username} by {assigned_by_username}")
            return user_role
            
        except SuperAdminRole.DoesNotExist:
            raise ValidationError(f"Role with ID {role_id} not found or inactive")
        except Exception as e:
            logger.error(f"Error assigning role {role_id} to user {user_id}: {e}")
            raise ValidationError(f"Failed to assign role: {e}")
    
    @staticmethod
    @transaction.atomic
    def revoke_role_from_user(user_id, role_id, revoked_by_id=None, 
                             revoked_by_username='', reason=''):
        """
        Revoke a role from a user.
        """
        try:
            user_role = SuperAdminUserRole.objects.get(
                user_id=user_id,
                role_id=role_id,
                is_active=True
            )
            
            user_role.revoke(revoked_by_id, revoked_by_username, reason)
            
            # Clear user permission cache
            clear_user_permission_cache(user_id)
            
            logger.info(f"Revoked role {user_role.role.name} from user {user_role.user_username} by {revoked_by_username}")
            return True
            
        except SuperAdminUserRole.DoesNotExist:
            raise ValidationError("Active role assignment not found")
        except Exception as e:
            logger.error(f"Error revoking role {role_id} from user {user_id}: {e}")
            raise ValidationError(f"Failed to revoke role: {e}")
    
    @staticmethod
    def get_user_roles(user_id):
        """
        Get all active roles for a user.
        """
        return SuperAdminUserRole.objects.filter(
            user_id=user_id,
            is_active=True,
            role__is_active=True
        ).select_related('role').prefetch_related('role__permissions')
    
    @staticmethod
    def get_user_permissions(user_id):
        """
        Get all permissions for a user through their roles.
        """
        user_roles = RBACService.get_user_roles(user_id)
        permissions = set()
        
        for user_role in user_roles:
            if not user_role.is_expired:
                role_permissions = user_role.role.get_all_permissions()
                permissions.update(role_permissions)
        
        return permissions
    
    @staticmethod
    def user_has_permission(user_id, permission_codename):
        """
        Check if user has specific permission.
        """
        user_permissions = RBACService.get_user_permissions(user_id)
        return any(perm.codename == permission_codename for perm in user_permissions)
    
    @staticmethod
    def get_role_statistics():
        """
        Get statistics about roles and assignments.
        """
        return {
            'total_roles': SuperAdminRole.objects.filter(is_active=True).count(),
            'system_roles': SuperAdminRole.objects.filter(role_type='system', is_active=True).count(),
            'custom_roles': SuperAdminRole.objects.filter(role_type='custom', is_active=True).count(),
            'total_permissions': SuperAdminPermission.objects.filter(is_active=True).count(),
            'active_assignments': SuperAdminUserRole.objects.filter(is_active=True).count(),
            'expired_assignments': SuperAdminUserRole.objects.filter(
                is_active=True,
                expires_at__lt=timezone.now()
            ).count()
        }
    
    @staticmethod
    def cleanup_expired_assignments():
        """
        Cleanup expired role assignments.
        """
        expired_assignments = SuperAdminUserRole.objects.filter(
            is_active=True,
            expires_at__lt=timezone.now()
        )
        
        count = 0
        for assignment in expired_assignments:
            assignment.is_active = False
            assignment.notes = (assignment.notes or '') + f"\nAuto-expired at {timezone.now()}"
            assignment.save()
            
            # Clear user permission cache
            clear_user_permission_cache(assignment.user_id)
            count += 1
        
        logger.info(f"Cleaned up {count} expired role assignments")
        return count
    
    @staticmethod
    @transaction.atomic
    def toggle_role_permission(role_id, permission_id, updated_by_id=None, updated_by_username=''):
        """
        Toggle a permission for a role (add if not exists, remove if exists).
        
        Args:
            role_id: ID of the role
            permission_id: ID of the permission
            updated_by_id: ID of the user making the change
            updated_by_username: Username of the user making the change
        
        Returns:
            dict: Result with success status and whether permission was added or removed
        """
        try:
            role = SuperAdminRole.objects.get(id=role_id, is_active=True)
            permission = SuperAdminPermission.objects.get(id=permission_id, is_active=True)
            
            # Check if role currently has this permission
            has_permission = role.permissions.filter(id=permission_id).exists()
            
            if has_permission:
                # Remove permission
                role.permissions.remove(permission)
                action = 'removed'
                audit_action = 'permission_removed_from_role'
            else:
                # Add permission
                role.permissions.add(permission)
                action = 'added'
                audit_action = 'permission_added_to_role'
            
            # Clear cache for all users with this role
            user_roles = SuperAdminUserRole.objects.filter(role=role, is_active=True)
            for user_role in user_roles:
                clear_user_permission_cache(user_role.user_id)
            
            # Log the action
            RolePermissionAuditLog.log_action(
                action=audit_action,
                object_type='role_permission',
                object_id=role.id,
                object_name=f"{role.name} - {permission.name}",
                old_values={'has_permission': has_permission},
                new_values={'has_permission': not has_permission},
                performed_by_id=updated_by_id or 0,
                performed_by_username=updated_by_username or 'system'
            )
            
            logger.info(f"Permission {permission.codename} {action} for role {role.name} by {updated_by_username}")
            
            return {
                'success': True,
                'action': action,
                'has_permission': not has_permission,
                'role_name': role.name_persian or role.name,
                'permission_name': permission.name_persian or permission.name
            }
            
        except SuperAdminRole.DoesNotExist:
            logger.error(f"Role with ID {role_id} not found")
            raise ValidationError(_("نقش یافت نشد."))
        except SuperAdminPermission.DoesNotExist:
            logger.error(f"Permission with ID {permission_id} not found")
            raise ValidationError(_("مجوز یافت نشد."))
        except Exception as e:
            logger.error(f"Error toggling permission {permission_id} for role {role_id}: {e}")
            raise ValidationError(f"خطا در تغییر مجوز: {e}")