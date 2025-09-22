"""
URLs for jewelry inventory management module.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .barcode_views import (
    BarcodeGenerationViewSet, BarcodeScanView, BarcodeScanHistoryViewSet,
    BarcodeTemplateViewSet, BarcodeSettingsViewSet
)

app_name = 'jewelry'

# DRF Router for barcode API endpoints
router = DefaultRouter()
router.register(r'barcode-generations', BarcodeGenerationViewSet, basename='barcode-generation')
router.register(r'scan-history', BarcodeScanHistoryViewSet, basename='scan-history')
router.register(r'barcode-templates', BarcodeTemplateViewSet, basename='barcode-template')
router.register(r'barcode-settings', BarcodeSettingsViewSet, basename='barcode-settings')

urlpatterns = [
    # Main inventory views
    path('', views.InventoryDashboardView.as_view(), name='dashboard'),
    path('inventory/', views.InventoryListView.as_view(), name='inventory_list'),
    path('inventory/<int:pk>/', views.InventoryDetailView.as_view(), name='inventory_detail'),
    path('inventory/create/', views.InventoryCreateView.as_view(), name='inventory_create'),
    path('inventory/<int:pk>/edit/', views.InventoryUpdateView.as_view(), name='inventory_edit'),
    
    # Category management
    path('categories/', views.CategoryManagementView.as_view(), name='category_management'),
    
    # Stock alerts and valuation
    path('stock-alerts/', views.StockAlertsView.as_view(), name='stock_alerts'),
    path('valuation/', views.InventoryValuationView.as_view(), name='inventory_valuation'),
    
    # Barcode and QR code endpoints
    path('barcode/', views.BarcodeManagementView.as_view(), name='barcode_management'),
    path('barcode/mobile/', views.MobileScannerView.as_view(), name='mobile_scanner'),
    path('barcode/history/', views.BarcodeHistoryView.as_view(), name='barcode_history'),
    path('barcode/scan/', BarcodeScanView.as_view(), name='barcode_scan'),
    path('api/barcode/', include(router.urls)),
    
    # Barcode API endpoints
    path('api/barcode/items/', views.barcode_items_api, name='barcode_items_api'),
    path('api/barcode/statistics/', views.barcode_statistics_api, name='barcode_statistics_api'),
    
    # AJAX endpoints
    path('api/search/', views.inventory_search_api, name='inventory_search_api'),
    path('api/update-stock-thresholds/', views.update_stock_thresholds, name='update_stock_thresholds'),
    path('api/update-gold-values/', views.update_gold_values, name='update_gold_values'),
    path('api/assign-serial/<int:item_id>/', views.assign_serial_number, name='assign_serial_number'),
    path('api/delete-photo/<int:photo_id>/', views.delete_photo, name='delete_photo'),
    path('api/reorder-photos/<int:item_id>/', views.reorder_photos, name='reorder_photos'),
    path('api/create-category/', views.create_category, name='create_category'),
]