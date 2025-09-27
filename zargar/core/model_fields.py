"""
Custom model fields for Persian calendar support in ZARGAR jewelry SaaS platform.
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import date, datetime
from typing import Optional, Tuple, Any
import jdatetime

from .calendar_utils import PersianCalendarUtils
from .widgets import PersianDateWidget, PersianDateTimeWidget


class PersianDateField(models.DateField):
    """
    Custom model field for Persian (Shamsi) dates with automatic conversion.
    
    This field stores dates in Gregorian format in the database but provides
    Persian calendar interface for input/output operations.
    """
    
    description = _("Persian date field with Shamsi calendar support")
    
    def __init__(self, *args, **kwargs):
        # Set default widget for forms
        kwargs.setdefault('help_text', _('تاریخ را به صورت شمسی وارد کنید'))
        super().__init__(*args, **kwargs)
    
    def formfield(self, **kwargs):
        """Return a form field for this model field."""
        from .fields import PersianDateField as PersianDateFormField
        
        defaults = {
            'form_class': PersianDateFormField,
            'widget': PersianDateWidget,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)
    
    def to_python(self, value):
        """Convert value to Python date object."""
        if value is None:
            return value
        
        if isinstance(value, date):
            return value
        
        if isinstance(value, datetime):
            return value.date()
        
        # If it's a string, try to parse as Persian date
        if isinstance(value, str):
            try:
                parsed_date = PersianCalendarUtils.parse_persian_date_string(value)
                if parsed_date:
                    year, month, day = parsed_date
                    return PersianCalendarUtils.shamsi_to_gregorian(year, month, day)
            except (ValueError, TypeError):
                pass
        
        # Fall back to parent implementation
        return super().to_python(value)
    
    def get_prep_value(self, value):
        """Prepare value for database storage."""
        value = super().get_prep_value(value)
        if value is None:
            return value
        
        # Ensure we're storing a proper date object
        if isinstance(value, datetime):
            return value.date()
        
        return value
    
    def value_to_string(self, obj):
        """Convert field value to string for serialization."""
        value = self.value_from_object(obj)
        if value is None:
            return ''
        
        # Convert to Persian format for display
        try:
            persian_date = PersianCalendarUtils.gregorian_to_shamsi(value)
            return PersianCalendarUtils.format_persian_date(persian_date, format_style='numeric')
        except (ValueError, TypeError):
            return str(value)
    
    def get_persian_date(self, obj) -> Optional[Tuple[int, int, int]]:
        """
        Get the Persian date tuple for this field value.
        
        Args:
            obj: Model instance
            
        Returns:
            Tuple of (year, month, day) in Persian calendar or None
        """
        value = self.value_from_object(obj)
        if value is None:
            return None
        
        try:
            return PersianCalendarUtils.gregorian_to_shamsi(value)
        except (ValueError, TypeError):
            return None
    
    def get_formatted_persian_date(self, obj, format_style: str = 'full', 
                                  include_weekday: bool = False) -> str:
        """
        Get formatted Persian date string for this field value.
        
        Args:
            obj: Model instance
            format_style: 'full', 'short', or 'numeric'
            include_weekday: Whether to include weekday name
            
        Returns:
            Formatted Persian date string
        """
        persian_date = self.get_persian_date(obj)
        if persian_date is None:
            return ''
        
        return PersianCalendarUtils.format_persian_date(
            persian_date, 
            include_weekday=include_weekday,
            format_style=format_style
        )


class PersianDateTimeField(models.DateTimeField):
    """
    Custom model field for Persian (Shamsi) datetimes with automatic conversion.
    
    This field stores datetimes in Gregorian format in the database but provides
    Persian calendar interface for input/output operations.
    """
    
    description = _("Persian datetime field with Shamsi calendar support")
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('help_text', _('تاریخ و زمان را به صورت شمسی وارد کنید'))
        super().__init__(*args, **kwargs)
    
    def formfield(self, **kwargs):
        """Return a form field for this model field."""
        from .fields import PersianDateTimeField as PersianDateTimeFormField
        
        defaults = {
            'form_class': PersianDateTimeFormField,
            'widget': PersianDateTimeWidget,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)
    
    def to_python(self, value):
        """Convert value to Python datetime object."""
        if value is None:
            return value
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        
        # If it's a string, try to parse as Persian datetime
        if isinstance(value, str):
            try:
                # Try to parse Persian datetime format
                if ' - ' in value:
                    date_part, time_part = value.split(' - ')
                    parsed_date = PersianCalendarUtils.parse_persian_date_string(date_part)
                    
                    if parsed_date:
                        year, month, day = parsed_date
                        gregorian_date = PersianCalendarUtils.shamsi_to_gregorian(year, month, day)
                        
                        # Parse time part
                        time_part = PersianCalendarUtils.to_english_digits(time_part)
                        if ':' in time_part:
                            hour, minute = map(int, time_part.split(':'))
                            return datetime.combine(gregorian_date, datetime.min.time().replace(hour=hour, minute=minute))
            except (ValueError, TypeError):
                pass
        
        # Fall back to parent implementation
        return super().to_python(value)
    
    def value_to_string(self, obj):
        """Convert field value to string for serialization."""
        value = self.value_from_object(obj)
        if value is None:
            return ''
        
        # Convert to Persian format for display
        try:
            persian_date = PersianCalendarUtils.gregorian_to_shamsi(value.date())
            date_str = PersianCalendarUtils.format_persian_date(persian_date, format_style='numeric')
            time_str = PersianCalendarUtils.to_persian_digits(value.strftime('%H:%M'))
            return f"{date_str} - {time_str}"
        except (ValueError, TypeError):
            return str(value)
    
    def get_persian_datetime(self, obj) -> Optional[Tuple[int, int, int, int, int]]:
        """
        Get the Persian datetime tuple for this field value.
        
        Args:
            obj: Model instance
            
        Returns:
            Tuple of (year, month, day, hour, minute) in Persian calendar or None
        """
        value = self.value_from_object(obj)
        if value is None:
            return None
        
        try:
            year, month, day = PersianCalendarUtils.gregorian_to_shamsi(value.date())
            return year, month, day, value.hour, value.minute
        except (ValueError, TypeError):
            return None
    
    def get_formatted_persian_datetime(self, obj, format_style: str = 'full', 
                                     include_weekday: bool = False) -> str:
        """
        Get formatted Persian datetime string for this field value.
        
        Args:
            obj: Model instance
            format_style: 'full', 'short', or 'numeric'
            include_weekday: Whether to include weekday name
            
        Returns:
            Formatted Persian datetime string
        """
        persian_datetime = self.get_persian_datetime(obj)
        if persian_datetime is None:
            return ''
        
        year, month, day, hour, minute = persian_datetime
        date_str = PersianCalendarUtils.format_persian_date(
            (year, month, day), 
            include_weekday=include_weekday,
            format_style=format_style
        )
        time_str = PersianCalendarUtils.to_persian_digits(f"{hour:02d}:{minute:02d}")
        
        return f"{date_str} - {time_str}"


class PersianFiscalYearField(models.IntegerField):
    """
    Custom field for Persian fiscal years.
    
    Stores the Persian year and provides utilities for fiscal year operations.
    """
    
    description = _("Persian fiscal year field")
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('help_text', _('سال مالی شمسی'))
        # Set reasonable bounds for Persian years
        kwargs.setdefault('validators', [])
        super().__init__(*args, **kwargs)
    
    def validate(self, value, model_instance):
        """Validate Persian fiscal year."""
        super().validate(value, model_instance)
        
        if value is not None:
            if not (1300 <= value <= 1500):
                raise ValidationError(
                    _('سال مالی باید بین ۱۳۰۰ تا ۱۵۰۰ باشد.'),
                    code='invalid_fiscal_year'
                )
    
    def get_fiscal_year_start_date(self, obj) -> Optional[date]:
        """
        Get the start date of the fiscal year (1st Farvardin).
        
        Args:
            obj: Model instance
            
        Returns:
            Gregorian date object for start of fiscal year
        """
        value = self.value_from_object(obj)
        if value is None:
            return None
        
        try:
            return PersianCalendarUtils.shamsi_to_gregorian(value, 1, 1)
        except (ValueError, TypeError):
            return None
    
    def get_fiscal_year_end_date(self, obj) -> Optional[date]:
        """
        Get the end date of the fiscal year (29th or 30th Esfand).
        
        Args:
            obj: Model instance
            
        Returns:
            Gregorian date object for end of fiscal year
        """
        value = self.value_from_object(obj)
        if value is None:
            return None
        
        try:
            # Get last day of Esfand (month 12)
            last_day = PersianCalendarUtils.get_persian_month_days(value, 12)
            return PersianCalendarUtils.shamsi_to_gregorian(value, 12, last_day)
        except (ValueError, TypeError):
            return None
    
    def get_current_fiscal_year(self) -> int:
        """
        Get current Persian fiscal year.
        
        Returns:
            Current Persian fiscal year
        """
        current_persian = PersianCalendarUtils.get_current_persian_date()
        return current_persian[0]  # Return year
    
    def value_to_string(self, obj):
        """Convert field value to string for serialization."""
        value = self.value_from_object(obj)
        if value is None:
            return ''
        
        return PersianCalendarUtils.to_persian_digits(str(value))


class PersianQuarterField(models.IntegerField):
    """
    Custom field for Persian fiscal quarters (1-4).
    """
    
    description = _("Persian fiscal quarter field")
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('help_text', _('فصل مالی (۱-۴)'))
        kwargs.setdefault('choices', [
            (1, _('فصل اول (فروردین - خرداد)')),
            (2, _('فصل دوم (تیر - شهریور)')),
            (3, _('فصل سوم (مهر - آذر)')),
            (4, _('فصل چهارم (دی - اسفند)')),
        ])
        super().__init__(*args, **kwargs)
    
    def validate(self, value, model_instance):
        """Validate quarter value."""
        super().validate(value, model_instance)
        
        if value is not None and not (1 <= value <= 4):
            raise ValidationError(
                _('فصل باید بین ۱ تا ۴ باشد.'),
                code='invalid_quarter'
            )
    
    def get_quarter_months(self, obj) -> Optional[Tuple[int, int, int]]:
        """
        Get the months included in this quarter.
        
        Args:
            obj: Model instance
            
        Returns:
            Tuple of (start_month, middle_month, end_month) or None
        """
        value = self.value_from_object(obj)
        if value is None:
            return None
        
        quarter_months = {
            1: (1, 2, 3),    # فروردین - خرداد
            2: (4, 5, 6),    # تیر - شهریور
            3: (7, 8, 9),    # مهر - آذر
            4: (10, 11, 12), # دی - اسفند
        }
        
        return quarter_months.get(value)
    
    def get_quarter_name(self, obj) -> str:
        """
        Get the Persian name of the quarter.
        
        Args:
            obj: Model instance
            
        Returns:
            Persian quarter name
        """
        value = self.value_from_object(obj)
        if value is None:
            return ''
        
        quarter_names = {
            1: 'فصل اول (فروردین - خرداد)',
            2: 'فصل دوم (تیر - شهریور)',
            3: 'فصل سوم (مهر - آذر)',
            4: 'فصل چهارم (دی - اسفند)',
        }
        
        return quarter_names.get(value, '')
    
    def value_to_string(self, obj):
        """Convert field value to string for serialization."""
        value = self.value_from_object(obj)
        if value is None:
            return ''
        
        return PersianCalendarUtils.to_persian_digits(str(value))


# Register custom fields for migrations
try:
    from django.db.migrations.writer import MigrationWriter
    from django.db.migrations.serializer import BaseSerializer
    
    # Custom serializer classes for Persian fields
    class PersianDateFieldSerializer(BaseSerializer):
        @staticmethod
        def serialize(field):
            return (
                "zargar.core.model_fields.PersianDateField",
                [],
                {
                    "help_text": repr(field.help_text),
                    "null": field.null,
                    "blank": field.blank,
                }
            )
    
    class PersianDateTimeFieldSerializer(BaseSerializer):
        @staticmethod
        def serialize(field):
            return (
                "zargar.core.model_fields.PersianDateTimeField",
                [],
                {
                    "help_text": repr(field.help_text),
                    "null": field.null,
                    "blank": field.blank,
                }
            )
    
    class PersianFiscalYearFieldSerializer(BaseSerializer):
        @staticmethod
        def serialize(field):
            return (
                "zargar.core.model_fields.PersianFiscalYearField",
                [],
                {
                    "help_text": repr(field.help_text),
                    "null": field.null,
                    "blank": field.blank,
                }
            )
    
    class PersianQuarterFieldSerializer(BaseSerializer):
        @staticmethod
        def serialize(field):
            return (
                "zargar.core.model_fields.PersianQuarterField",
                [],
                {
                    "help_text": repr(field.help_text),
                    "null": field.null,
                    "blank": field.blank,
                    "choices": field.choices,
                }
            )
    
    # Register serializers
    MigrationWriter.register_serializer(PersianDateField, PersianDateFieldSerializer)
    MigrationWriter.register_serializer(PersianDateTimeField, PersianDateTimeFieldSerializer)
    MigrationWriter.register_serializer(PersianFiscalYearField, PersianFiscalYearFieldSerializer)
    MigrationWriter.register_serializer(PersianQuarterField, PersianQuarterFieldSerializer)
    
except ImportError:
    # Migration serializers not available during testing or in some environments
    pass