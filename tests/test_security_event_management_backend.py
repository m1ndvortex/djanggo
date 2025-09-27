"""
Unit tests for Security Event Management Backend Services.

Tests the filtering, categorization, investigation workflow, and resolution
system for security events in the super admin panel.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing models
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta, datetime
from unittest.mock import patch, MagicMock

from zargar.core.security_models import SecurityEvent, SuspiciousActivity, AuditLog
from zargar.tenants.models import SuperAdmin
from zargar.admin_panel.security_event_services import (
    SecurityEventFilterService,
    SecurityEventCategorizationService,
    SecurityEventInvestigationService,
    SecurityEventResolutionService,
)

User = get_user_model()


class SecurityEventFilterServiceTest(TestCase):
    """Test SecurityEventFilterService functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.super_admin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        # Create test security events
        self.event1 = SecurityEvent.objects.create(
            event_type='login_failed',
            severity='medium',
            user=self.user,
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            details={'test': 'data'}
        )
        
        self.event2 = SecurityEvent.objects.create(
            event_type='brute_force_attempt',
            severity='high',
            username_attempted='testuser',
            ip_address='192.168.1.2',
            user_agent='Malicious Bot',
            is_resolved=True,
            resolved_by=self.super_admin,
            resolved_at=timezone.now(),
            resolution_notes='Resolved by admin'
        )
        
        self.event3 = SecurityEvent.objects.create(
            event_type='unauthorized_access',
            severity='critical',
            user=self.user,
            ip_address='192.168.1.1',
            user_agent='Test Browser'
        )
    
    def test_get_filtered_events_no_filters(self):
        """Test getting events without any filters."""
        events, metadata = SecurityEventFilterService.get_filtered_events()
        
        self.assertEqual(len(events), 3)
        self.assertEqual(metadata['total_count'], 3)
        self.assertEqual(metadata['page'], 1)
        self.assertEqual(metadata['per_page'], 25)
        self.assertTrue(metadata['total_pages'] >= 1)
    
    def test_get_filtered_events_by_event_type(self):
        """Test filtering events by event type."""
        events, metadata = SecurityEventFilterService.get_filtered_events(
            event_type='login_failed'
        )
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, 'login_failed')
        self.assertEqual(metadata['filters_applied']['event_type'], 'login_failed')
    
    def test_get_filtered_events_by_severity(self):
        """Test filtering events by severity."""
        events, metadata = SecurityEventFilterService.get_filtered_events(
            severity='high'
        )
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].severity, 'high')
    
    def test_get_filtered_events_by_resolution_status(self):
        """Test filtering events by resolution status."""
        # Test unresolved events
        events, metadata = SecurityEventFilterService.get_filtered_events(
            is_resolved=False
        )
        
        self.assertEqual(len(events), 2)
        for event in events:
            self.assertFalse(event.is_resolved)
        
        # Test resolved events
        events, metadata = SecurityEventFilterService.get_filtered_events(
            is_resolved=True
        )
        
        self.assertEqual(len(events), 1)
        self.assertTrue(events[0].is_resolved)
    
    def test_get_filtered_events_by_ip_address(self):
        """Test filtering events by IP address."""
        events, metadata = SecurityEventFilterService.get_filtered_events(
            ip_address='192.168.1.1'
        )
        
        self.assertEqual(len(events), 2)
        for event in events:
            self.assertEqual(event.ip_address, '192.168.1.1')
    
    def test_get_filtered_events_by_user(self):
        """Test filtering events by user."""
        events, metadata = SecurityEventFilterService.get_filtered_events(
            user_id=self.user.id
        )
        
        self.assertEqual(len(events), 2)
        for event in events:
            self.assertEqual(event.user, self.user)
    
    def test_get_filtered_events_by_date_range(self):
        """Test filtering events by date range."""
        now = timezone.now()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)
        
        events, metadata = SecurityEventFilterService.get_filtered_events(
            date_from=yesterday,
            date_to=tomorrow
        )
        
        self.assertEqual(len(events), 3)  # All events should be in range
    
    def test_get_filtered_events_search_query(self):
        """Test filtering events by search query."""
        events, metadata = SecurityEventFilterService.get_filtered_events(
            search_query='testuser'
        )
        
        self.assertGreaterEqual(len(events), 1)
        
        # Test IP search
        events, metadata = SecurityEventFilterService.get_filtered_events(
            search_query='192.168.1.1'
        )
        
        self.assertEqual(len(events), 2)
    
    def test_get_filtered_events_pagination(self):
        """Test pagination functionality."""
        # Test first page
        events, metadata = SecurityEventFilterService.get_filtered_events(
            per_page=2,
            page=1
        )
        
        self.assertEqual(len(events), 2)
        self.assertEqual(metadata['page'], 1)
        self.assertEqual(metadata['per_page'], 2)
        self.assertTrue(metadata['has_next'])
        self.assertFalse(metadata['has_previous'])
        
        # Test second page
        events, metadata = SecurityEventFilterService.get_filtered_events(
            per_page=2,
            page=2
        )
        
        self.assertEqual(len(events), 1)
        self.assertEqual(metadata['page'], 2)
        self.assertFalse(metadata['has_next'])
        self.assertTrue(metadata['has_previous'])
    
    def test_get_event_statistics(self):
        """Test getting event statistics."""
        stats = SecurityEventFilterService.get_event_statistics()
        
        self.assertEqual(stats['total_events'], 3)
        self.assertEqual(stats['resolved_events'], 1)
        self.assertEqual(stats['unresolved_events'], 2)
        self.assertAlmostEqual(stats['resolution_rate'], 33.33, places=1)
        
        # Check severity breakdown
        self.assertIn('severity_breakdown', stats)
        self.assertIn('medium', stats['severity_breakdown'])
        self.assertIn('high', stats['severity_breakdown'])
        self.assertIn('critical', stats['severity_breakdown'])
        
        # Check top event types
        self.assertIn('top_event_types', stats)
        self.assertIsInstance(stats['top_event_types'], list)
        
        # Check top risk IPs
        self.assertIn('top_risk_ips', stats)
        self.assertIsInstance(stats['top_risk_ips'], list)


