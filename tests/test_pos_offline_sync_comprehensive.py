"""
Comprehensive tests for POS offline sync system (Task 12.3).
Tests real API endpoints, tenant isolation, database operations, and heavy load scenarios.
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
from decimal import Decimal
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.utils import get_tenant_model, tenant_context, schema_context
from django.db import transaction, connections
from unittest.mock import patch, MagicMock

from zargar.pos.models import POSTransaction, POSOfflineStorage, OfflinePOSSystem
from zargar.pos.services import POSOfflineService, POSTransactionService
from zargar.customers.models import Customer
from zargar.jewelry.models import JewelryItem, Category
from zargar.gold_installments.services import GoldPriceService

User = get_user_model()


class POSOfflineSyncComprehensiveTest(TransactionTestCase):
    """
    Comprehensive test suite for POS offline sync functionality.
    Tests real database operations, API endpoints, and tenant isolation.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with multiple tenants."""
        super().setUpClass()
        
        # Create multiple tenants for isolation testing
        Tenant = get_tenant_model()
        
        cls.tenant1 = Tenant.objects.create(
            schema_name='test_pos_sync_1',
            name='Test POS Sync Shop 1',
            owner_name='Test Owner 1',
            owner_email='owner1@test.com'
        )
        
        cls.tenant2 = Tenant.objects.create(
            schema_name='test_pos_sync_2', 
            name='Test POS Sync Shop 2',
            owner_name='Test Owner 2',
            owner_email='owner2@test.com'
        )
        
        # Create schemas
        cls.tenant1.create_schema(check_if_exists=True)
        cls.tenant2.create_schema(check_if_exists=True)
    
    def setUp(self):
        """Set up test data for each tenant."""
        self.setup_tenant_data(self.tenant1)
        self.setup_tenant_data(self.tenant2)
    
    def setup_tenant_data(self, tenant):
        """Set up test data within a tenant context."""
        with tenant_context(tenant):
            # Create user
            user = User.objects.create_user(
                username=f'testuser_{tenant.schema_name}',
                email=f'test_{tenant.schema_name}@example.com',
                password='testpass123'
            )
            
            # Create customers
            customer1 = Customer.objects.create(
                first_name='احمد',
                last_name='محمدی',
                persian_first_name='احمد',
                persian_last_name='محمدی',
                phone_number=f'0912345{tenant.id}001'
            )
            
            customer2 = Customer.objects.create(
                first_name='فاطمه',
                last_name='احمدی',
                persian_first_name='فاطمه',
                persian_last_name='احمدی',
                phone_number=f'0912345{tenant.id}002'
            )
            
            # Create category and jewelry items
            category = Category.objects.create(
                name=f'Test Rings {tenant.schema_name}',
                name_persian=f'انگشتر تست {tenant.schema_name}'
            )
            
            for i in range(10):
                JewelryItem.objects.create(
                    name=f'Gold Ring {i+1} - {tenant.schema_name}',
                    category=category,
                    sku=f'{tenant.schema_name.upper()}-RING-{i+1:03d}',
                    weight_grams=Decimal(f'{5.5 + i * 0.1:.1f}'),
                    karat=18,
                    manufacturing_cost=Decimal('500000.00'),
                    selling_price=Decimal(f'{2500000 + i * 100000}.00'),
                    quantity=50,
                    status='in_stock'
                )
            
            # Store references for later use
            setattr(self, f'user_{tenant.schema_name}', user)
            setattr(self, f'customer1_{tenant.schema_name}', customer1)
            setattr(self, f'customer2_{tenant.schema_name}', customer2)
            setattr(self, f'category_{tenant.schema_name}', category)
    
    def test_offline_transaction_creation_with_real_data(self):
        """Test creating offline transactions with real jewelry items and customers."""
        with tenant_context(self.tenant1):
            # Get test data
            jewelry_items = list(JewelryItem.objects.all()[:3])
            customer = getattr(self, f'customer1_{self.tenant1.schema_name}')
            
            # Create offline POS system
            offline_pos = OfflinePOSSystem(
                device_id='REAL-DATA-TEST-001',
                device_name='Real Data Test Device'
            )
            
            # Create line items with real jewelry data
            line_items = []
            total_expected = Decimal('0.00')
            
            for i, item in enumerate(jewelry_items):
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
            
            # Create offline transaction
            offline_storage = offline_pos.create_offline_transaction(
                customer_id=customer.id,
                line_items=line_items,
                payment_method='cash',
                amount_paid=total_expected,
                transaction_type='sale'
            )
            
            # Verify transaction data
            self.assertIsNotNone(offline_storage)
            self.assertEqual(offline_storage.device_id, 'REAL-DATA-TEST-001')
            self.assertFalse(offline_storage.is_synced)
            self.assertEqual(offline_storage.sync_status, 'pending')
            
            # Verify transaction data structure
            transaction_data = offline_storage.transaction_data
            self.assertEqual(transaction_data['customer_id'], customer.id)
            self.assertEqual(len(transaction_data['line_items']), 3)
            self.assertEqual(Decimal(transaction_data['total_amount']), total_expected)
            
            # Verify line items data
            for i, line_item in enumerate(transaction_data['line_items']):
                expected_item = jewelry_items[i]
                self.assertEqual(line_item['jewelry_item_id'], expected_item.id)
                self.assertEqual(line_item['item_sku'], expected_item.sku)
                self.assertEqual(int(line_item['quantity']), i + 1)
    
    def test_tenant_isolation_in_offline_sync(self):
        """Test that offline transactions are properly isolated between tenants."""
        # Create offline transactions in both tenants
        with tenant_context(self.tenant1):
            customer1 = getattr(self, f'customer1_{self.tenant1.schema_name}')
            jewelry_item1 = JewelryItem.objects.first()
            
            offline_pos1 = OfflinePOSSystem(
                device_id='TENANT1-DEVICE-001',
                device_name='Tenant 1 Device'
            )
            
            storage1 = offline_pos1.create_offline_transaction(
                customer_id=customer1.id,
                line_items=[{
                    'jewelry_item_id': jewelry_item1.id,
                    'item_name': jewelry_item1.name,
                    'item_sku': jewelry_item1.sku,
                    'quantity': 1,
                    'unit_price': str(jewelry_item1.selling_price),
                    'gold_weight_grams': str(jewelry_item1.weight_grams),
                    'gold_karat': jewelry_item1.karat
                }],
                payment_method='cash',
                amount_paid=jewelry_item1.selling_price
            )
        
        with tenant_context(self.tenant2):
            customer2 = getattr(self, f'customer1_{self.tenant2.schema_name}')
            jewelry_item2 = JewelryItem.objects.first()
            
            offline_pos2 = OfflinePOSSystem(
                device_id='TENANT2-DEVICE-001',
                device_name='Tenant 2 Device'
            )
            
            storage2 = offline_pos2.create_offline_transaction(
                customer_id=customer2.id,
                line_items=[{
                    'jewelry_item_id': jewelry_item2.id,
                    'item_name': jewelry_item2.name,
                    'item_sku': jewelry_item2.sku,
                    'quantity': 1,
                    'unit_price': str(jewelry_item2.selling_price),
                    'gold_weight_grams': str(jewelry_item2.weight_grams),
                    'gold_karat': jewelry_item2.karat
                }],
                payment_method='cash',
                amount_paid=jewelry_item2.selling_price
            )
        
        # Verify tenant isolation
        with tenant_context(self.tenant1):
            tenant1_storages = POSOfflineStorage.objects.all()
            self.assertEqual(tenant1_storages.count(), 1)
            self.assertEqual(tenant1_storages.first().device_id, 'TENANT1-DEVICE-001')
            
            # Verify customer data belongs to tenant 1
            transaction_data = tenant1_storages.first().transaction_data
            customer_in_data = Customer.objects.get(id=transaction_data['customer_id'])
            self.assertEqual(customer_in_data.phone_number, customer1.phone_number)
        
        with tenant_context(self.tenant2):
            tenant2_storages = POSOfflineStorage.objects.all()
            self.assertEqual(tenant2_storages.count(), 1)
            self.assertEqual(tenant2_storages.first().device_id, 'TENANT2-DEVICE-001')
            
            # Verify customer data belongs to tenant 2
            transaction_data = tenant2_storages.first().transaction_data
            customer_in_data = Customer.objects.get(id=transaction_data['customer_id'])
            self.assertEqual(customer_in_data.phone_number, customer2.phone_number)
    
    def test_real_api_endpoints_with_authentication(self):
        """Test real API endpoints with proper authentication and tenant context."""
        with tenant_context(self.tenant1):
            user = getattr(self, f'user_{self.tenant1.schema_name}')
            customer = getattr(self, f'customer1_{self.tenant1.schema_name}')
            jewelry_item = JewelryItem.objects.first()
            
            # Create authenticated client
            client = Client()
            login_success = client.login(
                username=user.username,
                password='testpass123'
            )
            self.assertTrue(login_success)
            
            # Test offline transaction creation API
            url = reverse('pos:api_offline_create')
            
            data = {
                'device_id': 'API-TEST-DEVICE-001',
                'device_name': 'API Test Device',
                'customer_id': customer.id,
                'line_items': [{
                    'jewelry_item_id': jewelry_item.id,
                    'item_name': jewelry_item.name,
                    'item_sku': jewelry_item.sku,
                    'quantity': 2,
                    'unit_price': str(jewelry_item.selling_price),
                    'gold_weight_grams': str(jewelry_item.weight_grams * 2),
                    'gold_karat': jewelry_item.karat
                }],
                'payment_method': 'card',
                'amount_paid': str(jewelry_item.selling_price * 2),
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
            
            storage_id = response_data['storage_id']
            
            # Verify offline storage was created
            offline_storage = POSOfflineStorage.objects.get(storage_id=storage_id)
            self.assertEqual(offline_storage.device_id, 'API-TEST-DEVICE-001')
            self.assertEqual(offline_storage.sync_status, 'pending')
            
            # Test offline status API
            status_url = reverse('pos:api_offline_status')
            status_response = client.get(status_url, {
                'device_id': 'API-TEST-DEVICE-001',
                'device_name': 'API Test Device'
            })
            
            self.assertEqual(status_response.status_code, 200)
            
            status_data = json.loads(status_response.content)
            self.assertTrue(status_data['success'])
            
            summary = status_data['summary']
            self.assertEqual(summary['total_transactions'], 1)
            self.assertEqual(summary['pending_sync'], 1)
            self.assertEqual(summary['synced'], 0)
    
    def test_offline_sync_with_inventory_updates(self):
        """Test that offline sync properly updates inventory when synced."""
        with tenant_context(self.tenant1):
            jewelry_item = JewelryItem.objects.first()
            initial_quantity = jewelry_item.quantity
            
            # Create offline transaction
            offline_pos = OfflinePOSSystem(
                device_id='INVENTORY-TEST-001',
                device_name='Inventory Test Device'
            )
            
            sale_quantity = 3
            offline_storage = offline_pos.create_offline_transaction(
                customer_id=None,  # Walk-in customer
                line_items=[{
                    'jewelry_item_id': jewelry_item.id,
                    'item_name': jewelry_item.name,
                    'item_sku': jewelry_item.sku,
                    'quantity': sale_quantity,
                    'unit_price': str(jewelry_item.selling_price),
                    'gold_weight_grams': str(jewelry_item.weight_grams * sale_quantity),
                    'gold_karat': jewelry_item.karat
                }],
                payment_method='cash',
                amount_paid=jewelry_item.selling_price * sale_quantity
            )
            
            # Verify inventory hasn't changed yet (offline)
            jewelry_item.refresh_from_db()
            self.assertEqual(jewelry_item.quantity, initial_quantity)
            
            # Mock connection check to simulate online status
            with patch('zargar.pos.models.OfflinePOSSystem._check_connection', return_value=True):
                # Sync offline transactions
                sync_results = offline_pos.sync_offline_transactions()
                
                self.assertEqual(sync_results['total_pending'], 1)
                self.assertEqual(sync_results['synced_successfully'], 1)
                self.assertEqual(sync_results['failed'], 0)
            
            # Verify inventory was updated
            jewelry_item.refresh_from_db()
            self.assertEqual(jewelry_item.quantity, initial_quantity - sale_quantity)
            
            # Verify offline storage is marked as synced
            offline_storage.refresh_from_db()
            self.assertTrue(offline_storage.is_synced)
            self.assertEqual(offline_storage.sync_status, 'synced')
            self.assertIsNotNone(offline_storage.synced_at)
    
    def test_conflict_resolution_scenarios(self):
        """Test various conflict resolution scenarios."""
        with tenant_context(self.tenant1):
            jewelry_item = JewelryItem.objects.first()
            
            # Create offline transaction
            offline_pos = OfflinePOSSystem(
                device_id='CONFLICT-TEST-001',
                device_name='Conflict Test Device'
            )
            
            # Create transaction that would cause inventory conflict
            offline_storage = offline_pos.create_offline_transaction(
                customer_id=None,
                line_items=[{
                    'jewelry_item_id': jewelry_item.id,
                    'item_name': jewelry_item.name,
                    'item_sku': jewelry_item.sku,
                    'quantity': jewelry_item.quantity + 10,  # More than available
                    'unit_price': str(jewelry_item.selling_price),
                    'gold_weight_grams': str(jewelry_item.weight_grams),
                    'gold_karat': jewelry_item.karat
                }],
                payment_method='cash',
                amount_paid=jewelry_item.selling_price
            )
            
            # Simulate sync that would cause conflict
            offline_storage.sync_status = 'conflict'
            offline_storage.has_conflicts = True
            offline_storage.conflict_details = {
                'type': 'inventory_insufficient',
                'item_id': jewelry_item.id,
                'requested': jewelry_item.quantity + 10,
                'available': jewelry_item.quantity
            }
            offline_storage.save()
            
            # Test retry resolution (should fail due to insufficient inventory)
            success = offline_storage.resolve_conflict('retry')
            self.assertFalse(success)
            self.assertEqual(offline_storage.sync_status, 'conflict')
            
            # Test skip resolution
            success = offline_storage.resolve_conflict('skip')
            self.assertTrue(success)
            self.assertEqual(offline_storage.sync_status, 'skipped')
            self.assertFalse(offline_storage.has_conflicts)
            
            # Test manual resolution with adjusted quantity
            offline_storage.sync_status = 'conflict'
            offline_storage.has_conflicts = True
            offline_storage.save()
            
            # Adjust transaction data
            transaction_data = offline_storage.transaction_data
            transaction_data['line_items'][0]['quantity'] = str(jewelry_item.quantity - 1)
            offline_storage.transaction_data = transaction_data
            offline_storage.save()
            
            success = offline_storage.resolve_conflict('retry')
            self.assertTrue(success)
            self.assertEqual(offline_storage.sync_status, 'pending')


class POSOfflineHeavyLoadTest(TransactionTestCase):
    """
    Heavy load test for POS offline sync system.
    Tests 100 concurrent sync operations to ensure system can handle high load.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test class for load testing."""
        super().setUpClass()
        
        # Create tenant for load testing
        Tenant = get_tenant_model()
        cls.tenant = Tenant.objects.create(
            schema_name='test_pos_load',
            name='Test POS Load Shop',
            owner_name='Load Test Owner',
            owner_email='loadtest@test.com'
        )
        cls.tenant.create_schema(check_if_exists=True)
    
    def setUp(self):
        """Set up test data for load testing."""
        with tenant_context(self.tenant):
            # Create user
            self.user = User.objects.create_user(
                username='loadtest_user',
                email='loadtest@example.com',
                password='testpass123'
            )
            
            # Create customers for load testing
            self.customers = []
            for i in range(50):
                customer = Customer.objects.create(
                    first_name=f'Customer{i}',
                    last_name='LoadTest',
                    persian_first_name=f'مشتری{i}',
                    persian_last_name='تست',
                    phone_number=f'091234567{i:02d}'
                )
                self.customers.append(customer)
            
            # Create jewelry items for load testing
            category = Category.objects.create(
                name='Load Test Items',
                name_persian='اقلام تست بار'
            )
            
            self.jewelry_items = []
            for i in range(100):
                item = JewelryItem.objects.create(
                    name=f'Load Test Item {i}',
                    category=category,
                    sku=f'LOAD-{i:03d}',
                    weight_grams=Decimal(f'{5.0 + i * 0.1:.1f}'),
                    karat=18,
                    manufacturing_cost=Decimal('500000.00'),
                    selling_price=Decimal(f'{1000000 + i * 50000}.00'),
                    quantity=1000,  # High quantity for load testing
                    status='in_stock'
                )
                self.jewelry_items.append(item)
    
    def create_offline_transaction_worker(self, device_id, transaction_count):
        """Worker function to create offline transactions."""
        results = {
            'device_id': device_id,
            'created': 0,
            'errors': [],
            'start_time': time.time()
        }
        
        try:
            with tenant_context(self.tenant):
                offline_pos = OfflinePOSSystem(
                    device_id=device_id,
                    device_name=f'Load Test Device {device_id}'
                )
                
                for i in range(transaction_count):
                    try:
                        # Select random customer and items
                        import random
                        customer = random.choice(self.customers)
                        selected_items = random.sample(self.jewelry_items, random.randint(1, 5))
                        
                        line_items = []
                        total_amount = Decimal('0.00')
                        
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
                            total_amount += item.selling_price * quantity
                        
                        # Create offline transaction
                        offline_storage = offline_pos.create_offline_transaction(
                            customer_id=customer.id,
                            line_items=line_items,
                            payment_method=random.choice(['cash', 'card', 'bank_transfer']),
                            amount_paid=total_amount,
                            transaction_type='sale'
                        )
                        
                        results['created'] += 1
                        
                    except Exception as e:
                        results['errors'].append(f'Transaction {i}: {str(e)}')
                        
        except Exception as e:
            results['errors'].append(f'Worker error: {str(e)}')
        
        results['end_time'] = time.time()
        results['duration'] = results['end_time'] - results['start_time']
        
        return results
    
    def sync_offline_transactions_worker(self, device_id):
        """Worker function to sync offline transactions."""
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
                    device_name=f'Load Test Device {device_id}'
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
    
    def test_concurrent_offline_transaction_creation(self):
        """Test creating 100 concurrent offline transactions."""
        print("\n🚀 Starting concurrent offline transaction creation test...")
        
        # Create 20 devices, each creating 5 transactions concurrently
        device_count = 20
        transactions_per_device = 5
        total_expected = device_count * transactions_per_device
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=device_count) as executor:
            # Submit all creation tasks
            future_to_device = {
                executor.submit(
                    self.create_offline_transaction_worker,
                    f'LOAD-DEVICE-{i:03d}',
                    transactions_per_device
                ): f'LOAD-DEVICE-{i:03d}'
                for i in range(device_count)
            }
            
            # Collect results
            creation_results = []
            for future in concurrent.futures.as_completed(future_to_device):
                device_id = future_to_device[future]
                try:
                    result = future.result(timeout=30)  # 30 second timeout
                    creation_results.append(result)
                    print(f"✅ Device {device_id}: Created {result['created']} transactions in {result['duration']:.2f}s")
                except Exception as e:
                    print(f"❌ Device {device_id} failed: {e}")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze results
        total_created = sum(r['created'] for r in creation_results)
        total_errors = sum(len(r['errors']) for r in creation_results)
        
        print(f"\n📊 Concurrent Creation Results:")
        print(f"   Total devices: {device_count}")
        print(f"   Expected transactions: {total_expected}")
        print(f"   Created transactions: {total_created}")
        print(f"   Total errors: {total_errors}")
        print(f"   Total duration: {total_duration:.2f}s")
        print(f"   Transactions per second: {total_created / total_duration:.2f}")
        
        # Verify in database
        with tenant_context(self.tenant):
            db_count = POSOfflineStorage.objects.count()
            print(f"   Database count: {db_count}")
        
        # Assertions
        self.assertGreaterEqual(total_created, total_expected * 0.95)  # Allow 5% failure rate
        self.assertEqual(total_created, db_count)
        self.assertLess(total_duration, 60)  # Should complete within 60 seconds
    
    def test_concurrent_offline_sync_operations(self):
        """Test syncing 100 offline transactions concurrently."""
        print("\n🔄 Starting concurrent offline sync test...")
        
        # First, create offline transactions to sync
        device_count = 20
        transactions_per_device = 5
        
        print("   Creating offline transactions...")
        with tenant_context(self.tenant):
            for i in range(device_count):
                device_id = f'SYNC-DEVICE-{i:03d}'
                offline_pos = OfflinePOSSystem(
                    device_id=device_id,
                    device_name=f'Sync Test Device {device_id}'
                )
                
                for j in range(transactions_per_device):
                    import random
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
        
        print(f"   Created {device_count * transactions_per_device} offline transactions")
        
        # Now sync them concurrently
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=device_count) as executor:
            # Submit all sync tasks
            future_to_device = {
                executor.submit(
                    self.sync_offline_transactions_worker,
                    f'SYNC-DEVICE-{i:03d}'
                ): f'SYNC-DEVICE-{i:03d}'
                for i in range(device_count)
            }
            
            # Collect results
            sync_results = []
            for future in concurrent.futures.as_completed(future_to_device):
                device_id = future_to_device[future]
                try:
                    result = future.result(timeout=60)  # 60 second timeout
                    sync_results.append(result)
                    if result['sync_results']:
                        synced = result['sync_results']['synced_successfully']
                        print(f"✅ Device {device_id}: Synced {synced} transactions in {result['duration']:.2f}s")
                    else:
                        print(f"⚠️ Device {device_id}: No sync results")
                except Exception as e:
                    print(f"❌ Device {device_id} sync failed: {e}")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze results
        total_synced = sum(
            r['sync_results']['synced_successfully'] 
            for r in sync_results 
            if r['sync_results']
        )
        total_failed = sum(
            r['sync_results']['failed'] 
            for r in sync_results 
            if r['sync_results']
        )
        
        print(f"\n📊 Concurrent Sync Results:")
        print(f"   Total devices: {device_count}")
        print(f"   Expected syncs: {device_count * transactions_per_device}")
        print(f"   Successful syncs: {total_synced}")
        print(f"   Failed syncs: {total_failed}")
        print(f"   Total duration: {total_duration:.2f}s")
        print(f"   Syncs per second: {total_synced / total_duration:.2f}")
        
        # Verify in database
        with tenant_context(self.tenant):
            synced_count = POSOfflineStorage.objects.filter(is_synced=True).count()
            pos_transactions = POSTransaction.objects.count()
            print(f"   Database synced count: {synced_count}")
            print(f"   POS transactions created: {pos_transactions}")
        
        # Assertions
        expected_total = device_count * transactions_per_device
        self.assertGreaterEqual(total_synced, expected_total * 0.95)  # Allow 5% failure rate
        self.assertEqual(total_synced, synced_count)
        self.assertEqual(total_synced, pos_transactions)
        self.assertLess(total_duration, 120)  # Should complete within 2 minutes
    
    def test_mixed_concurrent_operations(self):
        """Test mixed concurrent operations: creation, sync, and status checks."""
        print("\n🔀 Starting mixed concurrent operations test...")
        
        operations_count = 100
        start_time = time.time()
        
        def mixed_operation_worker(operation_id):
            """Worker that performs mixed operations."""
            results = {
                'operation_id': operation_id,
                'operations': [],
                'errors': []
            }
            
            try:
                with tenant_context(self.tenant):
                    device_id = f'MIXED-DEVICE-{operation_id % 10:03d}'
                    offline_pos = OfflinePOSSystem(
                        device_id=device_id,
                        device_name=f'Mixed Test Device {device_id}'
                    )
                    
                    import random
                    
                    # Perform random operations
                    for _ in range(random.randint(1, 5)):
                        operation_type = random.choice(['create', 'sync', 'status'])
                        
                        if operation_type == 'create':
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
                            results['operations'].append('create')
                            
                        elif operation_type == 'sync':
                            # Sync offline transactions
                            with patch('zargar.pos.models.OfflinePOSSystem._check_connection', return_value=True):
                                offline_pos.sync_offline_transactions()
                            results['operations'].append('sync')
                            
                        elif operation_type == 'status':
                            # Get status
                            offline_pos.get_offline_transaction_summary()
                            results['operations'].append('status')
                            
            except Exception as e:
                results['errors'].append(str(e))
            
            return results
        
        # Run mixed operations concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [
                executor.submit(mixed_operation_worker, i)
                for i in range(operations_count)
            ]
            
            mixed_results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    mixed_results.append(result)
                except Exception as e:
                    print(f"❌ Mixed operation failed: {e}")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze results
        total_operations = sum(len(r['operations']) for r in mixed_results)
        total_errors = sum(len(r['errors']) for r in mixed_results)
        operation_counts = {}
        
        for result in mixed_results:
            for op in result['operations']:
                operation_counts[op] = operation_counts.get(op, 0) + 1
        
        print(f"\n📊 Mixed Operations Results:")
        print(f"   Total workers: {operations_count}")
        print(f"   Total operations: {total_operations}")
        print(f"   Total errors: {total_errors}")
        print(f"   Duration: {total_duration:.2f}s")
        print(f"   Operations per second: {total_operations / total_duration:.2f}")
        print(f"   Operation breakdown: {operation_counts}")
        
        # Verify system stability
        with tenant_context(self.tenant):
            total_offline = POSOfflineStorage.objects.count()
            total_pos = POSTransaction.objects.count()
            print(f"   Total offline storages: {total_offline}")
            print(f"   Total POS transactions: {total_pos}")
        
        # Assertions
        self.assertGreater(total_operations, operations_count)  # Should have multiple ops per worker
        self.assertLess(total_errors / total_operations, 0.05)  # Less than 5% error rate
        self.assertLess(total_duration, 90)  # Should complete within 90 seconds


if __name__ == '__main__':
    import unittest
    
    # Run comprehensive tests
    print("=" * 80)
    print("POS OFFLINE SYNC COMPREHENSIVE TESTS")
    print("=" * 80)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add comprehensive tests
    suite.addTest(unittest.makeSuite(POSOfflineSyncComprehensiveTest))
    
    # Add load tests
    suite.addTest(unittest.makeSuite(POSOfflineHeavyLoadTest))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n🎉 All tests passed successfully!")
    else:
        print(f"\n❌ {len(result.failures)} failures, {len(result.errors)} errors")