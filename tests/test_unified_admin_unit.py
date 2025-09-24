"""
Unit tests for unified admin system components.
Tests individual functions, classes, and methods in isolation.
"""
import os
import django
from django.conf import settings

# Configure Django settings
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils import timezone
from unittest.mock import Mock, patch, MagicMock
from datetime import timedelta, datetime
import json

from zargar.tenants.admin_models import SuperAdmin, TenantAccessLog, SuperAdminSession
from zargar.tenants.models import Tenant
from zargar.admin_panel.unified_auth_backend import (
    UnifiedSuperAdminAuthBackend,
    UnifiedSessionManager,
    UnifiedAuthPermissions
)
from zargar.admin_panel.unified_auth_middleware import (
    UnifiedAdminAuthMiddleware,
    UnifiedAdminSecurityMiddleware
)


class UnifiedSuperAdminAuthBackendUnitTests(TestCase):
    """
    Unit tests for UnifiedSuperAdminAuthBackend class.
    """
    
    def setUp(self):
        """Set up test data."""
        self.backend = UnifiedSuperAdminAuthBackend()
        self.factory = RequestFactory()
        
        # Create test SuperAdmin
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_active=True
        )
        
        # Create inactive SuperAdmin
        self.inactive_admin = SuperAdmin.objects.create_user(
            username='inactiveadmin',
            email='inactive@test.com',
            password='testpass123',
            is_superuser=True,
            is_active=False
        )
    
    def test_authenticate_valid_credentials(self):
        """Test authenticate method with valid credentials."""
        request = self.factory.post('/admin/login/')
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        
        user = self.backend.authenticate(
            request=request,
            username='testadmin',
            password='testpass123'
        )
        
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'testadmin')
        self.assertIsInstance(user, SuperAdmin)
    
    def test_authenticate_invalid_username(self):
        """Test authenticate method with invalid username."""
        request = self.factory.post('/admin/login/')
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        
        user = self.backend.authenticate(
            request=request,
            username='nonexistent',
            password='testpass123'
        )
        
        self.assertIsNone(user)
    
    def test_authenticate_invalid_password(self):
        """Test authenticate method with invalid password."""
        request = self.factory.post('/admin/login/')
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        
        user = self.backend.authenticate(
            request=request,
            username='testadmin',
            password='wrongpassword'
        )
        
        self.assertIsNone(user)
    
    def test_authenticate_inactive_user(self):
        """Test authenticate method with inactive user."""
        request = self.factory.post('/admin/login/')
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        
        user = self.backend.authenticate(
            request=request,
            username='inactiveadmin',
            password='testpass123'
        )
        
        self.assertIsNone(user)
    
    def test_authenticate_missing_credentials(self):
        """Test authenticate method with missing credentials."""
        request = self.factory.post('/admin/login/')
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        
        # Missing username
        user = self.backend.authenticate(
            request=request,
            username=None,
            password='testpass123'
        )
        self.assertIsNone(user)
        
        # Missing password
        user = self.backend.authenticate(
            request=request,
            username='testadmin',
            password=None
        )
        self.assertIsNone(user)
    
    def test_authenticate_2fa_enabled_no_token(self):
        """Test authenticate with 2FA enabled but no token provided."""
        self.superadmin.is_2fa_enabled = True
        self.superadmin.save()
        
        request = self.factory.post('/admin/login/')
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        
        user = self.backend.authenticate(
            request=request,
            username='testadmin',
            password='testpass123'
        )
        
        self.assertIsNone(user)  # Should return None to prompt for 2FA
    
    @patch('zargar.admin_panel.unified_auth_backend.match_token')
    def test_authenticate_2fa_valid_token(self, mock_match_token):
        """Test authenticate with valid 2FA token."""
        self.superadmin.is_2fa_enabled = True
        self.superadmin.save()
        
        # Mock successful 2FA verification
        mock_device = Mock()
        mock_match_token.return_value = mock_device
        
        request = self.factory.post('/admin/login/')
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        
        user = self.backend.authenticate(
            request=request,
            username='testadmin',
            password='testpass123',
            otp_token='123456'
        )
        
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'testadmin')
        mock_match_token.assert_called_once_with(self.superadmin, '123456')
    
    @patch('zargar.admin_panel.unified_auth_backend.match_token')
    def test_authenticate_2fa_invalid_token(self, mock_match_token):
        """Test authenticate with invalid 2FA token."""
        self.superadmin.is_2fa_enabled = True
        self.superadmin.save()
        
        # Mock failed 2FA verification
        mock_match_token.return_value = None
        
        request = self.factory.post('/admin/login/')
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        
        user = self.backend.authenticate(
            request=request,
            username='testadmin',
            password='testpass123',
            otp_token='invalid'
        )
        
        self.assertIsNone(user)
        mock_match_token.assert_called_once_with(self.superadmin, 'invalid')
    
    def test_get_user_valid_id(self):
        """Test get_user method with valid user ID."""
        user = self.backend.get_user(self.superadmin.id)
        self.assertEqual(user, self.superadmin)
    
    def test_get_user_invalid_id(self):
        """Test get_user method with invalid user ID."""
        user = self.backend.get_user(99999)
        self.assertIsNone(user)
    
    def test_user_can_authenticate_valid_superadmin(self):
        """Test user_can_authenticate with valid SuperAdmin."""
        result = self.backend.user_can_authenticate(self.superadmin)
        self.assertTrue(result)
    
    def test_user_can_authenticate_inactive_superadmin(self):
        """Test user_can_authenticate with inactive SuperAdmin."""
        result = self.backend.user_can_authenticate(self.inactive_admin)
        self.assertFalse(result)
    
    def test_user_can_authenticate_non_superadmin(self):
        """Test user_can_authenticate with non-SuperAdmin user."""
        regular_user = Mock()
        regular_user.is_active = True
        regular_user.is_superuser = False
        
        result = self.backend.user_can_authenticate(regular_user)
        self.assertFalse(result)
    
    def test_verify_2fa_token_success(self):
        """Test _verify_2fa_token method with successful verification."""
        with patch('zargar.admin_panel.unified_auth_backend.match_token') as mock_match:
            mock_device = Mock()
            mock_match.return_value = mock_device
            
            result = self.backend._verify_2fa_token(self.superadmin, '123456')
            self.assertTrue(result)
            mock_match.assert_called_once_with(self.superadmin, '123456')
    
    def test_verify_2fa_token_failure(self):
        """Test _verify_2fa_token method with failed verification."""
        with patch('zargar.admin_panel.unified_auth_backend.match_token') as mock_match:
            mock_match.return_value = None
            
            result = self.backend._verify_2fa_token(self.superadmin, 'invalid')
            self.assertFalse(result)
            mock_match.assert_called_once_with(self.superadmin, 'invalid')
    
    def test_verify_2fa_token_exception(self):
        """Test _verify_2fa_token method with exception."""
        with patch('zargar.admin_panel.unified_auth_backend.match_token') as mock_match:
            mock_match.side_effect = Exception('Test exception')
            
            result = self.backend._verify_2fa_token(self.superadmin, '123456')
            self.assertFalse(result)
    
    def test_get_client_ip_with_forwarded_header(self):
        """Test _get_client_ip method with X-Forwarded-For header."""
        request = self.factory.post('/admin/login/')
        request.META = {'HTTP_X_FORWARDED_FOR': '192.168.1.1, 10.0.0.1'}
        
        ip = self.backend._get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')
    
    def test_get_client_ip_without_forwarded_header(self):
        """Test _get_client_ip method without X-Forwarded-For header."""
        request = self.factory.post('/admin/login/')
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        ip = self.backend._get_client_ip(request)
        self.assertEqual(ip, '127.0.0.1')
    
    def test_get_client_ip_no_ip_info(self):
        """Test _get_client_ip method with no IP information."""
        request = self.factory.post('/admin/login/')
        request.META = {}
        
        ip = self.backend._get_client_ip(request)
        self.assertEqual(ip, '')


