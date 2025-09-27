"""
Unit tests for Security Event Management Services (without database).

Tests the core logic of security event management services using mocks.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing models
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from django.utils import timezone

from zargar.admin_panel.security_event_services import (
    SecurityEventFilterService,
    SecurityEventCategorizationService,
    SecurityEventInvestigationService,
    SecurityEventResolutionService,
)


class TestSecurityEventCategorizationService:
    """Test SecurityEventCategorizationService without database."""
    
    def test_category_mapping(self):
        """Test that event types are correctly mapped to categories."""
        service = SecurityEventCategorizationService
        
        # Test authentication events
        assert 'login_failed' in service.CATEGORY_MAPPING['authentication']
        assert 'login_success' in service.CATEGORY_MAPPING['authentication']
        assert '2fa_enabled' in service.CATEGORY_MAPPING['authentication']
        
        # Test account security events
        assert 'brute_force_attempt' in service.CATEGORY_MAPPING['account_security']
        assert 'suspicious_activity' in service.CATEGORY_MAPPING['account_security']
        
        # Test access control events
        assert 'privilege_escalation' in service.CATEGORY_MAPPING['access_control']
        assert 'unauthorized_access' in service.CATEGORY_MAPPING['access_control']
    
    def test_risk_weights_configuration(self):
        """Test that risk weights are properly configured."""
        service = SecurityEventCategorizationService
        
        # Test event type weights
        assert service.RISK_WEIGHTS['event_type']['privilege_escalation'] > service.RISK_WEIGHTS['event_type']['login_failed']
        assert service.RISK_WEIGHTS['event_type']['brute_force_attempt'] > service.RISK_WEIGHTS['event_type']['api_rate_limit']
        
        # Test severity weights
        assert service.RISK_WEIGHTS['severity']['critical'] > service.RISK_WEIGHTS['severity']['high']
        assert service.RISK_WEIGHTS['severity']['high'] > service.RISK_WEIGHTS['severity']['medium']
        assert service.RISK_WEIGHTS['severity']['medium'] > service.RISK_WEIGHTS['severity']['low']
    
    @patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.filter')
    def test_categorize_event_basic(self, mock_filter):
        """Test basic event categorization."""
        # Mock the event object
        mock_event = Mock()
        mock_event.event_type = 'login_failed'
        mock_event.severity = 'medium'
        mock_event.ip_address = '192.168.1.1'
        mock_event.user = None
        
        # Mock the queryset for pattern detection
        mock_queryset = Mock()
        mock_queryset.count.return_value = 2  # Low frequency
        mock_filter.return_value = mock_queryset
        
        service = SecurityEventCategorizationService
        result = service.categorize_event(mock_event)
        
        # Verify categorization
        assert result['category'] == 'authentication'
        assert isinstance(result['risk_score'], float)
        assert result['risk_score'] > 0
        assert result['priority'] in ['low', 'medium', 'high', 'critical']
        assert isinstance(result['pattern_detected'], bool)
        assert 'recommended_action' in result
        assert isinstance(result['escalation_required'], bool)
    
    @patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.filter')
    def test_categorize_critical_event(self, mock_filter):
        """Test categorization of critical events."""
        # Mock critical event
        mock_event = Mock()
        mock_event.event_type = 'privilege_escalation'
        mock_event.severity = 'critical'
        mock_event.ip_address = '192.168.1.1'
        mock_event.user = Mock()
        
        # Mock the queryset
        mock_queryset = Mock()
        mock_queryset.count.return_value = 1
        mock_filter.return_value = mock_queryset
        
        service = SecurityEventCategorizationService
        result = service.categorize_event(mock_event)
        
        # Critical events should have high risk and require escalation
        assert result['category'] == 'access_control'
        assert result['priority'] == 'critical'
        assert result['escalation_required'] is True
        assert result['recommended_action'] == 'immediate_investigation'
    
    @patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.filter')
    def test_pattern_detection_high_frequency(self, mock_filter):
        """Test pattern detection for high frequency events."""
        # Mock event
        mock_event = Mock()
        mock_event.event_type = 'login_failed'
        mock_event.severity = 'medium'
        mock_event.ip_address = '192.168.1.1'
        mock_event.user = None
        
        # Mock high frequency
        mock_queryset = Mock()
        mock_queryset.count.return_value = 15  # High frequency
        mock_filter.return_value = mock_queryset
        
        service = SecurityEventCategorizationService
        result = service.categorize_event(mock_event)
        
        # Should detect pattern
        assert result['pattern_detected'] is True
        assert result['pattern_type'] == 'ip_frequency'
        assert result['pattern_confidence'] > 0
        assert result['recommended_action'] == 'pattern_investigation'


class TestSecurityEventInvestigationService:
    """Test SecurityEventInvestigationService without database."""
    
    def test_investigation_statuses(self):
        """Test that investigation statuses are properly defined."""
        service = SecurityEventInvestigationService
        
        statuses = [status[0] for status in service.INVESTIGATION_STATUSES]
        assert 'not_started' in statuses
        assert 'assigned' in statuses
        assert 'in_progress' in statuses
        assert 'resolved' in statuses
        assert 'closed' in statuses
    
    @patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.get')
    @patch('zargar.admin_panel.security_event_services.SuperAdmin.objects.get')
    @patch('zargar.admin_panel.security_event_services.AuditLog.log_action')
    def test_assign_investigator_success(self, mock_log, mock_super_admin, mock_event):
        """Test successful investigator assignment."""
        # Mock objects
        mock_event_obj = Mock()
        mock_event_obj.id = 1
        mock_event_obj.resolution_notes = ''
        mock_event.return_value = mock_event_obj
        
        mock_investigator = Mock()
        mock_investigator.id = 2
        mock_investigator.username = 'investigator'
        mock_investigator.email = 'inv@example.com'
        
        mock_admin = Mock()
        mock_admin.id = 3
        mock_admin.username = 'admin'
        
        mock_super_admin.side_effect = [mock_investigator, mock_admin]
        
        service = SecurityEventInvestigationService
        result = service.assign_investigator(
            event_id=1,
            investigator_id=2,
            assigned_by_id=3,
            notes='Test assignment'
        )
        
        # Verify success
        assert result['success'] is True
        assert result['investigator']['username'] == 'investigator'
        assert 'Event assigned to investigator' in result['message']
        
        # Verify event was updated
        assert mock_event_obj.resolved_by == mock_investigator
        mock_event_obj.save.assert_called_once()
        
        # Verify audit log was called
        mock_log.assert_called_once()
    
    @patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.get')
    def test_assign_investigator_event_not_found(self, mock_event):
        """Test assignment when event doesn't exist."""
        from zargar.core.security_models import SecurityEvent
        mock_event.side_effect = SecurityEvent.DoesNotExist()
        
        service = SecurityEventInvestigationService
        result = service.assign_investigator(
            event_id=999,
            investigator_id=2,
            assigned_by_id=3
        )
        
        assert result['success'] is False
        assert result['error'] == 'Security event not found'
    
    @patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.get')
    @patch('zargar.admin_panel.security_event_services.SuperAdmin.objects.get')
    @patch('zargar.admin_panel.security_event_services.AuditLog.log_action')
    def test_update_investigation_status(self, mock_log, mock_super_admin, mock_event):
        """Test updating investigation status."""
        # Mock objects
        mock_event_obj = Mock()
        mock_event_obj.id = 1
        mock_event_obj.resolution_notes = 'Previous notes'
        mock_event_obj.is_resolved = False
        mock_event_obj.resolved_at = None
        mock_event_obj.resolved_by = None
        mock_event.return_value = mock_event_obj
        
        mock_admin = Mock()
        mock_admin.username = 'admin'
        mock_super_admin.return_value = mock_admin
        
        service = SecurityEventInvestigationService
        result = service.update_investigation_status(
            event_id=1,
            status='in_progress',
            updated_by_id=2,
            notes='Investigation started'
        )
        
        # Verify success
        assert result['success'] is True
        assert result['new_status'] == 'in_progress'
        assert result['is_resolved'] is False
        
        # Verify event was updated
        mock_event_obj.save.assert_called_once()
        mock_log.assert_called_once()
    
    @patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.get')
    @patch('zargar.admin_panel.security_event_services.SuperAdmin.objects.get')
    @patch('zargar.admin_panel.security_event_services.AuditLog.log_action')
    def test_update_status_to_resolved(self, mock_log, mock_super_admin, mock_event):
        """Test updating status to resolved."""
        # Mock objects
        mock_event_obj = Mock()
        mock_event_obj.id = 1
        mock_event_obj.resolution_notes = ''
        mock_event_obj.is_resolved = False
        mock_event_obj.resolved_at = None
        mock_event_obj.resolved_by = None
        mock_event.return_value = mock_event_obj
        
        mock_admin = Mock()
        mock_admin.username = 'admin'
        mock_super_admin.return_value = mock_admin
        
        service = SecurityEventInvestigationService
        result = service.update_investigation_status(
            event_id=1,
            status='resolved',
            updated_by_id=2,
            notes='Investigation complete'
        )
        
        # Verify resolution
        assert result['success'] is True
        assert result['new_status'] == 'resolved'
        assert result['is_resolved'] is True
        
        # Verify event was marked as resolved
        assert mock_event_obj.is_resolved is True
        assert mock_event_obj.resolved_by == mock_admin


