"""
Tests for Persian Accounting System UI (Frontend).

This module tests the Persian accounting system UI components including:
- Chart of accounts management interface
- Journal entry creation and editing forms
- General ledger and subsidiary ledger viewing interfaces
- Bank account management interface
- Cheque management interface
- Persian financial reporting interface
"""

import os
import django
from django.conf import settings

# Configure Django settings before importing models
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

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

User = get_user_model()


class AccountingUITestCase(TestCase):
    """Base test case for accounting UI tests."""
    
    def setUp(self):
        """Set up test data."""
        # Create tenant (using a simple approach for testing)
        from django_tenants.models import TenantMixin
        
        # For testing, we'll skip tenant creation as it requires complex setup
        self.tenant = None
        
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create client and login
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # Create sample chart of accounts
        self.asset_account = ChartOfAccounts.objects.create(
            account_code='1101',
            account_name_persian='صندوق',
            account_name_english='Cash',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit',
            allow_posting=True
        )
        
        self.revenue_account = ChartOfAccounts.objects.create(
            account_code='4101',
            account_name_persian='فروش طلا',
            account_name_english='Gold Sales',
            account_type='revenue',
            account_category='sales_revenue',
            normal_balance='credit',
            allow_posting=True
        )
        
        # Create sample bank account
        self.bank_account = BankAccount.objects.create(
            account_name='حساب جاری بانک ملی',
            account_number='1234567890',
            iban='IR123456789012345678901234',
            bank_name='melli',
            account_type='checking',
            account_holder_name='فروشگاه طلا و جواهر',
            opening_date=timezone.now().date(),
            chart_account=self.asset_account
        )


