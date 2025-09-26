/**
 * RTL-enhanced Flowbite components for ZARGAR jewelry SaaS platform
 * Provides Persian-native UI components with dual theme support
 */

class RTLFlowbiteComponents {
    constructor() {
        this.isRTL = document.documentElement.dir === 'rtl';
        this.currentTheme = document.body.classList.contains('dark') ? 'dark' : 'light';
        this.components = new Map();
        this.init();
    }

    init() {
        this.initializeFlowbiteComponents();
        this.enhanceForRTL();
        this.setupThemeIntegration();
        this.createCustomComponents();
    }

    initializeFlowbiteComponents() {
        // Initialize Flowbite components with RTL awareness
        if (window.Flowbite) {
            window.Flowbite.init();
        }
    }

    enhanceForRTL() {
        // Enhance existing Flowbite components for RTL
        this.enhanceDropdowns();
        this.enhanceModals();
        this.enhanceTooltips();
        this.enhanceAccordions();
        this.enhanceTabs();
        this.enhanceCarousels();
    }

    enhanceDropdowns() {
        const dropdowns = document.querySelectorAll('[data-dropdown-toggle]');
        dropdowns.forEach(dropdown => {
            const targetId = dropdown.getAttribute('data-dropdown-toggle');
            const target = document.getElementById(targetId);
            
            if (target) {
                // Add RTL positioning
                target.classList.add('rtl-dropdown');
                
                // Adjust positioning for RTL
                const placement = dropdown.getAttribute('data-dropdown-placement') || 'bottom-start';
                const rtlPlacement = this.convertPlacementForRTL(placement);
                dropdown.setAttribute('data-dropdown-placement', rtlPlacement);
                
                // Add Persian styling
                if (this.currentTheme === 'dark') {
                    target.classList.add('cyber-dropdown');
                } else {
                    target.classList.add('light-dropdown');
                }
            }
        });
    }

    enhanceModals() {
        const modals = document.querySelectorAll('[data-modal-toggle]');
        modals.forEach(modal => {
            const targetId = modal.getAttribute('data-modal-toggle');
            const target = document.getElementById(targetId);
            
            if (target) {
                // Add RTL modal enhancements
                target.classList.add('rtl-modal');
                
                // Enhance modal content
                const modalContent = target.querySelector('.modal-content, [data-modal-body]');
                if (modalContent) {
                    modalContent.style.direction = 'rtl';
                    modalContent.style.textAlign = 'right';
                }
                
                // Position close button for RTL
                const closeButton = target.querySelector('[data-modal-hide]');
                if (closeButton) {
                    closeButton.classList.add('rtl-modal-close');
                }
                
                // Add theme-specific styling
                if (this.currentTheme === 'dark') {
                    target.classList.add('cyber-modal');
                } else {
                    target.classList.add('light-modal');
                }
            }
        });
    }

    enhanceTooltips() {
        const tooltips = document.querySelectorAll('[data-tooltip-target]');
        tooltips.forEach(tooltip => {
            const targetId = tooltip.getAttribute('data-tooltip-target');
            const target = document.getElementById(targetId);
            
            if (target) {
                // Add RTL tooltip positioning
                const placement = tooltip.getAttribute('data-tooltip-placement') || 'top';
                const rtlPlacement = this.convertPlacementForRTL(placement);
                tooltip.setAttribute('data-tooltip-placement', rtlPlacement);
                
                // Add Persian styling
                target.classList.add('persian-tooltip');
                if (this.currentTheme === 'dark') {
                    target.classList.add('cyber-tooltip');
                } else {
                    target.classList.add('light-tooltip');
                }
            }
        });
    }

    enhanceAccordions() {
        const accordions = document.querySelectorAll('[data-accordion]');
        accordions.forEach(accordion => {
            // Add RTL accordion styling
            accordion.classList.add('rtl-accordion');
            
            // Enhance accordion items
            const items = accordion.querySelectorAll('[data-accordion-target]');
            items.forEach(item => {
                // Flip chevron icons for RTL
                const chevron = item.querySelector('svg');
                if (chevron) {
                    chevron.classList.add('rtl-flip');
                }
                
                // Add Persian styling
                if (this.currentTheme === 'dark') {
                    item.classList.add('cyber-accordion-item');
                } else {
                    item.classList.add('light-accordion-item');
                }
            });
        });
    }

