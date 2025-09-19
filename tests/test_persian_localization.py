"""
Tests for Persian localization functionality in ZARGAR jewelry SaaS platform.
"""
import pytest
from django.test import TestCase, RequestFactory, override_settings
from django.utils import translation
from django.template import Context, Template
from django.contrib.auth import get_user_model
from decimal import Decimal
import jdatetime
from datetime import date, datetime

from zargar.core.templatetags.persian_tags import (
    persian_number, persian_currency, persian_weight, 
    to_mithqal, to_soot, persian_date, persian_datetime,
    karat_display, percentage_persian
)
from zargar.core.fields import (
    PersianDateField, PersianDecimalField, PersianCurrencyField,
    PersianWeightField, KaratField, PersianPhoneField
)
from zargar.core.widgets import (
    PersianDateWidget, PersianNumberWidget, PersianCurrencyWidget,
    PersianWeightWidget, KaratSelectWidget
)
from zargar.core.context_processors import (
    persian_context, theme_context, persian_number_formatter
)
# Import middleware classes in test methods to avoid app loading issues

# User model will be imported in test methods when needed


class PersianTemplateTagsTest(TestCase):
    """Test Persian template tags functionality."""
    
    def test_persian_number_conversion(self):
        """Test conversion of English digits to Persian digits."""
        self.assertEqual(persian_number("123"), "۱۲۳")
        self.assertEqual(persian_number("0"), "۰")
        self.assertEqual(persian_number("9876543210"), "۹۸۷۶۵۴۳۲۱۰")
        self.assertEqual(persian_number(""), "")
        self.assertEqual(persian_number(None), "")
    
    def test_persian_currency_formatting(self):
        """Test Persian currency formatting with Toman."""
        self.assertEqual(persian_currency(1000), "۱٬۰۰۰ تومان")
        self.assertEqual(persian_currency(1234567), "۱٬۲۳۴٬۵۶۷ تومان")
        self.assertEqual(persian_currency(0), "۰ تومان")
        self.assertEqual(persian_currency(""), "")
        self.assertEqual(persian_currency(None), "")
    
    def test_persian_weight_formatting(self):
        """Test Persian weight formatting with grams."""
        self.assertEqual(persian_weight(10.500), "۱۰٫۵۰۰ گرم")
        self.assertEqual(persian_weight(1.234), "۱٫۲۳۴ گرم")
        self.assertEqual(persian_weight(0), "۰٫۰۰۰ گرم")
        self.assertEqual(persian_weight(""), "")
        self.assertEqual(persian_weight(None), "")
    
    def test_mithqal_conversion(self):
        """Test conversion from grams to Mithqal."""
        # 1 Mithqal = 4.608 grams
        result = to_mithqal(4.608)
        self.assertIn("۱٫۰۰۰ مثقال", result)
        
        result = to_mithqal(9.216)  # 2 Mithqal
        self.assertIn("۲٫۰۰۰ مثقال", result)
    
    def test_soot_conversion(self):
        """Test conversion from grams to Soot."""
        # 1 Soot = 3.456 grams
        result = to_soot(3.456)
        self.assertIn("۱٫۰۰۰ سوت", result)
        
        result = to_soot(6.912)  # 2 Soot
        self.assertIn("۲٫۰۰۰ سوت", result)
    
    def test_persian_date_formatting(self):
        """Test Persian date formatting."""
        gregorian_date = date(2024, 9, 19)
        result = persian_date(gregorian_date)
        
        # Should contain Persian digits
        self.assertTrue(any(char in result for char in "۰۱۲۳۴۵۶۷۸۹"))
        self.assertIn("/", result)  # Should have date separators
    
    def test_karat_display(self):
        """Test karat display formatting."""
        self.assertEqual(karat_display(18), "عیار ۱۸")
        self.assertEqual(karat_display(21), "عیار ۲۱")
        self.assertEqual(karat_display(24), "عیار ۲۴")
        self.assertEqual(karat_display(""), "")
        self.assertEqual(karat_display(None), "")
    
    def test_percentage_persian(self):
        """Test Persian percentage formatting."""
        self.assertEqual(percentage_persian(25.5), "۲۵٫۵%")
        self.assertEqual(percentage_persian(100), "۱۰۰٫۰%")
        self.assertEqual(percentage_persian(0), "۰٫۰%")


