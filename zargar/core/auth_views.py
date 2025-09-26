"""
Authentication views for super-panel (admin) functionality.
"""
from django.contrib.auth import views as auth_views
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, View
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from .models import User, AuditLog, TOTPDevice


# Legacy admin login/logout views removed - now using unified admin system
# All admin authentication is handled by zargar.admin_panel.unified_auth_views


class AdminPasswordResetView(auth_views.PasswordResetView):
    """
    Password reset view for admin users.
    """
    template_name = 'auth/admin_password_reset.html'
    email_template_name = 'auth/admin_password_reset_email.html'
    subject_template_name = 'auth/admin_password_reset_subject.txt'
    success_url = reverse_lazy('core:admin_password_reset_done')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'بازیابی رمز عبور مدیر',
            'is_admin_reset': True,
        })
        return context


class AdminPasswordResetDoneView(auth_views.PasswordResetDoneView):
    """
    Password reset done view for admin users.
    """
    template_name = 'auth/admin_password_reset_done.html'


class AdminPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """
    Password reset confirm view for admin users.
    """
    template_name = 'auth/admin_password_reset_confirm.html'
    success_url = reverse_lazy('core:admin_password_reset_complete')


class AdminPasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    """
    Password reset complete view for admin users.
    """
    template_name = 'auth/admin_password_reset_complete.html'


@method_decorator(csrf_exempt, name='dispatch')
class ThemeToggleView(View):
    """
    Handle theme toggle requests via AJAX.
    """
    
    def post(self, request, *args, **kwargs):
        """Toggle user theme preference."""
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        try:
            data = json.loads(request.body)
            theme = data.get('theme', 'light')
            
            # Validate theme
            if theme not in settings.THEME_SETTINGS['AVAILABLE_THEMES']:
                return JsonResponse({'error': 'Invalid theme'}, status=400)
            
            # Update user preference
            request.user.theme_preference = theme
            request.user.save(update_fields=['theme_preference'])
            
            # Set cookie
            response = JsonResponse({
                'success': True,
                'theme': theme,
                'message': f'تم به {theme} تغییر یافت'
            })
            
            response.set_cookie(
                settings.THEME_SETTINGS['THEME_COOKIE_NAME'],
                theme,
                max_age=settings.THEME_SETTINGS['THEME_COOKIE_AGE'],
                secure=not settings.DEBUG,
                httponly=False,  # Allow JavaScript access for theme switching
                samesite='Lax'
            )
            
            # Log theme change
            AuditLog.objects.create(
                user=request.user,
                action='theme_changed',
                details={
                    'old_theme': request.COOKIES.get(settings.THEME_SETTINGS['THEME_COOKIE_NAME'], 'light'),
                    'new_theme': theme,
                    'ip_address': self.get_client_ip(request),
                },
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            
            return response
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class Admin2FASetupView(LoginRequiredMixin, TemplateView):
    """
    2FA setup view for admin users.
    This will be implemented in a later task.
    """
    template_name = 'auth/admin_2fa_setup.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'تنظیم احراز هویت دو مرحله‌ای',
            'is_2fa_setup': True,
        })
        return context


class Admin2FAVerifyView(TemplateView):
    """
    2FA verification view for admin users.
    """
    template_name = 'auth/admin_2fa_verify.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Check if admin user needs 2FA verification."""
        # Check if user is in 2FA verification state
        if not request.session.get('2fa_user_id') or not request.session.get('is_admin_login'):
            messages.error(request, _('جلسه احراز هویت منقضی شده است.'))
            return redirect('admin_panel:unified_login')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'تأیید کد دو مرحله‌ای',
            'is_2fa_verify': True,
            'is_admin_verify': True,
        })
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle admin 2FA verification."""
        user_id = request.session.get('2fa_user_id')
        token = request.POST.get('token', '').strip()
        
        if not user_id or not token:
            messages.error(request, _('اطلاعات ناقص ارسال شده است.'))
            return self.get(request, *args, **kwargs)
        
        try:
            user = User.objects.get(id=user_id)
            
            # Verify user is super admin
            if not user.is_superuser:
                messages.error(request, _('دسترسی غیرمجاز.'))
                return redirect('admin_panel:unified_login')
            
            totp_device = TOTPDevice.objects.get(user=user, is_confirmed=True)
            
            if totp_device.verify_token(token):
                # Complete admin login process
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                # Clear 2FA session data
                del request.session['2fa_user_id']
                del request.session['is_admin_login']
                
                messages.success(request, _(f'خوش آمدید، {user.full_persian_name}'))
                
                # Log successful admin 2FA verification
                AuditLog.objects.create(
                    user=user,
                    action='2fa_verified',
                    details={
                        'ip_address': self.get_client_ip(),
                        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                        'login_type': 'admin_panel',
                    },
                    ip_address=self.get_client_ip(),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                )
                
                # Redirect to admin dashboard
                next_url = request.session.get('2fa_next_url', '/admin/dashboard/')
                if '2fa_next_url' in request.session:
                    del request.session['2fa_next_url']
                
                return redirect(next_url)
            else:
                messages.error(request, _('کد تأیید نامعتبر است.'))
                
                # Log failed admin 2FA verification
                AuditLog.objects.create(
                    user=user,
                    action='2fa_failed',
                    details={
                        'action_type': 'admin_login_verification',
                        'ip_address': self.get_client_ip(),
                        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    },
                    ip_address=self.get_client_ip(),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                )
                
        except (User.DoesNotExist, TOTPDevice.DoesNotExist):
            messages.error(request, _('خطا در احراز هویت.'))
            return redirect('admin_panel:unified_login')
        except Exception as e:
            messages.error(request, _('خطای سیستمی رخ داده است.'))
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Admin 2FA verification error: {str(e)}")
        
        return self.get(request, *args, **kwargs)