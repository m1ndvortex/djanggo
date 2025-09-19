"""
Simple tests for Persian number display components without Django TestCase.
Tests basic functionality and template rendering.
"""
import pytest
from decimal import Decimal
import re


class TestPersianNumberDisplayBasic:
    """Basic tests for Persian number display functionality."""
    
    def test_persian_number_formatter_import(self):
        """Test that Persian number formatter can be imported."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        
        # Test basic functionality
        result = PersianNumberFormatter.format_currency(1500000)
        assert '۱،۵۰۰،۰۰۰ تومان' in result
    
    def test_persian_digits_conversion(self):
        """Test Persian digits conversion."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        
        # Test English to Persian
        result = PersianNumberFormatter.to_persian_digits("123456")
        assert result == "۱۲۳۴۵۶"
        
        # Test Persian to English
        result = PersianNumberFormatter.to_english_digits("۱۲۳۴۵۶")
        assert result == "123456"
    
    def test_currency_formatting(self):
        """Test currency formatting functionality."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        
        # Test basic currency formatting
        result = PersianNumberFormatter.format_currency(1000000)
        assert "۱،۰۰۰،۰۰۰ تومان" in result
        
        # Test without symbol
        result = PersianNumberFormatter.format_currency(1000000, include_symbol=False)
        assert "۱،۰۰۰،۰۰۰" == result
        
        # Test with English digits
        result = PersianNumberFormatter.format_currency(1000000, use_persian_digits=False)
        assert "1,000,000 تومان" in result
    
    def test_weight_formatting(self):
        """Test weight formatting functionality."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        
        # Test basic weight formatting
        result = PersianNumberFormatter.format_weight(100, 'gram')
        assert "۱۰۰ گرم" in result
        
        # Test mesghal formatting
        result = PersianNumberFormatter.format_weight(1, 'mesghal')
        assert "۱ مثقال" in result
        
        # Test soot formatting
        result = PersianNumberFormatter.format_weight(20, 'soot')
        assert "۲۰ سوت" in result
    
    def test_weight_conversion(self):
        """Test weight conversion functionality."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        
        # Test gram to mesghal conversion
        result = PersianNumberFormatter.convert_weight(4.608, 'gram', 'mesghal')
        assert result == Decimal('1.000')
        
        # Test mesghal to gram conversion
        result = PersianNumberFormatter.convert_weight(1, 'mesghal', 'gram')
        assert result == Decimal('4.608')
        
        # Test gram to soot conversion
        result = PersianNumberFormatter.convert_weight(0.2304, 'gram', 'soot')
        assert result == Decimal('1.000')
    
    def test_percentage_formatting(self):
        """Test percentage formatting functionality."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        
        # Test basic percentage formatting
        result = PersianNumberFormatter.format_percentage(25.5)
        assert "۲۵.۵٪" in result
        
        # Test with English digits
        result = PersianNumberFormatter.format_percentage(25.5, use_persian_digits=False)
        assert "25.5%" in result
        
        # Test without decimals
        result = PersianNumberFormatter.format_percentage(25.7, decimal_places=0)
        assert "۲۶٪" in result
    
    def test_large_number_formatting(self):
        """Test large number formatting functionality."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        
        # Test basic large number formatting
        result = PersianNumberFormatter.format_large_number(1234567)
        assert "۱،۲۳۴،۵۶۷" in result
        
        # Test with word format
        result = PersianNumberFormatter.format_large_number(1000000, use_word_format=True)
        assert "۱ میلیون" in result
        
        # Test with English digits
        result = PersianNumberFormatter.format_large_number(1234567, use_persian_digits=False)
        assert "1,234,567" in result
    
    def test_gold_price_calculation(self):
        """Test gold price calculation functionality."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        
        # Test basic gold price calculation
        result = PersianNumberFormatter.format_gold_price(1000000, 5.5)
        
        assert 'price_per_gram' in result
        assert 'total_value' in result
        assert 'weight_display' in result
        assert 'weight_mesghal' in result
        assert 'weight_soot' in result
        
        # Check that calculations are correct
        assert "۱،۰۰۰،۰۰۰ تومان" in result['price_per_gram']
        assert "۵،۵۰۰،۰۰۰ تومان" in result['total_value']
        assert "۵.۵ گرم" in result['weight_display']
    
    def test_number_parsing(self):
        """Test Persian number parsing functionality."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        
        # Test basic parsing
        result = PersianNumberFormatter.parse_persian_number("۱۲۳")
        assert result == Decimal('123')
        
        # Test with separators
        result = PersianNumberFormatter.parse_persian_number("۱،۰۰۰")
        assert result == Decimal('1000')
        
        # Test with currency
        result = PersianNumberFormatter.parse_persian_number("۱۰۰۰ تومان")
        assert result == Decimal('1000')
        
        # Test invalid input
        result = PersianNumberFormatter.parse_persian_number("invalid")
        assert result is None
    
    def test_input_validation(self):
        """Test input validation functionality."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        
        # Test valid currency input
        is_valid, value, error = PersianNumberFormatter.validate_currency_input("۱۰۰۰")
        assert is_valid is True
        assert value == Decimal('1000')
        assert error == ""
        
        # Test invalid currency input
        is_valid, value, error = PersianNumberFormatter.validate_currency_input("invalid")
        assert is_valid is False
        assert value is None
        assert "نامعتبر" in error
        
        # Test valid weight input
        is_valid, value, error = PersianNumberFormatter.validate_weight_input("۱۰۰", "gram")
        assert is_valid is True
        assert value == Decimal('100')
        assert error == ""
        
        # Test invalid weight input
        is_valid, value, error = PersianNumberFormatter.validate_weight_input("۰", "gram")
        assert is_valid is False
        assert value is None
        assert "مثبت" in error


