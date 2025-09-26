/**
 * Tests for Dashboard Interactive Components
 * ZARGAR Jewelry SaaS Platform
 */

// Mock Alpine.js and global objects
global.Alpine = {
    data: jest.fn(),
    store: jest.fn(() => ({
        theme: 'light',
        showNotification: jest.fn()
    })),
    initTree: jest.fn()
};

global.document = {
    addEventListener: jest.fn(),
    querySelector: jest.fn(),
    querySelectorAll: jest.fn(() => []),
    contains: jest.fn(() => true)
};

global.window = {
    zargarConfig: {
        csrfToken: 'test-token',
        currentTheme: 'light'
    },
    WebSocket: jest.fn(() => ({
        onmessage: null,
        onclose: null,
        close: jest.fn()
    })),
    location: {
        protocol: 'https:',
        host: 'test.zargar.com'
    },
    Chart: jest.fn(() => ({
        data: { labels: [], datasets: [] },
        config: { type: 'line' },
        update: jest.fn(),
        destroy: jest.fn()
    })),
    fetch: jest.fn()
};

// Mock Chart.js
global.Chart = jest.fn(() => ({
    data: { labels: [], datasets: [] },
    config: { type: 'line' },
    update: jest.fn(),
    destroy: jest.fn()
}));

global.Chart.defaults = {
    font: { family: '' },
    plugins: {
        tooltip: { rtl: false, textDirection: 'ltr' }
    }
};

// Load the dashboard components
require('../../static/js/dashboard-interactive.js');

