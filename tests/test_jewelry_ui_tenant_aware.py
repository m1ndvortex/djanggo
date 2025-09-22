"""
Tenant-aware tests for jewelry inventory management UI functionality.
Tests the core functionality with proper tenant setup for task 14.2.
"""
import json
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context

from zargar.tenants.models import Tenant, Domain
from zargar.jewelry.models import JewelryItem, Category, Gemstone, JewelryItemPhoto
from zargar.jewelry.services import (
    SerialNumberTrackingService, 
    StockAlertService, 
    InventoryValuationService
)

User = get_user_model()


class InventoryUITenantAwareTest(TenantTestCase):
    """
    Tenant-aware test case for inventory management UI.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up tenant for testing."""
        # Set up the tenant first
        cls.tenant = Tenant(
            schema_name='test_jewelry_ui',
            name='Test Jewelry UI Shop',
            owner_name='Test Owner',
            owner_email='test@example.com',
            is_active=True
        )
        
        # Create domain for tenant
        cls.domain = Domain(
            domain='testui.localhost',
            tenant=cls.tenant,
            is_primary=True
        )
        
        # Call parent setUpClass which will save the tenant
        super().setUpClass()
    
    def setUp(self):
        """Set up test data for each test."""
        # Set tenant context
        self.tenant = self.__class__.tenant
        
        # Create test data within tenant schema
        with schema_context(self.tenant.schema_name):
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
                description='Test jewelry item'
            )
        
        # Set up client with tenant
        self.client = Client(HTTP_HOST='testui.localhost')
        self.client.login(username='testuser', password='testpass123')
    
    def test_inventory_dashboard_view_loads(self):
        """Test that inventory dashboard loads without errors."""
        with schema_context(self.tenant.schema_name):
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
    
    def test_inventory_list_view_loads(self):
        """Test that inventory list view loads and shows items."""
        with schema_context(self.tenant.schema_name):
            url = reverse('jewelry:inventory_list')
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'فهرست موجودی')
            self.assertContains(response, 'Test Gold Ring')
    
    def test_inventory_list_search_functionality(self):
        """Test search functionality in inventory list."""
        with schema_context(self.tenant.schema_name):
            url = reverse('jewelry:inventory_list')
            
            # Test search by name
            response = self.client.get(url, {'search': 'Test'})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Test Gold Ring')
            
            # Test search by SKU
            response = self.client.get(url, {'search': 'TEST001'})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Test Gold Ring')
            
            # Test search with no results
            response = self.client.get(url, {'search': 'NonExistent'})
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'Test Gold Ring')
    
    def test_inventory_list_filtering(self):
        """Test filtering functionality in inventory list."""
        with schema_context(self.tenant.schema_name):
            url = reverse('jewelry:inventory_list')
            
            # Test category filter
            response = self.client.get(url, {'category': self.category.id})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Test Gold Ring')
            
            # Test status filter
            response = self.client.get(url, {'status': 'in_stock'})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Test Gold Ring')
            
            # Test karat filter
            response = self.client.get(url, {'karat': '18'})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Test Gold Ring')
    
    def test_inventory_detail_view_loads(self):
        """Test that inventory detail view loads correctly."""
        with schema_context(self.tenant.schema_name):
            url = reverse('jewelry:inventory_detail', kwargs={'pk': self.jewelry_item.pk})
            
            with patch('zargar.jewelry.views.SerialNumberTrackingService.assign_serial_number') as mock_serial:
                mock_serial.return_value = {'success': False, 'requires_high_value': True}
                
                response = self.client.get(url)
                
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Test Gold Ring')
                self.assertContains(response, 'TEST001')
                self.assertContains(response, '18 عیار')
    
    def test_inventory_create_view_loads(self):
        """Test that inventory create form loads correctly."""
        with schema_context(self.tenant.schema_name):
            url = reverse('jewelry:inventory_create')
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'افزودن کالای جدید')
            self.assertContains(response, 'نام کالا')
            self.assertContains(response, 'کد کالا')
    
    def test_inventory_create_form_submission(self):
        """Test inventory item creation through form."""
        with schema_context(self.tenant.schema_name):
            url = reverse('jewelry:inventory_create')
            
            data = {
                'name': 'New Test Ring',
                'sku': 'TEST002',
                'category': self.category.id,
                'weight_grams': '3.250',
                'karat': 21,
                'manufacturing_cost': '800000',
                'gemstone_value': '300000',
                'selling_price': '3500000',
                'quantity': 5,
                'minimum_stock': 1,
                'description': 'New test ring description'
            }
            
            with patch('zargar.jewelry.views.SerialNumberTrackingService.assign_serial_number') as mock_serial:
                mock_serial.return_value = {'success': False}
                
                response = self.client.post(url, data)
                
                # Should redirect to detail view
                self.assertEqual(response.status_code, 302)
                
                # Check item was created
                new_item = JewelryItem.objects.get(sku='TEST002')
                self.assertEqual(new_item.name, 'New Test Ring')
                self.assertEqual(new_item.karat, 21)
                self.assertEqual(new_item.quantity, 5)
    
    def test_inventory_update_view_loads(self):
        """Test that inventory update form loads correctly."""
        with schema_context(self.tenant.schema_name):
            url = reverse('jewelry:inventory_edit', kwargs={'pk': self.jewelry_item.pk})
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'ویرایش کالا')
            self.assertContains(response, 'Test Gold Ring')
    
    def test_inventory_update_form_submission(self):
        """Test inventory item update through form."""
        with schema_context(self.tenant.schema_name):
            url = reverse('jewelry:inventory_edit', kwargs={'pk': self.jewelry_item.pk})
            
            data = {
                'name': 'Updated Test Ring',
                'sku': 'TEST001',
                'category': self.category.id,
                'weight_grams': '6.000',
                'karat': 18,
                'manufacturing_cost': '1200000',
                'gemstone_value': '600000',
                'selling_price': '5500000',
                'quantity': 8,
                'minimum_stock': 2,
                'status': 'in_stock',
                'description': 'Updated description'
            }
            
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, 302)
            
            # Check item was updated
            updated_item = JewelryItem.objects.get(pk=self.jewelry_item.pk)
            self.assertEqual(updated_item.name, 'Updated Test Ring')
            self.assertEqual(updated_item.weight_grams, Decimal('6.000'))
            self.assertEqual(updated_item.quantity, 8)
    
    def test_category_management_view_loads(self):
        """Test that category management view loads correctly."""
        with schema_context(self.tenant.schema_name):
            url = reverse('jewelry:category_management')
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'مدیریت دسته‌بندی‌ها')
            self.assertContains(response, 'انگشتر')
    
    def test_stock_alerts_view_loads(self):
        """Test that stock alerts view loads correctly."""
        with schema_context(self.tenant.schema_name):
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
    
    def test_inventory_valuation_view_loads(self):
        """Test that inventory valuation view loads correctly."""
        with schema_context(self.tenant.schema_name):
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
        with schema_context(self.tenant.schema_name):
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
        with schema_context(self.tenant.schema_name):
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
    
    def test_template_rendering_with_persian_content(self):
        """Test that templates render Persian content correctly."""
        with schema_context(self.tenant.schema_name):
            url = reverse('jewelry:dashboard')
            
            with patch('zargar.jewelry.views.StockAlertService.get_stock_alerts_summary') as mock_alerts, \
                 patch('zargar.jewelry.views.InventoryValuationService.calculate_total_inventory_value') as mock_valuation:
                
                mock_alerts.return_value = {'total_low_stock_items': 0, 'critical_items': 0, 'out_of_stock_items': 0, 'total_value_at_risk': 0, 'category_breakdown': {}}
                mock_valuation.return_value = {'total_items': 1, 'total_current_value': 5000000, 'gold_value_change': 0, 'gold_value_change_percentage': 0}
                
                response = self.client.get(url)
                
                # Check for Persian text
                self.assertContains(response, 'داشبورد موجودی')
                self.assertContains(response, 'تعداد کل کالاها')
                self.assertContains(response, 'ارزش کل موجودی')
    
    def test_permission_based_ui_elements(self):
        """Test that UI elements respect user permissions."""
        with schema_context(self.tenant.schema_name):
            # Test with owner role (should have edit permissions)
            url = reverse('jewelry:inventory_detail', kwargs={'pk': self.jewelry_item.pk})
            
            with patch('zargar.jewelry.views.SerialNumberTrackingService.assign_serial_number') as mock_serial:
                mock_serial.return_value = {'success': False, 'requires_high_value': True}
                
                response = self.client.get(url)
                self.assertTrue(response.context['can_edit'])
                self.assertTrue(response.context['can_delete'])
            
            # Test with salesperson role (limited permissions)
            salesperson = User.objects.create_user(
                username='salesperson',
                email='sales@example.com',
                password='testpass123',
                role='salesperson'
            )
            
            self.client.logout()
            self.client.login(username='salesperson', password='testpass123')
            
            with patch('zargar.jewelry.views.SerialNumberTrackingService.assign_serial_number') as mock_serial:
                mock_serial.return_value = {'success': False, 'requires_high_value': True}
                
                response = self.client.get(url)
                self.assertFalse(response.context['can_edit'])
                self.assertFalse(response.context['can_delete'])


