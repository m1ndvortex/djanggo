"""
Basic tests for django-tenants configuration and functionality.
"""
import pytest
from django.test import TestCase, TransactionTestCase
from django.db import connection
from django.core.management import call_command
from django.contrib.auth import get_user_model
from zargar.tenants.models import Tenant, Domain

User = get_user_model()


class TenantConfigurationTest(TestCase):
    """
    Test basic tenant configuration and models.
    """
    
    def test_tenant_model_creation(self):
        """Test creating a tenant with jewelry shop specific fields."""
        tenant = Tenant.objects.create(
            name='طلافروشی نور',
            schema_name='noor_jewelry',
            owner_name='علی احمدی',
            owner_email='ali@noorjewelry.com',
            phone_number='09123456789',
            address='تهران، خیابان ولیعصر، پلاک ۱۲۳',
            subscription_plan='pro'
        )
        
        self.assertEqual(tenant.name, 'طلافروشی نور')
        self.assertEqual(tenant.schema_name, 'noor_jewelry')
        self.assertEqual(tenant.owner_name, 'علی احمدی')
        self.assertEqual(tenant.owner_email, 'ali@noorjewelry.com')
        self.assertEqual(tenant.phone_number, '09123456789')
        self.assertEqual(tenant.subscription_plan, 'pro')
        self.assertTrue(tenant.is_active)
        self.assertTrue(tenant.auto_create_schema)
        self.assertTrue(tenant.auto_drop_schema)
    
    def test_tenant_string_representation(self):
        """Test tenant string representation."""
        tenant = Tenant.objects.create(
            name='زرگری سپهر',
            schema_name='sepehr_jewelry',
            owner_name='محمد سپهری',
            owner_email='mohammad@sepehrjewelry.com'
        )
        
        self.assertEqual(str(tenant), 'زرگری سپهر')
    
    def test_tenant_subscription_plans(self):
        """Test all subscription plan options."""
        plans = ['basic', 'pro', 'enterprise']
        
        for i, plan in enumerate(plans):
            tenant = Tenant.objects.create(
                name=f'Shop {i+1}',
                schema_name=f'shop_{i+1}',
                owner_name=f'Owner {i+1}',
                owner_email=f'owner{i+1}@shop.com',
                subscription_plan=plan
            )
            self.assertEqual(tenant.subscription_plan, plan)
    
    def test_domain_model_creation(self):
        """Test creating domains for tenants."""
        tenant = Tenant.objects.create(
            name='Test Jewelry Shop',
            schema_name='test_jewelry',
            owner_name='Test Owner',
            owner_email='test@jewelry.com'
        )
        
        # Primary domain
        primary_domain = Domain.objects.create(
            domain='testjewelry.zargar.com',
            tenant=tenant,
            is_primary=True
        )
        
        # Secondary domain
        secondary_domain = Domain.objects.create(
            domain='testjewelry.example.com',
            tenant=tenant,
            is_primary=False
        )
        
        self.assertEqual(primary_domain.tenant, tenant)
        self.assertEqual(secondary_domain.tenant, tenant)
        self.assertTrue(primary_domain.is_primary)
        self.assertFalse(secondary_domain.is_primary)
        self.assertEqual(tenant.domains.count(), 2)
    
    def test_domain_tenant_relationship(self):
        """Test domain to tenant relationship."""
        tenant = Tenant.objects.create(
            name='Relationship Test Shop',
            schema_name='relationship_test',
            owner_name='Test Owner',
            owner_email='test@relationship.com'
        )
        
        domain = Domain.objects.create(
            domain='relationshiptest.zargar.com',
            tenant=tenant,
            is_primary=True
        )
        
        # Test forward relationship
        self.assertEqual(domain.tenant, tenant)
        
        # Test reverse relationship
        self.assertEqual(tenant.domains.first(), domain)
        
        # Test domain lookup
        found_domain = Domain.objects.get(domain='relationshiptest.zargar.com')
        self.assertEqual(found_domain.tenant, tenant)


