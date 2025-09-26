"""
Comprehensive tests for POS backend functionality.
Tests transaction processing, gold price calculations, and offline synchronization.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing models
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

from zargar.pos.models import (
    POSTransaction, POSTransactionLineItem, POSInvoice, POSOfflineStorage
)
from zargar.pos.services import (
    POSTransactionService, POSOfflineService, POSInvoiceService, POSReportingService
)
from zargar.jewelry.models import JewelryItem, Category
from zargar.customers.models import Customer
from zargar.gold_installments.services import GoldPriceService

User = get_user_model()


class POSTransactionModelTest(TestCase):
    """Test POS transaction model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role='salesperson'
        )
        
        self.customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            persian_first_name='جان',
            persian_last_name='دو',
            phone_number='09123456789',
            email='john@example.com'
        )
        
        self.category = Category.objects.create(
            name='Rings',
            name_persian='انگشتر'
        )
        
        self.jewelry_item = JewelryItem.objects.create(
            name='Gold Ring',
            sku='GR001',
            category=self.category,
            weight_grams=Decimal('5.500'),
            karat=18,
            manufacturing_cost=Decimal('500000'),
            selling_price=Decimal('2000000'),
            quantity=10
        )
    
    def test_transaction_creation(self):
        """Test POS transaction creation."""
        transaction = POSTransaction.objects.create(
            customer=self.customer,
            transaction_type='sale',
            payment_method='cash',
            gold_price_18k_at_transaction=Decimal('3500000'),
            created_by=self.user
        )
        
        self.assertIsNotNone(transaction.transaction_number)
        self.assertIsNotNone(transaction.transaction_date_shamsi)
        self.assertEqual(transaction.status, 'pending')
        self.assertEqual(transaction.subtotal, Decimal('0.00'))
        self.assertEqual(transaction.total_amount, Decimal('0.00'))
    
    def test_transaction_number_generation(self):
        """Test unique transaction number generation."""
        transaction1 = POSTransaction.objects.create(
            customer=self.customer,
            created_by=self.user
        )
        transaction2 = POSTransaction.objects.create(
            customer=self.customer,
            created_by=self.user
        )
        
        self.assertNotEqual(transaction1.transaction_number, transaction2.transaction_number)
        self.assertTrue(transaction1.transaction_number.startswith('POS-'))
        self.assertTrue(transaction2.transaction_number.startswith('POS-'))
    
    def test_add_line_item(self):
        """Test adding line items to transaction."""
        transaction = POSTransaction.objects.create(
            customer=self.customer,
            gold_price_18k_at_transaction=Decimal('3500000'),
            created_by=self.user
        )
        
        line_item = transaction.add_line_item(
            jewelry_item=self.jewelry_item,
            quantity=2,
            gold_price_per_gram=Decimal('3500000')
        )
        
        self.assertEqual(line_item.quantity, 2)
        self.assertEqual(line_item.item_name, 'Gold Ring')
        self.assertEqual(line_item.item_sku, 'GR001')
        self.assertEqual(line_item.gold_weight_grams, Decimal('11.000'))  # 5.5 * 2
        
        # Check transaction totals updated
        transaction.refresh_from_db()
        self.assertGreater(transaction.subtotal, Decimal('0.00'))
        self.assertEqual(transaction.total_gold_weight_grams, Decimal('11.000'))
    
    def test_complete_transaction(self):
        """Test completing a transaction."""
        transaction = POSTransaction.objects.create(
            customer=self.customer,
            gold_price_18k_at_transaction=Decimal('3500000'),
            created_by=self.user
        )
        
        # Add line item
        transaction.add_line_item(
            jewelry_item=self.jewelry_item,
            quantity=1,
            gold_price_per_gram=Decimal('3500000')
        )
        
        # Complete transaction
        transaction.amount_paid = transaction.total_amount + Decimal('100000')  # Extra for change
        transaction.complete_transaction()
        
        self.assertEqual(transaction.status, 'completed')
        self.assertGreater(transaction.change_amount, Decimal('0.00'))
        
        # Check inventory updated
        self.jewelry_item.refresh_from_db()
        self.assertEqual(self.jewelry_item.quantity, 9)  # Reduced by 1
        
        # Check customer stats updated
        self.customer.refresh_from_db()
        self.assertGreater(self.customer.total_purchases, Decimal('0.00'))
        self.assertGreater(self.customer.loyalty_points, 0)
    
    def test_cancel_transaction(self):
        """Test cancelling a transaction."""
        transaction = POSTransaction.objects.create(
            customer=self.customer,
            created_by=self.user
        )
        
        transaction.cancel_transaction('Customer changed mind')
        
        self.assertEqual(transaction.status, 'cancelled')
        self.assertIn('Customer changed mind', transaction.internal_notes)
    
    def test_offline_transaction_backup(self):
        """Test creating offline transaction backup."""
        transaction = POSTransaction.objects.create(
            customer=self.customer,
            subtotal=Decimal('1000000'),
            total_amount=Decimal('1000000'),
            created_by=self.user
        )
        
        # Add line item
        POSTransactionLineItem.objects.create(
            transaction=transaction,
            item_name='Test Item',
            quantity=1,
            unit_price=Decimal('1000000')
        )
        
        offline_data = transaction.create_offline_backup()
        
        self.assertTrue(transaction.is_offline_transaction)
        self.assertEqual(transaction.sync_status, 'pending_sync')
        self.assertIn('transaction_id', offline_data)
        self.assertIn('line_items', offline_data)
        self.assertEqual(len(offline_data['line_items']), 1)