describe('Dashboard Component', () => {
    let component;
    
    beforeEach(() => {
        // Reset and setup fetch mock
        global.fetch = jest.fn();
        
        global.setInterval = jest.fn();
        global.clearInterval = jest.fn();
        global.setTimeout = jest.fn();
        
        const componentFactory = Alpine.data.mock.calls.find(call => call[0] === 'dashboard')[1];
        component = componentFactory();
        
        component.$watch = jest.fn();
        component.showNotification = jest.fn();
        
        // Don't call init() here to avoid automatic API calls
    });
    
    test('should initialize with default values', () => {
        // Test initial state before any API calls
        const freshComponent = Alpine.data.mock.calls.find(call => call[0] === 'dashboard')[1]();
        
        expect(freshComponent.metrics.todaySales).toBe(0);
        expect(freshComponent.goldPrice.current).toBe(0);
        expect(freshComponent.recentSales).toEqual([]);
        expect(freshComponent.notifications).toEqual([]);
        expect(freshComponent.selectedPeriod).toBe('today');
        expect(freshComponent.autoRefresh).toBe(true);
    });
    
    test('should load dashboard data', async () => {
        await component.loadDashboardData();
        
        expect(global.fetch).toHaveBeenCalledWith('/api/dashboard/metrics/?period=today');
        expect(global.fetch).toHaveBeenCalledWith('/api/gold-prices/current/');
        expect(global.fetch).toHaveBeenCalledWith('/api/dashboard/recent-sales/');
        expect(global.fetch).toHaveBeenCalledWith('/api/dashboard/notifications/');
    });
    
    test('should load metrics correctly', async () => {
        global.fetch.mockResolvedValueOnce({
            json: () => Promise.resolve({
                metrics: {
                    todaySales: 5000000,
                    monthlySales: 150000000
                }
            })
        });
        
        await component.loadMetrics();
        
        expect(component.metrics.todaySales).toBe(5000000);
        expect(component.metrics.monthlySales).toBe(150000000);
        expect(component.loading.metrics).toBe(false);
    });
    
    test('should load gold price correctly', async () => {
        global.fetch.mockResolvedValueOnce({
            json: () => Promise.resolve({
                price: 2500000,
                change: 50000,
                trend: 'up'
            })
        });
        
        await component.loadGoldPrice();
        
        expect(component.goldPrice.current).toBe(2500000);
        expect(component.goldPrice.change).toBe(50000);
        expect(component.goldPrice.trend).toBe('up');
        expect(component.loading.goldPrice).toBe(false);
    });
    
    test('should load recent sales correctly', async () => {
        global.fetch.mockResolvedValueOnce({
            json: () => Promise.resolve({
                sales: [
                    { id: 1, customer: 'علی احمدی', amount: 1000000 }
                ]
            })
        });
        
        await component.loadRecentSales();
        
        expect(component.recentSales).toHaveLength(1);
        expect(component.recentSales[0].customer).toBe('علی احمدی');
        expect(component.loading.sales).toBe(false);
    });
    
    test('should load notifications correctly', async () => {
        global.fetch.mockResolvedValueOnce({
            json: () => Promise.resolve({
                notifications: [
                    { id: 1, message: 'فروش جدید', type: 'info' }
                ]
            })
        });
        
        await component.loadNotifications();
        
        expect(component.notifications).toHaveLength(1);
        expect(component.notifications[0].message).toBe('فروش جدید');
    });
    
    test('should setup auto refresh', () => {
        component.setupAutoRefresh();
        
        expect(global.setInterval).toHaveBeenCalledWith(
            expect.any(Function),
            30000 // 30 seconds
        );
    });
    
    test('should toggle auto refresh', () => {
        component.autoRefresh = true;
        component.refreshTimer = 'mock-timer';
        
        component.toggleAutoRefresh();
        
        expect(component.autoRefresh).toBe(false);
        expect(global.clearInterval).toHaveBeenCalledWith('mock-timer');
    });
    
    test('should change period and reload metrics', () => {
        component.changePeriod('week');
        
        expect(component.selectedPeriod).toBe('week');
    });
    
    test('should setup WebSocket connection', () => {
        // Mock window.location for WebSocket URL construction
        global.window.location = {
            protocol: 'https:',
            host: 'test.zargar.com'
        };
        
        const mockWebSocket = jest.fn();
        global.WebSocket = mockWebSocket;
        
        component.setupWebSocket();
        
        expect(mockWebSocket).toHaveBeenCalledWith('wss://test.zargar.com/ws/dashboard/');
    });
    
    test('should handle WebSocket messages', () => {
        const metricsUpdate = {
            type: 'metrics_update',
            metrics: { todaySales: 6000000 }
        };
        
        component.handleWebSocketMessage(metricsUpdate);
        
        expect(component.metrics.todaySales).toBe(6000000);
    });
    
    test('should handle gold price updates via WebSocket', () => {
        const goldPriceUpdate = {
            type: 'gold_price_update',
            goldPrice: { current: 2600000, change: 100000 }
        };
        
        component.handleWebSocketMessage(goldPriceUpdate);
        
        expect(component.goldPrice.current).toBe(2600000);
        expect(component.goldPrice.change).toBe(100000);
    });
    
    test('should handle new sale notifications via WebSocket', () => {
        const newSale = {
            type: 'new_sale',
            sale: { id: 2, customer: 'فاطمه رضایی', amount: 2000000 }
        };
        
        component.recentSales = [{ id: 1 }];
        component.handleWebSocketMessage(newSale);
        
        expect(component.recentSales).toHaveLength(2);
        expect(component.recentSales[0].customer).toBe('فاطمه رضایی');
    });
    
    test('should format currency correctly', () => {
        const formatted = component.formatCurrency(1234567);
        expect(formatted).toContain('تومان');
        expect(formatted).toContain('۱');
    });
    
    test('should format numbers correctly', () => {
        const formatted = component.formatNumber(12345);
        expect(formatted).toContain('۱');
        expect(formatted).toContain('۲');
    });
    
    test('should format dates correctly', () => {
        const formatted = component.formatDate('2023-01-01T12:00:00Z');
        expect(formatted).toBeDefined();
    });
    
    test('should get correct gold price change class', () => {
        component.goldPrice.change = 100;
        expect(component.goldPriceChangeClass).toBe('text-green-500');
        
        component.goldPrice.change = -100;
        expect(component.goldPriceChangeClass).toBe('text-red-500');
        
        component.goldPrice.change = 0;
        expect(component.goldPriceChangeClass).toBe('text-gray-500');
    });
    
    test('should get correct gold price icon', () => {
        component.goldPrice.change = 100;
        expect(component.goldPriceIcon).toBe('trending-up');
        
        component.goldPrice.change = -100;
        expect(component.goldPriceIcon).toBe('trending-down');
        
        component.goldPrice.change = 0;
        expect(component.goldPriceIcon).toBe('minus');
    });
});

