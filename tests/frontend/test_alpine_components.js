/**
 * Tests for Alpine.js Components
 * ZARGAR Jewelry SaaS Platform
 */

// Mock Alpine.js for testing
global.Alpine = {
    data: jest.fn(),
    store: jest.fn(() => ({
        theme: 'light',
        showNotification: jest.fn(),
        goldPrice: 2500000
    })),
    initTree: jest.fn()
};

// Mock fetch globally
global.fetch = jest.fn();

// Mock DOM methods
global.document = {
    addEventListener: jest.fn(),
    querySelector: jest.fn(),
    querySelectorAll: jest.fn(() => []),
    createElement: jest.fn(() => ({
        classList: { add: jest.fn(), remove: jest.fn() },
        setAttribute: jest.fn(),
        appendChild: jest.fn()
    })),
    body: {
        appendChild: jest.fn(),
        addEventListener: jest.fn()
    },
    documentElement: {
        classList: { toggle: jest.fn() }
    }
};

global.window = {
    zargarConfig: {
        csrfToken: 'test-token',
        currentTheme: 'light',
        isAuthenticated: true,
        userRole: 'owner'
    },
    localStorage: {
        getItem: jest.fn(),
        setItem: jest.fn()
    },
    fetch: jest.fn(),
    WebSocket: jest.fn()
};

// Load the components
require('../../static/js/alpine-components.js');

describe('Persian Date Picker Component', () => {
    let component;
    
    beforeEach(() => {
        // Get the component factory function
        const componentFactory = Alpine.data.mock.calls.find(call => call[0] === 'persianDatePicker')[1];
        component = componentFactory();
        
        // Mock $el, $nextTick, $watch, $dispatch
        component.$el = { contains: jest.fn(() => false) };
        component.$nextTick = jest.fn(cb => cb());
        component.$watch = jest.fn();
        component.$dispatch = jest.fn();
        
        component.init();
    });
    
    test('should initialize with current date', () => {
        expect(component.currentMonth).toBeDefined();
        expect(component.currentYear).toBeDefined();
        // Days array is populated after generateCalendar() is called in init()
        expect(component.days).toBeDefined();
        expect(Array.isArray(component.days)).toBe(true);
    });
    
    test('should toggle calendar visibility', () => {
        expect(component.isOpen).toBe(false);
        component.toggle();
        expect(component.isOpen).toBe(true);
        component.toggle();
        expect(component.isOpen).toBe(false);
    });
    
    test('should select date correctly', () => {
        const day = { number: 15, disabled: false };
        component.currentYear = 1403;
        component.currentMonth = 6;
        
        component.selectDate(day);
        
        expect(component.selectedDate).toBe('1403/06/15');
        expect(component.isOpen).toBe(false);
        expect(component.$dispatch).toHaveBeenCalledWith('date-changed', { date: '1403/06/15' });
    });
    
    test('should not select disabled date', () => {
        const day = { number: 15, disabled: true };
        const originalDate = component.selectedDate;
        
        component.selectDate(day);
        
        expect(component.selectedDate).toBe(originalDate);
    });
    
    test('should navigate months correctly', () => {
        component.currentMonth = 6;
        component.currentYear = 1403;
        
        component.nextMonth();
        expect(component.currentMonth).toBe(7);
        
        component.currentMonth = 12;
        component.nextMonth();
        expect(component.currentMonth).toBe(1);
        expect(component.currentYear).toBe(1404);
        
        component.previousMonth();
        expect(component.currentMonth).toBe(12);
        expect(component.currentYear).toBe(1403);
    });
    
    test('should convert to Persian digits', () => {
        expect(component.toPersianDigits('123')).toBe('۱۲۳');
        expect(component.toPersianDigits('0')).toBe('۰');
    });
    
    test('should format date correctly', () => {
        component.selectedDate = '1403/06/15';
        expect(component.formattedDate).toBe('۱۴۰۳/۰۶/۱۵');
        
        component.selectedDate = null;
        expect(component.formattedDate).toBe('تاریخ را انتخاب کنید');
    });
});

