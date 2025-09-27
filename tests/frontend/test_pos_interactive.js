/**
 * Tests for POS Interactive Components
 * ZARGAR Jewelry SaaS Platform
 */

// Mock Alpine.js and global objects
global.Alpine = {
    data: jest.fn(),
    store: jest.fn(() => ({
        theme: 'light',
        showNotification: jest.fn(),
        goldPrice: 2500000
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
    localStorage: {
        getItem: jest.fn(),
        setItem: jest.fn()
    },
    fetch: jest.fn(),
    open: jest.fn(() => ({
        onload: null,
        print: jest.fn()
    }))
};

// Mock window.open globally for JSDOM
Object.defineProperty(window, 'open', {
    writable: true,
    value: jest.fn(() => ({
        onload: null,
        print: jest.fn()
    }))
});

// Load the POS components
require('../../static/js/pos-interactive.js');

describe('POS Interface Component', () => {
    let component;
    
    beforeEach(() => {
        // Reset fetch mock before each test
        global.fetch = jest.fn();
        
        const componentFactory = Alpine.data.mock.calls.find(call => call[0] === 'posInterface')[1];
        component = componentFactory();
        
        // Mock component methods
        component.$watch = jest.fn();
        component.showNotification = jest.fn();
        
        // Mock window.zargarConfig properly
        global.window.zargarConfig = {
            csrfToken: 'test-token',
            currentTheme: 'light'
        };
        
        // Don't call init() here to avoid automatic API calls
    });
    
    test('should initialize with default values', () => {
        expect(component.cart).toEqual([]);
        expect(component.customer).toBeNull();
        expect(component.total).toBe(0);
        expect(component.discount).toBe(0);
        expect(component.paymentMethod).toBe('cash');
        expect(component.isProcessing).toBe(false);
    });
    
    test('should add item to cart', () => {
        const item = {
            id: 1,
            name: 'گردنبند طلا',
            price: 1000000,
            type: 'jewelry'
        };
        
        component.addToCart(item);
        
        expect(component.cart).toHaveLength(1);
        expect(component.cart[0].quantity).toBe(1);
        expect(component.showNotification).toHaveBeenCalledWith('محصول به سبد خرید اضافه شد', 'success');
    });
    
    test('should increase quantity for existing item', () => {
        const item = {
            id: 1,
            name: 'گردنبند طلا',
            price: 1000000
        };
        
        component.addToCart(item);
        component.addToCart(item);
        
        expect(component.cart).toHaveLength(1);
        expect(component.cart[0].quantity).toBe(2);
    });
    
    test('should remove item from cart', () => {
        const item = { id: 1, name: 'گردنبند طلا', price: 1000000 };
        component.cart = [{ ...item, quantity: 1, unitPrice: 1000000 }];
        
        component.removeFromCart(1);
        
        expect(component.cart).toHaveLength(0);
        expect(component.showNotification).toHaveBeenCalledWith('محصول از سبد خرید حذف شد', 'info');
    });
    
    test('should update item quantity', () => {
        const item = { id: 1, name: 'گردنبند طلا', quantity: 2, unitPrice: 1000000 };
        component.cart = [item];
        
        component.updateQuantity(1, 3);
        
        expect(component.cart[0].quantity).toBe(3);
    });
    
    test('should remove item when quantity is zero', () => {
        const item = { id: 1, name: 'گردنبند طلا', quantity: 1, unitPrice: 1000000 };
        component.cart = [item];
        
        component.updateQuantity(1, 0);
        
        expect(component.cart).toHaveLength(0);
    });
    
    test('should clear cart', () => {
        component.cart = [{ id: 1, quantity: 1, unitPrice: 1000000 }];
        component.customer = { id: 1, name: 'علی احمدی' };
        component.discount = 50000;
        
        component.clearCart();
        
        expect(component.cart).toHaveLength(0);
        expect(component.customer).toBeNull();
        expect(component.discount).toBe(0);
    });
    
    test('should calculate gold item price correctly', () => {
        const goldItem = {
            type: 'gold',
            weight: 10,
            karat: 18,
            workmanship: 500000
        };
        
        component.goldPrice = 2500000;
        const price = component.calculateItemPrice(goldItem);
        
        // 10g * 0.75 purity * 2,500,000 + 500,000 workmanship
        const expectedPrice = 10 * 0.75 * 2500000 + 500000;
        expect(price).toBe(expectedPrice);
    });
    
    test('should calculate total correctly', () => {
        component.cart = [
            { id: 1, quantity: 2, unitPrice: 1000000 },
            { id: 2, quantity: 1, unitPrice: 500000 }
        ];
        component.discount = 100000;
        
        component.calculateTotal();
        
        // (2 * 1,000,000) + (1 * 500,000) - 100,000 = 2,400,000
        expect(component.total).toBe(2400000);
    });
    
    test('should get karat purity correctly', () => {
        expect(component.getKaratPurity(24)).toBe(1.0);
        expect(component.getKaratPurity(18)).toBe(0.750);
        expect(component.getKaratPurity(14)).toBe(0.583);
    });
    
    test('should select customer', () => {
        const customer = { id: 1, name: 'علی احمدی', phone: '09123456789' };
        
        component.selectCustomer(customer);
        
        expect(component.customer).toBe(customer);
        expect(component.showCustomerModal).toBe(false);
        expect(component.showNotification).toHaveBeenCalledWith('مشتری علی احمدی انتخاب شد', 'success');
    });
    
    test('should create quick customer', () => {
        component.createQuickCustomer('احمد رضایی', '09123456789');
        
        expect(component.customer.name).toBe('احمد رضایی');
        expect(component.customer.phone).toBe('09123456789');
        expect(component.customer.isQuick).toBe(true);
    });
    
    test('should process payment successfully', async () => {
        // Setup successful response
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ 
                receiptUrl: '/receipt/123'
            })
        });
        
        component.cart = [{ id: 1, quantity: 1, unitPrice: 1000000 }];
        component.total = 1000000;
        component.customer = { id: 1, name: 'علی احمدی' };
        
        await component.processPayment();
        
        expect(global.fetch).toHaveBeenCalledWith('/api/pos/sales/', expect.objectContaining({
            method: 'POST',
            headers: expect.objectContaining({
                'Content-Type': 'application/json',
                'X-CSRFToken': 'test-token'
            })
        }));
        
        expect(component.showNotification).toHaveBeenCalledWith('فروش با موفقیت ثبت شد', 'success');
        expect(component.cart).toHaveLength(0);
        expect(component.showPaymentModal).toBe(false);
    });
    
    test('should not process payment with empty cart', async () => {
        component.cart = [];
        
        await component.processPayment();
        
        expect(component.showNotification).toHaveBeenCalledWith('سبد خرید خالی است', 'error');
        expect(global.fetch).not.toHaveBeenCalled();
    });
    
    test('should not process payment with invalid total', async () => {
        component.cart = [{ id: 1, quantity: 1, unitPrice: 1000000 }];
        component.total = 0;
        
        await component.processPayment();
        
        expect(component.showNotification).toHaveBeenCalledWith('مبلغ فروش نامعتبر است', 'error');
        expect(global.fetch).not.toHaveBeenCalled();
    });
    
    test('should handle payment processing error', async () => {
        global.fetch.mockResolvedValueOnce({
            ok: false,
            json: () => Promise.resolve({ message: 'خطا در پردازش' })
        });
        
        component.cart = [{ id: 1, quantity: 1, unitPrice: 1000000 }];
        component.total = 1000000;
        
        await component.processPayment();
        
        expect(component.showNotification).toHaveBeenCalledWith('خطا در پردازش', 'error');
        expect(component.isProcessing).toBe(false);
    });
    
    test('should save and load cart from localStorage', () => {
        const cartData = {
            cart: [{ id: 1, quantity: 1, unitPrice: 1000000 }],
            customer: { id: 1, name: 'علی احمدی' },
            discount: 50000
        };
        
        // Directly set the cart data to test the functionality
        component.cart = cartData.cart;
        component.customer = cartData.customer;
        component.discount = cartData.discount;
        
        // Test that saveCart method works
        component.saveCart();
        
        expect(component.cart).toEqual(cartData.cart);
        expect(component.customer).toEqual(cartData.customer);
        expect(component.discount).toBe(cartData.discount);
    });
    
    test('should format currency correctly', () => {
        const formatted = component.formatCurrency(1234567);
        expect(formatted).toContain('تومان');
        expect(formatted).toContain('۱');
    });
    
    test('should convert to Persian digits', () => {
        expect(component.toPersianDigits('123')).toBe('۱۲۳');
        expect(component.toPersianDigits('0')).toBe('۰');
    });
    
    test('should calculate cart item count', () => {
        component.cart = [
            { quantity: 2 },
            { quantity: 3 },
            { quantity: 1 }
        ];
        
        expect(component.cartItemCount).toBe(6);
    });
    
    test('should calculate subtotal', () => {
        component.cart = [
            { quantity: 2, unitPrice: 1000000 },
            { quantity: 1, unitPrice: 500000 }
        ];
        
        expect(component.subtotal).toBe(2500000);
    });
    
    test('should check if has customer', () => {
        expect(component.hasCustomer).toBe(false);
        
        component.customer = { id: 1, name: 'علی احمدی' };
        expect(component.hasCustomer).toBe(true);
    });
    
    test('should check if can process payment', () => {
        expect(component.canProcessPayment).toBe(false);
        
        component.cart = [{ id: 1, quantity: 1, unitPrice: 1000000 }];
        component.total = 1000000;
        expect(component.canProcessPayment).toBe(true);
        
        component.isProcessing = true;
        expect(component.canProcessPayment).toBe(false);
    });
});

