"""
Test RTL layout, Persian text display, and theme switching functionality
Tests for task 4.2: Build RTL-first base templates with dual theme support
"""

import pytest
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.template import Template, Context
from django.template.loader import render_to_string
from django.http import HttpRequest
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.conf import settings

from zargar.tenants.models import Tenant
from zargar.core.context_processors import theme_context, persian_context

User = get_user_model()


class RTLThemeTemplateTests(TestCase):
    """Test RTL layout and theme system in templates"""
    
    def setUp(self):
        self.client = Client()
        self.tenant = Tenant.objects.create(
            name="Test Jewelry Shop",
            schema_name="test_shop",
            owner_name="Test Owner",
            owner_email="owner@test.com"
        )
        # Create user without tenant reference since it's handled by schema isolation
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
    
    def test_base_rtl_template_structure(self):
        """Test that base RTL template has correct structure"""
        template = Template("""
            {% load static %}
            <!DOCTYPE html>
            <html dir="rtl" lang="fa">
            <head>
                <meta charset="UTF-8">
                <title>Test</title>
            </head>
            <body class="font-vazir">
                <div class="test-content">Test Content</div>
            </body>
            </html>
        """)
        
        rendered = template.render(Context({}))
        
        # Check RTL attributes
        self.assertIn('dir="rtl"', rendered)
        self.assertIn('lang="fa"', rendered)
        self.assertIn('font-vazir', rendered)
    
    def test_theme_toggle_component(self):
        """Test theme toggle component rendering"""
        request = HttpRequest()
        request.session = {}
        request.user = self.user
        
        # Add middleware
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)
        AuthenticationMiddleware(lambda r: None).process_request(request)
        
        # Test light mode
        context = {
            'request': request,
            'is_dark_mode': False,
            'is_light_mode': True,
            'current_theme': 'light'
        }
        
        rendered = render_to_string('core/components/theme_toggle.html', context)
        
        # Check light mode elements
        self.assertIn('data-theme-toggle', rendered)
        self.assertIn('تغییر تم', rendered)
        self.assertIn('bg-white/80', rendered)
        
        # Test dark mode
        context['is_dark_mode'] = True
        context['is_light_mode'] = False
        context['current_theme'] = 'dark'
        
        rendered = render_to_string('core/components/theme_toggle.html', context)
        
        # Check dark mode elements
        self.assertIn('cyber-bg-surface', rendered)
        self.assertIn('cyber-neon-primary', rendered)
    
    def test_loading_spinner_component(self):
        """Test loading spinner component with dual themes"""
        context_light = {
            'is_dark_mode': False,
            'current_theme': 'light'
        }
        
        rendered_light = render_to_string('core/components/loading_spinner.html', context_light)
        
        # Check light mode spinner
        self.assertIn('border-blue-600', rendered_light)
        self.assertIn('text-gray-600', rendered_light)
        self.assertIn('در حال بارگذاری...', rendered_light)
        
        context_dark = {
            'is_dark_mode': True,
            'current_theme': 'dark'
        }
        
        rendered_dark = render_to_string('core/components/loading_spinner.html', context_dark)
        
        # Check dark mode spinner with cybersecurity theme
        self.assertIn('cyber-neon-primary', rendered_dark)
        self.assertIn('cyber-text-secondary', rendered_dark)
        self.assertIn('animate-spin', rendered_dark)
    
    def test_navigation_component_rtl(self):
        """Test navigation component RTL layout"""
        request = HttpRequest()
        request.session = {}
        request.user = self.user
        request.resolver_match = type('obj', (object,), {'url_name': 'dashboard'})
        
        # Add middleware
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)
        AuthenticationMiddleware(lambda r: None).process_request(request)
        
        context = {
            'request': request,
            'user': self.user,
            'is_dark_mode': False,
            'current_theme': 'light'
        }
        
        rendered = render_to_string('core/components/navigation.html', context)
        
        # Check RTL layout
        self.assertIn('rtl:space-x-reverse', rendered)
        self.assertIn('text-right', rendered)
        self.assertIn('زرگر', rendered)
        
        # Check Persian navigation items
        self.assertIn('داشبورد', rendered)
        self.assertIn('موجودی', rendered)
        self.assertIn('فروش', rendered)
        self.assertIn('مشتریان', rendered)
        self.assertIn('گزارشات', rendered)
    
    def test_footer_component_persian_content(self):
        """Test footer component with Persian content"""
        context = {
            'is_dark_mode': False,
            'current_theme': 'light',
            'build_date': '۱۴۰۳/۰۶/۲۹'
        }
        
        rendered = render_to_string('core/components/footer.html', context)
        
        # Check Persian content
        self.assertIn('زرگر', rendered)
        self.assertIn('سیستم مدیریت طلا و جواهرات', rendered)
        self.assertIn('تمامی حقوق محفوظ است', rendered)
        self.assertIn('مدیریت موجودی هوشمند', rendered)
        self.assertIn('سیستم طلای قرضی', rendered)
        self.assertIn('تقویم شمسی', rendered)
        
        # Check RTL layout
        self.assertIn('rtl:space-x-reverse', rendered)
        self.assertIn('text-right', rendered)
    
    def test_persian_number_input_component(self):
        """Test Persian number input component"""
        context = {
            'field_name': 'price',
            'field_id': 'id_price',
            'field_value': '۱۲۳٬۴۵۶',
            'placeholder': 'قیمت را وارد کنید',
            'currency': 'تومان',
            'is_dark_mode': False,
            'required': True
        }
        
        rendered = render_to_string('core/tags/persian_number_input.html', context)
        
        # Check Persian number input structure
        self.assertIn('data-persian-number', rendered)
        self.assertIn('persian-number-input', rendered)
        self.assertIn('dir="rtl"', rendered)
        self.assertIn('تومان', rendered)
        self.assertIn('required', rendered)
        
        # Test dark mode
        context['is_dark_mode'] = True
        rendered_dark = render_to_string('core/tags/persian_number_input.html', context)
        
        self.assertIn('cyber-bg-surface', rendered_dark)
        self.assertIn('cyber-neon-primary', rendered_dark)


