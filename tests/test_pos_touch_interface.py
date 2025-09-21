"""
Tests for POS touch-optimized interface.
Tests responsiveness, touch optimization, and Persian UI functionality.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing models
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock

from zargar.tenants.models import Tenant, Domain
from zargar.pos.models import POSTransaction, POSTransactionLineItem
from zargar.customers.models import Customer
from zargar.jewelry.models import JewelryItem, Category

User = get_user_model()


class POSTouchInterfaceTestCase(TestCase):
    """Base test case for POS touch interface tests."""
    
    def setUp(self):
        """Set up test data."""
        # Create tenant
        self.tenant = Tenant.objects.create(
            name="Test Jewelry Shop",
            schema_name="test_jewelry",
            paid_until=timezone.now().date(),
            on_trial=False
        )
        
        # Create domain
        self.domain = Domain.objects.create(
            domain="testjewelry.zargar.local",
            tenant=self.tenant,
            is_primary=True
        )
        
        # Set tenant in connection
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            # Create user
            self.user = User.objects.create_user(
                username='testuser',
                password='testpass123',
                role='owner'
            )
            
            # Create test customer
            self.customer = Customer.objects.create(
                persian_first_name='علی',
                persian_last_name='احمدی',
                phone_number='09123456789',
                email='ali@example.com'
            )
            
            # Create jewelry category
            self.category = Category.objects.create(
                name='Ring',
                name_persian='انگشتر'
            )
            
            # Create jewelry item
            self.jewelry_item = JewelryItem.objects.create(
                name='Gold Ring',
                name_persian='انگشتر طلا',
                category=self.category,
                sku='RING001',
                weight_grams=Decimal('5.500'),
                karat=18,
                manufacturing_cost=Decimal('500000'),
                selling_price=Decimal('2500000'),
                quantity=10,
                status='in_stock'
            )
        
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')


class POSTouchInterfaceViewTests(POSTouchInterfaceTestCase):
    """Test POS touch interface view."""
    
    def test_touch_interface_loads(self):
        """Test that touch interface loads successfully."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'سیستم فروش لمسی')
            self.assertContains(response, 'تراکنش جاری')
            self.assertContains(response, 'قیمت طلا')
    
    def test_touch_interface_context_data(self):
        """Test that touch interface includes required context data."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            self.assertIn('today_stats', response.context)
            self.assertIn('sales_count', response.context['today_stats'])
            self.assertIn('total_sales', response.context['today_stats'])
            self.assertIn('gold_weight', response.context['today_stats'])
    
    def test_touch_interface_responsive_meta_tags(self):
        """Test that touch interface includes responsive meta tags."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for mobile-optimized viewport
            self.assertContains(response, 'user-scalable=no')
            self.assertContains(response, 'maximum-scale=1.0')
            self.assertContains(response, 'minimum-scale=1.0')
            
            # Check for mobile app capabilities
            self.assertContains(response, 'mobile-web-app-capable')
            self.assertContains(response, 'apple-mobile-web-app-capable')
    
    def test_touch_interface_persian_ui_elements(self):
        """Test that touch interface includes Persian UI elements."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for Persian text
            self.assertContains(response, 'افزودن کالا')
            self.assertContains(response, 'ماشین حساب')
            self.assertContains(response, 'جستجوی کالا')
            self.assertContains(response, 'انتخاب مشتری')
            self.assertContains(response, 'تکمیل تراکنش')
    
    def test_touch_interface_large_buttons(self):
        """Test that touch interface includes large touch-friendly buttons."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for touch-optimized CSS classes
            self.assertContains(response, 'touch-btn')
            self.assertContains(response, 'large-touch')
            self.assertContains(response, 'high-contrast')


