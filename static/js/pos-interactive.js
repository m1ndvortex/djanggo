/**
 * Interactive POS Components for ZARGAR Jewelry SaaS Platform
 * Touch-optimized components with Persian RTL support and dual theme
 */

// POS Main Interface Component
Alpine.data('posInterface', () => ({
    // State
    cart: [],
    customer: null,
    goldPrice: 0,
    total: 0,
    discount: 0,
    paymentMethod: 'cash',
    isProcessing: false,
    
    // UI State
    showCustomerModal: false,
    showPaymentModal: false,
    showCalculator: false,
    activeTab: 'items',
    
    init() {
        this.loadGoldPrice();
        this.loadCart();
        
        // Watch for cart changes
        this.$watch('cart', () => {
            this.calculateTotal();
            this.saveCart();
        });
        
        // Watch for discount changes
        this.$watch('discount', () => {
            this.calculateTotal();
        });
    },
    
    // Cart Management
    addToCart(item) {
        const existingItem = this.cart.find(cartItem => cartItem.id === item.id);
        
        if (existingItem) {
            existingItem.quantity += 1;
        } else {
            this.cart.push({
                ...item,
                quantity: 1,
                unitPrice: item.price || this.calculateItemPrice(item)
            });
        }
        
        // Show success feedback
        this.showNotification('محصول به سبد خرید اضافه شد', 'success');
    },
    
    removeFromCart(itemId) {
        this.cart = this.cart.filter(item => item.id !== itemId);
        this.showNotification('محصول از سبد خرید حذف شد', 'info');
    },
    
    updateQuantity(itemId, quantity) {
        const item = this.cart.find(cartItem => cartItem.id === itemId);
        if (item) {
            if (quantity <= 0) {
                this.removeFromCart(itemId);
            } else {
                item.quantity = quantity;
            }
        }
    },
    
    clearCart() {
        this.cart = [];
        this.customer = null;
        this.discount = 0;
        this.showNotification('سبد خرید پاک شد', 'info');
    },
    
    // Price Calculations
    calculateItemPrice(item) {
        if (item.type === 'gold') {
            const purity = this.getKaratPurity(item.karat || 24);
            return (item.weight || 0) * purity * this.goldPrice + (item.workmanship || 0);
        }
        return item.price || 0;
    },
    
    calculateTotal() {
        const subtotal = this.cart.reduce((sum, item) => {
            return sum + (item.unitPrice * item.quantity);
        }, 0);
        
        this.total = subtotal - this.discount;
    },
    
    getKaratPurity(karat) {
        const purities = {
            24: 1.0,
            22: 0.916,
            21: 0.875,
            18: 0.750,
            14: 0.583
        };
        return purities[karat] || 1.0;
    },
    
    // Customer Management
    selectCustomer(customer) {
        this.customer = customer;
        this.showCustomerModal = false;
        this.showNotification(`مشتری ${customer.name} انتخاب شد`, 'success');
    },
    
    createQuickCustomer(name, phone) {
        const customer = {
            id: Date.now(),
            name: name,
            phone: phone,
            isQuick: true
        };
        
        this.selectCustomer(customer);
    },
    
    // Payment Processing
    async processPayment() {
        if (this.cart.length === 0) {
            this.showNotification('سبد خرید خالی است', 'error');
            return;
        }
        
        if (this.total <= 0) {
            this.showNotification('مبلغ فروش نامعتبر است', 'error');
            return;
        }
        
        this.isProcessing = true;
        
        try {
            const saleData = {
                customer: this.customer,
                items: this.cart,
                total: this.total,
                discount: this.discount,
                paymentMethod: this.paymentMethod,
                goldPrice: this.goldPrice
            };
            
            const response = await fetch('/api/pos/sales/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.zargarConfig.csrfToken
                },
                body: JSON.stringify(saleData)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showNotification('فروش با موفقیت ثبت شد', 'success');
                this.clearCart();
                this.showPaymentModal = false;
                
                // Print receipt if requested
                if (result.receiptUrl) {
                    this.printReceipt(result.receiptUrl);
                }
            } else {
                throw new Error(result.message || 'خطا در ثبت فروش');
            }
        } catch (error) {
            this.showNotification(error.message || 'خطا در ثبت فروش', 'error');
        } finally {
            this.isProcessing = false;
        }
    },
    
    // Receipt Management
    printReceipt(receiptUrl) {
        const printWindow = window.open(receiptUrl, '_blank');
        printWindow.onload = function() {
            printWindow.print();
        };
    },
    
    // Data Persistence
    saveCart() {
        localStorage.setItem('pos_cart', JSON.stringify({
            cart: this.cart,
            customer: this.customer,
            discount: this.discount
        }));
    },
    
    loadCart() {
        const saved = localStorage.getItem('pos_cart');
        if (saved) {
            try {
                const data = JSON.parse(saved);
                this.cart = data.cart || [];
                this.customer = data.customer || null;
                this.discount = data.discount || 0;
            } catch (e) {
                console.error('Failed to load cart:', e);
            }
        }
    },
    
    // Gold Price Management
    async loadGoldPrice() {
        try {
            const response = await fetch('/api/gold-prices/current/');
            const data = await response.json();
            this.goldPrice = data.price || 2500000;
        } catch (error) {
            console.error('Failed to load gold price:', error);
            this.goldPrice = 2500000; // Fallback
        }
    },
    
    // Utility Methods
    formatCurrency(amount) {
        if (!amount) return '۰ تومان';
        const formatted = new Intl.NumberFormat('fa-IR').format(Math.round(amount));
        return this.toPersianDigits(formatted) + ' تومان';
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
    get cartItemCount() {
        return this.cart.reduce((sum, item) => sum + item.quantity, 0);
    },
    
    get subtotal() {
        return this.cart.reduce((sum, item) => sum + (item.unitPrice * item.quantity), 0);
    },
    
    get hasCustomer() {
        return this.customer !== null;
    },
    
    get canProcessPayment() {
        return this.cart.length > 0 && this.total > 0 && !this.isProcessing;
    }
}));