class POSTransactionLineItemModelTest(TestCase):
    """Test POS transaction line item model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.transaction = POSTransaction.objects.create(
            created_by=self.user
        )
    
    def test_line_item_creation(self):
        """Test line item creation and total calculation."""
        line_item = POSTransactionLineItem.objects.create(
            transaction=self.transaction,
            item_name='Test Item',
            quantity=3,
            unit_price=Decimal('100000')
        )
        
        self.assertEqual(line_item.line_total, Decimal('300000'))  # 3 * 100000
    
    def test_apply_discount(self):
        """Test applying discount to line item."""
        line_item = POSTransactionLineItem.objects.create(
            transaction=self.transaction,
            item_name='Test Item',
            quantity=1,
            unit_price=Decimal('100000')
        )
        
        # Apply 10% discount
        line_item.apply_discount(discount_percentage=Decimal('10.00'))
        
        self.assertEqual(line_item.discount_percentage, Decimal('10.00'))
        self.assertEqual(line_item.discount_amount, Decimal('10000'))
        self.assertEqual(line_item.line_total, Decimal('90000'))  # 100000 - 10000
    
    def test_format_for_display(self):
        """Test Persian formatting for display."""
        line_item = POSTransactionLineItem.objects.create(
            transaction=self.transaction,
            item_name='Test Item',
            item_sku='TEST001',
            quantity=2,
            unit_price=Decimal('150000'),
            gold_weight_grams=Decimal('3.500')
        )
        
        display_data = line_item.format_for_display()
        
        self.assertIn('item_name', display_data)
        self.assertIn('quantity_display', display_data)
        self.assertIn('unit_price_display', display_data)
        self.assertIn('gold_weight_display', display_data)


class POSInvoiceModelTest(TestCase):
    """Test POS invoice model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.customer = Customer.objects.create(
            first_name='Jane',
            last_name='Smith',
            persian_first_name='جین',
            persian_last_name='اسمیت',
            phone_number='09123456789'
        )
        
        self.transaction = POSTransaction.objects.create(
            customer=self.customer,
            subtotal=Decimal('1500000'),
            total_amount=Decimal('1500000'),
            status='completed',
            created_by=self.user
        )
    
    def test_invoice_creation(self):
        """Test invoice creation."""
        invoice = POSInvoice.objects.create(
            transaction=self.transaction
        )
        
        self.assertIsNotNone(invoice.invoice_number)
        self.assertIsNotNone(invoice.issue_date_shamsi)
        self.assertEqual(invoice.invoice_total_amount, self.transaction.total_amount)
        self.assertEqual(invoice.status, 'draft')
    
    def test_invoice_number_generation(self):
        """Test unique invoice number generation."""
        invoice1 = POSInvoice.objects.create(transaction=self.transaction)
        
        # Create another transaction for second invoice
        transaction2 = POSTransaction.objects.create(
            customer=self.customer,
            subtotal=Decimal('2000000'),
            total_amount=Decimal('2000000'),
            status='completed',
            created_by=self.user
        )
        invoice2 = POSInvoice.objects.create(transaction=transaction2)
        
        self.assertNotEqual(invoice1.invoice_number, invoice2.invoice_number)
        self.assertTrue(invoice1.invoice_number.startswith('INV-'))
        self.assertTrue(invoice2.invoice_number.startswith('INV-'))
    
    def test_generate_persian_invoice_data(self):
        """Test generating Persian invoice data."""
        invoice = POSInvoice.objects.create(
            transaction=self.transaction,
            invoice_notes='Test invoice notes'
        )
        
        invoice_data = invoice.generate_persian_invoice_data()
        
        self.assertIn('business_info', invoice_data)
        self.assertIn('customer_info', invoice_data)
        self.assertIn('invoice_details', invoice_data)
        self.assertIn('financial_totals', invoice_data)
        
        # Check customer info
        self.assertEqual(invoice_data['customer_info']['name'], 'جین اسمیت')
        
        # Check invoice details
        self.assertEqual(invoice_data['invoice_details']['invoice_number'], invoice.invoice_number)