class POSAPIEndpointTests(POSTouchInterfaceTestCase):
    """Test POS API endpoints for touch interface."""
    
    def test_today_stats_api(self):
        """Test today's statistics API endpoint."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            # Create a test transaction
            transaction = POSTransaction.objects.create(
                customer=self.customer,
                transaction_type='sale',
                status='completed',
                subtotal=Decimal('2500000'),
                total_amount=Decimal('2500000'),
                amount_paid=Decimal('2500000'),
                gold_price_18k_at_transaction=Decimal('3500000'),
                total_gold_weight_grams=Decimal('5.500')
            )
            
            response = self.client.get(reverse('pos:api_today_stats'))
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            
            self.assertTrue(data['success'])
            self.assertEqual(data['stats']['sales_count'], 1)
            self.assertEqual(data['stats']['total_sales'], 2500000.0)
            self.assertEqual(data['stats']['gold_weight'], 5.5)
    
    def test_recent_transactions_api(self):
        """Test recent transactions API endpoint."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            # Create test transactions
            transaction1 = POSTransaction.objects.create(
                customer=self.customer,
                transaction_type='sale',
                status='completed',
                subtotal=Decimal('1000000'),
                total_amount=Decimal('1000000'),
                amount_paid=Decimal('1000000')
            )
            
            transaction2 = POSTransaction.objects.create(
                transaction_type='sale',
                status='completed',
                subtotal=Decimal('500000'),
                total_amount=Decimal('500000'),
                amount_paid=Decimal('500000')
            )
            
            response = self.client.get(reverse('pos:api_recent_transactions'))
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            
            self.assertTrue(data['success'])
            self.assertEqual(len(data['transactions']), 2)
            
            # Check transaction data structure
            transaction_data = data['transactions'][0]
            self.assertIn('transaction_number', transaction_data)
            self.assertIn('total_amount', transaction_data)
            self.assertIn('transaction_date_shamsi', transaction_data)
    
    @patch('zargar.gold_installments.services.GoldPriceService.get_current_gold_price')
    def test_gold_price_api(self, mock_gold_price):
        """Test gold price API endpoint."""
        # Mock gold price service
        mock_gold_price.return_value = {
            'price_per_gram': Decimal('3500000'),
            'karat': 18,
            'timestamp': timezone.now(),
            'source': 'test'
        }
        
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:api_gold_price'))
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            
            self.assertTrue(data['success'])
            self.assertIn('price_data', data)
            self.assertEqual(data['price_data']['karat'], 18)
            self.assertEqual(data['price_data']['price_per_gram'], '3500000')
    
    def test_customer_lookup_api(self):
        """Test customer lookup API endpoint."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(
                reverse('pos:api_customer_lookup') + '?q=علی'
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            
            self.assertTrue(data['success'])
            self.assertEqual(len(data['customers']), 1)
            
            customer_data = data['customers'][0]
            self.assertEqual(customer_data['id'], self.customer.id)
            self.assertIn('علی', customer_data['name'])
            self.assertEqual(customer_data['phone'], '09123456789')
    
    def test_jewelry_search_api(self):
        """Test jewelry item search API endpoint."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(
                reverse('pos:api_jewelry_search') + '?q=Gold'
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            
            self.assertTrue(data['success'])
            self.assertEqual(len(data['items']), 1)
            
            item_data = data['items'][0]
            self.assertEqual(item_data['id'], self.jewelry_item.id)
            self.assertEqual(item_data['name'], 'Gold Ring')
            self.assertEqual(item_data['sku'], 'RING001')
            self.assertEqual(item_data['karat'], 18)


class POSTouchOptimizationTests(POSTouchInterfaceTestCase):
    """Test touch optimization features."""
    
    def test_touch_css_classes_present(self):
        """Test that touch-optimized CSS classes are present."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for touch-specific CSS classes
            self.assertContains(response, 'touch-btn')
            self.assertContains(response, 'large-touch')
            self.assertContains(response, 'high-contrast')
            self.assertContains(response, 'pos-grid')
    
    def test_mobile_viewport_configuration(self):
        """Test mobile viewport configuration."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check viewport meta tag
            self.assertContains(
                response, 
                'width=device-width, initial-scale=1.0, user-scalable=no'
            )
    
    def test_touch_friendly_button_sizes(self):
        """Test that buttons meet minimum touch target sizes."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for minimum touch target CSS
            self.assertContains(response, 'min-height: 60px')
            self.assertContains(response, 'min-width: 60px')
    
    def test_persian_number_formatting(self):
        """Test Persian number formatting in interface."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for Persian number CSS classes
            self.assertContains(response, 'persian-numbers')
            self.assertContains(response, 'persian-display')


