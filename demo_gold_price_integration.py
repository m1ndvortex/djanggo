#!/usr/bin/env python
"""
Demo script for gold price integration and payment processing.
Demonstrates the complete gold installment system with real-time price integration.
"""
import os
import sys
import django
from decimal import Decimal
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django_tenants.utils import connection
from zargar.gold_installments.services import (
    GoldPriceService,
    PaymentProcessingService,
    GoldPriceProtectionService
)
from zargar.gold_installments.models import GoldInstallmentContract
from zargar.customers.models import Customer
from zargar.tenants.models import Tenant, Domain
from zargar.core.models import User


def create_demo_data():
    """Create demo tenant, customer, and contract."""
    print("🏪 Creating demo tenant and customer...")
    
    # Switch to public schema for tenant operations
    connection.set_schema_to_public()
    
    # Create or get tenant
    tenant, created = Tenant.objects.get_or_create(
        schema_name="demo_shop",
        defaults={
            "name": "Demo Jewelry Shop",
            "owner_name": "Ahmad Rezaei",
            "owner_email": "ahmad@demoshop.com"
        }
    )
    
    # Create or get domain
    domain, created = Domain.objects.get_or_create(
        domain="demo-shop.localhost",
        defaults={
            "tenant": tenant,
            "is_primary": True
        }
    )
    
    # Switch to tenant schema for tenant-specific operations
    connection.set_tenant(tenant)
    
    # For demo purposes, we'll skip user creation
    user = None
    
    # Create or get customer
    customer, created = Customer.objects.get_or_create(
        phone_number="09123456789",
        defaults={
            "first_name": "Maryam",
            "last_name": "Hosseini",
            "persian_first_name": "مریم",
            "persian_last_name": "حسینی",
            "email": "maryam@example.com"
        }
    )
    
    # Create or get gold installment contract
    contract, created = GoldInstallmentContract.objects.get_or_create(
        customer=customer,
        defaults={
            "contract_date": datetime.now().date(),
            "initial_gold_weight_grams": Decimal('10.000'),
            "remaining_gold_weight_grams": Decimal('10.000'),
            "gold_karat": 18,
            "payment_schedule": 'monthly',
            "status": 'active',
            "early_payment_discount_percentage": Decimal('5.00'),
            "contract_terms_persian": "شرایط قرارداد طلای قرضی - نمونه آزمایشی"
        }
    )
    
    # Reset contract for demo if it was already completed
    if contract.status == 'completed':
        contract.remaining_gold_weight_grams = Decimal('10.000')
        contract.status = 'active'
        contract.save()
    
    print(f"✅ Created tenant: {tenant.name}")
    print(f"✅ Created customer: {customer.persian_first_name} {customer.persian_last_name}")
    print(f"✅ Created contract: {contract.contract_number}")
    print(f"   Initial gold weight: {contract.initial_gold_weight_grams} grams")
    print(f"   Gold karat: {contract.gold_karat}k")
    
    return tenant, customer, contract, user


def demo_gold_price_service():
    """Demonstrate gold price service functionality."""
    print("\n💰 Gold Price Service Demo")
    print("=" * 50)
    
    # Test different karats
    karats = [14, 18, 21, 24]
    
    for karat in karats:
        price_data = GoldPriceService.get_current_gold_price(karat)
        print(f"Gold {karat}k: {price_data['price_per_gram']:,} Toman/gram (Source: {price_data['source']})")
    
    # Test price trend
    print(f"\n📈 Price trend for 18k gold (last 7 days):")
    trend_data = GoldPriceService.get_price_trend(18, 7)
    for day_data in trend_data[-3:]:  # Show last 3 days
        print(f"   {day_data['date']}: {day_data['price_per_gram']:,} Toman/gram")
    
    # Test cache functionality
    print(f"\n🔄 Testing cache functionality...")
    import time
    start_time = time.time()
    price1 = GoldPriceService.get_current_gold_price(18)
    first_call_time = time.time() - start_time
    
    start_time = time.time()
    price2 = GoldPriceService.get_current_gold_price(18)
    second_call_time = time.time() - start_time
    
    print(f"   First call (API): {first_call_time:.3f}s")
    print(f"   Second call (cache): {second_call_time:.3f}s")
    print(f"   Cache speedup: {first_call_time/second_call_time:.1f}x faster")


