"""
Frontend tests for RTL layout and responsive design
Tests the RTL-first interface with Tailwind CSS and Flowbite integration
"""

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from zargar.tenants.models import Tenant, Domain
from zargar.core.models import User

User = get_user_model()


class RTLLayoutTestCase(TestCase):
    """Test RTL layout functionality and responsive design"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test tenant
        self.tenant = Tenant.objects.create(
            name="Test Jewelry Shop",
            schema_name="test_shop",
            is_active=True
        )
        
        # Create domain for tenant
        self.domain = Domain.objects.create(
            domain="testshop.zargar.com",
            tenant=self.tenant,
            is_primary=True
        )
        
        # Create test user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            tenant=self.tenant
        )
    
    def test_base_template_rtl_attributes(self):
        """Test that base template has proper RTL attributes"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check HTML direction attribute
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, 'lang="fa"')
        
        # Check Persian font loading
        self.assertContains(response, 'Vazirmatn')
        self.assertContains(response, 'Yekan Bakh')
        
        # Check Tailwind CSS loading
        self.assertContains(response, 'tailwindcss.com')
        
        # Check Flowbite integration
        self.assertContains(response, 'flowbite')
    
    def test_theme_toggle_functionality(self):
        """Test theme toggle button and functionality"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check theme toggle button exists
        self.assertContains(response, 'data-theme-toggle')
        
        # Check theme icons
        self.assertContains(response, 'theme-light-icon')
        self.assertContains(response, 'theme-dark-icon')
        
        # Check theme classes
        self.assertContains(response, 'light')
        self.assertContains(response, 'dark')
    
    def test_persian_font_integration(self):
        """Test Persian font integration and loading"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check font preloading
        self.assertContains(response, 'rel="preconnect"')
        self.assertContains(response, 'fonts.googleapis.com')
        
        # Check font family definitions
        self.assertContains(response, 'font-vazir')
        self.assertContains(response, 'font-yekan')
        
        # Check Persian text classes
        self.assertContains(response, 'persian-text')
        self.assertContains(response, 'persian-numbers')
    
    def test_cybersecurity_theme_elements(self):
        """Test cybersecurity theme elements and styling"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check cybersecurity color variables
        self.assertContains(response, 'cyber-bg-primary')
        self.assertContains(response, 'cyber-neon-primary')
        self.assertContains(response, '#0B0E1A')
        self.assertContains(response, '#00D4FF')
        
        # Check glassmorphism classes
        self.assertContains(response, 'cyber-glass-card')
        self.assertContains(response, 'backdrop-blur')
        
        # Check neon effects
        self.assertContains(response, 'cyber-neon-button')
        self.assertContains(response, 'neon-pulse')
    
    def test_responsive_design_classes(self):
        """Test responsive design classes and breakpoints"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check responsive classes
        self.assertContains(response, 'sm:')
        self.assertContains(response, 'md:')
        self.assertContains(response, 'lg:')
        self.assertContains(response, 'xl:')
        
        # Check mobile-specific classes
        self.assertContains(response, 'mobile')
        
        # Check RTL responsive utilities
        self.assertContains(response, 'rtl-')
    
    def test_flowbite_component_integration(self):
        """Test Flowbite component integration with RTL"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check Flowbite CSS and JS loading
        self.assertContains(response, 'flowbite.min.css')
        self.assertContains(response, 'flowbite.min.js')
        
        # Check data attributes for Flowbite components
        self.assertContains(response, 'data-dropdown')
        self.assertContains(response, 'data-modal')
        
        # Check RTL enhancements
        self.assertContains(response, 'rtl-dropdown')
        self.assertContains(response, 'rtl-modal')
    
    def test_persian_number_formatting(self):
        """Test Persian number formatting functionality"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check Persian number utilities
        self.assertContains(response, 'PersianNumbers')
        self.assertContains(response, 'toPersian')
        self.assertContains(response, 'formatCurrency')
        
        # Check Persian digit classes
        self.assertContains(response, 'persian-numbers')
        self.assertContains(response, 'persian-currency')
    
    def test_rtl_form_elements(self):
        """Test RTL form elements and validation"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check Persian input classes
        self.assertContains(response, 'persian-input')
        self.assertContains(response, 'text-align: right')
        self.assertContains(response, 'direction: rtl')
        
        # Check form validation
        self.assertContains(response, 'persian-validation')
        self.assertContains(response, 'PersianFormValidator')
    
    def test_animation_and_transitions(self):
        """Test animations and transitions for both themes"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check animation classes
        self.assertContains(response, 'animate-')
        self.assertContains(response, 'transition-')
        
        # Check cybersecurity animations
        self.assertContains(response, 'neon-pulse')
        self.assertContains(response, 'cyber-glow')
        
        # Check Framer Motion integration
        self.assertContains(response, 'framer-motion')
    
    def test_accessibility_features(self):
        """Test accessibility features for RTL layout"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check ARIA labels
        self.assertContains(response, 'aria-label')
        self.assertContains(response, 'تغییر تم')  # Theme toggle label in Persian
        
        # Check focus styles
        self.assertContains(response, 'focus-visible')
        self.assertContains(response, 'focus:')
        
        # Check semantic HTML
        self.assertContains(response, 'role=')
        self.assertContains(response, 'tabindex')
    
    def test_print_styles(self):
        """Test print-specific styles"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check print media queries
        self.assertContains(response, '@media print')
        
        # Check print optimizations
        self.assertContains(response, 'display: none !important')
    
    def test_high_contrast_support(self):
        """Test high contrast mode support"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check high contrast media query
        self.assertContains(response, 'prefers-contrast: high')
        
        # Check enhanced contrast variables
        self.assertContains(response, 'rgba(255, 255, 255, 0.3)')
    
    def test_reduced_motion_support(self):
        """Test reduced motion accessibility support"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check reduced motion media query
        self.assertContains(response, 'prefers-reduced-motion: reduce')
        
        # Check animation disabling
        self.assertContains(response, 'animation: none')


