/**
 * Layaway Plan Detail JavaScript
 * Handles plan detail interactions, payments, and status changes
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeLayawayDetail();
});

function initializeLayawayDetail() {
    // Initialize progress circle animation
    initializeProgressCircle();
    
    // Initialize modal handlers
    initializeModals();
    
    // Initialize payment form
    initializePaymentForm();
    
    // Initialize refund calculation
    initializeRefundCalculation();
    
    // Initialize theme-aware components
    initializeThemeComponents();
    
    // Initialize auto-refresh for status updates
    initializeAutoRefresh();
}

function initializeProgressCircle() {
    const circle = document.querySelector('.progress-circle');
    if (!circle) return;
    
    const percentage = parseFloat(circle.dataset.percentage) || 0;
    
    // Animate the progress circle
    let currentPercentage = 0;
    const increment = percentage / 50; // 50 steps
    
    const timer = setInterval(() => {
        currentPercentage += increment;
        if (currentPercentage >= percentage) {
            currentPercentage = percentage;
            clearInterval(timer);
        }
        
        const degrees = (currentPercentage / 100) * 360;
        circle.style.background = `conic-gradient(#28a745 ${degrees}deg, #e9ecef 0deg)`;
        
        // Update text
        const progressText = circle.querySelector('.progress-text');
        if (progressText) {
            progressText.textContent = `${Math.round(currentPercentage)}%`;
        }
    }, 20);
}

function initializeModals() {
    // Payment modal
    const paymentModal = document.getElementById('paymentModal');
    if (paymentModal) {
        paymentModal.addEventListener('show.bs.modal', function() {
            // Focus on amount field when modal opens
            setTimeout(() => {
                const amountField = paymentModal.querySelector('[name="amount"]');
                if (amountField) {
                    amountField.focus();
                }
            }, 300);
        });
    }
    
    // Cancel modal
    const cancelModal = document.getElementById('cancelModal');
    if (cancelModal) {
        cancelModal.addEventListener('show.bs.modal', function() {
            // Reset form when modal opens
            const form = cancelModal.querySelector('form');
            if (form) {
                form.reset();
                // Set default refund percentage
                const refundField = form.querySelector('[name="refund_percentage"]');
                if (refundField) {
                    refundField.value = '90';
                    updateRefundAmount();
                }
            }
        });
    }
}

function initializePaymentForm() {
    const paymentForm = document.querySelector('#paymentModal form');
    if (!paymentForm) return;
    
    // Real-time validation
    const amountField = paymentForm.querySelector('[name="amount"]');
    if (amountField) {
        amountField.addEventListener('input', function() {
            validatePaymentAmount(this);
        });
        
        amountField.addEventListener('blur', function() {
            validatePaymentAmount(this);
        });
    }
    
    // Form submission
    paymentForm.addEventListener('submit', function(e) {
        if (!validatePaymentForm()) {
            e.preventDefault();
            showNotification('لطفاً اطلاعات پرداخت را صحیح وارد کنید', 'error');
        }
    });
}

function validatePaymentAmount(field) {
    const amount = parseFloat(field.value) || 0;
    let isValid = true;
    let errorMessage = '';
    
    if (amount <= 0) {
        isValid = false;
        errorMessage = 'مبلغ پرداخت باید بیشتر از صفر باشد';
    } else if (amount > 1000000000) { // 1 billion Toman limit
        isValid = false;
        errorMessage = 'مبلغ پرداخت بیش از حد مجاز است';
    }
    
    if (!isValid) {
        showFieldError(field, errorMessage);
    } else {
        clearFieldError(field);
    }
    
    return isValid;
}

function validatePaymentForm() {
    const form = document.querySelector('#paymentModal form');
    const amountField = form.querySelector('[name="amount"]');
    const methodField = form.querySelector('[name="payment_method"]');
    
    let isValid = true;
    
    if (!validatePaymentAmount(amountField)) {
        isValid = false;
    }
    
    if (!methodField.value) {
        showFieldError(methodField, 'لطفاً روش پرداخت را انتخاب کنید');
        isValid = false;
    } else {
        clearFieldError(methodField);
    }
    
    return isValid;
}

function initializeRefundCalculation() {
    const refundInput = document.querySelector('[name="refund_percentage"]');
    if (!refundInput) return;
    
    refundInput.addEventListener('input', updateRefundAmount);
    
    // Initial calculation
    updateRefundAmount();
}

function updateRefundAmount() {
    const refundInput = document.querySelector('[name="refund_percentage"]');
    const refundAmountSpan = document.getElementById('refundAmount');
    
    if (!refundInput || !refundAmountSpan) return;
    
    const percentage = parseFloat(refundInput.value) || 0;
    const totalPaidElement = document.querySelector('[data-total-paid]');
    const totalPaid = parseFloat(totalPaidElement?.dataset.totalPaid) || 0;
    
    const refundAmount = (totalPaid * percentage) / 100;
    refundAmountSpan.textContent = formatPersianNumber(Math.round(refundAmount));
}

function initializeAutoRefresh() {
    // Auto-refresh plan status every 2 minutes
    setInterval(function() {
        refreshPlanStatus();
    }, 2 * 60 * 1000); // 2 minutes
}

async function refreshPlanStatus() {
    try {
        const response = await fetch(window.location.href, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (response.ok) {
            const html = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            
            // Update status banner
            const newStatusBanner = doc.querySelector('.status-banner');
            const currentStatusBanner = document.querySelector('.status-banner');
            if (newStatusBanner && currentStatusBanner) {
                currentStatusBanner.innerHTML = newStatusBanner.innerHTML;
                currentStatusBanner.className = newStatusBanner.className;
            }
            
            // Update financial summary
            const newFinancialSummary = doc.querySelector('.financial-summary');
            const currentFinancialSummary = document.querySelector('.financial-summary');
            if (newFinancialSummary && currentFinancialSummary) {
                currentFinancialSummary.innerHTML = newFinancialSummary.innerHTML;
            }
            
            // Update payment schedule table
            const newScheduleTable = doc.querySelector('.card:has(.table) .table-responsive');
            const currentScheduleTable = document.querySelector('.card:has(.table) .table-responsive');
            if (newScheduleTable && currentScheduleTable) {
                currentScheduleTable.innerHTML = newScheduleTable.innerHTML;
            }
            
            // Re-initialize progress circle
            initializeProgressCircle();
            
            console.log('Plan status refreshed');
        }
    } catch (error) {
        console.error('Error refreshing plan status:', error);
    }
}

async function processQuickPayment(amount) {
    const form = document.querySelector('#paymentModal form');
    if (!form) return;
    
    // Fill form with quick payment amount
    const amountField = form.querySelector('[name="amount"]');
    const methodField = form.querySelector('[name="payment_method"]');
    
    if (amountField) {
        amountField.value = amount;
        validatePaymentAmount(amountField);
    }
    
    if (methodField) {
        methodField.value = 'cash'; // Default to cash
    }
    
    // Show modal
    const modal = document.getElementById('paymentModal');
    if (modal && typeof $ !== 'undefined') {
        $(modal).modal('show');
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
                    updateProgressCircleForDarkMode();
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
    // Add neon glow effects to status banner
    const statusBanner = document.querySelector('.status-banner');
    if (statusBanner) {
        statusBanner.addEventListener('mouseenter', function() {
            this.style.animation = 'statusPulse 2s ease-in-out infinite';
        });
        
        statusBanner.addEventListener('mouseleave', function() {
            this.style.animation = '';
        });
    }
    
    // Add glassmorphism effects to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        if (!card.classList.contains('glass-effect')) {
            card.classList.add('glass-effect');
        }
    });
}

function updateProgressCircleForDarkMode() {
    const circle = document.querySelector('.progress-circle');
    if (!circle) return;
    
    const percentage = parseFloat(circle.dataset.percentage) || 0;
    const degrees = (percentage / 100) * 360;
    
    // Update colors for dark mode
    circle.style.background = `conic-gradient(#00FF88 ${degrees}deg, rgba(255,255,255,0.1) 0deg)`;
    
    // Update inner circle background
    const beforeElement = circle.querySelector('::before');
    if (beforeElement) {
        beforeElement.style.background = '#1A1D29';
    }
}

// Utility functions
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

function formatPersianNumber(number) {
    if (typeof number !== 'number') {
        number = parseFloat(number) || 0;
    }
    
    // Format with thousand separators and convert to Persian numerals
    const formatted = new Intl.NumberFormat('fa-IR').format(number);
    return formatted;
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

// Export functions for use in other scripts
window.LayawayDetail = {
    processQuickPayment,
    refreshPlanStatus,
    formatPersianNumber,
    showNotification,
    updateRefundAmount
};

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    @keyframes statusPulse {
        0%, 100% { box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6); }
        50% { box-shadow: 0 15px 50px rgba(0, 212, 255, 0.15); }
    }
    
    .notification-toast {
        animation: slideInRight 0.3s ease-out;
    }
    
    .glass-effect {
        backdrop-filter: blur(16px) saturate(150%);
    }
    
    .progress-circle {
        transition: background 0.5s ease;
    }
    
    .modal.fade .modal-dialog {
        transition: transform 0.3s ease-out;
    }
    
    .modal.show .modal-dialog {
        transform: none;
    }
`;
document.head.appendChild(style);