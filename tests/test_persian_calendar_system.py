"""
Unit tests for Persian calendar system integration in ZARGAR jewelry SaaS platform.
Tests calendar conversion utilities, model fields, and widgets.
"""
import pytest
from datetime import date, datetime, timedelta
from django.test import TestCase, override_settings
from django.core.exceptions import ValidationError
from django.forms import Form
from django.db import models
from django.conf import settings

# Configure Django settings for testing
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'zargar.core',
        ],
        SECRET_KEY='test-secret-key',
        USE_TZ=True,
        USE_I18N=True,
        LANGUAGE_CODE='fa',
        TIME_ZONE='Asia/Tehran',
    )

import django
django.setup()

from zargar.core.calendar_utils import PersianCalendarUtils, PersianDateRange
from zargar.core.model_fields import (
    PersianDateField, PersianDateTimeField, 
    PersianFiscalYearField, PersianQuarterField
)
from zargar.core.fields import PersianDateField as PersianDateFormField
from zargar.core.widgets import PersianDateWidget


class TestPersianCalendarUtils(TestCase):
    """Test Persian calendar utility functions."""
    
    def test_shamsi_to_gregorian_conversion(self):
        """Test conversion from Shamsi to Gregorian dates."""
        # Test known date conversions
        test_cases = [
            # (Persian year, month, day) -> Expected Gregorian date
            ((1403, 1, 1), date(2024, 3, 20)),  # Nowruz 1403
            ((1403, 6, 31), date(2024, 9, 21)), # End of summer 1403
            ((1403, 12, 29), date(2025, 3, 19)), # End of year 1403 (non-leap)
            ((1400, 1, 1), date(2021, 3, 21)),  # Nowruz 1400
        ]
        
        for persian_date, expected_gregorian in test_cases:
            year, month, day = persian_date
            result = PersianCalendarUtils.shamsi_to_gregorian(year, month, day)
            self.assertEqual(result, expected_gregorian, 
                           f"Failed for Persian date {persian_date}")
    
    def test_gregorian_to_shamsi_conversion(self):
        """Test conversion from Gregorian to Shamsi dates."""
        test_cases = [
            # Gregorian date -> Expected (Persian year, month, day)
            (date(2024, 3, 20), (1403, 1, 1)),   # Nowruz 1403
            (date(2024, 9, 21), (1403, 6, 31)),  # End of summer 1403
            (date(2025, 3, 19), (1403, 12, 29)), # End of year 1403
            (date(2021, 3, 21), (1400, 1, 1)),   # Nowruz 1400
        ]
        
        for gregorian_date, expected_persian in test_cases:
            result = PersianCalendarUtils.gregorian_to_shamsi(gregorian_date)
            self.assertEqual(result, expected_persian,
                           f"Failed for Gregorian date {gregorian_date}")
    
    def test_shamsi_to_hijri_conversion(self):
        """Test conversion from Shamsi to Hijri dates."""
        # Test a known conversion
        persian_date = (1403, 1, 1)  # Nowruz 1403
        hijri_result = PersianCalendarUtils.shamsi_to_hijri(*persian_date)
        
        # Verify it's a valid Hijri date tuple
        self.assertIsInstance(hijri_result, tuple)
        self.assertEqual(len(hijri_result), 3)
        
        hijri_year, hijri_month, hijri_day = hijri_result
        self.assertIsInstance(hijri_year, int)
        self.assertIsInstance(hijri_month, int)
        self.assertIsInstance(hijri_day, int)
        
        # Verify reasonable ranges
        self.assertTrue(1400 <= hijri_year <= 1500)
        self.assertTrue(1 <= hijri_month <= 12)
        self.assertTrue(1 <= hijri_day <= 31)
    
    def test_hijri_to_shamsi_conversion(self):
        """Test conversion from Hijri to Shamsi dates."""
        # Test a known Hijri date
        hijri_date = (1445, 9, 10)  # A date in Ramadan 1445
        persian_result = PersianCalendarUtils.hijri_to_shamsi(*hijri_date)
        
        # Verify it's a valid Persian date tuple
        self.assertIsInstance(persian_result, tuple)
        self.assertEqual(len(persian_result), 3)
        
        persian_year, persian_month, persian_day = persian_result
        self.assertIsInstance(persian_year, int)
        self.assertIsInstance(persian_month, int)
        self.assertIsInstance(persian_day, int)
        
        # Verify reasonable ranges
        self.assertTrue(1400 <= persian_year <= 1450)
        self.assertTrue(1 <= persian_month <= 12)
        self.assertTrue(1 <= persian_day <= 31)
    
    def test_format_persian_date(self):
        """Test Persian date formatting in various styles."""
        test_date = (1403, 1, 15)  # 15 Farvardin 1403
        
        # Test numeric format
        numeric_result = PersianCalendarUtils.format_persian_date(
            test_date, format_style='numeric'
        )
        self.assertEqual(numeric_result, '۱۴۰۳/۰۱/۱۵')
        
        # Test full format
        full_result = PersianCalendarUtils.format_persian_date(
            test_date, format_style='full'
        )
        self.assertEqual(full_result, '۱۵ فروردین ۱۴۰۳')
        
        # Test short format
        short_result = PersianCalendarUtils.format_persian_date(
            test_date, format_style='short'
        )
        self.assertEqual(short_result, '۱۵ فروردین ۱۴۰۳')
    
    def test_format_persian_date_with_weekday(self):
        """Test Persian date formatting with weekday."""
        test_date = (1403, 1, 1)  # Nowruz 1403
        
        result = PersianCalendarUtils.format_persian_date(
            test_date, include_weekday=True, format_style='full'
        )
        
        # Should include weekday name
        self.assertIn('،', result)  # Persian comma separator
        weekdays = PersianCalendarUtils.PERSIAN_WEEKDAYS
        self.assertTrue(any(weekday in result for weekday in weekdays))
    
    def test_format_hijri_date(self):
        """Test Hijri date formatting."""
        hijri_date = (1445, 9, 15)  # 15 Ramadan 1445
        
        result = PersianCalendarUtils.format_hijri_date(hijri_date)
        
        # Should contain Persian digits and Hijri month name
        self.assertIn('۱۵', result)  # Persian day
        self.assertIn('۱۴۴۵', result)  # Persian year
        self.assertIn('رمضان', result)  # Ramadan month name
        self.assertIn('ه.ق', result)  # Hijri indicator
    
    def test_get_current_persian_date(self):
        """Test getting current Persian date."""
        result = PersianCalendarUtils.get_current_persian_date()
        
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        
        year, month, day = result
        self.assertTrue(1400 <= year <= 1450)  # Reasonable range
        self.assertTrue(1 <= month <= 12)
        self.assertTrue(1 <= day <= 31)
    
    def test_get_persian_fiscal_year(self):
        """Test Persian fiscal year calculation."""
        # Test with specific date
        test_date = (1403, 6, 15)  # Middle of year 1403
        start_year, end_year = PersianCalendarUtils.get_persian_fiscal_year(test_date)
        
        self.assertEqual(start_year, 1403)
        self.assertEqual(end_year, 1403)
        
        # Test with current date
        current_fiscal = PersianCalendarUtils.get_persian_fiscal_year()
        self.assertIsInstance(current_fiscal, tuple)
        self.assertEqual(len(current_fiscal), 2)
    
    def test_get_persian_month_days(self):
        """Test getting number of days in Persian months."""
        # Test first 6 months (31 days each)
        for month in range(1, 7):
            days = PersianCalendarUtils.get_persian_month_days(1403, month)
            self.assertEqual(days, 31, f"Month {month} should have 31 days")
        
        # Test months 7-11 (30 days each)
        for month in range(7, 12):
            days = PersianCalendarUtils.get_persian_month_days(1403, month)
            self.assertEqual(days, 30, f"Month {month} should have 30 days")
        
        # Test Esfand (month 12) - varies by leap year
        esfand_days = PersianCalendarUtils.get_persian_month_days(1403, 12)
        self.assertIn(esfand_days, [29, 30], "Esfand should have 29 or 30 days")
    
    def test_is_persian_leap_year(self):
        """Test Persian leap year detection."""
        # Test known leap years and non-leap years
        test_cases = [
            (1403, False),  # Non-leap year
            (1404, True),   # Leap year
            (1400, True),   # Leap year
            (1401, False),  # Non-leap year
        ]
        
        for year, expected_leap in test_cases:
            result = PersianCalendarUtils.is_persian_leap_year(year)
            self.assertEqual(result, expected_leap, 
                           f"Year {year} leap status incorrect")
    
    def test_get_persian_holidays(self):
        """Test Persian holidays retrieval."""
        holidays = PersianCalendarUtils.get_persian_holidays(1403)
        
        self.assertIsInstance(holidays, dict)
        
        # Check for known holidays
        self.assertIn((1, 1), holidays)  # Nowruz
        self.assertIn((1, 13), holidays)  # Sizdeh Bedar
        self.assertIn((11, 22), holidays)  # Revolution Day
        
        # Check holiday names are in Persian
        for holiday_name in holidays.values():
            self.assertIsInstance(holiday_name, str)
            self.assertTrue(len(holiday_name) > 0)
    
    def test_parse_persian_date_string(self):
        """Test parsing Persian date strings."""
        test_cases = [
            ('۱۴۰۳/۰۱/۰۱', (1403, 1, 1)),
            ('1403/01/01', (1403, 1, 1)),
            ('۱۴۰۳/۱/۱', (1403, 1, 1)),
            ('1403/1/1', (1403, 1, 1)),
        ]
        
        for date_string, expected in test_cases:
            result = PersianCalendarUtils.parse_persian_date_string(date_string)
            self.assertEqual(result, expected, 
                           f"Failed to parse '{date_string}'")
        
        # Test invalid strings
        invalid_cases = ['', 'invalid', '1403/13/01', '1403/01/32', '1200/01/01']
        for invalid_string in invalid_cases:
            result = PersianCalendarUtils.parse_persian_date_string(invalid_string)
            self.assertIsNone(result, f"Should not parse '{invalid_string}'")
    
    def test_digit_conversion(self):
        """Test Persian and English digit conversion."""
        # Test Persian to English
        persian_text = '۱۲۳۴۵۶۷۸۹۰'
        english_result = PersianCalendarUtils.to_english_digits(persian_text)
        self.assertEqual(english_result, '1234567890')
        
        # Test English to Persian
        english_text = '1234567890'
        persian_result = PersianCalendarUtils.to_persian_digits(english_text)
        self.assertEqual(persian_result, '۱۲۳۴۵۶۷۸۹۰')
        
        # Test mixed text
        mixed_text = 'سال ۱۴۰۳ ماه ۱'
        english_mixed = PersianCalendarUtils.to_english_digits(mixed_text)
        self.assertEqual(english_mixed, 'سال 1403 ماه 1')
    
    def test_date_range_persian(self):
        """Test Persian date range generation."""
        start_date = (1403, 1, 1)
        end_date = (1403, 1, 5)
        
        date_range = PersianCalendarUtils.get_date_range_persian(start_date, end_date)
        
        self.assertEqual(len(date_range), 5)
        self.assertEqual(date_range[0], (1403, 1, 1))
        self.assertEqual(date_range[-1], (1403, 1, 5))
    
    def test_calculate_age_persian(self):
        """Test age calculation in Persian calendar."""
        birth_date = (1380, 5, 15)  # Born in 1380
        reference_date = (1403, 5, 20)  # Reference in 1403
        
        age = PersianCalendarUtils.calculate_age_persian(birth_date, reference_date)
        self.assertEqual(age, 23)  # Should be 23 years old
        
        # Test before birthday this year
        reference_before = (1403, 5, 10)
        age_before = PersianCalendarUtils.calculate_age_persian(birth_date, reference_before)
        self.assertEqual(age_before, 22)  # Should be 22 years old
    
    def test_get_quarter_persian(self):
        """Test Persian fiscal quarter calculation."""
        test_cases = [
            ((1403, 1, 15), 1),   # Farvardin -> Q1
            ((1403, 4, 15), 2),   # Tir -> Q2
            ((1403, 7, 15), 3),   # Mehr -> Q3
            ((1403, 10, 15), 4),  # Dey -> Q4
        ]
        
        for date_tuple, expected_quarter in test_cases:
            result = PersianCalendarUtils.get_quarter_persian(date_tuple)
            self.assertEqual(result, expected_quarter,
                           f"Date {date_tuple} should be in quarter {expected_quarter}")
    
    def test_validate_persian_date(self):
        """Test Persian date validation."""
        # Valid dates
        valid_dates = [
            (1403, 1, 1),
            (1403, 6, 31),
            (1403, 12, 29),
            (1404, 12, 30),  # Leap year
        ]
        
        for year, month, day in valid_dates:
            result = PersianCalendarUtils.validate_persian_date(year, month, day)
            self.assertTrue(result, f"Date {year}/{month}/{day} should be valid")
        
        # Invalid dates
        invalid_dates = [
            (1403, 13, 1),   # Invalid month
            (1403, 1, 32),   # Invalid day
            (1403, 12, 30),  # Invalid day for non-leap year
            (1200, 1, 1),    # Invalid year
        ]
        
        for year, month, day in invalid_dates:
            result = PersianCalendarUtils.validate_persian_date(year, month, day)
            self.assertFalse(result, f"Date {year}/{month}/{day} should be invalid")


