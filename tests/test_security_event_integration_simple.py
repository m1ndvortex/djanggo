"""
Simple integration test for Security Event Management Services.

Tests basic integration without complex database setup.
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


class TestSecurityEventManagementIntegration:
    """Integration tests for security event management services."""
    
    @patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.filter')
    @patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.get')
    @patch('zargar.admin_panel.security_event_services.SuperAdmin.objects.get')
    @patch('zargar.admin_panel.security_event_services.AuditLog.log_action')
    def test_complete_investigation_workflow(self, mock_log, mock_super_admin, mock_event_get, mock_event_filter):
        """Test complete investigation workflow from categorization to resolution."""
        
        # Mock event for categorization
        mock_event = Mock()
        mock_event.id = 1
        mock_event.event_type = 'suspicious_activity'
        mock_event.severity = 'high'
        mock_event.ip_address = '192.168.1.1'
        mock_event.user = Mock()
        mock_event.resolution_notes = ''
        mock_event.is_resolved = False
        mock_event.resolved_at = None
        mock_event.resolved_by = None
        
        # Mock for pattern detection
        mock_queryset = Mock()
        mock_queryset.count.return_value = 3  # Medium frequency
        mock_event_filter.return_value = mock_queryset
        
        # Mock for get operations
        mock_event_get.return_value = mock_event
        
        # Mock users
        mock_investigator = Mock()
        mock_investigator.id = 2
        mock_investigator.username = 'investigator'
        mock_investigator.email = 'inv@example.com'
        
        mock_admin = Mock()
        mock_admin.id = 3
        mock_admin.username = 'admin'
        
        mock_super_admin.side_effect = [mock_investigator, mock_admin, mock_investigator, mock_investigator, mock_investigator]
        
        # Step 1: Categorize event
        categorization = SecurityEventCategorizationService.categorize_event(mock_event)
        
        assert categorization['category'] == 'account_security'
        assert categorization['priority'] in ['high', 'critical']
        assert isinstance(categorization['risk_score'], float)
        assert categorization['risk_score'] > 0
        
        # Step 2: Assign investigator
        assign_result = SecurityEventInvestigationService.assign_investigator(
            event_id=1,
            investigator_id=2,
            assigned_by_id=3,
            notes='High priority investigation'
        )
        
        assert assign_result['success'] is True
        assert assign_result['investigator']['username'] == 'investigator'
        
        # Step 3: Update status to in progress
        status_result = SecurityEventInvestigationService.update_investigation_status(
            event_id=1,
            status='in_progress',
            updated_by_id=2,
            notes='Starting investigation'
        )
        
        assert status_result['success'] is True
        assert status_result['new_status'] == 'in_progress'
        
        # Step 4: Add investigation note
        note_result = SecurityEventInvestigationService.add_investigation_note(
            event_id=1,
            note='Analyzed logs, found normal user behavior',
            added_by_id=2
        )
        
        assert note_result['success'] is True
        
        # Step 5: Resolve event
        resolve_result = SecurityEventResolutionService.resolve_event(
            event_id=1,
            resolved_by_id=2,
            resolution_notes='False positive - normal user behavior confirmed'
        )
        
        assert resolve_result['success'] is True
        assert resolve_result['resolved_by'] == 'investigator'
        
        # Verify that the event was updated through the workflow
        assert mock_event.save.call_count >= 4  # Assignment, status update, note, resolution
        assert mock_log.call_count >= 4  # Each step should log
    
    def test_categorization_and_filtering_integration(self):
        """Test integration between categorization and filtering logic."""
        
        # Test different event types and their categorization
        test_events = [
            {
                'event_type': 'login_failed',
                'severity': 'medium',
                'expected_category': 'authentication'
            },
            {
                'event_type': 'brute_force_attempt',
                'severity': 'high',
                'expected_category': 'account_security'
            },
            {
                'event_type': 'privilege_escalation',
                'severity': 'critical',
                'expected_category': 'access_control'
            },
            {
                'event_type': 'data_export',
                'severity': 'medium',
                'expected_category': 'data_operations'
            },
            {
                'event_type': 'api_rate_limit',
                'severity': 'low',
                'expected_category': 'system_security'
            }
        ]
        
        with patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.filter') as mock_filter:
            # Mock low frequency for all events
            mock_queryset = Mock()
            mock_queryset.count.return_value = 1
            mock_filter.return_value = mock_queryset
            
            for test_event in test_events:
                mock_event = Mock()
                mock_event.event_type = test_event['event_type']
                mock_event.severity = test_event['severity']
                mock_event.ip_address = '192.168.1.1'
                mock_event.user = None
                
                categorization = SecurityEventCategorizationService.categorize_event(mock_event)
                
                assert categorization['category'] == test_event['expected_category']
                assert isinstance(categorization['risk_score'], float)
                assert categorization['risk_score'] > 0
                assert categorization['priority'] in ['low', 'medium', 'high', 'critical']
    
    @patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.get')
    @patch('zargar.admin_panel.security_event_services.SuperAdmin.objects.get')
    @patch('zargar.admin_panel.security_event_services.AuditLog.log_action')
    def test_resolution_and_reopening_workflow(self, mock_log, mock_super_admin, mock_event_get):
        """Test resolution and reopening workflow."""
        
        # Mock event
        mock_event = Mock()
        mock_event.id = 1
        mock_event.resolution_notes = ''
        mock_event.is_resolved = False
        mock_event.resolved_at = None
        mock_event.resolved_by = None
        mock_event_get.return_value = mock_event
        
        # Mock resolver
        mock_resolver = Mock()
        mock_resolver.username = 'resolver'
        mock_super_admin.return_value = mock_resolver
        
        # Step 1: Resolve event
        resolve_result = SecurityEventResolutionService.resolve_event(
            event_id=1,
            resolved_by_id=2,
            resolution_notes='Initial resolution - false positive'
        )
        
        assert resolve_result['success'] is True
        assert resolve_result['resolved_by'] == 'resolver'
        
        # Verify event was marked as resolved
        assert mock_event.is_resolved is True
        assert mock_event.resolved_by == mock_resolver
        
        # Step 2: Reopen event (simulate new evidence)
        reopen_result = SecurityEventResolutionService.reopen_event(
            event_id=1,
            reopened_by_id=2,
            reason='New evidence found - requires re-investigation'
        )
        
        assert reopen_result['success'] is True
        assert reopen_result['reopened_by'] == 'resolver'
        
        # Verify event was reopened
        assert mock_event.is_resolved is False
        assert mock_event.resolved_at is None
        
        # Step 3: Resolve again
        resolve_result2 = SecurityEventResolutionService.resolve_event(
            event_id=1,
            resolved_by_id=2,
            resolution_notes='Final resolution after re-investigation'
        )
        
        assert resolve_result2['success'] is True
        
        # Verify multiple save calls (resolve, reopen, resolve again)
        assert mock_event.save.call_count >= 3
        assert mock_log.call_count >= 3
    
    def test_service_error_handling(self):
        """Test error handling across services."""
        
        # Test with non-existent event ID
        with patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.get') as mock_event_get:
            from zargar.core.security_models import SecurityEvent
            mock_event_get.side_effect = SecurityEvent.DoesNotExist()
            
            assign_result = SecurityEventInvestigationService.assign_investigator(
                event_id=99999,
                investigator_id=1,
                assigned_by_id=2
            )
            
            assert assign_result['success'] is False
            assert assign_result['error'] == 'Security event not found'
        
        # Test with non-existent investigator
        with patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.get') as mock_event, \
             patch('zargar.admin_panel.security_event_services.SuperAdmin.objects.get') as mock_super_admin:
            
            mock_event.return_value = Mock()
            
            from zargar.tenants.models import SuperAdmin
            mock_super_admin.side_effect = SuperAdmin.DoesNotExist()
            
            assign_result = SecurityEventInvestigationService.assign_investigator(
                event_id=1,
                investigator_id=99999,
                assigned_by_id=2
            )
            
            assert assign_result['success'] is False
            assert assign_result['error'] == 'Investigator not found'
    
    def test_bulk_operations(self):
        """Test bulk operations functionality."""
        
        with patch('zargar.admin_panel.security_event_services.SuperAdmin.objects.get') as mock_super_admin, \
             patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.filter') as mock_filter, \
             patch('zargar.admin_panel.security_event_services.SecurityEventResolutionService.resolve_event') as mock_resolve, \
             patch('zargar.admin_panel.security_event_services.AuditLog.log_action') as mock_log:
            
            # Mock resolver
            mock_resolver = Mock()
            mock_resolver.username = 'bulk_resolver'
            mock_super_admin.return_value = mock_resolver
            
            # Mock events
            mock_events = [Mock(id=1), Mock(id=2), Mock(id=3)]
            mock_filter.return_value = mock_events
            
            # Mock successful individual resolutions
            mock_resolve.side_effect = [
                {'success': True},
                {'success': True},
                {'success': True}
            ]
            
            # Test bulk resolution
            result = SecurityEventResolutionService.bulk_resolve_events(
                event_ids=[1, 2, 3],
                resolved_by_id=2,
                resolution_notes='Bulk resolution - all false positives'
            )
            
            assert result['success'] is True
            assert result['resolved_count'] == 3
            assert result['failed_count'] == 0
            
            # Verify individual resolve calls
            assert mock_resolve.call_count == 3
            mock_log.assert_called_once()  # Bulk operation should be logged


if __name__ == '__main__':
    pytest.main([__file__, '-v'])