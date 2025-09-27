"""
Custom authentication backends for tenant-aware authentication.
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context


class TenantAwareAuthBackend(ModelBackend):
    """
    Authentication backend that handles both SuperAdmin (shared schema) 
    and regular User (tenant schema) authentication.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user in the appropriate schema.
        
        For public schema: Try SuperAdmin authentication
        For tenant schema: Try regular User authentication
        """
        if not username or not password:
            return None
        
        # Get current schema
        current_schema = connection.schema_name
        
        if current_schema == get_public_schema_name():
            # In public schema - authenticate SuperAdmin
            return self._authenticate_superadmin(username, password)
        else:
            # In tenant schema - authenticate regular User
            return self._authenticate_user(username, password)
    
    def _authenticate_superadmin(self, username, password):
        """Authenticate SuperAdmin in public schema."""
        try:
            from zargar.tenants.admin_models import SuperAdmin
            
            try:
                user = SuperAdmin.objects.get(username=username)
            except SuperAdmin.DoesNotExist:
                # Run the default password hasher once to reduce the timing
                # difference between an existing and a nonexistent user
                SuperAdmin().set_password(password)
                return None
            
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
                
        except ImportError:
            pass
        
        return None
    
    def _authenticate_user(self, username, password):
        """Authenticate regular User in tenant schema."""
        UserModel = get_user_model()
        
        try:
            user = UserModel.objects.get(username=username)
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user
            UserModel().set_password(password)
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None
    
    def get_user(self, user_id):
        """
        Get user by ID from the appropriate schema.
        """
        current_schema = connection.schema_name
        
        if current_schema == get_public_schema_name():
            # Try to get SuperAdmin
            try:
                from zargar.tenants.admin_models import SuperAdmin
                return SuperAdmin.objects.get(pk=user_id)
            except (SuperAdmin.DoesNotExist, ImportError):
                return None
        else:
            # Try to get regular User
            UserModel = get_user_model()
            try:
                return UserModel.objects.get(pk=user_id)
            except UserModel.DoesNotExist:
                return None
    
    def user_can_authenticate(self, user):
        """
        Reject users with is_active=False. Custom user models that don't have
        an `is_active` field are allowed.
        """
        is_active = getattr(user, 'is_active', None)
        return is_active or is_active is None


class SuperAdminBackend(ModelBackend):
    """
    Specialized backend for SuperAdmin authentication.
    Only works in public schema.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """Authenticate SuperAdmin only."""
        if connection.schema_name != get_public_schema_name():
            return None
        
        try:
            from zargar.tenants.admin_models import SuperAdmin
            
            try:
                user = SuperAdmin.objects.get(username=username)
            except SuperAdmin.DoesNotExist:
                SuperAdmin().set_password(password)
                return None
            
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
                
        except ImportError:
            pass
        
        return None
    
    def get_user(self, user_id):
        """Get SuperAdmin by ID."""
        if connection.schema_name != get_public_schema_name():
            return None
        
        try:
            from zargar.tenants.admin_models import SuperAdmin
            return SuperAdmin.objects.get(pk=user_id)
        except (SuperAdmin.DoesNotExist, ImportError):
            return None


class TenantUserBackend(ModelBackend):
    """
    Specialized backend for tenant User authentication.
    Only works in tenant schemas.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """Authenticate tenant User only."""
        if connection.schema_name == get_public_schema_name():
            return None
        
        UserModel = get_user_model()
        
        try:
            user = UserModel.objects.get(username=username)
        except UserModel.DoesNotExist:
            UserModel().set_password(password)
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None
    
    def get_user(self, user_id):
        """Get tenant User by ID."""
        if connection.schema_name == get_public_schema_name():
            return None
        
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None