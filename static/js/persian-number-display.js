/**
 * Persian Number Display Components for ZARGAR Jewelry SaaS
 * Provides comprehensive frontend components for displaying Persian numbers,
 * currency, weights, and financial data with proper formatting.
 */

class PersianNumberDisplay {
    constructor() {
        this.englishDigits = '0123456789';
        this.persianDigits = '۰۱۲۳۴۵۶۷۸۹';
        this.persianDecimalSeparator = '٫';
        this.persianThousandSeparator = '،';
        
        // Weight unit conversions (to grams)
        this.weightUnits = {
            'gram': { name: 'گرم', symbol: 'گ', toGram: 1 },
            'mesghal': { name: 'مثقال', symbol: 'م', toGram: 4.608 },
            'soot': { name: 'سوت', symbol: 'س', toGram: 0.2304 },
            'dirham': { name: 'درهم', symbol: 'د', toGram: 3.125 },
            'ounce': { name: 'اونس', symbol: 'او', toGram: 28.3495 },
            'tola': { name: 'تولا', symbol: 'ت', toGram: 11.6638 }
        };
        
        this.init();
    }
    
    init() {
        this.initializeCurrencyDisplays();
        this.initializeWeightDisplays();
        this.initializeNumberDisplays();
        this.initializeGoldPriceDisplays();
        this.initializePercentageDisplays();
        this.setupAutoUpdate();
    }
    
    /**
     * Convert English digits to Persian digits
     */
    toPersianDigits(text) {
        if (!text) return '';
        
        let result = String(text);
        for (let i = 0; i < this.englishDigits.length; i++) {
            result = result.replace(new RegExp(this.englishDigits[i], 'g'), this.persianDigits[i]);
        }
        
        // Convert decimal and thousand separators
        result = result.replace(/\./g, this.persianDecimalSeparator);
        result = result.replace(/,/g, this.persianThousandSeparator);
        
        return result;
    }
    
    /**
     * Convert Persian digits to English digits
     */
    toEnglishDigits(text) {
        if (!text) return '';
        
        let result = String(text);
        for (let i = 0; i < this.persianDigits.length; i++) {
            result = result.replace(new RegExp(this.persianDigits[i], 'g'), this.englishDigits[i]);
        }
        
        // Convert separators back
        result = result.replace(new RegExp(this.persianDecimalSeparator, 'g'), '.');
        result = result.replace(new RegExp(this.persianThousandSeparator, 'g'), ',');
        
        return result;
    }
    
    /**
     * Format currency with Persian numerals
     */
    formatCurrency(amount, options = {}) {
        const {
            includeSymbol = true,
            usePersianDigits = true,
            showDecimals = false,
            decimalPlaces = 0,
            symbol = 'تومان'
        } = options;
        
        if (amount === null || amount === undefined || amount === '') {
            return usePersianDigits ? '۰ تومان' : '0 تومان';
        }
        
        let numericAmount = parseFloat(amount);
        if (isNaN(numericAmount)) {
            return usePersianDigits ? '۰ تومان' : '0 تومان';
        }
        
        // Format with appropriate decimal places
        let formatted;
        if (showDecimals && decimalPlaces > 0) {
            formatted = numericAmount.toFixed(decimalPlaces);
        } else {
            formatted = Math.round(numericAmount).toString();
        }
        
        // Add thousand separators
        formatted = this.addThousandSeparators(formatted);
        
        // Convert to Persian digits if requested
        if (usePersianDigits) {
            formatted = this.toPersianDigits(formatted);
        }
        
        // Add currency symbol
        if (includeSymbol) {
            formatted += ` ${symbol}`;
        }
        
        return formatted;
    }
    
    /**
     * Format weight with Persian units
     */
    formatWeight(weight, options = {}) {
        const {
            unit = 'gram',
            usePersianDigits = true,
            showUnitName = true,
            precision = 3
        } = options;
        
        if (weight === null || weight === undefined || weight === '') {
            const unitInfo = this.weightUnits[unit] || this.weightUnits['gram'];
            return usePersianDigits ? `۰ ${unitInfo.name}` : `0 ${unitInfo.name}`;
        }
        
        let numericWeight = parseFloat(weight);
        if (isNaN(numericWeight)) {
            const unitInfo = this.weightUnits[unit] || this.weightUnits['gram'];
            return usePersianDigits ? `۰ ${unitInfo.name}` : `0 ${unitInfo.name}`;
        }
        
        if (!(unit in this.weightUnits)) {
            throw new Error(`Unsupported weight unit: ${unit}`);
        }
        
        // Format with precision, removing trailing zeros
        let formatted = numericWeight.toFixed(precision);
        formatted = parseFloat(formatted).toString();
        
        // Add thousand separators
        formatted = this.addThousandSeparators(formatted);
        
        // Convert to Persian digits if requested
        if (usePersianDigits) {
            formatted = this.toPersianDigits(formatted);
        }
        
        // Add unit name
        if (showUnitName) {
            const unitInfo = this.weightUnits[unit];
            formatted += ` ${unitInfo.name}`;
        }
        
        return formatted;
    }
    
