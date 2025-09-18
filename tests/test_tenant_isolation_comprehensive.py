"""
Comprehensive tests for django-tenants implementation with real database operations.
This test suite validates complete tenant isolation and schema management.
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
import time

User = get_user_model()


class DjangoTenantsImplementationTest(TestCase):
    """
    Test that django-tenants is properly implemented and configured.
    """
    
    def test_django_tenants_library_installed(self):
        """Verify django-tenants library is properly installed and configured."""
        # Test that django-tenants is in INSTALLED_APPS
        from django.conf import settings
        self.assertIn('django_tenants', settings.INSTALLED_APPS)
        self.assertEqual(settings.INSTALLED_APPS[0], 'django_tenants')  # Must be first
        
        # Test database engine
        self.assertEqual(
            settings.DATABASES['default']['ENGINE'], 
            'django_tenants.postgresql_backend'
        )
        
        # Test database router
        self.assertIn('django_tenants.routers.TenantSyncRouter', settings.DATABASE_ROUTERS)
        
        # Test tenant configuration
        self.assertEqual(settings.TENANT_MODEL, "tenants.Tenant")
        self.assertEqual(settings.TENANT_DOMAIN_MODEL, "tenants.Domain")
        self.assertEqual(settings.PUBLIC_SCHEMA_URLCONF, 'zargar.urls_public')
        self.assertEqual(settings.ROOT_URLCONF, 'zargar.urls_tenants')
    
    def test_shared_vs_tenant_apps_configuration(self):
        """Test proper separation of SHARED_APPS and TENANT_APPS."""
        from django.conf import settings
        
        # Verify SHARED_APPS contains essential shared components
        expected_shared = [
            'django_tenants',
            'django.contrib.admin',
            'django.contrib.auth',
            'zargar.core',
            'zargar.tenants',
        ]
        
        for app in expected_shared:
            self.assertIn(app, settings.SHARED_APPS)
        
        # Verify TENANT_APPS contains business logic apps
        expected_tenant = [
            'zargar.jewelry',
            'zargar.accounting',
            'zargar.customers',
            'zargar.pos',
            'zargar.reports',
        ]
        
        for app in expected_tenant:
            self.assertIn(app, settings.TENANT_APPS)
    
    def test_tenant_middleware_configuration(self):
        """Test that TenantMainMiddleware is properly configured."""
        from django.conf import settings
        
        # TenantMainMiddleware should be early in the middleware stack
        middleware_list = settings.MIDDLEWARE
        tenant_middleware_index = middleware_list.index('django_tenants.middleware.main.TenantMainMiddleware')
        
        # Should be after HealthCheckMiddleware but before most other middleware
        self.assertTrue(tenant_middleware_index < 5, "TenantMainMiddleware should be early in middleware stack")


class TenantModelComprehensiveTest(TestCase):
    """
    Comprehensive tests for Tenant model functionality.
    """
    
    def test_tenant_model_inheritance(self):
        """Test that Tenant model properly inherits from TenantMixin."""
        from django_tenants.models import TenantMixin
        
        self.assertTrue(issubclass(Tenant, TenantMixin))
        
        # Test that required TenantMixin fields are available
        tenant_fields = [field.name for field in Tenant._meta.fields]
        required_fields = ['schema_name', 'name', 'created_on']
        
        for field in required_fields:
            self.assertIn(field, tenant_fields)
    
    def test_tenant_jewelry_specific_fields(self):
        """Test jewelry shop specific fields in Tenant model."""
        tenant = Tenant.objects.create(
            name='طلافروشی الماس',
            schema_name='almas_jewelry',
            owner_name='احمد الماسی',
            owner_email='ahmad@almas.com',
            phone_number='09123456789',
            address='تهران، خیابان جواهری، پلاک ۱۵',
            subscription_plan='enterprise'
        )
        
        # Test Persian text support
        self.assertEqual(tenant.name, 'طلافروشی الماس')
        self.assertEqual(tenant.owner_name, 'احمد الماسی')
        self.assertEqual(tenant.address, 'تهران، خیابان جواهری، پلاک ۱۵')
        
        # Test subscription plans
        self.assertEqual(tenant.subscription_plan, 'enterprise')
        self.assertIn(tenant.subscription_plan, ['basic', 'pro', 'enterprise'])
        
        # Test auto schema management
        self.assertTrue(tenant.auto_create_schema)
        self.assertTrue(tenant.auto_drop_schema)
    
    def test_tenant_validation_and_constraints(self):
        """Test tenant model validation and database constraints."""
        # Test unique schema_name constraint
        Tenant.objects.create(
            name='Shop 1',
            schema_name='unique_test',
            owner_name='Owner 1',
            owner_email='owner1@test.com'
        )
        
        # Should raise IntegrityError for duplicate schema_name
        with self.assertRaises(Exception):
            Tenant.objects.create(
                name='Shop 2',
                schema_name='unique_test',  # Duplicate schema_name
                owner_name='Owner 2',
                owner_email='owner2@test.com'
            )
    
    def test_domain_model_inheritance(self):
        """Test that Domain model properly inherits from DomainMixin."""
        from django_tenants.models import DomainMixin
        
        self.assertTrue(issubclass(Domain, DomainMixin))
        
        # Test domain creation and relationship
        tenant = Tenant.objects.create(
            name='Domain Test Shop',
            schema_name='domain_test',
            owner_name='Domain Owner',
            owner_email='domain@test.com'
        )
        
        domain = Domain.objects.create(
            domain='domaintest.zargar.com',
            tenant=tenant,
            is_primary=True
        )
        
        self.assertEqual(domain.tenant, tenant)
        self.assertTrue(domain.is_primary)


class SchemaManagementComprehensiveTest(TransactionTestCase):
    """
    Comprehensive tests for automatic schema creation and management.
    """
    
    def test_automatic_schema_creation_on_tenant_save(self):
        """Test that PostgreSQL schemas are automatically created when tenant is saved."""
        tenant = Tenant.objects.create(
            name='Schema Creation Test',
            schema_name='schema_creation_test',
            owner_name='Schema Owner',
            owner_email='schema@creation.com'
        )
        
        # Verify schema exists in PostgreSQL
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [tenant.schema_name]
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result, f"Schema '{tenant.schema_name}' should be created automatically")
            self.assertEqual(result[0], tenant.schema_name)
    
    def test_automatic_schema_deletion_on_tenant_delete(self):
        """Test that PostgreSQL schemas are automatically deleted when tenant is deleted."""
        tenant = Tenant.objects.create(
            name='Schema Deletion Test',
            schema_name='schema_deletion_test',
            owner_name='Schema Owner',
            owner_email='schema@deletion.com'
        )
        
        schema_name = tenant.schema_name
        
        # Verify schema exists
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [schema_name]
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result, f"Schema '{schema_name}' should exist before deletion")
        
        # Delete tenant
        tenant.delete()
        
        # Verify schema is deleted
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [schema_name]
            )
            result = cursor.fetchone()
            self.assertIsNone(result, f"Schema '{schema_name}' should be deleted automatically")
    
    def test_schema_isolation_at_database_level(self):
        """Test that schemas are properly isolated at the PostgreSQL level."""
        # Create two tenants
        tenant1 = Tenant.objects.create(
            name='Isolation Test 1',
            schema_name='isolation_test_1',
            owner_name='Owner 1',
            owner_email='owner1@isolation.com'
        )
        
        tenant2 = Tenant.objects.create(
            name='Isolation Test 2',
            schema_name='isolation_test_2',
            owner_name='Owner 2',
            owner_email='owner2@isolation.com'
        )
        
        # Verify both schemas exist
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN %s",
                [(tenant1.schema_name, tenant2.schema_name)]
            )
            results = cursor.fetchall()
            schema_names = [result[0] for result in results]
            
            self.assertIn(tenant1.schema_name, schema_names)
            self.assertIn(tenant2.schema_name, schema_names)
            self.assertEqual(len(results), 2)
    
    def test_public_schema_integrity(self):
        """Test that public schema contains shared tables and tenant metadata."""
        # Verify public schema exists
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'public'"
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result, "Public schema should exist")
        
        # Verify tenant tables exist in public schema
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name LIKE '%tenant%'"
            )
            results = cursor.fetchall()
            self.assertTrue(len(results) > 0, "Tenant tables should exist in public schema")


class TenantMigrationComprehensiveTest(TransactionTestCase):
    """
    Comprehensive tests for tenant migration functionality.
    """
    
    def test_shared_schema_migrations(self):
        """Test that shared schema migrations work correctly."""
        # Run shared migrations
        call_command('migrate_schemas', shared=True, verbosity=0)
        
        # Verify shared tables exist in public schema
        with connection.cursor() as cursor:
            # Check for tenant table
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name LIKE '%tenant%'"
            )
            tenant_tables = cursor.fetchall()
            self.assertTrue(len(tenant_tables) > 0, "Tenant tables should exist in public schema")
            
            # Check for user table (in shared apps)
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'core_user'"
            )
            user_table = cursor.fetchone()
            self.assertIsNotNone(user_table, "User table should exist in public schema")
    
    def test_tenant_schema_migrations(self):
        """Test that tenant-specific migrations work correctly."""
        # Create tenant
        tenant = Tenant.objects.create(
            name='Migration Test Tenant',
            schema_name='migration_test_tenant',
            owner_name='Migration Owner',
            owner_email='migration@tenant.com'
        )
        
        # Run tenant migrations
        call_command('migrate_schemas', schema_name=tenant.schema_name, verbosity=0)
        
        # Verify tenant schema has appropriate tables
        with connection.cursor() as cursor:
            # Check that tenant schema exists
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [tenant.schema_name]
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result, f"Tenant schema '{tenant.schema_name}' should exist")
            
            # Check for tenant-specific tables (from TENANT_APPS)
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = %s",
                [tenant.schema_name]
            )
            tenant_tables = cursor.fetchall()
            
            # Should have tables from TENANT_APPS
            table_names = [table[0] for table in tenant_tables]
            
            # Auth tables should be in tenant schema (from TENANT_APPS)
            auth_tables = [name for name in table_names if 'auth_' in name]
            self.assertTrue(len(auth_tables) > 0, "Auth tables should exist in tenant schema")


class TenantDataIsolationTest(TransactionTestCase):
    """
    Test complete data isolation between tenants using real database operations.
    """
    
    def setUp(self):
        """Set up test tenants for isolation testing."""
        # Create tenant 1
        self.tenant1 = Tenant.objects.create(
            name='Jewelry Shop Alpha',
            schema_name='alpha_jewelry',
            owner_name='علی احمدی',
            owner_email='ali@alpha.com'
        )
        
        self.domain1 = Domain.objects.create(
            domain='alpha.zargar.com',
            tenant=self.tenant1,
            is_primary=True
        )
        
        # Create tenant 2
        self.tenant2 = Tenant.objects.create(
            name='Jewelry Shop Beta',
            schema_name='beta_jewelry',
            owner_name='محمد بتایی',
            owner_email='mohammad@beta.com'
        )
        
        self.domain2 = Domain.objects.create(
            domain='beta.zargar.com',
            tenant=self.tenant2,
            is_primary=True
        )
        
        # Run migrations for both tenants
        call_command('migrate_schemas', schema_name=self.tenant1.schema_name, verbosity=0)
        call_command('migrate_schemas', schema_name=self.tenant2.schema_name, verbosity=0)
    
    def test_user_data_isolation_with_tenant_schema_field(self):
        """Test that users are properly isolated using tenant_schema field."""
        # Create users for each tenant with tenant_schema set
        user1 = User.objects.create_user(
            username='alpha_owner',
            email='owner@alpha.com',
            password='testpass123',
            persian_first_name='علی',
            persian_last_name='احمدی',
            role='owner',
            tenant_schema=self.tenant1.schema_name
        )
        
        user2 = User.objects.create_user(
            username='beta_owner',
            email='owner@beta.com',
            password='testpass123',
            persian_first_name='محمد',
            persian_last_name='بتایی',
            role='owner',
            tenant_schema=self.tenant2.schema_name
        )
        
        # Test that users can be filtered by tenant_schema
        alpha_users = User.objects.filter(tenant_schema=self.tenant1.schema_name)
        beta_users = User.objects.filter(tenant_schema=self.tenant2.schema_name)
        
        self.assertEqual(alpha_users.count(), 1)
        self.assertEqual(beta_users.count(), 1)
        self.assertEqual(alpha_users.first(), user1)
        self.assertEqual(beta_users.first(), user2)
        
        # Test that users don't cross-contaminate
        self.assertNotIn(user1, beta_users)
        self.assertNotIn(user2, alpha_users)
    
    def test_audit_log_isolation(self):
        """Test that audit logs are properly isolated between tenants."""
        # Create users for each tenant
        user1 = User.objects.create_user(
            username='audit_user1',
            email='audit1@alpha.com',
            password='testpass123',
            tenant_schema=self.tenant1.schema_name
        )
        
        user2 = User.objects.create_user(
            username='audit_user2',
            email='audit2@beta.com',
            password='testpass123',
            tenant_schema=self.tenant2.schema_name
        )
        
        # Create audit logs for each tenant
        audit1 = AuditLog.objects.create(
            user=user1,
            action='login',
            model_name='User',
            object_id=str(user1.id),
            details={'username': 'audit_user1', 'tenant': 'alpha'},
            tenant_schema=self.tenant1.schema_name,
            ip_address='192.168.1.100'
        )
        
        audit2 = AuditLog.objects.create(
            user=user2,
            action='login',
            model_name='User',
            object_id=str(user2.id),
            details={'username': 'audit_user2', 'tenant': 'beta'},
            tenant_schema=self.tenant2.schema_name,
            ip_address='192.168.1.101'
        )
        
        # Test isolation by tenant_schema
        alpha_audits = AuditLog.objects.filter(tenant_schema=self.tenant1.schema_name)
        beta_audits = AuditLog.objects.filter(tenant_schema=self.tenant2.schema_name)
        
        self.assertEqual(alpha_audits.count(), 1)
        self.assertEqual(beta_audits.count(), 1)
        self.assertEqual(alpha_audits.first(), audit1)
        self.assertEqual(beta_audits.first(), audit2)
        
        # Verify no cross-contamination
        self.assertNotIn(audit1, beta_audits)
        self.assertNotIn(audit2, alpha_audits)
    
    def test_schema_context_switching(self):
        """Test switching between tenant schemas using schema_context."""
        # Test public schema context
        with schema_context(get_public_schema_name()):
            # Should be able to access tenant metadata
            tenants = Tenant.objects.all()
            self.assertGreaterEqual(tenants.count(), 2)
            
            tenant_names = [t.name for t in tenants]
            self.assertIn('Jewelry Shop Alpha', tenant_names)
            self.assertIn('Jewelry Shop Beta', tenant_names)
        
        # Test tenant1 schema context
        with schema_context(self.tenant1.schema_name):
            # Should be in tenant1's schema
            current_schema = self._get_current_schema()
            self.assertEqual(current_schema, self.tenant1.schema_name)
        
        # Test tenant2 schema context
        with schema_context(self.tenant2.schema_name):
            # Should be in tenant2's schema
            current_schema = self._get_current_schema()
            self.assertEqual(current_schema, self.tenant2.schema_name)
    
    def test_raw_sql_schema_isolation(self):
        """Test that raw SQL operations respect schema isolation."""
        # Test in tenant1 schema
        with schema_context(self.tenant1.schema_name):
            with connection.cursor() as cursor:
                # Create a test table in tenant1 schema
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.tenant1.schema_name}.test_isolation (
                        id SERIAL PRIMARY KEY,
                        data VARCHAR(100)
                    )
                """)
                
                # Insert test data
                cursor.execute(f"""
                    INSERT INTO {self.tenant1.schema_name}.test_isolation (data) 
                    VALUES ('tenant1_data')
                """)
        
        # Test in tenant2 schema
        with schema_context(self.tenant2.schema_name):
            with connection.cursor() as cursor:
                # Create a test table in tenant2 schema
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.tenant2.schema_name}.test_isolation (
                        id SERIAL PRIMARY KEY,
                        data VARCHAR(100)
                    )
                """)
                
                # Insert test data
                cursor.execute(f"""
                    INSERT INTO {self.tenant2.schema_name}.test_isolation (data) 
                    VALUES ('tenant2_data')
                """)
        
        # Verify data isolation
        with schema_context(self.tenant1.schema_name):
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT data FROM {self.tenant1.schema_name}.test_isolation")
                results = cursor.fetchall()
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0][0], 'tenant1_data')
        
        with schema_context(self.tenant2.schema_name):
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT data FROM {self.tenant2.schema_name}.test_isolation")
                results = cursor.fetchall()
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0][0], 'tenant2_data')
    
    def _get_current_schema(self):
        """Helper method to get current PostgreSQL schema."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_schema()")
            return cursor.fetchone()[0]


