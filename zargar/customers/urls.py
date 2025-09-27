"""
URLs for customers module.
"""
from django.urls import path
from . import views
from .layaway_views import (
    LayawayDashboardView, LayawayPlanListView, LayawayPlanCreateView, 
    LayawayPlanDetailView, LayawayReminderManagementView, LayawayReportsView,
    LayawayAjaxView
)
from .supplier_views import (
    SupplierManagementDashboardView, SupplierListView, SupplierDetailView,
    SupplierCreateView, SupplierUpdateView, PurchaseOrderListView,
    PurchaseOrderDetailView, PurchaseOrderCreateView, PurchaseOrderUpdateView,
    SupplierPerformanceReportView, SupplierAjaxView
)

app_name = 'customers'

urlpatterns = [
    # Customer Loyalty Management
    path('', views.CustomerLoyaltyDashboardView.as_view(), name='loyalty_dashboard'),
    path('loyalty/', views.CustomerLoyaltyDashboardView.as_view(), name='loyalty_dashboard'),
    path('loyalty/<int:pk>/', views.CustomerLoyaltyDetailView.as_view(), name='loyalty_detail'),
    
    # Customer Engagement
    path('engagement/', views.CustomerEngagementDashboardView.as_view(), name='engagement_dashboard'),
    path('engagement/events/', views.CustomerEngagementEventListView.as_view(), name='engagement_events'),
    
    # Birthday and Anniversary Reminders
    path('reminders/', views.BirthdayReminderView.as_view(), name='birthday_reminders'),
    
    # Layaway and Installment Plans
    path('layaway/', LayawayDashboardView.as_view(), name='layaway_dashboard'),
    path('layaway/list/', LayawayPlanListView.as_view(), name='layaway_list'),
    path('layaway/create/', LayawayPlanCreateView.as_view(), name='layaway_create'),
    path('layaway/<int:pk>/', LayawayPlanDetailView.as_view(), name='layaway_detail'),
    path('layaway/reminders/', LayawayReminderManagementView.as_view(), name='layaway_reminders'),
    path('layaway/reports/', LayawayReportsView.as_view(), name='layaway_reports'),
    
    # Supplier Management
    path('suppliers/', SupplierManagementDashboardView.as_view(), name='supplier_dashboard'),
    path('suppliers/list/', SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/create/', SupplierCreateView.as_view(), name='supplier_create'),
    path('suppliers/<int:pk>/', SupplierDetailView.as_view(), name='supplier_detail'),
    path('suppliers/<int:pk>/edit/', SupplierUpdateView.as_view(), name='supplier_update'),
    path('suppliers/performance/', SupplierPerformanceReportView.as_view(), name='supplier_performance'),
    
    # Purchase Order Management
    path('purchase-orders/', PurchaseOrderListView.as_view(), name='purchase_order_list'),
    path('purchase-orders/create/', PurchaseOrderCreateView.as_view(), name='purchase_order_create'),
    path('purchase-orders/<int:pk>/', PurchaseOrderDetailView.as_view(), name='purchase_order_detail'),
    path('purchase-orders/<int:pk>/edit/', PurchaseOrderUpdateView.as_view(), name='purchase_order_update'),
    
    # AJAX endpoints
    path('ajax/loyalty/', views.CustomerLoyaltyAjaxView.as_view(), name='loyalty_ajax'),
    path('layaway/ajax/', LayawayAjaxView.as_view(), name='layaway_ajax'),
    path('suppliers/ajax/', SupplierAjaxView.as_view(), name='supplier_ajax'),
    
    # Placeholder for other customer features
    path('placeholder/', views.PlaceholderView.as_view(), name='placeholder'),
]