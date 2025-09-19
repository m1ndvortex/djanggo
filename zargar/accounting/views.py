"""
Persian Accounting System Views for ZARGAR Jewelry SaaS.

This module implements comprehensive Persian accounting views following Iranian
accounting standards and terminology. All views are tenant-aware and support
Persian localization with RTL layout and Shamsi calendar integration.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.paginator import Paginator
from django.db import transaction
from decimal import Decimal
import json
import jdatetime
from datetime import datetime, timedelta

from zargar.core.mixins import TenantContextMixin
from zargar.core.persian_number_formatter import PersianNumberFormatter
from .models import (
    ChartOfAccounts, JournalEntry, JournalEntryLine, 
    GeneralLedger, SubsidiaryLedger, BankAccount, ChequeManagement
)
from .forms import (
    ChartOfAccountsForm, JournalEntryForm, JournalEntryLineFormSet,
    BankAccountForm, ChequeManagementForm, FinancialReportForm
)


class AccountingDashboardView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Main accounting dashboard with key metrics and quick actions.
    """
    template_name = 'accounting/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current Shamsi date
        today = timezone.now().date()
        shamsi_today = jdatetime.date.fromgregorian(date=today)
        current_year = str(shamsi_today.year)
        current_month = shamsi_today.month
        
        # Key metrics
        context.update({
            'total_accounts': ChartOfAccounts.objects.filter(is_active=True).count(),
            'pending_entries': JournalEntry.objects.filter(status='draft').count(),
            'monthly_entries': JournalEntry.objects.filter(
                entry_date__year=today.year,
                entry_date__month=today.month
            ).count(),
            'active_bank_accounts': BankAccount.objects.filter(is_active=True).count(),
            'pending_cheques': ChequeManagement.objects.filter(status='pending').count(),
            'overdue_cheques': ChequeManagement.objects.filter(
                status__in=['pending', 'presented'],
                due_date__lt=today
            ).count(),
            'shamsi_date': shamsi_today.strftime('%Y/%m/%d'),
            'current_year': current_year,
            'current_month': current_month,
        })
        
        # Recent journal entries
        context['recent_entries'] = JournalEntry.objects.select_related().order_by('-created_at')[:5]
        
        # Account type summary
        account_summary = ChartOfAccounts.objects.filter(is_active=True).values('account_type').annotate(
            count=Count('id'),
            total_balance=Sum('current_balance')
        )
        context['account_summary'] = account_summary
        
        return context


# Chart of Accounts Views
class ChartOfAccountsListView(LoginRequiredMixin, TenantContextMixin, ListView):
    """
    List view for Chart of Accounts with Persian terminology.
    """
    model = ChartOfAccounts
    template_name = 'accounting/chart_of_accounts/list.html'
    context_object_name = 'accounts'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = ChartOfAccounts.objects.filter(is_active=True).order_by('account_code')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(account_code__icontains=search) |
                Q(account_name_persian__icontains=search) |
                Q(account_name_english__icontains=search)
            )
        
        # Filter by account type
        account_type = self.request.GET.get('type')
        if account_type:
            queryset = queryset.filter(account_type=account_type)
        
        # Filter by category
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(account_category=category)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['account_types'] = ChartOfAccounts.ACCOUNT_TYPES
        context['account_categories'] = ChartOfAccounts.ACCOUNT_CATEGORIES
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_type'] = self.request.GET.get('type', '')
        context['selected_category'] = self.request.GET.get('category', '')
        return context


