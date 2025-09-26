"""
URL patterns for billing and subscription management.
"""

from django.urls import path
from . import billing_views

app_name = 'billing'

urlpatterns = [
    # Billing Dashboard
    path('', billing_views.BillingDashboardView.as_view(), name='dashboard'),
    
    # Subscription Plans Management
    path('plans/', billing_views.SubscriptionPlanListView.as_view(), name='subscription_plans'),
    path('plans/create/', billing_views.SubscriptionPlanCreateView.as_view(), name='subscription_plan_create'),
    path('plans/<int:pk>/edit/', billing_views.SubscriptionPlanUpdateView.as_view(), name='subscription_plan_update'),
    path('plans/<int:pk>/delete/', billing_views.SubscriptionPlanDeleteView.as_view(), name='subscription_plan_delete'),
    
    # Invoice Management
    path('invoices/', billing_views.InvoiceListView.as_view(), name='invoices'),
    path('invoices/create/', billing_views.InvoiceCreateView.as_view(), name='invoice_create'),
    path('invoices/<int:pk>/', billing_views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<int:pk>/payment/', billing_views.InvoicePaymentProcessView.as_view(), name='invoice_payment'),
    
    # Bulk Operations
    path('bulk-generation/', billing_views.BulkInvoiceGenerationView.as_view(), name='bulk_invoice_generation'),
    
    # Reports and Analytics
    path('reports/', billing_views.BillingReportsView.as_view(), name='reports'),
    
    # Settings
    path('settings/', billing_views.BillingSettingsView.as_view(), name='settings'),
]