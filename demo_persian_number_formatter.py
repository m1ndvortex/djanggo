#!/usr/bin/env python
"""
Demo script for Persian number formatting and currency system.
Showcases the comprehensive Persian number formatting capabilities.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from decimal import Decimal
from zargar.core.persian_number_formatter import PersianNumberFormatter


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def demo_digit_conversion():
    """Demonstrate Persian digit conversion."""
    print_section("Persian Digit Conversion")
    
    test_numbers = ["123", "1000", "12.34", "999,999"]
    
    for number in test_numbers:
        persian = PersianNumberFormatter.to_persian_digits(number)
        back_to_english = PersianNumberFormatter.to_english_digits(persian)
        print(f"Original: {number:>10} → Persian: {persian:>15} → Back: {back_to_english:>10}")


def demo_currency_formatting():
    """Demonstrate Persian currency formatting."""
    print_section("Persian Currency Formatting")
    
    amounts = [1000, 50000, 1000000, 12345678, Decimal('123.45')]
    
    for amount in amounts:
        # With Persian digits and symbol
        persian_full = PersianNumberFormatter.format_currency(amount)
        
        # Without symbol
        persian_no_symbol = PersianNumberFormatter.format_currency(amount, include_symbol=False)
        
        # With English digits
        english_digits = PersianNumberFormatter.format_currency(amount, use_persian_digits=False)
        
        print(f"Amount: {amount}")
        print(f"  Persian Full:    {persian_full}")
        print(f"  Persian No Symbol: {persian_no_symbol}")
        print(f"  English Digits:  {english_digits}")
        print()


def demo_weight_conversion():
    """Demonstrate Persian weight conversion and formatting."""
    print_section("Persian Weight Conversion & Formatting")
    
    # Test weight conversions
    weights_in_grams = [4.608, 9.216, 100, 1000]
    
    for weight in weights_in_grams:
        print(f"Weight: {weight} grams")
        
        # Convert to different units
        mesghal = PersianNumberFormatter.convert_weight(weight, 'gram', 'mesghal')
        soot = PersianNumberFormatter.convert_weight(weight, 'gram', 'soot')
        
        # Format in different units
        gram_formatted = PersianNumberFormatter.format_weight(weight, 'gram')
        mesghal_formatted = PersianNumberFormatter.format_weight(mesghal, 'mesghal')
        soot_formatted = PersianNumberFormatter.format_weight(soot, 'soot')
        
        print(f"  Grams:   {gram_formatted}")
        print(f"  Mesghal: {mesghal_formatted}")
        print(f"  Soot:    {soot_formatted}")
        print()


def demo_weight_with_conversion():
    """Demonstrate weight formatting with multiple unit conversion."""
    print_section("Weight with Multiple Unit Conversion")
    
    weights = [4.608, 23.04, 100]
    
    for weight in weights:
        print(f"Weight: {weight} grams")
        conversions = PersianNumberFormatter.format_weight_with_conversion(weight)
        
        for unit, formatted in conversions.items():
            print(f"  {unit.capitalize():>8}: {formatted}")
        print()


def demo_large_number_formatting():
    """Demonstrate large number formatting."""
    print_section("Large Number Formatting")
    
    numbers = [1000, 50000, 1000000, 1500000, 1000000000, 1234567890]
    
    for number in numbers:
        # Standard formatting
        standard = PersianNumberFormatter.format_large_number(number)
        
        # Word format
        word_format = PersianNumberFormatter.format_large_number(number, use_word_format=True)
        
        # English digits
        english = PersianNumberFormatter.format_large_number(number, use_persian_digits=False)
        
        print(f"Number: {number:>12}")
        print(f"  Standard:     {standard}")
        print(f"  Word Format:  {word_format}")
        print(f"  English:      {english}")
        print()


def demo_percentage_formatting():
    """Demonstrate percentage formatting."""
    print_section("Percentage Formatting")
    
    percentages = [25, 33.333, 75.5, 100, 0.5]
    
    for percent in percentages:
        # Default formatting
        default = PersianNumberFormatter.format_percentage(percent)
        
        # No decimals
        no_decimals = PersianNumberFormatter.format_percentage(percent, decimal_places=0)
        
        # Multiple decimals
        multi_decimals = PersianNumberFormatter.format_percentage(percent, decimal_places=2)
        
        # English digits
        english = PersianNumberFormatter.format_percentage(percent, use_persian_digits=False)
        
        print(f"Percentage: {percent}")
        print(f"  Default:        {default}")
        print(f"  No Decimals:    {no_decimals}")
        print(f"  Multi Decimals: {multi_decimals}")
        print(f"  English:        {english}")
        print()


def demo_gold_price_calculation():
    """Demonstrate gold price calculations."""
    print_section("Gold Price Calculations")
    
    # Sample gold prices and weights
    scenarios = [
        (1000000, 5.5),    # 1M Toman per gram, 5.5 grams
        (1200000, 4.608),  # 1.2M Toman per gram, 1 mesghal
        (950000, 23.04),   # 950K Toman per gram, 5 mesghal
    ]
    
    for price_per_gram, weight_grams in scenarios:
        print(f"Gold Price: {price_per_gram:,} Toman/gram, Weight: {weight_grams} grams")
        
        gold_calc = PersianNumberFormatter.format_gold_price(price_per_gram, weight_grams)
        
        print(f"  Price per gram: {gold_calc['price_per_gram']}")
        print(f"  Total value:    {gold_calc['total_value']}")
        print(f"  Weight (grams): {gold_calc['weight_display']}")
        print(f"  Weight (mesghal): {gold_calc['weight_mesghal']}")
        print(f"  Weight (soot):  {gold_calc['weight_soot']}")
        print()


def demo_number_parsing():
    """Demonstrate Persian number parsing."""
    print_section("Persian Number Parsing")
    
    persian_numbers = [
        "۱۲۳",
        "۱،۰۰۰",
        "۱۲۳،۴۵۶ تومان",
        "۵.۵ گرم",
        "۲۵٪",
        "invalid text",
        "۱۰۰ مثقال"
    ]
    
    for persian_num in persian_numbers:
        parsed = PersianNumberFormatter.parse_persian_number(persian_num)
        print(f"Input: {persian_num:>15} → Parsed: {parsed}")


def demo_input_validation():
    """Demonstrate input validation."""
    print_section("Input Validation")
    
    # Currency validation
    print("Currency Validation:")
    currency_inputs = ["۱۰۰۰", "۱،۰۰۰ تومان", "-۵۰۰", "invalid", ""]
    
    for input_text in currency_inputs:
        is_valid, value, error = PersianNumberFormatter.validate_currency_input(input_text)
        status = "✓ Valid" if is_valid else "✗ Invalid"
        print(f"  {input_text:>15} → {status:>10} | Value: {value} | Error: {error}")
    
    print("\nWeight Validation:")
    weight_inputs = ["۱۰۰", "۵.۵ گرم", "۰", "invalid", ""]
    
    for input_text in weight_inputs:
        is_valid, value, error = PersianNumberFormatter.validate_weight_input(input_text, 'gram')
        status = "✓ Valid" if is_valid else "✗ Invalid"
        print(f"  {input_text:>15} → {status:>10} | Value: {value} | Error: {error}")


def demo_supported_weight_units():
    """Demonstrate supported weight units."""
    print_section("Supported Weight Units")
    
    units = PersianNumberFormatter.get_supported_weight_units()
    
    print(f"{'Unit':>10} | {'Persian Name':>15} | {'Symbol':>8} | {'To Gram Ratio':>15}")
    print("-" * 60)
    
    for unit_key, unit_info in units.items():
        print(f"{unit_key:>10} | {unit_info['name']:>15} | {unit_info['symbol']:>8} | {unit_info['to_gram']:>15}")


def main():
    """Run all demonstrations."""
    print("Persian Number Formatting System Demo")
    print("ZARGAR Jewelry SaaS Platform")
    print("=" * 60)
    
    # Run all demonstrations
    demo_digit_conversion()
    demo_currency_formatting()
    demo_weight_conversion()
    demo_weight_with_conversion()
    demo_large_number_formatting()
    demo_percentage_formatting()
    demo_gold_price_calculation()
    demo_number_parsing()
    demo_input_validation()
    demo_supported_weight_units()
    
    print(f"\n{'='*60}")
    print(" Demo Complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()