class SecurityEventCategorizationServiceTest(TestCase):
    """Test SecurityEventCategorizationService functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_categorize_authentication_event(self):
        """Test categorizing authentication events."""
        event = SecurityEvent.objects.create(
            event_type='login_failed',
            severity='medium',
            user=self.user,
            ip_address='192.168.1.1'
        )
        
        categorization = SecurityEventCategorizationService.categorize_event(event)
        
        self.assertEqual(categorization['category'], 'authentication')
        self.assertGreater(categorization['risk_score'], 0)
        self.assertIn(categorization['priority'], ['low', 'medium', 'high', 'critical'])
        self.assertIn('recommended_action', categorization)
        self.assertIsInstance(categorization['escalation_required'], bool)
    
    def test_categorize_account_security_event(self):
        """Test categorizing account security events."""
        event = SecurityEvent.objects.create(
            event_type='brute_force_attempt',
            severity='high',
            ip_address='192.168.1.1'
        )
        
        categorization = SecurityEventCategorizationService.categorize_event(event)
        
        self.assertEqual(categorization['category'], 'account_security')
        self.assertGreater(categorization['risk_score'], 5)  # Should be high risk
        self.assertIn(categorization['priority'], ['high', 'critical'])
    
    def test_categorize_access_control_event(self):
        """Test categorizing access control events."""
        event = SecurityEvent.objects.create(
            event_type='privilege_escalation',
            severity='critical',
            user=self.user,
            ip_address='192.168.1.1'
        )
        
        categorization = SecurityEventCategorizationService.categorize_event(event)
        
        self.assertEqual(categorization['category'], 'access_control')
        self.assertEqual(categorization['priority'], 'critical')
        self.assertTrue(categorization['escalation_required'])
        self.assertEqual(categorization['recommended_action'], 'immediate_investigation')
    
    def test_risk_score_calculation(self):
        """Test risk score calculation."""
        # Low risk event
        low_event = SecurityEvent.objects.create(
            event_type='logout',
            severity='low',
            ip_address='192.168.1.1'
        )
        
        low_categorization = SecurityEventCategorizationService.categorize_event(low_event)
        
        # High risk event
        high_event = SecurityEvent.objects.create(
            event_type='privilege_escalation',
            severity='critical',
            ip_address='192.168.1.1'
        )
        
        high_categorization = SecurityEventCategorizationService.categorize_event(high_event)
        
        self.assertLess(low_categorization['risk_score'], high_categorization['risk_score'])
        self.assertLessEqual(high_categorization['risk_score'], 10.0)  # Should be capped at 10
    
    @patch('zargar.admin_panel.security_event_services.SecurityEvent.objects.filter')
    def test_pattern_detection(self, mock_filter):
        """Test pattern detection in events."""
        # Mock frequent events from same IP
        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 15  # High frequency
        mock_filter.return_value = mock_queryset
        
        event = SecurityEvent.objects.create(
            event_type='login_failed',
            severity='medium',
            ip_address='192.168.1.1'
        )
        
        categorization = SecurityEventCategorizationService.categorize_event(event)
        
        self.assertTrue(categorization['pattern_detected'])
        self.assertEqual(categorization['pattern_type'], 'ip_frequency')
        self.assertGreater(categorization['pattern_confidence'], 0)
    
    def test_get_categorized_events_summary(self):
        """Test getting categorized events summary."""
        # Create events of different categories
        SecurityEvent.objects.create(
            event_type='login_failed',
            severity='medium',
            ip_address='192.168.1.1'
        )
        
        SecurityEvent.objects.create(
            event_type='brute_force_attempt',
            severity='high',
            ip_address='192.168.1.2'
        )
        
        SecurityEvent.objects.create(
            event_type='privilege_escalation',
            severity='critical',
            ip_address='192.168.1.3'
        )
        
        summary = SecurityEventCategorizationService.get_categorized_events_summary()
        
        self.assertIn('category_summary', summary)
        self.assertIn('priority_summary', summary)
        self.assertIn('total_events', summary)
        
        # Check that categories are present
        categories = summary['category_summary']
        self.assertIn('authentication', categories)
        self.assertIn('account_security', categories)
        self.assertIn('access_control', categories)
        
        # Check priority summary
        priorities = summary['priority_summary']
        self.assertIn('critical', priorities)
        self.assertIn('high', priorities)
        self.assertIn('medium', priorities)
        self.assertIn('low', priorities)


class SecurityEventInvestigationServiceTest(TestCase):
    """Test SecurityEventInvestigationService functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.investigator = SuperAdmin.objects.create_user(
            username='investigator',
            email='investigator@example.com',
            password='invpass123'
        )
        
        self.admin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.event = SecurityEvent.objects.create(
            event_type='suspicious_activity',
            severity='high',
            user=self.user,
            ip_address='192.168.1.1',
            user_agent='Test Browser'
        )
    
    def test_assign_investigator(self):
        """Test assigning investigator to security event."""
        result = SecurityEventInvestigationService.assign_investigator(
            event_id=self.event.id,
            investigator_id=self.investigator.id,
            assigned_by_id=self.admin.id,
            notes='Assigning for investigation'
        )
        
        self.assertTrue(result['success'])
        self.assertIn('investigator', result)
        self.assertEqual(result['investigator']['username'], 'investigator')
        
        # Check that event was updated
        self.event.refresh_from_db()
        self.assertEqual(self.event.resolved_by, self.investigator)
        self.assertIn('Assigned to investigator', self.event.resolution_notes)
    
    def test_assign_investigator_nonexistent_event(self):
        """Test assigning investigator to nonexistent event."""
        result = SecurityEventInvestigationService.assign_investigator(
            event_id=99999,
            investigator_id=self.investigator.id,
            assigned_by_id=self.admin.id
        )
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Security event not found')
    
    def test_assign_investigator_nonexistent_investigator(self):
        """Test assigning nonexistent investigator."""
        result = SecurityEventInvestigationService.assign_investigator(
            event_id=self.event.id,
            investigator_id=99999,
            assigned_by_id=self.admin.id
        )
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Investigator not found')
    
    def test_update_investigation_status(self):
        """Test updating investigation status."""
        result = SecurityEventInvestigationService.update_investigation_status(
            event_id=self.event.id,
            status='in_progress',
            updated_by_id=self.investigator.id,
            notes='Starting investigation'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['new_status'], 'in_progress')
        self.assertFalse(result['is_resolved'])
        
        # Check that event was updated
        self.event.refresh_from_db()
        self.assertIn('Status updated to \'in_progress\'', self.event.resolution_notes)
    
    def test_update_investigation_status_to_resolved(self):
        """Test updating status to resolved."""
        result = SecurityEventInvestigationService.update_investigation_status(
            event_id=self.event.id,
            status='resolved',
            updated_by_id=self.investigator.id,
            notes='Investigation complete'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['new_status'], 'resolved')
        self.assertTrue(result['is_resolved'])
        
        # Check that event was marked as resolved
        self.event.refresh_from_db()
        self.assertTrue(self.event.is_resolved)
        self.assertIsNotNone(self.event.resolved_at)
    
    def test_add_investigation_note(self):
        """Test adding investigation note."""
        result = SecurityEventInvestigationService.add_investigation_note(
            event_id=self.event.id,
            note='Found suspicious patterns in logs',
            added_by_id=self.investigator.id,
            note_type='investigation'
        )
        
        self.assertTrue(result['success'])
        self.assertIn('formatted_note', result)
        
        # Check that note was added
        self.event.refresh_from_db()
        self.assertIn('INVESTIGATION by investigator', self.event.resolution_notes)
        self.assertIn('Found suspicious patterns in logs', self.event.resolution_notes)
    
    def test_get_investigation_timeline(self):
        """Test getting investigation timeline."""
        # Add some notes to create timeline
        SecurityEventInvestigationService.add_investigation_note(
            event_id=self.event.id,
            note='Starting investigation',
            added_by_id=self.investigator.id
        )
        
        SecurityEventInvestigationService.update_investigation_status(
            event_id=self.event.id,
            status='in_progress',
            updated_by_id=self.investigator.id
        )
        
        result = SecurityEventInvestigationService.get_investigation_timeline(self.event.id)
        
        self.assertTrue(result['success'])
        self.assertIn('timeline', result)
        self.assertGreater(result['total_entries'], 0)
        
        timeline = result['timeline']
        self.assertTrue(any(entry['type'] == 'event_created' for entry in timeline))
    
    def test_get_related_events(self):
        """Test getting related events."""
        # Create related events
        SecurityEvent.objects.create(
            event_type='login_failed',
            severity='medium',
            user=self.user,
            ip_address='192.168.1.1'
        )
        
        SecurityEvent.objects.create(
            event_type='login_failed',
            severity='medium',
            ip_address='192.168.1.2'
        )
        
        SecurityEvent.objects.create(
            event_type='suspicious_activity',
            severity='high',
            ip_address='192.168.1.3'
        )
        
        result = SecurityEventInvestigationService.get_related_events(self.event.id)
        
        self.assertTrue(result['success'])
        self.assertIn('related_events', result)
        
        related = result['related_events']
        self.assertIn('by_ip', related)
        self.assertIn('by_user', related)
        self.assertIn('by_type', related)
        self.assertIn('suspicious_activities', related)
        
        # Should have events by same IP and user
        self.assertGreater(len(related['by_ip']), 0)
        self.assertGreater(len(related['by_user']), 0)


