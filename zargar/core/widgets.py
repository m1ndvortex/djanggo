"""
Persian form widgets for ZARGAR jewelry SaaS platform.
"""
from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
import jdatetime


class PersianDateWidget(forms.DateInput):
    """
    Persian date picker widget with Shamsi calendar support and interactive calendar.
    """
    
    def __init__(self, attrs=None, format=None, show_calendar=True, show_today_button=True):
        default_attrs = {
            'class': 'persian-date-input form-control',
            'placeholder': '۱۴۰۳/۰۱/۰۱',
            'data-persian-date-picker': 'true',
            'data-show-calendar': str(show_calendar).lower(),
            'data-show-today': str(show_today_button).lower(),
            'autocomplete': 'off',
            'readonly': 'readonly',  # Prevent manual typing, use calendar only
        }
        if attrs:
            # Handle class attribute merging specially
            if 'class' in attrs:
                default_attrs['class'] = f"{default_attrs['class']} {attrs['class']}"
                attrs = attrs.copy()
                del attrs['class']
            default_attrs.update(attrs)
        
        self.show_calendar = show_calendar
        self.show_today_button = show_today_button
        super().__init__(attrs=default_attrs, format=format)
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render the widget with calendar interface."""
        from .calendar_utils import PersianCalendarUtils
        
        # Get the basic input field
        input_html = super().render(name, value, attrs, renderer)
        
        if not self.show_calendar:
            return input_html
        
        # Get current Persian date for calendar initialization
        if value:
            try:
                if hasattr(value, 'strftime'):
                    current_persian = PersianCalendarUtils.gregorian_to_shamsi(value)
                else:
                    current_persian = PersianCalendarUtils.get_current_persian_date()
            except:
                current_persian = PersianCalendarUtils.get_current_persian_date()
        else:
            current_persian = PersianCalendarUtils.get_current_persian_date()
        
        current_year, current_month, current_day = current_persian
        
        # Generate calendar HTML
        calendar_html = self._generate_calendar_html(name, current_year, current_month, current_day)
        
        # Combine input and calendar
        widget_html = f"""
        <div class="persian-date-widget" data-field-name="{name}">
            {input_html}
            <div class="persian-calendar-container" style="display: none;">
                {calendar_html}
            </div>
        </div>
        """
        
        return mark_safe(widget_html)
    
    def _generate_calendar_html(self, field_name, year, month, day):
        """Generate Persian calendar HTML."""
        from .calendar_utils import PersianCalendarUtils
        
        # Calendar header with navigation
        persian_year = PersianCalendarUtils.to_persian_digits(str(year))
        month_name = PersianCalendarUtils.PERSIAN_MONTHS[month - 1]
        
        calendar_html = f"""
        <div class="persian-calendar" data-year="{year}" data-month="{month}">
            <div class="calendar-header">
                <button type="button" class="btn btn-sm btn-outline-primary prev-year" data-action="prev-year">
                    <i class="fas fa-angle-double-right"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-primary prev-month" data-action="prev-month">
                    <i class="fas fa-angle-right"></i>
                </button>
                <div class="calendar-title">
                    <span class="month-name">{month_name}</span>
                    <span class="year-name">{persian_year}</span>
                </div>
                <button type="button" class="btn btn-sm btn-outline-primary next-month" data-action="next-month">
                    <i class="fas fa-angle-left"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-primary next-year" data-action="next-year">
                    <i class="fas fa-angle-double-left"></i>
                </button>
            </div>
            <div class="calendar-weekdays">
                <div class="weekday">ش</div>
                <div class="weekday">ی</div>
                <div class="weekday">د</div>
                <div class="weekday">س</div>
                <div class="weekday">چ</div>
                <div class="weekday">پ</div>
                <div class="weekday">ج</div>
            </div>
            <div class="calendar-days">
                {self._generate_calendar_days(year, month, day)}
            </div>
            <div class="calendar-footer">
                {self._generate_calendar_footer()}
            </div>
        </div>
        """
        
        return calendar_html
    
    def _generate_calendar_days(self, year, month, selected_day):
        """Generate calendar days HTML."""
        from .calendar_utils import PersianCalendarUtils
        
        days_html = ""
        
        # Get number of days in month
        days_in_month = PersianCalendarUtils.get_persian_month_days(year, month)
        
        # Get first day of month to calculate weekday
        first_day_gregorian = PersianCalendarUtils.shamsi_to_gregorian(year, month, 1)
        first_weekday = first_day_gregorian.weekday()
        # Convert to Persian weekday (Saturday = 0)
        persian_first_weekday = (first_weekday + 2) % 7
        
        # Add empty cells for days before month starts
        for _ in range(persian_first_weekday):
            days_html += '<div class="calendar-day empty"></div>'
        
        # Add days of the month
        for day in range(1, days_in_month + 1):
            persian_day = PersianCalendarUtils.to_persian_digits(str(day))
            selected_class = "selected" if day == selected_day else ""
            
            # Check if it's today
            current_persian = PersianCalendarUtils.get_current_persian_date()
            today_class = ""
            if (year, month, day) == current_persian:
                today_class = "today"
            
            days_html += f'''
            <div class="calendar-day {selected_class} {today_class}" 
                 data-day="{day}" 
                 data-persian-date="{year}/{month:02d}/{day:02d}">
                {persian_day}
            </div>
            '''
        
        return days_html
    
    def _generate_calendar_footer(self):
        """Generate calendar footer with action buttons."""
        footer_html = ""
        
        if self.show_today_button:
            footer_html += '''
            <button type="button" class="btn btn-sm btn-primary today-btn" data-action="today">
                امروز
            </button>
            '''
        
        footer_html += '''
        <button type="button" class="btn btn-sm btn-secondary clear-btn" data-action="clear">
            پاک کردن
        </button>
        <button type="button" class="btn btn-sm btn-success confirm-btn" data-action="confirm">
            تأیید
        </button>
        '''
        
        return footer_html
    
    def format_value(self, value):
        """Format the value for display in Persian."""
        if value is None:
            return ''
        
        if hasattr(value, 'strftime'):
            # Convert Gregorian to Persian
            try:
                from .calendar_utils import PersianCalendarUtils
                persian_date = PersianCalendarUtils.gregorian_to_shamsi(value)
                formatted = f"{persian_date[0]:04d}/{persian_date[1]:02d}/{persian_date[2]:02d}"
                return PersianCalendarUtils.to_persian_digits(formatted)
            except (ValueError, AttributeError):
                return str(value)
        
        return str(value)
    
    def value_from_datadict(self, data, files, name):
        """Convert Persian date input back to Gregorian."""
        value = data.get(name)
        if not value:
            return None
        
        try:
            from .calendar_utils import PersianCalendarUtils
            
            # Convert Persian digits to English
            english_value = PersianCalendarUtils.to_english_digits(value)
            
            # Parse Persian date
            parts = english_value.split('/')
            if len(parts) == 3:
                year, month, day = map(int, parts)
                return PersianCalendarUtils.shamsi_to_gregorian(year, month, day)
        except (ValueError, AttributeError):
            pass
        
        return value
    
    class Media:
        css = {
            'all': ('css/persian-calendar.css',)
        }
        js = ('js/persian-calendar.js',)


class PersianDateTimeWidget(forms.DateTimeInput):
    """
    Persian datetime picker widget with Shamsi calendar support.
    """
    
    def __init__(self, attrs=None, format=None):
        default_attrs = {
            'class': 'persian-datetime-input',
            'placeholder': '۱۴۰۳/۰۱/۰۱ - ۱۲:۳۰',
            'data-persian-datetime-picker': '',
            'autocomplete': 'off',
        }
        if attrs:
            default_attrs.update(attrs)
        
        super().__init__(attrs=default_attrs, format=format)
    
    def format_value(self, value):
        """Format the value for display in Persian."""
        if value is None:
            return ''
        
        if hasattr(value, 'strftime'):
            try:
                persian_datetime = jdatetime.datetime.fromgregorian(datetime=value)
                formatted = persian_datetime.strftime('%Y/%m/%d - %H:%M')
                return self.convert_to_persian_digits(formatted)
            except (ValueError, AttributeError):
                return str(value)
        
        return str(value)
    
    def convert_to_persian_digits(self, text):
        """Convert English digits to Persian digits."""
        english_digits = '0123456789'
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        
        for i, digit in enumerate(english_digits):
            text = text.replace(digit, persian_digits[i])
        
        return text


class PersianNumberWidget(forms.NumberInput):
    """
    Persian number input widget with automatic formatting.
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'persian-number-input',
            'data-persian-number-input': '',
            'dir': 'rtl',
            'style': 'text-align: right;',
        }
        if attrs:
            default_attrs.update(attrs)
        
        super().__init__(attrs=default_attrs)
    
    def format_value(self, value):
        """Format the value for display in Persian."""
        if value is None or value == '':
            return ''
        
        try:
            # Format with thousand separators
            formatted = f"{float(value):,.0f}"
            
            # Convert to Persian digits
            persian_formatted = self.convert_to_persian_digits(formatted)
            
            # Replace comma with Persian thousand separator
            persian_formatted = persian_formatted.replace(',', '٬')
            
            return persian_formatted
        except (ValueError, TypeError):
            return str(value)
    
    def value_from_datadict(self, data, files, name):
        """Convert Persian formatted number back to numeric value."""
        value = data.get(name)
        if not value:
            return None
        
        try:
            # Convert Persian digits to English
            english_value = self.convert_to_english_digits(value)
            
            # Remove thousand separators
            english_value = english_value.replace(',', '')
            english_value = english_value.replace('٬', '')
            
            # Convert decimal separator
            english_value = english_value.replace('٫', '.')
            
            return float(english_value)
        except (ValueError, TypeError):
            return value
    
    def convert_to_persian_digits(self, text):
        """Convert English digits to Persian digits."""
        english_digits = '0123456789'
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        
        for i, digit in enumerate(english_digits):
            text = text.replace(digit, persian_digits[i])
        
        return text
    
    def convert_to_english_digits(self, text):
        """Convert Persian digits to English digits."""
        english_digits = '0123456789'
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        
        for i, digit in enumerate(persian_digits):
            text = text.replace(digit, english_digits[i])
        
        return text


