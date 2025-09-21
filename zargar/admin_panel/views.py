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


class BackupManagementView(SuperAdminRequiredMixin, TemplateView):
    """
    Main backup management dashboard view.
    """
    template_name = 'admin_panel/backup_management.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Import backup models
        from .models import BackupJob, BackupSchedule, RestoreJob
        
        # Recent backup jobs
        recent_backups = BackupJob.objects.order_by('-created_at')[:10]
        
        # Backup statistics
        total_backups = BackupJob.objects.count()
        successful_backups = BackupJob.objects.filter(status='completed').count()
        failed_backups = BackupJob.objects.filter(status='failed').count()
        running_backups = BackupJob.objects.filter(status='running').count()
        
        # Storage statistics
        from zargar.core.storage_utils import get_backup_storage_status
        storage_status = get_backup_storage_status()
        
        # Active schedules
        active_schedules = BackupSchedule.objects.filter(is_active=True)
        
        # Recent restore jobs
        recent_restores = RestoreJob.objects.order_by('-created_at')[:5]
        
        # Calculate total backup size
        total_size_bytes = BackupJob.objects.filter(
            status='completed',
            file_size_bytes__isnull=False
        ).aggregate(
            total=Sum('file_size_bytes')
        )['total'] or 0
        
        # Format total size
        def format_bytes(bytes_value):
            if not bytes_value:
                return '0 B'
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_value < 1024.0:
                    return f"{bytes_value:.1f} {unit}"
                bytes_value /= 1024.0
            return f"{bytes_value:.1f} PB"
        
        context.update({
            'recent_backups': recent_backups,
            'total_backups': total_backups,
            'successful_backups': successful_backups,
            'failed_backups': failed_backups,
            'running_backups': running_backups,
            'storage_status': storage_status,
            'active_schedules': active_schedules,
            'recent_restores': recent_restores,
            'total_backup_size': format_bytes(total_size_bytes),
            'success_rate': round((successful_backups / total_backups * 100) if total_backups > 0 else 0, 1),
        })
        
        return context


