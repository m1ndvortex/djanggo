"""
Tests for RTL layout and Persian text rendering.
"""
import pytest
import os
import sys
import django
from django.conf import settings
from django.template import Context, Template

# Configure Django settings for testing
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'zargar.core',
        ],
        USE_I18N=True,
        USE_L10N=True,
        LANGUAGE_CODE='fa',
        LANGUAGES=[('fa', 'Persian')],
        LOCALE_PATHS=['/app/locale'],
        SECRET_KEY='test-secret-key',
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [],
                'APP_DIRS': True,
                'OPTIONS': {
                    'context_processors': [
                        'django.template.context_processors.debug',
                        'django.template.context_processors.request',
                        'django.template.context_processors.i18n',
                    ],
                },
            },
        ],
    )
    django.setup()


def test_rtl_template_tags():
    """Test RTL-related template tags."""
    from zargar.core.templatetags.persian_tags import rtl_class, persian_direction, persian_lang
    
    assert rtl_class() == 'rtl'
    assert persian_direction() == 'rtl'
    assert persian_lang() == 'fa'


def test_persian_template_rendering():
    """Test Persian template rendering with RTL layout."""
    template = Template("""
        {% load persian_tags %}
        <div dir="{% persian_direction %}" class="{% rtl_class %}">
            <span>{{ amount|persian_currency }}</span>
            <span>{{ weight|persian_weight }}</span>
            <span>{{ karat|karat_display }}</span>
        </div>
    """)
    
    context = Context({
        'amount': 1000,
        'weight': 10.5,
        'karat': 18
    })
    
    rendered = template.render(context)
    
    # Check RTL direction
    assert 'dir="rtl"' in rendered
    assert 'class="rtl"' in rendered
    
    # Check Persian formatting
    assert "تومان" in rendered
    assert "گرم" in rendered
    assert "عیار" in rendered
    
    # Check Persian digits
    assert any(char in rendered for char in "۰۱۲۳۴۵۶۷۸۹")


def test_add_rtl_class_filter():
    """Test adding RTL class to existing CSS classes."""
    from zargar.core.templatetags.persian_tags import add_rtl_class
    
    assert add_rtl_class("btn btn-primary") == "btn btn-primary rtl"
    assert add_rtl_class("") == "rtl"
    assert add_rtl_class(None) == "rtl"


def test_persian_ordinal():
    """Test Persian ordinal number formatting."""
    from zargar.core.templatetags.persian_tags import persian_ordinal
    
    assert persian_ordinal(1) == "۱م"
    assert persian_ordinal(2) == "۲م"
    assert persian_ordinal(10) == "۱۰م"
    assert persian_ordinal("") == ""
    assert persian_ordinal(None) == ""


def test_persian_business_terms():
    """Test Persian business term translations."""
    from zargar.core.templatetags.persian_tags import persian_business_term
    
    assert persian_business_term('weight') == 'وزن'
    assert persian_business_term('karat') == 'عیار'
    assert persian_business_term('gold') == 'طلا'
    assert persian_business_term('customer') == 'مشتری'
    assert persian_business_term('jewelry') == 'جواهرات'
    assert persian_business_term('dashboard') == 'داشبورد'
    
    # Test unknown term returns the key
    assert persian_business_term('unknown_term') == 'unknown_term'


def test_current_persian_date_tags():
    """Test current Persian date template tags."""
    from zargar.core.templatetags.persian_tags import current_persian_year, current_persian_date, current_persian_datetime
    
    # These should return Persian digits
    year = current_persian_year()
    assert any(char in year for char in "۰۱۲۳۴۵۶۷۸۹")
    assert len(year) == 4  # Should be 4-digit year
    
    date = current_persian_date()
    assert any(char in date for char in "۰۱۲۳۴۵۶۷۸۹")
    assert "/" in date  # Should have date separators
    
    datetime = current_persian_datetime()
    assert any(char in datetime for char in "۰۱۲۳۴۵۶۷۸۹")
    assert "/" in datetime and ":" in datetime  # Should have date and time separators


if __name__ == "__main__":
    pytest.main([__file__])