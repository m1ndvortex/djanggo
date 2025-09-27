"""
Unit tests for audit log management backend functionality.
Tests the audit log filtering, searching, export, and integrity verification services.
"""

import pytest
from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from datetime import datetime, timedelta
import json
import csv
import io

from zargar.tenants.admin_models import PublicAuditLog
from zargar.admin_panel.audit_services import (
    AuditLogFilterService,
    AuditLogDetailService,
    AuditLogExportService,
    AuditLogSearchService
)
from zargar.admin_panel.audit_views import (
    AuditLogListView,
    AuditLogDetailView,
    AuditLogExportView,
    AuditLogSearchAPIView,
    AuditLogIntegrityCheckView,
    AuditLogStatsAPIView
)


class AuditLogFilterServiceTest(TestCase):
    """Test AuditLogFilterService functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.service = AuditLogFilterService()
        
        # Create test audit logs
        self.log1 = PublicAuditLog.objects.create(
            action='create',
            user_id=1,
            user_username='testuser1',
            model_name='TestModel',
            object_id='123',
            object_repr='Test Object 1',
            ip_address='192.168.1.1',
            tenant_schema='tenant1',
            request_path='/test/path/',
            request_method='POST',
            details={'test': 'data1'},
            checksum='test_checksum_1'
        )
        
        self.log2 = PublicAuditLog.objects.create(
            action='update',
            user_id=2,
            user_username='testuser2',
            model_name='AnotherModel',
            object_id='456',
            object_repr='Test Object 2',
            ip_address='192.168.1.2',
            tenant_schema='tenant2',
            request_path='/another/path/',
            request_method='PUT',
            details={'test': 'data2'},
            old_values={'field1': 'old_value'},
            new_values={'field1': 'new_value'},
            checksum='test_checksum_2'
        )
        
        self.log3 = PublicAuditLog.objects.create(
            action='delete',
            user_id=1,
            user_username='testuser1',
            model_name='TestModel',
            object_id='789',
            object_repr='Test Object 3',
            ip_address='192.168.1.1',
            tenant_schema='tenant1',
            request_path='/delete/path/',
            request_method='DELETE',
            details={'test': 'data3'},
            checksum=''  # No checksum for testing integrity
        )
    
    def test_filter_by_action(self):
        """Test filtering by action type."""
        filters = {'action': 'create'}
        queryset = self.service.get_filtered_queryset(filters)
        
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().id, self.log1.id)
    
    def test_filter_by_user_id(self):
        """Test filtering by user ID."""
        filters = {'user_id': '1'}
        queryset = self.service.get_filtered_queryset(filters)
        
        self.assertEqual(queryset.count(), 2)
        user_ids = [log.user_id for log in queryset]
        self.assertIn(1, user_ids)
    
    def test_filter_by_username(self):
        """Test filtering by username."""
        filters = {'username': 'testuser2'}
        queryset = self.service.get_filtered_queryset(filters)
        
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().user_username, 'testuser2')
    
    def test_filter_by_model_name(self):
        """Test filtering by model name."""
        filters = {'model_name': 'TestModel'}
        queryset = self.service.get_filtered_queryset(filters)
        
        self.assertEqual(queryset.count(), 2)
        for log in queryset:
            self.assertIn('TestModel', log.model_name)
    
    def test_filter_by_tenant_schema(self):
        """Test filtering by tenant schema."""
        filters = {'tenant_schema': 'tenant1'}
        queryset = self.service.get_filtered_queryset(filters)
        
        self.assertEqual(queryset.count(), 2)
        for log in queryset:
            self.assertEqual(log.tenant_schema, 'tenant1')
    
    def test_filter_by_ip_address(self):
        """Test filtering by IP address."""
        filters = {'ip_address': '192.168.1.2'}
        queryset = self.service.get_filtered_queryset(filters)
        
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().ip_address, '192.168.1.2')
    
    def test_filter_by_date_range(self):
        """Test filtering by date range."""
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        filters = {
            'date_from': yesterday.strftime('%Y-%m-%d'),
            'date_to': today.strftime('%Y-%m-%d')
        }
        queryset = self.service.get_filtered_queryset(filters)
        
        # Should return all logs created today
        self.assertEqual(queryset.count(), 3)
    
    def test_search_functionality(self):
        """Test search across multiple fields."""
        filters = {'search': 'testuser1'}
        queryset = self.service.get_filtered_queryset(filters)
        
        self.assertEqual(queryset.count(), 2)
        for log in queryset:
            self.assertEqual(log.user_username, 'testuser1')
    
    def test_integrity_status_filter(self):
        """Test filtering by integrity status."""
        filters = {'integrity_status': 'compromised'}
        queryset = self.service.get_filtered_queryset(filters)
        
        # Should return logs without checksum
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().checksum, '')
    
    def test_multiple_filters(self):
        """Test applying multiple filters simultaneously."""
        filters = {
            'action': 'create',
            'user_id': '1',
            'tenant_schema': 'tenant1'
        }
        queryset = self.service.get_filtered_queryset(filters)
        
        self.assertEqual(queryset.count(), 1)
        log = queryset.first()
        self.assertEqual(log.action, 'create')
        self.assertEqual(log.user_id, 1)
        self.assertEqual(log.tenant_schema, 'tenant1')
    
    def test_get_filter_options(self):
        """Test getting available filter options."""
        options = self.service.get_filter_options()
        
        self.assertIn('action_types', options)
        self.assertIn('model_names', options)
        self.assertIn('tenant_schemas', options)
        self.assertIn('users', options)
        
        # Check that our test data is included
        self.assertIn('create', options['action_types'])
        self.assertIn('update', options['action_types'])
        self.assertIn('delete', options['action_types'])
        
        self.assertIn('TestModel', options['model_names'])
        self.assertIn('AnotherModel', options['model_names'])
        
        self.assertIn('tenant1', options['tenant_schemas'])
        self.assertIn('tenant2', options['tenant_schemas'])


class AuditLogDetailServiceTest(TestCase):
    """Test AuditLogDetailService functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.service = AuditLogDetailService()
        
        # Create test audit log with changes
        self.log_with_changes = PublicAuditLog.objects.create(
            action='update',
            user_id=1,
            user_username='testuser',
            model_name='TestModel',
            object_id='123',
            object_repr='Test Object',
            ip_address='192.168.1.1',
            old_values={'field1': 'old_value', 'field2': 'unchanged'},
            new_values={'field1': 'new_value', 'field2': 'unchanged'},
            changes={'field1': {'old': 'old_value', 'new': 'new_value'}},
            checksum='valid_checksum'
        )
        
        # Create log without checksum
        self.log_no_checksum = PublicAuditLog.objects.create(
            action='create',
            user_id=1,
            user_username='testuser',
            model_name='TestModel',
            object_id='456',
            object_repr='Test Object 2',
            ip_address='192.168.1.1',
            checksum=''
        )
    
    def test_get_audit_log_detail_success(self):
        """Test successful retrieval of audit log details."""
        detail = self.service.get_audit_log_detail(self.log_with_changes.id)
        
        self.assertIsNotNone(detail)
        self.assertIn('log_entry', detail)
        self.assertIn('integrity_status', detail)
        self.assertIn('formatted_changes', detail)
        self.assertIn('related_logs', detail)
        self.assertIn('has_before_after', detail)
        
        self.assertEqual(detail['log_entry'].id, self.log_with_changes.id)
        self.assertTrue(detail['has_before_after'])
    
    def test_get_audit_log_detail_not_found(self):
        """Test handling of non-existent audit log."""
        detail = self.service.get_audit_log_detail(99999)
        self.assertIsNone(detail)
    
    def test_verify_log_integrity_no_checksum(self):
        """Test integrity verification for log without checksum."""
        status = self.service.verify_log_integrity(self.log_no_checksum)
        
        self.assertEqual(status['status'], 'no_checksum')
        self.assertFalse(status['is_valid'])
        self.assertEqual(status['color'], 'warning')
    
    def test_format_changes_with_data(self):
        """Test formatting changes when data is present."""
        formatted = self.service.format_changes(self.log_with_changes)
        
        self.assertTrue(formatted['has_changes'])
        self.assertGreater(len(formatted['field_changes']), 0)
        self.assertIn('old_values_json', formatted)
        self.assertIn('new_values_json', formatted)
        
        # Check field changes
        field_changes = formatted['field_changes']
        field1_change = next((fc for fc in field_changes if fc['field'] == 'field1'), None)
        self.assertIsNotNone(field1_change)
        self.assertTrue(field1_change['is_changed'])
        self.assertEqual(field1_change['old_value'], 'old_value')
        self.assertEqual(field1_change['new_value'], 'new_value')
    
    def test_format_changes_no_data(self):
        """Test formatting changes when no change data is present."""
        formatted = self.service.format_changes(self.log_no_checksum)
        
        self.assertFalse(formatted['has_changes'])
        self.assertEqual(len(formatted['field_changes']), 0)
    
    def test_get_related_logs(self):
        """Test getting related audit logs."""
        # Create a related log (same object, close time)
        related_log = PublicAuditLog.objects.create(
            action='read',
            user_id=1,
            user_username='testuser',
            model_name='TestModel',
            object_id='123',  # Same object as log_with_changes
            object_repr='Test Object',
            ip_address='192.168.1.1',
            content_type=self.log_with_changes.content_type
        )
        
        related_logs = self.service.get_related_logs(self.log_with_changes)
        
        self.assertGreater(len(related_logs), 0)
        # Should not include the original log
        related_ids = [log.id for log in related_logs]
        self.assertNotIn(self.log_with_changes.id, related_ids)


