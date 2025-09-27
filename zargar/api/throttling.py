"""
Custom throttling classes for API rate limiting with tenant awareness.
"""
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django.core.cache import cache
from django.db import connection
from django_tenants.utils import get_public_schema_name
from django.utils.translation import gettext_lazy as _


class TenantAPIThrottle(UserRateThrottle):
    """
    Tenant-aware API throttling that applies different rates per tenant.
    """
    scope = 'tenant_api'
    
    def get_cache_key(self, request, view):
        """
        Generate cache key that includes tenant context.
        """
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        
        # Include tenant schema in cache key for isolation
        tenant_schema = connection.schema_name
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': f"{tenant_schema}:{ident}"
        }
    
    def get_rate(self):
        """
        Get throttle rate based on tenant and user type.
        """
        # Different rates for different contexts
        current_schema = connection.schema_name
        
        if current_schema == get_public_schema_name():
            # Super admin context - higher limits
            return '1000/hour'
        else:
            # Tenant context - standard limits
            return '500/hour'


class TenantBurstThrottle(UserRateThrottle):
    """
    Burst throttling for short-term rate limiting.
    """
    scope = 'tenant_burst'
    
    def get_cache_key(self, request, view):
        """
        Generate cache key that includes tenant context.
        """
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        
        tenant_schema = connection.schema_name
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': f"{tenant_schema}:{ident}"
        }
    
    def get_rate(self):
        """
        Get burst rate - more restrictive for short periods.
        """
        return '60/min'


class TenantAnonThrottle(AnonRateThrottle):
    """
    Throttling for anonymous users with tenant awareness.
    """
    scope = 'tenant_anon'
    
    def get_cache_key(self, request, view):
        """
        Generate cache key for anonymous users with tenant context.
        """
        ident = self.get_ident(request)
        tenant_schema = connection.schema_name
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': f"{tenant_schema}:{ident}"
        }
    
    def get_rate(self):
        """
        Get rate for anonymous users - more restrictive.
        """
        return '100/hour'


class POSThrottle(UserRateThrottle):
    """
    Special throttling for POS operations - higher limits for sales.
    """
    scope = 'pos_api'
    
    def get_cache_key(self, request, view):
        """
        Generate cache key for POS operations.
        """
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        
        tenant_schema = connection.schema_name
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': f"{tenant_schema}:{ident}"
        }
    
    def get_rate(self):
        """
        Higher rate limits for POS operations.
        """
        return '1000/hour'


class AccountingThrottle(UserRateThrottle):
    """
    Throttling for accounting operations - moderate limits.
    """
    scope = 'accounting_api'
    
    def get_cache_key(self, request, view):
        """
        Generate cache key for accounting operations.
        """
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        
        tenant_schema = connection.schema_name
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': f"{tenant_schema}:{ident}"
        }
    
    def get_rate(self):
        """
        Moderate rate limits for accounting operations.
        """
        return '300/hour'


class ReportingThrottle(UserRateThrottle):
    """
    Throttling for reporting operations - lower limits due to resource intensity.
    """
    scope = 'reporting_api'
    
    def get_cache_key(self, request, view):
        """
        Generate cache key for reporting operations.
        """
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        
        tenant_schema = connection.schema_name
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': f"{tenant_schema}:{ident}"
        }
    
    def get_rate(self):
        """
        Lower rate limits for resource-intensive reporting operations.
        """
        return '50/hour'


class SuperAdminThrottle(UserRateThrottle):
    """
    Throttling for super admin operations - highest limits.
    """
    scope = 'superadmin_api'
    
    def allow_request(self, request, view):
        """
        Only apply throttling to super admin users.
        """
        # Check if user is super admin
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            from zargar.tenants.admin_models import SuperAdmin
            if not isinstance(request.user, SuperAdmin):
                return False
        except ImportError:
            return False
        
        return super().allow_request(request, view)
    
    def get_rate(self):
        """
        Highest rate limits for super admin operations.
        """
        return '2000/hour'


class TenantCreationThrottle(UserRateThrottle):
    """
    Special throttling for tenant creation - very restrictive.
    """
    scope = 'tenant_creation'
    
    def get_rate(self):
        """
        Very restrictive rate for tenant creation.
        """
        return '10/day'


class LoginThrottle(AnonRateThrottle):
    """
    Throttling for login attempts to prevent brute force attacks.
    """
    scope = 'login_attempts'
    
    def get_cache_key(self, request, view):
        """
        Generate cache key based on IP and username if provided.
        """
        ident = self.get_ident(request)
        
        # Include username in throttling if provided
        username = request.data.get('username') if hasattr(request, 'data') else None
        if username:
            ident = f"{ident}:{username}"
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }
    
    def get_rate(self):
        """
        Restrictive rate for login attempts.
        """
        return '10/min'


class PasswordResetThrottle(AnonRateThrottle):
    """
    Throttling for password reset requests.
    """
    scope = 'password_reset'
    
    def get_rate(self):
        """
        Very restrictive rate for password reset requests.
        """
        return '5/hour'


class TwoFactorThrottle(UserRateThrottle):
    """
    Throttling for 2FA verification attempts.
    """
    scope = 'two_factor'
    
    def get_rate(self):
        """
        Moderate throttling for 2FA attempts.
        """
        return '20/hour'


# Custom throttle classes for different API endpoints
class JewelryAPIThrottle(TenantAPIThrottle):
    """Throttling for jewelry management API."""
    scope = 'jewelry_api'


class CustomerAPIThrottle(TenantAPIThrottle):
    """Throttling for customer management API."""
    scope = 'customer_api'


class SalesAPIThrottle(POSThrottle):
    """Throttling for sales API - uses POS throttling."""
    pass


class InventoryAPIThrottle(TenantAPIThrottle):
    """Throttling for inventory management API."""
    scope = 'inventory_api'


class GoldPriceAPIThrottle(UserRateThrottle):
    """
    Throttling for gold price API calls - external service integration.
    """
    scope = 'gold_price_api'
    
    def get_rate(self):
        """
        Moderate rate for gold price API calls.
        """
        return '100/hour'