"""
Simple frontend tests for tenant restoration UI workflow.
Tests the exact restoration UI workflow as specified in task 9.7.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing Django modules
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
import json
import uuid

from zargar.tenants.admin_models import SuperAdmin
from zargar.tenants.models import Tenant, Domain
from zargar.admin_panel.models import BackupJob, RestoreJob


User = get_user_model()


class TenantRestorationUISimpleTestCase(TestCase):
    """Simple test case for tenant restoration UI workflow."""
    
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
        
        # Create test tenant
        self.tenant = Tenant.objects.create(
            schema_name='test_tenant',
            name='Test Tenant',
            owner_name='Test Owner',
            owner_email='owner@test.com',
            is_active=True
        )
        
        # Create domain for tenant
        self.domain = Domain.objects.create(
            domain='test.example.com',
            tenant=self.tenant,
            is_primary=True
        )
        
        # Create test backup job
        self.backup = BackupJob.objects.create(
            name='Daily Backup - 2025-09-17-03:00',
            backup_type='full_system',
            status='completed',
            created_by_id=self.super_admin.id,
            created_by_username=self.super_admin.username,
            file_size_bytes=1024*1024*100,  # 100MB
            file_path='/backups/daily-2025-09-17.sql.gz'
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
        self.assertContains(response, self.backup.name)
        self.assertContains(response, 'Daily Backup - 2025-09-17-03:00')
    
    def test_backup_selection_interface(self):
        """Test backup selection interface functionality."""
        url = '/super-panel/backup/restore/'
        response = self.client.get(url)
        
        # Check that backup cards are present with correct data
        self.assertContains(response, f'selectBackup(\'{self.backup.job_id}\'')
        
        # Check backup details are displayed
        self.assertContains(response, 'پشتیبان کامل سیستم')
        
        # Check that backup cards have proper styling classes
        self.assertContains(response, 'backup-card')
        self.assertContains(response, 'selected')  # For selected state
    
    def test_restore_single_tenant_option(self):
        """Test "Restore a Single Tenant" option with dropdown."""
        url = '/super-panel/backup/restore/'
        response = self.client.get(url)
        
        # Check that restore button is present
        self.assertContains(response, 'بازیابی تک تنانت')
        self.assertContains(response, '@click="showRestoreModal = true"')
        self.assertContains(response, ':disabled="!selectedBackup"')
        
        # Check that tenant dropdown is present in modal
        self.assertContains(response, self.tenant.name)
        self.assertContains(response, self.domain.domain)
        
        # Check tenant selection functionality
        self.assertContains(response, f'selectTenant(\'{self.tenant.id}\'')
    
    def test_critical_confirmation_modal(self):
        """Test critical confirmation modal with exact warning message."""
        url = '/super-panel/backup/restore/'
        response = self.client.get(url)
        
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
    
    def test_progress_indicator_system(self):
        """Test progress indicator and monitoring system."""
        url = '/super-panel/backup/restore/'
        response = self.client.get(url)
        
        # Check that progress modal is present
        self.assertContains(response, 'showProgressModal')
        self.assertContains(response, 'در حال بازیابی تنانت')
        self.assertContains(response, 'progressPercentage')
        self.assertContains(response, 'progressMessage')
        
        # Check progress bar elements
        self.assertContains(response, 'progress-bar')
        self.assertContains(response, 'progress-fill')
        
        # Check progress monitoring function
        self.assertContains(response, 'monitorRestoreProgress()')
    
    def test_completion_notification_system(self):
        """Test completion notification system."""
        url = '/super-panel/backup/restore/'
        response = self.client.get(url)
        
        # Check completion modal elements
        self.assertContains(response, 'showCompletionModal')
        self.assertContains(response, 'restoreSuccess')
        self.assertContains(response, 'completionMessage')
        
        # Check success and failure states
        self.assertContains(response, 'بازیابی موفقیت‌آمیز')
        self.assertContains(response, 'بازیابی ناموفق')
        
        # Check completion handler
        self.assertContains(response, 'closeCompletionModal()')
        self.assertContains(response, 'window.location.reload()')
    
    def test_javascript_functionality(self):
        """Test JavaScript functionality and Alpine.js integration."""
        url = '/super-panel/backup/restore/'
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
    
    def test_persian_rtl_layout(self):
        """Test Persian RTL layout and localization."""
        url = '/super-panel/backup/restore/'
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
    
    def test_ui_workflow_matches_requirements(self):
        """Test that UI workflow exactly matches task 9.7 requirements."""
        url = '/super-panel/backup/restore/'
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