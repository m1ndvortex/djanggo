/**
 * Persian Date Range Selector
 * Specialized component for selecting date ranges with Persian calendar
 * Supports fiscal year and quarter selection for ZARGAR jewelry SaaS platform
 */

class PersianDateRange {
    constructor(container) {
        this.container = container;
        this.startInput = container.querySelector('.persian-date-range-start');
        this.endInput = container.querySelector('.persian-date-range-end');
        this.rangeDisplay = container.querySelector('.persian-date-range-display');
        this.quickSelectors = container.querySelector('.persian-date-range-quick');
        
        this.startDate = null;
        this.endDate = null;
        
        this.persianMonths = [
            'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
            'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
        ];
        
        this.init();
    }
    
    init() {
        this.setupQuickSelectors();
        this.bindEvents();
        this.updateDisplay();
    }
    
    setupQuickSelectors() {
        if (!this.quickSelectors) return;
        
        const currentYear = this.getCurrentPersianDate().year;
        const persianCurrentYear = this.toPersianDigits(currentYear.toString());
        const persianPrevYear = this.toPersianDigits((currentYear - 1).toString());
        
        this.quickSelectors.innerHTML = `
            <div class="quick-selector-group">
                <h4 class="quick-selector-title">انتخاب سریع بازه زمانی</h4>
                
                <div class="quick-selector-section">
                    <h5>بازه‌های زمانی</h5>
                    <div class="quick-selector-buttons">
                        <button type="button" class="quick-selector-btn" data-range="today">امروز</button>
                        <button type="button" class="quick-selector-btn" data-range="yesterday">دیروز</button>
                        <button type="button" class="quick-selector-btn" data-range="this-week">این هفته</button>
                        <button type="button" class="quick-selector-btn" data-range="last-week">هفته گذشته</button>
                        <button type="button" class="quick-selector-btn" data-range="this-month">این ماه</button>
                        <button type="button" class="quick-selector-btn" data-range="last-month">ماه گذشته</button>
                    </div>
                </div>
                
                <div class="quick-selector-section">
                    <h5>سال مالی</h5>
                    <div class="quick-selector-buttons">
                        <button type="button" class="quick-selector-btn" data-range="current-fiscal-year">
                            سال جاری (${persianCurrentYear})
                        </button>
                        <button type="button" class="quick-selector-btn" data-range="prev-fiscal-year">
                            سال گذشته (${persianPrevYear})
                        </button>
                    </div>
                </div>
                
                <div class="quick-selector-section">
                    <h5>فصل مالی سال جاری</h5>
                    <div class="quick-selector-buttons">
                        <button type="button" class="quick-selector-btn" data-range="q1">فصل اول (فروردین - خرداد)</button>
                        <button type="button" class="quick-selector-btn" data-range="q2">فصل دوم (تیر - شهریور)</button>
                        <button type="button" class="quick-selector-btn" data-range="q3">فصل سوم (مهر - آذر)</button>
                        <button type="button" class="quick-selector-btn" data-range="q4">فصل چهارم (دی - اسفند)</button>
                    </div>
                </div>
                
                <div class="quick-selector-section">
                    <h5>فصل مالی سال گذشته</h5>
                    <div class="quick-selector-buttons">
                        <button type="button" class="quick-selector-btn" data-range="prev-q1">فصل اول سال گذشته</button>
                        <button type="button" class="quick-selector-btn" data-range="prev-q2">فصل دوم سال گذشته</button>
                        <button type="button" class="quick-selector-btn" data-range="prev-q3">فصل سوم سال گذشته</button>
                        <button type="button" class="quick-selector-btn" data-range="prev-q4">فصل چهارم سال گذشته</button>
                    </div>
                </div>
            </div>
        `;
    }
    
    bindEvents() {
        // Quick selector buttons
        if (this.quickSelectors) {
            this.quickSelectors.addEventListener('click', (e) => {
                if (e.target.classList.contains('quick-selector-btn')) {
                    const range = e.target.dataset.range;
                    this.selectQuickRange(range);
                }
            });
        }
        
        // Input change events
        if (this.startInput) {
            this.startInput.addEventListener('change', () => {
                this.parseStartDate();
                this.updateDisplay();
            });
        }
        
        if (this.endInput) {
            this.endInput.addEventListener('change', () => {
                this.parseEndDate();
                this.updateDisplay();
            });
        }
    }
    
