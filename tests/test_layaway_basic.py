"""
Basic tests for layaway and installment plan system.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from zargar.customers.layaway_models import (
    LayawayPlan, LayawayScheduledPayment, LayawayPayment,
    LayawayContract, LayawayReminder
)
from zargar.customers.layaway_services import (
    LayawayPlanService, LayawayContractService
)


class LayawayModelBasicTest(TestCase):
    """Basic tests for LayawayPlan model."""
    
    def test_layaway_plan_creation(self):
        """Test creating a layaway plan."""
        plan = LayawayPlan(
            plan_number='TEST-001',
            total_amount=Decimal('15000000'),
            down_payment=Decimal('3000000'),
            remaining_balance=Decimal('12000000'),
            installment_amount=Decimal('2000000'),
            payment_frequency='monthly',
            number_of_payments=6,
            start_date=date.today(),
            status='active'
        )
        
        self.assertEqual(plan.total_amount, Decimal('15000000'))
        self.assertEqual(plan.down_payment, Decimal('3000000'))
        self.assertEqual(plan.remaining_balance, Decimal('12000000'))
        self.assertEqual(plan.status, 'active')
    
    def test_completion_percentage_calculation(self):
        """Test completion percentage calculation."""
        plan = LayawayPlan(
            total_amount=Decimal('10000000'),
            total_paid=Decimal('6000000')
        )
        
        self.assertEqual(plan.completion_percentage, 60.0)
    
    def test_plan_number_generation(self):
        """Test automatic plan number generation."""
        plan = LayawayPlan()
        plan_number = plan.generate_plan_number()
        
        self.assertIsNotNone(plan_number)
        self.assertTrue(plan_number.startswith('LAY-'))
        self.assertEqual(len(plan_number), 17)  # LAY-YYYYMMDD-XXXX


class LayawayScheduledPaymentTest(TestCase):
    """Test LayawayScheduledPayment model."""
    
    def test_scheduled_payment_creation(self):
        """Test creating scheduled payment."""
        payment = LayawayScheduledPayment(
            payment_number=1,
            due_date=date.today() + timedelta(days=30),
            amount=Decimal('2000000'),
            is_paid=False
        )
        
        self.assertEqual(payment.payment_number, 1)
        self.assertEqual(payment.amount, Decimal('2000000'))
        self.assertFalse(payment.is_paid)
        self.assertEqual(payment.remaining_amount, Decimal('2000000'))
    
    def test_days_overdue_calculation(self):
        """Test days overdue calculation."""
        # Create overdue payment
        overdue_date = date.today() - timedelta(days=10)
        payment = LayawayScheduledPayment(
            due_date=overdue_date,
            amount=Decimal('2000000'),
            is_paid=False
        )
        
        # Mock layaway plan with grace period
        class MockPlan:
            grace_period_days = 7
        
        payment.layaway_plan = MockPlan()
        
        self.assertEqual(payment.days_overdue, 3)  # 10 days - 7 grace period


class LayawayPaymentTest(TestCase):
    """Test LayawayPayment model."""
    
    def test_payment_creation(self):
        """Test creating payment record."""
        payment = LayawayPayment(
            amount=Decimal('2000000'),
            payment_method='cash',
            payment_date=date.today(),
            notes='Monthly payment'
        )
        
        self.assertEqual(payment.amount, Decimal('2000000'))
        self.assertEqual(payment.payment_method, 'cash')
        self.assertEqual(payment.notes, 'Monthly payment')
    
    def test_receipt_number_generation(self):
        """Test receipt number generation."""
        payment = LayawayPayment()
        receipt_number = payment.generate_receipt_number()
        
        self.assertIsNotNone(receipt_number)
        self.assertTrue(receipt_number.startswith('LAY-REC-'))


class LayawayContractTest(TestCase):
    """Test LayawayContract model."""
    
    def test_contract_creation(self):
        """Test creating contract template."""
        contract = LayawayContract(
            name='Standard Contract',
            contract_type='standard',
            persian_title='قرارداد استاندارد',
            contract_template='Contract template content',
            is_active=True,
            is_default=True
        )
        
        self.assertEqual(contract.name, 'Standard Contract')
        self.assertEqual(contract.contract_type, 'standard')
        self.assertTrue(contract.is_active)
        self.assertTrue(contract.is_default)


class LayawayReminderTest(TestCase):
    """Test LayawayReminder model."""
    
    def test_reminder_creation(self):
        """Test creating reminder."""
        reminder = LayawayReminder(
            reminder_type='upcoming',
            scheduled_date=date.today(),
            delivery_method='sms',
            recipient='09123456789',
            message_template='Payment reminder template',
            is_sent=False
        )
        
        self.assertEqual(reminder.reminder_type, 'upcoming')
        self.assertEqual(reminder.delivery_method, 'sms')
        self.assertFalse(reminder.is_sent)


class LayawayContractServiceTest(TestCase):
    """Test LayawayContractService functionality."""
    
    def test_create_default_contract_template(self):
        """Test creating default contract template."""
        contract = LayawayContractService.create_default_contract_template()
        
        self.assertIsInstance(contract, LayawayContract)
        self.assertEqual(contract.contract_type, 'standard')
        self.assertTrue(contract.is_default)
        self.assertTrue(contract.is_active)
        self.assertIn('قرارداد طلای قرضی', contract.contract_template)
    
    def test_contract_content_generation(self):
        """Test contract content generation."""
        # Create mock layaway plan
        class MockCustomer:
            full_persian_name = 'احمد محمدی'
            phone_number = '09123456789'
            address = 'تهران'
        
        class MockJewelryItem:
            name = 'انگشتر طلا'
            sku = 'RING-001'
        
        class MockPlan:
            plan_number = 'LAY-20250922-1234'
            customer = MockCustomer()
            jewelry_item = MockJewelryItem()
            total_amount = Decimal('15000000')
            down_payment = Decimal('3000000')
            installment_amount = Decimal('2000000')
            number_of_payments = 6
            start_date_shamsi = '1404/07/01'
            expected_completion_date = date.today() + timedelta(days=180)
            grace_period_days = 7
            
            def get_payment_frequency_display(self):
                return 'ماهانه'
        
        # Create contract template
        contract_template = LayawayContractService.create_default_contract_template()
        
        # Generate contract content
        content = contract_template.generate_contract(MockPlan())
        
        self.assertIn('LAY-20250922-1234', content)
        self.assertIn('احمد محمدی', content)
        self.assertIn('انگشتر طلا', content)
        self.assertIn('15000000', content)


class LayawayValidationTest(TestCase):
    """Test layaway system validation."""
    
    def test_plan_validation(self):
        """Test layaway plan validation."""
        # Test negative amounts
        with self.assertRaises(ValidationError):
            plan = LayawayPlan(
                total_amount=Decimal('-1000000'),
                down_payment=Decimal('0'),
                installment_amount=Decimal('1000000'),
                number_of_payments=1
            )
            plan.full_clean()
        
        # Test invalid payment count
        with self.assertRaises(ValidationError):
            plan = LayawayPlan(
                total_amount=Decimal('1000000'),
                down_payment=Decimal('0'),
                installment_amount=Decimal('1000000'),
                number_of_payments=0
            )
            plan.full_clean()


if __name__ == '__main__':
    pytest.main([__file__])