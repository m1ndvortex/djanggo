"""
Integration settings views for super admin panel.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.http import JsonResponse, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.core.paginator import Paginator
import json
import logging

from .models import (
    ExternalServiceConfiguration, 
    APIRateLimitConfiguration,
    IntegrationHealthCheck
)
from .views import SuperAdminRequiredMixin

# Mock integration managers for now
class MockIntegrationManager:
    def get_all_services_health(self):
        return []
    
    def get_service_health_status(self, service_id):
        return {'overall_status': 'healthy', 'response_time_ms': 150, 'last_check_time': timezone.now()}
    
    def test_service_connection(self, service_id):
        return {'success': True, 'message': 'Connection successful'}
    
    def perform_health_check(self, service_id, check_type):
        return IntegrationHealthCheck(
            service_id=service_id,
            check_type=check_type,
            status='healthy',
            success=True,
            response_time_ms=150,
            checked_at=timezone.now()
        )

class MockRateLimitManager:
    def get_rate_limit_statistics(self):
        return {}

# Initialize mock managers
integration_manager = MockIntegrationManager()
rate_limit_manager = MockRateLimitManager()

logger = logging.getLogger(__name__)


class IntegrationSettingsView(SuperAdminRequiredMixin, TemplateView):
    """
    Main integration settings interface.
    """
    template_name = 'admin_panel/settings/integration_settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Get all external service configurations
            services = ExternalServiceConfiguration.objects.all().order_by('name')
            
            # Get rate limit configurations
            rate_limits = APIRateLimitConfiguration.objects.all().order_by('name')
            
            # Get health status for all services
            health_statuses = integration_manager.get_all_services_health()
            
            # Get rate limit statistics
            rate_limit_stats = rate_limit_manager.get_rate_limit_statistics()
            
            # Calculate overall integration health
            total_services = services.count()
            healthy_services = total_services  # Mock: assume all are healthy for now
            
            overall_health = 'healthy'
            if total_services > 0:
                health_percentage = (healthy_services / total_services) * 100
                if health_percentage < 50:
                    overall_health = 'critical'
                elif health_percentage < 80:
                    overall_health = 'warning'
            
            # Get choices from model if they exist, otherwise use defaults
            service_types = getattr(ExternalServiceConfiguration, 'SERVICE_TYPES', [
                ('gold_price', 'Gold Price API'),
                ('payment', 'Payment Gateway'),
                ('sms', 'SMS Service'),
                ('email', 'Email Service'),
            ])
            
            authentication_types = getattr(ExternalServiceConfiguration, 'AUTHENTICATION_TYPES', [
                ('api_key', 'API Key'),
                ('basic_auth', 'Basic Authentication'),
                ('oauth2', 'OAuth 2.0'),
                ('none', 'No Authentication'),
            ])
            
            rate_limit_types = getattr(APIRateLimitConfiguration, 'LIMIT_TYPES', [
                ('per_user', 'Per User'),
                ('per_ip', 'Per IP Address'),
                ('global', 'Global'),
                ('per_endpoint', 'Per Endpoint'),
            ])
            
            context.update({
                'services': services,
                'rate_limits': rate_limits,
                'health_statuses': health_statuses,
                'rate_limit_stats': rate_limit_stats,
                'overall_health': overall_health,
                'total_services': total_services,
                'healthy_services': healthy_services,
                'service_types': service_types,
                'authentication_types': authentication_types,
                'rate_limit_types': rate_limit_types,
            })
            
        except Exception as e:
            logger.error(f"Error loading integration settings context: {e}")
            # Provide default context in case of errors
            context.update({
                'services': [],
                'rate_limits': [],
                'health_statuses': [],
                'rate_limit_stats': {},
                'overall_health': 'healthy',
                'total_services': 0,
                'healthy_services': 0,
                'service_types': [('gold_price', 'Gold Price API')],
                'authentication_types': [('api_key', 'API Key')],
                'rate_limit_types': [('per_user', 'Per User'), ('per_service', 'Per Service')],
            })


class ServiceConfigurationView(SuperAdminRequiredMixin, View):
    """
    Handle service configuration CRUD operations.
    """
    
    def post(self, request):
        """Create or update service configuration."""
        try:
            action = request.POST.get('action')
            
            if action == 'create':
                return self._create_service(request)
            elif action == 'update':
                return self._update_service(request)
            elif action == 'delete':
                return self._delete_service(request)
            elif action == 'test_connection':
                return self._test_connection(request)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid action'
                })
                
        except Exception as e:
            logger.error(f"Service configuration error: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    def _create_service(self, request):
        """Create a new service configuration."""
        try:
            # Extract form data
            name = request.POST.get('name')
            service_type = request.POST.get('service_type')
            base_url = request.POST.get('base_url')
            authentication_type = request.POST.get('authentication_type', 'api_key')
            
            # Validate required fields
            if not all([name, service_type, base_url]):
                return JsonResponse({
                    'success': False,
                    'error': 'Name, service type, and base URL are required'
                })
            
            # Create the service directly using Django ORM
            service = ExternalServiceConfiguration.objects.create(
                name=name,
                service_type=service_type,
                base_url=base_url,
                authentication_type=authentication_type,
                description=request.POST.get('description', ''),
                timeout_seconds=int(request.POST.get('timeout_seconds', 30)),
                max_retries=int(request.POST.get('max_retries', 3)),
                rate_limit_requests=int(request.POST.get('rate_limit_requests', 100)),
                rate_limit_window_seconds=int(request.POST.get('rate_limit_window_seconds', 3600)),
                health_check_interval_minutes=int(request.POST.get('health_check_interval_minutes', 15)),
                api_key=request.POST.get('api_key', '') if authentication_type == 'api_key' else '',
                username=request.POST.get('auth_username', '') if authentication_type == 'basic_auth' else '',
                password=request.POST.get('auth_password', '') if authentication_type == 'basic_auth' else '',
                oauth_client_id=request.POST.get('oauth_client_id', '') if authentication_type == 'oauth2' else '',
                oauth_client_secret=request.POST.get('oauth_client_secret', '') if authentication_type == 'oauth2' else '',
                status='active',
                is_enabled=True,
                created_by_id=request.user.id,
                created_by_username=request.user.username,
            )
            
            messages.success(request, f'Service configuration "{name}" created successfully.')
            
            return JsonResponse({
                'success': True,
                'service_id': str(service.service_id),
                'message': 'Service configuration created successfully'
            })
            
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        except Exception as e:
            logger.error(f"Failed to create service configuration: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to create service configuration'
            })
    
    def _update_service(self, request):
        """Update an existing service configuration."""
        try:
            service_id = request.POST.get('service_id')
            if not service_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Service ID is required'
                })
            
            # Prepare updates
            updates = {}
            
            # Basic fields
            for field in ['name', 'description', 'base_url', 'authentication_type']:
                value = request.POST.get(field)
                if value is not None:
                    updates[field] = value
            
            # Numeric fields
            for field in ['timeout_seconds', 'max_retries', 'rate_limit_requests', 
                         'rate_limit_window_seconds', 'health_check_interval_minutes']:
                value = request.POST.get(field)
                if value is not None:
                    try:
                        updates[field] = int(value)
                    except ValueError:
                        pass
            
            # Boolean fields
            for field in ['is_enabled']:
                value = request.POST.get(field)
                if value is not None:
                    updates[field] = value.lower() in ['true', '1', 'on']
            
            # Authentication fields
            auth_type = request.POST.get('authentication_type')
            if auth_type == 'api_key':
                api_key = request.POST.get('api_key')
                if api_key:
                    updates['api_key'] = api_key
            elif auth_type == 'basic_auth':
                username = request.POST.get('auth_username')
                password = request.POST.get('auth_password')
                if username:
                    updates['username'] = username
                if password:
                    updates['password'] = password
            elif auth_type == 'oauth2':
                client_id = request.POST.get('oauth_client_id')
                client_secret = request.POST.get('oauth_client_secret')
                if client_id:
                    updates['oauth_client_id'] = client_id
                if client_secret:
                    updates['oauth_client_secret'] = client_secret
            
            # JSON fields
            custom_headers_json = request.POST.get('custom_headers')
            if custom_headers_json:
                try:
                    updates['custom_headers'] = json.loads(custom_headers_json)
                except json.JSONDecodeError:
                    pass
            
            configuration_json = request.POST.get('configuration')
            if configuration_json:
                try:
                    updates['configuration'] = json.loads(configuration_json)
                except json.JSONDecodeError:
                    pass
            
            # Update the service
            service = integration_manager.update_service_configuration(
                service_id=service_id,
                user_id=request.user.id,
                user_username=request.user.username,
                **updates
            )
            
            messages.success(request, f'Service configuration "{service.name}" updated successfully.')
            
            return JsonResponse({
                'success': True,
                'message': 'Service configuration updated successfully'
            })
            
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        except Exception as e:
            logger.error(f"Failed to update service configuration: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to update service configuration'
            })
    
    def _delete_service(self, request):
        """Delete a service configuration."""
        try:
            service_id = request.POST.get('service_id')
            if not service_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Service ID is required'
                })
            
            service = get_object_or_404(ExternalServiceConfiguration, service_id=service_id)
            service_name = service.name
            service.delete()
            
            messages.success(request, f'Service configuration "{service_name}" deleted successfully.')
            
            return JsonResponse({
                'success': True,
                'message': 'Service configuration deleted successfully'
            })
            
        except Exception as e:
            logger.error(f"Failed to delete service configuration: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to delete service configuration'
            })
    
    def _test_connection(self, request):
        """Test connection to a service."""
        try:
            service_id = request.POST.get('service_id')
            if not service_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Service ID is required'
                })
            
            # Get the service
            service = get_object_or_404(ExternalServiceConfiguration, service_id=service_id)
            
            # Perform a simple connection test
            import requests
            import time
            
            start_time = time.time()
            try:
                # Prepare headers
                headers = {'User-Agent': 'Zargar-Integration-Test/1.0'}
                
                # Add authentication
                if service.authentication_type == 'api_key' and service.api_key:
                    headers['Authorization'] = f'Bearer {service.api_key}'
                elif service.authentication_type == 'basic_auth' and service.username:
                    auth = (service.username, service.password)
                else:
                    auth = None
                
                # Make test request
                response = requests.get(
                    service.base_url,
                    headers=headers,
                    auth=auth,
                    timeout=service.timeout_seconds,
                    verify=True
                )
                
                response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                # Update service statistics
                service.update_statistics(success=True, response_time_ms=response_time)
                service.mark_healthy()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Connection successful! Response time: {response_time:.0f}ms',
                    'response_time_ms': response_time,
                    'status_code': response.status_code
                })
                
            except requests.exceptions.Timeout:
                service.update_statistics(success=False)
                service.record_error('Connection timeout')
                return JsonResponse({
                    'success': False,
                    'message': 'Connection timeout - service did not respond within the specified time limit'
                })
                
            except requests.exceptions.ConnectionError:
                service.update_statistics(success=False)
                service.record_error('Connection failed')
                return JsonResponse({
                    'success': False,
                    'message': 'Connection failed - unable to reach the service'
                })
                
            except requests.exceptions.RequestException as e:
                service.update_statistics(success=False)
                service.record_error(str(e))
                return JsonResponse({
                    'success': False,
                    'message': f'Request failed: {str(e)}'
                })
            
        except Exception as e:
            logger.error(f"Failed to test service connection: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to test service connection'
            })


class RateLimitConfigurationView(SuperAdminRequiredMixin, View):
    """
    Handle rate limit configuration CRUD operations.
    """
    
    def post(self, request):
        """Create or update rate limit configuration."""
        try:
            action = request.POST.get('action')
            
            if action == 'create':
                return self._create_rate_limit(request)
            elif action == 'update':
                return self._update_rate_limit(request)
            elif action == 'delete':
                return self._delete_rate_limit(request)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid action'
                })
                
        except Exception as e:
            logger.error(f"Rate limit configuration error: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    def _create_rate_limit(self, request):
        """Create a new rate limit configuration."""
        try:
            # Extract form data
            name = request.POST.get('name')
            limit_type = request.POST.get('limit_type')
            requests_limit = int(request.POST.get('requests_limit', 100))
            time_window_seconds = int(request.POST.get('time_window_seconds', 3600))
            
            # Validate required fields
            if not all([name, limit_type]):
                return JsonResponse({
                    'success': False,
                    'error': 'Name and limit type are required'
                })
            
            # Create the rate limit configuration directly using Django ORM
            config = APIRateLimitConfiguration.objects.create(
                name=name,
                limit_type=limit_type,
                requests_limit=requests_limit,
                time_window_seconds=time_window_seconds,
                description=request.POST.get('description', ''),
                endpoint_pattern=request.POST.get('endpoint_pattern', ''),
                block_duration_seconds=int(request.POST.get('block_duration_seconds', 3600)),
                warning_threshold_percentage=int(request.POST.get('warning_threshold_percentage', 80)),
                custom_error_message=request.POST.get('custom_error_message', ''),
                is_active=True,
                created_by_id=request.user.id,
                created_by_username=request.user.username,
            )
            
            messages.success(request, f'Rate limit configuration "{name}" created successfully.')
            
            return JsonResponse({
                'success': True,
                'config_id': str(config.config_id),
                'message': 'Rate limit configuration created successfully'
            })
            
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        except Exception as e:
            logger.error(f"Failed to create rate limit configuration: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to create rate limit configuration'
            })
    
    def _update_rate_limit(self, request):
        """Update an existing rate limit configuration."""
        try:
            config_id = request.POST.get('config_id')
            if not config_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Configuration ID is required'
                })
            
            # Prepare updates
            updates = {}
            
            # Basic fields
            for field in ['name', 'description', 'endpoint_pattern', 'custom_error_message']:
                value = request.POST.get(field)
                if value is not None:
                    updates[field] = value
            
            # Numeric fields
            for field in ['requests_limit', 'time_window_seconds', 'block_duration_seconds', 
                         'warning_threshold_percentage']:
                value = request.POST.get(field)
                if value is not None:
                    try:
                        updates[field] = int(value)
                    except ValueError:
                        pass
            
            # Boolean fields
            for field in ['is_active']:
                value = request.POST.get(field)
                if value is not None:
                    updates[field] = value.lower() in ['true', '1', 'on']
            
            # JSON fields
            for json_field in ['custom_headers', 'exempt_user_ids', 'exempt_ip_addresses']:
                json_value = request.POST.get(json_field)
                if json_value is not None:
                    try:
                        updates[json_field] = json.loads(json_value)
                    except json.JSONDecodeError:
                        pass
            
            # Update the configuration
            config = rate_limit_manager.update_rate_limit_config(
                config_id=config_id,
                user_id=request.user.id,
                user_username=request.user.username,
                **updates
            )
            
            # Validate the updated configuration
            issues = rate_limit_manager.validate_rate_limit_config(config)
            if issues:
                return JsonResponse({
                    'success': False,
                    'error': 'Configuration validation failed',
                    'issues': issues
                })
            
            messages.success(request, f'Rate limit configuration "{config.name}" updated successfully.')
            
            return JsonResponse({
                'success': True,
                'message': 'Rate limit configuration updated successfully'
            })
            
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        except Exception as e:
            logger.error(f"Failed to update rate limit configuration: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to update rate limit configuration'
            })
    
    def _delete_rate_limit(self, request):
        """Delete a rate limit configuration."""
        try:
            config_id = request.POST.get('config_id')
            if not config_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Configuration ID is required'
                })
            
            config = get_object_or_404(APIRateLimitConfiguration, config_id=config_id)
            config_name = config.name
            config.delete()
            
            messages.success(request, f'Rate limit configuration "{config_name}" deleted successfully.')
            
            return JsonResponse({
                'success': True,
                'message': 'Rate limit configuration deleted successfully'
            })
            
        except Exception as e:
            logger.error(f"Failed to delete rate limit configuration: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to delete rate limit configuration'
            })


class IntegrationHealthView(SuperAdminRequiredMixin, View):
    """
    Handle integration health monitoring operations.
    """
    
    def get(self, request):
        """Get health status for services."""
        try:
            service_id = request.GET.get('service_id')
            
            if service_id:
                # Get health status for specific service
                health_status = integration_manager.get_service_health_status(service_id)
                return JsonResponse(health_status)
            else:
                # Get health status for all services
                health_statuses = integration_manager.get_all_services_health()
                return JsonResponse({
                    'services': health_statuses
                })
                
        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to get health status'
            })
    
    def post(self, request):
        """Perform health check operations."""
        try:
            action = request.POST.get('action')
            
            if action == 'health_check':
                return self._perform_health_check(request)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid action'
                })
                
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    def _perform_health_check(self, request):
        """Perform a health check on a service."""
        try:
            service_id = request.POST.get('service_id')
            check_type = request.POST.get('check_type', 'connectivity')
            
            if not service_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Service ID is required'
                })
            
            # Perform the health check
            health_check = integration_manager.perform_health_check(service_id, check_type)
            
            return JsonResponse({
                'success': True,
                'health_check': {
                    'check_id': str(health_check.check_id),
                    'check_type': health_check.check_type,
                    'status': health_check.status,
                    'success': health_check.success,
                    'response_time_ms': health_check.response_time_ms,
                    'checked_at': health_check.checked_at.isoformat(),
                    'error_message': health_check.error_message,
                    'warnings': health_check.warnings,
                    'details': health_check.details
                }
            })
            
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        except Exception as e:
            logger.error(f"Failed to perform health check: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to perform health check'
            })


class IntegrationHealthHistoryView(SuperAdminRequiredMixin, TemplateView):
    """
    View for displaying integration health check history.
    """
    template_name = 'admin_panel/settings/integration_health_history.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        service_id = self.request.GET.get('service_id')
        check_type = self.request.GET.get('check_type', '')
        
        # Get health checks
        health_checks = IntegrationHealthCheck.objects.all().order_by('-checked_at')
        
        if service_id:
            try:
                service = ExternalServiceConfiguration.objects.get(service_id=service_id)
                health_checks = health_checks.filter(service=service)
                context['selected_service'] = service
            except ExternalServiceConfiguration.DoesNotExist:
                pass
        
        if check_type:
            health_checks = health_checks.filter(check_type=check_type)
            context['selected_check_type'] = check_type
        
        # Paginate results
        paginator = Paginator(health_checks, 50)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Get all services for filter dropdown
        services = ExternalServiceConfiguration.objects.all().order_by('name')
        
        context.update({
            'health_checks': page_obj,
            'services': services,
            'check_types': IntegrationHealthCheck.CHECK_TYPES,
            'status_choices': IntegrationHealthCheck.STATUS_CHOICES,
        })
        
        return context