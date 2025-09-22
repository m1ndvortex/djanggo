"""
Comprehensive test suite for inventory tracking system backend.

This test suite covers:
- Serial number tracking for high-value jewelry pieces
- Stock alert system with customizable thresholds
- Real-time inventory valuation based on current gold prices
- Inventory tracking and valuation calculations
- Requirements: 7.1, 7.2, 7.3, 7.5
"""

import os
import django
from django.conf import settings

# Configure Django settings before importing models
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth import get_user_model

from zargar.jewelry.models import Category, Gemstone, JewelryItem
from zargar.jewelry.services import (
    SerialNumberTrackingService,
    StockAlertService,
    InventoryValuationService,
    InventoryTrackingService
)

User = get_user_model()


class SerialNumberTrackingServiceTest(TransactionTestCase):
    """Test SerialNumberTrackingService functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Clear cache
        cache.clear()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testowner',
            email='owner@testshop.com',
            password='testpass123',
            role='owner'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Rings',
            name_persian='انگشتر',
            created_by=self.user
        )
        
        # Create high-value jewelry item
        self.high_value_item = JewelryItem.objects.create(
            name='Premium Diamond Ring',
            sku='RING-001',
            category=self.category,
            weight_grams=Decimal('15.000'),
            karat=18,
            manufacturing_cost=Decimal('10000000.00'),  # 10M Toman
            gold_value=Decimal('30000000.00'),  # 30M Toman
            gemstone_value=Decimal('20000000.00'),  # 20M Toman
            quantity=1,
            created_by=self.user
        )
        
        # Create low-value jewelry item
        self.low_value_item = JewelryItem.objects.create(
            name='Simple Gold Ring',
            sku='RING-002',
            category=self.category,
            weight_grams=Decimal('5.000'),
            karat=14,
            manufacturing_cost=Decimal('2000000.00'),  # 2M Toman
            gold_value=Decimal('8000000.00'),  # 8M Toman
            quantity=1,
            created_by=self.user
        )
    
    def test_generate_serial_number(self):
        """Test serial number generation."""
        serial_number = SerialNumberTrackingService.generate_serial_number(self.high_value_item)
        
        # Check format: ZRG-YYYY-CAT-NNNN
        parts = serial_number.split('-')
        self.assertEqual(len(parts), 4)
        self.assertEqual(parts[0], 'ZRG')
        self.assertEqual(parts[1], str(timezone.now().year))
        self.assertEqual(parts[2], 'RIN')  # First 3 letters of 'RINGS'
        self.assertEqual(len(parts[3]), 4)
        self.assertTrue(parts[3].isdigit())
    
    def test_get_category_code(self):
        """Test category code generation."""
        # Test normal category
        code = SerialNumberTrackingService._get_category_code(self.category)
        self.assertEqual(code, 'RIN')
        
        # Test short category name
        short_category = Category.objects.create(
            name='AB',
            created_by=self.user
        )
        code = SerialNumberTrackingService._get_category_code(short_category)
        self.assertEqual(code, 'ABX')
        
        # Test category with spaces
        spaced_category = Category.objects.create(
            name='Wedding Rings',
            created_by=self.user
        )
        code = SerialNumberTrackingService._get_category_code(spaced_category)
        self.assertEqual(code, 'WED')
    
    def test_get_next_sequence(self):
        """Test sequence number generation."""
        # First sequence should be 1
        sequence = SerialNumberTrackingService._get_next_sequence('RIN', 2024)
        self.assertEqual(sequence, 1)
        
        # Create item with serial number
        self.high_value_item.barcode = 'ZRG-2024-RIN-0001'
        self.high_value_item.save()
        
        # Next sequence should be 2
        sequence = SerialNumberTrackingService._get_next_sequence('RIN', 2024)
        self.assertEqual(sequence, 2)
    
    def test_assign_serial_number_high_value(self):
        """Test serial number assignment for high-value items."""
        result = SerialNumberTrackingService.assign_serial_number(self.high_value_item)
        
        self.assertTrue(result['success'])
        self.assertIn('serial_number', result)
        self.assertTrue(result['is_high_value'])
        self.assertEqual(result['item_value'], self.high_value_item.total_value)
        
        # Verify item was updated
        self.high_value_item.refresh_from_db()
        self.assertEqual(self.high_value_item.barcode, result['serial_number'])
    
    def test_assign_serial_number_low_value(self):
        """Test serial number assignment for low-value items."""
        result = SerialNumberTrackingService.assign_serial_number(self.low_value_item)
        
        self.assertFalse(result['success'])
        self.assertIn('threshold', result['message'])
        self.assertTrue(result['requires_high_value'])
        self.assertEqual(result['threshold'], SerialNumberTrackingService.HIGH_VALUE_THRESHOLD)
    
    def test_assign_serial_number_force(self):
        """Test forced serial number assignment."""
        result = SerialNumberTrackingService.assign_serial_number(
            self.low_value_item, 
            force_assign=True
        )
        
        self.assertTrue(result['success'])
        self.assertIn('serial_number', result)
        self.assertFalse(result['is_high_value'])
        
        # Verify item was updated
        self.low_value_item.refresh_from_db()
        self.assertEqual(self.low_value_item.barcode, result['serial_number'])
    
    def test_assign_serial_number_already_exists(self):
        """Test serial number assignment when item already has one."""
        self.high_value_item.barcode = 'EXISTING-SERIAL'
        self.high_value_item.save()
        
        result = SerialNumberTrackingService.assign_serial_number(self.high_value_item)
        
        self.assertFalse(result['success'])
        self.assertIn('already has', result['message'])
        self.assertEqual(result['serial_number'], 'EXISTING-SERIAL')
    
    def test_validate_serial_number_valid(self):
        """Test valid serial number validation."""
        valid_serial = 'ZRG-2024-RIN-0001'
        result = SerialNumberTrackingService.validate_serial_number(valid_serial)
        
        self.assertTrue(result['valid'])
        self.assertIn('parsed', result)
        self.assertEqual(result['parsed']['prefix'], 'ZRG')
        self.assertEqual(result['parsed']['year'], 2024)
        self.assertEqual(result['parsed']['category_code'], 'RIN')
        self.assertEqual(result['parsed']['sequence'], 1)
    
    def test_validate_serial_number_invalid_format(self):
        """Test invalid serial number format validation."""
        invalid_serials = [
            'INVALID',
            'ZRG-2024-RIN',
            'ZRG-2024-RIN-0001-EXTRA',
            'ABC-2024-RIN-0001',
            'ZRG-YEAR-RIN-0001',
            'ZRG-2024-R1-0001',
            'ZRG-2024-RIN-ABCD'
        ]
        
        for serial in invalid_serials:
            result = SerialNumberTrackingService.validate_serial_number(serial)
            self.assertFalse(result['valid'], f"Serial {serial} should be invalid")
    
    def test_validate_serial_number_duplicate(self):
        """Test duplicate serial number validation."""
        # Create item with serial number
        self.high_value_item.barcode = 'ZRG-2024-RIN-0001'
        self.high_value_item.save()
        
        # Try to validate same serial number
        result = SerialNumberTrackingService.validate_serial_number('ZRG-2024-RIN-0001')
        
        self.assertFalse(result['valid'])
        self.assertIn('already exists', result['message'])
    
    def test_get_high_value_items_without_serial(self):
        """Test getting high-value items without serial numbers."""
        # Initially, high-value item should be in the list
        items = SerialNumberTrackingService.get_high_value_items_without_serial()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0], self.high_value_item)
        
        # Assign serial number
        self.high_value_item.barcode = 'ZRG-2024-RIN-0001'
        self.high_value_item.save()
        
        # Now list should be empty
        items = SerialNumberTrackingService.get_high_value_items_without_serial()
        self.assertEqual(len(items), 0)


class StockAlertServiceTest(TransactionTestCase):
    """Test StockAlertService functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Clear cache
        cache.clear()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testowner',
            email='owner@testshop.com',
            password='testpass123',
            role='owner'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Rings',
            name_persian='انگشتر',
            created_by=self.user
        )
        
        # Create items with different stock levels
        self.low_stock_item = JewelryItem.objects.create(
            name='Low Stock Ring',
            sku='LOW-001',
            category=self.category,
            weight_grams=Decimal('10.000'),
            karat=18,
            manufacturing_cost=Decimal('5000000.00'),
            gold_value=Decimal('15000000.00'),
            quantity=1,  # Below minimum
            minimum_stock=3,
            status='in_stock',
            created_by=self.user
        )
        
        self.out_of_stock_item = JewelryItem.objects.create(
            name='Out of Stock Ring',
            sku='OUT-001',
            category=self.category,
            weight_grams=Decimal('8.000'),
            karat=14,
            manufacturing_cost=Decimal('3000000.00'),
            gold_value=Decimal('10000000.00'),
            quantity=0,  # Out of stock
            minimum_stock=2,
            status='in_stock',
            created_by=self.user
        )
        
        self.normal_stock_item = JewelryItem.objects.create(
            name='Normal Stock Ring',
            sku='NORMAL-001',
            category=self.category,
            weight_grams=Decimal('12.000'),
            karat=18,
            manufacturing_cost=Decimal('6000000.00'),
            gold_value=Decimal('18000000.00'),
            quantity=5,  # Above minimum
            minimum_stock=2,
            status='in_stock',
            created_by=self.user
        )
    
    def test_get_low_stock_items(self):
        """Test getting low stock items."""
        low_stock_items = StockAlertService.get_low_stock_items()
        
        # Should return 2 items (low stock and out of stock)
        self.assertEqual(len(low_stock_items), 2)
        
        # Check item details
        item_skus = [item['item'].sku for item in low_stock_items]
        self.assertIn('LOW-001', item_skus)
        self.assertIn('OUT-001', item_skus)
        self.assertNotIn('NORMAL-001', item_skus)
        
        # Check shortage calculation
        for item_data in low_stock_items:
            if item_data['item'].sku == 'LOW-001':
                self.assertEqual(item_data['shortage'], 2)  # 3 - 1
                self.assertEqual(item_data['current_quantity'], 1)
            elif item_data['item'].sku == 'OUT-001':
                self.assertEqual(item_data['shortage'], 2)  # 2 - 0
                self.assertEqual(item_data['current_quantity'], 0)
    
    def test_get_low_stock_items_with_threshold_override(self):
        """Test getting low stock items with threshold override."""
        # Use threshold of 4 - should include normal stock item too
        low_stock_items = StockAlertService.get_low_stock_items(threshold_override=4)
        
        # Should return all 3 items
        self.assertEqual(len(low_stock_items), 3)
        
        item_skus = [item['item'].sku for item in low_stock_items]
        self.assertIn('LOW-001', item_skus)
        self.assertIn('OUT-001', item_skus)
        self.assertIn('NORMAL-001', item_skus)
    
    def test_get_stock_alerts_summary(self):
        """Test stock alerts summary."""
        summary = StockAlertService.get_stock_alerts_summary()
        
        self.assertEqual(summary['total_low_stock_items'], 2)
        self.assertEqual(summary['out_of_stock_items'], 1)
        self.assertGreater(summary['total_value_at_risk'], 0)
        self.assertIn('انگشتر', summary['category_breakdown'])
        self.assertEqual(len(summary['most_critical_items']), 2)
    
    def test_update_stock_thresholds(self):
        """Test updating stock thresholds."""
        updates = [
            {'item_id': self.low_stock_item.id, 'new_threshold': 5},
            {'item_id': self.normal_stock_item.id, 'new_threshold': 1}
        ]
        
        result = StockAlertService.update_stock_thresholds(updates)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['updated_count'], 2)
        self.assertEqual(len(result['errors']), 0)
        
        # Verify updates
        self.low_stock_item.refresh_from_db()
        self.normal_stock_item.refresh_from_db()
        
        self.assertEqual(self.low_stock_item.minimum_stock, 5)
        self.assertEqual(self.normal_stock_item.minimum_stock, 1)
    
    def test_update_stock_thresholds_with_errors(self):
        """Test updating stock thresholds with errors."""
        updates = [
            {'item_id': 99999, 'new_threshold': 5},  # Non-existent item
            {'item_id': self.low_stock_item.id, 'new_threshold': -1},  # Invalid threshold
            {'item_id': self.normal_stock_item.id, 'new_threshold': 3}  # Valid update
        ]
        
        result = StockAlertService.update_stock_thresholds(updates)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['updated_count'], 1)
        self.assertEqual(len(result['errors']), 2)
        
        # Check error details
        error_messages = [error['error'] for error in result['errors']]
        self.assertIn('Item not found', error_messages)
        self.assertIn('Threshold cannot be negative', error_messages)
    
    def test_create_reorder_suggestions(self):
        """Test creating reorder suggestions."""
        suggestions = StockAlertService.create_reorder_suggestions()
        
        # Should have suggestions for low stock items
        self.assertEqual(len(suggestions), 2)
        
        # Check suggestion details
        for suggestion in suggestions:
            self.assertIn('suggested_reorder_quantity', suggestion)
            self.assertIn('priority', suggestion)
            self.assertIn('estimated_cost', suggestion)
            self.assertGreater(suggestion['suggested_reorder_quantity'], 0)
            self.assertGreater(suggestion['priority'], 0)
    
    def test_calculate_reorder_priority(self):
        """Test reorder priority calculation."""
        item_data = {
            'shortage': 5,
            'value_at_risk': Decimal('100000000.00'),  # 100M Toman
            'days_since_low': 10
        }
        
        priority = StockAlertService._calculate_reorder_priority(item_data)
        
        # Should be high priority due to high shortage, value, and days
        self.assertGreater(priority, 50)
    
    def test_cache_functionality(self):
        """Test caching functionality."""
        # First call should cache the result
        result1 = StockAlertService.get_low_stock_items()
        
        # Second call should return cached result
        result2 = StockAlertService.get_low_stock_items()
        
        self.assertEqual(len(result1), len(result2))
        
        # Invalidate cache
        StockAlertService.invalidate_cache()
        
        # Should work after cache invalidation
        result3 = StockAlertService.get_low_stock_items()
        self.assertEqual(len(result1), len(result3))


