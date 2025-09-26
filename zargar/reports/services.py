"""
Comprehensive reporting engine services for ZARGAR jewelry SaaS platform.

This module implements the core reporting logic including Persian financial reports,
inventory valuation, customer aging reports, and automated report generation.
"""

from django.db import models
from django.db.models import Sum, Count, Avg, Q, F, Case, When, Value
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Tuple
import jdatetime
from datetime import date, datetime, timedelta

from zargar.core.persian_number_formatter import PersianNumberFormatter
from zargar.accounting.models import (
    ChartOfAccounts, JournalEntry, JournalEntryLine, 
    GeneralLedger, SubsidiaryLedger
)
from zargar.jewelry.models import JewelryItem, Category
from zargar.customers.models import Customer
from zargar.gold_installments.models import GoldInstallmentContract, GoldInstallmentPayment
from .models import ReportTemplate, GeneratedReport


class ComprehensiveReportingEngine:
    """
    Main reporting engine class that handles all report generation logic.
    """
    
    def __init__(self, tenant=None):
        """Initialize reporting engine with tenant context."""
        self.tenant = tenant
        self.formatter = PersianNumberFormatter()
    
    def generate_report(self, template: ReportTemplate, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a report based on template and parameters.
        
        Args:
            template: Report template instance
            parameters: Report generation parameters
            
        Returns:
            Dictionary containing report data
        """
        report_type = template.report_type
        
        # Route to appropriate report generator
        if report_type == 'trial_balance':
            return self.generate_trial_balance(parameters)
        elif report_type == 'profit_loss':
            return self.generate_profit_loss_statement(parameters)
        elif report_type == 'balance_sheet':
            return self.generate_balance_sheet(parameters)
        elif report_type == 'inventory_valuation':
            return self.generate_inventory_valuation_report(parameters)
        elif report_type == 'customer_aging':
            return self.generate_customer_aging_report(parameters)
        elif report_type == 'sales_summary':
            return self.generate_sales_summary_report(parameters)
        elif report_type == 'gold_price_analysis':
            return self.generate_gold_price_analysis_report(parameters)
        elif report_type == 'installment_summary':
            return self.generate_installment_summary_report(parameters)
        else:
            raise ValueError(f"Unsupported report type: {report_type}")
    
    def generate_trial_balance(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Trial Balance report (ترازنامه آزمایشی).
        
        Args:
            parameters: Report parameters including date_from, date_to
            
        Returns:
            Trial balance report data
        """
        date_from = parameters.get('date_from')
        date_to = parameters.get('date_to', timezone.now().date())
        
        # Get all active accounts
        accounts = ChartOfAccounts.objects.filter(
            is_active=True,
            allow_posting=True
        ).order_by('account_code')
        
        trial_balance_data = []
        total_debits = Decimal('0.00')
        total_credits = Decimal('0.00')
        
        for account in accounts:
            # Calculate account balance as of date_to
            balance = account.get_balance_as_of_date(date_to)
            
            # Skip accounts with zero balance unless requested
            if balance == 0 and not parameters.get('include_zero_balances', False):
                continue
            
            # Determine debit/credit presentation
            if account.normal_balance == 'debit':
                debit_amount = balance if balance > 0 else Decimal('0.00')
                credit_amount = abs(balance) if balance < 0 else Decimal('0.00')
            else:
                credit_amount = balance if balance > 0 else Decimal('0.00')
                debit_amount = abs(balance) if balance < 0 else Decimal('0.00')
            
            total_debits += debit_amount
            total_credits += credit_amount
            
            trial_balance_data.append({
                'account_code': account.account_code,
                'account_name_persian': account.account_name_persian,
                'account_name_english': account.account_name_english,
                'account_type': account.get_account_type_display(),
                'debit_amount': debit_amount,
                'credit_amount': credit_amount,
                'debit_amount_formatted': self.formatter.format_currency(
                    debit_amount, use_persian_digits=True
                ),
                'credit_amount_formatted': self.formatter.format_currency(
                    credit_amount, use_persian_digits=True
                ),
            })
        
        # Convert dates to Shamsi
        date_from_shamsi = ""
        date_to_shamsi = ""
        if date_from:
            shamsi_from = jdatetime.date.fromgregorian(date=date_from)
            date_from_shamsi = shamsi_from.strftime('%Y/%m/%d')
        if date_to:
            shamsi_to = jdatetime.date.fromgregorian(date=date_to)
            date_to_shamsi = shamsi_to.strftime('%Y/%m/%d')
        
        return {
            'report_type': 'trial_balance',
            'report_title_persian': 'ترازنامه آزمایشی',
            'report_title_english': 'Trial Balance',
            'date_from': date_from,
            'date_to': date_to,
            'date_from_shamsi': date_from_shamsi,
            'date_to_shamsi': date_to_shamsi,
            'accounts': trial_balance_data,
            'total_debits': total_debits,
            'total_credits': total_credits,
            'total_debits_formatted': self.formatter.format_currency(
                total_debits, use_persian_digits=True
            ),
            'total_credits_formatted': self.formatter.format_currency(
                total_credits, use_persian_digits=True
            ),
            'is_balanced': total_debits == total_credits,
            'generated_at': timezone.now(),
            'generated_at_shamsi': jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M'),
        }
    
    def generate_profit_loss_statement(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Profit & Loss Statement (سود و زیان).
        
        Args:
            parameters: Report parameters including date_from, date_to
            
        Returns:
            P&L statement report data
        """
        date_from = parameters.get('date_from')
        date_to = parameters.get('date_to', timezone.now().date())
        
        # Get revenue accounts
        revenue_accounts = ChartOfAccounts.objects.filter(
            account_type='revenue',
            is_active=True
        ).order_by('account_code')
        
        # Get expense accounts
        expense_accounts = ChartOfAccounts.objects.filter(
            account_type__in=['expense', 'cost_of_goods_sold'],
            is_active=True
        ).order_by('account_code')
        
        # Calculate revenue totals
        revenue_data = []
        total_revenue = Decimal('0.00')
        
        for account in revenue_accounts:
            balance = account.get_balance_as_of_date(date_to)
            if date_from:
                opening_balance = account.get_balance_as_of_date(date_from - timedelta(days=1))
                period_balance = balance - opening_balance
            else:
                period_balance = balance
            
            if period_balance != 0 or parameters.get('include_zero_balances', False):
                revenue_data.append({
                    'account_code': account.account_code,
                    'account_name_persian': account.account_name_persian,
                    'amount': period_balance,
                    'amount_formatted': self.formatter.format_currency(
                        period_balance, use_persian_digits=True
                    ),
                })
                total_revenue += period_balance
        
        # Calculate expense totals
        expense_data = []
        total_expenses = Decimal('0.00')
        
        for account in expense_accounts:
            balance = account.get_balance_as_of_date(date_to)
            if date_from:
                opening_balance = account.get_balance_as_of_date(date_from - timedelta(days=1))
                period_balance = balance - opening_balance
            else:
                period_balance = balance
            
            if period_balance != 0 or parameters.get('include_zero_balances', False):
                expense_data.append({
                    'account_code': account.account_code,
                    'account_name_persian': account.account_name_persian,
                    'amount': period_balance,
                    'amount_formatted': self.formatter.format_currency(
                        period_balance, use_persian_digits=True
                    ),
                })
                total_expenses += period_balance
        
        # Calculate net income
        net_income = total_revenue - total_expenses
        
        # Convert dates to Shamsi
        date_from_shamsi = ""
        date_to_shamsi = ""
        if date_from:
            shamsi_from = jdatetime.date.fromgregorian(date=date_from)
            date_from_shamsi = shamsi_from.strftime('%Y/%m/%d')
        if date_to:
            shamsi_to = jdatetime.date.fromgregorian(date=date_to)
            date_to_shamsi = shamsi_to.strftime('%Y/%m/%d')
        
        return {
            'report_type': 'profit_loss',
            'report_title_persian': 'صورت سود و زیان',
            'report_title_english': 'Profit & Loss Statement',
            'date_from': date_from,
            'date_to': date_to,
            'date_from_shamsi': date_from_shamsi,
            'date_to_shamsi': date_to_shamsi,
            'revenue_accounts': revenue_data,
            'expense_accounts': expense_data,
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'net_income': net_income,
            'total_revenue_formatted': self.formatter.format_currency(
                total_revenue, use_persian_digits=True
            ),
            'total_expenses_formatted': self.formatter.format_currency(
                total_expenses, use_persian_digits=True
            ),
            'net_income_formatted': self.formatter.format_currency(
                net_income, use_persian_digits=True
            ),
            'is_profitable': net_income > 0,
            'generated_at': timezone.now(),
            'generated_at_shamsi': jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M'),
        }
    
    def generate_balance_sheet(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Balance Sheet (ترازنامه).
        
        Args:
            parameters: Report parameters including as_of_date
            
        Returns:
            Balance sheet report data
        """
        as_of_date = parameters.get('as_of_date', timezone.now().date())
        
        # Get asset accounts
        asset_accounts = ChartOfAccounts.objects.filter(
            account_type='asset',
            is_active=True
        ).order_by('account_category', 'account_code')
        
        # Get liability accounts
        liability_accounts = ChartOfAccounts.objects.filter(
            account_type='liability',
            is_active=True
        ).order_by('account_category', 'account_code')
        
        # Get equity accounts
        equity_accounts = ChartOfAccounts.objects.filter(
            account_type='equity',
            is_active=True
        ).order_by('account_category', 'account_code')
        
        # Calculate assets
        assets_data = {}
        total_assets = Decimal('0.00')
        
        for account in asset_accounts:
            balance = account.get_balance_as_of_date(as_of_date)
            if balance != 0 or parameters.get('include_zero_balances', False):
                category = account.get_account_category_display()
                if category not in assets_data:
                    assets_data[category] = []
                
                assets_data[category].append({
                    'account_code': account.account_code,
                    'account_name_persian': account.account_name_persian,
                    'amount': balance,
                    'amount_formatted': self.formatter.format_currency(
                        balance, use_persian_digits=True
                    ),
                })
                total_assets += balance
        
        # Calculate liabilities
        liabilities_data = {}
        total_liabilities = Decimal('0.00')
        
        for account in liability_accounts:
            balance = account.get_balance_as_of_date(as_of_date)
            if balance != 0 or parameters.get('include_zero_balances', False):
                category = account.get_account_category_display()
                if category not in liabilities_data:
                    liabilities_data[category] = []
                
                liabilities_data[category].append({
                    'account_code': account.account_code,
                    'account_name_persian': account.account_name_persian,
                    'amount': balance,
                    'amount_formatted': self.formatter.format_currency(
                        balance, use_persian_digits=True
                    ),
                })
                total_liabilities += balance
        
        # Calculate equity
        equity_data = {}
        total_equity = Decimal('0.00')
        
        for account in equity_accounts:
            balance = account.get_balance_as_of_date(as_of_date)
            if balance != 0 or parameters.get('include_zero_balances', False):
                category = account.get_account_category_display()
                if category not in equity_data:
                    equity_data[category] = []
                
                equity_data[category].append({
                    'account_code': account.account_code,
                    'account_name_persian': account.account_name_persian,
                    'amount': balance,
                    'amount_formatted': self.formatter.format_currency(
                        balance, use_persian_digits=True
                    ),
                })
                total_equity += balance
        
        # Calculate totals
        total_liabilities_equity = total_liabilities + total_equity
        
        # Convert date to Shamsi
        shamsi_date = jdatetime.date.fromgregorian(date=as_of_date)
        as_of_date_shamsi = shamsi_date.strftime('%Y/%m/%d')
        
        return {
            'report_type': 'balance_sheet',
            'report_title_persian': 'ترازنامه',
            'report_title_english': 'Balance Sheet',
            'as_of_date': as_of_date,
            'as_of_date_shamsi': as_of_date_shamsi,
            'assets': assets_data,
            'liabilities': liabilities_data,
            'equity': equity_data,
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'total_equity': total_equity,
            'total_liabilities_equity': total_liabilities_equity,
            'total_assets_formatted': self.formatter.format_currency(
                total_assets, use_persian_digits=True
            ),
            'total_liabilities_formatted': self.formatter.format_currency(
                total_liabilities, use_persian_digits=True
            ),
            'total_equity_formatted': self.formatter.format_currency(
                total_equity, use_persian_digits=True
            ),
            'total_liabilities_equity_formatted': self.formatter.format_currency(
                total_liabilities_equity, use_persian_digits=True
            ),
            'is_balanced': total_assets == total_liabilities_equity,
            'generated_at': timezone.now(),
            'generated_at_shamsi': jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M'),
        }    

    def generate_inventory_valuation_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Inventory Valuation Report (ارزش‌گذاری موجودی).
        
        Args:
            parameters: Report parameters including as_of_date, gold_price_per_gram
            
        Returns:
            Inventory valuation report data
        """
        as_of_date = parameters.get('as_of_date', timezone.now().date())
        gold_price_per_gram = parameters.get('gold_price_per_gram', Decimal('0.00'))
        
        # Get all jewelry items in stock
        jewelry_items = JewelryItem.objects.filter(
            status='in_stock',
            quantity__gt=0
        ).select_related('category').order_by('category__name_persian', 'name')
        
        # Group by category
        categories_data = {}
        total_inventory_value = Decimal('0.00')
        total_items_count = 0
        total_weight = Decimal('0.000')
        
        for item in jewelry_items:
            category_name = item.category.name_persian or item.category.name
            
            if category_name not in categories_data:
                categories_data[category_name] = {
                    'category_name': category_name,
                    'items': [],
                    'category_total_value': Decimal('0.00'),
                    'category_total_weight': Decimal('0.000'),
                    'category_items_count': 0,
                }
            
            # Calculate current gold value if gold price provided
            current_gold_value = Decimal('0.00')
            if gold_price_per_gram > 0:
                current_gold_value = item.calculate_gold_value(gold_price_per_gram)
            
            # Calculate total item value
            item_total_value = (
                current_gold_value + 
                (item.gemstone_value or Decimal('0.00')) + 
                (item.manufacturing_cost or Decimal('0.00'))
            ) * item.quantity
            
            item_data = {
                'sku': item.sku,
                'name': item.name,
                'quantity': item.quantity,
                'weight_grams': item.weight_grams,
                'karat': item.karat,
                'manufacturing_cost': item.manufacturing_cost or Decimal('0.00'),
                'gemstone_value': item.gemstone_value or Decimal('0.00'),
                'current_gold_value': current_gold_value,
                'total_item_value': item_total_value,
                'weight_grams_formatted': self.formatter.format_weight(
                    item.weight_grams, 'gram', use_persian_digits=True
                ),
                'manufacturing_cost_formatted': self.formatter.format_currency(
                    item.manufacturing_cost or Decimal('0.00'), use_persian_digits=True
                ),
                'gemstone_value_formatted': self.formatter.format_currency(
                    item.gemstone_value or Decimal('0.00'), use_persian_digits=True
                ),
                'current_gold_value_formatted': self.formatter.format_currency(
                    current_gold_value, use_persian_digits=True
                ),
                'total_item_value_formatted': self.formatter.format_currency(
                    item_total_value, use_persian_digits=True
                ),
                'is_low_stock': item.is_low_stock,
            }
            
            categories_data[category_name]['items'].append(item_data)
            categories_data[category_name]['category_total_value'] += item_total_value
            categories_data[category_name]['category_total_weight'] += (item.weight_grams * item.quantity)
            categories_data[category_name]['category_items_count'] += item.quantity
            
            total_inventory_value += item_total_value
            total_items_count += item.quantity
            total_weight += (item.weight_grams * item.quantity)
        
        # Format category totals
        for category_data in categories_data.values():
            category_data['category_total_value_formatted'] = self.formatter.format_currency(
                category_data['category_total_value'], use_persian_digits=True
            )
            category_data['category_total_weight_formatted'] = self.formatter.format_weight(
                category_data['category_total_weight'], 'gram', use_persian_digits=True
            )
        
        # Convert date to Shamsi
        shamsi_date = jdatetime.date.fromgregorian(date=as_of_date)
        as_of_date_shamsi = shamsi_date.strftime('%Y/%m/%d')
        
        return {
            'report_type': 'inventory_valuation',
            'report_title_persian': 'گزارش ارزش‌گذاری موجودی',
            'report_title_english': 'Inventory Valuation Report',
            'as_of_date': as_of_date,
            'as_of_date_shamsi': as_of_date_shamsi,
            'gold_price_per_gram': gold_price_per_gram,
            'gold_price_per_gram_formatted': self.formatter.format_currency(
                gold_price_per_gram, use_persian_digits=True
            ),
            'categories': list(categories_data.values()),
            'total_inventory_value': total_inventory_value,
            'total_items_count': total_items_count,
            'total_weight': total_weight,
            'total_inventory_value_formatted': self.formatter.format_currency(
                total_inventory_value, use_persian_digits=True
            ),
            'total_items_count_formatted': self.formatter.format_number(
                total_items_count, use_persian_digits=True
            ),
            'total_weight_formatted': self.formatter.format_weight(
                total_weight, 'gram', use_persian_digits=True
            ),
            'generated_at': timezone.now(),
            'generated_at_shamsi': jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M'),
        }
    
    def generate_customer_aging_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Customer Aging Report (تحلیل سن مطالبات).
        
        Args:
            parameters: Report parameters including as_of_date, aging_periods
            
        Returns:
            Customer aging report data
        """
        as_of_date = parameters.get('as_of_date', timezone.now().date())
        aging_periods = parameters.get('aging_periods', [30, 60, 90, 120])  # Days
        
        # Get all customers with active gold installment contracts
        customers_with_contracts = Customer.objects.filter(
            gold_installment_contracts__status='active'
        ).distinct().order_by('persian_last_name', 'last_name')
        
        aging_data = []
        total_outstanding = Decimal('0.00')
        aging_totals = {f'period_{i}': Decimal('0.00') for i in range(len(aging_periods) + 1)}
        
        for customer in customers_with_contracts:
            # Get active contracts for this customer
            active_contracts = GoldInstallmentContract.objects.filter(
                customer=customer,
                status='active'
            )
            
            customer_total = Decimal('0.00')
            customer_aging = {f'period_{i}': Decimal('0.00') for i in range(len(aging_periods) + 1)}
            
            for contract in active_contracts:
                # Calculate current gold value
                current_gold_price = parameters.get('current_gold_price_per_gram', Decimal('0.00'))
                if current_gold_price > 0:
                    gold_value_data = contract.calculate_current_gold_value(current_gold_price)
                    outstanding_amount = gold_value_data['total_value_toman']
                else:
                    # Use a default calculation if no gold price provided
                    outstanding_amount = contract.remaining_gold_weight_grams * Decimal('1000000')  # Placeholder
                
                customer_total += outstanding_amount
                
                # Determine aging period based on last payment or contract date
                last_payment = contract.payments.order_by('-payment_date').first()
                reference_date = last_payment.payment_date if last_payment else contract.contract_date
                days_outstanding = (as_of_date - reference_date).days
                
                # Categorize into aging periods
                period_index = len(aging_periods)  # Default to oldest period
                for i, period_days in enumerate(aging_periods):
                    if days_outstanding <= period_days:
                        period_index = i
                        break
                
                customer_aging[f'period_{period_index}'] += outstanding_amount
                aging_totals[f'period_{period_index}'] += outstanding_amount
            
            if customer_total > 0:
                customer_data = {
                    'customer_id': customer.id,
                    'customer_name': customer.full_persian_name,
                    'phone_number': customer.phone_number,
                    'total_outstanding': customer_total,
                    'total_outstanding_formatted': self.formatter.format_currency(
                        customer_total, use_persian_digits=True
                    ),
                    'aging_breakdown': customer_aging,
                    'aging_breakdown_formatted': {
                        key: self.formatter.format_currency(value, use_persian_digits=True)
                        for key, value in customer_aging.items()
                    },
                    'active_contracts_count': active_contracts.count(),
                }
                
                aging_data.append(customer_data)
                total_outstanding += customer_total
        
        # Create aging period labels
        aging_period_labels = []
        for i, period_days in enumerate(aging_periods):
            if i == 0:
                aging_period_labels.append(f'0-{period_days} روز')
            else:
                aging_period_labels.append(f'{aging_periods[i-1]+1}-{period_days} روز')
        aging_period_labels.append(f'بیش از {aging_periods[-1]} روز')
        
        # Convert date to Shamsi
        shamsi_date = jdatetime.date.fromgregorian(date=as_of_date)
        as_of_date_shamsi = shamsi_date.strftime('%Y/%m/%d')
        
        return {
            'report_type': 'customer_aging',
            'report_title_persian': 'گزارش تحلیل سن مطالبات مشتریان',
            'report_title_english': 'Customer Aging Report',
            'as_of_date': as_of_date,
            'as_of_date_shamsi': as_of_date_shamsi,
            'aging_periods': aging_periods,
            'aging_period_labels': aging_period_labels,
            'customers': aging_data,
            'total_outstanding': total_outstanding,
            'aging_totals': aging_totals,
            'total_outstanding_formatted': self.formatter.format_currency(
                total_outstanding, use_persian_digits=True
            ),
            'aging_totals_formatted': {
                key: self.formatter.format_currency(value, use_persian_digits=True)
                for key, value in aging_totals.items()
            },
            'total_customers': len(aging_data),
            'generated_at': timezone.now(),
            'generated_at_shamsi': jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M'),
        }
    
    def generate_sales_summary_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Sales Summary Report (خلاصه فروش).
        
        Args:
            parameters: Report parameters including date_from, date_to
            
        Returns:
            Sales summary report data
        """
        date_from = parameters.get('date_from')
        date_to = parameters.get('date_to', timezone.now().date())
        
        # Note: This is a placeholder implementation since POS/Sales models aren't fully implemented yet
        # In a complete implementation, this would query actual sales transactions
        
        # For now, we'll use gold installment payments as a proxy for sales data
        payments_query = GoldInstallmentPayment.objects.filter(
            payment_date__lte=date_to
        )
        
        if date_from:
            payments_query = payments_query.filter(payment_date__gte=date_from)
        
        # Calculate summary statistics
        total_payments = payments_query.count()
        total_amount = payments_query.aggregate(
            total=Sum('payment_amount_toman')
        )['total'] or Decimal('0.00')
        
        average_payment = total_amount / total_payments if total_payments > 0 else Decimal('0.00')
        
        # Group by payment method
        payment_methods = payments_query.values('payment_method').annotate(
            count=Count('id'),
            total_amount=Sum('payment_amount_toman')
        ).order_by('-total_amount')
        
        # Daily breakdown for the period
        daily_breakdown = []
        if date_from and date_to:
            current_date = date_from
            while current_date <= date_to:
                daily_payments = payments_query.filter(payment_date=current_date)
                daily_total = daily_payments.aggregate(
                    total=Sum('payment_amount_toman')
                )['total'] or Decimal('0.00')
                
                daily_breakdown.append({
                    'date': current_date,
                    'date_shamsi': jdatetime.date.fromgregorian(date=current_date).strftime('%Y/%m/%d'),
                    'payment_count': daily_payments.count(),
                    'total_amount': daily_total,
                    'total_amount_formatted': self.formatter.format_currency(
                        daily_total, use_persian_digits=True
                    ),
                })
                
                current_date += timedelta(days=1)
        
        # Convert dates to Shamsi
        date_from_shamsi = ""
        date_to_shamsi = ""
        if date_from:
            shamsi_from = jdatetime.date.fromgregorian(date=date_from)
            date_from_shamsi = shamsi_from.strftime('%Y/%m/%d')
        if date_to:
            shamsi_to = jdatetime.date.fromgregorian(date=date_to)
            date_to_shamsi = shamsi_to.strftime('%Y/%m/%d')
        
        return {
            'report_type': 'sales_summary',
            'report_title_persian': 'گزارش خلاصه فروش',
            'report_title_english': 'Sales Summary Report',
            'date_from': date_from,
            'date_to': date_to,
            'date_from_shamsi': date_from_shamsi,
            'date_to_shamsi': date_to_shamsi,
            'total_payments': total_payments,
            'total_amount': total_amount,
            'average_payment': average_payment,
            'total_payments_formatted': self.formatter.format_number(
                total_payments, use_persian_digits=True
            ),
            'total_amount_formatted': self.formatter.format_currency(
                total_amount, use_persian_digits=True
            ),
            'average_payment_formatted': self.formatter.format_currency(
                average_payment, use_persian_digits=True
            ),
            'payment_methods': list(payment_methods),
            'daily_breakdown': daily_breakdown,
            'generated_at': timezone.now(),
            'generated_at_shamsi': jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M'),
        }
    
    def generate_gold_price_analysis_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Gold Price Analysis Report (تحلیل قیمت طلا).
        
        Args:
            parameters: Report parameters including date_from, date_to
            
        Returns:
            Gold price analysis report data
        """
        date_from = parameters.get('date_from')
        date_to = parameters.get('date_to', timezone.now().date())
        
        # Note: This is a placeholder implementation since gold price tracking isn't fully implemented
        # In a complete implementation, this would query actual gold price history
        
        # For now, we'll create sample data structure
        current_gold_price = parameters.get('current_gold_price_per_gram', Decimal('1500000'))  # Sample price
        
        # Generate sample price trend data
        price_history = []
        if date_from and date_to:
            current_date = date_from
            base_price = current_gold_price
            
            while current_date <= date_to:
                # Simulate price fluctuation (±5%)
                import random
                fluctuation = Decimal(str(random.uniform(-0.05, 0.05)))
                daily_price = base_price * (1 + fluctuation)
                
                price_history.append({
                    'date': current_date,
                    'date_shamsi': jdatetime.date.fromgregorian(date=current_date).strftime('%Y/%m/%d'),
                    'price_per_gram': daily_price,
                    'price_per_gram_formatted': self.formatter.format_currency(
                        daily_price, use_persian_digits=True
                    ),
                    'change_from_previous': fluctuation * 100,  # Percentage change
                })
                
                current_date += timedelta(days=1)
        
        # Calculate statistics
        if price_history:
            prices = [item['price_per_gram'] for item in price_history]
            min_price = min(prices)
            max_price = max(prices)
            avg_price = sum(prices) / len(prices)
            
            price_volatility = (max_price - min_price) / avg_price * 100
        else:
            min_price = max_price = avg_price = current_gold_price
            price_volatility = Decimal('0.00')
        
        # Convert dates to Shamsi
        date_from_shamsi = ""
        date_to_shamsi = ""
        if date_from:
            shamsi_from = jdatetime.date.fromgregorian(date=date_from)
            date_from_shamsi = shamsi_from.strftime('%Y/%m/%d')
        if date_to:
            shamsi_to = jdatetime.date.fromgregorian(date=date_to)
            date_to_shamsi = shamsi_to.strftime('%Y/%m/%d')
        
        return {
            'report_type': 'gold_price_analysis',
            'report_title_persian': 'گزارش تحلیل قیمت طلا',
            'report_title_english': 'Gold Price Analysis Report',
            'date_from': date_from,
            'date_to': date_to,
            'date_from_shamsi': date_from_shamsi,
            'date_to_shamsi': date_to_shamsi,
            'current_price': current_gold_price,
            'min_price': min_price,
            'max_price': max_price,
            'average_price': avg_price,
            'price_volatility': price_volatility,
            'current_price_formatted': self.formatter.format_currency(
                current_gold_price, use_persian_digits=True
            ),
            'min_price_formatted': self.formatter.format_currency(
                min_price, use_persian_digits=True
            ),
            'max_price_formatted': self.formatter.format_currency(
                max_price, use_persian_digits=True
            ),
            'average_price_formatted': self.formatter.format_currency(
                avg_price, use_persian_digits=True
            ),
            'price_volatility_formatted': self.formatter.format_number(
                price_volatility, use_persian_digits=True
            ) + '%',
            'price_history': price_history,
            'generated_at': timezone.now(),
            'generated_at_shamsi': jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M'),
        }
    
    def generate_installment_summary_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Installment Summary Report (خلاصه اقساط).
        
        Args:
            parameters: Report parameters including date_from, date_to
            
        Returns:
            Installment summary report data
        """
        date_from = parameters.get('date_from')
        date_to = parameters.get('date_to', timezone.now().date())
        
        # Get all gold installment contracts
        contracts_query = GoldInstallmentContract.objects.all()
        
        if date_from:
            contracts_query = contracts_query.filter(contract_date__gte=date_from)
        if date_to:
            contracts_query = contracts_query.filter(contract_date__lte=date_to)
        
        # Group by status
        status_summary = contracts_query.values('status').annotate(
            count=Count('id'),
            total_initial_weight=Sum('initial_gold_weight_grams'),
            total_remaining_weight=Sum('remaining_gold_weight_grams')
        ).order_by('status')
        
        # Calculate totals
        total_contracts = contracts_query.count()
        total_initial_weight = contracts_query.aggregate(
            total=Sum('initial_gold_weight_grams')
        )['total'] or Decimal('0.000')
        total_remaining_weight = contracts_query.aggregate(
            total=Sum('remaining_gold_weight_grams')
        )['total'] or Decimal('0.000')
        
        # Get overdue contracts
        overdue_contracts = []
        current_gold_price = parameters.get('current_gold_price_per_gram', Decimal('1500000'))
        
        for contract in contracts_query.filter(status='active'):
            # Check if contract has overdue payments
            last_payment = contract.payments.order_by('-payment_date').first()
            if last_payment:
                days_since_payment = (timezone.now().date() - last_payment.payment_date).days
                if days_since_payment > 30:  # Consider overdue after 30 days
                    overdue_contracts.append({
                        'contract_id': contract.id,
                        'customer_name': contract.customer.full_persian_name,
                        'remaining_weight': contract.remaining_gold_weight_grams,
                        'remaining_weight_formatted': self.formatter.format_weight(
                            contract.remaining_gold_weight_grams, 'gram', use_persian_digits=True
                        ),
                        'days_overdue': days_since_payment,
                        'estimated_value': contract.remaining_gold_weight_grams * current_gold_price,
                        'estimated_value_formatted': self.formatter.format_currency(
                            contract.remaining_gold_weight_grams * current_gold_price,
                            use_persian_digits=True
                        ),
                    })
        
        # Recent payments
        recent_payments = GoldInstallmentPayment.objects.filter(
            payment_date__gte=date_from if date_from else timezone.now().date() - timedelta(days=30),
            payment_date__lte=date_to
        ).order_by('-payment_date')[:10]
        
        recent_payments_data = []
        for payment in recent_payments:
            recent_payments_data.append({
                'payment_date': payment.payment_date,
                'payment_date_shamsi': jdatetime.date.fromgregorian(
                    date=payment.payment_date
                ).strftime('%Y/%m/%d'),
                'customer_name': payment.contract.customer.full_persian_name,
                'payment_amount': payment.payment_amount_toman,
                'payment_amount_formatted': self.formatter.format_currency(
                    payment.payment_amount_toman, use_persian_digits=True
                ),
                'gold_weight_reduced': payment.gold_weight_reduced_grams,
                'gold_weight_reduced_formatted': self.formatter.format_weight(
                    payment.gold_weight_reduced_grams, 'gram', use_persian_digits=True
                ),
            })
        
        # Convert dates to Shamsi
        date_from_shamsi = ""
        date_to_shamsi = ""
        if date_from:
            shamsi_from = jdatetime.date.fromgregorian(date=date_from)
            date_from_shamsi = shamsi_from.strftime('%Y/%m/%d')
        if date_to:
            shamsi_to = jdatetime.date.fromgregorian(date=date_to)
            date_to_shamsi = shamsi_to.strftime('%Y/%m/%d')
        
        return {
            'report_type': 'installment_summary',
            'report_title_persian': 'گزارش خلاصه اقساط طلا',
            'report_title_english': 'Gold Installment Summary Report',
            'date_from': date_from,
            'date_to': date_to,
            'date_from_shamsi': date_from_shamsi,
            'date_to_shamsi': date_to_shamsi,
            'total_contracts': total_contracts,
            'total_initial_weight': total_initial_weight,
            'total_remaining_weight': total_remaining_weight,
            'total_contracts_formatted': self.formatter.format_number(
                total_contracts, use_persian_digits=True
            ),
            'total_initial_weight_formatted': self.formatter.format_weight(
                total_initial_weight, 'gram', use_persian_digits=True
            ),
            'total_remaining_weight_formatted': self.formatter.format_weight(
                total_remaining_weight, 'gram', use_persian_digits=True
            ),
            'status_summary': list(status_summary),
            'overdue_contracts': overdue_contracts,
            'overdue_count': len(overdue_contracts),
            'recent_payments': recent_payments_data,
            'generated_at': timezone.now(),
            'generated_at_shamsi': jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M'),
        }


class ReportValidationService:
    """
    Service for validating report parameters and data.
    """
    
    @staticmethod
    def validate_date_range(date_from: Optional[date], date_to: Optional[date]) -> Dict[str, Any]:
        """
        Validate date range parameters.
        
        Args:
            date_from: Start date
            date_to: End date
            
        Returns:
            Validation result dictionary
        """
        errors = []
        warnings = []
        
        if date_from and date_to:
            if date_from > date_to:
                errors.append("تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد")
            
            # Check if date range is too large
            date_diff = (date_to - date_from).days
            if date_diff > 365:
                warnings.append("بازه زمانی انتخابی بیش از یک سال است و ممکن است تولید گزارش زمان‌بر باشد")
            
            # Check if dates are in the future
            today = timezone.now().date()
            if date_from > today:
                warnings.append("تاریخ شروع در آینده است")
            if date_to > today:
                warnings.append("تاریخ پایان در آینده است")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    @staticmethod
    def validate_report_parameters(report_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate report-specific parameters.
        
        Args:
            report_type: Type of report
            parameters: Report parameters
            
        Returns:
            Validation result dictionary
        """
        errors = []
        warnings = []
        
        # Common validations
        date_validation = ReportValidationService.validate_date_range(
            parameters.get('date_from'),
            parameters.get('date_to')
        )
        errors.extend(date_validation['errors'])
        warnings.extend(date_validation['warnings'])
        
        # Report-specific validations
        if report_type == 'customer_aging':
            aging_periods = parameters.get('aging_periods', [])
            if not aging_periods:
                errors.append("دوره‌های سنی باید مشخص شوند")
            elif not all(isinstance(p, int) and p > 0 for p in aging_periods):
                errors.append("دوره‌های سنی باید اعداد مثبت باشند")
        
        elif report_type == 'inventory_valuation':
            gold_price = parameters.get('gold_price_per_gram')
            if gold_price is not None and gold_price <= 0:
                errors.append("قیمت طلا باید مثبت باشد")
        
        elif report_type in ['trial_balance', 'profit_loss', 'balance_sheet']:
            # Check if accounting system is set up
            from zargar.accounting.models import ChartOfAccounts
            if not ChartOfAccounts.objects.exists():
                errors.append("سیستم حسابداری تنظیم نشده است")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }


class ReportCacheService:
    """
    Service for caching report data to improve performance.
    """
    
    def __init__(self):
        """Initialize cache service."""
        from django.core.cache import cache
        self.cache = cache
        self.cache_timeout = 3600  # 1 hour default
    
    def get_cache_key(self, template_id: int, parameters: Dict[str, Any]) -> str:
        """
        Generate cache key for report.
        
        Args:
            template_id: Report template ID
            parameters: Report parameters
            
        Returns:
            Cache key string
        """
        import hashlib
        import json
        
        # Create a hash of parameters for cache key
        params_str = json.dumps(parameters, sort_keys=True, default=str)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()
        
        return f"report_cache_{template_id}_{params_hash}"
    
    def get_cached_report(self, template_id: int, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get cached report data.
        
        Args:
            template_id: Report template ID
            parameters: Report parameters
            
        Returns:
            Cached report data or None
        """
        cache_key = self.get_cache_key(template_id, parameters)
        return self.cache.get(cache_key)
    
    def cache_report(self, template_id: int, parameters: Dict[str, Any], report_data: Dict[str, Any], timeout: Optional[int] = None):
        """
        Cache report data.
        
        Args:
            template_id: Report template ID
            parameters: Report parameters
            report_data: Report data to cache
            timeout: Cache timeout in seconds
        """
        cache_key = self.get_cache_key(template_id, parameters)
        cache_timeout = timeout or self.cache_timeout
        
        self.cache.set(cache_key, report_data, cache_timeout)
    
    def invalidate_report_cache(self, template_id: int):
        """
        Invalidate all cached reports for a template.
        
        Args:
            template_id: Report template ID
        """
        # Note: This is a simplified implementation
        # In production, you might want to use cache versioning or tags
        cache_pattern = f"report_cache_{template_id}_*"
        
        # Django's cache doesn't support pattern deletion by default
        # This would need to be implemented based on your cache backend
        passayment_methods = payments_query.values('payment_method').annotate(
            count=Count('id'),
            total_amount=Sum('payment_amount_toman')
        ).order_by('-total_amount')
        
        # Group by month for trend analysis
        monthly_data = []
        if date_from and date_to:
            current_date = date_from.replace(day=1)  # Start of month
            while current_date <= date_to:
                next_month = current_date.replace(day=28) + timedelta(days=4)
                next_month = next_month.replace(day=1)
                
                month_payments = payments_query.filter(
                    payment_date__gte=current_date,
                    payment_date__lt=next_month
                )
                
                month_total = month_payments.aggregate(
                    total=Sum('payment_amount_toman')
                )['total'] or Decimal('0.00')
                
                # Convert to Shamsi month
                shamsi_date = jdatetime.date.fromgregorian(date=current_date)
                
                monthly_data.append({
                    'month': current_date,
                    'month_shamsi': shamsi_date.strftime('%Y/%m'),
                    'month_name_persian': shamsi_date.strftime('%B %Y'),
                    'payment_count': month_payments.count(),
                    'total_amount': month_total,
                    'total_amount_formatted': self.formatter.format_currency(
                        month_total, use_persian_digits=True
                    ),
                })
                
                current_date = next_month
        
        # Convert dates to Shamsi
        date_from_shamsi = ""
        date_to_shamsi = ""
        if date_from:
            shamsi_from = jdatetime.date.fromgregorian(date=date_from)
            date_from_shamsi = shamsi_from.strftime('%Y/%m/%d')
        if date_to:
            shamsi_to = jdatetime.date.fromgregorian(date=date_to)
            date_to_shamsi = shamsi_to.strftime('%Y/%m/%d')
        
        return {
            'report_type': 'sales_summary',
            'report_title_persian': 'گزارش خلاصه فروش',
            'report_title_english': 'Sales Summary Report',
            'date_from': date_from,
            'date_to': date_to,
            'date_from_shamsi': date_from_shamsi,
            'date_to_shamsi': date_to_shamsi,
            'total_transactions': total_payments,
            'total_amount': total_amount,
            'average_transaction': average_payment,
            'total_amount_formatted': self.formatter.format_currency(
                total_amount, use_persian_digits=True
            ),
            'average_transaction_formatted': self.formatter.format_currency(
                average_payment, use_persian_digits=True
            ),
            'payment_methods': [
                {
                    'method': method['payment_method'],
                    'method_display': dict(GoldInstallmentPayment.PAYMENT_METHOD_CHOICES).get(
                        method['payment_method'], method['payment_method']
                    ),
                    'count': method['count'],
                    'total_amount': method['total_amount'],
                    'total_amount_formatted': self.formatter.format_currency(
                        method['total_amount'], use_persian_digits=True
                    ),
                    'percentage': (method['total_amount'] / total_amount * 100) if total_amount > 0 else 0,
                }
                for method in payment_methods
            ],
            'monthly_data': monthly_data,
            'generated_at': timezone.now(),
            'generated_at_shamsi': jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M'),
        }
    
    def generate_gold_price_analysis_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Gold Price Analysis Report (تحلیل قیمت طلا).
        
        Args:
            parameters: Report parameters including date_from, date_to
            
        Returns:
            Gold price analysis report data
        """
        date_from = parameters.get('date_from')
        date_to = parameters.get('date_to', timezone.now().date())
        
        # Get gold price data from installment payments
        payments_query = GoldInstallmentPayment.objects.filter(
            payment_date__lte=date_to
        ).order_by('payment_date')
        
        if date_from:
            payments_query = payments_query.filter(payment_date__gte=date_from)
        
        # Calculate price statistics
        price_data = payments_query.values_list(
            'payment_date', 'gold_price_per_gram_at_payment'
        )
        
        if not price_data:
            return {
                'report_type': 'gold_price_analysis',
                'report_title_persian': 'گزارش تحلیل قیمت طلا',
                'report_title_english': 'Gold Price Analysis Report',
                'error': 'No gold price data available for the selected period',
            }
        
        prices = [price[1] for price in price_data]
        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)
        
        # Calculate price trend
        first_price = prices[0]
        last_price = prices[-1]
        price_change = last_price - first_price
        price_change_percentage = (price_change / first_price * 100) if first_price > 0 else 0
        
        # Group by date for daily analysis
        daily_prices = {}
        for payment_date, price in price_data:
            if payment_date not in daily_prices:
                daily_prices[payment_date] = []
            daily_prices[payment_date].append(price)
        
        # Calculate daily averages
        daily_analysis = []
        for date, day_prices in daily_prices.items():
            daily_avg = sum(day_prices) / len(day_prices)
            shamsi_date = jdatetime.date.fromgregorian(date=date)
            
            daily_analysis.append({
                'date': date,
                'date_shamsi': shamsi_date.strftime('%Y/%m/%d'),
                'average_price': daily_avg,
                'min_price': min(day_prices),
                'max_price': max(day_prices),
                'transaction_count': len(day_prices),
                'average_price_formatted': self.formatter.format_currency(
                    daily_avg, use_persian_digits=True
                ),
                'min_price_formatted': self.formatter.format_currency(
                    min(day_prices), use_persian_digits=True
                ),
                'max_price_formatted': self.formatter.format_currency(
                    max(day_prices), use_persian_digits=True
                ),
            })
        
        # Convert dates to Shamsi
        date_from_shamsi = ""
        date_to_shamsi = ""
        if date_from:
            shamsi_from = jdatetime.date.fromgregorian(date=date_from)
            date_from_shamsi = shamsi_from.strftime('%Y/%m/%d')
        if date_to:
            shamsi_to = jdatetime.date.fromgregorian(date=date_to)
            date_to_shamsi = shamsi_to.strftime('%Y/%m/%d')
        
        return {
            'report_type': 'gold_price_analysis',
            'report_title_persian': 'گزارش تحلیل قیمت طلا',
            'report_title_english': 'Gold Price Analysis Report',
            'date_from': date_from,
            'date_to': date_to,
            'date_from_shamsi': date_from_shamsi,
            'date_to_shamsi': date_to_shamsi,
            'min_price': min_price,
            'max_price': max_price,
            'average_price': avg_price,
            'first_price': first_price,
            'last_price': last_price,
            'price_change': price_change,
            'price_change_percentage': price_change_percentage,
            'min_price_formatted': self.formatter.format_currency(
                min_price, use_persian_digits=True
            ),
            'max_price_formatted': self.formatter.format_currency(
                max_price, use_persian_digits=True
            ),
            'average_price_formatted': self.formatter.format_currency(
                avg_price, use_persian_digits=True
            ),
            'price_change_formatted': self.formatter.format_currency(
                price_change, use_persian_digits=True
            ),
            'price_change_percentage_formatted': self.formatter.format_percentage(
                price_change_percentage, use_persian_digits=True
            ),
            'is_price_increasing': price_change > 0,
            'total_transactions': len(prices),
            'daily_analysis': daily_analysis,
            'generated_at': timezone.now(),
            'generated_at_shamsi': jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M'),
        }
    
    def generate_installment_summary_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Installment Summary Report (خلاصه اقساط).
        
        Args:
            parameters: Report parameters including date_from, date_to, status_filter
            
        Returns:
            Installment summary report data
        """
        date_from = parameters.get('date_from')
        date_to = parameters.get('date_to', timezone.now().date())
        status_filter = parameters.get('status_filter', 'all')
        
        # Build query for contracts
        contracts_query = GoldInstallmentContract.objects.all()
        
        if status_filter != 'all':
            contracts_query = contracts_query.filter(status=status_filter)
        
        if date_from:
            contracts_query = contracts_query.filter(contract_date__gte=date_from)
        if date_to:
            contracts_query = contracts_query.filter(contract_date__lte=date_to)
        
        # Calculate summary statistics
        total_contracts = contracts_query.count()
        
        # Group by status
        status_summary = contracts_query.values('status').annotate(
            count=Count('id'),
            total_initial_weight=Sum('initial_gold_weight_grams'),
            total_remaining_weight=Sum('remaining_gold_weight_grams'),
            total_payments_received=Sum('total_payments_received')
        ).order_by('status')
        
        # Calculate completion statistics
        completed_contracts = contracts_query.filter(status='completed').count()
        active_contracts = contracts_query.filter(status='active').count()
        defaulted_contracts = contracts_query.filter(status='defaulted').count()
        
        completion_rate = (completed_contracts / total_contracts * 100) if total_contracts > 0 else 0
        
        # Get overdue contracts
        overdue_contracts = []
        for contract in contracts_query.filter(status='active'):
            if contract.is_overdue:
                overdue_contracts.append({
                    'contract_number': contract.contract_number,
                    'customer_name': str(contract.customer),
                    'remaining_weight': contract.remaining_gold_weight_grams,
                    'remaining_weight_formatted': self.formatter.format_weight(
                        contract.remaining_gold_weight_grams, 'gram', use_persian_digits=True
                    ),
                    'contract_date': contract.contract_date,
                    'contract_date_shamsi': contract.contract_date_shamsi,
                })
        
        # Calculate totals
        total_initial_weight = contracts_query.aggregate(
            total=Sum('initial_gold_weight_grams')
        )['total'] or Decimal('0.000')
        
        total_remaining_weight = contracts_query.aggregate(
            total=Sum('remaining_gold_weight_grams')
        )['total'] or Decimal('0.000')
        
        total_payments_received = contracts_query.aggregate(
            total=Sum('total_payments_received')
        )['total'] or Decimal('0.00')
        
        # Convert dates to Shamsi
        date_from_shamsi = ""
        date_to_shamsi = ""
        if date_from:
            shamsi_from = jdatetime.date.fromgregorian(date=date_from)
            date_from_shamsi = shamsi_from.strftime('%Y/%m/%d')
        if date_to:
            shamsi_to = jdatetime.date.fromgregorian(date=date_to)
            date_to_shamsi = shamsi_to.strftime('%Y/%m/%d')
        
        return {
            'report_type': 'installment_summary',
            'report_title_persian': 'گزارش خلاصه قراردادهای اقساط طلا',
            'report_title_english': 'Gold Installment Summary Report',
            'date_from': date_from,
            'date_to': date_to,
            'date_from_shamsi': date_from_shamsi,
            'date_to_shamsi': date_to_shamsi,
            'status_filter': status_filter,
            'total_contracts': total_contracts,
            'completed_contracts': completed_contracts,
            'active_contracts': active_contracts,
            'defaulted_contracts': defaulted_contracts,
            'completion_rate': completion_rate,
            'completion_rate_formatted': self.formatter.format_percentage(
                completion_rate, use_persian_digits=True
            ),
            'total_initial_weight': total_initial_weight,
            'total_remaining_weight': total_remaining_weight,
            'total_payments_received': total_payments_received,
            'total_initial_weight_formatted': self.formatter.format_weight(
                total_initial_weight, 'gram', use_persian_digits=True
            ),
            'total_remaining_weight_formatted': self.formatter.format_weight(
                total_remaining_weight, 'gram', use_persian_digits=True
            ),
            'total_payments_received_formatted': self.formatter.format_currency(
                total_payments_received, use_persian_digits=True
            ),
            'status_summary': [
                {
                    'status': item['status'],
                    'status_display': dict(GoldInstallmentContract.STATUS_CHOICES).get(
                        item['status'], item['status']
                    ),
                    'count': item['count'],
                    'total_initial_weight': item['total_initial_weight'] or Decimal('0.000'),
                    'total_remaining_weight': item['total_remaining_weight'] or Decimal('0.000'),
                    'total_payments_received': item['total_payments_received'] or Decimal('0.00'),
                    'total_initial_weight_formatted': self.formatter.format_weight(
                        item['total_initial_weight'] or Decimal('0.000'), 'gram', use_persian_digits=True
                    ),
                    'total_remaining_weight_formatted': self.formatter.format_weight(
                        item['total_remaining_weight'] or Decimal('0.000'), 'gram', use_persian_digits=True
                    ),
                    'total_payments_received_formatted': self.formatter.format_currency(
                        item['total_payments_received'] or Decimal('0.00'), use_persian_digits=True
                    ),
                }
                for item in status_summary
            ],
            'overdue_contracts': overdue_contracts,
            'overdue_contracts_count': len(overdue_contracts),
            'generated_at': timezone.now(),
            'generated_at_shamsi': jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M'),
        }