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
    'django.contrib.admin',  # Admin only in shared schema for unified admin panel
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_otp',
    'hijack',
    'hijack.contrib.admin',
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
    'zargar.admin_panel',  # Super-admin panel for cross-tenant management
    'zargar.system',   # System-wide models like backups
]

TENANT_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    # NOTE: Django admin removed - we use unified admin panel only
    
    # Core functionality with PERFECT tenant isolation
    'zargar.core',     # User model and core functionality - IN TENANT_APPS for perfect isolation
    
    # Tenant-specific business apps - ALL perfectly isolated
    'zargar.jewelry',
    'zargar.accounting',
    'zargar.customers',
    'zargar.gold_installments',  # Gold installment system
    'zargar.pos',
    'zargar.reports',
]

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

MIDDLEWARE = [
    'zargar.core.middleware.HealthCheckMiddleware',  # Must be first for health checks
    'django_tenants.middleware.main.TenantMainMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'zargar.admin_panel.unified_auth_middleware.UnifiedAdminSecurityMiddleware',  # Admin security
    'zargar.core.security_middleware.SecurityAuditMiddleware',  # Security audit logging
    'zargar.core.security_middleware.RateLimitMiddleware',  # Rate limiting
    'zargar.core.security_middleware.SuspiciousActivityDetectionMiddleware',  # Threat detection
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'zargar.admin_panel.unified_auth_middleware.UnifiedAdminAuthMiddleware',  # Unified admin auth
    'django_otp.middleware.OTPMiddleware',
    'hijack.middleware.HijackUserMiddleware',  # Django-hijack middleware
    'zargar.admin_panel.middleware.ImpersonationAuditMiddleware',  # Custom impersonation audit
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
                'zargar.core.context_processors.domain_settings',
                'zargar.core.context_processors.site_settings',
                'zargar.core.context_processors.admin_context',
                'zargar.admin_panel.context_processors.admin_navigation',
                'zargar.admin_panel.context_processors.admin_theme',
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
        'zargar.core.authentication.TenantAwareJWTAuthentication',
        'zargar.core.authentication.TenantAwareTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
        'zargar.core.permissions.TenantPermission',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'zargar.api.throttling.TenantAPIThrottle',
        'zargar.api.throttling.TenantBurstThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'tenant_api': '500/hour',
        'tenant_burst': '60/min',
        'tenant_anon': '100/hour',
        'pos_api': '1000/hour',
        'accounting_api': '300/hour',
        'reporting_api': '50/hour',
        'superadmin_api': '2000/hour',
        'tenant_creation': '10/day',
        'login_attempts': '10/min',
        'password_reset': '5/hour',
        'two_factor': '20/hour',
        'jewelry_api': '500/hour',
        'customer_api': '500/hour',
        'inventory_api': '500/hour',
        'gold_price_api': '100/hour',
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
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

# Additional CORS settings for API
CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-tenant-schema',
    'x-api-version',
    'x-client-type',
    'x-device-id',
    'x-request-id',
]

CORS_EXPOSE_HEADERS = [
    'x-tenant-schema',
    'x-api-version',
    'x-rate-limit-remaining',
    'x-rate-limit-limit',
    'x-rate-limit-reset',
]

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

# Storage Configuration
# Cloudflare R2
CLOUDFLARE_R2_ACCESS_KEY = config('CLOUDFLARE_R2_ACCESS_KEY', default='3f3dfdd35d139a687d4d00d75da96c76')
CLOUDFLARE_R2_SECRET_KEY = config('CLOUDFLARE_R2_SECRET_KEY', default='2999aa7307448cadfebe63cce0e55f6f74726edfcc32e5de8881015a31c4c897')
CLOUDFLARE_R2_BUCKET = config('CLOUDFLARE_R2_BUCKET', default='securesyntax')
CLOUDFLARE_R2_ENDPOINT = config('CLOUDFLARE_R2_ENDPOINT', default='https://b7900eeee7c415345d86ea859c9dad47.r2.cloudflarestorage.com')
CLOUDFLARE_R2_ACCOUNT_ID = config('CLOUDFLARE_R2_ACCOUNT_ID', default='b7900eeee7c415345d86ea859c9dad47')

# Backblaze B2
BACKBLAZE_B2_ACCESS_KEY = config('BACKBLAZE_B2_ACCESS_KEY', default='005acba9882c2b80000000001')
BACKBLAZE_B2_SECRET_KEY = config('BACKBLAZE_B2_SECRET_KEY', default='K005LzPhrovqG5Eq37oYWxIQiIKIHh8')
BACKBLAZE_B2_BUCKET = config('BACKBLAZE_B2_BUCKET', default='securesyntax')
BACKBLAZE_B2_ENDPOINT = config('BACKBLAZE_B2_ENDPOINT', default='https://s3.us-east-005.backblazeb2.com')
BACKBLAZE_B2_BUCKET_ID = config('BACKBLAZE_B2_BUCKET_ID', default='2a0cfb4aa9f8f8f29c820b18')

# Storage backends configuration
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "backup_primary": {
        "BACKEND": "zargar.core.storage.CloudflareR2Storage",
    },
    "backup_secondary": {
        "BACKEND": "zargar.core.storage.BackblazeB2Storage",
    },
    "backup_redundant": {
        "BACKEND": "zargar.core.storage.RedundantBackupStorage",
    },
}

