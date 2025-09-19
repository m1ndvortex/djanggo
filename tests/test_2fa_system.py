"""
Comprehensive tests for Two-Factor Authentication (2FA) system.
Tests TOTP device enrollment, verification, and management workflows.
"""
import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.utils import timezone
from unittest.mock import patch, MagicMock
import pyotp
import json

from zargar.core.models import TOTPDevice, AuditLog
from zargar.tenants.models import Tenant

User = get_user_model()


class TOTPDeviceModelTest(TestCase):
    """Test TOTP device model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            persian_first_name='علی',
            persian_last_name='احمدی'
        )
    
    def test_totp_device_creation(self):
        """Test TOTP device creation with automatic secret generation."""
        device = TOTPDevice.objects.create(user=self.user)
        
        self.assertEqual(device.user, self.user)
        self.assertIsNotNone(device.secret_key)
        self.assertEqual(len(device.secret_key), 32)  # Base32 secret length
        self.assertFalse(device.is_confirmed)
        self.assertEqual(len(device.backup_tokens), 10)  # Default backup tokens
        self.assertIsNone(device.last_used_at)
    
    def test_totp_device_str_representation(self):
        """Test string representation of TOTP device."""
        device = TOTPDevice.objects.create(user=self.user)
        expected = f"TOTP Device for {self.user.username}"
        self.assertEqual(str(device), expected)
    
    def test_backup_token_generation(self):
        """Test backup token generation."""
        device = TOTPDevice.objects.create(user=self.user)
        
        # Check initial backup tokens
        self.assertEqual(len(device.backup_tokens), 10)
        for token in device.backup_tokens:
            self.assertEqual(len(token), 8)
            self.assertTrue(token.isupper())
            self.assertTrue(token.isalnum())
        
        # Test regeneration
        new_tokens = device.generate_backup_tokens(count=5)
        self.assertEqual(len(new_tokens), 5)
        self.assertNotEqual(new_tokens, device.backup_tokens)
    
    def test_totp_verification(self):
        """Test TOTP token verification."""
        device = TOTPDevice.objects.create(user=self.user)
        totp = device.get_totp()
        
        # Generate valid token
        valid_token = totp.now()
        self.assertTrue(device.verify_token(valid_token))
        self.assertIsNotNone(device.last_used_at)
        
        # Test invalid token
        self.assertFalse(device.verify_token('000000'))
    
    def test_backup_token_verification(self):
        """Test backup token verification."""
        device = TOTPDevice.objects.create(user=self.user)
        backup_token = device.backup_tokens[0]
        
        # Verify backup token
        self.assertTrue(device.verify_token(backup_token))
        self.assertNotIn(backup_token, device.backup_tokens)  # Token should be removed
        self.assertIsNotNone(device.last_used_at)
        
        # Try to use same token again
        self.assertFalse(device.verify_token(backup_token))
    
    def test_device_confirmation(self):
        """Test device confirmation process."""
        device = TOTPDevice.objects.create(user=self.user)
        totp = device.get_totp()
        valid_token = totp.now()
        
        # Confirm device
        self.assertTrue(device.confirm_device(valid_token))
        self.assertTrue(device.is_confirmed)
        
        # User's 2FA should be enabled
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_2fa_enabled)
    
    def test_qr_code_generation(self):
        """Test QR code URL and image generation."""
        device = TOTPDevice.objects.create(user=self.user)
        
        # Test QR code URL
        qr_url = device.get_qr_code_url()
        self.assertIn('otpauth://totp/', qr_url)
        self.assertIn(self.user.username, qr_url)
        self.assertIn('ZARGAR', qr_url)
        
        # Test QR code image
        qr_image = device.get_qr_code_image()
        self.assertTrue(qr_image.startswith('data:image/png;base64,'))
    
    def test_device_deletion_disables_2fa(self):
        """Test that deleting device disables 2FA for user."""
        device = TOTPDevice.objects.create(user=self.user)
        device.is_confirmed = True
        device.save()
        
        # Enable 2FA
        self.user.is_2fa_enabled = True
        self.user.save()
        
        # Delete device
        device.delete()
        
        # Check that 2FA is disabled
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_2fa_enabled)


class TwoFAViewsTest(TestCase):
    """Test 2FA views and workflows."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            persian_first_name='علی',
            persian_last_name='احمدی'
        )
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            persian_first_name='مدیر',
            persian_last_name='سیستم'
        )
    
    def test_2fa_setup_view_get(self):
        """Test 2FA setup view GET request."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('tenant:2fa_setup'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تنظیم احراز هویت دو مرحله‌ای')
        self.assertIn('qr_code_image', response.context)
        self.assertIn('secret_key', response.context)
    
    def test_2fa_setup_confirmation(self):
        """Test 2FA setup confirmation with valid token."""
        self.client.login(username='testuser', password='testpass123')
        
        # Create device
        device = TOTPDevice.objects.create(user=self.user)
        totp = device.get_totp()
        valid_token = totp.now()
        
        # Confirm setup
        response = self.client.post(reverse('tenant:2fa_setup'), {
            'token': valid_token
        })
        
        # Check redirect and success message
        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('فعال شد' in str(m) for m in messages))
        
        # Check device is confirmed
        device.refresh_from_db()
        self.assertTrue(device.is_confirmed)
        
        # Check user has 2FA enabled
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_2fa_enabled)
    
    def test_2fa_setup_invalid_token(self):
        """Test 2FA setup with invalid token."""
        self.client.login(username='testuser', password='testpass123')
        
        # Create device
        TOTPDevice.objects.create(user=self.user)
        
        # Try invalid token
        response = self.client.post(reverse('tenant:2fa_setup'), {
            'token': '000000'
        })
        
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('نامعتبر' in str(m) for m in messages))
    
    def test_2fa_disable_view(self):
        """Test 2FA disable functionality."""
        self.client.login(username='testuser', password='testpass123')
        
        # Setup 2FA
        device = TOTPDevice.objects.create(user=self.user, is_confirmed=True)
        self.user.is_2fa_enabled = True
        self.user.save()
        
        # Disable 2FA
        response = self.client.post(reverse('tenant:2fa_disable'), {
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Check device is deleted
        self.assertFalse(TOTPDevice.objects.filter(user=self.user).exists())
        
        # Check user 2FA is disabled
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_2fa_enabled)
    
    def test_2fa_disable_wrong_password(self):
        """Test 2FA disable with wrong password."""
        self.client.login(username='testuser', password='testpass123')
        
        # Setup 2FA
        TOTPDevice.objects.create(user=self.user, is_confirmed=True)
        self.user.is_2fa_enabled = True
        self.user.save()
        
        # Try to disable with wrong password
        response = self.client.post(reverse('tenant:2fa_disable'), {
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('نادرست' in str(m) for m in messages))
        
        # Check 2FA is still enabled
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_2fa_enabled)
    
    def test_2fa_verification_view(self):
        """Test 2FA verification during login."""
        # Setup 2FA for user
        device = TOTPDevice.objects.create(user=self.user, is_confirmed=True)
        self.user.is_2fa_enabled = True
        self.user.save()
        
        # Simulate login attempt (sets session)
        session = self.client.session
        session['2fa_user_id'] = self.user.id
        session['2fa_next_url'] = '/dashboard/'
        session.save()
        
        # Get verification page
        response = self.client.get(reverse('tenant:2fa_verify'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تأیید کد دو مرحله‌ای')
        
        # Verify with valid token
        totp = device.get_totp()
        valid_token = totp.now()
        
        response = self.client.post(reverse('tenant:2fa_verify'), {
            'token': valid_token
        })
        
        # Should redirect and complete login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session.get('_auth_user_id'))
    
    def test_2fa_verification_invalid_session(self):
        """Test 2FA verification with invalid session."""
        response = self.client.get(reverse('tenant:2fa_verify'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_backup_tokens_view(self):
        """Test backup tokens view and regeneration."""
        self.client.login(username='testuser', password='testpass123')
        
        # Setup 2FA
        device = TOTPDevice.objects.create(user=self.user, is_confirmed=True)
        self.user.is_2fa_enabled = True
        self.user.save()
        
        # View backup tokens
        response = self.client.get(reverse('tenant:2fa_backup_tokens'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'کدهای پشتیبان')
        
        # Regenerate tokens
        old_tokens = device.backup_tokens.copy()
        response = self.client.post(reverse('tenant:2fa_backup_tokens'), {
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, 200)
        device.refresh_from_db()
        self.assertNotEqual(old_tokens, device.backup_tokens)
    
    def test_2fa_status_api(self):
        """Test 2FA status API endpoint."""
        self.client.login(username='testuser', password='testpass123')
        
        # Test without 2FA
        response = self.client.get(reverse('tenant:2fa_status_api'))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['is_2fa_enabled'])
        self.assertFalse(data['is_confirmed'])
        
        # Setup 2FA
        device = TOTPDevice.objects.create(user=self.user, is_confirmed=True)
        self.user.is_2fa_enabled = True
        self.user.save()
        
        # Test with 2FA
        response = self.client.get(reverse('tenant:2fa_status_api'))
        data = json.loads(response.content)
        self.assertTrue(data['is_2fa_enabled'])
        self.assertTrue(data['is_confirmed'])
        self.assertEqual(data['backup_tokens_count'], 10)


class AdminTwoFATest(TestCase):
    """Test admin-specific 2FA functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            persian_first_name='مدیر',
            persian_last_name='سیستم'
        )
    
    def test_admin_login_requires_2fa(self):
        """Test that admin login requires 2FA."""
        # Try to login without 2FA setup
        response = self.client.post(reverse('core:admin_login'), {
            'username': 'admin',
            'password': 'adminpass123'
        })
        
        # Should fail because 2FA is not enabled
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('اجباری' in str(m) for m in messages))
    
    def test_admin_login_with_2fa(self):
        """Test admin login with 2FA enabled."""
        # Setup 2FA for admin
        device = TOTPDevice.objects.create(user=self.superuser, is_confirmed=True)
        self.superuser.is_2fa_enabled = True
        self.superuser.save()
        
        # Login attempt
        response = self.client.post(reverse('core:admin_login'), {
            'username': 'admin',
            'password': 'adminpass123'
        })
        
        # Should redirect to 2FA verification
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session.get('2fa_user_id'))
        self.assertTrue(self.client.session.get('is_admin_login'))
    
    def test_admin_2fa_verification(self):
        """Test admin 2FA verification process."""
        # Setup 2FA
        device = TOTPDevice.objects.create(user=self.superuser, is_confirmed=True)
        self.superuser.is_2fa_enabled = True
        self.superuser.save()
        
        # Simulate admin login attempt
        session = self.client.session
        session['2fa_user_id'] = self.superuser.id
        session['is_admin_login'] = True
        session['2fa_next_url'] = '/admin/dashboard/'
        session.save()
        
        # Verify with valid token
        totp = device.get_totp()
        valid_token = totp.now()
        
        response = self.client.post(reverse('core:admin_2fa_verify'), {
            'token': valid_token
        })
        
        # Should complete login and redirect
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session.get('_auth_user_id'))
        self.assertNotIn('2fa_user_id', self.client.session)