def demo_price_protection(contract):
    """Demonstrate price protection functionality."""
    print("\n🛡️ Price Protection Demo")
    print("=" * 50)
    
    # Set up price protection
    result = GoldPriceProtectionService.setup_price_protection(
        contract=contract,
        ceiling_price=Decimal('4000000'),  # 4M Toman ceiling
        floor_price=Decimal('3000000')     # 3M Toman floor
    )
    
    print(f"✅ Price protection set up:")
    print(f"   Ceiling: {result['ceiling_price']:,} Toman/gram")
    print(f"   Floor: {result['floor_price']:,} Toman/gram")
    
    # Analyze impact
    impact = GoldPriceProtectionService.analyze_price_protection_impact(contract)
    
    print(f"\n📊 Price protection impact analysis:")
    print(f"   Protection active: {impact['protection_active']}")
    if impact['protection_active']:
        print(f"   Protection type: {impact['protection_type']}")
        print(f"   Market price: {impact['market_price']:,} Toman/gram")
        print(f"   Effective price: {impact['effective_price']:,} Toman/gram")
        print(f"   Customer benefit: {impact['customer_benefit']}")
        print(f"   Value impact: {impact['value_impact']:,} Toman")


def demo_payment_processing(contract):
    """Demonstrate payment processing functionality."""
    print("\n💳 Payment Processing Demo")
    print("=" * 50)
    
    print(f"Contract balance before payments: {contract.remaining_gold_weight_grams} grams")
    
    # Process first payment
    print(f"\n1️⃣ Processing first payment (2 grams worth)...")
    result1 = PaymentProcessingService.process_payment(
        contract=contract,
        payment_amount=Decimal('7000000'),  # Approximately 2 grams
        payment_method='cash',
        notes='First payment - cash'
    )
    
    if result1['success']:
        payment1 = result1['payment']
        print(f"   ✅ Payment processed successfully")
        print(f"   Amount: {payment1.payment_amount_toman:,} Toman")
        print(f"   Gold weight equivalent: {payment1.gold_weight_equivalent_grams} grams")
        print(f"   Gold price used: {payment1.effective_gold_price_per_gram:,} Toman/gram")
        print(f"   Remaining balance: {result1['remaining_balance']} grams")
        
        if payment1.price_protection_applied:
            print(f"   🛡️ Price protection was applied")
    
    # Process second payment
    print(f"\n2️⃣ Processing second payment (3 grams worth)...")
    result2 = PaymentProcessingService.process_payment(
        contract=contract,
        payment_amount=Decimal('10500000'),  # Approximately 3 grams
        payment_method='bank_transfer',
        notes='Second payment - bank transfer'
    )
    
    if result2['success']:
        payment2 = result2['payment']
        print(f"   ✅ Payment processed successfully")
        print(f"   Amount: {payment2.payment_amount_toman:,} Toman")
        print(f"   Gold weight equivalent: {payment2.gold_weight_equivalent_grams} grams")
        print(f"   Remaining balance: {result2['remaining_balance']} grams")
    
    # Calculate early payment savings
    print(f"\n💰 Early payment discount calculation...")
    savings = PaymentProcessingService.calculate_early_payment_savings(contract)
    
    if savings['eligible']:
        print(f"   ✅ Early payment discount available:")
        print(f"   Discount percentage: {savings['discount_percentage']}%")
        print(f"   Current balance value: {savings['current_balance_value']:,} Toman")
        print(f"   Discount amount: {savings['discount_amount']:,} Toman")
        print(f"   Final payment needed: {savings['final_payment_amount']:,} Toman")
        print(f"   Total savings: {savings['savings']:,} Toman")
        
        # Process final payment with discount
        print(f"\n3️⃣ Processing final payment with early discount...")
        result3 = PaymentProcessingService.process_payment(
            contract=contract,
            payment_amount=savings['current_balance_value'],
            payment_method='cash',
            apply_early_discount=True,
            notes='Final payment with early discount'
        )
        
        if result3['success']:
            payment3 = result3['payment']
            print(f"   ✅ Final payment processed with discount")
            print(f"   Original amount: {savings['current_balance_value']:,} Toman")
            print(f"   Discount applied: {payment3.discount_amount_toman:,} Toman")
            print(f"   Final amount paid: {payment3.payment_amount_toman:,} Toman")
            print(f"   Contract status: {contract.status}")
            
            if contract.status == 'completed':
                print(f"   🎉 Contract completed successfully!")


