"""
Tests for POS customer lookup and credit/debt management backend functionality.
Tests customer search, balance calculations, and payment processing.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing models
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from zargar.pos.models import POSTransaction, POSTransactionLineItem
from zargar.pos.services import POSCustomerService, POSTransactionService
from zargar.customers.models import Customer, CustomerNote
from zargar.jewelry.models import JewelryItem, Category
from zargar.core.models import User


@pytest.mark.django_db
class TestPOSCustomerLookup(TestCase):
    """Test POS customer lookup functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test customers
        self.customer1 = Customer.objects.create(
            first_name='احمد',
            last_name='محمدی',
            persian_first_name='احمد',
            persian_last_name='محمدی',
            phone_number='09123456789',
            email='ahmad@example.com',
            address='تهران، خیابان ولیعصر',
            national_id='1234567890',
            loyalty_points=1500,
            total_purchases=Decimal('5000000'),
            is_vip=True
        )
        
        self.customer2 = Customer.objects.create(
            first_name='فاطمه',
            last_name='احمدی',
            persian_first_name='فاطمه',
            persian_last_name='احمدی',
            phone_number='09987654321',
            email='fateme@example.com',
            loyalty_points=500,
            total_purchases=Decimal('1200000')
        )
        
        self.customer3 = Customer.objects.create(
            first_name='John',
            last_name='Smith',
            phone_number='09111222333',
            email='john@example.com',
            loyalty_points=0,
            total_purchases=Decimal('0')
        )
        
        # Create jewelry category and item
        self.category = Category.objects.create(
            name='Ring',
            name_persian='انگشتر'
        )
        
        self.jewelry_item = JewelryItem.objects.create(
            name='Gold Ring 18K',
            category=self.category,
            sku='RING-001',
            weight_grams=Decimal('5.500'),
            karat=18,
            selling_price=Decimal('2500000'),
            quantity=10,
            status='in_stock'
        )
    
    def test_search_customers_by_persian_name(self):
        """Test searching customers by Persian name."""
        results = POSCustomerService.search_customers('احمد')
        
        self.assertEqual(len(results), 1)
        customer_data = results[0]
        
        self.assertEqual(customer_data['id'], self.customer1.id)
        self.assertEqual(customer_data['name'], 'احمد محمدی')
        self.assertEqual(customer_data['full_persian_name'], 'احمد محمدی')
        self.assertEqual(customer_data['phone_number'], '09123456789')
        self.assertTrue(customer_data['is_vip'])
        self.assertEqual(customer_data['loyalty_points'], 1500)
    
    def test_search_customers_by_phone_number(self):
        """Test searching customers by phone number."""
        results = POSCustomerService.search_customers('0912345')
        
        self.assertEqual(len(results), 1)
        customer_data = results[0]
        self.assertEqual(customer_data['id'], self.customer1.id)
        self.assertEqual(customer_data['phone_number'], '09123456789')
    
    def test_search_customers_by_email(self):
        """Test searching customers by email."""
        results = POSCustomerService.search_customers('fateme@')
        
        self.assertEqual(len(results), 1)
        customer_data = results[0]
        self.assertEqual(customer_data['id'], self.customer2.id)
        self.assertEqual(customer_data['email'], 'fateme@example.com')
    
    def test_search_customers_by_national_id(self):
        """Test searching customers by national ID."""
        results = POSCustomerService.search_customers('123456')
        
        self.assertEqual(len(results), 1)
        customer_data = results[0]
        self.assertEqual(customer_data['id'], self.customer1.id)
    
    def test_search_customers_by_english_name(self):
        """Test searching customers by English name."""
        results = POSCustomerService.search_customers('John')
        
        self.assertEqual(len(results), 1)
        customer_data = results[0]
        self.assertEqual(customer_data['id'], self.customer3.id)
        self.assertEqual(customer_data['name'], 'John Smith')
    
    def test_search_customers_empty_query(self):
        """Test that empty or short queries return no results."""
        results = POSCustomerService.search_customers('')
        self.assertEqual(len(results), 0)
        
        results = POSCustomerService.search_customers('a')
        self.assertEqual(len(results), 0)
    
    def test_search_customers_limit(self):
        """Test search results limit."""
        # Create many customers
        for i in range(25):
            Customer.objects.create(
                first_name=f'Customer{i}',
                last_name='Test',
                phone_number=f'0912345{i:04d}',
                email=f'customer{i}@test.com'
            )
        
        results = POSCustomerService.search_customers('Customer', limit=10)
        self.assertEqual(len(results), 10)
    
    def test_search_customers_includes_balance_info(self):
        """Test that search results include balance information."""
        results = POSCustomerService.search_customers('احمد')
        
        self.assertEqual(len(results), 1)
        customer_data = results[0]
        
        self.assertIn('balance_info', customer_data)
        balance_info = customer_data['balance_info']
        
        self.assertIn('current_balance', balance_info)
        self.assertIn('balance_type', balance_info)
        self.assertIn('total_purchases', balance_info)
        self.assertIn('formatted_balance', balance_info)


