"""
URLs for Persian Accounting System module.
"""
from django.urls import path
from . import views

app_name = 'accounting'

urlpatterns = [
    # Main dashboard
    path('', views.AccountingDashboardView.as_view(), name='dashboard'),
    
    # Chart of Accounts URLs
    path('chart-of-accounts/', views.ChartOfAccountsListView.as_view(), name='chart_of_accounts_list'),
    path('chart-of-accounts/create/', views.ChartOfAccountsCreateView.as_view(), name='chart_of_accounts_create'),
    path('chart-of-accounts/<int:pk>/', views.ChartOfAccountsDetailView.as_view(), name='chart_of_accounts_detail'),
    path('chart-of-accounts/<int:pk>/edit/', views.ChartOfAccountsUpdateView.as_view(), name='chart_of_accounts_edit'),
    
    # Journal Entry URLs
    path('journal-entries/', views.JournalEntryListView.as_view(), name='journal_entries_list'),
    path('journal-entries/create/', views.JournalEntryCreateView.as_view(), name='journal_entries_create'),
    path('journal-entries/<int:pk>/', views.JournalEntryDetailView.as_view(), name='journal_entries_detail'),
    path('journal-entries/<int:pk>/edit/', views.JournalEntryUpdateView.as_view(), name='journal_entries_edit'),
    path('journal-entries/post/', views.PostJournalEntryView.as_view(), name='post_journal_entry'),
    
    # General Ledger URLs
    path('general-ledger/', views.GeneralLedgerView.as_view(), name='general_ledger'),
    
    # Subsidiary Ledger URLs
    path('subsidiary-ledger/', views.SubsidiaryLedgerView.as_view(), name='subsidiary_ledger'),
    
    # Bank Account URLs
    path('bank-accounts/', views.BankAccountListView.as_view(), name='bank_accounts_list'),
    path('bank-accounts/create/', views.BankAccountCreateView.as_view(), name='bank_accounts_create'),
    path('bank-accounts/<int:pk>/', views.BankAccountDetailView.as_view(), name='bank_accounts_detail'),
    path('bank-accounts/<int:pk>/edit/', views.BankAccountUpdateView.as_view(), name='bank_accounts_edit'),
    
    # Cheque Management URLs
    path('cheques/', views.ChequeManagementListView.as_view(), name='cheques_list'),
    path('cheques/create/', views.ChequeManagementCreateView.as_view(), name='cheques_create'),
    path('cheques/<int:pk>/', views.ChequeManagementDetailView.as_view(), name='cheques_detail'),
    path('cheques/<int:pk>/edit/', views.ChequeManagementUpdateView.as_view(), name='cheques_edit'),
    path('cheques/update-status/', views.ChequeStatusUpdateView.as_view(), name='cheques_update_status'),
    
    # Financial Reports URLs
    path('reports/', views.FinancialReportsView.as_view(), name='reports_dashboard'),
    path('reports/trial-balance/', views.TrialBalanceReportView.as_view(), name='trial_balance_report'),
    path('reports/profit-loss/', views.ProfitLossReportView.as_view(), name='profit_loss_report'),
    path('reports/balance-sheet/', views.BalanceSheetReportView.as_view(), name='balance_sheet_report'),
]