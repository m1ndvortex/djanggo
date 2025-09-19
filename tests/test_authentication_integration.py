"""
Integration tests for authentication system with existing tenant functionality.
"""
import pytest
from django.test import TestCase
from django.contrib.auth import authenticate
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_public_schema_name, schema_context

from zargar.tenants.models import Tenant, Domain
from zargar.tenants.admin_models import SuperAdmin
from zargar.core.models import User
from zargar.core.authentication import RoleBasedAuthentication, SuperAdminAuthentication


class AuthenticationIntegrationTestCase(TenantTestCase):
    """
    Test authentication system integration with tenant functionality.
    """
    
    def test_user_model_integration(self):
        """Test User model works correctly in tenant schema."""
        # Create users with different roles
        owner = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='pass123',
            role='owner',
            persian_first_name='علی',
            persian_last_name='احمدی'
        )
        
        accountant = User.objects.create_user(
            username='accountant',
            email='accountant@test.com',
            password='pass123',
            role='accountant'
        )
        
        salesperson = User.objects.create_user(
            username='salesperson',
            email='sales@test.com',
            password='pass123',
            role='salesperson'
        )
        
        # Verify users were created correctly
        self.assertEqual(User.objects.count(), 3)
        
        # Test owner permissions
        self.assertTrue(owner.is_tenant_owner)
        self.assertTrue(owner.can_access_accounting())
        self.assertTrue(owner.can_access_pos())
        self.assertTrue(owner.can_manage_users())
        self.assertEqual(owner.full_persian_name, 'علی احمدی')
        
        # Test accountant permissions
        self.assertFalse(accountant.is_tenant_owner)
        self.assertTrue(accountant.can_access_accounting())
        self.assertTrue(accountant.can_access_pos())
        self.assertFalse(accountant.can_manage_users())
        
        # Test salesperson permissions
        self.assertFalse(salesperson.is_tenant_owner)
        self.assertFalse(salesperson.can_access_accounting())
        self.assertTrue(salesperson.can_access_pos())
        self.assertFalse(salesperson.can_manage_users())
    
    def test_authentication_in_tenant_schema(self):
        """Test authentication works correctly in tenant schema."""
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
        self.assertEqual(authenticated_user.role, 'owner')
        
        # Test failed authentication
        authenticated_user = authenticate(username='testuser', password='wrongpass')
        self.assertIsNone(authenticated_user)
        
        # Test non-existent user
        authenticated_user = authenticate(username='nonexistent', password='anypass')
        self.assertIsNone(authenticated_user)
    
    def test_role_based_authentication_utilities(self):
        """Test role-based authentication utility functions."""
        # Create users
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
        
        # Test role permission checking
        self.assertTrue(RoleBasedAuthentication.check_role_permission(owner, 'owner'))
        self.assertTrue(RoleBasedAuthentication.check_role_permission(accountant, 'accountant'))
        self.assertTrue(RoleBasedAuthentication.check_role_permission(salesperson, 'salesperson'))
        
        # Test multiple role checking
        self.assertTrue(RoleBasedAuthentication.check_role_permission(owner, ['owner', 'accountant']))
        self.assertTrue(RoleBasedAuthentication.check_role_permission(accountant, ['owner', 'accountant']))
        self.assertFalse(RoleBasedAuthentication.check_role_permission(salesperson, ['owner', 'accountant']))
        
        # Test specific permission functions
        self.assertTrue(RoleBasedAuthentication.check_owner_permission(owner))
        self.assertFalse(RoleBasedAuthentication.check_owner_permission(accountant))
        
        self.assertTrue(RoleBasedAuthentication.check_accounting_permission(owner))
        self.assertTrue(RoleBasedAuthentication.check_accounting_permission(accountant))
        self.assertFalse(RoleBasedAuthentication.check_accounting_permission(salesperson))
        
        self.assertTrue(RoleBasedAuthentication.check_pos_permission(owner))
        self.assertTrue(RoleBasedAuthentication.check_pos_permission(accountant))
        self.assertTrue(RoleBasedAuthentication.check_pos_permission(salesperson))
        
        self.assertTrue(RoleBasedAuthentication.check_user_management_permission(owner))
        self.assertFalse(RoleBasedAuthentication.check_user_management_permission(accountant))
        self.assertFalse(RoleBasedAuthentication.check_user_management_permission(salesperson))
    
    def test_tenant_aware_model_functionality(self):
        """Test TenantAwareModel functionality with User model."""
        # Create user
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='pass123',
            role='owner'
        )
        
        # Verify audit fields are set
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)
        
        # Test that user is properly isolated in tenant schema
        self.assertEqual(connection.schema_name, self.tenant.schema_name)
        
        # Test user exists only in current tenant
        users_in_tenant = User.objects.all()
        self.assertIn(user, users_in_tenant)
    
    def test_user_manager_functionality(self):
        """Test custom user manager functionality."""
        # Test create_user
        user = User.objects.create_user(
            username='manager_test',
            email='manager@test.com',
            password='pass123',
            role='accountant'
        )
        
        self.assertEqual(user.username, 'manager_test')
        self.assertEqual(user.role, 'accountant')
        self.assertTrue(user.check_password('pass123'))
        
        # Test queryset filtering
        users = User.objects.all()
        self.assertIn(user, users)
        
        # Test get by username
        retrieved_user = User.objects.get(username='manager_test')
        self.assertEqual(retrieved_user.id, user.id)


class SuperAdminIntegrationTestCase(TestCase):
    """
    Test SuperAdmin integration with authentication system.
    """
    
    def test_superadmin_authentication_utilities(self):
        """Test SuperAdmin authentication utility functions."""
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
            self.assertTrue(SuperAdminAuthentication.can_access_tenant(superadmin, 'any_tenant'))
            self.assertTrue(SuperAdminAuthentication.can_create_tenants(superadmin))
            self.assertTrue(SuperAdminAuthentication.can_suspend_tenants(superadmin))
    
    def test_regular_user_is_not_superadmin(self):
        """Test that regular users are not identified as SuperAdmins."""
        # Create tenant and user
        tenant = Tenant(
            schema_name='test_tenant',
            name='Test Tenant',
            owner_name='Test Owner',
            owner_email='owner@test.com'
        )
        tenant.save()
        
        domain = Domain(
            domain='test.localhost',
            tenant=tenant,
            is_primary=True
        )
        domain.save()
        
        with schema_context(tenant.schema_name):
            user = User.objects.create_user(
                username='regular_user',
                email='user@test.com',
                password='pass123',
                role='owner'
            )
            
            # Test that regular user is not SuperAdmin
            self.assertFalse(SuperAdminAuthentication.is_superadmin(user))
            self.assertFalse(SuperAdminAuthentication.can_access_tenant(user, 'any_tenant'))
            self.assertFalse(SuperAdminAuthentication.can_create_tenants(user))
            self.assertFalse(SuperAdminAuthentication.can_suspend_tenants(user))


if __name__ == '__main__':
    pytest.main([__file__])