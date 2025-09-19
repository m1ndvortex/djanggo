"""
Custom permission classes for role-based access control.
"""
from rest_framework.permissions import BasePermission
from django.db import connection
from django_tenants.utils import get_public_schema_name
from django.utils.translation import gettext_lazy as _

from .authentication import RoleBasedAuthentication, SuperAdminAuthentication


class TenantPermission(BasePermission):
    """
    Base permission class that ensures user belongs to current tenant.
    """
    message = _('You do not have permission to access this tenant.')
    
    def has_permission(self, request, view):
        """
        Check if user has permission to access current tenant.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        current_schema = connection.schema_name
        
        # In public schema, only SuperAdmins are allowed
        if current_schema == get_public_schema_name():
            return SuperAdminAuthentication.is_superadmin(request.user)
        
        # In tenant schema, regular users are allowed
        # Tenant isolation is handled by django-tenants at database level
        return True
    
    def has_object_permission(self, request, view, obj):
        """
        Check object-level permissions.
        """
        # Object-level tenant isolation is handled by django-tenants
        # All objects in tenant schema belong to that tenant
        return self.has_permission(request, view)


class OwnerPermission(BasePermission):
    """
    Permission class for tenant owners only.
    """
    message = _('Only tenant owners can perform this action.')
    
    def has_permission(self, request, view):
        """
        Check if user is tenant owner.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        return RoleBasedAuthentication.check_owner_permission(request.user)


class AccountingPermission(BasePermission):
    """
    Permission class for accounting access (owners and accountants).
    """
    message = _('You do not have permission to access accounting features.')
    
    def has_permission(self, request, view):
        """
        Check if user can access accounting features.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        return RoleBasedAuthentication.check_accounting_permission(request.user)


class POSPermission(BasePermission):
    """
    Permission class for POS access (all roles).
    """
    message = _('You do not have permission to access POS features.')
    
    def has_permission(self, request, view):
        """
        Check if user can access POS features.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        return RoleBasedAuthentication.check_pos_permission(request.user)


class UserManagementPermission(BasePermission):
    """
    Permission class for user management (owners only).
    """
    message = _('Only tenant owners can manage users.')
    
    def has_permission(self, request, view):
        """
        Check if user can manage other users.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        return RoleBasedAuthentication.check_user_management_permission(request.user)


class SuperAdminPermission(BasePermission):
    """
    Permission class for SuperAdmin access only.
    """
    message = _('Only super administrators can perform this action.')
    
    def has_permission(self, request, view):
        """
        Check if user is SuperAdmin.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        return SuperAdminAuthentication.is_superadmin(request.user)


class TenantCreationPermission(BasePermission):
    """
    Permission class for tenant creation (SuperAdmin only).
    """
    message = _('You do not have permission to create tenants.')
    
    def has_permission(self, request, view):
        """
        Check if user can create tenants.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        return SuperAdminAuthentication.can_create_tenants(request.user)


class TenantSuspensionPermission(BasePermission):
    """
    Permission class for tenant suspension (SuperAdmin only).
    """
    message = _('You do not have permission to suspend tenants.')
    
    def has_permission(self, request, view):
        """
        Check if user can suspend tenants.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        return SuperAdminAuthentication.can_suspend_tenants(request.user)


class RoleBasedPermission(BasePermission):
    """
    Generic role-based permission class.
    """
    required_roles = []  # Override in subclasses
    
    def has_permission(self, request, view):
        """
        Check if user has required role.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not self.required_roles:
            return True
        
        return RoleBasedAuthentication.check_role_permission(
            request.user, 
            self.required_roles
        )


class OwnerOrAccountantPermission(RoleBasedPermission):
    """
    Permission for owners and accountants.
    """
    required_roles = ['owner', 'accountant']
    message = _('Only owners and accountants can perform this action.')


class OwnerOrSalespersonPermission(RoleBasedPermission):
    """
    Permission for owners and salespersons.
    """
    required_roles = ['owner', 'salesperson']
    message = _('Only owners and salespersons can perform this action.')


class AllRolesPermission(RoleBasedPermission):
    """
    Permission for all tenant roles.
    """
    required_roles = ['owner', 'accountant', 'salesperson']
    message = _('You must be a tenant user to perform this action.')


class SelfOrOwnerPermission(BasePermission):
    """
    Permission that allows users to access their own data or owners to access any data.
    """
    message = _('You can only access your own data unless you are an owner.')
    
    def has_permission(self, request, view):
        """
        Basic authentication check.
        """
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Check if user can access specific object.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Owners can access everything
        if RoleBasedAuthentication.check_owner_permission(request.user):
            return True
        
        # Users can access their own data
        if hasattr(obj, 'created_by') and obj.created_by == request.user:
            return True
        
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        if hasattr(obj, 'id') and obj.id == request.user.id:
            return True
        
        return False


class ReadOnlyOrOwnerPermission(BasePermission):
    """
    Permission that allows read-only access to all users, but write access only to owners.
    """
    message = _('Only owners can modify this data.')
    
    def has_permission(self, request, view):
        """
        Check basic permission.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read permissions for all authenticated users
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Write permissions only for owners
        return RoleBasedAuthentication.check_owner_permission(request.user)
    
    def has_object_permission(self, request, view, obj):
        """
        Check object-level permission.
        """
        return self.has_permission(request, view)