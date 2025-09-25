"""
Tests for notification management frontend functionality.
Tests email configuration, alert settings, delivery status, and UI navigation.
"""
import json
import pytest
import django
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch, MagicMock

# Setup Django before importing models
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
django.setup()

from zargar.tenants.admin_models import SuperAdmin
from zargar.admin_panel.models import SystemSetting, NotificationSetting
from zargar.admin_panel.services.notification_service import (
    EmailServerConfiguration,
    AlertThresholdManager,
    NotificationDeliveryService
)

User = get_user_model()


class NotificationManagementFrontendTestCase(TestCase):
    """Test notification management frontend functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_active=True
        )
        
        # Login as super admin
        self.client.force_login(self.super_admin)
        
        # Create test system settings
        self.email_settings = [
            SystemSetting.objects.create(
                key='email_host',
                value='smtp.test.com',
                setting_type='string',
                category='notifications',
                section='email_server'
            ),
            SystemSetting.objects.create(
                key='email_port',
                value='587',
                setting_type='integer',
                category='notifications',
                section='email_server'
            ),
            SystemSetting.objects.create(
                key='email_username',
                value='test@test.com',
                setting_type='string',
                category='notifications',
                section='email_server'
            ),
        ]
        
        # Create test notification settings
        self.notification_setting = NotificationSetting.objects.create(
            name='Test Security Alert',
            event_type='security_event',
            notification_type='email',
            is_enabled=True,
            recipients=['admin@test.com'],
            priority_threshold='medium'
        )
    
    def test_notification_management_view_loads(self):
        """Test that the notification management view loads correctly."""
        url = reverse('admin_panel:notifications_management')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مدیریت اعلان‌ها')
        self.assertContains(response, 'تنظیمات ایمیل')
        self.assertContains(response, 'تنظیمات هشدار')
        self.assertContains(response, 'وضعیت تحویل')
    
    def test_notification_management_view_context(self):
        """Test that the notification management view has correct context."""
        url = reverse('admin_panel:notifications_management')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('email_config', response.context)
        self.assertIn('alert_thresholds', response.context)
        self.assertIn('notification_recipients', response.context)
        self.assertIn('delivery_stats', response.context)
    
    def test_notification_management_breadcrumb_navigation(self):
        """Test that breadcrumb navigation is correct."""
        url = reverse('admin_panel:notifications_management')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'پنل مدیریت')
        self.assertContains(response, 'تنظیمات')
        self.assertContains(response, 'مدیریت اعلان‌ها')
    
    def test_notification_management_theme_support(self):
        """Test that the interface supports dual themes."""
        url = reverse('admin_panel:notifications_management')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for dark theme classes
        self.assertContains(response, 'dark:bg-cyber-bg-primary')
        self.assertContains(response, 'dark:text-cyber-text-primary')
        self.assertContains(response, 'dark:border-cyber-neon-primary')
        # Check for glassmorphism effects
        self.assertContains(response, 'glassmorphism')
        self.assertContains(response, 'cyber-glow')
    
    def test_notification_management_persian_rtl_layout(self):
        """Test that the interface supports Persian RTL layout."""
        url = reverse('admin_panel:notifications_management')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for RTL classes
        self.assertContains(response, 'rtl:space-x-reverse')
        self.assertContains(response, 'text-right')
        # Check for Persian text
        self.assertContains(response, 'تنظیمات ایمیل')
        self.assertContains(response, 'هشدارهای امنیتی')
        self.assertContains(response, 'آستانه ورود ناموفق')


class EmailConfigurationAPITestCase(TestCase):
    """Test email configuration API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_active=True
        )
        
        # Login as super admin
        self.client.force_login(self.super_admin)
    
    def test_get_email_configuration(self):
        """Test getting current email configuration."""
        url = reverse('admin_panel:api_email_config')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('config', data)
        self.assertIn('status', data)
    
    @patch('zargar.admin_panel.services.notification_service.EmailServerConfiguration.update_email_config')
    def test_update_email_configuration(self, mock_update):
        """Test updating email configuration."""
        mock_update.return_value = {
            'success': True,
            'updated_settings': [],
            'errors': {},
            'test_result': {'success': True}
        }
        
        url = reverse('admin_panel:api_email_config')
        data = {
            'host': 'smtp.gmail.com',
            'port': 587,
            'username': 'test@gmail.com',
            'password': 'testpass',
            'use_tls': True,
            'from_email': 'noreply@test.com'
        }
        
        response = self.client.post(
            url,
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('message', response_data)
        mock_update.assert_called_once()
    
    @patch('zargar.admin_panel.services.notification_service.EmailServerConfiguration.test_connection')
    def test_email_connection_test(self, mock_test):
        """Test email server connection testing."""
        mock_test.return_value = {
            'success': True,
            'error': None,
            'details': {'connection_status': 'success'},
            'timestamp': timezone.now().isoformat()
        }
        
        url = reverse('admin_panel:api_email_test')
        data = {
            'config': {
                'host': 'smtp.test.com',
                'port': 587,
                'username': 'test@test.com',
                'password': 'testpass'
            }
        }
        
        response = self.client.post(
            url,
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('result', response_data)
        mock_test.assert_called_once()
    
    @patch('zargar.admin_panel.services.notification_service.EmailServerConfiguration.send_test_email')
    def test_send_test_email(self, mock_send):
        """Test sending test email."""
        mock_send.return_value = {
            'success': True,
            'error': None,
            'recipient': 'test@test.com',
            'timestamp': timezone.now().isoformat()
        }
        
        url = reverse('admin_panel:api_send_test_email')
        data = {
            'recipient': 'test@test.com',
            'config': {
                'host': 'smtp.test.com',
                'port': 587
            }
        }
        
        response = self.client.post(
            url,
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('message', response_data)
        mock_send.assert_called_once()


class AlertConfigurationAPITestCase(TestCase):
    """Test alert configuration API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_active=True
        )
        
        # Login as super admin
        self.client.force_login(self.super_admin)
    
    def test_get_alert_configuration(self):
        """Test getting current alert configuration."""
        url = reverse('admin_panel:api_alert_config')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('thresholds', data)
        self.assertIn('recipients', data)
    
    @patch('zargar.admin_panel.services.notification_service.AlertThresholdManager.update_alert_thresholds')
    @patch('zargar.admin_panel.services.notification_service.AlertThresholdManager.update_notification_recipients')
    def test_update_alert_configuration(self, mock_update_recipients, mock_update_thresholds):
        """Test updating alert configuration."""
        mock_update_thresholds.return_value = {
            'success': True,
            'updated_settings': [],
            'errors': {}
        }
        mock_update_recipients.return_value = {
            'success': True,
            'updated_settings': [],
            'errors': {}
        }
        
        url = reverse('admin_panel:api_alert_config')
        data = {
            'thresholds': {
                'security_events': {
                    'failed_login_threshold': 10,
                    'suspicious_activity_threshold': 5
                }
            },
            'recipients': {
                'security_alerts': ['admin@test.com', 'security@test.com']
            }
        }
        
        response = self.client.post(
            url,
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        mock_update_thresholds.assert_called_once()
        mock_update_recipients.assert_called_once()


class DeliveryStatisticsAPITestCase(TestCase):
    """Test delivery statistics API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_active=True
        )
        
        # Login as super admin
        self.client.force_login(self.super_admin)
    
    @patch('zargar.admin_panel.services.notification_service.NotificationDeliveryService.get_delivery_statistics')
    def test_get_delivery_statistics(self, mock_get_stats):
        """Test getting delivery statistics."""
        mock_get_stats.return_value = {
            'total_sent': 100,
            'total_failed': 5,
            'pending': 2,
            'success_rate': 95.0
        }
        
        url = reverse('admin_panel:api_delivery_stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('stats', data)
        self.assertEqual(data['stats']['total_sent'], 100)
        self.assertEqual(data['stats']['success_rate'], 95.0)
        mock_get_stats.assert_called_once()
    
    def test_get_delivery_statistics_with_days_parameter(self):
        """Test getting delivery statistics with custom days parameter."""
        url = reverse('admin_panel:api_delivery_stats')
        response = self.client.get(url, {'days': 7})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])


class NotificationTestAPITestCase(TestCase):
    """Test notification testing API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_active=True
        )
        
        # Login as super admin
        self.client.force_login(self.super_admin)
    
    @patch('zargar.admin_panel.services.notification_service.NotificationDeliveryService.send_notification')
    def test_notification_test(self, mock_send):
        """Test notification delivery testing."""
        mock_send.return_value = {
            'success': True,
            'notifications_sent': 1,
            'notifications_failed': 0,
            'delivery_results': [],
            'errors': []
        }
        
        url = reverse('admin_panel:api_notification_test')
        data = {
            'event_type': 'test_event',
            'priority': 'high',
            'event_data': {
                'test_message': 'This is a test notification'
            }
        }
        
        response = self.client.post(
            url,
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('message', response_data)
        mock_send.assert_called_once()


class NotificationManagementUINavigationTestCase(TestCase):
    """Test UI navigation and accessibility."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_active=True
        )
        
        # Login as super admin
        self.client.force_login(self.super_admin)
    
    def test_navigation_from_settings_menu(self):
        """Test navigation from Settings → Notifications."""
        # First check that the settings page has the notification link
        settings_url = reverse('admin_panel:settings_management')
        settings_response = self.client.get(settings_url)
        self.assertEqual(settings_response.status_code, 200)
        
        # Check that notification management is accessible
        notifications_url = reverse('admin_panel:notifications_management')
        notifications_response = self.client.get(notifications_url)
        self.assertEqual(notifications_response.status_code, 200)
        self.assertContains(notifications_response, 'مدیریت اعلان‌ها')
    
    def test_navigation_breadcrumbs(self):
        """Test that breadcrumb navigation works correctly."""
        url = reverse('admin_panel:notifications_management')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check breadcrumb structure
        self.assertContains(response, 'پنل مدیریت')
        self.assertContains(response, 'تنظیمات')
        self.assertContains(response, 'مدیریت اعلان‌ها')
        
        # Check that breadcrumb links are present
        self.assertContains(response, reverse('admin_panel:dashboard'))
        self.assertContains(response, reverse('admin_panel:settings_management'))
    
    def test_tab_navigation_functionality(self):
        """Test that tab navigation is properly implemented."""
        url = reverse('admin_panel:notifications_management')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for tab buttons
        self.assertContains(response, 'تنظیمات ایمیل')
        self.assertContains(response, 'تنظیمات هشدار')
        self.assertContains(response, 'وضعیت تحویل')
        
        # Check for Alpine.js tab functionality
        self.assertContains(response, 'activeTab')
        self.assertContains(response, 'x-show="activeTab === \'email\'"')
        self.assertContains(response, 'x-show="activeTab === \'alerts\'"')
        self.assertContains(response, 'x-show="activeTab === \'status\'"')
    
    def test_mobile_responsiveness_classes(self):
        """Test that mobile responsive classes are present."""
        url = reverse('admin_panel:notifications_management')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for responsive grid classes
        self.assertContains(response, 'grid-cols-1')
        self.assertContains(response, 'md:grid-cols-2')
        self.assertContains(response, 'lg:grid-cols-2')
        
        # Check for responsive spacing
        self.assertContains(response, 'px-4')
        self.assertContains(response, 'sm:px-6')
        self.assertContains(response, 'lg:px-8')
    
    def test_accessibility_features(self):
        """Test that accessibility features are implemented."""
        url = reverse('admin_panel:notifications_management')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for proper form labels
        self.assertContains(response, '<label')
        
        # Check for ARIA attributes
        self.assertContains(response, 'aria-')
        
        # Check for proper button types
        self.assertContains(response, 'type="button"')
        self.assertContains(response, 'type="submit"')
        
        # Check for disabled state handling
        self.assertContains(response, ':disabled="loading"')


