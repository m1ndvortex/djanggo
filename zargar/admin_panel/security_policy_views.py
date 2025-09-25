"""
Security Policy management views for super admin panel.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
import json
import logging

from .models import SecurityPolicy
from .security_services import (
    PasswordPolicyService,
    SessionPolicyService,
    RateLimitPolicyService,
    AuthenticationPolicyService
)
from .views import SuperAdminRequiredMixin

logger = logging.getLogger(__name__)


class SecurityPolicyManagementView(SuperAdminRequiredMixin, TemplateView):
    """
    Main security policy management interface.
    """
    template_name = 'admin_panel/settings/security_policies.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all security policies grouped by type
        policies_by_type = {}
        for policy_type, display_name in SecurityPolicy.POLICY_TYPES:
            active_policy = SecurityPolicy.get_active_policy(policy_type)
            policies_by_type[policy_type] = {
                'display_name': display_name,
                'active_policy': active_policy,
                'default_config': self._get_default_config(policy_type),
                'current_config': active_policy.configuration if active_policy else self._get_default_config(policy_type)
            }
        
        # Get policy statistics
        total_policies = SecurityPolicy.objects.count()
        active_policies = SecurityPolicy.objects.filter(is_active=True).count()
        
        context.update({
            'policies_by_type': policies_by_type,
            'total_policies': total_policies,
            'active_policies': active_policies,
            'policy_types': SecurityPolicy.POLICY_TYPES,
        })
        
        return context
    
    def _get_default_config(self, policy_type):
        """Get default configuration for a policy type."""
        if policy_type == 'password':
            return SecurityPolicy.get_password_policy()
        elif policy_type == 'session':
            return SecurityPolicy.get_session_policy()
        elif policy_type == 'rate_limit':
            return SecurityPolicy.get_rate_limit_policy()
        elif policy_type == 'authentication':
            return SecurityPolicy.get_authentication_policy()
        return {}


class SecurityPolicyUpdateView(SuperAdminRequiredMixin, View):
    """
    Handle security policy updates via AJAX.
    """
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            policy_type = data.get('policy_type')
            configuration = data.get('configuration')
            reason = data.get('reason', 'Policy update')
            
            if not policy_type or not configuration:
                return JsonResponse({
                    'success': False,
                    'error': 'نوع سیاست و پیکربندی الزامی است'
                }, status=400)
            
            # Validate policy type
            valid_types = [choice[0] for choice in SecurityPolicy.POLICY_TYPES]
            if policy_type not in valid_types:
                return JsonResponse({
                    'success': False,
                    'error': 'نوع سیاست نامعتبر است'
                }, status=400)
            
            with transaction.atomic():
                # Deactivate existing active policy of this type
                SecurityPolicy.objects.filter(
                    policy_type=policy_type,
                    is_active=True
                ).update(is_active=False)
                
                # Create new active policy
                policy = SecurityPolicy.objects.create(
                    name=f"{dict(SecurityPolicy.POLICY_TYPES)[policy_type]} - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                    policy_type=policy_type,
                    configuration=configuration,
                    description=reason,
                    is_active=True,
                    created_by_id=request.user.id,
                    created_by_username=request.user.username,
                    updated_by_id=request.user.id,
                    updated_by_username=request.user.username
                )
                
                # Validate the policy
                policy.clean()
                policy.save()
            
            # Log the change
            logger.info(f"Security policy {policy_type} updated by {request.user.username}")
            
            return JsonResponse({
                'success': True,
                'message': f'سیاست {dict(SecurityPolicy.POLICY_TYPES)[policy_type]} با موفقیت به‌روزرسانی شد',
                'policy_id': policy.id,
                'requires_restart': self._requires_restart(policy_type),
            })
            
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': f'خطای اعتبارسنجی: {str(e)}'
            }, status=400)
        except Exception as e:
            logger.error(f"Error updating security policy: {e}")
            return JsonResponse({
                'success': False,
                'error': 'خطای غیرمنتظره‌ای رخ داد'
            }, status=500)
    
    def _requires_restart(self, policy_type):
        """Check if policy type requires system restart."""
        restart_required_types = ['session', 'rate_limit']
        return policy_type in restart_required_types


class SecurityPolicyResetView(SuperAdminRequiredMixin, View):
    """
    Reset security policy to default values.
    """
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            policy_type = data.get('policy_type')
            reason = data.get('reason', 'Reset to default')
            
            if not policy_type:
                return JsonResponse({
                    'success': False,
                    'error': 'نوع سیاست الزامی است'
                }, status=400)
            
            # Validate policy type
            valid_types = [choice[0] for choice in SecurityPolicy.POLICY_TYPES]
            if policy_type not in valid_types:
                return JsonResponse({
                    'success': False,
                    'error': 'نوع سیاست نامعتبر است'
                }, status=400)
            
            with transaction.atomic():
                # Deactivate existing active policy of this type
                SecurityPolicy.objects.filter(
                    policy_type=policy_type,
                    is_active=True
                ).update(is_active=False)
                
                # Get default configuration
                if policy_type == 'password':
                    default_config = SecurityPolicy.get_password_policy()
                elif policy_type == 'session':
                    default_config = SecurityPolicy.get_session_policy()
                elif policy_type == 'rate_limit':
                    default_config = SecurityPolicy.get_rate_limit_policy()
                elif policy_type == 'authentication':
                    default_config = SecurityPolicy.get_authentication_policy()
                else:
                    default_config = {}
                
                # Create new policy with default configuration
                policy = SecurityPolicy.objects.create(
                    name=f"{dict(SecurityPolicy.POLICY_TYPES)[policy_type]} - Default - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                    policy_type=policy_type,
                    configuration=default_config,
                    description=f"Reset to default: {reason}",
                    is_active=True,
                    created_by_id=request.user.id,
                    created_by_username=request.user.username,
                    updated_by_id=request.user.id,
                    updated_by_username=request.user.username
                )
            
            # Log the change
            logger.info(f"Security policy {policy_type} reset to default by {request.user.username}")
            
            return JsonResponse({
                'success': True,
                'message': f'سیاست {dict(SecurityPolicy.POLICY_TYPES)[policy_type]} به تنظیمات پیش‌فرض بازگردانده شد',
                'policy_id': policy.id,
                'default_config': default_config,
                'requires_restart': self._requires_restart(policy_type),
            })
            
        except Exception as e:
            logger.error(f"Error resetting security policy: {e}")
            return JsonResponse({
                'success': False,
                'error': 'خطای غیرمنتظره‌ای رخ داد'
            }, status=500)
    
    def _requires_restart(self, policy_type):
        """Check if policy type requires system restart."""
        restart_required_types = ['session', 'rate_limit']
        return policy_type in restart_required_types


class SecurityPolicyValidateView(SuperAdminRequiredMixin, View):
    """
    Validate security policy configuration without saving.
    """
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            policy_type = data.get('policy_type')
            configuration = data.get('configuration')
            
            if not policy_type or not configuration:
                return JsonResponse({
                    'success': False,
                    'error': 'نوع سیاست و پیکربندی الزامی است'
                }, status=400)
            
            # Create temporary policy for validation
            temp_policy = SecurityPolicy(
                name='Temporary',
                policy_type=policy_type,
                configuration=configuration
            )
            
            # Validate the policy
            temp_policy.clean()
            
            # Additional validation based on policy type
            validation_errors = []
            if policy_type == 'password':
                validation_errors = self._validate_password_policy_extra(configuration)
            elif policy_type == 'session':
                validation_errors = self._validate_session_policy_extra(configuration)
            elif policy_type == 'rate_limit':
                validation_errors = self._validate_rate_limit_policy_extra(configuration)
            elif policy_type == 'authentication':
                validation_errors = self._validate_authentication_policy_extra(configuration)
            
            if validation_errors:
                return JsonResponse({
                    'success': False,
                    'error': 'خطاهای اعتبارسنجی',
                    'validation_errors': validation_errors
                }, status=400)
            
            return JsonResponse({
                'success': True,
                'message': 'پیکربندی معتبر است',
            })
            
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': f'خطای اعتبارسنجی: {str(e)}'
            }, status=400)
        except Exception as e:
            logger.error(f"Error validating security policy: {e}")
            return JsonResponse({
                'success': False,
                'error': 'خطای غیرمنتظره‌ای رخ داد'
            }, status=500)
    
    def _validate_password_policy_extra(self, config):
        """Additional validation for password policy."""
        errors = []
        
        # Check password length constraints
        min_length = config.get('min_length', 8)
        if min_length > 128:
            errors.append('حداقل طول رمز عبور نمی‌تواند بیشتر از ۱۲۸ کاراکتر باشد')
        
        # Check max age constraints
        max_age_days = config.get('max_age_days', 90)
        if max_age_days > 365:
            errors.append('حداکثر عمر رمز عبور نمی‌تواند بیشتر از ۳۶۵ روز باشد')
        
        # Check reuse count constraints
        prevent_reuse_count = config.get('prevent_reuse_count', 5)
        if prevent_reuse_count > 50:
            errors.append('تعداد رمزهای عبور قبلی برای جلوگیری از استفاده مجدد نمی‌تواند بیشتر از ۵۰ باشد')
        
        return errors
    
    def _validate_session_policy_extra(self, config):
        """Additional validation for session policy."""
        errors = []
        
        # Check timeout constraints
        timeout_minutes = config.get('timeout_minutes', 480)
        if timeout_minutes > 10080:  # 1 week
            errors.append('مهلت نشست نمی‌تواند بیشتر از یک هفته باشد')
        
        # Check concurrent sessions constraints
        max_concurrent = config.get('max_concurrent_sessions', 3)
        if max_concurrent > 100:
            errors.append('حداکثر نشست‌های همزمان نمی‌تواند بیشتر از ۱۰۰ باشد')
        
        return errors
    
    def _validate_rate_limit_policy_extra(self, config):
        """Additional validation for rate limit policy."""
        errors = []
        
        limits = config.get('limits', {})
        for limit_type, limit_config in limits.items():
            requests = limit_config.get('requests', 0)
            window_minutes = limit_config.get('window_minutes', 0)
            
            if requests > 10000:
                errors.append(f'تعداد درخواست‌های مجاز برای {limit_type} نمی‌تواند بیشتر از ۱۰۰۰۰ باشد')
            
            if window_minutes > 1440:  # 24 hours
                errors.append(f'پنجره زمانی برای {limit_type} نمی‌تواند بیشتر از ۲۴ ساعت باشد')
        
        return errors
    
    def _validate_authentication_policy_extra(self, config):
        """Additional validation for authentication policy."""
        errors = []
        
        # Check lockout attempts constraints
        lockout_attempts = config.get('lockout_attempts', 5)
        if lockout_attempts > 100:
            errors.append('تعداد تلاش‌های ناموفق برای قفل کردن حساب نمی‌تواند بیشتر از ۱۰۰ باشد')
        
        # Check lockout duration constraints
        lockout_duration = config.get('lockout_duration_minutes', 30)
        if lockout_duration > 10080:  # 1 week
            errors.append('مدت زمان قفل شدن حساب نمی‌تواند بیشتر از یک هفته باشد')
        
        return errors


class SecurityPolicyHistoryView(SuperAdminRequiredMixin, TemplateView):
    """
    View security policy change history.
    """
    template_name = 'admin_panel/settings/security_policy_history.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        policy_type = self.request.GET.get('type')
        limit = int(self.request.GET.get('limit', 50))
        
        # Get policy history
        policies = SecurityPolicy.objects.filter(
            policy_type=policy_type
        ).order_by('-created_at')[:limit]
        
        context.update({
            'policies': policies,
            'policy_type': policy_type,
            'policy_type_display': dict(SecurityPolicy.POLICY_TYPES).get(policy_type, policy_type),
            'limit': limit,
        })
        
        return context


class SecurityPolicyTestView(SuperAdminRequiredMixin, View):
    """
    Test security policy configuration.
    """
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            policy_type = data.get('policy_type')
            configuration = data.get('configuration')
            test_data = data.get('test_data', {})
            
            if not policy_type or not configuration:
                return JsonResponse({
                    'success': False,
                    'error': 'نوع سیاست و پیکربندی الزامی است'
                }, status=400)
            
            # Perform policy-specific tests
            test_results = {}
            
            if policy_type == 'password':
                test_results = self._test_password_policy(configuration, test_data)
            elif policy_type == 'session':
                test_results = self._test_session_policy(configuration, test_data)
            elif policy_type == 'rate_limit':
                test_results = self._test_rate_limit_policy(configuration, test_data)
            elif policy_type == 'authentication':
                test_results = self._test_authentication_policy(configuration, test_data)
            
            return JsonResponse({
                'success': True,
                'message': 'تست سیاست با موفقیت انجام شد',
                'test_results': test_results,
            })
            
        except Exception as e:
            logger.error(f"Error testing security policy: {e}")
            return JsonResponse({
                'success': False,
                'error': 'خطای غیرمنتظره‌ای رخ داد'
            }, status=500)
    
    def _test_password_policy(self, config, test_data):
        """Test password policy with sample passwords."""
        test_passwords = test_data.get('passwords', [
            'password123',  # Weak
            'Password123!',  # Strong
            '12345678',  # Numbers only
            'PASSWORD',  # Uppercase only
        ])
        
        results = []
        for password in test_passwords:
            is_valid, errors = PasswordPolicyService.validate_password(password)
            results.append({
                'password': password,
                'is_valid': is_valid,
                'errors': errors
            })
        
        return {
            'type': 'password_validation',
            'results': results
        }
    
    def _test_session_policy(self, config, test_data):
        """Test session policy configuration."""
        timeout_minutes = config.get('timeout_minutes', 480)
        max_concurrent = config.get('max_concurrent_sessions', 3)
        
        return {
            'type': 'session_configuration',
            'timeout_seconds': timeout_minutes * 60,
            'timeout_display': f"{timeout_minutes // 60} ساعت و {timeout_minutes % 60} دقیقه",
            'max_concurrent_sessions': max_concurrent,
            'secure_cookies': config.get('secure_cookies', True),
            'extend_on_activity': config.get('extend_on_activity', True),
        }
    
    def _test_rate_limit_policy(self, config, test_data):
        """Test rate limit policy configuration."""
        limits = config.get('limits', {})
        
        results = []
        for limit_type, limit_config in limits.items():
            requests = limit_config.get('requests', 0)
            window_minutes = limit_config.get('window_minutes', 0)
            
            results.append({
                'type': limit_type,
                'requests_per_window': requests,
                'window_minutes': window_minutes,
                'requests_per_minute': round(requests / window_minutes, 2) if window_minutes > 0 else 0,
            })
        
        return {
            'type': 'rate_limit_configuration',
            'limits': results
        }
    
    def _test_authentication_policy(self, config, test_data):
        """Test authentication policy configuration."""
        return {
            'type': 'authentication_configuration',
            'require_2fa': config.get('require_2fa', False),
            'lockout_attempts': config.get('lockout_attempts', 5),
            'lockout_duration_minutes': config.get('lockout_duration_minutes', 30),
            'password_reset_token_expiry_hours': config.get('password_reset_token_expiry_hours', 24),
            'remember_me_duration_days': config.get('remember_me_duration_days', 30),
        }