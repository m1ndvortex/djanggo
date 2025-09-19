"""
Core authentication system tests.
"""
import pytest
from django.test import TestCase
from django.contrib.auth import authenticate
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status

from zargar.tenants.models import Tenant, Domain
from zargar.core.models import User
from zargar.core.authentication import RoleBasedAuthentication


class UserModelTestCase(TenantTestCase):
    """
    Test User model functionality.
    """
    
    def test_user_creation_with_roles(self):
        """Test creating users with different roles."""
        # Create owner
        owner = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='pass123',
            role='owner'
        )
        
        self.assertEqual(owner.role, 'owner')
        self.assertTrue(owner.is_tenant_owner)
        self.assertTrue(owner.can_access_accounting())
        self.assertTrue(owner.can_access_pos())
        self.assertTrue(owner.can_manage_users())
        
        # Create accountant
        accountant = User.objects.create_user(
            username='accountant',
            email='accountant@test.com',
            password='pass123',
            role='accountant'
        )
        
        self.assertEqual(accountant.role, 'accountant')
        self.assertFalse(accountant.is_tenant_owner)
        self.assertTrue(accountant.can_access_accounting())
        self.assertTrue(accountant.can_access_pos())
        self.assertFalse(accountant.can_manage_users())
        
        # Create salesperson
        salesperson = User.objects.create_user(
            username='salesperson',
            email='sales@test.com',
            password='pass123',
            role='salesperson'
        )
        
        self.assertEqual(salesperson.role, 'salesperson')
        self.assertFalse(salesperson.is_tenant_owner)
        self.assertFalse(salesperson.can_access_accounting())
        self.assertTrue(salesperson.can_access_pos())
        self.assertFalse(salesperson.can_manage_users())
    
    def test_user_authentication(self):
        """Test user authentication."""
        # Create user
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role='owner'
        )
        
        # Test successful authentication
        authenticated_user = authenticate(username='testuser', password='testpass123')
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user.id, user.id)
        
        # Test failed authentication
        authenticated_user = authenticate(username='testuser', password='wrongpass')
        self.assertIsNone(authenticated_user)
    
    def test_persian_name_handling(self):
        """Test Persian name functionality."""
        user = User.objects.create_user(
            username='persian_user',
            email='persian@test.com',
            password='pass123',
            persian_first_name='علی',
            persian_last_name='احمدی'
        )
        
        self.assertEqual(user.full_persian_name, 'علی احمدی')
        self.assertEqual(str(user), 'علی احمدی')
    
    def test_theme_preference(self):
        """Test theme preference functionality."""
        user = User.objects.create_user(
            username='theme_user',
            email='theme@test.com',
            password='pass123',
            theme_preference='dark'
        )
        
        self.assertEqual(user.theme_preference, 'dark')


