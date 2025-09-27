"""
Tests for core models and middleware.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context
from zargar.tenants.models import Tenant, Domain
from zargar.core.models import (
    get_current_tenant, set_current_tenant, _thread_locals,
    TenantAwareManager, TenantAwareQuerySet
)

User = get_user_model()


class MockTenant:
    """Mock tenant for testing."""
    def __init__(self, schema_name, name="Test Tenant"):
        self.schema_name = schema_name
        self.name = name
        self.id = 1


class TenantAwareModelTestCase(TenantTestCase):
    """Test tenant-aware model functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test tenant."""
        super().setUpClass()
        
        # Create test tenant in public schema
        from django_tenants.utils import get_public_schema_name
        with schema_context(get_public_schema_name()):
            cls.tenant = Tenant.objects.create(
                name="Core Test Shop",
                schema_name="core_test",
                owner_name="Core Owner",
                owner_email="core@test.com"
            )
            
            Domain.objects.create(
                domain="coretest.testserver",
                tenant=cls.tenant,
                is_primary=True
            )
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        # Create user in tenant schema
        with schema_context(self.tenant.schema_name):
            set_current_tenant(self.tenant)
            self.user = User.objects.create_user(
                username="testuser",
                email="test@example.com",
                password="testpass123",
                role="owner"
            )
            _thread_locals.user = self.user
        
        self.mock_tenant = MockTenant("test_schema")
    
    def test_thread_local_tenant_storage(self):
        """Test that tenant context is stored in thread-local storage."""
        # Clear any existing tenant first
        set_current_tenant(None)
        self.assertIsNone(get_current_tenant())
        
        # Set tenant
        set_current_tenant(self.mock_tenant)
        self.assertEqual(get_current_tenant(), self.mock_tenant)
        self.assertEqual(get_current_tenant().schema_name, "test_schema")
        
        # Clear tenant
        set_current_tenant(None)
        self.assertIsNone(get_current_tenant())
    
    def test_thread_local_user_storage(self):
        """Test that user context is stored in thread-local storage."""
        # Set user in thread-local storage
        _thread_locals.user = self.user
        
        # Verify user is accessible
        self.assertEqual(_thread_locals.user, self.user)
        self.assertTrue(_thread_locals.user.is_authenticated)
        
        # Clear user
        if hasattr(_thread_locals, 'user'):
            delattr(_thread_locals, 'user')
        
        # Verify user is cleared
        self.assertFalse(hasattr(_thread_locals, 'user'))
    
    def test_tenant_aware_queryset_initialization(self):
        """Test that TenantAwareQuerySet initializes correctly."""
        # Create a mock model
        class MockModel:
            _meta = type('Meta', (), {'db_table': 'test_table'})()
        
        queryset = TenantAwareQuerySet(model=MockModel)
        self.assertFalse(queryset._tenant_filtered)
        
        # Test cloning maintains state
        clone = queryset._clone()
        self.assertFalse(clone._tenant_filtered)
    
    def test_tenant_aware_manager_initialization(self):
        """Test that TenantAwareManager initializes correctly."""
        manager = TenantAwareManager()
        self.assertIsInstance(manager, TenantAwareManager)
    
    def test_user_role_permissions(self):
        """Test user role-based permissions."""
        with schema_context(self.tenant.schema_name):
            set_current_tenant(self.tenant)
            
            # Test owner permissions
            owner = User.objects.create_user(
                username="owner",
                email="owner@example.com",
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
                email="accountant@example.com",
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
                email="salesperson@example.com",
                password="pass123",
                role="salesperson"
            )
            
            self.assertFalse(salesperson.is_tenant_owner)
            self.assertFalse(salesperson.can_access_accounting())
            self.assertTrue(salesperson.can_access_pos())
            self.assertFalse(salesperson.can_manage_users())
    
    def test_superuser_permissions(self):
        """Test superuser permissions (tenant users are never super admins)."""
        with schema_context(self.tenant.schema_name):
            set_current_tenant(self.tenant)
            
            superuser = User.objects.create_superuser(
                username="admin",
                email="admin@example.com",
                password="adminpass123"
            )
            
            # Tenant users are never super admins (that's handled by SuperAdmin model)
            self.assertFalse(superuser.is_super_admin)
            self.assertTrue(superuser.is_superuser)  # Django superuser flag
            # The create_superuser method still sets super_admin role, but is_super_admin property returns False
            # This is correct behavior - tenant superusers are not true super admins
    
    def tearDown(self):
        """Clean up after each test."""
        # Clear thread-local storage
        if hasattr(_thread_locals, 'tenant'):
            delattr(_thread_locals, 'tenant')
        if hasattr(_thread_locals, 'user'):
            delattr(_thread_locals, 'user')