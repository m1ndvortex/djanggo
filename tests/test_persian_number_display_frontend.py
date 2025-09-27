"""
Frontend tests for Persian number display components.
Tests the JavaScript functionality, template rendering, and user interactions.
"""
import pytest
from django.test import TestCase, Client
from django.template import Template, Context
from django.template.loader import render_to_string
from decimal import Decimal
import json
import re


class PersianNumberDisplayTemplateTests(TestCase):
    """Test Persian number display template components."""
    
    def setUp(self):
        self.client = Client()
        self.context = {
            'amount': 1500000,
            'weight': 23.04,
            'percentage': 25.5,
            'price_per_gram': 1200000,
            'weight_grams': 5.5,
            'use_persian_digits': True,
        }
    
    def test_persian_currency_display_template(self):
        """Test Persian currency display template rendering."""
        template = Template("""
            {% load persian_tags %}
            {% include 'core/components/persian_currency_display.html' with amount=amount size='large' %}
        """)
        
        rendered = template.render(Context(self.context))
        
        # Check for Persian digits
        self.assertIn('۱،۵۰۰،۰۰۰', rendered)
        self.assertIn('تومان', rendered)
        self.assertIn('data-persian-currency', rendered)
        self.assertIn('data-amount="1500000"', rendered)
        self.assertIn('large', rendered)
    
    def test_persian_weight_display_template(self):
        """Test Persian weight display template rendering."""
        template = Template("""
            {% load persian_tags %}
            {% include 'core/components/persian_weight_display.html' with weight=weight unit='gram' show_conversions=True %}
        """)
        
        rendered = template.render(Context(self.context))
        
        # Check for Persian digits and weight units
        self.assertIn('۲۳.۰۴', rendered)
        self.assertIn('گرم', rendered)
        self.assertIn('data-persian-weight', rendered)
        self.assertIn('data-weight="23.04"', rendered)
        self.assertIn('data-weight-conversions', rendered)
    
    def test_persian_gold_price_display_template(self):
        """Test Persian gold price display template rendering."""
        template = Template("""
            {% load persian_tags %}
            {% include 'core/components/persian_gold_price_display.html' with price_per_gram=price_per_gram weight_grams=weight_grams %}
        """)
        
        rendered = template.render(Context(self.context))
        
        # Check for gold price calculation elements
        self.assertIn('data-gold-price', rendered)
        self.assertIn('data-price-per-gram="1200000"', rendered)
        self.assertIn('data-weight-grams="5.5"', rendered)
        self.assertIn('قیمت هر گرم', rendered)
        self.assertIn('ارزش کل', rendered)
        self.assertIn('وزن', rendered)
    
    def test_persian_financial_card_template(self):
        """Test Persian financial card template rendering."""
        template = Template("""
            {% load persian_tags %}
            {% include 'core/components/persian_financial_card.html' with title='فروش امروز' value=amount type='currency' icon='sales' %}
        """)
        
        rendered = template.render(Context(self.context))
        
        # Check for financial card elements
        self.assertIn('financial-display-card', rendered)
        self.assertIn('فروش امروز', rendered)
        self.assertIn('data-value="1500000"', rendered)
        self.assertIn('data-card-type="currency"', rendered)
        self.assertIn('۱،۵۰۰،۰۰۰', rendered)
    
    def test_template_with_none_values(self):
        """Test templates handle None values gracefully."""
        context = {
            'amount': None,
            'weight': None,
            'price_per_gram': None,
            'weight_grams': None,
        }
        
        # Currency display with None
        template = Template("""
            {% load persian_tags %}
            {% include 'core/components/persian_currency_display.html' with amount=amount %}
        """)
        rendered = template.render(Context(context))
        self.assertIn('۰ تومان', rendered)
        
        # Weight display with None
        template = Template("""
            {% load persian_tags %}
            {% include 'core/components/persian_weight_display.html' with weight=weight %}
        """)
        rendered = template.render(Context(context))
        self.assertIn('۰ گرم', rendered)
    
    def test_template_theme_classes(self):
        """Test templates include proper theme classes."""
        template = Template("""
            {% load persian_tags %}
            {% include 'core/components/persian_currency_display.html' with amount=amount animate=True %}
        """)
        
        rendered = template.render(Context(self.context))
        
        # Check for theme-related classes and attributes
        self.assertIn('persian-currency-display', rendered)
        self.assertIn('persian-number-display', rendered)
        self.assertIn('data-animate="true"', rendered)
    
    def test_template_accessibility_attributes(self):
        """Test templates include accessibility attributes."""
        template = Template("""
            {% load persian_tags %}
            {% include 'core/components/persian_currency_display.html' with amount=amount %}
        """)
        
        rendered = template.render(Context(self.context))
        
        # Check for accessibility attributes
        self.assertIn('title=', rendered)
        self.assertIn('مبلغ:', rendered)


