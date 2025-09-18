"""
Tests for tenant isolation and schema management.
"""
import pytest
from django.test import TestCase, TransactionTestCase
from django.db import connection, transaction
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context, tenant_context, get_public_schema_name
from zargar.tenants.models import Tenant, Domain
from zargar.core.models import AuditLog, SystemSettings
import json

User = get_user_model()


class TenantModelTest(TestCase):
    """
    Test Tenant model functionality.
    """
    
    def test_tenant_creation(self):
        """Test creating a new tenant."""
        tenant = Tenant.objects.create(
            name='Test Jewelry Shop',
            schema_name='test_shop',
            owner_name='احمد رضایی',
            owner_email='ahmad@testshop.com',
            phone_number='09123456789',
            address='تهران، خیابان ولیعصر، پلاک ۱۲۳',
            subscription_plan='basic'
        )
        
        self.assertEqual(tenant.name, 'Test Jewelry Shop')
        self.assertEqual(tenant.schema_name, 'test_shop')
        self.assertEqual(tenant.owner_name, 'احمد رضایی')
        self.assertEqual(tenant.owner_email, 'ahmad@testshop.com')
        self.assertEqual(tenant.subscription_plan, 'basic')
        self.assertTrue(tenant.is_active)
        self.assertTrue(tenant.auto_create_schema)
        self.assertTrue(tenant.auto_drop_schema)
    
    def test_tenant_string_representation(self):
        """Test tenant string representation."""
        tenant = Tenant.objects.create(
            name='طلافروشی نور',
            schema_name='noor_jewelry',
            owner_name='علی احمدی',
            owner_email='ali@noorjewelry.com'
        )
        
        self.assertEqual(str(tenant), 'طلافروشی نور')
    
    def test_tenant_subscription_plans(self):
        """Test tenant subscription plan choices."""
        # Test basic plan
        tenant_basic = Tenant.objects.create(
            name='Basic Shop',
            schema_name='basic_shop',
            owner_name='Test Owner',
            owner_email='basic@test.com',
            subscription_plan='basic'
        )
        self.assertEqual(tenant_basic.subscription_plan, 'basic')
        
        # Test pro plan
        tenant_pro = Tenant.objects.create(
            name='Pro Shop',
            schema_name='pro_shop',
            owner_name='Test Owner',
            owner_email='pro@test.com',
            subscription_plan='pro'
        )
        self.assertEqual(tenant_pro.subscription_plan, 'pro')
        
        # Test enterprise plan
        tenant_enterprise = Tenant.objects.create(
            name='Enterprise Shop',
            schema_name='enterprise_shop',
            owner_name='Test Owner',
            owner_email='enterprise@test.com',
            subscription_plan='enterprise'
        )
        self.assertEqual(tenant_enterprise.subscription_plan, 'enterprise')


class DomainModelTest(TestCase):
    """
    Test Domain model functionality.
    """
    
    def test_domain_creation(self):
        """Test creating a domain for a tenant."""
        tenant = Tenant.objects.create(
            name='Test Shop',
            schema_name='test_shop',
            owner_name='Test Owner',
            owner_email='test@shop.com'
        )
        
        domain = Domain.objects.create(
            domain='testshop.zargar.com',
            tenant=tenant,
            is_primary=True
        )
        
        self.assertEqual(domain.domain, 'testshop.zargar.com')
        self.assertEqual(domain.tenant, tenant)
        self.assertTrue(domain.is_primary)
    
    def test_multiple_domains_per_tenant(self):
        """Test that a tenant can have multiple domains."""
        tenant = Tenant.objects.create(
            name='Multi Domain Shop',
            schema_name='multi_shop',
            owner_name='Test Owner',
            owner_email='test@multishop.com'
        )
        
        # Primary domain
        primary_domain = Domain.objects.create(
            domain='multishop.zargar.com',
            tenant=tenant,
            is_primary=True
        )
        
        # Secondary domain
        secondary_domain = Domain.objects.create(
            domain='multishop.example.com',
            tenant=tenant,
            is_primary=False
        )
        
        self.assertEqual(tenant.domains.count(), 2)
        self.assertTrue(primary_domain.is_primary)
        self.assertFalse(secondary_domain.is_primary)


