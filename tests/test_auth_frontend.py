"""
Frontend tests for authentication templates and theme switching.
"""
import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from zargar.tenants.models import Tenant, Domain
from zargar.core.models import AuditLog
import json

User = get_user_model()


class AuthenticationTemplateTests(TestCase):
    """
    Test authentication templates and functionality.
    """
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test tenant
        self.tenant = Tenant.objects.create(
            name='Test Jewelry Shop',
            schema_name='test_shop',
            is_active=True
        )
        
        # Create domain for tenant
        self.domain = Domain.objects.create(
            domain='testshop.zargar.com',
            tenant=self.tenant,
            is_primary=True
        )
        
        # Create test users
        self.super_admin = User.objects.create_user(
            username='superadmin',
            email='admin@zargar.com',
            password='testpass123',
            role='super_admin',
            is_superuser=True,
            persian_first_name='مدیر',
            persian_last_name='سیستم'
        )
        
        self.tenant_owner = User.objects.create_user(
            username='shopowner',
            email='owner@testshop.com',
            password='testpass123',
            role='owner',
            tenant_schema='test_shop',
            persian_first_name='مالک',
            persian_last_name='فروشگاه'
        )
        
        self.tenant_employee = User.objects.create_user(
            username='employee',
            email='employee@testshop.com',
            password='testpass123',
            role='salesperson',
            tenant_schema='test_shop',
            persian_first_name='کارمند',
            persian_last_name='فروش'
        )
    
    def test_admin_login_template_renders(self):
        """Test that admin login template renders correctly."""
        response = self.client.get('/super-panel/login/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ورود مدیر سیستم')
        self.assertContains(response, 'پنل مدیریت سوپر ادمین')
        self.assertContains(response, 'نام کاربری')
        self.assertContains(response, 'رمز عبور')
        self.assertContains(response, 'مرا به خاطر بسپار')
        
        # Check for theme toggle button
        self.assertContains(response, 'data-theme-toggle')
        
        # Check for Persian elements
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, 'lang="fa"')
        self.assertContains(response, 'font-vazir')
    
    def test_tenant_login_template_renders(self):
        """Test that tenant login template renders correctly."""
        # Simulate tenant request
        response = self.client.get('/login/', HTTP_HOST='testshop.zargar.com')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ورود به فروشگاه')
        self.assertContains(response, 'نام کاربری')
        self.assertContains(response, 'رمز عبور')
        
        # Check for theme toggle button
        self.assertContains(response, 'data-theme-toggle')
        
        # Check for Persian elements
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, 'lang="fa"')
    
    def test_admin_login_functionality(self):
        """Test admin login functionality."""
        response = self.client.post('/super-panel/login/', {
            'username': 'superadmin',
            'password': 'testpass123'
        })
        
        # Should redirect to dashboard after successful login
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/super-panel/')
        
        # Check audit log
        audit_log = AuditLog.objects.filter(
            user=self.super_admin,
            action='login'
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['login_type'], 'admin_panel')
    
    def test_tenant_login_functionality(self):
        """Test tenant login functionality."""
        response = self.client.post('/login/', {
            'username': 'shopowner',
            'password': 'testpass123'
        }, HTTP_HOST='testshop.zargar.com')
        
        # Should redirect to tenant dashboard after successful login
        self.assertEqual(response.status_code, 302)
        
        # Check audit log
        audit_log = AuditLog.objects.filter(
            user=self.tenant_owner,
            action='login'
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['login_type'], 'tenant_portal')
    
    def test_failed_login_audit_logging(self):
        """Test that failed login attempts are logged."""
        response = self.client.post('/super-panel/login/', {
            'username': 'wronguser',
            'password': 'wrongpass'
        })
        
        # Should stay on login page
        self.assertEqual(response.status_code, 200)
        
        # Check audit log for failed attempt
        audit_log = AuditLog.objects.filter(
            action='login_failed'
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['username'], 'wronguser')
        self.assertEqual(audit_log.details['login_type'], 'admin_panel')
    
    def test_theme_toggle_functionality(self):
        """Test theme toggle functionality."""
        # Login first
        self.client.login(username='superadmin', password='testpass123')
        
        # Test theme toggle
        response = self.client.post('/super-panel/theme/toggle/', 
            json.dumps({'theme': 'dark'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['theme'], 'dark')
        
        # Check that user preference was updated
        self.super_admin.refresh_from_db()
        self.assertEqual(self.super_admin.theme_preference, 'dark')
        
        # Check that cookie was set
        self.assertIn(settings.THEME_SETTINGS['THEME_COOKIE_NAME'], response.cookies)
        self.assertEqual(
            response.cookies[settings.THEME_SETTINGS['THEME_COOKIE_NAME']].value,
            'dark'
        )
        
        # Check audit log
        audit_log = AuditLog.objects.filter(
            user=self.super_admin,
            action='theme_changed'
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['new_theme'], 'dark')
    
    def test_theme_persistence_across_sessions(self):
        """Test that theme preference persists across sessions."""
        # Set user theme preference
        self.super_admin.theme_preference = 'dark'
        self.super_admin.save()
        
        # Login
        self.client.login(username='superadmin', password='testpass123')
        
        # Check that theme is applied
        response = self.client.get('/super-panel/')
        self.assertContains(response, 'dark')
        self.assertContains(response, 'cyber-theme')
    
    def test_rtl_layout_elements(self):
        """Test that RTL layout elements are present."""
        response = self.client.get('/super-panel/login/')
        
        # Check RTL attributes
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, 'lang="fa"')
        
        # Check Persian font
        self.assertContains(response, 'font-vazir')
        
        # Check Persian text
        self.assertContains(response, 'ورود مدیر سیستم')
        self.assertContains(response, 'نام کاربری')
        self.assertContains(response, 'رمز عبور')
    
    def test_cybersecurity_theme_elements(self):
        """Test that cybersecurity theme elements are present in dark mode."""
        # Set theme cookie to dark
        self.client.cookies[settings.THEME_SETTINGS['THEME_COOKIE_NAME']] = 'dark'
        
        response = self.client.get('/super-panel/login/')
        
        # Check for cybersecurity theme classes
        self.assertContains(response, 'cyber-theme')
        self.assertContains(response, 'cyber-glass-card')
        self.assertContains(response, 'cyber-neon-button')
        
        # Check for cybersecurity colors
        self.assertContains(response, '#0B0E1A')  # cyber-bg-primary
        self.assertContains(response, '#00D4FF')  # cyber-neon-primary
        self.assertContains(response, '#00FF88')  # cyber-neon-secondary
    
    def test_2fa_field_toggle(self):
        """Test that 2FA field can be toggled."""
        response = self.client.get('/super-panel/login/')
        
        # Check for 2FA toggle button
        self.assertContains(response, 'show2FA')
        self.assertContains(response, 'two_factor_code')
        
        # Check for 2FA field attributes
        self.assertContains(response, 'maxlength="6"')
        self.assertContains(response, 'pattern="[0-9]{6}"')
        self.assertContains(response, 'data-persian-input')
    
    def test_persian_number_formatting(self):
        """Test that Persian number formatting is applied."""
        response = self.client.get('/super-panel/login/')
        
        # Check for Persian number classes
        self.assertContains(response, 'persian-numbers')
        
        # Check for Persian number placeholder
        self.assertContains(response, '۱۲۳۴۵۶')
    
    def test_responsive_design_elements(self):
        """Test that responsive design elements are present."""
        response = self.client.get('/super-panel/login/')
        
        # Check for responsive classes
        self.assertContains(response, 'sm:px-6')
        self.assertContains(response, 'lg:px-8')
        self.assertContains(response, 'max-w-md')
        
        # Check for mobile-friendly viewport
        self.assertContains(response, 'width=device-width')
        self.assertContains(response, 'initial-scale=1.0')
    
    def test_accessibility_features(self):
        """Test that accessibility features are present."""
        response = self.client.get('/super-panel/login/')
        
        # Check for proper labels
        self.assertContains(response, 'for="username"')
        self.assertContains(response, 'for="password"')
        
        # Check for aria-label
        self.assertContains(response, 'aria-label')
        
        # Check for required attributes
        self.assertContains(response, 'required')
    
    def test_security_features(self):
        """Test that security features are present."""
        response = self.client.get('/super-panel/login/')
        
        # Check for CSRF token
        self.assertContains(response, 'csrfmiddlewaretoken')
        
        # Check for secure form attributes
        self.assertContains(response, 'method="post"')
        
        # Check for password field security
        self.assertContains(response, 'type="password"')
    
    def test_javascript_integration(self):
        """Test that JavaScript integration is present."""
        response = self.client.get('/super-panel/login/')
        
        # Check for required JavaScript libraries
        self.assertContains(response, 'alpine')
        self.assertContains(response, 'htmx')
        self.assertContains(response, 'tailwind')
        
        # Check for custom JavaScript files
        self.assertContains(response, 'theme-toggle.js')
        self.assertContains(response, 'persian-utils.js')
        
        # Check for JavaScript variables
        self.assertContains(response, 'window.csrfToken')
        self.assertContains(response, 'window.currentTheme')
    
    def test_logout_functionality(self):
        """Test logout functionality."""
        # Login first
        self.client.login(username='superadmin', password='testpass123')
        
        # Logout
        response = self.client.post('/super-panel/logout/')
        
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        
        # Check audit log
        audit_log = AuditLog.objects.filter(
            user=self.super_admin,
            action='logout'
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['logout_type'], 'admin_panel')


class ThemeSwitchingTests(TestCase):
    """
    Test theme switching functionality.
    """
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='super_admin',
            is_superuser=True
        )
    
    def test_light_to_dark_theme_switch(self):
        """Test switching from light to dark theme."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post('/super-panel/theme/toggle/',
            json.dumps({'theme': 'dark'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['theme'], 'dark')
        
        # Check user preference
        self.user.refresh_from_db()
        self.assertEqual(self.user.theme_preference, 'dark')
    
    def test_dark_to_light_theme_switch(self):
        """Test switching from dark to light theme."""
        self.user.theme_preference = 'dark'
        self.user.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post('/super-panel/theme/toggle/',
            json.dumps({'theme': 'light'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['theme'], 'light')
        
        # Check user preference
        self.user.refresh_from_db()
        self.assertEqual(self.user.theme_preference, 'light')
    
    def test_invalid_theme_rejection(self):
        """Test that invalid themes are rejected."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post('/super-panel/theme/toggle/',
            json.dumps({'theme': 'invalid'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_unauthenticated_theme_toggle(self):
        """Test that unauthenticated users cannot toggle theme."""
        response = self.client.post('/super-panel/theme/toggle/',
            json.dumps({'theme': 'dark'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_theme_cookie_setting(self):
        """Test that theme cookie is set correctly."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post('/super-panel/theme/toggle/',
            json.dumps({'theme': 'dark'}),
            content_type='application/json'
        )
        
        # Check cookie
        cookie_name = settings.THEME_SETTINGS['THEME_COOKIE_NAME']
        self.assertIn(cookie_name, response.cookies)
        self.assertEqual(response.cookies[cookie_name].value, 'dark')
        
        # Check cookie attributes
        cookie = response.cookies[cookie_name]
        self.assertEqual(cookie['max-age'], settings.THEME_SETTINGS['THEME_COOKIE_AGE'])
        self.assertEqual(cookie['samesite'], 'Lax')


@pytest.mark.django_db
class PersianLocalizationTests(TestCase):
    """
    Test Persian localization features.
    """
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
    
    def test_persian_date_display(self):
        """Test that Persian dates are displayed correctly."""
        response = self.client.get('/super-panel/login/')
        
        # Check for Persian date elements
        self.assertContains(response, 'shamsi_today')
        self.assertContains(response, 'persian-numbers')
    
    def test_rtl_direction(self):
        """Test that RTL direction is set correctly."""
        response = self.client.get('/super-panel/login/')
        
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, 'lang="fa"')
    
    def test_persian_fonts(self):
        """Test that Persian fonts are loaded."""
        response = self.client.get('/super-panel/login/')
        
        self.assertContains(response, 'Vazirmatn')
        self.assertContains(response, 'font-vazir')
    
    def test_persian_text_content(self):
        """Test that Persian text content is present."""
        response = self.client.get('/super-panel/login/')
        
        # Check for Persian text
        self.assertContains(response, 'ورود مدیر سیستم')
        self.assertContains(response, 'نام کاربری')
        self.assertContains(response, 'رمز عبور')
        self.assertContains(response, 'مرا به خاطر بسپار')
        self.assertContains(response, 'فراموشی رمز عبور؟')
    
    def test_persian_number_inputs(self):
        """Test that Persian number inputs are configured."""
        response = self.client.get('/super-panel/login/')
        
        # Check for Persian input attributes
        self.assertContains(response, 'data-persian-input')
        self.assertContains(response, '۱۲۳۴۵۶')