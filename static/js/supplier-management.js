/**
 * Supplier Management JavaScript
 * Handles supplier management UI interactions and AJAX operations
 */

// Global CSRF token for AJAX requests
window.csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                   document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

/**
 * Supplier Dashboard Functions
 */
function supplierDashboard() {
    return {
        darkMode: localStorage.getItem('theme') === 'dark',
        loading: false,
        
        initDashboard() {
            console.log('Supplier dashboard initialized');
            this.setupEventListeners();
            this.loadDashboardData();
        },
        
        setupEventListeners() {
            // Theme toggle
            document.addEventListener('themeChanged', (e) => {
                this.darkMode = e.detail.darkMode;
            });
        },
        
        loadDashboardData() {
            // Load real-time dashboard data if needed
            this.updateMetrics();
        },
        
        updateMetrics() {
            // Update dashboard metrics
            const metricCards = document.querySelectorAll('.metric-card, .cyber-metric-card');
            metricCards.forEach((card, index) => {
                setTimeout(() => {
                    card.style.animationDelay = `${index * 0.1}s`;
                    card.classList.add('animate-fade-in-up');
                }, 100);
            });
        },
        
        toggleSupplierStatus(supplierId, field) {
            this.loading = true;
            
            fetch('/customers/suppliers/ajax/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': window.csrfToken
                },
                body: `action=toggle_${field}&supplier_id=${supplierId}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showMessage(data.message, 'success');
                    setTimeout(() => window.location.reload(), 1000);
                } else {
                    this.showMessage(data.error, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.showMessage('خطا در ارتباط با سرور', 'error');
            })
            .finally(() => {
                this.loading = false;
            });
        },
        
        showMessage(message, type) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `fixed top-20 right-4 z-50 p-4 rounded-lg shadow-lg max-w-sm transition-all duration-300 ${
                type === 'success' ? 'bg-green-100 text-green-800 border border-green-200' :
                type === 'error' ? 'bg-red-100 text-red-800 border border-red-200' :
                'bg-blue-100 text-blue-800 border border-blue-200'
            }`;
            
            if (this.darkMode) {
                messageDiv.className = messageDiv.className.replace('bg-green-100 text-green-800 border-green-200', 'cyber-glass-card text-cyber-neon-secondary border-cyber-neon-secondary/30');
                messageDiv.className = messageDiv.className.replace('bg-red-100 text-red-800 border-red-200', 'cyber-glass-card text-cyber-neon-danger border-cyber-neon-danger/30');
                messageDiv.className = messageDiv.className.replace('bg-blue-100 text-blue-800 border-blue-200', 'cyber-glass-card text-cyber-neon-primary border-cyber-neon-primary/30');
            }
            
            messageDiv.textContent = message;
            document.body.appendChild(messageDiv);
            
            // Animate in
            setTimeout(() => {
                messageDiv.style.transform = 'translateX(0)';
                messageDiv.style.opacity = '1';
            }, 100);
            
            // Remove after 5 seconds
            setTimeout(() => {
                messageDiv.style.transform = 'translateX(100%)';
                messageDiv.style.opacity = '0';
                setTimeout(() => messageDiv.remove(), 300);
            }, 5000);
        }
    }
}

/**
 * Supplier List Functions
 */
function supplierList() {
    return {
        darkMode: localStorage.getItem('theme') === 'dark',
        loading: false,
        selectedSuppliers: [],
        
        initList() {
            console.log('Supplier list initialized');
            this.setupTableInteractions();
            this.setupBulkActions();
        },
        
        setupTableInteractions() {
            // Add hover effects to table rows
            const tableRows = document.querySelectorAll('tbody tr');
            tableRows.forEach(row => {
                row.addEventListener('mouseenter', () => {
                    if (this.darkMode) {
                        row.classList.add('cyber-glass-hover');
                    }
                });
                
                row.addEventListener('mouseleave', () => {
                    row.classList.remove('cyber-glass-hover');
                });
            });
        },
        
        setupBulkActions() {
            // Setup bulk selection
            const selectAllCheckbox = document.getElementById('selectAll');
            const supplierCheckboxes = document.querySelectorAll('.supplier-checkbox');
            
            if (selectAllCheckbox) {
                selectAllCheckbox.addEventListener('change', (e) => {
                    supplierCheckboxes.forEach(checkbox => {
                        checkbox.checked = e.target.checked;
                    });
                    this.updateSelectedSuppliers();
                });
            }
            
            supplierCheckboxes.forEach(checkbox => {
                checkbox.addEventListener('change', () => {
                    this.updateSelectedSuppliers();
                });
            });
        },
        
        updateSelectedSuppliers() {
            const checkedBoxes = document.querySelectorAll('.supplier-checkbox:checked');
            this.selectedSuppliers = Array.from(checkedBoxes).map(cb => cb.value);
            
            // Update bulk action buttons
            const bulkActionButtons = document.querySelectorAll('.bulk-action-btn');
            bulkActionButtons.forEach(btn => {
                btn.disabled = this.selectedSuppliers.length === 0;
            });
        },
        
        toggleSupplierStatus(supplierId, field) {
            this.loading = true;
            
            fetch('/customers/suppliers/ajax/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': window.csrfToken
                },
                body: `action=toggle_${field}&supplier_id=${supplierId}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showMessage(data.message, 'success');
                    setTimeout(() => window.location.reload(), 1000);
                } else {
                    this.showMessage(data.error, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.showMessage('خطا در ارتباط با سرور', 'error');
            })
            .finally(() => {
                this.loading = false;
            });
        },
        
        exportSuppliers(format) {
            const params = new URLSearchParams(window.location.search);
            params.set('export', format);
            window.location.href = `${window.location.pathname}?${params.toString()}`;
        },
        
        showMessage(message, type) {
            // Same as dashboard showMessage
            const messageDiv = document.createElement('div');
            messageDiv.className = `fixed top-20 right-4 z-50 p-4 rounded-lg shadow-lg max-w-sm transition-all duration-300 ${
                type === 'success' ? 'bg-green-100 text-green-800 border border-green-200' :
                type === 'error' ? 'bg-red-100 text-red-800 border border-red-200' :
                'bg-blue-100 text-blue-800 border border-blue-200'
            }`;
            
            if (this.darkMode) {
                messageDiv.className = messageDiv.className.replace('bg-green-100 text-green-800 border-green-200', 'cyber-glass-card text-cyber-neon-secondary border-cyber-neon-secondary/30');
                messageDiv.className = messageDiv.className.replace('bg-red-100 text-red-800 border-red-200', 'cyber-glass-card text-cyber-neon-danger border-cyber-neon-danger/30');
                messageDiv.className = messageDiv.className.replace('bg-blue-100 text-blue-800 border-blue-200', 'cyber-glass-card text-cyber-neon-primary border-cyber-neon-primary/30');
            }
            
            messageDiv.textContent = message;
            document.body.appendChild(messageDiv);
            
            setTimeout(() => {
                messageDiv.style.transform = 'translateX(0)';
                messageDiv.style.opacity = '1';
            }, 100);
            
            setTimeout(() => {
                messageDiv.style.transform = 'translateX(100%)';
                messageDiv.style.opacity = '0';
                setTimeout(() => messageDiv.remove(), 300);
            }, 5000);
        }
    }
}

