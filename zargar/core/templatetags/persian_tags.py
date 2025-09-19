"""
Persian template tags for ZARGAR jewelry SaaS platform.
"""
from django import template
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from decimal import Decimal
import jdatetime
from django.utils import timezone

register = template.Library()


@register.filter
def persian_number(value):
    """Convert English digits to Persian digits."""
    if value is None:
        return ''
    
    english_digits = '0123456789'
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    
    str_value = str(value)
    for i, digit in enumerate(english_digits):
        str_value = str_value.replace(digit, persian_digits[i])
    
    return str_value


@register.filter
def persian_currency(amount):
    """Format currency in Persian with Toman."""
    if amount is None or amount == '':
        return ''
    
    try:
        # Convert to float if it's a string
        if isinstance(amount, str):
            amount = float(amount.replace(',', ''))
        
        # Format with thousand separators
        formatted = f"{amount:,.0f}"
        
        # Convert to Persian digits
        persian_formatted = persian_number(formatted)
        
        # Replace comma with Persian thousand separator
        persian_formatted = persian_formatted.replace(',', '٬')
        
        return mark_safe(f"{persian_formatted} تومان")
    except (ValueError, TypeError):
        return str(amount)


@register.filter
def persian_weight(grams):
    """Format weight in Persian with grams."""
    if grams is None or grams == '':
        return ''
    
    try:
        if isinstance(grams, str):
            grams = float(grams)
        
        formatted = f"{grams:.3f}"
        persian_formatted = persian_number(formatted)
        persian_formatted = persian_formatted.replace('.', '٫')
        
        return mark_safe(f"{persian_formatted} گرم")
    except (ValueError, TypeError):
        return str(grams)


@register.filter
def to_mithqal(grams):
    """Convert grams to Mithqal (traditional Persian weight unit)."""
    if grams is None or grams == '':
        return ''
    
    try:
        if isinstance(grams, str):
            grams = float(grams)
        
        # 1 Mithqal = 4.608 grams (traditional Iranian measurement)
        mithqal = float(grams) / 4.608
        formatted = f"{mithqal:.3f}"
        persian_formatted = persian_number(formatted)
        persian_formatted = persian_formatted.replace('.', '٫')
        
        return mark_safe(f"{persian_formatted} مثقال")
    except (ValueError, TypeError):
        return str(grams)


@register.filter
def to_soot(grams):
    """Convert grams to Soot (traditional Persian weight unit)."""
    if grams is None or grams == '':
        return ''
    
    try:
        if isinstance(grams, str):
            grams = float(grams)
        
        # 1 Soot = 3.456 grams (traditional Iranian measurement)
        soot = float(grams) / 3.456
        formatted = f"{soot:.3f}"
        persian_formatted = persian_number(formatted)
        persian_formatted = persian_formatted.replace('.', '٫')
        
        return mark_safe(f"{persian_formatted} سوت")
    except (ValueError, TypeError):
        return str(grams)


@register.filter
def persian_date(date_obj):
    """Convert Gregorian date to Persian date."""
    if date_obj is None:
        return ''
    
    try:
        if hasattr(date_obj, 'date'):
            # It's a datetime object
            persian_date = jdatetime.date.fromgregorian(date=date_obj.date())
        else:
            # It's a date object
            persian_date = jdatetime.date.fromgregorian(date=date_obj)
        
        formatted = persian_date.strftime('%Y/%m/%d')
        return persian_number(formatted)
    except (ValueError, TypeError, AttributeError):
        return str(date_obj)


@register.filter
def persian_datetime(datetime_obj):
    """Convert Gregorian datetime to Persian datetime."""
    if datetime_obj is None:
        return ''
    
    try:
        persian_datetime = jdatetime.datetime.fromgregorian(datetime=datetime_obj)
        formatted = persian_datetime.strftime('%Y/%m/%d - %H:%M')
        return persian_number(formatted)
    except (ValueError, TypeError, AttributeError):
        return str(datetime_obj)


@register.filter
def persian_month_name(month_number):
    """Get Persian month name from month number."""
    persian_months = [
        'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
        'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
    ]
    
    try:
        month_num = int(month_number)
        if 1 <= month_num <= 12:
            return persian_months[month_num - 1]
        return str(month_number)
    except (ValueError, TypeError):
        return str(month_number)


