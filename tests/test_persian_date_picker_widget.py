"""
Unit tests for Persian date picker widget functionality.
Tests widget rendering and JavaScript integration.
"""
import pytest
from datetime import date
from django.test import TestCase, override_settings
from django.forms import Form
from django.conf import settings
import os

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

from zargar.core.widgets import PersianDateWidget
from zargar.core.fields import PersianDateField as PersianDateFormField


class TestPersianDateWidget(TestCase):
    """Test Persian date widget functionality."""
    
    def test_widget_initialization(self):
        """Test Persian date widget initialization."""
        widget = PersianDateWidget()
        
        # Check default attributes
        self.assertIn('persian-date-input', widget.attrs['class'])
        self.assertEqual(widget.attrs['placeholder'], '۱۴۰۳/۰۱/۰۱')
        self.assertEqual(widget.attrs['data-persian-date-picker'], 'true')
        self.assertEqual(widget.attrs['autocomplete'], 'off')
        self.assertEqual(widget.attrs['readonly'], 'readonly')
    
    def test_widget_with_custom_attributes(self):
        """Test Persian date widget with custom attributes."""
        custom_attrs = {
            'class': 'custom-class',
            'placeholder': 'تاریخ مورد نظر',
            'data-custom': 'value'
        }
        
        widget = PersianDateWidget(attrs=custom_attrs)
        
        # Should merge with default attributes
        self.assertIn('custom-class', widget.attrs['class'])
        self.assertIn('persian-date-input', widget.attrs['class'])
        self.assertEqual(widget.attrs['placeholder'], 'تاریخ مورد نظر')
        self.assertEqual(widget.attrs['data-custom'], 'value')
    
    def test_widget_calendar_options(self):
        """Test Persian date widget calendar options."""
        # Widget with calendar
        widget_with_calendar = PersianDateWidget(show_calendar=True, show_today_button=True)
        self.assertTrue(widget_with_calendar.show_calendar)
        self.assertTrue(widget_with_calendar.show_today_button)
        self.assertEqual(widget_with_calendar.attrs['data-show-calendar'], 'true')
        self.assertEqual(widget_with_calendar.attrs['data-show-today'], 'true')
        
        # Widget without calendar
        widget_without_calendar = PersianDateWidget(show_calendar=False, show_today_button=False)
        self.assertFalse(widget_without_calendar.show_calendar)
        self.assertFalse(widget_without_calendar.show_today_button)
        self.assertEqual(widget_without_calendar.attrs['data-show-calendar'], 'false')
        self.assertEqual(widget_without_calendar.attrs['data-show-today'], 'false')
    
    def test_widget_value_formatting(self):
        """Test Persian date widget value formatting."""
        widget = PersianDateWidget()
        
        # Test with Gregorian date (Nowruz 1403)
        test_date = date(2024, 3, 20)
        formatted = widget.format_value(test_date)
        
        # Should be formatted as Persian date
        self.assertEqual(formatted, '۱۴۰۳/۰۱/۰۱')
    
    def test_widget_value_formatting_none(self):
        """Test Persian date widget with None value."""
        widget = PersianDateWidget()
        
        formatted = widget.format_value(None)
        self.assertEqual(formatted, '')
    
    def test_widget_value_from_datadict(self):
        """Test Persian date widget value extraction from form data."""
        widget = PersianDateWidget()
        
        # Test with Persian date input
        data = {'test_date': '۱۴۰۳/۰۱/۰۱'}
        result = widget.value_from_datadict(data, {}, 'test_date')
        
        # Should return Gregorian date object
        self.assertIsInstance(result, date)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 3)
        self.assertEqual(result.day, 20)
    
    def test_widget_value_from_datadict_empty(self):
        """Test Persian date widget with empty input."""
        widget = PersianDateWidget()
        
        # Test with empty input
        data = {'test_date': ''}
        result = widget.value_from_datadict(data, {}, 'test_date')
        
        self.assertIsNone(result)
    
    def test_widget_value_from_datadict_invalid(self):
        """Test Persian date widget with invalid input."""
        widget = PersianDateWidget()
        
        # Test with invalid date
        data = {'test_date': 'invalid_date'}
        result = widget.value_from_datadict(data, {}, 'test_date')
        
        # Should return the original value for form validation to handle
        self.assertEqual(result, 'invalid_date')
    
    def test_widget_rendering_basic(self):
        """Test basic Persian date widget rendering."""
        widget = PersianDateWidget(show_calendar=False)
        
        html = widget.render('test_date', None)
        
        # Should contain input field
        self.assertIn('persian-date-input', html)
        self.assertIn('name="test_date"', html)
        self.assertIn('placeholder="۱۴۰۳/۰۱/۰۱"', html)
    
    def test_widget_rendering_with_value(self):
        """Test Persian date widget rendering with value."""
        widget = PersianDateWidget(show_calendar=False)
        test_date = date(2024, 3, 20)  # Nowruz 1403
        
        html = widget.render('test_date', test_date)
        
        # Should contain the formatted Persian date
        self.assertIn('value="۱۴۰۳/۰۱/۰۱"', html)
    
    def test_widget_rendering_with_calendar(self):
        """Test Persian date widget rendering with calendar."""
        widget = PersianDateWidget(show_calendar=True)
        test_date = date(2024, 3, 20)  # Nowruz 1403
        
        html = widget.render('test_date', test_date)
        
        # Should contain calendar elements
        self.assertIn('persian-date-widget', html)
        self.assertIn('persian-calendar-container', html)
        self.assertIn('persian-calendar', html)
        self.assertIn('calendar-header', html)
        self.assertIn('calendar-days', html)
        self.assertIn('فروردین', html)  # Month name
        self.assertIn('۱۴۰۳', html)  # Year in Persian digits
    
    def test_widget_calendar_generation(self):
        """Test Persian calendar HTML generation."""
        widget = PersianDateWidget(show_calendar=True)
        
        # Test calendar generation method
        calendar_html = widget._generate_calendar_html('test_field', 1403, 1, 15)
        
        # Should contain calendar structure
        self.assertIn('persian-calendar', calendar_html)
        self.assertIn('calendar-header', calendar_html)
        self.assertIn('calendar-weekdays', calendar_html)
        self.assertIn('calendar-days', calendar_html)
        self.assertIn('calendar-footer', calendar_html)
        
        # Should contain Persian month and year
        self.assertIn('فروردین', calendar_html)
        self.assertIn('۱۴۰۳', calendar_html)
    
    def test_widget_calendar_days_generation(self):
        """Test Persian calendar days generation."""
        widget = PersianDateWidget(show_calendar=True)
        
        # Test days generation for Farvardin 1403
        days_html = widget._generate_calendar_days(1403, 1, 15)
        
        # Should contain day elements
        self.assertIn('calendar-day', days_html)
        self.assertIn('data-day="15"', days_html)
        self.assertIn('data-persian-date="1403/01/15"', days_html)
        
        # Should contain Persian digits
        self.assertIn('۱۵', days_html)  # Day 15 in Persian
    
    def test_widget_calendar_footer_generation(self):
        """Test Persian calendar footer generation."""
        widget = PersianDateWidget(show_calendar=True, show_today_button=True)
        
        footer_html = widget._generate_calendar_footer()
        
        # Should contain action buttons
        self.assertIn('today-btn', footer_html)
        self.assertIn('clear-btn', footer_html)
        self.assertIn('confirm-btn', footer_html)
        
        # Should contain Persian button text
        self.assertIn('امروز', footer_html)
        self.assertIn('پاک کردن', footer_html)
        self.assertIn('تأیید', footer_html)
    
    def test_widget_media_files(self):
        """Test Persian date widget media files."""
        widget = PersianDateWidget()
        
        # Should include CSS and JS files
        self.assertIn('css/persian-calendar.css', widget.media._css['all'])
        self.assertIn('js/persian-calendar.js', widget.media._js)


