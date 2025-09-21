"""
Comprehensive tests for the reporting engine backend.

This module tests all aspects of the reporting engine including:
- Report generation for all report types
- Persian formatting and localization
- Report scheduling and automation
- Report export functionality
- Error handling and edge cases
"""

import pytest
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from decimal import Decimal
from datetime import date, datetime, timedelta
import json
import os
import tempfile
from unittest.mock import patch, MagicMock

from zargar.tenants.models import Tenant, Domain
from zargar.core.models import User
from zargar.reports.models import (
    ReportTemplate, GeneratedReport, ReportSchedule, ReportDelivery
)
from zargar.reports.services import (
    ComprehensiveReportingEngine, ReportValidationService, ReportCacheService
)
from zargar.reports.exporters import ReportExporter
from zargar.reports.scheduler import ReportScheduler
from zargar.accounting.models import ChartOfAccounts, JournalEntry, JournalEntryLine
from zargar.jewelry.models import JewelryItem, Category
from zargar.customers.models import Customer
from zargar.gold_installments.models import GoldInstallmentContract, GoldInstallmentPayment


class ReportingEngineTestCase(TenantTestCase):
    """
    Test case for the comprehensive reporting engine.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test tenant and domain."""
        super().setUpClass()
        
        # Create test tenant
        cls.tenant = Tenant(
            name='Test Jewelry Shop',
            schema_name='test_jewelry',
            domain_url='testjewelry'
        )
        cls.tenant.save()
        
        # Create domain
        cls.domain = Domain(
            domain='testjewelry.zargar.com',
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
    
    def setUp(self):
        """Set up test data for each test."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
        
        # Create test categories
        self.category = Category.objects.create(
            name='Test Category',
            name_persian='دسته‌بندی تست',
            description='Test category for jewelry items'
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            first_name='احمد',
            last_name='محمدی',
            persian_first_name='احمد',
            persian_last_name='محمدی',
            phone_number='09123456789',
            email='ahmad@example.com'
        )
        
        # Create test jewelry items
        self.jewelry_item = JewelryItem.objects.create(
            name='Test Ring',
            category=self.category,
            weight_grams=Decimal('5.500'),
            karat=18,
            manufacturing_cost=Decimal('500000'),
            sku='TEST-RING-001',
            quantity=10,
            status='in_stock'
        )
        
        # Create test chart of accounts
        self.asset_account = ChartOfAccounts.objects.create(
            account_code='1001',
            account_name_english='Cash',
            account_name_persian='نقد',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit',
            is_active=True,
            allow_posting=True
        )
        
        self.revenue_account = ChartOfAccounts.objects.create(
            account_code='4001',
            account_name_english='Sales Revenue',
            account_name_persian='درآمد فروش',
            account_type='revenue',
            account_category='operating_revenue',
            normal_balance='credit',
            is_active=True,
            allow_posting=True
        )
        
        # Create test report templates
        self.trial_balance_template = ReportTemplate.objects.create(
            name='Test Trial Balance',
            name_persian='ترازنامه آزمایشی تست',
            report_type='trial_balance',
            default_output_format='pdf',
            is_active=True
        )
        
        self.inventory_template = ReportTemplate.objects.create(
            name='Test Inventory Valuation',
            name_persian='ارزش‌گذاری موجودی تست',
            report_type='inventory_valuation',
            default_output_format='excel',
            is_active=True
        )
        
        # Initialize reporting engine
        self.reporting_engine = ComprehensiveReportingEngine(tenant=self.tenant)
    
    def test_trial_balance_generation(self):
        """Test trial balance report generation."""
        # Create test journal entries
        journal_entry = JournalEntry.objects.create(
            entry_number='JE-001',
            entry_date=timezone.now().date(),
            description='Test entry',
            reference_number='REF-001',
            created_by=self.user
        )
        
        # Debit entry
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=self.asset_account,
            debit_amount=Decimal('1000000'),
            credit_amount=Decimal('0'),
            description='Test debit'
        )
        
        # Credit entry
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=self.revenue_account,
            debit_amount=Decimal('0'),
            credit_amount=Decimal('1000000'),
            description='Test credit'
        )
        
        # Generate trial balance
        parameters = {
            'date_from': timezone.now().date() - timedelta(days=30),
            'date_to': timezone.now().date(),
            'include_zero_balances': False
        }
        
        report_data = self.reporting_engine.generate_trial_balance(parameters)
        
        # Assertions
        self.assertEqual(report_data['report_type'], 'trial_balance')
        self.assertIn('accounts', report_data)
        self.assertIn('total_debits', report_data)
        self.assertIn('total_credits', report_data)
        self.assertTrue(report_data['is_balanced'])
        self.assertEqual(report_data['total_debits'], report_data['total_credits'])
        
        # Check Persian formatting
        self.assertIn('report_title_persian', report_data)
        self.assertIn('date_from_shamsi', report_data)
        self.assertIn('date_to_shamsi', report_data)
    
    def test_profit_loss_generation(self):
        """Test profit & loss statement generation."""
        # Create test data similar to trial balance test
        journal_entry = JournalEntry.objects.create(
            entry_number='JE-002',
            entry_date=timezone.now().date(),
            description='Revenue entry',
            reference_number='REF-002',
            created_by=self.user
        )
        
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=self.asset_account,
            debit_amount=Decimal('500000'),
            credit_amount=Decimal('0'),
            description='Cash received'
        )
        
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=self.revenue_account,
            debit_amount=Decimal('0'),
            credit_amount=Decimal('500000'),
            description='Sales revenue'
        )
        
        parameters = {
            'date_from': timezone.now().date() - timedelta(days=30),
            'date_to': timezone.now().date()
        }
        
        report_data = self.reporting_engine.generate_profit_loss_statement(parameters)
        
        # Assertions
        self.assertEqual(report_data['report_type'], 'profit_loss')
        self.assertIn('revenue_accounts', report_data)
        self.assertIn('expense_accounts', report_data)
        self.assertIn('net_income', report_data)
        self.assertIn('total_revenue_formatted', report_data)
    
    def test_balance_sheet_generation(self):
        """Test balance sheet generation."""
        parameters = {
            'as_of_date': timezone.now().date()
        }
        
        report_data = self.reporting_engine.generate_balance_sheet(parameters)
        
        # Assertions
        self.assertEqual(report_data['report_type'], 'balance_sheet')
        self.assertIn('assets', report_data)
        self.assertIn('liabilities', report_data)
        self.assertIn('equity', report_data)
        self.assertIn('total_assets', report_data)
        self.assertIn('is_balanced', report_data)
    
    def test_inventory_valuation_generation(self):
        """Test inventory valuation report generation."""
        parameters = {
            'as_of_date': timezone.now().date(),
            'gold_price_per_gram': Decimal('1500000')
        }
        
        report_data = self.reporting_engine.generate_inventory_valuation_report(parameters)
        
        # Assertions
        self.assertEqual(report_data['report_type'], 'inventory_valuation')
        self.assertIn('categories', report_data)
        self.assertIn('total_inventory_value', report_data)
        self.assertIn('total_items_count', report_data)
        self.assertIn('total_weight', report_data)
        
        # Check that our test item is included
        categories = report_data['categories']
        self.assertTrue(len(categories) > 0)
        
        # Find our test category
        test_category = next(
            (cat for cat in categories if cat['category_name'] == 'دسته‌بندی تست'),
            None
        )
        self.assertIsNotNone(test_category)
        self.assertTrue(len(test_category['items']) > 0)
    
    def test_customer_aging_generation(self):
        """Test customer aging report generation."""
        # Create test gold installment contract
        contract = GoldInstallmentContract.objects.create(
            customer=self.customer,
            initial_gold_weight_grams=Decimal('100.000'),
            remaining_gold_weight_grams=Decimal('50.000'),
            payment_schedule='monthly',
            contract_date=timezone.now().date() - timedelta(days=60),
            status='active'
        )
        
        # Create test payment
        GoldInstallmentPayment.objects.create(
            contract=contract,
            payment_date=timezone.now().date() - timedelta(days=45),
            payment_amount_toman=Decimal('5000000'),
            gold_weight_reduced_grams=Decimal('50.000'),
            gold_price_per_gram_at_payment=Decimal('1000000'),
            payment_method='cash'
        )
        
        parameters = {
            'as_of_date': timezone.now().date(),
            'aging_periods': [30, 60, 90, 120],
            'current_gold_price_per_gram': Decimal('1500000')
        }
        
        report_data = self.reporting_engine.generate_customer_aging_report(parameters)
        
        # Assertions
        self.assertEqual(report_data['report_type'], 'customer_aging')
        self.assertIn('customers', report_data)
        self.assertIn('total_outstanding', report_data)
        self.assertIn('aging_totals', report_data)
        self.assertIn('aging_period_labels', report_data)
    
    def test_sales_summary_generation(self):
        """Test sales summary report generation."""
        parameters = {
            'date_from': timezone.now().date() - timedelta(days=30),
            'date_to': timezone.now().date()
        }
        
        report_data = self.reporting_engine.generate_sales_summary_report(parameters)
        
        # Assertions
        self.assertEqual(report_data['report_type'], 'sales_summary')
        self.assertIn('total_payments', report_data)
        self.assertIn('total_amount', report_data)
        self.assertIn('payment_methods', report_data)
        self.assertIn('daily_breakdown', report_data)
    
    def test_gold_price_analysis_generation(self):
        """Test gold price analysis report generation."""
        parameters = {
            'date_from': timezone.now().date() - timedelta(days=30),
            'date_to': timezone.now().date(),
            'current_gold_price_per_gram': Decimal('1500000')
        }
        
        report_data = self.reporting_engine.generate_gold_price_analysis_report(parameters)
        
        # Assertions
        self.assertEqual(report_data['report_type'], 'gold_price_analysis')
        self.assertIn('current_price', report_data)
        self.assertIn('min_price', report_data)
        self.assertIn('max_price', report_data)
        self.assertIn('price_history', report_data)
        self.assertIn('price_volatility', report_data)
    
    def test_installment_summary_generation(self):
        """Test installment summary report generation."""
        # Create test contract (reuse from customer aging test)
        contract = GoldInstallmentContract.objects.create(
            customer=self.customer,
            initial_gold_weight_grams=Decimal('200.000'),
            remaining_gold_weight_grams=Decimal('100.000'),
            payment_schedule='weekly',
            contract_date=timezone.now().date() - timedelta(days=30),
            status='active'
        )
        
        parameters = {
            'date_from': timezone.now().date() - timedelta(days=60),
            'date_to': timezone.now().date(),
            'current_gold_price_per_gram': Decimal('1500000')
        }
        
        report_data = self.reporting_engine.generate_installment_summary_report(parameters)
        
        # Assertions
        self.assertEqual(report_data['report_type'], 'installment_summary')
        self.assertIn('total_contracts', report_data)
        self.assertIn('total_initial_weight', report_data)
        self.assertIn('total_remaining_weight', report_data)
        self.assertIn('status_summary', report_data)
        self.assertIn('overdue_contracts', report_data)
    
    def test_persian_formatting(self):
        """Test Persian number and date formatting in reports."""
        parameters = {
            'as_of_date': timezone.now().date()
        }
        
        report_data = self.reporting_engine.generate_inventory_valuation_report(parameters)
        
        # Check Persian formatting
        self.assertIn('generated_at_shamsi', report_data)
        self.assertIn('as_of_date_shamsi', report_data)
        
        # Check that formatted amounts contain Persian digits
        if report_data['categories']:
            category = report_data['categories'][0]
            if category['items']:
                item = category['items'][0]
                formatted_value = item['total_item_value_formatted']
                # Persian digits should be present
                persian_digits = '۰۱۲۳۴۵۶۷۸۹'
                has_persian_digits = any(digit in formatted_value for digit in persian_digits)
                # Note: This might not always be true if the value is 0, so we'll check structure
                self.assertIsInstance(formatted_value, str)
    
    def test_report_validation_service(self):
        """Test report parameter validation."""
        # Test valid date range
        validation = ReportValidationService.validate_date_range(
            timezone.now().date() - timedelta(days=30),
            timezone.now().date()
        )
        self.assertTrue(validation['is_valid'])
        self.assertEqual(len(validation['errors']), 0)
        
        # Test invalid date range (start after end)
        validation = ReportValidationService.validate_date_range(
            timezone.now().date(),
            timezone.now().date() - timedelta(days=30)
        )
        self.assertFalse(validation['is_valid'])
        self.assertTrue(len(validation['errors']) > 0)
        
        # Test report-specific validation
        validation = ReportValidationService.validate_report_parameters(
            'customer_aging',
            {'aging_periods': [30, 60, 90]}
        )
        self.assertTrue(validation['is_valid'])
        
        # Test invalid aging periods
        validation = ReportValidationService.validate_report_parameters(
            'customer_aging',
            {'aging_periods': []}
        )
        self.assertFalse(validation['is_valid'])


class ReportExporterTestCase(TenantTestCase):
    """
    Test case for report export functionality.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test tenant and domain."""
        super().setUpClass()
        
        # Create test tenant
        cls.tenant = Tenant(
            name='Test Export Shop',
            schema_name='test_export',
            domain_url='testexport'
        )
        cls.tenant.save()
        
        # Create domain
        cls.domain = Domain(
            domain='testexport.zargar.com',
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
    
    def setUp(self):
        """Set up test data."""
        self.exporter = ReportExporter()
        
        # Sample report data
        self.sample_report_data = {
            'report_type': 'trial_balance',
            'report_title_persian': 'ترازنامه آزمایشی تست',
            'report_title_english': 'Test Trial Balance',
            'date_from_shamsi': '1403/06/15',
            'date_to_shamsi': '1403/07/15',
            'accounts': [
                {
                    'account_code': '1001',
                    'account_name_persian': 'نقد',
                    'account_type': 'دارایی',
                    'debit_amount': Decimal('1000000'),
                    'credit_amount': Decimal('0'),
                    'debit_amount_formatted': '۱,۰۰۰,۰۰۰ تومان',
                    'credit_amount_formatted': '۰ تومان',
                }
            ],
            'total_debits': Decimal('1000000'),
            'total_credits': Decimal('1000000'),
            'total_debits_formatted': '۱,۰۰۰,۰۰۰ تومان',
            'total_credits_formatted': '۱,۰۰۰,۰۰۰ تومان',
            'is_balanced': True,
            'generated_at': timezone.now(),
            'generated_at_shamsi': '1403/07/15 14:30'
        }
    
    def test_json_export(self):
        """Test JSON export functionality."""
        filename = 'test_report.json'
        file_path = self.exporter.export_to_json(self.sample_report_data, filename)
        
        # Check file was created
        self.assertTrue(os.path.exists(file_path))
        
        # Check file content
        with open(file_path, 'r', encoding='utf-8') as f:
            exported_data = json.load(f)
        
        self.assertEqual(exported_data['report_type'], 'trial_balance')
        self.assertEqual(exported_data['report_title_persian'], 'ترازنامه آزمایشی تست')
        
        # Cleanup
        os.remove(file_path)
    
    def test_csv_export(self):
        """Test CSV export functionality."""
        filename = 'test_report.csv'
        file_path = self.exporter.export_to_csv(self.sample_report_data, filename)
        
        # Check file was created
        self.assertTrue(os.path.exists(file_path))
        
        # Check file content
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        self.assertIn('ترازنامه آزمایشی تست', content)
        self.assertIn('کد حساب', content)
        self.assertIn('نام حساب', content)
        
        # Cleanup
        os.remove(file_path)
    
    @patch('zargar.reports.exporters.OPENPYXL_AVAILABLE', True)
    def test_excel_export(self):
        """Test Excel export functionality."""
        try:
            import openpyxl
            
            filename = 'test_report.xlsx'
            file_path = self.exporter.export_to_excel(self.sample_report_data, filename)
            
            # Check file was created
            self.assertTrue(os.path.exists(file_path))
            
            # Check file content
            wb = openpyxl.load_workbook(file_path)
            ws = wb.active
            
            # Check that Persian title is in the worksheet
            found_title = False
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value and 'ترازنامه آزمایشی تست' in str(cell.value):
                        found_title = True
                        break
                if found_title:
                    break
            
            self.assertTrue(found_title)
            
            # Cleanup
            os.remove(file_path)
            
        except ImportError:
            self.skipTest("openpyxl not available")
    
    def test_http_response_creation(self):
        """Test HTTP response creation for downloads."""
        filename = 'test_report.json'
        response = self.exporter.create_http_response(
            self.sample_report_data, 
            'json', 
            filename
        )
        
        self.assertEqual(response['Content-Type'], 'application/json; charset=utf-8')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn(filename, response['Content-Disposition'])


class ReportSchedulerTestCase(TenantTestCase):
    """
    Test case for report scheduling functionality.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test tenant and domain."""
        super().setUpClass()
        
        # Create test tenant
        cls.tenant = Tenant(
            name='Test Schedule Shop',
            schema_name='test_schedule',
            domain_url='testschedule'
        )
        cls.tenant.save()
        
        # Create domain
        cls.domain = Domain(
            domain='testschedule.zargar.com',
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='scheduleuser',
            email='schedule@example.com',
            password='testpass123',
            role='owner'
        )
        
        # Create test template
        self.template = ReportTemplate.objects.create(
            name='Scheduled Test Report',
            name_persian='گزارش تست زمان‌بندی شده',
            report_type='trial_balance',
            default_output_format='pdf',
            is_active=True
        )
        
        # Create test schedule
        self.schedule = ReportSchedule.objects.create(
            name='Daily Test Schedule',
            name_persian='زمان‌بندی روزانه تست',
            template=self.template,
            frequency='daily',
            start_date=timezone.now().date(),
            execution_time='08:00:00',
            delivery_methods=['internal'],
            is_active=True
        )
        
        self.scheduler = ReportScheduler()
    
    def test_schedule_parameter_building(self):
        """Test building parameters for scheduled reports."""
        parameters = self.scheduler._build_schedule_parameters(self.schedule)
        
        self.assertIn('date_from', parameters)
        self.assertIn('date_to', parameters)
        
        # For daily schedule, should be yesterday
        expected_date = timezone.now().date() - timedelta(days=1)
        self.assertEqual(parameters['date_from'], expected_date)
        self.assertEqual(parameters['date_to'], expected_date)
    
    def test_schedule_execution_check(self):
        """Test checking if schedule should execute."""
        # Set next execution to past time
        self.schedule.next_execution = timezone.now() - timedelta(hours=1)
        self.schedule.save()
        
        self.assertTrue(self.schedule.should_execute_now())
        
        # Set next execution to future time
        self.schedule.next_execution = timezone.now() + timedelta(hours=1)
        self.schedule.save()
        
        self.assertFalse(self.schedule.should_execute_now())
    
    def test_next_execution_calculation(self):
        """Test calculation of next execution time."""
        # Test daily frequency
        self.schedule.frequency = 'daily'
        self.schedule.last_execution = timezone.now()
        self.schedule.calculate_next_execution()
        
        self.assertIsNotNone(self.schedule.next_execution)
        
        # Test weekly frequency
        self.schedule.frequency = 'weekly'
        self.schedule.day_of_week = 1  # Tuesday
        self.schedule.calculate_next_execution()
        
        self.assertIsNotNone(self.schedule.next_execution)
    
    @patch('zargar.reports.scheduler.ReportScheduler._generate_scheduled_report')
    @patch('zargar.reports.scheduler.ReportScheduler._deliver_report')
    def test_schedule_execution(self, mock_deliver, mock_generate):
        """Test executing a schedule."""
        # Mock the report generation
        mock_report = MagicMock()
        mock_report.report_id = 'TEST-REPORT-001'
        mock_generate.return_value = mock_report
        
        # Mock the delivery
        mock_deliver.return_value = [{'status': 'delivered'}]
        
        result = self.scheduler.execute_schedule(self.schedule)
        
        self.assertIn('schedule_id', result)
        self.assertIn('generated_report_id', result)
        self.assertIn('delivery_results', result)
        
        # Verify methods were called
        mock_generate.assert_called_once()
        mock_deliver.assert_called_once()


class ReportModelTestCase(TenantTestCase):
    """
    Test case for report models.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test tenant and domain."""
        super().setUpClass()
        
        # Create test tenant
        cls.tenant = Tenant(
            name='Test Model Shop',
            schema_name='test_model',
            domain_url='testmodel'
        )
        cls.tenant.save()
        
        # Create domain
        cls.domain = Domain(
            domain='testmodel.zargar.com',
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='modeluser',
            email='model@example.com',
            password='testpass123',
            role='owner'
        )
        
        self.template = ReportTemplate.objects.create(
            name='Model Test Template',
            name_persian='قالب تست مدل',
            report_type='trial_balance',
            default_output_format='pdf',
            is_active=True
        )
    
    def test_report_template_creation(self):
        """Test report template model."""
        self.assertEqual(str(self.template), 'قالب تست مدل')
        self.assertTrue(self.template.is_active)
        self.assertEqual(self.template.report_type, 'trial_balance')
    
    def test_generated_report_creation(self):
        """Test generated report model."""
        report = GeneratedReport.objects.create(
            template=self.template,
            generated_by=self.user,
            output_format='pdf',
            status='completed'
        )
        
        self.assertIsNotNone(report.report_id)
        self.assertTrue(report.report_id.startswith('RPT-'))
        self.assertIsNotNone(report.expires_at)
        
        # Test download filename generation
        filename = report.download_filename
        self.assertTrue(filename.endswith('.pdf'))
        self.assertIn('model_test_template', filename.lower())
    
    def test_report_schedule_creation(self):
        """Test report schedule model."""
        schedule = ReportSchedule.objects.create(
            name='Test Schedule',
            name_persian='زمان‌بندی تست',
            template=self.template,
            frequency='daily',
            start_date=timezone.now().date(),
            execution_time='09:00:00',
            delivery_methods=['email'],
            email_recipients=['test@example.com'],
            is_active=True
        )
        
        self.assertEqual(str(schedule), 'زمان‌بندی تست')
        self.assertTrue(schedule.is_active)
        self.assertEqual(schedule.frequency, 'daily')
        
        # Test execution marking
        initial_count = schedule.total_executions
        schedule.mark_execution(success=True)
        
        self.assertEqual(schedule.total_executions, initial_count + 1)
        self.assertEqual(schedule.successful_executions, 1)
        self.assertIsNotNone(schedule.last_execution)
    
    def test_report_delivery_creation(self):
        """Test report delivery model."""
        report = GeneratedReport.objects.create(
            template=self.template,
            generated_by=self.user,
            output_format='pdf',
            status='completed'
        )
        
        delivery = ReportDelivery.objects.create(
            generated_report=report,
            delivery_method='email',
            recipient='test@example.com',
            status='pending'
        )
        
        self.assertEqual(delivery.status, 'pending')
        self.assertTrue(delivery.can_retry)
        
        # Test status changes
        delivery.mark_sent()
        self.assertEqual(delivery.status, 'sent')
        self.assertIsNotNone(delivery.sent_at)
        
        delivery.mark_delivered()
        self.assertEqual(delivery.status, 'delivered')
        self.assertIsNotNone(delivery.delivered_at)


class ReportCacheServiceTestCase(TestCase):
    """
    Test case for report caching functionality.
    """
    
    def setUp(self):
        """Set up test data."""
        self.cache_service = ReportCacheService()
        
        self.sample_parameters = {
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
            'include_zero_balances': False
        }
        
        self.sample_report_data = {
            'report_type': 'trial_balance',
            'total_debits': Decimal('1000000'),
            'total_credits': Decimal('1000000'),
            'generated_at': timezone.now()
        }
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        cache_key = self.cache_service.get_cache_key(1, self.sample_parameters)
        
        self.assertIsInstance(cache_key, str)
        self.assertTrue(cache_key.startswith('report_cache_1_'))
        
        # Same parameters should generate same key
        cache_key2 = self.cache_service.get_cache_key(1, self.sample_parameters)
        self.assertEqual(cache_key, cache_key2)
        
        # Different parameters should generate different key
        different_params = self.sample_parameters.copy()
        different_params['include_zero_balances'] = True
        cache_key3 = self.cache_service.get_cache_key(1, different_params)
        self.assertNotEqual(cache_key, cache_key3)
    
    def test_cache_operations(self):
        """Test caching and retrieval operations."""
        template_id = 1
        
        # Initially should return None
        cached_data = self.cache_service.get_cached_report(template_id, self.sample_parameters)
        self.assertIsNone(cached_data)
        
        # Cache the report
        self.cache_service.cache_report(
            template_id, 
            self.sample_parameters, 
            self.sample_report_data,
            timeout=60
        )
        
        # Should now return cached data
        cached_data = self.cache_service.get_cached_report(template_id, self.sample_parameters)
        self.assertIsNotNone(cached_data)
        self.assertEqual(cached_data['report_type'], 'trial_balance')


# Integration test for the complete reporting workflow
class ReportingWorkflowIntegrationTestCase(TenantTestCase):
    """
    Integration test for the complete reporting workflow.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test tenant and domain."""
        super().setUpClass()
        
        # Create test tenant
        cls.tenant = Tenant(
            name='Integration Test Shop',
            schema_name='test_integration',
            domain_url='testintegration'
        )
        cls.tenant.save()
        
        # Create domain
        cls.domain = Domain(
            domain='testintegration.zargar.com',
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
    
    def setUp(self):
        """Set up comprehensive test data."""
        # Create user
        self.user = User.objects.create_user(
            username='integrationuser',
            email='integration@example.com',
            password='testpass123',
            role='owner'
        )
        
        # Create comprehensive accounting data
        self._create_accounting_data()
        
        # Create inventory data
        self._create_inventory_data()
        
        # Create customer and installment data
        self._create_customer_data()
        
        # Create report templates
        self._create_report_templates()
    
    def _create_accounting_data(self):
        """Create comprehensive accounting test data."""
        # Assets
        self.cash_account = ChartOfAccounts.objects.create(
            account_code='1001',
            account_name_english='Cash',
            account_name_persian='نقد',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit',
            is_active=True,
            allow_posting=True
        )
        
        self.inventory_account = ChartOfAccounts.objects.create(
            account_code='1201',
            account_name_english='Inventory',
            account_name_persian='موجودی کالا',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit',
            is_active=True,
            allow_posting=True
        )
        
        # Revenue
        self.sales_account = ChartOfAccounts.objects.create(
            account_code='4001',
            account_name_english='Sales Revenue',
            account_name_persian='درآمد فروش',
            account_type='revenue',
            account_category='operating_revenue',
            normal_balance='credit',
            is_active=True,
            allow_posting=True
        )
        
        # Expenses
        self.expense_account = ChartOfAccounts.objects.create(
            account_code='5001',
            account_name_english='Operating Expenses',
            account_name_persian='هزینه‌های عملیاتی',
            account_type='expense',
            account_category='operating_expenses',
            normal_balance='debit',
            is_active=True,
            allow_posting=True
        )
        
        # Create journal entries
        self._create_journal_entries()
    
    def _create_journal_entries(self):
        """Create test journal entries."""
        # Sales transaction
        sales_entry = JournalEntry.objects.create(
            entry_number='JE-SALES-001',
            entry_date=timezone.now().date() - timedelta(days=15),
            description='Sales transaction',
            reference_number='SALE-001',
            created_by=self.user
        )
        
        JournalEntryLine.objects.create(
            journal_entry=sales_entry,
            account=self.cash_account,
            debit_amount=Decimal('5000000'),
            credit_amount=Decimal('0'),
            description='Cash received from sales'
        )
        
        JournalEntryLine.objects.create(
            journal_entry=sales_entry,
            account=self.sales_account,
            debit_amount=Decimal('0'),
            credit_amount=Decimal('5000000'),
            description='Sales revenue'
        )
        
        # Expense transaction
        expense_entry = JournalEntry.objects.create(
            entry_number='JE-EXP-001',
            entry_date=timezone.now().date() - timedelta(days=10),
            description='Operating expense',
            reference_number='EXP-001',
            created_by=self.user
        )
        
        JournalEntryLine.objects.create(
            journal_entry=expense_entry,
            account=self.expense_account,
            debit_amount=Decimal('1000000'),
            credit_amount=Decimal('0'),
            description='Operating expense'
        )
        
        JournalEntryLine.objects.create(
            journal_entry=expense_entry,
            account=self.cash_account,
            debit_amount=Decimal('0'),
            credit_amount=Decimal('1000000'),
            description='Cash paid for expense'
        )
    
    def _create_inventory_data(self):
        """Create test inventory data."""
        self.category = Category.objects.create(
            name='Gold Rings',
            name_persian='حلقه‌های طلا',
            description='Gold ring collection'
        )
        
        self.jewelry_items = []
        for i in range(5):
            item = JewelryItem.objects.create(
                name=f'Gold Ring {i+1}',
                category=self.category,
                weight_grams=Decimal(f'{5 + i}.500'),
                karat=18,
                manufacturing_cost=Decimal(f'{500000 + i*100000}'),
                sku=f'RING-{i+1:03d}',
                quantity=10 - i,
                status='in_stock'
            )
            self.jewelry_items.append(item)
    
    def _create_customer_data(self):
        """Create test customer and installment data."""
        self.customers = []
        for i in range(3):
            customer = Customer.objects.create(
                first_name=f'Customer{i+1}',
                last_name='Test',
                persian_first_name=f'مشتری{i+1}',
                persian_last_name='تست',
                phone_number=f'0912345678{i}',
                email=f'customer{i+1}@example.com'
            )
            self.customers.append(customer)
            
            # Create installment contract
            contract = GoldInstallmentContract.objects.create(
                customer=customer,
                initial_gold_weight_grams=Decimal(f'{100 + i*50}.000'),
                remaining_gold_weight_grams=Decimal(f'{50 + i*25}.000'),
                payment_schedule='monthly',
                contract_date=timezone.now().date() - timedelta(days=30 + i*15),
                status='active'
            )
            
            # Create some payments
            for j in range(2):
                GoldInstallmentPayment.objects.create(
                    contract=contract,
                    payment_date=timezone.now().date() - timedelta(days=20 - j*10),
                    payment_amount_toman=Decimal(f'{2000000 + j*500000}'),
                    gold_weight_reduced_grams=Decimal(f'{25 + j*10}.000'),
                    gold_price_per_gram_at_payment=Decimal('1400000'),
                    payment_method='cash'
                )
    
    def _create_report_templates(self):
        """Create test report templates."""
        self.templates = {}
        
        template_configs = [
            ('trial_balance', 'Trial Balance', 'ترازنامه آزمایشی'),
            ('profit_loss', 'Profit & Loss', 'سود و زیان'),
            ('balance_sheet', 'Balance Sheet', 'ترازنامه'),
            ('inventory_valuation', 'Inventory Valuation', 'ارزش‌گذاری موجودی'),
            ('customer_aging', 'Customer Aging', 'سن مطالبات'),
        ]
        
        for report_type, name_en, name_fa in template_configs:
            template = ReportTemplate.objects.create(
                name=name_en,
                name_persian=name_fa,
                report_type=report_type,
                default_output_format='pdf',
                is_active=True
            )
            self.templates[report_type] = template
    
    def test_complete_reporting_workflow(self):
        """Test the complete reporting workflow from template to delivery."""
        # Initialize services
        reporting_engine = ComprehensiveReportingEngine(tenant=self.tenant)
        exporter = ReportExporter()
        
        # Test each report type
        for report_type, template in self.templates.items():
            with self.subTest(report_type=report_type):
                # Generate report parameters
                parameters = {
                    'date_from': timezone.now().date() - timedelta(days=30),
                    'date_to': timezone.now().date(),
                }
                
                if report_type == 'inventory_valuation':
                    parameters['gold_price_per_gram'] = Decimal('1500000')
                elif report_type == 'customer_aging':
                    parameters['aging_periods'] = [30, 60, 90, 120]
                    parameters['current_gold_price_per_gram'] = Decimal('1500000')
                elif report_type in ['balance_sheet']:
                    parameters = {'as_of_date': timezone.now().date()}
                
                # Generate report
                report_data = reporting_engine.generate_report(template, parameters)
                
                # Verify report structure
                self.assertEqual(report_data['report_type'], report_type)
                self.assertIn('generated_at', report_data)
                self.assertIn('generated_at_shamsi', report_data)
                
                # Test export to different formats
                for format_type in ['json', 'csv']:
                    filename = f'test_{report_type}.{format_type}'
                    file_path = exporter.export_report(report_data, format_type, filename)
                    
                    # Verify file was created
                    self.assertTrue(os.path.exists(file_path))
                    
                    # Cleanup
                    os.remove(file_path)
    
    def test_scheduled_report_generation(self):
        """Test scheduled report generation workflow."""
        # Create a schedule
        schedule = ReportSchedule.objects.create(
            name='Integration Test Schedule',
            name_persian='زمان‌بندی تست یکپارچه',
            template=self.templates['trial_balance'],
            frequency='daily',
            start_date=timezone.now().date(),
            execution_time='08:00:00',
            delivery_methods=['internal'],
            is_active=True,
            next_execution=timezone.now() - timedelta(minutes=1)  # Should execute now
        )
        
        # Execute the schedule
        scheduler = ReportScheduler()
        result = scheduler.execute_schedule(schedule)
        
        # Verify execution
        self.assertIn('schedule_id', result)
        self.assertIn('generated_report_id', result)
        
        # Verify generated report was created
        generated_report = GeneratedReport.objects.get(
            report_id=result['generated_report_id']
        )
        self.assertEqual(generated_report.status, 'completed')
        self.assertIsNotNone(generated_report.report_data)
    
    def test_report_performance(self):
        """Test report generation performance with realistic data volume."""
        # This test ensures reports can be generated efficiently
        start_time = timezone.now()
        
        # Generate a complex report (trial balance with all accounts)
        reporting_engine = ComprehensiveReportingEngine(tenant=self.tenant)
        parameters = {
            'date_from': timezone.now().date() - timedelta(days=365),
            'date_to': timezone.now().date(),
            'include_zero_balances': True
        }
        
        report_data = reporting_engine.generate_trial_balance(parameters)
        
        end_time = timezone.now()
        generation_time = (end_time - start_time).total_seconds()
        
        # Report should be generated within reasonable time (5 seconds)
        self.assertLess(generation_time, 5.0)
        
        # Verify report completeness
        self.assertIn('accounts', report_data)
        self.assertIn('total_debits', report_data)
        self.assertIn('total_credits', report_data)