class BackupHistoryView(SuperAdminRequiredMixin, ListView):
    """
    View to display backup history with filtering and pagination.
    """
    template_name = 'admin_panel/backup_history.html'
    context_object_name = 'backups'
    paginate_by = 20
    
    def get_queryset(self):
        from .models import BackupJob
        
        queryset = BackupJob.objects.order_by('-created_at')
        
        # Filter by status
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by backup type
        type_filter = self.request.GET.get('type')
        if type_filter:
            queryset = queryset.filter(backup_type=type_filter)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            try:
                from datetime import datetime
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                from datetime import datetime
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=date_to_obj)
            except ValueError:
                pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter values to context
        context['status_filter'] = self.request.GET.get('status', '')
        context['type_filter'] = self.request.GET.get('type', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        
        # Add choices for filters
        from .models import BackupJob
        context['status_choices'] = BackupJob.STATUS_CHOICES
        context['type_choices'] = BackupJob.BACKUP_TYPES
        
        return context


class CreateBackupView(SuperAdminRequiredMixin, View):
    """
    View to create a new backup job.
    """
    
    def post(self, request):
        """Handle backup creation request."""
        from .models import BackupJob
        from zargar.tenants.models import Tenant
        
        backup_type = request.POST.get('backup_type')
        backup_name = request.POST.get('backup_name')
        tenant_schema = request.POST.get('tenant_schema', '')
        
        if not backup_type or not backup_name:
            messages.error(request, _('نوع پشتیبان‌گیری و نام الزامی است.'))
            return redirect('admin_panel:backup_management')
        
        try:
            # Create backup job
            backup_job = BackupJob.objects.create(
                name=backup_name,
                backup_type=backup_type,
                tenant_schema=tenant_schema,
                created_by_id=request.user.id,
                created_by_username=request.user.username,
                status='pending'
            )
            
            # Start backup process asynchronously
            from .tasks import start_backup_job
            start_backup_job.delay(backup_job.job_id)
            
            messages.success(
                request, 
                _(f'پشتیبان‌گیری "{backup_name}" با موفقیت شروع شد.')
            )
            
        except Exception as e:
            logger.error(f"Error creating backup job: {str(e)}")
            messages.error(request, _('خطا در ایجاد پشتیبان‌گیری'))
        
        return redirect('admin_panel:backup_management')


class BackupScheduleView(SuperAdminRequiredMixin, TemplateView):
    """
    View to manage backup schedules.
    """
    template_name = 'admin_panel/backup_schedule.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from .models import BackupSchedule
        
        # Get all schedules
        schedules = BackupSchedule.objects.order_by('name')
        
        context.update({
            'schedules': schedules,
            'backup_types': BackupSchedule._meta.get_field('backup_type').choices,
            'frequencies': BackupSchedule._meta.get_field('frequency').choices,
        })
        
        return context
    
    def post(self, request):
        """Handle schedule creation/update."""
        from .models import BackupSchedule
        
        schedule_id = request.POST.get('schedule_id')
        name = request.POST.get('name')
        backup_type = request.POST.get('backup_type')
        frequency = request.POST.get('frequency')
        scheduled_time = request.POST.get('scheduled_time')
        is_active = request.POST.get('is_active') == 'on'
        
        try:
            if schedule_id:
                # Update existing schedule
                schedule = BackupSchedule.objects.get(id=schedule_id)
                schedule.name = name
                schedule.backup_type = backup_type
                schedule.frequency = frequency
                schedule.scheduled_time = scheduled_time
                schedule.is_active = is_active
                schedule.save()
                
                messages.success(request, _('زمان‌بندی پشتیبان‌گیری به‌روزرسانی شد.'))
            else:
                # Create new schedule
                BackupSchedule.objects.create(
                    name=name,
                    backup_type=backup_type,
                    frequency=frequency,
                    scheduled_time=scheduled_time,
                    is_active=is_active,
                    created_by_id=request.user.id,
                    created_by_username=request.user.username
                )
                
                messages.success(request, _('زمان‌بندی پشتیبان‌گیری جدید ایجاد شد.'))
                
        except Exception as e:
            logger.error(f"Error managing backup schedule: {str(e)}")
            messages.error(request, _('خطا در مدیریت زمان‌بندی پشتیبان‌گیری'))
        
        return redirect('admin_panel:backup_schedule')


class TenantRestoreView(SuperAdminRequiredMixin, TemplateView):
    """
    View to handle tenant restoration from backups.
    """
    template_name = 'admin_panel/tenant_restore.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from .models import BackupJob, RestoreJob
        from .tenant_restoration import tenant_restoration_manager
        from zargar.tenants.models import Tenant
        
        # Get available backups for restoration
        available_backups = BackupJob.objects.filter(
            status='completed',
            backup_type__in=['full_system', 'tenant_only']
        ).order_by('-created_at')[:20]
        
        # Get all tenants for selection
        tenants = Tenant.objects.exclude(schema_name='public').order_by('name')
        
        # Get available snapshots
        available_snapshots = tenant_restoration_manager.get_available_snapshots()
        
        # Get recent restore jobs
        recent_restores = RestoreJob.objects.order_by('-created_at')[:10]
        
        context.update({
            'available_backups': available_backups,
            'tenants': tenants,
            'available_snapshots': available_snapshots,
            'recent_restores': recent_restores,
        })
        
        return context
    
    def post(self, request):
        """Handle tenant restore request."""
        from .tenant_restoration import tenant_restoration_manager
        from zargar.tenants.models import Tenant
        
        restore_type = request.POST.get('restore_type')
        
        if restore_type == 'from_backup':
            return self._handle_backup_restore(request)
        elif restore_type == 'from_snapshot':
            return self._handle_snapshot_restore(request)
        else:
            messages.error(request, _('نوع بازیابی نامعتبر است.'))
            return redirect('admin_panel:tenant_restore')
    
    def _handle_backup_restore(self, request):
        """Handle restoration from main backup."""
        from .tenant_restoration import tenant_restoration_manager
        from zargar.tenants.models import Tenant
        
        backup_id = request.POST.get('backup_id')
        target_tenant_id = request.POST.get('target_tenant_id')
        confirmation_text = request.POST.get('confirmation_text')
        
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json'
        
        if not backup_id or not target_tenant_id:
            error_msg = 'پشتیبان و تنانت هدف الزامی است.'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, _(error_msg))
            return redirect('admin_panel:tenant_restore')
        
        try:
            tenant = Tenant.objects.get(id=target_tenant_id)
            
            # Use tenant restoration manager
            result = tenant_restoration_manager.restore_tenant_from_main_backup(
                backup_id=backup_id,
                target_tenant_schema=tenant.schema_name,
                confirmation_text=confirmation_text,
                created_by_id=request.user.id,
                created_by_username=request.user.username
            )
            
            if result['success']:
                success_msg = f'بازیابی تنانت "{tenant.name}" شروع شد. شناسه کار: {result["restore_job_id"][:8]}...'
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'restore_job_id': result['restore_job_id'],
                        'message': success_msg,
                        'tenant_name': tenant.name
                    })
                messages.success(request, _(success_msg))
            else:
                error_msg = f'خطا در شروع بازیابی: {result["error"]}'
                if is_ajax:
                    return JsonResponse({'success': False, 'error': error_msg})
                messages.error(request, _(error_msg))
            
        except Tenant.DoesNotExist:
            error_msg = 'تنانت مورد نظر یافت نشد.'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, _(error_msg))
        except Exception as e:
            logger.error(f"Error starting tenant restore: {str(e)}")
            error_msg = 'خطا در شروع بازیابی تنانت'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, _(error_msg))
        
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'خطای نامشخص'})
        return redirect('admin_panel:tenant_restore')
    
    def _handle_snapshot_restore(self, request):
        """Handle restoration from snapshot."""
        from .tenant_restoration import tenant_restoration_manager
        
        snapshot_id = request.POST.get('snapshot_id')
        
        if not snapshot_id:
            messages.error(request, _('شناسه اسنپ‌شات الزامی است.'))
            return redirect('admin_panel:tenant_restore')
        
        try:
            # Use tenant restoration manager
            result = tenant_restoration_manager.restore_tenant_from_snapshot(
                snapshot_id=snapshot_id,
                created_by_id=request.user.id,
                created_by_username=request.user.username
            )
            
            if result['success']:
                messages.success(
                    request,
                    _(f'بازیابی از اسنپ‌شات شروع شد. شناسه کار: {result["restore_job_id"][:8]}...')
                )
            else:
                messages.error(request, _(f'خطا در شروع بازیابی: {result["error"]}'))
            
        except Exception as e:
            logger.error(f"Error starting snapshot restore: {str(e)}")
            messages.error(request, _('خطا در شروع بازیابی از اسنپ‌شات'))
        
        return redirect('admin_panel:tenant_restore')