describe('Persian Number Input Component', () => {
    let component;
    
    beforeEach(() => {
        const componentFactory = Alpine.data.mock.calls.find(call => call[0] === 'persianNumberInput')[1];
        component = componentFactory({ currency: true, decimals: true });
        
        component.$watch = jest.fn();
        component.init();
    });
    
    test('should initialize with default values', () => {
        expect(component.value).toBe('');
        expect(component.isCurrency).toBe(true);
        expect(component.allowDecimals).toBe(true);
    });
    
    test('should handle input correctly', () => {
        const mockEvent = {
            target: { value: '۱۲۳۴۵' }
        };
        
        component.handleInput(mockEvent);
        
        expect(component.value).toBe('12345');
    });
    
    test('should format currency values', () => {
        component.value = '1000000';
        const formatted = component.formatValue();
        expect(formatted).toContain('تومان');
    });
    
    test('should convert between Persian and English digits', () => {
        expect(component.toPersianDigits('123')).toBe('۱۲۳');
        expect(component.toEnglishDigits('۱۲۳')).toBe('123');
    });
    
    test('should respect min/max constraints', () => {
        component.maxValue = 1000;
        component.minValue = 10;
        
        const mockEvent1 = { target: { value: '2000' } };
        component.handleInput(mockEvent1);
        expect(component.value).toBe('1000');
        
        const mockEvent2 = { target: { value: '5' } };
        component.handleInput(mockEvent2);
        expect(component.value).toBe('10');
    });
});

describe('Gold Calculator Component', () => {
    let component;
    
    beforeEach(() => {
        global.fetch = jest.fn(() => 
            Promise.resolve({
                json: () => Promise.resolve({ price: 2500000 })
            })
        );
        
        const componentFactory = Alpine.data.mock.calls.find(call => call[0] === 'goldCalculator')[1];
        component = componentFactory();
        
        component.$watch = jest.fn();
        component.init();
    });
    
    test('should initialize and load gold price', async () => {
        await component.loadGoldPrice();
        expect(component.currentGoldPrice).toBe(2500000);
    });
    
    test('should calculate gold value correctly', () => {
        component.weight = '10';
        component.karat = 18;
        component.currentGoldPrice = 2500000;
        
        const result = component.calculate();
        
        expect(result.totalValue).toBeGreaterThan(0);
        expect(result.pureGoldValue).toBeGreaterThan(0);
    });
    
    test('should get correct karat purity', () => {
        expect(component.getKaratPurity(24)).toBe(1.0);
        expect(component.getKaratPurity(18)).toBe(0.750);
        expect(component.getKaratPurity(14)).toBe(0.583);
    });
    
    test('should format currency correctly', () => {
        const formatted = component.formatCurrency(1000000);
        expect(formatted).toContain('تومان');
        expect(formatted).toContain('۱');
    });
    
    test('should handle zero values', () => {
        component.weight = '0';
        component.currentGoldPrice = 2500000;
        
        const result = component.calculate();
        
        expect(result.totalValue).toBe(0);
        expect(result.pureGoldValue).toBe(0);
    });
});

