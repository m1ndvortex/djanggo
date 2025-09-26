"""
Unit tests for notification management backend.
Tests email server configuration, alert thresholds, and delivery system.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing models
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.mail import EmailMessage
import json
import smtplib
from datetime import timedelta

from zargar.admin_panel.models import SystemSetting, NotificationSetting
from zargar.admin_panel.services.notification_service import (
    EmailServerConfiguration,
    AlertThresholdManager,
    NotificationDeliveryService
)


class EmailServerConfigurationTest(TestCase):
    """Test email server configuration functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create email configuration settings
        self.email_settings = [
            ('email_host', 'smtp.example.com'),
            ('email_port', '587'),
            ('email_username', 'test@example.com'),
            ('email_password', 'testpass'),
            ('email_use_tls', 'true'),
            ('email_use_ssl', 'false'),
            ('email_from_address', 'noreply@example.com'),
            ('email_timeout', '30'),
        ]
        
        for key, value in self.email_settings:
            SystemSetting.objects.create(
                key=key,
                name=key.replace('_', ' ').title(),
                description=f'Test {key}',
                value=value,
                default_value=value,
                setting_type='string' if key not in ['email_port', 'email_timeout'] else 'integer',
                category='notifications',
                section='email_server',
            )
    
    def test_get_email_config(self):
        """Test getting email configuration."""
        config = EmailServerConfiguration.get_email_config()
        
        self.assertEqual(config['host'], 'smtp.example.com')
        self.assertEqual(config['port'], 587)
        self.assertEqual(config['username'], 'test@example.com')
        self.assertEqual(config['password'], 'testpass')
        self.assertTrue(config['use_tls'])
        self.assertFalse(config['use_ssl'])
        self.assertEqual(config['from_email'], 'noreply@example.com')
        self.assertEqual(config['timeout'], 30)
    
    def test_update_email_config_success(self):
        """Test successful email configuration update."""
        new_config = {
            'host': 'smtp.newserver.com',
            'port': 465,
            'username': 'newuser@example.com',
            'password': 'newpass',
            'use_tls': False,
            'use_ssl': True,
            'from_email': 'admin@example.com',
            'timeout': 60,
        }
        
        result = EmailServerConfiguration.update_email_config(new_config)
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['updated_settings']), 8)
        self.assertEqual(len(result['errors']), 0)
        
        # Verify settings were updated
        updated_config = EmailServerConfiguration.get_email_config()
        self.assertEqual(updated_config['host'], 'smtp.newserver.com')
        self.assertEqual(updated_config['port'], 465)
        self.assertFalse(updated_config['use_tls'])
        self.assertTrue(updated_config['use_ssl'])
    
    def test_update_email_config_validation_error(self):
        """Test email configuration update with validation errors."""
        invalid_config = {
            'port': 'invalid_port',  # Should be integer
            'from_email': 'invalid_email',  # Should be valid email
        }
        
        result = EmailServerConfiguration.update_email_config(invalid_config)
        
        self.assertFalse(result['success'])
        self.assertGreater(len(result['errors']), 0)
    
    @patch('smtplib.SMTP')
    def test_connection_test_success(self, mock_smtp):
        """Test successful SMTP connection test."""
        # Mock successful SMTP connection
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        config = {
            'host': 'smtp.example.com',
            'port': 587,
            'username': 'test@example.com',
            'password': 'testpass',
            'use_tls': True,
            'use_ssl': False,
            'timeout': 30,
        }
        
        result = EmailServerConfiguration.test_connection(config)
        
        self.assertTrue(result['success'])
        self.assertIsNone(result['error'])
        self.assertEqual(result['details']['connection_status'], 'success')
        
        # Verify SMTP methods were called
        mock_smtp.assert_called_once_with('smtp.example.com', 587, timeout=30)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('test@example.com', 'testpass')
        mock_server.quit.assert_called_once()
    
    @patch('smtplib.SMTP')
    def test_connection_test_auth_failure(self, mock_smtp):
        """Test SMTP connection test with authentication failure."""
        # Mock authentication failure
        mock_server = Mock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, 'Authentication failed')
        mock_smtp.return_value = mock_server
        
        config = {
            'host': 'smtp.example.com',
            'port': 587,
            'username': 'test@example.com',
            'password': 'wrongpass',
            'use_tls': True,
            'use_ssl': False,
            'timeout': 30,
        }
        
        result = EmailServerConfiguration.test_connection(config)
        
        self.assertFalse(result['success'])
        self.assertIn('Authentication failed', result['error'])
        self.assertEqual(result['details']['connection_status'], 'auth_failed')
    
    @patch('smtplib.SMTP')
    def test_connection_test_connection_failure(self, mock_smtp):
        """Test SMTP connection test with connection failure."""
        # Mock connection failure
        mock_smtp.side_effect = smtplib.SMTPConnectError(421, 'Service not available')
        
        config = {
            'host': 'nonexistent.example.com',
            'port': 587,
            'timeout': 30,
        }
        
        result = EmailServerConfiguration.test_connection(config)
        
        self.assertFalse(result['success'])
        self.assertIn('Connection failed', result['error'])
        self.assertEqual(result['details']['connection_status'], 'connection_failed')
    
    @patch('django.core.mail.send_mail')
    def test_send_test_email_success(self, mock_send_mail):
        """Test successful test email sending."""
        mock_send_mail.return_value = True
        
        config = {
            'host': 'smtp.example.com',
            'port': 587,
            'username': 'test@example.com',
            'password': 'testpass',
            'use_tls': True,
            'use_ssl': False,
            'from_email': 'noreply@example.com',
            'timeout': 30,
        }
        
        result = EmailServerConfiguration.send_test_email('recipient@example.com', config)
        
        self.assertTrue(result['success'])
        self.assertIsNone(result['error'])
        self.assertEqual(result['recipient'], 'recipient@example.com')
        
        # Verify send_mail was called
        mock_send_mail.assert_called_once()
    
    @patch('django.core.mail.send_mail')
    def test_send_test_email_failure(self, mock_send_mail):
        """Test test email sending failure."""
        mock_send_mail.side_effect = Exception('SMTP server error')
        
        result = EmailServerConfiguration.send_test_email('recipient@example.com')
        
        self.assertFalse(result['success'])
        self.assertIn('SMTP server error', result['error'])


