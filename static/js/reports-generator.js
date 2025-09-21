/**
 * Reports Generator JavaScript Module
 * Handles report generation, progress monitoring, and UI interactions
 * Supports Persian RTL layout and dual theme system
 */

class ReportsGenerator {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializePersianNumbers();
        this.setupDatePickers();
        this.setupFormValidation();
    }

    setupEventListeners() {
        // Template selection
        document.addEventListener('change', (e) => {
            if (e.target.name === 'template_id') {
                this.handleTemplateSelection(e.target.value);
            }
        });

        // Quick date range buttons
        document.addEventListener('click', (e) => {
            if (e.target.dataset.dateRange) {
                this.setQuickDateRange(e.target.dataset.dateRange);
            }
        });

        // Gold price fetch button
        const goldPriceBtn = document.getElementById('fetchGoldPrice');
        if (goldPriceBtn) {
            goldPriceBtn.addEventListener('click', () => {
                this.fetchCurrentGoldPrice();
            });
        }

        // Form submission
        const reportForm = document.getElementById('reportGenerationForm');
        if (reportForm) {
            reportForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.generateReport();
            });
        }
    }

    initializePersianNumbers() {
        // Convert numbers to Persian digits
        const persianNumbers = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        const elements = document.querySelectorAll('.persian-numbers');
        
        elements.forEach(element => {
            let text = element.textContent || element.value;
            if (text) {
                text = text.replace(/[0-9]/g, (match) => persianNumbers[parseInt(match)]);
                if (element.tagName === 'INPUT') {
                    element.value = text;
                } else {
                    element.textContent = text;
                }
            }
        });
    }

    setupDatePickers() {
        // Initialize Persian date pickers using persian-date library
        if (typeof PersianDate !== 'undefined') {
            const dateInputs = document.querySelectorAll('input[type="text"][name*="shamsi"]');
            
            dateInputs.forEach(input => {
                this.initializePersianDatePicker(input);
            });
        }
    }

    initializePersianDatePicker(input) {
        // Create a simple Persian date picker
        input.addEventListener('focus', () => {
            // You can integrate with a Persian date picker library here
            // For now, we'll add placeholder functionality
            if (!input.value) {
                const today = new PersianDate();
                input.value = today.format('YYYY/MM/DD');
            }
        });

        // Validate Persian date format
        input.addEventListener('blur', () => {
            const value = input.value;
            if (value && !this.isValidPersianDate(value)) {
                this.showNotification('فرمت تاریخ صحیح نیست. لطفاً از فرمت YYYY/MM/DD استفاده کنید.', 'error');
                input.focus();
            }
        });
    }

    isValidPersianDate(dateString) {
        const regex = /^(\d{4})\/(\d{1,2})\/(\d{1,2})$/;
        const match = dateString.match(regex);
        
        if (!match) return false;
        
        const year = parseInt(match[1]);
        const month = parseInt(match[2]);
        const day = parseInt(match[3]);
        
        return year >= 1300 && year <= 1500 && 
               month >= 1 && month <= 12 && 
               day >= 1 && day <= 31;
    }

    setupFormValidation() {
        const form = document.getElementById('reportGenerationForm');
        if (!form) return;

        // Real-time validation
        form.addEventListener('input', (e) => {
            this.validateField(e.target);
        });

        // Form submission validation
        form.addEventListener('submit', (e) => {
            if (!this.validateForm()) {
                e.preventDefault();
            }
        });
    }

    validateField(field) {
        const value = field.value.trim();
        let isValid = true;
        let message = '';

        switch (field.name) {
            case 'template_id':
                isValid = value !== '';
                message = 'لطفاً نوع گزارش را انتخاب کنید';
                break;
            
            case 'date_from_shamsi':
            case 'date_to_shamsi':
                if (value) {
                    isValid = this.isValidPersianDate(value);
                    message = 'فرمت تاریخ صحیح نیست';
                }
                break;
            
            case 'gold_price_per_gram':
                if (value) {
                    isValid = !isNaN(value) && parseFloat(value) > 0;
                    message = 'قیمت طلا باید عددی مثبت باشد';
                }
                break;
        }

        this.updateFieldValidation(field, isValid, message);
        return isValid;
    }

    updateFieldValidation(field, isValid, message) {
        const container = field.closest('.form-group') || field.parentElement;
        const errorElement = container.querySelector('.error-message');
        
        // Remove existing error styling
        field.classList.remove('border-red-500', 'border-cyber-neon-danger');
        if (errorElement) {
            errorElement.remove();
        }

        if (!isValid && message) {
            // Add error styling
            if (document.body.classList.contains('dark')) {
                field.classList.add('border-cyber-neon-danger');
            } else {
                field.classList.add('border-red-500');
            }

            // Add error message
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message text-xs mt-1';
            errorDiv.textContent = message;
            
            if (document.body.classList.contains('dark')) {
                errorDiv.classList.add('text-cyber-neon-danger');
            } else {
                errorDiv.classList.add('text-red-600');
            }
            
            container.appendChild(errorDiv);
        }
    }

    validateForm() {
        const form = document.getElementById('reportGenerationForm');
        const fields = form.querySelectorAll('input, select, textarea');
        let isValid = true;

        fields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        // Check required fields
        const templateId = form.querySelector('input[name="template_id"]:checked');
        if (!templateId) {
            this.showNotification('لطفاً نوع گزارش را انتخاب کنید', 'error');
            isValid = false;
        }

        return isValid;
    }

    handleTemplateSelection(templateId) {
        if (!templateId) return;

        // Find template data
        const templates = window.reportTemplates || [];
        const template = templates.find(t => t.id == templateId);
        
        if (template) {
            this.updateTemplateInfo(template);
            this.showRelevantParameters(template.report_type);
        }
    }

    updateTemplateInfo(template) {
        const infoContainer = document.getElementById('templateInfo');
        if (!infoContainer) return;

        infoContainer.innerHTML = `
            <div class="space-y-3">
                <div>
                    <p class="text-sm font-medium text-gray-600 dark:text-cyber-text-secondary">نوع گزارش:</p>
                    <p class="text-sm text-gray-900 dark:text-cyber-text-primary">${template.report_type_display}</p>
                </div>
                <div>
                    <p class="text-sm font-medium text-gray-600 dark:text-cyber-text-secondary">فرمت پیش‌فرض:</p>
                    <p class="text-sm text-gray-900 dark:text-cyber-text-primary">${template.default_output_format_display}</p>
                </div>
                <div>
                    <p class="text-sm font-medium text-gray-600 dark:text-cyber-text-secondary">توضیحات:</p>
                    <p class="text-sm text-gray-900 dark:text-cyber-text-primary">${template.description || 'توضیحی موجود نیست'}</p>
                </div>
            </div>
        `;
    }

    showRelevantParameters(reportType) {
        // Hide all parameter sections
        const parameterSections = document.querySelectorAll('.parameter-section');
        parameterSections.forEach(section => {
            section.style.display = 'none';
        });

        // Show relevant parameters based on report type
        switch (reportType) {
            case 'inventory_valuation':
                const goldPriceSection = document.getElementById('goldPriceSection');
                if (goldPriceSection) {
                    goldPriceSection.style.display = 'block';
                }
                break;
            
            case 'customer_aging':
                const agingSection = document.getElementById('agingPeriodsSection');
                if (agingSection) {
                    agingSection.style.display = 'block';
                }
                break;
        }
    }

    setQuickDateRange(range) {
        const today = new Date();
        let fromDate, toDate;

        switch (range) {
            case 'this_month':
                fromDate = new Date(today.getFullYear(), today.getMonth(), 1);
                toDate = today;
                break;
            case 'last_month':
                fromDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                toDate = new Date(today.getFullYear(), today.getMonth(), 0);
                break;
            case 'this_quarter':
                const quarter = Math.floor(today.getMonth() / 3);
                fromDate = new Date(today.getFullYear(), quarter * 3, 1);
                toDate = today;
                break;
            case 'this_year':
                fromDate = new Date(today.getFullYear(), 0, 1);
                toDate = today;
                break;
        }

        // Convert to Persian dates if PersianDate is available
        if (typeof PersianDate !== 'undefined') {
            const pFromDate = new PersianDate(fromDate);
            const pToDate = new PersianDate(toDate);

            const fromInput = document.getElementById('dateFromShamsi');
            const toInput = document.getElementById('dateToShamsi');

            if (fromInput) fromInput.value = pFromDate.format('YYYY/MM/DD');
            if (toInput) toInput.value = pToDate.format('YYYY/MM/DD');
        }
    }

    async fetchCurrentGoldPrice() {
        const goldPriceInput = document.getElementById('goldPriceInput');
        const fetchButton = document.getElementById('fetchGoldPrice');
        
        if (!goldPriceInput || !fetchButton) return;

        try {
            // Show loading state
            fetchButton.disabled = true;
            fetchButton.innerHTML = `
                <svg class="animate-spin w-4 h-4 ml-2" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                در حال دریافت...
            `;

            const response = await fetch('/reports/ajax/gold-price/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();

            if (data.success) {
                goldPriceInput.value = data.price_per_gram;
                this.showNotification('قیمت طلا به‌روزرسانی شد', 'success');
            } else {
                throw new Error(data.error || 'خطا در دریافت قیمت طلا');
            }

        } catch (error) {
            console.error('Error fetching gold price:', error);
            this.showNotification('خطا در دریافت قیمت طلا: ' + error.message, 'error');
        } finally {
            // Reset button state
            fetchButton.disabled = false;
            fetchButton.innerHTML = 'قیمت فعلی';
        }
    }

    async generateReport() {
        if (!this.validateForm()) {
            return;
        }

        const form = document.getElementById('reportGenerationForm');
        const formData = new FormData(form);
        
        try {
            // Show progress modal
            this.showProgressModal();
            
            const response = await fetch(form.action || '/reports/generate/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();

            if (data.success) {
                // Start progress monitoring
                this.monitorReportProgress(data.report_id);
            } else {
                throw new Error(data.error || 'خطا در تولید گزارش');
            }

        } catch (error) {
            console.error('Error generating report:', error);
            this.hideProgressModal();
            this.showNotification('خطا در تولید گزارش: ' + error.message, 'error');
        }
    }

    showProgressModal() {
        const modal = document.getElementById('progressModal');
        if (modal) {
            modal.style.display = 'flex';
            this.updateProgress(0);
        }
    }

    hideProgressModal() {
        const modal = document.getElementById('progressModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    updateProgress(percentage) {
        const progressBar = document.querySelector('.progress-fill');
        const progressText = document.getElementById('progressText');
        
        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
        }
        
        if (progressText) {
            progressText.textContent = `${percentage}% تکمیل شده`;
        }
    }

    async monitorReportProgress(reportId) {
        const checkProgress = async () => {
            try {
                const response = await fetch(`/reports/ajax/status/${reportId}/`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                const data = await response.json();
                
                this.updateProgress(data.progress || 0);

                if (data.status === 'completed') {
                    this.updateProgress(100);
                    setTimeout(() => {
                        this.hideProgressModal();
                        if (data.download_url) {
                            window.location.href = data.download_url;
                        } else {
                            window.location.href = `/reports/detail/${reportId}/`;
                        }
                    }, 1000);
                } else if (data.status === 'failed') {
                    throw new Error(data.error_message || 'خطا در تولید گزارش');
                } else {
                    // Continue monitoring
                    setTimeout(checkProgress, 2000);
                }

            } catch (error) {
                console.error('Error checking progress:', error);
                this.hideProgressModal();
                this.showNotification('خطا در بررسی وضعیت گزارش: ' + error.message, 'error');
            }
        };

        checkProgress();
    }

    showNotification(message, type = 'info', duration = 5000) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-20 right-4 z-50 max-w-sm p-4 rounded-lg shadow-lg backdrop-blur-sm transition-all duration-300 animate-slide-in-right`;
        
        // Set theme-appropriate classes
        const isDark = document.body.classList.contains('dark');
        
        switch (type) {
            case 'success':
                notification.className += isDark 
                    ? ' bg-green-900/80 border border-green-500/50 text-green-200'
                    : ' bg-green-50 border border-green-200 text-green-800';
                break;
            case 'error':
                notification.className += isDark 
                    ? ' bg-red-900/80 border border-red-500/50 text-red-200'
                    : ' bg-red-50 border border-red-200 text-red-800';
                break;
            case 'warning':
                notification.className += isDark 
                    ? ' bg-yellow-900/80 border border-yellow-500/50 text-yellow-200'
                    : ' bg-yellow-50 border border-yellow-200 text-yellow-800';
                break;
            default:
                notification.className += isDark 
                    ? ' bg-cyber-bg-surface/80 border border-cyber-neon-primary/30 text-cyber-text-primary'
                    : ' bg-blue-50 border border-blue-200 text-blue-800';
        }

        notification.innerHTML = `
            <div class="flex items-center justify-between">
                <p class="text-sm font-medium">${message}</p>
                <button onclick="this.parentElement.parentElement.remove()" 
                        class="mr-2 text-current opacity-70 hover:opacity-100 transition-opacity">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        `;

        document.body.appendChild(notification);

        // Auto remove after duration
        setTimeout(() => {
            if (notification.parentElement) {
                notification.style.transform = 'translateX(100%)';
                notification.style.opacity = '0';
                setTimeout(() => {
                    notification.remove();
                }, 300);
            }
        }, duration);
    }

    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    // Utility methods for Persian number conversion
    toPersianNumbers(str) {
        const persianNumbers = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return str.replace(/[0-9]/g, (match) => persianNumbers[parseInt(match)]);
    }

    toEnglishNumbers(str) {
        const persianNumbers = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        const englishNumbers = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];
        
        persianNumbers.forEach((persian, index) => {
            str = str.replace(new RegExp(persian, 'g'), englishNumbers[index]);
        });
        
        return str;
    }

    // Format currency for display
    formatCurrency(amount, usePersianDigits = true) {
        if (typeof amount !== 'number') {
            amount = parseFloat(amount) || 0;
        }

        // Format with thousand separators
        let formatted = amount.toLocaleString('fa-IR');
        
        if (usePersianDigits) {
            formatted = this.toPersianNumbers(formatted);
        }
        
        return formatted + ' تومان';
    }

    // Format weight for display
    formatWeight(grams, unit = 'gram', usePersianDigits = true) {
        let value = parseFloat(grams) || 0;
        let unitText = 'گرم';
        
        if (unit === 'mesghal') {
            value = value / 4.608; // Convert grams to mesghal
            unitText = 'مثقال';
        }
        
        let formatted = value.toFixed(3);
        
        if (usePersianDigits) {
            formatted = this.toPersianNumbers(formatted);
        }
        
        return formatted + ' ' + unitText;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.reportsGenerator = new ReportsGenerator();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ReportsGenerator;
}