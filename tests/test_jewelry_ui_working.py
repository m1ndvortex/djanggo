"""
Working tests for jewelry inventory management UI functionality.
These tests verify that Task 14.2 is working correctly.
"""
import json
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch

from zargar.jewelry.models import JewelryItem, Category
from zargar.jewelry.services import (
    SerialNumberTrackingService, 
    StockAlertService, 
    InventoryValuationService
)

User = get_user_model()


class InventoryUIWorkingTest(TestCase):
    """
    Working test case for inventory management UI - Task 14.2.
    """
    
    def setUp(self):
        """Set up test data for each test."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Rings',
            name_persian='انگشتر',
            description='Test rings category'
        )
        
        # Create test jewelry item
        self.jewelry_item = JewelryItem.objects.create(
            name='Test Gold Ring',
            sku='TEST001',
            category=self.category,
            weight_grams=Decimal('5.500'),
            karat=18,
            manufacturing_cost=Decimal('1000000'),
            gemstone_value=Decimal('500000'),
            selling_price=Decimal('5000000'),
            quantity=10,
            minimum_stock=2,
            description='Test jewelry item',
            barcode='TEST001_BARCODE'
        )
        
        # Login user
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_inventory_dashboard_loads(self):
        """Test that inventory dashboard loads without errors."""
        with patch('zargar.jewelry.views.StockAlertService.get_stock_alerts_summary') as mock_alerts, \
             patch('zargar.jewelry.views.InventoryValuationService.calculate_total_inventory_value') as mock_valuation:
            
            # Mock service responses
            mock_alerts.return_value = {
                'total_low_stock_items': 0,
                'critical_items': 0,
                'out_of_stock_items': 0,
                'total_value_at_risk': 0,
                'category_breakdown': {}
            }
            
            mock_valuation.return_value = {
                'total_items': 1,
                'total_current_value': 5000000,
                'gold_value_change': 0,
                'gold_value_change_percentage': 0
            }
            
            url = reverse('jewelry:dashboard')
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'داشبورد موجودی')
    
    def test_inventory_list_loads(self):
        """Test that inventory list view loads and shows items."""
        url = reverse('jewelry:inventory_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'فهرست موجودی')
        self.assertContains(response, 'Test Gold Ring')
    
    def test_inventory_detail_loads(self):
        """Test that inventory detail view loads correctly."""
        url = reverse('jewelry:inventory_detail', kwargs={'pk': self.jewelry_item.pk})
        
        with patch('zargar.jewelry.views.SerialNumberTrackingService.assign_serial_number') as mock_serial:
            mock_serial.return_value = {'success': False, 'requires_high_value': True}
            
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Test Gold Ring')
            self.assertContains(response, 'TEST001')
    
    def test_inventory_create_form_loads(self):
        """Test that inventory create form loads correctly."""
        url = reverse('jewelry:inventory_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'افزودن کالای جدید')
        self.assertContains(response, 'نام کالا')
    
    def test_inventory_edit_form_loads(self):
        """Test that inventory update form loads correctly."""
        url = reverse('jewelry:inventory_edit', kwargs={'pk': self.jewelry_item.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ویرایش کالا')
        self.assertContains(response, 'Test Gold Ring')
    
    def test_category_management_loads(self):
        """Test that category management view loads correctly."""
        url = reverse('jewelry:category_management')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مدیریت دسته‌بندی‌ها')
        self.assertContains(response, 'انگشتر')
    
    def test_stock_alerts_loads(self):
        """Test that stock alerts view loads correctly."""
        with patch('zargar.jewelry.views.StockAlertService.get_stock_alerts_summary') as mock_summary, \
             patch('zargar.jewelry.views.StockAlertService.get_low_stock_items') as mock_items, \
             patch('zargar.jewelry.views.StockAlertService.create_reorder_suggestions') as mock_suggestions:
            
            mock_summary.return_value = {
                'total_low_stock_items': 0,
                'critical_items': 0,
                'out_of_stock_items': 0,
                'total_value_at_risk': 0,
                'category_breakdown': {}
            }
            mock_items.return_value = []
            mock_suggestions.return_value = []
            
            url = reverse('jewelry:stock_alerts')
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'هشدارهای موجودی')
    
    def test_inventory_valuation_loads(self):
        """Test that inventory valuation view loads correctly."""
        with patch('zargar.jewelry.views.InventoryValuationService.calculate_total_inventory_value') as mock_valuation:
            mock_valuation.return_value = {
                'total_items': 1,
                'total_gold_weight_grams': Decimal('5.500'),
                'total_current_value': 5000000,
                'gold_value_change': 0,
                'gold_value_change_percentage': 0,
                'gold_prices_used': {18: 2500000},
                'calculation_timestamp': '2024-01-01 12:00:00',
                'karat_breakdown': {},
                'category_breakdown': {}
            }
            
            url = reverse('jewelry:inventory_valuation')
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'ارزیابی موجودی')
    
    def test_inventory_search_api(self):
        """Test inventory search API endpoint."""
        url = reverse('jewelry:inventory_search_api')
        
        # Test search
        response = self.client.get(url, {'q': 'Test', 'limit': 10})
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) > 0)
        self.assertEqual(data['results'][0]['name'], 'Test Gold Ring')
    
    def test_create_category_api(self):
        """Test category creation API."""
        url = reverse('jewelry:create_category')
        
        data = {
            'name': 'Necklaces',
            'name_persian': 'گردنبند',
            'description': 'Test necklaces category',
            'is_active': True
        }
        
        response = self.client.post(
            url,
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Check category was created
        new_category = Category.objects.get(name='Necklaces')
        self.assertEqual(new_category.name_persian, 'گردنبند')
        self.assertTrue(new_category.is_active)


class InventoryServicesWorkingTest(TestCase):
    """
    Test inventory services functionality.
    """
    
    def setUp(self):
        """Set up test data."""
        self.category = Category.objects.create(
            name='Rings',
            name_persian='انگشتر'
        )
        
        self.jewelry_item = JewelryItem.objects.create(
            name='Test Ring',
            sku='TEST001',
            category=self.category,
            weight_grams=Decimal('5.000'),
            karat=18,
            manufacturing_cost=Decimal('1000000'),
            selling_price=Decimal('5000000'),
            quantity=1,  # Low stock
            minimum_stock=3,
            barcode='TEST001_SERVICE_BARCODE'
        )
    
    def test_serial_number_validation(self):
        """Test serial number generation service."""
        # Test serial number format validation
        result = SerialNumberTrackingService.validate_serial_number('ZRG-2024-RIN-0001')
        self.assertTrue(result['valid'])
        
        # Test invalid format
        result = SerialNumberTrackingService.validate_serial_number('INVALID')
        self.assertFalse(result['valid'])
    
    def test_stock_alert_detection(self):
        """Test stock alert service functionality."""
        # Get low stock items
        low_stock_items = StockAlertService.get_low_stock_items()
        
        # Should include our test item (quantity 1 <= minimum_stock 3)
        self.assertTrue(len(low_stock_items) > 0)
        
        # Check that our item is in the list
        item_names = [item['item'].name for item in low_stock_items]
        self.assertIn('Test Ring', item_names)
    
    def test_inventory_valuation_calculation(self):
        """Test inventory valuation service."""
        with patch('zargar.gold_installments.services.GoldPriceService.get_current_gold_price') as mock_price:
            mock_price.return_value = {'price_per_gram': Decimal('2500000')}
            
            valuation = InventoryValuationService.calculate_total_inventory_value()
            
            self.assertIn('total_items', valuation)
            self.assertIn('total_current_value', valuation)
            self.assertEqual(valuation['total_items'], 1)


if __name__ == '__main__':
    print("🧪 Running Task 14.2 - Inventory Management UI Tests")
    print("=" * 60)
    
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['tests.test_jewelry_ui_working'])
    
    if failures == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Task 14.2 - Inventory Management UI is working correctly!")
    else:
        print(f"\n❌ {failures} test(s) failed")