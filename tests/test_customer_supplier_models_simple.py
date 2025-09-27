"""
Simple test suite for customer and supplier management models.
Tests model definitions, validation, and basic functionality without database operations.
"""

import pytest
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from zargar.customers.models import (
    Customer, CustomerLoyaltyTransaction, CustomerNote,
    Supplier, PurchaseOrder, PurchaseOrderItem
)

User = get_user_model()


class CustomerModelDefinitionTest(TestCase):
    """Test Customer model definitions and basic functionality."""
    
    def test_customer_model_fields(self):
        """Test Customer model field definitions."""
        # Test model can be instantiated
        customer = Customer(
            first_name='John',
            last_name='Doe',
            persian_first_name='جان',
            persian_last_name='دو',
            phone_number='09123456789',
            email='john.doe@example.com',
            address='123 Main St',
            city='Tehran',
            province='Tehran',
            postal_code='1234567890',
            national_id='1234567890',
            customer_type='individual',
            loyalty_points=100,
            total_purchases=Decimal('5000000.00'),
            is_active=True,
            is_vip=False,
            internal_notes='Test customer'
        )
        
        # Test field values
        self.assertEqual(customer.first_name, 'John')
        self.assertEqual(customer.last_name, 'Doe')
        self.assertEqual(customer.persian_first_name, 'جان')
        self.assertEqual(customer.persian_last_name, 'دو')
        self.assertEqual(customer.phone_number, '09123456789')
        self.assertEqual(customer.email, 'john.doe@example.com')
        self.assertEqual(customer.address, '123 Main St')
        self.assertEqual(customer.city, 'Tehran')
        self.assertEqual(customer.province, 'Tehran')
        self.assertEqual(customer.postal_code, '1234567890')
        self.assertEqual(customer.national_id, '1234567890')
        self.assertEqual(customer.customer_type, 'individual')
        self.assertEqual(customer.loyalty_points, 100)
        self.assertEqual(customer.total_purchases, Decimal('5000000.00'))
        self.assertTrue(customer.is_active)
        self.assertFalse(customer.is_vip)
        self.assertEqual(customer.internal_notes, 'Test customer')
    
    def test_customer_str_method(self):
        """Test Customer string representation."""
        # With Persian name
        customer_with_persian = Customer(
            first_name='John',
            last_name='Doe',
            persian_first_name='جان',
            persian_last_name='دو'
        )
        self.assertEqual(str(customer_with_persian), 'جان دو')
        
        # Without Persian name
        customer_without_persian = Customer(
            first_name='Jane',
            last_name='Smith'
        )
        self.assertEqual(str(customer_without_persian), 'Jane Smith')
    
    def test_customer_full_name_properties(self):
        """Test customer full name properties."""
        customer = Customer(
            first_name='John',
            last_name='Doe',
            persian_first_name='جان',
            persian_last_name='دو'
        )
        
        self.assertEqual(customer.full_name, 'John Doe')
        self.assertEqual(customer.full_persian_name, 'جان دو')
        
        # Test fallback when no Persian name
        customer_no_persian = Customer(
            first_name='Jane',
            last_name='Smith'
        )
        self.assertEqual(customer_no_persian.full_persian_name, 'Jane Smith')
    
    def test_customer_type_choices(self):
        """Test customer type choices."""
        valid_types = ['individual', 'business', 'vip']
        
        for customer_type in valid_types:
            customer = Customer(
                first_name='Test',
                last_name='Customer',
                customer_type=customer_type
            )
            self.assertEqual(customer.customer_type, customer_type)
    
    def test_customer_default_values(self):
        """Test customer default values."""
        customer = Customer(
            first_name='John',
            last_name='Doe'
        )
        
        # Check default values
        self.assertEqual(customer.customer_type, 'individual')
        self.assertEqual(customer.loyalty_points, 0)
        self.assertEqual(customer.total_purchases, Decimal('0'))
        self.assertTrue(customer.is_active)
        self.assertFalse(customer.is_vip)


