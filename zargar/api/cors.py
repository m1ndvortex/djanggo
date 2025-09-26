"""
CORS configuration for API endpoints with tenant awareness.
"""
from django.conf import settings
from corsheaders.defaults import default_headers
from django.db import connection
from django_tenants.utils import get_public_schema_name


class TenantAwareCORSConfig:
    """
    Tenant-aware CORS configuration that adjusts settings based on tenant context.
    """
    
    @staticmethod
    def get_allowed_origins():
        """
        Get allowed origins based on tenant context.
        """
        base_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
        
        # Add tenant-specific origins if in tenant context
        current_schema = connection.schema_name
        if current_schema != get_public_schema_name():
            # Add tenant subdomain origins
            tenant_domain = getattr(settings, 'TENANT_BASE_DOMAIN', 'zargar.com')
            base_origins.extend([
                f"https://{current_schema}.{tenant_domain}",
                f"http://{current_schema}.{tenant_domain}",
            ])
        
        return base_origins
    
    @staticmethod
    def get_allowed_headers():
        """
        Get allowed headers for API requests.
        """
        return list(default_headers) + [
            'x-tenant-schema',
            'x-api-version',
            'x-client-type',
            'x-device-id',
            'x-request-id',
        ]
    
    @staticmethod
    def get_exposed_headers():
        """
        Get headers to expose to the client.
        """
        return [
            'x-tenant-schema',
            'x-api-version',
            'x-rate-limit-remaining',
            'x-rate-limit-limit',
            'x-rate-limit-reset',
        ]


def cors_allow_all_origins():
    """
    Check if CORS should allow all origins (development only).
    """
    return getattr(settings, 'DEBUG', False)


def cors_allowed_origin_regexes():
    """
    Get regex patterns for allowed origins.
    """
    if getattr(settings, 'DEBUG', False):
        return [
            r"^https?://localhost:\d+$",
            r"^https?://127\.0\.0\.1:\d+$",
            r"^https?://.*\.zargar\.com$",
            r"^https?://.*\.zargar\.local$",
        ]
    
    return [
        r"^https://.*\.zargar\.com$",
    ]


def cors_allow_credentials():
    """
    Check if CORS should allow credentials.
    """
    return True


def cors_allow_headers():
    """
    Get list of allowed headers.
    """
    return TenantAwareCORSConfig.get_allowed_headers()


def cors_expose_headers():
    """
    Get list of headers to expose.
    """
    return TenantAwareCORSConfig.get_exposed_headers()


# CORS settings for different environments
CORS_SETTINGS = {
    'development': {
        'CORS_ALLOW_ALL_ORIGINS': True,
        'CORS_ALLOW_CREDENTIALS': True,
        'CORS_ALLOWED_HEADERS': cors_allow_headers(),
        'CORS_EXPOSE_HEADERS': cors_expose_headers(),
    },
    'production': {
        'CORS_ALLOW_ALL_ORIGINS': False,
        'CORS_ALLOWED_ORIGIN_REGEXES': cors_allowed_origin_regexes(),
        'CORS_ALLOW_CREDENTIALS': True,
        'CORS_ALLOWED_HEADERS': cors_allow_headers(),
        'CORS_EXPOSE_HEADERS': cors_expose_headers(),
    }
}


def get_cors_settings():
    """
    Get CORS settings based on environment.
    """
    if getattr(settings, 'DEBUG', False):
        return CORS_SETTINGS['development']
    else:
        return CORS_SETTINGS['production']