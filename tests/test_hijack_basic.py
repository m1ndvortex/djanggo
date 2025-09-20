"""
Basic tests for django-hijack integration.
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
from django.utils import timezone
from unittest.mock import MagicMock
from datetime import timedelta

from zargar.tenants.admin_models import SuperAdmin
from zargar.tenants.models import Tenant, Domain
from zargar.admin_panel.models import ImpersonationSession
from zargar.admin_panel.hijack_permissions import (
    is_super_admin, authorize_hijack, check_hijack_permissions
)
from zargar.core.models import User

User = get_user_model()


@pytest.mark.django_db
class BasicHijackTestCase(TestCase):
    """Test basic hijack functionality."""
    
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
            self.tenant_user = User.objects.create_user(
                username='employee',
                email='employee@test.com',
                password='password123',
                role='salesperson'
            )
    
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
    
    def test_impersonation_session_creation(self):
        """Test creation and management of impersonation sessions."""
        session = ImpersonationSession.objects.create(
            admin_user_id=self.super_admin.id,
            admin_username=self.super_admin.username,
            target_user_id=self.tenant_user.id,
            target_username=self.tenant_user.username,
            tenant_schema=self.tenant.schema_name,
            tenant_domain=self.domain.domain,
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
    
    def test_permission_checks(self):
        """Test comprehensive permission checking."""
        # Test valid hijack
        allowed, reason = check_hijack_permissions(self.super_admin, self.tenant_user)
        self.assertTrue(allowed)
        
        # Test self-hijacking
        allowed, reason = check_hijack_permissions(self.super_admin, self.super_admin)
        self.assertFalse(allowed)
        self.assertIn('yourself', reason)
    
    def test_session_audit_logging(self):
        """Test that sessions are properly logged."""
        session = ImpersonationSession.objects.create(
            admin_user_id=self.super_admin.id,
            admin_username=self.super_admin.username,
            target_user_id=self.tenant_user.id,
            target_username=self.tenant_user.username,
            tenant_schema=self.tenant.schema_name,
            tenant_domain=self.domain.domain,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            status='active'
        )
        
        # Add some actions
        session.add_action('create', 'Created jewelry item', '/jewelry/add/')
        session.add_page_visit('/dashboard/', 'Dashboard')
        
        # Verify logging
        self.assertEqual(len(session.actions_performed), 1)
        self.assertEqual(len(session.pages_visited), 1)
        
        # Check action details
        action = session.actions_performed[0]
        self.assertEqual(action['type'], 'create')
        self.assertEqual(action['description'], 'Created jewelry item')
    
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


if __name__ == '__main__':
    pytest.main([__file__])