"""
Tests for POS invoice generation backend functionality.
Tests invoice generation with automatic gold price calculation and Persian formatting.
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
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from zargar.pos.models import POSTransaction, POSTransactionLineItem, POSInvoice
from zargar.pos.services import POSInvoiceService, POSTransactionService
from zargar.customers.models import Customer
from zargar.jewelry.models import JewelryItem, Category
from zargar.core.models import User


@pytest.mark.django_db
class TestPOSInvoiceGeneration(TestCase):
    """Test POS invoice generation with gold price calculations."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            first_name='احمد',
            last_name='محمدی',
            persian_first_name='احمد',
            persian_last_name='محمدی',
            phone_number='09123456789',
            email='ahmad@example.com',
            address='تهران، خیابان ولیعصر'
        )
        
        # Create jewelry category
        self.category = Category.objects.create(
            name='Ring',
            name_persian='انگشتر',
            description='Gold rings'
        )
        
        # Create jewelry item
        self.jewelry_item = JewelryItem.objects.create(
            name='Gold Ring 18K',
            name_persian='انگشتر طلای ۱۸ عیار',
            category=self.category,
            sku='RING-001',
            weight_grams=Decimal('5.500'),
            karat=18,
            manufacturing_cost=Decimal('500000'),
            selling_price=Decimal('2500000'),
            quantity=10,
            status='in_stock'
        )
        
        # Create completed transaction
        self.transaction = POSTransactionService.create_transaction(
            customer_id=self.customer.id,
            transaction_type='sale',
            payment_method='cash',
            user=self.user
        )
        
        # Add jewelry item to transaction
        self.line_item = POSTransactionService.add_jewelry_item_to_transaction(
            transaction=self.transaction,
            jewelry_item_id=self.jewelry_item.id,
            quantity=1
        )
        
        # Complete the transaction
        POSTransactionService.process_payment(
            transaction=self.transaction,
            amount_paid=Decimal('2500000'),
            payment_method='cash'
        )
    
    def test_generate_invoice_for_completed_transaction(self):
        """Test generating invoice for completed transaction."""
        invoice = POSInvoiceService.generate_invoice_for_transaction(
            transaction=self.transaction,
            invoice_type='sale',
            auto_issue=True
        )
        
        # Verify invoice creation
        self.assertIsInstance(invoice, POSInvoice)
        self.assertEqual(invoice.transaction, self.transaction)
        self.assertEqual(invoice.invoice_type, 'sale')
        self.assertEqual(invoice.status, 'issued')
        self.assertTrue(invoice.invoice_number.startswith('INV-'))
        
        # Verify financial amounts match transaction
        self.assertEqual(invoice.invoice_subtotal, self.transaction.subtotal)
        self.assertEqual(invoice.invoice_total_amount, self.transaction.total_amount)
        
        # Verify Shamsi date is set
        self.assertIsNotNone(invoice.issue_date_shamsi)
        self.assertTrue(len(invoice.issue_date_shamsi) == 10)  # Format: YYYY/MM/DD
    
    def test_generate_invoice_for_incomplete_transaction(self):
        """Test that invoice generation fails for incomplete transaction."""
        # Create incomplete transaction
        incomplete_transaction = POSTransactionService.create_transaction(
            customer_id=self.customer.id,
            transaction_type='sale',
            payment_method='cash',
            user=self.user
        )
        
        with self.assertRaises(ValidationError) as context:
            POSInvoiceService.generate_invoice_for_transaction(
                transaction=incomplete_transaction
            )
        
        self.assertIn("incomplete transaction", str(context.exception))
    
    def test_generate_persian_invoice_data(self):
        """Test generating Persian invoice data with proper formatting."""
        invoice = POSInvoiceService.generate_invoice_for_transaction(
            transaction=self.transaction
        )
        
        invoice_data = invoice.generate_persian_invoice_data()
        
        # Verify structure
        self.assertIn('business_info', invoice_data)
        self.assertIn('customer_info', invoice_data)
        self.assertIn('invoice_details', invoice_data)
        self.assertIn('line_items', invoice_data)
        self.assertIn('financial_totals', invoice_data)
        
        # Verify customer information
        customer_info = invoice_data['customer_info']
        self.assertEqual(customer_info['name'], 'احمد محمدی')
        self.assertEqual(customer_info['phone'], '09123456789')
        
        # Verify line items
        line_items = invoice_data['line_items']
        self.assertEqual(len(line_items), 1)
        
        line_item = line_items[0]
        self.assertEqual(line_item['name'], 'Gold Ring 18K')
        self.assertEqual(line_item['sku'], 'RING-001')
        self.assertIn('۱', line_item['quantity'])  # Persian numeral for 1
        
        # Verify financial totals include Persian formatting
        financial_totals = invoice_data['financial_totals']
        self.assertIn('total_in_words', financial_totals)
        self.assertTrue(len(financial_totals['total_in_words']) > 0)
    
    def test_generate_invoice_pdf(self):
        """Test PDF generation for invoice."""
        invoice = POSInvoiceService.generate_invoice_for_transaction(
            transaction=self.transaction
        )
        
        pdf_content = POSInvoiceService.generate_invoice_pdf(invoice)
        
        # Verify PDF content is generated
        self.assertIsInstance(pdf_content, bytes)
        self.assertTrue(len(pdf_content) > 0)
    
    def test_invoice_with_multiple_items(self):
        """Test invoice generation with multiple jewelry items."""
        # Add another jewelry item
        jewelry_item2 = JewelryItem.objects.create(
            name='Gold Necklace 18K',
            name_persian='گردنبند طلای ۱۸ عیار',
            category=self.category,
            sku='NECK-001',
            weight_grams=Decimal('12.750'),
            karat=18,
            manufacturing_cost=Decimal('800000'),
            selling_price=Decimal('4500000'),
            quantity=5,
            status='in_stock'
        )
        
        # Create new transaction with multiple items
        transaction = POSTransactionService.create_transaction(
            customer_id=self.customer.id,
            transaction_type='sale',
            payment_method='card',
            user=self.user
        )
        
        # Add both items
        POSTransactionService.add_jewelry_item_to_transaction(
            transaction=transaction,
            jewelry_item_id=self.jewelry_item.id,
            quantity=2
        )
        
        POSTransactionService.add_jewelry_item_to_transaction(
            transaction=transaction,
            jewelry_item_id=jewelry_item2.id,
            quantity=1
        )
        
        # Complete transaction
        total_amount = transaction.total_amount
        POSTransactionService.process_payment(
            transaction=transaction,
            amount_paid=total_amount,
            payment_method='card'
        )
        
        # Generate invoice
        invoice = POSInvoiceService.generate_invoice_for_transaction(transaction)
        invoice_data = invoice.generate_persian_invoice_data()
        
        # Verify multiple line items
        line_items = invoice_data['line_items']
        self.assertEqual(len(line_items), 2)
        
        # Verify total calculations
        self.assertEqual(invoice.invoice_total_amount, total_amount)
    
    def test_invoice_with_custom_item(self):
        """Test invoice generation with custom (non-jewelry) items."""
        # Create transaction with custom item
        transaction = POSTransactionService.create_transaction(
            customer_id=self.customer.id,
            transaction_type='sale',
            payment_method='cash',
            user=self.user
        )
        
        # Add custom item
        POSTransactionService.add_custom_item_to_transaction(
            transaction=transaction,
            item_name='خدمات تعمیر',
            unit_price=Decimal('300000'),
            quantity=1,
            item_sku='SERVICE-001'
        )
        
        # Complete transaction
        POSTransactionService.process_payment(
            transaction=transaction,
            amount_paid=Decimal('300000'),
            payment_method='cash'
        )
        
        # Generate invoice
        invoice = POSInvoiceService.generate_invoice_for_transaction(transaction)
        invoice_data = invoice.generate_persian_invoice_data()
        
        # Verify custom item in invoice
        line_items = invoice_data['line_items']
        self.assertEqual(len(line_items), 1)
        
        line_item = line_items[0]
        self.assertEqual(line_item['name'], 'خدمات تعمیر')
        self.assertEqual(line_item['sku'], 'SERVICE-001')
    
    def test_invoice_with_discount(self):
        """Test invoice generation with transaction discount."""
        # Apply discount to transaction
        POSTransactionService.apply_transaction_discount(
            transaction=self.transaction,
            discount_amount=Decimal('100000')
        )
        
        # Generate invoice
        invoice = POSInvoiceService.generate_invoice_for_transaction(
            transaction=self.transaction
        )
        
        # Verify discount is reflected in invoice
        self.assertEqual(invoice.invoice_discount_amount, Decimal('100000'))
        self.assertEqual(
            invoice.invoice_total_amount,
            invoice.invoice_subtotal - invoice.invoice_discount_amount
        )
        
        # Verify in Persian data
        invoice_data = invoice.generate_persian_invoice_data()
        financial_totals = invoice_data['financial_totals']
        self.assertNotEqual(financial_totals['discount_amount'], '۰')
    
    def test_invoice_with_tax(self):
        """Test invoice generation with tax calculation."""
        # Calculate tax for transaction
        POSTransactionService.calculate_tax(
            transaction=self.transaction,
            tax_rate=Decimal('9.00')  # Iranian VAT
        )
        
        # Generate invoice
        invoice = POSInvoiceService.generate_invoice_for_transaction(
            transaction=self.transaction
        )
        
        # Verify tax is included
        expected_tax = self.transaction.subtotal * Decimal('0.09')
        self.assertEqual(invoice.invoice_tax_amount, expected_tax.quantize(Decimal('0.01')))
        
        # Verify total includes tax
        expected_total = invoice.invoice_subtotal + invoice.invoice_tax_amount
        self.assertEqual(invoice.invoice_total_amount, expected_total)
    
    def test_invoice_for_walk_in_customer(self):
        """Test invoice generation for walk-in customer (no customer record)."""
        # Create transaction without customer
        transaction = POSTransactionService.create_transaction(
            customer_id=None,
            transaction_type='sale',
            payment_method='cash',
            user=self.user
        )
        
        # Add item and complete
        POSTransactionService.add_jewelry_item_to_transaction(
            transaction=transaction,
            jewelry_item_id=self.jewelry_item.id,
            quantity=1
        )
        
        POSTransactionService.process_payment(
            transaction=transaction,
            amount_paid=transaction.total_amount,
            payment_method='cash'
        )
        
        # Generate invoice
        invoice = POSInvoiceService.generate_invoice_for_transaction(transaction)
        invoice_data = invoice.generate_persian_invoice_data()
        
        # Verify walk-in customer handling
        customer_info = invoice_data['customer_info']
        self.assertEqual(customer_info['name'], 'مشتری نقدی')  # Cash customer
        self.assertEqual(customer_info['phone'], '')
        self.assertEqual(customer_info['address'], '')
    
    def test_invoice_number_uniqueness(self):
        """Test that invoice numbers are unique."""
        # Generate multiple invoices
        invoice1 = POSInvoiceService.generate_invoice_for_transaction(
            transaction=self.transaction
        )
        
        # Create another transaction and invoice
        transaction2 = POSTransactionService.create_transaction(
            customer_id=self.customer.id,
            transaction_type='sale',
            payment_method='cash',
            user=self.user
        )
        
        POSTransactionService.add_jewelry_item_to_transaction(
            transaction=transaction2,
            jewelry_item_id=self.jewelry_item.id,
            quantity=1
        )
        
        POSTransactionService.process_payment(
            transaction=transaction2,
            amount_paid=transaction2.total_amount,
            payment_method='cash'
        )
        
        invoice2 = POSInvoiceService.generate_invoice_for_transaction(transaction2)
        
        # Verify unique invoice numbers
        self.assertNotEqual(invoice1.invoice_number, invoice2.invoice_number)
        self.assertTrue(invoice1.invoice_number.startswith('INV-'))
        self.assertTrue(invoice2.invoice_number.startswith('INV-'))
    
    def test_invoice_already_exists(self):
        """Test that generating invoice for transaction with existing invoice returns existing invoice."""
        # Generate first invoice
        invoice1 = POSInvoiceService.generate_invoice_for_transaction(
            transaction=self.transaction
        )
        
        # Try to generate again
        invoice2 = POSInvoiceService.generate_invoice_for_transaction(
            transaction=self.transaction
        )
        
        # Should return the same invoice
        self.assertEqual(invoice1.id, invoice2.id)
        self.assertEqual(invoice1.invoice_number, invoice2.invoice_number)
    
    def test_invoice_with_gold_price_calculation(self):
        """Test that invoice includes gold price information from transaction."""
        # Verify transaction has gold price
        self.assertIsNotNone(self.transaction.gold_price_18k_at_transaction)
        self.assertGreater(self.transaction.gold_price_18k_at_transaction, 0)
        
        # Generate invoice
        invoice = POSInvoiceService.generate_invoice_for_transaction(
            transaction=self.transaction
        )
        
        # Verify line item has gold information
        line_item = self.transaction.line_items.first()
        self.assertEqual(line_item.gold_karat, 18)
        self.assertEqual(line_item.gold_weight_grams, Decimal('5.500'))
        self.assertIsNotNone(line_item.gold_price_per_gram_at_sale)
        
        # Verify invoice data includes gold weight
        invoice_data = invoice.generate_persian_invoice_data()
        line_items = invoice_data['line_items']
        self.assertIn('gold_weight', line_items[0])
        self.assertIn('گرم', line_items[0]['gold_weight'])  # Persian unit