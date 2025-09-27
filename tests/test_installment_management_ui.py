"""
Tests for installment management and notification system UI functionality.
Tests task 7.4: Build installment management and notification system UI (Frontend)
"""
import pytest
from django.test import TestCase, Client, TransactionTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import connection
from django.core.management import call_command
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from decimal import Decimal
from datetime import date, timedelta
import json

from zargar.tenants.models import Tenant
from zargar.customers.models import Customer
from zargar.gold_installments.models import (
    GoldInstallmentContract, 
    GoldInstallmentPayment,
    GoldWeightAdjustment
)

User = get_user_model()


class InstallmentTrackingDashboardTest(TenantTestCase):
    """Test installment tracking dashboard with overdue payment management."""
    
    @classmethod
    def setUpClass(cls):
        """Set up tenant for testing."""
        super().setUpClass()
        # Create tenant
        cls.tenant = Tenant(
            name="Test Jewelry Shop",
            domain_url="testshop.localhost",
            schema_name="testshop"
        )
        cls.tenant.save()
        
        # Set up domain
        from django_tenants.models import Domain
        domain = Domain()
        domain.domain = "testshop.localhost"
        domain.tenant = cls.tenant
        domain.is_primary = True
        domain.save()
    
    def setUp(self):
        """Set up test data."""
        # Use TenantClient for proper tenant context
        self.client = TenantClient(self.tenant)
        
        # Create user with proper tenant context
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com"
        )
        
        # Create customer
        self.customer = Customer.objects.create(
            first_name="John",
            last_name="Doe",
            persian_first_name="جان",
            persian_last_name="دو",
            phone_number="09123456789",
            email="john@example.com"
        )
        
        # Create test contracts
        self.active_contract = GoldInstallmentContract.objects.create(
            customer=self.customer,
            contract_number="GIC-20250920-1001",
            contract_date=date.today() - timedelta(days=30),
            initial_gold_weight_grams=Decimal('100.000'),
            remaining_gold_weight_grams=Decimal('75.000'),
            gold_karat=18,
            status='active',
            contract_terms_persian="شرایط قرارداد طلای قرضی",
            created_by=self.user
        )
        
        self.overdue_contract = GoldInstallmentContract.objects.create(
            customer=self.customer,
            contract_number="GIC-20250920-1002",
            contract_date=date.today() - timedelta(days=60),
            initial_gold_weight_grams=Decimal('50.000'),
            remaining_gold_weight_grams=Decimal('40.000'),
            gold_karat=18,
            status='active',
            contract_terms_persian="شرایط قرارداد طلای قرضی",
            created_by=self.user
        )
        
        # Create old payment to make contract overdue
        GoldInstallmentPayment.objects.create(
            contract=self.overdue_contract,
            payment_date=date.today() - timedelta(days=45),
            payment_amount_toman=Decimal('5000000'),
            gold_price_per_gram_at_payment=Decimal('3500000'),
            effective_gold_price_per_gram=Decimal('3500000'),
            gold_weight_equivalent_grams=Decimal('1.429'),
            payment_method='cash',
            created_by=self.user
        )
        
        self.client.login(username="testuser", password="testpass123")
    
    def test_installment_tracking_dashboard_view(self):
        """Test installment tracking dashboard loads correctly."""
        url = reverse('gold_installments:installment_tracking')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Installment Tracking Dashboard")
        self.assertContains(response, "Active Contracts")
        self.assertContains(response, "Overdue")
        self.assertContains(response, "Due Soon")
        
    def test_tracking_statistics_display(self):
        """Test tracking statistics are calculated and displayed correctly."""
        url = reverse('gold_installments:installment_tracking')
        response = self.client.get(url)
        
        # Check statistics in context
        self.assertIn('tracking_stats', response.context)
        stats = response.context['tracking_stats']
        
        self.assertEqual(stats['total_active'], 2)
        self.assertGreaterEqual(stats['overdue_count'], 1)
        
    def test_overdue_filter(self):
        """Test filtering by overdue contracts."""
        url = reverse('gold_installments:installment_tracking')
        response = self.client.get(url, {'tracking_filter': 'overdue'})
        
        self.assertEqual(response.status_code, 200)
        # Should show overdue contracts
        self.assertContains(response, self.overdue_contract.contract_number)
        
    def test_active_filter(self):
        """Test filtering by active contracts."""
        url = reverse('gold_installments:installment_tracking')
        response = self.client.get(url, {'tracking_filter': 'active'})
        
        self.assertEqual(response.status_code, 200)
        # Should show both active contracts
        self.assertContains(response, self.active_contract.contract_number)
        self.assertContains(response, self.overdue_contract.contract_number)
        
    def test_contract_search(self):
        """Test searching contracts by number or customer name."""
        url = reverse('gold_installments:installment_tracking')
        response = self.client.get(url, {'search': 'GIC-20250920-1001'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.active_contract.contract_number)
        
    def test_send_reminder_functionality(self):
        """Test send reminder functionality from tracking dashboard."""
        url = reverse('gold_installments:send_payment_reminder', args=[self.overdue_contract.pk])
        
        response = self.client.post(url, {
            'reminder_type': 'payment_reminder',
            'send_method': 'sms',
            'message_template': 'Dear {customer_name}, your payment is due.'
        })
        
        # Should redirect back to notification management
        self.assertEqual(response.status_code, 302)


class DefaultManagementTest(TenantTestCase):
    """Test default management interface for non-payment situations."""
    
    @classmethod
    def setUpClass(cls):
        """Set up tenant for testing."""
        super().setUpClass()
        cls.tenant = Tenant(
            name="Test Jewelry Shop 2",
            domain_url="testshop2.localhost",
            schema_name="testshop2"
        )
        cls.tenant.save()
        
        from django_tenants.models import Domain
        domain = Domain()
        domain.domain = "testshop2.localhost"
        domain.tenant = cls.tenant
        domain.is_primary = True
        domain.save()
    
    def setUp(self):
        """Set up test data."""
        self.client = TenantClient(self.tenant)
        
        self.user = User.objects.create_user(
            username="testuser2",
            password="testpass123",
            email="test2@example.com"
        )
        
        # Create customer
        self.customer = Customer.objects.create(
            first_name="Jane",
            last_name="Smith",
            persian_first_name="جین",
            persian_last_name="اسمیت",
            phone_number="09123456788"
        )
        
        # Create defaulted contract
        self.defaulted_contract = GoldInstallmentContract.objects.create(
            customer=self.customer,
            contract_number="GIC-20250920-2001",
            contract_date=date.today() - timedelta(days=90),
            initial_gold_weight_grams=Decimal('200.000'),
            remaining_gold_weight_grams=Decimal('150.000'),
            gold_karat=18,
            status='active',  # Will be marked as defaulted in tests
            contract_terms_persian="شرایط قرارداد طلای قرضی",
            created_by=self.user
        )
        
        self.client.login(username="testuser", password="testpass123")
    
    def test_default_management_view(self):
        """Test default management interface loads correctly."""
        url = reverse('gold_installments:default_management', args=[self.defaulted_contract.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Default Management")
        self.assertContains(response, self.defaulted_contract.contract_number)
        self.assertContains(response, "Payment History Analysis")
        self.assertContains(response, "Recovery Options")
        
    def test_payment_analysis_no_payments(self):
        """Test payment analysis when no payments have been made."""
        url = reverse('gold_installments:default_management', args=[self.defaulted_contract.pk])
        response = self.client.get(url)
        
        payment_analysis = response.context['payment_analysis']
        self.assertEqual(payment_analysis['status'], 'no_payments')
        self.assertIn('days_since_contract', payment_analysis)
        
    def test_payment_analysis_with_payments(self):
        """Test payment analysis with existing payments."""
        # Add a payment
        GoldInstallmentPayment.objects.create(
            contract=self.defaulted_contract,
            payment_date=date.today() - timedelta(days=60),
            payment_amount_toman=Decimal('10000000'),
            gold_price_per_gram_at_payment=Decimal('3500000'),
            effective_gold_price_per_gram=Decimal('3500000'),
            gold_weight_equivalent_grams=Decimal('2.857'),
            payment_method='cash',
            created_by=self.user
        )
        
        url = reverse('gold_installments:default_management', args=[self.defaulted_contract.pk])
        response = self.client.get(url)
        
        payment_analysis = response.context['payment_analysis']
        self.assertNotEqual(payment_analysis['status'], 'no_payments')
        self.assertIn('last_payment_date', payment_analysis)
        self.assertIn('days_since_last_payment', payment_analysis)
        
    def test_recovery_options_display(self):
        """Test recovery options are displayed correctly."""
        url = reverse('gold_installments:default_management', args=[self.defaulted_contract.pk])
        response = self.client.get(url)
        
        recovery_options = response.context['recovery_options']
        self.assertIn('current_debt_value', recovery_options)
        self.assertIn('recovery_methods', recovery_options)
        
        # Check recovery methods
        methods = recovery_options['recovery_methods']
        method_types = [method['method'] for method in methods]
        self.assertIn('payment_plan', method_types)
        self.assertIn('partial_settlement', method_types)
        self.assertIn('gold_return', method_types)
        self.assertIn('legal_action', method_types)
        
    def test_suspend_contract_action(self):
        """Test suspending a contract."""
        url = reverse('gold_installments:process_default_action', args=[self.defaulted_contract.pk])
        
        response = self.client.post(url, {
            'action': 'suspend_contract',
            'reason': 'non_payment',
            'notes': 'Customer has not made payments for 60 days'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Check contract status changed
        self.defaulted_contract.refresh_from_db()
        self.assertEqual(self.defaulted_contract.status, 'suspended')
        
        # Check audit record created
        adjustments = GoldWeightAdjustment.objects.filter(contract=self.defaulted_contract)
        self.assertTrue(adjustments.exists())
        
    def test_mark_defaulted_action(self):
        """Test marking contract as defaulted."""
        url = reverse('gold_installments:process_default_action', args=[self.defaulted_contract.pk])
        
        response = self.client.post(url, {
            'action': 'mark_defaulted',
            'reason': 'non_payment',
            'notes': 'Customer unreachable, marking as defaulted'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Check contract status changed
        self.defaulted_contract.refresh_from_db()
        self.assertEqual(self.defaulted_contract.status, 'defaulted')


class NotificationManagementTest(TenantTestCase):
    """Test notification management interface for payment reminders."""
    
    @classmethod
    def setUpClass(cls):
        """Set up tenant for testing."""
        super().setUpClass()
        cls.tenant = Tenant(
            name="Test Jewelry Shop 3",
            domain_url="testshop3.localhost",
            schema_name="testshop3"
        )
        cls.tenant.save()
        
        from django_tenants.models import Domain
        domain = Domain()
        domain.domain = "testshop3.localhost"
        domain.tenant = cls.tenant
        domain.is_primary = True
        domain.save()
    
    def setUp(self):
        """Set up test data."""
        self.client = TenantClient(self.tenant)
        
        self.user = User.objects.create_user(
            username="testuser3",
            password="testpass123",
            email="test3@example.com"
        )
        
        # Create customer
        self.customer = Customer.objects.create(
            first_name="Alice",
            last_name="Johnson",
            persian_first_name="آلیس",
            persian_last_name="جانسون",
            phone_number="09123456787"
        )
        
        # Create active contract
        self.active_contract = GoldInstallmentContract.objects.create(
            customer=self.customer,
            contract_number="GIC-20250920-3001",
            contract_date=date.today() - timedelta(days=15),
            initial_gold_weight_grams=Decimal('80.000'),
            remaining_gold_weight_grams=Decimal('60.000'),
            gold_karat=18,
            status='active',
            contract_terms_persian="شرایط قرارداد طلای قرضی",
            created_by=self.user
        )
        
        self.client.login(username="testuser", password="testpass123")
    
    def test_notification_management_view(self):
        """Test notification management interface loads correctly."""
        url = reverse('gold_installments:notification_management')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Notification Management")
        self.assertContains(response, "Pending Reminders")
        self.assertContains(response, "Notification Templates")
        self.assertContains(response, "Notification Scheduling")
        
    def test_notification_statistics(self):
        """Test notification statistics are calculated correctly."""
        url = reverse('gold_installments:notification_management')
        response = self.client.get(url)
        
        stats = response.context['notification_stats']
        self.assertIn('pending_reminders', stats)
        self.assertIn('sent_today', stats)
        self.assertIn('scheduled_notifications', stats)
        self.assertIn('overdue_notifications', stats)
        
    def test_notification_templates_display(self):
        """Test notification templates are displayed correctly."""
        url = reverse('gold_installments:notification_management')
        response = self.client.get(url)
        
        templates = response.context['notification_templates']
        self.assertGreater(len(templates), 0)
        
        # Check template types
        template_types = [template['type'] for template in templates]
        self.assertIn('payment_reminder', template_types)
        self.assertIn('overdue_notice', template_types)
        self.assertIn('payment_confirmation', template_types)
        self.assertIn('contract_completion', template_types)
        
    def test_schedule_options_display(self):
        """Test notification schedule options are available."""
        url = reverse('gold_installments:notification_management')
        response = self.client.get(url)
        
        schedule_options = response.context['schedule_options']
        self.assertGreater(len(schedule_options), 0)
        
        # Check some expected options
        days_options = [option['days'] for option in schedule_options]
        self.assertIn(7, days_options)  # 7 days before due
        self.assertIn(0, days_options)  # On due date
        self.assertIn(-1, days_options)  # 1 day after due
        
    def test_send_payment_reminder(self):
        """Test sending payment reminder to customer."""
        url = reverse('gold_installments:send_payment_reminder', args=[self.active_contract.pk])
        
        response = self.client.post(url, {
            'reminder_type': 'payment_reminder',
            'send_method': 'sms',
            'message_template': 'Dear {customer_name}, your payment for contract {contract_number} is due.'
        })
        
        self.assertEqual(response.status_code, 302)
        
    def test_schedule_notification(self):
        """Test scheduling notification for contract."""
        url = reverse('gold_installments:schedule_notification', args=[self.active_contract.pk])
        
        response = self.client.post(url, {
            'notification_type': 'payment_reminder',
            'schedule_days': '7',
            'message_template': 'Payment reminder for {customer_name}'
        })
        
        self.assertEqual(response.status_code, 302)
        
    def test_contracts_requiring_notifications(self):
        """Test contracts requiring notifications are listed."""
        url = reverse('gold_installments:notification_management')
        response = self.client.get(url)
        
        contracts = response.context['contracts']
        self.assertIn(self.active_contract, contracts)


class ContractGenerationTest(TenantTestCase):
    """Test contract generation interface with Persian legal terms."""
    
    @classmethod
    def setUpClass(cls):
        """Set up tenant for testing."""
        super().setUpClass()
        cls.tenant = Tenant(
            name="Test Jewelry Shop 4",
            domain_url="testshop4.localhost",
            schema_name="testshop4"
        )
        cls.tenant.save()
        
        from django_tenants.models import Domain
        domain = Domain()
        domain.domain = "testshop4.localhost"
        domain.tenant = cls.tenant
        domain.is_primary = True
        domain.save()
    
    def setUp(self):
        """Set up test data."""
        self.client = TenantClient(self.tenant)
        
        self.user = User.objects.create_user(
            username="testuser4",
            password="testpass123",
            email="test4@example.com"
        )
        
        # Create customer
        self.customer = Customer.objects.create(
            first_name="Bob",
            last_name="Wilson",
            persian_first_name="باب",
            persian_last_name="ویلسون",
            phone_number="09123456786"
        )
        
        # Create contract
        self.contract = GoldInstallmentContract.objects.create(
            customer=self.customer,
            contract_number="GIC-20250920-4001",
            contract_date=date.today(),
            initial_gold_weight_grams=Decimal('120.000'),
            remaining_gold_weight_grams=Decimal('120.000'),
            gold_karat=18,
            status='active',
            payment_schedule='monthly',
            has_price_protection=True,
            price_ceiling_per_gram=Decimal('4000000'),
            early_payment_discount_percentage=Decimal('5.00'),
            contract_terms_persian="شرایط قرارداد طلای قرضی",
            special_conditions="شرایط خاص این قرارداد",
            created_by=self.user
        )
        
        self.client.login(username="testuser", password="testpass123")
    
    def test_contract_generation_view(self):
        """Test contract generation interface loads correctly."""
        url = reverse('gold_installments:contract_generation', args=[self.contract.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contract Generation")
        self.assertContains(response, self.contract.contract_number)
        self.assertContains(response, "Contract Customization")
        
    def test_legal_terms_template(self):
        """Test Persian legal terms template is provided."""
        url = reverse('gold_installments:contract_generation', args=[self.contract.pk])
        response = self.client.get(url)
        
        legal_terms = response.context['legal_terms_template']
        self.assertIn('title', legal_terms)
        self.assertIn('terms', legal_terms)
        self.assertIn('footer', legal_terms)
        
        # Check terms are present
        self.assertGreater(len(legal_terms['terms']), 0)
        
    def test_contract_data_formatting(self):
        """Test contract data is formatted correctly for display."""
        url = reverse('gold_installments:contract_generation', args=[self.contract.pk])
        response = self.client.get(url)
        
        contract_data = response.context['contract_data']
        self.assertEqual(contract_data['contract_number'], self.contract.contract_number)
        self.assertEqual(contract_data['customer_name'], "باب ویلسون")
        self.assertEqual(contract_data['customer_phone'], self.customer.phone_number)
        self.assertEqual(contract_data['gold_karat'], 18)
        
    def test_signature_requirements(self):
        """Test signature requirements are defined."""
        url = reverse('gold_installments:contract_generation', args=[self.contract.pk])
        response = self.client.get(url)
        
        signatures = response.context['signature_requirements']
        self.assertGreater(len(signatures), 0)
        
        # Check required signatures
        parties = [sig['party'] for sig in signatures]
        self.assertIn('customer', parties)
        self.assertIn('shop_owner', parties)
        
    def test_generate_contract_pdf(self):
        """Test PDF generation functionality."""
        url = reverse('gold_installments:generate_contract_pdf', args=[self.contract.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])
        
    def test_contract_preview_elements(self):
        """Test contract preview contains all necessary elements."""
        url = reverse('gold_installments:contract_generation', args=[self.contract.pk])
        response = self.client.get(url)
        
        # Check contract sections are present
        self.assertContains(response, "Contract Parties")
        self.assertContains(response, "Contract Details")
        self.assertContains(response, "Terms and Conditions")
        self.assertContains(response, "Payment Information")
        self.assertContains(response, "Signatures")
        
        # Check specific contract details
        self.assertContains(response, str(self.contract.initial_gold_weight_grams))
        self.assertContains(response, str(self.contract.gold_karat))
        self.assertContains(response, "Price Protection")
        self.assertContains(response, "Early Payment Discount")


class PaymentSchedulingTest(TenantTestCase):
    """Test payment scheduling and notification delivery workflows."""
    
    @classmethod
    def setUpClass(cls):
        """Set up tenant for testing."""
        super().setUpClass()
        cls.tenant = Tenant(
            name="Test Jewelry Shop 5",
            domain_url="testshop5.localhost",
            schema_name="testshop5"
        )
        cls.tenant.save()
        
        from django_tenants.models import Domain
        domain = Domain()
        domain.domain = "testshop5.localhost"
        domain.tenant = cls.tenant
        domain.is_primary = True
        domain.save()
    
    def setUp(self):
        """Set up test data."""
        self.client = TenantClient(self.tenant)
        
        self.user = User.objects.create_user(
            username="testuser5",
            password="testpass123",
            email="test5@example.com"
        )
        
        # Create customer
        self.customer = Customer.objects.create(
            first_name="Charlie",
            last_name="Brown",
            persian_first_name="چارلی",
            persian_last_name="براون",
            phone_number="09123456785"
        )
        
        # Create contract with payment schedule
        self.contract = GoldInstallmentContract.objects.create(
            customer=self.customer,
            contract_number="GIC-20250920-5001",
            contract_date=date.today() - timedelta(days=7),
            initial_gold_weight_grams=Decimal('60.000'),
            remaining_gold_weight_grams=Decimal('45.000'),
            gold_karat=18,
            status='active',
            payment_schedule='weekly',
            payment_amount_per_period=Decimal('2000000'),
            contract_terms_persian="شرایط قرارداد طلای قرضی",
            created_by=self.user
        )
        
        self.client.login(username="testuser", password="testpass123")
    
    def test_payment_schedule_calculation(self):
        """Test payment schedule calculation based on contract terms."""
        # Add a payment to establish payment history
        last_payment_date = date.today() - timedelta(days=5)
        GoldInstallmentPayment.objects.create(
            contract=self.contract,
            payment_date=last_payment_date,
            payment_amount_toman=Decimal('2000000'),
            gold_price_per_gram_at_payment=Decimal('3500000'),
            effective_gold_price_per_gram=Decimal('3500000'),
            gold_weight_equivalent_grams=Decimal('0.571'),
            payment_method='cash',
            created_by=self.user
        )
        
        # Calculate next payment date
        next_payment_date = self.contract.calculate_next_payment_date(last_payment_date)
        expected_date = last_payment_date + timedelta(weeks=1)
        
        self.assertEqual(next_payment_date, expected_date)
        
    def test_overdue_detection(self):
        """Test overdue payment detection logic."""
        # Add old payment to make contract overdue
        old_payment_date = date.today() - timedelta(days=15)
        GoldInstallmentPayment.objects.create(
            contract=self.contract,
            payment_date=old_payment_date,
            payment_amount_toman=Decimal('2000000'),
            gold_price_per_gram_at_payment=Decimal('3500000'),
            effective_gold_price_per_gram=Decimal('3500000'),
            gold_weight_equivalent_grams=Decimal('0.571'),
            payment_method='cash',
            created_by=self.user
        )
        
        # Check if contract is detected as overdue
        self.assertTrue(self.contract.is_overdue)
        
    def test_notification_workflow_integration(self):
        """Test integration between payment scheduling and notifications."""
        # Test that overdue contracts appear in notification management
        url = reverse('gold_installments:notification_management')
        response = self.client.get(url)
        
        # Should include contracts that need notifications
        self.assertEqual(response.status_code, 200)
        
        # Test sending reminder for scheduled payment
        reminder_url = reverse('gold_installments:send_payment_reminder', args=[self.contract.pk])
        response = self.client.post(reminder_url, {
            'reminder_type': 'payment_reminder',
            'send_method': 'sms',
            'message_template': 'Payment due for {customer_name}'
        })
        
        self.assertEqual(response.status_code, 302)


class UIWorkflowIntegrationTest(TenantTestCase):
    """Test complete UI workflows for installment management."""
    
    @classmethod
    def setUpClass(cls):
        """Set up tenant for testing."""
        super().setUpClass()
        cls.tenant = Tenant(
            name="Test Jewelry Shop 6",
            domain_url="testshop6.localhost",
            schema_name="testshop6"
        )
        cls.tenant.save()
        
        from django_tenants.models import Domain
        domain = Domain()
        domain.domain = "testshop6.localhost"
        domain.tenant = cls.tenant
        domain.is_primary = True
        domain.save()
    
    def setUp(self):
        """Set up test data."""
        self.client = TenantClient(self.tenant)
        
        self.user = User.objects.create_user(
            username="testuser6",
            password="testpass123",
            email="test6@example.com"
        )
        
        # Create customer
        self.customer = Customer.objects.create(
            first_name="David",
            last_name="Miller",
            persian_first_name="دیوید",
            persian_last_name="میلر",
            phone_number="09123456784"
        )
        
        # Create contract
        self.contract = GoldInstallmentContract.objects.create(
            customer=self.customer,
            contract_number="GIC-20250920-6001",
            contract_date=date.today() - timedelta(days=30),
            initial_gold_weight_grams=Decimal('100.000'),
            remaining_gold_weight_grams=Decimal('80.000'),
            gold_karat=18,
            status='active',
            contract_terms_persian="شرایط قرارداد طلای قرضی",
            created_by=self.user
        )
        
        self.client.login(username="testuser", password="testpass123")
    
    def test_complete_workflow_tracking_to_default_management(self):
        """Test complete workflow from tracking to default management."""
        # 1. Start at tracking dashboard
        tracking_url = reverse('gold_installments:installment_tracking')
        response = self.client.get(tracking_url)
        self.assertEqual(response.status_code, 200)
        
        # 2. Navigate to default management for overdue contract
        default_url = reverse('gold_installments:default_management', args=[self.contract.pk])
        response = self.client.get(default_url)
        self.assertEqual(response.status_code, 200)
        
        # 3. Process default action
        action_url = reverse('gold_installments:process_default_action', args=[self.contract.pk])
        response = self.client.post(action_url, {
            'action': 'suspend_contract',
            'reason': 'non_payment',
            'notes': 'Customer not responding'
        })
        self.assertEqual(response.status_code, 302)
        
        # 4. Verify contract status changed
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, 'suspended')
        
    def test_complete_workflow_notification_to_contract_generation(self):
        """Test workflow from notification management to contract generation."""
        # 1. Start at notification management
        notification_url = reverse('gold_installments:notification_management')
        response = self.client.get(notification_url)
        self.assertEqual(response.status_code, 200)
        
        # 2. Send reminder
        reminder_url = reverse('gold_installments:send_payment_reminder', args=[self.contract.pk])
        response = self.client.post(reminder_url, {
            'reminder_type': 'payment_reminder',
            'send_method': 'sms',
            'message_template': 'Payment reminder'
        })
        self.assertEqual(response.status_code, 302)
        
        # 3. Navigate to contract generation
        generation_url = reverse('gold_installments:contract_generation', args=[self.contract.pk])
        response = self.client.get(generation_url)
        self.assertEqual(response.status_code, 200)
        
        # 4. Generate PDF contract
        pdf_url = reverse('gold_installments:generate_contract_pdf', args=[self.contract.pk])
        response = self.client.get(pdf_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        
    def test_ajax_functionality(self):
        """Test AJAX endpoints work correctly."""
        # Test gold price calculator
        calc_url = reverse('gold_installments:ajax_gold_calculator')
        response = self.client.get(calc_url, {
            'amount': '3500000',
            'gold_price': '3500000'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('gold_weight_grams', data)
        self.assertEqual(data['gold_weight_grams'], 1.0)
        
    def test_permission_and_security(self):
        """Test permission and security for installment management views."""
        # Test unauthenticated access
        self.client.logout()
        
        urls_to_test = [
            reverse('gold_installments:installment_tracking'),
            reverse('gold_installments:default_management', args=[self.contract.pk]),
            reverse('gold_installments:notification_management'),
            reverse('gold_installments:contract_generation', args=[self.contract.pk]),
        ]
        
        for url in urls_to_test:
            response = self.client.get(url)
            # Should redirect to login or return 403
            self.assertIn(response.status_code, [302, 403])
        
        # Test cross-tenant access by creating another tenant
        other_tenant = Tenant(
            name="Other Shop",
            domain_url="othershop.localhost",
            schema_name="othershop"
        )
        other_tenant.save()
        
        from django_tenants.models import Domain
        other_domain = Domain()
        other_domain.domain = "othershop.localhost"
        other_domain.tenant = other_tenant
        other_domain.is_primary = True
        other_domain.save()
        
        # Use different client for other tenant
        other_client = TenantClient(other_tenant)
        other_user = User.objects.create_user(
            username="otheruser",
            password="testpass123",
            email="other@example.com"
        )
        
        other_client.login(username="otheruser", password="testpass123")
        
        # Should not be able to access contracts from different tenant
        response = other_client.get(reverse('gold_installments:default_management', args=[self.contract.pk]))
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    pytest.main([__file__])