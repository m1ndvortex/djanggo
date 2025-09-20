"""
Comprehensive tests for subscription and billing management backend.
Tests subscription plans, invoice generation, and billing workflows for Iranian market.
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
from django.test import TestCase, TransactionTestCase
from django.db import transaction
from django.core.management import call_command
import jdatetime
from unittest.mock import patch, MagicMock

from zargar.tenants.models import Tenant, Domain
from zargar.tenants.admin_models import (
    SuperAdmin, SubscriptionPlan, TenantInvoice, BillingCycle, TenantAccessLog
)
from zargar.tenants.billing_services import (
    SubscriptionManager, InvoiceGenerator, BillingWorkflow
)


class SubscriptionPlanModelTest(TestCase):
    """Test SubscriptionPlan model functionality."""
    
    def setUp(self):
        self.admin_user = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@zargar.com',
            password='testpass123'
        )
    
    def test_create_subscription_plan(self):
        """Test creating a subscription plan with Iranian market pricing."""
        plan = SubscriptionPlan.objects.create(
            name='Test Plan',
            name_persian='پلن تست',
            plan_type='basic',
            monthly_price_toman=Decimal('500000'),
            yearly_price_toman=Decimal('5000000'),
            max_users=5,
            max_inventory_items=1000,
            max_customers=500,
            max_monthly_transactions=1000,
            max_storage_gb=10,
            features={
                'pos_system': True,
                'inventory_management': True,
                'accounting_system': False
            },
            created_by=self.admin_user
        )
        
        self.assertEqual(plan.name, 'Test Plan')
        self.assertEqual(plan.name_persian, 'پلن تست')
        self.assertEqual(plan.monthly_price_toman, Decimal('500000'))
        self.assertEqual(plan.yearly_price_toman, Decimal('5000000'))
        self.assertEqual(plan.max_users, 5)
        self.assertTrue(plan.features['pos_system'])
        self.assertFalse(plan.features['accounting_system'])
    
    def test_yearly_discount_calculation(self):
        """Test yearly discount percentage calculation."""
        plan = SubscriptionPlan.objects.create(
            name='Pro Plan',
            name_persian='پلن حرفه‌ای',
            plan_type='pro',
            monthly_price_toman=Decimal('1000000'),  # 1M Toman/month
            yearly_price_toman=Decimal('10000000'),  # 10M Toman/year (2 months free)
            max_users=10,
            max_inventory_items=5000,
            max_customers=2000,
            max_monthly_transactions=5000,
            max_storage_gb=50
        )
        
        # 12M - 10M = 2M discount, 2M/12M = 16.7% discount
        expected_discount = 16.7
        self.assertAlmostEqual(plan.yearly_discount_percentage, expected_discount, places=1)
    
    def test_features_persian_property(self):
        """Test Persian feature descriptions."""
        plan = SubscriptionPlan.objects.create(
            name='Enterprise Plan',
            name_persian='پلن سازمانی',
            plan_type='enterprise',
            monthly_price_toman=Decimal('2000000'),
            max_users=20,
            max_inventory_items=10000,
            max_customers=5000,
            max_monthly_transactions=10000,
            max_storage_gb=100,
            features={
                'pos_system': True,
                'inventory_management': True,
                'accounting_system': True,
                'gold_installment': True,
                'reporting': True
            }
        )
        
        persian_features = plan.features_persian
        self.assertIn('سیستم فروش (POS)', persian_features)
        self.assertIn('مدیریت موجودی', persian_features)
        self.assertIn('سیستم حسابداری', persian_features)
        self.assertIn('سیستم طلای قرضی', persian_features)
        self.assertIn('گزارش‌گیری', persian_features)
    
    def test_plan_string_representation(self):
        """Test string representation of subscription plan."""
        plan = SubscriptionPlan.objects.create(
            name='Basic Plan',
            name_persian='پلن پایه',
            plan_type='basic',
            monthly_price_toman=Decimal('500000'),
            max_users=2,
            max_inventory_items=500,
            max_customers=200,
            max_monthly_transactions=500,
            max_storage_gb=5
        )
        
        expected_str = 'پلن پایه (Basic Plan)'
        self.assertEqual(str(plan), expected_str)


class TenantInvoiceModelTest(TestCase):
    """Test TenantInvoice model functionality."""
    
    def setUp(self):
        self.admin_user = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@zargar.com',
            password='testpass123'
        )
        
        self.subscription_plan = SubscriptionPlan.objects.create(
            name='Pro Plan',
            name_persian='پلن حرفه‌ای',
            plan_type='pro',
            monthly_price_toman=Decimal('1200000'),
            max_users=5,
            max_inventory_items=2000,
            max_customers=1000,
            max_monthly_transactions=2000,
            max_storage_gb=20
        )
        
        self.tenant = Tenant.objects.create(
            name='Test Jewelry Shop',
            schema_name='test_shop',
            owner_name='احمد رضایی',
            owner_email='ahmad@testshop.com',
            subscription_plan=self.subscription_plan
        )
        
        Domain.objects.create(
            domain='testshop.zargar.com',
            tenant=self.tenant,
            is_primary=True
        )
    
    def test_create_invoice(self):
        """Test creating a tenant invoice with Persian dates."""
        current_date = jdatetime.date.today()
        
        invoice = TenantInvoice.objects.create(
            tenant=self.tenant,
            subscription_plan=self.subscription_plan,
            issue_date_shamsi=current_date.togregorian(),
            due_date_shamsi=(current_date + jdatetime.timedelta(days=30)).togregorian(),
            billing_period_start=current_date.replace(day=1).togregorian(),
            billing_period_end=current_date.replace(day=30).togregorian(),
            subtotal_toman=self.subscription_plan.monthly_price_toman,
            created_by=self.admin_user
        )
        
        self.assertEqual(invoice.tenant, self.tenant)
        self.assertEqual(invoice.subscription_plan, self.subscription_plan)
        self.assertEqual(invoice.subtotal_toman, Decimal('1200000'))
        self.assertEqual(invoice.status, 'pending')
        self.assertTrue(invoice.invoice_number.startswith('INV-'))
    
    def test_invoice_number_generation(self):
        """Test automatic invoice number generation."""
        current_date = jdatetime.date.today()
        
        invoice1 = TenantInvoice.objects.create(
            tenant=self.tenant,
            subscription_plan=self.subscription_plan,
            issue_date_shamsi=current_date.togregorian(),
            due_date_shamsi=(current_date + jdatetime.timedelta(days=30)).togregorian(),
            billing_period_start=current_date.replace(day=1).togregorian(),
            billing_period_end=current_date.replace(day=30).togregorian(),
            subtotal_toman=self.subscription_plan.monthly_price_toman
        )
        
        invoice2 = TenantInvoice.objects.create(
            tenant=self.tenant,
            subscription_plan=self.subscription_plan,
            issue_date_shamsi=current_date.togregorian(),
            due_date_shamsi=(current_date + jdatetime.timedelta(days=30)).togregorian(),
            billing_period_start=current_date.replace(day=1).togregorian(),
            billing_period_end=current_date.replace(day=30).togregorian(),
            subtotal_toman=self.subscription_plan.monthly_price_toman
        )
        
        # Both invoices should have unique numbers
        self.assertNotEqual(invoice1.invoice_number, invoice2.invoice_number)
        
        # Second invoice should have higher sequence number
        seq1 = int(invoice1.invoice_number.split('-')[-1])
        seq2 = int(invoice2.invoice_number.split('-')[-1])
        self.assertEqual(seq2, seq1 + 1)
    
    def test_amount_calculations(self):
        """Test tax and total amount calculations."""
        current_date = jdatetime.date.today()
        
        invoice = TenantInvoice.objects.create(
            tenant=self.tenant,
            subscription_plan=self.subscription_plan,
            issue_date_shamsi=current_date.togregorian(),
            due_date_shamsi=(current_date + jdatetime.timedelta(days=30)).togregorian(),
            billing_period_start=current_date.replace(day=1).togregorian(),
            billing_period_end=current_date.replace(day=30).togregorian(),
            subtotal_toman=Decimal('1000000'),  # 1M Toman
            tax_rate=Decimal('9.00'),  # 9% Iranian VAT
            discount_amount_toman=Decimal('50000')  # 50K discount
        )
        
        # Tax: 1,000,000 * 9% = 90,000
        expected_tax = Decimal('90000')
        self.assertEqual(invoice.tax_amount_toman, expected_tax)
        
        # Total: 1,000,000 + 90,000 - 50,000 = 1,040,000
        expected_total = Decimal('1040000')
        self.assertEqual(invoice.total_amount_toman, expected_total)
    
    def test_overdue_calculation(self):
        """Test overdue invoice detection."""
        past_date = jdatetime.date.today() - jdatetime.timedelta(days=10)
        
        invoice = TenantInvoice.objects.create(
            tenant=self.tenant,
            subscription_plan=self.subscription_plan,
            issue_date_shamsi=past_date.togregorian(),
            due_date_shamsi=(past_date + jdatetime.timedelta(days=5)).togregorian(),  # 5 days overdue
            billing_period_start=past_date.replace(day=1).togregorian(),
            billing_period_end=past_date.replace(day=30).togregorian(),
            subtotal_toman=self.subscription_plan.monthly_price_toman,
            status='pending'
        )
        
        self.assertTrue(invoice.is_overdue)
        self.assertEqual(invoice.days_overdue, 5)
    
    def test_mark_as_paid(self):
        """Test marking invoice as paid."""
        current_date = jdatetime.date.today()
        
        invoice = TenantInvoice.objects.create(
            tenant=self.tenant,
            subscription_plan=self.subscription_plan,
            issue_date_shamsi=current_date.togregorian(),
            due_date_shamsi=(current_date + jdatetime.timedelta(days=30)).togregorian(),
            billing_period_start=current_date.replace(day=1).togregorian(),
            billing_period_end=current_date.replace(day=30).togregorian(),
            subtotal_toman=self.subscription_plan.monthly_price_toman,
            created_by=self.admin_user
        )
        
        invoice.mark_as_paid(
            payment_method='bank_transfer',
            payment_reference='TXN123456'
        )
        
        self.assertEqual(invoice.status, 'paid')
        self.assertEqual(invoice.payment_method, 'bank_transfer')
        self.assertEqual(invoice.payment_reference, 'TXN123456')
        self.assertEqual(invoice.payment_date_shamsi, jdatetime.date.today().togregorian())


class SubscriptionManagerTest(TestCase):
    """Test SubscriptionManager service functionality."""
    
    def test_create_default_plans(self):
        """Test creation of default subscription plans."""
        created_plans = SubscriptionManager.create_default_plans()
        
        # Should create 3 default plans
        self.assertEqual(len(created_plans), 3)
        
        # Check plan types
        plan_types = [plan.plan_type for plan in created_plans]
        self.assertIn('basic', plan_types)
        self.assertIn('pro', plan_types)
        self.assertIn('enterprise', plan_types)
        
        # Check Persian names
        basic_plan = next(plan for plan in created_plans if plan.plan_type == 'basic')
        self.assertEqual(basic_plan.name_persian, 'پلن پایه')
        
        # Check pricing
        self.assertEqual(basic_plan.monthly_price_toman, Decimal('500000'))
        self.assertEqual(basic_plan.yearly_price_toman, Decimal('5000000'))
    
    def test_get_plan_by_type(self):
        """Test retrieving plan by type."""
        SubscriptionManager.create_default_plans()
        
        basic_plan = SubscriptionManager.get_plan_by_type('basic')
        self.assertIsNotNone(basic_plan)
        self.assertEqual(basic_plan.plan_type, 'basic')
        
        nonexistent_plan = SubscriptionManager.get_plan_by_type('nonexistent')
        self.assertIsNone(nonexistent_plan)
    
    def test_upgrade_tenant_plan(self):
        """Test upgrading tenant subscription plan."""
        # Create plans
        SubscriptionManager.create_default_plans()
        basic_plan = SubscriptionManager.get_plan_by_type('basic')
        pro_plan = SubscriptionManager.get_plan_by_type('pro')
        
        # Create tenant with basic plan
        tenant = Tenant.objects.create(
            name='Test Shop',
            schema_name='test_shop',
            owner_name='Test Owner',
            owner_email='owner@test.com',
            subscription_plan=basic_plan
        )
        
        Domain.objects.create(
            domain='testshop.zargar.com',
            tenant=tenant,
            is_primary=True
        )
        
        # Create admin user
        admin_user = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@zargar.com',
            password='testpass123'
        )
        
        # Upgrade to pro plan
        result = SubscriptionManager.upgrade_tenant_plan(tenant, pro_plan, admin_user)
        
        self.assertTrue(result)
        tenant.refresh_from_db()
        self.assertEqual(tenant.subscription_plan, pro_plan)
        
        # Check audit log
        log_entry = TenantAccessLog.objects.filter(
            tenant_schema=tenant.schema_name,
            action='update',
            model_name='Tenant'
        ).first()
        
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.details['action'], 'plan_upgrade')


class InvoiceGeneratorTest(TestCase):
    """Test InvoiceGenerator service functionality."""
    
    def setUp(self):
        self.admin_user = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@zargar.com',
            password='testpass123'
        )
        
        SubscriptionManager.create_default_plans()
        self.pro_plan = SubscriptionManager.get_plan_by_type('pro')
        
        self.tenant = Tenant.objects.create(
            name='Test Jewelry Shop',
            schema_name='test_shop',
            owner_name='احمد رضایی',
            owner_email='ahmad@testshop.com',
            subscription_plan=self.pro_plan
        )
        
        Domain.objects.create(
            domain='testshop.zargar.com',
            tenant=self.tenant,
            is_primary=True
        )
    
    def test_generate_monthly_invoice(self):
        """Test monthly invoice generation."""
        current_date = jdatetime.date.today()
        billing_month = current_date.replace(day=1)
        
        invoice = InvoiceGenerator.generate_monthly_invoice(
            tenant=self.tenant,
            billing_month=billing_month,
            admin_user=self.admin_user
        )
        
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.tenant, self.tenant)
        self.assertEqual(invoice.subscription_plan, self.pro_plan)
        self.assertEqual(invoice.subtotal_toman, self.pro_plan.monthly_price_toman)
        self.assertEqual(invoice.billing_period_start, billing_month)
        
        # Check line items
        self.assertEqual(len(invoice.line_items), 1)
        line_item = invoice.line_items[0]
        self.assertIn('اشتراک ماهانه', line_item['description'])
        self.assertEqual(line_item['quantity'], 1)
    
    def test_generate_yearly_invoice(self):
        """Test yearly invoice generation."""
        current_year = jdatetime.date.today().year
        
        invoice = InvoiceGenerator.generate_yearly_invoice(
            tenant=self.tenant,
            billing_year=current_year,
            admin_user=self.admin_user
        )
        
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.tenant, self.tenant)
        
        # Check discount calculation
        monthly_total = self.pro_plan.monthly_price_toman * 12
        expected_discount = monthly_total - self.pro_plan.yearly_price_toman
        self.assertEqual(invoice.discount_amount_toman, expected_discount)
        
        # Check line items (subscription + discount)
        self.assertEqual(len(invoice.line_items), 2)
        
        subscription_item = invoice.line_items[0]
        self.assertIn('اشتراک سالانه', subscription_item['description'])
        self.assertEqual(subscription_item['quantity'], 12)
        
        discount_item = invoice.line_items[1]
        self.assertIn('تخفیف اشتراک سالانه', discount_item['description'])
        self.assertTrue(discount_item.get('is_discount', False))
    
    def test_duplicate_invoice_prevention(self):
        """Test prevention of duplicate invoice generation."""
        current_date = jdatetime.date.today()
        billing_month = current_date.replace(day=1)
        
        # Generate first invoice
        invoice1 = InvoiceGenerator.generate_monthly_invoice(
            tenant=self.tenant,
            billing_month=billing_month,
            admin_user=self.admin_user
        )
        
        # Try to generate duplicate
        invoice2 = InvoiceGenerator.generate_monthly_invoice(
            tenant=self.tenant,
            billing_month=billing_month,
            admin_user=self.admin_user
        )
        
        # Should return the same invoice
        self.assertEqual(invoice1.id, invoice2.id)
    
    @patch('zargar.tenants.billing_services.send_mail')
    def test_send_invoice_notification(self, mock_send_mail):
        """Test sending invoice notification email."""
        mock_send_mail.return_value = True
        
        current_date = jdatetime.date.today()
        billing_month = current_date.replace(day=1)
        
        invoice = InvoiceGenerator.generate_monthly_invoice(
            tenant=self.tenant,
            billing_month=billing_month,
            admin_user=self.admin_user
        )
        
        result = InvoiceGenerator.send_invoice_notification(invoice, 'email')
        
        self.assertTrue(result)
        mock_send_mail.assert_called_once()
        
        # Check email parameters
        call_args = mock_send_mail.call_args
        self.assertIn('فاکتور جدید', call_args[1]['subject'])
        self.assertEqual(call_args[1]['recipient_list'], [self.tenant.owner_email])


class BillingWorkflowTest(TestCase):
    """Test BillingWorkflow service functionality."""
    
    def setUp(self):
        self.admin_user = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@zargar.com',
            password='testpass123'
        )
        
        SubscriptionManager.create_default_plans()
        self.pro_plan = SubscriptionManager.get_plan_by_type('pro')
        
        self.tenant = Tenant.objects.create(
            name='Test Jewelry Shop',
            schema_name='test_shop',
            owner_name='احمد رضایی',
            owner_email='ahmad@testshop.com',
            subscription_plan=self.pro_plan
        )
        
        Domain.objects.create(
            domain='testshop.zargar.com',
            tenant=self.tenant,
            is_primary=True
        )
    
    def test_setup_tenant_billing(self):
        """Test setting up billing cycle for tenant."""
        billing_cycle = BillingWorkflow.setup_tenant_billing(
            tenant=self.tenant,
            cycle_type='monthly',
            billing_day=15,
            admin_user=self.admin_user
        )
        
        self.assertIsNotNone(billing_cycle)
        self.assertEqual(billing_cycle.tenant, self.tenant)
        self.assertEqual(billing_cycle.cycle_type, 'monthly')
        self.assertEqual(billing_cycle.billing_day, 15)
        self.assertTrue(billing_cycle.is_active)
        
        # Check audit log
        log_entry = TenantAccessLog.objects.filter(
            tenant_schema=self.tenant.schema_name,
            action='create',
            model_name='BillingCycle'
        ).first()
        
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.details['action'], 'billing_setup')
    
    def test_manual_payment_processing(self):
        """Test manual payment processing."""
        # Create invoice
        current_date = jdatetime.date.today()
        invoice = TenantInvoice.objects.create(
            tenant=self.tenant,
            subscription_plan=self.pro_plan,
            issue_date_shamsi=current_date.togregorian(),
            due_date_shamsi=(current_date + jdatetime.timedelta(days=30)).togregorian(),
            billing_period_start=current_date.replace(day=1).togregorian(),
            billing_period_end=current_date.replace(day=30).togregorian(),
            subtotal_toman=self.pro_plan.monthly_price_toman,
            status='pending'
        )
        
        # Suspend tenant
        self.tenant.is_active = False
        self.tenant.save()
        
        # Process payment
        result = BillingWorkflow.manual_payment_processing(
            invoice=invoice,
            payment_method='bank_transfer',
            payment_reference='TXN789',
            admin_user=self.admin_user
        )
        
        self.assertTrue(result)
        
        # Check invoice status
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'paid')
        self.assertEqual(invoice.payment_method, 'bank_transfer')
        self.assertEqual(invoice.payment_reference, 'TXN789')
        
        # Check tenant reactivation
        self.tenant.refresh_from_db()
        self.assertTrue(self.tenant.is_active)


class BillingCycleModelTest(TestCase):
    """Test BillingCycle model functionality."""
    
    def setUp(self):
        SubscriptionManager.create_default_plans()
        self.basic_plan = SubscriptionManager.get_plan_by_type('basic')
        
        self.tenant = Tenant.objects.create(
            name='Test Shop',
            schema_name='test_shop',
            owner_name='Test Owner',
            owner_email='owner@test.com',
            subscription_plan=self.basic_plan
        )
        
        Domain.objects.create(
            domain='testshop.zargar.com',
            tenant=self.tenant,
            is_primary=True
        )
    
    def test_calculate_next_billing_date(self):
        """Test next billing date calculation."""
        current_date = jdatetime.date.today()
        
        billing_cycle = BillingCycle.objects.create(
            tenant=self.tenant,
            cycle_type='monthly',
            next_billing_date=current_date.togregorian(),
            billing_day=15
        )
        
        # Calculate next billing date
        next_date = billing_cycle.calculate_next_billing_date()
        
        self.assertIsNotNone(next_date)
        self.assertGreater(next_date, current_date)
        
        # For monthly cycle, should be next month
        if current_date.month == 12:
            expected_month = 1
            expected_year = current_date.year + 1
        else:
            expected_month = current_date.month + 1
            expected_year = current_date.year
        
        self.assertEqual(next_date.month, expected_month)
        self.assertEqual(next_date.year, expected_year)


class ManagementCommandTest(TransactionTestCase):
    """Test Django management commands for billing."""
    
    def test_create_subscription_plans_command(self):
        """Test create_subscription_plans management command."""
        # Ensure no plans exist
        SubscriptionPlan.objects.all().delete()
        
        # Run command
        call_command('create_subscription_plans')
        
        # Check plans were created
        plans = SubscriptionPlan.objects.all()
        self.assertEqual(len(plans), 3)
        
        plan_types = [plan.plan_type for plan in plans]
        self.assertIn('basic', plan_types)
        self.assertIn('pro', plan_types)
        self.assertIn('enterprise', plan_types)
    
    def test_generate_monthly_invoices_command_dry_run(self):
        """Test generate_monthly_invoices command in dry run mode."""
        # Create test data
        SubscriptionManager.create_default_plans()
        pro_plan = SubscriptionManager.get_plan_by_type('pro')
        
        tenant = Tenant.objects.create(
            name='Test Shop',
            schema_name='test_shop',
            owner_name='Test Owner',
            owner_email='owner@test.com',
            subscription_plan=pro_plan
        )
        
        Domain.objects.create(
            domain='testshop.zargar.com',
            tenant=tenant,
            is_primary=True
        )
        
        # Setup billing cycle due today
        current_date = jdatetime.date.today()
        BillingCycle.objects.create(
            tenant=tenant,
            cycle_type='monthly',
            next_billing_date=current_date.togregorian(),
            billing_day=current_date.day,
            is_active=True
        )
        
        # Run command in dry run mode
        call_command('generate_monthly_invoices', '--dry-run')
        
        # No invoices should be created
        invoices = TenantInvoice.objects.filter(tenant=tenant)
        self.assertEqual(len(invoices), 0)


@pytest.mark.django_db
class TestSubscriptionBillingIntegration:
    """Integration tests for subscription and billing system."""
    
    def test_complete_billing_workflow(self):
        """Test complete billing workflow from plan creation to payment."""
        # Create admin user
        admin_user = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@zargar.com',
            password='testpass123'
        )
        
        # Create subscription plans
        created_plans = SubscriptionManager.create_default_plans()
        assert len(created_plans) == 3
        
        pro_plan = SubscriptionManager.get_plan_by_type('pro')
        assert pro_plan is not None
        
        # Create tenant
        tenant = Tenant.objects.create(
            name='Integration Test Shop',
            schema_name='integration_shop',
            owner_name='علی احمدی',
            owner_email='ali@integrationshop.com',
            subscription_plan=pro_plan
        )
        
        Domain.objects.create(
            domain='integrationshop.zargar.com',
            tenant=tenant,
            is_primary=True
        )
        
        # Setup billing cycle
        billing_cycle = BillingWorkflow.setup_tenant_billing(
            tenant=tenant,
            cycle_type='monthly',
            billing_day=1,
            admin_user=admin_user
        )
        assert billing_cycle is not None
        
        # Generate invoice
        invoice = InvoiceGenerator.generate_monthly_invoice(
            tenant=tenant,
            admin_user=admin_user
        )
        assert invoice is not None
        assert invoice.status == 'pending'
        assert invoice.total_amount_toman > 0
        
        # Process payment
        result = BillingWorkflow.manual_payment_processing(
            invoice=invoice,
            payment_method='bank_transfer',
            payment_reference='INT_TEST_123',
            admin_user=admin_user
        )
        assert result is True
        
        # Verify final state
        invoice.refresh_from_db()
        assert invoice.status == 'paid'
        assert invoice.payment_method == 'bank_transfer'
        assert invoice.payment_reference == 'INT_TEST_123'
        
        tenant.refresh_from_db()
        assert tenant.is_active is True
        
        # Check audit logs
        logs = TenantAccessLog.objects.filter(tenant_schema=tenant.schema_name)
        assert len(logs) >= 3  # billing setup, invoice creation, payment processing
    
    def test_plan_upgrade_workflow(self):
        """Test tenant plan upgrade workflow."""
        # Create admin user
        admin_user = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@zargar.com',
            password='testpass123'
        )
        
        # Create plans
        SubscriptionManager.create_default_plans()
        basic_plan = SubscriptionManager.get_plan_by_type('basic')
        pro_plan = SubscriptionManager.get_plan_by_type('pro')
        
        # Create tenant with basic plan
        tenant = Tenant.objects.create(
            name='Upgrade Test Shop',
            schema_name='upgrade_shop',
            owner_name='محمد حسینی',
            owner_email='mohammad@upgradeshop.com',
            subscription_plan=basic_plan
        )
        
        Domain.objects.create(
            domain='upgradeshop.zargar.com',
            tenant=tenant,
            is_primary=True
        )
        
        # Verify initial plan
        assert tenant.subscription_plan == basic_plan
        
        # Upgrade to pro plan
        result = SubscriptionManager.upgrade_tenant_plan(
            tenant=tenant,
            new_plan=pro_plan,
            admin_user=admin_user
        )
        assert result is True
        
        # Verify upgrade
        tenant.refresh_from_db()
        assert tenant.subscription_plan == pro_plan
        
        # Generate invoice with new plan
        invoice = InvoiceGenerator.generate_monthly_invoice(
            tenant=tenant,
            admin_user=admin_user
        )
        
        # Should use new plan pricing
        assert invoice.subtotal_toman == pro_plan.monthly_price_toman
        assert invoice.subscription_plan == pro_plan