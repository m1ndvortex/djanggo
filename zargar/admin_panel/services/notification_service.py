"""
Enhanced notification management service for super admin panel.
Implements email server configuration, alert thresholds, and delivery system with fallbacks.
"""
from django.core.exceptions import ValidationError
from django.core.mail import send_mail, get_connection
from django.core.mail.backends.smtp import EmailBackend
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from typing import Dict, List, Any, Optional, Union, Tuple
import json
import logging
import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

from ..models import SystemSetting, NotificationSetting

# Safe import for AuditLog - handle missing table gracefully
try:
    from zargar.core.security_models import AuditLog
    AUDIT_LOG_AVAILABLE = True
except ImportError:
    AUDIT_LOG_AVAILABLE = False
    AuditLog = None

logger = logging.getLogger(__name__)


def safe_audit_log(action, user=None, content_object=None, **kwargs):
    """Safely log audit events, handling missing AuditLog table."""
    if AUDIT_LOG_AVAILABLE and AuditLog:
        try:
            AuditLog.log_action(
                action=action,
                user=user,
                content_object=content_object,
                **kwargs
            )
        except Exception as e:
            logger.warning(f"Failed to log audit event: {e}")
    else:
        logger.info(f"Audit log not available - Action: {action}, User: {user}")


class EmailServerConfiguration:
    """
    Email server configuration management with connection testing.
    """
    
    @staticmethod
    def get_email_config() -> Dict[str, Any]:
        """
        Get current email server configuration.
        
        Returns:
            Dictionary containing email configuration
        """
        from ..services.settings_service import SettingsManager
        
        return {
            'host': SettingsManager.get_setting('email_host', 'localhost'),
            'port': SettingsManager.get_setting('email_port', 587),
            'username': SettingsManager.get_setting('email_username', ''),
            'password': SettingsManager.get_setting('email_password', ''),
            'use_tls': SettingsManager.get_setting('email_use_tls', True),
            'use_ssl': SettingsManager.get_setting('email_use_ssl', False),
            'from_email': SettingsManager.get_setting('email_from_address', ''),
            'timeout': SettingsManager.get_setting('email_timeout', 30),
        }
    
    @staticmethod
    def update_email_config(config: Dict[str, Any], user=None) -> Dict[str, Any]:
        """
        Update email server configuration with validation.
        
        Args:
            config: New email configuration
            user: User making the change
            
        Returns:
            Dictionary with update results
        """
        from ..services.settings_service import SettingsManager
        
        results = {
            'success': True,
            'updated_settings': [],
            'errors': {},
            'test_result': None,
        }
        
        # Define email settings mapping
        email_settings = {
            'email_host': config.get('host'),
            'email_port': config.get('port'),
            'email_username': config.get('username'),
            'email_password': config.get('password'),
            'email_use_tls': config.get('use_tls'),
            'email_use_ssl': config.get('use_ssl'),
            'email_from_address': config.get('from_email'),
            'email_timeout': config.get('timeout'),
        }
        
        try:
            # Update each setting individually to avoid transaction issues
            for key, value in email_settings.items():
                if value is not None:
                    try:
                        setting = SettingsManager.set_setting(
                            key, value, user, 
                            reason='Email server configuration update'
                        )
                        results['updated_settings'].append({
                            'key': key,
                            'name': setting.name,
                            'value': value,
                        })
                    except ValidationError as e:
                        results['errors'][key] = str(e)
                        results['success'] = False
                    except Exception as e:
                        logger.error(f"Error updating setting {key}: {e}")
                        results['errors'][key] = str(e)
                        results['success'] = False
            
            # Test connection if update was successful
            if results['success'] and config.get('test_connection', False):
                test_result = EmailServerConfiguration.test_connection(config)
                results['test_result'] = test_result
                
                if not test_result['success']:
                    results['success'] = False
                    results['errors']['connection_test'] = test_result['error']
        
        except Exception as e:
            logger.error(f"Error updating email configuration: {e}")
            results['success'] = False
            results['errors']['general'] = str(e)
        
        return results
    
    @staticmethod
    def test_connection(config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Test email server connection.
        
        Args:
            config: Email configuration to test (uses current if None)
            
        Returns:
            Dictionary with test results
        """
        if config is None:
            config = EmailServerConfiguration.get_email_config()
        
        result = {
            'success': False,
            'error': None,
            'details': {},
            'timestamp': timezone.now().isoformat(),
        }
        
        try:
            # Test SMTP connection
            host = config.get('host', 'localhost')
            port = int(config.get('port', 587))
            username = config.get('username', '')
            password = config.get('password', '')
            use_tls = config.get('use_tls', True)
            use_ssl = config.get('use_ssl', False)
            timeout = int(config.get('timeout', 30))
            
            result['details']['host'] = host
            result['details']['port'] = port
            result['details']['use_tls'] = use_tls
            result['details']['use_ssl'] = use_ssl
            result['details']['timeout'] = timeout
            
            # Create SMTP connection
            if use_ssl:
                server = smtplib.SMTP_SSL(host, port, timeout=timeout)
            else:
                server = smtplib.SMTP(host, port, timeout=timeout)
            
            # Enable TLS if required
            if use_tls and not use_ssl:
                server.starttls()
            
            # Authenticate if credentials provided
            if username and password:
                server.login(username, password)
                result['details']['authentication'] = 'success'
            else:
                result['details']['authentication'] = 'not_required'
            
            # Test successful
            server.quit()
            result['success'] = True
            result['details']['connection_status'] = 'success'
            
            logger.info(f"Email server connection test successful: {host}:{port}")
        
        except smtplib.SMTPAuthenticationError as e:
            result['error'] = f"Authentication failed: {str(e)}"
            result['details']['connection_status'] = 'auth_failed'
            logger.warning(f"Email server authentication failed: {e}")
        
        except smtplib.SMTPConnectError as e:
            result['error'] = f"Connection failed: {str(e)}"
            result['details']['connection_status'] = 'connection_failed'
            logger.warning(f"Email server connection failed: {e}")
        
        except socket.timeout:
            result['error'] = f"Connection timeout after {timeout} seconds"
            result['details']['connection_status'] = 'timeout'
            logger.warning(f"Email server connection timeout: {host}:{port}")
        
        except Exception as e:
            result['error'] = f"Unexpected error: {str(e)}"
            result['details']['connection_status'] = 'error'
            logger.error(f"Email server test error: {e}")
        
        return result
    
    @staticmethod
    def send_test_email(recipient: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send a test email to verify configuration.
        
        Args:
            recipient: Email address to send test to
            config: Email configuration to use (uses current if None)
            
        Returns:
            Dictionary with send results
        """
        if config is None:
            config = EmailServerConfiguration.get_email_config()
        
        result = {
            'success': False,
            'error': None,
            'recipient': recipient,
            'timestamp': timezone.now().isoformat(),
        }
        
        try:
            # Create email backend with custom configuration
            backend = EmailBackend(
                host=config.get('host'),
                port=int(config.get('port', 587)),
                username=config.get('username'),
                password=config.get('password'),
                use_tls=config.get('use_tls', True),
                use_ssl=config.get('use_ssl', False),
                timeout=int(config.get('timeout', 30)),
            )
            
            # Send test email
            subject = _('ZARGAR System - Email Configuration Test')
            message = _(
                'This is a test email from ZARGAR jewelry management system.\n\n'
                'If you received this email, your email server configuration is working correctly.\n\n'
                'Test sent at: {timestamp}\n'
                'From: Super Admin Panel'
            ).format(timestamp=timezone.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            from_email = config.get('from_email', settings.DEFAULT_FROM_EMAIL)
            
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=[recipient],
                connection=backend,
                fail_silently=False,
            )
            
            result['success'] = True
            logger.info(f"Test email sent successfully to {recipient}")
        
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Failed to send test email to {recipient}: {e}")
        
        return result


class AlertThresholdManager:
    """
    Alert threshold configuration and recipient management.
    """
    
    @staticmethod
    def get_alert_thresholds() -> Dict[str, Any]:
        """
        Get current alert threshold configurations.
        
        Returns:
            Dictionary containing alert thresholds
        """
        from ..services.settings_service import SettingsManager
        
        return {
            'security_events': {
                'failed_login_threshold': SettingsManager.get_setting('alert_failed_login_threshold', 5),
                'failed_login_window_minutes': SettingsManager.get_setting('alert_failed_login_window', 15),
                'suspicious_activity_threshold': SettingsManager.get_setting('alert_suspicious_activity_threshold', 3),
                'rate_limit_threshold': SettingsManager.get_setting('alert_rate_limit_threshold', 10),
            },
            'system_health': {
                'cpu_usage_threshold': SettingsManager.get_setting('alert_cpu_threshold', 80),
                'memory_usage_threshold': SettingsManager.get_setting('alert_memory_threshold', 85),
                'disk_usage_threshold': SettingsManager.get_setting('alert_disk_threshold', 90),
                'response_time_threshold': SettingsManager.get_setting('alert_response_time_threshold', 5000),
            },
            'backup_system': {
                'backup_failure_threshold': SettingsManager.get_setting('alert_backup_failure_threshold', 1),
                'backup_delay_hours': SettingsManager.get_setting('alert_backup_delay_threshold', 25),
            },
            'tenant_management': {
                'tenant_creation_rate_threshold': SettingsManager.get_setting('alert_tenant_creation_threshold', 10),
                'tenant_suspension_threshold': SettingsManager.get_setting('alert_tenant_suspension_threshold', 5),
            },
        }
    
    @staticmethod
    def update_alert_thresholds(thresholds: Dict[str, Any], user=None) -> Dict[str, Any]:
        """
        Update alert threshold configurations.
        
        Args:
            thresholds: New threshold values
            user: User making the change
            
        Returns:
            Dictionary with update results
        """
        from ..services.settings_service import SettingsManager
        
        results = {
            'success': True,
            'updated_settings': [],
            'errors': {},
        }
        
        # Flatten threshold structure for setting updates
        flat_settings = {}
        for category, category_thresholds in thresholds.items():
            for key, value in category_thresholds.items():
                setting_key = f"alert_{key}"
                flat_settings[setting_key] = value
        
        try:
            # Update each setting individually to avoid transaction issues
            for key, value in flat_settings.items():
                try:
                    setting = SettingsManager.set_setting(
                        key, value, user,
                        reason='Alert threshold configuration update'
                    )
                    results['updated_settings'].append({
                        'key': key,
                        'name': setting.name,
                        'value': value,
                    })
                except ValidationError as e:
                    results['errors'][key] = str(e)
                    results['success'] = False
                except Exception as e:
                    logger.error(f"Error updating threshold {key}: {e}")
                    results['errors'][key] = str(e)
                    results['success'] = False
        
        except Exception as e:
            logger.error(f"Error updating alert thresholds: {e}")
            results['success'] = False
            results['errors']['general'] = str(e)
        
        return results
    
    @staticmethod
    def get_notification_recipients() -> Dict[str, List[str]]:
        """
        Get notification recipients by category.
        
        Returns:
            Dictionary of recipient lists by category
        """
        from ..services.settings_service import SettingsManager
        
        return {
            'security_alerts': SettingsManager.get_setting('recipients_security_alerts', []),
            'system_health': SettingsManager.get_setting('recipients_system_health', []),
            'backup_alerts': SettingsManager.get_setting('recipients_backup_alerts', []),
            'tenant_alerts': SettingsManager.get_setting('recipients_tenant_alerts', []),
            'critical_alerts': SettingsManager.get_setting('recipients_critical_alerts', []),
        }
    
    @staticmethod
    def update_notification_recipients(recipients: Dict[str, List[str]], user=None) -> Dict[str, Any]:
        """
        Update notification recipient lists.
        
        Args:
            recipients: New recipient lists by category
            user: User making the change
            
        Returns:
            Dictionary with update results
        """
        from ..services.settings_service import SettingsManager
        import json
        
        results = {
            'success': True,
            'updated_settings': [],
            'errors': {},
        }
        
        try:
            # Update each recipient list individually to avoid transaction issues
            for category, recipient_list in recipients.items():
                setting_key = f"recipients_{category}"
                try:
                    # Validate email addresses
                    from django.core.validators import validate_email
                    for email in recipient_list:
                        validate_email(email)
                    
                    # Convert list to JSON string for storage
                    json_value = json.dumps(recipient_list, ensure_ascii=False)
                    
                    setting = SettingsManager.set_setting(
                        setting_key, json_value, user,
                        reason='Notification recipients update'
                    )
                    results['updated_settings'].append({
                        'key': setting_key,
                        'name': setting.name,
                        'value': recipient_list,
                    })
                except ValidationError as e:
                    results['errors'][setting_key] = str(e)
                    results['success'] = False
                except Exception as e:
                    logger.error(f"Error updating recipients {setting_key}: {e}")
                    results['errors'][setting_key] = str(e)
                    results['success'] = False
        
        except Exception as e:
            logger.error(f"Error updating notification recipients: {e}")
            results['success'] = False
            results['errors']['general'] = str(e)
        
        return results


class NotificationDeliveryService:
    """
    Notification delivery system with fallback mechanisms.
    """
    
    @staticmethod
    def send_notification(
        event_type: str,
        priority: str = 'medium',
        event_data: Dict[str, Any] = None,
        force_send: bool = False
    ) -> Dict[str, Any]:
        """
        Send notifications for an event with fallback mechanisms.
        
        Args:
            event_type: Type of event triggering notification
            priority: Event priority level
            event_data: Additional event data
            force_send: Skip throttling and conditions
            
        Returns:
            Dictionary with delivery results
        """
        from ..services.settings_service import NotificationManager
        
        results = {
            'success': True,
            'notifications_sent': 0,
            'notifications_failed': 0,
            'delivery_results': [],
            'errors': [],
        }
        
        try:
            # Get notification settings that should be triggered
            if force_send:
                settings_to_trigger = NotificationManager.get_notification_settings(event_type=event_type)
            else:
                settings_to_trigger = NotificationManager.should_send_notification(
                    event_type, priority, event_data
                )
            
            if not settings_to_trigger:
                results['message'] = 'No notification settings matched the event criteria'
                return results
            
            # Send notifications for each matching setting
            for setting in settings_to_trigger:
                delivery_result = NotificationDeliveryService._deliver_notification(
                    setting, event_data or {}
                )
                
                results['delivery_results'].append(delivery_result)
                
                if delivery_result['success']:
                    results['notifications_sent'] += 1
                    setting.record_sent()
                else:
                    results['notifications_failed'] += 1
                    setting.record_failed()
                    results['errors'].append(delivery_result['error'])
            
            # Update overall success status
            results['success'] = results['notifications_failed'] == 0
        
        except Exception as e:
            logger.error(f"Error in notification delivery service: {e}")
            results['success'] = False
            results['errors'].append(str(e))
        
        return results
    
    @staticmethod
    def _deliver_notification(setting: NotificationSetting, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deliver a single notification with fallback mechanisms.
        
        Args:
            setting: NotificationSetting instance
            event_data: Event data for template rendering
            
        Returns:
            Dictionary with delivery result
        """
        result = {
            'success': False,
            'setting_id': setting.id,
            'setting_name': setting.name,
            'notification_type': setting.notification_type,
            'recipients': setting.recipients,
            'attempts': 0,
            'error': None,
            'delivery_method': None,
        }
        
        # Render message content
        try:
            subject, message = setting.render_message(event_data)
        except Exception as e:
            result['error'] = f"Template rendering failed: {str(e)}"
            return result
        
        # Try primary delivery method
        max_attempts = setting.retry_attempts or 3
        delay_minutes = setting.retry_delay_minutes or 5
        
        for attempt in range(max_attempts):
            result['attempts'] = attempt + 1
            
            try:
                if setting.notification_type == 'email':
                    delivery_success = NotificationDeliveryService._send_email(
                        setting, subject, message, event_data
                    )
                elif setting.notification_type == 'webhook':
                    delivery_success = NotificationDeliveryService._send_webhook(
                        setting, subject, message, event_data
                    )
                else:
                    # Placeholder for other notification types
                    delivery_success = False
                    result['error'] = f"Notification type '{setting.notification_type}' not implemented"
                
                if delivery_success:
                    result['success'] = True
                    result['delivery_method'] = setting.notification_type
                    break
                
            except Exception as e:
                result['error'] = str(e)
                logger.warning(f"Notification delivery attempt {attempt + 1} failed: {e}")
            
            # Wait before retry (except on last attempt)
            if attempt < max_attempts - 1:
                # Use shorter delay for testing, longer for production
                delay_seconds = min(delay_minutes * 60, 5)  # Max 5 seconds for testing
                time.sleep(delay_seconds)
        
        # Try fallback methods if primary failed
        if not result['success']:
            fallback_result = NotificationDeliveryService._try_fallback_delivery(
                setting, subject, message, event_data
            )
            if fallback_result['success']:
                result.update(fallback_result)
        
        return result
    
    @staticmethod
    def _send_email(
        setting: NotificationSetting,
        subject: str,
        message: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """
        Send email notification.
        
        Args:
            setting: NotificationSetting instance
            subject: Email subject
            message: Email message
            event_data: Event data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get email configuration
            email_config = EmailServerConfiguration.get_email_config()
            
            # Create email backend
            backend = EmailBackend(
                host=email_config.get('host'),
                port=int(email_config.get('port', 587)),
                username=email_config.get('username'),
                password=email_config.get('password'),
                use_tls=email_config.get('use_tls', True),
                use_ssl=email_config.get('use_ssl', False),
                timeout=int(email_config.get('timeout', 30)),
            )
            
            # Send email
            from_email = email_config.get('from_email', settings.DEFAULT_FROM_EMAIL)
            
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=setting.recipients,
                connection=backend,
                fail_silently=False,
            )
            
            logger.info(f"Email notification sent successfully: {setting.name}")
            return True
        
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return False
    
    @staticmethod
    def _send_webhook(
        setting: NotificationSetting,
        subject: str,
        message: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """
        Send webhook notification.
        
        Args:
            setting: NotificationSetting instance
            subject: Notification subject
            message: Notification message
            event_data: Event data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import requests
            
            webhook_config = setting.delivery_config
            webhook_url = webhook_config.get('url')
            
            if not webhook_url:
                logger.error("Webhook URL not configured")
                return False
            
            payload = {
                'subject': subject,
                'message': message,
                'event_type': setting.event_type,
                'priority': event_data.get('priority', 'medium'),
                'timestamp': timezone.now().isoformat(),
                'event_data': event_data,
            }
            
            headers = webhook_config.get('headers', {})
            timeout = webhook_config.get('timeout', 30)
            
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            
            response.raise_for_status()
            
            logger.info(f"Webhook notification sent successfully: {setting.name}")
            return True
        
        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")
            return False
    
    @staticmethod
    def _try_fallback_delivery(
        setting: NotificationSetting,
        subject: str,
        message: str,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Try fallback delivery methods.
        
        Args:
            setting: NotificationSetting instance
            subject: Notification subject
            message: Notification message
            event_data: Event data
            
        Returns:
            Dictionary with fallback result
        """
        result = {
            'success': False,
            'delivery_method': None,
            'error': 'No fallback methods available',
        }
        
        # Try logging as fallback for critical notifications
        if event_data.get('priority') == 'critical':
            try:
                logger.critical(
                    f"CRITICAL NOTIFICATION FALLBACK - {subject}\n"
                    f"Message: {message}\n"
                    f"Recipients: {setting.recipients}\n"
                    f"Event Data: {json.dumps(event_data, indent=2)}"
                )
                result['success'] = True
                result['delivery_method'] = 'log_fallback'
                result['error'] = None
            except Exception as e:
                result['error'] = f"Even log fallback failed: {str(e)}"
        
        return result
    
    @staticmethod
    def get_delivery_statistics(days: int = 30) -> Dict[str, Any]:
        """
        Get notification delivery statistics.
        
        Args:
            days: Number of days to include in statistics
            
        Returns:
            Dictionary with delivery statistics
        """
        from django.db.models import Sum, Count, Q
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Get statistics from notification settings
        stats = NotificationSetting.objects.filter(
            updated_at__gte=cutoff_date
        ).aggregate(
            total_sent=Sum('total_sent'),
            total_failed=Sum('total_failed'),
            active_settings=Count('id', filter=Q(is_enabled=True)),
            inactive_settings=Count('id', filter=Q(is_enabled=False)),
        )
        
        # Calculate success rate
        total_attempts = (stats['total_sent'] or 0) + (stats['total_failed'] or 0)
        success_rate = (stats['total_sent'] / total_attempts * 100) if total_attempts > 0 else 0
        
        return {
            'period_days': days,
            'total_sent': stats['total_sent'] or 0,
            'total_failed': stats['total_failed'] or 0,
            'success_rate': round(success_rate, 2),
            'active_settings': stats['active_settings'] or 0,
            'inactive_settings': stats['inactive_settings'] or 0,
            'total_settings': (stats['active_settings'] or 0) + (stats['inactive_settings'] or 0),
        }