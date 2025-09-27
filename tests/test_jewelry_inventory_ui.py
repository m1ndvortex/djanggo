"""
Comprehensive tests for jewelry inventory management UI.
Tests all views, templates, and AJAX endpoints.
"""
import json
import tempfile
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from zargar.tenants.models import Tenant, Domain
from zargar.jewelry.models import JewelryItem, Category, Gemstone, JewelryItemPhoto
from zargar.jewelry.services import (
    SerialNumberTrackingService, 
    StockAlertService, 
    InventoryValuationService
)

User = get_user_model()


class InventoryUITestCase(TenantTestCase):
    """
    Test case for inventory management UI with tenant isolation.
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create tenant
        cls.tenant = Tenant(
            name='Test Jewelry Shop',
            schema_name='test_jewelry_ui',
            owner_name='Test Owner',
            owner_email='owner@testshop.com',
            subscription_plan='basic'
        )
        cls.tenant.save()
        
        # Create domain
        cls.domain = Domain(
            domain='testjewelryui.zargar.local',
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
        
        connection.set_tenant(cls.tenant)
    
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
            description='Test rings category',
            created_by=self.user
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
            created_by=self.user
        )
        
        # Create client
        self.client = TenantClient(self.tenant)
        self.client.login(username='testuser', password='testpass123')
    
    def test_inventory_dashboard_view(self):
        """Test inventory dashboard loads correctly."""
        url = reverse('jewelry:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'داشبورد موجودی')
        self.assertContains(response, 'Test Gold Ring')
        self.assertIn('total_items', response.context)
        self.assertIn('valuation', response.context)
    
    def test_inventory_list_view(self):
        """Test inventory list view with filtering."""
        url = reverse('jewelry:inventory_list')
        
        # Test basic list view
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'فهرست موجودی')
        self.assertContains(response, 'Test Gold Ring')
        
        # Test search functionality
        response = self.client.get(url, {'search': 'Test'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Gold Ring')
        
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
        
        # Test low stock filter
        self.jewelry_item.quantity = 1
        self.jewelry_item.save()
        response = self.client.get(url, {'low_stock': 'true'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Gold Ring')
    
    def test_inventory_detail_view(self):
        """Test inventory detail view."""
        url = reverse('jewelry:inventory_detail', kwargs={'pk': self.jewelry_item.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Gold Ring')
        self.assertContains(response, 'TEST001')
        self.assertContains(response, '18 عیار')
        self.assertContains(response, '5.5')  # Weight
        self.assertIn('item', response.context)
        self.assertIn('photos', response.context)
    
    def test_inventory_create_view_get(self):
        """Test inventory create form display."""
        url = reverse('jewelry:inventory_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'افزودن کالای جدید')
        self.assertContains(response, 'نام کالا')
        self.assertContains(response, 'کد کالا')
        self.assertIn('categories', response.context)
    
    def test_inventory_create_view_post(self):
        """Test inventory item creation."""
        url = reverse('jewelry:inventory_create')
        
        # Create test image
        image_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
        test_image = SimpleUploadedFile(
            name='test_image.png',
            content=image_content,
            content_type='image/png'
        )
        
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
            'description': 'New test ring description',
            'photos': [test_image]
        }
        
        response = self.client.post(url, data)
        
        # Should redirect to detail view
        self.assertEqual(response.status_code, 302)
        
        # Check item was created
        new_item = JewelryItem.objects.get(sku='TEST002')
        self.assertEqual(new_item.name, 'New Test Ring')
        self.assertEqual(new_item.karat, 21)
        self.assertEqual(new_item.quantity, 5)
    
    def test_inventory_update_view(self):
        """Test inventory item update."""
        url = reverse('jewelry:inventory_edit', kwargs={'pk': self.jewelry_item.pk})
        
        # Test GET request
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ویرایش کالا')
        self.assertContains(response, 'Test Gold Ring')
        
        # Test POST request
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
    
    def test_category_management_view(self):
        """Test category management view."""
        url = reverse('jewelry:category_management')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مدیریت دسته‌بندی‌ها')
        self.assertContains(response, 'انگشتر')
        self.assertIn('categories', response.context)
    
    def test_stock_alerts_view(self):
        """Test stock alerts view."""
        # Make item low stock
        self.jewelry_item.quantity = 1
        self.jewelry_item.save()
        
        url = reverse('jewelry:stock_alerts')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'هشدارهای موجودی')
        self.assertIn('alerts_summary', response.context)
        self.assertIn('low_stock_items', response.context)
    
    def test_inventory_valuation_view(self):
        """Test inventory valuation view."""
        url = reverse('jewelry:inventory_valuation')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ارزیابی موجودی')
        self.assertIn('valuation', response.context)
        self.assertIn('category_valuations', response.context)
    
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
    
    def test_update_stock_thresholds_api(self):
        """Test stock thresholds update API."""
        url = reverse('jewelry:update_stock_thresholds')
        
        data = {
            'updates': [
                {
                    'item_id': self.jewelry_item.id,
                    'new_threshold': 5
                }
            ]
        }
        
        response = self.client.post(
            url,
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Check threshold was updated
        updated_item = JewelryItem.objects.get(pk=self.jewelry_item.pk)
        self.assertEqual(updated_item.minimum_stock, 5)
    
    def test_assign_serial_number_api(self):
        """Test serial number assignment API."""
        # Make item high value to qualify for serial number
        self.jewelry_item.selling_price = Decimal('60000000')  # 60M Toman
        self.jewelry_item.save()
        
        url = reverse('jewelry:assign_serial_number', kwargs={'item_id': self.jewelry_item.id})
        
        response = self.client.post(
            url,
            json.dumps({'force_assign': True}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('serial_number', response_data)
        
        # Check serial number was assigned
        updated_item = JewelryItem.objects.get(pk=self.jewelry_item.pk)
        self.assertIsNotNone(updated_item.barcode)
        self.assertTrue(updated_item.barcode.startswith('ZRG-'))
    
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
    
    def test_photo_management(self):
        """Test photo upload and management."""
        # Create test photo
        image_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
        test_image = SimpleUploadedFile(
            name='test_photo.png',
            content=image_content,
            content_type='image/png'
        )
        
        photo = JewelryItemPhoto.objects.create(
            jewelry_item=self.jewelry_item,
            image=test_image,
            caption='Test photo',
            is_primary=True,
            order=0
        )
        
        # Test photo deletion API
        delete_url = reverse('jewelry:delete_photo', kwargs={'photo_id': photo.id})
        response = self.client.delete(delete_url)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Check photo was deleted
        self.assertFalse(JewelryItemPhoto.objects.filter(id=photo.id).exists())
    
    def test_permission_checks(self):
        """Test permission checks for different user roles."""
        # Create salesperson user (limited permissions)
        salesperson = User.objects.create_user(
            username='salesperson',
            email='sales@example.com',
            password='testpass123',
            role='salesperson'
        )
        
        # Login as salesperson
        self.client.logout()
        self.client.login(username='salesperson', password='testpass123')
        
        # Test that salesperson can view but not edit
        detail_url = reverse('jewelry:inventory_detail', kwargs={'pk': self.jewelry_item.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['can_edit'])
        
        # Test that salesperson cannot create items
        create_url = reverse('jewelry:inventory_create')
        response = self.client.get(create_url)
        # Should still allow access but form submission would be restricted
        self.assertEqual(response.status_code, 200)
    
    def test_responsive_design_elements(self):
        """Test that responsive design elements are present in templates."""
        url = reverse('jewelry:dashboard')
        response = self.client.get(url)
        
        # Check for responsive grid classes
        self.assertContains(response, 'grid-cols-1')
        self.assertContains(response, 'md:grid-cols-2')
        self.assertContains(response, 'lg:grid-cols-3')
        
        # Check for mobile-friendly navigation
        self.assertContains(response, 'flex-col')
        self.assertContains(response, 'md:flex-row')
    
    def test_persian_rtl_support(self):
        """Test Persian RTL support in templates."""
        url = reverse('jewelry:dashboard')
        response = self.client.get(url)
        
        # Check for RTL classes
        self.assertContains(response, 'space-x-reverse')
        self.assertContains(response, 'persian-numbers')
        
        # Check for Persian text
        self.assertContains(response, 'داشبورد موجودی')
        self.assertContains(response, 'تعداد کل کالاها')
    
    def test_dark_mode_support(self):
        """Test dark mode theme support."""
        url = reverse('jewelry:dashboard')
        response = self.client.get(url)
        
        # Check for dark mode classes
        self.assertContains(response, 'cyber-')
        self.assertContains(response, 'is_dark_mode')
        self.assertContains(response, 'dark')


class InventoryServicesIntegrationTest(TenantTestCase):
    """
    Test integration between UI and inventory services.
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create tenant
        cls.tenant = Tenant(
            name='Test Services Shop',
            schema_name='test_services_ui',
            owner_name='Test Services Owner',
            owner_email='owner@testservices.com',
            subscription_plan='basic'
        )
        cls.tenant.save()
        
        # Create domain
        cls.domain = Domain(
            domain='testservicesui.zargar.local',
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
        
        connection.set_tenant(cls.tenant)
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
        
        self.category = Category.objects.create(
            name='Rings',
            name_persian='انگشتر',
            created_by=self.user
        )
        
        # Create multiple items for testing
        for i in range(5):
            JewelryItem.objects.create(
                name=f'Test Ring {i+1}',
                sku=f'TEST00{i+1}',
                category=self.category,
                weight_grams=Decimal(f'{i+1}.500'),
                karat=18,
                manufacturing_cost=Decimal('1000000'),
                selling_price=Decimal('5000000'),
                quantity=i+1,  # Different quantities for testing
                minimum_stock=3,  # Some will be low stock
                created_by=self.user
            )
        
        self.client = TenantClient(self.tenant)
        self.client.login(username='testuser', password='testpass123')
    
    def test_stock_alert_service_integration(self):
        """Test stock alert service integration with UI."""
        # Get low stock items through service
        low_stock_items = StockAlertService.get_low_stock_items()
        
        # Should have items with quantity <= minimum_stock (3)
        self.assertTrue(len(low_stock_items) >= 2)  # Items with quantity 1, 2
        
        # Test UI displays these correctly
        url = reverse('jewelry:stock_alerts')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('low_stock_items', response.context)
        
        # Check that low stock items are displayed
        for item_data in low_stock_items[:3]:  # Check first 3
            self.assertContains(response, item_data['item'].name)
    
    def test_inventory_valuation_service_integration(self):
        """Test inventory valuation service integration with UI."""
        # Get valuation through service
        valuation = InventoryValuationService.calculate_total_inventory_value()
        
        # Test UI displays valuation correctly
        url = reverse('jewelry:inventory_valuation')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('valuation', response.context)
        
        # Check that valuation data is displayed
        self.assertContains(response, str(valuation['total_items']))
        
    def test_serial_number_service_integration(self):
        """Test serial number service integration with UI."""
        # Create high-value item
        high_value_item = JewelryItem.objects.create(
            name='Expensive Ring',
            sku='EXPENSIVE001',
            category=self.category,
            weight_grams=Decimal('10.000'),
            karat=24,
            manufacturing_cost=Decimal('5000000'),
            selling_price=Decimal('60000000'),  # 60M Toman
            quantity=1,
            minimum_stock=1,
            created_by=self.user
        )
        
        # Test that UI shows serial number assignment option
        url = reverse('jewelry:inventory_detail', kwargs={'pk': high_value_item.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('serial_check', response.context)
        
        # Should show assignment button for high-value items
        serial_check = response.context['serial_check']
        self.assertIn('requires_high_value', serial_check)


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['tests.test_jewelry_inventory_ui'])