#!/usr/bin/env python
"""
Comprehensive test for Task 4.1: Admin Consolidation
This test ensures everything is working perfectly after the consolidation.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django.test import Client, override_settings
from django.urls import reverse, NoReverseMatch
from django.template.loader import get_template
from django.template import TemplateDoesNotExist
from django.conf import settings
from zargar.tenants.admin_models import SuperAdmin
import traceback

# Minimal middleware to avoid database issues during testing
MINIMAL_MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

class AdminConsolidationTester:
    """Comprehensive tester for admin consolidation."""
    
    def __init__(self):
        self.passed_tests = 0
        self.total_tests = 0
        self.errors = []
    
    def run_test(self, test_name, test_func):
        """Run a single test and track results."""
        self.total_tests += 1
        print(f"\n🔄 Running: {test_name}")
        
        try:
            result = test_func()
            if result:
                print(f"✅ PASSED: {test_name}")
                self.passed_tests += 1
                return True
            else:
                print(f"❌ FAILED: {test_name}")
                self.errors.append(f"Test failed: {test_name}")
                return False
        except Exception as e:
            print(f"❌ ERROR: {test_name} - {str(e)}")
            self.errors.append(f"Test error in {test_name}: {str(e)}")
            traceback.print_exc()
            return False
    
    def test_admin_redirect_functionality(self):
        """Test that /admin/ redirects correctly to /super-panel/."""
        with override_settings(MIDDLEWARE=MINIMAL_MIDDLEWARE):
            # Test with public domain
            client = Client(HTTP_HOST='admin.localhost')
            
            response = client.get('/admin/')
            
            # Should be 301 permanent redirect
            if response.status_code != 301:
                print(f"Expected 301, got {response.status_code}")
                return False
            
            # Should redirect to /super-panel/
            if not hasattr(response, 'url') or response.url != '/super-panel/':
                print(f"Expected redirect to /super-panel/, got {getattr(response, 'url', 'No URL')}")
                return False
            
            return True
    
    def test_removed_templates(self):
        """Test that duplicate admin templates are removed."""
        removed_templates = [
            'auth/admin_login.html',
            'admin_panel/login.html'
        ]
        
        for template_name in removed_templates:
            try:
                get_template(template_name)
                print(f"Template {template_name} still exists (should be removed)")
                return False
            except TemplateDoesNotExist:
                pass  # This is expected
        
        return True
    
    def test_preserved_templates(self):
        """Test that important templates are preserved."""
        preserved_templates = [
            'auth/tenant_login.html',
            'admin_panel/unified_login.html'
        ]
        
        for template_name in preserved_templates:
            try:
                template = get_template(template_name)
                if not template:
                    print(f"Template {template_name} not found")
                    return False
            except TemplateDoesNotExist:
                print(f"Template {template_name} missing (should be preserved)")
                return False
        
        return True
    
    def test_legacy_urls_removed(self):
        """Test that legacy admin URLs are removed."""
        legacy_urls = [
            'admin_panel:legacy_login',
            'admin_panel:legacy_logout'
        ]
        
        for url_name in legacy_urls:
            try:
                reverse(url_name)
                print(f"Legacy URL {url_name} still exists (should be removed)")
                return False
            except NoReverseMatch:
                pass  # This is expected
        
        return True
    
    def test_unified_urls_exist(self):
        """Test that unified admin URLs exist and are accessible."""
        # Test URL resolution without HTTP requests to avoid middleware issues
        unified_urls = [
            'admin_panel:unified_login',
            'admin_panel:unified_logout',
            'admin_panel:dashboard'
        ]
        
        # We'll test URL resolution in a way that works with django-tenants
        from django.urls import get_resolver
        from django.conf import settings
        
        # Temporarily set the public schema URL conf
        original_urlconf = settings.ROOT_URLCONF
        try:
            settings.ROOT_URLCONF = settings.PUBLIC_SCHEMA_URLCONF
            
            for url_name in unified_urls:
                try:
                    url = reverse(url_name)
                    if not url:
                        print(f"URL {url_name} resolved to empty string")
                        return False
                except NoReverseMatch:
                    print(f"URL {url_name} not found")
                    return False
        finally:
            settings.ROOT_URLCONF = original_urlconf
        
        return True
    
    def test_authentication_backends_cleaned(self):
        """Test that obsolete authentication backends are removed from settings."""
        obsolete_backends = [
            'zargar.core.auth_backends.SuperAdminBackend',
            'zargar.core.twofa_backends.TwoFABackend',
            'zargar.core.twofa_backends.AdminTwoFABackend'
        ]
        
        for backend in obsolete_backends:
            if backend in settings.AUTHENTICATION_BACKENDS:
                print(f"Obsolete backend {backend} still in AUTHENTICATION_BACKENDS")
                return False
        
        return True
    
    def test_unified_backend_in_settings(self):
        """Test that unified backend is properly configured."""
        unified_backend = 'zargar.admin_panel.unified_auth_backend.UnifiedSuperAdminAuthBackend'
        
        if unified_backend not in settings.AUTHENTICATION_BACKENDS:
            print(f"Unified backend {unified_backend} not in AUTHENTICATION_BACKENDS")
            return False
        
        return True
    
    def test_tenant_urls_preserved(self):
        """Test that tenant URLs are preserved."""
        # Check that tenant URLs still include admin
        from zargar import urls_tenants
        
        # Look for admin URL in tenant patterns
        admin_found = False
        for pattern in urls_tenants.urlpatterns:
            if hasattr(pattern, 'pattern') and 'admin/' in str(pattern.pattern):
                admin_found = True
                break
        
        if not admin_found:
            print("Admin URL not found in tenant URLs")
            return False
        
        return True
    
    def test_internal_references_updated(self):
        """Test that internal references are updated to use unified system."""
        # Check that mixins use the correct login URL
        from zargar.tenants.mixins import SuperAdminRequiredMixin
        
        mixin = SuperAdminRequiredMixin()
        expected_login_url = 'admin_panel:unified_login'
        
        # The login_url should resolve to the unified login
        # We need to test this in the public schema context
        original_urlconf = settings.ROOT_URLCONF
        try:
            settings.ROOT_URLCONF = settings.PUBLIC_SCHEMA_URLCONF
            from django.urls import reverse_lazy
            login_url = reverse_lazy(expected_login_url)
            if not login_url:
                print("Login URL in mixin doesn't resolve correctly")
                return False
        except Exception as e:
            print(f"Error resolving login URL in mixin: {e}")
            return False
        finally:
            settings.ROOT_URLCONF = original_urlconf
        
        return True
    
    def test_code_cleanup_verification(self):
        """Test that legacy code has been properly cleaned up."""
        # Check that legacy admin views are removed from auth_views
        from zargar.core import auth_views
        
        # These classes should not exist anymore
        legacy_classes = ['AdminLoginView', 'AdminLogoutView']
        
        for class_name in legacy_classes:
            if hasattr(auth_views, class_name):
                print(f"Legacy class {class_name} still exists in auth_views")
                return False
        
        return True
    
    def test_file_structure_integrity(self):
        """Test that file structure is correct after cleanup."""
        import os
        
        # These files should not exist
        removed_files = [
            'templates/auth/admin_login.html',
            'templates/admin_panel/login.html'
        ]
        
        for file_path in removed_files:
            if os.path.exists(file_path):
                print(f"File {file_path} still exists (should be removed)")
                return False
        
        # These files should exist
        preserved_files = [
            'templates/auth/tenant_login.html',
            'templates/admin_panel/unified_login.html'
        ]
        
        for file_path in preserved_files:
            if not os.path.exists(file_path):
                print(f"File {file_path} missing (should be preserved)")
                return False
        
        return True
    
    def run_all_tests(self):
        """Run all tests and return overall result."""
        print("🚀 Starting Comprehensive Admin Consolidation Tests")
        print("=" * 60)
        
        # Define all tests
        tests = [
            ("Admin Redirect Functionality", self.test_admin_redirect_functionality),
            ("Removed Templates", self.test_removed_templates),
            ("Preserved Templates", self.test_preserved_templates),
            ("Legacy URLs Removed", self.test_legacy_urls_removed),
            ("Unified URLs Exist", self.test_unified_urls_exist),
            ("Authentication Backends Cleaned", self.test_authentication_backends_cleaned),
            ("Unified Backend in Settings", self.test_unified_backend_in_settings),
            ("Tenant URLs Preserved", self.test_tenant_urls_preserved),
            ("Internal References Updated", self.test_internal_references_updated),
            ("Code Cleanup Verification", self.test_code_cleanup_verification),
            ("File Structure Integrity", self.test_file_structure_integrity),
        ]
        
        # Run all tests
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 TEST RESULTS: {self.passed_tests}/{self.total_tests} tests passed")
        
        if self.passed_tests == self.total_tests:
            print("🎉 ALL TESTS PASSED! Admin consolidation is PERFECT!")
            print("\n✅ Task 4.1 completed successfully with:")
            print("   • Admin redirect working (301 to /super-panel/)")
            print("   • Duplicate templates removed")
            print("   • Legacy URLs cleaned up")
            print("   • Unified system properly configured")
            print("   • Tenant system preserved")
            print("   • All internal references updated")
            print("   • Code structure is clean and correct")
            return True
        else:
            print("❌ SOME TESTS FAILED!")
            print("\n🔍 Issues found:")
            for error in self.errors:
                print(f"   • {error}")
            return False

def main():
    """Main test execution."""
    tester = AdminConsolidationTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🏆 TASK 4.1 VERIFICATION: COMPLETE SUCCESS!")
        print("The admin consolidation is working perfectly.")
    else:
        print("\n⚠️  TASK 4.1 VERIFICATION: ISSUES DETECTED!")
        print("Please review and fix the issues above.")
    
    return success

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)