class UnifiedSessionManagerUnitTests(TestCase):
    """
    Unit tests for UnifiedSessionManager class.
    """
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        
        # Create test SuperAdmin
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_active=True
        )
    
    def test_create_admin_session_success(self):
        """Test create_admin_session method with successful creation."""
        request = self.factory.post('/admin/login/')
        request.session = {}
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        
        session = UnifiedSessionManager.create_admin_session(request, self.superadmin)
        
        self.assertIsNotNone(session)
        self.assertEqual(session.super_admin, self.superadmin)
        self.assertEqual(session.tenant_schema, 'public')
        self.assertTrue(session.is_active)
        
        # Check session data
        self.assertIn('admin_session_id', request.session)
        self.assertIn('admin_user_id', request.session)
        self.assertIn('admin_username', request.session)
        self.assertEqual(request.session['admin_user_id'], self.superadmin.id)
        self.assertEqual(request.session['admin_username'], 'testadmin')
    
    def test_create_admin_session_exception(self):
        """Test create_admin_session method with exception."""
        request = self.factory.post('/admin/login/')
        request.session = {}
        request.META = {}
        
        with patch('zargar.tenants.admin_models.SuperAdminSession.objects.create') as mock_create:
            mock_create.side_effect = Exception('Test exception')
            
            session = UnifiedSessionManager.create_admin_session(request, self.superadmin)
            self.assertIsNone(session)
    
    def test_track_tenant_access_success(self):
        """Test track_tenant_access method with successful tracking."""
        request = self.factory.get('/admin/tenants/')
        request.session = {}
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        
        UnifiedSessionManager.track_tenant_access(request, self.superadmin, 'tenant1')
        
        # Check session updated
        self.assertEqual(request.session.get('current_tenant_schema'), 'tenant1')
        self.assertIn('last_tenant_access', request.session)
        
        # Check audit log created
        log_exists = TenantAccessLog.objects.filter(
            username=self.superadmin.username,
            action='tenant_switch',
            tenant_schema='tenant1'
        ).exists()
        self.assertTrue(log_exists)
    
    def test_track_tenant_access_exception(self):
        """Test track_tenant_access method with exception."""
        request = self.factory.get('/admin/tenants/')
        request.session = {}
        request.META = {}
        
        with patch('zargar.tenants.admin_models.TenantAccessLog.log_action') as mock_log:
            mock_log.side_effect = Exception('Test exception')
            
            # Should not raise exception
            UnifiedSessionManager.track_tenant_access(request, self.superadmin, 'tenant1')
    
    def test_end_admin_session_success(self):
        """Test end_admin_session method with successful termination."""
        # First create a session
        request = self.factory.post('/admin/login/')
        request.session = {}
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        
        session = UnifiedSessionManager.create_admin_session(request, self.superadmin)
        
        # Now end the session
        request.path = '/admin/logout/'
        request.method = 'POST'
        UnifiedSessionManager.end_admin_session(request, self.superadmin)
        
        # Check session marked inactive
        session.refresh_from_db()
        self.assertFalse(session.is_active)
        
        # Check audit log created
        log_exists = TenantAccessLog.objects.filter(
            username=self.superadmin.username,
            action='logout'
        ).exists()
        self.assertTrue(log_exists)
        
        # Check session data cleared
        admin_keys = [key for key in request.session.keys() if key.startswith('admin_')]
        self.assertEqual(len(admin_keys), 0)
    
    def test_end_admin_session_no_session(self):
        """Test end_admin_session method with no existing session."""
        request = self.factory.post('/admin/logout/')
        request.session = {}
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        
        # Should not raise exception
        UnifiedSessionManager.end_admin_session(request, self.superadmin)
    
    def test_calculate_session_duration_valid(self):
        """Test _calculate_session_duration method with valid start time."""
        request = Mock()
        request.session = {
            'session_start_time': timezone.now().isoformat()
        }
        
        duration = UnifiedSessionManager._calculate_session_duration(request)
        self.assertIsInstance(duration, int)
        self.assertGreaterEqual(duration, 0)
    
    def test_calculate_session_duration_invalid(self):
        """Test _calculate_session_duration method with invalid start time."""
        request = Mock()
        request.session = {}
        
        duration = UnifiedSessionManager._calculate_session_duration(request)
        self.assertEqual(duration, 0)
    
    def test_get_client_ip_methods(self):
        """Test _get_client_ip method variations."""
        # Test with X-Forwarded-For
        request = Mock()
        request.META = {'HTTP_X_FORWARDED_FOR': '192.168.1.1, 10.0.0.1'}
        
        ip = UnifiedSessionManager._get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')
        
        # Test with REMOTE_ADDR
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        ip = UnifiedSessionManager._get_client_ip(request)
        self.assertEqual(ip, '127.0.0.1')
        
        # Test with no IP info
        request.META = {}
        
        ip = UnifiedSessionManager._get_client_ip(request)
        self.assertEqual(ip, '')


