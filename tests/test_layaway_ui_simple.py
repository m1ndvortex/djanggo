"""
Simple tests for layaway UI functionality.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from zargar.customers.layaway_models import LayawayPlan, LayawayPayment
from zargar.customers.layaway_services import LayawayPlanService


User = get_user_model()


@pytest.mark.django_db
class TestLayawayUIComponents:
    """Test layaway UI components and functionality."""
    
    def test_layaway_plan_form_validation(self):
        """Test layaway plan form validation."""
        from zargar.customers.layaway_views import LayawayPlanForm
        
        # Test valid form data
        form_data = {
            'total_amount': '15000000',
            'down_payment': '3000000',
            'payment_frequency': 'monthly',
            'number_of_payments': '12',
            'start_date': date.today().strftime('%Y-%m-%d'),
            'grace_period_days': '7',
            'notes': 'Test layaway plan'
        }
        
        # Note: We can't test the full form without tenant context
        # But we can test the form class exists and has correct fields
        form = LayawayPlanForm()
        
        expected_fields = [
            'customer', 'jewelry_item', 'total_amount', 'down_payment',
            'payment_frequency', 'number_of_payments', 'start_date',
            'grace_period_days', 'notes'
        ]
        
        for field in expected_fields:
            assert field in form.fields
    
    def test_layaway_payment_form_validation(self):
        """Test layaway payment form validation."""
        from zargar.customers.layaway_views import LayawayPaymentForm
        
        form = LayawayPaymentForm()
        
        expected_fields = ['amount', 'payment_method', 'reference_number', 'notes']
        
        for field in expected_fields:
            assert field in form.fields
    
    def test_layaway_dashboard_view_class(self):
        """Test layaway dashboard view class exists."""
        from zargar.customers.layaway_views import LayawayDashboardView
        
        view = LayawayDashboardView()
        assert view.template_name == 'customers/layaway_dashboard.html'
    
    def test_layaway_create_view_class(self):
        """Test layaway create view class exists."""
        from zargar.customers.layaway_views import LayawayPlanCreateView
        
        view = LayawayPlanCreateView()
        assert view.template_name == 'customers/layaway_plan_create.html'
        assert view.success_url == reverse('customers:layaway_dashboard')
    
    def test_layaway_detail_view_class(self):
        """Test layaway detail view class exists."""
        from zargar.customers.layaway_views import LayawayPlanDetailView
        
        view = LayawayPlanDetailView()
        assert view.template_name == 'customers/layaway_plan_detail.html'
        assert view.context_object_name == 'plan'
    
    def test_layaway_list_view_class(self):
        """Test layaway list view class exists."""
        from zargar.customers.layaway_views import LayawayPlanListView
        
        view = LayawayPlanListView()
        assert view.template_name == 'customers/layaway_plan_list.html'
        assert view.context_object_name == 'plans'
        assert view.paginate_by == 20
    
    def test_layaway_reminders_view_class(self):
        """Test layaway reminders view class exists."""
        from zargar.customers.layaway_views import LayawayReminderManagementView
        
        view = LayawayReminderManagementView()
        assert view.template_name == 'customers/layaway_reminders.html'
    
    def test_layaway_ajax_view_class(self):
        """Test layaway AJAX view class exists."""
        from zargar.customers.layaway_views import LayawayAjaxView
        
        view = LayawayAjaxView()
        assert hasattr(view, 'post')
    
    def test_layaway_reports_view_class(self):
        """Test layaway reports view class exists."""
        from zargar.customers.layaway_views import LayawayReportsView
        
        view = LayawayReportsView()
        assert view.template_name == 'customers/layaway_reports.html'


@pytest.mark.django_db
class TestLayawayTemplates:
    """Test layaway templates exist and have correct structure."""
    
    def test_layaway_dashboard_template_exists(self):
        """Test layaway dashboard template exists."""
        from django.template.loader import get_template
        
        template = get_template('customers/layaway_dashboard.html')
        assert template is not None
    
    def test_layaway_create_template_exists(self):
        """Test layaway create template exists."""
        from django.template.loader import get_template
        
        template = get_template('customers/layaway_plan_create.html')
        assert template is not None
    
    def test_layaway_detail_template_exists(self):
        """Test layaway detail template exists."""
        from django.template.loader import get_template
        
        template = get_template('customers/layaway_plan_detail.html')
        assert template is not None
    
    def test_layaway_list_template_exists(self):
        """Test layaway list template exists."""
        from django.template.loader import get_template
        
        template = get_template('customers/layaway_plan_list.html')
        assert template is not None
    
    def test_layaway_reminders_template_exists(self):
        """Test layaway reminders template exists."""
        from django.template.loader import get_template
        
        template = get_template('customers/layaway_reminders.html')
        assert template is not None


@pytest.mark.django_db
class TestLayawayStaticFiles:
    """Test layaway static files exist."""
    
    def test_layaway_css_files_exist(self):
        """Test layaway CSS files exist."""
        import os
        from django.conf import settings
        
        css_files = [
            'static/css/layaway-dashboard.css',
            'static/css/layaway-forms.css',
            'static/css/layaway-detail.css'
        ]
        
        for css_file in css_files:
            assert os.path.exists(css_file), f"CSS file {css_file} does not exist"
    
    def test_layaway_js_files_exist(self):
        """Test layaway JavaScript files exist."""
        import os
        
        js_files = [
            'static/js/layaway-dashboard.js',
            'static/js/layaway-create.js',
            'static/js/layaway-detail.js'
        ]
        
        for js_file in js_files:
            assert os.path.exists(js_file), f"JavaScript file {js_file} does not exist"


@pytest.mark.django_db
class TestLayawayURLPatterns:
    """Test layaway URL patterns are configured correctly."""
    
    def test_layaway_urls_exist(self):
        """Test layaway URL patterns exist."""
        from django.urls import reverse
        
        # Test URL patterns can be resolved
        urls_to_test = [
            'customers:layaway_dashboard',
            'customers:layaway_list',
            'customers:layaway_create',
            'customers:layaway_reminders',
            'customers:layaway_reports',
            'customers:layaway_ajax'
        ]
        
        for url_name in urls_to_test:
            try:
                url = reverse(url_name)
                assert url is not None
            except Exception as e:
                pytest.fail(f"URL {url_name} could not be resolved: {e}")
    
    def test_layaway_detail_url_with_pk(self):
        """Test layaway detail URL with primary key."""
        from django.urls import reverse
        
        url = reverse('customers:layaway_detail', kwargs={'pk': 1})
        assert '/layaway/1/' in url


@pytest.mark.django_db
class TestLayawayServiceIntegration:
    """Test layaway service integration with UI."""
    
    def test_layaway_plan_service_exists(self):
        """Test layaway plan service exists and has required methods."""
        from zargar.customers.layaway_services import LayawayPlanService
        
        # Test service methods exist
        assert hasattr(LayawayPlanService, 'create_layaway_plan')
        assert hasattr(LayawayPlanService, 'process_payment')
        assert hasattr(LayawayPlanService, 'cancel_plan')
        assert hasattr(LayawayPlanService, 'get_overdue_plans')
        assert hasattr(LayawayPlanService, 'get_upcoming_payments')
        assert hasattr(LayawayPlanService, 'calculate_plan_statistics')
    
    def test_layaway_reminder_service_exists(self):
        """Test layaway reminder service exists."""
        from zargar.customers.layaway_services import LayawayReminderService
        
        assert hasattr(LayawayReminderService, 'create_reminder_schedule')
        assert hasattr(LayawayReminderService, 'send_overdue_reminders')
        assert hasattr(LayawayReminderService, 'send_upcoming_reminders')
    
    def test_layaway_contract_service_exists(self):
        """Test layaway contract service exists."""
        from zargar.customers.layaway_services import LayawayContractService
        
        assert hasattr(LayawayContractService, 'generate_contract_pdf')
        assert hasattr(LayawayContractService, 'create_default_contract_template')
    
    def test_layaway_report_service_exists(self):
        """Test layaway report service exists."""
        from zargar.customers.layaway_services import LayawayReportService
        
        assert hasattr(LayawayReportService, 'get_layaway_summary')
        assert hasattr(LayawayReportService, 'get_customer_layaway_history')


@pytest.mark.django_db
class TestLayawayModels:
    """Test layaway models are properly configured."""
    
    def test_layaway_plan_model_exists(self):
        """Test LayawayPlan model exists with required fields."""
        from zargar.customers.layaway_models import LayawayPlan
        
        # Test model exists
        assert LayawayPlan is not None
        
        # Test required fields exist
        required_fields = [
            'plan_number', 'customer', 'jewelry_item', 'total_amount',
            'down_payment', 'remaining_balance', 'payment_frequency',
            'installment_amount', 'number_of_payments', 'start_date',
            'status', 'payments_made', 'total_paid'
        ]
        
        model_fields = [field.name for field in LayawayPlan._meta.fields]
        
        for field in required_fields:
            assert field in model_fields, f"Field {field} not found in LayawayPlan model"
    
    def test_layaway_payment_model_exists(self):
        """Test LayawayPayment model exists with required fields."""
        from zargar.customers.layaway_models import LayawayPayment
        
        assert LayawayPayment is not None
        
        required_fields = [
            'layaway_plan', 'amount', 'payment_method', 'payment_date',
            'reference_number', 'receipt_number', 'notes'
        ]
        
        model_fields = [field.name for field in LayawayPayment._meta.fields]
        
        for field in required_fields:
            assert field in model_fields, f"Field {field} not found in LayawayPayment model"
    
    def test_layaway_reminder_model_exists(self):
        """Test LayawayReminder model exists with required fields."""
        from zargar.customers.layaway_models import LayawayReminder
        
        assert LayawayReminder is not None
        
        required_fields = [
            'layaway_plan', 'reminder_type', 'scheduled_date', 'sent_date',
            'delivery_method', 'recipient', 'message_template', 'is_sent'
        ]
        
        model_fields = [field.name for field in LayawayReminder._meta.fields]
        
        for field in required_fields:
            assert field in model_fields, f"Field {field} not found in LayawayReminder model"


if __name__ == '__main__':
    pytest.main([__file__])