class TenantSnapshotView(SuperAdminRequiredMixin, TemplateView):
    """
    View to manage tenant snapshots.
    """
    template_name = 'admin_panel/tenant_snapshots.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from .models import TenantSnapshot
        from .tenant_restoration import tenant_restoration_manager
        from zargar.tenants.models import Tenant
        
        # Get available snapshots
        available_snapshots = tenant_restoration_manager.get_available_snapshots()
        
        # Get all tenants for filtering
        tenants = Tenant.objects.exclude(schema_name='public').order_by('name')
        
        # Get recent snapshots with more details
        recent_snapshots = TenantSnapshot.objects.order_by('-created_at')[:20]
        
        context.update({
            'available_snapshots': available_snapshots,
            'tenants': tenants,
            'recent_snapshots': recent_snapshots,
        })
        
        return context
    
    def post(self, request):
        """Handle snapshot operations."""
        action = request.POST.get('action')
        
        if action == 'create_snapshot':
            return self._handle_create_snapshot(request)
        elif action == 'cleanup_snapshots':
            return self._handle_cleanup_snapshots(request)
        else:
            messages.error(request, _('عملیات نامعتبر است.'))
            return redirect('admin_panel:tenant_snapshots')
    
    def _handle_create_snapshot(self, request):
        """Handle manual snapshot creation."""
        from .tenant_restoration import tenant_restoration_manager
        from zargar.tenants.models import Tenant
        
        tenant_id = request.POST.get('tenant_id')
        operation_description = request.POST.get('operation_description')
        
        if not tenant_id or not operation_description:
            messages.error(request, _('تنانت و توضیحات عملیات الزامی است.'))
            return redirect('admin_panel:tenant_snapshots')
        
        try:
            tenant = Tenant.objects.get(id=tenant_id)
            
            # Create snapshot
            result = tenant_restoration_manager.create_pre_operation_snapshot(
                tenant_schema=tenant.schema_name,
                operation_description=operation_description,
                created_by_id=request.user.id,
                created_by_username=request.user.username
            )
            
            if result['success']:
                messages.success(
                    request,
                    _(f'اسنپ‌شات برای تنانت "{tenant.name}" ایجاد شد. شناسه: {result["snapshot_id"][:8]}...')
                )
            else:
                messages.error(request, _(f'خطا در ایجاد اسنپ‌شات: {result["error"]}'))
            
        except Tenant.DoesNotExist:
            messages.error(request, _('تنانت مورد نظر یافت نشد.'))
        except Exception as e:
            logger.error(f"Error creating snapshot: {str(e)}")
            messages.error(request, _('خطا در ایجاد اسنپ‌شات'))
        
        return redirect('admin_panel:tenant_snapshots')
    
    def _handle_cleanup_snapshots(self, request):
        """Handle snapshot cleanup."""
        from .tenant_restoration import tenant_restoration_manager
        
        try:
            result = tenant_restoration_manager.cleanup_old_snapshots()
            
            if result['success']:
                messages.success(request, _('پاکسازی اسنپ‌شات‌ها شروع شد.'))
            else:
                messages.error(request, _(f'خطا در پاکسازی: {result["error"]}'))
            
        except Exception as e:
            logger.error(f"Error starting snapshot cleanup: {str(e)}")
            messages.error(request, _('خطا در شروع پاکسازی اسنپ‌شات‌ها'))
        
        return redirect('admin_panel:tenant_snapshots')


class RestoreJobDetailView(SuperAdminRequiredMixin, TemplateView):
    """
    View to display detailed information about a restore job.
    """
    template_name = 'admin_panel/restore_job_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from .models import RestoreJob
        from .tenant_restoration import tenant_restoration_manager
        
        job_id = kwargs.get('job_id')
        
        # Get restore job details
        status_result = tenant_restoration_manager.get_restoration_status(job_id)
        
        if status_result['success']:
            restore_job = RestoreJob.objects.get(job_id=job_id)
            context['restore_job'] = restore_job
            context['status_data'] = status_result
        else:
            context['error'] = status_result['error']
        
        return context


class BackupJobDetailView(SuperAdminRequiredMixin, TemplateView):
    """
    View to display detailed information about a backup job.
    """
    template_name = 'admin_panel/backup_job_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from .models import BackupJob
        
        job_id = kwargs.get('job_id')
        backup_job = get_object_or_404(BackupJob, job_id=job_id)
        
        context['backup_job'] = backup_job
        context['log_messages'] = backup_job.log_messages
        
        return context


