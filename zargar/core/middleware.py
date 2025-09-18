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
    Middleware to add tenant context to all requests.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Add tenant information to request
        if hasattr(request, 'tenant'):
            request.tenant_context = {
                'tenant': request.tenant,
                'schema_name': request.tenant.schema_name,
                'domain_url': request.tenant.domain_url,
                'name': request.tenant.name,
            }
        else:
            request.tenant_context = None
        
        response = self.get_response(request)
        return response


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