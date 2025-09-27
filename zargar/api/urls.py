"""
API URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import (
    JewelryItemViewSet,
    CategoryViewSet,
    GemstoneViewSet,
    CustomerViewSet,
    SupplierViewSet,
    POSTransactionViewSet,
    POSTransactionLineItemViewSet,
)
from .mobile_views import (
    MobilePOSViewSet,
    MobileInventoryViewSet,
    MobileCustomerViewSet,
    MobileSyncViewSet,
    MobileNotificationViewSet,
)
from .push_notification_api import MobileDeviceViewSet

# Create router and register ViewSets
router = DefaultRouter()

# Jewelry management endpoints
router.register(r'jewelry-items', JewelryItemViewSet, basename='jewelryitem')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'gemstones', GemstoneViewSet, basename='gemstone')

# Customer management endpoints
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'suppliers', SupplierViewSet, basename='supplier')

# POS endpoints
router.register(r'pos-transactions', POSTransactionViewSet, basename='postransaction')
router.register(r'pos-line-items', POSTransactionLineItemViewSet, basename='postransactionlineitem')

# Mobile-specific endpoints
router.register(r'mobile/pos', MobilePOSViewSet, basename='mobile-pos')
router.register(r'mobile/inventory', MobileInventoryViewSet, basename='mobile-inventory')
router.register(r'mobile/customers', MobileCustomerViewSet, basename='mobile-customers')
router.register(r'mobile/sync', MobileSyncViewSet, basename='mobile-sync')
router.register(r'mobile/notifications', MobileNotificationViewSet, basename='mobile-notifications')
router.register(r'mobile/devices', MobileDeviceViewSet, basename='mobile-devices')

urlpatterns = [
    # JWT Authentication endpoints
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # API endpoints
    path('', include(router.urls)),
    
    # Mobile offline sync endpoints
    path('mobile/sync/', include('zargar.api.offline_sync_urls')),
    
    # Push notification endpoints
    path('mobile/push/', include('zargar.api.push_notification_urls')),
    
    # Core authentication and user management API
    path('', include('zargar.core.api_urls')),
]