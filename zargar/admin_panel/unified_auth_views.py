"""
Unified authentication views for SuperAdmin access.
Handles login, logout, 2FA, and session management.
"""
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, View
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import connection
from django_tenants.utils import get_public_schema_name
from django_otp import match_token
from django_otp.models import Device

from zargar.tenants.admin_models import SuperAdmin, TenantAccessLog
from .unified_auth_backend import UnifiedSessionManager, UnifiedAuthPermissions

logger = logging.getLogger('zargar.admin_auth')


class UnifiedAdminLoginView(TemplateView):
    """
    Unified login view for SuperAdmin users.
    Handles authentication, 2FA, and session creation.
    """
    template_name = 'admin_panel/unified_login.html'
    
    def dispatch(self, request, *args, **kwargs):
        """
        Ensure we're in public schema and handle already authenticated users.
        """
        # Ensure we're in public schema
        if connection.schema_name != get_public_schema_name():
            messages.error(request, _('دسترسی غیرمجاز'))
            return redirect('/')
        
        # Redirect if already authenticated
        if request.user.is_authenticated and UnifiedAuthPermissions.check_superadmin_permission(request.user):
            next_url = request.GET.get('next') or request.session.get('next_url') or reverse('admin_panel:unified_dashboard')
            return redirect(next_url)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """
        Add context data for login form.
        """
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': _('ورود مدیر سیستم'),
            'show_2fa_field': self.request.session.get('requires_2fa', False),
            'username': self.request.session.get('partial_auth_username', ''),
            'login_attempts': self.request.session.get('login_attempts', 0),
            'max_attempts': 5,
        })
        return context
    
    @method_decorator(csrf_protect)
    def post(self, request):
        """
        Handle login form submission.
        """
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        otp_token = request.POST.get('otp_token', '').strip()
        remember_me = request.POST.get('remember_me') == 'on'
        
        # Basic validation
        if not username or not password:
            messages.error(request, _('نام کاربری و رمز عبور الزامی است.'))
            return self.get(request)
        
        # Check rate limiting
        if self._is_rate_limited(request, username):
            messages.error(request, _('تعداد تلاش‌های ناموفق زیاد است. لطفاً بعداً تلاش کنید.'))
            return self.get(request)
        
        # Handle 2FA flow
        if request.session.get('requires_2fa') and request.session.get('partial_auth_username') == username:
            return self._handle_2fa_verification(request, username, otp_token)
        
        # Initial authentication
        return self._handle_initial_authentication(request, username, password, remember_me)
    
    def _handle_initial_authentication(self, request, username, password, remember_me):
        """
        Handle initial username/password authentication.
        """
        try:
            # Attempt authentication
            user = authenticate(request, username=username, password=password)
            
            if user is None:
                self._handle_failed_login(request, username, 'invalid_credentials')
                messages.error(request, _('نام کاربری یا رمز عبور اشتباه است.'))
                return self.get(request)
            
            # Check if 2FA is required
            if user.is_2fa_enabled:
                # Store partial authentication state
                request.session['requires_2fa'] = True
                request.session['partial_auth_username'] = username
                request.session['partial_auth_user_id'] = user.id
                request.session['partial_auth_timestamp'] = timezone.now().isoformat()
                
                messages.info(request, _('لطفاً کد تأیید دو مرحله‌ای را وارد کنید.'))
                return self.get(request)
            
            # Complete login without 2FA
            return self._complete_login(request, user, remember_me)
            
        except Exception as e:
            logger.error(f"Error during initial authentication: {str(e)}")
            messages.error(request, _('خطا در فرآیند احراز هویت. لطفاً مجدداً تلاش کنید.'))
            return self.get(request)
    
    def _handle_2fa_verification(self, request, username, otp_token):
        """
        Handle 2FA token verification.
        """
        try:
            if not otp_token:
                messages.error(request, _('کد تأیید دو مرحله‌ای الزامی است.'))
                return self.get(request)
            
            # Check partial auth timeout (5 minutes)
            partial_auth_time_str = request.session.get('partial_auth_timestamp')
            if partial_auth_time_str:
                from datetime import datetime, timedelta
                partial_auth_time = datetime.fromisoformat(partial_auth_time_str.replace('Z', '+00:00'))
                if (timezone.now() - partial_auth_time) > timedelta(minutes=5):
                    self._clear_partial_auth(request)
                    messages.error(request, _('زمان تأیید دو مرحله‌ای منقضی شده است. لطفاً مجدداً وارد شوید.'))
                    return self.get(request)
            
            # Get user from partial auth
            user_id = request.session.get('partial_auth_user_id')
            if not user_id:
                self._clear_partial_auth(request)
                messages.error(request, _('خطا در فرآیند احراز هویت. لطفاً مجدداً وارد شوید.'))
                return self.get(request)
            
            try:
                user = SuperAdmin.objects.get(id=user_id)
            except SuperAdmin.DoesNotExist:
                self._clear_partial_auth(request)
                messages.error(request, _('کاربر یافت نشد.'))
                return self.get(request)
            
            # Verify 2FA token
            if not self._verify_2fa_token(user, otp_token):
                self._handle_failed_2fa(request, username)
                messages.error(request, _('کد تأیید دو مرحله‌ای اشتباه است.'))
                return self.get(request)
            
            # Clear partial auth state
            self._clear_partial_auth(request)
            
            # Complete login
            return self._complete_login(request, user, False)
            
        except Exception as e:
            logger.error(f"Error during 2FA verification: {str(e)}")
            self._clear_partial_auth(request)
            messages.error(request, _('خطا در تأیید دو مرحله‌ای. لطفاً مجدداً تلاش کنید.'))
            return self.get(request)
    
    def _complete_login(self, request, user, remember_me):
        """
        Complete the login process.
        """
        try:
            # Login user
            login(request, user)
            
            # Set session expiry
            if remember_me:
                request.session.set_expiry(30 * 24 * 60 * 60)  # 30 days
            else:
                request.session.set_expiry(2 * 60 * 60)  # 2 hours
            
            # Create admin session
            UnifiedSessionManager.create_admin_session(request, user)
            
            # Log successful login
            TenantAccessLog.log_action(
                user=user,
                tenant_schema='public',
                action='login',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
                success=True,
                details={
                    'login_method': 'unified_admin_login',
                    '2fa_used': user.is_2fa_enabled,
                    'remember_me': remember_me,
                    'login_timestamp': timezone.now().isoformat()
                }
            )
            
            # Clear login attempts
            self._clear_login_attempts(request, user.username)
            
            # Redirect to next URL or dashboard
            next_url = request.GET.get('next') or request.session.get('next_url') or reverse('admin_panel:unified_dashboard')
            if 'next_url' in request.session:
                del request.session['next_url']
            
            messages.success(request, _(f'خوش آمدید، {user.get_full_name() or user.username}'))
            
            logger.info(f"Successful unified admin login: {user.username} from {self._get_client_ip(request)}")
            
            return redirect(next_url)
            
        except Exception as e:
            logger.error(f"Error completing login: {str(e)}")
            messages.error(request, _('خطا در تکمیل فرآیند ورود.'))
            return self.get(request)
    
    def _verify_2fa_token(self, user, token):
        """
        Verify 2FA token for user.
        """
        try:
            device = match_token(user, token)
            return device is not None
        except Exception as e:
            logger.error(f"Error verifying 2FA token: {str(e)}")
            return False
    
    def _is_rate_limited(self, request, username):
        """
        Check if user is rate limited.
        """
        try:
            session_key = f'login_attempts_{username}'
            attempts = request.session.get(session_key, 0)
            
            # Allow 5 attempts per 15 minutes
            if attempts >= 5:
                last_attempt_str = request.session.get(f'last_attempt_{username}')
                if last_attempt_str:
                    from datetime import datetime, timedelta
                    last_attempt = datetime.fromisoformat(last_attempt_str.replace('Z', '+00:00'))
                    if (timezone.now() - last_attempt) < timedelta(minutes=15):
                        return True
                    else:
                        # Reset attempts after timeout
                        request.session[session_key] = 0
            
            return False
        except Exception:
            return False
    
    def _handle_failed_login(self, request, username, reason):
        """
        Handle failed login attempt.
        """
        try:
            # Increment attempts
            session_key = f'login_attempts_{username}'
            attempts = request.session.get(session_key, 0) + 1
            request.session[session_key] = attempts
            request.session[f'last_attempt_{username}'] = timezone.now().isoformat()
            
            # Log failed attempt
            TenantAccessLog.objects.create(
                user_type='superadmin',
                user_id=0,
                username=username,
                tenant_schema='public',
                action='login',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
                success=False,
                error_message=f'Login failed: {reason}',
                details={
                    'failure_reason': reason,
                    'attempt_number': attempts,
                    'attempt_timestamp': timezone.now().isoformat()
                }
            )
            
            logger.warning(f"Failed admin login attempt: {username} from {self._get_client_ip(request)} - {reason}")
        except Exception as e:
            logger.error(f"Error handling failed login: {str(e)}")
    
    def _handle_failed_2fa(self, request, username):
        """
        Handle failed 2FA attempt.
        """
        try:
            # Log failed 2FA
            TenantAccessLog.objects.create(
                user_type='superadmin',
                user_id=request.session.get('partial_auth_user_id', 0),
                username=username,
                tenant_schema='public',
                action='2fa_verification',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
                success=False,
                error_message='2FA verification failed',
                details={
                    'failure_reason': 'invalid_2fa_token',
                    'attempt_timestamp': timezone.now().isoformat()
                }
            )
            
            logger.warning(f"Failed 2FA attempt: {username} from {self._get_client_ip(request)}")
        except Exception as e:
            logger.error(f"Error handling failed 2FA: {str(e)}")
    
    def _clear_partial_auth(self, request):
        """
        Clear partial authentication state.
        """
        keys_to_clear = [
            'requires_2fa',
            'partial_auth_username',
            'partial_auth_user_id',
            'partial_auth_timestamp'
        ]
        for key in keys_to_clear:
            if key in request.session:
                del request.session[key]
    
    def _clear_login_attempts(self, request, username):
        """
        Clear login attempts for successful login.
        """
        keys_to_clear = [
            f'login_attempts_{username}',
            f'last_attempt_{username}'
        ]
        for key in keys_to_clear:
            if key in request.session:
                del request.session[key]
    
    def _get_client_ip(self, request):
        """
        Get client IP address.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip


class UnifiedAdminLogoutView(LoginRequiredMixin, View):
    """
    Unified logout view for SuperAdmin users.
    """
    login_url = reverse_lazy('admin_panel:unified_login')
    
    def dispatch(self, request, *args, **kwargs):
        """
        Ensure user is SuperAdmin.
        """
        if not UnifiedAuthPermissions.check_superadmin_permission(request.user):
            messages.error(request, _('دسترسی غیرمجاز'))
            return redirect(self.login_url)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        """
        Handle logout request.
        """
        return self._perform_logout(request)
    
    def post(self, request):
        """
        Handle logout request.
        """
        return self._perform_logout(request)
    
    def _perform_logout(self, request):
        """
        Perform logout and cleanup.
        """
        try:
            user = request.user
            
            # End admin session
            UnifiedSessionManager.end_admin_session(request, user)
            
            # Log logout
            TenantAccessLog.log_action(
                user=user,
                tenant_schema='public',
                action='logout',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
                success=True,
                details={
                    'logout_method': 'unified_admin_logout',
                    'logout_timestamp': timezone.now().isoformat()
                }
            )
            
            # Logout user
            logout(request)
            
            messages.success(request, _('با موفقیت خارج شدید.'))
            
            logger.info(f"Successful admin logout: {user.username} from {self._get_client_ip(request)}")
            
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
            messages.error(request, _('خطا در فرآیند خروج.'))
        
        return redirect(reverse('admin_panel:unified_login'))
    
    def _get_client_ip(self, request):
        """
        Get client IP address.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip


class UnifiedAdmin2FASetupView(LoginRequiredMixin, TemplateView):
    """
    View for setting up 2FA for SuperAdmin users.
    """
    template_name = 'admin_panel/2fa_setup.html'
    login_url = reverse_lazy('admin_panel:unified_login')
    
    def dispatch(self, request, *args, **kwargs):
        """
        Ensure user is SuperAdmin.
        """
        if not UnifiedAuthPermissions.check_superadmin_permission(request.user):
            messages.error(request, _('دسترسی غیرمجاز'))
            return redirect(self.login_url)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """
        Add 2FA setup context.
        """
        context = super().get_context_data(**kwargs)
        
        # Generate QR code for 2FA setup
        from django_otp.plugins.otp_totp.models import TOTPDevice
        
        device, created = TOTPDevice.objects.get_or_create(
            user=self.request.user,
            name='default',
            defaults={'confirmed': False}
        )
        
        if created or not device.confirmed:
            qr_url = device.config_url
            context['qr_url'] = qr_url
            context['secret_key'] = device.key
            context['device_id'] = device.id
        
        context['is_2fa_enabled'] = self.request.user.is_2fa_enabled
        
        return context
    
    def post(self, request):
        """
        Handle 2FA setup confirmation.
        """
        try:
            device_id = request.POST.get('device_id')
            verification_code = request.POST.get('verification_code', '').strip()
            
            if not device_id or not verification_code:
                messages.error(request, _('کد تأیید الزامی است.'))
                return self.get(request)
            
            from django_otp.plugins.otp_totp.models import TOTPDevice
            
            try:
                device = TOTPDevice.objects.get(id=device_id, user=request.user)
            except TOTPDevice.DoesNotExist:
                messages.error(request, _('دستگاه یافت نشد.'))
                return self.get(request)
            
            # Verify the code
            if device.verify_token(verification_code):
                device.confirmed = True
                device.save()
                
                # Enable 2FA for user
                request.user.is_2fa_enabled = True
                request.user.save(update_fields=['is_2fa_enabled'])
                
                # Log 2FA setup
                TenantAccessLog.log_action(
                    user=request.user,
                    tenant_schema='public',
                    action='2fa_enabled',
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    request_path=request.path,
                    request_method=request.method,
                    success=True,
                    details={
                        'setup_timestamp': timezone.now().isoformat()
                    }
                )
                
                messages.success(request, _('احراز هویت دو مرحله‌ای با موفقیت فعال شد.'))
                
                logger.info(f"2FA enabled for admin user: {request.user.username}")
                
                return redirect(reverse('admin_panel:unified_dashboard'))
            else:
                messages.error(request, _('کد تأیید اشتباه است.'))
                return self.get(request)
                
        except Exception as e:
            logger.error(f"Error setting up 2FA: {str(e)}")
            messages.error(request, _('خطا در راه‌اندازی احراز هویت دو مرحله‌ای.'))
            return self.get(request)
    
    def _get_client_ip(self, request):
        """
        Get client IP address.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip


class UnifiedAdminSessionStatusView(LoginRequiredMixin, View):
    """
    API view to check admin session status.
    """
    login_url = reverse_lazy('admin_panel:unified_login')
    
    def dispatch(self, request, *args, **kwargs):
        """
        Ensure user is SuperAdmin.
        """
        if not UnifiedAuthPermissions.check_superadmin_permission(request.user):
            return JsonResponse({'authenticated': False, 'error': 'Unauthorized'}, status=401)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        """
        Return session status information.
        """
        try:
            session_info = {
                'authenticated': True,
                'username': request.user.username,
                'full_name': request.user.get_full_name() or request.user.username,
                'is_2fa_enabled': request.user.is_2fa_enabled,
                'session_start': request.session.get('session_start_time'),
                'last_activity': request.session.get('last_activity'),
                'current_tenant': request.session.get('current_tenant_schema', 'public'),
                'permissions': {
                    'can_create_tenants': getattr(request.user, 'can_create_tenants', True),
                    'can_suspend_tenants': getattr(request.user, 'can_suspend_tenants', True),
                    'can_access_all_data': getattr(request.user, 'can_access_all_data', True),
                }
            }
            
            return JsonResponse(session_info)
            
        except Exception as e:
            logger.error(f"Error getting session status: {str(e)}")
            return JsonResponse({'authenticated': False, 'error': 'Internal error'}, status=500)