    selectQuickRange(rangeType) {
        const currentDate = this.getCurrentPersianDate();
        let startDate, endDate;
        
        switch (rangeType) {
            case 'today':
                startDate = endDate = currentDate;
                break;
                
            case 'yesterday':
                const yesterday = this.addDays(currentDate, -1);
                startDate = endDate = yesterday;
                break;
                
            case 'this-week':
                startDate = this.getWeekStart(currentDate);
                endDate = this.getWeekEnd(currentDate);
                break;
                
            case 'last-week':
                const lastWeekStart = this.addDays(this.getWeekStart(currentDate), -7);
                startDate = lastWeekStart;
                endDate = this.addDays(lastWeekStart, 6);
                break;
                
            case 'this-month':
                startDate = { year: currentDate.year, month: currentDate.month, day: 1 };
                endDate = { 
                    year: currentDate.year, 
                    month: currentDate.month, 
                    day: this.getDaysInPersianMonth(currentDate.year, currentDate.month) 
                };
                break;
                
            case 'last-month':
                const lastMonth = currentDate.month === 1 ? 12 : currentDate.month - 1;
                const lastMonthYear = currentDate.month === 1 ? currentDate.year - 1 : currentDate.year;
                startDate = { year: lastMonthYear, month: lastMonth, day: 1 };
                endDate = { 
                    year: lastMonthYear, 
                    month: lastMonth, 
                    day: this.getDaysInPersianMonth(lastMonthYear, lastMonth) 
                };
                break;
                
            case 'current-fiscal-year':
                startDate = { year: currentDate.year, month: 1, day: 1 };
                endDate = { 
                    year: currentDate.year, 
                    month: 12, 
                    day: this.getDaysInPersianMonth(currentDate.year, 12) 
                };
                break;
                
            case 'prev-fiscal-year':
                const prevYear = currentDate.year - 1;
                startDate = { year: prevYear, month: 1, day: 1 };
                endDate = { 
                    year: prevYear, 
                    month: 12, 
                    day: this.getDaysInPersianMonth(prevYear, 12) 
                };
                break;
                
            case 'q1':
                startDate = { year: currentDate.year, month: 1, day: 1 };
                endDate = { year: currentDate.year, month: 3, day: 31 };
                break;
                
            case 'q2':
                startDate = { year: currentDate.year, month: 4, day: 1 };
                endDate = { year: currentDate.year, month: 6, day: 31 };
                break;
                
            case 'q3':
                startDate = { year: currentDate.year, month: 7, day: 1 };
                endDate = { year: currentDate.year, month: 9, day: 30 };
                break;
                
            case 'q4':
                startDate = { year: currentDate.year, month: 10, day: 1 };
                endDate = { 
                    year: currentDate.year, 
                    month: 12, 
                    day: this.getDaysInPersianMonth(currentDate.year, 12) 
                };
                break;
                
            case 'prev-q1':
                const prevYearQ1 = currentDate.year - 1;
                startDate = { year: prevYearQ1, month: 1, day: 1 };
                endDate = { year: prevYearQ1, month: 3, day: 31 };
                break;
                
            case 'prev-q2':
                const prevYearQ2 = currentDate.year - 1;
                startDate = { year: prevYearQ2, month: 4, day: 1 };
                endDate = { year: prevYearQ2, month: 6, day: 31 };
                break;
                
            case 'prev-q3':
                const prevYearQ3 = currentDate.year - 1;
                startDate = { year: prevYearQ3, month: 7, day: 1 };
                endDate = { year: prevYearQ3, month: 9, day: 30 };
                break;
                
            case 'prev-q4':
                const prevYearQ4 = currentDate.year - 1;
                startDate = { year: prevYearQ4, month: 10, day: 1 };
                endDate = { 
                    year: prevYearQ4, 
                    month: 12, 
                    day: this.getDaysInPersianMonth(prevYearQ4, 12) 
                };
                break;
        }
        
        if (startDate && endDate) {
            this.setDateRange(startDate, endDate);
        }
    }
    
    setDateRange(startDate, endDate) {
        this.startDate = startDate;
        this.endDate = endDate;
        
        // Update input fields
        if (this.startInput) {
            this.startInput.value = this.formatDateForInput(startDate);
        }
        if (this.endInput) {
            this.endInput.value = this.formatDateForInput(endDate);
        }
        
        this.updateDisplay();
        this.triggerChangeEvent();
    }
    
    parseStartDate() {
        if (this.startInput && this.startInput.value) {
            this.startDate = this.parsePersianDate(this.startInput.value);
        }
    }
    
    parseEndDate() {
        if (this.endInput && this.endInput.value) {
            this.endDate = this.parsePersianDate(this.endInput.value);
        }
    }
    
    updateDisplay() {
        if (!this.rangeDisplay) return;
        
        if (this.startDate && this.endDate) {
            const startFormatted = this.formatDateForDisplay(this.startDate);
            const endFormatted = this.formatDateForDisplay(this.endDate);
            const daysDiff = this.calculateDaysDifference(this.startDate, this.endDate);
            const persianDaysDiff = this.toPersianDigits(daysDiff.toString());
            
            this.rangeDisplay.innerHTML = `
                <div class="range-display-content">
                    <div class="range-dates">
                        <span class="range-start">${startFormatted}</span>
                        <span class="range-separator">تا</span>
                        <span class="range-end">${endFormatted}</span>
                    </div>
                    <div class="range-duration">
                        مدت زمان: ${persianDaysDiff} روز
                    </div>
                </div>
            `;
        } else {
            this.rangeDisplay.innerHTML = '<div class="range-display-empty">بازه زمانی انتخاب نشده</div>';
        }
    }
    
