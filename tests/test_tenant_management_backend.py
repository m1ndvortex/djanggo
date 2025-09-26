"""
Integration tests for tenant management system backend.
Tests tenant CRUD operations, automated schema provisioning, statistics collection,
and search/filtering functionality.
"""

import pytest
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone
from django_tenants.utils import schema_context
from unittest.mock import patch, MagicMock
import json
from datetime import timedelta

from zargar.tenants.models import Tenant, Domain
from zargar.tenants.admin_models import SuperAdmin, TenantAccessLog
from zargar.tenants.services import TenantProvisioningService, TenantStatisticsService
from zargar.tenants.forms import TenantCreateForm, TenantUpdateForm, TenantSearchForm

User = get_user_model()


class TenantManagementBackendTestCase(TransactionTestCase):
    """
    Test case for tenant management backend functionality.
    Uses TransactionTestCase to handle schema creation/deletion.
    """
    
    def setUp(self):
        """Set up test data."""
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='superadmin',
            email='admin@zargar.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True,
            can_create_tenants=True,
            can_suspend_tenants=True,
            can_access_all_data=True
        )
        
        # Create test tenant data
        self.tenant_data = {
            'name': 'طلا و جواهرات آریا',
            'owner_name': 'علی احمدی',
            'owner_email': 'ali@aria-jewelry.com',
            'phone_number': '09123456789',
            'address': 'تهران، خیابان ولیعصر، پلاک ۱۲۳',
            'subscription_plan': 'basic'
        }
        
        self.domain_data = {
            'domain_url': 'aria-jewelry'
        }
    
    def tearDown(self):
        """Clean up after tests."""
        # Clean up any created tenants
        test_tenants = Tenant.objects.filter(name__icontains='test').exclude(schema_name='public')
        for tenant in test_tenants:
            try:
                tenant.delete()
            except:
                pass
    
    def test_tenant_provisioning_service_complete_workflow(self):
        """Test complete tenant provisioning workflow."""
        # Create tenant instance
        tenant = Tenant.objects.create(
            name='Test Jewelry Shop',
            schema_name='test_jewelry_shop',
            owner_name='Test Owner',
            owner_email='test@example.com',
            subscription_plan='basic'
        )
        
        # Test provisioning service
        provisioning_service = TenantProvisioningService()
        result = provisioning_service.provision_tenant(tenant)
        
        # Verify provisioning success
        self.assertTrue(result['success'])
        self.assertIn('schema_created', result['details'])
        self.assertIn('migrations_run', result['details'])
        self.assertIn('initial_data', result['details'])
        self.assertIn('admin_user', result['details'])
        
        # Verify schema exists
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [tenant.schema_name]
            )
            self.assertIsNotNone(cursor.fetchone())
        
        # Verify initial data setup
        with schema_context(tenant.schema_name):
            from django.contrib.auth.models import Group
            
            # Check that user groups were created
            self.assertTrue(Group.objects.filter(name='مالک فروشگاه').exists())
            self.assertTrue(Group.objects.filter(name='حسابدار').exists())
            self.assertTrue(Group.objects.filter(name='فروشنده').exists())
            
            # Check that owner user was created
            owner_user = User.objects.filter(email=tenant.owner_email).first()
            self.assertIsNotNone(owner_user)
            self.assertTrue(owner_user.is_staff)
            self.assertTrue(owner_user.is_active)
    
    def test_tenant_statistics_service(self):
        """Test tenant statistics collection."""
        # Create and provision tenant
        tenant = Tenant.objects.create(
            name='Stats Test Shop',
            schema_name='stats_test_shop',
            owner_name='Stats Owner',
            owner_email='stats@example.com',
            subscription_plan='pro'
        )
        
        provisioning_service = TenantProvisioningService()
        provisioning_service.provision_tenant(tenant)
        
        # Create some test activity logs
        TenantAccessLog.objects.create(
            user_type='user',
            user_id=1,
            username='testuser',
            tenant_schema=tenant.schema_name,
            tenant_name=tenant.name,
            action='login',
            success=True,
            duration_ms=150
        )
        
        TenantAccessLog.objects.create(
            user_type='user',
            user_id=1,
            username='testuser',
            tenant_schema=tenant.schema_name,
            tenant_name=tenant.name,
            action='create',
            model_name='JewelryItem',
            success=True,
            duration_ms=200
        )
        
        # Test statistics service
        stats_service = TenantStatisticsService(tenant)
        stats = stats_service.get_comprehensive_stats()
        
        # Verify statistics structure
        self.assertIn('basic_info', stats)
        self.assertIn('usage_metrics', stats)
        self.assertIn('activity_stats', stats)
        self.assertIn('performance_metrics', stats)
        self.assertIn('storage_usage', stats)
        self.assertIn('user_statistics', stats)
        
        # Verify basic info
        basic_info = stats['basic_info']
        self.assertEqual(basic_info['name'], tenant.name)
        self.assertEqual(basic_info['schema_name'], tenant.schema_name)
        self.assertEqual(basic_info['subscription_plan'], tenant.subscription_plan)
        
        # Verify activity stats
        activity_stats = stats['activity_stats']
        self.assertEqual(activity_stats['total_actions_30_days'], 2)
        self.assertEqual(activity_stats['success_rate'], 100.0)
    
    def test_tenant_create_view_with_authentication(self):
        """Test tenant creation view with proper authentication."""
        self.client.force_login(self.super_admin)
        
        # Test GET request (form display)
        url = reverse('core:tenants:tenant_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ایجاد تنانت جدید')
        
        # Test POST request (tenant creation)
        form_data = {
            **self.tenant_data,
            **self.domain_data,
            'confirm_creation': True
        }
        
        response = self.client.post(url, form_data)
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Verify tenant was created
        tenant = Tenant.objects.filter(name=self.tenant_data['name']).first()
        self.assertIsNotNone(tenant)
        self.assertEqual(tenant.owner_email, self.tenant_data['owner_email'])
        
        # Verify domain was created
        domain = Domain.objects.filter(tenant=tenant).first()
        self.assertIsNotNone(domain)
        self.assertTrue(domain.is_primary)
        
        # Verify access log was created
        log_entry = TenantAccessLog.objects.filter(
            action='create',
            model_name='Tenant',
            object_id=str(tenant.id)
        ).first()
        self.assertIsNotNone(log_entry)
    
    def test_tenant_list_view_with_search_and_filtering(self):
        """Test tenant list view with search and filtering capabilities."""
        self.client.force_login(self.super_admin)
        
        # Create test tenants
        tenant1 = Tenant.objects.create(
            name='Gold Shop 1',
            schema_name='gold_shop_1',
            owner_name='Owner 1',
            owner_email='owner1@example.com',
            subscription_plan='basic',
            is_active=True
        )
        
        tenant2 = Tenant.objects.create(
            name='Silver Shop 2',
            schema_name='silver_shop_2',
            owner_name='Owner 2',
            owner_email='owner2@example.com',
            subscription_plan='pro',
            is_active=False
        )
        
        # Test basic list view
        url = reverse('core:tenants:tenant_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gold Shop 1')
        self.assertContains(response, 'Silver Shop 2')
        
        # Test search functionality
        response = self.client.get(url, {'search': 'Gold'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gold Shop 1')
        self.assertNotContains(response, 'Silver Shop 2')
        
        # Test status filtering
        response = self.client.get(url, {'status': 'active'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gold Shop 1')
        self.assertNotContains(response, 'Silver Shop 2')
        
        # Test plan filtering
        response = self.client.get(url, {'plan': 'pro'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Gold Shop 1')
        self.assertContains(response, 'Silver Shop 2')
    
    def test_tenant_detail_view_with_statistics(self):
        """Test tenant detail view with comprehensive statistics."""
        self.client.force_login(self.super_admin)
        
        # Create and provision tenant
        tenant = Tenant.objects.create(
            name='Detail Test Shop',
            schema_name='detail_test_shop',
            owner_name='Detail Owner',
            owner_email='detail@example.com',
            subscription_plan='enterprise'
        )
        
        provisioning_service = TenantProvisioningService()
        provisioning_service.provision_tenant(tenant)
        
        # Test detail view
        url = reverse('core:tenants:tenant_detail', kwargs={'pk': tenant.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Verify tenant information is displayed
        self.assertContains(response, tenant.name)
        self.assertContains(response, tenant.owner_name)
        self.assertContains(response, tenant.owner_email)
        self.assertContains(response, tenant.get_subscription_plan_display())
        
        # Verify statistics are included
        self.assertIn('tenant_stats', response.context)
        stats = response.context['tenant_stats']
        self.assertIn('basic_info', stats)
        self.assertIn('usage_metrics', stats)
    
    def test_tenant_update_view(self):
        """Test tenant update functionality."""
        self.client.force_login(self.super_admin)
        
        # Create tenant
        tenant = Tenant.objects.create(
            name='Update Test Shop',
            schema_name='update_test_shop',
            owner_name='Update Owner',
            owner_email='update@example.com',
            subscription_plan='basic'
        )
        
        # Test GET request (form display)
        url = reverse('core:tenants:tenant_update', kwargs={'pk': tenant.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, tenant.name)
        
        # Test POST request (update)
        updated_data = {
            'name': 'Updated Shop Name',
            'owner_name': 'Updated Owner Name',
            'owner_email': tenant.owner_email,  # Keep same email
            'phone_number': '09987654321',
            'address': 'Updated Address',
            'subscription_plan': 'pro',
            'is_active': True
        }
        
        response = self.client.post(url, updated_data)
        self.assertEqual(response.status_code, 302)
        
        # Verify updates
        tenant.refresh_from_db()
        self.assertEqual(tenant.name, 'Updated Shop Name')
        self.assertEqual(tenant.subscription_plan, 'pro')
        self.assertEqual(tenant.phone_number, '09987654321')
        
        # Verify update log was created
        log_entry = TenantAccessLog.objects.filter(
            action='update',
            model_name='Tenant',
            object_id=str(tenant.id)
        ).first()
        self.assertIsNotNone(log_entry)
    
    def test_tenant_toggle_status_ajax(self):
        """Test tenant status toggle via AJAX."""
        self.client.force_login(self.super_admin)
        
        # Create tenant
        tenant = Tenant.objects.create(
            name='Toggle Test Shop',
            schema_name='toggle_test_shop',
            owner_name='Toggle Owner',
            owner_email='toggle@example.com',
            subscription_plan='basic',
            is_active=True
        )
        
        # Test toggle to inactive
        url = reverse('core:tenants:tenant_toggle_status', kwargs={'pk': tenant.pk})
        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertFalse(data['new_status'])
        
        # Verify status changed
        tenant.refresh_from_db()
        self.assertFalse(tenant.is_active)
        
        # Test toggle back to active
        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertTrue(data['new_status'])
        
        # Verify status changed back
        tenant.refresh_from_db()
        self.assertTrue(tenant.is_active)
    
    def test_tenant_search_ajax(self):
        """Test tenant search via AJAX."""
        self.client.force_login(self.super_admin)
        
        # Create test tenants
        tenant1 = Tenant.objects.create(
            name='Search Test Shop 1',
            schema_name='search_test_1',
            owner_name='Search Owner 1',
            owner_email='search1@example.com',
            subscription_plan='basic'
        )
        
        tenant2 = Tenant.objects.create(
            name='Another Shop',
            schema_name='another_shop',
            owner_name='Another Owner',
            owner_email='another@example.com',
            subscription_plan='pro'
        )
        
        # Test search
        url = reverse('core:tenants:tenant_search')
        response = self.client.get(url, {'q': 'Search'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['name'], 'Search Test Shop 1')
    
    def test_tenant_bulk_actions(self):
        """Test bulk actions on multiple tenants."""
        self.client.force_login(self.super_admin)
        
        # Create test tenants
        tenant1 = Tenant.objects.create(
            name='Bulk Test Shop 1',
            schema_name='bulk_test_1',
            owner_name='Bulk Owner 1',
            owner_email='bulk1@example.com',
            subscription_plan='basic',
            is_active=True
        )
        
        tenant2 = Tenant.objects.create(
            name='Bulk Test Shop 2',
            schema_name='bulk_test_2',
            owner_name='Bulk Owner 2',
            owner_email='bulk2@example.com',
            subscription_plan='pro',
            is_active=True
        )
        
        # Test bulk deactivation
        url = reverse('core:tenants:tenant_bulk_action')
        response = self.client.post(url, {
            'action': 'deactivate',
            'tenant_ids': [tenant1.id, tenant2.id]
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify tenants were deactivated
        tenant1.refresh_from_db()
        tenant2.refresh_from_db()
        self.assertFalse(tenant1.is_active)
        self.assertFalse(tenant2.is_active)
    
    def test_tenant_delete_with_schema_cleanup(self):
        """Test tenant deletion with schema cleanup using service directly."""
        # Create and provision tenant
        tenant = Tenant.objects.create(
            name='Delete Test Shop',
            schema_name='delete_test_shop',
            owner_name='Delete Owner',
            owner_email='delete@example.com',
            subscription_plan='basic'
        )
        
        provisioning_service = TenantProvisioningService()
        provisioning_service.provision_tenant(tenant)
        
        # Verify schema exists before deletion
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [tenant.schema_name]
            )
            self.assertIsNotNone(cursor.fetchone())
        
        # Test deprovisioning service
        deprovision_result = provisioning_service.deprovision_tenant(tenant)
        self.assertTrue(deprovision_result['success'])
        
        # Test tenant deletion (this will trigger schema deletion due to auto_drop_schema=True)
        tenant_id = tenant.id
        tenant.delete()
        
        # Verify tenant was deleted
        self.assertFalse(Tenant.objects.filter(pk=tenant_id).exists())
    
    def test_unauthorized_access_protection(self):
        """Test that non-super-admin users cannot access tenant management views."""
        # Create regular user (non-super-admin)
        regular_user = SuperAdmin.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='testpass123',
            is_superuser=False,  # Not a superuser
            can_create_tenants=False,
            can_suspend_tenants=False,
            can_access_all_data=False
        )
        
        # Test that SuperAdminRequiredMixin properly restricts access
        from zargar.tenants.views import TenantListView
        from django.test import RequestFactory
        from django.contrib.auth.models import AnonymousUser
        
        factory = RequestFactory()
        request = factory.get('/tenants/')
        request.user = regular_user
        
        view = TenantListView()
        view.request = request
        
        # Should raise PermissionDenied for non-superuser
        from django.core.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            view.dispatch(request)
    
    def test_form_validation(self):
        """Test form validation for tenant creation and updates."""
        # Test tenant creation form validation
        form_data = {
            'name': '',  # Empty name should fail
            'owner_email': 'invalid-email',  # Invalid email
            'domain_url': 'invalid domain!',  # Invalid domain
            'confirm_creation': False  # Missing confirmation
        }
        
        form = TenantCreateForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('owner_email', form.errors)
        self.assertIn('domain_url', form.errors)
        self.assertIn('confirm_creation', form.errors)
        
        # Test valid form data
        valid_data = {
            'name': 'Valid Shop Name',
            'owner_name': 'Valid Owner',
            'owner_email': 'valid@example.com',
            'phone_number': '09123456789',
            'address': 'Valid Address',
            'subscription_plan': 'basic',
            'domain_url': 'valid-domain',
            'confirm_creation': True
        }
        
        form = TenantCreateForm(data=valid_data)
        self.assertTrue(form.is_valid())
    
    def test_global_statistics(self):
        """Test global statistics across all tenants."""
        # Create multiple tenants
        for i in range(3):
            Tenant.objects.create(
                name=f'Global Stats Shop {i}',
                schema_name=f'global_stats_{i}',
                owner_name=f'Owner {i}',
                owner_email=f'owner{i}@example.com',
                subscription_plan='basic' if i % 2 == 0 else 'pro',
                is_active=i != 2  # Make one inactive
            )
        
        # Get global statistics
        global_stats = TenantStatisticsService.get_global_statistics()
        
        # Verify statistics
        self.assertGreaterEqual(global_stats['total_tenants'], 3)
        self.assertGreaterEqual(global_stats['active_tenants'], 2)
        self.assertGreaterEqual(global_stats['inactive_tenants'], 1)
        self.assertIn('plan_distribution', global_stats)
        self.assertIn('recent_signups', global_stats)


class TenantFormTestCase(TestCase):
    """Test cases for tenant management forms."""
    
    def test_tenant_create_form_validation(self):
        """Test comprehensive validation for tenant creation form."""
        # Test duplicate name validation
        Tenant.objects.create(
            name='Existing Shop',
            schema_name='existing_shop',
            owner_email='existing@example.com'
        )
        
        form_data = {
            'name': 'Existing Shop',  # Duplicate name
            'owner_email': 'new@example.com',
            'domain_url': 'new-domain',
            'confirm_creation': True
        }
        
        form = TenantCreateForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_phone_number_normalization(self):
        """Test Iranian phone number validation and normalization."""
        test_cases = [
            ('09123456789', '09123456789'),  # Already normalized
            ('+989123456789', '09123456789'),  # With country code
            ('989123456789', '09123456789'),  # Without + but with country code
            ('9123456789', '09123456789'),  # Without leading 0
        ]
        
        for input_phone, expected_phone in test_cases:
            form_data = {
                'name': 'Test Shop',
                'owner_email': 'test@example.com',
                'phone_number': input_phone,
                'domain_url': 'test-domain',
                'confirm_creation': True
            }
            
            form = TenantCreateForm(data=form_data)
            if form.is_valid():
                self.assertEqual(form.cleaned_data['phone_number'], expected_phone)
    
    def test_domain_validation(self):
        """Test domain URL validation."""
        # Test reserved words
        reserved_domains = ['admin', 'api', 'www', 'system']
        
        for domain in reserved_domains:
            form_data = {
                'name': 'Test Shop',
                'owner_email': 'test@example.com',
                'domain_url': domain,
                'confirm_creation': True
            }
            
            form = TenantCreateForm(data=form_data)
            self.assertFalse(form.is_valid())
            self.assertIn('domain_url', form.errors)


if __name__ == '__main__':
    pytest.main([__file__])