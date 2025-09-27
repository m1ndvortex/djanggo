"""
Simple tests for RTL layout and theme switching functionality
Tests for task 4.2: Build RTL-first base templates with dual theme support
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.template import Template, Context
from django.http import HttpRequest
from django.contrib.sessions.middleware import SessionMiddleware
from django.conf import settings
import os

from zargar.core.context_processors import theme_context, persian_context

User = get_user_model()


class RTLTemplateBasicTests(TestCase):
    """Test basic RTL template functionality"""
    
    def test_rtl_html_structure(self):
        """Test that RTL HTML structure is correct"""
        template = Template("""
            <!DOCTYPE html>
            <html dir="rtl" lang="fa">
            <head>
                <meta charset="UTF-8">
                <title>Test</title>
            </head>
            <body class="font-vazir">
                <div class="persian-text">متن فارسی</div>
            </body>
            </html>
        """)
        
        rendered = template.render(Context({}))
        
        # Check RTL attributes
        self.assertIn('dir="rtl"', rendered)
        self.assertIn('lang="fa"', rendered)
        self.assertIn('font-vazir', rendered)
        self.assertIn('متن فارسی', rendered)
    
    def test_persian_number_template_tag(self):
        """Test Persian number formatting in templates"""
        template = Template("""
            <span class="persian-numbers">123456</span>
        """)
        
        rendered = template.render(Context({}))
        
        # Should contain the number (conversion happens in JavaScript)
        self.assertIn('123456', rendered)
        self.assertIn('persian-numbers', rendered)
    
    def test_rtl_css_classes(self):
        """Test RTL-specific CSS classes"""
        template = Template("""
            <div class="rtl-content text-right">
                <p class="persian-text">متن فارسی</p>
            </div>
        """)
        
        rendered = template.render(Context({}))
        
        self.assertIn('rtl-content', rendered)
        self.assertIn('text-right', rendered)
        self.assertIn('persian-text', rendered)


class ThemeContextTests(TestCase):
    """Test theme context processor"""
    
    def test_theme_context_light_mode(self):
        """Test theme context for light mode"""
        request = HttpRequest()
        request.session = {}
        request.theme = 'light'
        
        SessionMiddleware(lambda r: None).process_request(request)
        
        context = theme_context(request)
        
        self.assertEqual(context['current_theme'], 'light')
        self.assertTrue(context['is_light_mode'])
        self.assertFalse(context['is_dark_mode'])
        self.assertIn('light', context['available_themes'])
        self.assertIn('dark', context['available_themes'])
    
    def test_theme_context_dark_mode(self):
        """Test theme context for dark mode"""
        request = HttpRequest()
        request.session = {}
        request.theme = 'dark'
        
        SessionMiddleware(lambda r: None).process_request(request)
        
        context = theme_context(request)
        
        self.assertEqual(context['current_theme'], 'dark')
        self.assertFalse(context['is_light_mode'])
        self.assertTrue(context['is_dark_mode'])
        self.assertTrue(context['cybersecurity_theme'])
        self.assertTrue(context['glassmorphism_enabled'])
        self.assertTrue(context['neon_effects_enabled'])


class PersianContextTests(TestCase):
    """Test Persian context processor"""
    
    def test_persian_context_basic(self):
        """Test basic Persian context"""
        request = HttpRequest()
        request.session = {}
        
        context = persian_context(request)
        
        self.assertEqual(context['LANGUAGE_CODE'], 'fa')
        self.assertTrue(context['LANGUAGE_BIDI'])
        self.assertEqual(context['language_direction'], 'rtl')
        self.assertTrue(context['is_rtl'])
        self.assertTrue(context['persian_locale'])
    
    def test_persian_months_and_days(self):
        """Test Persian month and day names"""
        request = HttpRequest()
        request.session = {}
        
        context = persian_context(request)
        
        # Check that we have a Persian month name (current month)
        self.assertIsInstance(context['persian_month_name'], str)
        self.assertTrue(len(context['persian_month_name']) > 0)
        
        # Check Persian day names
        self.assertIn(context['persian_day_name'], [
            'شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 
            'چهارشنبه', 'پنج‌شنبه', 'جمعه'
        ])
    
    def test_persian_business_terms(self):
        """Test Persian business terminology"""
        request = HttpRequest()
        request.session = {}
        
        context = persian_context(request)
        
        business_terms = context['business_terms']
        
        self.assertEqual(business_terms['weight_unit'], 'گرم')
        self.assertEqual(business_terms['karat_unit'], 'عیار')
        self.assertEqual(business_terms['manufacturing_cost'], 'اجرت')
        self.assertEqual(business_terms['gold_price'], 'قیمت طلا')
        self.assertEqual(business_terms['customer'], 'مشتری')
    
    def test_persian_currency_formatting(self):
        """Test Persian currency formatting"""
        request = HttpRequest()
        request.session = {}
        
        context = persian_context(request)
        
        self.assertEqual(context['currency_symbol'], 'تومان')
        self.assertEqual(context['thousand_separator'], '٬')
        self.assertEqual(context['decimal_separator'], '٫')


class StaticFilesTests(TestCase):
    """Test that static files exist"""
    
    def test_rtl_css_file_exists(self):
        """Test that RTL CSS file exists"""
        css_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'base-rtl.css')
        self.assertTrue(os.path.exists(css_path), f"RTL CSS file not found at {css_path}")
    
    def test_rtl_js_file_exists(self):
        """Test that RTL JavaScript file exists"""
        js_path = os.path.join(settings.BASE_DIR, 'static', 'js', 'rtl-components.js')
        self.assertTrue(os.path.exists(js_path), f"RTL JS file not found at {js_path}")
    
    def test_theme_toggle_js_exists(self):
        """Test that theme toggle JavaScript exists"""
        js_path = os.path.join(settings.BASE_DIR, 'static', 'js', 'theme-toggle.js')
        self.assertTrue(os.path.exists(js_path), f"Theme toggle JS file not found at {js_path}")
    
    def test_persian_utils_js_exists(self):
        """Test that Persian utilities JavaScript exists"""
        js_path = os.path.join(settings.BASE_DIR, 'static', 'js', 'persian-utils.js')
        self.assertTrue(os.path.exists(js_path), f"Persian utils JS file not found at {js_path}")


class ComponentTemplateTests(TestCase):
    """Test component templates"""
    
    def test_theme_toggle_component_structure(self):
        """Test theme toggle component has correct structure"""
        template_path = os.path.join(settings.BASE_DIR, 'templates', 'core', 'components', 'theme_toggle.html')
        self.assertTrue(os.path.exists(template_path), f"Theme toggle template not found at {template_path}")
        
        # Read template content
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for essential elements
        self.assertIn('data-theme-toggle', content)
        self.assertIn('تغییر تم', content)
        self.assertIn('cyber-neon-primary', content)
        self.assertIn('bg-white/80', content)
    
    def test_loading_spinner_component_structure(self):
        """Test loading spinner component has correct structure"""
        template_path = os.path.join(settings.BASE_DIR, 'templates', 'core', 'components', 'loading_spinner.html')
        self.assertTrue(os.path.exists(template_path), f"Loading spinner template not found at {template_path}")
        
        # Read template content
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for essential elements
        self.assertIn('در حال بارگذاری...', content)
        self.assertIn('animate-spin', content)
        self.assertIn('cyber-neon-primary', content)
    
    def test_navigation_component_structure(self):
        """Test navigation component has correct structure"""
        template_path = os.path.join(settings.BASE_DIR, 'templates', 'core', 'components', 'navigation.html')
        self.assertTrue(os.path.exists(template_path), f"Navigation template not found at {template_path}")
        
        # Read template content
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for essential elements
        self.assertIn('زرگر', content)
        self.assertIn('داشبورد', content)
        self.assertIn('موجودی', content)
        self.assertIn('rtl:space-x-reverse', content)
    
    def test_footer_component_structure(self):
        """Test footer component has correct structure"""
        template_path = os.path.join(settings.BASE_DIR, 'templates', 'core', 'components', 'footer.html')
        self.assertTrue(os.path.exists(template_path), f"Footer template not found at {template_path}")
        
        # Read template content
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for essential elements
        self.assertIn('زرگر', content)
        self.assertIn('سیستم مدیریت طلا و جواهرات', content)
        self.assertIn('تمامی حقوق محفوظ است', content)


class BaseRTLTemplateTests(TestCase):
    """Test base RTL template"""
    
    def test_base_rtl_template_exists(self):
        """Test that base RTL template exists"""
        template_path = os.path.join(settings.BASE_DIR, 'templates', 'base_rtl.html')
        self.assertTrue(os.path.exists(template_path), f"Base RTL template not found at {template_path}")
        
        # Read template content
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for essential RTL elements
        self.assertIn('dir="rtl"', content)
        self.assertIn('lang="fa"', content)
        self.assertIn('font-vazir', content)
        self.assertIn('Vazirmatn', content)
        
        # Check for theme system
        self.assertIn('themeData()', content)
        self.assertIn('cyber-bg-primary', content)
        self.assertIn('light-bg-primary', content)
        
        # Check for Persian fonts
        self.assertIn('Yekan Bakh', content)
        
        # Check for framework integration
        self.assertIn('tailwindcss.com', content)
        self.assertIn('alpinejs', content)
        self.assertIn('htmx', content)
        self.assertIn('framer-motion', content)


class CybersecurityThemeTests(TestCase):
    """Test cybersecurity theme specific features"""
    
    def test_cyber_color_palette(self):
        """Test cybersecurity color palette in CSS"""
        css_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'base-rtl.css')
        
        with open(css_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for cybersecurity colors
        self.assertIn('#00D4FF', content)  # Neon primary
        self.assertIn('#00FF88', content)  # Neon secondary
        self.assertIn('#FF6B35', content)  # Neon tertiary
        self.assertIn('#0B0E1A', content)  # Background primary
    
    def test_glassmorphism_effects(self):
        """Test glassmorphism effects in CSS"""
        css_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'base-rtl.css')
        
        with open(css_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for glassmorphism effects
        self.assertIn('backdrop-filter', content)
        self.assertIn('blur(', content)
        self.assertIn('cyber-glass-card', content)
    
    def test_neon_animations(self):
        """Test neon animations in CSS"""
        css_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'base-rtl.css')
        
        with open(css_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for neon animations
        self.assertIn('neon-pulse', content)
        self.assertIn('cyber-glow', content)
        self.assertIn('@keyframes', content)


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["__main__"])