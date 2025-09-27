/**
 * Theme toggle functionality for ZARGAR jewelry SaaS platform
 * Handles switching between light and dark (cybersecurity) themes
 */

class ThemeManager {
    constructor() {
        this.currentTheme = this.getCurrentTheme();
        this.init();
    }

    getCurrentTheme() {
        // Check cookie first, then localStorage, then default
        const cookieTheme = this.getCookie('zargar_theme');
        if (cookieTheme) return cookieTheme;
        
        const localTheme = localStorage.getItem('zargar_theme');
        if (localTheme) return localTheme;
        
        return 'light'; // default theme
    }

    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    setCookie(name, value, days = 365) {
        const expires = new Date();
        expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
        document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/`;
    }

    init() {
        this.applyTheme(this.currentTheme);
        this.setupEventListeners();
        this.initializeToggleButtons();
    }

    applyTheme(theme) {
        const body = document.body;
        const html = document.documentElement;
        
        // Remove existing theme classes
        body.classList.remove('light', 'dark', 'cyber-theme', 'modern-theme');
        html.classList.remove('light', 'dark');
        
        // Apply new theme classes
        if (theme === 'dark') {
            body.classList.add('dark', 'cyber-theme');
            html.classList.add('dark');
            this.applyCyberTheme();
        } else {
            body.classList.add('light', 'modern-theme');
            html.classList.add('light');
            this.applyLightTheme();
        }
        
        // Store theme preference
        localStorage.setItem('zargar_theme', theme);
        this.setCookie('zargar_theme', theme);
        
        // Dispatch theme change event
        window.dispatchEvent(new CustomEvent('themeChanged', { 
            detail: { theme: theme } 
        }));
    }

    applyCyberTheme() {
        // Apply cybersecurity theme specific styles
        const metaTheme = document.querySelector('meta[name="theme-color"]');
        if (metaTheme) {
            metaTheme.setAttribute('content', '#0B0E1A');
        }
        
        // Initialize cyber animations if Framer Motion is available
        if (window.Motion) {
            this.initCyberAnimations();
        }
    }

    applyLightTheme() {
        // Apply light theme specific styles
        const metaTheme = document.querySelector('meta[name="theme-color"]');
        if (metaTheme) {
            metaTheme.setAttribute('content', '#f9fafb');
        }
    }

    initCyberAnimations() {
        // Initialize Framer Motion animations for cybersecurity theme
        const cards = document.querySelectorAll('.cyber-glass-card');
        cards.forEach((card, index) => {
            if (window.Motion) {
                window.Motion.animate(card, {
                    opacity: [0, 1],
                    y: [20, 0],
                    scale: [0.95, 1]
                }, {
                    duration: 0.4,
                    delay: index * 0.1,
                    ease: [0.4, 0, 0.2, 1]
                });
            }
        });
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.currentTheme = newTheme;
        this.applyTheme(newTheme);
        
        // Send to server if user is authenticated
        if (window.csrfToken) {
            this.updateServerTheme(newTheme);
        }
        
        return newTheme;
    }

    async updateServerTheme(theme) {
        try {
            const response = await fetch('/theme/toggle/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfToken,
                },
                body: JSON.stringify({ theme: theme })
            });
            
            if (!response.ok) {
                console.warn('Failed to update theme on server');
            }
        } catch (error) {
            console.warn('Error updating theme on server:', error);
        }
    }

    setupEventListeners() {
        // Listen for system theme changes
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addListener((e) => {
                if (!localStorage.getItem('zargar_theme')) {
                    this.applyTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
    }

    initializeToggleButtons() {
        const toggleButtons = document.querySelectorAll('[data-theme-toggle]');
        toggleButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleTheme();
                this.updateToggleButtonState(button);
            });
            
            // Set initial state
            this.updateToggleButtonState(button);
        });
    }

    updateToggleButtonState(button) {
        const isDark = this.currentTheme === 'dark';
        
        // Update button text/icon
        const lightIcon = button.querySelector('.theme-light-icon');
        const darkIcon = button.querySelector('.theme-dark-icon');
        
        if (lightIcon && darkIcon) {
            lightIcon.style.display = isDark ? 'none' : 'block';
            darkIcon.style.display = isDark ? 'block' : 'none';
        }
        
        // Update aria-label
        button.setAttribute('aria-label', 
            isDark ? 'Switch to light mode' : 'Switch to dark mode'
        );
    }
}

// Persian number conversion utility
class PersianNumbers {
    static persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
    static englishDigits = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];

    static toPersian(str) {
        return str.toString().replace(/\d/g, (digit) => {
            return this.persianDigits[parseInt(digit)];
        });
    }

    static toEnglish(str) {
        return str.toString().replace(/[۰-۹]/g, (digit) => {
            return this.englishDigits[this.persianDigits.indexOf(digit)];
        });
    }

    static formatCurrency(amount, currency = 'تومان') {
        const formatted = new Intl.NumberFormat('fa-IR').format(amount);
        return `${this.toPersian(formatted)} ${currency}`;
    }
}

// Initialize theme manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.themeManager = new ThemeManager();
    window.PersianNumbers = PersianNumbers;
    
    // Auto-convert numbers to Persian in elements with persian-numbers class
    const persianNumberElements = document.querySelectorAll('.persian-numbers');
    persianNumberElements.forEach(element => {
        element.textContent = PersianNumbers.toPersian(element.textContent);
    });
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ThemeManager, PersianNumbers };
}