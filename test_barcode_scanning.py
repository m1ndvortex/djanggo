#!/usr/bin/env python
"""
Test barcode scanning functionality.
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.insert(0, '/app')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')

# Setup Django
django.setup()

def test_barcode_scanning():
    """Test barcode scanning functionality."""
    from django_tenants.utils import schema_context
    from zargar.tenants.models import Tenant
    from zargar.jewelry.models import JewelryItem
    from zargar.jewelry.barcode_services import BarcodeScanningService
    
    # Get test tenant
    tenant = Tenant.objects.get(schema_name='test_barcode')
    
    # Work within tenant schema
    with schema_context(tenant.schema_name):
        try:
            # Get the jewelry item we created earlier
            jewelry_item = JewelryItem.objects.get(sku='TEST-BARCODE-001')
            print(f"✓ Found jewelry item: {jewelry_item.name}")
            print(f"✓ Item barcode: {jewelry_item.barcode}")
            
            # Test barcode scanning
            service = BarcodeScanningService()
            
            # Test scanning by barcode
            result = service.scan_barcode(
                jewelry_item.barcode,
                scan_action='inventory_check',
                scanner_device='test_scanner',
                location='test_location',
                notes='Integration test scan'
            )
            
            if result['success']:
                print("✓ Barcode scan successful")
                print(f"✓ Found item: {result['jewelry_item'].name}")
                print(f"✓ Scan history ID: {result['scan_history'].id}")
            else:
                print(f"✗ Barcode scan failed: {result['error']}")
                return False
            
            # Test scanning by SKU
            result2 = service.scan_barcode(
                jewelry_item.sku,
                scan_action='lookup',
                scanner_device='test_scanner'
            )
            
            if result2['success']:
                print("✓ SKU scan successful")
                print(f"✓ Found item: {result2['jewelry_item'].name}")
            else:
                print(f"✗ SKU scan failed: {result2['error']}")
                return False
            
            # Test scan history
            history = service.get_scan_history(jewelry_item, limit=10)
            print(f"✓ Scan history entries: {len(history)}")
            
            # Test scan statistics
            stats = service.get_scan_statistics(jewelry_item)
            print(f"✓ Total scans for item: {stats['total_scans']}")
            
            # Test invalid barcode
            result3 = service.scan_barcode('INVALID-BARCODE-123')
            if not result3['success']:
                print("✓ Invalid barcode correctly rejected")
            else:
                print("✗ Invalid barcode should have been rejected")
                return False
            
            return True
            
        except Exception as e:
            print(f"✗ Scanning test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Run scanning test."""
    print("Testing barcode scanning functionality...")
    
    if test_barcode_scanning():
        print("\n✓ All scanning tests passed!")
        return 0
    else:
        print("\n✗ Scanning tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())