class TestPersianNumberDisplayFiles:
    """Test that required files exist and have correct content."""
    
    def test_javascript_file_exists(self):
        """Test that JavaScript file exists and has correct content."""
        import os
        js_file = 'static/js/persian-number-display.js'
        assert os.path.exists(js_file), f"JavaScript file {js_file} should exist"
        
        with open(js_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for key classes and methods
        assert 'class PersianNumberDisplay' in content
        assert 'formatCurrency' in content
        assert 'formatWeight' in content
        assert 'convertWeight' in content
        assert 'formatPercentage' in content
        assert 'formatGoldPrice' in content
        assert 'toPersianDigits' in content
        assert 'toEnglishDigits' in content
    
    def test_css_file_exists(self):
        """Test that CSS file exists and has correct content."""
        import os
        css_file = 'static/css/persian-number-display.css'
        assert os.path.exists(css_file), f"CSS file {css_file} should exist"
        
        with open(css_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for key CSS classes
        assert '.persian-number-display' in content
        assert '.persian-currency-display' in content
        assert '.persian-weight-display' in content
        assert '.gold-price-info' in content
        assert '.financial-display-card' in content
        assert '.weight-conversions' in content
        assert '.cyber-theme' in content
        assert '.light-mode' in content
        assert '.dark-mode' in content
    
    def test_template_files_exist(self):
        """Test that template files exist."""
        import os
        
        template_files = [
            'templates/core/components/persian_currency_display.html',
            'templates/core/components/persian_weight_display.html',
            'templates/core/components/persian_gold_price_display.html',
            'templates/core/components/persian_financial_card.html',
            'templates/demo/persian_number_display_demo.html'
        ]
        
        for template_file in template_files:
            assert os.path.exists(template_file), f"Template file {template_file} should exist"
    
    def test_template_content(self):
        """Test that template files have correct content."""
        import os
        
        # Test currency display template
        with open('templates/core/components/persian_currency_display.html', 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'data-persian-currency' in content
            assert 'persian-currency-display' in content
            assert 'تومان' in content
        
        # Test weight display template
        with open('templates/core/components/persian_weight_display.html', 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'data-persian-weight' in content
            assert 'persian-weight-display' in content
            assert 'گرم' in content
            assert 'مثقال' in content
            assert 'سوت' in content
        
        # Test gold price display template
        with open('templates/core/components/persian_gold_price_display.html', 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'data-gold-price' in content
            assert 'gold-price-info' in content
            assert 'قیمت هر گرم' in content
            assert 'ارزش کل' in content
        
        # Test financial card template
        with open('templates/core/components/persian_financial_card.html', 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'financial-display-card' in content
            assert 'data-card-type' in content
        
        # Test demo template
        with open('templates/demo/persian_number_display_demo.html', 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'سیستم نمایش اعداد فارسی' in content
            assert 'persian-number-display.js' in content
            assert 'persian-number-display.css' in content


class TestPersianNumberDisplayIntegration:
    """Test integration between components."""
    
    def test_template_tags_integration(self):
        """Test that template tags work with the formatter."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        from zargar.core.templatetags.persian_tags import persian_currency, persian_weight
        
        # Test currency template tag
        result = persian_currency(1500000)
        expected = PersianNumberFormatter.format_currency(1500000)
        assert result == expected
        
        # Test weight template tag
        result = persian_weight(100, 'gram')
        expected = PersianNumberFormatter.format_weight(100, 'gram')
        assert result == expected
    
    def test_weight_units_consistency(self):
        """Test that weight units are consistent across components."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        
        supported_units = PersianNumberFormatter.get_supported_weight_units()
        
        # Check that all expected units are present
        expected_units = ['gram', 'mesghal', 'soot', 'dirham', 'ounce', 'tola']
        for unit in expected_units:
            assert unit in supported_units
            assert 'name' in supported_units[unit]
            assert 'symbol' in supported_units[unit]
            assert 'to_gram' in supported_units[unit]
    
    def test_persian_digits_consistency(self):
        """Test that Persian digits are consistent across all formatting."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        
        # Test that all formatting methods use the same Persian digits
        currency_result = PersianNumberFormatter.format_currency(12345)
        weight_result = PersianNumberFormatter.format_weight(12345, 'gram')
        percentage_result = PersianNumberFormatter.format_percentage(12.345)
        number_result = PersianNumberFormatter.format_large_number(12345)
        
        # All should contain Persian digits
        persian_digit_pattern = r'[۰-۹]'
        assert re.search(persian_digit_pattern, currency_result)
        assert re.search(persian_digit_pattern, weight_result)
        assert re.search(persian_digit_pattern, percentage_result)
        assert re.search(persian_digit_pattern, number_result)
    
    def test_error_handling_consistency(self):
        """Test that error handling is consistent across all methods."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        
        # Test None values
        assert PersianNumberFormatter.format_currency(None) == "۰ تومان"
        assert PersianNumberFormatter.format_weight(None) == "۰ گرم"
        assert PersianNumberFormatter.format_percentage(None) == "۰٪"
        assert PersianNumberFormatter.format_large_number(None) == "۰"
        
        # Test invalid parsing
        assert PersianNumberFormatter.parse_persian_number(None) is None
        assert PersianNumberFormatter.parse_persian_number("") is None
        assert PersianNumberFormatter.parse_persian_number("invalid") is None


if __name__ == '__main__':
    pytest.main([__file__])