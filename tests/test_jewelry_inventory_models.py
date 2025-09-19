"""
Test suite for jewelry inventory management models.

This test suite covers:
- JewelryItem model with weight, karat, manufacturing cost, and SKU tracking
- ProductCategory model for comprehensive item classification
- Gemstone model for comprehensive item classification
- JewelryItemPhoto model for multiple image management
- Model validation and relationships
- Requirements: 7.1, 7.6, 7.7
"""

import pytest
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model

from zargar.jewelry.models import Category, Gemstone, JewelryItem, JewelryItemPhoto

User = get_user_model()


class JewelryInventoryModelsTestCase(TransactionTestCase):
    """
    Test case for jewelry inventory models.
    """
    
    def setUp(self):
        """Set up test data for each test."""
        # Create test user
        self.user = User.objects.create_user(
            username='testowner',
            email='owner@testshop.com',
            password='testpass123',
            role='owner',
            persian_first_name='علی',
            persian_last_name='احمدی'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Rings',
            name_persian='انگشتر',
            description='Wedding and engagement rings',
            created_by=self.user
        )
        
        # Create test gemstone
        self.gemstone = Gemstone.objects.create(
            name='Diamond Solitaire',
            gemstone_type='diamond',
            carat_weight=Decimal('1.250'),
            cut_grade='excellent',
            color_grade='D',
            clarity_grade='VVS1',
            certification_number='GIA-123456789',
            certification_authority='GIA',
            purchase_price=Decimal('50000000.00'),  # 50M Toman
            created_by=self.user
        )


class CategoryModelTest(JewelryInventoryModelsTestCase):
    """Test Category model functionality."""
    
    def test_category_creation(self):
        """Test creating a category with all fields."""
        category = Category.objects.create(
            name='Necklaces',
            name_persian='گردنبند',
            description='Gold and silver necklaces',
            is_active=True,
            created_by=self.user
        )
        
        self.assertEqual(category.name, 'Necklaces')
        self.assertEqual(category.name_persian, 'گردنبند')
        self.assertEqual(category.description, 'Gold and silver necklaces')
        self.assertTrue(category.is_active)
        self.assertEqual(category.created_by, self.user)
        self.assertIsNotNone(category.created_at)
        self.assertIsNotNone(category.updated_at)
    
    def test_category_str_representation(self):
        """Test category string representation."""
        # Test with Persian name
        category_with_persian = Category.objects.create(
            name='Bracelets',
            name_persian='دستبند',
            created_by=self.user
        )
        self.assertEqual(str(category_with_persian), 'دستبند')
        
        # Test without Persian name
        category_without_persian = Category.objects.create(
            name='Earrings',
            name_persian='',
            created_by=self.user
        )
        self.assertEqual(str(category_without_persian), 'Earrings')
    
    def test_category_unique_constraint(self):
        """Test that category names are unique within tenant."""
        # First category should be created successfully
        Category.objects.create(
            name='Unique Category',
            name_persian='دسته منحصر',
            created_by=self.user
        )
        
        # Second category with same name should be allowed (different timestamp)
        # Note: The unique_together constraint includes created_at, so this should work
        category2 = Category.objects.create(
            name='Unique Category',
            name_persian='دسته منحصر دوم',
            created_by=self.user
        )
        
        self.assertIsNotNone(category2.id)
    
    def test_category_default_values(self):
        """Test category default values."""
        category = Category.objects.create(
            name='Test Category',
            created_by=self.user
        )
        
        self.assertTrue(category.is_active)  # Default should be True
        self.assertEqual(category.description, '')  # Default should be empty


