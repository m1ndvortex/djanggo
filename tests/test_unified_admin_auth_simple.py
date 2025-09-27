"""
Simple tests for unified SuperAdmin authentication system.
Tests core authentication functionality without complex Django setup.
"""
import pytest
from unittest.mock import MagicMock, patch
from django.test import TestCase
from django.contrib.auth import authenticate
from django.db import connection
from django_tenants.utils import get_public_schema_name

from zargar.tenants.admin_models import SuperAdmin
from zargar.admin_panel.unified_auth_backend import (
    UnifiedSuperAdminAuthBackend,
    UnifiedAuthPermissions
)


class TestUnifiedSuperAdminAuthBackend(TestCase):
    """Test the unified SuperAdmin authentication backend."""
    
    def setUp(self):
        """Set up test data."""
        self.backend = UnifiedSuperAdminAuthBackend()
        
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
        """Test authentication with valid credentials."""
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        request.path = '/admin/login/'
        request.method = 'POST'
        
        user = self.backend.authenticate(
            request=request,
            username='testadmin',
            password='testpass123'
        )
        
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'testadmin')
        self.assertIsInstance(user, SuperAdmin)
    
    def test_authenticate_invalid_password(self):
        """Test authentication with invalid password."""
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        request.path = '/admin/login/'
        request.method = 'POST'
        
        user = self.backend.authenticate(
            request=request,
            username='testadmin',
            password='wrongpassword'
        )
        
        self.assertIsNone(user)
    
    def test_authenticate_nonexistent_user(self):
        """Test authentication with non-existent user."""
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        request.path = '/admin/login/'
        request.method = 'POST'
        
        user = self.backend.authenticate(
            request=request,
            username='nonexistent',
            password='testpass123'
        )
        
        self.assertIsNone(user)
    
    def test_authenticate_inactive_user(self):
        """Test authentication with inactive user."""
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        request.path = '/admin/login/'
        request.method = 'POST'
        
        user = self.backend.authenticate(
            request=request,
            username='inactiveadmin',
            password='testpass123'
        )
        
        self.assertIsNone(user)
    
    def test_authenticate_missing_credentials(self):
        """Test authentication with missing credentials."""
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        request.path = '/admin/login/'
        request.method = 'POST'
        
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
        
        # Both missing
        user = self.backend.authenticate(
            request=request,
            username=None,
            password=None
        )
        self.assertIsNone(user)
    
    def test_authenticate_2fa_required_no_token(self):
        """Test authentication when 2FA is required but no token provided."""
        # Enable 2FA for user
        self.superadmin.is_2fa_enabled = True
        self.superadmin.save()
        
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        request.path = '/admin/login/'
        request.method = 'POST'
        
        user = self.backend.authenticate(
            request=request,
            username='testadmin',
            password='testpass123'
        )
        
        # Should return None to indicate 2FA is required
        self.assertIsNone(user)
    
    @patch('zargar.admin_panel.unified_auth_backend.match_token')
    def test_authenticate_2fa_valid_token(self, mock_match_token):
        """Test authentication with valid 2FA token."""
        # Enable 2FA for user
        self.superadmin.is_2fa_enabled = True
        self.superadmin.save()
        
        # Mock successful 2FA verification
        mock_device = MagicMock()
        mock_match_token.return_value = mock_device
        
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        request.path = '/admin/login/'
        request.method = 'POST'
        
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
        """Test authentication with invalid 2FA token."""
        # Enable 2FA for user
        self.superadmin.is_2fa_enabled = True
        self.superadmin.save()
        
        # Mock failed 2FA verification
        mock_match_token.return_value = None
        
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
        request.path = '/admin/login/'
        request.method = 'POST'
        
        user = self.backend.authenticate(
            request=request,
            username='testadmin',
            password='testpass123',
            otp_token='123456'
        )
        
        self.assertIsNone(user)
        mock_match_token.assert_called_once_with(self.superadmin, '123456')
    
    def test_get_user_valid_id(self):
        """Test getting user by valid ID."""
        user = self.backend.get_user(self.superadmin.id)
        self.assertEqual(user, self.superadmin)
    
    def test_get_user_invalid_id(self):
        """Test getting user by invalid ID."""
        user = self.backend.get_user(99999)
        self.assertIsNone(user)
    
    def test_user_can_authenticate_active_superuser(self):
        """Test user_can_authenticate with active superuser."""
        result = self.backend.user_can_authenticate(self.superadmin)
        self.assertTrue(result)
    
    def test_user_can_authenticate_inactive_user(self):
        """Test user_can_authenticate with inactive user."""
        result = self.backend.user_can_authenticate(self.inactive_admin)
        self.assertFalse(result)
    
    def test_user_can_authenticate_non_superadmin(self):
        """Test user_can_authenticate with non-SuperAdmin user."""
        regular_user = MagicMock()
        regular_user.is_active = True
        regular_user.is_superuser = False
        
        result = self.backend.user_can_authenticate(regular_user)
        self.assertFalse(result)  # Should return False for non-SuperAdmin users


