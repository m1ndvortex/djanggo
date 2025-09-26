"""
Simple test for mobile responsiveness files
Tests for task 10: Mobile Responsiveness & Persian Localization
"""

import os
import pytest


class TestMobileFiles:
    """Test that mobile responsiveness files exist and have proper content"""
    
    def test_mobile_css_file_exists(self):
        """Test that mobile CSS file exists"""
        css_file = 'static/css/mobile-responsive-security-settings.css'
        assert os.path.exists(css_file), f"Mobile CSS file {css_file} does not exist"
    
    def test_mobile_js_file_exists(self):
        """Test that mobile JavaScript file exists"""
        js_file = 'static/js/mobile-security-settings.js'
        assert os.path.exists(js_file), f"Mobile JS file {js_file} does not exist"
    
    def test_mobile_templates_exist(self):
        """Test that mobile templates exist"""
        templates = [
            'templates/admin_panel/mobile/security_dashboard_mobile.html',
            'templates/admin_panel/mobile/audit_logs_mobile.html',
            'templates/admin_panel/mobile/settings_management_mobile.html'
        ]
        
        for template in templates:
            assert os.path.exists(template), f"Mobile template {template} does not exist"
    
    def test_mobile_css_has_responsive_breakpoints(self):
        """Test that CSS file contains mobile breakpoints"""
        css_file = 'static/css/mobile-responsive-security-settings.css'
        
        with open(css_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for mobile breakpoints
        assert '@media (max-width: 768px)' in content
        assert '@media (min-width: 768px) and (max-width: 1024px)' in content
        assert '@media (max-width: 479px)' in content
        
        # Check for touch device optimizations
        assert '@media (hover: none) and (pointer: coarse)' in content
        
        # Check for orientation handling
        assert '@media (orientation: landscape)' in content
    
    def test_mobile_css_has_persian_font_support(self):
        """Test that CSS file includes Persian font support"""
        css_file = 'static/css/mobile-responsive-security-settings.css'
        
        with open(css_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for Persian font
        assert 'Vazirmatn' in content
        assert 'fonts.googleapis.com' in content
        
        # Check for Persian number formatting
        assert 'persian-numbers' in content
        
        # Check for RTL support
        assert 'direction: ltr' in content  # For numbers
        assert 'unicode-bidi: embed' in content
    
    def test_mobile_css_has_touch_friendly_elements(self):
        """Test that CSS includes touch-friendly elements"""
        css_file = 'static/css/mobile-responsive-security-settings.css'
        
        with open(css_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for minimum touch target sizes
        assert 'min-height: 44px' in content
        assert 'min-height: 48px' in content
        
        # Check for touch feedback
        assert ':active' in content
        assert 'transform: scale(0.98)' in content
    
    def test_mobile_js_has_touch_gesture_support(self):
        """Test that JavaScript includes touch gesture support"""
        js_file = 'static/js/mobile-security-settings.js'
        
        with open(js_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for touch event handling
        assert 'touchstart' in content
        assert 'touchmove' in content
        assert 'touchend' in content
        
        # Check for swipe gesture handling
        assert 'swipe' in content.lower()
    
    def test_mobile_js_has_persian_number_formatting(self):
        """Test that JavaScript includes Persian number formatting"""
        js_file = 'static/js/mobile-security-settings.js'
        
        with open(js_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for Persian number formatting
        assert 'formatPersianNumbers' in content
        assert '۰۱۲۳۴۵۶۷۸۹' in content
        
        # Check for Persian date formatting
        assert 'formatPersianDate' in content
        assert 'persianMonths' in content
    
    def test_mobile_js_has_navigation_handling(self):
        """Test that JavaScript includes mobile navigation handling"""
        js_file = 'static/js/mobile-security-settings.js'
        
        with open(js_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for mobile navigation
        assert 'mobile-nav-toggle' in content
        assert 'mobile-sidebar' in content
        assert 'toggleMobileSidebar' in content
        
        # Check for modal handling
        assert 'mobile-modal' in content
        assert 'openMobileModal' in content
    
    def test_mobile_templates_have_persian_content(self):
        """Test that mobile templates contain Persian content"""
        template_file = 'templates/admin_panel/mobile/security_dashboard_mobile.html'
        
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for Persian text
        persian_texts = [
            'داشبورد امنیت',
            'وضعیت امنیتی سیستم',
            'رویدادهای امنیتی',
            'لاگ‌های حسابرسی',
            'تهدیدات فعال',
            'ورود ناموفق',
            'فعالیت مشکوک'
        ]
        
        for text in persian_texts:
            assert text in content, f"Persian text '{text}' not found in template"
    
    def test_mobile_templates_have_rtl_support(self):
        """Test that mobile templates have RTL support"""
        template_file = 'templates/admin_panel/mobile/security_dashboard_mobile.html'
        
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for RTL classes
        assert 'space-x-reverse' in content
        assert 'text-right' in content or 'text-center' in content
        
        # Check for Persian number classes
        assert 'persian-numbers' in content
    
    def test_mobile_templates_have_responsive_classes(self):
        """Test that mobile templates have responsive classes"""
        template_file = 'templates/admin_panel/mobile/security_dashboard_mobile.html'
        
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for mobile-specific classes
        mobile_classes = [
            'mobile-stat-card',
            'mobile-chart-container',
            'mobile-btn',
            'mobile-nav-item',
            'mobile-modal'
        ]
        
        for css_class in mobile_classes:
            assert css_class in content, f"Mobile class '{css_class}' not found in template"
    
    def test_css_file_size_reasonable(self):
        """Test that CSS file size is reasonable for mobile"""
        css_file = 'static/css/mobile-responsive-security-settings.css'
        file_size = os.path.getsize(css_file)
        
        # CSS file should be less than 100KB for good mobile performance
        assert file_size < 100 * 1024, f"CSS file is too large for mobile: {file_size} bytes"
    
    def test_js_file_size_reasonable(self):
        """Test that JavaScript file size is reasonable for mobile"""
        js_file = 'static/js/mobile-security-settings.js'
        file_size = os.path.getsize(js_file)
        
        # JS file should be less than 200KB for good mobile performance
        assert file_size < 200 * 1024, f"JavaScript file is too large for mobile: {file_size} bytes"
    
    def test_accessibility_features_present(self):
        """Test that accessibility features are present"""
        css_file = 'static/css/mobile-responsive-security-settings.css'
        
        with open(css_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for accessibility features
        assert '@media (prefers-reduced-motion: reduce)' in content
        assert '@media (prefers-contrast: high)' in content
        assert 'animation: none' in content
        assert 'transition: none' in content
    
    def test_print_styles_included(self):
        """Test that print styles are included"""
        css_file = 'static/css/mobile-responsive-security-settings.css'
        
        with open(css_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for print styles
        assert '@media print' in content
        assert 'display: none' in content  # For hiding elements in print


if __name__ == '__main__':
    pytest.main([__file__, '-v'])