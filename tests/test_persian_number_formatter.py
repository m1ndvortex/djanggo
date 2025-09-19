"""
Tests for Persian number formatting and currency system.
"""
import pytest
from decimal import Decimal
from zargar.core.persian_number_formatter import PersianNumberFormatter


class TestPersianDigitConversion:
    """Test Persian digit conversion functionality."""
    
    def test_to_persian_digits_string(self):
        """Test converting English digits to Persian in strings."""
        assert PersianNumberFormatter.to_persian_digits("123") == "۱۲۳"
        assert PersianNumberFormatter.to_persian_digits("0987654321") == "۰۹۸۷۶۵۴۳۲۱"
        assert PersianNumberFormatter.to_persian_digits("Price: 1000") == "Price: ۱۰۰۰"
        assert PersianNumberFormatter.to_persian_digits("") == ""
    
    def test_to_persian_digits_numbers(self):
        """Test converting numbers to Persian digits."""
        assert PersianNumberFormatter.to_persian_digits(123) == "۱۲۳"
        assert PersianNumberFormatter.to_persian_digits(0) == "۰"
        assert PersianNumberFormatter.to_persian_digits(12.34) == "۱۲.۳۴"
        assert PersianNumberFormatter.to_persian_digits(Decimal('456.78')) == "۴۵۶.۷۸"
    
    def test_to_english_digits(self):
        """Test converting Persian digits to English."""
        assert PersianNumberFormatter.to_english_digits("۱۲۳") == "123"
        assert PersianNumberFormatter.to_english_digits("۰۹۸۷۶۵۴۳۲۱") == "0987654321"
        assert PersianNumberFormatter.to_english_digits("قیمت: ۱۰۰۰") == "قیمت: 1000"
        assert PersianNumberFormatter.to_english_digits("") == ""
    
    def test_digit_conversion_roundtrip(self):
        """Test that digit conversion is reversible."""
        original = "123456789"
        persian = PersianNumberFormatter.to_persian_digits(original)
        back_to_english = PersianNumberFormatter.to_english_digits(persian)
        assert back_to_english == original


class TestCurrencyFormatting:
    """Test currency formatting functionality."""
    
    def test_format_currency_basic(self):
        """Test basic currency formatting."""
        assert PersianNumberFormatter.format_currency(1000) == "۱،۰۰۰ تومان"
        assert PersianNumberFormatter.format_currency(0) == "۰ تومان"
        assert PersianNumberFormatter.format_currency(123456) == "۱۲۳،۴۵۶ تومان"
    
    def test_format_currency_without_symbol(self):
        """Test currency formatting without symbol."""
        assert PersianNumberFormatter.format_currency(1000, include_symbol=False) == "۱،۰۰۰"
        assert PersianNumberFormatter.format_currency(123456, include_symbol=False) == "۱۲۳،۴۵۶"
    
    def test_format_currency_english_digits(self):
        """Test currency formatting with English digits."""
        assert PersianNumberFormatter.format_currency(1000, use_persian_digits=False) == "1,000 تومان"
        assert PersianNumberFormatter.format_currency(123456, use_persian_digits=False) == "123,456 تومان"
    
    def test_format_currency_with_decimals(self):
        """Test currency formatting with decimal places."""
        assert PersianNumberFormatter.format_currency(
            1000.50, show_decimals=True, decimal_places=2
        ) == "۱،۰۰۰.۵۰ تومان"
        
        assert PersianNumberFormatter.format_currency(
            Decimal('123.45'), show_decimals=True, decimal_places=2
        ) == "۱۲۳.۴۵ تومان"
    
    def test_format_currency_large_amounts(self):
        """Test currency formatting for large amounts."""
        assert PersianNumberFormatter.format_currency(1000000) == "۱،۰۰۰،۰۰۰ تومان"
        assert PersianNumberFormatter.format_currency(1234567890) == "۱،۲۳۴،۵۶۷،۸۹۰ تومان"
    
    def test_format_currency_none_value(self):
        """Test currency formatting with None value."""
        assert PersianNumberFormatter.format_currency(None) == "۰ تومان"
        assert PersianNumberFormatter.format_currency(None, use_persian_digits=False) == "0 تومان"
    
    def test_format_currency_decimal_precision(self):
        """Test currency formatting with Decimal precision."""
        # Test rounding
        assert PersianNumberFormatter.format_currency(
            Decimal('123.456'), show_decimals=True, decimal_places=2
        ) == "۱۲۳.۴۶ تومان"
        
        # Test no rounding needed
        assert PersianNumberFormatter.format_currency(
            Decimal('123.40'), show_decimals=True, decimal_places=2
        ) == "۱۲۳.۴۰ تومان"


