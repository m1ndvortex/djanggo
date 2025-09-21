#!/usr/bin/env python
"""
Simple test to check if POSOfflineStorage table exists in tenant schema.
"""
import os
import sys
import django
from django.conf import settings

# Add the project root to the Python path
sys.path.insert(0, '/app')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django.db import connection
from django_tenants.utils import get_tenant_model, tenant_context
from zargar.pos.models import POSOfflineStorage

def check_table_exists():
    """Check if POSOfflineStorage table exists."""
    print("Checking if POSOfflineStorage table exists...")
    
    # Get tenant model
    Tenant = get_tenant_model()
    
    # Get first non-public tenant
    try:
        tenant = Tenant.objects.exclude(schema_name='public').first()
        if not tenant:
            print("No tenants found. Creating a test tenant...")
            # Create a test tenant
            tenant = Tenant.objects.create(
                schema_name='test_pos_offline',
                name='Test POS Offline',
                domain_url='test-pos-offline.localhost'
            )
            print(f"Created tenant: {tenant.name}")
        
        print(f"Using tenant: {tenant.name} (schema: {tenant.schema_name})")
        
        # Switch to tenant context
        with tenant_context(tenant):
            print(f"Current schema: {connection.schema_name}")
            
            # Check if table exists
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = %s 
                        AND table_name = 'pos_posofflinestorage'
                    );
                """, [connection.schema_name])
                
                table_exists = cursor.fetchone()[0]
                print(f"Table 'pos_posofflinestorage' exists: {table_exists}")
                
                if not table_exists:
                    print("Table does not exist. Listing all tables in schema:")
                    cursor.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = %s 
                        ORDER BY table_name;
                    """, [connection.schema_name])
                    
                    tables = cursor.fetchall()
                    for table in tables:
                        print(f"  - {table[0]}")
                
                # Try to create a POSOfflineStorage instance
                if table_exists:
                    print("\nTrying to create POSOfflineStorage instance...")
                    try:
                        offline_storage = POSOfflineStorage.objects.create(
                            device_id='TEST-DEVICE-001',
                            device_name='Test Device',
                            transaction_data={'test': 'data'}
                        )
                        print(f"Successfully created: {offline_storage.storage_id}")
                        
                        # Clean up
                        offline_storage.delete()
                        print("Cleaned up test record")
                        
                    except Exception as e:
                        print(f"Error creating POSOfflineStorage: {e}")
                        return False
                
                return table_exists
                
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("TABLE EXISTENCE CHECK")
    print("=" * 60)
    
    success = check_table_exists()
    
    if success:
        print("\n✅ Table check completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Table check failed!")
        sys.exit(1)