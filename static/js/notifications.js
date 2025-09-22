/**
 * Notification Management JavaScript
 * Handles all notification-related UI interactions and AJAX calls
 */

// Global notification functions
function showNotification(message, type = 'info', duration = 5000) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = `
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 9999;
        min-width: 300px;
        max-width: 500px;
    `;
    
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-${getIconForType(type)} me-2"></i>
            <span>${message}</span>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
}

function getIconForType(type) {
    const icons = {
        'success': 'check-circle',
        'error': 'exclamation-triangle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle',
        'danger': 'exclamation-triangle'
    };
    return icons[type] || 'info-circle';
}

// CSRF token helper
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Persian number conversion
function persianNumber(num) {
    const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
    return num.toString().replace(/\d/g, (digit) => persianDigits[digit]);
}

// Notification Dashboard Functions
class NotificationDashboard {
    constructor() {
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.startAutoRefresh();
    }
    
    bindEvents() {
        // Status filter functionality
        const statusFilters = document.querySelectorAll('input[name="statusFilter"]');
        statusFilters.forEach(filter => {
            filter.addEventListener('change', (e) => {
                this.filterNotifications(e.target.value);
            });
        });
        
        // Quick action buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action]')) {
                const action = e.target.dataset.action;
                const notificationId = e.target.dataset.notificationId;
                this.handleQuickAction(action, notificationId);
            }
        });
    }
    
    filterNotifications(status) {
        const notifications = document.querySelectorAll('.notification-item');
        notifications.forEach(notification => {
            if (status === '' || notification.dataset.status === status) {
                notification.style.display = 'block';
            } else {
                notification.style.display = 'none';
            }
        });
    }
    
    handleQuickAction(action, notificationId) {
        switch (action) {
            case 'cancel':
                this.cancelNotification(notificationId);
                break;
            case 'retry':
                this.retryNotification(notificationId);
                break;
            case 'duplicate':
                this.duplicateNotification(notificationId);
                break;
        }
    }
    
    cancelNotification(notificationId) {
        if (confirm('آیا مطمئن هستید که می‌خواهید این اعلان را لغو کنید؟')) {
            this.makeRequest(`/notifications/ajax/cancel/${notificationId}/`, 'POST')
                .then(data => {
                    if (data.success) {
                        showNotification(data.message, 'success');
                        location.reload();
                    } else {
                        showNotification(data.error, 'error');
                    }
                });
        }
    }
    
    retryNotification(notificationId) {
        if (confirm('آیا می‌خواهید ارسال مجدد این اعلان را امتحان کنید؟')) {
            this.makeRequest(`/notifications/ajax/retry/${notificationId}/`, 'POST')
                .then(data => {
                    if (data.success) {
                        showNotification(data.message, 'success');
                        location.reload();
                    } else {
                        showNotification(data.error, 'error');
                    }
                });
        }
    }
    
    duplicateNotification(notificationId) {
        showNotification('قابلیت کپی کردن اعلان به زودی پیاده‌سازی خواهد شد', 'info');
    }
    
    refreshStatistics() {
        this.makeRequest('/notifications/ajax/statistics/', 'GET')
            .then(data => {
                if (data.success) {
                    this.updateStatisticsCards(data.stats);
                }
            })
            .catch(error => {
                console.error('Error refreshing statistics:', error);
            });
    }
    
    updateStatisticsCards(stats) {
        const cards = document.querySelectorAll('#statisticsCards .h4');
        if (cards.length >= 4) {
            cards[0].textContent = persianNumber(stats.total_notifications);
            cards[1].textContent = persianNumber(stats.pending_notifications);
            cards[2].textContent = persianNumber(stats.sent_today);
            cards[3].textContent = persianNumber(stats.failed_today);
        }
    }
    
    startAutoRefresh() {
        // Auto-refresh statistics every 30 seconds
        setInterval(() => {
            this.refreshStatistics();
        }, 30000);
    }
    
    makeRequest(url, method, data = null) {
        const options = {
            method: method,
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        return fetch(url, options)
            .then(response => response.json())
            .catch(error => {
                console.error('Request error:', error);
                showNotification('خطا در اتصال به سرور', 'error');
                throw error;
            });
    }
}