class TestLargeNumberFormatting:
    """Test large number formatting functionality."""
    
    def test_format_large_number_basic(self):
        """Test basic large number formatting."""
        assert PersianNumberFormatter.format_large_number(1000) == "۱،۰۰۰"
        assert PersianNumberFormatter.format_large_number(1234567) == "۱،۲۳۴،۵۶۷"
        assert PersianNumberFormatter.format_large_number(0) == "۰"
    
    def test_format_large_number_english_digits(self):
        """Test large number formatting with English digits."""
        assert PersianNumberFormatter.format_large_number(1000, use_persian_digits=False) == "1,000"
        assert PersianNumberFormatter.format_large_number(1234567, use_persian_digits=False) == "1,234,567"
    
    def test_format_large_number_with_words(self):
        """Test large number formatting with word format."""
        assert PersianNumberFormatter.format_large_number(1000000, use_word_format=True) == "۱ میلیون"
        assert PersianNumberFormatter.format_large_number(1500000, use_word_format=True) == "۱ میلیون و ۵۰۰ هزار"
        assert PersianNumberFormatter.format_large_number(1000000000, use_word_format=True) == "۱ میلیارد"
    
    def test_format_large_number_negative(self):
        """Test large number formatting with negative numbers."""
        assert PersianNumberFormatter.format_large_number(-1000) == "-۱،۰۰۰"
        assert PersianNumberFormatter.format_large_number(-1000000, use_word_format=True) == "-۱ میلیون"
    
    def test_format_large_number_none_value(self):
        """Test large number formatting with None value."""
        assert PersianNumberFormatter.format_large_number(None) == "۰"
        assert PersianNumberFormatter.format_large_number(None, use_persian_digits=False) == "0"


class TestWeightConversion:
    """Test weight conversion functionality."""
    
    def test_convert_weight_gram_to_mesghal(self):
        """Test converting grams to mesghal."""
        result = PersianNumberFormatter.convert_weight(4.608, 'gram', 'mesghal')
        assert result == Decimal('1.000')
        
        result = PersianNumberFormatter.convert_weight(9.216, 'gram', 'mesghal')
        assert result == Decimal('2.000')
    
    def test_convert_weight_mesghal_to_gram(self):
        """Test converting mesghal to grams."""
        result = PersianNumberFormatter.convert_weight(1, 'mesghal', 'gram')
        assert result == Decimal('4.608')
        
        result = PersianNumberFormatter.convert_weight(2.5, 'mesghal', 'gram')
        assert result == Decimal('11.520')
    
    def test_convert_weight_gram_to_soot(self):
        """Test converting grams to soot."""
        result = PersianNumberFormatter.convert_weight(0.2304, 'gram', 'soot')
        assert result == Decimal('1.000')
        
        result = PersianNumberFormatter.convert_weight(4.608, 'gram', 'soot')
        assert result == Decimal('20.000')
    
    def test_convert_weight_soot_to_mesghal(self):
        """Test converting soot to mesghal."""
        result = PersianNumberFormatter.convert_weight(20, 'soot', 'mesghal')
        assert result == Decimal('1.000')
        
        result = PersianNumberFormatter.convert_weight(10, 'soot', 'mesghal')
        assert result == Decimal('0.500')
    
    def test_convert_weight_precision(self):
        """Test weight conversion with different precision."""
        result = PersianNumberFormatter.convert_weight(1, 'gram', 'soot', precision=5)
        assert str(result) == "4.34028"
        
        result = PersianNumberFormatter.convert_weight(1, 'gram', 'soot', precision=1)
        assert str(result) == "4.3"
    
    def test_convert_weight_invalid_units(self):
        """Test weight conversion with invalid units."""
        with pytest.raises(ValueError, match="Unsupported source unit"):
            PersianNumberFormatter.convert_weight(1, 'invalid', 'gram')
        
        with pytest.raises(ValueError, match="Unsupported target unit"):
            PersianNumberFormatter.convert_weight(1, 'gram', 'invalid')
    
    def test_convert_weight_decimal_input(self):
        """Test weight conversion with Decimal input."""
        result = PersianNumberFormatter.convert_weight(Decimal('4.608'), 'gram', 'mesghal')
        assert result == Decimal('1.000')