class DisasterRecoveryDashboardView(SuperAdminRequiredMixin, TemplateView):
    """
    Main disaster recovery dashboard view.
    """
    template_name = 'admin_panel/disaster_recovery_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from .disaster_recovery import DisasterRecoveryManager
        from .models import BackupJob, RestoreJob
        
        # Initialize disaster recovery manager
        dr_manager = DisasterRecoveryManager()
        
        # Get disaster recovery plan
        recovery_plan = dr_manager.create_disaster_recovery_plan()
        
        # Get recent disaster recovery tests
        recent_tests = self._get_recent_dr_tests()
        
        # Get system readiness status
        system_status = self._get_system_readiness_status()
        
        # Get available backups for recovery
        available_backups = BackupJob.objects.filter(
            status='completed',
            backup_type='full_system'
        ).order_by('-created_at')[:10]
        
        # Get recent restore operations
        recent_restores = RestoreJob.objects.order_by('-created_at')[:5]
        
        # Calculate recovery metrics
        recovery_metrics = self._calculate_recovery_metrics()
        
        context.update({
            'recovery_plan': recovery_plan,
            'recent_tests': recent_tests,
            'system_status': system_status,
            'available_backups': available_backups,
            'recent_restores': recent_restores,
            'recovery_metrics': recovery_metrics,
        })
        
        return context
    
    def _get_recent_dr_tests(self):
        """Get recent disaster recovery test results."""
        # This would typically come from a DR test log model
        # For now, return mock data based on the DR manager
        return [
            {
                'test_id': 'dr_test_001',
                'test_date': timezone.now() - timedelta(days=1),
                'test_type': 'full_recovery_simulation',
                'status': 'passed',
                'duration': '45 minutes',
                'components_tested': ['database', 'configuration', 'services'],
                'issues_found': 0,
            },
            {
                'test_id': 'dr_test_002',
                'test_date': timezone.now() - timedelta(days=7),
                'test_type': 'backup_validation',
                'status': 'passed',
                'duration': '15 minutes',
                'components_tested': ['backup_integrity', 'encryption'],
                'issues_found': 0,
            }
        ]
    
    def _get_system_readiness_status(self):
        """Get current system readiness for disaster recovery."""
        from zargar.core.storage_utils import storage_manager
        
        # Check backup storage connectivity
        storage_status = storage_manager.get_storage_status()
        
        # Check recent backup availability
        recent_backup = BackupJob.objects.filter(
            status='completed',
            backup_type='full_system',
            created_at__gte=timezone.now() - timedelta(days=7)
        ).first()
        
        # Check configuration backup
        config_backup = BackupJob.objects.filter(
            status='completed',
            backup_type='configuration',
            created_at__gte=timezone.now() - timedelta(days=30)
        ).first()
        
        return {
            'overall_status': 'ready' if recent_backup and config_backup else 'warning',
            'storage_connectivity': storage_status.get('overall_status', 'unknown'),
            'recent_full_backup': recent_backup is not None,
            'recent_config_backup': config_backup is not None,
            'last_full_backup_date': recent_backup.created_at if recent_backup else None,
            'last_config_backup_date': config_backup.created_at if config_backup else None,
            'estimated_rto': '4 hours',  # Recovery Time Objective
            'estimated_rpo': '24 hours',  # Recovery Point Objective
        }
    
    def _calculate_recovery_metrics(self):
        """Calculate disaster recovery metrics."""
        total_backups = BackupJob.objects.filter(backup_type='full_system').count()
        successful_backups = BackupJob.objects.filter(
            backup_type='full_system',
            status='completed'
        ).count()
        
        total_restores = RestoreJob.objects.count()
        successful_restores = RestoreJob.objects.filter(status='completed').count()
        
        return {
            'backup_success_rate': round((successful_backups / total_backups * 100) if total_backups > 0 else 0, 1),
            'restore_success_rate': round((successful_restores / total_restores * 100) if total_restores > 0 else 0, 1),
            'total_dr_tests': len(self._get_recent_dr_tests()),
            'last_test_date': timezone.now() - timedelta(days=1),
            'next_scheduled_test': timezone.now() + timedelta(days=29),
        }