class AlertThresholdManagerTest(TestCase):
    """Test alert threshold management functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create alert threshold settings
        self.threshold_settings = [
            ('alert_failed_login_threshold', '5'),
            ('alert_failed_login_window', '15'),
            ('alert_suspicious_activity_threshold', '3'),
            ('alert_cpu_threshold', '80'),
            ('alert_memory_threshold', '85'),
            ('alert_backup_failure_threshold', '1'),
        ]
        
        for key, value in self.threshold_settings:
            SystemSetting.objects.create(
                key=key,
                name=key.replace('_', ' ').title(),
                description=f'Test {key}',
                value=value,
                default_value=value,
                setting_type='integer',
                category='notifications',
                section='alerts',
            )
        
        # Create recipient settings
        self.recipient_settings = [
            ('recipients_security_alerts', '["admin@example.com", "security@example.com"]'),
            ('recipients_system_health', '["ops@example.com"]'),
            ('recipients_critical_alerts', '["admin@example.com"]'),
        ]
        
        for key, value in self.recipient_settings:
            SystemSetting.objects.create(
                key=key,
                name=key.replace('_', ' ').title(),
                description=f'Test {key}',
                value=value,
                default_value=value,
                setting_type='json',
                category='notifications',
                section='recipients',
            )
    
    def test_get_alert_thresholds(self):
        """Test getting alert thresholds."""
        thresholds = AlertThresholdManager.get_alert_thresholds()
        
        self.assertEqual(thresholds['security_events']['failed_login_threshold'], 5)
        self.assertEqual(thresholds['security_events']['failed_login_window_minutes'], 15)
        self.assertEqual(thresholds['security_events']['suspicious_activity_threshold'], 3)
        self.assertEqual(thresholds['system_health']['cpu_usage_threshold'], 80)
        self.assertEqual(thresholds['system_health']['memory_usage_threshold'], 85)
        self.assertEqual(thresholds['backup_system']['backup_failure_threshold'], 1)
    
    def test_update_alert_thresholds_success(self):
        """Test successful alert threshold update."""
        new_thresholds = {
            'security_events': {
                'failed_login_threshold': 10,
                'suspicious_activity_threshold': 5,
            },
            'system_health': {
                'cpu_usage_threshold': 90,
                'memory_usage_threshold': 95,
            },
        }
        
        result = AlertThresholdManager.update_alert_thresholds(new_thresholds)
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['updated_settings']), 4)
        self.assertEqual(len(result['errors']), 0)
        
        # Verify thresholds were updated
        updated_thresholds = AlertThresholdManager.get_alert_thresholds()
        self.assertEqual(updated_thresholds['security_events']['failed_login_threshold'], 10)
        self.assertEqual(updated_thresholds['security_events']['suspicious_activity_threshold'], 5)
        self.assertEqual(updated_thresholds['system_health']['cpu_usage_threshold'], 90)
        self.assertEqual(updated_thresholds['system_health']['memory_usage_threshold'], 95)
    
    def test_get_notification_recipients(self):
        """Test getting notification recipients."""
        recipients = AlertThresholdManager.get_notification_recipients()
        
        self.assertEqual(recipients['security_alerts'], ['admin@example.com', 'security@example.com'])
        self.assertEqual(recipients['system_health'], ['ops@example.com'])
        self.assertEqual(recipients['critical_alerts'], ['admin@example.com'])
    
    def test_update_notification_recipients_success(self):
        """Test successful notification recipients update."""
        new_recipients = {
            'security_alerts': ['newadmin@example.com', 'newsecurity@example.com'],
            'system_health': ['newops@example.com', 'monitoring@example.com'],
        }
        
        result = AlertThresholdManager.update_notification_recipients(new_recipients)
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['updated_settings']), 2)
        self.assertEqual(len(result['errors']), 0)
        
        # Verify recipients were updated
        updated_recipients = AlertThresholdManager.get_notification_recipients()
        self.assertEqual(updated_recipients['security_alerts'], ['newadmin@example.com', 'newsecurity@example.com'])
        self.assertEqual(updated_recipients['system_health'], ['newops@example.com', 'monitoring@example.com'])
    
    def test_update_notification_recipients_invalid_email(self):
        """Test notification recipients update with invalid email."""
        invalid_recipients = {
            'security_alerts': ['invalid_email', 'valid@example.com'],
        }
        
        result = AlertThresholdManager.update_notification_recipients(invalid_recipients)
        
        self.assertFalse(result['success'])
        self.assertGreater(len(result['errors']), 0)


class NotificationDeliveryServiceTest(TestCase):
    """Test notification delivery service functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create notification setting
        self.notification_setting = NotificationSetting.objects.create(
            name='Test Security Alert',
            event_type='security_alert',
            notification_type='email',
            recipients=['admin@example.com', 'security@example.com'],
            priority_threshold='medium',
            is_enabled=True,
            subject_template='Security Alert: {event_type}',
            message_template='Alert: {message}\nTime: {timestamp}',
            template_variables={'event_type': 'Security Event'},
            retry_attempts=3,
            retry_delay_minutes=1,
        )
        
        # Create email configuration settings
        email_settings = [
            ('email_host', 'smtp.example.com'),
            ('email_port', '587'),
            ('email_username', 'test@example.com'),
            ('email_password', 'testpass'),
            ('email_use_tls', 'true'),
            ('email_from_address', 'noreply@example.com'),
            ('email_timeout', '30'),
        ]
        
        for key, value in email_settings:
            SystemSetting.objects.create(
                key=key,
                name=key.replace('_', ' ').title(),
                description=f'Test {key}',
                value=value,
                default_value=value,
                setting_type='string' if key not in ['email_port', 'email_timeout'] else 'integer',
                category='notifications',
                section='email_server',
            )
    
    @patch('zargar.admin_panel.services.settings_service.NotificationManager.should_send_notification')
    @patch('zargar.admin_panel.services.notification_service.NotificationDeliveryService._deliver_notification')
    def test_send_notification_success(self, mock_deliver, mock_should_send):
        """Test successful notification sending."""
        # Mock should_send_notification to return our test setting
        mock_should_send.return_value = [self.notification_setting]
        
        # Mock successful delivery
        mock_deliver.return_value = {
            'success': True,
            'setting_id': self.notification_setting.id,
            'setting_name': self.notification_setting.name,
            'notification_type': 'email',
            'recipients': ['admin@example.com'],
            'attempts': 1,
            'error': None,
            'delivery_method': 'email',
        }
        
        event_data = {
            'message': 'Test security event',
            'timestamp': timezone.now().isoformat(),
            'priority': 'high',
        }
        
        result = NotificationDeliveryService.send_notification(
            'security_alert', 'high', event_data
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['notifications_sent'], 1)
        self.assertEqual(result['notifications_failed'], 0)
        self.assertEqual(len(result['delivery_results']), 1)
        
        # Verify methods were called
        mock_should_send.assert_called_once_with('security_alert', 'high', event_data)
        mock_deliver.assert_called_once()
    
    @patch('zargar.admin_panel.services.settings_service.NotificationManager.should_send_notification')
    def test_send_notification_no_matching_settings(self, mock_should_send):
        """Test notification sending with no matching settings."""
        # Mock no matching settings
        mock_should_send.return_value = []
        
        result = NotificationDeliveryService.send_notification('security_alert', 'low')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['notifications_sent'], 0)
        self.assertEqual(result['notifications_failed'], 0)
        self.assertIn('No notification settings matched', result['message'])
    
    @patch('django.core.mail.send_mail')
    def test_deliver_notification_email_success(self, mock_send_mail):
        """Test successful email notification delivery."""
        mock_send_mail.return_value = True
        
        event_data = {
            'message': 'Test security event',
            'timestamp': timezone.now().isoformat(),
        }
        
        result = NotificationDeliveryService._deliver_notification(
            self.notification_setting, event_data
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['attempts'], 1)
        self.assertEqual(result['delivery_method'], 'email')
        self.assertIsNone(result['error'])
        
        # Verify send_mail was called
        mock_send_mail.assert_called_once()
    
    @patch('django.core.mail.send_mail')
    def test_deliver_notification_email_failure_with_retry(self, mock_send_mail):
        """Test email notification delivery failure with retry."""
        # Mock send_mail to fail
        mock_send_mail.side_effect = Exception('SMTP error')
        
        # Set short retry delay for testing
        self.notification_setting.retry_delay_minutes = 0
        self.notification_setting.save()
        
        event_data = {
            'message': 'Test security event',
            'timestamp': timezone.now().isoformat(),
        }
        
        result = NotificationDeliveryService._deliver_notification(
            self.notification_setting, event_data
        )
        
        self.assertFalse(result['success'])
        self.assertEqual(result['attempts'], 3)  # Should retry 3 times
        self.assertIn('SMTP error', result['error'])
        
        # Verify send_mail was called multiple times
        self.assertEqual(mock_send_mail.call_count, 3)
    
    def test_deliver_notification_template_rendering_error(self):
        """Test notification delivery with template rendering error."""
        # Create setting with invalid template
        invalid_setting = NotificationSetting.objects.create(
            name='Invalid Template Test',
            event_type='security_alert',
            notification_type='email',
            recipients=['admin@example.com'],
            subject_template='Subject: {invalid_variable}',
            message_template='Message: {another_invalid_variable}',
            is_enabled=True,
        )
        
        event_data = {'valid_variable': 'test'}
        
        result = NotificationDeliveryService._deliver_notification(
            invalid_setting, event_data
        )
        
        self.assertFalse(result['success'])
        self.assertEqual(result['attempts'], 0)
        self.assertIn('Template rendering failed', result['error'])
    
    @patch('requests.post')
    def test_deliver_notification_webhook_success(self, mock_post):
        """Test successful webhook notification delivery."""
        # Create webhook notification setting
        webhook_setting = NotificationSetting.objects.create(
            name='Test Webhook Alert',
            event_type='security_alert',
            notification_type='webhook',
            recipients=['http://example.com/webhook'],
            delivery_config={
                'url': 'http://example.com/webhook',
                'headers': {'Authorization': 'Bearer token'},
                'timeout': 30,
            },
            subject_template='Webhook Alert: {event_type}',
            message_template='Alert: {message}',
            is_enabled=True,
        )
        
        # Mock successful webhook response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        event_data = {
            'message': 'Test webhook event',
            'priority': 'high',
        }
        
        result = NotificationDeliveryService._deliver_notification(
            webhook_setting, event_data
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['delivery_method'], 'webhook')
        
        # Verify webhook was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[1]['json']['event_type'], 'security_alert')
        self.assertEqual(call_args[1]['json']['message'], 'Alert: Test webhook event')
    
    def test_get_delivery_statistics(self):
        """Test getting delivery statistics."""
        # Update notification setting with some statistics
        self.notification_setting.total_sent = 10
        self.notification_setting.total_failed = 2
        self.notification_setting.save()
        
        # Create another setting
        NotificationSetting.objects.create(
            name='Another Setting',
            event_type='backup_complete',
            notification_type='email',
            recipients=['ops@example.com'],
            total_sent=5,
            total_failed=1,
            is_enabled=True,
        )
        
        stats = NotificationDeliveryService.get_delivery_statistics(30)
        
        self.assertEqual(stats['period_days'], 30)
        self.assertEqual(stats['total_sent'], 15)
        self.assertEqual(stats['total_failed'], 3)
        self.assertEqual(stats['success_rate'], 83.33)  # 15/(15+3) * 100
        self.assertEqual(stats['active_settings'], 2)
        self.assertEqual(stats['total_settings'], 2)
    
    @patch('zargar.admin_panel.services.notification_service.logger')
    def test_fallback_delivery_critical_event(self, mock_logger):
        """Test fallback delivery for critical events."""
        event_data = {
            'priority': 'critical',
            'message': 'Critical system failure',
        }
        
        result = NotificationDeliveryService._try_fallback_delivery(
            self.notification_setting, 'Critical Alert', 'System failure detected', event_data
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['delivery_method'], 'log_fallback')
        
        # Verify critical log was written
        mock_logger.critical.assert_called_once()
        log_call_args = mock_logger.critical.call_args[0][0]
        self.assertIn('CRITICAL NOTIFICATION FALLBACK', log_call_args)
        self.assertIn('Critical Alert', log_call_args)
    
    def test_fallback_delivery_non_critical_event(self):
        """Test fallback delivery for non-critical events."""
        event_data = {
            'priority': 'medium',
            'message': 'Regular system event',
        }
        
        result = NotificationDeliveryService._try_fallback_delivery(
            self.notification_setting, 'Regular Alert', 'System event', event_data
        )
        
        self.assertFalse(result['success'])
        self.assertIsNone(result['delivery_method'])
        self.assertEqual(result['error'], 'No fallback methods available')


