/**
 * Customer Reminders JavaScript
 * Handles birthday and anniversary reminder functionality
 */

// Import utility functions
const { 
    formatNumber, 
    formatCurrency, 
    toPersianNumbers, 
    showNotification,
    makeAjaxRequest 
} = window.CustomerLoyalty || {};

class CustomerReminders {
    constructor() {
        this.reminderForms = {};
        this.giftSuggestions = {};
        this.init();
    }

    init() {
        this.initEventListeners();
        this.initForms();
        this.loadGiftSuggestions();
        this.initCulturalEvents();
    }

    initEventListeners() {
        // Form submission handlers
        document.addEventListener('submit', (e) => {
            if (e.target.matches('[data-reminder-form]')) {
                e.preventDefault();
                this.handleReminderFormSubmit(e.target);
            }
        });

        // Gift suggestion interactions
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-gift-suggestion]')) {
                this.handleGiftSuggestionClick(e.target);
            }
            if (e.target.matches('[data-view-message]')) {
                this.showMessagePreview(e.target.dataset.eventId);
            }
            if (e.target.matches('[data-send-reminder]')) {
                this.sendReminder(e.target.dataset.eventId);
            }
        });

        // Cultural event handlers
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-cultural-event]')) {
                this.handleCulturalEventClick(e.target);
            }
        });

        // Filter and search
        document.addEventListener('input', (e) => {
            if (e.target.matches('[data-search-reminders]')) {
                this.handleReminderSearch(e.target.value);
            }
        });

        document.addEventListener('change', (e) => {
            if (e.target.matches('[data-filter-reminders]')) {
                this.handleReminderFilter(e.target);
            }
        });
    }

    initForms() {
        const forms = document.querySelectorAll('[data-reminder-form]');
        forms.forEach(form => {
            const formType = form.dataset.reminderForm;
            this.reminderForms[formType] = {
                element: form,
                isSubmitting: false
            };
        });
    }

    async handleReminderFormSubmit(form) {
        const formType = form.dataset.reminderForm;
        const formData = new FormData(form);
        
        if (this.reminderForms[formType]?.isSubmitting) {
            return;
        }

        try {
            this.reminderForms[formType].isSubmitting = true;
            this.setFormLoading(form, true);

            const result = await makeAjaxRequest(form.action || window.location.pathname, {
                action: formData.get('action'),
                days_ahead: formData.get('days_ahead'),
                event_type: formData.get('event_type')
            });

            if (result.success) {
                showNotification(result.message, 'success');
                this.resetForm(form);
                
                // Refresh the page after a short delay to show updated data
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showNotification(result.error || 'خطا در ایجاد یادآوری', 'error');
            }

        } catch (error) {
            console.error('Error submitting reminder form:', error);
            showNotification('خطا در ایجاد یادآوری', 'error');
        } finally {
            this.reminderForms[formType].isSubmitting = false;
            this.setFormLoading(form, false);
        }
    }

    setFormLoading(form, isLoading) {
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = isLoading;
            submitButton.textContent = isLoading ? 'در حال ایجاد...' : submitButton.dataset.originalText || submitButton.textContent;
            
            if (!submitButton.dataset.originalText) {
                submitButton.dataset.originalText = submitButton.textContent;
            }
        }

        // Add loading class to form
        form.classList.toggle('reminder-loading', isLoading);
    }

    resetForm(form) {
        form.reset();
        form.classList.remove('reminder-success', 'reminder-error');
        
        // Reset any custom styling
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.classList.remove('border-red-500', 'border-green-500');
        });
    }

    loadGiftSuggestions() {
        // Load gift suggestions for different occasions
        this.giftSuggestions = {
            birthday: [
                { type: 'ring', name_persian: 'انگشتر طلا', price_range: '5000000-15000000', icon: '💍' },
                { type: 'necklace', name_persian: 'گردنبند طلا', price_range: '8000000-25000000', icon: '📿' },
                { type: 'earrings', name_persian: 'گوشواره طلا', price_range: '3000000-12000000', icon: '👂' },
                { type: 'bracelet', name_persian: 'دستبند طلا', price_range: '4000000-18000000', icon: '⌚' }
            ],
            anniversary: [
                { type: 'jewelry_set', name_persian: 'سرویس طلا', price_range: '15000000-50000000', icon: '💎' },
                { type: 'watch', name_persian: 'ساعت طلا', price_range: '20000000-80000000', icon: '⌚' },
                { type: 'pendant', name_persian: 'آویز طلا', price_range: '6000000-20000000', icon: '🔗' }
            ],
            vip: [
                { type: 'diamond_ring', name_persian: 'انگشتر الماس', price_range: '25000000-100000000', icon: '💎' },
                { type: 'emerald_necklace', name_persian: 'گردنبند زمرد', price_range: '30000000-120000000', icon: '💚' }
            ]
        };
    }

    handleGiftSuggestionClick(element) {
        const giftType = element.dataset.giftType;
        const customerId = element.dataset.customerId;
        
        // Toggle selection
        element.classList.toggle('selected');
        
        // Update gift suggestion in the system
        this.updateGiftSuggestion(customerId, giftType, element.classList.contains('selected'));
    }

    async updateGiftSuggestion(customerId, giftType, isSelected) {
        try {
            const result = await makeAjaxRequest('/customers/ajax/reminders/', {
                action: 'update_gift_suggestion',
                customer_id: customerId,
                gift_type: giftType,
                is_selected: isSelected
            });

            if (result.success) {
                // Visual feedback
                showNotification(
                    isSelected ? 'پیشنهاد هدیه اضافه شد' : 'پیشنهاد هدیه حذف شد', 
                    'success'
                );
            }
        } catch (error) {
            console.error('Error updating gift suggestion:', error);
        }
    }

    showMessagePreview(eventId) {
        const messageElement = document.querySelector(`[data-message-preview="${eventId}"]`);
        if (messageElement) {
            // Toggle visibility
            messageElement.classList.toggle('hidden');
            
            // Animate in
            if (!messageElement.classList.contains('hidden')) {
                messageElement.style.opacity = '0';
                messageElement.style.transform = 'translateY(-10px)';
                
                setTimeout(() => {
                    messageElement.style.transition = 'all 0.3s ease';
                    messageElement.style.opacity = '1';
                    messageElement.style.transform = 'translateY(0)';
                }, 10);
            }
        }
    }

    async sendReminder(eventId) {
        if (!confirm('آیا از ارسال این یادآوری اطمینان دارید؟')) {
            return;
        }

        try {
            const result = await makeAjaxRequest('/customers/ajax/reminders/', {
                action: 'send_reminder',
                event_id: eventId
            });

            if (result.success) {
                showNotification(result.message, 'success');
                
                // Update UI to show sent status
                this.updateReminderStatus(eventId, 'sent');
            } else {
                showNotification(result.error, 'error');
            }
        } catch (error) {
            showNotification('خطا در ارسال یادآوری', 'error');
        }
    }

    updateReminderStatus(eventId, newStatus) {
        const reminderElement = document.querySelector(`[data-reminder-id="${eventId}"]`);
        if (reminderElement) {
            const statusElement = reminderElement.querySelector('[data-status]');
            if (statusElement) {
                statusElement.textContent = this.getStatusDisplayName(newStatus);
                statusElement.className = `status-${newStatus}`;
            }

            // Update send button
            const sendButton = reminderElement.querySelector('[data-send-reminder]');
            if (sendButton && newStatus === 'sent') {
                sendButton.disabled = true;
                sendButton.textContent = 'ارسال شده';
                sendButton.classList.add('opacity-50');
            }
        }
    }

    getStatusDisplayName(status) {
        const statusNames = {
            'pending': 'در انتظار',
            'sent': 'ارسال شده',
            'delivered': 'تحویل شده',
            'failed': 'ناموفق'
        };
        return statusNames[status] || status;
    }

    initCulturalEvents() {
        const culturalEvents = {
            nowruz: {
                name: 'نوروز',
                description: 'سال نو فارسی',
                color: 'green',
                message_template: 'نوروز مبارک! سال نو برایتان پر از شادی و موفقیت باشد!'
            },
            yalda: {
                name: 'شب یلدا',
                description: 'طولانی‌ترین شب سال',
                color: 'purple',
                message_template: 'شب یلدا مبارک! این طولانی‌ترین شب برایتان گرمی و خوشحالی به ارمغان بیاورد!'
            },
            mehregan: {
                name: 'مهرگان',
                description: 'جشن مهر و دوستی',
                color: 'yellow',
                message_template: 'مهرگان مبارک! زیبایی پاییز و دوستی را با شما جشن می‌گیریم!'
            }
        };

        // Store for later use
        this.culturalEvents = culturalEvents;
    }

    async handleCulturalEventClick(element) {
        const eventType = element.dataset.culturalEvent;
        const eventInfo = this.culturalEvents[eventType];

        if (!eventInfo) {
            showNotification('نوع رویداد نامعتبر', 'error');
            return;
        }

        // Show confirmation with event details
        const confirmed = confirm(
            `آیا می‌خواهید برای همه مشتریان VIP یادآوری ${eventInfo.name} ایجاد کنید؟\n\n` +
            `پیام: ${eventInfo.message_template}`
        );

        if (!confirmed) {
            return;
        }

        try {
            // Disable button during request
            element.disabled = true;
            element.textContent = 'در حال ایجاد...';

            const result = await makeAjaxRequest(window.location.pathname, {
                action: 'create_cultural_event',
                event_type: eventType
            });

            if (result.success) {
                showNotification(result.message, 'success');
                
                // Update button to show success
                element.textContent = 'ایجاد شد ✓';
                element.classList.add('reminder-success');
                
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                showNotification(result.error, 'error');
                element.textContent = eventInfo.name;
                element.disabled = false;
            }
        } catch (error) {
            showNotification('خطا در ایجاد یادآوری فرهنگی', 'error');
            element.textContent = eventInfo.name;
            element.disabled = false;
        }
    }

    handleReminderSearch(searchTerm) {
        const reminders = document.querySelectorAll('[data-reminder-item]');
        const term = searchTerm.toLowerCase();

        reminders.forEach(reminder => {
            const customerName = reminder.querySelector('[data-customer-name]')?.textContent.toLowerCase() || '';
            const eventType = reminder.querySelector('[data-event-type]')?.textContent.toLowerCase() || '';
            
            const matches = customerName.includes(term) || eventType.includes(term);
            reminder.style.display = matches ? '' : 'none';
        });

        this.updateSearchResults(searchTerm);
    }

    updateSearchResults(searchTerm) {
        const visibleReminders = document.querySelectorAll('[data-reminder-item]:not([style*="display: none"])');
        const resultCount = document.querySelector('[data-search-results]');
        
        if (resultCount) {
            if (searchTerm.trim()) {
                resultCount.textContent = `${toPersianNumbers(visibleReminders.length.toString())} نتیجه یافت شد`;
                resultCount.classList.remove('hidden');
            } else {
                resultCount.classList.add('hidden');
            }
        }
    }

    handleReminderFilter(filterElement) {
        const filterType = filterElement.dataset.filterType;
        const filterValue = filterElement.value;
        const reminders = document.querySelectorAll('[data-reminder-item]');

        reminders.forEach(reminder => {
            const itemValue = reminder.dataset[filterType] || '';
            const shouldShow = !filterValue || itemValue === filterValue;
            reminder.style.display = shouldShow ? '' : 'none';
        });

        this.updateFilterResults(filterType, filterValue);
    }

    updateFilterResults(filterType, filterValue) {
        const visibleReminders = document.querySelectorAll('[data-reminder-item]:not([style*="display: none"])');
        const resultCount = document.querySelector('[data-filter-results]');
        
        if (resultCount) {
            if (filterValue) {
                resultCount.textContent = `${toPersianNumbers(visibleReminders.length.toString())} مورد فیلتر شده`;
                resultCount.classList.remove('hidden');
            } else {
                resultCount.classList.add('hidden');
            }
        }
    }

    // Utility methods
    formatPersianDate(date) {
        if (!date) return '';
        
        try {
            const d = new Date(date);
            const options = { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric',
                calendar: 'persian',
                numberingSystem: 'arabext'
            };
            
            return new Intl.DateTimeFormat('fa-IR', options).format(d);
        } catch (e) {
            // Fallback
            return toPersianNumbers(new Date(date).toLocaleDateString('fa-IR'));
        }
    }

    calculateDaysUntil(targetDate) {
        const today = new Date();
        const target = new Date(targetDate);
        const diffTime = target - today;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        return Math.max(0, diffDays);
    }

    // Animation helpers
    animateReminderCard(element) {
        element.classList.add('reminder-card-enter');
        
        setTimeout(() => {
            element.classList.remove('reminder-card-enter');
        }, 400);
    }

    // Cleanup
    destroy() {
        // Clean up any intervals or event listeners if needed
    }
}

// Initialize reminders system
let customerReminders;

document.addEventListener('DOMContentLoaded', function() {
    customerReminders = new CustomerReminders();
    
    // Convert Persian numbers on load
    const numberElements = document.querySelectorAll('.persian-numbers');
    numberElements.forEach(el => {
        if (el.textContent && !el.dataset.converted) {
            el.textContent = toPersianNumbers(el.textContent);
            el.dataset.converted = 'true';
        }
    });
    
    console.log('Customer Reminders JavaScript initialized');
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (customerReminders) {
        customerReminders.destroy();
    }
});

// Export for global use
window.CustomerReminders = CustomerReminders;