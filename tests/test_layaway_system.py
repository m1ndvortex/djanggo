"""
Comprehensive tests for layaway and installment plan system.
"""
import os
import django
from django.conf import settings

# Configure Django settings
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction

from zargar.customers.models import Customer
from zargar.customers.layaway_models import (
    LayawayPlan, LayawayScheduledPayment, LayawayPayment,
    LayawayRefund, LayawayContract, LayawayReminder
)
from zargar.customers.layaway_services import (
    LayawayPlanService, LayawayReminderService, LayawayContractService,
    LayawayReportService
)
from zargar.jewelry.models import JewelryItem, Category
from zargar.core.models import User


class LayawayPlanModelTest(TestCase):
    """Test LayawayPlan model functionality."""
    
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
            email='ahmad@example.com'
        )
        
        # Create test jewelry category and item
        self.category = Category.objects.create(
            name='Ring',
            name_persian='انگشتر'
        )
        
        self.jewelry_item = JewelryItem.objects.create(
            name='Gold Ring',
            sku='RING-001',
            category=self.category,
            weight_grams=Decimal('5.500'),
            karat=18,
            manufacturing_cost=Decimal('2000000'),
            selling_price=Decimal('15000000')
        )
    
    def test_layaway_plan_creation(self):
        """Test creating a layaway plan."""
        plan = LayawayPlan.objects.create(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('15000000'),
            down_payment=Decimal('3000000'),
            installment_amount=Decimal('2000000'),
            payment_frequency='monthly',
            number_of_payments=6,
            start_date=date.today()
        )
        
        self.assertEqual(plan.customer, self.customer)
        self.assertEqual(plan.jewelry_item, self.jewelry_item)
        self.assertEqual(plan.total_amount, Decimal('15000000'))
        self.assertEqual(plan.remaining_balance, Decimal('12000000'))
        self.assertEqual(plan.status, 'active')
        self.assertTrue(plan.plan_number.startswith('LAY-'))
    
    def test_plan_number_generation(self):
        """Test automatic plan number generation."""
        plan = LayawayPlan.objects.create(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('10000000'),
            down_payment=Decimal('2000000'),
            installment_amount=Decimal('1000000'),
            payment_frequency='monthly',
            number_of_payments=8,
            start_date=date.today()
        )
        
        self.assertIsNotNone(plan.plan_number)
        self.assertTrue(plan.plan_number.startswith('LAY-'))
        self.assertEqual(len(plan.plan_number), 17)  # LAY-YYYYMMDD-XXXX
    
    def test_completion_percentage_calculation(self):
        """Test completion percentage calculation."""
        plan = LayawayPlan.objects.create(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('10000000'),
            down_payment=Decimal('2000000'),
            installment_amount=Decimal('2000000'),
            payment_frequency='monthly',
            number_of_payments=4,
            start_date=date.today(),
            total_paid=Decimal('6000000')
        )
        
        self.assertEqual(plan.completion_percentage, 60.0)
    
    def test_overdue_detection(self):
        """Test overdue payment detection."""
        plan = LayawayPlan.objects.create(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('10000000'),
            down_payment=Decimal('2000000'),
            installment_amount=Decimal('2000000'),
            payment_frequency='monthly',
            number_of_payments=4,
            start_date=date.today()
        )
        
        # Create overdue scheduled payment
        overdue_date = date.today() - timedelta(days=10)
        LayawayScheduledPayment.objects.create(
            layaway_plan=plan,
            payment_number=1,
            due_date=overdue_date,
            amount=Decimal('2000000')
        )
        
        self.assertTrue(plan.is_overdue)
        self.assertEqual(plan.days_overdue, 3)  # 10 days - 7 grace period
    
    def test_payment_schedule_generation(self):
        """Test payment schedule generation."""
        plan = LayawayPlan.objects.create(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('12000000'),
            down_payment=Decimal('2000000'),
            installment_amount=Decimal('2000000'),
            payment_frequency='monthly',
            number_of_payments=5,
            start_date=date.today()
        )
        
        plan.generate_payment_schedule()
        
        scheduled_payments = plan.scheduled_payments.all()
        self.assertEqual(scheduled_payments.count(), 5)
        
        # Check payment amounts
        for payment in scheduled_payments:
            self.assertEqual(payment.amount, Decimal('2000000'))
        
        # Check payment dates are properly spaced
        payments_list = list(scheduled_payments.order_by('due_date'))
        for i in range(1, len(payments_list)):
            days_diff = (payments_list[i].due_date - payments_list[i-1].due_date).days
            self.assertAlmostEqual(days_diff, 30, delta=2)  # Monthly payments


