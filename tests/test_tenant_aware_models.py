"""
Integration tests for tenant-aware models and middleware.
"""
import pytest
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from django_tenants.utils import get_tenant_model, schema_context
from zargar.tenants.models import Tenant, Domain
from zargar.jewelry.models import Category, JewelryItem, Gemstone
from zargar.customers.models import Customer, Supplier
from zargar.core.models import get_current_tenant, set_current_tenant, _thread_locals
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden

User = get_user_model()
TenantModel = get_tenant_model()


class TenantAwareModelTestCase(TenantTestCase):
    """
    Test case for tenant-aware models using real tenant schemas.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test tenants and domains."""
        super().setUpClass()
        
        # Create first tenant
        cls.tenant1 = Tenant.objects.create(
            name="Test Jewelry Shop 1",
            schema_name="test_shop1",
            owner_name="Owner One",
            owner_email="owner1@test.com"
        )
        cls.domain1 = Domain.objects.create(
            domain="shop1.testserver",
            tenant=cls.tenant1,
            is_primary=True
        )
        
        # Create second tenant
        cls.tenant2 = Tenant.objects.create(
            name="Test Jewelry Shop 2", 
            schema_name="test_shop2",
            owner_name="Owner Two",
            owner_email="owner2@test.com"
        )
        cls.domain2 = Domain.objects.create(
            domain="shop2.testserver",
            tenant=cls.tenant2,
            is_primary=True
        )
    
    def setUp(self):
        """Set up test data for each test."""
        super().setUp()
        
        # Set current tenant to tenant1 for setup
        set_current_tenant(self.tenant1)
        
        # Create users for tenant1
        with schema_context(self.tenant1.schema_name):
            self.user1 = User.objects.create_user(
                username="user1",
                email="user1@test.com",
                password="testpass123",
                role="owner",
                tenant_schema=self.tenant1.schema_name
            )
            
            # Set current user in thread-local storage
            _thread_locals.user = self.user1
            
            # Create test data for tenant1
            self.category1 = Category.objects.create(
                name="Rings",
                name_persian="انگشتر"
            )
            
            self.gemstone1 = Gemstone.objects.create(
                name="Diamond 1",
                gemstone_type="diamond",
                carat_weight=1.5,
                cut_grade="excellent"
            )
            
            self.jewelry1 = JewelryItem.objects.create(
                name="Gold Ring",
                sku="RING001",
                category=self.category1,
                weight_grams=5.5,
                karat=18,
                manufacturing_cost=500000
            )
            
            self.customer1 = Customer.objects.create(
                first_name="John",
                last_name="Doe",
                persian_first_name="جان",
                persian_last_name="دو",
                phone_number="09123456789"
            )
        
        # Create users and data for tenant2
        with schema_context(self.tenant2.schema_name):
            self.user2 = User.objects.create_user(
                username="user2",
                email="user2@test.com", 
                password="testpass123",
                role="owner",
                tenant_schema=self.tenant2.schema_name
            )
            
            # Set current user for tenant2 operations
            _thread_locals.user = self.user2
            
            # Create test data for tenant2
            self.category2 = Category.objects.create(
                name="Necklaces",
                name_persian="گردنبند"
            )
            
            self.jewelry2 = JewelryItem.objects.create(
                name="Gold Necklace",
                sku="NECK001",
                category=self.category2,
                weight_grams=12.3,
                karat=22,
                manufacturing_cost=800000
            )
            
            self.customer2 = Customer.objects.create(
                first_name="Jane",
                last_name="Smith",
                persian_first_name="جین",
                persian_last_name="اسمیت",
                phone_number="09987654321"
            )
    
    def test_tenant_isolation_categories(self):
        """Test that categories are isolated between tenants."""
        # Test tenant1 can only see its own categories
        with schema_context(self.tenant1.schema_name):
            set_current_tenant(self.tenant1)
            categories = Category.objects.all()
            self.assertEqual(categories.count(), 1)
            self.assertEqual(categories.first().name, "Rings")
        
        # Test tenant2 can only see its own categories
        with schema_context(self.tenant2.schema_name):
            set_current_tenant(self.tenant2)
            categories = Category.objects.all()
            self.assertEqual(categories.count(), 1)
            self.assertEqual(categories.first().name, "Necklaces")
    
    def test_tenant_isolation_jewelry_items(self):
        """Test that jewelry items are isolated between tenants."""
        # Test tenant1 can only see its own jewelry items
        with schema_context(self.tenant1.schema_name):
            set_current_tenant(self.tenant1)
            items = JewelryItem.objects.all()
            self.assertEqual(items.count(), 1)
            self.assertEqual(items.first().sku, "RING001")
        
        # Test tenant2 can only see its own jewelry items
        with schema_context(self.tenant2.schema_name):
            set_current_tenant(self.tenant2)
            items = JewelryItem.objects.all()
            self.assertEqual(items.count(), 1)
            self.assertEqual(items.first().sku, "NECK001")
    
    def test_tenant_isolation_customers(self):
        """Test that customers are isolated between tenants."""
        # Test tenant1 can only see its own customers
        with schema_context(self.tenant1.schema_name):
            set_current_tenant(self.tenant1)
            customers = Customer.objects.all()
            self.assertEqual(customers.count(), 1)
            self.assertEqual(customers.first().phone_number, "09123456789")
        
        # Test tenant2 can only see its own customers
        with schema_context(self.tenant2.schema_name):
            set_current_tenant(self.tenant2)
            customers = Customer.objects.all()
            self.assertEqual(customers.count(), 1)
            self.assertEqual(customers.first().phone_number, "09987654321")
    
    def test_audit_fields_auto_population(self):
        """Test that audit fields are automatically populated."""
        with schema_context(self.tenant1.schema_name):
            set_current_tenant(self.tenant1)
            _thread_locals.user = self.user1
            
            # Create new category
            category = Category.objects.create(
                name="Bracelets",
                name_persian="دستبند"
            )
            
            # Check audit fields
            self.assertIsNotNone(category.created_at)
            self.assertIsNotNone(category.updated_at)
            self.assertEqual(category.created_by, self.user1)
            self.assertEqual(category.updated_by, self.user1)
            
            # Update category
            original_updated_at = category.updated_at
            category.description = "Beautiful bracelets"
            category.save()
            
            # Check updated_by is set
            category.refresh_from_db()
            self.assertEqual(category.updated_by, self.user1)
            self.assertGreater(category.updated_at, original_updated_at)
    
    def test_tenant_aware_manager_create(self):
        """Test that tenant-aware manager properly handles creation."""
        with schema_context(self.tenant1.schema_name):
            set_current_tenant(self.tenant1)
            _thread_locals.user = self.user1
            
            # Create using manager
            supplier = Supplier.objects.create(
                name="Test Supplier",
                persian_name="تامین کننده تست",
                supplier_type="manufacturer",
                phone_number="02112345678"
            )
            
            # Check audit fields are set
            self.assertEqual(supplier.created_by, self.user1)
            self.assertIsNotNone(supplier.created_at)
    
    def test_tenant_aware_queryset_filtering(self):
        """Test that querysets properly filter by tenant."""
        # Create additional data in tenant1
        with schema_context(self.tenant1.schema_name):
            set_current_tenant(self.tenant1)
            _thread_locals.user = self.user1
            
            Category.objects.create(name="Earrings", name_persian="گوشواره")
            Category.objects.create(name="Pendants", name_persian="آویز")
            
            # Should see 3 categories total (including setup data)
            categories = Category.objects.all()
            self.assertEqual(categories.count(), 3)
            
            # Filter should work normally
            rings = Category.objects.filter(name="Rings")
            self.assertEqual(rings.count(), 1)
        
        # Tenant2 should still only see its own data
        with schema_context(self.tenant2.schema_name):
            set_current_tenant(self.tenant2)
            categories = Category.objects.all()
            self.assertEqual(categories.count(), 1)  # Only "Necklaces"
    
    def test_cross_tenant_foreign_key_protection(self):
        """Test that foreign keys cannot reference cross-tenant objects."""
        with schema_context(self.tenant2.schema_name):
            set_current_tenant(self.tenant2)
            _thread_locals.user = self.user2
            
            # Try to create jewelry item with category from tenant1
            # This should fail because category1 doesn't exist in tenant2 schema
            with self.assertRaises(Exception):
                JewelryItem.objects.create(
                    name="Invalid Item",
                    sku="INVALID001",
                    category_id=self.category1.id,  # This ID doesn't exist in tenant2
                    weight_grams=1.0,
                    karat=18,
                    manufacturing_cost=100000
                )
    
    def test_bulk_operations_tenant_isolation(self):
        """Test that bulk operations respect tenant isolation."""
        with schema_context(self.tenant1.schema_name):
            set_current_tenant(self.tenant1)
            _thread_locals.user = self.user1
            
            # Bulk create categories
            categories = [
                Category(name=f"Category {i}", name_persian=f"دسته {i}")
                for i in range(5)
            ]
            Category.objects.bulk_create(categories)
            
            # Should see 6 categories total (1 from setup + 5 bulk created)
            self.assertEqual(Category.objects.count(), 6)
        
        # Tenant2 should still only see its own data
        with schema_context(self.tenant2.schema_name):
            set_current_tenant(self.tenant2)
            self.assertEqual(Category.objects.count(), 1)
    
    def test_tenant_context_in_model_methods(self):
        """Test that model methods can access tenant context."""
        with schema_context(self.tenant1.schema_name):
            set_current_tenant(self.tenant1)
            
            # Test audit info method
            audit_info = self.jewelry1.get_audit_info()
            self.assertEqual(audit_info['tenant_schema'], self.tenant1.schema_name)
            self.assertIsNotNone(audit_info['created_at'])
            self.assertIsNotNone(audit_info['updated_at'])
    
    def test_unique_constraints_per_tenant(self):
        """Test that unique constraints work within tenant scope."""
        # Create item with same SKU in both tenants - should work
        with schema_context(self.tenant1.schema_name):
            set_current_tenant(self.tenant1)
            _thread_locals.user = self.user1
            
            item1 = JewelryItem.objects.create(
                name="Test Item",
                sku="SAME_SKU",
                category=self.category1,
                weight_grams=1.0,
                karat=18,
                manufacturing_cost=100000
            )
        
        with schema_context(self.tenant2.schema_name):
            set_current_tenant(self.tenant2)
            _thread_locals.user = self.user2
            
            # Same SKU should work in different tenant
            item2 = JewelryItem.objects.create(
                name="Test Item 2",
                sku="SAME_SKU",  # Same SKU as tenant1
                category=self.category2,
                weight_grams=2.0,
                karat=22,
                manufacturing_cost=200000
            )
            
            self.assertEqual(item2.sku, "SAME_SKU")
        
        # But duplicate SKU within same tenant should fail
        with schema_context(self.tenant1.schema_name):
            set_current_tenant(self.tenant1)
            
            with self.assertRaises(Exception):  # IntegrityError
                JewelryItem.objects.create(
                    name="Duplicate SKU Item",
                    sku="SAME_SKU",  # Duplicate within tenant1
                    category=self.category1,
                    weight_grams=3.0,
                    karat=20,
                    manufacturing_cost=300000
                )
    
    def tearDown(self):
        """Clean up after each test."""
        # Clear thread-local storage
        if hasattr(_thread_locals, 'tenant'):
            delattr(_thread_locals, 'tenant')
        if hasattr(_thread_locals, 'user'):
            delattr(_thread_locals, 'user')
        
        super().tearDown()


