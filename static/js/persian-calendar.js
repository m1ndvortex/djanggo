/**
 * Persian Calendar Widget JavaScript
 * Provides interactive Shamsi calendar functionality for ZARGAR jewelry SaaS platform
 */

class PersianCalendar {
    constructor(container) {
        this.container = container;
        this.input = container.querySelector('.persian-date-input');
        this.calendarContainer = container.querySelector('.persian-calendar-container');
        this.calendar = container.querySelector('.persian-calendar');
        this.fieldName = container.dataset.fieldName;
        
        this.currentYear = parseInt(this.calendar.dataset.year);
        this.currentMonth = parseInt(this.calendar.dataset.month);
        this.selectedDate = null;
        
        this.persianMonths = [
            'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
            'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
        ];
        
        this.persianWeekdays = [
            'شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه'
        ];
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.parseCurrentValue();
    }
    
    bindEvents() {
        // Input click to show calendar
        this.input.addEventListener('click', (e) => {
            e.preventDefault();
            this.showCalendar();
        });
        
        // Navigation buttons
        this.calendar.addEventListener('click', (e) => {
            const action = e.target.dataset.action;
            if (action) {
                e.preventDefault();
                this.handleAction(action);
            }
        });
        
        // Day selection
        this.calendar.addEventListener('click', (e) => {
            if (e.target.classList.contains('calendar-day') && !e.target.classList.contains('empty')) {
                const day = parseInt(e.target.dataset.day);
                this.selectDate(this.currentYear, this.currentMonth, day);
            }
        });
        
        // Close calendar when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.hideCalendar();
            }
        });
        
        // Keyboard navigation
        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.showCalendar();
            } else if (e.key === 'Escape') {
                this.hideCalendar();
            }
        });
    }
    
    parseCurrentValue() {
        const value = this.input.value;
        if (value) {
            const parsed = this.parsePersianDate(value);
            if (parsed) {
                this.selectedDate = parsed;
                this.currentYear = parsed.year;
                this.currentMonth = parsed.month;
            }
        }
    }
    
    parsePersianDate(dateString) {
        if (!dateString) return null;
        
        // Convert Persian digits to English
        const englishString = this.toEnglishDigits(dateString);
        
        // Parse YYYY/MM/DD format
        const parts = englishString.split('/');
        if (parts.length === 3) {
            const year = parseInt(parts[0]);
            const month = parseInt(parts[1]);
            const day = parseInt(parts[2]);
            
            if (this.isValidPersianDate(year, month, day)) {
                return { year, month, day };
            }
        }
        
        return null;
    }
    
    isValidPersianDate(year, month, day) {
        if (year < 1300 || year > 1500) return false;
        if (month < 1 || month > 12) return false;
        if (day < 1 || day > 31) return false;
        
        // Check days in month
        const daysInMonth = this.getDaysInPersianMonth(year, month);
        return day <= daysInMonth;
    }
    
    getDaysInPersianMonth(year, month) {
        if (month <= 6) {
            return 31;
        } else if (month <= 11) {
            return 30;
        } else {
            // Esfand - check for leap year
            return this.isPersianLeapYear(year) ? 30 : 29;
        }
    }
    
    isPersianLeapYear(year) {
        // Simplified Persian leap year calculation
        const cycle = year % 128;
        const leapYears = [1, 5, 9, 13, 17, 22, 26, 30, 34, 38, 42, 46, 50, 55, 59, 63, 67, 71, 75, 79, 83, 88, 92, 96, 100, 104, 108, 112, 116, 121, 125];
        return leapYears.includes(cycle);
    }
    
    showCalendar() {
        this.calendarContainer.style.display = 'block';
        setTimeout(() => {
            this.calendarContainer.classList.add('show');
        }, 10);
        
        this.updateCalendar();
    }
    
    hideCalendar() {
        this.calendarContainer.classList.remove('show');
        setTimeout(() => {
            this.calendarContainer.style.display = 'none';
        }, 300);
    }
    
    handleAction(action) {
        switch (action) {
            case 'prev-year':
                this.currentYear--;
                this.updateCalendar();
                break;
            case 'next-year':
                this.currentYear++;
                this.updateCalendar();
                break;
            case 'prev-month':
                this.currentMonth--;
                if (this.currentMonth < 1) {
                    this.currentMonth = 12;
                    this.currentYear--;
                }
                this.updateCalendar();
                break;
            case 'next-month':
                this.currentMonth++;
                if (this.currentMonth > 12) {
                    this.currentMonth = 1;
                    this.currentYear++;
                }
                this.updateCalendar();
                break;
            case 'today':
                const today = this.getCurrentPersianDate();
                this.selectDate(today.year, today.month, today.day);
                break;
            case 'clear':
                this.clearDate();
                break;
            case 'confirm':
                this.hideCalendar();
                break;
        }
    }
    
    updateCalendar() {
        // Update header
        const monthName = this.calendar.querySelector('.month-name');
        const yearName = this.calendar.querySelector('.year-name');
        
        monthName.textContent = this.persianMonths[this.currentMonth - 1];
        yearName.textContent = this.toPersianDigits(this.currentYear.toString());
        
        // Update calendar data attributes
        this.calendar.dataset.year = this.currentYear;
        this.calendar.dataset.month = this.currentMonth;
        
        // Update days
        this.updateCalendarDays();
    }
    
    updateCalendarDays() {
        const daysContainer = this.calendar.querySelector('.calendar-days');
        daysContainer.innerHTML = '';
        
        const daysInMonth = this.getDaysInPersianMonth(this.currentYear, this.currentMonth);
        const firstDayWeekday = this.getFirstDayWeekday(this.currentYear, this.currentMonth);
        
        // Add empty cells for days before month starts
        for (let i = 0; i < firstDayWeekday; i++) {
            const emptyDay = document.createElement('div');
            emptyDay.className = 'calendar-day empty';
            daysContainer.appendChild(emptyDay);
        }
        
        // Add days of the month
        for (let day = 1; day <= daysInMonth; day++) {
            const dayElement = document.createElement('div');
            dayElement.className = 'calendar-day';
            dayElement.dataset.day = day;
            dayElement.dataset.persianDate = `${this.currentYear}/${this.currentMonth.toString().padStart(2, '0')}/${day.toString().padStart(2, '0')}`;
            dayElement.textContent = this.toPersianDigits(day.toString());
            
            // Check if selected
            if (this.selectedDate && 
                this.selectedDate.year === this.currentYear && 
                this.selectedDate.month === this.currentMonth && 
                this.selectedDate.day === day) {
                dayElement.classList.add('selected');
            }
            
            // Check if today
            const today = this.getCurrentPersianDate();
            if (today.year === this.currentYear && 
                today.month === this.currentMonth && 
                today.day === day) {
                dayElement.classList.add('today');
            }
            
            daysContainer.appendChild(dayElement);
        }
    }
    
    getFirstDayWeekday(year, month) {
        // Convert to Gregorian to get weekday
        const gregorianDate = this.persianToGregorian(year, month, 1);
        const weekday = gregorianDate.getDay();
        // Convert to Persian weekday (Saturday = 0)
        return (weekday + 1) % 7;
    }
    
    selectDate(year, month, day) {
        this.selectedDate = { year, month, day };
        
        // Format and set input value
        const formattedDate = `${year.toString().padStart(4, '0')}/${month.toString().padStart(2, '0')}/${day.toString().padStart(2, '0')}`;
        const persianFormattedDate = this.toPersianDigits(formattedDate);
        this.input.value = persianFormattedDate;
        
        // Update calendar display
        this.updateCalendarDays();
        
        // Trigger change event
        this.input.dispatchEvent(new Event('change', { bubbles: true }));
    }
    
    clearDate() {
        this.selectedDate = null;
        this.input.value = '';
        this.updateCalendarDays();
        this.input.dispatchEvent(new Event('change', { bubbles: true }));
    }
    
    getCurrentPersianDate() {
        const now = new Date();
        return this.gregorianToPersian(now);
    }
    
    gregorianToPersian(gregorianDate) {
        // Simplified conversion - in production, use a proper library
        const year = gregorianDate.getFullYear();
        const month = gregorianDate.getMonth() + 1;
        const day = gregorianDate.getDate();
        
        // This is a simplified approximation
        // In production, use jdatetime or similar library
        let persianYear = year - 621;
        let persianMonth = month;
        let persianDay = day;
        
        // Adjust for Persian calendar differences
        if (month >= 3 && month <= 5) {
            persianMonth = month - 2;
        } else if (month >= 6 && month <= 8) {
            persianMonth = month - 2;
        } else if (month >= 9 && month <= 11) {
            persianMonth = month - 2;
        } else {
            persianMonth = month + 10;
            if (month <= 2) {
                persianYear--;
            }
        }
        
        return { year: persianYear, month: persianMonth, day: persianDay };
    }
    
    persianToGregorian(persianYear, persianMonth, persianDay) {
        // Simplified conversion - in production, use a proper library
        let gregorianYear = persianYear + 621;
        let gregorianMonth = persianMonth;
        let gregorianDay = persianDay;
        
        // Adjust for Gregorian calendar differences
        if (persianMonth >= 1 && persianMonth <= 3) {
            gregorianMonth = persianMonth + 2;
        } else if (persianMonth >= 4 && persianMonth <= 6) {
            gregorianMonth = persianMonth + 2;
        } else if (persianMonth >= 7 && persianMonth <= 9) {
            gregorianMonth = persianMonth + 2;
        } else {
            gregorianMonth = persianMonth - 10;
            if (persianMonth >= 10) {
                gregorianYear++;
            }
        }
        
        return new Date(gregorianYear, gregorianMonth - 1, gregorianDay);
    }
    
    toPersianDigits(text) {
        const englishDigits = '0123456789';
        const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
        
        return text.replace(/[0-9]/g, (digit) => {
            return persianDigits[englishDigits.indexOf(digit)];
        });
    }
    
    toEnglishDigits(text) {
        const englishDigits = '0123456789';
        const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
        
        return text.replace(/[۰-۹]/g, (digit) => {
            return englishDigits[persianDigits.indexOf(digit)];
        });
    }
}

// Initialize Persian calendars when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const calendarWidgets = document.querySelectorAll('.persian-date-widget');
    calendarWidgets.forEach(widget => {
        new PersianCalendar(widget);
    });
});

// Also initialize for dynamically added calendars
const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        mutation.addedNodes.forEach(function(node) {
            if (node.nodeType === 1) { // Element node
                const calendarWidgets = node.querySelectorAll ? node.querySelectorAll('.persian-date-widget') : [];
                calendarWidgets.forEach(widget => {
                    if (!widget.hasAttribute('data-initialized')) {
                        widget.setAttribute('data-initialized', 'true');
                        new PersianCalendar(widget);
                    }
                });
            }
        });
    });
});

observer.observe(document.body, {
    childList: true,
    subtree: true
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PersianCalendar;
}