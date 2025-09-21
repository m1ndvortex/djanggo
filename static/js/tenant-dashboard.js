/**
 * Tenant Dashboard JavaScript with Dual Theme Support
 * Handles real-time updates, Persian formatting, and cybersecurity theme animations
 */

// Persian number conversion
const persianNumbers = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
const englishNumbers = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];

function toPersianNumbers(str) {
    if (typeof str !== 'string') {
        str = String(str);
    }
    
    for (let i = 0; i < englishNumbers.length; i++) {
        str = str.replace(new RegExp(englishNumbers[i], 'g'), persianNumbers[i]);
    }
    return str;
}

function toEnglishNumbers(str) {
    if (typeof str !== 'string') {
        str = String(str);
    }
    
    for (let i = 0; i < persianNumbers.length; i++) {
        str = str.replace(new RegExp(persianNumbers[i], 'g'), englishNumbers[i]);
    }
    return str;
}

// Currency formatting
function formatCurrency(amount) {
    if (!amount || isNaN(amount)) return '۰ تومان';
    
    const formatted = new Intl.NumberFormat('fa-IR').format(amount);
    return toPersianNumbers(formatted) + ' تومان';
}

function formatNumber(num) {
    if (!num || isNaN(num)) return '۰';
    
    const formatted = new Intl.NumberFormat('fa-IR').format(num);
    return toPersianNumbers(formatted);
}

// Persian date and time
function getCurrentPersianTime() {
    const now = new Date();
    const options = {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZone: 'Asia/Tehran'
    };
    
    const timeStr = now.toLocaleTimeString('fa-IR', options);
    return toPersianNumbers(timeStr);
}

// Persian calendar utilities
function getCurrentPersianDate() {
    const now = new Date();
    
    // Simple Persian date conversion (approximation)
    // In production, use a proper Persian calendar library
    const gregorianYear = now.getFullYear();
    const gregorianMonth = now.getMonth() + 1;
    const gregorianDay = now.getDate();
    
    // Approximate conversion to Persian calendar
    let persianYear = gregorianYear - 621;
    let persianMonth = gregorianMonth;
    let persianDay = gregorianDay;
    
    // Adjust for Persian calendar differences
    if (gregorianMonth <= 3) {
        persianYear--;
        persianMonth += 9;
    } else {
        persianMonth -= 3;
    }
    
    // Format with Persian numbers
    const formattedYear = toPersianNumbers(persianYear.toString());
    const formattedMonth = toPersianNumbers(persianMonth.toString().padStart(2, '0'));
    const formattedDay = toPersianNumbers(persianDay.toString().padStart(2, '0'));
    
    return `${formattedYear}/${formattedMonth}/${formattedDay}`;
}

function updatePersianDate() {
    const dateElement = document.getElementById('persian-date-display');
    if (dateElement) {
        dateElement.textContent = getCurrentPersianDate();
    }
}

function updatePersianTime() {
    const timeElement = document.getElementById('current-persian-time');
    if (timeElement) {
        timeElement.textContent = getCurrentPersianTime();
    }
}

