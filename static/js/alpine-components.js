/**
 * Alpine.js Components for ZARGAR Jewelry SaaS Platform
 * Provides Persian-native interactive components with dual theme support
 */

// Global Alpine.js store for shared state
document.addEventListener('alpine:init', () => {
    Alpine.store('zargar', {
        // Theme management
        theme: window.zargarConfig?.currentTheme || 'light',
        
        // User state
        user: {
            isAuthenticated: window.zargarConfig?.isAuthenticated || false,
            role: window.zargarConfig?.userRole || null
        },
        
        // Notifications
        notifications: [],
        
        // Loading states
        loading: {
            global: false,
            components: {}
        },
        
        // Gold price data
        goldPrice: {
            current: 0,
            trend: 'stable',
            lastUpdated: null
        },
        
        // Methods
        toggleTheme() {
            this.theme = this.theme === 'dark' ? 'light' : 'dark';
            document.documentElement.classList.toggle('dark', this.theme === 'dark');
            
            // Persist theme preference
            fetch('/api/theme/toggle/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.zargarConfig.csrfToken
                },
                body: JSON.stringify({ theme: this.theme })
            });
        },
        
        showNotification(message, type = 'info', duration = 5000) {
            const notification = {
                id: Date.now(),
                message,
                type,
                show: true
            };
            
            this.notifications.push(notification);
            
            setTimeout(() => {
                notification.show = false;
                setTimeout(() => {
                    this.notifications = this.notifications.filter(n => n.id !== notification.id);
                }, 300);
            }, duration);
        },
        
        setLoading(component, state) {
            this.loading.components[component] = state;
        },
        
        isLoading(component) {
            return this.loading.components[component] || false;
        }
    });
});

// Persian Date Picker Component
Alpine.data('persianDatePicker', (initialDate = null) => ({
    isOpen: false,
    selectedDate: initialDate,
    currentMonth: null,
    currentYear: null,
    days: [],
    
    init() {
        const today = new Date();
        this.currentMonth = today.getMonth() + 1;
        this.currentYear = today.getFullYear();
        this.generateCalendar();
        
        // Close on outside click
        this.$watch('isOpen', (value) => {
            if (value) {
                this.$nextTick(() => {
                    document.addEventListener('click', this.handleOutsideClick);
                });
            } else {
                document.removeEventListener('click', this.handleOutsideClick);
            }
        });
    },
    
    handleOutsideClick(event) {
        if (!this.$el.contains(event.target)) {
            this.isOpen = false;
        }
    },
    
    toggle() {
        this.isOpen = !this.isOpen;
    },
    
    selectDate(day) {
        if (day.disabled) return;
        
        this.selectedDate = `${this.currentYear}/${this.currentMonth.toString().padStart(2, '0')}/${day.number.toString().padStart(2, '0')}`;
        this.isOpen = false;
        
        // Dispatch change event
        this.$dispatch('date-changed', { date: this.selectedDate });
    },
    
    previousMonth() {
        if (this.currentMonth === 1) {
            this.currentMonth = 12;
            this.currentYear--;
        } else {
            this.currentMonth--;
        }
        this.generateCalendar();
    },
    
    nextMonth() {
        if (this.currentMonth === 12) {
            this.currentMonth = 1;
            this.currentYear++;
        } else {
            this.currentMonth++;
        }
        this.generateCalendar();
    },
    
    generateCalendar() {
        // Persian month names
        const monthNames = [
            'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
            'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
        ];
        
        this.monthName = monthNames[this.currentMonth - 1];
        
        // Generate days (simplified - in real implementation would use proper Persian calendar)
        const daysInMonth = this.getDaysInMonth(this.currentMonth, this.currentYear);
        this.days = [];
        
        for (let i = 1; i <= daysInMonth; i++) {
            this.days.push({
                number: i,
                persianNumber: this.toPersianDigits(i),
                disabled: false,
                isToday: this.isToday(i),
                isSelected: this.isSelected(i)
            });
        }
    },
    
    getDaysInMonth(month, year) {
        // Simplified - Persian calendar has different rules
        if (month <= 6) return 31;
        if (month <= 11) return 30;
        return this.isLeapYear(year) ? 30 : 29;
    },
    
    isLeapYear(year) {
        // Simplified Persian leap year calculation
        return ((year + 2346) % 128) % 33 % 4 === 1;
    },
    
    isToday(day) {
        const today = new Date();
        return day === today.getDate() && 
               this.currentMonth === today.getMonth() + 1 && 
               this.currentYear === today.getFullYear();
    },
    
    isSelected(day) {
        if (!this.selectedDate) return false;
        const [year, month, dayStr] = this.selectedDate.split('/');
        return parseInt(dayStr) === day && 
               parseInt(month) === this.currentMonth && 
               parseInt(year) === this.currentYear;
    },
    
    toPersianDigits(num) {
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return num.toString().replace(/\d/g, (digit) => persianDigits[parseInt(digit)]);
    },
    
    get formattedDate() {
        return this.selectedDate ? this.toPersianDigits(this.selectedDate) : 'تاریخ را انتخاب کنید';
    }
}));