class PersianFieldsTest(TestCase):
    """Test Persian form fields functionality."""
    
    def test_persian_date_field(self):
        """Test Persian date field validation and conversion."""
        field = PersianDateField()
        
        # Test valid Persian date
        result = field.to_python("۱۴۰۳/۰۱/۰۱")
        self.assertIsInstance(result, date)
        
        # Test English digits
        result = field.to_python("1403/01/01")
        self.assertIsInstance(result, date)
        
        # Test empty value
        result = field.to_python("")
        self.assertIsNone(result)
        
        # Test invalid date
        with self.assertRaises(Exception):
            field.to_python("invalid")
    
    def test_persian_decimal_field(self):
        """Test Persian decimal field conversion."""
        field = PersianDecimalField()
        
        # Test Persian digits
        result = field.to_python("۱۲۳٫۴۵")
        self.assertEqual(result, Decimal("123.45"))
        
        # Test with thousand separators
        result = field.to_python("۱٬۲۳۴٫۵۶")
        self.assertEqual(result, Decimal("1234.56"))
        
        # Test English digits
        result = field.to_python("123.45")
        self.assertEqual(result, Decimal("123.45"))
        
        # Test empty value
        result = field.to_python("")
        self.assertIsNone(result)
    
    def test_persian_currency_field(self):
        """Test Persian currency field validation."""
        field = PersianCurrencyField()
        
        # Test currency with text
        result = field.to_python("۱۰۰ تومان")
        self.assertEqual(result, Decimal("100"))
        
        # Test negative value validation
        with self.assertRaises(Exception):
            field.clean(-100)
    
    def test_persian_weight_field(self):
        """Test Persian weight field validation."""
        field = PersianWeightField()
        
        # Test weight with unit
        result = field.to_python("۱۰٫۵ گرم")
        self.assertEqual(result, Decimal("10.5"))
        
        # Test negative weight validation
        with self.assertRaises(Exception):
            field.clean(-10)
        
        # Test excessive weight validation
        with self.assertRaises(Exception):
            field.clean(20000)  # Over 10kg limit
    
    def test_karat_field(self):
        """Test karat field validation."""
        field = KaratField()
        
        # Test valid karat values
        field.clean(18)
        field.clean(21)
        field.clean(22)
        field.clean(24)
        
        # Test invalid karat value
        with self.assertRaises(Exception):
            field.clean(15)  # Invalid karat
    
    def test_persian_phone_field(self):
        """Test Persian phone number field validation."""
        field = PersianPhoneField()
        
        # Test valid mobile number
        result = field.to_python("۰۹۱۲۳۴۵۶۷۸۹")
        self.assertEqual(result, "09123456789")
        
        # Test valid landline
        result = field.to_python("۰۲۱۱۲۳۴۵۶۷۸")
        self.assertEqual(result, "02112345678")
        
        # Test invalid phone number
        with self.assertRaises(Exception):
            field.clean("123")


class PersianWidgetsTest(TestCase):
    """Test Persian form widgets functionality."""
    
    def test_persian_date_widget(self):
        """Test Persian date widget formatting."""
        widget = PersianDateWidget()
        
        # Test date formatting
        test_date = date(2024, 9, 19)
        formatted = widget.format_value(test_date)
        
        # Should contain Persian digits
        self.assertTrue(any(char in formatted for char in "۰۱۲۳۴۵۶۷۸۹"))
    
    def test_persian_number_widget(self):
        """Test Persian number widget formatting."""
        widget = PersianNumberWidget()
        
        # Test number formatting
        formatted = widget.format_value(1234.56)
        self.assertIn("۱٬۲۳۴", formatted)
    
    def test_persian_currency_widget(self):
        """Test Persian currency widget formatting."""
        widget = PersianCurrencyWidget()
        
        # Test currency formatting
        formatted = widget.format_value(1000)
        self.assertIn("تومان", formatted)
        self.assertIn("۱٬۰۰۰", formatted)
    
    def test_karat_select_widget(self):
        """Test karat select widget choices."""
        widget = KaratSelectWidget()
        
        # Check that common karat values are available
        choices = dict(widget.choices)
        self.assertIn(18, choices)
        self.assertIn(21, choices)
        self.assertIn(22, choices)
        self.assertIn(24, choices)


