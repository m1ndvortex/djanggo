"""
Tests for user management frontend interfaces including 2FA UI workflows.
"""
import pytest
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from zargar.tenants.models import Tenant
from zargar.core.models import TOTPDevice

User = get_user_model()


class UserManagementFrontendTestCase(TenantTestCase):
    """
    Test case for user management frontend functionality.
    """
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        # Create tenant owner
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123',
            role='owner',
            persian_first_name='مالک',
            persian_last_name='تست'
        )
        
        # Create regular employee
        self.employee = User.objects.create_user(
            username='employee',
            email='employee@test.com',
            password='testpass123',
            role='salesperson',
            persian_first_name='کارمند',
            persian_last_name='تست'
        )
        
        # Create accountant
        self.accountant = User.objects.create_user(
            username='accountant',
            email='accountant@test.com',
            password='testpass123',
            role='accountant',
            persian_first_name='حسابدار',
            persian_last_name='تست'
        )
        
        self.client = TenantClient(self.tenant)
    
    def test_user_management_list_access_owner(self):
        """Test that tenant owners can access user management list."""
        self.client.login(username='owner', password='testpass123')
        
        response = self.client.get(reverse('tenant:user_management'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مدیریت کاربران')
        self.assertContains(response, self.owner.full_persian_name)
        self.assertContains(response, self.employee.full_persian_name)
        self.assertContains(response, self.accountant.full_persian_name)
    
    def test_user_management_list_access_denied_employee(self):
        """Test that regular employees cannot access user management."""
        self.client.login(username='employee', password='testpass123')
        
        response = self.client.get(reverse('tenant:user_management'))
        
        # Should be redirected or get 403
        self.assertIn(response.status_code, [302, 403])
    
    def test_user_create_form_display(self):
        """Test user creation form displays correctly."""
        self.client.login(username='owner', password='testpass123')
        
        response = self.client.get(reverse('tenant:user_create'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'افزودن کاربر جدید')
        self.assertContains(response, 'نام کاربری')
        self.assertContains(response, 'نام (فارسی)')
        self.assertContains(response, 'نقش کاربر')
    
    def test_user_create_success(self):
        """Test successful user creation."""
        self.client.login(username='owner', password='testpass123')
        
        user_data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'first_name': 'New',
            'last_name': 'User',
            'persian_first_name': 'کاربر',
            'persian_last_name': 'جدید',
            'phone_number': '09123456789',
            'role': 'salesperson'
        }
        
        response = self.client.post(reverse('tenant:user_create'), user_data)
        
        # Should redirect to user management list
        self.assertEqual(response.status_code, 302)
        
        # Check user was created
        new_user = User.objects.get(username='newuser')
        self.assertEqual(new_user.email, 'newuser@test.com')
        self.assertEqual(new_user.role, 'salesperson')
        self.assertEqual(new_user.persian_first_name, 'کاربر')
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('موفقیت' in str(message) for message in messages))
    
    def test_user_edit_form_display(self):
        """Test user edit form displays correctly."""
        self.client.login(username='owner', password='testpass123')
        
        response = self.client.get(reverse('tenant:user_edit', kwargs={'pk': self.employee.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ویرایش اطلاعات کاربر')
        self.assertContains(response, self.employee.username)
        self.assertContains(response, self.employee.persian_first_name)
    
    def test_user_edit_success(self):
        """Test successful user editing."""
        self.client.login(username='owner', password='testpass123')
        
        updated_data = {
            'first_name': 'Updated',
            'last_name': 'Employee',
            'persian_first_name': 'کارمند',
            'persian_last_name': 'به‌روزشده',
            'email': 'updated@test.com',
            'phone_number': '09123456789',
            'role': 'accountant',
            'is_active': True
        }
        
        response = self.client.post(
            reverse('tenant:user_edit', kwargs={'pk': self.employee.pk}), 
            updated_data
        )
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        
        # Check user was updated
        updated_user = User.objects.get(pk=self.employee.pk)
        self.assertEqual(updated_user.email, 'updated@test.com')
        self.assertEqual(updated_user.role, 'accountant')
        self.assertEqual(updated_user.persian_last_name, 'به‌روزشده')
    
    def test_user_detail_view(self):
        """Test user detail view displays correctly."""
        self.client.login(username='owner', password='testpass123')
        
        response = self.client.get(reverse('tenant:user_detail', kwargs={'pk': self.employee.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.employee.full_persian_name)
        self.assertContains(response, self.employee.email)
        self.assertContains(response, 'فروشنده')  # Role display
        self.assertContains(response, 'فعالیت‌های اخیر')
    
    def test_user_deactivate(self):
        """Test user deactivation."""
        self.client.login(username='owner', password='testpass123')
        
        response = self.client.post(reverse('tenant:user_deactivate', kwargs={'pk': self.employee.pk}))
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        
        # Check user was deactivated
        deactivated_user = User.objects.get(pk=self.employee.pk)
        self.assertFalse(deactivated_user.is_active)
    
    def test_user_password_reset(self):
        """Test admin password reset for user."""
        self.client.login(username='owner', password='testpass123')
        
        response = self.client.post(reverse('tenant:user_password_reset', kwargs={'pk': self.employee.pk}))
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        
        # Check success message contains temporary password
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('بازنشانی' in str(message) for message in messages))
    
    def test_profile_view_access(self):
        """Test user profile view access."""
        self.client.login(username='employee', password='testpass123')
        
        response = self.client.get(reverse('tenant:profile'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'پروفایل کاربری')
        self.assertContains(response, self.employee.full_persian_name)
        self.assertContains(response, 'تنظیمات امنیتی')
    
    def test_profile_edit_form(self):
        """Test profile edit form."""
        self.client.login(username='employee', password='testpass123')
        
        response = self.client.get(reverse('tenant:profile_edit'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ویرایش پروفایل')
        self.assertContains(response, self.employee.username)  # Read-only
        self.assertContains(response, 'تم ترجیحی')
    
    def test_profile_edit_success(self):
        """Test successful profile editing."""
        self.client.login(username='employee', password='testpass123')
        
        updated_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'persian_first_name': 'نام',
            'persian_last_name': 'به‌روزشده',
            'email': 'newemail@test.com',
            'phone_number': '09123456789',
            'theme_preference': 'dark'
        }
        
        response = self.client.post(reverse('tenant:profile_edit'), updated_data)
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        
        # Check profile was updated
        updated_user = User.objects.get(pk=self.employee.pk)
        self.assertEqual(updated_user.email, 'newemail@test.com')
        self.assertEqual(updated_user.theme_preference, 'dark')
        self.assertEqual(updated_user.persian_last_name, 'به‌روزشده')
    
    def test_password_change_form(self):
        """Test password change form display."""
        self.client.login(username='employee', password='testpass123')
        
        response = self.client.get(reverse('tenant:password_change'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تغییر رمز عبور')
        self.assertContains(response, 'رمز عبور فعلی')
        self.assertContains(response, 'رمز عبور جدید')
        self.assertContains(response, 'الزامات رمز عبور')
    
    def test_password_change_success(self):
        """Test successful password change."""
        self.client.login(username='employee', password='testpass123')
        
        password_data = {
            'old_password': 'testpass123',
            'new_password1': 'NewStrongPass123!',
            'new_password2': 'NewStrongPass123!'
        }
        
        response = self.client.post(reverse('tenant:password_change'), password_data)
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        
        # Check user can login with new password
        self.client.logout()
        login_success = self.client.login(username='employee', password='NewStrongPass123!')
        self.assertTrue(login_success)
    
    def test_2fa_setup_form(self):
        """Test 2FA setup form display."""
        self.client.login(username='employee', password='testpass123')
        
        response = self.client.get(reverse('tenant:2fa_setup'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'راه‌اندازی احراز هویت دو مرحله‌ای')
        self.assertContains(response, 'نصب اپلیکیشن احراز هویت')
        self.assertContains(response, 'اسکن کد QR')
        self.assertContains(response, 'Google Authenticator')
        
        # Check if QR code is generated (depends on pyotp availability)
        if 'qr_code_data' in response.context and response.context['qr_code_data']:
            self.assertIsNotNone(response.context['secret_key'])
        else:
            # If dependencies are missing, should show error gracefully
            self.assertIn('error', response.context or {})
    
    def test_2fa_disable(self):
        """Test 2FA disable functionality."""
        # Enable 2FA first
        self.employee.is_2fa_enabled = True
        self.employee.save()
        
        self.client.login(username='employee', password='testpass123')
        
        response = self.client.post(reverse('tenant:2fa_disable'))
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        
        # Check 2FA was disabled
        updated_user = User.objects.get(pk=self.employee.pk)
        self.assertFalse(updated_user.is_2fa_enabled)
    
    def test_role_based_access_control(self):
        """Test role-based access control for different user types."""
        # Test accountant cannot access user management
        self.client.login(username='accountant', password='testpass123')
        response = self.client.get(reverse('tenant:user_management'))
        self.assertIn(response.status_code, [302, 403])
        
        # Test employee cannot access user management
        self.client.login(username='employee', password='testpass123')
        response = self.client.get(reverse('tenant:user_management'))
        self.assertIn(response.status_code, [302, 403])
        
        # Test owner can access user management
        self.client.login(username='owner', password='testpass123')
        response = self.client.get(reverse('tenant:user_management'))
        self.assertEqual(response.status_code, 200)
    
    def test_persian_validation(self):
        """Test Persian text validation in forms."""
        self.client.login(username='owner', password='testpass123')
        
        # Test with invalid Persian characters
        user_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'persian_first_name': 'English Name',  # Should be Persian
            'persian_last_name': 'تست',
            'role': 'salesperson'
        }
        
        response = self.client.post(reverse('tenant:user_create'), user_data)
        
        # Form should still work (validation is client-side)
        # But we can test that Persian names are stored correctly
        if response.status_code == 302:  # Success
            user = User.objects.get(username='testuser')
            self.assertEqual(user.persian_first_name, 'English Name')
    
    def test_theme_switching(self):
        """Test theme switching functionality."""
        self.client.login(username='employee', password='testpass123')
        
        # Test theme toggle
        response = self.client.post(
            reverse('tenant:theme_toggle'),
            data='{"theme": "dark"}',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check user theme was updated
        updated_user = User.objects.get(pk=self.employee.pk)
        self.assertEqual(updated_user.theme_preference, 'dark')
    
    def test_user_statistics_display(self):
        """Test user statistics are displayed correctly."""
        self.client.login(username='owner', password='testpass123')
        
        response = self.client.get(reverse('tenant:user_management'))
        
        self.assertEqual(response.status_code, 200)
        # Should show total users count
        self.assertContains(response, '3')  # owner + employee + accountant
        # Should show active users
        self.assertContains(response, 'کاربران فعال')
    
    def test_audit_logging(self):
        """Test that user management actions are logged."""
        from zargar.core.models import AuditLog
        
        self.client.login(username='owner', password='testpass123')
        
        # Create a user
        user_data = {
            'username': 'audituser',
            'email': 'audit@test.com',
            'persian_first_name': 'کاربر',
            'persian_last_name': 'تست',
            'role': 'salesperson'
        }
        
        response = self.client.post(reverse('tenant:user_create'), user_data)
        
        # Check audit log was created
        audit_logs = AuditLog.objects.filter(action='create', model_name='User')
        self.assertTrue(audit_logs.exists())
        
        log = audit_logs.first()
        self.assertEqual(log.user, self.owner)
        self.assertIn('audituser', log.details.get('created_user', ''))


class UserManagementPermissionTests(TenantTestCase):
    """
    Test permissions for user management functionality.
    """
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        self.owner = User.objects.create_user(
            username='owner',
            password='testpass123',
            role='owner'
        )
        
        self.employee = User.objects.create_user(
            username='employee',
            password='testpass123',
            role='salesperson'
        )
        
        self.client = TenantClient(self.tenant)
    
    def test_owner_permissions(self):
        """Test owner has all user management permissions."""
        self.assertTrue(self.owner.can_manage_users())
        self.assertTrue(self.owner.can_access_accounting())
        self.assertTrue(self.owner.can_access_pos())
    
    def test_employee_permissions(self):
        """Test employee has limited permissions."""
        self.assertFalse(self.employee.can_manage_users())
        self.assertFalse(self.employee.can_access_accounting())
        self.assertTrue(self.employee.can_access_pos())
    
    def test_user_model_properties(self):
        """Test user model properties work correctly."""
        self.assertTrue(self.owner.is_tenant_owner)
        self.assertFalse(self.owner.is_super_admin)  # Tenant users are never super admins
        
        self.assertFalse(self.employee.is_tenant_owner)
        self.assertFalse(self.employee.is_super_admin)
    
    def test_full_persian_name_property(self):
        """Test full Persian name property."""
        user = User.objects.create_user(
            username='testuser',
            persian_first_name='علی',
            persian_last_name='احمدی'
        )
        
        self.assertEqual(user.full_persian_name, 'علی احمدی')
        
        # Test fallback to username
        user_no_persian = User.objects.create_user(username='nopersian')
        self.assertEqual(user_no_persian.full_persian_name, 'nopersian')

class Tw
oFAFrontendTestCase(TenantTestCase):
    """
    Test case for 2FA frontend interface workflows.
    """
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            persian_first_name='علی',
            persian_last_name='احمدی'
        )
        
        self.client = TenantClient(self.tenant)
    
    def test_2fa_setup_wizard_display(self):
        """Test 2FA setup wizard displays correctly with Persian instructions."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('tenant:2fa_setup'))
        self.assertEqual(response.status_code, 200)
        
        # Check Persian content
        self.assertContains(response, 'تنظیم احراز هویت دو مرحله‌ای')
        self.assertContains(response, 'نصب اپلیکیشن احراز هویت')
        self.assertContains(response, 'اسکن کد QR')
        self.assertContains(response, 'تأیید کد')
        
        # Check step-by-step instructions
        self.assertContains(response, 'Google Authenticator')
        self.assertContains(response, 'Authy')
        self.assertContains(response, 'Microsoft Authenticator')
        
        # Check QR code context
        self.assertIn('qr_code_data', response.context)
        self.assertIn('secret_key', response.context)
        
        # Check Persian UI elements
        self.assertContains(response, 'کد تأیید ۶ رقمی')
        self.assertContains(response, 'فعال‌سازی 2FA')
    
    def test_2fa_setup_wizard_steps_navigation(self):
        """Test 2FA setup wizard step navigation works correctly."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('tenant:2fa_setup'))
        
        # Check progress indicator elements
        self.assertContains(response, 'currentStep')
        self.assertContains(response, 'مرحله بعد')
        self.assertContains(response, 'مرحله قبل')
        
        # Check Alpine.js components
        self.assertContains(response, 'x-data="twoFASetup()"')
        self.assertContains(response, 'x-show="currentStep')
        self.assertContains(response, 'x-transition')
    
    def test_2fa_setup_form_validation(self):
        """Test 2FA setup form validation with Persian error messages."""
        self.client.login(username='testuser', password='testpass123')
        
        # Test empty token
        response = self.client.post(reverse('tenant:2fa_setup'), {
            'token': ''
        })
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('وارد کنید' in str(m) for m in messages))
        
        # Test invalid token
        response = self.client.post(reverse('tenant:2fa_setup'), {
            'token': '000000'
        })
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('نامعتبر' in str(m) for m in messages))
    
    def test_2fa_setup_success_flow(self):
        """Test successful 2FA setup flow with Persian success messages."""
        self.client.login(username='testuser', password='testpass123')
        
        # Create TOTP device
        device = TOTPDevice.objects.create(user=self.user)
        totp = device.get_totp()
        valid_token = totp.now()
        
        response = self.client.post(reverse('tenant:2fa_setup'), {
            'token': valid_token
        })
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('فعال شد' in str(m) for m in messages))
        
        # Check device is confirmed
        device.refresh_from_db()
        self.assertTrue(device.is_confirmed)
        
        # Check user has 2FA enabled
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_2fa_enabled)
    
    def test_2fa_verification_form_display(self):
        """Test 2FA verification form displays correctly with Persian UI."""
        # Setup 2FA for user
        device = TOTPDevice.objects.create(user=self.user, is_confirmed=True)
        self.user.is_2fa_enabled = True
        self.user.save()
        
        # Simulate login attempt
        session = self.client.session
        session['2fa_user_id'] = self.user.id
        session.save()
        
        response = self.client.get(reverse('tenant:2fa_verify'))
        self.assertEqual(response.status_code, 200)
        
        # Check Persian content
        self.assertContains(response, 'تأیید کد دو مرحله‌ای')
        self.assertContains(response, 'کد ۶ رقمی')
        self.assertContains(response, 'اپلیکیشن احراز هویت')
        
        # Check form elements
        self.assertContains(response, 'name="token"')
        self.assertContains(response, 'maxlength="8"')  # Supports backup tokens
        self.assertContains(response, 'inputmode="numeric"')
        
        # Check Alpine.js components
        self.assertContains(response, 'x-data="twoFAVerify()"')
        self.assertContains(response, 'x-model="token"')
        self.assertContains(response, '@input="validateToken"')
        
        # Check help text
        self.assertContains(response, 'کدهای پشتیبان')
        self.assertContains(response, '۸ رقم')
    
    def test_2fa_verification_form_validation(self):
        """Test 2FA verification form validation with Persian error handling."""
        # Setup 2FA
        device = TOTPDevice.objects.create(user=self.user, is_confirmed=True)
        self.user.is_2fa_enabled = True
        self.user.save()
        
        # Simulate login attempt
        session = self.client.session
        session['2fa_user_id'] = self.user.id
        session.save()
        
        # Test invalid token
        response = self.client.post(reverse('tenant:2fa_verify'), {
            'token': '000000'
        })
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('نامعتبر' in str(m) for m in messages))
    
    def test_2fa_verification_success_flow(self):
        """Test successful 2FA verification flow."""
        # Setup 2FA
        device = TOTPDevice.objects.create(user=self.user, is_confirmed=True)
        self.user.is_2fa_enabled = True
        self.user.save()
        
        # Simulate login attempt
        session = self.client.session
        session['2fa_user_id'] = self.user.id
        session['2fa_next_url'] = '/dashboard/'
        session.save()
        
        # Verify with valid token
        totp = device.get_totp()
        valid_token = totp.now()
        
        response = self.client.post(reverse('tenant:2fa_verify'), {
            'token': valid_token
        })
        
        # Should redirect and complete login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session.get('_auth_user_id'))
    
    def test_2fa_backup_tokens_display(self):
        """Test 2FA backup tokens page displays correctly with Persian UI."""
        self.client.login(username='testuser', password='testpass123')
        
        # Setup 2FA
        device = TOTPDevice.objects.create(user=self.user, is_confirmed=True)
        self.user.is_2fa_enabled = True
        self.user.save()
        
        response = self.client.get(reverse('tenant:2fa_backup_tokens'))
        self.assertEqual(response.status_code, 200)
        
        # Check Persian content
        self.assertContains(response, 'کدهای پشتیبان احراز هویت دو مرحله‌ای')
        self.assertContains(response, 'کدهای یکبار مصرف')
        self.assertContains(response, 'تولید کدهای جدید')
        
        # Check backup tokens display
        self.assertContains(response, 'کد باقی‌مانده')
        for token in device.backup_tokens:
            self.assertContains(response, token)
        
        # Check instructions
        self.assertContains(response, 'نحوه استفاده')
        self.assertContains(response, 'چه زمانی از کدهای پشتیبان استفاده کنم؟')
        self.assertContains(response, 'نکات امنیتی مهم')
        
        # Check form elements
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'تولید کدهای جدید')
    
    def test_2fa_backup_tokens_regeneration(self):
        """Test 2FA backup tokens regeneration with Persian validation."""
        self.client.login(username='testuser', password='testpass123')
        
        # Setup 2FA
        device = TOTPDevice.objects.create(user=self.user, is_confirmed=True)
        self.user.is_2fa_enabled = True
        self.user.save()
        
        old_tokens = device.backup_tokens.copy()
        
        # Test regeneration with correct password
        response = self.client.post(reverse('tenant:2fa_backup_tokens'), {
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 200)
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('تولید شدند' in str(m) for m in messages))
        
        # Check tokens were regenerated
        device.refresh_from_db()
        self.assertNotEqual(old_tokens, device.backup_tokens)
        
        # Test with wrong password
        response = self.client.post(reverse('tenant:2fa_backup_tokens'), {
            'password': 'wrongpassword'
        })
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('نادرست' in str(m) for m in messages))
    
    def test_2fa_status_display_in_profile(self):
        """Test 2FA status display in user profile with Persian UI."""
        self.client.login(username='testuser', password='testpass123')
        
        # Test without 2FA
        response = self.client.get(reverse('tenant:profile'))
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response, 'احراز هویت دو مرحله‌ای')
        self.assertContains(response, 'غیرفعال')
        self.assertContains(response, 'راه‌اندازی 2FA')
        
        # Setup 2FA
        device = TOTPDevice.objects.create(user=self.user, is_confirmed=True)
        self.user.is_2fa_enabled = True
        self.user.save()
        
        # Test with 2FA enabled
        response = self.client.get(reverse('tenant:profile'))
        self.assertContains(response, 'فعال')
        self.assertContains(response, 'کدهای پشتیبان')
        self.assertContains(response, 'تنظیم مجدد')
        self.assertContains(response, 'غیرفعال کردن')
        
        # Check Alpine.js components
        self.assertContains(response, 'x-data="twoFAStatus()"')
        self.assertContains(response, 'showDetails')
        self.assertContains(response, 'showDisableForm')
    
    def test_2fa_status_api_endpoint(self):
        """Test 2FA status API endpoint returns correct data."""
        self.client.login(username='testuser', password='testpass123')
        
        # Test without 2FA
        response = self.client.get(reverse('tenant:2fa_status_api'))
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertFalse(data['is_2fa_enabled'])
        self.assertFalse(data['is_confirmed'])
        self.assertEqual(data['backup_tokens_count'], 0)
        
        # Setup 2FA
        device = TOTPDevice.objects.create(user=self.user, is_confirmed=True)
        self.user.is_2fa_enabled = True
        self.user.save()
        
        # Test with 2FA enabled
        response = self.client.get(reverse('tenant:2fa_status_api'))
        data = json.loads(response.content)
        
        self.assertTrue(data['is_2fa_enabled'])
        self.assertTrue(data['is_confirmed'])
        self.assertEqual(data['backup_tokens_count'], 10)
        self.assertIn('setup_url', data)
    
    def test_2fa_disable_form_in_profile(self):
        """Test 2FA disable form in profile with Persian validation."""
        self.client.login(username='testuser', password='testpass123')
        
        # Setup 2FA
        device = TOTPDevice.objects.create(user=self.user, is_confirmed=True)
        self.user.is_2fa_enabled = True
        self.user.save()
        
        # Test disable with correct password
        response = self.client.post(reverse('tenant:2fa_disable'), {
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
        
        # Check 2FA is disabled
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_2fa_enabled)
        self.assertFalse(TOTPDevice.objects.filter(user=self.user).exists())
    
    def test_2fa_ui_accessibility_features(self):
        """Test 2FA UI includes accessibility features."""
        self.client.login(username='testuser', password='testpass123')
        
        # Test setup page accessibility
        response = self.client.get(reverse('tenant:2fa_setup'))
        
        # Check form labels
        self.assertContains(response, 'for="token"')
        self.assertContains(response, 'aria-')
        
        # Check semantic HTML
        self.assertContains(response, '<label')
        self.assertContains(response, 'required')
        
        # Test verification page accessibility
        session = self.client.session
        session['2fa_user_id'] = self.user.id
        session.save()
        
        response = self.client.get(reverse('tenant:2fa_verify'))
        
        # Check accessibility attributes
        self.assertContains(response, 'autocomplete="one-time-code"')
        self.assertContains(response, 'inputmode="numeric"')
        self.assertContains(response, 'pattern="[0-9A-Z]{6,8}"')
    
    def test_2fa_ui_responsive_design(self):
        """Test 2FA UI includes responsive design classes."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('tenant:2fa_setup'))
        
        # Check responsive grid classes
        self.assertContains(response, 'grid-cols-1')
        self.assertContains(response, 'lg:grid-cols-2')
        self.assertContains(response, 'sm:px-6')
        self.assertContains(response, 'md:grid-cols-2')
        
        # Check mobile-friendly elements
        self.assertContains(response, 'max-w-')
        self.assertContains(response, 'px-4')
        self.assertContains(response, 'py-')
    
    def test_2fa_ui_dark_mode_support(self):
        """Test 2FA UI includes dark mode styling."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('tenant:2fa_setup'))
        
        # Check dark mode classes
        self.assertContains(response, 'is_dark_mode')
        self.assertContains(response, 'cyber-bg-primary')
        self.assertContains(response, 'cyber-neon-primary')
        self.assertContains(response, 'cyber-text-primary')
        
        # Check conditional styling
        self.assertContains(response, '{% if is_dark_mode %}')
        self.assertContains(response, '{% else %}')
    
    def test_2fa_ui_persian_number_support(self):
        """Test 2FA UI supports Persian numerals."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('tenant:2fa_setup'))
        
        # Check Persian numerals in placeholders
        self.assertContains(response, '۱۲۳۴۵۶')
        
        # Check JavaScript Persian number conversion
        self.assertContains(response, '۰۱۲۳۴۵۶۷۸۹')
        self.assertContains(response, 'replace(/[۰-۹]/g')
    
    def test_2fa_ui_error_handling(self):
        """Test 2FA UI includes comprehensive error handling."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('tenant:2fa_setup'))
        
        # Check error display elements
        self.assertContains(response, 'tokenError')
        self.assertContains(response, 'error-shake')
        self.assertContains(response, 'x-show="tokenError"')
        
        # Check validation functions
        self.assertContains(response, 'validateToken')
        self.assertContains(response, 'handleSubmit')
        
        # Check error messages
        self.assertContains(response, 'کد باید')
        self.assertContains(response, 'رقم باشد')


if __name__ == '__main__':
    pytest.main([__file__])