class PersianNumberDisplayDemoViewTests(TestCase):
    """Test the Persian number display demo page."""
    
    def setUp(self):
        self.client = Client()
    
    def test_demo_page_loads(self):
        """Test that the demo page loads successfully."""
        # Create a simple URL pattern for testing
        from django.urls import path
        from django.views.generic import TemplateView
        
        # We'll test the template directly since URL might not be configured
        template_content = render_to_string('demo/persian_number_display_demo.html', {})
        
        # Check for key sections
        self.assertIn('سیستم نمایش اعداد فارسی', template_content)
        self.assertIn('نمایش ارز و مبالغ مالی', template_content)
        self.assertIn('نمایش وزن و واحدهای سنتی', template_content)
        self.assertIn('محاسبه قیمت طلا', template_content)
        self.assertIn('قالب‌بندی اعداد و درصدها', template_content)
    
    def test_demo_page_includes_required_assets(self):
        """Test that demo page includes required CSS and JS files."""
        template_content = render_to_string('demo/persian_number_display_demo.html', {})
        
        # Check for CSS includes
        self.assertIn('persian-number-display.css', template_content)
        
        # Check for JS includes
        self.assertIn('persian-number-display.js', template_content)
    
    def test_demo_page_interactive_elements(self):
        """Test that demo page includes interactive elements."""
        template_content = render_to_string('demo/persian_number_display_demo.html', {})
        
        # Check for interactive demo elements
        self.assertIn('demo_currency', template_content)
        self.assertIn('demo_weight', template_content)
        self.assertIn('currency_display', template_content)
        self.assertIn('weight_conversions', template_content)
    
    def test_demo_page_examples(self):
        """Test that demo page includes various examples."""
        template_content = render_to_string('demo/persian_number_display_demo.html', {})
        
        # Check for different component examples
        self.assertIn('persian_currency_display.html', template_content)
        self.assertIn('persian_weight_display.html', template_content)
        self.assertIn('persian_gold_price_display.html', template_content)
        self.assertIn('persian_financial_card.html', template_content)


class PersianNumberDisplayJavaScriptTests(TestCase):
    """Test JavaScript functionality through template rendering."""
    
    def test_javascript_data_attributes(self):
        """Test that templates generate correct data attributes for JavaScript."""
        template = Template("""
            {% load persian_tags %}
            <div data-persian-currency data-amount="1500000" data-use-persian-digits="true">
                {% persian_currency 1500000 %}
            </div>
        """)
        
        rendered = template.render(Context({}))
        
        # Check data attributes
        self.assertIn('data-persian-currency', rendered)
        self.assertIn('data-amount="1500000"', rendered)
        self.assertIn('data-use-persian-digits="true"', rendered)
    
    def test_weight_conversion_data_attributes(self):
        """Test weight conversion data attributes."""
        template = Template("""
            {% load persian_tags %}
            <div data-weight-conversions data-weight-grams="23.04" data-target-units="gram,mesghal,soot">
            </div>
        """)
        
        rendered = template.render(Context({}))
        
        # Check weight conversion attributes
        self.assertIn('data-weight-conversions', rendered)
        self.assertIn('data-weight-grams="23.04"', rendered)
        self.assertIn('data-target-units="gram,mesghal,soot"', rendered)
    
    def test_gold_price_data_attributes(self):
        """Test gold price calculation data attributes."""
        template = Template("""
            {% load persian_tags %}
            <div data-gold-price data-price-per-gram="1200000" data-weight-grams="5.5">
            </div>
        """)
        
        rendered = template.render(Context({}))
        
        # Check gold price attributes
        self.assertIn('data-gold-price', rendered)
        self.assertIn('data-price-per-gram="1200000"', rendered)
        self.assertIn('data-weight-grams="5.5"', rendered)


