"""
Tests for audit log management frontend functionality.
Tests the audit log management interface, theme switching, and UI navigation.
"""

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import json

from zargar.tenants.admin_models import SuperAdmin, PublicAuditLog
from zargar.admin_panel.audit_services import (
    AuditLogFilterService,
    AuditLogDetailService,
    AuditLogExportService
)


class AuditLogManagementFrontendTestCase(TestCase):
    """Test case for audit log management frontend functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create super admin user
        self.super_admin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        
        # Create test audit logs
        self.audit_logs = []
        for i in range(10):
            log = PublicAuditLog.objects.create(
                user_id=self.super_admin.id,
                user_username=self.super_admin.username,
                action='create' if i % 2 == 0 else 'update',
                model_name='TestModel',
                object_id=str(i),
                object_repr=f'Test Object {i}',
                ip_address=f'192.168.1.{i+1}',
                tenant_schema=f'tenant_{i % 3}',
                old_values={'field': f'old_value_{i}'} if i % 2 == 1 else None,
                new_values={'field': f'new_value_{i}'},
                changes={'field': [f'old_value_{i}', f'new_value_{i}']} if i % 2 == 1 else None,
                checksum='test_checksum' if i % 3 == 0 else '',
                details={'test': f'detail_{i}'}
            )
            self.audit_logs.append(log)
        
        # Login as super admin
        self.client.login(username='testadmin', password='testpass123')
    
    def test_audit_logs_list_view_access(self):
        """Test that audit logs list view is accessible."""
        url = reverse('admin_panel:audit_logs')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'لاگ‌های حسابرسی')
        self.assertContains(response, 'مشاهده و مدیریت لاگ‌های حسابرسی سیستم')
    
    def test_audit_logs_list_view_content(self):
        """Test that audit logs list view displays correct content."""
        url = reverse('admin_panel:audit_logs')
        response = self.client.get(url)
        
        # Check statistics cards
        self.assertContains(response, 'کل لاگ‌ها')
        self.assertContains(response, 'فیلتر شده')
        self.assertContains(response, '۲۴ ساعت اخیر')
        self.assertContains(response, 'نیاز به بررسی')
        
        # Check filter section
        self.assertContains(response, 'فیلترهای پیشرفته')
        self.assertContains(response, 'جستجو')
        self.assertContains(response, 'عملیات')
        self.assertContains(response, 'وضعیت یکپارچگی')
        
        # Check table headers
        self.assertContains(response, 'تاریخ و زمان')
        self.assertContains(response, 'کاربر')
        self.assertContains(response, 'شیء')
        self.assertContains(response, 'IP')
        self.assertContains(response, 'تنانت')
        self.assertContains(response, 'یکپارچگی')
        
        # Check that audit logs are displayed
        for log in self.audit_logs[:5]:  # Check first few logs
            self.assertContains(response, log.user_username)
            self.assertContains(response, log.object_repr)
    
    def test_audit_logs_filtering(self):
        """Test audit logs filtering functionality."""
        url = reverse('admin_panel:audit_logs')
        
        # Test action filter
        response = self.client.get(url, {'action': 'create'})
        self.assertEqual(response.status_code, 200)
        
        # Test username filter
        response = self.client.get(url, {'username': 'testadmin'})
        self.assertEqual(response.status_code, 200)
        
        # Test IP address filter
        response = self.client.get(url, {'ip_address': '192.168.1.1'})
        self.assertEqual(response.status_code, 200)
        
        # Test tenant filter
        response = self.client.get(url, {'tenant_schema': 'tenant_0'})
        self.assertEqual(response.status_code, 200)
        
        # Test date range filter
        today = timezone.now().date()
        response = self.client.get(url, {
            'date_from': today.strftime('%Y-%m-%d'),
            'date_to': today.strftime('%Y-%m-%d')
        })
        self.assertEqual(response.status_code, 200)
        
        # Test search filter
        response = self.client.get(url, {'search': 'Test Object'})
        self.assertEqual(response.status_code, 200)
        
        # Test integrity status filter
        response = self.client.get(url, {'integrity_status': 'verified'})
        self.assertEqual(response.status_code, 200)
    
    def test_audit_logs_pagination(self):
        """Test audit logs pagination."""
        # Create more audit logs to test pagination
        for i in range(50):
            PublicAuditLog.objects.create(
                user_id=self.super_admin.id,
                user_username=f'user_{i}',
                action='create',
                model_name='TestModel',
                object_id=str(i + 100),
                object_repr=f'Paginated Object {i}',
                ip_address='192.168.1.100',
                tenant_schema='test_tenant'
            )
        
        url = reverse('admin_panel:audit_logs')
        response = self.client.get(url)
        
        # Check pagination controls
        self.assertContains(response, 'نمایش')
        self.assertContains(response, 'نتیجه')
        
        # Test second page
        response = self.client.get(url, {'page': 2})
        self.assertEqual(response.status_code, 200)
    
    def test_audit_log_detail_view_access(self):
        """Test that audit log detail view is accessible."""
        log = self.audit_logs[0]
        url = reverse('admin_panel:audit_log_detail', kwargs={'log_id': log.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'جزئیات لاگ حسابرسی')
        self.assertContains(response, f'لاگ شماره {log.id}')
    
    def test_audit_log_detail_view_content(self):
        """Test that audit log detail view displays correct content."""
        log = self.audit_logs[1]  # Use log with changes
        url = reverse('admin_panel:audit_log_detail', kwargs={'log_id': log.id})
        response = self.client.get(url)
        
        # Check basic information section
        self.assertContains(response, 'اطلاعات کلی')
        self.assertContains(response, log.user_username)
        self.assertContains(response, log.get_action_display())
        self.assertContains(response, log.ip_address)
        self.assertContains(response, log.object_repr)
        
        # Check integrity status section
        self.assertContains(response, 'وضعیت یکپارچگی')
        
        # Check changes section (for logs with changes)
        if log.old_values or log.new_values:
            self.assertContains(response, 'تغییرات')
            self.assertContains(response, 'مقدار قبلی')
            self.assertContains(response, 'مقدار جدید')
        
        # Check raw JSON data section
        self.assertContains(response, 'داده‌های خام')
        
        # Check quick actions section
        self.assertContains(response, 'عملیات سریع')
        self.assertContains(response, 'کپی جزئیات')
        self.assertContains(response, 'صادرات JSON')
        
        # Check technical details section
        self.assertContains(response, 'جزئیات فنی')
        self.assertContains(response, str(log.id))
    
    def test_audit_log_detail_breadcrumb_navigation(self):
        """Test breadcrumb navigation in audit log detail view."""
        log = self.audit_logs[0]
        url = reverse('admin_panel:audit_log_detail', kwargs={'log_id': log.id})
        response = self.client.get(url)
        
        # Check breadcrumb elements
        self.assertContains(response, 'داشبورد')
        self.assertContains(response, 'لاگ‌های حسابرسی')
        self.assertContains(response, 'جزئیات لاگ')
        
        # Check breadcrumb links
        dashboard_url = reverse('admin_panel:dashboard')
        audit_logs_url = reverse('admin_panel:audit_logs')
        self.assertContains(response, f'href="{dashboard_url}"')
        self.assertContains(response, f'href="{audit_logs_url}"')
    
    def test_audit_log_export_csv(self):
        """Test CSV export functionality."""
        url = reverse('admin_panel:audit_log_export')
        response = self.client.get(url, {'format': 'csv'})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertTrue(response['Content-Disposition'].startswith('attachment; filename='))
        
        # Check CSV content
        content = response.content.decode('utf-8')
        self.assertIn('شناسه', content)  # CSV header
        self.assertIn('تاریخ و زمان', content)
        self.assertIn('کاربر', content)
    
    def test_audit_log_export_json(self):
        """Test JSON export functionality."""
        url = reverse('admin_panel:audit_log_export')
        response = self.client.get(url, {'format': 'json'})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json; charset=utf-8')
        self.assertTrue(response['Content-Disposition'].startswith('attachment; filename='))
        
        # Check JSON content
        content = json.loads(response.content.decode('utf-8'))
        self.assertIn('export_info', content)
        self.assertIn('audit_logs', content)
        self.assertIsInstance(content['audit_logs'], list)
    
    def test_audit_log_export_with_filters(self):
        """Test export functionality with filters applied."""
        url = reverse('admin_panel:audit_log_export')
        response = self.client.get(url, {
            'format': 'csv',
            'action': 'create',
            'username': 'testadmin'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
    
    def test_audit_log_search_api(self):
        """Test audit log search API functionality."""
        url = reverse('admin_panel:audit_log_search_api')
        response = self.client.get(url, {'q': 'Test Object'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertIn('results', data)
        self.assertIn('pagination', data)
        self.assertIn('search_metadata', data)
        
        # Check result structure
        if data['results']:
            result = data['results'][0]
            self.assertIn('id', result)
            self.assertIn('created_at', result)
            self.assertIn('user_username', result)
            self.assertIn('action', result)
            self.assertIn('integrity_status', result)
    
    def test_audit_log_stats_api(self):
        """Test audit log statistics API."""
        url = reverse('admin_panel:audit_log_stats_api')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertIn('statistics', data)
        
        stats = data['statistics']
        self.assertIn('total_logs', stats)
        self.assertIn('recent_logs', stats)
        self.assertIn('action_breakdown', stats)
        self.assertIn('user_activity', stats)
        self.assertIn('tenant_activity', stats)
        self.assertIn('daily_trend', stats)
        self.assertIn('integrity_stats', stats)
    
    def test_audit_log_integrity_check(self):
        """Test bulk integrity check functionality."""
        url = reverse('admin_panel:audit_log_integrity_check')
        
        # Test checking specific logs
        log_ids = [log.id for log in self.audit_logs[:3]]
        response = self.client.post(
            url,
            json.dumps({'log_ids': log_ids}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertIn('results', data)
        
        results = data['results']
        self.assertIn('total_checked', results)
        self.assertIn('verified', results)
        self.assertIn('compromised', results)
        self.assertIn('no_checksum', results)
        self.assertIn('errors', results)
    
    def test_navigation_integration(self):
        """Test that audit logs are accessible from navigation."""
        # Test main dashboard has security section
        dashboard_url = reverse('admin_panel:dashboard')
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, 200)
        
        # Test that audit logs link is in navigation
        audit_logs_url = reverse('admin_panel:audit_logs')
        response = self.client.get(audit_logs_url)
        self.assertEqual(response.status_code, 200)
        
        # Check that navigation includes security section
        self.assertContains(response, 'امنیت و حسابرسی')
        self.assertContains(response, 'لاگ‌های حسابرسی')
    
    def test_theme_support(self):
        """Test that audit log interface supports dual theme."""
        url = reverse('admin_panel:audit_logs')
        response = self.client.get(url)
        
        # Check for theme-related CSS classes
        self.assertContains(response, 'dark:bg-cyber-bg-')
        self.assertContains(response, 'dark:text-cyber-text-')
        self.assertContains(response, 'dark:border-cyber-neon-')
        
        # Check for theme toggle functionality
        self.assertContains(response, 'darkMode')
        
        # Check for cybersecurity styling elements
        self.assertContains(response, 'cyber-neon-')
        self.assertContains(response, 'glass-effect')
    
    def test_persian_rtl_layout(self):
        """Test Persian RTL layout support."""
        url = reverse('admin_panel:audit_logs')
        response = self.client.get(url)
        
        # Check RTL direction
        self.assertContains(response, 'dir="rtl"')
        
        # Check Persian font
        self.assertContains(response, 'font-vazir')
        
        # Check Persian text content
        self.assertContains(response, 'لاگ‌های حسابرسی')
        self.assertContains(response, 'فیلترهای پیشرفته')
        self.assertContains(response, 'وضعیت یکپارچگی')
        
        # Check Persian number formatting
        self.assertContains(response, 'persian-numbers')
    
    def test_mobile_responsiveness(self):
        """Test mobile responsiveness of audit log interface."""
        url = reverse('admin_panel:audit_logs')
        response = self.client.get(url)
        
        # Check responsive grid classes
        self.assertContains(response, 'grid-cols-1')
        self.assertContains(response, 'md:grid-cols-')
        self.assertContains(response, 'lg:grid-cols-')
        
        # Check responsive table
        self.assertContains(response, 'overflow-x-auto')
        
        # Check mobile-specific elements
        self.assertContains(response, 'sm:hidden')
        self.assertContains(response, 'hidden sm:flex')
    
    def test_error_handling(self):
        """Test error handling in audit log views."""
        # Test non-existent log detail
        url = reverse('admin_panel:audit_log_detail', kwargs={'log_id': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        
        # Test invalid export format
        export_url = reverse('admin_panel:audit_log_export')
        response = self.client.get(export_url, {'format': 'invalid'})
        self.assertEqual(response.status_code, 400)
        
        # Test search API with invalid parameters
        search_url = reverse('admin_panel:audit_log_search_api')
        response = self.client.get(search_url, {'page': 'invalid'})
        self.assertEqual(response.status_code, 200)  # Should handle gracefully
    
    def test_security_access_control(self):
        """Test that audit log views require proper authentication."""
        # Logout
        self.client.logout()
        
        # Test audit logs list view
        url = reverse('admin_panel:audit_logs')
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)  # Should redirect or deny
        
        # Test audit log detail view
        log = self.audit_logs[0]
        detail_url = reverse('admin_panel:audit_log_detail', kwargs={'log_id': log.id})
        response = self.client.get(detail_url)
        self.assertNotEqual(response.status_code, 200)  # Should redirect or deny
        
        # Test export view
        export_url = reverse('admin_panel:audit_log_export')
        response = self.client.get(export_url)
        self.assertNotEqual(response.status_code, 200)  # Should redirect or deny
    
    def test_performance_with_large_dataset(self):
        """Test performance with large audit log dataset."""
        # Create a large number of audit logs
        logs_to_create = []
        for i in range(1000):
            logs_to_create.append(PublicAuditLog(
                user_id=self.super_admin.id,
                user_username=f'user_{i}',
                action='create',
                model_name='TestModel',
                object_id=str(i),
                object_repr=f'Performance Test Object {i}',
                ip_address='192.168.1.1',
                tenant_schema='performance_test'
            ))
        
        PublicAuditLog.objects.bulk_create(logs_to_create)
        
        # Test list view performance
        url = reverse('admin_panel:audit_logs')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Test filtered view performance
        response = self.client.get(url, {'tenant_schema': 'performance_test'})
        self.assertEqual(response.status_code, 200)
        
        # Test search performance
        response = self.client.get(url, {'search': 'Performance Test'})
        self.assertEqual(response.status_code, 200)


class AuditLogServiceIntegrationTestCase(TestCase):
    """Integration tests for audit log services with frontend."""
    
    def setUp(self):
        """Set up test data."""
        self.super_admin = SuperAdmin.objects.create_user(
            username='servicetest',
            email='service@test.com',
            password='testpass123'
        )
        
        # Create test audit logs with various scenarios
        self.test_logs = []
        
        # Log with checksum (verified)
        log1 = PublicAuditLog.objects.create(
            user_id=self.super_admin.id,
            user_username=self.super_admin.username,
            action='create',
            model_name='TestModel',
            object_repr='Verified Log',
            checksum='valid_checksum_123'
        )
        self.test_logs.append(log1)
        
        # Log without checksum
        log2 = PublicAuditLog.objects.create(
            user_id=self.super_admin.id,
            user_username=self.super_admin.username,
            action='update',
            model_name='TestModel',
            object_repr='Unverified Log',
            checksum=''
        )
        self.test_logs.append(log2)
        
        # Log with changes
        log3 = PublicAuditLog.objects.create(
            user_id=self.super_admin.id,
            user_username=self.super_admin.username,
            action='update',
            model_name='TestModel',
            object_repr='Changed Log',
            old_values={'name': 'old_name', 'status': 'inactive'},
            new_values={'name': 'new_name', 'status': 'active'},
            changes={'name': ['old_name', 'new_name'], 'status': ['inactive', 'active']}
        )
        self.test_logs.append(log3)
    
    def test_filter_service_integration(self):
        """Test filter service integration with frontend."""
        filter_service = AuditLogFilterService()
        
        # Test getting filter options
        options = filter_service.get_filter_options()
        self.assertIn('action_types', options)
        self.assertIn('model_names', options)
        self.assertIn('tenant_schemas', options)
        
        # Test filtering
        filters = {'action': 'create'}
        queryset = filter_service.get_filtered_queryset(filters)
        self.assertTrue(queryset.exists())
        
        # Test search filtering
        filters = {'search': 'Verified'}
        queryset = filter_service.get_filtered_queryset(filters)
        self.assertTrue(queryset.exists())
    
    def test_detail_service_integration(self):
        """Test detail service integration with frontend."""
        detail_service = AuditLogDetailService()
        
        # Test getting log detail
        log = self.test_logs[0]
        detail_info = detail_service.get_audit_log_detail(log.id)
        
        self.assertIsNotNone(detail_info)
        self.assertIn('log_entry', detail_info)
        self.assertIn('integrity_status', detail_info)
        self.assertIn('formatted_changes', detail_info)
        
        # Test integrity verification
        integrity_status = detail_service.verify_log_integrity(log)
        self.assertIn('status', integrity_status)
        self.assertIn('message', integrity_status)
        self.assertIn('is_valid', integrity_status)
        
        # Test changes formatting
        log_with_changes = self.test_logs[2]
        formatted_changes = detail_service.format_changes(log_with_changes)
        self.assertIn('has_changes', formatted_changes)
        self.assertIn('field_changes', formatted_changes)
    
    def test_export_service_integration(self):
        """Test export service integration with frontend."""
        export_service = AuditLogExportService()
        queryset = PublicAuditLog.objects.all()
        
        # Test export statistics
        stats = export_service.get_export_statistics(queryset)
        self.assertIn('total_count', stats)
        self.assertIn('action_breakdown', stats)
        self.assertIn('integrity_stats', stats)
        
        # Test CSV export (mock response)
        csv_response = export_service.export_to_csv(queryset)
        self.assertEqual(csv_response['Content-Type'], 'text/csv; charset=utf-8')
        
        # Test JSON export (mock response)
        json_response = export_service.export_to_json(queryset)
        self.assertEqual(json_response['Content-Type'], 'application/json; charset=utf-8')


if __name__ == '__main__':
    pytest.main([__file__])