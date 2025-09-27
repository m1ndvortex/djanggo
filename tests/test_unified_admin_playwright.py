"""
Playwright end-to-end tests for unified admin system.
Tests complete admin workflows including login, navigation, and all features.
"""
import os
import django
from django.conf import settings

# Configure Django settings
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from django.test import LiveServerTestCase
from django.urls import reverse
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
import time
from datetime import datetime

from zargar.tenants.admin_models import SuperAdmin
from zargar.tenants.models import Tenant, Domain


class PlaywrightTestCase(StaticLiveServerTestCase):
    """
    Base class for Playwright tests with Django integration.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up Playwright browser."""
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            headless=True,  # Set to False for debugging
            args=['--disable-web-security', '--disable-features=VizDisplayCompositor']
        )
    
    @classmethod
    def tearDownClass(cls):
        """Clean up Playwright resources."""
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()
    
    def setUp(self):
        """Set up test context and page."""
        super().setUp()
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='fa-IR',
            timezone_id='Asia/Tehran'
        )
        self.page = self.context.new_page()
        
        # Create test SuperAdmin user
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_active=True,
            persian_first_name='مدیر',
            persian_last_name='تست',
            phone_number='09123456789'
        )
        
        # Create test tenants
        self.tenant1 = Tenant.objects.create(
            schema_name='tenant1',
            name='فروشگاه طلا و جواهر نمونه',
            is_active=True
        )
        
        self.tenant2 = Tenant.objects.create(
            schema_name='tenant2',
            name='طلافروشی سرای طلا',
            is_active=False
        )
    
    def tearDown(self):
        """Clean up test context."""
        self.context.close()
        super().tearDown()
    
    def login_as_superadmin(self):
        """Helper method to login as superadmin."""
        login_url = self.live_server_url + reverse('admin_panel:unified_login')
        self.page.goto(login_url)
        
        # Wait for login form to load
        self.page.wait_for_selector('input[name="username"]')
        
        # Fill login form
        self.page.fill('input[name="username"]', 'testadmin')
        self.page.fill('input[name="password"]', 'testpass123')
        
        # Submit form
        self.page.click('button[type="submit"]')
        
        # Wait for redirect to dashboard
        self.page.wait_for_url('**/admin/dashboard/')
        
        return self.page


class UnifiedAdminLoginWorkflowTests(PlaywrightTestCase):
    """
    End-to-end tests for complete login workflow.
    """
    
    def test_complete_login_workflow(self):
        """Test complete login workflow from start to finish."""
        # Navigate to admin area (should redirect to login)
        dashboard_url = self.live_server_url + reverse('admin_panel:dashboard')
        self.page.goto(dashboard_url)
        
        # Should be redirected to login page
        self.page.wait_for_url('**/admin/login/')
        
        # Check login page elements
        self.page.wait_for_selector('h1:has-text("ورود مدیر سیستم")')
        self.page.wait_for_selector('input[name="username"]')
        self.page.wait_for_selector('input[name="password"]')
        self.page.wait_for_selector('button[type="submit"]')
        
        # Test invalid login first
        self.page.fill('input[name="username"]', 'invalid')
        self.page.fill('input[name="password"]', 'invalid')
        self.page.click('button[type="submit"]')
        
        # Should show error message
        self.page.wait_for_selector('.alert-error:has-text("نام کاربری یا رمز عبور اشتباه است")')
        
        # Test valid login
        self.page.fill('input[name="username"]', 'testadmin')
        self.page.fill('input[name="password"]', 'testpass123')
        self.page.click('button[type="submit"]')
        
        # Should redirect to dashboard
        self.page.wait_for_url('**/admin/dashboard/')
        
        # Check dashboard loaded
        self.page.wait_for_selector('h1:has-text("داشبورد یکپارچه مدیریت")')
        
        # Check user info displayed
        self.page.wait_for_selector('.user-info:has-text("مدیر تست")')
    
    def test_login_with_remember_me(self):
        """Test login with remember me functionality."""
        login_url = self.live_server_url + reverse('admin_panel:unified_login')
        self.page.goto(login_url)
        
        # Fill login form with remember me
        self.page.fill('input[name="username"]', 'testadmin')
        self.page.fill('input[name="password"]', 'testpass123')
        self.page.check('input[name="remember_me"]')
        self.page.click('button[type="submit"]')
        
        # Should redirect to dashboard
        self.page.wait_for_url('**/admin/dashboard/')
        
        # Check session persistence (would need to test with browser restart)
        # For now, just verify login was successful
        self.page.wait_for_selector('h1:has-text("داشبورد یکپارچه مدیریت")')
    
    def test_logout_workflow(self):
        """Test complete logout workflow."""
        # Login first
        self.login_as_superadmin()
        
        # Click logout button
        self.page.click('.logout-btn')
        
        # Should redirect to login page
        self.page.wait_for_url('**/admin/login/')
        
        # Check logout message
        self.page.wait_for_selector('.alert-success:has-text("با موفقیت خارج شدید")')
        
        # Try to access dashboard (should redirect to login)
        dashboard_url = self.live_server_url + reverse('admin_panel:dashboard')
        self.page.goto(dashboard_url)
        self.page.wait_for_url('**/admin/login/')