class SecurityEventResolutionServiceTest(TestCase):
    """Test SecurityEventResolutionService functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.resolver = SuperAdmin.objects.create_user(
            username='resolver',
            email='resolver@example.com',
            password='resolverpass123'
        )
        
        self.event = SecurityEvent.objects.create(
            event_type='suspicious_activity',
            severity='high',
            user=self.user,
            ip_address='192.168.1.1'
        )
    
    def test_resolve_event(self):
        """Test resolving a security event."""
        result = SecurityEventResolutionService.resolve_event(
            event_id=self.event.id,
            resolved_by_id=self.resolver.id,
            resolution_notes='False positive - user behavior normal',
            resolution_type='manual'
        )
        
        self.assertTrue(result['success'])
        self.assertIn('resolved_at', result)
        self.assertEqual(result['resolved_by'], 'resolver')
        
        # Check that event was resolved
        self.event.refresh_from_db()
        self.assertTrue(self.event.is_resolved)
        self.assertEqual(self.event.resolved_by, self.resolver)
        self.assertIsNotNone(self.event.resolved_at)
        self.assertIn('RESOLVED by resolver', self.event.resolution_notes)
    
    def test_resolve_event_with_follow_up(self):
        """Test resolving event with follow-up required."""
        result = SecurityEventResolutionService.resolve_event(
            event_id=self.event.id,
            resolved_by_id=self.resolver.id,
            resolution_notes='Resolved but needs monitoring',
            follow_up_required=True
        )
        
        self.assertTrue(result['success'])
        
        # Check that follow-up flag was added
        self.event.refresh_from_db()
        self.assertIn('[FOLLOW-UP REQUIRED]', self.event.resolution_notes)
    
    def test_resolve_nonexistent_event(self):
        """Test resolving nonexistent event."""
        result = SecurityEventResolutionService.resolve_event(
            event_id=99999,
            resolved_by_id=self.resolver.id,
            resolution_notes='Test resolution'
        )
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Security event not found')
    
    def test_bulk_resolve_events(self):
        """Test bulk resolving multiple events."""
        # Create additional events
        event2 = SecurityEvent.objects.create(
            event_type='login_failed',
            severity='medium',
            ip_address='192.168.1.2'
        )
        
        event3 = SecurityEvent.objects.create(
            event_type='api_rate_limit',
            severity='low',
            ip_address='192.168.1.3'
        )
        
        event_ids = [self.event.id, event2.id, event3.id]
        
        result = SecurityEventResolutionService.bulk_resolve_events(
            event_ids=event_ids,
            resolved_by_id=self.resolver.id,
            resolution_notes='Bulk resolution - false positives'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['resolved_count'], 3)
        self.assertEqual(result['failed_count'], 0)
        
        # Check that all events were resolved
        for event_id in event_ids:
            event = SecurityEvent.objects.get(id=event_id)
            self.assertTrue(event.is_resolved)
            self.assertIn('[BULK RESOLUTION]', event.resolution_notes)
    
    def test_reopen_event(self):
        """Test reopening a resolved event."""
        # First resolve the event
        SecurityEventResolutionService.resolve_event(
            event_id=self.event.id,
            resolved_by_id=self.resolver.id,
            resolution_notes='Initial resolution'
        )
        
        # Now reopen it
        result = SecurityEventResolutionService.reopen_event(
            event_id=self.event.id,
            reopened_by_id=self.resolver.id,
            reason='New evidence found'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['reopened_by'], 'resolver')
        
        # Check that event was reopened
        self.event.refresh_from_db()
        self.assertFalse(self.event.is_resolved)
        self.assertIsNone(self.event.resolved_at)
        self.assertIn('REOPENED by resolver', self.event.resolution_notes)
        self.assertIn('New evidence found', self.event.resolution_notes)
    
    def test_reopen_unresolved_event(self):
        """Test reopening an unresolved event."""
        result = SecurityEventResolutionService.reopen_event(
            event_id=self.event.id,
            reopened_by_id=self.resolver.id,
            reason='Test reason'
        )
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Event is not resolved')


@pytest.mark.django_db
class SecurityEventManagementIntegrationTest:
    """Integration tests for security event management services."""
    
    def test_complete_investigation_workflow(self):
        """Test complete investigation workflow from assignment to resolution."""
        # Create test data
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        investigator = SuperAdmin.objects.create_user(
            username='investigator',
            email='investigator@example.com',
            password='invpass123'
        )
        
        admin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        event = SecurityEvent.objects.create(
            event_type='suspicious_activity',
            severity='high',
            user=user,
            ip_address='192.168.1.1'
        )
        
        # Step 1: Categorize event
        categorization = SecurityEventCategorizationService.categorize_event(event)
        assert categorization['category'] == 'account_security'
        assert categorization['priority'] in ['high', 'critical']
        
        # Step 2: Assign investigator
        assign_result = SecurityEventInvestigationService.assign_investigator(
            event_id=event.id,
            investigator_id=investigator.id,
            assigned_by_id=admin.id,
            notes='High priority investigation'
        )
        assert assign_result['success']
        
        # Step 3: Update status to in progress
        status_result = SecurityEventInvestigationService.update_investigation_status(
            event_id=event.id,
            status='in_progress',
            updated_by_id=investigator.id,
            notes='Starting investigation'
        )
        assert status_result['success']
        
        # Step 4: Add investigation notes
        note_result = SecurityEventInvestigationService.add_investigation_note(
            event_id=event.id,
            note='Analyzed logs, found normal user behavior',
            added_by_id=investigator.id
        )
        assert note_result['success']
        
        # Step 5: Resolve event
        resolve_result = SecurityEventResolutionService.resolve_event(
            event_id=event.id,
            resolved_by_id=investigator.id,
            resolution_notes='False positive - normal user behavior confirmed'
        )
        assert resolve_result['success']
        
        # Verify final state
        event.refresh_from_db()
        assert event.is_resolved
        assert event.resolved_by == investigator
        assert 'Assigned to investigator' in event.resolution_notes
        assert 'Status updated to \'in_progress\'' in event.resolution_notes
        assert 'INVESTIGATION by investigator' in event.resolution_notes
        assert 'RESOLVED by investigator' in event.resolution_notes
        
        # Step 6: Get investigation timeline
        timeline_result = SecurityEventInvestigationService.get_investigation_timeline(event.id)
        assert timeline_result['success']
        assert len(timeline_result['timeline']) >= 4  # Creation + assignment + status + resolution
    
    def test_filtering_and_statistics_integration(self):
        """Test integration between filtering and statistics."""
        # Create test events
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        resolver = SuperAdmin.objects.create_user(
            username='resolver',
            email='resolver@example.com',
            password='resolverpass123'
        )
        
        # Create various events
        events = [
            SecurityEvent.objects.create(
                event_type='login_failed',
                severity='medium',
                user=user,
                ip_address='192.168.1.1'
            ),
            SecurityEvent.objects.create(
                event_type='brute_force_attempt',
                severity='high',
                ip_address='192.168.1.2'
            ),
            SecurityEvent.objects.create(
                event_type='privilege_escalation',
                severity='critical',
                user=user,
                ip_address='192.168.1.1'
            ),
        ]
        
        # Resolve one event
        SecurityEventResolutionService.resolve_event(
            event_id=events[0].id,
            resolved_by_id=resolver.id,
            resolution_notes='Resolved'
        )
        
        # Test filtering
        high_severity_events, metadata = SecurityEventFilterService.get_filtered_events(
            severity='high'
        )
        assert len(high_severity_events) == 1
        assert high_severity_events[0].severity == 'high'
        
        # Test statistics
        stats = SecurityEventFilterService.get_event_statistics()
        assert stats['total_events'] == 3
        assert stats['resolved_events'] == 1
        assert stats['unresolved_events'] == 2
        
        # Test categorization summary
        summary = SecurityEventCategorizationService.get_categorized_events_summary()
        assert 'authentication' in summary['category_summary']
        assert 'account_security' in summary['category_summary']
        assert 'access_control' in summary['category_summary']
        assert summary['priority_summary']['critical'] >= 1
        assert summary['priority_summary']['high'] >= 1