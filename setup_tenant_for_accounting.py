#!/usr/bin/env python
"""
Setup script to create a test tenant and apply accounting migrations.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from zargar.tenants.models import Tenant, Domain
from django.core.management import call_command


def main():
    """Create test tenant and apply migrations."""
    print("🏪 Setting up tenant for accounting system")
    print("=" * 50)
    
    try:
        # Create test tenant
        print("Creating test tenant...")
        tenant = Tenant.objects.create(
            schema_name='test_accounting',
            name='Test Accounting Shop',
            owner_name='Test Owner',
            owner_email='owner@test-accounting.com',
            is_active=True
        )
        print(f"✓ Created tenant: {tenant}")
        
        # Create domain
        domain = Domain.objects.create(
            domain='test-accounting.localhost',
            tenant=tenant,
            is_primary=True
        )
        print(f"✓ Created domain: {domain}")
        
        print("\n✅ Test tenant created successfully!")
        print(f"Schema name: {tenant.schema_name}")
        print(f"Domain: {domain.domain}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())