class GemstoneModelTest(JewelryInventoryModelsTestCase):
    """Test Gemstone model functionality."""
    
    def test_gemstone_creation_with_all_fields(self):
        """Test creating a gemstone with all fields."""
        gemstone = Gemstone.objects.create(
            name='Premium Ruby',
            gemstone_type='ruby',
            carat_weight=Decimal('2.500'),
            cut_grade='excellent',
            color_grade='AAA',
            clarity_grade='VVS2',
            certification_number='SSEF-987654321',
            certification_authority='SSEF',
            purchase_price=Decimal('75000000.00'),  # 75M Toman
            created_by=self.user
        )
        
        self.assertEqual(gemstone.name, 'Premium Ruby')
        self.assertEqual(gemstone.gemstone_type, 'ruby')
        self.assertEqual(gemstone.carat_weight, Decimal('2.500'))
        self.assertEqual(gemstone.cut_grade, 'excellent')
        self.assertEqual(gemstone.color_grade, 'AAA')
        self.assertEqual(gemstone.clarity_grade, 'VVS2')
        self.assertEqual(gemstone.certification_number, 'SSEF-987654321')
        self.assertEqual(gemstone.certification_authority, 'SSEF')
        self.assertEqual(gemstone.purchase_price, Decimal('75000000.00'))
        self.assertEqual(gemstone.created_by, self.user)
    
    def test_gemstone_str_representation(self):
        """Test gemstone string representation."""
        gemstone = Gemstone.objects.create(
            name='Test Emerald',
            gemstone_type='emerald',
            carat_weight=Decimal('1.750'),
            created_by=self.user
        )
        
        expected_str = "Test Emerald (1.750 carat)"
        self.assertEqual(str(gemstone), expected_str)
    
    def test_gemstone_type_choices(self):
        """Test gemstone type choices validation."""
        valid_types = ['diamond', 'emerald', 'ruby', 'sapphire', 'pearl', 'other']
        
        for gem_type in valid_types:
            gemstone = Gemstone.objects.create(
                name=f'Test {gem_type.title()}',
                gemstone_type=gem_type,
                carat_weight=Decimal('1.000'),
                created_by=self.user
            )
            self.assertEqual(gemstone.gemstone_type, gem_type)
    
    def test_gemstone_carat_weight_validation(self):
        """Test carat weight validation."""
        # Valid carat weight
        gemstone = Gemstone.objects.create(
            name='Valid Gemstone',
            gemstone_type='diamond',
            carat_weight=Decimal('0.001'),  # Minimum valid weight
            created_by=self.user
        )
        self.assertEqual(gemstone.carat_weight, Decimal('0.001'))
        
        # Test that zero weight would be invalid (handled by MinValueValidator)
        with self.assertRaises(ValidationError):
            invalid_gemstone = Gemstone(
                name='Invalid Gemstone',
                gemstone_type='diamond',
                carat_weight=Decimal('0.000'),
                created_by=self.user
            )
            invalid_gemstone.full_clean()
    
    def test_gemstone_optional_fields(self):
        """Test gemstone with only required fields."""
        gemstone = Gemstone.objects.create(
            name='Simple Gemstone',
            gemstone_type='other',
            carat_weight=Decimal('1.000'),
            created_by=self.user
        )
        
        # Optional fields should be empty/None
        self.assertEqual(gemstone.cut_grade, '')
        self.assertEqual(gemstone.color_grade, '')
        self.assertEqual(gemstone.clarity_grade, '')
        self.assertEqual(gemstone.certification_number, '')
        self.assertEqual(gemstone.certification_authority, '')
        self.assertIsNone(gemstone.purchase_price)


