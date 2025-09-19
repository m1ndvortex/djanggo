"""
API URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    # Core authentication and user management API
    path('', include('zargar.core.api_urls')),
]