class SupplierModelDefinitionTest(TestCase):
    """Test Supplier model definitions and basic functionality."""
    
    def test_supplier_model_fields(self):
        """Test Supplier model field definitions."""
        supplier = Supplier(
            name='Gold Supplier Inc',
            persian_name='تامین کننده طلا',
            supplier_type='gold_supplier',
            contact_person='Ahmad Rezaei',
            phone_number='02112345678',
            email='info@goldsupplier.com',
            website='https://goldsupplier.com',
            address='123 Gold Street',
            city='Tehran',
            tax_id='1234567890',
            payment_terms='Net 30',
            credit_limit=Decimal('100000000.00'),
            is_active=True,
            is_preferred=True,
            notes='Reliable supplier'
        )
        
        # Verify all fields
        self.assertEqual(supplier.name, 'Gold Supplier Inc')
        self.assertEqual(supplier.persian_name, 'تامین کننده طلا')
        self.assertEqual(supplier.supplier_type, 'gold_supplier')
        self.assertEqual(supplier.contact_person, 'Ahmad Rezaei')
        self.assertEqual(supplier.phone_number, '02112345678')
        self.assertEqual(supplier.email, 'info@goldsupplier.com')
        self.assertEqual(supplier.website, 'https://goldsupplier.com')
        self.assertEqual(supplier.address, '123 Gold Street')
        self.assertEqual(supplier.city, 'Tehran')
        self.assertEqual(supplier.tax_id, '1234567890')
        self.assertEqual(supplier.payment_terms, 'Net 30')
        self.assertEqual(supplier.credit_limit, Decimal('100000000.00'))
        self.assertTrue(supplier.is_active)
        self.assertTrue(supplier.is_preferred)
        self.assertEqual(supplier.notes, 'Reliable supplier')
    
    def test_supplier_str_method(self):
        """Test Supplier string representation."""
        # With Persian name
        supplier_with_persian = Supplier(
            name='Gold Supplier',
            persian_name='تامین کننده طلا'
        )
        self.assertEqual(str(supplier_with_persian), 'تامین کننده طلا')
        
        # Without Persian name
        supplier_without_persian = Supplier(
            name='Silver Supplier'
        )
        self.assertEqual(str(supplier_without_persian), 'Silver Supplier')
    
    def test_supplier_type_choices(self):
        """Test supplier type choices."""
        valid_types = ['manufacturer', 'wholesaler', 'gemstone_dealer', 'gold_supplier', 'service_provider']
        
        for supplier_type in valid_types:
            supplier = Supplier(
                name=f'Test {supplier_type.title()}',
                supplier_type=supplier_type
            )
            self.assertEqual(supplier.supplier_type, supplier_type)
    
    def test_supplier_default_values(self):
        """Test supplier default values."""
        supplier = Supplier(
            name='Test Supplier',
            supplier_type='manufacturer'
        )
        
        # Check default values
        self.assertTrue(supplier.is_active)
        self.assertFalse(supplier.is_preferred)
        self.assertEqual(supplier.total_orders, 0)
        self.assertEqual(supplier.total_amount, Decimal('0'))


class PurchaseOrderModelDefinitionTest(TestCase):
    """Test PurchaseOrder model definitions and basic functionality."""
    
    def test_purchase_order_model_fields(self):
        """Test PurchaseOrder model field definitions."""
        from django.utils import timezone
        
        order_date = timezone.now().date()
        expected_delivery = order_date + timezone.timedelta(days=7)
        
        po = PurchaseOrder(
            order_number='PO-TEST-001',
            order_date=order_date,
            expected_delivery_date=expected_delivery,
            status='draft',
            priority='normal',
            subtotal=Decimal('10000000.00'),
            tax_amount=Decimal('900000.00'),
            discount_amount=Decimal('500000.00'),
            payment_terms='Net 30',
            notes='Test order'
        )
        
        # Verify fields
        self.assertEqual(po.order_number, 'PO-TEST-001')
        self.assertEqual(po.order_date, order_date)
        self.assertEqual(po.expected_delivery_date, expected_delivery)
        self.assertEqual(po.status, 'draft')
        self.assertEqual(po.priority, 'normal')
        self.assertEqual(po.subtotal, Decimal('10000000.00'))
        self.assertEqual(po.tax_amount, Decimal('900000.00'))
        self.assertEqual(po.discount_amount, Decimal('500000.00'))
        self.assertEqual(po.payment_terms, 'Net 30')
        self.assertEqual(po.notes, 'Test order')
    
    def test_purchase_order_status_choices(self):
        """Test purchase order status choices."""
        valid_statuses = ['draft', 'sent', 'confirmed', 'partially_received', 'completed', 'cancelled']
        
        for status in valid_statuses:
            po = PurchaseOrder(
                order_number=f'PO-{status.upper()}',
                status=status
            )
            self.assertEqual(po.status, status)
    
    def test_purchase_order_priority_choices(self):
        """Test purchase order priority choices."""
        valid_priorities = ['low', 'normal', 'high', 'urgent']
        
        for priority in valid_priorities:
            po = PurchaseOrder(
                order_number=f'PO-{priority.upper()}',
                priority=priority
            )
            self.assertEqual(po.priority, priority)
    
    def test_purchase_order_default_values(self):
        """Test purchase order default values."""
        po = PurchaseOrder(
            order_number='PO-DEFAULT'
        )
        
        # Check default values
        self.assertEqual(po.status, 'draft')
        self.assertEqual(po.priority, 'normal')
        self.assertEqual(po.subtotal, Decimal('0'))
        self.assertEqual(po.tax_amount, Decimal('0'))
        self.assertEqual(po.discount_amount, Decimal('0'))
        self.assertEqual(po.total_amount, Decimal('0'))
        self.assertFalse(po.is_paid)
    
    def test_purchase_order_generate_order_number(self):
        """Test purchase order number generation."""
        po = PurchaseOrder()
        order_number = po.generate_order_number()
        
        # Should start with PO- and contain date
        self.assertTrue(order_number.startswith('PO-'))
        self.assertIn('2025', order_number)  # Current year
        self.assertGreaterEqual(len(order_number), 15)  # PO-YYYYMMDD-XXXX format (at least 15 chars)


class PurchaseOrderItemModelDefinitionTest(TestCase):
    """Test PurchaseOrderItem model definitions and basic functionality."""
    
    def test_purchase_order_item_model_fields(self):
        """Test PurchaseOrderItem model field definitions."""
        item = PurchaseOrderItem(
            item_name='Gold Ring',
            item_description='18k gold ring with diamond',
            sku='RING-001',
            quantity_ordered=5,
            unit_price=Decimal('2000000.00'),
            weight_grams=Decimal('15.750'),
            karat=18,
            gemstone_type='diamond',
            notes='Special order'
        )
        
        # Verify fields
        self.assertEqual(item.item_name, 'Gold Ring')
        self.assertEqual(item.item_description, '18k gold ring with diamond')
        self.assertEqual(item.sku, 'RING-001')
        self.assertEqual(item.quantity_ordered, 5)
        self.assertEqual(item.unit_price, Decimal('2000000.00'))
        self.assertEqual(item.weight_grams, Decimal('15.750'))
        self.assertEqual(item.karat, 18)
        self.assertEqual(item.gemstone_type, 'diamond')
        self.assertEqual(item.notes, 'Special order')
    
    def test_purchase_order_item_quantity_properties(self):
        """Test purchase order item quantity properties."""
        item = PurchaseOrderItem(
            quantity_ordered=10,
            quantity_received=4
        )
        
        self.assertEqual(item.quantity_pending, 6)
        self.assertFalse(item.is_fully_received)
        
        # Test fully received
        item.quantity_received = 10
        self.assertEqual(item.quantity_pending, 0)
        self.assertTrue(item.is_fully_received)
        
        # Test over-received
        item.quantity_received = 12
        self.assertEqual(item.quantity_pending, 0)  # Should not go negative
        self.assertTrue(item.is_fully_received)
    
    def test_purchase_order_item_default_values(self):
        """Test purchase order item default values."""
        item = PurchaseOrderItem(
            item_name='Test Item',
            quantity_ordered=1,
            unit_price=Decimal('1000000.00')
        )
        
        # Check default values
        self.assertEqual(item.quantity_received, 0)
        self.assertFalse(item.is_received)


class CustomerLoyaltyTransactionModelTest(TestCase):
    """Test CustomerLoyaltyTransaction model definitions."""
    
    def test_loyalty_transaction_model_fields(self):
        """Test CustomerLoyaltyTransaction model field definitions."""
        transaction = CustomerLoyaltyTransaction(
            points=50,
            transaction_type='earned',
            reason='Purchase reward',
            reference_id='SALE-001'
        )
        
        # Verify fields
        self.assertEqual(transaction.points, 50)
        self.assertEqual(transaction.transaction_type, 'earned')
        self.assertEqual(transaction.reason, 'Purchase reward')
        self.assertEqual(transaction.reference_id, 'SALE-001')
    
    def test_loyalty_transaction_type_choices(self):
        """Test loyalty transaction type choices."""
        valid_types = ['earned', 'redeemed', 'expired', 'adjusted']
        
        for transaction_type in valid_types:
            transaction = CustomerLoyaltyTransaction(
                points=10,
                transaction_type=transaction_type
            )
            self.assertEqual(transaction.transaction_type, transaction_type)


class CustomerNoteModelTest(TestCase):
    """Test CustomerNote model definitions."""
    
    def test_customer_note_model_fields(self):
        """Test CustomerNote model field definitions."""
        note = CustomerNote(
            note_type='complaint',
            title='Product Issue',
            content='Customer reported quality issue',
            is_important=True,
            is_resolved=False
        )
        
        # Verify fields
        self.assertEqual(note.note_type, 'complaint')
        self.assertEqual(note.title, 'Product Issue')
        self.assertEqual(note.content, 'Customer reported quality issue')
        self.assertTrue(note.is_important)
        self.assertFalse(note.is_resolved)
    
    def test_customer_note_type_choices(self):
        """Test customer note type choices."""
        valid_types = ['general', 'complaint', 'compliment', 'follow_up', 'preference']
        
        for note_type in valid_types:
            note = CustomerNote(
                note_type=note_type,
                title='Test Note',
                content='Test content'
            )
            self.assertEqual(note.note_type, note_type)
    
    def test_customer_note_default_values(self):
        """Test customer note default values."""
        note = CustomerNote(
            title='Test Note',
            content='Test content'
        )
        
        # Check default values
        self.assertEqual(note.note_type, 'general')
        self.assertFalse(note.is_important)
        self.assertFalse(note.is_resolved)


class ModelMetaOptionsTest(TestCase):
    """Test model Meta options."""
    
    def test_customer_meta_options(self):
        """Test Customer model Meta options."""
        # Persian verbose names are expected for this Persian-first application
        self.assertIn(Customer._meta.verbose_name.lower(), ['customer', 'مشتری'])
        self.assertIn(Customer._meta.verbose_name_plural.lower(), ['customers', 'مشتریان'])
        
        # Test indexes
        indexes = Customer._meta.indexes
        index_fields = [list(index.fields) for index in indexes]
        
        expected_indexes = [
            ['phone_number'],
            ['email'],
            ['customer_type'],
            ['is_vip']
        ]
        
        for expected_index in expected_indexes:
            self.assertIn(expected_index, index_fields, 
                         f"Index on {expected_index} should exist")
    
    def test_supplier_meta_options(self):
        """Test Supplier model Meta options."""
        self.assertEqual(Supplier._meta.verbose_name.lower(), 'supplier')
        self.assertEqual(Supplier._meta.verbose_name_plural.lower(), 'suppliers')
        
        # Test indexes
        indexes = Supplier._meta.indexes
        index_fields = [list(index.fields) for index in indexes]
        
        expected_indexes = [
            ['supplier_type'],
            ['is_active'],
            ['is_preferred']
        ]
        
        for expected_index in expected_indexes:
            self.assertIn(expected_index, index_fields, 
                         f"Index on {expected_index} should exist")
    
    def test_purchase_order_meta_options(self):
        """Test PurchaseOrder model Meta options."""
        self.assertEqual(PurchaseOrder._meta.verbose_name.lower(), 'purchase order')
        self.assertEqual(PurchaseOrder._meta.verbose_name_plural.lower(), 'purchase orders')
        self.assertEqual(PurchaseOrder._meta.ordering, ['-order_date', '-created_at'])
        
        # Test indexes
        indexes = PurchaseOrder._meta.indexes
        index_fields = [list(index.fields) for index in indexes]
        
        expected_indexes = [
            ['order_number'],
            ['supplier'],
            ['status'],
            ['order_date'],
            ['expected_delivery_date']
        ]
        
        for expected_index in expected_indexes:
            self.assertIn(expected_index, index_fields, 
                         f"Index on {expected_index} should exist")
    
    def test_purchase_order_item_meta_options(self):
        """Test PurchaseOrderItem model Meta options."""
        self.assertEqual(PurchaseOrderItem._meta.verbose_name.lower(), 'purchase order item')
        self.assertEqual(PurchaseOrderItem._meta.verbose_name_plural.lower(), 'purchase order items')
        self.assertEqual(PurchaseOrderItem._meta.ordering, ['id'])


if __name__ == '__main__':
    pytest.main([__file__])