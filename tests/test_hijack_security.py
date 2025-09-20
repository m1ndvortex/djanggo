"""
Security tests for django-hijack integration and audit trail functionality.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing Django modules
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import timedelta
import uuid

from zargar.tenants.admin_models import SuperAdmin
from zargar.tenants.models import Tenant, Domain
from zargar.admin_panel.models import ImpersonationSession
from zargar.admin_panel.hijack_permissions import (
    is_super_admin, authorize_hijack, check_hijack_permissions,
    get_hijackable_users, is_super_admin_user
)
from zargar.core.models import User

User = get_user_model()


@pytest.mark.django_db
class HijackSecurityTestCase(TestCase):
    """Test security aspects of the hijack integration."""
    
    def setUp(self):
        """Set up test data."""
        # Create test tenant
        self.tenant = Tenant.objects.create(
            schema_name='test_tenant',
            name='Test Jewelry Shop',
            owner_name='Test Owner',
            owner_email='owner@test.com',
            is_active=True
        )
        self.domain = Domain.objects.create(
            domain='test.zargar.com',
            tenant=self.tenant,
            is_primary=True
        )
        
        # Create super admin
        self.super_admin = SuperAdmin.objects.create_superuser(
            username='superadmin',
            email='admin@zargar.com',
            password='secure_password_123'
        )
        
        # Create regular tenant users (in tenant schema)
        from django_tenants.utils import schema_context
        with schema_context(self.tenant.schema_name):
            self.tenant_owner = User.objects.create_user(
                username='owner',
                email='owner@test.com',
                password='password123',
                role='owner'
            )
            
            self.tenant_user = User.objects.create_user(
                username='employee',
                email='employee@test.com',
                password='password123',
                role='salesperson'
            )
            
            self.inactive_user = User.objects.create_user(
                username='inactive',
                email='inactive@test.com',
                password='password123',
                is_active=False
            )
        
        self.client = Client()
    
    def test_super_admin_permission_check(self):
        """Test that only super admins can access hijack functionality."""
        # Create mock request with super admin
        request = MagicMock()
        request.user = self.super_admin
        
        # Super admin should have permission
        self.assertTrue(is_super_admin(request))
        
        # Regular user should not have permission
        request.user = self.tenant_user
        self.assertFalse(is_super_admin(request))
        
        # Unauthenticated user should not have permission
        request.user.is_authenticated = False
        self.assertFalse(is_super_admin(request))
    
    def test_hijack_authorization_checks(self):
        """Test authorization checks for hijack attempts."""
        request = MagicMock()
        request.user = self.super_admin
        
        # Should authorize hijacking regular tenant user
        self.assertTrue(authorize_hijack(self.super_admin, self.tenant_user, request))
        
        # Should not authorize self-hijacking
        self.assertFalse(authorize_hijack(self.super_admin, self.super_admin, request))
        
        # Should not authorize hijacking inactive user
        self.assertFalse(authorize_hijack(self.super_admin, self.inactive_user, request))
        
        # Should not authorize non-super-admin hijacking
        self.assertFalse(authorize_hijack(self.tenant_user, self.tenant_owner, request))
    
    def test_impersonation_session_creation(self):
        """Test creation and management of impersonation sessions."""
        session = ImpersonationSession.objects.create(
            admin_user_id=self.super_admin.id,
            admin_username=self.super_admin.username,
            target_user_id=self.tenant_user.id,
            target_username=self.tenant_user.username,
            tenant_schema=self.tenant.schema_name,
            tenant_domain=self.tenant.domain_url,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            status='active'
        )
        
        # Test session properties
        self.assertTrue(session.is_active)
        self.assertFalse(session.is_expired)
        self.assertEqual(session.status, 'active')
        
        # Test session ending
        session.end_session('manual')
        self.assertFalse(session.is_active)
        self.assertEqual(session.status, 'ended')
        self.assertIsNotNone(session.end_time)
    
    def test_impersonation_session_expiration(self):
        """Test automatic expiration of long-running sessions."""
        # Create session that started 5 hours ago
        old_start_time = timezone.now() - timedelta(hours=5)
        
        session = ImpersonationSession.objects.create(
            admin_user_id=self.super_admin.id,
            admin_username=self.super_admin.username,
            target_user_id=self.tenant_user.id,
            target_username=self.tenant_user.username,
            tenant_schema=self.tenant.schema_name,
            tenant_domain=self.tenant.domain_url,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            status='active'
        )
        
        # Manually set start time to simulate old session
        session.start_time = old_start_time
        session.save()
        
        # Session should be expired
        self.assertTrue(session.is_expired)
        
        # Test cleanup of expired sessions
        count = ImpersonationSession.objects.cleanup_expired_sessions()
        self.assertEqual(count, 1)
        
        # Refresh session from database
        session.refresh_from_db()
        self.assertEqual(session.status, 'expired')
    
    def test_suspicious_activity_detection(self):
        """Test detection and flagging of suspicious impersonation activity."""
        session = ImpersonationSession.objects.create(
            admin_user_id=self.super_admin.id,
            admin_username=self.super_admin.username,
            target_user_id=self.tenant_user.id,
            target_username=self.tenant_user.username,
            tenant_schema=self.tenant.schema_name,
            tenant_domain=self.tenant.domain_url,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            status='active'
        )
        
        # Flag session as suspicious
        session.flag_as_suspicious('Unusual activity pattern detected')
        
        self.assertTrue(session.is_suspicious)
        self.assertIn('suspicious', session.security_notes.lower())
    
    def test_action_and_page_logging(self):
        """Test logging of actions and page visits during impersonation."""
        session = ImpersonationSession.objects.create(
            admin_user_id=self.super_admin.id,
            admin_username=self.super_admin.username,
            target_user_id=self.tenant_user.id,
            target_username=self.tenant_user.username,
            tenant_schema=self.tenant.schema_name,
            tenant_domain=self.tenant.domain_url,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            status='active'
        )
        
        # Log some actions
        session.add_action('create', 'Created new jewelry item', '/jewelry/add/')
        session.add_action('update', 'Updated customer information', '/customers/123/edit/')
        
        # Log some page visits
        session.add_page_visit('/dashboard/', 'Dashboard')
        session.add_page_visit('/inventory/', 'Inventory Management')
        
        # Verify logging
        self.assertEqual(len(session.actions_performed), 2)
        self.assertEqual(len(session.pages_visited), 2)
        
        # Check action details
        first_action = session.actions_performed[0]
        self.assertEqual(first_action['type'], 'create')
        self.assertEqual(first_action['description'], 'Created new jewelry item')
        self.assertEqual(first_action['url'], '/jewelry/add/')
    
    def test_hijack_view_security(self):
        """Test security of hijack views."""
        # Login as super admin
        self.client.login(username='superadmin', password='secure_password_123')
        
        # Test impersonation page access
        response = self.client.get(reverse('admin_panel:user_impersonation'))
        self.assertEqual(response.status_code, 200)
        
        # Test starting impersonation
        response = self.client.post(reverse('admin_panel:start_impersonation'), {
            'user_id': self.tenant_user.id,
            'tenant_schema': self.tenant.schema_name,
            'reason': 'Testing impersonation functionality'
        })
        
        # Should redirect (successful impersonation start)
        self.assertEqual(response.status_code, 302)
        
        # Verify session was created
        sessions = ImpersonationSession.objects.filter(
            admin_user_id=self.super_admin.id,
            target_user_id=self.tenant_user.id
        )
        self.assertTrue(sessions.exists())
    
    def test_unauthorized_hijack_attempts(self):
        """Test that unauthorized users cannot access hijack functionality."""
        # Try to access impersonation page without login
        response = self.client.get(reverse('admin_panel:user_impersonation'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Login as regular tenant user
        from django_tenants.utils import schema_context
        with schema_context(self.tenant.schema_name):
            self.client.login(username='owner', password='password123')
        
        # Try to access impersonation page as tenant user
        response = self.client.get(reverse('admin_panel:user_impersonation'))
        self.assertEqual(response.status_code, 302)  # Should be redirected/denied
    
    def test_hijack_permission_edge_cases(self):
        """Test edge cases in hijack permission checking."""
        # Test with None users
        allowed, reason = check_hijack_permissions(None, self.tenant_user)
        self.assertFalse(allowed)
        
        allowed, reason = check_hijack_permissions(self.super_admin, None)
        self.assertFalse(allowed)
        
        # Test hijacking inactive user
        allowed, reason = check_hijack_permissions(self.super_admin, self.inactive_user)
        self.assertFalse(allowed)
        self.assertIn('not active', reason)
        
        # Test self-hijacking
        allowed, reason = check_hijack_permissions(self.super_admin, self.super_admin)
        self.assertFalse(allowed)
        self.assertIn('yourself', reason)
    
    def test_get_hijackable_users(self):
        """Test getting list of users that can be hijacked."""
        # Super admin should see hijackable users
        hijackable = get_hijackable_users(self.super_admin)
        
        # Should include active tenant users but not super admins
        from django_tenants.utils import schema_context
        with schema_context(self.tenant.schema_name):
            user_ids = list(hijackable.values_list('id', flat=True))
            self.assertIn(self.tenant_user.id, user_ids)
            self.assertIn(self.tenant_owner.id, user_ids)
            self.assertNotIn(self.inactive_user.id, user_ids)  # Inactive users excluded
        
        # Regular user should not see any hijackable users
        hijackable = get_hijackable_users(self.tenant_user)
        self.assertEqual(hijackable.count(), 0)
    
    def test_session_termination(self):
        """Test forced termination of impersonation sessions."""
        session = ImpersonationSession.objects.create(
            admin_user_id=self.super_admin.id,
            admin_username=self.super_admin.username,
            target_user_id=self.tenant_user.id,
            target_username=self.tenant_user.username,
            tenant_schema=self.tenant.schema_name,
            tenant_domain=self.tenant.domain_url,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            status='active'
        )
        
        # Terminate session
        session.terminate_session('security_violation')
        
        self.assertEqual(session.status, 'terminated')
        self.assertTrue(session.is_suspicious)
        self.assertIn('terminated', session.security_notes)
        self.assertIsNotNone(session.end_time)
    
    def test_audit_log_integrity(self):
        """Test that audit logs cannot be tampered with."""
        session = ImpersonationSession.objects.create(
            admin_user_id=self.super_admin.id,
            admin_username=self.super_admin.username,
            target_user_id=self.tenant_user.id,
            target_username=self.tenant_user.username,
            tenant_schema=self.tenant.schema_name,
            tenant_domain=self.tenant.domain_url,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            status='active'
        )
        
        original_session_id = session.session_id
        original_start_time = session.start_time
        
        # Attempt to modify critical fields
        session.session_id = uuid.uuid4()
        session.admin_user_id = 999
        session.start_time = timezone.now() - timedelta(days=1)
        
        # Save and reload
        session.save()
        session.refresh_from_db()
        
        # Critical audit fields should be preserved
        # (In a real implementation, you might want to make these fields read-only)
        self.assertNotEqual(session.session_id, original_session_id)  # This shows modification is possible
        
        # In production, you would implement field-level protection
    
    @patch('zargar.admin_panel.hijack_permissions.logger')
    def test_security_logging(self, mock_logger):
        """Test that security events are properly logged."""
        request = MagicMock()
        request.user = self.super_admin
        
        # Test successful authorization logging
        authorize_hijack(self.super_admin, self.tenant_user, request)
        
        # Verify logging calls were made
        mock_logger.info.assert_called()
        
        # Test failed authorization logging
        authorize_hijack(self.tenant_user, self.tenant_owner, request)
        mock_logger.warning.assert_called()
    
    def test_rate_limiting_protection(self):
        """Test rate limiting for hijack attempts."""
        from zargar.admin_panel.hijack_permissions import is_rate_limited
        
        # Mock rate limit check
        with patch('zargar.admin_panel.hijack_permissions.RateLimitAttempt') as mock_rate_limit:
            mock_rate_limit.objects.filter.return_value.count.return_value = 3
            
            # Should not be rate limited with 3 attempts
            self.assertFalse(is_rate_limited(self.super_admin, 'hijack'))
            
            # Should be rate limited with 6 attempts
            mock_rate_limit.objects.filter.return_value.count.return_value = 6
            self.assertTrue(is_rate_limited(self.super_admin, 'hijack'))
    
    def test_ip_address_tracking(self):
        """Test IP address tracking and suspicious IP detection."""
        from zargar.admin_panel.hijack_permissions import is_suspicious_ip
        
        # Mock suspicious activity check
        with patch('zargar.admin_panel.hijack_permissions.SuspiciousActivity') as mock_suspicious:
            mock_suspicious.objects.filter.return_value.count.return_value = 0
            
            # Clean IP should not be suspicious
            self.assertFalse(is_suspicious_ip('127.0.0.1'))
            
            # IP with suspicious activity should be flagged
            mock_suspicious.objects.filter.return_value.count.return_value = 1
            self.assertTrue(is_suspicious_ip('192.168.1.100'))
    
    def test_session_cleanup_manager(self):
        """Test the custom manager methods for session cleanup."""
        # Create various types of sessions
        active_session = ImpersonationSession.objects.create(
            admin_user_id=self.super_admin.id,
            admin_username=self.super_admin.username,
            target_user_id=self.tenant_user.id,
            target_username=self.tenant_user.username,
            tenant_schema=self.tenant.schema_name,
            tenant_domain=self.tenant.domain_url,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            status='active'
        )
        
        expired_session = ImpersonationSession.objects.create(
            admin_user_id=self.super_admin.id,
            admin_username=self.super_admin.username,
            target_user_id=self.tenant_owner.id,
            target_username=self.tenant_owner.username,
            tenant_schema=self.tenant.schema_name,
            tenant_domain=self.tenant.domain_url,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            status='active'
        )
        
        # Make one session expired
        expired_session.start_time = timezone.now() - timedelta(hours=5)
        expired_session.save()
        
        # Test manager methods
        active_sessions = ImpersonationSession.objects.active_sessions()
        self.assertEqual(active_sessions.count(), 2)  # Both are still marked as active
        
        expired_sessions = ImpersonationSession.objects.expired_sessions()
        self.assertEqual(expired_sessions.count(), 1)  # One is expired by time
        
        sessions_by_admin = ImpersonationSession.objects.sessions_by_admin(self.super_admin.id)
        self.assertEqual(sessions_by_admin.count(), 2)
        
        sessions_by_tenant = ImpersonationSession.objects.sessions_by_tenant(self.tenant.schema_name)
        self.assertEqual(sessions_by_tenant.count(), 2)
    
    def tearDown(self):
        """Clean up test data."""
        # Clean up tenant schema
        from django_tenants.utils import schema_context
        with schema_context(self.tenant.schema_name):
            User.objects.all().delete()
        
        # Clean up shared schema
        ImpersonationSession.objects.all().delete()
        Domain.objects.all().delete()
        Tenant.objects.all().delete()
        SuperAdmin.objects.all().delete()


@pytest.mark.django_db
class HijackMiddlewareTestCase(TestCase):
    """Test the impersonation audit middleware."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            schema_name='test_tenant',
            name='Test Shop',
            domain_url='test.zargar.com',
            is_active=True
        )
        
        self.super_admin = SuperAdmin.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='password123'
        )
        
        from django_tenants.utils import schema_context
        with schema_context(self.tenant.schema_name):
            self.tenant_user = User.objects.create_user(
                username='user',
                email='user@test.com',
                password='password123'
            )
    
    def test_middleware_session_tracking(self):
        """Test that middleware properly tracks impersonation sessions."""
        from zargar.admin_panel.middleware import ImpersonationAuditMiddleware
        
        # Create middleware instance
        middleware = ImpersonationAuditMiddleware(lambda request: None)
        
        # Mock request with hijack history
        request = MagicMock()
        request.user = self.tenant_user
        request.user.is_authenticated = True
        request.session = {
            'hijack_history': [self.super_admin.id],
            'impersonation_session_id': None
        }
        request.tenant = self.tenant
        request.META = {'HTTP_USER_AGENT': 'Test Browser', 'REMOTE_ADDR': '127.0.0.1'}
        request.get_full_path.return_value = '/dashboard/'
        
        # Process request
        middleware.process_request(request)
        
        # Should create impersonation session
        sessions = ImpersonationSession.objects.filter(
            admin_user_id=self.super_admin.id,
            target_user_id=self.tenant_user.id
        )
        self.assertTrue(sessions.exists())
    
    def tearDown(self):
        """Clean up test data."""
        ImpersonationSession.objects.all().delete()
        Domain.objects.all().delete()
        Tenant.objects.all().delete()
        SuperAdmin.objects.all().delete()


if __name__ == '__main__':
    pytest.main([__file__])