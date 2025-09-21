"""
Tests for POS offline system functionality.
Tests offline transaction storage, synchronization, and conflict resolution.
"""
import os
import django
from django.conf import settings

# Setup Django
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from zargar.pos.models import (
    POSTransaction, POSTransactionLineItem, POSOfflineStorage, OfflinePOSSystem
)
from zargar.pos.services import POSOfflineService
from zargar.jewelry.models import JewelryItem, Category
from zargar.customers.models import Customer
from zargar.core.models import User

User = get_user_model()


class POSOfflineStorageModelTest(TestCase):
    """Test POSOfflineStorage model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.customer = Customer.objects.create(
            first_name='احمد',
            last_name='محمدی',
            persian_first_name='احمد',
            persian_last_name='محمدی',
            phone_number='09123456789',
            email='ahmad@example.com'
        )
        
        self.category = Category.objects.create(
            name='Rings',
            name_persian='انگشتر',
            description='Gold rings'
        )
        
        self.jewelry_item = JewelryItem.objects.create(
            name='Gold Ring 18K',
            name_persian='انگشتر طلای ۱۸ عیار',
            category=self.category,
            sku='RING-001',
            weight_grams=Decimal('5.500'),
            karat=18,
            manufacturing_cost=Decimal('500000.00'),
            selling_price=Decimal('2500000.00'),
            quantity=10,
            status='in_stock'
        )
        
        self.transaction_data = {
            'transaction_id': 'test-transaction-123',
            'customer_id': self.customer.id,
            'transaction_date': timezone.now().isoformat(),
            'transaction_type': 'sale',
            'payment_method': 'cash',
            'subtotal': '2500000.00',
            'tax_amount': '0.00',
            'discount_amount': '0.00',
            'total_amount': '2500000.00',
            'amount_paid': '2500000.00',
            'gold_price_18k_at_transaction': '4500000.00',
            'line_items': [
                {
                    'jewelry_item_id': self.jewelry_item.id,
                    'item_name': 'Gold Ring 18K',
                    'item_sku': 'RING-001',
                    'quantity': '1',
                    'unit_price': '2500000.00',
                    'gold_weight_grams': '5.500',
                    'gold_karat': 18
                }
            ],
            'offline_created_at': timezone.now().isoformat()
        }
    
    def test_create_offline_storage(self):
        """Test creating offline storage record."""
        offline_storage = POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            device_name='Test POS Device',
            transaction_data=self.transaction_data
        )
        
        self.assertIsNotNone(offline_storage.storage_id)
        self.assertEqual(offline_storage.device_id, 'TEST-DEVICE-001')
        self.assertEqual(offline_storage.sync_status, 'pending')
        self.assertFalse(offline_storage.is_synced)
        self.assertEqual(offline_storage.transaction_data, self.transaction_data)
    
    def test_sync_to_database_success(self):
        """Test successful sync to database."""
        offline_storage = POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            device_name='Test POS Device',
            transaction_data=self.transaction_data
        )
        
        # Mock gold price service
        with patch('zargar.pos.models.GoldPriceService') as mock_gold_service:
            mock_gold_service.get_current_gold_price.return_value = {
                'price_per_gram': Decimal('4500000.00')
            }
            
            success = offline_storage.sync_to_database()
        
        self.assertTrue(success)
        self.assertTrue(offline_storage.is_synced)
        self.assertEqual(offline_storage.sync_status, 'synced')
        self.assertIsNotNone(offline_storage.synced_at)
        self.assertIsNotNone(offline_storage.synced_transaction_id)
        
        # Verify transaction was created
        transaction = POSTransaction.objects.get(
            transaction_id=offline_storage.synced_transaction_id
        )
        self.assertEqual(transaction.customer, self.customer)
        self.assertEqual(transaction.total_amount, Decimal('2500000.00'))
        self.assertTrue(transaction.is_offline_transaction)
        
        # Verify line item was created
        line_items = transaction.line_items.all()
        self.assertEqual(line_items.count(), 1)
        self.assertEqual(line_items[0].jewelry_item, self.jewelry_item)
    
    def test_sync_to_database_failure(self):
        """Test sync failure handling."""
        # Create invalid transaction data (missing required fields)
        invalid_data = {
            'transaction_id': 'invalid-transaction',
            'invalid_field': 'invalid_value'
        }
        
        offline_storage = POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=invalid_data
        )
        
        success = offline_storage.sync_to_database()
        
        self.assertFalse(success)
        self.assertFalse(offline_storage.is_synced)
        self.assertEqual(offline_storage.sync_status, 'failed')
        self.assertIsNotNone(offline_storage.sync_error)
        self.assertEqual(offline_storage.sync_retry_count, 1)
    
    def test_sync_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded."""
        invalid_data = {'invalid': 'data'}
        
        offline_storage = POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=invalid_data,
            max_retry_attempts=2
        )
        
        # First attempt
        offline_storage.sync_to_database()
        self.assertEqual(offline_storage.sync_retry_count, 1)
        self.assertEqual(offline_storage.sync_status, 'failed')
        
        # Second attempt
        offline_storage.sync_to_database()
        self.assertEqual(offline_storage.sync_retry_count, 2)
        self.assertEqual(offline_storage.sync_status, 'conflict')
        self.assertTrue(offline_storage.has_conflicts)
        self.assertIsNotNone(offline_storage.conflict_data)
    
    def test_resolve_conflict_retry(self):
        """Test resolving conflict with retry action."""
        offline_storage = POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=self.transaction_data,
            sync_status='conflict',
            has_conflicts=True,
            sync_retry_count=3
        )
        
        success = offline_storage.resolve_conflict('retry')
        
        self.assertTrue(success)
        self.assertEqual(offline_storage.sync_status, 'pending')
        self.assertFalse(offline_storage.has_conflicts)
        self.assertEqual(offline_storage.sync_retry_count, 0)
    
    def test_resolve_conflict_skip(self):
        """Test resolving conflict with skip action."""
        offline_storage = POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=self.transaction_data,
            sync_status='conflict',
            has_conflicts=True
        )
        
        success = offline_storage.resolve_conflict('skip')
        
        self.assertTrue(success)
        self.assertEqual(offline_storage.sync_status, 'failed')
        self.assertFalse(offline_storage.has_conflicts)
        self.assertEqual(offline_storage.conflict_data['resolution'], 'skipped')
    
    def test_resolve_conflict_manual_merge(self):
        """Test resolving conflict with manual merge."""
        offline_storage = POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=self.transaction_data,
            sync_status='conflict',
            has_conflicts=True
        )
        
        resolution_data = {'total_amount': '2600000.00'}
        success = offline_storage.resolve_conflict('manual_merge', resolution_data)
        
        self.assertTrue(success)
        self.assertEqual(offline_storage.sync_status, 'pending')
        self.assertFalse(offline_storage.has_conflicts)
        self.assertEqual(offline_storage.transaction_data['total_amount'], '2600000.00')
    
    def test_get_transaction_summary(self):
        """Test getting transaction summary."""
        offline_storage = POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            device_name='Test Device',
            transaction_data=self.transaction_data
        )
        
        summary = offline_storage.get_transaction_summary()
        
        self.assertEqual(summary['device_name'], 'Test Device')
        self.assertEqual(summary['total_amount'], '2500000.00')
        self.assertEqual(summary['payment_method'], 'cash')
        self.assertEqual(summary['line_items_count'], 1)
        self.assertEqual(summary['sync_status'], 'pending')
        self.assertFalse(summary['has_conflicts'])