@register.filter
def persian_day_name(weekday_number):
    """Get Persian day name from weekday number (0=Saturday)."""
    persian_days = [
        'شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه'
    ]
    
    try:
        day_num = int(weekday_number)
        if 0 <= day_num <= 6:
            return persian_days[day_num]
        return str(weekday_number)
    except (ValueError, TypeError):
        return str(weekday_number)


@register.filter
def karat_display(karat):
    """Display karat with Persian text."""
    if karat is None or karat == '':
        return ''
    
    try:
        karat_num = persian_number(str(karat))
        return mark_safe(f"عیار {karat_num}")
    except (ValueError, TypeError):
        return str(karat)


@register.filter
def percentage_persian(value):
    """Display percentage with Persian digits."""
    if value is None or value == '':
        return ''
    
    try:
        if isinstance(value, str):
            value = float(value)
        
        formatted = f"{value:.1f}%"
        persian_formatted = persian_number(formatted)
        # Replace decimal point with Persian decimal separator
        persian_formatted = persian_formatted.replace('.', '٫')
        return persian_formatted
    except (ValueError, TypeError):
        return str(value)


@register.simple_tag
def persian_business_term(term_key):
    """Get Persian business term translation."""
    terms = {
        'weight': 'وزن',
        'karat': 'عیار',
        'manufacturing_cost': 'اجرت',
        'gold_price': 'قیمت طلا',
        'customer': 'مشتری',
        'invoice': 'فاکتور',
        'payment': 'پرداخت',
        'installment': 'قسط',
        'jewelry': 'جواهرات',
        'gold': 'طلا',
        'silver': 'نقره',
        'diamond': 'الماس',
        'ring': 'انگشتر',
        'necklace': 'گردنبند',
        'bracelet': 'دستبند',
        'earrings': 'گوشواره',
        'inventory': 'موجودی',
        'sales': 'فروش',
        'accounting': 'حسابداری',
        'reports': 'گزارش‌ها',
        'dashboard': 'داشبورد',
    }
    
    return terms.get(term_key, term_key)


@register.simple_tag
def rtl_class():
    """Return RTL CSS class."""
    return 'rtl'


@register.simple_tag
def persian_direction():
    """Return text direction for Persian."""
    return 'rtl'


@register.simple_tag
def persian_lang():
    """Return Persian language code."""
    return 'fa'


@register.inclusion_tag('core/tags/persian_date_picker.html')
def persian_date_picker(field_name, field_value=None, field_id=None):
    """Render Persian date picker widget."""
    context = {
        'field_name': field_name,
        'field_value': field_value,
        'field_id': field_id or field_name,
        'current_persian_date': jdatetime.date.today().strftime('%Y/%m/%d'),
    }
    return context


@register.inclusion_tag('core/tags/theme_toggle.html')
def theme_toggle_button():
    """Render theme toggle button."""
    return {}


@register.inclusion_tag('core/tags/persian_number_input.html')
def persian_number_input(field_name, field_value=None, field_id=None, placeholder=''):
    """Render Persian number input with automatic formatting."""
    context = {
        'field_name': field_name,
        'field_value': field_value,
        'field_id': field_id or field_name,
        'placeholder': placeholder,
    }
    return context


@register.filter
def add_rtl_class(css_classes):
    """Add RTL class to existing CSS classes."""
    if css_classes:
        return f"{css_classes} rtl"
    return "rtl"


@register.filter
def persian_ordinal(number):
    """Convert number to Persian ordinal (1st, 2nd, etc.)."""
    if number is None:
        return ''
    
    try:
        num = int(number)
        persian_num = persian_number(str(num))
        return f"{persian_num}م"  # Persian ordinal suffix
    except (ValueError, TypeError):
        return str(number)


@register.simple_tag
def current_persian_year():
    """Get current Persian year."""
    now = timezone.now()
    persian_now = jdatetime.datetime.fromgregorian(datetime=now)
    return persian_number(str(persian_now.year))


@register.simple_tag
def current_persian_date():
    """Get current Persian date formatted."""
    now = timezone.now()
    persian_now = jdatetime.datetime.fromgregorian(datetime=now)
    formatted = persian_now.strftime('%Y/%m/%d')
    return persian_number(formatted)


@register.simple_tag
def current_persian_datetime():
    """Get current Persian datetime formatted."""
    now = timezone.now()
    persian_now = jdatetime.datetime.fromgregorian(datetime=now)
    formatted = persian_now.strftime('%Y/%m/%d - %H:%M')
    return persian_number(formatted)