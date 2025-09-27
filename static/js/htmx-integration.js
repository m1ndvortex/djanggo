/**
 * HTMX Integration for ZARGAR Jewelry SaaS Platform
 * Provides seamless server-side rendering updates with Persian RTL support
 */

// HTMX Configuration and Extensions
document.addEventListener('DOMContentLoaded', function() {
    // Configure HTMX
    htmx.config.globalViewTransitions = true;
    htmx.config.useTemplateFragments = true;
    htmx.config.refreshOnHistoryMiss = true;
    
    // Set default headers
    htmx.config.requestClass = 'htmx-request';
    htmx.config.addedClass = 'htmx-added';
    htmx.config.settlingClass = 'htmx-settling';
    htmx.config.swappingClass = 'htmx-swapping';
    
    // Persian-specific configurations
    htmx.config.defaultSwapStyle = 'innerHTML';
    htmx.config.defaultSwapDelay = 0;
    htmx.config.defaultSettleDelay = 20;
});

// HTMX Event Handlers for Persian UI
document.body.addEventListener('htmx:configRequest', function(evt) {
    // Add CSRF token to all requests
    evt.detail.headers['X-CSRFToken'] = window.zargarConfig?.csrfToken || '';
    
    // Add Persian locale header
    evt.detail.headers['Accept-Language'] = 'fa';
    
    // Add current theme to requests
    evt.detail.headers['X-Theme'] = Alpine.store('zargar')?.theme || 'light';
});

document.body.addEventListener('htmx:beforeRequest', function(evt) {
    // Show loading indicator
    const target = evt.detail.target;
    if (target) {
        target.classList.add('htmx-loading');
        
        // Add Persian loading text
        const loadingText = target.getAttribute('data-loading-text') || 'در حال بارگذاری...';
        target.setAttribute('data-original-content', target.innerHTML);
        
        if (target.tagName === 'BUTTON') {
            target.innerHTML = `
                <div class="flex items-center justify-center">
                    <svg class="animate-spin -ml-1 mr-3 h-4 w-4 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    ${loadingText}
                </div>
            `;
            target.disabled = true;
        }
    }
});

document.body.addEventListener('htmx:afterRequest', function(evt) {
    // Hide loading indicator
    const target = evt.detail.target;
    if (target) {
        target.classList.remove('htmx-loading');
        
        if (target.tagName === 'BUTTON') {
            const originalContent = target.getAttribute('data-original-content');
            if (originalContent) {
                target.innerHTML = originalContent;
                target.removeAttribute('data-original-content');
            }
            target.disabled = false;
        }
    }
    
    // Handle response status
    if (evt.detail.xhr.status >= 400) {
        handleHTMXError(evt);
    }
});

document.body.addEventListener('htmx:afterSwap', function(evt) {
    // Re-initialize Persian components after content swap
    initializePersianComponents(evt.detail.target);
    
    // Re-initialize Alpine.js components
    if (window.Alpine) {
        Alpine.initTree(evt.detail.target);
    }
    
    // Apply theme to new content
    applyThemeToNewContent(evt.detail.target);
    
    // Initialize Flowbite components
    if (window.Flowbite) {
        window.Flowbite.init();
    }
});

document.body.addEventListener('htmx:responseError', function(evt) {
    handleHTMXError(evt);
});

document.body.addEventListener('htmx:sendError', function(evt) {
    handleHTMXError(evt);
});

// Error handling
function handleHTMXError(evt) {
    const xhr = evt.detail.xhr;
    let message = 'خطایی رخ داده است';
    
    if (xhr.status === 0) {
        message = 'خطا در اتصال به سرور';
    } else if (xhr.status === 403) {
        message = 'دسترسی غیرمجاز';
    } else if (xhr.status === 404) {
        message = 'صفحه مورد نظر یافت نشد';
    } else if (xhr.status === 500) {
        message = 'خطای داخلی سرور';
    } else if (xhr.status >= 400) {
        try {
            const response = JSON.parse(xhr.responseText);
            message = response.message || response.error || message;
        } catch (e) {
            // Use default message
        }
    }
    
    // Show error notification
    if (Alpine.store('zargar')) {
        Alpine.store('zargar').showNotification(message, 'error');
    }
}