class ResponsiveDesignTestCase(TestCase):
    """Test responsive design functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test tenant
        self.tenant = Tenant.objects.create(
            name="Test Jewelry Shop",
            schema_name="test_shop",
            is_active=True
        )
        
        # Create domain for tenant
        self.domain = Domain.objects.create(
            domain="testshop.zargar.com",
            tenant=self.tenant,
            is_primary=True
        )
    
    def test_mobile_responsive_classes(self):
        """Test mobile responsive classes"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check mobile breakpoint classes
        self.assertContains(response, 'sm:')
        self.assertContains(response, 'max-width: 768px')
        self.assertContains(response, 'max-width: 480px')
        
        # Check mobile-specific adjustments
        self.assertContains(response, 'mx-2')
        self.assertContains(response, 'p-4')
        self.assertContains(response, 'text-sm')
    
    def test_tablet_responsive_classes(self):
        """Test tablet responsive classes"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check tablet breakpoint classes
        self.assertContains(response, 'md:')
        self.assertContains(response, 'lg:')
        
        # Check tablet-specific layouts
        self.assertContains(response, 'grid-cols-')
        self.assertContains(response, 'flex-col')
    
    def test_desktop_responsive_classes(self):
        """Test desktop responsive classes"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check desktop breakpoint classes
        self.assertContains(response, 'xl:')
        self.assertContains(response, '2xl:')
        
        # Check desktop-specific layouts
        self.assertContains(response, 'container')
        self.assertContains(response, 'max-w-')
    
    def test_component_responsiveness(self):
        """Test component responsiveness"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check responsive component classes
        self.assertContains(response, 'persian-calendar')
        self.assertContains(response, 'min-width: 280px')
        self.assertContains(response, 'min-width: 260px')
        self.assertContains(response, 'min-width: 240px')
        
        # Check responsive search results
        self.assertContains(response, 'search-results')
        self.assertContains(response, 'min-width: 300px')


class ComponentIntegrationTestCase(TestCase):
    """Test component integration with RTL and themes"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test tenant
        self.tenant = Tenant.objects.create(
            name="Test Jewelry Shop",
            schema_name="test_shop",
            is_active=True
        )
        
        # Create domain for tenant
        self.domain = Domain.objects.create(
            domain="testshop.zargar.com",
            tenant=self.tenant,
            is_primary=True
        )
    
    def test_persian_date_picker_integration(self):
        """Test Persian date picker component integration"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check date picker attributes
        self.assertContains(response, 'data-persian-datepicker')
        self.assertContains(response, 'PersianDatePickerComponent')
        
        # Check Persian month names
        self.assertContains(response, 'فروردین')
        self.assertContains(response, 'اردیبهشت')
        
        # Check Persian day names
        self.assertContains(response, 'شنبه')
        self.assertContains(response, 'یکشنبه')
    
    def test_persian_number_input_integration(self):
        """Test Persian number input component integration"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check number input attributes
        self.assertContains(response, 'data-persian-number-input')
        self.assertContains(response, 'PersianNumberInputComponent')
        
        # Check currency formatting
        self.assertContains(response, 'data-currency')
        self.assertContains(response, 'formatCurrency')
    
    def test_gold_calculator_integration(self):
        """Test gold calculator component integration"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check calculator attributes
        self.assertContains(response, 'data-gold-calculator')
        self.assertContains(response, 'GoldCalculatorComponent')
        
        # Check Persian labels
        self.assertContains(response, 'محاسبه‌گر طلا')
        self.assertContains(response, 'وزن (گرم)')
        self.assertContains(response, 'عیار')
    
    def test_persian_search_integration(self):
        """Test Persian search component integration"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check search attributes
        self.assertContains(response, 'data-persian-search')
        self.assertContains(response, 'PersianSearchComponent')
        
        # Check search placeholder
        self.assertContains(response, 'جستجو')
    
    def test_notification_system_integration(self):
        """Test notification system integration"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check notification system
        self.assertContains(response, 'PersianNotificationSystem')
        self.assertContains(response, 'persian-notifications')
        
        # Check notification types
        self.assertContains(response, 'success')
        self.assertContains(response, 'error')
        self.assertContains(response, 'warning')


class ThemeIntegrationTestCase(TestCase):
    """Test theme integration with components"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test tenant
        self.tenant = Tenant.objects.create(
            name="Test Jewelry Shop",
            schema_name="test_shop",
            is_active=True
        )
        
        # Create domain for tenant
        self.domain = Domain.objects.create(
            domain="testshop.zargar.com",
            tenant=self.tenant,
            is_primary=True
        )
    
    def test_light_theme_integration(self):
        """Test light theme integration"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check light theme classes
        self.assertContains(response, 'light-card')
        self.assertContains(response, 'light-button')
        self.assertContains(response, 'light-dropdown')
        self.assertContains(response, 'light-modal')
        
        # Check light theme colors
        self.assertContains(response, 'bg-white')
        self.assertContains(response, 'text-gray-900')
        self.assertContains(response, 'border-gray-200')
    
    def test_dark_theme_integration(self):
        """Test dark theme (cybersecurity) integration"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check dark theme classes
        self.assertContains(response, 'cyber-glass-card')
        self.assertContains(response, 'cyber-neon-button')
        self.assertContains(response, 'cyber-dropdown')
        self.assertContains(response, 'cyber-modal')
        
        # Check cybersecurity colors
        self.assertContains(response, 'cyber-bg-primary')
        self.assertContains(response, 'cyber-neon-primary')
        self.assertContains(response, 'cyber-text-primary')
    
    def test_theme_switching_functionality(self):
        """Test theme switching functionality"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check theme manager
        self.assertContains(response, 'ThemeManager')
        self.assertContains(response, 'toggleTheme')
        self.assertContains(response, 'applyTheme')
        
        # Check theme persistence
        self.assertContains(response, 'localStorage')
        self.assertContains(response, 'zargar_theme')
    
    def test_component_theme_updates(self):
        """Test component theme updates"""
        response = self.client.get('/', HTTP_HOST='testshop.zargar.com')
        
        # Check theme update methods
        self.assertContains(response, 'updateComponentThemes')
        self.assertContains(response, 'themeChanged')
        
        # Check component theme classes
        self.assertContains(response, 'updateDropdownThemes')
        self.assertContains(response, 'updateModalThemes')


if __name__ == '__main__':
    pytest.main([__file__])