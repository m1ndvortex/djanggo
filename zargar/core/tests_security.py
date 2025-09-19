"""
Tests for security and audit logging functionality.
"""
import json
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.http import JsonResponse

from .security_models import SecurityEvent, AuditLog, RateLimitAttempt, SuspiciousActivity
from .security_middleware import (
    SecurityAuditMiddleware, RateLimitMiddleware, 
    SuspiciousActivityDetectionMiddleware
)
from .security_utils import SecurityMonitor, SecurityValidator, AuditLogger, ThreatDetector

User = get_user_model()


class SecurityEventModelTest(TestCase):
    """Test SecurityEvent model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.factory = RequestFactory()
    
    def test_create_security_event(self):
        """Test creating a security event."""
        event = SecurityEvent.objects.create(
            event_type='login_success',
            severity='low',
            user=self.user,
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            details={'test': 'data'}
        )
        
        self.assertEqual(event.event_type, 'login_success')
        self.assertEqual(event.severity, 'low')
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.ip_address, '192.168.1.1')
        self.assertEqual(event.details, {'test': 'data'})
    
    def test_log_event_convenience_method(self):
        """Test the log_event convenience method."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'
        request.session = MagicMock()
        request.session.session_key = 'test_session'
        request.path = '/test/'
        request.method = 'GET'
        
        event = SecurityEvent.log_event(
            event_type='login_success',
            request=request,
            user=self.user,
            severity='low',
            details={'test': 'data'}
        )
        
        self.assertEqual(event.event_type, 'login_success')
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.ip_address, '192.168.1.1')
        self.assertEqual(event.user_agent, 'Test Browser')
        self.assertEqual(event.session_key, 'test_session')
        self.assertEqual(event.request_path, '/test/')
        self.assertEqual(event.request_method, 'GET')
    
    def test_resolve_security_event(self):
        """Test resolving a security event."""
        event = SecurityEvent.objects.create(
            event_type='suspicious_activity',
            severity='medium',
            user=self.user,
            ip_address='192.168.1.1'
        )
        
        resolver = User.objects.create_user(
            username='resolver',
            email='resolver@example.com',
            password='resolverpass123'
        )
        
        event.resolve(resolver, 'False positive - legitimate activity')
        
        self.assertTrue(event.is_resolved)
        self.assertEqual(event.resolved_by, resolver)
        self.assertIsNotNone(event.resolved_at)
        self.assertEqual(event.resolution_notes, 'False positive - legitimate activity')
    
    def test_get_risk_score(self):
        """Test risk score calculation."""
        # High severity brute force attempt should have high risk score
        event = SecurityEvent.objects.create(
            event_type='brute_force_attempt',
            severity='critical',
            user=self.user,
            ip_address='192.168.1.1'
        )
        
        risk_score = event.get_risk_score()
        self.assertGreaterEqual(risk_score, 10)  # Should be high risk
        
        # Low severity login success should have low risk score
        event2 = SecurityEvent.objects.create(
            event_type='login_success',
            severity='low',
            user=self.user,
            ip_address='192.168.1.1'
        )
        
        risk_score2 = event2.get_risk_score()
        self.assertLessEqual(risk_score2, 2)  # Should be low risk


