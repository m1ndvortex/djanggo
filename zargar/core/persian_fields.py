"""
Django model fields for Persian number formatting and currency system.
"""
from decimal import Decimal
from typing import Optional, Any, Dict, Union
from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from .persian_number_formatter import PersianNumberFormatter


class PersianCurrencyField(models.DecimalField):
    """
    Django model field for Persian currency (Toman) with automatic formatting.
    """
    
    description = _("Persian currency field with Toman formatting")
    
    def __init__(self, *args, **kwargs):
        # Set default decimal places and max digits for currency
        kwargs.setdefault('max_digits', 15)  # Up to 999 trillion Toman
        kwargs.setdefault('decimal_places', 2)  # Support cents if needed
        super().__init__(*args, **kwargs)
    
    def formfield(self, **kwargs):
        """Return a form field for this model field."""
        defaults = {
            'form_class': PersianCurrencyFormField,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)
    
    def to_python(self, value):
        """Convert value to Python Decimal."""
        if value is None:
            return value
        
        # If it's a string with Persian formatting, parse it
        if isinstance(value, str):
            parsed_value = PersianNumberFormatter.parse_persian_number(value)
            if parsed_value is not None:
                value = parsed_value
        
        return super().to_python(value)
    
    def get_prep_value(self, value):
        """Prepare value for database storage."""
        if value is None:
            return value
        
        # Ensure it's a Decimal
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        
        return super().get_prep_value(value)


class PersianWeightField(models.DecimalField):
    """
    Django model field for Persian weight units with conversion support.
    """
    
    description = _("Persian weight field with unit conversion")
    
    def __init__(self, unit='gram', *args, **kwargs):
        self.unit = unit
        # Set default decimal places and max digits for weight
        kwargs.setdefault('max_digits', 10)  # Up to 9,999,999 grams
        kwargs.setdefault('decimal_places', 3)  # Support precise measurements
        super().__init__(*args, **kwargs)
    
    def formfield(self, **kwargs):
        """Return a form field for this model field."""
        defaults = {
            'form_class': PersianWeightFormField,
            'unit': self.unit,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)
    
    def to_python(self, value):
        """Convert value to Python Decimal."""
        if value is None:
            return value
        
        # If it's a string with Persian formatting, parse it
        if isinstance(value, str):
            parsed_value = PersianNumberFormatter.parse_persian_number(value)
            if parsed_value is not None:
                value = parsed_value
        
        return super().to_python(value)
    
    def deconstruct(self):
        """Return field definition for migrations."""
        name, path, args, kwargs = super().deconstruct()
        if self.unit != 'gram':
            kwargs['unit'] = self.unit
        return name, path, args, kwargs


class PersianPercentageField(models.DecimalField):
    """
    Django model field for Persian percentage formatting.
    """
    
    description = _("Persian percentage field")
    
    def __init__(self, *args, **kwargs):
        # Set default decimal places and max digits for percentage
        kwargs.setdefault('max_digits', 5)  # Up to 999.99%
        kwargs.setdefault('decimal_places', 2)  # Support precise percentages
        super().__init__(*args, **kwargs)
    
    def formfield(self, **kwargs):
        """Return a form field for this model field."""
        defaults = {
            'form_class': PersianPercentageFormField,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)
    
    def to_python(self, value):
        """Convert value to Python Decimal."""
        if value is None:
            return value
        
        # If it's a string with Persian formatting, parse it
        if isinstance(value, str):
            # Remove percentage symbol if present
            value = value.replace('٪', '').replace('%', '').strip()
            parsed_value = PersianNumberFormatter.parse_persian_number(value)
            if parsed_value is not None:
                value = parsed_value
        
        return super().to_python(value)


# Form Fields

class PersianCurrencyFormField(forms.DecimalField):
    """
    Form field for Persian currency input with validation.
    """
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_digits', 15)
        kwargs.setdefault('decimal_places', 2)
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        """Convert form input to Python value."""
        if value in self.empty_values:
            return None
        
        # Parse Persian number
        if isinstance(value, str):
            parsed_value = PersianNumberFormatter.parse_persian_number(value)
            if parsed_value is None:
                raise ValidationError(_('مبلغ وارد شده معتبر نیست.'))
            value = parsed_value
        
        return super().to_python(value)
    
    def validate(self, value):
        """Validate the currency value."""
        super().validate(value)
        
        if value is not None:
            # Use the formatter's validation
            is_valid, _, error_message = PersianNumberFormatter.validate_currency_input(str(value))
            if not is_valid and error_message:
                raise ValidationError(error_message)


class PersianWeightFormField(forms.DecimalField):
    """
    Form field for Persian weight input with unit conversion.
    """
    
    def __init__(self, unit='gram', *args, **kwargs):
        self.unit = unit
        kwargs.setdefault('max_digits', 10)
        kwargs.setdefault('decimal_places', 3)
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        """Convert form input to Python value."""
        if value in self.empty_values:
            return None
        
        # Parse Persian number
        if isinstance(value, str):
            parsed_value = PersianNumberFormatter.parse_persian_number(value)
            if parsed_value is None:
                raise ValidationError(_('وزن وارد شده معتبر نیست.'))
            value = parsed_value
        
        return super().to_python(value)
    
    def validate(self, value):
        """Validate the weight value."""
        super().validate(value)
        
        if value is not None:
            # Use the formatter's validation
            is_valid, _, error_message = PersianNumberFormatter.validate_weight_input(str(value), self.unit)
            if not is_valid and error_message:
                raise ValidationError(error_message)


