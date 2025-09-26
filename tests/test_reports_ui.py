"""
Test cases for Reports UI implementation.

This module tests the frontend reporting interface including:
- Report generation UI
- Report viewing and preview
- Export functionality
- Persian formatting and RTL layout
- Dual theme support
"""

import pytest
import django
from django.conf import settings
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import json
import os

# Configure Django settings for testing
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

from zargar.reports.models import ReportTemplate, GeneratedReport, ReportSchedule

User = get_user_model()


class ReportsUITestCase(TestCase):
    """Base test case for reports UI tests."""
    
    def setUp(self):
        """Set up test data."""
        # Create user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        # Set user role if the field exists
        if hasattr(self.user, 'role'):
            self.user.role = "owner"
            self.user.save()
        
        # Create report template
        self.template = ReportTemplate.objects.create(
            name="Test Trial Balance",
            name_persian="ترازنامه آزمایشی تست",
            description="Test trial balance report",
            report_type="trial_balance",
            default_output_format="pdf",
            created_by=self.user
        )
        
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")


class ReportsDashboardUITest(ReportsUITestCase):
    """Test reports dashboard UI."""
    
    def test_dashboard_loads_successfully(self):
        """Test that dashboard loads with correct context."""
        response = self.client.get(reverse('reports:dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'گزارش‌های مالی و عملیاتی')
        self.assertContains(response, 'تولید گزارش جدید')
        
    def test_dashboard_displays_statistics(self):
        """Test that dashboard shows report statistics."""
        # Create some test reports
        GeneratedReport.objects.create(
            template=self.template,
            generated_by=self.user,
            output_format="pdf",
            status="completed"
        )
        
        response = self.client.get(reverse('reports:dashboard'))
        
        self.assertContains(response, 'کل گزارش‌ها')
        self.assertContains(response, 'گزارش‌های این ماه')
        
    def test_dashboard_shows_recent_reports(self):
        """Test that dashboard displays recent reports."""
        report = GeneratedReport.objects.create(
            template=self.template,
            generated_by=self.user,
            output_format="pdf",
            status="completed"
        )
        
        response = self.client.get(reverse('reports:dashboard'))
        
        self.assertContains(response, 'گزارش‌های اخیر')
        self.assertContains(response, self.template.name_persian)
        
    def test_dashboard_persian_formatting(self):
        """Test Persian number formatting on dashboard."""
        response = self.client.get(reverse('reports:dashboard'))
        
        # Check for Persian class for number formatting
        self.assertContains(response, 'persian-numbers')
        
    def test_dashboard_theme_support(self):
        """Test dual theme support in dashboard."""
        response = self.client.get(reverse('reports:dashboard'))
        
        # Check for theme-aware CSS classes
        self.assertContains(response, 'is_dark_mode')
        self.assertContains(response, 'cyber-bg-primary')
        self.assertContains(response, 'cyber-text-primary')


class ReportGenerationUITest(ReportsUITestCase):
    """Test report generation UI."""
    
    def test_generation_page_loads(self):
        """Test that report generation page loads correctly."""
        response = self.client.get(reverse('reports:generate'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تولید گزارش جدید')
        self.assertContains(response, 'انتخاب نوع گزارش')
        
    def test_template_selection_interface(self):
        """Test template selection interface."""
        response = self.client.get(reverse('reports:generate'))
        
        self.assertContains(response, self.template.name_persian)
        self.assertContains(response, 'template_id')
        self.assertContains(response, 'radio')
        
    def test_date_range_picker(self):
        """Test Persian date range picker."""
        response = self.client.get(reverse('reports:generate'))
        
        self.assertContains(response, 'از تاریخ (شمسی)')
        self.assertContains(response, 'تا تاریخ (شمسی)')
        self.assertContains(response, 'date_from_shamsi')
        self.assertContains(response, 'date_to_shamsi')
        
    def test_quick_date_ranges(self):
        """Test quick date range buttons."""
        response = self.client.get(reverse('reports:generate'))
        
        self.assertContains(response, 'این ماه')
        self.assertContains(response, 'ماه گذشته')
        self.assertContains(response, 'این فصل')
        self.assertContains(response, 'امسال')
        
    def test_report_parameters_section(self):
        """Test report-specific parameters section."""
        response = self.client.get(reverse('reports:generate'))
        
        self.assertContains(response, 'پارامترهای گزارش')
        self.assertContains(response, 'فرمت خروجی')
        
    def test_gold_price_parameter(self):
        """Test gold price parameter for inventory reports."""
        # Create inventory template
        inventory_template = ReportTemplate.objects.create(
            name="Inventory Valuation",
            name_persian="ارزش‌گذاری موجودی",
            report_type="inventory_valuation",
            created_by=self.user
        )
        
        response = self.client.get(
            reverse('reports:generate_template', kwargs={'template_id': inventory_template.id})
        )
        
        self.assertContains(response, 'قیمت طلا')
        self.assertContains(response, 'gold_price_per_gram')
        self.assertContains(response, 'قیمت فعلی')
        
    def test_output_format_selection(self):
        """Test output format selection."""
        response = self.client.get(reverse('reports:generate'))
        
        self.assertContains(response, 'PDF')
        self.assertContains(response, 'Excel')
        self.assertContains(response, 'CSV')
        
    def test_form_validation_ui(self):
        """Test form validation in UI."""
        response = self.client.post(reverse('reports:generate'), {
            # Missing required fields
        })
        
        # Should show validation errors
        self.assertContains(response, 'انتخاب کنید')
        
    def test_progress_modal(self):
        """Test progress modal for report generation."""
        response = self.client.get(reverse('reports:generate'))
        
        self.assertContains(response, 'در حال تولید گزارش')
        self.assertContains(response, 'progress')


class ReportListUITest(ReportsUITestCase):
    """Test report list UI."""
    
    def test_list_page_loads(self):
        """Test that report list page loads correctly."""
        response = self.client.get(reverse('reports:list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'لیست گزارش‌ها')
        
    def test_filter_interface(self):
        """Test report filtering interface."""
        response = self.client.get(reverse('reports:list'))
        
        self.assertContains(response, 'جستجو')
        self.assertContains(response, 'وضعیت')
        self.assertContains(response, 'نوع گزارش')
        self.assertContains(response, 'اعمال فیلتر')
        
    def test_reports_table_display(self):
        """Test reports table display."""
        report = GeneratedReport.objects.create(
            template=self.template,
            generated_by=self.user,
            output_format="pdf",
            status="completed"
        )
        
        response = self.client.get(reverse('reports:list'))
        
        self.assertContains(response, self.template.name_persian)
        self.assertContains(response, report.report_id)
        self.assertContains(response, 'تکمیل شده')
        
    def test_status_indicators(self):
        """Test status indicators in list."""
        # Create reports with different statuses
        GeneratedReport.objects.create(
            template=self.template,
            generated_by=self.user,
            output_format="pdf",
            status="completed"
        )
        
        GeneratedReport.objects.create(
            template=self.template,
            generated_by=self.user,
            output_format="pdf",
            status="generating"
        )
        
        response = self.client.get(reverse('reports:list'))
        
        self.assertContains(response, 'تکمیل شده')
        self.assertContains(response, 'در حال تولید')
        
    def test_pagination_display(self):
        """Test pagination in report list."""
        # Create multiple reports to trigger pagination
        for i in range(25):
            GeneratedReport.objects.create(
                template=self.template,
                generated_by=self.user,
                output_format="pdf",
                status="completed"
            )
        
        response = self.client.get(reverse('reports:list'))
        
        self.assertContains(response, 'نمایش')
        self.assertContains(response, 'نتیجه')
        
    def test_empty_state(self):
        """Test empty state when no reports exist."""
        response = self.client.get(reverse('reports:list'))
        
        self.assertContains(response, 'هیچ گزارشی یافت نشد')
        self.assertContains(response, 'تولید گزارش جدید')


class ReportDetailUITest(ReportsUITestCase):
    """Test report detail UI."""
    
    def setUp(self):
        super().setUp()
        self.report = GeneratedReport.objects.create(
            template=self.template,
            generated_by=self.user,
            output_format="pdf",
            status="completed",
            report_data={
                'report_type': 'trial_balance',
                'accounts': [
                    {
                        'account_code': '1001',
                        'account_name_persian': 'صندوق',
                        'debit_amount': 1000000,
                        'credit_amount': 0
                    }
                ],
                'total_debits': 1000000,
                'total_credits': 1000000
            }
        )
    
    def test_detail_page_loads(self):
        """Test that report detail page loads correctly."""
        response = self.client.get(
            reverse('reports:report_detail', kwargs={'report_id': self.report.report_id})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.template.name_persian)
        self.assertContains(response, self.report.report_id)
        
    def test_report_info_cards(self):
        """Test report information cards."""
        response = self.client.get(
            reverse('reports:report_detail', kwargs={'report_id': self.report.report_id})
        )
        
        self.assertContains(response, 'وضعیت')
        self.assertContains(response, 'تاریخ تولید')
        self.assertContains(response, 'فرمت خروجی')
        
    def test_download_options(self):
        """Test download options for completed reports."""
        response = self.client.get(
            reverse('reports:report_detail', kwargs={'report_id': self.report.report_id})
        )
        
        self.assertContains(response, 'دانلود گزارش')
        self.assertContains(response, 'دانلود PDF')
        self.assertContains(response, 'دانلود Excel')
        
    def test_report_preview(self):
        """Test report preview display."""
        response = self.client.get(
            reverse('reports:report_detail', kwargs={'report_id': self.report.report_id})
        )
        
        self.assertContains(response, 'پیش‌نمایش گزارش')
        self.assertContains(response, 'صندوق')  # Account name from test data
        
    def test_generating_status_display(self):
        """Test display for generating reports."""
        self.report.status = 'generating'
        self.report.save()
        
        response = self.client.get(
            reverse('reports:report_detail', kwargs={'report_id': self.report.report_id})
        )
        
        self.assertContains(response, 'در حال تولید گزارش')
        self.assertContains(response, 'progress')
        
    def test_failed_status_display(self):
        """Test display for failed reports."""
        self.report.status = 'failed'
        self.report.error_message = 'Test error message'
        self.report.save()
        
        response = self.client.get(
            reverse('reports:report_detail', kwargs={'report_id': self.report.report_id})
        )
        
        self.assertContains(response, 'خطا در تولید گزارش')
        self.assertContains(response, 'Test error message')
        self.assertContains(response, 'تولید مجدد')


class ReportScheduleUITest(ReportsUITestCase):
    """Test report scheduling UI."""
    
    def test_schedule_list_loads(self):
        """Test that schedule list page loads correctly."""
        response = self.client.get(reverse('reports:schedule_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'زمان‌بندی گزارش‌ها')
        
    def test_schedule_creation_form(self):
        """Test schedule creation form."""
        response = self.client.get(reverse('reports:schedule_create'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'زمان‌بندی جدید')
        self.assertContains(response, 'name_persian')
        self.assertContains(response, 'frequency')
        
    def test_schedule_display(self):
        """Test schedule display in list."""
        schedule = ReportSchedule.objects.create(
            name="Daily Report",
            name_persian="گزارش روزانه",
            template=self.template,
            frequency="daily",
            start_date=timezone.now().date(),
            created_by=self.user
        )
        
        response = self.client.get(reverse('reports:schedule_list'))
        
        self.assertContains(response, 'گزارش روزانه')
        self.assertContains(response, 'روزانه')
        self.assertContains(response, 'فعال')


class ReportExportUITest(ReportsUITestCase):
    """Test report export functionality."""
    
    def setUp(self):
        super().setUp()
        self.report = GeneratedReport.objects.create(
            template=self.template,
            generated_by=self.user,
            output_format="pdf",
            status="completed"
        )
    
    def test_export_links_present(self):
        """Test that export links are present."""
        response = self.client.get(
            reverse('reports:report_detail', kwargs={'report_id': self.report.report_id})
        )
        
        self.assertContains(response, 'دانلود PDF')
        self.assertContains(response, 'دانلود Excel')
        self.assertContains(response, 'دانلود CSV')
        
    def test_export_url_generation(self):
        """Test export URL generation."""
        pdf_url = reverse('reports:download', kwargs={
            'report_id': self.report.report_id,
            'format': 'pdf'
        })
        
        self.assertIn(self.report.report_id, pdf_url)
        self.assertIn('pdf', pdf_url)


class PersianFormattingUITest(ReportsUITestCase):
    """Test Persian formatting in UI."""
    
    def test_persian_number_classes(self):
        """Test Persian number CSS classes."""
        response = self.client.get(reverse('reports:dashboard'))
        
        self.assertContains(response, 'persian-numbers')
        
    def test_rtl_layout_classes(self):
        """Test RTL layout CSS classes."""
        response = self.client.get(reverse('reports:dashboard'))
        
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, 'text-right')
        
    def test_persian_fonts(self):
        """Test Persian font usage."""
        response = self.client.get(reverse('reports:dashboard'))
        
        self.assertContains(response, 'Vazirmatn')
        self.assertContains(response, 'font-vazir')


class ThemeUITest(ReportsUITestCase):
    """Test dual theme support in UI."""
    
    def test_theme_toggle_present(self):
        """Test that theme toggle is present."""
        response = self.client.get(reverse('reports:dashboard'))
        
        self.assertContains(response, 'theme-toggle')
        self.assertContains(response, 'toggleTheme')
        
    def test_dark_theme_classes(self):
        """Test dark theme CSS classes."""
        response = self.client.get(reverse('reports:dashboard'))
        
        self.assertContains(response, 'cyber-bg-primary')
        self.assertContains(response, 'cyber-text-primary')
        self.assertContains(response, 'cyber-neon-primary')
        
    def test_light_theme_classes(self):
        """Test light theme CSS classes."""
        response = self.client.get(reverse('reports:dashboard'))
        
        self.assertContains(response, 'bg-gray-50')
        self.assertContains(response, 'text-gray-900')


class ResponsiveUITest(ReportsUITestCase):
    """Test responsive design."""
    
    def test_mobile_responsive_classes(self):
        """Test mobile responsive CSS classes."""
        response = self.client.get(reverse('reports:dashboard'))
        
        self.assertContains(response, 'md:grid-cols-2')
        self.assertContains(response, 'lg:grid-cols-4')
        self.assertContains(response, 'sm:flex')
        
    def test_grid_layout_classes(self):
        """Test grid layout classes."""
        response = self.client.get(reverse('reports:dashboard'))
        
        self.assertContains(response, 'grid')
        self.assertContains(response, 'grid-cols-1')


class AccessibilityUITest(ReportsUITestCase):
    """Test accessibility features."""
    
    def test_aria_labels(self):
        """Test ARIA labels for accessibility."""
        response = self.client.get(reverse('reports:dashboard'))
        
        self.assertContains(response, 'aria-label')
        
    def test_semantic_html(self):
        """Test semantic HTML structure."""
        response = self.client.get(reverse('reports:dashboard'))
        
        self.assertContains(response, '<main')
        self.assertContains(response, '<nav')
        self.assertContains(response, '<section')
        
    def test_form_labels(self):
        """Test form labels for accessibility."""
        response = self.client.get(reverse('reports:generate'))
        
        self.assertContains(response, '<label')
        self.assertContains(response, 'for=')


class JavaScriptIntegrationTest(ReportsUITestCase):
    """Test JavaScript integration."""
    
    def test_javascript_includes(self):
        """Test JavaScript file includes."""
        response = self.client.get(reverse('reports:dashboard'))
        
        self.assertContains(response, 'reports-dashboard.js')
        
    def test_alpine_js_integration(self):
        """Test Alpine.js integration."""
        response = self.client.get(reverse('reports:generate'))
        
        self.assertContains(response, 'x-data')
        self.assertContains(response, 'x-show')
        
    def test_htmx_integration(self):
        """Test HTMX integration."""
        response = self.client.get(reverse('reports:list'))
        
        self.assertContains(response, 'hx-')


if __name__ == '__main__':
    pytest.main([__file__])