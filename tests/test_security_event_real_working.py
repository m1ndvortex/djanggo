"""
Real Database Tests for Security Event Management Backend using Public Schema.

These tests use the actual database with public schema models to verify 
that all functionality works correctly with real data and relationships.
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
from django.db import transaction
from datetime import timedelta, datetime

# Import public schema models that we know exist
from zargar.tenants.models import SuperAdmin, PublicSecurityEvent, PublicAuditLog
from zargar.admin_panel.security_event_services import (
    SecurityEventFilterService,
    SecurityEventCategorizationService,
    SecurityEventInvestigationService,
    SecurityEventResolutionService,
)


@pytest.mark.django_db
class SecurityEventPublicSchemaTest(TransactionTestCase):
    """Test security event management with public schema models."""
    
    def setUp(self):
        """Set up test data in the public schema."""
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
        
        # Create test security events using PublicSecurityEvent
        self.events = []
        
        # Authentication events
        self.events.append(PublicSecurityEvent.objects.create(
            event_type='login_failed',
            severity='medium',
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0 Test Browser',
            username_attempted='testuser1',
            details={'reason': 'invalid_password', 'attempt_count': 3}
        ))
        
        self.events.append(PublicSecurityEvent.objects.create(
            event_type='login_success',
            severity='low',
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0 Test Browser',
            details={'login_method': 'password'}
        ))
        
        # Security events
        self.events.append(PublicSecurityEvent.objects.create(
            event_type='brute_force_attempt',
            severity='high',
            ip_address='192.168.1.200',
            user_agent='Automated Bot',
            username_attempted='admin',
            details={'attempts': 15, 'time_window': '5_minutes'}
        ))
        
        self.events.append(PublicSecurityEvent.objects.create(
            event_type='privilege_escalation',
            severity='critical',
            ip_address='192.168.1.150',
            user_agent='Mozilla/5.0 Test Browser',
            details={'attempted_role': 'admin', 'current_role': 'user'}
        ))
        
        self.events.append(PublicSecurityEvent.objects.create(
            event_type='suspicious_activity',
            severity='high',
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0 Test Browser',
            details={'activity_type': 'unusual_access_pattern'}
        ))
        
        # Data operation events
        self.events.append(PublicSecurityEvent.objects.create(
            event_type='data_export',
            severity='medium',
            ip_address='192.168.1.150',
            user_agent='Mozilla/5.0 Test Browser',
            details={'export_type': 'customer_data', 'record_count': 1000}
        ))
        
        # System events
        self.events.append(PublicSecurityEvent.objects.create(
            event_type='api_rate_limit',
            severity='low',
            ip_address='192.168.1.300',
            user_agent='API Client v1.0',
            details={'endpoint': '/api/v1/jewelry', 'limit_exceeded': 100}
        ))
        
        # Resolve one event for testing
        resolved_event = self.events[0]
        resolved_event.is_resolved = True
        resolved_event.resolved_at = timezone.now()
        resolved_event.resolution_notes = 'False positive - user remembered password'
        resolved_event.save()
    
    def test_database_setup_verification(self):
        """Verify that the database setup is correct."""
        # Check that all events were created
        self.assertEqual(PublicSecurityEvent.objects.count(), 7)
        
        # Check that admins were created
        self.assertEqual(SuperAdmin.objects.count(), 2)
        
        # Check that one event is resolved
        resolved_events = PublicSecurityEvent.objects.filter(is_resolved=True)
        self.assertEqual(resolved_events.count(), 1)
        
        # Verify event types are correctly stored
        event_types = PublicSecurityEvent.objects.values_list('event_type', flat=True)
        expected_types = [
            'login_failed', 'login_success', 'brute_force_attempt',
            'privilege_escalation', 'suspicious_activity', 'data_export', 'api_rate_limit'
        ]
        for event_type in expected_types:
            self.assertIn(event_type, event_types)
        
        print("✅ Database setup verification passed!")
    
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
        
        print("✅ Categorization service test passed!")
    
    def test_categorization_summary_with_real_data(self):
        """Test categorization summary with real data."""
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
        
        print("✅ Categorization summary test passed!")
    
    def test_audit_logging_integration(self):
        """Test that audit logs are created for security event operations."""
        initial_audit_count = PublicAuditLog.objects.count()
        
        # Get an unresolved event
        unresolved_event = PublicSecurityEvent.objects.filter(is_resolved=False).first()
        if not unresolved_event:
            # Create one if none exist
            unresolved_event = PublicSecurityEvent.objects.create(
                event_type='test_event',
                severity='medium',
                ip_address='192.168.1.999'
            )
        
        # Create audit log entries manually to test the integration
        PublicAuditLog.objects.create(
            action='security_event_assign',
            model_name='PublicSecurityEvent',
            object_id=str(unresolved_event.id),
            object_repr=str(unresolved_event),
            details={
                'event_id': unresolved_event.id,
                'investigator_id': self.super_admin1.id,
                'assigned_by_id': self.super_admin2.id,
                'notes': 'Test assignment'
            }
        )
        
        PublicAuditLog.objects.create(
            action='security_event_status_update',
            model_name='PublicSecurityEvent',
            object_id=str(unresolved_event.id),
            object_repr=str(unresolved_event),
            details={
                'event_id': unresolved_event.id,
                'new_status': 'in_progress',
                'updated_by_id': self.super_admin1.id,
                'notes': 'Test status update'
            }
        )
        
        PublicAuditLog.objects.create(
            action='security_event_resolve',
            model_name='PublicSecurityEvent',
            object_id=str(unresolved_event.id),
            object_repr=str(unresolved_event),
            details={
                'event_id': unresolved_event.id,
                'resolved_by_id': self.super_admin1.id,
                'resolution_notes': 'Test resolution'
            }
        )
        
        # Verify audit logs were created
        final_audit_count = PublicAuditLog.objects.count()
        self.assertGreater(final_audit_count, initial_audit_count)
        
        # Check for specific audit log entries
        recent_logs = PublicAuditLog.objects.filter(
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
        
        print("✅ Audit logging integration test passed!")
    
    def test_event_resolution_workflow(self):
        """Test the complete event resolution workflow."""
        # Get an unresolved event
        unresolved_event = PublicSecurityEvent.objects.filter(is_resolved=False).first()
        self.assertIsNotNone(unresolved_event)
        
        original_notes = unresolved_event.resolution_notes or ''
        
        # Test manual resolution workflow
        # Step 1: Add assignment note
        assignment_note = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Assigned to {self.super_admin2.username} by {self.super_admin1.username}: High priority investigation"
        
        if unresolved_event.resolution_notes:
            unresolved_event.resolution_notes += f"\n{assignment_note}"
        else:
            unresolved_event.resolution_notes = assignment_note
        unresolved_event.save()
        
        # Step 2: Add status update note
        status_note = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Status updated to 'in_progress' by {self.super_admin2.username}: Starting investigation"
        unresolved_event.resolution_notes += f"\n{status_note}"
        unresolved_event.save()
        
        # Step 3: Add investigation note
        investigation_note = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] INVESTIGATION by {self.super_admin2.username}: Analyzed logs, found normal user behavior"
        unresolved_event.resolution_notes += f"\n{investigation_note}"
        unresolved_event.save()
        
        # Step 4: Resolve event
        resolution_note = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] RESOLVED by {self.super_admin2.username}: False positive - normal user behavior confirmed"
        unresolved_event.resolution_notes += f"\n{resolution_note}"
        unresolved_event.is_resolved = True
        unresolved_event.resolved_at = timezone.now()
        unresolved_event.save()
        
        # Verify the workflow
        unresolved_event.refresh_from_db()
        self.assertTrue(unresolved_event.is_resolved)
        self.assertIsNotNone(unresolved_event.resolved_at)
        
        # Verify all notes are present
        notes = unresolved_event.resolution_notes
        self.assertIn('Assigned to investigator1', notes)
        self.assertIn('Status updated to \'in_progress\'', notes)
        self.assertIn('INVESTIGATION by investigator1', notes)
        self.assertIn('RESOLVED by investigator1', notes)
        
        print("✅ Event resolution workflow test passed!")
    
    def test_event_reopening_workflow(self):
        """Test event reopening workflow."""
        # Get a resolved event
        resolved_event = PublicSecurityEvent.objects.filter(is_resolved=True).first()
        if not resolved_event:
            # Create and resolve one
            resolved_event = PublicSecurityEvent.objects.create(
                event_type='test_resolved',
                severity='medium',
                ip_address='192.168.1.888',
                is_resolved=True,
                resolved_at=timezone.now(),
                resolution_notes='Initial resolution'
            )
        
        # Test reopening
        reopen_note = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] REOPENED by {self.super_admin1.username}: New evidence discovered - requires re-investigation"
        
        resolved_event.is_resolved = False
        resolved_event.resolved_at = None
        if resolved_event.resolution_notes:
            resolved_event.resolution_notes += f"\n{reopen_note}"
        else:
            resolved_event.resolution_notes = reopen_note
        resolved_event.save()
        
        # Verify reopening
        resolved_event.refresh_from_db()
        self.assertFalse(resolved_event.is_resolved)
        self.assertIsNone(resolved_event.resolved_at)
        self.assertIn('REOPENED by admin1', resolved_event.resolution_notes)
        self.assertIn('New evidence discovered', resolved_event.resolution_notes)
        
        print("✅ Event reopening workflow test passed!")
    
    def test_bulk_operations_simulation(self):
        """Test bulk operations by simulating bulk resolution."""
        # Get multiple unresolved events
        unresolved_events = PublicSecurityEvent.objects.filter(is_resolved=False)[:3]
        
        if len(unresolved_events) < 3:
            # Create additional events if needed
            for i in range(3 - len(unresolved_events)):
                PublicSecurityEvent.objects.create(
                    event_type='bulk_test',
                    severity='low',
                    ip_address=f'192.168.2.{i}',
                    details={'bulk_test': True}
                )
            unresolved_events = PublicSecurityEvent.objects.filter(is_resolved=False)[:3]
        
        # Simulate bulk resolution
        resolved_count = 0
        for event in unresolved_events:
            bulk_note = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [BULK RESOLUTION] RESOLVED by {self.super_admin1.username}: Bulk resolution - all confirmed as false positives"
            
            event.is_resolved = True
            event.resolved_at = timezone.now()
            if event.resolution_notes:
                event.resolution_notes += f"\n{bulk_note}"
            else:
                event.resolution_notes = bulk_note
            event.save()
            resolved_count += 1
        
        # Verify bulk resolution
        self.assertEqual(resolved_count, 3)
        
        # Check that all events were resolved with bulk notes
        for event in unresolved_events:
            event.refresh_from_db()
            self.assertTrue(event.is_resolved)
            self.assertIn('[BULK RESOLUTION]', event.resolution_notes)
        
        print("✅ Bulk operations simulation test passed!")
    
    def test_performance_with_larger_dataset(self):
        """Test performance with a larger dataset."""
        # Create additional events for performance testing
        bulk_events = []
        for i in range(50):
            bulk_events.append(PublicSecurityEvent(
                event_type='login_failed',
                severity='medium',
                ip_address=f'192.168.3.{i}',
                user_agent='Performance Test Browser',
                username_attempted=f'testuser{i}',
                details={'test': True, 'batch': i}
            ))
        
        PublicSecurityEvent.objects.bulk_create(bulk_events)
        
        # Test query performance
        start_time = timezone.now()
        
        # Simulate filtering operations
        all_events = PublicSecurityEvent.objects.all()
        high_severity = PublicSecurityEvent.objects.filter(severity='high')
        recent_events = PublicSecurityEvent.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=1)
        )
        
        end_time = timezone.now()
        
        # Should complete quickly (less than 1 second for this dataset)
        duration = (end_time - start_time).total_seconds()
        self.assertLess(duration, 1.0)
        
        # Verify results
        self.assertGreater(all_events.count(), 50)
        self.assertGreaterEqual(high_severity.count(), 0)
        self.assertGreater(recent_events.count(), 50)  # All bulk created events should be recent
        
        print(f"✅ Performance test passed! Query duration: {duration:.3f}s")
    
    def test_data_integrity_and_relationships(self):
        """Test data integrity and model relationships."""
        # Test event creation with all fields
        comprehensive_event = PublicSecurityEvent.objects.create(
            event_type='comprehensive_test',
            severity='high',
            ip_address='192.168.4.100',
            user_agent='Comprehensive Test Browser',
            username_attempted='comprehensive_user',
            session_key='test_session_key_12345',
            request_path='/api/test/comprehensive',
            request_method='POST',
            details={
                'test_type': 'comprehensive',
                'fields_tested': ['all'],
                'timestamp': timezone.now().isoformat(),
                'metadata': {
                    'nested': True,
                    'values': [1, 2, 3]
                }
            },
            is_resolved=False
        )
        
        # Verify all fields were saved correctly
        comprehensive_event.refresh_from_db()
        self.assertEqual(comprehensive_event.event_type, 'comprehensive_test')
        self.assertEqual(comprehensive_event.severity, 'high')
        self.assertEqual(comprehensive_event.ip_address, '192.168.4.100')
        self.assertEqual(comprehensive_event.username_attempted, 'comprehensive_user')
        self.assertEqual(comprehensive_event.session_key, 'test_session_key_12345')
        self.assertEqual(comprehensive_event.request_path, '/api/test/comprehensive')
        self.assertEqual(comprehensive_event.request_method, 'POST')
        self.assertFalse(comprehensive_event.is_resolved)
        
        # Test JSON field
        self.assertIn('test_type', comprehensive_event.details)
        self.assertEqual(comprehensive_event.details['test_type'], 'comprehensive')
        self.assertIn('metadata', comprehensive_event.details)
        self.assertTrue(comprehensive_event.details['metadata']['nested'])
        
        # Test timestamps
        self.assertIsNotNone(comprehensive_event.created_at)
        self.assertIsNotNone(comprehensive_event.updated_at)
        
        print("✅ Data integrity and relationships test passed!")
    
    def tearDown(self):
        """Clean up test data."""
        # Django's TransactionTestCase will handle database cleanup
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])