class POSTransactionServiceTest(TestCase):
    """Test POS transaction service functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role='salesperson'
        )
        
        self.customer = Customer.objects.create(
            first_name='Alice',
            last_name='Johnson',
            phone_number='09123456789'
        )
        
        self.category = Category.objects.create(
            name='Necklaces',
            name_persian='گردنبند'
        )
        
        self.jewelry_item = JewelryItem.objects.create(
            name='Gold Necklace',
            sku='GN001',
            category=self.category,
            weight_grams=Decimal('8.750'),
            karat=18,
            manufacturing_cost=Decimal('800000'),
            selling_price=Decimal('3500000'),
            quantity=5
        )
    
    @patch.object(GoldPriceService, 'get_current_gold_price')
    def test_create_transaction(self, mock_gold_price):
        """Test creating transaction via service."""
        mock_gold_price.return_value = {
            'price_per_gram': Decimal('3500000'),
            'karat': 18,
            'source': 'test'
        }
        
        transaction = POSTransactionService.create_transaction(
            customer_id=self.customer.id,
            transaction_type='sale',
            payment_method='card',
            user=self.user
        )
        
        self.assertEqual(transaction.customer, self.customer)
        self.assertEqual(transaction.transaction_type, 'sale')
        self.assertEqual(transaction.payment_method, 'card')
        self.assertEqual(transaction.gold_price_18k_at_transaction, Decimal('3500000'))
        self.assertEqual(transaction.created_by, self.user)
    
    def test_add_jewelry_item_to_transaction(self):
        """Test adding jewelry item via service."""
        transaction = POSTransaction.objects.create(
            customer=self.customer,
            gold_price_18k_at_transaction=Decimal('3500000'),
            created_by=self.user
        )
        
        line_item = POSTransactionService.add_jewelry_item_to_transaction(
            transaction=transaction,
            jewelry_item_id=self.jewelry_item.id,
            quantity=2,
            discount_percentage=Decimal('5.00')
        )
        
        self.assertEqual(line_item.jewelry_item, self.jewelry_item)
        self.assertEqual(line_item.quantity, 2)
        self.assertEqual(line_item.gold_weight_grams, Decimal('17.500'))  # 8.75 * 2
        self.assertEqual(line_item.discount_percentage, Decimal('5.00'))
        
        # Check transaction totals updated
        transaction.refresh_from_db()
        self.assertGreater(transaction.subtotal, Decimal('0.00'))
    
    def test_add_jewelry_item_insufficient_inventory(self):
        """Test adding jewelry item with insufficient inventory."""
        transaction = POSTransaction.objects.create(
            customer=self.customer,
            created_by=self.user
        )
        
        with self.assertRaises(ValidationError) as context:
            POSTransactionService.add_jewelry_item_to_transaction(
                transaction=transaction,
                jewelry_item_id=self.jewelry_item.id,
                quantity=10  # More than available (5)
            )
        
        self.assertIn('Insufficient inventory', str(context.exception))
    
    def test_add_custom_item_to_transaction(self):
        """Test adding custom item via service."""
        transaction = POSTransaction.objects.create(
            customer=self.customer,
            created_by=self.user
        )
        
        line_item = POSTransactionService.add_custom_item_to_transaction(
            transaction=transaction,
            item_name='Custom Repair Service',
            unit_price=Decimal('500000'),
            quantity=1,
            item_sku='REPAIR001'
        )
        
        self.assertEqual(line_item.item_name, 'Custom Repair Service')
        self.assertEqual(line_item.item_sku, 'REPAIR001')
        self.assertEqual(line_item.unit_price, Decimal('500000'))
        self.assertEqual(line_item.quantity, 1)
        
        # Check transaction totals updated
        transaction.refresh_from_db()
        self.assertEqual(transaction.subtotal, Decimal('500000'))
    
    def test_process_payment(self):
        """Test processing payment via service."""
        transaction = POSTransaction.objects.create(
            customer=self.customer,
            subtotal=Decimal('2000000'),
            total_amount=Decimal('2000000'),
            created_by=self.user
        )
        
        # Add line item
        POSTransactionLineItem.objects.create(
            transaction=transaction,
            item_name='Test Item',
            quantity=1,
            unit_price=Decimal('2000000')
        )
        
        result = POSTransactionService.process_payment(
            transaction=transaction,
            amount_paid=Decimal('2100000'),  # Extra for change
            payment_method='cash',
            reference_number='REF123'
        )
        
        self.assertTrue(result['success'])
        self.assertTrue(result['payment_successful'])
        self.assertEqual(result['change_amount'], Decimal('100000'))
        
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, 'completed')
        self.assertEqual(transaction.amount_paid, Decimal('2100000'))
        self.assertEqual(transaction.reference_number, 'REF123')
    
    def test_process_payment_insufficient_amount(self):
        """Test processing payment with insufficient amount."""
        transaction = POSTransaction.objects.create(
            customer=self.customer,
            subtotal=Decimal('2000000'),
            total_amount=Decimal('2000000'),
            created_by=self.user
        )
        
        with self.assertRaises(ValidationError) as context:
            POSTransactionService.process_payment(
                transaction=transaction,
                amount_paid=Decimal('1500000')  # Less than required
            )
        
        self.assertIn('Insufficient payment', str(context.exception))
    
    def test_cancel_transaction(self):
        """Test cancelling transaction via service."""
        transaction = POSTransaction.objects.create(
            customer=self.customer,
            created_by=self.user
        )
        
        result = POSTransactionService.cancel_transaction(
            transaction=transaction,
            reason='Customer request'
        )
        
        self.assertTrue(result['success'])
        self.assertTrue(result['cancelled'])
        
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, 'cancelled')
        self.assertIn('Customer request', transaction.internal_notes)


class POSOfflineServiceTest(TestCase):
    """Test POS offline service functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.customer = Customer.objects.create(
            first_name='Bob',
            last_name='Wilson',
            phone_number='09123456789'
        )
    
    @patch.object(GoldPriceService, 'get_current_gold_price')
    def test_create_offline_transaction_data(self, mock_gold_price):
        """Test creating offline transaction data."""
        mock_gold_price.return_value = {
            'price_per_gram': Decimal('3500000'),
            'karat': 18,
            'source': 'test'
        }
        
        line_items = [
            {
                'jewelry_item_id': None,
                'item_name': 'Custom Item',
                'item_sku': 'CUSTOM001',
                'quantity': '1',
                'unit_price': '1000000',
                'gold_weight_grams': '0.000',
                'gold_karat': 0
            }
        ]
        
        offline_data = POSOfflineService.create_offline_transaction_data(
            customer_id=self.customer.id,
            line_items=line_items,
            payment_method='cash',
            amount_paid=Decimal('1000000'),
            transaction_type='sale'
        )
        
        self.assertIn('transaction_id', offline_data)
        self.assertEqual(offline_data['customer_id'], self.customer.id)
        self.assertEqual(offline_data['payment_method'], 'cash')
        self.assertEqual(offline_data['subtotal'], '1000000')
        self.assertEqual(len(offline_data['line_items']), 1)
    
    def test_store_offline_transaction(self):
        """Test storing offline transaction."""
        transaction_data = {
            'transaction_id': 'test-uuid',
            'customer_id': self.customer.id,
            'transaction_date': timezone.now().isoformat(),
            'total_amount': '1500000',
            'line_items': []
        }
        
        offline_storage = POSOfflineService.store_offline_transaction(
            transaction_data=transaction_data,
            device_id='tablet-001'
        )
        
        self.assertFalse(offline_storage.is_synced)
        self.assertEqual(offline_storage.device_id, 'tablet-001')
        self.assertEqual(offline_storage.transaction_data, transaction_data)
    
    def test_get_offline_transaction_summary(self):
        """Test getting offline transaction summary."""
        # Create some offline transactions
        POSOfflineStorage.objects.create(
            transaction_data={'total_amount': '1000000'},
            device_id='tablet-001',
            is_synced=False
        )
        POSOfflineStorage.objects.create(
            transaction_data={'total_amount': '2000000'},
            device_id='tablet-001',
            is_synced=True
        )
        
        summary = POSOfflineService.get_offline_transaction_summary(device_id='tablet-001')
        
        self.assertEqual(summary['total_transactions'], 2)
        self.assertEqual(summary['pending_sync'], 1)
        self.assertEqual(summary['synced'], 1)
        self.assertEqual(summary['total_pending_value'], Decimal('1000000'))


