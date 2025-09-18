"""
URLs for core super-panel functionality.
"""
from django.urls import path, include
from . import views

app_name = 'core'

urlpatterns = [
    # Super-panel dashboard
    path('', views.SuperPanelDashboardView.as_view(), name='dashboard'),
    
    # Tenant management
    path('tenants/', views.TenantListView.as_view(), name='tenant_list'),
    path('tenants/create/', views.TenantCreateView.as_view(), name='tenant_create'),
    path('tenants/<int:pk>/', views.TenantDetailView.as_view(), name='tenant_detail'),
    path('tenants/<int:pk>/edit/', views.TenantUpdateView.as_view(), name='tenant_edit'),
    path('tenants/<int:pk>/suspend/', views.TenantSuspendView.as_view(), name='tenant_suspend'),
    
    # System health
    path('health/', views.SystemHealthView.as_view(), name='system_health'),
    
    # User management
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    
    # Audit logs
    path('audit/', views.AuditLogListView.as_view(), name='audit_logs'),
    
    # Settings
    path('settings/', views.SystemSettingsView.as_view(), name='settings'),
]