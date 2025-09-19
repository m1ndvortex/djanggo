"""
Test suite for customer and supplier management models.

This test suite covers:
- Customer model with Persian name handling and loyalty point tracking
- Supplier model with purchase order and payment term management
- PurchaseOrder model for supplier relationship management
- Unit tests for customer and supplier model functionality
- Requirements: 9.3, 7.8
"""

import pytest
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone

from zargar.customers.models import (
    Customer, CustomerLoyaltyTransaction, CustomerNote,
    Supplier, PurchaseOrder, PurchaseOrderItem
)

User = get_user_model()


class CustomerModelTest(TestCase):
    """Test Customer model functionality."""
    
    def setUp(self):
        """Set up test data for each test."""
        # Create test user
        self.user = User.objects.create_user(
            username='testowner',
            email='owner@testshop.com',
            password='testpass123',
            role='owner',
            persian_first_name='علی',
            persian_last_name='احمدی'
        )
    
    def test_customer_creation_with_all_fields(self):
        """Test creating a customer with all fields."""
        customer = Customer.objects.create(
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
            internal_notes='Test customer',
            created_by=self.user
        )
        
        # Verify all fields
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
        self.assertEqual(customer.created_by, self.user)
    
    def test_customer_str_representation(self):
        """Test customer string representation."""
        # With Persian name
        customer_with_persian = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            persian_first_name='جان',
            persian_last_name='دو',
            phone_number='09123456789',
            created_by=self.user
        )
        self.assertEqual(str(customer_with_persian), 'جان دو')
        
        # Without Persian name
        customer_without_persian = Customer.objects.create(
            first_name='Jane',
            last_name='Smith',
            phone_number='09987654321',
            created_by=self.user
        )
        self.assertEqual(str(customer_without_persian), 'Jane Smith')
    
    def test_customer_full_name_properties(self):
        """Test customer full name properties."""
        customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            persian_first_name='جان',
            persian_last_name='دو',
            phone_number='09123456789',
            created_by=self.user
        )
        
        self.assertEqual(customer.full_name, 'John Doe')
        self.assertEqual(customer.full_persian_name, 'جان دو')
        
        # Test fallback when no Persian name
        customer_no_persian = Customer.objects.create(
            first_name='Jane',
            last_name='Smith',
            phone_number='09987654321',
            created_by=self.user
        )
        self.assertEqual(customer_no_persian.full_persian_name, 'Jane Smith')
    
    def test_customer_phone_validation(self):
        """Test customer phone number validation."""
        # Valid phone number
        customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            phone_number='09123456789',
            created_by=self.user
        )
        self.assertEqual(customer.phone_number, '09123456789')
        
        # Invalid phone number format
        with self.assertRaises(ValidationError):
            invalid_customer = Customer(
                first_name='Jane',
                last_name='Smith',
                phone_number='123456789',  # Invalid format
                created_by=self.user
            )
            invalid_customer.full_clean()
    
    def test_customer_loyalty_points_management(self):
        """Test customer loyalty points management."""
        customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            phone_number='09123456789',
            loyalty_points=100,
            created_by=self.user
        )
        
        # Add loyalty points
        customer.add_loyalty_points(50, "Purchase reward")
        customer.refresh_from_db()
        self.assertEqual(customer.loyalty_points, 150)
        
        # Check transaction was created
        transaction = CustomerLoyaltyTransaction.objects.filter(customer=customer).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.points, 50)
        self.assertEqual(transaction.transaction_type, 'earned')
        self.assertEqual(transaction.reason, "Purchase reward")
        
        # Redeem loyalty points
        success = customer.redeem_loyalty_points(75, "Discount applied")
        self.assertTrue(success)
        customer.refresh_from_db()
        self.assertEqual(customer.loyalty_points, 75)
        
        # Try to redeem more than available
        success = customer.redeem_loyalty_points(100, "Too much")
        self.assertFalse(success)
        customer.refresh_from_db()
        self.assertEqual(customer.loyalty_points, 75)  # Should remain unchanged
    
    def test_customer_purchase_stats_update(self):
        """Test customer purchase statistics update."""
        customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            phone_number='09123456789',
            total_purchases=Decimal('10000000.00'),
            created_by=self.user
        )
        
        # Update purchase stats
        customer.update_purchase_stats(Decimal('15000000.00'))
        customer.refresh_from_db()
        
        self.assertEqual(customer.total_purchases, Decimal('25000000.00'))
        self.assertIsNotNone(customer.last_purchase_date)
        
        # Test VIP upgrade
        customer.update_purchase_stats(Decimal('30000000.00'))  # Total will be 55M
        customer.refresh_from_db()
        
        self.assertTrue(customer.is_vip)
        self.assertEqual(customer.customer_type, 'vip')
    
    def test_customer_default_values(self):
        """Test customer default values."""
        customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            phone_number='09123456789',
            created_by=self.user
        )
        
        # Check default values
        self.assertEqual(customer.customer_type, 'individual')
        self.assertEqual(customer.loyalty_points, 0)
        self.assertEqual(customer.total_purchases, Decimal('0'))
        self.assertTrue(customer.is_active)
        self.assertFalse(customer.is_vip)


