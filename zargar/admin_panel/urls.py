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
    
    # Include tenant management URLs
    path('', include('zargar.tenants.urls', namespace='tenants')),
]