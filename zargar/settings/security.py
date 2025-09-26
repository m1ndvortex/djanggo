"""
Security-focused settings for ZARGAR jewelry SaaS platform.
This module contains all security-related configurations.
"""
from decouple import config

# Security Headers Configuration
SECURITY_HEADERS = {
    'SECURE_BROWSER_XSS_FILTER': True,
    'SECURE_CONTENT_TYPE_NOSNIFF': True,
    'X_FRAME_OPTIONS': 'DENY',
    'SECURE_REFERRER_POLICY': 'strict-origin-when-cross-origin',
}

# SSL/TLS Configuration
SSL_CONFIG = {
    'SECURE_SSL_REDIRECT': True,
    'SECURE_PROXY_SSL_HEADER': ('HTTP_X_FORWARDED_PROTO', 'https'),
    'SECURE_HSTS_SECONDS': 31536000,  # 1 year
    'SECURE_HSTS_INCLUDE_SUBDOMAINS': True,
    'SECURE_HSTS_PRELOAD': True,
}

# Cookie Security
COOKIE_SECURITY = {
    'SESSION_COOKIE_SECURE': True,
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Strict',
    'SESSION_COOKIE_AGE': 3600,  # 1 hour
    'CSRF_COOKIE_SECURE': True,
    'CSRF_COOKIE_HTTPONLY': True,
    'CSRF_COOKIE_SAMESITE': 'Strict',
}

# Content Security Policy
CSP_CONFIG = {
    'CSP_DEFAULT_SRC': ("'self'",),
    'CSP_SCRIPT_SRC': ("'self'", "'unsafe-inline'"),
    'CSP_STYLE_SRC': ("'self'", "'unsafe-inline'"),
    'CSP_IMG_SRC': ("'self'", "data:", "https:"),
    'CSP_FONT_SRC': ("'self'", "https:"),
    'CSP_CONNECT_SRC': ("'self'",),
    'CSP_FRAME_ANCESTORS': ("'none'",),
    'CSP_BASE_URI': ("'self'",),
    'CSP_FORM_ACTION': ("'self'",),
}

# Authentication Security
AUTH_SECURITY = {
    'AUTH_PASSWORD_VALIDATORS': [
        {
            'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
            'OPTIONS': {
                'min_length': 12,
            }
        },
        {
            'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        },
    ],
    'LOGIN_ATTEMPTS_LIMIT': 5,
    'LOGIN_ATTEMPTS_TIMEOUT': 300,  # 5 minutes
    'PASSWORD_RESET_TIMEOUT': 3600,  # 1 hour
}

# Rate Limiting
RATE_LIMITING = {
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'login': '5/minute',
        'password_reset': '3/hour',
    }
}

# File Upload Security
FILE_UPLOAD_SECURITY = {
    'FILE_UPLOAD_MAX_MEMORY_SIZE': 5242880,  # 5MB
    'DATA_UPLOAD_MAX_MEMORY_SIZE': 5242880,  # 5MB
    'FILE_UPLOAD_PERMISSIONS': 0o644,
    'ALLOWED_UPLOAD_EXTENSIONS': [
        '.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx'
    ],
    'MAX_UPLOAD_SIZE': 10485760,  # 10MB
}

# Database Security
DATABASE_SECURITY = {
    'CONN_MAX_AGE': 0,  # Don't persist connections
    'CONN_HEALTH_CHECKS': True,
    'OPTIONS': {
        'sslmode': 'require',
        'connect_timeout': 10,
        'options': '-c default_transaction_isolation=serializable'
    }
}

# Logging Security
SECURITY_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'security': {
            'format': '{levelname} {asctime} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/zargar/security.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'security',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': True,
        },
        'zargar.security': {
            'handlers': ['security_file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Environment-specific security settings
def get_security_settings(environment='production'):
    """Get security settings for specific environment."""
    settings = {}
    
    if environment == 'production':
        settings.update(SSL_CONFIG)
        settings.update(SECURITY_HEADERS)
        settings.update(COOKIE_SECURITY)
        settings.update(CSP_CONFIG)
        settings['DEBUG'] = False
        settings['ALLOWED_HOSTS'] = config('ALLOWED_HOSTS', default='').split(',')
        
    elif environment == 'staging':
        settings.update(SSL_CONFIG)
        settings.update(SECURITY_HEADERS)
        settings.update(COOKIE_SECURITY)
        settings['DEBUG'] = False
        settings['ALLOWED_HOSTS'] = ['staging.zargar.com']
        
    elif environment == 'development':
        settings['DEBUG'] = True
        settings['ALLOWED_HOSTS'] = ['localhost', '127.0.0.1', '0.0.0.0']
        # Relaxed security for development
        settings['SECURE_SSL_REDIRECT'] = False
        settings['SESSION_COOKIE_SECURE'] = False
        settings['CSRF_COOKIE_SECURE'] = False
    
    return settings