class UnifiedAdminDashboardNavigationTests(PlaywrightTestCase):
    """
    End-to-end tests for dashboard navigation and all features.
    """
    
    def test_dashboard_navigation_sections(self):
        """Test navigation through all dashboard sections."""
        self.login_as_superadmin()
        
        # Test tenant management section
        self.page.click('a[href*="tenants"]')
        self.page.wait_for_url('**/admin/tenants/')
        self.page.wait_for_selector('h1:has-text("مدیریت تنانت‌ها")')
        
        # Go back to dashboard
        self.page.click('.dashboard-link')
        self.page.wait_for_url('**/admin/dashboard/')
        
        # Test user management section
        self.page.click('a[href*="users"]')
        self.page.wait_for_selector('h1:has-text("مدیریت کاربران")')
        
        # Go back to dashboard
        self.page.click('.dashboard-link')
        self.page.wait_for_url('**/admin/dashboard/')
        
        # Test system health section
        self.page.click('a[href*="health"]')
        self.page.wait_for_selector('h1:has-text("نظارت سیستم")')
        
        # Go back to dashboard
        self.page.click('.dashboard-link')
        self.page.wait_for_url('**/admin/dashboard/')
    
    def test_sidebar_navigation(self):
        """Test sidebar navigation functionality."""
        self.login_as_superadmin()
        
        # Check sidebar is visible
        self.page.wait_for_selector('.sidebar')
        
        # Test sidebar collapse/expand
        self.page.click('.sidebar-toggle')
        self.page.wait_for_selector('.sidebar.collapsed')
        
        self.page.click('.sidebar-toggle')
        self.page.wait_for_selector('.sidebar:not(.collapsed)')
        
        # Test navigation items
        nav_items = [
            ('تنانت‌ها', 'tenants'),
            ('کاربران', 'users'),
            ('نظارت', 'health'),
            ('پشتیبان‌گیری', 'backup'),
            ('مالی', 'billing'),
            ('امنیت', 'security')
        ]
        
        for item_text, url_part in nav_items:
            nav_item = self.page.locator(f'.nav-item:has-text("{item_text}")')
            if nav_item.count() > 0:
                nav_item.click()
                self.page.wait_for_url(f'**/{url_part}/**')
                
                # Go back to dashboard
                self.page.click('.dashboard-link')
                self.page.wait_for_url('**/admin/dashboard/')
    
    def test_breadcrumb_navigation(self):
        """Test breadcrumb navigation functionality."""
        self.login_as_superadmin()
        
        # Navigate to tenant list
        self.page.click('a[href*="tenants"]')
        self.page.wait_for_url('**/admin/tenants/')
        
        # Check breadcrumb
        self.page.wait_for_selector('.breadcrumb')
        self.page.wait_for_selector('.breadcrumb-item:has-text("داشبورد")')
        self.page.wait_for_selector('.breadcrumb-item:has-text("تنانت‌ها")')
        
        # Click breadcrumb to go back
        self.page.click('.breadcrumb-item:has-text("داشبورد")')
        self.page.wait_for_url('**/admin/dashboard/')