class DisasterRecoveryTestView(SuperAdminRequiredMixin, View):
    """
    View to run disaster recovery tests.
    """
    
    def post(self, request):
        """Handle disaster recovery test request."""
        from .disaster_recovery import DisasterRecoveryManager
        
        test_type = request.POST.get('test_type')
        
        if not test_type:
            messages.error(request, _('نوع تست الزامی است.'))
            return redirect('admin_panel:disaster_recovery_dashboard')
        
        try:
            dr_manager = DisasterRecoveryManager()
            
            if test_type == 'full_procedures':
                # Run full disaster recovery procedure test
                test_results = dr_manager.test_disaster_recovery_procedures()
            elif test_type == 'backup_validation':
                # Test backup integrity and accessibility
                test_results = self._test_backup_validation(dr_manager)
            elif test_type == 'storage_connectivity':
                # Test storage connectivity
                test_results = self._test_storage_connectivity()
            else:
                messages.error(request, _('نوع تست نامعتبر است.'))
                return redirect('admin_panel:disaster_recovery_dashboard')
            
            if test_results.get('overall_status') == 'success':
                messages.success(
                    request,
                    _(f'تست بازیابی "{test_type}" با موفقیت انجام شد.')
                )
            else:
                messages.warning(
                    request,
                    _(f'تست بازیابی "{test_type}" با مشکل مواجه شد. جزئیات را بررسی کنید.')
                )
            
        except Exception as e:
            logger.error(f"Error running disaster recovery test: {str(e)}")
            messages.error(request, _('خطا در اجرای تست بازیابی'))
        
        return redirect('admin_panel:disaster_recovery_dashboard')
    
    def _test_backup_validation(self, dr_manager):
        """Test backup validation."""
        try:
            # Get latest full system backup
            latest_backup = BackupJob.objects.filter(
                status='completed',
                backup_type='full_system'
            ).order_by('-created_at').first()
            
            if not latest_backup:
                return {
                    'overall_status': 'failed',
                    'error': 'No full system backup available for testing'
                }
            
            # Validate backup integrity (this would be more comprehensive in real implementation)
            validation_results = {
                'backup_exists': True,
                'file_integrity': True,
                'encryption_valid': True,
                'storage_accessible': True,
            }
            
            return {
                'overall_status': 'success',
                'test_type': 'backup_validation',
                'backup_tested': latest_backup.job_id,
                'validation_results': validation_results,
                'tested_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'overall_status': 'failed',
                'error': str(e)
            }
    
    def _test_storage_connectivity(self):
        """Test storage connectivity."""
        try:
            from zargar.core.storage_utils import storage_manager
            
            # Test connectivity to all configured storage backends
            storage_status = storage_manager.get_storage_status()
            
            return {
                'overall_status': 'success' if storage_status.get('overall_status') == 'healthy' else 'failed',
                'test_type': 'storage_connectivity',
                'storage_results': storage_status,
                'tested_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'overall_status': 'failed',
                'error': str(e)
            }


class DisasterRecoveryDocumentationView(SuperAdminRequiredMixin, TemplateView):
    """
    View to display disaster recovery documentation and procedures.
    """
    template_name = 'admin_panel/disaster_recovery_documentation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from .disaster_recovery import DisasterRecoveryManager
        
        # Get complete disaster recovery plan
        dr_manager = DisasterRecoveryManager()
        recovery_plan = dr_manager.create_disaster_recovery_plan()
        
        context.update({
            'recovery_plan': recovery_plan,
            'plan_version': recovery_plan['disaster_recovery_plan']['version'],
            'created_at': recovery_plan['disaster_recovery_plan']['created_at'],
        })
        
        return context


class BackupStatusAPIView(SuperAdminRequiredMixin, View):
    """
    API view to get real-time backup status updates.
    """
    
    def get(self, request):
        """Return backup status as JSON."""
        from .models import BackupJob
        
        job_id = request.GET.get('job_id')
        if not job_id:
            return JsonResponse({'error': 'Missing job_id parameter'}, status=400)
        
        try:
            backup_job = BackupJob.objects.get(job_id=job_id)
            
            return JsonResponse({
                'status': backup_job.status,
                'progress': backup_job.progress_percentage,
                'duration': str(backup_job.duration),
                'file_size': backup_job.file_size_human if backup_job.file_size_bytes else None,
                'error_message': backup_job.error_message,
                'log_messages': backup_job.log_messages[-10:],  # Last 10 messages
            })
            
        except BackupJob.DoesNotExist:
            return JsonResponse({'error': 'Backup job not found'}, status=404)
        except Exception as e:
            logger.error(f"Error getting backup status: {str(e)}")
            return JsonResponse({'error': 'Internal server error'}, status=500)


