/**
 * Gold Installments System JavaScript
 * Provides interactive functionality for gold installment management
 */

// Persian Number Formatter utility
const PersianFormatter = {
    // Persian digits mapping
    persianDigits: ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'],
    
    // Convert English digits to Persian
    toPersianDigits: function(str) {
        return str.toString().replace(/\d/g, function(match) {
            return this.persianDigits[parseInt(match)];
        }.bind(this));
    },
    
    // Format currency with Persian digits
    formatCurrency: function(amount, usePersianDigits = true) {
        const formatted = new Intl.NumberFormat('fa-IR').format(amount) + ' تومان';
        return usePersianDigits ? this.toPersianDigits(formatted) : formatted;
    },
    
    // Format weight with Persian digits
    formatWeight: function(weight, unit = 'gram', usePersianDigits = true) {
        const unitMap = {
            'gram': 'گرم',
            'mesghal': 'مثقال',
            'soot': 'سوت'
        };
        const formatted = parseFloat(weight).toFixed(3) + ' ' + (unitMap[unit] || unit);
        return usePersianDigits ? this.toPersianDigits(formatted) : formatted;
    },
    
    // Format percentage
    formatPercentage: function(percentage, usePersianDigits = true) {
        const formatted = parseFloat(percentage).toFixed(1) + '%';
        return usePersianDigits ? this.toPersianDigits(formatted) : formatted;
    },
    
    // Format number
    formatNumber: function(number, usePersianDigits = true) {
        const formatted = new Intl.NumberFormat('fa-IR').format(number);
        return usePersianDigits ? this.toPersianDigits(formatted) : formatted;
    }
};

