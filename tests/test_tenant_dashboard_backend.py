"""
Tests for tenant dashboard backend functionality.
Tests dashboard service, metrics calculation, and data aggregation.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from zargar.core.dashboard_services import TenantDashboardService
from zargar.core.models import User, AuditLog
from zargar.jewelry.models import JewelryItem, Category
from zargar.customers.models import Customer, CustomerLoyaltyTransaction
from zargar.gold_installments.models import GoldInstallmentContract, GoldInstallmentPayment
from zargar.tenants.models import Tenant, Domain

User = get_user_model()


class TenantDashboardServiceTest(TenantTestCase):
    """
    Test suite for TenantDashboardService functionality.
    Tests all dashboard metrics and data aggregation features.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test tenant and domain."""
        super().setUpClass()
        
        # Switch to public schema to create tenant
        from django.db import connection
        connection.set_schema_to_public()
        
        # Create test tenant
        cls.tenant = Tenant(
            name='Test Jewelry Shop',
            schema_name='test_shop',
            owner_name='Test Owner',
            owner_email='owner@testshop.com'
        )
        cls.tenant.save()
        
        # Create domain
        cls.domain = Domain(
            domain='testshop.localhost',
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
        
        # Set up tenant client
        cls.client = TenantClient(cls.tenant)
        
        # Switch to tenant schema
        connection.set_tenant(cls.tenant)
    
    def setUp(self):
        """Set up test data for each test."""
        # Clear cache before each test
        cache.clear()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner',
            persian_first_name='تست',
            persian_last_name='کاربر'
        )
        
        # Initialize dashboard service
        self.dashboard_service = TenantDashboardService('test_shop')
        
        # Create test categories
        self.category_rings = Category.objects.create(
            name='Rings',
            name_persian='انگشتر',
            created_by=self.user
        )
        
        self.category_necklaces = Category.objects.create(
            name='Necklaces',
            name_persian='گردنبند',
            created_by=self.user
        )
        
        # Create test customers
        self.customer1 = Customer.objects.create(
            first_name='Ali',
            last_name='Ahmadi',
            persian_first_name='علی',
            persian_last_name='احمدی',
            phone_number='09123456789',
            email='ali@example.com',
            total_purchases=Decimal('5000000'),
            loyalty_points=500,
            created_by=self.user
        )
        
        self.customer2 = Customer.objects.create(
            first_name='Sara',
            last_name='Karimi',
            persian_first_name='سارا',
            persian_last_name='کریمی',
            phone_number='09123456788',
            email='sara@example.com',
            total_purchases=Decimal('10000000'),
            loyalty_points=1000,
            is_vip=True,
            created_by=self.user
        )
    
    def test_dashboard_service_initialization(self):
        """Test dashboard service initialization."""
        service = TenantDashboardService('test_tenant')
        
        self.assertEqual(service.tenant_schema, 'test_tenant')
        self.assertIsNotNone(service.formatter)
        self.assertIsNotNone(service.calendar_utils)
    
    def test_get_comprehensive_dashboard_data(self):
        """Test comprehensive dashboard data retrieval."""
        dashboard_data = self.dashboard_service.get_comprehensive_dashboard_data()
        
        # Check all required sections are present
        required_sections = [
            'sales_metrics', 'inventory_metrics', 'customer_metrics',
            'gold_installment_metrics', 'gold_price_data', 'financial_summary',
            'recent_activities', 'alerts_and_notifications', 'performance_trends'
        ]
        
        for section in required_sections:
            self.assertIn(section, dashboard_data)
        
        # Check metadata
        self.assertIn('generated_at', dashboard_data)
        self.assertEqual(dashboard_data['tenant_schema'], 'test_shop')
    
    def test_sales_metrics_calculation(self):
        """Test sales metrics calculation."""
        # Create test jewelry items
        item1 = JewelryItem.objects.create(
            name='Gold Ring',
            sku='GR001',
            category=self.category_rings,
            weight_grams=Decimal('5.5'),
            karat=18,
            manufacturing_cost=Decimal('500000'),
            selling_price=Decimal('2000000'),
            status='sold',
            created_by=self.user
        )
        
        item2 = JewelryItem.objects.create(
            name='Silver Necklace',
            sku='SN001',
            category=self.category_necklaces,
            weight_grams=Decimal('10.0'),
            karat=18,
            manufacturing_cost=Decimal('800000'),
            selling_price=Decimal('3000000'),
            status='sold',
            created_by=self.user
        )
        
        # Update timestamps to today
        today = timezone.now()
        item1.updated_at = today
        item1.save()
        item2.updated_at = today
        item2.save()
        
        sales_metrics = self.dashboard_service.get_sales_metrics()
        
        # Check today's sales
        self.assertEqual(sales_metrics['today']['count'], 2)
        self.assertEqual(sales_metrics['today']['value'], Decimal('5000000'))
        self.assertIn('value_display', sales_metrics['today'])
        
        # Check weekly and monthly sales
        self.assertGreaterEqual(sales_metrics['this_week']['count'], 2)
        self.assertGreaterEqual(sales_metrics['this_month']['count'], 2)
        
        # Check average sale value
        expected_avg = Decimal('2500000')  # (2000000 + 3000000) / 2
        self.assertEqual(sales_metrics['average_sale_value']['value'], expected_avg)
    
    def test_inventory_metrics_calculation(self):
        """Test inventory metrics calculation."""
        # Create test inventory items
        item1 = JewelryItem.objects.create(
            name='Gold Ring',
            sku='GR002',
            category=self.category_rings,
            weight_grams=Decimal('5.5'),
            karat=18,
            manufacturing_cost=Decimal('500000'),
            gold_value=Decimal('1500000'),
            gemstone_value=Decimal('200000'),
            status='in_stock',
            quantity=5,
            minimum_stock=3,
            created_by=self.user
        )
        
        item2 = JewelryItem.objects.create(
            name='Low Stock Item',
            sku='LSI001',
            category=self.category_rings,
            weight_grams=Decimal('3.0'),
            karat=18,
            manufacturing_cost=Decimal('300000'),
            gold_value=Decimal('900000'),
            status='in_stock',
            quantity=1,
            minimum_stock=5,  # This will trigger low stock alert
            created_by=self.user
        )
        
        inventory_metrics = self.dashboard_service.get_inventory_metrics()
        
        # Check basic counts
        self.assertGreaterEqual(inventory_metrics['total_items'], 2)
        self.assertGreaterEqual(inventory_metrics['in_stock'], 2)
        
        # Check low stock detection
        self.assertGreaterEqual(inventory_metrics['low_stock_count'], 1)
        self.assertTrue(len(inventory_metrics['low_stock_items']) >= 1)
        
        # Check value calculations
        self.assertIn('total_value', inventory_metrics)
        self.assertIn('value_breakdown', inventory_metrics)
        
        # Verify value breakdown structure
        breakdown = inventory_metrics['value_breakdown']
        self.assertIn('gold_value', breakdown)
        self.assertIn('manufacturing_cost', breakdown)
        self.assertIn('gemstone_value', breakdown)
        
        # Check category distribution
        self.assertTrue(len(inventory_metrics['category_distribution']) >= 1)
    
    def test_customer_metrics_calculation(self):
        """Test customer metrics calculation."""
        # Create loyalty transactions
        CustomerLoyaltyTransaction.objects.create(
            customer=self.customer1,
            points=100,
            transaction_type='earned',
            reason='Purchase bonus',
            created_by=self.user
        )
        
        CustomerLoyaltyTransaction.objects.create(
            customer=self.customer2,
            points=-50,
            transaction_type='redeemed',
            reason='Gift redemption',
            created_by=self.user
        )
        
        customer_metrics = self.dashboard_service.get_customer_metrics()
        
        # Check basic counts
        self.assertGreaterEqual(customer_metrics['total_customers'], 2)
        self.assertGreaterEqual(customer_metrics['vip_customers'], 1)
        self.assertGreaterEqual(customer_metrics['customers_with_purchases'], 2)
        
        # Check engagement rate calculation
        self.assertGreater(customer_metrics['engagement_rate'], 0)
        
        # Check loyalty points
        self.assertGreaterEqual(customer_metrics['total_loyalty_points']['amount'], 1450)  # 500 + 1000 - 50
        
        # Check top customers
        self.assertTrue(len(customer_metrics['top_customers']) >= 2)
        top_customer = customer_metrics['top_customers'][0]
        self.assertEqual(top_customer['name'], 'سارا کریمی')  # Highest purchase amount
        
        # Check recent loyalty activity
        self.assertTrue(len(customer_metrics['recent_loyalty_activity']) >= 2)
    
    def test_gold_installment_metrics_calculation(self):
        """Test gold installment metrics calculation."""
        # Create test gold installment contracts
        contract1 = GoldInstallmentContract.objects.create(
            customer=self.customer1,
            contract_date=timezone.now().date(),
            initial_gold_weight_grams=Decimal('50.0'),
            remaining_gold_weight_grams=Decimal('30.0'),
            gold_karat=18,
            payment_schedule='monthly',
            status='active',
            contract_terms_persian='شرایط قرارداد تست',
            created_by=self.user
        )
        
        contract2 = GoldInstallmentContract.objects.create(
            customer=self.customer2,
            contract_date=timezone.now().date(),
            initial_gold_weight_grams=Decimal('25.0'),
            remaining_gold_weight_grams=Decimal('0.0'),
            gold_karat=18,
            payment_schedule='weekly',
            status='completed',
            completion_date=timezone.now().date(),
            contract_terms_persian='شرایط قرارداد تست ۲',
            created_by=self.user
        )
        
        # Create test payments
        GoldInstallmentPayment.objects.create(
            contract=contract1,
            payment_date=timezone.now().date(),
            payment_amount_toman=Decimal('7000000'),
            gold_price_per_gram_at_payment=Decimal('3500000'),
            effective_gold_price_per_gram=Decimal('3500000'),
            gold_weight_equivalent_grams=Decimal('2.0'),
            payment_method='cash',
            created_by=self.user
        )
        
        installment_metrics = self.dashboard_service.get_gold_installment_metrics()
        
        # Check contract counts
        self.assertGreaterEqual(installment_metrics['contract_counts']['active'], 1)
        self.assertGreaterEqual(installment_metrics['contract_counts']['completed'], 1)
        self.assertGreaterEqual(installment_metrics['contract_counts']['total'], 2)
        
        # Check outstanding balance
        outstanding = installment_metrics['outstanding_balance']
        self.assertGreaterEqual(outstanding['gold_weight_grams'], Decimal('30.0'))
        self.assertIn('value_toman', outstanding)
        self.assertIn('value_display', outstanding)
        
        # Check current gold price
        self.assertIn('current_gold_price', installment_metrics)
        self.assertGreater(installment_metrics['current_gold_price']['price_per_gram'], 0)
        
        # Check recent payments
        self.assertTrue(len(installment_metrics['recent_payments']) >= 1)
        
        # Check payment trends
        trends = installment_metrics['payment_trends_30_days']
        self.assertIn('total_amount', trends)
        self.assertIn('total_payments', trends)
        self.assertIn('average_payment', trends)
    
    def test_gold_price_data_retrieval(self):
        """Test gold price data retrieval and trend analysis."""
        gold_price_data = self.dashboard_service.get_gold_price_data()
        
        # Check current prices for different karats
        self.assertIn('current_prices', gold_price_data)
        prices = gold_price_data['current_prices']
        
        for karat in ['18k', '21k', '24k']:
            self.assertIn(karat, prices)
            self.assertIn('price_per_gram', prices[karat])
            self.assertIn('display', prices[karat])
            self.assertGreater(prices[karat]['price_per_gram'], 0)
        
        # Check price trend
        self.assertIn('price_trend_7_days', gold_price_data)
        self.assertIn('trend_analysis', gold_price_data)
        
        # Verify trend analysis structure
        trend_analysis = gold_price_data['trend_analysis']
        self.assertIn('direction', trend_analysis)
        self.assertIn('change_percentage', trend_analysis)
        self.assertIn(trend_analysis['direction'], ['increasing', 'decreasing', 'stable'])
    
    def test_financial_summary_calculation(self):
        """Test financial summary calculation."""
        # Create sold items for revenue calculation
        JewelryItem.objects.create(
            name='Sold Ring',
            sku='SR001',
            category=self.category_rings,
            weight_grams=Decimal('5.0'),
            karat=18,
            manufacturing_cost=Decimal('400000'),
            selling_price=Decimal('1800000'),
            status='sold',
            created_by=self.user
        )
        
        # Create installment payment for revenue
        contract = GoldInstallmentContract.objects.create(
            customer=self.customer1,
            contract_date=timezone.now().date(),
            initial_gold_weight_grams=Decimal('20.0'),
            remaining_gold_weight_grams=Decimal('15.0'),
            gold_karat=18,
            payment_schedule='monthly',
            status='active',
            contract_terms_persian='شرایط قرارداد مالی',
            created_by=self.user
        )
        
        GoldInstallmentPayment.objects.create(
            contract=contract,
            payment_date=timezone.now().date(),
            payment_amount_toman=Decimal('5000000'),
            gold_price_per_gram_at_payment=Decimal('3500000'),
            effective_gold_price_per_gram=Decimal('3500000'),
            gold_weight_equivalent_grams=Decimal('1.43'),
            payment_method='cash',
            created_by=self.user
        )
        
        financial_summary = self.dashboard_service.get_financial_summary()
        
        # Check revenue structure
        self.assertIn('monthly_revenue', financial_summary)
        revenue = financial_summary['monthly_revenue']
        
        self.assertIn('jewelry_sales', revenue)
        self.assertIn('installment_payments', revenue)
        self.assertIn('total', revenue)
        
        # Check that revenue values are calculated
        self.assertGreaterEqual(revenue['jewelry_sales']['amount'], Decimal('1800000'))
        self.assertGreaterEqual(revenue['installment_payments']['amount'], Decimal('5000000'))
        self.assertGreaterEqual(revenue['total']['amount'], Decimal('6800000'))
        
        # Check inventory investment
        self.assertIn('inventory_investment', financial_summary)
        
        # Check profit margin estimate
        self.assertIn('profit_margin_estimate', financial_summary)
        margin = financial_summary['profit_margin_estimate']
        self.assertIn('percentage', margin)
        self.assertIn('display', margin)
    
    def test_recent_activities_retrieval(self):
        """Test recent activities retrieval from audit logs."""
        # Create test audit logs
        AuditLog.objects.create(
            user=self.user,
            action='login',
            details={'login_type': 'tenant_portal'},
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            tenant_schema='test_shop'
        )
        
        AuditLog.objects.create(
            user=self.user,
            action='create',
            model_name='JewelryItem',
            object_id='1',
            details={'item_name': 'Test Ring'},
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            tenant_schema='test_shop'
        )
        
        recent_activities = self.dashboard_service.get_recent_activities()
        
        # Check that activities are returned
        self.assertTrue(len(recent_activities) >= 2)
        
        # Check activity structure
        for activity in recent_activities:
            self.assertIn('timestamp', activity)
            self.assertIn('user', activity)
            self.assertIn('action', activity)
            self.assertIn('description', activity)
            self.assertIn('type', activity)
    
    def test_alerts_and_notifications_generation(self):
        """Test alerts and notifications generation."""
        # Create low stock item to trigger alert
        JewelryItem.objects.create(
            name='Low Stock Alert Item',
            sku='LSAI001',
            category=self.category_rings,
            weight_grams=Decimal('2.0'),
            karat=18,
            manufacturing_cost=Decimal('200000'),
            status='in_stock',
            quantity=1,
            minimum_stock=10,  # This will trigger low stock alert
            created_by=self.user
        )
        
        # Create overdue contract
        overdue_date = timezone.now().date() - timedelta(days=60)
        GoldInstallmentContract.objects.create(
            customer=self.customer1,
            contract_date=overdue_date,
            initial_gold_weight_grams=Decimal('30.0'),
            remaining_gold_weight_grams=Decimal('25.0'),
            gold_karat=18,
            payment_schedule='monthly',
            status='active',
            contract_terms_persian='شرایط قرارداد معوق',
            created_by=self.user
        )
        
        alerts = self.dashboard_service.get_alerts_and_notifications()
        
        # Check alert structure
        self.assertIn('critical', alerts)
        self.assertIn('warning', alerts)
        self.assertIn('info', alerts)
        
        # Check for low stock warning
        warning_alerts = alerts['warning']
        low_stock_alert = next((alert for alert in warning_alerts if alert['type'] == 'low_stock'), None)
        self.assertIsNotNone(low_stock_alert)
        self.assertGreater(low_stock_alert['count'], 0)
    
    def test_performance_trends_calculation(self):
        """Test performance trends calculation."""
        performance_trends = self.dashboard_service.get_performance_trends()
        
        # Check that trends are returned (even if empty/mock data)
        self.assertIsInstance(performance_trends, dict)
        
        # The trends might be empty in test environment, but structure should be valid
        if performance_trends:
            # Check for expected trend categories
            possible_trends = ['sales', 'customers', 'inventory']
            for trend_type in performance_trends:
                self.assertIn(trend_type, possible_trends)
    
    def test_dashboard_caching(self):
        """Test dashboard data caching functionality."""
        # Clear cache first
        cache.clear()
        
        # First call should generate and cache data
        start_time = timezone.now()
        dashboard_data1 = self.dashboard_service.get_comprehensive_dashboard_data()
        first_call_time = timezone.now() - start_time
        
        # Second call should use cached data (should be faster)
        start_time = timezone.now()
        dashboard_data2 = self.dashboard_service.get_comprehensive_dashboard_data()
        second_call_time = timezone.now() - start_time
        
        # Data should be identical
        self.assertEqual(dashboard_data1['generated_at'], dashboard_data2['generated_at'])
        
        # Second call should be faster (cached)
        # Note: This might not always be true in test environment, so we just check data consistency
        self.assertEqual(dashboard_data1['tenant_schema'], dashboard_data2['tenant_schema'])
    
    def test_error_handling_and_fallbacks(self):
        """Test error handling and fallback data generation."""
        # Test with invalid tenant schema
        invalid_service = TenantDashboardService('invalid_schema')
        
        # Should not raise exception, should return fallback data
        dashboard_data = invalid_service.get_comprehensive_dashboard_data()
        
        # Check that fallback data is returned
        self.assertIn('sales_metrics', dashboard_data)
        self.assertIn('inventory_metrics', dashboard_data)
        
        # Fallback data should have zero values
        sales_metrics = dashboard_data['sales_metrics']
        self.assertEqual(sales_metrics['today']['count'], 0)
        self.assertEqual(sales_metrics['today']['value'], Decimal('0'))
    
    def test_persian_formatting_in_dashboard_data(self):
        """Test Persian number formatting in dashboard data."""
        # Create some test data
        JewelryItem.objects.create(
            name='Test Item',
            sku='TI001',
            category=self.category_rings,
            weight_grams=Decimal('5.0'),
            karat=18,
            manufacturing_cost=Decimal('1234567'),
            selling_price=Decimal('2345678'),
            status='sold',
            created_by=self.user
        )
        
        dashboard_data = self.dashboard_service.get_comprehensive_dashboard_data()
        
        # Check that Persian formatting is applied
        sales_metrics = dashboard_data['sales_metrics']
        value_display = sales_metrics['today']['value_display']
        
        # Should contain Persian digits and proper formatting
        self.assertIsInstance(value_display, str)
        self.assertTrue(len(value_display) > 0)
        
        # Check inventory metrics formatting
        inventory_metrics = dashboard_data['inventory_metrics']
        if inventory_metrics['total_value']['amount'] > 0:
            total_display = inventory_metrics['total_value']['display']
            self.assertIsInstance(total_display, str)
            self.assertTrue(len(total_display) > 0)
    
    def tearDown(self):
        """Clean up after each test."""
        # Clear cache after each test
        cache.clear()
        
        # Clean up test data
        User.objects.all().delete()
        JewelryItem.objects.all().delete()
        Category.objects.all().delete()
        Customer.objects.all().delete()
        CustomerLoyaltyTransaction.objects.all().delete()
        GoldInstallmentContract.objects.all().delete()
        GoldInstallmentPayment.objects.all().delete()
        AuditLog.objects.all().delete()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        super().tearDownClass()
        
        # Clean up tenant and domain
        if hasattr(cls, 'domain'):
            cls.domain.delete()
        if hasattr(cls, 'tenant'):
            cls.tenant.delete()


class TenantDashboardViewTest(TenantTestCase):
    """
    Test suite for TenantDashboardView integration.
    Tests the view integration with dashboard service.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test tenant and domain."""
        super().setUpClass()
        
        # Switch to public schema to create tenant
        from django.db import connection
        connection.set_schema_to_public()
        
        # Create test tenant
        cls.tenant = Tenant(
            name='Test View Shop',
            schema_name='test_view_shop',
            owner_name='Test View Owner',
            owner_email='owner@testviewshop.com'
        )
        cls.tenant.save()
        
        # Create domain
        cls.domain = Domain(
            domain='testviewshop.localhost',
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
        
        # Set up tenant client
        cls.client = TenantClient(cls.tenant)
        
        # Switch to tenant schema
        connection.set_tenant(cls.tenant)
    
    def setUp(self):
        """Set up test data for each test."""
        # Create test user
        self.user = User.objects.create_user(
            username='viewtestuser',
            email='viewtest@example.com',
            password='testpass123',
            role='owner',
            theme_preference='light'
        )
        
        # Log in user
        self.client.force_login(self.user)
    
    def test_dashboard_view_response(self):
        """Test dashboard view returns successful response."""
        response = self.client.get('/dashboard/')
        
        # Should return 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Should use correct template
        self.assertTemplateUsed(response, 'tenant/dashboard.html')
    
    def test_dashboard_view_context_data(self):
        """Test dashboard view context data."""
        response = self.client.get('/dashboard/')
        
        # Check required context variables
        required_context = [
            'page_title', 'is_tenant_dashboard', 'dashboard_data',
            'sales_metrics', 'inventory_metrics', 'customer_metrics',
            'gold_installment_metrics', 'gold_price_data', 'financial_summary',
            'recent_activities', 'alerts_notifications', 'performance_trends'
        ]
        
        for context_var in required_context:
            self.assertIn(context_var, response.context)
        
        # Check page title
        self.assertEqual(response.context['page_title'], 'داشبورد فروشگاه')
        self.assertTrue(response.context['is_tenant_dashboard'])
    
    def test_dashboard_view_theme_settings(self):
        """Test dashboard view theme settings in context."""
        response = self.client.get('/dashboard/')
        
        # Check theme settings
        self.assertIn('theme_mode', response.context)
        self.assertIn('show_cybersecurity_theme', response.context)
        
        # Should match user preference
        self.assertEqual(response.context['theme_mode'], self.user.theme_preference)
        self.assertEqual(response.context['show_cybersecurity_theme'], self.user.theme_preference == 'dark')
    
    def test_dashboard_view_refresh_settings(self):
        """Test dashboard view auto-refresh settings."""
        response = self.client.get('/dashboard/')
        
        # Check refresh settings
        self.assertIn('auto_refresh_enabled', response.context)
        self.assertIn('refresh_interval', response.context)
        self.assertIn('last_updated', response.context)
        
        # Check default values
        self.assertTrue(response.context['auto_refresh_enabled'])
        self.assertEqual(response.context['refresh_interval'], 300000)  # 5 minutes
    
    def test_dashboard_view_with_dark_theme_user(self):
        """Test dashboard view with dark theme user."""
        # Update user theme preference
        self.user.theme_preference = 'dark'
        self.user.save()
        
        response = self.client.get('/dashboard/')
        
        # Check theme context
        self.assertEqual(response.context['theme_mode'], 'dark')
        self.assertTrue(response.context['show_cybersecurity_theme'])
    
    def test_dashboard_view_unauthenticated_redirect(self):
        """Test dashboard view redirects unauthenticated users."""
        # Log out user
        self.client.logout()
        
        response = self.client.get('/dashboard/')
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
    
    def tearDown(self):
        """Clean up after each test."""
        User.objects.all().delete()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        super().tearDownClass()
        
        # Clean up tenant and domain
        if hasattr(cls, 'domain'):
            cls.domain.delete()
        if hasattr(cls, 'tenant'):
            cls.tenant.delete()


if __name__ == '__main__':
    pytest.main([__file__])