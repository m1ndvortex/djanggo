"""
Development settings for zargar project.
"""
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Add development-specific apps
INSTALLED_APPS += [
    'debug_toolbar',
]

# Add debug toolbar middleware
MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
] + MIDDLEWARE

# Debug toolbar configuration
INTERNAL_IPS = [
    '127.0.0.1',
    '0.0.0.0',
    'localhost',
]

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable HTTPS requirements in development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True

# Logging for development
LOGGING['loggers']['zargar']['level'] = 'DEBUG'
LOGGING['root']['level'] = 'DEBUG'

# Create logs directory if it doesn't exist
import os
os.makedirs(BASE_DIR / 'logs', exist_ok=True)