class LayawayPlanServiceTest(TestCase):
    """Test LayawayPlanService functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.customer = Customer.objects.create(
            first_name='فاطمه',
            last_name='احمدی',
            persian_first_name='فاطمه',
            persian_last_name='احمدی',
            phone_number='09123456789',
            email='fateme@example.com'
        )
        
        self.category = Category.objects.create(
            name='Necklace',
            name_persian='گردنبند'
        )
        
        self.jewelry_item = JewelryItem.objects.create(
            name='Gold Necklace',
            sku='NECK-001',
            category=self.category,
            weight_grams=Decimal('12.500'),
            karat=18,
            manufacturing_cost=Decimal('5000000'),
            selling_price=Decimal('25000000')
        )
    
    def test_create_layaway_plan_service(self):
        """Test creating layaway plan through service."""
        plan = LayawayPlanService.create_layaway_plan(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('25000000'),
            down_payment=Decimal('5000000'),
            payment_frequency='monthly',
            number_of_payments=10,
            notes='Test layaway plan'
        )
        
        self.assertIsInstance(plan, LayawayPlan)
        self.assertEqual(plan.customer, self.customer)
        self.assertEqual(plan.jewelry_item, self.jewelry_item)
        self.assertEqual(plan.total_amount, Decimal('25000000'))
        self.assertEqual(plan.down_payment, Decimal('5000000'))
        self.assertEqual(plan.installment_amount, Decimal('2000000'))
        self.assertEqual(plan.status, 'active')
        
        # Check that payment schedule was generated
        self.assertEqual(plan.scheduled_payments.count(), 10)
        
        # Check that jewelry item is reserved
        self.jewelry_item.refresh_from_db()
        self.assertEqual(self.jewelry_item.status, 'reserved')
    
    def test_process_payment_service(self):
        """Test processing payment through service."""
        plan = LayawayPlanService.create_layaway_plan(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('20000000'),
            down_payment=Decimal('4000000'),
            payment_frequency='monthly',
            number_of_payments=8
        )
        
        # Process a payment
        payment = LayawayPlanService.process_payment(
            plan=plan,
            amount=Decimal('2000000'),
            payment_method='bank_transfer',
            notes='Monthly payment',
            reference_number='TXN123456'
        )
        
        self.assertIsInstance(payment, LayawayPayment)
        self.assertEqual(payment.amount, Decimal('2000000'))
        self.assertEqual(payment.payment_method, 'bank_transfer')
        self.assertEqual(payment.reference_number, 'TXN123456')
        
        # Check plan totals updated
        plan.refresh_from_db()
        self.assertEqual(plan.total_paid, Decimal('6000000'))  # 4M down + 2M payment
        self.assertEqual(plan.payments_made, 2)  # Down payment + this payment
    
    def test_plan_completion(self):
        """Test automatic plan completion when fully paid."""
        plan = LayawayPlanService.create_layaway_plan(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('10000000'),
            down_payment=Decimal('8000000'),
            payment_frequency='monthly',
            number_of_payments=2
        )
        
        # Make final payment
        LayawayPlanService.process_payment(
            plan=plan,
            amount=Decimal('2000000'),
            payment_method='cash'
        )
        
        plan.refresh_from_db()
        self.assertEqual(plan.status, 'completed')
        self.assertIsNotNone(plan.actual_completion_date)
        
        # Check jewelry item status changed to sold
        self.jewelry_item.refresh_from_db()
        self.assertEqual(self.jewelry_item.status, 'sold')
    
    def test_cancel_plan_service(self):
        """Test cancelling layaway plan through service."""
        plan = LayawayPlanService.create_layaway_plan(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('15000000'),
            down_payment=Decimal('3000000'),
            payment_frequency='monthly',
            number_of_payments=6
        )
        
        # Make one payment
        LayawayPlanService.process_payment(
            plan=plan,
            amount=Decimal('2000000'),
            payment_method='cash'
        )
        
        # Cancel plan with 80% refund
        refund = LayawayPlanService.cancel_plan(
            plan=plan,
            reason='Customer changed mind',
            refund_percentage=Decimal('80.00'),
            processed_by=self.user
        )
        
        plan.refresh_from_db()
        self.assertEqual(plan.status, 'cancelled')
        
        # Check refund calculation (5M total paid * 80% = 4M refund)
        self.assertIsInstance(refund, LayawayRefund)
        self.assertEqual(refund.refund_amount, Decimal('4000000'))
        
        # Check jewelry item released
        self.jewelry_item.refresh_from_db()
        self.assertEqual(self.jewelry_item.status, 'in_stock')
    
    def test_modify_payment_schedule(self):
        """Test modifying payment schedule."""
        plan = LayawayPlanService.create_layaway_plan(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('20000000'),
            down_payment=Decimal('4000000'),
            payment_frequency='monthly',
            number_of_payments=8
        )
        
        # Modify to bi-weekly payments
        success = LayawayPlanService.modify_payment_schedule(
            plan=plan,
            new_frequency='bi_weekly',
            new_installment_amount=Decimal('1000000'),
            reason='Customer requested more frequent payments'
        )
        
        self.assertTrue(success)
        
        plan.refresh_from_db()
        self.assertEqual(plan.payment_frequency, 'bi_weekly')
        self.assertEqual(plan.installment_amount, Decimal('1000000'))
        
        # Check new payment schedule generated
        remaining_payments = plan.scheduled_payments.filter(is_paid=False)
        self.assertGreater(remaining_payments.count(), 0)
    
    def test_get_overdue_plans(self):
        """Test getting overdue plans."""
        # Create plan with overdue payment
        plan = LayawayPlanService.create_layaway_plan(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('12000000'),
            down_payment=Decimal('2000000'),
            payment_frequency='monthly',
            number_of_payments=5
        )
        
        # Create overdue scheduled payment
        overdue_date = date.today() - timedelta(days=15)
        LayawayScheduledPayment.objects.create(
            layaway_plan=plan,
            payment_number=1,
            due_date=overdue_date,
            amount=Decimal('2000000')
        )
        
        overdue_plans = LayawayPlanService.get_overdue_plans(days_overdue=5)
        self.assertIn(plan, overdue_plans)
    
    def test_validation_errors(self):
        """Test validation errors in plan creation."""
        # Test inactive customer
        inactive_customer = Customer.objects.create(
            first_name='Test',
            last_name='User',
            phone_number='09123456788',
            is_active=False
        )
        
        with self.assertRaises(ValidationError):
            LayawayPlanService.create_layaway_plan(
                customer=inactive_customer,
                jewelry_item=self.jewelry_item,
                total_amount=Decimal('10000000'),
                down_payment=Decimal('2000000'),
                payment_frequency='monthly',
                number_of_payments=4
            )
        
        # Test sold jewelry item
        sold_item = JewelryItem.objects.create(
            name='Sold Ring',
            sku='SOLD-001',
            category=self.category,
            weight_grams=Decimal('3.000'),
            karat=18,
            manufacturing_cost=Decimal('1000000'),
            status='sold'
        )
        
        with self.assertRaises(ValidationError):
            LayawayPlanService.create_layaway_plan(
                customer=self.customer,
                jewelry_item=sold_item,
                total_amount=Decimal('10000000'),
                down_payment=Decimal('2000000'),
                payment_frequency='monthly',
                number_of_payments=4
            )


class LayawayReminderServiceTest(TestCase):
    """Test LayawayReminderService functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.customer = Customer.objects.create(
            first_name='علی',
            last_name='رضایی',
            persian_first_name='علی',
            persian_last_name='رضایی',
            phone_number='09123456789',
            email='ali@example.com'
        )
        
        self.category = Category.objects.create(
            name='Bracelet',
            name_persian='دستبند'
        )
        
        self.jewelry_item = JewelryItem.objects.create(
            name='Gold Bracelet',
            sku='BRAC-001',
            category=self.category,
            weight_grams=Decimal('8.000'),
            karat=18,
            manufacturing_cost=Decimal('3000000'),
            selling_price=Decimal('18000000')
        )
        
        self.plan = LayawayPlanService.create_layaway_plan(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('18000000'),
            down_payment=Decimal('3000000'),
            payment_frequency='monthly',
            number_of_payments=6
        )
    
    def test_create_reminder_schedule(self):
        """Test creating reminder schedule."""
        LayawayReminderService.create_reminder_schedule(self.plan)
        
        # Check reminders created
        reminders = self.plan.reminders.all()
        self.assertGreater(reminders.count(), 0)
        
        # Check reminder types
        upcoming_reminders = reminders.filter(reminder_type='upcoming')
        self.assertGreater(upcoming_reminders.count(), 0)
    
    def test_reminder_message_generation(self):
        """Test reminder message generation."""
        # Create upcoming payment reminder
        reminder = LayawayReminder.objects.create(
            layaway_plan=self.plan,
            reminder_type='upcoming',
            scheduled_date=date.today(),
            delivery_method='sms',
            recipient=self.customer.phone_number,
            message_template=LayawayReminderService._get_upcoming_payment_template()
        )
        
        # Generate personalized message
        message = reminder.generate_personalized_message()
        
        self.assertIn(self.customer.full_persian_name, message)
        self.assertIn(self.plan.plan_number, message)
        self.assertIn(str(self.plan.next_payment_amount), message)


class LayawayContractServiceTest(TestCase):
    """Test LayawayContractService functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.customer = Customer.objects.create(
            first_name='مریم',
            last_name='کریمی',
            persian_first_name='مریم',
            persian_last_name='کریمی',
            phone_number='09123456789',
            email='maryam@example.com',
            address='تهران، خیابان ولیعصر'
        )
        
        self.category = Category.objects.create(
            name='Earrings',
            name_persian='گوشواره'
        )
        
        self.jewelry_item = JewelryItem.objects.create(
            name='Diamond Earrings',
            sku='EAR-001',
            category=self.category,
            weight_grams=Decimal('4.500'),
            karat=18,
            manufacturing_cost=Decimal('4000000'),
            selling_price=Decimal('22000000')
        )
        
        self.plan = LayawayPlanService.create_layaway_plan(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('22000000'),
            down_payment=Decimal('4000000'),
            payment_frequency='monthly',
            number_of_payments=9
        )
    
    def test_create_default_contract_template(self):
        """Test creating default contract template."""
        contract = LayawayContractService.create_default_contract_template()
        
        self.assertIsInstance(contract, LayawayContract)
        self.assertEqual(contract.contract_type, 'standard')
        self.assertTrue(contract.is_default)
        self.assertTrue(contract.is_active)
        self.assertIn('قرارداد طلای قرضی', contract.contract_template)
    
    def test_generate_contract_content(self):
        """Test generating contract content."""
        # Create contract template
        contract_template = LayawayContractService.create_default_contract_template()
        
        # Generate contract
        contract_content = LayawayContractService.generate_contract_pdf(
            self.plan, contract_template
        )
        
        self.assertIsInstance(contract_content, bytes)
        
        # Decode and check content
        content_str = contract_content.decode('utf-8')
        self.assertIn(self.plan.plan_number, content_str)
        self.assertIn(self.customer.full_persian_name, content_str)
        self.assertIn(self.jewelry_item.name, content_str)
        self.assertIn(str(self.plan.total_amount), content_str)


class LayawayReportServiceTest(TestCase):
    """Test LayawayReportService functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.customer1 = Customer.objects.create(
            first_name='حسن',
            last_name='محمدی',
            phone_number='09123456789'
        )
        
        self.customer2 = Customer.objects.create(
            first_name='زهرا',
            last_name='احمدی',
            phone_number='09123456788'
        )
        
        self.category = Category.objects.create(
            name='Ring',
            name_persian='انگشتر'
        )
        
        self.jewelry_item1 = JewelryItem.objects.create(
            name='Gold Ring 1',
            sku='RING-001',
            category=self.category,
            weight_grams=Decimal('5.000'),
            karat=18,
            manufacturing_cost=Decimal('2000000'),
            selling_price=Decimal('12000000')
        )
        
        self.jewelry_item2 = JewelryItem.objects.create(
            name='Gold Ring 2',
            sku='RING-002',
            category=self.category,
            weight_grams=Decimal('6.000'),
            karat=18,
            manufacturing_cost=Decimal('2500000'),
            selling_price=Decimal('15000000')
        )
    
    def test_layaway_summary_report(self):
        """Test generating layaway summary report."""
        # Create test plans
        plan1 = LayawayPlanService.create_layaway_plan(
            customer=self.customer1,
            jewelry_item=self.jewelry_item1,
            total_amount=Decimal('12000000'),
            down_payment=Decimal('2000000'),
            payment_frequency='monthly',
            number_of_payments=5
        )
        
        plan2 = LayawayPlanService.create_layaway_plan(
            customer=self.customer2,
            jewelry_item=self.jewelry_item2,
            total_amount=Decimal('15000000'),
            down_payment=Decimal('3000000'),
            payment_frequency='monthly',
            number_of_payments=6
        )
        
        # Complete one plan
        for _ in range(5):
            LayawayPlanService.process_payment(
                plan=plan1,
                amount=Decimal('2000000'),
                payment_method='cash'
            )
        
        # Generate summary
        summary = LayawayReportService.get_layaway_summary()
        
        self.assertEqual(summary['total_plans'], 2)
        self.assertEqual(summary['active_plans'], 1)
        self.assertEqual(summary['completed_plans'], 1)
        self.assertEqual(summary['total_value'], Decimal('27000000'))
        self.assertGreater(summary['collection_rate'], 0)
    
    def test_customer_layaway_history(self):
        """Test getting customer layaway history."""
        # Create multiple plans for customer
        plan1 = LayawayPlanService.create_layaway_plan(
            customer=self.customer1,
            jewelry_item=self.jewelry_item1,
            total_amount=Decimal('12000000'),
            down_payment=Decimal('2000000'),
            payment_frequency='monthly',
            number_of_payments=5
        )
        
        plan2 = LayawayPlanService.create_layaway_plan(
            customer=self.customer1,
            jewelry_item=self.jewelry_item2,
            total_amount=Decimal('15000000'),
            down_payment=Decimal('3000000'),
            payment_frequency='monthly',
            number_of_payments=6
        )
        
        # Get customer history
        history = LayawayReportService.get_customer_layaway_history(self.customer1)
        
        self.assertEqual(history['total_plans'], 2)
        self.assertEqual(history['active_plans'], 2)
        self.assertEqual(history['current_balance'], Decimal('22000000'))  # 10M + 12M remaining
        self.assertEqual(len(history['payment_history']), 2)


