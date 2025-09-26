"""
Offline synchronization API for ZARGAR jewelry SaaS platform.
Handles data synchronization between mobile devices and server for offline POS operations.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, F, Sum, Count, Max
from django.core.cache import cache
from decimal import Decimal
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from zargar.core.permissions import TenantPermission, POSPermission, AllRolesPermission
from zargar.jewelry.models import JewelryItem, Category
from zargar.customers.models import Customer
from zargar.pos.models import POSTransaction, POSTransactionLineItem
from zargar.core.models import User
from .mobile_serializers import (
    MobileJewelryItemSerializer, MobileCustomerSerializer,
    MobilePOSTransactionSerializer, OfflineTransactionSerializer,
    MobileSyncDataSerializer
)
from .throttling import TenantAPIThrottle


@api_view(['GET'])
@permission_classes([IsAuthenticated, TenantPermission, AllRolesPermission])
@throttle_classes([TenantAPIThrottle])
def get_sync_manifest(request):
    """
    Get synchronization manifest for mobile app.
    Returns metadata about available data for synchronization.
    """
    try:
        # Get last sync timestamp from request
        last_sync = request.GET.get('last_sync')
        if last_sync:
            try:
                last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
            except ValueError:
                last_sync_dt = None
        else:
            last_sync_dt = None
        
        # Calculate data counts and checksums
        manifest = {
            'server_time': timezone.now().isoformat(),
            'last_sync': last_sync,
            'data_manifest': {}
        }
        
        # Categories manifest
        categories_qs = Category.objects.filter(is_active=True)
        if last_sync_dt:
            categories_qs = categories_qs.filter(updated_at__gt=last_sync_dt)
        
        manifest['data_manifest']['categories'] = {
            'count': categories_qs.count(),
            'last_updated': categories_qs.aggregate(
                max_updated=Max('updated_at')
            )['max_updated'].isoformat() if categories_qs.exists() else None,
            'checksum': _calculate_queryset_checksum(categories_qs, ['id', 'name_persian', 'updated_at'])
        }
        
        # Jewelry items manifest
        items_qs = JewelryItem.objects.filter(status__in=['available', 'reserved'])
        if last_sync_dt:
            items_qs = items_qs.filter(updated_at__gt=last_sync_dt)
        
        manifest['data_manifest']['jewelry_items'] = {
            'count': min(items_qs.count(), 500),  # Limit for performance
            'last_updated': items_qs.aggregate(
                max_updated=Max('updated_at')
            )['max_updated'].isoformat() if items_qs.exists() else None,
            'checksum': _calculate_queryset_checksum(
                items_qs[:500], ['id', 'name', 'sku', 'selling_price', 'updated_at']
            )
        }
        
        # Customers manifest
        customers_qs = Customer.objects.filter(is_active=True)
        if last_sync_dt:
            customers_qs = customers_qs.filter(updated_at__gt=last_sync_dt)
        else:
            # For initial sync, get recent customers only
            customers_qs = customers_qs.order_by('-created_at')[:200]
        
        manifest['data_manifest']['customers'] = {
            'count': customers_qs.count(),
            'last_updated': customers_qs.aggregate(
                max_updated=Max('updated_at')
            )['max_updated'].isoformat() if customers_qs.exists() else None,
            'checksum': _calculate_queryset_checksum(
                customers_qs, ['id', 'phone_number', 'updated_at']
            )
        }
        
        # System settings
        manifest['system_settings'] = {
            'current_gold_price': _get_current_gold_price(),
            'tax_rate': _get_tax_rate(),
            'currency_symbol': 'تومان',
            'min_app_version': '1.0.0',
            'force_sync_required': False
        }
        
        return Response({
            'success': True,
            'manifest': manifest
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, TenantPermission, AllRolesPermission])
@throttle_classes([TenantAPIThrottle])
def download_sync_data(request):
    """
    Download synchronization data for mobile app.
    Returns data based on requested categories and timestamps.
    """
    try:
        # Parse request data
        requested_data = request.data.get('requested_data', {})
        last_sync = request.data.get('last_sync')
        device_id = request.data.get('device_id', '')
        
        if last_sync:
            try:
                last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
            except ValueError:
                last_sync_dt = None
        else:
            last_sync_dt = None
        
        sync_data = {
            'sync_timestamp': timezone.now().isoformat(),
            'device_id': device_id,
            'data': {}
        }
        
        # Download categories if requested
        if requested_data.get('categories', False):
            categories_qs = Category.objects.filter(is_active=True)
            if last_sync_dt:
                categories_qs = categories_qs.filter(updated_at__gt=last_sync_dt)
            
            sync_data['data']['categories'] = [
                {
                    'id': cat.id,
                    'name': cat.name_persian,
                    'description': cat.description,
                    'is_active': cat.is_active,
                    'updated_at': cat.updated_at.isoformat()
                }
                for cat in categories_qs
            ]
        
        # Download jewelry items if requested
        if requested_data.get('jewelry_items', False):
            items_qs = JewelryItem.objects.filter(status__in=['available', 'reserved'])
            if last_sync_dt:
                items_qs = items_qs.filter(updated_at__gt=last_sync_dt)
            
            # Limit items for performance
            items_qs = items_qs.select_related('category').prefetch_related('photos')[:500]
            
            sync_data['data']['jewelry_items'] = MobileJewelryItemSerializer(
                items_qs, many=True, context={'request': request}
            ).data
        
        # Download customers if requested
        if requested_data.get('customers', False):
            customers_qs = Customer.objects.filter(is_active=True)
            if last_sync_dt:
                customers_qs = customers_qs.filter(updated_at__gt=last_sync_dt)
            else:
                # For initial sync, get recent customers only
                customers_qs = customers_qs.order_by('-created_at')[:200]
            
            sync_data['data']['customers'] = MobileCustomerSerializer(
                customers_qs, many=True, context={'request': request}
            ).data
        
        # Add system settings
        sync_data['system_settings'] = {
            'current_gold_price': _get_current_gold_price(),
            'tax_rate': _get_tax_rate(),
            'currency_symbol': 'تومان',
            'server_time': timezone.now().isoformat()
        }
        
        # Cache the sync data for potential retry
        cache_key = f"sync_data_{request.user.id}_{device_id}_{timezone.now().timestamp()}"
        cache.set(cache_key, sync_data, timeout=3600)  # Cache for 1 hour
        
        return Response({
            'success': True,
            'sync_data': sync_data,
            'cache_key': cache_key
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, TenantPermission, POSPermission])
@throttle_classes([TenantAPIThrottle])
def upload_offline_transactions(request):
    """
    Upload offline transactions for synchronization.
    Processes multiple offline transactions in a batch.
    """
    try:
        transactions_data = request.data.get('transactions', [])
        device_id = request.data.get('device_id', '')
        
        if not transactions_data:
            return Response({
                'success': False,
                'error': _('No transactions provided for upload')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        sync_results = {
            'total_transactions': len(transactions_data),
            'successful_syncs': 0,
            'failed_syncs': 0,
            'duplicate_transactions': 0,
            'errors': [],
            'synced_transactions': []
        }
        
        with transaction.atomic():
            for transaction_data in transactions_data:
                try:
                    # Check for duplicate transactions
                    offline_transaction_id = transaction_data.get('offline_transaction_id')
                    if offline_transaction_id:
                        existing_transaction = POSTransaction.objects.filter(
                            offline_data__offline_transaction_id=offline_transaction_id
                        ).first()
                        
                        if existing_transaction:
                            sync_results['duplicate_transactions'] += 1
                            sync_results['synced_transactions'].append({
                                'offline_id': offline_transaction_id,
                                'server_id': str(existing_transaction.transaction_id),
                                'status': 'duplicate'
                            })
                            continue
                    
                    # Create transaction from offline data
                    serializer = OfflineTransactionSerializer(data=transaction_data)
                    if serializer.is_valid():
                        pos_transaction = serializer.save(created_by=request.user)
                        
                        # Add device information to offline data
                        pos_transaction.offline_data.update({
                            'device_id': device_id,
                            'upload_timestamp': timezone.now().isoformat()
                        })
                        pos_transaction.save(update_fields=['offline_data'])
                        
                        # Attempt to sync the transaction
                        if pos_transaction.sync_offline_transaction():
                            sync_results['successful_syncs'] += 1
                            sync_results['synced_transactions'].append({
                                'offline_id': offline_transaction_id,
                                'server_id': str(pos_transaction.transaction_id),
                                'transaction_number': pos_transaction.transaction_number,
                                'status': 'synced'
                            })
                        else:
                            sync_results['failed_syncs'] += 1
                            sync_results['errors'].append({
                                'offline_id': offline_transaction_id,
                                'error': 'Sync failed after creation'
                            })
                    else:
                        sync_results['failed_syncs'] += 1
                        sync_results['errors'].append({
                            'offline_id': offline_transaction_id,
                            'errors': serializer.errors
                        })
                        
                except Exception as e:
                    sync_results['failed_syncs'] += 1
                    sync_results['errors'].append({
                        'offline_id': transaction_data.get('offline_transaction_id', 'unknown'),
                        'error': str(e)
                    })
        
        # Log sync activity
        _log_sync_activity(
            user=request.user,
            device_id=device_id,
            activity_type='upload_transactions',
            results=sync_results
        )
        
        return Response({
            'success': True,
            'sync_results': sync_results
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, TenantPermission, AllRolesPermission])
@throttle_classes([TenantAPIThrottle])
def upload_inventory_changes(request):
    """
    Upload inventory changes from mobile app.
    Processes stock level adjustments made offline.
    """
    try:
        inventory_changes = request.data.get('inventory_changes', [])
        device_id = request.data.get('device_id', '')
        
        if not inventory_changes:
            return Response({
                'success': False,
                'error': _('No inventory changes provided')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        update_results = {
            'total_changes': len(inventory_changes),
            'successful_updates': 0,
            'failed_updates': 0,
            'conflicts': [],
            'errors': []
        }
        
        with transaction.atomic():
            for change_data in inventory_changes:
                try:
                    item_id = change_data.get('item_id')
                    new_quantity = change_data.get('quantity')
                    change_type = change_data.get('change_type', 'set')  # set, add, subtract
                    reason = change_data.get('reason', 'Mobile update')
                    timestamp = change_data.get('timestamp')
                    
                    if not all([item_id is not None, new_quantity is not None]):
                        update_results['failed_updates'] += 1
                        update_results['errors'].append({
                            'item_id': item_id,
                            'error': 'Missing required fields'
                        })
                        continue
                    
                    # Get jewelry item
                    try:
                        item = JewelryItem.objects.select_for_update().get(id=item_id)
                    except JewelryItem.DoesNotExist:
                        update_results['failed_updates'] += 1
                        update_results['errors'].append({
                            'item_id': item_id,
                            'error': 'Item not found'
                        })
                        continue
                    
                    # Check for conflicts (item updated after offline change)
                    if timestamp:
                        try:
                            change_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            if item.updated_at > change_timestamp:
                                update_results['conflicts'].append({
                                    'item_id': item_id,
                                    'item_name': item.name,
                                    'server_quantity': item.quantity,
                                    'mobile_quantity': new_quantity,
                                    'conflict_reason': 'Item updated on server after mobile change'
                                })
                                continue
                        except ValueError:
                            pass  # Invalid timestamp format, proceed with update
                    
                    # Apply quantity change
                    old_quantity = item.quantity
                    
                    if change_type == 'set':
                        item.quantity = new_quantity
                    elif change_type == 'add':
                        item.quantity += new_quantity
                    elif change_type == 'subtract':
                        item.quantity = max(0, item.quantity - new_quantity)
                    
                    item.save(update_fields=['quantity', 'updated_at'])
                    
                    # TODO: Create inventory adjustment log entry
                    # This would record the change for audit purposes
                    
                    update_results['successful_updates'] += 1
                    
                except Exception as e:
                    update_results['failed_updates'] += 1
                    update_results['errors'].append({
                        'item_id': change_data.get('item_id'),
                        'error': str(e)
                    })
        
        # Log sync activity
        _log_sync_activity(
            user=request.user,
            device_id=device_id,
            activity_type='upload_inventory_changes',
            results=update_results
        )
        
        return Response({
            'success': True,
            'update_results': update_results
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, TenantPermission, AllRolesPermission])
@throttle_classes([TenantAPIThrottle])
def get_sync_status(request):
    """
    Get synchronization status for mobile app.
    Returns information about pending syncs and conflicts.
    """
    try:
        device_id = request.GET.get('device_id', '')
        
        # Get pending transactions
        pending_transactions = POSTransaction.objects.filter(
            sync_status='pending_sync',
            is_offline_transaction=True,
            created_by=request.user
        )
        
        if device_id:
            pending_transactions = pending_transactions.filter(
                offline_data__device_id=device_id
            )
        
        # Get failed transactions
        failed_transactions = POSTransaction.objects.filter(
            sync_status='sync_failed',
            is_offline_transaction=True,
            created_by=request.user
        )
        
        if device_id:
            failed_transactions = failed_transactions.filter(
                offline_data__device_id=device_id
            )
        
        # Get recent sync activity
        # TODO: Implement sync activity log model and query
        
        sync_status = {
            'pending_transactions_count': pending_transactions.count(),
            'failed_transactions_count': failed_transactions.count(),
            'last_successful_sync': None,  # TODO: Get from sync log
            'server_time': timezone.now().isoformat(),
            'sync_required': pending_transactions.exists() or failed_transactions.exists(),
            'pending_transactions': MobilePOSTransactionSerializer(
                pending_transactions[:10], many=True, context={'request': request}
            ).data,
            'failed_transactions': MobilePOSTransactionSerializer(
                failed_transactions[:10], many=True, context={'request': request}
            ).data
        }
        
        return Response({
            'success': True,
            'sync_status': sync_status
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, TenantPermission, AllRolesPermission])
@throttle_classes([TenantAPIThrottle])
def resolve_sync_conflicts(request):
    """
    Resolve synchronization conflicts.
    Allows manual resolution of data conflicts between mobile and server.
    """
    try:
        conflicts = request.data.get('conflicts', [])
        device_id = request.data.get('device_id', '')
        
        if not conflicts:
            return Response({
                'success': False,
                'error': _('No conflicts provided for resolution')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        resolution_results = {
            'total_conflicts': len(conflicts),
            'resolved_conflicts': 0,
            'failed_resolutions': 0,
            'errors': []
        }
        
        with transaction.atomic():
            for conflict_data in conflicts:
                try:
                    conflict_type = conflict_data.get('conflict_type')
                    resolution = conflict_data.get('resolution')  # 'use_server', 'use_mobile', 'merge'
                    
                    if conflict_type == 'inventory_quantity':
                        item_id = conflict_data.get('item_id')
                        mobile_quantity = conflict_data.get('mobile_quantity')
                        
                        item = JewelryItem.objects.get(id=item_id)
                        
                        if resolution == 'use_mobile':
                            item.quantity = mobile_quantity
                            item.save(update_fields=['quantity'])
                        elif resolution == 'use_server':
                            # Keep server value, no action needed
                            pass
                        elif resolution == 'merge':
                            # Custom merge logic could be implemented here
                            pass
                        
                        resolution_results['resolved_conflicts'] += 1
                    
                    # Add other conflict types as needed
                    
                except Exception as e:
                    resolution_results['failed_resolutions'] += 1
                    resolution_results['errors'].append({
                        'conflict': conflict_data,
                        'error': str(e)
                    })
        
        return Response({
            'success': True,
            'resolution_results': resolution_results
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Helper functions

def _calculate_queryset_checksum(queryset, fields: List[str]) -> str:
    """Calculate checksum for queryset based on specified fields."""
    try:
        data_string = ""
        for obj in queryset:
            field_values = []
            for field in fields:
                value = getattr(obj, field, '')
                if hasattr(value, 'isoformat'):  # DateTime field
                    value = value.isoformat()
                field_values.append(str(value))
            data_string += '|'.join(field_values) + '\n'
        
        return hashlib.md5(data_string.encode('utf-8')).hexdigest()
    except Exception:
        return 'error'


def _get_current_gold_price() -> float:
    """Get current gold price (placeholder implementation)."""
    # TODO: Integrate with real gold price API
    cached_price = cache.get('current_gold_price')
    if cached_price:
        return cached_price
    
    # Default price in Toman per gram for 18K gold
    default_price = 2500000.0
    cache.set('current_gold_price', default_price, timeout=3600)  # Cache for 1 hour
    return default_price


def _get_tax_rate() -> float:
    """Get current tax rate."""
    # TODO: Get from tenant settings
    return 0.09  # 9% VAT


def _log_sync_activity(user: User, device_id: str, activity_type: str, results: Dict[str, Any]):
    """Log synchronization activity for audit purposes."""
    # TODO: Implement sync activity logging
    # This would create entries in a SyncActivityLog model
    pass