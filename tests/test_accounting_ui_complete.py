"""
Complete tests for Persian Accounting System UI components.

This test suite verifies that all accounting UI components work correctly
with Persian localization, RTL layout, and dual theme support.
"""

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import jdatetime

from zargar.accounting.models import (
    ChartOfAccounts, JournalEntry, JournalEntryLine, 
    BankAccount, ChequeManagement
)
from zargar.accounting.forms import (
    ChartOfAccountsForm, JournalEntryForm, BankAccountForm, ChequeManagementForm
)

User = get_user_model()


class AccountingUITestCase(TestCase):
    """Base test case for accounting UI tests."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
        
        # Login user
        self.client.login(username='testuser', password='testpass123')
        
        # Create test chart of accounts
        self.asset_account = ChartOfAccounts.objects.create(
            account_code='1101',
            account_name_persian='صندوق',
            account_name_english='Cash',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit',
            current_balance=Decimal('1000000.00')
        )
        
        self.revenue_account = ChartOfAccounts.objects.create(
            account_code='4101',
            account_name_persian='درآمد فروش',
            account_name_english='Sales Revenue',
            account_type='revenue',
            account_category='sales_revenue',
            normal_balance='credit',
            current_balance=Decimal('500000.00')
        )
        
        # Create test bank account
        self.bank_account = BankAccount.objects.create(
            account_name='حساب جاری بانک ملی',
            account_number='1234567890',
            iban='IR123456789012345678901234',
            bank_name='melli',
            bank_branch='شعبه مرکزی',
            bank_branch_code='001',
            account_type='checking',
            currency='IRR',
            account_holder_name='شرکت تست',
            account_holder_national_id='1234567890',
            opening_date=timezone.now().date(),
            current_balance=Decimal('2000000.00'),
            available_balance=Decimal('1800000.00'),
            is_default=True,
            chart_account=self.asset_account
        )


class ChartOfAccountsUITests(AccountingUITestCase):
    """Test Chart of Accounts UI components."""
    
    def test_chart_of_accounts_list_view(self):
        """Test chart of accounts list view renders correctly."""
        url = reverse('accounting:chart_of_accounts_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'فهرست حساب‌ها')
        self.assertContains(response, self.asset_account.account_name_persian)
        self.assertContains(response, self.asset_account.account_code)
        self.assertContains(response, 'حساب جدید')
    
    def test_chart_of_accounts_create_view(self):
        """Test chart of accounts create view."""
        url = reverse('accounting:chart_of_accounts_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'حساب جدید')
        self.assertContains(response, 'کد حساب')
        self.assertContains(response, 'نام حساب')
        self.assertContains(response, 'نوع حساب')
    
    def test_chart_of_accounts_create_post(self):
        """Test creating a new chart of account."""
        url = reverse('accounting:chart_of_accounts_create')
        data = {
            'account_code': '1102',
            'account_name_persian': 'بانک',
            'account_name_english': 'Bank',
            'account_type': 'asset',
            'account_category': 'current_assets',
            'normal_balance': 'debit',
            'allow_posting': True,
            'description': 'حساب بانکی'
        }
        
        response = self.client.post(url, data)
        
        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        
        # Verify account was created
        account = ChartOfAccounts.objects.get(account_code='1102')
        self.assertEqual(account.account_name_persian, 'بانک')
        self.assertEqual(account.account_type, 'asset')
    
    def test_chart_of_accounts_form_validation(self):
        """Test chart of accounts form validation."""
        form_data = {
            'account_code': '1103',
            'account_name_persian': 'حساب تست',
            'account_type': 'asset',
            'account_category': 'current_assets',
            'normal_balance': 'credit',  # Wrong balance for asset
            'allow_posting': True
        }
        
        form = ChartOfAccountsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('normal_balance', form.errors)


class JournalEntryUITests(AccountingUITestCase):
    """Test Journal Entry UI components."""
    
    def test_journal_entries_list_view(self):
        """Test journal entries list view."""
        # Create a test journal entry
        entry = JournalEntry.objects.create(
            entry_type='general',
            entry_date=timezone.now().date(),
            description='سند تست',
            total_debit=Decimal('100000.00'),
            total_credit=Decimal('100000.00')
        )
        
        url = reverse('accounting:journal_entries_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'اسناد حسابداری')
        self.assertContains(response, 'سند جدید')
        self.assertContains(response, entry.description)
    
    def test_journal_entry_create_view(self):
        """Test journal entry create view."""
        url = reverse('accounting:journal_entries_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'سند حسابداری جدید')
        self.assertContains(response, 'نوع سند')
        self.assertContains(response, 'تاریخ سند')
        self.assertContains(response, 'شرح سند')
        self.assertContains(response, 'ردیف‌های سند')
        self.assertContains(response, 'تراز سند')
    
    def test_journal_entry_form_validation(self):
        """Test journal entry form validation."""
        form_data = {
            'entry_type': 'general',
            'entry_date': timezone.now().date(),
            'description': 'سند تست',
            'notes': ''
        }
        
        form = JournalEntryForm(data=form_data)
        self.assertTrue(form.is_valid())


class BankAccountUITests(AccountingUITestCase):
    """Test Bank Account UI components."""
    
    def test_bank_accounts_list_view(self):
        """Test bank accounts list view."""
        url = reverse('accounting:bank_accounts_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'حساب‌های بانکی')
        self.assertContains(response, 'حساب بانکی جدید')
        self.assertContains(response, self.bank_account.account_name)
        self.assertContains(response, self.bank_account.account_number)
    
    def test_bank_account_create_view(self):
        """Test bank account create view."""
        url = reverse('accounting:bank_accounts_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'حساب بانکی جدید')
        self.assertContains(response, 'نام حساب')
        self.assertContains(response, 'شماره حساب')
        self.assertContains(response, 'شماره شبا')
    
    def test_bank_account_form_validation(self):
        """Test bank account form validation."""
        form_data = {
            'account_name': 'حساب تست',
            'account_number': '9876543210',
            'iban': 'IR987654321098765432109876',
            'bank_name': 'tejarat',
            'bank_branch': 'شعبه تست',
            'bank_branch_code': '002',
            'account_type': 'savings',
            'currency': 'IRR',
            'account_holder_name': 'نام تست',
            'account_holder_national_id': '0987654321',
            'opening_date': timezone.now().date(),
            'is_default': False,
            'chart_account': self.asset_account.id
        }
        
        form = BankAccountForm(data=form_data)
        self.assertTrue(form.is_valid())


class FinancialReportsUITests(AccountingUITestCase):
    """Test Financial Reports UI components."""
    
    def test_reports_dashboard_view(self):
        """Test financial reports dashboard."""
        url = reverse('accounting:reports_dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'گزارش‌های مالی')
        self.assertContains(response, 'تراز آزمایشی')
        self.assertContains(response, 'صورت سود و زیان')
        self.assertContains(response, 'ترازنامه')
        self.assertContains(response, 'دفتر کل')
        self.assertContains(response, 'دفتر معین')
    
    def test_trial_balance_report_view(self):
        """Test trial balance report view."""
        url = reverse('accounting:trial_balance_report')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تراز آزمایشی')
        self.assertContains(response, 'سال مالی')
        self.assertContains(response, 'ماه دوره')
    
    def test_general_ledger_view(self):
        """Test general ledger view."""
        url = reverse('accounting:general_ledger')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'دفتر کل')
        self.assertContains(response, 'سال مالی')
        self.assertContains(response, 'ماه دوره')
    
    def test_subsidiary_ledger_view(self):
        """Test subsidiary ledger view."""
        url = reverse('accounting:subsidiary_ledger')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'دفتر معین')
        self.assertContains(response, 'انتخاب حساب')


class PersianLocalizationTests(AccountingUITestCase):
    """Test Persian localization in accounting UI."""
    
    def test_persian_numbers_display(self):
        """Test that Persian numbers are displayed correctly."""
        url = reverse('accounting:chart_of_accounts_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check that Persian number formatting is applied
        self.assertContains(response, 'persian-numbers')
    
    def test_shamsi_date_display(self):
        """Test that Shamsi dates are displayed correctly."""
        entry = JournalEntry.objects.create(
            entry_type='general',
            entry_date=timezone.now().date(),
            description='سند تست تاریخ'
        )
        
        url = reverse('accounting:journal_entries_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should contain Shamsi date
        shamsi_date = jdatetime.date.fromgregorian(date=entry.entry_date)
        self.assertContains(response, shamsi_date.strftime('%Y/%m/%d'))
    
    def test_rtl_layout(self):
        """Test that RTL layout is applied correctly."""
        url = reverse('accounting:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for RTL-specific CSS classes
        self.assertContains(response, 'base_rtl.html')


class ThemeSystemTests(AccountingUITestCase):
    """Test dual theme system in accounting UI."""
    
    def test_light_theme_classes(self):
        """Test that light theme classes are applied."""
        url = reverse('accounting:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for light theme classes
        self.assertContains(response, 'light-text-primary')
    
    def test_dark_theme_classes(self):
        """Test that dark theme classes are available."""
        url = reverse('accounting:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for dark theme classes
        self.assertContains(response, 'cyber-text-primary')
        self.assertContains(response, 'is_dark_mode')


class FormValidationTests(AccountingUITestCase):
    """Test form validation in accounting UI."""
    
    def test_account_code_uniqueness(self):
        """Test that account codes must be unique."""
        form_data = {
            'account_code': '1101',  # Same as existing account
            'account_name_persian': 'حساب تکراری',
            'account_type': 'asset',
            'account_category': 'current_assets',
            'normal_balance': 'debit',
            'allow_posting': True
        }
        
        form = ChartOfAccountsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('account_code', form.errors)
    
    def test_iban_validation(self):
        """Test IBAN validation in bank account form."""
        form_data = {
            'account_name': 'حساب تست',
            'account_number': '1111111111',
            'iban': 'INVALID_IBAN',  # Invalid IBAN
            'bank_name': 'melli',
            'bank_branch': 'شعبه تست',
            'account_type': 'checking',
            'currency': 'IRR',
            'account_holder_name': 'نام تست',
            'opening_date': timezone.now().date(),
            'chart_account': self.asset_account.id
        }
        
        form = BankAccountForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('iban', form.errors)


class AccessibilityTests(AccountingUITestCase):
    """Test accessibility features in accounting UI."""
    
    def test_form_labels(self):
        """Test that forms have proper labels."""
        url = reverse('accounting:chart_of_accounts_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for proper form labels
        self.assertContains(response, '<label')
        self.assertContains(response, 'for=')
    
    def test_required_field_indicators(self):
        """Test that required fields are properly marked."""
        url = reverse('accounting:chart_of_accounts_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for required field indicators
        self.assertContains(response, 'required-indicator')
        self.assertContains(response, '*')
    
    def test_error_messages(self):
        """Test that error messages are displayed properly."""
        url = reverse('accounting:chart_of_accounts_create')
        data = {
            'account_code': '',  # Missing required field
            'account_name_persian': '',  # Missing required field
        }
        
        response = self.client.post(url, data)
        
        # Should show form with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form-error')


if __name__ == '__main__':
    pytest.main([__file__])