class TestPersianDateRange(TestCase):
    """Test PersianDateRange helper class."""
    
    def test_date_range_iteration(self):
        """Test iterating over Persian date range."""
        start_date = (1403, 1, 1)
        end_date = (1403, 1, 3)
        
        date_range = PersianDateRange(start_date, end_date)
        dates = list(date_range)
        
        expected_dates = [
            (1403, 1, 1),
            (1403, 1, 2),
            (1403, 1, 3),
        ]
        
        self.assertEqual(dates, expected_dates)
    
    def test_date_range_length(self):
        """Test Persian date range length calculation."""
        start_date = (1403, 1, 1)
        end_date = (1403, 1, 5)
        
        date_range = PersianDateRange(start_date, end_date)
        self.assertEqual(len(date_range), 5)
    
    def test_date_range_contains(self):
        """Test checking if date is in range."""
        start_date = (1403, 1, 1)
        end_date = (1403, 1, 5)
        
        date_range = PersianDateRange(start_date, end_date)
        
        self.assertIn((1403, 1, 3), date_range)
        self.assertNotIn((1403, 1, 6), date_range)
        self.assertNotIn((1402, 12, 29), date_range)
    
    def test_date_range_format(self):
        """Test formatting Persian date range."""
        start_date = (1403, 1, 1)
        end_date = (1403, 1, 5)
        
        date_range = PersianDateRange(start_date, end_date)
        formatted = date_range.format_range(format_style='numeric')
        
        self.assertIn('۱۴۰۳/۰۱/۰۱', formatted)
        self.assertIn('۱۴۰۳/۰۱/۰۵', formatted)
        self.assertIn('تا', formatted)


