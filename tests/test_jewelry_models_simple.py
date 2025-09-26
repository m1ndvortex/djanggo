"""
Simple test suite for jewelry inventory management models.
Tests model definitions, validation, and basic functionality without database operations.
"""

import pytest
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from zargar.jewelry.models import Category, Gemstone, JewelryItem, JewelryItemPhoto

User = get_user_model()


class JewelryModelDefinitionTest(TestCase):
    """Test jewelry model definitions and basic functionality."""
    
    def test_category_model_fields(self):
        """Test Category model field definitions."""
        # Test model can be instantiated
        category = Category(
            name='Test Category',
            name_persian='دسته آزمایشی',
            description='Test description',
            is_active=True
        )
        
        # Test field values
        self.assertEqual(category.name, 'Test Category')
        self.assertEqual(category.name_persian, 'دسته آزمایشی')
        self.assertEqual(category.description, 'Test description')
        self.assertTrue(category.is_active)
    
    def test_category_str_method(self):
        """Test Category string representation."""
        # With Persian name
        category_with_persian = Category(
            name='Rings',
            name_persian='انگشتر'
        )
        self.assertEqual(str(category_with_persian), 'انگشتر')
        
        # Without Persian name
        category_without_persian = Category(
            name='Bracelets',
            name_persian=''
        )
        self.assertEqual(str(category_without_persian), 'Bracelets')
    
    def test_gemstone_model_fields(self):
        """Test Gemstone model field definitions."""
        gemstone = Gemstone(
            name='Test Diamond',
            gemstone_type='diamond',
            carat_weight=Decimal('1.500'),
            cut_grade='excellent',
            color_grade='D',
            clarity_grade='VVS1',
            certification_number='GIA-123456',
            certification_authority='GIA',
            purchase_price=Decimal('50000000.00')
        )
        
        # Test field values
        self.assertEqual(gemstone.name, 'Test Diamond')
        self.assertEqual(gemstone.gemstone_type, 'diamond')
        self.assertEqual(gemstone.carat_weight, Decimal('1.500'))
        self.assertEqual(gemstone.cut_grade, 'excellent')
        self.assertEqual(gemstone.color_grade, 'D')
        self.assertEqual(gemstone.clarity_grade, 'VVS1')
        self.assertEqual(gemstone.certification_number, 'GIA-123456')
        self.assertEqual(gemstone.certification_authority, 'GIA')
        self.assertEqual(gemstone.purchase_price, Decimal('50000000.00'))
    
    def test_gemstone_str_method(self):
        """Test Gemstone string representation."""
        gemstone = Gemstone(
            name='Test Ruby',
            carat_weight=Decimal('2.250')
        )
        expected_str = "Test Ruby (2.250 carat)"
        self.assertEqual(str(gemstone), expected_str)
    
    def test_gemstone_type_choices(self):
        """Test gemstone type choices are valid."""
        valid_types = ['diamond', 'emerald', 'ruby', 'sapphire', 'pearl', 'other']
        
        for gem_type in valid_types:
            gemstone = Gemstone(
                name=f'Test {gem_type.title()}',
                gemstone_type=gem_type,
                carat_weight=Decimal('1.000')
            )
            self.assertEqual(gemstone.gemstone_type, gem_type)
    
    def test_jewelry_item_model_fields(self):
        """Test JewelryItem model field definitions."""
        jewelry_item = JewelryItem(
            name='Test Ring',
            sku='TEST-001',
            barcode='1234567890',
            weight_grams=Decimal('15.750'),
            karat=18,
            manufacturing_cost=Decimal('5000000.00'),
            gold_value=Decimal('25000000.00'),
            gemstone_value=Decimal('50000000.00'),
            selling_price=Decimal('85000000.00'),
            status='in_stock',
            quantity=1,
            minimum_stock=1,
            description='Beautiful gold ring',
            notes='Special order'
        )
        
        # Test field values
        self.assertEqual(jewelry_item.name, 'Test Ring')
        self.assertEqual(jewelry_item.sku, 'TEST-001')
        self.assertEqual(jewelry_item.barcode, '1234567890')
        self.assertEqual(jewelry_item.weight_grams, Decimal('15.750'))
        self.assertEqual(jewelry_item.karat, 18)
        self.assertEqual(jewelry_item.manufacturing_cost, Decimal('5000000.00'))
        self.assertEqual(jewelry_item.gold_value, Decimal('25000000.00'))
        self.assertEqual(jewelry_item.gemstone_value, Decimal('50000000.00'))
        self.assertEqual(jewelry_item.selling_price, Decimal('85000000.00'))
        self.assertEqual(jewelry_item.status, 'in_stock')
        self.assertEqual(jewelry_item.quantity, 1)
        self.assertEqual(jewelry_item.minimum_stock, 1)
        self.assertEqual(jewelry_item.description, 'Beautiful gold ring')
        self.assertEqual(jewelry_item.notes, 'Special order')
    
    def test_jewelry_item_str_method(self):
        """Test JewelryItem string representation."""
        jewelry_item = JewelryItem(
            name='Test Necklace',
            sku='NECK-001'
        )
        expected_str = "Test Necklace (NECK-001)"
        self.assertEqual(str(jewelry_item), expected_str)
    
    def test_jewelry_item_status_choices(self):
        """Test jewelry item status choices."""
        valid_statuses = ['in_stock', 'sold', 'reserved', 'repair', 'consignment']
        
        for status in valid_statuses:
            jewelry_item = JewelryItem(
                name=f'Item {status}',
                sku=f'ITEM-{status.upper()}',
                status=status
            )
            self.assertEqual(jewelry_item.status, status)
    
    def test_jewelry_item_total_value_property(self):
        """Test total_value property calculation."""
        jewelry_item = JewelryItem(
            manufacturing_cost=Decimal('5000000.00'),  # 5M
            gold_value=Decimal('10000000.00'),  # 10M
            gemstone_value=Decimal('15000000.00')  # 15M
        )
        
        expected_total = Decimal('30000000.00')  # 5M + 10M + 15M
        self.assertEqual(jewelry_item.total_value, expected_total)
    
    def test_jewelry_item_total_value_with_none_values(self):
        """Test total_value property with None values."""
        jewelry_item = JewelryItem(
            manufacturing_cost=Decimal('5000000.00'),
            gold_value=None,  # None value
            gemstone_value=Decimal('15000000.00')
        )
        
        expected_total = Decimal('20000000.00')  # 5M + 0 + 15M
        self.assertEqual(jewelry_item.total_value, expected_total)
    
    def test_jewelry_item_is_low_stock_property(self):
        """Test is_low_stock property."""
        # Stock above minimum
        high_stock_item = JewelryItem(
            quantity=5,
            minimum_stock=2
        )
        self.assertFalse(high_stock_item.is_low_stock)
        
        # Stock at minimum
        min_stock_item = JewelryItem(
            quantity=2,
            minimum_stock=2
        )
        self.assertTrue(min_stock_item.is_low_stock)
        
        # Stock below minimum
        low_stock_item = JewelryItem(
            quantity=1,
            minimum_stock=3
        )
        self.assertTrue(low_stock_item.is_low_stock)
    
    def test_jewelry_item_calculate_gold_value(self):
        """Test calculate_gold_value method."""
        jewelry_item = JewelryItem(
            weight_grams=Decimal('20.000'),  # 20 grams
            karat=18  # 18k gold (75% pure)
        )
        
        gold_price_per_gram = Decimal('3000000.00')  # 3M Toman per gram
        
        # Calculate expected value: (20g * 18k / 24k) * 3M = 15g * 3M = 45M
        expected_value = Decimal('45000000.00')
        calculated_value = jewelry_item.calculate_gold_value(gold_price_per_gram)
        
        self.assertEqual(calculated_value, expected_value)
    
    def test_jewelry_item_calculate_gold_value_edge_cases(self):
        """Test calculate_gold_value with edge cases."""
        # No weight
        item_no_weight = JewelryItem(weight_grams=None, karat=18)
        self.assertEqual(item_no_weight.calculate_gold_value(Decimal('3000000.00')), 0)
        
        # No karat
        item_no_karat = JewelryItem(weight_grams=Decimal('10.000'), karat=None)
        self.assertEqual(item_no_karat.calculate_gold_value(Decimal('3000000.00')), 0)
        
        # 24k gold (pure)
        pure_gold_item = JewelryItem(
            weight_grams=Decimal('10.000'),
            karat=24
        )
        expected_pure = Decimal('10.000') * Decimal('3000000.00')
        self.assertEqual(pure_gold_item.calculate_gold_value(Decimal('3000000.00')), expected_pure)
    
    def test_jewelry_item_photo_model_fields(self):
        """Test JewelryItemPhoto model field definitions."""
        photo = JewelryItemPhoto(
            caption='Front view',
            is_primary=True,
            order=1
        )
        
        # Test field values
        self.assertEqual(photo.caption, 'Front view')
        self.assertTrue(photo.is_primary)
        self.assertEqual(photo.order, 1)
    
    def test_jewelry_item_photo_str_method(self):
        """Test JewelryItemPhoto string representation."""
        # Create a mock jewelry item
        jewelry_item = JewelryItem(name='Test Ring')
        photo = JewelryItemPhoto(jewelry_item=jewelry_item)
        
        expected_str = "Photo for Test Ring"
        self.assertEqual(str(photo), expected_str)
    
    def test_model_field_validation_constraints(self):
        """Test model field validation constraints."""
        # Test weight validation constraint exists
        jewelry_item = JewelryItem(
            weight_grams=Decimal('0.000')  # Invalid weight
        )
        
        # The MinValueValidator should be present in the field
        weight_field = JewelryItem._meta.get_field('weight_grams')
        validators = weight_field.validators
        
        # Check that MinValueValidator is present
        from django.core.validators import MinValueValidator
        has_min_validator = any(isinstance(v, MinValueValidator) for v in validators)
        self.assertTrue(has_min_validator, "Weight field should have MinValueValidator")
        
        # Test karat validation constraint exists
        karat_field = JewelryItem._meta.get_field('karat')
        karat_validators = karat_field.validators
        
        # Check that MinValueValidator and MaxValueValidator are present
        from django.core.validators import MaxValueValidator
        has_min_karat = any(isinstance(v, MinValueValidator) for v in karat_validators)
        has_max_karat = any(isinstance(v, MaxValueValidator) for v in karat_validators)
        self.assertTrue(has_min_karat, "Karat field should have MinValueValidator")
        self.assertTrue(has_max_karat, "Karat field should have MaxValueValidator")
    
    def test_model_meta_options(self):
        """Test model Meta options."""
        # Test Category Meta
        self.assertEqual(Category._meta.verbose_name.lower(), 'category')
        self.assertEqual(Category._meta.verbose_name_plural.lower(), 'categories')
        
        # Test Gemstone Meta
        self.assertEqual(Gemstone._meta.verbose_name.lower(), 'gemstone')
        self.assertEqual(Gemstone._meta.verbose_name_plural.lower(), 'gemstones')
        
        # Test JewelryItem Meta
        self.assertEqual(JewelryItem._meta.verbose_name.lower(), 'jewelry item')
        self.assertEqual(JewelryItem._meta.verbose_name_plural.lower(), 'jewelry items')
        
        # Test JewelryItemPhoto Meta
        self.assertEqual(JewelryItemPhoto._meta.verbose_name.lower(), 'jewelry item photo')
        self.assertEqual(JewelryItemPhoto._meta.verbose_name_plural.lower(), 'jewelry item photos')
        
        # Test JewelryItemPhoto ordering
        self.assertEqual(JewelryItemPhoto._meta.ordering, ['order', 'created_at'])
    
    def test_model_indexes(self):
        """Test model database indexes."""
        # Test JewelryItem indexes
        indexes = JewelryItem._meta.indexes
        index_fields = [list(index.fields) for index in indexes]
        
        # Check that important fields have indexes
        expected_indexes = [
            ['sku'],
            ['barcode'],
            ['status'],
            ['category']
        ]
        
        for expected_index in expected_indexes:
            self.assertIn(expected_index, index_fields, 
                         f"Index on {expected_index} should exist")


