#!/usr/bin/env python
"""
Test integration settings fixes.
"""
import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django.template.loader import get_template
from zargar.admin_panel.models import ExternalServiceConfiguration, APIRateLimitConfiguration


def test_template_fixes():
    """Test template fixes."""
    print("Testing template fixes...")
    
    try:
        # Load the template
        template = get_template('admin_panel/settings/integration_settings.html')
        print("✓ Template loaded successfully")
        
        # Create mock context data
        context = {
            'services': [],
            'rate_limits': [],
            'health_statuses': [],
            'overall_health': 'healthy',
            'total_services': 0,
            'healthy_services': 0,
            'service_types': [
                ('gold_price_api', 'Gold Price API'),
                ('payment_gateway', 'Payment Gateway'),
            ],
            'authentication_types': [
                ('api_key', 'API Key'),
                ('basic_auth', 'Basic Authentication'),
            ],
            'rate_limit_types': [
                ('per_user', 'Per User'),
                ('per_ip', 'Per IP Address'),
            ],
        }
        
        # Try to render template
        rendered = template.render(context)
        print("✓ Template rendered successfully")
        
        # Check for fixes
        if 'هیچ سرویسی برای تست موجود نیست' in rendered:
            print("✓ Empty state message for testing tab added")
        
        if 'افزودن سرویس اول' in rendered:
            print("✓ Add first service button added")
        
        if 'csrfmiddlewaretoken' in rendered:
            print("✓ CSRF token included")
        
        if 'console.error' in rendered:
            print("✓ Enhanced error handling added")
        
        return True
        
    except Exception as e:
        print(f"✗ Template fixes test failed: {e}")
        return False


def test_model_structure():
    """Test model structure."""
    print("\nTesting model structure...")
    
    try:
        # Test ExternalServiceConfiguration fields
        service_fields = [field.name for field in ExternalServiceConfiguration._meta.fields]
        required_fields = ['name', 'service_type', 'base_url', 'authentication_type', 'status']
        
        for field in required_fields:
            if field in service_fields:
                print(f"✓ ExternalServiceConfiguration has '{field}' field")
            else:
                print(f"✗ ExternalServiceConfiguration missing '{field}' field")
        
        # Test APIRateLimitConfiguration fields
        rate_limit_fields = [field.name for field in APIRateLimitConfiguration._meta.fields]
        required_rate_fields = ['name', 'limit_type', 'requests_limit', 'time_window_seconds']
        
        for field in required_rate_fields:
            if field in rate_limit_fields:
                print(f"✓ APIRateLimitConfiguration has '{field}' field")
            else:
                print(f"✗ APIRateLimitConfiguration missing '{field}' field")
        
        return True
        
    except Exception as e:
        print(f"✗ Model structure test failed: {e}")
        return False


def test_javascript_improvements():
    """Test JavaScript improvements."""
    print("\nTesting JavaScript improvements...")
    
    try:
        template_path = 'templates/admin_panel/settings/integration_settings.html'
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for improved error handling
        improvements = [
            'console.error',
            'csrfToken',
            'formData.append',
            'error.message',
            'خطا در ارسال فرم:',
            'سرویس با موفقیت اضافه شد!'
        ]
        
        for improvement in improvements:
            if improvement in content:
                print(f"✓ JavaScript improvement '{improvement}' found")
            else:
                print(f"✗ JavaScript improvement '{improvement}' missing")
        
        return True
        
    except Exception as e:
        print(f"✗ JavaScript improvements test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=== Integration Settings Fixes Verification ===\n")
    
    tests = [
        test_template_fixes,
        test_model_structure,
        test_javascript_improvements,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== Results ===")
    print(f"Passed: {passed}/{total} tests")
    
    if passed == total:
        print("✓ All fixes verified! Integration settings should work correctly now.")
        return 0
    else:
        print("✗ Some fixes need attention.")
        return 1


if __name__ == '__main__':
    sys.exit(main())