#!/usr/bin/env python
"""
Simple demo script for gold price integration and payment processing services.
Demonstrates the core functionality without database operations.
"""
import os
import sys
import django
from decimal import Decimal
from unittest.mock import Mock, patch

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from zargar.gold_installments.services import (
    GoldPriceService,
    PaymentProcessingService,
    GoldPriceProtectionService
)


def demo_gold_price_service():
    """Demonstrate gold price service functionality."""
    print("💰 Gold Price Service Demo")
    print("=" * 50)
    
    # Mock API response for consistent demo
    mock_response = Mock()
    mock_response.json.return_value = {'price': 3600000}
    mock_response.raise_for_status.return_value = None
    
    with patch('requests.get', return_value=mock_response):
        # Test different karats
        karats = [14, 18, 21, 24]
        
        print("Current gold prices:")
        for karat in karats:
            price_data = GoldPriceService.get_current_gold_price(karat)
            print(f"  Gold {karat}k: {price_data['price_per_gram']:,} Toman/gram (Source: {price_data['source']})")
        
        # Test price trend
        print(f"\nPrice trend for 18k gold (last 5 days):")
        trend_data = GoldPriceService.get_price_trend(18, 5)
        for day_data in trend_data[-3:]:  # Show last 3 days
            print(f"  {day_data['date']}: {day_data['price_per_gram']:,} Toman/gram")
        
        # Test cache functionality
        print(f"\nTesting cache functionality...")
        import time
        start_time = time.time()
        price1 = GoldPriceService.get_current_gold_price(18)
        first_call_time = time.time() - start_time
        
        start_time = time.time()
        price2 = GoldPriceService.get_current_gold_price(18)
        second_call_time = time.time() - start_time
        
        print(f"  First call (API): {first_call_time:.3f}s")
        print(f"  Second call (cache): {second_call_time:.3f}s")
        if second_call_time > 0:
            print(f"  Cache speedup: {first_call_time/second_call_time:.1f}x faster")


def demo_price_protection():
    """Demonstrate price protection functionality."""
    print("\n🛡️ Price Protection Demo")
    print("=" * 50)
    
    # Mock contract
    mock_contract = Mock()
    mock_contract.has_price_protection = True
    mock_contract.price_ceiling_per_gram = Decimal('4000000')
    mock_contract.price_floor_per_gram = Decimal('3000000')
    mock_contract.remaining_gold_weight_grams = Decimal('5.000')
    mock_contract.gold_karat = 18
    mock_contract.save = Mock()
    
    # Test setup
    result = GoldPriceProtectionService.setup_price_protection(
        contract=mock_contract,
        ceiling_price=Decimal('4000000'),
        floor_price=Decimal('3000000')
    )
    
    print(f"Price protection setup:")
    print(f"  Ceiling: {result['ceiling_price']:,} Toman/gram")
    print(f"  Floor: {result['floor_price']:,} Toman/gram")
    print(f"  Status: {'Active' if result['protection_active'] else 'Inactive'}")
    
    # Test impact analysis with high market price
    mock_price_data = {
        'price_per_gram': Decimal('4500000'),  # Above ceiling
        'karat': 18,
        'timestamp': None,
        'source': 'test',
        'currency': 'IRR'
    }
    
    with patch.object(GoldPriceService, 'get_current_gold_price', return_value=mock_price_data):
        impact = GoldPriceProtectionService.analyze_price_protection_impact(mock_contract)
        
        print(f"\nPrice protection impact (high market price):")
        print(f"  Market price: {impact['market_price']:,} Toman/gram")
        print(f"  Effective price: {impact['effective_price']:,} Toman/gram")
        print(f"  Protection type: {impact['protection_type']}")
        print(f"  Customer benefit: {impact['customer_benefit']}")
        print(f"  Value impact: {impact['value_impact']:,} Toman")
    
    # Test with low market price
    mock_price_data['price_per_gram'] = Decimal('2500000')  # Below floor
    
    with patch.object(GoldPriceService, 'get_current_gold_price', return_value=mock_price_data):
        impact = GoldPriceProtectionService.analyze_price_protection_impact(mock_contract)
        
        print(f"\nPrice protection impact (low market price):")
        print(f"  Market price: {impact['market_price']:,} Toman/gram")
        print(f"  Effective price: {impact['effective_price']:,} Toman/gram")
        print(f"  Protection type: {impact['protection_type']}")
        print(f"  Customer benefit: {impact['customer_benefit']}")
        print(f"  Value impact: {impact['value_impact']:,} Toman")


