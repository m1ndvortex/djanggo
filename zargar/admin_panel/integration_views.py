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
from .services.integration_service import integration_manager, rate_limit_manager
from .views import SuperAdminRequiredMixin

logger = logging.getLogger(__name__)


class IntegrationSettingsView(SuperAdminRequiredMixin, TemplateView):
    """
    Main integration settings interface.
    """
    template_name = 'admin_panel/settings/integration_settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all external service configurations
        services = ExternalServiceConfiguration.objects.all().order_by('name')
        
        # Get rate limit configurations
        rate_limits = APIRateLimitConfiguration.objects.all().order_by('name')
        
        # Get health status for all services
        health_statuses = integration_manager.get_all_services_health()
        
        # Get rate limit statistics
        rate_limit_stats = rate_limit_manager.get_rate_limit_statistics()
        
        # Calculate overall integration health
        total_services = len(health_statuses)
        healthy_services = sum(1 for status in health_statuses if status.get('overall_status') == 'healthy')
        
        overall_health = 'healthy'
        if total_services > 0:
            health_percentage = (healthy_services / total_services) * 100
            if health_percentage < 50:
                overall_health = 'critical'
            elif health_percentage < 80:
                overall_health = 'warning'
        
        context.update({
            'services': services,
            'rate_limits': rate_limits,
            'health_statuses': health_statuses,
            'rate_limit_stats': rate_limit_stats,
            'overall_health': overall_health,
            'total_services': total_services,
            'healthy_services': healthy_services,
            'service_types': ExternalServiceConfiguration.SERVICE_TYPES,
            'authentication_types': ExternalServiceConfiguration.AUTHENTICATION_TYPES,
            'rate_limit_types': APIRateLimitConfiguration.LIMIT_TYPES,
            'time_windows': APIRateLimitConfiguration.TIME_WINDOWS,
        })
        
        return context


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
            
            # Prepare additional fields
            kwargs = {
                'description': request.POST.get('description', ''),
                'timeout_seconds': int(request.POST.get('timeout_seconds', 30)),
                'max_retries': int(request.POST.get('max_retries', 3)),
                'rate_limit_requests': int(request.POST.get('rate_limit_requests', 100)),
                'rate_limit_window_seconds': int(request.POST.get('rate_limit_window_seconds', 3600)),
                'health_check_interval_minutes': int(request.POST.get('health_check_interval_minutes', 15)),
                'created_by_id': request.user.id,
                'created_by_username': request.user.username,
            }
            
            # Add authentication fields based on type
            if authentication_type == 'api_key':
                kwargs['api_key'] = request.POST.get('api_key', '')
            elif authentication_type == 'basic_auth':
                kwargs['username'] = request.POST.get('auth_username', '')
                kwargs['password'] = request.POST.get('auth_password', '')
            elif authentication_type == 'oauth2':
                kwargs['oauth_client_id'] = request.POST.get('oauth_client_id', '')
                kwargs['oauth_client_secret'] = request.POST.get('oauth_client_secret', '')
            
            # Parse custom headers
            custom_headers_json = request.POST.get('custom_headers', '{}')
            try:
                kwargs['custom_headers'] = json.loads(custom_headers_json)
            except json.JSONDecodeError:
                kwargs['custom_headers'] = {}
            
            # Parse configuration
            configuration_json = request.POST.get('configuration', '{}')
            try:
                kwargs['configuration'] = json.loads(configuration_json)
            except json.JSONDecodeError:
                kwargs['configuration'] = {}
            
            # Create the service
            service = integration_manager.create_service_configuration(
                name=name,
                service_type=service_type,
                base_url=base_url,
                authentication_type=authentication_type,
                **kwargs
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
            
            # Test the connection
            result = integration_manager.test_service_connection(service_id)
            
            return JsonResponse(result)
            
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
            
            # Prepare additional fields
            kwargs = {
                'description': request.POST.get('description', ''),
                'endpoint_pattern': request.POST.get('endpoint_pattern', ''),
                'block_duration_seconds': int(request.POST.get('block_duration_seconds', 3600)),
                'warning_threshold_percentage': int(request.POST.get('warning_threshold_percentage', 80)),
                'custom_error_message': request.POST.get('custom_error_message', ''),
                'created_by_id': request.user.id,
                'created_by_username': request.user.username,
            }
            
            # Parse JSON fields
            for json_field in ['custom_headers', 'exempt_user_ids', 'exempt_ip_addresses']:
                json_value = request.POST.get(json_field, '[]' if 'ids' in json_field or 'addresses' in json_field else '{}')
                try:
                    kwargs[json_field] = json.loads(json_value)
                except json.JSONDecodeError:
                    kwargs[json_field] = [] if 'ids' in json_field or 'addresses' in json_field else {}
            
            # Create the rate limit configuration
            config = rate_limit_manager.create_rate_limit_config(
                name=name,
                limit_type=limit_type,
                requests_limit=requests_limit,
                time_window_seconds=time_window_seconds,
                **kwargs
            )
            
            # Validate the configuration
            issues = rate_limit_manager.validate_rate_limit_config(config)
            if issues:
                config.delete()
                return JsonResponse({
                    'success': False,
                    'error': 'Configuration validation failed',
                    'issues': issues
                })
            
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