class NotificationSettingModelTest(TestCase):
    """Test NotificationSetting model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.notification_setting = NotificationSetting.objects.create(
            name='Test Notification',
            event_type='security_alert',
            notification_type='email',
            recipients=['admin@example.com'],
            priority_threshold='medium',
            is_enabled=True,
            throttle_minutes=60,
            quiet_hours_start='22:00',
            quiet_hours_end='06:00',
            subject_template='Alert: {event_type}',
            message_template='Message: {message}',
            template_variables={'event_type': 'Security Alert'},
            conditions={'severity': 'high'},
        )
    
    def test_should_send_notification_enabled(self):
        """Test should_send_notification when enabled."""
        result = self.notification_setting.should_send_notification('high')
        self.assertTrue(result)
    
    def test_should_send_notification_disabled(self):
        """Test should_send_notification when disabled."""
        self.notification_setting.is_enabled = False
        self.notification_setting.save()
        
        result = self.notification_setting.should_send_notification('high')
        self.assertFalse(result)
    
    def test_should_send_notification_priority_threshold(self):
        """Test should_send_notification with priority threshold."""
        # Low priority should not trigger medium threshold
        result = self.notification_setting.should_send_notification('low')
        self.assertFalse(result)
        
        # High priority should trigger medium threshold
        result = self.notification_setting.should_send_notification('high')
        self.assertTrue(result)
    
    def test_should_send_notification_throttling(self):
        """Test should_send_notification with throttling."""
        # Set last sent time to recent
        self.notification_setting.last_sent_at = timezone.now() - timedelta(minutes=30)
        self.notification_setting.save()
        
        # Should be throttled (60 minute throttle, only 30 minutes passed)
        result = self.notification_setting.should_send_notification('high')
        self.assertFalse(result)
        
        # Set last sent time to older
        self.notification_setting.last_sent_at = timezone.now() - timedelta(minutes=90)
        self.notification_setting.save()
        
        # Should not be throttled
        result = self.notification_setting.should_send_notification('high')
        self.assertTrue(result)
    
    def test_should_send_notification_conditions(self):
        """Test should_send_notification with custom conditions."""
        # Event data matching conditions
        event_data = {'severity': 'high', 'source': 'auth_system'}
        result = self.notification_setting.should_send_notification('high', event_data)
        self.assertTrue(result)
        
        # Event data not matching conditions
        event_data = {'severity': 'low', 'source': 'auth_system'}
        result = self.notification_setting.should_send_notification('high', event_data)
        self.assertFalse(result)
    
    def test_render_message(self):
        """Test message rendering with template variables."""
        event_data = {
            'message': 'Login failed',
            'user': 'testuser',
            'timestamp': '2023-01-01 12:00:00',
        }
        
        subject, message = self.notification_setting.render_message(event_data)
        
        self.assertEqual(subject, 'Alert: Security Alert')
        self.assertEqual(message, 'Message: Login failed')
    
    def test_record_sent(self):
        """Test recording successful notification send."""
        initial_count = self.notification_setting.total_sent
        initial_time = self.notification_setting.last_sent_at
        
        self.notification_setting.record_sent()
        
        self.assertEqual(self.notification_setting.total_sent, initial_count + 1)
        self.assertIsNotNone(self.notification_setting.last_sent_at)
        self.assertNotEqual(self.notification_setting.last_sent_at, initial_time)
    
    def test_record_failed(self):
        """Test recording failed notification delivery."""
        initial_count = self.notification_setting.total_failed
        
        self.notification_setting.record_failed()
        
        self.assertEqual(self.notification_setting.total_failed, initial_count + 1)


if __name__ == '__main__':
    pytest.main([__file__])