// Template Management Functions
class TemplateManager {
    constructor() {
        this.init();
    }
    
    init() {
        this.bindEvents();
    }
    
    bindEvents() {
        // Template preview
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-template-preview]')) {
                const templateId = e.target.dataset.templatePreview;
                this.previewTemplate(templateId);
            }
        });
        
        // Template actions
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-template-action]')) {
                const action = e.target.dataset.templateAction;
                const templateId = e.target.dataset.templateId;
                this.handleTemplateAction(action, templateId);
            }
        });
    }
    
    previewTemplate(templateId) {
        fetch(`/notifications/ajax/template-preview/${templateId}/`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showTemplatePreview(data);
                } else {
                    showNotification('خطا در نمایش الگو: ' + data.error, 'error');
                }
            })
            .catch(error => {
                console.error('Error previewing template:', error);
                showNotification('خطا در اتصال به سرور', 'error');
            });
    }
    
    showTemplatePreview(templateData) {
        // Update preview modal content
        document.getElementById('previewType').textContent = templateData.template_type || '-';
        document.getElementById('previewDeliveryMethods').textContent = 
            templateData.delivery_methods ? templateData.delivery_methods.join(', ').toUpperCase() : '-';
        document.getElementById('previewTitle').textContent = templateData.title || 'عنوان پیام';
        document.getElementById('previewContent').textContent = templateData.content || 'محتوای پیام در اینجا نمایش داده می‌شود';
        
        // Update available variables
        const variablesContainer = document.getElementById('availableVariables');
        if (variablesContainer) {
            variablesContainer.innerHTML = '';
            
            if (templateData.available_variables && Object.keys(templateData.available_variables).length > 0) {
                Object.entries(templateData.available_variables).forEach(([key, description]) => {
                    const variableDiv = document.createElement('div');
                    variableDiv.className = 'col-md-6 mb-2';
                    variableDiv.innerHTML = `
                        <div class="card card-body p-2">
                            <code>{${key}}</code>
                            <small class="text-muted">${description}</small>
                        </div>
                    `;
                    variablesContainer.appendChild(variableDiv);
                });
                
                document.getElementById('previewVariables').textContent = Object.keys(templateData.available_variables).length + ' متغیر';
            } else {
                variablesContainer.innerHTML = '<div class="col-12"><p class="text-muted">هیچ متغیری برای این الگو موجود نیست</p></div>';
                document.getElementById('previewVariables').textContent = 'هیچ کدام';
            }
        }
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('templatePreviewModal'));
        modal.show();
    }
    
    handleTemplateAction(action, templateId) {
        switch (action) {
            case 'use':
                this.useTemplate(templateId);
                break;
            case 'duplicate':
                this.duplicateTemplate(templateId);
                break;
            case 'toggle-status':
                this.toggleTemplateStatus(templateId);
                break;
            case 'set-default':
                this.setAsDefault(templateId);
                break;
        }
    }
    
    useTemplate(templateType) {
        // Redirect to dashboard with template pre-selected
        window.location.href = `/notifications/?template=${templateType}`;
    }
    
    duplicateTemplate(templateId) {
        if (confirm('آیا می‌خواهید کپی از این الگو ایجاد کنید؟')) {
            showNotification('قابلیت کپی کردن الگو به زودی پیاده‌سازی خواهد شد', 'info');
        }
    }
    
    toggleTemplateStatus(templateId) {
        showNotification('قابلیت تغییر وضعیت الگو به زودی پیاده‌سازی خواهد شد', 'info');
    }
    
    setAsDefault(templateId) {
        if (confirm('آیا مطمئن هستید که می‌خواهید این الگو را به عنوان پیش‌فرض تنظیم کنید؟')) {
            showNotification('قابلیت تنظیم الگو پیش‌فرض به زودی پیاده‌سازی خواهد شد', 'info');
        }
    }
}

