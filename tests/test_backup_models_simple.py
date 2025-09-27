#!/usr/bin/env python
"""
Simple test for backup models functionality.
"""
import os
import sys
import django
from django.test import TestCase

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.base')
django.setup()

from zargar.admin_panel.models import BackupJob, BackupSchedule, RestoreJob


class BackupModelsTest(TestCase):
    """Test backup models functionality."""
    
    def test_backup_job_creation(self):
        """Test creating a backup job."""
        backup_job = BackupJob.objects.create(
            name='Test Backup',
            backup_type='full_system',
            frequency='manual',
            status='pending',
            created_by_id=1,
            created_by_username='admin'
        )
        
        self.assertEqual(backup_job.name, 'Test Backup')
        self.assertEqual(backup_job.backup_type, 'full_system')
        self.assertEqual(backup_job.status, 'pending')
        self.assertEqual(backup_job.progress_percentage, 0)
        self.assertFalse(backup_job.is_running)
        self.assertFalse(backup_job.is_completed)
    
    def test_backup_job_progress_update(self):
        """Test updating backup job progress."""
        backup_job = BackupJob.objects.create(
            name='Test Backup',
            backup_type='database_only',
            status='running',
            created_by_id=1,
            created_by_username='admin'
        )
        
        # Update progress
        backup_job.update_progress(50, 'Halfway done')
        
        self.assertEqual(backup_job.progress_percentage, 50)
        self.assertEqual(len(backup_job.log_messages), 1)
        self.assertEqual(backup_job.log_messages[0]['level'], 'info')
        self.assertEqual(backup_job.log_messages[0]['message'], 'Halfway done')
    
    def test_backup_job_completion(self):
        """Test marking backup job as completed."""
        backup_job = BackupJob.objects.create(
            name='Test Backup',
            backup_type='configuration',
            status='running',
            created_by_id=1,
            created_by_username='admin'
        )
        
        # Mark as completed
        backup_job.mark_as_completed(
            file_path='backups/test_backup.sql',
            file_size_bytes=1024000,
            storage_backends=['cloudflare_r2', 'backblaze_b2']
        )
        
        self.assertEqual(backup_job.status, 'completed')
        self.assertEqual(backup_job.progress_percentage, 100)
        self.assertEqual(backup_job.file_path, 'backups/test_backup.sql')
        self.assertEqual(backup_job.file_size_bytes, 1024000)
        self.assertEqual(backup_job.storage_backends, ['cloudflare_r2', 'backblaze_b2'])
        self.assertTrue(backup_job.is_completed)
    
    def test_backup_job_failure(self):
        """Test marking backup job as failed."""
        backup_job = BackupJob.objects.create(
            name='Test Backup',
            backup_type='tenant_only',
            status='running',
            created_by_id=1,
            created_by_username='admin'
        )
        
        # Mark as failed
        backup_job.mark_as_failed('Database connection failed')
        
        self.assertEqual(backup_job.status, 'failed')
        self.assertEqual(backup_job.error_message, 'Database connection failed')
        self.assertTrue(backup_job.is_failed)
    
    def test_backup_schedule_creation(self):
        """Test creating a backup schedule."""
        schedule = BackupSchedule.objects.create(
            name='Daily Backup',
            backup_type='full_system',
            frequency='daily',
            scheduled_time='03:00:00',
            is_active=True,
            retention_days=30,
            max_backups=10,
            created_by_id=1,
            created_by_username='admin'
        )
        
        self.assertEqual(schedule.name, 'Daily Backup')
        self.assertEqual(schedule.frequency, 'daily')
        self.assertTrue(schedule.is_active)
        self.assertEqual(schedule.retention_days, 30)
        self.assertEqual(schedule.max_backups, 10)
    
    def test_restore_job_creation(self):
        """Test creating a restore job."""
        # First create a backup job
        backup_job = BackupJob.objects.create(
            name='Source Backup',
            backup_type='full_system',
            status='completed',
            created_by_id=1,
            created_by_username='admin'
        )
        
        # Create restore job
        restore_job = RestoreJob.objects.create(
            restore_type='single_tenant',
            source_backup=backup_job,
            target_tenant_schema='test_tenant',
            status='pending',
            created_by_id=1,
            created_by_username='admin'
        )
        
        self.assertEqual(restore_job.restore_type, 'single_tenant')
        self.assertEqual(restore_job.source_backup, backup_job)
        self.assertEqual(restore_job.target_tenant_schema, 'test_tenant')
        self.assertEqual(restore_job.status, 'pending')
    
    def test_backup_job_string_representation(self):
        """Test backup job string representation."""
        backup_job = BackupJob.objects.create(
            name='Test Backup',
            backup_type='full_system',
            status='completed',
            created_by_id=1,
            created_by_username='admin'
        )
        
        expected_str = 'Test Backup (Completed)'
        self.assertEqual(str(backup_job), expected_str)
    
    def test_backup_schedule_string_representation(self):
        """Test backup schedule string representation."""
        schedule = BackupSchedule.objects.create(
            name='Weekly Backup',
            backup_type='database_only',
            frequency='weekly',
            scheduled_time='02:00:00',
            created_by_id=1,
            created_by_username='admin'
        )
        
        expected_str = 'Weekly Backup (Weekly)'
        self.assertEqual(str(schedule), expected_str)


def main():
    """Run the tests."""
    print("🧪 Testing Backup Models")
    print("=" * 50)
    
    # Run tests
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=True)
    
    # Run specific test
    failures = test_runner.run_tests(['tests.test_backup_models_simple'])
    
    if failures:
        print(f"\n❌ {failures} test(s) failed")
        return False
    else:
        print("\n✅ All backup model tests passed!")
        return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(1)