// Persian Number Input Component
Alpine.data('persianNumberInput', (options = {}) => ({
    value: '',
    isCurrency: options.currency || false,
    allowDecimals: options.decimals !== false,
    maxValue: options.max || null,
    minValue: options.min || null,
    
    init() {
        this.$watch('value', (newValue) => {
            this.formatValue();
        });
    },
    
    handleInput(event) {
        let inputValue = event.target.value;
        
        // Remove non-numeric characters except Persian digits and decimal point
        inputValue = inputValue.replace(/[^\d۰-۹.]/g, '');
        
        // Convert Persian digits to English
        inputValue = this.toEnglishDigits(inputValue);
        
        // Handle decimal places
        if (!this.allowDecimals) {
            inputValue = inputValue.replace(/\./g, '');
        }
        
        // Apply min/max constraints
        const numValue = parseFloat(inputValue);
        if (this.maxValue && numValue > this.maxValue) {
            inputValue = this.maxValue.toString();
        }
        if (this.minValue && numValue < this.minValue) {
            inputValue = this.minValue.toString();
        }
        
        this.value = inputValue;
        event.target.value = this.formattedValue;
    },
    
    formatValue() {
        if (!this.value) return '';
        
        const numValue = parseFloat(this.value);
        if (isNaN(numValue)) return '';
        
        let formatted = new Intl.NumberFormat('fa-IR').format(numValue);
        
        if (this.isCurrency) {
            formatted += ' تومان';
        }
        
        return this.toPersianDigits(formatted);
    },
    
    toPersianDigits(str) {
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return str.toString().replace(/\d/g, (digit) => persianDigits[parseInt(digit)]);
    },
    
    toEnglishDigits(str) {
        const englishDigits = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return str.toString().replace(/[۰-۹]/g, (digit) => {
            return englishDigits[persianDigits.indexOf(digit)];
        });
    },
    
    get formattedValue() {
        return this.formatValue();
    },
    
    get numericValue() {
        return parseFloat(this.toEnglishDigits(this.value)) || 0;
    }
}));