// POS Calculator Component
Alpine.data('posCalculator', () => ({
    display: '0',
    previousValue: null,
    operation: null,
    waitingForOperand: false,
    
    inputDigit(digit) {
        if (this.waitingForOperand) {
            this.display = String(digit);
            this.waitingForOperand = false;
        } else {
            this.display = this.display === '0' ? String(digit) : this.display + digit;
        }
    },
    
    inputDecimal() {
        if (this.waitingForOperand) {
            this.display = '0.';
            this.waitingForOperand = false;
        } else if (this.display.indexOf('.') === -1) {
            this.display += '.';
        }
    },
    
    clear() {
        this.display = '0';
        this.previousValue = null;
        this.operation = null;
        this.waitingForOperand = false;
    },
    
    performOperation(nextOperation) {
        const inputValue = parseFloat(this.display);
        
        if (this.previousValue === null) {
            this.previousValue = inputValue;
        } else if (this.operation) {
            const currentValue = this.previousValue || 0;
            const newValue = this.calculate(currentValue, inputValue, this.operation);
            
            this.display = String(newValue);
            this.previousValue = newValue;
        }
        
        this.waitingForOperand = true;
        this.operation = nextOperation;
    },
    
    calculate(firstValue, secondValue, operation) {
        switch (operation) {
            case '+':
                return firstValue + secondValue;
            case '-':
                return firstValue - secondValue;
            case '*':
                return firstValue * secondValue;
            case '/':
                return firstValue / secondValue;
            case '=':
                return secondValue;
            default:
                return secondValue;
        }
    },
    
    equals() {
        const inputValue = parseFloat(this.display);
        
        if (this.previousValue !== null && this.operation) {
            const newValue = this.calculate(this.previousValue, inputValue, this.operation);
            this.display = String(newValue);
            this.previousValue = null;
            this.operation = null;
            this.waitingForOperand = true;
        }
    },
    
    get formattedDisplay() {
        const value = parseFloat(this.display);
        if (isNaN(value)) return '۰';
        
        const formatted = new Intl.NumberFormat('fa-IR').format(value);
        return this.toPersianDigits(formatted);
    },
    
    toPersianDigits(str) {
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return str.toString().replace(/\d/g, (digit) => persianDigits[parseInt(digit)]);
    }
}));