class AuditLogExportServiceTest(TestCase):
    """Test AuditLogExportService functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.service = AuditLogExportService()
        
        # Create test audit logs
        self.log1 = PublicAuditLog.objects.create(
            action='create',
            user_id=1,
            user_username='testuser1',
            model_name='TestModel',
            object_id='123',
            object_repr='Test Object 1',
            ip_address='192.168.1.1',
            tenant_schema='tenant1',
            request_path='/test/',
            request_method='POST',
            details={'key': 'value'},
            checksum='checksum1'
        )
        
        self.log2 = PublicAuditLog.objects.create(
            action='update',
            user_id=2,
            user_username='testuser2',
            model_name='TestModel',
            object_id='456',
            object_repr='Test Object 2',
            ip_address='192.168.1.2',
            tenant_schema='tenant2',
            request_path='/test/',
            request_method='PUT',
            checksum='checksum2'
        )
    
    def test_export_to_csv(self):
        """Test CSV export functionality."""
        queryset = PublicAuditLog.objects.all()
        response = self.service.export_to_csv(queryset, 'test_export.csv')
        
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('test_export.csv', response['Content-Disposition'])
        
        # Check CSV content
        content = response.content.decode('utf-8-sig')
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)
        
        # Should have header + 2 data rows
        self.assertEqual(len(rows), 3)
        
        # Check headers (in Persian)
        headers = rows[0]
        self.assertIn('شناسه', headers)
        self.assertIn('تاریخ و زمان', headers)
        self.assertIn('کاربر', headers)
        
        # Check data rows
        self.assertEqual(rows[1][0], str(self.log1.id))  # First log ID
        self.assertEqual(rows[2][0], str(self.log2.id))  # Second log ID
    
    def test_export_to_json(self):
        """Test JSON export functionality."""
        queryset = PublicAuditLog.objects.all()
        response = self.service.export_to_json(queryset, 'test_export.json')
        
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response['Content-Type'], 'application/json; charset=utf-8')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('test_export.json', response['Content-Disposition'])
        
        # Check JSON content
        content = response.content.decode('utf-8')
        data = json.loads(content)
        
        self.assertIn('export_info', data)
        self.assertIn('audit_logs', data)
        
        # Check export info
        export_info = data['export_info']
        self.assertEqual(export_info['total_records'], 2)
        self.assertEqual(export_info['format'], 'json')
        
        # Check audit logs
        audit_logs = data['audit_logs']
        self.assertEqual(len(audit_logs), 2)
        
        # Check first log data
        first_log = audit_logs[0]
        self.assertEqual(first_log['id'], self.log1.id)
        self.assertEqual(first_log['action'], 'create')
        self.assertEqual(first_log['user_username'], 'testuser1')
        self.assertIn('integrity_status', first_log)
    
    def test_get_export_statistics(self):
        """Test export statistics calculation."""
        queryset = PublicAuditLog.objects.all()
        stats = self.service.get_export_statistics(queryset)
        
        self.assertIn('total_count', stats)
        self.assertIn('action_breakdown', stats)
        self.assertIn('user_breakdown', stats)
        self.assertIn('tenant_breakdown', stats)
        self.assertIn('time_range', stats)
        self.assertIn('integrity_stats', stats)
        
        self.assertEqual(stats['total_count'], 2)
        
        # Check action breakdown
        action_breakdown = stats['action_breakdown']
        actions = [item['action'] for item in action_breakdown]
        self.assertIn('create', actions)
        self.assertIn('update', actions)
        
        # Check integrity stats
        integrity_stats = stats['integrity_stats']
        self.assertEqual(integrity_stats['logs_with_checksum'], 2)
        self.assertEqual(integrity_stats['logs_without_checksum'], 0)
        self.assertEqual(integrity_stats['integrity_percentage'], 100.0)


class AuditLogSearchServiceTest(TestCase):
    """Test AuditLogSearchService functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.service = AuditLogSearchService()
        
        # Create test audit logs
        self.log1 = PublicAuditLog.objects.create(
            action='create',
            user_id=1,
            user_username='admin_user',
            model_name='UserModel',
            object_id='123',
            object_repr='Admin User Object',
            ip_address='192.168.1.1',
            tenant_schema='admin_tenant',
            request_path='/admin/users/',
            details={'role': 'admin'}
        )
        
        self.log2 = PublicAuditLog.objects.create(
            action='update',
            user_id=2,
            user_username='regular_user',
            model_name='ProductModel',
            object_id='456',
            object_repr='Product Object',
            ip_address='192.168.1.2',
            tenant_schema='shop_tenant',
            request_path='/shop/products/',
            details={'category': 'jewelry'}
        )
    
    def test_advanced_search_full_text(self):
        """Test full-text search functionality."""
        search_params = {'q': 'admin'}
        queryset, metadata = self.service.advanced_search(search_params)
        
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().user_username, 'admin_user')
        
        # Check metadata
        self.assertIn('admin', metadata['search_terms_used'])
        self.assertIn('full_text_search', metadata['filters_applied'])
        self.assertEqual(metadata['total_after_search'], 1)
    
    def test_advanced_search_with_filters(self):
        """Test search with additional filters."""
        search_params = {
            'q': 'user',
            'action': 'create',
            'tenant_schema': 'admin_tenant'
        }
        queryset, metadata = self.service.advanced_search(search_params)
        
        self.assertEqual(queryset.count(), 1)
        log = queryset.first()
        self.assertEqual(log.action, 'create')
        self.assertEqual(log.tenant_schema, 'admin_tenant')
        
        # Check metadata
        self.assertIn('user', metadata['search_terms_used'])
        self.assertIn('full_text_search', metadata['filters_applied'])
        self.assertIn('action', metadata['filters_applied'])
        self.assertIn('tenant_schema', metadata['filters_applied'])
    
    def test_advanced_search_no_results(self):
        """Test search with no matching results."""
        search_params = {'q': 'nonexistent_term'}
        queryset, metadata = self.service.advanced_search(search_params)
        
        self.assertEqual(queryset.count(), 0)
        self.assertEqual(metadata['total_after_search'], 0)
        self.assertGreater(metadata['results_filtered'], 0)
    
    def test_advanced_search_empty_params(self):
        """Test search with empty parameters."""
        search_params = {}
        queryset, metadata = self.service.advanced_search(search_params)
        
        # Should return all logs
        self.assertEqual(queryset.count(), 2)
        self.assertEqual(len(metadata['search_terms_used']), 0)
        self.assertEqual(metadata['results_filtered'], 0)


