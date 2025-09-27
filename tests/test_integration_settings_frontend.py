"""
Test integration settings frontend functionality.
"""
import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from zargar.tenants.models import SuperAdmin
from zargar.admin_panel.models import (
    ExternalServiceConfiguration, 
    APIRateLimitConfiguration,
    IntegrationHealthCheck
)


class IntegrationSettingsFrontendTest(TestCase):
    """Test integration settings frontend views and functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create a super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        
        # Create test external service
        self.test_service = ExternalServiceConfiguration.objects.create(
            name='Test Gold Price API',
            service_type='gold_price_api',
            base_url='https://api.goldprice.test',
            authentication_type='api_key',
            api_key='test-api-key-123',
            status='active',
            is_enabled=True,
            created_by_id=self.super_admin.id,
            created_by_username=self.super_admin.username
        )
        
        # Create test rate limit configuration
        self.test_rate_limit = APIRateLimitConfiguration.objects.create(
            name='Test Rate Limit',
            limit_type='per_user',
            requests_limit=100,
            time_window_seconds=3600,
            is_active=True,
            created_by_id=self.super_admin.id,
            created_by_username=self.super_admin.username
        )
        
        # Create test health check
        self.test_health_check = IntegrationHealthCheck.objects.create(
            service=self.test_service,
            check_type='connectivity',
            status='healthy',
            success=True,
            response_time_ms=150.5
        )
    
    def test_integration_settings_page_loads(self):
        """Test that integration settings page loads successfully."""
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
        
        # Access integration settings page
        url = reverse('admin_panel:integration_settings')
        response = self.client.get(url)
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تنظیمات یکپارچه‌سازی')
        self.assertContains(response, 'مدیریت سرویس‌های خارجی و API')
    
    def test_integration_settings_displays_services(self):
        """Test that integration settings page displays external services."""
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
        
        # Access integration settings page
        url = reverse('admin_panel:integration_settings')
        response = self.client.get(url)
        
        # Check that test service is displayed
        self.assertContains(response, 'Test Gold Price API')
        self.assertContains(response, 'https://api.goldprice.test')
        self.assertContains(response, 'API Key')
    
    def test_integration_settings_displays_rate_limits(self):
        """Test that integration settings page displays rate limits."""
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
        
        # Access integration settings page
        url = reverse('admin_panel:integration_settings')
        response = self.client.get(url)
        
        # Check that test rate limit is displayed
        self.assertContains(response, 'Test Rate Limit')
        self.assertContains(response, 'Per User Limit')
        self.assertContains(response, '100 درخواست')
    
    def test_integration_settings_displays_health_status(self):
        """Test that integration settings page displays health monitoring."""
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
        
        # Access integration settings page
        url = reverse('admin_panel:integration_settings')
        response = self.client.get(url)
        
        # Check that health status is displayed
        self.assertContains(response, 'نظارت سلامت')
        self.assertContains(response, 'status-healthy')
    
    def test_integration_settings_context_data(self):
        """Test that integration settings view provides correct context data."""
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
        
        # Access integration settings page
        url = reverse('admin_panel:integration_settings')
        response = self.client.get(url)
        
        # Check context data
        self.assertIn('services', response.context)
        self.assertIn('rate_limits', response.context)
        self.assertIn('health_statuses', response.context)
        self.assertIn('overall_health', response.context)
        self.assertIn('total_services', response.context)
        self.assertIn('healthy_services', response.context)
        
        # Check values
        self.assertEqual(response.context['total_services'], 1)
        self.assertEqual(response.context['healthy_services'], 1)
        self.assertEqual(response.context['overall_health'], 'healthy')
    
    def test_integration_settings_requires_authentication(self):
        """Test that integration settings page requires authentication."""
        # Access without login
        url = reverse('admin_panel:integration_settings')
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_integration_settings_theme_support(self):
        """Test that integration settings page supports dual themes."""
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
        
        # Access integration settings page
        url = reverse('admin_panel:integration_settings')
        response = self.client.get(url)
        
        # Check for theme-aware CSS classes
        self.assertContains(response, 'dark:bg-cyber-bg-primary')
        self.assertContains(response, 'dark:text-cyber-text-primary')
        self.assertContains(response, 'dark:border-cyber-neon-primary')
        self.assertContains(response, 'glassmorphism')
    
    def test_integration_settings_persian_rtl_support(self):
        """Test that integration settings page supports Persian RTL layout."""
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
        
        # Access integration settings page
        url = reverse('admin_panel:integration_settings')
        response = self.client.get(url)
        
        # Check for RTL support
        self.assertContains(response, 'space-x-reverse')
        self.assertContains(response, 'persian-numbers')
        self.assertContains(response, 'تنظیمات یکپارچه‌سازی')
    
    def test_integration_settings_navigation_breadcrumb(self):
        """Test that integration settings page has proper navigation breadcrumb."""
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
        
        # Access integration settings page
        url = reverse('admin_panel:integration_settings')
        response = self.client.get(url)
        
        # Check for navigation elements
        self.assertContains(response, 'تنظیمات یکپارچه‌سازی')
        self.assertContains(response, 'مدیریت سرویس‌های خارجی و API')
    
    def test_integration_settings_mobile_responsive(self):
        """Test that integration settings page is mobile responsive."""
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
        
        # Access integration settings page
        url = reverse('admin_panel:integration_settings')
        response = self.client.get(url)
        
        # Check for responsive CSS classes
        self.assertContains(response, 'grid-cols-1')
        self.assertContains(response, 'md:grid-cols-2')
        self.assertContains(response, 'lg:grid-cols-3')
        self.assertContains(response, 'xl:grid-cols-3')
    
    def test_integration_settings_tabs_functionality(self):
        """Test that integration settings page has working tabs."""
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
        
        # Access integration settings page
        url = reverse('admin_panel:integration_settings')
        response = self.client.get(url)
        
        # Check for tab elements
        self.assertContains(response, 'سرویس‌های خارجی')
        self.assertContains(response, 'محدودیت‌های نرخ')
        self.assertContains(response, 'نظارت سلامت')
        self.assertContains(response, 'تست اتصال')
        
        # Check for Alpine.js tab functionality
        self.assertContains(response, "activeTab = 'services'")
        self.assertContains(response, "activeTab = 'rate_limits'")
        self.assertContains(response, "activeTab = 'health_monitoring'")
        self.assertContains(response, "activeTab = 'testing'")


class IntegrationSettingsAPITest(TestCase):
    """Test integration settings API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create a super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        
        # Create test external service
        self.test_service = ExternalServiceConfiguration.objects.create(
            name='Test Service',
            service_type='gold_price_api',
            base_url='https://api.test.com',
            authentication_type='api_key',
            api_key='test-key',
            status='active',
            is_enabled=True,
            created_by_id=self.super_admin.id,
            created_by_username=self.super_admin.username
        )
    
    def test_service_configuration_create(self):
        """Test creating a new service configuration via API."""
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
        
        # Create service via API
        url = reverse('admin_panel:service_configuration')
        data = {
            'action': 'create',
            'name': 'New Test Service',
            'service_type': 'payment_gateway',
            'base_url': 'https://api.payment.test',
            'authentication_type': 'api_key',
            'api_key': 'new-test-key'
        }
        
        response = self.client.post(url, data)
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Check that service was created
        self.assertTrue(
            ExternalServiceConfiguration.objects.filter(
                name='New Test Service'
            ).exists()
        )
    
    def test_service_configuration_test_connection(self):
        """Test testing service connection via API."""
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
        
        # Test connection via API
        url = reverse('admin_panel:service_configuration')
        data = {
            'action': 'test_connection',
            'service_id': str(self.test_service.service_id)
        }
        
        response = self.client.post(url, data)
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Parse JSON response
        result = response.json()
        self.assertIn('success', result)
    
    def test_rate_limit_configuration_create(self):
        """Test creating a new rate limit configuration via API."""
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
        
        # Create rate limit via API
        url = reverse('admin_panel:rate_limit_configuration')
        data = {
            'action': 'create',
            'name': 'New Rate Limit',
            'limit_type': 'per_ip',
            'requests_limit': 50,
            'time_window_seconds': 3600
        }
        
        response = self.client.post(url, data)
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Check that rate limit was created
        self.assertTrue(
            APIRateLimitConfiguration.objects.filter(
                name='New Rate Limit'
            ).exists()
        )
    
    def test_integration_health_check(self):
        """Test integration health check via API."""
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
        
        # Get health status via API
        url = reverse('admin_panel:integration_health')
        response = self.client.get(url)
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Parse JSON response
        result = response.json()
        self.assertIn('services', result)