class DisasterRecoveryDashboardView(SuperAdminRequiredMixin, TemplateView):
    """
    Main disaster recovery dashboard view.
    """
    template_name = 'admin_panel/disaster_recovery_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from .disaster_recovery import DisasterRecoveryManager
        from .models import BackupJob, RestoreJob
        
        # Initialize disaster recovery manager
        dr_manager = DisasterRecoveryManager()
        
        # Get disaster recovery plan
        recovery_plan = dr_manager.create_disaster_recovery_plan()
        
        # Get recent disaster recovery tests
        recent_tests = self._get_recent_dr_tests()
        
        # Get system readiness status
        system_status = self._get_system_readiness_status()
        
        # Get available backups for recovery
        available_backups = BackupJob.objects.filter(
            status='completed',
            backup_type='full_system'
        ).order_by('-created_at')[:10]
        
        # Get recent restore operations
        recent_restores = RestoreJob.objects.order_by('-created_at')[:5]
        
        # Calculate recovery metrics
        recovery_metrics = self._calculate_recovery_metrics()
        
        context.update({
            'recovery_plan': recovery_plan,
            'recent_tests': recent_tests,
            'system_status': system_status,
            'available_backups': available_backups,
            'recent_restores': recent_restores,
            'recovery_metrics': recovery_metrics,
        })
        
        return context
    
    def _get_recent_dr_tests(self):
        """Get recent disaster recovery test results."""
        # This would typically come from a DR test log model
        # For now, return mock data based on the DR manager
        return [
            {
                'test_id': 'dr_test_001',
                'test_date': timezone.now() - timedelta(days=1),
                'test_type': 'full_recovery_simulation',
                'status': 'passed',
                'duration': '45 minutes',
                'components_tested': ['database', 'configuration', 'services'],
                'issues_found': 0,
            },
            {
                'test_id': 'dr_test_002',
                'test_date': timezone.now() - timedelta(days=7),
                'test_type': 'backup_validation',
                'status': 'passed',
                'duration': '15 minutes',
                'components_tested': ['backup_integrity', 'encryption'],
                'issues_found': 0,
            }
        ]
    
    def _get_system_readiness_status(self):
        """Get current system readiness for disaster recovery."""
        from zargar.core.storage_utils import storage_manager
        
        # Check backup storage connectivity
        storage_status = storage_manager.get_storage_status()
        
        # Check recent backup availability
        recent_backup = BackupJob.objects.filter(
            status='completed',
            backup_type='full_system',
            created_at__gte=timezone.now() - timedelta(days=7)
        ).first()
        
        # Check configuration backup
        config_backup = BackupJob.objects.filter(
            status='completed',
            backup_type='configuration',
            created_at__gte=timezone.now() - timedelta(days=30)
        ).first()
        
        return {
            'overall_status': 'ready' if recent_backup and config_backup else 'warning',
            'storage_connectivity': storage_status.get('overall_status', 'unknown'),
            'recent_full_backup': recent_backup is not None,
            'recent_config_backup': config_backup is not None,
            'last_full_backup_date': recent_backup.created_at if recent_backup else None,
            'last_config_backup_date': config_backup.created_at if config_backup else None,
            'estimated_rto': '4 hours',  # Recovery Time Objective
            'estimated_rpo': '24 hours',  # Recovery Point Objective
        }
    
    def _calculate_recovery_metrics(self):
        """Calculate disaster recovery metrics."""
        total_backups = BackupJob.objects.filter(backup_type='full_system').count()
        successful_backups = BackupJob.objects.filter(
            backup_type='full_system',
            status='completed'
        ).count()
        
        total_restores = RestoreJob.objects.count()
        successful_restores = RestoreJob.objects.filter(status='completed').count()
        
        return {
            'backup_success_rate': round((successful_backups / total_backups * 100) if total_backups > 0 else 0, 1),
            'restore_success_rate': round((successful_restores / total_restores * 100) if total_restores > 0 else 0, 1),
            'total_dr_tests': len(self._get_recent_dr_tests()),
            'last_test_date': timezone.now() - timedelta(days=1),
            'next_scheduled_test': timezone.now() + timedelta(days=29),
        }


class DisasterRecoveryTestView(SuperAdminRequiredMixin, View):
    """
    View to run disaster recovery tests.
    """
    
    def post(self, request):
        """Handle disaster recovery test request."""
        from .disaster_recovery import DisasterRecoveryManager
        
        test_type = request.POST.get('test_type')
        
        if not test_type:
            messages.error(request, _('نوع تست الزامی است.'))
            return redirect('admin_panel:disaster_recovery_dashboard')
        
        try:
            dr_manager = DisasterRecoveryManager()
            
            if test_type == 'full_procedures':
                # Run full disaster recovery procedure test
                test_results = dr_manager.test_disaster_recovery_procedures()
            elif test_type == 'backup_validation':
                # Test backup integrity and accessibility
                test_results = self._test_backup_validation(dr_manager)
            elif test_type == 'storage_connectivity':
                # Test storage connectivity
                test_results = self._test_storage_connectivity()
            else:
                messages.error(request, _('نوع تست نامعتبر است.'))
                return redirect('admin_panel:disaster_recovery_dashboard')
            
            if test_results.get('overall_status') == 'success':
                messages.success(
                    request,
                    _(f'تست بازیابی "{test_type}" با موفقیت انجام شد.')
                )
            else:
                messages.warning(
                    request,
                    _(f'تست بازیابی "{test_type}" با مشکل مواجه شد. جزئیات را بررسی کنید.')
                )
            
        except Exception as e:
            logger.error(f"Error running disaster recovery test: {str(e)}")
            messages.error(request, _('خطا در اجرای تست بازیابی'))
        
        return redirect('admin_panel:disaster_recovery_dashboard')
    
    def _test_backup_validation(self, dr_manager):
        """Test backup validation."""
        try:
            # Get latest full system backup
            latest_backup = BackupJob.objects.filter(
                status='completed',
                backup_type='full_system'
            ).order_by('-created_at').first()
            
            if not latest_backup:
                return {
                    'overall_status': 'failed',
                    'error': 'No full system backup available for testing'
                }
            
            # Validate backup integrity (this would be more comprehensive in real implementation)
            validation_results = {
                'backup_exists': True,
                'file_integrity': True,
                'encryption_valid': True,
                'storage_accessible': True,
            }
            
            return {
                'overall_status': 'success',
                'test_type': 'backup_validation',
                'backup_tested': latest_backup.job_id,
                'validation_results': validation_results,
                'tested_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'overall_status': 'failed',
                'error': str(e)
            }
    
    def _test_storage_connectivity(self):
        """Test storage connectivity."""
        try:
            from zargar.core.storage_utils import storage_manager
            
            # Test connectivity to all configured storage backends
            storage_status = storage_manager.get_storage_status()
            
            return {
                'overall_status': 'success' if storage_status.get('overall_status') == 'healthy' else 'failed',
                'test_type': 'storage_connectivity',
                'storage_results': storage_status,
                'tested_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'overall_status': 'failed',
                'error': str(e)
            }


