"""
Unit tests for integration settings backend functionality.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing Django modules
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
import json
import uuid
import requests
from unittest.mock import patch, Mock
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from zargar.admin_panel.models import (
    ExternalServiceConfiguration,
    APIRateLimitConfiguration,
    IntegrationHealthCheck,
    SettingChangeHistory
)
from zargar.admin_panel.services.integration_service import (
    IntegrationManager,
    APIRateLimitManager,
    integration_manager,
    rate_limit_manager
)

User = get_user_model()


class ExternalServiceConfigurationModelTest(TestCase):
    """Test ExternalServiceConfiguration model."""
    
    def setUp(self):
        self.service_data = {
            'name': 'Test Gold Price API',
            'service_type': 'gold_price_api',
            'base_url': 'https://api.goldprice.com/v1',
            'authentication_type': 'api_key',
            'api_key': 'test-api-key-123',
            'timeout_seconds': 30,
            'max_retries': 3,
            'rate_limit_requests': 100,
            'rate_limit_window_seconds': 3600,
            'health_check_interval_minutes': 15,
        }
    
    def test_create_service_configuration(self):
        """Test creating a service configuration."""
        service = ExternalServiceConfiguration.objects.create(**self.service_data)
        
        self.assertEqual(service.name, 'Test Gold Price API')
        self.assertEqual(service.service_type, 'gold_price_api')
        self.assertEqual(service.base_url, 'https://api.goldprice.com/v1')
        self.assertEqual(service.authentication_type, 'api_key')
        self.assertEqual(service.status, 'inactive')  # Default status
        self.assertTrue(service.is_enabled)  # Default enabled
        self.assertIsNotNone(service.service_id)  # UUID should be generated
    
    def test_service_string_representation(self):
        """Test string representation of service."""
        service = ExternalServiceConfiguration.objects.create(**self.service_data)
        expected = f"{service.name} ({service.get_service_type_display()})"
        self.assertEqual(str(service), expected)
    
    def test_service_health_properties(self):
        """Test service health-related properties."""
        service = ExternalServiceConfiguration.objects.create(**self.service_data)
        
        # Initially not healthy (no health check)
        self.assertFalse(service.is_healthy)
        
        # Mark as healthy
        service.mark_healthy()
        self.assertTrue(service.is_healthy)
        self.assertEqual(service.status, 'active')
    
    def test_service_statistics(self):
        """Test service statistics tracking."""
        service = ExternalServiceConfiguration.objects.create(**self.service_data)
        
        # Initial statistics
        self.assertEqual(service.total_requests, 0)
        self.assertEqual(service.successful_requests, 0)
        self.assertEqual(service.failed_requests, 0)
        self.assertEqual(service.success_rate, 0.0)
        
        # Update statistics
        service.update_statistics(success=True, response_time_ms=150.5)
        service.refresh_from_db()
        
        self.assertEqual(service.total_requests, 1)
        self.assertEqual(service.successful_requests, 1)
        self.assertEqual(service.failed_requests, 0)
        self.assertEqual(service.success_rate, 100.0)
        self.assertEqual(service.average_response_time_ms, 150.5)
        
        # Add failed request
        service.update_statistics(success=False, response_time_ms=300.0)
        service.refresh_from_db()
        
        self.assertEqual(service.total_requests, 2)
        self.assertEqual(service.successful_requests, 1)
        self.assertEqual(service.failed_requests, 1)
        self.assertEqual(service.success_rate, 50.0)
    
    def test_record_error(self):
        """Test error recording."""
        service = ExternalServiceConfiguration.objects.create(**self.service_data)
        
        error_message = "Connection timeout"
        service.record_error(error_message)
        service.refresh_from_db()
        
        self.assertEqual(service.last_error_message, error_message)
        self.assertIsNotNone(service.last_error_time)
        self.assertEqual(service.status, 'error')
    
    def test_get_masked_credentials(self):
        """Test credential masking for display."""
        service = ExternalServiceConfiguration.objects.create(**self.service_data)
        
        masked = service.get_masked_credentials()
        
        # API key should be masked
        self.assertIn('api_key', masked)
        self.assertTrue(masked['api_key'].startswith('*'))
        self.assertTrue(masked['api_key'].endswith('123'))  # Last 4 chars


class APIRateLimitConfigurationModelTest(TestCase):
    """Test APIRateLimitConfiguration model."""
    
    def setUp(self):
        self.rate_limit_data = {
            'name': 'Test API Rate Limit',
            'limit_type': 'per_user',
            'requests_limit': 100,
            'time_window_seconds': 3600,
            'endpoint_pattern': '/api/v1/.*',
            'block_duration_seconds': 3600,
            'warning_threshold_percentage': 80,
        }
    
    def test_create_rate_limit_configuration(self):
        """Test creating a rate limit configuration."""
        config = APIRateLimitConfiguration.objects.create(**self.rate_limit_data)
        
        self.assertEqual(config.name, 'Test API Rate Limit')
        self.assertEqual(config.limit_type, 'per_user')
        self.assertEqual(config.requests_limit, 100)
        self.assertEqual(config.time_window_seconds, 3600)
        self.assertTrue(config.is_active)  # Default active
        self.assertIsNotNone(config.config_id)  # UUID should be generated
    
    def test_rate_limit_string_representation(self):
        """Test string representation of rate limit."""
        config = APIRateLimitConfiguration.objects.create(**self.rate_limit_data)
        expected = f"{config.name} ({config.requests_limit}/Per Hour)"
        self.assertEqual(str(config), expected)
    
    def test_exemption_methods(self):
        """Test exemption checking methods."""
        config = APIRateLimitConfiguration.objects.create(
            **self.rate_limit_data,
            exempt_user_ids=[1, 2, 3],
            exempt_ip_addresses=['192.168.1.1', '10.0.0.1']
        )
        
        # Test user exemptions
        self.assertTrue(config.is_exempt_user(1))
        self.assertTrue(config.is_exempt_user(2))
        self.assertFalse(config.is_exempt_user(4))
        
        # Test IP exemptions
        self.assertTrue(config.is_exempt_ip('192.168.1.1'))
        self.assertTrue(config.is_exempt_ip('10.0.0.1'))
        self.assertFalse(config.is_exempt_ip('192.168.1.2'))
    
    def test_record_statistics(self):
        """Test recording rate limit statistics."""
        config = APIRateLimitConfiguration.objects.create(**self.rate_limit_data)
        
        # Initial statistics
        self.assertEqual(config.total_requests_blocked, 0)
        self.assertEqual(config.total_warnings_issued, 0)
        self.assertIsNone(config.last_triggered)
        
        # Record block
        config.record_block()
        config.refresh_from_db()
        
        self.assertEqual(config.total_requests_blocked, 1)
        self.assertIsNotNone(config.last_triggered)
        
        # Record warning
        config.record_warning()
        config.refresh_from_db()
        
        self.assertEqual(config.total_warnings_issued, 1)


class IntegrationHealthCheckModelTest(TestCase):
    """Test IntegrationHealthCheck model."""
    
    def setUp(self):
        self.service = ExternalServiceConfiguration.objects.create(
            name='Test Service',
            service_type='gold_price_api',
            base_url='https://api.test.com',
            authentication_type='api_key',
            api_key='test-key'
        )
    
    def test_create_health_check(self):
        """Test creating a health check record."""
        health_check = IntegrationHealthCheck.objects.create(
            service=self.service,
            check_type='connectivity',
            status='healthy',
            success=True,
            response_time_ms=150.5,
            details={'status_code': 200},
            metrics={'response_size': 1024}
        )
        
        self.assertEqual(health_check.service, self.service)
        self.assertEqual(health_check.check_type, 'connectivity')
        self.assertEqual(health_check.status, 'healthy')
        self.assertTrue(health_check.success)
        self.assertEqual(health_check.response_time_ms, 150.5)
        self.assertIsNotNone(health_check.check_id)
    
    def test_health_check_string_representation(self):
        """Test string representation of health check."""
        health_check = IntegrationHealthCheck.objects.create(
            service=self.service,
            check_type='connectivity',
            status='healthy',
            success=True
        )
        
        expected = f"{self.service.name} - Connectivity Check (Healthy)"
        self.assertEqual(str(health_check), expected)
    
    def test_calculate_next_check(self):
        """Test next check calculation."""
        health_check = IntegrationHealthCheck.objects.create(
            service=self.service,
            check_type='connectivity',
            status='healthy',
            success=True
        )
        
        # Initially no next check time
        self.assertIsNone(health_check.next_check_at)
        
        # Calculate next check
        health_check.calculate_next_check()
        
        # Should have next check time
        self.assertIsNotNone(health_check.next_check_at)
        self.assertGreater(health_check.next_check_at, health_check.checked_at)
    
    def test_is_overdue(self):
        """Test overdue check detection."""
        health_check = IntegrationHealthCheck.objects.create(
            service=self.service,
            check_type='connectivity',
            status='healthy',
            success=True
        )
        
        # Not overdue without next check time
        self.assertFalse(health_check.is_overdue)
        
        # Set next check time in the past
        past_time = timezone.now() - timezone.timedelta(hours=1)
        health_check.next_check_at = past_time
        health_check.save()
        
        # Should be overdue
        self.assertTrue(health_check.is_overdue)


class IntegrationManagerTest(TestCase):
    """Test IntegrationManager service."""
    
    def setUp(self):
        self.manager = IntegrationManager()
        self.service_data = {
            'name': 'Test Service',
            'service_type': 'gold_price_api',
            'base_url': 'https://api.test.com',
            'authentication_type': 'api_key',
            'api_key': 'test-api-key'
        }
    
    def test_create_service_configuration(self):
        """Test creating service configuration through manager."""
        service = self.manager.create_service_configuration(**self.service_data)
        
        self.assertIsInstance(service, ExternalServiceConfiguration)
        self.assertEqual(service.name, 'Test Service')
        self.assertEqual(service.service_type, 'gold_price_api')
    
    def test_create_service_with_invalid_data(self):
        """Test creating service with invalid data."""
        invalid_data = self.service_data.copy()
        invalid_data['base_url'] = 'invalid-url'  # Invalid URL
        
        with self.assertRaises(ValidationError):
            self.manager.create_service_configuration(**invalid_data)
    
    def test_update_service_configuration(self):
        """Test updating service configuration."""
        # Create service first
        service = self.manager.create_service_configuration(**self.service_data)
        
        # Update service
        updated_service = self.manager.update_service_configuration(
            service_id=str(service.service_id),
            user_id=1,
            user_username='testuser',
            name='Updated Service Name',
            timeout_seconds=60
        )
        
        self.assertEqual(updated_service.name, 'Updated Service Name')
        self.assertEqual(updated_service.timeout_seconds, 60)
    
    def test_update_nonexistent_service(self):
        """Test updating non-existent service."""
        fake_id = str(uuid.uuid4())
        
        with self.assertRaises(ValidationError):
            self.manager.update_service_configuration(
                service_id=fake_id,
                user_id=1,
                user_username='testuser',
                name='Updated Name'
            )
    
    @patch('requests.get')
    def test_test_service_connection_success(self, mock_get):
        """Test successful service connection test."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.reason = 'OK'
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.content = b'{"status": "ok"}'
        mock_get.return_value = mock_response
        
        # Create service
        service = self.manager.create_service_configuration(**self.service_data)
        
        # Test connection
        result = self.manager.test_service_connection(str(service.service_id))
        
        self.assertTrue(result['success'])
        self.assertEqual(result['status_code'], 200)
        self.assertIn('response_time_ms', result)
        self.assertEqual(result['message'], 'Connection test successful')
    
    @patch('requests.get')
    def test_test_service_connection_failure(self, mock_get):
        """Test failed service connection test."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.reason = 'Unauthorized'
        mock_response.text = 'Invalid API key'
        mock_get.return_value = mock_response
        
        # Create service
        service = self.manager.create_service_configuration(**self.service_data)
        
        # Test connection
        result = self.manager.test_service_connection(str(service.service_id))
        
        self.assertFalse(result['success'])
        self.assertEqual(result['status_code'], 401)
        self.assertEqual(result['message'], 'Connection test failed')
        self.assertIn('error', result)
    
    @patch('requests.get')
    def test_test_service_connection_timeout(self, mock_get):
        """Test service connection timeout."""
        # Mock timeout exception
        mock_get.side_effect = requests.exceptions.Timeout()
        
        # Create service
        service = self.manager.create_service_configuration(**self.service_data)
        
        # Test connection
        result = self.manager.test_service_connection(str(service.service_id))
        
        self.assertFalse(result['success'])
        self.assertEqual(result['message'], 'Connection test failed')
        self.assertIn('timeout', result['error'].lower())
    
    def test_get_service_health_status(self):
        """Test getting service health status."""
        # Create service
        service = self.manager.create_service_configuration(**self.service_data)
        
        # Get health status
        health_status = self.manager.get_service_health_status(str(service.service_id))
        
        self.assertIn('service_id', health_status)
        self.assertIn('service_name', health_status)
        self.assertIn('overall_status', health_status)
        self.assertIn('health_score', health_status)
        self.assertIn('statistics', health_status)
        self.assertEqual(health_status['service_name'], 'Test Service')
    
    def test_get_all_services_health(self):
        """Test getting health status for all services."""
        # Create multiple services
        service1 = self.manager.create_service_configuration(**self.service_data)
        
        service2_data = self.service_data.copy()
        service2_data['name'] = 'Test Service 2'
        service2 = self.manager.create_service_configuration(**service2_data)
        
        # Get all health statuses
        health_statuses = self.manager.get_all_services_health()
        
        self.assertEqual(len(health_statuses), 2)
        service_names = [status['service_name'] for status in health_statuses]
        self.assertIn('Test Service', service_names)
        self.assertIn('Test Service 2', service_names)
    
    @patch('requests.get')
    def test_perform_health_check(self, mock_get):
        """Test performing health check."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.reason = 'OK'
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.content = b'{"status": "ok"}'
        mock_get.return_value = mock_response
        
        # Create service
        service = self.manager.create_service_configuration(**self.service_data)
        
        # Perform health check
        health_check = self.manager.perform_health_check(
            str(service.service_id), 
            'connectivity'
        )
        
        self.assertIsInstance(health_check, IntegrationHealthCheck)
        self.assertEqual(health_check.service, service)
        self.assertEqual(health_check.check_type, 'connectivity')
        self.assertTrue(health_check.success)
        self.assertEqual(health_check.status, 'healthy')


