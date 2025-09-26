"""
Gold installment system forms for ZARGAR jewelry SaaS platform.
Provides comprehensive forms for contract management and payment processing.
"""
from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date, timedelta

from zargar.core.widgets import PersianNumberWidget
from zargar.customers.models import Customer
from .models import GoldInstallmentContract, GoldInstallmentPayment, GoldWeightAdjustment


class GoldInstallmentContractForm(forms.ModelForm):
    """Form for creating and editing gold installment contracts."""
    
    # Customer selection with search
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-select persian-select',
            'data-search': 'true'
        }),
        label=_('Customer'),
        help_text=_('Select customer for this contract')
    )
    
    # Contract date with Persian calendar
    contract_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control persian-date-picker',
            'placeholder': _('Select contract date'),
            'type': 'date'
        }),
        label=_('Contract Date'),
        initial=date.today
    )
    
    # Gold specifications
    initial_gold_weight_grams = forms.DecimalField(
        max_digits=10,
        decimal_places=3,
        min_value=Decimal('0.001'),
        widget=PersianNumberWidget(attrs={
            'class': 'form-control persian-number-input',
            'placeholder': _('Enter gold weight in grams'),
            'step': '0.001'
        }),
        label=_('Initial Gold Weight (Grams)'),
        help_text=_('Total gold weight at contract start')
    )
    
    gold_karat = forms.IntegerField(
        min_value=1,
        max_value=24,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter gold karat (1-24)')
        }),
        label=_('Gold Karat (عیار)'),
        initial=18
    )
    
    # Payment terms
    payment_schedule = forms.ChoiceField(
        choices=GoldInstallmentContract.PAYMENT_SCHEDULE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label=_('Payment Schedule'),
        initial='monthly'
    )
    
    payment_amount_per_period = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=PersianNumberWidget(attrs={
            'class': 'form-control persian-currency-input',
            'placeholder': _('Enter payment amount (optional)')
        }),
        label=_('Payment Amount per Period (Toman)'),
        help_text=_('Fixed payment amount if applicable')
    )
    
    # Price protection
    has_price_protection = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'data-toggle': 'price-protection'
        }),
        label=_('Enable Price Protection'),
        help_text=_('Protect against gold price fluctuations')
    )
    
    price_ceiling_per_gram = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=PersianNumberWidget(attrs={
            'class': 'form-control persian-currency-input',
            'placeholder': _('Maximum price per gram')
        }),
        label=_('Price Ceiling per Gram (Toman)'),
        help_text=_('Maximum gold price for calculations')
    )
    
    price_floor_per_gram = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=PersianNumberWidget(attrs={
            'class': 'form-control persian-currency-input',
            'placeholder': _('Minimum price per gram')
        }),
        label=_('Price Floor per Gram (Toman)'),
        help_text=_('Minimum gold price for calculations')
    )
    
    # Early payment discount
    early_payment_discount_percentage = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('0.00'),
        max_value=Decimal('50.00'),
        widget=PersianNumberWidget(attrs={
            'class': 'form-control persian-percentage-input',
            'placeholder': _('Discount percentage (0-50%)')
        }),
        label=_('Early Payment Discount (%)'),
        initial=Decimal('0.00'),
        help_text=_('Discount for early contract completion')
    )
    
    # Contract terms
    contract_terms_persian = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control persian-textarea',
            'rows': 6,
            'placeholder': _('Enter contract terms in Persian')
        }),
        label=_('Contract Terms (Persian)'),
        help_text=_('Legal terms and conditions in Persian')
    )
    
    special_conditions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control persian-textarea',
            'rows': 3,
            'placeholder': _('Additional conditions (optional)')
        }),
        label=_('Special Conditions'),
        help_text=_('Additional contract-specific conditions')
    )
    
    class Meta:
        model = GoldInstallmentContract
        fields = [
            'customer', 'contract_date', 'initial_gold_weight_grams', 'gold_karat',
            'payment_schedule', 'payment_amount_per_period', 'has_price_protection',
            'price_ceiling_per_gram', 'price_floor_per_gram', 'early_payment_discount_percentage',
            'contract_terms_persian', 'special_conditions'
        ]
    
    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        
        if self.tenant:
            self.fields['customer'].queryset = Customer.objects.filter(tenant=self.tenant)
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate price protection settings
        has_price_protection = cleaned_data.get('has_price_protection')
        price_ceiling = cleaned_data.get('price_ceiling_per_gram')
        price_floor = cleaned_data.get('price_floor_per_gram')
        
        if has_price_protection:
            if not price_ceiling and not price_floor:
                raise ValidationError({
                    'has_price_protection': _('Price ceiling or floor must be set when price protection is enabled')
                })
            
            if price_ceiling and price_floor and price_ceiling <= price_floor:
                raise ValidationError({
                    'price_ceiling_per_gram': _('Price ceiling must be higher than price floor')
                })
        
        return cleaned_data


