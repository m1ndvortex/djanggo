#!/usr/bin/env python
"""
Simple test for offline POS API endpoints.
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

import json
from decimal import Decimal
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django_tenants.utils import get_tenant_model, tenant_context

from zargar.pos.models import POSOfflineStorage
from zargar.customers.models import Customer
from zargar.jewelry.models import JewelryItem, Category

User = get_user_model()


def test_offline_api():
    """Test offline POS API endpoints."""
    print("Testing Offline POS API...")
    
    # Get tenant
    Tenant = get_tenant_model()
    tenant = Tenant.objects.exclude(schema_name='public').first()
    
    if not tenant:
        print("No tenant found, skipping test")
        return False
    
    print(f"Using tenant: {tenant.name} (schema: {tenant.schema_name})")
    
    with tenant_context(tenant):
        # Create test user
        try:
            user = User.objects.get(username='api_test_user')
        except User.DoesNotExist:
            user = User.objects.create_user(
                username='api_test_user',
                email='apitest@example.com',
                password='testpass123'
            )
        
        # Create test data
        try:
            customer = Customer.objects.get(phone_number='09111111111')
        except Customer.DoesNotExist:
            customer = Customer.objects.create(
                first_name='علی',
                last_name='احمدی',
                persian_first_name='علی',
                persian_last_name='احمدی',
                phone_number='09111111111'
            )
        
        try:
            category = Category.objects.get(name='Test Rings')
        except Category.DoesNotExist:
            category = Category.objects.create(
                name='Test Rings',
                name_persian='انگشتر تست'
            )
        
        try:
            jewelry_item = JewelryItem.objects.get(sku='TEST-RING-001')
        except JewelryItem.DoesNotExist:
            jewelry_item = JewelryItem.objects.create(
                name='Test Gold Ring 18K',
                category=category,
                sku='TEST-RING-001',
                barcode='TEST-BARCODE-001',
                weight_grams=Decimal('5.500'),
                karat=18,
                manufacturing_cost=Decimal('500000.00'),
                selling_price=Decimal('2500000.00'),
                quantity=10,
                status='in_stock'
            )
        
        # Create client and login
        client = Client()
        login_success = client.login(username='api_test_user', password='testpass123')
        
        if not login_success:
            print("Failed to login user")
            return False
        
        print("✅ User logged in successfully")
        
        # Test 1: Create offline transaction
        print("\n1. Testing offline transaction creation API...")
        
        url = reverse('pos:api_offline_create')
        
        data = {
            'device_id': 'TEST-API-DEVICE-001',
            'device_name': 'Test API Device',
            'customer_id': customer.id,
            'line_items': [
                {
                    'jewelry_item_id': jewelry_item.id,
                    'item_name': 'Test Gold Ring 18K',
                    'item_sku': 'TEST-RING-001',
                    'quantity': 1,
                    'unit_price': '2500000.00',
                    'gold_weight_grams': '5.500',
                    'gold_karat': 18
                }
            ],
            'payment_method': 'cash',
            'amount_paid': '2500000.00',
            'transaction_type': 'sale'
        }
        
        try:
            response = client.post(
                url,
                data=json.dumps(data),
                content_type='application/json'
            )
            
            print(f"   Response status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = json.loads(response.content)
                if response_data.get('success'):
                    print(f"   ✅ Transaction created: {response_data['storage_id']}")
                    storage_id = response_data['storage_id']
                else:
                    print(f"   ❌ API returned error: {response_data.get('error')}")
                    return False
            else:
                print(f"   ❌ HTTP error: {response.status_code}")
                print(f"   Response: {response.content}")
                return False
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            return False
        
        # Test 2: Get offline status
        print("\n2. Testing offline status API...")
        
        url = reverse('pos:api_offline_status')
        
        try:
            response = client.get(url, {
                'device_id': 'TEST-API-DEVICE-001',
                'device_name': 'Test API Device'
            })
            
            print(f"   Response status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = json.loads(response.content)
                if response_data.get('success'):
                    summary = response_data['summary']
                    print(f"   ✅ Status retrieved:")
                    print(f"      Total transactions: {summary['total_transactions']}")
                    print(f"      Pending sync: {summary['pending_sync']}")
                    print(f"      Synced: {summary['synced']}")
                else:
                    print(f"   ❌ API returned error: {response_data.get('error')}")
                    return False
            else:
                print(f"   ❌ HTTP error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            return False
        
        # Test 3: Export offline data
        print("\n3. Testing offline export API...")
        
        url = reverse('pos:api_offline_export')
        
        try:
            response = client.get(url, {
                'device_id': 'TEST-API-DEVICE-001',
                'device_name': 'Test API Device'
            })
            
            print(f"   Response status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = json.loads(response.content)
                if response_data.get('success'):
                    export_data = response_data['export_data']
                    print(f"   ✅ Export data retrieved:")
                    print(f"      Device ID: {export_data['device_id']}")
                    print(f"      Transactions count: {len(export_data['transactions'])}")
                else:
                    print(f"   ❌ API returned error: {response_data.get('error')}")
                    return False
            else:
                print(f"   ❌ HTTP error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            return False
        
        print("\n✅ All API tests passed!")
        return True


if __name__ == '__main__':
    print("=" * 60)
    print("OFFLINE POS API TESTS")
    print("=" * 60)
    
    success = test_offline_api()
    
    if success:
        print("\n🎉 API tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ API tests failed!")
        sys.exit(1)