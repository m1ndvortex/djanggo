"""
Persian form fields for ZARGAR jewelry SaaS platform.
"""
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from decimal import Decimal, InvalidOperation
import jdatetime
import re
from .widgets import (
    PersianDateWidget, PersianDateTimeWidget, PersianNumberWidget,
    PersianCurrencyWidget, PersianWeightWidget, PersianTextWidget,
    PersianTextareaWidget, KaratSelectWidget
)


class PersianDateField(forms.DateField):
    """
    Persian date field with Shamsi calendar support.
    """
    
    widget = PersianDateWidget
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('help_text', 'تاریخ را به صورت شمسی وارد کنید (مثال: ۱۴۰۳/۰۱/۰۱)')
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        """Convert Persian date string to Python date object."""
        if not value:
            return None
        
        if hasattr(value, 'strftime'):
            return value
        
        # Convert Persian digits to English
        english_value = self.convert_to_english_digits(str(value))
        
        # Try to parse Persian date
        try:
            # Remove any extra characters
            english_value = re.sub(r'[^\d/]', '', english_value)
            
            if '/' in english_value:
                parts = english_value.split('/')
                if len(parts) == 3:
                    year, month, day = map(int, parts)
                    
                    # Validate Persian date ranges
                    if not (1300 <= year <= 1500):
                        raise ValidationError(_('سال باید بین ۱۳۰۰ تا ۱۵۰۰ باشد.'))
                    
                    if not (1 <= month <= 12):
                        raise ValidationError(_('ماه باید بین ۱ تا ۱۲ باشد.'))
                    
                    if not (1 <= day <= 31):
                        raise ValidationError(_('روز باید بین ۱ تا ۳۱ باشد.'))
                    
                    # Create Persian date and convert to Gregorian
                    persian_date = jdatetime.date(year, month, day)
                    return persian_date.togregorian()
        except ValueError as e:
            raise ValidationError(_('تاریخ وارد شده معتبر نیست. لطفاً تاریخ را به صورت صحیح وارد کنید.'))
        
        raise ValidationError(_('فرمت تاریخ نامعتبر است. لطفاً از فرمت ۱۴۰۳/۰۱/۰۱ استفاده کنید.'))
    
    def convert_to_english_digits(self, text):
        """Convert Persian digits to English digits."""
        english_digits = '0123456789'
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        
        for i, digit in enumerate(persian_digits):
            text = text.replace(digit, english_digits[i])
        
        return text


class PersianDateTimeField(forms.DateTimeField):
    """
    Persian datetime field with Shamsi calendar support.
    """
    
    widget = PersianDateTimeWidget
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('help_text', 'تاریخ و زمان را به صورت شمسی وارد کنید (مثال: ۱۴۰۳/۰۱/۰۱ - ۱۲:۳۰)')
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        """Convert Persian datetime string to Python datetime object."""
        if not value:
            return None
        
        if hasattr(value, 'strftime'):
            return value
        
        # Convert Persian digits to English
        english_value = self.convert_to_english_digits(str(value))
        
        try:
            # Parse Persian datetime format: YYYY/MM/DD - HH:MM
            if ' - ' in english_value:
                date_part, time_part = english_value.split(' - ')
                
                # Parse date
                date_parts = date_part.split('/')
                if len(date_parts) == 3:
                    year, month, day = map(int, date_parts)
                    
                    # Parse time
                    time_parts = time_part.split(':')
                    if len(time_parts) == 2:
                        hour, minute = map(int, time_parts)
                        
                        # Create Persian datetime and convert to Gregorian
                        persian_datetime = jdatetime.datetime(year, month, day, hour, minute)
                        return persian_datetime.togregorian()
        except ValueError:
            pass
        
        raise ValidationError(_('فرمت تاریخ و زمان نامعتبر است. لطفاً از فرمت ۱۴۰۳/۰۱/۰۱ - ۱۲:۳۰ استفاده کنید.'))
    
    def convert_to_english_digits(self, text):
        """Convert Persian digits to English digits."""
        english_digits = '0123456789'
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        
        for i, digit in enumerate(persian_digits):
            text = text.replace(digit, english_digits[i])
        
        return text


class PersianDecimalField(forms.DecimalField):
    """
    Persian decimal field with Persian number formatting.
    """
    
    widget = PersianNumberWidget
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('help_text', 'عدد را با ارقام فارسی وارد کنید')
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        """Convert Persian formatted number to Decimal."""
        if not value:
            return None
        
        if isinstance(value, Decimal):
            return value
        
        # Convert Persian digits to English
        english_value = self.convert_to_english_digits(str(value))
        
        # Remove thousand separators
        english_value = english_value.replace(',', '')
        english_value = english_value.replace('٬', '')
        
        # Convert decimal separator
        english_value = english_value.replace('٫', '.')
        
        # Remove any non-numeric characters except decimal point and minus
        english_value = re.sub(r'[^\d.-]', '', english_value)
        
        try:
            return Decimal(english_value)
        except (InvalidOperation, ValueError):
            raise ValidationError(_('عدد وارد شده معتبر نیست.'))
    
    def convert_to_english_digits(self, text):
        """Convert Persian digits to English digits."""
        english_digits = '0123456789'
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        
        for i, digit in enumerate(persian_digits):
            text = text.replace(digit, english_digits[i])
        
        return text