// Notification Form Handlers
class NotificationFormHandler {
    constructor() {
        this.init();
    }
    
    init() {
        this.bindEvents();
    }
    
    bindEvents() {
        // Single notification form
        const singleForm = document.getElementById('singleNotificationForm');
        if (singleForm) {
            this.initSingleNotificationForm();
        }
        
        // Bulk notification form
        const bulkForm = document.getElementById('bulkNotificationForm');
        if (bulkForm) {
            this.initBulkNotificationForm();
        }
        
        // Schedule notification form
        const scheduleForm = document.getElementById('scheduleNotificationForm');
        if (scheduleForm) {
            this.initScheduleNotificationForm();
        }
    }
    
    initSingleNotificationForm() {
        const templateSelect = document.getElementById('singleTemplateType');
        const recipientTypeSelect = document.getElementById('singleRecipientType');
        
        if (templateSelect) {
            templateSelect.addEventListener('change', () => {
                this.updateContextFields(templateSelect.value, 'single');
                this.updateMessagePreview('single');
            });
        }
        
        if (recipientTypeSelect) {
            recipientTypeSelect.addEventListener('change', () => {
                this.loadRecipients(recipientTypeSelect.value, 'singleRecipientId');
            });
        }
        
        // Send immediately checkbox
        const sendImmediately = document.getElementById('sendImmediately');
        if (sendImmediately) {
            sendImmediately.addEventListener('change', () => {
                const scheduleFields = document.getElementById('scheduleFields');
                const sendButtonText = document.getElementById('sendButtonText');
                
                if (sendImmediately.checked) {
                    scheduleFields.style.display = 'none';
                    sendButtonText.textContent = 'ارسال اعلان';
                } else {
                    scheduleFields.style.display = 'block';
                    sendButtonText.textContent = 'زمان‌بندی اعلان';
                }
            });
        }
    }
    
