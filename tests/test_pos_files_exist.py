"""
Basic tests to verify POS touch interface files exist and contain required content.
"""
import os
import unittest


class POSFilesExistTests(unittest.TestCase):
    """Test that POS files exist and contain required content."""
    
    def test_pos_templates_exist(self):
        """Test that POS templates exist."""
        template_files = [
            'templates/pos/touch_interface.html',
            'templates/pos/base_pos.html',
            'templates/pos/components/customer_lookup_modal.html',
            'templates/pos/components/inventory_search_modal.html',
            'templates/pos/components/calculator_modal.html'
        ]
        
        for template_file in template_files:
            self.assertTrue(os.path.exists(template_file), f"Template {template_file} does not exist")
    
    def test_pos_static_files_exist(self):
        """Test that POS static files exist."""
        static_files = [
            'static/css/pos-interface.css',
            'static/js/pos-interface.js'
        ]
        
        for static_file in static_files:
            self.assertTrue(os.path.exists(static_file), f"Static file {static_file} does not exist")
    
    def test_touch_interface_template_content(self):
        """Test touch interface template contains required content."""
        template_path = 'templates/pos/touch_interface.html'
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for key elements
        required_elements = [
            'سیستم فروش لمسی',  # Touch POS System
            'touch-btn',
            'large-touch',
            'high-contrast',
            'x-data="touchPOSInterface()"',
            'افزودن کالا',  # Add Item
            'ماشین حساب',  # Calculator
            'قیمت طلا',  # Gold Price
            'تکمیل تراکنش'  # Complete Transaction
        ]
        
        for element in required_elements:
            self.assertIn(element, content, f"Required element '{element}' not found in touch interface template")
    
    def test_pos_css_touch_optimizations(self):
        """Test POS CSS contains touch optimizations."""
        css_path = 'static/css/pos-interface.css'
        
        with open(css_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for touch-specific CSS
        touch_features = [
            'touch-btn',
            'large-touch',
            'high-contrast',
            'min-height: 44px',  # iOS minimum touch target
            'touch-action: manipulation',
            'user-select: none',
            '-webkit-tap-highlight-color: transparent',
            '@media (max-width: 768px)',  # Mobile responsive
            'pos-grid'
        ]
        
        for feature in touch_features:
            self.assertIn(feature, content, f"Touch feature '{feature}' not found in CSS")
    
    def test_pos_css_persian_support(self):
        """Test POS CSS contains Persian/RTL support."""
        css_path = 'static/css/pos-interface.css'
        
        with open(css_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for Persian/RTL features
        persian_features = [
            'persian-display',
            'persian-numbers',
            'Vazirmatn',
            'font-variant-numeric: tabular-nums'
        ]
        
        for feature in persian_features:
            self.assertIn(feature, content, f"Persian feature '{feature}' not found in CSS")
    
    def test_pos_javascript_functionality(self):
        """Test POS JavaScript contains required functionality."""
        js_path = 'static/js/pos-interface.js'
        
        with open(js_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for required JavaScript features
        js_features = [
            'class POSInterface',
            'setupTouchOptimizations',
            'setupOfflineHandling',
            'formatCurrency',
            'toPersianDigits',
            'toEnglishDigits',
            'showNotification',
            'updateGoldPrices',
            'touchstart',
            'touchend'
        ]
        
        for feature in js_features:
            self.assertIn(feature, content, f"JavaScript feature '{feature}' not found")
    
    def test_customer_lookup_modal_content(self):
        """Test customer lookup modal contains required content."""
        modal_path = 'templates/pos/components/customer_lookup_modal.html'
        
        with open(modal_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for modal features
        modal_features = [
            'جستجوی مشتری',  # Customer Search
            'x-data="customerLookupModal()"',
            'searchCustomers()',
            'selectCustomer',
            'مشتری نقدی'  # Cash Customer
        ]
        
        for feature in modal_features:
            self.assertIn(feature, content, f"Modal feature '{feature}' not found")
    
    def test_inventory_search_modal_content(self):
        """Test inventory search modal contains required content."""
        modal_path = 'templates/pos/components/inventory_search_modal.html'
        
        with open(modal_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for modal features
        modal_features = [
            'جستجوی محصولات',  # Product Search
            'x-data="inventorySearchModal()"',
            'searchItems()',
            'selectItem',
            'filterByCategory'
        ]
        
        for feature in modal_features:
            self.assertIn(feature, content, f"Modal feature '{feature}' not found")
    
    def test_calculator_modal_content(self):
        """Test calculator modal contains required content."""
        modal_path = 'templates/pos/components/calculator_modal.html'
        
        with open(modal_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for calculator features
        calculator_features = [
            'ماشین حساب طلا',  # Gold Calculator
            'x-data="posCalculatorModal()"',
            'inputNumber',
            'calculate()',
            'setGoldPrice',
            'calculateGoldValue',
            'قیمت طلا (تومان در گرم)'  # Gold Price (Toman per gram)
        ]
        
        for feature in calculator_features:
            self.assertIn(feature, content, f"Calculator feature '{feature}' not found")
    
    def test_base_pos_template_content(self):
        """Test base POS template contains required content."""
        template_path = 'templates/pos/base_pos.html'
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for base template features
        base_features = [
            'extends "base_rtl.html"',
            'سیستم فروش',  # POS System
            'pos-navbar',
            'connection-status',
            'current-gold-price',
            'user-scalable=no',  # Touch optimization
            'mobile-web-app-capable'  # PWA support
        ]
        
        for feature in base_features:
            self.assertIn(feature, content, f"Base template feature '{feature}' not found")
    
    def test_responsive_design_in_templates(self):
        """Test responsive design classes in templates."""
        template_path = 'templates/pos/touch_interface.html'
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for responsive design classes
        responsive_classes = [
            'grid-cols-1',
            'md:grid-cols-2',
            'lg:grid-cols-3',
            'max-w-',
            'sm:flex',
            'md:block',
            'lg:grid'
        ]
        
        responsive_found = any(cls in content for cls in responsive_classes)
        self.assertTrue(responsive_found, "No responsive design classes found in touch interface")
    
    def test_persian_ui_text_in_templates(self):
        """Test Persian UI text in templates."""
        template_files = [
            'templates/pos/touch_interface.html',
            'templates/pos/base_pos.html'
        ]
        
        persian_texts = [
            'سیستم فروش',  # POS System
            'تراکنش جاری',  # Current Transaction
            'افزودن کالا',  # Add Item
            'ماشین حساب',  # Calculator
            'قیمت طلا',  # Gold Price
            'جستجوی کالا',  # Search Items
            'انتخاب مشتری',  # Select Customer
            'تکمیل تراکنش'  # Complete Transaction
        ]
        
        for template_file in template_files:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # At least some Persian text should be present
            persian_found = any(text in content for text in persian_texts)
            self.assertTrue(persian_found, f"No Persian UI text found in {template_file}")


if __name__ == '__main__':
    unittest.main()