    /**
     * Convert weight between units
     */
    convertWeight(weight, fromUnit, toUnit, precision = 3) {
        if (!(fromUnit in this.weightUnits) || !(toUnit in this.weightUnits)) {
            throw new Error('Unsupported weight unit');
        }
        
        const numericWeight = parseFloat(weight);
        if (isNaN(numericWeight)) {
            return 0;
        }
        
        // Convert to grams first, then to target unit
        const weightInGrams = numericWeight * this.weightUnits[fromUnit].toGram;
        const convertedWeight = weightInGrams / this.weightUnits[toUnit].toGram;
        
        return parseFloat(convertedWeight.toFixed(precision));
    }
    
    /**
     * Format weight with multiple unit conversions
     */
    formatWeightWithConversions(weightGrams, options = {}) {
        const {
            targetUnits = ['gram', 'mesghal', 'soot'],
            usePersianDigits = true
        } = options;
        
        const results = {};
        
        for (const unit of targetUnits) {
            if (unit in this.weightUnits) {
                const convertedWeight = this.convertWeight(weightGrams, 'gram', unit);
                results[unit] = this.formatWeight(convertedWeight, {
                    unit: unit,
                    usePersianDigits: usePersianDigits
                });
            }
        }
        
        return results;
    }
    
    /**
     * Format percentage with Persian digits
     */
    formatPercentage(percentage, options = {}) {
        const {
            usePersianDigits = true,
            decimalPlaces = 1
        } = options;
        
        if (percentage === null || percentage === undefined || percentage === '') {
            return usePersianDigits ? '۰٪' : '0%';
        }
        
        const numericPercentage = parseFloat(percentage);
        if (isNaN(numericPercentage)) {
            return usePersianDigits ? '۰٪' : '0%';
        }
        
        let formatted = numericPercentage.toFixed(decimalPlaces);
        
        if (usePersianDigits) {
            formatted = this.toPersianDigits(formatted);
            formatted += '٪'; // Persian percent sign
        } else {
            formatted += '%';
        }
        
        return formatted;
    }
    
    /**
     * Format large numbers with Persian word format
     */
    formatLargeNumber(number, options = {}) {
        const {
            usePersianDigits = true,
            useWordFormat = false
        } = options;
        
        if (number === null || number === undefined || number === '') {
            return usePersianDigits ? '۰' : '0';
        }
        
        const numericNumber = parseFloat(number);
        if (isNaN(numericNumber)) {
            return usePersianDigits ? '۰' : '0';
        }
        
        const isNegative = numericNumber < 0;
        const absNumber = Math.abs(numericNumber);
        
        let formatted;
        
        if (useWordFormat && absNumber >= 1000) {
            formatted = this.formatNumberWithWords(absNumber, usePersianDigits);
        } else {
            formatted = this.addThousandSeparators(Math.round(absNumber).toString());
            if (usePersianDigits) {
                formatted = this.toPersianDigits(formatted);
            }
        }
        
        if (isNegative) {
            formatted = `-${formatted}`;
        }
        
        return formatted;
    }
    
    /**
     * Format number with Persian word units
     */
    formatNumberWithWords(number, usePersianDigits) {
        const units = [
            { value: 1000000000000, name: 'بیلیون' },
            { value: 1000000000, name: 'میلیارد' },
            { value: 1000000, name: 'میلیون' },
            { value: 1000, name: 'هزار' }
        ];
        
        for (const unit of units) {
            if (number >= unit.value) {
                const quotient = Math.floor(number / unit.value);
                const remainder = number % unit.value;
                
                let quotientStr = this.addThousandSeparators(quotient.toString());
                if (usePersianDigits) {
                    quotientStr = this.toPersianDigits(quotientStr);
                }
                
                let result = `${quotientStr} ${unit.name}`;
                
                if (remainder >= 1000) {
                    const remainderStr = this.formatNumberWithWords(remainder, usePersianDigits);
                    result += ` و ${remainderStr}`;
                } else if (remainder > 0) {
                    let remainderStr = remainder.toString();
                    if (usePersianDigits) {
                        remainderStr = this.toPersianDigits(remainderStr);
                    }
                    result += ` و ${remainderStr}`;
                }
                
                return result;
            }
        }
        
        // For numbers less than 1000
        let formatted = Math.round(number).toString();
        if (usePersianDigits) {
            formatted = this.toPersianDigits(formatted);
        }
        return formatted;
    }
    
