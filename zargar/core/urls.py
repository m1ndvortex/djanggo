"""
URL configuration for core super-panel functionality.
"""
from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from .auth_views import (
    AdminLoginView, 
    AdminLogoutView, 
    ThemeToggleView,
    AdminPasswordResetView,
    AdminPasswordResetDoneView,
    AdminPasswordResetConfirmView,
    AdminPasswordResetCompleteView,
    Admin2FAVerifyView
)
from .twofa_views import (
    TwoFASetupView,
    TwoFADisableView,
    TwoFAVerifyView,
    TwoFABackupTokensView,
    TwoFAStatusAPIView
)
# Import security views only if they exist
try:
    from .security_views import (
        SecurityDashboardView,
        SecurityEventsListView,
        SecurityEventDetailView,
        SecurityEventResolveView,
        AuditLogsListView,
        SuspiciousActivitiesListView,
        SuspiciousActivityInvestigateView,
        SecurityAlertsAPIView,
        RateLimitAttemptsListView,
        UnblockRateLimitView
    )
    SECURITY_VIEWS_AVAILABLE = True
except ImportError:
    SECURITY_VIEWS_AVAILABLE = False

app_name = 'core'

urlpatterns = [
    # Super-panel dashboard
    path('', views.SuperPanelDashboardView.as_view(), name='super_panel_dashboard'),
    
    # Authentication URLs
    path('login/', AdminLoginView.as_view(), name='admin_login'),
    path('logout/', AdminLogoutView.as_view(), name='admin_logout'),
    
    # Password reset URLs
    path('password-reset/', AdminPasswordResetView.as_view(), name='admin_password_reset'),
    path('password-reset/done/', AdminPasswordResetDoneView.as_view(), name='admin_password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', AdminPasswordResetConfirmView.as_view(), name='admin_password_reset_confirm'),
    path('password-reset/complete/', AdminPasswordResetCompleteView.as_view(), name='admin_password_reset_complete'),
    
    # Theme toggle
    path('theme/toggle/', ThemeToggleView.as_view(), name='theme_toggle'),
    
    # 2FA URLs
    path('2fa/verify/', Admin2FAVerifyView.as_view(), name='admin_2fa_verify'),
    
    # Tenant management - include tenant management URLs
    path('tenants/', include('zargar.tenants.urls')),
    
    # User management
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    
    # System monitoring
    path('health/', views.SystemHealthView.as_view(), name='system_health'),
    path('settings/', views.SystemSettingsView.as_view(), name='system_settings'),
    
    # Demo URLs
    path('demo/persian-calendar/', views.PersianCalendarDemoView.as_view(), name='persian_calendar_demo'),
    
]

# Add security dashboard URLs if views are available
if SECURITY_VIEWS_AVAILABLE:
    urlpatterns += [
        # Security dashboard
        path('security/', SecurityDashboardView.as_view(), name='security_dashboard'),
        path('security/events/', SecurityEventsListView.as_view(), name='security_events'),
        path('security/events/<int:pk>/', SecurityEventDetailView.as_view(), name='security_event_detail'),
        path('security/events/<int:pk>/resolve/', SecurityEventResolveView.as_view(), name='security_event_resolve'),
        path('security/audit-logs/', AuditLogsListView.as_view(), name='audit_logs'),
        path('security/suspicious-activities/', SuspiciousActivitiesListView.as_view(), name='suspicious_activities'),
        path('security/suspicious-activities/<int:pk>/investigate/', SuspiciousActivityInvestigateView.as_view(), name='suspicious_activity_investigate'),
        path('security/rate-limits/', RateLimitAttemptsListView.as_view(), name='rate_limits'),
        path('security/rate-limits/<int:pk>/unblock/', UnblockRateLimitView.as_view(), name='unblock_rate_limit'),
        path('security/alerts/api/', SecurityAlertsAPIView.as_view(), name='security_alerts_api'),
    ]