class UnifiedAuthPermissionsUnitTests(TestCase):
    """
    Unit tests for UnifiedAuthPermissions class.
    """
    
    def setUp(self):
        """Set up test data."""
        # Create test SuperAdmin
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_active=True,
            can_create_tenants=True,
            can_suspend_tenants=True,
            can_access_all_data=True
        )
        
        # Create SuperAdmin with limited permissions
        self.limited_admin = SuperAdmin.objects.create_user(
            username='limitedadmin',
            email='limited@test.com',
            password='testpass123',
            is_superuser=True,
            is_active=True,
            can_create_tenants=False,
            can_suspend_tenants=False,
            can_access_all_data=False
        )
        
        # Create inactive SuperAdmin
        self.inactive_admin = SuperAdmin.objects.create_user(
            username='inactiveadmin',
            email='inactive@test.com',
            password='testpass123',
            is_superuser=True,
            is_active=False
        )
    
    def test_check_superadmin_permission_valid(self):
        """Test check_superadmin_permission with valid SuperAdmin."""
        result = UnifiedAuthPermissions.check_superadmin_permission(self.superadmin)
        self.assertTrue(result)
    
    def test_check_superadmin_permission_inactive(self):
        """Test check_superadmin_permission with inactive SuperAdmin."""
        result = UnifiedAuthPermissions.check_superadmin_permission(self.inactive_admin)
        self.assertFalse(result)
    
    def test_check_superadmin_permission_none(self):
        """Test check_superadmin_permission with None user."""
        result = UnifiedAuthPermissions.check_superadmin_permission(None)
        self.assertFalse(result)
    
    def test_check_superadmin_permission_unauthenticated(self):
        """Test check_superadmin_permission with unauthenticated user."""
        user = Mock()
        user.is_authenticated = False
        
        result = UnifiedAuthPermissions.check_superadmin_permission(user)
        self.assertFalse(result)
    
    def test_check_superadmin_permission_non_superadmin(self):
        """Test check_superadmin_permission with non-SuperAdmin user."""
        user = Mock()
        user.is_authenticated = True
        user.is_active = True
        user.is_superuser = False
        
        result = UnifiedAuthPermissions.check_superadmin_permission(user)
        self.assertFalse(result)
    
    def test_check_tenant_access_permission_allowed(self):
        """Test check_tenant_access_permission with allowed access."""
        result = UnifiedAuthPermissions.check_tenant_access_permission(
            self.superadmin, 'tenant1'
        )
        self.assertTrue(result)
    
    def test_check_tenant_access_permission_denied(self):
        """Test check_tenant_access_permission with denied access."""
        result = UnifiedAuthPermissions.check_tenant_access_permission(
            self.limited_admin, 'tenant1'
        )
        self.assertFalse(result)
    
    def test_check_tenant_access_permission_non_superadmin(self):
        """Test check_tenant_access_permission with non-SuperAdmin."""
        user = Mock()
        user.is_authenticated = True
        
        result = UnifiedAuthPermissions.check_tenant_access_permission(user, 'tenant1')
        self.assertFalse(result)
    
    def test_check_tenant_creation_permission_allowed(self):
        """Test check_tenant_creation_permission with allowed permission."""
        result = UnifiedAuthPermissions.check_tenant_creation_permission(self.superadmin)
        self.assertTrue(result)
    
    def test_check_tenant_creation_permission_denied(self):
        """Test check_tenant_creation_permission with denied permission."""
        result = UnifiedAuthPermissions.check_tenant_creation_permission(self.limited_admin)
        self.assertFalse(result)
    
    def test_check_tenant_suspension_permission_allowed(self):
        """Test check_tenant_suspension_permission with allowed permission."""
        result = UnifiedAuthPermissions.check_tenant_suspension_permission(self.superadmin)
        self.assertTrue(result)
    
    def test_check_tenant_suspension_permission_denied(self):
        """Test check_tenant_suspension_permission with denied permission."""
        result = UnifiedAuthPermissions.check_tenant_suspension_permission(self.limited_admin)
        self.assertFalse(result)
    
    def test_check_impersonation_permission_allowed(self):
        """Test check_impersonation_permission with allowed permission."""
        result = UnifiedAuthPermissions.check_impersonation_permission(self.superadmin)
        self.assertTrue(result)
    
    def test_check_impersonation_permission_denied(self):
        """Test check_impersonation_permission with denied permission."""
        result = UnifiedAuthPermissions.check_impersonation_permission(self.limited_admin)
        self.assertFalse(result)