class JewelryModelValidationTest(TestCase):
    """Test jewelry model validation logic."""
    
    def test_gemstone_carat_weight_field_validation(self):
        """Test gemstone carat weight field validation."""
        # Test that the field has proper validators
        carat_field = Gemstone._meta.get_field('carat_weight')
        validators = carat_field.validators
        
        from django.core.validators import MinValueValidator
        has_min_validator = any(isinstance(v, MinValueValidator) for v in validators)
        self.assertTrue(has_min_validator, "Carat weight field should have MinValueValidator")
        
        # Test that minimum value is 0.001
        min_validator = next(v for v in validators if isinstance(v, MinValueValidator))
        self.assertEqual(float(min_validator.limit_value), 0.001)
    
    def test_jewelry_item_weight_field_validation(self):
        """Test jewelry item weight field validation."""
        # Test that the field has proper validators
        weight_field = JewelryItem._meta.get_field('weight_grams')
        validators = weight_field.validators
        
        from django.core.validators import MinValueValidator
        has_min_validator = any(isinstance(v, MinValueValidator) for v in validators)
        self.assertTrue(has_min_validator, "Weight field should have MinValueValidator")
        
        # Test that minimum value is 0.001
        min_validator = next(v for v in validators if isinstance(v, MinValueValidator))
        self.assertEqual(float(min_validator.limit_value), 0.001)
    
    def test_jewelry_item_karat_field_validation(self):
        """Test jewelry item karat field validation."""
        # Test that the field has proper validators
        karat_field = JewelryItem._meta.get_field('karat')
        validators = karat_field.validators
        
        from django.core.validators import MinValueValidator, MaxValueValidator
        has_min_validator = any(isinstance(v, MinValueValidator) for v in validators)
        has_max_validator = any(isinstance(v, MaxValueValidator) for v in validators)
        
        self.assertTrue(has_min_validator, "Karat field should have MinValueValidator")
        self.assertTrue(has_max_validator, "Karat field should have MaxValueValidator")
        
        # Test validator limits
        min_validator = next(v for v in validators if isinstance(v, MinValueValidator))
        max_validator = next(v for v in validators if isinstance(v, MaxValueValidator))
        
        self.assertEqual(min_validator.limit_value, 1)
        self.assertEqual(max_validator.limit_value, 24)


if __name__ == '__main__':
    pytest.main([__file__])