class RoleBasedAuthenticationTestCase(TestCase):
    """
    Test role-based authentication utilities.
    """
    
    def setUp(self):
        """Set up test data."""
        # Create a mock user for testing
        class MockUser:
            def __init__(self, role, is_authenticated=True):
                self.role = role
                self.is_authenticated = is_authenticated
                self.is_tenant_owner = (role == 'owner')
            
            def can_access_accounting(self):
                return self.role in ['owner', 'accountant']
            
            def can_access_pos(self):
                return self.role in ['owner', 'accountant', 'salesperson']
            
            def can_manage_users(self):
                return self.role == 'owner'
        
        self.owner = MockUser('owner')
        self.accountant = MockUser('accountant')
        self.salesperson = MockUser('salesperson')
        self.unauthenticated = MockUser('owner', is_authenticated=False)
    
    def test_check_role_permission(self):
        """Test role permission checking."""
        # Test single role
        self.assertTrue(RoleBasedAuthentication.check_role_permission(self.owner, 'owner'))
        self.assertFalse(RoleBasedAuthentication.check_role_permission(self.accountant, 'owner'))
        
        # Test multiple roles
        self.assertTrue(RoleBasedAuthentication.check_role_permission(self.owner, ['owner', 'accountant']))
        self.assertTrue(RoleBasedAuthentication.check_role_permission(self.accountant, ['owner', 'accountant']))
        self.assertFalse(RoleBasedAuthentication.check_role_permission(self.salesperson, ['owner', 'accountant']))
        
        # Test unauthenticated user
        self.assertFalse(RoleBasedAuthentication.check_role_permission(self.unauthenticated, 'owner'))
    
    def test_check_owner_permission(self):
        """Test owner permission checking."""
        self.assertTrue(RoleBasedAuthentication.check_owner_permission(self.owner))
        self.assertFalse(RoleBasedAuthentication.check_owner_permission(self.accountant))
        self.assertFalse(RoleBasedAuthentication.check_owner_permission(self.salesperson))
        self.assertFalse(RoleBasedAuthentication.check_owner_permission(self.unauthenticated))
    
    def test_check_accounting_permission(self):
        """Test accounting permission checking."""
        self.assertTrue(RoleBasedAuthentication.check_accounting_permission(self.owner))
        self.assertTrue(RoleBasedAuthentication.check_accounting_permission(self.accountant))
        self.assertFalse(RoleBasedAuthentication.check_accounting_permission(self.salesperson))
        self.assertFalse(RoleBasedAuthentication.check_accounting_permission(self.unauthenticated))
    
    def test_check_pos_permission(self):
        """Test POS permission checking."""
        self.assertTrue(RoleBasedAuthentication.check_pos_permission(self.owner))
        self.assertTrue(RoleBasedAuthentication.check_pos_permission(self.accountant))
        self.assertTrue(RoleBasedAuthentication.check_pos_permission(self.salesperson))
        self.assertFalse(RoleBasedAuthentication.check_pos_permission(self.unauthenticated))
    
    def test_check_user_management_permission(self):
        """Test user management permission checking."""
        self.assertTrue(RoleBasedAuthentication.check_user_management_permission(self.owner))
        self.assertFalse(RoleBasedAuthentication.check_user_management_permission(self.accountant))
        self.assertFalse(RoleBasedAuthentication.check_user_management_permission(self.salesperson))
        self.assertFalse(RoleBasedAuthentication.check_user_management_permission(self.unauthenticated))


class JWTTokenTestCase(TenantTestCase):
    """
    Test JWT token functionality.
    """
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        self.user = User.objects.create_user(
            username='jwt_user',
            email='jwt@test.com',
            password='pass123',
            role='owner'
        )
    
    def test_jwt_token_generation(self):
        """Test JWT token generation with custom claims."""
        refresh = RefreshToken.for_user(self.user)
        
        # Add custom claims
        refresh['username'] = self.user.username
        refresh['role'] = self.user.role
        refresh['schema'] = connection.schema_name
        refresh['is_tenant_user'] = True
        
        # Verify token contains expected claims
        self.assertEqual(refresh['username'], 'jwt_user')
        self.assertEqual(refresh['role'], 'owner')
        self.assertEqual(refresh['schema'], self.tenant.schema_name)
        self.assertTrue(refresh['is_tenant_user'])
        
        # Verify access token
        access_token = refresh.access_token
        self.assertEqual(access_token['username'], 'jwt_user')
        self.assertEqual(access_token['role'], 'owner')


class APIEndpointsTestCase(TenantTestCase):
    """
    Test API endpoints with proper authentication.
    """
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        self.owner = User.objects.create_user(
            username='api_owner',
            email='owner@api.com',
            password='pass123',
            role='owner'
        )
        
        self.client = APIClient()
    
    def test_login_endpoint(self):
        """Test login API endpoint."""
        url = '/api/auth/login/'
        
        # Test successful login
        data = {
            'username': 'api_owner',
            'password': 'pass123'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertIn('user', response_data)
        self.assertIn('tokens', response_data)
        self.assertEqual(response_data['user']['username'], 'api_owner')
        
        # Test failed login
        data = {
            'username': 'api_owner',
            'password': 'wrongpass'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_jwt_token_endpoint(self):
        """Test JWT token obtain endpoint."""
        url = '/api/auth/token/'
        
        data = {
            'username': 'api_owner',
            'password': 'pass123'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertIn('access', response_data)
        self.assertIn('refresh', response_data)
        self.assertIn('user', response_data)
    
    def test_authenticated_endpoint_access(self):
        """Test accessing authenticated endpoints."""
        # Authenticate user
        self.client.force_authenticate(user=self.owner)
        
        # Test profile endpoint
        url = '/api/profile/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['username'], 'api_owner')
    
    def test_current_user_endpoint(self):
        """Test current user endpoint."""
        self.client.force_authenticate(user=self.owner)
        
        url = '/api/me/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertIn('user', response_data)
        self.assertIn('permissions', response_data)
        self.assertEqual(response_data['user']['username'], 'api_owner')
        self.assertTrue(response_data['permissions']['is_tenant_owner'])


if __name__ == '__main__':
    pytest.main([__file__])