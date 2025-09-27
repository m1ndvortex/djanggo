"""
Django admin interface for security models.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import json

from .security_models import SecurityEvent, AuditLog, RateLimitAttempt, SuspiciousActivity


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    """Admin interface for SecurityEvent model."""
    
    list_display = [
        'event_type', 'severity', 'user_link', 'ip_address', 
        'created_at', 'is_resolved', 'risk_indicator'
    ]
    list_filter = [
        'event_type', 'severity', 'is_resolved', 'created_at',
        ('user', admin.RelatedOnlyFieldListFilter)
    ]
    search_fields = [
        'user__username', 'username_attempted', 'ip_address', 
        'user_agent', 'request_path'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'created_by', 'updated_by',
        'risk_score_display', 'details_formatted'
    ]
    fieldsets = (
        ('Event Information', {
            'fields': (
                'event_type', 'severity', 'user', 'username_attempted',
                'risk_score_display'
            )
        }),
        ('Request Details', {
            'fields': (
                'ip_address', 'user_agent', 'session_key',
                'request_path', 'request_method'
            )
        }),
        ('Event Details', {
            'fields': ('details_formatted',),
            'classes': ('collapse',)
        }),
        ('Resolution', {
            'fields': (
                'is_resolved', 'resolved_by', 'resolved_at', 'resolution_notes'
            )
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_resolved', 'mark_unresolved', 'export_events']
    
    def user_link(self, obj):
        """Create link to user admin page."""
        if obj.user:
            url = reverse('admin:core_user_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return obj.username_attempted or '-'
    user_link.short_description = 'User'
    
    def risk_indicator(self, obj):
        """Display risk level indicator."""
        risk_score = obj.get_risk_score()
        if risk_score >= 8:
            color = 'red'
            icon = '🔴'
        elif risk_score >= 5:
            color = 'orange'
            icon = '🟠'
        elif risk_score >= 3:
            color = 'yellow'
            icon = '🟡'
        else:
            color = 'green'
            icon = '🟢'
        
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icon, risk_score
        )
    risk_indicator.short_description = 'Risk'
    
    def risk_score_display(self, obj):
        """Display formatted risk score."""
        return f"{obj.get_risk_score()}/10"
    risk_score_display.short_description = 'Risk Score'
    
    def details_formatted(self, obj):
        """Display formatted JSON details."""
        if obj.details:
            return format_html(
                '<pre>{}</pre>',
                json.dumps(obj.details, indent=2)
            )
        return '-'
    details_formatted.short_description = 'Details'
    
    def mark_resolved(self, request, queryset):
        """Mark selected events as resolved."""
        updated = queryset.update(
            is_resolved=True,
            resolved_by=request.user,
            resolved_at=timezone.now()
        )
        self.message_user(request, f'{updated} events marked as resolved.')
    mark_resolved.short_description = 'Mark selected events as resolved'
    
    def mark_unresolved(self, request, queryset):
        """Mark selected events as unresolved."""
        updated = queryset.update(
            is_resolved=False,
            resolved_by=None,
            resolved_at=None,
            resolution_notes=''
        )
        self.message_user(request, f'{updated} events marked as unresolved.')
    mark_unresolved.short_description = 'Mark selected events as unresolved'
    
    def export_events(self, request, queryset):
        """Export selected events to JSON."""
        # This would typically generate a downloadable file
        self.message_user(request, f'{queryset.count()} events exported.')
    export_events.short_description = 'Export selected events'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('user', 'resolved_by')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for AuditLog model."""
    
    list_display = [
        'action', 'user_link', 'model_name', 'object_repr',
        'created_at', 'ip_address', 'integrity_status'
    ]
    list_filter = [
        'action', 'model_name', 'created_at',
        ('user', admin.RelatedOnlyFieldListFilter)
    ]
    search_fields = [
        'user__username', 'model_name', 'object_repr',
        'ip_address', 'request_path'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'created_by', 'updated_by',
        'checksum', 'integrity_status', 'changes_formatted',
        'old_values_formatted', 'new_values_formatted', 'details_formatted'
    ]
    fieldsets = (
        ('Action Information', {
            'fields': (
                'action', 'user', 'model_name', 'object_id', 'object_repr'
            )
        }),
        ('Changes', {
            'fields': (
                'changes_formatted', 'old_values_formatted', 'new_values_formatted'
            ),
            'classes': ('collapse',)
        }),
        ('Request Context', {
            'fields': (
                'ip_address', 'user_agent', 'session_key',
                'request_path', 'request_method'
            )
        }),
        ('Additional Details', {
            'fields': ('details_formatted', 'tenant_schema'),
            'classes': ('collapse',)
        }),
        ('Integrity', {
            'fields': ('checksum', 'integrity_status'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['verify_integrity', 'export_logs']
    
    def user_link(self, obj):
        """Create link to user admin page."""
        if obj.user:
            url = reverse('admin:core_user_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '-'
    user_link.short_description = 'User'
    
    def integrity_status(self, obj):
        """Display integrity verification status."""
        if obj.verify_integrity():
            return format_html('<span style="color: green;">✓ Valid</span>')
        else:
            return format_html('<span style="color: red;">✗ Tampered</span>')
    integrity_status.short_description = 'Integrity'
    
    def changes_formatted(self, obj):
        """Display formatted changes."""
        if obj.changes:
            return format_html('<pre>{}</pre>', json.dumps(obj.changes, indent=2))
        return '-'
    changes_formatted.short_description = 'Changes'
    
    def old_values_formatted(self, obj):
        """Display formatted old values."""
        if obj.old_values:
            return format_html('<pre>{}</pre>', json.dumps(obj.old_values, indent=2))
        return '-'
    old_values_formatted.short_description = 'Old Values'
    
    def new_values_formatted(self, obj):
        """Display formatted new values."""
        if obj.new_values:
            return format_html('<pre>{}</pre>', json.dumps(obj.new_values, indent=2))
        return '-'
    new_values_formatted.short_description = 'New Values'
    
    def details_formatted(self, obj):
        """Display formatted details."""
        if obj.details:
            return format_html('<pre>{}</pre>', json.dumps(obj.details, indent=2))
        return '-'
    details_formatted.short_description = 'Details'
    
    def verify_integrity(self, request, queryset):
        """Verify integrity of selected audit logs."""
        valid_count = 0
        invalid_count = 0
        
        for log in queryset:
            if log.verify_integrity():
                valid_count += 1
            else:
                invalid_count += 1
        
        self.message_user(
            request,
            f'Integrity check completed: {valid_count} valid, {invalid_count} tampered'
        )
    verify_integrity.short_description = 'Verify integrity of selected logs'
    
    def export_logs(self, request, queryset):
        """Export selected logs."""
        self.message_user(request, f'{queryset.count()} logs exported.')
    export_logs.short_description = 'Export selected logs'
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('user', 'content_type')


@admin.register(RateLimitAttempt)
class RateLimitAttemptAdmin(admin.ModelAdmin):
    """Admin interface for RateLimitAttempt model."""
    
    list_display = [
        'identifier', 'limit_type', 'endpoint', 'attempts',
        'is_blocked', 'blocked_until', 'window_start', 'last_attempt'
    ]
    list_filter = [
        'limit_type', 'is_blocked', 'window_start', 'last_attempt'
    ]
    search_fields = ['identifier', 'endpoint', 'user_agent']
    readonly_fields = ['window_start', 'last_attempt', 'details_formatted']
    
    fieldsets = (
        ('Rate Limit Information', {
            'fields': (
                'identifier', 'limit_type', 'endpoint', 'attempts'
            )
        }),
        ('Blocking Status', {
            'fields': ('is_blocked', 'blocked_until')
        }),
        ('Timing', {
            'fields': ('window_start', 'last_attempt')
        }),
        ('Additional Information', {
            'fields': ('user_agent', 'details_formatted'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['unblock_attempts', 'reset_attempts']
    
    def details_formatted(self, obj):
        """Display formatted details."""
        if obj.details:
            return format_html('<pre>{}</pre>', json.dumps(obj.details, indent=2))
        return '-'
    details_formatted.short_description = 'Details'
    
    def unblock_attempts(self, request, queryset):
        """Unblock selected rate limit attempts."""
        updated = queryset.update(
            is_blocked=False,
            blocked_until=None
        )
        self.message_user(request, f'{updated} rate limit attempts unblocked.')
    unblock_attempts.short_description = 'Unblock selected attempts'
    
    def reset_attempts(self, request, queryset):
        """Reset attempt counters."""
        updated = queryset.update(
            attempts=0,
            is_blocked=False,
            blocked_until=None,
            window_start=timezone.now()
        )
        self.message_user(request, f'{updated} rate limit attempts reset.')
    reset_attempts.short_description = 'Reset selected attempts'


@admin.register(SuspiciousActivity)
class SuspiciousActivityAdmin(admin.ModelAdmin):
    """Admin interface for SuspiciousActivity model."""
    
    list_display = [
        'activity_type', 'risk_level', 'user_link', 'ip_address',
        'confidence_score', 'is_investigated', 'is_false_positive',
        'created_at'
    ]
    list_filter = [
        'activity_type', 'risk_level', 'is_investigated', 
        'is_false_positive', 'created_at',
        ('user', admin.RelatedOnlyFieldListFilter)
    ]
    search_fields = [
        'user__username', 'ip_address', 'user_agent', 'session_key'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'created_by', 'updated_by',
        'pattern_data_formatted', 'confidence_indicator'
    ]
    fieldsets = (
        ('Activity Information', {
            'fields': (
                'activity_type', 'risk_level', 'user', 'confidence_score',
                'confidence_indicator'
            )
        }),
        ('Context', {
            'fields': (
                'ip_address', 'user_agent', 'session_key'
            )
        }),
        ('Pattern Data', {
            'fields': ('pattern_data_formatted',),
            'classes': ('collapse',)
        }),
        ('Investigation', {
            'fields': (
                'is_investigated', 'investigated_by', 'investigated_at',
                'investigation_notes', 'is_false_positive'
            )
        }),
        ('Related Events', {
            'fields': ('related_events',),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_investigated', 'mark_false_positive', 'mark_legitimate_threat']
    filter_horizontal = ['related_events']
    
    def user_link(self, obj):
        """Create link to user admin page."""
        if obj.user:
            url = reverse('admin:core_user_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '-'
    user_link.short_description = 'User'
    
    def confidence_indicator(self, obj):
        """Display confidence score indicator."""
        score = obj.confidence_score
        if score >= 0.8:
            color = 'red'
            icon = '🔴'
        elif score >= 0.6:
            color = 'orange'
            icon = '🟠'
        elif score >= 0.4:
            color = 'yellow'
            icon = '🟡'
        else:
            color = 'green'
            icon = '🟢'
        
        return format_html(
            '<span style="color: {};">{} {:.1%}</span>',
            color, icon, score
        )
    confidence_indicator.short_description = 'Confidence'
    
    def pattern_data_formatted(self, obj):
        """Display formatted pattern data."""
        if obj.pattern_data:
            return format_html('<pre>{}</pre>', json.dumps(obj.pattern_data, indent=2))
        return '-'
    pattern_data_formatted.short_description = 'Pattern Data'
    
    def mark_investigated(self, request, queryset):
        """Mark selected activities as investigated."""
        updated = queryset.update(
            is_investigated=True,
            investigated_by=request.user,
            investigated_at=timezone.now()
        )
        self.message_user(request, f'{updated} activities marked as investigated.')
    mark_investigated.short_description = 'Mark as investigated'
    
    def mark_false_positive(self, request, queryset):
        """Mark selected activities as false positives."""
        updated = queryset.update(
            is_investigated=True,
            investigated_by=request.user,
            investigated_at=timezone.now(),
            is_false_positive=True
        )
        self.message_user(request, f'{updated} activities marked as false positives.')
    mark_false_positive.short_description = 'Mark as false positive'
    
    def mark_legitimate_threat(self, request, queryset):
        """Mark selected activities as legitimate threats."""
        updated = queryset.update(
            is_investigated=True,
            investigated_by=request.user,
            investigated_at=timezone.now(),
            is_false_positive=False
        )
        self.message_user(request, f'{updated} activities marked as legitimate threats.')
    mark_legitimate_threat.short_description = 'Mark as legitimate threat'
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related(
            'user', 'investigated_by'
        ).prefetch_related('related_events')


# Custom admin views for security dashboard
class SecurityDashboardAdmin(admin.ModelAdmin):
    """Custom admin view for security dashboard."""
    
    def changelist_view(self, request, extra_context=None):
        """Custom changelist view with security statistics."""
        extra_context = extra_context or {}
        
        # Get recent statistics
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        
        # Security events statistics
        recent_events = SecurityEvent.objects.filter(created_at__gte=last_24h)
        critical_events = recent_events.filter(severity='critical').count()
        high_events = recent_events.filter(severity='high').count()
        unresolved_events = recent_events.filter(is_resolved=False).count()
        
        # Suspicious activities statistics
        recent_activities = SuspiciousActivity.objects.filter(created_at__gte=last_24h)
        unresolved_activities = recent_activities.filter(is_investigated=False).count()
        high_risk_activities = recent_activities.filter(risk_level__in=['high', 'critical']).count()
        
        # Rate limiting statistics
        blocked_attempts = RateLimitAttempt.objects.filter(
            last_attempt__gte=last_24h,
            is_blocked=True
        ).count()
        
        # Top risk IPs
        risk_ips = SecurityEvent.objects.filter(
            created_at__gte=last_7d,
            severity__in=['high', 'critical']
        ).values('ip_address').annotate(
            event_count=Count('id')
        ).order_by('-event_count')[:5]
        
        extra_context.update({
            'security_stats': {
                'critical_events': critical_events,
                'high_events': high_events,
                'unresolved_events': unresolved_events,
                'unresolved_activities': unresolved_activities,
                'high_risk_activities': high_risk_activities,
                'blocked_attempts': blocked_attempts,
                'risk_ips': list(risk_ips),
            }
        })
        
        return super().changelist_view(request, extra_context)