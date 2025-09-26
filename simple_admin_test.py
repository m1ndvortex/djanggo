#!/usr/bin/env python3
"""
Simple admin consolidation test using direct HTTP requests.
"""

import requests
import time
import sys

def test_admin_consolidation():
    """Test admin consolidation with direct HTTP requests."""
    base_url = 'http://localhost:8000'
    results = []
    
    def log_result(test_name, success, message):
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        results.append({'test': test_name, 'success': success, 'message': message})
    
    print("🚀 Starting Simple Admin Consolidation Tests")
    print("=" * 60)
    
    # Test 1: Legacy admin redirect
    print("\n🔍 Testing legacy admin redirect...")
    try:
        response = requests.get(f'{base_url}/admin/', allow_redirects=False, timeout=10)
        if response.status_code in [301, 302]:
            redirect_url = response.headers.get('Location', '')
            if '/super-panel/' in redirect_url:
                log_result("Legacy Admin Redirect", True, f"Redirects to {redirect_url}")
            else:
                log_result("Legacy Admin Redirect", False, f"Redirects to wrong URL: {redirect_url}")
        elif response.status_code == 404:
            log_result("Legacy Admin Redirect", True, "Legacy admin properly disabled (404)")
        else:
            log_result("Legacy Admin Redirect", False, f"Unexpected status: {response.status_code}")
    except Exception as e:
        log_result("Legacy Admin Redirect", False, f"Error: {e}")
    
    # Test 2: Unified admin login page
    print("\n🔍 Testing unified admin login page...")
    try:
        response = requests.get(f'{base_url}/super-panel/login/', timeout=10)
        if response.status_code == 200:
            # Check for Persian content
            has_persian = 'ورود مدیر سیستم' in response.text or 'نام کاربری' in response.text
            # Check for login form
            has_form = 'name="username"' in response.text and 'name="password"' in response.text
            # Check for RTL
            has_rtl = 'dir="rtl"' in response.text or 'direction: rtl' in response.text
            
            if has_persian and has_form:
                log_result("Unified Admin Login Page", True, "Login page loads with Persian content and form")
            else:
                missing = []
                if not has_persian: missing.append("Persian content")
                if not has_form: missing.append("login form")
                log_result("Unified Admin Login Page", False, f"Missing: {', '.join(missing)}")
        else:
            log_result("Unified Admin Login Page", False, f"Status: {response.status_code}")
    except Exception as e:
        log_result("Unified Admin Login Page", False, f"Error: {e}")
    
    # Test 3: Dashboard redirect (should redirect to login)
    print("\n🔍 Testing dashboard access without authentication...")
    try:
        response = requests.get(f'{base_url}/super-panel/', allow_redirects=False, timeout=10)
        if response.status_code in [301, 302]:
            redirect_url = response.headers.get('Location', '')
            if '/login/' in redirect_url:
                log_result("Dashboard Security", True, f"Dashboard redirects to login: {redirect_url}")
            else:
                log_result("Dashboard Security", False, f"Dashboard redirects to: {redirect_url}")
        else:
            log_result("Dashboard Security", False, f"Dashboard accessible without auth (status: {response.status_code})")
    except Exception as e:
        log_result("Dashboard Security", False, f"Error: {e}")
    
    # Test 4: Login functionality
    print("\n🔍 Testing login functionality...")
    try:
        # First get the login page to get CSRF token
        session = requests.Session()
        login_page = session.get(f'{base_url}/super-panel/login/', timeout=10)
        
        if login_page.status_code == 200:
            # Try to extract CSRF token (simplified)
            csrf_token = None
            if 'csrfmiddlewaretoken' in login_page.text:
                # Extract CSRF token (basic extraction)
                import re
                csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', login_page.text)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
            
            # Attempt login with test credentials
            login_data = {
                'username': 'testadmin',
                'password': 'testpass123'
            }
            if csrf_token:
                login_data['csrfmiddlewaretoken'] = csrf_token
            
            login_response = session.post(f'{base_url}/super-panel/login/', data=login_data, allow_redirects=False, timeout=10)
            
            if login_response.status_code in [301, 302]:
                redirect_url = login_response.headers.get('Location', '')
                if '/super-panel/' in redirect_url and '/login/' not in redirect_url:
                    log_result("Login Functionality", True, f"Login successful, redirects to: {redirect_url}")
                else:
                    log_result("Login Functionality", False, f"Login failed or wrong redirect: {redirect_url}")
            else:
                log_result("Login Functionality", False, f"Login returned status: {login_response.status_code}")
        else:
            log_result("Login Functionality", False, "Could not access login page")
    except Exception as e:
        log_result("Login Functionality", False, f"Error: {e}")
    
    # Test 5: Health endpoint
    print("\n🔍 Testing health endpoint...")
    try:
        response = requests.get(f'{base_url}/health/', timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            if health_data.get('schema') == 'public':
                log_result("Health Endpoint", True, f"Health endpoint works, schema: {health_data.get('schema')}")
            else:
                log_result("Health Endpoint", False, f"Wrong schema: {health_data.get('schema')}")
        else:
            log_result("Health Endpoint", False, f"Status: {response.status_code}")
    except Exception as e:
        log_result("Health Endpoint", False, f"Error: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result in results if result['success'])
    total = len(results)
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{status}: {result['test']}")
    
    print(f"\n🎯 OVERALL RESULT: {passed}/{total} tests passed ({passed/total:.1%})")
    
    if passed == total:
        print("🎉 All tests passed! Admin consolidation is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False

if __name__ == '__main__':
    success = test_admin_consolidation()
    sys.exit(0 if success else 1)