class UnifiedAdminAuthMiddlewareUnitTests(TestCase):
    """
    Unit tests for UnifiedAdminAuthMiddleware class.
    """
    
    def setUp(self):
        """Set up test data."""
        self.middleware = UnifiedAdminAuthMiddleware(Mock())
        self.factory = RequestFactory()
        
        # Create test SuperAdmin
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_active=True
        )
    
    def test_process_request_exempt_url(self):
        """Test process_request with exempt URL."""
        request = self.factory.get('/admin/login/')
        
        result = self.middleware.process_request(request)
        self.assertIsNone(result)
    
    def test_process_request_non_admin_url(self):
        """Test process_request with non-admin URL."""
        request = self.factory.get('/api/health/')
        
        result = self.middleware.process_request(request)
        self.assertIsNone(result)
    
    def test_process_request_authenticated_superadmin(self):
        """Test process_request with authenticated SuperAdmin."""
        request = self.factory.get('/admin/dashboard/')
        request.user = self.superadmin
        request.session = {}
        
        result = self.middleware.process_request(request)
        self.assertIsNone(result)
    
    def test_process_request_unauthenticated(self):
        """Test process_request with unauthenticated user."""
        request = self.factory.get('/admin/dashboard/')
        request.user = AnonymousUser()
        
        # Add session middleware
        middleware = SessionMiddleware(Mock())
        middleware.process_request(request)
        request.session.save()
        
        result = self.middleware.process_request(request)
        self.assertIsNotNone(result)  # Should redirect
    
    def test_is_authenticated_superadmin_valid(self):
        """Test _is_authenticated_superadmin with valid SuperAdmin."""
        request = Mock()
        request.user = self.superadmin
        
        result = self.middleware._is_authenticated_superadmin(request)
        self.assertTrue(result)
    
    def test_is_authenticated_superadmin_unauthenticated(self):
        """Test _is_authenticated_superadmin with unauthenticated user."""
        request = Mock()
        request.user = AnonymousUser()
        
        result = self.middleware._is_authenticated_superadmin(request)
        self.assertFalse(result)
    
    def test_is_authenticated_superadmin_no_user(self):
        """Test _is_authenticated_superadmin with no user attribute."""
        request = Mock()
        del request.user
        
        result = self.middleware._is_authenticated_superadmin(request)
        self.assertFalse(result)
    
    def test_update_session_activity(self):
        """Test _update_session_activity method."""
        request = Mock()
        request.session = {}
        
        self.middleware._update_session_activity(request)
        
        self.assertIn('last_activity', request.session)
    
    def test_is_session_expired_no_activity(self):
        """Test _is_session_expired with no last activity."""
        request = Mock()
        request.session = {}
        
        result = self.middleware._is_session_expired(request)
        self.assertTrue(result)
    
    def test_is_session_expired_recent_activity(self):
        """Test _is_session_expired with recent activity."""
        request = Mock()
        request.session = {
            'last_activity': timezone.now().isoformat()
        }
        
        result = self.middleware._is_session_expired(request)
        self.assertFalse(result)
    
    def test_is_session_expired_old_activity(self):
        """Test _is_session_expired with old activity."""
        old_time = timezone.now() - timedelta(hours=3)
        request = Mock()
        request.session = {
            'last_activity': old_time.isoformat()
        }
        
        result = self.middleware._is_session_expired(request)
        self.assertTrue(result)
    
    def test_check_ip_consistency_no_stored_ip(self):
        """Test _check_ip_consistency with no stored IP."""
        request = Mock()
        request.session = {}
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        result = self.middleware._check_ip_consistency(request)
        self.assertTrue(result)
        self.assertEqual(request.session['session_ip'], '127.0.0.1')
    
    def test_check_ip_consistency_matching_ip(self):
        """Test _check_ip_consistency with matching IP."""
        request = Mock()
        request.session = {'session_ip': '127.0.0.1'}
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        result = self.middleware._check_ip_consistency(request)
        self.assertTrue(result)
    
    def test_check_ip_consistency_different_ip(self):
        """Test _check_ip_consistency with different IP."""
        request = Mock()
        request.session = {'session_ip': '127.0.0.1'}
        request.META = {'REMOTE_ADDR': '192.168.1.1'}
        
        result = self.middleware._check_ip_consistency(request)
        self.assertFalse(result)
    
    def test_get_client_ip_variations(self):
        """Test _get_client_ip method with different scenarios."""
        # Test with X-Forwarded-For
        request = Mock()
        request.META = {'HTTP_X_FORWARDED_FOR': '192.168.1.1, 10.0.0.1'}
        
        ip = self.middleware._get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')
        
        # Test with REMOTE_ADDR
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        ip = self.middleware._get_client_ip(request)
        self.assertEqual(ip, '127.0.0.1')
        
        # Test with no IP info
        request.META = {}
        
        ip = self.middleware._get_client_ip(request)
        self.assertEqual(ip, '')


