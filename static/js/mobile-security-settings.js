/**
 * Mobile Security & Settings JavaScript
 * Handles mobile navigation, touch interactions, and responsive behavior
 */

class MobileSecuritySettings {
    constructor() {
        this.isMobile = window.innerWidth <= 768;
        this.isTablet = window.innerWidth > 768 && window.innerWidth <= 1024;
        this.sidebarOpen = false;
        this.filterPanelOpen = false;
        this.activeModal = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupMobileNavigation();
        this.setupTouchGestures();
        this.setupResponsiveCharts();
        this.setupMobileModals();
        this.setupMobileToasts();
        this.setupPersianNumberFormatting();
        
        // Update on resize
        window.addEventListener('resize', this.handleResize.bind(this));
    }
    
    setupEventListeners() {
        // Mobile navigation toggle
        document.addEventListener('click', (e) => {
            if (e.target.matches('.mobile-nav-toggle') || e.target.closest('.mobile-nav-toggle')) {
                e.preventDefault();
                this.toggleMobileSidebar();
            }
            
            // Close sidebar when clicking overlay
            if (e.target.matches('.mobile-sidebar-overlay')) {
                this.closeMobileSidebar();
            }
            
            // Filter panel toggle
            if (e.target.matches('.mobile-filter-toggle') || e.target.closest('.mobile-filter-toggle')) {
                e.preventDefault();
                this.toggleFilterPanel();
            }
            
            // Modal close buttons
            if (e.target.matches('.mobile-modal-close') || e.target.closest('.mobile-modal-close')) {
                e.preventDefault();
                this.closeActiveModal();
            }
            
            // Table row actions on mobile
            if (this.isMobile && (e.target.matches('.table-row-action') || e.target.closest('.table-row-action'))) {
                e.preventDefault();
                this.handleTableRowAction(e.target.closest('.table-row-action'));
            }
        });
        
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (this.activeModal) {
                    this.closeActiveModal();
                } else if (this.sidebarOpen) {
                    this.closeMobileSidebar();
                } else if (this.filterPanelOpen) {
                    this.toggleFilterPanel();
                }
            }
        });
        
        // Form submission handling
        document.addEventListener('submit', (e) => {
            if (e.target.matches('.mobile-form')) {
                this.handleMobileFormSubmit(e);
            }
        });
    }
    
    setupMobileNavigation() {
        if (!this.isMobile) return;
        
        // Create mobile navigation toggle if it doesn't exist
        if (!document.querySelector('.mobile-nav-toggle')) {
            this.createMobileNavToggle();
        }
        
        // Create mobile sidebar if it doesn't exist
        if (!document.querySelector('.mobile-sidebar')) {
            this.createMobileSidebar();
        }
        
        // Create overlay
        if (!document.querySelector('.mobile-sidebar-overlay')) {
            this.createSidebarOverlay();
        }
    }
    
    createMobileNavToggle() {
        const toggle = document.createElement('button');
        toggle.className = 'mobile-nav-toggle';
        toggle.innerHTML = `
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
            </svg>
        `;
        toggle.setAttribute('aria-label', 'باز کردن منوی ناوبری');
        document.body.appendChild(toggle);
    }
    
    createMobileSidebar() {
        const sidebar = document.createElement('div');
        sidebar.className = 'mobile-sidebar';
        sidebar.innerHTML = this.generateMobileSidebarContent();
        document.body.appendChild(sidebar);
    }
    
    createSidebarOverlay() {
        const overlay = document.createElement('div');
        overlay.className = 'mobile-sidebar-overlay';
        document.body.appendChild(overlay);
    }
    
    generateMobileSidebarContent() {
        const currentPath = window.location.pathname;
        const menuItems = [
            { href: '/super-panel/', icon: 'home', text: 'داشبورد اصلی' },
            { href: '/super-panel/security/dashboard/', icon: 'shield', text: 'داشبورد امنیت' },
            { href: '/super-panel/security/audit-logs/', icon: 'document-text', text: 'لاگ‌های حسابرسی' },
            { href: '/super-panel/security/security-events/', icon: 'exclamation-triangle', text: 'رویدادهای امنیتی' },
            { href: '/super-panel/security/access-control/', icon: 'key', text: 'کنترل دسترسی' },
            { href: '/super-panel/settings/', icon: 'cog', text: 'تنظیمات سیستم' },
            { href: '/super-panel/settings/security-policies/', icon: 'lock-closed', text: 'سیاست‌های امنیتی' },
            { href: '/super-panel/settings/notifications/', icon: 'bell', text: 'مدیریت اعلان‌ها' },
            { href: '/super-panel/settings/integrations/', icon: 'puzzle', text: 'تنظیمات یکپارچه‌سازی' }
        ];
        
        const sidebarHeader = `
            <div class="flex items-center justify-between mb-6 pb-4 border-b border-gray-200 dark:border-cyber-neon-primary/20">
                <h2 class="text-lg font-semibold text-gray-900 dark:text-cyber-text-primary">منوی ناوبری</h2>
                <button class="mobile-sidebar-close p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-cyber-bg-elevated">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        `;
        
        const menuItemsHtml = menuItems.map(item => `
            <a href="${item.href}" class="mobile-nav-item ${currentPath === item.href ? 'active' : ''}">
                <div class="flex items-center">
                    ${this.getIconSvg(item.icon)}
                    <span class="mr-3">${item.text}</span>
                </div>
            </a>
        `).join('');
        
        return sidebarHeader + menuItemsHtml;
    }
    
    getIconSvg(iconName) {
        const icons = {
            home: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path></svg>',
            shield: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>',
            'document-text': '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>',
            'exclamation-triangle': '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path></svg>',
            key: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"></path></svg>',
            cog: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>',
            'lock-closed': '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>',
            bell: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path></svg>',
            puzzle: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z"></path></svg>'
        };
        return icons[iconName] || icons.cog;
    }
    
    toggleMobileSidebar() {
        this.sidebarOpen = !this.sidebarOpen;
        const sidebar = document.querySelector('.mobile-sidebar');
        const overlay = document.querySelector('.mobile-sidebar-overlay');
        
        if (this.sidebarOpen) {
            sidebar?.classList.add('open');
            overlay?.classList.add('active');
            document.body.style.overflow = 'hidden';
        } else {
            sidebar?.classList.remove('open');
            overlay?.classList.remove('active');
            document.body.style.overflow = '';
        }
    }
    
    closeMobileSidebar() {
        this.sidebarOpen = false;
        const sidebar = document.querySelector('.mobile-sidebar');
        const overlay = document.querySelector('.mobile-sidebar-overlay');
        
        sidebar?.classList.remove('open');
        overlay?.classList.remove('active');
        document.body.style.overflow = '';
    }
    
    toggleFilterPanel() {
        this.filterPanelOpen = !this.filterPanelOpen;
        const panel = document.querySelector('.mobile-filter-panel');
        const toggle = document.querySelector('.mobile-filter-toggle');
        
        if (panel) {
            panel.classList.toggle('open', this.filterPanelOpen);
        }
        
        if (toggle) {
            const icon = toggle.querySelector('svg');
            if (icon) {
                icon.style.transform = this.filterPanelOpen ? 'rotate(180deg)' : 'rotate(0deg)';
            }
        }
    }
    
    setupTouchGestures() {
        if (!this.isMobile) return;
        
        let startX = 0;
        let startY = 0;
        let currentX = 0;
        let currentY = 0;
        
        document.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        }, { passive: true });
        
        document.addEventListener('touchmove', (e) => {
            currentX = e.touches[0].clientX;
            currentY = e.touches[0].clientY;
        }, { passive: true });
        
        document.addEventListener('touchend', (e) => {
            const diffX = startX - currentX;
            const diffY = startY - currentY;
            
            // Swipe right to open sidebar (from left edge)
            if (startX < 50 && diffX < -100 && Math.abs(diffY) < 100) {
                if (!this.sidebarOpen) {
                    this.toggleMobileSidebar();
                }
            }
            
            // Swipe left to close sidebar
            if (this.sidebarOpen && diffX > 100 && Math.abs(diffY) < 100) {
                this.closeMobileSidebar();
            }
        }, { passive: true });
    }
    
    setupResponsiveCharts() {
        // Make charts responsive on mobile
        if (typeof Chart !== 'undefined') {
            Chart.defaults.responsive = true;
            Chart.defaults.maintainAspectRatio = false;
            
            // Update chart options for mobile
            const originalChartOptions = Chart.defaults.plugins.legend;
            if (this.isMobile) {
                Chart.defaults.plugins.legend.position = 'bottom';
                Chart.defaults.plugins.legend.labels.boxWidth = 12;
                Chart.defaults.plugins.legend.labels.fontSize = 12;
            }
        }
    }
    
    setupMobileModals() {
        // Convert desktop modals to mobile-friendly bottom sheets
        document.querySelectorAll('.modal').forEach(modal => {
            if (this.isMobile) {
                modal.classList.add('mobile-modal');
                this.convertToMobileModal(modal);
            }
        });
    }
    
    convertToMobileModal(modal) {
        const content = modal.querySelector('.modal-content');
        if (content) {
            content.classList.add('mobile-modal-content');
            
            // Add mobile modal header if not exists
            if (!content.querySelector('.mobile-modal-header')) {
                const header = document.createElement('div');
                header.className = 'mobile-modal-header';
                header.innerHTML = `
                    <h3 class="mobile-modal-title">${modal.getAttribute('data-title') || 'جزئیات'}</h3>
                    <button class="mobile-modal-close">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                `;
                content.insertBefore(header, content.firstChild);
            }
        }
    }
    
    openMobileModal(modalId, title = '') {
        const modal = document.getElementById(modalId);
        if (modal) {
            this.activeModal = modal;
            modal.classList.add('open');
            
            if (title) {
                const titleElement = modal.querySelector('.mobile-modal-title');
                if (titleElement) {
                    titleElement.textContent = title;
                }
            }
            
            document.body.style.overflow = 'hidden';
        }
    }
    
    closeActiveModal() {
        if (this.activeModal) {
            this.activeModal.classList.remove('open');
            this.activeModal = null;
            document.body.style.overflow = '';
        }
    }
    
    setupMobileToasts() {
        // Create toast container if it doesn't exist
        if (!document.querySelector('.mobile-toast-container')) {
            const container = document.createElement('div');
            container.className = 'mobile-toast-container';
            document.body.appendChild(container);
        }
    }
    
    showMobileToast(message, type = 'info', duration = 3000) {
        const container = document.querySelector('.mobile-toast-container');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `mobile-toast mobile-toast-${type}`;
        
        const iconMap = {
            success: '<svg class="mobile-toast-icon text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>',
            error: '<svg class="mobile-toast-icon text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>',
            warning: '<svg class="mobile-toast-icon text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path></svg>',
            info: '<svg class="mobile-toast-icon text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>'
        };
        
        toast.innerHTML = `
            <div class="mobile-toast-content">
                ${iconMap[type] || iconMap.info}
                <span class="mobile-toast-message">${message}</span>
            </div>
        `;
        
        container.appendChild(toast);
        
        // Show toast
        setTimeout(() => toast.classList.add('show'), 100);
        
        // Hide and remove toast
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => container.removeChild(toast), 300);
        }, duration);
    }
    
    setupPersianNumberFormatting() {
        // Format all numbers to Persian
        document.querySelectorAll('.persian-numbers').forEach(element => {
            const text = element.textContent;
            element.textContent = this.formatPersianNumbers(text);
        });
        
        // Format dates to Persian
        document.querySelectorAll('[data-persian-date]').forEach(element => {
            const date = new Date(element.getAttribute('data-persian-date'));
            element.textContent = this.formatPersianDate(date);
        });
    }
    
    formatPersianNumbers(text) {
        const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
        return text.replace(/\d/g, (digit) => persianDigits[digit]);
    }
    
    formatPersianDate(date) {
        // Simple Persian date formatting (you might want to use a proper Persian calendar library)
        const persianMonths = [
            'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
            'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
        ];
        
        // This is a simplified conversion - in production, use a proper Persian calendar library
        const gregorianMonth = date.getMonth();
        const day = this.formatPersianNumbers(date.getDate().toString());
        const year = this.formatPersianNumbers((date.getFullYear() - 621).toString());
        
        return `${day} ${persianMonths[gregorianMonth]} ${year}`;
    }
    
    handleTableRowAction(actionElement) {
        const action = actionElement.getAttribute('data-action');
        const rowId = actionElement.getAttribute('data-row-id');
        
        switch (action) {
            case 'view-details':
                this.openMobileModal('details-modal', 'جزئیات');
                break;
            case 'edit':
                this.openMobileModal('edit-modal', 'ویرایش');
                break;
            case 'delete':
                if (confirm('آیا مطمئن هستید؟')) {
                    this.handleDelete(rowId);
                }
                break;
        }
    }
    
    handleMobileFormSubmit(event) {
        event.preventDefault();
        
        const form = event.target;
        const submitButton = form.querySelector('button[type="submit"]');
        
        // Show loading state
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = `
                <svg class="animate-spin w-4 h-4 ml-2" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                در حال پردازش...
            `;
        }
        
        // Submit form via fetch
        const formData = new FormData(form);
        fetch(form.action, {
            method: form.method,
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showMobileToast(data.message || 'عملیات با موفقیت انجام شد', 'success');
                if (data.redirect) {
                    setTimeout(() => window.location.href = data.redirect, 1000);
                }
            } else {
                this.showMobileToast(data.error || 'خطایی رخ داد', 'error');
            }
        })
        .catch(error => {
            this.showMobileToast('خطای شبکه', 'error');
        })
        .finally(() => {
            // Reset button state
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = submitButton.getAttribute('data-original-text') || 'ارسال';
            }
        });
    }
    
    handleResize() {
        const newIsMobile = window.innerWidth <= 768;
        const newIsTablet = window.innerWidth > 768 && window.innerWidth <= 1024;
        
        if (newIsMobile !== this.isMobile) {
            this.isMobile = newIsMobile;
            this.isTablet = newIsTablet;
            
            if (this.isMobile) {
                this.setupMobileNavigation();
            } else {
                this.closeMobileSidebar();
            }
        }
    }
    
    // Utility methods for external use
    showLoading(message = 'در حال بارگذاری...') {
        const loading = document.createElement('div');
        loading.className = 'mobile-loading';
        loading.innerHTML = `
            <div class="mobile-loading-content">
                <div class="mobile-loading-spinner"></div>
                <p class="text-gray-900 dark:text-cyber-text-primary font-medium">${message}</p>
            </div>
        `;
        loading.id = 'mobile-loading';
        document.body.appendChild(loading);
    }
    
    hideLoading() {
        const loading = document.getElementById('mobile-loading');
        if (loading) {
            loading.remove();
        }
    }
    
    updateSecurityMetrics(metrics) {
        // Update mobile security metric cards
        Object.keys(metrics).forEach(key => {
            const element = document.querySelector(`[data-metric="${key}"]`);
            if (element) {
                element.textContent = this.formatPersianNumbers(metrics[key].toString());
            }
        });
    }
    
    refreshCharts() {
        // Refresh charts for mobile view
        if (typeof Chart !== 'undefined') {
            Chart.instances.forEach(chart => {
                chart.resize();
            });
        }
    }
}

// Initialize mobile security settings when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.mobileSecuritySettings = new MobileSecuritySettings();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MobileSecuritySettings;
}