class AccountingDashboardUITest(AccountingUITestCase):
    """Test accounting dashboard UI."""
    
    def test_dashboard_loads_successfully(self):
        """Test that accounting dashboard loads successfully."""
        response = self.client.get(reverse('accounting:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'داشبورد حسابداری')
        self.assertContains(response, 'کل حساب‌ها')
        self.assertContains(response, 'اسناد در انتظار')
    
    def test_dashboard_displays_metrics(self):
        """Test that dashboard displays key metrics."""
        response = self.client.get(reverse('accounting:dashboard'))
        self.assertContains(response, 'total_accounts')
        self.assertContains(response, 'pending_entries')
        self.assertContains(response, 'monthly_entries')
        self.assertContains(response, 'active_bank_accounts')
    
    def test_dashboard_quick_actions(self):
        """Test dashboard quick action buttons."""
        response = self.client.get(reverse('accounting:dashboard'))
        self.assertContains(response, 'سند جدید')
        self.assertContains(response, 'حساب جدید')
        self.assertContains(response, reverse('accounting:journal_entries_create'))
        self.assertContains(response, reverse('accounting:chart_of_accounts_create'))


class ChartOfAccountsUITest(AccountingUITestCase):
    """Test Chart of Accounts UI."""
    
    def test_chart_of_accounts_list_loads(self):
        """Test that chart of accounts list loads successfully."""
        response = self.client.get(reverse('accounting:chart_of_accounts_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'فهرست حساب‌ها')
        self.assertContains(response, 'کدینگ حسابداری')
        self.assertContains(response, self.asset_account.account_name_persian)
    
    def test_chart_of_accounts_search(self):
        """Test chart of accounts search functionality."""
        response = self.client.get(
            reverse('accounting:chart_of_accounts_list'),
            {'search': 'صندوق'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.asset_account.account_name_persian)
        self.assertNotContains(response, self.revenue_account.account_name_persian)
    
    def test_chart_of_accounts_filter_by_type(self):
        """Test filtering chart of accounts by type."""
        response = self.client.get(
            reverse('accounting:chart_of_accounts_list'),
            {'type': 'asset'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.asset_account.account_name_persian)
        self.assertNotContains(response, self.revenue_account.account_name_persian)
    
    def test_chart_of_accounts_create_form_loads(self):
        """Test that chart of accounts create form loads."""
        response = self.client.get(reverse('accounting:chart_of_accounts_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'حساب جدید')
        self.assertContains(response, 'کد حساب')
        self.assertContains(response, 'نام حساب (فارسی)')
        self.assertContains(response, 'نوع حساب')
    
    def test_chart_of_accounts_create_post(self):
        """Test creating a new chart of account."""
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
        response = self.client.post(reverse('accounting:chart_of_accounts_create'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        
        # Check that account was created
        account = ChartOfAccounts.objects.get(account_code='1102')
        self.assertEqual(account.account_name_persian, 'بانک')
    
    def test_chart_of_accounts_edit_form_loads(self):
        """Test that chart of accounts edit form loads."""
        response = self.client.get(
            reverse('accounting:chart_of_accounts_edit', args=[self.asset_account.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ویرایش حساب')
        self.assertContains(response, self.asset_account.account_name_persian)
    
    def test_chart_of_accounts_detail_view(self):
        """Test chart of accounts detail view."""
        response = self.client.get(
            reverse('accounting:chart_of_accounts_detail', args=[self.asset_account.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.asset_account.account_name_persian)
        self.assertContains(response, self.asset_account.account_code)


class JournalEntryUITest(AccountingUITestCase):
    """Test Journal Entry UI."""
    
    def setUp(self):
        super().setUp()
        # Create sample journal entry
        self.journal_entry = JournalEntry.objects.create(
            entry_type='general',
            entry_date=timezone.now().date(),
            description='تست سند حسابداری',
            status='draft'
        )
        
        # Create journal entry lines
        JournalEntryLine.objects.create(
            journal_entry=self.journal_entry,
            account=self.asset_account,
            description='بدهکار صندوق',
            debit_amount=Decimal('1000000'),
            line_number=1
        )
        
        JournalEntryLine.objects.create(
            journal_entry=self.journal_entry,
            account=self.revenue_account,
            description='بستانکار فروش',
            credit_amount=Decimal('1000000'),
            line_number=2
        )
    
    def test_journal_entries_list_loads(self):
        """Test that journal entries list loads successfully."""
        response = self.client.get(reverse('accounting:journal_entries_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'اسناد حسابداری')
        self.assertContains(response, self.journal_entry.description)
    
    def test_journal_entries_search(self):
        """Test journal entries search functionality."""
        response = self.client.get(
            reverse('accounting:journal_entries_list'),
            {'search': 'تست'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.journal_entry.description)
    
    def test_journal_entries_filter_by_status(self):
        """Test filtering journal entries by status."""
        response = self.client.get(
            reverse('accounting:journal_entries_list'),
            {'status': 'draft'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.journal_entry.description)
    
    def test_journal_entry_create_form_loads(self):
        """Test that journal entry create form loads."""
        response = self.client.get(reverse('accounting:journal_entries_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'سند جدید')
        self.assertContains(response, 'نوع سند')
        self.assertContains(response, 'تاریخ')
        self.assertContains(response, 'شرح سند')
    
    def test_journal_entry_detail_view(self):
        """Test journal entry detail view."""
        response = self.client.get(
            reverse('accounting:journal_entries_detail', args=[self.journal_entry.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.journal_entry.description)
        self.assertContains(response, self.journal_entry.entry_number)
        self.assertContains(response, 'بدهکار صندوق')
        self.assertContains(response, 'بستانکار فروش')
    
    def test_journal_entry_edit_form_loads(self):
        """Test that journal entry edit form loads for draft entries."""
        response = self.client.get(
            reverse('accounting:journal_entries_edit', args=[self.journal_entry.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ویرایش سند')
        self.assertContains(response, self.journal_entry.description)


class BankAccountUITest(AccountingUITestCase):
    """Test Bank Account UI."""
    
    def test_bank_accounts_list_loads(self):
        """Test that bank accounts list loads successfully."""
        response = self.client.get(reverse('accounting:bank_accounts_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'حساب‌های بانکی')
        self.assertContains(response, self.bank_account.account_name)
    
    def test_bank_account_create_form_loads(self):
        """Test that bank account create form loads."""
        response = self.client.get(reverse('accounting:bank_accounts_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'حساب بانکی جدید')
        self.assertContains(response, 'نام حساب')
        self.assertContains(response, 'شماره حساب')
        self.assertContains(response, 'شماره شبا')
        self.assertContains(response, 'نام بانک')
    
    def test_bank_account_create_post(self):
        """Test creating a new bank account."""
        data = {
            'account_name': 'حساب پس‌انداز',
            'account_number': '9876543210',
            'iban': 'IR987654321098765432109876',
            'bank_name': 'mellat',
            'account_type': 'savings',
            'account_holder_name': 'فروشگاه طلا',
            'opening_date': timezone.now().date(),
            'chart_account': self.asset_account.pk
        }
        response = self.client.post(reverse('accounting:bank_accounts_create'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        
        # Check that bank account was created
        bank_account = BankAccount.objects.get(account_number='9876543210')
        self.assertEqual(bank_account.account_name, 'حساب پس‌انداز')
    
    def test_bank_account_detail_view(self):
        """Test bank account detail view."""
        response = self.client.get(
            reverse('accounting:bank_accounts_detail', args=[self.bank_account.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.bank_account.account_name)
        self.assertContains(response, self.bank_account.account_number)


class ChequeManagementUITest(AccountingUITestCase):
    """Test Cheque Management UI."""
    
    def setUp(self):
        super().setUp()
        # Create sample cheque
        self.cheque = ChequeManagement.objects.create(
            cheque_number='123456',
            cheque_type='received',
            bank_account=self.bank_account,
            amount=Decimal('5000000'),
            issue_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            payee_name='فروشگاه طلا',
            payer_name='مشتری تست',
            description='چک دریافتی تست'
        )
    
    def test_cheques_list_loads(self):
        """Test that cheques list loads successfully."""
        response = self.client.get(reverse('accounting:cheques_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مدیریت چک‌ها')
        self.assertContains(response, self.cheque.cheque_number)
    
    def test_cheques_filter_by_type(self):
        """Test filtering cheques by type."""
        response = self.client.get(
            reverse('accounting:cheques_list'),
            {'type': 'received'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.cheque.cheque_number)
    
    def test_cheque_create_form_loads(self):
        """Test that cheque create form loads."""
        response = self.client.get(reverse('accounting:cheques_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'چک جدید')
        self.assertContains(response, 'شماره چک')
        self.assertContains(response, 'نوع چک')
        self.assertContains(response, 'مبلغ چک')
    
    def test_cheque_create_post(self):
        """Test creating a new cheque."""
        data = {
            'cheque_number': '789012',
            'cheque_type': 'issued',
            'bank_account': self.bank_account.pk,
            'amount': Decimal('3000000'),
            'issue_date': timezone.now().date(),
            'due_date': timezone.now().date() + timezone.timedelta(days=15),
            'payee_name': 'تامین‌کننده',
            'description': 'چک صادره تست'
        }
        response = self.client.post(reverse('accounting:cheques_create'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        
        # Check that cheque was created
        cheque = ChequeManagement.objects.get(cheque_number='789012')
        self.assertEqual(cheque.cheque_type, 'issued')
    
    def test_cheque_detail_view(self):
        """Test cheque detail view."""
        response = self.client.get(
            reverse('accounting:cheques_detail', args=[self.cheque.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.cheque.cheque_number)
        self.assertContains(response, self.cheque.description)


class FinancialReportsUITest(AccountingUITestCase):
    """Test Financial Reports UI."""
    
    def test_reports_dashboard_loads(self):
        """Test that reports dashboard loads successfully."""
        response = self.client.get(reverse('accounting:reports_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'گزارش‌های مالی')
        self.assertContains(response, 'تراز آزمایشی')
        self.assertContains(response, 'صورت سود و زیان')
        self.assertContains(response, 'ترازنامه')
    
    def test_trial_balance_report_loads(self):
        """Test that trial balance report loads."""
        response = self.client.get(reverse('accounting:trial_balance_report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تراز آزمایشی')
        self.assertContains(response, 'سال مالی')
        self.assertContains(response, 'ماه دوره')
    
    def test_profit_loss_report_loads(self):
        """Test that profit & loss report loads."""
        response = self.client.get(reverse('accounting:profit_loss_report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'صورت سود و زیان')
        self.assertContains(response, 'سال مالی')
    
    def test_balance_sheet_report_loads(self):
        """Test that balance sheet report loads."""
        response = self.client.get(reverse('accounting:balance_sheet_report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ترازنامه')
        self.assertContains(response, 'سال مالی')


class GeneralLedgerUITest(AccountingUITestCase):
    """Test General Ledger UI."""
    
    def test_general_ledger_loads(self):
        """Test that general ledger view loads successfully."""
        response = self.client.get(reverse('accounting:general_ledger'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'دفتر کل')
        self.assertContains(response, 'سال مالی')
        self.assertContains(response, 'ماه دوره')


class SubsidiaryLedgerUITest(AccountingUITestCase):
    """Test Subsidiary Ledger UI."""
    
    def test_subsidiary_ledger_loads(self):
        """Test that subsidiary ledger view loads successfully."""
        response = self.client.get(reverse('accounting:subsidiary_ledger'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'دفتر معین')
        self.assertContains(response, 'انتخاب حساب')


class PersianFormattingUITest(AccountingUITestCase):
    """Test Persian formatting in UI."""
    
    def test_persian_numbers_in_dashboard(self):
        """Test that Persian numbers are displayed correctly."""
        response = self.client.get(reverse('accounting:dashboard'))
        self.assertEqual(response.status_code, 200)
        # Check for Persian number class
        self.assertContains(response, 'persian-numbers')
    
    def test_persian_currency_formatting(self):
        """Test Persian currency formatting in templates."""
        response = self.client.get(reverse('accounting:chart_of_accounts_list'))
        self.assertEqual(response.status_code, 200)
        # Check for Persian currency filter usage
        self.assertContains(response, 'persian_currency')
    
    def test_shamsi_date_display(self):
        """Test Shamsi date display in UI."""
        response = self.client.get(reverse('accounting:dashboard'))
        self.assertEqual(response.status_code, 200)
        # Check for Shamsi date display
        self.assertContains(response, 'تاریخ شمسی')


class ResponsiveDesignUITest(AccountingUITestCase):
    """Test responsive design elements."""
    
    def test_mobile_responsive_classes(self):
        """Test that mobile responsive classes are present."""
        response = self.client.get(reverse('accounting:dashboard'))
        self.assertEqual(response.status_code, 200)
        # Check for responsive grid classes
        self.assertContains(response, 'grid-cols-1')
        self.assertContains(response, 'md:grid-cols-2')
        self.assertContains(response, 'lg:grid-cols-4')
    
    def test_cybersecurity_theme_classes(self):
        """Test that cybersecurity theme classes are present."""
        response = self.client.get(reverse('accounting:dashboard'))
        self.assertEqual(response.status_code, 200)
        # Check for cybersecurity theme classes
        self.assertContains(response, 'card-cyber')
        self.assertContains(response, 'btn-primary-cyber')
        self.assertContains(response, 'cyber-text-primary')


class AccessibilityUITest(AccountingUITestCase):
    """Test accessibility features."""
    
    def test_form_labels_present(self):
        """Test that form labels are present for accessibility."""
        response = self.client.get(reverse('accounting:chart_of_accounts_create'))
        self.assertEqual(response.status_code, 200)
        # Check for proper form labels
        self.assertContains(response, '<label')
        self.assertContains(response, 'for=')
    
    def test_aria_labels_present(self):
        """Test that ARIA labels are present where needed."""
        response = self.client.get(reverse('accounting:dashboard'))
        self.assertEqual(response.status_code, 200)
        # Check for button titles/aria-labels
        self.assertContains(response, 'title=')


if __name__ == '__main__':
    pytest.main([__file__])