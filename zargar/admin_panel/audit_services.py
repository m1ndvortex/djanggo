"""
Audit log management services for the super admin panel.
Provides backend logic for audit log filtering, searching, and export functionality.
"""

from django.db.models import Q, Count, F, Min, Max
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.contrib.contenttypes.models import ContentType
from datetime import datetime, timedelta
import csv
import json
import logging
from typing import Dict, List, Optional, Tuple, Any

from zargar.tenants.admin_models import PublicAuditLog
from zargar.core.models import User

logger = logging.getLogger(__name__)


class AuditLogFilterService:
    """
    Service for filtering and searching audit logs with advanced criteria.
    """
    
    @staticmethod
    def get_filtered_queryset(filters: Dict[str, Any]) -> 'QuerySet':
        """
        Get filtered audit log queryset based on provided filters.
        
        Args:
            filters: Dictionary containing filter criteria
            
        Returns:
            Filtered QuerySet of AuditLog objects
        """
        try:
            queryset = PublicAuditLog.objects.all().order_by('-created_at')
        except Exception:
            # Return empty queryset if there are database issues
            return PublicAuditLog.objects.none()
        
        # Action filter
        if filters.get('action'):
            queryset = queryset.filter(action=filters['action'])
        
        # Model name filter
        if filters.get('model_name'):
            queryset = queryset.filter(model_name__icontains=filters['model_name'])
        
        # User filter
        if filters.get('user_id'):
            try:
                user_id = int(filters['user_id'])
                queryset = queryset.filter(user_id=user_id)
            except (ValueError, TypeError):
                pass
        
        # Username filter
        if filters.get('username'):
            queryset = queryset.filter(user__username__icontains=filters['username'])
        
        # Tenant schema filter
        if filters.get('tenant_schema'):
            queryset = queryset.filter(tenant_schema=filters['tenant_schema'])
        
        # IP address filter
        if filters.get('ip_address'):
            queryset = queryset.filter(ip_address__icontains=filters['ip_address'])
        
        # Date range filters
        if filters.get('date_from'):
            try:
                date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=date_from)
            except ValueError:
                pass
        
        if filters.get('date_to'):
            try:
                date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=date_to)
            except ValueError:
                pass
        
        # Time range filters (for specific hours)
        if filters.get('time_from'):
            try:
                time_from = datetime.strptime(filters['time_from'], '%H:%M').time()
                queryset = queryset.filter(created_at__time__gte=time_from)
            except ValueError:
                pass
        
        if filters.get('time_to'):
            try:
                time_to = datetime.strptime(filters['time_to'], '%H:%M').time()
                queryset = queryset.filter(created_at__time__lte=time_to)
            except ValueError:
                pass
        
        # Content type filter
        if filters.get('content_type_id'):
            try:
                content_type_id = int(filters['content_type_id'])
                queryset = queryset.filter(content_type_id=content_type_id)
            except (ValueError, TypeError):
                pass
        
        # Object ID filter
        if filters.get('object_id'):
            queryset = queryset.filter(object_id__icontains=filters['object_id'])
        
        # Search across multiple fields
        if filters.get('search'):
            search_term = filters['search']
            queryset = queryset.filter(
                Q(user__username__icontains=search_term) |
                Q(object_repr__icontains=search_term) |
                Q(ip_address__icontains=search_term) |
                Q(model_name__icontains=search_term) |
                Q(request_path__icontains=search_term) |
                Q(details__icontains=search_term)
            )
        
        # Integrity status filter
        if filters.get('integrity_status'):
            if filters['integrity_status'] == 'verified':
                # Only include logs with valid checksums
                queryset = queryset.exclude(checksum='')
            elif filters['integrity_status'] == 'compromised':
                # This would require actual integrity verification
                # For now, we'll filter logs without checksums
                queryset = queryset.filter(checksum='')
        
        return queryset
    
    @staticmethod
    def get_filter_options() -> Dict[str, List]:
        """
        Get available filter options for the audit log interface.
        
        Returns:
            Dictionary containing filter options
        """
        try:
            # Get distinct action types
            action_types = list(PublicAuditLog.objects.values_list(
                'action', flat=True
            ).distinct().order_by('action'))
            
            # Get distinct model names
            model_names = list(PublicAuditLog.objects.values_list(
                'model_name', flat=True
            ).distinct().order_by('model_name'))
            
            # Get distinct tenant schemas
            tenant_schemas = list(PublicAuditLog.objects.exclude(
                tenant_schema=''
            ).values_list('tenant_schema', flat=True).distinct().order_by('tenant_schema'))
            
            # Get content types that have audit logs
            try:
                content_types = list(ContentType.objects.filter(
                    id__in=PublicAuditLog.objects.values_list('content_type_id', flat=True).distinct()
                ).values('id', 'model', 'app_label').order_by('app_label', 'model'))
            except Exception:
                content_types = []
            
            # Get users who have audit logs
            try:
                users = []
                user_logs = PublicAuditLog.objects.exclude(user_username='').values_list('user_username', flat=True).distinct()
                for username in user_logs:
                    if username:
                        users.append({'username': username})
            except Exception:
                users = []
            
            return {
                'action_types': action_types,
                'model_names': model_names,
                'tenant_schemas': tenant_schemas,
                'content_types': content_types,
                'users': users,
            }
        except Exception as e:
            logger.error(f"Error getting filter options: {str(e)}")
            return {
                'action_types': [],
                'model_names': [],
                'tenant_schemas': [],
                'content_types': [],
                'users': [],
            }