class OfflinePOSSystemTest(TestCase):
    """Test OfflinePOSSystem class functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.customer = Customer.objects.create(
            first_name='احمد',
            last_name='محمدی',
            persian_first_name='احمد',
            persian_last_name='محمدی',
            phone_number='09123456789'
        )
        
        self.category = Category.objects.create(
            name='Rings',
            name_persian='انگشتر'
        )
        
        self.jewelry_item = JewelryItem.objects.create(
            name='Gold Ring 18K',
            category=self.category,
            sku='RING-001',
            weight_grams=Decimal('5.500'),
            karat=18,
            selling_price=Decimal('2500000.00'),
            quantity=10,
            status='in_stock'
        )
        
        self.offline_pos = OfflinePOSSystem(
            device_id='TEST-DEVICE-001',
            device_name='Test POS Device'
        )
    
    @patch('zargar.pos.models.requests.get')
    def test_check_connection_online(self, mock_get):
        """Test connection check when online."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        is_online = self.offline_pos._check_connection()
        
        self.assertTrue(is_online)
        mock_get.assert_called_once_with('https://www.google.com', timeout=5)
    
    @patch('zargar.pos.models.requests.get')
    def test_check_connection_offline(self, mock_get):
        """Test connection check when offline."""
        mock_get.side_effect = Exception('Connection failed')
        
        is_online = self.offline_pos._check_connection()
        
        self.assertFalse(is_online)
    
    def test_generate_device_id(self):
        """Test device ID generation."""
        device_id = self.offline_pos._generate_device_id()
        
        self.assertIsInstance(device_id, str)
        self.assertTrue(device_id.startswith('POS-'))
        self.assertEqual(len(device_id), 16)  # POS- + 12 characters
    
    @patch('zargar.gold_installments.services.GoldPriceService.get_current_gold_price')
    def test_create_offline_transaction(self, mock_gold_price):
        """Test creating offline transaction."""
        mock_gold_price.return_value = {
            'price_per_gram': Decimal('4500000.00')
        }
        
        line_items = [
            {
                'jewelry_item_id': self.jewelry_item.id,
                'item_name': 'Gold Ring 18K',
                'item_sku': 'RING-001',
                'quantity': 1,
                'unit_price': '2500000.00',
                'gold_weight_grams': '5.500',
                'gold_karat': 18
            }
        ]
        
        offline_storage = self.offline_pos.create_offline_transaction(
            customer_id=self.customer.id,
            line_items=line_items,
            payment_method='cash',
            amount_paid=Decimal('2500000.00')
        )
        
        self.assertIsInstance(offline_storage, POSOfflineStorage)
        self.assertEqual(offline_storage.device_id, 'TEST-DEVICE-001')
        self.assertEqual(offline_storage.device_name, 'Test POS Device')
        
        transaction_data = offline_storage.transaction_data
        self.assertEqual(transaction_data['customer_id'], self.customer.id)
        self.assertEqual(transaction_data['payment_method'], 'cash')
        self.assertEqual(transaction_data['amount_paid'], '2500000.00')
        self.assertEqual(len(transaction_data['line_items']), 1)
        self.assertEqual(transaction_data['gold_price_18k_at_transaction'], '4500000.00')
    
    @patch.object(OfflinePOSSystem, '_check_connection')
    def test_sync_offline_transactions_no_connection(self, mock_check_connection):
        """Test sync when no connection available."""
        mock_check_connection.return_value = False
        
        result = self.offline_pos.sync_offline_transactions()
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'No internet connection available')
    
    @patch.object(OfflinePOSSystem, '_check_connection')
    def test_sync_offline_transactions_success(self, mock_check_connection):
        """Test successful sync of offline transactions."""
        mock_check_connection.return_value = True
        
        # Create offline transactions
        offline_storage1 = POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=self._create_test_transaction_data()
        )
        
        offline_storage2 = POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=self._create_test_transaction_data()
        )
        
        with patch.object(POSOfflineStorage, 'sync_to_database') as mock_sync:
            mock_sync.return_value = True
            
            result = self.offline_pos.sync_offline_transactions()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_pending'], 2)
        self.assertEqual(result['synced_successfully'], 2)
        self.assertEqual(result['sync_failed'], 0)
        self.assertEqual(result['conflicts'], 0)
    
    @patch.object(OfflinePOSSystem, '_check_connection')
    def test_sync_offline_transactions_with_failures(self, mock_check_connection):
        """Test sync with some failures."""
        mock_check_connection.return_value = True
        
        # Create offline transactions
        offline_storage1 = POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=self._create_test_transaction_data()
        )
        
        offline_storage2 = POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=self._create_test_transaction_data(),
            has_conflicts=True
        )
        
        def mock_sync_side_effect():
            if offline_storage1.id == offline_storage1.id:
                return True
            else:
                offline_storage2.sync_error = 'Test error'
                offline_storage2.has_conflicts = True
                return False
        
        with patch.object(POSOfflineStorage, 'sync_to_database', side_effect=[True, False]):
            result = self.offline_pos.sync_offline_transactions()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_pending'], 2)
        self.assertEqual(result['synced_successfully'], 1)
        self.assertEqual(result['sync_failed'], 0)
        self.assertEqual(result['conflicts'], 1)
    
    def test_get_offline_transaction_summary(self):
        """Test getting offline transaction summary."""
        # Create offline transactions
        POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=self._create_test_transaction_data()
        )
        
        POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=self._create_test_transaction_data(),
            is_synced=True
        )
        
        POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=self._create_test_transaction_data(),
            has_conflicts=True
        )
        
        summary = self.offline_pos.get_offline_transaction_summary()
        
        self.assertEqual(summary['device_id'], 'TEST-DEVICE-001')
        self.assertEqual(summary['device_name'], 'Test POS Device')
        self.assertEqual(summary['total_transactions'], 3)
        self.assertEqual(summary['pending_sync'], 2)  # 2 not synced
        self.assertEqual(summary['synced'], 1)
        self.assertEqual(summary['conflicts'], 1)
        self.assertGreater(summary['total_pending_value'], 0)
    
    def test_resolve_sync_conflicts(self):
        """Test resolving sync conflicts."""
        # Create conflicted transactions
        offline_storage1 = POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=self._create_test_transaction_data(),
            has_conflicts=True
        )
        
        offline_storage2 = POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=self._create_test_transaction_data(),
            has_conflicts=True
        )
        
        resolution_actions = {
            str(offline_storage1.storage_id): 'retry',
            str(offline_storage2.storage_id): 'skip'
        }
        
        result = self.offline_pos.resolve_sync_conflicts(resolution_actions)
        
        self.assertEqual(result['total_conflicts'], 2)
        self.assertEqual(result['resolved'], 2)
        self.assertEqual(result['failed'], 0)
        
        # Verify resolutions
        offline_storage1.refresh_from_db()
        offline_storage2.refresh_from_db()
        
        self.assertFalse(offline_storage1.has_conflicts)
        self.assertEqual(offline_storage1.sync_status, 'pending')
        
        self.assertFalse(offline_storage2.has_conflicts)
        self.assertEqual(offline_storage2.sync_status, 'failed')
    
    def test_cleanup_old_transactions(self):
        """Test cleaning up old synced transactions."""
        # Create old synced transaction
        old_date = timezone.now() - timedelta(days=35)
        POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=self._create_test_transaction_data(),
            is_synced=True,
            synced_at=old_date
        )
        
        # Create recent synced transaction
        POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=self._create_test_transaction_data(),
            is_synced=True,
            synced_at=timezone.now()
        )
        
        # Create unsynced transaction
        POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=self._create_test_transaction_data(),
            is_synced=False
        )
        
        cleaned_count = self.offline_pos.cleanup_old_transactions(days_old=30)
        
        self.assertEqual(cleaned_count, 1)
        self.assertEqual(POSOfflineStorage.objects.filter(device_id='TEST-DEVICE-001').count(), 2)
    
    def test_export_offline_data(self):
        """Test exporting offline data."""
        # Create offline transactions
        offline_storage = POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=self._create_test_transaction_data()
        )
        
        export_data = self.offline_pos.export_offline_data()
        
        self.assertEqual(export_data['device_id'], 'TEST-DEVICE-001')
        self.assertEqual(export_data['device_name'], 'Test POS Device')
        self.assertIsNotNone(export_data['export_timestamp'])
        self.assertEqual(len(export_data['transactions']), 1)
        
        transaction_export = export_data['transactions'][0]
        self.assertEqual(transaction_export['storage_id'], str(offline_storage.storage_id))
        self.assertEqual(transaction_export['sync_status'], 'pending')
        self.assertFalse(transaction_export['is_synced'])
        self.assertIsNotNone(transaction_export['transaction_data'])
    
    def _create_test_transaction_data(self):
        """Helper method to create test transaction data."""
        return {
            'transaction_id': 'test-transaction-123',
            'customer_id': self.customer.id,
            'transaction_date': timezone.now().isoformat(),
            'transaction_type': 'sale',
            'payment_method': 'cash',
            'subtotal': '2500000.00',
            'tax_amount': '0.00',
            'discount_amount': '0.00',
            'total_amount': '2500000.00',
            'amount_paid': '2500000.00',
            'gold_price_18k_at_transaction': '4500000.00',
            'line_items': [
                {
                    'jewelry_item_id': self.jewelry_item.id,
                    'item_name': 'Gold Ring 18K',
                    'item_sku': 'RING-001',
                    'quantity': '1',
                    'unit_price': '2500000.00',
                    'gold_weight_grams': '5.500',
                    'gold_karat': 18
                }
            ],
            'offline_created_at': timezone.now().isoformat()
        }


