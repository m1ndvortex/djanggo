#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from zargar.tenants.models import Domain

print("Checking configured domains:")
domains = Domain.objects.all()
for domain in domains:
    tenant_name = domain.tenant.name if domain.tenant else "Public"
    print(f'Domain: {domain.domain}, Tenant: {tenant_name}, Primary: {domain.is_primary}')

if not domains.exists():
    print("No domains configured!")
    print("This might be why the URLs are not working.")