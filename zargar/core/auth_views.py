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
from .models import User, AuditLog


class AdminLoginView(auth_views.LoginView):
    """
    Custom login view for super-panel administrators.
    """
    template_name = 'auth/admin_login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('core:dashboard')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'ورود مدیر سیستم',
            'is_admin_login': True,
        })
        return context
    
    def form_valid(self, form):
        """Handle successful login with audit logging."""
        user = form.get_user()
        
        # Check if user is super admin
        if not user.is_super_admin:
            messages.error(self.request, _('شما مجوز دسترسی به پنل مدیریت را ندارید.'))
            return self.form_invalid(form)
        
        # Log successful login
        AuditLog.objects.create(
            user=user,
            action='login',
            details={
                'login_type': 'admin_panel',
                'ip_address': self.get_client_ip(),
                'user_agent': self.request.META.get('HTTP_USER_AGENT', ''),
            },
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
        )
        
        messages.success(self.request, _(f'خوش آمدید، {user.full_persian_name}'))
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Handle failed login attempts."""
        username = form.cleaned_data.get('username', '')
        
        # Log failed login attempt
        AuditLog.objects.create(
            user=None,
            action='login_failed',
            details={
                'username': username,
                'login_type': 'admin_panel',
                'ip_address': self.get_client_ip(),
                'user_agent': self.request.META.get('HTTP_USER_AGENT', ''),
                'errors': form.errors.as_json(),
            },
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
        )
        
        return super().form_invalid(form)
    
    def get_client_ip(self):
        """Get client IP address."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class AdminLogoutView(auth_views.LogoutView):
    """
    Custom logout view for super-panel administrators.
    """
    next_page = reverse_lazy('core:admin_login')
    
    def dispatch(self, request, *args, **kwargs):
        """Log logout action before processing."""
        if request.user.is_authenticated:
            AuditLog.objects.create(
                user=request.user,
                action='logout',
                details={
                    'logout_type': 'admin_panel',
                    'ip_address': self.get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                },
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            
            messages.success(request, _('با موفقیت از سیستم خارج شدید.'))
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


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
    This will be implemented in a later task.
    """
    template_name = 'auth/admin_2fa_verify.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'تأیید کد دو مرحله‌ای',
            'is_2fa_verify': True,
        })
        return context