class TestWeightFormatting:
    """Test weight formatting functionality."""
    
    def test_format_weight_basic(self):
        """Test basic weight formatting."""
        assert PersianNumberFormatter.format_weight(100, 'gram') == "۱۰۰ گرم"
        assert PersianNumberFormatter.format_weight(1.5, 'mesghal') == "۱.۵ مثقال"
        assert PersianNumberFormatter.format_weight(20, 'soot') == "۲۰ سوت"
    
    def test_format_weight_english_digits(self):
        """Test weight formatting with English digits."""
        assert PersianNumberFormatter.format_weight(100, 'gram', use_persian_digits=False) == "100 گرم"
        assert PersianNumberFormatter.format_weight(1.5, 'mesghal', use_persian_digits=False) == "1.5 مثقال"
    
    def test_format_weight_without_unit_name(self):
        """Test weight formatting without unit name."""
        assert PersianNumberFormatter.format_weight(100, 'gram', show_unit_name=False) == "۱۰۰"
        assert PersianNumberFormatter.format_weight(1.5, 'mesghal', show_unit_name=False) == "۱.۵"
    
    def test_format_weight_large_numbers(self):
        """Test weight formatting with large numbers."""
        assert PersianNumberFormatter.format_weight(1000, 'gram') == "۱،۰۰۰ گرم"
        assert PersianNumberFormatter.format_weight(12345.678, 'gram') == "۱۲،۳۴۵.۶۷۸ گرم"
    
    def test_format_weight_integer_display(self):
        """Test weight formatting shows integers without decimals."""
        assert PersianNumberFormatter.format_weight(100.0, 'gram') == "۱۰۰ گرم"
        assert PersianNumberFormatter.format_weight(Decimal('50.000'), 'gram') == "۵۰ گرم"
    
    def test_format_weight_none_value(self):
        """Test weight formatting with None value."""
        assert PersianNumberFormatter.format_weight(None) == "۰ گرم"
        assert PersianNumberFormatter.format_weight(None, use_persian_digits=False) == "0 gram"
    
    def test_format_weight_invalid_unit(self):
        """Test weight formatting with invalid unit."""
        with pytest.raises(ValueError, match="Unsupported weight unit"):
            PersianNumberFormatter.format_weight(100, 'invalid_unit')


