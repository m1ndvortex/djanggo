"""
Simple unit tests for Persian widgets without Django app dependencies.
Tests widget functionality in isolation.
"""
import pytest
from datetime import date
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Configure minimal Django settings
import django
from django.conf import settings

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

from zargar.core.widgets import PersianDateWidget, PersianNumberWidget, PersianCurrencyWidget
from zargar.core.calendar_utils import PersianCalendarUtils


class TestPersianDateWidget:
    """Test Persian date widget functionality."""
    
    def test_widget_initialization(self):
        """Test Persian date widget initialization."""
        widget = PersianDateWidget()
        
        # Check default attributes
        assert 'persian-date-input' in widget.attrs['class']
        assert widget.attrs['placeholder'] == '۱۴۰۳/۰۱/۰۱'
        assert widget.attrs['data-persian-date-picker'] == 'true'
        assert widget.attrs['autocomplete'] == 'off'
        assert widget.attrs['readonly'] == 'readonly'
    
    def test_widget_with_custom_attributes(self):
        """Test Persian date widget with custom attributes."""
        custom_attrs = {
            'class': 'custom-class',
            'placeholder': 'تاریخ مورد نظر',
            'data-custom': 'value'
        }
        
        widget = PersianDateWidget(attrs=custom_attrs)
        
        # Should merge with default attributes
        assert 'custom-class' in widget.attrs['class']
        assert 'persian-date-input' in widget.attrs['class']
        assert widget.attrs['placeholder'] == 'تاریخ مورد نظر'
        assert widget.attrs['data-custom'] == 'value'
    
    def test_widget_calendar_options(self):
        """Test Persian date widget calendar options."""
        # Widget with calendar
        widget_with_calendar = PersianDateWidget(show_calendar=True, show_today_button=True)
        assert widget_with_calendar.show_calendar == True
        assert widget_with_calendar.show_today_button == True
        assert widget_with_calendar.attrs['data-show-calendar'] == 'true'
        assert widget_with_calendar.attrs['data-show-today'] == 'true'
        
        # Widget without calendar
        widget_without_calendar = PersianDateWidget(show_calendar=False, show_today_button=False)
        assert widget_without_calendar.show_calendar == False
        assert widget_without_calendar.show_today_button == False
        assert widget_without_calendar.attrs['data-show-calendar'] == 'false'
        assert widget_without_calendar.attrs['data-show-today'] == 'false'
    
    def test_widget_value_formatting(self):
        """Test Persian date widget value formatting."""
        widget = PersianDateWidget()
        
        # Test with Gregorian date (Nowruz 1403)
        test_date = date(2024, 3, 20)
        formatted = widget.format_value(test_date)
        
        # Should be formatted as Persian date
        assert formatted == '۱۴۰۳/۰۱/۰۱'
    
    def test_widget_value_formatting_none(self):
        """Test Persian date widget with None value."""
        widget = PersianDateWidget()
        
        formatted = widget.format_value(None)
        assert formatted == ''
    
    def test_widget_value_from_datadict(self):
        """Test Persian date widget value extraction from form data."""
        widget = PersianDateWidget()
        
        # Test with Persian date input
        data = {'test_date': '۱۴۰۳/۰۱/۰۱'}
        result = widget.value_from_datadict(data, {}, 'test_date')
        
        # Should return Gregorian date object
        assert isinstance(result, date)
        assert result.year == 2024
        assert result.month == 3
        assert result.day == 20
    
    def test_widget_value_from_datadict_empty(self):
        """Test Persian date widget with empty input."""
        widget = PersianDateWidget()
        
        # Test with empty input
        data = {'test_date': ''}
        result = widget.value_from_datadict(data, {}, 'test_date')
        
        assert result is None
    
    def test_widget_value_from_datadict_invalid(self):
        """Test Persian date widget with invalid input."""
        widget = PersianDateWidget()
        
        # Test with invalid date
        data = {'test_date': 'invalid_date'}
        result = widget.value_from_datadict(data, {}, 'test_date')
        
        # Should return the original value for form validation to handle
        assert result == 'invalid_date'
    
    def test_widget_calendar_generation(self):
        """Test Persian calendar HTML generation."""
        widget = PersianDateWidget(show_calendar=True)
        
        # Test calendar generation method
        calendar_html = widget._generate_calendar_html('test_field', 1403, 1, 15)
        
        # Should contain calendar structure
        assert 'persian-calendar' in calendar_html
        assert 'calendar-header' in calendar_html
        assert 'calendar-weekdays' in calendar_html
        assert 'calendar-days' in calendar_html
        assert 'calendar-footer' in calendar_html
        
        # Should contain Persian month and year
        assert 'فروردین' in calendar_html
        assert '۱۴۰۳' in calendar_html
    
    def test_widget_calendar_days_generation(self):
        """Test Persian calendar days generation."""
        widget = PersianDateWidget(show_calendar=True)
        
        # Test days generation for Farvardin 1403
        days_html = widget._generate_calendar_days(1403, 1, 15)
        
        # Should contain day elements
        assert 'calendar-day' in days_html
        assert 'data-day="15"' in days_html
        assert 'data-persian-date="1403/01/15"' in days_html
        
        # Should contain Persian digits
        assert '۱۵' in days_html  # Day 15 in Persian
    
    def test_widget_calendar_footer_generation(self):
        """Test Persian calendar footer generation."""
        widget = PersianDateWidget(show_calendar=True, show_today_button=True)
        
        footer_html = widget._generate_calendar_footer()
        
        # Should contain action buttons
        assert 'today-btn' in footer_html
        assert 'clear-btn' in footer_html
        assert 'confirm-btn' in footer_html
        
        # Should contain Persian button text
        assert 'امروز' in footer_html
        assert 'پاک کردن' in footer_html
        assert 'تأیید' in footer_html
    
    def test_widget_media_files(self):
        """Test Persian date widget media files."""
        widget = PersianDateWidget()
        
        # Should include CSS and JS files
        assert 'css/persian-calendar.css' in widget.media._css['all']
        assert 'js/persian-calendar.js' in widget.media._js


