"""
Heavy load test for POS offline sync system - 100 concurrent operations.
Tests the system's ability to handle 100 simultaneous sync operations with real data.
"""
import os
import django
from django.conf import settings

# Setup Django
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import json
import time
import threading
import concurrent.futures
import random
from decimal import Decimal
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.utils import get_tenant_model, tenant_context
from django.db import transaction, connections
from unittest.mock import patch

from zargar.pos.models import POSTransaction, POSOfflineStorage, OfflinePOSSystem
from zargar.pos.services import POSOfflineService
from zargar.customers.models import Customer
from zargar.jewelry.models import JewelryItem, Category

User = get_user_model()


class POSOfflineHeavyLoad100ConcurrentTest(TransactionTestCase):
    """
    Heavy load test for 100 concurrent POS offline sync operations.
    Simulates real-world scenario where 100 POS devices come online simultaneously.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test class for heavy load testing."""
        super().setUpClass()
        
        # Create tenant for load testing
        Tenant = get_tenant_model()
        cls.tenant = Tenant.objects.create(
            schema_name='test_pos_heavy_load_100',
            name='Test POS Heavy Load 100 Shop',
            owner_name='Heavy Load Test Owner',
            owner_email='heavyload@test.com'
        )
        cls.tenant.create_schema(check_if_exists=True)
        
        print("🏗️ Setting up heavy load test environment...")
    
    def setUp(self):
        """Set up extensive test data for heavy load testing."""
        with tenant_context(self.tenant):
            print("📊 Creating test data for 100 concurrent operations...")
            
            # Create users
            self.users = []
            for i in range(10):  # 10 users for variety
                user = User.objects.create_user(
                    username=f'loadtest_user_{i}',
                    email=f'loadtest{i}@example.com',
                    password='testpass123',
                    role='salesperson'
                )
                self.users.append(user)
            
            # Create customers (200 customers for variety)
            self.customers = []
            for i in range(200):
                customer = Customer.objects.create(
                    first_name=f'مشتری{i}',
                    last_name='تست بار',
                    persian_first_name=f'مشتری{i}',
                    persian_last_name='تست بار',
                    phone_number=f'091234{i:05d}',
                    email=f'customer{i}@loadtest.com'
                )
                self.customers.append(customer)
            
            # Create jewelry categories
            self.categories = []
            category_names = [
                ('Rings', 'انگشتر'),
                ('Necklaces', 'گردنبند'),
                ('Bracelets', 'دستبند'),
                ('Earrings', 'گوشواره'),
                ('Chains', 'زنجیر')
            ]
            
            for name_en, name_fa in category_names:
                category = Category.objects.create(
                    name=f'{name_en} Load Test',
                    name_persian=f'{name_fa} تست بار'
                )
                self.categories.append(category)
            
            # Create jewelry items (500 items for variety)
            self.jewelry_items = []
            for i in range(500):
                category = self.categories[i % len(self.categories)]
                
                item = JewelryItem.objects.create(
                    name=f'Load Test Item {i}',
                    category=category,
                    sku=f'LOAD-{i:04d}',
                    weight_grams=Decimal(f'{3.0 + (i % 20) * 0.5:.1f}'),
                    karat=random.choice([14, 18, 22]),
                    manufacturing_cost=Decimal(f'{300000 + (i % 50) * 10000}.00'),
                    selling_price=Decimal(f'{1500000 + (i % 100) * 25000}.00'),
                    quantity=2000,  # High quantity for load testing
                    status='in_stock'
                )
                self.jewelry_items.append(item)
            
            print(f"✅ Created {len(self.customers)} customers and {len(self.jewelry_items)} jewelry items")
    
    def create_offline_transactions_for_device(self, device_id, transaction_count):
        """Create offline transactions for a specific device."""
        results = {
            'device_id': device_id,
            'transactions_created': 0,
            'total_amount': Decimal('0.00'),
            'errors': [],
            'start_time': time.time()
        }
        
        try:
            with tenant_context(self.tenant):
                offline_pos = OfflinePOSSystem(
                    device_id=device_id,
                    device_name=f'Heavy Load Device {device_id}'
                )
                
                for i in range(transaction_count):
                    try:
                        # Select random customer and items
                        customer = random.choice(self.customers)
                        num_items = random.randint(1, 8)  # 1-8 items per transaction
                        selected_items = random.sample(self.jewelry_items, num_items)
                        
                        line_items = []
                        transaction_total = Decimal('0.00')
                        
                        for item in selected_items:
                            quantity = random.randint(1, 3)
                            line_item = {
                                'jewelry_item_id': item.id,
                                'item_name': item.name,
                                'item_sku': item.sku,
                                'quantity': quantity,
                                'unit_price': str(item.selling_price),
                                'gold_weight_grams': str(item.weight_grams * quantity),
                                'gold_karat': item.karat
                            }
                            line_items.append(line_item)
                            transaction_total += item.selling_price * quantity
                        
                        # Create offline transaction
                        offline_storage = offline_pos.create_offline_transaction(
                            customer_id=customer.id,
                            line_items=line_items,
                            payment_method=random.choice(['cash', 'card', 'bank_transfer']),
                            amount_paid=transaction_total,
                            transaction_type='sale'
                        )
                        
                        results['transactions_created'] += 1
                        results['total_amount'] += transaction_total
                        
                    except Exception as e:
                        results['errors'].append(f'Transaction {i}: {str(e)}')
                        
        except Exception as e:
            results['errors'].append(f'Device setup error: {str(e)}')
        
        results['end_time'] = time.time()
        results['duration'] = results['end_time'] - results['start_time']
        
        return results
    
    def sync_offline_transactions_for_device(self, device_id):
        """Sync offline transactions for a specific device."""
        results = {
            'device_id': device_id,
            'sync_results': None,
            'errors': [],
            'start_time': time.time()
        }
        
        try:
            with tenant_context(self.tenant):
                offline_pos = OfflinePOSSystem(
                    device_id=device_id,
                    device_name=f'Heavy Load Device {device_id}'
                )
                
                # Mock connection check to simulate online status
                with patch('zargar.pos.models.OfflinePOSSystem._check_connection', return_value=True):
                    sync_results = offline_pos.sync_offline_transactions()
                    results['sync_results'] = sync_results
                    
        except Exception as e:
            results['errors'].append(f'Sync error: {str(e)}')
        
        results['end_time'] = time.time()
        results['duration'] = results['end_time'] - results['start_time']
        
        return results
    
    def test_100_concurrent_device_sync_operations(self):
        """
        Test 100 concurrent devices syncing their offline transactions.
        This simulates the scenario where 100 POS devices come online simultaneously.
        """
        print("\n🚀 Starting 100 concurrent device sync test...")
        print("📋 Phase 1: Creating offline transactions for 100 devices...")
        
        device_count = 100
        transactions_per_device = 10  # Each device has 10 offline transactions
        total_expected_transactions = device_count * transactions_per_device
        
        # Phase 1: Create offline transactions for all devices
        creation_start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            # Create offline transactions for all devices
            creation_futures = {
                executor.submit(
                    self.create_offline_transactions_for_device,
                    f'HEAVY-LOAD-{i:03d}',
                    transactions_per_device
                ): f'HEAVY-LOAD-{i:03d}'
                for i in range(device_count)
            }
            
            creation_results = []
            for future in concurrent.futures.as_completed(creation_futures):
                device_id = creation_futures[future]
                try:
                    result = future.result(timeout=60)
                    creation_results.append(result)
                    if result['transactions_created'] == transactions_per_device:
                        print(f"✅ Device {device_id}: Created {result['transactions_created']} transactions")
                    else:
                        print(f"⚠️ Device {device_id}: Created {result['transactions_created']}/{transactions_per_device} transactions")
                except Exception as e:
                    print(f"❌ Device {device_id} creation failed: {e}")
        
        creation_end_time = time.time()
        creation_duration = creation_end_time - creation_start_time
        
        # Analyze creation results
        total_created = sum(r['transactions_created'] for r in creation_results)
        total_creation_errors = sum(len(r['errors']) for r in creation_results)
        
        print(f"\n📊 Creation Phase Results:")
        print(f"   Expected transactions: {total_expected_transactions}")
        print(f"   Created transactions: {total_created}")
        print(f"   Creation errors: {total_creation_errors}")
        print(f"   Creation duration: {creation_duration:.2f}s")
        print(f"   Creation rate: {total_created / creation_duration:.2f} transactions/second")
        
        # Verify in database
        with tenant_context(self.tenant):
            db_offline_count = POSOfflineStorage.objects.filter(is_synced=False).count()
            print(f"   Database offline count: {db_offline_count}")
        
        # Phase 2: Sync all devices concurrently (THE MAIN TEST)
        print(f"\n🔄 Phase 2: Syncing {device_count} devices concurrently...")
        
        sync_start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            # Submit all sync tasks simultaneously
            sync_futures = {
                executor.submit(
                    self.sync_offline_transactions_for_device,
                    f'HEAVY-LOAD-{i:03d}'
                ): f'HEAVY-LOAD-{i:03d}'
                for i in range(device_count)
            }
            
            sync_results = []
            completed_devices = 0
            
            for future in concurrent.futures.as_completed(sync_futures):
                device_id = sync_futures[future]
                try:
                    result = future.result(timeout=120)  # 2 minute timeout per device
                    sync_results.append(result)
                    completed_devices += 1
                    
                    if result['sync_results']:
                        synced = result['sync_results']['synced_successfully']
                        failed = result['sync_results']['failed']
                        print(f"✅ Device {device_id} ({completed_devices}/{device_count}): Synced {synced}, Failed {failed} in {result['duration']:.2f}s")
                    else:
                        print(f"⚠️ Device {device_id} ({completed_devices}/{device_count}): No sync results")
                        
                except Exception as e:
                    completed_devices += 1
                    print(f"❌ Device {device_id} ({completed_devices}/{device_count}) sync failed: {e}")
        
        sync_end_time = time.time()
        sync_duration = sync_end_time - sync_start_time
        
        # Analyze sync results
        total_synced = sum(
            r['sync_results']['synced_successfully'] 
            for r in sync_results 
            if r['sync_results']
        )
        total_sync_failed = sum(
            r['sync_results']['failed'] 
            for r in sync_results 
            if r['sync_results']
        )
        total_sync_errors = sum(len(r['errors']) for r in sync_results)
        
        print(f"\n📊 Sync Phase Results:")
        print(f"   Devices synced: {len(sync_results)}")
        print(f"   Total transactions synced: {total_synced}")
        print(f"   Total sync failures: {total_sync_failed}")
        print(f"   Total sync errors: {total_sync_errors}")
        print(f"   Sync duration: {sync_duration:.2f}s")
        print(f"   Sync rate: {total_synced / sync_duration:.2f} transactions/second")
        print(f"   Device sync rate: {len(sync_results) / sync_duration:.2f} devices/second")
        
        # Verify final database state
        with tenant_context(self.tenant):
            final_offline_synced = POSOfflineStorage.objects.filter(is_synced=True).count()
            final_offline_pending = POSOfflineStorage.objects.filter(is_synced=False).count()
            final_pos_transactions = POSTransaction.objects.count()
            
            print(f"\n📊 Final Database State:")
            print(f"   Offline synced: {final_offline_synced}")
            print(f"   Offline pending: {final_offline_pending}")
            print(f"   POS transactions: {final_pos_transactions}")
        
        # Performance and correctness assertions
        self.assertGreaterEqual(total_created, total_expected_transactions * 0.95)  # 95% creation success
        self.assertGreaterEqual(total_synced, total_created * 0.95)  # 95% sync success
        self.assertEqual(total_synced, final_pos_transactions)  # Sync integrity
        self.assertLess(sync_duration, 300)  # Should complete within 5 minutes
        self.assertGreater(total_synced / sync_duration, 10)  # At least 10 transactions/second
        
        print(f"\n🎉 100 concurrent device sync test completed successfully!")
        print(f"   ✅ Created {total_created} offline transactions")
        print(f"   ✅ Synced {total_synced} transactions in {sync_duration:.2f}s")
        print(f"   ✅ Average sync rate: {total_synced / sync_duration:.2f} transactions/second")
    
    def test_100_concurrent_api_sync_requests(self):
        """
        Test 100 concurrent API sync requests.
        This tests the API layer's ability to handle concurrent sync requests.
        """
        print("\n🌐 Starting 100 concurrent API sync requests test...")
        
        # Create authenticated clients for API testing
        with tenant_context(self.tenant):
            user = self.users[0]
            
            # Create offline transactions for API testing
            device_count = 100
            transactions_per_device = 5
            
            print(f"📋 Creating offline transactions for {device_count} devices...")
            
            for i in range(device_count):
                device_id = f'API-SYNC-{i:03d}'
                offline_pos = OfflinePOSSystem(
                    device_id=device_id,
                    device_name=f'API Sync Device {device_id}'
                )
                
                for j in range(transactions_per_device):
                    customer = random.choice(self.customers)
                    item = random.choice(self.jewelry_items)
                    
                    offline_pos.create_offline_transaction(
                        customer_id=customer.id,
                        line_items=[{
                            'jewelry_item_id': item.id,
                            'item_name': item.name,
                            'item_sku': item.sku,
                            'quantity': 1,
                            'unit_price': str(item.selling_price),
                            'gold_weight_grams': str(item.weight_grams),
                            'gold_karat': item.karat
                        }],
                        payment_method='cash',
                        amount_paid=item.selling_price
                    )
            
            print(f"✅ Created {device_count * transactions_per_device} offline transactions")
        
        def make_api_sync_request(device_index):
            """Make API sync request for a device."""
            result = {
                'device_index': device_index,
                'device_id': f'API-SYNC-{device_index:03d}',
                'success': False,
                'sync_count': 0,
                'response_time': 0,
                'error': None
            }
            
            try:
                with tenant_context(self.tenant):
                    client = Client()
                    login_success = client.login(username=user.username, password='testpass123')
                    
                    if not login_success:
                        result['error'] = 'Login failed'
                        return result
                    
                    url = reverse('pos:api_offline_sync')
                    
                    data = {
                        'device_id': result['device_id'],
                        'device_name': f'API Sync Device {result["device_id"]}'
                    }
                    
                    start_time = time.time()
                    
                    # Mock connection check
                    with patch('zargar.pos.models.OfflinePOSSystem._check_connection', return_value=True):
                        response = client.post(
                            url,
                            data=json.dumps(data),
                            content_type='application/json'
                        )
                    
                    end_time = time.time()
                    result['response_time'] = end_time - start_time
                    
                    if response.status_code == 200:
                        response_data = json.loads(response.content)
                        if response_data.get('success'):
                            result['success'] = True
                            sync_results = response_data.get('sync_results', {})
                            result['sync_count'] = sync_results.get('synced_successfully', 0)
                        else:
                            result['error'] = response_data.get('error', 'Unknown API error')
                    else:
                        result['error'] = f'HTTP {response.status_code}'
                        
            except Exception as e:
                result['error'] = str(e)
            
            return result
        
        # Make 100 concurrent API requests
        print(f"🌐 Making {device_count} concurrent API sync requests...")
        
        api_start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            api_futures = [
                executor.submit(make_api_sync_request, i)
                for i in range(device_count)
            ]
            
            api_results = []
            for future in concurrent.futures.as_completed(api_futures):
                try:
                    result = future.result(timeout=60)
                    api_results.append(result)
                except Exception as e:
                    print(f"❌ API request failed: {e}")
        
        api_end_time = time.time()
        api_duration = api_end_time - api_start_time
        
        # Analyze API results
        successful_requests = sum(1 for r in api_results if r['success'])
        failed_requests = len(api_results) - successful_requests
        total_synced_via_api = sum(r['sync_count'] for r in api_results if r['success'])
        average_response_time = sum(r['response_time'] for r in api_results) / len(api_results)
        
        print(f"\n📊 API Sync Results:")
        print(f"   Total API requests: {len(api_results)}")
        print(f"   Successful requests: {successful_requests}")
        print(f"   Failed requests: {failed_requests}")
        print(f"   Total synced via API: {total_synced_via_api}")
        print(f"   API duration: {api_duration:.2f}s")
        print(f"   Average response time: {average_response_time:.3f}s")
        print(f"   Requests per second: {len(api_results) / api_duration:.2f}")
        
        # Verify final state
        with tenant_context(self.tenant):
            final_synced = POSOfflineStorage.objects.filter(is_synced=True).count()
            final_pos_transactions = POSTransaction.objects.count()
            
            print(f"   Final synced count: {final_synced}")
            print(f"   Final POS transactions: {final_pos_transactions}")
        
        # API performance assertions
        self.assertGreaterEqual(successful_requests, device_count * 0.95)  # 95% success rate
        self.assertEqual(total_synced_via_api, final_pos_transactions)
        self.assertLess(api_duration, 180)  # Should complete within 3 minutes
        self.assertLess(average_response_time, 5.0)  # Average response under 5 seconds
        
        print(f"\n🎉 100 concurrent API sync test completed successfully!")
    
    def test_stress_test_continuous_operations(self):
        """
        Stress test with continuous operations for 5 minutes.
        Simulates real-world continuous load with mixed operations.
        """
        print("\n⚡ Starting 5-minute stress test with continuous operations...")
        
        test_duration = 300  # 5 minutes
        operation_stats = {
            'create': 0,
            'sync': 0,
            'status': 0,
            'errors': 0
        }
        
        def continuous_operations_worker(worker_id):
            """Worker that continuously performs operations."""
            worker_stats = {
                'create': 0,
                'sync': 0,
                'status': 0,
                'errors': 0
            }
            
            start_time = time.time()
            
            while time.time() - start_time < test_duration:
                try:
                    with tenant_context(self.tenant):
                        device_id = f'STRESS-{worker_id:03d}'
                        offline_pos = OfflinePOSSystem(
                            device_id=device_id,
                            device_name=f'Stress Test Device {device_id}'
                        )
                        
                        # Random operation
                        operation = random.choice(['create', 'create', 'sync', 'status'])  # Bias towards create
                        
                        if operation == 'create':
                            # Create offline transaction
                            customer = random.choice(self.customers)
                            item = random.choice(self.jewelry_items)
                            
                            offline_pos.create_offline_transaction(
                                customer_id=customer.id,
                                line_items=[{
                                    'jewelry_item_id': item.id,
                                    'item_name': item.name,
                                    'item_sku': item.sku,
                                    'quantity': 1,
                                    'unit_price': str(item.selling_price),
                                    'gold_weight_grams': str(item.weight_grams),
                                    'gold_karat': item.karat
                                }],
                                payment_method='cash',
                                amount_paid=item.selling_price
                            )
                            worker_stats['create'] += 1
                            
                        elif operation == 'sync':
                            # Sync offline transactions
                            with patch('zargar.pos.models.OfflinePOSSystem._check_connection', return_value=True):
                                offline_pos.sync_offline_transactions()
                            worker_stats['sync'] += 1
                            
                        elif operation == 'status':
                            # Get status
                            offline_pos.get_offline_transaction_summary()
                            worker_stats['status'] += 1
                        
                        # Small delay to prevent overwhelming
                        time.sleep(random.uniform(0.01, 0.1))
                        
                except Exception as e:
                    worker_stats['errors'] += 1
            
            return worker_stats
        
        # Run stress test with 50 concurrent workers
        worker_count = 50
        
        print(f"⚡ Running stress test with {worker_count} workers for {test_duration}s...")
        
        stress_start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            stress_futures = [
                executor.submit(continuous_operations_worker, i)
                for i in range(worker_count)
            ]
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(stress_futures):
                try:
                    worker_stats = future.result()
                    for op, count in worker_stats.items():
                        operation_stats[op] += count
                except Exception as e:
                    operation_stats['errors'] += 1
                    print(f"❌ Worker failed: {e}")
        
        stress_end_time = time.time()
        actual_duration = stress_end_time - stress_start_time
        
        # Calculate rates
        total_operations = sum(operation_stats.values()) - operation_stats['errors']
        operations_per_second = total_operations / actual_duration
        
        print(f"\n📊 Stress Test Results ({actual_duration:.1f}s):")
        print(f"   Create operations: {operation_stats['create']}")
        print(f"   Sync operations: {operation_stats['sync']}")
        print(f"   Status operations: {operation_stats['status']}")
        print(f"   Total operations: {total_operations}")
        print(f"   Errors: {operation_stats['errors']}")
        print(f"   Operations per second: {operations_per_second:.2f}")
        print(f"   Error rate: {operation_stats['errors'] / (total_operations + operation_stats['errors']) * 100:.2f}%")
        
        # Verify system state after stress test
        with tenant_context(self.tenant):
            final_offline_total = POSOfflineStorage.objects.count()
            final_offline_synced = POSOfflineStorage.objects.filter(is_synced=True).count()
            final_pos_transactions = POSTransaction.objects.count()
            
            print(f"   Final offline total: {final_offline_total}")
            print(f"   Final offline synced: {final_offline_synced}")
            print(f"   Final POS transactions: {final_pos_transactions}")
        
        # Stress test assertions
        self.assertGreater(total_operations, 1000)  # Should perform at least 1000 operations
        self.assertLess(operation_stats['errors'] / (total_operations + operation_stats['errors']), 0.05)  # Less than 5% error rate
        self.assertGreater(operations_per_second, 10)  # At least 10 operations per second
        self.assertEqual(final_offline_synced, final_pos_transactions)  # Data integrity
        
        print(f"\n🎉 Stress test completed successfully!")
        print(f"   ✅ Performed {total_operations} operations in {actual_duration:.1f}s")
        print(f"   ✅ Maintained {operations_per_second:.2f} operations/second")
        print(f"   ✅ Error rate: {operation_stats['errors'] / (total_operations + operation_stats['errors']) * 100:.2f}%")


if __name__ == '__main__':
    import unittest
    
    print("=" * 80)
    print("POS OFFLINE HEAVY LOAD TEST - 100 CONCURRENT OPERATIONS")
    print("=" * 80)
    
    unittest.main(verbosity=2)