class TestPersianDateFormIntegration(TestCase):
    """Test integration between Persian date field and widget."""
    
    def test_form_field_widget_integration(self):
        """Test Persian date form field with widget."""
        class TestForm(Form):
            persian_date = PersianDateFormField(widget=PersianDateWidget())
        
        # Test form rendering
        form = TestForm()
        html = str(form['persian_date'])
        
        # Should contain widget elements
        self.assertIn('persian-date-input', html)
        self.assertIn('data-persian-date-picker', html)
    
    def test_form_validation_with_widget(self):
        """Test form validation with Persian date widget."""
        class TestForm(Form):
            persian_date = PersianDateFormField(widget=PersianDateWidget())
        
        # Test with valid Persian date
        form_data = {'persian_date': '۱۴۰۳/۰۱/۰۱'}
        form = TestForm(data=form_data)
        
        self.assertTrue(form.is_valid())
        
        cleaned_date = form.cleaned_data['persian_date']
        self.assertIsInstance(cleaned_date, date)
        self.assertEqual(cleaned_date.year, 2024)
        self.assertEqual(cleaned_date.month, 3)
        self.assertEqual(cleaned_date.day, 20)
    
    def test_form_validation_invalid_date(self):
        """Test form validation with invalid Persian date."""
        class TestForm(Form):
            persian_date = PersianDateFormField(widget=PersianDateWidget())
        
        # Test with invalid Persian date
        form_data = {'persian_date': '۱۴۰۳/۱۳/۰۱'}  # Invalid month
        form = TestForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('persian_date', form.errors)
    
    def test_form_rendering_with_initial_value(self):
        """Test form rendering with initial Persian date value."""
        class TestForm(Form):
            persian_date = PersianDateFormField(
                widget=PersianDateWidget(),
                initial=date(2024, 3, 20)  # Nowruz 1403
            )
        
        form = TestForm()
        html = str(form['persian_date'])
        
        # Should contain the formatted Persian date
        self.assertIn('value="۱۴۰۳/۰۱/۰۱"', html)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])