class TestPersianModelFields(TestCase):
    """Test Persian model fields."""
    
    def setUp(self):
        """Set up test model."""
        class TestModel(models.Model):
            persian_date = PersianDateField()
            persian_datetime = PersianDateTimeField()
            fiscal_year = PersianFiscalYearField()
            quarter = PersianQuarterField()
            
            class Meta:
                app_label = 'test'
        
        self.TestModel = TestModel
    
    def test_persian_date_field_storage(self):
        """Test Persian date field stores Gregorian dates."""
        field = PersianDateField()
        
        # Test conversion from Persian string
        persian_string = '1403/01/01'
        result = field.to_python(persian_string)
        
        self.assertIsInstance(result, date)
        # Should be approximately March 20, 2024
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 3)
    
    def test_persian_date_field_validation(self):
        """Test Persian date field validation."""
        field = PersianDateField()
        
        # Valid Persian date
        valid_date = '1403/01/01'
        result = field.to_python(valid_date)
        self.assertIsInstance(result, date)
        
        # Invalid Persian date should raise ValidationError
        with self.assertRaises(ValidationError):
            field.to_python('1403/13/01')  # Invalid month
    
    def test_persian_datetime_field_storage(self):
        """Test Persian datetime field stores Gregorian datetimes."""
        field = PersianDateTimeField()
        
        # Test conversion from Persian string
        persian_string = '1403/01/01 - 12:30'
        result = field.to_python(persian_string)
        
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.hour, 12)
        self.assertEqual(result.minute, 30)
    
    def test_fiscal_year_field_validation(self):
        """Test Persian fiscal year field validation."""
        field = PersianFiscalYearField()
        
        # Valid fiscal year
        field.validate(1403, None)  # Should not raise
        
        # Invalid fiscal year
        with self.assertRaises(ValidationError):
            field.validate(1200, None)  # Too old
        
        with self.assertRaises(ValidationError):
            field.validate(1600, None)  # Too far in future
    
    def test_quarter_field_validation(self):
        """Test Persian quarter field validation."""
        field = PersianQuarterField()
        
        # Valid quarters
        for quarter in [1, 2, 3, 4]:
            field.validate(quarter, None)  # Should not raise
        
        # Invalid quarters
        with self.assertRaises(ValidationError):
            field.validate(0, None)
        
        with self.assertRaises(ValidationError):
            field.validate(5, None)


