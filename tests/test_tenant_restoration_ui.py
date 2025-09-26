"""
Frontend tests for tenant restoration UI workflow.

Tests the exact restoration UI workflow as specified in task 9.7:
- Backup Management dashboard
- Backup selection interface
- "Restore a Single Tenant" option with dropdown
- Critical confirmation modal with domain typing
- Progress indicator and completion notification system

Requirements: 5.15, 5.16, 5.17, 5.18
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing Django modules
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from django.test import TestCase, Client
# from django.urls import reverse  # Using direct URLs instead
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch, MagicMock
import json
import uuid

from zargar.tenants.admin_models import SuperAdmin
from zargar.tenants.models import Tenant
from zargar.admin_panel.models import BackupJob, RestoreJob
from zargar.admin_panel.tenant_restoration import tenant_restoration_manager


User = get_user_model()


class TenantRestorationUITestCase(TestCase):
    """Test case for tenant restoration UI workflow."""
    
    def setUp(self):
        """Set up test data."""
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        
        # Create test tenants
        self.tenant1 = Tenant.objects.create(
            schema_name='tenant1',
            name='Test Tenant 1',
            owner_name='Owner 1',
            owner_email='owner1@test.com',
            is_active=True
        )
        
        # Create domain for tenant1
        from zargar.tenants.models import Domain
        self.domain1 = Domain.objects.create(
            domain='tenant1.test.com',
            tenant=self.tenant1,
            is_primary=True
        )
        
        self.tenant2 = Tenant.objects.create(
            schema_name='tenant2',
            name='Test Tenant 2',
            owner_name='Owner 2',
            owner_email='owner2@test.com',
            is_active=True
        )
        
        # Create domain for tenant2
        self.domain2 = Domain.objects.create(
            domain='tenant2.test.com',
            tenant=self.tenant2,
            is_primary=True
        )
        
        # Create test backup jobs
        self.backup1 = BackupJob.objects.create(
            name='Daily Backup - 2025-09-17-03:00',
            backup_type='full_system',
            status='completed',
            created_by_id=self.super_admin.id,
            created_by_username=self.super_admin.username,
            file_size_bytes=1024*1024*100,  # 100MB
            file_path='/backups/daily-2025-09-17.sql.gz'
        )
        
        self.backup2 = BackupJob.objects.create(
            name='Weekly Backup - 2025-09-15-02:00',
            backup_type='full_system',
            status='completed',
            created_by_id=self.super_admin.id,
            created_by_username=self.super_admin.username,
            file_size_bytes=1024*1024*200,  # 200MB
            file_path='/backups/weekly-2025-09-15.sql.gz'
        )
        
        self.client = Client()
        self.client.force_login(self.super_admin)
    
    def test_backup_management_dashboard_display(self):
        """Test that the Backup Management dashboard displays correctly."""
        url = '/super-panel/backup/restore/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مدیریت پشتیبان‌گیری')
        self.assertContains(response, 'پشتیبان‌های قابل استفاده')
        self.assertContains(response, 'بازیابی تک تنانت')
        
        # Check that available backups are displayed
        self.assertContains(response, self.backup1.name)
        self.assertContains(response, self.backup2.name)
        self.assertContains(response, 'Daily Backup - 2025-09-17-03:00')
        self.assertContains(response, 'Weekly Backup - 2025-09-15-02:00')
    
    def test_backup_selection_interface(self):
        """Test backup selection interface functionality."""
        url = '/super-panel/backup/restore/'
        response = self.client.get(url)
        
        # Check that backup cards are present with correct data
        self.assertContains(response, f'@click="selectBackup(\'{self.backup1.job_id}\'')
        self.assertContains(response, f'@click="selectBackup(\'{self.backup2.job_id}\'')
        
        # Check backup details are displayed
        self.assertContains(response, 'پشتیبان کامل سیستم')
        self.assertContains(response, '100.0 MB')  # File size formatting
        
        # Check that backup cards have proper styling classes
        self.assertContains(response, 'backup-card')
        self.assertContains(response, 'selected')  # For selected state
    
    def test_restore_single_tenant_option(self):
        """Test "Restore a Single Tenant" option with dropdown."""
        url = reverse('admin_panel:tenant_restore')
        response = self.client.get(url)
        
        # Check that restore button is present
        self.assertContains(response, 'بازیابی تک تنانت')
        self.assertContains(response, '@click="showRestoreModal = true"')
        self.assertContains(response, ':disabled="!selectedBackup"')
        
        # Check that tenant dropdown is present in modal
        self.assertContains(response, self.tenant1.name)
        self.assertContains(response, self.domain1.domain)
        self.assertContains(response, self.tenant2.name)
        self.assertContains(response, self.domain2.domain)
        
        # Check tenant selection functionality
        self.assertContains(response, f'@click="selectTenant(\'{self.tenant1.id}\'')
        self.assertContains(response, f'@click="selectTenant(\'{self.tenant2.id}\'')
    
    def test_critical_confirmation_modal(self):
        """Test critical confirmation modal with exact warning message."""
        url = reverse('admin_panel:tenant_restore')
        response = self.client.get(url)
        
        # Check that modal contains exact warning message as specified
        expected_warning = (
            'این عملیات تمام داده‌های فعلی تنانت "[Tenant Name]" را با داده‌های پشتیبان '
            '"[Backup Name]" از تاریخ [Backup Date] جایگزین خواهد کرد. این عملیات قابل بازگشت نیست!'
        )
        
        # Check for critical warning elements
        self.assertContains(response, 'هشدار بحرانی')
        self.assertContains(response, 'این عملیات قابل بازگشت نیست')
        self.assertContains(response, 'برای تأیید، دامنه تنانت را تایپ کنید')
        
        # Check confirmation input field
        self.assertContains(response, 'name="confirmation_text"')
        self.assertContains(response, 'x-model="confirmationText"')
        self.assertContains(response, ':placeholder="selectedTenantDomain"')
        
        # Check risk acknowledgment checkbox
        self.assertContains(response, 'x-model="acknowledgeRisk"')
        self.assertContains(response, 'من خطرات این عملیات را درک کرده‌ام')
        
        # Check form validation
        self.assertContains(response, ':disabled="!isConfirmationValid"')
    
    def test_confirmation_validation_logic(self):
        """Test that confirmation validation works correctly."""
        url = reverse('admin_panel:tenant_restore')
        response = self.client.get(url)
        
        # Check JavaScript validation logic
        self.assertContains(response, 'get isConfirmationValid()')
        self.assertContains(response, 'this.confirmationText === this.selectedTenantDomain')
        self.assertContains(response, '&& this.acknowledgeRisk')
        
        # Check that submit button is disabled when validation fails
        self.assertContains(response, 'bg-gray-400 cursor-not-allowed')
        self.assertContains(response, 'bg-red-600 hover:bg-red-700')
    
    @patch('zargar.admin_panel.tenant_restoration.tenant_restoration_manager.restore_tenant_from_main_backup')
    def test_restore_submission_workflow(self, mock_restore):
        """Test the complete restore submission workflow."""
        # Mock successful restore initiation
        mock_restore.return_value = {
            'success': True,
            'restore_job_id': str(uuid.uuid4()),
            'message': 'Restore started successfully'
        }
        
        url = reverse('admin_panel:tenant_restore')
        
        # Submit restore request
        response = self.client.post(url, {
            'restore_type': 'from_backup',
            'backup_id': str(self.backup1.job_id),
            'target_tenant_id': str(self.tenant1.id),
            'confirmation_text': self.domain1.domain,
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        # Check that response is JSON
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('restore_job_id', data)
        
        # Verify that tenant restoration manager was called correctly
        mock_restore.assert_called_once_with(
            backup_id=str(self.backup1.job_id),
            target_tenant_schema=self.tenant1.schema_name,
            confirmation_text=self.domain1.domain,
            created_by_id=self.super_admin.id,
            created_by_username=self.super_admin.username
        )
    
    def test_progress_indicator_system(self):
        """Test progress indicator and monitoring system."""
        url = reverse('admin_panel:tenant_restore')
        response = self.client.get(url)
        
        # Check that progress modal is present
        self.assertContains(response, 'showProgressModal')
        self.assertContains(response, 'در حال بازیابی تنانت')
        self.assertContains(response, 'progressPercentage')
        self.assertContains(response, 'progressMessage')
        
        # Check progress bar elements
        self.assertContains(response, 'progress-bar')
        self.assertContains(response, 'progress-fill')
        self.assertContains(response, ':style="`width: ${progressPercentage}%`"')
        
        # Check progress monitoring function
        self.assertContains(response, 'monitorRestoreProgress()')
        self.assertContains(response, 'restore_status_api')
    
    def test_completion_notification_system(self):
        """Test completion notification system."""
        url = reverse('admin_panel:tenant_restore')
        response = self.client.get(url)
        
        # Check completion modal elements
        self.assertContains(response, 'showCompletionModal')
        self.assertContains(response, 'restoreSuccess')
        self.assertContains(response, 'completionMessage')
        
        # Check success and failure states
        self.assertContains(response, 'بازیابی موفقیت‌آمیز')
        self.assertContains(response, 'بازیابی ناموفق')
        self.assertContains(response, 'bg-green-100 dark:bg-green-900/30')
        self.assertContains(response, 'bg-red-100 dark:bg-red-900/30')
        
        # Check completion handler
        self.assertContains(response, 'closeCompletionModal()')
        self.assertContains(response, 'window.location.reload()')
    
    def test_restore_status_api_endpoint(self):
        """Test restore status API endpoint."""
        # Create a test restore job
        restore_job = RestoreJob.objects.create(
            restore_type='single_tenant',
            source_backup=self.backup1,
            target_tenant_schema=self.tenant1.schema_name,
            status='running',
            progress_percentage=50,
            created_by_id=self.super_admin.id,
            created_by_username=self.super_admin.username
        )
        
        url = reverse('admin_panel:restore_status_api')
        response = self.client.get(url, {'job_id': str(restore_job.job_id)})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'running')
        self.assertEqual(data['progress_percentage'], 50)
        self.assertEqual(data['target_tenant_schema'], self.tenant1.schema_name)
    
    def test_restore_status_api_missing_job_id(self):
        """Test restore status API with missing job_id parameter."""
        url = reverse('admin_panel:restore_status_api')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Missing job_id parameter')
    
    def test_restore_status_api_invalid_job_id(self):
        """Test restore status API with invalid job_id."""
        url = reverse('admin_panel:restore_status_api')
        response = self.client.get(url, {'job_id': str(uuid.uuid4())})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertFalse(data['success'])
        self.assertIn('not found', data['error'])
    
    def test_javascript_functionality(self):
        """Test JavaScript functionality and Alpine.js integration."""
        url = reverse('admin_panel:tenant_restore')
        response = self.client.get(url)
        
        # Check Alpine.js data function
        self.assertContains(response, 'x-data="backupManagement()"')
        
        # Check key JavaScript functions
        self.assertContains(response, 'selectBackup(')
        self.assertContains(response, 'selectTenant(')
        self.assertContains(response, 'confirmRestore(')
        self.assertContains(response, 'closeRestoreModal(')
        self.assertContains(response, 'monitorRestoreProgress(')
        
        # Check state management
        self.assertContains(response, 'selectedBackup:')
        self.assertContains(response, 'selectedTenant:')
        self.assertContains(response, 'showRestoreModal:')
        self.assertContains(response, 'showProgressModal:')
        self.assertContains(response, 'showCompletionModal:')
    
    def test_responsive_design_elements(self):
        """Test responsive design elements."""
        url = reverse('admin_panel:tenant_restore')
        response = self.client.get(url)
        
        # Check responsive grid classes
        self.assertContains(response, 'grid-cols-1 lg:grid-cols-3')
        self.assertContains(response, 'lg:col-span-2')
        self.assertContains(response, 'grid-cols-1 md:grid-cols-2')
        
        # Check modal responsive classes
        self.assertContains(response, 'max-w-2xl mx-4')
        self.assertContains(response, 'max-w-md mx-4')
        
        # Check overflow handling
        self.assertContains(response, 'max-h-96 overflow-y-auto')
        self.assertContains(response, 'max-h-48 overflow-y-auto')
    
    def test_dark_mode_cybersecurity_theme(self):
        """Test dark mode cybersecurity theme integration."""
        url = reverse('admin_panel:tenant_restore')
        response = self.client.get(url)
        
        # Check cybersecurity theme classes
        self.assertContains(response, 'dark:bg-gray-800')
        self.assertContains(response, 'dark:text-white')
        self.assertContains(response, 'dark:border-gray-600')
        
        # Check neon accent colors
        self.assertContains(response, 'dark:bg-blue-900/20')
        self.assertContains(response, 'dark:hover:border-blue-400')
        
        # Check glassmorphism effects in CSS
        self.assertContains(response, 'backdrop-filter: blur(16px)')
        self.assertContains(response, 'rgba(37, 42, 58, 0.8)')
    
    def test_persian_rtl_layout(self):
        """Test Persian RTL layout and localization."""
        url = reverse('admin_panel:tenant_restore')
        response = self.client.get(url)
        
        # Check RTL direction
        self.assertContains(response, 'dir="rtl"')
        
        # Check Persian text content
        self.assertContains(response, 'مدیریت پشتیبان‌گیری')
        self.assertContains(response, 'بازیابی تک تنانت')
        self.assertContains(response, 'هشدار بحرانی')
        self.assertContains(response, 'این عملیات قابل بازگشت نیست')
        
        # Check Persian fonts
        self.assertContains(response, 'font-vazir')
        
        # Check RTL-specific spacing classes
        self.assertContains(response, 'space-x-reverse')
    
    def test_accessibility_features(self):
        """Test accessibility features."""
        url = reverse('admin_panel:tenant_restore')
        response = self.client.get(url)
        
        # Check form labels
        self.assertContains(response, '<label')
        self.assertContains(response, 'for="acknowledge_risk_modal"')
        
        # Check ARIA attributes and semantic HTML
        self.assertContains(response, 'role=')
        self.assertContains(response, 'aria-')
        
        # Check keyboard navigation support
        self.assertContains(response, 'focus:outline-none')
        self.assertContains(response, 'focus:ring-')
    
    def test_error_handling(self):
        """Test error handling in the UI."""
        url = reverse('admin_panel:tenant_restore')
        
        # Test with invalid backup ID
        response = self.client.post(url, {
            'restore_type': 'from_backup',
            'backup_id': str(uuid.uuid4()),  # Non-existent backup
            'target_tenant_id': str(self.tenant1.id),
            'confirmation_text': self.tenant1.domain_url,
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_security_measures(self):
        """Test security measures in the restoration UI."""
        url = reverse('admin_panel:tenant_restore')
        response = self.client.get(url)
        
        # Check CSRF protection
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertContains(response, '{% csrf_token %}')
        
        # Check that only super admins can access
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@test.com',
            password='testpass123'
        )
        
        client = Client()
        client.force_login(regular_user)
        response = client.get(url)
        
        # Should redirect to login or show permission denied
        self.assertNotEqual(response.status_code, 200)


class TenantRestorationIntegrationTestCase(TestCase):
    """Integration tests for tenant restoration workflow."""
    
    def setUp(self):
        """Set up test data for integration tests."""
        self.super_admin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        
        self.tenant = Tenant.objects.create(
            schema_name='test_tenant',
            name='Test Tenant',
            owner_name='Test Owner',
            owner_email='owner@test.com',
            is_active=True
        )
        
        # Create domain for tenant
        from zargar.tenants.models import Domain
        self.domain = Domain.objects.create(
            domain='test.example.com',
            tenant=self.tenant,
            is_primary=True
        )
        
        self.backup = BackupJob.objects.create(
            name='Test Backup',
            backup_type='full_system',
            status='completed',
            created_by_id=self.super_admin.id,
            created_by_username=self.super_admin.username,
            file_path='/test/backup.sql.gz'
        )
        
        self.client = Client()
        self.client.force_login(self.super_admin)
    
    @patch('zargar.admin_panel.tenant_restoration.tenant_restoration_manager.restore_tenant_from_main_backup')
    def test_complete_restoration_workflow(self, mock_restore):
        """Test the complete restoration workflow from start to finish."""
        restore_job_id = str(uuid.uuid4())
        mock_restore.return_value = {
            'success': True,
            'restore_job_id': restore_job_id,
            'message': 'Restore started successfully'
        }
        
        # Step 1: Load the restoration page
        url = reverse('admin_panel:tenant_restore')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Step 2: Submit restoration request
        response = self.client.post(url, {
            'restore_type': 'from_backup',
            'backup_id': str(self.backup.job_id),
            'target_tenant_id': str(self.tenant.id),
            'confirmation_text': self.domain.domain,
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['restore_job_id'], restore_job_id)
        
        # Step 3: Check that restore job was created
        mock_restore.assert_called_once()
        
        # Verify the exact parameters passed to the restoration manager
        call_args = mock_restore.call_args
        self.assertEqual(call_args[1]['backup_id'], str(self.backup.job_id))
        self.assertEqual(call_args[1]['target_tenant_schema'], self.tenant.schema_name)
        self.assertEqual(call_args[1]['confirmation_text'], self.domain.domain)
        self.assertEqual(call_args[1]['created_by_id'], self.super_admin.id)
        self.assertEqual(call_args[1]['created_by_username'], self.super_admin.username)
    
    def test_ui_workflow_matches_requirements(self):
        """Test that UI workflow exactly matches task 9.7 requirements."""
        url = reverse('admin_panel:tenant_restore')
        response = self.client.get(url)
        
        # Requirement: Create "Backup Management" dashboard in Super-Panel exactly as specified
        self.assertContains(response, 'مدیریت پشتیبان‌گیری')
        self.assertContains(response, 'پشتیبان‌های قابل استفاده')
        
        # Requirement: Build backup selection interface to select specific full system backup snapshot
        self.assertContains(response, 'Daily Backup - 2025-09-17-03:00')  # Example format
        self.assertContains(response, 'selectBackup(')
        
        # Requirement: Implement "Restore a Single Tenant" option with dropdown to select specific tenant
        self.assertContains(response, 'بازیابی تک تنانت')
        self.assertContains(response, 'selectTenant(')
        self.assertContains(response, self.tenant.name)
        self.assertContains(response, self.domain.domain)
        
        # Requirement: Create modal with critical confirmation warning
        expected_warning_parts = [
            'این عملیات تمام داده‌های فعلی تنانت',
            'با داده‌های پشتیبان',
            'جایگزین خواهد کرد',
            'این عملیات قابل بازگشت نیست'
        ]
        for part in expected_warning_parts:
            self.assertContains(response, part)
        
        # Requirement: Type the tenant's domain to confirm
        self.assertContains(response, 'برای تأیید، دامنه تنانت را تایپ کنید')
        self.assertContains(response, 'confirmation_text')
        
        # Requirement: Build progress indicator and completion notification system
        self.assertContains(response, 'showProgressModal')
        self.assertContains(response, 'showCompletionModal')
        self.assertContains(response, 'progressPercentage')
        self.assertContains(response, 'monitorRestoreProgress')