    enhanceTabs() {
        const tabGroups = document.querySelectorAll('[role="tablist"]');
        tabGroups.forEach(tabGroup => {
            // Add RTL tab styling
            tabGroup.classList.add('rtl-tabs');
            
            // Enhance tab items
            const tabs = tabGroup.querySelectorAll('[role="tab"]');
            tabs.forEach(tab => {
                if (this.currentTheme === 'dark') {
                    tab.classList.add('cyber-tab');
                } else {
                    tab.classList.add('light-tab');
                }
            });
        });
    }

    enhanceCarousels() {
        const carousels = document.querySelectorAll('[data-carousel]');
        carousels.forEach(carousel => {
            // Add RTL carousel styling
            carousel.classList.add('rtl-carousel');
            
            // Flip navigation buttons for RTL
            const prevButton = carousel.querySelector('[data-carousel-prev]');
            const nextButton = carousel.querySelector('[data-carousel-next]');
            
            if (prevButton && nextButton) {
                // Swap button positions for RTL
                const prevIcon = prevButton.querySelector('svg');
                const nextIcon = nextButton.querySelector('svg');
                
                if (prevIcon) prevIcon.classList.add('rtl-flip');
                if (nextIcon) nextIcon.classList.add('rtl-flip');
            }
        });
    }

    setupThemeIntegration() {
        // Listen for theme changes
        window.addEventListener('themeChanged', (e) => {
            this.currentTheme = e.detail.theme;
            this.updateComponentThemes();
        });
    }

    updateComponentThemes() {
        // Update all components when theme changes
        this.updateDropdownThemes();
        this.updateModalThemes();
        this.updateTooltipThemes();
        this.updateAccordionThemes();
        this.updateTabThemes();
    }

    updateDropdownThemes() {
        const dropdowns = document.querySelectorAll('.rtl-dropdown');
        dropdowns.forEach(dropdown => {
            dropdown.classList.remove('cyber-dropdown', 'light-dropdown');
            if (this.currentTheme === 'dark') {
                dropdown.classList.add('cyber-dropdown');
            } else {
                dropdown.classList.add('light-dropdown');
            }
        });
    }

    updateModalThemes() {
        const modals = document.querySelectorAll('.rtl-modal');
        modals.forEach(modal => {
            modal.classList.remove('cyber-modal', 'light-modal');
            if (this.currentTheme === 'dark') {
                modal.classList.add('cyber-modal');
            } else {
                modal.classList.add('light-modal');
            }
        });
    }

    updateTooltipThemes() {
        const tooltips = document.querySelectorAll('.persian-tooltip');
        tooltips.forEach(tooltip => {
            tooltip.classList.remove('cyber-tooltip', 'light-tooltip');
            if (this.currentTheme === 'dark') {
                tooltip.classList.add('cyber-tooltip');
            } else {
                tooltip.classList.add('light-tooltip');
            }
        });
    }

    updateAccordionThemes() {
        const accordions = document.querySelectorAll('.rtl-accordion [data-accordion-target]');
        accordions.forEach(accordion => {
            accordion.classList.remove('cyber-accordion-item', 'light-accordion-item');
            if (this.currentTheme === 'dark') {
                accordion.classList.add('cyber-accordion-item');
            } else {
                accordion.classList.add('light-accordion-item');
            }
        });
    }

    updateTabThemes() {
        const tabs = document.querySelectorAll('.rtl-tabs [role="tab"]');
        tabs.forEach(tab => {
            tab.classList.remove('cyber-tab', 'light-tab');
            if (this.currentTheme === 'dark') {
                tab.classList.add('cyber-tab');
            } else {
                tab.classList.add('light-tab');
            }
        });
    }

    createCustomComponents() {
        this.createPersianDatePicker();
        this.createPersianNumberInput();
        this.createGoldCalculatorWidget();
        this.createPersianSearchBox();
        this.createNotificationToast();
    }

