"""
Notification management views for super admin panel.
Implements email server configuration, alert thresholds, and delivery status management.
"""
import json
import logging
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from .views import SuperAdminRequiredMixin
from .services.notification_service import (
    EmailServerConfiguration,
    AlertThresholdManager,
    NotificationDeliveryService
)

logger = logging.getLogger(__name__)


class NotificationManagementView(SuperAdminRequiredMixin, TemplateView):
    """
    Main notification management interface.
    """
    template_name = 'admin_panel/settings/notifications.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get initial data for the interface
        try:
            email_config = EmailServerConfiguration.get_email_config()
            alert_thresholds = AlertThresholdManager.get_alert_thresholds()
            notification_recipients = AlertThresholdManager.get_notification_recipients()
            delivery_stats = NotificationDeliveryService.get_delivery_statistics()
            
            context.update({
                'email_config': email_config,
                'alert_thresholds': alert_thresholds,
                'notification_recipients': notification_recipients,
                'delivery_stats': delivery_stats,
            })
        except Exception as e:
            logger.error(f"Error loading notification management data: {e}")
            context.update({
                'email_config': {},
                'alert_thresholds': {},
                'notification_recipients': {},
                'delivery_stats': {},
            })
        
        return context


class EmailConfigurationAPIView(SuperAdminRequiredMixin, View):
    """
    API endpoint for email server configuration management.
    """
    
    def get(self, request):
        """Get current email configuration and status."""
        try:
            config = EmailServerConfiguration.get_email_config()
            
            # Test connection status
            test_result = EmailServerConfiguration.test_connection(config)
            
            return JsonResponse({
                'success': True,
                'config': config,
                'status': {
                    'connected': test_result['success'],
                    'last_test': test_result['timestamp'],
                    'error': test_result.get('error')
                }
            })
        except Exception as e:
            logger.error(f"Error getting email configuration: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def post(self, request):
        """Update email server configuration."""
        try:
            data = json.loads(request.body)
            
            # Update email configuration
            result = EmailServerConfiguration.update_email_config(
                config=data,
                user=request.user
            )
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'message': _('تنظیمات ایمیل با موفقیت به‌روزرسانی شد'),
                    'updated_settings': result['updated_settings'],
                    'status': {
                        'connected': result.get('test_result', {}).get('success', False),
                        'last_test': timezone.now().isoformat(),
                        'error': result.get('test_result', {}).get('error')
                    }
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': _('خطا در به‌روزرسانی تنظیمات ایمیل'),
                    'errors': result['errors']
                }, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': _('فرمت داده‌های ارسالی نامعتبر است')
            }, status=400)
        except Exception as e:
            logger.error(f"Error updating email configuration: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class EmailTestAPIView(SuperAdminRequiredMixin, View):
    """
    API endpoint for testing email server connection.
    """
    
    def post(self, request):
        """Test email server connection."""
        try:
            data = json.loads(request.body)
            config = data.get('config')
            
            if not config:
                # Use current configuration if none provided
                config = EmailServerConfiguration.get_email_config()
            
            # Test connection
            result = EmailServerConfiguration.test_connection(config)
            
            return JsonResponse({
                'success': True,
                'result': result
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': _('فرمت داده‌های ارسالی نامعتبر است')
            }, status=400)
        except Exception as e:
            logger.error(f"Error testing email connection: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class SendTestEmailAPIView(SuperAdminRequiredMixin, View):
    """
    API endpoint for sending test emails.
    """
    
    def post(self, request):
        """Send a test email."""
        try:
            data = json.loads(request.body)
            recipient = data.get('recipient')
            config = data.get('config')
            
            if not recipient:
                return JsonResponse({
                    'success': False,
                    'error': _('آدرس ایمیل گیرنده الزامی است')
                }, status=400)
            
            # Send test email
            result = EmailServerConfiguration.send_test_email(
                recipient=recipient,
                config=config
            )
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'message': _('ایمیل تست با موفقیت ارسال شد'),
                    'result': result
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result['error']
                }, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': _('فرمت داده‌های ارسالی نامعتبر است')
            }, status=400)
        except Exception as e:
            logger.error(f"Error sending test email: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class AlertConfigurationAPIView(SuperAdminRequiredMixin, View):
    """
    API endpoint for alert threshold and recipient management.
    """
    
    def get(self, request):
        """Get current alert configuration."""
        try:
            thresholds = AlertThresholdManager.get_alert_thresholds()
            recipients = AlertThresholdManager.get_notification_recipients()
            
            return JsonResponse({
                'success': True,
                'thresholds': thresholds,
                'recipients': recipients
            })
        except Exception as e:
            logger.error(f"Error getting alert configuration: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def post(self, request):
        """Update alert configuration."""
        try:
            data = json.loads(request.body)
            thresholds = data.get('thresholds', {})
            recipients = data.get('recipients', {})
            
            results = {
                'success': True,
                'threshold_result': None,
                'recipient_result': None,
                'errors': {}
            }
            
            # Update thresholds if provided
            if thresholds:
                threshold_result = AlertThresholdManager.update_alert_thresholds(
                    thresholds=thresholds,
                    user=request.user
                )
                results['threshold_result'] = threshold_result
                if not threshold_result['success']:
                    results['success'] = False
                    results['errors'].update(threshold_result['errors'])
            
            # Update recipients if provided
            if recipients:
                recipient_result = AlertThresholdManager.update_notification_recipients(
                    recipients=recipients,
                    user=request.user
                )
                results['recipient_result'] = recipient_result
                if not recipient_result['success']:
                    results['success'] = False
                    results['errors'].update(recipient_result['errors'])
            
            if results['success']:
                return JsonResponse({
                    'success': True,
                    'message': _('تنظیمات هشدار با موفقیت به‌روزرسانی شد'),
                    'results': results
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': _('خطا در به‌روزرسانی تنظیمات هشدار'),
                    'errors': results['errors']
                }, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': _('فرمت داده‌های ارسالی نامعتبر است')
            }, status=400)
        except Exception as e:
            logger.error(f"Error updating alert configuration: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class DeliveryStatisticsAPIView(SuperAdminRequiredMixin, View):
    """
    API endpoint for notification delivery statistics.
    """
    
    def get(self, request):
        """Get notification delivery statistics."""
        try:
            days = int(request.GET.get('days', 30))
            
            # Get delivery statistics
            stats = NotificationDeliveryService.get_delivery_statistics(days=days)
            
            # Get recent notifications (last 24 hours)
            recent_notifications = self._get_recent_notifications()
            
            return JsonResponse({
                'success': True,
                'stats': stats,
                'recent': recent_notifications
            })
        except Exception as e:
            logger.error(f"Error getting delivery statistics: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def _get_recent_notifications(self):
        """Get recent notification delivery attempts."""
        try:
            from .models import NotificationSetting
            
            # Get notifications from the last 24 hours
            cutoff_time = timezone.now() - timedelta(hours=24)
            
            # This is a simplified implementation
            # In a real system, you'd have a NotificationDelivery model
            recent = []
            
            # Get recent notification settings that were used
            recent_settings = NotificationSetting.objects.filter(
                updated_at__gte=cutoff_time
            ).order_by('-updated_at')[:20]
            
            for setting in recent_settings:
                # Mock recent notification data
                # In production, this would come from actual delivery logs
                recent.append({
                    'id': setting.id,
                    'timestamp': setting.updated_at.isoformat(),
                    'type': setting.get_notification_type_display(),
                    'recipient': setting.recipients[0] if setting.recipients else 'N/A',
                    'status': 'sent' if setting.is_enabled else 'disabled',
                    'details': f"Event: {setting.event_type}"
                })
            
            return recent
            
        except Exception as e:
            logger.error(f"Error getting recent notifications: {e}")
            return []


class NotificationTestAPIView(SuperAdminRequiredMixin, View):
    """
    API endpoint for testing notification delivery.
    """
    
    def post(self, request):
        """Test notification delivery."""
        try:
            data = json.loads(request.body)
            event_type = data.get('event_type', 'test')
            priority = data.get('priority', 'medium')
            event_data = data.get('event_data', {})
            
            # Add test flag to event data
            event_data['test_notification'] = True
            event_data['test_user'] = request.user.username
            event_data['test_timestamp'] = timezone.now().isoformat()
            
            # Send test notification
            result = NotificationDeliveryService.send_notification(
                event_type=event_type,
                priority=priority,
                event_data=event_data,
                force_send=True  # Skip throttling for tests
            )
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'message': _('تست اعلان با موفقیت انجام شد'),
                    'result': result
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': _('خطا در تست اعلان'),
                    'errors': result['errors']
                }, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': _('فرمت داده‌های ارسالی نامعتبر است')
            }, status=400)
        except Exception as e:
            logger.error(f"Error testing notification: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)