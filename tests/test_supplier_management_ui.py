#!/usr/bin/env python
"""
Test supplier management UI workflows and purchase order interface.
"""
import os
import sys
import django
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
django.setup()

from zargar.customers.models import Supplier, PurchaseOrder, PurchaseOrderItem
from zargar.customers.supplier_services import SupplierPayment, DeliverySchedule, SupplierPerformanceMetrics
from zargar.tenants.models import Tenant, Domain

User = get_user_model()


class SupplierManagementUITest(TestCase):
    """Test supplier management UI workflows and purchase order interface."""
    
    def setUp(self):
        """Set up test data."""
        # Create tenant
        self.tenant = Tenant.objects.create(
            name="Test Jewelry Shop",
            schema_name="test_shop",
            owner_name="Test Owner",
            owner_email="test@example.com"
        )
        
        # Create domain
        self.domain = Domain.objects.create(
            domain="testshop.zargar.com",
            tenant=self.tenant,
            is_primary=True
        )
        
        # Create user in tenant context
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            self.user = User.objects.create_user(
                username="testuser",
                email="test@example.com",
                password="testpass123"
            )
        
            # Create test suppliers in tenant context
            self.supplier1 = Supplier.objects.create(
                name="Gold Supplier Co",
                persian_name="شرکت تامین طلا",
                supplier_type="gold_supplier",
                contact_person="احمد محمدی",
                phone_number="09123456789",
                email="info@goldsupplier.com",
                payment_terms="30 روزه",
                is_active=True,
                is_preferred=True
            )
            
            self.supplier2 = Supplier.objects.create(
                name="Gemstone Dealer",
                persian_name="فروشنده سنگ قیمتی",
                supplier_type="gemstone_dealer",
                contact_person="فاطمه احمدی",
                phone_number="09987654321",
                email="info@gemstones.com",
                payment_terms="نقدی",
                is_active=True,
                is_preferred=False
            )
        
            # Create test purchase orders in tenant context
            self.purchase_order1 = PurchaseOrder.objects.create(
                supplier=self.supplier1,
                order_date=date.today(),
                expected_delivery_date=date.today() + timedelta(days=7),
                status='draft',
                priority='normal',
                subtotal=Decimal('5000000'),
                total_amount=Decimal('5000000'),
                payment_terms="30 روزه",
                notes="سفارش تست"
            )
            
            # Create purchase order items
            self.po_item1 = PurchaseOrderItem.objects.create(
                purchase_order=self.purchase_order1,
                item_name="طلای 18 عیار",
                quantity_ordered=10,
                unit_price=Decimal('500000'),
                weight_grams=Decimal('100.5'),
                karat=18
            )
        
        # Setup client
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")
    
    def test_supplier_dashboard_view(self):
        """Test supplier management dashboard view."""
        url = reverse('customers:supplier_dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "مدیریت تامین‌کنندگان")
        self.assertContains(response, self.supplier1.persian_name)
        self.assertContains(response, "کل تامین‌کنندگان")
        self.assertContains(response, "تامین‌کنندگان ترجیحی")
    
    def test_supplier_list_view(self):
        """Test supplier list view with search and filtering."""
        url = reverse('customers:supplier_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "لیست تامین‌کنندگان")
        self.assertContains(response, self.supplier1.persian_name)
        self.assertContains(response, self.supplier2.persian_name)
    
    def test_supplier_list_search(self):
        """Test supplier list search functionality."""
        url = reverse('customers:supplier_list')
        response = self.client.get(url, {'search': 'طلا'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.supplier1.persian_name)
        self.assertNotContains(response, self.supplier2.persian_name)
    
    def test_supplier_list_filter_by_type(self):
        """Test supplier list filtering by type."""
        url = reverse('customers:supplier_list')
        response = self.client.get(url, {'supplier_type': 'gold_supplier'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.supplier1.persian_name)
        self.assertNotContains(response, self.supplier2.persian_name)
    
    def test_supplier_list_filter_by_status(self):
        """Test supplier list filtering by status."""
        url = reverse('customers:supplier_list')
        response = self.client.get(url, {'status': 'preferred'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.supplier1.persian_name)
        self.assertNotContains(response, self.supplier2.persian_name)
    
    def test_supplier_create_view(self):
        """Test supplier creation form."""
        url = reverse('customers:supplier_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "تامین‌کننده جدید")
        self.assertContains(response, "نام تامین‌کننده")
        self.assertContains(response, "نوع تامین‌کننده")
    
    def test_supplier_create_post(self):
        """Test supplier creation via POST."""
        url = reverse('customers:supplier_create')
        data = {
            'name': 'New Supplier',
            'persian_name': 'تامین‌کننده جدید',
            'supplier_type': 'manufacturer',
            'contact_person': 'علی رضایی',
            'phone_number': '09111111111',
            'email': 'new@supplier.com',
            'payment_terms': 'نقدی',
            'is_preferred': False
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        
        # Check if supplier was created
        supplier = Supplier.objects.filter(name='New Supplier').first()
        self.assertIsNotNone(supplier)
        self.assertEqual(supplier.persian_name, 'تامین‌کننده جدید')
        self.assertEqual(supplier.tenant, self.tenant)
    
    def test_supplier_detail_view(self):
        """Test supplier detail view."""
        url = reverse('customers:supplier_detail', kwargs={'pk': self.supplier1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.supplier1.persian_name)
        self.assertContains(response, self.supplier1.contact_person)
        self.assertContains(response, "سفارشات خرید")
        self.assertContains(response, "عملکرد تامین‌کننده")
    
    def test_supplier_update_view(self):
        """Test supplier update form."""
        url = reverse('customers:supplier_update', kwargs={'pk': self.supplier1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ویرایش تامین‌کننده")
        self.assertContains(response, self.supplier1.name)
    
    def test_supplier_update_post(self):
        """Test supplier update via POST."""
        url = reverse('customers:supplier_update', kwargs={'pk': self.supplier1.pk})
        data = {
            'name': self.supplier1.name,
            'persian_name': 'نام جدید',
            'supplier_type': self.supplier1.supplier_type,
            'contact_person': self.supplier1.contact_person,
            'phone_number': self.supplier1.phone_number,
            'email': self.supplier1.email,
            'payment_terms': 'شرایط جدید',
            'is_active': True,
            'is_preferred': True
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 302)  # Redirect after successful update
        
        # Check if supplier was updated
        supplier = Supplier.objects.get(pk=self.supplier1.pk)
        self.assertEqual(supplier.persian_name, 'نام جدید')
        self.assertEqual(supplier.payment_terms, 'شرایط جدید')
    
    def test_purchase_order_list_view(self):
        """Test purchase order list view."""
        url = reverse('customers:purchase_order_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "سفارشات خرید")
        self.assertContains(response, self.purchase_order1.order_number)
        self.assertContains(response, self.supplier1.persian_name)
    
    def test_purchase_order_list_filter_by_supplier(self):
        """Test purchase order list filtering by supplier."""
        url = reverse('customers:purchase_order_list')
        response = self.client.get(url, {'supplier': self.supplier1.pk})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.purchase_order1.order_number)
    
    def test_purchase_order_list_filter_by_status(self):
        """Test purchase order list filtering by status."""
        url = reverse('customers:purchase_order_list')
        response = self.client.get(url, {'status': 'draft'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.purchase_order1.order_number)
    
    def test_purchase_order_create_view(self):
        """Test purchase order creation form."""
        url = reverse('customers:purchase_order_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "سفارش خرید جدید")
        self.assertContains(response, "تامین‌کننده")
        self.assertContains(response, "تاریخ سفارش")
    
    def test_purchase_order_create_post(self):
        """Test purchase order creation via POST."""
        url = reverse('customers:purchase_order_create')
        data = {
            'supplier': self.supplier1.pk,
            'order_date': date.today(),
            'expected_delivery_date': date.today() + timedelta(days=10),
            'priority': 'normal',
            'payment_terms': '30 روزه',
            'notes': 'سفارش تست جدید'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        
        # Check if purchase order was created
        po = PurchaseOrder.objects.filter(notes='سفارش تست جدید').first()
        self.assertIsNotNone(po)
        self.assertEqual(po.supplier, self.supplier1)
    
    def test_purchase_order_detail_view(self):
        """Test purchase order detail view."""
        url = reverse('customers:purchase_order_detail', kwargs={'pk': self.purchase_order1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.purchase_order1.order_number)
        self.assertContains(response, self.supplier1.persian_name)
        self.assertContains(response, "اقلام سفارش")
        self.assertContains(response, self.po_item1.item_name)
    
    def test_purchase_order_update_view(self):
        """Test purchase order update form (only for draft orders)."""
        url = reverse('customers:purchase_order_update', kwargs={'pk': self.purchase_order1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ویرایش سفارش خرید")
        self.assertContains(response, self.purchase_order1.order_number)
    
    def test_supplier_performance_report_view(self):
        """Test supplier performance report view."""
        url = reverse('customers:supplier_performance')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "گزارش عملکرد تامین‌کنندگان")
        self.assertContains(response, "کل سفارشات")
        self.assertContains(response, "تکمیل شده")
    
    def test_supplier_performance_report_with_date_filter(self):
        """Test supplier performance report with date filtering."""
        url = reverse('customers:supplier_performance')
        date_from = date.today() - timedelta(days=30)
        date_to = date.today()
        
        response = self.client.get(url, {
            'date_from': date_from.strftime('%Y-%m-%d'),
            'date_to': date_to.strftime('%Y-%m-%d')
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "گزارش عملکرد تامین‌کنندگان")
    
    def test_supplier_ajax_toggle_preferred(self):
        """Test AJAX toggle preferred supplier status."""
        url = reverse('customers:supplier_ajax')
        data = {
            'action': 'toggle_preferred',
            'supplier_id': self.supplier2.pk
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 200)
        
        # Parse JSON response
        json_response = json.loads(response.content)
        self.assertTrue(json_response['success'])
        self.assertIn('message', json_response)
        
        # Check if supplier status was updated
        supplier = Supplier.objects.get(pk=self.supplier2.pk)
        self.assertTrue(supplier.is_preferred)
    
    def test_supplier_ajax_toggle_active(self):
        """Test AJAX toggle active supplier status."""
        url = reverse('customers:supplier_ajax')
        data = {
            'action': 'toggle_active',
            'supplier_id': self.supplier1.pk
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 200)
        
        # Parse JSON response
        json_response = json.loads(response.content)
        self.assertTrue(json_response['success'])
        
        # Check if supplier status was updated
        supplier = Supplier.objects.get(pk=self.supplier1.pk)
        self.assertFalse(supplier.is_active)
    
    def test_supplier_ajax_update_payment_terms(self):
        """Test AJAX update payment terms."""
        url = reverse('customers:supplier_ajax')
        data = {
            'action': 'update_payment_terms',
            'supplier_id': self.supplier1.pk,
            'payment_terms': 'شرایط جدید'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 200)
        
        # Parse JSON response
        json_response = json.loads(response.content)
        self.assertTrue(json_response['success'])
        
        # Check if payment terms were updated
        supplier = Supplier.objects.get(pk=self.supplier1.pk)
        self.assertEqual(supplier.payment_terms, 'شرایط جدید')
    
    def test_supplier_ajax_send_purchase_order(self):
        """Test AJAX send purchase order."""
        url = reverse('customers:supplier_ajax')
        data = {
            'action': 'send_purchase_order',
            'order_id': self.purchase_order1.pk
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 200)
        
        # Parse JSON response
        json_response = json.loads(response.content)
        self.assertTrue(json_response['success'])
        
        # Check if order status was updated
        po = PurchaseOrder.objects.get(pk=self.purchase_order1.pk)
        self.assertEqual(po.status, 'sent')
    
    def test_supplier_ajax_cancel_order(self):
        """Test AJAX cancel purchase order."""
        url = reverse('customers:supplier_ajax')
        data = {
            'action': 'cancel_order',
            'order_id': self.purchase_order1.pk,
            'reason': 'تست لغو'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 200)
        
        # Parse JSON response
        json_response = json.loads(response.content)
        self.assertTrue(json_response['success'])
        
        # Check if order was cancelled
        po = PurchaseOrder.objects.get(pk=self.purchase_order1.pk)
        self.assertEqual(po.status, 'cancelled')
        self.assertIn('تست لغو', po.internal_notes)
    
    def test_supplier_ajax_receive_items(self):
        """Test AJAX receive purchase order items."""
        url = reverse('customers:supplier_ajax')
        item_quantities = {str(self.po_item1.pk): 5}
        data = {
            'action': 'receive_items',
            'order_id': self.purchase_order1.pk,
            'item_quantities': json.dumps(item_quantities)
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 200)
        
        # Parse JSON response
        json_response = json.loads(response.content)
        self.assertTrue(json_response['success'])
        
        # Check if item quantity was updated
        item = PurchaseOrderItem.objects.get(pk=self.po_item1.pk)
        self.assertEqual(item.quantity_received, 5)
    
    def test_supplier_form_validation(self):
        """Test supplier form validation."""
        url = reverse('customers:supplier_create')
        
        # Test with missing required fields
        data = {
            'name': '',  # Required field missing
            'supplier_type': 'manufacturer',
            'phone_number': '09123456789'
        }
        
        response = self.client.post(url, data)
        
        # Should not redirect (form has errors)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "این فیلد الزامی است")
    
    def test_purchase_order_form_validation(self):
        """Test purchase order form validation."""
        url = reverse('customers:purchase_order_create')
        
        # Test with missing required fields
        data = {
            'supplier': '',  # Required field missing
            'order_date': date.today()
        }
        
        response = self.client.post(url, data)
        
        # Should not redirect (form has errors)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'supplier', 'این فیلد الزامی است.')
    
    def test_supplier_dashboard_metrics(self):
        """Test supplier dashboard metrics calculation."""
        url = reverse('customers:supplier_dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check context data
        context = response.context
        self.assertEqual(context['total_suppliers'], 2)
        self.assertEqual(context['active_suppliers'], 2)
        self.assertEqual(context['preferred_suppliers'], 1)
    
    def test_supplier_performance_metrics_calculation(self):
        """Test supplier performance metrics calculation."""
        # Create performance metrics
        metrics = SupplierPerformanceMetrics.objects.create(
            supplier=self.supplier1
        )
        
        # Update metrics
        metrics.update_metrics()
        
        # Check calculated values
        self.assertEqual(metrics.total_order_value, 0)  # No completed orders yet
        self.assertEqual(metrics.on_time_delivery_rate, 0)  # No deliveries yet
    
    def test_unauthorized_access(self):
        """Test unauthorized access to supplier management."""
        # Logout user
        self.client.logout()
        
        url = reverse('customers:supplier_dashboard')
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_cross_tenant_access_prevention(self):
        """Test that users cannot access other tenants' suppliers."""
        # Create another tenant and user
        other_tenant = Tenant.objects.create(
            name="Other Shop",
            schema_name="other_shop",
            owner_name="Other Owner",
            owner_email="other@example.com"
        )
        
        other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="testpass123",
            tenant=other_tenant
        )
        
        # Login as other user
        self.client.logout()
        self.client.login(username="otheruser", password="testpass123")
        
        # Try to access supplier from different tenant
        url = reverse('customers:supplier_detail', kwargs={'pk': self.supplier1.pk})
        response = self.client.get(url)
        
        # Should return 404 (not found) due to tenant filtering
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    import unittest
    unittest.main()