class AuditLogModelTest(TestCase):
    """Test AuditLog model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.factory = RequestFactory()
    
    def test_create_audit_log(self):
        """Test creating an audit log entry."""
        log = AuditLog.objects.create(
            user=self.user,
            action='create',
            model_name='test_model',
            object_id='123',
            changes={'field1': 'value1'},
            ip_address='192.168.1.1'
        )
        
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'create')
        self.assertEqual(log.model_name, 'test_model')
        self.assertEqual(log.object_id, '123')
        self.assertEqual(log.changes, {'field1': 'value1'})
        self.assertIsNotNone(log.checksum)  # Should generate checksum
    
    def test_log_action_convenience_method(self):
        """Test the log_action convenience method."""
        request = self.factory.post('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'
        request.session = MagicMock()
        request.session.session_key = 'test_session'
        request.path = '/test/'
        request.method = 'POST'
        
        log = AuditLog.log_action(
            action='create',
            user=self.user,
            request=request,
            changes={'field1': {'old': None, 'new': 'value1'}},
            details={'operation': 'test_create'}
        )
        
        self.assertEqual(log.action, 'create')
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.ip_address, '192.168.1.1')
        self.assertEqual(log.user_agent, 'Test Browser')
        self.assertEqual(log.changes, {'field1': {'old': None, 'new': 'value1'}})
        self.assertEqual(log.details, {'operation': 'test_create'})
    
    def test_integrity_verification(self):
        """Test audit log integrity verification."""
        log = AuditLog.objects.create(
            user=self.user,
            action='create',
            model_name='test_model',
            object_id='123',
            changes={'field1': 'value1'},
            ip_address='192.168.1.1'
        )
        
        # Should verify correctly initially
        self.assertTrue(log.verify_integrity())
        
        # Tamper with the data
        log.changes = {'field1': 'tampered_value'}
        
        # Should fail verification after tampering
        self.assertFalse(log.verify_integrity())


class RateLimitAttemptModelTest(TestCase):
    """Test RateLimitAttempt model functionality."""
    
    def test_record_attempt(self):
        """Test recording rate limit attempts."""
        attempt, is_blocked = RateLimitAttempt.record_attempt(
            identifier='192.168.1.1',
            limit_type='login',
            endpoint='/login/',
            user_agent='Test Browser'
        )
        
        self.assertEqual(attempt.identifier, '192.168.1.1')
        self.assertEqual(attempt.limit_type, 'login')
        self.assertEqual(attempt.attempts, 1)
        self.assertFalse(is_blocked)
    
    def test_rate_limit_blocking(self):
        """Test that rate limiting blocks after threshold."""
        identifier = '192.168.1.1'
        
        # Make multiple attempts
        for i in range(6):  # Login limit is 5
            attempt, is_blocked = RateLimitAttempt.record_attempt(
                identifier=identifier,
                limit_type='login',
                endpoint='/login/'
            )
        
        # Should be blocked after 5 attempts
        self.assertTrue(is_blocked)
        self.assertTrue(attempt.is_blocked)
        self.assertIsNotNone(attempt.blocked_until)
    
    def test_should_be_blocked(self):
        """Test should_be_blocked logic."""
        attempt = RateLimitAttempt.objects.create(
            identifier='192.168.1.1',
            limit_type='login',
            attempts=5
        )
        
        self.assertTrue(attempt.should_be_blocked())
        
        attempt.attempts = 3
        self.assertFalse(attempt.should_be_blocked())
    
    def test_is_currently_blocked(self):
        """Test current blocking status."""
        attempt = RateLimitAttempt.objects.create(
            identifier='192.168.1.1',
            limit_type='login',
            attempts=5,
            is_blocked=True,
            blocked_until=timezone.now() + timedelta(hours=1)
        )
        
        # Should be blocked (future blocked_until)
        self.assertTrue(attempt.is_currently_blocked())
        
        # Set blocked_until to past
        attempt.blocked_until = timezone.now() - timedelta(hours=1)
        attempt.save()
        
        # Should not be blocked anymore
        self.assertFalse(attempt.is_currently_blocked())
        self.assertFalse(attempt.is_blocked)  # Should auto-unblock


class SuspiciousActivityModelTest(TestCase):
    """Test SuspiciousActivity model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_detect_and_create(self):
        """Test detecting and creating suspicious activity."""
        activity = SuspiciousActivity.detect_and_create(
            activity_type='multiple_failed_logins',
            user=self.user,
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            pattern_data={'failed_attempts': 5},
            confidence_score=0.9
        )
        
        self.assertEqual(activity.activity_type, 'multiple_failed_logins')
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.ip_address, '192.168.1.1')
        self.assertEqual(activity.pattern_data, {'failed_attempts': 5})
        self.assertEqual(activity.confidence_score, 0.9)
        
        # Should also create a related security event
        security_event = SecurityEvent.objects.filter(
            event_type='suspicious_activity',
            user=self.user
        ).first()
        self.assertIsNotNone(security_event)
    
    def test_calculate_risk_level(self):
        """Test risk level calculation."""
        # High confidence privilege escalation should be critical
        risk_level = SuspiciousActivity._calculate_risk_level(
            'privilege_escalation', 0.9
        )
        self.assertEqual(risk_level, 'critical')
        
        # Low confidence time anomaly should be low
        risk_level = SuspiciousActivity._calculate_risk_level(
            'time_anomaly', 0.2
        )
        self.assertEqual(risk_level, 'low')
    
    def test_investigate(self):
        """Test investigating suspicious activity."""
        activity = SuspiciousActivity.objects.create(
            activity_type='unusual_access_pattern',
            user=self.user,
            ip_address='192.168.1.1',
            risk_level='medium'
        )
        
        investigator = User.objects.create_user(
            username='investigator',
            email='investigator@example.com',
            password='investigatorpass123'
        )
        
        activity.investigate(
            investigated_by=investigator,
            notes='Legitimate user behavior',
            is_false_positive=True
        )
        
        self.assertTrue(activity.is_investigated)
        self.assertEqual(activity.investigated_by, investigator)
        self.assertIsNotNone(activity.investigated_at)
        self.assertTrue(activity.is_false_positive)


