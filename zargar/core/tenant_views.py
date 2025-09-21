"""
Views for tenant-specific functionality.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, UpdateView, View, ListView, CreateView, DeleteView
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
import json
from .models import User, AuditLog, TOTPDevice


class TenantContextMixin:
    """
    Mixin to add tenant context to views.
    """
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add tenant-specific context
        if hasattr(self.request, 'tenant_context') and self.request.tenant_context:
            context.update({
                'tenant': self.request.tenant_context['tenant'],
                'tenant_name': self.request.tenant_context['name'],
                'tenant_domain': self.request.tenant_context['domain_url'],
                'tenant_schema': self.request.tenant_context['schema_name'],
            })
        
        return context


class TenantOwnerRequiredMixin(UserPassesTestMixin):
    """
    Mixin to require tenant owner access.
    """
    def test_func(self):
        return (self.request.user.is_authenticated and 
                self.request.user.can_manage_users())


class TenantDashboardView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Main dashboard for tenant portal with comprehensive business metrics.
    """
    template_name = 'tenant/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get tenant schema for dashboard service
        tenant_schema = getattr(self.request, 'tenant_context', {}).get('schema_name', 'default')
        
        # Initialize dashboard service
        from .dashboard_services import TenantDashboardService
        dashboard_service = TenantDashboardService(tenant_schema)
        
        # Get comprehensive dashboard data
        dashboard_data = dashboard_service.get_comprehensive_dashboard_data()
        
        context.update({
            'page_title': 'داشبورد فروشگاه',
            'is_tenant_dashboard': True,
            'dashboard_data': dashboard_data,
            
            # Individual metric sections for template access
            'sales_metrics': dashboard_data.get('sales_metrics', {}),
            'inventory_metrics': dashboard_data.get('inventory_metrics', {}),
            'customer_metrics': dashboard_data.get('customer_metrics', {}),
            'gold_installment_metrics': dashboard_data.get('gold_installment_metrics', {}),
            'gold_price_data': dashboard_data.get('gold_price_data', {}),
            'financial_summary': dashboard_data.get('financial_summary', {}),
            'recent_activities': dashboard_data.get('recent_activities', []),
            'alerts_notifications': dashboard_data.get('alerts_and_notifications', {}),
            'performance_trends': dashboard_data.get('performance_trends', {}),
            
            # Theme and display settings
            'current_theme': self.request.user.theme_preference if self.request.user.is_authenticated else 'light',
            'is_dark_mode': self.request.user.theme_preference == 'dark' if self.request.user.is_authenticated else False,
            'show_cybersecurity_theme': self.request.user.theme_preference == 'dark' if self.request.user.is_authenticated else False,
            
            # Dashboard refresh settings
            'auto_refresh_enabled': True,
            'refresh_interval': 300000,  # 5 minutes in milliseconds
            'last_updated': dashboard_data.get('generated_at'),
        })
        
        return context


