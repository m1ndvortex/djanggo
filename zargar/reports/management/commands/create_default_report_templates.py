"""
Management command to create default report templates.
"""

from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _
from zargar.reports.models import ReportTemplate
import json


class Command(BaseCommand):
    """
    Create default system report templates for all tenants.
    """
    help = 'Create default system report templates'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing templates',
        )
    
    def handle(self, *args, **options):
        """Create default report templates."""
        
        templates_data = [
            {
                'name': 'Standard Trial Balance',
                'name_persian': 'ترازنامه آزمایشی استاندارد',
                'description': 'Standard trial balance report with Persian formatting',
                'report_type': 'trial_balance',
                'default_format': 'pdf',
                'default_period': 'monthly',
                'parameters': {
                    'include_zero_balances': False,
                    'group_by_category': True,
                    'show_account_codes': True,
                },
                'include_charts': True,
                'include_summary': True,
                'show_comparisons': False,
                'is_system_template': True,
            },
            {
                'name': 'Monthly Profit & Loss',
                'name_persian': 'صورت سود و زیان ماهانه',
                'description': 'Monthly profit and loss statement with Persian formatting',
                'report_type': 'profit_loss',
                'default_format': 'pdf',
                'default_period': 'monthly',
                'parameters': {
                    'include_budget_comparison': False,
                    'show_percentages': True,
                    'group_by_category': True,
                },
                'include_charts': True,
                'include_summary': True,
                'show_comparisons': True,
                'is_system_template': True,
            },
            {
                'name': 'Balance Sheet',
                'name_persian': 'ترازنامه',
                'description': 'Balance sheet with financial ratios and Persian formatting',
                'report_type': 'balance_sheet',
                'default_format': 'pdf',
                'default_period': 'monthly',
                'parameters': {
                    'show_previous_period': True,
                    'include_ratios': True,
                    'group_by_category': True,
                },
                'include_charts': True,
                'include_summary': True,
                'show_comparisons': True,
                'is_system_template': True,
            },
            {
                'name': 'Inventory Valuation Report',
                'name_persian': 'گزارش ارزش‌گذاری موجودی',
                'description': 'Comprehensive inventory valuation with current market prices',
                'report_type': 'inventory_valuation',
                'default_format': 'pdf',
                'default_period': 'monthly',
                'parameters': {
                    'valuation_method': 'current_market',
                    'include_photos': False,
                    'group_by_category': True,
                },
                'include_charts': True,
                'include_summary': True,
                'show_comparisons': False,
                'is_system_template': True,
            },
            {
                'name': 'Customer Aging Report',
                'name_persian': 'گزارش سن مطالبات مشتریان',
                'description': 'Customer aging analysis with payment history',
                'report_type': 'customer_aging',
                'default_format': 'pdf',
                'default_period': 'monthly',
                'parameters': {
                    'aging_periods': [30, 60, 90, 120],
                    'include_contact_info': True,
                    'show_payment_history': False,
                },
                'include_charts': True,
                'include_summary': True,
                'show_comparisons': False,
                'is_system_template': True,
            },
            {
                'name': 'Sales Summary Report',
                'name_persian': 'گزارش خلاصه فروش',
                'description': 'Daily, weekly, and monthly sales summary',
                'report_type': 'sales_summary',
                'default_format': 'pdf',
                'default_period': 'monthly',
                'parameters': {
                    'include_trends': True,
                    'group_by_category': True,
                    'show_top_items': True,
                },
                'include_charts': True,
                'include_summary': True,
                'show_comparisons': True,
                'is_system_template': True,
            },
            {
                'name': 'Gold Price Analysis',
                'name_persian': 'تحلیل قیمت طلا',
                'description': 'Gold price trends and market analysis',
                'report_type': 'gold_price_analysis',
                'default_format': 'pdf',
                'default_period': 'monthly',
                'parameters': {
                    'include_trends': True,
                    'show_forecasts': False,
                    'compare_periods': True,
                },
                'include_charts': True,
                'include_summary': True,
                'show_comparisons': True,
                'is_system_template': True,
            },
            {
                'name': 'Installment Summary Report',
                'name_persian': 'گزارش خلاصه اقساط',
                'description': 'Gold installment contracts and payment tracking',
                'report_type': 'installment_summary',
                'default_format': 'pdf',
                'default_period': 'monthly',
                'parameters': {
                    'include_overdue': True,
                    'show_payment_history': True,
                    'group_by_status': True,
                },
                'include_charts': True,
                'include_summary': True,
                'show_comparisons': False,
                'is_system_template': True,
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for template_data in templates_data:
            # Check if template already exists
            existing_template = ReportTemplate.objects.filter(
                name=template_data['name'],
                is_system_template=True
            ).first()
            
            if existing_template:
                if options['overwrite']:
                    # Update existing template
                    for key, value in template_data.items():
                        setattr(existing_template, key, value)
                    existing_template.save()
                    updated_count += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Updated template: {template_data["name_persian"]}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Template already exists: {template_data["name_persian"]} (use --overwrite to update)'
                        )
                    )
            else:
                # Create new template
                ReportTemplate.objects.create(**template_data)
                created_count += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created template: {template_data["name_persian"]}'
                    )
                )
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary: Created {created_count} templates, Updated {updated_count} templates'
            )
        )
        
        if created_count == 0 and updated_count == 0:
            self.stdout.write(
                self.style.WARNING(
                    'No templates were created or updated. Use --overwrite to update existing templates.'
                )
            )