    /**
     * Calculate and format gold price information
     */
    formatGoldPrice(pricePerGram, weightGrams, options = {}) {
        const { usePersianDigits = true } = options;
        
        if (!pricePerGram || !weightGrams) {
            const emptyValue = usePersianDigits ? '۰ تومان' : '0 تومان';
            return {
                pricePerGram: emptyValue,
                totalValue: emptyValue,
                weightDisplay: usePersianDigits ? '۰ گرم' : '0 gram',
                weightMesghal: usePersianDigits ? '۰ مثقال' : '0 مثقال',
                weightSoot: usePersianDigits ? '۰ سوت' : '0 سوت'
            };
        }
        
        const price = parseFloat(pricePerGram);
        const weight = parseFloat(weightGrams);
        
        if (isNaN(price) || isNaN(weight)) {
            const emptyValue = usePersianDigits ? '۰ تومان' : '0 تومان';
            return {
                pricePerGram: emptyValue,
                totalValue: emptyValue,
                weightDisplay: usePersianDigits ? '۰ گرم' : '0 gram',
                weightMesghal: usePersianDigits ? '۰ مثقال' : '0 مثقال',
                weightSoot: usePersianDigits ? '۰ سوت' : '0 سوت'
            };
        }
        
        const totalValue = price * weight;
        
        return {
            pricePerGram: this.formatCurrency(price, { usePersianDigits }),
            totalValue: this.formatCurrency(totalValue, { usePersianDigits }),
            weightDisplay: this.formatWeight(weight, { unit: 'gram', usePersianDigits }),
            weightMesghal: this.formatWeight(
                this.convertWeight(weight, 'gram', 'mesghal'), 
                { unit: 'mesghal', usePersianDigits }
            ),
            weightSoot: this.formatWeight(
                this.convertWeight(weight, 'gram', 'soot'), 
                { unit: 'soot', usePersianDigits }
            )
        };
    }
    
    /**
     * Add thousand separators to a number string
     */
    addThousandSeparators(numberString) {
        const parts = numberString.split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        return parts.join('.');
    }
    
    /**
     * Initialize currency display elements
     */
    initializeCurrencyDisplays() {
        const currencyElements = document.querySelectorAll('[data-persian-currency]');
        
        currencyElements.forEach(element => {
            const amount = element.dataset.amount || element.textContent;
            const includeSymbol = element.dataset.includeSymbol !== 'false';
            const usePersianDigits = element.dataset.usePersianDigits !== 'false';
            const showDecimals = element.dataset.showDecimals === 'true';
            const decimalPlaces = parseInt(element.dataset.decimalPlaces) || 0;
            const symbol = element.dataset.symbol || 'تومان';
            
            const formatted = this.formatCurrency(amount, {
                includeSymbol,
                usePersianDigits,
                showDecimals,
                decimalPlaces,
                symbol
            });
            
            element.textContent = formatted;
            element.setAttribute('title', `مقدار: ${amount}`);
        });
    }
    
    /**
     * Initialize weight display elements
     */
    initializeWeightDisplays() {
        const weightElements = document.querySelectorAll('[data-persian-weight]');
        
        weightElements.forEach(element => {
            const weight = element.dataset.weight || element.textContent;
            const unit = element.dataset.unit || 'gram';
            const usePersianDigits = element.dataset.usePersianDigits !== 'false';
            const showUnitName = element.dataset.showUnitName !== 'false';
            const precision = parseInt(element.dataset.precision) || 3;
            
            const formatted = this.formatWeight(weight, {
                unit,
                usePersianDigits,
                showUnitName,
                precision
            });
            
            element.textContent = formatted;
            element.setAttribute('title', `وزن: ${weight} ${unit}`);
        });
        
        // Initialize weight conversion displays
        const weightConversionElements = document.querySelectorAll('[data-weight-conversions]');
        
        weightConversionElements.forEach(element => {
            const weightGrams = element.dataset.weightGrams;
            const targetUnits = element.dataset.targetUnits ? 
                element.dataset.targetUnits.split(',') : 
                ['gram', 'mesghal', 'soot'];
            const usePersianDigits = element.dataset.usePersianDigits !== 'false';
            
            const conversions = this.formatWeightWithConversions(weightGrams, {
                targetUnits,
                usePersianDigits
            });
            
            // Create conversion display
            let html = '<div class="weight-conversions">';
            for (const [unit, formatted] of Object.entries(conversions)) {
                html += `<span class="weight-conversion-item" data-unit="${unit}">${formatted}</span>`;
            }
            html += '</div>';
            
            element.innerHTML = html;
        });
    }
    