class TenantLoginView(TenantContextMixin, auth_views.LoginView):
    """
    Custom login view for tenant users.
    """
    template_name = 'auth/tenant_login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('tenant:dashboard')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'ورود به فروشگاه',
            'is_tenant_login': True,
        })
        return context
    
    def form_valid(self, form):
        """Handle successful login with audit logging and 2FA check."""
        user = form.get_user()
        
        # Check if user belongs to current tenant
        tenant_schema = getattr(self.request, 'tenant_context', {}).get('schema_name')
        if tenant_schema and hasattr(user, 'tenant_schema') and user.tenant_schema and user.tenant_schema != tenant_schema:
            messages.error(self.request, _('شما مجوز دسترسی به این فروشگاه را ندارید.'))
            return self.form_invalid(form)
        
        # Check if user has 2FA enabled
        if user.is_2fa_enabled:
            try:
                totp_device = TOTPDevice.objects.get(user=user, is_confirmed=True)
                
                # Store user ID in session for 2FA verification
                self.request.session['2fa_user_id'] = user.id
                self.request.session['2fa_next_url'] = self.get_success_url()
                
                # Log initial login attempt (before 2FA)
                AuditLog.objects.create(
                    user=user,
                    action='login_attempt',
                    details={
                        'login_type': 'tenant_portal',
                        'requires_2fa': True,
                        'tenant_schema': tenant_schema,
                        'ip_address': self.get_client_ip(),
                        'user_agent': self.request.META.get('HTTP_USER_AGENT', ''),
                    },
                    ip_address=self.get_client_ip(),
                    user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                    tenant_schema=tenant_schema,
                )
                
                # Redirect to 2FA verification
                return redirect('tenant:2fa_verify')
                
            except TOTPDevice.DoesNotExist:
                # User has 2FA enabled but no confirmed device - disable 2FA
                user.is_2fa_enabled = False
                user.save(update_fields=['is_2fa_enabled'])
                messages.warning(self.request, _('احراز هویت دو مرحله‌ای غیرفعال شد زیرا دستگاه تأیید شده‌ای یافت نشد.'))
        
        # Log successful login (no 2FA required)
        AuditLog.objects.create(
            user=user,
            action='login',
            details={
                'login_type': 'tenant_portal',
                'tenant_schema': tenant_schema,
                'ip_address': self.get_client_ip(),
                'user_agent': self.request.META.get('HTTP_USER_AGENT', ''),
            },
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            tenant_schema=tenant_schema,
        )
        
        messages.success(self.request, _(f'خوش آمدید، {user.full_persian_name}'))
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Handle failed login attempts."""
        username = form.cleaned_data.get('username', '')
        tenant_schema = getattr(self.request, 'tenant_context', {}).get('schema_name')
        
        # Log failed login attempt
        AuditLog.objects.create(
            user=None,
            action='login_failed',
            details={
                'username': username,
                'login_type': 'tenant_portal',
                'tenant_schema': tenant_schema,
                'ip_address': self.get_client_ip(),
                'user_agent': self.request.META.get('HTTP_USER_AGENT', ''),
                'errors': form.errors.as_json(),
            },
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            tenant_schema=tenant_schema,
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


class TenantLogoutView(auth_views.LogoutView):
    """
    Custom logout view for tenant users.
    """
    next_page = reverse_lazy('tenant:login')
    
    def dispatch(self, request, *args, **kwargs):
        """Log logout action before processing."""
        if request.user.is_authenticated:
            tenant_schema = getattr(request, 'tenant_context', {}).get('schema_name')
            
            AuditLog.objects.create(
                user=request.user,
                action='logout',
                details={
                    'logout_type': 'tenant_portal',
                    'tenant_schema': tenant_schema,
                    'ip_address': self.get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                },
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                tenant_schema=tenant_schema,
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


class TenantPasswordResetView(TenantContextMixin, auth_views.PasswordResetView):
    """
    Password reset view for tenant users.
    """
    template_name = 'auth/tenant_password_reset.html'
    email_template_name = 'auth/tenant_password_reset_email.html'
    subject_template_name = 'auth/tenant_password_reset_subject.txt'
    success_url = reverse_lazy('tenant:password_reset_done')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'بازیابی رمز عبور',
            'is_tenant_reset': True,
        })
        return context


class TenantPasswordResetDoneView(TenantContextMixin, auth_views.PasswordResetDoneView):
    """
    Password reset done view for tenant users.
    """
    template_name = 'auth/tenant_password_reset_done.html'


class TenantPasswordResetConfirmView(TenantContextMixin, auth_views.PasswordResetConfirmView):
    """
    Password reset confirm view for tenant users.
    """
    template_name = 'auth/tenant_password_reset_confirm.html'
    success_url = reverse_lazy('tenant:password_reset_complete')


class TenantPasswordResetCompleteView(TenantContextMixin, auth_views.PasswordResetCompleteView):
    """
    Password reset complete view for tenant users.
    """
    template_name = 'auth/tenant_password_reset_complete.html'


class UserProfileView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    User profile view.
    """
    template_name = 'core/tenant/profile.html'


