"""
Simple unit tests for Persian form fields without Django app dependencies.
Tests field functionality in isolation.
"""
import pytest
from datetime import date, datetime
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Configure minimal Django settings
import django
from django.conf import settings
from django.core.exceptions import ValidationError

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='test-secret-key',
        USE_TZ=True,
        USE_I18N=True,
        LANGUAGE_CODE='fa',
        TIME_ZONE='Asia/Tehran',
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
        ],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        }
    )

django.setup()

from zargar.core.fields import (
    PersianDateField, PersianDateTimeField, PersianDecimalField,
    PersianCurrencyField, PersianWeightField, KaratField,
    PersianTextField, PersianPhoneField, PersianEmailField,
    PersianPostalCodeField
)
from zargar.core.calendar_utils import PersianCalendarUtils


class TestPersianDateField:
    """Test Persian date form field."""
    
    def test_field_initialization(self):
        """Test Persian date field initialization."""
        field = PersianDateField()
        
        # Should have Persian help text
        assert 'شمسی' in field.help_text
    
    def test_field_to_python_valid_date(self):
        """Test Persian date field with valid Persian date."""
        field = PersianDateField()
        
        # Test with Persian date string
        result = field.to_python('۱۴۰۳/۰۱/۰۱')
        
        assert isinstance(result, date)
        assert result.year == 2024
        assert result.month == 3
        assert result.day == 20
    
    def test_field_to_python_invalid_date(self):
        """Test Persian date field with invalid Persian date."""
        field = PersianDateField()
        
        # Test with invalid Persian date
        with pytest.raises(ValidationError):
            field.to_python('۱۴۰۳/۱۳/۰۱')  # Invalid month
    
    def test_field_to_python_empty_value(self):
        """Test Persian date field with empty values."""
        field = PersianDateField(required=False)
        
        # Empty string should return None
        result = field.to_python('')
        assert result is None
        
        # None should return None
        result = field.to_python(None)
        assert result is None
    
    def test_field_digit_conversion(self):
        """Test Persian date field digit conversion."""
        field = PersianDateField()
        
        # Persian digits should be converted
        result = field.to_python('۱۴۰۳/۰۱/۰۱')
        assert isinstance(result, date)
        
        # English digits should also work
        result = field.to_python('1403/01/01')
        assert isinstance(result, date)
    
    def test_field_validation_ranges(self):
        """Test Persian date field validation ranges."""
        field = PersianDateField()
        
        # Valid year range
        result = field.to_python('1403/01/01')
        assert isinstance(result, date)
        
        # Invalid year (too old)
        with pytest.raises(ValidationError):
            field.to_python('1200/01/01')
        
        # Invalid month
        with pytest.raises(ValidationError):
            field.to_python('1403/13/01')
        
        # Invalid day
        with pytest.raises(ValidationError):
            field.to_python('1403/01/32')


class TestPersianDateTimeField:
    """Test Persian datetime form field."""
    
    def test_field_initialization(self):
        """Test Persian datetime field initialization."""
        field = PersianDateTimeField()
        
        # Should have Persian help text
        assert 'شمسی' in field.help_text
    
    def test_field_to_python_valid_datetime(self):
        """Test Persian datetime field with valid Persian datetime."""
        field = PersianDateTimeField()
        
        # Test with Persian datetime string
        result = field.to_python('۱۴۰۳/۰۱/۰۱ - ۱۲:۳۰')
        
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 3
        assert result.day == 20
        assert result.hour == 12
        assert result.minute == 30
    
    def test_field_to_python_invalid_datetime(self):
        """Test Persian datetime field with invalid format."""
        field = PersianDateTimeField()
        
        # Test with invalid format
        with pytest.raises(ValidationError):
            field.to_python('invalid_datetime')


class TestPersianDecimalField:
    """Test Persian decimal form field."""
    
    def test_field_initialization(self):
        """Test Persian decimal field initialization."""
        field = PersianDecimalField()
        
        # Should have Persian help text
        assert 'فارسی' in field.help_text
    
    def test_field_to_python_valid_number(self):
        """Test Persian decimal field with valid Persian number."""
        field = PersianDecimalField()
        
        # Test with Persian digits
        result = field.to_python('۱۲۳٫۴۵')
        
        assert float(result) == 123.45
    
    def test_field_to_python_with_separators(self):
        """Test Persian decimal field with thousand separators."""
        field = PersianDecimalField()
        
        # Test with Persian thousand separators
        result = field.to_python('۱٬۲۳۴٫۵۶')
        
        assert float(result) == 1234.56
    
    def test_field_to_python_invalid_number(self):
        """Test Persian decimal field with invalid number."""
        field = PersianDecimalField()
        
        # Test with invalid number
        with pytest.raises(ValidationError):
            field.to_python('invalid_number')


class TestPersianCurrencyField:
    """Test Persian currency form field."""
    
    def test_field_initialization(self):
        """Test Persian currency field initialization."""
        field = PersianCurrencyField()
        
        # Should have Toman help text
        assert 'تومان' in field.help_text
        assert field.decimal_places == 0
        assert field.max_digits == 15
    
    def test_field_to_python_with_currency_text(self):
        """Test Persian currency field with currency text."""
        field = PersianCurrencyField()
        
        # Test with currency text
        result = field.to_python('۱۰۰٬۰۰۰ تومان')
        
        assert int(result) == 100000
    
    def test_field_validation_negative(self):
        """Test Persian currency field negative validation."""
        field = PersianCurrencyField()
        
        # Negative values should be invalid
        with pytest.raises(ValidationError):
            field.clean(-1000)