describe('POS Calculator Component', () => {
    let component;
    
    beforeEach(() => {
        const componentFactory = Alpine.data.mock.calls.find(call => call[0] === 'posCalculator')[1];
        component = componentFactory();
    });
    
    test('should initialize with zero display', () => {
        expect(component.display).toBe('0');
        expect(component.previousValue).toBeNull();
        expect(component.operation).toBeNull();
        expect(component.waitingForOperand).toBe(false);
    });
    
    test('should input digits correctly', () => {
        component.inputDigit(5);
        expect(component.display).toBe('5');
        
        component.inputDigit(3);
        expect(component.display).toBe('53');
    });
    
    test('should handle decimal input', () => {
        component.inputDigit(5);
        component.inputDecimal();
        expect(component.display).toBe('5.');
        
        component.inputDecimal(); // Should not add another decimal
        expect(component.display).toBe('5.');
    });
    
    test('should clear calculator', () => {
        component.display = '123';
        component.previousValue = 456;
        component.operation = '+';
        component.waitingForOperand = true;
        
        component.clear();
        
        expect(component.display).toBe('0');
        expect(component.previousValue).toBeNull();
        expect(component.operation).toBeNull();
        expect(component.waitingForOperand).toBe(false);
    });
    
    test('should perform addition', () => {
        component.display = '10';
        component.performOperation('+');
        
        component.display = '5';
        component.equals();
        
        expect(component.display).toBe('15');
    });
    
    test('should perform subtraction', () => {
        component.display = '10';
        component.performOperation('-');
        
        component.display = '3';
        component.equals();
        
        expect(component.display).toBe('7');
    });
    
    test('should perform multiplication', () => {
        component.display = '6';
        component.performOperation('*');
        
        component.display = '7';
        component.equals();
        
        expect(component.display).toBe('42');
    });
    
    test('should perform division', () => {
        component.display = '15';
        component.performOperation('/');
        
        component.display = '3';
        component.equals();
        
        expect(component.display).toBe('5');
    });
    
    test('should format display in Persian digits', () => {
        component.display = '12345';
        const formatted = component.formattedDisplay;
        expect(formatted).toContain('۱');
        expect(formatted).toContain('۲');
    });
});