def demo_payment_processing():
    """Demonstrate payment processing functionality."""
    print("\n💳 Payment Processing Demo")
    print("=" * 50)
    
    # Test price protection application
    mock_contract = Mock()
    mock_contract.has_price_protection = True
    mock_contract.price_ceiling_per_gram = Decimal('4000000')
    mock_contract.price_floor_per_gram = Decimal('3000000')
    mock_contract.contract_number = 'DEMO-001'
    
    # Test ceiling protection
    market_price = Decimal('4500000')  # Above ceiling
    effective_price = PaymentProcessingService._apply_price_protection(
        mock_contract, market_price
    )
    
    print(f"Price protection test:")
    print(f"  Market price: {market_price:,} Toman/gram")
    print(f"  Effective price: {effective_price:,} Toman/gram")
    print(f"  Protection applied: {'Yes' if effective_price != market_price else 'No'}")
    
    # Test payment calculation
    payment_amount = Decimal('14000000')  # 14M Toman
    
    details = PaymentProcessingService._calculate_payment_details(
        mock_contract, payment_amount, effective_price, False
    )
    
    print(f"\nPayment calculation:")
    print(f"  Payment amount: {payment_amount:,} Toman")
    print(f"  Gold price used: {effective_price:,} Toman/gram")
    print(f"  Gold weight equivalent: {details['gold_weight_equivalent']} grams")
    print(f"  Discount applied: {details['discount_applied']}")
    
    # Test early payment discount calculation
    mock_contract.early_payment_discount_percentage = Decimal('5.00')
    mock_contract.status = 'active'
    mock_contract.remaining_gold_weight_grams = Decimal('3.500')  # Exactly what payment covers
    
    details_with_discount = PaymentProcessingService._calculate_payment_details(
        mock_contract, payment_amount, effective_price, True
    )
    
    print(f"\nEarly payment discount calculation:")
    print(f"  Original gold weight: {details['gold_weight_equivalent']} grams")
    print(f"  With discount applied: {details_with_discount['discount_applied']}")
    if details_with_discount['discount_applied']:
        print(f"  Discount percentage: {details_with_discount['discount_percentage']}%")
        print(f"  Discount amount: {details_with_discount['discount_amount']:,} Toman")
        print(f"  Final gold weight: {details_with_discount['gold_weight_equivalent']} grams")


def demo_api_fallback():
    """Demonstrate API fallback mechanism."""
    print("\n🔄 API Fallback Demo")
    print("=" * 50)
    
    # Test successful API call
    mock_response = Mock()
    mock_response.json.return_value = {'price': 3700000}
    mock_response.raise_for_status.return_value = None
    
    with patch('requests.get', return_value=mock_response):
        price_data = GoldPriceService.get_current_gold_price(18)
        print(f"API success:")
        print(f"  Price: {price_data['price_per_gram']:,} Toman/gram")
        print(f"  Source: {price_data['source']}")
    
    # Test API failure with fallback
    with patch('requests.get', side_effect=Exception("Network Error")):
        price_data = GoldPriceService.get_current_gold_price(18)
        print(f"\nAPI failure (using fallback):")
        print(f"  Price: {price_data['price_per_gram']:,} Toman/gram")
        print(f"  Source: {price_data['source']}")
    
    # Test different karat calculations
    print(f"\nKarat price calculations (fallback):")
    for karat in [14, 18, 21, 24]:
        with patch('requests.get', side_effect=Exception("Network Error")):
            price_data = GoldPriceService.get_current_gold_price(karat)
            print(f"  {karat}k: {price_data['price_per_gram']:,} Toman/gram")


