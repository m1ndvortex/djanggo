#!/usr/bin/env python
"""
Simple test script to verify django-hijack integration is working correctly.
"""
import os
import django
from django.conf import settings

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
django.setup()

from django.test import Client
from django.urls import reverse
from zargar.tenants.admin_models import SuperAdmin
from zargar.tenants.models import Tenant, Domain
from zargar.core.models import User
from django_tenants.utils import schema_context


def test_hijack_integration():
    """Test basic hijack integration functionality."""
    print("🔧 Testing Django-Hijack Integration...")
    
    try:
        # Test 1: Check if hijack URLs are accessible
        print("✅ 1. Checking URL configuration...")
        
        # Test admin panel URLs (direct paths)
        admin_urls = [
            '/super-panel/impersonation/',
            '/super-panel/impersonation/audit/',
            '/super-panel/impersonation/stats/',
        ]
        
        for url_path in admin_urls:
            try:
                from django.test import Client
                client = Client()
                # Just test that the URL pattern exists (will get 302 redirect due to auth)
                response = client.get(url_path)
                if response.status_code in [200, 302, 403]:  # Valid responses
                    print(f"   ✓ {url_path}: Status {response.status_code}")
                else:
                    print(f"   ✗ {url_path}: Status {response.status_code}")
                    return False
            except Exception as e:
                print(f"   ✗ {url_path}: {e}")
                return False
        
        # Test 2: Check hijack settings
        print("✅ 2. Checking hijack settings...")
        
        hijack_settings = [
            'HIJACK_LOGIN_REDIRECT_URL',
            'HIJACK_LOGOUT_REDIRECT_URL',
            'HIJACK_PERMISSION_CHECK',
            'HIJACK_AUTHORIZATION_CHECK',
        ]
        
        for setting in hijack_settings:
            if hasattr(settings, setting):
                print(f"   ✓ {setting}: {getattr(settings, setting)}")
            else:
                print(f"   ✗ {setting}: Not configured")
                return False
        
        # Test 3: Check if hijack is in INSTALLED_APPS
        print("✅ 3. Checking hijack installation...")
        
        if 'hijack' in settings.INSTALLED_APPS:
            print("   ✓ django-hijack is installed")
        else:
            print("   ✗ django-hijack is not in INSTALLED_APPS")
            return False
        
        if 'hijack.contrib.admin' in settings.INSTALLED_APPS:
            print("   ✓ hijack.contrib.admin is installed")
        else:
            print("   ✗ hijack.contrib.admin is not in INSTALLED_APPS")
            return False
        
        # Test 4: Check middleware
        print("✅ 4. Checking middleware configuration...")
        
        hijack_middleware = [
            'hijack.middleware.HijackUserMiddleware',
            'zargar.admin_panel.middleware.ImpersonationAuditMiddleware',
        ]
        
        for middleware in hijack_middleware:
            if middleware in settings.MIDDLEWARE:
                print(f"   ✓ {middleware}")
            else:
                print(f"   ✗ {middleware}: Not in MIDDLEWARE")
                return False
        
        # Test 5: Check template files exist
        print("✅ 5. Checking template files...")
        
        template_files = [
            'templates/admin_panel/user_impersonation.html',
            'templates/admin_panel/impersonation_audit.html',
            'templates/admin_panel/impersonation_session_detail.html',
            'templates/admin_panel/impersonation_stats.html',
            'templates/admin/hijack/impersonation_banner.html',
        ]
        
        for template_file in template_files:
            if os.path.exists(template_file):
                print(f"   ✓ {template_file}")
            else:
                print(f"   ✗ {template_file}: File not found")
                return False
        
        # Test 6: Check models
        print("✅ 6. Checking models...")
        
        try:
            from zargar.admin_panel.models import ImpersonationSession
            print("   ✓ ImpersonationSession model imported successfully")
            
            # Check model fields
            required_fields = [
                'session_id', 'admin_user_id', 'admin_username',
                'target_user_id', 'target_username', 'tenant_schema',
                'tenant_domain', 'start_time', 'status', 'ip_address'
            ]
            
            for field in required_fields:
                if hasattr(ImpersonationSession, field):
                    print(f"   ✓ Field: {field}")
                else:
                    print(f"   ✗ Field: {field} - Missing")
                    return False
                    
        except ImportError as e:
            print(f"   ✗ ImpersonationSession model: {e}")
            return False
        
        # Test 7: Check permissions module
        print("✅ 7. Checking permissions module...")
        
        try:
            from zargar.admin_panel.hijack_permissions import (
                is_super_admin, authorize_hijack, check_hijack_permissions
            )
            print("   ✓ Hijack permissions module imported successfully")
            
        except ImportError as e:
            print(f"   ✗ Hijack permissions module: {e}")
            return False
        
        print("\n🎉 All tests passed! Django-Hijack integration is properly configured.")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False


def test_frontend_templates():
    """Test frontend template functionality."""
    print("\n🎨 Testing Frontend Templates...")
    
    try:
        from django.template.loader import get_template
        from django.template import Context
        
        # Test template loading
        templates_to_test = [
            'admin_panel/user_impersonation.html',
            'admin_panel/impersonation_audit.html',
            'admin_panel/impersonation_session_detail.html',
            'admin_panel/impersonation_stats.html',
        ]
        
        for template_name in templates_to_test:
            try:
                template = get_template(template_name)
                print(f"   ✓ Template loaded: {template_name}")
            except Exception as e:
                print(f"   ✗ Template error: {template_name} - {e}")
                return False
        
        print("\n🎉 All frontend templates loaded successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Frontend template test failed: {e}")
        return False


if __name__ == '__main__':
    print("🚀 Starting Django-Hijack Integration Tests...\n")
    
    # Run tests
    integration_test = test_hijack_integration()
    frontend_test = test_frontend_templates()
    
    if integration_test and frontend_test:
        print("\n✅ ALL TESTS PASSED! Django-Hijack frontend implementation is complete and working correctly.")
        exit(0)
    else:
        print("\n❌ SOME TESTS FAILED! Please check the implementation.")
        exit(1)