class PersianPercentageFormField(forms.DecimalField):
    """
    Form field for Persian percentage input.
    """
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_digits', 5)
        kwargs.setdefault('decimal_places', 2)
        kwargs.setdefault('min_value', Decimal('0'))
        kwargs.setdefault('max_value', Decimal('100'))
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        """Convert form input to Python value."""
        if value in self.empty_values:
            return None
        
        # Parse Persian number
        if isinstance(value, str):
            # Remove percentage symbols
            value = value.replace('٪', '').replace('%', '').strip()
            parsed_value = PersianNumberFormatter.parse_persian_number(value)
            if parsed_value is None:
                raise ValidationError(_('درصد وارد شده معتبر نیست.'))
            value = parsed_value
        
        return super().to_python(value)


# Widget classes for better form rendering

class PersianCurrencyWidget(forms.TextInput):
    """
    Widget for Persian currency input with formatting hints.
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'persian-currency-input',
            'placeholder': 'مثال: ۱۰۰،۰۰۰ تومان',
            'dir': 'rtl',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def format_value(self, value):
        """Format value for display in the widget."""
        if value is None or value == '':
            return ''
        
        try:
            # Format as Persian currency
            if isinstance(value, (int, float, Decimal)):
                return PersianNumberFormatter.format_currency(value, include_symbol=False)
            return str(value)
        except (ValueError, TypeError):
            return str(value)


class PersianWeightWidget(forms.TextInput):
    """
    Widget for Persian weight input with unit display.
    """
    
    def __init__(self, unit='gram', attrs=None):
        self.unit = unit
        unit_info = PersianNumberFormatter.get_supported_weight_units().get(unit, {})
        unit_name = unit_info.get('name', 'گرم')
        
        default_attrs = {
            'class': 'persian-weight-input',
            'placeholder': f'مثال: ۱۰۰ {unit_name}',
            'dir': 'rtl',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def format_value(self, value):
        """Format value for display in the widget."""
        if value is None or value == '':
            return ''
        
        try:
            # Format as Persian weight
            if isinstance(value, (int, float, Decimal)):
                return PersianNumberFormatter.format_weight(value, self.unit, show_unit_name=False)
            return str(value)
        except (ValueError, TypeError):
            return str(value)


class PersianPercentageWidget(forms.TextInput):
    """
    Widget for Persian percentage input.
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'persian-percentage-input',
            'placeholder': 'مثال: ۲۵٪',
            'dir': 'rtl',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def format_value(self, value):
        """Format value for display in the widget."""
        if value is None or value == '':
            return ''
        
        try:
            # Format as Persian percentage
            if isinstance(value, (int, float, Decimal)):
                return PersianNumberFormatter.format_percentage(value, decimal_places=1).replace('٪', '')
            return str(value)
        except (ValueError, TypeError):
            return str(value)


# Helper functions for templates and views

def format_currency_display(amount: Union[int, float, Decimal, None], 
                          use_persian_digits: bool = True) -> str:
    """
    Helper function to format currency for template display.
    
    Args:
        amount: Currency amount
        use_persian_digits: Whether to use Persian digits
        
    Returns:
        Formatted currency string
    """
    return PersianNumberFormatter.format_currency(amount, use_persian_digits=use_persian_digits)


def format_weight_display(weight: Union[int, float, Decimal, None], 
                         unit: str = 'gram',
                         use_persian_digits: bool = True) -> str:
    """
    Helper function to format weight for template display.
    
    Args:
        weight: Weight value
        unit: Weight unit
        use_persian_digits: Whether to use Persian digits
        
    Returns:
        Formatted weight string
    """
    return PersianNumberFormatter.format_weight(weight, unit, use_persian_digits=use_persian_digits)


def format_percentage_display(percentage: Union[int, float, Decimal, None],
                            use_persian_digits: bool = True) -> str:
    """
    Helper function to format percentage for template display.
    
    Args:
        percentage: Percentage value
        use_persian_digits: Whether to use Persian digits
        
    Returns:
        Formatted percentage string
    """
    return PersianNumberFormatter.format_percentage(percentage, use_persian_digits=use_persian_digits)


def get_weight_conversions(weight_grams: Union[int, float, Decimal, None],
                          use_persian_digits: bool = True) -> Dict[str, str]:
    """
    Helper function to get weight in multiple units for display.
    
    Args:
        weight_grams: Weight in grams
        use_persian_digits: Whether to use Persian digits
        
    Returns:
        Dictionary of weight conversions
    """
    return PersianNumberFormatter.format_weight_with_conversion(
        weight_grams, use_persian_digits=use_persian_digits
    )


def format_gold_price_display(price_per_gram: Union[int, float, Decimal, None],
                            weight_grams: Union[int, float, Decimal, None],
                            use_persian_digits: bool = True) -> Dict[str, str]:
    """
    Helper function to format gold price calculations for display.
    
    Args:
        price_per_gram: Gold price per gram
        weight_grams: Weight in grams
        use_persian_digits: Whether to use Persian digits
        
    Returns:
        Dictionary with formatted gold price information
    """
    return PersianNumberFormatter.format_gold_price(
        price_per_gram, weight_grams, use_persian_digits=use_persian_digits
    )