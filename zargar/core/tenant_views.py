"""
Views for tenant-specific functionality.
"""
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from .models import User


class TenantContextMixin:
    """
    Mixin to add tenant context to views.
    """
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self.request, 'tenant'):
            context['tenant'] = self.request.tenant
        return context


class TenantDashboardView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Main dashboard for tenant portal.
    """
    template_name = 'core/tenant/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add dashboard metrics
        context['dashboard_metrics'] = self.get_dashboard_metrics()
        
        # Add recent activities
        context['recent_activities'] = self.get_recent_activities()
        
        return context
    
    def get_dashboard_metrics(self):
        """
        Get basic dashboard metrics for the tenant.
        """
        # TODO: Implement actual metrics from business modules
        return {
            'total_sales_today': 0,
            'total_customers': 0,
            'inventory_items': 0,
            'pending_installments': 0,
        }
    
    def get_recent_activities(self):
        """
        Get recent activities for the tenant.
        """
        # TODO: Implement actual activities from audit logs
        return []


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


class ThemeToggleView(LoginRequiredMixin, View):
    """
    Toggle user theme preference.
    """
    def post(self, request):
        user = request.user
        current_theme = user.theme_preference
        new_theme = 'dark' if current_theme == 'light' else 'light'
        
        user.theme_preference = new_theme
        user.save(update_fields=['theme_preference'])
        
        response = JsonResponse({
            'success': True,
            'new_theme': new_theme,
            'message': _('Theme updated successfully.')
        })
        
        # Set theme cookie
        response.set_cookie(
            settings.THEME_SETTINGS['THEME_COOKIE_NAME'],
            new_theme,
            max_age=settings.THEME_SETTINGS['THEME_COOKIE_AGE']
        )
        
        return response


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