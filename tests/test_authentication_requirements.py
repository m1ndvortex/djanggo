"""
Test authentication system against specific requirements.
"""
import pytest
from django.test import TestCase
from django.contrib.auth import authenticate
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework_simplejwt.tokens import RefreshToken

from zargar.tenants.models import Tenant, Domain
from zargar.tenants.admin_models import SuperAdmin
from zargar.core.models import User
from zargar.core.authentication import (
    TenantAwareJWTAuthentication,
    RoleBasedAuthentication,
    SuperAdminAuthentication
)
from zargar.core.serializers import TenantAwareTokenObtainPairSerializer


class AuthenticationRequirementsTestCase(TenantTestCase):
    """
    Test authentication system against task requirements:
    - Create custom User model extending AbstractUser with tenant relationship
    - Implement role-based access control with Owner, Accountant, Salesperson roles
    - Configure DRF token authentication with JWT support for API access
    - Write unit tests for authentication and authorization logic
    """
    
    def test_requirement_custom_user_model_with_tenant_relationship(self):
        """
        Requirement: Create custom User model extending AbstractUser with tenant relationship
        """
        # Create user in tenant schema
        user = User.objects.create_user(
            username='tenant_user',
            email='user@tenant.com',
            password='pass123',
            role='owner',
            persian_first_name='علی',
            persian_last_name='احمدی',
            phone_number='09123456789',
            theme_preference='dark'
        )
        
        # Verify User extends AbstractUser
        from django.contrib.auth.models import AbstractUser
        self.assertTrue(issubclass(User, AbstractUser))
        
        # Verify tenant relationship (implicit through schema isolation)
        self.assertEqual(connection.schema_name, self.tenant.schema_name)
        
        # Verify additional fields
        self.assertEqual(user.role, 'owner')
        self.assertEqual(user.persian_first_name, 'علی')
        self.assertEqual(user.persian_last_name, 'احمدی')
        self.assertEqual(user.phone_number, '09123456789')
        self.assertEqual(user.theme_preference, 'dark')
        self.assertFalse(user.is_2fa_enabled)
        
        # Verify Persian name functionality
        self.assertEqual(user.full_persian_name, 'علی احمدی')
        self.assertEqual(str(user), 'علی احمدی')
        
        # Verify audit fields
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)
    
    def test_requirement_role_based_access_control(self):
        """
        Requirement: Implement role-based access control with Owner, Accountant, Salesperson roles
        """
        # Create users with all three roles
        owner = User.objects.create_user(
            username='owner',
            password='pass123',
            role='owner'
        )
        
        accountant = User.objects.create_user(
            username='accountant',
            password='pass123',
            role='accountant'
        )
        
        salesperson = User.objects.create_user(
            username='salesperson',
            password='pass123',
            role='salesperson'
        )
        
        # Test Owner role permissions
        self.assertEqual(owner.role, 'owner')
        self.assertTrue(owner.is_tenant_owner)
        self.assertTrue(owner.can_access_accounting())
        self.assertTrue(owner.can_access_pos())
        self.assertTrue(owner.can_manage_users())
        
        # Test Accountant role permissions
        self.assertEqual(accountant.role, 'accountant')
        self.assertFalse(accountant.is_tenant_owner)
        self.assertTrue(accountant.can_access_accounting())
        self.assertTrue(accountant.can_access_pos())
        self.assertFalse(accountant.can_manage_users())
        
        # Test Salesperson role permissions
        self.assertEqual(salesperson.role, 'salesperson')
        self.assertFalse(salesperson.is_tenant_owner)
        self.assertFalse(salesperson.can_access_accounting())
        self.assertTrue(salesperson.can_access_pos())
        self.assertFalse(salesperson.can_manage_users())
        
        # Test role-based authentication utilities
        self.assertTrue(RoleBasedAuthentication.check_role_permission(owner, 'owner'))
        self.assertTrue(RoleBasedAuthentication.check_role_permission(accountant, 'accountant'))
        self.assertTrue(RoleBasedAuthentication.check_role_permission(salesperson, 'salesperson'))
        
        # Test cross-role permissions
        self.assertFalse(RoleBasedAuthentication.check_role_permission(accountant, 'owner'))
        self.assertFalse(RoleBasedAuthentication.check_role_permission(salesperson, 'owner'))
        self.assertFalse(RoleBasedAuthentication.check_role_permission(salesperson, 'accountant'))
        
        # Test multiple role checking
        self.assertTrue(RoleBasedAuthentication.check_role_permission(owner, ['owner', 'accountant']))
        self.assertTrue(RoleBasedAuthentication.check_role_permission(accountant, ['owner', 'accountant']))
        self.assertFalse(RoleBasedAuthentication.check_role_permission(salesperson, ['owner', 'accountant']))
    
    def test_requirement_drf_token_authentication_with_jwt(self):
        """
        Requirement: Configure DRF token authentication with JWT support for API access
        """
        # Create user
        user = User.objects.create_user(
            username='jwt_user',
            email='jwt@test.com',
            password='pass123',
            role='owner'
        )
        
        # Test JWT token generation
        refresh = RefreshToken.for_user(user)
        
        # Add tenant-specific claims
        refresh['username'] = user.username
        refresh['role'] = user.role
        refresh['schema'] = connection.schema_name
        refresh['is_tenant_user'] = True
        refresh['tenant_schema'] = connection.schema_name
        
        # Verify token contains expected claims
        self.assertEqual(refresh['username'], 'jwt_user')
        self.assertEqual(refresh['role'], 'owner')
        self.assertEqual(refresh['schema'], self.tenant.schema_name)
        self.assertTrue(refresh['is_tenant_user'])
        self.assertEqual(refresh['tenant_schema'], self.tenant.schema_name)
        
        # Test access token
        access_token = refresh.access_token
        self.assertEqual(access_token['username'], 'jwt_user')
        self.assertEqual(access_token['role'], 'owner')
        
        # Test custom JWT serializer
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post('/api/auth/token/')
        
        serializer = TenantAwareTokenObtainPairSerializer(
            data={'username': 'jwt_user', 'password': 'pass123'},
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid())
        validated_data = serializer.validated_data
        
        self.assertIn('access', validated_data)
        self.assertIn('refresh', validated_data)
        self.assertIn('user', validated_data)
        self.assertEqual(validated_data['user']['username'], 'jwt_user')
        self.assertEqual(validated_data['user']['role'], 'owner')
    
    def test_requirement_authentication_and_authorization_logic(self):
        """
        Requirement: Write unit tests for authentication and authorization logic
        """
        # Create users for testing
        owner = User.objects.create_user(
            username='auth_owner',
            password='ownerpass123',
            role='owner'
        )
        
        accountant = User.objects.create_user(
            username='auth_accountant',
            password='accountantpass123',
            role='accountant'
        )
        
        salesperson = User.objects.create_user(
            username='auth_salesperson',
            password='salespass123',
            role='salesperson'
        )
        
        # Test authentication logic
        # Successful authentication
        authenticated_user = authenticate(username='auth_owner', password='ownerpass123')
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user.id, owner.id)
        
        authenticated_user = authenticate(username='auth_accountant', password='accountantpass123')
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user.id, accountant.id)
        
        authenticated_user = authenticate(username='auth_salesperson', password='salespass123')
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user.id, salesperson.id)
        
        # Failed authentication
        self.assertIsNone(authenticate(username='auth_owner', password='wrongpass'))
        self.assertIsNone(authenticate(username='nonexistent', password='anypass'))
        
        # Test authorization logic
        # Owner permissions
        self.assertTrue(RoleBasedAuthentication.check_owner_permission(owner))
        self.assertTrue(RoleBasedAuthentication.check_accounting_permission(owner))
        self.assertTrue(RoleBasedAuthentication.check_pos_permission(owner))
        self.assertTrue(RoleBasedAuthentication.check_user_management_permission(owner))
        
        # Accountant permissions
        self.assertFalse(RoleBasedAuthentication.check_owner_permission(accountant))
        self.assertTrue(RoleBasedAuthentication.check_accounting_permission(accountant))
        self.assertTrue(RoleBasedAuthentication.check_pos_permission(accountant))
        self.assertFalse(RoleBasedAuthentication.check_user_management_permission(accountant))
        
        # Salesperson permissions
        self.assertFalse(RoleBasedAuthentication.check_owner_permission(salesperson))
        self.assertFalse(RoleBasedAuthentication.check_accounting_permission(salesperson))
        self.assertTrue(RoleBasedAuthentication.check_pos_permission(salesperson))
        self.assertFalse(RoleBasedAuthentication.check_user_management_permission(salesperson))
        
        # Test unauthenticated user
        from django.contrib.auth.models import AnonymousUser
        anonymous = AnonymousUser()
        
        self.assertFalse(RoleBasedAuthentication.check_owner_permission(anonymous))
        self.assertFalse(RoleBasedAuthentication.check_accounting_permission(anonymous))
        self.assertFalse(RoleBasedAuthentication.check_pos_permission(anonymous))
        self.assertFalse(RoleBasedAuthentication.check_user_management_permission(anonymous))
    
    def test_tenant_isolation_in_authentication(self):
        """
        Test that authentication properly isolates tenants.
        """
        # Create user in current tenant
        user1 = User.objects.create_user(
            username='tenant1_user',
            password='pass123',
            role='owner'
        )
        
        # Test that user exists in current tenant
        self.assertEqual(User.objects.filter(username='tenant1_user').count(), 1)
        self.assertEqual(connection.schema_name, self.tenant.schema_name)
        
        # Test authentication in current tenant
        authenticated_user = authenticate(username='tenant1_user', password='pass123')
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user.id, user1.id)
        
        # Test that non-existent user cannot authenticate
        authenticated_user = authenticate(username='nonexistent_user', password='pass123')
        self.assertIsNone(authenticated_user)
        
        # Test that wrong password fails
        authenticated_user = authenticate(username='tenant1_user', password='wrongpass')
        self.assertIsNone(authenticated_user)
        
        # Verify tenant isolation by checking schema
        self.assertEqual(connection.schema_name, self.tenant.schema_name)
        self.assertNotEqual(connection.schema_name, get_public_schema_name())


