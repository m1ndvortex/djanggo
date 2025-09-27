#!/usr/bin/env python
"""
Basic test to verify barcode system imports and functionality.
"""
import os
import sys
import django
from decimal import Decimal

# Add the project directory to Python path
sys.path.insert(0, '/app')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')

# Setup Django
django.setup()

def test_barcode_imports():
    """Test that barcode models can be imported."""
    try:
        from zargar.jewelry.barcode_models import (
            BarcodeGeneration, BarcodeScanHistory, BarcodeTemplate, 
            BarcodeSettings, BarcodeType
        )
        print("✓ Barcode models imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import barcode models: {e}")
        return False

def test_barcode_services():
    """Test that barcode services can be imported."""
    try:
        from zargar.jewelry.barcode_services import (
            BarcodeGenerationService, BarcodeScanningService,
            BarcodeTemplateService, BarcodeSettingsService
        )
        print("✓ Barcode services imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import barcode services: {e}")
        return False

def test_basic_functionality():
    """Test basic barcode functionality."""
    try:
        from zargar.jewelry.barcode_services import BarcodeGenerationService
        from zargar.jewelry.models import JewelryItem, Category
        
        # Create service instance
        service = BarcodeGenerationService()
        
        # Test barcode data generation (without database)
        class MockItem:
            def __init__(self):
                self.sku = 'TEST-001'
                self.name = 'Test Item'
                self.category = MockCategory()
        
        class MockCategory:
            def __init__(self):
                self.name = 'Test Category'
        
        mock_item = MockItem()
        barcode_data = service.generate_barcode_data(mock_item)
        
        print(f"✓ Generated barcode data: {barcode_data}")
        return True
        
    except Exception as e:
        print(f"✗ Failed basic functionality test: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing barcode system...")
    
    tests = [
        test_barcode_imports,
        test_barcode_services,
        test_basic_functionality
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())