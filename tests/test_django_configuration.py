"""
Tests for Django configuration and service integration.
"""
import pytest
from django.test import TestCase, override_settings
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.db import connection
from django.template.loader import render_to_string
from django.test.client import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from zargar.core.middleware import TenantContextMiddleware, PersianLocalizationMiddleware
from zargar.core.context_processors import tenant_context, persian_context, theme_context
from zargar.tenants.models import Tenant, Domain
import json
import jdatetime

User = get_user_model()


class DjangoConfigurationTest(TestCase):
    """
    Test Django configuration and basic settings.
    """
    
    def test_installed_apps_configuration(self):
        """Test that all required apps are installed."""
        required_apps = [
            'django_tenants',
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'rest_framework',
            'rest_framework_simplejwt',
            'corsheaders',
            'django_otp',
            'storages',
            'compressor',
            'sass_processor',
            'health_check',
            'django_jalali',
            'zargar.core',
            'zargar.tenants',
            'zargar.api',
        ]
        
        for app in required_apps:
            self.assertIn(app, settings.INSTALLED_APPS, f"App {app} not found in INSTALLED_APPS")
    
    def test_middleware_configuration(self):
        """Test that all required middleware are configured."""
        required_middleware = [
            'zargar.core.middleware.HealthCheckMiddleware',
            'django_tenants.middleware.main.TenantMainMiddleware',
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'corsheaders.middleware.CorsMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django_otp.middleware.OTPMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
            'django.middleware.locale.LocaleMiddleware',
            'zargar.core.middleware.TenantContextMiddleware',
            'zargar.core.middleware.PersianLocalizationMiddleware',
        ]
        
        for middleware in required_middleware:
            self.assertIn(middleware, settings.MIDDLEWARE, f"Middleware {middleware} not found in MIDDLEWARE")
    
    def test_database_configuration(self):
        """Test database configuration."""
        self.assertEqual(settings.DATABASES['default']['ENGINE'], 'django_tenants.postgresql_backend')
        self.assertIn('django_tenants.routers.TenantSyncRouter', settings.DATABASE_ROUTERS)
    
    def test_cache_configuration(self):
        """Test Redis cache configuration."""
        self.assertEqual(settings.CACHES['default']['BACKEND'], 'django_redis.cache.RedisCache')
        self.assertIn('redis://', settings.CACHES['default']['LOCATION'])
    
    def test_internationalization_configuration(self):
        """Test Persian localization configuration."""
        self.assertEqual(settings.LANGUAGE_CODE, 'fa')
        self.assertEqual(settings.TIME_ZONE, 'Asia/Tehran')
        self.assertTrue(settings.USE_I18N)
        self.assertTrue(settings.USE_L10N)
        self.assertTrue(settings.USE_TZ)
        self.assertIn(('fa', 'Persian'), settings.LANGUAGES)
    
    def test_rest_framework_configuration(self):
        """Test DRF configuration."""
        self.assertIn('rest_framework_simplejwt.authentication.JWTAuthentication', 
                     settings.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'])
        self.assertIn('rest_framework.authentication.SessionAuthentication',
                     settings.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'])
        self.assertEqual(settings.REST_FRAMEWORK['PAGE_SIZE'], 20)
    
    def test_tenant_configuration(self):
        """Test django-tenants configuration."""
        self.assertEqual(settings.TENANT_MODEL, "tenants.Tenant")
        self.assertEqual(settings.TENANT_DOMAIN_MODEL, "tenants.Domain")
        self.assertEqual(settings.PUBLIC_SCHEMA_URLCONF, 'zargar.urls_public')
        self.assertEqual(settings.ROOT_URLCONF, 'zargar.urls_tenants')
    
    def test_custom_user_model(self):
        """Test custom user model configuration."""
        self.assertEqual(settings.AUTH_USER_MODEL, 'core.User')
    
    def test_theme_configuration(self):
        """Test theme configuration."""
        self.assertIn('DEFAULT_THEME', settings.THEME_SETTINGS)
        self.assertIn('AVAILABLE_THEMES', settings.THEME_SETTINGS)
        self.assertEqual(settings.THEME_SETTINGS['DEFAULT_THEME'], 'light')
        self.assertIn('light', settings.THEME_SETTINGS['AVAILABLE_THEMES'])
        self.assertIn('dark', settings.THEME_SETTINGS['AVAILABLE_THEMES'])
    
    def test_frontend_settings(self):
        """Test frontend integration settings."""
        self.assertIn('TAILWIND_CSS_VERSION', settings.FRONTEND_SETTINGS)
        self.assertIn('FLOWBITE_VERSION', settings.FRONTEND_SETTINGS)
        self.assertIn('ALPINE_JS_VERSION', settings.FRONTEND_SETTINGS)
        self.assertIn('HTMX_VERSION', settings.FRONTEND_SETTINGS)


class DatabaseIntegrationTest(TestCase):
    """
    Test database integration and connectivity.
    """
    
    def test_database_connection(self):
        """Test database connection."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)
    
    def test_user_model_creation(self):
        """Test custom user model creation."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            persian_first_name='تست',
            persian_last_name='کاربر',
            phone_number='09123456789',
            role='salesperson'
        )
        
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.persian_first_name, 'تست')
        self.assertEqual(user.persian_last_name, 'کاربر')
        self.assertEqual(user.role, 'salesperson')
        self.assertEqual(user.full_persian_name, 'تست کاربر')
        self.assertFalse(user.is_2fa_enabled)
        self.assertEqual(user.theme_preference, 'light')