class TestPersianFormFields(TestCase):
    """Test Persian form fields."""
    
    def test_persian_date_form_field(self):
        """Test Persian date form field."""
        field = PersianDateFormField()
        
        # Test valid Persian date
        result = field.clean('۱۴۰۳/۰۱/۰۱')
        self.assertIsInstance(result, date)
        
        # Test invalid Persian date
        with self.assertRaises(ValidationError):
            field.clean('۱۴۰۳/۱۳/۰۱')
    
    def test_persian_date_form_field_empty_value(self):
        """Test Persian date form field with empty values."""
        field = PersianDateFormField(required=False)
        
        # Empty string should return None
        result = field.clean('')
        self.assertIsNone(result)
        
        # None should return None
        result = field.clean(None)
        self.assertIsNone(result)
    
    def test_persian_date_form_field_digit_conversion(self):
        """Test Persian date form field digit conversion."""
        field = PersianDateFormField()
        
        # Persian digits should be converted
        result = field.clean('۱۴۰۳/۰۱/۰۱')
        self.assertIsInstance(result, date)
        
        # English digits should also work
        result = field.clean('1403/01/01')
        self.assertIsInstance(result, date)


class TestPersianDateWidget(TestCase):
    """Test Persian date widget."""
    
    def test_widget_rendering(self):
        """Test Persian date widget HTML rendering."""
        widget = PersianDateWidget()
        
        # Test rendering with value
        test_date = date(2024, 3, 20)  # Nowruz 1403
        html = widget.render('test_date', test_date)
        
        self.assertIn('persian-date-widget', html)
        self.assertIn('persian-date-input', html)
        self.assertIn('persian-calendar-container', html)
        self.assertIn('۱۴۰۳/۰۱/۰۱', html)  # Persian formatted date
    
    def test_widget_value_formatting(self):
        """Test Persian date widget value formatting."""
        widget = PersianDateWidget()
        
        # Test Gregorian to Persian formatting
        test_date = date(2024, 3, 20)  # Nowruz 1403
        formatted = widget.format_value(test_date)
        
        self.assertEqual(formatted, '۱۴۰۳/۰۱/۰۱')
    
    def test_widget_value_from_datadict(self):
        """Test Persian date widget value extraction."""
        widget = PersianDateWidget()
        
        # Test Persian input
        data = {'test_date': '۱۴۰۳/۰۱/۰۱'}
        result = widget.value_from_datadict(data, {}, 'test_date')
        
        self.assertIsInstance(result, date)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 3)
    
    def test_widget_calendar_generation(self):
        """Test Persian calendar HTML generation."""
        widget = PersianDateWidget(show_calendar=True)
        
        test_date = date(2024, 3, 20)  # Nowruz 1403
        html = widget.render('test_date', test_date)
        
        # Should contain calendar elements
        self.assertIn('persian-calendar', html)
        self.assertIn('calendar-header', html)
        self.assertIn('calendar-days', html)
        self.assertIn('فروردین', html)  # Month name
        self.assertIn('۱۴۰۳', html)  # Year in Persian digits
    
    def test_widget_without_calendar(self):
        """Test Persian date widget without calendar interface."""
        widget = PersianDateWidget(show_calendar=False)
        
        test_date = date(2024, 3, 20)
        html = widget.render('test_date', test_date)
        
        # Should not contain calendar elements
        self.assertNotIn('persian-calendar-container', html)
        self.assertIn('persian-date-input', html)


