"""
Context processors for ZARGAR jewelry SaaS platform.
"""
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
import jdatetime
from decimal import Decimal


def tenant_context(request):
    """
    Add tenant-specific context to all templates.
    """
    context = {
        'tenant': getattr(request, 'tenant', None),
        'tenant_name': getattr(request, 'tenant_name', None),
        'tenant_domain': getattr(request, 'tenant_domain', None),
        'is_tenant_context': hasattr(request, 'tenant') and request.tenant is not None,
        'is_public_context': not (hasattr(request, 'tenant') and request.tenant is not None),
    }
    
    # Add tenant-specific settings if available
    if hasattr(request, 'tenant') and request.tenant:
        context.update({
            'tenant_settings': getattr(request.tenant, 'settings', {}),
            'tenant_logo': getattr(request.tenant, 'logo', None),
            'tenant_theme': getattr(request.tenant, 'theme_preference', 'light'),
        })
    
    return context


def persian_context(request):
    """
    Add Persian localization context to all templates.
    """
    # Get current Persian date
    now = timezone.now()
    persian_now = jdatetime.datetime.fromgregorian(datetime=now)
    
    # Persian month names
    persian_months = [
        'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
        'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
    ]
    
    # Persian day names
    persian_days = [
        'شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه'
    ]
    
    context = {
        # Language and direction
        'LANGUAGE_CODE': 'fa',
        'LANGUAGE_BIDI': True,
        'language_direction': 'rtl',
        'is_rtl': True,
        'persian_locale': True,
        
        # Persian date and time
        'persian_date': persian_now,
        'persian_date_formatted': persian_now.strftime('%Y/%m/%d'),
        'persian_datetime_formatted': persian_now.strftime('%Y/%m/%d - %H:%M'),
        'persian_year': persian_now.year,
        'persian_month': persian_now.month,
        'persian_day': persian_now.day,
        'persian_month_name': persian_months[persian_now.month - 1],
        'persian_day_name': persian_days[persian_now.weekday()],
        
        # Persian number formatting
        'use_persian_numbers': True,
        'currency_symbol': 'تومان',
        'currency_code': 'IRR',
        'thousand_separator': '٬',
        'decimal_separator': '٫',
        
        # Persian business terms
        'business_terms': {
            'weight_unit': 'گرم',
            'karat_unit': 'عیار',
            'manufacturing_cost': 'اجرت',
            'gold_price': 'قیمت طلا',
            'customer': 'مشتری',
            'invoice': 'فاکتور',
            'payment': 'پرداخت',
            'installment': 'قسط',
        },
        
        # Persian UI text
        'ui_text': {
            'dashboard': _('Dashboard'),
            'inventory': _('Inventory'),
            'customers': _('Customers'),
            'sales': _('Sales'),
            'accounting': _('Accounting'),
            'reports': _('Reports'),
            'settings': _('Settings'),
            'logout': _('Logout'),
            'login': _('Login'),
            'save': _('Save'),
            'cancel': _('Cancel'),
            'delete': _('Delete'),
            'edit': _('Edit'),
            'add': _('Add'),
            'search': _('Search'),
            'filter': _('Filter'),
            'export': _('Export'),
            'print': _('Print'),
        }
    }
    
    return context


def theme_context(request):
    """
    Add theme-specific context to all templates.
    """
    theme = getattr(request, 'theme', settings.THEME_SETTINGS['DEFAULT_THEME'])
    
    context = {
        'current_theme': theme,
        'is_dark_mode': theme == 'dark',
        'is_light_mode': theme == 'light',
        'theme_classes': getattr(request, 'theme_classes', ''),
        'theme_type': getattr(request, 'theme_type', 'modern'),
        'available_themes': settings.THEME_SETTINGS['AVAILABLE_THEMES'],
    }
    
    # Theme-specific settings
    if theme == 'dark':
        context.update({
            'cybersecurity_theme': True,
            'glassmorphism_enabled': True,
            'neon_effects_enabled': True,
            'animations_enabled': True,
            'cyber_colors': {
                'primary': '#00D4FF',
                'secondary': '#00FF88',
                'tertiary': '#FF6B35',
                'warning': '#FFB800',
                'danger': '#FF4757',
                'success': '#00FF88',
                'purple': '#A55EEA',
            },
            'cyber_backgrounds': {
                'primary': '#0B0E1A',
                'secondary': '#1A1D29',
                'surface': '#252A3A',
                'elevated': '#2D3348',
            }
        })
    else:
        context.update({
            'modern_theme': True,
            'clean_design': True,
            'professional_layout': True,
            'light_colors': {
                'primary': '#1F2937',
                'secondary': '#374151',
                'accent': '#3B82F6',
                'success': '#10B981',
                'warning': '#F59E0B',
                'danger': '#EF4444',
            }
        })
    
    return context