class PersianCurrencyWidget(PersianNumberWidget):
    """
    Persian currency input widget with Toman formatting.
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'placeholder': '۱۰۰٬۰۰۰ تومان',
        }
        if attrs:
            default_attrs.update(attrs)
        
        super().__init__(attrs=default_attrs)
    
    def format_value(self, value):
        """Format the value as Persian currency."""
        if value is None or value == '':
            return ''
        
        try:
            formatted = super().format_value(value)
            return f"{formatted} تومان" if formatted else ''
        except (ValueError, TypeError):
            return str(value)


class PersianWeightWidget(PersianNumberWidget):
    """
    Persian weight input widget with gram formatting.
    """
    
    def __init__(self, attrs=None, show_mithqal=False):
        default_attrs = {
            'placeholder': '۱۰٫۵۰۰ گرم',
            'step': '0.001',
        }
        if attrs:
            default_attrs.update(attrs)
        
        self.show_mithqal = show_mithqal
        super().__init__(attrs=default_attrs)
    
    def format_value(self, value):
        """Format the value as Persian weight."""
        if value is None or value == '':
            return ''
        
        try:
            # Format with 3 decimal places for weight
            formatted = f"{float(value):.3f}"
            
            # Convert to Persian digits
            persian_formatted = self.convert_to_persian_digits(formatted)
            
            # Replace decimal point with Persian decimal separator
            persian_formatted = persian_formatted.replace('.', '٫')
            
            return f"{persian_formatted} گرم"
        except (ValueError, TypeError):
            return str(value)


class PersianTextWidget(forms.TextInput):
    """
    Persian text input widget with RTL support.
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'persian-text-input',
            'dir': 'rtl',
            'style': 'text-align: right;',
        }
        if attrs:
            default_attrs.update(attrs)
        
        super().__init__(attrs=default_attrs)