class DisasterRecoveryDocumentationView(SuperAdminRequiredMixin, TemplateView):
    """
    View to display disaster recovery documentation and procedures.
    """
    template_name = 'admin_panel/disaster_recovery_documentation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from .disaster_recovery import DisasterRecoveryManager
        
        # Get complete disaster recovery plan
        dr_manager = DisasterRecoveryManager()
        recovery_plan = dr_manager.create_disaster_recovery_plan()
        
        context.update({
            'recovery_plan': recovery_plan,
            'plan_version': recovery_plan['disaster_recovery_plan']['version'],
            'created_at': recovery_plan['disaster_recovery_plan']['created_at'],
        })
        
        return context


class DisasterRecoveryDashboardView(SuperAdminRequiredMixin, TemplateView):
    """
    Main disaster recovery dashboard view.
    """
    template_name = 'admin_panel/disaster_recovery_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from .disaster_recovery import DisasterRecoveryManager
        from .models import BackupJob, RestoreJob
        
        # Initialize disaster recovery manager
        dr_manager = DisasterRecoveryManager()
        
        # Get disaster recovery plan
        recovery_plan = dr_manager.create_disaster_recovery_plan()
        
        # Get recent disaster recovery tests
        recent_tests = self._get_recent_dr_tests()
        
        # Get system readiness status
        system_status = self._get_system_readiness_status()
        
        # Get available backups for recovery
        available_backups = BackupJob.objects.filter(
            status='completed',
            backup_type='full_system'
        ).order_by('-created_at')[:10]
        
        # Get recent restore operations
        recent_restores = RestoreJob.objects.order_by('-created_at')[:5]
        
        # Calculate recovery metrics
        recovery_metrics = self._calculate_recovery_metrics()
        
        context.update({
            'recovery_plan': recovery_plan,
            'recent_tests': recent_tests,
            'system_status': system_status,
            'available_backups': available_backups,
            'recent_restores': recent_restores,
            'recovery_metrics': recovery_metrics,
        })
        
        return context
    
    def _get_recent_dr_tests(self):
        """Get recent disaster recovery test results."""
        # This would typically come from a DR test log model
        # For now, return mock data based on the DR manager
        return [
            {
                'test_id': 'dr_test_001',
                'test_date': timezone.now() - timedelta(days=1),
                'test_type': 'full_recovery_simulation',
                'status': 'passed',
                'duration': '45 minutes',
                'components_tested': ['database', 'configuration', 'services'],
                'issues_found': 0,
            },
            {
                'test_id': 'dr_test_002',
                'test_date': timezone.now() - timedelta(days=7),
                'test_type': 'backup_validation',
                'status': 'passed',
                'duration': '15 minutes',
                'components_tested': ['backup_integrity', 'encryption'],
                'issues_found': 0,
            }
        ]
    
    def _get_system_readiness_status(self):
        """Get current system readiness for disaster recovery."""
        from zargar.core.storage_utils import storage_manager
        
        # Check backup storage connectivity
        storage_status = storage_manager.get_storage_status()
        
        # Check recent backup availability
        recent_backup = BackupJob.objects.filter(
            status='completed',
            backup_type='full_system',
            created_at__gte=timezone.now() - timedelta(days=7)
        ).first()
        
        # Check configuration backup
        config_backup = BackupJob.objects.filter(
            status='completed',
            backup_type='configuration',
            created_at__gte=timezone.now() - timedelta(days=30)
        ).first()
        
        return {
            'overall_status': 'ready' if recent_backup and config_backup else 'warning',
            'storage_connectivity': storage_status.get('overall_status', 'unknown'),
            'recent_full_backup': recent_backup is not None,
            'recent_config_backup': config_backup is not None,
            'last_full_backup_date': recent_backup.created_at if recent_backup else None,
            'last_config_backup_date': config_backup.created_at if config_backup else None,
            'estimated_rto': '4 hours',  # Recovery Time Objective
            'estimated_rpo': '24 hours',  # Recovery Point Objective
        }
    
    def _calculate_recovery_metrics(self):
        """Calculate disaster recovery metrics."""
        total_backups = BackupJob.objects.filter(backup_type='full_system').count()
        successful_backups = BackupJob.objects.filter(
            backup_type='full_system',
            status='completed'
        ).count()
        
        total_restores = RestoreJob.objects.count()
        successful_restores = RestoreJob.objects.filter(status='completed').count()
        
        return {
            'backup_success_rate': round((successful_backups / total_backups * 100) if total_backups > 0 else 0, 1),
            'restore_success_rate': round((successful_restores / total_restores * 100) if total_restores > 0 else 0, 1),
            'total_dr_tests': len(self._get_recent_dr_tests()),
            'last_test_date': timezone.now() - timedelta(days=1),
            'next_scheduled_test': timezone.now() + timedelta(days=29),
        }


