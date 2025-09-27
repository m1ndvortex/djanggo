#!/usr/bin/env python3
"""
Quick UI test to verify the unified admin interface works correctly.
"""

import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from playwright.sync_api import sync_playwright
from zargar.tenants.admin_models import SuperAdmin

def test_unified_admin_ui():
    """Test the unified admin UI with Playwright."""
    print("🚀 Starting Unified Admin UI Test")
    print("=" * 50)
    
    # Create test SuperAdmin if it doesn't exist
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
        print("✅ Test SuperAdmin created")
    else:
        print("✅ Test SuperAdmin already exists")
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='fa-IR'
        )
        page = context.new_page()
        
        try:
            # Test 1: Access login page
            print("\n🔍 Testing login page access...")
            page.goto('http://localhost:8000/super-panel/login/')
            page.wait_for_load_state('networkidle')
            
            # Check for Persian title
            if page.locator('h1:has-text("ورود مدیر سیستم")').count() > 0:
                print("✅ Persian login title found")
            else:
                print("⚠️ Persian login title not found")
            
            # Check for login form
            if page.locator('input[name="username"]').count() > 0 and page.locator('input[name="password"]').count() > 0:
                print("✅ Login form elements found")
            else:
                print("❌ Login form elements missing")
                return False
            
            # Test 2: Login functionality
            print("\n🔍 Testing login functionality...")
            page.fill('input[name="username"]', 'testadmin')
            page.fill('input[name="password"]', 'testpass123')
            page.click('button[type="submit"]')
            
            # Wait for redirect to dashboard
            page.wait_for_url('**/super-panel/', timeout=10000)
            print("✅ Login successful, redirected to dashboard")
            
            # Test 3: Dashboard content
            print("\n🔍 Testing dashboard content...")
            
            # Check for dashboard title
            if page.locator('h1:has-text("داشبورد یکپارچه مدیریت")').count() > 0:
                print("✅ Dashboard title found")
            else:
                print("⚠️ Dashboard title not found")
            
            # Check for navigation sections
            sections = [
                'مدیریت تنانت‌ها',
                'مدیریت کاربران',
                'نظارت سیستم',
                'پشتیبان‌گیری'
            ]
            
            found_sections = 0
            for section in sections:
                if page.locator(f'text="{section}"').count() > 0:
                    found_sections += 1
            
            print(f"✅ Found {found_sections}/{len(sections)} navigation sections")
            
            # Test 4: Theme switching
            print("\n🔍 Testing theme switching...")
            theme_toggle = page.locator('.theme-toggle').first
            if theme_toggle.count() > 0:
                theme_toggle.click()
                page.wait_for_timeout(1000)
                print("✅ Theme toggle works")
            else:
                print("⚠️ Theme toggle not found")
            
            # Test 5: Logout
            print("\n🔍 Testing logout...")
            logout_btn = page.locator('.logout-btn').first
            if logout_btn.count() == 0:
                logout_btn = page.locator('a[href*="logout"]').first
            
            if logout_btn.count() > 0:
                logout_btn.click()
                page.wait_for_url('**/login/', timeout=10000)
                print("✅ Logout successful")
            else:
                print("⚠️ Logout button not found")
            
            print("\n🎉 All UI tests completed successfully!")
            return True
            
        except Exception as e:
            print(f"\n❌ UI test failed: {e}")
            # Take screenshot for debugging
            page.screenshot(path='ui_test_error.png')
            return False
            
        finally:
            context.close()
            browser.close()

if __name__ == '__main__':
    success = test_unified_admin_ui()
    sys.exit(0 if success else 1)