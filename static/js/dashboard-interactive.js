/**
 * Interactive Dashboard Components for ZARGAR Jewelry SaaS Platform
 * Real-time dashboard widgets with Persian RTL support and dual theme
 */

// Main Dashboard Component
Alpine.data('dashboard', () => ({
    // State
    metrics: {
        todaySales: 0,
        monthlySales: 0,
        inventoryValue: 0,
        lowStockItems: 0,
        pendingInstallments: 0,
        activeCustomers: 0
    },
    goldPrice: {
        current: 0,
        change: 0,
        trend: 'stable',
        lastUpdated: null
    },
    recentSales: [],
    notifications: [],
    loading: {
        metrics: false,
        goldPrice: false,
        sales: false
    },
    
    // UI State
    selectedPeriod: 'today',
    chartType: 'line',
    autoRefresh: true,
    refreshInterval: 30, // seconds
    
    init() {
        this.loadDashboardData();
        this.setupAutoRefresh();
        
        // Listen for real-time updates
        this.setupWebSocket();
    },
    
    async loadDashboardData() {
        await Promise.all([
            this.loadMetrics(),
            this.loadGoldPrice(),
            this.loadRecentSales(),
            this.loadNotifications()
        ]);
    },
    
    async loadMetrics() {
        this.loading.metrics = true;
        try {
            const response = await fetch(`/api/dashboard/metrics/?period=${this.selectedPeriod}`);
            const data = await response.json();
            this.metrics = { ...this.metrics, ...data.metrics };
        } catch (error) {
            console.error('Failed to load metrics:', error);
            this.showNotification('خطا در بارگذاری آمار', 'error');
        } finally {
            this.loading.metrics = false;
        }
    },
    
    async loadGoldPrice() {
        this.loading.goldPrice = true;
        try {
            const response = await fetch('/api/gold-prices/current/');
            const data = await response.json();
            this.goldPrice = {
                current: data.price || 0,
                change: data.change || 0,
                trend: data.trend || 'stable',
                lastUpdated: data.lastUpdated || new Date().toISOString()
            };
        } catch (error) {
            console.error('Failed to load gold price:', error);
        } finally {
            this.loading.goldPrice = false;
        }
    },
    
    async loadRecentSales() {
        this.loading.sales = true;
        try {
            const response = await fetch('/api/dashboard/recent-sales/');
            const data = await response.json();
            this.recentSales = data.sales || [];
        } catch (error) {
            console.error('Failed to load recent sales:', error);
        } finally {
            this.loading.sales = false;
        }
    },
    
    async loadNotifications() {
        try {
            const response = await fetch('/api/dashboard/notifications/');
            const data = await response.json();
            this.notifications = data.notifications || [];
        } catch (error) {
            console.error('Failed to load notifications:', error);
        }
    },
    
    setupAutoRefresh() {
        if (this.autoRefresh) {
            this.refreshTimer = setInterval(() => {
                this.loadDashboardData();
            }, this.refreshInterval * 1000);
        }
    },
    
    toggleAutoRefresh() {
        this.autoRefresh = !this.autoRefresh;
        
        if (this.autoRefresh) {
            this.setupAutoRefresh();
        } else if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
    },
    
    changePeriod(period) {
        this.selectedPeriod = period;
        this.loadMetrics();
    },
    
    setupWebSocket() {
        // WebSocket for real-time updates (if available)
        if (window.WebSocket) {
            try {
                const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${wsProtocol}//${window.location.host}/ws/dashboard/`;
                
                this.ws = new WebSocket(wsUrl);
                
                this.ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                };
                
                this.ws.onclose = () => {
                    // Attempt to reconnect after 5 seconds
                    setTimeout(() => {
                        this.setupWebSocket();
                    }, 5000);
                };
            } catch (error) {
                console.log('WebSocket not available, using polling instead');
            }
        }
    },
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'metrics_update':
                this.metrics = { ...this.metrics, ...data.metrics };
                break;
            case 'gold_price_update':
                this.goldPrice = data.goldPrice;
                break;
            case 'new_sale':
                this.recentSales.unshift(data.sale);
                this.recentSales = this.recentSales.slice(0, 10); // Keep only 10 recent
                break;
            case 'notification':
                this.notifications.unshift(data.notification);
                this.showNotification(data.notification.message, data.notification.type);
                break;
        }
    },
    
    // Utility Methods
    formatCurrency(amount) {
        if (!amount) return '۰ تومان';
        const formatted = new Intl.NumberFormat('fa-IR').format(Math.round(amount));
        return this.toPersianDigits(formatted) + ' تومان';
    },
    
    formatNumber(number) {
        if (!number) return '۰';
        const formatted = new Intl.NumberFormat('fa-IR').format(number);
        return this.toPersianDigits(formatted);
    },
    
    formatDate(dateString) {
        const date = new Date(dateString);
        return new Intl.DateTimeFormat('fa-IR').format(date);
    },
    
    toPersianDigits(str) {
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return str.toString().replace(/\d/g, (digit) => persianDigits[parseInt(digit)]);
    },
    
    showNotification(message, type = 'info') {
        if (Alpine.store('zargar')) {
            Alpine.store('zargar').showNotification(message, type);
        }
    },
    
    // Computed Properties
    get goldPriceChangeClass() {
        if (this.goldPrice.change > 0) return 'text-green-500';
        if (this.goldPrice.change < 0) return 'text-red-500';
        return 'text-gray-500';
    },
    
    get goldPriceIcon() {
        if (this.goldPrice.change > 0) return 'trending-up';
        if (this.goldPrice.change < 0) return 'trending-down';
        return 'minus';
    }
}));