    createPersianDatePicker() {
        const datePickers = document.querySelectorAll('[data-persian-datepicker]');
        datePickers.forEach(picker => {
            const component = new PersianDatePickerComponent(picker, this.currentTheme);
            this.components.set(picker, component);
        });
    }

    createPersianNumberInput() {
        const numberInputs = document.querySelectorAll('[data-persian-number-input]');
        numberInputs.forEach(input => {
            const component = new PersianNumberInputComponent(input, this.currentTheme);
            this.components.set(input, component);
        });
    }

    createGoldCalculatorWidget() {
        const calculators = document.querySelectorAll('[data-gold-calculator]');
        calculators.forEach(calculator => {
            const component = new GoldCalculatorComponent(calculator, this.currentTheme);
            this.components.set(calculator, component);
        });
    }

    createPersianSearchBox() {
        const searchBoxes = document.querySelectorAll('[data-persian-search]');
        searchBoxes.forEach(searchBox => {
            const component = new PersianSearchComponent(searchBox, this.currentTheme);
            this.components.set(searchBox, component);
        });
    }

    createNotificationToast() {
        // Create notification system
        this.notificationSystem = new PersianNotificationSystem(this.currentTheme);
    }

    convertPlacementForRTL(placement) {
        const rtlMap = {
            'top-start': 'top-end',
            'top-end': 'top-start',
            'bottom-start': 'bottom-end',
            'bottom-end': 'bottom-start',
            'left': 'right',
            'right': 'left',
            'left-start': 'right-start',
            'left-end': 'right-end',
            'right-start': 'left-start',
            'right-end': 'left-end'
        };
        
        return rtlMap[placement] || placement;
    }

    // Public API methods
    showNotification(message, type = 'info', duration = 5000) {
        if (this.notificationSystem) {
            this.notificationSystem.show(message, type, duration);
        }
    }

    getComponent(element) {
        return this.components.get(element);
    }

    destroyComponent(element) {
        const component = this.components.get(element);
        if (component && component.destroy) {
            component.destroy();
        }
        this.components.delete(element);
    }
}

// Persian Date Picker Component
class PersianDatePickerComponent {
    constructor(element, theme) {
        this.element = element;
        this.theme = theme;
        this.isOpen = false;
        this.selectedDate = null;
        this.init();
    }

    init() {
        this.createDatePicker();
        this.setupEventListeners();
    }

    createDatePicker() {
        // Create date picker HTML structure
        const pickerHTML = `
            <div class="relative">
                <input type="text" 
                       class="persian-input w-full ${this.theme === 'dark' ? 'dark' : ''}"
                       placeholder="تاریخ را انتخاب کنید"
                       readonly>
                <div class="absolute left-3 top-1/2 transform -translate-y-1/2 pointer-events-none">
                    <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                    </svg>
                </div>
                <div class="persian-calendar absolute z-50 mt-1 hidden">
                    ${this.generateCalendarHTML()}
                </div>
            </div>
        `;
        
        this.element.innerHTML = pickerHTML;
        this.input = this.element.querySelector('input');
        this.calendar = this.element.querySelector('.persian-calendar');
    }

    generateCalendarHTML() {
        const monthNames = [
            'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
            'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
        ];
        
        const dayNames = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج'];
        
        return `
            <div class="p-4 rounded-lg shadow-lg backdrop-blur-sm
                        ${this.theme === 'dark' ? 
                          'bg-cyber-bg-surface/90 border border-cyber-border-glass' : 
                          'bg-white border border-gray-200'}">
                <div class="flex items-center justify-between mb-4">
                    <button class="p-1 rounded hover:bg-gray-100 dark:hover:bg-cyber-bg-elevated" 
                            data-prev-month>
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
                        </svg>
                    </button>
                    <div class="text-sm font-medium" data-month-year>
                        شهریور ۱۴۰۳
                    </div>
                    <button class="p-1 rounded hover:bg-gray-100 dark:hover:bg-cyber-bg-elevated" 
                            data-next-month>
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                        </svg>
                    </button>
                </div>
                
                <div class="grid grid-cols-7 gap-1 mb-2">
                    ${dayNames.map(day => `
                        <div class="text-center text-xs font-medium p-2 
                                   ${this.theme === 'dark' ? 'text-cyber-text-secondary' : 'text-gray-600'}">
                            ${day}
                        </div>
                    `).join('')}
                </div>
                
                <div class="grid grid-cols-7 gap-1" data-calendar-days>
                    ${this.generateDaysHTML()}
                </div>
            </div>
        `;
    }