class TenantSchemaTest(TransactionTestCase):
    """
    Test tenant schema creation and management.
    """
    
    def test_automatic_schema_creation(self):
        """Test that schemas are created automatically."""
        tenant = Tenant.objects.create(
            name='Schema Test Shop',
            schema_name='schema_test_auto',
            owner_name='Schema Owner',
            owner_email='schema@test.com'
        )
        
        Domain.objects.create(
            domain='schematest.zargar.com',
            tenant=tenant,
            is_primary=True
        )
        
        # Check that schema exists in database
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [tenant.schema_name]
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result, f"Schema {tenant.schema_name} should be created automatically")
    
    def test_schema_deletion_on_tenant_delete(self):
        """Test that schemas are deleted when tenant is deleted."""
        tenant = Tenant.objects.create(
            name='Delete Test Shop',
            schema_name='delete_test_auto',
            owner_name='Delete Owner',
            owner_email='delete@test.com'
        )
        
        Domain.objects.create(
            domain='deletetest.zargar.com',
            tenant=tenant,
            is_primary=True
        )
        
        schema_name = tenant.schema_name
        
        # Verify schema exists
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [schema_name]
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result, f"Schema {schema_name} should exist before deletion")
        
        # Delete tenant
        tenant.delete()
        
        # Verify schema is deleted
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [schema_name]
            )
            result = cursor.fetchone()
            self.assertIsNone(result, f"Schema {schema_name} should be deleted automatically")


class TenantMigrationTest(TransactionTestCase):
    """
    Test tenant migration functionality.
    """
    
    def test_shared_schema_migration(self):
        """Test migrating shared schema."""
        # This should not raise any errors
        call_command('migrate_schemas', shared=True, verbosity=0)
        
        # Check that tenant table exists in public schema
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name LIKE '%tenant%'"
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result, "Tenant-related tables should exist in public schema")
    
    def test_tenant_schema_migration(self):
        """Test migrating a specific tenant schema."""
        # Create tenant
        tenant = Tenant.objects.create(
            name='Migration Test Shop',
            schema_name='migration_test_specific',
            owner_name='Migration Owner',
            owner_email='migration@test.com'
        )
        
        Domain.objects.create(
            domain='migrationtest.zargar.com',
            tenant=tenant,
            is_primary=True
        )
        
        # Run migrations for this tenant
        call_command('migrate_schemas', schema_name=tenant.schema_name, verbosity=0)
        
        # Check that tenant schema was created and migrations ran successfully
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [tenant.schema_name]
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result, f"Tenant schema {tenant.schema_name} should exist after migration")