class LayawayIntegrationTest(TestCase):
    """Integration tests for complete layaway workflows."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='testpass123'
        )
        
        self.customer = Customer.objects.create(
            first_name='محمد',
            last_name='رضایی',
            persian_first_name='محمد',
            persian_last_name='رضایی',
            phone_number='09123456789',
            email='mohammad@example.com'
        )
        
        self.category = Category.objects.create(
            name='Necklace',
            name_persian='گردنبند'
        )
        
        self.jewelry_item = JewelryItem.objects.create(
            name='Premium Gold Necklace',
            sku='PREM-001',
            category=self.category,
            weight_grams=Decimal('15.000'),
            karat=18,
            manufacturing_cost=Decimal('8000000'),
            selling_price=Decimal('35000000')
        )
    
    def test_complete_layaway_workflow(self):
        """Test complete layaway workflow from creation to completion."""
        # 1. Create layaway plan
        plan = LayawayPlanService.create_layaway_plan(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('35000000'),
            down_payment=Decimal('7000000'),
            payment_frequency='monthly',
            number_of_payments=7
        )
        
        self.assertEqual(plan.status, 'active')
        self.assertEqual(plan.total_paid, Decimal('7000000'))
        self.assertEqual(self.jewelry_item.status, 'reserved')
        
        # 2. Make several payments
        for i in range(6):
            payment = LayawayPlanService.process_payment(
                plan=plan,
                amount=Decimal('4000000'),
                payment_method='bank_transfer',
                notes=f'Payment {i+1}'
            )
            self.assertIsInstance(payment, LayawayPayment)
        
        plan.refresh_from_db()
        self.assertEqual(plan.total_paid, Decimal('31000000'))
        self.assertEqual(plan.payments_made, 7)  # 6 payments + down payment
        
        # 3. Make final payment to complete
        final_payment = LayawayPlanService.process_payment(
            plan=plan,
            amount=Decimal('4000000'),
            payment_method='cash',
            notes='Final payment'
        )
        
        plan.refresh_from_db()
        self.assertEqual(plan.status, 'completed')
        self.assertIsNotNone(plan.actual_completion_date)
        
        # 4. Check jewelry item status changed
        self.jewelry_item.refresh_from_db()
        self.assertEqual(self.jewelry_item.status, 'sold')
        
        # 5. Check customer stats updated
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.total_purchases, Decimal('35000000'))
    
    def test_layaway_cancellation_workflow(self):
        """Test layaway cancellation workflow."""
        # 1. Create plan and make some payments
        plan = LayawayPlanService.create_layaway_plan(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('30000000'),
            down_payment=Decimal('6000000'),
            payment_frequency='monthly',
            number_of_payments=6
        )
        
        # Make 2 payments
        LayawayPlanService.process_payment(plan, Decimal('4000000'), 'cash')
        LayawayPlanService.process_payment(plan, Decimal('4000000'), 'cash')
        
        plan.refresh_from_db()
        self.assertEqual(plan.total_paid, Decimal('14000000'))
        
        # 2. Cancel plan with refund
        refund = LayawayPlanService.cancel_plan(
            plan=plan,
            reason='Customer financial difficulties',
            refund_percentage=Decimal('85.00'),
            processed_by=self.user
        )
        
        # 3. Verify cancellation
        plan.refresh_from_db()
        self.assertEqual(plan.status, 'cancelled')
        
        # 4. Verify refund
        self.assertIsInstance(refund, LayawayRefund)
        expected_refund = Decimal('14000000') * Decimal('0.85')
        self.assertEqual(refund.refund_amount, expected_refund)
        
        # 5. Verify jewelry item released
        self.jewelry_item.refresh_from_db()
        self.assertEqual(self.jewelry_item.status, 'in_stock')
    
    def test_payment_schedule_modification_workflow(self):
        """Test modifying payment schedule workflow."""
        # 1. Create plan
        plan = LayawayPlanService.create_layaway_plan(
            customer=self.customer,
            jewelry_item=self.jewelry_item,
            total_amount=Decimal('24000000'),
            down_payment=Decimal('4000000'),
            payment_frequency='monthly',
            number_of_payments=10
        )
        
        original_schedule_count = plan.scheduled_payments.count()
        
        # 2. Make a few payments
        LayawayPlanService.process_payment(plan, Decimal('2000000'), 'cash')
        LayawayPlanService.process_payment(plan, Decimal('2000000'), 'cash')
        
        # 3. Modify payment schedule
        success = LayawayPlanService.modify_payment_schedule(
            plan=plan,
            new_frequency='bi_weekly',
            new_installment_amount=Decimal('1000000'),
            reason='Customer requested smaller, more frequent payments'
        )
        
        self.assertTrue(success)
        
        # 4. Verify modifications
        plan.refresh_from_db()
        self.assertEqual(plan.payment_frequency, 'bi_weekly')
        self.assertEqual(plan.installment_amount, Decimal('1000000'))
        
        # 5. Verify new schedule generated
        remaining_payments = plan.scheduled_payments.filter(is_paid=False)
        self.assertGreater(remaining_payments.count(), 0)


if __name__ == '__main__':
    pytest.main([__file__])