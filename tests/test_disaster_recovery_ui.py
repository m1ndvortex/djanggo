"""
Tests for disaster recovery UI functionality.

This module tests the disaster recovery dashboard, documentation viewer,
and testing interface components.

Requirements: 5.11, 5.12
"""
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from zargar.tenants.admin_models import SuperAdmin
from zargar.admin_panel.models import BackupJob, RestoreJob
from zargar.admin_panel.disaster_recovery import DisasterRecoveryManager


User = get_user_model()


class DisasterRecoveryDashboardUITest(TestCase):
    """Test disaster recovery dashboard UI functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
        
        # Create test backup jobs
        self.full_backup = BackupJob.objects.create(
            name='Test Full Backup',
            backup_type='full_system',
            status='completed',
            created_by_id=self.super_admin.id,
            created_by_username=self.super_admin.username,
            file_size_bytes=1024*1024*100,  # 100MB
            progress_percentage=100
        )
        
        self.config_backup = BackupJob.objects.create(
            name='Test Config Backup',
            backup_type='configuration',
            status='completed',
            created_by_id=self.super_admin.id,
            created_by_username=self.super_admin.username,
            file_size_bytes=1024*50,  # 50KB
            progress_percentage=100
        )
        
        # Create test restore job
        self.restore_job = RestoreJob.objects.create(
            restore_type='single_tenant',
            source_backup=self.full_backup,
            target_tenant_schema='test_tenant',
            created_by_id=self.super_admin.id,
            created_by_username=self.super_admin.username,
            status='completed'
        )
    
    def test_disaster_recovery_dashboard_access_requires_super_admin(self):
        """Test that disaster recovery dashboard requires super admin access."""
        # Test unauthenticated access
        response = self.client.get(reverse('admin_panel:disaster_recovery_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Test regular user access (would need to create regular user in tenant schema)
        # For now, just test super admin access
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_panel:disaster_recovery_dashboard'))
        self.assertEqual(response.status_code, 200)
    
    @patch('zargar.admin_panel.views.DisasterRecoveryManager')
    def test_disaster_recovery_dashboard_context_data(self, mock_dr_manager):
        """Test that dashboard loads with correct context data."""
        # Mock disaster recovery manager
        mock_instance = MagicMock()
        mock_dr_manager.return_value = mock_instance
        
        mock_recovery_plan = {
            'disaster_recovery_plan': {
                'version': '1.0',
                'created_at': timezone.now().isoformat(),
                'overview': {
                    'philosophy': 'Test philosophy',
                    'recovery_time_objective': '4 hours',
                    'recovery_point_objective': '24 hours'
                },
                'recovery_procedures': {},
                'validation_steps': {},
                'rollback_procedures': {},
                'emergency_contacts': {}
            }
        }
        mock_instance.create_disaster_recovery_plan.return_value = mock_recovery_plan
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_panel:disaster_recovery_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('recovery_plan', response.context)
        self.assertIn('system_status', response.context)
        self.assertIn('available_backups', response.context)
        self.assertIn('recovery_metrics', response.context)
        
        # Check that backups are included
        available_backups = response.context['available_backups']
        self.assertIn(self.full_backup, available_backups)
    
    def test_disaster_recovery_dashboard_template_rendering(self):
        """Test that dashboard template renders correctly."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_panel:disaster_recovery_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'داشبورد بازیابی فاجعه')
        self.assertContains(response, 'وضعیت کلی')
        self.assertContains(response, 'نرخ موفقیت پشتیبان')
        self.assertContains(response, 'مراحل بازیابی فاجعه')
        self.assertContains(response, 'تست کامل بازیابی')
    
    def test_disaster_recovery_dashboard_system_status_calculation(self):
        """Test system readiness status calculation."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_panel:disaster_recovery_dashboard'))
        
        system_status = response.context['system_status']
        
        # Should be ready since we have recent backups
        self.assertEqual(system_status['overall_status'], 'ready')
        self.assertTrue(system_status['recent_full_backup'])
        self.assertTrue(system_status['recent_config_backup'])
        self.assertEqual(system_status['estimated_rto'], '4 hours')
        self.assertEqual(system_status['estimated_rpo'], '24 hours')
    
    def test_disaster_recovery_dashboard_metrics_calculation(self):
        """Test recovery metrics calculation."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_panel:disaster_recovery_dashboard'))
        
        recovery_metrics = response.context['recovery_metrics']
        
        # Should have 100% success rate since all our test backups are completed
        self.assertEqual(recovery_metrics['backup_success_rate'], 100.0)
        self.assertEqual(recovery_metrics['restore_success_rate'], 100.0)
    
    def test_disaster_recovery_dashboard_theme_support(self):
        """Test that dashboard supports both light and dark themes."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_panel:disaster_recovery_dashboard'))
        
        # Check for cybersecurity theme CSS classes
        self.assertContains(response, 'cyber-glow')
        self.assertContains(response, 'dr-card')
        self.assertContains(response, 'dark:bg-cyber-bg-primary')


class DisasterRecoveryTestUITest(TestCase):
    """Test disaster recovery testing interface."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
    
    def test_disaster_recovery_test_post_requires_super_admin(self):
        """Test that DR test endpoint requires super admin access."""
        response = self.client.post(reverse('admin_panel:disaster_recovery_test'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    @patch('zargar.admin_panel.views.DisasterRecoveryManager')
    def test_disaster_recovery_full_procedures_test(self, mock_dr_manager):
        """Test running full disaster recovery procedures test."""
        mock_instance = MagicMock()
        mock_dr_manager.return_value = mock_instance
        
        mock_test_results = {
            'overall_status': 'success',
            'test_type': 'full_procedures',
            'duration': '45 minutes',
            'components_tested': ['database', 'configuration', 'services'],
            'issues_found': 0
        }
        mock_instance.test_disaster_recovery_procedures.return_value = mock_test_results
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(
            reverse('admin_panel:disaster_recovery_test'),
            {'test_type': 'full_procedures'}
        )
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        mock_instance.test_disaster_recovery_procedures.assert_called_once()
    
    def test_disaster_recovery_backup_validation_test(self):
        """Test running backup validation test."""
        # Create a test backup
        backup = BackupJob.objects.create(
            name='Test Backup for Validation',
            backup_type='full_system',
            status='completed',
            created_by_id=self.super_admin.id,
            created_by_username=self.super_admin.username
        )
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(
            reverse('admin_panel:disaster_recovery_test'),
            {'test_type': 'backup_validation'}
        )
        
        self.assertEqual(response.status_code, 302)  # Redirect after test
    
    @patch('zargar.core.storage_utils.storage_manager')
    def test_disaster_recovery_storage_connectivity_test(self, mock_storage):
        """Test running storage connectivity test."""
        mock_storage.get_storage_status.return_value = {
            'overall_status': 'healthy',
            'configuration': {
                'cloudflare_r2': {'configured': True, 'connected': True},
                'backblaze_b2': {'configured': True, 'connected': True}
            }
        }
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(
            reverse('admin_panel:disaster_recovery_test'),
            {'test_type': 'storage_connectivity'}
        )
        
        self.assertEqual(response.status_code, 302)  # Redirect after test
    
    def test_disaster_recovery_test_invalid_type(self):
        """Test handling of invalid test type."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(
            reverse('admin_panel:disaster_recovery_test'),
            {'test_type': 'invalid_test'}
        )
        
        self.assertEqual(response.status_code, 302)  # Redirect with error message
    
    def test_disaster_recovery_test_missing_type(self):
        """Test handling of missing test type."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(
            reverse('admin_panel:disaster_recovery_test'),
            {}  # No test_type provided
        )
        
        self.assertEqual(response.status_code, 302)  # Redirect with error message


class DisasterRecoveryDocumentationUITest(TestCase):
    """Test disaster recovery documentation viewer."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
    
    def test_disaster_recovery_documentation_access_requires_super_admin(self):
        """Test that documentation requires super admin access."""
        response = self.client.get(reverse('admin_panel:disaster_recovery_documentation'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_panel:disaster_recovery_documentation'))
        self.assertEqual(response.status_code, 200)
    
    @patch('zargar.admin_panel.views.DisasterRecoveryManager')
    def test_disaster_recovery_documentation_content(self, mock_dr_manager):
        """Test that documentation loads with complete recovery plan."""
        mock_instance = MagicMock()
        mock_dr_manager.return_value = mock_instance
        
        mock_recovery_plan = {
            'disaster_recovery_plan': {
                'version': '1.0',
                'created_at': timezone.now().isoformat(),
                'overview': {
                    'philosophy': 'Separation of Data, Configuration, and Code',
                    'components': {
                        'data': 'Complete PostgreSQL database dumps',
                        'configuration': 'Environment files, Docker configs',
                        'code': 'Git repository'
                    },
                    'recovery_time_objective': '4 hours',
                    'recovery_point_objective': '24 hours'
                },
                'prerequisites': {
                    'server_requirements': {
                        'cpu': '4-8 cores minimum',
                        'memory': '16-32GB RAM minimum',
                        'storage': '500GB+ SSD storage'
                    },
                    'software_requirements': [
                        'Docker Engine 20.10+',
                        'Docker Compose 2.0+',
                        'Git 2.30+'
                    ],
                    'access_requirements': [
                        'Cloudflare R2 access credentials',
                        'Git repository access'
                    ]
                },
                'recovery_procedures': {
                    'phase_1_server_preparation': {
                        'description': 'Prepare new server environment',
                        'estimated_time': '30 minutes',
                        'steps': [
                            {
                                'step': 1,
                                'title': 'Server Setup',
                                'description': 'Set up new server',
                                'commands': ['sudo apt update'],
                                'validation': 'System updated'
                            }
                        ]
                    }
                },
                'validation_steps': {
                    'database_validation': {
                        'description': 'Validate database restoration',
                        'checks': ['Database connectivity', 'Data integrity']
                    }
                },
                'rollback_procedures': {
                    'rollback_1': {
                        'title': 'Database Rollback',
                        'description': 'Rollback database changes',
                        'steps': ['Stop services', 'Restore previous backup']
                    }
                },
                'emergency_contacts': {
                    'technical_lead': {
                        'role': 'Technical Lead',
                        'name': 'Test User',
                        'phone': '+98-21-12345678',
                        'email': 'tech@test.com',
                        'availability': '24/7'
                    }
                }
            }
        }
        mock_instance.create_disaster_recovery_plan.return_value = mock_recovery_plan
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_panel:disaster_recovery_documentation'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('recovery_plan', response.context)
        self.assertEqual(response.context['plan_version'], '1.0')
    
    def test_disaster_recovery_documentation_template_rendering(self):
        """Test that documentation template renders correctly."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_panel:disaster_recovery_documentation'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مستندات بازیابی فاجعه')
        self.assertContains(response, 'فهرست مطالب')
        self.assertContains(response, 'نگاه کلی')
        self.assertContains(response, 'پیش‌نیازها')
        self.assertContains(response, 'مراحل بازیابی فاجعه')
        self.assertContains(response, 'چاپ مستندات')
    
    def test_disaster_recovery_documentation_print_friendly(self):
        """Test that documentation includes print-friendly elements."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_panel:disaster_recovery_documentation'))
        
        # Check for print-friendly CSS classes
        self.assertContains(response, 'print-friendly')
        self.assertContains(response, 'no-print')
        
        # Check for print-specific content
        self.assertContains(response, 'سیستم مدیریت زرگر')
    
    def test_disaster_recovery_documentation_table_of_contents(self):
        """Test that documentation includes functional table of contents."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_panel:disaster_recovery_documentation'))
        
        # Check for TOC links
        self.assertContains(response, 'href="#overview"')
        self.assertContains(response, 'href="#prerequisites"')
        self.assertContains(response, 'href="#procedures"')
        self.assertContains(response, 'href="#validation"')
        self.assertContains(response, 'href="#rollback"')
        self.assertContains(response, 'href="#contacts"')
    
    def test_disaster_recovery_documentation_command_blocks(self):
        """Test that documentation properly displays command blocks."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_panel:disaster_recovery_documentation'))
        
        # Check for command block styling
        self.assertContains(response, 'command-block')
        self.assertContains(response, 'font-family: \'Courier New\'')
    
    def test_disaster_recovery_documentation_cybersecurity_theme(self):
        """Test that documentation supports cybersecurity theme."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_panel:disaster_recovery_documentation'))
        
        # Check for cybersecurity theme CSS
        self.assertContains(response, 'doc-section')
        self.assertContains(response, '[data-theme="dark"]')
        self.assertContains(response, '#00D4FF')  # Cybersecurity neon color


class DisasterRecoveryUIIntegrationTest(TestCase):
    """Integration tests for disaster recovery UI components."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
    
    def test_disaster_recovery_navigation_flow(self):
        """Test navigation between disaster recovery pages."""
        self.client.login(username='admin', password='testpass123')
        
        # Start at dashboard
        response = self.client.get(reverse('admin_panel:disaster_recovery_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Navigate to documentation
        response = self.client.get(reverse('admin_panel:disaster_recovery_documentation'))
        self.assertEqual(response.status_code, 200)
        
        # Check that documentation has link back to dashboard
        self.assertContains(response, reverse('admin_panel:disaster_recovery_dashboard'))
    
    def test_disaster_recovery_dashboard_quick_actions(self):
        """Test quick action buttons on dashboard."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_panel:disaster_recovery_dashboard'))
        
        # Check for quick action buttons
        self.assertContains(response, 'تست اعتبار پشتیبان')
        self.assertContains(response, 'تست اتصال ذخیره‌سازی')
        self.assertContains(response, 'مدیریت پشتیبان‌گیری')
        
        # Check that backup management link is present
        self.assertContains(response, reverse('admin_panel:backup_management'))
    
    def test_disaster_recovery_dashboard_status_monitoring(self):
        """Test real-time status monitoring interface."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_panel:disaster_recovery_dashboard'))
        
        # Check for status indicators
        self.assertContains(response, 'status-indicator')
        self.assertContains(response, 'وضعیت کلی')
        self.assertContains(response, 'اتصال ذخیره‌سازی')
        self.assertContains(response, 'پشتیبان کامل اخیر')
    
    @patch('zargar.admin_panel.views.DisasterRecoveryManager')
    def test_disaster_recovery_test_results_display(self, mock_dr_manager):
        """Test that test results are properly displayed."""
        # Create mock test results
        mock_instance = MagicMock()
        mock_dr_manager.return_value = mock_instance
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_panel:disaster_recovery_dashboard'))
        
        # Check for test results section
        self.assertContains(response, 'نتایج تست‌های اخیر')
        self.assertContains(response, 'test-result-badge')
    
    def test_disaster_recovery_responsive_design(self):
        """Test that UI is responsive and mobile-friendly."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_panel:disaster_recovery_dashboard'))
        
        # Check for responsive grid classes
        self.assertContains(response, 'grid-cols-1')
        self.assertContains(response, 'lg:grid-cols-3')
        self.assertContains(response, 'md:grid-cols-2')
        
        # Check for mobile-friendly navigation
        self.assertContains(response, 'lg:col-span-2')
    
    def test_disaster_recovery_accessibility_features(self):
        """Test accessibility features in disaster recovery UI."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_panel:disaster_recovery_dashboard'))
        
        # Check for proper heading structure
        self.assertContains(response, '<h1')
        self.assertContains(response, '<h2')
        self.assertContains(response, '<h3')
        
        # Check for ARIA labels and semantic HTML
        self.assertContains(response, 'role=')
        self.assertContains(response, 'aria-')
        
        # Check for keyboard navigation support
        self.assertContains(response, 'tabindex')


class DisasterRecoveryUIPerformanceTest(TestCase):
    """Performance tests for disaster recovery UI."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
        
        # Create multiple backup jobs for performance testing
        for i in range(50):
            BackupJob.objects.create(
                name=f'Test Backup {i}',
                backup_type='full_system',
                status='completed',
                created_by_id=self.super_admin.id,
                created_by_username=self.super_admin.username
            )
    
    def test_disaster_recovery_dashboard_load_time(self):
        """Test that dashboard loads efficiently with many backups."""
        self.client.login(username='admin', password='testpass123')
        
        import time
        start_time = time.time()
        response = self.client.get(reverse('admin_panel:disaster_recovery_dashboard'))
        load_time = time.time() - start_time
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(load_time, 2.0)  # Should load within 2 seconds
    
    def test_disaster_recovery_documentation_load_time(self):
        """Test that documentation loads efficiently."""
        self.client.login(username='admin', password='testpass123')
        
        import time
        start_time = time.time()
        response = self.client.get(reverse('admin_panel:disaster_recovery_documentation'))
        load_time = time.time() - start_time
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(load_time, 1.0)  # Should load within 1 second
    
    def test_disaster_recovery_dashboard_query_efficiency(self):
        """Test that dashboard uses efficient database queries."""
        self.client.login(username='admin', password='testpass123')
        
        with self.assertNumQueries(10):  # Should use reasonable number of queries
            response = self.client.get(reverse('admin_panel:disaster_recovery_dashboard'))
            self.assertEqual(response.status_code, 200)