    generateDaysHTML() {
        // Generate days for current month (simplified)
        let daysHTML = '';
        for (let i = 1; i <= 30; i++) {
            daysHTML += `
                <button class="text-center text-sm p-2 rounded hover:bg-blue-100 dark:hover:bg-cyber-bg-elevated
                               ${this.theme === 'dark' ? 'text-cyber-text-primary' : 'text-gray-900'}"
                        data-date="${i}">
                    ${this.toPersianDigits(i)}
                </button>
            `;
        }
        return daysHTML;
    }

    setupEventListeners() {
        // Input click to show calendar
        this.input.addEventListener('click', () => {
            this.toggleCalendar();
        });

        // Calendar date selection
        this.calendar.addEventListener('click', (e) => {
            if (e.target.hasAttribute('data-date')) {
                const date = e.target.getAttribute('data-date');
                this.selectDate(date);
            }
        });

        // Close calendar when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.element.contains(e.target)) {
                this.hideCalendar();
            }
        });
    }

    toggleCalendar() {
        if (this.isOpen) {
            this.hideCalendar();
        } else {
            this.showCalendar();
        }
    }

    showCalendar() {
        this.calendar.classList.remove('hidden');
        this.isOpen = true;
    }

    hideCalendar() {
        this.calendar.classList.add('hidden');
        this.isOpen = false;
    }

    selectDate(day) {
        const formattedDate = `۱۴۰۳/۰۶/${this.toPersianDigits(day.padStart(2, '0'))}`;
        this.input.value = formattedDate;
        this.selectedDate = formattedDate;
        this.hideCalendar();
        
        // Dispatch change event
        this.input.dispatchEvent(new Event('change'));
    }

    toPersianDigits(str) {
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return str.toString().replace(/\d/g, (digit) => {
            return persianDigits[parseInt(digit)];
        });
    }
}

// Persian Number Input Component
class PersianNumberInputComponent {
    constructor(element, theme) {
        this.element = element;
        this.theme = theme;
        this.isCurrency = element.hasAttribute('data-currency');
        this.init();
    }

    init() {
        this.setupInput();
        this.setupEventListeners();
    }

    setupInput() {
        this.element.classList.add('persian-input');
        if (this.theme === 'dark') {
            this.element.classList.add('dark');
        }
        
        if (this.isCurrency) {
            this.element.classList.add('persian-currency-input');
        }
    }

    setupEventListeners() {
        this.element.addEventListener('input', (e) => {
            this.formatInput(e);
        });

        this.element.addEventListener('keydown', (e) => {
            this.handleKeydown(e);
        });
    }

    formatInput(e) {
        let value = e.target.value;
        
        // Convert English digits to Persian
        value = this.toPersianDigits(value);
        
        // Format as currency if specified
        if (this.isCurrency) {
            value = this.formatCurrency(value);
        }
        
        e.target.value = value;
    }

    handleKeydown(e) {
        // Allow: backspace, delete, tab, escape, enter
        if ([8, 9, 27, 13, 46].indexOf(e.keyCode) !== -1 ||
            // Allow: Ctrl+A, Ctrl+C, Ctrl+V, Ctrl+X
            (e.keyCode === 65 && e.ctrlKey === true) ||
            (e.keyCode === 67 && e.ctrlKey === true) ||
            (e.keyCode === 86 && e.ctrlKey === true) ||
            (e.keyCode === 88 && e.ctrlKey === true)) {
            return;
        }
        
        // Ensure that it is a number and stop the keypress
        if ((e.shiftKey || (e.keyCode < 48 || e.keyCode > 57)) && (e.keyCode < 96 || e.keyCode > 105)) {
            e.preventDefault();
        }
    }

