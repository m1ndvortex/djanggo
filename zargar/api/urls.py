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

urlpatterns = [
    # JWT Authentication endpoints
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # API endpoints
    path('', include(router.urls)),
    
    # Core authentication and user management API
    path('', include('zargar.core.api_urls')),
]