class AuditLogViewsTest(TestCase):
    """Test audit log management views."""
    
    def setUp(self):
        """Set up test data and request factory."""
        self.factory = RequestFactory()
        
        # Create test audit log
        self.log = PublicAuditLog.objects.create(
            action='create',
            user_id=1,
            user_username='testuser',
            model_name='TestModel',
            object_id='123',
            object_repr='Test Object',
            ip_address='192.168.1.1',
            tenant_schema='test_tenant',
            checksum='test_checksum'
        )
    
    def test_audit_log_list_view_queryset(self):
        """Test audit log list view queryset filtering."""
        request = self.factory.get('/admin-panel/security/audit-logs/', {
            'action': 'create',
            'user_id': '1'
        })
        
        view = AuditLogListView()
        view.request = request
        queryset = view.get_queryset()
        
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().id, self.log.id)
    
    def test_audit_log_detail_view_object(self):
        """Test audit log detail view object retrieval."""
        view = AuditLogDetailView()
        view.kwargs = {'log_id': self.log.id}
        
        obj = view.get_object()
        self.assertEqual(obj.id, self.log.id)
    
    def test_audit_log_search_api_response_structure(self):
        """Test audit log search API response structure."""
        request = self.factory.get('/admin-panel/security/audit-logs/search/api/', {
            'q': 'test',
            'page': '1'
        })
        
        view = AuditLogSearchAPIView()
        view.request = request
        
        # Mock the SuperAdminRequiredMixin check
        view.dispatch = lambda req: view.get(req)
        
        response = view.get(request)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('success', data)
        self.assertIn('results', data)
        self.assertIn('pagination', data)
        self.assertIn('search_metadata', data)