class SecurityAuditMiddlewareTest(TestCase):
    """Test SecurityAuditMiddleware functionality."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = SecurityAuditMiddleware(lambda request: JsonResponse({'status': 'ok'}))
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_should_skip_logging(self):
        """Test that certain endpoints are skipped from logging."""
        request = self.factory.get('/static/css/style.css')
        self.assertTrue(self.middleware._should_skip_logging(request))
        
        request = self.factory.get('/health/')
        self.assertTrue(self.middleware._should_skip_logging(request))
        
        request = self.factory.get('/api/users/')
        self.assertFalse(self.middleware._should_skip_logging(request))
    
    def test_is_sensitive_endpoint(self):
        """Test sensitive endpoint detection."""
        request = self.factory.post('/login/')
        self.assertTrue(self.middleware._is_sensitive_endpoint(request))
        
        request = self.factory.get('/admin/')
        self.assertTrue(self.middleware._is_sensitive_endpoint(request))
        
        request = self.factory.get('/dashboard/')
        self.assertFalse(self.middleware._is_sensitive_endpoint(request))
    
    def test_middleware_processing(self):
        """Test middleware request processing."""
        request = self.factory.post('/api/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'
        request.user = self.user
        
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 200)
        
        # Should create audit log entry
        audit_logs = AuditLog.objects.filter(user=self.user)
        self.assertGreater(audit_logs.count(), 0)


class RateLimitMiddlewareTest(TestCase):
    """Test RateLimitMiddleware functionality."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = RateLimitMiddleware(lambda request: JsonResponse({'status': 'ok'}))
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_get_limit_type(self):
        """Test limit type detection."""
        request = self.factory.post('/login/')
        self.assertEqual(self.middleware._get_limit_type(request), 'login')
        
        request = self.factory.post('/api/users/')
        self.assertEqual(self.middleware._get_limit_type(request), 'api_general')
        
        request = self.factory.post('/api/admin/users/')
        self.assertEqual(self.middleware._get_limit_type(request), 'api_sensitive')
        
        request = self.factory.get('/dashboard/')
        self.assertIsNone(self.middleware._get_limit_type(request))
    
    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        # Make multiple requests to trigger rate limiting
        for i in range(6):  # Login limit is 5
            request = self.factory.post('/login/')
            request.META['REMOTE_ADDR'] = '192.168.1.1'
            request.META['HTTP_USER_AGENT'] = 'Test Browser'
            request.user = self.user
            
            response = self.middleware(request)
            
            if i < 5:
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 429)  # Too Many Requests
    
    def test_rate_limit_headers(self):
        """Test rate limit headers are added."""
        request = self.factory.post('/api/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = self.user
        
        response = self.middleware(request)
        
        self.assertIn('X-RateLimit-Limit', response)
        self.assertIn('X-RateLimit-Remaining', response)
        self.assertIn('X-RateLimit-Window', response)


class SuspiciousActivityDetectionMiddlewareTest(TestCase):
    """Test SuspiciousActivityDetectionMiddleware functionality."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = SuspiciousActivityDetectionMiddleware(
            lambda request: JsonResponse({'status': 'ok'})
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        cache.clear()  # Clear cache before each test
    
    def test_detect_suspicious_user_agent(self):
        """Test suspicious user agent detection."""
        user_agent = 'sqlmap/1.0'
        self.assertTrue(self.middleware._detect_suspicious_user_agent(user_agent))
        
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        self.assertFalse(self.middleware._detect_suspicious_user_agent(user_agent))
    
    def test_detect_suspicious_path(self):
        """Test suspicious path detection."""
        self.assertTrue(self.middleware._detect_suspicious_path('/admin/'))
        self.assertTrue(self.middleware._detect_suspicious_path('/wp-admin/'))
        self.assertTrue(self.middleware._detect_suspicious_path('/.env'))
        self.assertFalse(self.middleware._detect_suspicious_path('/dashboard/'))
    
    def test_detect_bulk_data_access(self):
        """Test bulk data access detection."""
        request = self.factory.get('/api/users/?page_size=500')
        self.assertTrue(self.middleware._detect_bulk_data_access(request))
        
        request = self.factory.get('/api/users/?page_size=20')
        self.assertFalse(self.middleware._detect_bulk_data_access(request))
        
        request = self.factory.get('/export/users/')
        self.assertTrue(self.middleware._detect_bulk_data_access(request))
    
    def test_middleware_creates_suspicious_activity(self):
        """Test that middleware creates suspicious activity records."""
        request = self.factory.get('/admin/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'sqlmap/1.0'
        request.user = self.user
        
        response = self.middleware(request)
        
        # Should create suspicious activity records
        suspicious_activities = SuspiciousActivity.objects.filter(
            ip_address='192.168.1.1'
        )
        self.assertGreater(suspicious_activities.count(), 0)


class SecurityMonitorTest(TestCase):
    """Test SecurityMonitor functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_check_account_security(self):
        """Test account security check."""
        # Create some security events
        SecurityEvent.objects.create(
            event_type='login_failed',
            user=self.user,
            ip_address='192.168.1.1',
            severity='medium'
        )
        
        SuspiciousActivity.objects.create(
            activity_type='multiple_failed_logins',
            user=self.user,
            ip_address='192.168.1.1',
            risk_level='medium'
        )
        
        security_check = SecurityMonitor.check_account_security(self.user)
        
        self.assertEqual(security_check['user_id'], self.user.id)
        self.assertIn('risk_score', security_check)
        self.assertIn('risk_level', security_check)
        self.assertIn('recommendations', security_check)
        self.assertGreater(security_check['failed_logins_7d'], 0)
        self.assertGreater(security_check['suspicious_activities_7d'], 0)
    
    def test_get_system_security_overview(self):
        """Test system security overview."""
        # Create some test data
        SecurityEvent.objects.create(
            event_type='login_failed',
            ip_address='192.168.1.1',
            severity='high'
        )
        
        SuspiciousActivity.objects.create(
            activity_type='brute_force_attempt',
            ip_address='192.168.1.1',
            risk_level='high'
        )
        
        overview = SecurityMonitor.get_system_security_overview()
        
        self.assertIn('security_events', overview)
        self.assertIn('suspicious_activities', overview)
        self.assertIn('rate_limiting', overview)
        self.assertIn('recommendations', overview)
        self.assertGreater(overview['security_events']['total'], 0)


class SecurityValidatorTest(TestCase):
    """Test SecurityValidator functionality."""
    
    def test_validate_password_strength(self):
        """Test password strength validation."""
        # Strong password
        result = SecurityValidator.validate_password_strength('StrongP@ssw0rd123')
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['strength'], 'strong')
        
        # Weak password
        result = SecurityValidator.validate_password_strength('weak')
        self.assertFalse(result['is_valid'])
        self.assertEqual(result['strength'], 'very_weak')
        self.assertGreater(len(result['issues']), 0)
        
        # Common password
        result = SecurityValidator.validate_password_strength('password123')
        self.assertFalse(result['is_valid'])
        self.assertIn('Password is too common', result['issues'])
    
    def test_generate_secure_token(self):
        """Test secure token generation."""
        token = SecurityValidator.generate_secure_token(32)
        self.assertEqual(len(token), 32)
        
        # Generate multiple tokens to ensure they're different
        token2 = SecurityValidator.generate_secure_token(32)
        self.assertNotEqual(token, token2)
    
    def test_generate_backup_codes(self):
        """Test backup code generation."""
        codes = SecurityValidator.generate_backup_codes(10, 8)
        self.assertEqual(len(codes), 10)
        
        for code in codes:
            self.assertEqual(len(code), 8)
            self.assertTrue(code.isupper())
            self.assertTrue(code.isalnum())
        
        # Ensure all codes are unique
        self.assertEqual(len(codes), len(set(codes)))


