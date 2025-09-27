"""
Unit tests for Persian Accounting System Models.

Tests cover all accounting models with comprehensive validation,
business logic, and Persian localization features.
"""

import pytest
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import IntegrityError
import jdatetime

from zargar.accounting.models import (
    ChartOfAccounts, JournalEntry, JournalEntryLine,
    GeneralLedger, SubsidiaryLedger, BankAccount, ChequeManagement
)
from zargar.core.models import User


class ChartOfAccountsModelTest(TestCase):
    """Test ChartOfAccounts model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role='accountant'
        )
    
    def test_create_chart_of_accounts(self):
        """Test creating a chart of accounts entry."""
        account = ChartOfAccounts.objects.create(
            account_code='1001',
            account_name_persian='نقد در صندوق',
            account_name_english='Cash in Hand',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit',
            description='Cash account for daily operations'
        )
        
        self.assertEqual(account.account_code, '1001')
        self.assertEqual(account.account_name_persian, 'نقد در صندوق')
        self.assertEqual(account.account_type, 'asset')
        self.assertEqual(account.normal_balance, 'debit')
        self.assertTrue(account.is_active)
        self.assertTrue(account.allow_posting)
        self.assertEqual(account.account_level, 1)
        self.assertEqual(account.current_balance, Decimal('0.00'))
    
    def test_hierarchical_accounts(self):
        """Test hierarchical account structure."""
        # Create parent account
        parent = ChartOfAccounts.objects.create(
            account_code='1000',
            account_name_persian='دارایی‌های جاری',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit',
            allow_posting=False  # Parent accounts typically don't allow posting
        )
        
        # Create child account
        child = ChartOfAccounts.objects.create(
            account_code='1001',
            account_name_persian='نقد در صندوق',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit',
            parent_account=parent
        )
        
        self.assertEqual(child.parent_account, parent)
        self.assertEqual(child.account_level, 2)
        self.assertIn(child, parent.get_children())
        self.assertEqual(child.account_path, 'دارایی‌های جاری > نقد در صندوق')
    
    def test_account_code_validation(self):
        """Test account code validation."""
        with self.assertRaises(ValidationError):
            account = ChartOfAccounts(
                account_code='ABC123',  # Invalid: contains letters
                account_name_persian='تست',
                account_type='asset',
                account_category='current_assets',
                normal_balance='debit'
            )
            account.full_clean()
    
    def test_circular_reference_validation(self):
        """Test prevention of circular references in hierarchy."""
        parent = ChartOfAccounts.objects.create(
            account_code='1000',
            account_name_persian='والد',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit'
        )
        
        child = ChartOfAccounts.objects.create(
            account_code='1001',
            account_name_persian='فرزند',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit',
            parent_account=parent
        )
        
        # Try to create circular reference
        with self.assertRaises(ValidationError):
            parent.parent_account = child
            parent.full_clean()
    
    def test_normal_balance_validation(self):
        """Test normal balance validation based on account type."""
        # Asset account should have debit normal balance
        with self.assertRaises(ValidationError):
            account = ChartOfAccounts(
                account_code='1001',
                account_name_persian='دارایی',
                account_type='asset',
                account_category='current_assets',
                normal_balance='credit'  # Invalid for asset
            )
            account.full_clean()
        
        # Revenue account should have credit normal balance
        with self.assertRaises(ValidationError):
            account = ChartOfAccounts(
                account_code='4001',
                account_name_persian='درآمد',
                account_type='revenue',
                account_category='sales_revenue',
                normal_balance='debit'  # Invalid for revenue
            )
            account.full_clean()
    
    def test_update_balance(self):
        """Test account balance updates."""
        account = ChartOfAccounts.objects.create(
            account_code='1001',
            account_name_persian='نقد',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit'
        )
        
        # Test debit increase for debit normal balance
        account.update_balance(Decimal('1000.00'), is_debit=True)
        account.refresh_from_db()
        self.assertEqual(account.current_balance, Decimal('1000.00'))
        
        # Test credit decrease for debit normal balance
        account.update_balance(Decimal('300.00'), is_debit=False)
        account.refresh_from_db()
        self.assertEqual(account.current_balance, Decimal('700.00'))
    
    def test_string_representation(self):
        """Test string representation of account."""
        account = ChartOfAccounts.objects.create(
            account_code='1001',
            account_name_persian='نقد در صندوق',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit'
        )
        
        expected = '1001 - نقد در صندوق'
        self.assertEqual(str(account), expected)
        self.assertEqual(account.full_account_name, expected)


class JournalEntryModelTest(TestCase):
    """Test JournalEntry and JournalEntryLine models."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role='accountant'
        )
        
        # Create test accounts
        self.cash_account = ChartOfAccounts.objects.create(
            account_code='1001',
            account_name_persian='نقد در صندوق',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit'
        )
        
        self.sales_account = ChartOfAccounts.objects.create(
            account_code='4001',
            account_name_persian='درآمد فروش',
            account_type='revenue',
            account_category='sales_revenue',
            normal_balance='credit'
        )
    
    def test_create_journal_entry(self):
        """Test creating a journal entry."""
        entry = JournalEntry.objects.create(
            entry_type='sales',
            entry_date=timezone.now().date(),
            description='فروش طلا به مشتری',
            reference_number='INV-001'
        )
        
        self.assertTrue(entry.entry_number.startswith('JE-'))
        self.assertEqual(entry.entry_type, 'sales')
        self.assertEqual(entry.status, 'draft')
        self.assertEqual(entry.total_debit, Decimal('0.00'))
        self.assertEqual(entry.total_credit, Decimal('0.00'))
        self.assertIsNotNone(entry.entry_date_shamsi)
    
    def test_journal_entry_lines(self):
        """Test creating journal entry lines."""
        entry = JournalEntry.objects.create(
            entry_type='sales',
            entry_date=timezone.now().date(),
            description='فروش طلا'
        )
        
        # Create debit line
        debit_line = JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.cash_account,
            description='دریافت نقد از فروش',
            debit_amount=Decimal('1000000.00')
        )
        
        # Create credit line
        credit_line = JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.sales_account,
            description='درآمد فروش طلا',
            credit_amount=Decimal('1000000.00')
        )
        
        # Check line numbers are auto-assigned
        self.assertEqual(debit_line.line_number, 1)
        self.assertEqual(credit_line.line_number, 2)
        
        # Check entry totals are updated
        entry.refresh_from_db()
        self.assertEqual(entry.total_debit, Decimal('1000000.00'))
        self.assertEqual(entry.total_credit, Decimal('1000000.00'))
        self.assertTrue(entry.is_balanced)
    
    def test_journal_entry_line_validation(self):
        """Test journal entry line validation."""
        entry = JournalEntry.objects.create(
            entry_type='general',
            entry_date=timezone.now().date(),
            description='تست'
        )
        
        # Test: cannot have both debit and credit
        with self.assertRaises(ValidationError):
            line = JournalEntryLine(
                journal_entry=entry,
                account=self.cash_account,
                description='تست',
                debit_amount=Decimal('100.00'),
                credit_amount=Decimal('100.00')
            )
            line.full_clean()
        
        # Test: must have either debit or credit
        with self.assertRaises(ValidationError):
            line = JournalEntryLine(
                journal_entry=entry,
                account=self.cash_account,
                description='تست',
                debit_amount=Decimal('0.00'),
                credit_amount=Decimal('0.00')
            )
            line.full_clean()
    
    def test_journal_entry_posting(self):
        """Test posting journal entries."""
        entry = JournalEntry.objects.create(
            entry_type='sales',
            entry_date=timezone.now().date(),
            description='فروش طلا'
        )
        
        # Add balanced lines
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.cash_account,
            description='دریافت نقد',
            debit_amount=Decimal('500000.00')
        )
        
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.sales_account,
            description='درآمد فروش',
            credit_amount=Decimal('500000.00')
        )
        
        # Test posting
        self.assertTrue(entry.can_be_posted)
        entry.post(user=self.user)
        
        self.assertEqual(entry.status, 'posted')
        self.assertIsNotNone(entry.posted_at)
        self.assertEqual(entry.posted_by, self.user)
        
        # Check account balances updated
        self.cash_account.refresh_from_db()
        self.sales_account.refresh_from_db()
        self.assertEqual(self.cash_account.current_balance, Decimal('500000.00'))
        self.assertEqual(self.sales_account.current_balance, Decimal('500000.00'))
    
    def test_unbalanced_entry_cannot_be_posted(self):
        """Test that unbalanced entries cannot be posted."""
        entry = JournalEntry.objects.create(
            entry_type='general',
            entry_date=timezone.now().date(),
            description='تست نامتعادل'
        )
        
        # Add unbalanced lines
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.cash_account,
            description='بدهکار',
            debit_amount=Decimal('1000.00')
        )
        
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.sales_account,
            description='بستانکار',
            credit_amount=Decimal('800.00')  # Unbalanced
        )
        
        self.assertFalse(entry.can_be_posted)
        
        with self.assertRaises(ValidationError):
            entry.post()
    
    def test_shamsi_date_conversion(self):
        """Test automatic Shamsi date conversion."""
        gregorian_date = timezone.now().date()
        entry = JournalEntry.objects.create(
            entry_type='general',
            entry_date=gregorian_date,
            description='تست تاریخ شمسی'
        )
        
        # Check Shamsi date is automatically set
        self.assertIsNotNone(entry.entry_date_shamsi)
        
        # Verify conversion is correct
        expected_shamsi = jdatetime.date.fromgregorian(date=gregorian_date)
        self.assertEqual(entry.entry_date_shamsi, expected_shamsi.strftime('%Y/%m/%d'))