class PersianContextProcessorsTest(TestCase):
    """Test Persian context processors."""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_persian_context(self):
        """Test Persian context processor."""
        request = self.factory.get('/')
        context = persian_context(request)
        
        # Check Persian locale settings
        self.assertEqual(context['LANGUAGE_CODE'], 'fa')
        self.assertTrue(context['LANGUAGE_BIDI'])
        self.assertTrue(context['is_rtl'])
        self.assertTrue(context['persian_locale'])
        
        # Check Persian date context
        self.assertIn('persian_date', context)
        self.assertIn('persian_year', context)
        self.assertIn('persian_month', context)
        
        # Check Persian number formatting
        self.assertTrue(context['use_persian_numbers'])
        self.assertEqual(context['currency_symbol'], 'تومان')
        self.assertEqual(context['thousand_separator'], '٬')
        self.assertEqual(context['decimal_separator'], '٫')
    
    def test_theme_context(self):
        """Test theme context processor."""
        request = self.factory.get('/')
        request.theme = 'light'
        request.theme_classes = 'bg-gray-50 text-gray-900'
        request.theme_type = 'modern'
        
        context = theme_context(request)
        
        self.assertEqual(context['current_theme'], 'light')
        self.assertTrue(context['is_light_mode'])
        self.assertFalse(context['is_dark_mode'])
        self.assertTrue(context['modern_theme'])
    
    def test_persian_number_formatter(self):
        """Test Persian number formatter functions."""
        request = self.factory.get('/')
        context = persian_number_formatter(request)
        
        # Test formatter functions
        format_persian_number = context['format_persian_number']
        format_persian_currency = context['format_persian_currency']
        format_persian_weight = context['format_persian_weight']
        
        self.assertEqual(format_persian_number(123), "۱۲۳")
        self.assertIn("تومان", format_persian_currency(1000))
        self.assertIn("گرم", format_persian_weight(10.5))


class PersianMiddlewareTest(TestCase):
    """Test Persian localization middleware."""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_persian_localization_middleware(self):
        """Test Persian localization middleware sets correct context."""
        from zargar.core.middleware import PersianLocalizationMiddleware
        
        request = self.factory.get('/')
        middleware = PersianLocalizationMiddleware(lambda r: None)
        
        middleware.process_request(request)
        
        # Check Persian settings
        self.assertTrue(request.is_rtl)
        self.assertEqual(request.language_direction, 'rtl')
        self.assertTrue(request.persian_locale)
        self.assertTrue(request.use_persian_numbers)
        self.assertEqual(request.currency_symbol, 'تومان')
    
    def test_theme_middleware(self):
        """Test theme middleware functionality."""
        from zargar.core.middleware import ThemeMiddleware
        
        middleware = ThemeMiddleware(lambda r: None)
        request = self.factory.get('/')
        request.user = None
        request.session = {}
        request.COOKIES = {}
        
        middleware.process_request(request)
        
        # Should set default theme
        self.assertIn(request.theme, ['light', 'dark'])
        self.assertIsNotNone(request.theme_classes)
        self.assertIsNotNone(request.theme_type)


@override_settings(USE_I18N=True, LANGUAGE_CODE='fa')
class PersianTemplateRenderingTest(TestCase):
    """Test Persian template rendering with RTL layout."""
    
    def test_persian_template_tags_in_template(self):
        """Test Persian template tags work in actual templates."""
        template = Template("""
            {% load persian_tags %}
            <div dir="{{ persian_direction }}">
                <span>{{ amount|persian_currency }}</span>
                <span>{{ weight|persian_weight }}</span>
                <span>{{ karat|karat_display }}</span>
            </div>
        """)
        
        context = Context({
            'amount': 1000,
            'weight': 10.5,
            'karat': 18
        })
        
        rendered = template.render(context)
        
        # Check RTL direction
        self.assertIn('dir="rtl"', rendered)
        
        # Check Persian formatting
        self.assertIn("تومان", rendered)
        self.assertIn("گرم", rendered)
        self.assertIn("عیار", rendered)
        
        # Check Persian digits
        self.assertTrue(any(char in rendered for char in "۰۱۲۳۴۵۶۷۸۹"))
    
    def test_theme_toggle_template_tag(self):
        """Test theme toggle template tag rendering."""
        template = Template("""
            {% load persian_tags %}
            {% theme_toggle_button %}
        """)
        
        context = Context({})
        rendered = template.render(context)
        
        # Should contain theme toggle elements
        self.assertIn("theme-toggle", rendered)
    
    def test_persian_date_picker_template_tag(self):
        """Test Persian date picker template tag rendering."""
        template = Template("""
            {% load persian_tags %}
            {% persian_date_picker "birth_date" %}
        """)
        
        context = Context({})
        rendered = template.render(context)
        
        # Should contain date picker elements
        self.assertIn("persian-date-picker", rendered)
        self.assertIn("persian-calendar", rendered)


