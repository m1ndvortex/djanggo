/**
 * Layaway Plan Creation JavaScript
 * Handles form interactions, calculations, and validations
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeLayawayCreate();
});

function initializeLayawayCreate() {
    // Initialize Select2 for dropdowns
    initializeSelect2();
    
    // Initialize form validation
    initializeFormValidation();
    
    // Initialize calculation handlers
    initializeCalculations();
    
    // Initialize quick term buttons
    initializeQuickTerms();
    
    // Initialize theme-aware components
    initializeThemeComponents();
    
    // Set default start date to today
    setDefaultStartDate();
}

function initializeSelect2() {
    // Initialize Select2 for customer and jewelry item dropdowns
    if (typeof $ !== 'undefined' && $.fn.select2) {
        $('.select2').select2({
            theme: 'bootstrap4',
            width: '100%',
            placeholder: function() {
                return $(this).data('placeholder') || 'انتخاب کنید...';
            },
            allowClear: true,
            language: {
                noResults: function() {
                    return 'نتیجه‌ای یافت نشد';
                },
                searching: function() {
                    return 'در حال جستجو...';
                }
            }
        });
    }
}

function initializeFormValidation() {
    const form = document.querySelector('.layaway-form');
    if (!form) return;
    
    // Real-time validation
    const requiredFields = form.querySelectorAll('[required]');
    requiredFields.forEach(field => {
        field.addEventListener('blur', function() {
            validateField(this);
        });
        
        field.addEventListener('input', function() {
            clearFieldError(this);
        });
    });
    
    // Form submission validation
    form.addEventListener('submit', function(e) {
        if (!validateForm()) {
            e.preventDefault();
            showNotification('لطفاً خطاهای فرم را برطرف کنید', 'error');
        }
    });
}

function validateField(field) {
    const value = field.value.trim();
    let isValid = true;
    let errorMessage = '';
    
    // Required field validation
    if (field.hasAttribute('required') && !value) {
        isValid = false;
        errorMessage = 'این فیلد الزامی است';
    }
    
    // Specific field validations
    switch (field.name) {
        case 'total_amount':
            if (value && parseFloat(value) <= 0) {
                isValid = false;
                errorMessage = 'مبلغ کل باید بیشتر از صفر باشد';
            }
            break;
            
        case 'down_payment':
            const totalAmount = parseFloat(document.querySelector('[name="total_amount"]').value) || 0;
            if (value && parseFloat(value) >= totalAmount) {
                isValid = false;
                errorMessage = 'پیش پرداخت نمی‌تواند بیشتر از مبلغ کل باشد';
            }
            break;
            
        case 'number_of_payments':
            if (value && (parseInt(value) < 1 || parseInt(value) > 120)) {
                isValid = false;
                errorMessage = 'تعداد اقساط باید بین ۱ تا ۱۲۰ باشد';
            }
            break;
    }
    
    if (!isValid) {
        showFieldError(field, errorMessage);
    } else {
        clearFieldError(field);
    }
    
    return isValid;
}

function showFieldError(field, message) {
    field.classList.add('is-invalid');
    
    // Remove existing error message
    const existingError = field.parentElement.querySelector('.invalid-feedback');
    if (existingError) {
        existingError.remove();
    }
    
    // Add new error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback d-block';
    errorDiv.textContent = message;
    field.parentElement.appendChild(errorDiv);
}

function clearFieldError(field) {
    field.classList.remove('is-invalid');
    const errorDiv = field.parentElement.querySelector('.invalid-feedback');
    if (errorDiv) {
        errorDiv.remove();
    }
}

function validateForm() {
    const form = document.querySelector('.layaway-form');
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!validateField(field)) {
            isValid = false;
        }
    });
    
    return isValid;
}

function initializeCalculations() {
    // Bind calculation events
    const calculationFields = [
        'total_amount',
        'down_payment', 
        'number_of_payments',
        'payment_frequency'
    ];
    
    calculationFields.forEach(fieldName => {
        const field = document.querySelector(`[name="${fieldName}"]`);
        if (field) {
            field.addEventListener('input', debounce(calculateInstallments, 500));
            field.addEventListener('change', calculateInstallments);
        }
    });
    
    // Initial calculation
    setTimeout(calculateInstallments, 100);
}

async function calculateInstallments() {
    const totalAmount = parseFloat(document.querySelector('[name="total_amount"]').value) || 0;
    const downPayment = parseFloat(document.querySelector('[name="down_payment"]').value) || 0;
    const numberOfPayments = parseInt(document.querySelector('[name="number_of_payments"]').value) || 1;
    const paymentFrequency = document.querySelector('[name="payment_frequency"]').value || 'monthly';
    
    if (totalAmount <= 0 || numberOfPayments <= 0) {
        hideCalculationResults();
        return;
    }
    
    try {
        const response = await fetch('/customers/layaway/ajax/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCsrfToken()
            },
            body: new URLSearchParams({
                action: 'calculate_installments',
                total_amount: totalAmount,
                down_payment: downPayment,
                number_of_payments: numberOfPayments,
                payment_frequency: paymentFrequency
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showCalculationResults(data.calculation);
            updateDownPaymentPercentage();
        } else {
            console.error('Calculation error:', data.error);
            hideCalculationResults();
        }
    } catch (error) {
        console.error('Error calculating installments:', error);
        hideCalculationResults();
    }
}

function showCalculationResults(calculation) {
    const resultsDiv = document.querySelector('.calculation-results');
    if (!resultsDiv) return;
    
    // Update calculation values
    const remainingAmount = resultsDiv.querySelector('[data-field="remaining_amount"]');
    const installmentAmount = resultsDiv.querySelector('[data-field="installment_amount"]');
    const completionDate = resultsDiv.querySelector('[data-field="completion_date"]');
    const totalPayments = resultsDiv.querySelector('[data-field="total_payments"]');
    
    if (remainingAmount) remainingAmount.textContent = formatPersianNumber(calculation.remaining_amount);
    if (installmentAmount) installmentAmount.textContent = formatPersianNumber(calculation.installment_amount);
    if (completionDate) completionDate.textContent = formatPersianDate(calculation.completion_date);
    if (totalPayments) totalPayments.textContent = formatPersianNumber(calculation.total_payments);
    
    // Show results with animation
    resultsDiv.style.display = 'block';
    resultsDiv.classList.add('fade-in');
}

function hideCalculationResults() {
    const resultsDiv = document.querySelector('.calculation-results');
    if (resultsDiv) {
        resultsDiv.style.display = 'none';
        resultsDiv.classList.remove('fade-in');
    }
}

function updateDownPaymentPercentage() {
    const totalAmount = parseFloat(document.querySelector('[name="total_amount"]').value) || 0;
    const downPayment = parseFloat(document.querySelector('[name="down_payment"]').value) || 0;
    
    const percentageSpan = document.querySelector('[data-field="down_payment_percentage"]');
    if (percentageSpan && totalAmount > 0) {
        const percentage = Math.round((downPayment / totalAmount) * 100);
        percentageSpan.textContent = formatPersianNumber(percentage);
    }
}

function initializeQuickTerms() {
    const quickTermButtons = document.querySelectorAll('[data-quick-term]');
    
    quickTermButtons.forEach(button => {
        button.addEventListener('click', function() {
            const termType = this.dataset.quickTerm;
            setQuickTerms(termType);
        });
    });
}

function setQuickTerms(type) {
    const frequencyField = document.querySelector('[name="payment_frequency"]');
    const paymentsField = document.querySelector('[name="number_of_payments"]');
    
    switch (type) {
        case '3_months':
            frequencyField.value = 'monthly';
            paymentsField.value = '3';
            break;
        case '6_months':
            frequencyField.value = 'monthly';
            paymentsField.value = '6';
            break;
        case '12_months':
            frequencyField.value = 'monthly';
            paymentsField.value = '12';
            break;
        case 'weekly_6_months':
            frequencyField.value = 'weekly';
            paymentsField.value = '24';
            break;
    }
    
    // Trigger change events
    frequencyField.dispatchEvent(new Event('change'));
    paymentsField.dispatchEvent(new Event('input'));
    
    // Visual feedback
    const buttons = document.querySelectorAll('[data-quick-term]');
    buttons.forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-quick-term="${type}"]`).classList.add('active');
    
    setTimeout(() => {
        document.querySelector(`[data-quick-term="${type}"]`).classList.remove('active');
    }, 1000);
}

async function loadCustomerHistory(customerId) {
    if (!customerId) return;
    
    try {
        const response = await fetch('/customers/layaway/ajax/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCsrfToken()
            },
            body: new URLSearchParams({
                action: 'get_customer_history',
                customer_id: customerId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showCustomerHistory(data.history);
        }
    } catch (error) {
        console.error('Error loading customer history:', error);
    }
}

function showCustomerHistory(history) {
    const historyDiv = document.querySelector('.customer-history');
    if (!historyDiv) return;
    
    const statsDiv = historyDiv.querySelector('.history-stats');
    if (statsDiv) {
        statsDiv.innerHTML = `
            <small class="text-info">
                ${formatPersianNumber(history.total_plans)} قرارداد قبلی
            </small>
            <small class="text-success">
                ${formatPersianNumber(history.current_balance)} تومان مانده فعلی
            </small>
            <small class="text-warning">
                ${formatPersianNumber(history.completed_plans)} تکمیل شده
            </small>
        `;
    }
    
    historyDiv.style.display = 'block';
}

async function loadItemDetails(itemId) {
    if (!itemId) return;
    
    try {
        const response = await fetch('/customers/layaway/ajax/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCsrfToken()
            },
            body: new URLSearchParams({
                action: 'get_jewelry_item_details',
                item_id: itemId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showItemDetails(data.item);
            
            // Auto-fill total amount if available
            if (data.item.selling_price > 0) {
                document.querySelector('[name="total_amount"]').value = data.item.selling_price;
                calculateInstallments();
            }
        }
    } catch (error) {
        console.error('Error loading item details:', error);
    }
}

function showItemDetails(item) {
    const detailsDiv = document.querySelector('.item-details');
    if (!detailsDiv) return;
    
    const gridDiv = detailsDiv.querySelector('.details-grid');
    if (gridDiv) {
        gridDiv.innerHTML = `
            <small class="text-info">
                وزن: ${formatPersianNumber(item.weight_grams)} گرم
            </small>
            <small class="text-info">
                عیار: ${formatPersianNumber(item.karat)}
            </small>
            <small class="text-success">
                قیمت پیشنهادی: ${formatPersianNumber(item.selling_price)} تومان
            </small>
            <small class="text-muted">
                وضعیت: ${item.status}
            </small>
        `;
    }
    
    detailsDiv.style.display = 'block';
}

function setDefaultStartDate() {
    const startDateField = document.querySelector('[name="start_date"]');
    if (startDateField && !startDateField.value) {
        const today = new Date();
        const formattedDate = today.toISOString().split('T')[0];
        startDateField.value = formattedDate;
    }
}

function initializeThemeComponents() {
    // Handle theme-specific animations and effects
    const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
    
    if (isDarkMode) {
        initializeDarkModeEffects();
    }
    
    // Listen for theme changes
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
                const newTheme = document.documentElement.getAttribute('data-theme');
                if (newTheme === 'dark') {
                    initializeDarkModeEffects();
                }
            }
        });
    });
    
    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme']
    });
}

function initializeDarkModeEffects() {
    // Add neon glow effects to form controls on focus
    const formControls = document.querySelectorAll('.form-control');
    formControls.forEach(control => {
        control.addEventListener('focus', function() {
            this.style.animation = 'neonGlow 0.3s ease-out';
        });
        
        control.addEventListener('blur', function() {
            this.style.animation = '';
        });
    });
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

function formatPersianNumber(number) {
    if (typeof number !== 'number') {
        number = parseFloat(number) || 0;
    }
    
    // Format with thousand separators and convert to Persian numerals
    const formatted = new Intl.NumberFormat('fa-IR').format(number);
    return formatted;
}

function formatPersianDate(dateString) {
    // Convert ISO date to Persian format
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('fa-IR').format(date);
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} notification-toast`;
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} ml-2"></i>
            <span>${message}</span>
            <button type="button" class="close mr-2" onclick="this.parentElement.parentElement.remove()">
                <span>&times;</span>
            </button>
        </div>
    `;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        left: 20px;
        z-index: 9999;
        min-width: 300px;
        border-radius: 8px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        animation: slideInRight 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => notification.remove(), 300);
        }
    }, 5000);
}

// Export functions for use in Alpine.js or other scripts
window.LayawayCreate = {
    calculateInstallments,
    loadCustomerHistory,
    loadItemDetails,
    setQuickTerms,
    formatPersianNumber,
    showNotification
};

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    .fade-in {
        animation: fadeIn 0.3s ease-out;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .notification-toast {
        animation: slideInRight 0.3s ease-out;
    }
    
    [data-quick-term].active {
        transform: scale(0.95);
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.2);
    }
`;
document.head.appendChild(style);