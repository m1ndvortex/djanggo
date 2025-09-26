/**
 * Tenant Management JavaScript
 * Handles all frontend interactions for tenant management interface
 */

class TenantManagement {
    constructor() {
        this.selectedTenants = new Set();
        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeComponents();
    }

    bindEvents() {
        // Bulk selection events
        document.addEventListener('change', (e) => {
            if (e.target.name === 'tenant_ids') {
                this.handleTenantSelection(e.target);
            } else if (e.target.id === 'select-all') {
                this.handleSelectAll(e.target);
            }
        });

        // Search form events
        const searchForm = document.querySelector('form[hx-get]');
        if (searchForm) {
            this.initializeSearch(searchForm);
        }

        // Bulk action events
        const bulkActionBtn = document.getElementById('apply-bulk-action');
        if (bulkActionBtn) {
            bulkActionBtn.addEventListener('click', () => this.handleBulkAction());
        }

        const clearSelectionBtn = document.getElementById('clear-selection');
        if (clearSelectionBtn) {
            clearSelectionBtn.addEventListener('click', () => this.clearSelection());
        }

        // Status toggle events
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('toggle-status-btn')) {
                e.preventDefault();
                this.handleStatusToggle(e.target);
            }
        });

        // Statistics modal events
        document.addEventListener('click', (e) => {
            if (e.target.closest('[onclick*="showTenantStats"]')) {
                e.preventDefault();
                const tenantId = e.target.closest('[onclick*="showTenantStats"]').getAttribute('onclick').match(/\d+/)[0];
                this.showTenantStats(tenantId);
            }
        });
    }

    initializeComponents() {
        // Initialize tooltips
        this.initializeTooltips();
        
        // Initialize keyboard shortcuts
        this.initializeKeyboardShortcuts();
        
        // Initialize auto-refresh
        this.initializeAutoRefresh();
    }

    handleTenantSelection(checkbox) {
        const tenantId = checkbox.value;
        
        if (checkbox.checked) {
            this.selectedTenants.add(tenantId);
        } else {
            this.selectedTenants.delete(tenantId);
        }
        
        this.updateBulkActions();
        this.updateSelectAllState();
    }

    handleSelectAll(selectAllCheckbox) {
        const tenantCheckboxes = document.querySelectorAll('input[name="tenant_ids"]');
        
        tenantCheckboxes.forEach(checkbox => {
            checkbox.checked = selectAllCheckbox.checked;
            
            if (selectAllCheckbox.checked) {
                this.selectedTenants.add(checkbox.value);
            } else {
                this.selectedTenants.delete(checkbox.value);
            }
        });
        
        this.updateBulkActions();
    }

    updateBulkActions() {
        const bulkActionsDiv = document.getElementById('bulk-actions');
        const selectedCountSpan = document.getElementById('selected-count');
        
        if (!bulkActionsDiv || !selectedCountSpan) return;
        
        const count = this.selectedTenants.size;
        
        if (count > 0) {
            bulkActionsDiv.classList.remove('hidden');
            selectedCountSpan.textContent = this.formatPersianNumber(count);
        } else {
            bulkActionsDiv.classList.add('hidden');
        }
    }

    updateSelectAllState() {
        const selectAllCheckbox = document.getElementById('select-all');
        const tenantCheckboxes = document.querySelectorAll('input[name="tenant_ids"]');
        
        if (!selectAllCheckbox || tenantCheckboxes.length === 0) return;
        
        const checkedCount = this.selectedTenants.size;
        const totalCount = tenantCheckboxes.length;
        
        if (checkedCount === 0) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        } else if (checkedCount === totalCount) {
            selectAllCheckbox.checked = true;
            selectAllCheckbox.indeterminate = false;
        } else {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = true;
        }
    }

    clearSelection() {
        this.selectedTenants.clear();
        
        const tenantCheckboxes = document.querySelectorAll('input[name="tenant_ids"]');
        const selectAllCheckbox = document.getElementById('select-all');
        
        tenantCheckboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
        
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        }
        
        this.updateBulkActions();
    }

    async handleBulkAction() {
        const bulkActionSelect = document.getElementById('bulk-action-select');
        const action = bulkActionSelect.value;
        
        if (!action) {
            this.showMessage('لطفاً عملی را انتخاب کنید.', 'error');
            return;
        }
        
        if (this.selectedTenants.size === 0) {
            this.showMessage('لطفاً حداقل یک تنانت را انتخاب کنید.', 'error');
            return;
        }
        
        const actionText = {
            'activate': 'فعال کردن',
            'deactivate': 'غیرفعال کردن',
            'delete': 'حذف'
        }[action];
        
        const confirmMessage = `آیا مطمئن هستید که می‌خواهید ${actionText} ${this.formatPersianNumber(this.selectedTenants.size)} تنانت انتخاب شده را انجام دهید؟`;
        
        if (!confirm(confirmMessage)) {
            return;
        }
        
        try {
            this.showLoading();
            
            const response = await fetch('/admin/tenants/bulk-action/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: new URLSearchParams({
                    'action': action,
                    'tenant_ids': Array.from(this.selectedTenants)
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showMessage(data.message, 'success');
                this.refreshTenantList();
            } else {
                this.showMessage(data.message, 'error');
            }
        } catch (error) {
            this.showMessage('خطا در انجام عملیات', 'error');
            console.error('Bulk action error:', error);
        } finally {
            this.hideLoading();
        }
    }

    async handleStatusToggle(button) {
        const tenantId = button.dataset.tenantId;
        const currentStatus = button.dataset.currentStatus === 'true';
        const newStatusText = currentStatus ? 'غیرفعال' : 'فعال';
        
        if (!confirm(`آیا مطمئن هستید که می‌خواهید این تنانت را ${newStatusText} کنید؟`)) {
            return;
        }
        
        try {
            this.showLoading();
            
            const response = await fetch(`/admin/tenants/${tenantId}/toggle-status/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showMessage(data.message, 'success');
                this.refreshTenantList();
            } else {
                this.showMessage(data.message, 'error');
            }
        } catch (error) {
            this.showMessage('خطا در تغییر وضعیت', 'error');
            console.error('Status toggle error:', error);
        } finally {
            this.hideLoading();
        }
    }

    async showTenantStats(tenantId) {
        const modal = document.getElementById('tenant-stats-modal');
        const content = document.getElementById('tenant-stats-content');
        
        if (!modal || !content) return;
        
        modal.classList.remove('hidden');
        
        // Reset content to loading state
        content.innerHTML = `
            <div class="text-center py-8">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500 dark:border-cyber-neon-primary mx-auto"></div>
                <p class="mt-2 text-gray-600 dark:text-cyber-text-secondary">در حال بارگذاری آمار...</p>
            </div>
        `;
        
        try {
            const response = await fetch(`/admin/tenants/${tenantId}/statistics/`);
            const data = await response.json();
            
            if (data.success) {
                this.displayTenantStats(data.stats);
            } else {
                this.showStatsError(data.message);
            }
        } catch (error) {
            this.showStatsError('خطا در ارتباط با سرور');
            console.error('Stats loading error:', error);
        }
    }

    displayTenantStats(stats) {
        const content = document.getElementById('tenant-stats-content');
        
        let html = '<div class="grid grid-cols-1 md:grid-cols-2 gap-6">';
        
        // Basic Info
        if (stats.basic_info) {
            html += this.renderStatsSection('اطلاعات پایه', [
                { label: 'نام', value: stats.basic_info.name || 'نامشخص' },
                { label: 'مالک', value: stats.basic_info.owner_name || 'نامشخص' },
                { label: 'پلن اشتراک', value: stats.basic_info.subscription_plan || 'نامشخص' },
                { label: 'روزهای فعالیت', value: this.formatPersianNumber(stats.basic_info.days_active || 0) }
            ]);
        }
        
        // Usage Metrics
        if (stats.usage_metrics) {
            const metrics = [
                { label: 'کل کاربران', value: this.formatPersianNumber(stats.usage_metrics.total_users || 0) },
                { label: 'کاربران فعال', value: this.formatPersianNumber(stats.usage_metrics.active_users || 0) }
            ];
            
            if (stats.usage_metrics.total_jewelry_items !== undefined) {
                metrics.push({ label: 'اقلام جواهرات', value: this.formatPersianNumber(stats.usage_metrics.total_jewelry_items) });
            }
            
            if (stats.usage_metrics.total_customers !== undefined) {
                metrics.push({ label: 'مشتریان', value: this.formatPersianNumber(stats.usage_metrics.total_customers) });
            }
            
            html += this.renderStatsSection('آمار استفاده', metrics);
        }
        
        // Activity Stats
        if (stats.activity_stats) {
            html += this.renderStatsSection('فعالیت (۳۰ روز اخیر)', [
                { label: 'کل عملیات', value: this.formatPersianNumber(stats.activity_stats.total_actions_30_days || 0) },
                { label: 'نرخ موفقیت', value: this.formatPersianNumber(stats.activity_stats.success_rate || 0) + '%' }
            ]);
        }
        
        // Storage Usage
        if (stats.storage_usage) {
            html += this.renderStatsSection('فضای ذخیره', [
                { label: 'حجم اسکیما', value: stats.storage_usage.schema_size_pretty || '0 bytes' }
            ]);
        }
        
        html += '</div>';
        content.innerHTML = html;
    }

    renderStatsSection(title, items) {
        let html = `
            <div class="bg-gray-50 dark:bg-cyber-bg-surface rounded-lg p-4">
                <h4 class="font-medium text-gray-900 dark:text-cyber-text-primary mb-3">${title}</h4>
                <div class="space-y-2 text-sm">
        `;
        
        items.forEach(item => {
            html += `
                <div class="flex justify-between">
                    <span class="text-gray-600 dark:text-cyber-text-secondary">${item.label}:</span>
                    <span class="text-gray-900 dark:text-cyber-text-primary">${item.value}</span>
                </div>
            `;
        });
        
        html += '</div></div>';
        return html;
    }

    showStatsError(message) {
        const content = document.getElementById('tenant-stats-content');
        content.innerHTML = `
            <div class="text-center py-8">
                <svg class="mx-auto h-12 w-12 text-red-400 dark:text-cyber-neon-danger mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <p class="text-red-600 dark:text-cyber-neon-danger">${message}</p>
            </div>
        `;
    }

    initializeSearch(form) {
        const searchInput = form.querySelector('input[name="search"]');
        if (!searchInput) return;
        
        let searchTimeout;
        
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.performSearch(form);
            }, 500);
        });
        
        // Handle filter changes
        const filterInputs = form.querySelectorAll('select, input[type="date"]');
        filterInputs.forEach(input => {
            input.addEventListener('change', () => {
                this.performSearch(form);
            });
        });
    }

    async performSearch(form) {
        try {
            this.showLoading();
            
            const formData = new FormData(form);
            const params = new URLSearchParams(formData);
            
            const response = await fetch(`${form.action}?${params}`, {
                headers: {
                    'HX-Request': 'true'
                }
            });
            
            if (response.ok) {
                const html = await response.text();
                const container = document.getElementById('tenant-list-container');
                if (container) {
                    container.innerHTML = html;
                    this.selectedTenants.clear();
                    this.updateBulkActions();
                }
            }
        } catch (error) {
            this.showMessage('خطا در جستجو', 'error');
            console.error('Search error:', error);
        } finally {
            this.hideLoading();
        }
    }

    refreshTenantList() {
        const currentUrl = new URL(window.location);
        this.performSearch({ action: currentUrl.pathname, elements: [] });
    }

    initializeTooltips() {
        // Initialize tooltips for action buttons
        const actionButtons = document.querySelectorAll('[title]');
        actionButtons.forEach(button => {
            button.addEventListener('mouseenter', (e) => {
                this.showTooltip(e.target, e.target.getAttribute('title'));
            });
            
            button.addEventListener('mouseleave', () => {
                this.hideTooltip();
            });
        });
    }

    showTooltip(element, text) {
        const tooltip = document.createElement('div');
        tooltip.className = 'tooltip';
        tooltip.textContent = text;
        tooltip.style.cssText = `
            position: absolute;
            background: #1f2937;
            color: white;
            padding: 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            z-index: 1000;
            pointer-events: none;
        `;
        
        document.body.appendChild(tooltip);
        
        const rect = element.getBoundingClientRect();
        tooltip.style.top = `${rect.top - tooltip.offsetHeight - 5}px`;
        tooltip.style.left = `${rect.left + (rect.width - tooltip.offsetWidth) / 2}px`;
        
        this.currentTooltip = tooltip;
    }

    hideTooltip() {
        if (this.currentTooltip) {
            this.currentTooltip.remove();
            this.currentTooltip = null;
        }
    }

    initializeKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + A to select all
            if ((e.ctrlKey || e.metaKey) && e.key === 'a' && !e.target.matches('input, textarea')) {
                e.preventDefault();
                const selectAllCheckbox = document.getElementById('select-all');
                if (selectAllCheckbox) {
                    selectAllCheckbox.checked = true;
                    this.handleSelectAll(selectAllCheckbox);
                }
            }
            
            // Escape to clear selection
            if (e.key === 'Escape') {
                this.clearSelection();
                
                // Close modals
                const modals = document.querySelectorAll('.modal-overlay:not(.hidden)');
                modals.forEach(modal => modal.classList.add('hidden'));
            }
            
            // Delete key for bulk delete (with confirmation)
            if (e.key === 'Delete' && this.selectedTenants.size > 0 && !e.target.matches('input, textarea')) {
                e.preventDefault();
                const bulkActionSelect = document.getElementById('bulk-action-select');
                if (bulkActionSelect) {
                    bulkActionSelect.value = 'delete';
                    this.handleBulkAction();
                }
            }
        });
    }

    initializeAutoRefresh() {
        // Auto-refresh every 5 minutes
        setInterval(() => {
            if (document.visibilityState === 'visible') {
                this.refreshTenantList();
            }
        }, 5 * 60 * 1000);
    }

    // Utility methods
    formatPersianNumber(number) {
        const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
        return number.toString().replace(/\d/g, (digit) => persianDigits[digit]);
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('fa-IR').format(amount) + ' تومان';
    }

    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    showLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.remove('hidden');
        }
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }
    }

    showMessage(message, type = 'info') {
        const toast = document.createElement('div');
        const bgColor = type === 'error' ? 'bg-red-500' : type === 'success' ? 'bg-green-500' : 'bg-blue-500';
        
        toast.className = `fixed top-4 left-4 ${bgColor} text-white px-6 py-3 rounded-lg shadow-lg z-50 transform transition-transform duration-300 translate-x-full`;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => toast.classList.remove('translate-x-full'), 100);
        setTimeout(() => {
            toast.classList.add('translate-x-full');
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 3000);
    }
}

// Global functions for template compatibility
window.showTenantStats = function(tenantId) {
    if (window.tenantManagement) {
        window.tenantManagement.showTenantStats(tenantId);
    }
};

window.closeTenantStatsModal = function() {
    const modal = document.getElementById('tenant-stats-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.tenantManagement = new TenantManagement();
    
    // Close modal when clicking outside
    const modal = document.getElementById('tenant-stats-modal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                window.closeTenantStatsModal();
            }
        });
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TenantManagement;
}