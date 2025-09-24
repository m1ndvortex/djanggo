"""
Role-Based Access Control (RBAC) utilities for Super Admin panel.
Provides middleware, decorators, and helper functions for permission checking.
"""
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.core.cache import cache
from django.utils.decorators import method_decorator
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class RBACMiddleware:
    """
    Middleware to enforce role-based access control for super admin panel.
    Checks permissions for all requests to super admin sections.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Define URL patterns that require specific permissions
        self.permission_map = {
            # Dashboard permissions
            '/super-panel/': 'dashboard.view',
            '/super-panel/dashboard/': 'dashboard.view',
            
            # Tenant management permissions
            '/super-panel/tenants/': 'tenants.view',
            '/super-panel/tenants/create/': 'tenants.create',
            '/super-panel/tenants/edit/': 'tenants.edit',
            '/super-panel/tenants/delete/': 'tenants.delete',
            '/super-panel/tenants/suspend/': 'tenants.manage',
            
            # User management permissions
            '/super-panel/users/': 'users.view',
            '/super-panel/users/create/': 'users.create',
            '/super-panel/users/edit/': 'users.edit',
            '/super-panel/users/delete/': 'users.delete',
            '/super-panel/users/impersonate/': 'users.manage',
            
            # Billing permissions
            '/super-panel/billing/': 'billing.view',
            '/super-panel/billing/invoices/': 'billing.view',
            '/super-panel/billing/create-invoice/': 'billing.create',
            '/super-panel/billing/subscriptions/': 'billing.manage',
            
            # Security permissions
            '/super-panel/security/': 'security.view',
            '/super-panel/security/dashboard/': 'security.view',
            '/super-panel/security/audit-logs/': 'security.view',
            '/super-panel/security/security-events/': 'security.view',
            '/super-panel/security/access-control/': 'security.manage',
            
            # Settings permissions
            '/super-panel/settings/': 'settings.view',
            '/super-panel/settings/security-policies/': 'settings.manage',
            '/super-panel/settings/notifications/': 'settings.manage',
            '/super-panel/settings/backup-settings/': 'settings.manage',
            '/super-panel/settings/integrations/': 'settings.manage',
            
            # Backup permissions
            '/super-panel/backup/': 'backup.view',
            '/super-panel/backup/create/': 'backup.create',
            '/super-panel/backup/restore/': 'backup.manage',
            
            # Monitoring permissions
            '/super-panel/monitoring/': 'monitoring.view',
            '/super-panel/monitoring/system-health/': 'monitoring.view',
            '/super-panel/monitoring/performance/': 'monitoring.view',
            
            # Reports permissions
            '/super-panel/reports/': 'reports.view',
            '/super-panel/reports/export/': 'reports.export',
            '/super-panel/reports/analytics/': 'reports.view',
            
            # Integration permissions
            '/super-panel/integrations/': 'integrations.view',
            '/super-panel/integrations/api/': 'integrations.manage',
        }
    
    def __call__(self, request):
        # Process request before view
        response = self.process_request(request)
        if response:
            return response
        
        # Get response from view
        response = self.get_response(request)
        
        return response
    
    def process_request(self, request):
        """
        Check permissions before processing the request.
        """
        # Skip permission check for non-super-panel URLs
        if not request.path.startswith('/super-panel/'):
            return None
        
        # Skip permission check for login/logout URLs
        if request.path in ['/super-panel/login/', '/super-panel/logout/']:
            return None
        
        # Check if user is authenticated as super admin
        if not self.is_super_admin(request.user):
            return redirect('admin_panel:login')
        
        # Get required permission for this URL
        required_permission = self.get_required_permission(request.path)
        if not required_permission:
            # No specific permission required, allow access
            return None
        
        # Check if user has required permission
        if not self.user_has_permission(request.user, required_permission):
            logger.warning(
                f"Access denied for user {request.user.username} to {request.path}. "
                f"Required permission: {required_permission}"
            )
            
            # Return appropriate response based on request type
            if request.headers.get('Accept', '').startswith('application/json'):
                return JsonResponse({
                    'error': 'Access denied',
                    'message': _('You do not have permission to access this resource.'),
                    'required_permission': required_permission
                }, status=403)
            else:
                messages.error(
                    request, 
                    _('You do not have permission to access this section. Required permission: {}').format(
                        required_permission
                    )
                )
                return redirect('admin_panel:dashboard')
        
        return None
    
    def is_super_admin(self, user):
        """
        Check if user is a super admin.
        """
        if not user or not user.is_authenticated:
            return False
        
        # Check if user is instance of SuperAdmin model
        return hasattr(user, '_meta') and user._meta.model_name == 'superadmin'
    
    def get_required_permission(self, path):
        """
        Get required permission for a given URL path.
        """
        # Try exact match first
        if path in self.permission_map:
            return self.permission_map[path]
        
        # Try pattern matching for dynamic URLs
        for pattern, permission in self.permission_map.items():
            if path.startswith(pattern.rstrip('/')):
                return permission
        
        return None
    
    def user_has_permission(self, user, permission_codename):
        """
        Check if user has specific permission through their roles.
        Uses caching for performance.
        """
        if not user or not user.is_authenticated:
            return False
        
        # Cache key for user permissions
        cache_key = f"superadmin_permissions_{user.id}"
        user_permissions = cache.get(cache_key)
        
        if user_permissions is None:
            # Get user permissions from database
            user_permissions = self.get_user_permissions(user)
            # Cache for 5 minutes
            cache.set(cache_key, user_permissions, 300)
        
        return permission_codename in user_permissions
    
    def get_user_permissions(self, user):
        """
        Get all permissions for a user through their active roles.
        """
        from .models import SuperAdminUserRole
        
        try:
            # Get all active roles for the user
            user_roles = SuperAdminUserRole.objects.filter(
                user_id=user.id,
                is_active=True,
                role__is_active=True
            ).select_related('role').prefetch_related('role__permissions')
            
            permissions = set()
            for user_role in user_roles:
                # Skip expired roles
                if user_role.is_expired:
                    continue
                
                # Get all permissions for this role (including inherited)
                role_permissions = user_role.role.get_all_permissions()
                permissions.update(perm.codename for perm in role_permissions)
            
            return permissions
            
        except Exception as e:
            logger.error(f"Error getting user permissions for {user.username}: {e}")
            return set()


def require_permission(permission_codename, raise_exception=False):
    """
    Decorator to require specific permission for a view.
    
    Args:
        permission_codename (str): Required permission (e.g., 'tenants.create')
        raise_exception (bool): If True, raise 403 exception instead of redirecting
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check if user has permission
            rbac_middleware = RBACMiddleware(None)
            
            if not rbac_middleware.user_has_permission(request.user, permission_codename):
                logger.warning(
                    f"Permission denied for user {request.user.username}. "
                    f"Required permission: {permission_codename}"
                )
                
                if raise_exception:
                    return HttpResponseForbidden(
                        _('You do not have permission to perform this action.')
                    )
                
                # Check if it's an AJAX request
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': 'Permission denied',
                        'message': _('You do not have permission to perform this action.'),
                        'required_permission': permission_codename
                    }, status=403)
                
                messages.error(
                    request,
                    _('You do not have permission to perform this action. Required permission: {}').format(
                        permission_codename
                    )
                )
                return redirect('admin_panel:dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_permissions(*permission_codenames, require_all=True):
    """
    Decorator to require multiple permissions for a view.
    
    Args:
        *permission_codenames: List of required permissions
        require_all (bool): If True, user must have ALL permissions. If False, user needs ANY permission.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            rbac_middleware = RBACMiddleware(None)
            
            user_permissions = rbac_middleware.get_user_permissions(request.user)
            
            if require_all:
                # User must have ALL permissions
                missing_permissions = [
                    perm for perm in permission_codenames 
                    if perm not in user_permissions
                ]
                has_access = len(missing_permissions) == 0
            else:
                # User must have ANY permission
                has_access = any(perm in user_permissions for perm in permission_codenames)
                missing_permissions = list(permission_codenames)
            
            if not has_access:
                logger.warning(
                    f"Permission denied for user {request.user.username}. "
                    f"Required permissions: {permission_codenames}, "
                    f"Missing: {missing_permissions if require_all else 'all'}"
                )
                
                # Check if it's an AJAX request
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': 'Permission denied',
                        'message': _('You do not have sufficient permissions to perform this action.'),
                        'required_permissions': list(permission_codenames),
                        'missing_permissions': missing_permissions if require_all else list(permission_codenames)
                    }, status=403)
                
                messages.error(
                    request,
                    _('You do not have sufficient permissions to perform this action.')
                )
                return redirect('admin_panel:dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


class RequirePermissionMixin:
    """
    Mixin for class-based views to require specific permissions.
    """
    permission_required = None
    permissions_required = None
    require_all_permissions = True
    raise_exception = False
    
    def dispatch(self, request, *args, **kwargs):
        """
        Check permissions before dispatching to view method.
        """
        if not self.has_permission(request):
            return self.handle_no_permission(request)
        
        return super().dispatch(request, *args, **kwargs)
    
    def has_permission(self, request):
        """
        Check if user has required permissions.
        """
        rbac_middleware = RBACMiddleware(None)
        
        # Check single permission
        if self.permission_required:
            return rbac_middleware.user_has_permission(request.user, self.permission_required)
        
        # Check multiple permissions
        if self.permissions_required:
            user_permissions = rbac_middleware.get_user_permissions(request.user)
            
            if self.require_all_permissions:
                return all(perm in user_permissions for perm in self.permissions_required)
            else:
                return any(perm in user_permissions for perm in self.permissions_required)
        
        # No permissions specified, allow access
        return True
    
    def handle_no_permission(self, request):
        """
        Handle case where user doesn't have required permissions.
        """
        required_perms = self.permission_required or self.permissions_required
        
        logger.warning(
            f"Permission denied for user {request.user.username}. "
            f"Required permissions: {required_perms}"
        )
        
        if self.raise_exception:
            return HttpResponseForbidden(
                _('You do not have permission to access this resource.')
            )
        
        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'error': 'Permission denied',
                'message': _('You do not have permission to access this resource.'),
                'required_permissions': required_perms
            }, status=403)
        
        messages.error(
            request,
            _('You do not have permission to access this resource.')
        )
        return redirect('admin_panel:dashboard')


def clear_user_permission_cache(user_id):
    """
    Clear cached permissions for a specific user.
    Call this when user roles or permissions change.
    """
    cache_key = f"superadmin_permissions_{user_id}"
    cache.delete(cache_key)


def get_user_accessible_sections(user):
    """
    Get list of super admin panel sections that user can access.
    """
    rbac_middleware = RBACMiddleware(None)
    user_permissions = rbac_middleware.get_user_permissions(user)
    
    # Map permissions to sections
    sections = set()
    for permission in user_permissions:
        if '.' in permission:
            section = permission.split('.')[0]
            sections.add(section)
    
    return list(sections)


def user_can_access_section(user, section):
    """
    Check if user can access a specific section of the super admin panel.
    """
    accessible_sections = get_user_accessible_sections(user)
    return section in accessible_sections


# Audit logging for permission checks
def log_permission_check(user, permission, granted, request_path='', ip_address=None):
    """
    Log permission check for audit purposes.
    """
    from .models import RolePermissionAuditLog
    
    try:
        RolePermissionAuditLog.log_action(
            action='permission_checked',
            object_type='permission',
            object_id=0,
            object_name=permission,
            performed_by_id=user.id if user and user.is_authenticated else 0,
            performed_by_username=user.username if user and user.is_authenticated else 'anonymous',
            details={
                'permission': permission,
                'granted': granted,
                'request_path': request_path,
                'timestamp': timezone.now().isoformat()
            },
            ip_address=ip_address
        )
    except Exception as e:
        logger.error(f"Error logging permission check: {e}")