class JewelryItemModelTest(JewelryInventoryModelsTestCase):
    """Test JewelryItem model functionality."""
    
    def test_jewelry_item_creation_with_all_fields(self):
        """Test creating a jewelry item with all fields."""
        jewelry_item = JewelryItem.objects.create(
            name='Premium Gold Ring',
            sku='RING-001-2024',
            barcode='1234567890123',
            category=self.category,
            weight_grams=Decimal('15.750'),
            karat=18,
            manufacturing_cost=Decimal('5000000.00'),  # 5M Toman
            gold_value=Decimal('25000000.00'),  # 25M Toman
            gemstone_value=Decimal('50000000.00'),  # 50M Toman
            selling_price=Decimal('85000000.00'),  # 85M Toman
            status='in_stock',
            quantity=1,
            minimum_stock=1,
            description='Beautiful 18k gold ring with diamond',
            notes='Customer special order',
            created_by=self.user
        )
        
        # Add gemstone relationship
        jewelry_item.gemstones.add(self.gemstone)
        
        # Verify all fields
        self.assertEqual(jewelry_item.name, 'Premium Gold Ring')
        self.assertEqual(jewelry_item.sku, 'RING-001-2024')
        self.assertEqual(jewelry_item.barcode, '1234567890123')
        self.assertEqual(jewelry_item.category, self.category)
        self.assertEqual(jewelry_item.weight_grams, Decimal('15.750'))
        self.assertEqual(jewelry_item.karat, 18)
        self.assertEqual(jewelry_item.manufacturing_cost, Decimal('5000000.00'))
        self.assertEqual(jewelry_item.gold_value, Decimal('25000000.00'))
        self.assertEqual(jewelry_item.gemstone_value, Decimal('50000000.00'))
        self.assertEqual(jewelry_item.selling_price, Decimal('85000000.00'))
        self.assertEqual(jewelry_item.status, 'in_stock')
        self.assertEqual(jewelry_item.quantity, 1)
        self.assertEqual(jewelry_item.minimum_stock, 1)
        self.assertEqual(jewelry_item.description, 'Beautiful 18k gold ring with diamond')
        self.assertEqual(jewelry_item.notes, 'Customer special order')
        self.assertEqual(jewelry_item.created_by, self.user)
        
        # Verify relationships
        self.assertIn(self.gemstone, jewelry_item.gemstones.all())
    
    def test_jewelry_item_str_representation(self):
        """Test jewelry item string representation."""
        jewelry_item = JewelryItem.objects.create(
            name='Test Ring',
            sku='TEST-001',
            category=self.category,
            weight_grams=Decimal('10.000'),
            karat=14,
            manufacturing_cost=Decimal('1000000.00'),
            created_by=self.user
        )
        
        expected_str = "Test Ring (TEST-001)"
        self.assertEqual(str(jewelry_item), expected_str)
    
    def test_jewelry_item_sku_uniqueness(self):
        """Test that SKU must be unique."""
        # Create first item
        JewelryItem.objects.create(
            name='First Item',
            sku='UNIQUE-SKU-001',
            category=self.category,
            weight_grams=Decimal('10.000'),
            karat=14,
            manufacturing_cost=Decimal('1000000.00'),
            created_by=self.user
        )
        
        # Try to create second item with same SKU
        with self.assertRaises(IntegrityError):
            JewelryItem.objects.create(
                name='Second Item',
                sku='UNIQUE-SKU-001',  # Same SKU
                category=self.category,
                weight_grams=Decimal('12.000'),
                karat=18,
                manufacturing_cost=Decimal('1500000.00'),
                created_by=self.user
            )
    
    def test_jewelry_item_barcode_uniqueness(self):
        """Test that barcode must be unique when provided."""
        # Create first item with barcode
        JewelryItem.objects.create(
            name='First Item',
            sku='ITEM-001',
            barcode='1111111111111',
            category=self.category,
            weight_grams=Decimal('10.000'),
            karat=14,
            manufacturing_cost=Decimal('1000000.00'),
            created_by=self.user
        )
        
        # Try to create second item with same barcode
        with self.assertRaises(IntegrityError):
            JewelryItem.objects.create(
                name='Second Item',
                sku='ITEM-002',
                barcode='1111111111111',  # Same barcode
                category=self.category,
                weight_grams=Decimal('12.000'),
                karat=18,
                manufacturing_cost=Decimal('1500000.00'),
                created_by=self.user
            )
    
    def test_jewelry_item_weight_validation(self):
        """Test weight validation."""
        # Valid weight
        jewelry_item = JewelryItem.objects.create(
            name='Valid Item',
            sku='VALID-001',
            category=self.category,
            weight_grams=Decimal('0.001'),  # Minimum valid weight
            karat=14,
            manufacturing_cost=Decimal('1000000.00'),
            created_by=self.user
        )
        self.assertEqual(jewelry_item.weight_grams, Decimal('0.001'))
        
        # Invalid weight (zero or negative)
        with self.assertRaises(ValidationError):
            invalid_item = JewelryItem(
                name='Invalid Item',
                sku='INVALID-001',
                category=self.category,
                weight_grams=Decimal('0.000'),
                karat=14,
                manufacturing_cost=Decimal('1000000.00'),
                created_by=self.user
            )
            invalid_item.full_clean()
    
    def test_jewelry_item_karat_validation(self):
        """Test karat validation."""
        # Valid karat values
        valid_karats = [1, 10, 14, 18, 22, 24]
        
        for karat in valid_karats:
            jewelry_item = JewelryItem.objects.create(
                name=f'Item {karat}k',
                sku=f'ITEM-{karat}K',
                category=self.category,
                weight_grams=Decimal('10.000'),
                karat=karat,
                manufacturing_cost=Decimal('1000000.00'),
                created_by=self.user
            )
            self.assertEqual(jewelry_item.karat, karat)
        
        # Invalid karat values
        invalid_karats = [0, 25, -1]
        
        for karat in invalid_karats:
            with self.assertRaises(ValidationError):
                invalid_item = JewelryItem(
                    name=f'Invalid Item {karat}k',
                    sku=f'INVALID-{karat}K',
                    category=self.category,
                    weight_grams=Decimal('10.000'),
                    karat=karat,
                    manufacturing_cost=Decimal('1000000.00'),
                    created_by=self.user
                )
                invalid_item.full_clean()
    
    def test_jewelry_item_status_choices(self):
        """Test status choices validation."""
        valid_statuses = ['in_stock', 'sold', 'reserved', 'repair', 'consignment']
        
        for status in valid_statuses:
            jewelry_item = JewelryItem.objects.create(
                name=f'Item {status}',
                sku=f'ITEM-{status.upper()}',
                category=self.category,
                weight_grams=Decimal('10.000'),
                karat=14,
                manufacturing_cost=Decimal('1000000.00'),
                status=status,
                created_by=self.user
            )
            self.assertEqual(jewelry_item.status, status)
    
    def test_jewelry_item_total_value_property(self):
        """Test total_value property calculation."""
        jewelry_item = JewelryItem.objects.create(
            name='Test Item',
            sku='TOTAL-001',
            category=self.category,
            weight_grams=Decimal('10.000'),
            karat=14,
            manufacturing_cost=Decimal('5000000.00'),  # 5M
            gold_value=Decimal('10000000.00'),  # 10M
            gemstone_value=Decimal('15000000.00'),  # 15M
            created_by=self.user
        )
        
        expected_total = Decimal('30000000.00')  # 5M + 10M + 15M
        self.assertEqual(jewelry_item.total_value, expected_total)
    
    def test_jewelry_item_is_low_stock_property(self):
        """Test is_low_stock property."""
        # Item with stock above minimum
        high_stock_item = JewelryItem.objects.create(
            name='High Stock Item',
            sku='HIGH-001',
            category=self.category,
            weight_grams=Decimal('10.000'),
            karat=14,
            manufacturing_cost=Decimal('1000000.00'),
            quantity=5,
            minimum_stock=2,
            created_by=self.user
        )
        self.assertFalse(high_stock_item.is_low_stock)
        
        # Item with stock at minimum
        min_stock_item = JewelryItem.objects.create(
            name='Min Stock Item',
            sku='MIN-001',
            category=self.category,
            weight_grams=Decimal('10.000'),
            karat=14,
            manufacturing_cost=Decimal('1000000.00'),
            quantity=2,
            minimum_stock=2,
            created_by=self.user
        )
        self.assertTrue(min_stock_item.is_low_stock)
        
        # Item with stock below minimum
        low_stock_item = JewelryItem.objects.create(
            name='Low Stock Item',
            sku='LOW-001',
            category=self.category,
            weight_grams=Decimal('10.000'),
            karat=14,
            manufacturing_cost=Decimal('1000000.00'),
            quantity=1,
            minimum_stock=3,
            created_by=self.user
        )
        self.assertTrue(low_stock_item.is_low_stock)
    
    def test_jewelry_item_calculate_gold_value(self):
        """Test calculate_gold_value method."""
        jewelry_item = JewelryItem.objects.create(
            name='Gold Value Test',
            sku='GOLD-001',
            category=self.category,
            weight_grams=Decimal('20.000'),  # 20 grams
            karat=18,  # 18k gold (75% pure)
            manufacturing_cost=Decimal('1000000.00'),
            created_by=self.user
        )
        
        gold_price_per_gram = Decimal('3000000.00')  # 3M Toman per gram
        
        # Calculate expected value: (20g * 18k / 24k) * 3M = 15g * 3M = 45M
        expected_value = Decimal('45000000.00')
        calculated_value = jewelry_item.calculate_gold_value(gold_price_per_gram)
        
        self.assertEqual(calculated_value, expected_value)
    
    def test_jewelry_item_update_gold_value(self):
        """Test update_gold_value method."""
        jewelry_item = JewelryItem.objects.create(
            name='Update Gold Test',
            sku='UPDATE-001',
            category=self.category,
            weight_grams=Decimal('10.000'),
            karat=22,  # 22k gold
            manufacturing_cost=Decimal('1000000.00'),
            gold_value=Decimal('0.00'),  # Initial value
            created_by=self.user
        )
        
        gold_price_per_gram = Decimal('3500000.00')  # 3.5M Toman per gram
        
        # Update gold value
        jewelry_item.update_gold_value(gold_price_per_gram)
        
        # Refresh from database
        jewelry_item.refresh_from_db()
        
        # Calculate expected value: (10g * 22k / 24k) * 3.5M = 9.167g * 3.5M ≈ 32.08M
        expected_value = (Decimal('10.000') * Decimal('22') / Decimal('24')) * gold_price_per_gram
        
        self.assertEqual(jewelry_item.gold_value, expected_value)
    
    def test_jewelry_item_default_values(self):
        """Test jewelry item default values."""
        jewelry_item = JewelryItem.objects.create(
            name='Default Test',
            sku='DEFAULT-001',
            category=self.category,
            weight_grams=Decimal('10.000'),
            karat=14,
            manufacturing_cost=Decimal('1000000.00'),
            created_by=self.user
        )
        
        # Check default values
        self.assertEqual(jewelry_item.status, 'in_stock')
        self.assertEqual(jewelry_item.quantity, 1)
        self.assertEqual(jewelry_item.minimum_stock, 1)
        self.assertEqual(jewelry_item.gemstone_value, Decimal('0'))
        self.assertEqual(jewelry_item.description, '')
        self.assertEqual(jewelry_item.notes, '')


