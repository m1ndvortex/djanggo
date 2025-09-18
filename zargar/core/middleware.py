"""
Custom middleware for zargar project.
"""
from django.http import JsonResponse
from django.urls import resolve, Resolver404


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