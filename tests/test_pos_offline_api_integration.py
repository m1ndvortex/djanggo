"""
Real API integration tests for POS offline sync system.
Tests actual HTTP endpoints with real database operations and tenant isolation.
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
from decimal import Decimal
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.utils import get_tenant_model, tenant_context
from unittest.mock import patch

from zargar.pos.models import POSTransaction, POSOfflineStorage
from zargar.customers.models import Customer
from zargar.jewelry.models import JewelryItem, Category
from zargar.gold_installments.services import GoldPriceService

User = get_user_model()


class POSOfflineAPIIntegrationTest(TransactionTestCase):
    """
    Integration tests for POS offline API endpoints.
    Tests real HTTP requests, authentication, and database operations.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with tenant."""
        super().setUpClass()
        
        # Create tenant for API testing
        Tenant = get_tenant_model()
        cls.tenant = Tenant.objects.create(
            schema_name='test_pos_api_integration',
            name='Test POS API Integration Shop',
            owner_name='API Test Owner',
            owner_email='apitest@test.com'
        )
        cls.tenant.create_schema(check_if_exists=True)
    
    def setUp(self):
        """Set up test data."""
        with tenant_context(self.tenant):
            # Create users with different roles
            self.owner_user = User.objects.create_user(
                username='owner_user',
                email='owner@test.com',
                password='testpass123',
                role='owner'
            )
            
            self.salesperson_user = User.objects.create_user(
                username='salesperson_user',
                email='salesperson@test.com',
                password='testpass123',
                role='salesperson'
            )
            
            # Create customers
            self.customers = []
            for i in range(10):
                customer = Customer.objects.create(
                    first_name=f'مشتری{i}',
                    last_name='تست',
                    persian_first_name=f'مشتری{i}',
                    persian_last_name='تست',
                    phone_number=f'0912345{i:04d}',
                    email=f'customer{i}@test.com'
                )
                self.customers.append(customer)
            
            # Create jewelry items
            self.category = Category.objects.create(
                name='API Test Items',
                name_persian='اقلام تست API'
            )
            
            self.jewelry_items = []
            for i in range(20):
                item = JewelryItem.objects.create(
                    name=f'API Test Item {i}',
                    category=self.category,
                    sku=f'API-{i:03d}',
                    weight_grams=Decimal(f'{5.0 + i * 0.5:.1f}'),
                    karat=18,
                    manufacturing_cost=Decimal('500000.00'),
                    selling_price=Decimal(f'{2000000 + i * 100000}.00'),
                    quantity=100,
                    status='in_stock'
                )
                self.jewelry_items.append(item)
    
    def test_api_authentication_and_authorization(self):
        """Test API authentication and role-based authorization."""
        with tenant_context(self.tenant):
            # Test unauthenticated access
            client = Client()
            
            url = reverse('pos:api_offline_create')
            data = {'test': 'data'}
            
            response = client.post(
                url,
                data=json.dumps(data),
                content_type='application/json'
            )
            
            # Should require authentication
            self.assertIn(response.status_code, [302, 401, 403])
            
            # Test authenticated access with salesperson
            client.login(username='salesperson_user', password='testpass123')
            
            customer = self.customers[0]
            item = self.jewelry_items[0]
            
            valid_data = {
                'device_id': 'AUTH-TEST-001',
                'device_name': 'Auth Test Device',
                'customer_id': customer.id,
                'line_items': [{
                    'jewelry_item_id': item.id,
                    'item_name': item.name,
                    'item_sku': item.sku,
                    'quantity': 1,
                    'unit_price': str(item.selling_price),
                    'gold_weight_grams': str(item.weight_grams),
                    'gold_karat': item.karat
                }],
                'payment_method': 'cash',
                'amount_paid': str(item.selling_price),
                'transaction_type': 'sale'
            }
            
            response = client.post(
                url,
                data=json.dumps(valid_data),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            
            response_data = json.loads(response.content)
            self.assertTrue(response_data['success'])
    
    def test_offline_transaction_creation_api_comprehensive(self):
        """Test comprehensive offline transaction creation via API."""
        with tenant_context(self.tenant):
            client = Client()
            client.login(username='owner_user', password='testpass123')
            
            url = reverse('pos:api_offline_create')
            
            # Test 1: Single item transaction
            customer = self.customers[0]
            item = self.jewelry_items[0]
            
            data = {
                'device_id': 'COMP-TEST-001',
                'device_name': 'Comprehensive Test Device',
                'customer_id': customer.id,
                'line_items': [{
                    'jewelry_item_id': item.id,
                    'item_name': item.name,
                    'item_sku': item.sku,
                    'quantity': 2,
                    'unit_price': str(item.selling_price),
                    'gold_weight_grams': str(item.weight_grams * 2),
                    'gold_karat': item.karat
                }],
                'payment_method': 'cash',
                'amount_paid': str(item.selling_price * 2),
                'transaction_type': 'sale'
            }
            
            response = client.post(
                url,
                data=json.dumps(data),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            
            response_data = json.loads(response.content)
            self.assertTrue(response_data['success'])
            self.assertIn('storage_id', response_data)
            
            # Verify in database
            storage_id = response_data['storage_id']
            offline_storage = POSOfflineStorage.objects.get(storage_id=storage_id)
            
            self.assertEqual(offline_storage.device_id, 'COMP-TEST-001')
            self.assertEqual(offline_storage.sync_status, 'pending')
            
            transaction_data = offline_storage.transaction_data
            self.assertEqual(transaction_data['customer_id'], customer.id)
            self.assertEqual(len(transaction_data['line_items']), 1)
            self.assertEqual(Decimal(transaction_data['total_amount']), item.selling_price * 2)
            
            # Test 2: Multiple items transaction
            items = self.jewelry_items[1:4]
            line_items = []
            total_expected = Decimal('0.00')
            
            for i, item in enumerate(items):
                quantity = i + 1
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
                total_expected += item.selling_price * quantity
            
            data = {
                'device_id': 'COMP-TEST-002',
                'device_name': 'Multi Item Test Device',
                'customer_id': customer.id,
                'line_items': line_items,
                'payment_method': 'card',
                'amount_paid': str(total_expected),
                'transaction_type': 'sale'
            }
            
            response = client.post(
                url,
                data=json.dumps(data),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            
            response_data = json.loads(response.content)
            self.assertTrue(response_data['success'])
            
            # Verify multi-item transaction
            storage_id = response_data['storage_id']
            offline_storage = POSOfflineStorage.objects.get(storage_id=storage_id)
            
            transaction_data = offline_storage.transaction_data
            self.assertEqual(len(transaction_data['line_items']), 3)
            self.assertEqual(Decimal(transaction_data['total_amount']), total_expected)
            
            # Test 3: Walk-in customer (no customer_id)
            item = self.jewelry_items[4]
            
            data = {
                'device_id': 'COMP-TEST-003',
                'device_name': 'Walk-in Test Device',
                'customer_id': None,
                'line_items': [{
                    'jewelry_item_id': item.id,
                    'item_name': item.name,
                    'item_sku': item.sku,
                    'quantity': 1,
                    'unit_price': str(item.selling_price),
                    'gold_weight_grams': str(item.weight_grams),
                    'gold_karat': item.karat
                }],
                'payment_method': 'cash',
                'amount_paid': str(item.selling_price),
                'transaction_type': 'sale'
            }
            
            response = client.post(
                url,
                data=json.dumps(data),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            
            response_data = json.loads(response.content)
            self.assertTrue(response_data['success'])
            
            # Verify walk-in transaction
            storage_id = response_data['storage_id']
            offline_storage = POSOfflineStorage.objects.get(storage_id=storage_id)
            
            transaction_data = offline_storage.transaction_data
            self.assertIsNone(transaction_data['customer_id'])
    
    def test_offline_status_api_detailed(self):
        """Test detailed offline status API functionality."""
        with tenant_context(self.tenant):
            client = Client()
            client.login(username='owner_user', password='testpass123')
            
            # Create multiple offline transactions for different devices
            devices_data = [
                ('STATUS-DEVICE-001', 'Status Test Device 1', 3),
                ('STATUS-DEVICE-002', 'Status Test Device 2', 5),
                ('STATUS-DEVICE-003', 'Status Test Device 3', 2),
            ]
            
            for device_id, device_name, transaction_count in devices_data:
                for i in range(transaction_count):
                    customer = self.customers[i % len(self.customers)]
                    item = self.jewelry_items[i % len(self.jewelry_items)]
                    
                    # Create some synced and some pending
                    is_synced = i % 2 == 0
                    
                    offline_storage = POSOfflineStorage.objects.create(
                        device_id=device_id,
                        device_name=device_name,
                        transaction_data={
                            'transaction_id': f'test-{device_id}-{i}',
                            'customer_id': customer.id,
                            'line_items': [{
                                'jewelry_item_id': item.id,
                                'item_name': item.name,
                                'quantity': 1,
                                'unit_price': str(item.selling_price)
                            }],
                            'total_amount': str(item.selling_price),
                            'payment_method': 'cash'
                        },
                        is_synced=is_synced,
                        sync_status='synced' if is_synced else 'pending',
                        synced_at=timezone.now() if is_synced else None
                    )
            
            # Test status API for each device
            url = reverse('pos:api_offline_status')
            
            for device_id, device_name, transaction_count in devices_data:
                response = client.get(url, {
                    'device_id': device_id,
                    'device_name': device_name
                })
                
                self.assertEqual(response.status_code, 200)
                
                response_data = json.loads(response.content)
                self.assertTrue(response_data['success'])
                
                summary = response_data['summary']
                self.assertEqual(summary['device_id'], device_id)
                self.assertEqual(summary['total_transactions'], transaction_count)
                
                # Verify counts based on our creation pattern
                expected_synced = (transaction_count + 1) // 2  # Every other one is synced
                expected_pending = transaction_count - expected_synced
                
                self.assertEqual(summary['synced'], expected_synced)
                self.assertEqual(summary['pending_sync'], expected_pending)
    
    def test_offline_sync_api_with_real_transactions(self):
        """Test offline sync API with real transaction processing."""
        with tenant_context(self.tenant):
            client = Client()
            client.login(username='owner_user', password='testpass123')
            
            # Create offline transactions to sync
            device_id = 'SYNC-API-TEST-001'
            device_name = 'Sync API Test Device'
            
            offline_transactions = []
            for i in range(5):
                customer = self.customers[i]
                item = self.jewelry_items[i]
                
                offline_storage = POSOfflineStorage.objects.create(
                    device_id=device_id,
                    device_name=device_name,
                    transaction_data={
                        'transaction_id': f'sync-test-{i}',
                        'customer_id': customer.id,
                        'transaction_type': 'sale',
                        'payment_method': 'cash',
                        'subtotal': str(item.selling_price),
                        'tax_amount': '0.00',
                        'discount_amount': '0.00',
                        'total_amount': str(item.selling_price),
                        'amount_paid': str(item.selling_price),
                        'line_items': [{
                            'jewelry_item_id': item.id,
                            'item_name': item.name,
                            'item_sku': item.sku,
                            'quantity': 1,
                            'unit_price': str(item.selling_price),
                            'gold_weight_grams': str(item.weight_grams),
                            'gold_karat': item.karat
                        }]
                    }
                )
                offline_transactions.append(offline_storage)
            
            # Verify initial state
            self.assertEqual(POSOfflineStorage.objects.filter(device_id=device_id, is_synced=False).count(), 5)
            self.assertEqual(POSTransaction.objects.count(), 0)
            
            # Test sync API
            url = reverse('pos:api_offline_sync')
            
            data = {
                'device_id': device_id,
                'device_name': device_name
            }
            
            # Mock connection check to simulate online status
            with patch('zargar.pos.models.OfflinePOSSystem._check_connection', return_value=True):
                response = client.post(
                    url,
                    data=json.dumps(data),
                    content_type='application/json'
                )
            
            self.assertEqual(response.status_code, 200)
            
            response_data = json.loads(response.content)
            self.assertTrue(response_data['success'])
            
            sync_results = response_data['sync_results']
            self.assertEqual(sync_results['total_pending'], 5)
            self.assertEqual(sync_results['synced_successfully'], 5)
            self.assertEqual(sync_results['failed'], 0)
            
            # Verify sync results in database
            synced_storages = POSOfflineStorage.objects.filter(device_id=device_id, is_synced=True)
            self.assertEqual(synced_storages.count(), 5)
            
            pos_transactions = POSTransaction.objects.all()
            self.assertEqual(pos_transactions.count(), 5)
            
            # Verify transaction data integrity
            for pos_transaction in pos_transactions:
                self.assertEqual(pos_transaction.status, 'completed')
                self.assertIsNotNone(pos_transaction.customer)
                self.assertEqual(pos_transaction.line_items.count(), 1)
                
                line_item = pos_transaction.line_items.first()
                self.assertIsNotNone(line_item.jewelry_item)
                self.assertEqual(line_item.quantity, 1)
    
    def test_api_error_handling_and_validation(self):
        """Test API error handling and input validation."""
        with tenant_context(self.tenant):
            client = Client()
            client.login(username='owner_user', password='testpass123')
            
            url = reverse('pos:api_offline_create')
            
            # Test 1: Invalid JSON
            response = client.post(
                url,
                data='invalid json',
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 400)
            
            response_data = json.loads(response.content)
            self.assertFalse(response_data['success'])
            self.assertIn('error', response_data)
            
            # Test 2: Missing required fields
            data = {
                'device_id': 'ERROR-TEST-001'
                # Missing other required fields
            }
            
            response = client.post(
                url,
                data=json.dumps(data),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 400)
            
            response_data = json.loads(response.content)
            self.assertFalse(response_data['success'])
            
            # Test 3: Invalid customer ID
            item = self.jewelry_items[0]
            
            data = {
                'device_id': 'ERROR-TEST-002',
                'device_name': 'Error Test Device',
                'customer_id': 99999,  # Non-existent customer
                'line_items': [{
                    'jewelry_item_id': item.id,
                    'item_name': item.name,
                    'item_sku': item.sku,
                    'quantity': 1,
                    'unit_price': str(item.selling_price),
                    'gold_weight_grams': str(item.weight_grams),
                    'gold_karat': item.karat
                }],
                'payment_method': 'cash',
                'amount_paid': str(item.selling_price),
                'transaction_type': 'sale'
            }
            
            response = client.post(
                url,
                data=json.dumps(data),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 400)
            
            response_data = json.loads(response.content)
            self.assertFalse(response_data['success'])
            
            # Test 4: Invalid jewelry item ID
            customer = self.customers[0]
            
            data = {
                'device_id': 'ERROR-TEST-003',
                'device_name': 'Error Test Device',
                'customer_id': customer.id,
                'line_items': [{
                    'jewelry_item_id': 99999,  # Non-existent item
                    'item_name': 'Non-existent Item',
                    'item_sku': 'NON-EXIST',
                    'quantity': 1,
                    'unit_price': '1000000.00',
                    'gold_weight_grams': '5.0',
                    'gold_karat': 18
                }],
                'payment_method': 'cash',
                'amount_paid': '1000000.00',
                'transaction_type': 'sale'
            }
            
            response = client.post(
                url,
                data=json.dumps(data),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 400)
            
            response_data = json.loads(response.content)
            self.assertFalse(response_data['success'])
    
    def test_api_performance_with_large_transactions(self):
        """Test API performance with large transactions."""
        with tenant_context(self.tenant):
            client = Client()
            client.login(username='owner_user', password='testpass123')
            
            url = reverse('pos:api_offline_create')
            
            # Create large transaction with many line items
            customer = self.customers[0]
            line_items = []
            total_amount = Decimal('0.00')
            
            # Add all available jewelry items
            for item in self.jewelry_items:
                line_item = {
                    'jewelry_item_id': item.id,
                    'item_name': item.name,
                    'item_sku': item.sku,
                    'quantity': 2,
                    'unit_price': str(item.selling_price),
                    'gold_weight_grams': str(item.weight_grams * 2),
                    'gold_karat': item.karat
                }
                line_items.append(line_item)
                total_amount += item.selling_price * 2
            
            data = {
                'device_id': 'PERF-TEST-001',
                'device_name': 'Performance Test Device',
                'customer_id': customer.id,
                'line_items': line_items,
                'payment_method': 'card',
                'amount_paid': str(total_amount),
                'transaction_type': 'sale'
            }
            
            # Measure response time
            start_time = time.time()
            
            response = client.post(
                url,
                data=json.dumps(data),
                content_type='application/json'
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            self.assertEqual(response.status_code, 200)
            
            response_data = json.loads(response.content)
            self.assertTrue(response_data['success'])
            
            # Verify large transaction was created
            storage_id = response_data['storage_id']
            offline_storage = POSOfflineStorage.objects.get(storage_id=storage_id)
            
            transaction_data = offline_storage.transaction_data
            self.assertEqual(len(transaction_data['line_items']), len(self.jewelry_items))
            self.assertEqual(Decimal(transaction_data['total_amount']), total_amount)
            
            # Performance assertion (should complete within reasonable time)
            self.assertLess(response_time, 5.0)  # Should complete within 5 seconds
            
            print(f"Large transaction API response time: {response_time:.3f}s")
            print(f"Line items count: {len(line_items)}")
            print(f"Total amount: {total_amount}")
    
    def test_concurrent_api_requests(self):
        """Test concurrent API requests to ensure thread safety."""
        with tenant_context(self.tenant):
            client = Client()
            client.login(username='owner_user', password='testpass123')
            
            url = reverse('pos:api_offline_create')
            
            def make_api_request(request_id):
                """Make a single API request."""
                customer = self.customers[request_id % len(self.customers)]
                item = self.jewelry_items[request_id % len(self.jewelry_items)]
                
                data = {
                    'device_id': f'CONCURRENT-{request_id:03d}',
                    'device_name': f'Concurrent Test Device {request_id}',
                    'customer_id': customer.id,
                    'line_items': [{
                        'jewelry_item_id': item.id,
                        'item_name': item.name,
                        'item_sku': item.sku,
                        'quantity': 1,
                        'unit_price': str(item.selling_price),
                        'gold_weight_grams': str(item.weight_grams),
                        'gold_karat': item.karat
                    }],
                    'payment_method': 'cash',
                    'amount_paid': str(item.selling_price),
                    'transaction_type': 'sale'
                }
                
                response = client.post(
                    url,
                    data=json.dumps(data),
                    content_type='application/json'
                )
                
                return {
                    'request_id': request_id,
                    'status_code': response.status_code,
                    'success': response.status_code == 200 and json.loads(response.content).get('success', False)
                }
            
            # Make concurrent requests
            import concurrent.futures
            
            request_count = 20
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(make_api_request, i)
                    for i in range(request_count)
                ]
                
                results = []
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    results.append(result)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Analyze results
            successful_requests = sum(1 for r in results if r['success'])
            failed_requests = request_count - successful_requests
            
            print(f"Concurrent API requests: {request_count}")
            print(f"Successful: {successful_requests}")
            print(f"Failed: {failed_requests}")
            print(f"Total time: {total_time:.3f}s")
            print(f"Requests per second: {request_count / total_time:.2f}")
            
            # Verify in database
            created_storages = POSOfflineStorage.objects.filter(
                device_id__startswith='CONCURRENT-'
            ).count()
            
            # Assertions
            self.assertGreaterEqual(successful_requests, request_count * 0.95)  # 95% success rate
            self.assertEqual(successful_requests, created_storages)
            self.assertLess(total_time, 30)  # Should complete within 30 seconds


if __name__ == '__main__':
    import unittest
    
    print("=" * 80)
    print("POS OFFLINE API INTEGRATION TESTS")
    print("=" * 80)
    
    unittest.main(verbosity=2)