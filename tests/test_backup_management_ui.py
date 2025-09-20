#!/usr/bin/env python
"""
Test backup management UI functionality.
"""
import os
import sys
import django
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.base')
django.setup()

from zargar.tenants.admin_models import SuperAdmin
from zargar.admin_panel.models import BackupJob, BackupSchedule


class BackupManagementUITest(TestCase):
    """Test backup management UI functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create superadmin user
        self.superadmin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        
        # Create test backup job
        self.backup_job = BackupJob.objects.create(
            name='Test Backup',
            backup_type='full_system',
            status='completed',
            progress_percentage=100,
            created_by_id=self.superadmin.id,
            created_by_username=self.superadmin.username
        )
        
        # Create test backup schedule
        self.backup_schedule = BackupSchedule.objects.create(
            name='Daily Backup',
            backup_type='full_system',
            frequency='daily',
            scheduled_time='03:00:00',
            is_active=True,
            created_by_id=self.superadmin.id,
            created_by_username=self.superadmin.username
        )
        
        self.client = Client()
    
    def test_backup_management_dashboard_access(self):
        """Test access to backup management dashboard."""
        # Login as superadmin
        self.client.login(username='admin', password='testpass123')
        
        # Access backup management dashboard
        response = self.client.get(reverse('admin_panel:backup_management'))
        
        # Should be accessible
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مدیریت پشتیبان‌گیری')
        self.assertContains(response, 'Test Backup')
    
    def test_backup_history_page(self):
        """Test backup history page."""
        # Login as superadmin
        self.client.login(username='admin', password='testpass123')
        
        # Access backup history
        response = self.client.get(reverse('admin_panel:backup_history'))
        
        # Should be accessible and show backup
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تاریخچه پشتیبان‌گیری')
        self.assertContains(response, 'Test Backup')
    
    def test_backup_schedule_page(self):
        """Test backup schedule page."""
        # Login as superadmin
        self.client.login(username='admin', password='testpass123')
        
        # Access backup schedule
        response = self.client.get(reverse('admin_panel:backup_schedule'))
        
        # Should be accessible and show schedule
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'زمان‌بندی پشتیبان‌گیری')
        self.assertContains(response, 'Daily Backup')
    
    def test_tenant_restore_page(self):
        """Test tenant restore page."""
        # Login as superadmin
        self.client.login(username='admin', password='testpass123')
        
        # Access tenant restore
        response = self.client.get(reverse('admin_panel:tenant_restore'))
        
        # Should be accessible
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'بازیابی تنانت')
    
    def test_backup_job_detail_page(self):
        """Test backup job detail page."""
        # Login as superadmin
        self.client.login(username='admin', password='testpass123')
        
        # Access backup job detail
        response = self.client.get(
            reverse('admin_panel:backup_job_detail', kwargs={'job_id': self.backup_job.job_id})
        )
        
        # Should be accessible and show job details
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'جزئیات پشتیبان‌گیری')
        self.assertContains(response, 'Test Backup')
    
    def test_create_backup_job(self):
        """Test creating a new backup job."""
        # Login as superadmin
        self.client.login(username='admin', password='testpass123')
        
        # Create backup job
        response = self.client.post(reverse('admin_panel:create_backup'), {
            'backup_name': 'New Test Backup',
            'backup_type': 'database_only'
        })
        
        # Should redirect and create backup job
        self.assertEqual(response.status_code, 302)
        
        # Check if backup job was created
        backup_exists = BackupJob.objects.filter(
            name='New Test Backup',
            backup_type='database_only'
        ).exists()
        self.assertTrue(backup_exists)
    
    def test_create_backup_schedule(self):
        """Test creating a new backup schedule."""
        # Login as superadmin
        self.client.login(username='admin', password='testpass123')
        
        # Create backup schedule
        response = self.client.post(reverse('admin_panel:backup_schedule'), {
            'name': 'Weekly Backup',
            'backup_type': 'full_system',
            'frequency': 'weekly',
            'scheduled_time': '02:00',
            'is_active': 'on',
            'retention_days': '30'
        })
        
        # Should redirect and create schedule
        self.assertEqual(response.status_code, 302)
        
        # Check if schedule was created
        schedule_exists = BackupSchedule.objects.filter(
            name='Weekly Backup',
            frequency='weekly'
        ).exists()
        self.assertTrue(schedule_exists)
    
    def test_backup_status_api(self):
        """Test backup status API endpoint."""
        # Login as superadmin
        self.client.login(username='admin', password='testpass123')
        
        # Get backup status
        response = self.client.get(
            reverse('admin_panel:backup_status_api'),
            {'job_id': str(self.backup_job.job_id)}
        )
        
        # Should return JSON with status
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Parse JSON response
        import json
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'completed')
        self.assertEqual(data['progress'], 100)
    
    def test_unauthorized_access(self):
        """Test that unauthorized users cannot access backup management."""
        # Try to access without login
        response = self.client.get('/super-panel/backup/')
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)


def main():
    """Run the tests."""
    print("🧪 Testing Backup Management UI")
    print("=" * 50)
    
    # Run tests
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=True)
    
    # Run specific test
    failures = test_runner.run_tests(['tests.test_backup_management_ui'])
    
    if failures:
        print(f"\n❌ {failures} test(s) failed")
        return False
    else:
        print("\n✅ All backup management UI tests passed!")
        return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(1)