"""
Comprehensive tests for the automated backup system.
Tests backup creation, encryption, storage upload, and integrity verification.
"""
import os
import tempfile
import hashlib
import gzip
from unittest.mock import patch, MagicMock, mock_open
from django.test import TestCase, override_settings
from django.utils import timezone
from django.core.files.base import ContentFile
from datetime import datetime, timedelta
from django_tenants.utils import get_tenant_model
from cryptography.fernet import Fernet
from zargar.core.backup_manager import BackupManager, backup_manager
from zargar.system.models import BackupRecord, BackupSchedule, BackupIntegrityCheck
from zargar.core.backup_tasks import (
    create_daily_backup,
    create_weekly_backup,
    create_tenant_backup,
    verify_backup_integrity,
    cleanup_old_backups,
    generate_backup_report
)
from zargar.tenants.models import Tenant


class BackupManagerTestCase(TestCase):
    """Test cases for BackupManager class."""
    
    def setUp(self):
        """Set up test environment."""
        self.backup_manager = BackupManager()
        self.test_tenant_schema = 'test_tenant_schema'
        self.test_tenant_domain = 'test.zargar.com'
        
        # Create test tenant
        self.tenant = Tenant.objects.create(
            schema_name=self.test_tenant_schema,
            name='Test Tenant',
            domain_url=self.test_tenant_domain
        )
    
    def test_backup_manager_initialization(self):
        """Test BackupManager initialization."""
        self.assertIsNotNone(self.backup_manager.storage_manager)
        self.assertIsNotNone(self.backup_manager.encryption_key)
        self.assertIsNotNone(self.backup_manager.fernet)
        self.assertIsInstance(self.backup_manager.fernet, Fernet)
        self.assertTrue(self.backup_manager.compression_enabled)
        self.assertTrue(self.backup_manager.encryption_enabled)
    
    def test_generate_backup_id(self):
        """Test backup ID generation."""
        backup_id = self.backup_manager._generate_backup_id('full_system')
        self.assertIn('full_system_system_', backup_id)
        
        tenant_backup_id = self.backup_manager._generate_backup_id('tenant_only', 'test_schema')
        self.assertIn('tenant_only_test_schema_', tenant_backup_id)
    
    def test_get_backup_file_path(self):
        """Test backup file path generation."""
        backup_id = 'test_backup_20241220_120000'
        
        system_path = self.backup_manager._get_backup_file_path(backup_id, 'full_system')
        self.assertIn('backups/system/', system_path)
        self.assertIn('.sql.gz.enc', system_path)
        
        tenant_path = self.backup_manager._get_backup_file_path(backup_id, 'tenant_only')
        self.assertIn('backups/tenants/', tenant_path)
        
        snapshot_path = self.backup_manager._get_backup_file_path(backup_id, 'snapshot')
        self.assertIn('backups/snapshots/', snapshot_path)
    
    def test_create_pg_dump_command(self):
        """Test pg_dump command creation."""
        # Test full system backup command
        cmd = self.backup_manager._create_pg_dump_command()
        self.assertIn('pg_dump', cmd)
        self.assertIn('--format=custom', cmd)
        self.assertIn('--compress=9', cmd)
        
        # Test tenant-specific backup command
        tenant_cmd = self.backup_manager._create_pg_dump_command(schema_name='test_schema')
        self.assertIn('--schema=test_schema', tenant_cmd)
    
    @patch('subprocess.run')
    def test_execute_pg_dump_success(self, mock_subprocess):
        """Test successful pg_dump execution."""
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stderr = ""
        
        with tempfile.NamedTemporaryFile() as temp_file:
            success, error = self.backup_manager._execute_pg_dump(
                ['pg_dump', '--version'],
                temp_file.name
            )
            
            self.assertTrue(success)
            self.assertEqual(error, "")
    
    @patch('subprocess.run')
    def test_execute_pg_dump_failure(self, mock_subprocess):
        """Test failed pg_dump execution."""
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "Connection failed"
        
        with tempfile.NamedTemporaryFile() as temp_file:
            success, error = self.backup_manager._execute_pg_dump(
                ['pg_dump', '--version'],
                temp_file.name
            )
            
            self.assertFalse(success)
            self.assertIn("Connection failed", error)
    
    def test_compress_file(self):
        """Test file compression."""
        test_content = b"This is test content for compression testing."
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, 'input.txt')
            output_file = os.path.join(temp_dir, 'output.gz')
            
            # Create input file
            with open(input_file, 'wb') as f:
                f.write(test_content)
            
            # Test compression
            success, error = self.backup_manager._compress_file(input_file, output_file)
            
            self.assertTrue(success)
            self.assertEqual(error, "")
            self.assertTrue(os.path.exists(output_file))
            
            # Verify compressed content
            with gzip.open(output_file, 'rb') as f:
                decompressed_content = f.read()
            
            self.assertEqual(decompressed_content, test_content)
    
    def test_encrypt_file(self):
        """Test file encryption."""
        test_content = b"This is test content for encryption testing."
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, 'input.txt')
            output_file = os.path.join(temp_dir, 'output.enc')
            
            # Create input file
            with open(input_file, 'wb') as f:
                f.write(test_content)
            
            # Test encryption
            success, error = self.backup_manager._encrypt_file(input_file, output_file)
            
            self.assertTrue(success)
            self.assertEqual(error, "")
            self.assertTrue(os.path.exists(output_file))
            
            # Verify encrypted content can be decrypted
            with open(output_file, 'rb') as f:
                encrypted_content = f.read()
            
            decrypted_content = self.backup_manager.fernet.decrypt(encrypted_content)
            self.assertEqual(decrypted_content, test_content)
    
    def test_calculate_file_hash(self):
        """Test file hash calculation."""
        test_content = b"This is test content for hash calculation."
        expected_hash = hashlib.sha256(test_content).hexdigest()
        
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(test_content)
            temp_file.flush()
            
            calculated_hash = self.backup_manager._calculate_file_hash(temp_file.name)
            self.assertEqual(calculated_hash, expected_hash)
    
    @patch('zargar.core.backup_manager.backup_manager.storage_manager')
    def test_upload_backup_to_storage(self, mock_storage_manager):
        """Test backup upload to storage."""
        mock_storage_manager.upload_backup_file.return_value = {
            'success': True,
            'uploaded_to': ['cloudflare_r2', 'backblaze_b2']
        }
        
        test_content = b"Test backup content"
        
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(test_content)
            temp_file.flush()
            
            success, result = self.backup_manager._upload_backup_to_storage(
                temp_file.name,
                'test/backup/path.sql.gz.enc'
            )
            
            self.assertTrue(success)
            self.assertIn('cloudflare_r2', result['uploaded_to'])
            self.assertIn('backblaze_b2', result['uploaded_to'])
    
    @patch('zargar.core.backup_manager.backup_manager._execute_pg_dump')
    @patch('zargar.core.backup_manager.backup_manager._upload_backup_to_storage')
    def test_create_full_system_backup_success(self, mock_upload, mock_pg_dump):
        """Test successful full system backup creation."""
        # Mock successful pg_dump
        mock_pg_dump.return_value = (True, "")
        
        # Mock successful upload
        mock_upload.return_value = (True, {
            'success': True,
            'uploaded_to': ['cloudflare_r2', 'backblaze_b2']
        })
        
        result = self.backup_manager.create_full_system_backup(
            frequency='manual',
            created_by='test_user'
        )
        
        self.assertTrue(result['success'])
        self.assertIn('backup_id', result)
        self.assertIn('file_size', result)
        self.assertIn('file_hash', result)
        
        # Verify backup record was created
        backup_record = BackupRecord.objects.get(backup_id=result['backup_id'])
        self.assertEqual(backup_record.backup_type, 'full_system')
        self.assertEqual(backup_record.status, 'completed')
        self.assertEqual(backup_record.created_by, 'test_user')
    
    @patch('zargar.core.backup_manager.backup_manager._execute_pg_dump')
    def test_create_full_system_backup_pg_dump_failure(self, mock_pg_dump):
        """Test full system backup with pg_dump failure."""
        # Mock failed pg_dump
        mock_pg_dump.return_value = (False, "Database connection failed")
        
        result = self.backup_manager.create_full_system_backup()
        
        self.assertFalse(result['success'])
        self.assertIn('Database connection failed', result['error'])
        
        # Verify backup record was marked as failed
        backup_record = BackupRecord.objects.get(backup_id=result['backup_id'])
        self.assertEqual(backup_record.status, 'failed')
    
    @patch('zargar.core.backup_manager.backup_manager._execute_pg_dump')
    @patch('zargar.core.backup_manager.backup_manager._upload_backup_to_storage')
    def test_create_tenant_backup_success(self, mock_upload, mock_pg_dump):
        """Test successful tenant backup creation."""
        # Mock successful pg_dump
        mock_pg_dump.return_value = (True, "")
        
        # Mock successful upload
        mock_upload.return_value = (True, {
            'success': True,
            'uploaded_to': ['cloudflare_r2', 'backblaze_b2']
        })
        
        result = self.backup_manager.create_tenant_backup(
            tenant_schema=self.test_tenant_schema,
            tenant_domain=self.test_tenant_domain,
            frequency='manual',
            created_by='test_user'
        )
        
        self.assertTrue(result['success'])
        self.assertIn('backup_id', result)
        
        # Verify backup record was created with tenant information
        backup_record = BackupRecord.objects.get(backup_id=result['backup_id'])
        self.assertEqual(backup_record.backup_type, 'tenant_only')
        self.assertEqual(backup_record.tenant_schema, self.test_tenant_schema)
        self.assertEqual(backup_record.tenant_domain, self.test_tenant_domain)
    
    @patch('zargar.core.backup_manager.backup_manager.create_tenant_backup')
    def test_create_snapshot_backup(self, mock_tenant_backup):
        """Test snapshot backup creation."""
        mock_tenant_backup.return_value = {
            'success': True,
            'backup_id': 'snapshot_test_20241220_120000',
            'file_size': 1024,
            'file_hash': 'test_hash'
        }
        
        result = self.backup_manager.create_snapshot_backup(
            tenant_schema=self.test_tenant_schema,
            operation_description="Test data import",
            created_by='test_user'
        )
        
        self.assertTrue(result['success'])
    
    @patch('zargar.core.backup_manager.backup_manager.storage_manager')
    def test_verify_backup_integrity_success(self, mock_storage_manager):
        """Test successful backup integrity verification."""
        # Create test backup record
        test_content = b"Test backup content"
        test_hash = hashlib.sha256(test_content).hexdigest()
        
        backup_record = BackupRecord.objects.create(
            backup_id='test_backup_integrity',
            backup_type='full_system',
            file_path='test/path.sql.gz.enc',
            file_hash=test_hash,
            status='completed'
        )
        
        # Mock storage download
        mock_storage_manager.download_backup_file.return_value = test_content
        
        result = self.backup_manager.verify_backup_integrity('test_backup_integrity')
        
        self.assertTrue(result['success'])
        self.assertTrue(result['integrity_passed'])
        self.assertEqual(result['expected_hash'], test_hash)
        self.assertEqual(result['actual_hash'], test_hash)
        
        # Verify integrity check record was created
        integrity_check = BackupIntegrityCheck.objects.get(backup_record=backup_record)
        self.assertEqual(integrity_check.status, 'passed')
    
    @patch('zargar.core.backup_manager.backup_manager.storage_manager')
    def test_verify_backup_integrity_failure(self, mock_storage_manager):
        """Test backup integrity verification failure."""
        # Create test backup record
        original_content = b"Original backup content"
        corrupted_content = b"Corrupted backup content"
        original_hash = hashlib.sha256(original_content).hexdigest()
        
        backup_record = BackupRecord.objects.create(
            backup_id='test_backup_corrupted',
            backup_type='full_system',
            file_path='test/path.sql.gz.enc',
            file_hash=original_hash,
            status='completed'
        )
        
        # Mock storage download with corrupted content
        mock_storage_manager.download_backup_file.return_value = corrupted_content
        
        result = self.backup_manager.verify_backup_integrity('test_backup_corrupted')
        
        self.assertTrue(result['success'])
        self.assertFalse(result['integrity_passed'])
        self.assertEqual(result['expected_hash'], original_hash)
        self.assertNotEqual(result['actual_hash'], original_hash)
        
        # Verify backup was marked as corrupted
        backup_record.refresh_from_db()
        self.assertEqual(backup_record.status, 'corrupted')
    
    @patch('zargar.core.backup_manager.backup_manager.storage_manager')
    def test_cleanup_expired_backups(self, mock_storage_manager):
        """Test cleanup of expired backups."""
        # Create expired backup records
        expired_backup1 = BackupRecord.objects.create(
            backup_id='expired_backup_1',
            backup_type='full_system',
            file_path='expired/backup1.sql.gz.enc',
            status='completed',
            expires_at=timezone.now() - timedelta(days=1)
        )
        
        expired_backup2 = BackupRecord.objects.create(
            backup_id='expired_backup_2',
            backup_type='tenant_only',
            file_path='expired/backup2.sql.gz.enc',
            status='completed',
            expires_at=timezone.now() - timedelta(days=2)
        )
        
        # Create non-expired backup
        active_backup = BackupRecord.objects.create(
            backup_id='active_backup',
            backup_type='full_system',
            file_path='active/backup.sql.gz.enc',
            status='completed',
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        # Mock successful storage deletion
        mock_storage_manager.delete_backup_file.return_value = {'success': True}
        
        result = self.backup_manager.cleanup_expired_backups()
        
        self.assertEqual(result['total_expired'], 2)
        self.assertEqual(result['deleted_successfully'], 2)
        self.assertEqual(result['deletion_errors'], 0)
        
        # Verify expired backups were deleted
        self.assertFalse(BackupRecord.objects.filter(backup_id='expired_backup_1').exists())
        self.assertFalse(BackupRecord.objects.filter(backup_id='expired_backup_2').exists())
        
        # Verify active backup still exists
        self.assertTrue(BackupRecord.objects.filter(backup_id='active_backup').exists())
    
    def test_get_backup_statistics(self):
        """Test backup statistics generation."""
        # Create test backup records
        BackupRecord.objects.create(
            backup_id='stats_backup_1',
            backup_type='full_system',
            status='completed',
            file_size=1024000
        )
        
        BackupRecord.objects.create(
            backup_id='stats_backup_2',
            backup_type='tenant_only',
            status='completed',
            file_size=512000,
            stored_in_primary=True,
            stored_in_secondary=True
        )
        
        BackupRecord.objects.create(
            backup_id='stats_backup_3',
            backup_type='full_system',
            status='failed'
        )
        
        stats = self.backup_manager.get_backup_statistics()
        
        self.assertEqual(stats['total_backups'], 3)
        self.assertEqual(stats['completed_backups'], 2)
        self.assertEqual(stats['failed_backups'], 1)
        self.assertAlmostEqual(stats['success_rate'], 66.67, places=1)
        self.assertEqual(stats['total_storage_used'], 1536000)
        self.assertEqual(stats['redundant_backups'], 1)


class BackupModelsTestCase(TestCase):
    """Test cases for backup models."""
    
    def test_backup_record_creation(self):
        """Test BackupRecord model creation."""
        backup_record = BackupRecord.objects.create(
            backup_id='test_backup_model',
            backup_type='full_system',
            file_path='test/path.sql.gz.enc',
            is_encrypted=True
        )
        
        self.assertEqual(backup_record.backup_id, 'test_backup_model')
        self.assertEqual(backup_record.status, 'pending')
        self.assertTrue(backup_record.is_encrypted)
        self.assertIsNotNone(backup_record.created_at)
    
    def test_backup_record_mark_started(self):
        """Test marking backup as started."""
        backup_record = BackupRecord.objects.create(
            backup_id='test_started',
            backup_type='full_system',
            file_path='test/path.sql.gz.enc'
        )
        
        backup_record.mark_started()
        
        self.assertEqual(backup_record.status, 'in_progress')
        self.assertIsNotNone(backup_record.started_at)
    
    def test_backup_record_mark_completed(self):
        """Test marking backup as completed."""
        backup_record = BackupRecord.objects.create(
            backup_id='test_completed',
            backup_type='full_system',
            file_path='test/path.sql.gz.enc'
        )
        
        backup_record.mark_completed(file_size=1024, file_hash='test_hash')
        
        self.assertEqual(backup_record.status, 'completed')
        self.assertEqual(backup_record.file_size, 1024)
        self.assertEqual(backup_record.file_hash, 'test_hash')
        self.assertIsNotNone(backup_record.completed_at)
    
    def test_backup_record_mark_failed(self):
        """Test marking backup as failed."""
        backup_record = BackupRecord.objects.create(
            backup_id='test_failed',
            backup_type='full_system',
            file_path='test/path.sql.gz.enc'
        )
        
        backup_record.mark_failed('Test error message')
        
        self.assertEqual(backup_record.status, 'failed')
        self.assertEqual(backup_record.error_message, 'Test error message')
        self.assertIsNotNone(backup_record.completed_at)
    
    def test_backup_record_properties(self):
        """Test BackupRecord properties."""
        # Test duration calculation
        backup_record = BackupRecord.objects.create(
            backup_id='test_properties',
            backup_type='full_system',
            file_path='test/path.sql.gz.enc',
            started_at=timezone.now() - timedelta(minutes=30),
            completed_at=timezone.now()
        )
        
        duration = backup_record.duration
        self.assertIsNotNone(duration)
        self.assertGreater(duration.total_seconds(), 1700)  # Approximately 30 minutes
        
        # Test expiration
        backup_record.expires_at = timezone.now() - timedelta(days=1)
        self.assertTrue(backup_record.is_expired)
        
        # Test redundancy
        backup_record.stored_in_primary = True
        backup_record.stored_in_secondary = True
        self.assertTrue(backup_record.is_redundant)
    
    def test_backup_schedule_creation(self):
        """Test BackupSchedule model creation."""
        schedule = BackupSchedule.objects.create(
            name='Daily System Backup',
            schedule_type='full_system',
            frequency='daily',
            hour=3,
            minute=0,
            retention_days=30
        )
        
        self.assertEqual(schedule.name, 'Daily System Backup')
        self.assertEqual(schedule.frequency, 'daily')
        self.assertTrue(schedule.is_active)
        self.assertEqual(schedule.total_runs, 0)
    
    def test_backup_schedule_calculate_next_run(self):
        """Test next run calculation for backup schedules."""
        # Test daily schedule
        daily_schedule = BackupSchedule.objects.create(
            name='Daily Backup',
            schedule_type='full_system',
            frequency='daily',
            hour=3,
            minute=30
        )
        
        next_run = daily_schedule.calculate_next_run()
        self.assertIsNotNone(next_run)
        self.assertEqual(next_run.hour, 3)
        self.assertEqual(next_run.minute, 30)
        
        # Test weekly schedule
        weekly_schedule = BackupSchedule.objects.create(
            name='Weekly Backup',
            schedule_type='full_system',
            frequency='weekly',
            hour=2,
            minute=0,
            day_of_week=0  # Monday
        )
        
        next_run = weekly_schedule.calculate_next_run()
        self.assertIsNotNone(next_run)
        self.assertEqual(next_run.weekday(), 0)  # Monday
    
    def test_backup_schedule_record_run(self):
        """Test recording backup run execution."""
        schedule = BackupSchedule.objects.create(
            name='Test Schedule',
            schedule_type='full_system',
            frequency='daily',
            hour=3,
            minute=0
        )
        
        # Record successful run
        schedule.record_run(success=True, backup_id='test_backup_123')
        
        self.assertEqual(schedule.total_runs, 1)
        self.assertEqual(schedule.successful_runs, 1)
        self.assertEqual(schedule.failed_runs, 0)
        self.assertEqual(schedule.last_backup_id, 'test_backup_123')
        self.assertIsNotNone(schedule.last_run_at)
        self.assertIsNotNone(schedule.next_run_at)
        
        # Record failed run
        schedule.record_run(success=False)
        
        self.assertEqual(schedule.total_runs, 2)
        self.assertEqual(schedule.successful_runs, 1)
        self.assertEqual(schedule.failed_runs, 1)
    
    def test_backup_schedule_success_rate(self):
        """Test backup schedule success rate calculation."""
        schedule = BackupSchedule.objects.create(
            name='Test Schedule',
            schedule_type='full_system',
            frequency='daily',
            hour=3,
            minute=0
        )
        
        # No runs yet
        self.assertEqual(schedule.success_rate, 0)
        
        # Record some runs
        schedule.record_run(success=True)
        schedule.record_run(success=True)
        schedule.record_run(success=False)
        
        self.assertAlmostEqual(schedule.success_rate, 66.67, places=1)
    
    def test_backup_integrity_check_creation(self):
        """Test BackupIntegrityCheck model creation."""
        backup_record = BackupRecord.objects.create(
            backup_id='test_integrity_backup',
            backup_type='full_system',
            file_path='test/path.sql.gz.enc',
            file_hash='test_hash'
        )
        
        integrity_check = BackupIntegrityCheck.objects.create(
            backup_record=backup_record,
            expected_hash='test_hash'
        )
        
        self.assertEqual(integrity_check.backup_record, backup_record)
        self.assertEqual(integrity_check.status, 'pending')
        self.assertEqual(integrity_check.expected_hash, 'test_hash')
    
    def test_backup_integrity_check_mark_completed(self):
        """Test marking integrity check as completed."""
        backup_record = BackupRecord.objects.create(
            backup_id='test_integrity_completed',
            backup_type='full_system',
            file_path='test/path.sql.gz.enc'
        )
        
        integrity_check = BackupIntegrityCheck.objects.create(
            backup_record=backup_record
        )
        
        integrity_check.mark_completed(
            passed=True,
            actual_hash='calculated_hash',
            file_size=1024
        )
        
        self.assertEqual(integrity_check.status, 'passed')
        self.assertEqual(integrity_check.actual_hash, 'calculated_hash')
        self.assertEqual(integrity_check.file_size_verified, 1024)
        self.assertIsNotNone(integrity_check.completed_at)


class BackupTasksTestCase(TestCase):
    """Test cases for backup Celery tasks."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_tenant_schema = 'test_tenant_schema'
        
        # Create test tenant
        self.tenant = Tenant.objects.create(
            schema_name=self.test_tenant_schema,
            name='Test Tenant',
            domain_url='test.zargar.com'
        )
    
    @patch('zargar.core.backup_tasks.backup_manager')
    def test_create_daily_backup_task_success(self, mock_backup_manager):
        """Test successful daily backup task execution."""
        mock_backup_manager.create_full_system_backup.return_value = {
            'success': True,
            'backup_id': 'daily_backup_20241220_030000',
            'file_size': 1024000,
            'file_hash': 'test_hash'
        }
        
        result = create_daily_backup.apply().result
        
        self.assertTrue(result['success'])
        self.assertEqual(result['backup_id'], 'daily_backup_20241220_030000')
        self.assertIn('Daily backup completed successfully', result['message'])
    
    @patch('zargar.core.backup_tasks.backup_manager')
    def test_create_daily_backup_task_failure(self, mock_backup_manager):
        """Test failed daily backup task execution."""
        mock_backup_manager.create_full_system_backup.return_value = {
            'success': False,
            'error': 'Database connection failed',
            'backup_id': 'failed_backup_20241220_030000'
        }
        
        result = create_daily_backup.apply().result
        
        self.assertFalse(result['success'])
        self.assertIn('Database connection failed', result['error'])
    
    @patch('zargar.core.backup_tasks.backup_manager')
    def test_create_weekly_backup_task(self, mock_backup_manager):
        """Test weekly backup task execution."""
        mock_backup_manager.create_full_system_backup.return_value = {
            'success': True,
            'backup_id': 'weekly_backup_20241220_030000',
            'file_size': 2048000,
            'file_hash': 'weekly_hash'
        }
        
        result = create_weekly_backup.apply().result
        
        self.assertTrue(result['success'])
        self.assertEqual(result['backup_id'], 'weekly_backup_20241220_030000')
        
        # Verify extended retention was set
        backup_record = BackupRecord.objects.get(backup_id='weekly_backup_20241220_030000')
        self.assertIsNotNone(backup_record.expires_at)
    
    @patch('zargar.core.backup_tasks.backup_manager')
    def test_create_tenant_backup_task(self, mock_backup_manager):
        """Test tenant backup task execution."""
        mock_backup_manager.create_tenant_backup.return_value = {
            'success': True,
            'backup_id': 'tenant_backup_20241220_120000',
            'file_size': 512000,
            'file_hash': 'tenant_hash'
        }
        
        result = create_tenant_backup.apply(
            args=[self.test_tenant_schema, 'test.zargar.com', 'manual', 'test_user']
        ).result
        
        self.assertTrue(result['success'])
        self.assertEqual(result['tenant_schema'], self.test_tenant_schema)
        self.assertIn('Tenant backup completed successfully', result['message'])
    
    @patch('zargar.core.backup_tasks.backup_manager')
    def test_verify_backup_integrity_task(self, mock_backup_manager):
        """Test backup integrity verification task."""
        mock_backup_manager.verify_backup_integrity.return_value = {
            'success': True,
            'integrity_passed': True,
            'file_size': 1024,
            'expected_hash': 'expected_hash',
            'actual_hash': 'expected_hash'
        }
        
        result = verify_backup_integrity.apply(args=['test_backup_id']).result
        
        self.assertTrue(result['success'])
        self.assertTrue(result['integrity_passed'])
        self.assertIn('Backup integrity verification passed', result['message'])
    
    @patch('zargar.core.backup_tasks.backup_manager')
    def test_cleanup_old_backups_task(self, mock_backup_manager):
        """Test cleanup old backups task."""
        mock_backup_manager.cleanup_expired_backups.return_value = {
            'total_expired': 5,
            'deleted_successfully': 4,
            'deletion_errors': 1,
            'errors': ['Failed to delete backup_5']
        }
        
        result = cleanup_old_backups.apply().result
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_expired'], 5)
        self.assertEqual(result['deleted_successfully'], 4)
        self.assertEqual(result['deletion_errors'], 1)
    
    @patch('zargar.core.backup_tasks.backup_manager')
    def test_generate_backup_report_task(self, mock_backup_manager):
        """Test backup report generation task."""
        mock_backup_manager.get_backup_statistics.return_value = {
            'total_backups': 10,
            'completed_backups': 8,
            'failed_backups': 2,
            'success_rate': 80.0
        }
        
        # Create some test backup records for the report
        BackupRecord.objects.create(
            backup_id='report_backup_1',
            backup_type='full_system',
            status='completed',
            created_at=timezone.now() - timedelta(hours=12)
        )
        
        result = generate_backup_report.apply(args=['daily']).result
        
        self.assertTrue(result['success'])
        self.assertEqual(result['report_type'], 'daily')
        self.assertIn('report_data', result)
        self.assertIn('statistics', result['report_data'])


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True
)
class BackupIntegrationTestCase(TestCase):
    """Integration tests for the complete backup system."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_tenant_schema = 'integration_test_tenant'
        
        # Create test tenant
        self.tenant = Tenant.objects.create(
            schema_name=self.test_tenant_schema,
            name='Integration Test Tenant',
            domain_url='integration.zargar.com'
        )
    
    @patch('zargar.core.backup_manager.backup_manager._execute_pg_dump')
    @patch('zargar.core.backup_manager.backup_manager._upload_backup_to_storage')
    def test_full_backup_workflow(self, mock_upload, mock_pg_dump):
        """Test complete backup workflow from creation to verification."""
        # Mock successful pg_dump and upload
        mock_pg_dump.return_value = (True, "")
        mock_upload.return_value = (True, {
            'success': True,
            'uploaded_to': ['cloudflare_r2', 'backblaze_b2']
        })
        
        # Create backup
        result = backup_manager.create_full_system_backup(
            frequency='manual',
            created_by='integration_test'
        )
        
        self.assertTrue(result['success'])
        backup_id = result['backup_id']
        
        # Verify backup record exists
        backup_record = BackupRecord.objects.get(backup_id=backup_id)
        self.assertEqual(backup_record.status, 'completed')
        self.assertTrue(backup_record.stored_in_primary)
        self.assertTrue(backup_record.stored_in_secondary)
        
        # Test backup statistics
        stats = backup_manager.get_backup_statistics()
        self.assertGreater(stats['total_backups'], 0)
        self.assertGreater(stats['completed_backups'], 0)
    
    def test_backup_schedule_workflow(self):
        """Test backup schedule creation and management."""
        # Create backup schedule
        schedule = BackupSchedule.objects.create(
            name='Integration Test Schedule',
            description='Test schedule for integration testing',
            schedule_type='full_system',
            frequency='daily',
            hour=3,
            minute=30,
            retention_days=30,
            is_active=True
        )
        
        # Test next run calculation
        next_run = schedule.calculate_next_run()
        self.assertIsNotNone(next_run)
        self.assertEqual(next_run.hour, 3)
        self.assertEqual(next_run.minute, 30)
        
        # Update next run
        schedule.update_next_run()
        self.assertIsNotNone(schedule.next_run_at)
        
        # Record a run
        schedule.record_run(success=True, backup_id='test_backup_123')
        self.assertEqual(schedule.total_runs, 1)
        self.assertEqual(schedule.successful_runs, 1)
        self.assertEqual(schedule.success_rate, 100.0)
    
    def test_backup_retention_and_cleanup(self):
        """Test backup retention policy and cleanup."""
        # Create expired backup
        expired_backup = BackupRecord.objects.create(
            backup_id='expired_integration_backup',
            backup_type='full_system',
            file_path='expired/backup.sql.gz.enc',
            status='completed',
            expires_at=timezone.now() - timedelta(days=1)
        )
        
        # Create active backup
        active_backup = BackupRecord.objects.create(
            backup_id='active_integration_backup',
            backup_type='full_system',
            file_path='active/backup.sql.gz.enc',
            status='completed',
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        # Mock storage deletion
        with patch('zargar.core.backup_manager.backup_manager.storage_manager') as mock_storage:
            mock_storage.delete_backup_file.return_value = {'success': True}
            
            # Run cleanup
            result = backup_manager.cleanup_expired_backups()
            
            self.assertEqual(result['total_expired'], 1)
            self.assertEqual(result['deleted_successfully'], 1)
        
        # Verify expired backup was deleted
        self.assertFalse(BackupRecord.objects.filter(backup_id='expired_integration_backup').exists())
        
        # Verify active backup still exists
        self.assertTrue(BackupRecord.objects.filter(backup_id='active_integration_backup').exists())