@pytest.mark.django_db
class TestAuditLogManagementIntegration:
    """Integration tests for audit log management functionality."""
    
    def test_full_audit_log_workflow(self):
        """Test complete audit log management workflow."""
        # Create test data
        log = PublicAuditLog.objects.create(
            action='update',
            user_id=1,
            user_username='testuser',
            model_name='TestModel',
            object_id='123',
            object_repr='Test Object',
            ip_address='192.168.1.1',
            tenant_schema='test_tenant',
            old_values={'field1': 'old'},
            new_values={'field1': 'new'},
            checksum='test_checksum'
        )
        
        # Test filtering
        filter_service = AuditLogFilterService()
        filtered_queryset = filter_service.get_filtered_queryset({'action': 'update'})
        assert filtered_queryset.count() == 1
        
        # Test detail retrieval
        detail_service = AuditLogDetailService()
        detail = detail_service.get_audit_log_detail(log.id)
        assert detail is not None
        assert detail['has_before_after'] is True
        
        # Test export
        export_service = AuditLogExportService()
        csv_response = export_service.export_to_csv(filtered_queryset)
        assert csv_response.status_code == 200
        assert 'text/csv' in csv_response['Content-Type']
        
        json_response = export_service.export_to_json(filtered_queryset)
        assert json_response.status_code == 200
        assert 'application/json' in json_response['Content-Type']
        
        # Test search
        search_service = AuditLogSearchService()
        search_queryset, metadata = search_service.advanced_search({'q': 'testuser'})
        assert search_queryset.count() == 1
        assert 'testuser' in metadata['search_terms_used']
    
    def test_integrity_verification_workflow(self):
        """Test integrity verification workflow."""
        # Create log with valid checksum
        valid_log = PublicAuditLog.objects.create(
            action='create',
            user_id=1,
            user_username='testuser',
            model_name='TestModel',
            object_id='123',
            checksum='valid_checksum'
        )
        
        # Create log without checksum
        invalid_log = PublicAuditLog.objects.create(
            action='create',
            user_id=1,
            user_username='testuser',
            model_name='TestModel',
            object_id='456',
            checksum=''
        )
        
        detail_service = AuditLogDetailService()
        
        # Test valid log
        valid_status = detail_service.verify_log_integrity(valid_log)
        assert valid_status['status'] in ['verified', 'compromised']  # Depends on actual checksum validation
        
        # Test invalid log
        invalid_status = detail_service.verify_log_integrity(invalid_log)
        assert invalid_status['status'] == 'no_checksum'
        assert invalid_status['is_valid'] is False
    
    def test_export_statistics_accuracy(self):
        """Test export statistics calculation accuracy."""
        # Create diverse test data
        PublicAuditLog.objects.create(
            action='create',
            user_id=1,
            user_username='user1',
            tenant_schema='tenant1',
            checksum='checksum1'
        )
        
        PublicAuditLog.objects.create(
            action='update',
            user_id=2,
            user_username='user2',
            tenant_schema='tenant1',
            checksum='checksum2'
        )
        
        PublicAuditLog.objects.create(
            action='create',
            user_id=1,
            user_username='user1',
            tenant_schema='tenant2',
            checksum=''  # No checksum
        )
        
        export_service = AuditLogExportService()
        queryset = PublicAuditLog.objects.all()
        stats = export_service.get_export_statistics(queryset)
        
        assert stats['total_count'] == 3
        assert stats['integrity_stats']['logs_with_checksum'] == 2
        assert stats['integrity_stats']['logs_without_checksum'] == 1
        assert stats['integrity_stats']['integrity_percentage'] == 66.67
        
        # Check action breakdown
        action_counts = {item['action']: item['count'] for item in stats['action_breakdown']}
        assert action_counts['create'] == 2
        assert action_counts['update'] == 1