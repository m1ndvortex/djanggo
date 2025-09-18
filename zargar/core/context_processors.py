"""
Context processors for zargar project.
"""
from django.conf import settings
import jdatetime
from django.utils import timezone


def tenant_context(request):
    """
    Add tenant context to all templates.
    """
    context = {}
    
    if hasattr(request, 'tenant_context') and request.tenant_context:
        context.update({
            'tenant': request.tenant_context['tenant'],
            'tenant_name': request.tenant_context['name'],
            'tenant_domain': request.tenant_context['domain_url'],
            'tenant_schema': request.tenant_context['schema_name'],
        })
    
    return context


def persian_context(request):
    """
    Add Persian localization context to all templates.
    """
    context = {}
    
    if hasattr(request, 'persian_date'):
        context.update({
            'persian_date': request.persian_date,
            'shamsi_today': request.persian_date['today'],
            'shamsi_now': request.persian_date['now'],
        })
    else:
        # Fallback if middleware didn't run
        today = jdatetime.date.today()
        now = jdatetime.datetime.now()
        context.update({
            'persian_date': {
                'today': today,
                'now': now,
                'shamsi_year': today.year,
                'shamsi_month': today.month,
                'shamsi_day': today.day,
            },
            'shamsi_today': today,
            'shamsi_now': now,
        })
    
    # Add Persian number formatting utilities
    context.update({
        'persian_numbers': {
            '0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
            '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'
        },
        'rtl_direction': True,
        'language_code': 'fa',
    })
    
    return context


def theme_context(request):
    """
    Add theme context to all templates.
    """
    # Get theme from cookie or use default
    theme = request.COOKIES.get(
        settings.THEME_SETTINGS['THEME_COOKIE_NAME'],
        settings.THEME_SETTINGS['DEFAULT_THEME']
    )
    
    # Validate theme
    if theme not in settings.THEME_SETTINGS['AVAILABLE_THEMES']:
        theme = settings.THEME_SETTINGS['DEFAULT_THEME']
    
    context = {
        'current_theme': theme,
        'is_dark_mode': theme == 'dark',
        'is_light_mode': theme == 'light',
        'available_themes': settings.THEME_SETTINGS['AVAILABLE_THEMES'],
        'theme_settings': settings.THEME_SETTINGS,
    }
    
    # Add theme-specific CSS classes
    if theme == 'dark':
        context.update({
            'theme_classes': 'dark cyber-theme',
            'bg_primary': 'cyber-bg-primary',
            'text_primary': 'cyber-text-primary',
            'card_classes': 'cyber-glass-card',
            'button_classes': 'cyber-neon-button',
        })
    else:
        context.update({
            'theme_classes': 'light modern-theme',
            'bg_primary': 'bg-gray-50',
            'text_primary': 'text-gray-900',
            'card_classes': 'bg-white shadow-sm',
            'button_classes': 'bg-blue-600 hover:bg-blue-700',
        })
    
    # Add frontend integration settings
    context.update({
        'frontend_settings': settings.FRONTEND_SETTINGS,
        'tailwind_version': settings.FRONTEND_SETTINGS['TAILWIND_CSS_VERSION'],
        'flowbite_version': settings.FRONTEND_SETTINGS['FLOWBITE_VERSION'],
        'alpine_version': settings.FRONTEND_SETTINGS['ALPINE_JS_VERSION'],
        'htmx_version': settings.FRONTEND_SETTINGS['HTMX_VERSION'],
    })
    
    return context