class APIRateLimitManagerTest(TestCase):
    """Test APIRateLimitManager service."""
    
    def setUp(self):
        self.manager = APIRateLimitManager()
        self.rate_limit_data = {
            'name': 'Test Rate Limit',
            'limit_type': 'per_user',
            'requests_limit': 100,
            'time_window_seconds': 3600
        }
    
    def test_create_rate_limit_config(self):
        """Test creating rate limit configuration."""
        config = self.manager.create_rate_limit_config(**self.rate_limit_data)
        
        self.assertIsInstance(config, APIRateLimitConfiguration)
        self.assertEqual(config.name, 'Test Rate Limit')
        self.assertEqual(config.limit_type, 'per_user')
        self.assertEqual(config.requests_limit, 100)
    
    def test_update_rate_limit_config(self):
        """Test updating rate limit configuration."""
        # Create config first
        config = self.manager.create_rate_limit_config(**self.rate_limit_data)
        
        # Update config
        updated_config = self.manager.update_rate_limit_config(
            config_id=str(config.config_id),
            user_id=1,
            user_username='testuser',
            name='Updated Rate Limit',
            requests_limit=200
        )
        
        self.assertEqual(updated_config.name, 'Updated Rate Limit')
        self.assertEqual(updated_config.requests_limit, 200)
    
    def test_validate_rate_limit_config(self):
        """Test rate limit configuration validation."""
        # Create valid config
        config = self.manager.create_rate_limit_config(**self.rate_limit_data)
        
        # Should have no validation issues
        issues = self.manager.validate_rate_limit_config(config)
        self.assertEqual(len(issues), 0)
        
        # Create invalid config
        config.time_window_seconds = 30  # Too short
        config.requests_limit = 0  # Too low
        config.warning_threshold_percentage = 150  # Too high
        
        issues = self.manager.validate_rate_limit_config(config)
        self.assertGreater(len(issues), 0)
        self.assertTrue(any('time window' in issue.lower() for issue in issues))
        self.assertTrue(any('requests limit' in issue.lower() for issue in issues))
        self.assertTrue(any('warning threshold' in issue.lower() for issue in issues))
    
    def test_get_active_rate_limits(self):
        """Test getting active rate limits."""
        # Create active config
        active_config = self.manager.create_rate_limit_config(
            **self.rate_limit_data,
            is_active=True
        )
        
        # Create inactive config
        inactive_data = self.rate_limit_data.copy()
        inactive_data['name'] = 'Inactive Rate Limit'
        inactive_config = self.manager.create_rate_limit_config(
            **inactive_data,
            is_active=False
        )
        
        # Get active configs
        active_configs = self.manager.get_active_rate_limits()
        
        self.assertEqual(len(active_configs), 1)
        self.assertEqual(active_configs[0].name, 'Test Rate Limit')
    
    def test_get_rate_limit_statistics(self):
        """Test getting rate limit statistics."""
        # Create configs with some statistics
        config1 = self.manager.create_rate_limit_config(**self.rate_limit_data)
        config1.total_requests_blocked = 10
        config1.total_warnings_issued = 5
        config1.save()
        
        config2_data = self.rate_limit_data.copy()
        config2_data['name'] = 'Test Rate Limit 2'
        config2 = self.manager.create_rate_limit_config(**config2_data)
        config2.total_requests_blocked = 20
        config2.total_warnings_issued = 15
        config2.save()
        
        # Get statistics
        stats = self.manager.get_rate_limit_statistics()
        
        self.assertEqual(stats['total_configurations'], 2)
        self.assertEqual(stats['active_configurations'], 2)
        self.assertEqual(stats['total_requests_blocked'], 30)
        self.assertEqual(stats['total_warnings_issued'], 20)
        self.assertEqual(len(stats['most_triggered_configs']), 2)


