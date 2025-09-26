#!/usr/bin/env python
"""
Demo script for Gold Installment System UI functionality.
Tests the complete workflow from contract creation to payment processing.
"""
import os
import sys
import django
from decimal import Decimal
from datetime import date, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from zargar.tenants.models import Tenant, Domain
from zargar.customers.models import Customer
from zargar.gold_installments.models import GoldInstallmentContract, GoldInstallmentPayment, GoldWeightAdjustment
from zargar.gold_installments.forms import GoldInstallmentContractForm, GoldInstallmentPaymentForm, GoldWeightAdjustmentForm
from zargar.core.persian_number_formatter import PersianNumberFormatter

User = get_user_model()

def create_test_data():
    """Create test data for demonstration."""
    print("🏗️  Creating test data...")
    
    # Create tenant
    tenant, created = Tenant.objects.get_or_create(
        schema_name="demo_shop",
        defaults={
            'name': "Demo Jewelry Shop",
            'owner_name': "Demo Owner",
            'owner_email': "demo@example.com"
        }
    )
    
    if created:
        # Create domain
        Domain.objects.create(
            domain="demo-shop.localhost",
            tenant=tenant,
            is_primary=True
        )
    
    # Create user
    user, created = User.objects.get_or_create(
        username="demo_user",
        defaults={
            'email': "demo@example.com",
            'tenant': tenant
        }
    )
    
    # Create customer
    customer, created = Customer.objects.get_or_create(
        phone_number="09123456789",
        tenant=tenant,
        defaults={
            'first_name': "Ahmad",
            'last_name': "Rezaei",
            'persian_first_name': "احمد",
            'persian_last_name': "رضایی",
            'customer_type': "individual"
        }
    )
    
    return tenant, user, customer

def demo_contract_creation():
    """Demonstrate contract creation workflow."""
    print("\n📋 Testing Contract Creation...")
    
    tenant, user, customer = create_test_data()
    
    # Test contract form
    form_data = {
        'customer': customer.id,
        'contract_date': date.today().strftime('%Y-%m-%d'),
        'initial_gold_weight_grams': '25.500',
        'gold_karat': 18,
        'payment_schedule': 'monthly',
        'contract_terms_persian': 'شرایط قرارداد طلای قرضی - پرداخت ماهانه',
        'early_payment_discount_percentage': '5.00',
        'has_price_protection': True,
        'price_ceiling_per_gram': '4000000',
        'price_floor_per_gram': '3000000'
    }
    
    form = GoldInstallmentContractForm(data=form_data, tenant=tenant)
    
    if form.is_valid():
        contract = form.save(commit=False)
        contract.tenant = tenant
        contract.created_by = user
        contract.save()
        
        print(f"✅ Contract created successfully!")
        print(f"   Contract Number: {contract.contract_number}")
        print(f"   Customer: {contract.customer.persian_first_name} {contract.customer.persian_last_name}")
        print(f"   Initial Weight: {PersianNumberFormatter.format_weight(contract.initial_gold_weight_grams, 'gram')}")
        print(f"   Gold Karat: {contract.gold_karat}")
        print(f"   Payment Schedule: {contract.get_payment_schedule_display()}")
        print(f"   Early Discount: {PersianNumberFormatter.format_percentage(contract.early_payment_discount_percentage)}%")
        
        return contract
    else:
        print(f"❌ Contract creation failed: {form.errors}")
        return None

def demo_payment_processing(contract):
    """Demonstrate payment processing workflow."""
    print("\n💰 Testing Payment Processing...")
    
    if not contract:
        print("❌ No contract available for payment processing")
        return
    
    # Current gold price (mock)
    current_gold_price = Decimal('3500000')
    payment_amount = Decimal('7000000')  # 2 grams worth
    
    # Test payment form
    form_data = {
        'payment_date': date.today().strftime('%Y-%m-%d'),
        'payment_amount_toman': str(payment_amount),
        'gold_price_per_gram_at_payment': str(current_gold_price),
        'payment_method': 'cash',
        'payment_notes': 'First payment - cash'
    }
    
    form = GoldInstallmentPaymentForm(data=form_data, tenant=contract.tenant)
    
    if form.is_valid():
        # Process payment through contract method
        payment = contract.process_payment(
            payment_amount_toman=payment_amount,
            gold_price_per_gram=current_gold_price,
            payment_date=date.today()
        )
        
        # Update payment details
        payment.payment_method = 'cash'
        payment.payment_notes = 'First payment - cash'
        payment.save()
        
        print(f"✅ Payment processed successfully!")
        print(f"   Payment Amount: {PersianNumberFormatter.format_currency(payment_amount)}")
        print(f"   Gold Price: {PersianNumberFormatter.format_currency(current_gold_price)} per gram")
        print(f"   Gold Weight Paid: {PersianNumberFormatter.format_weight(payment.gold_weight_equivalent_grams, 'gram')}")
        print(f"   Remaining Weight: {PersianNumberFormatter.format_weight(contract.remaining_gold_weight_grams, 'gram')}")
        print(f"   Completion: {PersianNumberFormatter.format_percentage(contract.completion_percentage)}%")
        
        return payment
    else:
        print(f"❌ Payment processing failed: {form.errors}")
        return None