class TwoFAAuditLogTest(TestCase):
    """Test audit logging for 2FA operations."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_2fa_enable_audit_log(self):
        """Test audit logging when 2FA is enabled."""
        self.client.login(username='testuser', password='testpass123')
        
        # Setup and confirm 2FA
        device = TOTPDevice.objects.create(user=self.user)
        totp = device.get_totp()
        valid_token = totp.now()
        
        self.client.post(reverse('tenant:2fa_setup'), {
            'token': valid_token
        })
        
        # Check audit log
        log_entry = AuditLog.objects.filter(
            user=self.user,
            action='2fa_enabled'
        ).first()
        
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.details['device_id'], device.id)
    
    def test_2fa_disable_audit_log(self):
        """Test audit logging when 2FA is disabled."""
        self.client.login(username='testuser', password='testpass123')
        
        # Setup 2FA
        device = TOTPDevice.objects.create(user=self.user, is_confirmed=True)
        self.user.is_2fa_enabled = True
        self.user.save()
        
        # Disable 2FA
        self.client.post(reverse('tenant:2fa_disable'), {
            'password': 'testpass123'
        })
        
        # Check audit log
        log_entry = AuditLog.objects.filter(
            user=self.user,
            action='2fa_disabled'
        ).first()
        
        self.assertIsNotNone(log_entry)
    
    def test_2fa_verification_audit_log(self):
        """Test audit logging for 2FA verification."""
        # Setup 2FA
        device = TOTPDevice.objects.create(user=self.user, is_confirmed=True)
        self.user.is_2fa_enabled = True
        self.user.save()
        
        # Simulate login attempt
        session = self.client.session
        session['2fa_user_id'] = self.user.id
        session.save()
        
        # Verify with valid token
        totp = device.get_totp()
        valid_token = totp.now()
        
        self.client.post(reverse('tenant:2fa_verify'), {
            'token': valid_token
        })
        
        # Check audit log
        log_entry = AuditLog.objects.filter(
            user=self.user,
            action='2fa_verified'
        ).first()
        
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.details['login_type'], 'tenant_portal')
    
    def test_backup_token_usage_audit_log(self):
        """Test audit logging when backup token is used."""
        # Setup 2FA
        device = TOTPDevice.objects.create(user=self.user, is_confirmed=True)
        self.user.is_2fa_enabled = True
        self.user.save()
        
        backup_token = device.backup_tokens[0]
        
        # Simulate login attempt
        session = self.client.session
        session['2fa_user_id'] = self.user.id
        session.save()
        
        # Verify with backup token
        self.client.post(reverse('tenant:2fa_verify'), {
            'token': backup_token
        })
        
        # Check audit logs
        verified_log = AuditLog.objects.filter(
            user=self.user,
            action='2fa_verified'
        ).first()
        
        backup_log = AuditLog.objects.filter(
            user=self.user,
            action='backup_token_used'
        ).first()
        
        self.assertIsNotNone(verified_log)
        self.assertIsNotNone(backup_log)
        self.assertEqual(backup_log.details['remaining_tokens'], 9)


class TwoFAIntegrationTest(TestCase):
    """Integration tests for 2FA system."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_complete_2fa_enrollment_workflow(self):
        """Test complete 2FA enrollment workflow."""
        # Login
        self.client.login(username='testuser', password='testpass123')
        
        # Access 2FA setup
        response = self.client.get(reverse('tenant:2fa_setup'))
        self.assertEqual(response.status_code, 200)
        
        # Get device and generate token
        device = TOTPDevice.objects.get(user=self.user)
        totp = device.get_totp()
        valid_token = totp.now()
        
        # Confirm setup
        response = self.client.post(reverse('tenant:2fa_setup'), {
            'token': valid_token
        })
        
        # Check everything is set up correctly
        device.refresh_from_db()
        self.user.refresh_from_db()
        
        self.assertTrue(device.is_confirmed)
        self.assertTrue(self.user.is_2fa_enabled)
        self.assertEqual(len(device.backup_tokens), 10)
    
    def test_complete_2fa_login_workflow(self):
        """Test complete 2FA login workflow."""
        # Setup 2FA
        device = TOTPDevice.objects.create(user=self.user, is_confirmed=True)
        self.user.is_2fa_enabled = True
        self.user.save()
        
        # Logout to test login
        self.client.logout()
        
        # Login attempt (should redirect to 2FA)
        response = self.client.post(reverse('tenant:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Should redirect to 2FA verification
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session.get('2fa_user_id'))
        
        # Complete 2FA verification
        totp = device.get_totp()
        valid_token = totp.now()
        
        response = self.client.post(reverse('tenant:2fa_verify'), {
            'token': valid_token
        })
        
        # Should be logged in and redirected
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session.get('_auth_user_id'))
    
    def test_2fa_disable_and_reenable_workflow(self):
        """Test disabling and re-enabling 2FA."""
        self.client.login(username='testuser', password='testpass123')
        
        # Enable 2FA
        device = TOTPDevice.objects.create(user=self.user)
        totp = device.get_totp()
        valid_token = totp.now()
        
        self.client.post(reverse('tenant:2fa_setup'), {
            'token': valid_token
        })
        
        # Verify 2FA is enabled
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_2fa_enabled)
        
        # Disable 2FA
        self.client.post(reverse('tenant:2fa_disable'), {
            'password': 'testpass123'
        })
        
        # Verify 2FA is disabled
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_2fa_enabled)
        self.assertFalse(TOTPDevice.objects.filter(user=self.user).exists())
        
        # Re-enable 2FA
        response = self.client.get(reverse('tenant:2fa_setup'))
        self.assertEqual(response.status_code, 200)
        
        # New device should be created
        new_device = TOTPDevice.objects.get(user=self.user)
        self.assertNotEqual(new_device.secret_key, device.secret_key)


if __name__ == '__main__':
    pytest.main([__file__])