"""
Views for the super-admin panel.
These views operate in the shared schema and manage cross-tenant functionality.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, ListView, View
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Sum, Q
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import logging

from zargar.tenants.admin_models import SuperAdmin, SubscriptionPlan, TenantInvoice
from zargar.tenants.models import Tenant
from .models import ImpersonationSession
from .hijack_permissions import check_hijack_permissions, get_hijackable_users, log_hijack_attempt

logger = logging.getLogger('hijack_audit')
User = get_user_model()


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


class UserImpersonationView(SuperAdminRequiredMixin, TemplateView):
    """
    View to display users available for impersonation.
    """
    template_name = 'admin_panel/user_impersonation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all tenants with their users
        tenants_with_users = []
        for tenant in Tenant.objects.exclude(schema_name='public').filter(is_active=True):
            # Switch to tenant schema to get users
            from django_tenants.utils import schema_context
            with schema_context(tenant.schema_name):
                users = get_hijackable_users(self.request.user)
                if users.exists():
                    tenants_with_users.append({
                        'tenant': tenant,
                        'users': users[:10]  # Limit to 10 users per tenant for display
                    })
        
        context['tenants_with_users'] = tenants_with_users
        context['active_sessions'] = ImpersonationSession.objects.active_sessions()[:10]
        
        return context


class ImpersonationAuditView(SuperAdminRequiredMixin, ListView):
    """
    View to display impersonation audit logs.
    """
    model = ImpersonationSession
    template_name = 'admin_panel/impersonation_audit.html'
    context_object_name = 'sessions'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = ImpersonationSession.objects.all().order_by('-start_time')
        
        # Filter by admin user
        admin_filter = self.request.GET.get('admin')
        if admin_filter:
            queryset = queryset.filter(admin_username__icontains=admin_filter)
        
        # Filter by target user
        target_filter = self.request.GET.get('target')
        if target_filter:
            queryset = queryset.filter(target_username__icontains=target_filter)
        
        # Filter by tenant
        tenant_filter = self.request.GET.get('tenant')
        if tenant_filter:
            queryset = queryset.filter(tenant_schema__icontains=tenant_filter)
        
        # Filter by status
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by suspicious sessions
        if self.request.GET.get('suspicious') == 'true':
            queryset = queryset.filter(is_suspicious=True)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context['admin_filter'] = self.request.GET.get('admin', '')
        context['target_filter'] = self.request.GET.get('target', '')
        context['tenant_filter'] = self.request.GET.get('tenant', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['suspicious_filter'] = self.request.GET.get('suspicious', '')
        
        # Add statistics
        context['total_sessions'] = ImpersonationSession.objects.count()
        context['active_sessions'] = ImpersonationSession.objects.active_sessions().count()
        context['suspicious_sessions'] = ImpersonationSession.objects.suspicious_sessions().count()
        
        return context


class StartImpersonationView(SuperAdminRequiredMixin, View):
    """
    View to start impersonation of a specific user.
    """
    
    def post(self, request):
        """Handle impersonation start request."""
        user_id = request.POST.get('user_id')
        tenant_schema = request.POST.get('tenant_schema')
        reason = request.POST.get('reason', '')
        
        if not user_id or not tenant_schema:
            messages.error(request, _('Missing required parameters'))
            return redirect('admin_panel:user_impersonation')
        
        try:
            # Switch to tenant schema to get the user
            from django_tenants.utils import schema_context
            with schema_context(tenant_schema):
                target_user = get_object_or_404(User, id=user_id)
                
                # Check permissions
                allowed, reason_denied = check_hijack_permissions(request.user, target_user)
                if not allowed:
                    log_hijack_attempt(request.user, target_user, False, reason_denied)
                    messages.error(request, _(f'Impersonation denied: {reason_denied}'))
                    return redirect('admin_panel:user_impersonation')
                
                # Use django-hijack to start impersonation
                from hijack.helpers import login_user
                
                # Get the tenant for redirect
                tenant = Tenant.objects.get(schema_name=tenant_schema)
                
                # Create impersonation session record
                session = ImpersonationSession.objects.create(
                    admin_user_id=request.user.id,
                    admin_username=request.user.username,
                    target_user_id=target_user.id,
                    target_username=target_user.username,
                    tenant_schema=tenant_schema,
                    tenant_domain=tenant.domain_url,
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    reason=reason,
                    status='active'
                )
                
                # Store session ID for tracking
                request.session['impersonation_session_id'] = str(session.session_id)
                
                # Log successful hijack attempt
                log_hijack_attempt(request.user, target_user, True)
                
                # Perform the hijack
                login_user(request, target_user)
                
                # Redirect to tenant domain
                redirect_url = f"https://{tenant.domain_url}/"
                messages.success(request, _(f'Successfully impersonating {target_user.username}'))
                
                return redirect(redirect_url)
        
        except Exception as e:
            logger.error(f"Error starting impersonation: {str(e)}")
            messages.error(request, _('Error starting impersonation'))
            return redirect('admin_panel:user_impersonation')
    
    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip


class EndImpersonationView(View):
    """
    View to end impersonation session.
    """
    
    def post(self, request):
        """Handle impersonation end request."""
        try:
            # Get current impersonation session
            session_id = request.session.get('impersonation_session_id')
            if session_id:
                session = ImpersonationSession.objects.get(session_id=session_id)
                session.end_session('manual')
                
                # Remove from session
                del request.session['impersonation_session_id']
                
                logger.info(f"Impersonation session {session_id} ended manually")
            
            # Use django-hijack to release user
            from hijack.helpers import release_hijack
            release_hijack(request)
            
            messages.success(request, _('Impersonation ended successfully'))
            return redirect('admin_panel:dashboard')
        
        except Exception as e:
            logger.error(f"Error ending impersonation: {str(e)}")
            messages.error(request, _('Error ending impersonation'))
            return redirect('admin_panel:dashboard')


class TerminateImpersonationView(SuperAdminRequiredMixin, View):
    """
    View to forcefully terminate an active impersonation session.
    """
    
    def post(self, request):
        """Handle impersonation termination request."""
        session_id = request.POST.get('session_id')
        reason = request.POST.get('reason', 'admin_termination')
        
        if not session_id:
            return JsonResponse({'success': False, 'error': 'Missing session ID'})
        
        try:
            session = get_object_or_404(ImpersonationSession, session_id=session_id)
            
            if session.is_active:
                session.terminate_session(reason)
                logger.info(f"Impersonation session {session_id} terminated by admin {request.user.username}")
                
                return JsonResponse({
                    'success': True,
                    'message': 'Session terminated successfully'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Session is not active'
                })
        
        except Exception as e:
            logger.error(f"Error terminating impersonation session: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Error terminating session'
            })


class ImpersonationSessionDetailView(SuperAdminRequiredMixin, TemplateView):
    """
    View to display detailed information about an impersonation session.
    """
    template_name = 'admin_panel/impersonation_session_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        session_id = kwargs.get('session_id')
        session = get_object_or_404(ImpersonationSession, session_id=session_id)
        
        context['session'] = session
        context['actions'] = session.actions_performed
        context['pages'] = session.pages_visited
        
        return context


class ImpersonationStatsView(SuperAdminRequiredMixin, TemplateView):
    """
    View to display impersonation statistics and analytics.
    """
    template_name = 'admin_panel/impersonation_stats.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Basic statistics
        total_sessions = ImpersonationSession.objects.count()
        active_sessions = ImpersonationSession.objects.active_sessions().count()
        suspicious_sessions = ImpersonationSession.objects.suspicious_sessions().count()
        
        # Sessions by admin
        sessions_by_admin = ImpersonationSession.objects.values(
            'admin_username'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Sessions by tenant
        sessions_by_tenant = ImpersonationSession.objects.values(
            'tenant_schema', 'tenant_domain'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Recent sessions
        recent_sessions = ImpersonationSession.objects.order_by('-start_time')[:20]
        
        # Average session duration
        from django.db.models import Avg
        avg_duration = ImpersonationSession.objects.filter(
            end_time__isnull=False
        ).aggregate(
            avg_duration=Avg('end_time') - Avg('start_time')
        )
        
        context.update({
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'suspicious_sessions': suspicious_sessions,
            'sessions_by_admin': sessions_by_admin,
            'sessions_by_tenant': sessions_by_tenant,
            'recent_sessions': recent_sessions,
            'avg_duration': avg_duration.get('avg_duration'),
        })
        
        return context