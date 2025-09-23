#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django.test import Client
from django.urls import reverse

# Test with admin domain
print("Testing with admin.localhost domain:")
client = Client(HTTP_HOST='admin.localhost')

print("\nTesting /admin/ redirect:")
response = client.get('/admin/')
print(f'Status: {response.status_code}')
if hasattr(response, 'url'):
    print(f'Redirect URL: {response.url}')

print("\nTesting /super-panel/ access:")
response = client.get('/super-panel/')
print(f'Status: {response.status_code}')

# Test URL resolution with admin domain
try:
    url = reverse('admin_panel:dashboard')
    print(f'Dashboard URL resolved: {url}')
except Exception as e:
    print(f'Error resolving dashboard URL: {e}')

# Test unified login URL
try:
    url = reverse('admin_panel:unified_login')
    print(f'Unified login URL resolved: {url}')
except Exception as e:
    print(f'Error resolving unified login URL: {e}')