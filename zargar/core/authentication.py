"""
Custom authentication classes for tenant-aware JWT and token authentication.
"""
from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.utils import get_public_schema_name
from django.utils.translation import gettext_lazy as _

from .models import set_current_tenant, get_current_tenant


class TenantAwareJWTAuthentication(JWTAuthentication):
    """
    JWT Authentication that validates tenant context and sets current tenant.
    """
    
    def authenticate(self, request):
        """
        Authenticate JWT token with tenant validation.
        """
        header = self.get_header(request)
        if header is None:
            return None
        
        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None
        
        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        
        # Validate tenant context
        self._validate_tenant_context(validated_token, request)
        
        # Set current tenant in thread-local storage
        self._set_tenant_context(user)
        
        return (user, validated_token)
    
    def get_user(self, validated_token):
        """
        Get user from validated token with tenant context.
        """
        try:
            user_id = validated_token['user_id']
        except KeyError:
            raise InvalidToken(_('Token contained no recognizable user identification'))
        
        # Get current schema
        current_schema = connection.schema_name
        token_schema = validated_token.get('schema', current_schema)
        
        # Validate schema consistency
        if current_schema != token_schema:
            raise AuthenticationFailed(
                _('Token was issued for a different tenant context.')
            )
        
        # Get user from appropriate model
        if current_schema == get_public_schema_name():
            # SuperAdmin authentication
            try:
                from zargar.tenants.admin_models import SuperAdmin
                user = SuperAdmin.objects.get(id=user_id)
            except (SuperAdmin.DoesNotExist, ImportError):
                raise AuthenticationFailed(_('User not found.'))
        else:
            # Regular user authentication
            User = get_user_model()
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise AuthenticationFailed(_('User not found.'))
        
        if not user.is_active:
            raise AuthenticationFailed(_('User is inactive.'))
        
        return user
    
    def _validate_tenant_context(self, validated_token, request):
        """
        Validate that token is being used in correct tenant context.
        """
        current_schema = connection.schema_name
        token_schema = validated_token.get('schema')
        
        if not token_schema:
            raise AuthenticationFailed(
                _('Token does not contain tenant context information.')
            )
        
        if current_schema != token_schema:
            raise AuthenticationFailed(
                _('Token cannot be used in this tenant context.')
            )
        
        # Additional validation for tenant users
        if current_schema != get_public_schema_name():
            is_tenant_user = validated_token.get('is_tenant_user', False)
            if not is_tenant_user:
                raise AuthenticationFailed(
                    _('Invalid token type for tenant context.')
                )
        else:
            # In public schema, only superadmin tokens are valid
            is_superadmin = validated_token.get('is_superadmin', False)
            if not is_superadmin:
                raise AuthenticationFailed(
                    _('Invalid token type for admin context.')
                )
    
    def _set_tenant_context(self, user):
        """
        Set tenant context in thread-local storage.
        """
        # Get current tenant from connection
        current_tenant = get_current_tenant()
        if current_tenant:
            set_current_tenant(current_tenant)


class TenantAwareTokenAuthentication(TokenAuthentication):
    """
    Token authentication that validates tenant context.
    """
    
    def authenticate_credentials(self, key):
        """
        Authenticate token with tenant validation.
        """
        model = self.get_model()
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            raise AuthenticationFailed(_('Invalid token.'))
        
        if not token.user.is_active:
            raise AuthenticationFailed(_('User inactive or deleted.'))
        
        # Validate tenant context
        current_schema = connection.schema_name
        
        # For tenant schemas, ensure user belongs to current tenant
        if current_schema != get_public_schema_name():
            # User should be in tenant schema
            User = get_user_model()
            if not isinstance(token.user, User):
                raise AuthenticationFailed(
                    _('Token user type invalid for tenant context.')
                )
        
        # Set tenant context
        self._set_tenant_context(token.user)
        
        return (token.user, token)
    
    def _set_tenant_context(self, user):
        """
        Set tenant context in thread-local storage.
        """
        current_tenant = get_current_tenant()
        if current_tenant:
            set_current_tenant(current_tenant)


class RoleBasedAuthentication:
    """
    Mixin for role-based authentication checks.
    """
    
    @staticmethod
    def check_role_permission(user, required_roles):
        """
        Check if user has required role.
        """
        if not user or not user.is_authenticated:
            return False
        
        if isinstance(required_roles, str):
            required_roles = [required_roles]
        
        user_role = getattr(user, 'role', None)
        return user_role in required_roles
    
    @staticmethod
    def check_owner_permission(user):
        """
        Check if user is tenant owner.
        """
        return user and user.is_authenticated and getattr(user, 'is_tenant_owner', False)
    
    @staticmethod
    def check_accounting_permission(user):
        """
        Check if user can access accounting features.
        """
        return user and user.is_authenticated and user.can_access_accounting()
    
    @staticmethod
    def check_pos_permission(user):
        """
        Check if user can access POS features.
        """
        return user and user.is_authenticated and user.can_access_pos()
    
    @staticmethod
    def check_user_management_permission(user):
        """
        Check if user can manage other users.
        """
        return user and user.is_authenticated and user.can_manage_users()


class SuperAdminAuthentication:
    """
    Authentication utilities for SuperAdmin users.
    """
    
    @staticmethod
    def is_superadmin(user):
        """
        Check if user is a SuperAdmin.
        """
        if not user or not user.is_authenticated:
            return False
        
        # Check if user is SuperAdmin model instance
        try:
            from zargar.tenants.admin_models import SuperAdmin
            return isinstance(user, SuperAdmin)
        except ImportError:
            return False
    
    @staticmethod
    def can_access_tenant(user, tenant_schema):
        """
        Check if SuperAdmin can access specific tenant.
        """
        if not SuperAdminAuthentication.is_superadmin(user):
            return False
        
        # SuperAdmins can access all tenants by default
        return getattr(user, 'can_access_all_data', True)
    
    @staticmethod
    def can_create_tenants(user):
        """
        Check if SuperAdmin can create tenants.
        """
        if not SuperAdminAuthentication.is_superadmin(user):
            return False
        
        return getattr(user, 'can_create_tenants', True)
    
    @staticmethod
    def can_suspend_tenants(user):
        """
        Check if SuperAdmin can suspend tenants.
        """
        if not SuperAdminAuthentication.is_superadmin(user):
            return False
        
        return getattr(user, 'can_suspend_tenants', True)