/**
 * POS Interface JavaScript
 * Touch-optimized functionality for jewelry shop point of sale system
 */

class POSInterface {
    constructor() {
        this.isOnline = navigator.onLine;
        this.offlineQueue = [];
        this.goldPriceCache = null;
        this.lastGoldPriceUpdate = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupOfflineHandling();
        this.setupTouchOptimizations();
        this.loadCachedData();
        
        console.log('POS Interface initialized');
    }
    
    setupEventListeners() {
        // Online/offline status
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.syncOfflineQueue();
            this.updateConnectionStatus();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.updateConnectionStatus();
        });
        
        // Prevent accidental page refresh
        window.addEventListener('beforeunload', (e) => {
            if (this.hasUnsavedChanges()) {
                e.preventDefault();
                e.returnValue = 'تراکنش‌های ذخیره نشده وجود دارد. آیا مطمئن هستید؟';
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcuts(e);
        });
        
        // Touch events for better responsiveness
        document.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: true });
        document.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: true });
    }
    
    setupOfflineHandling() {
        // Check if service worker is supported
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/js/pos-sw.js')
                .then(registration => {
                    console.log('POS Service Worker registered:', registration);
                })
                .catch(error => {
                    console.log('POS Service Worker registration failed:', error);
                });
        }
        
        // Load offline queue from localStorage
        const savedQueue = localStorage.getItem('pos_offline_queue');
        if (savedQueue) {
            this.offlineQueue = JSON.parse(savedQueue);
        }
    }
    
    setupTouchOptimizations() {
        // Disable double-tap zoom on buttons
        const touchButtons = document.querySelectorAll('.touch-btn');
        touchButtons.forEach(button => {
            let lastTouchEnd = 0;
            button.addEventListener('touchend', (e) => {
                const now = new Date().getTime();
                if (now - lastTouchEnd <= 300) {
                    e.preventDefault();
                }
                lastTouchEnd = now;
            }, false);
        });
        
        // Add haptic feedback for supported devices
        if ('vibrate' in navigator) {
            touchButtons.forEach(button => {
                button.addEventListener('click', () => {
                    navigator.vibrate(10); // Short vibration
                });
            });
        }
    }
    
    loadCachedData() {
        // Load cached gold prices
        const cachedGoldPrice = localStorage.getItem('pos_gold_price_cache');
        const cacheTimestamp = localStorage.getItem('pos_gold_price_timestamp');
        
        if (cachedGoldPrice && cacheTimestamp) {
            const cacheAge = Date.now() - parseInt(cacheTimestamp);
            // Use cache if less than 5 minutes old
            if (cacheAge < 5 * 60 * 1000) {
                this.goldPriceCache = JSON.parse(cachedGoldPrice);
                this.lastGoldPriceUpdate = new Date(parseInt(cacheTimestamp));
            }
        }
    }
    
    handleKeyboardShortcuts(e) {
        // Only handle shortcuts when not in input fields
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        switch (e.key) {
            case 'F1':
                e.preventDefault();
                this.openCustomerLookup();
                break;
            case 'F2':
                e.preventDefault();
                this.openInventorySearch();
                break;
            case 'F3':
                e.preventDefault();
                this.openCalculator();
                break;
            case 'F9':
                e.preventDefault();
                this.completeTransaction();
                break;
            case 'Escape':
                this.closeAllModals();
                break;
        }
    }
    
    handleTouchStart(e) {
        // Add visual feedback for touch
        if (e.target.classList.contains('touch-btn')) {
            e.target.classList.add('touching');
        }
    }
    
    handleTouchEnd(e) {
        // Remove visual feedback
        if (e.target.classList.contains('touch-btn')) {
            setTimeout(() => {
                e.target.classList.remove('touching');
            }, 150);
        }
    }
    
    updateConnectionStatus() {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            const indicator = statusElement.querySelector('.w-2');
            const text = statusElement.querySelector('span');
            
            if (this.isOnline) {
                indicator.className = 'w-2 h-2 rounded-full bg-green-500 animate-pulse';
                text.textContent = 'آنلاین';
            } else {
                indicator.className = 'w-2 h-2 rounded-full bg-red-500';
                text.textContent = 'آفلاین';
            }
        }
    }
    
    async syncOfflineQueue() {
        if (this.offlineQueue.length === 0) return;
        
        console.log(`Syncing ${this.offlineQueue.length} offline transactions`);
        
        const syncPromises = this.offlineQueue.map(async (transaction) => {
            try {
                const response = await fetch('/pos/sync/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify(transaction)
                });
                
                if (response.ok) {
                    return { success: true, transaction };
                } else {
                    throw new Error('Sync failed');
                }
            } catch (error) {
                console.error('Failed to sync transaction:', error);
                return { success: false, transaction, error };
            }
        });
        
        const results = await Promise.allSettled(syncPromises);
        
        // Remove successfully synced transactions
        const failedTransactions = [];
        results.forEach((result, index) => {
            if (result.status === 'rejected' || !result.value.success) {
                failedTransactions.push(this.offlineQueue[index]);
            }
        });
        
        this.offlineQueue = failedTransactions;
        this.saveOfflineQueue();
        
        // Show sync results
        const syncedCount = results.length - failedTransactions.length;
        if (syncedCount > 0) {
            this.showNotification(`${syncedCount} تراکنش با موفقیت همگام‌سازی شد`, 'success');
        }
        
        if (failedTransactions.length > 0) {
            this.showNotification(`${failedTransactions.length} تراکنش همگام‌سازی نشد`, 'warning');
        }
    }
    
    saveOfflineQueue() {
        localStorage.setItem('pos_offline_queue', JSON.stringify(this.offlineQueue));
    }
    
    addToOfflineQueue(transaction) {
        transaction.offline_timestamp = Date.now();
        transaction.offline_id = this.generateOfflineId();
        this.offlineQueue.push(transaction);
        this.saveOfflineQueue();
        
        this.showNotification('تراکنش در صف آفلاین ذخیره شد', 'info');
    }
    
    generateOfflineId() {
        return 'offline_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    hasUnsavedChanges() {
        return this.offlineQueue.length > 0;
    }
    
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : window.zargarConfig?.csrfToken || '';
    }
    
    // Gold price management
    async updateGoldPrices() {
        try {
            const response = await fetch('/pos/api/gold-price/');
            const data = await response.json();
            
            if (data.success) {
                this.goldPriceCache = data.price_data;
                this.lastGoldPriceUpdate = new Date();
                
                // Cache the data
                localStorage.setItem('pos_gold_price_cache', JSON.stringify(this.goldPriceCache));
                localStorage.setItem('pos_gold_price_timestamp', Date.now().toString());
                
                // Update UI
                this.updateGoldPriceDisplay();
                
                return this.goldPriceCache;
            }
        } catch (error) {
            console.error('Failed to update gold prices:', error);
            
            // Use cached data if available
            if (this.goldPriceCache) {
                this.showNotification('استفاده از قیمت طلای ذخیره شده', 'warning');
                return this.goldPriceCache;
            }
            
            throw error;
        }
    }
    
    updateGoldPriceDisplay() {
        const priceElement = document.getElementById('current-gold-price');
        if (priceElement && this.goldPriceCache) {
            const formattedPrice = this.formatCurrency(this.goldPriceCache.price_per_gram);
            priceElement.textContent = `${formattedPrice} (${this.goldPriceCache.karat} عیار)`;
        }
    }
    
    // Utility functions
    formatCurrency(amount, usePersianDigits = true) {
        if (!amount) return '۰ تومان';
        
        const formatted = new Intl.NumberFormat('fa-IR').format(amount);
        return usePersianDigits ? this.toPersianDigits(formatted) + ' تومان' : formatted + ' تومان';
    }
    
    formatWeight(weight, unit = 'گرم', usePersianDigits = true) {
        if (!weight) return '۰ ' + unit;
        
        const formatted = new Intl.NumberFormat('fa-IR', {
            minimumFractionDigits: 3,
            maximumFractionDigits: 3
        }).format(weight);
        
        return usePersianDigits ? this.toPersianDigits(formatted) + ' ' + unit : formatted + ' ' + unit;
    }
    
    toPersianDigits(str) {
        const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
        const englishDigits = '0123456789';
        
        return str.toString().replace(/[0-9]/g, function(w) {
            return persianDigits[englishDigits.indexOf(w)];
        });
    }
    
    toEnglishDigits(str) {
        const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
        const englishDigits = '0123456789';
        
        return str.toString().replace(/[۰-۹]/g, function(w) {
            return englishDigits[persianDigits.indexOf(w)];
        });
    }
    
    showNotification(message, type = 'info', duration = 5000) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-20 right-4 z-50 max-w-sm p-4 rounded-lg shadow-lg backdrop-blur-sm transition-all duration-300 animate-slide-in-right`;
        
        // Set type-specific styling
        switch (type) {
            case 'success':
                notification.className += ' bg-green-900/80 border border-green-500/50 text-green-200';
                break;
            case 'error':
                notification.className += ' bg-red-900/80 border border-red-500/50 text-red-200';
                break;
            case 'warning':
                notification.className += ' bg-yellow-900/80 border border-yellow-500/50 text-yellow-200';
                break;
            default:
                notification.className += ' bg-cyber-bg-surface/80 border border-cyber-neon-primary/30 text-cyber-text-primary';
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
        
        // Auto-remove after duration
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, duration);
    }
    
    // Modal management
    openCustomerLookup() {
        if (window.POSModals && window.POSModals.openCustomerLookup) {
            window.POSModals.openCustomerLookup();
        }
    }
    
    openInventorySearch() {
        if (window.POSModals && window.POSModals.openInventorySearch) {
            window.POSModals.openInventorySearch();
        }
    }
    
    openCalculator() {
        if (window.POSModals && window.POSModals.openCalculator) {
            window.POSModals.openCalculator();
        }
    }
    
    closeAllModals() {
        // Close any open modals
        const modals = document.querySelectorAll('[x-show="showModal"]');
        modals.forEach(modal => {
            const alpineData = modal.__x?.$data;
            if (alpineData && alpineData.showModal) {
                alpineData.closeModal();
            }
        });
    }
    
    // Transaction management
    async completeTransaction() {
        // This would be called from the Alpine.js component
        // Implementation depends on the current transaction state
        console.log('Complete transaction requested');
    }
    
    // Barcode scanning (if supported)
    async startBarcodeScanning() {
        if ('BarcodeDetector' in window) {
            try {
                const barcodeDetector = new BarcodeDetector({
                    formats: ['code_128', 'code_39', 'ean_13', 'ean_8']
                });
                
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: 'environment' }
                });
                
                // Implementation would continue with video processing
                console.log('Barcode scanning started');
                
            } catch (error) {
                console.error('Barcode scanning not supported:', error);
                this.showNotification('اسکن بارکد پشتیبانی نمی‌شود', 'warning');
            }
        } else {
            this.showNotification('اسکن بارکد در این مرورگر پشتیبانی نمی‌شود', 'warning');
        }
    }
    
    // Print functionality
    async printReceipt(transactionId) {
        try {
            // Open print window
            const printWindow = window.open(`/pos/invoice/${transactionId}/pdf/`, '_blank');
            
            if (printWindow) {
                printWindow.onload = () => {
                    printWindow.print();
                };
            } else {
                throw new Error('Popup blocked');
            }
            
        } catch (error) {
            console.error('Print failed:', error);
            this.showNotification('خطا در چاپ فاکتور', 'error');
        }
    }
    
    // Performance monitoring
    measurePerformance(operation, fn) {
        const start = performance.now();
        const result = fn();
        const end = performance.now();
        
        console.log(`${operation} took ${end - start} milliseconds`);
        
        // Log slow operations
        if (end - start > 1000) {
            console.warn(`Slow operation detected: ${operation}`);
        }
        
        return result;
    }
}

// Initialize POS Interface
window.POSInterface = new POSInterface();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = POSInterface;
}