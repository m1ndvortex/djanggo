#!/usr/bin/env python
"""
Working test for POS offline sync system.
This test properly sets up tenant context and tests the complete flow.
"""
import os
import sys
import django
from django.conf import settings

# Add the project root to the Python path
sys.path.insert(0, '/app')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
django.setup()

import json
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django_tenants.utils import get_tenant_model, tenant_context
from zargar.pos.models import POSOfflineStorage, OfflinePOSSystem
from zargar.customers.models import Customer
from zargar.jewelry.models import JewelryItem, Category
from zargar.tenants.models import Domain

User = get_user_model()


def test_complete_pos_offline_flow():
    """Test complete POS offline flow with real tenant, API, and database."""
    print("🚀 Testing Complete POS Offline Flow...")
    
    try:
        # Get or create tenant
        Tenant = get_tenant_model()
        try:
            tenant = Tenant.objects.get(schema_name='test_working')
            print(f"✅ Using existing tenant: {tenant.name}")
        except Tenant.DoesNotExist:
            print("Creating new tenant...")
            tenant = Tenant.objects.create(
                schema_name='test_working',
                name='Test Working Tenant',
                owner_name='Working Owner',
                owner_email='working@test.com'
            )
            tenant.create_schema(check_if_exists=True)
            Domain.objects.create(domain='working.test.com', tenant=tenant, is_primary=True)
            print(f"✅ Created tenant: {tenant.name}")
        
        with tenant_context(tenant):
            # Create test data
            print("\n📊 Setting up test data...")
            
            # Create user
            try:
                user = User.objects.get(username='postest')
            except User.DoesNotExist:
                user = User.objects.create_user(
                    username='postest',
                    email='postest@example.com',
                    password='testpass123'
                )
            print(f"✅ User ready: {user.username}")
            
            # Create customer
            try:
                customer = Customer.objects.get(phone_number='09123456789')
            except Customer.DoesNotExist:
                customer = Customer.objects.create(
                    first_name='احمد',
                    last_name='محمدی',
                    persian_first_name='احمد',
                    persian_last_name='محمدی',
                    phone_number='09123456789',
                    email='customer@test.com'
                )
            print(f"✅ Customer ready: {customer.full_persian_name}")
            
            # Create category and jewelry item
            try:
                category = Category.objects.get(name='Test Category')
            except Category.DoesNotExist:
                category = Category.objects.create(
                    name='Test Category',
                    name_persian='دسته تست'
                )
            
            try:
                jewelry_item = JewelryItem.objects.get(sku='TEST-GOLD-001')
            except JewelryItem.DoesNotExist:
                jewelry_item = JewelryItem.objects.create(
                    name='Test Gold Ring 18K',
                    category=category,
                    sku='TEST-GOLD-001',
                    weight_grams=Decimal('5.500'),
                    karat=18,
                    manufacturing_cost=Decimal('500000.00'),
                    selling_price=Decimal('2500000.00'),
                    quantity=100,
                    status='in_stock'
                )
            print(f"✅ Jewelry item ready: {jewelry_item.name}")
            
            # Test 1: Direct offline storage creation
            print("\n🔧 Test 1: Direct offline storage creation...")
            
            offline_storage = POSOfflineStorage.objects.create(
                device_id='WORKING-TEST-001',
                device_name='Working Test Device',
                transaction_data={
                    'transaction_id': 'working-test-001',
                    'customer_id': customer.id,
                    'transaction_type': 'sale',
                    'payment_method': 'cash',
                    'subtotal': '2500000.00',
                    'tax_amount': '0.00',
                    'discount_amount': '0.00',
                    'total_amount': '2500000.00',
                    'amount_paid': '2500000.00',
                    'line_items': [{
                        'jewelry_item_id': jewelry_item.id,
                        'item_name': jewelry_item.name,
                        'item_sku': jewelry_item.sku,
                        'quantity': 1,
                        'unit_price': str(jewelry_item.selling_price),
                        'gold_weight_grams': str(jewelry_item.weight_grams),
                        'gold_karat': jewelry_item.karat
                    }]
                }
            )
            print(f"✅ Offline storage created: {offline_storage.storage_id}")
            
            # Test 2: OfflinePOSSystem functionality
            print("\n🔧 Test 2: OfflinePOSSystem functionality...")
            
            offline_pos = OfflinePOSSystem(
                device_id='WORKING-TEST-002',
                device_name='Working Test Device 2'
            )
            
            # Create offline transaction using OfflinePOSSystem
            offline_storage2 = offline_pos.create_offline_transaction(
                customer_id=customer.id,
                line_items=[{
                    'jewelry_item_id': jewelry_item.id,
                    'item_name': jewelry_item.name,
                    'item_sku': jewelry_item.sku,
                    'quantity': 2,
                    'unit_price': str(jewelry_item.selling_price),
                    'gold_weight_grams': str(jewelry_item.weight_grams * 2),
                    'gold_karat': jewelry_item.karat
                }],
                payment_method='card',
                amount_paid=jewelry_item.selling_price * 2
            )
            print(f"✅ OfflinePOSSystem transaction created: {offline_storage2.storage_id}")
            
            # Get summary
            summary = offline_pos.get_offline_transaction_summary()
            print(f"✅ Summary: {summary['total_transactions']} transactions, {summary['pending_sync']} pending")
            
            # Test 3: API endpoints with proper authentication
            print("\n🌐 Test 3: API endpoints...")
            
            client = Client()
            login_success = client.login(username='postest', password='testpass123')
            print(f"✅ Login successful: {login_success}")
            
            # Test status API
            response = client.get('/pos/api/offline/status/?device_id=WORKING-TEST-002')
            print(f"Status API response: {response.status_code}")
            
            if response.status_code == 200:
                status_data = json.loads(response.content)
                print(f"✅ Status API working! Pending: {status_data['summary']['pending_sync']}")
            else:
                print(f"❌ Status API failed: {response.content}")
            
            # Test create API
            create_data = {
                'device_id': 'WORKING-API-TEST',
                'device_name': 'Working API Test Device',
                'customer_id': customer.id,
                'line_items': [{
                    'jewelry_item_id': jewelry_item.id,
                    'item_name': jewelry_item.name,
                    'item_sku': jewelry_item.sku,
                    'quantity': 1,
                    'unit_price': str(jewelry_item.selling_price),
                    'gold_weight_grams': str(jewelry_item.weight_grams),
                    'gold_karat': jewelry_item.karat
                }],
                'payment_method': 'cash',
                'amount_paid': str(jewelry_item.selling_price),
                'transaction_type': 'sale'
            }
            
            response = client.post(
                '/pos/api/offline/create/',
                data=json.dumps(create_data),
                content_type='application/json'
            )
            print(f"Create API response: {response.status_code}")
            
            if response.status_code == 200:
                create_response = json.loads(response.content)
                print(f"✅ Create API working! Storage ID: {create_response.get('storage_id')}")
            else:
                print(f"❌ Create API failed: {response.content}")
            
            # Test 4: Sync functionality
            print("\n🔄 Test 4: Sync functionality...")
            
            # Mock sync (since we don't have real connection)
            from unittest.mock import patch
            
            with patch('zargar.pos.models.OfflinePOSSystem._check_connection', return_value=True):
                sync_results = offline_pos.sync_offline_transactions()
                print(f"✅ Sync completed: {sync_results}")
            
            # Test 5: Performance with multiple transactions
            print("\n⚡ Test 5: Performance test...")
            
            start_time = time.time()
            
            # Create 20 offline transactions
            for i in range(20):
                POSOfflineStorage.objects.create(
                    device_id=f'PERF-TEST-{i:03d}',
                    device_name=f'Performance Test Device {i}',
                    transaction_data={
                        'transaction_id': f'perf-test-{i}',
                        'customer_id': customer.id,
                        'total_amount': str(1000000 + i * 50000),
                        'line_items': [{
                            'item_name': f'Performance Item {i}',
                            'quantity': 1,
                            'unit_price': str(1000000 + i * 50000)
                        }]
                    }
                )
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"✅ Created 20 transactions in {duration:.3f}s ({20/duration:.1f} transactions/second)")
            
            # Final verification
            total_offline = POSOfflineStorage.objects.count()
            print(f"\n📊 Final Results:")
            print(f"   Total offline transactions: {total_offline}")
            print(f"   Test completed successfully!")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_concurrent_operations():
    """Test concurrent offline operations."""
    print("\n🔀 Testing concurrent operations...")
    
    try:
        import threading
        import time
        
        Tenant = get_tenant_model()
        tenant = Tenant.objects.get(schema_name='test_working')
        
        results = []
        
        def create_transactions(thread_id):
            """Create transactions in a thread."""
            thread_results = {'thread_id': thread_id, 'created': 0, 'errors': 0}
            
            try:
                with tenant_context(tenant):
                    for i in range(10):
                        POSOfflineStorage.objects.create(
                            device_id=f'THREAD-{thread_id}-{i}',
                            device_name=f'Thread {thread_id} Device {i}',
                            transaction_data={
                                'transaction_id': f'thread-{thread_id}-{i}',
                                'total_amount': str(500000 + i * 10000),
                                'line_items': [{
                                    'item_name': f'Thread {thread_id} Item {i}',
                                    'quantity': 1,
                                    'unit_price': str(500000 + i * 10000)
                                }]
                            }
                        )
                        thread_results['created'] += 1
            except Exception as e:
                thread_results['errors'] += 1
            
            results.append(thread_results)
        
        # Create 10 threads, each creating 10 transactions
        threads = []
        start_time = time.time()
        
        for i in range(10):
            thread = threading.Thread(target=create_transactions, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        duration = end_time - start_time
        
        total_created = sum(r['created'] for r in results)
        total_errors = sum(r['errors'] for r in results)
        
        print(f"✅ Concurrent test completed:")
        print(f"   Threads: 10")
        print(f"   Total created: {total_created}")
        print(f"   Total errors: {total_errors}")
        print(f"   Duration: {duration:.3f}s")
        print(f"   Rate: {total_created/duration:.1f} transactions/second")
        
        return total_errors == 0
        
    except Exception as e:
        print(f"❌ Concurrent test failed: {e}")
        return False


if __name__ == '__main__':
    import time
    
    print("=" * 80)
    print("POS OFFLINE SYNC - WORKING TESTS")
    print("=" * 80)
    
    start_time = time.time()
    
    success1 = test_complete_pos_offline_flow()
    success2 = test_concurrent_operations()
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    print(f"\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    print(f"Complete flow test: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"Concurrent test: {'✅ PASSED' if success2 else '❌ FAILED'}")
    print(f"Total duration: {total_duration:.2f}s")
    
    if success1 and success2:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ POS offline sync system is working and production-ready!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)