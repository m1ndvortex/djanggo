"""
Unit tests for security policy backend implementation.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing Django modules
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from datetime import datetime, timedelta
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.cache import cache
from unittest.mock import patch, MagicMock

from zargar.admin_panel.models import SecurityPolicy
from zargar.admin_panel.security_services import (
    PasswordPolicyService,
    SessionPolicyService,
    RateLimitPolicyService,
    AuthenticationPolicyService,
    SecurityPolicyEnforcer
)
from zargar.admin_panel.middleware import (
    SecurityPolicyMiddleware,
    PasswordPolicyMiddleware,
    SessionSecurityMiddleware
)

User = get_user_model()


class SecurityPolicyModelTest(TestCase):
    """Test SecurityPolicy model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.password_policy_data = {
            'name': 'Default Password Policy',
            'policy_type': 'password',
            'is_active': True,
            'configuration': {
                'min_length': 8,
                'require_uppercase': True,
                'require_lowercase': True,
                'require_numbers': True,
                'require_special_chars': True,
                'max_age_days': 90,
                'prevent_reuse_count': 5,
                'special_chars': '!@#$%^&*()_+-=[]{}|;:,.<>?',
            },
            'description': 'Default password policy for all users',
            'created_by_username': 'admin',
        }
    
    def test_create_password_policy(self):
        """Test creating a password policy."""
        policy = SecurityPolicy.objects.create(**self.password_policy_data)
        
        self.assertEqual(policy.name, 'Default Password Policy')
        self.assertEqual(policy.policy_type, 'password')
        self.assertTrue(policy.is_active)
        self.assertEqual(policy.configuration['min_length'], 8)
        self.assertIsNotNone(policy.created_at)
    
    def test_password_policy_validation(self):
        """Test password policy configuration validation."""
        # Test valid configuration
        policy = SecurityPolicy(**self.password_policy_data)
        policy.clean()  # Should not raise
        
        # Test missing required field
        invalid_config = self.password_policy_data.copy()
        invalid_config['configuration'] = {'min_length': 8}  # Missing required fields
        
        policy = SecurityPolicy(**invalid_config)
        with self.assertRaises(ValidationError):
            policy.clean()
    
    def test_session_policy_validation(self):
        """Test session policy configuration validation."""
        session_policy_data = {
            'name': 'Default Session Policy',
            'policy_type': 'session',
            'is_active': True,
            'configuration': {
                'timeout_minutes': 480,
                'max_concurrent_sessions': 3,
                'require_reauth_for_sensitive': True,
                'extend_on_activity': True,
                'secure_cookies': True,
            },
        }
        
        policy = SecurityPolicy(**session_policy_data)
        policy.clean()  # Should not raise
        
        # Test invalid timeout
        invalid_config = session_policy_data.copy()
        invalid_config['configuration']['timeout_minutes'] = -1
        
        policy = SecurityPolicy(**invalid_config)
        with self.assertRaises(ValidationError):
            policy.clean()
    
    def test_rate_limit_policy_validation(self):
        """Test rate limit policy configuration validation."""
        rate_limit_policy_data = {
            'name': 'Default Rate Limit Policy',
            'policy_type': 'rate_limit',
            'is_active': True,
            'configuration': {
                'limits': {
                    'login': {'requests': 5, 'window_minutes': 60},
                    'api_call': {'requests': 1000, 'window_minutes': 60},
                }
            },
        }
        
        policy = SecurityPolicy(**rate_limit_policy_data)
        policy.clean()  # Should not raise
        
        # Test invalid limits structure
        invalid_config = rate_limit_policy_data.copy()
        invalid_config['configuration']['limits'] = 'invalid'
        
        policy = SecurityPolicy(**invalid_config)
        with self.assertRaises(ValidationError):
            policy.clean()
    
    def test_get_active_policy(self):
        """Test getting active policy by type."""
        # Create multiple policies, only one active
        SecurityPolicy.objects.create(
            name='Inactive Policy',
            policy_type='password',
            is_active=False,
            configuration={}
        )
        
        active_policy = SecurityPolicy.objects.create(**self.password_policy_data)
        
        retrieved_policy = SecurityPolicy.get_active_policy('password')
        self.assertEqual(retrieved_policy.id, active_policy.id)
        
        # Test non-existent policy type
        no_policy = SecurityPolicy.get_active_policy('nonexistent')
        self.assertIsNone(no_policy)
    
    def test_get_default_policies(self):
        """Test getting default policy configurations."""
        # Test password policy defaults
        password_config = SecurityPolicy.get_password_policy()
        self.assertIn('min_length', password_config)
        self.assertEqual(password_config['min_length'], 8)
        
        # Test session policy defaults
        session_config = SecurityPolicy.get_session_policy()
        self.assertIn('timeout_minutes', session_config)
        self.assertEqual(session_config['timeout_minutes'], 480)
        
        # Test rate limit policy defaults
        rate_limit_config = SecurityPolicy.get_rate_limit_policy()
        self.assertIn('limits', rate_limit_config)
        self.assertIn('login', rate_limit_config['limits'])