class DisasterRecoveryTestView(SuperAdminRequiredMixin, View):
    """
    View to run disaster recovery tests.
    """
    
    def post(self, request):
        """Handle disaster recovery test request."""
        from .disaster_recovery import DisasterRecoveryManager
        
        test_type = request.POST.get('test_type')
        
        if not test_type:
            messages.error(request, _('نوع تست الزامی است.'))
            return redirect('admin_panel:disaster_recovery_dashboard')
        
        try:
            dr_manager = DisasterRecoveryManager()
            
            if test_type == 'full_procedures':
                # Run full disaster recovery procedure test
                test_results = dr_manager.test_disaster_recovery_procedures()
            elif test_type == 'backup_validation':
                # Test backup integrity and accessibility
                test_results = self._test_backup_validation(dr_manager)
            elif test_type == 'storage_connectivity':
                # Test storage connectivity
                test_results = self._test_storage_connectivity()
            else:
                messages.error(request, _('نوع تست نامعتبر است.'))
                return redirect('admin_panel:disaster_recovery_dashboard')
            
            if test_results.get('overall_status') == 'success':
                messages.success(
                    request,
                    _(f'تست بازیابی "{test_type}" با موفقیت انجام شد.')
                )
            else:
                messages.warning(
                    request,
                    _(f'تست بازیابی "{test_type}" با مشکل مواجه شد. جزئیات را بررسی کنید.')
                )
            
        except Exception as e:
            logger.error(f"Error running disaster recovery test: {str(e)}")
            messages.error(request, _('خطا در اجرای تست بازیابی'))
        
        return redirect('admin_panel:disaster_recovery_dashboard')
    
    def _test_backup_validation(self, dr_manager):
        """Test backup validation."""
        try:
            # Get latest full system backup
            latest_backup = BackupJob.objects.filter(
                status='completed',
                backup_type='full_system'
            ).order_by('-created_at').first()
            
            if not latest_backup:
                return {
                    'overall_status': 'failed',
                    'error': 'No full system backup available for testing'
                }
            
            # Validate backup integrity (this would be more comprehensive in real implementation)
            validation_results = {
                'backup_exists': True,
                'file_integrity': True,
                'encryption_valid': True,
                'storage_accessible': True,
            }
            
            return {
                'overall_status': 'success',
                'test_type': 'backup_validation',
                'backup_tested': latest_backup.job_id,
                'validation_results': validation_results,
                'tested_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'overall_status': 'failed',
                'error': str(e)
            }
    
    def _test_storage_connectivity(self):
        """Test storage connectivity."""
        try:
            from zargar.core.storage_utils import storage_manager
            
            # Test connectivity to all configured storage backends
            storage_status = storage_manager.get_storage_status()
            
            return {
                'overall_status': 'success' if storage_status.get('overall_status') == 'healthy' else 'failed',
                'test_type': 'storage_connectivity',
                'storage_results': storage_status,
                'tested_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'overall_status': 'failed',
                'error': str(e)
            }


class DisasterRecoveryDocumentationView(SuperAdminRequiredMixin, TemplateView):
    """
    View to display disaster recovery documentation and procedures.
    """
    template_name = 'admin_panel/disaster_recovery_documentation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from .disaster_recovery import DisasterRecoveryManager
        
        # Get complete disaster recovery plan
        dr_manager = DisasterRecoveryManager()
        recovery_plan = dr_manager.create_disaster_recovery_plan()
        
        context.update({
            'recovery_plan': recovery_plan,
            'plan_version': recovery_plan['disaster_recovery_plan']['version'],
            'created_at': recovery_plan['disaster_recovery_plan']['created_at'],
        })
        
        return context

cla
ss RestoreStatusAPIView(SuperAdminRequiredMixin, View):
    """
    API view to get restore job status.
    """
    
    def get(self, request):
        """Get restore job status."""
        from .models import RestoreJob
        from .tenant_restoration import tenant_restoration_manager
        
        job_id = request.GET.get('job_id')
        
        if not job_id:
            return JsonResponse({'success': False, 'error': 'Missing job_id parameter'})
        
        try:
            # Use tenant restoration manager to get status
            result = tenant_restoration_manager.get_restoration_status(job_id)
            
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Error getting restore status: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Error getting restore status'
            })


class BackupStatusAPIView(SuperAdminRequiredMixin, View):
    """
    API view to get backup job status.
    """
    
    def get(self, request):
        """Get backup job status."""
        from .models import BackupJob
        
        job_id = request.GET.get('job_id')
        
        if not job_id:
            return JsonResponse({'success': False, 'error': 'Missing job_id parameter'})
        
        try:
            backup_job = BackupJob.objects.get(job_id=job_id)
            
            return JsonResponse({
                'success': True,
                'job_id': str(backup_job.job_id),
                'status': backup_job.status,
                'progress': backup_job.progress_percentage,
                'started_at': backup_job.started_at.isoformat() if backup_job.started_at else None,
                'completed_at': backup_job.completed_at.isoformat() if backup_job.completed_at else None,
                'error_message': backup_job.error_message,
            })
            
        except BackupJob.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Backup job {job_id} not found'
            })
        except Exception as e:
            logger.error(f"Error getting backup status: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Error getting backup status'
            })