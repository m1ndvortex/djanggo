"""
Unit tests for gold price services.
Tests the gold price integration and payment processing services.
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, Mock
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.cache import cache

from zargar.gold_installments.services import (
    GoldPriceService, 
    PaymentProcessingService,
    GoldPriceProtectionService
)


class GoldPriceServiceTest(TestCase):
    """Test gold price service functionality."""
    
    def setUp(self):
        """Set up test data."""
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
    
    def test_parse_api_response_primary(self):
        """Test parsing primary API response."""
        data = {'price': 3500000}
        result = GoldPriceService._parse_api_response(data, 'primary', 18)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['price_per_gram'], Decimal('3500000'))
        self.assertEqual(result['karat'], 18)
    
    def test_parse_api_response_invalid_data(self):
        """Test parsing invalid API response."""
        data = {'invalid': 'data'}
        result = GoldPriceService._parse_api_response(data, 'primary', 18)
        
        self.assertIsNone(result)
    
    def test_get_fallback_price(self):
        """Test fallback price generation."""
        fallback_18k = GoldPriceService._get_fallback_price(18)
        fallback_24k = GoldPriceService._get_fallback_price(24)
        
        self.assertEqual(fallback_18k['karat'], 18)
        self.assertEqual(fallback_24k['karat'], 24)
        self.assertEqual(fallback_18k['source'], 'fallback')
        self.assertEqual(fallback_24k['source'], 'fallback')
        
        # 24k should be more expensive than 18k
        self.assertGreater(fallback_24k['price_per_gram'], fallback_18k['price_per_gram'])


class PaymentProcessingServiceTest(TestCase):
    """Test payment processing service functionality."""
    
    def test_apply_price_protection_ceiling(self):
        """Test price protection ceiling application."""
        # Mock contract with price protection
        mock_contract = Mock()
        mock_contract.has_price_protection = True
        mock_contract.price_ceiling_per_gram = Decimal('3000000')
        mock_contract.price_floor_per_gram = Decimal('2000000')
        mock_contract.contract_number = 'TEST-001'
        
        # Market price above ceiling
        market_price = Decimal('3500000')
        
        effective_price = PaymentProcessingService._apply_price_protection(
            mock_contract, market_price
        )
        
        # Should use ceiling price
        self.assertEqual(effective_price, Decimal('3000000'))
    
    def test_apply_price_protection_floor(self):
        """Test price protection floor application."""
        # Mock contract with price protection
        mock_contract = Mock()
        mock_contract.has_price_protection = True
        mock_contract.price_ceiling_per_gram = Decimal('4000000')
        mock_contract.price_floor_per_gram = Decimal('3000000')
        mock_contract.contract_number = 'TEST-001'
        
        # Market price below floor
        market_price = Decimal('2500000')
        
        effective_price = PaymentProcessingService._apply_price_protection(
            mock_contract, market_price
        )
        
        # Should use floor price
        self.assertEqual(effective_price, Decimal('3000000'))
    
    def test_apply_price_protection_no_protection(self):
        """Test when no price protection is applied."""
        # Mock contract without price protection
        mock_contract = Mock()
        mock_contract.has_price_protection = False
        
        market_price = Decimal('3500000')
        
        effective_price = PaymentProcessingService._apply_price_protection(
            mock_contract, market_price
        )
        
        # Should use market price
        self.assertEqual(effective_price, market_price)
    
    def test_calculate_payment_details_basic(self):
        """Test basic payment details calculation."""
        # Mock contract
        mock_contract = Mock()
        mock_contract.early_payment_discount_percentage = Decimal('0.00')
        mock_contract.status = 'active'
        
        payment_amount = Decimal('7000000')
        effective_price = Decimal('3500000')
        
        details = PaymentProcessingService._calculate_payment_details(
            mock_contract, payment_amount, effective_price, False
        )
        
        self.assertEqual(details['gold_weight_equivalent'], Decimal('2.000'))
        self.assertFalse(details['discount_applied'])
        self.assertEqual(details['discount_percentage'], Decimal('0.00'))
        self.assertEqual(details['discount_amount'], Decimal('0.00'))
    
    def test_calculate_payment_details_with_discount(self):
        """Test payment details calculation with early discount."""
        # Mock contract with early payment discount
        mock_contract = Mock()
        mock_contract.early_payment_discount_percentage = Decimal('5.00')
        mock_contract.status = 'active'
        mock_contract.remaining_gold_weight_grams = Decimal('2.000')
        
        # Payment amount that covers remaining balance
        payment_amount = Decimal('7000000')  # 2 grams worth
        effective_price = Decimal('3500000')
        
        details = PaymentProcessingService._calculate_payment_details(
            mock_contract, payment_amount, effective_price, True
        )
        
        self.assertTrue(details['discount_applied'])
        self.assertEqual(details['discount_percentage'], Decimal('5.00'))
        self.assertGreater(details['discount_amount'], Decimal('0.00'))


class GoldPriceProtectionServiceTest(TestCase):
    """Test gold price protection service functionality."""
    
    def test_setup_price_protection_valid(self):
        """Test valid price protection setup."""
        # Mock contract
        mock_contract = Mock()
        mock_contract.save = Mock()
        
        result = GoldPriceProtectionService.setup_price_protection(
            contract=mock_contract,
            ceiling_price=Decimal('4000000'),
            floor_price=Decimal('3000000')
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['ceiling_price'], Decimal('4000000'))
        self.assertEqual(result['floor_price'], Decimal('3000000'))
        self.assertTrue(result['protection_active'])
        
        # Verify contract was updated
        mock_contract.save.assert_called_once()
    
    def test_setup_price_protection_invalid_prices(self):
        """Test price protection setup with invalid prices."""
        mock_contract = Mock()
        
        # Test ceiling lower than floor
        with self.assertRaises(ValidationError):
            GoldPriceProtectionService.setup_price_protection(
                contract=mock_contract,
                ceiling_price=Decimal('3000000'),
                floor_price=Decimal('4000000')
            )
        
        # Test no prices provided
        with self.assertRaises(ValidationError):
            GoldPriceProtectionService.setup_price_protection(
                contract=mock_contract
            )
    
    def test_remove_price_protection(self):
        """Test removing price protection."""
        mock_contract = Mock()
        mock_contract.save = Mock()
        
        result = GoldPriceProtectionService.remove_price_protection(mock_contract)
        
        self.assertTrue(result['success'])
        self.assertFalse(result['protection_active'])
        
        # Verify contract was updated
        mock_contract.save.assert_called_once()
    
    def test_analyze_price_protection_impact_no_protection(self):
        """Test impact analysis when no protection is active."""
        mock_contract = Mock()
        mock_contract.has_price_protection = False
        
        impact = GoldPriceProtectionService.analyze_price_protection_impact(mock_contract)
        
        self.assertFalse(impact['has_protection'])
        self.assertIsNone(impact['impact_analysis'])
    
    def test_analyze_price_protection_impact_ceiling_active(self):
        """Test impact analysis when ceiling protection is active."""
        mock_contract = Mock()
        mock_contract.has_price_protection = True
        mock_contract.price_ceiling_per_gram = Decimal('3500000')
        mock_contract.price_floor_per_gram = Decimal('2500000')
        mock_contract.remaining_gold_weight_grams = Decimal('5.000')
        mock_contract.gold_karat = 18
        
        # Mock high market price
        mock_price_data = {
            'price_per_gram': Decimal('4000000'),  # Above ceiling
            'karat': 18,
            'timestamp': timezone.now(),
            'source': 'test',
            'currency': 'IRR'
        }
        
        with patch.object(GoldPriceService, 'get_current_gold_price', return_value=mock_price_data):
            impact = GoldPriceProtectionService.analyze_price_protection_impact(mock_contract)
            
            self.assertTrue(impact['has_protection'])
            self.assertTrue(impact['protection_active'])
            self.assertEqual(impact['protection_type'], 'ceiling')
            self.assertEqual(impact['market_price'], Decimal('4000000'))
            self.assertEqual(impact['effective_price'], Decimal('3500000'))
            self.assertEqual(impact['price_difference'], Decimal('500000'))
            self.assertTrue(impact['customer_benefit'])
            
            # Check value calculations
            expected_market_value = Decimal('5.000') * Decimal('4000000')
            expected_protected_value = Decimal('5.000') * Decimal('3500000')
            expected_impact = expected_market_value - expected_protected_value
            
            self.assertEqual(impact['remaining_value_market'], expected_market_value)
            self.assertEqual(impact['remaining_value_protected'], expected_protected_value)
            self.assertEqual(impact['value_impact'], expected_impact)
    
    def test_analyze_price_protection_impact_floor_active(self):
        """Test impact analysis when floor protection is active."""
        mock_contract = Mock()
        mock_contract.has_price_protection = True
        mock_contract.price_ceiling_per_gram = Decimal('4000000')
        mock_contract.price_floor_per_gram = Decimal('3000000')
        mock_contract.remaining_gold_weight_grams = Decimal('3.000')
        mock_contract.gold_karat = 18
        
        # Mock low market price
        mock_price_data = {
            'price_per_gram': Decimal('2500000'),  # Below floor
            'karat': 18,
            'timestamp': timezone.now(),
            'source': 'test',
            'currency': 'IRR'
        }
        
        with patch.object(GoldPriceService, 'get_current_gold_price', return_value=mock_price_data):
            impact = GoldPriceProtectionService.analyze_price_protection_impact(mock_contract)
            
            self.assertTrue(impact['has_protection'])
            self.assertTrue(impact['protection_active'])
            self.assertEqual(impact['protection_type'], 'floor')
            self.assertEqual(impact['market_price'], Decimal('2500000'))
            self.assertEqual(impact['effective_price'], Decimal('3000000'))
            self.assertEqual(impact['price_difference'], Decimal('-500000'))
            self.assertFalse(impact['customer_benefit'])  # Shop bears the cost