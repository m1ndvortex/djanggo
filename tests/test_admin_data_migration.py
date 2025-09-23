"""
Comprehensive tests for admin data migration and system integrity.
"""
import pytest
import json
import tempfile
import os
import django
from django.test import TestCase, TransactionTestCase
from django.core.management import call_command
from django.utils import timezone
from django.db import connection
from io import StringIO
from unittest.mock import patch, MagicMock

# Configure Django settings for tests
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django.contrib.sessions.models import Session

from zargar.tenants.admin_models import (
    SuperAdmin, SuperAdminSession, TenantAccessLog, 
    SubscriptionPlan, TenantInvoice, BillingCycle
)
from zargar.tenants.models import Tenant, Domain


class AdminDataMigrationTestCase(TransactionTestCase):
    """Test admin data migration functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create test SuperAdmin
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='test@example.com',
            password='testpass123',
            persian_first_name='تست',
            persian_last_name='ادمین',
            phone_number='09123456789',
            is_staff=True,
            is_superuser=True
        )
        
        # Create test tenant
        self.tenant = Tenant.objects.create(
            schema_name='test_tenant',
            name='Test Jewelry Shop',
            owner_name='Test Owner',
            owner_email='owner@test.com',
            phone_number='09123456789',
            subscription_plan='basic'
        )
        
        # Create domain for tenant
        Domain.objects.create(
            domain='test.localhost',
            tenant=self.tenant,
            is_primary=True
        )
        
        # Create test session
        self.session = SuperAdminSession.objects.create(
            super_admin=self.superadmin,
            tenant_schema='test_tenant',
            session_key='test_session_key',
            ip_address='127.0.0.1',
            user_agent='Test User Agent',
            is_active=True
        )
        
        # Create test audit log
        self.audit_log = TenantAccessLog.objects.create(
            user_type='superadmin',
            user_id=self.superadmin.id,
            username=self.superadmin.username,
            tenant_schema='test_tenant',
            tenant_name=self.tenant.name,
            action='login',
            ip_address='127.0.0.1',
            user_agent='Test User Agent',
            request_path='/admin/dashboard/',
            request_method='GET',
            success=True
        )
    
    def test_migrate_admin_data_dry_run(self):
        """Test migration command in dry run mode."""
        # Clear theme preference to test migration
        original_theme = self.superadmin.theme_preference
        self.superadmin.theme_preference = ''
        self.superadmin.save()
        
        out = StringIO()
        call_command('migrate_admin_data', '--dry-run', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Dry run completed', output)
        self.assertIn('Would migrate: testadmin', output)
        
        # Verify no actual changes were made
        admin = SuperAdmin.objects.get(username='testadmin')
        self.assertEqual(admin.theme_preference, '')  # Should be unchanged
        
        # Restore original theme
        self.superadmin.theme_preference = original_theme
        self.superadmin.save()
    
    def test_migrate_superadmin_data(self):
        """Test SuperAdmin data migration."""
        # Clear theme preference to test migration
        self.superadmin.theme_preference = ''
        self.superadmin.can_create_tenants = False  # Use False instead of None
        self.superadmin.save()
        
        out = StringIO()
        call_command('migrate_admin_data', stdout=out)
        
        # Verify migration
        admin = SuperAdmin.objects.get(username='testadmin')
        self.assertEqual(admin.theme_preference, 'light')
        self.assertTrue(admin.can_create_tenants)  # Should be set to True by migration
        self.assertTrue(admin.can_suspend_tenants)
        self.assertTrue(admin.can_access_all_data)
        
        output = out.getvalue()
        self.assertIn('Updated: testadmin', output)
    
    def test_migrate_session_data(self):
        """Test session data migration."""
        # Create expired session
        expired_session = SuperAdminSession.objects.create(
            super_admin=self.superadmin,
            tenant_schema='test_tenant',
            session_key='expired_session',
            access_time=timezone.now() - timezone.timedelta(days=2),
            is_active=True
        )
        
        out = StringIO()
        call_command('migrate_admin_data', stdout=out)
        
        # Verify expired session was deactivated
        expired_session.refresh_from_db()
        self.assertFalse(expired_session.is_active)
        
        # Verify active session remains active
        self.session.refresh_from_db()
        self.assertTrue(self.session.is_active)
        
        output = out.getvalue()
        self.assertIn('Deactivated old session', output)
    
    def test_migrate_audit_logs(self):
        """Test audit log migration."""
        # Create audit log without tenant name
        incomplete_log = TenantAccessLog.objects.create(
            user_type='superadmin',
            user_id=self.superadmin.id,
            username=self.superadmin.username,
            tenant_schema='test_tenant',
            tenant_name='',  # Missing tenant name
            action='view',
            success=True
        )
        
        out = StringIO()
        call_command('migrate_admin_data', stdout=out)
        
        # Verify tenant name was added
        incomplete_log.refresh_from_db()
        self.assertEqual(incomplete_log.tenant_name, self.tenant.name)
        
        output = out.getvalue()
        self.assertIn('Updated 1 audit log records', output)
    
    def test_migrate_system_settings(self):
        """Test system settings migration."""
        # Remove subscription plan from tenant
        self.tenant.subscription_plan_fk = None
        self.tenant.save()
        
        out = StringIO()
        call_command('migrate_admin_data', stdout=out)
        
        # Verify default subscription plan was created and assigned
        self.tenant.refresh_from_db()
        self.assertIsNotNone(self.tenant.subscription_plan_fk)
        self.assertEqual(self.tenant.subscription_plan_fk.plan_type, 'basic')
        
        # Verify default plan exists
        default_plan = SubscriptionPlan.objects.get(plan_type='basic')
        self.assertEqual(default_plan.name, 'Basic Plan')
        self.assertEqual(default_plan.name_persian, 'پلن پایه')
        
        output = out.getvalue()
        self.assertIn('Created default subscription plan', output)
    
    def test_backup_data_creation(self):
        """Test data backup functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('zargar.tenants.management.commands.migrate_admin_data.settings') as mock_settings:
                mock_settings.BASE_DIR = temp_dir
                
                out = StringIO()
                call_command('migrate_admin_data', '--backup-data', stdout=out)
                
                output = out.getvalue()
                self.assertIn('Backup created:', output)
                
                # Verify backup file was created
                import os
                backup_files = [f for f in os.listdir(f'{temp_dir}/backups') if f.startswith('admin_data_backup_')]
                self.assertEqual(len(backup_files), 1)
                
                # Verify backup content
                with open(f'{temp_dir}/backups/{backup_files[0]}', 'r') as f:
                    backup_data = json.load(f)
                
                self.assertIn('superadmins', backup_data)
                self.assertIn('sessions', backup_data)
                self.assertIn('audit_logs', backup_data)
                self.assertIn('tenants', backup_data)
                
                # Verify SuperAdmin data in backup
                self.assertEqual(len(backup_data['superadmins']), 1)
                admin_backup = backup_data['superadmins'][0]
                self.assertEqual(admin_backup['username'], 'testadmin')
                self.assertEqual(admin_backup['persian_first_name'], 'تست')
    
    def test_data_integrity_verification(self):
        """Test data integrity verification."""
        out = StringIO()
        call_command('migrate_admin_data', '--verify-only', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Data integrity verification passed', output)
        self.assertNotIn('data integrity issues', output)
    
    def test_data_integrity_with_issues(self):
        """Test data integrity verification with issues."""
        # Create SuperAdmin with missing email
        bad_admin = SuperAdmin.objects.create_user(
            username='baduser',
            email='',  # Missing email
            password='testpass123'
        )
        
        out = StringIO()
        call_command('migrate_admin_data', '--verify-only', stdout=out)
        
        output = out.getvalue()
        self.assertIn('data integrity issues', output)
        self.assertIn('missing email', output)
        
        # Clean up
        bad_admin.delete()
    
    def test_system_performance_validation(self):
        """Test system performance validation."""
        out = StringIO()
        call_command('migrate_admin_data', '--verify-only', stdout=out)
        
        output = out.getvalue()
        self.assertIn('System performance validation completed', output)
        self.assertIn('SuperAdmin query time:', output)
        self.assertIn('Tenant query time:', output)
        self.assertIn('Audit log query time:', output)
    
    def test_clean_obsolete_data(self):
        """Test obsolete data cleanup."""
        # Create a test obsolete table
        with connection.cursor() as cursor:
            cursor.execute('CREATE TABLE IF NOT EXISTS test_old_table (id SERIAL PRIMARY KEY)')
        
        out = StringIO()
        call_command('migrate_admin_data', '--clean-obsolete', '--dry-run', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Cleaning up obsolete data', output)
        
        # Clean up test table
        with connection.cursor() as cursor:
            cursor.execute('DROP TABLE IF EXISTS test_old_table')
    
    def test_full_migration_workflow(self):
        """Test complete migration workflow."""
        # Prepare data that needs migration
        self.superadmin.theme_preference = ''
        self.superadmin.can_create_tenants = None
        self.superadmin.save()
        
        self.tenant.subscription_plan_fk = None
        self.tenant.save()
        
        # Create expired session
        SuperAdminSession.objects.create(
            super_admin=self.superadmin,
            tenant_schema='test_tenant',
            session_key='expired_session',
            access_time=timezone.now() - timezone.timedelta(days=2),
            is_active=True
        )
        
        # Run full migration
        out = StringIO()
        call_command('migrate_admin_data', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Admin data migration completed successfully', output)
        
        # Verify all migrations were applied
        self.superadmin.refresh_from_db()
        self.assertEqual(self.superadmin.theme_preference, 'light')
        self.assertTrue(self.superadmin.can_create_tenants)
        
        self.tenant.refresh_from_db()
        self.assertIsNotNone(self.tenant.subscription_plan_fk)
        
        # Verify expired session was deactivated
        expired_sessions = SuperAdminSession.objects.filter(
            session_key='expired_session',
            is_active=False
        )
        self.assertEqual(expired_sessions.count(), 1)


class AdminDataIntegrityTestCase(TestCase):
    """Test admin data integrity checks."""
    
    def setUp(self):
        """Set up test data."""
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='test@example.com',
            password='testpass123',
            theme_preference='light',
            can_create_tenants=True,
            can_suspend_tenants=True,
            can_access_all_data=True
        )
        
        self.tenant = Tenant.objects.create(
            schema_name='test_tenant',
            name='Test Shop',
            owner_name='Test Owner',
            owner_email='owner@test.com'
        )
        
        # Create subscription plan
        self.plan = SubscriptionPlan.objects.create(
            name='Test Plan',
            name_persian='پلن تست',
            plan_type='basic',
            monthly_price_toman=500000,
            max_users=5,
            max_inventory_items=1000,
            max_customers=500,
            max_monthly_transactions=1000,
            max_storage_gb=5,
            features={'pos_system': True}
        )
        
        self.tenant.subscription_plan_fk = self.plan
        self.tenant.save()
    
    def test_superadmin_data_integrity(self):
        """Test SuperAdmin data integrity."""
        # Test valid SuperAdmin
        self.assertTrue(self.superadmin.username)
        self.assertTrue(self.superadmin.email)
        self.assertIn(self.superadmin.theme_preference, ['light', 'dark'])
        self.assertIsNotNone(self.superadmin.can_create_tenants)
        self.assertIsNotNone(self.superadmin.can_suspend_tenants)
        self.assertIsNotNone(self.superadmin.can_access_all_data)
    
    def test_tenant_data_integrity(self):
        """Test tenant data integrity."""
        # Test valid tenant
        self.assertTrue(self.tenant.schema_name)
        self.assertTrue(self.tenant.name)
        self.assertIsNotNone(self.tenant.subscription_plan_fk)
        self.assertEqual(self.tenant.subscription_plan_fk.plan_type, 'basic')
    
    def test_subscription_plan_integrity(self):
        """Test subscription plan data integrity."""
        # Test valid subscription plan
        self.assertTrue(self.plan.name)
        self.assertTrue(self.plan.name_persian)
        self.assertIn(self.plan.plan_type, ['basic', 'pro', 'enterprise'])
        self.assertGreater(self.plan.monthly_price_toman, 0)
        self.assertGreater(self.plan.max_users, 0)
        self.assertIsInstance(self.plan.features, dict)
    
    def test_audit_log_integrity(self):
        """Test audit log data integrity."""
        log = TenantAccessLog.objects.create(
            user_type='superadmin',
            user_id=self.superadmin.id,
            username=self.superadmin.username,
            tenant_schema=self.tenant.schema_name,
            tenant_name=self.tenant.name,
            action='login',
            success=True
        )
        
        # Test valid audit log
        self.assertIn(log.user_type, ['superadmin', 'user'])
        self.assertTrue(log.username)
        self.assertTrue(log.tenant_schema)
        self.assertTrue(log.action)
        self.assertIsNotNone(log.success)
    
    def test_session_integrity(self):
        """Test session data integrity."""
        session = SuperAdminSession.objects.create(
            super_admin=self.superadmin,
            tenant_schema=self.tenant.schema_name,
            session_key='test_session',
            is_active=True
        )
        
        # Test valid session
        self.assertIsNotNone(session.super_admin)
        self.assertTrue(session.tenant_schema)
        self.assertTrue(session.session_key)
        self.assertIsNotNone(session.is_active)


class AdminDataPerformanceTestCase(TestCase):
    """Test admin data performance."""
    
    def setUp(self):
        """Set up performance test data."""
        # Create multiple SuperAdmins
        for i in range(10):
            SuperAdmin.objects.create_user(
                username=f'admin{i}',
                email=f'admin{i}@test.com',
                password='testpass123'
            )
        
        # Create multiple tenants
        for i in range(20):
            Tenant.objects.create(
                schema_name=f'tenant{i}',
                name=f'Shop {i}',
                owner_name=f'Owner {i}',
                owner_email=f'owner{i}@test.com'
            )
        
        # Create multiple audit logs
        admin = SuperAdmin.objects.first()
        tenant = Tenant.objects.first()
        
        for i in range(100):
            TenantAccessLog.objects.create(
                user_type='superadmin',
                user_id=admin.id,
                username=admin.username,
                tenant_schema=tenant.schema_name,
                tenant_name=tenant.name,
                action='view',
                success=True
            )
    
    def test_superadmin_query_performance(self):
        """Test SuperAdmin query performance."""
        import time
        
        start_time = time.time()
        list(SuperAdmin.objects.all())
        query_time = time.time() - start_time
        
        # Should complete within reasonable time
        self.assertLess(query_time, 1.0)
    
    def test_tenant_query_performance(self):
        """Test tenant query performance."""
        import time
        
        start_time = time.time()
        list(Tenant.objects.all())
        query_time = time.time() - start_time
        
        # Should complete within reasonable time
        self.assertLess(query_time, 1.0)
    
    def test_audit_log_query_performance(self):
        """Test audit log query performance."""
        import time
        
        start_time = time.time()
        list(TenantAccessLog.objects.all()[:50])
        query_time = time.time() - start_time
        
        # Should complete within reasonable time
        self.assertLess(query_time, 2.0)
    
    def test_complex_query_performance(self):
        """Test complex query performance."""
        import time
        
        start_time = time.time()
        
        # Complex query with joins
        result = list(
            TenantAccessLog.objects.select_related().filter(
                user_type='superadmin',
                success=True,
                timestamp__gte=timezone.now() - timezone.timedelta(days=7)
            )[:20]
        )
        
        query_time = time.time() - start_time
        
        # Should complete within reasonable time
        self.assertLess(query_time, 2.0)
        self.assertGreater(len(result), 0)


@pytest.mark.django_db
class TestAdminDataMigrationPytest:
    """Pytest-based tests for admin data migration."""
    
    def test_migration_command_exists(self):
        """Test that migration command exists and is callable."""
        from django.core.management import get_commands
        commands = get_commands()
        assert 'migrate_admin_data' in commands
    
    def test_migration_with_no_data(self):
        """Test migration when no data exists."""
        out = StringIO()
        call_command('migrate_admin_data', '--dry-run', stdout=out)
        
        output = out.getvalue()
        assert 'Dry run completed' in output
        assert 'Migrated 0 SuperAdmin records' in output
    
    def test_backup_creation_with_no_data(self):
        """Test backup creation when no data exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('zargar.tenants.management.commands.migrate_admin_data.settings') as mock_settings:
                mock_settings.BASE_DIR = temp_dir
                
                out = StringIO()
                call_command('migrate_admin_data', '--backup-data', '--dry-run', stdout=out)
                
                output = out.getvalue()
                assert 'Backup created:' in output
    
    @pytest.mark.parametrize('theme', ['light', 'dark'])
    def test_theme_migration(self, theme):
        """Test theme preference migration."""
        admin = SuperAdmin.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            theme_preference=theme
        )
        
        out = StringIO()
        call_command('migrate_admin_data', stdout=out)
        
        admin.refresh_from_db()
        assert admin.theme_preference == theme
    
    def test_error_handling(self):
        """Test error handling in migration command."""
        with patch('zargar.tenants.management.commands.migrate_admin_data.SuperAdmin.objects.all') as mock_all:
            mock_all.side_effect = Exception('Database error')
            
            with pytest.raises(Exception):
                call_command('migrate_admin_data')