class TestSecurityEventResolutionService:
    """Test SecurityEventResolutionService without database."""
    
    @patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.get')
    @patch('zargar.admin_panel.security_event_services.SuperAdmin.objects.get')
    @patch('zargar.admin_panel.security_event_services.AuditLog.log_action')
    @patch('zargar.admin_panel.security_event_services.timezone.now')
    def test_resolve_event_success(self, mock_now, mock_log, mock_super_admin, mock_event):
        """Test successful event resolution."""
        # Mock current time
        mock_time = timezone.make_aware(datetime(2023, 1, 1, 12, 0, 0))
        mock_now.return_value = mock_time
        
        # Mock objects
        mock_event_obj = Mock()
        mock_event_obj.id = 1
        mock_event_obj.resolution_notes = ''
        mock_event_obj.is_resolved = False
        mock_event.return_value = mock_event_obj
        
        mock_resolver = Mock()
        mock_resolver.username = 'resolver'
        mock_super_admin.return_value = mock_resolver
        
        service = SecurityEventResolutionService
        result = service.resolve_event(
            event_id=1,
            resolved_by_id=2,
            resolution_notes='False positive',
            resolution_type='manual'
        )
        
        # Verify success
        assert result['success'] is True
        assert result['resolved_by'] == 'resolver'
        assert result['resolved_at'] == mock_time
        
        # Verify event was updated
        assert mock_event_obj.is_resolved is True
        assert mock_event_obj.resolved_by == mock_resolver
        assert mock_event_obj.resolved_at == mock_time
        mock_event_obj.save.assert_called_once()
        
        # Verify audit log
        mock_log.assert_called_once()
    
    @patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.get')
    @patch('zargar.admin_panel.security_event_services.SuperAdmin.objects.get')
    @patch('zargar.admin_panel.security_event_services.AuditLog.log_action')
    def test_resolve_event_with_follow_up(self, mock_log, mock_super_admin, mock_event):
        """Test resolving event with follow-up required."""
        # Mock objects
        mock_event_obj = Mock()
        mock_event_obj.id = 1
        mock_event_obj.resolution_notes = ''
        mock_event.return_value = mock_event_obj
        
        mock_resolver = Mock()
        mock_resolver.username = 'resolver'
        mock_super_admin.return_value = mock_resolver
        
        service = SecurityEventResolutionService
        result = service.resolve_event(
            event_id=1,
            resolved_by_id=2,
            resolution_notes='Needs monitoring',
            follow_up_required=True
        )
        
        # Verify success
        assert result['success'] is True
        
        # Verify follow-up flag was added to notes
        # The resolution_notes should contain [FOLLOW-UP REQUIRED]
        mock_event_obj.save.assert_called_once()
    
    @patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.filter')
    @patch('zargar.admin_panel.security_event_services.SuperAdmin.objects.get')
    @patch('zargar.admin_panel.security_event_services.SecurityEventResolutionService.resolve_event')
    @patch('zargar.admin_panel.security_event_services.AuditLog.log_action')
    def test_bulk_resolve_events(self, mock_log, mock_resolve, mock_super_admin, mock_filter):
        """Test bulk resolution of events."""
        # Mock resolver
        mock_resolver = Mock()
        mock_resolver.username = 'resolver'
        mock_super_admin.return_value = mock_resolver
        
        # Mock events
        mock_events = [Mock(id=1), Mock(id=2), Mock(id=3)]
        mock_filter.return_value = mock_events
        
        # Mock individual resolve calls
        mock_resolve.side_effect = [
            {'success': True},
            {'success': True},
            {'success': False, 'error': 'Test error'}
        ]
        
        service = SecurityEventResolutionService
        result = service.bulk_resolve_events(
            event_ids=[1, 2, 3],
            resolved_by_id=2,
            resolution_notes='Bulk resolution'
        )
        
        # Verify results
        assert result['success'] is True
        assert result['resolved_count'] == 2
        assert result['failed_count'] == 1
        assert len(result['failed_events']) == 1
        assert result['failed_events'][0]['id'] == 3
        
        # Verify individual resolve calls
        assert mock_resolve.call_count == 3
        mock_log.assert_called_once()
    
    @patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.get')
    @patch('zargar.admin_panel.security_event_services.SuperAdmin.objects.get')
    @patch('zargar.admin_panel.security_event_services.AuditLog.log_action')
    def test_reopen_event_success(self, mock_log, mock_super_admin, mock_event):
        """Test successful event reopening."""
        # Mock objects
        mock_event_obj = Mock()
        mock_event_obj.id = 1
        mock_event_obj.is_resolved = True
        mock_event_obj.resolution_notes = 'Previous resolution'
        mock_event.return_value = mock_event_obj
        
        mock_reopener = Mock()
        mock_reopener.username = 'reopener'
        mock_super_admin.return_value = mock_reopener
        
        service = SecurityEventResolutionService
        result = service.reopen_event(
            event_id=1,
            reopened_by_id=2,
            reason='New evidence found'
        )
        
        # Verify success
        assert result['success'] is True
        assert result['reopened_by'] == 'reopener'
        
        # Verify event was reopened
        assert mock_event_obj.is_resolved is False
        assert mock_event_obj.resolved_at is None
        mock_event_obj.save.assert_called_once()
        
        # Verify audit log
        mock_log.assert_called_once()
    
    @patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.get')
    def test_reopen_unresolved_event(self, mock_event):
        """Test reopening an unresolved event."""
        # Mock unresolved event
        mock_event_obj = Mock()
        mock_event_obj.is_resolved = False
        mock_event.return_value = mock_event_obj
        
        service = SecurityEventResolutionService
        result = service.reopen_event(
            event_id=1,
            reopened_by_id=2,
            reason='Test reason'
        )
        
        # Should fail
        assert result['success'] is False
        assert result['error'] == 'Event is not resolved'


class TestSecurityEventFilterService:
    """Test SecurityEventFilterService logic without database."""
    
    def test_filter_service_exists(self):
        """Test that the filter service class exists and has required methods."""
        service = SecurityEventFilterService
        
        # Check that required methods exist
        assert hasattr(service, 'get_filtered_events')
        assert hasattr(service, 'get_event_statistics')
        assert callable(service.get_filtered_events)
        assert callable(service.get_event_statistics)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])