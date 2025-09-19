"""
Basic tests to verify tenant functionality works.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context, get_public_schema_name
from zargar.tenants.models import Tenant, Domain
from zargar.tenants.admin_models import SuperAdmin
from zargar.core.models import set_current_tenant, get_current_tenant, _thread_locals

User = get_user_model()


class BasicTenantFunctionalityTestCase(TestCase):
    """
    Basic tests to ensure tenant functionality works.
    """
    
    def setUp(self):
        """Set up basic test data."""
        # Create a tenant
        self.tenant = Tenant.objects.create(
            name="Basic Test Shop",
            schema_name="basic_test",
            owner_name="Basic Owner",
            owner_email="basic@test.com"
        )
        
        Domain.objects.create(
            domain="basic.testserver",
            tenant=self.tenant,
            is_primary=True
        )
    
    def test_superadmin_creation(self):
        """Test that SuperAdmin can be created in public schema."""
        with schema_context(get_public_schema_name()):
            superadmin = SuperAdmin.objects.create_user(
                username="testsuper",
                email="test@super.com",
                password="superpass123"
            )
            
            self.assertEqual(superadmin.username, "testsuper")
            self.assertTrue(superadmin.can_create_tenants)
            self.assertTrue(superadmin.can_suspend_tenants)
            self.assertTrue(superadmin.can_access_all_data)
    
    def test_tenant_user_creation(self):
        """Test that regular User can be created in tenant schema."""
        with schema_context(self.tenant.schema_name):
            set_current_tenant(self.tenant)
            
            user = User.objects.create_user(
                username="testuser",
                email="test@user.com",
                password="userpass123",
                role="owner"
            )
            
            self.assertEqual(user.username, "testuser")
            self.assertEqual(user.role, "owner")
            self.assertTrue(user.is_tenant_owner)
            self.assertFalse(user.is_super_admin)  # Tenant users are never super admins
    
    def test_tenant_context_functionality(self):
        """Test that tenant context works correctly."""
        # Test setting and getting tenant context
        self.assertIsNone(get_current_tenant())
        
        set_current_tenant(self.tenant)
        current_tenant = get_current_tenant()
        
        self.assertIsNotNone(current_tenant)
        self.assertEqual(current_tenant.schema_name, self.tenant.schema_name)
        self.assertEqual(current_tenant.name, self.tenant.name)
    
    def test_user_role_permissions(self):
        """Test that user role permissions work correctly."""
        with schema_context(self.tenant.schema_name):
            # Test owner permissions
            owner = User.objects.create_user(
                username="owner",
                email="owner@test.com",
                password="pass123",
                role="owner"
            )
            
            self.assertTrue(owner.is_tenant_owner)
            self.assertTrue(owner.can_access_accounting())
            self.assertTrue(owner.can_access_pos())
            self.assertTrue(owner.can_manage_users())
            
            # Test accountant permissions
            accountant = User.objects.create_user(
                username="accountant",
                email="accountant@test.com",
                password="pass123",
                role="accountant"
            )
            
            self.assertFalse(accountant.is_tenant_owner)
            self.assertTrue(accountant.can_access_accounting())
            self.assertTrue(accountant.can_access_pos())
            self.assertFalse(accountant.can_manage_users())
            
            # Test salesperson permissions
            salesperson = User.objects.create_user(
                username="salesperson",
                email="salesperson@test.com",
                password="pass123",
                role="salesperson"
            )
            
            self.assertFalse(salesperson.is_tenant_owner)
            self.assertFalse(salesperson.can_access_accounting())
            self.assertTrue(salesperson.can_access_pos())
            self.assertFalse(salesperson.can_manage_users())
    
    def tearDown(self):
        """Clean up after each test."""
        # Clear thread-local storage
        if hasattr(_thread_locals, 'tenant'):
            delattr(_thread_locals, 'tenant')
        if hasattr(_thread_locals, 'user'):
            delattr(_thread_locals, 'user')