class GeneralLedgerModelTest(TestCase):
    """Test GeneralLedger model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role='accountant'
        )
        
        self.account = ChartOfAccounts.objects.create(
            account_code='1001',
            account_name_persian='نقد',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit'
        )
    
    def test_create_general_ledger_entry(self):
        """Test creating general ledger entry."""
        gl_entry = GeneralLedger.objects.create(
            account=self.account,
            fiscal_year='1402',
            period_month=1,
            opening_balance=Decimal('100000.00'),
            period_debit=Decimal('50000.00'),
            period_credit=Decimal('20000.00')
        )
        
        self.assertEqual(gl_entry.account, self.account)
        self.assertEqual(gl_entry.fiscal_year, '1402')
        self.assertEqual(gl_entry.period_month, 1)
        self.assertFalse(gl_entry.is_closed)
        
        # Test closing balance calculation
        expected_closing = Decimal('100000.00') + Decimal('50000.00') - Decimal('20000.00')
        self.assertEqual(gl_entry.calculate_closing_balance(), expected_closing)
    
    def test_unique_constraint(self):
        """Test unique constraint on account, fiscal year, and period."""
        GeneralLedger.objects.create(
            account=self.account,
            fiscal_year='1402',
            period_month=1
        )
        
        # Try to create duplicate
        with self.assertRaises(IntegrityError):
            GeneralLedger.objects.create(
                account=self.account,
                fiscal_year='1402',
                period_month=1
            )
    
    def test_period_closing(self):
        """Test period closing functionality."""
        gl_entry = GeneralLedger.objects.create(
            account=self.account,
            fiscal_year='1402',
            period_month=1
        )
        
        # Close period
        gl_entry.close_period(user=self.user)
        
        self.assertTrue(gl_entry.is_closed)
        self.assertIsNotNone(gl_entry.closed_at)
        self.assertEqual(gl_entry.closed_by, self.user)
        
        # Test reopening
        gl_entry.reopen_period()
        
        self.assertFalse(gl_entry.is_closed)
        self.assertIsNone(gl_entry.closed_at)
        self.assertIsNone(gl_entry.closed_by)


class BankAccountModelTest(TestCase):
    """Test BankAccount model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role='owner'
        )
        
        self.chart_account = ChartOfAccounts.objects.create(
            account_code='1101',
            account_name_persian='حساب بانک ملی',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit'
        )
    
    def test_create_bank_account(self):
        """Test creating a bank account."""
        bank_account = BankAccount.objects.create(
            account_name='حساب جاری اصلی',
            account_number='1234567890',
            iban='IR123456789012345678901234',
            bank_name='melli',
            bank_branch='شعبه مرکزی',
            account_type='checking',
            account_holder_name='شرکت زرگری طلایی',
            opening_date=timezone.now().date(),
            chart_account=self.chart_account
        )
        
        self.assertEqual(bank_account.account_name, 'حساب جاری اصلی')
        self.assertEqual(bank_account.bank_name, 'melli')
        self.assertEqual(bank_account.current_balance, Decimal('0.00'))
        self.assertEqual(bank_account.available_balance, Decimal('0.00'))
        self.assertTrue(bank_account.is_active)
    
    def test_iban_validation(self):
        """Test IBAN validation."""
        # Valid IBAN
        bank_account = BankAccount(
            account_name='تست',
            account_number='1234567890',
            iban='IR123456789012345678901234',
            bank_name='melli',
            account_type='checking',
            account_holder_name='تست',
            opening_date=timezone.now().date()
        )
        bank_account.full_clean()  # Should not raise
        
        # Invalid IBAN - wrong format
        with self.assertRaises(ValidationError):
            bank_account = BankAccount(
                account_name='تست',
                account_number='1234567890',
                iban='INVALID_IBAN',
                bank_name='melli',
                account_type='checking',
                account_holder_name='تست',
                opening_date=timezone.now().date()
            )
            bank_account.full_clean()
    
    def test_national_id_validation(self):
        """Test national ID validation."""
        # Valid national ID
        bank_account = BankAccount(
            account_name='تست',
            account_number='1234567890',
            bank_name='melli',
            account_type='checking',
            account_holder_name='تست',
            account_holder_national_id='1234567890',
            opening_date=timezone.now().date()
        )
        bank_account.full_clean()  # Should not raise
        
        # Invalid national ID - wrong length
        with self.assertRaises(ValidationError):
            bank_account = BankAccount(
                account_name='تست',
                account_number='1234567890',
                bank_name='melli',
                account_type='checking',
                account_holder_name='تست',
                account_holder_national_id='123456789',  # Only 9 digits
                opening_date=timezone.now().date()
            )
            bank_account.full_clean()
    
    def test_default_account_logic(self):
        """Test default account logic."""
        # Create first account as default
        account1 = BankAccount.objects.create(
            account_name='حساب اول',
            account_number='1111111111',
            bank_name='melli',
            account_type='checking',
            account_holder_name='تست',
            opening_date=timezone.now().date(),
            is_default=True
        )
        
        # Create second account as default
        account2 = BankAccount.objects.create(
            account_name='حساب دوم',
            account_number='2222222222',
            bank_name='mellat',
            account_type='checking',
            account_holder_name='تست',
            opening_date=timezone.now().date(),
            is_default=True
        )
        
        # First account should no longer be default
        account1.refresh_from_db()
        self.assertFalse(account1.is_default)
        self.assertTrue(account2.is_default)
    
    def test_balance_updates(self):
        """Test balance update functionality."""
        bank_account = BankAccount.objects.create(
            account_name='تست',
            account_number='1234567890',
            bank_name='melli',
            account_type='checking',
            account_holder_name='تست',
            opening_date=timezone.now().date()
        )
        
        # Test deposit
        bank_account.update_balance(Decimal('1000000.00'), 'deposit')
        self.assertEqual(bank_account.current_balance, Decimal('1000000.00'))
        self.assertEqual(bank_account.available_balance, Decimal('1000000.00'))
        
        # Test withdrawal
        bank_account.update_balance(Decimal('300000.00'), 'withdrawal')
        self.assertEqual(bank_account.current_balance, Decimal('700000.00'))
        self.assertEqual(bank_account.available_balance, Decimal('700000.00'))
        
        # Test hold
        bank_account.update_balance(Decimal('100000.00'), 'hold')
        self.assertEqual(bank_account.current_balance, Decimal('700000.00'))
        self.assertEqual(bank_account.available_balance, Decimal('600000.00'))
        self.assertEqual(bank_account.held_amount, Decimal('100000.00'))
    
    def test_masked_numbers(self):
        """Test masked account number and IBAN."""
        bank_account = BankAccount.objects.create(
            account_name='تست',
            account_number='1234567890',
            iban='IR123456789012345678901234',
            bank_name='melli',
            account_type='checking',
            account_holder_name='تست',
            opening_date=timezone.now().date()
        )
        
        self.assertEqual(bank_account.masked_account_number, '****7890')
        self.assertEqual(bank_account.masked_iban, 'IR12****1234')