class AuditLoggerTest(TestCase):
    """Test AuditLogger functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.factory = RequestFactory()
    
    def test_log_model_change(self):
        """Test logging model changes."""
        # Create a test model instance (using User as example)
        test_user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        
        old_values = {'email': 'test2@example.com'}
        new_values = {'email': 'newemail@example.com'}
        
        AuditLogger.log_model_change(
            instance=test_user,
            action='update',
            user=self.user,
            old_values=old_values,
            new_values=new_values
        )
        
        # Check that audit log was created
        audit_log = AuditLog.objects.filter(
            action='update',
            user=self.user,
            model_name='user'
        ).first()
        
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.changes['email']['old'], 'test2@example.com')
        self.assertEqual(audit_log.changes['email']['new'], 'newemail@example.com')
    
    def test_log_business_operation(self):
        """Test logging business operations."""
        request = self.factory.post('/api/sales/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        AuditLogger.log_business_operation(
            operation_type='sale_create',
            user=self.user,
            request=request,
            details={
                'sale_amount': 1000,
                'customer_id': 123,
                'items': ['item1', 'item2']
            }
        )
        
        # Check that audit log was created
        audit_log = AuditLog.objects.filter(
            action='sale_create',
            user=self.user
        ).first()
        
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['sale_amount'], 1000)
        self.assertEqual(audit_log.ip_address, '192.168.1.1')
    
    def test_log_admin_action(self):
        """Test logging admin actions."""
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )
        
        target_user = User.objects.create_user(
            username='target',
            email='target@example.com',
            password='targetpass123'
        )
        
        request = self.factory.post('/admin/impersonate/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        AuditLogger.log_admin_action(
            admin_user=admin_user,
            action='user_impersonate',
            target_user=target_user,
            request=request,
            details={'reason': 'troubleshooting'}
        )
        
        # Check that audit log was created
        audit_log = AuditLog.objects.filter(
            action='user_impersonate',
            user=admin_user
        ).first()
        
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['target_user_id'], target_user.id)
        self.assertTrue(audit_log.details['is_admin_action'])
        
        # Check that security event was also created
        security_event = SecurityEvent.objects.filter(
            user=admin_user,
            event_type='admin_impersonation'
        ).first()
        
        self.assertIsNotNone(security_event)


class ThreatDetectorTest(TestCase):
    """Test ThreatDetector functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_analyze_login_pattern(self):
        """Test login pattern analysis."""
        # Create some historical login data
        SecurityEvent.objects.create(
            event_type='login_success',
            user=self.user,
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            created_at=timezone.now() - timedelta(days=1)
        )
        
        # Analyze new login from different IP
        analysis = ThreatDetector.analyze_login_pattern(
            user=self.user,
            ip_address='10.0.0.1',
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
        )
        
        self.assertIn('threats', analysis)
        self.assertIn('risk_score', analysis)
        self.assertIn('risk_level', analysis)
        self.assertIn('requires_additional_verification', analysis)
        
        # Should detect geographic and device anomalies
        threat_types = [threat['type'] for threat in analysis['threats']]
        self.assertIn('geographic_anomaly', threat_types)
        self.assertIn('device_anomaly', threat_types)
    
    def test_detect_geographic_anomaly(self):
        """Test geographic anomaly detection."""
        # Create historical login from one IP
        SecurityEvent.objects.create(
            event_type='login_success',
            user=self.user,
            ip_address='192.168.1.100',
            created_at=timezone.now() - timedelta(days=1)
        )
        
        # New IP should be detected as anomaly
        self.assertTrue(ThreatDetector._detect_geographic_anomaly(self.user, '10.0.0.1'))
        
        # Same IP should not be anomaly
        self.assertFalse(ThreatDetector._detect_geographic_anomaly(self.user, '192.168.1.100'))
    
    def test_detect_device_anomaly(self):
        """Test device anomaly detection."""
        # Create historical login with one user agent
        SecurityEvent.objects.create(
            event_type='login_success',
            user=self.user,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            ip_address='192.168.1.1',
            created_at=timezone.now() - timedelta(days=1)
        )
        
        # New user agent should be detected as anomaly
        self.assertTrue(ThreatDetector._detect_device_anomaly(
            self.user, 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
        ))
        
        # Same user agent should not be anomaly
        self.assertFalse(ThreatDetector._detect_device_anomaly(
            self.user, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        ))
    
    def test_detect_velocity_anomaly(self):
        """Test velocity anomaly detection."""
        # Create recent login from different IP
        SecurityEvent.objects.create(
            event_type='login_success',
            user=self.user,
            ip_address='192.168.1.100',
            created_at=timezone.now() - timedelta(minutes=30)
        )
        
        # Login from different IP within 1 hour should be velocity anomaly
        self.assertTrue(ThreatDetector._detect_velocity_anomaly(self.user, '10.0.0.1'))
        
        # Login from same IP should not be velocity anomaly
        self.assertFalse(ThreatDetector._detect_velocity_anomaly(self.user, '192.168.1.100'))