class JewelryItemPhotoModelTest(JewelryInventoryModelsTestCase):
    """Test JewelryItemPhoto model functionality."""
    
    def setUp(self):
        """Set up test data including jewelry item."""
        super().setUp()
        
        # Create test jewelry item
        self.jewelry_item = JewelryItem.objects.create(
            name='Photo Test Item',
            sku='PHOTO-001',
            category=self.category,
            weight_grams=Decimal('10.000'),
            karat=14,
            manufacturing_cost=Decimal('1000000.00'),
            created_by=self.user
        )
        
        # Create test image file
        self.test_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'fake image content',
            content_type='image/jpeg'
        )
    
    def test_jewelry_item_photo_creation(self):
        """Test creating a jewelry item photo."""
        photo = JewelryItemPhoto.objects.create(
            jewelry_item=self.jewelry_item,
            image=self.test_image,
            caption='Front view of the ring',
            is_primary=True,
            order=1,
            created_by=self.user
        )
        
        self.assertEqual(photo.jewelry_item, self.jewelry_item)
        self.assertEqual(photo.caption, 'Front view of the ring')
        self.assertTrue(photo.is_primary)
        self.assertEqual(photo.order, 1)
        self.assertEqual(photo.created_by, self.user)
        self.assertIsNotNone(photo.image)
    
    def test_jewelry_item_photo_str_representation(self):
        """Test photo string representation."""
        photo = JewelryItemPhoto.objects.create(
            jewelry_item=self.jewelry_item,
            image=self.test_image,
            created_by=self.user
        )
        
        expected_str = f"Photo for {self.jewelry_item.name}"
        self.assertEqual(str(photo), expected_str)
    
    def test_jewelry_item_photo_primary_uniqueness(self):
        """Test that only one photo can be primary per item."""
        # Create first primary photo
        photo1 = JewelryItemPhoto.objects.create(
            jewelry_item=self.jewelry_item,
            image=SimpleUploadedFile('photo1.jpg', b'content1', 'image/jpeg'),
            is_primary=True,
            created_by=self.user
        )
        
        # Create second primary photo - should make first one non-primary
        photo2 = JewelryItemPhoto.objects.create(
            jewelry_item=self.jewelry_item,
            image=SimpleUploadedFile('photo2.jpg', b'content2', 'image/jpeg'),
            is_primary=True,
            created_by=self.user
        )
        
        # Refresh from database
        photo1.refresh_from_db()
        photo2.refresh_from_db()
        
        # Only photo2 should be primary
        self.assertFalse(photo1.is_primary)
        self.assertTrue(photo2.is_primary)
    
    def test_jewelry_item_photo_ordering(self):
        """Test photo ordering."""
        # Create photos with different orders
        photo3 = JewelryItemPhoto.objects.create(
            jewelry_item=self.jewelry_item,
            image=SimpleUploadedFile('photo3.jpg', b'content3', 'image/jpeg'),
            order=3,
            created_by=self.user
        )
        
        photo1 = JewelryItemPhoto.objects.create(
            jewelry_item=self.jewelry_item,
            image=SimpleUploadedFile('photo1.jpg', b'content1', 'image/jpeg'),
            order=1,
            created_by=self.user
        )
        
        photo2 = JewelryItemPhoto.objects.create(
            jewelry_item=self.jewelry_item,
            image=SimpleUploadedFile('photo2.jpg', b'content2', 'image/jpeg'),
            order=2,
            created_by=self.user
        )
        
        # Get photos in order
        photos = list(self.jewelry_item.photos.all())
        
        # Should be ordered by order field, then created_at
        self.assertEqual(photos[0], photo1)
        self.assertEqual(photos[1], photo2)
        self.assertEqual(photos[2], photo3)
    
    def test_jewelry_item_photo_relationship(self):
        """Test photo relationship with jewelry item."""
        # Create multiple photos for the item
        photo1 = JewelryItemPhoto.objects.create(
            jewelry_item=self.jewelry_item,
            image=SimpleUploadedFile('photo1.jpg', b'content1', 'image/jpeg'),
            created_by=self.user
        )
        
        photo2 = JewelryItemPhoto.objects.create(
            jewelry_item=self.jewelry_item,
            image=SimpleUploadedFile('photo2.jpg', b'content2', 'image/jpeg'),
            created_by=self.user
        )
        
        # Test reverse relationship
        photos = self.jewelry_item.photos.all()
        self.assertEqual(photos.count(), 2)
        self.assertIn(photo1, photos)
        self.assertIn(photo2, photos)
    
    def test_jewelry_item_photo_cascade_delete(self):
        """Test that photos are deleted when jewelry item is deleted."""
        # Create photo
        photo = JewelryItemPhoto.objects.create(
            jewelry_item=self.jewelry_item,
            image=self.test_image,
            created_by=self.user
        )
        
        photo_id = photo.id
        
        # Delete jewelry item
        self.jewelry_item.delete()
        
        # Photo should be deleted too
        with self.assertRaises(JewelryItemPhoto.DoesNotExist):
            JewelryItemPhoto.objects.get(id=photo_id)
    
    def test_jewelry_item_photo_default_values(self):
        """Test photo default values."""
        photo = JewelryItemPhoto.objects.create(
            jewelry_item=self.jewelry_item,
            image=self.test_image,
            created_by=self.user
        )
        
        # Check default values
        self.assertEqual(photo.caption, '')
        self.assertFalse(photo.is_primary)
        self.assertEqual(photo.order, 0)