    formatCurrency(value) {
        // Remove non-numeric characters except Persian digits
        const numericValue = this.toEnglishDigits(value).replace(/[^\d]/g, '');
        if (!numericValue) return '';
        
        // Format with thousand separators
        const formatted = new Intl.NumberFormat('fa-IR').format(parseInt(numericValue));
        return this.toPersianDigits(formatted) + ' تومان';
    }

    toPersianDigits(str) {
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return str.toString().replace(/\d/g, (digit) => {
            return persianDigits[parseInt(digit)];
        });
    }

    toEnglishDigits(str) {
        const englishDigits = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return str.toString().replace(/[۰-۹]/g, (digit) => {
            return englishDigits[persianDigits.indexOf(digit)];
        });
    }
}

// Gold Calculator Component
class GoldCalculatorComponent {
    constructor(element, theme) {
        this.element = element;
        this.theme = theme;
        this.currentGoldPrice = 0;
        this.init();
    }

    init() {
        this.createCalculator();
        this.setupEventListeners();
        this.loadGoldPrice();
    }

    createCalculator() {
        const calculatorHTML = `
            <div class="${this.theme === 'dark' ? 'cyber-glass-card' : 'light-card'} p-6">
                <h3 class="text-lg font-semibold mb-4 
                          ${this.theme === 'dark' ? 'text-cyber-text-primary' : 'text-gray-900'}">
                    محاسبه‌گر طلا
                </h3>
                
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium mb-2">وزن (گرم)</label>
                        <input type="text" 
                               class="persian-input w-full ${this.theme === 'dark' ? 'dark' : ''}"
                               data-weight
                               placeholder="وزن را وارد کنید">
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium mb-2">عیار</label>
                        <select class="persian-input w-full ${this.theme === 'dark' ? 'dark' : ''}" data-karat>
                            <option value="24">۲۴ عیار</option>
                            <option value="22">۲۲ عیار</option>
                            <option value="21">۲۱ عیار</option>
                            <option value="18">۱۸ عیار</option>
                            <option value="14">۱۴ عیار</option>
                        </select>
                    </div>
                    
                    <div class="pt-4 border-t ${this.theme === 'dark' ? 'border-cyber-border-glass' : 'border-gray-200'}">
                        <div class="flex justify-between items-center mb-2">
                            <span>قیمت طلای خالص:</span>
                            <span class="font-semibold ${this.theme === 'dark' ? 'cyber-number-glow' : 'text-green-600'}" 
                                  data-pure-gold-value>۰ تومان</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span>ارزش کل:</span>
                            <span class="font-bold text-lg ${this.theme === 'dark' ? 'cyber-number-glow' : 'text-green-600'}" 
                                  data-total-value>۰ تومان</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.element.innerHTML = calculatorHTML;
        
        // Get references to inputs
        this.weightInput = this.element.querySelector('[data-weight]');
        this.karatSelect = this.element.querySelector('[data-karat]');
        this.pureGoldValueSpan = this.element.querySelector('[data-pure-gold-value]');
        this.totalValueSpan = this.element.querySelector('[data-total-value]');
    }

    setupEventListeners() {
        this.weightInput.addEventListener('input', () => {
            this.calculate();
        });

        this.karatSelect.addEventListener('change', () => {
            this.calculate();
        });
    }

    async loadGoldPrice() {
        try {
            // In a real implementation, this would fetch from the gold price API
            // For now, use a mock price
            this.currentGoldPrice = 2500000; // 2.5M Toman per gram
            this.calculate();
        } catch (error) {
            console.error('Failed to load gold price:', error);
        }
    }

    calculate() {
        const weight = parseFloat(this.toEnglishDigits(this.weightInput.value)) || 0;
        const karat = parseInt(this.karatSelect.value) || 24;
        
        if (weight > 0 && this.currentGoldPrice > 0) {
            const purity = this.getKaratPurity(karat);
            const pureGoldWeight = weight * purity;
            const totalValue = pureGoldWeight * this.currentGoldPrice;
            
            this.pureGoldValueSpan.textContent = this.formatCurrency(pureGoldWeight * this.currentGoldPrice);
            this.totalValueSpan.textContent = this.formatCurrency(totalValue);
        } else {
            this.pureGoldValueSpan.textContent = '۰ تومان';
            this.totalValueSpan.textContent = '۰ تومان';
        }
    }

    getKaratPurity(karat) {
        const purities = {
            24: 1.0,
            22: 0.916,
            21: 0.875,
            18: 0.750,
            14: 0.583
        };
        return purities[karat] || 1.0;
    }

    formatCurrency(amount) {
        const formatted = new Intl.NumberFormat('fa-IR').format(Math.round(amount));
        return this.toPersianDigits(formatted) + ' تومان';
    }

    toPersianDigits(str) {
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return str.toString().replace(/\d/g, (digit) => {
            return persianDigits[parseInt(digit)];
        });
    }

    toEnglishDigits(str) {
        const englishDigits = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return str.toString().replace(/[۰-۹]/g, (digit) => {
            return englishDigits[persianDigits.indexOf(digit)];
        });
    }
}

// Persian Search Component
class PersianSearchComponent {
    constructor(element, theme) {
        this.element = element;
        this.theme = theme;
        this.results = [];
        this.isOpen = false;
        this.init();
    }

    init() {
        this.createSearchBox();
        this.setupEventListeners();
    }

    createSearchBox() {
        const searchHTML = `
            <div class="relative">
                <div class="relative">
                    <input type="text" 
                           class="persian-input w-full pr-10 ${this.theme === 'dark' ? 'dark' : ''}"
                           placeholder="جستجو..."
                           data-search-input>
                    <div class="absolute right-3 top-1/2 transform -translate-y-1/2">
                        <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                        </svg>
                    </div>
                </div>
                
                <div class="search-results absolute z-50 w-full mt-1 hidden">
                    <div class="rounded-lg shadow-lg backdrop-blur-sm max-h-60 overflow-y-auto
                                ${this.theme === 'dark' ? 
                                  'bg-cyber-bg-surface/90 border border-cyber-border-glass' : 
                                  'bg-white border border-gray-200'}">
                        <div class="p-2" data-results-container>
                            <!-- Search results will be inserted here -->
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.element.innerHTML = searchHTML;
        
        this.searchInput = this.element.querySelector('[data-search-input]');
        this.resultsContainer = this.element.querySelector('[data-results-container]');
        this.resultsDropdown = this.element.querySelector('.search-results');
    }