    initBulkNotificationForm() {
        const templateSelect = document.getElementById('bulkTemplateType');
        const targetSelect = document.getElementById('bulkTargetType');
        
        if (templateSelect) {
            templateSelect.addEventListener('change', () => {
                this.updateContextFields(templateSelect.value, 'bulk');
                this.updateBulkSummary();
            });
        }
        
        if (targetSelect) {
            targetSelect.addEventListener('change', () => {
                this.handleTargetTypeChange(targetSelect.value);
                this.updateBulkSummary();
            });
        }
        
        // Delivery method checkboxes
        document.querySelectorAll('input[name="delivery_methods"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateBulkSummary();
            });
        });
    }
    
    initScheduleNotificationForm() {
        const templateSelect = document.getElementById('scheduleTemplateType');
        const recipientTypeSelect = document.getElementById('scheduleRecipientType');
        
        if (templateSelect) {
            templateSelect.addEventListener('change', () => {
                this.updateContextFields(templateSelect.value, 'schedule');
                this.updateScheduleSummary();
            });
        }
        
        if (recipientTypeSelect) {
            recipientTypeSelect.addEventListener('change', () => {
                this.loadRecipients(recipientTypeSelect.value, 'scheduleRecipientId');
            });
        }
    }
    
    updateContextFields(templateType, formType) {
        const contextVariables = document.getElementById(`${formType}ContextVariables`);
        const contextFields = document.getElementById(`${formType}ContextFields`);
        
        if (!contextFields) return;
        
        // Clear existing fields
        contextFields.innerHTML = '';
        
        const fieldConfigs = {
            'payment_reminder': [
                { name: 'contract_number', label: 'شماره قرارداد', placeholder: 'GI-2024-001' },
                { name: 'amount', label: 'مبلغ (تومان)', placeholder: '2,500,000' },
                { name: 'due_date', label: 'تاریخ سررسید', placeholder: '1403/07/15' }
            ],
            'payment_overdue': [
                { name: 'contract_number', label: 'شماره قرارداد', placeholder: 'GI-2024-001' },
                { name: 'overdue_amount', label: 'مبلغ معوقه', placeholder: '1,000,000' },
                { name: 'overdue_days', label: 'روزهای تأخیر', placeholder: '5' }
            ],
            'birthday_greeting': [
                { name: 'age', label: 'سن', placeholder: '35' },
                { name: 'special_offer', label: 'پیشنهاد ویژه', placeholder: '10% تخفیف' }
            ],
            'appointment_reminder': [
                { name: 'appointment_date', label: 'تاریخ قرار', placeholder: '1403/07/20' },
                { name: 'appointment_time', label: 'ساعت قرار', placeholder: '14:30' },
                { name: 'service_type', label: 'نوع خدمات', placeholder: 'تعمیر جواهرات' }
            ],
            'special_offer': [
                { name: 'offer_title', label: 'عنوان پیشنهاد', placeholder: 'تخفیف ویژه طلا' },
                { name: 'discount_percentage', label: 'درصد تخفیف', placeholder: '20' },
                { name: 'expiry_date', label: 'تاریخ انقضا', placeholder: '1403/08/01' }
            ]
        };
        
        const fields = fieldConfigs[templateType] || [];
        
        if (fields.length > 0 && contextVariables) {
            contextVariables.style.display = 'block';
            
            fields.forEach(field => {
                const colDiv = document.createElement('div');
                colDiv.className = 'col-md-6 mb-3';
                
                colDiv.innerHTML = `
                    <label for="${formType}_context_${field.name}" class="form-label">${field.label}</label>
                    <input type="text" class="form-control" id="${formType}_context_${field.name}" 
                           name="${formType}_context_${field.name}" placeholder="${field.placeholder}">
                `;
                
                contextFields.appendChild(colDiv);
            });
        } else if (contextVariables) {
            contextVariables.style.display = 'none';
        }
    }
    
    loadRecipients(recipientType, selectId) {
        const recipientSelect = document.getElementById(selectId);
        if (!recipientSelect) return;
        
        // Clear existing options
        recipientSelect.innerHTML = '<option value="">در حال بارگذاری...</option>';
        
        // Simulate loading recipients (in real implementation, fetch from API)
        setTimeout(() => {
            recipientSelect.innerHTML = '<option value="">انتخاب گیرنده</option>';
            
            if (recipientType === 'customer') {
                const customers = [
                    { id: 1, name: 'احمد رضایی', phone: '09123456789' },
                    { id: 2, name: 'مریم حسینی', phone: '09987654321' },
                    { id: 3, name: 'علی محمدی', phone: '09111222333' }
                ];
                
                customers.forEach(customer => {
                    const option = document.createElement('option');
                    option.value = customer.id;
                    option.textContent = `${customer.name} (${customer.phone})`;
                    recipientSelect.appendChild(option);
                });
            } else if (recipientType === 'user') {
                const users = [
                    { id: 1, name: 'مدیر فروشگاه', role: 'owner' },
                    { id: 2, name: 'حسابدار', role: 'accountant' }
                ];
                
                users.forEach(user => {
                    const option = document.createElement('option');
                    option.value = user.id;
                    option.textContent = `${user.name} (${user.role})`;
                    recipientSelect.appendChild(option);
                });
            }
        }, 500);
    }
    
    updateMessagePreview(formType = 'single') {
        const templateType = document.getElementById(`${formType}TemplateType`)?.value;
        const previewDiv = document.getElementById('messagePreview');
        const titleElement = document.getElementById('previewMessageTitle');
        const contentElement = document.getElementById('previewMessageContent');
        
        if (!templateType || !previewDiv) return;
        
        let title = '';
        let content = '';
        
        if (templateType === 'custom') {
            title = document.getElementById('customTitle')?.value || 'پیام سفارشی';
            content = document.getElementById('customContent')?.value || 'پیام سفارشی شما در اینجا نمایش داده می‌شود';
        } else {
            // Get context values
            const context = {};
            const contextInputs = document.querySelectorAll(`#${formType}ContextFields input`);
            contextInputs.forEach(input => {
                const fieldName = input.name.replace(`${formType}_context_`, '');
                context[fieldName] = input.value || input.placeholder;
            });
            
            // Sample templates
            const templates = {
                'payment_reminder': {
                    title: 'یادآوری پرداخت',
                    content: `سلام {customer_name}، پرداخت قرارداد ${context.contract_number || '{contract_number}'} به مبلغ ${context.amount || '{amount}'} تومان در تاریخ ${context.due_date || '{due_date}'} سررسید می‌شود.`
                },
                'birthday_greeting': {
                    title: 'تولدت مبارک',
                    content: `سلام {customer_name}، تولد ${context.age || '{age}'} سالگی‌ت مبارک! ${context.special_offer || '{special_offer}'} ویژه شما آماده است.`
                }
            };
            
            const template = templates[templateType];
            if (template) {
                title = template.title;
                content = template.content;
            }
        }
        
        if (titleElement) titleElement.textContent = title;
        if (contentElement) contentElement.textContent = content;
        if (previewDiv) previewDiv.style.display = 'block';
    }
    
    updateBulkSummary() {
        const templateType = document.getElementById('bulkTemplateType')?.value;
        const targetType = document.getElementById('bulkTargetType')?.value;
        const deliveryMethods = Array.from(document.querySelectorAll('input[name="delivery_methods"]:checked'))
                                    .map(cb => cb.value);
        
        // Update template display
        const summaryTemplate = document.getElementById('summaryTemplate');
        if (summaryTemplate) {
            if (templateType) {
                const templateSelect = document.getElementById('bulkTemplateType');
                summaryTemplate.textContent = templateSelect.options[templateSelect.selectedIndex].text;
            } else {
                summaryTemplate.textContent = 'انتخاب نشده';
            }
        }
        
        // Update recipients count
        const summaryRecipients = document.getElementById('summaryRecipients');
        if (summaryRecipients) {
            let recipientCount = 0;
            
            if (targetType === 'selected_customers') {
                recipientCount = document.querySelectorAll('#selectedCustomers > div').length;
            } else if (targetType) {
                const counts = {
                    'all_customers': 150,
                    'vip_customers': 25,
                    'recent_customers': 45,
                    'birthday_customers': 3,
                    'overdue_customers': 12
                };
                recipientCount = counts[targetType] || 0;
            }
            
            summaryRecipients.textContent = persianNumber(recipientCount);
        }
        
        // Update delivery methods
        const summaryDelivery = document.getElementById('summaryDelivery');
        if (summaryDelivery) {
            if (deliveryMethods.length > 0) {
                summaryDelivery.textContent = deliveryMethods.join(', ').toUpperCase();
            } else {
                summaryDelivery.textContent = 'انتخاب نشده';
            }
        }
        
        // Calculate estimated cost
        const estimatedCost = document.getElementById('estimatedCost');
        if (estimatedCost) {
            const recipientCount = parseInt(document.getElementById('summaryRecipients')?.textContent.replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d)) || '0');
            
            if (recipientCount > 0 && deliveryMethods.length > 0) {
                const costs = { sms: 500, email: 100, push: 0, whatsapp: 300 };
                let totalCost = 0;
                
                deliveryMethods.forEach(method => {
                    totalCost += (costs[method] || 0) * recipientCount;
                });
                
                estimatedCost.textContent = `${totalCost.toLocaleString('fa-IR')} تومان`;
            } else {
                estimatedCost.textContent = 'در حال محاسبه...';
            }
        }
    }
    
    updateScheduleSummary() {
        // Implementation for schedule summary update
        console.log('Schedule summary update');
    }
    
    handleTargetTypeChange(targetType) {
        const customerSelectionSection = document.getElementById('customerSelectionSection');
        
        if (customerSelectionSection) {
            if (targetType === 'selected_customers') {
                customerSelectionSection.style.display = 'block';
                this.loadAvailableCustomers();
            } else {
                customerSelectionSection.style.display = 'none';
            }
        }
    }
    
    loadAvailableCustomers() {
        const availableCustomers = document.getElementById('availableCustomers');
        if (!availableCustomers) return;
        
        const customers = [
            { id: 1, name: 'احمد رضایی', phone: '09123456789', type: 'vip' },
            { id: 2, name: 'مریم حسینی', phone: '09987654321', type: 'regular' },
            { id: 3, name: 'علی محمدی', phone: '09111222333', type: 'regular' },
            { id: 4, name: 'فاطمه احمدی', phone: '09444555666', type: 'vip' },
            { id: 5, name: 'حسن کریمی', phone: '09777888999', type: 'regular' }
        ];
        
        availableCustomers.innerHTML = '';
        
        customers.forEach(customer => {
            const customerDiv = document.createElement('div');
            customerDiv.className = 'form-check mb-2';
            customerDiv.innerHTML = `
                <input class="form-check-input" type="checkbox" id="customer_${customer.id}" 
                       value="${customer.id}" onchange="toggleCustomerSelection(${customer.id}, '${customer.name}', '${customer.phone}')">
                <label class="form-check-label" for="customer_${customer.id}">
                    <div>
                        <strong>${customer.name}</strong>
                        ${customer.type === 'vip' ? '<span class="badge bg-warning ms-2">VIP</span>' : ''}
                    </div>
                    <small class="text-muted">${customer.phone}</small>
                </label>
            `;
            
            availableCustomers.appendChild(customerDiv);
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize notification dashboard if on dashboard page
    if (document.querySelector('#statisticsCards')) {
        new NotificationDashboard();
    }
    
    // Initialize template manager if on template pages
    if (document.querySelector('[data-template-preview]') || document.querySelector('[data-template-action]')) {
        new TemplateManager();
    }
    
    // Initialize form handlers if forms are present
    if (document.querySelector('#singleNotificationForm') || 
        document.querySelector('#bulkNotificationForm') || 
        document.querySelector('#scheduleNotificationForm')) {
        new NotificationFormHandler();
    }
});

// Global functions for template usage
window.toggleCustomerSelection = function(customerId, customerName, customerPhone) {
    const checkbox = document.getElementById(`customer_${customerId}`);
    const selectedCustomers = document.getElementById('selectedCustomers');
    
    if (!checkbox || !selectedCustomers) return;
    
    if (checkbox.checked) {
        // Add to selected
        const selectedDiv = document.createElement('div');
        selectedDiv.id = `selected_${customerId}`;
        selectedDiv.className = 'mb-2 p-2 bg-light rounded';
        selectedDiv.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <strong>${customerName}</strong>
                    <br><small class="text-muted">${customerPhone}</small>
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger" 
                        onclick="removeCustomerSelection(${customerId})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        selectedCustomers.appendChild(selectedDiv);
    } else {
        // Remove from selected
        const selectedDiv = document.getElementById(`selected_${customerId}`);
        if (selectedDiv) {
            selectedDiv.remove();
        }
    }
    
    // Update bulk summary if function exists
    if (typeof updateBulkSummary === 'function') {
        updateBulkSummary();
    }
};

window.removeCustomerSelection = function(customerId) {
    // Uncheck the checkbox
    const checkbox = document.getElementById(`customer_${customerId}`);
    if (checkbox) {
        checkbox.checked = false;
    }
    
    // Remove from selected
    const selectedDiv = document.getElementById(`selected_${customerId}`);
    if (selectedDiv) {
        selectedDiv.remove();
    }
    
    // Update bulk summary if function exists
    if (typeof updateBulkSummary === 'function') {
        updateBulkSummary();
    }
};