/**
 * RTL Components and utilities for ZARGAR jewelry SaaS platform
 * Enhanced RTL support with Persian UI components and dual theme system
 */

class RTLComponents {
    constructor() {
        this.isRTL = document.documentElement.dir === 'rtl';
        this.currentTheme = document.body.classList.contains('dark') ? 'dark' : 'light';
        this.init();
    }

    init() {
        this.initializeComponents();
        this.setupEventListeners();
        this.initializeAnimations();
    }

    initializeComponents() {
        // Initialize Persian input components
        this.initializePersianInputs();
        
        // Initialize RTL-aware modals
        this.initializeModals();
        
        // Initialize Persian date pickers
        this.initializeDatePickers();
        
        // Initialize Persian number inputs
        this.initializeNumberInputs();
        
        // Initialize RTL tooltips
        this.initializeTooltips();
        
        // Initialize Persian form validation
        this.initializeFormValidation();
    }

    initializePersianInputs() {
        const persianInputs = document.querySelectorAll('[data-persian-input]');
        persianInputs.forEach(input => {
            this.setupPersianInput(input);
        });
    }

    setupPersianInput(input) {
        // Auto-convert English to Persian characters
        input.addEventListener('input', (e) => {
            const cursorPos = e.target.selectionStart;
            let value = e.target.value;
            
            // Convert English digits to Persian
            value = value.replace(/[0-9]/g, (digit) => {
                const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
                return persianDigits[parseInt(digit)];
            });
            
            // Convert common English characters to Persian
            const charMap = {
                'q': 'ض', 'w': 'ص', 'e': 'ث', 'r': 'ق', 't': 'ف',
                'y': 'غ', 'u': 'ع', 'i': 'ه', 'o': 'خ', 'p': 'ح',
                'a': 'ش', 's': 'س', 'd': 'ی', 'f': 'ب', 'g': 'ل',
                'h': 'ا', 'j': 'ت', 'k': 'ن', 'l': 'م', ';': 'ک',
                'z': 'ظ', 'x': 'ط', 'c': 'ز', 'v': 'ر', 'b': 'ذ',
                'n': 'د', 'm': 'پ', ',': 'و', '.': '.'
            };
            
            let converted = '';
            for (let char of value) {
                converted += charMap[char.toLowerCase()] || char;
            }
            
            if (converted !== value) {
                e.target.value = converted;
                e.target.setSelectionRange(cursorPos, cursorPos);
            }
        });

        // Add Persian input styling
        input.classList.add('persian-input');
        if (this.currentTheme === 'dark') {
            input.classList.add('cyber-input');
        }
    }

    initializeModals() {
        const modals = document.querySelectorAll('[data-modal]');
        modals.forEach(modal => {
            this.setupRTLModal(modal);
        });
    }

    setupRTLModal(modal) {
        // Ensure proper RTL positioning
        modal.style.direction = 'rtl';
        
        // Add RTL-aware animations
        const modalContent = modal.querySelector('.modal-content');
        if (modalContent) {
            modalContent.classList.add('rtl-modal-content');
        }
        
        // Setup close button positioning for RTL
        const closeButton = modal.querySelector('.modal-close');
        if (closeButton) {
            closeButton.classList.add('rtl-close-button');
        }
    }

    initializeDatePickers() {
        const datePickers = document.querySelectorAll('[data-persian-date]');
        datePickers.forEach(picker => {
            this.setupPersianDatePicker(picker);
        });
    }

    setupPersianDatePicker(picker) {
        // Create Persian calendar widget
        const calendar = this.createPersianCalendar();
        
        picker.addEventListener('focus', () => {
            this.showPersianCalendar(picker, calendar);
        });
        
        picker.addEventListener('blur', (e) => {
            // Delay hiding to allow calendar interaction
            setTimeout(() => {
                if (!calendar.contains(document.activeElement)) {
                    this.hidePersianCalendar(calendar);
                }
            }, 200);
        });
    }

    createPersianCalendar() {
        const calendar = document.createElement('div');
        calendar.className = `persian-calendar absolute z-50 mt-1 rounded-lg shadow-lg backdrop-blur-sm
                             ${this.currentTheme === 'dark' ? 
                               'bg-cyber-bg-surface/90 border border-cyber-border-glass' : 
                               'bg-white border border-gray-200'}`;
        
        // Add calendar content
        calendar.innerHTML = this.generateCalendarHTML();
        
        return calendar;
    }