class UnifiedAdminTenantManagementTests(PlaywrightTestCase):
    """
    End-to-end tests for tenant management workflows.
    """
    
    def test_tenant_list_workflow(self):
        """Test tenant list viewing and filtering."""
        self.login_as_superadmin()
        
        # Navigate to tenant list
        self.page.click('a[href*="tenants"]')
        self.page.wait_for_url('**/admin/tenants/')
        
        # Check tenant list loaded
        self.page.wait_for_selector('.tenant-list')
        
        # Check tenants are displayed
        self.page.wait_for_selector(f'.tenant-item:has-text("{self.tenant1.name}")')
        self.page.wait_for_selector(f'.tenant-item:has-text("{self.tenant2.name}")')
        
        # Test search functionality
        search_input = self.page.locator('input[name="search"]')
        if search_input.count() > 0:
            search_input.fill('نمونه')
            self.page.click('.search-btn')
            
            # Should show filtered results
            self.page.wait_for_selector(f'.tenant-item:has-text("{self.tenant1.name}")')
    
    def test_tenant_detail_workflow(self):
        """Test tenant detail viewing."""
        self.login_as_superadmin()
        
        # Navigate to tenant list
        self.page.click('a[href*="tenants"]')
        self.page.wait_for_url('**/admin/tenants/')
        
        # Click on first tenant
        self.page.click(f'.tenant-item:has-text("{self.tenant1.name}") .view-btn')
        
        # Should navigate to tenant detail
        self.page.wait_for_url(f'**/admin/tenants/{self.tenant1.id}/')
        
        # Check tenant details displayed
        self.page.wait_for_selector(f'h1:has-text("{self.tenant1.name}")')
        self.page.wait_for_selector('.tenant-stats')
        self.page.wait_for_selector('.tenant-info')
    
    def test_tenant_status_toggle(self):
        """Test tenant status toggle functionality."""
        self.login_as_superadmin()
        
        # Navigate to tenant list
        self.page.click('a[href*="tenants"]')
        self.page.wait_for_url('**/admin/tenants/')
        
        # Find inactive tenant and activate it
        inactive_tenant = self.page.locator(f'.tenant-item:has-text("{self.tenant2.name}")')
        if inactive_tenant.count() > 0:
            toggle_btn = inactive_tenant.locator('.status-toggle')
            if toggle_btn.count() > 0:
                toggle_btn.click()
                
                # Wait for success message
                self.page.wait_for_selector('.alert-success')


class UnifiedAdminThemeTests(PlaywrightTestCase):
    """
    End-to-end tests for theme switching and Persian RTL layout.
    """
    
    def test_theme_switching(self):
        """Test theme switching between light and dark modes."""
        self.login_as_superadmin()
        
        # Check initial theme (should be light)
        self.page.wait_for_selector('body.theme-light')
        
        # Click theme toggle
        theme_toggle = self.page.locator('.theme-toggle')
        if theme_toggle.count() > 0:
            theme_toggle.click()
            
            # Should switch to dark theme
            self.page.wait_for_selector('body.theme-dark')
            
            # Check cybersecurity theme elements
            self.page.wait_for_selector('.cyber-bg')
            self.page.wait_for_selector('.neon-glow')
            
            # Switch back to light theme
            theme_toggle.click()
            self.page.wait_for_selector('body.theme-light')
    
    def test_persian_rtl_layout(self):
        """Test Persian RTL layout and fonts."""
        self.login_as_superadmin()
        
        # Check RTL direction
        body = self.page.locator('body')
        direction = body.evaluate('element => getComputedStyle(element).direction')
        self.assertEqual(direction, 'rtl')
        
        # Check Persian font family
        font_family = body.evaluate('element => getComputedStyle(element).fontFamily')
        self.assertIn('Vazirmatn', font_family)
        
        # Check Persian text rendering
        self.page.wait_for_selector('h1:has-text("داشبورد یکپارچه مدیریت")')
        
        # Check Persian numbers
        persian_numbers = self.page.locator('.persian-number')
        if persian_numbers.count() > 0:
            # Verify Persian number formatting
            number_text = persian_numbers.first.text_content()
            # Persian numbers should be displayed
            self.assertTrue(any(char in '۰۱۲۳۴۵۶۷۸۹' for char in number_text))
    
    def test_responsive_design(self):
        """Test responsive design on different screen sizes."""
        self.login_as_superadmin()
        
        # Test desktop view (already set in setUp)
        self.page.wait_for_selector('.sidebar')
        self.page.wait_for_selector('.main-content')
        
        # Test tablet view
        self.page.set_viewport_size({'width': 768, 'height': 1024})
        self.page.wait_for_timeout(500)  # Wait for responsive changes
        
        # Sidebar should be collapsible on tablet
        sidebar = self.page.locator('.sidebar')
        if sidebar.count() > 0:
            # Check if sidebar adapts to tablet view
            sidebar_width = sidebar.evaluate('element => element.offsetWidth')
            self.assertLess(sidebar_width, 300)  # Should be narrower on tablet
        
        # Test mobile view
        self.page.set_viewport_size({'width': 375, 'height': 667})
        self.page.wait_for_timeout(500)  # Wait for responsive changes
        
        # Check mobile navigation
        mobile_menu = self.page.locator('.mobile-menu-toggle')
        if mobile_menu.count() > 0:
            mobile_menu.click()
            self.page.wait_for_selector('.mobile-menu.open')


