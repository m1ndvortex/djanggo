"""
Unit tests for Persian calendar utilities only (no Django dependencies).
Tests core calendar conversion functionality.
"""
import pytest
from datetime import date, datetime
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the calendar utils directly
from zargar.core.calendar_utils import PersianCalendarUtils, PersianDateRange


class TestPersianCalendarUtils:
    """Test Persian calendar utility functions."""
    
    def test_shamsi_to_gregorian_conversion(self):
        """Test conversion from Shamsi to Gregorian dates."""
        # Test known date conversions
        test_cases = [
            # (Persian year, month, day) -> Expected Gregorian date
            ((1403, 1, 1), date(2024, 3, 20)),  # Nowruz 1403
            ((1403, 6, 31), date(2024, 9, 21)), # End of summer 1403
            ((1400, 1, 1), date(2021, 3, 21)),  # Nowruz 1400
        ]
        
        for persian_date, expected_gregorian in test_cases:
            year, month, day = persian_date
            result = PersianCalendarUtils.shamsi_to_gregorian(year, month, day)
            assert result == expected_gregorian, f"Failed for Persian date {persian_date}"
    
    def test_gregorian_to_shamsi_conversion(self):
        """Test conversion from Gregorian to Shamsi dates."""
        test_cases = [
            # Gregorian date -> Expected (Persian year, month, day)
            (date(2024, 3, 20), (1403, 1, 1)),   # Nowruz 1403
            (date(2024, 9, 21), (1403, 6, 31)),  # End of summer 1403
            (date(2021, 3, 21), (1400, 1, 1)),   # Nowruz 1400
        ]
        
        for gregorian_date, expected_persian in test_cases:
            result = PersianCalendarUtils.gregorian_to_shamsi(gregorian_date)
            assert result == expected_persian, f"Failed for Gregorian date {gregorian_date}"
    
    def test_shamsi_to_hijri_conversion(self):
        """Test conversion from Shamsi to Hijri dates."""
        # Test a known conversion
        persian_date = (1403, 1, 1)  # Nowruz 1403
        hijri_result = PersianCalendarUtils.shamsi_to_hijri(*persian_date)
        
        # Verify it's a valid Hijri date tuple
        assert isinstance(hijri_result, tuple)
        assert len(hijri_result) == 3
        
        hijri_year, hijri_month, hijri_day = hijri_result
        assert isinstance(hijri_year, int)
        assert isinstance(hijri_month, int)
        assert isinstance(hijri_day, int)
        
        # Verify reasonable ranges
        assert 1400 <= hijri_year <= 1500
        assert 1 <= hijri_month <= 12
        assert 1 <= hijri_day <= 31
    
    def test_format_persian_date(self):
        """Test Persian date formatting in various styles."""
        test_date = (1403, 1, 15)  # 15 Farvardin 1403
        
        # Test numeric format
        numeric_result = PersianCalendarUtils.format_persian_date(
            test_date, format_style='numeric'
        )
        assert numeric_result == '۱۴۰۳/۰۱/۱۵'
        
        # Test full format
        full_result = PersianCalendarUtils.format_persian_date(
            test_date, format_style='full'
        )
        assert full_result == '۱۵ فروردین ۱۴۰۳'
    
    def test_get_persian_month_days(self):
        """Test getting number of days in Persian months."""
        # Test first 6 months (31 days each)
        for month in range(1, 7):
            days = PersianCalendarUtils.get_persian_month_days(1403, month)
            assert days == 31, f"Month {month} should have 31 days"
        
        # Test months 7-11 (30 days each)
        for month in range(7, 12):
            days = PersianCalendarUtils.get_persian_month_days(1403, month)
            assert days == 30, f"Month {month} should have 30 days"
        
        # Test Esfand (month 12) - varies by leap year
        esfand_days = PersianCalendarUtils.get_persian_month_days(1403, 12)
        assert esfand_days in [29, 30], "Esfand should have 29 or 30 days"
    
    def test_is_persian_leap_year(self):
        """Test Persian leap year detection."""
        # Test known leap years and non-leap years
        test_cases = [
            (1403, True),   # Leap year
            (1404, False),  # Non-leap year
            (1400, False),  # Non-leap year
            (1401, False),  # Non-leap year
        ]
        
        for year, expected_leap in test_cases:
            result = PersianCalendarUtils.is_persian_leap_year(year)
            assert result == expected_leap, f"Year {year} leap status incorrect"
    
    def test_parse_persian_date_string(self):
        """Test parsing Persian date strings."""
        test_cases = [
            ('۱۴۰۳/۰۱/۰۱', (1403, 1, 1)),
            ('1403/01/01', (1403, 1, 1)),
            ('۱۴۰۳/۱/۱', (1403, 1, 1)),
            ('1403/1/1', (1403, 1, 1)),
        ]
        
        for date_string, expected in test_cases:
            result = PersianCalendarUtils.parse_persian_date_string(date_string)
            assert result == expected, f"Failed to parse '{date_string}'"
        
        # Test invalid strings
        invalid_cases = ['', 'invalid', '1403/13/01', '1403/01/32', '1200/01/01']
        for invalid_string in invalid_cases:
            result = PersianCalendarUtils.parse_persian_date_string(invalid_string)
            assert result is None, f"Should not parse '{invalid_string}'"
    
    def test_digit_conversion(self):
        """Test Persian and English digit conversion."""
        # Test Persian to English
        persian_text = '۱۲۳۴۵۶۷۸۹۰'
        english_result = PersianCalendarUtils.to_english_digits(persian_text)
        assert english_result == '1234567890'
        
        # Test English to Persian
        english_text = '1234567890'
        persian_result = PersianCalendarUtils.to_persian_digits(english_text)
        assert persian_result == '۱۲۳۴۵۶۷۸۹۰'
        
        # Test mixed text
        mixed_text = 'سال ۱۴۰۳ ماه ۱'
        english_mixed = PersianCalendarUtils.to_english_digits(mixed_text)
        assert english_mixed == 'سال 1403 ماه 1'
    
    def test_validate_persian_date(self):
        """Test Persian date validation."""
        # Valid dates
        valid_dates = [
            (1403, 1, 1),
            (1403, 6, 31),
            (1403, 12, 29),
            (1403, 12, 30),  # Leap year
        ]
        
        for year, month, day in valid_dates:
            result = PersianCalendarUtils.validate_persian_date(year, month, day)
            assert result == True, f"Date {year}/{month}/{day} should be valid"
        
        # Invalid dates
        invalid_dates = [
            (1403, 13, 1),   # Invalid month
            (1403, 1, 32),   # Invalid day
            (1404, 12, 30),  # Invalid day for non-leap year
            (1403, 0, 1),    # Invalid month (0)
        ]
        
        for year, month, day in invalid_dates:
            result = PersianCalendarUtils.validate_persian_date(year, month, day)
            assert result == False, f"Date {year}/{month}/{day} should be invalid"


class TestPersianDateRange:
    """Test PersianDateRange helper class."""
    
    def test_date_range_iteration(self):
        """Test iterating over Persian date range."""
        start_date = (1403, 1, 1)
        end_date = (1403, 1, 3)
        
        date_range = PersianDateRange(start_date, end_date)
        dates = list(date_range)
        
        expected_dates = [
            (1403, 1, 1),
            (1403, 1, 2),
            (1403, 1, 3),
        ]
        
        assert dates == expected_dates
    
    def test_date_range_length(self):
        """Test Persian date range length calculation."""
        start_date = (1403, 1, 1)
        end_date = (1403, 1, 5)
        
        date_range = PersianDateRange(start_date, end_date)
        assert len(date_range) == 5
    
    def test_date_range_contains(self):
        """Test checking if date is in range."""
        start_date = (1403, 1, 1)
        end_date = (1403, 1, 5)
        
        date_range = PersianDateRange(start_date, end_date)
        
        assert (1403, 1, 3) in date_range
        assert (1403, 1, 6) not in date_range
        assert (1402, 12, 29) not in date_range


if __name__ == '__main__':
    pytest.main([__file__, '-v'])