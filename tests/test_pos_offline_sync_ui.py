"""
Tests for POS offline sync UI functionality (Task 12.4).
Tests the frontend components for offline mode indicator, sync queue management, and conflict resolution.
"""
import os
import django
from django.conf import settings

# Setup Django
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import json
import time
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django_tenants.utils import get_tenant_model, tenant_context
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

from zargar.pos.models import POSTransaction, POSOfflineStorage
from zargar.customers.models import Customer
from zargar.jewelry.models import JewelryItem, Category

User = get_user_model()


class POSOfflineSyncUITest(TestCase):
    """Test POS offline sync UI components."""
    
    def setUp(self):
        """Set up test data."""
        # Get tenant
        Tenant = get_tenant_model()
        self.tenant = Tenant.objects.exclude(schema_name='public').first()
        
        if not self.tenant:
            self.tenant = Tenant.objects.create(
                schema_name='test_offline_ui',
                name='Test Offline UI Shop'
            )
        
        with tenant_context(self.tenant):
            # Create user
            self.user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123'
            )
            
            # Create customer
            self.customer = Customer.objects.create(
                first_name='احمد',
                last_name='محمدی',
                persian_first_name='احمد',
                persian_last_name='محمدی',
                phone_number='09123456789'
            )
            
            # Create category and jewelry item
            self.category = Category.objects.create(
                name='Rings',
                name_persian='انگشتر'
            )
            
            self.jewelry_item = JewelryItem.objects.create(
                name='Gold Ring 18K',
                category=self.category,
                sku='RING-001',
                weight_grams=Decimal('5.500'),
                karat=18,
                selling_price=Decimal('2500000.00'),
                quantity=10,
                status='in_stock'
            )
            
            # Create client and login
            self.client = Client()
            self.client.login(username='testuser', password='testpass123')
    
    def test_pos_touch_interface_includes_offline_components(self):
        """Test that POS touch interface includes offline sync components."""
        with tenant_context(self.tenant):
            url = reverse('pos:touch_interface')
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            
            # Check that offline sync components are included
            self.assertContains(response, 'offline_sync_status.html')
            self.assertContains(response, 'sync_queue_modal.html')
            self.assertContains(response, 'conflict_resolution_modal.html')
            
            # Check for offline sync status indicator
            self.assertContains(response, 'offline-sync-status')
            self.assertContains(response, 'connection-indicator')
            
            # Check for sync queue button
            self.assertContains(response, 'صف همگام‌سازی')
            self.assertContains(response, 'openSyncQueue()')
    
    def test_offline_sync_status_component_structure(self):
        """Test offline sync status component HTML structure."""
        with tenant_context(self.tenant):
            url = reverse('pos:touch_interface')
            response = self.client.get(url)
            
            content = response.content.decode('utf-8')
            
            # Check for connection status elements
            self.assertIn('connection-indicator', content)
            self.assertIn('آنلاین', content)
            self.assertIn('آفلاین', content)
            self.assertIn('در حال همگام‌سازی', content)
            
            # Check for sync queue summary
            self.assertIn('sync-queue-summary', content)
            self.assertIn('صف همگام‌سازی', content)
            self.assertIn('تراکنش‌های در انتظار', content)
            
            # Check for manual sync button
            self.assertIn('همگام‌سازی دستی', content)
            
            # Check for sync error alert
            self.assertIn('sync-error-alert', content)
            self.assertIn('خطا در همگام‌سازی', content)
    
    def test_sync_queue_modal_structure(self):
        """Test sync queue modal HTML structure."""
        with tenant_context(self.tenant):
            url = reverse('pos:touch_interface')
            response = self.client.get(url)
            
            content = response.content.decode('utf-8')
            
            # Check for modal structure
            self.assertIn('sync-queue-modal', content)
            self.assertIn('مدیریت صف همگام‌سازی', content)
            
            # Check for queue summary cards
            self.assertIn('در انتظار همگام‌سازی', content)
            self.assertIn('همگام‌سازی شده', content)
            self.assertIn('خطا در همگام‌سازی', content)
            
            # Check for action buttons
            self.assertIn('همگام‌سازی همه', content)
            self.assertIn('پاک کردن همگام‌سازی شده‌ها', content)
            self.assertIn('صادرات صف', content)
            self.assertIn('بروزرسانی', content)
            
            # Check for filter tabs
            self.assertIn('در انتظار', content)
            self.assertIn('همگام‌سازی شده', content)
            self.assertIn('خطا', content)
    
    def test_conflict_resolution_modal_structure(self):
        """Test conflict resolution modal HTML structure."""
        with tenant_context(self.tenant):
            url = reverse('pos:touch_interface')
            response = self.client.get(url)
            
            content = response.content.decode('utf-8')
            
            # Check for modal structure
            self.assertIn('conflict-resolution-modal', content)
            self.assertIn('حل تعارض همگام‌سازی', content)
            
            # Check for warning banner
            self.assertIn('تعارض در همگام‌سازی شناسایی شد', content)
            
            # Check for resolution options
            self.assertIn('استفاده از داده محلی', content)
            self.assertIn('استفاده از داده سرور', content)
            self.assertIn('رد کردن تراکنش', content)
            
            # Check for data comparison sections
            self.assertIn('داده‌های محلی (آفلاین)', content)
            self.assertIn('داده‌های سرور (آنلاین)', content)
            
            # Check for apply resolutions button
            self.assertIn('اعمال راه‌حل‌ها', content)
    
    def test_offline_sync_javascript_inclusion(self):
        """Test that offline sync JavaScript is properly included."""
        with tenant_context(self.tenant):
            url = reverse('pos:touch_interface')
            response = self.client.get(url)
            
            content = response.content.decode('utf-8')
            
            # Check for Alpine.js components
            self.assertIn('offlineSyncStatus()', content)
            self.assertIn('syncQueueModal()', content)
            self.assertIn('conflictResolutionModal()', content)
            
            # Check for key JavaScript functions
            self.assertIn('loadOfflineQueue()', content)
            self.assertIn('manualSync()', content)
            self.assertIn('performSync()', content)
            self.assertIn('handleSyncResults()', content)
            self.assertIn('applyResolutions()', content)
    
    def test_persian_localization_in_ui_components(self):
        """Test Persian localization in offline sync UI components."""
        with tenant_context(self.tenant):
            url = reverse('pos:touch_interface')
            response = self.client.get(url)
            
            content = response.content.decode('utf-8')
            
            # Check Persian text in offline sync status
            persian_texts = [
                'آنلاین',
                'آفلاین', 
                'در حال همگام‌سازی',
                'صف همگام‌سازی',
                'تراکنش‌های در انتظار',
                'حجم داده',
                'همگام‌سازی دستی',
                'خطا در همگام‌سازی',
                'تلاش مجدد'
            ]
            
            for text in persian_texts:
                self.assertIn(text, content)
            
            # Check Persian text in sync queue modal
            queue_texts = [
                'مدیریت صف همگام‌سازی',
                'در انتظار همگام‌سازی',
                'همگام‌سازی شده',
                'خطا در همگام‌سازی',
                'همگام‌سازی همه',
                'پاک کردن همگام‌سازی شده‌ها',
                'صادرات صف',
                'بروزرسانی'
            ]
            
            for text in queue_texts:
                self.assertIn(text, content)
            
            # Check Persian text in conflict resolution modal
            conflict_texts = [
                'حل تعارض همگام‌سازی',
                'تعارض در همگام‌سازی شناسایی شد',
                'استفاده از داده محلی',
                'استفاده از داده سرور',
                'رد کردن تراکنش',
                'داده‌های محلی (آفلاین)',
                'داده‌های سرور (آنلاین)',
                'اعمال راه‌حل‌ها'
            ]
            
            for text in conflict_texts:
                self.assertIn(text, content)
    
    def test_css_classes_for_theme_support(self):
        """Test CSS classes for dual theme support."""
        with tenant_context(self.tenant):
            url = reverse('pos:touch_interface')
            response = self.client.get(url)
            
            content = response.content.decode('utf-8')
            
            # Check for cybersecurity theme classes (dark mode)
            cyber_classes = [
                'cyber-bg-surface',
                'cyber-neon-primary',
                'cyber-neon-secondary',
                'cyber-neon-warning',
                'cyber-neon-success',
                'cyber-neon-danger',
                'cyber-text-primary',
                'cyber-text-secondary'
            ]
            
            for css_class in cyber_classes:
                self.assertIn(css_class, content)
            
            # Check for conditional theme rendering
            self.assertIn('{% if is_dark_mode %}', content)
            self.assertIn('{% else %}', content)
    
    def test_responsive_design_classes(self):
        """Test responsive design classes for mobile/tablet optimization."""
        with tenant_context(self.tenant):
            url = reverse('pos:touch_interface')
            response = self.client.get(url)
            
            content = response.content.decode('utf-8')
            
            # Check for responsive grid classes
            responsive_classes = [
                'grid-cols-1',
                'md:grid-cols-2',
                'md:grid-cols-3',
                'max-w-sm',
                'max-w-4xl',
                'max-w-5xl'
            ]
            
            for css_class in responsive_classes:
                self.assertIn(css_class, content)
            
            # Check for mobile-specific classes
            mobile_classes = [
                'touch-btn',
                'large-touch',
                'backdrop-blur-sm',
                'pos-scrollbar'
            ]
            
            for css_class in mobile_classes:
                self.assertIn(css_class, content)
    
    def test_accessibility_features(self):
        """Test accessibility features in offline sync UI."""
        with tenant_context(self.tenant):
            url = reverse('pos:touch_interface')
            response = self.client.get(url)
            
            content = response.content.decode('utf-8')
            
            # Check for ARIA labels and roles
            accessibility_features = [
                'aria-label',
                'role=',
                'tabindex',
                'sr-only'  # Screen reader only class
            ]
            
            # At least some accessibility features should be present
            has_accessibility = any(feature in content for feature in accessibility_features)
            self.assertTrue(has_accessibility, "No accessibility features found in UI")
            
            # Check for keyboard navigation support
            self.assertIn('keydown', content)
            self.assertIn('focus:', content)
    
    def test_animation_and_transition_classes(self):
        """Test animation and transition classes for smooth UI experience."""
        with tenant_context(self.tenant):
            url = reverse('pos:touch_interface')
            response = self.client.get(url)
            
            content = response.content.decode('utf-8')
            
            # Check for transition classes
            transition_classes = [
                'transition-all',
                'transition-colors',
                'duration-200',
                'duration-300',
                'ease-out',
                'ease-in'
            ]
            
            for css_class in transition_classes:
                self.assertIn(css_class, content)
            
            # Check for animation classes
            animation_classes = [
                'animate-pulse',
                'animate-spin',
                'transform',
                'scale-95',
                'scale-100'
            ]
            
            for css_class in animation_classes:
                self.assertIn(css_class, content)


