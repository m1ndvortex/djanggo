"""
Audit log management views for the super admin panel.
Provides comprehensive audit log viewing, filtering, searching, and export functionality.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, View
from django.http import JsonResponse, HttpResponse, Http404
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from datetime import datetime, timedelta
import json
import logging

from zargar.tenants.admin_models import PublicAuditLog
from .views import SuperAdminRequiredMixin
from .audit_services import (
    AuditLogFilterService,
    AuditLogDetailService,
    AuditLogExportService,
    AuditLogSearchService
)

logger = logging.getLogger(__name__)


class AuditLogListView(SuperAdminRequiredMixin, ListView):
    """
    Main audit log list view with filtering and search capabilities.
    """
    model = PublicAuditLog
    template_name = 'admin_panel/security/audit_logs.html'
    context_object_name = 'audit_logs'
    paginate_by = 50
    
    def get_queryset(self):
        """Get filtered queryset based on request parameters."""
        try:
            # Get filter parameters from request
            filters = {
                'action': self.request.GET.get('action', ''),
                'model_name': self.request.GET.get('model_name', ''),
                'user_id': self.request.GET.get('user_id', ''),
                'username': self.request.GET.get('username', ''),
                'tenant_schema': self.request.GET.get('tenant_schema', ''),
                'ip_address': self.request.GET.get('ip_address', ''),
                'date_from': self.request.GET.get('date_from', ''),
                'date_to': self.request.GET.get('date_to', ''),
                'time_from': self.request.GET.get('time_from', ''),
                'time_to': self.request.GET.get('time_to', ''),
                'content_type_id': self.request.GET.get('content_type_id', ''),
                'object_id': self.request.GET.get('object_id', ''),
                'search': self.request.GET.get('search', ''),
                'integrity_status': self.request.GET.get('integrity_status', ''),
            }
            
            # Remove empty filters
            filters = {k: v for k, v in filters.items() if v}
            
            # Use filter service to get queryset
            filter_service = AuditLogFilterService()
            queryset = filter_service.get_filtered_queryset(filters)
            
            return queryset
            
        except Exception as e:
            logger.error(f"Error filtering audit logs: {str(e)}")
            try:
                messages.error(self.request, 'خطا در فیلتر کردن لاگ‌های حسابرسی')
            except:
                pass
            return PublicAuditLog.objects.none()
    
    def get_context_data(self, **kwargs):
        """Add filter options and current filters to context."""
        context = super().get_context_data(**kwargs)
        
        try:
            # Get filter options
            filter_service = AuditLogFilterService()
            filter_options = filter_service.get_filter_options()
            
            # Current filters for form persistence
            current_filters = {
                'action': self.request.GET.get('action', ''),
                'model_name': self.request.GET.get('model_name', ''),
                'user_id': self.request.GET.get('user_id', ''),
                'username': self.request.GET.get('username', ''),
                'tenant_schema': self.request.GET.get('tenant_schema', ''),
                'ip_address': self.request.GET.get('ip_address', ''),
                'date_from': self.request.GET.get('date_from', ''),
                'date_to': self.request.GET.get('date_to', ''),
                'time_from': self.request.GET.get('time_from', ''),
                'time_to': self.request.GET.get('time_to', ''),
                'content_type_id': self.request.GET.get('content_type_id', ''),
                'object_id': self.request.GET.get('object_id', ''),
                'search': self.request.GET.get('search', ''),
                'integrity_status': self.request.GET.get('integrity_status', ''),
            }
            
            # Calculate statistics
            total_logs = self.get_queryset().count()
            all_logs_count = PublicAuditLog.objects.count()
            
            # Recent activity summary (last 24 hours)
            last_24h = timezone.now() - timedelta(hours=24)
            recent_activity = PublicAuditLog.objects.filter(
                created_at__gte=last_24h
            ).values('action').annotate(count=Count('id')).order_by('-count')[:5]
            
            context.update({
                'filter_options': filter_options,
                'current_filters': current_filters,
                'total_filtered_logs': total_logs,
                'total_all_logs': all_logs_count,
                'recent_activity': recent_activity,
                'has_filters': any(current_filters.values()),
                'integrity_status_choices': [
                    ('', 'همه'),
                    ('verified', 'تایید شده'),
                    ('compromised', 'مشکوک'),
                ],
            })
            
        except Exception as e:
            logger.error(f"Error preparing audit log context: {str(e)}")
            messages.error(self.request, 'خطا در آماده‌سازی اطلاعات')
        
        return context


class AuditLogDetailView(SuperAdminRequiredMixin, DetailView):
    """
    Detailed view for a specific audit log entry with integrity verification.
    """
    model = PublicAuditLog
    template_name = 'admin_panel/security/audit_log_detail.html'
    context_object_name = 'audit_log'
    pk_url_kwarg = 'log_id'
    
    def get_object(self, queryset=None):
        """Get audit log object with error handling."""
        try:
            log_id = self.kwargs.get('log_id')
            return get_object_or_404(PublicAuditLog, id=log_id)
        except Exception as e:
            logger.error(f"Error retrieving audit log {log_id}: {str(e)}")
            raise Http404("لاگ حسابرسی یافت نشد")
    
    def get_context_data(self, **kwargs):
        """Add detailed audit log information to context."""
        context = super().get_context_data(**kwargs)
        
        try:
            log_entry = self.get_object()
            
            # Get detailed information using service
            detail_service = AuditLogDetailService()
            detail_info = detail_service.get_audit_log_detail(log_entry.id)
            
            if detail_info:
                context.update(detail_info)
            else:
                messages.error(self.request, 'خطا در دریافت جزئیات لاگ حسابرسی')
            
            # Add navigation context
            context['can_navigate'] = True
            
        except Exception as e:
            logger.error(f"Error preparing audit log detail context: {str(e)}")
            messages.error(self.request, 'خطا در آماده‌سازی جزئیات')
        
        return context


class AuditLogExportView(SuperAdminRequiredMixin, View):
    """
    View for exporting audit logs in various formats.
    """
    
    def get(self, request):
        """Handle audit log export requests."""
        try:
            export_format = request.GET.get('format', 'csv')
            
            # Get the same filters as the list view
            filters = {
                'action': request.GET.get('action', ''),
                'model_name': request.GET.get('model_name', ''),
                'user_id': request.GET.get('user_id', ''),
                'username': request.GET.get('username', ''),
                'tenant_schema': request.GET.get('tenant_schema', ''),
                'ip_address': request.GET.get('ip_address', ''),
                'date_from': request.GET.get('date_from', ''),
                'date_to': request.GET.get('date_to', ''),
                'time_from': request.GET.get('time_from', ''),
                'time_to': request.GET.get('time_to', ''),
                'content_type_id': request.GET.get('content_type_id', ''),
                'object_id': request.GET.get('object_id', ''),
                'search': request.GET.get('search', ''),
                'integrity_status': request.GET.get('integrity_status', ''),
            }
            
            # Remove empty filters
            filters = {k: v for k, v in filters.items() if v}
            
            # Get filtered queryset
            filter_service = AuditLogFilterService()
            queryset = filter_service.get_filtered_queryset(filters)
            
            # Limit export size for performance
            max_export_size = 10000
            if queryset.count() > max_export_size:
                messages.warning(
                    request, 
                    f'تعداد رکوردها بیش از حد مجاز ({max_export_size}) است. لطفاً فیلترهای بیشتری اعمال کنید.'
                )
                return JsonResponse({
                    'success': False,
                    'error': f'تعداد رکوردها بیش از حد مجاز ({max_export_size}) است'
                }, status=400)
            
            # Generate filename
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            
            # Export based on format
            export_service = AuditLogExportService()
            
            if export_format == 'csv':
                filename = f'audit_logs_{timestamp}.csv'
                return export_service.export_to_csv(queryset, filename)
            elif export_format == 'json':
                filename = f'audit_logs_{timestamp}.json'
                return export_service.export_to_json(queryset, filename)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'فرمت صادرات نامعتبر'
                }, status=400)
                
        except Exception as e:
            logger.error(f"Error exporting audit logs: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'خطا در صادرات لاگ‌های حسابرسی'
            }, status=500)
    
    def post(self, request):
        """Handle export preview and statistics."""
        try:
            # Get the same filters as the list view
            filters = json.loads(request.body)
            
            # Get filtered queryset
            filter_service = AuditLogFilterService()
            queryset = filter_service.get_filtered_queryset(filters)
            
            # Get export statistics
            export_service = AuditLogExportService()
            statistics = export_service.get_export_statistics(queryset)
            
            return JsonResponse({
                'success': True,
                'statistics': statistics
            })
            
        except Exception as e:
            logger.error(f"Error getting export statistics: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'خطا در محاسبه آمار صادرات'
            }, status=500)


class AuditLogSearchAPIView(SuperAdminRequiredMixin, View):
    """
    API endpoint for advanced audit log search functionality.
    """
    
    def get(self, request):
        """Handle search requests."""
        try:
            # Get search parameters
            search_params = {
                'q': request.GET.get('q', ''),
                'action': request.GET.get('action', ''),
                'model_name': request.GET.get('model_name', ''),
                'user_id': request.GET.get('user_id', ''),
                'username': request.GET.get('username', ''),
                'tenant_schema': request.GET.get('tenant_schema', ''),
                'ip_address': request.GET.get('ip_address', ''),
                'date_from': request.GET.get('date_from', ''),
                'date_to': request.GET.get('date_to', ''),
                'integrity_status': request.GET.get('integrity_status', ''),
            }
            
            # Remove empty parameters
            search_params = {k: v for k, v in search_params.items() if v}
            
            # Perform search
            search_service = AuditLogSearchService()
            queryset, search_metadata = search_service.advanced_search(search_params)
            
            # Paginate results
            page = int(request.GET.get('page', 1))
            paginator = Paginator(queryset, 20)
            page_obj = paginator.get_page(page)
            
            # Format results for JSON response
            results = []
            for log in page_obj:
                # Verify integrity for each log
                detail_service = AuditLogDetailService()
                integrity_status = detail_service.verify_log_integrity(log)
                
                results.append({
                    'id': log.id,
                    'created_at': log.created_at.isoformat(),
                    'user_username': log.user_username or 'نامشخص',
                    'action': log.action,
                    'action_display': log.get_action_display(),
                    'model_name': log.model_name or '',
                    'object_repr': log.object_repr or '',
                    'ip_address': log.ip_address or '',
                    'tenant_schema': log.tenant_schema or '',
                    'integrity_status': integrity_status,
                    'has_changes': bool(log.old_values or log.new_values),
                })
            
            return JsonResponse({
                'success': True,
                'results': results,
                'pagination': {
                    'current_page': page_obj.number,
                    'total_pages': paginator.num_pages,
                    'total_results': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                },
                'search_metadata': search_metadata,
            })
            
        except Exception as e:
            logger.error(f"Error in audit log search API: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'خطا در جستجوی لاگ‌های حسابرسی'
            }, status=500)


class AuditLogIntegrityCheckView(SuperAdminRequiredMixin, View):
    """
    View for checking audit log integrity in bulk.
    """
    
    def post(self, request):
        """Perform bulk integrity check on audit logs."""
        try:
            # Get parameters
            data = json.loads(request.body)
            log_ids = data.get('log_ids', [])
            check_all = data.get('check_all', False)
            
            if check_all:
                # Check all logs (limit for performance)
                queryset = PublicAuditLog.objects.all()[:1000]
            elif log_ids:
                # Check specific logs
                queryset = PublicAuditLog.objects.filter(id__in=log_ids)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'پارامترهای نامعتبر'
                }, status=400)
            
            # Perform integrity checks
            detail_service = AuditLogDetailService()
            results = {
                'total_checked': 0,
                'verified': 0,
                'compromised': 0,
                'no_checksum': 0,
                'errors': 0,
                'details': []
            }
            
            for log in queryset:
                results['total_checked'] += 1
                integrity_status = detail_service.verify_log_integrity(log)
                
                if integrity_status['status'] == 'verified':
                    results['verified'] += 1
                elif integrity_status['status'] == 'compromised':
                    results['compromised'] += 1
                elif integrity_status['status'] == 'no_checksum':
                    results['no_checksum'] += 1
                else:
                    results['errors'] += 1
                
                # Add details for compromised logs
                if integrity_status['status'] == 'compromised':
                    results['details'].append({
                        'log_id': log.id,
                        'created_at': log.created_at.isoformat(),
                        'user_username': log.user_username,
                        'action': log.get_action_display(),
                        'status': integrity_status['message']
                    })
            
            return JsonResponse({
                'success': True,
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Error in bulk integrity check: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'خطا در بررسی یکپارچگی'
            }, status=500)


class AuditLogStatsAPIView(SuperAdminRequiredMixin, View):
    """
    API endpoint for audit log statistics and metrics.
    """
    
    def get(self, request):
        """Get audit log statistics."""
        try:
            # Time range for statistics
            days = int(request.GET.get('days', 7))
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            # Basic counts
            total_logs = PublicAuditLog.objects.count()
            recent_logs = PublicAuditLog.objects.filter(
                created_at__gte=start_date
            ).count()
            
            # Action breakdown
            action_stats = PublicAuditLog.objects.filter(
                created_at__gte=start_date
            ).values('action').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            # User activity
            user_stats = PublicAuditLog.objects.filter(
                created_at__gte=start_date
            ).exclude(user_username='').values('user_username').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            # Tenant activity
            tenant_stats = PublicAuditLog.objects.filter(
                created_at__gte=start_date
            ).exclude(tenant_schema='').values('tenant_schema').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            # Daily activity trend
            daily_stats = []
            for i in range(days):
                day_start = start_date + timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                
                day_count = PublicAuditLog.objects.filter(
                    created_at__gte=day_start,
                    created_at__lt=day_end
                ).count()
                
                daily_stats.append({
                    'date': day_start.strftime('%Y-%m-%d'),
                    'date_persian': day_start.strftime('%d/%m'),
                    'count': day_count
                })
            
            # Integrity statistics
            logs_with_checksum = PublicAuditLog.objects.exclude(checksum='').count()
            integrity_percentage = (logs_with_checksum / total_logs * 100) if total_logs > 0 else 0
            
            return JsonResponse({
                'success': True,
                'statistics': {
                    'total_logs': total_logs,
                    'recent_logs': recent_logs,
                    'period_days': days,
                    'action_breakdown': list(action_stats),
                    'user_activity': list(user_stats),
                    'tenant_activity': list(tenant_stats),
                    'daily_trend': daily_stats,
                    'integrity_stats': {
                        'logs_with_checksum': logs_with_checksum,
                        'logs_without_checksum': total_logs - logs_with_checksum,
                        'integrity_percentage': round(integrity_percentage, 2),
                    }
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting audit log statistics: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'خطا در دریافت آمار'
            }, status=500)