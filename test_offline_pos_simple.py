#!/usr/bin/env python
"""
Simple test script for offline POS system functionality.
"""
import os
import sys
import django
from django.conf import settings

# Add the project root to the Python path
sys.path.insert(0, '/app')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from decimal import Decimal
from django.utils import timezone
from zargar.pos.models import POSOfflineStorage, OfflinePOSSystem


def test_offline_pos_system():
    """Test basic offline POS system functionality."""
    print("Testing Offline POS System...")
    
    # Get tenant context
    from django_tenants.utils import get_tenant_model, tenant_context
    Tenant = get_tenant_model()
    tenant = Tenant.objects.exclude(schema_name='public').first()
    
    if not tenant:
        print("No tenant found, skipping test")
        return False
    
    print(f"Using tenant: {tenant.name} (schema: {tenant.schema_name})")
    
    with tenant_context(tenant):
        # Test 1: Create OfflinePOSSystem instance
        print("\n1. Creating OfflinePOSSystem instance...")
        offline_pos = OfflinePOSSystem(
            device_id='TEST-DEVICE-001',
            device_name='Test POS Device'
        )
        print(f"   Device ID: {offline_pos.device_id}")
        print(f"   Device Name: {offline_pos.device_name}")
        
        # Test 2: Create offline transaction data
        print("\n2. Creating offline transaction...")
        line_items = [
            {
                'jewelry_item_id': 1,
                'item_name': 'Gold Ring 18K',
                'item_sku': 'RING-001',
                'quantity': 1,
                'unit_price': '2500000.00',
                'gold_weight_grams': '5.500',
                'gold_karat': 18
            }
        ]
        
        try:
            offline_storage = offline_pos.create_offline_transaction(
                customer_id=None,  # Walk-in customer
                line_items=line_items,
                payment_method='cash',
                amount_paid=Decimal('2500000.00')
            )
            print(f"   Created offline storage: {offline_storage.storage_id}")
            print(f"   Sync status: {offline_storage.sync_status}")
            print(f"   Is synced: {offline_storage.is_synced}")
        except Exception as e:
            print(f"   Error creating offline transaction: {e}")
            return False
        
        # Test 3: Get offline transaction summary
        print("\n3. Getting offline transaction summary...")
        try:
            summary = offline_pos.get_offline_transaction_summary()
            print(f"   Total transactions: {summary['total_transactions']}")
            print(f"   Pending sync: {summary['pending_sync']}")
            print(f"   Synced: {summary['synced']}")
            print(f"   Total pending value: {summary['total_pending_value']}")
        except Exception as e:
            print(f"   Error getting summary: {e}")
            return False
        
        # Test 4: Test POSOfflineStorage model methods
        print("\n4. Testing POSOfflineStorage model methods...")
        try:
            transaction_summary = offline_storage.get_transaction_summary()
            print(f"   Storage ID: {transaction_summary['storage_id']}")
            print(f"   Device name: {transaction_summary['device_name']}")
            print(f"   Total amount: {transaction_summary['total_amount']}")
            print(f"   Line items count: {transaction_summary['line_items_count']}")
        except Exception as e:
            print(f"   Error getting transaction summary: {e}")
            return False
        
        # Test 5: Test conflict resolution
        print("\n5. Testing conflict resolution...")
        try:
            # Simulate a conflict
            offline_storage.sync_status = 'conflict'
            offline_storage.has_conflicts = True
            offline_storage.save()
            
            # Resolve with retry
            success = offline_storage.resolve_conflict('retry')
            print(f"   Conflict resolution success: {success}")
            print(f"   New sync status: {offline_storage.sync_status}")
            print(f"   Has conflicts: {offline_storage.has_conflicts}")
        except Exception as e:
            print(f"   Error testing conflict resolution: {e}")
            return False
        
        print("\n✅ All tests passed successfully!")
        return True


def test_pos_offline_service():
    """Test POSOfflineService functionality."""
    print("\nTesting POSOfflineService...")
    
    from zargar.pos.services import POSOfflineService
    from django_tenants.utils import get_tenant_model, tenant_context
    
    # Get tenant context
    Tenant = get_tenant_model()
    tenant = Tenant.objects.exclude(schema_name='public').first()
    
    if not tenant:
        print("No tenant found, skipping test")
        return False
    
    with tenant_context(tenant):
        # Test 1: Create offline transaction data
        print("\n1. Creating offline transaction data...")
        try:
            line_items = [
                {
                    'jewelry_item_id': 1,
                    'item_name': 'Gold Ring',
                    'unit_price': '2500000.00',
                    'quantity': 1
                }
            ]
            
            transaction_data = POSOfflineService.create_offline_transaction_data(
                customer_id=None,
                line_items=line_items,
                payment_method='cash',
                amount_paid=Decimal('2500000.00')
            )
            
            print(f"   Transaction ID: {transaction_data['transaction_id']}")
            print(f"   Payment method: {transaction_data['payment_method']}")
            print(f"   Total amount: {transaction_data['total_amount']}")
            print(f"   Line items count: {len(transaction_data['line_items'])}")
        except Exception as e:
            print(f"   Error creating transaction data: {e}")
            return False
        
        # Test 2: Store offline transaction
        print("\n2. Storing offline transaction...")
        try:
            offline_storage = POSOfflineService.store_offline_transaction(
                transaction_data=transaction_data,
                device_id='TEST-DEVICE-002'
            )
            
            print(f"   Storage ID: {offline_storage.storage_id}")
            print(f"   Device ID: {offline_storage.device_id}")
            print(f"   Is synced: {offline_storage.is_synced}")
        except Exception as e:
            print(f"   Error storing offline transaction: {e}")
            return False
        
        # Test 3: Get offline transaction summary
        print("\n3. Getting offline transaction summary...")
        try:
            summary = POSOfflineService.get_offline_transaction_summary(
                device_id='TEST-DEVICE-002'
            )
            
            print(f"   Total transactions: {summary['total_transactions']}")
            print(f"   Pending sync: {summary['pending_sync']}")
            print(f"   Total pending value: {summary['total_pending_value']}")
        except Exception as e:
            print(f"   Error getting summary: {e}")
            return False
        
        print("\n✅ POSOfflineService tests passed!")
        return True


if __name__ == '__main__':
    print("=" * 60)
    print("OFFLINE POS SYSTEM TESTS")
    print("=" * 60)
    
    success1 = test_offline_pos_system()
    success2 = test_pos_offline_service()
    
    if success1 and success2:
        print("\n🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)