/**
 * Supplier Form Functions
 */
function supplierForm() {
    return {
        darkMode: localStorage.getItem('theme') === 'dark',
        formData: {},
        
        initForm() {
            console.log('Supplier form initialized');
            this.setupFormValidation();
            this.setupDynamicFields();
        },
        
        setupFormValidation() {
            const form = document.querySelector('form');
            const requiredFields = form.querySelectorAll('[required]');
            
            requiredFields.forEach(field => {
                field.addEventListener('blur', () => {
                    this.validateField(field);
                });
                
                field.addEventListener('input', () => {
                    this.clearFieldError(field);
                });
            });
            
            // Phone number validation
            const phoneField = document.querySelector('input[name="phone_number"]');
            if (phoneField) {
                phoneField.addEventListener('input', (e) => {
                    this.formatPhoneNumber(e.target);
                });
            }
            
            // Email validation
            const emailField = document.querySelector('input[name="email"]');
            if (emailField) {
                emailField.addEventListener('blur', (e) => {
                    this.validateEmail(e.target);
                });
            }
        },
        
        setupDynamicFields() {
            // Supplier type change handler
            const supplierTypeField = document.querySelector('select[name="supplier_type"]');
            if (supplierTypeField) {
                supplierTypeField.addEventListener('change', (e) => {
                    this.handleSupplierTypeChange(e.target.value);
                });
            }
            
            // Auto-fill Persian name
            const nameField = document.querySelector('input[name="name"]');
            const persianNameField = document.querySelector('input[name="persian_name"]');
            
            if (nameField && persianNameField && !persianNameField.value) {
                nameField.addEventListener('input', (e) => {
                    if (!persianNameField.value) {
                        persianNameField.value = e.target.value;
                    }
                });
            }
        },
        
        validateField(field) {
            const value = field.value.trim();
            const fieldContainer = field.closest('div');
            
            if (field.hasAttribute('required') && !value) {
                this.showFieldError(field, 'این فیلد الزامی است');
                return false;
            }
            
            this.clearFieldError(field);
            return true;
        },
        
        validateEmail(field) {
            const email = field.value.trim();
            if (email && !this.isValidEmail(email)) {
                this.showFieldError(field, 'فرمت ایمیل صحیح نیست');
                return false;
            }
            return true;
        },
        
        formatPhoneNumber(field) {
            let value = field.value.replace(/\D/g, '');
            
            // Iranian mobile number format
            if (value.startsWith('98')) {
                value = value.substring(2);
            }
            
            if (value.startsWith('0')) {
                value = value.substring(1);
            }
            
            if (value.length > 0 && !value.startsWith('9')) {
                value = '9' + value;
            }
            
            if (value.length > 10) {
                value = value.substring(0, 10);
            }
            
            field.value = value ? '0' + value : '';
        },
        
        handleSupplierTypeChange(supplierType) {
            // Show/hide relevant fields based on supplier type
            const gemstoneFields = document.querySelectorAll('.gemstone-field');
            const goldFields = document.querySelectorAll('.gold-field');
            const serviceFields = document.querySelectorAll('.service-field');
            
            // Hide all type-specific fields first
            [gemstoneFields, goldFields, serviceFields].forEach(fields => {
                fields.forEach(field => field.style.display = 'none');
            });
            
            // Show relevant fields
            switch (supplierType) {
                case 'gemstone_dealer':
                    gemstoneFields.forEach(field => field.style.display = 'block');
                    break;
                case 'gold_supplier':
                    goldFields.forEach(field => field.style.display = 'block');
                    break;
                case 'service_provider':
                    serviceFields.forEach(field => field.style.display = 'block');
                    break;
            }
        },
        
        showFieldError(field, message) {
            this.clearFieldError(field);
            
            const errorElement = document.createElement('p');
            errorElement.className = `mt-1 text-sm field-error ${
                this.darkMode ? 'text-cyber-neon-danger' : 'text-red-600'
            }`;
            errorElement.textContent = message;
            
            field.parentNode.appendChild(errorElement);
            field.classList.add('border-red-500');
        },
        
        clearFieldError(field) {
            const errorElement = field.parentNode.querySelector('.field-error');
            if (errorElement) {
                errorElement.remove();
            }
            field.classList.remove('border-red-500');
        },
        
        isValidEmail(email) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return emailRegex.test(email);
        }
    }
}

