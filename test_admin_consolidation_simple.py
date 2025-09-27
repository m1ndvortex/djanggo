#!/usr/bin/env python
"""
Simple test script for admin consolidation task 4.1
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django.test import Client
from django.urls import reverse, NoReverseMatch
from django.template.loader import get_template
from django.template import TemplateDoesNotExist

def test_admin_redirect():
    """Test that /admin/ redirects to unified admin system."""
    print("Testing admin redirect...")
    client = Client()
    response = client.get('/admin/')
    
    print(f"Status code: {response.status_code}")
    if hasattr(response, 'url'):
        print(f"Redirect URL: {response.url}")
    
    if response.status_code == 301 and hasattr(response, 'url') and response.url == '/super-panel/':
        print("✅ Admin redirect test PASSED")
        return True
    else:
        print("❌ Admin redirect test FAILED")
        return False

def test_removed_templates():
    """Test that duplicate admin templates are removed."""
    print("\nTesting removed templates...")
    removed_templates = [
        'auth/admin_login.html',
        'admin_panel/login.html'
    ]
    
    all_removed = True
    for template_name in removed_templates:
        try:
            get_template(template_name)
            print(f"❌ Template {template_name} still exists (should be removed)")
            all_removed = False
        except TemplateDoesNotExist:
            print(f"✅ Template {template_name} correctly removed")
    
    return all_removed

def test_preserved_templates():
    """Test that important templates are preserved."""
    print("\nTesting preserved templates...")
    preserved_templates = [
        'auth/tenant_login.html',
        'admin_panel/unified_login.html'
    ]
    
    all_preserved = True
    for template_name in preserved_templates:
        try:
            get_template(template_name)
            print(f"✅ Template {template_name} correctly preserved")
        except TemplateDoesNotExist:
            print(f"❌ Template {template_name} missing (should be preserved)")
            all_preserved = False
    
    return all_preserved

def test_unified_urls():
    """Test that unified admin URLs exist."""
    print("\nTesting unified admin URLs...")
    unified_urls = [
        'admin_panel:unified_login',
        'admin_panel:unified_logout',
        'admin_panel:dashboard'
    ]
    
    all_exist = True
    for url_name in unified_urls:
        try:
            url = reverse(url_name)
            print(f"✅ URL {url_name} exists: {url}")
        except NoReverseMatch:
            print(f"❌ URL {url_name} missing")
            all_exist = False
    
    return all_exist

def test_legacy_urls_removed():
    """Test that legacy admin URLs are removed."""
    print("\nTesting legacy URLs removal...")
    legacy_urls = [
        'admin_panel:legacy_login',
        'admin_panel:legacy_logout'
    ]
    
    all_removed = True
    for url_name in legacy_urls:
        try:
            reverse(url_name)
            print(f"❌ Legacy URL {url_name} still exists (should be removed)")
            all_removed = False
        except NoReverseMatch:
            print(f"✅ Legacy URL {url_name} correctly removed")
    
    return all_removed

def test_unified_login_page():
    """Test that unified login page loads."""
    print("\nTesting unified login page...")
    try:
        client = Client()
        url = reverse('admin_panel:unified_login')
        response = client.get(url)
        
        if response.status_code == 200:
            print("✅ Unified login page loads successfully")
            return True
        else:
            print(f"❌ Unified login page returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error loading unified login page: {e}")
        return False

def main():
    """Run all tests."""
    print("🔄 Running Admin Consolidation Tests (Task 4.1)")
    print("=" * 50)
    
    tests = [
        test_admin_redirect,
        test_removed_templates,
        test_preserved_templates,
        test_unified_urls,
        test_legacy_urls_removed,
        test_unified_login_page
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests PASSED! Admin consolidation task 4.1 completed successfully.")
        return True
    else:
        print("⚠️  Some tests FAILED. Please review the issues above.")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)