class PasswordPolicyServiceTest(TestCase):
    """Test PasswordPolicyService functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpassword123'
        )
        
        # Create a password policy
        SecurityPolicy.objects.create(
            name='Test Password Policy',
            policy_type='password',
            is_active=True,
            configuration={
                'min_length': 10,
                'require_uppercase': True,
                'require_lowercase': True,
                'require_numbers': True,
                'require_special_chars': True,
                'max_age_days': 90,
                'prevent_reuse_count': 3,
                'special_chars': '!@#$%^&*()_+-=[]{}|;:,.<>?',
            }
        )
    
    def test_validate_strong_password(self):
        """Test validation of a strong password."""
        strong_password = 'StrongPass123!'
        is_valid, errors = PasswordPolicyService.validate_password(strong_password, self.user)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_weak_passwords(self):
        """Test validation of weak passwords."""
        weak_passwords = [
            ('short', 'Too short'),
            ('nouppercase123!', 'No uppercase'),
            ('NOLOWERCASE123!', 'No lowercase'),
            ('NoNumbers!', 'No numbers'),
            ('NoSpecialChars123', 'No special characters'),
        ]
        
        for password, description in weak_passwords:
            is_valid, errors = PasswordPolicyService.validate_password(password, self.user)
            self.assertFalse(is_valid, f'Password should be invalid: {description}')
            self.assertGreater(len(errors), 0, f'Should have errors for: {description}')
    
    def test_password_strength_score(self):
        """Test password strength scoring."""
        test_cases = [
            ('weak', 0, 30),  # Very weak password
            ('StrongPass123!', 70, 100),  # Strong password
            ('VeryLongAndComplexPassword123!@#', 80, 100),  # Very strong password
        ]
        
        for password, min_score, max_score in test_cases:
            score = PasswordPolicyService.get_password_strength_score(password)
            self.assertGreaterEqual(score, min_score)
            self.assertLessEqual(score, max_score)
    
    @patch('zargar.admin_panel.security_services.PasswordPolicyService._is_password_reused')
    def test_password_reuse_check(self, mock_reuse_check):
        """Test password reuse checking."""
        mock_reuse_check.return_value = True
        
        password = 'ReusedPassword123!'
        is_valid, errors = PasswordPolicyService.validate_password(password, self.user)
        
        self.assertFalse(is_valid)
        self.assertTrue(any('cannot be one of your last' in error for error in errors))
    
    def test_password_expiry_check(self):
        """Test password expiry checking."""
        # Mock user with old password
        old_date = timezone.now() - timedelta(days=100)
        self.user.password_changed_at = old_date
        
        is_expired = PasswordPolicyService.is_password_expired(self.user)
        self.assertTrue(is_expired)
        
        # Test with recent password change
        recent_date = timezone.now() - timedelta(days=30)
        self.user.password_changed_at = recent_date
        
        is_expired = PasswordPolicyService.is_password_expired(self.user)
        self.assertFalse(is_expired)


class SessionPolicyServiceTest(TestCase):
    """Test SessionPolicyService functionality."""
    
    def setUp(self):
        """Set up test data."""
        SecurityPolicy.objects.create(
            name='Test Session Policy',
            policy_type='session',
            is_active=True,
            configuration={
                'timeout_minutes': 120,
                'max_concurrent_sessions': 2,
                'require_reauth_for_sensitive': True,
                'extend_on_activity': True,
                'secure_cookies': True,
            }
        )
    
    def test_get_session_timeout(self):
        """Test getting session timeout."""
        timeout = SessionPolicyService.get_session_timeout()
        self.assertEqual(timeout, 120 * 60)  # Should be in seconds
    
    def test_get_max_concurrent_sessions(self):
        """Test getting max concurrent sessions."""
        max_sessions = SessionPolicyService.get_max_concurrent_sessions()
        self.assertEqual(max_sessions, 2)
    
    def test_should_require_reauth(self):
        """Test sensitive action re-authentication requirement."""
        # Test sensitive actions
        sensitive_actions = [
            'password_change',
            'user_delete',
            'security_settings_change',
            'backup_restore',
        ]
        
        for action in sensitive_actions:
            self.assertTrue(SessionPolicyService.should_require_reauth(action))
        
        # Test non-sensitive action
        self.assertFalse(SessionPolicyService.should_require_reauth('view_dashboard'))
    
    def test_extend_session_on_activity(self):
        """Test session extension on activity."""
        should_extend = SessionPolicyService.extend_session_on_activity()
        self.assertTrue(should_extend)
    
    def test_use_secure_cookies(self):
        """Test secure cookies setting."""
        use_secure = SessionPolicyService.use_secure_cookies()
        self.assertTrue(use_secure)


class RateLimitPolicyServiceTest(TestCase):
    """Test RateLimitPolicyService functionality."""
    
    def setUp(self):
        """Set up test data."""
        SecurityPolicy.objects.create(
            name='Test Rate Limit Policy',
            policy_type='rate_limit',
            is_active=True,
            configuration={
                'limits': {
                    'login': {'requests': 3, 'window_minutes': 60},
                    'api_call': {'requests': 100, 'window_minutes': 60},
                }
            }
        )
        
        # Clear cache before each test
        cache.clear()
    
    def test_get_rate_limit(self):
        """Test getting rate limit configuration."""
        login_limit = RateLimitPolicyService.get_rate_limit('login')
        self.assertEqual(login_limit['requests'], 3)
        self.assertEqual(login_limit['window_minutes'], 60)
        
        # Test non-existent limit type (should return default)
        default_limit = RateLimitPolicyService.get_rate_limit('nonexistent')
        self.assertEqual(default_limit['requests'], 100)
        self.assertEqual(default_limit['window_minutes'], 60)
    
    def test_rate_limiting_flow(self):
        """Test complete rate limiting flow."""
        identifier = '192.168.1.1'
        limit_type = 'login'
        
        # First request - should not be limited
        is_limited, remaining, reset_time = RateLimitPolicyService.is_rate_limited(
            identifier, limit_type
        )
        self.assertFalse(is_limited)
        self.assertEqual(remaining, 3)
        
        # Record requests up to limit
        for i in range(3):
            is_now_limited, remaining, reset_time = RateLimitPolicyService.record_request(
                identifier, limit_type
            )
            
            if i < 2:  # First two requests
                self.assertFalse(is_now_limited)
                self.assertEqual(remaining, 2 - i)
            else:  # Third request hits limit
                self.assertTrue(is_now_limited)
                self.assertEqual(remaining, 0)
        
        # Fourth request should be limited
        is_limited, remaining, reset_time = RateLimitPolicyService.is_rate_limited(
            identifier, limit_type
        )
        self.assertTrue(is_limited)
        self.assertEqual(remaining, 0)
    
    def test_rate_limit_window_reset(self):
        """Test rate limit window reset."""
        identifier = '192.168.1.2'
        limit_type = 'login'
        
        # Hit the rate limit
        for i in range(3):
            RateLimitPolicyService.record_request(identifier, limit_type)
        
        # Should be limited
        is_limited, _, _ = RateLimitPolicyService.is_rate_limited(identifier, limit_type)
        self.assertTrue(is_limited)
        
        # Mock time passage (simulate window reset)
        with patch('django.utils.timezone.now') as mock_now:
            future_time = timezone.now() + timedelta(hours=2)
            mock_now.return_value = future_time
            
            # Should not be limited after window reset
            is_limited, remaining, _ = RateLimitPolicyService.is_rate_limited(
                identifier, limit_type
            )
            self.assertFalse(is_limited)
            self.assertEqual(remaining, 3)


class AuthenticationPolicyServiceTest(TestCase):
    """Test AuthenticationPolicyService functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        SecurityPolicy.objects.create(
            name='Test Auth Policy',
            policy_type='authentication',
            is_active=True,
            configuration={
                'require_2fa': True,
                'lockout_attempts': 3,
                'lockout_duration_minutes': 15,
                'password_reset_token_expiry_hours': 12,
                'remember_me_duration_days': 14,
            }
        )
    
    def test_requires_2fa(self):
        """Test 2FA requirement check."""
        requires_2fa = AuthenticationPolicyService.requires_2fa(self.user)
        self.assertTrue(requires_2fa)
    
    def test_get_lockout_config(self):
        """Test getting lockout configuration."""
        lockout_config = AuthenticationPolicyService.get_lockout_config()
        self.assertEqual(lockout_config['attempts'], 3)
        self.assertEqual(lockout_config['duration_minutes'], 15)
    
    def test_get_password_reset_token_expiry(self):
        """Test getting password reset token expiry."""
        expiry = AuthenticationPolicyService.get_password_reset_token_expiry()
        self.assertEqual(expiry, 12)
    
    def test_get_remember_me_duration(self):
        """Test getting remember me duration."""
        duration = AuthenticationPolicyService.get_remember_me_duration()
        self.assertEqual(duration, 14)