/**
 * Purchase Order List Functions
 */
function purchaseOrderList() {
    return {
        darkMode: localStorage.getItem('theme') === 'dark',
        loading: false,
        
        initList() {
            console.log('Purchase order list initialized');
            this.setupDateFilters();
            this.setupStatusFilters();
        },
        
        setupDateFilters() {
            const dateFromField = document.querySelector('input[name="date_from"]');
            const dateToField = document.querySelector('input[name="date_to"]');
            
            if (dateFromField && dateToField) {
                dateFromField.addEventListener('change', () => {
                    if (dateFromField.value && dateToField.value) {
                        if (new Date(dateFromField.value) > new Date(dateToField.value)) {
                            dateToField.value = dateFromField.value;
                        }
                    }
                });
                
                dateToField.addEventListener('change', () => {
                    if (dateFromField.value && dateToField.value) {
                        if (new Date(dateToField.value) < new Date(dateFromField.value)) {
                            dateFromField.value = dateToField.value;
                        }
                    }
                });
            }
        },
        
        setupStatusFilters() {
            // Add quick filter buttons
            const statusButtons = document.querySelectorAll('.status-filter-btn');
            statusButtons.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const status = e.target.dataset.status;
                    const statusSelect = document.querySelector('select[name="status"]');
                    if (statusSelect) {
                        statusSelect.value = status;
                        statusSelect.form.submit();
                    }
                });
            });
        },
        
        sendOrder(orderId) {
            if (!confirm('آیا از ارسال این سفارش به تامین‌کننده اطمینان دارید؟')) {
                return;
            }
            
            this.loading = true;
            
            fetch('/customers/suppliers/ajax/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': window.csrfToken
                },
                body: `action=send_purchase_order&order_id=${orderId}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showMessage(data.message, 'success');
                    setTimeout(() => window.location.reload(), 1000);
                } else {
                    this.showMessage(data.error, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.showMessage('خطا در ارتباط با سرور', 'error');
            })
            .finally(() => {
                this.loading = false;
            });
        },
        
        cancelOrder(orderId) {
            const reason = prompt('دلیل لغو سفارش را وارد کنید:');
            if (!reason) return;
            
            this.loading = true;
            
            fetch('/customers/suppliers/ajax/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': window.csrfToken
                },
                body: `action=cancel_order&order_id=${orderId}&reason=${encodeURIComponent(reason)}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showMessage(data.message, 'success');
                    setTimeout(() => window.location.reload(), 1000);
                } else {
                    this.showMessage(data.error, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.showMessage('خطا در ارتباط با سرور', 'error');
            })
            .finally(() => {
                this.loading = false;
            });
        },
        
        showMessage(message, type) {
            // Same as other showMessage implementations
            const messageDiv = document.createElement('div');
            messageDiv.className = `fixed top-20 right-4 z-50 p-4 rounded-lg shadow-lg max-w-sm transition-all duration-300 ${
                type === 'success' ? 'bg-green-100 text-green-800 border border-green-200' :
                type === 'error' ? 'bg-red-100 text-red-800 border border-red-200' :
                'bg-blue-100 text-blue-800 border border-blue-200'
            }`;
            
            if (this.darkMode) {
                messageDiv.className = messageDiv.className.replace('bg-green-100 text-green-800 border-green-200', 'cyber-glass-card text-cyber-neon-secondary border-cyber-neon-secondary/30');
                messageDiv.className = messageDiv.className.replace('bg-red-100 text-red-800 border-red-200', 'cyber-glass-card text-cyber-neon-danger border-cyber-neon-danger/30');
                messageDiv.className = messageDiv.className.replace('bg-blue-100 text-blue-800 border-blue-200', 'cyber-glass-card text-cyber-neon-primary border-cyber-neon-primary/30');
            }
            
            messageDiv.textContent = message;
            document.body.appendChild(messageDiv);
            
            setTimeout(() => {
                messageDiv.style.transform = 'translateX(0)';
                messageDiv.style.opacity = '1';
            }, 100);
            
            setTimeout(() => {
                messageDiv.style.transform = 'translateX(100%)';
                messageDiv.style.opacity = '0';
                setTimeout(() => messageDiv.remove(), 300);
            }, 5000);
        }
    }
}