class GoldInstallmentPaymentForm(forms.ModelForm):
    """Form for processing gold installment payments."""
    
    # Payment details
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control persian-date-picker',
            'placeholder': _('Select payment date'),
            'type': 'date'
        }),
        label=_('Payment Date'),
        initial=date.today
    )
    
    payment_amount_toman = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=PersianNumberWidget(attrs={
            'class': 'form-control persian-currency-input',
            'placeholder': _('Enter payment amount'),
            'data-calculator': 'gold-weight'
        }),
        label=_('Payment Amount (Toman)'),
        help_text=_('Amount paid by customer')
    )
    
    # Gold price information
    gold_price_per_gram_at_payment = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=PersianNumberWidget(attrs={
            'class': 'form-control persian-currency-input',
            'placeholder': _('Current gold price per gram'),
            'readonly': True
        }),
        label=_('Gold Price per Gram (Toman)'),
        help_text=_('Current market gold price')
    )
    
    # Payment method
    payment_method = forms.ChoiceField(
        choices=GoldInstallmentPayment.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label=_('Payment Method'),
        initial='cash'
    )
    
    # Reference information
    reference_number = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Bank reference, cheque number, etc.')
        }),
        label=_('Reference Number'),
        help_text=_('Bank reference, cheque number, etc.')
    )
    
    # Notes
    payment_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control persian-textarea',
            'rows': 3,
            'placeholder': _('Additional notes (optional)')
        }),
        label=_('Payment Notes'),
        help_text=_('Additional information about this payment')
    )
    
    class Meta:
        model = GoldInstallmentPayment
        fields = [
            'payment_date', 'payment_amount_toman', 'gold_price_per_gram_at_payment',
            'payment_method', 'reference_number', 'payment_notes'
        ]
    
    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
    
    def clean_payment_amount_toman(self):
        amount = self.cleaned_data['payment_amount_toman']
        if amount <= 0:
            raise ValidationError(_('Payment amount must be greater than zero'))
        return amount
    
    def clean_gold_price_per_gram_at_payment(self):
        price = self.cleaned_data['gold_price_per_gram_at_payment']
        if price <= 0:
            raise ValidationError(_('Gold price must be greater than zero'))
        return price


