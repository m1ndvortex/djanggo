"""
Unit tests for notification service core functionality.
Tests the service logic without database dependencies.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import smtplib
import socket
from django.core.exceptions import ValidationError

# Test the service classes directly without Django setup
def test_email_server_configuration_test_connection_success():
    """Test successful SMTP connection test."""
    from zargar.admin_panel.services.notification_service import EmailServerConfiguration
    
    with patch('smtplib.SMTP') as mock_smtp:
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
        
        assert result['success'] is True
        assert result['error'] is None
        assert result['details']['connection_status'] == 'success'
        
        # Verify SMTP methods were called
        mock_smtp.assert_called_once_with('smtp.example.com', 587, timeout=30)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('test@example.com', 'testpass')
        mock_server.quit.assert_called_once()


def test_email_server_configuration_test_connection_auth_failure():
    """Test SMTP connection test with authentication failure."""
    from zargar.admin_panel.services.notification_service import EmailServerConfiguration
    
    with patch('smtplib.SMTP') as mock_smtp:
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
        
        assert result['success'] is False
        assert 'Authentication failed' in result['error']
        assert result['details']['connection_status'] == 'auth_failed'


def test_email_server_configuration_test_connection_failure():
    """Test SMTP connection test with connection failure."""
    from zargar.admin_panel.services.notification_service import EmailServerConfiguration
    
    with patch('smtplib.SMTP') as mock_smtp:
        # Mock connection failure
        mock_smtp.side_effect = smtplib.SMTPConnectError(421, 'Service not available')
        
        config = {
            'host': 'nonexistent.example.com',
            'port': 587,
            'timeout': 30,
        }
        
        result = EmailServerConfiguration.test_connection(config)
        
        assert result['success'] is False
        assert 'Connection failed' in result['error']
        assert result['details']['connection_status'] == 'connection_failed'


def test_email_server_configuration_test_connection_timeout():
    """Test SMTP connection test with timeout."""
    from zargar.admin_panel.services.notification_service import EmailServerConfiguration
    
    with patch('smtplib.SMTP') as mock_smtp:
        # Mock timeout
        mock_smtp.side_effect = socket.timeout()
        
        config = {
            'host': 'slow.example.com',
            'port': 587,
            'timeout': 5,
        }
        
        result = EmailServerConfiguration.test_connection(config)
        
        assert result['success'] is False
        assert 'Connection timeout after 5 seconds' in result['error']
        assert result['details']['connection_status'] == 'timeout'


def test_notification_delivery_service_fallback_critical():
    """Test fallback delivery for critical events."""
    from zargar.admin_panel.services.notification_service import NotificationDeliveryService
    
    # Mock notification setting
    mock_setting = Mock()
    mock_setting.recipients = ['admin@example.com']
    
    event_data = {
        'priority': 'critical',
        'message': 'Critical system failure',
    }
    
    with patch('zargar.admin_panel.services.notification_service.logger') as mock_logger:
        result = NotificationDeliveryService._try_fallback_delivery(
            mock_setting, 'Critical Alert', 'System failure detected', event_data
        )
        
        assert result['success'] is True
        assert result['delivery_method'] == 'log_fallback'
        
        # Verify critical log was written
        mock_logger.critical.assert_called_once()
        log_call_args = mock_logger.critical.call_args[0][0]
        assert 'CRITICAL NOTIFICATION FALLBACK' in log_call_args
        assert 'Critical Alert' in log_call_args


def test_notification_delivery_service_fallback_non_critical():
    """Test fallback delivery for non-critical events."""
    from zargar.admin_panel.services.notification_service import NotificationDeliveryService
    
    # Mock notification setting
    mock_setting = Mock()
    mock_setting.recipients = ['admin@example.com']
    
    event_data = {
        'priority': 'medium',
        'message': 'Regular system event',
    }
    
    result = NotificationDeliveryService._try_fallback_delivery(
        mock_setting, 'Regular Alert', 'System event', event_data
    )
    
    assert result['success'] is False
    assert result['delivery_method'] is None
    assert result['error'] == 'No fallback methods available'


def test_notification_delivery_service_send_email():
    """Test email notification sending."""
    from zargar.admin_panel.services.notification_service import NotificationDeliveryService
    
    # Mock notification setting
    mock_setting = Mock()
    mock_setting.recipients = ['admin@example.com', 'security@example.com']
    
    with patch('zargar.admin_panel.services.notification_service.EmailServerConfiguration.get_email_config') as mock_get_config:
        with patch('django.core.mail.send_mail') as mock_send_mail:
            # Mock email configuration
            mock_get_config.return_value = {
                'host': 'smtp.example.com',
                'port': 587,
                'username': 'test@example.com',
                'password': 'testpass',
                'use_tls': True,
                'use_ssl': False,
                'from_email': 'noreply@example.com',
                'timeout': 30,
            }
            
            mock_send_mail.return_value = True
            
            result = NotificationDeliveryService._send_email(
                mock_setting, 'Test Subject', 'Test Message', {}
            )
            
            assert result is True
            mock_send_mail.assert_called_once()


def test_notification_delivery_service_send_email_failure():
    """Test email notification sending failure."""
    from zargar.admin_panel.services.notification_service import NotificationDeliveryService
    
    # Mock notification setting
    mock_setting = Mock()
    mock_setting.recipients = ['admin@example.com']
    
    with patch('zargar.admin_panel.services.notification_service.EmailServerConfiguration.get_email_config') as mock_get_config:
        with patch('django.core.mail.send_mail') as mock_send_mail:
            # Mock email configuration
            mock_get_config.return_value = {
                'host': 'smtp.example.com',
                'port': 587,
                'from_email': 'noreply@example.com',
            }
            
            # Mock send_mail failure
            mock_send_mail.side_effect = Exception('SMTP error')
            
            result = NotificationDeliveryService._send_email(
                mock_setting, 'Test Subject', 'Test Message', {}
            )
            
            assert result is False


def test_notification_delivery_service_send_webhook():
    """Test webhook notification sending."""
    from zargar.admin_panel.services.notification_service import NotificationDeliveryService
    
    # Mock notification setting
    mock_setting = Mock()
    mock_setting.delivery_config = {
        'url': 'http://example.com/webhook',
        'headers': {'Authorization': 'Bearer token'},
        'timeout': 30,
    }
    mock_setting.event_type = 'security_alert'
    
    with patch('requests.post') as mock_post:
        # Mock successful webhook response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        event_data = {
            'message': 'Test webhook event',
            'priority': 'high',
        }
        
        result = NotificationDeliveryService._send_webhook(
            mock_setting, 'Webhook Alert', 'Alert message', event_data
        )
        
        assert result is True
        
        # Verify webhook was called with correct data
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]['json']['event_type'] == 'security_alert'
        assert call_args[1]['json']['message'] == 'Alert message'
        assert call_args[1]['json']['subject'] == 'Webhook Alert'


def test_notification_delivery_service_send_webhook_failure():
    """Test webhook notification sending failure."""
    from zargar.admin_panel.services.notification_service import NotificationDeliveryService
    
    # Mock notification setting
    mock_setting = Mock()
    mock_setting.delivery_config = {
        'url': 'http://example.com/webhook',
        'timeout': 30,
    }
    mock_setting.event_type = 'security_alert'
    
    with patch('requests.post') as mock_post:
        # Mock webhook failure
        mock_post.side_effect = Exception('Connection error')
        
        result = NotificationDeliveryService._send_webhook(
            mock_setting, 'Webhook Alert', 'Alert message', {}
        )
        
        assert result is False


def test_notification_delivery_service_send_webhook_no_url():
    """Test webhook notification with missing URL."""
    from zargar.admin_panel.services.notification_service import NotificationDeliveryService
    
    # Mock notification setting without URL
    mock_setting = Mock()
    mock_setting.delivery_config = {}
    
    result = NotificationDeliveryService._send_webhook(
        mock_setting, 'Webhook Alert', 'Alert message', {}
    )
    
    assert result is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])