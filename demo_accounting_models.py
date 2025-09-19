#!/usr/bin/env python
"""
Demo script to test Persian Accounting System Models.

This script demonstrates the functionality of the accounting models
and verifies they work correctly with Persian localization.
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from zargar.accounting.models import (
    ChartOfAccounts, JournalEntry, JournalEntryLine,
    GeneralLedger, BankAccount, ChequeManagement
)
from django.utils import timezone
import jdatetime


def demo_chart_of_accounts():
    """Demonstrate Chart of Accounts functionality."""
    print("=== Chart of Accounts Demo ===")
    
    # Create parent account
    parent_account = ChartOfAccounts.objects.create(
        account_code='1000',
        account_name_persian='دارایی‌های جاری',
        account_name_english='Current Assets',
        account_type='asset',
        account_category='current_assets',
        normal_balance='debit',
        allow_posting=False,
        description='Parent account for current assets'
    )
    print(f"Created parent account: {parent_account}")
    
    # Create child account
    cash_account = ChartOfAccounts.objects.create(
        account_code='1001',
        account_name_persian='نقد در صندوق',
        account_name_english='Cash in Hand',
        account_type='asset',
        account_category='current_assets',
        normal_balance='debit',
        parent_account=parent_account,
        description='Cash account for daily operations'
    )
    print(f"Created cash account: {cash_account}")
    print(f"Account path: {cash_account.account_path}")
    print(f"Account level: {cash_account.account_level}")
    
    # Create revenue account
    sales_account = ChartOfAccounts.objects.create(
        account_code='4001',
        account_name_persian='درآمد فروش طلا',
        account_name_english='Gold Sales Revenue',
        account_type='revenue',
        account_category='sales_revenue',
        normal_balance='credit',
        description='Revenue from gold jewelry sales'
    )
    print(f"Created sales account: {sales_account}")
    
    return cash_account, sales_account


def demo_journal_entries(cash_account, sales_account):
    """Demonstrate Journal Entry functionality."""
    print("\n=== Journal Entry Demo ===")
    
    # Create journal entry
    entry = JournalEntry.objects.create(
        entry_type='sales',
        entry_date=timezone.now().date(),
        description='فروش طلا به مشتری - نقدی',
        reference_number='INV-001'
    )
    print(f"Created journal entry: {entry}")
    print(f"Entry number: {entry.entry_number}")
    print(f"Shamsi date: {entry.entry_date_shamsi}")
    
    # Create journal entry lines
    debit_line = JournalEntryLine.objects.create(
        journal_entry=entry,
        account=cash_account,
        description='دریافت نقد از فروش طلا',
        debit_amount=Decimal('5000000.00')  # 5 million Toman
    )
    print(f"Created debit line: {debit_line}")
    
    credit_line = JournalEntryLine.objects.create(
        journal_entry=entry,
        account=sales_account,
        description='درآمد فروش طلا',
        credit_amount=Decimal('5000000.00')
    )
    print(f"Created credit line: {credit_line}")
    
    # Check if entry is balanced
    entry.refresh_from_db()
    print(f"Entry is balanced: {entry.is_balanced}")
    print(f"Total debit: {entry.total_debit:,} تومان")
    print(f"Total credit: {entry.total_credit:,} تومان")
    print(f"Can be posted: {entry.can_be_posted}")
    
    return entry


def demo_bank_account():
    """Demonstrate Bank Account functionality."""
    print("\n=== Bank Account Demo ===")
    
    # Create chart account for bank
    bank_chart_account = ChartOfAccounts.objects.create(
        account_code='1101',
        account_name_persian='حساب بانک ملی',
        account_name_english='Bank Melli Account',
        account_type='asset',
        account_category='current_assets',
        normal_balance='debit'
    )
    
    # Create bank account
    bank_account = BankAccount.objects.create(
        account_name='حساب جاری اصلی',
        account_number='1234567890',
        iban='IR123456789012345678901234',
        bank_name='melli',
        bank_branch='شعبه مرکزی تهران',
        account_type='checking',
        account_holder_name='شرکت زرگری طلایی',
        account_holder_national_id='1234567890',
        opening_date=timezone.now().date(),
        chart_account=bank_chart_account,
        is_default=True
    )
    print(f"Created bank account: {bank_account}")
    print(f"IBAN: {bank_account.iban}")
    print(f"Masked account number: {bank_account.masked_account_number}")
    print(f"Masked IBAN: {bank_account.masked_iban}")
    
    # Test balance operations
    bank_account.update_balance(Decimal('10000000.00'), 'deposit')
    print(f"After deposit - Current balance: {bank_account.current_balance:,} تومان")
    
    bank_account.update_balance(Decimal('2000000.00'), 'withdrawal')
    print(f"After withdrawal - Current balance: {bank_account.current_balance:,} تومان")
    
    bank_account.update_balance(Decimal('500000.00'), 'hold')
    print(f"After hold - Available balance: {bank_account.available_balance:,} تومان")
    print(f"Held amount: {bank_account.held_amount:,} تومان")
    
    return bank_account


def demo_cheque_management(bank_account):
    """Demonstrate Cheque Management functionality."""
    print("\n=== Cheque Management Demo ===")
    
    # Create issued cheque
    issued_cheque = ChequeManagement.objects.create(
        cheque_number='1234567',
        cheque_type='issued',
        bank_account=bank_account,
        amount=Decimal('3000000.00'),
        issue_date=timezone.now().date(),
        due_date=timezone.now().date() + timezone.timedelta(days=30),
        payee_name='تامین‌کننده طلا',
        description='پرداخت بابت خرید طلا'
    )
    print(f"Created issued cheque: {issued_cheque}")
    print(f"Shamsi issue date: {issued_cheque.issue_date_shamsi}")
    print(f"Shamsi due date: {issued_cheque.due_date_shamsi}")
    print(f"Days until due: {issued_cheque.days_until_due}")
    
    # Create received cheque
    received_cheque = ChequeManagement.objects.create(
        cheque_number='7654321',
        cheque_type='received',
        bank_account=bank_account,
        amount=Decimal('2500000.00'),
        issue_date=timezone.now().date(),
        due_date=timezone.now().date() + timezone.timedelta(days=15),
        payee_name='شرکت زرگری طلایی',
        payer_name='مشتری طلا',
        description='دریافت بابت فروش طلا'
    )
    print(f"Created received cheque: {received_cheque}")
    
    # Test cheque lifecycle
    print("\n--- Cheque Lifecycle ---")
    print(f"Initial status: {received_cheque.get_status_display()}")
    
    received_cheque.present_cheque()
    print(f"After presentation: {received_cheque.get_status_display()}")
    
    initial_balance = bank_account.current_balance
    received_cheque.clear_cheque()
    print(f"After clearance: {received_cheque.get_status_display()}")
    
    bank_account.refresh_from_db()
    print(f"Bank balance before: {initial_balance:,} تومان")
    print(f"Bank balance after: {bank_account.current_balance:,} تومان")
    print(f"Balance increase: {bank_account.current_balance - initial_balance:,} تومان")
    
    return issued_cheque, received_cheque


def demo_general_ledger(cash_account):
    """Demonstrate General Ledger functionality."""
    print("\n=== General Ledger Demo ===")
    
    # Create general ledger entry
    gl_entry = GeneralLedger.objects.create(
        account=cash_account,
        fiscal_year='1402',
        period_month=6,  # Shahrivar
        opening_balance=Decimal('1000000.00'),
        period_debit=Decimal('5000000.00'),
        period_credit=Decimal('2000000.00')
    )
    print(f"Created general ledger entry: {gl_entry}")
    
    # Calculate closing balance
    closing_balance = gl_entry.calculate_closing_balance()
    print(f"Opening balance: {gl_entry.opening_balance:,} تومان")
    print(f"Period debit: {gl_entry.period_debit:,} تومان")
    print(f"Period credit: {gl_entry.period_credit:,} تومان")
    print(f"Closing balance: {closing_balance:,} تومان")
    
    return gl_entry


def main():
    """Run all demos."""
    print("🏪 Persian Accounting System Models Demo")
    print("=" * 50)
    
    try:
        # Demo Chart of Accounts
        cash_account, sales_account = demo_chart_of_accounts()
        
        # Demo Journal Entries
        journal_entry = demo_journal_entries(cash_account, sales_account)
        
        # Demo Bank Account
        bank_account = demo_bank_account()
        
        # Demo Cheque Management
        issued_cheque, received_cheque = demo_cheque_management(bank_account)
        
        # Demo General Ledger
        gl_entry = demo_general_ledger(cash_account)
        
        print("\n✅ All demos completed successfully!")
        print("\n📊 Summary:")
        print(f"- Created {ChartOfAccounts.objects.count()} chart of accounts")
        print(f"- Created {JournalEntry.objects.count()} journal entries")
        print(f"- Created {JournalEntryLine.objects.count()} journal entry lines")
        print(f"- Created {BankAccount.objects.count()} bank accounts")
        print(f"- Created {ChequeManagement.objects.count()} cheques")
        print(f"- Created {GeneralLedger.objects.count()} general ledger entries")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())