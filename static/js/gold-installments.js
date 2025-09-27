/**
 * Gold Installments JavaScript functionality
 * Supports installment management and notification system UI
 */

// Persian number formatter utility
const PersianFormatter = {
    toPersianDigits: function(str) {
        const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
        const englishDigits = '0123456789';
        
        return str.toString().replace(/[0-9]/g, function(match) {
            return persianDigits[englishDigits.indexOf(match)];
        });
    },
    
    formatCurrency: function(amount, usePersianDigits = true) {
        const formatted = new Intl.NumberFormat('fa-IR').format(amount);
        return usePersianDigits ? this.toPersianDigits(formatted) + ' تومان' : formatted + ' تومان';
    },
    
    formatWeight: function(weight, unit = 'gram', usePersianDigits = true) {
        const formatted = parseFloat(weight).toFixed(3);
        const result = usePersianDigits ? this.toPersianDigits(formatted) : formatted;
        return result + (unit === 'gram' ? ' گرم' : ' ' + unit);
    },
    
    formatPercentage: function(percentage, usePersianDigits = true) {
        const formatted = parseFloat(percentage).toFixed(2);
        const result = usePersianDigits ? this.toPersianDigits(formatted) : formatted;
        return result + '٪';
    }
};

// Gold price calculator
const GoldCalculator = {
    calculateGoldWeight: function(paymentAmount, goldPricePerGram) {
        if (paymentAmount <= 0 || goldPricePerGram <= 0) {
            return 0;
        }
        return paymentAmount / goldPricePerGram;
    },
    
    calculatePaymentAmount: function(goldWeight, goldPricePerGram) {
        if (goldWeight <= 0 || goldPricePerGram <= 0) {
            return 0;
        }
        return goldWeight * goldPricePerGram;
    },
    
    applyDiscount: function(amount, discountPercentage) {
        if (discountPercentage <= 0) {
            return amount;
        }
        return amount * (1 - discountPercentage / 100);
    }
};

// Notification management
const NotificationManager = {
    templates: {
        payment_reminder: 'عزیز {customer_name}، پرداخت شما برای قرارداد {contract_number} در تاریخ {date} سررسید می‌شود.',
        overdue_notice: 'عزیز {customer_name}، پرداخت شما برای قرارداد {contract_number} معوقه شده است. لطفاً با ما تماس بگیرید.',
        payment_confirmation: 'عزیز {customer_name}، پرداخت شما به مبلغ {amount} با موفقیت دریافت شد.',
        contract_completion: 'تبریک {customer_name}، قرارداد طلای قرضی شما با شماره {contract_number} تکمیل شد!'
    },
    
    formatMessage: function(template, data) {
        let message = this.templates[template] || template;
        
        // Replace placeholders with actual data
        Object.keys(data).forEach(key => {
            const placeholder = '{' + key + '}';
            message = message.replace(new RegExp(placeholder, 'g'), data[key]);
        });
        
        return message;
    },
    
    validatePhoneNumber: function(phoneNumber) {
        // Iranian mobile number validation
        const iranMobileRegex = /^(\+98|0)?9\d{9}$/;
        return iranMobileRegex.test(phoneNumber);
    }
};

// Contract management utilities
const ContractManager = {
    calculateProgress: function(initialWeight, remainingWeight) {
        if (initialWeight <= 0) return 0;
        const paidWeight = initialWeight - remainingWeight;
        return (paidWeight / initialWeight) * 100;
    },
    
    isOverdue: function(lastPaymentDate, paymentSchedule) {
        if (!lastPaymentDate) return true;
        
        const today = new Date();
        const lastPayment = new Date(lastPaymentDate);
        const daysDiff = Math.floor((today - lastPayment) / (1000 * 60 * 60 * 24));
        
        // Determine overdue threshold based on payment schedule
        let threshold = 30; // Default monthly
        switch (paymentSchedule) {
            case 'weekly':
                threshold = 10;
                break;
            case 'bi_weekly':
                threshold = 17;
                break;
            case 'monthly':
                threshold = 35;
                break;
        }
        
        return daysDiff > threshold;
    },
    
    getStatusColor: function(status, isOverdue = false) {
        if (isOverdue) return 'danger';
        
        switch (status) {
            case 'active': return 'success';
            case 'completed': return 'primary';
            case 'suspended': return 'warning';
            case 'defaulted': return 'danger';
            default: return 'secondary';
        }
    }
};

// UI utilities
const UIUtils = {
    showToast: function(message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0 position-fixed top-0 end-0 m-3`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove toast after it's hidden
        toast.addEventListener('hidden.bs.toast', () => {
            document.body.removeChild(toast);
        });
    },
    
    confirmAction: function(message, callback) {
        if (confirm(message)) {
            callback();
        }
    },
    
    formatDatePersian: function(date) {
        // Simple Persian date formatting (would use proper library in production)
        const options = { 
            year: 'numeric', 
            month: '2-digit', 
            day: '2-digit',
            calendar: 'persian',
            numberingSystem: 'persian'
        };
        
        try {
            return new Intl.DateTimeFormat('fa-IR', options).format(new Date(date));
        } catch (e) {
            // Fallback to simple formatting
            const d = new Date(date);
            return `${d.getFullYear()}/${(d.getMonth() + 1).toString().padStart(2, '0')}/${d.getDate().toString().padStart(2, '0')}`;
        }
    }
};

// AJAX utilities
const AjaxUtils = {
    getCsrfToken: function() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    },
    
    post: function(url, data, successCallback, errorCallback) {
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken(),
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                successCallback(data);
            } else {
                errorCallback(data.error || 'Unknown error');
            }
        })
        .catch(error => {
            errorCallback(error.message);
        });
    },
    
    get: function(url, successCallback, errorCallback) {
        fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success !== false) {
                successCallback(data);
            } else {
                errorCallback(data.error || 'Unknown error');
            }
        })
        .catch(error => {
            errorCallback(error.message);
        });
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Persian number inputs
    document.querySelectorAll('.persian-number-input').forEach(input => {
        input.addEventListener('input', function() {
            // Convert English digits to Persian on display
            const value = this.value;
            const persianValue = PersianFormatter.toPersianDigits(value);
            
            // Update display without affecting the actual value
            if (this.dataset.displayElement) {
                const displayElement = document.getElementById(this.dataset.displayElement);
                if (displayElement) {
                    displayElement.textContent = persianValue;
                }
            }
        });
    });
    
    // Initialize currency inputs
    document.querySelectorAll('.persian-currency-input').forEach(input => {
        input.addEventListener('blur', function() {
            const value = parseFloat(this.value) || 0;
            if (value > 0) {
                this.title = PersianFormatter.formatCurrency(value);
            }
        });
    });
    
    // Initialize gold weight calculators
    document.querySelectorAll('[data-calculator="gold-weight"]').forEach(input => {
        input.addEventListener('input', function() {
            const amount = parseFloat(this.value) || 0;
            const goldPrice = parseFloat(this.dataset.goldPrice) || 3500000;
            
            if (amount > 0) {
                const goldWeight = GoldCalculator.calculateGoldWeight(amount, goldPrice);
                const displayElement = document.querySelector(this.dataset.target);
                
                if (displayElement) {
                    displayElement.textContent = PersianFormatter.formatWeight(goldWeight);
                }
            }
        });
    });
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// Export for global access
window.PersianFormatter = PersianFormatter;
window.GoldCalculator = GoldCalculator;
window.NotificationManager = NotificationManager;
window.ContractManager = ContractManager;
window.UIUtils = UIUtils;
window.AjaxUtils = AjaxUtils;