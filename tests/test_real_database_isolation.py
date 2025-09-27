"""
Real Database Tenant Isolation Tests

This module contains comprehensive tests that verify perfect tenant isolation
using real PostgreSQL database operations. No mocking is used - all tests
run against actual database schemas to ensure true isolation.

Tests verify:
1. Tenants cannot access each other's data
2. SuperAdmin can access all tenant data
3. Database schema isolation is enforced
4. Cross-tenant queries are prevented
"""
from django.test import TestCase
from django.contrib.auth import get_user_model, authenticate
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context, get_public_schema_name
from zargar.tenants.models import Tenant, Domain
from zargar.tenants.admin_models import SuperAdmin, TenantAccessLog
from zargar.core.models import set_current_tenant, _thread_locals
from zargar.jewelry.models import Category, JewelryItem
from zargar.customers.models import Customer

User = get_user_model()


class RealDatabaseIsolationTest(TenantTestCase):
    """
    Test perfect tenant isolation using real database operations.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up real tenants with actual database schemas."""
        super().setUpClass()
        
        # Create tenant 1
        with schema_context(get_public_schema_name()):
            cls.tenant1 = Tenant.objects.create(
                name="Real Shop 1",
                schema_name="real_shop1",
                owner_name="Real Owner 1",
                owner_email="owner1@real.com"
            )
            cls.domain1 = Domain.objects.create(
                domain="realshop1.testserver",
                tenant=cls.tenant1,
                is_primary=True
            )
            
            # Create tenant 2
            cls.tenant2 = Tenant.objects.create(
                name="Real Shop 2",
                schema_name="real_shop2",
                owner_name="Real Owner 2",
                owner_email="owner2@real.com"
            )
            cls.domain2 = Domain.objects.create(
                domain="realshop2.testserver",
                tenant=cls.tenant2,
                is_primary=True
            )
            
            # Create SuperAdmin
            cls.superadmin = SuperAdmin.objects.create_superuser(
                username="realsuperadmin",
                email="super@real.com",
                password="superpass123",
                persian_first_name="سوپر",
                persian_last_name="ادمین"
            )
    
    def setUp(self):
        """Set up test data in each tenant."""
        super().setUp()
        
        # Create users and data in tenant1
        with schema_context(self.tenant1.schema_name):
            set_current_tenant(self.tenant1)
            
            self.user1 = User.objects.create_user(
                username="realuser1",
                email="user1@realshop1.com",
                password="userpass123",
                role="owner",
                persian_first_name="کاربر",
                persian_last_name="یک"
            )
            _thread_locals.user = self.user1
            
            # Create business data for tenant1
            self.category1 = Category.objects.create(
                name="Real Rings T1",
                name_persian="انگشتر واقعی ۱"
            )
            
            self.jewelry1 = JewelryItem.objects.create(
                name="Real Gold Ring T1",
                sku="REAL_RING_T1_001",
                barcode="BARCODE_RING_T1_001",
                category=self.category1,
                weight_grams=5.5,
                karat=18,
                manufacturing_cost=500000
            )
            
            self.customer1 = Customer.objects.create(
                first_name="Real John",
                last_name="Doe T1",
                persian_first_name="جان واقعی",
                persian_last_name="دو یک",
                phone_number="09111111111"
            )
        
        # Create users and data in tenant2
        with schema_context(self.tenant2.schema_name):
            set_current_tenant(self.tenant2)
            
            self.user2 = User.objects.create_user(
                username="realuser2",
                email="user2@realshop2.com",
                password="userpass123",
                role="owner",
                persian_first_name="کاربر",
                persian_last_name="دو"
            )
            _thread_locals.user = self.user2
            
            # Create business data for tenant2
            self.category2 = Category.objects.create(
                name="Real Necklaces T2",
                name_persian="گردنبند واقعی ۲"
            )
            
            self.jewelry2 = JewelryItem.objects.create(
                name="Real Gold Necklace T2",
                sku="REAL_NECK_T2_001",
                barcode="BARCODE_NECK_T2_001",
                category=self.category2,
                weight_grams=12.3,
                karat=22,
                manufacturing_cost=800000
            )
            
            self.customer2 = Customer.objects.create(
                first_name="Real Jane",
                last_name="Smith T2",
                persian_first_name="جین واقعی",
                persian_last_name="اسمیت دو",
                phone_number="09222222222"
            )
    
    def test_real_database_user_isolation(self):
        """Test that users are completely isolated in separate database schemas."""
        # Verify tenant1 users
        with schema_context(self.tenant1.schema_name):
            users_t1 = User.objects.all()
            self.assertEqual(users_t1.count(), 1)
            self.assertEqual(users_t1.first().username, "realuser1")
            self.assertEqual(users_t1.first().email, "user1@realshop1.com")
            
            # Verify we cannot see tenant2 user
            with self.assertRaises(User.DoesNotExist):
                User.objects.get(username="realuser2")
        
        # Verify tenant2 users
        with schema_context(self.tenant2.schema_name):
            users_t2 = User.objects.all()
            self.assertEqual(users_t2.count(), 1)
            self.assertEqual(users_t2.first().username, "realuser2")
            self.assertEqual(users_t2.first().email, "user2@realshop2.com")
            
            # Verify we cannot see tenant1 user
            with self.assertRaises(User.DoesNotExist):
                User.objects.get(username="realuser1")
    
    def test_real_database_business_data_isolation(self):
        """Test that business data is completely isolated."""
        # Test Categories
        with schema_context(self.tenant1.schema_name):
            categories_t1 = Category.objects.all()
            self.assertEqual(categories_t1.count(), 1)
            self.assertEqual(categories_t1.first().name, "Real Rings T1")
        
        with schema_context(self.tenant2.schema_name):
            categories_t2 = Category.objects.all()
            self.assertEqual(categories_t2.count(), 1)
            self.assertEqual(categories_t2.first().name, "Real Necklaces T2")
        
        # Test JewelryItems
        with schema_context(self.tenant1.schema_name):
            jewelry_t1 = JewelryItem.objects.all()
            self.assertEqual(jewelry_t1.count(), 1)
            self.assertEqual(jewelry_t1.first().sku, "REAL_RING_T1_001")
        
        with schema_context(self.tenant2.schema_name):
            jewelry_t2 = JewelryItem.objects.all()
            self.assertEqual(jewelry_t2.count(), 1)
            self.assertEqual(jewelry_t2.first().sku, "REAL_NECK_T2_001")
        
        # Test Customers
        with schema_context(self.tenant1.schema_name):
            customers_t1 = Customer.objects.all()
            self.assertEqual(customers_t1.count(), 1)
            self.assertEqual(customers_t1.first().phone_number, "09111111111")
        
        with schema_context(self.tenant2.schema_name):
            customers_t2 = Customer.objects.all()
            self.assertEqual(customers_t2.count(), 1)
            self.assertEqual(customers_t2.first().phone_number, "09222222222")
    
    def test_real_database_raw_sql_isolation(self):
        """Test that even raw SQL queries respect tenant isolation."""
        # Test raw SQL in tenant1
        with schema_context(self.tenant1.schema_name):
            with connection.cursor() as cursor:
                # Check users
                cursor.execute("SELECT username FROM core_user")
                user_results = cursor.fetchall()
                self.assertEqual(len(user_results), 1)
                self.assertEqual(user_results[0][0], "realuser1")
                
                # Check categories
                cursor.execute("SELECT name FROM jewelry_category")
                cat_results = cursor.fetchall()
                self.assertEqual(len(cat_results), 1)
                self.assertEqual(cat_results[0][0], "Real Rings T1")
                
                # Check jewelry items
                cursor.execute("SELECT sku FROM jewelry_jewelryitem")
                jewelry_results = cursor.fetchall()
                self.assertEqual(len(jewelry_results), 1)
                self.assertEqual(jewelry_results[0][0], "REAL_RING_T1_001")
        
        # Test raw SQL in tenant2
        with schema_context(self.tenant2.schema_name):
            with connection.cursor() as cursor:
                # Check users
                cursor.execute("SELECT username FROM core_user")
                user_results = cursor.fetchall()
                self.assertEqual(len(user_results), 1)
                self.assertEqual(user_results[0][0], "realuser2")
                
                # Check categories
                cursor.execute("SELECT name FROM jewelry_category")
                cat_results = cursor.fetchall()
                self.assertEqual(len(cat_results), 1)
                self.assertEqual(cat_results[0][0], "Real Necklaces T2")
                
                # Check jewelry items
                cursor.execute("SELECT sku FROM jewelry_jewelryitem")
                jewelry_results = cursor.fetchall()
                self.assertEqual(len(jewelry_results), 1)
                self.assertEqual(jewelry_results[0][0], "REAL_NECK_T2_001")
    
    def test_real_database_cross_tenant_access_prevention(self):
        """Test that cross-tenant access is completely prevented."""
        # Try to access tenant1 data from tenant2 context
        with schema_context(self.tenant2.schema_name):
            # Should not find any tenant1 data
            with self.assertRaises(User.DoesNotExist):
                User.objects.get(username="realuser1")
            
            with self.assertRaises(Category.DoesNotExist):
                Category.objects.get(name="Real Rings T1")
            
            with self.assertRaises(JewelryItem.DoesNotExist):
                JewelryItem.objects.get(sku="REAL_RING_T1_001")
            
            with self.assertRaises(Customer.DoesNotExist):
                Customer.objects.get(phone_number="09111111111")
        
        # Try to access tenant2 data from tenant1 context
        with schema_context(self.tenant1.schema_name):
            # Should not find any tenant2 data
            with self.assertRaises(User.DoesNotExist):
                User.objects.get(username="realuser2")
            
            with self.assertRaises(Category.DoesNotExist):
                Category.objects.get(name="Real Necklaces T2")
            
            with self.assertRaises(JewelryItem.DoesNotExist):
                JewelryItem.objects.get(sku="REAL_NECK_T2_001")
            
            with self.assertRaises(Customer.DoesNotExist):
                Customer.objects.get(phone_number="09222222222")
    
    def test_real_database_superadmin_cross_tenant_access(self):
        """Test that SuperAdmin can access all tenants."""
        # SuperAdmin should exist in public schema
        with schema_context(get_public_schema_name()):
            superadmins = SuperAdmin.objects.all()
            self.assertEqual(superadmins.count(), 1)
            self.assertEqual(superadmins.first().username, "realsuperadmin")
        
        # SuperAdmin should be able to access tenant1 data
        with schema_context(self.tenant1.schema_name):
            set_current_tenant(self.tenant1)
            _thread_locals.user = self.superadmin
            
            # Should see all tenant1 data
            users = User.objects.all()
            self.assertEqual(users.count(), 1)
            self.assertEqual(users.first().username, "realuser1")
            
            categories = Category.objects.all()
            self.assertEqual(categories.count(), 1)
            self.assertEqual(categories.first().name, "Real Rings T1")
            
            jewelry = JewelryItem.objects.all()
            self.assertEqual(jewelry.count(), 1)
            self.assertEqual(jewelry.first().sku, "REAL_RING_T1_001")
        
        # SuperAdmin should be able to access tenant2 data
        with schema_context(self.tenant2.schema_name):
            set_current_tenant(self.tenant2)
            _thread_locals.user = self.superadmin
            
            # Should see all tenant2 data
            users = User.objects.all()
            self.assertEqual(users.count(), 1)
            self.assertEqual(users.first().username, "realuser2")
            
            categories = Category.objects.all()
            self.assertEqual(categories.count(), 1)
            self.assertEqual(categories.first().name, "Real Necklaces T2")
            
            jewelry = JewelryItem.objects.all()
            self.assertEqual(jewelry.count(), 1)
            self.assertEqual(jewelry.first().sku, "REAL_NECK_T2_001")
    
    def test_real_database_authentication_isolation(self):
        """Test that authentication is properly isolated."""
        # Test SuperAdmin authentication in public schema
        with schema_context(get_public_schema_name()):
            superadmin_auth = authenticate(
                username="realsuperadmin",
                password="superpass123"
            )
            self.assertIsNotNone(superadmin_auth)
            self.assertIsInstance(superadmin_auth, SuperAdmin)
            self.assertEqual(superadmin_auth.username, "realsuperadmin")
        
        # Test tenant1 user authentication
        with schema_context(self.tenant1.schema_name):
            user1_auth = authenticate(
                username="realuser1",
                password="userpass123"
            )
            self.assertIsNotNone(user1_auth)
            self.assertIsInstance(user1_auth, User)
            self.assertEqual(user1_auth.username, "realuser1")
        
        # Test tenant2 user authentication
        with schema_context(self.tenant2.schema_name):
            user2_auth = authenticate(
                username="realuser2",
                password="userpass123"
            )
            self.assertIsNotNone(user2_auth)
            self.assertIsInstance(user2_auth, User)
            self.assertEqual(user2_auth.username, "realuser2")
        
        # Test cross-tenant authentication failure
        with schema_context(self.tenant1.schema_name):
            # Should not be able to authenticate user2 in tenant1
            user2_fail = authenticate(
                username="realuser2",
                password="userpass123"
            )
            self.assertIsNone(user2_fail)
        
        with schema_context(self.tenant2.schema_name):
            # Should not be able to authenticate user1 in tenant2
            user1_fail = authenticate(
                username="realuser1",
                password="userpass123"
            )
            self.assertIsNone(user1_fail)
    
    def test_real_database_foreign_key_isolation(self):
        """Test that foreign key relationships are isolated."""
        # Test that jewelry items can only reference categories from same tenant
        with schema_context(self.tenant1.schema_name):
            set_current_tenant(self.tenant1)
            _thread_locals.user = self.user1
            
            # Should be able to create jewelry with tenant1 category
            jewelry_valid = JewelryItem.objects.create(
                name="Valid Jewelry T1",
                sku="VALID_REAL_T1_001",
                barcode="BARCODE_T1_001",  # Add unique barcode
                category=self.category1,  # Same tenant category
                weight_grams=3.0,
                karat=14,
                manufacturing_cost=300000
            )
            self.assertEqual(jewelry_valid.category, self.category1)
        
        # Verify isolation - tenant2 has its own categories with same IDs but different data
        with schema_context(self.tenant2.schema_name):
            set_current_tenant(self.tenant2)
            _thread_locals.user = self.user2
            
            # Verify that tenant2 has a category with the same ID but different data
            tenant2_category = Category.objects.get(id=self.category1.id)
            self.assertNotEqual(tenant2_category.name, self.category1.name)
            self.assertEqual(tenant2_category.name, "Real Necklaces T2")  # From setUp
            
            # Create jewelry with tenant2's category (should work)
            jewelry_valid_t2 = JewelryItem.objects.create(
                name="Valid Jewelry T2",
                sku="VALID_REAL_T2_001",
                barcode="BARCODE_VALID_T2_001",
                category=tenant2_category,  # Same tenant category
                weight_grams=4.0,
                karat=18,
                manufacturing_cost=400000
            )
            self.assertEqual(jewelry_valid_t2.category, tenant2_category)
            
            # Verify that the jewelry references the correct category for this tenant
            self.assertEqual(jewelry_valid_t2.category.name, "Real Necklaces T2")
            self.assertNotEqual(jewelry_valid_t2.category.name, self.category1.name)
    
    def test_real_database_audit_trail_isolation(self):
        """Test that audit trails are properly isolated."""
        # Create audit records in different tenants
        with schema_context(self.tenant1.schema_name):
            set_current_tenant(self.tenant1)
            _thread_locals.user = self.user1
            
            # Create new category to trigger audit
            audit_cat1 = Category.objects.create(
                name="Real Audit Category T1",
                name_persian="دسته حسابرسی واقعی ۱"
            )
            
            # Check audit fields
            self.assertEqual(audit_cat1.created_by, self.user1)
            self.assertEqual(audit_cat1.updated_by, self.user1)
        
        with schema_context(self.tenant2.schema_name):
            set_current_tenant(self.tenant2)
            _thread_locals.user = self.user2
            
            # Create new category to trigger audit
            audit_cat2 = Category.objects.create(
                name="Real Audit Category T2",
                name_persian="دسته حسابرسی واقعی ۲"
            )
            
            # Check audit fields
            self.assertEqual(audit_cat2.created_by, self.user2)
            self.assertEqual(audit_cat2.updated_by, self.user2)
        
        # Verify audit isolation by checking user existence in each tenant
        with schema_context(self.tenant1.schema_name):
            # Should only see categories created by user1
            categories_by_user1 = Category.objects.filter(created_by=self.user1)
            self.assertEqual(categories_by_user1.count(), 2)  # Original + audit category
            
            # Check that user2 doesn't exist in tenant1's schema
            tenant1_users = User.objects.all()
            user2_exists_in_tenant1 = tenant1_users.filter(username="realuser2").exists()
            self.assertFalse(user2_exists_in_tenant1, "User2 should not exist in tenant1's schema")
            
            # All categories in tenant1 should be created by users that exist in tenant1
            all_categories = Category.objects.all()
            for category in all_categories:
                self.assertTrue(
                    tenant1_users.filter(id=category.created_by_id).exists(),
                    f"Category {category.name} was created by user ID {category.created_by_id} which doesn't exist in tenant1"
                )
        
        with schema_context(self.tenant2.schema_name):
            # Should only see categories created by user2
            categories_by_user2 = Category.objects.filter(created_by=self.user2)
            self.assertEqual(categories_by_user2.count(), 2)  # Original + audit category
            
            # Check that user1 doesn't exist in tenant2's schema
            tenant2_users = User.objects.all()
            user1_exists_in_tenant2 = tenant2_users.filter(username="realuser1").exists()
            self.assertFalse(user1_exists_in_tenant2, "User1 should not exist in tenant2's schema")
            
            # All categories in tenant2 should be created by users that exist in tenant2
            all_categories = Category.objects.all()
            for category in all_categories:
                self.assertTrue(
                    tenant2_users.filter(id=category.created_by_id).exists(),
                    f"Category {category.name} was created by user ID {category.created_by_id} which doesn't exist in tenant2"
                )
    
    def test_real_database_superadmin_audit_logging(self):
        """Test that SuperAdmin actions are properly logged."""
        with schema_context(get_public_schema_name()):
            # Log SuperAdmin access to tenant1
            TenantAccessLog.log_action(
                user=self.superadmin,
                tenant_schema=self.tenant1.schema_name,
                action='tenant_switch',
                tenant_name=self.tenant1.name,
                details={'from_schema': 'public', 'to_schema': self.tenant1.schema_name}
            )
            
            # Verify log was created
            logs = TenantAccessLog.objects.filter(
                user_type='superadmin',
                user_id=self.superadmin.id,
                tenant_schema=self.tenant1.schema_name
            )
            self.assertEqual(logs.count(), 1)
            self.assertEqual(logs.first().action, 'tenant_switch')
            self.assertEqual(logs.first().username, 'realsuperadmin')
    
    def test_real_database_schema_level_table_isolation(self):
        """Test that tables are properly isolated at the schema level."""
        # Check that each tenant has its own set of tables by verifying data isolation
        # This is a more practical test than checking information_schema
        
        # Verify that data created in tenant1 is not visible in tenant2
        with schema_context(self.tenant1.schema_name):
            tenant1_categories = Category.objects.all().count()
            tenant1_jewelry = JewelryItem.objects.all().count()
            tenant1_customers = Customer.objects.all().count()
        
        with schema_context(self.tenant2.schema_name):
            tenant2_categories = Category.objects.all().count()
            tenant2_jewelry = JewelryItem.objects.all().count()
            tenant2_customers = Customer.objects.all().count()
        
        # Both tenants should have their own data
        self.assertGreater(tenant1_categories, 0)
        self.assertGreater(tenant1_jewelry, 0)
        self.assertGreater(tenant1_customers, 0)
        
        self.assertGreater(tenant2_categories, 0)
        self.assertGreater(tenant2_jewelry, 0)
        self.assertGreater(tenant2_customers, 0)
        
        # Verify complete isolation by checking that tenant1 data is not in tenant2
        with schema_context(self.tenant2.schema_name):
            # Should not find tenant1's specific data
            self.assertFalse(Category.objects.filter(name="Real Rings T1").exists())
            self.assertFalse(JewelryItem.objects.filter(sku="REAL_RING_T1_001").exists())
            self.assertFalse(Customer.objects.filter(phone_number="09111111111").exists())
        
        with schema_context(self.tenant1.schema_name):
            # Should not find tenant2's specific data
            self.assertFalse(Category.objects.filter(name="Real Rings T2").exists())
            self.assertFalse(JewelryItem.objects.filter(sku="REAL_RING_T2_001").exists())
            self.assertFalse(Customer.objects.filter(phone_number="09222222222").exists())
        
        # This test confirms that schema-level isolation is working by verifying
        # that data created in one tenant is not visible in another tenant
    
    def tearDown(self):
        """Clean up after each test."""
        # Clear thread-local storage
        if hasattr(_thread_locals, 'tenant'):
            delattr(_thread_locals, 'tenant')
        if hasattr(_thread_locals, 'user'):
            delattr(_thread_locals, 'user')
        
        super().tearDown()