class SuperAdminRequirementsTestCase(TestCase):
    """
    Test SuperAdmin functionality as part of authentication system.
    """
    
    def test_superadmin_vs_tenant_user_distinction(self):
        """
        Test that SuperAdmin and tenant User are properly distinguished.
        """
        # Create SuperAdmin in public schema
        with schema_context(get_public_schema_name()):
            superadmin = SuperAdmin.objects.create_user(
                username='superadmin',
                email='super@admin.com',
                password='superpass123',
                is_superuser=True,
                is_staff=True
            )
            
            # Test SuperAdmin identification
            self.assertTrue(SuperAdminAuthentication.is_superadmin(superadmin))
            self.assertTrue(superadmin.is_superuser)
            self.assertTrue(superadmin.is_staff)
        
        # Create tenant and regular user
        tenant = Tenant(
            schema_name='test_superadmin_tenant',
            name='Test SuperAdmin Tenant',
            owner_name='Test Owner',
            owner_email='owner@test.com'
        )
        tenant.save()
        
        domain = Domain(
            domain='superadmin.localhost',
            tenant=tenant,
            is_primary=True
        )
        domain.save()
        
        with schema_context(tenant.schema_name):
            user = User.objects.create_user(
                username='tenant_owner',
                email='owner@tenant.com',
                password='pass123',
                role='owner'
            )
            
            # Test that tenant user is not SuperAdmin
            self.assertFalse(SuperAdminAuthentication.is_superadmin(user))
            self.assertFalse(user.is_superuser)
            self.assertFalse(user.is_staff)
            
            # Test tenant user permissions
            self.assertTrue(user.is_tenant_owner)
            self.assertTrue(user.can_manage_users())
            
            # But cannot do SuperAdmin operations
            self.assertFalse(SuperAdminAuthentication.can_create_tenants(user))
            self.assertFalse(SuperAdminAuthentication.can_suspend_tenants(user))


if __name__ == '__main__':
    pytest.main([__file__])