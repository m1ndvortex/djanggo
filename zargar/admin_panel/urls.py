"""
URL configuration for admin panel.
"""
from django.urls import path, include
from . import views
from . import disaster_recovery_views
from . import unified_auth_views
from . import domain_views
from . import security_views
from . import audit_views
from . import rbac_views
from . import settings_views
from . import security_policy_views
from . import notification_views

app_name = 'admin_panel'

urlpatterns = [
    # Admin panel dashboard
    path('', views.UnifiedAdminDashboardView.as_view(), name='dashboard'),
    path('legacy/', views.AdminPanelDashboardView.as_view(), name='legacy_dashboard'),
    
    # Unified Authentication
    path('login/', unified_auth_views.UnifiedAdminLoginView.as_view(), name='unified_login'),
    path('logout/', unified_auth_views.UnifiedAdminLogoutView.as_view(), name='unified_logout'),
    path('2fa/setup/', unified_auth_views.UnifiedAdmin2FASetupView.as_view(), name='2fa_setup'),
    path('session/status/', unified_auth_views.UnifiedAdminSessionStatusView.as_view(), name='session_status'),
    
    # Domain Settings
    path('domain-settings/', domain_views.DomainSettingsView.as_view(), name='domain_settings'),
    

    
    # User Impersonation
    path('impersonation/', views.UserImpersonationView.as_view(), name='user_impersonation'),
    path('impersonation/start/', views.StartImpersonationView.as_view(), name='start_impersonation'),
    path('impersonation/end/', views.EndImpersonationView.as_view(), name='end_impersonation'),
    path('impersonation/terminate/', views.TerminateImpersonationView.as_view(), name='terminate_impersonation'),
    
    # Impersonation Audit
    path('impersonation/audit/', views.ImpersonationAuditView.as_view(), name='impersonation_audit'),
    path('impersonation/session/<uuid:session_id>/', views.ImpersonationSessionDetailView.as_view(), name='impersonation_session_detail'),
    path('impersonation/stats/', views.ImpersonationStatsView.as_view(), name='impersonation_stats'),
    
    # Backup Management
    path('backup/', views.BackupManagementView.as_view(), name='backup_management'),
    path('backup/history/', views.BackupHistoryView.as_view(), name='backup_history'),
    path('backup/create/', views.CreateBackupView.as_view(), name='create_backup'),
    path('backup/schedule/', views.BackupScheduleView.as_view(), name='backup_schedule'),
    path('backup/restore/', views.TenantRestoreView.as_view(), name='tenant_restore'),
    path('backup/job/<uuid:job_id>/', views.BackupJobDetailView.as_view(), name='backup_job_detail'),
    path('backup/status/', views.BackupStatusAPIView.as_view(), name='backup_status_api'),
    path('restore/status/', views.RestoreStatusAPIView.as_view(), name='restore_status_api'),
    
    # System Health Monitoring
    path('health/', views.SystemHealthDashboardView.as_view(), name='system_health_dashboard'),
    path('health/metrics/api/', views.SystemHealthMetricsAPIView.as_view(), name='system_health_metrics_api'),
    path('health/historical/api/', views.SystemHealthHistoricalView.as_view(), name='system_health_historical_api'),
    path('health/alerts/', views.SystemHealthAlertsView.as_view(), name='system_health_alerts'),
    path('health/alerts/action/', views.AlertActionView.as_view(), name='alert_action'),
    path('health/reports/', views.SystemHealthReportsView.as_view(), name='system_health_reports'),
    
    # Security Dashboard
    path('security/', security_views.SecurityDashboardView.as_view(), name='security_dashboard'),
    path('security/metrics/api/', security_views.SecurityMetricsAPIView.as_view(), name='security_metrics_api'),
    path('security/trends/api/', security_views.SecurityTrendsAPIView.as_view(), name='security_trends_api'),
    path('security/event/resolve/', security_views.SecurityEventResolveView.as_view(), name='security_event_resolve'),
    path('security/activity/investigate/', security_views.SuspiciousActivityInvestigateView.as_view(), name='suspicious_activity_investigate'),
    
    # Security Event Management
    path('security/events/', security_views.SecurityEventManagementView.as_view(), name='security_events'),
    path('security/events/<int:event_id>/', security_views.SecurityEventDetailView.as_view(), name='security_event_detail'),
    path('security/events/investigate/', security_views.SecurityEventInvestigateView.as_view(), name='security_event_investigate'),
    path('security/events/bulk-action/', security_views.SecurityEventBulkActionView.as_view(), name='security_event_bulk_action'),
    
    # RBAC Management
    path('security/rbac/', rbac_views.RBACManagementView.as_view(), name='rbac_management'),
    path('security/rbac/roles/', rbac_views.RoleListView.as_view(), name='rbac_role_list'),
    path('security/rbac/roles/create/', rbac_views.CreateRoleView.as_view(), name='rbac_create_role'),
    path('security/rbac/roles/<int:role_id>/', rbac_views.RoleDetailView.as_view(), name='rbac_role_detail'),
    path('security/rbac/assignments/', rbac_views.UserRoleAssignmentView.as_view(), name='rbac_user_assignments'),
    path('security/rbac/assignments/remove/', rbac_views.RemoveUserRoleView.as_view(), name='rbac_remove_user_role'),
    path('security/rbac/matrix/', rbac_views.PermissionMatrixView.as_view(), name='rbac_permission_matrix'),
    # RBAC API endpoints
    path('security/rbac/api/stats/', rbac_views.RBACStatsAPIView.as_view(), name='rbac_stats_api'),
    path('security/rbac/api/role/delete/', rbac_views.DeleteRoleAPIView.as_view(), name='rbac_delete_role_api'),
    path('security/rbac/api/user/permissions/', rbac_views.UserPermissionsAPIView.as_view(), name='rbac_user_permissions_api'),
    path('security/rbac/api/toggle-permission/', rbac_views.ToggleRolePermissionAPIView.as_view(), name='rbac_toggle_permission_api'),
    
    # Audit Log Management
    path('security/audit-logs/', audit_views.AuditLogListView.as_view(), name='audit_logs'),
    path('security/audit-logs/<int:log_id>/', audit_views.AuditLogDetailView.as_view(), name='audit_log_detail'),
    path('security/audit-logs/export/', audit_views.AuditLogExportView.as_view(), name='audit_log_export'),
    path('security/audit-logs/search/api/', audit_views.AuditLogSearchAPIView.as_view(), name='audit_log_search_api'),
    path('security/audit-logs/integrity/check/', audit_views.AuditLogIntegrityCheckView.as_view(), name='audit_log_integrity_check'),
    path('security/audit-logs/stats/api/', audit_views.AuditLogStatsAPIView.as_view(), name='audit_log_stats_api'),
    
    # Settings Management
    path('settings/', settings_views.SettingsManagementView.as_view(), name='settings_management'),
    path('settings/update/', settings_views.SettingUpdateView.as_view(), name='setting_update'),
    path('settings/bulk-update/', settings_views.BulkSettingsUpdateView.as_view(), name='bulk_settings_update'),
    path('settings/reset/', settings_views.SettingResetView.as_view(), name='setting_reset'),
    path('settings/history/<str:key>/', settings_views.SettingHistoryView.as_view(), name='setting_history'),
    path('settings/rollback/', settings_views.SettingRollbackView.as_view(), name='setting_rollback'),
    path('settings/export/', settings_views.SettingsExportView.as_view(), name='settings_export'),
    path('settings/import/', settings_views.SettingsImportView.as_view(), name='settings_import'),
    
    # Security Policy Settings
    path('settings/security-policies/', security_policy_views.SecurityPolicyManagementView.as_view(), name='security_policies'),
    path('settings/security-policies/update/', security_policy_views.SecurityPolicyUpdateView.as_view(), name='security_policy_update'),
    path('settings/security-policies/reset/', security_policy_views.SecurityPolicyResetView.as_view(), name='security_policy_reset'),
    path('settings/security-policies/validate/', security_policy_views.SecurityPolicyValidateView.as_view(), name='security_policy_validate'),
    path('settings/security-policies/test/', security_policy_views.SecurityPolicyTestView.as_view(), name='security_policy_test'),
    path('settings/security-policies/history/', security_policy_views.SecurityPolicyHistoryView.as_view(), name='security_policy_history'),
    
    # Notification Settings (Legacy)
    path('settings/notifications/', settings_views.NotificationSettingsView.as_view(), name='notification_settings'),
    path('settings/notifications/<int:setting_id>/', settings_views.NotificationSettingUpdateView.as_view(), name='notification_setting_update'),
    path('settings/notifications/<int:setting_id>/test/', settings_views.NotificationTestView.as_view(), name='notification_test'),
    
    # New Notification Management
    path('settings/notifications-management/', notification_views.NotificationManagementView.as_view(), name='notifications_management'),
    
    # Notification Management API endpoints
    path('api/notifications/email-config/', notification_views.EmailConfigurationAPIView.as_view(), name='api_email_config'),
    path('api/notifications/email-test/', notification_views.EmailTestAPIView.as_view(), name='api_email_test'),
    path('api/notifications/send-test/', notification_views.SendTestEmailAPIView.as_view(), name='api_send_test_email'),
    path('api/notifications/alert-config/', notification_views.AlertConfigurationAPIView.as_view(), name='api_alert_config'),
    path('api/notifications/delivery-stats/', notification_views.DeliveryStatisticsAPIView.as_view(), name='api_delivery_stats'),
    path('api/notifications/test/', notification_views.NotificationTestAPIView.as_view(), name='api_notification_test'),
    
    # Disaster Recovery
    path('disaster-recovery/', disaster_recovery_views.DisasterRecoveryDashboardView.as_view(), name='disaster_recovery_dashboard'),
    path('disaster-recovery/test/', disaster_recovery_views.DisasterRecoveryTestView.as_view(), name='disaster_recovery_test'),
    path('disaster-recovery/documentation/', disaster_recovery_views.DisasterRecoveryDocumentationView.as_view(), name='disaster_recovery_documentation'),
    
    # API endpoints for unified dashboard
    path('api/stats/', views.UnifiedAdminStatsAPIView.as_view(), name='unified_stats_api'),
    path('api/recent-activity/', views.UnifiedAdminRecentActivityAPIView.as_view(), name='unified_activity_api'),
    path('api/system-alerts/', views.UnifiedAdminSystemAlertsAPIView.as_view(), name='unified_alerts_api'),
    
    # Include django-hijack URLs
    path('hijack/', include('hijack.urls')),
    
    # Include tenant management URLs
    path('tenants/', include('zargar.tenants.urls', namespace='tenants')),
]