class NotificationManagementThemeTestCase(TestCase):
    """Test theme functionality and styling."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_active=True
        )
        
        # Login as super admin
        self.client.force_login(self.super_admin)
    
    def test_dual_theme_support(self):
        """Test that both light and dark themes are supported."""
        url = reverse('admin_panel:notifications_management')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check for light theme classes
        self.assertContains(response, 'bg-white')
        self.assertContains(response, 'text-gray-900')
        self.assertContains(response, 'border-gray-200')
        
        # Check for dark theme classes
        self.assertContains(response, 'dark:bg-cyber-bg-surface')
        self.assertContains(response, 'dark:text-cyber-text-primary')
        self.assertContains(response, 'dark:border-cyber-neon-primary')
    
    def test_cybersecurity_styling_dark_mode(self):
        """Test cybersecurity styling for dark mode."""
        url = reverse('admin_panel:notifications_management')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check for cybersecurity color scheme
        self.assertContains(response, 'cyber-neon-primary')
        self.assertContains(response, 'cyber-neon-success')
        self.assertContains(response, 'cyber-neon-danger')
        self.assertContains(response, 'cyber-neon-warning')
        self.assertContains(response, 'cyber-neon-info')
        
        # Check for glassmorphism effects
        self.assertContains(response, 'glassmorphism')
        self.assertContains(response, 'backdrop-filter: blur(10px)')
        
        # Check for cyber glow effects
        self.assertContains(response, 'cyber-glow')
    
    def test_theme_aware_components(self):
        """Test that components are theme-aware."""
        url = reverse('admin_panel:notifications_management')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check for theme-aware status badges
        self.assertContains(response, 'status-success')
        self.assertContains(response, 'status-error')
        self.assertContains(response, 'status-warning')
        self.assertContains(response, 'status-info')
        
        # Check for theme transitions
        self.assertContains(response, 'transition-colors')
        self.assertContains(response, 'transition-all')


if __name__ == '__main__':
    pytest.main([__file__])