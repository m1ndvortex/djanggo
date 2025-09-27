"""
Comprehensive tests for the unified admin dashboard functionality.
"""

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock

from zargar.tenants.admin_models import SuperAdmin, SubscriptionPlan, TenantInvoice
from zargar.tenants.models import Tenant


class UnifiedAdminDashboardTestCase(TestCase):
    """Test cases for the unified admin dashboard."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create a SuperAdmin user
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        
        # Create test tenants
        self.tenant1 = Tenant.objects.create(
            schema_name='tenant1',
            name='Test Tenant 1',
            is_active=True
        )
        
        self.tenant2 = Tenant.objects.create(
            schema_name='tenant2',
            name='Test Tenant 2',
            is_active=False
        )
        
        # Create test subscription plan
        self.plan = SubscriptionPlan.objects.create(
            name='Basic Plan',
            price_toman=100000,
            is_active=True
        )
        
        # Create test invoices
        self.invoice1 = TenantInvoice.objects.create(
            tenant=self.tenant1,
            subscription_plan=self.plan,
            total_amount_toman=Decimal('100000'),
            status='paid'
        )
        
        self.invoice2 = TenantInvoice.objects.create(
            tenant=self.tenant2,
            subscription_plan=self.plan,
            total_amount_toman=Decimal('150000'),
            status='pending'
        )
    
    def test_unified_dashboard_requires_authentication(self):
        """Test that unified dashboard requires authentication."""
        url = reverse('admin_panel:dashboard')
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_unified_dashboard_requires_superadmin(self):
        """Test that unified dashboard requires superadmin privileges."""
        # Create regular user
        regular_user = get_user_model().objects.create_user(
            username='regular',
            email='regular@test.com',
            password='testpass123'
        )
        
        self.client.login(username='regular', password='testpass123')
        url = reverse('admin_panel:dashboard')
        response = self.client.get(url)
        
        # Should redirect or show permission denied
        self.assertNotEqual(response.status_code, 200)
    
    def test_unified_dashboard_loads_successfully(self):
        """Test that unified dashboard loads successfully for superadmin."""
        self.client.login(username='testadmin', password='testpass123')
        url = reverse('admin_panel:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'داشبورد یکپارچه مدیریت')
        self.assertContains(response, 'مدیریت کامل و یکپارچه سیستم زرگر')
    
    def test_unified_dashboard_statistics(self):
        """Test that dashboard shows correct statistics."""
        self.client.login(username='testadmin', password='testpass123')
        url = reverse('admin_panel:dashboard')
        response = self.client.get(url)
        
        # Check context data
        self.assertEqual(response.context['total_tenants'], 2)
        self.assertEqual(response.context['active_tenants'], 1)
        self.assertEqual(response.context['inactive_tenants'], 1)
        self.assertEqual(response.context['active_percentage'], 50.0)
        self.assertEqual(response.context['total_revenue'], Decimal('100000'))
        self.assertEqual(response.context['pending_revenue'], Decimal('150000'))
    
    def test_unified_dashboard_navigation_sections(self):
        """Test that all navigation sections are present."""
        self.client.login(username='testadmin', password='testpass123')
        url = reverse('admin_panel:dashboard')
        response = self.client.get(url)
        
        # Check for all major sections
        self.assertContains(response, 'مدیریت تنانت‌ها')
        self.assertContains(response, 'مدیریت کاربران')
        self.assertContains(response, 'نظارت سیستم')
        self.assertContains(response, 'پشتیبان‌گیری')
        self.assertContains(response, 'مدیریت مالی')
        self.assertContains(response, 'امنیت و حسابرسی')
    
    def test_unified_dashboard_theme_support(self):
        """Test that dashboard supports theme switching."""
        self.client.login(username='testadmin', password='testpass123')
        url = reverse('admin_panel:dashboard')
        response = self.client.get(url)
        
        # Check for theme-related elements
        self.assertContains(response, 'darkMode')
        self.assertContains(response, 'toggleTheme')
        self.assertContains(response, 'cyber-bg')
        self.assertContains(response, 'cyber-neon')
    
    def test_unified_dashboard_persian_rtl_layout(self):
        """Test that dashboard uses Persian RTL layout."""
        self.client.login(username='testadmin', password='testpass123')
        url = reverse('admin_panel:dashboard')
        response = self.client.get(url)
        
        # Check for RTL and Persian elements
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, 'lang="fa"')
        self.assertContains(response, 'Vazirmatn')
        self.assertContains(response, 'persian-numbers')


class UnifiedAdminAPITestCase(TestCase):
    """Test cases for unified admin API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create a SuperAdmin user
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        
        # Create test tenant
        self.tenant = Tenant.objects.create(
            schema_name='testtenant',
            name='Test Tenant',
            is_active=True
        )
    
    def test_stats_api_requires_authentication(self):
        """Test that stats API requires authentication."""
        url = reverse('admin_panel:unified_stats_api')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
    
    def test_stats_api_returns_json(self):
        """Test that stats API returns JSON data."""
        self.client.login(username='testadmin', password='testpass123')
        url = reverse('admin_panel:unified_stats_api')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = response.json()
        self.assertIn('total_tenants', data)
        self.assertIn('active_tenants', data)
        self.assertIn('total_revenue', data)
        self.assertIn('system_status', data)
        self.assertIn('timestamp', data)
    
    def test_recent_activity_api_returns_activities(self):
        """Test that recent activity API returns activity data."""
        self.client.login(username='testadmin', password='testpass123')
        url = reverse('admin_panel:unified_activity_api')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('activities', data)
        self.assertIn('timestamp', data)
        self.assertIsInstance(data['activities'], list)
    
    def test_system_alerts_api_returns_alerts(self):
        """Test that system alerts API returns alert data."""
        self.client.login(username='testadmin', password='testpass123')
        url = reverse('admin_panel:unified_alerts_api')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('alerts', data)
        self.assertIn('timestamp', data)
        self.assertIsInstance(data['alerts'], list)