class SupplierModelTest(TestCase):
    """Test Supplier model functionality."""
    
    def setUp(self):
        """Set up test data for each test."""
        # Create test user
        self.user = User.objects.create_user(
            username='testowner',
            email='owner@testshop.com',
            password='testpass123',
            role='owner'
        )
    
    def test_supplier_creation_with_all_fields(self):
        """Test creating a supplier with all fields."""
        supplier = Supplier.objects.create(
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
            notes='Reliable supplier',
            created_by=self.user
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
        self.assertEqual(supplier.created_by, self.user)
    
    def test_supplier_str_representation(self):
        """Test supplier string representation."""
        # With Persian name
        supplier_with_persian = Supplier.objects.create(
            name='Gold Supplier',
            persian_name='تامین کننده طلا',
            supplier_type='gold_supplier',
            phone_number='02112345678',
            created_by=self.user
        )
        self.assertEqual(str(supplier_with_persian), 'تامین کننده طلا')
        
        # Without Persian name
        supplier_without_persian = Supplier.objects.create(
            name='Silver Supplier',
            supplier_type='manufacturer',
            phone_number='02187654321',
            created_by=self.user
        )
        self.assertEqual(str(supplier_without_persian), 'Silver Supplier')
    
    def test_supplier_type_choices(self):
        """Test supplier type choices."""
        valid_types = ['manufacturer', 'wholesaler', 'gemstone_dealer', 'gold_supplier', 'service_provider']
        
        for supplier_type in valid_types:
            supplier = Supplier.objects.create(
                name=f'Test {supplier_type.title()}',
                supplier_type=supplier_type,
                phone_number='02112345678',
                created_by=self.user
            )
            self.assertEqual(supplier.supplier_type, supplier_type)
    
    def test_supplier_order_stats_update(self):
        """Test supplier order statistics update."""
        supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='manufacturer',
            phone_number='02112345678',
            total_orders=5,
            total_amount=Decimal('25000000.00'),
            created_by=self.user
        )
        
        # Update order stats
        supplier.update_order_stats(Decimal('10000000.00'))
        supplier.refresh_from_db()
        
        self.assertEqual(supplier.total_orders, 6)
        self.assertEqual(supplier.total_amount, Decimal('35000000.00'))
        self.assertIsNotNone(supplier.last_order_date)
    
    def test_supplier_default_values(self):
        """Test supplier default values."""
        supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='manufacturer',
            phone_number='02112345678',
            created_by=self.user
        )
        
        # Check default values
        self.assertTrue(supplier.is_active)
        self.assertFalse(supplier.is_preferred)
        self.assertEqual(supplier.total_orders, 0)
        self.assertEqual(supplier.total_amount, Decimal('0'))


