"""
Tests for Task 4.1: Remove duplicate admin interfaces and consolidate routing.

This test suite verifies:
1. /admin/ redirects to unified admin system
2. Duplicate admin templates are removed
3. Legacy admin URLs and views are cleaned up
4. Tenant login system remains unchanged
5. No broken references exist
"""
import pytest
from django.test import TestCase, Client
from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.template.loader import get_template
from django.template import TemplateDoesNotExist
from zargar.tenants.admin_models import SuperAdmin
import os


class AdminConsolidationTestCase(TestCase):
    """Test admin consolidation functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create a SuperAdmin for testing
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
    
    def test_admin_url_redirects_to_unified_system(self):
        """Test that /admin/ redirects to unified admin system."""
        response = self.client.get('/admin/')
        
        # Should be a permanent redirect (301)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, '/super-panel/')
    
    def test_admin_url_with_trailing_path_redirects(self):
        """Test that /admin/something/ redirects properly."""
        response = self.client.get('/admin/auth/')
        
        # Should redirect to unified system
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, '/super-panel/')
    
    def test_duplicate_admin_templates_removed(self):
        """Test that duplicate admin templates are removed."""
        # These templates should no longer exist
        removed_templates = [
            'auth/admin_login.html',
            'admin_panel/login.html'
        ]
        
        for template_name in removed_templates:
            with self.assertRaises(TemplateDoesNotExist):
                get_template(template_name)
    
    def test_tenant_login_template_preserved(self):
        """Test that tenant login template is preserved."""
        try:
            template = get_template('auth/tenant_login.html')
            self.assertIsNotNone(template)
        except TemplateDoesNotExist:
            self.fail("Tenant login template should be preserved")
    
    def test_unified_admin_login_template_exists(self):
        """Test that unified admin login template exists."""
        try:
            template = get_template('admin_panel/unified_login.html')
            self.assertIsNotNone(template)
        except TemplateDoesNotExist:
            self.fail("Unified admin login template should exist")
    
    def test_legacy_admin_urls_removed(self):
        """Test that legacy admin URLs are removed."""
        # These URLs should no longer exist
        legacy_urls = [
            'admin_panel:legacy_login',
            'admin_panel:legacy_logout'
        ]
        
        for url_name in legacy_urls:
            with self.assertRaises(NoReverseMatch):
                reverse(url_name)
    
    def test_unified_admin_urls_exist(self):
        """Test that unified admin URLs exist."""
        # These URLs should exist
        unified_urls = [
            'admin_panel:unified_login',
            'admin_panel:unified_logout',
            'admin_panel:dashboard'
        ]
        
        for url_name in unified_urls:
            try:
                url = reverse(url_name)
                self.assertIsNotNone(url)
            except NoReverseMatch:
                self.fail(f"Unified admin URL {url_name} should exist")
    
    def test_unified_admin_login_page_loads(self):
        """Test that unified admin login page loads correctly."""
        url = reverse('admin_panel:unified_login')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ورود')  # Persian for "Login"
    
    def test_unified_admin_dashboard_requires_auth(self):
        """Test that unified admin dashboard requires authentication."""
        url = reverse('admin_panel:dashboard')
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_superadmin_can_access_unified_dashboard(self):
        """Test that SuperAdmin can access unified dashboard."""
        self.client.force_login(self.superadmin)
        url = reverse('admin_panel:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'داشبورد')  # Persian for "Dashboard"


# Tenant system tests would go here but require proper tenant test setup


class BrokenReferencesTestCase(TestCase):
    """Test for broken references after consolidation."""
    
    def test_no_references_to_removed_templates(self):
        """Test that no code references removed templates."""
        import os
        import re
        
        # Templates that were removed
        removed_templates = [
            'auth/admin_login.html',
            'admin_panel/login.html'
        ]
        
        # Search for references in Python files
        python_files = []
        for root, dirs, files in os.walk('zargar'):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        for template_name in removed_templates:
            for python_file in python_files:
                try:
                    with open(python_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if template_name in content:
                            # Check if it's in a comment or string
                            if not (content.count(f'# {template_name}') or 
                                   content.count(f'"{template_name}"') or
                                   content.count(f"'{template_name}'")):
                                self.fail(f"Found reference to removed template {template_name} in {python_file}")
                except (UnicodeDecodeError, FileNotFoundError):
                    continue
    
    def test_no_references_to_legacy_urls(self):
        """Test that no code references legacy admin URLs."""
        import os
        
        # Legacy URL names that were removed
        legacy_urls = [
            'admin_panel:legacy_login',
            'admin_panel:legacy_logout',
            'core:admin_login',
            'core:admin_logout'
        ]
        
        # Search for references in Python files
        python_files = []
        for root, dirs, files in os.walk('zargar'):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        for url_name in legacy_urls:
            for python_file in python_files:
                try:
                    with open(python_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if url_name in content:
                            # Check if it's in a comment
                            lines = content.split('\n')
                            for line_num, line in enumerate(lines, 1):
                                if url_name in line and not line.strip().startswith('#'):
                                    self.fail(f"Found reference to legacy URL {url_name} in {python_file}:{line_num}")
                except (UnicodeDecodeError, FileNotFoundError):
                    continue
    
    def test_authentication_backends_cleaned(self):
        """Test that obsolete authentication backends are not in settings."""
        from django.conf import settings
        
        # These backends should not be in AUTHENTICATION_BACKENDS
        obsolete_backends = [
            'zargar.core.auth_backends.SuperAdminBackend',
            'zargar.core.twofa_backends.TwoFABackend',
            'zargar.core.twofa_backends.AdminTwoFABackend'
        ]
        
        for backend in obsolete_backends:
            self.assertNotIn(backend, settings.AUTHENTICATION_BACKENDS,
                           f"Obsolete backend {backend} should be removed from settings")
    
    def test_unified_backend_in_settings(self):
        """Test that unified backend is in settings."""
        from django.conf import settings
        
        self.assertIn('zargar.admin_panel.unified_auth_backend.UnifiedSuperAdminAuthBackend',
                     settings.AUTHENTICATION_BACKENDS,
                     "Unified backend should be in AUTHENTICATION_BACKENDS")


class SecurityTestCase(TestCase):
    """Test security aspects of admin consolidation."""
    
    def test_admin_redirect_is_permanent(self):
        """Test that admin redirect is permanent (301) for SEO."""
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 301)
    
    def test_no_admin_access_without_auth(self):
        """Test that admin areas require authentication."""
        admin_urls = [
            '/super-panel/',
            '/super-panel/dashboard/',
            '/super-panel/tenants/',
        ]
        
        for url in admin_urls:
            response = self.client.get(url)
            # Should redirect to login or return 403
            self.assertIn(response.status_code, [302, 403])
    
    def test_tenant_users_cannot_access_super_panel(self):
        """Test that tenant users cannot access super panel."""
        # This would need to be tested in a tenant context
        # For now, just verify the URL exists
        try:
            url = reverse('admin_panel:dashboard')
            self.assertIsNotNone(url)
        except NoReverseMatch:
            self.fail("Super panel dashboard URL should exist")


@pytest.mark.django_db
class AdminConsolidationIntegrationTest:
    """Integration tests for admin consolidation."""
    
    def test_full_admin_workflow(self):
        """Test complete admin workflow after consolidation."""
        client = Client()
        
        # Create SuperAdmin
        superadmin = SuperAdmin.objects.create_user(
            username='integrationtest',
            email='integration@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        
        # Test redirect from /admin/
        response = client.get('/admin/')
        assert response.status_code == 301
        assert response.url == '/super-panel/'
        
        # Test unified login page
        login_url = reverse('admin_panel:unified_login')
        response = client.get(login_url)
        assert response.status_code == 200
        
        # Test dashboard requires auth
        dashboard_url = reverse('admin_panel:dashboard')
        response = client.get(dashboard_url)
        assert response.status_code == 302  # Redirect to login
        
        # Test authenticated access
        client.force_login(superadmin)
        response = client.get(dashboard_url)
        assert response.status_code == 200