"""
Frontend tests for admin dashboard with dual theme system.
Tests layout, theme switching, and responsiveness.
"""

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from unittest.mock import patch, MagicMock
from zargar.core.views import SuperPanelDashboardView

User = get_user_model()


class AdminDashboardFrontendTest(TestCase):
    """Test admin dashboard frontend functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.factory = RequestFactory()
        
        # Create super admin user
        self.super_admin = User.objects.create_user(
            username='admin',
            email='admin@zargar.com',
            password='admin123',
            is_superuser=True,
            is_staff=True
        )
        
        # Create regular user for permission testing
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@zargar.com',
            password='user123'
        )
    
    def test_dashboard_access_requires_super_admin(self):
        """Test that dashboard requires super admin access."""
        # Test unauthenticated access
        response = self.client.get(reverse('core:super_panel_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Test regular user access
        self.client.login(username='user', password='user123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        self.assertEqual(response.status_code, 403)  # Forbidden
        
        # Test super admin access
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        self.assertEqual(response.status_code, 200)  # Success
    
    def test_dashboard_template_rendering(self):
        """Test that dashboard template renders correctly."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check template used
        self.assertTemplateUsed(response, 'core/super_panel/dashboard.html')
        self.assertTemplateUsed(response, 'base.html')
        
        # Check essential elements are present
        self.assertContains(response, 'داشبورد مدیریت سیستم')
        self.assertContains(response, 'admin-dashboard')
        self.assertContains(response, 'x-data="adminDashboard()"')
    
    def test_dashboard_context_data(self):
        """Test dashboard context data."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check context variables
        self.assertIn('total_tenants', response.context)
        self.assertIn('active_tenants', response.context)
        self.assertIn('total_users', response.context)
        self.assertIn('system_health', response.context)
        self.assertIn('tenant_growth', response.context)
        self.assertIn('user_growth', response.context)
        self.assertIn('recent_logs', response.context)
        
        # Check chart data
        self.assertIn('tenant_growth_data', response.context)
        self.assertIn('system_performance_data', response.context)
        self.assertIn('active_tenants_trend', response.context)
    
    def test_light_theme_rendering(self):
        """Test light theme rendering."""
        self.client.login(username='admin', password='admin123')
        
        # Set light theme in session
        session = self.client.session
        session['theme'] = 'light'
        session.save()
        
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check light theme classes and elements
        self.assertContains(response, 'modern-theme-active')
        self.assertContains(response, 'modern-nav-item')
        self.assertNotContains(response, 'cyber-theme-active')
        
        # Check theme context
        self.assertFalse(response.context['is_dark_mode'])
        self.assertEqual(response.context['current_theme'], 'light')
    
    def test_dark_theme_rendering(self):
        """Test dark theme (cybersecurity) rendering."""
        self.client.login(username='admin', password='admin123')
        
        # Set dark theme in session
        session = self.client.session
        session['theme'] = 'dark'
        session.save()
        
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check dark theme classes and elements
        self.assertContains(response, 'cyber-theme-active')
        self.assertContains(response, 'cyber-nav-item')
        self.assertContains(response, 'cyber-glass-card')
        self.assertContains(response, 'cyber-neon-button')
        
        # Check theme context
        self.assertTrue(response.context['is_dark_mode'])
        self.assertEqual(response.context['current_theme'], 'dark')
    
    def test_navigation_menu_structure(self):
        """Test navigation menu structure and links."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check navigation links
        self.assertContains(response, 'داشبورد')
        self.assertContains(response, 'مدیریت فروشگاه‌ها')
        self.assertContains(response, 'مدیریت کاربران')
        self.assertContains(response, 'وضعیت سیستم')
        self.assertContains(response, 'گزارش‌های امنیتی')
        self.assertContains(response, 'تنظیمات سیستم')
        
        # Check sidebar structure
        self.assertContains(response, 'admin-sidebar')
        self.assertContains(response, 'sidebar-header')
        self.assertContains(response, 'sidebar-menu')
        self.assertContains(response, 'sidebar-footer')
    
    def test_metrics_cards_rendering(self):
        """Test metrics cards rendering."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check metrics cards
        self.assertContains(response, 'کل فروشگاه‌ها')
        self.assertContains(response, 'فروشگاه‌های فعال')
        self.assertContains(response, 'کل کاربران')
        self.assertContains(response, 'وضعیت سیستم')
        
        # Check metrics grid structure
        self.assertContains(response, 'metrics-grid')
        self.assertContains(response, 'metric-card')
        self.assertContains(response, 'metric-icon')
        self.assertContains(response, 'persian-numbers')
    
    def test_charts_integration(self):
        """Test charts integration."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check chart containers
        self.assertContains(response, 'tenantGrowthChart')
        self.assertContains(response, 'systemPerformanceChart')
        self.assertContains(response, 'activeTenantsChart')
        
        # Check Chart.js integration
        self.assertContains(response, 'chart.js')
        self.assertContains(response, 'initCharts()')
        
        # Check chart sections
        self.assertContains(response, 'رشد فروشگاه‌ها')
        self.assertContains(response, 'عملکرد سیستم')
    
    def test_activity_feed_rendering(self):
        """Test activity feed rendering."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check activity feed structure
        self.assertContains(response, 'فعالیت‌های اخیر')
        self.assertContains(response, 'activity-feed')
        self.assertContains(response, 'activity-list')
        
        # Check empty state
        self.assertContains(response, 'هیچ فعالیت اخیری وجود ندارد')
    
    def test_quick_actions_rendering(self):
        """Test quick actions rendering."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check quick actions
        self.assertContains(response, 'عملیات سریع')
        self.assertContains(response, 'ایجاد فروشگاه جدید')
        self.assertContains(response, 'بررسی وضعیت سیستم')
        self.assertContains(response, 'گزارش‌های امنیتی')
        self.assertContains(response, 'تنظیمات سیستم')
        
        # Check quick actions structure
        self.assertContains(response, 'quick-actions')
        self.assertContains(response, 'action-button')
    
    def test_framer_motion_integration(self):
        """Test Framer Motion integration for animations."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check Framer Motion script inclusion
        self.assertContains(response, 'framer-motion')
        
        # Check animation initialization
        self.assertContains(response, 'initAnimations()')
        self.assertContains(response, 'Motion.animate')
    
    def test_alpine_js_integration(self):
        """Test Alpine.js integration."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check Alpine.js directives
        self.assertContains(response, 'x-data="adminDashboard()"')
        self.assertContains(response, 'x-init="initDashboard()"')
        self.assertContains(response, '@click="sidebarOpen')
        self.assertContains(response, 'x-show="sidebarOpen"')
        
        # Check Alpine.js store usage
        self.assertContains(response, '$store.theme.current')
    
    def test_responsive_design_classes(self):
        """Test responsive design classes."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check responsive grid classes
        self.assertContains(response, 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4')
        self.assertContains(response, 'lg:col-span-2')
        self.assertContains(response, 'md:hidden')
        self.assertContains(response, 'md:mr-64')
        
        # Check mobile menu functionality
        self.assertContains(response, 'sidebarOpen = !sidebarOpen')
    
    def test_rtl_layout_support(self):
        """Test RTL layout support."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check RTL classes
        self.assertContains(response, 'space-x-reverse')
        self.assertContains(response, 'text-right')
        self.assertContains(response, 'mr-')  # Margin-right instead of margin-left
        
        # Check Persian font usage
        self.assertContains(response, 'font-vazir')
        self.assertContains(response, 'persian-numbers')
    
    def test_accessibility_features(self):
        """Test accessibility features."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check ARIA labels
        self.assertContains(response, 'aria-label')
        self.assertContains(response, 'title=')
        
        # Check semantic HTML
        self.assertContains(response, '<nav')
        self.assertContains(response, '<main')
        self.assertContains(response, '<header')
        
        # Check focus management
        self.assertContains(response, 'focus-visible')
    
    @patch('zargar.core.views.psutil')
    def test_system_performance_data_with_psutil(self, mock_psutil):
        """Test system performance data collection with psutil."""
        # Mock psutil functions
        mock_psutil.cpu_percent.return_value = 45.5
        mock_psutil.virtual_memory.return_value = MagicMock(percent=67.2)
        mock_psutil.disk_usage.return_value = MagicMock(percent=78.9)
        
        view = SuperPanelDashboardView()
        result = view.get_system_performance_data()
        
        self.assertEqual(result, "46,67,79")
        mock_psutil.cpu_percent.assert_called_once_with(interval=1)
        mock_psutil.virtual_memory.assert_called_once()
        mock_psutil.disk_usage.assert_called_once_with('/')
    
    def test_system_performance_data_fallback(self):
        """Test system performance data fallback when psutil unavailable."""
        view = SuperPanelDashboardView()
        
        # Mock psutil import error
        with patch('zargar.core.views.psutil', side_effect=ImportError):
            result = view.get_system_performance_data()
            self.assertEqual(result, "65,78,45")
    
    def test_theme_switching_functionality(self):
        """Test theme switching functionality."""
        self.client.login(username='admin', password='admin123')
        
        # Test default theme
        response = self.client.get(reverse('core:super_panel_dashboard'))
        self.assertEqual(response.context['current_theme'], 'light')
        
        # Test theme switching via session
        session = self.client.session
        session['theme'] = 'dark'
        session.save()
        
        response = self.client.get(reverse('core:super_panel_dashboard'))
        self.assertEqual(response.context['current_theme'], 'dark')
        self.assertTrue(response.context['is_dark_mode'])
    
    def test_persian_number_formatting(self):
        """Test Persian number formatting."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check Persian number classes
        self.assertContains(response, 'persian-numbers')
        
        # Check JavaScript Persian number conversion
        self.assertContains(response, 'PersianNumbers')
        self.assertContains(response, 'toPersian')
    
    def test_real_time_updates(self):
        """Test real-time updates functionality."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check real-time update functions
        self.assertContains(response, 'updateTime()')
        self.assertContains(response, 'checkSystemStatus()')
        self.assertContains(response, 'setInterval')
        
        # Check system status indicator
        self.assertContains(response, 'system-status-indicator')
        self.assertContains(response, 'animate-pulse')
    
    def test_error_handling(self):
        """Test error handling in dashboard."""
        self.client.login(username='admin', password='admin123')
        
        # Test with database connection error
        with patch('zargar.core.views.connection') as mock_connection:
            mock_connection.cursor.side_effect = Exception("Database error")
            
            response = self.client.get(reverse('core:super_panel_dashboard'))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['system_health']['database'], 'error')


class AdminDashboardJavaScriptTest(TestCase):
    """Test JavaScript functionality in admin dashboard."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.super_admin = User.objects.create_user(
            username='admin',
            email='admin@zargar.com',
            password='admin123',
            is_superuser=True,
            is_staff=True
        )
    
    def test_javascript_functions_included(self):
        """Test that JavaScript functions are included."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check main dashboard function
        self.assertContains(response, 'function adminDashboard()')
        
        # Check initialization functions
        self.assertContains(response, 'initDashboard()')
        self.assertContains(response, 'initCharts()')
        self.assertContains(response, 'initAnimations()')
        
        # Check utility functions
        self.assertContains(response, 'updateTime()')
        self.assertContains(response, 'checkSystemStatus()')
    
    def test_chart_initialization_code(self):
        """Test chart initialization code."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check chart initialization functions
        self.assertContains(response, 'initTenantGrowthChart()')
        self.assertContains(response, 'initSystemPerformanceChart()')
        self.assertContains(response, 'initActiveTenantsChart()')
        
        # Check Chart.js usage
        self.assertContains(response, 'new Chart(')
        self.assertContains(response, 'type: \'line\'')
        self.assertContains(response, 'type: \'doughnut\'')
    
    def test_theme_aware_javascript(self):
        """Test theme-aware JavaScript code."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check theme detection
        self.assertContains(response, 'Alpine.store(\'theme\').current')
        self.assertContains(response, 'isDark')
        
        # Check theme-based styling
        self.assertContains(response, 'isDark ? \'#00D4FF\' : \'#3B82F6\'')
        self.assertContains(response, 'themeChanged')
    
    def test_animation_code(self):
        """Test animation code for cybersecurity theme."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('core:super_panel_dashboard'))
        
        # Check Framer Motion usage
        self.assertContains(response, 'Motion.animate')
        self.assertContains(response, 'opacity: [0, 1]')
        self.assertContains(response, 'y: [20, 0]')
        self.assertContains(response, 'scale: [0.95, 1]')
        
        # Check animation conditions
        self.assertContains(response, 'typeof Motion === \'undefined\'')
        self.assertContains(response, 'current !== \'dark\'')


@pytest.mark.django_db
class AdminDashboardSeleniumTest:
    """Selenium tests for admin dashboard (requires selenium setup)."""
    
    def test_theme_toggle_functionality(self):
        """Test theme toggle functionality with Selenium."""
        # This would require Selenium WebDriver setup
        # Placeholder for actual Selenium tests
        pass
    
    def test_responsive_behavior(self):
        """Test responsive behavior with different screen sizes."""
        # This would test mobile menu, sidebar collapse, etc.
        pass
    
    def test_chart_interactions(self):
        """Test chart interactions and hover effects."""
        # This would test Chart.js interactions
        pass
    
    def test_real_time_updates(self):
        """Test real-time updates functionality."""
        # This would test AJAX updates and live data
        pass