class SecurityPolicyEnforcerTest(TestCase):
    """Test SecurityPolicyEnforcer integration."""
    
    def setUp(self):
        """Set up test data."""
        self.enforcer = SecurityPolicyEnforcer()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_validate_password_integration(self):
        """Test password validation through enforcer."""
        is_valid, errors = self.enforcer.validate_password('StrongPass123!', self.user)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_rate_limit_integration(self):
        """Test rate limiting through enforcer."""
        identifier = '192.168.1.3'
        limit_type = 'api_call'
        
        is_limited, _, _ = self.enforcer.check_rate_limit(identifier, limit_type)
        self.assertFalse(is_limited)
        
        # Record a request
        is_now_limited, _, _ = self.enforcer.record_request(identifier, limit_type)
        self.assertFalse(is_now_limited)
    
    def test_session_timeout_integration(self):
        """Test session timeout through enforcer."""
        timeout = self.enforcer.get_session_timeout()
        self.assertIsInstance(timeout, int)
        self.assertGreater(timeout, 0)
    
    def test_2fa_requirement_integration(self):
        """Test 2FA requirement through enforcer."""
        requires_2fa = self.enforcer.requires_2fa(self.user)
        self.assertIsInstance(requires_2fa, bool)
    
    def test_reauth_requirement_integration(self):
        """Test re-authentication requirement through enforcer."""
        requires_reauth = self.enforcer.should_require_reauth('password_change')
        self.assertTrue(requires_reauth)
        
        requires_reauth = self.enforcer.should_require_reauth('view_dashboard')
        self.assertFalse(requires_reauth)