class PersianNumberFormattingTest(TestCase):
    """Test Persian number formatting utilities."""
    
    def test_large_number_formatting(self):
        """Test formatting of large numbers with Persian separators."""
        self.assertEqual(persian_number("1234567890"), "۱۲۳۴۵۶۷۸۹۰")
        
        # Test currency formatting with large amounts
        result = persian_currency(1234567890)
        self.assertIn("۱٬۲۳۴٬۵۶۷٬۸۹۰", result)
        self.assertIn("تومان", result)
    
    def test_decimal_formatting(self):
        """Test decimal number formatting with Persian separators."""
        result = persian_weight(1234.567)
        self.assertIn("۱٬۲۳۴٫۵۶۷", result)
        self.assertIn("گرم", result)
    
    def test_traditional_weight_conversions(self):
        """Test traditional Persian weight unit conversions."""
        # Test multiple Mithqal conversion
        result = to_mithqal(23.04)  # 5 Mithqal
        self.assertIn("۵٫۰۰۰", result)
        self.assertIn("مثقال", result)
        
        # Test multiple Soot conversion
        result = to_soot(17.28)  # 5 Soot
        self.assertIn("۵٫۰۰۰", result)
        self.assertIn("سوت", result)


class PersianCalendarTest(TestCase):
    """Test Persian calendar functionality."""
    
    def test_persian_date_conversion(self):
        """Test conversion between Gregorian and Persian dates."""
        # Test known date conversion
        gregorian_date = date(2024, 9, 19)
        persian_formatted = persian_date(gregorian_date)
        
        # Should be formatted with Persian digits
        self.assertTrue(any(char in persian_formatted for char in "۰۱۲۳۴۵۶۷۸۹"))
        
        # Should have proper date format
        self.assertRegex(persian_formatted, r'۱۴\d{2}/\d{2}/\d{2}')
    
    def test_persian_datetime_conversion(self):
        """Test Persian datetime formatting."""
        test_datetime = datetime(2024, 9, 19, 14, 30)
        result = persian_datetime(test_datetime)
        
        # Should contain both date and time
        self.assertIn("/", result)  # Date separators
        self.assertIn(":", result)  # Time separator
        self.assertIn("-", result)  # Date-time separator
        
        # Should use Persian digits
        self.assertTrue(any(char in result for char in "۰۱۲۳۴۵۶۷۸۹"))


@pytest.mark.django_db
class PersianLocalizationIntegrationTest(TestCase):
    """Integration tests for Persian localization."""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_full_persian_request_cycle(self):
        """Test complete request cycle with Persian localization."""
        # Create request with Persian locale
        request = self.factory.get('/')
        request.session = {}
        request.COOKIES = {}
        request.user = None
        
        # Apply Persian middleware
        from zargar.core.middleware import PersianLocalizationMiddleware, ThemeMiddleware
        
        persian_middleware = PersianLocalizationMiddleware(lambda r: None)
        theme_middleware = ThemeMiddleware(lambda r: None)
        
        persian_middleware.process_request(request)
        theme_middleware.process_request(request)
        
        # Check all Persian settings are applied
        self.assertTrue(request.is_rtl)
        self.assertEqual(request.language_direction, 'rtl')
        self.assertTrue(request.persian_locale)
        self.assertTrue(request.use_persian_numbers)
        self.assertEqual(request.currency_symbol, 'تومان')
        
        # Check theme settings
        self.assertIsNotNone(request.theme)
        self.assertIsNotNone(request.theme_classes)
    
    def test_persian_form_validation_integration(self):
        """Test Persian form fields work together properly."""
        # Test multiple Persian fields in combination
        date_field = PersianDateField()
        currency_field = PersianCurrencyField()
        weight_field = PersianWeightField()
        phone_field = PersianPhoneField()
        
        # Test valid data
        date_result = date_field.to_python("۱۴۰۳/۰۶/۲۸")
        currency_result = currency_field.to_python("۱۰۰٬۰۰۰ تومان")
        weight_result = weight_field.to_python("۲۵٫۵۰۰ گرم")
        phone_result = phone_field.to_python("۰۹۱۲۳۴۵۶۷۸۹")
        
        # All should convert properly
        self.assertIsInstance(date_result, date)
        self.assertEqual(currency_result, Decimal("100000"))
        self.assertEqual(weight_result, Decimal("25.500"))
        self.assertEqual(phone_result, "09123456789")
    
    @override_settings(LANGUAGE_CODE='fa', USE_I18N=True)
    def test_persian_translation_loading(self):
        """Test Persian translations are loaded correctly."""
        with translation.override('fa'):
            # Test basic translations
            self.assertEqual(translation.gettext('Login'), 'ورود')
            self.assertEqual(translation.gettext('Dashboard'), 'داشبورد')
            self.assertEqual(translation.gettext('Save'), 'ذخیره')
            
            # Test business terms
            self.assertEqual(translation.gettext('Jewelry'), 'جواهرات')
            self.assertEqual(translation.gettext('Gold'), 'طلا')
            self.assertEqual(translation.gettext('Customer'), 'مشتری')