class UserModelTest(TestCase):
    """
    Test custom User model functionality.
    """
    
    def test_user_creation_with_persian_fields(self):
        """Test creating users with Persian-specific fields."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            persian_first_name='علی',
            persian_last_name='احمدی',
            phone_number='09123456789',
            role='owner',
            tenant_schema='test_tenant'
        )
        
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.persian_first_name, 'علی')
        self.assertEqual(user.persian_last_name, 'احمدی')
        self.assertEqual(user.phone_number, '09123456789')
        self.assertEqual(user.role, 'owner')
        self.assertEqual(user.tenant_schema, 'test_tenant')
        self.assertFalse(user.is_2fa_enabled)
        self.assertEqual(user.theme_preference, 'light')
    
    def test_user_full_persian_name(self):
        """Test full Persian name property."""
        user = User.objects.create_user(
            username='persian_user',
            email='persian@test.com',
            password='testpass123',
            persian_first_name='محمد',
            persian_last_name='رضایی'
        )
        
        self.assertEqual(user.full_persian_name, 'محمد رضایی')
    
    def test_user_role_permissions(self):
        """Test user role-based permission methods."""
        # Test owner
        owner = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123',
            role='owner'
        )
        
        self.assertTrue(owner.is_tenant_owner)
        self.assertTrue(owner.can_access_accounting())
        self.assertTrue(owner.can_access_pos())
        self.assertTrue(owner.can_manage_users())
        
        # Test accountant
        accountant = User.objects.create_user(
            username='accountant',
            email='accountant@test.com',
            password='testpass123',
            role='accountant'
        )
        
        self.assertFalse(accountant.is_tenant_owner)
        self.assertTrue(accountant.can_access_accounting())
        self.assertTrue(accountant.can_access_pos())
        self.assertFalse(accountant.can_manage_users())
        
        # Test salesperson
        salesperson = User.objects.create_user(
            username='salesperson',
            email='salesperson@test.com',
            password='testpass123',
            role='salesperson'
        )
        
        self.assertFalse(salesperson.is_tenant_owner)
        self.assertFalse(salesperson.can_access_accounting())
        self.assertTrue(salesperson.can_access_pos())
        self.assertFalse(salesperson.can_manage_users())
    
    def test_user_theme_preferences(self):
        """Test user theme preference options."""
        # Test light theme
        light_user = User.objects.create_user(
            username='light_user',
            email='light@test.com',
            password='testpass123',
            theme_preference='light'
        )
        self.assertEqual(light_user.theme_preference, 'light')
        
        # Test dark theme
        dark_user = User.objects.create_user(
            username='dark_user',
            email='dark@test.com',
            password='testpass123',
            theme_preference='dark'
        )
        self.assertEqual(dark_user.theme_preference, 'dark')
    
    def test_superuser_properties(self):
        """Test superuser properties."""
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass123',
            role='super_admin'
        )
        
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_super_admin)


class TenantAwareModelTest(TestCase):
    """
    Test TenantAwareModel abstract base class.
    """
    
    def test_tenant_aware_model_fields(self):
        """Test that TenantAwareModel has required audit fields."""
        from zargar.core.models import TenantAwareModel
        
        # Check that the abstract model has the expected fields
        field_names = [field.name for field in TenantAwareModel._meta.fields]
        
        self.assertIn('created_at', field_names)
        self.assertIn('updated_at', field_names)
        self.assertIn('created_by', field_names)


class SystemSettingsTest(TestCase):
    """
    Test SystemSettings model.
    """
    
    def test_system_settings_creation(self):
        """Test creating system settings."""
        from zargar.core.models import SystemSettings
        
        setting = SystemSettings.objects.create(
            key='gold_price_api_url',
            value='https://api.example.com/gold-price',
            description='URL for fetching current gold prices',
            is_active=True
        )
        
        self.assertEqual(setting.key, 'gold_price_api_url')
        self.assertEqual(setting.value, 'https://api.example.com/gold-price')
        self.assertTrue(setting.is_active)
        self.assertIn('gold_price_api_url', str(setting))


class AuditLogTest(TestCase):
    """
    Test AuditLog model.
    """
    
    def test_audit_log_creation(self):
        """Test creating audit log entries."""
        from zargar.core.models import AuditLog
        
        user = User.objects.create_user(
            username='audit_user',
            email='audit@test.com',
            password='testpass123'
        )
        
        audit_log = AuditLog.objects.create(
            user=user,
            action='create',
            model_name='User',
            object_id=str(user.id),
            details={'username': 'audit_user'},
            ip_address='192.168.1.100',
            user_agent='Test Browser',
            tenant_schema='test_tenant'
        )
        
        self.assertEqual(audit_log.user, user)
        self.assertEqual(audit_log.action, 'create')
        self.assertEqual(audit_log.model_name, 'User')
        self.assertEqual(audit_log.details['username'], 'audit_user')
        self.assertEqual(audit_log.ip_address, '192.168.1.100')
        self.assertEqual(audit_log.tenant_schema, 'test_tenant')
        self.assertIn('audit_user', str(audit_log))