class TestUnifiedAuthPermissions(TestCase):
    """Test the unified authentication permissions."""
    
    def setUp(self):
        """Set up test data."""
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
        
        self.inactive_admin = SuperAdmin.objects.create_user(
            username='inactiveadmin',
            email='inactive@test.com',
            password='testpass123',
            is_superuser=True,
            is_active=False
        )
    
    def test_check_superadmin_permission_valid(self):
        """Test SuperAdmin permission check with valid user."""
        result = UnifiedAuthPermissions.check_superadmin_permission(self.superadmin)
        self.assertTrue(result)
    
    def test_check_superadmin_permission_inactive(self):
        """Test SuperAdmin permission check with inactive user."""
        result = UnifiedAuthPermissions.check_superadmin_permission(self.inactive_admin)
        self.assertFalse(result)
    
    def test_check_superadmin_permission_none(self):
        """Test SuperAdmin permission check with None user."""
        result = UnifiedAuthPermissions.check_superadmin_permission(None)
        self.assertFalse(result)
    
    def test_check_superadmin_permission_unauthenticated(self):
        """Test SuperAdmin permission check with unauthenticated user."""
        user = MagicMock()
        user.is_authenticated = False
        
        result = UnifiedAuthPermissions.check_superadmin_permission(user)
        self.assertFalse(result)
    
    def test_check_tenant_access_permission_allowed(self):
        """Test tenant access permission when allowed."""
        result = UnifiedAuthPermissions.check_tenant_access_permission(self.superadmin, 'tenant1')
        self.assertTrue(result)
    
    def test_check_tenant_access_permission_denied(self):
        """Test tenant access permission when denied."""
        self.superadmin.can_access_all_data = False
        self.superadmin.save()
        
        result = UnifiedAuthPermissions.check_tenant_access_permission(self.superadmin, 'tenant1')
        self.assertFalse(result)
    
    def test_check_tenant_access_permission_non_superadmin(self):
        """Test tenant access permission with non-SuperAdmin."""
        regular_user = MagicMock()
        regular_user.is_authenticated = True
        
        result = UnifiedAuthPermissions.check_tenant_access_permission(regular_user, 'tenant1')
        self.assertFalse(result)
    
    def test_check_tenant_creation_permission_allowed(self):
        """Test tenant creation permission when allowed."""
        result = UnifiedAuthPermissions.check_tenant_creation_permission(self.superadmin)
        self.assertTrue(result)
    
    def test_check_tenant_creation_permission_denied(self):
        """Test tenant creation permission when denied."""
        self.superadmin.can_create_tenants = False
        self.superadmin.save()
        
        result = UnifiedAuthPermissions.check_tenant_creation_permission(self.superadmin)
        self.assertFalse(result)
    
    def test_check_tenant_suspension_permission_allowed(self):
        """Test tenant suspension permission when allowed."""
        result = UnifiedAuthPermissions.check_tenant_suspension_permission(self.superadmin)
        self.assertTrue(result)
    
    def test_check_tenant_suspension_permission_denied(self):
        """Test tenant suspension permission when denied."""
        self.superadmin.can_suspend_tenants = False
        self.superadmin.save()
        
        result = UnifiedAuthPermissions.check_tenant_suspension_permission(self.superadmin)
        self.assertFalse(result)
    
    def test_check_impersonation_permission_allowed(self):
        """Test impersonation permission when allowed."""
        result = UnifiedAuthPermissions.check_impersonation_permission(self.superadmin)
        self.assertTrue(result)
    
    def test_check_impersonation_permission_denied(self):
        """Test impersonation permission when denied."""
        self.superadmin.can_access_all_data = False
        self.superadmin.save()
        
        result = UnifiedAuthPermissions.check_impersonation_permission(self.superadmin)
        self.assertFalse(result)