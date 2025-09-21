"""
URLs for customers module.
"""
from django.urls import path
from . import views

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
    
    # AJAX endpoints
    path('ajax/loyalty/', views.CustomerLoyaltyAjaxView.as_view(), name='loyalty_ajax'),
    
    # Placeholder for other customer features
    path('placeholder/', views.PlaceholderView.as_view(), name='placeholder'),
]