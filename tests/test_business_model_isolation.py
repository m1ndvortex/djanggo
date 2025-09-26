"""
Test tenant isolation for business models (jewelry, customers).
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from django_tenants.utils import schema_context
from zargar.tenants.models import Tenant, Domain
from zargar.core.models import set_current_tenant, _thread_locals

User = get_user_model()


class BusinessModelIsolationTestCase(TestCase):
    """
    Test that business models are properly isolated between tenants.
    """
    
    def setUp(self):
        """Set up test data."""
        # Create tenants
        self.tenant1 = Tenant.objects.create(
            name="Shop 1",
            schema_name="shop1_test",
            owner_name="Owner 1",
            owner_email="owner1@test.com"
        )
        
        self.tenant2 = Tenant.objects.create(
            name="Shop 2",
            schema_name="shop2_test", 
            owner_name="Owner 2",
            owner_email="owner2@test.com"
        )
        
        # Create domains
        Domain.objects.create(
            domain="shop1test.testserver",
            tenant=self.tenant1,
            is_primary=True
        )
        
        Domain.objects.create(
            domain="shop2test.testserver",
            tenant=self.tenant2,
            is_primary=True
        )
        
        # Create users (shared across tenants)
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@test.com",
            password="testpass123",
            role="owner",
            tenant_schema=self.tenant1.schema_name
        )
        
        self.user2 = User.objects.create_user(
            username="user2", 
            email="user2@test.com",
            password="testpass123",
            role="owner",
            tenant_schema=self.tenant2.schema_name
        )
    
    def test_tenant_aware_model_functionality(self):
        """Test that tenant-aware models work correctly."""
        # Test with tenant 1 context
        set_current_tenant(self.tenant1)
        _thread_locals.user = self.user1
        
        # Import business models
        from zargar.jewelry.models import Category
        from zargar.customers.models import Customer
        
        # Create data in tenant 1 context
        with schema_context(self.tenant1.schema_name):
            category1 = Category.objects.create(
                name="Rings",
                name_persian="انگشتر"
            )
            
            customer1 = Customer.objects.create(
                first_name="John",
                last_name="Doe",
                phone_number="09123456789"
            )
            
            # Verify audit fields are set
            self.assertEqual(category1.created_by, self.user1)
            self.assertEqual(customer1.created_by, self.user1)
            
            # Verify data exists in tenant 1
            self.assertEqual(Category.objects.count(), 1)
            self.assertEqual(Customer.objects.count(), 1)
        
        # Test with tenant 2 context
        set_current_tenant(self.tenant2)
        _thread_locals.user = self.user2
        
        # Create data in tenant 2 context
        with schema_context(self.tenant2.schema_name):
            category2 = Category.objects.create(
                name="Necklaces",
                name_persian="گردنبند"
            )
            
            customer2 = Customer.objects.create(
                first_name="Jane",
                last_name="Smith", 
                phone_number="09987654321"
            )
            
            # Verify audit fields are set
            self.assertEqual(category2.created_by, self.user2)
            self.assertEqual(customer2.created_by, self.user2)
            
            # Verify data exists in tenant 2
            self.assertEqual(Category.objects.count(), 1)
            self.assertEqual(Customer.objects.count(), 1)
        
        # Verify isolation - tenant 1 should only see its data
        with schema_context(self.tenant1.schema_name):
            set_current_tenant(self.tenant1)
            categories = Category.objects.all()
            customers = Customer.objects.all()
            
            self.assertEqual(categories.count(), 1)
            self.assertEqual(categories.first().name, "Rings")
            self.assertEqual(customers.count(), 1)
            self.assertEqual(customers.first().first_name, "John")
        
        # Verify isolation - tenant 2 should only see its data
        with schema_context(self.tenant2.schema_name):
            set_current_tenant(self.tenant2)
            categories = Category.objects.all()
            customers = Customer.objects.all()
            
            self.assertEqual(categories.count(), 1)
            self.assertEqual(categories.first().name, "Necklaces")
            self.assertEqual(customers.count(), 1)
            self.assertEqual(customers.first().first_name, "Jane")
    
    def test_user_tenant_association(self):
        """Test that users are properly associated with tenants."""
        # Users are shared but have tenant_schema field
        self.assertEqual(self.user1.tenant_schema, self.tenant1.schema_name)
        self.assertEqual(self.user2.tenant_schema, self.tenant2.schema_name)
        
        # Both users exist in shared space
        self.assertEqual(User.objects.count(), 2)
        
        # Users can be filtered by tenant_schema
        tenant1_users = User.objects.filter(tenant_schema=self.tenant1.schema_name)
        tenant2_users = User.objects.filter(tenant_schema=self.tenant2.schema_name)
        
        self.assertEqual(tenant1_users.count(), 1)
        self.assertEqual(tenant2_users.count(), 1)
        self.assertEqual(tenant1_users.first(), self.user1)
        self.assertEqual(tenant2_users.first(), self.user2)
    
    def test_superuser_access(self):
        """Test that superusers can access all tenants."""
        superuser = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="adminpass123"
        )
        
        # Superuser should not have tenant_schema restriction
        self.assertIsNone(superuser.tenant_schema)
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_super_admin)
        
        # Superuser should be able to work with any tenant
        set_current_tenant(self.tenant1)
        _thread_locals.user = superuser
        
        from zargar.jewelry.models import Category
        
        with schema_context(self.tenant1.schema_name):
            category = Category.objects.create(
                name="Admin Category",
                name_persian="دسته مدیر"
            )
            
            # Superuser should be set as creator
            self.assertEqual(category.created_by, superuser)
    
    def tearDown(self):
        """Clean up after each test."""
        # Clear thread-local storage
        if hasattr(_thread_locals, 'tenant'):
            delattr(_thread_locals, 'tenant')
        if hasattr(_thread_locals, 'user'):
            delattr(_thread_locals, 'user')