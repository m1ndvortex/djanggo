"""
Unit tests for dashboard service functionality.
Tests dashboard service methods without complex tenant setup.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.cache import cache
from unittest.mock import Mock, patch, MagicMock

from zargar.core.dashboard_services import TenantDashboardService


class TenantDashboardServiceUnitTest(TestCase):
    """
    Unit test suite for TenantDashboardService.
    Tests individual methods and functionality without database dependencies.
    """
    
    def setUp(self):
        """Set up test data for each test."""
        # Clear cache before each test
        cache.clear()
        
        # Initialize dashboard service
        self.dashboard_service = TenantDashboardService('test_tenant')
    
    def test_dashboard_service_initialization(self):
        """Test dashboard service initialization."""
        service = TenantDashboardService('test_tenant')
        
        self.assertEqual(service.tenant_schema, 'test_tenant')
        self.assertIsNotNone(service.formatter)
        self.assertIsNotNone(service.calendar_utils)
    
    def test_get_fallback_dashboard_data(self):
        """Test fallback dashboard data generation."""
        fallback_data = self.dashboard_service._get_fallback_dashboard_data()
        
        # Check all required sections are present
        required_sections = [
            'sales_metrics', 'inventory_metrics', 'customer_metrics',
            'gold_installment_metrics', 'gold_price_data', 'financial_summary',
            'recent_activities', 'alerts_and_notifications', 'performance_trends'
        ]
        
        for section in required_sections:
            self.assertIn(section, fallback_data)
        
        # Check metadata
        self.assertIn('generated_at', fallback_data)
        self.assertEqual(fallback_data['tenant_schema'], 'test_tenant')
        self.assertTrue(fallback_data['error'])
    
    def test_get_fallback_sales_metrics(self):
        """Test fallback sales metrics structure."""
        sales_metrics = self.dashboard_service._get_fallback_sales_metrics()
        
        # Check required structure
        required_keys = ['today', 'this_week', 'this_month', 'average_sale_value']
        for key in required_keys:
            self.assertIn(key, sales_metrics)
        
        # Check that all values are zero/empty
        self.assertEqual(sales_metrics['today']['count'], 0)
        self.assertEqual(sales_metrics['today']['value'], Decimal('0'))
        self.assertEqual(sales_metrics['today']['value_display'], '۰ تومان')
        
        # Check lists are empty
        self.assertEqual(sales_metrics['top_selling_categories'], [])
        self.assertEqual(sales_metrics['sales_trend'], [])
    
    def test_get_fallback_inventory_metrics(self):
        """Test fallback inventory metrics structure."""
        inventory_metrics = self.dashboard_service._get_fallback_inventory_metrics()
        
        # Check basic counts
        self.assertEqual(inventory_metrics['total_items'], 0)
        self.assertEqual(inventory_metrics['in_stock'], 0)
        self.assertEqual(inventory_metrics['sold'], 0)
        self.assertEqual(inventory_metrics['reserved'], 0)
        self.assertEqual(inventory_metrics['low_stock_count'], 0)
        
        # Check value structure
        self.assertIn('total_value', inventory_metrics)
        self.assertEqual(inventory_metrics['total_value']['amount'], Decimal('0'))
        self.assertEqual(inventory_metrics['total_value']['display'], '۰ تومان')
        
        # Check value breakdown
        breakdown = inventory_metrics['value_breakdown']
        self.assertIn('gold_value', breakdown)
        self.assertIn('manufacturing_cost', breakdown)
        self.assertIn('gemstone_value', breakdown)
        
        # Check lists are empty
        self.assertEqual(inventory_metrics['low_stock_items'], [])
        self.assertEqual(inventory_metrics['category_distribution'], [])
    
    def test_get_fallback_customer_metrics(self):
        """Test fallback customer metrics structure."""
        customer_metrics = self.dashboard_service._get_fallback_customer_metrics()
        
        # Check basic counts
        self.assertEqual(customer_metrics['total_customers'], 0)
        self.assertEqual(customer_metrics['vip_customers'], 0)
        self.assertEqual(customer_metrics['new_customers_this_month'], 0)
        self.assertEqual(customer_metrics['customers_with_purchases'], 0)
        self.assertEqual(customer_metrics['engagement_rate'], 0)
        
        # Check loyalty points
        self.assertEqual(customer_metrics['total_loyalty_points']['amount'], 0)
        self.assertEqual(customer_metrics['total_loyalty_points']['display'], '۰')
        
        # Check lists are empty
        self.assertEqual(customer_metrics['top_customers'], [])
        self.assertEqual(customer_metrics['birthday_customers_this_month'], [])
        self.assertEqual(customer_metrics['recent_loyalty_activity'], [])
    
    def test_get_fallback_gold_installment_metrics(self):
        """Test fallback gold installment metrics structure."""
        installment_metrics = self.dashboard_service._get_fallback_gold_installment_metrics()
        
        # Check contract counts
        counts = installment_metrics['contract_counts']
        self.assertEqual(counts['active'], 0)
        self.assertEqual(counts['completed'], 0)
        self.assertEqual(counts['defaulted'], 0)
        self.assertEqual(counts['total'], 0)
        
        # Check outstanding balance
        balance = installment_metrics['outstanding_balance']
        self.assertEqual(balance['gold_weight_grams'], Decimal('0'))
        self.assertEqual(balance['gold_weight_display'], '۰ گرم')
        self.assertEqual(balance['value_toman'], Decimal('0'))
        self.assertEqual(balance['value_display'], '۰ تومان')
        
        # Check current gold price (should have fallback value)
        gold_price = installment_metrics['current_gold_price']
        self.assertEqual(gold_price['price_per_gram'], Decimal('3500000'))
        self.assertIn('display', gold_price)
        
        # Check lists are empty
        self.assertEqual(installment_metrics['overdue_contracts']['count'], 0)
        self.assertEqual(installment_metrics['overdue_contracts']['contracts'], [])
        self.assertEqual(installment_metrics['recent_payments'], [])
    
    def test_get_fallback_gold_price_data(self):
        """Test fallback gold price data structure."""
        gold_price_data = self.dashboard_service._get_fallback_gold_price_data()
        
        # Check current prices for different karats
        prices = gold_price_data['current_prices']
        for karat in ['18k', '21k', '24k']:
            self.assertIn(karat, prices)
            self.assertIn('price_per_gram', prices[karat])
            self.assertIn('display', prices[karat])
            self.assertGreater(prices[karat]['price_per_gram'], 0)
        
        # Check 18k price (base fallback)
        self.assertEqual(prices['18k']['price_per_gram'], Decimal('3500000'))
        self.assertEqual(prices['18k']['source'], 'fallback')
        
        # Check trend data
        self.assertEqual(gold_price_data['price_trend_7_days'], [])
        
        # Check trend analysis
        trend_analysis = gold_price_data['trend_analysis']
        self.assertEqual(trend_analysis['direction'], 'stable')
        self.assertEqual(trend_analysis['change_percentage'], Decimal('0'))
        self.assertEqual(trend_analysis['change_display'], '۰٪')
    
    def test_get_fallback_financial_summary(self):
        """Test fallback financial summary structure."""
        financial_summary = self.dashboard_service._get_fallback_financial_summary()
        
        # Check monthly revenue structure
        revenue = financial_summary['monthly_revenue']
        self.assertIn('jewelry_sales', revenue)
        self.assertIn('installment_payments', revenue)
        self.assertIn('total', revenue)
        
        # Check all revenue values are zero
        self.assertEqual(revenue['jewelry_sales']['amount'], Decimal('0'))
        self.assertEqual(revenue['installment_payments']['amount'], Decimal('0'))
        self.assertEqual(revenue['total']['amount'], Decimal('0'))
        
        # Check inventory investment
        self.assertEqual(financial_summary['inventory_investment']['amount'], Decimal('0'))
        
        # Check profit margin
        margin = financial_summary['profit_margin_estimate']
        self.assertEqual(margin['percentage'], Decimal('0'))
        self.assertEqual(margin['display'], '۰٪')
        self.assertEqual(margin['profit_amount']['value'], Decimal('0'))
    
    def test_format_activity_description(self):
        """Test activity description formatting."""
        # Mock audit log object
        mock_log = Mock()
        mock_log.action = 'login'
        mock_log.model_name = None
        
        description = self.dashboard_service._format_activity_description(mock_log)
        self.assertEqual(description, 'ورود به سیستم')
        
        # Test with model name
        mock_log.action = 'create'
        mock_log.model_name = 'JewelryItem'
        
        description = self.dashboard_service._format_activity_description(mock_log)
        self.assertEqual(description, 'ایجاد رکورد جدید در JewelryItem')
    
    def test_categorize_activity(self):
        """Test activity categorization."""
        # Test authentication activities
        self.assertEqual(self.dashboard_service._categorize_activity('login'), 'authentication')
        self.assertEqual(self.dashboard_service._categorize_activity('logout'), 'authentication')
        
        # Test data modification activities
        self.assertEqual(self.dashboard_service._categorize_activity('create'), 'data_modification')
        self.assertEqual(self.dashboard_service._categorize_activity('update'), 'data_modification')
        self.assertEqual(self.dashboard_service._categorize_activity('delete'), 'data_modification')
        
        # Test general activities
        self.assertEqual(self.dashboard_service._categorize_activity('view'), 'general')
        self.assertEqual(self.dashboard_service._categorize_activity('unknown'), 'general')
    
    def test_analyze_price_trend(self):
        """Test gold price trend analysis."""
        # Test with empty trend data
        empty_trend = []
        analysis = self.dashboard_service._analyze_price_trend(empty_trend)
        self.assertEqual(analysis['direction'], 'stable')
        self.assertEqual(analysis['change_percentage'], 0)
        
        # Test with single data point
        single_trend = [{'price_per_gram': Decimal('3500000')}]
        analysis = self.dashboard_service._analyze_price_trend(single_trend)
        self.assertEqual(analysis['direction'], 'stable')
        
        # Test with increasing trend
        increasing_trend = [
            {'price_per_gram': Decimal('3000000')},
            {'price_per_gram': Decimal('3500000')}
        ]
        analysis = self.dashboard_service._analyze_price_trend(increasing_trend)
        self.assertEqual(analysis['direction'], 'increasing')
        self.assertGreater(analysis['change_percentage'], 1)
        
        # Test with decreasing trend
        decreasing_trend = [
            {'price_per_gram': Decimal('4000000')},
            {'price_per_gram': Decimal('3500000')}
        ]
        analysis = self.dashboard_service._analyze_price_trend(decreasing_trend)
        self.assertEqual(analysis['direction'], 'decreasing')
        self.assertLess(analysis['change_percentage'], -1)
        
        # Test with stable trend (small change)
        stable_trend = [
            {'price_per_gram': Decimal('3500000')},
            {'price_per_gram': Decimal('3510000')}
        ]
        analysis = self.dashboard_service._analyze_price_trend(stable_trend)
        self.assertEqual(analysis['direction'], 'stable')
    
    def test_calculate_profit_margin_estimate(self):
        """Test profit margin calculation."""
        # Test with zero revenue
        margin = self.dashboard_service._calculate_profit_margin_estimate(Decimal('0'), Decimal('1000'))
        self.assertEqual(margin['percentage'], 0)
        self.assertEqual(margin['display'], '۰٪')
        
        # Test with positive profit
        revenue = Decimal('10000000')
        costs = Decimal('6000000')
        margin = self.dashboard_service._calculate_profit_margin_estimate(revenue, costs)
        
        expected_percentage = Decimal('40.00')  # (10M - 6M) / 10M * 100
        self.assertEqual(margin['percentage'], expected_percentage)
        self.assertEqual(margin['profit_amount']['value'], Decimal('4000000'))
        
        # Test with loss (negative profit)
        revenue = Decimal('5000000')
        costs = Decimal('8000000')
        margin = self.dashboard_service._calculate_profit_margin_estimate(revenue, costs)
        
        expected_percentage = Decimal('-60.00')  # (5M - 8M) / 5M * 100
        self.assertEqual(margin['percentage'], expected_percentage)
        self.assertEqual(margin['profit_amount']['value'], Decimal('-3000000'))
    
    @patch('zargar.core.dashboard_services.TenantDashboardService.get_sales_metrics')
    def test_comprehensive_dashboard_data_with_error(self, mock_sales_metrics):
        """Test comprehensive dashboard data with error handling."""
        # Mock an exception in sales metrics
        mock_sales_metrics.side_effect = Exception("Database error")
        
        dashboard_data = self.dashboard_service.get_comprehensive_dashboard_data()
        
        # Should return fallback data
        self.assertTrue(dashboard_data.get('error', False))
        self.assertIn('sales_metrics', dashboard_data)
        
        # Sales metrics should be fallback data
        sales_metrics = dashboard_data['sales_metrics']
        self.assertEqual(sales_metrics['today']['count'], 0)
    
    def test_dashboard_caching_key_generation(self):
        """Test dashboard caching functionality."""
        # Clear cache first
        cache.clear()
        
        # Test cache key generation
        cache_key = f"dashboard_data_{self.dashboard_service.tenant_schema}"
        expected_key = "dashboard_data_test_tenant"
        self.assertEqual(cache_key, expected_key)
        
        # Test cache storage and retrieval
        test_data = {'test': 'data', 'timestamp': timezone.now()}
        cache.set(cache_key, test_data, 300)
        
        cached_data = cache.get(cache_key)
        self.assertEqual(cached_data['test'], 'data')
    
    def test_persian_number_formatting_integration(self):
        """Test Persian number formatting integration."""
        # Test currency formatting
        amount = Decimal('1234567')
        formatted = self.dashboard_service.formatter.format_currency(amount, use_persian_digits=True)
        
        # Should be a string with Persian formatting
        self.assertIsInstance(formatted, str)
        self.assertTrue(len(formatted) > 0)
        
        # Test weight formatting
        weight = Decimal('12.345')
        formatted_weight = self.dashboard_service.formatter.format_weight(
            weight, 'gram', use_persian_digits=True
        )
        
        self.assertIsInstance(formatted_weight, str)
        self.assertTrue(len(formatted_weight) > 0)
    
    def tearDown(self):
        """Clean up after each test."""
        # Clear cache after each test
        cache.clear()


if __name__ == '__main__':
    pytest.main([__file__])