class TestPersianWeightField:
    """Test Persian weight form field."""
    
    def test_field_initialization(self):
        """Test Persian weight field initialization."""
        field = PersianWeightField()
        
        # Should have gram help text
        assert 'گرم' in field.help_text
        assert field.decimal_places == 3
        assert field.max_digits == 10
    
    def test_field_to_python_with_weight_text(self):
        """Test Persian weight field with weight text."""
        field = PersianWeightField()
        
        # Test with weight text
        result = field.to_python('۱۲٫۵ گرم')
        
        assert float(result) == 12.5
    
    def test_field_validation_negative(self):
        """Test Persian weight field negative validation."""
        field = PersianWeightField()
        
        # Negative values should be invalid
        with pytest.raises(ValidationError):
            field.clean(-10.5)
    
    def test_field_validation_too_heavy(self):
        """Test Persian weight field maximum weight validation."""
        field = PersianWeightField()
        
        # Values over 10kg should be invalid
        with pytest.raises(ValidationError):
            field.clean(15000)  # 15kg


class TestKaratField:
    """Test gold karat form field."""
    
    def test_field_initialization(self):
        """Test karat field initialization."""
        field = KaratField()
        
        # Should have Persian help text
        assert 'عیار' in field.help_text
    
    def test_field_validation_valid_karats(self):
        """Test karat field with valid karat values."""
        field = KaratField()
        
        # Valid karat values
        valid_karats = [18, 21, 22, 24]
        for karat in valid_karats:
            field.validate(karat)  # Should not raise
    
    def test_field_validation_invalid_karats(self):
        """Test karat field with invalid karat values."""
        field = KaratField()
        
        # Invalid karat values
        invalid_karats = [10, 14, 16, 20, 25]
        for karat in invalid_karats:
            with pytest.raises(ValidationError):
                field.validate(karat)


class TestPersianTextField:
    """Test Persian text form field."""
    
    def test_field_initialization(self):
        """Test Persian text field initialization."""
        field = PersianTextField()
        
        # Should have Persian help text
        assert 'فارسی' in field.help_text
    
    def test_field_validation_persian_text(self):
        """Test Persian text field with Persian text."""
        field = PersianTextField()
        
        # Persian text should be valid
        field.validate('سلام دنیا')  # Should not raise


class TestPersianPhoneField:
    """Test Persian phone form field."""
    
    def test_field_initialization(self):
        """Test Persian phone field initialization."""
        field = PersianPhoneField()
        
        # Should have phone help text
        assert 'تلفن' in field.help_text
        assert field.max_length == 15
    
    def test_field_to_python_persian_digits(self):
        """Test Persian phone field with Persian digits."""
        field = PersianPhoneField()
        
        # Test with Persian digits
        result = field.to_python('۰۹۱۲۳۴۵۶۷۸۹')
        
        assert result == '09123456789'
    
    def test_field_validation_valid_mobile(self):
        """Test Persian phone field with valid mobile number."""
        field = PersianPhoneField()
        
        # Valid mobile number
        field.validate('09123456789')  # Should not raise
    
    def test_field_validation_invalid_phone(self):
        """Test Persian phone field with invalid phone number."""
        field = PersianPhoneField()
        
        # Invalid phone number
        with pytest.raises(ValidationError):
            field.validate('123456')


class TestPersianEmailField:
    """Test Persian email form field."""
    
    def test_field_initialization(self):
        """Test Persian email field initialization."""
        field = PersianEmailField()
        
        # Should have email help text
        assert 'ایمیل' in field.help_text
    
    def test_field_validation_valid_email(self):
        """Test Persian email field with valid email."""
        field = PersianEmailField()
        
        # Valid email
        result = field.clean('test@example.com')  # Should not raise
        assert result == 'test@example.com'
    
    def test_field_validation_invalid_email(self):
        """Test Persian email field with invalid email."""
        field = PersianEmailField()
        
        # Invalid email
        with pytest.raises(ValidationError):
            field.clean('invalid_email')


class TestPersianPostalCodeField:
    """Test Persian postal code form field."""
    
    def test_field_initialization(self):
        """Test Persian postal code field initialization."""
        field = PersianPostalCodeField()
        
        # Should have postal code help text
        assert 'پستی' in field.help_text
        assert field.max_length == 10
        assert field.min_length == 10
    
    def test_field_to_python_persian_digits(self):
        """Test Persian postal code field with Persian digits."""
        field = PersianPostalCodeField()
        
        # Test with Persian digits
        result = field.to_python('۱۲۳۴۵۶۷۸۹۰')
        
        assert result == '1234567890'
    
    def test_field_validation_valid_postal_code(self):
        """Test Persian postal code field with valid postal code."""
        field = PersianPostalCodeField()
        
        # Valid 10-digit postal code
        field.validate('1234567890')  # Should not raise
    
    def test_field_validation_invalid_postal_code(self):
        """Test Persian postal code field with invalid postal code."""
        field = PersianPostalCodeField()
        
        # Invalid postal code (wrong length)
        with pytest.raises(ValidationError):
            field.validate('12345')


class TestFieldIntegration:
    """Test integration between fields and calendar utilities."""
    
    def test_date_field_calendar_utils_integration(self):
        """Test integration between date field and calendar utils."""
        field = PersianDateField()
        
        # Test that field uses calendar utils correctly
        result = field.to_python('۱۴۰۳/۰۱/۰۱')
        
        # Should match calendar utils conversion
        expected = PersianCalendarUtils.shamsi_to_gregorian(1403, 1, 1)
        assert result == expected
    
    def test_field_digit_conversion_integration(self):
        """Test field digit conversion with calendar utils."""
        field = PersianDecimalField()
        
        # Test digit conversion
        result = field.to_python('۱۲۳٫۴۵')
        
        # Should correctly convert Persian digits
        assert float(result) == 123.45


if __name__ == '__main__':
    pytest.main([__file__, '-v'])