# Django Tenants Configuration
TENANT_MODEL = "tenants.Tenant"
TENANT_DOMAIN_MODEL = "tenants.Domain"
PUBLIC_SCHEMA_URLCONF = 'zargar.urls_public'
ROOT_URLCONF = 'zargar.urls_tenants'

# Domain Configuration
TENANT_BASE_DOMAIN = config('TENANT_BASE_DOMAIN', default='zargar.com')
TENANT_SUBDOMAIN_SEPARATOR = config('TENANT_SUBDOMAIN_SEPARATOR', default='.')
TENANT_DOMAIN_PROTOCOL = config('TENANT_DOMAIN_PROTOCOL', default='https')

# Custom User Model
AUTH_USER_MODEL = 'core.User'

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    'zargar.admin_panel.unified_auth_backend.UnifiedSuperAdminAuthBackend',  # Unified SuperAdmin auth
    'zargar.core.auth_backends.TenantAwareAuthBackend',
    'zargar.core.auth_backends.TenantUserBackend',
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

# Django-Hijack Configuration
HIJACK_LOGIN_REDIRECT_URL = '/'  # Redirect to tenant dashboard after hijack
HIJACK_LOGOUT_REDIRECT_URL = '/admin/dashboard/'  # Redirect to admin panel after release
HIJACK_ALLOW_GET_REQUESTS = False  # Only allow POST requests for security
HIJACK_REGISTER_ADMIN = False  # Don't auto-register in admin (we'll do it manually)
HIJACK_USE_BOOTSTRAP = False  # We use our own styling
HIJACK_DISPLAY_ADMIN_BUTTON = False  # We'll create custom buttons
HIJACK_DISPLAY_WARNING = True  # Show warning banner
HIJACK_PERMISSION_CHECK = 'zargar.admin_panel.hijack_permissions.is_super_admin'  # Custom permission check
HIJACK_AUTHORIZATION_CHECK = 'zargar.admin_panel.hijack_permissions.authorize_hijack'  # Custom authorization
HIJACK_DECORATOR = 'zargar.admin_panel.hijack_permissions.hijack_decorator'  # Custom decorator

# Hijack session settings
HIJACK_INSERT_BEFORE = '</body>'  # Where to insert the hijack banner
HIJACK_NOTIFY_ADMIN = True  # Notify admin of hijack sessions
HIJACK_NOTIFY_USER = False  # Don't notify the hijacked user

# External Service Configuration

# Iranian SMS Providers Configuration
KAVENEGAR_SMS_API_KEY = config('KAVENEGAR_SMS_API_KEY', default='')
KAVENEGAR_SMS_API_SECRET = config('KAVENEGAR_SMS_API_SECRET', default='')
KAVENEGAR_SMS_SENDER = config('KAVENEGAR_SMS_SENDER', default='10008663')

MELIPAYAMAK_SMS_API_KEY = config('MELIPAYAMAK_SMS_API_KEY', default='')
MELIPAYAMAK_SMS_API_SECRET = config('MELIPAYAMAK_SMS_API_SECRET', default='')
MELIPAYAMAK_SMS_SENDER = config('MELIPAYAMAK_SMS_SENDER', default='10008663')

FARAPAYAMAK_SMS_API_KEY = config('FARAPAYAMAK_SMS_API_KEY', default='')
FARAPAYAMAK_SMS_API_SECRET = config('FARAPAYAMAK_SMS_API_SECRET', default='')
FARAPAYAMAK_SMS_SENDER = config('FARAPAYAMAK_SMS_SENDER', default='10008663')

SMS_IR_SMS_API_KEY = config('SMS_IR_SMS_API_KEY', default='')
SMS_IR_SMS_API_SECRET = config('SMS_IR_SMS_API_SECRET', default='')
SMS_IR_SMS_SENDER = config('SMS_IR_SMS_SENDER', default='10008663')

# Test phone number for SMS connectivity validation
SMS_TEST_PHONE_NUMBER = config('SMS_TEST_PHONE_NUMBER', default=None)

# Email Configuration
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@zargar.com')
EMAIL_TEST_RECIPIENT = config('EMAIL_TEST_RECIPIENT', default=None)

# External Service Health Check Configuration
EXTERNAL_SERVICE_HEALTH_CHECK_INTERVAL = config('EXTERNAL_SERVICE_HEALTH_CHECK_INTERVAL', default=3600, cast=int)  # 1 hour
GOLD_PRICE_UPDATE_INTERVAL = config('GOLD_PRICE_UPDATE_INTERVAL', default=300, cast=int)  # 5 minutes

# Iranian Gold Price API Configuration
IRANIAN_GOLD_PRICE_CACHE_TIMEOUT = config('IRANIAN_GOLD_PRICE_CACHE_TIMEOUT', default=300, cast=int)  # 5 minutes
IRANIAN_GOLD_PRICE_API_TIMEOUT = config('IRANIAN_GOLD_PRICE_API_TIMEOUT', default=10, cast=int)  # 10 seconds

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
        'hijack_audit': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'hijack_audit.log',
            'formatter': 'verbose',
        },
        'external_services': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'external_services.log',
            'formatter': 'verbose',
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
        'hijack_audit': {
            'handlers': ['hijack_audit', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'zargar.core.external_services': {
            'handlers': ['external_services', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'zargar.core.external_service_tasks': {
            'handlers': ['external_services', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}