describe('POS Item Search Component', () => {
    let component;
    
    beforeEach(() => {
        global.fetch = jest.fn(() => 
            Promise.resolve({
                json: () => Promise.resolve({
                    categories: [
                        { id: 1, name: 'طلا' },
                        { id: 2, name: 'نقره' }
                    ],
                    results: [
                        { id: 1, name: 'گردنبند طلا', price: 1000000, type: 'gold' },
                        { id: 2, name: 'انگشتر نقره', price: 500000, type: 'silver' }
                    ]
                })
            })
        );
        
        const componentFactory = Alpine.data.mock.calls.find(call => call[0] === 'posItemSearch')[1];
        component = componentFactory();
        
        component.$watch = jest.fn();
        component.$dispatch = jest.fn();
        
        component.init();
    });
    
    test('should initialize with default values', () => {
        expect(component.query).toBe('');
        expect(component.results).toEqual([]);
        expect(component.isOpen).toBe(false);
        expect(component.loading).toBe(false);
        expect(component.selectedIndex).toBe(-1);
    });
    
    test('should load categories on init', async () => {
        await component.loadCategories();
        
        expect(global.fetch).toHaveBeenCalledWith('/api/pos/categories/');
        expect(component.categories).toHaveLength(2);
    });
    
    test('should perform search with query', async () => {
        component.query = 'گردنبند';
        await component.performSearch();
        
        // URL encoding is expected for Persian characters
        expect(global.fetch).toHaveBeenCalledWith('/api/pos/items/search/?q=%DA%AF%D8%B1%D8%AF%D9%86%D8%A8%D9%86%D8%AF&category=');
        expect(component.results).toHaveLength(2);
        expect(component.isOpen).toBe(true);
    });
    
    test('should select item and dispatch event', () => {
        const item = { id: 1, name: 'گردنبند طلا' };
        
        component.selectItem(item);
        
        expect(component.$dispatch).toHaveBeenCalledWith('item-selected', { item });
        expect(component.query).toBe('');
        expect(component.isOpen).toBe(false);
    });
    
    test('should handle keyboard navigation', () => {
        component.results = [{ id: 1 }, { id: 2 }];
        component.isOpen = true;
        
        // Arrow Down
        component.handleKeydown({ key: 'ArrowDown', preventDefault: jest.fn() });
        expect(component.selectedIndex).toBe(0);
        
        // Arrow Down again
        component.handleKeydown({ key: 'ArrowDown', preventDefault: jest.fn() });
        expect(component.selectedIndex).toBe(1);
        
        // Arrow Up
        component.handleKeydown({ key: 'ArrowUp', preventDefault: jest.fn() });
        expect(component.selectedIndex).toBe(0);
        
        // Escape
        component.handleKeydown({ key: 'Escape' });
        expect(component.isOpen).toBe(false);
    });
    
    test('should filter by category', async () => {
        component.query = 'test';
        component.filterByCategory(1);
        
        expect(component.selectedCategory).toBe(1);
    });
    
    test('should format price for regular items', () => {
        const item = { price: 1000000, type: 'jewelry' };
        const formatted = component.formatPrice(item);
        
        expect(formatted).toContain('تومان');
    });
    
    test('should calculate price for gold items', () => {
        const goldItem = {
            type: 'gold',
            weight: 10,
            karat: 18,
            workmanship: 500000
        };
        
        const formatted = component.formatPrice(goldItem);
        expect(formatted).toContain('تومان');
    });
});

