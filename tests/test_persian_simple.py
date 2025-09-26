"""
Simple tests for Persian localization functionality.
"""
import pytest
import os
import sys
import django
from django.conf import settings

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
    )
    django.setup()


def test_persian_digit_conversion():
    """Test basic Persian digit conversion."""
    from zargar.core.templatetags.persian_tags import persian_number
    
    # Test basic conversion
    assert persian_number("123") == "۱۲۳"
    assert persian_number("0") == "۰"
    assert persian_number("9876543210") == "۹۸۷۶۵۴۳۲۱۰"
    assert persian_number("") == ""
    assert persian_number(None) == ""


def test_persian_currency_formatting():
    """Test Persian currency formatting."""
    from zargar.core.templatetags.persian_tags import persian_currency
    
    # Test currency formatting
    result = persian_currency(1000)
    assert "۱٬۰۰۰" in result
    assert "تومان" in result
    
    result = persian_currency(1234567)
    assert "۱٬۲۳۴٬۵۶۷" in result
    assert "تومان" in result
    
    assert persian_currency(0) == "۰ تومان"
    assert persian_currency("") == ""
    assert persian_currency(None) == ""


def test_persian_weight_formatting():
    """Test Persian weight formatting."""
    from zargar.core.templatetags.persian_tags import persian_weight
    
    result = persian_weight(10.500)
    assert "۱۰٫۵۰۰" in result
    assert "گرم" in result
    
    result = persian_weight(1.234)
    assert "۱٫۲۳۴" in result
    assert "گرم" in result
    
    assert persian_weight("") == ""
    assert persian_weight(None) == ""


def test_karat_display():
    """Test karat display formatting."""
    from zargar.core.templatetags.persian_tags import karat_display
    
    assert karat_display(18) == "عیار ۱۸"
    assert karat_display(21) == "عیار ۲۱"
    assert karat_display(24) == "عیار ۲۴"
    assert karat_display("") == ""
    assert karat_display(None) == ""


def test_mithqal_conversion():
    """Test conversion from grams to Mithqal."""
    from zargar.core.templatetags.persian_tags import to_mithqal
    
    # 1 Mithqal = 4.608 grams
    result = to_mithqal(4.608)
    assert "۱٫۰۰۰" in result
    assert "مثقال" in result
    
    result = to_mithqal(9.216)  # 2 Mithqal
    assert "۲٫۰۰۰" in result
    assert "مثقال" in result


def test_soot_conversion():
    """Test conversion from grams to Soot."""
    from zargar.core.templatetags.persian_tags import to_soot
    
    # 1 Soot = 3.456 grams
    result = to_soot(3.456)
    assert "۱٫۰۰۰" in result
    assert "سوت" in result
    
    result = to_soot(6.912)  # 2 Soot
    assert "۲٫۰۰۰" in result
    assert "سوت" in result


def test_percentage_persian():
    """Test Persian percentage formatting."""
    from zargar.core.templatetags.persian_tags import percentage_persian
    
    assert percentage_persian(25.5) == "۲۵٫۵%"
    assert percentage_persian(100) == "۱۰۰٫۰%"
    assert percentage_persian(0) == "۰٫۰%"


if __name__ == "__main__":
    pytest.main([__file__])