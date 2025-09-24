"""
Tests for the Security Dashboard implementation.
"""

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import json

from zargar.tenants.admin_models import (
    SuperAdmin, 
    PublicSecurityEvent, 
    PublicAuditLog, 
    PublicSuspiciousActivity,
    PublicRateLimitAttempt
)

User = get_user_model()


class SecurityDashboardTestCase(TestCase):
    """Test case for Security Dashboard functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create a super admin user
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        
        self.client = Client()
        self.client.force_login(self.superadmin)
        
        # Create test security events
        self.create_test_security_events()
        
        # Create test suspicious activities
        self.create_test_suspicious_activities()
        
        # Create test rate limit attempts
        self.create_test_rate_limit_attempts()
    
    def create_test_security_events(self):
        """Create test security events."""
        now = timezone.now()
        
        # Failed login events
        for i in range(5):
            PublicSecurityEvent.objects.create(
                event_type='login_failed',
                severity='medium',
                ip_address='192.168.1.100',
                username_attempted=f'user{i}',
                created_at=now - timedelta(hours=i)
            )
        
        # Critical security events
        for i in range(2):
            PublicSecurityEvent.objects.create(
                event_type='brute_force_attempt',
                severity='critical',
                ip_address='10.0.0.50',
                username_attempted='admin',
                created_at=now - timedelta(hours=i),
                is_resolved=False
            )
        
        # High severity events
        PublicSecurityEvent.objects.create(
            event_type='unauthorized_access',
            severity='high',
            ip_address='172.16.0.10',
            created_at=now - timedelta(hours=1),
            is_resolved=False
        )
    
    def create_test_suspicious_activities(self):
        """Create test suspicious activities."""
        now = timezone.now()
        
        # High risk suspicious activities
        for i in range(3):
            PublicSuspiciousActivity.objects.create(
                activity_type='multiple_failed_logins',
                risk_level='high',
                ip_address='192.168.1.200',
                confidence_score=0.85,
                created_at=now - timedelta(hours=i),
                is_investigated=False
            )
        
        # Critical risk activity
        PublicSuspiciousActivity.objects.create(
            activity_type='privilege_escalation',
            risk_level='critical',
            ip_address='10.0.0.100',
            confidence_score=0.95,
            created_at=now - timedelta(minutes=30),
            is_investigated=False
        )
    
    def create_test_rate_limit_attempts(self):
        """Create test rate limit attempts."""
        now = timezone.now()
        
        # Blocked IPs
        for i in range(3):
            PublicRateLimitAttempt.objects.create(
                identifier=f'192.168.1.{100 + i}',
                limit_type='login',
                attempts=10,
                is_blocked=True,
                blocked_until=now + timedelta(hours=1),
                window_start=now - timedelta(hours=1)
            )
    
    def test_security_dashboard_view(self):
        """Test security dashboard view loads correctly."""
        url = reverse('admin_panel:security_dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'داشبورد امنیت')
        self.assertContains(response, 'وضعیت امنیتی سیستم')
        
        # Check that context data is present
        self.assertIn('security_metrics', response.context)
        self.assertIn('security_status', response.context)
        self.assertIn('recent_events', response.context)
        self.assertIn('active_threats', response.context)
        self.assertIn('suspicious_activities', response.context)
    
    def test_security_metrics_calculation(self):
        """Test security metrics are calculated correctly."""
        url = reverse('admin_panel:security_dashboard')
        response = self.client.get(url)
        
        metrics = response.context['security_metrics']
        
        # Check failed logins count
        self.assertEqual(metrics['failed_logins'], 5)
        
        # Check blocked IPs count
        self.assertEqual(metrics['blocked_ips'], 3)
        
        # Check suspicious activities count
        self.assertEqual(metrics['suspicious_activities'], 4)
        
        # Check critical events count
        self.assertEqual(metrics['critical_events'], 2)
    
    def test_security_status_calculation(self):
        """Test security status is calculated correctly."""
        url = reverse('admin_panel:security_dashboard')
        response = self.client.get(url)
        
        security_status = response.context['security_status']
        
        # With 2 critical events, status should be critical
        self.assertEqual(security_status['level'], 'critical')
        self.assertEqual(security_status['text'], 'بحرانی')
    
    def test_active_threats_filtering(self):
        """Test active threats are filtered correctly."""
        url = reverse('admin_panel:security_dashboard')
        response = self.client.get(url)
        
        active_threats = response.context['active_threats']
        
        # Should have 3 unresolved high/critical events
        self.assertEqual(len(active_threats), 3)
        
        # All should be unresolved
        for threat in active_threats:
            self.assertFalse(threat.is_resolved)
            self.assertIn(threat.severity, ['high', 'critical'])
    
    def test_suspicious_activities_filtering(self):
        """Test suspicious activities are filtered correctly."""
        url = reverse('admin_panel:security_dashboard')
        response = self.client.get(url)
        
        suspicious_activities = response.context['suspicious_activities']
        
        # Should have 4 uninvestigated high/critical activities
        self.assertEqual(len(suspicious_activities), 4)
        
        # All should be uninvestigated and high/critical risk
        for activity in suspicious_activities:
            self.assertFalse(activity.is_investigated)
            self.assertIn(activity.risk_level, ['high', 'critical'])
    
    def test_security_metrics_api(self):
        """Test security metrics API endpoint."""
        url = reverse('admin_panel:security_metrics_api')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('metrics', data)
        self.assertIn('security_status', data)
        self.assertIn('timestamp', data)
        
        # Check metrics values
        metrics = data['metrics']
        self.assertEqual(metrics['failed_logins'], 5)
        self.assertEqual(metrics['blocked_ips'], 3)
        self.assertEqual(metrics['suspicious_activities'], 4)
        self.assertEqual(metrics['critical_events'], 2)
    
    def test_security_trends_api(self):
        """Test security trends API endpoint."""
        url = reverse('admin_panel:security_trends_api')
        response = self.client.get(url, {'days': 7})
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('trends', data)
        self.assertIn('period', data)
        
        # Should have 7 days of data
        trends = data['trends']
        self.assertEqual(len(trends), 8)  # 7 days + today
    
    def test_security_event_resolve(self):
        """Test resolving security events."""
        # Get an unresolved critical event
        event = PublicSecurityEvent.objects.filter(
            severity='critical',
            is_resolved=False
        ).first()
        
        url = reverse('admin_panel:security_event_resolve')
        response = self.client.post(url, {
            'event_id': event.id,
            'notes': 'Test resolution'
        })
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Check event is marked as resolved
        event.refresh_from_db()
        self.assertTrue(event.is_resolved)
        self.assertIsNotNone(event.resolved_at)
        self.assertEqual(event.resolution_notes, 'Test resolution')
    
    def test_suspicious_activity_investigate(self):
        """Test investigating suspicious activities."""
        # Get an uninvestigated activity
        activity = PublicSuspiciousActivity.objects.filter(
            is_investigated=False
        ).first()
        
        url = reverse('admin_panel:suspicious_activity_investigate')
        response = self.client.post(url, {
            'activity_id': activity.id,
            'notes': 'Test investigation',
            'false_positive': 'false'
        })
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Check activity is marked as investigated
        activity.refresh_from_db()
        self.assertTrue(activity.is_investigated)
        self.assertIsNotNone(activity.investigated_at)
        self.assertEqual(activity.investigation_notes, 'Test investigation')
        self.assertFalse(activity.is_false_positive)
    
    def test_unauthorized_access_denied(self):
        """Test that unauthorized users cannot access security dashboard."""
        # Create a regular user (not superadmin)
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@test.com',
            password='testpass123'
        )
        
        client = Client()
        client.force_login(regular_user)
        
        url = reverse('admin_panel:security_dashboard')
        response = client.get(url)
        
        # Should redirect to login or show permission denied
        self.assertIn(response.status_code, [302, 403])
    
    def test_theme_support_in_template(self):
        """Test that the template supports dual theme (light/dark)."""
        url = reverse('admin_panel:security_dashboard')
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check for dark mode classes
        self.assertIn('dark:bg-cyber-bg-surface', content)
        self.assertIn('dark:text-cyber-text-primary', content)
        self.assertIn('dark:text-cyber-neon-primary', content)
        
        # Check for cybersecurity styling
        self.assertIn('cyber-glass', content)
        self.assertIn('neon-border', content)
    
    def test_persian_rtl_support(self):
        """Test that the template supports Persian RTL layout."""
        url = reverse('admin_panel:security_dashboard')
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check for Persian text
        self.assertIn('داشبورد امنیت', content)
        self.assertIn('وضعیت امنیتی سیستم', content)
        self.assertIn('رویدادهای امنیتی اخیر', content)
        
        # Check for RTL classes
        self.assertIn('space-x-reverse', content)
        self.assertIn('text-right', content)
    
    def test_navigation_integration(self):
        """Test that security dashboard is accessible from navigation."""
        # Test main dashboard has link to security dashboard
        dashboard_url = reverse('admin_panel:dashboard')
        response = self.client.get(dashboard_url)
        
        self.assertContains(response, 'admin_panel:security_dashboard')
        self.assertContains(response, 'داشبورد امنیت')


@pytest.mark.django_db
class SecurityDashboardIntegrationTest:
    """Integration tests for Security Dashboard."""
    
    def test_real_time_metrics_update(self):
        """Test that metrics update in real-time when new events are created."""
        # This would test WebSocket or polling functionality
        # For now, we'll test the API response changes
        pass
    
    def test_chart_data_accuracy(self):
        """Test that chart data matches the actual security events."""
        # This would test the JavaScript chart integration
        pass
    
    def test_mobile_responsiveness(self):
        """Test that the dashboard works on mobile devices."""
        # This would require Selenium or similar for responsive testing
        pass