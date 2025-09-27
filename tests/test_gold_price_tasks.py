"""
Tests for gold installment Celery tasks.
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, Mock
from django.test import TestCase
from django.utils import timezone

from zargar.gold_installments.tasks import (
    update_gold_prices,
    calculate_daily_contract_metrics,
    cleanup_expired_price_cache
)
from zargar.gold_installments.services import GoldPriceService


class GoldPriceTasksTest(TestCase):
    """Test Celery tasks for gold price system."""
    
    def test_update_gold_prices_task_success(self):
        """Test successful gold price update task."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {'price': 3600000}
        mock_response.raise_for_status.return_value = None
        
        with patch('requests.get', return_value=mock_response):
            # Run the task
            result = update_gold_prices.apply(args=[[18, 24]]).get()
            
            self.assertTrue(result['success'])
            self.assertIn('updated_prices', result)
            self.assertIn(18, result['updated_prices'])
            self.assertIn(24, result['updated_prices'])
            self.assertIn('timestamp', result)
            
            # Verify prices were updated
            price_18k = result['updated_prices'][18]
            price_24k = result['updated_prices'][24]
            
            self.assertEqual(price_18k['karat'], 18)
            self.assertEqual(price_24k['karat'], 24)
            self.assertEqual(price_18k['price_per_gram'], Decimal('3600000'))
            # 24k should be higher than 18k
            self.assertGreater(price_24k['price_per_gram'], price_18k['price_per_gram'])
    
    def test_update_gold_prices_task_api_failure(self):
        """Test gold price update task when API fails."""
        # Mock API failure
        with patch('requests.get', side_effect=Exception("API Error")):
            # Run the task
            result = update_gold_prices.apply(args=[[18]]).get()
            
            self.assertTrue(result['success'])  # Should still succeed with fallback
            self.assertIn('updated_prices', result)
            self.assertIn(18, result['updated_prices'])
            
            # Should use fallback source
            price_data = result['updated_prices'][18]
            self.assertEqual(price_data['source'], 'fallback')
    
    def test_update_gold_prices_task_default_karats(self):
        """Test gold price update task with default karats."""
        mock_response = Mock()
        mock_response.json.return_value = {'price': 3500000}
        mock_response.raise_for_status.return_value = None
        
        with patch('requests.get', return_value=mock_response):
            # Run task without specifying karats (should use defaults)
            result = update_gold_prices.apply().get()
            
            self.assertTrue(result['success'])
            self.assertIn('updated_prices', result)
            
            # Should have updated default karats
            expected_karats = [14, 18, 21, 22, 24]
            for karat in expected_karats:
                self.assertIn(karat, result['updated_prices'])
    
    def test_calculate_daily_contract_metrics_task(self):
        """Test daily contract metrics calculation task."""
        # Mock empty contract queryset to avoid database issues
        mock_queryset = Mock()
        mock_queryset.count.return_value = 0
        mock_queryset.__iter__ = Mock(return_value=iter([]))
        
        with patch('zargar.gold_installments.models.GoldInstallmentContract.objects.filter', return_value=mock_queryset):
            # Mock gold price service
            mock_price_data = {
                'price_per_gram': Decimal('3500000'),
                'karat': 18,
                'timestamp': timezone.now(),
                'source': 'test',
                'currency': 'IRR'
            }
            
            with patch.object(GoldPriceService, 'get_current_gold_price', return_value=mock_price_data):
                # Run the task
                result = calculate_daily_contract_metrics.apply().get()
                
                self.assertTrue(result['success'])
                self.assertIn('metrics', result)
                self.assertIn('timestamp', result)
                
                metrics = result['metrics']
                
                # Check required metrics are present
                required_metrics = [
                    'total_active_contracts',
                    'total_remaining_gold_weight',
                    'total_remaining_value',
                    'overdue_contracts',
                    'contracts_near_completion',
                    'price_protection_active'
                ]
                
                for metric in required_metrics:
                    self.assertIn(metric, metrics)
                    # All values should be strings (for JSON serialization)
                    self.assertIsInstance(metrics[metric], (str, int))
    
    def test_cleanup_expired_price_cache_task(self):
        """Test cache cleanup task."""
        # Run the task
        result = cleanup_expired_price_cache.apply().get()
        
        self.assertTrue(result['success'])
        self.assertIn('timestamp', result)
    
    def test_update_gold_prices_task_retry_mechanism(self):
        """Test retry mechanism for gold price update task."""
        # Mock API failure that should use fallback
        with patch('requests.get', side_effect=Exception("Network Error")):
            # Run the task - should succeed with fallback
            result = update_gold_prices.apply(args=[[18]]).get()
            
            # Should succeed with fallback mechanism
            self.assertTrue(result['success'])
            self.assertIn('updated_prices', result)
            self.assertIn(18, result['updated_prices'])
            
            # Should use fallback source
            price_data = result['updated_prices'][18]
            self.assertEqual(price_data['source'], 'fallback')
    
    def test_gold_price_service_integration_in_tasks(self):
        """Test that tasks properly integrate with GoldPriceService."""
        # Mock the service method
        mock_price_data = {
            'price_per_gram': Decimal('3700000'),
            'karat': 18,
            'timestamp': timezone.now(),
            'source': 'primary',
            'currency': 'IRR'
        }
        
        with patch.object(GoldPriceService, 'get_current_gold_price', return_value=mock_price_data) as mock_service:
            with patch.object(GoldPriceService, 'invalidate_cache') as mock_invalidate:
                # Run update task
                result = update_gold_prices.apply(args=[[18]]).get()
                
                # Verify service methods were called
                mock_invalidate.assert_called_with(18)
                mock_service.assert_called_with(18)
                
                # Verify result
                self.assertTrue(result['success'])
                self.assertEqual(
                    result['updated_prices'][18]['price_per_gram'], 
                    Decimal('3700000')
                )


