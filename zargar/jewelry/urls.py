"""
URLs for jewelry module.
"""
from django.urls import path
from . import views

app_name = 'jewelry'

urlpatterns = [
    # Placeholder URLs - will be implemented in later tasks
    path('', views.PlaceholderView.as_view(), name='index'),
]