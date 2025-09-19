"""
Integration tests for gold price integration and payment processing.
Tests the complete gold installment system with real-time price integration.
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, Mock
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.cache import cache
from datetime import datetime, timedelta

from zargar.gold_installments.services import (
    GoldPriceService, 
    PaymentProcessingService,
    GoldPriceProtectionService
)
from zargar.gold_installments.models import (
    GoldInstallmentContract, 
    GoldInstallmentPayment,
    GoldWeightAdjustment
)
from zargar.gold_installments.tasks import (
    update_gold_prices,
    process_scheduled_payment,
    send_payment_reminders,
    calculate_daily_contract_metrics
)
from zargar.customers.models import Customer
from zargar.tenants.models import Tenant, Domain
from zargar.core.models import User


class GoldPriceServiceIntegrationTest(TestCase):
    """Test gold price service integration with external APIs."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Jewelry Shop",
            schema_name="test_shop",
            owner_name="Test Owner",
            owner_email="owner@test.com"
        )
        
        # Create domain for tenant
        self.domain = Domain.objects.create(
            domain="test-shop.localhost",
            tenant=self.tenant,
            is_primary=True
        )
        
        # Clear cache before each test
        cache.clear()
    
    def test_get_current_gold_price_with_cache(self):
        """Test gold price retrieval with caching mechanism."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {'price': 3500000}
        mock_response.raise_for_status.return_value = None
        
        with patch('requests.get', return_value=mock_response):
            # First call should fetch from API
            price_data = GoldPriceService.get_current_gold_price(18)
            
            self.assertEqual(price_data['price_per_gram'], Decimal('3500000'))
            self.assertEqual(price_data['karat'], 18)
            self.assertEqual(price_data['source'], 'primary')
            self.assertEqual(price_data['currency'], 'IRR')
            
            # Second call should use cache
            cached_price_data = GoldPriceService.get_current_gold_price(18)
            self.assertEqual(cached_price_data, price_data)
    
    def test_get_current_gold_price_api_fallback(self):
        """Test API fallback mechanism when primary API fails."""
        # Mock primary API failure
        with patch('requests.get', side_effect=Exception("API Error")):
            price_data = GoldPriceService.get_current_gold_price(18)
            
            # Should return fallback price
            self.assertEqual(price_data['source'], 'fallback')
            self.assertEqual(price_data['karat'], 18)
            self.assertGreater(price_data['price_per_gram'], Decimal('0'))
    
    def test_get_current_gold_price_different_karats(self):
        """Test gold price calculation for different karats."""
        mock_response = Mock()
        mock_response.json.return_value = {'price': 3600000}  # 18k base price
        mock_response.raise_for_status.return_value = None
        
        with patch('requests.get', return_value=mock_response):
            # Test 18k (base)
            price_18k = GoldPriceService.get_current_gold_price(18)
            self.assertEqual(price_18k['price_per_gram'], Decimal('3600000'))
            
            # Test 14k (should be lower)
            price_14k = GoldPriceService.get_current_gold_price(14)
            expected_14k = Decimal('3600000') * (Decimal('14') / Decimal('18'))
            self.assertEqual(price_14k['price_per_gram'], expected_14k.quantize(Decimal('0.01')))
            
            # Test 24k (should be higher)
            price_24k = GoldPriceService.get_current_gold_price(24)
            expected_24k = Decimal('3600000') * (Decimal('24') / Decimal('18'))
            self.assertEqual(price_24k['price_per_gram'], expected_24k.quantize(Decimal('0.01')))
    
    def test_get_price_trend(self):
        """Test gold price trend analysis."""
        mock_response = Mock()
        mock_response.json.return_value = {'price': 3500000}
        mock_response.raise_for_status.return_value = None
        
        with patch('requests.get', return_value=mock_response):
            trend_data = GoldPriceService.get_price_trend(18, 7)
            
            self.assertEqual(len(trend_data), 7)
            
            for day_data in trend_data:
                self.assertIn('date', day_data)
                self.assertIn('price_per_gram', day_data)
                self.assertIn('karat', day_data)
                self.assertEqual(day_data['karat'], 18)
                self.assertIsInstance(day_data['price_per_gram'], Decimal)
    
    def test_invalidate_cache(self):
        """Test cache invalidation functionality."""
        # Set up cached data
        mock_response = Mock()
        mock_response.json.return_value = {'price': 3500000}
        mock_response.raise_for_status.return_value = None
        
        with patch('requests.get', return_value=mock_response):
            # Cache price data
            GoldPriceService.get_current_gold_price(18)
            
            # Verify cache exists
            cache_key = f"{GoldPriceService.CACHE_KEY_PREFIX}_18"
            self.assertIsNotNone(cache.get(cache_key))
            
            # Invalidate cache
            GoldPriceService.invalidate_cache(18)
            
            # Verify cache is cleared
            self.assertIsNone(cache.get(cache_key))


class PaymentProcessingServiceIntegrationTest(TransactionTestCase):
    """Test payment processing service with database transactions."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Jewelry Shop",
            domain_url="test-shop",
            schema_name="test_shop"
        )
        
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            tenant=self.tenant
        )
        
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            first_name="John",
            last_name="Doe",
            persian_first_name="جان",
            persian_last_name="دو",
            phone_number="09123456789",
            email="customer@example.com"
        )
        
        self.contract = GoldInstallmentContract.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            contract_date=timezone.now().date(),
            initial_gold_weight_grams=Decimal('10.000'),
            remaining_gold_weight_grams=Decimal('10.000'),
            gold_karat=18,
            payment_schedule='monthly',
            status='active',
            contract_terms_persian="شرایط قرارداد طلای قرضی"
        )
    
    def test_process_payment_basic(self):
        """Test basic payment processing."""
        # Mock gold price
        mock_price_data = {
            'price_per_gram': Decimal('3500000'),
            'karat': 18,
            'timestamp': timezone.now(),
            'source': 'test',
            'currency': 'IRR'
        }
        
        with patch.object(GoldPriceService, 'get_current_gold_price', return_value=mock_price_data):
            result = PaymentProcessingService.process_payment(
                contract=self.contract,
                payment_amount=Decimal('7000000'),  # 2 grams worth
                payment_method='cash'
            )
            
            self.assertTrue(result['success'])
            self.assertIsInstance(result['payment'], GoldInstallmentPayment)
            
            # Check payment details
            payment = result['payment']
            self.assertEqual(payment.payment_amount_toman, Decimal('7000000'))
            self.assertEqual(payment.gold_price_per_gram_at_payment, Decimal('3500000'))
            self.assertEqual(payment.effective_gold_price_per_gram, Decimal('3500000'))
            self.assertEqual(payment.gold_weight_equivalent_grams, Decimal('2.000'))
            
            # Check contract update
            self.contract.refresh_from_db()
            self.assertEqual(self.contract.remaining_gold_weight_grams, Decimal('8.000'))
            self.assertEqual(self.contract.total_gold_weight_paid, Decimal('2.000'))
            self.assertEqual(self.contract.status, 'active')
    
    def test_process_payment_with_price_protection(self):
        """Test payment processing with price protection."""
        # Set up price protection
        self.contract.has_price_protection = True
        self.contract.price_ceiling_per_gram = Decimal('3000000')
        self.contract.price_floor_per_gram = Decimal('2000000')
        self.contract.save()
        
        # Mock high gold price (above ceiling)
        mock_price_data = {
            'price_per_gram': Decimal('3800000'),  # Above ceiling
            'karat': 18,
            'timestamp': timezone.now(),
            'source': 'test',
            'currency': 'IRR'
        }
        
        with patch.object(GoldPriceService, 'get_current_gold_price', return_value=mock_price_data):
            result = PaymentProcessingService.process_payment(
                contract=self.contract,
                payment_amount=Decimal('6000000'),  # 2 grams at ceiling price
                payment_method='cash'
            )
            
            self.assertTrue(result['success'])
            
            payment = result['payment']
            # Should use ceiling price, not market price
            self.assertEqual(payment.gold_price_per_gram_at_payment, Decimal('3800000'))
            self.assertEqual(payment.effective_gold_price_per_gram, Decimal('3000000'))
            self.assertEqual(payment.gold_weight_equivalent_grams, Decimal('2.000'))
            self.assertTrue(payment.price_protection_applied)
    
    def test_process_payment_with_early_discount(self):
        """Test payment processing with early payment discount."""
        # Set up early payment discount
        self.contract.early_payment_discount_percentage = Decimal('5.00')
        self.contract.save()
        
        # Mock gold price
        mock_price_data = {
            'price_per_gram': Decimal('3500000'),
            'karat': 18,
            'timestamp': timezone.now(),
            'source': 'test',
            'currency': 'IRR'
        }
        
        with patch.object(GoldPriceService, 'get_current_gold_price', return_value=mock_price_data):
            # Pay full remaining amount with early discount
            remaining_value = self.contract.remaining_gold_weight_grams * Decimal('3500000')
            
            result = PaymentProcessingService.process_payment(
                contract=self.contract,
                payment_amount=remaining_value,
                payment_method='cash',
                apply_early_discount=True
            )
            
            self.assertTrue(result['success'])
            
            payment = result['payment']
            self.assertTrue(payment.discount_applied)
            self.assertEqual(payment.discount_percentage, Decimal('5.00'))
            self.assertGreater(payment.discount_amount_toman, Decimal('0'))
            self.assertEqual(payment.payment_type, 'early_completion')
            
            # Contract should be completed
            self.contract.refresh_from_db()
            self.assertEqual(self.contract.status, 'completed')
            self.assertEqual(self.contract.remaining_gold_weight_grams, Decimal('0.000'))
    
    def test_process_payment_contract_completion(self):
        """Test contract completion when payment covers remaining balance."""
        # Mock gold price
        mock_price_data = {
            'price_per_gram': Decimal('3500000'),
            'karat': 18,
            'timestamp': timezone.now(),
            'source': 'test',
            'currency': 'IRR'
        }
        
        with patch.object(GoldPriceService, 'get_current_gold_price', return_value=mock_price_data):
            # Pay full remaining amount
            full_payment = self.contract.remaining_gold_weight_grams * Decimal('3500000')
            
            result = PaymentProcessingService.process_payment(
                contract=self.contract,
                payment_amount=full_payment,
                payment_method='cash'
            )
            
            self.assertTrue(result['success'])
            
            # Contract should be completed
            self.contract.refresh_from_db()
            self.assertEqual(self.contract.status, 'completed')
            self.assertEqual(self.contract.remaining_gold_weight_grams, Decimal('0.000'))
            self.assertIsNotNone(self.contract.completion_date)
    
    def test_process_bidirectional_transaction(self):
        """Test bidirectional transaction processing (debt/credit)."""
        result = PaymentProcessingService.process_bidirectional_transaction(
            contract=self.contract,
            transaction_type='debt',
            amount=Decimal('2.000'),
            description='Additional gold added to contract',
            authorized_by=self.user
        )
        
        self.assertTrue(result['success'])
        self.assertIsInstance(result['adjustment'], GoldWeightAdjustment)
        
        # Check contract balance update
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.remaining_gold_weight_grams, Decimal('12.000'))
        
        # Test credit transaction
        result = PaymentProcessingService.process_bidirectional_transaction(
            contract=self.contract,
            transaction_type='credit',
            amount=Decimal('1.000'),
            description='Gold weight reduction',
            authorized_by=self.user
        )
        
        self.assertTrue(result['success'])
        
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.remaining_gold_weight_grams, Decimal('11.000'))
    
    def test_calculate_early_payment_savings(self):
        """Test early payment savings calculation."""
        # Set up early payment discount
        self.contract.early_payment_discount_percentage = Decimal('10.00')
        self.contract.save()
        
        # Mock gold price
        mock_price_data = {
            'price_per_gram': Decimal('3500000'),
            'karat': 18,
            'timestamp': timezone.now(),
            'source': 'test',
            'currency': 'IRR'
        }
        
        with patch.object(GoldPriceService, 'get_current_gold_price', return_value=mock_price_data):
            savings = PaymentProcessingService.calculate_early_payment_savings(self.contract)
            
            self.assertTrue(savings['eligible'])
            self.assertEqual(savings['discount_percentage'], Decimal('10.00'))
            
            expected_balance_value = self.contract.remaining_gold_weight_grams * Decimal('3500000')
            self.assertEqual(savings['current_balance_value'], expected_balance_value)
            
            expected_discount = expected_balance_value * Decimal('0.10')
            self.assertEqual(savings['discount_amount'], expected_discount)
            
            expected_final_payment = expected_balance_value - expected_discount
            self.assertEqual(savings['final_payment_amount'], expected_final_payment)


