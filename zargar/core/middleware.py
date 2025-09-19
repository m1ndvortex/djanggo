"""
Core middleware for ZARGAR jewelry SaaS platform.
"""
import logging
import time
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils import translation
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import get_user_model
from django_tenants.utils import get_tenant_model, get_public_schema_name
from django.db import connection

logger = logging.getLogger(__name__)


class HealthCheckMiddleware(MiddlewareMixin):
    """
    Middleware to handle health check requests without tenant resolution.
    Must be first in middleware stack.
    """
    
    def process_request(self, request):
        if request.path in ['/health/', '/health/db/', '/health/cache/']:
            # Skip tenant middleware for health checks
            return None
        return None


class TenantContextMiddleware(MiddlewareMixin):
    """
    Middleware to add tenant context to all requests.
    """
    
    def process_request(self, request):
        # Skip for public schema
        if connection.schema_name == get_public_schema_name():
            request.tenant = None
            return None
            
        # Get tenant from connection (set by django-tenants)
        try:
            tenant = connection.tenant
            request.tenant = tenant
            
            # Add tenant info to request for templates
            request.tenant_name = tenant.name if tenant else None
            request.tenant_domain = tenant.domain_url if tenant else None
            
        except AttributeError:
            request.tenant = None
            request.tenant_name = None
            request.tenant_domain = None
            
        return None


class TenantIsolationMiddleware(MiddlewareMixin):
    """
    Enhanced middleware to ensure perfect tenant isolation.
    """
    
    def process_request(self, request):
        # Skip for public schema and health checks
        if (connection.schema_name == get_public_schema_name() or 
            request.path.startswith('/health/')):
            return None
            
        # Ensure user belongs to current tenant
        if request.user.is_authenticated and hasattr(request, 'tenant'):
            if request.tenant and hasattr(request.user, 'tenant') and request.user.tenant and request.user.tenant.id != request.tenant.id:
                logger.warning(
                    f"User {request.user.username} attempted to access "
                    f"tenant {request.tenant.name} but belongs to different tenant"
                )
                # Log security violation
                from zargar.core.security_models import SecurityEvent
                SecurityEvent.objects.create(
                    event_type='cross_tenant_access_attempt',
                    user=request.user,
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    details={
                        'attempted_tenant': request.tenant.name,
                        'user_tenant': request.user.tenant.name if request.user.tenant else None,
                        'path': request.path
                    }
                )
                # Redirect to user's proper tenant or logout
                if request.user.tenant:
                    return redirect(f"https://{request.user.tenant.domain_url}{request.path}")
                else:
                    from django.contrib.auth import logout
                    logout(request)
                    return redirect('/login/')
                    
        return None
    
    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PersianLocalizationMiddleware(MiddlewareMixin):
    """
    Middleware to handle Persian localization, RTL layout, and number formatting.
    """
    
    def process_request(self, request):
        # Set Persian as default language
        translation.activate('fa')
        request.LANGUAGE_CODE = 'fa'
        
        # Add Persian context to request
        request.is_rtl = True
        request.language_direction = 'rtl'
        request.persian_locale = True
        
        # Set Persian number formatting context
        request.use_persian_numbers = True
        request.currency_symbol = 'تومان'
        request.thousand_separator = '٬'
        request.decimal_separator = '٫'
        
        return None
    
    def process_response(self, request, response):
        # Ensure Persian language is maintained
        if hasattr(request, 'LANGUAGE_CODE'):
            translation.activate(request.LANGUAGE_CODE)
        return response


class ThemeMiddleware(MiddlewareMixin):
    """
    Middleware to handle theme switching between light and dark modes.
    """
    
    def process_request(self, request):
        # Get theme from cookie, session, or user preference
        theme = None
        
        # 1. Check cookie first
        theme = request.COOKIES.get(settings.THEME_SETTINGS['THEME_COOKIE_NAME'])
        
        # 2. Check session
        if not theme:
            theme = request.session.get('theme')
            
        # 3. Check user preference if authenticated
        if not theme and request.user.is_authenticated:
            if hasattr(request.user, 'theme_preference'):
                theme = request.user.theme_preference
                
        # 4. Use default theme
        if not theme or theme not in settings.THEME_SETTINGS['AVAILABLE_THEMES']:
            theme = settings.THEME_SETTINGS['DEFAULT_THEME']
            
        # Set theme in request context
        request.theme = theme
        request.is_dark_mode = theme == 'dark'
        request.is_light_mode = theme == 'light'
        
        # Set theme-specific CSS classes
        if theme == 'dark':
            request.theme_classes = 'cyber-bg-primary cyber-text-primary dark-mode'
            request.theme_type = 'cybersecurity'
        else:
            request.theme_classes = 'bg-gray-50 text-gray-900 light-mode'
            request.theme_type = 'modern'
            
        return None
    
    def process_response(self, request, response):
        # Update theme cookie if theme was changed
        if hasattr(request, 'theme_changed') and request.theme_changed:
            response.set_cookie(
                settings.THEME_SETTINGS['THEME_COOKIE_NAME'],
                request.theme,
                max_age=settings.THEME_SETTINGS['THEME_COOKIE_AGE'],
                secure=not settings.DEBUG,
                httponly=False,  # Allow JavaScript access for theme switching
                samesite='Lax'
            )
        return response


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware to monitor request performance and log slow requests.
    """
    
    def process_request(self, request):
        request.start_time = time.time()
        return None
    
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Log slow requests (over 1 second)
            if duration > 1.0:
                logger.warning(
                    f"Slow request: {request.method} {request.path} "
                    f"took {duration:.2f}s"
                )
                
            # Add performance header for debugging
            if settings.DEBUG:
                response['X-Response-Time'] = f"{duration:.3f}s"
                
        return response


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all requests for audit purposes.
    """
    
    def process_request(self, request):
        # Skip logging for static files and health checks
        if (request.path.startswith('/static/') or 
            request.path.startswith('/media/') or
            request.path.startswith('/health/')):
            return None
            
        logger.info(
            f"Request: {request.method} {request.path} "
            f"from {self.get_client_ip(request)} "
            f"User: {request.user.username if request.user.is_authenticated else 'Anonymous'} "
            f"Tenant: {getattr(request, 'tenant_name', 'None')}"
        )
        return None
    
    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip