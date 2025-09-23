"""
Tests for supplier management backend functionality.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status

from zargar.customers.models import Supplier, PurchaseOrder, PurchaseOrderItem
from zargar.customers.supplier_services import (
    SupplierPayment,
    DeliverySchedule,
    SupplierPerformanceMetrics,
    SupplierManagementService
)

User = get_user_model()


class SupplierModelTest(TestCase):
    """Test supplier model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
    
    def test_create_supplier(self):
        """Test creating a supplier."""
        supplier = Supplier.objects.create(
            name='Test Supplier',
            persian_name='تامین کننده تست',
            supplier_type='manufacturer',
            phone_number='09123456789',
            email='supplier@example.com',
            payment_terms='Net 30',
            credit_limit=Decimal('10000000.00'),
            created_by=self.user
        )
        
        self.assertEqual(supplier.name, 'Test Supplier')
        self.assertEqual(supplier.persian_name, 'تامین کننده تست')
        self.assertEqual(supplier.supplier_type, 'manufacturer')
        self.assertTrue(supplier.is_active)
        self.assertFalse(supplier.is_preferred)
        self.assertEqual(supplier.total_orders, 0)
        self.assertEqual(supplier.total_amount, 0)
    
    def test_supplier_string_representation(self):
        """Test supplier string representation."""
        supplier = Supplier.objects.create(
            name='Test Supplier',
            persian_name='تامین کننده تست',
            supplier_type='manufacturer',
            phone_number='09123456789',
            created_by=self.user
        )
        
        self.assertEqual(str(supplier), 'تامین کننده تست')
        
        # Test without Persian name
        supplier.persian_name = ''
        supplier.save()
        self.assertEqual(str(supplier), 'Test Supplier')
    
    def test_update_order_stats(self):
        """Test updating supplier order statistics."""
        supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='manufacturer',
            phone_number='09123456789',
            created_by=self.user
        )
        
        # Update stats
        supplier.update_order_stats(Decimal('5000000.00'))
        
        self.assertEqual(supplier.total_orders, 1)
        self.assertEqual(supplier.total_amount, Decimal('5000000.00'))
        self.assertIsNotNone(supplier.last_order_date)


class PurchaseOrderModelTest(TestCase):
    """Test purchase order model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
        
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='manufacturer',
            phone_number='09123456789',
            created_by=self.user
        )
    
    def test_create_purchase_order(self):
        """Test creating a purchase order."""
        po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=date.today(),
            expected_delivery_date=date.today() + timedelta(days=7),
            subtotal=Decimal('1000000.00'),
            tax_amount=Decimal('90000.00'),
            shipping_cost=Decimal('50000.00'),
            created_by=self.user
        )
        
        self.assertIsNotNone(po.order_number)
        self.assertTrue(po.order_number.startswith('PO-'))
        self.assertEqual(po.status, 'draft')
        self.assertEqual(po.priority, 'normal')
        self.assertEqual(po.total_amount, Decimal('1140000.00'))  # subtotal + tax + shipping
        self.assertFalse(po.is_paid)
    
    def test_purchase_order_number_generation(self):
        """Test automatic purchase order number generation."""
        po1 = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=date.today(),
            created_by=self.user
        )
        
        po2 = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=date.today(),
            created_by=self.user
        )
        
        self.assertIsNotNone(po1.order_number)
        self.assertIsNotNone(po2.order_number)
        self.assertNotEqual(po1.order_number, po2.order_number)
    
    def test_purchase_order_overdue_property(self):
        """Test purchase order overdue property."""
        # Create overdue order
        overdue_po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=date.today() - timedelta(days=10),
            expected_delivery_date=date.today() - timedelta(days=2),
            status='confirmed',
            created_by=self.user
        )
        
        # Create future order
        future_po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=date.today(),
            expected_delivery_date=date.today() + timedelta(days=5),
            status='confirmed',
            created_by=self.user
        )
        
        self.assertTrue(overdue_po.is_overdue)
        self.assertFalse(future_po.is_overdue)
    
    def test_purchase_order_status_transitions(self):
        """Test purchase order status transitions."""
        po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=date.today(),
            created_by=self.user
        )
        
        # Test status transitions
        po.mark_as_sent()
        self.assertEqual(po.status, 'sent')
        
        po.mark_as_confirmed()
        self.assertEqual(po.status, 'confirmed')
        
        po.mark_as_received()
        self.assertEqual(po.status, 'completed')
        self.assertIsNotNone(po.actual_delivery_date)
    
    def test_cancel_purchase_order(self):
        """Test cancelling a purchase order."""
        po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=date.today(),
            created_by=self.user
        )
        
        po.cancel_order(reason="Supplier unavailable")
        
        self.assertEqual(po.status, 'cancelled')
        self.assertIn("Cancelled: Supplier unavailable", po.internal_notes)


class PurchaseOrderItemModelTest(TestCase):
    """Test purchase order item model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
        
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='manufacturer',
            phone_number='09123456789',
            created_by=self.user
        )
        
        self.po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=date.today(),
            created_by=self.user
        )
    
    def test_create_purchase_order_item(self):
        """Test creating a purchase order item."""
        item = PurchaseOrderItem.objects.create(
            purchase_order=self.po,
            item_name='Gold Ring',
            quantity_ordered=10,
            unit_price=Decimal('500000.00'),
            weight_grams=Decimal('5.500'),
            karat=18,
            created_by=self.user
        )
        
        self.assertEqual(item.item_name, 'Gold Ring')
        self.assertEqual(item.quantity_ordered, 10)
        self.assertEqual(item.quantity_received, 0)
        self.assertEqual(item.total_price, Decimal('5000000.00'))  # 10 * 500000
        self.assertFalse(item.is_received)
        self.assertEqual(item.quantity_pending, 10)
    
    def test_receive_item_quantity(self):
        """Test receiving item quantities."""
        item = PurchaseOrderItem.objects.create(
            purchase_order=self.po,
            item_name='Gold Ring',
            quantity_ordered=10,
            unit_price=Decimal('500000.00'),
            created_by=self.user
        )
        
        # Receive partial quantity
        success = item.receive_quantity(5)
        self.assertTrue(success)
        self.assertEqual(item.quantity_received, 5)
        self.assertEqual(item.quantity_pending, 5)
        self.assertFalse(item.is_fully_received)
        
        # Receive remaining quantity
        success = item.receive_quantity(5)
        self.assertTrue(success)
        self.assertEqual(item.quantity_received, 10)
        self.assertEqual(item.quantity_pending, 0)
        self.assertTrue(item.is_fully_received)
        self.assertTrue(item.is_received)
        self.assertIsNotNone(item.received_date)
    
    def test_receive_excess_quantity(self):
        """Test receiving more than ordered quantity."""
        item = PurchaseOrderItem.objects.create(
            purchase_order=self.po,
            item_name='Gold Ring',
            quantity_ordered=10,
            unit_price=Decimal('500000.00'),
            created_by=self.user
        )
        
        # Try to receive more than ordered
        success = item.receive_quantity(15)
        self.assertTrue(success)
        self.assertEqual(item.quantity_received, 10)  # Should cap at ordered quantity


class SupplierPaymentModelTest(TestCase):
    """Test supplier payment model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
        
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='manufacturer',
            phone_number='09123456789',
            created_by=self.user
        )
        
        self.po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=date.today(),
            total_amount=Decimal('5000000.00'),
            created_by=self.user
        )
    
    def test_create_supplier_payment(self):
        """Test creating a supplier payment."""
        payment = SupplierPayment.objects.create(
            supplier=self.supplier,
            purchase_order=self.po,
            amount=Decimal('2500000.00'),
            payment_date=date.today(),
            payment_method='bank_transfer',
            reference_number='TXN123456',
            created_by=self.user
        )
        
        self.assertIsNotNone(payment.payment_number)
        self.assertTrue(payment.payment_number.startswith('PAY-'))
        self.assertEqual(payment.status, 'pending')
        self.assertFalse(payment.is_approved)
        self.assertEqual(payment.amount, Decimal('2500000.00'))
    
    def test_approve_payment(self):
        """Test approving a payment."""
        payment = SupplierPayment.objects.create(
            supplier=self.supplier,
            amount=Decimal('1000000.00'),
            payment_date=date.today(),
            payment_method='cash',
            created_by=self.user
        )
        
        payment.approve_payment(self.user)
        
        self.assertTrue(payment.is_approved)
        self.assertEqual(payment.approved_by, self.user)
        self.assertIsNotNone(payment.approved_at)
        self.assertEqual(payment.status, 'processing')
    
    def test_complete_payment(self):
        """Test completing a payment."""
        payment = SupplierPayment.objects.create(
            supplier=self.supplier,
            amount=Decimal('1000000.00'),
            payment_date=date.today(),
            payment_method='cash',
            created_by=self.user
        )
        
        # Must approve before completing
        payment.approve_payment(self.user)
        payment.mark_as_completed()
        
        self.assertEqual(payment.status, 'completed')
    
    def test_cancel_payment(self):
        """Test cancelling a payment."""
        payment = SupplierPayment.objects.create(
            supplier=self.supplier,
            amount=Decimal('1000000.00'),
            payment_date=date.today(),
            payment_method='cash',
            created_by=self.user
        )
        
        payment.cancel_payment(reason="Duplicate payment")
        
        self.assertEqual(payment.status, 'cancelled')
        self.assertIn("Cancelled: Duplicate payment", payment.notes)


class DeliveryScheduleModelTest(TestCase):
    """Test delivery schedule model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
        
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='manufacturer',
            phone_number='09123456789',
            created_by=self.user
        )
        
        self.po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=date.today(),
            created_by=self.user
        )
    
    def test_create_delivery_schedule(self):
        """Test creating a delivery schedule."""
        delivery = DeliverySchedule.objects.create(
            purchase_order=self.po,
            scheduled_date=date.today() + timedelta(days=3),
            delivery_method='courier',
            delivery_address='Test Address',
            delivery_cost=Decimal('100000.00'),
            created_by=self.user
        )
        
        self.assertIsNotNone(delivery.delivery_number)
        self.assertTrue(delivery.delivery_number.startswith('DEL-'))
        self.assertEqual(delivery.status, 'scheduled')
        self.assertEqual(delivery.delivery_method, 'courier')
        self.assertFalse(delivery.is_overdue)
    
    def test_delivery_overdue_property(self):
        """Test delivery overdue property."""
        # Create overdue delivery
        overdue_delivery = DeliverySchedule.objects.create(
            purchase_order=self.po,
            scheduled_date=date.today() - timedelta(days=2),
            delivery_method='courier',
            delivery_address='Test Address',
            created_by=self.user
        )
        
        # Create future delivery
        future_delivery = DeliverySchedule.objects.create(
            purchase_order=self.po,
            scheduled_date=date.today() + timedelta(days=2),
            delivery_method='courier',
            delivery_address='Test Address',
            created_by=self.user
        )
        
        self.assertTrue(overdue_delivery.is_overdue)
        self.assertFalse(future_delivery.is_overdue)
    
    def test_mark_delivery_as_delivered(self):
        """Test marking delivery as delivered."""
        delivery = DeliverySchedule.objects.create(
            purchase_order=self.po,
            scheduled_date=date.today(),
            delivery_method='courier',
            delivery_address='Test Address',
            created_by=self.user
        )
        
        delivery.mark_as_delivered(
            received_by_name='John Doe',
            signature='Signature data'
        )
        
        self.assertEqual(delivery.status, 'delivered')
        self.assertIsNotNone(delivery.actual_delivery_date)
        self.assertEqual(delivery.received_by_name, 'John Doe')
        self.assertEqual(delivery.received_by_signature, 'Signature data')
    
    def test_mark_delivery_as_delayed(self):
        """Test marking delivery as delayed."""
        delivery = DeliverySchedule.objects.create(
            purchase_order=self.po,
            scheduled_date=date.today(),
            delivery_method='courier',
            delivery_address='Test Address',
            created_by=self.user
        )
        
        new_date = date.today() + timedelta(days=5)
        delivery.mark_as_delayed(new_date=new_date, reason='Weather conditions')
        
        self.assertEqual(delivery.status, 'delayed')
        self.assertEqual(delivery.scheduled_date, new_date)
        self.assertIn('Delayed: Weather conditions', delivery.notes)