@pytest.mark.django_db
class TestPOSCustomerBalance(TestCase):
    """Test customer balance calculations and management."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.customer = Customer.objects.create(
            first_name='احمد',
            last_name='محمدی',
            persian_first_name='احمد',
            persian_last_name='محمدی',
            phone_number='09123456789',
            email='ahmad@example.com'
        )
        
        self.category = Category.objects.create(
            name='Ring',
            name_persian='انگشتر'
        )
        
        self.jewelry_item = JewelryItem.objects.create(
            name='Gold Ring 18K',
            category=self.category,
            sku='RING-001',
            weight_grams=Decimal('5.500'),
            karat=18,
            selling_price=Decimal('1000000'),
            quantity=10,
            status='in_stock'
        )
    
    def test_customer_balance_zero_initial(self):
        """Test that new customer has zero balance."""
        balance_info = POSCustomerService.get_customer_balance(self.customer)
        
        self.assertEqual(balance_info['current_balance'], 0.0)
        self.assertEqual(balance_info['balance_type'], 'zero')
        self.assertEqual(balance_info['total_purchases'], 0.0)
        self.assertEqual(balance_info['total_payments'], 0.0)
        self.assertEqual(balance_info['formatted_balance'], 'تسویه')
    
    def test_customer_balance_with_completed_sale(self):
        """Test customer balance after completed sale (fully paid)."""
        # Create and complete transaction
        transaction = POSTransactionService.create_transaction(
            customer_id=self.customer.id,
            transaction_type='sale',
            payment_method='cash',
            user=self.user
        )
        
        POSTransactionService.add_jewelry_item_to_transaction(
            transaction=transaction,
            jewelry_item_id=self.jewelry_item.id,
            quantity=1
        )
        
        POSTransactionService.process_payment(
            transaction=transaction,
            amount_paid=transaction.total_amount,  # Fully paid
            payment_method='cash'
        )
        
        # Check balance (should be zero since fully paid)
        balance_info = POSCustomerService.get_customer_balance(self.customer)
        
        self.assertEqual(balance_info['current_balance'], 0.0)
        self.assertEqual(balance_info['balance_type'], 'zero')
        self.assertEqual(balance_info['total_purchases'], float(transaction.total_amount))
        self.assertEqual(balance_info['total_payments'], float(transaction.amount_paid))
    
    def test_customer_balance_with_partial_payment(self):
        """Test customer balance with partial payment (customer owes money)."""
        # Create transaction
        transaction = POSTransactionService.create_transaction(
            customer_id=self.customer.id,
            transaction_type='sale',
            payment_method='cash',
            user=self.user
        )
        
        POSTransactionService.add_jewelry_item_to_transaction(
            transaction=transaction,
            jewelry_item_id=self.jewelry_item.id,
            quantity=1
        )
        
        # Pay only half
        partial_payment = transaction.total_amount / 2
        transaction.amount_paid = partial_payment
        transaction.status = 'completed'  # Mark as completed for testing
        transaction.save()
        
        # Check balance (customer should owe money)
        balance_info = POSCustomerService.get_customer_balance(self.customer)
        
        expected_debt = float(transaction.total_amount - partial_payment)
        self.assertEqual(balance_info['current_balance'], expected_debt)
        self.assertEqual(balance_info['balance_type'], 'debt')
        self.assertIn('بدهکار', balance_info['formatted_balance'])
    
    def test_customer_balance_with_overpayment(self):
        """Test customer balance with overpayment (shop owes money to customer)."""
        # Create transaction
        transaction = POSTransactionService.create_transaction(
            customer_id=self.customer.id,
            transaction_type='sale',
            payment_method='cash',
            user=self.user
        )
        
        POSTransactionService.add_jewelry_item_to_transaction(
            transaction=transaction,
            jewelry_item_id=self.jewelry_item.id,
            quantity=1
        )
        
        # Pay more than required
        overpayment = transaction.total_amount + Decimal('500000')
        transaction.amount_paid = overpayment
        transaction.status = 'completed'
        transaction.save()
        
        # Check balance (shop should owe money to customer)
        balance_info = POSCustomerService.get_customer_balance(self.customer)
        
        expected_credit = float(overpayment - transaction.total_amount)
        self.assertEqual(balance_info['current_balance'], -expected_credit)
        self.assertEqual(balance_info['balance_type'], 'credit')
        self.assertIn('بستانکار', balance_info['formatted_balance'])
    
    def test_customer_balance_with_return(self):
        """Test customer balance calculation with return transactions."""
        # Create sale transaction
        sale_transaction = POSTransactionService.create_transaction(
            customer_id=self.customer.id,
            transaction_type='sale',
            payment_method='cash',
            user=self.user
        )
        
        POSTransactionService.add_jewelry_item_to_transaction(
            transaction=sale_transaction,
            jewelry_item_id=self.jewelry_item.id,
            quantity=1
        )
        
        POSTransactionService.process_payment(
            transaction=sale_transaction,
            amount_paid=sale_transaction.total_amount,
            payment_method='cash'
        )
        
        # Create return transaction
        return_transaction = POSTransactionService.create_transaction(
            customer_id=self.customer.id,
            transaction_type='return',
            payment_method='cash',
            user=self.user
        )
        
        return_transaction.total_amount = Decimal('300000')  # Partial return
        return_transaction.status = 'completed'
        return_transaction.save()
        
        # Check balance
        balance_info = POSCustomerService.get_customer_balance(self.customer)
        
        expected_credit = 300000.0  # Return amount creates credit
        self.assertEqual(balance_info['current_balance'], -expected_credit)
        self.assertEqual(balance_info['balance_type'], 'credit')
        self.assertEqual(balance_info['total_returns'], 300000.0)
    
    def test_process_customer_payment(self):
        """Test processing customer payment to reduce debt."""
        # Create debt by partial payment
        transaction = POSTransactionService.create_transaction(
            customer_id=self.customer.id,
            transaction_type='sale',
            payment_method='cash',
            user=self.user
        )
        
        POSTransactionService.add_jewelry_item_to_transaction(
            transaction=transaction,
            jewelry_item_id=self.jewelry_item.id,
            quantity=1
        )
        
        # Pay only half initially
        partial_payment = transaction.total_amount / 2
        transaction.amount_paid = partial_payment
        transaction.status = 'completed'
        transaction.save()
        
        # Verify debt exists
        balance_info = POSCustomerService.get_customer_balance(self.customer)
        initial_debt = balance_info['current_balance']
        self.assertGreater(initial_debt, 0)
        
        # Process additional payment
        payment_amount = Decimal('200000')
        payment_result = POSCustomerService.process_customer_payment(
            customer=self.customer,
            amount=payment_amount,
            payment_method='cash',
            reference_number='PAY-001',
            notes='Partial debt payment'
        )
        
        # Verify payment processing
        self.assertTrue(payment_result['success'])
        self.assertEqual(payment_result['payment_amount'], float(payment_amount))
        self.assertEqual(payment_result['previous_balance'], initial_debt)
        
        # Verify new balance
        new_balance_info = POSCustomerService.get_customer_balance(self.customer)
        expected_new_balance = initial_debt - float(payment_amount)
        self.assertEqual(new_balance_info['current_balance'], expected_new_balance)
        
        # Verify payment transaction was created
        payment_transaction = payment_result['payment_transaction']
        self.assertEqual(payment_transaction.transaction_type, 'payment')
        self.assertEqual(payment_transaction.amount_paid, payment_amount)
        self.assertEqual(payment_transaction.reference_number, 'PAY-001')
    
    def test_process_customer_payment_no_debt(self):
        """Test that payment processing fails when customer has no debt."""
        with self.assertRaises(ValidationError) as context:
            POSCustomerService.process_customer_payment(
                customer=self.customer,
                amount=Decimal('100000'),
                payment_method='cash'
            )
        
        self.assertIn("no outstanding debt", str(context.exception))
    
    def test_process_customer_payment_invalid_amount(self):
        """Test that payment processing fails with invalid amount."""
        with self.assertRaises(ValidationError) as context:
            POSCustomerService.process_customer_payment(
                customer=self.customer,
                amount=Decimal('0'),
                payment_method='cash'
            )
        
        self.assertIn("must be positive", str(context.exception))
    
    def test_create_customer_credit(self):
        """Test creating customer credit."""
        credit_amount = Decimal('500000')
        credit_result = POSCustomerService.create_customer_credit(
            customer=self.customer,
            amount=credit_amount,
            reason='Defective item return',
            reference_number='CREDIT-001'
        )
        
        # Verify credit creation
        self.assertTrue(credit_result['success'])
        self.assertEqual(credit_result['credit_amount'], float(credit_amount))
        self.assertEqual(credit_result['reason'], 'Defective item return')
        
        # Verify credit transaction
        credit_transaction = credit_result['credit_transaction']
        self.assertEqual(credit_transaction.transaction_type, 'credit')
        self.assertEqual(credit_transaction.total_amount, -credit_amount)  # Negative for credit
        self.assertEqual(credit_transaction.reference_number, 'CREDIT-001')
        
        # Verify balance reflects credit
        balance_info = POSCustomerService.get_customer_balance(self.customer)
        self.assertEqual(balance_info['current_balance'], -float(credit_amount))
        self.assertEqual(balance_info['balance_type'], 'credit')
    
    def test_get_customer_transaction_history(self):
        """Test retrieving customer transaction history."""
        # Create multiple transactions
        for i in range(3):
            transaction = POSTransactionService.create_transaction(
                customer_id=self.customer.id,
                transaction_type='sale',
                payment_method='cash',
                user=self.user
            )
            
            POSTransactionService.add_jewelry_item_to_transaction(
                transaction=transaction,
                jewelry_item_id=self.jewelry_item.id,
                quantity=1
            )
            
            POSTransactionService.process_payment(
                transaction=transaction,
                amount_paid=transaction.total_amount,
                payment_method='cash'
            )
        
        # Get transaction history
        history = POSCustomerService.get_customer_transaction_history(
            customer=self.customer,
            limit=5
        )
        
        # Verify history
        self.assertEqual(len(history), 3)
        
        # Verify transaction data structure
        transaction_data = history[0]
        self.assertIn('transaction_id', transaction_data)
        self.assertIn('transaction_number', transaction_data)
        self.assertIn('transaction_date', transaction_data)
        self.assertIn('transaction_date_shamsi', transaction_data)
        self.assertIn('total_amount', transaction_data)
        self.assertIn('formatted_data', transaction_data)
        
        # Verify transactions are ordered by date (newest first)
        dates = [t['transaction_date'] for t in history]
        self.assertEqual(dates, sorted(dates, reverse=True))
    
    def test_get_customer_detailed_info(self):
        """Test getting comprehensive customer information."""
        # Create some transaction history
        transaction = POSTransactionService.create_transaction(
            customer_id=self.customer.id,
            transaction_type='sale',
            payment_method='cash',
            user=self.user
        )
        
        POSTransactionService.add_jewelry_item_to_transaction(
            transaction=transaction,
            jewelry_item_id=self.jewelry_item.id,
            quantity=1
        )
        
        POSTransactionService.process_payment(
            transaction=transaction,
            amount_paid=transaction.total_amount,
            payment_method='cash'
        )
        
        # Create customer note
        CustomerNote.objects.create(
            customer=self.customer,
            note_type='preference',
            title='Prefers 18K gold',
            content='Customer always asks for 18K gold jewelry',
            is_important=True
        )
        
        # Get detailed info
        detailed_info = POSCustomerService.get_customer_detailed_info(self.customer.id)
        
        # Verify structure
        self.assertIn('customer_info', detailed_info)
        self.assertIn('balance_info', detailed_info)
        self.assertIn('loyalty_info', detailed_info)
        self.assertIn('recent_transactions', detailed_info)
        self.assertIn('recent_notes', detailed_info)
        
        # Verify customer info
        customer_info = detailed_info['customer_info']
        self.assertEqual(customer_info['id'], self.customer.id)
        self.assertEqual(customer_info['name'], 'احمد محمدی')
        self.assertEqual(customer_info['phone_number'], '09123456789')
        
        # Verify loyalty info
        loyalty_info = detailed_info['loyalty_info']
        self.assertEqual(loyalty_info['current_points'], self.customer.loyalty_points)
        self.assertEqual(loyalty_info['is_vip'], self.customer.is_vip)
        
        # Verify recent transactions
        recent_transactions = detailed_info['recent_transactions']
        self.assertEqual(len(recent_transactions), 1)
        
        # Verify recent notes
        recent_notes = detailed_info['recent_notes']
        self.assertEqual(len(recent_notes), 1)
        self.assertEqual(recent_notes[0]['title'], 'Prefers 18K gold')
    
    def test_get_customer_detailed_info_not_found(self):
        """Test getting detailed info for non-existent customer."""
        with self.assertRaises(ValidationError) as context:
            POSCustomerService.get_customer_detailed_info(99999)
        
        self.assertIn("not found", str(context.exception))