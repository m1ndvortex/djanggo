"""
URL configuration for gold installment system.
"""
from django.urls import path
from . import views

app_name = 'gold_installments'

urlpatterns = [
    # Dashboard and main views
    path('', views.GoldInstallmentDashboardView.as_view(), name='dashboard'),
    
    # Contract management
    path('contract/create/', views.GoldInstallmentContractCreateView.as_view(), name='contract_create'),
    path('contract/<int:pk>/', views.GoldInstallmentContractDetailView.as_view(), name='contract_detail'),
    path('contract/<int:pk>/edit/', views.GoldInstallmentContractUpdateView.as_view(), name='contract_edit'),
    
    # Payment processing
    path('contract/<int:contract_id>/payment/create/', views.GoldInstallmentPaymentCreateView.as_view(), name='payment_create'),
    path('contract/<int:contract_id>/payment/history/', views.contract_payment_history, name='payment_history'),
    
    # Weight adjustments
    path('contract/<int:contract_id>/adjustment/create/', views.GoldWeightAdjustmentCreateView.as_view(), name='adjustment_create'),
    
    # Payment processing endpoints
    path('contract/<int:contract_id>/process-payment/', views.process_payment_view, name='process_payment'),
    path('contract/<int:contract_id>/payment-preview/', views.calculate_payment_preview, name='payment_preview'),
    path('contract/<int:contract_id>/bidirectional-transaction/', views.process_bidirectional_transaction_view, name='bidirectional_transaction'),
    
    # Price protection endpoints
    path('contract/<int:contract_id>/setup-price-protection/', views.setup_price_protection_view, name='setup_price_protection'),
    path('contract/<int:contract_id>/remove-price-protection/', views.remove_price_protection_view, name='remove_price_protection'),
    path('contract/<int:contract_id>/analyze-price-protection/', views.analyze_price_protection_view, name='analyze_price_protection'),
    
    # Early payment endpoints
    path('contract/<int:contract_id>/early-payment-savings/', views.get_early_payment_savings_view, name='early_payment_savings'),
    
    # AJAX endpoints
    path('ajax/customer-search/', views.ajax_customer_search, name='ajax_customer_search'),
    path('ajax/gold-calculator/', views.ajax_gold_price_calculator, name='ajax_gold_calculator'),
    path('ajax/current-gold-price/', views.get_current_gold_price_api, name='current_gold_price'),
    
    # Export and reporting
    path('contract/<int:contract_id>/export/pdf/', views.contract_export_pdf, name='contract_export_pdf'),
    
    # Installment management and notification system
    path('tracking/', views.InstallmentTrackingDashboardView.as_view(), name='installment_tracking'),
    path('contract/<int:pk>/default-management/', views.DefaultManagementView.as_view(), name='default_management'),
    path('notifications/', views.NotificationManagementView.as_view(), name='notification_management'),
    path('contract/<int:pk>/contract-generation/', views.ContractGenerationView.as_view(), name='contract_generation'),
    
    # Notification actions
    path('contract/<int:contract_id>/send-reminder/', views.send_payment_reminder, name='send_payment_reminder'),
    path('contract/<int:contract_id>/schedule-notification/', views.schedule_notification, name='schedule_notification'),
    
    # Default management actions
    path('contract/<int:contract_id>/process-default-action/', views.process_default_action, name='process_default_action'),
    
    # Contract generation
    path('contract/<int:contract_id>/generate-pdf/', views.generate_contract_pdf, name='generate_contract_pdf'),
]