class PurchaseOrderModelTest(TestCase):
    """Test PurchaseOrder model functionality."""
    
    def setUp(self):
        """Set up test data for each test."""
        # Create test user
        self.user = User.objects.create_user(
            username='testowner',
            email='owner@testshop.com',
            password='testpass123',
            role='owner'
        )
        
        # Create test supplier
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='manufacturer',
            phone_number='02112345678',
            created_by=self.user
        )
    
    def test_purchase_order_creation(self):
        """Test creating a purchase order."""
        from django.utils import timezone
        
        order_date = timezone.now().date()
        expected_delivery = order_date + timezone.timedelta(days=7)
        
        po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=order_date,
            expected_delivery_date=expected_delivery,
            status='draft',
            priority='normal',
            subtotal=Decimal('10000000.00'),
            tax_amount=Decimal('900000.00'),
            discount_amount=Decimal('500000.00'),
            payment_terms='Net 30',
            notes='Test order',
            created_by=self.user
        )
        
        # Verify fields
        self.assertEqual(po.supplier, self.supplier)
        self.assertEqual(po.order_date, order_date)
        self.assertEqual(po.expected_delivery_date, expected_delivery)
        self.assertEqual(po.status, 'draft')
        self.assertEqual(po.priority, 'normal')
        self.assertEqual(po.subtotal, Decimal('10000000.00'))
        self.assertEqual(po.tax_amount, Decimal('900000.00'))
        self.assertEqual(po.discount_amount, Decimal('500000.00'))
        self.assertEqual(po.payment_terms, 'Net 30')
        self.assertEqual(po.notes, 'Test order')
        self.assertEqual(po.created_by, self.user)
        
        # Check auto-generated order number
        self.assertIsNotNone(po.order_number)
        self.assertTrue(po.order_number.startswith('PO-'))
        
        # Check calculated total
        expected_total = Decimal('10000000.00') + Decimal('900000.00') - Decimal('500000.00')
        self.assertEqual(po.total_amount, expected_total)
    
    def test_purchase_order_str_representation(self):
        """Test purchase order string representation."""
        po = PurchaseOrder.objects.create(
            order_number='PO-TEST-001',
            supplier=self.supplier,
            order_date=timezone.now().date(),
            created_by=self.user
        )
        
        expected_str = f"PO-TEST-001 - {self.supplier.name}"
        self.assertEqual(str(po), expected_str)
    
    def test_purchase_order_status_methods(self):
        """Test purchase order status management methods."""
        po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=timezone.now().date(),
            status='draft',
            created_by=self.user
        )
        
        # Mark as sent
        po.mark_as_sent()
        po.refresh_from_db()
        self.assertEqual(po.status, 'sent')
        
        # Mark as confirmed
        po.mark_as_confirmed()
        po.refresh_from_db()
        self.assertEqual(po.status, 'confirmed')
        
        # Mark as received (partial)
        po.mark_as_received(partial=True)
        po.refresh_from_db()
        self.assertEqual(po.status, 'partially_received')
        
        # Mark as completed
        po.mark_as_received(partial=False)
        po.refresh_from_db()
        self.assertEqual(po.status, 'completed')
        self.assertIsNotNone(po.actual_delivery_date)
        
        # Test cancel
        po2 = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=timezone.now().date(),
            status='sent',
            created_by=self.user
        )
        po2.cancel_order("Supplier unavailable")
        po2.refresh_from_db()
        self.assertEqual(po2.status, 'cancelled')
        self.assertIn("Cancelled: Supplier unavailable", po2.internal_notes)
    
    def test_purchase_order_overdue_property(self):
        """Test purchase order overdue property."""
        from django.utils import timezone
        
        # Order that's not overdue
        future_date = timezone.now().date() + timezone.timedelta(days=5)
        po_future = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=timezone.now().date(),
            expected_delivery_date=future_date,
            status='confirmed',
            created_by=self.user
        )
        self.assertFalse(po_future.is_overdue)
        
        # Order that's overdue
        past_date = timezone.now().date() - timezone.timedelta(days=5)
        po_past = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=timezone.now().date(),
            expected_delivery_date=past_date,
            status='confirmed',
            created_by=self.user
        )
        self.assertTrue(po_past.is_overdue)
        
        # Completed order should not be overdue
        po_completed = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=timezone.now().date(),
            expected_delivery_date=past_date,
            status='completed',
            created_by=self.user
        )
        self.assertFalse(po_completed.is_overdue)
    
    def test_purchase_order_days_until_delivery(self):
        """Test days until delivery calculation."""
        from django.utils import timezone
        
        # Future delivery
        future_date = timezone.now().date() + timezone.timedelta(days=7)
        po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=timezone.now().date(),
            expected_delivery_date=future_date,
            created_by=self.user
        )
        self.assertEqual(po.days_until_delivery, 7)
        
        # Past delivery
        past_date = timezone.now().date() - timezone.timedelta(days=3)
        po_past = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=timezone.now().date(),
            expected_delivery_date=past_date,
            created_by=self.user
        )
        self.assertEqual(po_past.days_until_delivery, -3)