    generateCalendarHTML() {
        const monthNames = [
            'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
            'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
        ];
        
        const dayNames = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج'];
        
        let html = `
            <div class="p-4">
                <div class="flex items-center justify-between mb-4">
                    <button class="p-1 rounded hover:bg-gray-100 dark:hover:bg-cyber-bg-elevated">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
                        </svg>
                    </button>
                    <div class="text-sm font-medium">
                        ${monthNames[5]} ۱۴۰۳
                    </div>
                    <button class="p-1 rounded hover:bg-gray-100 dark:hover:bg-cyber-bg-elevated">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                        </svg>
                    </button>
                </div>
                
                <div class="grid grid-cols-7 gap-1 mb-2">
                    ${dayNames.map(day => `
                        <div class="text-center text-xs font-medium p-2 
                                   ${this.currentTheme === 'dark' ? 'text-cyber-text-secondary' : 'text-gray-600'}">
                            ${day}
                        </div>
                    `).join('')}
                </div>
                
                <div class="grid grid-cols-7 gap-1">
                    ${Array.from({length: 30}, (_, i) => `
                        <button class="text-center text-sm p-2 rounded hover:bg-blue-100 dark:hover:bg-cyber-bg-elevated
                                       ${this.currentTheme === 'dark' ? 'text-cyber-text-primary' : 'text-gray-900'}"
                                data-date="${i + 1}">
                            ${this.toPersianDigits(i + 1)}
                        </button>
                    `).join('')}
                </div>
            </div>
        `;
        
        return html;
    }

    showPersianCalendar(input, calendar) {
        // Position calendar relative to input
        const rect = input.getBoundingClientRect();
        calendar.style.top = `${rect.bottom + window.scrollY}px`;
        calendar.style.right = `${window.innerWidth - rect.right}px`;
        
        document.body.appendChild(calendar);
        
        // Add event listeners for date selection
        calendar.addEventListener('click', (e) => {
            if (e.target.hasAttribute('data-date')) {
                const date = e.target.getAttribute('data-date');
                input.value = `۱۴۰۳/۰۶/${this.toPersianDigits(date.padStart(2, '0'))}`;
                this.hidePersianCalendar(calendar);
                input.dispatchEvent(new Event('change'));
            }
        });
    }

    hidePersianCalendar(calendar) {
        if (calendar.parentNode) {
            calendar.parentNode.removeChild(calendar);
        }
    }

    initializeNumberInputs() {
        const numberInputs = document.querySelectorAll('[data-persian-number]');
        numberInputs.forEach(input => {
            this.setupPersianNumberInput(input);
        });
    }

    setupPersianNumberInput(input) {
        input.addEventListener('input', (e) => {
            let value = e.target.value;
            
            // Convert English digits to Persian
            value = this.toPersianDigits(value);
            
            // Format as currency if specified
            if (input.hasAttribute('data-currency')) {
                value = this.formatPersianCurrency(value);
            }
            
            e.target.value = value;
        });
        
        // Add number input styling
        input.classList.add('persian-number-input');
        if (this.currentTheme === 'dark') {
            input.classList.add('cyber-number-input');
        }
    }

    initializeTooltips() {
        const tooltips = document.querySelectorAll('[data-tooltip]');
        tooltips.forEach(element => {
            this.setupRTLTooltip(element);
        });
    }

    setupRTLTooltip(element) {
        const tooltip = document.createElement('div');
        tooltip.className = `absolute z-50 px-2 py-1 text-xs rounded shadow-lg pointer-events-none opacity-0 transition-opacity duration-200
                            ${this.currentTheme === 'dark' ? 
                              'bg-cyber-bg-elevated text-cyber-text-primary border border-cyber-border-glass' : 
                              'bg-gray-900 text-white'}`;
        tooltip.textContent = element.getAttribute('data-tooltip');
        
        element.addEventListener('mouseenter', () => {
            document.body.appendChild(tooltip);
            this.positionRTLTooltip(element, tooltip);
            tooltip.classList.remove('opacity-0');
        });
        
        element.addEventListener('mouseleave', () => {
            tooltip.classList.add('opacity-0');
            setTimeout(() => {
                if (tooltip.parentNode) {
                    tooltip.parentNode.removeChild(tooltip);
                }
            }, 200);
        });
    }

    positionRTLTooltip(element, tooltip) {
        const rect = element.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        
        // Position above element, aligned to the right for RTL
        tooltip.style.top = `${rect.top - tooltipRect.height - 8 + window.scrollY}px`;
        tooltip.style.right = `${window.innerWidth - rect.right}px`;
    }

    initializeFormValidation() {
        const forms = document.querySelectorAll('[data-persian-validation]');
        forms.forEach(form => {
            this.setupPersianFormValidation(form);
        });
    }

    setupPersianFormValidation(form) {
        form.addEventListener('submit', (e) => {
            const validation = this.validatePersianForm(form);
            if (!validation.isValid) {
                e.preventDefault();
                this.showValidationErrors(form, validation.errors);
            }
        });
    }

    validatePersianForm(form) {
        const errors = [];
        const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
        
        inputs.forEach(input => {
            const value = input.value.trim();
            const label = input.getAttribute('data-label') || input.name;
            
            if (!value) {
                errors.push(`${label} الزامی است`);
                this.addErrorStyling(input);
            } else {
                this.removeErrorStyling(input);
                
                // Specific validations
                if (input.type === 'tel' && !this.validatePersianPhone(value)) {
                    errors.push(`شماره تلفن ${label} معتبر نیست`);
                    this.addErrorStyling(input);
                }
                
                if (input.hasAttribute('data-national-id') && !this.validateNationalId(value)) {
                    errors.push(`کد ملی ${label} معتبر نیست`);
                    this.addErrorStyling(input);
                }
            }
        });
        
        return {
            isValid: errors.length === 0,
            errors: errors
        };
    }

