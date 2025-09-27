/**
 * Persian Calendar Widget JavaScript
 * Provides interactive Shamsi calendar functionality for ZARGAR jewelry SaaS platform
 * Enhanced with date range selection and fiscal year support
 */

class PersianCalendar {
    constructor(container) {
        this.container = container;
        this.input = container.querySelector('.persian-date-input');
        this.calendarContainer = container.querySelector('.persian-calendar-container');
        this.calendar = container.querySelector('.persian-calendar');
        this.fieldName = container.dataset.fieldName;
        
        // Calendar configuration
        this.mode = container.dataset.mode || 'single'; // single, range, fiscal-year
        this.showFiscalYear = container.dataset.showFiscalYear === 'true';
        this.showQuarters = container.dataset.showQuarters === 'true';
        
        this.currentYear = parseInt(this.calendar?.dataset.year) || this.getCurrentPersianDate().year;
        this.currentMonth = parseInt(this.calendar?.dataset.month) || this.getCurrentPersianDate().month;
        this.selectedDate = null;
        this.selectedRange = { start: null, end: null };
        this.selectedFiscalYear = null;
        this.selectedQuarter = null;
        
        this.persianMonths = [
            'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
            'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
        ];
        
        this.persianWeekdays = [
            'شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه'
        ];
        
        this.persianQuarters = [
            { name: 'فصل اول', months: [1, 2, 3], description: 'فروردین - خرداد' },
            { name: 'فصل دوم', months: [4, 5, 6], description: 'تیر - شهریور' },
            { name: 'فصل سوم', months: [7, 8, 9], description: 'مهر - آذر' },
            { name: 'فصل چهارم', months: [10, 11, 12], description: 'دی - اسفند' }
        ];
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.parseCurrentValue();
        this.setupCalendarMode();
    }
    
    setupCalendarMode() {
        // Add mode-specific classes and setup
        this.container.classList.add(`persian-calendar-${this.mode}`);
        
        if (this.mode === 'range') {
            this.container.classList.add('range-mode');
        } else if (this.mode === 'fiscal-year') {
            this.container.classList.add('fiscal-year-mode');
            this.setupFiscalYearSelector();
        }
        
        if (this.showFiscalYear) {
            this.setupFiscalYearControls();
        }
        
        if (this.showQuarters) {
            this.setupQuarterControls();
        }
    }
    
    setupFiscalYearSelector() {
        // Create fiscal year selector if it doesn't exist
        if (!this.calendar.querySelector('.fiscal-year-selector')) {
            const fiscalYearHtml = this.generateFiscalYearSelector();
            const headerElement = this.calendar.querySelector('.calendar-header');
            if (headerElement) {
                headerElement.insertAdjacentHTML('afterend', fiscalYearHtml);
            }
        }
    }
    
    setupFiscalYearControls() {
        // Add fiscal year quick selection buttons
        if (!this.calendar.querySelector('.fiscal-year-controls')) {
            const controlsHtml = this.generateFiscalYearControls();
            const footerElement = this.calendar.querySelector('.calendar-footer');
            if (footerElement) {
                footerElement.insertAdjacentHTML('beforebegin', controlsHtml);
            }
        }
    }
    
