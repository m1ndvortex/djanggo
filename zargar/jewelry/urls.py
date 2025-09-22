"""
URLs for jewelry inventory management module.
"""
from django.urls import path
from . import views

app_name = 'jewelry'

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
    
    # AJAX endpoints
    path('api/search/', views.inventory_search_api, name='inventory_search_api'),
    path('api/update-stock-thresholds/', views.update_stock_thresholds, name='update_stock_thresholds'),
    path('api/update-gold-values/', views.update_gold_values, name='update_gold_values'),
    path('api/assign-serial/<int:item_id>/', views.assign_serial_number, name='assign_serial_number'),
    path('api/delete-photo/<int:photo_id>/', views.delete_photo, name='delete_photo'),
    path('api/reorder-photos/<int:item_id>/', views.reorder_photos, name='reorder_photos'),
    path('api/create-category/', views.create_category, name='create_category'),
]