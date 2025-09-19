"""
Persian form widgets for ZARGAR jewelry SaaS platform.
"""
from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
import jdatetime


class PersianDateWidget(forms.DateInput):
    """
    Persian date picker widget with Shamsi calendar support.
    """
    
    def __init__(self, attrs=None, format=None):
        default_attrs = {
            'class': 'persian-date-input',
            'placeholder': '۱۴۰۳/۰۱/۰۱',
            'data-persian-date-picker': '',
            'autocomplete': 'off',
        }
        if attrs:
            default_attrs.update(attrs)
        
        super().__init__(attrs=default_attrs, format=format)
    
    def format_value(self, value):
        """Format the value for display in Persian."""
        if value is None:
            return ''
        
        if hasattr(value, 'strftime'):
            # Convert Gregorian to Persian
            try:
                persian_date = jdatetime.date.fromgregorian(date=value)
                formatted = persian_date.strftime('%Y/%m/%d')
                return self.convert_to_persian_digits(formatted)
            except (ValueError, AttributeError):
                return str(value)
        
        return str(value)
    
    def value_from_datadict(self, data, files, name):
        """Convert Persian date input back to Gregorian."""
        value = data.get(name)
        if not value:
            return None
        
        try:
            # Convert Persian digits to English
            english_value = self.convert_to_english_digits(value)
            
            # Parse Persian date
            parts = english_value.split('/')
            if len(parts) == 3:
                year, month, day = map(int, parts)
                persian_date = jdatetime.date(year, month, day)
                return persian_date.togregorian()
        except (ValueError, AttributeError):
            pass
        
        return value
    
    def convert_to_persian_digits(self, text):
        """Convert English digits to Persian digits."""
        english_digits = '0123456789'
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        
        for i, digit in enumerate(english_digits):
            text = text.replace(digit, persian_digits[i])
        
        return text
    
    def convert_to_english_digits(self, text):
        """Convert Persian digits to English digits."""
        english_digits = '0123456789'
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        
        for i, digit in enumerate(persian_digits):
            text = text.replace(digit, english_digits[i])
        
        return text


class PersianDateTimeWidget(forms.DateTimeInput):
    """
    Persian datetime picker widget with Shamsi calendar support.
    """
    
    def __init__(self, attrs=None, format=None):
        default_attrs = {
            'class': 'persian-datetime-input',
            'placeholder': '۱۴۰۳/۰۱/۰۱ - ۱۲:۳۰',
            'data-persian-datetime-picker': '',
            'autocomplete': 'off',
        }
        if attrs:
            default_attrs.update(attrs)
        
        super().__init__(attrs=default_attrs, format=format)
    
    def format_value(self, value):
        """Format the value for display in Persian."""
        if value is None:
            return ''
        
        if hasattr(value, 'strftime'):
            try:
                persian_datetime = jdatetime.datetime.fromgregorian(datetime=value)
                formatted = persian_datetime.strftime('%Y/%m/%d - %H:%M')
                return self.convert_to_persian_digits(formatted)
            except (ValueError, AttributeError):
                return str(value)
        
        return str(value)
    
    def convert_to_persian_digits(self, text):
        """Convert English digits to Persian digits."""
        english_digits = '0123456789'
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        
        for i, digit in enumerate(english_digits):
            text = text.replace(digit, persian_digits[i])
        
        return text


class PersianNumberWidget(forms.NumberInput):
    """
    Persian number input widget with automatic formatting.
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'persian-number-input',
            'data-persian-number-input': '',
            'dir': 'rtl',
            'style': 'text-align: right;',
        }
        if attrs:
            default_attrs.update(attrs)
        
        super().__init__(attrs=default_attrs)
    
    def format_value(self, value):
        """Format the value for display in Persian."""
        if value is None or value == '':
            return ''
        
        try:
            # Format with thousand separators
            formatted = f"{float(value):,.0f}"
            
            # Convert to Persian digits
            persian_formatted = self.convert_to_persian_digits(formatted)
            
            # Replace comma with Persian thousand separator
            persian_formatted = persian_formatted.replace(',', '٬')
            
            return persian_formatted
        except (ValueError, TypeError):
            return str(value)
    
    def value_from_datadict(self, data, files, name):
        """Convert Persian formatted number back to numeric value."""
        value = data.get(name)
        if not value:
            return None
        
        try:
            # Convert Persian digits to English
            english_value = self.convert_to_english_digits(value)
            
            # Remove thousand separators
            english_value = english_value.replace(',', '')
            english_value = english_value.replace('٬', '')
            
            # Convert decimal separator
            english_value = english_value.replace('٫', '.')
            
            return float(english_value)
        except (ValueError, TypeError):
            return value
    
    def convert_to_persian_digits(self, text):
        """Convert English digits to Persian digits."""
        english_digits = '0123456789'
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        
        for i, digit in enumerate(english_digits):
            text = text.replace(digit, persian_digits[i])
        
        return text
    
    def convert_to_english_digits(self, text):
        """Convert Persian digits to English digits."""
        english_digits = '0123456789'
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        
        for i, digit in enumerate(persian_digits):
            text = text.replace(digit, english_digits[i])
        
        return text


class PersianCurrencyWidget(PersianNumberWidget):
    """
    Persian currency input widget with Toman formatting.
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'placeholder': '۱۰۰٬۰۰۰ تومان',
        }
        if attrs:
            default_attrs.update(attrs)
        
        super().__init__(attrs=default_attrs)
    
    def format_value(self, value):
        """Format the value as Persian currency."""
        if value is None or value == '':
            return ''
        
        try:
            formatted = super().format_value(value)
            return f"{formatted} تومان" if formatted else ''
        except (ValueError, TypeError):
            return str(value)