class SecurityPolicyMiddlewareTest(TestCase):
    """Test SecurityPolicyMiddleware functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.middleware = SecurityPolicyMiddleware(lambda r: None)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Clear cache
        cache.clear()
    
    def test_skip_security_check(self):
        """Test skipping security checks for certain paths."""
        skip_paths = ['/admin/login/', '/static/css/style.css', '/health/']
        
        for path in skip_paths:
            request = self.factory.get(path)
            self.assertTrue(self.middleware._should_skip_security_check(request))
        
        # Test path that should not be skipped
        request = self.factory.get('/admin/dashboard/')
        self.assertFalse(self.middleware._should_skip_security_check(request))
    
    def test_get_rate_limit_type(self):
        """Test determining rate limit type from request."""
        test_cases = [
            ('/admin/login/', 'login'),
            ('/admin/password_reset/', 'password_reset'),
            ('/api/users/', 'api_call'),
            ('/admin/export/data/', 'data_export'),
            ('/admin/bulk/update/', 'bulk_operation'),
            ('/admin/search/', 'search'),
            ('/admin/report/generate/', 'report_generation'),
        ]
        
        for path, expected_type in test_cases:
            request = self.factory.get(path)
            limit_type = self.middleware._get_rate_limit_type(request)
            self.assertEqual(limit_type, expected_type)
    
    def test_get_client_ip(self):
        """Test extracting client IP from request."""
        # Test with X-Forwarded-For header
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '192.168.1.1, 10.0.0.1'
        ip = self.middleware._get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')
        
        # Test with REMOTE_ADDR
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.2'
        ip = self.middleware._get_client_ip(request)
        self.assertEqual(ip, '192.168.1.2')
    
    def test_is_sensitive_action(self):
        """Test identifying sensitive actions."""
        sensitive_paths = [
            '/admin/auth/user/1/password/',
            '/admin/auth/user/1/delete/',
            '/admin/security/settings/',
            '/admin/backup/restore/123/',
        ]
        
        for path in sensitive_paths:
            request = self.factory.get(path)
            self.assertTrue(self.middleware._is_sensitive_action(request))
        
        # Test non-sensitive path
        request = self.factory.get('/admin/dashboard/')
        self.assertFalse(self.middleware._is_sensitive_action(request))


class PasswordPolicyMiddlewareTest(TestCase):
    """Test PasswordPolicyMiddleware functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.middleware = PasswordPolicyMiddleware(lambda r: None)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    @patch('zargar.admin_panel.security_services.PasswordPolicyService.is_password_expired')
    def test_password_expiry_redirect(self, mock_is_expired):
        """Test redirect when password is expired."""
        mock_is_expired.return_value = True
        
        request = self.factory.get('/admin/dashboard/')
        request.user = self.user
        
        response = self.middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)  # Redirect


