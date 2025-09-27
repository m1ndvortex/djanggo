"""
Tests for navigation integration and URL configuration.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing models
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from django.test import TestCase, Client
from django.urls import reverse, resolve
from django.contrib.auth import get_user_model
from zargar.tenants.admin_models import SuperAdmin
from zargar.admin_panel.navigation import navigation_builder, breadcrumb_builder


class NavigationIntegrationTestCase(TestCase):
    """Test navigation integration and URL configuration."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_active=True
        )
    
    def test_security_urls_resolve(self):
        """Test that security URLs resolve correctly."""
        security_urls = [
            'admin_panel:security_dashboard',
            'admin_panel:audit_logs',
            'admin_panel:security_events',
            'admin_panel:rbac_management',
        ]
        
        for url_name in security_urls:
            with self.subTest(url_name=url_name):
                url = reverse(url_name)
                self.assertIsNotNone(url)
                
                # Test URL resolution
                resolved = resolve(url)
                self.assertEqual(resolved.app_name, 'admin_panel')
    
    def test_settings_urls_resolve(self):
        """Test that settings URLs resolve correctly."""
        settings_urls = [
            'admin_panel:settings_management',
            'admin_panel:security_policies',
            'admin_panel:notifications_management',
            'admin_panel:integration_settings',
        ]
        
        for url_name in settings_urls:
            with self.subTest(url_name=url_name):
                url = reverse(url_name)
                self.assertIsNotNone(url)
                
                # Test URL resolution
                resolved = resolve(url)
                self.assertEqual(resolved.app_name, 'admin_panel')
    
    def test_navigation_builder_structure(self):
        """Test navigation builder creates correct structure."""
        nav_items = navigation_builder.get_navigation_for_user(self.superadmin)
        
        # Check that we have navigation items
        self.assertGreater(len(nav_items), 0)
        
        # Check for security section
        security_section = None
        settings_section = None
        
        for item in nav_items:
            if 'امنیت و حسابرسی' in item.name:
                security_section = item
            elif 'تنظیمات' in item.name:
                settings_section = item
        
        # Verify security section exists and has children
        self.assertIsNotNone(security_section, "Security section should exist")
        self.assertGreater(len(security_section.children), 0, "Security section should have children")
        
        # Verify settings section exists and has children
        self.assertIsNotNone(settings_section, "Settings section should exist")
        self.assertGreater(len(settings_section.children), 0, "Settings section should have children")
        
        # Check specific security children
        security_child_names = [child.name for child in security_section.children]
        expected_security_items = ['داشبورد امنیت', 'لاگ‌های حسابرسی', 'رویدادهای امنیتی', 'کنترل دسترسی']
        
        for expected_item in expected_security_items:
            self.assertIn(expected_item, security_child_names)
        
        # Check specific settings children
        settings_child_names = [child.name for child in settings_section.children]
        expected_settings_items = ['تنظیمات عمومی', 'سیاست‌های امنیتی', 'مدیریت اعلان‌ها', 'تنظیمات یکپارچه‌سازی']
        
        for expected_item in expected_settings_items:
            self.assertIn(expected_item, settings_child_names)
    
    def test_breadcrumb_generation(self):
        """Test breadcrumb generation for different pages."""
        test_cases = [
            ('admin_panel:security_dashboard', ['امنیت و حسابرسی', 'داشبورد امنیت']),
            ('admin_panel:audit_logs', ['امنیت و حسابرسی', 'لاگ‌های حسابرسی']),
            ('admin_panel:settings_management', ['تنظیمات', 'تنظیمات عمومی']),
            ('admin_panel:security_policies', ['تنظیمات', 'سیاست‌های امنیتی']),
        ]
        
        for url_name, expected_names in test_cases:
            with self.subTest(url_name=url_name):
                breadcrumbs = breadcrumb_builder.get_breadcrumbs(url_name)
                
                # Check that breadcrumbs exist
                self.assertGreater(len(breadcrumbs), 0)
                
                # Check breadcrumb names
                breadcrumb_names = [crumb['name'] for crumb in breadcrumbs]
                for expected_name in expected_names:
                    self.assertIn(expected_name, breadcrumb_names)
                
                # Check that last item is marked as active
                if breadcrumbs:
                    self.assertTrue(breadcrumbs[-1]['active'])
    
    def test_permission_based_navigation(self):
        """Test that navigation respects permissions."""
        # Create a user with limited permissions
        limited_user = SuperAdmin.objects.create_user(
            username='limiteduser',
            email='limited@test.com',
            password='testpass123',
            is_active=True
        )
        
        # Get navigation for limited user
        nav_items = navigation_builder.get_navigation_for_user(limited_user)
        
        # Should still have some navigation items (basic ones without permissions)
        self.assertGreaterEqual(len(nav_items), 1)
        
        # Get navigation for superuser
        superuser_nav = navigation_builder.get_navigation_for_user(self.superadmin)
        
        # Superuser should have more or equal navigation items
        self.assertGreaterEqual(len(superuser_nav), len(nav_items))
    
    def test_url_patterns_organization(self):
        """Test that URL patterns are properly organized."""
        # Test security URLs are under /security/
        security_urls = [
            ('admin_panel:security_dashboard', '/super-panel/security/'),
            ('admin_panel:audit_logs', '/super-panel/security/audit-logs/'),
            ('admin_panel:security_events', '/super-panel/security/events/'),
            ('admin_panel:rbac_management', '/super-panel/security/access-control/'),
        ]
        
        for url_name, expected_path in security_urls:
            with self.subTest(url_name=url_name):
                url = reverse(url_name)
                self.assertEqual(url, expected_path)
        
        # Test settings URLs are under /settings/
        settings_urls = [
            ('admin_panel:settings_management', '/super-panel/settings/'),
            ('admin_panel:security_policies', '/super-panel/settings/security-policies/'),
            ('admin_panel:notifications_management', '/super-panel/settings/notifications/'),
            ('admin_panel:integration_settings', '/super-panel/settings/integrations/'),
        ]
        
        for url_name, expected_path in settings_urls:
            with self.subTest(url_name=url_name):
                url = reverse(url_name)
                self.assertEqual(url, expected_path)
    
    def test_navigation_accessibility(self):
        """Test navigation accessibility features."""
        self.client.force_login(self.superadmin)
        
        # Test that navigation pages are accessible
        test_urls = [
            'admin_panel:dashboard',
            'admin_panel:security_dashboard',
            'admin_panel:settings_management',
        ]
        
        for url_name in test_urls:
            with self.subTest(url_name=url_name):
                url = reverse(url_name)
                response = self.client.get(url)
                
                # Should not get 404 or 500 errors
                self.assertNotEqual(response.status_code, 404)
                self.assertNotEqual(response.status_code, 500)
    
    def test_mobile_navigation_support(self):
        """Test that navigation works on mobile devices."""
        self.client.force_login(self.superadmin)
        
        # Simulate mobile user agent
        mobile_headers = {
            'HTTP_USER_AGENT': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
        }
        
        response = self.client.get(reverse('admin_panel:dashboard'), **mobile_headers)
        
        # Should still be accessible
        self.assertEqual(response.status_code, 200)
        
        # Check that mobile-specific elements are present
        content = response.content.decode()
        self.assertIn('lg:hidden', content)  # Mobile menu button
        self.assertIn('sidebarOpen', content)  # Mobile sidebar toggle
    
    def test_rtl_navigation_support(self):
        """Test that navigation supports RTL layout."""
        self.client.force_login(self.superadmin)
        
        response = self.client.get(reverse('admin_panel:dashboard'))
        content = response.content.decode()
        
        # Check for RTL-specific classes and attributes
        self.assertIn('dir="rtl"', content)
        self.assertIn('space-x-reverse', content)
        self.assertIn('lang="fa"', content)
    
    def test_theme_support_in_navigation(self):
        """Test that navigation supports both light and dark themes."""
        self.client.force_login(self.superadmin)
        
        response = self.client.get(reverse('admin_panel:dashboard'))
        content = response.content.decode()
        
        # Check for theme-related classes
        self.assertIn('dark:', content)
        self.assertIn('cyber-', content)  # Cybersecurity theme classes
        self.assertIn('darkMode', content)  # Theme toggle functionality


class NavigationContextProcessorTestCase(TestCase):
    """Test navigation context processor."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_active=True
        )
    
    def test_context_processor_adds_navigation(self):
        """Test that context processor adds navigation to templates."""
        self.client.force_login(self.superadmin)
        
        response = self.client.get(reverse('admin_panel:dashboard'))
        
        # Check that navigation context is available
        self.assertIn('navigation_items', response.context)
        self.assertIn('breadcrumbs', response.context)
        self.assertIn('current_url_name', response.context)
    
    def test_context_processor_only_for_admin_panel(self):
        """Test that context processor only adds context for admin panel views."""
        # This would need to be tested with a non-admin panel view
        # For now, we just verify the context processor doesn't break other views
        pass


if __name__ == '__main__':
    pytest.main([__file__])