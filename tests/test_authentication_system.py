"""
Comprehensive tests for tenant-aware authentication system.
"""
import pytest
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import authenticate
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
import json

from zargar.tenants.models import Tenant, Domain
from zargar.tenants.admin_models import SuperAdmin
from zargar.core.models import User
from zargar.core.authentication import (
    TenantAwareJWTAuthentication,
    RoleBasedAuthentication,
    SuperAdminAuthentication
)
from zargar.core.permissions import (
    TenantPermission,
    OwnerPermission,
    AccountingPermission,
    POSPermission,
    UserManagementPermission
)


class AuthenticationSystemTestCase(TransactionTestCase):
    """
    Test authentication system with proper tenant isolation.
    """
    
    def setUp(self):
        """Set up test data."""
        # Create tenant
        self.tenant = Tenant(
            schema_name='test_jewelry_shop',
            name='Test Jewelry Shop',
            owner_name='Test Owner',
            owner_email='owner@test.com'
        )
        self.tenant.save()
        
        # Create domain
        self.domain = Domain(
            domain='test.localhost',
            tenant=self.tenant,
            is_primary=True
        )
        self.domain.save()
        
        # Create SuperAdmin in public schema
        with schema_context(get_public_schema_name()):
            self.superadmin = SuperAdmin.objects.create_user(
                username='superadmin',
                email='super@admin.com',
                password='superpass123',
                is_superuser=True,
                is_staff=True
            )
    
    def test_superadmin_authentication_in_public_schema(self):
        """Test SuperAdmin authentication in public schema."""
        with schema_context(get_public_schema_name()):
            # Test successful authentication
            user = authenticate(username='superadmin', password='superpass123')
            self.assertIsNotNone(user)
            self.assertIsInstance(user, SuperAdmin)
            self.assertTrue(user.is_superuser)
            
            # Test failed authentication
            user = authenticate(username='superadmin', password='wrongpass')
            self.assertIsNone(user)
    
    def test_tenant_user_creation_and_authentication(self):
        """Test tenant user creation and authentication."""
        with schema_context(self.tenant.schema_name):
            # Create tenant users with different roles
            owner = User.objects.create_user(
                username='owner',
                email='owner@tenant.com',
                password='ownerpass123',
                role='owner'
            )
            
            accountant = User.objects.create_user(
                username='accountant',
                email='accountant@tenant.com',
                password='accountantpass123',
                role='accountant'
            )
            
            salesperson = User.objects.create_user(
                username='salesperson',
                email='sales@tenant.com',
                password='salespass123',
                role='salesperson'
            )
            
            # Test authentication for each role
            user = authenticate(username='owner', password='ownerpass123')
            self.assertIsNotNone(user)
            self.assertEqual(user.role, 'owner')
            self.assertTrue(user.is_tenant_owner)
            
            user = authenticate(username='accountant', password='accountantpass123')
            self.assertIsNotNone(user)
            self.assertEqual(user.role, 'accountant')
            self.assertFalse(user.is_tenant_owner)
            
            user = authenticate(username='salesperson', password='salespass123')
            self.assertIsNotNone(user)
            self.assertEqual(user.role, 'salesperson')
            self.assertFalse(user.is_tenant_owner)
    
    def test_role_based_permissions(self):
        """Test role-based permission system."""
        with schema_context(self.tenant.schema_name):
            # Create users with different roles
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
            
            # Test owner permissions
            self.assertTrue(owner.can_access_accounting())
            self.assertTrue(owner.can_access_pos())
            self.assertTrue(owner.can_manage_users())
            self.assertTrue(owner.is_tenant_owner)
            
            # Test accountant permissions
            self.assertTrue(accountant.can_access_accounting())
            self.assertTrue(accountant.can_access_pos())
            self.assertFalse(accountant.can_manage_users())
            self.assertFalse(accountant.is_tenant_owner)
            
            # Test salesperson permissions
            self.assertFalse(salesperson.can_access_accounting())
            self.assertTrue(salesperson.can_access_pos())
            self.assertFalse(salesperson.can_manage_users())
            self.assertFalse(salesperson.is_tenant_owner)
    
    def test_tenant_isolation_in_authentication(self):
        """Test that users from different tenants cannot authenticate in wrong schema."""
        # Create second tenant
        tenant2 = Tenant(
            schema_name='test_jewelry_shop_2',
            name='Test Jewelry Shop 2',
            owner_name='Test Owner 2',
            owner_email='owner2@test.com'
        )
        tenant2.save()
        
        domain2 = Domain(
            domain='test2.localhost',
            tenant=tenant2,
            is_primary=True
        )
        domain2.save()
        
        # Create user in first tenant
        with schema_context(self.tenant.schema_name):
            user1 = User.objects.create_user(
                username='user1',
                password='pass123',
                role='owner'
            )
        
        # Create user in second tenant
        with schema_context(tenant2.schema_name):
            user2 = User.objects.create_user(
                username='user2',
                password='pass123',
                role='owner'
            )
        
        # Test that user1 cannot authenticate in tenant2 schema
        with schema_context(tenant2.schema_name):
            user = authenticate(username='user1', password='pass123')
            self.assertIsNone(user)
        
        # Test that user2 cannot authenticate in tenant1 schema
        with schema_context(self.tenant.schema_name):
            user = authenticate(username='user2', password='pass123')
            self.assertIsNone(user)
        
        # Test that users can authenticate in their own schemas
        with schema_context(self.tenant.schema_name):
            user = authenticate(username='user1', password='pass123')
            self.assertIsNotNone(user)
            self.assertEqual(user.username, 'user1')
        
        with schema_context(tenant2.schema_name):
            user = authenticate(username='user2', password='pass123')
            self.assertIsNotNone(user)
            self.assertEqual(user.username, 'user2')


