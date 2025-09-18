"""
URLs for tenant-specific functionality.
"""
from django.urls import path
from . import tenant_views

app_name = 'tenant'

urlpatterns = [
    # Tenant dashboard
    path('', tenant_views.TenantDashboardView.as_view(), name='dashboard'),
    
    # User profile
    path('profile/', tenant_views.UserProfileView.as_view(), name='profile'),
    path('profile/edit/', tenant_views.UserProfileEditView.as_view(), name='profile_edit'),
    
    # Theme switching
    path('theme/toggle/', tenant_views.ThemeToggleView.as_view(), name='theme_toggle'),
    
    # 2FA management
    path('2fa/setup/', tenant_views.TwoFactorSetupView.as_view(), name='2fa_setup'),
    path('2fa/disable/', tenant_views.TwoFactorDisableView.as_view(), name='2fa_disable'),
]