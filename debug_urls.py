#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django.conf import settings
from django.urls import get_resolver
from django.test import Client

print(f'ROOT_URLCONF: {settings.ROOT_URLCONF}')
print(f'PUBLIC_SCHEMA_URLCONF: {getattr(settings, "PUBLIC_SCHEMA_URLCONF", "Not set")}')

# Test URL resolution
resolver = get_resolver()
print(f'URL resolver: {resolver}')

# Test client request
client = Client()
print("\nTesting /admin/ redirect:")
response = client.get('/admin/')
print(f'Status: {response.status_code}')
if hasattr(response, 'url'):
    print(f'Redirect URL: {response.url}')

print("\nTesting /super-panel/ access:")
response = client.get('/super-panel/')
print(f'Status: {response.status_code}')

# Check if admin_panel URLs are loaded
try:
    from django.urls import reverse
    url = reverse('admin_panel:dashboard')
    print(f'Dashboard URL resolved: {url}')
except Exception as e:
    print(f'Error resolving dashboard URL: {e}')