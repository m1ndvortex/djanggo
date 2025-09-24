"""
Tests for RBAC frontend views and templates.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing models
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from zargar.tenants.admin_models import SuperAdmin
from zargar.admin_panel.models import SuperAdminRole, SuperAdminPermission, SuperAdminUserRole
from zargar.admin_panel.services import RBACService


class RBACFrontendTestCase(TestCase):
    """Test RBAC frontend functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create a super admin user
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        
        # Create some test permissions
        self.permission1 = SuperAdminPermission.objects.create(
            codename='test.view',
            name='Test View',
            name_persian='مشاهده تست',
            section='test',
            action='view',
            description='Test permission for viewing'
        )
        
        self.permission2 = SuperAdminPermission.objects.create(
            codename='test.manage',
            name='Test Manage',
            name_persian='مدیریت تست',
            section='test',
            action='manage',
            description='Test permission for managing',
            is_dangerous=True
        )
        
        # Create a test role
        self.role = SuperAdminRole.objects.create(
            name='test_role',
            name_persian='نقش تست',
            description='Test role',
            role_type='custom'
        )
        self.role.permissions.add(self.permission1)
        
        # Login the superadmin
        self.client.login(username='testadmin', password='testpass123')
    
    def test_rbac_management_view(self):
        """Test RBAC management dashboard view."""
        url = reverse('admin_panel:rbac_management')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'کنترل دسترسی')
        self.assertContains(response, 'مدیریت نقش‌ها، مجوزها و دسترسی‌های کاربران')
    
    def test_role_list_view(self):
        """Test role list view."""
        url = reverse('admin_panel:rbac_role_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مدیریت نقش‌ها')
        self.assertContains(response, self.role.name_persian)
    
    def test_role_detail_view(self):
        """Test role detail view."""
        url = reverse('admin_panel:rbac_role_detail', kwargs={'role_id': self.role.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.role.name_persian)
        self.assertContains(response, 'مجوزهای نقش')
    
    def test_create_role_view_get(self):
        """Test create role view GET request."""
        url = reverse('admin_panel:rbac_create_role')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ایجاد نقش جدید')
        self.assertContains(response, 'انتخاب مجوزها')
    
    def test_create_role_view_post(self):
        """Test create role view POST request."""
        url = reverse('admin_panel:rbac_create_role')
        data = {
            'name': 'new_test_role',
            'name_persian': 'نقش تست جدید',
            'description': 'New test role',
            'description_persian': 'نقش تست جدید',
            'role_type': 'custom',
            'permissions': [self.permission1.id, self.permission2.id]
        }
        
        response = self.client.post(url, data)
        
        # Should redirect to role detail page
        self.assertEqual(response.status_code, 302)
        
        # Check that role was created
        new_role = SuperAdminRole.objects.get(name='new_test_role')
        self.assertEqual(new_role.name_persian, 'نقش تست جدید')
        self.assertEqual(new_role.permissions.count(), 2)
    
    def test_user_role_assignment_view(self):
        """Test user role assignment view."""
        url = reverse('admin_panel:rbac_user_assignments')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مدیریت اختصاص نقش‌ها')
        self.assertContains(response, 'اختصاص نقش جدید')
    
    def test_permission_matrix_view(self):
        """Test permission matrix view."""
        url = reverse('admin_panel:rbac_permission_matrix')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ماتریس مجوزها')
        self.assertContains(response, 'نمای کلی از مجوزهای هر نقش')
    
    def test_rbac_stats_api(self):
        """Test RBAC stats API endpoint."""
        url = reverse('admin_panel:rbac_stats_api')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('stats', data)
    
    def test_user_permissions_api(self):
        """Test user permissions API endpoint."""
        # Assign role to user
        SuperAdminUserRole.objects.create(
            user=self.superadmin,
            role=self.role,
            assigned_by_id=self.superadmin.id,
            assigned_by_username=self.superadmin.username
        )
        
        url = reverse('admin_panel:rbac_user_permissions_api')
        response = self.client.get(url, {'user_id': self.superadmin.id})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('permissions', data)
        self.assertGreater(len(data['permissions']), 0)
    
    def test_navigation_link_exists(self):
        """Test that RBAC navigation link exists in base template."""
        url = reverse('admin_panel:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check that the RBAC link is present in navigation
        rbac_url = reverse('admin_panel:rbac_management')
        self.assertContains(response, rbac_url)
    
    def test_unauthorized_access_denied(self):
        """Test that unauthorized users cannot access RBAC views."""
        # Logout the superadmin
        self.client.logout()
        
        # Try to access RBAC management
        url = reverse('admin_panel:rbac_management')
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_role_update_functionality(self):
        """Test role update via POST to role detail view."""
        url = reverse('admin_panel:rbac_role_detail', kwargs={'role_id': self.role.id})
        data = {
            'name': self.role.name,
            'name_persian': 'نقش تست به‌روزرسانی شده',
            'description': 'Updated test role',
            'description_persian': 'نقش تست به‌روزرسانی شده',
            'permissions': [self.permission1.id, self.permission2.id]
        }
        
        response = self.client.post(url, data)
        
        # Should redirect back to role detail
        self.assertEqual(response.status_code, 302)
        
        # Check that role was updated
        updated_role = SuperAdminRole.objects.get(id=self.role.id)
        self.assertEqual(updated_role.name_persian, 'نقش تست به‌روزرسانی شده')
        self.assertEqual(updated_role.permissions.count(), 2)


class RBACTemplateTestCase(TestCase):
    """Test RBAC template rendering and content."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create a super admin user
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        
        # Login the superadmin
        self.client.login(username='testadmin', password='testpass123')
    
    def test_rbac_management_template_content(self):
        """Test RBAC management template contains expected content."""
        url = reverse('admin_panel:rbac_management')
        response = self.client.get(url)
        
        # Check for key UI elements
        self.assertContains(response, 'کنترل دسترسی')
        self.assertContains(response, 'مدیریت نقش‌ها')
        self.assertContains(response, 'اختصاص نقش‌ها')
        self.assertContains(response, 'ماتریس مجوزها')
        self.assertContains(response, 'مجوزهای سیستم')
        
        # Check for statistics cards
        self.assertContains(response, 'کل نقش‌ها')
        self.assertContains(response, 'نقش‌های سیستمی')
        self.assertContains(response, 'نقش‌های سفارشی')
        self.assertContains(response, 'اختصاص‌های فعال')
    
    def test_role_list_template_content(self):
        """Test role list template contains expected content."""
        url = reverse('admin_panel:rbac_role_list')
        response = self.client.get(url)
        
        # Check for key UI elements
        self.assertContains(response, 'مدیریت نقش‌ها')
        self.assertContains(response, 'ایجاد نقش جدید')
        self.assertContains(response, 'جستجو')
        self.assertContains(response, 'نوع نقش')
        
        # Check for breadcrumb navigation
        self.assertContains(response, 'داشبورد')
        self.assertContains(response, 'کنترل دسترسی')
    
    def test_create_role_template_content(self):
        """Test create role template contains expected content."""
        url = reverse('admin_panel:rbac_create_role')
        response = self.client.get(url)
        
        # Check for form elements
        self.assertContains(response, 'نام انگلیسی')
        self.assertContains(response, 'نام فارسی')
        self.assertContains(response, 'نوع نقش')
        self.assertContains(response, 'حداکثر کاربران')
        self.assertContains(response, 'انتخاب مجوزها')
        self.assertContains(response, 'ایجاد نقش')
    
    def test_user_assignment_template_content(self):
        """Test user assignment template contains expected content."""
        url = reverse('admin_panel:rbac_user_assignments')
        response = self.client.get(url)
        
        # Check for key UI elements
        self.assertContains(response, 'مدیریت اختصاص نقش‌ها')
        self.assertContains(response, 'اختصاص نقش جدید')
        self.assertContains(response, 'اختصاص‌های فعلی')
        
        # Check for statistics
        self.assertContains(response, 'کل کاربران')
        self.assertContains(response, 'نقش‌های فعال')
        self.assertContains(response, 'اختصاص‌های فعال')
    
    def test_permission_matrix_template_content(self):
        """Test permission matrix template contains expected content."""
        url = reverse('admin_panel:rbac_permission_matrix')
        response = self.client.get(url)
        
        # Check for key UI elements
        self.assertContains(response, 'ماتریس مجوزها')
        self.assertContains(response, 'کنترل‌ها و راهنما')
        self.assertContains(response, 'صادرات ماتریس')
        
        # Check for legend
        self.assertContains(response, 'مجوز داده شده')
        self.assertContains(response, 'مجوز داده نشده')
        self.assertContains(response, 'مجوز خطرناک')
        self.assertContains(response, 'نیاز به 2FA')
    
    def test_templates_use_correct_base(self):
        """Test that all RBAC templates extend the correct base template."""
        urls_to_test = [
            'admin_panel:rbac_management',
            'admin_panel:rbac_role_list',
            'admin_panel:rbac_create_role',
            'admin_panel:rbac_user_assignments',
            'admin_panel:rbac_permission_matrix',
        ]
        
        for url_name in urls_to_test:
            url = reverse(url_name)
            response = self.client.get(url)
            
            # Check that it uses the unified base template
            self.assertContains(response, 'پنل مدیریت زرگر')
            self.assertContains(response, 'dark:bg-cyber-bg-primary')  # Dark mode classes
            self.assertContains(response, 'persian-numbers')  # Persian number formatting
    
    def test_responsive_design_classes(self):
        """Test that templates include responsive design classes."""
        url = reverse('admin_panel:rbac_management')
        response = self.client.get(url)
        
        # Check for responsive grid classes
        self.assertContains(response, 'grid-cols-1')
        self.assertContains(response, 'md:grid-cols-2')
        self.assertContains(response, 'lg:grid-cols-3')
        self.assertContains(response, 'lg:grid-cols-4')
        
        # Check for responsive spacing
        self.assertContains(response, 'space-x-reverse')
        self.assertContains(response, 'space-y-')
    
    def test_persian_rtl_support(self):
        """Test that templates include proper RTL and Persian support."""
        url = reverse('admin_panel:rbac_management')
        response = self.client.get(url)
        
        # Check for RTL classes
        self.assertContains(response, 'text-right')
        self.assertContains(response, 'space-x-reverse')
        
        # Check for Persian text
        self.assertContains(response, 'کنترل دسترسی')
        self.assertContains(response, 'مدیریت نقش‌ها')
        self.assertContains(response, 'persian-numbers')
    
    def test_dark_mode_support(self):
        """Test that templates include dark mode classes."""
        url = reverse('admin_panel:rbac_management')
        response = self.client.get(url)
        
        # Check for dark mode classes
        self.assertContains(response, 'dark:bg-cyber-bg-primary')
        self.assertContains(response, 'dark:bg-cyber-bg-secondary')
        self.assertContains(response, 'dark:text-cyber-text-primary')
        self.assertContains(response, 'dark:text-cyber-neon-primary')
        self.assertContains(response, 'dark:border-cyber-neon-primary')