    setupQuarterControls() {
        // Add quarter selection controls
        if (!this.calendar.querySelector('.quarter-controls')) {
            const quartersHtml = this.generateQuarterControls();
            const footerElement = this.calendar.querySelector('.calendar-footer');
            if (footerElement) {
                footerElement.insertAdjacentHTML('beforebegin', quartersHtml);
            }
        }
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
                this.handleDaySelection(this.currentYear, this.currentMonth, day);
            }
        });
        
        // Fiscal year selection
        this.calendar.addEventListener('click', (e) => {
            if (e.target.classList.contains('fiscal-year-option')) {
                const year = parseInt(e.target.dataset.year);
                this.selectFiscalYear(year);
            }
        });
        
        // Quarter selection
        this.calendar.addEventListener('click', (e) => {
            if (e.target.classList.contains('quarter-option')) {
                const quarter = parseInt(e.target.dataset.quarter);
                this.selectQuarter(quarter);
            }
        });
        
        // Range selection mode toggle
        this.calendar.addEventListener('click', (e) => {
            if (e.target.classList.contains('range-toggle')) {
                this.toggleRangeMode();
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
            } else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                this.handleKeyboardNavigation(e);
            }
        });
        
        // Input validation for manual entry
        this.input.addEventListener('input', (e) => {
            this.handleInputChange(e);
        });
        
        // Input blur validation
        this.input.addEventListener('blur', (e) => {
            this.validateAndFormatInput();
        });
    }
    
    parseCurrentValue() {
        const value = this.input.value.trim();
        if (!value) return;
        
        if (this.mode === 'single') {
            const parsed = this.parsePersianDate(value);
            if (parsed) {
                this.selectedDate = parsed;
                this.currentYear = parsed.year;
                this.currentMonth = parsed.month;
            }
        } else if (this.mode === 'range') {
            // Parse range format: "YYYY/MM/DD تا YYYY/MM/DD"
            if (value.includes(' تا ')) {
                const parts = value.split(' تا ');
                if (parts.length === 2) {
                    const startParsed = this.parsePersianDate(parts[0].trim());
                    const endParsed = this.parsePersianDate(parts[1].trim());
                    
                    if (startParsed && endParsed) {
                        this.selectedRange = { start: startParsed, end: endParsed };
                        this.currentYear = startParsed.year;
                        this.currentMonth = startParsed.month;
                    }
                }
            }
        } else if (this.mode === 'fiscal-year') {
            // Parse fiscal year format: "سال مالی YYYY"
            if (value.includes('سال مالی')) {
                const yearMatch = value.match(/(\d{4}|[۰-۹]{4})/);
                if (yearMatch) {
                    const yearStr = this.toEnglishDigits(yearMatch[1]);
                    const year = parseInt(yearStr);
                    if (year >= 1300 && year <= 1500) {
                        this.selectedFiscalYear = year;
                        this.currentYear = year;
                        this.currentMonth = 1;
                    }
                }
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
            case 'current-fiscal-year':
                const currentYear = this.getCurrentPersianDate().year;
                this.selectFiscalYear(currentYear);
                break;
            case 'prev-fiscal-year':
                const prevYear = this.getCurrentPersianDate().year - 1;
                this.selectFiscalYear(prevYear);
                break;
            case 'clear':
                this.clearDate();
                break;
            case 'confirm':
                this.hideCalendar();
                break;
        }
    }
    
    handleInputChange(e) {
        let value = e.target.value;
        
        // Convert English digits to Persian
        value = this.toPersianDigits(value);
        
        // Format based on mode
        if (this.mode === 'single') {
            // Format as single date (YYYY/MM/DD)
            value = value.replace(/[^\d۰-۹\/]/g, '');
            
            if (value.length > 4 && value.indexOf('/') === -1) {
                value = value.substring(0, 4) + '/' + value.substring(4);
            }
            if (value.length > 7 && value.lastIndexOf('/') === 4) {
                value = value.substring(0, 7) + '/' + value.substring(7);
            }
            
            // Limit to 10 characters (YYYY/MM/DD)
            if (value.length > 10) {
                value = value.substring(0, 10);
            }
        }
        
        e.target.value = value;
    }
    
    validateAndFormatInput() {
        const value = this.input.value.trim();
        if (!value) return;
        
        if (this.mode === 'single') {
            const parsed = this.parsePersianDate(value);
            if (parsed) {
                this.selectedDate = parsed;
                this.currentYear = parsed.year;
                this.currentMonth = parsed.month;
                this.input.value = this.formatDateForDisplay(parsed);
            }
        }
    }
    
    handleKeyboardNavigation(e) {
        if (!this.calendarContainer.style.display || this.calendarContainer.style.display === 'none') {
            return;
        }
        
        e.preventDefault();
        
        if (e.key === 'ArrowLeft') {
            // Navigate to next day/month
            if (e.shiftKey) {
                this.handleAction('next-month');
            } else {
                // Navigate to next day (implement if needed)
            }
        } else if (e.key === 'ArrowRight') {
            // Navigate to previous day/month
            if (e.shiftKey) {
                this.handleAction('prev-month');
            } else {
                // Navigate to previous day (implement if needed)
            }
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
            
            // Apply styling based on selection mode
            this.applyDayStyles(dayElement, this.currentYear, this.currentMonth, day);
            
            daysContainer.appendChild(dayElement);
        }
    }
    
    applyDayStyles(dayElement, year, month, day) {
        const currentDate = { year, month, day };
        
        // Check if selected (single mode)
        if (this.mode === 'single' && this.selectedDate && 
            this.selectedDate.year === year && 
            this.selectedDate.month === month && 
            this.selectedDate.day === day) {
            dayElement.classList.add('selected');
        }
        
        // Check if in range (range mode)
        if (this.mode === 'range' && this.selectedRange.start) {
            if (this.selectedRange.end) {
                // Complete range
                if (this.isDateInRange(currentDate, this.selectedRange.start, this.selectedRange.end)) {
                    dayElement.classList.add('in-range');
                    
                    if (this.compareDates(currentDate, this.selectedRange.start) === 0) {
                        dayElement.classList.add('range-start');
                    }
                    if (this.compareDates(currentDate, this.selectedRange.end) === 0) {
                        dayElement.classList.add('range-end');
                    }
                }
            } else {
                // Only start date selected
                if (this.compareDates(currentDate, this.selectedRange.start) === 0) {
                    dayElement.classList.add('range-start');
                }
            }
        }
        
        // Check if today
        const today = this.getCurrentPersianDate();
        if (today.year === year && today.month === month && today.day === day) {
            dayElement.classList.add('today');
        }
        
        // Check if in selected fiscal year/quarter
        if (this.selectedFiscalYear && year === this.selectedFiscalYear) {
            dayElement.classList.add('fiscal-year');
        }
        
        if (this.selectedQuarter) {
            const quarterInfo = this.persianQuarters[this.selectedQuarter - 1];
            if (quarterInfo.months.includes(month)) {
                dayElement.classList.add('quarter');
            }
        }
    }
    
    isDateInRange(date, startDate, endDate) {
        return this.compareDates(date, startDate) >= 0 && this.compareDates(date, endDate) <= 0;
    }
    
    generateFiscalYearSelector() {
        const currentYear = this.getCurrentPersianDate().year;
        const years = [];
        
        // Generate 5 years before and after current year
        for (let i = currentYear - 5; i <= currentYear + 5; i++) {
            years.push(i);
        }
        
        let html = '<div class="fiscal-year-selector">';
        html += '<div class="fiscal-year-title">انتخاب سال مالی:</div>';
        html += '<div class="fiscal-year-options">';
        
        years.forEach(year => {
            const persianYear = this.toPersianDigits(year.toString());
            const isSelected = year === this.selectedFiscalYear ? 'selected' : '';
            html += `<button type="button" class="fiscal-year-option ${isSelected}" data-year="${year}">${persianYear}</button>`;
        });
        
        html += '</div></div>';
        return html;
    }
    
    generateFiscalYearControls() {
        const currentYear = this.getCurrentPersianDate().year;
        const persianCurrentYear = this.toPersianDigits(currentYear.toString());
        const persianPrevYear = this.toPersianDigits((currentYear - 1).toString());
        
        return `
        <div class="fiscal-year-controls">
            <div class="fiscal-year-title">انتخاب سریع سال مالی:</div>
            <div class="fiscal-year-buttons">
                <button type="button" class="fiscal-year-quick" data-action="current-fiscal-year">
                    سال جاری (${persianCurrentYear})
                </button>
                <button type="button" class="fiscal-year-quick" data-action="prev-fiscal-year">
                    سال گذشته (${persianPrevYear})
                </button>
            </div>
        </div>
        `;
    }
    
    generateQuarterControls() {
        let html = '<div class="quarter-controls">';
        html += '<div class="quarter-title">انتخاب فصل مالی:</div>';
        html += '<div class="quarter-options">';
        
        this.persianQuarters.forEach((quarter, index) => {
            const quarterNum = index + 1;
            const persianQuarterNum = this.toPersianDigits(quarterNum.toString());
            const isSelected = quarterNum === this.selectedQuarter ? 'selected' : '';
            
            html += `
            <button type="button" class="quarter-option ${isSelected}" data-quarter="${quarterNum}">
                <div class="quarter-name">${quarter.name}</div>
                <div class="quarter-description">${quarter.description}</div>
            </button>
            `;
        });
        
        html += '</div></div>';
        return html;
    }
    
    getFirstDayWeekday(year, month) {
        // Convert to Gregorian to get weekday
        const gregorianDate = this.persianToGregorian(year, month, 1);
        const weekday = gregorianDate.getDay();
        // Convert to Persian weekday (Saturday = 0)
        return (weekday + 1) % 7;
    }
    
    handleDaySelection(year, month, day) {
        if (this.mode === 'range') {
            this.handleRangeDaySelection(year, month, day);
        } else {
            this.selectDate(year, month, day);
        }
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
        
        // Auto-hide calendar for single date selection
        if (this.mode === 'single') {
            setTimeout(() => this.hideCalendar(), 200);
        }
    }
    
    handleRangeDaySelection(year, month, day) {
        const selectedDate = { year, month, day };
        
        if (!this.selectedRange.start || (this.selectedRange.start && this.selectedRange.end)) {
            // Start new range selection
            this.selectedRange = { start: selectedDate, end: null };
        } else if (this.selectedRange.start && !this.selectedRange.end) {
            // Complete range selection
            const startDate = this.selectedRange.start;
            const endDate = selectedDate;
            
            // Ensure start is before end
            if (this.compareDates(startDate, endDate) > 0) {
                this.selectedRange = { start: endDate, end: startDate };
            } else {
                this.selectedRange = { start: startDate, end: endDate };
            }
            
            // Format and set input value for range
            this.setRangeInputValue();
        }
        
        // Update calendar display
        this.updateCalendarDays();
        
        // Trigger change event
        this.input.dispatchEvent(new Event('change', { bubbles: true }));
    }
    
    setRangeInputValue() {
        if (this.selectedRange.start && this.selectedRange.end) {
            const startFormatted = this.formatDateForDisplay(this.selectedRange.start);
            const endFormatted = this.formatDateForDisplay(this.selectedRange.end);
            this.input.value = `${startFormatted} تا ${endFormatted}`;
        } else if (this.selectedRange.start) {
            const startFormatted = this.formatDateForDisplay(this.selectedRange.start);
            this.input.value = `${startFormatted} تا ...`;
        }
    }
    
    formatDateForDisplay(dateObj) {
        const formattedDate = `${dateObj.year.toString().padStart(4, '0')}/${dateObj.month.toString().padStart(2, '0')}/${dateObj.day.toString().padStart(2, '0')}`;
        return this.toPersianDigits(formattedDate);
    }
    
    compareDates(date1, date2) {
        if (date1.year !== date2.year) return date1.year - date2.year;
        if (date1.month !== date2.month) return date1.month - date2.month;
        return date1.day - date2.day;
    }
    
    selectFiscalYear(year) {
        this.selectedFiscalYear = year;
        this.selectedRange = {
            start: { year, month: 1, day: 1 },
            end: { year, month: 12, day: this.getDaysInPersianMonth(year, 12) }
        };
        
        // Format fiscal year display
        const persianYear = this.toPersianDigits(year.toString());
        this.input.value = `سال مالی ${persianYear}`;
        
        // Update calendar display
        this.currentYear = year;
        this.currentMonth = 1;
        this.updateCalendar();
        
        // Trigger change event
        this.input.dispatchEvent(new Event('change', { bubbles: true }));
    }
    
    selectQuarter(quarter) {
        this.selectedQuarter = quarter;
        const currentYear = this.selectedFiscalYear || this.currentYear;
        const quarterInfo = this.persianQuarters[quarter - 1];
        
        this.selectedRange = {
            start: { year: currentYear, month: quarterInfo.months[0], day: 1 },
            end: { 
                year: currentYear, 
                month: quarterInfo.months[2], 
                day: this.getDaysInPersianMonth(currentYear, quarterInfo.months[2])
            }
        };
        
        // Format quarter display
        const persianYear = this.toPersianDigits(currentYear.toString());
        const persianQuarter = this.toPersianDigits(quarter.toString());
        this.input.value = `${quarterInfo.name} سال ${persianYear} (${quarterInfo.description})`;
        
        // Update calendar display
        this.updateCalendar();
        
        // Trigger change event
        this.input.dispatchEvent(new Event('change', { bubbles: true }));
    }
    
    toggleRangeMode() {
        this.mode = this.mode === 'range' ? 'single' : 'range';
        this.container.classList.toggle('range-mode');
        this.selectedRange = { start: null, end: null };
        this.updateCalendarDays();
    }
    
    clearDate() {
        this.selectedDate = null;
        this.selectedRange = { start: null, end: null };
        this.selectedFiscalYear = null;
        this.selectedQuarter = null;
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