class CacheIntegrationTest(TestCase):
    """
    Test Redis cache integration.
    """
    
    def test_cache_set_get(self):
        """Test cache set and get operations."""
        cache.set('test_key', 'test_value', 30)
        value = cache.get('test_key')
        self.assertEqual(value, 'test_value')
    
    def test_cache_delete(self):
        """Test cache delete operation."""
        cache.set('test_key_delete', 'test_value', 30)
        cache.delete('test_key_delete')
        value = cache.get('test_key_delete')
        self.assertIsNone(value)
    
    def test_cache_json_data(self):
        """Test caching JSON data."""
        test_data = {
            'name': 'طلای ۱۸ عیار',
            'weight': 5.5,
            'karat': 18,
            'price': 1500000
        }
        
        cache.set('jewelry_item', test_data, 60)
        cached_data = cache.get('jewelry_item')
        self.assertEqual(cached_data, test_data)


class MiddlewareTest(TestCase):
    """
    Test custom middleware functionality.
    """
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_health_check_middleware(self):
        """Test health check middleware."""
        from zargar.core.middleware import HealthCheckMiddleware
        
        def get_response(request):
            return None
        
        middleware = HealthCheckMiddleware(get_response)
        request = self.factory.get('/health/')
        response = middleware(request)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'zargar-jewelry-saas')
    
    def test_tenant_context_middleware(self):
        """Test tenant context middleware."""
        def get_response(request):
            return None
        
        middleware = TenantContextMiddleware(get_response)
        request = self.factory.get('/')
        
        # Mock tenant
        class MockTenant:
            schema_name = 'test_tenant'
            domain_url = 'test.zargar.com'
            name = 'Test Jewelry Shop'
        
        request.tenant = MockTenant()
        middleware(request)
        
        self.assertIsNotNone(request.tenant_context)
        self.assertEqual(request.tenant_context['schema_name'], 'test_tenant')
        self.assertEqual(request.tenant_context['name'], 'Test Jewelry Shop')
    
    def test_persian_localization_middleware(self):
        """Test Persian localization middleware."""
        from django.http import HttpResponse
        
        def get_response(request):
            return HttpResponse('test')
        
        middleware = PersianLocalizationMiddleware(get_response)
        request = self.factory.get('/')
        response = middleware(request)
        
        self.assertEqual(request.LANGUAGE_CODE, 'fa')
        self.assertIsNotNone(request.persian_date)
        self.assertIn('today', request.persian_date)
        self.assertIn('now', request.persian_date)
        self.assertEqual(response['Content-Language'], 'fa')


class ContextProcessorTest(TestCase):
    """
    Test custom context processors.
    """
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_tenant_context_processor(self):
        """Test tenant context processor."""
        request = self.factory.get('/')
        
        # Mock tenant context
        class MockTenant:
            name = 'Test Shop'
        
        request.tenant_context = {
            'tenant': MockTenant(),
            'name': 'Test Shop',
            'domain_url': 'test.zargar.com',
            'schema_name': 'test_tenant'
        }
        
        context = tenant_context(request)
        
        self.assertIn('tenant', context)
        self.assertEqual(context['tenant_name'], 'Test Shop')
        self.assertEqual(context['tenant_domain'], 'test.zargar.com')
    
    def test_persian_context_processor(self):
        """Test Persian context processor."""
        request = self.factory.get('/')
        
        # Mock Persian date
        request.persian_date = {
            'today': jdatetime.date.today(),
            'now': jdatetime.datetime.now(),
            'shamsi_year': 1403,
            'shamsi_month': 6,
            'shamsi_day': 29,
        }
        
        context = persian_context(request)
        
        self.assertIn('persian_date', context)
        self.assertIn('shamsi_today', context)
        self.assertIn('persian_numbers', context)
        self.assertTrue(context['rtl_direction'])
        self.assertEqual(context['language_code'], 'fa')
    
    def test_theme_context_processor(self):
        """Test theme context processor."""
        request = self.factory.get('/')
        request.COOKIES = {'zargar_theme': 'dark'}
        
        context = theme_context(request)
        
        self.assertEqual(context['current_theme'], 'dark')
        self.assertTrue(context['is_dark_mode'])
        self.assertFalse(context['is_light_mode'])
        self.assertIn('cyber-theme', context['theme_classes'])
        self.assertIn('frontend_settings', context)


