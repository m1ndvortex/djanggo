#!/usr/bin/env python
"""
Integration test for barcode system with database.
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

def test_barcode_integration():
    """Test barcode system integration with database."""
    from django_tenants.utils import schema_context
    from zargar.tenants.models import Tenant
    from zargar.jewelry.models import JewelryItem, Category
    from zargar.jewelry.barcode_models import BarcodeGeneration
    from zargar.jewelry.barcode_services import BarcodeGenerationService
    
    # Create or get test tenant
    tenant, created = Tenant.objects.get_or_create(
        schema_name='test_barcode',
        defaults={
            'name': 'Test Barcode Shop',
            'owner_name': 'Test Owner',
            'owner_email': 'test@example.com'
        }
    )
    
    if created:
        print("✓ Created test tenant")
    else:
        print("✓ Using existing test tenant")
    
    # Work within tenant schema
    with schema_context(tenant.schema_name):
        try:
            # Create test category
            category, created = Category.objects.get_or_create(
                name='Test Rings',
                defaults={'name_persian': 'حلقه تست'}
            )
            
            # Create test jewelry item
            jewelry_item, created = JewelryItem.objects.get_or_create(
                sku='TEST-BARCODE-001',
                defaults={
                    'name': 'Test Gold Ring for Barcode',
                    'category': category,
                    'weight_grams': Decimal('5.500'),
                    'karat': 18,
                    'manufacturing_cost': Decimal('500000'),
                    'selling_price': Decimal('2000000')
                }
            )
            
            print(f"✓ Created/found jewelry item: {jewelry_item.name}")
            
            # Test barcode generation
            service = BarcodeGenerationService()
            
            # Generate barcode data
            barcode_data = service.generate_barcode_data(jewelry_item)
            print(f"✓ Generated barcode data: {barcode_data}")
            
            # Generate QR code
            qr_data, qr_image = service.generate_qr_code(jewelry_item)
            print(f"✓ Generated QR code data (length: {len(qr_data)})")
            if qr_image:
                print(f"✓ Generated QR code image: {qr_image.name}")
            else:
                print("! QR code image not generated (PIL not available)")
            
            # Generate and save barcode for item
            barcode_gen = service.generate_barcode_for_item(jewelry_item)
            print(f"✓ Created barcode generation record: {barcode_gen.id}")
            
            # Verify barcode was saved
            jewelry_item.refresh_from_db()
            print(f"✓ Jewelry item barcode updated: {jewelry_item.barcode}")
            
            # Verify database record
            barcode_count = BarcodeGeneration.objects.filter(
                jewelry_item=jewelry_item,
                is_active=True
            ).count()
            print(f"✓ Active barcode generations in DB: {barcode_count}")
            
            return True
            
        except Exception as e:
            print(f"✗ Integration test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Run integration test."""
    print("Testing barcode system integration...")
    
    if test_barcode_integration():
        print("\n✓ All integration tests passed!")
        return 0
    else:
        print("\n✗ Integration tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())