class InventoryValuationServiceTest(TransactionTestCase):
    """Test InventoryValuationService functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Clear cache
        cache.clear()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testowner',
            email='owner@testshop.com',
            password='testpass123',
            role='owner'
        )
        
        # Create test categories
        self.ring_category = Category.objects.create(
            name='Rings',
            name_persian='انگشتر',
            created_by=self.user
        )
        
        self.necklace_category = Category.objects.create(
            name='Necklaces',
            name_persian='گردنبند',
            created_by=self.user
        )
        
        # Create test items
        self.ring_18k = JewelryItem.objects.create(
            name='18k Gold Ring',
            sku='RING-18K-001',
            category=self.ring_category,
            weight_grams=Decimal('15.000'),
            karat=18,
            manufacturing_cost=Decimal('5000000.00'),
            gold_value=Decimal('25000000.00'),
            gemstone_value=Decimal('10000000.00'),
            quantity=2,
            status='in_stock',
            created_by=self.user
        )
        
        self.necklace_14k = JewelryItem.objects.create(
            name='14k Gold Necklace',
            sku='NECK-14K-001',
            category=self.necklace_category,
            weight_grams=Decimal('20.000'),
            karat=14,
            manufacturing_cost=Decimal('8000000.00'),
            gold_value=Decimal('20000000.00'),
            gemstone_value=Decimal('5000000.00'),
            quantity=1,
            status='in_stock',
            created_by=self.user
        )
        
        self.sold_item = JewelryItem.objects.create(
            name='Sold Ring',
            sku='SOLD-001',
            category=self.ring_category,
            weight_grams=Decimal('10.000'),
            karat=18,
            manufacturing_cost=Decimal('3000000.00'),
            gold_value=Decimal('15000000.00'),
            quantity=1,
            status='sold',
            created_by=self.user
        )
    
    @patch('zargar.jewelry.services.GoldPriceService.get_current_gold_price')
    def test_calculate_total_inventory_value(self, mock_gold_price):
        """Test total inventory value calculation."""
        # Mock gold prices
        def mock_price_side_effect(karat):
            prices = {
                14: {'price_per_gram': Decimal('2500000.00')},  # 2.5M per gram
                18: {'price_per_gram': Decimal('3500000.00')},  # 3.5M per gram
                21: {'price_per_gram': Decimal('4000000.00')},
                22: {'price_per_gram': Decimal('4200000.00')},
                24: {'price_per_gram': Decimal('4500000.00')}
            }
            return prices.get(karat, {'price_per_gram': Decimal('0.00')})
        
        mock_gold_price.side_effect = mock_price_side_effect
        
        # Calculate valuation (excluding sold items)
        result = InventoryValuationService.calculate_total_inventory_value()
        
        self.assertEqual(result['total_items'], 3)  # 2 rings + 1 necklace
        self.assertFalse(result['includes_sold_items'])
        
        # Check category breakdown
        self.assertIn('انگشتر', result['category_breakdown'])
        self.assertIn('گردنبند', result['category_breakdown'])
        
        # Check karat breakdown
        self.assertIn('18k', result['karat_breakdown'])
        self.assertIn('14k', result['karat_breakdown'])
        
        # Verify gold prices were used
        self.assertIn(18, result['gold_prices_used'])
        self.assertIn(14, result['gold_prices_used'])
    
    @patch('zargar.jewelry.services.GoldPriceService.get_current_gold_price')
    def test_calculate_total_inventory_value_include_sold(self, mock_gold_price):
        """Test inventory valuation including sold items."""
        # Mock gold prices
        mock_gold_price.return_value = {'price_per_gram': Decimal('3500000.00')}
        
        # Calculate valuation including sold items
        result = InventoryValuationService.calculate_total_inventory_value(include_sold=True)
        
        self.assertEqual(result['total_items'], 4)  # All items
        self.assertTrue(result['includes_sold_items'])
    
    @patch('zargar.jewelry.services.GoldPriceService.get_current_gold_price')
    def test_calculate_total_inventory_value_category_filter(self, mock_gold_price):
        """Test inventory valuation with category filter."""
        # Mock gold prices
        mock_gold_price.return_value = {'price_per_gram': Decimal('3500000.00')}
        
        # Calculate valuation for rings only
        result = InventoryValuationService.calculate_total_inventory_value(
            category_filter=self.ring_category.id
        )
        
        self.assertEqual(result['total_items'], 2)  # Only rings
        self.assertEqual(result['category_filter'], self.ring_category.id)
        
        # Should only have ring category in breakdown
        self.assertIn('انگشتر', result['category_breakdown'])
        self.assertNotIn('گردنبند', result['category_breakdown'])
    
    @patch('zargar.jewelry.services.GoldPriceService.get_current_gold_price')
    def test_update_all_gold_values(self, mock_gold_price):
        """Test updating all gold values."""
        # Mock gold prices
        def mock_price_side_effect(karat):
            prices = {
                14: {'price_per_gram': Decimal('2800000.00')},  # New price
                18: {'price_per_gram': Decimal('3800000.00')},  # New price
                21: {'price_per_gram': Decimal('4200000.00')},
                22: {'price_per_gram': Decimal('4400000.00')},
                24: {'price_per_gram': Decimal('4700000.00')}
            }
            return prices.get(karat, {'price_per_gram': Decimal('0.00')})
        
        mock_gold_price.side_effect = mock_price_side_effect
        
        # Store original values
        original_ring_value = self.ring_18k.gold_value
        original_necklace_value = self.necklace_14k.gold_value
        
        # Update all gold values
        result = InventoryValuationService.update_all_gold_values()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['updated_count'], 2)  # Only in-stock items
        self.assertEqual(result['error_count'], 0)
        
        # Verify items were updated
        self.ring_18k.refresh_from_db()
        self.necklace_14k.refresh_from_db()
        
        # Values should have changed
        self.assertNotEqual(self.ring_18k.gold_value, original_ring_value)
        self.assertNotEqual(self.necklace_14k.gold_value, original_necklace_value)
        
        # Check updated values are correct
        expected_ring_value = self.ring_18k.calculate_gold_value(Decimal('3800000.00'))
        expected_necklace_value = self.necklace_14k.calculate_gold_value(Decimal('2800000.00'))
        
        self.assertEqual(self.ring_18k.gold_value, expected_ring_value)
        self.assertEqual(self.necklace_14k.gold_value, expected_necklace_value)
    
    @patch('zargar.jewelry.services.GoldPriceService.get_current_gold_price')
    def test_update_all_gold_values_with_errors(self, mock_gold_price):
        """Test updating gold values with API errors."""
        # Mock gold price service to raise exception
        mock_gold_price.side_effect = Exception("API Error")
        
        result = InventoryValuationService.update_all_gold_values()
        
        self.assertFalse(result['success'])
        self.assertIn('Could not retrieve any gold prices', result['message'])
    
    @patch('zargar.jewelry.services.GoldPriceService.get_current_gold_price')
    def test_get_top_value_items(self, mock_gold_price):
        """Test getting top value items."""
        # Mock gold prices
        mock_gold_price.return_value = {'price_per_gram': Decimal('3500000.00')}
        
        top_items = InventoryValuationService.get_top_value_items(limit=5)
        
        # Should return items sorted by value
        self.assertGreater(len(top_items), 0)
        self.assertLessEqual(len(top_items), 5)
        
        # Check that items are sorted by value (descending)
        if len(top_items) > 1:
            for i in range(len(top_items) - 1):
                self.assertGreaterEqual(
                    top_items[i]['current_total_value'],
                    top_items[i + 1]['current_total_value']
                )
        
        # Check item data structure
        for item_data in top_items:
            self.assertIn('item', item_data)
            self.assertIn('current_total_value', item_data)
            self.assertIn('current_gold_value', item_data)
            self.assertIn('value_per_unit', item_data)
            self.assertIn('category', item_data)
            self.assertIn('has_serial', item_data)
    
    def test_get_valuation_history(self):
        """Test getting valuation history."""
        history = InventoryValuationService.get_valuation_history(days=7)
        
        self.assertEqual(len(history), 7)
        
        # Check data structure
        for day_data in history:
            self.assertIn('date', day_data)
            self.assertIn('total_value', day_data)
            self.assertIn('gold_value', day_data)
            self.assertIn('manufacturing_cost', day_data)
            self.assertIn('gemstone_value', day_data)
    
    def test_cache_functionality(self):
        """Test caching functionality."""
        with patch('zargar.jewelry.services.GoldPriceService.get_current_gold_price') as mock_gold_price:
            mock_gold_price.return_value = {'price_per_gram': Decimal('3500000.00')}
            
            # First call should cache the result
            result1 = InventoryValuationService.calculate_total_inventory_value()
            
            # Second call should return cached result (mock shouldn't be called again)
            mock_gold_price.reset_mock()
            result2 = InventoryValuationService.calculate_total_inventory_value()
            
            # Results should be the same
            self.assertEqual(result1['total_items'], result2['total_items'])
            
            # Mock should not have been called for cached result
            mock_gold_price.assert_not_called()
            
            # Invalidate cache
            InventoryValuationService.invalidate_cache()
            
            # Next call should hit the API again
            result3 = InventoryValuationService.calculate_total_inventory_value()
            mock_gold_price.assert_called()


class InventoryTrackingServiceTest(TransactionTestCase):
    """Test InventoryTrackingService functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Clear cache
        cache.clear()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testowner',
            email='owner@testshop.com',
            password='testpass123',
            role='owner'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Rings',
            name_persian='انگشتر',
            created_by=self.user
        )
        
        # Create high-value item without serial
        self.high_value_item = JewelryItem.objects.create(
            name='Premium Ring',
            sku='PREMIUM-001',
            category=self.category,
            weight_grams=Decimal('20.000'),
            karat=18,
            manufacturing_cost=Decimal('15000000.00'),
            gold_value=Decimal('40000000.00'),
            gemstone_value=Decimal('25000000.00'),
            quantity=1,
            minimum_stock=2,  # Low stock
            status='in_stock',
            created_by=self.user
        )
    
    @patch('zargar.jewelry.services.GoldPriceService.get_current_gold_price')
    def test_get_comprehensive_inventory_status(self, mock_gold_price):
        """Test comprehensive inventory status."""
        # Mock gold prices
        mock_gold_price.return_value = {'price_per_gram': Decimal('3500000.00')}
        
        status = InventoryTrackingService.get_comprehensive_inventory_status()
        
        # Check all required sections
        self.assertIn('inventory_valuation', status)
        self.assertIn('stock_alerts', status)
        self.assertIn('serial_number_tracking', status)
        self.assertIn('top_value_items', status)
        self.assertIn('reorder_suggestions', status)
        self.assertIn('summary_statistics', status)
        self.assertIn('last_updated', status)
        
        # Check summary statistics
        summary = status['summary_statistics']
        self.assertIn('total_items', summary)
        self.assertIn('total_value', summary)
        self.assertIn('low_stock_items', summary)
        self.assertIn('items_needing_serial', summary)
        
        # Verify serial number tracking
        serial_tracking = status['serial_number_tracking']
        self.assertGreater(serial_tracking['high_value_without_serial'], 0)
        self.assertGreater(len(serial_tracking['items_needing_serial']), 0)
    
    @patch('zargar.jewelry.services.GoldPriceService.get_current_gold_price')
    def test_perform_daily_maintenance(self, mock_gold_price):
        """Test daily maintenance tasks."""
        # Mock gold prices
        mock_gold_price.return_value = {'price_per_gram': Decimal('3500000.00')}
        
        result = InventoryTrackingService.perform_daily_maintenance()
        
        self.assertIn('timestamp', result)
        self.assertIn('tasks_completed', result)
        self.assertIn('errors', result)
        
        # Check that tasks were attempted
        task_names = [task['task'] for task in result['tasks_completed']]
        self.assertIn('update_gold_values', task_names)
        self.assertIn('assign_serial_numbers', task_names)
        self.assertIn('clear_caches', task_names)
        
        # Verify serial number assignment
        serial_task = next(
            task for task in result['tasks_completed'] 
            if task['task'] == 'assign_serial_numbers'
        )
        self.assertTrue(serial_task['success'])
        self.assertGreaterEqual(serial_task['assigned_count'], 0)
        self.assertGreater(serial_task['eligible_count'], 0)
    
    @patch('zargar.jewelry.services.InventoryValuationService.update_all_gold_values')
    def test_perform_daily_maintenance_with_errors(self, mock_update_gold):
        """Test daily maintenance with errors."""
        # Mock gold value update to fail
        mock_update_gold.return_value = {
            'success': False,
            'message': 'API Error'
        }
        
        result = InventoryTrackingService.perform_daily_maintenance()
        
        # Should have errors
        self.assertGreater(len(result['errors']), 0)
        
        # Check error details
        error_tasks = [error['task'] for error in result['errors']]
        self.assertIn('update_gold_values', error_tasks)