/**
 * Purchase Order Form Functions
 */
function purchaseOrderForm() {
    return {
        darkMode: localStorage.getItem('theme') === 'dark',
        
        initForm() {
            console.log('Purchase order form initialized');
            this.setupFormValidation();
            this.setupSupplierChange();
            this.setupDateValidation();
        },
        
        setupFormValidation() {
            const form = document.querySelector('form');
            const requiredFields = form.querySelectorAll('[required]');
            
            requiredFields.forEach(field => {
                field.addEventListener('blur', () => {
                    this.validateField(field);
                });
                
                field.addEventListener('input', () => {
                    this.clearFieldError(field);
                });
            });
        },
        
        setupSupplierChange() {
            const supplierField = document.querySelector('select[name="supplier"]');
            const paymentTermsField = document.querySelector('input[name="payment_terms"]');
            
            if (supplierField && paymentTermsField) {
                supplierField.addEventListener('change', (e) => {
                    // Auto-fill payment terms from supplier if empty
                    if (!paymentTermsField.value && e.target.selectedOptions[0]) {
                        const supplierPaymentTerms = e.target.selectedOptions[0].dataset.paymentTerms;
                        if (supplierPaymentTerms) {
                            paymentTermsField.value = supplierPaymentTerms;
                        }
                    }
                });
            }
        },
        
        setupDateValidation() {
            const orderDateField = document.querySelector('input[name="order_date"]');
            const deliveryDateField = document.querySelector('input[name="expected_delivery_date"]');
            const paymentDueDateField = document.querySelector('input[name="payment_due_date"]');
            
            if (orderDateField && deliveryDateField) {
                orderDateField.addEventListener('change', () => {
                    if (orderDateField.value && deliveryDateField.value) {
                        if (new Date(orderDateField.value) > new Date(deliveryDateField.value)) {
                            this.showFieldError(deliveryDateField, 'تاریخ تحویل نمی‌تواند قبل از تاریخ سفارش باشد');
                        }
                    }
                });
                
                deliveryDateField.addEventListener('change', () => {
                    if (orderDateField.value && deliveryDateField.value) {
                        if (new Date(deliveryDateField.value) < new Date(orderDateField.value)) {
                            this.showFieldError(deliveryDateField, 'تاریخ تحویل نمی‌تواند قبل از تاریخ سفارش باشد');
                        } else {
                            this.clearFieldError(deliveryDateField);
                        }
                    }
                });
            }
        },
        
        validateField(field) {
            const value = field.value.trim();
            
            if (field.hasAttribute('required') && !value) {
                this.showFieldError(field, 'این فیلد الزامی است');
                return false;
            }
            
            this.clearFieldError(field);
            return true;
        },
        
        showFieldError(field, message) {
            this.clearFieldError(field);
            
            const errorElement = document.createElement('p');
            errorElement.className = `mt-1 text-sm field-error ${
                this.darkMode ? 'text-cyber-neon-danger' : 'text-red-600'
            }`;
            errorElement.textContent = message;
            
            field.parentNode.appendChild(errorElement);
            field.classList.add('border-red-500');
        },
        
        clearFieldError(field) {
            const errorElement = field.parentNode.querySelector('.field-error');
            if (errorElement) {
                errorElement.remove();
            }
            field.classList.remove('border-red-500');
        }
    }
}