class TestWeightWithConversion:
    """Test weight formatting with multiple unit conversion."""
    
    def test_format_weight_with_conversion_default_units(self):
        """Test weight conversion with default units."""
        result = PersianNumberFormatter.format_weight_with_conversion(4.608)
        
        expected = {
            'gram': '۴.۶۰۸ گرم',
            'mesghal': '۱ مثقال',
            'soot': '۲۰ سوت'
        }
        assert result == expected
    
    def test_format_weight_with_conversion_custom_units(self):
        """Test weight conversion with custom units."""
        result = PersianNumberFormatter.format_weight_with_conversion(
            100, target_units=['gram', 'ounce']
        )
        
        assert 'gram' in result
        assert 'ounce' in result
        assert result['gram'] == '۱۰۰ گرم'
    
    def test_format_weight_with_conversion_english_digits(self):
        """Test weight conversion with English digits."""
        result = PersianNumberFormatter.format_weight_with_conversion(
            4.608, use_persian_digits=False
        )
        
        expected = {
            'gram': '4.608 گرم',
            'mesghal': '1 مثقال',
            'soot': '20 سوت'
        }
        assert result == expected
    
    def test_format_weight_with_conversion_none_value(self):
        """Test weight conversion with None value."""
        result = PersianNumberFormatter.format_weight_with_conversion(None)
        
        expected = {
            'gram': '۰',
            'mesghal': '۰',
            'soot': '۰'
        }
        assert result == expected


class TestNumberParsing:
    """Test Persian number parsing functionality."""
    
    def test_parse_persian_number_basic(self):
        """Test basic Persian number parsing."""
        assert PersianNumberFormatter.parse_persian_number("۱۲۳") == Decimal('123')
        assert PersianNumberFormatter.parse_persian_number("۰") == Decimal('0')
        assert PersianNumberFormatter.parse_persian_number("۱۲۳.۴۵") == Decimal('123.45')
    
    def test_parse_persian_number_with_separators(self):
        """Test parsing Persian numbers with thousand separators."""
        assert PersianNumberFormatter.parse_persian_number("۱،۰۰۰") == Decimal('1000')
        assert PersianNumberFormatter.parse_persian_number("۱۲۳،۴۵۶") == Decimal('123456')
        assert PersianNumberFormatter.parse_persian_number("1,000") == Decimal('1000')
    
    def test_parse_persian_number_with_currency(self):
        """Test parsing Persian numbers with currency symbols."""
        assert PersianNumberFormatter.parse_persian_number("۱۰۰۰ تومان") == Decimal('1000')
        assert PersianNumberFormatter.parse_persian_number("۵۰۰ ریال") == Decimal('500')
    
    def test_parse_persian_number_with_weight_units(self):
        """Test parsing Persian numbers with weight units."""
        assert PersianNumberFormatter.parse_persian_number("۱۰۰ گرم") == Decimal('100')
        assert PersianNumberFormatter.parse_persian_number("۵ مثقال") == Decimal('5')
        assert PersianNumberFormatter.parse_persian_number("۲۰ سوت") == Decimal('20')
    
    def test_parse_persian_number_invalid_input(self):
        """Test parsing invalid Persian number input."""
        assert PersianNumberFormatter.parse_persian_number("") is None
        assert PersianNumberFormatter.parse_persian_number(None) is None
        assert PersianNumberFormatter.parse_persian_number("invalid") is None
        assert PersianNumberFormatter.parse_persian_number("abc۱۲۳def") is None
    
    def test_parse_persian_number_mixed_digits(self):
        """Test parsing numbers with mixed Persian and English digits."""
        assert PersianNumberFormatter.parse_persian_number("1۲3") == Decimal('123')
        assert PersianNumberFormatter.parse_persian_number("۱2۳") == Decimal('123')


class TestPercentageFormatting:
    """Test percentage formatting functionality."""
    
    def test_format_percentage_basic(self):
        """Test basic percentage formatting."""
        assert PersianNumberFormatter.format_percentage(50) == "۵۰.۰٪"
        assert PersianNumberFormatter.format_percentage(100) == "۱۰۰.۰٪"
        assert PersianNumberFormatter.format_percentage(0) == "۰.۰٪"
    
    def test_format_percentage_english_digits(self):
        """Test percentage formatting with English digits."""
        assert PersianNumberFormatter.format_percentage(50, use_persian_digits=False) == "50.0%"
        assert PersianNumberFormatter.format_percentage(75.5, use_persian_digits=False) == "75.5%"
    
    def test_format_percentage_no_decimals(self):
        """Test percentage formatting without decimal places."""
        assert PersianNumberFormatter.format_percentage(50, decimal_places=0) == "۵۰٪"
        assert PersianNumberFormatter.format_percentage(75.7, decimal_places=0) == "۷۶٪"  # Rounded
    
    def test_format_percentage_multiple_decimals(self):
        """Test percentage formatting with multiple decimal places."""
        assert PersianNumberFormatter.format_percentage(33.333, decimal_places=2) == "۳۳.۳۳٪"
        assert PersianNumberFormatter.format_percentage(66.666, decimal_places=3) == "۶۶.۶۶۶٪"
    
    def test_format_percentage_none_value(self):
        """Test percentage formatting with None value."""
        assert PersianNumberFormatter.format_percentage(None) == "۰٪"
        assert PersianNumberFormatter.format_percentage(None, use_persian_digits=False) == "0%"