def demo_bidirectional_transactions(contract, user):
    """Demonstrate bidirectional transaction functionality."""
    print("\n🔄 Bidirectional Transactions Demo")
    print("=" * 50)
    
    print(f"Current balance: {contract.remaining_gold_weight_grams} grams")
    
    # Skip if no user available
    if not user:
        print("⚠️ Skipping bidirectional transactions demo (no user available)")
        return
    
    # Add debt (customer brings more gold)
    print(f"\n➕ Adding debt transaction (customer brings additional gold)...")
    result1 = PaymentProcessingService.process_bidirectional_transaction(
        contract=contract,
        transaction_type='debt',
        amount=Decimal('2.500'),
        description='Customer brought additional gold jewelry for installment',
        authorized_by=user
    )
    
    if result1['success']:
        print(f"   ✅ Debt transaction processed")
        print(f"   Added: {Decimal('2.500')} grams")
        print(f"   New balance: {result1['new_balance']} grams")
        print(f"   Balance type: {result1['balance_type']}")
    
    # Process credit adjustment
    print(f"\n➖ Processing credit adjustment (weight correction)...")
    result2 = PaymentProcessingService.process_bidirectional_transaction(
        contract=contract,
        transaction_type='credit',
        amount=Decimal('0.300'),
        description='Weight measurement correction after re-weighing',
        authorized_by=user
    )
    
    if result2['success']:
        print(f"   ✅ Credit adjustment processed")
        print(f"   Reduced: {Decimal('0.300')} grams")
        print(f"   Final balance: {result2['new_balance']} grams")
        print(f"   Balance type: {result2['balance_type']}")


def demo_contract_summary(contract):
    """Display contract summary."""
    print("\n📋 Contract Summary")
    print("=" * 50)
    
    # Refresh contract from database
    contract.refresh_from_db()
    
    print(f"Contract Number: {contract.contract_number}")
    print(f"Customer: {contract.customer.persian_first_name} {contract.customer.persian_last_name}")
    print(f"Initial Gold Weight: {contract.initial_gold_weight_grams} grams")
    print(f"Remaining Gold Weight: {contract.remaining_gold_weight_grams} grams")
    print(f"Completion Percentage: {contract.completion_percentage}%")
    print(f"Status: {contract.get_status_display()}")
    print(f"Balance Type: {contract.get_balance_type_display()}")
    
    # Payment history
    payments = contract.payments.all().order_by('payment_date')
    print(f"\n💳 Payment History ({payments.count()} payments):")
    
    total_paid = Decimal('0.00')
    total_gold_weight = Decimal('0.000')
    
    for i, payment in enumerate(payments, 1):
        print(f"   {i}. {payment.payment_date} - {payment.payment_amount_toman:,} Toman")
        print(f"      Gold weight: {payment.gold_weight_equivalent_grams} grams")
        print(f"      Method: {payment.get_payment_method_display()}")
        if payment.discount_applied:
            print(f"      Discount: {payment.discount_percentage}% ({payment.discount_amount_toman:,} Toman)")
        
        total_paid += payment.payment_amount_toman
        total_gold_weight += payment.gold_weight_equivalent_grams
    
    print(f"\n📊 Totals:")
    print(f"   Total Amount Paid: {total_paid:,} Toman")
    print(f"   Total Gold Weight Paid: {total_gold_weight} grams")
    
    # Adjustments
    adjustments = contract.weight_adjustments.all().order_by('adjustment_date')
    if adjustments.exists():
        print(f"\n⚖️ Weight Adjustments ({adjustments.count()} adjustments):")
        for i, adj in enumerate(adjustments, 1):
            sign = '+' if adj.adjustment_amount_grams > 0 else ''
            print(f"   {i}. {adj.adjustment_date} - {sign}{adj.adjustment_amount_grams} grams")
            print(f"      Type: {adj.get_adjustment_type_display()}")
            print(f"      Reason: {adj.get_adjustment_reason_display()}")


def main():
    """Run the complete demo."""
    print("🚀 ZARGAR Gold Price Integration & Payment Processing Demo")
    print("=" * 70)
    
    try:
        # Create demo data
        tenant, customer, contract, user = create_demo_data()
        
        # Demo gold price service
        demo_gold_price_service()
        
        # Demo price protection
        demo_price_protection(contract)
        
        # Demo payment processing
        demo_payment_processing(contract)
        
        # Demo bidirectional transactions (if contract not completed)
        if contract.status != 'completed':
            demo_bidirectional_transactions(contract, user)
        
        # Show final contract summary
        demo_contract_summary(contract)
        
        print(f"\n🎉 Demo completed successfully!")
        print(f"✨ All gold price integration and payment processing features demonstrated.")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())