class AuditLogDetailService:
    """
    Service for retrieving detailed audit log information with integrity verification.
    """
    
    @staticmethod
    def get_audit_log_detail(log_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific audit log entry.
        
        Args:
            log_id: ID of the audit log entry
            
        Returns:
            Dictionary containing detailed audit log information or None if not found
        """
        try:
            log_entry = PublicAuditLog.objects.get(id=log_id)
            
            # Verify integrity
            integrity_status = AuditLogDetailService.verify_log_integrity(log_entry)
            
            # Format changes for display
            formatted_changes = AuditLogDetailService.format_changes(log_entry)
            
            # Get related logs (same object, similar timeframe)
            related_logs = AuditLogDetailService.get_related_logs(log_entry)
            
            return {
                'log_entry': log_entry,
                'integrity_status': integrity_status,
                'formatted_changes': formatted_changes,
                'related_logs': related_logs,
                'has_before_after': bool(log_entry.old_values or log_entry.new_values),
            }
            
        except PublicAuditLog.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error retrieving audit log detail {log_id}: {str(e)}")
            return None
    
    @staticmethod
    def verify_log_integrity(log_entry: 'PublicAuditLog') -> Dict[str, Any]:
        """
        Verify the integrity of an audit log entry.
        
        Args:
            log_entry: AuditLog instance
            
        Returns:
            Dictionary containing integrity verification results
        """
        if not log_entry.checksum:
            return {
                'status': 'no_checksum',
                'message': 'بدون چک‌سام - قابل تایید نیست',
                'is_valid': False,
                'color': 'warning'
            }
        
        try:
            # Verify integrity using the model's method
            is_valid = log_entry.verify_integrity()
            
            if is_valid:
                return {
                    'status': 'verified',
                    'message': 'تایید شده - دست‌نخورده',
                    'is_valid': True,
                    'color': 'success'
                }
            else:
                return {
                    'status': 'compromised',
                    'message': 'خطر - احتمال دستکاری',
                    'is_valid': False,
                    'color': 'danger'
                }
                
        except Exception as e:
            logger.error(f"Error verifying integrity for log {log_entry.id}: {str(e)}")
            return {
                'status': 'error',
                'message': 'خطا در تایید یکپارچگی',
                'is_valid': False,
                'color': 'danger'
            }
    
    @staticmethod
    def format_changes(log_entry: 'PublicAuditLog') -> Dict[str, Any]:
        """
        Format changes for display in the UI.
        
        Args:
            log_entry: AuditLog instance
            
        Returns:
            Dictionary containing formatted changes
        """
        formatted = {
            'has_changes': False,
            'field_changes': [],
            'old_values_json': '',
            'new_values_json': '',
            'changes_json': '',
        }
        
        try:
            # Format JSON for display
            if log_entry.old_values:
                formatted['old_values_json'] = json.dumps(
                    log_entry.old_values, indent=2, ensure_ascii=False
                )
            
            if log_entry.new_values:
                formatted['new_values_json'] = json.dumps(
                    log_entry.new_values, indent=2, ensure_ascii=False
                )
            
            if log_entry.changes:
                formatted['changes_json'] = json.dumps(
                    log_entry.changes, indent=2, ensure_ascii=False
                )
            
            # Create field-by-field comparison
            if log_entry.old_values and log_entry.new_values:
                formatted['has_changes'] = True
                
                all_fields = set(log_entry.old_values.keys()) | set(log_entry.new_values.keys())
                
                for field in sorted(all_fields):
                    old_value = log_entry.old_values.get(field, '(مقدار موجود نیست)')
                    new_value = log_entry.new_values.get(field, '(مقدار موجود نیست)')
                    
                    if old_value != new_value:
                        formatted['field_changes'].append({
                            'field': field,
                            'old_value': str(old_value),
                            'new_value': str(new_value),
                            'is_changed': True,
                        })
                    else:
                        formatted['field_changes'].append({
                            'field': field,
                            'old_value': str(old_value),
                            'new_value': str(new_value),
                            'is_changed': False,
                        })
            
        except Exception as e:
            logger.error(f"Error formatting changes for log {log_entry.id}: {str(e)}")
        
        return formatted
    
    @staticmethod
    def get_related_logs(log_entry: 'PublicAuditLog', limit: int = 5) -> List['PublicAuditLog']:
        """
        Get related audit logs for the same object or user.
        
        Args:
            log_entry: AuditLog instance
            limit: Maximum number of related logs to return
            
        Returns:
            List of related AuditLog instances
        """
        try:
            # Get logs for the same object within 1 hour
            time_window = timedelta(hours=1)
            start_time = log_entry.created_at - time_window
            end_time = log_entry.created_at + time_window
            
            related_queryset = PublicAuditLog.objects.filter(
                created_at__range=(start_time, end_time)
            ).exclude(id=log_entry.id)
            
            # Prioritize same object, then same user, then same IP
            if log_entry.content_type_id and log_entry.object_id:
                related_queryset = related_queryset.filter(
                    content_type_id=log_entry.content_type_id,
                    object_id=log_entry.object_id
                )
            elif log_entry.user_id:
                related_queryset = related_queryset.filter(user_id=log_entry.user_id)
            elif log_entry.ip_address:
                related_queryset = related_queryset.filter(ip_address=log_entry.ip_address)
            
            return list(related_queryset.order_by('-created_at')[:limit])
            
        except Exception as e:
            logger.error(f"Error getting related logs for {log_entry.id}: {str(e)}")
            return []


class AuditLogExportService:
    """
    Service for exporting audit logs in various formats for compliance reporting.
    """
    
    @staticmethod
    def export_to_csv(queryset: 'QuerySet', filename: str = None) -> HttpResponse:
        """
        Export audit logs to CSV format.
        
        Args:
            queryset: QuerySet of AuditLog objects
            filename: Optional filename for the export
            
        Returns:
            HttpResponse with CSV content
        """
        if not filename:
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f'audit_logs_{timestamp}.csv'
        
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Add BOM for proper UTF-8 handling in Excel
        response.write('\ufeff')
        
        writer = csv.writer(response)
        
        # Write headers in Persian
        headers = [
            'شناسه',
            'تاریخ و زمان',
            'کاربر',
            'عملیات',
            'مدل',
            'شناسه شیء',
            'نمایش شیء',
            'آدرس IP',
            'مسیر درخواست',
            'متد درخواست',
            'اسکیمای تنانت',
            'جزئیات',
            'وضعیت یکپارچگی',
        ]
        writer.writerow(headers)
        
        # Write data rows
        for log in queryset.iterator():
            integrity_status = AuditLogDetailService.verify_log_integrity(log)
            
            row = [
                log.id,
                log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                log.user.username if log.user else 'نامشخص',
                log.get_action_display(),
                log.model_name or '',
                log.object_id or '',
                log.object_repr or '',
                log.ip_address or '',
                log.request_path or '',
                log.request_method or '',
                log.tenant_schema or '',
                json.dumps(log.details, ensure_ascii=False) if log.details else '',
                integrity_status['message'],
            ]
            writer.writerow(row)
        
        return response
    
    @staticmethod
    def export_to_json(queryset: 'QuerySet', filename: str = None) -> HttpResponse:
        """
        Export audit logs to JSON format.
        
        Args:
            queryset: QuerySet of AuditLog objects
            filename: Optional filename for the export
            
        Returns:
            HttpResponse with JSON content
        """
        if not filename:
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f'audit_logs_{timestamp}.json'
        
        response = HttpResponse(content_type='application/json; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Prepare data for JSON export
        export_data = {
            'export_info': {
                'timestamp': timezone.now().isoformat(),
                'total_records': queryset.count(),
                'format': 'json',
            },
            'audit_logs': []
        }
        
        for log in queryset.iterator():
            integrity_status = AuditLogDetailService.verify_log_integrity(log)
            
            log_data = {
                'id': log.id,
                'created_at': log.created_at.isoformat(),
                'user_id': log.user.id if log.user else None,
                'user_username': log.user.username if log.user else None,
                'action': log.action,
                'action_display': log.get_action_display(),
                'model_name': log.model_name,
                'object_id': log.object_id,
                'object_repr': log.object_repr,
                'content_type': {
                    'id': log.content_type_id,
                    'model': log.content_type.model if log.content_type else None,
                    'app_label': log.content_type.app_label if log.content_type else None,
                },
                'changes': log.changes,
                'old_values': log.old_values,
                'new_values': log.new_values,
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'session_key': log.session_key,
                'request_path': log.request_path,
                'request_method': log.request_method,
                'tenant_schema': log.tenant_schema,
                'details': log.details,
                'checksum': log.checksum,
                'integrity_status': integrity_status,
            }
            
            export_data['audit_logs'].append(log_data)
        
        json_content = json.dumps(export_data, indent=2, ensure_ascii=False, default=str)
        response.write(json_content)
        
        return response
    
    @staticmethod
    def get_export_statistics(queryset: 'QuerySet') -> Dict[str, Any]:
        """
        Get statistics about the audit logs being exported.
        
        Args:
            queryset: QuerySet of AuditLog objects
            
        Returns:
            Dictionary containing export statistics
        """
        try:
            total_count = queryset.count()
            
            # Action breakdown
            action_stats = queryset.values('action').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # User breakdown
            user_stats = queryset.values('user_username').annotate(
                count=Count('id')
            ).order_by('-count')[:10]  # Top 10 users
            
            # Tenant breakdown
            tenant_stats = queryset.values('tenant_schema').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Time range
            time_range = queryset.aggregate(
                earliest=Min('created_at'),
                latest=Max('created_at')
            )
            
            # Integrity status
            logs_with_checksum = queryset.exclude(checksum='').count()
            integrity_percentage = (logs_with_checksum / total_count * 100) if total_count > 0 else 0
            
            return {
                'total_count': total_count,
                'action_breakdown': list(action_stats),
                'user_breakdown': list(user_stats),
                'tenant_breakdown': list(tenant_stats),
                'time_range': time_range,
                'integrity_stats': {
                    'logs_with_checksum': logs_with_checksum,
                    'logs_without_checksum': total_count - logs_with_checksum,
                    'integrity_percentage': round(integrity_percentage, 2),
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating export statistics: {str(e)}")
            return {
                'total_count': 0,
                'error': str(e)
            }


class AuditLogSearchService:
    """
    Advanced search service for audit logs with full-text search capabilities.
    """
    
    @staticmethod
    def advanced_search(search_params: Dict[str, Any]) -> Tuple['QuerySet', Dict[str, Any]]:
        """
        Perform advanced search across audit logs.
        
        Args:
            search_params: Dictionary containing search parameters
            
        Returns:
            Tuple of (filtered queryset, search metadata)
        """
        try:
            queryset = PublicAuditLog.objects.all().order_by('-created_at')
        except Exception:
            queryset = PublicAuditLog.objects.none()
        search_metadata = {
            'total_before_search': queryset.count(),
            'search_terms_used': [],
            'filters_applied': [],
        }
        
        # Full-text search across multiple fields
        if search_params.get('q'):
            search_term = search_params['q']
            search_metadata['search_terms_used'].append(search_term)
            
            queryset = queryset.filter(
                Q(user__username__icontains=search_term) |
                Q(object_repr__icontains=search_term) |
                Q(ip_address__icontains=search_term) |
                Q(model_name__icontains=search_term) |
                Q(request_path__icontains=search_term) |
                Q(details__icontains=search_term) |
                Q(old_values__icontains=search_term) |
                Q(new_values__icontains=search_term)
            )
            search_metadata['filters_applied'].append('full_text_search')
        
        # Apply additional filters
        filter_service = AuditLogFilterService()
        queryset = filter_service.get_filtered_queryset(search_params)
        
        # Add filter metadata
        for key, value in search_params.items():
            if value and key != 'q':
                search_metadata['filters_applied'].append(key)
        
        search_metadata['total_after_search'] = queryset.count()
        search_metadata['results_filtered'] = (
            search_metadata['total_before_search'] - search_metadata['total_after_search']
        )
        
        return queryset, search_metadata