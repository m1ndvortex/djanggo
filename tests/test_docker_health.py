"""
Unit tests for Docker container health and service connectivity.
Tests Requirements: 1.6, 1.7, 1.8
"""
import pytest
import redis
import psycopg2
from django.test import TestCase, override_settings
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from celery import current_app
from unittest.mock import patch, MagicMock


class DockerHealthTestCase(TestCase):
    """Test Docker container health and service connectivity."""

    def test_database_connection_health(self):
        """Test PostgreSQL database connection is healthy."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                self.assertEqual(result[0], 1)
        except Exception as e:
            self.fail(f"Database connection failed: {e}")

    def test_database_tenant_support(self):
        """Test that database supports django-tenants functionality."""
        try:
            with connection.cursor() as cursor:
                # Test schema creation capability
                cursor.execute("CREATE SCHEMA IF NOT EXISTS test_tenant_schema")
                cursor.execute("DROP SCHEMA IF EXISTS test_tenant_schema CASCADE")
        except Exception as e:
            self.fail(f"Database tenant schema support failed: {e}")

    def test_redis_connection_health(self):
        """Test Redis connection is healthy."""
        try:
            # Test cache connection
            cache.set('health_check', 'ok', 30)
            result = cache.get('health_check')
            self.assertEqual(result, 'ok')
            cache.delete('health_check')
        except Exception as e:
            self.fail(f"Redis connection failed: {e}")

    def test_redis_direct_connection(self):
        """Test direct Redis connection for Celery broker."""
        try:
            redis_client = redis.from_url(settings.CELERY_BROKER_URL)
            redis_client.ping()
            
            # Test basic operations
            redis_client.set('test_key', 'test_value', ex=30)
            result = redis_client.get('test_key')
            self.assertEqual(result.decode('utf-8'), 'test_value')
            redis_client.delete('test_key')
        except Exception as e:
            self.fail(f"Direct Redis connection failed: {e}")

    @patch('celery.current_app.control.inspect')
    def test_celery_worker_connectivity(self, mock_inspect):
        """Test Celery worker connectivity."""
        # Mock Celery inspect for testing
        mock_inspector = MagicMock()
        mock_inspector.ping.return_value = {'worker1@hostname': 'pong'}
        mock_inspect.return_value = mock_inspector
        
        try:
            # Test Celery configuration
            self.assertIsNotNone(current_app.conf.broker_url)
            self.assertIsNotNone(current_app.conf.result_backend)
            
            # Test broker connection
            broker_connection = current_app.connection()
            broker_connection.ensure_connection(max_retries=3)
            broker_connection.release()
            
        except Exception as e:
            self.fail(f"Celery connectivity test failed: {e}")

    def test_celery_task_execution(self):
        """Test Celery task execution capability."""
        from zargar.celery import debug_task
        
        try:
            # In test environment, tasks run synchronously
            result = debug_task.delay()
            self.assertIsNotNone(result)
        except Exception as e:
            self.fail(f"Celery task execution failed: {e}")

    def test_environment_variables_loaded(self):
        """Test that required environment variables are loaded."""
        # Database configuration
        self.assertIsNotNone(settings.DATABASES['default']['NAME'])
        self.assertIsNotNone(settings.DATABASES['default']['USER'])
        self.assertIsNotNone(settings.DATABASES['default']['HOST'])
        
        # Redis configuration
        self.assertIsNotNone(settings.CELERY_BROKER_URL)
        self.assertIsNotNone(settings.CELERY_RESULT_BACKEND)
        
        # Storage configuration (should be loaded even if empty in test)
        self.assertTrue(hasattr(settings, 'CLOUDFLARE_R2_ACCESS_KEY'))
        self.assertTrue(hasattr(settings, 'BACKBLAZE_B2_ACCESS_KEY'))

    def test_django_tenants_configuration(self):
        """Test django-tenants configuration is correct."""
        # Check tenant models are configured
        self.assertEqual(settings.TENANT_MODEL, "tenants.Tenant")
        self.assertEqual(settings.TENANT_DOMAIN_MODEL, "tenants.Domain")
        
        # Check database router is configured
        self.assertIn('django_tenants.routers.TenantSyncRouter', settings.DATABASE_ROUTERS)
        
        # Check middleware is configured
        self.assertIn('django_tenants.middleware.main.TenantMainMiddleware', settings.MIDDLEWARE)

    def test_storage_configuration(self):
        """Test storage backends configuration."""
        # Test that storage settings are properly configured
        storage_settings = [
            'CLOUDFLARE_R2_ACCESS_KEY',
            'CLOUDFLARE_R2_SECRET_KEY', 
            'CLOUDFLARE_R2_BUCKET',
            'CLOUDFLARE_R2_ENDPOINT',
            'BACKBLAZE_B2_ACCESS_KEY',
            'BACKBLAZE_B2_SECRET_KEY',
            'BACKBLAZE_B2_BUCKET',
        ]
        
        for setting in storage_settings:
            self.assertTrue(hasattr(settings, setting), f"Missing storage setting: {setting}")

    def test_drf_configuration(self):
        """Test Django REST Framework configuration."""
        # Check DRF is properly configured
        self.assertIn('rest_framework', settings.INSTALLED_APPS)
        self.assertIn('rest_framework_simplejwt', settings.INSTALLED_APPS)
        
        # Check authentication classes
        auth_classes = settings.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']
        self.assertIn('rest_framework_simplejwt.authentication.JWTAuthentication', auth_classes)
        self.assertIn('rest_framework.authentication.SessionAuthentication', auth_classes)

    def test_persian_localization_configuration(self):
        """Test Persian localization is properly configured."""
        # Check language settings
        self.assertEqual(settings.LANGUAGE_CODE, 'fa')
        self.assertEqual(settings.TIME_ZONE, 'Asia/Tehran')
        self.assertTrue(settings.USE_I18N)
        self.assertTrue(settings.USE_L10N)
        self.assertTrue(settings.USE_TZ)
        
        # Check Persian is in available languages
        language_codes = [lang[0] for lang in settings.LANGUAGES]
        self.assertIn('fa', language_codes)


@pytest.mark.integration
class ServiceIntegrationTestCase(TestCase):
    """Integration tests for service connectivity."""

    def test_database_redis_integration(self):
        """Test database and Redis work together."""
        try:
            # Test database operation
            with connection.cursor() as cursor:
                cursor.execute("SELECT NOW()")
                db_time = cursor.fetchone()[0]
            
            # Test cache operation
            cache.set('db_time', str(db_time), 60)
            cached_time = cache.get('db_time')
            
            self.assertIsNotNone(cached_time)
            self.assertEqual(cached_time, str(db_time))
            
        except Exception as e:
            self.fail(f"Database-Redis integration failed: {e}")

    def test_celery_database_integration(self):
        """Test Celery can access database."""
        from zargar.celery import debug_task
        
        try:
            # Test that Celery task can access database
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                self.assertEqual(result[0], 1)
                
            # Test task execution
            task_result = debug_task.delay()
            self.assertIsNotNone(task_result)
            
        except Exception as e:
            self.fail(f"Celery-Database integration failed: {e}")

    def test_all_services_health_check(self):
        """Comprehensive health check for all services."""
        health_status = {}
        
        # Database health
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                health_status['database'] = 'healthy'
        except Exception as e:
            health_status['database'] = f'unhealthy: {e}'
        
        # Redis health
        try:
            cache.set('health_test', 'ok', 10)
            cache.get('health_test')
            health_status['redis'] = 'healthy'
        except Exception as e:
            health_status['redis'] = f'unhealthy: {e}'
        
        # Celery health
        try:
            broker_connection = current_app.connection()
            broker_connection.ensure_connection(max_retries=1)
            broker_connection.release()
            health_status['celery'] = 'healthy'
        except Exception as e:
            health_status['celery'] = f'unhealthy: {e}'
        
        # Assert all services are healthy
        for service, status in health_status.items():
            self.assertEqual(status, 'healthy', f"Service {service} is not healthy: {status}")


@pytest.mark.unit
def test_docker_environment_variables():
    """Test that Docker environment variables are properly set."""
    import os
    
    # Test database URL is set
    database_url = os.getenv('DATABASE_URL')
    assert database_url is not None, "DATABASE_URL environment variable not set"
    assert 'postgresql://' in database_url, "DATABASE_URL should be PostgreSQL URL"
    
    # Test Redis URL is set
    redis_url = os.getenv('REDIS_URL')
    assert redis_url is not None, "REDIS_URL environment variable not set"
    assert 'redis://' in redis_url, "REDIS_URL should be Redis URL"
    
    # Test Celery broker URL is set
    celery_broker = os.getenv('CELERY_BROKER_URL')
    assert celery_broker is not None, "CELERY_BROKER_URL environment variable not set"


@pytest.mark.unit
def test_storage_credentials_available():
    """Test that storage credentials are available in environment."""
    import os
    
    # Cloudflare R2 credentials
    cloudflare_keys = [
        'CLOUDFLARE_R2_ACCESS_KEY',
        'CLOUDFLARE_R2_SECRET_KEY',
        'CLOUDFLARE_R2_BUCKET',
        'CLOUDFLARE_R2_ENDPOINT',
        'CLOUDFLARE_R2_ACCOUNT_ID'
    ]
    
    for key in cloudflare_keys:
        value = os.getenv(key)
        assert value is not None, f"{key} environment variable not set"
    
    # Backblaze B2 credentials
    backblaze_keys = [
        'BACKBLAZE_B2_ACCESS_KEY',
        'BACKBLAZE_B2_SECRET_KEY',
        'BACKBLAZE_B2_BUCKET'
    ]
    
    for key in backblaze_keys:
        value = os.getenv(key)
        assert value is not None, f"{key} environment variable not set"


@pytest.mark.integration
class NginxIntegrationTestCase(TestCase):
    """Integration tests for Nginx reverse proxy."""

    def test_nginx_configuration_exists(self):
        """Test that Nginx configuration file exists and is valid."""
        import os
        nginx_config_path = os.path.join(os.getcwd(), 'nginx.conf')
        self.assertTrue(os.path.exists(nginx_config_path), "nginx.conf file not found")
        
        # Read and validate basic nginx config structure
        with open(nginx_config_path, 'r') as f:
            config_content = f.read()
            
        # Check for essential nginx directives
        self.assertIn('upstream web', config_content)
        self.assertIn('server web:8000', config_content)
        self.assertIn('location /health/', config_content)
        self.assertIn('location /static/', config_content)
        self.assertIn('location /media/', config_content)
        self.assertIn('proxy_pass http://web', config_content)

    def test_nginx_security_headers(self):
        """Test that Nginx configuration includes security headers."""
        import os
        nginx_config_path = os.path.join(os.getcwd(), 'nginx.conf')
        
        with open(nginx_config_path, 'r') as f:
            config_content = f.read()
            
        # Check for security headers
        security_headers = [
            'X-Frame-Options DENY',
            'X-Content-Type-Options nosniff',
            'X-XSS-Protection',
            'Strict-Transport-Security'
        ]
        
        for header in security_headers:
            self.assertIn(header, config_content, f"Security header '{header}' not found in nginx.conf")

    def test_nginx_gzip_configuration(self):
        """Test that Nginx has gzip compression configured."""
        import os
        nginx_config_path = os.path.join(os.getcwd(), 'nginx.conf')
        
        with open(nginx_config_path, 'r') as f:
            config_content = f.read()
            
        # Check for gzip configuration
        gzip_directives = [
            'gzip on',
            'gzip_vary on',
            'gzip_min_length',
            'gzip_types'
        ]
        
        for directive in gzip_directives:
            self.assertIn(directive, config_content, f"Gzip directive '{directive}' not found in nginx.conf")

    def test_nginx_client_max_body_size(self):
        """Test that Nginx has appropriate client_max_body_size for file uploads."""
        import os
        nginx_config_path = os.path.join(os.getcwd(), 'nginx.conf')
        
        with open(nginx_config_path, 'r') as f:
            config_content = f.read()
            
        self.assertIn('client_max_body_size', config_content)
        # Should allow at least 100MB for jewelry images and documents
        self.assertIn('100M', config_content)

    def test_docker_compose_nginx_service(self):
        """Test that docker-compose.yml has properly configured Nginx service."""
        import os
        import yaml
        
        compose_path = os.path.join(os.getcwd(), 'docker-compose.yml')
        self.assertTrue(os.path.exists(compose_path), "docker-compose.yml file not found")
        
        with open(compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)
            
        # Check nginx service exists
        self.assertIn('nginx', compose_config['services'])
        nginx_service = compose_config['services']['nginx']
        
        # Check nginx configuration
        self.assertEqual(nginx_service['image'], 'nginx:alpine')
        self.assertIn('80:80', nginx_service['ports'])
        self.assertIn('443:443', nginx_service['ports'])
        
        # Check volumes are mounted
        volumes = nginx_service['volumes']
        nginx_conf_mounted = any('./nginx.conf:/etc/nginx/nginx.conf' in vol for vol in volumes)
        static_files_mounted = any('./staticfiles:/app/staticfiles' in vol for vol in volumes)
        
        self.assertTrue(nginx_conf_mounted, "nginx.conf not mounted in nginx service")
        self.assertTrue(static_files_mounted, "staticfiles not mounted in nginx service")
        
        # Check depends_on web service
        self.assertIn('web', nginx_service['depends_on'])

    def test_nginx_health_check_configuration(self):
        """Test that Nginx service has health check configured."""
        import os
        import yaml
        
        compose_path = os.path.join(os.getcwd(), 'docker-compose.yml')
        
        with open(compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)
            
        nginx_service = compose_config['services']['nginx']
        
        # Check health check is configured
        self.assertIn('healthcheck', nginx_service)
        healthcheck = nginx_service['healthcheck']
        
        # Verify health check configuration
        self.assertIn('test', healthcheck)
        self.assertIn('interval', healthcheck)
        self.assertIn('timeout', healthcheck)
        self.assertIn('retries', healthcheck)