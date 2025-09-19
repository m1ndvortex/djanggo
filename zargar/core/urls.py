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

app_name = 'core'

urlpatterns = [
    # Super-panel dashboard
    path('', views.SuperPanelDashboardView.as_view(), name='dashboard'),
    
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
    
    # Tenant management
    path('tenants/', views.TenantListView.as_view(), name='tenant_list'),
    path('tenants/<int:pk>/', views.TenantDetailView.as_view(), name='tenant_detail'),
    path('tenants/create/', views.TenantCreateView.as_view(), name='tenant_create'),
    path('tenants/<int:pk>/edit/', views.TenantUpdateView.as_view(), name='tenant_edit'),
    path('tenants/<int:pk>/suspend/', views.TenantSuspendView.as_view(), name='tenant_suspend'),
    
    # User management
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    
    # System monitoring
    path('health/', views.SystemHealthView.as_view(), name='system_health'),
    path('audit-logs/', views.AuditLogListView.as_view(), name='audit_logs'),
    path('settings/', views.SystemSettingsView.as_view(), name='system_settings'),
]