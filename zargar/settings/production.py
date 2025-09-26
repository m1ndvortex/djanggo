"""
Production settings for zargar project.
"""
from .base import *
from .security import get_security_settings, AUTH_SECURITY, RATE_LIMITING, FILE_UPLOAD_SECURITY

# Apply production security settings
security_settings = get_security_settings('production')
for key, value in security_settings.items():
    globals()[key] = value

# Apply additional security configurations
globals().update(AUTH_SECURITY)
globals().update(FILE_UPLOAD_SECURITY)

# Rate limiting for DRF
REST_FRAMEWORK.update({
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': RATE_LIMITING['DEFAULT_THROTTLE_RATES']
})

# Security middleware order is important
MIDDLEWARE.insert(1, 'django.middleware.security.SecurityMiddleware')

# Email configuration for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@zargar.com')

# Storage configuration for production
DEFAULT_FILE_STORAGE = 'zargar.core.storage.RedundantBackupStorage'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Logging for production
LOGGING['handlers']['file']['filename'] = '/var/log/zargar/django.log'
LOGGING['loggers']['zargar']['level'] = 'INFO'
LOGGING['root']['level'] = 'WARNING'