// Initialize Persian components in new content
function initializePersianComponents(container) {
    // Persian number formatting
    const numberElements = container.querySelectorAll('.persian-numbers, [data-persian-numbers]');
    numberElements.forEach(element => {
        if (window.PersianNumbers) {
            element.textContent = window.PersianNumbers.toPersian(element.textContent);
        }
    });
    
    // Persian date formatting
    const dateElements = container.querySelectorAll('[data-persian-date]');
    dateElements.forEach(element => {
        if (window.PersianDate) {
            const date = element.getAttribute('data-persian-date');
            element.textContent = window.PersianDate.format(date);
        }
    });
    
    // RTL text direction
    const rtlElements = container.querySelectorAll('[data-rtl]');
    rtlElements.forEach(element => {
        element.style.direction = 'rtl';
        element.style.textAlign = 'right';
    });
}

// Apply theme to new content
function applyThemeToNewContent(container) {
    const isDark = Alpine.store('zargar')?.theme === 'dark';
    
    if (isDark) {
        container.classList.add('dark');
    } else {
        container.classList.remove('dark');
    }
    
    // Apply theme-specific classes to elements
    const themeElements = container.querySelectorAll('[data-theme-light], [data-theme-dark]');
    themeElements.forEach(element => {
        const lightClasses = element.getAttribute('data-theme-light');
        const darkClasses = element.getAttribute('data-theme-dark');
        
        if (isDark && darkClasses) {
            element.className = darkClasses;
        } else if (!isDark && lightClasses) {
            element.className = lightClasses;
        }
    });
}

// HTMX Extensions for Persian UI

// Persian Form Validation Extension
htmx.defineExtension('persian-validation', {
    onEvent: function(name, evt) {
        if (name === 'htmx:beforeRequest') {
            const form = evt.detail.elt.closest('form');
            if (form && form.hasAttribute('data-persian-validation')) {
                if (!validatePersianForm(form)) {
                    evt.preventDefault();
                    return false;
                }
            }
        }
    }
});

function validatePersianForm(form) {
    let isValid = true;
    const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
    
    inputs.forEach(input => {
        const value = input.value.trim();
        const errorElement = form.querySelector(`[data-error-for="${input.name}"]`);
        
        if (!value) {
            isValid = false;
            input.classList.add('border-red-500', 'dark:border-red-400');
            
            if (errorElement) {
                errorElement.textContent = 'این فیلد الزامی است';
                errorElement.classList.remove('hidden');
            }
        } else {
            input.classList.remove('border-red-500', 'dark:border-red-400');
            
            if (errorElement) {
                errorElement.classList.add('hidden');
            }
        }
    });
    
    return isValid;
}

// Persian Number Formatting Extension
htmx.defineExtension('persian-numbers', {
    onEvent: function(name, evt) {
        if (name === 'htmx:afterSwap') {
            const container = evt.detail.target;
            formatPersianNumbers(container);
        }
    }
});

function formatPersianNumbers(container) {
    const elements = container.querySelectorAll('[data-format="persian-number"]');
    elements.forEach(element => {
        const value = element.textContent || element.value;
        if (value && window.PersianNumbers) {
            const formatted = window.PersianNumbers.toPersian(value);
            if (element.tagName === 'INPUT') {
                element.value = formatted;
            } else {
                element.textContent = formatted;
            }
        }
    });
}

// Auto-refresh Extension for Real-time Data
htmx.defineExtension('auto-refresh', {
    onEvent: function(name, evt) {
        if (name === 'htmx:afterSwap') {
            const element = evt.detail.target;
            const interval = element.getAttribute('data-refresh-interval');
            
            if (interval) {
                const intervalMs = parseInt(interval) * 1000;
                
                // Clear existing interval
                if (element._refreshInterval) {
                    clearInterval(element._refreshInterval);
                }
                
                // Set new interval
                element._refreshInterval = setInterval(() => {
                    if (document.contains(element)) {
                        htmx.trigger(element, 'refresh');
                    } else {
                        clearInterval(element._refreshInterval);
                    }
                }, intervalMs);
            }
        }
    }
});

