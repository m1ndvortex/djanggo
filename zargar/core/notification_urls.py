"""
URL patterns for notification system.
"""
from django.urls import path
from . import notification_views

app_name = 'notifications'

urlpatterns = [
    # Dashboard and main views
    path('', notification_views.NotificationDashboardView.as_view(), name='dashboard'),
    path('history/', notification_views.notification_history_view, name='history'),
    path('detail/<int:notification_id>/', notification_views.notification_detail_view, name='detail'),
    
    # Template management
    path('templates/', notification_views.NotificationTemplateListView.as_view(), name='template_list'),
    path('templates/create/', notification_views.NotificationTemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:pk>/edit/', notification_views.NotificationTemplateUpdateView.as_view(), name='template_edit'),
    path('templates/<int:pk>/delete/', notification_views.NotificationTemplateDeleteView.as_view(), name='template_delete'),
    
    # AJAX endpoints
    path('ajax/send/', notification_views.send_notification_ajax, name='send_ajax'),
    path('ajax/send-bulk/', notification_views.send_bulk_notifications_ajax, name='send_bulk_ajax'),
    path('ajax/schedule/', notification_views.schedule_notification_ajax, name='schedule_ajax'),
    path('ajax/template-preview/<int:template_id>/', notification_views.template_preview_ajax, name='template_preview_ajax'),
    path('ajax/statistics/', notification_views.notification_statistics_ajax, name='statistics_ajax'),
    path('ajax/cancel/<int:notification_id>/', notification_views.cancel_notification_ajax, name='cancel_ajax'),
    path('ajax/retry/<int:notification_id>/', notification_views.retry_notification_ajax, name='retry_ajax'),
]