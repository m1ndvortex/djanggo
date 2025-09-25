"""
Integration settings service for managing external service configurations.
"""
import requests
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from django.conf import settings
from cryptography.fernet import Fernet
import json
import re

from ..models import (
    ExternalServiceConfiguration, 
    APIRateLimitConfiguration,
    IntegrationHealthCheck,
    SettingChangeHistory
)

logger = logging.getLogger(__name__)


class IntegrationManager:
    """
    Service for managing external service integrations.
    """
    
    def __init__(self):
        self.encryption_key = self._get_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key) if self.encryption_key else None
    
    def _get_encryption_key(self) -> Optional[bytes]:
        """Get encryption key for sensitive data."""
        key = getattr(settings, 'INTEGRATION_ENCRYPTION_KEY', None)
        if key:
            return key.encode() if isinstance(key, str) else key
        return None
    
    def _encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data like API keys and passwords."""
        if not self.cipher_suite or not data:
            return data
        
        try:
            return self.cipher_suite.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt sensitive data: {e}")
            return data
    
    def _decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        if not self.cipher_suite or not encrypted_data:
            return encrypted_data
        
        try:
            return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt sensitive data: {e}")
            return encrypted_data
    
    def create_service_configuration(
        self, 
        name: str,
        service_type: str,
        base_url: str,
        authentication_type: str = 'api_key',
        **kwargs
    ) -> ExternalServiceConfiguration:
        """
        Create a new external service configuration.
        """
        try:
            with transaction.atomic():
                # Encrypt sensitive fields
                encrypted_kwargs = kwargs.copy()
                if 'api_key' in encrypted_kwargs:
                    encrypted_kwargs['api_key'] = self._encrypt_sensitive_data(
                        encrypted_kwargs['api_key']
                    )
                if 'password' in encrypted_kwargs:
                    encrypted_kwargs['password'] = self._encrypt_sensitive_data(
                        encrypted_kwargs['password']
                    )
                if 'oauth_client_secret' in encrypted_kwargs:
                    encrypted_kwargs['oauth_client_secret'] = self._encrypt_sensitive_data(
                        encrypted_kwargs['oauth_client_secret']
                    )
                
                service = ExternalServiceConfiguration.objects.create(
                    name=name,
                    service_type=service_type,
                    base_url=base_url,
                    authentication_type=authentication_type,
                    **encrypted_kwargs
                )
                
                logger.info(f"Created service configuration: {service.name}")
                return service
                
        except Exception as e:
            logger.error(f"Failed to create service configuration: {e}")
            raise ValidationError(f"Failed to create service configuration: {str(e)}")
    
    def update_service_configuration(
        self,
        service_id: str,
        user_id: int,
        user_username: str,
        **updates
    ) -> ExternalServiceConfiguration:
        """
        Update an existing service configuration.
        """
        try:
            service = ExternalServiceConfiguration.objects.get(service_id=service_id)
            old_values = {}
            new_values = {}
            
            with transaction.atomic():
                # Track changes for audit
                for field, new_value in updates.items():
                    if hasattr(service, field):
                        old_value = getattr(service, field)
                        
                        # Encrypt sensitive fields
                        if field in ['api_key', 'password', 'oauth_client_secret']:
                            new_value = self._encrypt_sensitive_data(str(new_value))
                            old_values[field] = '[ENCRYPTED]'
                            new_values[field] = '[ENCRYPTED]'
                        else:
                            old_values[field] = old_value
                            new_values[field] = new_value
                        
                        setattr(service, field, new_value)
                
                service.save()
                
                # Log the change
                SettingChangeHistory.log_change(
                    setting_type='integration',
                    setting_key=f"service_{service.service_id}",
                    old_values=old_values,
                    new_values=new_values,
                    performed_by_id=user_id,
                    performed_by_username=user_username,
                    object_id=str(service.service_id),
                    object_name=service.name
                )
                
                logger.info(f"Updated service configuration: {service.name}")
                return service
                
        except ExternalServiceConfiguration.DoesNotExist:
            raise ValidationError("Service configuration not found")
        except Exception as e:
            logger.error(f"Failed to update service configuration: {e}")
            raise ValidationError(f"Failed to update service configuration: {str(e)}")
    
    def test_service_connection(self, service_id: str) -> Dict[str, Any]:
        """
        Test connection to an external service.
        """
        try:
            service = ExternalServiceConfiguration.objects.get(service_id=service_id)
            
            # Prepare request headers
            headers = {'User-Agent': 'ZARGAR-Integration-Test/1.0'}
            headers.update(service.custom_headers)
            
            # Add authentication
            if service.authentication_type == 'api_key' and service.api_key:
                decrypted_key = self._decrypt_sensitive_data(service.api_key)
                headers['Authorization'] = f'Bearer {decrypted_key}'
            elif service.authentication_type == 'bearer_token' and service.api_key:
                decrypted_token = self._decrypt_sensitive_data(service.api_key)
                headers['Authorization'] = f'Bearer {decrypted_token}'
            elif service.authentication_type == 'custom_header' and service.api_key:
                decrypted_key = self._decrypt_sensitive_data(service.api_key)
                headers['X-API-Key'] = decrypted_key
            
            # Prepare authentication for basic auth
            auth = None
            if service.authentication_type == 'basic_auth':
                username = service.username
                password = self._decrypt_sensitive_data(service.password) if service.password else ''
                auth = (username, password)
            
            # Make test request
            start_time = time.time()
            
            try:
                response = requests.get(
                    service.base_url,
                    headers=headers,
                    auth=auth,
                    timeout=service.timeout_seconds,
                    verify=True  # Always verify SSL certificates
                )
                
                response_time_ms = (time.time() - start_time) * 1000
                
                # Update service statistics
                service.update_statistics(
                    success=response.status_code < 400,
                    response_time_ms=response_time_ms
                )
                
                if response.status_code < 400:
                    service.mark_healthy()
                    
                    return {
                        'success': True,
                        'status_code': response.status_code,
                        'response_time_ms': response_time_ms,
                        'message': 'Connection test successful',
                        'details': {
                            'url': service.base_url,
                            'response_headers': dict(response.headers),
                            'content_length': len(response.content)
                        }
                    }
                else:
                    error_msg = f"HTTP {response.status_code}: {response.reason}"
                    service.record_error(error_msg)
                    
                    return {
                        'success': False,
                        'status_code': response.status_code,
                        'response_time_ms': response_time_ms,
                        'message': 'Connection test failed',
                        'error': error_msg,
                        'details': {
                            'url': service.base_url,
                            'response_text': response.text[:500]  # First 500 chars
                        }
                    }
                    
            except requests.exceptions.Timeout:
                error_msg = f"Connection timeout after {service.timeout_seconds} seconds"
                service.record_error(error_msg)
                
                return {
                    'success': False,
                    'message': 'Connection test failed',
                    'error': error_msg,
                    'details': {'url': service.base_url}
                }
                
            except requests.exceptions.ConnectionError as e:
                error_msg = f"Connection error: {str(e)}"
                service.record_error(error_msg)
                
                return {
                    'success': False,
                    'message': 'Connection test failed',
                    'error': error_msg,
                    'details': {'url': service.base_url}
                }
                
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                service.record_error(error_msg)
                
                return {
                    'success': False,
                    'message': 'Connection test failed',
                    'error': error_msg,
                    'details': {'url': service.base_url}
                }
                
        except ExternalServiceConfiguration.DoesNotExist:
            return {
                'success': False,
                'message': 'Service configuration not found',
                'error': 'Invalid service ID'
            }
        except Exception as e:
            logger.error(f"Failed to test service connection: {e}")
            return {
                'success': False,
                'message': 'Connection test failed',
                'error': str(e)
            }
    
    def get_service_health_status(self, service_id: str) -> Dict[str, Any]:
        """
        Get comprehensive health status for a service.
        """
        try:
            service = ExternalServiceConfiguration.objects.get(service_id=service_id)
            
            # Get recent health checks
            recent_checks = IntegrationHealthCheck.objects.filter(
                service=service
            ).order_by('-checked_at')[:10]
            
            # Calculate health metrics
            total_checks = recent_checks.count()
            successful_checks = recent_checks.filter(success=True).count()
            
            health_score = 0
            if total_checks > 0:
                health_score = (successful_checks / total_checks) * 100
            
            # Determine overall status
            if health_score >= 95:
                overall_status = 'healthy'
            elif health_score >= 80:
                overall_status = 'warning'
            else:
                overall_status = 'critical'
            
            return {
                'service_id': str(service.service_id),
                'service_name': service.name,
                'overall_status': overall_status,
                'health_score': health_score,
                'is_enabled': service.is_enabled,
                'last_health_check': service.last_health_check,
                'is_healthy': service.is_healthy,
                'statistics': {
                    'total_requests': service.total_requests,
                    'successful_requests': service.successful_requests,
                    'failed_requests': service.failed_requests,
                    'success_rate': service.success_rate,
                    'average_response_time_ms': service.average_response_time_ms
                },
                'recent_checks': [
                    {
                        'check_type': check.check_type,
                        'status': check.status,
                        'success': check.success,
                        'response_time_ms': check.response_time_ms,
                        'checked_at': check.checked_at,
                        'error_message': check.error_message
                    }
                    for check in recent_checks
                ],
                'last_error': {
                    'message': service.last_error_message,
                    'time': service.last_error_time
                } if service.last_error_message else None
            }
            
        except ExternalServiceConfiguration.DoesNotExist:
            return {
                'error': 'Service configuration not found'
            }
        except Exception as e:
            logger.error(f"Failed to get service health status: {e}")
            return {
                'error': str(e)
            }
    
    def get_all_services_health(self) -> List[Dict[str, Any]]:
        """
        Get health status for all configured services.
        """
        services = ExternalServiceConfiguration.objects.filter(is_enabled=True)
        health_statuses = []
        
        for service in services:
            health_status = self.get_service_health_status(str(service.service_id))
            health_statuses.append(health_status)
        
        return health_statuses
    
    def perform_health_check(self, service_id: str, check_type: str = 'connectivity') -> IntegrationHealthCheck:
        """
        Perform a health check on a service.
        """
        try:
            service = ExternalServiceConfiguration.objects.get(service_id=service_id)
            
            # Perform the actual health check based on type
            if check_type == 'connectivity':
                result = self.test_service_connection(service_id)
            elif check_type == 'authentication':
                result = self._test_authentication(service)
            elif check_type == 'functionality':
                result = self._test_functionality(service)
            elif check_type == 'performance':
                result = self._test_performance(service)
            else:
                result = {'success': False, 'error': f'Unknown check type: {check_type}'}
            
            # Determine status based on result
            if result['success']:
                status = 'healthy'
            elif 'warning' in result.get('message', '').lower():
                status = 'warning'
            else:
                status = 'critical'
            
            # Create health check record
            health_check = IntegrationHealthCheck.objects.create(
                service=service,
                check_type=check_type,
                status=status,
                success=result['success'],
                response_time_ms=result.get('response_time_ms'),
                details=result.get('details', {}),
                error_message=result.get('error', ''),
                warnings=result.get('warnings', []),
                metrics=result.get('metrics', {})
            )
            
            # Calculate next check time
            health_check.calculate_next_check()
            
            logger.info(f"Performed {check_type} health check for {service.name}: {status}")
            return health_check
            
        except ExternalServiceConfiguration.DoesNotExist:
            logger.error(f"Service not found for health check: {service_id}")
            raise ValidationError("Service configuration not found")
        except Exception as e:
            logger.error(f"Failed to perform health check: {e}")
            raise ValidationError(f"Failed to perform health check: {str(e)}")
    
    def _test_authentication(self, service: ExternalServiceConfiguration) -> Dict[str, Any]:
        """Test authentication with the service."""
        # This is a placeholder - implement specific authentication tests
        # based on the service type and authentication method
        return self.test_service_connection(str(service.service_id))
    
    def _test_functionality(self, service: ExternalServiceConfiguration) -> Dict[str, Any]:
        """Test core functionality of the service."""
        # This is a placeholder - implement service-specific functionality tests
        return self.test_service_connection(str(service.service_id))
    
    def _test_performance(self, service: ExternalServiceConfiguration) -> Dict[str, Any]:
        """Test performance characteristics of the service."""
        # This is a placeholder - implement performance-specific tests
        result = self.test_service_connection(str(service.service_id))
        
        if result['success']:
            response_time = result.get('response_time_ms', 0)
            if response_time > 5000:  # 5 seconds
                result['warnings'] = ['High response time detected']
                result['status'] = 'warning'
        
        return result


class APIRateLimitManager:
    """
    Service for managing API rate limit configurations.
    """
    
    def create_rate_limit_config(
        self,
        name: str,
        limit_type: str,
        requests_limit: int,
        time_window_seconds: int,
        **kwargs
    ) -> APIRateLimitConfiguration:
        """
        Create a new API rate limit configuration.
        """
        try:
            with transaction.atomic():
                config = APIRateLimitConfiguration.objects.create(
                    name=name,
                    limit_type=limit_type,
                    requests_limit=requests_limit,
                    time_window_seconds=time_window_seconds,
                    **kwargs
                )
                
                logger.info(f"Created rate limit configuration: {config.name}")
                return config
                
        except Exception as e:
            logger.error(f"Failed to create rate limit configuration: {e}")
            raise ValidationError(f"Failed to create rate limit configuration: {str(e)}")
    
    def update_rate_limit_config(
        self,
        config_id: str,
        user_id: int,
        user_username: str,
        **updates
    ) -> APIRateLimitConfiguration:
        """
        Update an existing rate limit configuration.
        """
        try:
            config = APIRateLimitConfiguration.objects.get(config_id=config_id)
            old_values = {}
            new_values = {}
            
            with transaction.atomic():
                # Track changes for audit
                for field, new_value in updates.items():
                    if hasattr(config, field):
                        old_values[field] = getattr(config, field)
                        new_values[field] = new_value
                        setattr(config, field, new_value)
                
                config.save()
                
                # Log the change
                SettingChangeHistory.log_change(
                    setting_type='rate_limit',
                    setting_key=f"rate_limit_{config.config_id}",
                    old_values=old_values,
                    new_values=new_values,
                    performed_by_id=user_id,
                    performed_by_username=user_username,
                    object_id=str(config.config_id),
                    object_name=config.name
                )
                
                logger.info(f"Updated rate limit configuration: {config.name}")
                return config
                
        except APIRateLimitConfiguration.DoesNotExist:
            raise ValidationError("Rate limit configuration not found")
        except Exception as e:
            logger.error(f"Failed to update rate limit configuration: {e}")
            raise ValidationError(f"Failed to update rate limit configuration: {str(e)}")
    
    def validate_rate_limit_config(self, config: APIRateLimitConfiguration) -> List[str]:
        """
        Validate a rate limit configuration and return any issues.
        """
        issues = []
        
        # Validate endpoint pattern if it's a regex
        if config.endpoint_pattern:
            try:
                re.compile(config.endpoint_pattern)
            except re.error as e:
                issues.append(f"Invalid endpoint pattern regex: {str(e)}")
        
        # Validate time window
        if config.time_window_seconds < 60:
            issues.append("Time window should be at least 60 seconds")
        
        # Validate requests limit
        if config.requests_limit < 1:
            issues.append("Requests limit must be at least 1")
        
        # Validate warning threshold
        if config.warning_threshold_percentage < 1 or config.warning_threshold_percentage > 100:
            issues.append("Warning threshold must be between 1 and 100 percent")
        
        # Validate block duration
        if config.block_duration_seconds < 60:
            issues.append("Block duration should be at least 60 seconds")
        
        return issues
    
    def get_active_rate_limits(self) -> List[APIRateLimitConfiguration]:
        """
        Get all active rate limit configurations.
        """
        return list(APIRateLimitConfiguration.objects.filter(is_active=True))
    
    def get_rate_limit_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about rate limiting.
        """
        configs = APIRateLimitConfiguration.objects.all()
        
        total_configs = configs.count()
        active_configs = configs.filter(is_active=True).count()
        total_blocks = sum(config.total_requests_blocked for config in configs)
        total_warnings = sum(config.total_warnings_issued for config in configs)
        
        # Get most triggered configs
        most_triggered = configs.filter(
            total_requests_blocked__gt=0
        ).order_by('-total_requests_blocked')[:5]
        
        return {
            'total_configurations': total_configs,
            'active_configurations': active_configs,
            'total_requests_blocked': total_blocks,
            'total_warnings_issued': total_warnings,
            'most_triggered_configs': [
                {
                    'name': config.name,
                    'requests_blocked': config.total_requests_blocked,
                    'warnings_issued': config.total_warnings_issued,
                    'last_triggered': config.last_triggered
                }
                for config in most_triggered
            ]
        }


# Global instances
integration_manager = IntegrationManager()
rate_limit_manager = APIRateLimitManager()