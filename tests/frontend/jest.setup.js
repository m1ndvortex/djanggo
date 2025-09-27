/**
 * Jest setup file for RTL component tests
 * Configures test environment for Persian RTL components
 */

// Mock DOM APIs that might not be available in test environment
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.localStorage = localStorageMock;

// Mock sessionStorage
const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.sessionStorage = sessionStorageMock;

// Mock fetch API
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(''),
  })
);

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  observe() {
    return null;
  }
  disconnect() {
    return null;
  }
  unobserve() {
    return null;
  }
};

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  observe() {
    return null;
  }
  disconnect() {
    return null;
  }
  unobserve() {
    return null;
  }
};

// Mock MutationObserver
global.MutationObserver = class MutationObserver {
  constructor() {}
  observe() {
    return null;
  }
  disconnect() {
    return null;
  }
  takeRecords() {
    return [];
  }
};

// Mock requestAnimationFrame
global.requestAnimationFrame = jest.fn(cb => setTimeout(cb, 0));
global.cancelAnimationFrame = jest.fn(id => clearTimeout(id));

// Mock CSS.supports
global.CSS = {
  supports: jest.fn(() => true),
};

// Mock getComputedStyle
global.getComputedStyle = jest.fn(() => ({
  getPropertyValue: jest.fn(() => ''),
  direction: 'rtl',
  fontFamily: 'Vazirmatn',
}));

// Mock document.cookie
Object.defineProperty(document, 'cookie', {
  writable: true,
  value: '',
});

// Mock window.location
delete window.location;
window.location = {
  href: 'https://testshop.zargar.com',
  hostname: 'testshop.zargar.com',
  pathname: '/',
  search: '',
  hash: '',
  reload: jest.fn(),
  assign: jest.fn(),
};

// Mock console methods to reduce noise in tests
global.console = {
  ...console,
  log: jest.fn(),
  debug: jest.fn(),
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
};

// Set up RTL environment
document.documentElement.dir = 'rtl';
document.documentElement.lang = 'fa';

// Mock Flowbite
global.Flowbite = {
  init: jest.fn(),
  initDropdowns: jest.fn(),
  initModals: jest.fn(),
  initTooltips: jest.fn(),
  initAccordions: jest.fn(),
  initTabs: jest.fn(),
  initCarousels: jest.fn(),
};

// Mock Framer Motion
global.Motion = {
  animate: jest.fn(() => Promise.resolve()),
  timeline: jest.fn(),
  stagger: jest.fn(),
};

// Mock Alpine.js
global.Alpine = {
  data: jest.fn(),
  store: jest.fn(),
  start: jest.fn(),
};

// Mock HTMX
global.htmx = {
  process: jest.fn(),
  trigger: jest.fn(),
  ajax: jest.fn(),
};

// Persian test data
global.PERSIAN_TEST_DATA = {
  months: [
    'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
    'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
  ],
  days: ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه'],
  numbers: {
    persian: ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'],
    english: ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
  },
  sampleText: {
    greeting: 'سلام',
    welcome: 'خوش آمدید',
    search: 'جستجو',
    save: 'ذخیره',
    cancel: 'لغو',
    delete: 'حذف',
    edit: 'ویرایش',
    add: 'افزودن'
  },
  jewelry: {
    necklace: 'گردنبند',
    ring: 'انگشتر',
    bracelet: 'دستبند',
    earring: 'گوشواره',
    gold: 'طلا',
    silver: 'نقره',
    diamond: 'الماس'
  },
  currency: {
    toman: 'تومان',
    rial: 'ریال'
  }
};

// Test utilities
global.TEST_UTILS = {
  // Create a mock element with Persian attributes
  createPersianElement: (tag = 'div', attributes = {}) => {
    const element = document.createElement(tag);
    element.dir = 'rtl';
    element.lang = 'fa';
    
    Object.keys(attributes).forEach(key => {
      element.setAttribute(key, attributes[key]);
    });
    
    return element;
  },
  
  // Create a mock Persian input
  createPersianInput: (type = 'text', placeholder = 'متن را وارد کنید') => {
    const input = document.createElement('input');
    input.type = type;
    input.dir = 'rtl';
    input.lang = 'fa';
    input.placeholder = placeholder;
    input.style.textAlign = 'right';
    input.style.fontFamily = 'Vazirmatn';
    
    return input;
  },
  
  // Simulate theme change
  simulateThemeChange: (theme = 'dark') => {
    document.body.className = theme;
    document.documentElement.className = theme;
    
    const event = new CustomEvent('themeChanged', {
      detail: { theme: theme }
    });
    window.dispatchEvent(event);
  },
  
  // Simulate viewport change
  simulateViewportChange: (width, height = 800) => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: width,
    });
    
    Object.defineProperty(window, 'innerHeight', {
      writable: true,
      configurable: true,
      value: height,
    });
    
    const event = new Event('resize');
    window.dispatchEvent(event);
  },
  
  // Wait for async operations
  waitFor: (ms = 100) => new Promise(resolve => setTimeout(resolve, ms)),
  
  // Convert Persian to English digits for testing
  persianToEnglish: (str) => {
    const persian = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
    const english = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];
    
    return str.replace(/[۰-۹]/g, (digit) => {
      return english[persian.indexOf(digit)];
    });
  },
  
  // Convert English to Persian digits for testing
  englishToPersian: (str) => {
    const persian = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
    
    return str.replace(/\d/g, (digit) => {
      return persian[parseInt(digit)];
    });
  }
};

// Custom matchers for Persian text
expect.extend({
  toContainPersianText(received, expected) {
    const pass = received.includes(expected);
    
    if (pass) {
      return {
        message: () => `Expected "${received}" not to contain Persian text "${expected}"`,
        pass: true,
      };
    } else {
      return {
        message: () => `Expected "${received}" to contain Persian text "${expected}"`,
        pass: false,
      };
    }
  },
  
  toHaveRTLDirection(received) {
    const dir = received.dir || received.style.direction;
    const pass = dir === 'rtl';
    
    if (pass) {
      return {
        message: () => `Expected element not to have RTL direction`,
        pass: true,
      };
    } else {
      return {
        message: () => `Expected element to have RTL direction, but got "${dir}"`,
        pass: false,
      };
    }
  },
  
  toHavePersianFont(received) {
    const fontFamily = received.style.fontFamily || getComputedStyle(received).fontFamily;
    const pass = fontFamily.includes('Vazir') || fontFamily.includes('Yekan');
    
    if (pass) {
      return {
        message: () => `Expected element not to have Persian font`,
        pass: true,
      };
    } else {
      return {
        message: () => `Expected element to have Persian font, but got "${fontFamily}"`,
        pass: false,
      };
    }
  },
  
  toHaveCyberTheme(received) {
    const classList = Array.from(received.classList);
    const pass = classList.some(cls => cls.includes('cyber-'));
    
    if (pass) {
      return {
        message: () => `Expected element not to have cybersecurity theme classes`,
        pass: true,
      };
    } else {
      return {
        message: () => `Expected element to have cybersecurity theme classes`,
        pass: false,
      };
    }
  }
});

// Setup complete
console.log('🧪 Jest setup complete for RTL Persian components');
console.log('📱 RTL direction:', document.documentElement.dir);
console.log('🌐 Language:', document.documentElement.lang);
console.log('🎨 Test utilities loaded');