// Gold Calculator Component
Alpine.data('goldCalculator', () => ({
    weight: '',
    karat: 24,
    currentGoldPrice: 0,
    loading: false,
    
    init() {
        this.loadGoldPrice();
        
        // Watch for changes
        this.$watch('weight', () => this.calculate());
        this.$watch('karat', () => this.calculate());
    },
    
    async loadGoldPrice() {
        this.loading = true;
        try {
            const response = await fetch('/api/gold-prices/current/');
            const data = await response.json();
            this.currentGoldPrice = data.price || 2500000; // Fallback price
            this.calculate();
        } catch (error) {
            console.error('Failed to load gold price:', error);
            this.currentGoldPrice = 2500000; // Fallback price
        } finally {
            this.loading = false;
        }
    },
    
    calculate() {
        const weightNum = parseFloat(this.toEnglishDigits(this.weight)) || 0;
        if (weightNum <= 0 || this.currentGoldPrice <= 0) {
            return {
                pureGoldValue: 0,
                totalValue: 0
            };
        }
        
        const purity = this.getKaratPurity(this.karat);
        const pureGoldWeight = weightNum * purity;
        const totalValue = pureGoldWeight * this.currentGoldPrice;
        
        return {
            pureGoldValue: pureGoldWeight * this.currentGoldPrice,
            totalValue: totalValue
        };
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
    
    formatCurrency(amount) {
        if (!amount) return '۰ تومان';
        const formatted = new Intl.NumberFormat('fa-IR').format(Math.round(amount));
        return this.toPersianDigits(formatted) + ' تومان';
    },
    
    toPersianDigits(str) {
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return str.toString().replace(/\d/g, (digit) => persianDigits[parseInt(digit)]);
    },
    
    toEnglishDigits(str) {
        const englishDigits = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return str.toString().replace(/[۰-۹]/g, (digit) => {
            return englishDigits[persianDigits.indexOf(digit)];
        });
    },
    
    get calculatedValues() {
        return this.calculate();
    }
}));

// Search Component with HTMX integration
Alpine.data('persianSearch', (options = {}) => ({
    query: '',
    results: [],
    isOpen: false,
    loading: false,
    selectedIndex: -1,
    searchUrl: options.url || '/api/search/',
    minLength: options.minLength || 2,
    debounceMs: options.debounce || 300,
    
    init() {
        this.$watch('query', (newQuery) => {
            if (newQuery.length >= this.minLength) {
                this.debounceSearch();
            } else {
                this.results = [];
                this.isOpen = false;
            }
        });
        
        // Handle keyboard navigation
        this.$el.addEventListener('keydown', (e) => {
            if (this.isOpen) {
                this.handleKeydown(e);
            }
        });
    },
    
    debounceSearch() {
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            this.performSearch();
        }, this.debounceMs);
    },
    
    async performSearch() {
        if (!this.query || this.query.length < this.minLength) return;
        
        this.loading = true;
        try {
            const response = await fetch(`${this.searchUrl}?q=${encodeURIComponent(this.query)}`);
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
    
    selectResult(result, index) {
        this.query = result.title || result.name || '';
        this.isOpen = false;
        this.selectedIndex = -1;
        
        // Dispatch selection event
        this.$dispatch('search-selected', { result, query: this.query });
    },
    
    handleKeydown(e) {
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
                    this.selectResult(this.results[this.selectedIndex], this.selectedIndex);
                }
                break;
            case 'Escape':
                this.isOpen = false;
                this.selectedIndex = -1;
                break;
        }
    },
    
    highlightMatch(text, query) {
        if (!query) return text;
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<mark class="bg-yellow-200 dark:bg-yellow-800">$1</mark>');
    }
}));

// Modal Component
Alpine.data('modal', (options = {}) => ({
    isOpen: false,
    title: options.title || '',
    size: options.size || 'md',
    closable: options.closable !== false,
    
    open() {
        this.isOpen = true;
        document.body.style.overflow = 'hidden';
        
        // Focus trap
        this.$nextTick(() => {
            const focusableElements = this.$el.querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            if (focusableElements.length > 0) {
                focusableElements[0].focus();
            }
        });
    },
    
    close() {
        if (!this.closable) return;
        
        this.isOpen = false;
        document.body.style.overflow = '';
        this.$dispatch('modal-closed');
    },
    
    handleKeydown(e) {
        if (e.key === 'Escape' && this.closable) {
            this.close();
        }
    },
    
    handleBackdropClick(e) {
        if (e.target === e.currentTarget && this.closable) {
            this.close();
        }
    },
    
    get sizeClasses() {
        const sizes = {
            sm: 'max-w-md',
            md: 'max-w-lg',
            lg: 'max-w-2xl',
            xl: 'max-w-4xl',
            full: 'max-w-full mx-4'
        };
        return sizes[this.size] || sizes.md;
    }
}));

// Dropdown Component
Alpine.data('dropdown', (options = {}) => ({
    isOpen: false,
    placement: options.placement || 'bottom-start',
    
    init() {
        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!this.$el.contains(e.target)) {
                this.isOpen = false;
            }
        });
    },
    
    toggle() {
        this.isOpen = !this.isOpen;
    },
    
    close() {
        this.isOpen = false;
    },
    
    handleKeydown(e) {
        if (e.key === 'Escape') {
            this.close();
        }
    }
}));

// Tabs Component
Alpine.data('tabs', (defaultTab = 0) => ({
    activeTab: defaultTab,
    
    setActiveTab(index) {
        this.activeTab = index;
        this.$dispatch('tab-changed', { index });
    },
    
    isActive(index) {
        return this.activeTab === index;
    }
}));

// Accordion Component
Alpine.data('accordion', (options = {}) => ({
    openItems: options.multiple ? [] : [options.defaultOpen || null],
    multiple: options.multiple || false,
    
    toggle(index) {
        if (this.multiple) {
            if (this.openItems.includes(index)) {
                this.openItems = this.openItems.filter(i => i !== index);
            } else {
                this.openItems.push(index);
            }
        } else {
            this.openItems = this.openItems[0] === index ? [] : [index];
        }
    },
    
    isOpen(index) {
        return this.openItems.includes(index);
    }
}));