class TenantSchemaManagementTest(TransactionTestCase):
    """
    Test tenant schema creation and management.
    """
    
    def test_schema_creation_and_deletion(self):
        """Test automatic schema creation and deletion."""
        # Create tenant
        tenant = Tenant.objects.create(
            name='Schema Test Shop',
            schema_name='schema_test',
            owner_name='Test Owner',
            owner_email='schema@test.com'
        )
        
        # Create domain
        Domain.objects.create(
            domain='schematest.zargar.com',
            tenant=tenant,
            is_primary=True
        )
        
        # Check that schema exists
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [tenant.schema_name]
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result, "Schema should be created automatically")
        
        # Delete tenant (should also delete schema)
        tenant_schema_name = tenant.schema_name
        tenant.delete()
        
        # Check that schema is deleted
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [tenant_schema_name]
            )
            result = cursor.fetchone()
            self.assertIsNone(result, "Schema should be deleted automatically")
    
    def test_tenant_migrations(self):
        """Test running migrations for tenant schemas."""
        # Create tenant in public schema
        with schema_context(get_public_schema_name()):
            tenant = Tenant.objects.create(
                name='Migration Test Shop',
                schema_name='migration_test_unique',
                owner_name='Test Owner',
                owner_email='migration@test.com'
            )
            
            # Create domain
            Domain.objects.create(
                domain='migrationtestunique.zargar.com',
                tenant=tenant,
                is_primary=True
            )
        
        # Run tenant migrations
        call_command('migrate_schemas', schema_name=tenant.schema_name, verbosity=0)
        
        # Check that tenant-specific tables exist
        with schema_context(tenant.schema_name):
            with connection.cursor() as cursor:
                # Check for user tables (should exist in tenant schema)
                cursor.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_name LIKE '%user%'",
                    [tenant.schema_name]
                )
                result = cursor.fetchone()
                self.assertIsNotNone(result, "User table should exist in tenant schema")


