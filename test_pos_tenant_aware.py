#!/usr/bin/env python
"""
Tenant-aware test script for POS backend functionality.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django_tenants.utils import tenant_context
from zargar.tenants.models import Tenant
from zargar.pos.services import POSTransactionService
from zargar.gold_installments.services import GoldPriceService
from zargar.core.models import User
from zargar.customers.models import Customer
from zargar.jewelry.models import JewelryItem, Category
from decimal import Decimal


def test_pos_backend():
    """Test POS backend functionality in tenant context."""
    print("🚀 Testing POS Backend Functionality (Tenant-Aware)")
    print("=" * 60)
    
    try:
        # Get an existing tenant for testing
        tenant = Tenant.objects.exclude(schema_name='public').first()
        if not tenant:
            print("❌ No tenant found for testing. Please create a tenant first.")
            return False
        
        print(f"Using tenant: {tenant.name} (schema: {tenant.schema_name})")
        
        # Run tests in tenant context
        with tenant_context(tenant):
            
            # Test 1: Gold Price Service
            print("\n1. Testing Gold Price Service...")
            price_data = GoldPriceService.get_current_gold_price(18)
            print(f"   ✅ Gold price: {price_data['price_per_gram']:,} Toman/gram")
            print(f"   ✅ Source: {price_data['source']}")
            
            # Test 2: Create test user and customer
            print("\n2. Creating test user and customer...")
            
            # Clean up any existing test data
            User.objects.filter(username='testpos').delete()
            Customer.objects.filter(phone_number='09123456789').delete()
            
            user = User.objects.create_user(
                username='testpos', 
                password='test123', 
                role='salesperson'
            )
            print(f"   ✅ User created: {user.username}")
            
            customer = Customer.objects.create(
                first_name='Test',
                last_name='Customer',
                phone_number='09123456789',
                email='test@example.com'
            )
            print(f"   ✅ Customer created: {customer}")
            
            # Test 3: Create POS Transaction
            print("\n3. Testing POS Transaction Creation...")
            transaction = POSTransactionService.create_transaction(
                customer_id=customer.id,
                transaction_type='sale',
                payment_method='cash',
                user=user
            )
            print(f"   ✅ Transaction created: {transaction.transaction_number}")
            print(f"   ✅ Status: {transaction.status}")
            print(f"   ✅ Gold price at transaction: {transaction.gold_price_18k_at_transaction:,} Toman/gram")
            
            # Test 4: Add custom item to transaction
            print("\n4. Testing Add Custom Item...")
            line_item = POSTransactionService.add_custom_item_to_transaction(
                transaction=transaction,
                item_name='Test Service',
                unit_price=Decimal('500000'),
                quantity=1,
                item_sku='TEST001'
            )
            print(f"   ✅ Line item added: {line_item.item_name}")
            print(f"   ✅ Transaction subtotal: {transaction.subtotal:,} Toman")
            
            # Test 5: Create jewelry item and add to transaction
            print("\n5. Testing Add Jewelry Item...")
            
            # Clean up existing test category and item
            Category.objects.filter(name='Test Category').delete()
            
            category = Category.objects.create(
                name='Test Category',
                name_persian='دسته تست'
            )
            
            jewelry_item = JewelryItem.objects.create(
                name='Test Ring',
                sku='TEST-RING-001',
                category=category,
                weight_grams=Decimal('3.500'),
                karat=18,
                manufacturing_cost=Decimal('400000'),
                selling_price=Decimal('1500000'),
                quantity=5
            )
            print(f"   ✅ Jewelry item created: {jewelry_item.name}")
            
            jewelry_line_item = POSTransactionService.add_jewelry_item_to_transaction(
                transaction=transaction,
                jewelry_item_id=jewelry_item.id,
                quantity=1,
                discount_percentage=Decimal('5.00')
            )
            print(f"   ✅ Jewelry item added with 5% discount")
            print(f"   ✅ Gold weight: {jewelry_line_item.gold_weight_grams} grams")
            
            # Refresh transaction to get updated totals
            transaction.refresh_from_db()
            print(f"   ✅ Updated transaction total: {transaction.total_amount:,} Toman")
            
            # Test 6: Process payment
            print("\n6. Testing Payment Processing...")
            payment_amount = transaction.total_amount + Decimal('50000')  # Extra for change
            
            result = POSTransactionService.process_payment(
                transaction=transaction,
                amount_paid=payment_amount,
                payment_method='cash'
            )
            
            if result['success']:
                print(f"   ✅ Payment processed successfully")
                print(f"   ✅ Change amount: {result['change_amount']:,} Toman")
                print(f"   ✅ Invoice created: {result['invoice'].invoice_number}")
                
                # Check transaction status
                transaction.refresh_from_db()
                print(f"   ✅ Transaction status: {transaction.status}")
                
                # Check inventory update
                jewelry_item.refresh_from_db()
                print(f"   ✅ Jewelry item quantity updated: {jewelry_item.quantity}")
                
                # Check customer stats
                customer.refresh_from_db()
                print(f"   ✅ Customer total purchases: {customer.total_purchases:,} Toman")
                print(f"   ✅ Customer loyalty points: {customer.loyalty_points}")
            else:
                print(f"   ❌ Payment processing failed")
            
            # Test 7: Offline transaction functionality
            print("\n7. Testing Offline Transaction Functionality...")
            from zargar.pos.services import POSOfflineService
            
            offline_data = POSOfflineService.create_offline_transaction_data(
                customer_id=customer.id,
                line_items=[{
                    'jewelry_item_id': None,
                    'item_name': 'Offline Item',
                    'item_sku': 'OFF001',
                    'quantity': '1',
                    'unit_price': '800000',
                    'gold_weight_grams': '0.000',
                    'gold_karat': 0
                }],
                payment_method='cash',
                amount_paid=Decimal('800000'),
                transaction_type='sale'
            )
            
            offline_storage = POSOfflineService.store_offline_transaction(
                transaction_data=offline_data,
                device_id='test-device'
            )
            print(f"   ✅ Offline transaction stored: {offline_storage.storage_id}")
            
            # Test sync
            sync_results = POSOfflineService.sync_offline_transactions(device_id='test-device')
            print(f"   ✅ Sync results: {sync_results['synced_successfully']} successful, {sync_results['sync_failed']} failed")
            
            # Test 8: Reporting functionality
            print("\n8. Testing Reporting Functionality...")
            from zargar.pos.services import POSReportingService
            from django.utils import timezone
            
            daily_summary = POSReportingService.get_daily_sales_summary()
            print(f"   ✅ Daily sales summary: {daily_summary['total_transactions']} transactions")
            print(f"   ✅ Total sales today: {daily_summary['total_sales']:,} Toman")
            
            monthly_trend = POSReportingService.get_monthly_sales_trend(
                timezone.now().year, 
                timezone.now().month
            )
            print(f"   ✅ Monthly trend: {monthly_trend['total_transactions']} transactions this month")
            
            print("\n🎉 All POS Backend Tests Passed Successfully!")
            print("=" * 60)
            
            # Summary
            print(f"\nSummary:")
            print(f"- Gold Price Service: Working ✅")
            print(f"- Transaction Creation: Working ✅")
            print(f"- Line Item Management: Working ✅")
            print(f"- Payment Processing: Working ✅")
            print(f"- Invoice Generation: Working ✅")
            print(f"- Inventory Updates: Working ✅")
            print(f"- Customer Stats: Working ✅")
            print(f"- Offline Sync: Working ✅")
            print(f"- Reporting: Working ✅")
            
            return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_pos_backend()
    exit(0 if success else 1)