class SupplierPerformanceMetricsTest(TestCase):
    """Test supplier performance metrics functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
        
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='manufacturer',
            phone_number='09123456789',
            created_by=self.user
        )
        
        self.metrics = SupplierPerformanceMetrics.objects.create(
            supplier=self.supplier,
            total_deliveries=10,
            on_time_deliveries=8,
            late_deliveries=2,
            total_items_received=100,
            defective_items=2,
            returned_items=1,
            total_order_value=Decimal('50000000.00'),
            created_by=self.user
        )
    
    def test_on_time_delivery_rate(self):
        """Test on-time delivery rate calculation."""
        rate = self.metrics.on_time_delivery_rate
        self.assertEqual(rate, 80.0)  # 8/10 * 100
    
    def test_quality_rate(self):
        """Test quality rate calculation."""
        rate = self.metrics.quality_rate
        self.assertEqual(rate, 97.0)  # (100-2-1)/100 * 100
    
    def test_update_metrics(self):
        """Test updating performance metrics."""
        # Create some test data
        po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=date.today(),
            status='completed',
            total_amount=Decimal('1000000.00'),
            created_by=self.user
        )
        
        delivery = DeliverySchedule.objects.create(
            purchase_order=po,
            scheduled_date=date.today(),
            actual_delivery_date=timezone.now(),
            status='delivered',
            delivery_method='courier',
            delivery_address='Test Address',
            created_by=self.user
        )
        
        # Update metrics
        self.metrics.update_metrics()
        
        # Check that metrics were updated
        self.assertGreater(self.metrics.total_order_value, Decimal('50000000.00'))


class SupplierManagementServiceTest(TestCase):
    """Test supplier management service functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
    
    def test_create_supplier_with_contact_terms(self):
        """Test creating supplier with contact and payment terms."""
        contact_info = {
            'contact_person': 'John Smith',
            'phone_number': '09123456789',
            'email': 'john@supplier.com',
            'address': '123 Main St',
            'city': 'Tehran'
        }
        
        payment_terms = {
            'tax_id': '123456789',
            'terms': 'Net 30',
            'credit_limit': Decimal('5000000.00')
        }
        
        supplier = SupplierManagementService.create_supplier_with_contact_terms(
            name='Test Supplier',
            persian_name='تامین کننده تست',
            supplier_type='manufacturer',
            contact_info=contact_info,
            payment_terms=payment_terms
        )
        
        self.assertEqual(supplier.name, 'Test Supplier')
        self.assertEqual(supplier.contact_person, 'John Smith')
        self.assertEqual(supplier.payment_terms, 'Net 30')
        self.assertEqual(supplier.credit_limit, Decimal('5000000.00'))
        
        # Check that performance metrics were created
        self.assertTrue(
            SupplierPerformanceMetrics.objects.filter(supplier=supplier).exists()
        )
    
    def test_purchase_order_workflow(self):
        """Test creating purchase order with workflow."""
        supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='manufacturer',
            phone_number='09123456789',
            created_by=self.user
        )
        
        items = [
            {
                'name': 'Gold Ring',
                'quantity': 10,
                'unit_price': Decimal('500000.00'),
                'weight_grams': Decimal('5.5'),
                'karat': 18
            },
            {
                'name': 'Silver Necklace',
                'quantity': 5,
                'unit_price': Decimal('200000.00')
            }
        ]
        
        order_details = {
            'order_date': date.today(),
            'expected_delivery_date': date.today() + timedelta(days=7),
            'priority': 'high',
            'payment_terms': 'Net 15',
            'notes': 'Urgent order'
        }
        
        delivery_details = {
            'scheduled_date': date.today() + timedelta(days=7),
            'delivery_method': 'courier',
            'contact_person': 'Jane Doe',
            'contact_phone': '09987654321'
        }
        
        po, delivery = SupplierManagementService.create_purchase_order_workflow(
            supplier=supplier,
            items=items,
            order_details=order_details,
            delivery_details=delivery_details
        )
        
        self.assertEqual(po.supplier, supplier)
        self.assertEqual(po.priority, 'high')
        self.assertEqual(po.items.count(), 2)
        self.assertIsNotNone(delivery)
        self.assertEqual(delivery.delivery_method, 'courier')
    
    def test_supplier_payment(self):
        """Test processing supplier payment."""
        supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='manufacturer',
            phone_number='09123456789',
            created_by=self.user
        )
        
        payment = SupplierManagementService.process_supplier_payment(
            supplier=supplier,
            amount=Decimal('1000000.00'),
            payment_method='bank_transfer',
            reference_number='TXN123456',
            description='Payment for order PO-001'
        )
        
        self.assertEqual(payment.supplier, supplier)
        self.assertEqual(payment.amount, Decimal('1000000.00'))
        self.assertEqual(payment.payment_method, 'bank_transfer')
        self.assertEqual(payment.status, 'pending')
    
    def test_get_supplier_performance_report(self):
        """Test getting supplier performance report."""
        supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='manufacturer',
            phone_number='09123456789',
            created_by=self.user
        )
        
        report = SupplierManagementService.get_supplier_performance_report(supplier)
        
        self.assertEqual(report['supplier'], supplier)
        self.assertIn('metrics', report)
        self.assertIn('recent_orders', report)
        self.assertIn('pending_deliveries', report)
        self.assertIn('recent_payments', report)


