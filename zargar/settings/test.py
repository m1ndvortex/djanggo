"""
Test settings for zargar project.
"""
from .base import *

# Use test database configuration
import dj_database_url

# Use test database configuration
DATABASE_URL = config('DATABASE_URL', default='postgresql://zargar:zargar_test_password@db:5432/zargar_test')

DATABASES = {
    'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
}

# Override engine for django-tenants
DATABASES['default']['ENGINE'] = 'django_tenants.postgresql_backend'

# Use Redis cache for tests to test real integration
REDIS_URL = config('REDIS_URL', default='redis://redis:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Keep migrations enabled for proper testing

# Use console email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable logging during tests
LOGGING_CONFIG = None

# Password hashers for faster tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Celery configuration for tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Media files for tests
MEDIA_ROOT = BASE_DIR / 'test_media'

# Test-specific settings
TEST_RUNNER = 'django.test.runner.DiscoverRunner'