// POS Item Search Component
Alpine.data('posItemSearch', () => ({
    query: '',
    results: [],
    isOpen: false,
    loading: false,
    selectedIndex: -1,
    categories: [],
    selectedCategory: null,
    
    init() {
        this.loadCategories();
        
        this.$watch('query', (newQuery) => {
            if (newQuery.length >= 2) {
                this.debounceSearch();
            } else {
                this.results = [];
                this.isOpen = false;
            }
        });
    },
    
    async loadCategories() {
        try {
            const response = await fetch('/api/pos/categories/');
            const data = await response.json();
            this.categories = data.categories || [];
        } catch (error) {
            console.error('Failed to load categories:', error);
        }
    },
    
    debounceSearch() {
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            this.performSearch();
        }, 300);
    },
    
    async performSearch() {
        if (!this.query || this.query.length < 2) return;
        
        this.loading = true;
        try {
            const params = new URLSearchParams({
                q: this.query,
                category: this.selectedCategory || ''
            });
            
            const response = await fetch(`/api/pos/items/search/?${params}`);
            const data = await response.json();
            
            this.results = data.results || [];
            this.isOpen = this.results.length > 0;
            this.selectedIndex = -1;
        } catch (error) {
            console.error('Search failed:', error);
            this.results = [];
            this.isOpen = false;
        } finally {
            this.loading = false;
        }
    },
    
    selectItem(item) {
        this.$dispatch('item-selected', { item });
        this.query = '';
        this.results = [];
        this.isOpen = false;
        this.selectedIndex = -1;
    },
    
    handleKeydown(e) {
        if (!this.isOpen) return;
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, this.results.length - 1);
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                break;
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0 && this.results[this.selectedIndex]) {
                    this.selectItem(this.results[this.selectedIndex]);
                }
                break;
            case 'Escape':
                this.isOpen = false;
                this.selectedIndex = -1;
                break;
        }
    },
    
    filterByCategory(categoryId) {
        this.selectedCategory = categoryId;
        if (this.query) {
            this.performSearch();
        }
    },
    
    formatPrice(item) {
        let price = item.price;
        
        if (item.type === 'gold') {
            // Calculate gold price dynamically
            const goldPrice = Alpine.store('zargar')?.goldPrice || 2500000;
            const purity = this.getKaratPurity(item.karat || 24);
            price = (item.weight || 0) * purity * goldPrice + (item.workmanship || 0);
        }
        
        const formatted = new Intl.NumberFormat('fa-IR').format(Math.round(price));
        return this.toPersianDigits(formatted) + ' تومان';
    },
    
    getKaratPurity(karat) {
        const purities = {
            24: 1.0,
            22: 0.916,
            21: 0.875,
            18: 0.750,
            14: 0.583
        };
        return purities[karat] || 1.0;
    },
    
    toPersianDigits(str) {
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return str.toString().replace(/\d/g, (digit) => persianDigits[parseInt(digit)]);
    }
}));

// POS Customer Search Component
Alpine.data('posCustomerSearch', () => ({
    query: '',
    results: [],
    isOpen: false,
    loading: false,
    selectedIndex: -1,
    
    init() {
        this.$watch('query', (newQuery) => {
            if (newQuery.length >= 2) {
                this.debounceSearch();
            } else {
                this.results = [];
                this.isOpen = false;
            }
        });
    },
    
    debounceSearch() {
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            this.performSearch();
        }, 300);
    },
    
    async performSearch() {
        if (!this.query || this.query.length < 2) return;
        
        this.loading = true;
        try {
            const response = await fetch(`/api/pos/customers/search/?q=${encodeURIComponent(this.query)}`);
            const data = await response.json();
            
            this.results = data.results || [];
            this.isOpen = this.results.length > 0;
            this.selectedIndex = -1;
        } catch (error) {
            console.error('Customer search failed:', error);
            this.results = [];
            this.isOpen = false;
        } finally {
            this.loading = false;
        }
    },
    
    selectCustomer(customer) {
        this.$dispatch('customer-selected', { customer });
        this.query = customer.name;
        this.results = [];
        this.isOpen = false;
        this.selectedIndex = -1;
    },
    
    handleKeydown(e) {
        if (!this.isOpen) return;
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, this.results.length - 1);
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                break;
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0 && this.results[this.selectedIndex]) {
                    this.selectCustomer(this.results[this.selectedIndex]);
                }
                break;
            case 'Escape':
                this.isOpen = false;
                this.selectedIndex = -1;
                break;
        }
    },
    
    createNewCustomer() {
        this.$dispatch('create-customer', { name: this.query });
        this.query = '';
        this.results = [];
        this.isOpen = false;
    }
}));

// POS Quick Actions Component
Alpine.data('posQuickActions', () => ({
    actions: [
        { id: 'hold', label: 'نگهداری فروش', icon: 'pause', color: 'yellow' },
        { id: 'recall', label: 'بازیابی فروش', icon: 'play', color: 'blue' },
        { id: 'void', label: 'لغو فروش', icon: 'x', color: 'red' },
        { id: 'discount', label: 'تخفیف', icon: 'percent', color: 'green' },
        { id: 'customer', label: 'مشتری', icon: 'user', color: 'purple' },
        { id: 'calculator', label: 'ماشین حساب', icon: 'calculator', color: 'gray' }
    ],
    
    executeAction(actionId) {
        switch (actionId) {
            case 'hold':
                this.$dispatch('hold-sale');
                break;
            case 'recall':
                this.$dispatch('recall-sale');
                break;
            case 'void':
                this.$dispatch('void-sale');
                break;
            case 'discount':
                this.$dispatch('apply-discount');
                break;
            case 'customer':
                this.$dispatch('select-customer');
                break;
            case 'calculator':
                this.$dispatch('show-calculator');
                break;
        }
    }
}));

// Initialize POS components when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Auto-initialize POS interface if present
    const posContainer = document.querySelector('[data-pos-interface]');
    if (posContainer && !posContainer._x_dataStack) {
        Alpine.initTree(posContainer);
    }
});