class TestGoldPriceFormatting:
    """Test gold price formatting functionality."""
    
    def test_format_gold_price_basic(self):
        """Test basic gold price formatting."""
        result = PersianNumberFormatter.format_gold_price(1000000, 5.5)
        
        assert 'price_per_gram' in result
        assert 'total_value' in result
        assert 'weight_display' in result
        assert 'weight_mesghal' in result
        assert 'weight_soot' in result
        
        assert result['price_per_gram'] == "۱،۰۰۰،۰۰۰ تومان"
        assert result['total_value'] == "۵،۵۰۰،۰۰۰ تومان"
        assert result['weight_display'] == "۵.۵ گرم"
    
    def test_format_gold_price_english_digits(self):
        """Test gold price formatting with English digits."""
        result = PersianNumberFormatter.format_gold_price(1000000, 5.5, use_persian_digits=False)
        
        assert result['price_per_gram'] == "1,000,000 تومان"
        assert result['total_value'] == "5,500,000 تومان"
        assert result['weight_display'] == "5.5 گرم"
    
    def test_format_gold_price_none_values(self):
        """Test gold price formatting with None values."""
        result = PersianNumberFormatter.format_gold_price(None, 5.5)
        
        assert result['price_per_gram'] == "۰ تومان"
        assert result['total_value'] == "۰ تومان"
        assert result['weight_display'] == "۰ گرم"
        
        result = PersianNumberFormatter.format_gold_price(1000000, None)
        
        assert result['price_per_gram'] == "۰ تومان"
        assert result['total_value'] == "۰ تومان"
        assert result['weight_display'] == "۰ گرم"
    
    def test_format_gold_price_weight_conversions(self):
        """Test gold price formatting includes weight conversions."""
        result = PersianNumberFormatter.format_gold_price(1000000, 4.608)
        
        # 4.608 grams = 1 mesghal = 20 soot
        assert "۱ مثقال" in result['weight_mesghal']
        assert "۲۰ سوت" in result['weight_soot']


class TestInputValidation:
    """Test input validation functionality."""
    
    def test_validate_currency_input_valid(self):
        """Test currency input validation with valid inputs."""
        is_valid, value, error = PersianNumberFormatter.validate_currency_input("۱۰۰۰")
        assert is_valid is True
        assert value == Decimal('1000')
        assert error == ""
        
        is_valid, value, error = PersianNumberFormatter.validate_currency_input("۱،۰۰۰ تومان")
        assert is_valid is True
        assert value == Decimal('1000')
        assert error == ""
    
    def test_validate_currency_input_invalid(self):
        """Test currency input validation with invalid inputs."""
        is_valid, value, error = PersianNumberFormatter.validate_currency_input("")
        assert is_valid is False
        assert value is None
        assert "خالی" in error
        
        is_valid, value, error = PersianNumberFormatter.validate_currency_input("invalid")
        assert is_valid is False
        assert value is None
        assert "نامعتبر" in error
        
        is_valid, value, error = PersianNumberFormatter.validate_currency_input("-۱۰۰")
        assert is_valid is False
        assert value is None
        assert "منفی" in error
    
    def test_validate_weight_input_valid(self):
        """Test weight input validation with valid inputs."""
        is_valid, value, error = PersianNumberFormatter.validate_weight_input("۱۰۰", "gram")
        assert is_valid is True
        assert value == Decimal('100')
        assert error == ""
        
        is_valid, value, error = PersianNumberFormatter.validate_weight_input("۵.۵ گرم", "gram")
        assert is_valid is True
        assert value == Decimal('5.5')
        assert error == ""
    
    def test_validate_weight_input_invalid(self):
        """Test weight input validation with invalid inputs."""
        is_valid, value, error = PersianNumberFormatter.validate_weight_input("", "gram")
        assert is_valid is False
        assert value is None
        assert "خالی" in error
        
        is_valid, value, error = PersianNumberFormatter.validate_weight_input("۱۰۰", "invalid_unit")
        assert is_valid is False
        assert value is None
        assert "نامعتبر" in error
        
        is_valid, value, error = PersianNumberFormatter.validate_weight_input("۰", "gram")
        assert is_valid is False
        assert value is None
        assert "مثبت" in error


