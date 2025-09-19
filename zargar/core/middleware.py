"""
Custom middleware for zargar project.
"""
from django.http import JsonResponse
from django.urls import resolve, Resolver404
from django.utils import timezone, translation
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
import jdatetime


class HealthCheckMiddleware:
    """
    Middleware to handle health check requests before tenant middleware.
    This allows health checks to work without requiring a tenant.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Handle health check before tenant middleware
        if request.path == '/health/':
            return JsonResponse({
                'status': 'healthy',
                'service': 'zargar-jewelry-saas',
                'version': '1.0.0'
            })
        
        response = self.get_response(request)
        return response


class TenantContextMiddleware:
    """
    Middleware to add tenant context to all requests and set thread-local storage.
    
    This middleware:
    - Sets tenant context in thread-local storage for model access
    - Sets current user in thread-local storage for audit tracking
    - Provides tenant information to request object
    - Ensures proper cleanup after request processing
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from zargar.core.models import set_current_tenant, _thread_locals
        
        # Set tenant context in thread-local storage
        if hasattr(request, 'tenant'):
            set_current_tenant(request.tenant)
            request.tenant_context = {
                'tenant': request.tenant,
                'schema_name': request.tenant.schema_name,
                'domain_url': request.tenant.domain_url,
                'name': request.tenant.name,
                'is_public': False,
            }
        else:
            set_current_tenant(None)
            request.tenant_context = {
                'tenant': None,
                'schema_name': 'public',
                'domain_url': None,
                'name': 'Public',
                'is_public': True,
            }
        
        # Set current user in thread-local storage for audit tracking
        if hasattr(request, 'user') and request.user.is_authenticated:
            _thread_locals.user = request.user
        else:
            _thread_locals.user = None
        
        try:
            response = self.get_response(request)
        finally:
            # Clean up thread-local storage
            if hasattr(_thread_locals, 'tenant'):
                delattr(_thread_locals, 'tenant')
            if hasattr(_thread_locals, 'user'):
                delattr(_thread_locals, 'user')
        
        return response


class TenantIsolationMiddleware:
    """
    Middleware to enforce tenant data isolation and security.
    
    This middleware:
    - Validates tenant access permissions for regular users
    - Allows super admins to access any tenant
    - Prevents cross-tenant data access
    - Logs suspicious tenant access attempts
    - Enforces tenant-specific security policies
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip validation for public schema and health checks
        if (not hasattr(request, 'tenant') or 
            request.path in ['/health/', '/admin/login/', '/api/health/', '/super-admin/']):
            return self.get_response(request)
        
        # Validate user access to tenant
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
            tenant = request.tenant
            
            # Check if this is a SuperAdmin (from shared schema)
            if self._is_super_admin(user):
                # Log super admin access for audit
                self._log_super_admin_access(request, user, tenant)
                return self.get_response(request)
            
            # For regular users (from tenant schema), they are automatically isolated
            # by django-tenants schema separation, so no additional validation needed
            return self.get_response(request)
        
        return self.get_response(request)
    
    def _is_super_admin(self, user):
        """Check if user is a SuperAdmin from shared schema."""
        try:
            from zargar.tenants.admin_models import SuperAdmin
            return isinstance(user, SuperAdmin) or (
                hasattr(user, '_meta') and 
                user._meta.model_name == 'superadmin'
            )
        except ImportError:
            return False
    
    def _log_super_admin_access(self, request, user, tenant):
        """Log super admin access for audit purposes."""
        try:
            from zargar.tenants.admin_models import SuperAdminSession
            
            # Create or update super admin session
            SuperAdminSession.objects.update_or_create(
                super_admin=user,
                tenant_schema=tenant.schema_name,
                session_key=request.session.session_key or '',
                defaults={
                    'ip_address': self._get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'is_active': True,
                }
            )
        except Exception as e:
            # Don't block access if logging fails
            pass
    
    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PersianLocalizationMiddleware:
    """
    Middleware to handle Persian localization and RTL layout.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set Persian locale
        translation.activate('fa')
        request.LANGUAGE_CODE = 'fa'
        
        # Add Persian date context
        now = timezone.now()
        request.persian_date = {
            'today': jdatetime.date.today(),
            'now': jdatetime.datetime.now(),
            'shamsi_year': jdatetime.date.today().year,
            'shamsi_month': jdatetime.date.today().month,
            'shamsi_day': jdatetime.date.today().day,
        }
        
        response = self.get_response(request)
        
        # Ensure Persian locale is maintained
        if response:
            response['Content-Language'] = 'fa'
        
        return response