"""
URLs for reports module.
"""
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Placeholder URLs - will be implemented in later tasks
    path('', views.PlaceholderView.as_view(), name='index'),
]