    setupEventListeners() {
        let searchTimeout;
        
        this.searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.performSearch(e.target.value);
            }, 300);
        });

        this.searchInput.addEventListener('focus', () => {
            if (this.results.length > 0) {
                this.showResults();
            }
        });

        document.addEventListener('click', (e) => {
            if (!this.element.contains(e.target)) {
                this.hideResults();
            }
        });
    }

    async performSearch(query) {
        if (query.length < 2) {
            this.hideResults();
            return;
        }

        try {
            // In a real implementation, this would make an API call
            // For now, use mock data
            this.results = this.getMockResults(query);
            this.displayResults();
        } catch (error) {
            console.error('Search failed:', error);
        }
    }

    getMockResults(query) {
        const mockData = [
            { id: 1, title: 'گردنبند طلا', type: 'jewelry', price: '۱۵,۰۰۰,۰۰۰ تومان' },
            { id: 2, title: 'انگشتر نقره', type: 'jewelry', price: '۲,۵۰۰,۰۰۰ تومان' },
            { id: 3, title: 'دستبند طلا', type: 'jewelry', price: '۸,۰۰۰,۰۰۰ تومان' },
            { id: 4, title: 'احمد محمدی', type: 'customer', phone: '۰۹۱۲۳۴۵۶۷۸۹' },
            { id: 5, title: 'فاطمه احمدی', type: 'customer', phone: '۰۹۸۷۶۵۴۳۲۱۰' }
        ];

        return mockData.filter(item => 
            item.title.includes(query) || 
            (item.phone && item.phone.includes(query))
        );
    }

    displayResults() {
        if (this.results.length === 0) {
            this.resultsContainer.innerHTML = `
                <div class="p-3 text-center ${this.theme === 'dark' ? 'text-cyber-text-secondary' : 'text-gray-500'}">
                    نتیجه‌ای یافت نشد
                </div>
            `;
        } else {
            this.resultsContainer.innerHTML = this.results.map(result => `
                <div class="p-3 cursor-pointer rounded hover:bg-gray-100 dark:hover:bg-cyber-bg-elevated
                           ${this.theme === 'dark' ? 'text-cyber-text-primary' : 'text-gray-900'}"
                     data-result-id="${result.id}">
                    <div class="font-medium">${result.title}</div>
                    <div class="text-sm ${this.theme === 'dark' ? 'text-cyber-text-secondary' : 'text-gray-600'}">
                        ${result.type === 'jewelry' ? result.price : result.phone}
                    </div>
                </div>
            `).join('');
        }
        
        this.showResults();
    }

    showResults() {
        this.resultsDropdown.classList.remove('hidden');
        this.isOpen = true;
    }

    hideResults() {
        this.resultsDropdown.classList.add('hidden');
        this.isOpen = false;
    }
}