class GoldWeightAdjustmentForm(forms.ModelForm):
    """Form for manual gold weight adjustments."""
    
    # Adjustment details
    adjustment_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control persian-date-picker',
            'placeholder': _('Select adjustment date'),
            'type': 'date'
        }),
        label=_('Adjustment Date'),
        initial=date.today
    )
    
    # Weight information
    weight_before_grams = forms.DecimalField(
        max_digits=10,
        decimal_places=3,
        widget=PersianNumberWidget(attrs={
            'class': 'form-control persian-number-input',
            'readonly': True
        }),
        label=_('Weight Before Adjustment (Grams)'),
        help_text=_('Current gold weight before adjustment')
    )
    
    adjustment_amount_grams = forms.DecimalField(
        max_digits=10,
        decimal_places=3,
        widget=PersianNumberWidget(attrs={
            'class': 'form-control persian-number-input',
            'placeholder': _('Enter adjustment amount (+ or -)'),
            'step': '0.001'
        }),
        label=_('Adjustment Amount (Grams)'),
        help_text=_('Positive for increase, negative for decrease')
    )
    
    # Adjustment classification
    adjustment_type = forms.ChoiceField(
        choices=GoldWeightAdjustment.ADJUSTMENT_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label=_('Adjustment Type')
    )
    
    adjustment_reason = forms.ChoiceField(
        choices=GoldWeightAdjustment.ADJUSTMENT_REASON_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label=_('Adjustment Reason')
    )
    
    # Documentation
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control persian-textarea',
            'rows': 4,
            'placeholder': _('Detailed description of the adjustment')
        }),
        label=_('Description'),
        help_text=_('Detailed explanation of why this adjustment is needed')
    )
    
    supporting_documents = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': _('References to supporting documentation')
        }),
        label=_('Supporting Documents'),
        help_text=_('References to supporting documentation')
    )
    
    # Authorization
    authorization_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control persian-textarea',
            'rows': 2,
            'placeholder': _('Authorization notes (optional)')
        }),
        label=_('Authorization Notes'),
        help_text=_('Additional notes from authorizing user')
    )
    
    class Meta:
        model = GoldWeightAdjustment
        fields = [
            'adjustment_date', 'weight_before_grams', 'adjustment_amount_grams',
            'adjustment_type', 'adjustment_reason', 'description',
            'supporting_documents', 'authorization_notes'
        ]
    
    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
    
    def clean_adjustment_amount_grams(self):
        amount = self.cleaned_data['adjustment_amount_grams']
        weight_before = self.cleaned_data.get('weight_before_grams', Decimal('0'))
        
        # Check that adjustment doesn't result in negative weight
        if weight_before + amount < 0:
            raise ValidationError(
                _('Adjustment would result in negative weight. Maximum decrease is {max_decrease} grams.').format(
                    max_decrease=weight_before
                )
            )
        
        return amount


class PaymentScheduleForm(forms.Form):
    """Form for configuring payment schedules."""
    
    SCHEDULE_TYPES = [
        ('weekly', _('Weekly')),
        ('bi_weekly', _('Bi-weekly')),
        ('monthly', _('Monthly')),
        ('custom', _('Custom Schedule')),
    ]
    
    schedule_type = forms.ChoiceField(
        choices=SCHEDULE_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-toggle': 'schedule-options'
        }),
        label=_('Payment Schedule Type')
    )
    
    payment_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=PersianNumberWidget(attrs={
            'class': 'form-control persian-currency-input',
            'placeholder': _('Fixed payment amount (optional)')
        }),
        label=_('Fixed Payment Amount (Toman)'),
        help_text=_('Leave empty for flexible payment amounts')
    )
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control persian-date-picker',
            'placeholder': _('First payment date'),
            'type': 'date'
        }),
        label=_('First Payment Date'),
        initial=lambda: date.today() + timedelta(days=7)
    )
    
    number_of_payments = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=120,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Number of payments (optional)')
        }),
        label=_('Number of Payments'),
        help_text=_('Total number of scheduled payments')
    )
    
    # Custom schedule options
    custom_interval_days = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=365,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Days between payments')
        }),
        label=_('Custom Interval (Days)'),
        help_text=_('For custom schedules only')
    )
    
    def clean(self):
        cleaned_data = super().clean()
        schedule_type = cleaned_data.get('schedule_type')
        custom_interval = cleaned_data.get('custom_interval_days')
        
        if schedule_type == 'custom' and not custom_interval:
            raise ValidationError({
                'custom_interval_days': _('Custom interval is required for custom schedules')
            })
        
        return cleaned_data


class QuickPaymentForm(forms.Form):
    """Simplified form for quick payments from dashboard."""
    
    contract = forms.ModelChoiceField(
        queryset=GoldInstallmentContract.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-search': 'true'
        }),
        label=_('Contract')
    )
    
    payment_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=PersianNumberWidget(attrs={
            'class': 'form-control persian-currency-input',
            'placeholder': _('Payment amount')
        }),
        label=_('Payment Amount (Toman)')
    )
    
    payment_method = forms.ChoiceField(
        choices=GoldInstallmentPayment.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label=_('Payment Method'),
        initial='cash'
    )
    
    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        
        if tenant:
            self.fields['contract'].queryset = GoldInstallmentContract.objects.filter(
                tenant=tenant,
                status='active'
            )