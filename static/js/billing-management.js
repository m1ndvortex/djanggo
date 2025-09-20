/**
 * Billing Management JavaScript
 * Handles billing and subscription management functionality
 */

class BillingManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeCharts();
        this.setupFormValidation();
        this.initializePersianNumbers();
    }

    setupEventListeners() {
        // Payment processing
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action="process-payment"]')) {
                this.handlePaymentProcessing(e.target);
            }
        });

        // Invoice actions
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action="cancel-invoice"]')) {
                this.handleInvoiceCancellation(e.target);
            }
        });

        // Bulk operations
        document.addEventListener('change', (e) => {
            if (e.target.matches('.bulk-select-all')) {
                this.handleBulkSelectAll(e.target);
            }
        });

        // Form submissions
        document.addEventListener('submit', (e) => {
            if (e.target.matches('.billing-form')) {
                this.handleFormSubmission(e);
            }
        });

        // Real-time calculations
        document.addEventListener('input', (e) => {
            if (e.target.matches('[data-calculate]')) {
                this.handleRealTimeCalculation(e.target);
            }
        });
    }

    handlePaymentProcessing(element) {
        const invoiceId = element.dataset.invoiceId;
        const invoiceNumber = element.dataset.invoiceNumber;
        
        this.showPaymentModal(invoiceId, invoiceNumber);
    }

    showPaymentModal(invoiceId, invoiceNumber) {
        const modal = document.getElementById('paymentModal');
        if (!modal) return;

        // Set invoice information
        const form = modal.querySelector('#paymentForm');
        form.dataset.invoiceId = invoiceId;

        // Set today's date as default
        const today = new Date().toISOString().split('T')[0];
        const dateInput = form.querySelector('input[name="payment_date"]');
        if (dateInput) {
            dateInput.value = today;
        }

        // Show modal
        modal.classList.remove('hidden');
        
        // Focus on first input
        const firstInput = form.querySelector('select, input');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }

    closePaymentModal() {
        const modal = document.getElementById('paymentModal');
        if (modal) {
            modal.classList.add('hidden');
            const form = modal.querySelector('#paymentForm');
            if (form) {
                form.reset();
                delete form.dataset.invoiceId;
            }
        }
    }

    async processPayment(formData, invoiceId) {
        try {
            const response = await fetch(`/admin/tenants/billing/invoices/${invoiceId}/payment/`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showMessage(data.message, 'success');
                this.closePaymentModal();
                
                // Update UI
                setTimeout(() => {
                    this.updateInvoiceStatus(invoiceId, 'paid');
                    // Optionally reload page
                    if (data.reload) {
                        location.reload();
                    }
                }, 1000);
            } else {
                this.showMessage(data.message, 'error');
            }
        } catch (error) {
            console.error('Payment processing error:', error);
            this.showMessage('خطا در پردازش پرداخت', 'error');
        }
    }

    handleInvoiceCancellation(element) {
        const invoiceId = element.dataset.invoiceId;
        const invoiceNumber = element.dataset.invoiceNumber;

        if (confirm(`آیا از لغو فاکتور ${invoiceNumber} اطمینان دارید؟ این عمل قابل بازگشت نیست.`)) {
            this.cancelInvoice(invoiceId);
        }
    }

    async cancelInvoice(invoiceId) {
        try {
            const response = await fetch(`/admin/tenants/billing/invoices/${invoiceId}/cancel/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showMessage(data.message, 'success');
                this.updateInvoiceStatus(invoiceId, 'cancelled');
            } else {
                this.showMessage(data.message, 'error');
            }
        } catch (error) {
            console.error('Invoice cancellation error:', error);
            this.showMessage('خطا در لغو فاکتور', 'error');
        }
    }

    handleBulkSelectAll(checkbox) {
        const checkboxes = document.querySelectorAll('.bulk-select-item');
        checkboxes.forEach(cb => {
            cb.checked = checkbox.checked;
        });
        
        this.updateBulkActionButtons();
    }

    updateBulkActionButtons() {
        const selectedItems = document.querySelectorAll('.bulk-select-item:checked');
        const bulkActions = document.querySelector('.bulk-actions');
        
        if (bulkActions) {
            if (selectedItems.length > 0) {
                bulkActions.classList.remove('hidden');
                const countSpan = bulkActions.querySelector('.selected-count');
                if (countSpan) {
                    countSpan.textContent = this.formatPersianNumber(selectedItems.length);
                }
            } else {
                bulkActions.classList.add('hidden');
            }
        }
    }

    handleFormSubmission(e) {
        const form = e.target;
        
        // Validate form
        if (!this.validateForm(form)) {
            e.preventDefault();
            return;
        }

        // Show loading state
        this.showFormLoading(form);
    }

    validateForm(form) {
        let isValid = true;
        const errors = [];

        // Required field validation
        const requiredFields = form.querySelectorAll('[required]');
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                this.showFieldError(field, 'این فیلد الزامی است');
                isValid = false;
            } else {
                this.clearFieldError(field);
            }
        });

        // Email validation
        const emailFields = form.querySelectorAll('input[type="email"]');
        emailFields.forEach(field => {
            if (field.value && !this.isValidEmail(field.value)) {
                this.showFieldError(field, 'فرمت ایمیل صحیح نیست');
                isValid = false;
            }
        });

        // Number validation
        const numberFields = form.querySelectorAll('input[type="number"]');
        numberFields.forEach(field => {
            if (field.value && (isNaN(field.value) || parseFloat(field.value) < 0)) {
                this.showFieldError(field, 'عدد معتبر وارد کنید');
                isValid = false;
            }
        });

        // Persian validation for specific fields
        const persianFields = form.querySelectorAll('[data-persian-required]');
        persianFields.forEach(field => {
            if (field.value && !this.containsPersian(field.value)) {
                this.showFieldError(field, 'لطفاً متن فارسی وارد کنید');
                isValid = false;
            }
        });

        return isValid;
    }

    showFieldError(field, message) {
        this.clearFieldError(field);
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'billing-form-error';
        errorDiv.textContent = message;
        
        field.parentNode.appendChild(errorDiv);
        field.classList.add('border-red-500', 'dark:border-red-400');
    }

    clearFieldError(field) {
        const existingError = field.parentNode.querySelector('.billing-form-error');
        if (existingError) {
            existingError.remove();
        }
        field.classList.remove('border-red-500', 'dark:border-red-400');
    }

    showFormLoading(form) {
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = true;
            const originalText = submitButton.textContent;
            submitButton.textContent = 'در حال پردازش...';
            submitButton.dataset.originalText = originalText;
        }
    }

    hideFormLoading(form) {
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = false;
            if (submitButton.dataset.originalText) {
                submitButton.textContent = submitButton.dataset.originalText;
                delete submitButton.dataset.originalText;
            }
        }
    }

    handleRealTimeCalculation(element) {
        const calculationType = element.dataset.calculate;
        
        switch (calculationType) {
            case 'yearly-discount':
                this.calculateYearlyDiscount();
                break;
            case 'invoice-total':
                this.calculateInvoiceTotal();
                break;
            case 'plan-limits':
                this.calculatePlanLimits();
                break;
        }
    }

    calculateYearlyDiscount() {
        const monthlyPrice = parseFloat(document.getElementById('id_monthly_price_toman')?.value) || 0;
        const yearlyPrice = parseFloat(document.getElementById('id_yearly_price_toman')?.value) || 0;
        
        if (monthlyPrice > 0 && yearlyPrice > 0) {
            const monthlyYearly = monthlyPrice * 12;
            const discount = monthlyYearly - yearlyPrice;
            const discountPercentage = Math.round((discount / monthlyYearly) * 100);
            
            const discountDisplay = document.querySelector('.yearly-discount-display');
            if (discountDisplay) {
                discountDisplay.textContent = `تخفیف ${this.formatPersianNumber(discountPercentage)}% (صرفه‌جویی: ${this.formatCurrency(discount)} تومان)`;
                discountDisplay.classList.remove('hidden');
            }
        }
    }

    calculateInvoiceTotal() {
        const subtotal = parseFloat(document.getElementById('subtotal')?.value) || 0;
        const taxRate = parseFloat(document.getElementById('tax_rate')?.value) || 9;
        const discount = parseFloat(document.getElementById('discount')?.value) || 0;
        
        const taxAmount = (subtotal * taxRate) / 100;
        const total = subtotal + taxAmount - discount;
        
        const totalDisplay = document.getElementById('total_display');
        if (totalDisplay) {
            totalDisplay.textContent = this.formatCurrency(total);
        }
    }

    initializeCharts() {
        // Initialize Chart.js charts if present
        if (typeof Chart !== 'undefined') {
            this.initRevenueChart();
            this.initPaymentMethodsChart();
            this.initSubscriptionChart();
        }
    }

    initRevenueChart() {
        const canvas = document.getElementById('revenueChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const isDark = document.documentElement.classList.contains('dark');
        
        // Sample data - would be replaced with real data
        const data = {
            labels: ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور'],
            datasets: [{
                label: 'درآمد (تومان)',
                data: [12000000, 15000000, 13500000, 18000000, 16500000, 20000000],
                borderColor: isDark ? '#00D4FF' : '#3b82f6',
                backgroundColor: isDark ? 'rgba(0, 212, 255, 0.1)' : 'rgba(59, 130, 246, 0.1)',
                tension: 0.4,
                fill: true
            }]
        };

        new Chart(ctx, {
            type: 'line',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: isDark ? '#FFFFFF' : '#374151'
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: isDark ? '#B8BCC8' : '#6B7280',
                            callback: function(value) {
                                return new Intl.NumberFormat('fa-IR').format(value) + ' تومان';
                            }
                        },
                        grid: {
                            color: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: isDark ? '#B8BCC8' : '#6B7280'
                        },
                        grid: {
                            color: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'
                        }
                    }
                }
            }
        });
    }

    initPaymentMethodsChart() {
        const canvas = document.getElementById('paymentMethodsChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const isDark = document.documentElement.classList.contains('dark');
        
        const data = {
            labels: ['انتقال بانکی', 'نقدی', 'چک', 'کارت'],
            datasets: [{
                data: [45, 25, 20, 10],
                backgroundColor: [
                    isDark ? '#00D4FF' : '#3b82f6',
                    isDark ? '#00FF88' : '#10b981',
                    isDark ? '#FF6B35' : '#f59e0b',
                    isDark ? '#A55EEA' : '#8b5cf6'
                ]
            }]
        };

        new Chart(ctx, {
            type: 'doughnut',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: isDark ? '#FFFFFF' : '#374151'
                        }
                    }
                }
            }
        });
    }

    setupFormValidation() {
        // Real-time validation
        document.addEventListener('blur', (e) => {
            if (e.target.matches('.billing-form input, .billing-form select, .billing-form textarea')) {
                this.validateField(e.target);
            }
        }, true);
    }

    validateField(field) {
        const value = field.value.trim();
        let isValid = true;
        let errorMessage = '';

        // Required validation
        if (field.hasAttribute('required') && !value) {
            isValid = false;
            errorMessage = 'این فیلد الزامی است';
        }
        // Email validation
        else if (field.type === 'email' && value && !this.isValidEmail(value)) {
            isValid = false;
            errorMessage = 'فرمت ایمیل صحیح نیست';
        }
        // Number validation
        else if (field.type === 'number' && value && (isNaN(value) || parseFloat(value) < 0)) {
            isValid = false;
            errorMessage = 'عدد معتبر وارد کنید';
        }
        // Persian validation
        else if (field.hasAttribute('data-persian-required') && value && !this.containsPersian(value)) {
            isValid = false;
            errorMessage = 'لطفاً متن فارسی وارد کنید';
        }

        if (isValid) {
            this.clearFieldError(field);
        } else {
            this.showFieldError(field, errorMessage);
        }

        return isValid;
    }

    initializePersianNumbers() {
        // Convert numbers to Persian in elements with persian-numbers class
        document.querySelectorAll('.persian-numbers').forEach(element => {
            const text = element.textContent;
            element.textContent = this.convertToPersianNumbers(text);
        });
    }

    // Utility functions
    formatCurrency(amount) {
        return new Intl.NumberFormat('fa-IR').format(amount);
    }

    formatPersianNumber(number) {
        const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
        return number.toString().replace(/\d/g, (digit) => persianDigits[digit]);
    }

    convertToPersianNumbers(text) {
        const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
        return text.replace(/\d/g, (digit) => persianDigits[digit]);
    }

    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    containsPersian(text) {
        const persianRegex = /[\u0600-\u06FF]/;
        return persianRegex.test(text);
    }

    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    updateInvoiceStatus(invoiceId, status) {
        const statusElements = document.querySelectorAll(`[data-invoice-id="${invoiceId}"] .invoice-status`);
        statusElements.forEach(element => {
            element.className = `invoice-status ${status}`;
            element.textContent = this.getStatusDisplayText(status);
        });
    }

    getStatusDisplayText(status) {
        const statusMap = {
            'paid': 'پرداخت شده',
            'pending': 'در انتظار پرداخت',
            'overdue': 'معوقه',
            'cancelled': 'لغو شده'
        };
        return statusMap[status] || status;
    }

    showMessage(message, type = 'info') {
        // Use the global ZargarAdmin.showMessage if available
        if (window.ZargarAdmin && window.ZargarAdmin.showMessage) {
            window.ZargarAdmin.showMessage(message, type);
        } else {
            // Fallback to alert
            alert(message);
        }
    }

    showLoading() {
        if (window.ZargarAdmin && window.ZargarAdmin.showLoading) {
            window.ZargarAdmin.showLoading();
        }
    }

    hideLoading() {
        if (window.ZargarAdmin && window.ZargarAdmin.hideLoading) {
            window.ZargarAdmin.hideLoading();
        }
    }

    // Export functionality
    exportToCSV(data, filename) {
        const csv = data.map(row => row.join(',')).join('\n');
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
    }

    exportToExcel(data, filename) {
        // This would require a library like SheetJS
        console.log('Excel export functionality would be implemented here');
        this.showMessage('قابلیت خروجی Excel در حال توسعه است', 'info');
    }

    // Print functionality
    printInvoice(invoiceId) {
        const printWindow = window.open(`/admin/tenants/billing/invoices/${invoiceId}/print/`, '_blank');
        if (printWindow) {
            printWindow.onload = function() {
                printWindow.print();
            };
        }
    }
}

// Initialize billing manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.billingManager = new BillingManager();
});

// Global functions for template usage
window.processPayment = function(invoiceId, invoiceNumber) {
    if (window.billingManager) {
        window.billingManager.showPaymentModal(invoiceId, invoiceNumber);
    }
};

window.closePaymentModal = function() {
    if (window.billingManager) {
        window.billingManager.closePaymentModal();
    }
};

window.exportReports = function() {
    if (window.billingManager) {
        window.billingManager.showMessage('در حال تولید گزارش...', 'info');
        // Implementation would go here
    }
};

// Payment form submission handler
document.addEventListener('submit', function(e) {
    if (e.target.id === 'paymentForm') {
        e.preventDefault();
        
        const form = e.target;
        const invoiceId = form.dataset.invoiceId;
        const formData = new FormData(form);
        
        if (window.billingManager && invoiceId) {
            window.billingManager.showLoading();
            window.billingManager.processPayment(formData, invoiceId)
                .finally(() => {
                    window.billingManager.hideLoading();
                });
        }
    }
});