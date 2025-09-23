"""
URL configuration for zargar project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.decorators.cache import never_cache


@never_cache
def health_check(request):
    """Health check endpoint for Docker containers and load balancers."""
    return JsonResponse({
        'status': 'healthy',
        'service': 'zargar-jewelry-saas',
        'version': '1.0.0'
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    path('api/', include('zargar.api.urls')),
    path('pos/', include('zargar.pos.urls')),
    path('super-panel/', include('zargar.admin_panel.urls', namespace='admin_panel')),
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