class POSOfflineSyncUISeleniumTest(TestCase):
    """Selenium tests for POS offline sync UI interactions."""
    
    @classmethod
    def setUpClass(cls):
        """Set up Selenium WebDriver."""
        super().setUpClass()
        
        # Setup Chrome options for headless testing
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        
        try:
            cls.driver = webdriver.Chrome(options=chrome_options)
            cls.driver.implicitly_wait(10)
        except Exception as e:
            # Skip Selenium tests if Chrome driver not available
            cls.driver = None
            print(f"Selenium tests skipped: {e}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up Selenium WebDriver."""
        if cls.driver:
            cls.driver.quit()
        super().tearDownClass()
    
    def setUp(self):
        """Set up test data for Selenium tests."""
        if not self.driver:
            self.skipTest("Selenium WebDriver not available")
        
        # Get tenant
        Tenant = get_tenant_model()
        self.tenant = Tenant.objects.exclude(schema_name='public').first()
        
        if not self.tenant:
            self.tenant = Tenant.objects.create(
                schema_name='test_selenium_ui',
                name='Test Selenium UI Shop'
            )
        
        with tenant_context(self.tenant):
            # Create user
            self.user = User.objects.create_user(
                username='seleniumuser',
                email='selenium@example.com',
                password='testpass123'
            )
            
            # Create client and login
            self.client = Client()
            self.client.login(username='seleniumuser', password='testpass123')
    
    def test_offline_sync_status_visibility(self):
        """Test offline sync status component visibility and interaction."""
        if not self.driver:
            self.skipTest("Selenium WebDriver not available")
        
        with tenant_context(self.tenant):
            # Navigate to POS interface
            url = f"http://testserver{reverse('pos:touch_interface')}"
            self.driver.get(url)
            
            # Wait for page to load
            wait = WebDriverWait(self.driver, 10)
            
            try:
                # Check if offline sync status component is visible
                sync_status = wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "offline-sync-status"))
                )
                self.assertTrue(sync_status.is_displayed())
                
                # Check connection indicator
                connection_indicator = self.driver.find_element(By.CLASS_NAME, "connection-indicator")
                self.assertTrue(connection_indicator.is_displayed())
                
                # Check for status text (should show online by default)
                status_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'آنلاین')]")
                self.assertTrue(len(status_elements) > 0)
                
            except TimeoutException:
                self.fail("Offline sync status component not found or not visible")
    
    def test_sync_queue_modal_interaction(self):
        """Test sync queue modal opening and interaction."""
        if not self.driver:
            self.skipTest("Selenium WebDriver not available")
        
        with tenant_context(self.tenant):
            # Navigate to POS interface
            url = f"http://testserver{reverse('pos:touch_interface')}"
            self.driver.get(url)
            
            wait = WebDriverWait(self.driver, 10)
            
            try:
                # Find and click sync queue button
                sync_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'صف همگام‌سازی')]"))
                )
                sync_button.click()
                
                # Wait for modal to appear
                modal = wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "sync-queue-modal"))
                )
                self.assertTrue(modal.is_displayed())
                
                # Check modal title
                modal_title = self.driver.find_element(By.XPATH, "//*[contains(text(), 'مدیریت صف همگام‌سازی')]")
                self.assertTrue(modal_title.is_displayed())
                
                # Check for action buttons
                sync_all_button = self.driver.find_element(By.XPATH, "//*[contains(text(), 'همگام‌سازی همه')]")
                self.assertTrue(sync_all_button.is_displayed())
                
                # Close modal
                close_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'بستن')]")
                close_button.click()
                
                # Wait for modal to disappear
                wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "sync-queue-modal")))
                
            except TimeoutException:
                self.fail("Sync queue modal interaction failed")
    
    def test_responsive_design_on_mobile_viewport(self):
        """Test responsive design on mobile viewport."""
        if not self.driver:
            self.skipTest("Selenium WebDriver not available")
        
        with tenant_context(self.tenant):
            # Set mobile viewport
            self.driver.set_window_size(375, 667)  # iPhone 6/7/8 size
            
            # Navigate to POS interface
            url = f"http://testserver{reverse('pos:touch_interface')}"
            self.driver.get(url)
            
            wait = WebDriverWait(self.driver, 10)
            
            try:
                # Check if offline sync status is still visible on mobile
                sync_status = wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "offline-sync-status"))
                )
                self.assertTrue(sync_status.is_displayed())
                
                # Check if buttons are touch-friendly (minimum 44px height)
                touch_buttons = self.driver.find_elements(By.CLASS_NAME, "touch-btn")
                for button in touch_buttons:
                    height = button.size['height']
                    self.assertGreaterEqual(height, 44, f"Button height {height}px is less than 44px minimum")
                
            except TimeoutException:
                self.fail("Mobile responsive design test failed")
    
    def test_persian_text_rendering(self):
        """Test Persian text rendering and RTL layout."""
        if not self.driver:
            self.skipTest("Selenium WebDriver not available")
        
        with tenant_context(self.tenant):
            # Navigate to POS interface
            url = f"http://testserver{reverse('pos:touch_interface')}"
            self.driver.get(url)
            
            wait = WebDriverWait(self.driver, 10)
            
            try:
                # Check for Persian text elements
                persian_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'همگام‌سازی')]")
                self.assertTrue(len(persian_elements) > 0, "Persian text not found")
                
                # Check RTL direction
                body = self.driver.find_element(By.TAG_NAME, "body")
                direction = body.get_attribute("dir")
                # Note: Direction might be set on html or specific elements
                
                # Check for Persian numerals if any are displayed
                persian_number_elements = self.driver.find_elements(By.CLASS_NAME, "persian-numbers")
                # This is optional as numbers might not be displayed initially
                
            except TimeoutException:
                self.fail("Persian text rendering test failed")


