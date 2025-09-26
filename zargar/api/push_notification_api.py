"""
Push notification API for ZARGAR jewelry SaaS platform.
Handles mobile device registration and push notification delivery.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, throttle_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from django.conf import settings
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from zargar.core.permissions import TenantPermission, AllRolesPermission, OwnerPermission
from zargar.core.notification_services import (
    PushNotificationSystem, NotificationScheduler,
    send_payment_reminder, send_birthday_greeting, send_appointment_reminder
)
from zargar.core.notification_models import (
    Notification, NotificationTemplate, NotificationProvider, MobileDevice
)
from zargar.customers.models import Customer
from zargar.core.models import User
from .mobile_serializers import (
    MobileNotificationSerializer, MobileDeviceRegistrationSerializer
)
from .throttling import TenantAPIThrottle


class MobileDeviceViewSet(viewsets.ViewSet):
    """
    ViewSet for mobile device management and push notification setup.
    """
    permission_classes = [IsAuthenticated, TenantPermission, AllRolesPermission]
    throttle_classes = [TenantAPIThrottle]
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Register mobile device for push notifications.
        Stores device token and user preferences.
        """
        try:
            serializer = MobileDeviceRegistrationSerializer(data=request.data)
            if serializer.is_valid():
                device_data = serializer.validated_data
                
                # Check if device already exists
                try:
                    device = MobileDevice.objects.get(
                        user=request.user,
                        device_id=device_data['device_id']
                    )
                    # Update existing device
                    for field, value in device_data.items():
                        setattr(device, field, value)
                    device.last_active_at = timezone.now()
                    device.save()
                    
                    action_type = 'updated'
                except MobileDevice.DoesNotExist:
                    # Create new device
                    device = MobileDevice.objects.create(
                        user=request.user,
                        **device_data,
                        last_active_at=timezone.now(),
                        is_active=True
                    )
                    action_type = 'created'
                
                return Response({
                    'success': True,
                    'device_id': device.device_id,
                    'registration_id': str(device.id),
                    'action': action_type,
                    'message': _('Device registered successfully')
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def unregister(self, request):
        """
        Unregister mobile device from push notifications.
        """
        try:
            device_id = request.data.get('device_id')
            if not device_id:
                return Response({
                    'success': False,
                    'error': _('Device ID is required')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                device = MobileDevice.objects.get(
                    user=request.user,
                    device_id=device_id
                )
                device.is_active = False
                device.unregistered_at = timezone.now()
                device.save(update_fields=['is_active', 'unregistered_at'])
                
                return Response({
                    'success': True,
                    'message': _('Device unregistered successfully')
                }, status=status.HTTP_200_OK)
                
            except MobileDevice.DoesNotExist:
                return Response({
                    'success': False,
                    'error': _('Device not found')
                }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def update_preferences(self, request):
        """
        Update notification preferences for mobile device.
        """
        try:
            device_id = request.data.get('device_id')
            preferences = request.data.get('preferences', {})
            
            if not device_id:
                return Response({
                    'success': False,
                    'error': _('Device ID is required')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                device = MobileDevice.objects.get(
                    user=request.user,
                    device_id=device_id
                )
                
                # Update notification preferences
                valid_preferences = [
                    'enable_push_notifications',
                    'enable_payment_reminders',
                    'enable_appointment_reminders',
                    'enable_promotions',
                    'enable_system_notifications'
                ]
                
                for pref in valid_preferences:
                    if pref in preferences:
                        setattr(device, pref, preferences[pref])
                
                device.save()
                
                return Response({
                    'success': True,
                    'message': _('Preferences updated successfully')
                }, status=status.HTTP_200_OK)
                
            except MobileDevice.DoesNotExist:
                return Response({
                    'success': False,
                    'error': _('Device not found')
                }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def list_devices(self, request):
        """
        List registered devices for current user.
        """
        try:
            devices = MobileDevice.objects.filter(
                user=request.user,
                is_active=True
            ).order_by('-last_active_at')
            
            device_list = []
            for device in devices:
                device_list.append({
                    'device_id': device.device_id,
                    'device_type': device.device_type,
                    'device_model': device.device_model,
                    'app_version': device.app_version,
                    'last_active_at': device.last_active_at.isoformat(),
                    'preferences': {
                        'enable_push_notifications': device.enable_push_notifications,
                        'enable_payment_reminders': device.enable_payment_reminders,
                        'enable_appointment_reminders': device.enable_appointment_reminders,
                        'enable_promotions': device.enable_promotions,
                        'enable_system_notifications': device.enable_system_notifications,
                    }
                })
            
            return Response({
                'success': True,
                'devices': device_list
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, TenantPermission, AllRolesPermission])
@throttle_classes([TenantAPIThrottle])
def send_push_notification(request):
    """
    Send push notification to mobile devices.
    Supports both individual and bulk notifications.
    """
    try:
        serializer = MobileNotificationSerializer(data=request.data)
        if serializer.is_valid():
            notification_data = serializer.validated_data
            
            # Determine recipients
            recipient_type = request.data.get('recipient_type', 'user')
            recipient_ids = request.data.get('recipient_ids', [])
            
            if not recipient_ids:
                # Send to current user if no recipients specified
                recipient_ids = [request.user.id]
                recipient_type = 'user'
            
            # Use notification system
            notification_system = PushNotificationSystem()
            
            created_notifications = []
            for recipient_id in recipient_ids:
                notifications = notification_system.create_notification(
                    template_type=notification_data['notification_type'],
                    recipient_type=recipient_type,
                    recipient_id=recipient_id,
                    context={
                        'title': notification_data['title'],
                        'message': notification_data['message'],
                        'custom_data': notification_data.get('custom_data', {}),
                        'action_url': notification_data.get('action_url', ''),
                    },
                    delivery_methods=['push'],
                    scheduled_at=notification_data.get('scheduled_at'),
                    priority=notification_data['priority']
                )
                created_notifications.extend(notifications)
            
            # Send notifications immediately if not scheduled
            sent_count = 0
            if not notification_data.get('scheduled_at') or notification_data['scheduled_at'] <= timezone.now():
                for notification in created_notifications:
                    if notification_system.send_notification(notification):
                        sent_count += 1
            
            return Response({
                'success': True,
                'notifications_created': len(created_notifications),
                'notifications_sent': sent_count,
                'message': _('Notifications processed successfully')
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, TenantPermission, AllRolesPermission])
@throttle_classes([TenantAPIThrottle])
def send_payment_reminder_notification(request):
    """
    Send payment reminder notification to customer.
    Specialized endpoint for gold installment payment reminders.
    """
    try:
        customer_id = request.data.get('customer_id')
        contract_number = request.data.get('contract_number')
        amount = request.data.get('amount')
        due_date = request.data.get('due_date')
        
        if not all([customer_id, contract_number, amount, due_date]):
            return Response({
                'success': False,
                'error': _('Missing required fields: customer_id, contract_number, amount, due_date')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate customer exists
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return Response({
                'success': False,
                'error': _('Customer not found')
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Send payment reminder
        notifications = send_payment_reminder(
            customer_id=customer_id,
            contract_number=contract_number,
            amount=float(amount),
            due_date=due_date
        )
        
        return Response({
            'success': True,
            'notifications_created': len(notifications),
            'customer_name': customer.full_persian_name,
            'message': _('Payment reminder sent successfully')
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, TenantPermission, AllRolesPermission])
@throttle_classes([TenantAPIThrottle])
def send_birthday_notification(request):
    """
    Send birthday greeting notification to customer.
    """
    try:
        customer_id = request.data.get('customer_id')
        
        if not customer_id:
            return Response({
                'success': False,
                'error': _('Customer ID is required')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate customer exists
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return Response({
                'success': False,
                'error': _('Customer not found')
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Send birthday greeting
        notifications = send_birthday_greeting(customer_id=customer_id)
        
        return Response({
            'success': True,
            'notifications_created': len(notifications),
            'customer_name': customer.full_persian_name,
            'message': _('Birthday greeting sent successfully')
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, TenantPermission, AllRolesPermission])
@throttle_classes([TenantAPIThrottle])
def send_appointment_reminder_notification(request):
    """
    Send appointment reminder notification to customer.
    """
    try:
        customer_id = request.data.get('customer_id')
        appointment_date = request.data.get('appointment_date')
        appointment_time = request.data.get('appointment_time')
        
        if not all([customer_id, appointment_date, appointment_time]):
            return Response({
                'success': False,
                'error': _('Missing required fields: customer_id, appointment_date, appointment_time')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate customer exists
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return Response({
                'success': False,
                'error': _('Customer not found')
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Send appointment reminder
        notifications = send_appointment_reminder(
            customer_id=customer_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time
        )
        
        return Response({
            'success': True,
            'notifications_created': len(notifications),
            'customer_name': customer.full_persian_name,
            'message': _('Appointment reminder sent successfully')
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, TenantPermission, AllRolesPermission])
@throttle_classes([TenantAPIThrottle])
def get_notification_history(request):
    """
    Get notification history for current user or customer.
    """
    try:
        recipient_type = request.GET.get('recipient_type', 'user')
        recipient_id = request.GET.get('recipient_id', request.user.id)
        limit = min(int(request.GET.get('limit', 50)), 100)  # Max 100 notifications
        
        # Get notifications
        notifications = Notification.objects.filter(
            recipient_type=recipient_type,
            recipient_id=recipient_id
        ).order_by('-created_at')[:limit]
        
        notification_list = []
        for notification in notifications:
            notification_list.append({
                'id': notification.id,
                'title': notification.title,
                'content': notification.content,
                'notification_type': notification.template.template_type if notification.template else 'custom',
                'delivery_method': notification.delivery_method,
                'status': notification.status,
                'priority': notification.priority,
                'created_at': notification.created_at.isoformat(),
                'sent_at': notification.sent_at.isoformat() if notification.sent_at else None,
                'read_at': notification.read_at.isoformat() if notification.read_at else None,
                'is_read': notification.is_read,
            })
        
        return Response({
            'success': True,
            'notifications': notification_list,
            'total_count': len(notification_list)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, TenantPermission, AllRolesPermission])
@throttle_classes([TenantAPIThrottle])
def mark_notification_read(request):
    """
    Mark notification as read.
    """
    try:
        notification_id = request.data.get('notification_id')
        
        if not notification_id:
            return Response({
                'success': False,
                'error': _('Notification ID is required')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient_type='user',
                recipient_id=request.user.id
            )
            
            if not notification.is_read:
                notification.mark_as_read()
            
            return Response({
                'success': True,
                'message': _('Notification marked as read')
            }, status=status.HTTP_200_OK)
            
        except Notification.DoesNotExist:
            return Response({
                'success': False,
                'error': _('Notification not found')
            }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, TenantPermission, OwnerPermission])
@throttle_classes([TenantAPIThrottle])
def get_notification_statistics(request):
    """
    Get notification statistics for tenant.
    Only available to owners for analytics.
    """
    try:
        # Get date range
        days = int(request.GET.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Get notification statistics
        total_notifications = Notification.objects.filter(
            created_at__gte=start_date
        ).count()
        
        sent_notifications = Notification.objects.filter(
            created_at__gte=start_date,
            status='sent'
        ).count()
        
        failed_notifications = Notification.objects.filter(
            created_at__gte=start_date,
            status='failed'
        ).count()
        
        # Get statistics by type
        notification_types = Notification.objects.filter(
            created_at__gte=start_date
        ).values('template__template_type').distinct()
        
        type_statistics = []
        for nt in notification_types:
            template_type = nt['template__template_type']
            if template_type:
                count = Notification.objects.filter(
                    created_at__gte=start_date,
                    template__template_type=template_type
                ).count()
                type_statistics.append({
                    'type': template_type,
                    'count': count
                })
        
        # Get delivery method statistics
        delivery_methods = Notification.objects.filter(
            created_at__gte=start_date
        ).values('delivery_method').distinct()
        
        method_statistics = []
        for dm in delivery_methods:
            method = dm['delivery_method']
            count = Notification.objects.filter(
                created_at__gte=start_date,
                delivery_method=method
            ).count()
            method_statistics.append({
                'method': method,
                'count': count
            })
        
        statistics = {
            'period_days': days,
            'total_notifications': total_notifications,
            'sent_notifications': sent_notifications,
            'failed_notifications': failed_notifications,
            'success_rate': (sent_notifications / total_notifications * 100) if total_notifications > 0 else 0,
            'notification_types': type_statistics,
            'delivery_methods': method_statistics,
            'generated_at': timezone.now().isoformat()
        }
        
        return Response({
            'success': True,
            'statistics': statistics
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, TenantPermission, AllRolesPermission])
@throttle_classes([TenantAPIThrottle])
def test_push_notification(request):
    """
    Test push notification functionality.
    Sends a test notification to verify setup.
    """
    try:
        device_id = request.data.get('device_id')
        
        if not device_id:
            return Response({
                'success': False,
                'error': _('Device ID is required for testing')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if device is registered
        try:
            device = MobileDevice.objects.get(
                user=request.user,
                device_id=device_id,
                is_active=True
            )
        except MobileDevice.DoesNotExist:
            return Response({
                'success': False,
                'error': _('Device not found or not active')
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Send test notification
        notification_system = PushNotificationSystem()
        notifications = notification_system.create_notification(
            template_type='system_test',
            recipient_type='user',
            recipient_id=request.user.id,
            context={
                'title': 'تست اعلان',
                'message': 'این یک پیام تست برای بررسی عملکرد سیستم اعلانات است.',
                'test_timestamp': timezone.now().isoformat(),
            },
            delivery_methods=['push']
        )
        
        # Send immediately
        sent_count = 0
        for notification in notifications:
            if notification_system.send_notification(notification):
                sent_count += 1
        
        return Response({
            'success': True,
            'test_sent': sent_count > 0,
            'device_type': device.device_type,
            'message': _('Test notification sent successfully') if sent_count > 0 else _('Test notification failed')
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)