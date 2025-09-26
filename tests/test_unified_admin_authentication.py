"""
Comprehensive tests for unified SuperAdmin authentication system.
Tests authentication, 2FA, session management, and security controls.
"""
import os
import django
from django.conf import settings

# Configure Django settings
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context
from django_otp.plugins.otp_totp.models import TOTPDevice
from unittest.mock import patch, MagicMock
from datetime import timedelta

from zargar.tenants.admin_models import SuperAdmin, TenantAccessLog, SuperAdminSession
from zargar.admin_panel.unified_auth_backend import (
    UnifiedSuperAdminAuthBackend, 
    UnifiedSessionManager, 
    UnifiedAuthPermissions
)


class UnifiedAdminAuthenticationTestCase(TestCase):
    """
    Test case for unified admin authentication system.
    """
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test SuperAdmin user
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_active=True,
            persian_first_name='مدیر',
            persian_last_name='تست',
            phone_number='09123456789'
        )
        
        # Create inactive SuperAdmin for testing
        self.inactive_admin = SuperAdmin.objects.create_user(
            username='inactiveadmin',
            email='inactive@test.com',
            password='testpass123',
            is_superuser=True,
            is_active=False
        )
        
        # URLs
        self.login_url = reverse('admin_panel:unified_login')
        self.logout_url = reverse('admin_panel:unified_logout')
        self.dashboard_url = reverse('admin_panel:dashboard')
        self.session_status_url = reverse('admin_panel:session_status')
    
    def test_unified_auth_backend_valid_credentials(self):
        """Test authentication with valid credentials."""
        backend = UnifiedSuperAdminAuthBackend()
        
        # Mock request
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        request.path = '/admin/login/'
        request.method = 'POST'
        
        # Test authentication
        user = backend.authenticate(
            request=request,
            username='testadmin',
            password='testpass123'
        )
        
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'testadmin')
        self.assertIsInstance(user, SuperAdmin)
    
    def test_unified_auth_backend_invalid_credentials(self):
        """Test authentication with invalid credentials."""
        backend = UnifiedSuperAdminAuthBackend()
        
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        request.path = '/admin/login/'
        request.method = 'POST'
        
        # Test with wrong password
        user = backend.authenticate(
            request=request,
            username='testadmin',
            password='wrongpassword'
        )
        
        self.assertIsNone(user)
        
        # Test with non-existent user
        user = backend.authenticate(
            request=request,
            username='nonexistent',
            password='testpass123'
        )
        
        self.assertIsNone(user)
    
    def test_unified_auth_backend_inactive_user(self):
        """Test authentication with inactive user."""
        backend = UnifiedSuperAdminAuthBackend()
        
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        request.path = '/admin/login/'
        request.method = 'POST'
        
        user = backend.authenticate(
            request=request,
            username='inactiveadmin',
            password='testpass123'
        )
        
        self.assertIsNone(user)
    
    def test_unified_auth_backend_2fa_required(self):
        """Test authentication with 2FA enabled."""
        # Enable 2FA for user
        self.superadmin.is_2fa_enabled = True
        self.superadmin.save()
        
        backend = UnifiedSuperAdminAuthBackend()
        
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        request.path = '/admin/login/'
        request.method = 'POST'
        
        # Test without 2FA token
        user = backend.authenticate(
            request=request,
            username='testadmin',
            password='testpass123'
        )
        
        self.assertIsNone(user)  # Should return None to prompt for 2FA
        
        # Test with invalid 2FA token
        user = backend.authenticate(
            request=request,
            username='testadmin',
            password='testpass123',
            otp_token='123456'
        )
        
        self.assertIsNone(user)  # Should fail with invalid token
    
    @patch('zargar.admin_panel.unified_auth_backend.match_token')
    def test_unified_auth_backend_2fa_valid(self, mock_match_token):
        """Test authentication with valid 2FA token."""
        # Enable 2FA for user
        self.superadmin.is_2fa_enabled = True
        self.superadmin.save()
        
        # Mock successful 2FA verification
        mock_device = MagicMock()
        mock_match_token.return_value = mock_device
        
        backend = UnifiedSuperAdminAuthBackend()
        
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        request.path = '/admin/login/'
        request.method = 'POST'
        
        user = backend.authenticate(
            request=request,
            username='testadmin',
            password='testpass123',
            otp_token='123456'
        )
        
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'testadmin')
        mock_match_token.assert_called_once_with(self.superadmin, '123456')
    
    def test_unified_auth_backend_get_user(self):
        """Test getting user by ID."""
        backend = UnifiedSuperAdminAuthBackend()
        
        # Test valid user ID
        user = backend.get_user(self.superadmin.id)
        self.assertEqual(user, self.superadmin)
        
        # Test invalid user ID
        user = backend.get_user(99999)
        self.assertIsNone(user)
    
    def test_login_view_get(self):
        """Test login view GET request."""
        response = self.client.get(self.login_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ورود مدیر سیستم')
        self.assertContains(response, 'نام کاربری')
        self.assertContains(response, 'رمز عبور')
    
    def test_login_view_valid_credentials(self):
        """Test login with valid credentials."""
        response = self.client.post(self.login_url, {
            'username': 'testadmin',
            'password': 'testpass123'
        })
        
        # Should redirect to dashboard
        self.assertRedirects(response, self.dashboard_url)
        
        # Check session
        self.assertTrue('_auth_user_id' in self.client.session)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.superadmin.id)
    
    def test_login_view_invalid_credentials(self):
        """Test login with invalid credentials."""
        response = self.client.post(self.login_url, {
            'username': 'testadmin',
            'password': 'wrongpassword'
        })
        
        # Should stay on login page
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'نام کاربری یا رمز عبور اشتباه است')
        
        # Check no session created
        self.assertFalse('_auth_user_id' in self.client.session)
    
    def test_login_view_missing_fields(self):
        """Test login with missing fields."""
        # Missing password
        response = self.client.post(self.login_url, {
            'username': 'testadmin'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'نام کاربری و رمز عبور الزامی است')
        
        # Missing username
        response = self.client.post(self.login_url, {
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'نام کاربری و رمز عبور الزامی است')
    
    def test_login_view_inactive_user(self):
        """Test login with inactive user."""
        response = self.client.post(self.login_url, {
            'username': 'inactiveadmin',
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'نام کاربری یا رمز عبور اشتباه است')
    
    def test_login_view_rate_limiting(self):
        """Test login rate limiting."""
        # Make multiple failed attempts
        for i in range(6):  # Exceed the limit of 5
            response = self.client.post(self.login_url, {
                'username': 'testadmin',
                'password': 'wrongpassword'
            })
        
        # Should be rate limited
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تعداد تلاش‌های ناموفق زیاد است')
    
    def test_login_view_2fa_flow(self):
        """Test 2FA login flow."""
        # Enable 2FA for user
        self.superadmin.is_2fa_enabled = True
        self.superadmin.save()
        
        # First step: username/password
        response = self.client.post(self.login_url, {
            'username': 'testadmin',
            'password': 'testpass123'
        })
        
        # Should stay on login page but show 2FA field
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'کد تأیید دو مرحله‌ای را وارد کنید')
        
        # Check session state
        self.assertTrue(self.client.session.get('requires_2fa'))
        self.assertEqual(self.client.session.get('partial_auth_username'), 'testadmin')
    
    def test_logout_view(self):
        """Test logout functionality."""
        # Login first
        self.client.force_login(self.superadmin)
        
        # Test logout
        response = self.client.post(self.logout_url)
        
        # Should redirect to login
        self.assertRedirects(response, self.login_url)
        
        # Check session cleared
        self.assertFalse('_auth_user_id' in self.client.session)
    
    def test_logout_view_unauthenticated(self):
        """Test logout when not authenticated."""
        response = self.client.post(self.logout_url)
        
        # Should redirect to login
        self.assertRedirects(response, self.login_url)
    
    def test_session_manager_create_session(self):
        """Test session creation."""
        request = MagicMock()
        request.session = {}
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        
        session = UnifiedSessionManager.create_admin_session(request, self.superadmin)
        
        self.assertIsNotNone(session)
        self.assertEqual(session.super_admin, self.superadmin)
        self.assertEqual(session.tenant_schema, 'public')
        self.assertTrue(session.is_active)
        
        # Check session data stored
        self.assertIn('admin_session_id', request.session)
        self.assertIn('admin_user_id', request.session)
        self.assertIn('admin_username', request.session)
    
    def test_session_manager_track_tenant_access(self):
        """Test tenant access tracking."""
        request = MagicMock()
        request.session = {}
        request.path = '/admin/tenants/'
        request.method = 'GET'
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
    
    def test_session_manager_end_session(self):
        """Test session termination."""
        # Create session first
        request = MagicMock()
        request.session = {}
        request.path = '/admin/logout/'
        request.method = 'POST'
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        
        session = UnifiedSessionManager.create_admin_session(request, self.superadmin)
        
        # End session
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
    
    def test_auth_permissions_check_superadmin(self):
        """Test SuperAdmin permission checking."""
        # Valid SuperAdmin
        self.assertTrue(UnifiedAuthPermissions.check_superadmin_permission(self.superadmin))
        
        # Inactive SuperAdmin
        self.assertFalse(UnifiedAuthPermissions.check_superadmin_permission(self.inactive_admin))
        
        # None user
        self.assertFalse(UnifiedAuthPermissions.check_superadmin_permission(None))
        
        # Regular user (if exists)
        regular_user = MagicMock()
        regular_user.is_authenticated = True
        regular_user.is_active = True
        regular_user.is_superuser = False
        self.assertFalse(UnifiedAuthPermissions.check_superadmin_permission(regular_user))
    
    def test_auth_permissions_tenant_access(self):
        """Test tenant access permissions."""
        # SuperAdmin with access
        self.assertTrue(UnifiedAuthPermissions.check_tenant_access_permission(self.superadmin, 'tenant1'))
        
        # SuperAdmin without access
        self.superadmin.can_access_all_data = False
        self.superadmin.save()
        self.assertFalse(UnifiedAuthPermissions.check_tenant_access_permission(self.superadmin, 'tenant1'))
        
        # Non-SuperAdmin
        regular_user = MagicMock()
        regular_user.is_authenticated = True
        self.assertFalse(UnifiedAuthPermissions.check_tenant_access_permission(regular_user, 'tenant1'))
    
    def test_auth_permissions_tenant_creation(self):
        """Test tenant creation permissions."""
        # SuperAdmin with permission
        self.assertTrue(UnifiedAuthPermissions.check_tenant_creation_permission(self.superadmin))
        
        # SuperAdmin without permission
        self.superadmin.can_create_tenants = False
        self.superadmin.save()
        self.assertFalse(UnifiedAuthPermissions.check_tenant_creation_permission(self.superadmin))
    
    def test_auth_permissions_tenant_suspension(self):
        """Test tenant suspension permissions."""
        # SuperAdmin with permission
        self.assertTrue(UnifiedAuthPermissions.check_tenant_suspension_permission(self.superadmin))
        
        # SuperAdmin without permission
        self.superadmin.can_suspend_tenants = False
        self.superadmin.save()
        self.assertFalse(UnifiedAuthPermissions.check_tenant_suspension_permission(self.superadmin))
    
    def test_session_status_api_authenticated(self):
        """Test session status API when authenticated."""
        self.client.force_login(self.superadmin)
        
        response = self.client.get(self.session_status_url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['authenticated'])
        self.assertEqual(data['username'], 'testadmin')
        self.assertIn('permissions', data)
    
    def test_session_status_api_unauthenticated(self):
        """Test session status API when not authenticated."""
        response = self.client.get(self.session_status_url)
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        
        self.assertFalse(data['authenticated'])
        self.assertIn('error', data)
    
    def test_audit_logging(self):
        """Test comprehensive audit logging."""
        # Test successful login logging
        self.client.post(self.login_url, {
            'username': 'testadmin',
            'password': 'testpass123'
        })
        
        # Check login log created
        login_log = TenantAccessLog.objects.filter(
            username='testadmin',
            action='login',
            success=True
        ).first()
        
        self.assertIsNotNone(login_log)
        self.assertEqual(login_log.tenant_schema, 'public')
        self.assertIn('authentication_method', login_log.details)
        
        # Test failed login logging
        self.client.post(self.login_url, {
            'username': 'testadmin',
            'password': 'wrongpassword'
        })
        
        # Check failed login log created
        failed_log = TenantAccessLog.objects.filter(
            username='testadmin',
            action='login',
            success=False
        ).first()
        
        self.assertIsNotNone(failed_log)
        self.assertIn('failure_reason', failed_log.details)
    
    def test_security_headers(self):
        """Test security headers in admin responses."""
        self.client.force_login(self.superadmin)
        
        response = self.client.get(self.dashboard_url)
        
        # Check security headers
        self.assertEqual(response.get('X-Frame-Options'), 'DENY')
        self.assertEqual(response.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(response.get('X-XSS-Protection'), '1; mode=block')
        self.assertIn('Content-Security-Policy', response)
    
    def test_remember_me_functionality(self):
        """Test remember me functionality."""
        # Login with remember me
        response = self.client.post(self.login_url, {
            'username': 'testadmin',
            'password': 'testpass123',
            'remember_me': 'on'
        })
        
        self.assertRedirects(response, self.dashboard_url)
        
        # Check session expiry is extended (30 days)
        session_key = self.client.session.session_key
        session = Session.objects.get(session_key=session_key)
        
        # Session should expire in about 30 days
        expected_expiry = timezone.now() + timedelta(days=29)  # Allow some margin
        self.assertGreater(session.expire_date, expected_expiry)
    
    def test_csrf_protection(self):
        """Test CSRF protection on login form."""
        # GET request should include CSRF token
        response = self.client.get(self.login_url)
        self.assertContains(response, 'csrfmiddlewaretoken')
        
        # POST without CSRF should fail
        client_no_csrf = Client(enforce_csrf_checks=True)
        response = client_no_csrf.post(self.login_url, {
            'username': 'testadmin',
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, 403)
    
    def test_redirect_after_login(self):
        """Test redirect to next URL after login."""
        # Try to access protected page
        protected_url = '/admin/tenants/'
        response = self.client.get(protected_url)
        
        # Should redirect to login with next parameter
        self.assertRedirects(response, f'{self.login_url}?next={protected_url}')
        
        # Login should redirect to original page
        response = self.client.post(self.login_url, {
            'username': 'testadmin',
            'password': 'testpass123'
        })
        
        # Should redirect to the protected page
        self.assertRedirects(response, protected_url)


@pytest.mark.django_db
class UnifiedAdminAuthenticationIntegrationTest:
    """
    Integration tests for unified admin authentication.
    """
    
    def test_full_authentication_flow(self):
        """Test complete authentication flow."""
        client = Client()
        
        # Create SuperAdmin
        superadmin = SuperAdmin.objects.create_user(
            username='integrationtest',
            email='integration@test.com',
            password='testpass123',
            is_superuser=True,
            is_active=True
        )
        
        login_url = reverse('admin_panel:unified_login')
        dashboard_url = reverse('admin_panel:dashboard')
        logout_url = reverse('admin_panel:unified_logout')
        
        # Step 1: Access login page
        response = client.get(login_url)
        assert response.status_code == 200
        
        # Step 2: Submit login form
        response = client.post(login_url, {
            'username': 'integrationtest',
            'password': 'testpass123'
        })
        assert response.status_code == 302
        
        # Step 3: Access dashboard
        response = client.get(dashboard_url)
        assert response.status_code == 200
        
        # Step 4: Check session created
        assert SuperAdminSession.objects.filter(super_admin=superadmin).exists()
        
        # Step 5: Logout
        response = client.post(logout_url)
        assert response.status_code == 302
        
        # Step 6: Verify session ended
        session = SuperAdminSession.objects.filter(super_admin=superadmin).first()
        assert not session.is_active
    
    def test_security_violation_handling(self):
        """Test security violation detection and handling."""
        client = Client()
        
        # Create SuperAdmin
        superadmin = SuperAdmin.objects.create_user(
            username='securitytest',
            email='security@test.com',
            password='testpass123',
            is_superuser=True,
            is_active=True
        )
        
        login_url = reverse('admin_panel:unified_login')
        
        # Login successfully
        client.post(login_url, {
            'username': 'securitytest',
            'password': 'testpass123'
        })
        
        # Simulate IP change (security violation)
        with patch('zargar.admin_panel.unified_auth_middleware.UnifiedAdminAuthMiddleware._get_client_ip') as mock_ip:
            mock_ip.return_value = '192.168.1.100'  # Different IP
            
            response = client.get(reverse('admin_panel:dashboard'))
            
            # Should redirect to login due to security violation
            assert response.status_code == 302
            assert login_url in response.url
        
        # Check security violation logged
        violation_log = TenantAccessLog.objects.filter(
            username='securitytest',
            action='security_violation'
        ).first()
        
        assert violation_log is not None
        assert 'ip_mismatch' in violation_log.details.get('violation_type', '')


if __name__ == '__main__':
    pytest.main([__file__])