class JWTAuthenticationTestCase(TenantTestCase):
    """
    Test JWT authentication with tenant awareness.
    """
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        # Create tenant user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@tenant.com',
            password='testpass123',
            role='owner'
        )
    
    def test_jwt_token_generation_with_tenant_context(self):
        """Test JWT token generation includes tenant context."""
        refresh = RefreshToken.for_user(self.user)
        
        # Add tenant-specific claims
        refresh['username'] = self.user.username
        refresh['role'] = self.user.role
        refresh['schema'] = connection.schema_name
        refresh['is_tenant_user'] = True
        refresh['tenant_schema'] = connection.schema_name
        
        # Verify token contains expected claims
        self.assertEqual(refresh['username'], 'testuser')
        self.assertEqual(refresh['role'], 'owner')
        self.assertEqual(refresh['schema'], self.tenant.schema_name)
        self.assertTrue(refresh['is_tenant_user'])
        self.assertEqual(refresh['tenant_schema'], self.tenant.schema_name)
    
    def test_jwt_authentication_class(self):
        """Test custom JWT authentication class."""
        from django.test import RequestFactory
        from zargar.core.authentication import TenantAwareJWTAuthentication
        
        # Create request
        factory = RequestFactory()
        request = factory.get('/api/test/')
        
        # Generate token
        refresh = RefreshToken.for_user(self.user)
        refresh['schema'] = connection.schema_name
        refresh['is_tenant_user'] = True
        access_token = str(refresh.access_token)
        
        # Set authorization header
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
        
        # Test authentication
        auth = TenantAwareJWTAuthentication()
        result = auth.authenticate(request)
        
        self.assertIsNotNone(result)
        authenticated_user, token = result
        self.assertEqual(authenticated_user.id, self.user.id)