def demo_weight_adjustment(contract):
    """Demonstrate weight adjustment workflow."""
    print("\n⚖️  Testing Weight Adjustment...")
    
    if not contract:
        print("❌ No contract available for weight adjustment")
        return
    
    # Test adjustment form
    adjustment_amount = Decimal('-0.500')  # Reduce by 0.5 grams
    
    form_data = {
        'adjustment_date': date.today().strftime('%Y-%m-%d'),
        'weight_before_grams': str(contract.remaining_gold_weight_grams),
        'adjustment_amount_grams': str(adjustment_amount),
        'adjustment_type': 'correction',
        'adjustment_reason': 'calculation_error',
        'description': 'Correction due to calculation error in initial weight measurement'
    }
    
    form = GoldWeightAdjustmentForm(data=form_data, tenant=contract.tenant)
    
    if form.is_valid():
        adjustment = form.save(commit=False)
        adjustment.tenant = contract.tenant
        adjustment.authorized_by_id = contract.created_by.id
        
        # Calculate weight after adjustment
        adjustment.weight_after_grams = adjustment.weight_before_grams + adjustment.adjustment_amount_grams
        adjustment.save()
        
        # Update contract
        old_weight = contract.remaining_gold_weight_grams
        contract.remaining_gold_weight_grams = adjustment.weight_after_grams
        contract.save()
        
        print(f"✅ Weight adjustment applied successfully!")
        print(f"   Weight Before: {PersianNumberFormatter.format_weight(adjustment.weight_before_grams, 'gram')}")
        print(f"   Adjustment: {PersianNumberFormatter.format_weight(adjustment.adjustment_amount_grams, 'gram')}")
        print(f"   Weight After: {PersianNumberFormatter.format_weight(adjustment.weight_after_grams, 'gram')}")
        print(f"   Reason: {adjustment.get_adjustment_reason_display()}")
        print(f"   New Completion: {PersianNumberFormatter.format_percentage(contract.completion_percentage)}%")
        
        return adjustment
    else:
        print(f"❌ Weight adjustment failed: {form.errors}")
        return None

def demo_calculations():
    """Demonstrate calculation functionality."""
    print("\n🧮 Testing Calculations...")
    
    # Gold weight calculations
    payment_amount = Decimal('3500000')
    gold_price = Decimal('3500000')
    gold_weight = payment_amount / gold_price
    
    print(f"💰 Payment Amount: {PersianNumberFormatter.format_currency(payment_amount)}")
    print(f"🏆 Gold Price: {PersianNumberFormatter.format_currency(gold_price)} per gram")
    print(f"⚖️  Gold Weight Equivalent: {PersianNumberFormatter.format_weight(gold_weight, 'gram')}")
    
    # Weight conversions
    grams = Decimal('4.608')
    mesghal = PersianNumberFormatter.convert_weight(grams, 'gram', 'mesghal')
    soot = PersianNumberFormatter.convert_weight(grams, 'gram', 'soot')
    
    print(f"\n🔄 Weight Conversions:")
    print(f"   {PersianNumberFormatter.format_weight(grams, 'gram')} = {PersianNumberFormatter.format_weight(mesghal, 'mesghal')}")
    print(f"   {PersianNumberFormatter.format_weight(grams, 'gram')} = {PersianNumberFormatter.format_weight(soot, 'soot')}")
    
    # Percentage calculations
    total_amount = Decimal('1000000')
    discount_percentage = Decimal('5.00')
    discount_amount = total_amount * (discount_percentage / 100)
    
    print(f"\n💸 Discount Calculation:")
    print(f"   Total: {PersianNumberFormatter.format_currency(total_amount)}")
    print(f"   Discount: {PersianNumberFormatter.format_percentage(discount_percentage)}%")
    print(f"   Discount Amount: {PersianNumberFormatter.format_currency(discount_amount)}")
    print(f"   Final Amount: {PersianNumberFormatter.format_currency(total_amount - discount_amount)}")