/**
 * Supplier Performance Functions
 */
function supplierPerformance() {
    return {
        darkMode: localStorage.getItem('theme') === 'dark',
        
        initPerformance() {
            console.log('Supplier performance report initialized');
            this.setupCharts();
            this.setupExportButtons();
        },
        
        setupCharts() {
            // Initialize performance charts if Chart.js is available
            if (typeof Chart !== 'undefined') {
                this.initPerformanceCharts();
            }
        },
        
        setupExportButtons() {
            const exportButtons = document.querySelectorAll('.export-btn');
            exportButtons.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const format = e.target.dataset.format;
                    this.exportReport(format);
                });
            });
        },
        
        initPerformanceCharts() {
            // Performance chart implementation would go here
            // This is a placeholder for future chart integration
        },
        
        exportReport(format) {
            const params = new URLSearchParams(window.location.search);
            params.set('export', format);
            window.location.href = `${window.location.pathname}?${params.toString()}`;
        }
    }
}

/**
 * Utility Functions
 */
const SupplierUtils = {
    formatCurrency(amount) {
        return new Intl.NumberFormat('fa-IR', {
            style: 'currency',
            currency: 'IRR',
            minimumFractionDigits: 0
        }).format(amount);
    },
    
    formatPersianNumber(number) {
        const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
        return number.toString().replace(/\d/g, (digit) => persianDigits[digit]);
    },
    
    formatDate(date, locale = 'fa-IR') {
        return new Intl.DateTimeFormat(locale).format(new Date(date));
    },
    
    debounce(func, wait) {
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
};

/**
 * Initialize on DOM ready
 */
document.addEventListener('DOMContentLoaded', function() {
    // Apply theme-based styling to form elements
    const isDark = localStorage.getItem('theme') === 'dark';
    const inputs = document.querySelectorAll('input, select, textarea');
    
    inputs.forEach(input => {
        if (isDark) {
            input.classList.add('cyber-input');
        } else {
            input.classList.add('border', 'border-gray-300', 'rounded-lg', 'px-3', 'py-2', 'focus:ring-blue-500', 'focus:border-blue-500');
        }
    });
    
    // Setup global error handling
    window.addEventListener('unhandledrejection', function(event) {
        console.error('Unhandled promise rejection:', event.reason);
    });
});