// Gold Price Widget Alpine.js Component
function goldPriceWidget() {
    return {
        goldPrices: {
            '18k': 3500000,
            '21k': 4083333,
            '24k': 4666666
        },
        lastUpdated: 'چند لحظه پیش',
        isLoading: false,
        
        init() {
            this.fetchGoldPrices();
            // Update prices every 5 minutes
            setInterval(() => {
                this.fetchGoldPrices();
            }, 300000);
        },
        
        async fetchGoldPrices() {
            this.isLoading = true;
            
            try {
                const response = await fetch('/api/gold-prices/', {
                    headers: {
                        'X-CSRFToken': window.zargarConfig?.csrfToken || '',
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    this.goldPrices = {
                        '18k': data.prices['18k'] || this.goldPrices['18k'],
                        '21k': data.prices['21k'] || this.goldPrices['21k'],
                        '24k': data.prices['24k'] || this.goldPrices['24k']
                    };
                    this.lastUpdated = 'چند لحظه پیش';
                }
            } catch (error) {
                console.error('Error fetching gold prices:', error);
            } finally {
                this.isLoading = false;
            }
        },
        
        formatCurrency(amount) {
            return formatCurrency(amount);
        }
    };
}

// Main Tenant Dashboard Alpine.js Component
function tenantDashboard() {
    return {
        // Dashboard state
        isLoading: false,
        autoRefresh: true,
        refreshInterval: 300000, // 5 minutes
        lastRefresh: null,
        
        // Metrics data
        metrics: {
            sales: {},
            customers: {},
            inventory: {},
            installments: {}
        },
        
        // Notifications
        notifications: [],
        
        init() {
            console.log('Initializing Tenant Dashboard...');
            
            // Initialize Persian time and date updates
            this.startTimeUpdates();
            this.startDateUpdates();
            
            // Initialize auto-refresh
            if (this.autoRefresh) {
                this.startAutoRefresh();
            }
            
            // Initialize Persian number formatting
            this.formatPersianNumbers();
            
            // Initialize cybersecurity animations if in dark mode
            const isDarkMode = document.documentElement.classList.contains('dark') || 
                              document.body.classList.contains('dark') ||
                              localStorage.getItem('theme') === 'dark';
            
            if (isDarkMode) {
                this.initCyberAnimations();
            }
            
            // Listen for theme changes
            document.addEventListener('themeChanged', (event) => {
                if (event.detail.theme === 'dark') {
                    this.initCyberAnimations();
                } else {
                    this.removeCyberAnimations();
                }
            });
            
            // Initialize theme detection
            this.detectThemeChanges();
        },
        
        startTimeUpdates() {
            updatePersianTime();
            setInterval(updatePersianTime, 1000);
        },
        
        startDateUpdates() {
            updatePersianDate();
            // Update date every minute
            setInterval(updatePersianDate, 60000);
        },
        
        startAutoRefresh() {
            setInterval(() => {
                this.refreshDashboard();
            }, this.refreshInterval);
        },
        
        async refreshDashboard() {
            if (this.isLoading) return;
            
            this.isLoading = true;
            
            try {
                const response = await fetch('/api/dashboard/refresh/', {
                    headers: {
                        'X-CSRFToken': window.zargarConfig?.csrfToken || '',
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    this.updateMetrics(data);
                    this.lastRefresh = new Date();
                    this.showNotification('داده‌ها به‌روزرسانی شد', 'success');
                }
            } catch (error) {
                console.error('Error refreshing dashboard:', error);
                this.showNotification('خطا در به‌روزرسانی داده‌ها', 'error');
            } finally {
                this.isLoading = false;
            }
        },
        
        updateMetrics(data) {
            // Update metrics with animation
            this.animateMetricUpdate('sales', data.sales_metrics);
            this.animateMetricUpdate('customers', data.customer_metrics);
            this.animateMetricUpdate('inventory', data.inventory_metrics);
            this.animateMetricUpdate('installments', data.gold_installment_metrics);
        },
        
        animateMetricUpdate(type, newData) {
            const cards = document.querySelectorAll(`[data-metric="${type}"]`);
            
            cards.forEach(card => {
                card.style.transform = 'scale(1.02)';
                card.style.transition = 'transform 0.3s ease';
                
                setTimeout(() => {
                    card.style.transform = 'scale(1)';
                    // Update the data here
                    this.metrics[type] = newData;
                }, 300);
            });
        },
        
        formatPersianNumbers() {
            const elements = document.querySelectorAll('.persian-numbers');
            elements.forEach(element => {
                if (element.textContent) {
                    element.textContent = toPersianNumbers(element.textContent);
                }
            });
        },
        
        initCyberAnimations() {
            // Initialize cybersecurity theme animations
            console.log('Initializing cybersecurity animations...');
            
            this.initCardAnimations();
            this.initGlowEffects();
            this.initNeonBorders();
            this.initGradientEffects();
        },
        
        removeCyberAnimations() {
            // Remove cybersecurity animations when switching to light mode
            const animatedElements = document.querySelectorAll('[style*="animation"]');
            animatedElements.forEach(el => {
                el.style.animation = '';
            });
        },
        
        detectThemeChanges() {
            // Watch for theme changes using MutationObserver
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                        const isDark = document.documentElement.classList.contains('dark') ||
                                      document.body.classList.contains('dark');
                        
                        if (isDark) {
                            setTimeout(() => this.initCyberAnimations(), 100);
                        } else {
                            this.removeCyberAnimations();
                        }
                    }
                });
            });
            
            observer.observe(document.documentElement, {
                attributes: true,
                attributeFilter: ['class']
            });
            
            observer.observe(document.body, {
                attributes: true,
                attributeFilter: ['class']
            });
        },
        
        initCardAnimations() {
            const cards = document.querySelectorAll('.cyber-metric-card, .cyber-gold-price-card, .cyber-insight-card');
            
            cards.forEach((card, index) => {
                // Stagger animation delays
                card.style.animationDelay = `${index * 0.1}s`;
                
                // Add hover animations
                card.addEventListener('mouseenter', () => {
                    card.style.transform = 'translateY(-4px) scale(1.02)';
                    card.style.boxShadow = '0 20px 60px rgba(0, 0, 0, 0.8), 0 0 40px rgba(0, 212, 255, 0.2)';
                });
                
                card.addEventListener('mouseleave', () => {
                    card.style.transform = 'translateY(0) scale(1)';
                    card.style.boxShadow = '0 12px 40px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.03)';
                });
            });
        },
        
        initGlowEffects() {
            const glowElements = document.querySelectorAll('.cyber-number-glow, .cyber-glow-text');
            
            glowElements.forEach(element => {
                // Add pulsing glow effect
                element.style.animation = 'cyber-glow 3s ease-in-out infinite';
            });
        },
        
        initNeonBorders() {
            const neonElements = document.querySelectorAll('.cyber-metric-card, .cyber-gold-price-card');
            
            neonElements.forEach(element => {
                // Add neon border class for CSS animation
                element.classList.add('neon-border-gradient');
            });
        },
        
        initGradientEffects() {
            // Initialize inventory cards with gradient effects
            const inventoryCards = document.querySelectorAll('.cyber-metric-card');
            
            inventoryCards.forEach((card, index) => {
                // Add staggered hover effects
                card.addEventListener('mouseenter', () => {
                    card.style.transform = 'translateY(-4px) scale(1.02)';
                    card.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
                });
                
                card.addEventListener('mouseleave', () => {
                    card.style.transform = 'translateY(0) scale(1)';
                });
            });
            
            // Initialize gold price widget with special effects
            const goldPriceCard = document.querySelector('.cyber-gold-price-card');
            if (goldPriceCard) {
                goldPriceCard.addEventListener('mouseenter', () => {
                    goldPriceCard.style.boxShadow = '0 20px 60px rgba(255, 184, 0, 0.3), 0 0 40px rgba(255, 184, 0, 0.2)';
                });
                
                goldPriceCard.addEventListener('mouseleave', () => {
                    goldPriceCard.style.boxShadow = '0 12px 40px rgba(0, 0, 0, 0.6), 0 0 30px rgba(255, 184, 0, 0.1)';
                });
            }
        },
        
        showNotification(message, type = 'info', duration = 5000) {
            const notification = {
                id: Date.now(),
                message,
                type,
                show: true
            };
            
            this.notifications.push(notification);
            
            setTimeout(() => {
                notification.show = false;
                setTimeout(() => {
                    this.notifications = this.notifications.filter(n => n.id !== notification.id);
                }, 300);
            }, duration);
        },
        
        // Utility methods for template
        formatCurrency(amount) {
            return formatCurrency(amount);
        },
        
        formatNumber(num) {
            return formatNumber(num);
        },
        
        formatWeight(grams, unit = 'gram') {
            if (!grams || isNaN(grams)) return '۰ گرم';
            
            if (unit === 'gram') {
                return formatNumber(grams) + ' گرم';
            } else if (unit === 'mesghal') {
                const mesghal = grams / 4.608; // 1 مثقال = 4.608 گرم
                return formatNumber(mesghal.toFixed(2)) + ' مثقال';
            }
            
            return formatNumber(grams) + ' گرم';
        },
        
        getRelativeTime(timestamp) {
            if (!timestamp) return 'نامشخص';
            
            const now = new Date();
            const time = new Date(timestamp);
            const diffInSeconds = Math.floor((now - time) / 1000);
            
            if (diffInSeconds < 60) {
                return 'چند لحظه پیش';
            } else if (diffInSeconds < 3600) {
                const minutes = Math.floor(diffInSeconds / 60);
                return toPersianNumbers(minutes.toString()) + ' دقیقه پیش';
            } else if (diffInSeconds < 86400) {
                const hours = Math.floor(diffInSeconds / 3600);
                return toPersianNumbers(hours.toString()) + ' ساعت پیش';
            } else {
                const days = Math.floor(diffInSeconds / 86400);
                return toPersianNumbers(days.toString()) + ' روز پیش';
            }
        }
    };
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Format all Persian numbers on page load
    const persianNumberElements = document.querySelectorAll('.persian-numbers');
    persianNumberElements.forEach(element => {
        if (element.textContent) {
            element.textContent = toPersianNumbers(element.textContent);
        }
    });
    
    // Initialize time display
    updatePersianTime();
    
    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Add loading states to buttons
    document.querySelectorAll('button, .btn').forEach(button => {
        button.addEventListener('click', function() {
            if (!this.disabled) {
                this.style.opacity = '0.7';
                setTimeout(() => {
                    this.style.opacity = '1';
                }, 1000);
            }
        });
    });
});