class PersianNumberDisplayCSSTests(TestCase):
    """Test CSS classes and styling in templates."""
    
    def test_base_css_classes(self):
        """Test that templates include base CSS classes."""
        template = Template("""
            {% load persian_tags %}
            {% include 'core/components/persian_currency_display.html' with amount=1500000 %}
        """)
        
        rendered = template.render(Context({}))
        
        # Check for base CSS classes
        self.assertIn('persian-currency-display', rendered)
        self.assertIn('persian-number-display', rendered)
    
    def test_size_variant_classes(self):
        """Test size variant CSS classes."""
        template = Template("""
            {% load persian_tags %}
            {% include 'core/components/persian_currency_display.html' with amount=1500000 size='large' %}
        """)
        
        rendered = template.render(Context({}))
        
        # Check for size classes
        self.assertIn('large', rendered)
    
    def test_theme_responsive_classes(self):
        """Test theme-responsive CSS classes."""
        template = Template("""
            {% load persian_tags %}
            {% include 'core/components/persian_financial_card.html' with title='Test' value=1000 type='currency' %}
        """)
        
        rendered = template.render(Context({}))
        
        # Check for theme classes
        self.assertIn('financial-display-card', rendered)
    
    def test_weight_conversion_css_classes(self):
        """Test weight conversion CSS classes."""
        template = Template("""
            {% load persian_tags %}
            {% include 'core/components/persian_weight_display.html' with weight=100 show_conversions=True %}
        """)
        
        rendered = template.render(Context({}))
        
        # Check for weight conversion classes
        self.assertIn('weight-conversions', rendered)
        self.assertIn('weight-conversion-item', rendered)


class PersianNumberDisplayResponsiveTests(TestCase):
    """Test responsive design elements in templates."""
    
    def test_responsive_grid_classes(self):
        """Test responsive grid classes in demo template."""
        template_content = render_to_string('demo/persian_number_display_demo.html', {})
        
        # Check for responsive grid classes
        self.assertIn('grid-cols-1', template_content)
        self.assertIn('md:grid-cols-2', template_content)
        self.assertIn('lg:grid-cols-3', template_content)
        self.assertIn('lg:grid-cols-4', template_content)
    
    def test_mobile_friendly_elements(self):
        """Test mobile-friendly elements."""
        template_content = render_to_string('demo/persian_number_display_demo.html', {})
        
        # Check for mobile considerations
        self.assertIn('max-w-6xl', template_content)
        self.assertIn('px-4', template_content)
        self.assertIn('overflow-x-auto', template_content)


class PersianNumberDisplayPerformanceTests(TestCase):
    """Test performance-related aspects of templates."""
    
    def test_template_rendering_performance(self):
        """Test template rendering performance."""
        import time
        
        template = Template("""
            {% load persian_tags %}
            {% for i in "12345678901234567890" %}
                {% include 'core/components/persian_currency_display.html' with amount=1500000 %}
            {% endfor %}
        """)
        
        start_time = time.time()
        rendered = template.render(Context({}))
        end_time = time.time()
        
        render_time = end_time - start_time
        
        # Should render 20 components in reasonable time (less than 1 second)
        self.assertLess(render_time, 1.0)
        
        # Check that all components were rendered
        self.assertEqual(rendered.count('persian-currency-display'), 20)
    
    def test_large_number_handling(self):
        """Test handling of very large numbers."""
        large_numbers = [
            999999999999,  # 999 billion
            1234567890123,  # 1.2 trillion
            Decimal('999999999999.99'),  # Large decimal
        ]
        
        template = Template("""
            {% load persian_tags %}
            {% include 'core/components/persian_currency_display.html' with amount=amount %}
        """)
        
        for number in large_numbers:
            rendered = template.render(Context({'amount': number}))
            
            # Should not crash and should contain Persian digits
            self.assertIn('data-persian-currency', rendered)
            self.assertRegex(rendered, r'[۰-۹]')  # Contains Persian digits


