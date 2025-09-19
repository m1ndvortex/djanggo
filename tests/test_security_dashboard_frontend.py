"""
Frontend tests for security dashboard functionality.
"""
import pytest
import django
from django.conf import settings
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

# Configure Django settings before importing models
if not settings.configured:
    django.setup()

from zargar.core.security_models import SecurityEvent, AuditLog, SuspiciousActivity, RateLimitAttempt

User = get_user_model()


class SecurityDashboardFrontendTestCase(TestCase):
    """Test cases for security dashboard frontend functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create super admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        self.admin_user.is_super_admin = True
        self.admin_user.save()
        
        # Create regular user for testing
        self.regular_user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123'
        )
        
        # Create test security events
        self.security_event = SecurityEvent.objects.create(
            event_type='login_failed',
            severity='high',
            user=self.regular_user,
            ip_address='192.168.1.100',
            user_agent='Test Browser',
            details={'test': 'data'}
        )
        
        # Create test audit log
        self.audit_log = AuditLog.objects.create(
            action='login',
            user=self.regular_user,
            ip_address='192.168.1.100',
            details={'test': 'audit'}
        )
        
        # Create test suspicious activity
        self.suspicious_activity = SuspiciousActivity.objects.create(
            activity_type='multiple_failed_logins',
            risk_level='high',
            user=self.regular_user,
            ip_address='192.168.1.100',
            confidence_score=0.8
        )
        
        # Create test rate limit attempt
        self.rate_limit = RateLimitAttempt.objects.create(
            identifier='192.168.1.100',
            limit_type='login',
            attempts=5,
            is_blocked=True
        )
    
    def test_security_dashboard_access_requires_super_admin(self):
        """Test that security dashboard requires super admin access."""
        # Test unauthenticated access
        response = self.client.get(reverse('core:security_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Test regular user access
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:security_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect due to no permission
        
        # Test super admin access
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:security_dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_security_dashboard_displays_statistics(self):
        """Test that security dashboard displays correct statistics."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:security_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'داشبورد امنیت سیستم')
        self.assertContains(response, 'رویدادهای بحرانی')
        self.assertContains(response, 'فعالیت‌های مشکوک')
        
        # Check that statistics are present in context
        self.assertIn('security_stats', response.context)
        self.assertIn('critical_events', response.context)
        self.assertIn('suspicious_activities', response.context)
    
    def test_security_events_list_view(self):
        """Test security events list view functionality."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:security_events'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'رویدادهای امنیتی')
        self.assertContains(response, self.security_event.get_event_type_display())
        self.assertContains(response, self.security_event.ip_address)
    
    def test_security_events_filtering(self):
        """Test security events filtering functionality."""
        self.client.login(username='admin', password='testpass123')
        
        # Test event type filter
        response = self.client.get(reverse('core:security_events'), {
            'event_type': 'login_failed'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.security_event.ip_address)
        
        # Test severity filter
        response = self.client.get(reverse('core:security_events'), {
            'severity': 'high'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.security_event.ip_address)
        
        # Test search functionality
        response = self.client.get(reverse('core:security_events'), {
            'search': '192.168.1.100'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.security_event.ip_address)
    
    def test_security_event_detail_view(self):
        """Test security event detail view."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(
            reverse('core:security_event_detail', args=[self.security_event.pk])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'جزئیات رویداد امنیتی')
        self.assertContains(response, self.security_event.get_event_type_display())
        self.assertContains(response, self.security_event.ip_address)
        self.assertContains(response, self.security_event.user.username)
    
    def test_security_event_resolve_functionality(self):
        """Test security event resolution functionality."""
        self.client.login(username='admin', password='testpass123')
        
        # Test resolving an event
        response = self.client.post(
            reverse('core:security_event_resolve', args=[self.security_event.pk]),
            {
                'resolution_notes': 'Test resolution'
            },
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check that event is resolved
        self.security_event.refresh_from_db()
        self.assertTrue(self.security_event.is_resolved)
        self.assertEqual(self.security_event.resolved_by, self.admin_user)
        self.assertEqual(self.security_event.resolution_notes, 'Test resolution')
    
    def test_suspicious_activities_list_view(self):
        """Test suspicious activities list view."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:suspicious_activities'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'فعالیت‌های مشکوک')
        self.assertContains(response, self.suspicious_activity.get_activity_type_display())
        self.assertContains(response, self.suspicious_activity.ip_address)
    
    def test_suspicious_activities_filtering(self):
        """Test suspicious activities filtering."""
        self.client.login(username='admin', password='testpass123')
        
        # Test activity type filter
        response = self.client.get(reverse('core:suspicious_activities'), {
            'activity_type': 'multiple_failed_logins'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.suspicious_activity.ip_address)
        
        # Test risk level filter
        response = self.client.get(reverse('core:suspicious_activities'), {
            'risk_level': 'high'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.suspicious_activity.ip_address)
    
    def test_suspicious_activity_investigation(self):
        """Test suspicious activity investigation functionality."""
        self.client.login(username='admin', password='testpass123')
        
        # Test investigating an activity
        response = self.client.post(
            reverse('core:suspicious_activity_investigate', args=[self.suspicious_activity.pk]),
            {
                'is_false_positive': 'false',
                'investigation_notes': 'Test investigation'
            },
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check that activity is investigated
        self.suspicious_activity.refresh_from_db()
        self.assertTrue(self.suspicious_activity.is_investigated)
        self.assertEqual(self.suspicious_activity.investigated_by, self.admin_user)
        self.assertEqual(self.suspicious_activity.investigation_notes, 'Test investigation')
        self.assertFalse(self.suspicious_activity.is_false_positive)
    
    def test_audit_logs_list_view(self):
        """Test audit logs list view."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:audit_logs'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'گزارش‌های حسابرسی')
        self.assertContains(response, self.audit_log.get_action_display())
        self.assertContains(response, self.audit_log.user.username)
    
    def test_audit_logs_filtering(self):
        """Test audit logs filtering."""
        self.client.login(username='admin', password='testpass123')
        
        # Test action filter
        response = self.client.get(reverse('core:audit_logs'), {
            'action': 'login'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.audit_log.user.username)
        
        # Test user filter
        response = self.client.get(reverse('core:audit_logs'), {
            'user_id': self.regular_user.id
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.audit_log.user.username)
    
    def test_rate_limits_list_view(self):
        """Test rate limits list view."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:rate_limits'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'محدودیت‌های نرخ')
        self.assertContains(response, self.rate_limit.identifier)
        self.assertContains(response, self.rate_limit.get_limit_type_display())
    
    def test_rate_limit_unblock_functionality(self):
        """Test rate limit unblock functionality."""
        self.client.login(username='admin', password='testpass123')
        
        # Test unblocking a rate limit
        response = self.client.post(
            reverse('core:unblock_rate_limit', args=[self.rate_limit.pk]),
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check that rate limit is unblocked
        self.rate_limit.refresh_from_db()
        self.assertFalse(self.rate_limit.is_blocked)
        self.assertIsNone(self.rate_limit.blocked_until)
    
    def test_security_alerts_api(self):
        """Test security alerts API endpoint."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:security_alerts_api'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Parse JSON response
        import json
        data = json.loads(response.content)
        
        self.assertIn('alerts', data)
        self.assertIn('total_alerts', data)
        self.assertIn('timestamp', data)
    
    def test_theme_support_in_templates(self):
        """Test that templates support both light and dark themes."""
        self.client.login(username='admin', password='testpass123')
        
        # Test with light theme
        response = self.client.get(reverse('core:security_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'bg-gray-50')  # Light theme class
        
        # Test with dark theme (would need session/cookie setup for full test)
        # This is a basic check that dark theme classes are present in template
        self.assertContains(response, 'cyber-glass-card')  # Dark theme class
    
    def test_persian_rtl_support(self):
        """Test that templates support Persian RTL layout."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:security_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        # Check for RTL and Persian text
        self.assertContains(response, 'داشبورد امنیت سیستم')
        self.assertContains(response, 'رویدادهای بحرانی')
        self.assertContains(response, 'فعالیت‌های مشکوک')
    
    def test_responsive_design_classes(self):
        """Test that templates include responsive design classes."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:security_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        # Check for responsive grid classes
        self.assertContains(response, 'grid-cols-1')
        self.assertContains(response, 'md:grid-cols-2')
        self.assertContains(response, 'lg:grid-cols-4')
    
    def test_pagination_functionality(self):
        """Test pagination in list views."""
        # Create many security events to test pagination
        for i in range(30):
            SecurityEvent.objects.create(
                event_type='login_failed',
                severity='medium',
                ip_address=f'192.168.1.{i}',
                user_agent='Test Browser'
            )
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:security_events'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'صفحه')  # Persian pagination text
        
        # Test second page
        response = self.client.get(reverse('core:security_events'), {'page': 2})
        self.assertEqual(response.status_code, 200)


class SecurityDashboardJavaScriptTestCase(TestCase):
    """Test cases for JavaScript functionality in security dashboard."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create super admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        self.admin_user.is_super_admin = True
        self.admin_user.save()
    
    def test_security_dashboard_includes_javascript(self):
        """Test that security dashboard includes necessary JavaScript."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:security_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        # Check for JavaScript functions
        self.assertContains(response, 'securityAlerts()')
        self.assertContains(response, 'startPolling()')
        self.assertContains(response, 'fetchAlerts()')
    
    def test_events_list_includes_modal_javascript(self):
        """Test that events list includes modal JavaScript."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:security_events'))
        
        self.assertEqual(response.status_code, 200)
        # Check for modal functions
        self.assertContains(response, 'resolveEvent(')
        self.assertContains(response, 'closeResolveModal()')
    
    def test_suspicious_activities_includes_investigation_javascript(self):
        """Test that suspicious activities includes investigation JavaScript."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:suspicious_activities'))
        
        self.assertEqual(response.status_code, 200)
        # Check for investigation functions
        self.assertContains(response, 'investigateActivity(')
        self.assertContains(response, 'closeInvestigationModal()')
        self.assertContains(response, 'bulkInvestigate()')


if __name__ == '__main__':
    pytest.main([__file__])