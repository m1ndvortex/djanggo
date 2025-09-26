#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django.urls import reverse_lazy
from django.conf import settings

print(f'ROOT_URLCONF: {settings.ROOT_URLCONF}')
print(f'PUBLIC_SCHEMA_URLCONF: {getattr(settings, "PUBLIC_SCHEMA_URLCONF", "Not set")}')

# Test URL resolution in public schema context
original_urlconf = settings.ROOT_URLCONF
try:
    settings.ROOT_URLCONF = settings.PUBLIC_SCHEMA_URLCONF
    url = reverse_lazy('admin_panel:unified_login')
    print(f'Unified login URL: {url}')
    print('URL resolution successful!')
except Exception as e:
    print(f'Error resolving URL: {e}')
    
    # Try to see what URLs are available
    from django.urls import get_resolver
    resolver = get_resolver()
    print(f'Available URL patterns: {[str(p) for p in resolver.url_patterns[:3]]}')
finally:
    settings.ROOT_URLCONF = original_urlconf