// HTMX Helper Functions

// Trigger HTMX request programmatically
window.htmxRequest = function(method, url, data = {}, target = null) {
    const config = {
        method: method.toUpperCase(),
        url: url,
        headers: {
            'X-CSRFToken': window.zargarConfig?.csrfToken || '',
            'Content-Type': 'application/json',
            'Accept': 'text/html',
            'X-Theme': Alpine.store('zargar')?.theme || 'light'
        }
    };
    
    if (method.toUpperCase() !== 'GET' && Object.keys(data).length > 0) {
        config.body = JSON.stringify(data);
    }
    
    if (target) {
        config.target = target;
        config.swap = 'innerHTML';
    }
    
    return htmx.ajax(config.method, config.url, config);
};

// Update element content via HTMX
window.htmxUpdate = function(selector, url, data = {}) {
    const element = document.querySelector(selector);
    if (element) {
        return window.htmxRequest('GET', url, data, element);
    }
};

// Submit form via HTMX
window.htmxSubmitForm = function(formSelector, successCallback = null) {
    const form = document.querySelector(formSelector);
    if (form) {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        
        return window.htmxRequest('POST', form.action, data, form)
            .then(response => {
                if (successCallback) {
                    successCallback(response);
                }
            });
    }
};

// Refresh specific element
window.htmxRefresh = function(selector) {
    const element = document.querySelector(selector);
    if (element) {
        const url = element.getAttribute('hx-get') || 
                   element.getAttribute('hx-post') || 
                   element.getAttribute('data-refresh-url');
        
        if (url) {
            return window.htmxUpdate(selector, url);
        }
    }
};

// HTMX Indicators for Persian UI
document.addEventListener('DOMContentLoaded', function() {
    // Add global loading indicator
    const loadingIndicator = document.createElement('div');
    loadingIndicator.id = 'htmx-global-indicator';
    loadingIndicator.className = 'htmx-indicator fixed top-0 left-0 right-0 z-50 h-1 bg-gradient-to-r from-blue-500 to-purple-500 transform scale-x-0 origin-left transition-transform duration-300';
    loadingIndicator.innerHTML = '<div class="h-full bg-gradient-to-r from-blue-400 to-purple-400 animate-pulse"></div>';
    document.body.appendChild(loadingIndicator);
    
    // Show/hide global indicator
    document.body.addEventListener('htmx:beforeRequest', function() {
        loadingIndicator.style.transform = 'scaleX(1)';
    });
    
    document.body.addEventListener('htmx:afterRequest', function() {
        setTimeout(() => {
            loadingIndicator.style.transform = 'scaleX(0)';
        }, 100);
    });
});

// Persian-specific HTMX attributes
document.addEventListener('DOMContentLoaded', function() {
    // Auto-setup Persian forms
    const persianForms = document.querySelectorAll('form[data-persian]');
    persianForms.forEach(form => {
        if (!form.hasAttribute('hx-ext')) {
            form.setAttribute('hx-ext', 'persian-validation');
        }
    });
    
    // Auto-setup Persian number elements
    const numberElements = document.querySelectorAll('[data-persian-numbers]');
    numberElements.forEach(element => {
        if (!element.hasAttribute('hx-ext')) {
            element.setAttribute('hx-ext', 'persian-numbers');
        }
    });
    
    // Auto-setup refresh elements
    const refreshElements = document.querySelectorAll('[data-auto-refresh]');
    refreshElements.forEach(element => {
        if (!element.hasAttribute('hx-ext')) {
            element.setAttribute('hx-ext', 'auto-refresh');
        }
        
        const interval = element.getAttribute('data-auto-refresh');
        if (interval) {
            element.setAttribute('data-refresh-interval', interval);
        }
    });
});

// Export for global use
window.HTMXPersian = {
    request: window.htmxRequest,
    update: window.htmxUpdate,
    submitForm: window.htmxSubmitForm,
    refresh: window.htmxRefresh,
    validateForm: validatePersianForm,
    formatNumbers: formatPersianNumbers,
    initializeComponents: initializePersianComponents
};