class PersianCurrencyField(PersianDecimalField):
    """
    Persian currency field with Toman formatting.
    """
    
    widget = PersianCurrencyWidget
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('help_text', 'مبلغ را به تومان وارد کنید')
        kwargs.setdefault('decimal_places', 0)
        kwargs.setdefault('max_digits', 15)
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        """Convert Persian currency to Decimal."""
        if not value:
            return None
        
        # Remove currency text
        if isinstance(value, str):
            value = value.replace('تومان', '').strip()
        
        return super().to_python(value)
    
    def validate(self, value):
        """Validate currency value."""
        super().validate(value)
        
        if value is not None and value < 0:
            raise ValidationError(_('مبلغ نمی‌تواند منفی باشد.'))


class PersianWeightField(PersianDecimalField):
    """
    Persian weight field with gram formatting and traditional unit conversion.
    """
    
    widget = PersianWeightWidget
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('help_text', 'وزن را به گرم وارد کنید')
        kwargs.setdefault('decimal_places', 3)
        kwargs.setdefault('max_digits', 10)
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        """Convert Persian weight to Decimal."""
        if not value:
            return None
        
        # Remove weight unit text
        if isinstance(value, str):
            value = value.replace('گرم', '').strip()
            value = value.replace('مثقال', '').strip()
            value = value.replace('سوت', '').strip()
        
        return super().to_python(value)
    
    def validate(self, value):
        """Validate weight value."""
        super().validate(value)
        
        if value is not None:
            if value < 0:
                raise ValidationError(_('وزن نمی‌تواند منفی باشد.'))
            
            if value > 10000:  # 10kg limit for jewelry items
                raise ValidationError(_('وزن نمی‌تواند بیش از ۱۰ کیلوگرم باشد.'))


class KaratField(forms.IntegerField):
    """
    Gold karat field with validation for common karat values.
    """
    
    widget = KaratSelectWidget
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('help_text', 'عیار طلا را انتخاب کنید')
        super().__init__(*args, **kwargs)
    
    def validate(self, value):
        """Validate karat value."""
        super().validate(value)
        
        if value is not None:
            valid_karats = [18, 21, 22, 24]
            if value not in valid_karats:
                raise ValidationError(_('عیار باید یکی از مقادیر ۱۸، ۲۱، ۲۲ یا ۲۴ باشد.'))


class PersianTextField(forms.CharField):
    """
    Persian text field with RTL support and Persian validation.
    """
    
    widget = PersianTextWidget
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('help_text', 'متن را به فارسی وارد کنید')
        super().__init__(*args, **kwargs)
    
    def validate(self, value):
        """Validate Persian text."""
        super().validate(value)
        
        if value:
            # Check if text contains Persian characters
            persian_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
            if not persian_pattern.search(value) and len(value) > 2:
                # Only warn if text is longer than 2 characters (to allow codes/numbers)
                pass  # We'll be lenient and not enforce Persian-only text


class PersianPhoneField(forms.CharField):
    """
    Persian phone number field with Iranian phone number validation.
    """
    
    widget = PersianTextWidget
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('help_text', 'شماره تلفن را وارد کنید (مثال: ۰۹۱۲۳۴۵۶۷۸۹)')
        kwargs.setdefault('max_length', 15)
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        """Convert Persian phone number to standard format."""
        if not value:
            return None
        
        # Convert Persian digits to English
        english_value = self.convert_to_english_digits(str(value))
        
        # Remove any non-digit characters
        english_value = re.sub(r'[^\d]', '', english_value)
        
        return english_value
    
    def validate(self, value):
        """Validate Iranian phone number."""
        super().validate(value)
        
        if value:
            # Iranian mobile number patterns
            mobile_pattern = re.compile(r'^09\d{9}$')
            # Iranian landline patterns (with area codes)
            landline_pattern = re.compile(r'^0\d{2,3}\d{7,8}$')
            
            if not (mobile_pattern.match(value) or landline_pattern.match(value)):
                raise ValidationError(_('شماره تلفن وارد شده معتبر نیست.'))
    
    def convert_to_english_digits(self, text):
        """Convert Persian digits to English digits."""
        english_digits = '0123456789'
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        
        for i, digit in enumerate(persian_digits):
            text = text.replace(digit, english_digits[i])
        
        return text


class PersianEmailField(forms.EmailField):
    """
    Email field with Persian error messages.
    """
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('help_text', 'آدرس ایمیل معتبر وارد کنید')
        super().__init__(*args, **kwargs)
    
    def validate(self, value):
        """Validate email with Persian error messages."""
        if value:
            try:
                super().validate(value)
            except ValidationError:
                raise ValidationError(_('آدرس ایمیل وارد شده معتبر نیست.'))


class PersianPostalCodeField(forms.CharField):
    """
    Iranian postal code field with validation.
    """
    
    widget = PersianTextWidget
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('help_text', 'کد پستی ۱۰ رقمی وارد کنید')
        kwargs.setdefault('max_length', 10)
        kwargs.setdefault('min_length', 10)
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        """Convert Persian postal code to standard format."""
        if not value:
            return None
        
        # Convert Persian digits to English
        english_value = self.convert_to_english_digits(str(value))
        
        # Remove any non-digit characters
        english_value = re.sub(r'[^\d]', '', english_value)
        
        return english_value
    
    def validate(self, value):
        """Validate Iranian postal code."""
        super().validate(value)
        
        if value:
            # Iranian postal code is exactly 10 digits
            if not re.match(r'^\d{10}$', value):
                raise ValidationError(_('کد پستی باید دقیقاً ۱۰ رقم باشد.'))
    
    def convert_to_english_digits(self, text):
        """Convert Persian digits to English digits."""
        english_digits = '0123456789'
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        
        for i, digit in enumerate(persian_digits):
            text = text.replace(digit, english_digits[i])
        
        return text