// Sales Chart Component
Alpine.data('salesChart', (options = {}) => ({
    chartData: [],
    chartType: options.type || 'line',
    period: options.period || 'week',
    loading: false,
    chart: null,
    
    init() {
        this.loadChartData();
        this.$nextTick(() => {
            this.initChart();
        });
        
        this.$watch('period', () => {
            this.loadChartData();
        });
        
        this.$watch('chartType', () => {
            this.updateChart();
        });
    },
    
    async loadChartData() {
        this.loading = true;
        try {
            const response = await fetch(`/api/dashboard/sales-chart/?period=${this.period}`);
            const data = await response.json();
            this.chartData = data.chartData || [];
            this.updateChart();
        } catch (error) {
            console.error('Failed to load chart data:', error);
        } finally {
            this.loading = false;
        }
    },
    
    initChart() {
        const canvas = this.$refs.chartCanvas;
        if (!canvas || !window.Chart) return;
        
        const ctx = canvas.getContext('2d');
        
        this.chart = new Chart(ctx, {
            type: this.chartType,
            data: {
                labels: this.chartData.map(item => item.label),
                datasets: [{
                    label: 'فروش',
                    data: this.chartData.map(item => item.value),
                    borderColor: Alpine.store('zargar')?.theme === 'dark' ? '#00D4FF' : '#3B82F6',
                    backgroundColor: Alpine.store('zargar')?.theme === 'dark' ? 'rgba(0, 212, 255, 0.1)' : 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return new Intl.NumberFormat('fa-IR').format(value);
                            }
                        }
                    }
                }
            }
        });
    },
    
    updateChart() {
        if (!this.chart) return;
        
        this.chart.data.labels = this.chartData.map(item => item.label);
        this.chart.data.datasets[0].data = this.chartData.map(item => item.value);
        this.chart.update();
    },
    
    changePeriod(newPeriod) {
        this.period = newPeriod;
    },
    
    changeType(newType) {
        this.chartType = newType;
        if (this.chart) {
            this.chart.config.type = newType;
            this.chart.update();
        }
    }
}));

// Inventory Status Widget
Alpine.data('inventoryStatus', () => ({
    items: [],
    loading: false,
    filter: 'all', // all, low-stock, out-of-stock
    
    init() {
        this.loadInventoryStatus();
    },
    
    async loadInventoryStatus() {
        this.loading = true;
        try {
            const response = await fetch('/api/dashboard/inventory-status/');
            const data = await response.json();
            this.items = data.items || [];
        } catch (error) {
            console.error('Failed to load inventory status:', error);
        } finally {
            this.loading = false;
        }
    },
    
    setFilter(filter) {
        this.filter = filter;
    },
    
    get filteredItems() {
        switch (this.filter) {
            case 'low-stock':
                return this.items.filter(item => item.stock <= item.minStock && item.stock > 0);
            case 'out-of-stock':
                return this.items.filter(item => item.stock === 0);
            default:
                return this.items;
        }
    },
    
    getStockStatusClass(item) {
        if (item.stock === 0) return 'text-red-500';
        if (item.stock <= item.minStock) return 'text-yellow-500';
        return 'text-green-500';
    },
    
    getStockStatusText(item) {
        if (item.stock === 0) return 'ناموجود';
        if (item.stock <= item.minStock) return 'کم موجود';
        return 'موجود';
    }
}));

