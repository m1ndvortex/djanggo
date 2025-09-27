"""
Security dashboard views for zargar project.
"""
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.contrib import messages
import json

from .models import User
from .security_models import SecurityEvent, AuditLog, RateLimitAttempt, SuspiciousActivity
from .security_utils import SecurityMonitor


class SuperAdminRequiredMixin(LoginRequiredMixin):
    """
    Mixin to require super admin access for security dashboard.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not getattr(request.user, 'is_super_admin', False):
            messages.error(request, _('شما دسترسی به این بخش را ندارید.'))
            return self.handle_no_permission()
        
        return super().dispatch(request, *args, **kwargs)


class SecurityDashboardView(SuperAdminRequiredMixin, TemplateView):
    """
    Main security dashboard view showing overview of security events and alerts.
    """
    template_name = 'core/super_panel/security/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get time ranges
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)
        
        # Security events statistics
        context['security_stats'] = self.get_security_statistics(last_24h, last_7d, last_30d)
        
        # Recent critical events
        context['critical_events'] = SecurityEvent.objects.filter(
            severity='critical',
            created_at__gte=last_24h
        ).select_related('user').order_by('-created_at')[:5]
        
        # Unresolved security events
        context['unresolved_events'] = SecurityEvent.objects.filter(
            is_resolved=False,
            severity__in=['high', 'critical']
        ).count()
        
        # Top risk IPs
        context['risk_ips'] = self.get_top_risk_ips(last_7d)
        
        # Suspicious activities
        context['suspicious_activities'] = SuspiciousActivity.objects.filter(
            created_at__gte=last_24h,
            is_investigated=False
        ).select_related('user').order_by('-risk_level', '-created_at')[:5]
        
        # Rate limiting statistics
        context['rate_limit_stats'] = self.get_rate_limit_statistics(last_24h)
        
        # System security overview
        context['system_overview'] = SecurityMonitor.get_system_security_overview()
        
        return context
    
    def get_security_statistics(self, last_24h, last_7d, last_30d):
        """Get comprehensive security statistics."""
        stats = {}
        
        # Events by severity (last 24h)
        events_24h = SecurityEvent.objects.filter(created_at__gte=last_24h)
        stats['events_24h'] = {
            'total': events_24h.count(),
            'critical': events_24h.filter(severity='critical').count(),
            'high': events_24h.filter(severity='high').count(),
            'medium': events_24h.filter(severity='medium').count(),
            'low': events_24h.filter(severity='low').count(),
        }
        
        # Events by type (last 7d)
        events_7d = SecurityEvent.objects.filter(created_at__gte=last_7d)
        stats['events_by_type'] = list(
            events_7d.values('event_type').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
        )
        
        # Failed login attempts
        stats['failed_logins'] = {
            '24h': SecurityEvent.objects.filter(
                event_type='login_failed',
                created_at__gte=last_24h
            ).count(),
            '7d': SecurityEvent.objects.filter(
                event_type='login_failed',
                created_at__gte=last_7d
            ).count(),
        }
        
        # Blocked attempts
        stats['blocked_attempts'] = RateLimitAttempt.objects.filter(
            is_blocked=True,
            last_attempt__gte=last_24h
        ).count()
        
        # Suspicious activities
        stats['suspicious_activities'] = {
            'total': SuspiciousActivity.objects.filter(created_at__gte=last_24h).count(),
            'unresolved': SuspiciousActivity.objects.filter(
                created_at__gte=last_24h,
                is_investigated=False
            ).count(),
            'high_risk': SuspiciousActivity.objects.filter(
                created_at__gte=last_24h,
                risk_level__in=['high', 'critical']
            ).count(),
        }
        
        return stats
    
    def get_top_risk_ips(self, since):
        """Get top risk IP addresses."""
        return list(
            SecurityEvent.objects.filter(
                created_at__gte=since,
                severity__in=['high', 'critical']
            ).values('ip_address').annotate(
                event_count=Count('id'),
                risk_score=Count('id', filter=Q(severity='critical')) * 2 + 
                          Count('id', filter=Q(severity='high'))
            ).order_by('-risk_score')[:10]
        )
    
    def get_rate_limit_statistics(self, since):
        """Get rate limiting statistics."""
        return {
            'total_attempts': RateLimitAttempt.objects.filter(
                last_attempt__gte=since
            ).count(),
            'blocked_attempts': RateLimitAttempt.objects.filter(
                last_attempt__gte=since,
                is_blocked=True
            ).count(),
            'by_type': list(
                RateLimitAttempt.objects.filter(
                    last_attempt__gte=since
                ).values('limit_type').annotate(
                    total=Count('id'),
                    blocked=Count('id', filter=Q(is_blocked=True))
                ).order_by('-total')
            )
        }


class SecurityEventsListView(SuperAdminRequiredMixin, ListView):
    """
    List view for security events with filtering and search.
    """
    model = SecurityEvent
    template_name = 'core/super_panel/security/events_list.html'
    context_object_name = 'events'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = SecurityEvent.objects.select_related('user', 'resolved_by').order_by('-created_at')
        
        # Apply filters
        event_type = self.request.GET.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        severity = self.request.GET.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)
        
        is_resolved = self.request.GET.get('is_resolved')
        if is_resolved == 'true':
            queryset = queryset.filter(is_resolved=True)
        elif is_resolved == 'false':
            queryset = queryset.filter(is_resolved=False)
        
        # Date range filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search) |
                Q(username_attempted__icontains=search) |
                Q(ip_address__icontains=search) |
                Q(user_agent__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context['event_types'] = SecurityEvent.EVENT_TYPES
        context['severity_levels'] = SecurityEvent.SEVERITY_LEVELS
        
        # Current filters
        context['current_filters'] = {
            'event_type': self.request.GET.get('event_type', ''),
            'severity': self.request.GET.get('severity', ''),
            'is_resolved': self.request.GET.get('is_resolved', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'search': self.request.GET.get('search', ''),
        }
        
        return context


class SecurityEventDetailView(SuperAdminRequiredMixin, DetailView):
    """
    Detail view for individual security events.
    """
    model = SecurityEvent
    template_name = 'core/super_panel/security/event_detail.html'
    context_object_name = 'event'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get related events from same IP
        context['related_events'] = SecurityEvent.objects.filter(
            ip_address=self.object.ip_address
        ).exclude(id=self.object.id).order_by('-created_at')[:10]
        
        # Get user's recent events if user exists
        if self.object.user:
            context['user_events'] = SecurityEvent.objects.filter(
                user=self.object.user
            ).exclude(id=self.object.id).order_by('-created_at')[:10]
        
        return context


class SecurityEventResolveView(SuperAdminRequiredMixin, View):
    """
    View to resolve security events.
    """
    def post(self, request, pk):
        event = get_object_or_404(SecurityEvent, pk=pk)
        resolution_notes = request.POST.get('resolution_notes', '')
        
        event.resolve(resolved_by=request.user, notes=resolution_notes)
        
        messages.success(request, _('رویداد امنیتی با موفقیت حل شد.'))
        
        if request.headers.get('HX-Request'):
            return JsonResponse({'status': 'success', 'message': 'رویداد حل شد'})
        
        return redirect('core:security_event_detail', pk=pk)


class AuditLogsListView(SuperAdminRequiredMixin, ListView):
    """
    List view for audit logs with filtering and search.
    """
    model = AuditLog
    template_name = 'core/super_panel/security/audit_logs.html'
    context_object_name = 'logs'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = AuditLog.objects.select_related('user', 'content_type').order_by('-created_at')
        
        # Apply filters
        action = self.request.GET.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        model_name = self.request.GET.get('model_name')
        if model_name:
            queryset = queryset.filter(model_name=model_name)
        
        user_id = self.request.GET.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Date range filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search) |
                Q(object_repr__icontains=search) |
                Q(ip_address__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context['action_types'] = AuditLog.ACTION_TYPES
        context['model_names'] = AuditLog.objects.values_list('model_name', flat=True).distinct()
        context['users'] = User.objects.filter(
            id__in=AuditLog.objects.values_list('user_id', flat=True).distinct()
        )
        
        # Current filters
        context['current_filters'] = {
            'action': self.request.GET.get('action', ''),
            'model_name': self.request.GET.get('model_name', ''),
            'user_id': self.request.GET.get('user_id', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'search': self.request.GET.get('search', ''),
        }
        
        return context


class SuspiciousActivitiesListView(SuperAdminRequiredMixin, ListView):
    """
    List view for suspicious activities with investigation capabilities.
    """
    model = SuspiciousActivity
    template_name = 'core/super_panel/security/suspicious_activities.html'
    context_object_name = 'activities'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = SuspiciousActivity.objects.select_related(
            'user', 'investigated_by'
        ).prefetch_related('related_events').order_by('-created_at')
        
        # Apply filters
        activity_type = self.request.GET.get('activity_type')
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        
        risk_level = self.request.GET.get('risk_level')
        if risk_level:
            queryset = queryset.filter(risk_level=risk_level)
        
        is_investigated = self.request.GET.get('is_investigated')
        if is_investigated == 'true':
            queryset = queryset.filter(is_investigated=True)
        elif is_investigated == 'false':
            queryset = queryset.filter(is_investigated=False)
        
        is_false_positive = self.request.GET.get('is_false_positive')
        if is_false_positive == 'true':
            queryset = queryset.filter(is_false_positive=True)
        elif is_false_positive == 'false':
            queryset = queryset.filter(is_false_positive=False)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search) |
                Q(ip_address__icontains=search) |
                Q(user_agent__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context['activity_types'] = SuspiciousActivity.ACTIVITY_TYPES
        context['risk_levels'] = SuspiciousActivity.RISK_LEVELS
        
        # Current filters
        context['current_filters'] = {
            'activity_type': self.request.GET.get('activity_type', ''),
            'risk_level': self.request.GET.get('risk_level', ''),
            'is_investigated': self.request.GET.get('is_investigated', ''),
            'is_false_positive': self.request.GET.get('is_false_positive', ''),
            'search': self.request.GET.get('search', ''),
        }
        
        return context


class SuspiciousActivityInvestigateView(SuperAdminRequiredMixin, View):
    """
    View to investigate suspicious activities.
    """
    def post(self, request, pk):
        activity = get_object_or_404(SuspiciousActivity, pk=pk)
        investigation_notes = request.POST.get('investigation_notes', '')
        is_false_positive = request.POST.get('is_false_positive') == 'true'
        
        activity.is_investigated = True
        activity.investigated_by = request.user
        activity.investigated_at = timezone.now()
        activity.investigation_notes = investigation_notes
        activity.is_false_positive = is_false_positive
        activity.save()
        
        status = 'false positive' if is_false_positive else 'legitimate threat'
        messages.success(request, f'فعالیت مشکوک به عنوان {status} بررسی شد.')
        
        if request.headers.get('HX-Request'):
            return JsonResponse({'status': 'success', 'message': 'بررسی انجام شد'})
        
        return redirect('core:suspicious_activities')


class SecurityAlertsAPIView(SuperAdminRequiredMixin, View):
    """
    API endpoint for real-time security alerts.
    """
    def get(self, request):
        # Get recent unresolved critical events
        critical_events = SecurityEvent.objects.filter(
            severity='critical',
            is_resolved=False,
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        # Get unresolved suspicious activities
        suspicious_activities = SuspiciousActivity.objects.filter(
            is_investigated=False,
            risk_level__in=['high', 'critical'],
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        # Get blocked attempts
        blocked_attempts = RateLimitAttempt.objects.filter(
            is_blocked=True,
            last_attempt__gte=timezone.now() - timedelta(minutes=30)
        ).count()
        
        alerts = []
        
        if critical_events > 0:
            alerts.append({
                'type': 'critical',
                'message': f'{critical_events} رویداد امنیتی بحرانی نیاز به بررسی دارد',
                'count': critical_events,
                'url': '/admin/security/events/?severity=critical&is_resolved=false'
            })
        
        if suspicious_activities > 0:
            alerts.append({
                'type': 'warning',
                'message': f'{suspicious_activities} فعالیت مشکوک نیاز به بررسی دارد',
                'count': suspicious_activities,
                'url': '/admin/security/suspicious-activities/?is_investigated=false'
            })
        
        if blocked_attempts > 0:
            alerts.append({
                'type': 'info',
                'message': f'{blocked_attempts} تلاش مسدود شده در ۳۰ دقیقه گذشته',
                'count': blocked_attempts,
                'url': '/admin/security/rate-limits/'
            })
        
        return JsonResponse({
            'alerts': alerts,
            'total_alerts': len(alerts),
            'timestamp': timezone.now().isoformat()
        })


class RateLimitAttemptsListView(SuperAdminRequiredMixin, ListView):
    """
    List view for rate limit attempts.
    """
    model = RateLimitAttempt
    template_name = 'core/super_panel/security/rate_limits.html'
    context_object_name = 'attempts'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = RateLimitAttempt.objects.order_by('-last_attempt')
        
        # Apply filters
        limit_type = self.request.GET.get('limit_type')
        if limit_type:
            queryset = queryset.filter(limit_type=limit_type)
        
        is_blocked = self.request.GET.get('is_blocked')
        if is_blocked == 'true':
            queryset = queryset.filter(is_blocked=True)
        elif is_blocked == 'false':
            queryset = queryset.filter(is_blocked=False)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(identifier__icontains=search) |
                Q(endpoint__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context['limit_types'] = RateLimitAttempt.LIMIT_TYPES
        
        # Current filters
        context['current_filters'] = {
            'limit_type': self.request.GET.get('limit_type', ''),
            'is_blocked': self.request.GET.get('is_blocked', ''),
            'search': self.request.GET.get('search', ''),
        }
        
        return context


class UnblockRateLimitView(SuperAdminRequiredMixin, View):
    """
    View to unblock rate limited identifiers.
    """
    def post(self, request, pk):
        attempt = get_object_or_404(RateLimitAttempt, pk=pk)
        
        attempt.is_blocked = False
        attempt.blocked_until = None
        attempt.save()
        
        messages.success(request, f'شناسه {attempt.identifier} از حالت مسدود خارج شد.')
        
        if request.headers.get('HX-Request'):
            return JsonResponse({'status': 'success', 'message': 'مسدودیت برداشته شد'})
        
        return redirect('core:rate_limits')