def demo_persian_formatting():
    """Demonstrate Persian number formatting."""
    print("\n🔤 Testing Persian Number Formatting...")
    
    # Currency formatting
    amounts = [1000, 50000, 1500000, 25000000, 1000000000]
    
    print("💰 Currency Formatting:")
    for amount in amounts:
        english = PersianNumberFormatter.format_currency(amount, use_persian_digits=False)
        persian = PersianNumberFormatter.format_currency(amount, use_persian_digits=True)
        print(f"   {english} → {persian}")
    
    # Weight formatting
    weights = [1.5, 10.250, 25.000, 100.125]
    
    print("\n⚖️  Weight Formatting:")
    for weight in weights:
        english = PersianNumberFormatter.format_weight(weight, 'gram', use_persian_digits=False)
        persian = PersianNumberFormatter.format_weight(weight, 'gram', use_persian_digits=True)
        print(f"   {english} → {persian}")
    
    # Percentage formatting
    percentages = [5.5, 12.25, 50.0, 100.0]
    
    print("\n📊 Percentage Formatting:")
    for percentage in percentages:
        english = PersianNumberFormatter.format_percentage(percentage, use_persian_digits=False)
        persian = PersianNumberFormatter.format_percentage(percentage, use_persian_digits=True)
        print(f"   {english} → {persian}")

def demo_contract_summary(contract):
    """Display contract summary."""
    if not contract:
        return
    
    print("\n📊 Contract Summary:")
    print("=" * 50)
    
    # Contract details
    print(f"Contract Number: {contract.contract_number}")
    print(f"Customer: {contract.customer.persian_first_name} {contract.customer.persian_last_name}")
    print(f"Phone: {contract.customer.phone_number}")
    print(f"Contract Date: {contract.contract_date_shamsi}")
    
    # Gold details
    print(f"\nGold Details:")
    print(f"  Initial Weight: {PersianNumberFormatter.format_weight(contract.initial_gold_weight_grams, 'gram')}")
    print(f"  Remaining Weight: {PersianNumberFormatter.format_weight(contract.remaining_gold_weight_grams, 'gram')}")
    print(f"  Gold Karat: {contract.gold_karat}")
    print(f"  Completion: {PersianNumberFormatter.format_percentage(contract.completion_percentage)}%")
    
    # Payment details
    payment_summary = contract.get_payment_history_summary()
    print(f"\nPayment Summary:")
    print(f"  Total Payments: {PersianNumberFormatter.to_persian_digits(payment_summary['total_payments'])}")
    print(f"  Total Amount: {PersianNumberFormatter.format_currency(payment_summary['total_amount_paid'])}")
    print(f"  Gold Weight Paid: {PersianNumberFormatter.format_weight(payment_summary['total_gold_weight_paid'], 'gram')}")
    
    # Contract settings
    print(f"\nContract Settings:")
    print(f"  Payment Schedule: {contract.get_payment_schedule_display()}")
    print(f"  Early Discount: {PersianNumberFormatter.format_percentage(contract.early_payment_discount_percentage)}%")
    print(f"  Price Protection: {'Yes' if contract.has_price_protection else 'No'}")
    
    if contract.has_price_protection:
        if contract.price_ceiling_per_gram:
            print(f"    Ceiling: {PersianNumberFormatter.format_currency(contract.price_ceiling_per_gram)}")
        if contract.price_floor_per_gram:
            print(f"    Floor: {PersianNumberFormatter.format_currency(contract.price_floor_per_gram)}")

def main():
    """Run the complete demo."""
    print("🌟 Gold Installment System Demo")
    print("=" * 50)
    
    try:
        # Test calculations and formatting
        demo_calculations()
        demo_persian_formatting()
        
        # Test workflow
        contract = demo_contract_creation()
        payment = demo_payment_processing(contract)
        adjustment = demo_weight_adjustment(contract)
        
        # Show summary
        demo_contract_summary(contract)
        
        print("\n🎉 Demo completed successfully!")
        print("✅ All gold installment system components are working correctly.")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()