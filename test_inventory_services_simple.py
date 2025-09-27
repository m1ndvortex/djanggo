#!/usr/bin/env python
"""
Simple test script for inventory services.
"""

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from zargar.jewelry.services import (
    SerialNumberTrackingService,
    StockAlertService,
    InventoryValuationService,
    InventoryTrackingService
)
from unittest.mock import Mock
from decimal import Decimal

def test_serial_number_service():
    """Test SerialNumberTrackingService."""
    print("=== Testing SerialNumberTrackingService ===")
    
    # Test category code generation
    category = Mock()
    category.name = 'Rings'
    code = SerialNumberTrackingService._get_category_code(category)
    print(f"✅ Category code for 'Rings': {code}")
    assert code == 'RIN'
    
    category.name = 'Wedding Rings'
    code = SerialNumberTrackingService._get_category_code(category)
    print(f"✅ Category code for 'Wedding Rings': {code}")
    assert code == 'WED'
    
    category.name = 'AB'
    code = SerialNumberTrackingService._get_category_code(category)
    print(f"✅ Category code for 'AB': {code}")
    assert code == 'ABX'
    
    # Test serial number validation
    valid_serial = 'ZRG-2024-RIN-0001'
    result = SerialNumberTrackingService.validate_serial_number(valid_serial)
    print(f"✅ Valid serial '{valid_serial}': {result['valid']}")
    assert result['valid'] == True
    assert result['parsed']['prefix'] == 'ZRG'
    assert result['parsed']['year'] == 2024
    assert result['parsed']['category_code'] == 'RIN'
    assert result['parsed']['sequence'] == 1
    
    invalid_serial = 'INVALID-FORMAT'
    result = SerialNumberTrackingService.validate_serial_number(invalid_serial)
    print(f"✅ Invalid serial '{invalid_serial}': {result['valid']}")
    assert result['valid'] == False
    
    # Test constants
    print(f"✅ HIGH_VALUE_THRESHOLD: {SerialNumberTrackingService.HIGH_VALUE_THRESHOLD}")
    assert SerialNumberTrackingService.HIGH_VALUE_THRESHOLD == Decimal('50000000.00')
    
    print("✅ SerialNumberTrackingService tests passed\n")


def test_stock_alert_service():
    """Test StockAlertService."""
    print("=== Testing StockAlertService ===")
    
    # Test reorder priority calculation
    high_priority_data = {
        'shortage': 5,
        'value_at_risk': Decimal('100000000.00'),  # 100M Toman
        'days_since_low': 10
    }
    
    priority = StockAlertService._calculate_reorder_priority(high_priority_data)
    print(f"✅ High priority calculation: {priority}")
    assert priority > 80
    
    low_priority_data = {
        'shortage': 1,
        'value_at_risk': Decimal('5000000.00'),  # 5M Toman
        'days_since_low': 1
    }
    
    priority = StockAlertService._calculate_reorder_priority(low_priority_data)
    print(f"✅ Low priority calculation: {priority}")
    assert priority < 30
    
    # Test monthly demand estimation
    item = Mock()
    item.category = Mock()
    
    item.category.name = 'rings'
    demand = StockAlertService._estimate_monthly_demand(item)
    print(f"✅ Monthly demand for rings: {demand}")
    assert demand == 3
    
    item.category.name = 'earrings'
    demand = StockAlertService._estimate_monthly_demand(item)
    print(f"✅ Monthly demand for earrings: {demand}")
    assert demand == 4
    
    item.category.name = 'unknown'
    demand = StockAlertService._estimate_monthly_demand(item)
    print(f"✅ Monthly demand for unknown: {demand}")
    assert demand == 1
    
    # Test constants
    print(f"✅ CACHE_TIMEOUT: {StockAlertService.CACHE_TIMEOUT}")
    assert StockAlertService.CACHE_TIMEOUT == 3600
    
    print("✅ StockAlertService tests passed\n")


def test_inventory_valuation_service():
    """Test InventoryValuationService."""
    print("=== Testing InventoryValuationService ===")
    
    # Test constants
    print(f"✅ CACHE_KEY_PREFIX: {InventoryValuationService.CACHE_KEY_PREFIX}")
    assert InventoryValuationService.CACHE_KEY_PREFIX == 'inventory_valuation'
    
    print(f"✅ CACHE_TIMEOUT: {InventoryValuationService.CACHE_TIMEOUT}")
    assert InventoryValuationService.CACHE_TIMEOUT == 1800
    
    print("✅ InventoryValuationService tests passed\n")


def test_inventory_tracking_service():
    """Test InventoryTrackingService."""
    print("=== Testing InventoryTrackingService ===")
    
    # Test that service exists and can be imported
    print("✅ InventoryTrackingService imported successfully")
    
    # Test that methods exist
    assert hasattr(InventoryTrackingService, 'get_comprehensive_inventory_status')
    assert hasattr(InventoryTrackingService, 'perform_daily_maintenance')
    
    print("✅ InventoryTrackingService tests passed\n")


def main():
    """Run all tests."""
    print("🚀 Starting inventory services tests...\n")
    
    try:
        test_serial_number_service()
        test_stock_alert_service()
        test_inventory_valuation_service()
        test_inventory_tracking_service()
        
        print("🎉 All inventory services tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == '__main__':
    main()