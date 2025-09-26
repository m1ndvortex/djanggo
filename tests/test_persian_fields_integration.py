"""
Integration tests for Persian fields and template tags.
"""
import pytest
from decimal import Decimal
from django.test import TestCase
from django.template import Context, Template
from zargar.core.persian_fields import (
    PersianCurrencyField, PersianWeightField, PersianPercentageField,
    PersianCurrencyFormField, PersianWeightFormField, PersianPercentageFormField
)
from zargar.core.persian_number_formatter import PersianNumberFormatter


class TestPersianFieldsIntegration(TestCase):
    """Test Persian fields integration with Django."""
    
    def test_persian_currency_field_to_python(self):
        """Test PersianCurrencyField to_python method."""
        field = PersianCurrencyField()
        
        # Test with None
        assert field.to_python(None) is None
        
        # Test with Decimal
        assert field.to_python(Decimal('1000')) == Decimal('1000')
        
        # Test with Persian formatted string
        assert field.to_python("۱،۰۰۰ تومان") == Decimal('1000')
        
        # Test with English number
        assert field.to_python("1000") == Decimal('1000')
    
    def test_persian_weight_field_to_python(self):
        """Test PersianWeightField to_python method."""
        field = PersianWeightField(unit='gram')
        
        # Test with None
        assert field.to_python(None) is None
        
        # Test with Decimal
        assert field.to_python(Decimal('100.5')) == Decimal('100.5')
        
        # Test with Persian formatted string
        assert field.to_python("۱۰۰.۵ گرم") == Decimal('100.5')
    
    def test_persian_percentage_field_to_python(self):
        """Test PersianPercentageField to_python method."""
        field = PersianPercentageField()
        
        # Test with None
        assert field.to_python(None) is None
        
        # Test with Decimal
        assert field.to_python(Decimal('25.5')) == Decimal('25.5')
        
        # Test with Persian formatted string
        assert field.to_python("۲۵.۵٪") == Decimal('25.5')
    
    def test_persian_currency_form_field_validation(self):
        """Test PersianCurrencyFormField validation."""
        field = PersianCurrencyFormField()
        
        # Test valid input
        assert field.to_python("۱۰۰۰") == Decimal('1000')
        
        # Test invalid input
        with pytest.raises(Exception):  # ValidationError
            field.to_python("invalid")
    
    def test_persian_weight_form_field_validation(self):
        """Test PersianWeightFormField validation."""
        field = PersianWeightFormField(unit='gram')
        
        # Test valid input
        assert field.to_python("۱۰۰") == Decimal('100')
        
        # Test invalid input
        with pytest.raises(Exception):  # ValidationError
            field.to_python("invalid")


class TestPersianTemplateTagsIntegration(TestCase):
    """Test Persian template tags integration."""
    
    def test_persian_currency_template_tag(self):
        """Test persian_currency template tag."""
        template = Template("{% load persian_tags %}{% persian_currency 1000000 %}")
        rendered = template.render(Context({}))
        assert "۱،۰۰۰،۰۰۰ تومان" in rendered
    
    def test_persian_weight_template_tag(self):
        """Test persian_weight template tag."""
        template = Template("{% load persian_tags %}{% persian_weight 100 'gram' %}")
        rendered = template.render(Context({}))
        assert "۱۰۰ گرم" in rendered
    
    def test_persian_percentage_template_tag(self):
        """Test persian_percentage template tag."""
        template = Template("{% load persian_tags %}{% persian_percentage 25 %}")
        rendered = template.render(Context({}))
        assert "۲۵" in rendered and "٪" in rendered
    
    def test_persian_large_number_template_tag(self):
        """Test persian_large_number template tag."""
        template = Template("{% load persian_tags %}{% persian_large_number 1000000 True True %}")
        rendered = template.render(Context({}))
        assert "میلیون" in rendered
    
    def test_weight_conversions_template_tag(self):
        """Test weight_conversions template tag."""
        template = Template("{% load persian_tags %}{% weight_conversions 4.608 as conversions %}{{ conversions.mesghal }}")
        rendered = template.render(Context({}))
        assert "۱ مثقال" in rendered
    
    def test_gold_price_calculation_template_tag(self):
        """Test gold_price_calculation template tag."""
        template = Template("""
            {% load persian_tags %}
            {% gold_price_calculation 1000000 5.5 as gold_calc %}
            {{ gold_calc.total_value }}
        """)
        rendered = template.render(Context({}))
        assert "۵،۵۰۰،۰۰۰ تومان" in rendered
    
    def test_persian_digits_template_tag(self):
        """Test persian_digits template tag."""
        template = Template("{% load persian_tags %}{% persian_digits '123' %}")
        rendered = template.render(Context({}))
        assert rendered.strip() == "۱۲۳"
    
    def test_english_digits_template_tag(self):
        """Test english_digits template tag."""
        template = Template("{% load persian_tags %}{% english_digits '۱۲۳' %}")
        rendered = template.render(Context({}))
        assert rendered.strip() == "123"
    
    def test_currency_filter(self):
        """Test currency template filter."""
        template = Template("{% load persian_tags %}{{ amount|currency }}")
        rendered = template.render(Context({'amount': 1000}))
        assert "۱،۰۰۰ تومان" in rendered
    
    def test_weight_filter(self):
        """Test weight template filter."""
        template = Template("{% load persian_tags %}{{ weight_value|weight:'mesghal' }}")
        rendered = template.render(Context({'weight_value': 1}))
        assert "۱ مثقال" in rendered
    
    def test_percentage_filter(self):
        """Test percentage template filter."""
        template = Template("{% load persian_tags %}{{ percent_value|percentage:0 }}")
        rendered = template.render(Context({'percent_value': 25.7}))
        assert "۲۶٪" in rendered  # Should be rounded
    
    def test_large_number_filter(self):
        """Test large_number template filter."""
        template = Template("{% load persian_tags %}{{ big_number|large_number:True }}")
        rendered = template.render(Context({'big_number': 1000000}))
        assert "میلیون" in rendered
    
    def test_weight_in_units_filter(self):
        """Test weight_in_units template filter."""
        template = Template("{% load persian_tags %}{{ weight_grams|weight_in_units as units %}{{ units.mesghal }}")
        rendered = template.render(Context({'weight_grams': 4.608}))
        assert "۱ مثقال" in rendered
    
    def test_parse_persian_number_filter(self):
        """Test parse_persian_number template filter."""
        template = Template("{% load persian_tags %}{{ persian_num|parse_persian_number }}")
        rendered = template.render(Context({'persian_num': '۱۲۳،۴۵۶'}))
        assert "123456" in rendered


