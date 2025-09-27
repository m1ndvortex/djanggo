"""
URL configuration for push notification API endpoints.
"""
from django.urls import path
from . import push_notification_api

urlpatterns = [
    path('send/', push_notification_api.send_push_notification, name='push-send'),
    path('payment-reminder/', push_notification_api.send_payment_reminder_notification, name='push-payment-reminder'),
    path('birthday/', push_notification_api.send_birthday_notification, name='push-birthday'),
    path('appointment-reminder/', push_notification_api.send_appointment_reminder_notification, name='push-appointment-reminder'),
    path('history/', push_notification_api.get_notification_history, name='push-history'),
    path('mark-read/', push_notification_api.mark_notification_read, name='push-mark-read'),
    path('statistics/', push_notification_api.get_notification_statistics, name='push-statistics'),
    path('test/', push_notification_api.test_push_notification, name='push-test'),
]