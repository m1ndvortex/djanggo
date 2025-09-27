#!/usr/bin/env python
"""
Demonstration script for jewelry inventory management models.

This script demonstrates:
- Creating jewelry categories, gemstones, and items
- Model relationships and properties
- Gold value calculations
- Persian localization support
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from zargar.jewelry.models import Category, Gemstone, JewelryItem, JewelryItemPhoto
from zargar.core.models import User


def main():
    """Demonstrate jewelry inventory models."""
    print("🔸 ZARGAR Jewelry Inventory Models Demonstration")
    print("=" * 60)
    
    # Create a test user (in a real scenario, this would be done through proper authentication)
    try:
        user = User.objects.get(username='demo_user')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='demo_user',
            email='demo@zargar.com',
            password='demo123',
            role='owner',
            persian_first_name='علی',
            persian_last_name='احمدی'
        )
        print(f"✅ Created demo user: {user.full_persian_name}")
    
    # 1. Create Categories
    print("\n📂 Creating Jewelry Categories:")
    
    ring_category = Category.objects.get_or_create(
        name='Rings',
        defaults={
            'name_persian': 'انگشتر',
            'description': 'Wedding and engagement rings',
            'created_by': user
        }
    )[0]
    print(f"   • {ring_category}")
    
    necklace_category = Category.objects.get_or_create(
        name='Necklaces',
        defaults={
            'name_persian': 'گردنبند',
            'description': 'Gold and silver necklaces',
            'created_by': user
        }
    )[0]
    print(f"   • {necklace_category}")
    
    # 2. Create Gemstones
    print("\n💎 Creating Gemstones:")
    
    diamond = Gemstone.objects.get_or_create(
        name='Premium Diamond',
        defaults={
            'gemstone_type': 'diamond',
            'carat_weight': Decimal('1.250'),
            'cut_grade': 'excellent',
            'color_grade': 'D',
            'clarity_grade': 'VVS1',
            'certification_number': 'GIA-123456789',
            'certification_authority': 'GIA',
            'purchase_price': Decimal('50000000.00'),  # 50M Toman
            'created_by': user
        }
    )[0]
    print(f"   • {diamond}")
    
    ruby = Gemstone.objects.get_or_create(
        name='Burmese Ruby',
        defaults={
            'gemstone_type': 'ruby',
            'carat_weight': Decimal('2.000'),
            'cut_grade': 'excellent',
            'color_grade': 'Pigeon Blood',
            'clarity_grade': 'VVS2',
            'certification_number': 'SSEF-987654321',
            'certification_authority': 'SSEF',
            'purchase_price': Decimal('75000000.00'),  # 75M Toman
            'created_by': user
        }
    )[0]
    print(f"   • {ruby}")
    
    # 3. Create Jewelry Items
    print("\n💍 Creating Jewelry Items:")
    
    # Diamond Ring
    diamond_ring = JewelryItem.objects.get_or_create(
        sku='RING-DIA-001',
        defaults={
            'name': 'Premium Diamond Engagement Ring',
            'category': ring_category,
            'weight_grams': Decimal('15.750'),
            'karat': 18,  # 18k gold
            'manufacturing_cost': Decimal('8000000.00'),  # 8M Toman
            'gold_value': Decimal('0.00'),  # Will be calculated
            'gemstone_value': Decimal('50000000.00'),  # 50M Toman
            'selling_price': Decimal('85000000.00'),  # 85M Toman
            'status': 'in_stock',
            'quantity': 1,
            'minimum_stock': 1,
            'description': 'Exquisite 18k gold engagement ring with premium diamond',
            'notes': 'Special collection piece',
            'created_by': user
        }
    )[0]
    
    # Add diamond to the ring
    diamond_ring.gemstones.add(diamond)
    
    # Calculate and update gold value based on current market price
    current_gold_price = Decimal('3500000.00')  # 3.5M Toman per gram
    diamond_ring.update_gold_value(current_gold_price)
    
    print(f"   • {diamond_ring}")
    print(f"     - Weight: {diamond_ring.weight_grams}g ({diamond_ring.karat}k gold)")
    print(f"     - Gold Value: {diamond_ring.gold_value:,.0f} Toman")
    print(f"     - Total Value: {diamond_ring.total_value:,.0f} Toman")
    print(f"     - Low Stock: {'Yes' if diamond_ring.is_low_stock else 'No'}")
    
    # Ruby Necklace
    ruby_necklace = JewelryItem.objects.get_or_create(
        sku='NECK-RUBY-001',
        defaults={
            'name': 'Elegant Ruby Necklace',
            'category': necklace_category,
            'weight_grams': Decimal('25.500'),
            'karat': 22,  # 22k gold
            'manufacturing_cost': Decimal('12000000.00'),  # 12M Toman
            'gold_value': Decimal('0.00'),  # Will be calculated
            'gemstone_value': Decimal('75000000.00'),  # 75M Toman
            'selling_price': Decimal('125000000.00'),  # 125M Toman
            'status': 'in_stock',
            'quantity': 1,
            'minimum_stock': 1,
            'description': 'Luxurious 22k gold necklace with Burmese ruby',
            'notes': 'Limited edition piece',
            'created_by': user
        }
    )[0]
    
    # Add ruby to the necklace
    ruby_necklace.gemstones.add(ruby)
    
    # Calculate and update gold value
    ruby_necklace.update_gold_value(current_gold_price)
    
    print(f"   • {ruby_necklace}")
    print(f"     - Weight: {ruby_necklace.weight_grams}g ({ruby_necklace.karat}k gold)")
    print(f"     - Gold Value: {ruby_necklace.gold_value:,.0f} Toman")
    print(f"     - Total Value: {ruby_necklace.total_value:,.0f} Toman")
    print(f"     - Low Stock: {'Yes' if ruby_necklace.is_low_stock else 'No'}")
    
    # 4. Demonstrate Gold Value Calculations
    print("\n📊 Gold Value Calculations:")
    print(f"   Current Gold Price: {current_gold_price:,.0f} Toman/gram")
    
    # Diamond Ring (18k gold)
    pure_gold_weight_ring = (diamond_ring.weight_grams * diamond_ring.karat) / 24
    print(f"   Diamond Ring:")
    print(f"     - Total Weight: {diamond_ring.weight_grams}g")
    print(f"     - Pure Gold Weight: {pure_gold_weight_ring:.3f}g")
    print(f"     - Gold Value: {diamond_ring.gold_value:,.0f} Toman")
    
    # Ruby Necklace (22k gold)
    pure_gold_weight_necklace = (ruby_necklace.weight_grams * ruby_necklace.karat) / 24
    print(f"   Ruby Necklace:")
    print(f"     - Total Weight: {ruby_necklace.weight_grams}g")
    print(f"     - Pure Gold Weight: {pure_gold_weight_necklace:.3f}g")
    print(f"     - Gold Value: {ruby_necklace.gold_value:,.0f} Toman")
    
    # 5. Demonstrate Model Relationships
    print("\n🔗 Model Relationships:")
    
    # Category to Items
    ring_items = ring_category.jewelryitem_set.all()
    print(f"   Ring Category has {ring_items.count()} items:")
    for item in ring_items:
        print(f"     - {item.name}")
    
    # Gemstone to Items
    diamond_items = diamond.jewelryitem_set.all()
    print(f"   Diamond is used in {diamond_items.count()} items:")
    for item in diamond_items:
        print(f"     - {item.name}")
    
    # Item to Gemstones
    ring_gemstones = diamond_ring.gemstones.all()
    print(f"   Diamond Ring contains {ring_gemstones.count()} gemstones:")
    for gemstone in ring_gemstones:
        print(f"     - {gemstone.name} ({gemstone.carat_weight} carat)")
    
    # 6. Demonstrate Persian Support
    print("\n🇮🇷 Persian Localization:")
    print(f"   User: {user.full_persian_name}")
    print(f"   Categories: {ring_category.name_persian}, {necklace_category.name_persian}")
    
    # 7. Summary Statistics
    print("\n📈 Inventory Summary:")
    total_items = JewelryItem.objects.count()
    total_categories = Category.objects.count()
    total_gemstones = Gemstone.objects.count()
    total_inventory_value = sum(item.total_value for item in JewelryItem.objects.all())
    
    print(f"   Total Items: {total_items}")
    print(f"   Total Categories: {total_categories}")
    print(f"   Total Gemstones: {total_gemstones}")
    print(f"   Total Inventory Value: {total_inventory_value:,.0f} Toman")
    
    print("\n✅ Jewelry Inventory Models Demonstration Complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()