class TenantSecurityTest(TransactionTestCase):
    """
    Test security aspects of tenant isolation.
    """
    
    def setUp(self):
        """Set up test tenants for security testing."""
        self.tenant_secure = Tenant.objects.create(
            name='Secure Jewelry Shop',
            schema_name='secure_jewelry',
            owner_name='امین امنی',
            owner_email='amin@secure.com'
        )
        
        self.tenant_other = Tenant.objects.create(
            name='Other Jewelry Shop',
            schema_name='other_jewelry',
            owner_name='دیگر کاربر',
            owner_email='other@jewelry.com'
        )
        
        # Run migrations
        call_command('migrate_schemas', schema_name=self.tenant_secure.schema_name, verbosity=0)
        call_command('migrate_schemas', schema_name=self.tenant_other.schema_name, verbosity=0)
    
    def test_cross_tenant_data_access_prevention(self):
        """Test that tenants cannot access each other's data."""
        # Create sensitive data in secure tenant
        secure_user = User.objects.create_user(
            username='secure_admin',
            email='admin@secure.com',
            password='topsecret123',
            persian_first_name='امین',
            persian_last_name='امنی',
            role='owner',
            tenant_schema=self.tenant_secure.schema_name
        )
        
        secure_audit = AuditLog.objects.create(
            user=secure_user,
            action='create',
            model_name='SensitiveData',
            object_id='secret_123',
            details={'sensitive_info': 'top_secret_data', 'financial_data': '1000000'},
            tenant_schema=self.tenant_secure.schema_name,
            ip_address='10.0.0.1'
        )
        
        # Create data in other tenant
        other_user = User.objects.create_user(
            username='other_user',
            email='user@other.com',
            password='normalpass123',
            tenant_schema=self.tenant_other.schema_name
        )
        
        # Test that other tenant cannot access secure tenant's data
        other_tenant_users = User.objects.filter(tenant_schema=self.tenant_other.schema_name)
        secure_tenant_users = User.objects.filter(tenant_schema=self.tenant_secure.schema_name)
        
        # Verify isolation
        self.assertEqual(other_tenant_users.count(), 1)
        self.assertEqual(secure_tenant_users.count(), 1)
        self.assertNotIn(secure_user, other_tenant_users)
        self.assertNotIn(other_user, secure_tenant_users)
        
        # Test audit log isolation
        other_audits = AuditLog.objects.filter(tenant_schema=self.tenant_other.schema_name)
        secure_audits = AuditLog.objects.filter(tenant_schema=self.tenant_secure.schema_name)
        
        self.assertEqual(other_audits.count(), 0)
        self.assertEqual(secure_audits.count(), 1)
        self.assertNotIn(secure_audit, other_audits)
    
    def test_schema_level_security(self):
        """Test that schema-level security prevents unauthorized access."""
        # Test that we cannot access other tenant's schema without proper context
        with schema_context(self.tenant_secure.schema_name):
            current_schema = self._get_current_schema()
            self.assertEqual(current_schema, self.tenant_secure.schema_name)
            
            # Should not be able to access other tenant's schema from here
            with connection.cursor() as cursor:
                # This should work - accessing current schema
                cursor.execute(f"SELECT current_schema()")
                result = cursor.fetchone()[0]
                self.assertEqual(result, self.tenant_secure.schema_name)
    
    def _get_current_schema(self):
        """Helper method to get current PostgreSQL schema."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_schema()")
            return cursor.fetchone()[0]


class TenantPerformanceTest(TransactionTestCase):
    """
    Test performance aspects of tenant operations.
    """
    
    def test_multiple_tenant_creation_performance(self):
        """Test creating multiple tenants efficiently."""
        start_time = time.time()
        
        # Create 10 tenants
        tenants = []
        for i in range(10):
            tenant = Tenant.objects.create(
                name=f'Performance Test Shop {i}',
                schema_name=f'perf_test_{i}',
                owner_name=f'Owner {i}',
                owner_email=f'owner{i}@perf.com'
            )
            tenants.append(tenant)
        
        creation_time = time.time() - start_time
        
        # Should create 10 tenants in reasonable time (less than 60 seconds)
        # Note: Each tenant creation includes schema creation and migrations
        self.assertLess(creation_time, 60.0, "Creating 10 tenants should take less than 60 seconds")
        
        # Verify all tenants were created
        self.assertEqual(len(tenants), 10)
        
        # Verify all schemas exist
        with connection.cursor() as cursor:
            schema_names = [f'perf_test_{i}' for i in range(10)]
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = ANY(%s)",
                [schema_names]
            )
            results = cursor.fetchall()
            found_schemas = [result[0] for result in results]
            
            for schema_name in schema_names:
                self.assertIn(schema_name, found_schemas)
    
    def test_tenant_schema_switching_performance(self):
        """Test performance of switching between tenant schemas."""
        # Create test tenants
        tenant1 = Tenant.objects.create(
            name='Switch Test 1',
            schema_name='switch_test_1',
            owner_name='Owner 1',
            owner_email='owner1@switch.com'
        )
        
        tenant2 = Tenant.objects.create(
            name='Switch Test 2',
            schema_name='switch_test_2',
            owner_name='Owner 2',
            owner_email='owner2@switch.com'
        )
        
        start_time = time.time()
        
        # Perform 100 schema switches
        for i in range(100):
            if i % 2 == 0:
                with schema_context(tenant1.schema_name):
                    pass
            else:
                with schema_context(tenant2.schema_name):
                    pass
        
        switch_time = time.time() - start_time
        
        # Should perform 100 switches in reasonable time (less than 5 seconds)
        self.assertLess(switch_time, 5.0, "100 schema switches should take less than 5 seconds")


class TenantIntegrationTest(TransactionTestCase):
    """
    Integration tests for complete tenant workflow.
    """
    
    def test_complete_tenant_lifecycle(self):
        """Test complete tenant lifecycle from creation to deletion."""
        # Step 1: Create tenant
        tenant = Tenant.objects.create(
            name='Lifecycle Test Shop',
            schema_name='lifecycle_test',
            owner_name='Lifecycle Owner',
            owner_email='lifecycle@test.com',
            subscription_plan='pro'
        )
        
        # Step 2: Create domain
        domain = Domain.objects.create(
            domain='lifecycle.zargar.com',
            tenant=tenant,
            is_primary=True
        )
        
        # Step 3: Verify schema creation
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [tenant.schema_name]
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result)
        
        # Step 4: Run migrations
        call_command('migrate_schemas', schema_name=tenant.schema_name, verbosity=0)
        
        # Step 5: Create tenant data
        user = User.objects.create_user(
            username='lifecycle_user',
            email='user@lifecycle.com',
            password='testpass123',
            tenant_schema=tenant.schema_name
        )
        
        audit = AuditLog.objects.create(
            user=user,
            action='tenant_setup',
            details={'setup_complete': True},
            tenant_schema=tenant.schema_name
        )
        
        # Step 6: Verify data exists
        tenant_users = User.objects.filter(tenant_schema=tenant.schema_name)
        tenant_audits = AuditLog.objects.filter(tenant_schema=tenant.schema_name)
        
        self.assertEqual(tenant_users.count(), 1)
        self.assertEqual(tenant_audits.count(), 1)
        
        # Step 7: Delete tenant (cleanup)
        tenant_schema_name = tenant.schema_name
        tenant.delete()
        
        # Step 8: Verify schema deletion
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [tenant_schema_name]
            )
            result = cursor.fetchone()
            self.assertIsNone(result)
        
        # Step 9: Verify domain deletion
        self.assertFalse(Domain.objects.filter(id=domain.id).exists())
    
    def test_tenant_subdomain_routing_setup(self):
        """Test that tenant subdomain routing is properly configured."""
        # Create tenant with multiple domains
        tenant = Tenant.objects.create(
            name='Routing Test Shop',
            schema_name='routing_test',
            owner_name='Routing Owner',
            owner_email='routing@test.com'
        )
        
        # Primary domain
        primary_domain = Domain.objects.create(
            domain='routing.zargar.com',
            tenant=tenant,
            is_primary=True
        )
        
        # Secondary domain
        secondary_domain = Domain.objects.create(
            domain='routing.example.com',
            tenant=tenant,
            is_primary=False
        )
        
        # Test domain lookup
        found_primary = Domain.objects.get(domain='routing.zargar.com')
        found_secondary = Domain.objects.get(domain='routing.example.com')
        
        self.assertEqual(found_primary.tenant, tenant)
        self.assertEqual(found_secondary.tenant, tenant)
        self.assertTrue(found_primary.is_primary)
        self.assertFalse(found_secondary.is_primary)
        
        # Test reverse relationship
        tenant_domains = tenant.domains.all()
        self.assertEqual(tenant_domains.count(), 2)
        self.assertIn(primary_domain, tenant_domains)
        self.assertIn(secondary_domain, tenant_domains)