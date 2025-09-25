"""
Tests for security policy frontend functionality.
"""
import json
import django
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

# Setup Django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
django.setup()

from zargar.tenants.admin_models import SuperAdmin
from zargar.admin_panel.models import SecurityPolicy

User = get_user_model()


class SecurityPolicyFrontendTest(TestCase):
    """Test security policy frontend views and functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create superadmin user
        self.superadmin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
        
        # Login as superadmin
        self.client.force_login(self.superadmin)
        
        # Create test security policies
        self.password_policy = SecurityPolicy.objects.create(
            name='Test Password Policy',
            policy_type='password',
            is_active=True,
            configuration={
                'min_length': 8,
                'require_uppercase': True,
                'require_lowercase': True,
                'require_numbers': True,
                'require_special_chars': True,
                'max_age_days': 90,
                'prevent_reuse_count': 5,
                'special_chars': '!@#$%^&*()_+-=[]{}|;:,.<>?',
            },
            created_by_id=self.superadmin.id,
            created_by_username=self.superadmin.username
        )
        
        self.session_policy = SecurityPolicy.objects.create(
            name='Test Session Policy',
            policy_type='session',
            is_active=True,
            configuration={
                'timeout_minutes': 480,
                'max_concurrent_sessions': 3,
                'require_reauth_for_sensitive': True,
                'extend_on_activity': True,
                'secure_cookies': True,
            },
            created_by_id=self.superadmin.id,
            created_by_username=self.superadmin.username
        )
    
    def test_security_policy_management_view_access(self):
        """Test access to security policy management view."""
        url = reverse('admin_panel:security_policies')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'سیاست‌های امنیتی')
        self.assertContains(response, 'مدیریت و پیکربندی سیاست‌های امنیتی سیستم')
    
    def test_security_policy_management_view_context(self):
        """Test security policy management view context data."""
        url = reverse('admin_panel:security_policies')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check context data
        context = response.context
        self.assertIn('policies_by_type', context)
        self.assertIn('total_policies', context)
        self.assertIn('active_policies', context)
        
        # Check policies by type
        policies_by_type = context['policies_by_type']
        self.assertIn('password', policies_by_type)
        self.assertIn('session', policies_by_type)
        self.assertIn('rate_limit', policies_by_type)
        self.assertIn('authentication', policies_by_type)
        
        # Check password policy data
        password_data = policies_by_type['password']
        self.assertEqual(password_data['active_policy'].id, self.password_policy.id)
        self.assertEqual(password_data['current_config']['min_length'], 8)
    
    def test_security_policy_update_view_success(self):
        """Test successful security policy update."""
        url = reverse('admin_panel:security_policy_update')
        
        new_config = {
            'min_length': 12,
            'require_uppercase': True,
            'require_lowercase': True,
            'require_numbers': True,
            'require_special_chars': True,
            'max_age_days': 60,
            'prevent_reuse_count': 10,
            'special_chars': '!@#$%^&*()_+-=[]{}|;:,.<>?',
        }
        
        data = {
            'policy_type': 'password',
            'configuration': new_config,
            'reason': 'Test update'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('سیاست', response_data['message'])
        
        # Check that old policy is deactivated and new one is created
        self.password_policy.refresh_from_db()
        self.assertFalse(self.password_policy.is_active)
        
        new_policy = SecurityPolicy.objects.filter(
            policy_type='password',
            is_active=True
        ).first()
        self.assertIsNotNone(new_policy)
        self.assertEqual(new_policy.configuration['min_length'], 12)
        self.assertEqual(new_policy.configuration['max_age_days'], 60)
    
    def test_security_policy_update_view_validation_error(self):
        """Test security policy update with validation error."""
        url = reverse('admin_panel:security_policy_update')
        
        # Invalid configuration (missing required fields)
        invalid_config = {
            'min_length': 8,
            # Missing required fields
        }
        
        data = {
            'policy_type': 'password',
            'configuration': invalid_config,
            'reason': 'Test invalid update'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('خطای اعتبارسنجی', response_data['error'])
    
    def test_security_policy_update_view_invalid_policy_type(self):
        """Test security policy update with invalid policy type."""
        url = reverse('admin_panel:security_policy_update')
        
        data = {
            'policy_type': 'invalid_type',
            'configuration': {},
            'reason': 'Test invalid type'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('نوع سیاست نامعتبر', response_data['error'])
    
    def test_security_policy_reset_view_success(self):
        """Test successful security policy reset."""
        url = reverse('admin_panel:security_policy_reset')
        
        data = {
            'policy_type': 'password',
            'reason': 'Test reset'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('بازگردانده شد', response_data['message'])
        self.assertIn('default_config', response_data)
        
        # Check that old policy is deactivated
        self.password_policy.refresh_from_db()
        self.assertFalse(self.password_policy.is_active)
        
        # Check that new default policy is created
        new_policy = SecurityPolicy.objects.filter(
            policy_type='password',
            is_active=True
        ).first()
        self.assertIsNotNone(new_policy)
        self.assertIn('Default', new_policy.name)
    
    def test_security_policy_validate_view_success(self):
        """Test successful security policy validation."""
        url = reverse('admin_panel:security_policy_validate')
        
        valid_config = {
            'min_length': 10,
            'require_uppercase': True,
            'require_lowercase': True,
            'require_numbers': True,
            'require_special_chars': True,
            'max_age_days': 120,
            'prevent_reuse_count': 8,
            'special_chars': '!@#$%^&*()_+-=[]{}|;:,.<>?',
        }
        
        data = {
            'policy_type': 'password',
            'configuration': valid_config
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('معتبر است', response_data['message'])
    
    def test_security_policy_validate_view_validation_error(self):
        """Test security policy validation with validation error."""
        url = reverse('admin_panel:security_policy_validate')
        
        # Invalid configuration (password length too long)
        invalid_config = {
            'min_length': 200,  # Too long
            'require_uppercase': True,
            'require_lowercase': True,
            'require_numbers': True,
            'require_special_chars': True,
            'max_age_days': 90,
            'prevent_reuse_count': 5,
            'special_chars': '!@#$%^&*()_+-=[]{}|;:,.<>?',
        }
        
        data = {
            'policy_type': 'password',
            'configuration': invalid_config
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('validation_errors', response_data)
    
    def test_security_policy_test_view_password_policy(self):
        """Test security policy testing for password policy."""
        url = reverse('admin_panel:security_policy_test')
        
        config = {
            'min_length': 8,
            'require_uppercase': True,
            'require_lowercase': True,
            'require_numbers': True,
            'require_special_chars': True,
            'max_age_days': 90,
            'prevent_reuse_count': 5,
            'special_chars': '!@#$%^&*()_+-=[]{}|;:,.<>?',
        }
        
        data = {
            'policy_type': 'password',
            'configuration': config,
            'test_data': {
                'passwords': ['password123', 'Password123!', '12345678']
            }
        }
        
        with patch('zargar.admin_panel.security_policy_views.PasswordPolicyService.validate_password') as mock_validate:
            mock_validate.return_value = (True, [])
            
            response = self.client.post(
                url,
                data=json.dumps(data),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('test_results', response_data)
        self.assertEqual(response_data['test_results']['type'], 'password_validation')
    
    def test_security_policy_test_view_session_policy(self):
        """Test security policy testing for session policy."""
        url = reverse('admin_panel:security_policy_test')
        
        config = {
            'timeout_minutes': 480,
            'max_concurrent_sessions': 3,
            'require_reauth_for_sensitive': True,
            'extend_on_activity': True,
            'secure_cookies': True,
        }
        
        data = {
            'policy_type': 'session',
            'configuration': config,
            'test_data': {}
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('test_results', response_data)
        
        test_results = response_data['test_results']
        self.assertEqual(test_results['type'], 'session_configuration')
        self.assertEqual(test_results['timeout_seconds'], 480 * 60)
        self.assertEqual(test_results['max_concurrent_sessions'], 3)
    
    def test_security_policy_history_view(self):
        """Test security policy history view."""
        url = reverse('admin_panel:security_policy_history')
        
        response = self.client.get(url, {'type': 'password', 'limit': 10})
        
        self.assertEqual(response.status_code, 200)
        
        context = response.context
        self.assertIn('policies', context)
        self.assertIn('policy_type', context)
        self.assertEqual(context['policy_type'], 'password')
        
        # Check that our test policy is in the history
        policies = context['policies']
        policy_ids = [p.id for p in policies]
        self.assertIn(self.password_policy.id, policy_ids)
    
    def test_navigation_link_exists(self):
        """Test that security policies navigation link exists."""
        url = reverse('admin_panel:security_policies')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that the page contains navigation elements
        self.assertContains(response, 'سیاست‌های امنیتی')
        self.assertContains(response, 'تنظیمات')
    
    def test_theme_support_in_template(self):
        """Test that the template supports dual theme (light/dark)."""
        url = reverse('admin_panel:security_policies')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check for dark mode classes
        self.assertContains(response, 'dark:bg-cyber-bg-primary')
        self.assertContains(response, 'dark:text-cyber-text-primary')
        self.assertContains(response, 'dark:bg-cyber-bg-secondary')
        
        # Check for cybersecurity styling
        self.assertContains(response, 'cyber-neon-primary')
        self.assertContains(response, 'neon-border')
    
    def test_persian_localization(self):
        """Test Persian localization in the interface."""
        url = reverse('admin_panel:security_policies')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check for Persian text
        self.assertContains(response, 'سیاست‌های امنیتی')
        self.assertContains(response, 'مدیریت و پیکربندی')
        self.assertContains(response, 'حداقل طول')
        self.assertContains(response, 'حروف بزرگ')
        self.assertContains(response, 'الزامی')
        self.assertContains(response, 'اختیاری')
        
        # Check for RTL support
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, 'space-x-reverse')
    
    def test_mobile_responsiveness_classes(self):
        """Test that mobile responsiveness classes are present."""
        url = reverse('admin_panel:security_policies')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check for responsive grid classes
        self.assertContains(response, 'grid-cols-1')
        self.assertContains(response, 'lg:grid-cols-2')
        self.assertContains(response, 'md:grid-cols-2')
        
        # Check for responsive spacing
        self.assertContains(response, 'px-4')
        self.assertContains(response, 'sm:p-0')
    
    def test_unauthorized_access_redirect(self):
        """Test that unauthorized users are redirected."""
        # Logout the superadmin
        self.client.logout()
        
        url = reverse('admin_panel:security_policies')
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_ajax_requests_require_post(self):
        """Test that AJAX endpoints require POST method."""
        urls = [
            'admin_panel:security_policy_update',
            'admin_panel:security_policy_reset',
            'admin_panel:security_policy_validate',
            'admin_panel:security_policy_test',
        ]
        
        for url_name in urls:
            url = reverse(url_name)
            
            # GET should not be allowed
            response = self.client.get(url)
            self.assertEqual(response.status_code, 405)  # Method not allowed
    
    def test_csrf_protection(self):
        """Test CSRF protection on AJAX endpoints."""
        url = reverse('admin_panel:security_policy_update')
        
        # Remove CSRF token
        self.client.logout()
        self.client.force_login(self.superadmin)
        
        data = {
            'policy_type': 'password',
            'configuration': {},
            'reason': 'Test'
        }
        
        # Request without CSRF token should fail
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=''  # Empty CSRF token
        )
        
        # Should return 403 Forbidden due to CSRF failure
        self.assertEqual(response.status_code, 403)


class SecurityPolicyUIInteractionTest(TestCase):
    """Test UI interaction functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create superadmin user
        self.superadmin = SuperAdmin.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True
        )
        
        # Login as superadmin
        self.client.force_login(self.superadmin)
    
    def test_javascript_functions_present(self):
        """Test that required JavaScript functions are present in template."""
        url = reverse('admin_panel:security_policies')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check for Alpine.js data function
        self.assertContains(response, 'securityPolicyManager()')
        
        # Check for key JavaScript functions
        self.assertContains(response, 'editPolicy(')
        self.assertContains(response, 'resetPolicy(')
        self.assertContains(response, 'savePolicy(')
        self.assertContains(response, 'testPolicy(')
        self.assertContains(response, 'confirmAction(')
    
    def test_modal_elements_present(self):
        """Test that modal elements are present in template."""
        url = reverse('admin_panel:security_policies')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check for edit modal
        self.assertContains(response, 'showEditModal')
        self.assertContains(response, 'closeEditModal()')
        
        # Check for confirmation modal
        self.assertContains(response, 'showConfirmModal')
        self.assertContains(response, 'confirmMessage')
        
        # Check for toast notifications
        self.assertContains(response, 'showToast')
        self.assertContains(response, 'toastMessage')
    
    def test_form_validation_elements(self):
        """Test that form validation elements are present."""
        url = reverse('admin_panel:security_policies')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check for input validation attributes
        self.assertContains(response, 'min="4"')
        self.assertContains(response, 'max="128"')
        self.assertContains(response, 'type="number"')
        self.assertContains(response, 'type="checkbox"')
        
        # Check for validation messages
        self.assertContains(response, 'حداقل ۴ و حداکثر ۱۲۸ کاراکتر')
        self.assertContains(response, 'حداقل ۱ و حداکثر ۳۶۵ روز')