describe('Sales Chart Component', () => {
    let component;
    
    beforeEach(() => {
        global.fetch = jest.fn(() => 
            Promise.resolve({
                json: () => Promise.resolve({
                    chartData: [
                        { label: 'شنبه', value: 1000000 },
                        { label: 'یکشنبه', value: 1500000 },
                        { label: 'دوشنبه', value: 2000000 }
                    ]
                })
            })
        );
        
        const componentFactory = Alpine.data.mock.calls.find(call => call[0] === 'salesChart')[1];
        component = componentFactory({ type: 'line', period: 'week' });
        
        component.$refs = {
            chartCanvas: {
                getContext: jest.fn(() => ({}))
            }
        };
        component.$watch = jest.fn();
        component.$nextTick = jest.fn(cb => cb());
        
        component.init();
    });
    
    test('should initialize with options', () => {
        expect(component.chartType).toBe('line');
        expect(component.period).toBe('week');
        expect(component.loading).toBe(false);
    });
    
    test('should load chart data', async () => {
        await component.loadChartData();
        
        expect(global.fetch).toHaveBeenCalledWith('/api/dashboard/sales-chart/?period=week');
        expect(component.chartData).toHaveLength(3);
        expect(component.loading).toBe(false);
    });
    
    test('should initialize chart', () => {
        component.chartData = [
            { label: 'شنبه', value: 1000000 }
        ];
        
        component.initChart();
        
        expect(global.Chart).toHaveBeenCalled();
    });
    
    test('should update chart data', () => {
        component.chart = {
            data: { labels: [], datasets: [{ data: [] }] },
            update: jest.fn()
        };
        component.chartData = [
            { label: 'شنبه', value: 1000000 }
        ];
        
        component.updateChart();
        
        expect(component.chart.data.labels).toEqual(['شنبه']);
        expect(component.chart.data.datasets[0].data).toEqual([1000000]);
        expect(component.chart.update).toHaveBeenCalled();
    });
    
    test('should change period', () => {
        component.changePeriod('month');
        expect(component.period).toBe('month');
    });
    
    test('should change chart type', () => {
        component.chart = {
            config: { type: 'line' },
            update: jest.fn()
        };
        
        component.changeType('bar');
        
        expect(component.chartType).toBe('bar');
        expect(component.chart.config.type).toBe('bar');
        expect(component.chart.update).toHaveBeenCalled();
    });
});

