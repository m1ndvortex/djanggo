"""
Two-Factor Authentication (2FA) views for ZARGAR jewelry SaaS platform.
Handles TOTP device enrollment, verification, and management.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, View
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.urls import reverse_lazy, reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError
from django.utils import timezone
import json
import logging

from .models import User, TOTPDevice, AuditLog
from .tenant_views import TenantContextMixin

logger = logging.getLogger(__name__)


class TwoFASetupView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    2FA setup view for users to enroll their authenticator app.
    """
    template_name = 'core/tenant/user_management/2fa_setup.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get or create TOTP device
        totp_device, created = TOTPDevice.objects.get_or_create(user=user)
        
        context.update({
            'page_title': 'تنظیم احراز هویت دو مرحله‌ای',
            'totp_device': totp_device,
            'qr_code_data': totp_device.get_qr_code_image(),
            'qr_code_url': totp_device.get_qr_code_url(),
            'secret_key': totp_device.secret_key,
            'backup_tokens': totp_device.backup_tokens if totp_device.is_confirmed else None,
            'is_2fa_enabled': user.is_2fa_enabled,
            'setup_complete': totp_device.is_confirmed,
        })
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle 2FA setup confirmation."""
        user = request.user
        token = request.POST.get('token', '').strip()
        
        if not token:
            messages.error(request, _('لطفاً کد تأیید را وارد کنید.'))
            return self.get(request, *args, **kwargs)
        
        try:
            # Get user's TOTP device
            totp_device = TOTPDevice.objects.get(user=user)
            
            # Confirm device with token
            if totp_device.confirm_device(token):
                messages.success(request, _('احراز هویت دو مرحله‌ای با موفقیت فعال شد.'))
                
                # Log 2FA enablement
                AuditLog.objects.create(
                    user=user,
                    action='2fa_enabled',
                    details={
                        'device_id': totp_device.id,
                        'ip_address': self.get_client_ip(),
                        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    },
                    ip_address=self.get_client_ip(),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    tenant_schema=getattr(request, 'tenant', {}).get('schema_name', ''),
                )
                
                return redirect('core:profile')
            else:
                messages.error(request, _('کد تأیید نامعتبر است. لطفاً دوباره تلاش کنید.'))
                
                # Log failed 2FA setup
                AuditLog.objects.create(
                    user=user,
                    action='2fa_failed',
                    details={
                        'action_type': 'setup_confirmation',
                        'ip_address': self.get_client_ip(),
                        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    },
                    ip_address=self.get_client_ip(),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    tenant_schema=getattr(request, 'tenant', {}).get('schema_name', ''),
                )
                
        except TOTPDevice.DoesNotExist:
            messages.error(request, _('خطا در تنظیم احراز هویت دو مرحله‌ای.'))
            logger.error(f"TOTP device not found for user {user.username}")
        except Exception as e:
            messages.error(request, _('خطای سیستمی رخ داده است.'))
            logger.error(f"2FA setup error for user {user.username}: {str(e)}")
        
        return self.get(request, *args, **kwargs)


class TwoFADisableView(LoginRequiredMixin, TenantContextMixin, View):
    """
    Disable 2FA for the current user.
    """
    
    def post(self, request, *args, **kwargs):
        """Handle 2FA disable request."""
        user = request.user
        password = request.POST.get('password', '')
        
        # Verify password before disabling 2FA
        if not user.check_password(password):
            messages.error(request, _('رمز عبور نادرست است.'))
            return redirect('core:profile')
        
        try:
            # Delete TOTP device (this will automatically disable 2FA)
            totp_device = TOTPDevice.objects.get(user=user)
            totp_device.delete()
            
            messages.success(request, _('احراز هویت دو مرحله‌ای غیرفعال شد.'))
            
            # Log 2FA disablement
            AuditLog.objects.create(
                user=user,
                action='2fa_disabled',
                details={
                    'ip_address': self.get_client_ip(),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                },
                ip_address=self.get_client_ip(),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                tenant_schema=getattr(request, 'tenant', {}).get('schema_name', ''),
            )
            
        except TOTPDevice.DoesNotExist:
            messages.warning(request, _('احراز هویت دو مرحله‌ای قبلاً غیرفعال بوده است.'))
        except Exception as e:
            messages.error(request, _('خطای سیستمی رخ داده است.'))
            logger.error(f"2FA disable error for user {user.username}: {str(e)}")
        
        return redirect('core:profile')


class TwoFAVerifyView(TemplateView):
    """
    2FA verification view for login process.
    """
    template_name = 'auth/2fa_verify.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user needs 2FA verification."""
        # Check if user is in 2FA verification state
        if not request.session.get('2fa_user_id'):
            messages.error(request, _('جلسه احراز هویت منقضی شده است.'))
            return redirect('core:tenant_login')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'تأیید کد دو مرحله‌ای',
            'is_2fa_verify': True,
        })
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle 2FA verification."""
        user_id = request.session.get('2fa_user_id')
        token = request.POST.get('token', '').strip()
        
        if not user_id or not token:
            messages.error(request, _('اطلاعات ناقص ارسال شده است.'))
            return self.get(request, *args, **kwargs)
        
        try:
            user = User.objects.get(id=user_id)
            totp_device = TOTPDevice.objects.get(user=user, is_confirmed=True)
            
            if totp_device.verify_token(token):
                # Complete login process
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                # Clear 2FA session data
                del request.session['2fa_user_id']
                
                messages.success(request, _(f'خوش آمدید، {user.full_persian_name}'))
                
                # Log successful 2FA verification
                AuditLog.objects.create(
                    user=user,
                    action='2fa_verified',
                    details={
                        'ip_address': self.get_client_ip(),
                        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                        'login_type': 'tenant_portal',
                    },
                    ip_address=self.get_client_ip(),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    tenant_schema=getattr(request, 'tenant', {}).get('schema_name', ''),
                )
                
                # Check if backup token was used
                if token.upper() in totp_device.backup_tokens:
                    AuditLog.objects.create(
                        user=user,
                        action='backup_token_used',
                        details={
                            'remaining_tokens': len(totp_device.backup_tokens),
                            'ip_address': self.get_client_ip(),
                        },
                        ip_address=self.get_client_ip(),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        tenant_schema=getattr(request, 'tenant', {}).get('schema_name', ''),
                    )
                    
                    if len(totp_device.backup_tokens) <= 2:
                        messages.warning(request, _('تعداد کدهای پشتیبان شما کم است. لطفاً کدهای جدید تولید کنید.'))
                
                # Redirect to intended page or dashboard
                next_url = request.session.get('2fa_next_url', reverse('core:tenant_dashboard'))
                if '2fa_next_url' in request.session:
                    del request.session['2fa_next_url']
                
                return redirect(next_url)
            else:
                messages.error(request, _('کد تأیید نامعتبر است.'))
                
                # Log failed 2FA verification
                AuditLog.objects.create(
                    user=user,
                    action='2fa_failed',
                    details={
                        'action_type': 'login_verification',
                        'ip_address': self.get_client_ip(),
                        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    },
                    ip_address=self.get_client_ip(),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    tenant_schema=getattr(request, 'tenant', {}).get('schema_name', ''),
                )
                
        except (User.DoesNotExist, TOTPDevice.DoesNotExist):
            messages.error(request, _('خطا در احراز هویت.'))
            logger.error(f"2FA verification failed - user or device not found: {user_id}")
            return redirect('core:tenant_login')
        except Exception as e:
            messages.error(request, _('خطای سیستمی رخ داده است.'))
            logger.error(f"2FA verification error: {str(e)}")
        
        return self.get(request, *args, **kwargs)


class TwoFABackupTokensView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    View and regenerate backup tokens for 2FA.
    """
    template_name = 'core/tenant/user_management/2fa_backup_tokens.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        try:
            totp_device = TOTPDevice.objects.get(user=user, is_confirmed=True)
            context.update({
                'page_title': 'کدهای پشتیبان احراز هویت دو مرحله‌ای',
                'totp_device': totp_device,
                'backup_tokens': totp_device.backup_tokens,
                'tokens_count': len(totp_device.backup_tokens),
            })
        except TOTPDevice.DoesNotExist:
            messages.error(self.request, _('احراز هویت دو مرحله‌ای فعال نیست.'))
            context['no_2fa'] = True
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Regenerate backup tokens."""
        user = request.user
        password = request.POST.get('password', '')
        
        # Verify password before regenerating tokens
        if not user.check_password(password):
            messages.error(request, _('رمز عبور نادرست است.'))
            return self.get(request, *args, **kwargs)
        
        try:
            totp_device = TOTPDevice.objects.get(user=user, is_confirmed=True)
            
            # Generate new backup tokens
            totp_device.backup_tokens = totp_device.generate_backup_tokens()
            totp_device.save(update_fields=['backup_tokens'])
            
            messages.success(request, _('کدهای پشتیبان جدید تولید شدند.'))
            
            # Log backup token regeneration
            AuditLog.objects.create(
                user=user,
                action='backup_tokens_regenerated',
                details={
                    'tokens_count': len(totp_device.backup_tokens),
                    'ip_address': self.get_client_ip(),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                },
                ip_address=self.get_client_ip(),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                tenant_schema=getattr(request, 'tenant', {}).get('schema_name', ''),
            )
            
        except TOTPDevice.DoesNotExist:
            messages.error(request, _('احراز هویت دو مرحله‌ای فعال نیست.'))
        except Exception as e:
            messages.error(request, _('خطای سیستمی رخ داده است.'))
            logger.error(f"Backup token regeneration error for user {user.username}: {str(e)}")
        
        return self.get(request, *args, **kwargs)


@method_decorator(csrf_exempt, name='dispatch')
class TwoFAStatusAPIView(LoginRequiredMixin, View):
    """
    API endpoint to check 2FA status and get setup information.
    """
    
    def get(self, request, *args, **kwargs):
        """Get 2FA status for current user."""
        user = request.user
        
        try:
            totp_device = TOTPDevice.objects.get(user=user)
            
            return JsonResponse({
                'is_2fa_enabled': user.is_2fa_enabled,
                'is_confirmed': totp_device.is_confirmed,
                'backup_tokens_count': len(totp_device.backup_tokens),
                'last_used': totp_device.last_used_at.isoformat() if totp_device.last_used_at else None,
                'setup_url': reverse('core:2fa_setup'),
            })
            
        except TOTPDevice.DoesNotExist:
            return JsonResponse({
                'is_2fa_enabled': False,
                'is_confirmed': False,
                'backup_tokens_count': 0,
                'last_used': None,
                'setup_url': reverse('core:2fa_setup'),
            })
        except Exception as e:
            logger.error(f"2FA status API error for user {user.username}: {str(e)}")
            return JsonResponse({'error': 'Internal server error'}, status=500)


# Utility mixin for getting client IP
class ClientIPMixin:
    """Mixin to get client IP address."""
    
    def get_client_ip(self):
        """Get client IP address from request."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


# Add ClientIPMixin to all views
TwoFASetupView.__bases__ = TwoFASetupView.__bases__ + (ClientIPMixin,)
TwoFADisableView.__bases__ = TwoFADisableView.__bases__ + (ClientIPMixin,)
TwoFAVerifyView.__bases__ = TwoFAVerifyView.__bases__ + (ClientIPMixin,)
TwoFABackupTokensView.__bases__ = TwoFABackupTokensView.__bases__ + (ClientIPMixin,)