class POSReportingServiceTest(TestCase):
    """Test POS reporting service functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.customer = Customer.objects.create(
            first_name='Charlie',
            last_name='Brown',
            phone_number='09123456789'
        )
        
        # Create completed transactions for testing
        self.transaction1 = POSTransaction.objects.create(
            customer=self.customer,
            transaction_type='sale',
            payment_method='cash',
            subtotal=Decimal('1000000'),
            total_amount=Decimal('1000000'),
            status='completed',
            total_gold_weight_grams=Decimal('5.000'),
            created_by=self.user
        )
        
        self.transaction2 = POSTransaction.objects.create(
            customer=self.customer,
            transaction_type='sale',
            payment_method='card',
            subtotal=Decimal('2000000'),
            total_amount=Decimal('2000000'),
            status='completed',
            total_gold_weight_grams=Decimal('8.500'),
            created_by=self.user
        )
        
        # Add line items
        POSTransactionLineItem.objects.create(
            transaction=self.transaction1,
            item_name='Ring A',
            item_sku='RING-A',
            quantity=1,
            unit_price=Decimal('1000000'),
            line_total=Decimal('1000000')
        )
        
        POSTransactionLineItem.objects.create(
            transaction=self.transaction2,
            item_name='Necklace B',
            item_sku='NECK-B',
            quantity=1,
            unit_price=Decimal('2000000'),
            line_total=Decimal('2000000')
        )
    
    def test_get_daily_sales_summary(self):
        """Test getting daily sales summary."""
        today = timezone.now().date()
        
        summary = POSReportingService.get_daily_sales_summary(date=today)
        
        self.assertEqual(summary['date'], today)
        self.assertEqual(summary['total_transactions'], 2)
        self.assertEqual(summary['total_sales'], Decimal('3000000'))
        self.assertEqual(summary['total_gold_weight'], Decimal('13.500'))
        self.assertEqual(summary['average_transaction_value'], Decimal('1500000'))
        
        # Check payment method breakdown
        self.assertIn('cash', summary['payment_methods'])
        self.assertIn('card', summary['payment_methods'])
        self.assertEqual(summary['payment_methods']['cash']['count'], 1)
        self.assertEqual(summary['payment_methods']['card']['count'], 1)
        
        # Check top selling items
        self.assertEqual(len(summary['top_selling_items']), 2)
        top_item = summary['top_selling_items'][0]
        self.assertEqual(top_item['name'], 'Necklace B')  # Higher revenue
        self.assertEqual(top_item['revenue'], Decimal('2000000'))
    
    def test_get_monthly_sales_trend(self):
        """Test getting monthly sales trend."""
        now = timezone.now()
        year = now.year
        month = now.month
        
        trend = POSReportingService.get_monthly_sales_trend(year, month)
        
        self.assertEqual(trend['year'], year)
        self.assertEqual(trend['month'], month)
        self.assertEqual(trend['total_transactions'], 2)
        self.assertEqual(trend['total_sales'], Decimal('3000000'))
        self.assertEqual(trend['total_gold_weight'], Decimal('13.500'))
        
        # Check daily data structure
        self.assertIn('daily_data', trend)
        self.assertIsInstance(trend['daily_data'], list)
        
        # Find today's data
        today_data = None
        for day_data in trend['daily_data']:
            if day_data['date'] == now.date():
                today_data = day_data
                break
        
        self.assertIsNotNone(today_data)
        self.assertEqual(today_data['transactions'], 2)
        self.assertEqual(today_data['sales'], Decimal('3000000'))


@pytest.mark.django_db
class TestPOSIntegration:
    """Integration tests for POS system with real database operations."""
    
    def test_complete_pos_workflow(self):
        """Test complete POS workflow from creation to completion."""
        # Create user and customer
        user = User.objects.create_user(
            username='posuser',
            password='testpass123',
            role='salesperson'
        )
        
        customer = Customer.objects.create(
            first_name='Integration',
            last_name='Test',
            phone_number='09123456789',
            email='integration@test.com'
        )
        
        # Create jewelry item
        category = Category.objects.create(
            name='Test Category',
            name_persian='دسته تست'
        )
        
        jewelry_item = JewelryItem.objects.create(
            name='Test Ring',
            sku='TEST-RING-001',
            category=category,
            weight_grams=Decimal('4.250'),
            karat=18,
            manufacturing_cost=Decimal('400000'),
            selling_price=Decimal('1800000'),
            quantity=3
        )
        
        # Step 1: Create transaction
        with patch.object(GoldPriceService, 'get_current_gold_price') as mock_gold_price:
            mock_gold_price.return_value = {
                'price_per_gram': Decimal('3500000'),
                'karat': 18,
                'source': 'test'
            }
            
            transaction = POSTransactionService.create_transaction(
                customer_id=customer.id,
                transaction_type='sale',
                payment_method='cash',
                user=user
            )
        
        assert transaction.customer == customer
        assert transaction.status == 'pending'
        
        # Step 2: Add jewelry item
        line_item = POSTransactionService.add_jewelry_item_to_transaction(
            transaction=transaction,
            jewelry_item_id=jewelry_item.id,
            quantity=2,
            discount_percentage=Decimal('10.00')
        )
        
        assert line_item.quantity == 2
        assert line_item.discount_percentage == Decimal('10.00')
        
        # Step 3: Add custom item
        custom_line_item = POSTransactionService.add_custom_item_to_transaction(
            transaction=transaction,
            item_name='Gift Wrapping',
            unit_price=Decimal('50000'),
            quantity=1
        )
        
        assert custom_line_item.item_name == 'Gift Wrapping'
        
        # Step 4: Apply transaction discount
        POSTransactionService.apply_transaction_discount(
            transaction=transaction,
            discount_amount=Decimal('100000')
        )
        
        transaction.refresh_from_db()
        assert transaction.discount_amount == Decimal('100000')
        
        # Step 5: Calculate tax
        tax_amount = POSTransactionService.calculate_tax(
            transaction=transaction,
            tax_rate=Decimal('9.00')
        )
        
        assert tax_amount > Decimal('0.00')
        
        # Step 6: Process payment
        result = POSTransactionService.process_payment(
            transaction=transaction,
            amount_paid=transaction.total_amount + Decimal('50000'),  # Extra for change
            payment_method='cash'
        )
        
        assert result['success'] is True
        assert result['payment_successful'] is True
        assert result['change_amount'] == Decimal('50000')
        
        # Verify transaction completion
        transaction.refresh_from_db()
        assert transaction.status == 'completed'
        
        # Verify inventory update
        jewelry_item.refresh_from_db()
        assert jewelry_item.quantity == 1  # Reduced from 3 to 1
        
        # Verify customer stats update
        customer.refresh_from_db()
        assert customer.total_purchases > Decimal('0.00')
        assert customer.loyalty_points > 0
        
        # Verify invoice creation
        assert hasattr(transaction, 'invoice')
        invoice = transaction.invoice
        assert invoice.status == 'issued'
        assert invoice.invoice_total_amount == transaction.total_amount
    
    def test_offline_transaction_sync(self):
        """Test offline transaction synchronization."""
        # Create user and customer
        user = User.objects.create_user(
            username='offlineuser',
            password='testpass123'
        )
        
        customer = Customer.objects.create(
            first_name='Offline',
            last_name='Customer',
            phone_number='09123456789'
        )
        
        # Create offline transaction data
        with patch.object(GoldPriceService, 'get_current_gold_price') as mock_gold_price:
            mock_gold_price.return_value = {
                'price_per_gram': Decimal('3500000'),
                'karat': 18,
                'source': 'test'
            }
            
            line_items = [
                {
                    'jewelry_item_id': None,
                    'item_name': 'Offline Item',
                    'item_sku': 'OFF001',
                    'quantity': '1',
                    'unit_price': '1200000',
                    'gold_weight_grams': '0.000',
                    'gold_karat': 0
                }
            ]
            
            offline_data = POSOfflineService.create_offline_transaction_data(
                customer_id=customer.id,
                line_items=line_items,
                payment_method='cash',
                amount_paid=Decimal('1200000'),
                transaction_type='sale'
            )
        
        # Store offline transaction
        offline_storage = POSOfflineService.store_offline_transaction(
            transaction_data=offline_data,
            device_id='tablet-sync-test'
        )
        
        assert offline_storage.is_synced is False
        
        # Sync offline transactions
        sync_results = POSOfflineService.sync_offline_transactions(
            device_id='tablet-sync-test'
        )
        
        assert sync_results['total_pending'] == 1
        assert sync_results['synced_successfully'] == 1
        assert sync_results['sync_failed'] == 0
        
        # Verify offline storage is marked as synced
        offline_storage.refresh_from_db()
        assert offline_storage.is_synced is True
        assert offline_storage.synced_transaction is not None
        
        # Verify synced transaction
        synced_transaction = offline_storage.synced_transaction
        assert synced_transaction.customer == customer
        assert synced_transaction.status == 'completed'
        assert synced_transaction.is_offline_transaction is True
        assert synced_transaction.sync_status == 'synced'