class PurchaseOrderItemModelTest(TestCase):
    """Test PurchaseOrderItem model functionality."""
    
    def setUp(self):
        """Set up test data for each test."""
        # Create test user
        self.user = User.objects.create_user(
            username='testowner',
            email='owner@testshop.com',
            password='testpass123',
            role='owner'
        )
        
        # Create test supplier
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='manufacturer',
            phone_number='02112345678',
            created_by=self.user
        )
        
        # Create test purchase order
        self.purchase_order = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=timezone.now().date(),
            created_by=self.user
        )
    
    def test_purchase_order_item_creation(self):
        """Test creating a purchase order item."""
        item = PurchaseOrderItem.objects.create(
            purchase_order=self.purchase_order,
            item_name='Gold Ring',
            item_description='18k gold ring with diamond',
            sku='RING-001',
            quantity_ordered=5,
            unit_price=Decimal('2000000.00'),
            weight_grams=Decimal('15.750'),
            karat=18,
            gemstone_type='diamond',
            notes='Special order',
            created_by=self.user
        )
        
        # Verify fields
        self.assertEqual(item.purchase_order, self.purchase_order)
        self.assertEqual(item.item_name, 'Gold Ring')
        self.assertEqual(item.item_description, '18k gold ring with diamond')
        self.assertEqual(item.sku, 'RING-001')
        self.assertEqual(item.quantity_ordered, 5)
        self.assertEqual(item.unit_price, Decimal('2000000.00'))
        self.assertEqual(item.weight_grams, Decimal('15.750'))
        self.assertEqual(item.karat, 18)
        self.assertEqual(item.gemstone_type, 'diamond')
        self.assertEqual(item.notes, 'Special order')
        self.assertEqual(item.created_by, self.user)
        
        # Check calculated total price
        expected_total = 5 * Decimal('2000000.00')
        self.assertEqual(item.total_price, expected_total)
    
    def test_purchase_order_item_str_representation(self):
        """Test purchase order item string representation."""
        item = PurchaseOrderItem.objects.create(
            purchase_order=self.purchase_order,
            item_name='Gold Necklace',
            quantity_ordered=2,
            unit_price=Decimal('5000000.00'),
            created_by=self.user
        )
        
        expected_str = f"{self.purchase_order.order_number} - Gold Necklace"
        self.assertEqual(str(item), expected_str)
    
    def test_purchase_order_item_receive_quantity(self):
        """Test receiving quantities of purchase order items."""
        item = PurchaseOrderItem.objects.create(
            purchase_order=self.purchase_order,
            item_name='Gold Bracelet',
            quantity_ordered=10,
            unit_price=Decimal('1500000.00'),
            created_by=self.user
        )
        
        # Initially no quantity received
        self.assertEqual(item.quantity_received, 0)
        self.assertEqual(item.quantity_pending, 10)
        self.assertFalse(item.is_fully_received)
        self.assertFalse(item.is_received)
        
        # Receive partial quantity
        success = item.receive_quantity(4)
        self.assertTrue(success)
        item.refresh_from_db()
        self.assertEqual(item.quantity_received, 4)
        self.assertEqual(item.quantity_pending, 6)
        self.assertFalse(item.is_fully_received)
        
        # Receive remaining quantity
        success = item.receive_quantity(6)
        self.assertTrue(success)
        item.refresh_from_db()
        self.assertEqual(item.quantity_received, 10)
        self.assertEqual(item.quantity_pending, 0)
        self.assertTrue(item.is_fully_received)
        self.assertTrue(item.is_received)
        self.assertIsNotNone(item.received_date)
        
        # Try to receive more than ordered
        success = item.receive_quantity(5)
        self.assertTrue(success)  # Should succeed but not exceed ordered quantity
        item.refresh_from_db()
        self.assertEqual(item.quantity_received, 10)  # Should remain at 10
    
    def test_purchase_order_totals_update(self):
        """Test that purchase order totals are updated when items change."""
        # Create items
        item1 = PurchaseOrderItem.objects.create(
            purchase_order=self.purchase_order,
            item_name='Item 1',
            quantity_ordered=2,
            unit_price=Decimal('1000000.00'),
            created_by=self.user
        )
        
        item2 = PurchaseOrderItem.objects.create(
            purchase_order=self.purchase_order,
            item_name='Item 2',
            quantity_ordered=3,
            unit_price=Decimal('2000000.00'),
            created_by=self.user
        )
        
        # Check purchase order subtotal
        self.purchase_order.refresh_from_db()
        expected_subtotal = Decimal('2000000.00') + Decimal('6000000.00')  # 2*1M + 3*2M
        self.assertEqual(self.purchase_order.subtotal, expected_subtotal)


if __name__ == '__main__':
    pytest.main([__file__])