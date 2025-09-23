"""
Tenant schema URL configuration for zargar project.
This handles individual jewelry shop subdomains.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.decorators.cache import never_cache


@never_cache
def health_check(request):
    """Health check endpoint for tenant schemas."""
    tenant_name = getattr(request, 'tenant', None)
    return JsonResponse({
        'status': 'healthy',
        'service': 'zargar-jewelry-saas',
        'version': '1.0.0',
        'schema': 'tenant',
        'tenant': tenant_name.name if tenant_name else 'unknown'
    })


urlpatterns = [
    # Tenant admin (limited access - preserved for tenant users)
    path('admin/', admin.site.urls),
    
    # Health check
    path('health/', health_check, name='health_check'),
    
    # Main tenant dashboard
    path('', include('zargar.core.tenant_urls')),
    
    # API endpoints (tenant-specific)
    path('api/', include('zargar.api.urls')),
    
    # Business modules
    path('jewelry/', include('zargar.jewelry.urls')),
    path('accounting/', include('zargar.accounting.urls')),
    path('customers/', include('zargar.customers.urls')),
    path('gold-installments/', include('zargar.gold_installments.urls')),
    path('pos/', include('zargar.pos.urls')),
    path('reports/', include('zargar.reports.urls')),
    
    # Authentication URLs
    path('auth/', include('django.contrib.auth.urls')),
    
    # 2FA URLs (placeholder - will be implemented in later tasks)
    # path('2fa/', include('django_otp.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Add debug toolbar in development
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns