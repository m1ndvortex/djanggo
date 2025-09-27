"""
Unit tests for gold installment models.
Tests weight-based calculations, payment processing, and audit trail functionality.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from zargar.tenants.models import Tenant, Domain
from zargar.customers.models import Customer
from zargar.gold_installments.models import (
    GoldInstallmentContract, 
    GoldInstallmentPayment, 
    GoldWeightAdjustment
)

User = get_user_model()


class GoldInstallmentModelsTestCase(TenantTestCase):
    """Test case for gold installment models with tenant isolation."""
    
    @classmethod
    def setUpClass(cls):
        """Set up tenant for testing."""
        super().setUpClass()
        
        # Create tenant
        cls.tenant = Tenant(
            schema_name='test_jewelry_shop',
            name='Test Jewelry Shop',
            paid_until='2024-12-31',
            on_trial=False
        )
        cls.tenant.save()
        
        # Create domain
        cls.domain = Domain(
            domain='testshop.localhost',
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
        
        # Set tenant for test
        cls.tenant_client = TenantClient(cls.tenant)
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testowner',
            email='owner@testshop.com',
            password='testpass123',
            role='owner',
            first_name='Test',
            last_name='Owner'
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            first_name='Ahmad',
            last_name='Rezaei',
            persian_first_name='احمد',
            persian_last_name='رضایی',
            phone_number='09123456789',
            email='ahmad@example.com'
        )
        
        # Test data
        self.test_contract_data = {
            'customer': self.customer,
            'contract_date': date.today(),
            'initial_gold_weight_grams': Decimal('10.500'),
            'gold_karat': 18,
            'payment_schedule': 'monthly',
            'contract_terms_persian': 'شرایط قرارداد طلای قرضی'
        }
        
        self.test_gold_price = Decimal('3500000.00')  # 3.5 million Toman per gram
    
    def test_contract_creation(self):
        """Test gold installment contract creation."""
        contract = GoldInstallmentContract.objects.create(**self.test_contract_data)
        
        # Test basic fields
        self.assertEqual(contract.customer, self.customer)
        self.assertEqual(contract.initial_gold_weight_grams, Decimal('10.500'))
        self.assertEqual(contract.remaining_gold_weight_grams, Decimal('10.500'))
        self.assertEqual(contract.gold_karat, 18)
        self.assertEqual(contract.status, 'active')
        self.assertEqual(contract.balance_type, 'debt')
        
        # Test auto-generated fields
        self.assertTrue(contract.contract_number.startswith('GIC-'))
        self.assertIsNotNone(contract.contract_date_shamsi)
        
        # Test string representation
        self.assertIn(contract.contract_number, str(contract))
        self.assertIn('احمد رضایی', str(contract))
    
    def test_contract_number_generation(self):
        """Test unique contract number generation."""
        contract1 = GoldInstallmentContract.objects.create(**self.test_contract_data)
        contract2 = GoldInstallmentContract.objects.create(**self.test_contract_data)
        
        self.assertNotEqual(contract1.contract_number, contract2.contract_number)
        self.assertTrue(contract1.contract_number.startswith('GIC-'))
        self.assertTrue(contract2.contract_number.startswith('GIC-'))
    
    def test_contract_validation(self):
        """Test contract validation rules."""
        # Test remaining weight exceeds initial weight
        with self.assertRaises(ValidationError):
            contract = GoldInstallmentContract(**self.test_contract_data)
            contract.remaining_gold_weight_grams = Decimal('15.000')  # More than initial
            contract.full_clean()
        
        # Test price protection validation
        contract_data = self.test_contract_data.copy()
        contract_data['has_price_protection'] = True
        
        with self.assertRaises(ValidationError):
            contract = GoldInstallmentContract(**contract_data)
            contract.full_clean()  # Should fail - no price ceiling or floor set
        
        # Test price ceiling lower than floor
        contract_data['price_ceiling_per_gram'] = Decimal('3000000.00')
        contract_data['price_floor_per_gram'] = Decimal('4000000.00')
        
        with self.assertRaises(ValidationError):
            contract = GoldInstallmentContract(**contract_data)
            contract.full_clean()
    
    def test_contract_properties(self):
        """Test contract calculated properties."""
        contract = GoldInstallmentContract.objects.create(**self.test_contract_data)
        
        # Test completion percentage (initially 0%)
        self.assertEqual(contract.completion_percentage, Decimal('0.00'))
        
        # Test is_completed (initially False)
        self.assertFalse(contract.is_completed)
        
        # Simulate partial payment
        contract.remaining_gold_weight_grams = Decimal('5.250')  # Half paid
        contract.save()
        
        self.assertEqual(contract.completion_percentage, Decimal('50.00'))
        self.assertFalse(contract.is_completed)
        
        # Simulate full payment
        contract.remaining_gold_weight_grams = Decimal('0.000')
        contract.save()
        
        self.assertEqual(contract.completion_percentage, Decimal('100.00'))
        self.assertTrue(contract.is_completed)
    
    def test_gold_value_calculation(self):
        """Test gold value calculation with price protection."""
        contract = GoldInstallmentContract.objects.create(**self.test_contract_data)
        
        # Test basic calculation
        value_info = contract.calculate_current_gold_value(self.test_gold_price)
        
        expected_total_value = Decimal('10.500') * self.test_gold_price
        expected_pure_gold_weight = (Decimal('10.500') * 18) / 24  # 18k gold
        expected_pure_gold_value = expected_pure_gold_weight * self.test_gold_price
        
        self.assertEqual(value_info['remaining_weight_grams'], Decimal('10.500'))
        self.assertEqual(value_info['pure_gold_weight_grams'], expected_pure_gold_weight)
        self.assertEqual(value_info['effective_price_per_gram'], self.test_gold_price)
        self.assertEqual(value_info['total_value_toman'], expected_total_value)
        self.assertEqual(value_info['pure_gold_value_toman'], expected_pure_gold_value)
        self.assertFalse(value_info['price_protection_applied'])
    
    def test_price_protection(self):
        """Test price protection functionality."""
        contract_data = self.test_contract_data.copy()
        contract_data.update({
            'has_price_protection': True,
            'price_ceiling_per_gram': Decimal('4000000.00'),  # 4M ceiling
            'price_floor_per_gram': Decimal('3000000.00')     # 3M floor
        })
        
        contract = GoldInstallmentContract.objects.create(**contract_data)
        
        # Test price ceiling protection
        high_price = Decimal('5000000.00')  # Above ceiling
        value_info = contract.calculate_current_gold_value(high_price)
        
        self.assertEqual(value_info['effective_price_per_gram'], Decimal('4000000.00'))
        self.assertTrue(value_info['price_protection_applied'])
        
        # Test price floor protection
        low_price = Decimal('2000000.00')  # Below floor
        value_info = contract.calculate_current_gold_value(low_price)
        
        self.assertEqual(value_info['effective_price_per_gram'], Decimal('3000000.00'))
        self.assertTrue(value_info['price_protection_applied'])
        
        # Test normal price (within range)
        normal_price = Decimal('3500000.00')
        value_info = contract.calculate_current_gold_value(normal_price)
        
        self.assertEqual(value_info['effective_price_per_gram'], normal_price)
        self.assertFalse(value_info['price_protection_applied'])
    
    def test_early_payment_discount(self):
        """Test early payment discount calculation."""
        contract_data = self.test_contract_data.copy()
        contract_data['early_payment_discount_percentage'] = Decimal('5.00')  # 5% discount
        
        contract = GoldInstallmentContract.objects.create(**contract_data)
        
        discount_info = contract.calculate_early_payment_discount(self.test_gold_price)
        
        expected_original_value = Decimal('10.500') * self.test_gold_price
        expected_discount_amount = expected_original_value * Decimal('0.05')
        expected_discounted_value = expected_original_value - expected_discount_amount
        
        self.assertEqual(discount_info['original_value'], expected_original_value)
        self.assertEqual(discount_info['discount_percentage'], Decimal('5.00'))
        self.assertEqual(discount_info['discount_amount'], expected_discount_amount)
        self.assertEqual(discount_info['discounted_value'], expected_discounted_value)
        self.assertEqual(discount_info['savings'], expected_discount_amount)
    
    def test_payment_processing(self):
        """Test payment processing and contract updates."""
        contract = GoldInstallmentContract.objects.create(**self.test_contract_data)
        
        # Process a payment
        payment_amount = Decimal('17500000.00')  # 17.5M Toman
        payment = contract.process_payment(payment_amount, self.test_gold_price)
        
        # Test payment creation
        self.assertIsInstance(payment, GoldInstallmentPayment)
        self.assertEqual(payment.payment_amount_toman, payment_amount)
        self.assertEqual(payment.gold_price_per_gram_at_payment, self.test_gold_price)
        self.assertEqual(payment.effective_gold_price_per_gram, self.test_gold_price)
        
        # Calculate expected gold weight equivalent
        expected_gold_weight = payment_amount / self.test_gold_price
        self.assertEqual(payment.gold_weight_equivalent_grams, expected_gold_weight)
        
        # Test contract updates
        contract.refresh_from_db()
        expected_remaining = Decimal('10.500') - expected_gold_weight
        self.assertEqual(contract.remaining_gold_weight_grams, expected_remaining)
        self.assertEqual(contract.total_payments_received, payment_amount)
        self.assertEqual(contract.total_gold_weight_paid, expected_gold_weight)
    
    def test_contract_completion_via_payment(self):
        """Test contract completion through payment processing."""
        contract = GoldInstallmentContract.objects.create(**self.test_contract_data)
        
        # Make a payment that completes the contract
        total_value = Decimal('10.500') * self.test_gold_price
        payment = contract.process_payment(total_value, self.test_gold_price)
        
        # Test contract completion
        contract.refresh_from_db()
        self.assertEqual(contract.status, 'completed')
        self.assertEqual(contract.remaining_gold_weight_grams, Decimal('0.000'))
        self.assertIsNotNone(contract.completion_date)
        self.assertTrue(contract.is_completed)
    
    def test_payment_creation(self):
        """Test gold installment payment creation."""
        contract = GoldInstallmentContract.objects.create(**self.test_contract_data)
        
        payment_data = {
            'contract': contract,
            'payment_date': date.today(),
            'payment_amount_toman': Decimal('7000000.00'),
            'gold_price_per_gram_at_payment': self.test_gold_price,
            'effective_gold_price_per_gram': self.test_gold_price,
            'payment_method': 'cash'
        }
        
        payment = GoldInstallmentPayment.objects.create(**payment_data)
        
        # Test basic fields
        self.assertEqual(payment.contract, contract)
        self.assertEqual(payment.payment_amount_toman, Decimal('7000000.00'))
        self.assertEqual(payment.gold_price_per_gram_at_payment, self.test_gold_price)
        self.assertEqual(payment.payment_method, 'cash')
        
        # Test auto-calculated fields
        expected_gold_weight = Decimal('7000000.00') / self.test_gold_price
        self.assertEqual(payment.gold_weight_equivalent_grams, expected_gold_weight)
        self.assertIsNotNone(payment.payment_date_shamsi)
        
        # Test string representation
        self.assertIn(contract.contract_number, str(payment))
        self.assertIn('۷،۰۰۰،۰۰۰ تومان', str(payment))
    
    def test_payment_validation(self):
        """Test payment validation rules."""
        contract = GoldInstallmentContract.objects.create(**self.test_contract_data)
        
        # Test zero gold price
        with self.assertRaises(ValidationError):
            payment = GoldInstallmentPayment(
                contract=contract,
                payment_date=date.today(),
                payment_amount_toman=Decimal('1000000.00'),
                gold_price_per_gram_at_payment=Decimal('0.00'),
                effective_gold_price_per_gram=Decimal('0.00')
            )
            payment.full_clean()
        
        # Test discount validation
        with self.assertRaises(ValidationError):
            payment = GoldInstallmentPayment(
                contract=contract,
                payment_date=date.today(),
                payment_amount_toman=Decimal('1000000.00'),
                gold_price_per_gram_at_payment=self.test_gold_price,
                effective_gold_price_per_gram=self.test_gold_price,
                discount_applied=True,
                discount_percentage=Decimal('0.00')  # Should be > 0 if discount applied
            )
            payment.full_clean()
    
    def test_payment_properties(self):
        """Test payment calculated properties."""
        contract = GoldInstallmentContract.objects.create(**self.test_contract_data)
        
        # Test without price protection
        payment = GoldInstallmentPayment.objects.create(
            contract=contract,
            payment_date=date.today(),
            payment_amount_toman=Decimal('3500000.00'),
            gold_price_per_gram_at_payment=self.test_gold_price,
            effective_gold_price_per_gram=self.test_gold_price
        )
        
        self.assertFalse(payment.price_protection_applied)
        
        # Test with price protection
        payment_with_protection = GoldInstallmentPayment.objects.create(
            contract=contract,
            payment_date=date.today(),
            payment_amount_toman=Decimal('3500000.00'),
            gold_price_per_gram_at_payment=Decimal('5000000.00'),  # Market price
            effective_gold_price_per_gram=Decimal('4000000.00')    # Protected price
        )
        
        self.assertTrue(payment_with_protection.price_protection_applied)
    
    def test_weight_adjustment_creation(self):
        """Test gold weight adjustment creation."""
        contract = GoldInstallmentContract.objects.create(**self.test_contract_data)
        
        adjustment_data = {
            'contract': contract,
            'adjustment_date': date.today(),
            'weight_before_grams': contract.remaining_gold_weight_grams,
            'adjustment_amount_grams': Decimal('-0.500'),  # Decrease by 0.5g
            'adjustment_type': 'correction',
            'adjustment_reason': 'calculation_error',
            'description': 'Correction for calculation error in initial weight',
            'authorized_by': self.user
        }
        
        adjustment = GoldWeightAdjustment.objects.create(**adjustment_data)
        
        # Test basic fields
        self.assertEqual(adjustment.contract, contract)
        self.assertEqual(adjustment.weight_before_grams, Decimal('10.500'))
        self.assertEqual(adjustment.adjustment_amount_grams, Decimal('-0.500'))
        self.assertEqual(adjustment.weight_after_grams, Decimal('10.000'))
        self.assertEqual(adjustment.authorized_by, self.user)
        
        # Test auto-generated fields
        self.assertIsNotNone(adjustment.adjustment_date_shamsi)
        
        # Test contract update
        contract.refresh_from_db()
        self.assertEqual(contract.remaining_gold_weight_grams, Decimal('10.000'))
    
    def test_weight_adjustment_validation(self):
        """Test weight adjustment validation rules."""
        contract = GoldInstallmentContract.objects.create(**self.test_contract_data)
        
        # Test negative weight result
        with self.assertRaises(ValidationError):
            adjustment = GoldWeightAdjustment(
                contract=contract,
                adjustment_date=date.today(),
                weight_before_grams=Decimal('1.000'),
                adjustment_amount_grams=Decimal('-2.000'),  # Would result in -1.000
                adjustment_type='correction',
                adjustment_reason='other',
                description='Test adjustment',
                authorized_by=self.user
            )
            adjustment.full_clean()
        
        # Test reversal validation
        with self.assertRaises(ValidationError):
            adjustment = GoldWeightAdjustment(
                contract=contract,
                adjustment_date=date.today(),
                weight_before_grams=Decimal('10.000'),
                adjustment_amount_grams=Decimal('1.000'),
                adjustment_type='correction',
                adjustment_reason='other',
                description='Test adjustment',
                authorized_by=self.user,
                is_reversed=True  # Missing reversed_by and reversal_reason
            )
            adjustment.full_clean()
    
    def test_weight_adjustment_properties(self):
        """Test weight adjustment calculated properties."""
        contract = GoldInstallmentContract.objects.create(**self.test_contract_data)
        
        # Test increase adjustment
        increase_adjustment = GoldWeightAdjustment.objects.create(
            contract=contract,
            adjustment_date=date.today(),
            weight_before_grams=Decimal('10.000'),
            adjustment_amount_grams=Decimal('0.500'),
            adjustment_type='correction',
            adjustment_reason='other',
            description='Increase adjustment',
            authorized_by=self.user
        )
        
        self.assertTrue(increase_adjustment.is_increase)
        self.assertFalse(increase_adjustment.is_decrease)
        
        # Test decrease adjustment
        decrease_adjustment = GoldWeightAdjustment.objects.create(
            contract=contract,
            adjustment_date=date.today(),
            weight_before_grams=Decimal('10.500'),
            adjustment_amount_grams=Decimal('-0.250'),
            adjustment_type='correction',
            adjustment_reason='other',
            description='Decrease adjustment',
            authorized_by=self.user
        )
        
        self.assertFalse(decrease_adjustment.is_increase)
        self.assertTrue(decrease_adjustment.is_decrease)
    
    def test_weight_adjustment_reversal(self):
        """Test weight adjustment reversal functionality."""
        contract = GoldInstallmentContract.objects.create(**self.test_contract_data)
        
        # Create original adjustment
        original_adjustment = GoldWeightAdjustment.objects.create(
            contract=contract,
            adjustment_date=date.today(),
            weight_before_grams=Decimal('10.500'),
            adjustment_amount_grams=Decimal('-1.000'),
            adjustment_type='correction',
            adjustment_reason='calculation_error',
            description='Original adjustment',
            authorized_by=self.user
        )
        
        # Test reversal
        reversal_adjustment = original_adjustment.reverse_adjustment(
            self.user, 
            'Adjustment was incorrect'
        )
        
        # Test original adjustment is marked as reversed
        original_adjustment.refresh_from_db()
        self.assertTrue(original_adjustment.is_reversed)
        self.assertEqual(original_adjustment.reversed_by, self.user)
        self.assertIsNotNone(original_adjustment.reversal_date)
        self.assertEqual(original_adjustment.reversal_reason, 'Adjustment was incorrect')
        
        # Test reversal adjustment
        self.assertEqual(reversal_adjustment.adjustment_amount_grams, Decimal('1.000'))  # Opposite
        self.assertEqual(reversal_adjustment.related_adjustment, original_adjustment)
        self.assertEqual(reversal_adjustment.adjustment_type, 'correction')
        
        # Test contract weight is restored
        contract.refresh_from_db()
        self.assertEqual(contract.remaining_gold_weight_grams, Decimal('10.500'))  # Back to original
        
        # Test cannot reverse already reversed adjustment
        with self.assertRaises(ValidationError):
            original_adjustment.reverse_adjustment(self.user, 'Test')
    
    def test_payment_history_summary(self):
        """Test payment history summary calculation."""
        contract = GoldInstallmentContract.objects.create(**self.test_contract_data)
        
        # Create multiple payments
        payments_data = [
            (Decimal('3500000.00'), date.today() - timedelta(days=30)),
            (Decimal('7000000.00'), date.today() - timedelta(days=15)),
            (Decimal('1750000.00'), date.today())
        ]
        
        for amount, payment_date in payments_data:
            contract.process_payment(amount, self.test_gold_price, payment_date)
        
        summary = contract.get_payment_history_summary()
        
        self.assertEqual(summary['total_payments'], 3)
        self.assertEqual(summary['total_amount_paid'], Decimal('12250000.00'))
        self.assertEqual(summary['average_payment_amount'], Decimal('4083333.33'))
        self.assertEqual(summary['last_payment_date'], date.today())
        self.assertEqual(summary['first_payment_date'], date.today() - timedelta(days=30))
    
    def test_persian_formatting(self):
        """Test Persian number formatting in display methods."""
        contract = GoldInstallmentContract.objects.create(**self.test_contract_data)
        
        # Test contract formatting
        contract_display = contract.format_for_display()
        
        self.assertIn('۱۰٫۵۰۰ گرم', contract_display['initial_weight_display'])
        self.assertIn('۱۰٫۵۰۰ گرم', contract_display['remaining_weight_display'])
        self.assertIn('۰٪', contract_display['completion_percentage_display'])
        
        # Test payment formatting
        payment = contract.process_payment(Decimal('3500000.00'), self.test_gold_price)
        payment_display = payment.format_for_display()
        
        self.assertIn('۳،۵۰۰،۰۰۰ تومان', payment_display['payment_amount_display'])
        self.assertIn('۱٫۰۰۰ گرم', payment_display['gold_weight_display'])
        
        # Test adjustment formatting
        adjustment = GoldWeightAdjustment.objects.create(
            contract=contract,
            adjustment_date=date.today(),
            weight_before_grams=contract.remaining_gold_weight_grams,
            adjustment_amount_grams=Decimal('0.500'),
            adjustment_type='correction',
            adjustment_reason='other',
            description='Test adjustment',
            authorized_by=self.user
        )
        
        adjustment_display = adjustment.format_for_display()
        self.assertIn('گرم', adjustment_display['adjustment_amount_display'])
        self.assertTrue(adjustment_display['is_increase'])
    
    def test_overdue_detection(self):
        """Test overdue payment detection."""
        contract = GoldInstallmentContract.objects.create(**self.test_contract_data)
        
        # New contract should not be overdue initially
        self.assertFalse(contract.is_overdue)
        
        # Create old contract (simulate old contract date)
        old_contract_data = self.test_contract_data.copy()
        old_contract_data['contract_date'] = date.today() - timedelta(days=45)
        old_contract = GoldInstallmentContract.objects.create(**old_contract_data)
        
        # Old contract with no payments should be overdue
        self.assertTrue(old_contract.is_overdue)
        
        # Make a recent payment
        recent_payment_date = date.today() - timedelta(days=5)
        old_contract.process_payment(Decimal('1000000.00'), self.test_gold_price, recent_payment_date)
        
        # Should not be overdue with recent payment
        self.assertFalse(old_contract.is_overdue)
    
    def test_next_payment_date_calculation(self):
        """Test next payment date calculation based on schedule."""
        contract = GoldInstallmentContract.objects.create(**self.test_contract_data)
        
        last_payment_date = date.today()
        
        # Test weekly schedule
        contract.payment_schedule = 'weekly'
        next_date = contract.calculate_next_payment_date(last_payment_date)
        expected_date = last_payment_date + timedelta(weeks=1)
        self.assertEqual(next_date, expected_date)
        
        # Test bi-weekly schedule
        contract.payment_schedule = 'bi_weekly'
        next_date = contract.calculate_next_payment_date(last_payment_date)
        expected_date = last_payment_date + timedelta(weeks=2)
        self.assertEqual(next_date, expected_date)
        
        # Test monthly schedule
        contract.payment_schedule = 'monthly'
        next_date = contract.calculate_next_payment_date(last_payment_date)
        expected_date = last_payment_date + timedelta(days=30)
        self.assertEqual(next_date, expected_date)


@pytest.mark.django_db
class GoldInstallmentCalculationTests(TestCase):
    """Focused tests for gold weight calculations and business logic."""
    
    def test_pure_gold_weight_calculation(self):
        """Test pure gold weight calculation based on karat."""
        # Test 18k gold (75% pure)
        total_weight = Decimal('10.000')
        karat = 18
        expected_pure_weight = (total_weight * karat) / 24
        
        self.assertEqual(expected_pure_weight, Decimal('7.500'))
        
        # Test 22k gold (91.67% pure)
        karat = 22
        expected_pure_weight = (total_weight * karat) / 24
        
        self.assertEqual(expected_pure_weight, Decimal('9.166666666666666666666666667'))
        
        # Test 24k gold (100% pure)
        karat = 24
        expected_pure_weight = (total_weight * karat) / 24
        
        self.assertEqual(expected_pure_weight, Decimal('10.000'))
    
    def test_payment_to_gold_weight_conversion(self):
        """Test conversion of payment amount to gold weight equivalent."""
        payment_amount = Decimal('3500000.00')  # 3.5M Toman
        gold_price_per_gram = Decimal('3500000.00')  # 3.5M per gram
        
        expected_gold_weight = payment_amount / gold_price_per_gram
        self.assertEqual(expected_gold_weight, Decimal('1.000'))
        
        # Test with different price
        gold_price_per_gram = Decimal('7000000.00')  # 7M per gram
        expected_gold_weight = payment_amount / gold_price_per_gram
        self.assertEqual(expected_gold_weight, Decimal('0.500'))
    
    def test_percentage_calculations(self):
        """Test percentage calculations for completion and discounts."""
        initial_weight = Decimal('10.000')
        
        # Test 25% completion
        remaining_weight = Decimal('7.500')
        paid_weight = initial_weight - remaining_weight
        completion_percentage = (paid_weight / initial_weight) * 100
        
        self.assertEqual(completion_percentage, Decimal('25.00'))
        
        # Test 100% completion
        remaining_weight = Decimal('0.000')
        paid_weight = initial_weight - remaining_weight
        completion_percentage = (paid_weight / initial_weight) * 100
        
        self.assertEqual(completion_percentage, Decimal('100.00'))
        
        # Test discount calculation
        total_value = Decimal('35000000.00')  # 35M Toman
        discount_percentage = Decimal('5.00')  # 5%
        discount_amount = total_value * (discount_percentage / 100)
        
        self.assertEqual(discount_amount, Decimal('1750000.00'))  # 1.75M Toman
    
    def test_precision_handling(self):
        """Test decimal precision handling in calculations."""
        # Test weight precision (3 decimal places)
        weight = Decimal('10.123456')
        rounded_weight = weight.quantize(Decimal('0.001'))
        
        self.assertEqual(rounded_weight, Decimal('10.123'))
        
        # Test currency precision (2 decimal places)
        amount = Decimal('3500000.999')
        rounded_amount = amount.quantize(Decimal('0.01'))
        
        self.assertEqual(rounded_amount, Decimal('3500001.00'))
        
        # Test percentage precision (2 decimal places)
        percentage = Decimal('33.333333')
        rounded_percentage = percentage.quantize(Decimal('0.01'))
        
        self.assertEqual(rounded_percentage, Decimal('33.33'))