class UserProfileEditView(LoginRequiredMixin, TenantContextMixin, UpdateView):
    """
    Edit user profile.
    """
    model = User
    template_name = 'core/tenant/profile_edit.html'
    fields = [
        'first_name', 'last_name', 'persian_first_name', 'persian_last_name',
        'email', 'phone_number', 'theme_preference'
    ]
    
    def get_object(self):
        return self.request.user
    
    def form_valid(self, form):
        messages.success(self.request, _('Profile updated successfully.'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return '/profile/'


@method_decorator(csrf_exempt, name='dispatch')
class ThemeToggleView(View):
    """
    Handle theme toggle requests via AJAX for tenant users.
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
            tenant_schema = getattr(request, 'tenant_context', {}).get('schema_name')
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
                tenant_schema=tenant_schema,
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


class TwoFactorSetupView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    2FA setup view.
    """
    template_name = 'core/tenant/2fa_setup.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # TODO: Implement 2FA setup logic with django-otp
        context['qr_code_url'] = None
        context['secret_key'] = None
        
        return context


class TwoFactorDisableView(LoginRequiredMixin, View):
    """
    Disable 2FA for user.
    """
    def post(self, request):
        user = request.user
        user.is_2fa_enabled = False
        user.save(update_fields=['is_2fa_enabled'])
        
        # TODO: Remove 2FA devices with django-otp
        
        messages.success(request, _('Two-factor authentication disabled.'))
        return redirect('/profile/')


# User Management Views

class UserManagementListView(TenantOwnerRequiredMixin, TenantContextMixin, ListView):
    """
    List all users in the tenant for management.
    """
    model = User
    template_name = 'core/tenant/user_management/list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        """Get all users in current tenant."""
        return User.objects.filter(is_active=True).order_by('-date_joined')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'مدیریت کاربران',
            'total_users': self.get_queryset().count(),
            'active_users': self.get_queryset().filter(is_active=True).count(),
            'role_choices': User.ROLE_CHOICES,
        })
        return context


class UserCreateView(TenantOwnerRequiredMixin, TenantContextMixin, CreateView):
    """
    Create new user in tenant.
    """
    model = User
    template_name = 'core/tenant/user_management/create.html'
    fields = [
        'username', 'email', 'first_name', 'last_name',
        'persian_first_name', 'persian_last_name', 'phone_number', 'role'
    ]
    success_url = reverse_lazy('tenant:user_management')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'افزودن کاربر جدید',
            'form_action': 'create',
        })
        return context
    
    def form_valid(self, form):
        """Create user with temporary password."""
        user = form.save(commit=False)
        
        # Set temporary password
        import secrets
        import string
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        user.set_password(temp_password)
        user.save()
        
        # Log user creation
        AuditLog.objects.create(
            user=self.request.user,
            action='create',
            model_name='User',
            object_id=str(user.pk),
            details={
                'created_user': user.username,
                'role': user.role,
                'temp_password': temp_password,  # Store for initial setup
            },
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
        )
        
        messages.success(
            self.request, 
            _(f'کاربر {user.full_persian_name} با موفقیت ایجاد شد. رمز عبور موقت: {temp_password}')
        )
        return super().form_valid(form)
    
    def get_client_ip(self):
        """Get client IP address."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class UserUpdateView(TenantOwnerRequiredMixin, TenantContextMixin, UpdateView):
    """
    Update user information and role.
    """
    model = User
    template_name = 'core/tenant/user_management/edit.html'
    fields = [
        'first_name', 'last_name', 'persian_first_name', 'persian_last_name',
        'email', 'phone_number', 'role', 'is_active'
    ]
    success_url = reverse_lazy('tenant:user_management')
    
    def get_queryset(self):
        """Only allow editing users in current tenant."""
        return User.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': f'ویرایش کاربر: {self.object.full_persian_name}',
            'form_action': 'edit',
            'user_obj': self.object,
        })
        return context
    
    def form_valid(self, form):
        """Update user with audit logging."""
        old_role = self.object.role
        user = form.save()
        
        # Log role change if it occurred
        if old_role != user.role:
            AuditLog.objects.create(
                user=self.request.user,
                action='update',
                model_name='User',
                object_id=str(user.pk),
                details={
                    'updated_user': user.username,
                    'old_role': old_role,
                    'new_role': user.role,
                    'changed_by': self.request.user.username,
                },
                ip_address=self.get_client_ip(),
                user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            )
        
        messages.success(self.request, _(f'اطلاعات کاربر {user.full_persian_name} به‌روزرسانی شد.'))
        return super().form_valid(form)
    
    def get_client_ip(self):
        """Get client IP address."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class UserDetailView(TenantOwnerRequiredMixin, TenantContextMixin, TemplateView):
    """
    View user details and activity.
    """
    template_name = 'core/tenant/user_management/detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = kwargs.get('pk')
        user_obj = get_object_or_404(User, pk=user_id, is_active=True)
        
        # Get user's recent activities
        recent_activities = AuditLog.objects.filter(
            user=user_obj
        ).order_by('-timestamp')[:20]
        
        context.update({
            'page_title': f'جزئیات کاربر: {user_obj.full_persian_name}',
            'user_obj': user_obj,
            'recent_activities': recent_activities,
            'can_reset_password': True,
            'can_toggle_2fa': True,
        })
        return context


