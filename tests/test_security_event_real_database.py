"""
Real Database Tests for Security Event Management Backend.

These tests use the actual database to verify that all functionality works
correctly with real data, tables, and relationships.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing models
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from datetime import timedelta, datetime

from zargar.core.security_models import SecurityEvent, SuspiciousActivity, AuditLog
from zargar.tenants.models import SuperAdmin
from zargar.admin_panel.security_event_services import (
    SecurityEventFilterService,
    SecurityEventCategorizationService,
    SecurityEventInvestigationService,
    SecurityEventResolutionService,
)

User = get_user_model()


@pytest.mark.django_db
class SecurityEventRealDatabaseTest(TransactionTestCase):
    """Test security event management with real database operations."""
    
    def setUp(self):
        """Set up test data in the database."""
        # Create test users
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123'
        )
        
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        
        # Create super admins
        self.super_admin1 = SuperAdmin.objects.create_user(
            username='admin1',
            email='admin1@example.com',
            password='adminpass123'
        )
        
        self.super_admin2 = SuperAdmin.objects.create_user(
            username='investigator1',
            email='investigator1@example.com',
            password='invpass123'
        )
        
        # Create test security events with various types and severities
        self.events = []
        
        # Authentication events
        self.events.append(SecurityEvent.objects.create(
            event_type='login_failed',
            severity='medium',
            user=self.user1,
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0 Test Browser',
            username_attempted='testuser1',
            details={'reason': 'invalid_password', 'attempt_count': 3}
        ))
        
        self.events.append(SecurityEvent.objects.create(
            event_type='login_success',
            severity='low',
            user=self.user1,
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0 Test Browser',
            details={'login_method': 'password'}
        ))
        
        # Security events
        self.events.append(SecurityEvent.objects.create(
            event_type='brute_force_attempt',
            severity='high',
            ip_address='192.168.1.200',
            user_agent='Automated Bot',
            username_attempted='admin',
            details={'attempts': 15, 'time_window': '5_minutes'}
        ))
        
        self.events.append(SecurityEvent.objects.create(
            event_type='privilege_escalation',
            severity='critical',
            user=self.user2,
            ip_address='192.168.1.150',
            user_agent='Mozilla/5.0 Test Browser',
            details={'attempted_role': 'admin', 'current_role': 'user'}
        ))
        
        self.events.append(SecurityEvent.objects.create(
            event_type='suspicious_activity',
            severity='high',
            user=self.user1,
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0 Test Browser',
            details={'activity_type': 'unusual_access_pattern'}
        ))
        
        # Data operation events
        self.events.append(SecurityEvent.objects.create(
            event_type='data_export',
            severity='medium',
            user=self.user2,
            ip_address='192.168.1.150',
            user_agent='Mozilla/5.0 Test Browser',
            details={'export_type': 'customer_data', 'record_count': 1000}
        ))
        
        # System events
        self.events.append(SecurityEvent.objects.create(
            event_type='api_rate_limit',
            severity='low',
            ip_address='192.168.1.300',
            user_agent='API Client v1.0',
            details={'endpoint': '/api/v1/jewelry', 'limit_exceeded': 100}
        ))
        
        # Resolve one event for testing
        resolved_event = self.events[0]
        resolved_event.is_resolved = True
        resolved_event.resolved_by = self.super_admin1
        resolved_event.resolved_at = timezone.now()
        resolved_event.resolution_notes = 'False positive - user remembered password'
        resolved_event.save()
    
    def test_database_setup_verification(self):
        """Verify that the database setup is correct."""
        # Check that all events were created
        self.assertEqual(SecurityEvent.objects.count(), 7)
        
        # Check that users and admins were created
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(SuperAdmin.objects.count(), 2)
        
        # Check that one event is resolved
        resolved_events = SecurityEvent.objects.filter(is_resolved=True)
        self.assertEqual(resolved_events.count(), 1)
        
        # Verify event types are correctly stored
        event_types = SecurityEvent.objects.values_list('event_type', flat=True)
        expected_types = [
            'login_failed', 'login_success', 'brute_force_attempt',
            'privilege_escalation', 'suspicious_activity', 'data_export', 'api_rate_limit'
        ]
        for event_type in expected_types:
            self.assertIn(event_type, event_types)
    
    def test_filter_service_with_real_data(self):
        """Test SecurityEventFilterService with real database data."""
        # Test getting all events without filters
        events, metadata = SecurityEventFilterService.get_filtered_events()
        
        self.assertEqual(len(events), 7)
        self.assertEqual(metadata['total_count'], 7)
        self.assertEqual(metadata['page'], 1)
        self.assertEqual(metadata['per_page'], 25)
        
        # Test filtering by event type
        events, metadata = SecurityEventFilterService.get_filtered_events(
            event_type='login_failed'
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, 'login_failed')
        
        # Test filtering by severity
        events, metadata = SecurityEventFilterService.get_filtered_events(
            severity='critical'
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].severity, 'critical')
        self.assertEqual(events[0].event_type, 'privilege_escalation')
        
        # Test filtering by resolution status
        events, metadata = SecurityEventFilterService.get_filtered_events(
            is_resolved=True
        )
        self.assertEqual(len(events), 1)
        self.assertTrue(events[0].is_resolved)
        
        events, metadata = SecurityEventFilterService.get_filtered_events(
            is_resolved=False
        )
        self.assertEqual(len(events), 6)
        
        # Test filtering by IP address
        events, metadata = SecurityEventFilterService.get_filtered_events(
            ip_address='192.168.1.100'
        )
        self.assertEqual(len(events), 3)  # login_failed, login_success, suspicious_activity
        
        # Test filtering by user
        events, metadata = SecurityEventFilterService.get_filtered_events(
            user_id=self.user1.id
        )
        self.assertEqual(len(events), 3)  # Events associated with user1
        
        # Test search functionality
        events, metadata = SecurityEventFilterService.get_filtered_events(
            search_query='testuser1'
        )
        self.assertGreaterEqual(len(events), 1)
        
        # Test date range filtering
        yesterday = timezone.now() - timedelta(days=1)
        tomorrow = timezone.now() + timedelta(days=1)
        
        events, metadata = SecurityEventFilterService.get_filtered_events(
            date_from=yesterday,
            date_to=tomorrow
        )
        self.assertEqual(len(events), 7)  # All events should be in range
        
        # Test pagination
        events, metadata = SecurityEventFilterService.get_filtered_events(
            per_page=3,
            page=1
        )
        self.assertEqual(len(events), 3)
        self.assertTrue(metadata['has_next'])
        self.assertFalse(metadata['has_previous'])
        
        events, metadata = SecurityEventFilterService.get_filtered_events(
            per_page=3,
            page=2
        )
        self.assertEqual(len(events), 3)
        self.assertTrue(metadata['has_next'])
        self.assertTrue(metadata['has_previous'])
    
    def test_filter_service_statistics(self):
        """Test SecurityEventFilterService statistics with real data."""
        stats = SecurityEventFilterService.get_event_statistics()
        
        # Verify basic counts
        self.assertEqual(stats['total_events'], 7)
        self.assertEqual(stats['resolved_events'], 1)
        self.assertEqual(stats['unresolved_events'], 6)
        self.assertAlmostEqual(stats['resolution_rate'], 14.29, places=1)
        
        # Verify severity breakdown
        severity_breakdown = stats['severity_breakdown']
        self.assertEqual(severity_breakdown.get('low', 0), 2)  # login_success, api_rate_limit
        self.assertEqual(severity_breakdown.get('medium', 0), 2)  # login_failed, data_export
        self.assertEqual(severity_breakdown.get('high', 0), 2)  # brute_force, suspicious_activity
        self.assertEqual(severity_breakdown.get('critical', 0), 1)  # privilege_escalation
        
        # Verify top event types
        top_event_types = stats['top_event_types']
        self.assertIsInstance(top_event_types, list)
        self.assertGreater(len(top_event_types), 0)
        
        # Verify top risk IPs (should include high/critical severity IPs)
        top_risk_ips = stats['top_risk_ips']
        self.assertIsInstance(top_risk_ips, list)
        
        # Find the critical event IP in risk IPs
        critical_event_ip = None
        for event in self.events:
            if event.severity == 'critical':
                critical_event_ip = event.ip_address
                break
        
        if critical_event_ip:
            risk_ip_addresses = [ip['ip_address'] for ip in top_risk_ips]
            self.assertIn(critical_event_ip, risk_ip_addresses)
    
    def test_categorization_service_with_real_data(self):
        """Test SecurityEventCategorizationService with real database events."""
        for event in self.events:
            categorization = SecurityEventCategorizationService.categorize_event(event)
            
            # Verify all required fields are present
            self.assertIn('category', categorization)
            self.assertIn('risk_score', categorization)
            self.assertIn('priority', categorization)
            self.assertIn('pattern_detected', categorization)
            self.assertIn('recommended_action', categorization)
            self.assertIn('escalation_required', categorization)
            
            # Verify data types
            self.assertIsInstance(categorization['risk_score'], float)
            self.assertGreaterEqual(categorization['risk_score'], 0)
            self.assertLessEqual(categorization['risk_score'], 10)
            
            self.assertIn(categorization['priority'], ['low', 'medium', 'high', 'critical'])
            self.assertIsInstance(categorization['pattern_detected'], bool)
            self.assertIsInstance(categorization['escalation_required'], bool)
            
            # Verify specific categorizations
            if event.event_type in ['login_failed', 'login_success']:
                self.assertEqual(categorization['category'], 'authentication')
            elif event.event_type in ['brute_force_attempt', 'suspicious_activity']:
                self.assertEqual(categorization['category'], 'account_security')
            elif event.event_type == 'privilege_escalation':
                self.assertEqual(categorization['category'], 'access_control')
                self.assertEqual(categorization['priority'], 'critical')
                self.assertTrue(categorization['escalation_required'])
            elif event.event_type == 'data_export':
                self.assertEqual(categorization['category'], 'data_operations')
            elif event.event_type == 'api_rate_limit':
                self.assertEqual(categorization['category'], 'system_security')
        
        # Test categorization summary
        summary = SecurityEventCategorizationService.get_categorized_events_summary()
        
        self.assertIn('category_summary', summary)
        self.assertIn('priority_summary', summary)
        self.assertIn('total_events', summary)
        self.assertEqual(summary['total_events'], 7)
        
        # Verify categories are present
        categories = summary['category_summary']
        expected_categories = ['authentication', 'account_security', 'access_control', 'data_operations', 'system_security']
        for category in expected_categories:
            if category in categories:
                self.assertGreater(categories[category]['count'], 0)
        
        # Verify priority summary
        priorities = summary['priority_summary']
        self.assertIn('critical', priorities)
        self.assertIn('high', priorities)
        self.assertIn('medium', priorities)
        self.assertIn('low', priorities)
        self.assertEqual(priorities['critical'], 1)  # privilege_escalation
    
    def test_investigation_service_with_real_data(self):
        """Test SecurityEventInvestigationService with real database operations."""
        # Get an unresolved event for testing
        unresolved_event = SecurityEvent.objects.filter(is_resolved=False).first()
        self.assertIsNotNone(unresolved_event)
        
        # Test assigning investigator
        result = SecurityEventInvestigationService.assign_investigator(
            event_id=unresolved_event.id,
            investigator_id=self.super_admin2.id,
            assigned_by_id=self.super_admin1.id,
            notes='Assigning for immediate investigation'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['investigator']['username'], 'investigator1')
        
        # Verify database was updated
        unresolved_event.refresh_from_db()
        self.assertEqual(unresolved_event.resolved_by, self.super_admin2)
        self.assertIn('Assigned to investigator1', unresolved_event.resolution_notes)
        
        # Test updating investigation status
        result = SecurityEventInvestigationService.update_investigation_status(
            event_id=unresolved_event.id,
            status='in_progress',
            updated_by_id=self.super_admin2.id,
            notes='Starting detailed investigation'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['new_status'], 'in_progress')
        self.assertFalse(result['is_resolved'])
        
        # Verify database was updated
        unresolved_event.refresh_from_db()
        self.assertIn('Status updated to \'in_progress\'', unresolved_event.resolution_notes)
        
        # Test adding investigation note
        result = SecurityEventInvestigationService.add_investigation_note(
            event_id=unresolved_event.id,
            note='Found suspicious patterns in user behavior logs',
            added_by_id=self.super_admin2.id,
            note_type='investigation'
        )
        
        self.assertTrue(result['success'])
        
        # Verify database was updated
        unresolved_event.refresh_from_db()
        self.assertIn('INVESTIGATION by investigator1', unresolved_event.resolution_notes)
        self.assertIn('Found suspicious patterns', unresolved_event.resolution_notes)
        
        # Test getting investigation timeline
        result = SecurityEventInvestigationService.get_investigation_timeline(unresolved_event.id)
        
        self.assertTrue(result['success'])
        self.assertIn('timeline', result)
        self.assertGreater(result['total_entries'], 0)
        
        timeline = result['timeline']
        # Should have at least: creation, assignment, status update, note
        self.assertGreaterEqual(len(timeline), 4)
        
        # Verify timeline entries
        entry_types = [entry['type'] for entry in timeline]
        self.assertIn('event_created', entry_types)
        self.assertIn('assignment', entry_types)
        self.assertIn('status_update', entry_types)
        self.assertIn('investigation', entry_types)
        
        # Test getting related events
        result = SecurityEventInvestigationService.get_related_events(unresolved_event.id)
        
        self.assertTrue(result['success'])
        self.assertIn('related_events', result)
        
        related = result['related_events']
        self.assertIn('by_ip', related)
        self.assertIn('by_user', related)
        self.assertIn('by_type', related)
        self.assertIn('suspicious_activities', related)
        
        # If the event has a user, should find related events by user
        if unresolved_event.user:
            self.assertGreater(len(related['by_user']), 0)
        
        # Should find related events by IP
        if unresolved_event.ip_address:
            # May or may not have related events by IP depending on test data
            self.assertIsInstance(related['by_ip'], list)
    
    def test_resolution_service_with_real_data(self):
        """Test SecurityEventResolutionService with real database operations."""
        # Get an unresolved event for testing
        unresolved_event = SecurityEvent.objects.filter(is_resolved=False).first()
        self.assertIsNotNone(unresolved_event)
        
        original_id = unresolved_event.id
        
        # Test resolving event
        result = SecurityEventResolutionService.resolve_event(
            event_id=unresolved_event.id,
            resolved_by_id=self.super_admin1.id,
            resolution_notes='Investigation complete - determined to be false positive',
            resolution_type='manual'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['resolved_by'], 'admin1')
        self.assertIn('resolved_at', result)
        
        # Verify database was updated
        unresolved_event.refresh_from_db()
        self.assertTrue(unresolved_event.is_resolved)
        self.assertEqual(unresolved_event.resolved_by, self.super_admin1)
        self.assertIsNotNone(unresolved_event.resolved_at)
        self.assertIn('RESOLVED by admin1', unresolved_event.resolution_notes)
        self.assertIn('Investigation complete', unresolved_event.resolution_notes)
        
        # Test resolving with follow-up required
        another_event = SecurityEvent.objects.filter(is_resolved=False).first()
        if another_event:
            result = SecurityEventResolutionService.resolve_event(
                event_id=another_event.id,
                resolved_by_id=self.super_admin1.id,
                resolution_notes='Resolved but requires monitoring',
                follow_up_required=True
            )
            
            self.assertTrue(result['success'])
            
            # Verify follow-up flag was added
            another_event.refresh_from_db()
            self.assertIn('[FOLLOW-UP REQUIRED]', another_event.resolution_notes)
        
        # Test reopening event
        result = SecurityEventResolutionService.reopen_event(
            event_id=original_id,
            reopened_by_id=self.super_admin2.id,
            reason='New evidence discovered - requires re-investigation'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['reopened_by'], 'investigator1')
        
        # Verify database was updated
        reopened_event = SecurityEvent.objects.get(id=original_id)
        self.assertFalse(reopened_event.is_resolved)
        self.assertIsNone(reopened_event.resolved_at)
        self.assertIn('REOPENED by investigator1', reopened_event.resolution_notes)
        self.assertIn('New evidence discovered', reopened_event.resolution_notes)
        
        # Test bulk resolution
        unresolved_events = SecurityEvent.objects.filter(is_resolved=False)[:3]
        event_ids = [event.id for event in unresolved_events]
        
        if event_ids:
            result = SecurityEventResolutionService.bulk_resolve_events(
                event_ids=event_ids,
                resolved_by_id=self.super_admin1.id,
                resolution_notes='Bulk resolution - all confirmed as false positives'
            )
            
            self.assertTrue(result['success'])
            self.assertEqual(result['resolved_count'], len(event_ids))
            self.assertEqual(result['failed_count'], 0)
            
            # Verify all events were resolved
            for event_id in event_ids:
                event = SecurityEvent.objects.get(id=event_id)
                self.assertTrue(event.is_resolved)
                self.assertIn('[BULK RESOLUTION]', event.resolution_notes)
    
    def test_audit_logging_integration(self):
        """Test that audit logs are created for security event operations."""
        initial_audit_count = AuditLog.objects.count()
        
        # Get an unresolved event
        unresolved_event = SecurityEvent.objects.filter(is_resolved=False).first()
        if not unresolved_event:
            # Create one if none exist
            unresolved_event = SecurityEvent.objects.create(
                event_type='test_event',
                severity='medium',
                ip_address='192.168.1.999'
            )
        
        # Perform operations that should create audit logs
        SecurityEventInvestigationService.assign_investigator(
            event_id=unresolved_event.id,
            investigator_id=self.super_admin1.id,
            assigned_by_id=self.super_admin2.id,
            notes='Test assignment'
        )
        
        SecurityEventInvestigationService.update_investigation_status(
            event_id=unresolved_event.id,
            status='in_progress',
            updated_by_id=self.super_admin1.id,
            notes='Test status update'
        )
        
        SecurityEventResolutionService.resolve_event(
            event_id=unresolved_event.id,
            resolved_by_id=self.super_admin1.id,
            resolution_notes='Test resolution'
        )
        
        # Verify audit logs were created
        final_audit_count = AuditLog.objects.count()
        self.assertGreater(final_audit_count, initial_audit_count)
        
        # Check for specific audit log entries
        recent_logs = AuditLog.objects.filter(
            created_at__gte=timezone.now() - timedelta(minutes=1)
        )
        
        log_actions = [log.action for log in recent_logs]
        expected_actions = [
            'security_event_assign',
            'security_event_status_update',
            'security_event_resolve'
        ]
        
        for action in expected_actions:
            self.assertIn(action, log_actions)
    
    def test_error_handling_with_real_database(self):
        """Test error handling with real database constraints."""
        # Test with non-existent event ID
        result = SecurityEventInvestigationService.assign_investigator(
            event_id=99999,
            investigator_id=self.super_admin1.id,
            assigned_by_id=self.super_admin2.id
        )
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Security event not found')
        
        # Test with non-existent investigator ID
        valid_event = SecurityEvent.objects.filter(is_resolved=False).first()
        if valid_event:
            result = SecurityEventInvestigationService.assign_investigator(
                event_id=valid_event.id,
                investigator_id=99999,
                assigned_by_id=self.super_admin1.id
            )
            
            self.assertFalse(result['success'])
            self.assertEqual(result['error'], 'Investigator not found')
        
        # Test reopening an unresolved event
        unresolved_event = SecurityEvent.objects.filter(is_resolved=False).first()
        if unresolved_event:
            result = SecurityEventResolutionService.reopen_event(
                event_id=unresolved_event.id,
                reopened_by_id=self.super_admin1.id,
                reason='Test reason'
            )
            
            self.assertFalse(result['success'])
            self.assertEqual(result['error'], 'Event is not resolved')
    
    def test_performance_with_large_dataset(self):
        """Test performance with a larger dataset."""
        # Create additional events for performance testing
        bulk_events = []
        for i in range(50):
            bulk_events.append(SecurityEvent(
                event_type='login_failed',
                severity='medium',
                ip_address=f'192.168.2.{i}',
                user_agent='Performance Test Browser',
                username_attempted=f'testuser{i}',
                details={'test': True, 'batch': i}
            ))
        
        SecurityEvent.objects.bulk_create(bulk_events)
        
        # Test filtering performance
        start_time = timezone.now()
        events, metadata = SecurityEventFilterService.get_filtered_events(
            per_page=20,
            page=1
        )
        end_time = timezone.now()
        
        # Should complete quickly (less than 1 second for this dataset)
        duration = (end_time - start_time).total_seconds()
        self.assertLess(duration, 1.0)
        
        # Verify results
        self.assertEqual(len(events), 20)
        self.assertGreater(metadata['total_count'], 50)
        
        # Test statistics performance
        start_time = timezone.now()
        stats = SecurityEventFilterService.get_event_statistics()
        end_time = timezone.now()
        
        duration = (end_time - start_time).total_seconds()
        self.assertLess(duration, 2.0)
        
        # Verify statistics are accurate
        self.assertGreater(stats['total_events'], 50)
    
    def tearDown(self):
        """Clean up test data."""
        # Django's TransactionTestCase will handle database cleanup
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])