    triggerChangeEvent() {
        const event = new CustomEvent('dateRangeChange', {
            detail: {
                startDate: this.startDate,
                endDate: this.endDate,
                startDateFormatted: this.startDate ? this.formatDateForInput(this.startDate) : null,
                endDateFormatted: this.endDate ? this.formatDateForInput(this.endDate) : null
            }
        });
        this.container.dispatchEvent(event);
    }
    
    // Utility methods
    getCurrentPersianDate() {
        const now = new Date();
        return this.gregorianToPersian(now);
    }
    
    gregorianToPersian(gregorianDate) {
        // Simplified conversion - in production, use jdatetime or similar library
        const year = gregorianDate.getFullYear();
        const month = gregorianDate.getMonth() + 1;
        const day = gregorianDate.getDate();
        
        let persianYear = year - 621;
        let persianMonth = month;
        let persianDay = day;
        
        // Adjust for Persian calendar differences (simplified)
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
    
    parsePersianDate(dateString) {
        if (!dateString) return null;
        
        const englishString = this.toEnglishDigits(dateString.trim());
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
        
        const daysInMonth = this.getDaysInPersianMonth(year, month);
        return day <= daysInMonth;
    }
    
    getDaysInPersianMonth(year, month) {
        if (month <= 6) {
            return 31;
        } else if (month <= 11) {
            return 30;
        } else {
            return this.isPersianLeapYear(year) ? 30 : 29;
        }
    }
    
    isPersianLeapYear(year) {
        const cycle = year % 128;
        const leapYears = [1, 5, 9, 13, 17, 22, 26, 30, 34, 38, 42, 46, 50, 55, 59, 63, 67, 71, 75, 79, 83, 88, 92, 96, 100, 104, 108, 112, 116, 121, 125];
        return leapYears.includes(cycle);
    }
    
    formatDateForInput(dateObj) {
        const formatted = `${dateObj.year.toString().padStart(4, '0')}/${dateObj.month.toString().padStart(2, '0')}/${dateObj.day.toString().padStart(2, '0')}`;
        return this.toPersianDigits(formatted);
    }
    
    formatDateForDisplay(dateObj) {
        const monthName = this.persianMonths[dateObj.month - 1];
        const persianDay = this.toPersianDigits(dateObj.day.toString());
        const persianYear = this.toPersianDigits(dateObj.year.toString());
        return `${persianDay} ${monthName} ${persianYear}`;
    }
    
    addDays(dateObj, days) {
        // Simple day addition (would need proper calendar math in production)
        let newDay = dateObj.day + days;
        let newMonth = dateObj.month;
        let newYear = dateObj.year;
        
        while (newDay <= 0) {
            newMonth--;
            if (newMonth <= 0) {
                newMonth = 12;
                newYear--;
            }
            newDay += this.getDaysInPersianMonth(newYear, newMonth);
        }
        
        while (newDay > this.getDaysInPersianMonth(newYear, newMonth)) {
            newDay -= this.getDaysInPersianMonth(newYear, newMonth);
            newMonth++;
            if (newMonth > 12) {
                newMonth = 1;
                newYear++;
            }
        }
        
        return { year: newYear, month: newMonth, day: newDay };
    }
    
    getWeekStart(dateObj) {
        // Persian week starts on Saturday
        // This is a simplified implementation
        return this.addDays(dateObj, -((dateObj.day - 1) % 7));
    }
    
    getWeekEnd(dateObj) {
        const weekStart = this.getWeekStart(dateObj);
        return this.addDays(weekStart, 6);
    }
    
    calculateDaysDifference(startDate, endDate) {
        // Simplified calculation - would need proper calendar math in production
        const startDays = startDate.year * 365 + startDate.month * 30 + startDate.day;
        const endDays = endDate.year * 365 + endDate.month * 30 + endDate.day;
        return Math.abs(endDays - startDays) + 1;
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
    
    // Public API methods
    getStartDate() {
        return this.startDate;
    }
    
    getEndDate() {
        return this.endDate;
    }
    
    getDateRange() {
        return {
            start: this.startDate,
            end: this.endDate
        };
    }
    
    clearRange() {
        this.startDate = null;
        this.endDate = null;
        
        if (this.startInput) this.startInput.value = '';
        if (this.endInput) this.endInput.value = '';
        
        this.updateDisplay();
        this.triggerChangeEvent();
    }
}

// Initialize Persian date range selectors when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const dateRangeWidgets = document.querySelectorAll('.persian-date-range-widget');
    dateRangeWidgets.forEach(widget => {
        new PersianDateRange(widget);
    });
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PersianDateRange;
}