// Toast Notification Component
Alpine.data('toast', () => ({
    notifications: [],
    
    show(message, type = 'info', duration = 5000) {
        const notification = {
            id: Date.now(),
            message,
            type,
            show: true
        };
        
        this.notifications.push(notification);
        
        setTimeout(() => {
            notification.show = false;
            setTimeout(() => {
                this.notifications = this.notifications.filter(n => n.id !== notification.id);
            }, 300);
        }, duration);
    },
    
    remove(id) {
        const notification = this.notifications.find(n => n.id === id);
        if (notification) {
            notification.show = false;
            setTimeout(() => {
                this.notifications = this.notifications.filter(n => n.id !== id);
            }, 300);
        }
    }
}));

// Form Validation Component
Alpine.data('formValidator', (rules = {}) => ({
    errors: {},
    touched: {},
    
    validate(field, value) {
        const fieldRules = rules[field];
        if (!fieldRules) return true;
        
        this.errors[field] = [];
        
        for (const rule of fieldRules) {
            if (rule.required && (!value || value.trim() === '')) {
                this.errors[field].push(rule.message || `${field} الزامی است`);
            }
            
            if (rule.minLength && value && value.length < rule.minLength) {
                this.errors[field].push(rule.message || `حداقل ${rule.minLength} کاراکتر وارد کنید`);
            }
            
            if (rule.maxLength && value && value.length > rule.maxLength) {
                this.errors[field].push(rule.message || `حداکثر ${rule.maxLength} کاراکتر مجاز است`);
            }
            
            if (rule.pattern && value && !rule.pattern.test(value)) {
                this.errors[field].push(rule.message || 'فرمت وارد شده صحیح نیست');
            }
            
            if (rule.custom && typeof rule.custom === 'function') {
                const customResult = rule.custom(value);
                if (customResult !== true) {
                    this.errors[field].push(customResult || 'مقدار وارد شده صحیح نیست');
                }
            }
        }
        
        return this.errors[field].length === 0;
    },
    
    touch(field) {
        this.touched[field] = true;
    },
    
    hasError(field) {
        return this.touched[field] && this.errors[field] && this.errors[field].length > 0;
    },
    
    getError(field) {
        return this.hasError(field) ? this.errors[field][0] : '';
    },
    
    isValid() {
        return Object.keys(this.errors).every(field => 
            !this.errors[field] || this.errors[field].length === 0
        );
    }
}));

// Data Table Component
Alpine.data('dataTable', (options = {}) => ({
    data: options.data || [],
    sortField: options.sortField || null,
    sortDirection: 'asc',
    currentPage: 1,
    itemsPerPage: options.itemsPerPage || 10,
    searchQuery: '',
    selectedItems: [],
    
    init() {
        this.$watch('searchQuery', () => {
            this.currentPage = 1;
        });
    },
    
    sort(field) {
        if (this.sortField === field) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortField = field;
            this.sortDirection = 'asc';
        }
    },
    
    toggleSelection(item) {
        const index = this.selectedItems.findIndex(selected => selected.id === item.id);
        if (index > -1) {
            this.selectedItems.splice(index, 1);
        } else {
            this.selectedItems.push(item);
        }
    },
    
    selectAll() {
        if (this.selectedItems.length === this.paginatedData.length) {
            this.selectedItems = [];
        } else {
            this.selectedItems = [...this.paginatedData];
        }
    },
    
    isSelected(item) {
        return this.selectedItems.some(selected => selected.id === item.id);
    },
    
    get filteredData() {
        if (!this.searchQuery) return this.data;
        
        return this.data.filter(item => {
            return Object.values(item).some(value => 
                value.toString().toLowerCase().includes(this.searchQuery.toLowerCase())
            );
        });
    },
    
    get sortedData() {
        if (!this.sortField) return this.filteredData;
        
        return [...this.filteredData].sort((a, b) => {
            const aVal = a[this.sortField];
            const bVal = b[this.sortField];
            
            if (this.sortDirection === 'asc') {
                return aVal > bVal ? 1 : -1;
            } else {
                return aVal < bVal ? 1 : -1;
            }
        });
    },
    
    get paginatedData() {
        const start = (this.currentPage - 1) * this.itemsPerPage;
        const end = start + this.itemsPerPage;
        return this.sortedData.slice(start, end);
    },
    
    get totalPages() {
        return Math.ceil(this.sortedData.length / this.itemsPerPage);
    },
    
    goToPage(page) {
        if (page >= 1 && page <= this.totalPages) {
            this.currentPage = page;
        }
    }
}));