class InventoryTrackingIntegrationTest(TransactionTestCase):
    """Integration tests for the complete inventory tracking system."""
    
    def setUp(self):
        """Set up comprehensive test data."""
        # Clear cache
        cache.clear()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testowner',
            email='owner@testshop.com',
            password='testpass123',
            role='owner'
        )
        
        # Create categories
        self.ring_category = Category.objects.create(
            name='Rings',
            name_persian='انگشتر',
            created_by=self.user
        )
        
        # Create gemstone
        self.diamond = Gemstone.objects.create(
            name='Premium Diamond',
            gemstone_type='diamond',
            carat_weight=Decimal('1.500'),
            cut_grade='excellent',
            color_grade='D',
            clarity_grade='VVS1',
            purchase_price=Decimal('30000000.00'),
            created_by=self.user
        )
        
        # Create comprehensive test item
        self.test_item = JewelryItem.objects.create(
            name='Premium Diamond Ring',
            sku='PREMIUM-RING-001',
            category=self.ring_category,
            weight_grams=Decimal('18.500'),
            karat=18,
            manufacturing_cost=Decimal('12000000.00'),
            gold_value=Decimal('35000000.00'),
            gemstone_value=Decimal('30000000.00'),
            quantity=1,
            minimum_stock=3,
            status='in_stock',
            created_by=self.user
        )
        
        # Add gemstone relationship
        self.test_item.gemstones.add(self.diamond)
    
    @patch('zargar.jewelry.services.GoldPriceService.get_current_gold_price')
    def test_complete_inventory_workflow(self, mock_gold_price):
        """Test complete inventory tracking workflow."""
        # Mock gold prices
        mock_gold_price.return_value = {'price_per_gram': Decimal('4000000.00')}
        
        # 1. Check initial status
        status = InventoryTrackingService.get_comprehensive_inventory_status()
        
        # Should have low stock alert
        self.assertGreater(status['stock_alerts']['total_low_stock_items'], 0)
        
        # Should need serial number
        self.assertGreater(status['serial_number_tracking']['high_value_without_serial'], 0)
        
        # 2. Assign serial number
        serial_result = SerialNumberTrackingService.assign_serial_number(self.test_item)
        self.assertTrue(serial_result['success'])
        
        # 3. Update stock threshold
        threshold_result = StockAlertService.update_stock_thresholds([
            {'item_id': self.test_item.id, 'new_threshold': 1}
        ])
        self.assertTrue(threshold_result['success'])
        
        # 4. Update gold values
        valuation_result = InventoryValuationService.update_all_gold_values()
        self.assertTrue(valuation_result['success'])
        
        # 5. Check final status
        final_status = InventoryTrackingService.get_comprehensive_inventory_status()
        
        # Should have updated values
        self.assertGreater(final_status['inventory_valuation']['total_current_value'], 0)
        
        # Should have fewer items needing serial numbers
        self.assertEqual(final_status['serial_number_tracking']['high_value_without_serial'], 0)
        
        # Should have fewer low stock items (due to threshold change)
        self.assertEqual(final_status['stock_alerts']['total_low_stock_items'], 0)
    
    @patch('zargar.jewelry.services.GoldPriceService.get_current_gold_price')
    def test_performance_with_multiple_items(self, mock_gold_price):
        """Test system performance with multiple items."""
        # Mock gold prices
        mock_gold_price.return_value = {'price_per_gram': Decimal('3500000.00')}
        
        # Create multiple items
        items = []
        for i in range(50):
            item = JewelryItem.objects.create(
                name=f'Test Item {i}',
                sku=f'TEST-{i:03d}',
                category=self.ring_category,
                weight_grams=Decimal('10.000'),
                karat=18,
                manufacturing_cost=Decimal('5000000.00'),
                gold_value=Decimal('15000000.00'),
                quantity=i % 5,  # Varying quantities
                minimum_stock=2,
                status='in_stock',
                created_by=self.user
            )
            items.append(item)
        
        # Test comprehensive status (should handle 50+ items efficiently)
        import time
        start_time = time.time()
        
        status = InventoryTrackingService.get_comprehensive_inventory_status()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within reasonable time (< 5 seconds)
        self.assertLess(execution_time, 5.0)
        
        # Should have correct counts
        self.assertGreaterEqual(status['summary_statistics']['total_items'], 51)  # Original + 50 new
        
        # Should identify low stock items
        self.assertGreater(status['stock_alerts']['total_low_stock_items'], 0)
    
    def test_error_handling_and_recovery(self):
        """Test error handling and system recovery."""
        # Test with invalid item ID
        threshold_result = StockAlertService.update_stock_thresholds([
            {'item_id': 99999, 'new_threshold': 5}
        ])
        
        self.assertTrue(threshold_result['success'])  # Should succeed overall
        self.assertEqual(threshold_result['updated_count'], 0)
        self.assertGreater(len(threshold_result['errors']), 0)
        
        # Test serial number validation with invalid format
        validation_result = SerialNumberTrackingService.validate_serial_number('INVALID')
        self.assertFalse(validation_result['valid'])
        
        # System should continue working after errors
        status = InventoryTrackingService.get_comprehensive_inventory_status()
        self.assertIn('summary_statistics', status)


if __name__ == '__main__':
    pytest.main([__file__])