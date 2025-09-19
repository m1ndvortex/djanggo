"""
Persian calendar utilities for ZARGAR jewelry SaaS platform.
Provides comprehensive calendar conversion between Shamsi, Gregorian, and Hijri calendars.
"""
import jdatetime
from datetime import date, datetime, timedelta
from typing import Optional, Union, Tuple, Dict, Any
from django.utils.translation import gettext as _
import calendar
import hijri_converter


class PersianCalendarUtils:
    """
    Comprehensive Persian calendar utilities with conversion support.
    """
    
    # Persian month names
    PERSIAN_MONTHS = [
        'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
        'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
    ]
    
    # Persian weekday names
    PERSIAN_WEEKDAYS = [
        'شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه'
    ]
    
    # Hijri month names
    HIJRI_MONTHS = [
        'محرم', 'صفر', 'ربیع‌الاول', 'ربیع‌الثانی', 'جمادی‌الاول', 'جمادی‌الثانی',
        'رجب', 'شعبان', 'رمضان', 'شوال', 'ذی‌القعده', 'ذی‌الحجه'
    ]
    
    @classmethod
    def shamsi_to_gregorian(cls, year: int, month: int, day: int) -> date:
        """
        Convert Shamsi (Persian) date to Gregorian date.
        
        Args:
            year: Persian year (e.g., 1403)
            month: Persian month (1-12)
            day: Persian day (1-31)
            
        Returns:
            Gregorian date object
            
        Raises:
            ValueError: If the Persian date is invalid
        """
        try:
            persian_date = jdatetime.date(year, month, day)
            return persian_date.togregorian()
        except ValueError as e:
            raise ValueError(f"Invalid Persian date: {year}/{month}/{day} - {str(e)}")
    
    @classmethod
    def gregorian_to_shamsi(cls, gregorian_date: Union[date, datetime]) -> Tuple[int, int, int]:
        """
        Convert Gregorian date to Shamsi (Persian) date.
        
        Args:
            gregorian_date: Gregorian date or datetime object
            
        Returns:
            Tuple of (year, month, day) in Persian calendar
        """
        if isinstance(gregorian_date, datetime):
            gregorian_date = gregorian_date.date()
        
        persian_date = jdatetime.date.fromgregorian(date=gregorian_date)
        return persian_date.year, persian_date.month, persian_date.day
    
    @classmethod
    def shamsi_to_hijri(cls, year: int, month: int, day: int) -> Tuple[int, int, int]:
        """
        Convert Shamsi (Persian) date to Hijri date.
        
        Args:
            year: Persian year
            month: Persian month
            day: Persian day
            
        Returns:
            Tuple of (year, month, day) in Hijri calendar
        """
        # First convert to Gregorian, then to Hijri
        gregorian_date = cls.shamsi_to_gregorian(year, month, day)
        hijri_date = hijri_converter.Gregorian(
            gregorian_date.year, 
            gregorian_date.month, 
            gregorian_date.day
        ).to_hijri()
        
        return hijri_date.year, hijri_date.month, hijri_date.day
    
    @classmethod
    def hijri_to_shamsi(cls, year: int, month: int, day: int) -> Tuple[int, int, int]:
        """
        Convert Hijri date to Shamsi (Persian) date.
        
        Args:
            year: Hijri year
            month: Hijri month
            day: Hijri day
            
        Returns:
            Tuple of (year, month, day) in Persian calendar
        """
        # First convert to Gregorian, then to Persian
        gregorian_date = hijri_converter.Hijri(year, month, day).to_gregorian()
        gregorian_date_obj = date(gregorian_date.year, gregorian_date.month, gregorian_date.day)
        
        return cls.gregorian_to_shamsi(gregorian_date_obj)
    
    @classmethod
    def format_persian_date(cls, persian_date: Union[date, datetime, Tuple[int, int, int]], 
                          include_weekday: bool = False, 
                          format_style: str = 'full') -> str:
        """
        Format Persian date in various styles.
        
        Args:
            persian_date: Persian date as tuple (year, month, day) or date object
            include_weekday: Whether to include weekday name
            format_style: 'full', 'short', 'numeric'
            
        Returns:
            Formatted Persian date string
        """
        if isinstance(persian_date, (date, datetime)):
            year, month, day = cls.gregorian_to_shamsi(persian_date)
        else:
            year, month, day = persian_date
        
        if format_style == 'numeric':
            # Format with zero padding first, then convert to Persian digits
            formatted = f"{year:04d}/{month:02d}/{day:02d}"
            formatted = cls.to_persian_digits(formatted)
        elif format_style == 'short':
            month_name = cls.PERSIAN_MONTHS[month - 1]
            persian_day = cls.to_persian_digits(str(day))
            persian_year = cls.to_persian_digits(str(year))
            formatted = f"{persian_day} {month_name} {persian_year}"
        else:  # full
            month_name = cls.PERSIAN_MONTHS[month - 1]
            persian_day = cls.to_persian_digits(str(day))
            persian_year = cls.to_persian_digits(str(year))
            formatted = f"{persian_day} {month_name} {persian_year}"
        
        if include_weekday:
            # Calculate weekday
            gregorian_date = cls.shamsi_to_gregorian(year, month, day)
            weekday_index = gregorian_date.weekday()
            # Convert to Persian weekday (Saturday = 0)
            persian_weekday_index = (weekday_index + 2) % 7
            weekday_name = cls.PERSIAN_WEEKDAYS[persian_weekday_index]
            formatted = f"{weekday_name}، {formatted}"
        
        return formatted
    
    @classmethod
    def format_hijri_date(cls, hijri_date: Tuple[int, int, int], 
                         include_weekday: bool = False) -> str:
        """
        Format Hijri date in Persian.
        
        Args:
            hijri_date: Tuple of (year, month, day) in Hijri calendar
            include_weekday: Whether to include weekday name
            
        Returns:
            Formatted Hijri date string in Persian
        """
        year, month, day = hijri_date
        
        # Convert numbers to Persian digits
        persian_year = cls.to_persian_digits(str(year))
        persian_day = cls.to_persian_digits(str(day))
        
        month_name = cls.HIJRI_MONTHS[month - 1]
        formatted = f"{persian_day} {month_name} {persian_year} ه.ق"
        
        if include_weekday:
            # Convert to Gregorian to get weekday
            gregorian_date = hijri_converter.Hijri(year, month, day).to_gregorian()
            gregorian_date_obj = date(gregorian_date.year, gregorian_date.month, gregorian_date.day)
            weekday_index = gregorian_date_obj.weekday()
            persian_weekday_index = (weekday_index + 2) % 7
            weekday_name = cls.PERSIAN_WEEKDAYS[persian_weekday_index]
            formatted = f"{weekday_name}، {formatted}"
        
        return formatted
    
    @classmethod
    def get_current_persian_date(cls) -> Tuple[int, int, int]:
        """
        Get current date in Persian calendar.
        
        Returns:
            Tuple of (year, month, day) in Persian calendar
        """
        today = date.today()
        return cls.gregorian_to_shamsi(today)
    
    @classmethod
    def get_persian_fiscal_year(cls, persian_date: Optional[Tuple[int, int, int]] = None) -> Tuple[int, int]:
        """
        Get Persian fiscal year (Farvardin to Esfand).
        
        Args:
            persian_date: Persian date tuple, defaults to current date
            
        Returns:
            Tuple of (start_year, end_year) of fiscal year
        """
        if persian_date is None:
            persian_date = cls.get_current_persian_date()
        
        year, month, day = persian_date
        
        # Persian fiscal year starts from Farvardin (month 1)
        if month >= 1:
            return year, year
        else:
            # This shouldn't happen as months are 1-12, but just in case
            return year - 1, year - 1
    
    @classmethod
    def get_persian_month_days(cls, year: int, month: int) -> int:
        """
        Get number of days in a Persian month.
        
        Args:
            year: Persian year
            month: Persian month (1-12)
            
        Returns:
            Number of days in the month
        """
        try:
            # Create date for first day of next month, then subtract one day
            if month == 12:
                next_month_date = jdatetime.date(year + 1, 1, 1)
            else:
                next_month_date = jdatetime.date(year, month + 1, 1)
            
            last_day_date = next_month_date - timedelta(days=1)
            return last_day_date.day
        except ValueError:
            # Fallback to standard Persian calendar rules
            if month <= 6:
                return 31
            elif month <= 11:
                return 30
            else:  # month 12 (Esfand)
                return 30 if cls.is_persian_leap_year(year) else 29
    
    @classmethod
    def is_persian_leap_year(cls, year: int) -> bool:
        """
        Check if a Persian year is a leap year.
        
        Args:
            year: Persian year
            
        Returns:
            True if leap year, False otherwise
        """
        try:
            # Try to create Esfand 30 (day 30 of month 12)
            jdatetime.date(year, 12, 30)
            return True
        except ValueError:
            return False
    
    @classmethod
    def get_persian_holidays(cls, year: int) -> Dict[Tuple[int, int], str]:
        """
        Get Persian/Iranian holidays for a given year.
        
        Args:
            year: Persian year
            
        Returns:
            Dictionary mapping (month, day) tuples to holiday names
        """
        holidays = {
            # Fixed Persian holidays
            (1, 1): 'نوروز - جشن سال نو',
            (1, 2): 'عید نوروز',
            (1, 3): 'عید نوروز',
            (1, 4): 'عید نوروز',
            (1, 12): 'روز جمهوری اسلامی ایران',
            (1, 13): 'سیزده بدر',
            (3, 14): 'رحلت امام خمینی',
            (3, 15): 'قیام ۱۵ خرداد',
            (11, 22): 'پیروزی انقلاب اسلامی',
            (12, 29): 'روز ملی شدن صنعت نفت',
        }
        
        # Note: Religious holidays (based on Hijri calendar) would need 
        # separate calculation as they vary each year
        
        return holidays
    
    @classmethod
    def parse_persian_date_string(cls, date_string: str) -> Optional[Tuple[int, int, int]]:
        """
        Parse Persian date string in various formats.
        
        Args:
            date_string: Persian date string (e.g., "۱۴۰۳/۰۱/۰۱" or "۱ فروردین ۱۴۰۳")
            
        Returns:
            Tuple of (year, month, day) or None if parsing fails
        """
        if not date_string:
            return None
        
        # Convert Persian digits to English
        english_string = cls.to_english_digits(date_string.strip())
        
        # Try numeric format first (YYYY/MM/DD)
        if '/' in english_string:
            try:
                parts = english_string.split('/')
                if len(parts) == 3:
                    year, month, day = map(int, parts)
                    # Validate ranges
                    if 1300 <= year <= 1500 and 1 <= month <= 12 and 1 <= day <= 31:
                        return year, month, day
            except ValueError:
                pass
        
        # Try text format (DD MonthName YYYY)
        for i, month_name in enumerate(cls.PERSIAN_MONTHS, 1):
            if month_name in date_string:
                try:
                    # Extract day and year
                    parts = english_string.replace(month_name, '').split()
                    if len(parts) >= 2:
                        day = int(parts[0])
                        year = int(parts[-1])
                        if 1300 <= year <= 1500 and 1 <= day <= 31:
                            return year, i, day
                except (ValueError, IndexError):
                    continue
        
        return None
    
    @classmethod
    def to_persian_digits(cls, text: str) -> str:
        """
        Convert English digits to Persian digits.
        
        Args:
            text: Text containing English digits
            
        Returns:
            Text with Persian digits
        """
        english_digits = '0123456789'
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        
        for i, digit in enumerate(english_digits):
            text = text.replace(digit, persian_digits[i])
        
        return text
    
    @classmethod
    def to_english_digits(cls, text: str) -> str:
        """
        Convert Persian digits to English digits.
        
        Args:
            text: Text containing Persian digits
            
        Returns:
            Text with English digits
        """
        english_digits = '0123456789'
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        
        for i, digit in enumerate(persian_digits):
            text = text.replace(digit, english_digits[i])
        
        return text
    
    @classmethod
    def get_date_range_persian(cls, start_date: Tuple[int, int, int], 
                              end_date: Tuple[int, int, int]) -> list:
        """
        Generate list of Persian dates between start and end dates.
        
        Args:
            start_date: Start date tuple (year, month, day)
            end_date: End date tuple (year, month, day)
            
        Returns:
            List of Persian date tuples
        """
        dates = []
        
        # Convert to Gregorian for iteration
        start_gregorian = cls.shamsi_to_gregorian(*start_date)
        end_gregorian = cls.shamsi_to_gregorian(*end_date)
        
        current_date = start_gregorian
        while current_date <= end_gregorian:
            persian_date = cls.gregorian_to_shamsi(current_date)
            dates.append(persian_date)
            current_date += timedelta(days=1)
        
        return dates
    
    @classmethod
    def calculate_age_persian(cls, birth_date: Tuple[int, int, int], 
                            reference_date: Optional[Tuple[int, int, int]] = None) -> int:
        """
        Calculate age in Persian calendar.
        
        Args:
            birth_date: Birth date tuple (year, month, day)
            reference_date: Reference date, defaults to current date
            
        Returns:
            Age in years
        """
        if reference_date is None:
            reference_date = cls.get_current_persian_date()
        
        birth_year, birth_month, birth_day = birth_date
        ref_year, ref_month, ref_day = reference_date
        
        age = ref_year - birth_year
        
        # Adjust if birthday hasn't occurred this year
        if (ref_month, ref_day) < (birth_month, birth_day):
            age -= 1
        
        return age
    
    @classmethod
    def get_quarter_persian(cls, persian_date: Tuple[int, int, int]) -> int:
        """
        Get Persian fiscal quarter (1-4) for a given date.
        
        Args:
            persian_date: Persian date tuple
            
        Returns:
            Quarter number (1-4)
        """
        year, month, day = persian_date
        
        if month <= 3:
            return 1
        elif month <= 6:
            return 2
        elif month <= 9:
            return 3
        else:
            return 4
    
    @classmethod
    def format_date_for_api(cls, persian_date: Tuple[int, int, int]) -> str:
        """
        Format Persian date for API responses (ISO-like format).
        
        Args:
            persian_date: Persian date tuple
            
        Returns:
            Formatted date string (YYYY-MM-DD)
        """
        year, month, day = persian_date
        return f"{year:04d}-{month:02d}-{day:02d}"
    
    @classmethod
    def validate_persian_date(cls, year: int, month: int, day: int) -> bool:
        """
        Validate Persian date values.
        
        Args:
            year: Persian year
            month: Persian month
            day: Persian day
            
        Returns:
            True if valid, False otherwise
        """
        try:
            jdatetime.date(year, month, day)
            return True
        except ValueError:
            return False


class PersianDateRange:
    """
    Helper class for working with Persian date ranges.
    """
    
    def __init__(self, start_date: Tuple[int, int, int], end_date: Tuple[int, int, int]):
        self.start_date = start_date
        self.end_date = end_date
        self.utils = PersianCalendarUtils()
    
    def __iter__(self):
        """Iterate over dates in the range."""
        return iter(self.utils.get_date_range_persian(self.start_date, self.end_date))
    
    def __len__(self):
        """Get number of days in the range."""
        start_gregorian = self.utils.shamsi_to_gregorian(*self.start_date)
        end_gregorian = self.utils.shamsi_to_gregorian(*self.end_date)
        return (end_gregorian - start_gregorian).days + 1
    
    def __contains__(self, date_tuple: Tuple[int, int, int]):
        """Check if a date is in the range."""
        return self.start_date <= date_tuple <= self.end_date
    
    def format_range(self, format_style: str = 'full') -> str:
        """Format the date range as a string."""
        start_formatted = self.utils.format_persian_date(self.start_date, format_style=format_style)
        end_formatted = self.utils.format_persian_date(self.end_date, format_style=format_style)
        return f"{start_formatted} تا {end_formatted}"