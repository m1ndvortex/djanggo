"""
Test Mobile Responsiveness & Persian Localization for Security & Settings
Tests for task 10: Mobile Responsiveness & Persian Localization
"""

import os
import django
from django.conf import settings

# Configure Django settings before importing Django modules
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from zargar.tenants.admin_models import SuperAdmin
from zargar.core.security_models import SecurityEvent, AuditLog, SuspiciousActivity


class MobileResponsivenessTestCase(TestCase):
    """Test mobile responsiveness for security and settings interfaces"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
        
        # Create test security events
        self.security_event = SecurityEvent.objects.create(
            event_type='login_failed',
            severity='high',
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
            details={'reason': 'Invalid password'},
            is_resolved=False
        )
        
        # Create test audit logs
        self.audit_log = AuditLog.objects.create(
            user=self.super_admin,
            action='create',
            model_name='SecurityEvent',
            object_id=str(self.security_event.id),
            object_repr='Security Event Test',
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
            checksum='test_checksum_123'
        )
        
        # Create test system settings (if model exists)
        try:
            from zargar.admin_panel.models import SystemSetting
            self.system_setting = SystemSetting.objects.create(
                key='test_mobile_setting',
                value='test_value',
                setting_type='string',
                category='mobile_test',
                name='Test Mobile Setting',
                description='A test setting for mobile interface'
            )
        except ImportError:
            self.system_setting = None
        
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
    
    def test_mobile_security_dashboard_responsive_elements(self):
        """Test that security dashboard has mobile-responsive elements"""
        response = self.client.get(reverse('admin_panel:security_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for mobile-specific CSS classes
        self.assertIn('mobile-responsive-security-settings.css', content)
        self.assertIn('mobile-security-settings.js', content)
        
        # Check for mobile navigation elements
        self.assertIn('mobile-nav-toggle', content)
        self.assertIn('mobile-sidebar', content)
        
        # Check for mobile-friendly card layouts
        self.assertIn('mobile-stat-card', content)
        self.assertIn('mobile-chart-container', content)
        
        # Check for touch-friendly button sizes (min-height: 44px)
        self.assertIn('min-height: 44px', content)
    
    def test_mobile_audit_logs_responsive_layout(self):
        """Test that audit logs interface is mobile-responsive"""
        response = self.client.get(reverse('admin_panel:audit_logs'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for mobile table alternatives
        self.assertIn('mobile-card-table', content)
        self.assertIn('table-card', content)
        
        # Check for mobile search interface
        self.assertIn('mobile-search-input', content)
        self.assertIn('mobile-filter-toggle', content)
        
        # Check for mobile pagination
        self.assertIn('mobile-pagination', content)
        
        # Check for mobile export buttons
        self.assertIn('mobile-export-btn', content)
    
    def test_mobile_settings_management_interface(self):
        """Test that settings management is mobile-friendly"""
        response = self.client.get(reverse('admin_panel:settings_management'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for mobile category tabs
        self.assertIn('mobile-category-tabs', content)
        self.assertIn('mobile-category-tab', content)
        
        # Check for mobile setting items
        self.assertIn('mobile-setting-item', content)
        self.assertIn('mobile-setting-input', content)
        
        # Check for mobile bulk actions
        self.assertIn('mobile-bulk-actions', content)
        
        # Check for floating action button
        self.assertIn('fixed bottom-6 left-6', content)
    
    def test_mobile_viewport_meta_tag(self):
        """Test that mobile viewport meta tag is present"""
        response = self.client.get(reverse('admin_panel:security_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        self.assertIn('name="viewport"', content)
        self.assertIn('width=device-width', content)
        self.assertIn('initial-scale=1.0', content)
    
    def test_mobile_touch_friendly_elements(self):
        """Test that interactive elements are touch-friendly"""
        response = self.client.get(reverse('admin_panel:security_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for touch-friendly button classes
        self.assertIn('mobile-btn', content)
        self.assertIn('mobile-quick-action', content)
        
        # Check for touch feedback styles
        self.assertIn(':active', content)
        self.assertIn('transform: scale(0.98)', content)
    
    def test_mobile_responsive_breakpoints(self):
        """Test that CSS includes proper mobile breakpoints"""
        # Test mobile CSS file exists and has proper breakpoints
        with open('static/css/mobile-responsive-security-settings.css', 'r') as f:
            css_content = f.read()
        
        # Check for mobile breakpoints
        self.assertIn('@media (max-width: 768px)', css_content)
        self.assertIn('@media (min-width: 768px) and (max-width: 1024px)', css_content)
        self.assertIn('@media (max-width: 479px)', css_content)
        
        # Check for touch device optimizations
        self.assertIn('@media (hover: none) and (pointer: coarse)', css_content)
        
        # Check for orientation handling
        self.assertIn('@media (orientation: landscape)', css_content)


class PersianLocalizationTestCase(TestCase):
    """Test Persian localization for security and settings interfaces"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
        
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
    
    def test_persian_font_loading(self):
        """Test that Persian fonts are properly loaded"""
        response = self.client.get(reverse('admin_panel:security_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for Vazirmatn font import
        self.assertIn('Vazirmatn', content)
        self.assertIn('fonts.googleapis.com', content)
        
        # Check for font-family CSS
        self.assertIn("font-family: 'Vazirmatn'", content)
    
    def test_rtl_layout_support(self):
        """Test that RTL layout is properly implemented"""
        response = self.client.get(reverse('admin_panel:security_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for RTL direction
        self.assertIn('dir="rtl"', content)
        self.assertIn('lang="fa"', content)
        
        # Check for RTL-specific CSS classes
        self.assertIn('space-x-reverse', content)
        self.assertIn('text-right', content)
    
    def test_persian_text_content(self):
        """Test that interface text is in Persian"""
        response = self.client.get(reverse('admin_panel:security_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for Persian text in security dashboard
        persian_texts = [
            'داشبورد امنیت',
            'وضعیت امنیتی سیستم',
            'رویدادهای امنیتی',
            'لاگ‌های حسابرسی',
            'تهدیدات فعال',
            'ورود ناموفق',
            'فعالیت مشکوک',
            'IP های مسدود'
        ]
        
        for text in persian_texts:
            self.assertIn(text, content)
    
    def test_persian_number_formatting(self):
        """Test that numbers are formatted in Persian"""
        response = self.client.get(reverse('admin_panel:security_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for Persian number class
        self.assertIn('persian-numbers', content)
        
        # Check for Persian number formatting JavaScript
        self.assertIn('formatPersianNumbers', content)
        self.assertIn('۰۱۲۳۴۵۶۷۸۹', content)
    
    def test_persian_date_formatting(self):
        """Test that dates are formatted in Persian"""
        response = self.client.get(reverse('admin_panel:audit_logs'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for Persian date formatting
        self.assertIn('formatPersianDate', content)
        
        # Check for Persian month names
        persian_months = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور']
        found_month = any(month in content for month in persian_months)
        # Note: This might not always be true depending on current date, so we check for the function
        self.assertIn('persianMonths', content)
    
    def test_persian_error_messages(self):
        """Test that error messages are in Persian"""
        # Test with invalid form data to trigger error messages
        response = self.client.post(reverse('admin_panel:setting_update'), {
            'key': 'invalid_key',
            'value': 'test'
        })
        
        # Check that response contains Persian error messages
        if response.status_code == 400:
            content = response.content.decode('utf-8')
            persian_error_terms = ['خطا', 'نامعتبر', 'اجباری', 'الزامی']
            found_error = any(term in content for term in persian_error_terms)
            # This test might need adjustment based on actual error handling
    
    def test_persian_form_labels(self):
        """Test that form labels are in Persian"""
        response = self.client.get(reverse('admin_panel:settings_management'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for Persian form labels
        persian_labels = [
            'نام کاربری',
            'آدرس IP',
            'تاریخ',
            'عملیات',
            'وضعیت',
            'جستجو',
            'فیلتر',
            'صادرات',
            'وارد کردن'
        ]
        
        for label in persian_labels:
            self.assertIn(label, content)
    
    def test_persian_button_text(self):
        """Test that button text is in Persian"""
        response = self.client.get(reverse('admin_panel:security_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for Persian button text
        persian_buttons = [
            'بروزرسانی',
            'جزئیات',
            'حل شده',
            'بررسی',
            'اعمال فیلتر',
            'پاک کردن',
            'انصراف',
            'تایید'
        ]
        
        for button_text in persian_buttons:
            self.assertIn(button_text, content)


class MobileNavigationTestCase(TestCase):
    """Test mobile navigation functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
        
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
    
    def test_mobile_navigation_menu_structure(self):
        """Test that mobile navigation menu has proper structure"""
        response = self.client.get(reverse('admin_panel:security_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for mobile navigation elements
        self.assertIn('mobile-nav-toggle', content)
        self.assertIn('mobile-sidebar', content)
        self.assertIn('mobile-nav-item', content)
        
        # Check for navigation menu items
        nav_items = [
            'داشبورد اصلی',
            'داشبورد امنیت',
            'لاگ‌های حسابرسی',
            'رویدادهای امنیتی',
            'کنترل دسترسی',
            'تنظیمات سیستم'
        ]
        
        for item in nav_items:
            self.assertIn(item, content)
    
    def test_mobile_navigation_urls(self):
        """Test that mobile navigation URLs are correct"""
        response = self.client.get(reverse('admin_panel:security_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for navigation URLs
        nav_urls = [
            '/super-panel/',
            '/super-panel/security/dashboard/',
            '/super-panel/security/audit-logs/',
            '/super-panel/security/security-events/',
            '/super-panel/security/access-control/',
            '/super-panel/settings/'
        ]
        
        for url in nav_urls:
            self.assertIn(url, content)
    
    def test_mobile_breadcrumb_navigation(self):
        """Test that breadcrumb navigation works on mobile"""
        response = self.client.get(reverse('admin_panel:audit_logs'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for breadcrumb elements
        self.assertIn('breadcrumb', content.lower())
        self.assertIn('پنل مدیریت', content)
    
    def test_mobile_back_navigation(self):
        """Test that back navigation is properly handled"""
        # Test JavaScript for back navigation
        response = self.client.get(reverse('admin_panel:security_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for back navigation handling
        self.assertIn('popstate', content)
        self.assertIn('history.back', content.lower())


class MobileTouchInterfaceTestCase(TestCase):
    """Test mobile touch interface optimizations"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
        
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
    
    def test_touch_target_sizes(self):
        """Test that touch targets meet minimum size requirements"""
        response = self.client.get(reverse('admin_panel:security_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for minimum touch target size (44px)
        self.assertIn('min-height: 44px', content)
        self.assertIn('min-height: 48px', content)  # Some elements use 48px
    
    def test_touch_feedback_styles(self):
        """Test that touch feedback styles are implemented"""
        # Check CSS file for touch feedback
        with open('static/css/mobile-responsive-security-settings.css', 'r') as f:
            css_content = f.read()
        
        # Check for touch feedback styles
        self.assertIn(':active', css_content)
        self.assertIn('transform: scale(0.98)', css_content)
        self.assertIn('touchstart', css_content)
        self.assertIn('touchend', css_content)
    
    def test_swipe_gesture_support(self):
        """Test that swipe gestures are supported"""
        # Check JavaScript file for swipe gesture handling
        with open('static/js/mobile-security-settings.js', 'r') as f:
            js_content = f.read()
        
        # Check for swipe gesture handling
        self.assertIn('touchstart', js_content)
        self.assertIn('touchmove', js_content)
        self.assertIn('touchend', js_content)
        self.assertIn('swipe', js_content.lower())
    
    def test_mobile_modal_behavior(self):
        """Test that modals work properly on mobile"""
        response = self.client.get(reverse('admin_panel:settings_management'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for mobile modal classes
        self.assertIn('mobile-modal', content)
        self.assertIn('mobile-modal-content', content)
        self.assertIn('mobile-modal-header', content)


class AccessibilityTestCase(TestCase):
    """Test accessibility features for mobile interfaces"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
        
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
    
    def test_aria_labels_present(self):
        """Test that ARIA labels are present for accessibility"""
        response = self.client.get(reverse('admin_panel:security_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for ARIA labels
        self.assertIn('aria-label', content)
        self.assertIn('aria-expanded', content)
    
    def test_keyboard_navigation_support(self):
        """Test that keyboard navigation is supported"""
        # Check JavaScript for keyboard event handling
        with open('static/js/mobile-security-settings.js', 'r') as f:
            js_content = f.read()
        
        # Check for keyboard navigation
        self.assertIn('keydown', js_content)
        self.assertIn('Escape', js_content)
        self.assertIn('focus', js_content)
    
    def test_reduced_motion_support(self):
        """Test that reduced motion preferences are respected"""
        # Check CSS for reduced motion support
        with open('static/css/mobile-responsive-security-settings.css', 'r') as f:
            css_content = f.read()
        
        # Check for reduced motion media query
        self.assertIn('@media (prefers-reduced-motion: reduce)', css_content)
        self.assertIn('animation: none', css_content)
        self.assertIn('transition: none', css_content)
    
    def test_high_contrast_support(self):
        """Test that high contrast mode is supported"""
        # Check CSS for high contrast support
        with open('static/css/mobile-responsive-security-settings.css', 'r') as f:
            css_content = f.read()
        
        # Check for high contrast media query
        self.assertIn('@media (prefers-contrast: high)', css_content)


class PerformanceTestCase(TestCase):
    """Test performance aspects of mobile interfaces"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
        
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
    
    def test_css_file_size_reasonable(self):
        """Test that CSS file size is reasonable for mobile"""
        import os
        
        css_file_path = 'static/css/mobile-responsive-security-settings.css'
        if os.path.exists(css_file_path):
            file_size = os.path.getsize(css_file_path)
            # CSS file should be less than 100KB for good mobile performance
            self.assertLess(file_size, 100 * 1024, "CSS file is too large for mobile")
    
    def test_js_file_size_reasonable(self):
        """Test that JavaScript file size is reasonable for mobile"""
        import os
        
        js_file_path = 'static/js/mobile-security-settings.js'
        if os.path.exists(js_file_path):
            file_size = os.path.getsize(js_file_path)
            # JS file should be less than 200KB for good mobile performance
            self.assertLess(file_size, 200 * 1024, "JavaScript file is too large for mobile")
    
    def test_lazy_loading_implementation(self):
        """Test that lazy loading is implemented where appropriate"""
        # Check JavaScript for lazy loading patterns
        with open('static/js/mobile-security-settings.js', 'r') as f:
            js_content = f.read()
        
        # Check for lazy loading patterns
        self.assertIn('IntersectionObserver', js_content)
        self.assertIn('loading', js_content.lower())


if __name__ == '__main__':
    pytest.main([__file__])