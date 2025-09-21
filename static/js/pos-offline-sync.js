/**
 * POS Offline Sync JavaScript
 * Enhanced offline functionality for POS system with sync queue management
 */

class POSOfflineSync {
    constructor() {
        this.isOnline = navigator.onLine;
        this.offlineQueue = [];
        this.syncInProgress = false;
        this.deviceId = this.getDeviceId();
        this.lastSyncTime = null;
        this.syncConflicts = [];
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadOfflineQueue();
        this.startPeriodicSync();
        this.updateConnectionStatus();
        
        console.log('POS Offline Sync initialized');
    }
    
    setupEventListeners() {
        // Online/offline status
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.updateConnectionStatus();
            this.autoSync();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.updateConnectionStatus();
        });
        
        // Listen for new offline transactions
        window.addEventListener('transaction-created-offline', (event) => {
            this.addToOfflineQueue(event.detail.transaction);
        });
        
        // Listen for manual sync requests
        window.addEventListener('manual-sync-requested', () => {
            this.performSync();
        });
        
        // Listen for conflict resolution
        window.addEventListener('conflicts-resolved', (event) => {
            this.handleConflictResolution(event.detail.results);
        });
    }
    
    getDeviceId() {
        let deviceId = localStorage.getItem('pos_device_id');
        if (!deviceId) {
            deviceId = 'POS-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('pos_device_id', deviceId);
        }
        return deviceId;
    }
    
    loadOfflineQueue() {
        const savedQueue = localStorage.getItem('pos_offline_queue');
        if (savedQueue) {
            try {
                this.offlineQueue = JSON.parse(savedQueue);
                this.updateQueueStatus();
            } catch (error) {
                console.error('Error loading offline queue:', error);
                this.offlineQueue = [];
            }
        }
    }
    
    saveOfflineQueue() {
        try {
            localStorage.setItem('pos_offline_queue', JSON.stringify(this.offlineQueue));
            this.updateQueueStatus();
        } catch (error) {
            console.error('Error saving offline queue:', error);
        }
    }
    
    addToOfflineQueue(transaction) {
        // Add offline metadata
        transaction.offline_id = this.generateOfflineId();
        transaction.offline_timestamp = Date.now();
        transaction.device_id = this.deviceId;
        transaction.sync_status = 'pending';
        
        this.offlineQueue.push(transaction);
        this.saveOfflineQueue();
        
        // Show notification
        this.showNotification('تراکنش در صف آفلاین ذخیره شد', 'info');
        
        // Dispatch event for UI updates
        window.dispatchEvent(new CustomEvent('offline-queue-updated', {
            detail: { queueLength: this.offlineQueue.length }
        }));
    }
    
    generateOfflineId() {
        return 'offline_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    updateConnectionStatus() {
        // Dispatch event for UI components
        window.dispatchEvent(new CustomEvent('connection-status-changed', {
            detail: { 
                isOnline: this.isOnline,
                pendingCount: this.getPendingCount(),
                lastSyncTime: this.lastSyncTime
            }
        }));
    }
    
    updateQueueStatus() {
        // Dispatch event for queue status updates
        window.dispatchEvent(new CustomEvent('sync-queue-status-updated', {
            detail: {
                pendingCount: this.getPendingCount(),
                syncedCount: this.getSyncedCount(),
                failedCount: this.getFailedCount(),
                queueSize: this.calculateQueueSize()
            }
        }));
    }
    
    getPendingCount() {
        return this.offlineQueue.filter(t => 
            !t.sync_status || t.sync_status === 'pending'
        ).length;
    }
    
    getSyncedCount() {
        return this.offlineQueue.filter(t => 
            t.sync_status === 'synced'
        ).length;
    }
    
    getFailedCount() {
        return this.offlineQueue.filter(t => 
            t.sync_status === 'failed'
        ).length;
    }
    
    calculateQueueSize() {
        return JSON.stringify(this.offlineQueue).length;
    }
    
    async autoSync() {
        if (!this.isOnline || this.syncInProgress || this.getPendingCount() === 0) {
            return;
        }
        
        // Auto-sync with delay to avoid immediate sync on connection
        setTimeout(() => {
            this.performSync();
        }, 2000);
    }
    
    async performSync() {
        if (this.syncInProgress || !this.isOnline) {
            return;
        }
        
        const pendingTransactions = this.offlineQueue.filter(t => 
            !t.sync_status || t.sync_status === 'pending'
        );
        
        if (pendingTransactions.length === 0) {
            return;
        }
        
        this.syncInProgress = true;
        
        // Dispatch sync start event
        window.dispatchEvent(new CustomEvent('sync-started', {
            detail: { transactionCount: pendingTransactions.length }
        }));
        
        try {
            const response = await fetch('/pos/api/offline/sync/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    device_id: this.deviceId,
                    device_name: 'POS Terminal',
                    transactions: pendingTransactions
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.handleSyncSuccess(data.sync_results);
            } else {
                throw new Error(data.error || 'Sync failed');
            }
            
        } catch (error) {
            this.handleSyncError(error.message);
        } finally {
            this.syncInProgress = false;
            
            // Dispatch sync end event
            window.dispatchEvent(new CustomEvent('sync-completed', {
                detail: { success: true }
            }));
        }
    }
    
    handleSyncSuccess(syncResults) {
        const syncedIds = syncResults.synced || [];
        const failedResults = syncResults.failed || [];
        const conflicts = syncResults.conflicts || [];
        
        // Update synced transactions
        syncedIds.forEach(syncedId => {
            const transaction = this.offlineQueue.find(t => t.offline_id === syncedId);
            if (transaction) {
                transaction.sync_status = 'synced';
                transaction.synced_at = new Date().toISOString();
            }
        });
        
        // Update failed transactions
        failedResults.forEach(failedResult => {
            const transaction = this.offlineQueue.find(t => t.offline_id === failedResult.offline_id);
            if (transaction) {
                transaction.sync_status = 'failed';
                transaction.sync_error = failedResult.error;
            }
        });
        
        this.lastSyncTime = new Date();
        this.saveOfflineQueue();
        
        // Show success notification
        if (syncedIds.length > 0) {
            this.showNotification(
                `${syncedIds.length} تراکنش با موفقیت همگام‌سازی شد`,
                'success'
            );
        }
        
        // Handle conflicts if any
        if (conflicts.length > 0) {
            this.handleSyncConflicts(conflicts);
        }
        
        // Show failed notification
        if (failedResults.length > 0) {
            this.showNotification(
                `${failedResults.length} تراکنش همگام‌سازی نشد`,
                'warning'
            );
        }
    }
    
    handleSyncError(errorMessage) {
        this.showNotification('خطا در همگام‌سازی: ' + errorMessage, 'error');
        
        // Dispatch error event
        window.dispatchEvent(new CustomEvent('sync-error', {
            detail: { error: errorMessage }
        }));
    }
    
    handleSyncConflicts(conflicts) {
        this.syncConflicts = conflicts;
        
        // Dispatch conflict detection event
        window.dispatchEvent(new CustomEvent('sync-conflicts-detected', {
            detail: { conflicts }
        }));
    }
    
    handleConflictResolution(resolutionResults) {
        // Update transactions based on resolution results
        Object.entries(resolutionResults).forEach(([offlineId, result]) => {
            const transaction = this.offlineQueue.find(t => t.offline_id === offlineId);
            if (transaction) {
                if (result.success) {
                    transaction.sync_status = 'synced';
                    transaction.synced_at = new Date().toISOString();
                } else {
                    transaction.sync_status = 'failed';
                    transaction.sync_error = result.error;
                }
            }
        });
        
        this.saveOfflineQueue();
        this.syncConflicts = [];
        
        this.showNotification('تعارض‌ها حل شدند', 'success');
    }
    
    async syncSingleTransaction(offlineId) {
        const transaction = this.offlineQueue.find(t => t.offline_id === offlineId);
        if (!transaction || this.syncInProgress || !this.isOnline) {
            return false;
        }
        
        this.syncInProgress = true;
        
        try {
            const response = await fetch('/pos/api/offline/sync/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    device_id: this.deviceId,
                    device_name: 'POS Terminal',
                    transactions: [transaction]
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.handleSyncSuccess(data.sync_results);
                return true;
            } else {
                throw new Error(data.error || 'Sync failed');
            }
            
        } catch (error) {
            transaction.sync_status = 'failed';
            transaction.sync_error = error.message;
            this.saveOfflineQueue();
            
            this.showNotification('خطا در همگام‌سازی تراکنش: ' + error.message, 'error');
            return false;
        } finally {
            this.syncInProgress = false;
        }
    }
    
    removeFromQueue(offlineId) {
        this.offlineQueue = this.offlineQueue.filter(t => t.offline_id !== offlineId);
        this.saveOfflineQueue();
        
        this.showNotification('تراکنش از صف حذف شد', 'info');
    }
    
    clearSyncedTransactions() {
        this.offlineQueue = this.offlineQueue.filter(t => t.sync_status !== 'synced');
        this.saveOfflineQueue();
        
        this.showNotification('تراکنش‌های همگام‌سازی شده پاک شدند', 'success');
    }
    
    exportQueueData() {
        const dataStr = JSON.stringify(this.offlineQueue, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `pos_queue_${new Date().toISOString().slice(0, 10)}.json`;
        link.click();
        
        this.showNotification('صف همگام‌سازی صادر شد', 'success');
    }
    
    startPeriodicSync() {
        // Attempt sync every 30 seconds when online
        setInterval(() => {
            if (this.isOnline && !this.syncInProgress && this.getPendingCount() > 0) {
                this.autoSync();
            }
        }, 30000);
        
        // Update connection status every 5 seconds
        setInterval(() => {
            this.updateConnectionStatus();
        }, 5000);
    }
    
    // Utility methods
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : window.zargarConfig?.csrfToken || '';
    }
    
    showNotification(message, type = 'info') {
        if (window.POSInterface && window.POSInterface.showNotification) {
            window.POSInterface.showNotification(message, type);
        } else if (window.themeData && window.themeData.showNotification) {
            window.themeData.showNotification(message, type);
        } else {
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }
    
    // Public API methods
    getQueueSummary() {
        return {
            total: this.offlineQueue.length,
            pending: this.getPendingCount(),
            synced: this.getSyncedCount(),
            failed: this.getFailedCount(),
            queueSize: this.calculateQueueSize(),
            isOnline: this.isOnline,
            syncInProgress: this.syncInProgress,
            lastSyncTime: this.lastSyncTime
        };
    }
    
    getQueueItems() {
        return [...this.offlineQueue];
    }
    
    getPendingTransactions() {
        return this.offlineQueue.filter(t => 
            !t.sync_status || t.sync_status === 'pending'
        );
    }
    
    getSyncedTransactions() {
        return this.offlineQueue.filter(t => 
            t.sync_status === 'synced'
        );
    }
    
    getFailedTransactions() {
        return this.offlineQueue.filter(t => 
            t.sync_status === 'failed'
        );
    }
}

// Initialize POS Offline Sync
window.POSOfflineSync = new POSOfflineSync();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = POSOfflineSync;
}