    addErrorStyling(input) {
        input.classList.add('error');
        if (this.currentTheme === 'dark') {
            input.classList.add('cyber-error');
        }
    }

    removeErrorStyling(input) {
        input.classList.remove('error', 'cyber-error');
    }

    showValidationErrors(form, errors) {
        let errorContainer = form.querySelector('.form-errors');
        if (!errorContainer) {
            errorContainer = document.createElement('div');
            errorContainer.className = 'form-errors mb-4';
            form.insertBefore(errorContainer, form.firstChild);
        }
        
        errorContainer.innerHTML = `
            <div class="p-4 rounded-lg border
                       ${this.currentTheme === 'dark' ? 
                         'bg-red-900/20 border-red-500/50 text-red-200' : 
                         'bg-red-50 border-red-200 text-red-800'}">
                <div class="flex items-center mb-2">
                    <svg class="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <h4 class="font-medium">خطاهای فرم:</h4>
                </div>
                <ul class="list-disc list-inside space-y-1">
                    ${errors.map(error => `<li>${error}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    setupEventListeners() {
        // Listen for theme changes
        window.addEventListener('themeChanged', (e) => {
            this.currentTheme = e.detail.theme;
            this.updateComponentThemes();
        });
        
        // Listen for dynamic content changes
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            this.initializeNewComponents(node);
                        }
                    });
                }
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    initializeNewComponents(container) {
        // Initialize components in newly added content
        const persianInputs = container.querySelectorAll('[data-persian-input]');
        persianInputs.forEach(input => this.setupPersianInput(input));
        
        const datePickers = container.querySelectorAll('[data-persian-date]');
        datePickers.forEach(picker => this.setupPersianDatePicker(picker));
        
        const numberInputs = container.querySelectorAll('[data-persian-number]');
        numberInputs.forEach(input => this.setupPersianNumberInput(input));
        
        const tooltips = container.querySelectorAll('[data-tooltip]');
        tooltips.forEach(element => this.setupRTLTooltip(element));
    }

    updateComponentThemes() {
        // Update component themes when theme changes
        const components = document.querySelectorAll('.persian-input, .persian-number-input');
        components.forEach(component => {
            if (this.currentTheme === 'dark') {
                component.classList.add('cyber-input');
            } else {
                component.classList.remove('cyber-input');
            }
        });
    }

    initializeAnimations() {
        if (this.currentTheme === 'dark' && window.Motion) {
            this.initializeCyberAnimations();
        }
    }

    initializeCyberAnimations() {
        // Animate cards on page load
        const cards = document.querySelectorAll('.cyber-glass-card');
        cards.forEach((card, index) => {
            window.Motion.animate(card, {
                opacity: [0, 1],
                y: [20, 0],
                scale: [0.95, 1]
            }, {
                duration: 0.4,
                delay: index * 0.1,
                ease: [0.4, 0, 0.2, 1]
            });
        });
        
        // Animate buttons on hover
        const buttons = document.querySelectorAll('.cyber-neon-button');
        buttons.forEach(button => {
            button.addEventListener('mouseenter', () => {
                if (window.Motion) {
                    window.Motion.animate(button, {
                        scale: [1, 1.05]
                    }, {
                        duration: 0.2,
                        ease: 'easeOut'
                    });
                }
            });
            
            button.addEventListener('mouseleave', () => {
                if (window.Motion) {
                    window.Motion.animate(button, {
                        scale: [1.05, 1]
                    }, {
                        duration: 0.2,
                        ease: 'easeOut'
                    });
                }
            });
        });
    }

    // Utility methods
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

    formatPersianCurrency(value) {
        const numericValue = this.toEnglishDigits(value).replace(/[^\d]/g, '');
        if (!numericValue) return '';
        
        const formatted = new Intl.NumberFormat('fa-IR').format(parseInt(numericValue));
        return this.toPersianDigits(formatted) + ' تومان';
    }

    validatePersianPhone(phone) {
        const englishPhone = this.toEnglishDigits(phone);
        const phoneRegex = /^09[0-9]{9}$/;
        return phoneRegex.test(englishPhone);
    }

    validateNationalId(nationalId) {
        const englishId = this.toEnglishDigits(nationalId);
        const nationalIdRegex = /^[0-9]{10}$/;
        
        if (!nationalIdRegex.test(englishId)) return false;
        
        // Iranian national ID checksum validation
        const digits = englishId.split('').map(d => parseInt(d));
        const checksum = digits[9];
        let sum = 0;
        
        for (let i = 0; i < 9; i++) {
            sum += digits[i] * (10 - i);
        }
        
        const remainder = sum % 11;
        return (remainder < 2 && checksum === remainder) || 
               (remainder >= 2 && checksum === 11 - remainder);
    }
}

// Initialize RTL components when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.rtlComponents = new RTLComponents();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RTLComponents;
}