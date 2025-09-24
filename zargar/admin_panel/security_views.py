"""
Security dashboard views for the super-admin panel.
Provides security monitoring, audit management, and threat visualization.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, ListView, View
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Sum, Q
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta, datetime
import logging

from zargar.tenants.admin_models import (
    PublicSecurityEvent, 
    PublicAuditLog, 
    PublicRateLimitAttempt, 
    PublicSuspiciousActivity
)
from .views import SuperAdminRequiredMixin

logger = logging.getLogger(__name__)


class SecurityDashboardView(SuperAdminRequiredMixin, TemplateView):
    """
    Main security dashboard with real-time metrics and threat visualization.
    """
    template_name = 'admin_panel/security_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate time ranges
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)
        
        # Security metrics for the last 24 hours
        security_metrics = self._get_security_metrics(last_24h, now)
        
        # Recent security events (last 10)
        recent_events = PublicSecurityEvent.objects.filter(
            created_at__gte=last_24h
        ).order_by('-created_at')[:10]
        
        # Active threats (unresolved high/critical events)
        active_threats = PublicSecurityEvent.objects.filter(
            severity__in=['high', 'critical'],
            is_resolved=False
        ).order_by('-created_at')[:5]
        
        # Suspicious activities requiring investigation
        suspicious_activities = PublicSuspiciousActivity.objects.filter(
            is_investigated=False,
            risk_level__in=['high', 'critical']
        ).order_by('-created_at')[:5]
        
        # Security trends (7-day comparison)
        security_trends = self._get_security_trends(last_7d, now)
        
        # Top threat sources (by IP)
        threat_sources = self._get_threat_sources(last_7d)
        
        # System security status
        security_status = self._calculate_security_status(security_metrics)
        
        context.update({
            'security_metrics': security_metrics,
            'recent_events': recent_events,
            'active_threats': active_threats,
            'suspicious_activities': suspicious_activities,
            'security_trends': security_trends,
            'threat_sources': threat_sources,
            'security_status': security_status,
        })
        
        return context
    
    def _get_security_metrics(self, start_time, end_time):
        """Calculate security metrics for the given time range."""
        
        # Failed login attempts
        failed_logins = PublicSecurityEvent.objects.filter(
            event_type='login_failed',
            created_at__gte=start_time,
            created_at__lte=end_time
        ).count()
        
        # Blocked IPs (rate limited)
        blocked_ips = PublicRateLimitAttempt.objects.filter(
            is_blocked=True,
            window_start__gte=start_time
        ).values('identifier').distinct().count()
        
        # Suspicious activities detected
        suspicious_count = PublicSuspiciousActivity.objects.filter(
            created_at__gte=start_time,
            created_at__lte=end_time
        ).count()
        
        # Critical security events
        critical_events = PublicSecurityEvent.objects.filter(
            severity='critical',
            created_at__gte=start_time,
            created_at__lte=end_time
        ).count()
        
        # High severity events
        high_events = PublicSecurityEvent.objects.filter(
            severity='high',
            created_at__gte=start_time,
            created_at__lte=end_time
        ).count()
        
        # Brute force attempts
        brute_force = PublicSecurityEvent.objects.filter(
            event_type='brute_force_attempt',
            created_at__gte=start_time,
            created_at__lte=end_time
        ).count()
        
        # Unauthorized access attempts
        unauthorized_access = PublicSecurityEvent.objects.filter(
            event_type='unauthorized_access',
            created_at__gte=start_time,
            created_at__lte=end_time
        ).count()
        
        return {
            'failed_logins': failed_logins,
            'blocked_ips': blocked_ips,
            'suspicious_activities': suspicious_count,
            'critical_events': critical_events,
            'high_events': high_events,
            'brute_force_attempts': brute_force,
            'unauthorized_access': unauthorized_access,
            'total_events': failed_logins + suspicious_count + critical_events + high_events,
        }
    
    def _get_security_trends(self, start_time, end_time):
        """Calculate security trends over the time period."""
        
        # Get daily event counts
        daily_events = []
        current_date = start_time.date()
        end_date = end_time.date()
        
        while current_date <= end_date:
            day_start = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
            day_end = day_start + timedelta(days=1)
            
            events_count = PublicSecurityEvent.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end
            ).count()
            
            daily_events.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'date_persian': current_date.strftime('%d/%m'),
                'events': events_count
            })
            
            current_date += timedelta(days=1)
        
        return daily_events
    
    def _get_threat_sources(self, start_time):
        """Get top threat sources by IP address."""
        
        threat_sources = PublicSecurityEvent.objects.filter(
            created_at__gte=start_time,
            severity__in=['high', 'critical']
        ).values('ip_address').annotate(
            threat_count=Count('id')
        ).order_by('-threat_count')[:10]
        
        return list(threat_sources)
    
    def _calculate_security_status(self, metrics):
        """Calculate overall security status based on metrics."""
        
        # Define thresholds
        critical_threshold = 5
        high_threshold = 10
        suspicious_threshold = 20
        
        if metrics['critical_events'] >= critical_threshold:
            return {
                'level': 'critical',
                'text': 'بحرانی',
                'description': 'تهدیدات بحرانی شناسایی شده',
                'color': 'red'
            }
        elif metrics['high_events'] >= high_threshold:
            return {
                'level': 'high',
                'text': 'خطر بالا',
                'description': 'تهدیدات با اولویت بالا موجود',
                'color': 'orange'
            }
        elif metrics['suspicious_activities'] >= suspicious_threshold:
            return {
                'level': 'warning',
                'text': 'هشدار',
                'description': 'فعالیت‌های مشکوک شناسایی شده',
                'color': 'yellow'
            }
        else:
            return {
                'level': 'normal',
                'text': 'عادی',
                'description': 'وضعیت امنیتی مطلوب',
                'color': 'green'
            }


class SecurityMetricsAPIView(SuperAdminRequiredMixin, View):
    """
    API endpoint for real-time security metrics updates.
    """
    
    def get(self, request):
        """Return current security metrics as JSON."""
        try:
            now = timezone.now()
            last_24h = now - timedelta(hours=24)
            
            # Get security dashboard view instance to reuse methods
            dashboard_view = SecurityDashboardView()
            metrics = dashboard_view._get_security_metrics(last_24h, now)
            security_status = dashboard_view._calculate_security_status(metrics)
            
            # Get recent events count by severity
            severity_counts = PublicSecurityEvent.objects.filter(
                created_at__gte=last_24h
            ).values('severity').annotate(count=Count('id'))
            
            severity_data = {item['severity']: item['count'] for item in severity_counts}
            
            return JsonResponse({
                'success': True,
                'metrics': metrics,
                'security_status': security_status,
                'severity_breakdown': severity_data,
                'timestamp': now.isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error fetching security metrics: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'خطا در دریافت آمار امنیتی'
            }, status=500)


class SecurityTrendsAPIView(SuperAdminRequiredMixin, View):
    """
    API endpoint for security trends data.
    """
    
    def get(self, request):
        """Return security trends data for charts."""
        try:
            days = int(request.GET.get('days', 7))
            now = timezone.now()
            start_time = now - timedelta(days=days)
            
            dashboard_view = SecurityDashboardView()
            trends = dashboard_view._get_security_trends(start_time, now)
            
            return JsonResponse({
                'success': True,
                'trends': trends,
                'period': f'{days} روز گذشته'
            })
            
        except Exception as e:
            logger.error(f"Error fetching security trends: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'خطا در دریافت روند امنیتی'
            }, status=500)


class SecurityEventResolveView(SuperAdminRequiredMixin, View):
    """
    View to resolve security events.
    """
    
    def post(self, request):
        """Mark security event as resolved."""
        try:
            event_id = request.POST.get('event_id')
            resolution_notes = request.POST.get('notes', '')
            
            if not event_id:
                return JsonResponse({
                    'success': False,
                    'error': 'شناسه رویداد مشخص نشده'
                }, status=400)
            
            event = get_object_or_404(PublicSecurityEvent, id=event_id)
            
            # Mark as resolved
            event.is_resolved = True
            event.resolved_at = timezone.now()
            event.resolution_notes = resolution_notes
            event.save()
            
            # Log the resolution action
            PublicAuditLog.log_action(
                action='security_event_resolve',
                content_object=event,
                request=request,
                details={
                    'event_type': event.event_type,
                    'severity': event.severity,
                    'resolution_notes': resolution_notes,
                }
            )
            
            messages.success(request, f'رویداد امنیتی با موفقیت حل شد.')
            
            return JsonResponse({
                'success': True,
                'message': 'رویداد امنیتی حل شد'
            })
            
        except Exception as e:
            logger.error(f"Error resolving security event: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'خطا در حل رویداد امنیتی'
            }, status=500)


class SuspiciousActivityInvestigateView(SuperAdminRequiredMixin, View):
    """
    View to investigate suspicious activities.
    """
    
    def post(self, request):
        """Mark suspicious activity as investigated."""
        try:
            activity_id = request.POST.get('activity_id')
            investigation_notes = request.POST.get('notes', '')
            is_false_positive = request.POST.get('false_positive') == 'true'
            
            if not activity_id:
                return JsonResponse({
                    'success': False,
                    'error': 'شناسه فعالیت مشخص نشده'
                }, status=400)
            
            activity = get_object_or_404(PublicSuspiciousActivity, id=activity_id)
            
            # Mark as investigated
            activity.is_investigated = True
            activity.investigated_at = timezone.now()
            activity.investigation_notes = investigation_notes
            activity.is_false_positive = is_false_positive
            activity.save()
            
            # Log the investigation action
            PublicAuditLog.log_action(
                action='suspicious_activity_investigate',
                content_object=activity,
                request=request,
                details={
                    'activity_type': activity.activity_type,
                    'risk_level': activity.risk_level,
                    'is_false_positive': is_false_positive,
                    'investigation_notes': investigation_notes,
                }
            )
            
            status_text = 'مثبت کاذب' if is_false_positive else 'تایید شده'
            messages.success(request, f'فعالیت مشکوک بررسی شد: {status_text}')
            
            return JsonResponse({
                'success': True,
                'message': f'فعالیت مشکوک بررسی شد: {status_text}'
            })
            
        except Exception as e:
            logger.error(f"Error investigating suspicious activity: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'خطا در بررسی فعالیت مشکوک'
            }, status=500)


class SecurityEventManagementView(SuperAdminRequiredMixin, TemplateView):
    """
    Main security event management interface with filtering, categorization, and investigation workflow.
    """
    template_name = 'admin_panel/security/security_events.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Import the backend service
        from .security_event_services_public import PublicSecurityEventFilterService
        
        # Get filter parameters from request
        is_resolved_param = self.request.GET.get('is_resolved')
        is_resolved = None
        if is_resolved_param:
            is_resolved = is_resolved_param.lower() == 'true'
        
        filters = {
            'event_type': self.request.GET.get('event_type'),
            'severity': self.request.GET.get('severity'),
            'is_resolved': is_resolved,
            'search_query': self.request.GET.get('search'),
            'page': int(self.request.GET.get('page', 1)),
            'per_page': 25,
        }
        
        # Handle date filters
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            try:
                filters['date_from'] = timezone.datetime.strptime(date_from, '%Y-%m-%d').replace(tzinfo=timezone.get_current_timezone())
            except ValueError:
                pass
        
        if date_to:
            try:
                filters['date_to'] = timezone.datetime.strptime(date_to, '%Y-%m-%d').replace(tzinfo=timezone.get_current_timezone())
            except ValueError:
                pass
        
        # Get filtered events
        events, metadata = PublicSecurityEventFilterService.get_filtered_events(**filters)
        
        # Get event statistics
        stats = PublicSecurityEventFilterService.get_event_statistics()
        
        # Get severity distribution
        severity_stats = PublicSecurityEvent.objects.values('severity').annotate(
            count=Count('id')
        ).order_by('severity')
        
        # Get event type choices for filter dropdown
        event_type_choices = PublicSecurityEvent.EVENT_TYPES
        severity_choices = PublicSecurityEvent.SEVERITY_LEVELS
        
        # Get recent unresolved critical/high events for quick action
        critical_events = PublicSecurityEvent.objects.filter(
            severity__in=['critical', 'high'],
            is_resolved=False
        ).order_by('-created_at')[:5]
        
        context.update({
            'events': events,
            'metadata': metadata,
            'stats': stats,
            'severity_stats': list(severity_stats),
            'critical_events': critical_events,
            'event_type_choices': event_type_choices,
            'severity_choices': severity_choices,
            'current_filters': {
                'event_type': filters.get('event_type', ''),
                'severity': filters.get('severity', ''),
                'is_resolved': self.request.GET.get('is_resolved', ''),
                'search': filters.get('search_query', ''),
                'date_from': self.request.GET.get('date_from', ''),
                'date_to': self.request.GET.get('date_to', ''),
            }
        })
        
        return context


class SecurityEventDetailView(SuperAdminRequiredMixin, TemplateView):
    """
    Detailed view for individual security events with investigation workflow.
    """
    template_name = 'admin_panel/security/security_event_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        event_id = kwargs.get('event_id')
        event = get_object_or_404(PublicSecurityEvent, id=event_id)
        
        # Get related events from same IP or user
        related_events = PublicSecurityEvent.objects.filter(
            Q(ip_address=event.ip_address) | Q(username_attempted=event.username_attempted)
        ).exclude(id=event.id).order_by('-created_at')[:10]
        
        # Get investigation history from audit logs
        investigation_history = PublicAuditLog.objects.filter(
            model_name='publicsecurityevent',
            object_id=str(event.id)
        ).order_by('-created_at')
        
        context.update({
            'event': event,
            'related_events': related_events,
            'investigation_history': investigation_history,
        })
        
        return context


class SecurityEventInvestigateView(SuperAdminRequiredMixin, View):
    """
    View to handle security event investigation workflow.
    """
    
    def post(self, request):
        """Handle investigation actions for security events."""
        try:
            event_id = request.POST.get('event_id')
            action = request.POST.get('action')  # 'investigate', 'resolve', 'escalate'
            notes = request.POST.get('notes', '')
            assigned_to = request.POST.get('assigned_to', '')
            
            if not event_id or not action:
                return JsonResponse({
                    'success': False,
                    'error': 'پارامترهای مورد نیاز مشخص نشده'
                }, status=400)
            
            event = get_object_or_404(PublicSecurityEvent, id=event_id)
            
            # Handle different investigation actions
            if action == 'investigate':
                # Mark as under investigation
                event.details = event.details or {}
                event.details['investigation_status'] = 'under_investigation'
                event.details['investigation_started_at'] = timezone.now().isoformat()
                event.details['investigation_notes'] = notes
                event.details['assigned_to'] = assigned_to
                event.save()
                
                # Log the investigation action
                PublicAuditLog.log_action(
                    action='security_event_investigate_start',
                    content_object=event,
                    request=request,
                    details={
                        'event_type': event.event_type,
                        'severity': event.severity,
                        'investigation_notes': notes,
                        'assigned_to': assigned_to,
                    }
                )
                
                message = 'بررسی رویداد امنیتی آغاز شد'
                
            elif action == 'resolve':
                # Mark as resolved
                event.is_resolved = True
                event.resolved_at = timezone.now()
                event.resolution_notes = notes
                event.details = event.details or {}
                event.details['investigation_status'] = 'resolved'
                event.save()
                
                # Log the resolution action
                PublicAuditLog.log_action(
                    action='security_event_resolve',
                    content_object=event,
                    request=request,
                    details={
                        'event_type': event.event_type,
                        'severity': event.severity,
                        'resolution_notes': notes,
                    }
                )
                
                message = 'رویداد امنیتی حل شد'
                
            elif action == 'escalate':
                # Escalate severity
                old_severity = event.severity
                if event.severity == 'low':
                    event.severity = 'medium'
                elif event.severity == 'medium':
                    event.severity = 'high'
                elif event.severity == 'high':
                    event.severity = 'critical'
                
                event.details = event.details or {}
                event.details['escalated_from'] = old_severity
                event.details['escalation_reason'] = notes
                event.details['escalated_at'] = timezone.now().isoformat()
                event.save()
                
                # Log the escalation action
                PublicAuditLog.log_action(
                    action='security_event_escalate',
                    content_object=event,
                    request=request,
                    details={
                        'event_type': event.event_type,
                        'old_severity': old_severity,
                        'new_severity': event.severity,
                        'escalation_reason': notes,
                    }
                )
                
                message = f'رویداد امنیتی از {old_severity} به {event.severity} ارتقا یافت'
            
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'عملیات نامعتبر'
                }, status=400)
            
            messages.success(request, message)
            
            return JsonResponse({
                'success': True,
                'message': message,
                'event_status': {
                    'is_resolved': event.is_resolved,
                    'severity': event.severity,
                    'investigation_status': event.details.get('investigation_status', 'pending')
                }
            })
            
        except Exception as e:
            logger.error(f"Error handling security event investigation: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'خطا در بررسی رویداد امنیتی'
            }, status=500)


class SecurityEventBulkActionView(SuperAdminRequiredMixin, View):
    """
    View to handle bulk actions on security events.
    """
    
    def post(self, request):
        """Handle bulk actions on selected security events."""
        try:
            event_ids = request.POST.getlist('event_ids')
            action = request.POST.get('action')
            notes = request.POST.get('notes', '')
            
            if not event_ids or not action:
                return JsonResponse({
                    'success': False,
                    'error': 'رویدادها یا عملیات انتخاب نشده'
                }, status=400)
            
            events = PublicSecurityEvent.objects.filter(id__in=event_ids)
            
            if not events.exists():
                return JsonResponse({
                    'success': False,
                    'error': 'رویداد امنیتی یافت نشد'
                }, status=404)
            
            updated_count = 0
            
            if action == 'resolve_all':
                # Resolve all selected events
                for event in events:
                    if not event.is_resolved:
                        event.is_resolved = True
                        event.resolved_at = timezone.now()
                        event.resolution_notes = notes
                        event.save()
                        updated_count += 1
                        
                        # Log each resolution
                        PublicAuditLog.log_action(
                            action='security_event_bulk_resolve',
                            content_object=event,
                            request=request,
                            details={
                                'event_type': event.event_type,
                                'severity': event.severity,
                                'bulk_action': True,
                                'resolution_notes': notes,
                            }
                        )
                
                message = f'{updated_count} رویداد امنیتی حل شد'
                
            elif action == 'mark_investigated':
                # Mark all as investigated
                for event in events:
                    event.details = event.details or {}
                    event.details['investigation_status'] = 'investigated'
                    event.details['bulk_investigation_notes'] = notes
                    event.details['investigated_at'] = timezone.now().isoformat()
                    event.save()
                    updated_count += 1
                    
                    # Log each investigation
                    PublicAuditLog.log_action(
                        action='security_event_bulk_investigate',
                        content_object=event,
                        request=request,
                        details={
                            'event_type': event.event_type,
                            'severity': event.severity,
                            'bulk_action': True,
                            'investigation_notes': notes,
                        }
                    )
                
                message = f'{updated_count} رویداد امنیتی بررسی شد'
                
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'عملیات نامعتبر'
                }, status=400)
            
            messages.success(request, message)
            
            return JsonResponse({
                'success': True,
                'message': message,
                'updated_count': updated_count
            })
            
        except Exception as e:
            logger.error(f"Error handling bulk security event action: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'خطا در عملیات گروهی'
            }, status=500)