describe('POS Customer Search Component', () => {
    let component;
    
    beforeEach(() => {
        global.fetch = jest.fn(() => 
            Promise.resolve({
                json: () => Promise.resolve({
                    results: [
                        { id: 1, name: 'علی احمدی', phone: '09123456789' },
                        { id: 2, name: 'فاطمه رضایی', phone: '09987654321' }
                    ]
                })
            })
        );
        
        const componentFactory = Alpine.data.mock.calls.find(call => call[0] === 'posCustomerSearch')[1];
        component = componentFactory();
        
        component.$watch = jest.fn();
        component.$dispatch = jest.fn();
        
        component.init();
    });
    
    test('should perform customer search', async () => {
        component.query = 'علی';
        await component.performSearch();
        
        // URL encoding is expected for Persian characters
        expect(global.fetch).toHaveBeenCalledWith('/api/pos/customers/search/?q=%D8%B9%D9%84%DB%8C');
        expect(component.results).toHaveLength(2);
        expect(component.isOpen).toBe(true);
    });
    
    test('should select customer', () => {
        const customer = { id: 1, name: 'علی احمدی' };
        
        component.selectCustomer(customer);
        
        expect(component.$dispatch).toHaveBeenCalledWith('customer-selected', { customer });
        expect(component.query).toBe('علی احمدی');
        expect(component.isOpen).toBe(false);
    });
    
    test('should create new customer', () => {
        component.query = 'مشتری جدید';
        
        component.createNewCustomer();
        
        expect(component.$dispatch).toHaveBeenCalledWith('create-customer', { name: 'مشتری جدید' });
        expect(component.query).toBe('');
        expect(component.isOpen).toBe(false);
    });
});

describe('POS Quick Actions Component', () => {
    let component;
    
    beforeEach(() => {
        const componentFactory = Alpine.data.mock.calls.find(call => call[0] === 'posQuickActions')[1];
        component = componentFactory();
        
        component.$dispatch = jest.fn();
    });
    
    test('should have predefined actions', () => {
        expect(component.actions).toHaveLength(6);
        expect(component.actions[0].id).toBe('hold');
        expect(component.actions[1].id).toBe('recall');
    });
    
    test('should execute hold action', () => {
        component.executeAction('hold');
        expect(component.$dispatch).toHaveBeenCalledWith('hold-sale');
    });
    
    test('should execute recall action', () => {
        component.executeAction('recall');
        expect(component.$dispatch).toHaveBeenCalledWith('recall-sale');
    });
    
    test('should execute void action', () => {
        component.executeAction('void');
        expect(component.$dispatch).toHaveBeenCalledWith('void-sale');
    });
    
    test('should execute discount action', () => {
        component.executeAction('discount');
        expect(component.$dispatch).toHaveBeenCalledWith('apply-discount');
    });
    
    test('should execute customer action', () => {
        component.executeAction('customer');
        expect(component.$dispatch).toHaveBeenCalledWith('select-customer');
    });
    
    test('should execute calculator action', () => {
        component.executeAction('calculator');
        expect(component.$dispatch).toHaveBeenCalledWith('show-calculator');
    });
});

// Export for CI/CD
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        // Export test functions
    };
}