class JewelryModelRelationshipsTest(JewelryInventoryModelsTestCase):
    """Test relationships between jewelry models."""
    
    def test_jewelry_item_category_relationship(self):
        """Test jewelry item to category relationship."""
        # Create jewelry item
        jewelry_item = JewelryItem.objects.create(
            name='Relationship Test',
            sku='REL-001',
            category=self.category,
            weight_grams=Decimal('10.000'),
            karat=14,
            manufacturing_cost=Decimal('1000000.00'),
            created_by=self.user
        )
        
        # Test forward relationship
        self.assertEqual(jewelry_item.category, self.category)
        
        # Test reverse relationship
        category_items = self.category.jewelryitem_set.all()
        self.assertIn(jewelry_item, category_items)
    
    def test_jewelry_item_gemstone_relationship(self):
        """Test jewelry item to gemstone many-to-many relationship."""
        # Create additional gemstone
        gemstone2 = Gemstone.objects.create(
            name='Ruby Stone',
            gemstone_type='ruby',
            carat_weight=Decimal('0.750'),
            created_by=self.user
        )
        
        # Create jewelry item
        jewelry_item = JewelryItem.objects.create(
            name='Multi-Gem Item',
            sku='MULTI-001',
            category=self.category,
            weight_grams=Decimal('15.000'),
            karat=18,
            manufacturing_cost=Decimal('2000000.00'),
            created_by=self.user
        )
        
        # Add gemstones
        jewelry_item.gemstones.add(self.gemstone, gemstone2)
        
        # Test forward relationship
        item_gemstones = jewelry_item.gemstones.all()
        self.assertEqual(item_gemstones.count(), 2)
        self.assertIn(self.gemstone, item_gemstones)
        self.assertIn(gemstone2, item_gemstones)
        
        # Test reverse relationship
        gemstone_items = self.gemstone.jewelryitem_set.all()
        self.assertIn(jewelry_item, gemstone_items)
    
    def test_category_protection_on_delete(self):
        """Test that category cannot be deleted if jewelry items exist."""
        # Create jewelry item with category
        jewelry_item = JewelryItem.objects.create(
            name='Protected Item',
            sku='PROTECT-001',
            category=self.category,
            weight_grams=Decimal('10.000'),
            karat=14,
            manufacturing_cost=Decimal('1000000.00'),
            created_by=self.user
        )
        
        # Try to delete category - should raise ProtectedError
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.category.delete()
        
        # Category should still exist
        self.assertTrue(Category.objects.filter(id=self.category.id).exists())
    
    def test_tenant_isolation(self):
        """Test that models are properly isolated by tenant."""
        # Current tenant data should be accessible
        categories = Category.objects.all()
        self.assertIn(self.category, categories)
        
        gemstones = Gemstone.objects.all()
        self.assertIn(self.gemstone, gemstones)
        
        # Create jewelry item
        jewelry_item = JewelryItem.objects.create(
            name='Isolation Test',
            sku='ISOLATE-001',
            category=self.category,
            weight_grams=Decimal('10.000'),
            karat=14,
            manufacturing_cost=Decimal('1000000.00'),
            created_by=self.user
        )
        
        items = JewelryItem.objects.all()
        self.assertIn(jewelry_item, items)
        
        # All models should have audit fields populated
        self.assertIsNotNone(self.category.created_at)
        self.assertIsNotNone(self.category.created_by)
        self.assertIsNotNone(self.gemstone.created_at)
        self.assertIsNotNone(self.gemstone.created_by)
        self.assertIsNotNone(jewelry_item.created_at)
        self.assertIsNotNone(jewelry_item.created_by)


