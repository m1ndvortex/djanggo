#!/usr/bin/env python3
"""
Comprehensive test to verify admin consolidation is working correctly.
This script tests:
1. Legacy Django admin is disabled/redirected
2. Unified admin login works perfectly
3. All admin functionality is accessible
4. Tenant admin redirects work properly
"""

import os
import sys
import django
import requests
import time
from urllib.parse import urljoin

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from zargar.tenants.admin_models import SuperAdmin
from zargar.tenants.models import Tenant, Domain

class AdminConsolidationTester:
    def __init__(self):
        self.client = Client()
        self.base_url = 'http://localhost:8000'
        self.results = []
        
    def log_result(self, test_name, success, message):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        self.results.append({
            'test': test_name,
            'success': success,
            'message': message
        })
        
    def test_legacy_admin_redirect(self):
        """Test that legacy admin redirects to unified admin."""
        print("\n🔍 Testing legacy admin redirect...")
        
        try:
            response = self.client.get('/admin/', follow=True)
            
            # Check if we're redirected
            if response.redirect_chain:
                final_url = response.redirect_chain[-1][0]
                if '/super-panel/' in final_url:
                    self.log_result(
                        "Legacy Admin Redirect",
                        True,
                        f"Successfully redirected to {final_url}"
                    )
                else:
                    self.log_result(
                        "Legacy Admin Redirect",
                        False,
                        f"Redirected to wrong URL: {final_url}"
                    )
            else:
                # Check if we get a 404 or other error (also acceptable)
                if response.status_code in [404, 403]:
                    self.log_result(
                        "Legacy Admin Redirect",
                        True,
                        f"Legacy admin properly disabled (status: {response.status_code})"
                    )
                else:
                    self.log_result(
                        "Legacy Admin Redirect",
                        False,
                        f"Legacy admin still accessible (status: {response.status_code})"
                    )
                    
        except Exception as e:
            self.log_result(
                "Legacy Admin Redirect",
                False,
                f"Error testing redirect: {str(e)}"
            )
            
    def test_unified_admin_login_page(self):
        """Test that unified admin login page loads correctly."""
        print("\n🔍 Testing unified admin login page...")
        
        try:
            # Force public schema context
            from django.conf import settings
            original_urlconf = settings.ROOT_URLCONF
            settings.ROOT_URLCONF = settings.PUBLIC_SCHEMA_URLCONF
            
            response = self.client.get('/super-panel/login/')
            
            # Restore original
            settings.ROOT_URLCONF = original_urlconf
            
            if response.status_code == 200:
                content = response.content.decode('utf-8')
                
                # Check for Persian text
                has_persian = 'ورود مدیر سیستم' in content or 'نام کاربری' in content
                
                # Check for login form
                has_form = 'name="username"' in content and 'name="password"' in content
                
                # Check for RTL layout
                has_rtl = 'dir="rtl"' in content or 'direction: rtl' in content
                
                if has_persian and has_form and has_rtl:
                    self.log_result(
                        "Unified Admin Login Page",
                        True,
                        "Login page loads with Persian text, form, and RTL layout"
                    )
                else:
                    missing = []
                    if not has_persian: missing.append("Persian text")
                    if not has_form: missing.append("login form")
                    if not has_rtl: missing.append("RTL layout")
                    
                    self.log_result(
                        "Unified Admin Login Page",
                        False,
                        f"Login page missing: {', '.join(missing)}"
                    )
            else:
                self.log_result(
                    "Unified Admin Login Page",
                    False,
                    f"Login page returned status {response.status_code}"
                )
                
        except Exception as e:
            self.log_result(
                "Unified Admin Login Page",
                False,
                f"Error loading login page: {str(e)}"
            )
            
    def test_unified_admin_authentication(self):
        """Test unified admin authentication works."""
        print("\n🔍 Testing unified admin authentication...")
        
        try:
            # Create or get test SuperAdmin
            superadmin, created = SuperAdmin.objects.get_or_create(
                username='testadmin',
                defaults={
                    'email': 'admin@test.com',
                    'is_superuser': True,
                    'is_active': True,
                    'persian_first_name': 'مدیر',
                    'persian_last_name': 'تست',
                    'phone_number': '09123456789',
                    'can_create_tenants': True,
                    'can_suspend_tenants': True,
                    'can_access_all_data': True
                }
            )
            
            if created:
                superadmin.set_password('testpass123')
                superadmin.save()
                
            # Test login
            login_data = {
                'username': 'testadmin',
                'password': 'testpass123'
            }
            
            response = self.client.post('/super-panel/login/', login_data, follow=True)
            
            if response.status_code == 200:
                # Check if we're redirected to dashboard
                if '/super-panel/' in response.request['PATH_INFO']:
                    # Check if dashboard content is present
                    content = response.content.decode('utf-8')
                    
                    if 'داشبورد یکپارچه مدیریت' in content or 'dashboard' in content.lower():
                        self.log_result(
                            "Unified Admin Authentication",
                            True,
                            "Successfully logged in and redirected to dashboard"
                        )
                        return True
                    else:
                        self.log_result(
                            "Unified Admin Authentication",
                            False,
                            "Logged in but dashboard content not found"
                        )
                else:
                    self.log_result(
                        "Unified Admin Authentication",
                        False,
                        "Login successful but not redirected to dashboard"
                    )
            else:
                self.log_result(
                    "Unified Admin Authentication",
                    False,
                    f"Login failed with status {response.status_code}"
                )
                
        except Exception as e:
            self.log_result(
                "Unified Admin Authentication",
                False,
                f"Error during authentication: {str(e)}"
            )
            
        return False
        
    def test_unified_admin_dashboard_features(self):
        """Test that dashboard features are accessible."""
        print("\n🔍 Testing unified admin dashboard features...")
        
        # First login
        if not self.test_unified_admin_authentication():
            self.log_result(
                "Dashboard Features",
                False,
                "Cannot test features - login failed"
            )
            return
            
        try:
            response = self.client.get('/super-panel/')
            
            if response.status_code == 200:
                content = response.content.decode('utf-8')
                
                # Check for main sections
                expected_sections = [
                    'مدیریت تنانت‌ها',
                    'مدیریت کاربران',
                    'نظارت سیستم',
                    'پشتیبان‌گیری',
                    'مدیریت مالی',
                    'امنیت و حسابرسی'
                ]
                
                found_sections = []
                for section in expected_sections:
                    if section in content:
                        found_sections.append(section)
                        
                if len(found_sections) >= 4:  # At least 4 sections should be present
                    self.log_result(
                        "Dashboard Features",
                        True,
                        f"Found {len(found_sections)}/{len(expected_sections)} expected sections"
                    )
                else:
                    self.log_result(
                        "Dashboard Features",
                        False,
                        f"Only found {len(found_sections)}/{len(expected_sections)} expected sections"
                    )
            else:
                self.log_result(
                    "Dashboard Features",
                    False,
                    f"Dashboard returned status {response.status_code}"
                )
                
        except Exception as e:
            self.log_result(
                "Dashboard Features",
                False,
                f"Error testing dashboard features: {str(e)}"
            )
            
    def test_tenant_admin_redirect(self):
        """Test that tenant admin URLs redirect properly."""
        print("\n🔍 Testing tenant admin redirect...")
        
        try:
            # Create a test tenant if it doesn't exist
            tenant, created = Tenant.objects.get_or_create(
                schema_name='test_tenant',
                defaults={
                    'name': 'Test Tenant',
                    'is_active': True
                }
            )
            
            if created:
                # Create domain for the tenant
                Domain.objects.get_or_create(
                    domain='test.localhost',
                    tenant=tenant,
                    is_primary=True
                )
                
            # Test tenant admin URL (this would be accessed via tenant subdomain)
            # For now, we'll test the redirect function directly
            from zargar.urls_tenants import redirect_to_unified_admin
            from django.http import HttpRequest
            
            request = HttpRequest()
            response = redirect_to_unified_admin(request)
            
            if response.status_code in [301, 302]:
                redirect_url = response.url
                if '/super-panel/' in redirect_url:
                    self.log_result(
                        "Tenant Admin Redirect",
                        True,
                        f"Tenant admin redirects to {redirect_url}"
                    )
                else:
                    self.log_result(
                        "Tenant Admin Redirect",
                        False,
                        f"Tenant admin redirects to wrong URL: {redirect_url}"
                    )
            else:
                self.log_result(
                    "Tenant Admin Redirect",
                    False,
                    f"Tenant admin redirect returned status {response.status_code}"
                )
                
        except Exception as e:
            self.log_result(
                "Tenant Admin Redirect",
                False,
                f"Error testing tenant admin redirect: {str(e)}"
            )
            
    def test_admin_urls_accessibility(self):
        """Test that admin URLs are properly accessible."""
        print("\n🔍 Testing admin URLs accessibility...")
        
        # Login first
        self.test_unified_admin_authentication()
        
        admin_urls = [
            '/super-panel/',
            '/super-panel/login/',
            '/super-panel/tenants/',
            '/super-panel/health/',
            '/super-panel/backup/',
        ]
        
        accessible_urls = 0
        
        for url in admin_urls:
            try:
                response = self.client.get(url)
                if response.status_code in [200, 302]:  # 302 for redirects
                    accessible_urls += 1
                    print(f"  ✅ {url} - Status: {response.status_code}")
                else:
                    print(f"  ❌ {url} - Status: {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ {url} - Error: {str(e)}")
                
        success_rate = accessible_urls / len(admin_urls)
        
        if success_rate >= 0.8:  # At least 80% should be accessible
            self.log_result(
                "Admin URLs Accessibility",
                True,
                f"{accessible_urls}/{len(admin_urls)} URLs accessible ({success_rate:.1%})"
            )
        else:
            self.log_result(
                "Admin URLs Accessibility",
                False,
                f"Only {accessible_urls}/{len(admin_urls)} URLs accessible ({success_rate:.1%})"
            )
            
    def run_all_tests(self):
        """Run all consolidation tests."""
        print("🚀 Starting Admin Consolidation Tests")
        print("=" * 60)
        
        # Run all tests
        self.test_legacy_admin_redirect()
        self.test_unified_admin_login_page()
        self.test_unified_admin_authentication()
        self.test_unified_admin_dashboard_features()
        self.test_tenant_admin_redirect()
        self.test_admin_urls_accessibility()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.results if result['success'])
        total = len(self.results)
        
        for result in self.results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"{status}: {result['test']}")
            
        print(f"\n🎯 OVERALL RESULT: {passed}/{total} tests passed ({passed/total:.1%})")
        
        if passed == total:
            print("🎉 All tests passed! Admin consolidation is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Please review the issues above.")
            return False

def main():
    """Main function to run the tests."""
    tester = AdminConsolidationTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ Admin consolidation verification completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Admin consolidation verification failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()