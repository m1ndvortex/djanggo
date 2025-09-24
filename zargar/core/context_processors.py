"""
Context processors for the ZARGAR jewelry SaaS platform.
"""

from django.conf import settings
from django.utils import timezone


def domain_settings(request):
    """
    Add domain-related settings to template context.
    """
    return {
        'TENANT_BASE_DOMAIN': getattr(settings, 'TENANT_BASE_DOMAIN', 'zargar.com'),
        'TENANT_SUBDOMAIN_SEPARATOR': getattr(settings, 'TENANT_SUBDOMAIN_SEPARATOR', '.'),
        'TENANT_DOMAIN_PROTOCOL': getattr(settings, 'TENANT_DOMAIN_PROTOCOL', 'https'),
    }


def site_settings(request):
    """
    Add site-related settings to template context.
    """
    # Use domain from request or fallback to base domain
    site_domain = getattr(settings, 'TENANT_BASE_DOMAIN', 'zargar.com')
    
    # Try to get domain from request host
    if hasattr(request, 'get_host'):
        try:
            host = request.get_host()
            if host and '.' in host:
                site_domain = host
        except:
            pass
    
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'ZARGAR'),
        'SITE_DOMAIN': site_domain,
        'SITE_URL': f"{getattr(settings, 'TENANT_DOMAIN_PROTOCOL', 'https')}://{site_domain}",
    }


def system_info(request):
    """
    Add system information to template context.
    """
    return {
        'CURRENT_TIME': timezone.now(),
        'DEBUG_MODE': getattr(settings, 'DEBUG', False),
        'ENVIRONMENT': getattr(settings, 'ENVIRONMENT', 'development'),
    }


def tenant_context(request):
    """
    Add tenant-specific context information.
    """
    context = {}
    
    # Check if we have a tenant in the request
    if hasattr(request, 'tenant') and request.tenant:
        tenant = request.tenant
        context.update({
            'current_tenant': tenant,
            'tenant_name': tenant.name,
            'tenant_schema': tenant.schema_name,
            'tenant_domain': tenant.domain_url,
            'tenant_full_url': f"{getattr(settings, 'TENANT_DOMAIN_PROTOCOL', 'https')}://{tenant.domain_url}.{getattr(settings, 'TENANT_BASE_DOMAIN', 'zargar.com')}",
        })
    
    return context


def persian_context(request):
    """
    Add Persian/Farsi localization context.
    """
    return {
        'LANGUAGE_CODE': getattr(settings, 'LANGUAGE_CODE', 'fa'),
        'LANGUAGE_BIDI': True,
        'USE_JALALI': getattr(settings, 'USE_JALALI', True),
    }


def theme_context(request):
    """
    Add theme-related context.
    """
    theme_settings = getattr(settings, 'THEME_SETTINGS', {})
    current_theme = 'light'
    
    # Try to get theme from cookie
    if hasattr(request, 'COOKIES'):
        cookie_name = theme_settings.get('THEME_COOKIE_NAME', 'zargar_theme')
        current_theme = request.COOKIES.get(cookie_name, theme_settings.get('DEFAULT_THEME', 'light'))
    
    return {
        'CURRENT_THEME': current_theme,
        'AVAILABLE_THEMES': theme_settings.get('AVAILABLE_THEMES', ['light', 'dark']),
        'THEME_SETTINGS': theme_settings,
    }


def admin_context(request):
    """
    Add admin-specific context for super admin panel.
    """
    context = {}
    
    # Check if user is a super admin
    if hasattr(request, 'user') and request.user.is_authenticated:
        # Check if user is a SuperAdmin (from tenants app)
        try:
            from zargar.tenants.models import SuperAdmin
            is_super_admin = SuperAdmin.objects.filter(
                username=request.user.username
            ).exists()
            context['is_super_admin'] = is_super_admin
        except:
            context['is_super_admin'] = False
        
        # Add user info
        context.update({
            'current_user': request.user,
            'user_full_name': request.user.get_full_name() or request.user.username,
            'user_is_staff': getattr(request.user, 'is_staff', False),
            'user_is_superuser': getattr(request.user, 'is_superuser', False),
        })
    
    return context