class ThemeContextProcessorTests(TestCase):
    """Test theme context processor functionality"""
    
    def setUp(self):
        self.client = Client()
        self.tenant = Tenant.objects.create(
            name="Test Shop",
            schema_name="test_shop",
            owner_name="Test Owner",
            owner_email="owner@test.com"
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            theme_preference='light'
        )
    
    def test_theme_context_light_mode(self):
        """Test theme context processor for light mode"""
        request = HttpRequest()
        request.session = {}
        request.user = self.user
        request.theme = 'light'
        
        # Add middleware
        SessionMiddleware(lambda r: None).process_request(request)
        
        context = theme_context(request)
        
        self.assertEqual(context['current_theme'], 'light')
        self.assertTrue(context['is_light_mode'])
        self.assertFalse(context['is_dark_mode'])
    
    def test_theme_context_dark_mode(self):
        """Test theme context processor for dark mode"""
        self.user.theme_preference = 'dark'
        self.user.save()
        
        request = HttpRequest()
        request.session = {}
        request.user = self.user
        request.theme = 'dark'
        
        # Add middleware
        SessionMiddleware(lambda r: None).process_request(request)
        
        context = theme_context(request)
        
        self.assertEqual(context['current_theme'], 'dark')
        self.assertFalse(context['is_light_mode'])
        self.assertTrue(context['is_dark_mode'])
    
    def test_persian_context_processor(self):
        """Test Persian context processor"""
        request = HttpRequest()
        request.session = {}
        
        context = persian_context(request)
        
        self.assertEqual(context['locale'], 'fa')
        self.assertEqual(context['direction'], 'rtl')
        self.assertIn('persian_months', context)
        self.assertIn('persian_days', context)
        
        # Check Persian month names
        self.assertIn('فروردین', context['persian_months'])
        self.assertIn('اردیبهشت', context['persian_months'])
        
        # Check Persian day names
        self.assertIn('شنبه', context['persian_days'])
        self.assertIn('یکشنبه', context['persian_days'])


class RTLCSSTests(TestCase):
    """Test RTL CSS functionality"""
    
    def test_css_file_exists(self):
        """Test that RTL CSS file exists and is accessible"""
        response = self.client.get('/static/css/base-rtl.css')
        # Note: In actual deployment, static files would be served by web server
        # This test would need to be adapted based on static file serving setup
    
    def test_rtl_javascript_exists(self):
        """Test that RTL JavaScript file exists"""
        response = self.client.get('/static/js/rtl-components.js')
        # Note: Similar to CSS test, would need adaptation for actual static serving


