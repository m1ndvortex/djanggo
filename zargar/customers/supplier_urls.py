"""
URL patterns for supplier management API endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .supplier_views import (
    SupplierViewSet,
    PurchaseOrderViewSet,
    SupplierPaymentViewSet,
    DeliveryScheduleViewSet,
    SupplierPerformanceViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchaseorder')
router.register(r'supplier-payments', SupplierPaymentViewSet, basename='supplierpayment')
router.register(r'delivery-schedules', DeliveryScheduleViewSet, basename='deliveryschedule')
router.register(r'supplier-performance', SupplierPerformanceViewSet, basename='supplierperformance')

app_name = 'supplier_management'

urlpatterns = [
    path('api/', include(router.urls)),
]