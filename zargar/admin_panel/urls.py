"""
URL configuration for admin panel.
"""
from django.urls import path, include
from . import views

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
    
    # Include django-hijack URLs
    path('hijack/', include('hijack.urls')),
    
    # Include tenant management URLs
    path('tenants/', include('zargar.tenants.urls', namespace='tenants')),
]