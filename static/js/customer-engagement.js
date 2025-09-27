/**
 * Customer Engagement Dashboard JavaScript
 * Handles interactive functionality for customer engagement and reminders
 */

// Import utility functions from customer-loyalty.js
const { 
    formatNumber, 
    formatCurrency, 
    toPersianNumbers, 
    showNotification,
    makeAjaxRequest 
} = window.CustomerLoyalty || {};

// Engagement-specific functionality
class CustomerEngagement {
    constructor() {
        this.autoRefreshInterval = null;
        this.eventFilters = {
            type: '',
            status: '',
            customer: ''
        };
        this.init();
    }

    init() {
        this.initEventListeners();
        this.initFilters();
        this.initAutoRefresh();
        this.updateEngagementMetrics();
    }

    initEventListeners() {
        // Filter change handlers
        document.addEventListener('change', (e) => {
            if (e.target.matches('[data-filter-type]')) {
                this.handleFilterChange('type', e.target.value);
            }
            if (e.target.matches('[data-filter-status]')) {
                this.handleFilterChange('status', e.target.value);
            }
            if (e.target.matches('[data-filter-customer]')) {
                this.handleFilterChange('customer', e.target.value);
            }
        });

        // Search handlers
        document.addEventListener('input', (e) => {
            if (e.target.matches('[data-search-events]')) {
                this.handleEventSearch(e.target.value);
            }
        });

        // Event action handlers
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-send-event]')) {
                this.sendEvent(e.target.dataset.eventId);
            }
            if (e.target.matches('[data-cancel-event]')) {
                this.cancelEvent(e.target.dataset.eventId);
            }
            if (e.target.matches('[data-create-reminder]')) {
                this.createReminder(e.target.dataset.reminderType);
            }
        });
    }

    initFilters() {
        // Initialize filter dropdowns with current values
        const typeFilter = document.querySelector('[data-filter-type]');
        const statusFilter = document.querySelector('[data-filter-status]');
        const customerFilter = document.querySelector('[data-filter-customer]');

        if (typeFilter) typeFilter.value = this.eventFilters.type;
        if (statusFilter) statusFilter.value = this.eventFilters.status;
        if (customerFilter) customerFilter.value = this.eventFilters.customer;

        this.applyFilters();
    }

    initAutoRefresh() {
        // Auto-refresh engagement metrics every 2 minutes
        this.autoRefreshInterval = setInterval(() => {
            this.updateEngagementMetrics();
        }, 120000);
    }

    handleFilterChange(filterType, value) {
        this.eventFilters[filterType] = value;
        this.applyFilters();
    }

    applyFilters() {
        const events = document.querySelectorAll('[data-event-item]');
        
        events.forEach(event => {
            const eventType = event.dataset.eventType || '';
            const eventStatus = event.dataset.eventStatus || '';
            const eventCustomer = event.dataset.eventCustomer || '';
            
            const typeMatch = !this.eventFilters.type || eventType === this.eventFilters.type;
            const statusMatch = !this.eventFilters.status || eventStatus === this.eventFilters.status;
            const customerMatch = !this.eventFilters.customer || eventCustomer === this.eventFilters.customer;
            
            const shouldShow = typeMatch && statusMatch && customerMatch;
            event.style.display = shouldShow ? '' : 'none';
        });

        this.updateFilterCounts();
    }

    handleEventSearch(searchTerm) {
        const events = document.querySelectorAll('[data-event-item]');
        const term = searchTerm.toLowerCase();
        
        events.forEach(event => {
            const customerName = event.querySelector('[data-customer-name]')?.textContent.toLowerCase() || '';
            const eventTitle = event.querySelector('[data-event-title]')?.textContent.toLowerCase() || '';
            const eventMessage = event.querySelector('[data-event-message]')?.textContent.toLowerCase() || '';
            
            const matches = customerName.includes(term) || 
                          eventTitle.includes(term) || 
                          eventMessage.includes(term);
            
            event.style.display = matches ? '' : 'none';
        });
    }

    updateFilterCounts() {
        const visibleEvents = document.querySelectorAll('[data-event-item]:not([style*="display: none"])');
        const countElement = document.querySelector('[data-event-count]');
        
        if (countElement) {
            countElement.textContent = toPersianNumbers(visibleEvents.length.toString());
        }
    }

    async updateEngagementMetrics() {
        try {
            // Update engagement rate visualization
            this.updateEngagementRateBar();
            
            // Update event type distribution
            this.updateEventTypeDistribution();
            
            // Update upcoming events counter
            this.updateUpcomingEventsCounter();
            
        } catch (error) {
            console.error('Error updating engagement metrics:', error);
        }
    }

    updateEngagementRateBar() {
        const rateElement = document.querySelector('[data-engagement-rate]');
        const barElement = document.querySelector('.engagement-rate-fill');
        
        if (rateElement && barElement) {
            const rate = parseFloat(rateElement.textContent) || 0;
            barElement.style.width = `${rate}%`;
            
            // Add color coding based on rate
            barElement.className = 'engagement-rate-fill';
            if (rate >= 80) {
                barElement.classList.add('metric-progress-success');
            } else if (rate >= 60) {
                barElement.classList.add('metric-progress-warning');
            } else {
                barElement.classList.add('metric-progress-danger');
            }
        }
    }

    updateEventTypeDistribution() {
        const distributionItems = document.querySelectorAll('[data-event-type-count]');
        
        distributionItems.forEach(item => {
            const count = parseInt(item.dataset.eventTypeCount) || 0;
            const progressBar = item.querySelector('.metric-progress-bar');
            
            if (progressBar) {
                // Calculate percentage based on total events
                const totalEvents = Array.from(distributionItems)
                    .reduce((sum, el) => sum + (parseInt(el.dataset.eventTypeCount) || 0), 0);
                
                const percentage = totalEvents > 0 ? (count / totalEvents) * 100 : 0;
                progressBar.style.width = `${percentage}%`;
            }
        });
    }

    updateUpcomingEventsCounter() {
        const upcomingEvents = document.querySelectorAll('[data-upcoming-event]');
        const counterElement = document.querySelector('[data-upcoming-count]');
        
        if (counterElement) {
            counterElement.textContent = toPersianNumbers(upcomingEvents.length.toString());
        }
    }

    async sendEvent(eventId) {
        try {
            const result = await makeAjaxRequest('/customers/ajax/engagement/', {
                action: 'send_event',
                event_id: eventId
            });
            
            if (result.success) {
                showNotification(result.message, 'success');
                this.updateEventStatus(eventId, 'sent');
            } else {
                showNotification(result.error, 'error');
            }
        } catch (error) {
            showNotification('خطا در ارسال رویداد', 'error');
        }
    }

    async cancelEvent(eventId) {
        if (!confirm('آیا از لغو این رویداد اطمینان دارید؟')) {
            return;
        }
        
        try {
            const result = await makeAjaxRequest('/customers/ajax/engagement/', {
                action: 'cancel_event',
                event_id: eventId
            });
            
            if (result.success) {
                showNotification(result.message, 'success');
                this.updateEventStatus(eventId, 'cancelled');
            } else {
                showNotification(result.error, 'error');
            }
        } catch (error) {
            showNotification('خطا در لغو رویداد', 'error');
        }
    }

    async createReminder(reminderType) {
        try {
            const result = await makeAjaxRequest('/customers/reminders/', {
                action: 'create_reminders',
                reminder_type: reminderType
            });
            
            if (result.success) {
                showNotification(result.message, 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification(result.error, 'error');
            }
        } catch (error) {
            showNotification('خطا در ایجاد یادآوری', 'error');
        }
    }

    updateEventStatus(eventId, newStatus) {
        const eventElement = document.querySelector(`[data-event-id="${eventId}"]`);
        if (eventElement) {
            const statusElement = eventElement.querySelector('[data-event-status]');
            if (statusElement) {
                statusElement.textContent = this.getStatusDisplayName(newStatus);
                statusElement.className = `status-${newStatus}`;
            }
            
            // Update dataset
            eventElement.dataset.eventStatus = newStatus;
        }
    }

    getStatusDisplayName(status) {
        const statusNames = {
            'pending': 'در انتظار',
            'sent': 'ارسال شده',
            'delivered': 'تحویل شده',
            'failed': 'ناموفق',
            'cancelled': 'لغو شده'
        };
        return statusNames[status] || status;
    }

    // Birthday and Anniversary specific methods
    initBirthdayReminders() {
        this.loadUpcomingBirthdays();
        this.loadUpcomingAnniversaries();
        this.initCulturalEvents();
    }

    async loadUpcomingBirthdays() {
        try {
            const birthdayContainer = document.querySelector('[data-birthday-list]');
            if (!birthdayContainer) return;
            
            // Show loading state
            birthdayContainer.innerHTML = '<div class="engagement-loading">در حال بارگذاری...</div>';
            
            // In a real implementation, this would fetch from the server
            // For now, we'll work with existing data
            setTimeout(() => {
                this.renderBirthdayList();
            }, 500);
            
        } catch (error) {
            console.error('Error loading birthdays:', error);
        }
    }

    async loadUpcomingAnniversaries() {
        try {
            const anniversaryContainer = document.querySelector('[data-anniversary-list]');
            if (!anniversaryContainer) return;
            
            // Show loading state
            anniversaryContainer.innerHTML = '<div class="engagement-loading">در حال بارگذاری...</div>';
            
            // In a real implementation, this would fetch from the server
            setTimeout(() => {
                this.renderAnniversaryList();
            }, 500);
            
        } catch (error) {
            console.error('Error loading anniversaries:', error);
        }
    }

    renderBirthdayList() {
        // This would render the birthday list with gift suggestions
        // Implementation depends on the data structure
    }

    renderAnniversaryList() {
        // This would render the anniversary list with gift suggestions
        // Implementation depends on the data structure
    }

    initCulturalEvents() {
        const culturalEventButtons = document.querySelectorAll('[data-cultural-event]');
        
        culturalEventButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const eventType = e.target.dataset.culturalEvent;
                this.createCulturalEventReminders(eventType);
            });
        });
    }

    async createCulturalEventReminders(eventType) {
        try {
            const result = await makeAjaxRequest('/customers/reminders/', {
                action: 'create_cultural_event',
                event_type: eventType
            });
            
            if (result.success) {
                showNotification(`یادآوری ${eventType} برای ${result.count} مشتری ایجاد شد`, 'success');
            } else {
                showNotification(result.error, 'error');
            }
        } catch (error) {
            showNotification('خطا در ایجاد یادآوری فرهنگی', 'error');
        }
    }

    // Gift suggestion functionality
    generateGiftSuggestions(customer, occasion) {
        const suggestions = [];
        
        // Base suggestions by occasion
        const baseSuggestions = {
            birthday: [
                { type: 'ring', name_persian: 'انگشتر طلا', price_range: '5000000-15000000' },
                { type: 'necklace', name_persian: 'گردنبند طلا', price_range: '8000000-25000000' },
                { type: 'earrings', name_persian: 'گوشواره طلا', price_range: '3000000-12000000' },
                { type: 'bracelet', name_persian: 'دستبند طلا', price_range: '4000000-18000000' }
            ],
            anniversary: [
                { type: 'jewelry_set', name_persian: 'سرویس طلا', price_range: '15000000-50000000' },
                { type: 'watch', name_persian: 'ساعت طلا', price_range: '20000000-80000000' },
                { type: 'pendant', name_persian: 'آویز طلا', price_range: '6000000-20000000' }
            ]
        };
        
        suggestions.push(...(baseSuggestions[occasion] || []));
        
        // Add VIP suggestions if customer is VIP
        if (customer.is_vip) {
            suggestions.push(
                { type: 'diamond_ring', name_persian: 'انگشتر الماس', price_range: '25000000-100000000' },
                { type: 'emerald_necklace', name_persian: 'گردنبند زمرد', price_range: '30000000-120000000' }
            );
        }
        
        return suggestions.slice(0, 5); // Return top 5 suggestions
    }

    // Cleanup
    destroy() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
    }
}

// Initialize engagement dashboard
let engagementDashboard;

document.addEventListener('DOMContentLoaded', function() {
    engagementDashboard = new CustomerEngagement();
    
    // Initialize birthday reminders if on that page
    if (document.querySelector('[data-birthday-reminders]')) {
        engagementDashboard.initBirthdayReminders();
    }
    
    console.log('Customer Engagement JavaScript initialized');
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (engagementDashboard) {
        engagementDashboard.destroy();
    }
});

// Export for global use
window.CustomerEngagement = CustomerEngagement;