class UserDeactivateView(TenantOwnerRequiredMixin, View):
    """
    Deactivate user (soft delete).
    """
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk, is_active=True)
        
        # Prevent self-deactivation
        if user == request.user:
            messages.error(request, _('نمی‌توانید خودتان را غیرفعال کنید.'))
            return redirect('tenant:user_management')
        
        # Deactivate user
        user.is_active = False
        user.save(update_fields=['is_active'])
        
        # Log deactivation
        AuditLog.objects.create(
            user=request.user,
            action='update',
            model_name='User',
            object_id=str(user.pk),
            details={
                'deactivated_user': user.username,
                'deactivated_by': request.user.username,
                'action': 'deactivated',
            },
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        
        messages.success(request, _(f'کاربر {user.full_persian_name} غیرفعال شد.'))
        return redirect('tenant:user_management')
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserPasswordResetView(TenantOwnerRequiredMixin, View):
    """
    Reset user password (admin action).
    """
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk, is_active=True)
        
        # Generate new temporary password
        import secrets
        import string
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        user.set_password(temp_password)
        user.save(update_fields=['password'])
        
        # Log password reset
        AuditLog.objects.create(
            user=request.user,
            action='update',
            model_name='User',
            object_id=str(user.pk),
            details={
                'password_reset_user': user.username,
                'reset_by': request.user.username,
                'temp_password': temp_password,
                'action': 'password_reset',
            },
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        
        messages.success(
            request, 
            _(f'رمز عبور کاربر {user.full_persian_name} بازنشانی شد. رمز عبور جدید: {temp_password}')
        )
        return redirect('tenant:user_detail', pk=pk)
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserProfileView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    User profile view with 2FA management.
    """
    template_name = 'core/tenant/user_management/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'پروفایل کاربری',
            'user_obj': self.request.user,
            'can_change_password': True,
            'can_setup_2fa': not self.request.user.is_2fa_enabled,
            'can_disable_2fa': self.request.user.is_2fa_enabled,
        })
        return context


class UserProfileEditView(LoginRequiredMixin, TenantContextMixin, UpdateView):
    """
    Edit user profile.
    """
    model = User
    template_name = 'core/tenant/user_management/profile_edit.html'
    fields = [
        'first_name', 'last_name', 'persian_first_name', 'persian_last_name',
        'email', 'phone_number', 'theme_preference'
    ]
    success_url = reverse_lazy('tenant:profile')
    
    def get_object(self):
        return self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'ویرایش پروفایل',
            'form_action': 'edit_profile',
        })
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('پروفایل شما با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)


class UserPasswordChangeView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Change user password.
    """
    template_name = 'core/tenant/user_management/password_change.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'تغییر رمز عبور',
            'form': PasswordChangeForm(self.request.user),
        })
        return context
    
    def post(self, request, *args, **kwargs):
        form = PasswordChangeForm(request.user, request.POST)
        
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            
            # Log password change
            AuditLog.objects.create(
                user=request.user,
                action='update',
                model_name='User',
                object_id=str(user.pk),
                details={
                    'action': 'password_changed',
                    'changed_by_self': True,
                },
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            
            messages.success(request, _('رمز عبور شما با موفقیت تغییر یافت.'))
            return redirect('tenant:profile')
        else:
            context = self.get_context_data()
            context['form'] = form
            return render(request, self.template_name, context)
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class User2FASetupView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    2FA setup view with QR code generation.
    """
    template_name = 'core/tenant/user_management/2fa_setup.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Generate TOTP secret and QR code
            import pyotp
            import qrcode
            import io
            import base64
            
            # Generate secret key
            secret = pyotp.random_base32()
            
            # Create TOTP URI
            totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=self.request.user.email,
                issuer_name=f"زرگر - {getattr(self.request, 'tenant_context', {}).get('name', 'فروشگاه')}"
            )
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(totp_uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            qr_code_data = base64.b64encode(buffer.getvalue()).decode()
            
            context.update({
                'page_title': 'راه‌اندازی احراز هویت دو مرحله‌ای',
                'secret_key': secret,
                'qr_code_data': qr_code_data,
                'totp_uri': totp_uri,
            })
        except ImportError:
            # Handle missing dependencies gracefully
            context.update({
                'page_title': 'راه‌اندازی احراز هویت دو مرحله‌ای',
                'secret_key': 'DEMO_SECRET_KEY',
                'qr_code_data': None,
                'totp_uri': None,
                'error': 'Dependencies for 2FA are not installed'
            })
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Verify and enable 2FA."""
        try:
            import pyotp
        except ImportError:
            messages.error(request, _('Dependencies for 2FA are not installed.'))
            return redirect('tenant:profile')
        
        secret = request.POST.get('secret')
        token = request.POST.get('token')
        
        if not secret or not token:
            messages.error(request, _('کلید مخفی و کد تأیید الزامی است.'))
            return self.get(request, *args, **kwargs)
        
        # Verify token
        totp = pyotp.TOTP(secret)
        if totp.verify(token):
            # Enable 2FA for user
            request.user.is_2fa_enabled = True
            request.user.save(update_fields=['is_2fa_enabled'])
            
            # TODO: Store secret key securely with django-otp
            
            # Log 2FA setup
            AuditLog.objects.create(
                user=request.user,
                action='update',
                model_name='User',
                object_id=str(request.user.pk),
                details={
                    'action': '2fa_enabled',
                    'setup_by_self': True,
                },
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            
            messages.success(request, _('احراز هویت دو مرحله‌ای با موفقیت فعال شد.'))
            return redirect('tenant:profile')
        else:
            messages.error(request, _('کد تأیید نامعتبر است. لطفاً دوباره تلاش کنید.'))
            return self.get(request, *args, **kwargs)
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class User2FADisableView(LoginRequiredMixin, View):
    """
    Disable 2FA for user.
    """
    def post(self, request):
        if not request.user.is_2fa_enabled:
            messages.warning(request, _('احراز هویت دو مرحله‌ای از قبل غیرفعال است.'))
            return redirect('tenant:profile')
        
        # Disable 2FA
        request.user.is_2fa_enabled = False
        request.user.save(update_fields=['is_2fa_enabled'])
        
        # TODO: Remove 2FA devices with django-otp
        
        # Log 2FA disable
        AuditLog.objects.create(
            user=request.user,
            action='update',
            model_name='User',
            object_id=str(request.user.pk),
            details={
                'action': '2fa_disabled',
                'disabled_by_self': True,
            },
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        
        messages.success(request, _('احراز هویت دو مرحله‌ای غیرفعال شد.'))
        return redirect('tenant:profile')
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip