/**
 * Persian utilities for ZARGAR jewelry SaaS platform
 * Handles Persian calendar, number formatting, and RTL layout utilities
 */

class PersianCalendar {
    static monthNames = [
        'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
        'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
    ];

    static dayNames = [
        'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه', 'شنبه'
    ];

    static formatDate(shamsiDate) {
        if (!shamsiDate) return '';
        
        const parts = shamsiDate.split('/');
        if (parts.length !== 3) return shamsiDate;
        
        const year = parseInt(parts[0]);
        const month = parseInt(parts[1]) - 1;
        const day = parseInt(parts[2]);
        
        return `${PersianNumbers.toPersian(day.toString())} ${this.monthNames[month]} ${PersianNumbers.toPersian(year.toString())}`;
    }

    static getCurrentShamsiDate() {
        // This would typically come from the server
        // For now, return a placeholder
        const now = new Date();
        return {
            year: 1403,
            month: 6,
            day: 29,
            formatted: '۱۴۰۳/۰۶/۲۹'
        };
    }
}

class PersianValidation {
    static phoneRegex = /^09[0-9]{9}$/;
    static nationalIdRegex = /^[0-9]{10}$/;

    static validatePhone(phone) {
        const englishPhone = PersianNumbers.toEnglish(phone);
        return this.phoneRegex.test(englishPhone);
    }

    static validateNationalId(nationalId) {
        const englishId = PersianNumbers.toEnglish(nationalId);
        if (!this.nationalIdRegex.test(englishId)) return false;
        
        // Implement Iranian national ID checksum validation
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

    static formatPhone(phone) {
        const englishPhone = PersianNumbers.toEnglish(phone);
        if (englishPhone.length === 11 && englishPhone.startsWith('09')) {
            const formatted = `${englishPhone.slice(0, 4)}-${englishPhone.slice(4, 7)}-${englishPhone.slice(7)}`;
            return PersianNumbers.toPersian(formatted);
        }
        return phone;
    }
}

class GoldCalculator {
    static karatPurities = {
        24: 1.0,
        22: 0.916,
        21: 0.875,
        18: 0.750,
        14: 0.583,
        10: 0.417
    };

    static persianUnits = {
        'مثقال': 4.608, // grams
        'سوت': 0.144   // grams
    };

    static calculatePureGold(weight, karat) {
        const purity = this.karatPurities[karat] || 1.0;
        return weight * purity;
    }

    static convertToPersianUnits(grams) {
        const mesghal = grams / this.persianUnits['مثقال'];
        const soot = grams / this.persianUnits['سوت'];
        
        return {
            grams: grams,
            mesghal: mesghal,
            soot: soot,
            formatted: {
                grams: `${PersianNumbers.toPersian(grams.toFixed(3))} گرم`,
                mesghal: `${PersianNumbers.toPersian(mesghal.toFixed(2))} مثقال`,
                soot: `${PersianNumbers.toPersian(soot.toFixed(1))} سوت`
            }
        };
    }

    static calculateValue(weight, karat, pricePerGram) {
        const pureGold = this.calculatePureGold(weight, karat);
        const value = pureGold * pricePerGram;
        return {
            pureGold: pureGold,
            value: value,
            formatted: PersianNumbers.formatCurrency(value)
        };
    }
}

class RTLUtils {
    static flipIcon(element) {
        element.style.transform = 'scaleX(-1)';
    }

    static setTextDirection(element, direction = 'rtl') {
        element.style.direction = direction;
        element.setAttribute('dir', direction);
    }

    static formatAddress(address) {
        // Format Persian address with proper RTL layout
        return address.trim();
    }

    static alignNumber(element) {
        // Align numbers properly in RTL context
        element.style.direction = 'ltr';
        element.style.textAlign = 'right';
    }
}

class PersianKeyboard {
    static persianMap = {
        'q': 'ض', 'w': 'ص', 'e': 'ث', 'r': 'ق', 't': 'ف', 'y': 'غ', 'u': 'ع', 'i': 'ه', 'o': 'خ', 'p': 'ح',
        'a': 'ش', 's': 'س', 'd': 'ی', 'f': 'ب', 'g': 'ل', 'h': 'ا', 'j': 'ت', 'k': 'ن', 'l': 'م', ';': 'ک',
        'z': 'ظ', 'x': 'ط', 'c': 'ز', 'v': 'ر', 'b': 'ذ', 'n': 'د', 'm': 'پ', ',': 'و', '.': '.',
        '1': '۱', '2': '۲', '3': '۳', '4': '۴', '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹', '0': '۰'
    };

    static enablePersianInput(element) {
        element.addEventListener('input', (e) => {
            const cursorPos = e.target.selectionStart;
            let value = e.target.value;
            let converted = '';
            
            for (let char of value) {
                converted += this.persianMap[char.toLowerCase()] || char;
            }
            
            if (converted !== value) {
                e.target.value = converted;
                e.target.setSelectionRange(cursorPos, cursorPos);
            }
        });
    }

    static initializeInputs() {
        const persianInputs = document.querySelectorAll('[data-persian-input]');
        persianInputs.forEach(input => {
            this.enablePersianInput(input);
        });
    }
}

// Form validation utilities
class PersianFormValidator {
    static validateForm(form) {
        const errors = [];
        const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
        
        inputs.forEach(input => {
            const value = input.value.trim();
            const label = input.getAttribute('data-label') || input.name;
            
            if (!value) {
                errors.push(`${label} الزامی است`);
                input.classList.add('error');
            } else {
                input.classList.remove('error');
                
                // Specific validations
                if (input.type === 'tel' && !PersianValidation.validatePhone(value)) {
                    errors.push(`شماره تلفن ${label} معتبر نیست`);
                    input.classList.add('error');
                }
                
                if (input.getAttribute('data-national-id') && !PersianValidation.validateNationalId(value)) {
                    errors.push(`کد ملی ${label} معتبر نیست`);
                    input.classList.add('error');
                }
            }
        });
        
        return {
            isValid: errors.length === 0,
            errors: errors
        };
    }

    static showErrors(errors, container) {
        if (!container) return;
        
        container.innerHTML = '';
        if (errors.length > 0) {
            const errorList = document.createElement('ul');
            errorList.className = 'error-list';
            
            errors.forEach(error => {
                const li = document.createElement('li');
                li.textContent = error;
                errorList.appendChild(li);
            });
            
            container.appendChild(errorList);
            container.style.display = 'block';
        } else {
            container.style.display = 'none';
        }
    }
}

// Initialize Persian utilities when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Persian keyboard inputs
    PersianKeyboard.initializeInputs();
    
    // Format all Persian dates
    const dateElements = document.querySelectorAll('[data-shamsi-date]');
    dateElements.forEach(element => {
        const date = element.getAttribute('data-shamsi-date');
        element.textContent = PersianCalendar.formatDate(date);
    });
    
    // Format all phone numbers
    const phoneElements = document.querySelectorAll('[data-phone]');
    phoneElements.forEach(element => {
        const phone = element.textContent;
        element.textContent = PersianValidation.formatPhone(phone);
    });
    
    // Set up form validation
    const forms = document.querySelectorAll('form[data-persian-validation]');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const validation = PersianFormValidator.validateForm(form);
            if (!validation.isValid) {
                e.preventDefault();
                const errorContainer = form.querySelector('.form-errors');
                PersianFormValidator.showErrors(validation.errors, errorContainer);
            }
        });
    });
    
    // Make utilities globally available
    window.PersianCalendar = PersianCalendar;
    window.PersianValidation = PersianValidation;
    window.GoldCalculator = GoldCalculator;
    window.RTLUtils = RTLUtils;
    window.PersianKeyboard = PersianKeyboard;
    window.PersianFormValidator = PersianFormValidator;
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        PersianCalendar,
        PersianValidation,
        GoldCalculator,
        RTLUtils,
        PersianKeyboard,
        PersianFormValidator
    };
}