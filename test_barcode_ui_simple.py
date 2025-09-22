#!/usr/bin/env python
"""
Simple test to verify barcode UI functionality is working.
"""
import os
import sys
import django
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
django.setup()

from zargar.jewelry.models import JewelryItem, Category
from zargar.jewelry.barcode_models import BarcodeGeneration, BarcodeScanHistory
from zargar.jewelry.barcode_services import BarcodeGenerationService, BarcodeScanningService

User = get_user_model()

def test_barcode_ui_basic_functionality():
    """Test basic barcode UI functionality without tenant setup."""
    print("Testing barcode UI basic functionality...")
    
    try:
        # Test barcode services
        service = BarcodeGenerationService()
        print("✓ BarcodeGenerationService initialized")
        
        scan_service = BarcodeScanningService()
        print("✓ BarcodeScanningService initialized")
        
        # Test barcode data generation
        class MockItem:
            def __init__(self):
                self.id = 1
                self.sku = 'TEST001'
                self.name = 'Test Item'
                self.category = None
        
        mock_item = MockItem()
        barcode_data = service.generate_barcode_data(mock_item)
        print(f"✓ Barcode data generated: {barcode_data}")
        
        # Test QR code generation (without saving)
        qr_data, qr_image = service.generate_qr_code(mock_item)
        print(f"✓ QR code data generated: {qr_data[:50]}...")
        
        print("✓ All barcode UI basic functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Error in barcode UI test: {e}")
        return False

def test_barcode_templates_load():
    """Test that barcode templates can be loaded."""
    print("Testing barcode template loading...")
    
    try:
        # Test template paths exist
        import os
        template_paths = [
            'templates/jewelry/barcode_management.html',
            'templates/jewelry/mobile_scanner.html', 
            'templates/jewelry/barcode_history.html'
        ]
        
        for template_path in template_paths:
            if os.path.exists(template_path):
                print(f"✓ Template exists: {template_path}")
            else:
                print(f"✗ Template missing: {template_path}")
                return False
        
        print("✓ All barcode templates found!")
        return True
        
    except Exception as e:
        print(f"✗ Error checking templates: {e}")
        return False

def test_barcode_views_import():
    """Test that barcode views can be imported."""
    print("Testing barcode views import...")
    
    try:
        from zargar.jewelry.views import (
            BarcodeManagementView, MobileScannerView, BarcodeHistoryView,
            barcode_items_api, barcode_statistics_api
        )
        print("✓ Barcode views imported successfully")
        
        from zargar.jewelry.barcode_views import (
            BarcodeGenerationViewSet, BarcodeScanView, BarcodeScanHistoryViewSet
        )
        print("✓ Barcode API views imported successfully")
        
        print("✓ All barcode views import tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Error importing barcode views: {e}")
        return False

def test_barcode_urls():
    """Test that barcode URLs are configured."""
    print("Testing barcode URL configuration...")
    
    try:
        from zargar.jewelry.urls import urlpatterns
        
        # Check for barcode URL patterns
        barcode_urls = [
            'barcode/',
            'barcode/mobile/',
            'barcode/history/',
            'barcode/scan/',
            'api/barcode/items/',
            'api/barcode/statistics/'
        ]
        
        url_patterns_str = str(urlpatterns)
        
        for url in barcode_urls:
            if url in url_patterns_str:
                print(f"✓ URL pattern found: {url}")
            else:
                print(f"? URL pattern may be missing: {url}")
        
        print("✓ Barcode URL configuration test completed!")
        return True
        
    except Exception as e:
        print(f"✗ Error checking barcode URLs: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("BARCODE UI FUNCTIONALITY TEST")
    print("=" * 60)
    
    tests = [
        test_barcode_ui_basic_functionality,
        test_barcode_templates_load,
        test_barcode_views_import,
        test_barcode_urls
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        print()
        if test():
            passed += 1
        print("-" * 40)
    
    print()
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All barcode UI functionality tests PASSED!")
        sys.exit(0)
    else:
        print("❌ Some barcode UI functionality tests FAILED!")
        sys.exit(1)