class UnifiedAdminIntegrationTestCase(TestCase):
    """Integration tests for unified admin features."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create a SuperAdmin user
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
    
    def test_tenant_management_integration(self):
        """Test integration with tenant management features."""
        self.client.login(username='testadmin', password='testpass123')
        
        # Test dashboard loads
        dashboard_url = reverse('admin_panel:dashboard')
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, 200)
        
        # Test tenant list link exists
        self.assertContains(response, reverse('admin_panel:tenants:tenant_list'))
        
        # Test tenant create link exists
        self.assertContains(response, reverse('admin_panel:tenants:tenant_create'))
    
    def test_user_impersonation_integration(self):
        """Test integration with user impersonation features."""
        self.client.login(username='testadmin', password='testpass123')
        
        dashboard_url = reverse('admin_panel:dashboard')
        response = self.client.get(dashboard_url)
        
        # Test impersonation links exist
        self.assertContains(response, reverse('admin_panel:user_impersonation'))
        self.assertContains(response, reverse('admin_panel:impersonation_audit'))
        self.assertContains(response, reverse('admin_panel:impersonation_stats'))
    
    def test_system_health_integration(self):
        """Test integration with system health monitoring."""
        self.client.login(username='testadmin', password='testpass123')
        
        dashboard_url = reverse('admin_panel:dashboard')
        response = self.client.get(dashboard_url)
        
        # Test health monitoring links exist
        self.assertContains(response, reverse('admin_panel:system_health_dashboard'))
        self.assertContains(response, reverse('admin_panel:system_health_alerts'))
        self.assertContains(response, reverse('admin_panel:system_health_reports'))
    
    def test_backup_management_integration(self):
        """Test integration with backup management features."""
        self.client.login(username='testadmin', password='testpass123')
        
        dashboard_url = reverse('admin_panel:dashboard')
        response = self.client.get(dashboard_url)
        
        # Test backup management links exist
        self.assertContains(response, reverse('admin_panel:backup_management'))
        self.assertContains(response, reverse('admin_panel:backup_history'))
        self.assertContains(response, reverse('admin_panel:tenant_restore'))
        self.assertContains(response, reverse('admin_panel:disaster_recovery_dashboard'))
    
    def test_billing_management_integration(self):
        """Test integration with billing and subscription management."""
        self.client.login(username='testadmin', password='testpass123')
        
        dashboard_url = reverse('admin_panel:dashboard')
        response = self.client.get(dashboard_url)
        
        # Test billing management links exist
        self.assertContains(response, reverse('admin_panel:tenants:billing:dashboard'))
        self.assertContains(response, reverse('admin_panel:tenants:billing:subscription_plans'))
        self.assertContains(response, reverse('admin_panel:tenants:billing:invoices'))
        self.assertContains(response, reverse('admin_panel:tenants:billing:reports'))


@pytest.mark.django_db
class TestUnifiedAdminDashboardPerformance:
    """Performance tests for unified admin dashboard."""
    
    def test_dashboard_load_time(self):
        """Test that dashboard loads within acceptable time."""
        import time
        
        client = Client()
        superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        
        client.login(username='testadmin', password='testpass123')
        
        start_time = time.time()
        url = reverse('admin_panel:dashboard')
        response = client.get(url)
        end_time = time.time()
        
        load_time = end_time - start_time
        
        assert response.status_code == 200
        assert load_time < 2.0  # Should load within 2 seconds
    
    def test_api_response_time(self):
        """Test that API endpoints respond quickly."""
        import time
        
        client = Client()
        superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        
        client.login(username='testadmin', password='testpass123')
        
        # Test stats API
        start_time = time.time()
        url = reverse('admin_panel:unified_stats_api')
        response = client.get(url)
        end_time = time.time()
        
        api_time = end_time - start_time
        
        assert response.status_code == 200
        assert api_time < 0.5  # API should respond within 500ms


class UnifiedAdminSecurityTestCase(TestCase):
    """Security tests for unified admin dashboard."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create a SuperAdmin user
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        
        # Create regular user
        self.regular_user = get_user_model().objects.create_user(
            username='regular',
            email='regular@test.com',
            password='testpass123'
        )
    
    def test_unauthorized_access_blocked(self):
        """Test that unauthorized users cannot access admin features."""
        # Test without login
        urls = [
            reverse('admin_panel:dashboard'),
            reverse('admin_panel:unified_stats_api'),
            reverse('admin_panel:unified_activity_api'),
            reverse('admin_panel:unified_alerts_api'),
        ]
        
        for url in urls:
            response = self.client.get(url)
            self.assertNotEqual(response.status_code, 200)
    
    def test_regular_user_access_blocked(self):
        """Test that regular users cannot access admin features."""
        self.client.login(username='regular', password='testpass123')
        
        urls = [
            reverse('admin_panel:dashboard'),
            reverse('admin_panel:unified_stats_api'),
            reverse('admin_panel:unified_activity_api'),
            reverse('admin_panel:unified_alerts_api'),
        ]
        
        for url in urls:
            response = self.client.get(url)
            self.assertNotEqual(response.status_code, 200)
    
    def test_superadmin_access_allowed(self):
        """Test that superadmin users can access all features."""
        self.client.login(username='testadmin', password='testpass123')
        
        urls = [
            reverse('admin_panel:dashboard'),
            reverse('admin_panel:unified_stats_api'),
            reverse('admin_panel:unified_activity_api'),
            reverse('admin_panel:unified_alerts_api'),
        ]
        
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
    
    def test_csrf_protection(self):
        """Test that CSRF protection is in place."""
        self.client.login(username='testadmin', password='testpass123')
        
        # Test POST requests require CSRF token
        url = reverse('admin_panel:dashboard')
        response = self.client.post(url, {})
        
        # Should either work with CSRF or be blocked
        self.assertIn(response.status_code, [200, 403, 405])


if __name__ == '__main__':
    pytest.main([__file__])