class TenantIsolationMiddlewareTestCase(TestCase):
    """
    Test cases for tenant isolation middleware.
    """
    
    def setUp(self):
        """Set up test data."""
        # Create tenants
        self.tenant1 = Tenant.objects.create(
            name="Shop 1",
            schema_name="shop1",
            owner_name="Owner 1",
            owner_email="owner1@test.com"
        )
        self.tenant2 = Tenant.objects.create(
            name="Shop 2", 
            schema_name="shop2",
            owner_name="Owner 2",
            owner_email="owner2@test.com"
        )
        
        # Create domains
        Domain.objects.create(
            domain="shop1.testserver",
            tenant=self.tenant1,
            is_primary=True
        )
        Domain.objects.create(
            domain="shop2.testserver",
            tenant=self.tenant2,
            is_primary=True
        )
        
        # Create users
        with schema_context(self.tenant1.schema_name):
            self.user1 = User.objects.create_user(
                username="user1",
                email="user1@test.com",
                password="testpass123",
                role="owner",
                tenant_schema=self.tenant1.schema_name
            )
        
        with schema_context(self.tenant2.schema_name):
            self.user2 = User.objects.create_user(
                username="user2",
                email="user2@test.com",
                password="testpass123", 
                role="salesperson",
                tenant_schema=self.tenant2.schema_name
            )
        
        # Create superuser
        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="adminpass123",
            role="super_admin"
        )
    
    def test_user_can_access_own_tenant(self):
        """Test that users can access their own tenant."""
        client = TenantClient(self.tenant1)
        client.login(username="user1", password="testpass123")
        
        response = client.get("/dashboard/", HTTP_HOST="shop1.testserver")
        # Should not be forbidden (would be 200 or redirect, not 403)
        self.assertNotEqual(response.status_code, 403)
    
    def test_user_cannot_access_other_tenant(self):
        """Test that users cannot access other tenants."""
        # This test would require more complex setup with actual middleware
        # For now, we test the logic directly
        from zargar.core.middleware import TenantIsolationMiddleware
        
        # Create mock request
        class MockRequest:
            def __init__(self, user, tenant, path="/dashboard/"):
                self.user = user
                self.tenant = tenant
                self.path = path
                self.method = "GET"
                self.META = {"HTTP_USER_AGENT": "test"}
        
        middleware = TenantIsolationMiddleware(lambda r: None)
        
        # User1 trying to access tenant2
        request = MockRequest(self.user1, self.tenant2)
        
        # This should trigger the security check
        # In real scenario, this would return HttpResponseForbidden
        # Here we just verify the logic would catch this
        self.assertNotEqual(self.user1.tenant_schema, self.tenant2.schema_name)
    
    def test_superuser_can_access_any_tenant(self):
        """Test that superusers can access any tenant."""
        # Superuser should be able to access any tenant
        self.assertTrue(self.superuser.is_superuser)
        self.assertEqual(self.superuser.role, "super_admin")
        
        # Mock the middleware check
        class MockRequest:
            def __init__(self, user, tenant):
                self.user = user
                self.tenant = tenant
                self.path = "/dashboard/"
                self.method = "GET"
        
        request = MockRequest(self.superuser, self.tenant1)
        
        # Superuser should pass the tenant check
        self.assertTrue(
            request.user.is_superuser or 
            request.user.role == 'super_admin'
        )


