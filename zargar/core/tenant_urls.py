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
    TenantPasswordResetCompleteView
)

app_name = 'tenant'

urlpatterns = [
    # Tenant dashboard
    path('', TenantDashboardView.as_view(), name='dashboard'),
    
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
]