describe('Inventory Status Widget', () => {
    let component;
    
    beforeEach(() => {
        global.fetch = jest.fn(() => 
            Promise.resolve({
                json: () => Promise.resolve({
                    items: [
                        { id: 1, name: 'گردنبند طلا', stock: 5, minStock: 10 },
                        { id: 2, name: 'انگشتر نقره', stock: 0, minStock: 5 },
                        { id: 3, name: 'دستبند طلا', stock: 15, minStock: 10 }
                    ]
                })
            })
        );
        
        const componentFactory = Alpine.data.mock.calls.find(call => call[0] === 'inventoryStatus')[1];
        component = componentFactory();
        
        component.init();
    });
    
    test('should initialize with default values', () => {
        // Test initial state before any API calls
        const freshComponent = Alpine.data.mock.calls.find(call => call[0] === 'inventoryStatus')[1]();
        
        expect(freshComponent.items).toEqual([]);
        expect(freshComponent.loading).toBe(false);
        expect(freshComponent.filter).toBe('all');
    });
    
    test('should load inventory status', async () => {
        await component.loadInventoryStatus();
        
        expect(global.fetch).toHaveBeenCalledWith('/api/dashboard/inventory-status/');
        expect(component.items).toHaveLength(3);
        expect(component.loading).toBe(false);
    });
    
    test('should filter items correctly', () => {
        component.items = [
            { id: 1, stock: 5, minStock: 10 },
            { id: 2, stock: 0, minStock: 5 },
            { id: 3, stock: 15, minStock: 10 }
        ];
        
        // Test low-stock filter
        component.setFilter('low-stock');
        const lowStock = component.filteredItems;
        expect(lowStock).toHaveLength(1);
        expect(lowStock[0].id).toBe(1);
        
        // Test out-of-stock filter
        component.setFilter('out-of-stock');
        const outOfStock = component.filteredItems;
        expect(outOfStock).toHaveLength(1);
        expect(outOfStock[0].id).toBe(2);
        
        // Test all filter
        component.setFilter('all');
        const all = component.filteredItems;
        expect(all).toHaveLength(3);
    });
    
    test('should get correct stock status class', () => {
        expect(component.getStockStatusClass({ stock: 0 })).toBe('text-red-500');
        expect(component.getStockStatusClass({ stock: 5, minStock: 10 })).toBe('text-yellow-500');
        expect(component.getStockStatusClass({ stock: 15, minStock: 10 })).toBe('text-green-500');
    });
    
    test('should get correct stock status text', () => {
        expect(component.getStockStatusText({ stock: 0 })).toBe('ناموجود');
        expect(component.getStockStatusText({ stock: 5, minStock: 10 })).toBe('کم موجود');
        expect(component.getStockStatusText({ stock: 15, minStock: 10 })).toBe('موجود');
    });
});

describe('Recent Activities Widget', () => {
    let component;
    
    beforeEach(() => {
        global.fetch = jest.fn(() => 
            Promise.resolve({
                json: () => Promise.resolve({
                    activities: [
                        { id: 1, type: 'sale', description: 'فروش جدید', timestamp: '2023-01-01T12:00:00Z' },
                        { id: 2, type: 'payment', description: 'پرداخت دریافت شد', timestamp: '2023-01-01T11:30:00Z' }
                    ]
                })
            })
        );
        
        global.setInterval = jest.fn();
        
        const componentFactory = Alpine.data.mock.calls.find(call => call[0] === 'recentActivities')[1];
        component = componentFactory();
        
        component.init();
    });
    
    test('should initialize and load activities', async () => {
        await component.loadActivities();
        
        expect(global.fetch).toHaveBeenCalledWith('/api/dashboard/recent-activities/');
        expect(component.activities).toHaveLength(2);
        expect(component.loading).toBe(false);
    });
    
    test('should setup auto-refresh', () => {
        expect(global.setInterval).toHaveBeenCalledWith(
            expect.any(Function),
            120000 // 2 minutes
        );
    });
    
    test('should get correct activity icon', () => {
        expect(component.getActivityIcon('sale')).toBe('shopping-cart');
        expect(component.getActivityIcon('payment')).toBe('credit-card');
        expect(component.getActivityIcon('inventory')).toBe('package');
        expect(component.getActivityIcon('unknown')).toBe('activity');
    });
    
    test('should get correct activity color', () => {
        expect(component.getActivityColor('sale')).toBe('text-green-500');
        expect(component.getActivityColor('payment')).toBe('text-blue-500');
        expect(component.getActivityColor('inventory')).toBe('text-purple-500');
        expect(component.getActivityColor('unknown')).toBe('text-gray-500');
    });
    
    test('should format time correctly', () => {
        const now = new Date();
        const oneMinuteAgo = new Date(now.getTime() - 60000);
        const oneHourAgo = new Date(now.getTime() - 3600000);
        const oneDayAgo = new Date(now.getTime() - 86400000);
        
        expect(component.formatTime(now.toISOString())).toBe('همین الان');
        expect(component.formatTime(oneMinuteAgo.toISOString())).toContain('دقیقه پیش');
        expect(component.formatTime(oneHourAgo.toISOString())).toContain('ساعت پیش');
        expect(component.formatTime(oneDayAgo.toISOString())).toBeDefined();
    });
});