class SessionSecurityMiddlewareTest(TestCase):
    """Test SessionSecurityMiddleware functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.middleware = SessionSecurityMiddleware(lambda r: None)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_session_ip_consistency(self):
        """Test session IP consistency checking."""
        request = self.factory.get('/admin/dashboard/')
        request.user = self.user
        request.session = {}
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # First request - should store IP
        response = self.middleware.process_request(request)
        self.assertIsNone(response)
        self.assertEqual(request.session['client_ip'], '192.168.1.1')
        
        # Second request with different IP - should trigger security alert
        request.META['REMOTE_ADDR'] = '192.168.1.2'
        request.session['client_ip'] = '192.168.1.1'
        
        response = self.middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_user_agent_consistency(self):
        """Test user agent consistency checking."""
        request = self.factory.get('/admin/dashboard/')
        request.user = self.user
        request.session = {}
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 (Test Browser)'
        
        # First request - should store user agent
        response = self.middleware.process_request(request)
        self.assertIsNone(response)
        self.assertEqual(request.session['user_agent'], 'Mozilla/5.0 (Test Browser)')
        
        # Second request with different user agent - should log but not block
        request.META['HTTP_USER_AGENT'] = 'Different Browser'
        request.session['user_agent'] = 'Mozilla/5.0 (Test Browser)'
        
        response = self.middleware.process_request(request)
        self.assertIsNone(response)  # Should not block, just log


if __name__ == '__main__':
    pytest.main([__file__])