class TestUtilityMethods:
    """Test utility methods."""
    
    def test_get_supported_weight_units(self):
        """Test getting supported weight units."""
        units = PersianNumberFormatter.get_supported_weight_units()
        
        assert 'gram' in units
        assert 'mesghal' in units
        assert 'soot' in units
        assert 'dirham' in units
        assert 'ounce' in units
        assert 'tola' in units
        
        # Check unit structure
        gram_unit = units['gram']
        assert 'name' in gram_unit
        assert 'symbol' in gram_unit
        assert 'to_gram' in gram_unit
        assert gram_unit['name'] == 'گرم'
        assert gram_unit['to_gram'] == 1
    
    def test_weight_unit_conversions_accuracy(self):
        """Test accuracy of weight unit conversions."""
        # Test mesghal conversion (1 mesghal = 4.608 grams)
        result = PersianNumberFormatter.convert_weight(1, 'mesghal', 'gram')
        assert result == Decimal('4.608')
        
        # Test soot conversion (1 soot = 0.2304 grams, 20 soot = 1 mesghal)
        result = PersianNumberFormatter.convert_weight(20, 'soot', 'mesghal')
        assert result == Decimal('1.000')
        
        # Test round-trip conversion
        original = Decimal('100')
        converted = PersianNumberFormatter.convert_weight(original, 'gram', 'mesghal')
        back = PersianNumberFormatter.convert_weight(converted, 'mesghal', 'gram')
        assert abs(back - original) < Decimal('0.01')  # Allow for small rounding errors


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_very_large_numbers(self):
        """Test formatting very large numbers."""
        large_number = 999999999999
        result = PersianNumberFormatter.format_currency(large_number)
        assert "۹۹۹،۹۹۹،۹۹۹،۹۹۹ تومان" in result
        
        result = PersianNumberFormatter.format_large_number(large_number, use_word_format=True)
        assert "میلیارد" in result
    
    def test_very_small_weights(self):
        """Test formatting very small weights."""
        small_weight = Decimal('0.001')
        result = PersianNumberFormatter.format_weight(small_weight, 'gram')
        assert "۰.۰۰۱ گرم" in result
    
    def test_zero_values(self):
        """Test handling zero values."""
        assert PersianNumberFormatter.format_currency(0) == "۰ تومان"
        assert PersianNumberFormatter.format_weight(0, 'gram') == "۰ گرم"
        assert PersianNumberFormatter.format_percentage(0) == "۰.۰٪"
    
    def test_decimal_precision_edge_cases(self):
        """Test decimal precision in edge cases."""
        # Test rounding
        result = PersianNumberFormatter.format_currency(
            Decimal('123.999'), show_decimals=True, decimal_places=2
        )
        assert "۱۲۴.۰۰ تومان" in result
        
        # Test very small decimals
        result = PersianNumberFormatter.convert_weight(
            Decimal('0.0001'), 'gram', 'soot', precision=6
        )
        assert result > 0