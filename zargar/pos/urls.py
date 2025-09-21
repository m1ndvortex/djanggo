"""
URL configuration for POS module.
"""
from django.urls import path
from . import views

app_name = 'pos'

urlpatterns = [
    # Touch-Optimized POS Interface
    path('', views.POSTouchInterfaceView.as_view(), name='touch_interface'),
    path('touch/', views.POSTouchInterfaceView.as_view(), name='touch_interface_alt'),
    
    # POS Transaction Management
    path('transactions/', views.POSTransactionListView.as_view(), name='transaction_list'),
    path('create/', views.POSTransactionCreateView.as_view(), name='transaction_create'),
    path('transaction/<uuid:transaction_id>/', views.POSTransactionDetailView.as_view(), name='transaction_detail'),
    path('transaction/<uuid:transaction_id>/complete/', views.POSTransactionCompleteView.as_view(), name='transaction_complete'),
    path('transaction/<uuid:transaction_id>/cancel/', views.POSTransactionCancelView.as_view(), name='transaction_cancel'),
    
    # Line Item Management
    path('transaction/<uuid:transaction_id>/add-jewelry/', views.AddJewelryItemView.as_view(), name='add_jewelry_item'),
    path('transaction/<uuid:transaction_id>/add-custom/', views.AddCustomItemView.as_view(), name='add_custom_item'),
    path('transaction/<uuid:transaction_id>/remove-item/<int:line_item_id>/', views.RemoveLineItemView.as_view(), name='remove_line_item'),
    
    # Invoice Management
    path('invoice/<int:invoice_id>/', views.POSInvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoice/<int:invoice_id>/pdf/', views.POSInvoicePDFView.as_view(), name='invoice_pdf'),
    path('invoice/<int:invoice_id>/email/', views.POSInvoiceEmailView.as_view(), name='invoice_email'),
    
    # Offline Sync
    path('sync/', views.POSOfflineSyncView.as_view(), name='offline_sync'),
    path('sync/status/', views.POSOfflineSyncStatusView.as_view(), name='sync_status'),
    
    # Reporting
    path('reports/daily/', views.POSDailySalesReportView.as_view(), name='daily_sales_report'),
    path('reports/monthly/', views.POSMonthlySalesReportView.as_view(), name='monthly_sales_report'),
    
    # API Endpoints for AJAX/Mobile
    path('api/gold-price/', views.CurrentGoldPriceAPIView.as_view(), name='api_gold_price'),
    path('api/customer-lookup/', views.CustomerLookupAPIView.as_view(), name='api_customer_lookup'),
    path('api/jewelry-search/', views.JewelryItemSearchAPIView.as_view(), name='api_jewelry_search'),
    path('api/today-stats/', views.POSTodayStatsAPIView.as_view(), name='api_today_stats'),
    path('api/recent-transactions/', views.POSRecentTransactionsAPIView.as_view(), name='api_recent_transactions'),
    
    # Placeholder (for backward compatibility)
    path('placeholder/', views.PlaceholderView.as_view(), name='placeholder'),
]