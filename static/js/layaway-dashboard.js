/**
 * Layaway Dashboard JavaScript
 * Handles dashboard interactions and real-time updates
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeLayawayDashboard();
});

function initializeLayawayDashboard() {
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize auto-refresh
    initializeAutoRefresh();
    
    // Initialize search and filters
    initializeFilters();
    
    // Initialize progress animations
    initializeProgressAnimations();
    
    // Initialize theme-aware components
    initializeThemeComponents();
}

function initializeTooltips() {
    // Initialize Bootstrap tooltips for all elements with data-toggle="tooltip"
    if (typeof $ !== 'undefined' && $.fn.tooltip) {
        $('[data-toggle="tooltip"]').tooltip();
    }
}

function initializeAutoRefresh() {
    // Auto-refresh dashboard data every 5 minutes
    setInterval(function() {
        refreshDashboardData();
    }, 5 * 60 * 1000); // 5 minutes
}

function refreshDashboardData() {
    // Refresh summary cards
    fetch(window.location.href, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.text())
    .then(html => {
        // Parse the response and update specific sections
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Update summary cards
        const summaryCards = doc.querySelector('.summary-cards');
        if (summaryCards) {
            document.querySelector('.summary-cards').innerHTML = summaryCards.innerHTML;
        }
        
        // Update active plans table
        const activePlansTable = doc.querySelector('.card .table-responsive');
        if (activePlansTable) {
            const currentTable = document.querySelector('.card .table-responsive');
            if (currentTable) {
                currentTable.innerHTML = activePlansTable.innerHTML;
            }
        }
        
        // Re-initialize progress animations
        initializeProgressAnimations();
        
        console.log('Dashboard data refreshed');
    })
    .catch(error => {
        console.error('Error refreshing dashboard data:', error);
    });
}

function initializeFilters() {
    // Quick filter buttons
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            const filter = this.dataset.filter;
            applyQuickFilter(filter);
        });
    });
    
    // Search functionality
    const searchInput = document.getElementById('planSearch');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                filterPlans(this.value);
            }, 300);
        });
    }
}

function applyQuickFilter(filter) {
    const rows = document.querySelectorAll('.active-plans tbody tr');
    
    rows.forEach(row => {
        let show = true;
        
        switch (filter) {
            case 'overdue':
                show = row.querySelector('.badge-danger') !== null;
                break;
            case 'current':
                show = row.querySelector('.badge-success') !== null;
                break;
            case 'all':
            default:
                show = true;
                break;
        }
        
        row.style.display = show ? '' : 'none';
    });
}

function filterPlans(searchTerm) {
    const rows = document.querySelectorAll('.active-plans tbody tr');
    const term = searchTerm.toLowerCase();
    
    rows.forEach(row => {
        const planNumber = row.querySelector('.plan-number')?.textContent.toLowerCase() || '';
        const customerName = row.cells[1]?.textContent.toLowerCase() || '';
        const itemName = row.cells[2]?.textContent.toLowerCase() || '';
        
        const matches = planNumber.includes(term) || 
                       customerName.includes(term) || 
                       itemName.includes(term);
        
        row.style.display = matches ? '' : 'none';
    });
}

function initializeProgressAnimations() {
    // Animate progress bars
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        const width = bar.style.width;
        bar.style.width = '0%';
        
        setTimeout(() => {
            bar.style.transition = 'width 1s ease-in-out';
            bar.style.width = width;
        }, 100);
    });
    
    // Animate summary card numbers
    animateNumbers();
}

function animateNumbers() {
    const numberElements = document.querySelectorAll('.summary-card h3');
    
    numberElements.forEach(element => {
        const finalNumber = parseInt(element.textContent.replace(/[^\d]/g, ''));
        if (isNaN(finalNumber)) return;
        
        let currentNumber = 0;
        const increment = finalNumber / 50; // 50 steps
        const timer = setInterval(() => {
            currentNumber += increment;
            if (currentNumber >= finalNumber) {
                currentNumber = finalNumber;
                clearInterval(timer);
            }
            
            // Format number with Persian numerals if needed
            const formattedNumber = formatPersianNumber(Math.floor(currentNumber));
            element.textContent = formattedNumber;
        }, 20);
    });
}

function formatPersianNumber(number) {
    // Convert to Persian numerals
    const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
    return number.toString().replace(/\d/g, digit => persianDigits[digit]);
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
                } else {
                    removeDarkModeEffects();
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
    // Add neon glow effects to cards
    const summaryCards = document.querySelectorAll('.summary-card');
    summaryCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.animation = 'neonPulse 2s ease-in-out infinite';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.animation = '';
        });
    });
    
    // Add glassmorphism effects
    addGlassmorphismEffects();
}

function removeDarkModeEffects() {
    // Remove dark mode specific effects
    const summaryCards = document.querySelectorAll('.summary-card');
    summaryCards.forEach(card => {
        card.style.animation = '';
        card.removeEventListener('mouseenter', null);
        card.removeEventListener('mouseleave', null);
    });
}

function addGlassmorphismEffects() {
    // Add glassmorphism backdrop effects for dark mode
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        if (!card.classList.contains('glass-effect')) {
            card.classList.add('glass-effect');
        }
    });
}

// Utility functions for AJAX operations
function sendReminder(reminderId) {
    return fetch('/customers/layaway/ajax/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCsrfToken()
        },
        body: new URLSearchParams({
            action: 'send_reminder',
            reminder_id: reminderId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('یادآوری با موفقیت ارسال شد', 'success');
        } else {
            showNotification(data.error || 'خطا در ارسال یادآوری', 'error');
        }
        return data;
    })
    .catch(error => {
        console.error('Error sending reminder:', error);
        showNotification('خطا در ارسال یادآوری', 'error');
    });
}

function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
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
window.LayawayDashboard = {
    refreshData: refreshDashboardData,
    sendReminder: sendReminder,
    showNotification: showNotification,
    formatPersianNumber: formatPersianNumber
};

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .notification-toast {
        animation: slideInRight 0.3s ease-out;
    }
`;
document.head.appendChild(style);