class TemplateIntegrationTest(TestCase):
    """
    Test template integration and context processors.
    """
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_template_rendering_with_context(self):
        """Test template rendering with custom context processors."""
        # This would require actual template files
        # For now, just test that the context processors work
        request = self.factory.get('/')
        request.COOKIES = {'zargar_theme': 'light'}
        
        # Mock Persian date
        request.persian_date = {
            'today': jdatetime.date.today(),
            'now': jdatetime.datetime.now(),
        }
        
        context = {}
        context.update(persian_context(request))
        context.update(theme_context(request))
        
        self.assertIn('current_theme', context)
        self.assertIn('persian_date', context)
        self.assertIn('frontend_settings', context)


class StaticFilesTest(TestCase):
    """
    Test static files configuration.
    """
    
    def test_static_files_configuration(self):
        """Test static files settings."""
        self.assertEqual(settings.STATIC_URL, '/static/')
        self.assertIn('compressor.finders.CompressorFinder', settings.STATICFILES_FINDERS)
        self.assertIn('sass_processor.finders.CssFinder', settings.STATICFILES_FINDERS)
    
    def test_sass_processor_configuration(self):
        """Test Sass processor configuration."""
        self.assertIn('SASS_PROCESSOR_ROOT', dir(settings))
        self.assertIn('SASS_PROCESSOR_INCLUDE_DIRS', dir(settings))


class SecurityConfigurationTest(TestCase):
    """
    Test security configuration.
    """
    
    def test_password_hashers(self):
        """Test password hashers configuration."""
        # In test environment, MD5 hasher is used for speed
        # In production, Argon2 would be used
        if hasattr(settings, 'TESTING') or 'test' in settings.DATABASES['default']['NAME']:
            self.assertIn('django.contrib.auth.hashers.MD5PasswordHasher', settings.PASSWORD_HASHERS)
        else:
            self.assertIn('django.contrib.auth.hashers.Argon2PasswordHasher', settings.PASSWORD_HASHERS)
    
    def test_security_middleware(self):
        """Test security middleware configuration."""
        self.assertIn('django.middleware.security.SecurityMiddleware', settings.MIDDLEWARE)
        self.assertIn('django.middleware.clickjacking.XFrameOptionsMiddleware', settings.MIDDLEWARE)
    
    def test_session_configuration(self):
        """Test session configuration."""
        self.assertEqual(settings.SESSION_ENGINE, 'django.contrib.sessions.backends.cache')
        self.assertEqual(settings.SESSION_CACHE_ALIAS, 'default')
        self.assertEqual(settings.SESSION_COOKIE_AGE, 3600)


@pytest.mark.django_db
class CeleryIntegrationTest(TestCase):
    """
    Test Celery integration (basic configuration).
    """
    
    def test_celery_configuration(self):
        """Test Celery configuration."""
        self.assertIn('CELERY_BROKER_URL', dir(settings))
        self.assertIn('CELERY_RESULT_BACKEND', dir(settings))
        self.assertIn('redis://', settings.CELERY_BROKER_URL)
        self.assertIn('redis://', settings.CELERY_RESULT_BACKEND)


class HealthCheckTest(TestCase):
    """
    Test health check functionality.
    """
    
    def test_health_check_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'zargar-jewelry-saas')


class PersianNumberTest(TestCase):
    """
    Test Persian number formatting utilities.
    """
    
    def test_persian_number_formatting(self):
        """Test Persian number formatting configuration."""
        self.assertTrue(settings.USE_THOUSAND_SEPARATOR)
        self.assertEqual(settings.THOUSAND_SEPARATOR, '٬')
        self.assertEqual(settings.DECIMAL_SEPARATOR, '٫')
    
    def test_jalali_configuration(self):
        """Test Jalali calendar configuration."""
        self.assertTrue(settings.USE_JALALI)
        self.assertIn('JALALI_DATE_DEFAULTS', dir(settings))


class StorageConfigurationTest(TestCase):
    """
    Test storage configuration.
    """
    
    def test_storage_settings(self):
        """Test storage configuration."""
        self.assertIn('CLOUDFLARE_R2_ACCESS_KEY', dir(settings))
        self.assertIn('CLOUDFLARE_R2_SECRET_KEY', dir(settings))
        self.assertIn('BACKBLAZE_B2_ACCESS_KEY', dir(settings))
        self.assertIn('BACKBLAZE_B2_SECRET_KEY', dir(settings))


# Integration test that requires tenant setup
class TenantIntegrationTest(TestCase):
    """
    Test tenant-specific functionality (simplified for configuration testing).
    """
    
    def test_tenant_model_exists(self):
        """Test that tenant model is properly configured."""
        from zargar.tenants.models import Tenant
        self.assertTrue(hasattr(Tenant, 'name'))
        self.assertTrue(hasattr(Tenant, 'schema_name'))
    
    def test_tenant_health_check_basic(self):
        """Test basic health check functionality."""
        # Test the health check endpoint without tenant context
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'zargar-jewelry-saas')