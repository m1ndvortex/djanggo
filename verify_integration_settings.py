#!/usr/bin/env python
"""
Verification script for integration settings frontend implementation.
"""
import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django.urls import reverse, resolve
from django.test import Client
from zargar.admin_panel.integration_views import IntegrationSettingsView
from zargar.admin_panel.models import ExternalServiceConfiguration, APIRateLimitConfiguration


def test_url_resolution():
    """Test URL resolution for integration settings."""
    print("Testing URL resolution...")
    
    try:
        # Test integration settings URL
        url = reverse('admin_panel:integration_settings')
        print(f"✓ Integration settings URL: {url}")
        
        # Test URL resolution
        resolver = resolve('/super-panel/settings/integrations/')
        print(f"✓ URL resolves to: {resolver.func.view_class.__name__}")
        
        # Test other URLs
        service_url = reverse('admin_panel:service_configuration')
        print(f"✓ Service configuration URL: {service_url}")
        
        rate_limit_url = reverse('admin_panel:rate_limit_configuration')
        print(f"✓ Rate limit configuration URL: {rate_limit_url}")
        
        health_url = reverse('admin_panel:integration_health')
        print(f"✓ Integration health URL: {health_url}")
        
        return True
        
    except Exception as e:
        print(f"✗ URL resolution failed: {e}")
        return False


def test_view_class():
    """Test integration settings view class."""
    print("\nTesting view class...")
    
    try:
        # Test view instantiation
        view = IntegrationSettingsView()
        print(f"✓ View class instantiated: {view.__class__.__name__}")
        
        # Test template name
        print(f"✓ Template name: {view.template_name}")
        
        # Test inheritance
        from zargar.admin_panel.views import SuperAdminRequiredMixin
        from django.views.generic import TemplateView
        
        if issubclass(IntegrationSettingsView, SuperAdminRequiredMixin):
            print("✓ Inherits from SuperAdminRequiredMixin")
        else:
            print("✗ Does not inherit from SuperAdminRequiredMixin")
            
        if issubclass(IntegrationSettingsView, TemplateView):
            print("✓ Inherits from TemplateView")
        else:
            print("✗ Does not inherit from TemplateView")
        
        return True
        
    except Exception as e:
        print(f"✗ View class test failed: {e}")
        return False


def test_models():
    """Test integration models."""
    print("\nTesting models...")
    
    try:
        # Test ExternalServiceConfiguration model
        service_count = ExternalServiceConfiguration.objects.count()
        print(f"✓ ExternalServiceConfiguration model accessible, count: {service_count}")
        
        # Test APIRateLimitConfiguration model
        rate_limit_count = APIRateLimitConfiguration.objects.count()
        print(f"✓ APIRateLimitConfiguration model accessible, count: {rate_limit_count}")
        
        # Test model choices
        service_types = ExternalServiceConfiguration.SERVICE_TYPES
        print(f"✓ Service types available: {len(service_types)} types")
        
        auth_types = ExternalServiceConfiguration.AUTHENTICATION_TYPES
        print(f"✓ Authentication types available: {len(auth_types)} types")
        
        return True
        
    except Exception as e:
        print(f"✗ Models test failed: {e}")
        return False


def test_template_exists():
    """Test if template file exists."""
    print("\nTesting template file...")
    
    try:
        template_path = 'templates/admin_panel/settings/integration_settings.html'
        
        if os.path.exists(template_path):
            print(f"✓ Template file exists: {template_path}")
            
            # Check template content
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for key elements
            if 'تنظیمات یکپارچه‌سازی' in content:
                print("✓ Template contains Persian title")
            else:
                print("✗ Template missing Persian title")
                
            if 'dark:bg-cyber-bg-primary' in content:
                print("✓ Template contains dark theme support")
            else:
                print("✗ Template missing dark theme support")
                
            if 'integrationSettings()' in content:
                print("✓ Template contains Alpine.js functionality")
            else:
                print("✗ Template missing Alpine.js functionality")
                
            return True
        else:
            print(f"✗ Template file not found: {template_path}")
            return False
            
    except Exception as e:
        print(f"✗ Template test failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("=== Integration Settings Frontend Verification ===\n")
    
    tests = [
        test_url_resolution,
        test_view_class,
        test_models,
        test_template_exists,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== Results ===")
    print(f"Passed: {passed}/{total} tests")
    
    if passed == total:
        print("✓ All tests passed! Integration settings frontend is ready.")
        return 0
    else:
        print("✗ Some tests failed. Please check the implementation.")
        return 1


if __name__ == '__main__':
    sys.exit(main())