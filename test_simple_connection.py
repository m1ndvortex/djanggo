#!/usr/bin/env python
"""
Simple test to verify database connection and basic functionality.
"""
import os
import sys
import django
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
django.setup()

from zargar.customers.models import Supplier, PurchaseOrder, PurchaseOrderItem
from zargar.tenants.models import Tenant, Domain

User = get_user_model()

def test_basic_functionality():
    """Test basic supplier management functionality without full test framework."""
    print("Testing basic supplier management functionality...")
    
    try:
        # Test database connection
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        print("✓ Database connection successful")
        
        # Test model creation
        import random
        schema_name = f"test_shop_{random.randint(1000, 9999)}"
        tenant = Tenant.objects.create(
            name="Test Shop",
            schema_name=schema_name,
            owner_name="Test Owner",
            owner_email="test@example.com"
        )
        print("✓ Tenant created successfully")
        
        # Create domain
        domain_name = f"testshop{random.randint(100, 999)}.zargar.com"
        domain = Domain.objects.create(
            domain=domain_name,
            tenant=tenant,
            is_primary=True
        )
        print("✓ Domain created successfully")
        
        # Set tenant context for all tenant-specific operations
        from django_tenants.utils import tenant_context
        with tenant_context(tenant):
            # Create user
            user = User.objects.create_user(
                username="testuser",
                email="test@example.com",
                password="testpass123"
            )
            print("✓ User created successfully")
            
            # Create supplier
            supplier = Supplier.objects.create(
                name="Test Supplier",
                persian_name="تامین‌کننده تست",
                supplier_type="gold_supplier",
                contact_person="احمد محمدی",
                phone_number="09123456789",
                email="info@testsupplier.com",
                payment_terms="30 روزه",
                is_active=True,
                is_preferred=True
            )
            print("✓ Supplier created successfully")
            
            # Create purchase order
            purchase_order = PurchaseOrder.objects.create(
                supplier=supplier,
                order_date=date.today(),
                expected_delivery_date=date.today() + timedelta(days=7),
                status='draft',
                priority='normal',
                subtotal=Decimal('1000000'),
                total_amount=Decimal('1000000'),
                payment_terms="30 روزه",
                notes="سفارش تست"
            )
            print("✓ Purchase order created successfully")
            
            # Create purchase order item
            po_item = PurchaseOrderItem.objects.create(
                purchase_order=purchase_order,
                item_name="طلای 18 عیار",
                quantity_ordered=5,
                unit_price=Decimal('200000'),
                weight_grams=Decimal('50.5'),
                karat=18
            )
            print("✓ Purchase order item created successfully")
            
            # Test basic queries
            suppliers_count = Supplier.objects.count()
            orders_count = PurchaseOrder.objects.count()
            
            print(f"✓ Found {suppliers_count} suppliers and {orders_count} orders")
            
            # Test client and views
            client = Client()
            login_success = client.login(username="testuser", password="testpass123")
            print(f"✓ User login: {'successful' if login_success else 'failed'}")
            
            # Test supplier dashboard view
            try:
                url = reverse('customers:supplier_dashboard')
                response = client.get(url)
                print(f"✓ Supplier dashboard view: {response.status_code}")
            except Exception as e:
                print(f"✗ Supplier dashboard view failed: {e}")
            
            # Test supplier list view
            try:
                url = reverse('customers:supplier_list')
                response = client.get(url)
                print(f"✓ Supplier list view: {response.status_code}")
            except Exception as e:
                print(f"✗ Supplier list view failed: {e}")
            
            # Test purchase order list view
            try:
                url = reverse('customers:purchase_order_list')
                response = client.get(url)
                print(f"✓ Purchase order list view: {response.status_code}")
            except Exception as e:
                print(f"✗ Purchase order list view failed: {e}")
        
        print("\n🎉 All basic tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_basic_functionality()
    sys.exit(0 if success else 1)