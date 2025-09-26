"""
Simple test for integration settings frontend.
"""
import pytest
from django.test import TestCase
from django.urls import reverse, resolve
from zargar.admin_panel.integration_views import IntegrationSettingsView


class IntegrationSettingsSimpleTest(TestCase):
    """Simple test for integration settings functionality."""
    
    def test_integration_settings_url_resolves(self):
        """Test that integration settings URL resolves correctly."""
        url = reverse('admin_panel:integration_settings')
        self.assertEqual(url, '/super-panel/settings/integrations/')
        
        # Test URL resolution
        resolver = resolve('/super-panel/settings/integrations/')
        self.assertEqual(resolver.view_name, 'admin_panel:integration_settings')
        self.assertEqual(resolver.func.view_class, IntegrationSettingsView)
    
    def test_service_configuration_url_resolves(self):
        """Test that service configuration URL resolves correctly."""
        url = reverse('admin_panel:service_configuration')
        self.assertEqual(url, '/super-panel/settings/integrations/service/')
    
    def test_rate_limit_configuration_url_resolves(self):
        """Test that rate limit configuration URL resolves correctly."""
        url = reverse('admin_panel:rate_limit_configuration')
        self.assertEqual(url, '/super-panel/settings/integrations/rate-limit/')
    
    def test_integration_health_url_resolves(self):
        """Test that integration health URL resolves correctly."""
        url = reverse('admin_panel:integration_health')
        self.assertEqual(url, '/super-panel/settings/integrations/health/')
    
    def test_integration_health_history_url_resolves(self):
        """Test that integration health history URL resolves correctly."""
        url = reverse('admin_panel:integration_health_history')
        self.assertEqual(url, '/super-panel/settings/integrations/health/history/')


class IntegrationSettingsViewTest(TestCase):
    """Test integration settings view class."""
    
    def test_integration_settings_view_template(self):
        """Test that integration settings view uses correct template."""
        view = IntegrationSettingsView()
        self.assertEqual(view.template_name, 'admin_panel/settings/integration_settings.html')
    
    def test_integration_settings_view_inheritance(self):
        """Test that integration settings view inherits from correct base classes."""
        from zargar.admin_panel.views import SuperAdminRequiredMixin
        from django.views.generic import TemplateView
        
        # Check inheritance
        self.assertTrue(issubclass(IntegrationSettingsView, SuperAdminRequiredMixin))
        self.assertTrue(issubclass(IntegrationSettingsView, TemplateView))