class PersianTextareaWidget(forms.Textarea):
    """
    Persian textarea widget with RTL support.
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'persian-textarea',
            'dir': 'rtl',
            'style': 'text-align: right;',
            'rows': 4,
        }
        if attrs:
            default_attrs.update(attrs)
        
        super().__init__(attrs=default_attrs)


class PersianSelectWidget(forms.Select):
    """
    Persian select widget with RTL support.
    """
    
    def __init__(self, attrs=None, choices=()):
        default_attrs = {
            'class': 'persian-select',
            'dir': 'rtl',
        }
        if attrs:
            default_attrs.update(attrs)
        
        super().__init__(attrs=default_attrs, choices=choices)


class PersianCheckboxWidget(forms.CheckboxInput):
    """
    Persian checkbox widget with RTL support.
    """
    
    def __init__(self, attrs=None, check_test=None):
        default_attrs = {
            'class': 'persian-checkbox',
        }
        if attrs:
            default_attrs.update(attrs)
        
        super().__init__(attrs=default_attrs, check_test=check_test)


class PersianRadioSelectWidget(forms.RadioSelect):
    """
    Persian radio select widget with RTL support.
    """
    
    def __init__(self, attrs=None, choices=()):
        default_attrs = {
            'class': 'persian-radio-select',
        }
        if attrs:
            default_attrs.update(attrs)
        
        super().__init__(attrs=default_attrs, choices=choices)


class KaratSelectWidget(PersianSelectWidget):
    """
    Specialized widget for gold karat selection.
    """
    
    def __init__(self, attrs=None):
        # Common gold karat values in Iran
        karat_choices = [
            ('', 'انتخاب عیار'),
            (18, 'عیار ۱۸'),
            (21, 'عیار ۲۱'),
            (22, 'عیار ۲۲'),
            (24, 'عیار ۲۴'),
        ]
        
        super().__init__(attrs=attrs, choices=karat_choices)
    
    def format_value(self, value):
        """Format karat value in Persian."""
        if value is None or value == '':
            return ''
        
        try:
            karat_num = int(value)
            persian_num = self.convert_to_persian_digits(str(karat_num))
            return f"عیار {persian_num}"
        except (ValueError, TypeError):
            return str(value)
    
    def convert_to_persian_digits(self, text):
        """Convert English digits to Persian digits."""
        english_digits = '0123456789'
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        
        for i, digit in enumerate(english_digits):
            text = text.replace(digit, persian_digits[i])
        
        return text