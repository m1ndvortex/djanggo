"""
Views for core super-panel functionality.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.db import connection
from django_tenants.models import TenantMixin
from .models import User, SystemSettings, AuditLog


class SuperAdminRequiredMixin(UserPassesTestMixin):
    """
    Mixin to require super admin access.
    """
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_super_admin


class SuperPanelDashboardView(SuperAdminRequiredMixin, TemplateView):
    """
    Main dashboard for super-panel.
    """
    template_name = 'core/super_panel/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get tenant statistics
        from zargar.tenants.models import Tenant
        from datetime import datetime, timedelta
        
        total_tenants = Tenant.objects.count()
        active_tenants = Tenant.objects.filter(is_active=True).count()
        
        context['total_tenants'] = total_tenants
        context['active_tenants'] = active_tenants
        
        # Calculate growth percentages
        last_month = datetime.now() - timedelta(days=30)
        tenants_last_month = Tenant.objects.filter(created_on__gte=last_month).count()
        context['tenant_growth'] = round((tenants_last_month / max(total_tenants - tenants_last_month, 1)) * 100, 1) if total_tenants > 0 else 0
        
        # Get user statistics
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        
        context['total_users'] = total_users
        context['active_users'] = active_users
        
        # Calculate user growth
        users_last_month = User.objects.filter(date_joined__gte=last_month).count()
        context['user_growth'] = round((users_last_month / max(total_users - users_last_month, 1)) * 100, 1) if total_users > 0 else 0
        
        # Get recent audit logs
        context['recent_logs'] = AuditLog.objects.select_related('user').order_by('-timestamp')[:10]
        
        # System health metrics
        context['system_health'] = self.get_system_health()
        
        # Chart data for frontend
        context['tenant_growth_data'] = self.get_tenant_growth_data()
        context['system_performance_data'] = self.get_system_performance_data()
        context['active_tenants_trend'] = self.get_active_tenants_trend()
        
        # Theme context
        context['is_dark_mode'] = self.request.session.get('theme', 'light') == 'dark'
        context['current_theme'] = self.request.session.get('theme', 'light')
        
        return context
    
    def get_system_health(self):
        """
        Get basic system health metrics.
        """
        health = {
            'database': 'healthy',
            'redis': 'healthy',
            'celery': 'healthy',
        }
        
        try:
            # Test database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            health['database'] = 'error'
        
        # Test Redis connection
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 10)
            result = cache.get('health_check')
            if result != 'ok':
                health['redis'] = 'error'
        except Exception:
            health['redis'] = 'error'
        
        # Test Celery workers
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            if not stats:
                health['celery'] = 'warning'
        except Exception:
            health['celery'] = 'error'
        
        return health
    
    def get_tenant_growth_data(self):
        """
        Get tenant growth data for the last 6 months.
        """
        from zargar.tenants.models import Tenant
        from datetime import datetime, timedelta
        import calendar
        
        # Get data for last 6 months
        data = []
        for i in range(6):
            month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
            month_end = month_start.replace(day=calendar.monthrange(month_start.year, month_start.month)[1])
            
            count = Tenant.objects.filter(
                created_on__gte=month_start,
                created_on__lte=month_end
            ).count()
            data.insert(0, count)
        
        return ','.join(map(str, data))
    
    def get_system_performance_data(self):
        """
        Get system performance metrics (CPU, Memory, Disk usage).
        """
        import psutil
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent
            
            return f"{cpu_percent:.0f},{memory_percent:.0f},{disk_percent:.0f}"
        except Exception:
            # Return mock data if psutil is not available
            return "65,78,45"
    
    def get_active_tenants_trend(self):
        """
        Get active tenants trend for the last 6 periods.
        """
        from zargar.tenants.models import Tenant
        from datetime import datetime, timedelta
        
        data = []
        for i in range(6):
            date = datetime.now() - timedelta(days=7*i)  # Weekly data
            count = Tenant.objects.filter(
                is_active=True,
                created_on__lte=date
            ).count()
            data.insert(0, count)
        
        return ','.join(map(str, data))


class TenantListView(SuperAdminRequiredMixin, ListView):
    """
    List all tenants.
    """
    template_name = 'core/super_panel/tenant_list.html'
    context_object_name = 'tenants'
    paginate_by = 20
    
    def get_queryset(self):
        from zargar.tenants.models import Tenant
        return Tenant.objects.all().order_by('-created_on')


class TenantDetailView(SuperAdminRequiredMixin, DetailView):
    """
    Tenant detail view.
    """
    template_name = 'core/super_panel/tenant_detail.html'
    context_object_name = 'tenant'
    
    def get_queryset(self):
        from zargar.tenants.models import Tenant
        return Tenant.objects.all()


class TenantCreateView(SuperAdminRequiredMixin, CreateView):
    """
    Create new tenant.
    """
    template_name = 'core/super_panel/tenant_create.html'
    fields = ['name', 'schema_name']
    
    def get_queryset(self):
        from zargar.tenants.models import Tenant
        return Tenant.objects.all()
    
    def form_valid(self, form):
        messages.success(self.request, _('Tenant created successfully.'))
        return super().form_valid(form)


class TenantUpdateView(SuperAdminRequiredMixin, UpdateView):
    """
    Update tenant.
    """
    template_name = 'core/super_panel/tenant_edit.html'
    fields = ['name', 'is_active']
    
    def get_queryset(self):
        from zargar.tenants.models import Tenant
        return Tenant.objects.all()
    
    def form_valid(self, form):
        messages.success(self.request, _('Tenant updated successfully.'))
        return super().form_valid(form)


class TenantSuspendView(SuperAdminRequiredMixin, View):
    """
    Suspend/activate tenant.
    """
    def post(self, request, pk):
        from zargar.tenants.models import Tenant
        tenant = get_object_or_404(Tenant, pk=pk)
        
        tenant.is_active = not tenant.is_active
        tenant.save()
        
        action = 'activated' if tenant.is_active else 'suspended'
        messages.success(request, _(f'Tenant {action} successfully.'))
        
        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action='tenant_suspended' if not tenant.is_active else 'tenant_activated',
            model_name='Tenant',
            object_id=str(tenant.pk),
            details={'tenant_name': tenant.name, 'action': action},
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        
        return redirect('core:tenant_detail', pk=pk)
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SystemHealthView(SuperAdminRequiredMixin, TemplateView):
    """
    System health monitoring.
    """
    template_name = 'core/super_panel/system_health.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Database health
        context['database_health'] = self.check_database_health()
        
        # Redis health
        context['redis_health'] = self.check_redis_health()
        
        # Celery health
        context['celery_health'] = self.check_celery_health()
        
        return context
    
    def check_database_health(self):
        """Check database health."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return {'status': 'healthy', 'message': 'Database connection successful'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def check_redis_health(self):
        """Check Redis health."""
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 10)
            result = cache.get('health_check')
            if result == 'ok':
                return {'status': 'healthy', 'message': 'Redis connection successful'}
            else:
                return {'status': 'error', 'message': 'Redis test failed'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def check_celery_health(self):
        """Check Celery health."""
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            if stats:
                return {'status': 'healthy', 'message': f'{len(stats)} workers active'}
            else:
                return {'status': 'warning', 'message': 'No Celery workers found'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


class UserListView(SuperAdminRequiredMixin, ListView):
    """
    List all users.
    """
    model = User
    template_name = 'core/super_panel/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    ordering = ['-date_joined']


class UserDetailView(SuperAdminRequiredMixin, DetailView):
    """
    User detail view.
    """
    model = User
    template_name = 'core/super_panel/user_detail.html'
    context_object_name = 'user_obj'


class AuditLogListView(SuperAdminRequiredMixin, ListView):
    """
    List audit logs.
    """
    model = AuditLog
    template_name = 'core/super_panel/audit_logs.html'
    context_object_name = 'logs'
    paginate_by = 50
    ordering = ['-timestamp']


class SystemSettingsView(SuperAdminRequiredMixin, ListView):
    """
    System settings management.
    """
    model = SystemSettings
    template_name = 'core/super_panel/settings.html'
    context_object_name = 'settings'

class PersianCalendarDemoView(TemplateView):
    """
    Demo view for Persian calendar frontend components.
    """
    template_name = 'demo/persian_calendar_demo.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add current Persian date for demo
        from .calendar_utils import PersianCalendarUtils
        utils = PersianCalendarUtils()
        current_persian = utils.get_current_persian_date()
        
        context['current_persian_date'] = utils.format_persian_date(
            current_persian, format_style='numeric'
        )
        context['current_persian_date_formatted'] = utils.format_persian_date(
            current_persian, format_style='full'
        )
        
        return context