class TenantIsolationTest(TransactionTestCase):
    """
    Test data isolation between tenants.
    """
    
    def setUp(self):
        # Create first tenant in public schema
        with schema_context(get_public_schema_name()):
            self.tenant1 = Tenant.objects.create(
                name='Jewelry Shop 1',
                schema_name='shop1_test',
                owner_name='Owner 1',
                owner_email='owner1@shop1.com'
            )
            
            self.domain1 = Domain.objects.create(
                domain='shop1test.zargar.com',
                tenant=self.tenant1,
                is_primary=True
            )
            
            # Create second tenant
            self.tenant2 = Tenant.objects.create(
                name='Jewelry Shop 2',
                schema_name='shop2_test',
                owner_name='Owner 2',
                owner_email='owner2@shop2.com'
            )
            
            self.domain2 = Domain.objects.create(
                domain='shop2test.zargar.com',
                tenant=self.tenant2,
                is_primary=True
            )
        
        # Run migrations for both tenants
        call_command('migrate_schemas', schema_name=self.tenant1.schema_name, verbosity=0)
        call_command('migrate_schemas', schema_name=self.tenant2.schema_name, verbosity=0)
    
    def test_user_isolation_between_tenants(self):
        """Test that users are isolated between tenants."""
        # Create user in tenant1
        with tenant_context(self.tenant1):
            user1 = User.objects.create_user(
                username='user1',
                email='user1@shop1.com',
                password='testpass123',
                persian_first_name='کاربر',
                persian_last_name='یک',
                role='owner'
            )
            self.assertEqual(User.objects.count(), 1)
        
        # Create user in tenant2
        with tenant_context(self.tenant2):
            user2 = User.objects.create_user(
                username='user2',
                email='user2@shop2.com',
                password='testpass123',
                persian_first_name='کاربر',
                persian_last_name='دو',
                role='owner'
            )
            self.assertEqual(User.objects.count(), 1)  # Should only see tenant2's user
        
        # Verify isolation
        with tenant_context(self.tenant1):
            self.assertEqual(User.objects.count(), 1)
            self.assertTrue(User.objects.filter(username='user1').exists())
            self.assertFalse(User.objects.filter(username='user2').exists())
        
        with tenant_context(self.tenant2):
            self.assertEqual(User.objects.count(), 1)
            self.assertTrue(User.objects.filter(username='user2').exists())
            self.assertFalse(User.objects.filter(username='user1').exists())
    
    def test_audit_log_isolation(self):
        """Test that audit logs are isolated between tenants."""
        # Create audit log in tenant1
        with tenant_context(self.tenant1):
            user1 = User.objects.create_user(
                username='audit_user1',
                email='audit1@shop1.com',
                password='testpass123'
            )
            
            audit1 = AuditLog.objects.create(
                user=user1,
                action='create',
                model_name='User',
                object_id=str(user1.id),
                details={'username': 'audit_user1'},
                tenant_schema=self.tenant1.schema_name
            )
            self.assertEqual(AuditLog.objects.count(), 1)
        
        # Create audit log in tenant2
        with tenant_context(self.tenant2):
            user2 = User.objects.create_user(
                username='audit_user2',
                email='audit2@shop2.com',
                password='testpass123'
            )
            
            audit2 = AuditLog.objects.create(
                user=user2,
                action='create',
                model_name='User',
                object_id=str(user2.id),
                details={'username': 'audit_user2'},
                tenant_schema=self.tenant2.schema_name
            )
            self.assertEqual(AuditLog.objects.count(), 1)  # Should only see tenant2's audit log
        
        # Verify isolation
        with tenant_context(self.tenant1):
            self.assertEqual(AuditLog.objects.count(), 1)
            self.assertTrue(AuditLog.objects.filter(details__username='audit_user1').exists())
            self.assertFalse(AuditLog.objects.filter(details__username='audit_user2').exists())
        
        with tenant_context(self.tenant2):
            self.assertEqual(AuditLog.objects.count(), 1)
            self.assertTrue(AuditLog.objects.filter(details__username='audit_user2').exists())
            self.assertFalse(AuditLog.objects.filter(details__username='audit_user1').exists())
    
    def test_cross_tenant_data_access_prevention(self):
        """Test that cross-tenant data access is prevented."""
        # Create data in tenant1
        with tenant_context(self.tenant1):
            user1 = User.objects.create_user(
                username='cross_test1',
                email='cross1@shop1.com',
                password='testpass123'
            )
            user1_id = user1.id
        
        # Try to access tenant1 data from tenant2 context
        with tenant_context(self.tenant2):
            with self.assertRaises(User.DoesNotExist):
                User.objects.get(id=user1_id)
            
            # Should not be able to see any users from tenant1
            self.assertEqual(User.objects.count(), 0)
    
    def test_tenant_context_switching(self):
        """Test switching between tenant contexts."""
        # Create users in different tenants
        with tenant_context(self.tenant1):
            user1 = User.objects.create_user(
                username='context_user1',
                email='context1@shop1.com',
                password='testpass123'
            )
        
        with tenant_context(self.tenant2):
            user2 = User.objects.create_user(
                username='context_user2',
                email='context2@shop2.com',
                password='testpass123'
            )
        
        # Switch contexts and verify data visibility
        with tenant_context(self.tenant1):
            self.assertEqual(User.objects.count(), 1)
            self.assertEqual(User.objects.first().username, 'context_user1')
        
        with tenant_context(self.tenant2):
            self.assertEqual(User.objects.count(), 1)
            self.assertEqual(User.objects.first().username, 'context_user2')


class TenantClientTest(TransactionTestCase):
    """
    Test tenant-aware HTTP client functionality.
    """
    
    def setUp(self):
        # Create tenant in public schema
        with schema_context(get_public_schema_name()):
            self.tenant = Tenant.objects.create(
                name='Client Test Shop',
                schema_name='client_test_unique',
                owner_name='Client Owner',
                owner_email='client@test.com'
            )
            
            self.domain = Domain.objects.create(
                domain='clienttestunique.zargar.com',
                tenant=self.tenant,
                is_primary=True
            )
        
        # Run migrations
        call_command('migrate_schemas', schema_name=self.tenant.schema_name, verbosity=0)
    
    def test_tenant_client_health_check(self):
        """Test health check with tenant client."""
        # Test basic health check endpoint
        response = self.client.get('/health/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'zargar-jewelry-saas')
    
    def test_tenant_client_context(self):
        """Test that tenant client sets proper context."""
        # Create a user in this tenant
        with tenant_context(self.tenant):
            user = User.objects.create_user(
                username='client_user',
                email='client@test.com',
                password='testpass123'
            )
            self.assertEqual(User.objects.count(), 1)
        
        # Verify tenant exists
        self.assertIsNotNone(self.tenant)
        self.assertEqual(self.tenant.name, 'Client Test Shop')


class SubdomainRoutingTest(TestCase):
    """
    Test subdomain-based tenant routing.
    """
    
    def setUp(self):
        # Create tenant with domain
        self.tenant = Tenant.objects.create(
            name='Routing Test Shop',
            schema_name='routing_test',
            owner_name='Routing Owner',
            owner_email='routing@test.com'
        )
        
        self.domain = Domain.objects.create(
            domain='routingtest.zargar.com',
            tenant=self.tenant,
            is_primary=True
        )
    
    def test_domain_tenant_relationship(self):
        """Test domain to tenant relationship."""
        self.assertEqual(self.domain.tenant, self.tenant)
        self.assertTrue(self.domain.is_primary)
        self.assertEqual(self.tenant.domains.count(), 1)
        self.assertEqual(self.tenant.domains.first(), self.domain)
    
    def test_tenant_domain_lookup(self):
        """Test looking up tenant by domain."""
        found_domain = Domain.objects.get(domain='routingtest.zargar.com')
        self.assertEqual(found_domain.tenant, self.tenant)
    
    def test_multiple_domains_same_tenant(self):
        """Test multiple domains pointing to same tenant."""
        # Add secondary domain
        secondary_domain = Domain.objects.create(
            domain='routingtest.example.com',
            tenant=self.tenant,
            is_primary=False
        )
        
        self.assertEqual(self.tenant.domains.count(), 2)
        
        # Both domains should point to same tenant
        primary = Domain.objects.get(domain='routingtest.zargar.com')
        secondary = Domain.objects.get(domain='routingtest.example.com')
        
        self.assertEqual(primary.tenant, self.tenant)
        self.assertEqual(secondary.tenant, self.tenant)
        self.assertTrue(primary.is_primary)
        self.assertFalse(secondary.is_primary)


class TenantManagementCommandsTest(TransactionTestCase):
    """
    Test tenant management commands.
    """
    
    def test_migrate_schemas_shared(self):
        """Test migrating shared schema."""
        # This should not raise any errors
        call_command('migrate_schemas', shared=True, verbosity=0)
        
        # Check that shared tables exist
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'public.tenant'"
            )
            result = cursor.fetchone()
            # If the above doesn't work, try without the public prefix
            if not result:
                cursor.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name LIKE '%tenant%'"
                )
                result = cursor.fetchone()
            self.assertIsNotNone(result, "Tenant table should exist in public schema")
    
    def test_migrate_schemas_tenant(self):
        """Test migrating specific tenant schema."""
        # Create tenant in public schema
        with schema_context(get_public_schema_name()):
            tenant = Tenant.objects.create(
                name='Command Test Shop',
                schema_name='command_test_unique',
                owner_name='Command Owner',
                owner_email='command@test.com'
            )
            
            # Create domain
            Domain.objects.create(
                domain='commandtestunique.zargar.com',
                tenant=tenant,
                is_primary=True
            )
        
        # Run migrations for this tenant
        call_command('migrate_schemas', schema_name=tenant.schema_name, verbosity=0)
        
        # Check that tenant tables exist
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = %s AND table_name LIKE '%user%'",
                [tenant.schema_name]
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result, "User table should exist in tenant schema")