def persian_number_formatter(request):
    """
    Add Persian number formatting functions to templates.
    """
    def format_persian_number(number):
        """Convert English digits to Persian digits."""
        if number is None:
            return ''
        
        english_digits = '0123456789'
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        
        str_number = str(number)
        for i, digit in enumerate(english_digits):
            str_number = str_number.replace(digit, persian_digits[i])
        
        return str_number
    
    def format_persian_currency(amount):
        """Format currency in Persian with Toman."""
        if amount is None:
            return ''
        
        # Format with thousand separators
        formatted = f"{amount:,.0f}"
        
        # Convert to Persian digits
        persian_formatted = format_persian_number(formatted)
        
        # Replace comma with Persian thousand separator
        persian_formatted = persian_formatted.replace(',', '٬')
        
        return f"{persian_formatted} تومان"
    
    def format_persian_weight(grams):
        """Format weight in Persian with grams."""
        if grams is None:
            return ''
        
        formatted = f"{grams:.3f}"
        persian_formatted = format_persian_number(formatted)
        persian_formatted = persian_formatted.replace('.', '٫')
        
        return f"{persian_formatted} گرم"
    
    def convert_to_mithqal(grams):
        """Convert grams to Mithqal (traditional Persian weight unit)."""
        if grams is None:
            return ''
        
        # 1 Mithqal = 4.608 grams (traditional Iranian measurement)
        mithqal = float(grams) / 4.608
        formatted = f"{mithqal:.3f}"
        persian_formatted = format_persian_number(formatted)
        persian_formatted = persian_formatted.replace('.', '٫')
        
        return f"{persian_formatted} مثقال"
    
    def convert_to_soot(grams):
        """Convert grams to Soot (traditional Persian weight unit)."""
        if grams is None:
            return ''
        
        # 1 Soot = 3.456 grams (traditional Iranian measurement)
        soot = float(grams) / 3.456
        formatted = f"{soot:.3f}"
        persian_formatted = format_persian_number(formatted)
        persian_formatted = persian_formatted.replace('.', '٫')
        
        return f"{persian_formatted} سوت"
    
    return {
        'format_persian_number': format_persian_number,
        'format_persian_currency': format_persian_currency,
        'format_persian_weight': format_persian_weight,
        'convert_to_mithqal': convert_to_mithqal,
        'convert_to_soot': convert_to_soot,
    }


def persian_calendar_context(request):
    """
    Add Persian calendar context to templates.
    """
    now = timezone.now()
    persian_now = jdatetime.datetime.fromgregorian(datetime=now)
    
    # Calculate fiscal year (Persian calendar year)
    fiscal_year_start = jdatetime.datetime(persian_now.year, 1, 1)
    fiscal_year_end = jdatetime.datetime(persian_now.year, 12, 29)  # Esfand can have 29 or 30 days
    
    # Check if it's a leap year
    is_leap_year = jdatetime.j_y_is_leap(persian_now.year)
    if is_leap_year:
        fiscal_year_end = jdatetime.datetime(persian_now.year, 12, 30)
    
    context = {
        'persian_calendar': {
            'current_date': persian_now,
            'current_year': persian_now.year,
            'current_month': persian_now.month,
            'current_day': persian_now.day,
            'is_leap_year': is_leap_year,
            'fiscal_year_start': fiscal_year_start,
            'fiscal_year_end': fiscal_year_end,
            'days_in_year': 366 if is_leap_year else 365,
        },
        'persian_holidays': get_persian_holidays(persian_now.year),
    }
    
    return context


def get_persian_holidays(year):
    """
    Get Persian holidays for the given year.
    """
    holidays = [
        {'date': jdatetime.date(year, 1, 1), 'name': 'نوروز - سال نو'},
        {'date': jdatetime.date(year, 1, 2), 'name': 'عید نوروز'},
        {'date': jdatetime.date(year, 1, 3), 'name': 'عید نوروز'},
        {'date': jdatetime.date(year, 1, 4), 'name': 'عید نوروز'},
        {'date': jdatetime.date(year, 1, 12), 'name': 'روز جمهوری اسلامی ایران'},
        {'date': jdatetime.date(year, 1, 13), 'name': 'سیزده بدر'},
        {'date': jdatetime.date(year, 3, 14), 'name': 'رحلت امام خمینی'},
        {'date': jdatetime.date(year, 3, 15), 'name': 'قیام ۱۵ خرداد'},
        {'date': jdatetime.date(year, 6, 30), 'name': 'شهادت امام علی (ع)'},
        {'date': jdatetime.date(year, 7, 27), 'name': 'عید سعید فطر'},
        {'date': jdatetime.date(year, 10, 2), 'name': 'عید سعید قربان'},
        {'date': jdatetime.date(year, 10, 10), 'name': 'عید سعید غدیر خم'},
        {'date': jdatetime.date(year, 10, 28), 'name': 'تاسوعای حسینی'},
        {'date': jdatetime.date(year, 10, 29), 'name': 'عاشورای حسینی'},
        {'date': jdatetime.date(year, 11, 18), 'name': 'اربعین حسینی'},
        {'date': jdatetime.date(year, 11, 28), 'name': 'رحلت رسول اکرم'},
        {'date': jdatetime.date(year, 12, 1), 'name': 'شهادت امام رضا (ع)'},
        {'date': jdatetime.date(year, 12, 9), 'name': 'تولد حضرت فاطمه (س)'},
    ]
    
    return holidays


def frontend_settings_context(request):
    """
    Add frontend framework settings to templates.
    """
    return {
        'frontend_settings': settings.FRONTEND_SETTINGS,
        'tailwind_version': settings.FRONTEND_SETTINGS['TAILWIND_CSS_VERSION'],
        'flowbite_version': settings.FRONTEND_SETTINGS['FLOWBITE_VERSION'],
        'alpine_version': settings.FRONTEND_SETTINGS['ALPINE_JS_VERSION'],
        'htmx_version': settings.FRONTEND_SETTINGS['HTMX_VERSION'],
        'framer_motion_version': settings.FRONTEND_SETTINGS['FRAMER_MOTION_VERSION'],
    }