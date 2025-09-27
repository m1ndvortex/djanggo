"""
API URLs for core authentication and user management.
"""
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView

from .api_views import (
    TenantAwareTokenObtainPairView,
    LoginAPIView,
    LogoutAPIView,
    UserProfileAPIView,
    UserListCreateAPIView,
    UserDetailAPIView,
    PasswordChangeAPIView,
    RoleUpdateAPIView,
    UserPermissionsAPIView,
    UserActivationAPIView,
    current_user_api,
    user_roles_api,
    validate_token_api,
)
from . import api_dashboard

app_name = 'core_api'

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', LoginAPIView.as_view(), name='login'),
    path('auth/logout/', LogoutAPIView.as_view(), name='logout'),
    path('auth/token/', TenantAwareTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/validate/', validate_token_api, name='validate_token'),
    
    # User management endpoints
    path('users/', UserListCreateAPIView.as_view(), name='user_list_create'),
    path('users/<int:pk>/', UserDetailAPIView.as_view(), name='user_detail'),
    path('users/<int:user_id>/permissions/', UserPermissionsAPIView.as_view(), name='user_permissions'),
    path('users/<int:user_id>/role/', RoleUpdateAPIView.as_view(), name='user_role_update'),
    path('users/<int:user_id>/activation/', UserActivationAPIView.as_view(), name='user_activation'),
    
    # Current user endpoints
    path('profile/', UserProfileAPIView.as_view(), name='user_profile'),
    path('profile/password/', PasswordChangeAPIView.as_view(), name='password_change'),
    path('profile/permissions/', UserPermissionsAPIView.as_view(), name='current_user_permissions'),
    path('me/', current_user_api, name='current_user'),
    
    # Utility endpoints
    path('roles/', user_roles_api, name='user_roles'),
    
    # Dashboard API endpoints
    path('dashboard/', api_dashboard.dashboard_data_api, name='dashboard_data'),
    path('dashboard/sales/', api_dashboard.sales_metrics_api, name='sales_metrics'),
    path('dashboard/inventory/', api_dashboard.inventory_metrics_api, name='inventory_metrics'),
    path('dashboard/gold-price/', api_dashboard.gold_price_api, name='gold_price'),
    path('dashboard/alerts/', api_dashboard.alerts_api, name='alerts'),
    path('dashboard/health/', api_dashboard.dashboard_health_check, name='dashboard_health'),
]