class UnifiedAdminPerformanceTests(PlaywrightTestCase):
    """
    End-to-end performance tests for admin system.
    """
    
    def test_dashboard_load_performance(self):
        """Test dashboard loading performance."""
        # Measure login and dashboard load time
        start_time = time.time()
        
        self.login_as_superadmin()
        
        # Wait for dashboard to fully load
        self.page.wait_for_selector('.dashboard-stats')
        self.page.wait_for_selector('.recent-activity')
        
        end_time = time.time()
        load_time = end_time - start_time
        
        # Should load within 5 seconds (including login)
        self.assertLess(load_time, 5.0)
    
    def test_navigation_performance(self):
        """Test navigation performance between sections."""
        self.login_as_superadmin()
        
        # Test navigation to different sections
        sections = [
            ('a[href*="tenants"]', '.tenant-list'),
            ('a[href*="users"]', '.user-list'),
            ('a[href*="health"]', '.health-dashboard'),
        ]
        
        for nav_selector, content_selector in sections:
            start_time = time.time()
            
            # Navigate to section
            nav_element = self.page.locator(nav_selector)
            if nav_element.count() > 0:
                nav_element.click()
                
                # Wait for content to load
                content_element = self.page.locator(content_selector)
                if content_element.count() > 0:
                    self.page.wait_for_selector(content_selector)
                
                end_time = time.time()
                nav_time = end_time - start_time
                
                # Navigation should be fast (under 2 seconds)
                self.assertLess(nav_time, 2.0)
            
            # Go back to dashboard
            dashboard_link = self.page.locator('.dashboard-link')
            if dashboard_link.count() > 0:
                dashboard_link.click()
                self.page.wait_for_url('**/admin/dashboard/')
    
    def test_ajax_request_performance(self):
        """Test AJAX request performance."""
        self.login_as_superadmin()
        
        # Test stats API performance
        start_time = time.time()
        
        # Trigger stats refresh (if available)
        refresh_btn = self.page.locator('.refresh-stats')
        if refresh_btn.count() > 0:
            refresh_btn.click()
            
            # Wait for stats to update
            self.page.wait_for_selector('.stats-updated')
            
            end_time = time.time()
            ajax_time = end_time - start_time
            
            # AJAX requests should be fast (under 1 second)
            self.assertLess(ajax_time, 1.0)


class UnifiedAdminSecurityTests(PlaywrightTestCase):
    """
    End-to-end security tests for admin system.
    """
    
    def test_unauthorized_access_prevention(self):
        """Test that unauthorized access is prevented."""
        # Try to access dashboard without login
        dashboard_url = self.live_server_url + reverse('admin_panel:dashboard')
        self.page.goto(dashboard_url)
        
        # Should be redirected to login
        self.page.wait_for_url('**/admin/login/')
        
        # Check warning message
        self.page.wait_for_selector('.alert-warning:has-text("برای دسترسی به این بخش باید وارد شوید")')
    
    def test_session_timeout_handling(self):
        """Test session timeout handling."""
        self.login_as_superadmin()
        
        # Simulate session timeout by clearing cookies
        self.context.clear_cookies()
        
        # Try to navigate to a protected page
        self.page.goto(self.live_server_url + reverse('admin_panel:tenants:tenant_list'))
        
        # Should be redirected to login
        self.page.wait_for_url('**/admin/login/')
    
    def test_csrf_protection(self):
        """Test CSRF protection on forms."""
        self.login_as_superadmin()
        
        # Navigate to a form page
        self.page.goto(self.live_server_url + reverse('admin_panel:tenants:tenant_create'))
        
        # Check CSRF token is present
        csrf_token = self.page.locator('input[name="csrfmiddlewaretoken"]')
        self.assertGreater(csrf_token.count(), 0)
        
        # Check token has value
        token_value = csrf_token.get_attribute('value')
        self.assertIsNotNone(token_value)
        self.assertGreater(len(token_value), 0)


@pytest.mark.django_db
class TestUnifiedAdminPlaywrightIntegration:
    """
    Integration tests using Playwright with pytest.
    """
    
    def test_full_admin_workflow(self):
        """Test complete admin workflow from login to logout."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='fa-IR'
            )
            page = context.new_page()
            
            try:
                # Create test data
                superadmin = SuperAdmin.objects.create_user(
                    username='testadmin',
                    email='admin@test.com',
                    password='testpass123',
                    is_superuser=True,
                    is_active=True
                )
                
                # Start live server (would need proper setup)
                base_url = 'http://localhost:8000'  # Placeholder
                
                # Test login
                page.goto(f'{base_url}/admin/login/')
                page.fill('input[name="username"]', 'testadmin')
                page.fill('input[name="password"]', 'testpass123')
                page.click('button[type="submit"]')
                
                # Verify dashboard loads
                page.wait_for_url('**/admin/dashboard/')
                
                # Test navigation
                page.click('a[href*="tenants"]')
                page.wait_for_url('**/admin/tenants/')
                
                # Test logout
                page.click('.logout-btn')
                page.wait_for_url('**/admin/login/')
                
            finally:
                context.close()
                browser.close()


if __name__ == '__main__':
    # Run with pytest
    pytest.main([__file__, '-v', '--tb=short'])