class SecuritySignalTest(TestCase):
    """Test security signal handlers."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.factory = RequestFactory()
    
    def test_user_logged_in_signal(self):
        """Test user_logged_in signal handler."""
        request = self.factory.post('/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'
        request.session = MagicMock()
        request.session.session_key = 'test_session'
        
        # Send signal
        user_logged_in.send(sender=User, request=request, user=self.user)
        
        # Check that security event was created
        security_event = SecurityEvent.objects.filter(
            event_type='login_success',
            user=self.user
        ).first()
        
        self.assertIsNotNone(security_event)
        self.assertEqual(security_event.ip_address, '192.168.1.1')
        
        # Check that audit log was created
        audit_log = AuditLog.objects.filter(
            action='login',
            user=self.user
        ).first()
        
        self.assertIsNotNone(audit_log)
    
    def test_user_login_failed_signal(self):
        """Test user_login_failed signal handler."""
        request = self.factory.post('/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'
        
        credentials = {'username': 'testuser'}
        
        # Send signal multiple times to trigger brute force detection
        for i in range(6):
            user_login_failed.send(
                sender=User, 
                credentials=credentials, 
                request=request
            )
        
        # Check that failed login events were created
        failed_events = SecurityEvent.objects.filter(
            event_type='login_failed',
            username_attempted='testuser'
        )
        self.assertEqual(failed_events.count(), 6)
        
        # Check that brute force event was created
        brute_force_event = SecurityEvent.objects.filter(
            event_type='brute_force_attempt',
            username_attempted='testuser'
        ).first()
        
        self.assertIsNotNone(brute_force_event)
        self.assertEqual(brute_force_event.severity, 'high')
        
        # Check that suspicious activity was created
        suspicious_activity = SuspiciousActivity.objects.filter(
            activity_type='multiple_failed_logins',
            ip_address='192.168.1.1'
        ).first()
        
        self.assertIsNotNone(suspicious_activity)


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
})
class SecurityIntegrationTest(TestCase):
    """Integration tests for security system."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.factory = RequestFactory()
        cache.clear()
    
    def test_complete_security_workflow(self):
        """Test complete security workflow from detection to resolution."""
        # 1. Create suspicious activity through middleware
        middleware = SuspiciousActivityDetectionMiddleware(
            lambda request: JsonResponse({'status': 'ok'})
        )
        
        request = self.factory.get('/admin/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'sqlmap/1.0'
        request.user = self.user
        
        response = middleware(request)
        
        # 2. Verify suspicious activity was created
        suspicious_activity = SuspiciousActivity.objects.filter(
            ip_address='192.168.1.1'
        ).first()
        
        self.assertIsNotNone(suspicious_activity)
        
        # 3. Check security monitoring
        security_check = SecurityMonitor.check_account_security(self.user)
        self.assertGreater(security_check['risk_score'], 0)
        
        # 4. Investigate and resolve
        investigator = User.objects.create_user(
            username='investigator',
            email='investigator@example.com',
            password='investigatorpass123'
        )
        
        suspicious_activity.investigate(
            investigated_by=investigator,
            notes='False positive - security testing',
            is_false_positive=True
        )
        
        # 5. Verify resolution
        suspicious_activity.refresh_from_db()
        self.assertTrue(suspicious_activity.is_investigated)
        self.assertTrue(suspicious_activity.is_false_positive)
    
    def test_rate_limiting_integration(self):
        """Test rate limiting integration with security events."""
        middleware = RateLimitMiddleware(
            lambda request: JsonResponse({'status': 'ok'})
        )
        
        # Make multiple requests to trigger rate limiting
        for i in range(6):
            request = self.factory.post('/login/')
            request.META['REMOTE_ADDR'] = '192.168.1.1'
            request.META['HTTP_USER_AGENT'] = 'Test Browser'
            request.user = self.user
            
            response = middleware(request)
            
            if i >= 5:  # Should be rate limited
                self.assertEqual(response.status_code, 429)
        
        # Verify rate limit attempt was recorded
        rate_limit_attempt = RateLimitAttempt.objects.filter(
            identifier='ip:192.168.1.1',
            limit_type='login'
        ).first()
        
        self.assertIsNotNone(rate_limit_attempt)
        self.assertTrue(rate_limit_attempt.is_blocked)
        
        # Verify security event was created
        security_event = SecurityEvent.objects.filter(
            event_type='api_rate_limit',
            ip_address='192.168.1.1'
        ).first()
        
        self.assertIsNotNone(security_event)