class ChartOfAccountsCreateView(LoginRequiredMixin, TenantContextMixin, CreateView):
    """
    Create view for new Chart of Accounts.
    """
    model = ChartOfAccounts
    form_class = ChartOfAccountsForm
    template_name = 'accounting/chart_of_accounts/form.html'
    success_url = reverse_lazy('accounting:chart_of_accounts_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('حساب جدید با موفقیت ایجاد شد.'))
        return super().form_valid(form)


class ChartOfAccountsUpdateView(LoginRequiredMixin, TenantContextMixin, UpdateView):
    """
    Update view for Chart of Accounts.
    """
    model = ChartOfAccounts
    form_class = ChartOfAccountsForm
    template_name = 'accounting/chart_of_accounts/form.html'
    success_url = reverse_lazy('accounting:chart_of_accounts_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('حساب با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)


class ChartOfAccountsDetailView(LoginRequiredMixin, TenantContextMixin, DetailView):
    """
    Detail view for Chart of Accounts with transaction history.
    """
    model = ChartOfAccounts
    template_name = 'accounting/chart_of_accounts/detail.html'
    context_object_name = 'account'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        account = self.get_object()
        
        # Get recent transactions
        recent_transactions = SubsidiaryLedger.objects.filter(
            account=account
        ).order_by('-transaction_date')[:20]
        
        context['recent_transactions'] = recent_transactions
        context['formatted_balance'] = PersianNumberFormatter.format_currency(account.current_balance)
        
        return context


# Journal Entry Views
class JournalEntryListView(LoginRequiredMixin, TenantContextMixin, ListView):
    """
    List view for Journal Entries with Persian terminology.
    """
    model = JournalEntry
    template_name = 'accounting/journal_entries/list.html'
    context_object_name = 'entries'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = JournalEntry.objects.select_related().order_by('-entry_date', '-entry_number')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(entry_number__icontains=search) |
                Q(description__icontains=search) |
                Q(reference_number__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by entry type
        entry_type = self.request.GET.get('type')
        if entry_type:
            queryset = queryset.filter(entry_type=entry_type)
        
        # Date range filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(entry_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(entry_date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entry_types'] = JournalEntry.ENTRY_TYPES
        context['status_choices'] = JournalEntry.STATUS_CHOICES
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_type'] = self.request.GET.get('type', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        return context


class JournalEntryCreateView(LoginRequiredMixin, TenantContextMixin, CreateView):
    """
    Create view for new Journal Entry with lines.
    """
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'accounting/journal_entries/form.html'
    success_url = reverse_lazy('accounting:journal_entries_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = JournalEntryLineFormSet(self.request.POST)
        else:
            context['formset'] = JournalEntryLineFormSet()
        
        # Get active accounts for dropdown
        context['accounts'] = ChartOfAccounts.objects.filter(
            is_active=True, allow_posting=True
        ).order_by('account_code')
        
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        with transaction.atomic():
            if formset.is_valid():
                self.object = form.save()
                formset.instance = self.object
                formset.save()
                
                # Create subsidiary ledger entries
                for line in self.object.lines.all():
                    SubsidiaryLedger.objects.create(
                        account=line.account,
                        journal_entry_line=line
                    )
                
                messages.success(self.request, _('سند حسابداری با موفقیت ایجاد شد.'))
                return super().form_valid(form)
            else:
                return self.form_invalid(form)


class JournalEntryUpdateView(LoginRequiredMixin, TenantContextMixin, UpdateView):
    """
    Update view for Journal Entry (only if not posted).
    """
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'accounting/journal_entries/form.html'
    success_url = reverse_lazy('accounting:journal_entries_list')
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.status == 'posted':
            messages.error(self.request, _('نمی‌توان سند ثبت شده را ویرایش کرد.'))
            return redirect('accounting:journal_entries_list')
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = JournalEntryLineFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = JournalEntryLineFormSet(instance=self.object)
        
        context['accounts'] = ChartOfAccounts.objects.filter(
            is_active=True, allow_posting=True
        ).order_by('account_code')
        
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        with transaction.atomic():
            if formset.is_valid():
                self.object = form.save()
                formset.save()
                
                # Update subsidiary ledger entries
                # Delete existing entries
                SubsidiaryLedger.objects.filter(
                    journal_entry_line__journal_entry=self.object
                ).delete()
                
                # Create new entries
                for line in self.object.lines.all():
                    SubsidiaryLedger.objects.create(
                        account=line.account,
                        journal_entry_line=line
                    )
                
                messages.success(self.request, _('سند حسابداری با موفقیت به‌روزرسانی شد.'))
                return super().form_valid(form)
            else:
                return self.form_invalid(form)


class JournalEntryDetailView(LoginRequiredMixin, TenantContextMixin, DetailView):
    """
    Detail view for Journal Entry with lines.
    """
    model = JournalEntry
    template_name = 'accounting/journal_entries/detail.html'
    context_object_name = 'entry'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entry = self.get_object()
        
        context['lines'] = entry.lines.select_related('account').order_by('line_number')
        context['formatted_total_debit'] = PersianNumberFormatter.format_currency(entry.total_debit)
        context['formatted_total_credit'] = PersianNumberFormatter.format_currency(entry.total_credit)
        
        return context


# General Ledger Views
class GeneralLedgerView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    General Ledger view with period selection.
    """
    template_name = 'accounting/general_ledger/view.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current Shamsi year and month
        today = timezone.now().date()
        shamsi_today = jdatetime.date.fromgregorian(date=today)
        
        # Get parameters from request
        fiscal_year = self.request.GET.get('year', str(shamsi_today.year))
        period_month = int(self.request.GET.get('month', shamsi_today.month))
        account_id = self.request.GET.get('account')
        
        # Get general ledger entries
        queryset = GeneralLedger.objects.filter(
            fiscal_year=fiscal_year,
            period_month=period_month
        ).select_related('account').order_by('account__account_code')
        
        if account_id:
            queryset = queryset.filter(account_id=account_id)
        
        context.update({
            'ledger_entries': queryset,
            'fiscal_year': fiscal_year,
            'period_month': period_month,
            'selected_account': account_id,
            'accounts': ChartOfAccounts.objects.filter(is_active=True).order_by('account_code'),
            'shamsi_months': [
                (1, 'فروردین'), (2, 'اردیبهشت'), (3, 'خرداد'),
                (4, 'تیر'), (5, 'مرداد'), (6, 'شهریور'),
                (7, 'مهر'), (8, 'آبان'), (9, 'آذر'),
                (10, 'دی'), (11, 'بهمن'), (12, 'اسفند')
            ]
        })
        
        return context


# Subsidiary Ledger Views
class SubsidiaryLedgerView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Subsidiary Ledger view for detailed account transactions.
    """
    template_name = 'accounting/subsidiary_ledger/view.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        account_id = self.request.GET.get('account')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if not account_id:
            context['error'] = _('لطفاً حساب مورد نظر را انتخاب کنید.')
            context['accounts'] = ChartOfAccounts.objects.filter(is_active=True).order_by('account_code')
            return context
        
        account = get_object_or_404(ChartOfAccounts, id=account_id)
        
        # Get subsidiary ledger entries
        queryset = SubsidiaryLedger.objects.filter(
            account=account
        ).select_related('journal_entry_line__journal_entry').order_by('transaction_date', 'id')
        
        if date_from:
            queryset = queryset.filter(transaction_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(transaction_date__lte=date_to)
        
        # Paginate results
        paginator = Paginator(queryset, 50)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context.update({
            'account': account,
            'transactions': page_obj,
            'accounts': ChartOfAccounts.objects.filter(is_active=True).order_by('account_code'),
            'selected_account': account_id,
            'date_from': date_from,
            'date_to': date_to,
        })
        
        return context


# Bank Account Views
class BankAccountListView(LoginRequiredMixin, TenantContextMixin, ListView):
    """
    List view for Bank Accounts.
    """
    model = BankAccount
    template_name = 'accounting/bank_accounts/list.html'
    context_object_name = 'bank_accounts'
    
    def get_queryset(self):
        return BankAccount.objects.filter(is_active=True).order_by('bank_name', 'account_name')


class BankAccountCreateView(LoginRequiredMixin, TenantContextMixin, CreateView):
    """
    Create view for new Bank Account.
    """
    model = BankAccount
    form_class = BankAccountForm
    template_name = 'accounting/bank_accounts/form.html'
    success_url = reverse_lazy('accounting:bank_accounts_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('حساب بانکی جدید با موفقیت ایجاد شد.'))
        return super().form_valid(form)


class BankAccountUpdateView(LoginRequiredMixin, TenantContextMixin, UpdateView):
    """
    Update view for Bank Account.
    """
    model = BankAccount
    form_class = BankAccountForm
    template_name = 'accounting/bank_accounts/form.html'
    success_url = reverse_lazy('accounting:bank_accounts_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('حساب بانکی با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)


class BankAccountDetailView(LoginRequiredMixin, TenantContextMixin, DetailView):
    """
    Detail view for Bank Account with transaction history.
    """
    model = BankAccount
    template_name = 'accounting/bank_accounts/detail.html'
    context_object_name = 'bank_account'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bank_account = self.get_object()
        
        # Get recent cheques
        recent_cheques = ChequeManagement.objects.filter(
            bank_account=bank_account
        ).order_by('-created_at')[:10]
        
        context['recent_cheques'] = recent_cheques
        context['formatted_balance'] = PersianNumberFormatter.format_currency(bank_account.current_balance)
        context['formatted_available'] = PersianNumberFormatter.format_currency(bank_account.available_balance)
        
        return context


# Cheque Management Views
class ChequeManagementListView(LoginRequiredMixin, TenantContextMixin, ListView):
    """
    List view for Cheque Management.
    """
    model = ChequeManagement
    template_name = 'accounting/cheques/list.html'
    context_object_name = 'cheques'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = ChequeManagement.objects.select_related('bank_account').order_by('-due_date')
        
        # Filter by cheque type
        cheque_type = self.request.GET.get('type')
        if cheque_type:
            queryset = queryset.filter(cheque_type=cheque_type)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by bank account
        bank_account = self.request.GET.get('bank_account')
        if bank_account:
            queryset = queryset.filter(bank_account_id=bank_account)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cheque_types'] = ChequeManagement.CHEQUE_TYPES
        context['status_choices'] = ChequeManagement.CHEQUE_STATUS
        context['bank_accounts'] = BankAccount.objects.filter(is_active=True)
        context['selected_type'] = self.request.GET.get('type', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_bank_account'] = self.request.GET.get('bank_account', '')
        return context


class ChequeManagementCreateView(LoginRequiredMixin, TenantContextMixin, CreateView):
    """
    Create view for new Cheque.
    """
    model = ChequeManagement
    form_class = ChequeManagementForm
    template_name = 'accounting/cheques/form.html'
    success_url = reverse_lazy('accounting:cheques_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('چک جدید با موفقیت ایجاد شد.'))
        return super().form_valid(form)


class ChequeManagementUpdateView(LoginRequiredMixin, TenantContextMixin, UpdateView):
    """
    Update view for Cheque.
    """
    model = ChequeManagement
    form_class = ChequeManagementForm
    template_name = 'accounting/cheques/form.html'
    success_url = reverse_lazy('accounting:cheques_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('چک با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)


class ChequeManagementDetailView(LoginRequiredMixin, TenantContextMixin, DetailView):
    """
    Detail view for Cheque with lifecycle tracking.
    """
    model = ChequeManagement
    template_name = 'accounting/cheques/detail.html'
    context_object_name = 'cheque'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cheque = self.get_object()
        
        context['formatted_amount'] = PersianNumberFormatter.format_currency(cheque.amount)
        context['is_overdue'] = cheque.is_overdue
        context['days_until_due'] = cheque.days_until_due
        
        return context


# Financial Reports Views
class FinancialReportsView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Financial Reports dashboard with Persian reports.
    """
    template_name = 'accounting/reports/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current Shamsi date
        today = timezone.now().date()
        shamsi_today = jdatetime.date.fromgregorian(date=today)
        
        context.update({
            'current_shamsi_year': str(shamsi_today.year),
            'current_shamsi_month': shamsi_today.month,
            'shamsi_months': [
                (1, 'فروردین'), (2, 'اردیبهشت'), (3, 'خرداد'),
                (4, 'تیر'), (5, 'مرداد'), (6, 'شهریور'),
                (7, 'مهر'), (8, 'آبان'), (9, 'آذر'),
                (10, 'دی'), (11, 'بهمن'), (12, 'اسفند')
            ]
        })
        
        return context


class TrialBalanceReportView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Trial Balance Report (تراز آزمایشی).
    """
    template_name = 'accounting/reports/trial_balance.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get parameters
        fiscal_year = self.request.GET.get('year')
        period_month = self.request.GET.get('month')
        
        if fiscal_year and period_month:
            # Get trial balance data
            trial_balance = GeneralLedger.objects.filter(
                fiscal_year=fiscal_year,
                period_month=int(period_month)
            ).select_related('account').order_by('account__account_code')
            
            # Calculate totals
            total_debit = sum(entry.period_debit for entry in trial_balance)
            total_credit = sum(entry.period_credit for entry in trial_balance)
            total_balance_debit = sum(entry.closing_balance for entry in trial_balance if entry.closing_balance > 0)
            total_balance_credit = sum(abs(entry.closing_balance) for entry in trial_balance if entry.closing_balance < 0)
            
            context.update({
                'trial_balance': trial_balance,
                'fiscal_year': fiscal_year,
                'period_month': int(period_month),
                'total_debit': total_debit,
                'total_credit': total_credit,
                'total_balance_debit': total_balance_debit,
                'total_balance_credit': total_balance_credit,
                'formatted_total_debit': PersianNumberFormatter.format_currency(total_debit),
                'formatted_total_credit': PersianNumberFormatter.format_currency(total_credit),
            })
        
        # Get current Shamsi date for defaults
        today = timezone.now().date()
        shamsi_today = jdatetime.date.fromgregorian(date=today)
        
        context.update({
            'current_shamsi_year': str(shamsi_today.year),
            'current_shamsi_month': shamsi_today.month,
            'shamsi_months': [
                (1, 'فروردین'), (2, 'اردیبهشت'), (3, 'خرداد'),
                (4, 'تیر'), (5, 'مرداد'), (6, 'شهریور'),
                (7, 'مهر'), (8, 'آبان'), (9, 'آذر'),
                (10, 'دی'), (11, 'بهمن'), (12, 'اسفند')
            ]
        })
        
        return context


class ProfitLossReportView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Profit & Loss Statement (صورت سود و زیان).
    """
    template_name = 'accounting/reports/profit_loss.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get parameters
        fiscal_year = self.request.GET.get('year')
        
        if fiscal_year:
            # Get revenue accounts
            revenue_accounts = GeneralLedger.objects.filter(
                fiscal_year=fiscal_year,
                account__account_type='revenue'
            ).select_related('account')
            
            # Get expense accounts
            expense_accounts = GeneralLedger.objects.filter(
                fiscal_year=fiscal_year,
                account__account_type='expense'
            ).select_related('account')
            
            # Get COGS accounts
            cogs_accounts = GeneralLedger.objects.filter(
                fiscal_year=fiscal_year,
                account__account_type='cost_of_goods_sold'
            ).select_related('account')
            
            # Calculate totals
            total_revenue = sum(account.closing_balance for account in revenue_accounts)
            total_expenses = sum(account.closing_balance for account in expense_accounts)
            total_cogs = sum(account.closing_balance for account in cogs_accounts)
            
            gross_profit = total_revenue - total_cogs
            net_profit = gross_profit - total_expenses
            
            context.update({
                'revenue_accounts': revenue_accounts,
                'expense_accounts': expense_accounts,
                'cogs_accounts': cogs_accounts,
                'fiscal_year': fiscal_year,
                'total_revenue': total_revenue,
                'total_expenses': total_expenses,
                'total_cogs': total_cogs,
                'gross_profit': gross_profit,
                'net_profit': net_profit,
                'formatted_total_revenue': PersianNumberFormatter.format_currency(total_revenue),
                'formatted_gross_profit': PersianNumberFormatter.format_currency(gross_profit),
                'formatted_net_profit': PersianNumberFormatter.format_currency(net_profit),
            })
        
        # Get current Shamsi date for defaults
        today = timezone.now().date()
        shamsi_today = jdatetime.date.fromgregorian(date=today)
        
        context['current_shamsi_year'] = str(shamsi_today.year)
        
        return context


class BalanceSheetReportView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Balance Sheet Report (ترازنامه).
    """
    template_name = 'accounting/reports/balance_sheet.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get parameters
        fiscal_year = self.request.GET.get('year')
        
        if fiscal_year:
            # Get asset accounts
            asset_accounts = GeneralLedger.objects.filter(
                fiscal_year=fiscal_year,
                account__account_type='asset'
            ).select_related('account').order_by('account__account_category', 'account__account_code')
            
            # Get liability accounts
            liability_accounts = GeneralLedger.objects.filter(
                fiscal_year=fiscal_year,
                account__account_type='liability'
            ).select_related('account').order_by('account__account_category', 'account__account_code')
            
            # Get equity accounts
            equity_accounts = GeneralLedger.objects.filter(
                fiscal_year=fiscal_year,
                account__account_type='equity'
            ).select_related('account').order_by('account__account_category', 'account__account_code')
            
            # Calculate totals
            total_assets = sum(account.closing_balance for account in asset_accounts)
            total_liabilities = sum(account.closing_balance for account in liability_accounts)
            total_equity = sum(account.closing_balance for account in equity_accounts)
            
            context.update({
                'asset_accounts': asset_accounts,
                'liability_accounts': liability_accounts,
                'equity_accounts': equity_accounts,
                'fiscal_year': fiscal_year,
                'total_assets': total_assets,
                'total_liabilities': total_liabilities,
                'total_equity': total_equity,
                'formatted_total_assets': PersianNumberFormatter.format_currency(total_assets),
                'formatted_total_liabilities': PersianNumberFormatter.format_currency(total_liabilities),
                'formatted_total_equity': PersianNumberFormatter.format_currency(total_equity),
            })
        
        # Get current Shamsi date for defaults
        today = timezone.now().date()
        shamsi_today = jdatetime.date.fromgregorian(date=today)
        
        context['current_shamsi_year'] = str(shamsi_today.year)
        
        return context


# AJAX Views for dynamic functionality
class PostJournalEntryView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    AJAX view to post a journal entry.
    """
    def post(self, request, *args, **kwargs):
        entry_id = request.POST.get('entry_id')
        
        try:
            entry = get_object_or_404(JournalEntry, id=entry_id)
            
            if entry.can_be_posted:
                entry.post(user=request.user)
                return JsonResponse({
                    'success': True,
                    'message': _('سند با موفقیت ثبت شد.')
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': _('سند قابل ثبت نیست. لطفاً تراز سند را بررسی کنید.')
                })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })


class ChequeStatusUpdateView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    AJAX view to update cheque status.
    """
    def post(self, request, *args, **kwargs):
        cheque_id = request.POST.get('cheque_id')
        action = request.POST.get('action')
        
        try:
            cheque = get_object_or_404(ChequeManagement, id=cheque_id)
            
            if action == 'present':
                cheque.present_cheque()
                message = _('چک ارائه شد.')
            elif action == 'clear':
                cheque.clear_cheque()
                message = _('چک تسویه شد.')
            elif action == 'bounce':
                bounce_reason = request.POST.get('bounce_reason', 'other')
                notes = request.POST.get('notes', '')
                cheque.bounce_cheque(bounce_reason, notes=notes)
                message = _('چک برگشت خورد.')
            elif action == 'cancel':
                reason = request.POST.get('reason', '')
                cheque.cancel_cheque(reason)
                message = _('چک لغو شد.')
            else:
                return JsonResponse({
                    'success': False,
                    'message': _('عملیات نامعتبر.')
                })
            
            return JsonResponse({
                'success': True,
                'message': message,
                'new_status': cheque.get_status_display()
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })