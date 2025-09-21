/**
 * Customer Loyalty Dashboard JavaScript
 * Handles interactive functionality for the loyalty management system
 */

// Persian number conversion
const persianNumbers = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
const englishNumbers = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];

function toPersianNumbers(str) {
    if (typeof str !== 'string') str = String(str);
    for (let i = 0; i < englishNumbers.length; i++) {
        str = str.replace(new RegExp(englishNumbers[i], 'g'), persianNumbers[i]);
    }
    return str;
}

function toEnglishNumbers(str) {
    if (typeof str !== 'string') str = String(str);
    for (let i = 0; i < persianNumbers.length; i++) {
        str = str.replace(new RegExp(persianNumbers[i], 'g'), englishNumbers[i]);
    }
    return str;
}

// Number formatting functions
function formatNumber(num) {
    if (num === null || num === undefined) return '۰';
    return toPersianNumbers(Number(num).toLocaleString('en-US'));
}

function formatCurrency(amount) {
    if (amount === null || amount === undefined) return '۰ تومان';
    const formatted = Number(amount).toLocaleString('en-US');
    return toPersianNumbers(formatted) + ' تومان';
}

// Theme management
function initTheme() {
    const theme = localStorage.getItem('theme') || 'light';
    document.documentElement.classList.toggle('dark', theme === 'dark');
    return theme === 'dark';
}