// Gold Installments main object
const GoldInstallments = {
    
    // Initialize the system
    init: function() {
        this.initEventListeners();
        this.initPersianInputs();
        this.initTooltips();
    },
    
    // Initialize event listeners
    initEventListeners: function() {
        // Customer search functionality
        $(document).on('input', '.customer-search', this.handleCustomerSearch);
        
        // Gold price calculator
        $(document).on('input', '.gold-calculator-input', this.calculateGoldWeight);
        
        // Quick payment amounts
        $(document).on('click', '.quick-amount', this.setQuickAmount);
        
        // Form validation
        $(document).on('submit', '.gold-form', this.validateForm);
        
        // Price protection toggle
        $(document).on('change', '[data-toggle="price-protection"]', this.togglePriceProtection);
        
        // Payment schedule toggle
        $(document).on('change', '[data-toggle="schedule-options"]', this.toggleScheduleOptions);
    },
    
    // Initialize Persian input formatting
    initPersianInputs: function() {
        // Format currency inputs
        $('.persian-currency-input').on('input', function() {
            const value = $(this).val().replace(/[^\d]/g, '');
            if (value) {
                const formatted = PersianFormatter.formatNumber(value, false);
                $(this).val(formatted);
            }
        });
        
        // Format number inputs
        $('.persian-number-input').on('input', function() {
            const value = $(this).val();
            if (value && !isNaN(value)) {
                $(this).attr('data-original', value);
            }
        });
    },
    
    // Initialize tooltips
    initTooltips: function() {
        $('[data-bs-toggle="tooltip"]').tooltip();
    },
    
    // Handle customer search
    handleCustomerSearch: function() {
        const query = $(this).val();
        const resultsContainer = $('#customer-search-results');
        
        if (query.length < 2) {
            resultsContainer.addClass('d-none');
            return;
        }
        
        // AJAX call to search customers
        $.ajax({
            url: '/gold-installments/ajax/customer-search/',
            data: { q: query },
            success: function(data) {
                if (data.customers && data.customers.length > 0) {
                    let html = '';
                    data.customers.forEach(function(customer) {
                        html += `
                            <a href="#" class="list-group-item list-group-item-action customer-select" 
                               data-customer-id="${customer.id}">
                                <div class="d-flex justify-content-between">
                                    <div>
                                        <h6 class="mb-1">${customer.display_name}</h6>
                                        <small>${customer.phone}</small>
                                    </div>
                                </div>
                            </a>
                        `;
                    });
                    resultsContainer.html(html).removeClass('d-none');
                } else {
                    resultsContainer.addClass('d-none');
                }
            }
        });
    },
    
    // Calculate gold weight equivalent
    calculateGoldWeight: function() {
        const amount = parseFloat($(this).val()) || 0;
        const goldPrice = parseFloat($('#current-gold-price').data('price')) || 3500000;
        
        if (amount > 0) {
            const goldWeight = amount / goldPrice;
            const displayElement = $(this).closest('.form-group').find('.gold-weight-display');
            
            if (displayElement.length) {
                displayElement.text(PersianFormatter.formatWeight(goldWeight, 'gram'));
            }
            
            // Trigger custom event
            $(document).trigger('goldWeightCalculated', {
                amount: amount,
                goldPrice: goldPrice,
                goldWeight: goldWeight
            });
        }
    },
    
    // Set quick payment amount
    setQuickAmount: function(e) {
        e.preventDefault();
        const amount = $(this).data('amount');
        const targetInput = $('.payment-amount-input');
        
        if (targetInput.length) {
            targetInput.val(amount).trigger('input');
        }
    },
    
    // Validate form before submission
    validateForm: function(e) {
        const form = $(this);
        let isValid = true;
        
        // Check required fields
        form.find('[required]').each(function() {
            if (!$(this).val()) {
                isValid = false;
                $(this).addClass('is-invalid');
            } else {
                $(this).removeClass('is-invalid');
            }
        });
        
        // Custom validations
        const paymentAmount = parseFloat(form.find('.payment-amount-input').val()) || 0;
        if (paymentAmount <= 0) {
            isValid = false;
            form.find('.payment-amount-input').addClass('is-invalid');
        }
        
        if (!isValid) {
            e.preventDefault();
            this.showValidationError('لطفاً تمام فیلدهای الزامی را تکمیل کنید.');
        }
        
        return isValid;
    },
    
    // Toggle price protection options
    togglePriceProtection: function() {
        const isChecked = $(this).is(':checked');
        const optionsContainer = $('#price-protection-options');
        
        if (isChecked) {
            optionsContainer.removeClass('d-none');
        } else {
            optionsContainer.addClass('d-none');
            optionsContainer.find('input').val('');
        }
    },
    
    // Toggle schedule options
    toggleScheduleOptions: function() {
        const selectedValue = $(this).val();
        const customOptions = $('.custom-schedule-options');
        
        if (selectedValue === 'custom') {
            customOptions.removeClass('d-none');
        } else {
            customOptions.addClass('d-none');
        }
    },
    
    // Show validation error
    showValidationError: function(message) {
        const alert = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        $('.container-fluid').prepend(alert);
        
        // Auto dismiss after 5 seconds
        setTimeout(function() {
            $('.alert-danger').fadeOut();
        }, 5000);
    },
    
    // Show success message
    showSuccessMessage: function(message) {
        const alert = `
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                <i class="fas fa-check-circle me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        $('.container-fluid').prepend(alert);
        
        // Auto dismiss after 5 seconds
        setTimeout(function() {
            $('.alert-success').fadeOut();
        }, 5000);
    },
    
    // Initialize contract form
    initContractForm: function() {
        // Customer selection
        $(document).on('click', '.customer-select', function(e) {
            e.preventDefault();
            const customerId = $(this).data('customer-id');
            const customerName = $(this).find('h6').text();
            
            $('#id_customer').val(customerId);
            $('#selected-customer-info').removeClass('d-none');
            $('#customer-details').html(`<strong>${customerName}</strong>`);
            $('#customer-search-results').addClass('d-none');
        });
        
        // Gold value calculator
        $('#id_initial_gold_weight_grams, #id_gold_karat').on('input', function() {
            const weight = parseFloat($('#id_initial_gold_weight_grams').val()) || 0;
            const karat = parseInt($('#id_gold_karat').val()) || 18;
            const currentPrice = parseFloat($('#current-gold-price').data('price')) || 3500000;
            
            if (weight > 0) {
                const totalValue = weight * currentPrice;
                const pureGoldWeight = (weight * karat) / 24;
                const pureGoldValue = pureGoldWeight * currentPrice;
                
                $('#total-gold-value').text(PersianFormatter.formatCurrency(totalValue));
                $('#pure-gold-value').text(PersianFormatter.formatCurrency(pureGoldValue));
            }
        });
    },
    
    // Initialize payment form
    initPaymentForm: function() {
        // Payment calculator
        $('#id_payment_amount_toman').on('input', function() {
            const amount = parseFloat($(this).val()) || 0;
            const goldPrice = parseFloat($('#id_gold_price_per_gram_at_payment').val()) || 3500000;
            
            if (amount > 0 && goldPrice > 0) {
                const goldWeight = amount / goldPrice;
                $('#gold-weight-equivalent').text(PersianFormatter.formatWeight(goldWeight, 'gram'));
            }
        });
        
        // Payment method specific fields
        $('#id_payment_method').change(function() {
            const method = $(this).val();
            const referenceField = $('#id_reference_number').closest('.mb-3');
            
            if (method === 'bank_transfer' || method === 'cheque') {
                referenceField.show();
                $('#id_reference_number').attr('required', true);
            } else {
                referenceField.hide();
                $('#id_reference_number').attr('required', false);
            }
        });
    },
    
    // Export contract to PDF
    exportToPDF: function(contractId) {
        window.open(`/gold-installments/contract/${contractId}/export/pdf/`, '_blank');
    },
    
    // Print contract
    printContract: function() {
        window.print();
    }
};

// Initialize when document is ready
$(document).ready(function() {
    GoldInstallments.init();
});

// Export for global access
window.GoldInstallments = GoldInstallments;
window.PersianFormatter = PersianFormatter;