// Export functions for global use
window.tenantDashboard = tenantDashboard;
window.goldPriceWidget = goldPriceWidget;
window.formatCurrency = formatCurrency;
window.formatNumber = formatNumber;
window.toPersianNumbers = toPersianNumbers;
window.toEnglishNumbers = toEnglishNumbers;

// Handle theme changes
document.addEventListener('themeChanged', function(event) {
    const isDark = event.detail.theme === 'dark';
    
    if (isDark) {
        // Initialize cybersecurity animations
        setTimeout(() => {
            const dashboard = window.tenantDashboardInstance;
            if (dashboard && dashboard.initCyberAnimations) {
                dashboard.initCyberAnimations();
            }
        }, 100);
    }
});

// Handle visibility change for performance optimization
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Pause animations and updates when tab is not visible
        const animations = document.querySelectorAll('[style*="animation"]');
        animations.forEach(el => {
            el.style.animationPlayState = 'paused';
        });
    } else {
        // Resume animations when tab becomes visible
        const animations = document.querySelectorAll('[style*="animation"]');
        animations.forEach(el => {
            el.style.animationPlayState = 'running';
        });
    }
});

// Performance monitoring
if ('performance' in window) {
    window.addEventListener('load', function() {
        setTimeout(() => {
            const perfData = performance.getEntriesByType('navigation')[0];
            console.log('Dashboard Load Time:', perfData.loadEventEnd - perfData.loadEventStart, 'ms');
        }, 0);
    });
}