describe('Quick Stats Widget', () => {
    let component;
    
    beforeEach(() => {
        global.fetch = jest.fn(() => 
            Promise.resolve({
                json: () => Promise.resolve({
                    stats: {
                        todaySales: 5000000,
                        monthlyRevenue: 150000000,
                        totalCustomers: 250,
                        inventoryValue: 500000000
                    }
                })
            })
        );
        
        const componentFactory = Alpine.data.mock.calls.find(call => call[0] === 'quickStats')[1];
        component = componentFactory();
        
        component.init();
    });
    
    test('should initialize with predefined stats', () => {
        expect(component.stats).toHaveLength(4);
        expect(component.stats[0].key).toBe('todaySales');
        expect(component.stats[1].key).toBe('monthlyRevenue');
    });
    
    test('should load stats', async () => {
        await component.loadStats();
        
        expect(global.fetch).toHaveBeenCalledWith('/api/dashboard/quick-stats/');
        expect(component.loading).toBe(false);
    });
    
    test('should update stats', () => {
        const newStats = {
            todaySales: 6000000,
            monthlyRevenue: 180000000
        };
        
        component.updateStats(newStats);
        
        expect(component.stats[0].value).toBe(6000000);
        expect(component.stats[1].value).toBe(180000000);
    });
    
    test('should format values correctly', () => {
        const currencyStat = { key: 'todaySales', value: 1000000 };
        const numberStat = { key: 'totalCustomers', value: 250 };
        
        const currencyFormatted = component.formatValue(currencyStat);
        const numberFormatted = component.formatValue(numberStat);
        
        expect(currencyFormatted).toContain('تومان');
        expect(numberFormatted).toContain('۲');
    });
});

describe('Gold Price Ticker Widget', () => {
    let component;
    
    beforeEach(() => {
        global.fetch = jest.fn(() => 
            Promise.resolve({
                json: () => Promise.resolve({
                    current: 2500000,
                    previous: 2450000,
                    change: 50000,
                    changePercent: 2.04,
                    history: [
                        { time: '09:00', price: 2450000 },
                        { time: '10:00', price: 2500000 }
                    ]
                })
            })
        );
        
        global.setInterval = jest.fn();
        
        const componentFactory = Alpine.data.mock.calls.find(call => call[0] === 'goldPriceTicker')[1];
        component = componentFactory();
        
        component.init();
    });
    
    test('should initialize with default values', () => {
        // Test initial state before any API calls
        const freshComponent = Alpine.data.mock.calls.find(call => call[0] === 'goldPriceTicker')[1]();
        
        expect(freshComponent.prices.current).toBe(0);
        expect(freshComponent.prices.change).toBe(0);
        expect(freshComponent.history).toEqual([]);
        expect(freshComponent.loading).toBe(false);
    });
    
    test('should load gold price', async () => {
        await component.loadGoldPrice();
        
        expect(global.fetch).toHaveBeenCalledWith('/api/gold-prices/ticker/');
        expect(component.prices.current).toBe(2500000);
        expect(component.prices.change).toBe(50000);
        expect(component.history).toHaveLength(2);
        expect(component.loading).toBe(false);
    });
    
    test('should setup auto-refresh', () => {
        expect(global.setInterval).toHaveBeenCalledWith(
            expect.any(Function),
            30000 // 30 seconds
        );
    });
    
    test('should get correct change class', () => {
        component.prices.change = 100;
        expect(component.changeClass).toBe('text-green-500');
        
        component.prices.change = -100;
        expect(component.changeClass).toBe('text-red-500');
        
        component.prices.change = 0;
        expect(component.changeClass).toBe('text-gray-500');
    });
    
    test('should get correct change icon', () => {
        component.prices.change = 100;
        expect(component.changeIcon).toBe('arrow-up');
        
        component.prices.change = -100;
        expect(component.changeIcon).toBe('arrow-down');
        
        component.prices.change = 0;
        expect(component.changeIcon).toBe('minus');
    });
    
    test('should format price correctly', () => {
        const formatted = component.formatPrice(2500000);
        expect(formatted).toContain('۲');
        expect(formatted).toContain('۵');
    });
});

// Export for CI/CD
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        // Export test functions
    };
}