class InventoryServicesTenantAwareTest(TenantTestCase):
    """
    Test inventory services functionality with tenant support.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up tenant for testing."""
        # Set up the tenant first
        cls.tenant = Tenant(
            schema_name='test_services_ui',
            name='Test Services UI Shop',
            owner_name='Test Owner',
            owner_email='test@example.com',
            is_active=True
        )
        
        # Create domain for tenant
        cls.domain = Domain(
            domain='servicesui.localhost',
            tenant=cls.tenant,
            is_primary=True
        )
        
        # Call parent setUpClass which will save the tenant
        super().setUpClass()
    
    def setUp(self):
        """Set up test data."""
        # Set tenant context
        self.tenant = self.__class__.tenant
        
        with schema_context(self.tenant.schema_name):
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
                minimum_stock=3
            )
    
    def test_serial_number_generation(self):
        """Test serial number generation service."""
        with schema_context(self.tenant.schema_name):
            # Test serial number format validation
            result = SerialNumberTrackingService.validate_serial_number('ZRG-2024-RIN-0001')
            self.assertTrue(result['valid'])
            
            # Test invalid format
            result = SerialNumberTrackingService.validate_serial_number('INVALID')
            self.assertFalse(result['valid'])
    
    def test_stock_alert_service(self):
        """Test stock alert service functionality."""
        with schema_context(self.tenant.schema_name):
            # Get low stock items
            low_stock_items = StockAlertService.get_low_stock_items()
            
            # Should include our test item (quantity 1 <= minimum_stock 3)
            self.assertTrue(len(low_stock_items) > 0)
            
            # Check that our item is in the list
            item_names = [item['item'].name for item in low_stock_items]
            self.assertIn('Test Ring', item_names)
    
    def test_inventory_valuation_service(self):
        """Test inventory valuation service."""
        with schema_context(self.tenant.schema_name):
            with patch('zargar.gold_installments.services.GoldPriceService.get_current_gold_price') as mock_price:
                mock_price.return_value = {'price_per_gram': Decimal('2500000')}
                
                valuation = InventoryValuationService.calculate_total_inventory_value()
                
                self.assertIn('total_items', valuation)
                self.assertIn('total_current_value', valuation)
                self.assertEqual(valuation['total_items'], 1)


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['tests.test_jewelry_ui_tenant_aware'])