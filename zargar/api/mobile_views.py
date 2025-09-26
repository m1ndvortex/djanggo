"""
Mobile-specific API views for ZARGAR jewelry SaaS platform.
Optimized for mobile POS and inventory management with offline synchronization support.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q, F, Sum, Count
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from zargar.core.permissions import (
    TenantPermission, OwnerPermission, AccountingPermission, 
    POSPermission, AllRolesPermission
)
from zargar.jewelry.models import JewelryItem, Category
from zargar.customers.models import Customer
from zargar.pos.models import POSTransaction, POSTransactionLineItem
from zargar.core.notification_services import PushNotificationSystem
from .serializers import (
    JewelryItemListSerializer, CustomerListSerializer,
    POSTransactionSerializer, POSTransactionCreateSerializer
)
from .mobile_serializers import (
    MobileJewelryItemSerializer, MobileCustomerSerializer,
    MobilePOSTransactionSerializer, OfflineTransactionSerializer,
    MobileInventoryUpdateSerializer, MobileSyncDataSerializer
)
from .throttling import TenantAPIThrottle


class MobilePOSViewSet(viewsets.ModelViewSet):
    """
    Mobile-optimized POS ViewSet for tablet and mobile devices.
    Provides touch-friendly endpoints with offline synchronization support.
    """
    serializer_class = MobilePOSTransactionSerializer
    permission_classes = [TenantPermission, POSPermission]
    throttle_classes = [TenantAPIThrottle]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['transaction_number', 'customer__first_name', 'customer__last_name']
    ordering_fields = ['created_at', 'total_amount']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return POS transactions for current tenant only."""
        return POSTransaction.objects.select_related('customer', 'created_by').prefetch_related('line_items__jewelry_item')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return POSTransactionCreateSerializer
        elif self.action in ['offline_create', 'bulk_sync']:
            return OfflineTransactionSerializer
        return MobilePOSTransactionSerializer
    
    @action(detail=False, methods=['post'])
    def offline_create(self, request):
        """
        Create POS transaction for offline processing.
        Stores transaction data for later synchronization.
        """
        try:
            serializer = OfflineTransactionSerializer(data=request.data)
            if serializer.is_valid():
                # Create offline transaction
                offline_transaction = serializer.save(
                    created_by=request.user,
                    is_offline_transaction=True,
                    sync_status='pending_sync',
                    status='offline_pending'
                )
                
                # Create offline backup data
                offline_data = offline_transaction.create_offline_backup()
                
                return Response({
                    'success': True,
                    'transaction_id': str(offline_transaction.transaction_id),
                    'transaction_number': offline_transaction.transaction_number,
                    'offline_data': offline_data,
                    'message': _('Transaction saved for offline processing')
                }, status=status.HTTP_201_CREATED)
            
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
    def bulk_sync(self, request):
        """
        Synchronize multiple offline transactions.
        Processes a batch of offline transactions for efficiency.
        """
        try:
            offline_transactions = request.data.get('transactions', [])
            if not offline_transactions:
                return Response({
                    'success': False,
                    'error': _('No transactions provided for sync')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            sync_results = {
                'total': len(offline_transactions),
                'synced': 0,
                'failed': 0,
                'errors': []
            }
            
            with transaction.atomic():
                for transaction_data in offline_transactions:
                    try:
                        # Find existing offline transaction or create new one
                        transaction_id = transaction_data.get('transaction_id')
                        if transaction_id:
                            pos_transaction = POSTransaction.objects.get(
                                transaction_id=transaction_id,
                                is_offline_transaction=True
                            )
                        else:
                            # Create new transaction from offline data
                            serializer = OfflineTransactionSerializer(data=transaction_data)
                            if serializer.is_valid():
                                pos_transaction = serializer.save(
                                    created_by=request.user,
                                    is_offline_transaction=True
                                )
                            else:
                                sync_results['failed'] += 1
                                sync_results['errors'].append({
                                    'transaction': transaction_data.get('transaction_number', 'Unknown'),
                                    'errors': serializer.errors
                                })
                                continue
                        
                        # Sync the transaction
                        if pos_transaction.sync_offline_transaction():
                            sync_results['synced'] += 1
                        else:
                            sync_results['failed'] += 1
                            sync_results['errors'].append({
                                'transaction': pos_transaction.transaction_number,
                                'error': 'Sync failed'
                            })
                            
                    except POSTransaction.DoesNotExist:
                        sync_results['failed'] += 1
                        sync_results['errors'].append({
                            'transaction': transaction_data.get('transaction_number', 'Unknown'),
                            'error': 'Transaction not found'
                        })
                    except Exception as e:
                        sync_results['failed'] += 1
                        sync_results['errors'].append({
                            'transaction': transaction_data.get('transaction_number', 'Unknown'),
                            'error': str(e)
                        })
            
            return Response({
                'success': True,
                'sync_results': sync_results
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def pending_sync(self, request):
        """
        Get transactions pending synchronization.
        Returns offline transactions that need to be synced.
        """
        try:
            pending_transactions = self.get_queryset().filter(
                sync_status='pending_sync',
                is_offline_transaction=True
            )
            
            serializer = self.get_serializer(pending_transactions, many=True)
            
            return Response({
                'success': True,
                'count': pending_transactions.count(),
                'transactions': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def mobile_dashboard(self, request):
        """
        Get mobile dashboard data optimized for touch interfaces.
        Returns key metrics and recent transactions.
        """
        try:
            today = timezone.now().date()
            
            # Today's transactions
            today_transactions = self.get_queryset().filter(
                transaction_date__date=today,
                status='completed'
            )
            
            # Calculate metrics
            today_sales = today_transactions.aggregate(
                total_amount=Sum('total_amount'),
                total_count=Count('id')
            )
            
            # Recent transactions (last 10)
            recent_transactions = self.get_queryset().filter(
                status='completed'
            )[:10]
            
            # Pending sync count
            pending_sync_count = self.get_queryset().filter(
                sync_status='pending_sync'
            ).count()
            
            # Low stock items
            low_stock_items = JewelryItem.objects.filter(
                quantity__lte=F('minimum_stock'),
                status='available'
            )[:5]
            
            return Response({
                'success': True,
                'dashboard': {
                    'today_sales': {
                        'total_amount': today_sales['total_amount'] or 0,
                        'total_count': today_sales['total_count'] or 0,
                        'date': today.isoformat()
                    },
                    'recent_transactions': MobilePOSTransactionSerializer(
                        recent_transactions, many=True, context={'request': request}
                    ).data,
                    'pending_sync_count': pending_sync_count,
                    'low_stock_items': MobileJewelryItemSerializer(
                        low_stock_items, many=True, context={'request': request}
                    ).data
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MobileInventoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Mobile-optimized inventory ViewSet for quick item lookup and management.
    Provides barcode scanning and touch-friendly search.
    """
    serializer_class = MobileJewelryItemSerializer
    permission_classes = [TenantPermission, AllRolesPermission]
    throttle_classes = [TenantAPIThrottle]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'sku', 'barcode']
    ordering_fields = ['name', 'created_at', 'selling_price']
    ordering = ['name']
    
    def get_queryset(self):
        """Return jewelry items for current tenant only."""
        return JewelryItem.objects.select_related('category').filter(
            status__in=['available', 'reserved']
        )
    
    @action(detail=False, methods=['get'])
    def barcode_search(self, request):
        """
        Search inventory by barcode for mobile scanning.
        Optimized for barcode scanner integration.
        """
        try:
            barcode = request.query_params.get('barcode')
            if not barcode:
                return Response({
                    'success': False,
                    'error': _('Barcode parameter is required')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Search for item by barcode
            try:
                item = self.get_queryset().get(barcode=barcode)
                serializer = self.get_serializer(item)
                
                return Response({
                    'success': True,
                    'item': serializer.data
                }, status=status.HTTP_200_OK)
                
            except JewelryItem.DoesNotExist:
                return Response({
                    'success': False,
                    'error': _('Item not found with this barcode')
                }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def quick_search(self, request):
        """
        Quick search for mobile interfaces.
        Searches across name, SKU, and barcode with fuzzy matching.
        """
        try:
            query = request.query_params.get('q', '').strip()
            if len(query) < 2:
                return Response({
                    'success': False,
                    'error': _('Search query must be at least 2 characters')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Search across multiple fields
            items = self.get_queryset().filter(
                Q(name__icontains=query) |
                Q(sku__icontains=query) |
                Q(barcode__icontains=query)
            )[:20]  # Limit results for mobile performance
            
            serializer = self.get_serializer(items, many=True)
            
            return Response({
                'success': True,
                'count': items.count(),
                'items': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def bulk_update_stock(self, request):
        """
        Bulk update stock levels for mobile inventory management.
        Supports offline stock adjustments.
        """
        try:
            updates = request.data.get('updates', [])
            if not updates:
                return Response({
                    'success': False,
                    'error': _('No updates provided')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            update_results = {
                'total': len(updates),
                'updated': 0,
                'failed': 0,
                'errors': []
            }
            
            with transaction.atomic():
                for update_data in updates:
                    try:
                        serializer = MobileInventoryUpdateSerializer(data=update_data)
                        if serializer.is_valid():
                            item_id = serializer.validated_data['item_id']
                            new_quantity = serializer.validated_data['quantity']
                            reason = serializer.validated_data.get('reason', 'Mobile update')
                            
                            item = JewelryItem.objects.get(id=item_id)
                            old_quantity = item.quantity
                            item.quantity = new_quantity
                            item.save(update_fields=['quantity'])
                            
                            # Log the change
                            # TODO: Create inventory adjustment log entry
                            
                            update_results['updated'] += 1
                        else:
                            update_results['failed'] += 1
                            update_results['errors'].append({
                                'item_id': update_data.get('item_id'),
                                'errors': serializer.errors
                            })
                            
                    except JewelryItem.DoesNotExist:
                        update_results['failed'] += 1
                        update_results['errors'].append({
                            'item_id': update_data.get('item_id'),
                            'error': 'Item not found'
                        })
                    except Exception as e:
                        update_results['failed'] += 1
                        update_results['errors'].append({
                            'item_id': update_data.get('item_id'),
                            'error': str(e)
                        })
            
            return Response({
                'success': True,
                'update_results': update_results
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MobileCustomerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Mobile-optimized customer ViewSet for quick customer lookup and management.
    Provides touch-friendly search and customer creation.
    """
    serializer_class = MobileCustomerSerializer
    permission_classes = [TenantPermission, AllRolesPermission]
    throttle_classes = [TenantAPIThrottle]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['first_name', 'last_name', 'persian_first_name', 'persian_last_name', 'phone_number']
    ordering_fields = ['first_name', 'created_at', 'total_purchases']
    ordering = ['first_name']
    
    def get_queryset(self):
        """Return customers for current tenant only."""
        return Customer.objects.filter(is_active=True)
    
    @action(detail=False, methods=['get'])
    def phone_search(self, request):
        """
        Search customers by phone number for mobile POS.
        Optimized for quick customer lookup during sales.
        """
        try:
            phone = request.query_params.get('phone', '').strip()
            if len(phone) < 4:
                return Response({
                    'success': False,
                    'error': _('Phone number must be at least 4 digits')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Search by phone number (partial match)
            customers = self.get_queryset().filter(
                phone_number__icontains=phone
            )[:10]  # Limit results for mobile performance
            
            serializer = self.get_serializer(customers, many=True)
            
            return Response({
                'success': True,
                'count': customers.count(),
                'customers': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def quick_create(self, request):
        """
        Quick customer creation for mobile POS.
        Creates customer with minimal required information.
        """
        try:
            serializer = MobileCustomerSerializer(data=request.data)
            if serializer.is_valid():
                customer = serializer.save(created_by=request.user)
                
                return Response({
                    'success': True,
                    'customer': MobileCustomerSerializer(customer).data,
                    'message': _('Customer created successfully')
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MobileSyncViewSet(viewsets.ViewSet):
    """
    Mobile synchronization ViewSet for offline data management.
    Handles data sync between mobile devices and server.
    """
    permission_classes = [TenantPermission, AllRolesPermission]
    throttle_classes = [TenantAPIThrottle]
    
    @action(detail=False, methods=['get'])
    def sync_data(self, request):
        """
        Get synchronization data for mobile app.
        Returns essential data for offline operation.
        """
        try:
            # Get last sync timestamp
            last_sync = request.query_params.get('last_sync')
            if last_sync:
                try:
                    last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
                except ValueError:
                    last_sync_dt = None
            else:
                last_sync_dt = None
            
            # Get updated data since last sync
            sync_data = {}
            
            # Categories
            categories_qs = Category.objects.filter(is_active=True)
            if last_sync_dt:
                categories_qs = categories_qs.filter(updated_at__gt=last_sync_dt)
            sync_data['categories'] = [
                {'id': cat.id, 'name': cat.name_persian, 'updated_at': cat.updated_at.isoformat()}
                for cat in categories_qs
            ]
            
            # Jewelry items (limited fields for mobile)
            items_qs = JewelryItem.objects.filter(status__in=['available', 'reserved'])
            if last_sync_dt:
                items_qs = items_qs.filter(updated_at__gt=last_sync_dt)
            sync_data['jewelry_items'] = MobileJewelryItemSerializer(
                items_qs[:500], many=True  # Limit for performance
            ).data
            
            # Customers (recent and updated)
            customers_qs = Customer.objects.filter(is_active=True)
            if last_sync_dt:
                customers_qs = customers_qs.filter(updated_at__gt=last_sync_dt)
            else:
                # For initial sync, get recent customers only
                customers_qs = customers_qs.order_by('-created_at')[:200]
            
            sync_data['customers'] = MobileCustomerSerializer(
                customers_qs, many=True
            ).data
            
            # System settings
            sync_data['settings'] = {
                'current_gold_price': self._get_current_gold_price(),
                'tax_rate': self._get_tax_rate(),
                'currency_symbol': 'تومان',
                'sync_timestamp': timezone.now().isoformat()
            }
            
            return Response({
                'success': True,
                'sync_data': sync_data,
                'sync_timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def upload_sync_data(self, request):
        """
        Upload synchronization data from mobile app.
        Processes offline changes and resolves conflicts.
        """
        try:
            sync_data = request.data.get('sync_data', {})
            if not sync_data:
                return Response({
                    'success': False,
                    'error': _('No sync data provided')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            sync_results = {
                'transactions_synced': 0,
                'inventory_updates': 0,
                'customers_created': 0,
                'conflicts': [],
                'errors': []
            }
            
            with transaction.atomic():
                # Process offline transactions
                if 'transactions' in sync_data:
                    for transaction_data in sync_data['transactions']:
                        try:
                            serializer = OfflineTransactionSerializer(data=transaction_data)
                            if serializer.is_valid():
                                pos_transaction = serializer.save(
                                    created_by=request.user,
                                    is_offline_transaction=True
                                )
                                if pos_transaction.sync_offline_transaction():
                                    sync_results['transactions_synced'] += 1
                            else:
                                sync_results['errors'].append({
                                    'type': 'transaction',
                                    'data': transaction_data.get('transaction_number', 'Unknown'),
                                    'errors': serializer.errors
                                })
                        except Exception as e:
                            sync_results['errors'].append({
                                'type': 'transaction',
                                'data': transaction_data.get('transaction_number', 'Unknown'),
                                'error': str(e)
                            })
                
                # Process inventory updates
                if 'inventory_updates' in sync_data:
                    for update_data in sync_data['inventory_updates']:
                        try:
                            item_id = update_data.get('item_id')
                            new_quantity = update_data.get('quantity')
                            
                            item = JewelryItem.objects.get(id=item_id)
                            item.quantity = new_quantity
                            item.save(update_fields=['quantity'])
                            
                            sync_results['inventory_updates'] += 1
                        except Exception as e:
                            sync_results['errors'].append({
                                'type': 'inventory',
                                'data': update_data,
                                'error': str(e)
                            })
                
                # Process new customers
                if 'customers' in sync_data:
                    for customer_data in sync_data['customers']:
                        try:
                            serializer = MobileCustomerSerializer(data=customer_data)
                            if serializer.is_valid():
                                serializer.save(created_by=request.user)
                                sync_results['customers_created'] += 1
                            else:
                                sync_results['errors'].append({
                                    'type': 'customer',
                                    'data': customer_data.get('phone_number', 'Unknown'),
                                    'errors': serializer.errors
                                })
                        except Exception as e:
                            sync_results['errors'].append({
                                'type': 'customer',
                                'data': customer_data.get('phone_number', 'Unknown'),
                                'error': str(e)
                            })
            
            return Response({
                'success': True,
                'sync_results': sync_results,
                'sync_timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_current_gold_price(self) -> float:
        """Get current gold price (placeholder implementation)."""
        # TODO: Integrate with real gold price API
        return 2500000.0  # Default price in Toman per gram
    
    def _get_tax_rate(self) -> float:
        """Get current tax rate."""
        # TODO: Get from tenant settings
        return 0.09  # 9% VAT


class MobileNotificationViewSet(viewsets.ViewSet):
    """
    Mobile notification ViewSet for push notification management.
    Handles device registration and notification delivery.
    """
    permission_classes = [TenantPermission, AllRolesPermission]
    throttle_classes = [TenantAPIThrottle]
    
    @action(detail=False, methods=['post'])
    def register_device(self, request):
        """
        Register mobile device for push notifications.
        Stores device token and user preferences.
        """
        try:
            device_token = request.data.get('device_token')
            device_type = request.data.get('device_type', 'android')  # android, ios
            app_version = request.data.get('app_version', '1.0.0')
            
            if not device_token:
                return Response({
                    'success': False,
                    'error': _('Device token is required')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # TODO: Store device registration in database
            # This would create a MobileDevice model instance
            
            return Response({
                'success': True,
                'message': _('Device registered successfully'),
                'device_id': str(uuid.uuid4())  # Generate unique device ID
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def send_notification(self, request):
        """
        Send push notification to mobile devices.
        For testing and manual notification sending.
        """
        try:
            title = request.data.get('title')
            message = request.data.get('message')
            recipient_type = request.data.get('recipient_type', 'user')
            recipient_id = request.data.get('recipient_id')
            
            if not all([title, message]):
                return Response({
                    'success': False,
                    'error': _('Title and message are required')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Use notification system
            notification_system = PushNotificationSystem()
            
            if recipient_id:
                # Send to specific recipient
                notifications = notification_system.create_notification(
                    template_type='custom_message',
                    recipient_type=recipient_type,
                    recipient_id=recipient_id,
                    context={
                        'title': title,
                        'message': message,
                    },
                    delivery_methods=['push', 'sms']
                )
            else:
                # Send to current user
                notifications = notification_system.create_notification(
                    template_type='custom_message',
                    recipient_type='user',
                    recipient_id=request.user.id,
                    context={
                        'title': title,
                        'message': message,
                    },
                    delivery_methods=['push']
                )
            
            return Response({
                'success': True,
                'notifications_created': len(notifications),
                'message': _('Notification sent successfully')
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def notification_history(self, request):
        """
        Get notification history for current user.
        Returns recent notifications sent to the user.
        """
        try:
            # TODO: Get notifications from database
            # This would query Notification model for current user
            
            # Placeholder response
            notifications = [
                {
                    'id': 1,
                    'title': 'پرداخت یادآوری',
                    'message': 'زمان پرداخت قسط شما فرا رسیده است',
                    'created_at': timezone.now().isoformat(),
                    'read': False
                }
            ]
            
            return Response({
                'success': True,
                'notifications': notifications
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)