#!/usr/bin/env python
"""
Demonstration script for Persian calendar system integration.
Shows calendar conversion utilities, model fields, and widgets in action.
"""
import os
import sys
import django
from datetime import date, datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from zargar.core.calendar_utils import PersianCalendarUtils, PersianDateRange
from zargar.core.fields import PersianDateField as PersianDateFormField
from zargar.core.widgets import PersianDateWidget


def demo_calendar_conversions():
    """Demonstrate calendar conversion utilities."""
    print("=" * 60)
    print("PERSIAN CALENDAR SYSTEM DEMONSTRATION")
    print("=" * 60)
    
    print("\n1. CALENDAR CONVERSIONS")
    print("-" * 30)
    
    # Shamsi to Gregorian
    print("Shamsi to Gregorian conversions:")
    test_dates = [
        (1403, 1, 1),   # Nowruz 1403
        (1403, 6, 31),  # End of summer
        (1403, 12, 29), # End of year
    ]
    
    for persian_date in test_dates:
        year, month, day = persian_date
        gregorian = PersianCalendarUtils.shamsi_to_gregorian(year, month, day)
        formatted_persian = PersianCalendarUtils.format_persian_date(persian_date, format_style='full')
        print(f"  {formatted_persian} → {gregorian}")
    
    # Gregorian to Shamsi
    print("\nGregorian to Shamsi conversions:")
    gregorian_dates = [
        date(2024, 3, 20),  # Nowruz 1403
        date(2024, 9, 21),  # Autumn equinox
        date(2024, 12, 21), # Winter solstice
    ]
    
    for gregorian_date in gregorian_dates:
        persian_date = PersianCalendarUtils.gregorian_to_shamsi(gregorian_date)
        formatted_persian = PersianCalendarUtils.format_persian_date(persian_date, format_style='full')
        print(f"  {gregorian_date} → {formatted_persian}")
    
    # Shamsi to Hijri
    print("\nShamsi to Hijri conversions:")
    for persian_date in test_dates[:2]:  # Just first two for brevity
        hijri_date = PersianCalendarUtils.shamsi_to_hijri(*persian_date)
        formatted_persian = PersianCalendarUtils.format_persian_date(persian_date, format_style='full')
        formatted_hijri = PersianCalendarUtils.format_hijri_date(hijri_date)
        print(f"  {formatted_persian} → {formatted_hijri}")


def demo_date_formatting():
    """Demonstrate Persian date formatting options."""
    print("\n2. DATE FORMATTING")
    print("-" * 30)
    
    test_date = (1403, 1, 15)  # 15 Farvardin 1403
    
    print("Different formatting styles:")
    print(f"  Numeric: {PersianCalendarUtils.format_persian_date(test_date, format_style='numeric')}")
    print(f"  Short:   {PersianCalendarUtils.format_persian_date(test_date, format_style='short')}")
    print(f"  Full:    {PersianCalendarUtils.format_persian_date(test_date, format_style='full')}")
    print(f"  With weekday: {PersianCalendarUtils.format_persian_date(test_date, include_weekday=True, format_style='full')}")


def demo_calendar_utilities():
    """Demonstrate calendar utility functions."""
    print("\n3. CALENDAR UTILITIES")
    print("-" * 30)
    
    # Current Persian date
    current_persian = PersianCalendarUtils.get_current_persian_date()
    current_formatted = PersianCalendarUtils.format_persian_date(current_persian, format_style='full')
    print(f"Current Persian date: {current_formatted}")
    
    # Leap year detection
    print("\nLeap year detection:")
    test_years = [1400, 1401, 1402, 1403, 1404, 1405]
    for year in test_years:
        is_leap = PersianCalendarUtils.is_persian_leap_year(year)
        persian_year = PersianCalendarUtils.to_persian_digits(str(year))
        status = "کبیسه" if is_leap else "عادی"
        print(f"  {persian_year}: {status}")
    
    # Month days
    print("\nDays in Persian months (year 1403):")
    for month in range(1, 13):
        days = PersianCalendarUtils.get_persian_month_days(1403, month)
        month_name = PersianCalendarUtils.PERSIAN_MONTHS[month - 1]
        persian_days = PersianCalendarUtils.to_persian_digits(str(days))
        print(f"  {month_name}: {persian_days} روز")
    
    # Fiscal year and quarters
    test_date = (1403, 6, 15)
    fiscal_year = PersianCalendarUtils.get_persian_fiscal_year(test_date)
    quarter = PersianCalendarUtils.get_quarter_persian(test_date)
    print(f"\nFiscal year for {PersianCalendarUtils.format_persian_date(test_date)}: {fiscal_year[0]}")
    print(f"Quarter: {quarter}")


def demo_persian_holidays():
    """Demonstrate Persian holidays."""
    print("\n4. PERSIAN HOLIDAYS")
    print("-" * 30)
    
    holidays = PersianCalendarUtils.get_persian_holidays(1403)
    print("Persian holidays for 1403:")
    
    for (month, day), holiday_name in sorted(holidays.items()):
        date_str = PersianCalendarUtils.format_persian_date((1403, month, day), format_style='short')
        print(f"  {date_str}: {holiday_name}")