class POSResponsivenessTests(POSTouchInterfaceTestCase):
    """Test responsive design features."""
    
    def test_responsive_grid_layout(self):
        """Test responsive grid layout CSS."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for responsive grid classes
            self.assertContains(response, 'grid-cols-1')
            self.assertContains(response, 'md:grid-cols-2')
            self.assertContains(response, 'lg:grid-cols-3')
    
    def test_mobile_first_design(self):
        """Test mobile-first responsive design."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for mobile-first breakpoints
            self.assertContains(response, '@media (max-width: 768px)')
            self.assertContains(response, '@media (min-width: 769px)')
    
    def test_tablet_optimization(self):
        """Test tablet-specific optimizations."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for tablet-optimized elements
            self.assertContains(response, 'tablet-friendly')
            self.assertContains(response, 'touch-optimized')


class POSPersianUITests(POSTouchInterfaceTestCase):
    """Test Persian UI and RTL layout."""
    
    def test_rtl_layout(self):
        """Test RTL layout configuration."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for RTL direction
            self.assertContains(response, 'dir="rtl"')
            self.assertContains(response, 'lang="fa"')
    
    def test_persian_fonts(self):
        """Test Persian font configuration."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for Persian fonts
            self.assertContains(response, 'Vazirmatn')
            self.assertContains(response, 'font-vazir')
    
    def test_persian_text_content(self):
        """Test Persian text content."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for Persian UI text
            persian_texts = [
                'سیستم فروش لمسی',
                'تراکنش جاری',
                'افزودن کالا',
                'ماشین حساب',
                'قیمت طلا',
                'جستجوی کالا',
                'انتخاب مشتری',
                'تکمیل تراکنش'
            ]
            
            for text in persian_texts:
                self.assertContains(response, text)
    
    def test_persian_number_display(self):
        """Test Persian number display functionality."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for Persian number formatting JavaScript
            self.assertContains(response, 'toPersianDigits')
            self.assertContains(response, 'formatCurrency')


class POSModalComponentTests(POSTouchInterfaceTestCase):
    """Test POS modal components."""
    
    def test_customer_lookup_modal_present(self):
        """Test customer lookup modal is included."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            self.assertContains(response, 'customerLookupModal')
            self.assertContains(response, 'جستجوی مشتری')
    
    def test_inventory_search_modal_present(self):
        """Test inventory search modal is included."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            self.assertContains(response, 'inventorySearchModal')
            self.assertContains(response, 'جستجوی محصولات')
    
    def test_calculator_modal_present(self):
        """Test calculator modal is included."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            self.assertContains(response, 'posCalculatorModal')
            self.assertContains(response, 'ماشین حساب طلا')


class POSJavaScriptFunctionalityTests(POSTouchInterfaceTestCase):
    """Test JavaScript functionality."""
    
    def test_alpine_js_components(self):
        """Test Alpine.js components are present."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for Alpine.js data components
            self.assertContains(response, 'x-data="touchPOSInterface()"')
            self.assertContains(response, 'x-init="init()"')
    
    def test_pos_interface_javascript(self):
        """Test POS interface JavaScript is included."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for JavaScript includes
            self.assertContains(response, 'pos-interface.js')
    
    def test_event_listeners_setup(self):
        """Test event listeners are set up."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for event listener setup
            self.assertContains(response, 'customer-selected')
            self.assertContains(response, 'inventory-item-selected')


class POSAccessibilityTests(POSTouchInterfaceTestCase):
    """Test accessibility features."""
    
    def test_aria_labels_present(self):
        """Test ARIA labels are present for accessibility."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for ARIA labels
            self.assertContains(response, 'aria-label')
    
    def test_keyboard_navigation_support(self):
        """Test keyboard navigation support."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for keyboard event handling
            self.assertContains(response, '@keydown.escape')
    
    def test_focus_management(self):
        """Test focus management for modals."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for focus management
            self.assertContains(response, '$nextTick')
            self.assertContains(response, 'focus()')


@pytest.mark.django_db
class POSPerformanceTests(POSTouchInterfaceTestCase):
    """Test performance aspects of POS interface."""
    
    def test_minimal_database_queries(self):
        """Test that interface loads with minimal database queries."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            with self.assertNumQueries(5):  # Adjust based on actual requirements
                response = self.client.get(reverse('pos:touch_interface'))
                self.assertEqual(response.status_code, 200)
    
    def test_static_file_optimization(self):
        """Test static file optimization."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Check for optimized static file loading
            self.assertContains(response, 'defer')  # Deferred JavaScript loading
    
    def test_caching_headers(self):
        """Test appropriate caching headers."""
        from django_tenants.utils import tenant_context
        with tenant_context(self.tenant):
            response = self.client.get(reverse('pos:touch_interface'))
            
            # Interface should not be cached due to dynamic content
            self.assertNotIn('Cache-Control', response)


if __name__ == '__main__':
    pytest.main([__file__])