"""
URL configuration for admin panel.
"""
from django.urls import path, include
from . import views
from . import disaster_recovery_views

app_name = 'admin_panel'

urlpatterns = [
    # Admin panel dashboard
    path('', views.AdminPanelDashboardView.as_view(), name='dashboard'),
    
    # Authentication
    path('login/', views.AdminLoginView.as_view(), name='login'),
    path('logout/', views.AdminLogoutView.as_view(), name='logout'),
    
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
    
    # Disaster Recovery
    path('disaster-recovery/', disaster_recovery_views.DisasterRecoveryDashboardView.as_view(), name='disaster_recovery_dashboard'),
    path('disaster-recovery/test/', disaster_recovery_views.DisasterRecoveryTestView.as_view(), name='disaster_recovery_test'),
    path('disaster-recovery/documentation/', disaster_recovery_views.DisasterRecoveryDocumentationView.as_view(), name='disaster_recovery_documentation'),
    
    # Include django-hijack URLs
    path('hijack/', include('hijack.urls')),
    
    # Include tenant management URLs
    path('tenants/', include('zargar.tenants.urls', namespace='tenants')),
]