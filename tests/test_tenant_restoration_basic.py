"""
Basic tests for tenant restoration system functionality.

Tests core functionality without complex database operations.
"""
import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from zargar.admin_panel.models import BackupJob, RestoreJob, TenantSnapshot
from zargar.admin_panel.tenant_restoration import tenant_restoration_manager
from zargar.tenants.models import Tenant


class TenantRestorationBasicTest(TestCase):
    """
    Basic tests for tenant restoration functionality.
    """
    
    def setUp(self):
        """Set up test data."""
        # Create test tenant
        self.tenant = Tenant.objects.create(
            schema_name='test_tenant',
            name='Test Tenant',
            domain_url='test.zargar.com',
            is_active=True
        )
        
        # Create completed backup job
        self.backup_job = BackupJob.objects.create(
            name='Test Backup',
            backup_type='full_system',
            status='completed',
            file_path='backups/test_backup.sql',
            file_size_bytes=1024000,
            storage_backends=['cloudflare_r2'],
            created_by_username='test_admin'
        )
    
    def test_tenant_snapshot_model_creation(self):
        """Test creating TenantSnapshot model instances."""
        snapshot = TenantSnapshot.objects.create(
            name='Test Snapshot',
            snapshot_type='pre_operation',
            tenant_schema=self.tenant.schema_name,
            tenant_domain=self.tenant.domain_url,
            operation_description='Test operation requiring snapshot',
            status='completed',
            backup_job=self.backup_job,
            file_path='backups/snapshot.sql',
            file_size_bytes=512000,
            created_by_username='test_admin'
        )
        
        # Verify snapshot properties
        self.assertEqual(snapshot.tenant_schema, self.tenant.schema_name)
        self.assertEqual(snapshot.snapshot_type, 'pre_operation')
        self.assertEqual(snapshot.status, 'completed')
        self.assertTrue(snapshot.is_available_for_restore)
        self.assertFalse(snapshot.is_expired)
        self.assertEqual(snapshot.file_size_human, '500.0 KB')
    
    def test_restore_job_model_creation(self):
        """Test creating RestoreJob model instances."""
        restore_job = RestoreJob.objects.create(
            restore_type='single_tenant',
            source_backup=self.backup_job,
            target_tenant_schema=self.tenant.schema_name,
            confirmed_by_typing=self.tenant.domain_url,
            created_by_id=1,
            created_by_username='test_admin'
        )
        
        # Verify restore job properties
        self.assertEqual(restore_job.restore_type, 'single_tenant')
        self.assertEqual(restore_job.target_tenant_schema, self.tenant.schema_name)
        self.assertEqual(restore_job.source_backup, self.backup_job)
        self.assertEqual(restore_job.status, 'pending')
        
        # Test status updates
        restore_job.mark_as_running()
        self.assertEqual(restore_job.status, 'running')
        self.assertIsNotNone(restore_job.started_at)
        
        restore_job.mark_as_completed()
        self.assertEqual(restore_job.status, 'completed')
        self.assertIsNotNone(restore_job.completed_at)
        self.assertEqual(restore_job.progress_percentage, 100)
    
    def test_tenant_restoration_manager_validation(self):
        """Test tenant restoration manager validation methods."""
        manager = tenant_restoration_manager
        
        # Test tenant existence validation
        self.assertTrue(manager._validate_tenant_exists(self.tenant.schema_name))
        self.assertFalse(manager._validate_tenant_exists('nonexistent_tenant'))
        
        # Test restoration request validation
        result = manager._validate_restoration_request(
            backup_id=str(self.backup_job.job_id),
            target_tenant_schema=self.tenant.schema_name,
            confirmation_text=self.tenant.domain_url
        )
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['backup_job'], self.backup_job)
        self.assertEqual(result['tenant'], self.tenant)
        
        # Test validation with wrong confirmation text
        result = manager._validate_restoration_request(
            backup_id=str(self.backup_job.job_id),
            target_tenant_schema=self.tenant.schema_name,
            confirmation_text='wrong.domain.com'
        )
        
        self.assertFalse(result['valid'])
        self.assertIn('Confirmation text does not match', result['error'])
    
    def test_get_available_snapshots(self):
        """Test retrieving available snapshots."""
        # Create test snapshots
        snapshot1 = TenantSnapshot.objects.create(
            name='Available Snapshot 1',
            snapshot_type='pre_operation',
            tenant_schema=self.tenant.schema_name,
            tenant_domain=self.tenant.domain_url,
            operation_description='Operation 1',
            status='completed',
            file_size_bytes=1024000,
            created_by_username='test_admin'
        )
        
        snapshot2 = TenantSnapshot.objects.create(
            name='Available Snapshot 2',
            snapshot_type='manual',
            tenant_schema='another_tenant',
            tenant_domain='another.zargar.com',
            operation_description='Operation 2',
            status='completed',
            file_size_bytes=2048000,
            created_by_username='test_admin'
        )
        
        # Create expired snapshot (should not be included)
        TenantSnapshot.objects.create(
            name='Expired Snapshot',
            snapshot_type='pre_operation',
            tenant_schema=self.tenant.schema_name,
            operation_description='Expired operation',
            status='completed',
            expires_at=timezone.now() - timedelta(days=1),
            created_by_username='test_admin'
        )
        
        # Get all available snapshots
        snapshots = tenant_restoration_manager.get_available_snapshots()
        
        # Should return 2 available snapshots (not the expired one)
        self.assertEqual(len(snapshots), 2)
        
        # Verify snapshot data structure
        snapshot_ids = [s['snapshot_id'] for s in snapshots]
        self.assertIn(str(snapshot1.snapshot_id), snapshot_ids)
        self.assertIn(str(snapshot2.snapshot_id), snapshot_ids)
        
        # Test filtering by tenant
        tenant_snapshots = tenant_restoration_manager.get_available_snapshots(
            tenant_schema=self.tenant.schema_name
        )
        self.assertEqual(len(tenant_snapshots), 1)
        self.assertEqual(tenant_snapshots[0]['tenant_schema'], self.tenant.schema_name)
    
    def test_restoration_status_tracking(self):
        """Test tracking restoration job status."""
        # Create a restore job
        restore_job = RestoreJob.objects.create(
            restore_type='single_tenant',
            source_backup=self.backup_job,
            target_tenant_schema=self.tenant.schema_name,
            confirmed_by_typing=self.tenant.domain_url,
            status='running',
            progress_percentage=50,
            created_by_id=1,
            created_by_username='test_admin'
        )
        
        # Add some log messages
        restore_job.add_log_message('info', 'Starting restoration')
        restore_job.add_log_message('info', 'Downloaded backup file')
        restore_job.add_log_message('info', 'Restoring data')
        
        # Get status using manager
        status = tenant_restoration_manager.get_restoration_status(str(restore_job.job_id))
        
        # Verify status
        self.assertTrue(status['success'])
        self.assertEqual(status['status'], 'running')
        self.assertEqual(status['progress_percentage'], 50)
        self.assertEqual(status['target_tenant_schema'], self.tenant.schema_name)
        self.assertEqual(status['restore_type'], 'single_tenant')
        self.assertEqual(len(status['log_messages']), 3)
        
        # Test with non-existent job
        status = tenant_restoration_manager.get_restoration_status(str(uuid.uuid4()))
        self.assertFalse(status['success'])
        self.assertIn('not found', status['error'])
    
    def test_snapshot_expiration_logic(self):
        """Test snapshot expiration and availability logic."""
        # Create active snapshot
        active_snapshot = TenantSnapshot.objects.create(
            name='Active Snapshot',
            snapshot_type='pre_operation',
            tenant_schema=self.tenant.schema_name,
            operation_description='Active operation',
            status='completed',
            expires_at=timezone.now() + timedelta(days=1),
            created_by_username='test_admin'
        )
        
        # Create expired snapshot
        expired_snapshot = TenantSnapshot.objects.create(
            name='Expired Snapshot',
            snapshot_type='pre_operation',
            tenant_schema=self.tenant.schema_name,
            operation_description='Expired operation',
            status='completed',
            expires_at=timezone.now() - timedelta(days=1),
            created_by_username='test_admin'
        )
        
        # Test availability
        self.assertTrue(active_snapshot.is_available_for_restore)
        self.assertFalse(active_snapshot.is_expired)
        
        self.assertFalse(expired_snapshot.is_available_for_restore)
        self.assertTrue(expired_snapshot.is_expired)
    
    def test_snapshot_restoration_tracking(self):
        """Test snapshot restoration tracking."""
        snapshot = TenantSnapshot.objects.create(
            name='Test Snapshot',
            snapshot_type='pre_operation',
            tenant_schema=self.tenant.schema_name,
            operation_description='Test operation',
            status='completed',
            backup_job=self.backup_job,
            created_by_username='test_admin'
        )
        
        # Mark as restored
        snapshot.mark_as_restored(
            restored_by_id=1,
            restored_by_username='test_admin'
        )
        
        # Verify restoration tracking
        self.assertIsNotNone(snapshot.restored_at)
        self.assertEqual(snapshot.restored_by_id, 1)
        self.assertEqual(snapshot.restored_by_username, 'test_admin')
    
    def test_backup_job_extended_functionality(self):
        """Test extended BackupJob functionality for snapshots."""
        # Test backup job with tenant schema
        tenant_backup = BackupJob.objects.create(
            name='Tenant Backup',
            backup_type='tenant_only',
            tenant_schema=self.tenant.schema_name,
            status='completed',
            file_path='backups/tenant_backup.sql',
            file_size_bytes=512000,
            created_by_username='test_admin'
        )
        
        # Verify tenant-specific backup
        self.assertEqual(tenant_backup.backup_type, 'tenant_only')
        self.assertEqual(tenant_backup.tenant_schema, self.tenant.schema_name)
        self.assertTrue(tenant_backup.is_completed)
        
        # Test progress tracking
        running_backup = BackupJob.objects.create(
            name='Running Backup',
            backup_type='tenant_only',
            status='pending',
            created_by_username='test_admin'
        )
        
        running_backup.mark_as_running()
        self.assertTrue(running_backup.is_running)
        self.assertEqual(running_backup.progress_percentage, 0)
        
        running_backup.update_progress(50, 'Halfway complete')
        self.assertEqual(running_backup.progress_percentage, 50)
        
        running_backup.mark_as_completed(
            file_path='backups/completed.sql',
            file_size_bytes=1024000,
            storage_backends=['cloudflare_r2']
        )
        self.assertTrue(running_backup.is_completed)
        self.assertEqual(running_backup.progress_percentage, 100)
    
    @patch('zargar.admin_panel.tenant_restoration.create_tenant_snapshot')
    def test_pre_operation_snapshot_creation_mock(self, mock_create_snapshot):
        """Test pre-operation snapshot creation with mocked task."""
        # Mock successful snapshot creation
        mock_task_result = MagicMock()
        mock_task_result.get.return_value = {
            'success': True,
            'snapshot_id': str(uuid.uuid4()),
            'backup_id': str(uuid.uuid4()),
            'file_size': 1024000,
            'tenant_schema': self.tenant.schema_name
        }
        mock_create_snapshot.apply_async.return_value = mock_task_result
        
        # Test snapshot creation
        result = tenant_restoration_manager.create_pre_operation_snapshot(
            tenant_schema=self.tenant.schema_name,
            operation_description='Test data import',
            created_by_id=1,
            created_by_username='test_admin'
        )
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertIn('snapshot_id', result)
        self.assertEqual(result['tenant_schema'], self.tenant.schema_name)
        
        # Verify task was called
        mock_create_snapshot.apply_async.assert_called_once()
    
    def test_validation_error_handling(self):
        """Test error handling in validation methods."""
        manager = tenant_restoration_manager
        
        # Test with non-existent backup
        result = manager._validate_restoration_request(
            backup_id=str(uuid.uuid4()),
            target_tenant_schema=self.tenant.schema_name,
            confirmation_text=self.tenant.domain_url
        )
        
        self.assertFalse(result['valid'])
        self.assertIn('not found', result['error'])
        
        # Test with failed backup
        failed_backup = BackupJob.objects.create(
            name='Failed Backup',
            backup_type='full_system',
            status='failed',
            created_by_username='test_admin'
        )
        
        result = manager._validate_restoration_request(
            backup_id=str(failed_backup.job_id),
            target_tenant_schema=self.tenant.schema_name,
            confirmation_text=self.tenant.domain_url
        )
        
        self.assertFalse(result['valid'])
        self.assertIn('is not completed', result['error'])