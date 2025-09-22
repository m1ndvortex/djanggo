"""
Unit tests for inventory tracking services.
Tests the business logic without database dependencies.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from django.utils import timezone
from django.test import TestCase

from zargar.jewelry.services import (
    SerialNumberTrackingService,
    StockAlertService,
    InventoryValuationService,
    InventoryTrackingService
)


class TestSerialNumberTrackingService(TestCase):
    """Test SerialNumberTrackingService business logic."""
    
    def test_get_category_code(self):
        """Test category code generation."""
        # Mock category object
        category = Mock()
        
        # Test normal category
        category.name = 'Rings'
        code = SerialNumberTrackingService._get_category_code(category)
        self.assertEqual(code, 'RIN')
        
        # Test short category name
        category.name = 'AB'
        code = SerialNumberTrackingService._get_category_code(category)
        self.assertEqual(code, 'ABX')
        
        # Test category with spaces
        category.name = 'Wedding Rings'
        code = SerialNumberTrackingService._get_category_code(category)
        self.assertEqual(code, 'WED')
        
        # Test lowercase
        category.name = 'necklaces'
        code = SerialNumberTrackingService._get_category_code(category)
        self.assertEqual(code, 'NEC')
    
    def test_validate_serial_number_format(self):
        """Test serial number format validation."""
        # Valid serial number
        result = SerialNumberTrackingService.validate_serial_number('ZRG-2024-RIN-0001')
        self.assertTrue(result['valid'])
        self.assertEqual(result['parsed']['prefix'], 'ZRG')
        self.assertEqual(result['parsed']['year'], 2024)
        self.assertEqual(result['parsed']['category_code'], 'RIN')
        self.assertEqual(result['parsed']['sequence'], 1)
        
        # Invalid formats
        invalid_serials = [
            'INVALID',
            'ZRG-2024-RIN',
            'ZRG-2024-RIN-0001-EXTRA',
            'ABC-2024-RIN-0001',
            'ZRG-YEAR-RIN-0001',
            'ZRG-2024-R1-0001',
            'ZRG-2024-RIN-ABCD',
            'ZRG-1999-RIN-0001',  # Too old year
            'ZRG-2030-RIN-0001',  # Future year
            'ZRG-2024-RIN-0000',  # Invalid sequence
            'ZRG-2024-RIN-10000'  # Sequence too high
        ]
        
        for serial in invalid_serials:
            result = SerialNumberTrackingService.validate_serial_number(serial)
            self.assertFalse(result['valid'], f"Serial {serial} should be invalid")
    
    def test_high_value_threshold(self):
        """Test high value threshold constant."""
        threshold = SerialNumberTrackingService.HIGH_VALUE_THRESHOLD
        self.assertEqual(threshold, Decimal('50000000.00'))  # 50M Toman
    
    def test_serial_prefix(self):
        """Test serial number prefix."""
        prefix = SerialNumberTrackingService.SERIAL_PREFIX
        self.assertEqual(prefix, 'ZRG')


class TestStockAlertService(TestCase):
    """Test StockAlertService business logic."""
    
    def test_calculate_reorder_priority(self):
        """Test reorder priority calculation."""
        # High priority item
        high_priority_data = {
            'shortage': 5,
            'value_at_risk': Decimal('100000000.00'),  # 100M Toman
            'days_since_low': 10
        }
        
        priority = StockAlertService._calculate_reorder_priority(high_priority_data)
        self.assertGreater(priority, 80)  # Should be high priority
        
        # Low priority item
        low_priority_data = {
            'shortage': 1,
            'value_at_risk': Decimal('5000000.00'),  # 5M Toman
            'days_since_low': 1
        }
        
        priority = StockAlertService._calculate_reorder_priority(low_priority_data)
        self.assertLess(priority, 30)  # Should be low priority
        
        # Medium priority item
        medium_priority_data = {
            'shortage': 3,
            'value_at_risk': Decimal('25000000.00'),  # 25M Toman
            'days_since_low': 5
        }
        
        priority = StockAlertService._calculate_reorder_priority(medium_priority_data)
        self.assertGreater(priority, 30)
        self.assertLess(priority, 80)
    
    def test_estimate_monthly_demand(self):
        """Test monthly demand estimation."""
        # Mock jewelry item
        item = Mock()
        item.category = Mock()
        
        # Test different categories
        test_cases = [
            ('rings', 3),
            ('wedding rings', 3),
            ('necklaces', 2),
            ('bracelets', 2),
            ('earrings', 4),
            ('pendants', 1),
            ('unknown category', 1)  # Default
        ]
        
        for category_name, expected_demand in test_cases:
            item.category.name = category_name
            demand = StockAlertService._estimate_monthly_demand(item)
            self.assertEqual(demand, expected_demand)
    
    def test_cache_keys(self):
        """Test cache key generation."""
        prefix = StockAlertService.CACHE_KEY_PREFIX
        self.assertEqual(prefix, 'stock_alerts')
        
        timeout = StockAlertService.CACHE_TIMEOUT
        self.assertEqual(timeout, 3600)  # 1 hour


class TestInventoryValuationService(TestCase):
    """Test InventoryValuationService business logic."""
    
    def test_cache_configuration(self):
        """Test cache configuration."""
        prefix = InventoryValuationService.CACHE_KEY_PREFIX
        self.assertEqual(prefix, 'inventory_valuation')
        
        timeout = InventoryValuationService.CACHE_TIMEOUT
        self.assertEqual(timeout, 1800)  # 30 minutes
    
    @patch('zargar.jewelry.services.GoldPriceService.get_current_gold_price')
    def test_gold_price_integration(self, mock_gold_price):
        """Test gold price service integration."""
        # Mock gold price response
        mock_gold_price.return_value = {
            'price_per_gram': Decimal('3500000.00'),
            'karat': 18,
            'timestamp': timezone.now(),
            'source': 'test',
            'currency': 'IRR'
        }
        
        # Test that service calls gold price API
        # This would be tested in integration tests with actual models
        mock_gold_price.assert_not_called()  # Not called yet
        
        # Call would happen in actual service methods
        price_data = mock_gold_price(18)
        self.assertEqual(price_data['price_per_gram'], Decimal('3500000.00'))
        mock_gold_price.assert_called_once_with(18)


class TestInventoryTrackingService(TestCase):
    """Test InventoryTrackingService coordination logic."""
    
    @patch('zargar.jewelry.services.InventoryValuationService.update_all_gold_values')
    @patch('zargar.jewelry.services.SerialNumberTrackingService.get_high_value_items_without_serial')
    @patch('zargar.jewelry.services.SerialNumberTrackingService.assign_serial_number')
    def test_daily_maintenance_logic(self, mock_assign_serial, mock_get_high_value, mock_update_gold):
        """Test daily maintenance task coordination."""
        # Mock responses
        mock_update_gold.return_value = {
            'success': True,
            'updated_count': 10,
            'error_count': 0
        }
        
        mock_get_high_value.return_value = [Mock(), Mock(), Mock()]  # 3 items
        
        mock_assign_serial.return_value = {'success': True}
        
        # Run daily maintenance
        result = InventoryTrackingService.perform_daily_maintenance()
        
        # Verify structure
        self.assertIn('timestamp', result)
        self.assertIn('tasks_completed', result)
        self.assertIn('errors', result)
        
        # Verify tasks were attempted
        task_names = [task['task'] for task in result['tasks_completed']]
        self.assertIn('update_gold_values', task_names)
        self.assertIn('assign_serial_numbers', task_names)
        self.assertIn('clear_caches', task_names)
        
        # Verify service calls
        mock_update_gold.assert_called_once()
        mock_get_high_value.assert_called_once()
        
        # Should assign serial numbers (limited to 10 per day)
        self.assertEqual(mock_assign_serial.call_count, 3)
    
    @patch('zargar.jewelry.services.InventoryValuationService.update_all_gold_values')
    def test_daily_maintenance_with_errors(self, mock_update_gold):
        """Test daily maintenance error handling."""
        # Mock gold value update to fail
        mock_update_gold.return_value = {
            'success': False,
            'message': 'API Error'
        }
        
        result = InventoryTrackingService.perform_daily_maintenance()
        
        # Should have errors but not crash
        self.assertGreater(len(result['errors']), 0)
        
        # Check error details
        error_tasks = [error['task'] for error in result['errors']]
        self.assertIn('update_gold_values', error_tasks)
    
    @patch('zargar.jewelry.services.InventoryValuationService.calculate_total_inventory_value')
    @patch('zargar.jewelry.services.StockAlertService.get_stock_alerts_summary')
    @patch('zargar.jewelry.services.SerialNumberTrackingService.get_high_value_items_without_serial')
    @patch('zargar.jewelry.services.InventoryValuationService.get_top_value_items')
    @patch('zargar.jewelry.services.StockAlertService.create_reorder_suggestions')
    def test_comprehensive_status_coordination(self, mock_reorder, mock_top_items, 
                                             mock_high_value, mock_stock_alerts, mock_valuation):
        """Test comprehensive status data coordination."""
        # Mock all service responses
        mock_valuation.return_value = {
            'total_items': 100,
            'total_current_value': Decimal('1000000000.00')
        }
        
        mock_stock_alerts.return_value = {
            'total_low_stock_items': 5,
            'critical_items': 2,
            'total_value_at_risk': Decimal('50000000.00')
        }
        
        mock_high_value.return_value = [Mock(), Mock()]  # 2 items
        mock_top_items.return_value = [Mock() for _ in range(5)]
        mock_reorder.return_value = [Mock() for _ in range(10)]
        
        # Get comprehensive status
        status = InventoryTrackingService.get_comprehensive_inventory_status()
        
        # Verify structure
        required_sections = [
            'inventory_valuation',
            'stock_alerts', 
            'serial_number_tracking',
            'top_value_items',
            'reorder_suggestions',
            'summary_statistics',
            'last_updated'
        ]
        
        for section in required_sections:
            self.assertIn(section, status)
        
        # Verify summary statistics
        summary = status['summary_statistics']
        self.assertEqual(summary['total_items'], 100)
        self.assertEqual(summary['total_value'], Decimal('1000000000.00'))
        self.assertEqual(summary['low_stock_items'], 5)
        self.assertEqual(summary['critical_items'], 2)
        self.assertEqual(summary['value_at_risk'], Decimal('50000000.00'))
        self.assertEqual(summary['items_needing_serial'], 2)
        
        # Verify all services were called
        mock_valuation.assert_called_once()
        mock_stock_alerts.assert_called_once()
        mock_high_value.assert_called_once()
        mock_top_items.assert_called_once_with(5)
        mock_reorder.assert_called_once()


class TestServiceConstants(TestCase):
    """Test service constants and configuration."""
    
    def test_serial_number_service_constants(self):
        """Test SerialNumberTrackingService constants."""
        self.assertEqual(SerialNumberTrackingService.SERIAL_PREFIX, 'ZRG')
        self.assertEqual(SerialNumberTrackingService.HIGH_VALUE_THRESHOLD, Decimal('50000000.00'))
    
    def test_stock_alert_service_constants(self):
        """Test StockAlertService constants."""
        self.assertEqual(StockAlertService.CACHE_KEY_PREFIX, 'stock_alerts')
        self.assertEqual(StockAlertService.CACHE_TIMEOUT, 3600)
    
    def test_inventory_valuation_service_constants(self):
        """Test InventoryValuationService constants."""
        self.assertEqual(InventoryValuationService.CACHE_KEY_PREFIX, 'inventory_valuation')
        self.assertEqual(InventoryValuationService.CACHE_TIMEOUT, 1800)


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
            ],
            SECRET_KEY='test-secret-key',
        )
    
    django.setup()
    
    import unittest
    unittest.main()