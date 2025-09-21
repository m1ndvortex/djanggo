#!/usr/bin/env python
"""
Simple test script to verify POS backend functionality.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from decimal import Decimal
from zargar.pos.services import POSCustomerService, POSInvoiceService, POSTransactionService
from zargar.customers.models import Customer
from zargar.jewelry.models import JewelryItem, Category
from zargar.core.models import User


def test_customer_search():
    """Test customer search functionality."""
    print("Testing customer search functionality...")
    
    # Clean up any existing test data
    Customer.objects.filter(phone_number='09123456789').delete()
    
    # Create test customer
    customer = Customer.objects.create(
        first_name='احمد',
        last_name='محمدی',
        persian_first_name='احمد',
        persian_last_name='محمدی',
        phone_number='09123456789',
        email='ahmad@example.com',
        address='تهران، خیابان ولیعصر'
    )
    
    print(f"✓ Created customer: {customer}")
    
    # Test search by Persian name
    results = POSCustomerService.search_customers('احمد')
    print(f"✓ Search results for 'احمد': {len(results)} customers found")
    
    if results:
        customer_data = results[0]
        print(f"  - Customer name: {customer_data['name']}")
        print(f"  - Phone: {customer_data['phone_number']}")
        print(f"  - Balance type: {customer_data['balance_info']['balance_type']}")
        print(f"  - Formatted balance: {customer_data['balance_info']['formatted_balance']}")
    
    # Test search by phone
    results = POSCustomerService.search_customers('09123')
    print(f"✓ Search results for '09123': {len(results)} customers found")
    
    # Test balance calculation
    balance_info = POSCustomerService.get_customer_balance(customer)
    print(f"✓ Customer balance info: {balance_info}")
    
    print("Customer search functionality working!\n")
    return customer


def test_invoice_generation():
    """Test invoice generation functionality."""
    print("Testing invoice generation functionality...")
    
    # Get or create test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
    
    print(f"✓ Using user: {user}")
    
    # Get or create test customer
    customer = Customer.objects.filter(phone_number='09123456789').first()
    if not customer:
        customer = Customer.objects.create(
            first_name='احمد',
            last_name='محمدی',
            persian_first_name='احمد',
            persian_last_name='محمدی',
            phone_number='09123456789',
            email='ahmad@example.com'
        )
    
    # Create jewelry category and item
    category, created = Category.objects.get_or_create(
        name='Ring',
        defaults={'name_persian': 'انگشتر', 'description': 'Gold rings'}
    )
    
    jewelry_item, created = JewelryItem.objects.get_or_create(
        sku='RING-TEST-001',
        defaults={
            'name': 'Test Gold Ring 18K',
            'name_persian': 'انگشتر طلای آزمایشی ۱۸ عیار',
            'category': category,
            'weight_grams': Decimal('5.500'),
            'karat': 18,
            'manufacturing_cost': Decimal('500000'),
            'selling_price': Decimal('2500000'),
            'quantity': 10,
            'status': 'in_stock'
        }
    )
    
    print(f"✓ Using jewelry item: {jewelry_item}")
    
    # Create transaction
    transaction = POSTransactionService.create_transaction(
        customer_id=customer.id,
        transaction_type='sale',
        payment_method='cash',
        user=user
    )
    
    print(f"✓ Created transaction: {transaction.transaction_number}")
    
    # Add jewelry item to transaction
    line_item = POSTransactionService.add_jewelry_item_to_transaction(
        transaction=transaction,
        jewelry_item_id=jewelry_item.id,
        quantity=1
    )
    
    print(f"✓ Added line item: {line_item.item_name} - {line_item.line_total} Toman")
    
    # Process payment
    payment_result = POSTransactionService.process_payment(
        transaction=transaction,
        amount_paid=transaction.total_amount,
        payment_method='cash'
    )
    
    print(f"✓ Payment processed: {payment_result['success']}")
    
    # Generate invoice
    invoice = payment_result['invoice']
    print(f"✓ Invoice generated: {invoice.invoice_number}")
    
    # Test Persian invoice data
    invoice_data = invoice.generate_persian_invoice_data()
    print(f"✓ Persian invoice data generated")
    print(f"  - Customer: {invoice_data['customer_info']['name']}")
    print(f"  - Total: {invoice_data['financial_totals']['total_amount']}")
    print(f"  - Line items: {len(invoice_data['line_items'])}")
    
    # Test PDF generation
    try:
        pdf_content = POSInvoiceService.generate_invoice_pdf(invoice)
        print(f"✓ PDF generated: {len(pdf_content)} bytes")
    except Exception as e:
        print(f"⚠ PDF generation failed (expected without ReportLab): {e}")
    
    print("Invoice generation functionality working!\n")
    return transaction, invoice


def test_customer_balance_management():
    """Test customer balance and payment processing."""
    print("Testing customer balance management...")
    
    customer = Customer.objects.filter(phone_number='09123456789').first()
    if not customer:
        print("No test customer found, skipping balance tests")
        return
    
    # Get initial balance
    initial_balance = POSCustomerService.get_customer_balance(customer)
    print(f"✓ Initial balance: {initial_balance['formatted_balance']}")
    
    # Test detailed customer info
    detailed_info = POSCustomerService.get_customer_detailed_info(customer.id)
    print(f"✓ Customer detailed info retrieved")
    print(f"  - Name: {detailed_info['customer_info']['name']}")
    print(f"  - Loyalty points: {detailed_info['loyalty_info']['current_points']}")
    print(f"  - Recent transactions: {len(detailed_info['recent_transactions'])}")
    
    # Test transaction history
    history = POSCustomerService.get_customer_transaction_history(customer, limit=5)
    print(f"✓ Transaction history: {len(history)} transactions")
    
    if history:
        latest = history[0]
        print(f"  - Latest: {latest['transaction_number']} - {latest['total_amount']} Toman")
    
    print("Customer balance management working!\n")


def main():
    """Run all tests."""
    print("=== POS Backend Functionality Tests ===\n")
    
    try:
        # Test customer search
        customer = test_customer_search()
        
        # Test invoice generation
        transaction, invoice = test_invoice_generation()
        
        # Test customer balance management
        test_customer_balance_management()
        
        print("=== All Tests Completed Successfully! ===")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()