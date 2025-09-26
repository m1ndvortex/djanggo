"""
URL patterns for tenant management in the admin super-panel.
"""

from django.urls import path, include
from . import views

app_name = 'tenants'

urlpatterns = [
    # Tenant CRUD operations
    path('tenants/', views.TenantListView.as_view(), name='tenant_list'),
    path('tenants/create/', views.TenantCreateView.as_view(), name='tenant_create'),
    path('tenants/<int:pk>/', views.TenantDetailView.as_view(), name='tenant_detail'),
    path('tenants/<int:pk>/edit/', views.TenantUpdateView.as_view(), name='tenant_update'),
    path('tenants/<int:pk>/delete/', views.TenantDeleteView.as_view(), name='tenant_delete'),
    
    # Tenant management actions
    path('tenants/<int:pk>/toggle-status/', views.TenantToggleStatusView.as_view(), name='tenant_toggle_status'),
    path('tenants/<int:pk>/statistics/', views.TenantStatisticsView.as_view(), name='tenant_statistics'),
    
    # Search and bulk operations
    path('tenants/search/', views.TenantSearchView.as_view(), name='tenant_search'),
    path('tenants/bulk-action/', views.TenantBulkActionView.as_view(), name='tenant_bulk_action'),
    
    # Billing and Subscription Management
    path('billing/', include('zargar.tenants.billing_urls')),
]