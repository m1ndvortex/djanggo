"""
Views for the super-admin panel.
These views operate in the shared schema and manage cross-tenant functionality.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Sum
from decimal import Decimal

from zargar.tenants.admin_models import SuperAdmin, SubscriptionPlan, TenantInvoice
from zargar.tenants.models import Tenant


class SuperAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin that requires the user to be a superadmin.
    """
    login_url = reverse_lazy('admin_panel:login')
    
    def test_func(self):
        """Test if user is a superadmin."""
        return (
            self.request.user.is_authenticated and 
            self.request.user.is_superuser and
            hasattr(self.request.user, '_meta') and
            self.request.user._meta.model_name == 'superadmin'
        )
    
    def handle_no_permission(self):
        """Handle when user doesn't have permission."""
        if not self.request.user.is_authenticated:
            return redirect(self.get_login_url())
        
        messages.error(
            self.request, 
            _('شما دسترسی لازم برای مشاهده این صفحه را ندارید.')
        )
        return redirect('admin_panel:dashboard')


class AdminPanelDashboardView(SuperAdminRequiredMixin, TemplateView):
    """
    Main dashboard for the admin panel.
    """
    template_name = 'admin_panel/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get basic statistics
        total_tenants = Tenant.objects.exclude(schema_name='public').count()
        active_tenants = Tenant.objects.exclude(schema_name='public').filter(is_active=True).count()
        total_plans = SubscriptionPlan.objects.filter(is_active=True).count()
        total_invoices = TenantInvoice.objects.count()
        
        # Revenue statistics
        total_revenue = TenantInvoice.objects.filter(status='paid').aggregate(
            total=Sum('total_amount_toman')
        )['total'] or Decimal('0')
        
        pending_revenue = TenantInvoice.objects.filter(status='pending').aggregate(
            total=Sum('total_amount_toman')
        )['total'] or Decimal('0')
        
        context.update({
            'total_tenants': total_tenants,
            'active_tenants': active_tenants,
            'total_plans': total_plans,
            'total_invoices': total_invoices,
            'total_revenue': total_revenue,
            'pending_revenue': pending_revenue,
        })
        
        return context


class AdminLoginView(TemplateView):
    """
    Login view for super-admin panel.
    """
    template_name = 'admin_panel/login.html'
    
    def post(self, request):
        """Handle login form submission."""
        from django.contrib.auth import authenticate, login
        
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user and isinstance(user, SuperAdmin) and user.is_superuser:
                login(request, user)
                return redirect('admin_panel:dashboard')
            else:
                messages.error(request, 'نام کاربری یا رمز عبور اشتباه است.')
        
        return self.get(request)


class AdminLogoutView(TemplateView):
    """
    Logout view for super-admin panel.
    """
    
    def get(self, request):
        """Handle logout."""
        from django.contrib.auth import logout
        logout(request)
        return redirect('admin_panel:login')