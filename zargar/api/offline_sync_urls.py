"""
URL configuration for offline synchronization API endpoints.
"""
from django.urls import path
from . import offline_sync

urlpatterns = [
    path('manifest/', offline_sync.get_sync_manifest, name='sync-manifest'),
    path('download/', offline_sync.download_sync_data, name='sync-download'),
    path('upload/transactions/', offline_sync.upload_offline_transactions, name='sync-upload-transactions'),
    path('upload/inventory/', offline_sync.upload_inventory_changes, name='sync-upload-inventory'),
    path('status/', offline_sync.get_sync_status, name='sync-status'),
    path('resolve-conflicts/', offline_sync.resolve_sync_conflicts, name='sync-resolve-conflicts'),
]