// Notification system
function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 left-4 z-50 p-4 rounded-lg shadow-lg transform transition-all duration-300 ${getNotificationClasses(type)}`;
    notification.textContent = message;
    
    // Add to DOM
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.classList.add('translate-x-0');
        notification.classList.remove('translate-x-full');
    }, 100);
    
    // Remove after duration
    setTimeout(() => {
        notification.classList.add('translate-x-full');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, duration);
}

function getNotificationClasses(type) {
    const isDark = document.documentElement.classList.contains('dark');
    
    if (isDark) {
        switch (type) {
            case 'success':
                return 'bg-cyber-bg-surface border border-cyber-neon-success text-cyber-neon-success';
            case 'error':
                return 'bg-cyber-bg-surface border border-cyber-neon-danger text-cyber-neon-danger';
            case 'warning':
                return 'bg-cyber-bg-surface border border-cyber-neon-warning text-cyber-neon-warning';
            default:
                return 'bg-cyber-bg-surface border border-cyber-neon-primary text-cyber-text-primary';
        }
    } else {
        switch (type) {
            case 'success':
                return 'bg-green-500 text-white';
            case 'error':
                return 'bg-red-500 text-white';
            case 'warning':
                return 'bg-yellow-500 text-white';
            default:
                return 'bg-blue-500 text-white';
        }
    }
}

// AJAX helper functions
async function makeAjaxRequest(url, data) {
    try {
        const formData = new FormData();
        
        // Add CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (csrfToken) {
            formData.append('csrfmiddlewaretoken', csrfToken);
        }
        
        // Add data
        for (const [key, value] of Object.entries(data)) {
            formData.append(key, value);
        }
        
        const response = await fetch(url, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('AJAX request failed:', error);
        throw error;
    }
}

// Loyalty points management
async function awardLoyaltyPoints(customerId, points, reason) {
    try {
        const data = await makeAjaxRequest('/customers/ajax/loyalty/', {
            action: 'award_points',
            customer_id: customerId,
            points: points,
            reason: reason
        });
        
        if (data.success) {
            showNotification(data.message, 'success');
            return data;
        } else {
            showNotification(data.error, 'error');
            return null;
        }
    } catch (error) {
        showNotification('خطا در اعطای امتیاز', 'error');
        return null;
    }
}

async function redeemLoyaltyPoints(customerId, points, reason) {
    try {
        const data = await makeAjaxRequest('/customers/ajax/loyalty/', {
            action: 'redeem_points',
            customer_id: customerId,
            points: points,
            reason: reason
        });
        
        if (data.success) {
            showNotification(data.message, 'success');
            return data;
        } else {
            showNotification(data.error, 'error');
            return null;
        }
    } catch (error) {
        showNotification('خطا در کسر امتیاز', 'error');
        return null;
    }
}

async function updateCustomerTier(customerId) {
    try {
        const data = await makeAjaxRequest('/customers/ajax/loyalty/', {
            action: 'update_tier',
            customer_id: customerId
        });
        
        if (data.success) {
            showNotification(data.message, 'success');
            return data;
        } else {
            showNotification(data.message, 'warning');
            return null;
        }
    } catch (error) {
        showNotification('خطا در بروزرسانی سطح مشتری', 'error');
        return null;
    }
}

async function createSpecialOffer(customerId, offerType, discountPercentage, validDays) {
    try {
        const data = await makeAjaxRequest('/customers/ajax/loyalty/', {
            action: 'create_special_offer',
            customer_id: customerId,
            offer_type: offerType,
            discount_percentage: discountPercentage,
            valid_days: validDays
        });
        
        if (data.success) {
            showNotification(data.message, 'success');
            return data;
        } else {
            showNotification(data.error, 'error');
            return null;
        }
    } catch (error) {
        showNotification('خطا در ایجاد پیشنهاد ویژه', 'error');
        return null;
    }
}

// Form validation
function validateForm(formElement) {
    const requiredFields = formElement.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('border-red-500');
            isValid = false;
        } else {
            field.classList.remove('border-red-500');
        }
    });
    
    return isValid;
}

// Modal management
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'block';
        document.body.classList.add('overflow-hidden');
        
        // Focus first input
        const firstInput = modal.querySelector('input, select, textarea');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        document.body.classList.remove('overflow-hidden');
    }
}

// Data refresh
async function refreshDashboardData() {
    try {
        // Show loading indicator
        const loadingElements = document.querySelectorAll('.metric-card, .cyber-metric-card');
        loadingElements.forEach(el => {
            el.classList.add('loading-shimmer');
        });
        
        // Reload page to get fresh data
        setTimeout(() => {
            window.location.reload();
        }, 1000);
        
    } catch (error) {
        console.error('Error refreshing dashboard data:', error);
        showNotification('خطا در بروزرسانی داده‌ها', 'error');
    }
}

// Auto-refresh functionality
let autoRefreshInterval;

function startAutoRefresh(intervalMinutes = 5) {
    stopAutoRefresh(); // Clear any existing interval
    
    autoRefreshInterval = setInterval(() => {
        refreshDashboardData();
    }, intervalMinutes * 60 * 1000);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// Search and filter functionality
function initSearchAndFilter() {
    const searchInputs = document.querySelectorAll('[data-search]');
    const filterSelects = document.querySelectorAll('[data-filter]');
    
    searchInputs.forEach(input => {
        input.addEventListener('input', debounce(handleSearch, 300));
    });
    
    filterSelects.forEach(select => {
        select.addEventListener('change', handleFilter);
    });
}

function handleSearch(event) {
    const searchTerm = event.target.value.toLowerCase();
    const targetSelector = event.target.dataset.search;
    const items = document.querySelectorAll(targetSelector);
    
    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        const shouldShow = text.includes(searchTerm);
        item.style.display = shouldShow ? '' : 'none';
    });
}

function handleFilter(event) {
    const filterValue = event.target.value;
    const targetSelector = event.target.dataset.filter;
    const items = document.querySelectorAll(targetSelector);
    
    items.forEach(item => {
        const itemValue = item.dataset.filterValue;
        const shouldShow = !filterValue || itemValue === filterValue;
        item.style.display = shouldShow ? '' : 'none';
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

function formatDate(date, format = 'persian') {
    if (!date) return '';
    
    const d = new Date(date);
    
    if (format === 'persian') {
        // Convert to Persian calendar (simplified)
        const options = { 
            year: 'numeric', 
            month: '2-digit', 
            day: '2-digit',
            calendar: 'persian',
            numberingSystem: 'arabext'
        };
        
        try {
            return new Intl.DateTimeFormat('fa-IR', options).format(d);
        } catch (e) {
            // Fallback to Gregorian with Persian numbers
            const gregorian = d.toLocaleDateString('en-US');
            return toPersianNumbers(gregorian);
        }
    }
    
    return d.toLocaleDateString('fa-IR');
}

// Export functions for global use
window.CustomerLoyalty = {
    formatNumber,
    formatCurrency,
    toPersianNumbers,
    toEnglishNumbers,
    showNotification,
    awardLoyaltyPoints,
    redeemLoyaltyPoints,
    updateCustomerTier,
    createSpecialOffer,
    refreshDashboardData,
    startAutoRefresh,
    stopAutoRefresh,
    openModal,
    closeModal,
    validateForm,
    formatDate
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize theme
    initTheme();
    
    // Initialize search and filter
    initSearchAndFilter();
    
    // Convert numbers to Persian on page load
    const numberElements = document.querySelectorAll('.persian-numbers');
    numberElements.forEach(el => {
        if (el.textContent && !el.dataset.converted) {
            el.textContent = toPersianNumbers(el.textContent);
            el.dataset.converted = 'true';
        }
    });
    
    // Add click handlers for modal triggers
    document.addEventListener('click', function(e) {
        if (e.target.matches('[data-modal-open]')) {
            const modalId = e.target.dataset.modalOpen;
            openModal(modalId);
        }
        
        if (e.target.matches('[data-modal-close]')) {
            const modalId = e.target.dataset.modalClose;
            closeModal(modalId);
        }
    });
    
    // Handle escape key for modals
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const openModals = document.querySelectorAll('.modal[style*="block"]');
            openModals.forEach(modal => {
                modal.style.display = 'none';
            });
            document.body.classList.remove('overflow-hidden');
        }
    });
    
    console.log('Customer Loyalty JavaScript initialized');
});