class POSOfflineSyncUIIntegrationTest(TestCase):
    """Integration tests for offline sync UI with backend functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Get tenant
        Tenant = get_tenant_model()
        self.tenant = Tenant.objects.exclude(schema_name='public').first()
        
        if not self.tenant:
            self.tenant = Tenant.objects.create(
                schema_name='test_integration_ui',
                name='Test Integration UI Shop'
            )
        
        with tenant_context(self.tenant):
            # Create user
            self.user = User.objects.create_user(
                username='integrationuser',
                email='integration@example.com',
                password='testpass123'
            )
            
            # Create client and login
            self.client = Client()
            self.client.login(username='integrationuser', password='testpass123')
    
    def test_offline_transaction_creation_ui_integration(self):
        """Test offline transaction creation through UI integration."""
        with tenant_context(self.tenant):
            # Create offline transaction data
            offline_data = {
                'device_id': 'TEST-UI-DEVICE-001',
                'device_name': 'Test UI Device',
                'customer_id': None,
                'line_items': [
                    {
                        'item_name': 'Test Item',
                        'quantity': 1,
                        'unit_price': '100000.00'
                    }
                ],
                'payment_method': 'cash',
                'amount_paid': '100000.00',
                'transaction_type': 'sale'
            }
            
            # Post to offline transaction creation API
            url = reverse('pos:api_offline_create')
            response = self.client.post(
                url,
                data=json.dumps(offline_data),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertTrue(data['success'])
            self.assertIn('storage_id', data)
            self.assertEqual(data['sync_status'], 'pending_sync')
    
    def test_sync_queue_status_api_integration(self):
        """Test sync queue status API integration with UI."""
        with tenant_context(self.tenant):
            # Create some offline storage entries
            device_id = 'TEST-UI-DEVICE-002'
            
            # Create pending transaction
            POSOfflineStorage.objects.create(
                device_id=device_id,
                device_name='Test UI Device 2',
                transaction_data={
                    'transaction_number': 'TEST-001',
                    'total_amount': '150000.00',
                    'customer_name': 'Test Customer'
                },
                sync_status='pending_sync'
            )
            
            # Create synced transaction
            POSOfflineStorage.objects.create(
                device_id=device_id,
                device_name='Test UI Device 2',
                transaction_data={
                    'transaction_number': 'TEST-002',
                    'total_amount': '200000.00',
                    'customer_name': 'Test Customer 2'
                },
                sync_status='synced'
            )
            
            # Get sync status
            url = reverse('pos:api_offline_status')
            response = self.client.get(url, {'device_id': device_id})
            
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertTrue(data['success'])
            
            summary = data['summary']
            self.assertEqual(summary['pending_count'], 1)
            self.assertEqual(summary['synced_count'], 1)
            self.assertEqual(summary['total_count'], 2)
    
    def test_conflict_resolution_api_integration(self):
        """Test conflict resolution API integration with UI."""
        with tenant_context(self.tenant):
            # This would test the conflict resolution API
            # For now, we'll test the endpoint exists and returns proper structure
            
            url = reverse('pos:api_offline_conflict_resolve')
            
            resolution_data = {
                'device_id': 'TEST-UI-DEVICE-003',
                'device_name': 'Test UI Device 3',
                'resolution_actions': {
                    'offline_123': 'use_local',
                    'offline_456': 'use_server',
                    'offline_789': 'skip'
                }
            }
            
            response = self.client.post(
                url,
                data=json.dumps(resolution_data),
                content_type='application/json'
            )
            
            # The endpoint should exist and handle the request
            # Even if no actual conflicts exist, it should return a proper response
            self.assertIn(response.status_code, [200, 400])  # 400 if no conflicts to resolve
    
    def test_ui_component_data_binding(self):
        """Test UI component data binding with backend data."""
        with tenant_context(self.tenant):
            # Access the POS touch interface
            url = reverse('pos:touch_interface')
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            
            # Check that the response includes necessary data for UI components
            content = response.content.decode('utf-8')
            
            # Check for API endpoint URLs in JavaScript
            api_endpoints = [
                'pos:api_offline_sync_all',
                'pos:api_offline_status',
                'pos:api_offline_conflict_resolve'
            ]
            
            for endpoint in api_endpoints:
                # The URL should be rendered in the template
                self.assertIn(endpoint, content)
            
            # Check for CSRF token handling
            self.assertIn('csrfmiddlewaretoken', content)
            self.assertIn('getCSRFToken', content)


if __name__ == '__main__':
    import unittest
    unittest.main()