class GoldPriceProtectionServiceIntegrationTest(TestCase):
    """Test gold price protection service functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Jewelry Shop",
            domain_url="test-shop",
            schema_name="test_shop"
        )
        
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            first_name="John",
            last_name="Doe",
            persian_first_name="جان",
            persian_last_name="دو",
            phone_number="09123456789"
        )
        
        self.contract = GoldInstallmentContract.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            contract_date=timezone.now().date(),
            initial_gold_weight_grams=Decimal('5.000'),
            remaining_gold_weight_grams=Decimal('5.000'),
            gold_karat=18,
            payment_schedule='monthly',
            status='active',
            contract_terms_persian="شرایط قرارداد طلای قرضی"
        )
    
    def test_setup_price_protection(self):
        """Test setting up price protection for a contract."""
        result = GoldPriceProtectionService.setup_price_protection(
            contract=self.contract,
            ceiling_price=Decimal('4000000'),
            floor_price=Decimal('3000000')
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['ceiling_price'], Decimal('4000000'))
        self.assertEqual(result['floor_price'], Decimal('3000000'))
        self.assertTrue(result['protection_active'])
        
        # Check contract update
        self.contract.refresh_from_db()
        self.assertTrue(self.contract.has_price_protection)
        self.assertEqual(self.contract.price_ceiling_per_gram, Decimal('4000000'))
        self.assertEqual(self.contract.price_floor_per_gram, Decimal('3000000'))
    
    def test_setup_price_protection_validation(self):
        """Test price protection setup validation."""
        # Test invalid ceiling/floor combination
        with self.assertRaises(ValidationError):
            GoldPriceProtectionService.setup_price_protection(
                contract=self.contract,
                ceiling_price=Decimal('3000000'),
                floor_price=Decimal('4000000')  # Floor higher than ceiling
            )
        
        # Test no prices provided
        with self.assertRaises(ValidationError):
            GoldPriceProtectionService.setup_price_protection(
                contract=self.contract
            )
    
    def test_remove_price_protection(self):
        """Test removing price protection from a contract."""
        # First set up protection
        GoldPriceProtectionService.setup_price_protection(
            contract=self.contract,
            ceiling_price=Decimal('4000000'),
            floor_price=Decimal('3000000')
        )
        
        # Then remove it
        result = GoldPriceProtectionService.remove_price_protection(self.contract)
        
        self.assertTrue(result['success'])
        self.assertFalse(result['protection_active'])
        
        # Check contract update
        self.contract.refresh_from_db()
        self.assertFalse(self.contract.has_price_protection)
        self.assertIsNone(self.contract.price_ceiling_per_gram)
        self.assertIsNone(self.contract.price_floor_per_gram)
    
    def test_analyze_price_protection_impact(self):
        """Test price protection impact analysis."""
        # Set up price protection
        GoldPriceProtectionService.setup_price_protection(
            contract=self.contract,
            ceiling_price=Decimal('3500000'),
            floor_price=Decimal('2500000')
        )
        
        # Mock high market price (above ceiling)
        mock_price_data = {
            'price_per_gram': Decimal('4000000'),  # Above ceiling
            'karat': 18,
            'timestamp': timezone.now(),
            'source': 'test',
            'currency': 'IRR'
        }
        
        with patch.object(GoldPriceService, 'get_current_gold_price', return_value=mock_price_data):
            impact = GoldPriceProtectionService.analyze_price_protection_impact(self.contract)
            
            self.assertTrue(impact['has_protection'])
            self.assertTrue(impact['protection_active'])
            self.assertEqual(impact['protection_type'], 'ceiling')
            self.assertEqual(impact['market_price'], Decimal('4000000'))
            self.assertEqual(impact['effective_price'], Decimal('3500000'))
            self.assertEqual(impact['price_difference'], Decimal('500000'))
            self.assertTrue(impact['customer_benefit'])  # Customer benefits from ceiling
            
            # Check value impact
            expected_market_value = self.contract.remaining_gold_weight_grams * Decimal('4000000')
            expected_protected_value = self.contract.remaining_gold_weight_grams * Decimal('3500000')
            expected_impact = expected_market_value - expected_protected_value
            
            self.assertEqual(impact['remaining_value_market'], expected_market_value)
            self.assertEqual(impact['remaining_value_protected'], expected_protected_value)
            self.assertEqual(impact['value_impact'], expected_impact)


class CeleryTaskIntegrationTest(TransactionTestCase):
    """Test Celery tasks for gold installment system."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Jewelry Shop",
            domain_url="test-shop",
            schema_name="test_shop"
        )
        
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            first_name="John",
            last_name="Doe",
            persian_first_name="جان",
            persian_last_name="دو",
            phone_number="09123456789"
        )
        
        self.contract = GoldInstallmentContract.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            contract_date=timezone.now().date() - timedelta(days=35),  # Overdue
            initial_gold_weight_grams=Decimal('10.000'),
            remaining_gold_weight_grams=Decimal('8.000'),
            gold_karat=18,
            payment_schedule='monthly',
            status='active',
            contract_terms_persian="شرایط قرارداد طلای قرضی"
        )
    
    def test_update_gold_prices_task(self):
        """Test gold price update task."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {'price': 3600000}
        mock_response.raise_for_status.return_value = None
        
        with patch('requests.get', return_value=mock_response):
            result = update_gold_prices.apply(args=[[18, 24]]).get()
            
            self.assertTrue(result['success'])
            self.assertIn('updated_prices', result)
            self.assertIn(18, result['updated_prices'])
            self.assertIn(24, result['updated_prices'])
    
    def test_process_scheduled_payment_task(self):
        """Test scheduled payment processing task."""
        # Mock gold price
        mock_price_data = {
            'price_per_gram': Decimal('3500000'),
            'karat': 18,
            'timestamp': timezone.now(),
            'source': 'test',
            'currency': 'IRR'
        }
        
        with patch.object(GoldPriceService, 'get_current_gold_price', return_value=mock_price_data):
            result = process_scheduled_payment.apply(
                args=[self.contract.id, Decimal('3500000'), 'auto']
            ).get()
            
            self.assertTrue(result['success'])
            self.assertEqual(result['contract_id'], self.contract.id)
            self.assertIn('payment_id', result)
            
            # Check payment was created
            payment = GoldInstallmentPayment.objects.get(id=result['payment_id'])
            self.assertEqual(payment.payment_amount_toman, Decimal('3500000'))
            self.assertEqual(payment.payment_method, 'auto')
    
    def test_send_payment_reminders_task(self):
        """Test payment reminders task."""
        result = send_payment_reminders.apply().get()
        
        self.assertTrue(result['success'])
        self.assertGreaterEqual(result['overdue_contracts_found'], 1)
        # Note: reminders_sent might be 0 if email sending fails in test environment
    
    def test_calculate_daily_contract_metrics_task(self):
        """Test daily contract metrics calculation task."""
        # Mock gold price
        mock_price_data = {
            'price_per_gram': Decimal('3500000'),
            'karat': 18,
            'timestamp': timezone.now(),
            'source': 'test',
            'currency': 'IRR'
        }
        
        with patch.object(GoldPriceService, 'get_current_gold_price', return_value=mock_price_data):
            result = calculate_daily_contract_metrics.apply().get()
            
            self.assertTrue(result['success'])
            self.assertIn('metrics', result)
            
            metrics = result['metrics']
            self.assertGreaterEqual(int(metrics['total_active_contracts']), 1)
            self.assertGreater(Decimal(metrics['total_remaining_gold_weight']), Decimal('0'))
            self.assertGreater(Decimal(metrics['total_remaining_value']), Decimal('0'))


class EndToEndIntegrationTest(TransactionTestCase):
    """End-to-end integration tests for complete gold installment workflows."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Jewelry Shop",
            domain_url="test-shop",
            schema_name="test_shop"
        )
        
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            tenant=self.tenant
        )
        
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            first_name="Ahmad",
            last_name="Rezaei",
            persian_first_name="احمد",
            persian_last_name="رضایی",
            phone_number="09123456789",
            email="ahmad@example.com"
        )
    
    def test_complete_gold_installment_workflow(self):
        """Test complete workflow from contract creation to completion."""
        # Mock gold price throughout the test
        mock_price_data = {
            'price_per_gram': Decimal('3500000'),
            'karat': 18,
            'timestamp': timezone.now(),
            'source': 'test',
            'currency': 'IRR'
        }
        
        with patch.object(GoldPriceService, 'get_current_gold_price', return_value=mock_price_data):
            # Step 1: Create contract
            contract = GoldInstallmentContract.objects.create(
                tenant=self.tenant,
                customer=self.customer,
                contract_date=timezone.now().date(),
                initial_gold_weight_grams=Decimal('10.000'),
                remaining_gold_weight_grams=Decimal('10.000'),
                gold_karat=18,
                payment_schedule='monthly',
                status='active',
                early_payment_discount_percentage=Decimal('5.00'),
                contract_terms_persian="شرایط قرارداد طلای قرضی"
            )
            
            # Step 2: Set up price protection
            GoldPriceProtectionService.setup_price_protection(
                contract=contract,
                ceiling_price=Decimal('4000000'),
                floor_price=Decimal('3000000')
            )
            
            # Step 3: Process multiple payments
            # First payment - 3 grams worth
            result1 = PaymentProcessingService.process_payment(
                contract=contract,
                payment_amount=Decimal('10500000'),  # 3 grams
                payment_method='cash',
                notes='First payment'
            )
            self.assertTrue(result1['success'])
            
            contract.refresh_from_db()
            self.assertEqual(contract.remaining_gold_weight_grams, Decimal('7.000'))
            
            # Second payment - 4 grams worth
            result2 = PaymentProcessingService.process_payment(
                contract=contract,
                payment_amount=Decimal('14000000'),  # 4 grams
                payment_method='bank_transfer',
                notes='Second payment'
            )
            self.assertTrue(result2['success'])
            
            contract.refresh_from_db()
            self.assertEqual(contract.remaining_gold_weight_grams, Decimal('3.000'))
            
            # Step 4: Calculate early payment savings
            savings = PaymentProcessingService.calculate_early_payment_savings(contract)
            self.assertTrue(savings['eligible'])
            self.assertGreater(savings['savings'], Decimal('0'))
            
            # Step 5: Complete with early payment discount
            remaining_value = contract.remaining_gold_weight_grams * Decimal('3500000')
            result3 = PaymentProcessingService.process_payment(
                contract=contract,
                payment_amount=remaining_value,
                payment_method='cash',
                apply_early_discount=True,
                notes='Final payment with early discount'
            )
            self.assertTrue(result3['success'])
            
            # Step 6: Verify contract completion
            contract.refresh_from_db()
            self.assertEqual(contract.status, 'completed')
            self.assertEqual(contract.remaining_gold_weight_grams, Decimal('0.000'))
            self.assertIsNotNone(contract.completion_date)
            
            # Step 7: Verify payment history
            payments = contract.payments.all().order_by('payment_date')
            self.assertEqual(payments.count(), 3)
            
            # Check final payment has discount
            final_payment = payments.last()
            self.assertTrue(final_payment.discount_applied)
            self.assertEqual(final_payment.discount_percentage, Decimal('5.00'))
            self.assertGreater(final_payment.discount_amount_toman, Decimal('0'))
            
            # Step 8: Verify total payments and weights
            total_paid_amount = sum(p.payment_amount_toman for p in payments)
            total_gold_weight = sum(p.gold_weight_equivalent_grams for p in payments)
            
            self.assertGreater(total_paid_amount, Decimal('0'))
            self.assertEqual(total_gold_weight, contract.initial_gold_weight_grams)
    
    def test_contract_with_adjustments_workflow(self):
        """Test workflow with manual weight adjustments."""
        # Mock gold price
        mock_price_data = {
            'price_per_gram': Decimal('3500000'),
            'karat': 18,
            'timestamp': timezone.now(),
            'source': 'test',
            'currency': 'IRR'
        }
        
        with patch.object(GoldPriceService, 'get_current_gold_price', return_value=mock_price_data):
            # Create contract
            contract = GoldInstallmentContract.objects.create(
                tenant=self.tenant,
                customer=self.customer,
                contract_date=timezone.now().date(),
                initial_gold_weight_grams=Decimal('5.000'),
                remaining_gold_weight_grams=Decimal('5.000'),
                gold_karat=18,
                payment_schedule='monthly',
                status='active',
                contract_terms_persian="شرایط قرارداد طلای قرضی"
            )
            
            # Make initial payment
            PaymentProcessingService.process_payment(
                contract=contract,
                payment_amount=Decimal('7000000'),  # 2 grams
                payment_method='cash'
            )
            
            contract.refresh_from_db()
            self.assertEqual(contract.remaining_gold_weight_grams, Decimal('3.000'))
            
            # Add manual adjustment (customer brings additional gold)
            PaymentProcessingService.process_bidirectional_transaction(
                contract=contract,
                transaction_type='debt',
                amount=Decimal('1.500'),
                description='Customer added additional gold jewelry',
                authorized_by=self.user
            )
            
            contract.refresh_from_db()
            self.assertEqual(contract.remaining_gold_weight_grams, Decimal('4.500'))
            
            # Make correction adjustment
            PaymentProcessingService.process_bidirectional_transaction(
                contract=contract,
                transaction_type='credit',
                amount=Decimal('0.200'),
                description='Weight measurement correction',
                authorized_by=self.user
            )
            
            contract.refresh_from_db()
            self.assertEqual(contract.remaining_gold_weight_grams, Decimal('4.300'))
            
            # Complete the contract
            remaining_value = contract.remaining_gold_weight_grams * Decimal('3500000')
            PaymentProcessingService.process_payment(
                contract=contract,
                payment_amount=remaining_value,
                payment_method='cash'
            )
            
            contract.refresh_from_db()
            self.assertEqual(contract.status, 'completed')
            
            # Verify adjustment history
            adjustments = contract.weight_adjustments.all()
            self.assertEqual(adjustments.count(), 2)
            
            debt_adjustment = adjustments.filter(adjustment_type='increase').first()
            self.assertEqual(debt_adjustment.adjustment_amount_grams, Decimal('1.500'))
            
            credit_adjustment = adjustments.filter(adjustment_type='decrease').first()
            self.assertEqual(credit_adjustment.adjustment_amount_grams, Decimal('-0.200'))