// Recent Activities Widget
Alpine.data('recentActivities', () => ({
    activities: [],
    loading: false,
    
    init() {
        this.loadActivities();
        
        // Auto-refresh every 2 minutes
        setInterval(() => {
            this.loadActivities();
        }, 120000);
    },
    
    async loadActivities() {
        this.loading = true;
        try {
            const response = await fetch('/api/dashboard/recent-activities/');
            const data = await response.json();
            this.activities = data.activities || [];
        } catch (error) {
            console.error('Failed to load activities:', error);
        } finally {
            this.loading = false;
        }
    },
    
    getActivityIcon(type) {
        const icons = {
            'sale': 'shopping-cart',
            'payment': 'credit-card',
            'inventory': 'package',
            'customer': 'user',
            'installment': 'calendar'
        };
        return icons[type] || 'activity';
    },
    
    getActivityColor(type) {
        const colors = {
            'sale': 'text-green-500',
            'payment': 'text-blue-500',
            'inventory': 'text-purple-500',
            'customer': 'text-yellow-500',
            'installment': 'text-red-500'
        };
        return colors[type] || 'text-gray-500';
    },
    
    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'همین الان';
        if (diff < 3600000) return `${Math.floor(diff / 60000)} دقیقه پیش`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)} ساعت پیش`;
        
        return new Intl.DateTimeFormat('fa-IR').format(date);
    }
}));

// Quick Stats Widget
Alpine.data('quickStats', () => ({
    stats: [
        { key: 'todaySales', label: 'فروش امروز', value: 0, icon: 'trending-up', color: 'green' },
        { key: 'monthlyRevenue', label: 'درآمد ماهانه', value: 0, icon: 'dollar-sign', color: 'blue' },
        { key: 'totalCustomers', label: 'مشتریان', value: 0, icon: 'users', color: 'purple' },
        { key: 'inventoryValue', label: 'ارزش موجودی', value: 0, icon: 'package', color: 'yellow' }
    ],
    loading: false,
    
    init() {
        this.loadStats();
        
        // Listen for real-time updates
        document.addEventListener('dashboard-update', (e) => {
            this.updateStats(e.detail);
        });
    },
    
    async loadStats() {
        this.loading = true;
        try {
            const response = await fetch('/api/dashboard/quick-stats/');
            const data = await response.json();
            this.updateStats(data.stats);
        } catch (error) {
            console.error('Failed to load quick stats:', error);
        } finally {
            this.loading = false;
        }
    },
    
    updateStats(newStats) {
        this.stats = this.stats.map(stat => ({
            ...stat,
            value: newStats[stat.key] || stat.value
        }));
    },
    
    formatValue(stat) {
        if (stat.key.includes('Sales') || stat.key.includes('Revenue') || stat.key.includes('Value')) {
            return this.formatCurrency(stat.value);
        }
        return this.formatNumber(stat.value);
    },
    
    formatCurrency(amount) {
        if (!amount) return '۰ تومان';
        const formatted = new Intl.NumberFormat('fa-IR').format(Math.round(amount));
        return this.toPersianDigits(formatted) + ' تومان';
    },
    
    formatNumber(number) {
        if (!number) return '۰';
        const formatted = new Intl.NumberFormat('fa-IR').format(number);
        return this.toPersianDigits(formatted);
    },
    
    toPersianDigits(str) {
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return str.toString().replace(/\d/g, (digit) => persianDigits[parseInt(digit)]);
    }
}));

// Gold Price Ticker Widget
Alpine.data('goldPriceTicker', () => ({
    prices: {
        current: 0,
        previous: 0,
        change: 0,
        changePercent: 0
    },
    history: [],
    loading: false,
    
    init() {
        this.loadGoldPrice();
        
        // Update every 30 seconds
        setInterval(() => {
            this.loadGoldPrice();
        }, 30000);
    },
    
    async loadGoldPrice() {
        this.loading = true;
        try {
            const response = await fetch('/api/gold-prices/ticker/');
            const data = await response.json();
            
            this.prices = {
                current: data.current || 0,
                previous: data.previous || 0,
                change: data.change || 0,
                changePercent: data.changePercent || 0
            };
            
            this.history = data.history || [];
        } catch (error) {
            console.error('Failed to load gold price:', error);
        } finally {
            this.loading = false;
        }
    },
    
    get changeClass() {
        if (this.prices.change > 0) return 'text-green-500';
        if (this.prices.change < 0) return 'text-red-500';
        return 'text-gray-500';
    },
    
    get changeIcon() {
        if (this.prices.change > 0) return 'arrow-up';
        if (this.prices.change < 0) return 'arrow-down';
        return 'minus';
    },
    
    formatPrice(price) {
        const formatted = new Intl.NumberFormat('fa-IR').format(Math.round(price));
        return this.toPersianDigits(formatted);
    },
    
    toPersianDigits(str) {
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return str.toString().replace(/\d/g, (digit) => persianDigits[parseInt(digit)]);
    }
}));

// Initialize dashboard components when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Auto-initialize dashboard if present
    const dashboardContainer = document.querySelector('[data-dashboard]');
    if (dashboardContainer && !dashboardContainer._x_dataStack) {
        Alpine.initTree(dashboardContainer);
    }
    
    // Setup Chart.js defaults for Persian/RTL
    if (window.Chart) {
        Chart.defaults.font.family = 'Vazirmatn, sans-serif';
        Chart.defaults.plugins.tooltip.rtl = true;
        Chart.defaults.plugins.tooltip.textDirection = 'rtl';
    }
});