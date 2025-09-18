"""
URLs for POS module.
"""
from django.urls import path
from . import views

app_name = 'pos'

urlpatterns = [
    # Placeholder URLs - will be implemented in later tasks
    path('', views.PlaceholderView.as_view(), name='index'),
]