// Persian Notification System
class PersianNotificationSystem {
    constructor(theme) {
        this.theme = theme;
        this.notifications = [];
        this.container = this.createContainer();
    }

    createContainer() {
        const container = document.createElement('div');
        container.className = 'fixed top-4 right-4 z-50 space-y-2';
        container.id = 'persian-notifications';
        document.body.appendChild(container);
        return container;
    }

    show(message, type = 'info', duration = 5000) {
        const notification = this.createNotification(message, type);
        this.container.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.remove('translate-x-full', 'opacity-0');
        }, 10);
        
        // Auto remove
        setTimeout(() => {
            this.remove(notification);
        }, duration);
        
        return notification;
    }

    createNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `
            transform translate-x-full opacity-0 transition-all duration-300
            max-w-sm p-4 rounded-lg shadow-lg backdrop-blur-sm
            ${this.getTypeClasses(type)}
        `;
        
        notification.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center">
                    ${this.getTypeIcon(type)}
                    <p class="mr-3 text-sm font-medium">${message}</p>
                </div>
                <button class="mr-2 text-current opacity-70 hover:opacity-100 transition-opacity" 
                        onclick="this.parentElement.parentElement.remove()">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        `;
        
        return notification;
    }

    getTypeClasses(type) {
        const baseClasses = this.theme === 'dark' ? 'border' : 'border';
        
        switch (type) {
            case 'success':
                return this.theme === 'dark' 
                    ? `${baseClasses} bg-green-900/80 border-green-500/50 text-green-200`
                    : `${baseClasses} bg-green-50 border-green-200 text-green-800`;
            case 'error':
                return this.theme === 'dark'
                    ? `${baseClasses} bg-red-900/80 border-red-500/50 text-red-200`
                    : `${baseClasses} bg-red-50 border-red-200 text-red-800`;
            case 'warning':
                return this.theme === 'dark'
                    ? `${baseClasses} bg-yellow-900/80 border-yellow-500/50 text-yellow-200`
                    : `${baseClasses} bg-yellow-50 border-yellow-200 text-yellow-800`;
            default:
                return this.theme === 'dark'
                    ? `${baseClasses} bg-cyber-bg-surface/80 border-cyber-neon-primary/30 text-cyber-text-primary`
                    : `${baseClasses} bg-blue-50 border-blue-200 text-blue-800`;
        }
    }

    getTypeIcon(type) {
        const iconClass = "w-5 h-5 ml-2";
        
        switch (type) {
            case 'success':
                return `<svg class="${iconClass}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>`;
            case 'error':
                return `<svg class="${iconClass}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>`;
            case 'warning':
                return `<svg class="${iconClass}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z"></path>
                </svg>`;
            default:
                return `<svg class="${iconClass}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>`;
        }
    }

    remove(notification) {
        notification.classList.add('translate-x-full', 'opacity-0');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }
}

// Initialize RTL Flowbite Components when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.rtlFlowbiteComponents = new RTLFlowbiteComponents();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        RTLFlowbiteComponents,
        PersianDatePickerComponent,
        PersianNumberInputComponent,
        GoldCalculatorComponent,
        PersianSearchComponent,
        PersianNotificationSystem
    };
}