class TaskErrorHandlingTest(TestCase):
    """Test error handling in Celery tasks."""
    
    def test_update_gold_prices_handles_invalid_karat(self):
        """Test handling of invalid karat values."""
        # Test with invalid karat (should not crash)
        result = update_gold_prices.apply(args=[[0, -1, 999]]).get()
        
        # Task should complete but may have limited results
        self.assertTrue(result['success'])
        self.assertIn('updated_prices', result)
    
    def test_calculate_metrics_handles_no_contracts(self):
        """Test metrics calculation when no contracts exist."""
        # Mock empty contract queryset
        mock_queryset = Mock()
        mock_queryset.count.return_value = 0
        mock_queryset.__iter__ = Mock(return_value=iter([]))
        
        with patch('zargar.gold_installments.models.GoldInstallmentContract.objects.filter', return_value=mock_queryset):
            # Mock gold price service
            mock_price_data = {
                'price_per_gram': Decimal('3500000'),
                'karat': 18,
                'timestamp': timezone.now(),
                'source': 'test',
                'currency': 'IRR'
            }
            
            with patch.object(GoldPriceService, 'get_current_gold_price', return_value=mock_price_data):
                result = calculate_daily_contract_metrics.apply().get()
                
                self.assertTrue(result['success'])
                metrics = result['metrics']
                self.assertEqual(int(metrics['total_active_contracts']), 0)
                self.assertEqual(metrics['total_remaining_gold_weight'], '0.000')
                self.assertEqual(metrics['total_remaining_value'], '0.00')
    
    def test_task_exception_handling(self):
        """Test general exception handling in tasks."""
        # Mock contract queryset to avoid database issues
        mock_queryset = Mock()
        mock_queryset.count.return_value = 0
        mock_queryset.__iter__ = Mock(return_value=iter([]))
        
        with patch('zargar.gold_installments.models.GoldInstallmentContract.objects.filter', return_value=mock_queryset):
            # Mock a service method to raise an exception
            with patch.object(GoldPriceService, 'get_current_gold_price', side_effect=Exception("Service Error")):
                result = calculate_daily_contract_metrics.apply().get()
                
                # Task should handle the exception gracefully
                self.assertFalse(result['success'])
                self.assertIn('error', result)
                self.assertEqual(result['error'], 'Service Error')


class TaskPerformanceTest(TestCase):
    """Test performance aspects of tasks."""
    
    def test_update_gold_prices_caching_behavior(self):
        """Test that price updates properly use caching."""
        mock_response = Mock()
        mock_response.json.return_value = {'price': 3500000}
        mock_response.raise_for_status.return_value = None
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            # First update should fetch from API
            result1 = update_gold_prices.apply(args=[[18]]).get()
            self.assertTrue(result1['success'])
            
            # Verify API was called
            self.assertTrue(mock_get.called)
            
            # Reset mock
            mock_get.reset_mock()
            
            # Second call should use cache (no API call)
            price_data = GoldPriceService.get_current_gold_price(18)
            self.assertEqual(price_data['price_per_gram'], Decimal('3500000'))
            
            # API should not be called again due to caching
            self.assertFalse(mock_get.called)
    
    def test_bulk_price_update_efficiency(self):
        """Test efficiency of updating multiple karats."""
        mock_response = Mock()
        mock_response.json.return_value = {'price': 3500000}
        mock_response.raise_for_status.return_value = None
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            # Update multiple karats
            karats = [14, 18, 21, 22, 24]
            result = update_gold_prices.apply(args=[karats]).get()
            
            self.assertTrue(result['success'])
            self.assertEqual(len(result['updated_prices']), len(karats))
            
            # Verify all karats were processed
            for karat in karats:
                self.assertIn(karat, result['updated_prices'])
                price_data = result['updated_prices'][karat]
                self.assertEqual(price_data['karat'], karat)
                self.assertGreater(price_data['price_per_gram'], Decimal('0'))