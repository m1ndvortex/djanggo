"""
Tests for Persian calendar frontend components.
Tests the Persian date picker, date range selector, and fiscal year components.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing Django modules
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.template import Template, Context
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import date, datetime
import json

from zargar.core.calendar_utils import PersianCalendarUtils
from zargar.core.model_fields import PersianDateField
from zargar.core.widgets import PersianDateWidget

User = get_user_model()


class PersianCalendarFrontendTestCase(TestCase):
    """Test case for Persian calendar frontend components."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test user (without tenant for now)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Persian calendar utilities
        self.calendar_utils = PersianCalendarUtils()
        
        # Test dates
        self.test_gregorian_date = date(2024, 10, 15)
        self.test_persian_date = self.calendar_utils.gregorian_to_shamsi(self.test_gregorian_date)
    
    def test_persian_date_picker_widget_rendering(self):
        """Test Persian date picker widget renders correctly."""
        widget = PersianDateWidget()
        
        # Test basic rendering
        html = widget.render('test_date', None)
        
        self.assertIn('persian-date-widget', html)
        self.assertIn('persian-date-input', html)
        self.assertIn('persian-calendar-container', html)
        self.assertIn('data-field-name="test_date"', html)
        
        # Test with value
        html_with_value = widget.render('test_date', self.test_gregorian_date)
        
        # Should contain Persian formatted date
        persian_formatted = self.calendar_utils.format_persian_date(
            self.test_persian_date, format_style='numeric'
        )
        self.assertIn(persian_formatted, html_with_value)
    
    def test_persian_date_picker_template_tag(self):
        """Test Persian date picker template tag."""
        template = Template("""
            {% load persian_tags %}
            {% persian_date_picker 'birth_date' field_value='1403/07/24' %}
        """)
        
        rendered = template.render(Context({}))
        
        self.assertIn('persian-date-picker-container', rendered)
        self.assertIn('birth_date', rendered)
        self.assertIn('۱۴۰۳/۰۷/۲۴', rendered)
        self.assertIn('persian-calendar-widget', rendered)
    
    def test_persian_calendar_javascript_structure(self):
        """Test Persian calendar JavaScript structure."""
        # Read the JavaScript file
        with open('static/js/persian-calendar.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check for essential classes and methods
        self.assertIn('class PersianCalendar', js_content)
        self.assertIn('handleDaySelection', js_content)
        self.assertIn('selectFiscalYear', js_content)
        self.assertIn('selectQuarter', js_content)
        self.assertIn('handleRangeDaySelection', js_content)
        self.assertIn('generateFiscalYearSelector', js_content)
        self.assertIn('generateQuarterControls', js_content)
        
        # Check for Persian month names
        self.assertIn('فروردین', js_content)
        self.assertIn('اسفند', js_content)
        
        # Check for Persian weekday names
        self.assertIn('شنبه', js_content)
        self.assertIn('جمعه', js_content)
    
    def test_persian_calendar_css_structure(self):
        """Test Persian calendar CSS structure."""
        # Read the CSS file
        with open('static/css/persian-calendar.css', 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        # Check for essential classes
        self.assertIn('.persian-date-widget', css_content)
        self.assertIn('.persian-calendar', css_content)
        self.assertIn('.calendar-day', css_content)
        self.assertIn('.fiscal-year-selector', css_content)
        self.assertIn('.quarter-controls', css_content)
        self.assertIn('.range-mode', css_content)
        
        # Check for theme support
        self.assertIn('[data-theme="dark"]', css_content)
        self.assertIn('[data-theme="cybersecurity"]', css_content)
        
        # Check for range selection styles
        self.assertIn('.in-range', css_content)
        self.assertIn('.range-start', css_content)
        self.assertIn('.range-end', css_content)
    
    def test_persian_date_range_widget_structure(self):
        """Test Persian date range widget structure."""
        # Read the JavaScript file
        with open('static/js/persian-date-range.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check for essential classes and methods
        self.assertIn('class PersianDateRange', js_content)
        self.assertIn('selectQuickRange', js_content)
        self.assertIn('setDateRange', js_content)
        self.assertIn('setupQuickSelectors', js_content)
        
        # Check for fiscal year support
        self.assertIn('current-fiscal-year', js_content)
        self.assertIn('prev-fiscal-year', js_content)
        
        # Check for quarter support
        self.assertIn('فصل اول', js_content)
        self.assertIn('فصل چهارم', js_content)
        
        # Read the CSS file
        with open('static/css/persian-date-range.css', 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        # Check for essential classes
        self.assertIn('.persian-date-range-widget', css_content)
        self.assertIn('.quick-selector-btn', css_content)
        self.assertIn('.range-display-content', css_content)
    
    def test_persian_date_range_template_component(self):
        """Test Persian date range template component."""
        # Render the template component
        rendered = render_to_string('core/components/persian_date_range.html', {
            'field_name': 'date_range',
            'start_value': '۱۴۰۳/۰۱/۰۱',
            'end_value': '۱۴۰۳/۱۲/۲۹'
        })
        
        self.assertIn('persian-date-range-widget', rendered)
        self.assertIn('persian-date-range-start', rendered)
        self.assertIn('persian-date-range-end', rendered)
        self.assertIn('persian-date-range-quick', rendered)
        self.assertIn('تاریخ شروع:', rendered)
        self.assertIn('تاریخ پایان:', rendered)
        self.assertIn('۱۴۰۳/۰۱/۰۱', rendered)
        self.assertIn('۱۴۰۳/۱۲/۲۹', rendered)
    
    def test_persian_calendar_modes(self):
        """Test different Persian calendar modes."""
        # Test single mode
        widget_single = PersianDateWidget()
        html_single = widget_single.render('single_date', None)
        self.assertIn('persian-date-widget', html_single)
        
        # Test with show_calendar=False
        widget_no_calendar = PersianDateWidget(show_calendar=False)
        html_no_calendar = widget_no_calendar.render('no_calendar_date', None)
        self.assertNotIn('persian-calendar-container', html_no_calendar)
        
        # Test with show_today_button=False
        widget_no_today = PersianDateWidget(show_today_button=False)
        html_no_today = widget_no_today.render('no_today_date', None)
        self.assertNotIn('today-btn', html_no_today)
    
    def test_persian_calendar_fiscal_year_functionality(self):
        """Test fiscal year functionality in Persian calendar."""
        # Read JavaScript content to verify fiscal year methods
        with open('static/js/persian-calendar.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check fiscal year methods
        self.assertIn('selectFiscalYear', js_content)
        self.assertIn('generateFiscalYearSelector', js_content)
        self.assertIn('generateFiscalYearControls', js_content)
        
        # Check fiscal year quick actions
        self.assertIn('current-fiscal-year', js_content)
        self.assertIn('prev-fiscal-year', js_content)
        
        # Check Persian text for fiscal year
        self.assertIn('سال مالی', js_content)
        self.assertIn('سال جاری', js_content)
        self.assertIn('سال گذشته', js_content)
    
    def test_persian_calendar_quarter_functionality(self):
        """Test quarter functionality in Persian calendar."""
        # Read JavaScript content to verify quarter methods
        with open('static/js/persian-calendar.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check quarter methods
        self.assertIn('selectQuarter', js_content)
        self.assertIn('generateQuarterControls', js_content)
        
        # Check quarter definitions
        self.assertIn('persianQuarters', js_content)
        self.assertIn('فصل اول', js_content)
        self.assertIn('فصل دوم', js_content)
        self.assertIn('فصل سوم', js_content)
        self.assertIn('فصل چهارم', js_content)
        
        # Check quarter descriptions
        self.assertIn('فروردین - خرداد', js_content)
        self.assertIn('تیر - شهریور', js_content)
        self.assertIn('مهر - آذر', js_content)
        self.assertIn('دی - اسفند', js_content)
    
    def test_persian_calendar_range_selection(self):
        """Test range selection functionality."""
        # Read JavaScript content to verify range methods
        with open('static/js/persian-calendar.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check range selection methods
        self.assertIn('handleRangeDaySelection', js_content)
        self.assertIn('setRangeInputValue', js_content)
        self.assertIn('isDateInRange', js_content)
        self.assertIn('compareDates', js_content)
        
        # Check range CSS classes
        with open('static/css/persian-calendar.css', 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        self.assertIn('.in-range', css_content)
        self.assertIn('.range-start', css_content)
        self.assertIn('.range-end', css_content)
        self.assertIn('.range-mode', css_content)
    
    def test_persian_calendar_theme_support(self):
        """Test theme support in Persian calendar."""
        # Read CSS content to verify theme support
        with open('static/css/persian-calendar.css', 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        # Check dark theme support
        self.assertIn('[data-theme="dark"]', css_content)
        self.assertIn('[data-theme="dark"] .persian-calendar-container', css_content)
        self.assertIn('[data-theme="dark"] .calendar-day', css_content)
        
        # Check cybersecurity theme support
        self.assertIn('[data-theme="cybersecurity"]', css_content)
        self.assertIn('[data-theme="cybersecurity"] .persian-calendar-container', css_content)
        self.assertIn('linear-gradient', css_content)
        self.assertIn('#00d4ff', css_content)  # Cybersecurity primary color
        self.assertIn('#00ff88', css_content)  # Cybersecurity secondary color
        self.assertIn('#ff6b35', css_content)  # Cybersecurity tertiary color
        
        # Check glassmorphism effects
        self.assertIn('backdrop-filter: blur', css_content)
        self.assertIn('box-shadow:', css_content)
    
    def test_persian_date_range_quick_selectors(self):
        """Test quick selectors in date range widget."""
        # Read JavaScript content
        with open('static/js/persian-date-range.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check quick selector options
        quick_selectors = [
            'today', 'yesterday', 'this-week', 'last-week',
            'this-month', 'last-month', 'current-fiscal-year',
            'prev-fiscal-year', 'q1', 'q2', 'q3', 'q4',
            'prev-q1', 'prev-q2', 'prev-q3', 'prev-q4'
        ]
        
        for selector in quick_selectors:
            self.assertIn(f"'{selector}'", js_content)
        
        # Check Persian text for quick selectors
        persian_texts = [
            'امروز', 'دیروز', 'این هفته', 'هفته گذشته',
            'این ماه', 'ماه گذشته', 'سال جاری', 'سال گذشته',
            'فصل اول', 'فصل دوم', 'فصل سوم', 'فصل چهارم'
        ]
        
        for text in persian_texts:
            self.assertIn(text, js_content)
    
    def test_persian_calendar_accessibility(self):
        """Test accessibility features of Persian calendar."""
        widget = PersianDateWidget()
        html = widget.render('accessible_date', None)
        
        # Check for keyboard navigation support
        with open('static/js/persian-calendar.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        self.assertIn('keydown', js_content)
        self.assertIn('ArrowLeft', js_content)
        self.assertIn('ArrowRight', js_content)
        self.assertIn('Escape', js_content)
        self.assertIn('Enter', js_content)
        
        # Check for ARIA attributes and semantic HTML
        self.assertIn('button', html)
        self.assertIn('data-action', html)
    
    def test_persian_calendar_responsive_design(self):
        """Test responsive design of Persian calendar."""
        # Read CSS content
        with open('static/css/persian-calendar.css', 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        # Check for responsive breakpoints
        self.assertIn('@media (max-width: 768px)', css_content)
        self.assertIn('@media (max-width: 480px)', css_content)
        
        # Check for mobile-specific styles
        self.assertIn('position: fixed', css_content)
        self.assertIn('transform: translate(-50%, -50%)', css_content)
        
        # Check date range responsive design
        with open('static/css/persian-date-range.css', 'r', encoding='utf-8') as f:
            range_css_content = f.read()
        
        self.assertIn('@media (max-width: 768px)', range_css_content)
        self.assertIn('flex-direction: column', range_css_content)
    
    def test_persian_calendar_validation(self):
        """Test date validation in Persian calendar."""
        # Read JavaScript content
        with open('static/js/persian-calendar.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check validation methods
        self.assertIn('isValidPersianDate', js_content)
        self.assertIn('validateAndFormatInput', js_content)
        self.assertIn('getDaysInPersianMonth', js_content)
        self.assertIn('isPersianLeapYear', js_content)
        
        # Check validation ranges
        self.assertIn('1300', js_content)  # Minimum Persian year
        self.assertIn('1500', js_content)  # Maximum Persian year
    
    def test_persian_calendar_digit_conversion(self):
        """Test Persian digit conversion functionality."""
        # Read JavaScript content
        with open('static/js/persian-calendar.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check digit conversion methods
        self.assertIn('toPersianDigits', js_content)
        self.assertIn('toEnglishDigits', js_content)
        
        # Check digit mappings
        self.assertIn('۰۱۲۳۴۵۶۷۸۹', js_content)
        self.assertIn('0123456789', js_content)
        
        # Test template tag
        template = Template("""
            {% load persian_tags %}
            {{ "1403"|persian_number }}
        """)
        
        rendered = template.render(Context({}))
        self.assertEqual(rendered.strip(), '۱۴۰۳')
    
    def test_persian_calendar_integration_with_forms(self):
        """Test Persian calendar integration with Django forms."""
        from django import forms
        from zargar.core.fields import PersianDateField as PersianDateFormField
        
        class TestForm(forms.Form):
            birth_date = PersianDateFormField(
                widget=PersianDateWidget(),
                required=True
            )
        
        form = TestForm()
        form_html = str(form['birth_date'])
        
        self.assertIn('persian-date-widget', form_html)
        self.assertIn('persian-date-input', form_html)
        
        # Test form validation with Persian date
        form_data = {'birth_date': '۱۴۰۳/۰۷/۲۴'}
        form = TestForm(data=form_data)
        
        # Form should be valid (assuming proper form field implementation)
        # This would require the actual form field implementation
    
    def test_persian_calendar_performance(self):
        """Test performance considerations of Persian calendar."""
        # Read JavaScript content
        with open('static/js/persian-calendar.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check for performance optimizations
        self.assertIn('MutationObserver', js_content)  # For dynamic initialization
        self.assertIn('data-initialized', js_content)  # Prevent double initialization
        
        # Check for efficient event handling
        self.assertIn('addEventListener', js_content)
        self.assertIn('removeEventListener', js_content)
        
        # Check for CSS transitions instead of JavaScript animations
        with open('static/css/persian-calendar.css', 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        self.assertIn('transition:', css_content)
        self.assertIn('transform:', css_content)


class PersianCalendarIntegrationTestCase(TestCase):
    """Integration tests for Persian calendar components."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='integrationuser',
            email='integration@example.com',
            password='testpass123'
        )
    
    def test_persian_calendar_in_admin_interface(self):
        """Test Persian calendar in admin interface."""
        # This would test the calendar in actual admin forms
        # Requires proper admin setup and model with PersianDateField
        pass
    
    def test_persian_calendar_ajax_integration(self):
        """Test Persian calendar with AJAX requests."""
        # This would test calendar behavior with dynamic content loading
        pass
    
    def test_persian_calendar_with_real_data(self):
        """Test Persian calendar with real business data."""
        # This would test calendar with actual jewelry business scenarios
        pass


if __name__ == '__main__':
    pytest.main([__file__])