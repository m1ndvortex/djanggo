"""
Test layaway UI workflows and payment management interface.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from zargar.tenants.models import Tenant, Domain
from zargar.customers.models import Customer
from zargar.jewelry.models import JewelryItem, Category
from zargar.customers.layaway_models import LayawayPlan, LayawayPayment


User = get_user_model()


class LayawayUIWorkflowTest(TenantTestCase):
    """Test layaway UI workflows and payment management interface."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create tenant
        cls.tenant = Tenant.objects.create(
            name="Test Jewelry Shop",
            schema_name="test_jewelry",
            is_active=True
        )
        
        # Create domain
        cls.domain = Domain.objects.create(
            domain="testjewelry.zargar.local",
            tenant=cls.tenant,
            is_primary=True
        )
    
    def setUp(self):
        super().setUp()
        
        # Use tenant client
        self.client = TenantClient(self.tenant)
        
        # Create test user
        self.user = User.objects.create_user(
            username='testowner',
            email='owner@test.com',
            password='testpass123',
            role='owner'
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            persian_first_name='علی',
            persian_last_name='احمدی',
            first_name='Ali',
            last_name='Ahmadi',
            phone_number='09123456789',
            email='ali@test.com',
            is_active=True
        )
        
        # Create jewelry category
        self.category = Category.objects.create(
            name='انگشتر',
            name_english='Ring'
        )
        
        # Create jewelry item
        self.jewelry_item = JewelryItem.objects.create(
            name='انگشتر طلای ۱۸ عیار',
            sku='RING-001',
            category=self.category,
            weight_grams=Decimal('5.5'),
            karat=18,
            selling_price=Decimal('15000000'),  # 15 million Toman
            status='in_stock'
        )
        
        # Login user
        self.client.login(username='testowner', password='testpass123')
    
    def test_layaway_dashboard_access(self):
        """Test layaway dashboard page loads correctly."""
        url = reverse('customers:layaway_dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مدیریت طلای قرضی')
        self.assertContains(response, 'قرارداد جدید')
        self.assertContains(response, 'یادآوری‌ها')
        self.assertContains(response, 'گزارشات')
    
    def test_layaway_plan_creation_form(self):
        """Test layaway plan creation form displays correctly."""
        url = reverse('customers:layaway_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ایجاد قرارداد طلای قرضی جدید')
        self.assertContains(response, 'اطلاعات مشتری و کالا')
        self.assertContains(response, 'شرایط مالی')
        self.assertContains(response, 'اطلاعات تکمیلی')
        
        # Check form fields are present
        self.assertContains(response, 'name="customer"')
        self.assertContains(response, 'name="jewelry_item"')
        self.assertContains(response, 'name="total_amount"')
        self.assertContains(response, 'name="down_payment"')
        self.assertContains(response, 'name="payment_frequency"')
        self.assertContains(response, 'name="number_of_payments"')
    
    def test_layaway_plan_creation_workflow(self):
        """Test complete layaway plan creation workflow."""
        url = reverse('customers:layaway_create')
        
        # Test form submission
        form_data = {
            'customer': self.customer.id,
            'jewelry_item': self.jewelry_item.id,
            'total_amount': '15000000',  # 15 million Toman
            'down_payment': '3000000',   # 3 million Toman
            'payment_frequency': 'monthly',
            'number_of_payments': '12',
            'start_date': date.today().strftime('%Y-%m-%d'),
            'grace_period_days': '7',
            'notes': 'تست قرارداد طلای قرضی'
        }
        
        response = self.client.post(url, form_data)
        
        # Should redirect to plan detail page
        self.assertEqual(response.status_code, 302)
        
        # Check plan was created
        plan = LayawayPlan.objects.filter(customer=self.customer).first()
        self.assertIsNotNone(plan)
        self.assertEqual(plan.total_amount, Decimal('15000000'))
        self.assertEqual(plan.down_payment, Decimal('3000000'))
        self.assertEqual(plan.payment_frequency, 'monthly')
        self.assertEqual(plan.number_of_payments, 12)
        self.assertEqual(plan.status, 'active')
    
    def test_layaway_plan_detail_view(self):
        """Test layaway plan detail view displays correctly."""
        # Create a layaway plan
        plan = LayawayPlan.objects.create(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('15000000'),
            down_payment=Decimal('3000000'),
            installment_amount=Decimal('1000000'),
            payment_frequency='monthly',
            number_of_payments=12,
            start_date=date.today(),
            expected_completion_date=date.today() + timedelta(days=365),
            status='active',
            total_paid=Decimal('3000000')  # Down payment
        )
        
        url = reverse('customers:layaway_detail', kwargs={'pk': plan.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'قرارداد {plan.plan_number}')
        self.assertContains(response, 'اطلاعات قرارداد')
        self.assertContains(response, 'خلاصه مالی')
        self.assertContains(response, 'برنامه پرداخت')
        self.assertContains(response, 'تاریخچه پرداخت‌ها')
        
        # Check financial information
        self.assertContains(response, '15,000,000')  # Total amount
        self.assertContains(response, '3,000,000')   # Paid amount
        self.assertContains(response, '12,000,000')  # Remaining balance
        
        # Check action buttons
        self.assertContains(response, 'ثبت پرداخت')
        self.assertContains(response, 'تعلیق قرارداد')
        self.assertContains(response, 'لغو قرارداد')
    
    def test_layaway_payment_processing(self):
        """Test layaway payment processing workflow."""
        # Create a layaway plan
        plan = LayawayPlan.objects.create(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('15000000'),
            down_payment=Decimal('3000000'),
            installment_amount=Decimal('1000000'),
            payment_frequency='monthly',
            number_of_payments=12,
            start_date=date.today(),
            expected_completion_date=date.today() + timedelta(days=365),
            status='active',
            total_paid=Decimal('3000000')
        )
        
        # Generate payment schedule
        plan.generate_payment_schedule()
        
        url = reverse('customers:layaway_detail', kwargs={'pk': plan.pk})
        
        # Test payment processing
        payment_data = {
            'action': 'process_payment',
            'amount': '1000000',  # 1 million Toman
            'payment_method': 'cash',
            'reference_number': 'TEST-001',
            'notes': 'تست پرداخت قسط'
        }
        
        response = self.client.post(url, payment_data)
        
        # Should redirect back to detail page
        self.assertEqual(response.status_code, 302)
        
        # Check payment was recorded
        payment = LayawayPayment.objects.filter(layaway_plan=plan).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, Decimal('1000000'))
        self.assertEqual(payment.payment_method, 'cash')
        self.assertEqual(payment.reference_number, 'TEST-001')
        
        # Check plan totals were updated
        plan.refresh_from_db()
        self.assertEqual(plan.total_paid, Decimal('4000000'))  # 3M + 1M
        self.assertEqual(plan.remaining_balance, Decimal('11000000'))  # 15M - 4M
    
    def test_layaway_plan_list_view(self):
        """Test layaway plan list view with filtering."""
        # Create multiple layaway plans
        plan1 = LayawayPlan.objects.create(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('10000000'),
            down_payment=Decimal('2000000'),
            installment_amount=Decimal('800000'),
            payment_frequency='monthly',
            number_of_payments=10,
            start_date=date.today(),
            expected_completion_date=date.today() + timedelta(days=300),
            status='active',
            total_paid=Decimal('2000000')
        )
        
        plan2 = LayawayPlan.objects.create(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('8000000'),
            down_payment=Decimal('8000000'),
            installment_amount=Decimal('0'),
            payment_frequency='monthly',
            number_of_payments=1,
            start_date=date.today() - timedelta(days=30),
            expected_completion_date=date.today() - timedelta(days=30),
            status='completed',
            total_paid=Decimal('8000000'),
            actual_completion_date=date.today() - timedelta(days=30)
        )
        
        url = reverse('customers:layaway_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'لیست قراردادهای طلای قرضی')
        self.assertContains(response, plan1.plan_number)
        self.assertContains(response, plan2.plan_number)
        
        # Test filtering by status
        response = self.client.get(url, {'status': 'active'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, plan1.plan_number)
        self.assertNotContains(response, plan2.plan_number)
        
        # Test filtering by customer
        response = self.client.get(url, {'customer': self.customer.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, plan1.plan_number)
        self.assertContains(response, plan2.plan_number)
    
    def test_layaway_reminders_management(self):
        """Test layaway reminders management interface."""
        # Create a layaway plan
        plan = LayawayPlan.objects.create(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('15000000'),
            down_payment=Decimal('3000000'),
            installment_amount=Decimal('1000000'),
            payment_frequency='monthly',
            number_of_payments=12,
            start_date=date.today(),
            expected_completion_date=date.today() + timedelta(days=365),
            status='active',
            total_paid=Decimal('3000000')
        )
        
        url = reverse('customers:layaway_reminders')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مدیریت یادآوری‌های طلای قرضی')
        self.assertContains(response, 'عملیات سریع')
        self.assertContains(response, 'یادآوری‌های آتی')
        self.assertContains(response, 'یادآوری‌های اخیر')
        self.assertContains(response, 'یادآوری سفارشی')
    
    def test_layaway_ajax_endpoints(self):
        """Test AJAX endpoints for dynamic functionality."""
        # Test jewelry item details endpoint
        url = reverse('customers:layaway_ajax')
        
        response = self.client.post(url, {
            'action': 'get_jewelry_item_details',
            'item_id': self.jewelry_item.id
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['item']['name'], self.jewelry_item.name)
        self.assertEqual(data['item']['sku'], self.jewelry_item.sku)
        self.assertEqual(float(data['item']['selling_price']), float(self.jewelry_item.selling_price))
        
        # Test installment calculation endpoint
        response = self.client.post(url, {
            'action': 'calculate_installments',
            'total_amount': '15000000',
            'down_payment': '3000000',
            'number_of_payments': '12',
            'payment_frequency': 'monthly'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(float(data['calculation']['remaining_amount']), 12000000.0)
        self.assertEqual(float(data['calculation']['installment_amount']), 1000000.0)
    
    def test_layaway_plan_status_changes(self):
        """Test layaway plan status change workflows."""
        # Create a layaway plan
        plan = LayawayPlan.objects.create(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('15000000'),
            down_payment=Decimal('3000000'),
            installment_amount=Decimal('1000000'),
            payment_frequency='monthly',
            number_of_payments=12,
            start_date=date.today(),
            expected_completion_date=date.today() + timedelta(days=365),
            status='active',
            total_paid=Decimal('3000000')
        )
        
        url = reverse('customers:layaway_detail', kwargs={'pk': plan.pk})
        
        # Test putting plan on hold
        response = self.client.post(url, {
            'action': 'put_on_hold',
            'hold_reason': 'مشکل موقت مشتری'
        })
        
        self.assertEqual(response.status_code, 302)
        plan.refresh_from_db()
        self.assertEqual(plan.status, 'on_hold')
        
        # Test reactivating plan
        response = self.client.post(url, {
            'action': 'reactivate_plan',
            'reactivate_reason': 'مشکل برطرف شد'
        })
        
        self.assertEqual(response.status_code, 302)
        plan.refresh_from_db()
        self.assertEqual(plan.status, 'active')
        
        # Test cancelling plan
        response = self.client.post(url, {
            'action': 'cancel_plan',
            'cancel_reason': 'درخواست مشتری',
            'refund_percentage': '90'
        })
        
        self.assertEqual(response.status_code, 302)
        plan.refresh_from_db()
        self.assertEqual(plan.status, 'cancelled')
    
    def test_persian_ui_elements(self):
        """Test Persian UI elements and RTL layout."""
        url = reverse('customers:layaway_dashboard')
        response = self.client.get(url)
        
        # Check Persian text is present
        self.assertContains(response, 'مدیریت طلای قرضی')
        self.assertContains(response, 'قرارداد فعال')
        self.assertContains(response, 'ارزش کل')
        self.assertContains(response, 'مانده بدهی')
        self.assertContains(response, 'معوقات')
        
        # Check RTL layout
        self.assertContains(response, 'base_rtl.html')
        self.assertContains(response, 'dir="rtl"')
        
        # Check Persian CSS classes
        self.assertContains(response, 'layaway-dashboard.css')
    
    def test_theme_support(self):
        """Test dual theme support (light/dark mode)."""
        url = reverse('customers:layaway_dashboard')
        response = self.client.get(url)
        
        # Check theme-aware CSS is included
        self.assertContains(response, 'layaway-dashboard.css')
        
        # Check theme toggle functionality
        self.assertContains(response, 'data-theme')
        
        # Check cybersecurity theme elements for dark mode
        content = response.content.decode('utf-8')
        self.assertIn('[data-theme="dark"]', content)


class LayawayUIResponsivenessTest(TenantTestCase):
    """Test layaway UI responsiveness and mobile compatibility."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create tenant
        cls.tenant = Tenant.objects.create(
            name="Test Mobile Shop",
            schema_name="test_mobile",
            is_active=True
        )
        
        # Create domain
        cls.domain = Domain.objects.create(
            domain="testmobile.zargar.local",
            tenant=cls.tenant,
            is_primary=True
        )
    
    def setUp(self):
        super().setUp()
        
        # Use tenant client
        self.client = TenantClient(self.tenant)
        
        # Create test user
        self.user = User.objects.create_user(
            username='mobileuser',
            email='mobile@test.com',
            password='testpass123',
            role='owner'
        )
        
        # Login user
        self.client.login(username='mobileuser', password='testpass123')
    
    def test_mobile_responsive_design(self):
        """Test mobile responsive design elements."""
        url = reverse('customers:layaway_dashboard')
        
        # Simulate mobile user agent
        response = self.client.get(url, HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)')
        
        self.assertEqual(response.status_code, 200)
        
        # Check responsive CSS classes
        self.assertContains(response, 'col-md-')
        self.assertContains(response, 'col-lg-')
        
        # Check mobile-friendly elements
        content = response.content.decode('utf-8')
        self.assertIn('@media (max-width: 768px)', content)
    
    def test_touch_friendly_interface(self):
        """Test touch-friendly interface elements."""
        url = reverse('customers:layaway_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check for touch-friendly button sizes
        self.assertContains(response, 'btn-lg')
        self.assertContains(response, 'btn-block')
        
        # Check for large form controls
        self.assertContains(response, 'form-control')


if __name__ == '__main__':
    pytest.main([__file__])