describe('Search Component', () => {
    let component;
    
    beforeEach(() => {
        global.fetch.mockResolvedValue({
            json: () => Promise.resolve({ 
                results: [
                    { id: 1, title: 'گردنبند طلا', name: 'گردنبند طلا' },
                    { id: 2, title: 'انگشتر نقره', name: 'انگشتر نقره' }
                ]
            })
        });
        
        const componentFactory = Alpine.data.mock.calls.find(call => call[0] === 'persianSearch')[1];
        component = componentFactory({ url: '/api/search/' });
        
        component.$el = { addEventListener: jest.fn() };
        component.$watch = jest.fn();
        component.$dispatch = jest.fn();
        
        component.init();
    });
    
    test('should initialize with default values', () => {
        expect(component.query).toBe('');
        expect(component.results).toEqual([]);
        expect(component.isOpen).toBe(false);
        expect(component.loading).toBe(false);
    });
    
    test('should perform search when query length is sufficient', async () => {
        component.query = 'گردنبند';
        await component.performSearch();
        
        // URL encoding is expected for Persian characters
        expect(global.fetch).toHaveBeenCalledWith('/api/search/?q=%DA%AF%D8%B1%D8%AF%D9%86%D8%A8%D9%86%D8%AF');
        expect(component.results).toHaveLength(2);
        expect(component.isOpen).toBe(true);
    });
    
    test('should select result correctly', () => {
        const result = { id: 1, title: 'گردنبند طلا' };
        
        component.selectResult(result, 0);
        
        expect(component.query).toBe('گردنبند طلا');
        expect(component.isOpen).toBe(false);
        expect(component.$dispatch).toHaveBeenCalledWith('search-selected', { 
            result, 
            query: 'گردنبند طلا' 
        });
    });
    
    test('should handle keyboard navigation', () => {
        component.results = [{ id: 1 }, { id: 2 }];
        component.isOpen = true;
        component.selectedIndex = -1;
        
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
});

describe('Modal Component', () => {
    let component;
    
    beforeEach(() => {
        global.document.body.style = {};
        
        const componentFactory = Alpine.data.mock.calls.find(call => call[0] === 'modal')[1];
        component = componentFactory({ title: 'Test Modal' });
        
        component.$el = { 
            querySelectorAll: jest.fn(() => [{ focus: jest.fn() }])
        };
        component.$nextTick = jest.fn(cb => cb());
        component.$dispatch = jest.fn();
    });
    
    test('should initialize with correct values', () => {
        expect(component.isOpen).toBe(false);
        expect(component.title).toBe('Test Modal');
        expect(component.closable).toBe(true);
    });
    
    test('should open modal correctly', () => {
        component.open();
        
        expect(component.isOpen).toBe(true);
        expect(global.document.body.style.overflow).toBe('hidden');
    });
    
    test('should close modal correctly', () => {
        component.isOpen = true;
        global.document.body.style.overflow = 'hidden';
        
        component.close();
        
        expect(component.isOpen).toBe(false);
        expect(global.document.body.style.overflow).toBe('');
        expect(component.$dispatch).toHaveBeenCalledWith('modal-closed');
    });
    
    test('should handle escape key', () => {
        component.isOpen = true;
        
        component.handleKeydown({ key: 'Escape' });
        
        expect(component.isOpen).toBe(false);
    });
    
    test('should handle backdrop click', () => {
        component.isOpen = true;
        const mockEvent = {
            target: 'backdrop',
            currentTarget: 'backdrop'
        };
        
        component.handleBackdropClick(mockEvent);
        
        expect(component.isOpen).toBe(false);
    });
    
    test('should not close when not closable', () => {
        component.closable = false;
        component.isOpen = true;
        
        component.close();
        component.handleKeydown({ key: 'Escape' });
        
        expect(component.isOpen).toBe(true);
    });
});

describe('Form Validator Component', () => {
    let component;
    
    beforeEach(() => {
        const rules = {
            name: [
                { required: true, message: 'نام الزامی است' },
                { minLength: 2, message: 'حداقل ۲ کاراکتر' }
            ],
            email: [
                { required: true },
                { pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: 'ایمیل نامعتبر' }
            ]
        };
        
        const componentFactory = Alpine.data.mock.calls.find(call => call[0] === 'formValidator')[1];
        component = componentFactory(rules);
    });
    
    test('should initialize with empty errors', () => {
        expect(component.errors).toEqual({});
        expect(component.touched).toEqual({});
    });
    
    test('should validate required fields', () => {
        const isValid = component.validate('name', '');
        
        expect(isValid).toBe(false);
        expect(component.errors.name).toContain('نام الزامی است');
    });
    
    test('should validate minimum length', () => {
        const isValid = component.validate('name', 'a');
        
        expect(isValid).toBe(false);
        expect(component.errors.name).toContain('حداقل ۲ کاراکتر');
    });
    
    test('should validate pattern', () => {
        const isValid = component.validate('email', 'invalid-email');
        
        expect(isValid).toBe(false);
        expect(component.errors.email).toContain('ایمیل نامعتبر');
    });
    
    test('should pass valid input', () => {
        const isValid = component.validate('name', 'علی احمدی');
        
        expect(isValid).toBe(true);
        expect(component.errors.name).toEqual([]);
    });
    
    test('should track touched fields', () => {
        component.touch('name');
        
        expect(component.touched.name).toBe(true);
    });
    
    test('should check if field has error', () => {
        component.touched.name = true;
        component.errors.name = ['خطا'];
        
        expect(component.hasError('name')).toBe(true);
        
        component.errors.name = [];
        expect(component.hasError('name')).toBe(false);
    });
    
    test('should get first error message', () => {
        component.touched.name = true;
        component.errors.name = ['خطای اول', 'خطای دوم'];
        
        expect(component.getError('name')).toBe('خطای اول');
    });
    
    test('should check overall form validity', () => {
        component.errors = {
            name: [],
            email: ['خطا']
        };
        
        expect(component.isValid()).toBe(false);
        
        component.errors.email = [];
        expect(component.isValid()).toBe(true);
    });
});

describe('Data Table Component', () => {
    let component;
    
    beforeEach(() => {
        const data = [
            { id: 1, name: 'محصول ۱', price: 1000, category: 'طلا' },
            { id: 2, name: 'محصول ۲', price: 2000, category: 'نقره' },
            { id: 3, name: 'محصول ۳', price: 1500, category: 'طلا' }
        ];
        
        const componentFactory = Alpine.data.mock.calls.find(call => call[0] === 'dataTable')[1];
        component = componentFactory({ data, itemsPerPage: 2 });
        
        component.$watch = jest.fn();
        component.init();
    });
    
    test('should initialize with data', () => {
        expect(component.data).toHaveLength(3);
        expect(component.itemsPerPage).toBe(2);
        expect(component.currentPage).toBe(1);
    });
    
    test('should sort data correctly', () => {
        component.sort('price');
        
        expect(component.sortField).toBe('price');
        expect(component.sortDirection).toBe('asc');
        
        const sorted = component.sortedData;
        expect(sorted[0].price).toBe(1000);
        expect(sorted[2].price).toBe(2000);
        
        // Sort descending
        component.sort('price');
        expect(component.sortDirection).toBe('desc');
    });
    
    test('should filter data by search query', () => {
        component.searchQuery = 'محصول ۱';
        
        const filtered = component.filteredData;
        expect(filtered).toHaveLength(1);
        expect(filtered[0].name).toBe('محصول ۱');
    });
    
    test('should paginate data correctly', () => {
        const paginated = component.paginatedData;
        expect(paginated).toHaveLength(2);
        
        component.goToPage(2);
        expect(component.currentPage).toBe(2);
        
        const secondPage = component.paginatedData;
        expect(secondPage).toHaveLength(1);
    });
    
    test('should calculate total pages correctly', () => {
        expect(component.totalPages).toBe(2);
        
        component.itemsPerPage = 5;
        expect(component.totalPages).toBe(1);
    });
    
    test('should handle item selection', () => {
        const item = component.data[0];
        
        component.toggleSelection(item);
        expect(component.selectedItems).toContain(item);
        
        component.toggleSelection(item);
        expect(component.selectedItems).not.toContain(item);
    });
    
    test('should select all items', () => {
        component.selectAll();
        expect(component.selectedItems).toHaveLength(2); // Current page items
        
        component.selectAll();
        expect(component.selectedItems).toHaveLength(0);
    });
});

// Run tests
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        // Export test functions for CI/CD
    };
}