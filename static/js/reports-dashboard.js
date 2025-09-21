/**
 * Reports Dashboard JavaScript Module
 * Handles dashboard interactions, real-time updates, and Persian formatting
 */

class ReportsDashboard {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializePersianNumbers();
        this.setupAutoRefresh();
        this.initializeCharts();
    }

    setupEventListeners() {
        // Quick action buttons
        document.addEventListener('click', (e) => {
            if (e.target.dataset.action) {
                this.handleQuickAction(e.target.dataset.action, e.target);
            }
        });

        // Template selection for quick generation
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('template-selector')) {
                this.handleTemplateQuickGenerate(e.target.value);
            }
        });
    }

    initializePersianNumbers() {
        // Convert numbers to Persian digits
        const persianNumbers = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        const elements = document.querySelectorAll('.persian-numbers');
        
        elements.forEach(element => {
            let text = element.textContent;
            if (text) {
                text = text.replace(/[0-9]/g, (match) => persianNumbers[parseInt(match)]);
                element.textContent = text;
            }
        });
    }

    setupAutoRefresh() {
        // Auto-refresh generating reports every 30 seconds
        const generatingReports = document.querySelectorAll('.status-generating');
        if (generatingReports.length > 0) {
            setTimeout(() => {
                this.refreshReportStatuses();
            }, 30000);
        }
    }

    async refreshReportStatuses() {
        const generatingReports = document.querySelectorAll('.status-generating');
        
        for (const reportElement of generatingReports) {
            const reportId = reportElement.dataset.reportId;
            if (reportId) {
                try {
                    const response = await fetch(`/reports/ajax/status/${reportId}/`);
                    const data = await response.json();
                    
                    if (data.status !== 'generating') {
                        // Refresh the page to show updated status
                        window.location.reload();
                        break;
                    }
                } catch (error) {
                    console.error('Error checking report status:', error);
                }
            }
        }
    }

    initializeCharts() {
        // Initialize any charts on the dashboard
        this.initializeReportsChart();
        this.initializeStatusChart();
    }

    initializeReportsChart() {
        const chartCanvas = document.getElementById('reportsChart');
        if (!chartCanvas || typeof Chart === 'undefined') return;

        const ctx = chartCanvas.getContext('2d');
        const isDark = document.body.classList.contains('dark');
        
        // Sample data - replace with actual data from backend
        const chartData = {
            labels: ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور'],
            datasets: [{
                label: 'تعداد گزارش‌ها',
                data: [12, 19, 8, 15, 22, 18],
                borderColor: isDark ? '#00D4FF' : '#3b82f6',
                backgroundColor: isDark ? 'rgba(0, 212, 255, 0.1)' : 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        };

        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: isDark ? '#FFFFFF' : '#374151',
                        font: {
                            family: 'Vazirmatn, Tahoma, Arial, sans-serif'
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: isDark ? '#B8BCC8' : '#6b7280',
                        font: {
                            family: 'Vazirmatn, Tahoma, Arial, sans-serif'
                        }
                    },
                    grid: {
                        color: isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.1)'
                    }
                },
                y: {
                    ticks: {
                        color: isDark ? '#B8BCC8' : '#6b7280',
                        font: {
                            family: 'Vazirmatn, Tahoma, Arial, sans-serif'
                        }
                    },
                    grid: {
                        color: isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.1)'
                    }
                }
            }
        };

        new Chart(ctx, {
            type: 'line',
            data: chartData,
            options: chartOptions
        });
    }

    initializeStatusChart() {
        const chartCanvas = document.getElementById('statusChart');
        if (!chartCanvas || typeof Chart === 'undefined') return;

        const ctx = chartCanvas.getContext('2d');
        const isDark = document.body.classList.contains('dark');
        
        // Sample data - replace with actual data from backend
        const chartData = {
            labels: ['تکمیل شده', 'در حال تولید', 'خطا', 'در انتظار'],
            datasets: [{
                data: [65, 15, 10, 10],
                backgroundColor: isDark 
                    ? ['#00FF88', '#FFB800', '#FF4757', '#6B7280']
                    : ['#10b981', '#f59e0b', '#ef4444', '#6b7280'],
                borderWidth: 0
            }]
        };

        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: isDark ? '#FFFFFF' : '#374151',
                        font: {
                            family: 'Vazirmatn, Tahoma, Arial, sans-serif'
                        },
                        padding: 20
                    }
                }
            }
        };

        new Chart(ctx, {
            type: 'doughnut',
            data: chartData,
            options: chartOptions
        });
    }

    handleQuickAction(action, element) {
        switch (action) {
            case 'generate-report':
                this.showQuickGenerateModal();
                break;
            case 'view-schedules':
                window.location.href = '/reports/schedules/';
                break;
            case 'export-data':
                this.handleDataExport();
                break;
            default:
                console.log('Unknown action:', action);
        }
    }

    showQuickGenerateModal() {
        // Create and show a modal for quick report generation
        const modal = this.createQuickGenerateModal();
        document.body.appendChild(modal);
        
        // Show modal with animation
        setTimeout(() => {
            modal.classList.add('opacity-100');
            modal.querySelector('.modal-content').classList.add('scale-100');
        }, 10);
    }

    createQuickGenerateModal() {
        const isDark = document.body.classList.contains('dark');
        
        const modal = document.createElement('div');
        modal.className = `fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm transition-opacity duration-300 opacity-0 ${
            isDark ? 'bg-cyber-bg-primary/90' : 'bg-black/50'
        }`;
        
        modal.innerHTML = `
            <div class="modal-content max-w-md w-full mx-4 p-6 rounded-xl transform transition-transform duration-300 scale-95 ${
                isDark 
                    ? 'bg-gradient-to-br from-cyber-bg-surface to-cyber-bg-elevated border border-cyber-border-glass backdrop-blur-sm'
                    : 'bg-white border border-gray-200 shadow-xl'
            }">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-lg font-semibold ${
                        isDark ? 'text-cyber-text-primary' : 'text-gray-900'
                    }">
                        تولید سریع گزارش
                    </h3>
                    <button onclick="this.closest('.fixed').remove()" 
                            class="text-gray-400 hover:text-gray-600 transition-colors">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
                
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium mb-2 ${
                            isDark ? 'text-cyber-text-primary' : 'text-gray-700'
                        }">
                            نوع گزارش
                        </label>
                        <select class="w-full px-3 py-2 rounded-lg border transition-all duration-300 ${
                            isDark 
                                ? 'bg-cyber-bg-surface/60 border-cyber-border-glass text-cyber-text-primary focus:border-cyber-neon-primary'
                                : 'bg-white border-gray-300 text-gray-900 focus:border-blue-500'
                        }">
                            <option value="">انتخاب کنید...</option>
                            <option value="trial_balance">ترازنامه آزمایشی</option>
                            <option value="profit_loss">سود و زیان</option>
                            <option value="inventory_valuation">ارزش‌گذاری موجودی</option>
                            <option value="customer_aging">تحلیل سن مطالبات</option>
                        </select>
                    </div>
                    
                    <div class="flex space-x-3 space-x-reverse">
                        <button onclick="this.closest('.fixed').remove()" 
                                class="flex-1 px-4 py-2 rounded-lg font-medium transition-all duration-300 ${
                                    isDark 
                                        ? 'bg-cyber-bg-surface/60 border border-cyber-border-glass text-cyber-text-primary hover:bg-cyber-bg-elevated'
                                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                }">
                            انصراف
                        </button>
                        <button onclick="window.location.href='/reports/generate/'" 
                                class="flex-1 px-4 py-2 rounded-lg font-medium transition-all duration-300 ${
                                    isDark 
                                        ? 'bg-gradient-to-r from-cyber-neon-primary to-cyber-neon-secondary text-cyber-bg-primary hover:shadow-lg hover:shadow-cyber-neon-primary/20'
                                        : 'bg-blue-600 text-white hover:bg-blue-700'
                                }">
                            ادامه
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        return modal;
    }

    handleTemplateQuickGenerate(templateId) {
        if (templateId) {
            window.location.href = `/reports/generate/${templateId}/`;
        }
    }

    async handleDataExport() {
        try {
            this.showNotification('در حال آماده‌سازی فایل صادراتی...', 'info');
            
            const response = await fetch('/reports/export/dashboard-data/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `dashboard-data-${new Date().toISOString().split('T')[0]}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                this.showNotification('فایل با موفقیت دانلود شد', 'success');
            } else {
                throw new Error('خطا در دانلود فایل');
            }
        } catch (error) {
            console.error('Export error:', error);
            this.showNotification('خطا در صادرات داده‌ها: ' + error.message, 'error');
        }
    }

    showNotification(message, type = 'info', duration = 5000) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-20 right-4 z-50 max-w-sm p-4 rounded-lg shadow-lg backdrop-blur-sm transition-all duration-300 animate-slide-in-right`;
        
        // Set theme-appropriate classes
        const isDark = document.body.classList.contains('dark');
        
        switch (type) {
            case 'success':
                notification.className += isDark 
                    ? ' bg-green-900/80 border border-green-500/50 text-green-200'
                    : ' bg-green-50 border border-green-200 text-green-800';
                break;
            case 'error':
                notification.className += isDark 
                    ? ' bg-red-900/80 border border-red-500/50 text-red-200'
                    : ' bg-red-50 border border-red-200 text-red-800';
                break;
            case 'warning':
                notification.className += isDark 
                    ? ' bg-yellow-900/80 border border-yellow-500/50 text-yellow-200'
                    : ' bg-yellow-50 border border-yellow-200 text-yellow-800';
                break;
            default:
                notification.className += isDark 
                    ? ' bg-cyber-bg-surface/80 border border-cyber-neon-primary/30 text-cyber-text-primary'
                    : ' bg-blue-50 border border-blue-200 text-blue-800';
        }

        notification.innerHTML = `
            <div class="flex items-center justify-between">
                <p class="text-sm font-medium">${message}</p>
                <button onclick="this.parentElement.parentElement.remove()" 
                        class="mr-2 text-current opacity-70 hover:opacity-100 transition-opacity">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        `;

        document.body.appendChild(notification);

        // Auto remove after duration
        setTimeout(() => {
            if (notification.parentElement) {
                notification.style.transform = 'translateX(100%)';
                notification.style.opacity = '0';
                setTimeout(() => {
                    notification.remove();
                }, 300);
            }
        }, duration);
    }

    // Utility method to format Persian dates
    formatPersianDate(date) {
        if (typeof PersianDate !== 'undefined') {
            const pDate = new PersianDate(date);
            return pDate.format('YYYY/MM/DD');
        }
        return date.toLocaleDateString('fa-IR');
    }

    // Utility method to format Persian numbers
    toPersianNumbers(str) {
        const persianNumbers = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return str.replace(/[0-9]/g, (match) => persianNumbers[parseInt(match)]);
    }

    // Method to update dashboard stats in real-time
    async updateDashboardStats() {
        try {
            const response = await fetch('/reports/ajax/dashboard-stats/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                // Update stat cards
                this.updateStatCard('total-reports', data.total_reports);
                this.updateStatCard('reports-this-month', data.reports_this_month);
                this.updateStatCard('active-schedules', data.active_schedules);
                this.updateStatCard('templates-available', data.templates_available);
            }
        } catch (error) {
            console.error('Error updating dashboard stats:', error);
        }
    }

    updateStatCard(cardId, value) {
        const card = document.getElementById(cardId);
        if (card) {
            const valueElement = card.querySelector('.stat-value');
            if (valueElement) {
                valueElement.textContent = this.toPersianNumbers(value.toString());
            }
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.reportsDashboard = new ReportsDashboard();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ReportsDashboard;
}