"""
Tests for barcode UI workflows and mobile scanning interface.
"""
import json
from datetime import datetime, timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from zargar.tenants.models import Tenant, Domain
from zargar.jewelry.models import JewelryItem, Category
from zargar.jewelry.barcode_models import (
    BarcodeGeneration, BarcodeScanHistory, BarcodeTemplate, 
    BarcodeSettings, BarcodeType
)
from zargar.jewelry.barcode_services import (
    BarcodeGenerationService, BarcodeScanningService
)

User = get_user_model()


class BarcodeUIWorkflowsTestCase(TenantTestCase):
    """Test barcode UI workflows and functionality."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create tenant
        cls.tenant = Tenant(
            name="Test Jewelry Shop",
            schema_name="test_jewelry"
        )
        cls.tenant.save()
        
        # Create domain
        cls.domain = Domain(
            domain="testjewelry.localhost",
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
    
    def setUp(self):
        super().setUp()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            name_persian='دسته تست',
            is_active=True
        )
        
        # Create test jewelry items
        self.jewelry_item1 = JewelryItem.objects.create(
            name='Test Ring',
            sku='RING001',
            category=self.category,
            weight_grams=5.5,
            karat=18,
            manufacturing_cost=100.00,
            selling_price=500.00,
            quantity=10,
            created_by=self.user
        )
        
        self.jewelry_item2 = JewelryItem.objects.create(
            name='Test Necklace',
            sku='NECK001',
            category=self.category,
            weight_grams=12.3,
            karat=22,
            manufacturing_cost=200.00,
            selling_price=800.00,
            quantity=5,
            created_by=self.user
        )
        
        # Create barcode settings
        self.barcode_settings = BarcodeSettings.objects.create(
            auto_generate_on_create=True,
            default_barcode_type=BarcodeType.QR_CODE,
            tenant_prefix='TEST'
        )
        
        # Create client
        self.client = TenantClient(self.tenant)
        self.client.login(username='testuser', password='testpass123')
    
    def test_barcode_management_view_loads(self):
        """Test that barcode management view loads correctly."""
        url = reverse('jewelry:barcode_management')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مدیریت بارکد و QR کد')
        self.assertContains(response, 'تولید، چاپ و اسکن بارکد')
    
    def test_mobile_scanner_view_loads(self):
        """Test that mobile scanner view loads correctly."""
        url = reverse('jewelry:mobile_scanner')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'اسکن موبایل')
        self.assertContains(response, 'camera-preview')
    
    def test_barcode_history_view_loads(self):
        """Test that barcode history view loads correctly."""
        url = reverse('jewelry:barcode_history')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تاریخچه اسکن بارکد')
        self.assertContains(response, 'مشاهده و تحلیل تاریخچه')
    
    def test_barcode_items_api(self):
        """Test barcode items API endpoint."""
        # Generate barcode for item
        service = BarcodeGenerationService()
        barcode_gen = service.generate_barcode_for_item(self.jewelry_item1)
        
        url = reverse('jewelry:barcode_items_api')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertGreaterEqual(len(data['results']), 2)
        
        # Check item with barcode
        item_with_barcode = next(
            (item for item in data['results'] if item['id'] == self.jewelry_item1.id), 
            None
        )
        self.assertIsNotNone(item_with_barcode)
        self.assertIsNotNone(item_with_barcode['barcode'])
        self.assertEqual(item_with_barcode['barcode_type'], 'qr_code')
        
        # Check item without barcode
        item_without_barcode = next(
            (item for item in data['results'] if item['id'] == self.jewelry_item2.id), 
            None
        )
        self.assertIsNotNone(item_without_barcode)
        self.assertIsNone(item_without_barcode['barcode'])
    
    def test_barcode_statistics_api(self):
        """Test barcode statistics API endpoint."""
        # Generate some test data
        service = BarcodeGenerationService()
        service.generate_barcode_for_item(self.jewelry_item1)
        
        # Create scan history
        scan_service = BarcodeScanningService()
        scan_service.scan_barcode(
            self.jewelry_item1.barcode,
            'lookup',
            'test_device',
            'test_location'
        )
        
        url = reverse('jewelry:barcode_statistics_api')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['total_barcodes'], 1)
        self.assertGreaterEqual(data['today_scans'], 1)
        self.assertGreaterEqual(data['qr_codes'], 1)
        self.assertIsInstance(data['daily_activity'], list)
        self.assertIsInstance(data['scan_types'], list)
    
    def test_barcode_generation_workflow(self):
        """Test complete barcode generation workflow."""
        # Test single barcode generation
        url = reverse('jewelry:barcode-generation-generate-for-item')
        data = {
            'item_id': self.jewelry_item1.id,
            'barcode_type': 'qr_code'
        }
        
        response = self.client.post(
            url, 
            json.dumps(data), 
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertTrue(response_data['success'])
        self.assertIsNotNone(response_data['barcode_generation_id'])
        self.assertIsNotNone(response_data['barcode_data'])
        self.assertEqual(response_data['barcode_type'], 'qr_code')
        
        # Verify barcode was created
        barcode_gen = BarcodeGeneration.objects.get(
            id=response_data['barcode_generation_id']
        )
        self.assertEqual(barcode_gen.jewelry_item, self.jewelry_item1)
        self.assertEqual(barcode_gen.barcode_type, 'qr_code')
        self.assertTrue(barcode_gen.is_active)
    
    def test_bulk_barcode_generation_workflow(self):
        """Test bulk barcode generation workflow."""
        url = reverse('jewelry:barcode-generation-bulk-generate')
        data = {
            'item_ids': [self.jewelry_item1.id, self.jewelry_item2.id],
            'barcode_type': 'qr_code'
        }
        
        response = self.client.post(
            url, 
            json.dumps(data), 
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['generated_count'], 2)
        self.assertEqual(len(response_data['results']), 2)
        
        # Verify barcodes were created
        barcodes = BarcodeGeneration.objects.filter(
            jewelry_item__in=[self.jewelry_item1, self.jewelry_item2],
            is_active=True
        )
        self.assertEqual(barcodes.count(), 2)
    
    def test_mobile_scanning_workflow(self):
        """Test mobile scanning workflow."""
        # Generate barcode first
        service = BarcodeGenerationService()
        barcode_gen = service.generate_barcode_for_item(self.jewelry_item1)
        
        # Test scanning
        url = reverse('jewelry:barcode_scan')
        data = {
            'scanned_data': self.jewelry_item1.barcode,
            'scan_action': 'lookup',
            'scanner_device': 'mobile_web',
            'location': 'shop_counter'
        }
        
        response = self.client.post(
            url, 
            json.dumps(data), 
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['jewelry_item']['id'], self.jewelry_item1.id)
        self.assertEqual(response_data['jewelry_item']['name'], self.jewelry_item1.name)
        self.assertEqual(response_data['jewelry_item']['sku'], self.jewelry_item1.sku)
        
        # Verify scan history was created
        scan_history = BarcodeScanHistory.objects.filter(
            jewelry_item=self.jewelry_item1,
            scan_action='lookup'
        ).first()
        
        self.assertIsNotNone(scan_history)
        self.assertEqual(scan_history.scanner_device, 'mobile_web')
        self.assertEqual(scan_history.location, 'shop_counter')
    
    def test_scan_history_tracking(self):
        """Test scan history tracking functionality."""
        # Generate barcode and create multiple scans
        service = BarcodeGenerationService()
        barcode_gen = service.generate_barcode_for_item(self.jewelry_item1)
        
        scan_service = BarcodeScanningService()
        
        # Create multiple scan entries
        scan_actions = ['lookup', 'inventory_check', 'sale', 'audit']
        for action in scan_actions:
            scan_service.scan_barcode(
                self.jewelry_item1.barcode,
                action,
                'test_device',
                'test_location',
                f'Test scan for {action}'
            )
        
        # Test scan history API
        url = reverse('jewelry:scan-history-by-item')
        response = self.client.get(f"{url}?item_id={self.jewelry_item1.id}")
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(len(data['scan_history']), 4)
        self.assertEqual(data['jewelry_item']['id'], self.jewelry_item1.id)
        
        # Verify scan actions are recorded correctly
        recorded_actions = [scan['scan_action'] for scan in data['scan_history']]
        for action in scan_actions:
            self.assertIn(action, recorded_actions)
    
    def test_scan_statistics_tracking(self):
        """Test scan statistics tracking."""
        # Create test data
        service = BarcodeGenerationService()
        service.generate_barcode_for_item(self.jewelry_item1)
        service.generate_barcode_for_item(self.jewelry_item2)
        
        scan_service = BarcodeScanningService()
        
        # Create scans for different items
        scan_service.scan_barcode(self.jewelry_item1.barcode, 'lookup')
        scan_service.scan_barcode(self.jewelry_item1.barcode, 'sale')
        scan_service.scan_barcode(self.jewelry_item2.barcode, 'inventory_check')
        
        # Test statistics API
        url = reverse('jewelry:scan-history-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['total_scans'], 3)
        self.assertEqual(len(data['recent_scans']), 3)
        
        # Test item-specific statistics
        response = self.client.get(f"{url}?item_id={self.jewelry_item1.id}")
        data = json.loads(response.content)
        
        self.assertEqual(data['total_scans'], 2)
    
    def test_barcode_printing_workflow(self):
        """Test barcode printing workflow."""
        # Generate barcode with image
        service = BarcodeGenerationService()
        barcode_gen = service.generate_barcode_for_item(self.jewelry_item1)
        
        # Test barcode image download
        if barcode_gen.barcode_image:
            url = reverse('jewelry:barcode-generation-download-image', args=[barcode_gen.id])
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'image/png')
    
    def test_error_handling_invalid_scan(self):
        """Test error handling for invalid barcode scans."""
        url = reverse('jewelry:barcode_scan')
        data = {
            'scanned_data': 'INVALID_BARCODE_12345',
            'scan_action': 'lookup',
            'scanner_device': 'mobile_web'
        }
        
        response = self.client.post(
            url, 
            json.dumps(data), 
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        response_data = json.loads(response.content)
        
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)
    
    def test_barcode_template_functionality(self):
        """Test barcode template functionality."""
        # Create custom template
        template = BarcodeTemplate.objects.create(
            name='Custom QR Template',
            barcode_type=BarcodeType.QR_CODE,
            data_format='{sku}-{category}-{date}',
            include_sku=True,
            include_category=True,
            is_default=True
        )
        
        # Test template creation API
        url = reverse('jewelry:barcode-template-create-defaults')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
    
    def test_barcode_settings_management(self):
        """Test barcode settings management."""
        # Test getting current settings
        url = reverse('jewelry:barcode-settings-current')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertIn('auto_generate_on_create', data)
        self.assertIn('default_barcode_type', data)
        self.assertIn('tenant_prefix', data)
        
        # Test updating settings
        url = reverse('jewelry:barcode-settings-update-settings')
        update_data = {
            'auto_generate_on_create': False,
            'default_barcode_type': 'ean13',
            'tenant_prefix': 'NEW'
        }
        
        response = self.client.post(
            url, 
            json.dumps(update_data), 
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['settings']['tenant_prefix'], 'NEW')
    
    def test_mobile_scanner_responsive_design(self):
        """Test mobile scanner responsive design elements."""
        url = reverse('jewelry:mobile_scanner')
        response = self.client.get(url)
        
        # Check for mobile-specific CSS classes and elements
        self.assertContains(response, 'scanner-container')
        self.assertContains(response, 'camera-preview')
        self.assertContains(response, 'scanner-overlay')
        self.assertContains(response, 'camera-controls')
        self.assertContains(response, 'control-button')
        
        # Check for touch-friendly elements
        self.assertContains(response, 'scan-button')
        self.assertContains(response, 'touch-friendly')
    
    def test_barcode_ui_accessibility(self):
        """Test barcode UI accessibility features."""
        # Test barcode management view
        url = reverse('jewelry:barcode_management')
        response = self.client.get(url)
        
        # Check for accessibility attributes
        self.assertContains(response, 'aria-label')
        self.assertContains(response, 'role=')
        
        # Check for keyboard navigation support
        self.assertContains(response, 'tabindex')
        
        # Test mobile scanner view
        url = reverse('jewelry:mobile_scanner')
        response = self.client.get(url)
        
        # Check for screen reader support
        self.assertContains(response, 'alt=')
        self.assertContains(response, 'aria-')
    
    def test_barcode_ui_performance(self):
        """Test barcode UI performance considerations."""
        # Create multiple items for performance testing
        items = []
        for i in range(50):
            item = JewelryItem.objects.create(
                name=f'Performance Test Item {i}',
                sku=f'PERF{i:03d}',
                category=self.category,
                weight_grams=5.0,
                karat=18,
                manufacturing_cost=100.00,
                created_by=self.user
            )
            items.append(item)
        
        # Test barcode items API performance
        url = reverse('jewelry:barcode_items_api')
        
        import time
        start_time = time.time()
        response = self.client.get(url)
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        
        # Response should be reasonably fast (under 2 seconds)
        response_time = end_time - start_time
        self.assertLess(response_time, 2.0, f"API response took {response_time:.2f} seconds")
        
        data = json.loads(response.content)
        self.assertGreaterEqual(len(data['results']), 50)


class BarcodeUIIntegrationTestCase(TenantTestCase):
    """Integration tests for barcode UI workflows."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create tenant
        cls.tenant = Tenant(
            name="Integration Test Shop",
            schema_name="integration_test"
        )
        cls.tenant.save()
        
        # Create domain
        cls.domain = Domain(
            domain="integration.localhost",
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
    
    def setUp(self):
        super().setUp()
        
        # Create test user
        self.user = User.objects.create_user(
            username='integrationuser',
            email='integration@example.com',
            password='testpass123',
            role='owner'
        )
        
        # Create test data
        self.category = Category.objects.create(
            name='Integration Category',
            name_persian='دسته یکپارچگی',
            is_active=True
        )
        
        self.jewelry_item = JewelryItem.objects.create(
            name='Integration Test Ring',
            sku='INT001',
            category=self.category,
            weight_grams=7.5,
            karat=18,
            manufacturing_cost=150.00,
            selling_price=600.00,
            quantity=8,
            created_by=self.user
        )
        
        # Create client
        self.client = TenantClient(self.tenant)
        self.client.login(username='integrationuser', password='testpass123')
    
    def test_complete_barcode_workflow_integration(self):
        """Test complete barcode workflow from generation to scanning."""
        # Step 1: Generate barcode
        generation_url = reverse('jewelry:barcode-generation-generate-for-item')
        generation_data = {
            'item_id': self.jewelry_item.id,
            'barcode_type': 'qr_code'
        }
        
        generation_response = self.client.post(
            generation_url, 
            json.dumps(generation_data), 
            content_type='application/json'
        )
        
        self.assertEqual(generation_response.status_code, 200)
        generation_result = json.loads(generation_response.content)
        self.assertTrue(generation_result['success'])
        
        # Step 2: Verify barcode appears in management interface
        items_url = reverse('jewelry:barcode_items_api')
        items_response = self.client.get(items_url)
        
        self.assertEqual(items_response.status_code, 200)
        items_data = json.loads(items_response.content)
        
        item_with_barcode = next(
            (item for item in items_data['results'] if item['id'] == self.jewelry_item.id), 
            None
        )
        self.assertIsNotNone(item_with_barcode)
        self.assertIsNotNone(item_with_barcode['barcode'])
        
        # Step 3: Scan the barcode
        scan_url = reverse('jewelry:barcode_scan')
        scan_data = {
            'scanned_data': item_with_barcode['barcode'],
            'scan_action': 'inventory_check',
            'scanner_device': 'integration_test',
            'location': 'test_location',
            'notes': 'Integration test scan'
        }
        
        scan_response = self.client.post(
            scan_url, 
            json.dumps(scan_data), 
            content_type='application/json'
        )
        
        self.assertEqual(scan_response.status_code, 200)
        scan_result = json.loads(scan_response.content)
        self.assertTrue(scan_result['success'])
        self.assertEqual(scan_result['jewelry_item']['id'], self.jewelry_item.id)
        
        # Step 4: Verify scan appears in history
        history_url = reverse('jewelry:scan-history-by-item')
        history_response = self.client.get(f"{history_url}?item_id={self.jewelry_item.id}")
        
        self.assertEqual(history_response.status_code, 200)
        history_data = json.loads(history_response.content)
        
        self.assertEqual(len(history_data['scan_history']), 1)
        scan_entry = history_data['scan_history'][0]
        self.assertEqual(scan_entry['scan_action'], 'inventory_check')
        self.assertEqual(scan_entry['scanner_device'], 'integration_test')
        self.assertEqual(scan_entry['notes'], 'Integration test scan')
        
        # Step 5: Verify statistics are updated
        stats_url = reverse('jewelry:barcode_statistics_api')
        stats_response = self.client.get(stats_url)
        
        self.assertEqual(stats_response.status_code, 200)
        stats_data = json.loads(stats_response.content)
        
        self.assertGreaterEqual(stats_data['total_barcodes'], 1)
        self.assertGreaterEqual(stats_data['today_scans'], 1)
        self.assertGreaterEqual(stats_data['qr_codes'], 1)
    
    def test_mobile_scanner_workflow_integration(self):
        """Test mobile scanner workflow integration."""
        # Generate barcode first
        service = BarcodeGenerationService()
        barcode_gen = service.generate_barcode_for_item(self.jewelry_item)
        
        # Test mobile scanner page loads
        mobile_url = reverse('jewelry:mobile_scanner')
        mobile_response = self.client.get(mobile_url)
        
        self.assertEqual(mobile_response.status_code, 200)
        self.assertContains(mobile_response, 'اسکن موبایل')
        
        # Test scanning through mobile interface
        scan_url = reverse('jewelry:barcode_scan')
        scan_data = {
            'scanned_data': self.jewelry_item.barcode,
            'scan_action': 'lookup',
            'scanner_device': 'mobile_web',
            'location': 'mobile_scanner'
        }
        
        scan_response = self.client.post(
            scan_url, 
            json.dumps(scan_data), 
            content_type='application/json'
        )
        
        self.assertEqual(scan_response.status_code, 200)
        scan_result = json.loads(scan_response.content)
        
        self.assertTrue(scan_result['success'])
        self.assertEqual(scan_result['jewelry_item']['name'], self.jewelry_item.name)
        
        # Verify scan is recorded with mobile device info
        scan_history = BarcodeScanHistory.objects.filter(
            jewelry_item=self.jewelry_item,
            scanner_device='mobile_web'
        ).first()
        
        self.assertIsNotNone(scan_history)
        self.assertEqual(scan_history.location, 'mobile_scanner')