    /**
     * Initialize number display elements
     */
    initializeNumberDisplays() {
        const numberElements = document.querySelectorAll('[data-persian-number]');
        
        numberElements.forEach(element => {
            const number = element.dataset.number || element.textContent;
            const usePersianDigits = element.dataset.usePersianDigits !== 'false';
            const useWordFormat = element.dataset.useWordFormat === 'true';
            
            const formatted = this.formatLargeNumber(number, {
                usePersianDigits,
                useWordFormat
            });
            
            element.textContent = formatted;
            element.setAttribute('title', `عدد: ${number}`);
        });
    }
    
    /**
     * Initialize gold price display elements
     */
    initializeGoldPriceDisplays() {
        const goldPriceElements = document.querySelectorAll('[data-gold-price]');
        
        goldPriceElements.forEach(element => {
            const pricePerGram = element.dataset.pricePerGram;
            const weightGrams = element.dataset.weightGrams;
            const usePersianDigits = element.dataset.usePersianDigits !== 'false';
            
            const goldPriceInfo = this.formatGoldPrice(pricePerGram, weightGrams, {
                usePersianDigits
            });
            
            // Create gold price display
            let html = '<div class="gold-price-info">';
            html += `<div class="price-per-gram">قیمت هر گرم: ${goldPriceInfo.pricePerGram}</div>`;
            html += `<div class="total-value">ارزش کل: ${goldPriceInfo.totalValue}</div>`;
            html += `<div class="weight-display">وزن: ${goldPriceInfo.weightDisplay}</div>`;
            html += `<div class="weight-conversions">`;
            html += `<span class="weight-mesghal">${goldPriceInfo.weightMesghal}</span>`;
            html += `<span class="weight-soot">${goldPriceInfo.weightSoot}</span>`;
            html += `</div>`;
            html += '</div>';
            
            element.innerHTML = html;
        });
    }
    
    /**
     * Initialize percentage display elements
     */
    initializePercentageDisplays() {
        const percentageElements = document.querySelectorAll('[data-persian-percentage]');
        
        percentageElements.forEach(element => {
            const percentage = element.dataset.percentage || element.textContent;
            const usePersianDigits = element.dataset.usePersianDigits !== 'false';
            const decimalPlaces = parseInt(element.dataset.decimalPlaces) || 1;
            
            const formatted = this.formatPercentage(percentage, {
                usePersianDigits,
                decimalPlaces
            });
            
            element.textContent = formatted;
            element.setAttribute('title', `درصد: ${percentage}`);
        });
    }
    
    /**
     * Setup auto-update functionality for dynamic content
     */
    setupAutoUpdate() {
        // Watch for DOM changes and reinitialize displays
        const observer = new MutationObserver((mutations) => {
            let shouldUpdate = false;
            
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            if (node.matches('[data-persian-currency], [data-persian-weight], [data-persian-number], [data-gold-price], [data-persian-percentage]') ||
                                node.querySelector('[data-persian-currency], [data-persian-weight], [data-persian-number], [data-gold-price], [data-persian-percentage]')) {
                                shouldUpdate = true;
                            }
                        }
                    });
                }
            });
            
            if (shouldUpdate) {
                this.init();
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
    /**
     * Update specific element with new value
     */
    updateElement(element, newValue) {
        if (element.hasAttribute('data-persian-currency')) {
            element.dataset.amount = newValue;
            this.initializeCurrencyDisplays();
        } else if (element.hasAttribute('data-persian-weight')) {
            element.dataset.weight = newValue;
            this.initializeWeightDisplays();
        } else if (element.hasAttribute('data-persian-number')) {
            element.dataset.number = newValue;
            this.initializeNumberDisplays();
        } else if (element.hasAttribute('data-persian-percentage')) {
            element.dataset.percentage = newValue;
            this.initializePercentageDisplays();
        }
    }
    
    /**
     * Utility method to parse Persian number input
     */
    parsePersianNumber(input) {
        if (!input) return null;
        
        let cleaned = String(input).trim();
        
        // Convert Persian digits to English
        cleaned = this.toEnglishDigits(cleaned);
        
        // Remove Persian separators
        cleaned = cleaned.replace(/،/g, '');
        cleaned = cleaned.replace(/٫/g, '.');
        
        // Remove currency and weight unit names
        cleaned = cleaned.replace(/تومان|ریال|گرم|مثقال|سوت|درهم|اونس|تولا/g, '').trim();
        
        const number = parseFloat(cleaned);
        return isNaN(number) ? null : number;
    }
}

// Initialize Persian Number Display when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.persianNumberDisplay = new PersianNumberDisplay();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PersianNumberDisplay;
}