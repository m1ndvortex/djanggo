"""
Base settings for zargar project.
"""
import os
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,0.0.0.0', cast=lambda v: [s.strip() for s in v.split(',')])

# Application definition
SHARED_APPS = [
    'django_tenants',  # Must be first
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_otp',
    'storages',
    'compressor',
    'sass_processor',
    'health_check',
    'health_check.db',
    'health_check.cache',
    'health_check.storage',
    'django_jalali',
    
    # Local apps (shared across tenants)
    'zargar.tenants',  # Tenant, Domain, and SuperAdmin models in shared schema
    'zargar.api',      # API endpoints can be shared
]

TENANT_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',  # Admin is tenant-specific
    
    # Core functionality with PERFECT tenant isolation
    'zargar.core',     # User model and core functionality - IN TENANT_APPS for perfect isolation
    
    # Tenant-specific business apps - ALL perfectly isolated
    'zargar.jewelry',
    'zargar.accounting',
    'zargar.customers',
    'zargar.pos',
    'zargar.reports',
]

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

MIDDLEWARE = [
    'zargar.core.middleware.HealthCheckMiddleware',  # Must be first for health checks
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
    'zargar.core.middleware.TenantIsolationMiddleware',  # New tenant isolation middleware
    'zargar.core.middleware.PersianLocalizationMiddleware',
]

ROOT_URLCONF = 'zargar.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'zargar.core.context_processors.tenant_context',
                'zargar.core.context_processors.persian_context',
                'zargar.core.context_processors.theme_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'zargar.wsgi.application'

# Database
import dj_database_url

DATABASE_URL = config('DATABASE_URL', default='postgresql://zargar:zargar_password_2024@localhost:5432/zargar_dev')

DATABASES = {
    'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
}

# Override engine for django-tenants
DATABASES['default']['ENGINE'] = 'django_tenants.postgresql_backend'

DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)

# Cache configuration
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'fa'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('fa', 'Persian'),
    ('en', 'English'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
    'sass_processor.finders.CssFinder',
]

# Django Compressor settings
COMPRESS_ENABLED = not DEBUG
COMPRESS_CSS_FILTERS = [
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.rCSSMinFilter',
]
COMPRESS_JS_FILTERS = [
    'compressor.filters.jsmin.JSMinFilter',
]

# Sass processor settings
SASS_PROCESSOR_ROOT = BASE_DIR / 'static'
SASS_PROCESSOR_INCLUDE_DIRS = [
    BASE_DIR / 'static' / 'scss',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
}

# JWT Configuration
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

CORS_ALLOW_CREDENTIALS = True

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

# Storage Configuration
# Cloudflare R2
CLOUDFLARE_R2_ACCESS_KEY = config('CLOUDFLARE_R2_ACCESS_KEY', default='')
CLOUDFLARE_R2_SECRET_KEY = config('CLOUDFLARE_R2_SECRET_KEY', default='')
CLOUDFLARE_R2_BUCKET = config('CLOUDFLARE_R2_BUCKET', default='')
CLOUDFLARE_R2_ENDPOINT = config('CLOUDFLARE_R2_ENDPOINT', default='')
CLOUDFLARE_R2_ACCOUNT_ID = config('CLOUDFLARE_R2_ACCOUNT_ID', default='')

# Backblaze B2
BACKBLAZE_B2_ACCESS_KEY = config('BACKBLAZE_B2_ACCESS_KEY', default='')
BACKBLAZE_B2_SECRET_KEY = config('BACKBLAZE_B2_SECRET_KEY', default='')
BACKBLAZE_B2_BUCKET = config('BACKBLAZE_B2_BUCKET', default='')

# Django Tenants Configuration
TENANT_MODEL = "tenants.Tenant"
TENANT_DOMAIN_MODEL = "tenants.Domain"
PUBLIC_SCHEMA_URLCONF = 'zargar.urls_public'
ROOT_URLCONF = 'zargar.urls_tenants'

# Custom User Model
AUTH_USER_MODEL = 'core.User'

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    'zargar.core.auth_backends.TenantAwareAuthBackend',
    'django.contrib.auth.backends.ModelBackend',  # Fallback
]

# Password Hashing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# Persian/RTL Configuration
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = '٬'  # Persian thousand separator
DECIMAL_SEPARATOR = '٫'   # Persian decimal separator

# Persian Calendar Configuration
USE_JALALI = True
JALALI_DATE_DEFAULTS = {
    'Strftime': '%Y/%m/%d',
    'Static_url': '/static/admin/js/',
    'Date_field': 'date',
    'Datetime_field': 'datetime',
}

# Theme Configuration
THEME_SETTINGS = {
    'DEFAULT_THEME': 'light',
    'AVAILABLE_THEMES': ['light', 'dark'],
    'THEME_COOKIE_NAME': 'zargar_theme',
    'THEME_COOKIE_AGE': 365 * 24 * 60 * 60,  # 1 year
}

# Frontend Integration Settings
FRONTEND_SETTINGS = {
    'TAILWIND_CSS_VERSION': '3.3.0',
    'FLOWBITE_VERSION': '1.8.1',
    'ALPINE_JS_VERSION': '3.13.0',
    'HTMX_VERSION': '1.9.6',
    'FRAMER_MOTION_VERSION': '10.16.4',
}

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'zargar': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}