class SupplierAPITest(APITestCase):
    """Test supplier management API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
        self.client.force_authenticate(user=self.user)
        
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            persian_name='تامین کننده تست',
            supplier_type='manufacturer',
            phone_number='09123456789',
            created_by=self.user
        )
    
    def test_create_supplier_api(self):
        """Test creating supplier via API."""
        data = {
            'name': 'New Supplier',
            'persian_name': 'تامین کننده جدید',
            'supplier_type': 'wholesaler',
            'phone_number': '09987654321',
            'email': 'new@supplier.com',
            'contact_person': 'Ali Ahmadi',
            'payment_terms': 'Net 30',
            'credit_limit': '5000000.00'
        }
        
        response = self.client.post('/api/suppliers/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        supplier = Supplier.objects.get(name='New Supplier')
        self.assertEqual(supplier.persian_name, 'تامین کننده جدید')
        self.assertEqual(supplier.supplier_type, 'wholesaler')
    
    def test_get_supplier_performance_report_api(self):
        """Test getting supplier performance report via API."""
        response = self.client.get(f'/api/suppliers/{self.supplier.id}/performance_report/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('supplier', data)
        self.assertIn('metrics', data)
    
    def test_toggle_supplier_preferred_api(self):
        """Test toggling supplier preferred status via API."""
        response = self.client.post(f'/api/suppliers/{self.supplier.id}/toggle_preferred/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.supplier.refresh_from_db()
        self.assertTrue(self.supplier.is_preferred)
    
    def test_create_purchase_order_api(self):
        """Test creating purchase order via API."""
        data = {
            'supplier_id': self.supplier.id,
            'order_date': date.today().isoformat(),
            'expected_delivery_date': (date.today() + timedelta(days=7)).isoformat(),
            'priority': 'normal',
            'items': [
                {
                    'name': 'Gold Ring',
                    'quantity': 5,
                    'unit_price': '500000.00',
                    'weight_grams': '5.5',
                    'karat': 18
                }
            ]
        }
        
        response = self.client.post('/api/purchase-orders/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        po = PurchaseOrder.objects.get(supplier=self.supplier)
        self.assertEqual(po.items.count(), 1)
        self.assertEqual(po.priority, 'normal')
    
    def test_create_supplier_payment_api(self):
        """Test creating supplier payment via API."""
        data = {
            'supplier_id': self.supplier.id,
            'amount': '1000000.00',
            'payment_date': date.today().isoformat(),
            'payment_method': 'bank_transfer',
            'reference_number': 'TXN123456',
            'description': 'Test payment'
        }
        
        response = self.client.post('/api/supplier-payments/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        payment = SupplierPayment.objects.get(supplier=self.supplier)
        self.assertEqual(payment.amount, Decimal('1000000.00'))
        self.assertEqual(payment.payment_method, 'bank_transfer')


class DeliveryTrackingTest(TestCase):
    """Test delivery tracking functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
        
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='manufacturer',
            phone_number='09123456789',
            created_by=self.user
        )
        
        self.po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            order_date=date.today(),
            created_by=self.user
        )
    
    def test_delivery_tracking(self):
        """Test delivery tracking functionality."""
        delivery = DeliverySchedule.objects.create(
            purchase_order=self.po,
            scheduled_date=date.today() + timedelta(days=3),
            delivery_method='courier',
            delivery_address='Test Address',
            created_by=self.user
        )
        
        # Test updating delivery tracking
        updated_delivery = SupplierManagementService.update_delivery_tracking(
            delivery_schedule=delivery,
            status='in_transit',
            tracking_number='TRK123456',
            notes='Package picked up'
        )
        
        self.assertEqual(updated_delivery.status, 'in_transit')
        self.assertEqual(updated_delivery.tracking_number, 'TRK123456')
        self.assertIn('Package picked up', updated_delivery.notes)


if __name__ == '__main__':
    pytest.main([__file__])