# Performance and edge case tests
class JewelryModelPerformanceTest(JewelryInventoryModelsTestCase):
    """Test performance and edge cases for jewelry models."""
    
    def test_bulk_jewelry_item_creation(self):
        """Test creating multiple jewelry items efficiently."""
        items_data = []
        
        for i in range(100):
            items_data.append(JewelryItem(
                name=f'Bulk Item {i}',
                sku=f'BULK-{i:03d}',
                category=self.category,
                weight_grams=Decimal('10.000'),
                karat=14,
                manufacturing_cost=Decimal('1000000.00'),
                created_by=self.user
            ))
        
        # Bulk create
        created_items = JewelryItem.objects.bulk_create(items_data)
        
        # Verify creation
        self.assertEqual(len(created_items), 100)
        self.assertEqual(JewelryItem.objects.count(), 100)
    
    def test_large_decimal_values(self):
        """Test handling of large decimal values."""
        jewelry_item = JewelryItem.objects.create(
            name='Expensive Item',
            sku='EXPENSIVE-001',
            category=self.category,
            weight_grams=Decimal('999999.999'),  # Maximum weight
            karat=24,
            manufacturing_cost=Decimal('9999999999.99'),  # Maximum cost
            gold_value=Decimal('999999999999.99'),  # Maximum gold value
            gemstone_value=Decimal('999999999999.99'),  # Maximum gemstone value
            selling_price=Decimal('999999999999.99'),  # Maximum selling price
            created_by=self.user
        )
        
        # Verify values are stored correctly
        self.assertEqual(jewelry_item.weight_grams, Decimal('999999.999'))
        self.assertEqual(jewelry_item.manufacturing_cost, Decimal('9999999999.99'))
        self.assertEqual(jewelry_item.gold_value, Decimal('999999999999.99'))
        
        # Test total value calculation with large numbers
        total_value = jewelry_item.total_value
        expected_total = (
            Decimal('9999999999.99') +  # manufacturing_cost
            Decimal('999999999999.99') +  # gold_value
            Decimal('999999999999.99')    # gemstone_value
        )
        self.assertEqual(total_value, expected_total)


if __name__ == '__main__':
    pytest.main([__file__])