#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django.test import override_settings
from django.test import Client
from django.urls import reverse

# Test with minimal middleware to avoid database issues
MINIMAL_MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

@override_settings(MIDDLEWARE=MINIMAL_MIDDLEWARE)
def test_admin_redirect():
    """Test admin redirect with minimal middleware."""
    print("Testing admin redirect with minimal middleware...")
    
    # Test with admin domain
    client = Client(HTTP_HOST='admin.localhost')
    
    try:
        response = client.get('/admin/')
        print(f'Status: {response.status_code}')
        if hasattr(response, 'url'):
            print(f'Redirect URL: {response.url}')
        elif response.status_code == 301:
            print(f'Redirect URL: {response.get("Location", "Unknown")}')
        return response.status_code == 301
    except Exception as e:
        print(f'Error: {e}')
        return False

@override_settings(MIDDLEWARE=MINIMAL_MIDDLEWARE)
def test_url_resolution():
    """Test URL resolution."""
    print("\nTesting URL resolution...")
    
    try:
        # Test if we can resolve admin panel URLs
        dashboard_url = reverse('admin_panel:dashboard')
        print(f'Dashboard URL: {dashboard_url}')
        
        login_url = reverse('admin_panel:unified_login')
        print(f'Login URL: {login_url}')
        
        return True
    except Exception as e:
        print(f'URL resolution error: {e}')
        return False

if __name__ == '__main__':
    print("🔄 Testing Admin Consolidation (Simplified)")
    print("=" * 50)
    
    redirect_ok = test_admin_redirect()
    url_ok = test_url_resolution()
    
    print("\n" + "=" * 50)
    if redirect_ok and url_ok:
        print("✅ Basic admin consolidation tests PASSED")
    else:
        print("❌ Some tests FAILED")
        print(f"Redirect test: {'✅' if redirect_ok else '❌'}")
        print(f"URL resolution test: {'✅' if url_ok else '❌'}")