class IntegrationSettingsIntegrationTest(TransactionTestCase):
    """Integration tests for the complete integration settings system."""
    
    def setUp(self):
        self.integration_manager = IntegrationManager()
        self.rate_limit_manager = APIRateLimitManager()
    
    def test_complete_service_lifecycle(self):
        """Test complete service configuration lifecycle."""
        # Create service
        service = self.integration_manager.create_service_configuration(
            name='Lifecycle Test Service',
            service_type='gold_price_api',
            base_url='https://api.lifecycle.test',
            authentication_type='api_key',
            api_key='test-key-123'
        )
        
        self.assertIsNotNone(service.service_id)
        self.assertEqual(service.name, 'Lifecycle Test Service')
        
        # Update service
        updated_service = self.integration_manager.update_service_configuration(
            service_id=str(service.service_id),
            user_id=1,
            user_username='testuser',
            name='Updated Lifecycle Service',
            timeout_seconds=60
        )
        
        self.assertEqual(updated_service.name, 'Updated Lifecycle Service')
        self.assertEqual(updated_service.timeout_seconds, 60)
        
        # Get health status
        health_status = self.integration_manager.get_service_health_status(
            str(service.service_id)
        )
        
        self.assertEqual(health_status['service_name'], 'Updated Lifecycle Service')
        self.assertIn('overall_status', health_status)
        
        # Delete service
        service.delete()
        
        # Should not be able to get health status anymore
        health_status = self.integration_manager.get_service_health_status(
            str(service.service_id)
        )
        self.assertIn('error', health_status)
    
    def test_complete_rate_limit_lifecycle(self):
        """Test complete rate limit configuration lifecycle."""
        # Create rate limit config
        config = self.rate_limit_manager.create_rate_limit_config(
            name='Lifecycle Rate Limit',
            limit_type='per_user',
            requests_limit=100,
            time_window_seconds=3600
        )
        
        self.assertIsNotNone(config.config_id)
        self.assertEqual(config.name, 'Lifecycle Rate Limit')
        
        # Validate config
        issues = self.rate_limit_manager.validate_rate_limit_config(config)
        self.assertEqual(len(issues), 0)
        
        # Update config
        updated_config = self.rate_limit_manager.update_rate_limit_config(
            config_id=str(config.config_id),
            user_id=1,
            user_username='testuser',
            name='Updated Lifecycle Rate Limit',
            requests_limit=200
        )
        
        self.assertEqual(updated_config.name, 'Updated Lifecycle Rate Limit')
        self.assertEqual(updated_config.requests_limit, 200)
        
        # Record statistics
        config.record_block()
        config.record_warning()
        config.refresh_from_db()
        
        self.assertEqual(config.total_requests_blocked, 1)
        self.assertEqual(config.total_warnings_issued, 1)
        
        # Get statistics
        stats = self.rate_limit_manager.get_rate_limit_statistics()
        self.assertGreater(stats['total_configurations'], 0)
        self.assertGreater(stats['total_requests_blocked'], 0)
        
        # Delete config
        config.delete()
        
        # Should not be in active configs anymore
        active_configs = self.rate_limit_manager.get_active_rate_limits()
        config_ids = [str(c.config_id) for c in active_configs]
        self.assertNotIn(str(config.config_id), config_ids)


if __name__ == '__main__':
    pytest.main([__file__])