class UnifiedAdminSecurityMiddlewareUnitTests(TestCase):
    """
    Unit tests for UnifiedAdminSecurityMiddleware class.
    """
    
    def setUp(self):
        """Set up test data."""
        self.middleware = UnifiedAdminSecurityMiddleware(Mock())
        self.factory = RequestFactory()
    
    def test_process_request_admin_url(self):
        """Test process_request with admin URL."""
        request = self.factory.get('/admin/dashboard/')
        
        result = self.middleware.process_request(request)
        self.assertIsNone(result)
        
        # Check security context added
        self.assertTrue(hasattr(request, 'is_admin_request'))
        self.assertTrue(request.is_admin_request)
        self.assertTrue(hasattr(request, 'security_context'))
    
    def test_process_request_non_admin_url(self):
        """Test process_request with non-admin URL."""
        request = self.factory.get('/api/health/')
        
        result = self.middleware.process_request(request)
        self.assertIsNone(result)
        
        # Should not add security context
        self.assertFalse(hasattr(request, 'is_admin_request'))
    
    def test_process_response_admin_url(self):
        """Test process_response with admin URL."""
        request = self.factory.get('/admin/dashboard/')
        response = Mock()
        response.__setitem__ = Mock()
        
        result = self.middleware.process_response(request, response)
        
        # Check security headers added
        response.__setitem__.assert_any_call('X-Frame-Options', 'DENY')
        response.__setitem__.assert_any_call('X-Content-Type-Options', 'nosniff')
        response.__setitem__.assert_any_call('X-XSS-Protection', '1; mode=block')
    
    def test_process_response_non_admin_url(self):
        """Test process_response with non-admin URL."""
        request = self.factory.get('/api/health/')
        response = Mock()
        response.__setitem__ = Mock()
        
        result = self.middleware.process_response(request, response)
        
        # Should not add security headers
        response.__setitem__.assert_not_called()
    
    def test_add_security_headers(self):
        """Test _add_security_headers method."""
        request = self.factory.get('/admin/dashboard/')
        
        self.middleware._add_security_headers(request)
        
        # Check security context added
        self.assertTrue(request.is_admin_request)
        self.assertIn('requires_2fa', request.security_context)
        self.assertIn('session_timeout', request.security_context)
        self.assertIn('ip_validation', request.security_context)
        self.assertIn('user_agent_validation', request.security_context)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])