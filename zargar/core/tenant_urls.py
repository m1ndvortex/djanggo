"""
URL configuration for tenant-specific functionality.
"""
from django.urls import path, include
from django.contrib.auth import views as auth_views
from .tenant_views import (
    TenantDashboardView,
    TenantLoginView,
    TenantLogoutView,
    ThemeToggleView,
    TenantPasswordResetView,
    TenantPasswordResetDoneView,
    TenantPasswordResetConfirmView,
    TenantPasswordResetCompleteView,
    # User Management Views
    UserManagementListView,
    UserCreateView,
    UserUpdateView,
    UserDetailView,
    UserDeactivateView,
    UserPasswordResetView,
    UserProfileView,
    UserProfileEditView,
    UserPasswordChangeView,
)
from .twofa_views import (
    TwoFASetupView,
    TwoFADisableView,
    TwoFAVerifyView,
    TwoFABackupTokensView,
    TwoFAStatusAPIView
)

app_name = 'tenant'

urlpatterns = [
    # Tenant dashboard
    path('', TenantDashboardView.as_view(), name='dashboard'),
    
    # POS System URLs
    path('pos/', include('zargar.pos.urls')),
    
    # Authentication URLs
    path('login/', TenantLoginView.as_view(), name='login'),
    path('logout/', TenantLogoutView.as_view(), name='logout'),
    
    # Password reset URLs
    path('password-reset/', TenantPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', TenantPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', TenantPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', TenantPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    # Theme toggle
    path('theme/toggle/', ThemeToggleView.as_view(), name='theme_toggle'),
    
    # User Management URLs (Owner only)
    path('users/', UserManagementListView.as_view(), name='user_management'),
    path('users/create/', UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/edit/', UserUpdateView.as_view(), name='user_edit'),
    path('users/<int:pk>/deactivate/', UserDeactivateView.as_view(), name='user_deactivate'),
    path('users/<int:pk>/reset-password/', UserPasswordResetView.as_view(), name='user_password_reset'),
    
    # User Profile URLs
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/edit/', UserProfileEditView.as_view(), name='profile_edit'),
    path('profile/password/', UserPasswordChangeView.as_view(), name='password_change'),
    
    # 2FA URLs
    path('2fa/verify/', TwoFAVerifyView.as_view(), name='2fa_verify'),
    path('profile/2fa/setup/', TwoFASetupView.as_view(), name='2fa_setup'),
    path('profile/2fa/disable/', TwoFADisableView.as_view(), name='2fa_disable'),
    path('profile/2fa/backup-tokens/', TwoFABackupTokensView.as_view(), name='2fa_backup_tokens'),
    path('api/2fa/status/', TwoFAStatusAPIView.as_view(), name='2fa_status_api'),
]