class TenantSecurityTest(TransactionTestCase):
    """
    Test tenant security and access control.
    """
    
    def setUp(self):
        # Create two tenants for security testing in public schema
        with schema_context(get_public_schema_name()):
            self.tenant_a = Tenant.objects.create(
                name='Security Tenant A',
                schema_name='security_a_test',
                owner_name='Owner A',
                owner_email='a@security.com'
            )
            
            self.domain_a = Domain.objects.create(
                domain='securityatest.zargar.com',
                tenant=self.tenant_a,
                is_primary=True
            )
            
            self.tenant_b = Tenant.objects.create(
                name='Security Tenant B',
                schema_name='security_b_test',
                owner_name='Owner B',
                owner_email='b@security.com'
            )
            
            self.domain_b = Domain.objects.create(
                domain='securitybtest.zargar.com',
                tenant=self.tenant_b,
                is_primary=True
            )
        
        # Run migrations
        call_command('migrate_schemas', schema_name=self.tenant_a.schema_name, verbosity=0)
        call_command('migrate_schemas', schema_name=self.tenant_b.schema_name, verbosity=0)
    
    def test_tenant_data_cannot_be_accessed_across_schemas(self):
        """Test that tenant data cannot be accessed across schemas."""
        # Create sensitive data in tenant A
        with tenant_context(self.tenant_a):
            user_a = User.objects.create_user(
                username='sensitive_user_a',
                email='sensitive@a.com',
                password='secret123',
                persian_first_name='محرمانه',
                persian_last_name='کاربر'
            )
            
            audit_a = AuditLog.objects.create(
                user=user_a,
                action='login',
                details={'sensitive_data': 'top_secret_a'},
                ip_address='192.168.1.100',
                tenant_schema=self.tenant_a.schema_name
            )
        
        # Try to access from tenant B - should not see any data
        with tenant_context(self.tenant_b):
            self.assertEqual(User.objects.count(), 0)
            self.assertEqual(AuditLog.objects.count(), 0)
            
            # Specifically try to access the sensitive user
            self.assertFalse(User.objects.filter(username='sensitive_user_a').exists())
            self.assertFalse(AuditLog.objects.filter(details__sensitive_data='top_secret_a').exists())
    
    def test_schema_level_isolation(self):
        """Test that schema-level isolation is enforced."""
        # Create data in both tenants
        with tenant_context(self.tenant_a):
            User.objects.create_user(username='user_a', email='a@test.com', password='pass123')
        
        with tenant_context(self.tenant_b):
            User.objects.create_user(username='user_b', email='b@test.com', password='pass123')
        
        # Verify each tenant only sees its own data
        with tenant_context(self.tenant_a):
            users = User.objects.all()
            self.assertEqual(users.count(), 1)
            self.assertEqual(users.first().username, 'user_a')
        
        with tenant_context(self.tenant_b):
            users = User.objects.all()
            self.assertEqual(users.count(), 1)
            self.assertEqual(users.first().username, 'user_b')
    
    def test_raw_sql_isolation(self):
        """Test that even raw SQL respects tenant isolation."""
        # Create users in both tenants
        with tenant_context(self.tenant_a):
            user_a = User.objects.create_user(username='raw_a', email='raw_a@test.com', password='pass123')
        
        with tenant_context(self.tenant_b):
            user_b = User.objects.create_user(username='raw_b', email='raw_b@test.com', password='pass123')
        
        # Test raw SQL in tenant A context
        with tenant_context(self.tenant_a):
            with connection.cursor() as cursor:
                cursor.execute("SELECT username FROM core_user WHERE username LIKE 'raw_%'")
                results = cursor.fetchall()
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0][0], 'raw_a')
        
        # Test raw SQL in tenant B context
        with tenant_context(self.tenant_b):
            with connection.cursor() as cursor:
                cursor.execute("SELECT username FROM core_user WHERE username LIKE 'raw_%'")
                results = cursor.fetchall()
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0][0], 'raw_b')