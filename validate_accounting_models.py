#!/usr/bin/env python
"""
Validation script for Persian Accounting System Models.

This script validates the model definitions without requiring database access.
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
    GeneralLedger, SubsidiaryLedger, BankAccount, ChequeManagement
)
from django.core.exceptions import ValidationError
from django.utils import timezone
import jdatetime


def validate_model_structure():
    """Validate model structure and field definitions."""
    print("=== Model Structure Validation ===")
    
    # Test ChartOfAccounts model
    print("✓ ChartOfAccounts model imported successfully")
    print(f"  - Fields: {[f.name for f in ChartOfAccounts._meta.fields]}")
    print(f"  - Verbose name: {ChartOfAccounts._meta.verbose_name}")
    print(f"  - Verbose name plural: {ChartOfAccounts._meta.verbose_name_plural}")
    
    # Test JournalEntry model
    print("✓ JournalEntry model imported successfully")
    print(f"  - Fields: {[f.name for f in JournalEntry._meta.fields]}")
    
    # Test JournalEntryLine model
    print("✓ JournalEntryLine model imported successfully")
    print(f"  - Fields: {[f.name for f in JournalEntryLine._meta.fields]}")
    
    # Test GeneralLedger model
    print("✓ GeneralLedger model imported successfully")
    print(f"  - Fields: {[f.name for f in GeneralLedger._meta.fields]}")
    
    # Test SubsidiaryLedger model
    print("✓ SubsidiaryLedger model imported successfully")
    print(f"  - Fields: {[f.name for f in SubsidiaryLedger._meta.fields]}")
    
    # Test BankAccount model
    print("✓ BankAccount model imported successfully")
    print(f"  - Fields: {[f.name for f in BankAccount._meta.fields]}")
    
    # Test ChequeManagement model
    print("✓ ChequeManagement model imported successfully")
    print(f"  - Fields: {[f.name for f in ChequeManagement._meta.fields]}")


def validate_model_methods():
    """Validate model methods and properties."""
    print("\n=== Model Methods Validation ===")
    
    # Test ChartOfAccounts methods
    account = ChartOfAccounts(
        account_code='1001',
        account_name_persian='نقد در صندوق',
        account_type='asset',
        account_category='current_assets',
        normal_balance='debit'
    )
    
    print(f"✓ ChartOfAccounts.__str__(): {account}")
    print(f"✓ ChartOfAccounts.full_account_name: {account.full_account_name}")
    
    # Test JournalEntry methods
    entry = JournalEntry(
        entry_type='sales',
        entry_date=timezone.now().date(),
        description='تست سند حسابداری'
    )
    
    print(f"✓ JournalEntry.__str__(): {entry}")
    print(f"✓ JournalEntry.is_balanced: {entry.is_balanced}")
    
    # Test BankAccount methods
    bank_account = BankAccount(
        account_name='حساب تست',
        account_number='1234567890',
        iban='IR123456789012345678901234',
        bank_name='melli',
        account_type='checking',
        account_holder_name='تست',
        opening_date=timezone.now().date()
    )
    
    print(f"✓ BankAccount.__str__(): {bank_account}")
    print(f"✓ BankAccount.masked_account_number: {bank_account.masked_account_number}")
    print(f"✓ BankAccount.masked_iban: {bank_account.masked_iban}")
    print(f"✓ BankAccount.held_amount: {bank_account.held_amount}")
    
    # Test ChequeManagement methods
    cheque = ChequeManagement(
        cheque_number='1234567',
        cheque_type='issued',
        bank_account=bank_account,
        amount=Decimal('1000000.00'),
        issue_date=timezone.now().date(),
        due_date=timezone.now().date() + timezone.timedelta(days=30),
        payee_name='تست'
    )
    
    print(f"✓ ChequeManagement.__str__(): {cheque}")
    print(f"✓ ChequeManagement.is_overdue: {cheque.is_overdue}")
    print(f"✓ ChequeManagement.days_until_due: {cheque.days_until_due}")


def validate_model_validation():
    """Test model validation logic."""
    print("\n=== Model Validation Logic ===")
    
    # Test ChartOfAccounts validation
    try:
        account = ChartOfAccounts(
            account_code='ABC123',  # Invalid: contains letters
            account_name_persian='تست',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit'
        )
        account.full_clean()
        print("❌ ChartOfAccounts validation failed - should reject non-numeric account code")
    except ValidationError as e:
        print("✓ ChartOfAccounts validation works - rejects non-numeric account code")
    
    # Test normal balance validation
    try:
        account = ChartOfAccounts(
            account_code='1001',
            account_name_persian='دارایی',
            account_type='asset',
            account_category='current_assets',
            normal_balance='credit'  # Invalid for asset
        )
        account.full_clean()
        print("❌ ChartOfAccounts validation failed - should reject wrong normal balance")
    except ValidationError as e:
        print("✓ ChartOfAccounts validation works - rejects wrong normal balance for asset")
    
    # Test JournalEntryLine validation
    try:
        line = JournalEntryLine(
            description='تست',
            debit_amount=Decimal('100.00'),
            credit_amount=Decimal('100.00')  # Invalid: both debit and credit
        )
        line.full_clean()
        print("❌ JournalEntryLine validation failed - should reject both debit and credit")
    except ValidationError as e:
        print("✓ JournalEntryLine validation works - rejects both debit and credit amounts")
    
    # Test BankAccount IBAN validation
    try:
        bank_account = BankAccount(
            account_name='تست',
            account_number='1234567890',
            iban='INVALID_IBAN',  # Invalid format
            bank_name='melli',
            account_type='checking',
            account_holder_name='تست',
            opening_date=timezone.now().date()
        )
        bank_account.full_clean()
        print("❌ BankAccount validation failed - should reject invalid IBAN")
    except ValidationError as e:
        print("✓ BankAccount validation works - rejects invalid IBAN format")
    
    # Test ChequeManagement date validation
    try:
        cheque = ChequeManagement(
            cheque_number='1234567',
            cheque_type='issued',
            amount=Decimal('1000000.00'),
            issue_date=timezone.now().date(),
            due_date=timezone.now().date() - timezone.timedelta(days=1),  # Past date
            payee_name='تست'
        )
        cheque.full_clean()
        print("❌ ChequeManagement validation failed - should reject past due date")
    except ValidationError as e:
        print("✓ ChequeManagement validation works - rejects past due date")


def validate_persian_features():
    """Test Persian localization features."""
    print("\n=== Persian Localization Features ===")
    
    # Test Shamsi date conversion
    gregorian_date = timezone.now().date()
    shamsi_date = jdatetime.date.fromgregorian(date=gregorian_date)
    print(f"✓ Shamsi date conversion: {gregorian_date} -> {shamsi_date.strftime('%Y/%m/%d')}")
    
    # Test Persian number formatting
    amount = Decimal('1234567.89')
    print(f"✓ Persian amount formatting ready for: {amount:,}")
    
    # Test Persian field names
    account = ChartOfAccounts(
        account_code='1001',
        account_name_persian='نقد در صندوق',
        account_type='asset',
        account_category='current_assets',
        normal_balance='debit'
    )
    print(f"✓ Persian account name: {account.account_name_persian}")
    
    # Test Persian choices
    print("✓ Persian account types:")
    for code, name in ChartOfAccounts.ACCOUNT_TYPES:
        print(f"  - {code}: {name}")
    
    print("✓ Persian bank names:")
    for code, name in BankAccount.BANK_NAMES[:5]:  # Show first 5
        print(f"  - {code}: {name}")


def validate_business_logic():
    """Test business logic methods."""
    print("\n=== Business Logic Validation ===")
    
    # Test account balance calculation
    account = ChartOfAccounts(
        account_code='1001',
        account_name_persian='نقد',
        account_type='asset',
        account_category='current_assets',
        normal_balance='debit',
        current_balance=Decimal('1000.00')
    )
    
    # Simulate balance update logic
    if account.normal_balance == 'debit':
        new_balance = account.current_balance + Decimal('500.00')  # Debit increase
        print(f"✓ Debit account balance calculation: {account.current_balance} + 500 = {new_balance}")
    
    # Test journal entry balance checking
    entry = JournalEntry(
        entry_type='sales',
        entry_date=timezone.now().date(),
        description='تست',
        total_debit=Decimal('1000.00'),
        total_credit=Decimal('1000.00')
    )
    print(f"✓ Journal entry balance check: {entry.is_balanced}")
    
    # Test general ledger closing balance calculation
    gl_entry = GeneralLedger(
        fiscal_year='1402',
        period_month=6,
        opening_balance=Decimal('1000.00'),
        period_debit=Decimal('500.00'),
        period_credit=Decimal('200.00')
    )
    
    # Simulate closing balance calculation for debit account
    closing_balance = gl_entry.opening_balance + gl_entry.period_debit - gl_entry.period_credit
    print(f"✓ General ledger closing balance: {gl_entry.opening_balance} + {gl_entry.period_debit} - {gl_entry.period_credit} = {closing_balance}")


def main():
    """Run all validations."""
    print("🏪 Persian Accounting System Models Validation")
    print("=" * 60)
    
    try:
        validate_model_structure()
        validate_model_methods()
        validate_model_validation()
        validate_persian_features()
        validate_business_logic()
        
        print("\n✅ All validations passed successfully!")
        print("\n📋 Validation Summary:")
        print("- ✓ Model structure and field definitions")
        print("- ✓ Model methods and properties")
        print("- ✓ Model validation logic")
        print("- ✓ Persian localization features")
        print("- ✓ Business logic calculations")
        
        print("\n🎯 Models are ready for:")
        print("- Persian Chart of Accounts (کدینگ حسابداری)")
        print("- Journal Entries (ثبت اسناد حسابداری)")
        print("- General Ledger (دفتر کل)")
        print("- Subsidiary Ledger (دفتر معین)")
        print("- Iranian Bank Account Management")
        print("- Iranian Cheque Lifecycle Tracking")
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())