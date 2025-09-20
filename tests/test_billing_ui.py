"""
Tests for billing and subscription management UI functionality.
Tests Persian formatting, form validation, and billing workflows.
"""

import pytest
import django
from django.conf import settings
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import jdatetime

# Configure Django settings for testing
if not settings.configured:
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

from zargar.tenants.admin_models import SuperAdmin, SubscriptionPlan, TenantInvoice, BillingCycle
from zargar.tenants.models import Tenant
from zargar.tenants.billing_services import SubscriptionManager, InvoiceGenerator, BillingWorkflow


class BillingDashboardUITest(TestCase):
    """Test billing dashboard UI functionality."""
    
    def setUp(self):
        self.client = Client()
        self.superadmin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
        self.client.force_login(self.superadmin)
        
        # Create test subscription plans
        self.basic_plan = SubscriptionPlan.objects.create(
            name='Basic Plan',
            name_persian='پلن پایه',
            plan_type='basic',
            monthly_price_toman=Decimal('500000'),
            yearly_price_toman=Decimal('5000000'),
            max_users=2,
            max_inventory_items=1000,
            max_customers=500,
            max_monthly_transactions=1000,
            max_storage_gb=5,
            features={
                'pos_system': True,
                'inventory_management': True,
                'customer_management': True,
                'accounting_system': False,
                'gold_installment': False,
            },
            is_active=True
        )
        
        # Create test tenant
        self.tenant = Tenant.objects.create(
            name='Test Jewelry Shop',
            domain_url='testshop',
            owner_email='owner@testshop.com',
            subscription_plan_fk=self.basic_plan,
            is_active=True
        )
        
        # Create test invoice
        self.invoice = TenantInvoice.objects.create(
            tenant=self.tenant,
            subscription_plan=self.basic_plan,
            issue_date_shamsi=jdatetime.date.today().togregorian(),
            due_date_shamsi=(jdatetime.date.today() + jdatetime.timedelta(days=30)).togregorian(),
            billing_period_start=jdatetime.date.today().togregorian(),
            billing_period_end=jdatetime.date.today().togregorian(),
            subtotal_toman=self.basic_plan.monthly_price_toman,
            created_by=self.superadmin,
            line_items=[{
                'description': 'اشتراک ماهانه - پلن پایه',
                'quantity': 1,
                'unit_price': str(self.basic_plan.monthly_price_toman),
                'total_price': str(self.basic_plan.monthly_price_toman)
            }]
        )
    
    def test_billing_dashboard_loads(self):
        """Test that billing dashboard loads successfully."""
        url = reverse('core:tenants:billing:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'داشبورد مالی')
        self.assertContains(response, 'درآمد ماه جاری')
        self.assertContains(response, 'کل فاکتورها')
    
    def test_dashboard_statistics_display(self):
        """Test that dashboard displays correct statistics."""
        url = reverse('core:tenants:billing:dashboard')
        response = self.client.get(url)
        
        # Check that statistics are displayed
        self.assertContains(response, 'persian-numbers')
        self.assertContains(response, 'تومان')
        
        # Check that plan distribution is shown
        self.assertContains(response, self.basic_plan.name_persian)
    
    def test_dashboard_recent_invoices(self):
        """Test that recent invoices are displayed."""
        url = reverse('core:tenants:billing:dashboard')
        response = self.client.get(url)
        
        self.assertContains(response, self.invoice.invoice_number)
        self.assertContains(response, self.tenant.name)
    
    def test_dashboard_persian_formatting(self):
        """Test Persian number formatting in dashboard."""
        url = reverse('core:tenants:billing:dashboard')
        response = self.client.get(url)
        
        # Check for Persian number class
        self.assertContains(response, 'persian-numbers')
        
        # Check for Persian currency formatting
        self.assertContains(response, 'تومان')


class SubscriptionPlanUITest(TestCase):
    """Test subscription plan management UI."""
    
    def setUp(self):
        self.client = Client()
        self.superadmin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
        self.client.force_login(self.superadmin)
    
    def test_subscription_plans_list(self):
        """Test subscription plans list view."""
        # Create test plan
        plan = SubscriptionPlan.objects.create(
            name='Test Plan',
            name_persian='پلن تست',
            plan_type='basic',
            monthly_price_toman=Decimal('1000000'),
            max_users=5,
            max_inventory_items=2000,
            max_customers=1000,
            max_monthly_transactions=2000,
            max_storage_gb=10,
            features={'pos_system': True},
            is_active=True
        )
        
        url = reverse('core:tenants:billing:subscription_plans')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مدیریت پلن‌های اشتراک')
        self.assertContains(response, plan.name_persian)
        self.assertContains(response, 'persian-numbers')
    
    def test_subscription_plan_create_form(self):
        """Test subscription plan creation form."""
        url = reverse('core:tenants:billing:subscription_plan_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ایجاد پلن اشتراک جدید')
        self.assertContains(response, 'نام پلن (فارسی)')
        self.assertContains(response, 'قیمت ماهانه (تومان)')
        self.assertContains(response, 'امکانات پلن')
    
    def test_subscription_plan_create_post(self):
        """Test subscription plan creation via POST."""
        url = reverse('core:tenants:billing:subscription_plan_create')
        data = {
            'name': 'New Plan',
            'name_persian': 'پلن جدید',
            'plan_type': 'pro',
            'monthly_price_toman': '1500000',
            'yearly_price_toman': '15000000',
            'max_users': 10,
            'max_inventory_items': 5000,
            'max_customers': 2000,
            'max_monthly_transactions': 5000,
            'max_storage_gb': 20,
            'features': '{"pos_system": true, "accounting_system": true}',
            'is_active': True,
            'is_popular': False
        }
        
        response = self.client.post(url, data)
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Check that plan was created
        plan = SubscriptionPlan.objects.get(name_persian='پلن جدید')
        self.assertEqual(plan.plan_type, 'pro')
        self.assertEqual(plan.monthly_price_toman, Decimal('1500000'))
    
    def test_subscription_plan_form_validation(self):
        """Test form validation for subscription plans."""
        url = reverse('core:tenants:billing:subscription_plan_create')
        
        # Test with missing required fields
        data = {
            'name': '',  # Missing required field
            'name_persian': 'پلن تست',
            'plan_type': 'basic'
        }
        
        response = self.client.post(url, data)
        
        # Should not redirect (form has errors)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form-error')
    
    def test_subscription_plan_persian_validation(self):
        """Test Persian text validation in forms."""
        url = reverse('core:tenants:billing:subscription_plan_create')
        
        # Test with non-Persian text in Persian field
        data = {
            'name': 'Test Plan',
            'name_persian': 'Test Plan',  # Should be Persian
            'plan_type': 'basic',
            'monthly_price_toman': '1000000',
            'max_users': 5,
            'max_inventory_items': 1000,
            'max_customers': 500,
            'max_monthly_transactions': 1000,
            'max_storage_gb': 5,
            'features': '{}',
            'is_active': True
        }
        
        response = self.client.post(url, data)
        
        # Should still create (validation is client-side)
        # But we can test that the form includes Persian validation attributes
        get_response = self.client.get(url)
        self.assertContains(get_response, 'data-persian-required')


class InvoiceUITest(TestCase):
    """Test invoice management UI."""
    
    def setUp(self):
        self.client = Client()
        self.superadmin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
        self.client.force_login(self.superadmin)
        
        # Create test data
        self.plan = SubscriptionPlan.objects.create(
            name='Test Plan',
            name_persian='پلن تست',
            plan_type='basic',
            monthly_price_toman=Decimal('1000000'),
            max_users=5,
            max_inventory_items=1000,
            max_customers=500,
            max_monthly_transactions=1000,
            max_storage_gb=5,
            features={},
            is_active=True
        )
        
        self.tenant = Tenant.objects.create(
            name='Test Shop',
            domain_url='testshop',
            owner_email='owner@test.com',
            subscription_plan_fk=self.plan,
            is_active=True
        )
        
        self.invoice = TenantInvoice.objects.create(
            tenant=self.tenant,
            subscription_plan=self.plan,
            issue_date_shamsi=jdatetime.date.today().togregorian(),
            due_date_shamsi=(jdatetime.date.today() + jdatetime.timedelta(days=30)).togregorian(),
            billing_period_start=jdatetime.date.today().togregorian(),
            billing_period_end=jdatetime.date.today().togregorian(),
            subtotal_toman=self.plan.monthly_price_toman,
            status='pending',
            line_items=[{
                'description': 'اشتراک ماهانه',
                'quantity': 1,
                'unit_price': str(self.plan.monthly_price_toman),
                'total_price': str(self.plan.monthly_price_toman)
            }]
        )
    
    def test_invoice_list_view(self):
        """Test invoice list view."""
        url = reverse('core:tenants:billing:invoices')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مدیریت فاکتورها')
        self.assertContains(response, self.invoice.invoice_number)
        self.assertContains(response, self.tenant.name)
        self.assertContains(response, 'persian-numbers')
    
    def test_invoice_detail_view(self):
        """Test invoice detail view."""
        url = reverse('core:tenants:billing:invoice_detail', kwargs={'pk': self.invoice.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'فاکتور {self.invoice.invoice_number}')
        self.assertContains(response, self.tenant.name)
        self.assertContains(response, 'اطلاعات فاکتور')
        self.assertContains(response, 'آیتم‌های فاکتور')
        self.assertContains(response, 'خلاصه مالی')
    
    def test_invoice_search_functionality(self):
        """Test invoice search functionality."""
        url = reverse('core:tenants:billing:invoices')
        
        # Search by invoice number
        response = self.client.get(url, {'search': self.invoice.invoice_number})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.invoice.invoice_number)
        
        # Search by tenant name
        response = self.client.get(url, {'search': self.tenant.name})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.tenant.name)
    
    def test_invoice_status_filtering(self):
        """Test invoice status filtering."""
        url = reverse('core:tenants:billing:invoices')
        
        # Filter by pending status
        response = self.client.get(url, {'status': 'pending'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.invoice.invoice_number)
        
        # Filter by paid status (should not show our pending invoice)
        response = self.client.get(url, {'status': 'paid'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.invoice.invoice_number)
    
    def test_invoice_payment_processing_ui(self):
        """Test invoice payment processing UI elements."""
        url = reverse('core:tenants:billing:invoice_detail', kwargs={'pk': self.invoice.pk})
        response = self.client.get(url)
        
        # Should show payment processing button for pending invoices
        self.assertContains(response, 'پردازش پرداخت')
        self.assertContains(response, 'paymentModal')
        self.assertContains(response, 'روش پرداخت')
    
    def test_invoice_persian_date_formatting(self):
        """Test Persian date formatting in invoices."""
        url = reverse('core:tenants:billing:invoice_detail', kwargs={'pk': self.invoice.pk})
        response = self.client.get(url)
        
        # Check for Persian date formatting
        self.assertContains(response, 'persian-numbers')
        self.assertContains(response, 'تاریخ صدور')
        self.assertContains(response, 'سررسید')


class BillingReportsUITest(TestCase):
    """Test billing reports UI functionality."""
    
    def setUp(self):
        self.client = Client()
        self.superadmin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
        self.client.force_login(self.superadmin)
    
    def test_billing_reports_view(self):
        """Test billing reports view."""
        url = reverse('core:tenants:billing:reports')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'گزارش‌های مالی')
        self.assertContains(response, 'روند درآمد ماهانه')
        self.assertContains(response, 'عملکرد پلن‌های اشتراک')
        self.assertContains(response, 'توزیع روش‌های پرداخت')
    
    def test_reports_persian_formatting(self):
        """Test Persian formatting in reports."""
        url = reverse('core:tenants:billing:reports')
        response = self.client.get(url)
        
        # Check for Persian elements
        self.assertContains(response, 'persian-numbers')
        self.assertContains(response, 'فروردین')  # Persian month name
        self.assertContains(response, 'تومان')
        self.assertContains(response, 'ماه')
    
    def test_reports_chart_integration(self):
        """Test chart integration in reports."""
        url = reverse('core:tenants:billing:reports')
        response = self.client.get(url)
        
        # Check for chart elements
        self.assertContains(response, 'monthlyRevenueChart')
        self.assertContains(response, 'paymentMethodsChart')
        self.assertContains(response, 'Chart.js')


class BillingFormValidationTest(TestCase):
    """Test billing form validation and Persian input handling."""
    
    def setUp(self):
        self.client = Client()
        self.superadmin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
        self.client.force_login(self.superadmin)
    
    def test_persian_text_validation(self):
        """Test Persian text validation in forms."""
        url = reverse('core:tenants:billing:subscription_plan_create')
        response = self.client.get(url)
        
        # Check that Persian validation attributes are present
        self.assertContains(response, 'data-persian-required')
        self.assertContains(response, 'نام پلن (فارسی)')
    
    def test_currency_input_formatting(self):
        """Test currency input formatting."""
        url = reverse('core:tenants:billing:subscription_plan_create')
        response = self.client.get(url)
        
        # Check for currency formatting elements
        self.assertContains(response, 'تومان')
        self.assertContains(response, 'قیمت ماهانه')
        self.assertContains(response, 'قیمت سالانه')
    
    def test_number_validation(self):
        """Test number field validation."""
        url = reverse('core:tenants:billing:subscription_plan_create')
        
        # Test with invalid number
        data = {
            'name': 'Test Plan',
            'name_persian': 'پلن تست',
            'plan_type': 'basic',
            'monthly_price_toman': 'invalid',  # Invalid number
            'max_users': 5,
            'max_inventory_items': 1000,
            'max_customers': 500,
            'max_monthly_transactions': 1000,
            'max_storage_gb': 5,
            'features': '{}',
            'is_active': True
        }
        
        response = self.client.post(url, data)
        
        # Should show form with errors
        self.assertEqual(response.status_code, 200)
        # Django will handle the validation error
    
    def test_required_field_validation(self):
        """Test required field validation."""
        url = reverse('core:tenants:billing:subscription_plan_create')
        
        # Test with missing required fields
        data = {
            'name': '',  # Required field missing
            'name_persian': '',  # Required field missing
            'plan_type': 'basic'
        }
        
        response = self.client.post(url, data)
        
        # Should not redirect (form has errors)
        self.assertEqual(response.status_code, 200)


class BillingWorkflowUITest(TestCase):
    """Test billing workflow UI functionality."""
    
    def setUp(self):
        self.client = Client()
        self.superadmin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
        self.client.force_login(self.superadmin)
        
        # Create test data
        self.plan = SubscriptionPlan.objects.create(
            name='Test Plan',
            name_persian='پلن تست',
            plan_type='basic',
            monthly_price_toman=Decimal('1000000'),
            max_users=5,
            max_inventory_items=1000,
            max_customers=500,
            max_monthly_transactions=1000,
            max_storage_gb=5,
            features={},
            is_active=True
        )
        
        self.tenant = Tenant.objects.create(
            name='Test Shop',
            domain_url='testshop',
            owner_email='owner@test.com',
            subscription_plan_fk=self.plan,
            is_active=True
        )
    
    def test_invoice_creation_workflow(self):
        """Test invoice creation workflow."""
        url = reverse('core:tenants:billing:invoice_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ایجاد فاکتور جدید')
        self.assertContains(response, 'انتخاب تنانت')
        self.assertContains(response, 'نوع فاکتور')
    
    def test_bulk_invoice_generation_ui(self):
        """Test bulk invoice generation UI."""
        url = reverse('core:tenants:billing:bulk_invoice_generation')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تولید انبوه فاکتور')
        self.assertContains(response, self.tenant.name)
        self.assertContains(response, 'نوع فاکتور')
    
    def test_billing_settings_ui(self):
        """Test billing settings UI."""
        url = reverse('core:tenants:billing:settings')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تنظیمات سیستم مالی')
        self.assertContains(response, 'چرخه‌های صورتحساب')


@pytest.mark.django_db
class BillingUIIntegrationTest:
    """Integration tests for billing UI functionality."""
    
    def test_complete_billing_workflow(self, client, superadmin_user):
        """Test complete billing workflow from plan creation to payment."""
        client.force_login(superadmin_user)
        
        # 1. Create subscription plan
        plan_data = {
            'name': 'Integration Test Plan',
            'name_persian': 'پلن تست یکپارچه',
            'plan_type': 'pro',
            'monthly_price_toman': '2000000',
            'yearly_price_toman': '20000000',
            'max_users': 10,
            'max_inventory_items': 5000,
            'max_customers': 2000,
            'max_monthly_transactions': 5000,
            'max_storage_gb': 20,
            'features': '{"pos_system": true, "accounting_system": true}',
            'is_active': True,
            'is_popular': True
        }
        
        response = client.post(reverse('core:tenants:billing:subscription_plan_create'), plan_data)
        assert response.status_code == 302  # Redirect on success
        
        plan = SubscriptionPlan.objects.get(name_persian='پلن تست یکپارچه')
        assert plan.monthly_price_toman == Decimal('2000000')
        
        # 2. Create tenant with the plan
        tenant = Tenant.objects.create(
            name='Integration Test Shop',
            domain_url='integrationtest',
            owner_email='owner@integration.com',
            subscription_plan_fk=plan,
            is_active=True
        )
        
        # 3. Generate invoice
        invoice = InvoiceGenerator.generate_monthly_invoice(
            tenant=tenant,
            admin_user=superadmin_user
        )
        
        # 4. Check invoice detail view
        response = client.get(reverse('core:tenants:billing:invoice_detail', kwargs={'pk': invoice.pk}))
        assert response.status_code == 200
        assert 'پلن تست یکپارچه' in response.content.decode()
        assert 'Integration Test Shop' in response.content.decode()
        
        # 5. Process payment
        payment_data = {
            'payment_method': 'bank_transfer',
            'payment_reference': 'TEST123456',
            'payment_date': jdatetime.date.today().strftime('%Y-%m-%d')
        }
        
        response = client.post(
            reverse('core:tenants:billing:invoice_payment', kwargs={'pk': invoice.pk}),
            payment_data
        )
        assert response.status_code == 200
        
        # Check that invoice was marked as paid
        invoice.refresh_from_db()
        assert invoice.status == 'paid'
        assert invoice.payment_method == 'bank_transfer'
        assert invoice.payment_reference == 'TEST123456'


# Fixtures for pytest
@pytest.fixture
def superadmin_user():
    """Create a superadmin user for testing."""
    return SuperAdmin.objects.create_user(
        username='testadmin',
        email='admin@test.com',
        password='testpass123',
        is_superuser=True
    )


@pytest.fixture
def sample_subscription_plan():
    """Create a sample subscription plan for testing."""
    return SubscriptionPlan.objects.create(
        name='Sample Plan',
        name_persian='پلن نمونه',
        plan_type='basic',
        monthly_price_toman=Decimal('1000000'),
        yearly_price_toman=Decimal('10000000'),
        max_users=5,
        max_inventory_items=2000,
        max_customers=1000,
        max_monthly_transactions=2000,
        max_storage_gb=10,
        features={
            'pos_system': True,
            'inventory_management': True,
            'customer_management': True,
        },
        is_active=True
    )


@pytest.fixture
def sample_tenant(sample_subscription_plan):
    """Create a sample tenant for testing."""
    return Tenant.objects.create(
        name='Sample Jewelry Shop',
        domain_url='sampleshop',
        owner_email='owner@sample.com',
        subscription_plan_fk=sample_subscription_plan,
        is_active=True
    )