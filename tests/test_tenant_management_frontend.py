"""
Tests for tenant management frontend interface.
"""

import pytest
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from zargar.tenants.models import Tenant, Domain
from zargar.tenants.admin_models import SuperAdmin

User = get_user_model()


@override_settings(ROOT_URLCONF='zargar.urls_public')
class TenantManagementFrontendTest(TestCase):
    """Test tenant management frontend interface."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create superuser for admin access
        self.superuser = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        
        # Create test tenant
        self.tenant = Tenant.objects.create(
            name='Test Jewelry Shop',
            schema_name='test_shop',
            owner_name='Test Owner',
            owner_email='owner@test.com',
            phone_number='09123456789',
            address='Test Address',
            subscription_plan='basic',
            is_active=True
        )
        
        # Create domain for tenant
        self.domain = Domain.objects.create(
            domain='test-shop.zargar.com',
            tenant=self.tenant,
            is_primary=True
        )
    
    def test_tenant_list_view_requires_authentication(self):
        """Test that tenant list view requires authentication."""
        url = reverse('core:tenants:tenant_list')
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_tenant_list_view_authenticated(self):
        """Test tenant list view with authenticated user."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مدیریت تنانت‌ها')
        self.assertContains(response, self.tenant.name)
        self.assertContains(response, self.tenant.owner_name)
    
    def test_tenant_list_view_context(self):
        """Test tenant list view context data."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check context variables
        self.assertIn('tenants', response.context)
        self.assertIn('total_tenants', response.context)
        self.assertIn('active_tenants', response.context)
        self.assertIn('inactive_tenants', response.context)
        self.assertIn('recent_signups', response.context)
        
        # Check statistics
        self.assertEqual(response.context['total_tenants'], 1)
        self.assertEqual(response.context['active_tenants'], 1)
        self.assertEqual(response.context['inactive_tenants'], 0)
    
    def test_tenant_create_view_get(self):
        """Test tenant create view GET request."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ایجاد تنانت جدید')
        self.assertContains(response, 'نام فروشگاه')
        self.assertContains(response, 'Domain URL')
    
    def test_tenant_detail_view(self):
        """Test tenant detail view."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_detail', kwargs={'pk': self.tenant.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.tenant.name)
        self.assertContains(response, self.tenant.owner_name)
        self.assertContains(response, self.tenant.owner_email)
        self.assertContains(response, self.tenant.schema_name)
    
    def test_tenant_update_view_get(self):
        """Test tenant update view GET request."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_update', kwargs={'pk': self.tenant.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'ویرایش {self.tenant.name}')
        self.assertContains(response, 'value="' + self.tenant.name + '"')
        self.assertContains(response, 'value="' + self.tenant.owner_name + '"')
    
    def test_tenant_delete_view_get(self):
        """Test tenant delete view GET request."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_delete', kwargs={'pk': self.tenant.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'حذف {self.tenant.name}')
        self.assertContains(response, 'هشدار خطرناک')
        self.assertContains(response, 'این عمل غیرقابل بازگشت است')
    
    def test_tenant_search_functionality(self):
        """Test tenant search functionality."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_list')
        
        # Search by name
        response = self.client.get(url, {'search': 'Test Jewelry'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.tenant.name)
        
        # Search by owner
        response = self.client.get(url, {'search': 'Test Owner'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.tenant.name)
        
        # Search with no results
        response = self.client.get(url, {'search': 'NonExistent'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.tenant.name)
    
    def test_tenant_filter_functionality(self):
        """Test tenant filter functionality."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_list')
        
        # Filter by status
        response = self.client.get(url, {'status': 'active'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.tenant.name)
        
        response = self.client.get(url, {'status': 'inactive'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.tenant.name)
        
        # Filter by subscription plan
        response = self.client.get(url, {'plan': 'basic'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.tenant.name)
    
    def test_tenant_statistics_ajax(self):
        """Test tenant statistics AJAX endpoint."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_statistics', kwargs={'pk': self.tenant.pk})
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('stats', data)
    
    def test_tenant_toggle_status_ajax(self):
        """Test tenant status toggle AJAX endpoint."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_toggle_status', kwargs={'pk': self.tenant.pk})
        
        # Toggle to inactive
        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertFalse(data['new_status'])
        
        # Verify tenant is now inactive
        self.tenant.refresh_from_db()
        self.assertFalse(self.tenant.is_active)
    
    def test_tenant_search_ajax(self):
        """Test tenant search AJAX endpoint."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_search')
        
        response = self.client.get(url, {'q': 'Test'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['name'], self.tenant.name)
    
    def test_bulk_action_ajax(self):
        """Test bulk action AJAX endpoint."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_bulk_action')
        
        # Test activate action
        response = self.client.post(url, {
            'action': 'activate',
            'tenant_ids': [str(self.tenant.id)]
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
    
    def test_template_rendering(self):
        """Test that templates render without errors."""
        self.client.force_login(self.superuser)
        
        # Test all main tenant management templates
        urls_to_test = [
            reverse('core:tenants:tenant_list'),
            reverse('core:tenants:tenant_create'),
            reverse('core:tenants:tenant_detail', kwargs={'pk': self.tenant.pk}),
            reverse('core:tenants:tenant_update', kwargs={'pk': self.tenant.pk}),
            reverse('core:tenants:tenant_delete', kwargs={'pk': self.tenant.pk}),
        ]
        
        for url in urls_to_test:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Failed for URL: {url}")
            
            # Check for common template elements
            self.assertContains(response, 'پنل مدیریت زرگر')
            self.assertContains(response, 'html', msg_prefix=f"No HTML tag found in {url}")
    
    def test_persian_content_rendering(self):
        """Test that Persian content renders correctly."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_list')
        response = self.client.get(url)
        
        # Check for Persian text
        persian_texts = [
            'مدیریت تنانت‌ها',
            'ایجاد تنانت جدید',
            'کل تنانت‌ها',
            'فعال',
            'غیرفعال'
        ]
        
        for text in persian_texts:
            self.assertContains(response, text)
    
    def test_rtl_layout_elements(self):
        """Test that RTL layout elements are present."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_list')
        response = self.client.get(url)
        
        # Check for RTL attributes
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, 'lang="fa"')
    
    def test_theme_toggle_functionality(self):
        """Test that theme toggle elements are present."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_list')
        response = self.client.get(url)
        
        # Check for theme toggle elements
        self.assertContains(response, 'darkMode')
        self.assertContains(response, 'localStorage.getItem(\'theme\')')
    
    def test_responsive_design_elements(self):
        """Test that responsive design classes are present."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_list')
        response = self.client.get(url)
        
        # Check for responsive classes
        responsive_classes = [
            'grid-cols-1',
            'md:grid-cols-',
            'sm:flex-row',
            'lg:col-span-'
        ]
        
        content = response.content.decode()
        for css_class in responsive_classes:
            self.assertIn(css_class, content)
    
    def test_accessibility_attributes(self):
        """Test that accessibility attributes are present."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_list')
        response = self.client.get(url)
        
        # Check for accessibility attributes
        self.assertContains(response, 'aria-')
        self.assertContains(response, 'role=')
        self.assertContains(response, 'alt=')
    
    def test_form_validation_elements(self):
        """Test that form validation elements are present."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_create')
        response = self.client.get(url)
        
        # Check for validation elements
        self.assertContains(response, 'required')
        self.assertContains(response, 'form-error')
        self.assertContains(response, 'validateField')


@override_settings(ROOT_URLCONF='zargar.urls_public')
class TenantManagementJavaScriptTest(TestCase):
    """Test JavaScript functionality for tenant management."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create superuser
        self.superuser = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
    
    def test_javascript_files_included(self):
        """Test that JavaScript files are included in templates."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_list')
        response = self.client.get(url)
        
        # Check for JavaScript includes
        self.assertContains(response, 'tenant-management.js')
        self.assertContains(response, 'alpine.min.js')
        self.assertContains(response, 'htmx.min.js')
    
    def test_javascript_functions_defined(self):
        """Test that JavaScript functions are defined in templates."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_list')
        response = self.client.get(url)
        
        # Check for JavaScript functions
        js_functions = [
            'showTenantStats',
            'closeTenantStatsModal',
            'ZargarAdmin.showLoading',
            'ZargarAdmin.hideLoading',
            'ZargarAdmin.formatPersianNumber'
        ]
        
        content = response.content.decode()
        for function in js_functions:
            self.assertIn(function, content)
    
    def test_css_files_included(self):
        """Test that CSS files are included in templates."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_list')
        response = self.client.get(url)
        
        # Check for CSS includes
        self.assertContains(response, 'base-rtl.css')
        self.assertContains(response, 'admin-dashboard.css')
    
    def test_cybersecurity_theme_classes(self):
        """Test that cybersecurity theme CSS classes are present."""
        self.client.force_login(self.superuser)
        url = reverse('core:tenants:tenant_list')
        response = self.client.get(url)
        
        # Check for cybersecurity theme classes
        cyber_classes = [
            'cyber-glass',
            'cyber-card',
            'cyber-button',
            'cyber-neon-primary',
            'cyber-bg-surface'
        ]
        
        content = response.content.decode()
        for css_class in cyber_classes:
            self.assertIn(css_class, content)