def demo_date_parsing():
    """Demonstrate Persian date string parsing."""
    print("\n5. DATE STRING PARSING")
    print("-" * 30)
    
    test_strings = [
        '۱۴۰۳/۰۱/۰۱',
        '1403/01/01',
        '۱۴۰۳/۱/۱',
        '1403/1/1',
        'invalid_date',
        '۱۴۰۳/۱۳/۰۱',  # Invalid month
    ]
    
    print("Parsing Persian date strings:")
    for date_string in test_strings:
        result = PersianCalendarUtils.parse_persian_date_string(date_string)
        if result:
            formatted = PersianCalendarUtils.format_persian_date(result, format_style='full')
            print(f"  '{date_string}' → {formatted}")
        else:
            print(f"  '{date_string}' → Invalid")


def demo_date_ranges():
    """Demonstrate Persian date ranges."""
    print("\n6. DATE RANGES")
    print("-" * 30)
    
    start_date = (1403, 1, 1)
    end_date = (1403, 1, 7)
    
    date_range = PersianDateRange(start_date, end_date)
    
    print(f"Date range: {date_range.format_range(format_style='short')}")
    print(f"Length: {PersianCalendarUtils.to_persian_digits(str(len(date_range)))} days")
    
    print("Dates in range:")
    for i, date_tuple in enumerate(date_range):
        if i < 5:  # Show first 5 dates
            formatted = PersianCalendarUtils.format_persian_date(date_tuple, format_style='short')
            print(f"  {formatted}")
        elif i == 5:
            print("  ...")
            break
    
    # Test containment
    test_date = (1403, 1, 3)
    is_in_range = test_date in date_range
    print(f"\n{PersianCalendarUtils.format_persian_date(test_date)} in range: {'Yes' if is_in_range else 'No'}")


def demo_age_calculation():
    """Demonstrate age calculation in Persian calendar."""
    print("\n7. AGE CALCULATION")
    print("-" * 30)
    
    birth_date = (1380, 5, 15)  # Born in 1380
    current_date = PersianCalendarUtils.get_current_persian_date()
    
    age = PersianCalendarUtils.calculate_age_persian(birth_date, current_date)
    
    birth_formatted = PersianCalendarUtils.format_persian_date(birth_date, format_style='full')
    current_formatted = PersianCalendarUtils.format_persian_date(current_date, format_style='full')
    persian_age = PersianCalendarUtils.to_persian_digits(str(age))
    
    print(f"Birth date: {birth_formatted}")
    print(f"Current date: {current_formatted}")
    print(f"Age: {persian_age} سال")


def demo_digit_conversion():
    """Demonstrate Persian and English digit conversion."""
    print("\n8. DIGIT CONVERSION")
    print("-" * 30)
    
    test_texts = [
        "سال ۱۴۰۳ ماه ۱",
        "قیمت: ۱۰۰٬۰۰۰ تومان",
        "وزن: ۱۲٫۵ گرم",
        "Year 2024 Month 3",
    ]
    
    print("Persian ↔ English digit conversion:")
    for text in test_texts:
        english_version = PersianCalendarUtils.to_english_digits(text)
        persian_version = PersianCalendarUtils.to_persian_digits(english_version)
        print(f"  Original: {text}")
        print(f"  English:  {english_version}")
        print(f"  Persian:  {persian_version}")
        print()


def demo_form_field_integration():
    """Demonstrate Persian date form field integration."""
    print("\n9. FORM FIELD INTEGRATION")
    print("-" * 30)
    
    from django.forms import Form
    
    class TestForm(Form):
        persian_date = PersianDateFormField(
            widget=PersianDateWidget(),
            help_text="تاریخ را به صورت شمسی وارد کنید"
        )
    
    # Test form with Persian date input
    form_data = {'persian_date': '۱۴۰۳/۰۱/۰۱'}
    form = TestForm(data=form_data)
    
    print("Form validation test:")
    print(f"  Input: {form_data['persian_date']}")
    print(f"  Valid: {'Yes' if form.is_valid() else 'No'}")
    
    if form.is_valid():
        cleaned_date = form.cleaned_data['persian_date']
        print(f"  Cleaned value: {cleaned_date} (Gregorian)")
        
        # Convert back to Persian for display
        persian_display = PersianCalendarUtils.gregorian_to_shamsi(cleaned_date)
        formatted_display = PersianCalendarUtils.format_persian_date(persian_display, format_style='full')
        print(f"  Display value: {formatted_display}")
    else:
        print(f"  Errors: {form.errors}")


def main():
    """Run all demonstrations."""
    try:
        demo_calendar_conversions()
        demo_date_formatting()
        demo_calendar_utilities()
        demo_persian_holidays()
        demo_date_parsing()
        demo_date_ranges()
        demo_age_calculation()
        demo_digit_conversion()
        demo_form_field_integration()
        
        print("\n" + "=" * 60)
        print("PERSIAN CALENDAR SYSTEM DEMONSTRATION COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()