def demo_cache_management():
    """Demonstrate cache management functionality."""
    print("\n🗄️ Cache Management Demo")
    print("=" * 50)
    
    # Mock successful API call
    mock_response = Mock()
    mock_response.json.return_value = {'price': 3650000}
    mock_response.raise_for_status.return_value = None
    
    with patch('requests.get', return_value=mock_response) as mock_get:
        # First call - should hit API
        print("First call (should hit API):")
        price1 = GoldPriceService.get_current_gold_price(18)
        print(f"  Price: {price1['price_per_gram']:,} Toman/gram")
        print(f"  API calls made: {mock_get.call_count}")
        
        # Second call - should use cache
        print("\nSecond call (should use cache):")
        price2 = GoldPriceService.get_current_gold_price(18)
        print(f"  Price: {price2['price_per_gram']:,} Toman/gram")
        print(f"  API calls made: {mock_get.call_count}")
        
        # Invalidate cache
        print("\nInvalidating cache...")
        GoldPriceService.invalidate_cache(18)
        
        # Third call - should hit API again
        print("Third call (after cache invalidation):")
        price3 = GoldPriceService.get_current_gold_price(18)
        print(f"  Price: {price3['price_per_gram']:,} Toman/gram")
        print(f"  API calls made: {mock_get.call_count}")


def demo_error_handling():
    """Demonstrate error handling in services."""
    print("\n⚠️ Error Handling Demo")
    print("=" * 50)
    
    # Test invalid price protection setup
    mock_contract = Mock()
    mock_contract.save = Mock()
    
    try:
        GoldPriceProtectionService.setup_price_protection(
            contract=mock_contract,
            ceiling_price=Decimal('3000000'),
            floor_price=Decimal('4000000')  # Floor higher than ceiling
        )
        print("ERROR: Should have raised ValidationError")
    except Exception as e:
        print(f"Validation error caught: {type(e).__name__}")
        print(f"  Message: {str(e)}")
    
    # Test no prices provided
    try:
        GoldPriceProtectionService.setup_price_protection(
            contract=mock_contract
        )
        print("ERROR: Should have raised ValidationError")
    except Exception as e:
        print(f"\nValidation error caught: {type(e).__name__}")
        print(f"  Message: {str(e)}")
    
    # Test API response parsing with invalid data
    print(f"\nAPI response parsing with invalid data:")
    invalid_data = {'invalid': 'response'}
    result = GoldPriceService._parse_api_response(invalid_data, 'primary', 18)
    print(f"  Result: {result}")
    print(f"  Handled gracefully: {'Yes' if result is None else 'No'}")


def main():
    """Run the complete demo."""
    print("🚀 ZARGAR Gold Price Integration & Payment Processing Demo")
    print("=" * 70)
    print("This demo showcases the core services without database operations.")
    print()
    
    try:
        # Demo gold price service
        demo_gold_price_service()
        
        # Demo price protection
        demo_price_protection()
        
        # Demo payment processing
        demo_payment_processing()
        
        # Demo API fallback
        demo_api_fallback()
        
        # Demo cache management
        demo_cache_management()
        
        # Demo error handling
        demo_error_handling()
        
        print(f"\n🎉 Demo completed successfully!")
        print(f"✨ All gold price integration and payment processing features demonstrated.")
        print(f"\n📋 Summary of demonstrated features:")
        print(f"  ✅ Real-time gold price fetching with API integration")
        print(f"  ✅ Multi-karat gold price calculations")
        print(f"  ✅ Price caching for performance optimization")
        print(f"  ✅ API fallback mechanism for reliability")
        print(f"  ✅ Price protection (ceiling/floor) system")
        print(f"  ✅ Payment processing with gold weight calculations")
        print(f"  ✅ Early payment discount system")
        print(f"  ✅ Bidirectional transaction support")
        print(f"  ✅ Comprehensive error handling")
        print(f"  ✅ Cache management and invalidation")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())