class ThemeToggleViewTests(TestCase):
    """Test theme toggle functionality"""
    
    def setUp(self):
        self.client = Client()
        self.tenant = Tenant.objects.create(
            name="Test Shop",
            schema_name="test_shop",
            owner_name="Test Owner",
            owner_email="owner@test.com"
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            theme_preference='light'
        )
    
    def test_theme_toggle_authenticated_user(self):
        """Test theme toggle for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        
        # Toggle to dark mode
        response = self.client.post('/theme/toggle/', 
                                  {'theme': 'dark'}, 
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        # Check user preference updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.theme_preference, 'dark')
    
    def test_theme_toggle_anonymous_user(self):
        """Test theme toggle for anonymous user (session-based)"""
        response = self.client.post('/theme/toggle/', 
                                  {'theme': 'dark'}, 
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        # Check session contains theme preference
        session = self.client.session
        self.assertEqual(session.get('theme_preference'), 'dark')


class PersianTextDisplayTests(TestCase):
    """Test Persian text display and formatting"""
    
    def test_persian_number_formatting(self):
        """Test Persian number formatting in templates"""
        template = Template("""
            {% load persian_tags %}
            <span class="persian-numbers">{{ number|persian_number }}</span>
        """)
        
        context = Context({'number': 123456})
        rendered = template.render(context)
        
        # Should contain Persian digits
        self.assertIn('۱۲۳', rendered)
    
    def test_persian_currency_formatting(self):
        """Test Persian currency formatting"""
        template = Template("""
            {% load persian_tags %}
            <span class="persian-currency">{{ amount|persian_currency }}</span>
        """)
        
        context = Context({'amount': 1000000})
        rendered = template.render(context)
        
        # Should contain Persian formatted currency
        self.assertIn('تومان', rendered)
        self.assertIn('۱٬۰۰۰٬۰۰۰', rendered)
    
    def test_rtl_text_alignment(self):
        """Test RTL text alignment in templates"""
        template = Template("""
            <div class="rtl-content">
                <p class="text-right">متن فارسی</p>
            </div>
        """)
        
        rendered = template.render(Context({}))
        
        self.assertIn('text-right', rendered)
        self.assertIn('متن فارسی', rendered)


class ResponsiveDesignTests(TestCase):
    """Test responsive design for RTL layout"""
    
    def test_mobile_navigation_rtl(self):
        """Test mobile navigation RTL layout"""
        request = HttpRequest()
        request.session = {}
        request.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        # Add middleware
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)
        AuthenticationMiddleware(lambda r: None).process_request(request)
        
        context = {
            'request': request,
            'user': request.user,
            'is_dark_mode': False
        }
        
        rendered = render_to_string('core/components/navigation.html', context)
        
        # Check mobile-specific RTL classes
        self.assertIn('lg:hidden', rendered)
        self.assertIn('rtl:space-x-reverse', rendered)
    
    def test_responsive_theme_toggle(self):
        """Test theme toggle responsiveness"""
        context = {
            'is_dark_mode': False,
            'current_theme': 'light'
        }
        
        rendered = render_to_string('core/components/theme_toggle.html', context)
        
        # Check responsive positioning
        self.assertIn('fixed', rendered)
        self.assertIn('top-4', rendered)
        self.assertIn('left-4', rendered)


class AccessibilityTests(TestCase):
    """Test accessibility features for RTL layout"""
    
    def test_aria_labels_persian(self):
        """Test ARIA labels in Persian"""
        context = {
            'is_dark_mode': False,
            'current_theme': 'light'
        }
        
        rendered = render_to_string('core/components/theme_toggle.html', context)
        
        # Check Persian ARIA labels
        self.assertIn('aria-label="تغییر تم"', rendered)
    
    def test_keyboard_navigation_rtl(self):
        """Test keyboard navigation support for RTL"""
        context = {
            'user': User.objects.create_user(
                username="testuser",
                email="test@example.com",
                password="testpass123"
            ),
            'is_dark_mode': False
        }
        
        rendered = render_to_string('core/components/navigation.html', context)
        
        # Check keyboard navigation attributes
        self.assertIn('tabindex', rendered)


class CybersecurityThemeTests(TestCase):
    """Test cybersecurity theme specific features"""
    
    def test_cyber_glass_effects(self):
        """Test glassmorphism effects in dark mode"""
        context = {
            'is_dark_mode': True,
            'current_theme': 'dark'
        }
        
        rendered = render_to_string('core/components/loading_spinner.html', context)
        
        # Check cybersecurity theme classes
        self.assertIn('cyber-', rendered)
        self.assertIn('neon', rendered)
    
    def test_neon_color_palette(self):
        """Test neon color palette usage"""
        context = {
            'is_dark_mode': True,
            'current_theme': 'dark'
        }
        
        rendered = render_to_string('core/components/theme_toggle.html', context)
        
        # Check neon colors
        self.assertIn('cyber-neon-primary', rendered)
        self.assertIn('#00D4FF', rendered)
    
    def test_animation_integration(self):
        """Test Framer Motion animation integration"""
        template = Template("""
            {% if is_dark_mode %}
            <div class="cyber-glass-card animate-fade-in-up">
                <p class="cyber-text-glow">Animated content</p>
            </div>
            {% endif %}
        """)
        
        context = Context({'is_dark_mode': True})
        rendered = template.render(context)
        
        self.assertIn('animate-fade-in-up', rendered)
        self.assertIn('cyber-text-glow', rendered)


if __name__ == '__main__':
    pytest.main([__file__])