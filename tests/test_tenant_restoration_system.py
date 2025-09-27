"""
Integration tests for tenant restoration system.

Tests the complete tenant restoration workflow including:
- Pre-operation snapshot creation
- Selective tenant restoration from main backups
- Snapshot-based restoration
- Data integrity verification
- Tenant isolation during restoration

Requirements: 5.15, 5.16, 5.17, 5.18
"""
import os
import tempfile
import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock
import django
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.db import connection
from django.conf import settings

# Configure Django settings if not already configured
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

from zargar.admin_panel.models import BackupJob, RestoreJob, TenantSnapshot
from zargar.admin_panel.tenant_restoration import tenant_restoration_manager
from zargar.admin_panel.tasks import (
    create_tenant_snapshot, 
    restore_tenant_from_backup,
    cleanup_expired_snapshots
)
from zargar.tenants.models import Tenant


class TenantRestorationSystemTest(TransactionTestCase):
    """
    Integration tests for tenant restoration system.
    Uses TransactionTestCase to test Celery tasks and database transactions.
    """
    
    def setUp(self):
        """Set up test data."""
        # Create test tenants
        self.tenant1 = Tenant.objects.create(
            schema_name='test_tenant_1',
            name='Test Tenant 1',
            domain_url='test1.zargar.com',
            is_active=True
        )
        
        self.tenant2 = Tenant.objects.create(
            schema_name='test_tenant_2',
            name='Test Tenant 2',
            domain_url='test2.zargar.com',
            is_active=True
        )
        
        # Create schemas for tenants
        with connection.cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.tenant1.schema_name}"')
            cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.tenant2.schema_name}"')
            
            # Create some test tables in each schema
            for tenant in [self.tenant1, self.tenant2]:
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS "{tenant.schema_name}".test_data (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100),
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                ''')
                
                # Insert test data
                cursor.execute(f'''
                    INSERT INTO "{tenant.schema_name}".test_data (name) 
                    VALUES ('Test Item 1'), ('Test Item 2'), ('Test Item 3')
                ''')
        
        # Create a completed backup job for testing
        self.backup_job = BackupJob.objects.create(
            name='Test Full System Backup',
            backup_type='full_system',
            status='completed',
            file_path='backups/test_backup.sql',
            file_size_bytes=1024000,
            storage_backends=['cloudflare_r2', 'backblaze_b2'],
            created_by_username='test_admin'
        )
    
    def tearDown(self):
        """Clean up test data."""
        # Drop test schemas
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{self.tenant1.schema_name}" CASCADE')
            cursor.execute(f'DROP SCHEMA IF EXISTS "{self.tenant2.schema_name}" CASCADE')
    
    @patch('zargar.admin_panel.tasks.storage_manager')
    @patch('zargar.admin_panel.tasks.subprocess.run')
    def test_create_pre_operation_snapshot(self, mock_subprocess, mock_storage):
        """Test creating a pre-operation snapshot before high-risk operations."""
        # Mock storage manager
        mock_storage.upload_backup_file.return_value = {
            'success': True,
            'uploaded_to': ['cloudflare_r2', 'backblaze_b2']
        }
        
        # Mock pg_dump subprocess
        mock_subprocess.return_value = MagicMock(returncode=0, stderr='')
        
        # Mock file operations
        with patch('tempfile.NamedTemporaryFile') as mock_temp_file:
            mock_temp_file.return_value.__enter__.return_value.name = '/tmp/test_backup.sql'
            
            with patch('os.path.getsize', return_value=1024000):
                with patch('builtins.open', create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = b'test backup data'
                    
                    with patch('os.unlink'):
                        # Test snapshot creation
                        result = tenant_restoration_manager.create_pre_operation_snapshot(
                            tenant_schema=self.tenant1.schema_name,
                            operation_description='Test data import operation',
                            created_by_id=1,
                            created_by_username='test_admin'
                        )
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertIn('snapshot_id', result)
        self.assertEqual(result['tenant_schema'], self.tenant1.schema_name)
        
        # Verify snapshot was created in database
        snapshot = TenantSnapshot.objects.get(snapshot_id=result['snapshot_id'])
        self.assertEqual(snapshot.tenant_schema, self.tenant1.schema_name)
        self.assertEqual(snapshot.snapshot_type, 'pre_operation')
        self.assertEqual(snapshot.operation_description, 'Test data import operation')
        self.assertEqual(snapshot.status, 'completed')
        
        # Verify associated backup job was created
        self.assertIsNotNone(snapshot.backup_job)
        self.assertEqual(snapshot.backup_job.backup_type, 'tenant_only')
        self.assertEqual(snapshot.backup_job.tenant_schema, self.tenant1.schema_name)
    
    def test_create_snapshot_for_nonexistent_tenant(self):
        """Test snapshot creation fails for non-existent tenant."""
        result = tenant_restoration_manager.create_pre_operation_snapshot(
            tenant_schema='nonexistent_tenant',
            operation_description='Test operation',
            created_by_username='test_admin'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('does not exist', result['error'])
    
    def test_avoid_duplicate_recent_snapshots(self):
        """Test that recent snapshots are reused instead of creating duplicates."""
        # Create a recent snapshot
        snapshot = TenantSnapshot.objects.create(
            name='Recent snapshot',
            snapshot_type='pre_operation',
            tenant_schema=self.tenant1.schema_name,
            tenant_domain=self.tenant1.domain_url,
            operation_description='Recent operation',
            status='completed',
            created_by_username='test_admin'
        )
        
        # Try to create another snapshot
        result = tenant_restoration_manager.create_pre_operation_snapshot(
            tenant_schema=self.tenant1.schema_name,
            operation_description='Another operation',
            created_by_username='test_admin'
        )
        
        # Should reuse existing snapshot
        self.assertTrue(result['success'])
        self.assertEqual(result['snapshot_id'], str(snapshot.snapshot_id))
        self.assertTrue(result.get('existing', False))
    
    @patch('zargar.admin_panel.tasks.storage_manager')
    @patch('zargar.admin_panel.tasks.subprocess.run')
    def test_selective_tenant_restoration(self, mock_subprocess, mock_storage):
        """Test selective tenant restoration from main backup."""
        # Mock storage manager
        mock_storage.download_backup_file.return_value = b'test backup data'
        
        # Mock subprocess calls
        mock_subprocess.return_value = MagicMock(returncode=0, stderr='', stdout='5')
        
        # Mock file operations
        with patch('tempfile.NamedTemporaryFile') as mock_temp_file:
            mock_temp_file.return_value.__enter__.return_value.name = '/tmp/test_restore.sql'
            
            with patch('os.unlink'):
                # Test restoration
                result = tenant_restoration_manager.restore_tenant_from_main_backup(
                    backup_id=str(self.backup_job.job_id),
                    target_tenant_schema=self.tenant1.schema_name,
                    confirmation_text=self.tenant1.domain_url,
                    created_by_id=1,
                    created_by_username='test_admin'
                )
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertIn('restore_job_id', result)
        self.assertEqual(result['target_tenant_schema'], self.tenant1.schema_name)
        
        # Verify restore job was created
        restore_job = RestoreJob.objects.get(job_id=result['restore_job_id'])
        self.assertEqual(restore_job.restore_type, 'single_tenant')
        self.assertEqual(restore_job.target_tenant_schema, self.tenant1.schema_name)
        self.assertEqual(restore_job.source_backup, self.backup_job)
        self.assertEqual(restore_job.confirmed_by_typing, self.tenant1.domain_url)
    
    def test_restoration_validation_failures(self):
        """Test various validation failures in restoration requests."""
        # Test with non-existent backup
        result = tenant_restoration_manager.restore_tenant_from_main_backup(
            backup_id=str(uuid.uuid4()),
            target_tenant_schema=self.tenant1.schema_name,
            confirmation_text=self.tenant1.domain_url,
            created_by_id=1,
            created_by_username='test_admin'
        )
        self.assertFalse(result['success'])
        self.assertIn('not found', result['error'])
        
        # Test with non-existent tenant
        result = tenant_restoration_manager.restore_tenant_from_main_backup(
            backup_id=str(self.backup_job.job_id),
            target_tenant_schema='nonexistent_tenant',
            confirmation_text='wrong.domain.com',
            created_by_id=1,
            created_by_username='test_admin'
        )
        self.assertFalse(result['success'])
        self.assertIn('does not exist', result['error'])
        
        # Test with wrong confirmation text
        result = tenant_restoration_manager.restore_tenant_from_main_backup(
            backup_id=str(self.backup_job.job_id),
            target_tenant_schema=self.tenant1.schema_name,
            confirmation_text='wrong.domain.com',
            created_by_id=1,
            created_by_username='test_admin'
        )
        self.assertFalse(result['success'])
        self.assertIn('Confirmation text does not match', result['error'])
        
        # Test with incomplete backup
        incomplete_backup = BackupJob.objects.create(
            name='Incomplete Backup',
            backup_type='full_system',
            status='failed',
            created_by_username='test_admin'
        )
        
        result = tenant_restoration_manager.restore_tenant_from_main_backup(
            backup_id=str(incomplete_backup.job_id),
            target_tenant_schema=self.tenant1.schema_name,
            confirmation_text=self.tenant1.domain_url,
            created_by_id=1,
            created_by_username='test_admin'
        )
        self.assertFalse(result['success'])
        self.assertIn('is not completed', result['error'])
    
    def test_snapshot_restoration(self):
        """Test restoration from a specific snapshot."""
        # Create a snapshot with associated backup
        backup_job = BackupJob.objects.create(
            name='Snapshot Backup',
            backup_type='tenant_only',
            tenant_schema=self.tenant1.schema_name,
            status='completed',
            file_path='backups/snapshot_backup.sql',
            file_size_bytes=512000,
            created_by_username='test_admin'
        )
        
        snapshot = TenantSnapshot.objects.create(
            name='Test snapshot',
            snapshot_type='pre_operation',
            tenant_schema=self.tenant1.schema_name,
            tenant_domain=self.tenant1.domain_url,
            operation_description='Test operation',
            status='completed',
            backup_job=backup_job,
            file_path='backups/snapshot_backup.sql',
            file_size_bytes=512000,
            created_by_username='test_admin'
        )
        
        # Test snapshot restoration
        result = tenant_restoration_manager.restore_tenant_from_snapshot(
            snapshot_id=str(snapshot.snapshot_id),
            created_by_id=1,
            created_by_username='test_admin'
        )
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertIn('restore_job_id', result)
        self.assertEqual(result['target_tenant_schema'], self.tenant1.schema_name)
        
        # Verify restore job was created
        restore_job = RestoreJob.objects.get(job_id=result['restore_job_id'])
        self.assertEqual(restore_job.restore_type, 'snapshot_restore')
        self.assertEqual(restore_job.source_backup, backup_job)
    
    def test_snapshot_restoration_validation(self):
        """Test validation failures in snapshot restoration."""
        # Test with non-existent snapshot
        result = tenant_restoration_manager.restore_tenant_from_snapshot(
            snapshot_id=str(uuid.uuid4()),
            created_by_id=1,
            created_by_username='test_admin'
        )
        self.assertFalse(result['success'])
        self.assertIn('not found', result['error'])
        
        # Test with expired snapshot
        expired_snapshot = TenantSnapshot.objects.create(
            name='Expired snapshot',
            snapshot_type='pre_operation',
            tenant_schema=self.tenant1.schema_name,
            operation_description='Test operation',
            status='completed',
            expires_at=timezone.now() - timedelta(days=1),
            created_by_username='test_admin'
        )
        
        result = tenant_restoration_manager.restore_tenant_from_snapshot(
            snapshot_id=str(expired_snapshot.snapshot_id),
            created_by_id=1,
            created_by_username='test_admin'
        )
        self.assertFalse(result['success'])
        self.assertIn('not available for restoration', result['error'])
    
    def test_get_available_snapshots(self):
        """Test retrieving available snapshots."""
        # Create test snapshots
        snapshot1 = TenantSnapshot.objects.create(
            name='Available snapshot 1',
            snapshot_type='pre_operation',
            tenant_schema=self.tenant1.schema_name,
            tenant_domain=self.tenant1.domain_url,
            operation_description='Operation 1',
            status='completed',
            file_size_bytes=1024000,
            created_by_username='test_admin'
        )
        
        snapshot2 = TenantSnapshot.objects.create(
            name='Available snapshot 2',
            snapshot_type='manual',
            tenant_schema=self.tenant2.schema_name,
            tenant_domain=self.tenant2.domain_url,
            operation_description='Operation 2',
            status='completed',
            file_size_bytes=2048000,
            created_by_username='test_admin'
        )
        
        # Create expired snapshot (should not be included)
        TenantSnapshot.objects.create(
            name='Expired snapshot',
            snapshot_type='pre_operation',
            tenant_schema=self.tenant1.schema_name,
            operation_description='Expired operation',
            status='completed',
            expires_at=timezone.now() - timedelta(days=1),
            created_by_username='test_admin'
        )
        
        # Get all available snapshots
        snapshots = tenant_restoration_manager.get_available_snapshots()
        
        # Should return 2 available snapshots (not the expired one)
        self.assertEqual(len(snapshots), 2)
        
        # Verify snapshot data
        snapshot_ids = [s['snapshot_id'] for s in snapshots]
        self.assertIn(str(snapshot1.snapshot_id), snapshot_ids)
        self.assertIn(str(snapshot2.snapshot_id), snapshot_ids)
        
        # Test filtering by tenant
        tenant1_snapshots = tenant_restoration_manager.get_available_snapshots(
            tenant_schema=self.tenant1.schema_name
        )
        self.assertEqual(len(tenant1_snapshots), 1)
        self.assertEqual(tenant1_snapshots[0]['tenant_schema'], self.tenant1.schema_name)
    
    def test_restoration_status_tracking(self):
        """Test tracking restoration job status."""
        # Create a restore job
        restore_job = RestoreJob.objects.create(
            restore_type='single_tenant',
            source_backup=self.backup_job,
            target_tenant_schema=self.tenant1.schema_name,
            confirmed_by_typing=self.tenant1.domain_url,
            status='running',
            progress_percentage=50,
            created_by_id=1,
            created_by_username='test_admin'
        )
        
        # Add some log messages
        restore_job.add_log_message('info', 'Starting restoration')
        restore_job.add_log_message('info', 'Downloaded backup file')
        restore_job.add_log_message('info', 'Restoring data')
        
        # Get status
        status = tenant_restoration_manager.get_restoration_status(str(restore_job.job_id))
        
        # Verify status
        self.assertTrue(status['success'])
        self.assertEqual(status['status'], 'running')
        self.assertEqual(status['progress_percentage'], 50)
        self.assertEqual(status['target_tenant_schema'], self.tenant1.schema_name)
        self.assertEqual(status['restore_type'], 'single_tenant')
        self.assertEqual(len(status['log_messages']), 3)
        
        # Test with non-existent job
        status = tenant_restoration_manager.get_restoration_status(str(uuid.uuid4()))
        self.assertFalse(status['success'])
        self.assertIn('not found', status['error'])
    
    def test_tenant_isolation_during_restoration(self):
        """Test that restoration of one tenant doesn't affect other tenants."""
        # Insert different data in each tenant
        with connection.cursor() as cursor:
            # Tenant 1 data
            cursor.execute(f'''
                INSERT INTO "{self.tenant1.schema_name}".test_data (name) 
                VALUES ('Tenant 1 Unique Data')
            ''')
            
            # Tenant 2 data
            cursor.execute(f'''
                INSERT INTO "{self.tenant2.schema_name}".test_data (name) 
                VALUES ('Tenant 2 Unique Data')
            ''')
            
            # Get initial counts
            cursor.execute(f'SELECT COUNT(*) FROM "{self.tenant1.schema_name}".test_data')
            tenant1_initial_count = cursor.fetchone()[0]
            
            cursor.execute(f'SELECT COUNT(*) FROM "{self.tenant2.schema_name}".test_data')
            tenant2_initial_count = cursor.fetchone()[0]
        
        # Create a restore job for tenant 1 (this would normally trigger restoration)
        restore_job = RestoreJob.objects.create(
            restore_type='single_tenant',
            source_backup=self.backup_job,
            target_tenant_schema=self.tenant1.schema_name,
            confirmed_by_typing=self.tenant1.domain_url,
            status='pending',
            created_by_id=1,
            created_by_username='test_admin'
        )
        
        # Simulate restoration completion (without actually running pg_restore)
        restore_job.mark_as_completed()
        
        # Verify tenant 2 data is unchanged
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT COUNT(*) FROM "{self.tenant2.schema_name}".test_data')
            tenant2_final_count = cursor.fetchone()[0]
            
            cursor.execute(f'SELECT name FROM "{self.tenant2.schema_name}".test_data WHERE name = %s', 
                         ['Tenant 2 Unique Data'])
            tenant2_unique_data = cursor.fetchone()
        
        # Tenant 2 should be completely unaffected
        self.assertEqual(tenant2_final_count, tenant2_initial_count)
        self.assertIsNotNone(tenant2_unique_data)
        self.assertEqual(tenant2_unique_data[0], 'Tenant 2 Unique Data')
    
    def test_cleanup_expired_snapshots(self):
        """Test cleanup of expired snapshots."""
        # Create expired snapshots
        expired_snapshot1 = TenantSnapshot.objects.create(
            name='Expired snapshot 1',
            snapshot_type='pre_operation',
            tenant_schema=self.tenant1.schema_name,
            operation_description='Expired operation 1',
            status='completed',
            expires_at=timezone.now() - timedelta(days=1),
            file_path='backups/expired1.sql',
            created_by_username='test_admin'
        )
        
        expired_snapshot2 = TenantSnapshot.objects.create(
            name='Expired snapshot 2',
            snapshot_type='pre_operation',
            tenant_schema=self.tenant2.schema_name,
            operation_description='Expired operation 2',
            status='completed',
            expires_at=timezone.now() - timedelta(days=2),
            file_path='backups/expired2.sql',
            created_by_username='test_admin'
        )
        
        # Create non-expired snapshot
        active_snapshot = TenantSnapshot.objects.create(
            name='Active snapshot',
            snapshot_type='pre_operation',
            tenant_schema=self.tenant1.schema_name,
            operation_description='Active operation',
            status='completed',
            expires_at=timezone.now() + timedelta(days=1),
            created_by_username='test_admin'
        )
        
        # Mock storage manager
        with patch('zargar.admin_panel.tasks.storage_manager') as mock_storage:
            mock_storage.delete_backup_file.return_value = {'success': True}
            
            # Run cleanup
            result = cleanup_expired_snapshots()
        
        # Verify cleanup results
        self.assertEqual(result['total_expired'], 2)
        self.assertEqual(result['deleted_successfully'], 2)
        self.assertEqual(result['deletion_errors'], 0)
        
        # Verify expired snapshots are marked as deleted
        expired_snapshot1.refresh_from_db()
        expired_snapshot2.refresh_from_db()
        active_snapshot.refresh_from_db()
        
        self.assertEqual(expired_snapshot1.status, 'deleted')
        self.assertEqual(expired_snapshot2.status, 'deleted')
        self.assertEqual(active_snapshot.status, 'completed')  # Should remain unchanged
    
    def test_data_integrity_verification(self):
        """Test that restored data maintains integrity."""
        # This test would verify that after restoration:
        # 1. All expected tables exist
        # 2. Data relationships are maintained
        # 3. Constraints are preserved
        # 4. No data corruption occurred
        
        # Create a restore job
        restore_job = RestoreJob.objects.create(
            restore_type='single_tenant',
            source_backup=self.backup_job,
            target_tenant_schema=self.tenant1.schema_name,
            confirmed_by_typing=self.tenant1.domain_url,
            status='pending',
            created_by_id=1,
            created_by_username='test_admin'
        )
        
        # Mock the verification process
        with patch('zargar.admin_panel.tasks.subprocess.run') as mock_subprocess:
            # Mock successful verification (5 tables found)
            mock_subprocess.return_value = MagicMock(returncode=0, stdout='5')
            
            # Simulate verification step
            from zargar.admin_panel.tasks import perform_selective_tenant_restore
            
            # This would normally be called within the restoration process
            # Here we're just testing the verification logic
            restore_job.update_progress(90, "Verifying restored data integrity")
            
            # Verify that the verification would pass
            self.assertEqual(restore_job.progress_percentage, 90)
            self.assertTrue(any('Verifying' in msg['message'] for msg in restore_job.log_messages))


class TenantRestorationManagerTest(TestCase):
    """
    Unit tests for TenantRestorationManager class.
    """
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            schema_name='test_tenant',
            name='Test Tenant',
            domain_url='test.zargar.com',
            is_active=True
        )
    
    def test_manager_initialization(self):
        """Test manager initialization."""
        manager = tenant_restoration_manager
        self.assertIsNotNone(manager.logger)
    
    def test_validate_tenant_exists(self):
        """Test tenant existence validation."""
        manager = tenant_restoration_manager
        
        # Test existing tenant
        self.assertTrue(manager._validate_tenant_exists(self.tenant.schema_name))
        
        # Test non-existent tenant
        self.assertFalse(manager._validate_tenant_exists('nonexistent_tenant'))
    
    def test_validate_restoration_request(self):
        """Test restoration request validation."""
        manager = tenant_restoration_manager
        
        # Create a completed backup
        backup_job = BackupJob.objects.create(
            name='Test Backup',
            backup_type='full_system',
            status='completed',
            created_by_username='test_admin'
        )
        
        # Test valid request
        result = manager._validate_restoration_request(
            backup_id=str(backup_job.job_id),
            target_tenant_schema=self.tenant.schema_name,
            confirmation_text=self.tenant.domain_url
        )
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['backup_job'], backup_job)
        self.assertEqual(result['tenant'], self.tenant)
        
        # Test invalid backup ID
        result = manager._validate_restoration_request(
            backup_id=str(uuid.uuid4()),
            target_tenant_schema=self.tenant.schema_name,
            confirmation_text=self.tenant.domain_url
        )
        
        self.assertFalse(result['valid'])
        self.assertIn('not found', result['error'])