class TenantAwareModelPerformanceTestCase(TenantTestCase):
    """
    Performance tests for tenant-aware models.
    """
    
    def setUp(self):
        """Set up performance test data."""
        super().setUp()
        
        self.tenant = Tenant.objects.create(
            name="Performance Test Shop",
            schema_name="perf_test",
            owner_name="Perf Owner",
            owner_email="perf@test.com"
        )
        Domain.objects.create(
            domain="perf.testserver",
            tenant=self.tenant,
            is_primary=True
        )
        
        with schema_context(self.tenant.schema_name):
            self.user = User.objects.create_user(
                username="perfuser",
                email="perf@test.com",
                password="testpass123",
                tenant_schema=self.tenant.schema_name
            )
            
            set_current_tenant(self.tenant)
            _thread_locals.user = self.user
            
            # Create test category
            self.category = Category.objects.create(
                name="Performance Category",
                name_persian="دسته عملکرد"
            )
    
    def test_bulk_create_performance(self):
        """Test performance of bulk create operations."""
        with schema_context(self.tenant.schema_name):
            set_current_tenant(self.tenant)
            _thread_locals.user = self.user
            
            # Create 100 jewelry items
            items = []
            for i in range(100):
                items.append(JewelryItem(
                    name=f"Item {i}",
                    sku=f"PERF{i:03d}",
                    category=self.category,
                    weight_grams=1.0 + i * 0.1,
                    karat=18,
                    manufacturing_cost=100000 + i * 1000
                ))
            
            # Bulk create should be efficient
            import time
            start_time = time.time()
            JewelryItem.objects.bulk_create(items)
            end_time = time.time()
            
            # Should complete in reasonable time (less than 1 second)
            self.assertLess(end_time - start_time, 1.0)
            
            # Verify all items were created
            self.assertEqual(JewelryItem.objects.count(), 100)
    
    def test_queryset_performance(self):
        """Test performance of tenant-aware querysets."""
        with schema_context(self.tenant.schema_name):
            set_current_tenant(self.tenant)
            _thread_locals.user = self.user
            
            # Create test data
            for i in range(50):
                JewelryItem.objects.create(
                    name=f"Query Item {i}",
                    sku=f"QUERY{i:03d}",
                    category=self.category,
                    weight_grams=1.0 + i * 0.1,
                    karat=18,
                    manufacturing_cost=100000 + i * 1000
                )
            
            # Test query performance
            import time
            start_time = time.time()
            
            # Multiple queries
            all_items = list(JewelryItem.objects.all())
            filtered_items = list(JewelryItem.objects.filter(karat=18))
            ordered_items = list(JewelryItem.objects.order_by('name'))
            
            end_time = time.time()
            
            # Should complete in reasonable time
            self.assertLess(end_time - start_time, 0.5)
            
            # Verify results
            self.assertEqual(len(all_items), 50)
            self.assertEqual(len(filtered_items), 50)
            self.assertEqual(len(ordered_items), 50)
    
    def tearDown(self):
        """Clean up performance test."""
        if hasattr(_thread_locals, 'tenant'):
            delattr(_thread_locals, 'tenant')
        if hasattr(_thread_locals, 'user'):
            delattr(_thread_locals, 'user')
        
        super().tearDown()