class TestPersianNumberFormatterHelpers(TestCase):
    """Test Persian number formatter helper functions."""
    
    def test_format_currency_display(self):
        """Test format_currency_display helper function."""
        from zargar.core.persian_fields import format_currency_display
        
        result = format_currency_display(1000000)
        assert result == "۱،۰۰۰،۰۰۰ تومان"
        
        result = format_currency_display(1000000, use_persian_digits=False)
        assert result == "1,000,000 تومان"
        
        result = format_currency_display(None)
        assert result == "۰ تومان"
    
    def test_format_weight_display(self):
        """Test format_weight_display helper function."""
        from zargar.core.persian_fields import format_weight_display
        
        result = format_weight_display(100, 'gram')
        assert result == "۱۰۰ گرم"
        
        result = format_weight_display(1, 'mesghal')
        assert result == "۱ مثقال"
        
        result = format_weight_display(None)
        assert result == "۰ گرم"
    
    def test_format_percentage_display(self):
        """Test format_percentage_display helper function."""
        from zargar.core.persian_fields import format_percentage_display
        
        result = format_percentage_display(25.5)
        assert result == "۲۵.۵٪"
        
        result = format_percentage_display(25.5, use_persian_digits=False)
        assert result == "25.5%"
        
        result = format_percentage_display(None)
        assert result == "۰٪"
    
    def test_get_weight_conversions(self):
        """Test get_weight_conversions helper function."""
        from zargar.core.persian_fields import get_weight_conversions
        
        result = get_weight_conversions(4.608)
        assert 'gram' in result
        assert 'mesghal' in result
        assert 'soot' in result
        assert "۱ مثقال" in result['mesghal']
        
        result = get_weight_conversions(None)
        assert all('۰' in value for value in result.values())
    
    def test_format_gold_price_display(self):
        """Test format_gold_price_display helper function."""
        from zargar.core.persian_fields import format_gold_price_display
        
        result = format_gold_price_display(1000000, 5.5)
        assert 'price_per_gram' in result
        assert 'total_value' in result
        assert 'weight_display' in result
        assert 'weight_mesghal' in result
        assert 'weight_soot' in result
        
        assert "۱،۰۰۰،۰۰۰ تومان" in result['price_per_gram']
        assert "۵،۵۰۰،۰۰۰ تومان" in result['total_value']
        assert "۵.۵ گرم" in result['weight_display']
        
        result = format_gold_price_display(None, None)
        assert all("۰ تومان" in value or "۰ گرم" in value for value in result.values())


class TestPersianNumberFormatterEdgeCases(TestCase):
    """Test edge cases for Persian number formatter."""
    
    def test_very_large_currency_amounts(self):
        """Test formatting very large currency amounts."""
        large_amount = Decimal('999999999999')  # 999 billion
        result = PersianNumberFormatter.format_currency(large_amount)
        assert "۹۹۹،۹۹۹،۹۹۹،۹۹۹ تومان" in result
    
    def test_very_small_weight_values(self):
        """Test formatting very small weight values."""
        small_weight = Decimal('0.001')
        result = PersianNumberFormatter.format_weight(small_weight, 'gram')
        assert "۰.۰۰۱ گرم" in result
    
    def test_zero_values_formatting(self):
        """Test formatting zero values."""
        assert PersianNumberFormatter.format_currency(0) == "۰ تومان"
        assert PersianNumberFormatter.format_weight(0, 'gram') == "۰ گرم"
        assert PersianNumberFormatter.format_percentage(0) == "۰.۰٪"
    
    def test_negative_values_handling(self):
        """Test handling negative values."""
        result = PersianNumberFormatter.format_large_number(-1000)
        assert result.startswith("-")
        assert "۱،۰۰۰" in result
    
    def test_decimal_precision_consistency(self):
        """Test decimal precision consistency."""
        # Test currency with decimals
        result = PersianNumberFormatter.format_currency(
            Decimal('123.456'), show_decimals=True, decimal_places=2
        )
        assert "۱۲۳.۴۶ تومان" in result
        
        # Test weight precision
        result = PersianNumberFormatter.convert_weight(
            Decimal('1'), 'gram', 'soot', precision=2
        )
        assert len(str(result).split('.')[-1]) <= 2
    
    def test_input_validation_edge_cases(self):
        """Test input validation edge cases."""
        # Test empty string
        is_valid, value, error = PersianNumberFormatter.validate_currency_input("")
        assert not is_valid
        assert value is None
        assert "خالی" in error
        
        # Test very large amount
        is_valid, value, error = PersianNumberFormatter.validate_currency_input("999999999999999")
        assert not is_valid
        assert "بیش از حد" in error
        
        # Test negative weight
        is_valid, value, error = PersianNumberFormatter.validate_weight_input("-۱۰", "gram")
        assert not is_valid
        assert "مثبت" in error