class TestPersianNumberWidget:
    """Test Persian number widget functionality."""
    
    def test_widget_initialization(self):
        """Test Persian number widget initialization."""
        widget = PersianNumberWidget()
        
        # Check default attributes
        assert 'persian-number-input' in widget.attrs['class']
        assert widget.attrs['data-persian-number-input'] == ''
        assert widget.attrs['dir'] == 'rtl'
        assert 'text-align: right;' in widget.attrs['style']
    
    def test_widget_value_formatting(self):
        """Test Persian number widget value formatting."""
        widget = PersianNumberWidget()
        
        # Test with numeric value
        formatted = widget.format_value(1234567)
        
        # Should be formatted with Persian digits and separators
        assert '۱٬۲۳۴٬۵۶۷' in formatted
    
    def test_widget_value_from_datadict(self):
        """Test Persian number widget value extraction."""
        widget = PersianNumberWidget()
        
        # Test with Persian formatted number
        data = {'test_number': '۱٬۲۳۴٬۵۶۷'}
        result = widget.value_from_datadict(data, {}, 'test_number')
        
        # Should return numeric value
        assert result == 1234567.0
    
    def test_digit_conversion(self):
        """Test digit conversion methods."""
        widget = PersianNumberWidget()
        
        # Test Persian to English
        persian_text = '۱۲۳۴۵۶۷۸۹۰'
        english_result = widget.convert_to_english_digits(persian_text)
        assert english_result == '1234567890'
        
        # Test English to Persian
        english_text = '1234567890'
        persian_result = widget.convert_to_persian_digits(english_text)
        assert persian_result == '۱۲۳۴۵۶۷۸۹۰'


class TestPersianCurrencyWidget:
    """Test Persian currency widget functionality."""
    
    def test_widget_initialization(self):
        """Test Persian currency widget initialization."""
        widget = PersianCurrencyWidget()
        
        # Should inherit from PersianNumberWidget
        assert 'persian-number-input' in widget.attrs['class']
        assert widget.attrs['placeholder'] == '۱۰۰٬۰۰۰ تومان'
    
    def test_widget_value_formatting(self):
        """Test Persian currency widget value formatting."""
        widget = PersianCurrencyWidget()
        
        # Test with numeric value
        formatted = widget.format_value(100000)
        
        # Should be formatted with Persian digits and currency text
        assert '۱۰۰٬۰۰۰ تومان' in formatted


class TestWidgetIntegration:
    """Test integration between widgets and calendar utilities."""
    
    def test_date_widget_calendar_utils_integration(self):
        """Test integration between date widget and calendar utils."""
        widget = PersianDateWidget()
        
        # Test that widget uses calendar utils correctly
        test_date = date(2024, 3, 20)  # Nowruz 1403
        formatted = widget.format_value(test_date)
        
        # Should match calendar utils formatting
        persian_date = PersianCalendarUtils.gregorian_to_shamsi(test_date)
        expected = PersianCalendarUtils.format_persian_date(persian_date, format_style='numeric')
        
        assert formatted == expected
    
    def test_widget_date_parsing_integration(self):
        """Test widget date parsing with calendar utils."""
        widget = PersianDateWidget()
        
        # Test parsing Persian date string
        data = {'test_date': '۱۴۰۳/۰۱/۱۵'}
        result = widget.value_from_datadict(data, {}, 'test_date')
        
        # Should correctly parse and convert
        assert isinstance(result, date)
        
        # Convert back to verify
        persian_result = PersianCalendarUtils.gregorian_to_shamsi(result)
        assert persian_result == (1403, 1, 15)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])