class TestPersianCalendarIntegration(TestCase):
    """Test integration between different Persian calendar components."""
    
    def test_field_widget_integration(self):
        """Test integration between Persian date field and widget."""
        class TestForm(Form):
            persian_date = PersianDateFormField(widget=PersianDateWidget())
        
        # Test form with Persian date input
        form_data = {'persian_date': '۱۴۰۳/۰۱/۰۱'}
        form = TestForm(data=form_data)
        
        self.assertTrue(form.is_valid())
        
        cleaned_date = form.cleaned_data['persian_date']
        self.assertIsInstance(cleaned_date, date)
        self.assertEqual(cleaned_date.year, 2024)
        self.assertEqual(cleaned_date.month, 3)
    
    def test_model_field_form_field_integration(self):
        """Test integration between model field and form field."""
        model_field = PersianDateField()
        form_field = model_field.formfield()
        
        self.assertIsInstance(form_field, PersianDateFormField)
        self.assertIsInstance(form_field.widget, PersianDateWidget)
    
    def test_calendar_utils_field_integration(self):
        """Test integration between calendar utils and fields."""
        # Test that fields use calendar utils correctly
        field = PersianDateFormField()
        
        # Test with Persian date string
        result = field.clean('۱۴۰۳/۰۱/۰۱')
        
        # Convert back using calendar utils
        persian_date = PersianCalendarUtils.gregorian_to_shamsi(result)
        self.assertEqual(persian_date, (1403, 1, 1))
    
    def test_end_to_end_persian_date_handling(self):
        """Test complete Persian date handling from input to storage."""
        # Simulate user input
        user_input = '۱۴۰۳/۰۱/۱۵'  # 15 Farvardin 1403
        
        # Process through form field
        field = PersianDateFormField()
        cleaned_date = field.clean(user_input)
        
        # Verify it's a proper Gregorian date for storage
        self.assertIsInstance(cleaned_date, date)
        
        # Convert back to Persian for display
        persian_display = PersianCalendarUtils.gregorian_to_shamsi(cleaned_date)
        formatted_display = PersianCalendarUtils.format_persian_date(
            persian_display, format_style='numeric'
        )
        
        # Should match original input
        self.assertEqual(formatted_display, user_input)


if __name__ == '__main__':
    pytest.main([__file__])