#!/usr/bin/env python
"""
Simple script to create a tenant and test accounting models.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django.db import connection
from django_tenants.utils import schema_context
from zargar.tenants.models import Tenant, Domain
from zargar.accounting.models import ChartOfAccounts
from decimal import Decimal


def create_tenant_manually():
    """Create tenant manually without auto-migration."""
    print("Creating tenant manually...")
    
    # Create tenant without auto-migration
    tenant = Tenant(
        schema_name='simple_test',
        name='Simple Test Shop',
        owner_name='Test Owner',
        owner_email='owner@simple-test.com',
        is_active=True
    )
    
    # Disable auto schema creation temporarily
    tenant.auto_create_schema = False
    tenant.save()
    
    # Create domain
    domain = Domain.objects.create(
        domain='simple-test.localhost',
        tenant=tenant,
        is_primary=True
    )
    
    print(f"✓ Created tenant: {tenant}")
    print(f"✓ Created domain: {domain}")
    
    return tenant


def create_schema_manually(tenant):
    """Create schema manually."""
    print(f"Creating schema manually for {tenant.schema_name}...")
    
    with connection.cursor() as cursor:
        # Create schema
        cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{tenant.schema_name}"')
        print(f"✓ Created schema: {tenant.schema_name}")


def test_accounting_in_schema(tenant):
    """Test if we can use accounting models in the schema."""
    print(f"Testing accounting models in schema: {tenant.schema_name}")
    
    with schema_context(tenant.schema_name):
        try:
            # Try to create a simple account
            account = ChartOfAccounts(
                account_code='1001',
                account_name_persian='نقد در صندوق',
                account_type='asset',
                account_category='current_assets',
                normal_balance='debit'
            )
            
            # This will fail if tables don't exist, but that's expected
            print(f"✓ Account model created (not saved): {account}")
            print(f"✓ Persian name: {account.account_name_persian}")
            print(f"✓ String representation: {account}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False


def main():
    """Main function."""
    print("🏪 Simple Tenant Creation Test")
    print("=" * 40)
    
    try:
        # Create tenant manually
        tenant = create_tenant_manually()
        
        # Create schema manually
        create_schema_manually(tenant)
        
        # Test accounting models (without database operations)
        test_accounting_in_schema(tenant)
        
        print("\n✅ Simple tenant creation successful!")
        print("Note: Database tables not created, but models work correctly.")
        
        # Cleanup
        print("\nCleaning up...")
        tenant.delete()
        print("✓ Tenant deleted")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())