class POSOfflineServiceTest(TestCase):
    """Test POSOfflineService functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.customer = Customer.objects.create(
            first_name='احمد',
            last_name='محمدی',
            persian_first_name='احمد',
            persian_last_name='محمدی',
            phone_number='09123456789'
        )
    
    @patch('zargar.gold_installments.services.GoldPriceService.get_current_gold_price')
    def test_create_offline_transaction_data(self, mock_gold_price):
        """Test creating offline transaction data structure."""
        mock_gold_price.return_value = {
            'price_per_gram': Decimal('4500000.00')
        }
        
        line_items = [
            {
                'jewelry_item_id': 1,
                'item_name': 'Gold Ring',
                'unit_price': '2500000.00',
                'quantity': 1
            }
        ]
        
        transaction_data = POSOfflineService.create_offline_transaction_data(
            customer_id=self.customer.id,
            line_items=line_items,
            payment_method='cash',
            amount_paid=Decimal('2500000.00')
        )
        
        self.assertIsNotNone(transaction_data['transaction_id'])
        self.assertEqual(transaction_data['customer_id'], self.customer.id)
        self.assertEqual(transaction_data['payment_method'], 'cash')
        self.assertEqual(transaction_data['amount_paid'], '2500000.00')
        self.assertEqual(transaction_data['subtotal'], '2500000.00')
        self.assertEqual(transaction_data['total_amount'], '2500000.00')
        self.assertEqual(len(transaction_data['line_items']), 1)
        self.assertIsNotNone(transaction_data['offline_created_at'])
    
    def test_store_offline_transaction(self):
        """Test storing offline transaction."""
        transaction_data = {
            'transaction_id': 'test-123',
            'customer_id': self.customer.id,
            'total_amount': '2500000.00'
        }
        
        offline_storage = POSOfflineService.store_offline_transaction(
            transaction_data=transaction_data,
            device_id='TEST-DEVICE-001'
        )
        
        self.assertIsInstance(offline_storage, POSOfflineStorage)
        self.assertEqual(offline_storage.device_id, 'TEST-DEVICE-001')
        self.assertEqual(offline_storage.transaction_data, transaction_data)
        self.assertFalse(offline_storage.is_synced)
    
    def test_sync_offline_transactions(self):
        """Test syncing offline transactions."""
        # Create offline transactions
        transaction_data = {
            'transaction_id': 'test-123',
            'customer_id': self.customer.id,
            'transaction_type': 'sale',
            'payment_method': 'cash',
            'subtotal': '2500000.00',
            'total_amount': '2500000.00',
            'amount_paid': '2500000.00',
            'line_items': []
        }
        
        offline_storage1 = POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=transaction_data
        )
        
        offline_storage2 = POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-002',
            transaction_data=transaction_data
        )
        
        with patch.object(POSOfflineStorage, 'sync_to_database') as mock_sync:
            mock_sync.return_value = True
            
            # Sync specific device
            results = POSOfflineService.sync_offline_transactions(device_id='TEST-DEVICE-001')
        
        self.assertEqual(results['total_pending'], 1)
        self.assertEqual(results['synced_successfully'], 1)
        self.assertEqual(results['sync_failed'], 0)
    
    def test_get_offline_transaction_summary(self):
        """Test getting offline transaction summary."""
        transaction_data = {
            'total_amount': '2500000.00'
        }
        
        # Create transactions for different devices
        POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=transaction_data,
            is_synced=False
        )
        
        POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-001',
            transaction_data=transaction_data,
            is_synced=True
        )
        
        POSOfflineStorage.objects.create(
            device_id='TEST-DEVICE-002',
            transaction_data=transaction_data,
            is_synced=False
        )
        
        # Get summary for specific device
        summary = POSOfflineService.get_offline_transaction_summary(device_id='TEST-DEVICE-001')
        
        self.assertEqual(summary['total_transactions'], 2)
        self.assertEqual(summary['pending_sync'], 1)
        self.assertEqual(summary['synced'], 1)
        self.assertEqual(summary['total_pending_value'], Decimal('2500000.00'))


@pytest.mark.django_db
class TestOfflinePOSIntegration:
    """Integration tests for offline POS system."""
    
    def test_complete_offline_workflow(self):
        """Test complete offline workflow from creation to sync."""
        # Create test data
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        customer = Customer.objects.create(
            first_name='احمد',
            last_name='محمدی',
            persian_first_name='احمد',
            persian_last_name='محمدی',
            phone_number='09123456789'
        )
        
        category = Category.objects.create(
            name='Rings',
            name_persian='انگشتر'
        )
        
        jewelry_item = JewelryItem.objects.create(
            name='Gold Ring 18K',
            category=category,
            sku='RING-001',
            weight_grams=Decimal('5.500'),
            karat=18,
            selling_price=Decimal('2500000.00'),
            quantity=10,
            status='in_stock'
        )
        
        # Initialize offline POS system
        offline_pos = OfflinePOSSystem(
            device_id='TEST-DEVICE-001',
            device_name='Test POS Device'
        )
        
        # Create offline transaction
        line_items = [
            {
                'jewelry_item_id': jewelry_item.id,
                'item_name': jewelry_item.name,
                'item_sku': jewelry_item.sku,
                'quantity': 1,
                'unit_price': str(jewelry_item.selling_price),
                'gold_weight_grams': str(jewelry_item.weight_grams),
                'gold_karat': jewelry_item.karat
            }
        ]
        
        with patch('zargar.gold_installments.services.GoldPriceService.get_current_gold_price') as mock_gold_price:
            mock_gold_price.return_value = {
                'price_per_gram': Decimal('4500000.00')
            }
            
            offline_storage = offline_pos.create_offline_transaction(
                customer_id=customer.id,
                line_items=line_items,
                payment_method='cash',
                amount_paid=Decimal('2500000.00')
            )
        
        # Verify offline storage
        assert offline_storage.device_id == 'TEST-DEVICE-001'
        assert not offline_storage.is_synced
        assert offline_storage.sync_status == 'pending'
        
        # Sync offline transactions
        with patch.object(offline_pos, '_check_connection', return_value=True):
            sync_results = offline_pos.sync_offline_transactions()
        
        # Verify sync results
        assert sync_results['success']
        assert sync_results['synced_successfully'] == 1
        assert sync_results['sync_failed'] == 0
        
        # Verify transaction was created
        offline_storage.refresh_from_db()
        assert offline_storage.is_synced
        assert offline_storage.sync_status == 'synced'
        assert offline_storage.synced_transaction_id is not None
        
        # Verify actual transaction exists
        transaction = POSTransaction.objects.get(
            transaction_id=offline_storage.synced_transaction_id
        )
        assert transaction.customer == customer
        assert transaction.total_amount == Decimal('2500000.00')
        assert transaction.is_offline_transaction
        
        # Verify line item exists
        line_items_db = transaction.line_items.all()
        assert len(line_items_db) == 1
        assert line_items_db[0].jewelry_item == jewelry_item
        assert line_items_db[0].quantity == 1