class APIAuthenticationTestCase(TenantTestCase):
    """
    Test API authentication endpoints.
    """
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        # Create tenant users
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@tenant.com',
            password='ownerpass123',
            role='owner'
        )
        
        self.accountant = User.objects.create_user(
            username='accountant',
            email='accountant@tenant.com',
            password='accountantpass123',
            role='accountant'
        )
        
        self.salesperson = User.objects.create_user(
            username='salesperson',
            email='sales@tenant.com',
            password='salespass123',
            role='salesperson'
        )
        
        # Set up API client
        from rest_framework.test import APIClient
        self.client = APIClient()
        # Set tenant context for API client
        self.client.defaults['HTTP_HOST'] = self.tenant.get_primary_domain().domain
    
    def test_login_api_endpoint(self):
        """Test login API endpoint."""
        url = '/api/auth/login/'
        
        # Test successful login
        data = {
            'username': 'owner',
            'password': 'ownerpass123'
        }
        response = self.client.post(url, data, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertIn('user', response_data)
        self.assertIn('tokens', response_data)
        self.assertIn('permissions', response_data)
        self.assertEqual(response_data['user']['username'], 'owner')
        self.assertEqual(response_data['user']['role'], 'owner')
        
        # Test failed login
        data = {
            'username': 'owner',
            'password': 'wrongpass'
        }
        response = self.client.post(url, data, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_jwt_token_obtain_endpoint(self):
        """Test JWT token obtain endpoint."""
        url = '/api/auth/token/'
        
        data = {
            'username': 'owner',
            'password': 'ownerpass123'
        }
        response = self.client.post(url, data, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertIn('access', response_data)
        self.assertIn('refresh', response_data)
        self.assertIn('user', response_data)
    
    def test_user_profile_api_endpoint(self):
        """Test user profile API endpoint."""
        # Login first
        self.client.force_authenticate(user=self.owner)
        
        url = '/api/profile/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertEqual(response_data['username'], 'owner')
        self.assertEqual(response_data['role'], 'owner')
    
    def test_user_list_api_permissions(self):
        """Test user list API with different role permissions."""
        url = '/api/users/'
        
        # Test owner access
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test accountant access (should be denied)
        self.client.force_authenticate(user=self.accountant)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Test salesperson access (should be denied)
        self.client.force_authenticate(user=self.salesperson)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_user_creation_api(self):
        """Test user creation API endpoint."""
        url = '/api/users/'
        
        # Test owner can create users
        self.client.force_authenticate(user=self.owner)
        
        data = {
            'username': 'newuser',
            'email': 'newuser@tenant.com',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'role': 'salesperson',
            'first_name': 'New',
            'last_name': 'User'
        }
        response = self.client.post(url, data, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify user was created
        new_user = User.objects.get(username='newuser')
        self.assertEqual(new_user.role, 'salesperson')
        self.assertEqual(new_user.email, 'newuser@tenant.com')
    
    def test_password_change_api(self):
        """Test password change API endpoint."""
        url = '/api/profile/password/'
        
        self.client.force_authenticate(user=self.owner)
        
        data = {
            'old_password': 'ownerpass123',
            'new_password': 'newownerpass123',
            'new_password_confirm': 'newownerpass123'
        }
        response = self.client.post(url, data, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify password was changed
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.check_password('newownerpass123'))
    
    def test_role_update_api(self):
        """Test role update API endpoint."""
        # Test owner can update roles
        self.client.force_authenticate(user=self.owner)
        
        url = f'/api/users/{self.salesperson.id}/role/'
        data = {'role': 'accountant'}
        response = self.client.patch(url, data, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify role was updated
        self.salesperson.refresh_from_db()
        self.assertEqual(self.salesperson.role, 'accountant')
    
    def test_user_permissions_api(self):
        """Test user permissions API endpoint."""
        url = '/api/profile/permissions/'
        
        # Test owner permissions
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertTrue(response_data['can_access_accounting'])
        self.assertTrue(response_data['can_access_pos'])
        self.assertTrue(response_data['can_manage_users'])
        self.assertTrue(response_data['is_tenant_owner'])
        
        # Test accountant permissions
        self.client.force_authenticate(user=self.accountant)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertTrue(response_data['can_access_accounting'])
        self.assertTrue(response_data['can_access_pos'])
        self.assertFalse(response_data['can_manage_users'])
        self.assertFalse(response_data['is_tenant_owner'])


class PermissionClassesTestCase(TenantTestCase):
    """
    Test custom permission classes.
    """
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        # Create users with different roles
        self.owner = User.objects.create_user(
            username='owner',
            password='pass123',
            role='owner'
        )
        
        self.accountant = User.objects.create_user(
            username='accountant',
            password='pass123',
            role='accountant'
        )
        
        self.salesperson = User.objects.create_user(
            username='salesperson',
            password='pass123',
            role='salesperson'
        )
    
    def test_tenant_permission(self):
        """Test TenantPermission class."""
        from django.test import RequestFactory
        
        permission = TenantPermission()
        factory = RequestFactory()
        
        # Test authenticated user
        request = factory.get('/test/')
        request.user = self.owner
        self.assertTrue(permission.has_permission(request, None))
        
        # Test unauthenticated user
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        self.assertFalse(permission.has_permission(request, None))
    
    def test_owner_permission(self):
        """Test OwnerPermission class."""
        from django.test import RequestFactory
        
        permission = OwnerPermission()
        factory = RequestFactory()
        request = factory.get('/test/')
        
        # Test owner
        request.user = self.owner
        self.assertTrue(permission.has_permission(request, None))
        
        # Test non-owner
        request.user = self.accountant
        self.assertFalse(permission.has_permission(request, None))
    
    def test_accounting_permission(self):
        """Test AccountingPermission class."""
        from django.test import RequestFactory
        
        permission = AccountingPermission()
        factory = RequestFactory()
        request = factory.get('/test/')
        
        # Test owner (should have access)
        request.user = self.owner
        self.assertTrue(permission.has_permission(request, None))
        
        # Test accountant (should have access)
        request.user = self.accountant
        self.assertTrue(permission.has_permission(request, None))
        
        # Test salesperson (should not have access)
        request.user = self.salesperson
        self.assertFalse(permission.has_permission(request, None))
    
    def test_pos_permission(self):
        """Test POSPermission class."""
        from django.test import RequestFactory
        
        permission = POSPermission()
        factory = RequestFactory()
        request = factory.get('/test/')
        
        # All roles should have POS access
        for user in [self.owner, self.accountant, self.salesperson]:
            request.user = user
            self.assertTrue(permission.has_permission(request, None))
    
    def test_user_management_permission(self):
        """Test UserManagementPermission class."""
        from django.test import RequestFactory
        
        permission = UserManagementPermission()
        factory = RequestFactory()
        request = factory.get('/test/')
        
        # Test owner (should have access)
        request.user = self.owner
        self.assertTrue(permission.has_permission(request, None))
        
        # Test non-owners (should not have access)
        for user in [self.accountant, self.salesperson]:
            request.user = user
            self.assertFalse(permission.has_permission(request, None))


if __name__ == '__main__':
    pytest.main([__file__])