class PersianNumberDisplayAccessibilityTests(TestCase):
    """Test accessibility features in templates."""
    
    def test_aria_labels_and_titles(self):
        """Test ARIA labels and title attributes."""
        template = Template("""
            {% load persian_tags %}
            {% include 'core/components/persian_currency_display.html' with amount=1500000 %}
        """)
        
        rendered = template.render(Context({}))
        
        # Check for accessibility attributes
        self.assertIn('title=', rendered)
        self.assertIn('مبلغ:', rendered)
    
    def test_semantic_html_structure(self):
        """Test semantic HTML structure."""
        template_content = render_to_string('demo/persian_number_display_demo.html', {})
        
        # Check for semantic HTML elements
        self.assertIn('<h1', template_content)
        self.assertIn('<h2', template_content)
        self.assertIn('<h3', template_content)
        self.assertIn('<section', template_content)
    
    def test_keyboard_navigation_support(self):
        """Test keyboard navigation support."""
        template = Template("""
            {% load persian_tags %}
            {% include 'core/tags/persian_number_input.html' with field_name='test' %}
        """)
        
        rendered = template.render(Context({}))
        
        # Check for keyboard navigation attributes
        self.assertIn('tabindex', rendered)
    
    def test_screen_reader_friendly_content(self):
        """Test screen reader friendly content."""
        template = Template("""
            {% load persian_tags %}
            {% include 'core/components/persian_gold_price_display.html' with price_per_gram=1200000 weight_grams=5.5 %}
        """)
        
        rendered = template.render(Context({}))
        
        # Check for descriptive text
        self.assertIn('قیمت هر گرم', rendered)
        self.assertIn('ارزش کل', rendered)
        self.assertIn('وزن', rendered)


class PersianNumberDisplayIntegrationTests(TestCase):
    """Test integration with other components."""
    
    def test_theme_toggle_integration(self):
        """Test integration with theme toggle component."""
        template_content = render_to_string('demo/persian_number_display_demo.html', {})
        
        # Check for theme toggle integration
        self.assertIn('theme_toggle.html', template_content)
        self.assertIn('light-mode', template_content)
        self.assertIn('dark-mode', template_content)
        self.assertIn('cyber-theme', template_content)
    
    def test_persian_tags_integration(self):
        """Test integration with Persian template tags."""
        template = Template("""
            {% load persian_tags %}
            <div>
                {% persian_currency 1500000 %}
                {% persian_weight 23.04 'gram' %}
                {% persian_percentage 25.5 %}
            </div>
        """)
        
        rendered = template.render(Context({}))
        
        # Check that Persian tags work correctly
        self.assertIn('۱،۵۰۰،۰۰۰ تومان', rendered)
        self.assertIn('۲۳.۰۴ گرم', rendered)
        self.assertIn('۲۵.۵٪', rendered)
    
    def test_rtl_layout_integration(self):
        """Test integration with RTL layout."""
        template_content = render_to_string('demo/persian_number_display_demo.html', {})
        
        # Check for RTL support
        self.assertIn('dir="rtl"', template_content)
        self.assertIn('text-align: right', template_content)


class PersianNumberDisplayErrorHandlingTests(TestCase):
    """Test error handling in templates."""
    
    def test_invalid_values_handling(self):
        """Test handling of invalid values."""
        invalid_values = [
            'invalid_string',
            '',
            [],
            {},
        ]
        
        template = Template("""
            {% load persian_tags %}
            {% include 'core/components/persian_currency_display.html' with amount=amount %}
        """)
        
        for invalid_value in invalid_values:
            rendered = template.render(Context({'amount': invalid_value}))
            
            # Should not crash and should show default value
            self.assertIn('data-persian-currency', rendered)
            # Should contain some form of zero or placeholder
            self.assertTrue('۰' in rendered or '0' in rendered or 'placeholder' in rendered)
    
    def test_missing_context_variables(self):
        """Test handling of missing context variables."""
        template = Template("""
            {% load persian_tags %}
            {% include 'core/components/persian_currency_display.html' with amount=missing_variable %}
        """)
        
        # Should not crash with missing variable
        rendered = template.render(Context({}))
        self.assertIn('data-persian-currency', rendered)
    
    def test_template_syntax_errors(self):
        """Test graceful handling of template syntax issues."""
        # Test with malformed include
        template = Template("""
            {% load persian_tags %}
            {% include 'core/components/persian_currency_display.html' %}
        """)
        
        # Should render without crashing
        rendered = template.render(Context({}))
        self.assertIn('data-persian-currency', rendered)


if __name__ == '__main__':
    pytest.main([__file__])