class ChequeManagementModelTest(TestCase):
    """Test ChequeManagement model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role='accountant'
        )
        
        self.chart_account = ChartOfAccounts.objects.create(
            account_code='1101',
            account_name_persian='حساب بانک',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit'
        )
        
        self.bank_account = BankAccount.objects.create(
            account_name='حساب اصلی',
            account_number='1234567890',
            bank_name='melli',
            account_type='checking',
            account_holder_name='شرکت زرگری',
            opening_date=timezone.now().date(),
            chart_account=self.chart_account
        )
    
    def test_create_issued_cheque(self):
        """Test creating an issued cheque."""
        cheque = ChequeManagement.objects.create(
            cheque_number='1234567',
            cheque_type='issued',
            bank_account=self.bank_account,
            amount=Decimal('5000000.00'),
            issue_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            payee_name='تامین‌کننده طلا'
        )
        
        self.assertEqual(cheque.cheque_type, 'issued')
        self.assertEqual(cheque.status, 'pending')
        self.assertEqual(cheque.amount, Decimal('5000000.00'))
        self.assertIsNotNone(cheque.issue_date_shamsi)
        self.assertIsNotNone(cheque.due_date_shamsi)
    
    def test_create_received_cheque(self):
        """Test creating a received cheque."""
        cheque = ChequeManagement.objects.create(
            cheque_number='7654321',
            cheque_type='received',
            bank_account=self.bank_account,
            amount=Decimal('3000000.00'),
            issue_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=15),
            payee_name='شرکت زرگری',
            payer_name='مشتری طلا'
        )
        
        self.assertEqual(cheque.cheque_type, 'received')
        self.assertEqual(cheque.payer_name, 'مشتری طلا')
    
    def test_cheque_validation(self):
        """Test cheque validation."""
        # Test due date validation
        with self.assertRaises(ValidationError):
            cheque = ChequeManagement(
                cheque_number='1234567',
                cheque_type='issued',
                bank_account=self.bank_account,
                amount=Decimal('1000000.00'),
                issue_date=timezone.now().date(),
                due_date=timezone.now().date() - timezone.timedelta(days=1),  # Past date
                payee_name='تست'
            )
            cheque.full_clean()
        
        # Test negative amount validation
        with self.assertRaises(ValidationError):
            cheque = ChequeManagement(
                cheque_number='1234567',
                cheque_type='issued',
                bank_account=self.bank_account,
                amount=Decimal('-1000.00'),  # Negative amount
                issue_date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                payee_name='تست'
            )
            cheque.full_clean()
    
    def test_cheque_lifecycle(self):
        """Test complete cheque lifecycle."""
        cheque = ChequeManagement.objects.create(
            cheque_number='1234567',
            cheque_type='received',
            bank_account=self.bank_account,
            amount=Decimal('2000000.00'),
            issue_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            payee_name='شرکت زرگری',
            payer_name='مشتری'
        )
        
        # Present cheque
        cheque.present_cheque()
        self.assertEqual(cheque.status, 'presented')
        self.assertIsNotNone(cheque.presentation_date)
        
        # Clear cheque
        initial_balance = self.bank_account.current_balance
        cheque.clear_cheque()
        
        self.assertEqual(cheque.status, 'cleared')
        self.assertIsNotNone(cheque.clearance_date)
        
        # Check bank account balance updated
        self.bank_account.refresh_from_db()
        expected_balance = initial_balance + cheque.amount
        self.assertEqual(self.bank_account.current_balance, expected_balance)
    
    def test_cheque_bounce(self):
        """Test cheque bounce functionality."""
        cheque = ChequeManagement.objects.create(
            cheque_number='1234567',
            cheque_type='received',
            bank_account=self.bank_account,
            amount=Decimal('1000000.00'),
            issue_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            payee_name='شرکت زرگری',
            payer_name='مشتری'
        )
        
        # Present and then bounce
        cheque.present_cheque()
        cheque.bounce_cheque('insufficient_funds', notes='عدم کفایت موجودی')
        
        self.assertEqual(cheque.status, 'bounced')
        self.assertEqual(cheque.bounce_reason, 'insufficient_funds')
        self.assertIsNotNone(cheque.bounce_date)
        self.assertIn('عدم کفایت موجودی', cheque.notes)
    
    def test_overdue_cheque(self):
        """Test overdue cheque detection."""
        # Create overdue cheque
        past_date = timezone.now().date() - timezone.timedelta(days=5)
        cheque = ChequeManagement.objects.create(
            cheque_number='1234567',
            cheque_type='received',
            bank_account=self.bank_account,
            amount=Decimal('1000000.00'),
            issue_date=past_date - timezone.timedelta(days=30),
            due_date=past_date,
            payee_name='شرکت زرگری',
            payer_name='مشتری'
        )
        
        self.assertTrue(cheque.is_overdue)
        self.assertEqual(cheque.days_until_due, -5)
    
    def test_formatted_amount(self):
        """Test Persian formatted amount."""
        cheque = ChequeManagement.objects.create(
            cheque_number='1234567',
            cheque_type='issued',
            bank_account=self.bank_account,
            amount=Decimal('1234567.89'),
            issue_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            payee_name='تست'
        )
        
        # Test that formatted amount method exists and returns string
        formatted = cheque.formatted_amount
        self.assertIsInstance(formatted, str)
    
    def test_string_representation(self):
        """Test string representation of cheque."""
        cheque = ChequeManagement.objects.create(
            cheque_number='1234567',
            cheque_type='issued',
            bank_account=self.bank_account,
            amount=Decimal('1000000.00'),
            issue_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            payee_name='تست'
        )
        
        expected = 'چک صادره (Issued Cheque) - 1234567 - 1,000,000 ریال'
        self.assertIn('1234567', str(cheque))
        self.assertIn('1,000,000', str(cheque))


class AccountingModelsIntegrationTest(TestCase):
    """Integration tests for accounting models working together."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role='accountant'
        )
        
        # Create chart of accounts
        self.cash_account = ChartOfAccounts.objects.create(
            account_code='1001',
            account_name_persian='نقد در صندوق',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit'
        )
        
        self.bank_account_chart = ChartOfAccounts.objects.create(
            account_code='1101',
            account_name_persian='حساب بانک',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit'
        )
        
        self.sales_account = ChartOfAccounts.objects.create(
            account_code='4001',
            account_name_persian='درآمد فروش',
            account_type='revenue',
            account_category='sales_revenue',
            normal_balance='credit'
        )
        
        # Create bank account
        self.bank_account = BankAccount.objects.create(
            account_name='حساب اصلی',
            account_number='1234567890',
            bank_name='melli',
            account_type='checking',
            account_holder_name='شرکت زرگری',
            opening_date=timezone.now().date(),
            chart_account=self.bank_account_chart
        )
    
    def test_complete_sales_transaction(self):
        """Test complete sales transaction with journal entry and subsidiary ledger."""
        # Create sales journal entry
        entry = JournalEntry.objects.create(
            entry_type='sales',
            entry_date=timezone.now().date(),
            description='فروش طلا به مشتری',
            reference_number='INV-001'
        )
        
        # Add journal entry lines
        cash_line = JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.cash_account,
            description='دریافت نقد از فروش طلا',
            debit_amount=Decimal('5000000.00')
        )
        
        sales_line = JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.sales_account,
            description='درآمد فروش طلا',
            credit_amount=Decimal('5000000.00')
        )
        
        # Post the entry
        entry.post(user=self.user)
        
        # Verify account balances
        self.cash_account.refresh_from_db()
        self.sales_account.refresh_from_db()
        
        self.assertEqual(self.cash_account.current_balance, Decimal('5000000.00'))
        self.assertEqual(self.sales_account.current_balance, Decimal('5000000.00'))
        
        # Verify subsidiary ledger entries are created
        cash_subsidiary = SubsidiaryLedger.objects.filter(account=self.cash_account).first()
        sales_subsidiary = SubsidiaryLedger.objects.filter(account=self.sales_account).first()
        
        self.assertIsNotNone(cash_subsidiary)
        self.assertIsNotNone(sales_subsidiary)
        self.assertEqual(cash_subsidiary.debit_amount, Decimal('5000000.00'))
        self.assertEqual(sales_subsidiary.credit_amount, Decimal('5000000.00'))
    
    def test_cheque_to_journal_entry_integration(self):
        """Test integration between cheque management and journal entries."""
        # Create a received cheque
        cheque = ChequeManagement.objects.create(
            cheque_number='1234567',
            cheque_type='received',
            bank_account=self.bank_account,
            amount=Decimal('3000000.00'),
            issue_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            payee_name='شرکت زرگری',
            payer_name='مشتری طلا'
        )
        
        # Present and clear the cheque
        cheque.present_cheque()
        cheque.clear_cheque()
        
        # Verify journal entry was created
        self.assertIsNotNone(cheque.journal_entry)
        self.assertEqual(cheque.journal_entry.status, 'posted')
        
        # Verify bank account balance updated
        self.bank_account.refresh_from_db()
        self.assertEqual(self.bank_account.current_balance, Decimal('3000000.00'))
        
        # Verify chart account balance updated
        self.bank_account_chart.refresh_from_db()
        self.assertEqual(self.bank_account_chart.current_balance, Decimal('3000000.00'))


if __name__ == '__main__':
    pytest.main([__file__])