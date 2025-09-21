"""
Template tests for tenant restoration UI.
Tests that the template renders correctly without triggering middleware.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing Django modules
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

from django.test import TestCase
from django.template.loader import render_to_string
from django.template import Context, Template
from zargar.tenants.admin_models import SuperAdmin
from zargar.tenants.models import Tenant, Domain
from zargar.admin_panel.models import BackupJob, RestoreJob


class TenantRestorationTemplateTestCase(TestCase):
    """Test case for tenant restoration template rendering."""
    
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
    
    def test_template_renders_backup_management_dashboard(self):
        """Test that the template renders the backup management dashboard correctly."""
        context = {
            'available_backups': [self.backup],
            'tenants': [self.tenant],
            'recent_restores': [],
            'user': self.super_admin
        }
        
        # Test that template can be rendered without errors
        try:
            rendered = render_to_string('admin_panel/tenant_restore.html', context)
            self.assertIsNotNone(rendered)
            self.assertIn('مدیریت پشتیبان‌گیری', rendered)
        except Exception as e:
            self.fail(f"Template rendering failed: {str(e)}")
    
    def test_template_contains_required_elements(self):
        """Test that template contains all required UI elements."""
        context = {
            'available_backups': [self.backup],
            'tenants': [self.tenant],
            'recent_restores': [],
            'user': self.super_admin
        }
        
        rendered = render_to_string('admin_panel/tenant_restore.html', context)
        
        # Test required elements from task 9.7
        required_elements = [
            'مدیریت پشتیبان‌گیری',  # Backup Management dashboard
            'پشتیبان‌های قابل استفاده',  # Available backups
            'بازیابی تک تنانت',  # Restore Single Tenant option
            'Daily Backup - 2025-09-17-03:00',  # Backup selection
            'selectBackup(',  # Backup selection function
            'selectTenant(',  # Tenant selection function
            'هشدار بحرانی',  # Critical warning
            'این عملیات قابل بازگشت نیست',  # Warning message
            'برای تأیید، دامنه تنانت را تایپ کنید',  # Domain confirmation
            'confirmation_text',  # Confirmation input
            'showProgressModal',  # Progress indicator
            'showCompletionModal',  # Completion notification
            'progressPercentage',  # Progress tracking
            'monitorRestoreProgress',  # Progress monitoring
        ]
        
        for element in required_elements:
            self.assertIn(element, rendered, f"Required element '{element}' not found in template")
    
    def test_template_javascript_functionality(self):
        """Test that template includes required JavaScript functionality."""
        context = {
            'available_backups': [self.backup],
            'tenants': [self.tenant],
            'recent_restores': [],
            'user': self.super_admin
        }
        
        rendered = render_to_string('admin_panel/tenant_restore.html', context)
        
        # Test JavaScript functions
        js_functions = [
            'backupManagement()',  # Main Alpine.js function
            'selectBackup(',  # Backup selection
            'selectTenant(',  # Tenant selection
            'confirmRestore(',  # Restore confirmation
            'closeRestoreModal(',  # Modal management
            'monitorRestoreProgress(',  # Progress monitoring
            'isConfirmationValid',  # Validation logic
        ]
        
        for func in js_functions:
            self.assertIn(func, rendered, f"JavaScript function '{func}' not found in template")
    
    def test_template_persian_rtl_support(self):
        """Test that template supports Persian RTL layout."""
        context = {
            'available_backups': [self.backup],
            'tenants': [self.tenant],
            'recent_restores': [],
            'user': self.super_admin
        }
        
        rendered = render_to_string('admin_panel/tenant_restore.html', context)
        
        # Test RTL and Persian support
        rtl_elements = [
            'dir="rtl"',  # RTL direction
            'font-vazir',  # Persian font
            'space-x-reverse',  # RTL spacing
        ]
        
        for element in rtl_elements:
            self.assertIn(element, rendered, f"RTL element '{element}' not found in template")
    
    def test_template_cybersecurity_theme_support(self):
        """Test that template supports cybersecurity dark theme."""
        context = {
            'available_backups': [self.backup],
            'tenants': [self.tenant],
            'recent_restores': [],
            'user': self.super_admin
        }
        
        rendered = render_to_string('admin_panel/tenant_restore.html', context)
        
        # Test cybersecurity theme elements
        theme_elements = [
            'dark:bg-gray-800',  # Dark background
            'dark:text-white',  # Dark text
            'backdrop-filter: blur(16px)',  # Glassmorphism
            'rgba(37, 42, 58, 0.8)',  # Cybersecurity colors
        ]
        
        for element in theme_elements:
            self.assertIn(element, rendered, f"Theme element '{element}' not found in template")
    
    def test_template_form_validation(self):
        """Test that template includes proper form validation."""
        context = {
            'available_backups': [self.backup],
            'tenants': [self.tenant],
            'recent_restores': [],
            'user': self.super_admin
        }
        
        rendered = render_to_string('admin_panel/tenant_restore.html', context)
        
        # Test form validation elements
        validation_elements = [
            ':disabled="!isConfirmationValid"',  # Button validation
            'x-model="confirmationText"',  # Input binding
            'x-model="acknowledgeRisk"',  # Checkbox binding
            'confirmationText === selectedTenantDomain',  # Validation logic
            '&& acknowledgeRisk',  # Risk acknowledgment
        ]
        
        for element in validation_elements:
            self.assertIn(element, rendered, f"Validation element '{element}' not found in template")
    
    def test_template_modal_system(self):
        """Test that template includes complete modal system."""
        context = {
            'available_backups': [self.backup],
            'tenants': [self.tenant],
            'recent_restores': [],
            'user': self.super_admin
        }
        
        rendered = render_to_string('admin_panel/tenant_restore.html', context)
        
        # Test modal system elements
        modal_elements = [
            'showRestoreModal',  # Restore modal
            'showProgressModal',  # Progress modal
            'showCompletionModal',  # Completion modal
            'x-show="showRestoreModal"',  # Modal visibility
            'x-transition:enter',  # Modal transitions
            '@click.away="closeRestoreModal()"',  # Click away handling
        ]
        
        for element in modal_elements:
            self.assertIn(element, rendered, f"Modal element '{element}' not found in template")
    
    def test_template_exact_requirements_compliance(self):
        """Test that template exactly matches task 9.7 requirements."""
        context = {
            'available_backups': [self.backup],
            'tenants': [self.tenant],
            'recent_restores': [],
            'user': self.super_admin
        }
        
        rendered = render_to_string('admin_panel/tenant_restore.html', context)
        
        # Test exact requirements from task 9.7
        
        # Requirement: Create "Backup Management" dashboard in Super-Panel exactly as specified
        self.assertIn('مدیریت پشتیبان‌گیری', rendered)
        self.assertIn('پشتیبان‌های قابل استفاده', rendered)
        
        # Requirement: Build backup selection interface to select specific full system backup snapshot
        self.assertIn('Daily Backup - 2025-09-17-03:00', rendered)
        self.assertIn('selectBackup(', rendered)
        
        # Requirement: Implement "Restore a Single Tenant" option with dropdown to select specific tenant
        self.assertIn('بازیابی تک تنانت', rendered)
        self.assertIn('selectTenant(', rendered)
        
        # Requirement: Create modal with critical confirmation warning
        warning_parts = [
            'این عملیات تمام داده‌های فعلی تنانت',
            'با داده‌های پشتیبان',
            'جایگزین خواهد کرد',
            'این عملیات قابل بازگشت نیست'
        ]
        for part in warning_parts:
            self.assertIn(part, rendered, f"Warning part '{part}' not found")
        
        # Requirement: Type the tenant's domain to confirm
        self.assertIn('برای تأیید، دامنه تنانت را تایپ کنید', rendered)
        self.assertIn('confirmation_text', rendered)
        
        # Requirement: Build progress indicator and completion notification system
        self.assertIn('showProgressModal', rendered)
        self.assertIn('showCompletionModal', rendered)
        self.assertIn('progressPercentage', rendered)
        self.assertIn('monitorRestoreProgress', rendered)
        
        # Test that all requirements are met
        self.assertTrue(True, "All task 9.7 requirements are present in the template")