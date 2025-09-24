#!/usr/bin/env python
"""
Test SuperAdmin authentication and debug login issues.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django.contrib.auth import authenticate
from django.db import connection
from django_tenants.utils import get_public_schema_name
from zargar.tenants.admin_models import SuperAdmin

def test_superadmin_auth():
    """Test SuperAdmin authentication."""
    print("=== SuperAdmin Authentication Test ===")
    
    # Ensure we're in public schema
    print(f"Current schema: {connection.schema_name}")
    if connection.schema_name != get_public_schema_name():
        print("ERROR: Not in public schema!")
        return False
    
    # Check if SuperAdmin users exist
    print("\n--- Checking SuperAdmin users ---")
    superadmins = SuperAdmin.objects.all()
    print(f"Total SuperAdmin users: {superadmins.count()}")
    
    for admin in superadmins:
        print(f"- Username: {admin.username}")
        print(f"  Email: {admin.email}")
        print(f"  Is Active: {admin.is_active}")
        print(f"  Is 2FA Enabled: {admin.is_2fa_enabled}")
        print(f"  Last Login: {admin.last_login}")
    
    if not superadmins.exists():
        print("\nNo SuperAdmin users found. Creating test user...")
        try:
            admin = SuperAdmin.objects.create_user(
                username='admin',
                email='admin@zargar.com',
                password='admin123',
                first_name='System',
                last_name='Administrator'
            )
            print(f"Created SuperAdmin: {admin.username}")
        except Exception as e:
            print(f"Error creating SuperAdmin: {e}")
            return False
    
    # Test authentication
    print("\n--- Testing Authentication ---")
    test_credentials = [
        ('admin', 'admin123'),
        ('admin', 'wrong_password'),
    ]
    
    for username, password in test_credentials:
        print(f"\nTesting: {username} / {password}")
        try:
            user = authenticate(username=username, password=password)
            if user:
                print(f"✅ Authentication successful: {user.username}")
                print(f"   User type: {type(user)}")
                print(f"   Is SuperAdmin: {isinstance(user, SuperAdmin)}")
            else:
                print("❌ Authentication failed")
        except Exception as e:
            print(f"❌ Authentication error: {e}")
    
    return True

def test_login_view():
    """Test the login view directly."""
    print("\n=== Testing Login View ===")
    
    from django.test import Client
    from django.urls import reverse
    
    client = Client()
    
    # Test GET request
    try:
        url = reverse('admin_panel:unified_login')
        print(f"Login URL: {url}")
        
        response = client.get(url)
        print(f"GET response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Login page loads successfully")
        else:
            print(f"❌ Login page failed to load: {response.status_code}")
            print(f"Response content: {response.content[:500]}")
    except Exception as e:
        print(f"❌ Error testing login view: {e}")
    
    # Test POST request
    try:
        post_data = {
            'username': 'admin',
            'password': 'admin123',
        }
        
        response = client.post(url, post_data)
        print(f"POST response status: {response.status_code}")
        
        if response.status_code == 302:
            print(f"✅ Login redirect: {response.url}")
        elif response.status_code == 200:
            print("❌ Login failed - stayed on login page")
            # Check for error messages
            if hasattr(response, 'context') and response.context:
                messages = list(response.context.get('messages', []))
                for message in messages:
                    print(f"   Message: {message}")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing login POST: {e}")

if __name__ == '__main__':
    try:
        test_superadmin_auth()
        test_login_view()
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)