class PersianWeightWidget(PersianNumberWidget):
    """
    Persian weight input widget with gram formatting.
    """
    
    def __init__(self, attrs=None, show_mithqal=False):
        default_attrs = {
            'placeholder': '۱۰٫۵۰۰ گرم',
            'step': '0.001',
        }
        if attrs:
            default_attrs.update(attrs)
        
        self.show_mithqal = show_mithqal
        super().__init__(attrs=default_attrs)
    
    def format_value(self, value):
        """Format the value as Persian weight."""
        if value is None or value == '':
            return ''
        
        try:
            # Format with 3 decimal places for weight
            formatted = f"{float(value):.3f}"
            
            # Convert to Persian digits
            persian_formatted = self.convert_to_persian_digits(formatted)
            
            # Replace decimal point with Persian decimal separator
            persian_formatted = persian_formatted.replace('.', '٫')
            
            return f"{persian_formatted} گرم"
        except (ValueError, TypeError):
            return str(value)


class PersianTextWidget(forms.TextInput):
    """
    Persian text input widget with RTL support.
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'persian-text-input',
            'dir': 'rtl',
            'style': 'text-align: right;',
        }
        if attrs:
            default_attrs.update(attrs)
        
        super().__init__(attrs=default_attrs)


class PersianTextareaWidget(forms.Textarea):
    """
    Persian textarea widget with RTL support.
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'persian-textarea',
            'dir': 'rtl',
            'style': 'text-align: right;',
            'rows': 4,
        }
        if attrs:
            default_attrs.update(attrs)
        
        super().__init__(attrs=default_attrs)


class PersianSelectWidget(forms.Select):
    """
    Persian select widget with RTL support.
    """
    
    def __init__(self, attrs=None, choices=()):
        default_attrs = {
            'class': 'persian-select',
            'dir': 'rtl',
        }
        if attrs:
            default_attrs.update(attrs)
        
        super().__init__(attrs=default_attrs, choices=choices)


class PersianCheckboxWidget(forms.CheckboxInput):
    """
    Persian checkbox widget with RTL support.
    """
    
    def __init__(self, attrs=None, check_test=None):
        default_attrs = {
            'class': 'persian-checkbox',
        }
        if attrs:
            default_attrs.update(attrs)
        
        super().__init__(attrs=default_attrs, check_test=check_test)


class PersianRadioSelectWidget(forms.RadioSelect):
    """
    Persian radio select widget with RTL support.
    """
    
    def __init__(self, attrs=None, choices=()):
        default_attrs = {
            'class': 'persian-radio-select',
        }
        if attrs:
            default_attrs.update(attrs)
        
        super().__init__(attrs=default_attrs, choices=choices)


class KaratSelectWidget(PersianSelectWidget):
    """
    Specialized widget for gold karat selection.
    """
    
    def __init__(self, attrs=None):
        # Common gold karat values in Iran
        karat_choices = [
            ('', 'انتخاب عیار'),
            (18, 'عیار ۱۸'),
            (21, 'عیار ۲۱'),
            (22, 'عیار ۲۲'),
            (24, 'عیار ۲۴'),
        ]
        
        super().__init__(attrs=attrs, choices=karat_choices)
    
    def format_value(self, value):
        """Format karat value in Persian."""
        if value is None or value == '':
            return ''
        
        try:
            karat_num = int(value)
            persian_num = self.convert_to_persian_digits(str(karat_num))
            return f"عیار {persian_num}"
        except (ValueError, TypeError):
            return str(value)
    
    def convert_to_persian_digits(self, text):
        """Convert English digits to Persian digits."""
        english_digits = '0123456789'
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        
        for i, digit in enumerate(english_digits):
            text = text.replace(digit, persian_digits[i])
        
        return text