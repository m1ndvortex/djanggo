"""
Gold installment system models for ZARGAR jewelry SaaS platform.
Provides comprehensive gold installment contract management with weight-based calculations.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from zargar.core.models import TenantAwareModel
from zargar.core.persian_number_formatter import PersianNumberFormatter
from zargar.core.calendar_utils import PersianCalendarUtils
import jdatetime
from typing import Dict, Optional, Tuple


class GoldInstallmentContract(TenantAwareModel):
    """
    Gold installment contract model with weight-based calculations.
    Manages gold sales with flexible payment plans based on daily gold prices.
    """
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('completed', _('Completed')),
        ('defaulted', _('Defaulted')),
        ('cancelled', _('Cancelled')),
        ('suspended', _('Suspended')),
    ]
    
    PAYMENT_SCHEDULE_CHOICES = [
        ('weekly', _('Weekly')),
        ('bi_weekly', _('Bi-weekly')),
        ('monthly', _('Monthly')),
        ('custom', _('Custom Schedule')),
    ]
    
    BALANCE_TYPE_CHOICES = [
        ('debt', _('Customer Owes Gold')),
        ('credit', _('Shop Owes Customer')),
    ]
    
    # Contract identification
    contract_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Contract Number'),
        help_text=_('Unique contract identifier')
    )
    
    # Customer relationship
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='gold_installment_contracts',
        verbose_name=_('Customer')
    )
    
    # Contract dates
    contract_date = models.DateField(
        verbose_name=_('Contract Date (Gregorian)')
    )
    contract_date_shamsi = models.CharField(
        max_length=10,
        verbose_name=_('Contract Date (Shamsi)'),
        help_text=_('Format: 1403/01/01')
    )
    
    # Gold specifications
    initial_gold_weight_grams = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        verbose_name=_('Initial Gold Weight (Grams)'),
        help_text=_('Total gold weight at contract start')
    )
    remaining_gold_weight_grams = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.000'))],
        verbose_name=_('Remaining Gold Weight (Grams)'),
        help_text=_('Current outstanding gold weight')
    )
    gold_karat = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(24)],
        default=18,
        verbose_name=_('Gold Karat (عیار)'),
        help_text=_('Gold purity level')
    )
    
    # Payment terms
    payment_schedule = models.CharField(
        max_length=20,
        choices=PAYMENT_SCHEDULE_CHOICES,
        default='monthly',
        verbose_name=_('Payment Schedule')
    )
    payment_amount_per_period = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Payment Amount per Period (Toman)'),
        help_text=_('Fixed payment amount if applicable')
    )
    
    # Contract status and balance
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name=_('Contract Status')
    )
    balance_type = models.CharField(
        max_length=10,
        choices=BALANCE_TYPE_CHOICES,
        default='debt',
        verbose_name=_('Balance Type'),
        help_text=_('Whether customer owes gold or shop owes customer')
    )
    
    # Price protection settings
    has_price_protection = models.BooleanField(
        default=False,
        verbose_name=_('Has Price Protection'),
        help_text=_('Whether contract has price ceiling/floor protection')
    )
    price_ceiling_per_gram = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Price Ceiling per Gram (Toman)'),
        help_text=_('Maximum gold price for calculations')
    )
    price_floor_per_gram = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Price Floor per Gram (Toman)'),
        help_text=_('Minimum gold price for calculations')
    )
    
    # Early payment discount
    early_payment_discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('50.00'))],
        verbose_name=_('Early Payment Discount (%)'),
        help_text=_('Discount percentage for early contract completion')
    )
    
    # Contract terms and conditions
    contract_terms_persian = models.TextField(
        verbose_name=_('Contract Terms (Persian)'),
        help_text=_('Persian legal terms and conditions')
    )
    special_conditions = models.TextField(
        blank=True,
        verbose_name=_('Special Conditions'),
        help_text=_('Additional contract-specific conditions')
    )
    
    # Completion tracking
    completion_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Completion Date')
    )
    total_payments_received = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Total Payments Received (Toman)')
    )
    total_gold_weight_paid = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=Decimal('0.000'),
        verbose_name=_('Total Gold Weight Paid (Grams)')
    )
    
    # Audit and notes
    internal_notes = models.TextField(
        blank=True,
        verbose_name=_('Internal Notes')
    )
    
    class Meta:
        verbose_name = _('Gold Installment Contract')
        verbose_name_plural = _('Gold Installment Contracts')
        ordering = ['-contract_date', '-created_at']
        indexes = [
            models.Index(fields=['contract_number']),
            models.Index(fields=['customer']),
            models.Index(fields=['status']),
            models.Index(fields=['contract_date']),
            models.Index(fields=['balance_type']),
        ]
    
    def __str__(self):
        return f"{self.contract_number} - {self.customer}"
    
    def save(self, *args, **kwargs):
        """Override save to generate contract number and set Shamsi date."""
        if not self.contract_number:
            self.contract_number = self.generate_contract_number()
        
        # Set Shamsi date if not provided
        if self.contract_date and not self.contract_date_shamsi:
            shamsi_date = PersianCalendarUtils.gregorian_to_shamsi(self.contract_date)
            self.contract_date_shamsi = f"{shamsi_date[0]:04d}/{shamsi_date[1]:02d}/{shamsi_date[2]:02d}"
        
        # Initialize remaining weight if not set
        if not self.pk and self.remaining_gold_weight_grams is None:
            self.remaining_gold_weight_grams = self.initial_gold_weight_grams
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate contract data."""
        super().clean()
        
        # Validate remaining weight doesn't exceed initial weight
        if (self.remaining_gold_weight_grams is not None and 
            self.initial_gold_weight_grams is not None and
            self.remaining_gold_weight_grams > self.initial_gold_weight_grams):
            raise ValidationError({
                'remaining_gold_weight_grams': _('Remaining weight cannot exceed initial weight')
            })
        
        # Validate price protection settings
        if self.has_price_protection:
            if not self.price_ceiling_per_gram and not self.price_floor_per_gram:
                raise ValidationError({
                    'has_price_protection': _('Price ceiling or floor must be set when price protection is enabled')
                })
            
            if (self.price_ceiling_per_gram and self.price_floor_per_gram and 
                self.price_ceiling_per_gram <= self.price_floor_per_gram):
                raise ValidationError({
                    'price_ceiling_per_gram': _('Price ceiling must be higher than price floor')
                })
    
    def generate_contract_number(self) -> str:
        """Generate unique contract number."""
        from django.utils import timezone
        import random
        
        # Format: GIC-YYYYMMDD-XXXX (Gold Installment Contract)
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(random.randint(1000, 9999))
        return f"GIC-{date_str}-{random_str}"
    
    @property
    def is_completed(self) -> bool:
        """Check if contract is completed."""
        return self.status == 'completed' or self.remaining_gold_weight_grams <= Decimal('0.001')
    
    @property
    def is_overdue(self) -> bool:
        """Check if contract has overdue payments."""
        if self.status in ['completed', 'cancelled']:
            return False
        
        # Get last payment date
        last_payment = self.payments.order_by('-payment_date').first()
        if not last_payment:
            # No payments made, check if contract is old
            days_since_contract = (timezone.now().date() - self.contract_date).days
            return days_since_contract > 30  # Consider overdue after 30 days
        
        # Check based on payment schedule
        expected_next_payment_date = self.calculate_next_payment_date(last_payment.payment_date)
        return timezone.now().date() > expected_next_payment_date
    
    @property
    def completion_percentage(self) -> Decimal:
        """Calculate contract completion percentage."""
        if self.initial_gold_weight_grams <= 0:
            return Decimal('0.00')
        
        paid_weight = self.initial_gold_weight_grams - self.remaining_gold_weight_grams
        percentage = (paid_weight / self.initial_gold_weight_grams) * 100
        return percentage.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def calculate_next_payment_date(self, last_payment_date: models.DateField) -> models.DateField:
        """Calculate next expected payment date based on schedule."""
        from datetime import timedelta
        
        if self.payment_schedule == 'weekly':
            return last_payment_date + timedelta(weeks=1)
        elif self.payment_schedule == 'bi_weekly':
            return last_payment_date + timedelta(weeks=2)
        elif self.payment_schedule == 'monthly':
            # Add one month (approximately 30 days)
            return last_payment_date + timedelta(days=30)
        else:  # custom
            return last_payment_date + timedelta(days=30)  # Default to monthly
    
    def calculate_current_gold_value(self, current_gold_price_per_gram: Decimal) -> Dict[str, Decimal]:
        """
        Calculate current value of remaining gold weight.
        
        Args:
            current_gold_price_per_gram: Current market price per gram
            
        Returns:
            Dictionary with value calculations
        """
        # Apply price protection if enabled
        effective_price = current_gold_price_per_gram
        
        if self.has_price_protection:
            if self.price_ceiling_per_gram and effective_price > self.price_ceiling_per_gram:
                effective_price = self.price_ceiling_per_gram
            elif self.price_floor_per_gram and effective_price < self.price_floor_per_gram:
                effective_price = self.price_floor_per_gram
        
        # Calculate pure gold weight based on karat
        pure_gold_weight = (self.remaining_gold_weight_grams * self.gold_karat) / 24
        
        # Calculate values
        total_value = self.remaining_gold_weight_grams * effective_price
        pure_gold_value = pure_gold_weight * effective_price
        
        return {
            'remaining_weight_grams': self.remaining_gold_weight_grams,
            'pure_gold_weight_grams': pure_gold_weight,
            'effective_price_per_gram': effective_price,
            'total_value_toman': total_value,
            'pure_gold_value_toman': pure_gold_value,
            'price_protection_applied': effective_price != current_gold_price_per_gram
        }
    
    def calculate_early_payment_discount(self, current_gold_price_per_gram: Decimal) -> Dict[str, Decimal]:
        """
        Calculate early payment discount if applicable.
        
        Args:
            current_gold_price_per_gram: Current market price per gram
            
        Returns:
            Dictionary with discount calculations
        """
        current_value = self.calculate_current_gold_value(current_gold_price_per_gram)
        total_value = current_value['total_value_toman']
        
        discount_amount = total_value * (self.early_payment_discount_percentage / 100)
        discounted_value = total_value - discount_amount
        
        return {
            'original_value': total_value,
            'discount_percentage': self.early_payment_discount_percentage,
            'discount_amount': discount_amount,
            'discounted_value': discounted_value,
            'savings': discount_amount
        }
    
    def process_payment(self, payment_amount_toman: Decimal, 
                       gold_price_per_gram: Decimal,
                       payment_date: Optional[models.DateField] = None) -> 'GoldInstallmentPayment':
        """
        Process a payment and create payment record.
        
        Args:
            payment_amount_toman: Payment amount in Toman
            gold_price_per_gram: Gold price at time of payment
            payment_date: Payment date, defaults to today
            
        Returns:
            Created GoldInstallmentPayment instance
        """
        if payment_date is None:
            payment_date = timezone.now().date()
        
        # Apply price protection
        effective_price = gold_price_per_gram
        if self.has_price_protection:
            if self.price_ceiling_per_gram and effective_price > self.price_ceiling_per_gram:
                effective_price = self.price_ceiling_per_gram
            elif self.price_floor_per_gram and effective_price < self.price_floor_per_gram:
                effective_price = self.price_floor_per_gram
        
        # Calculate gold weight equivalent
        gold_weight_equivalent = payment_amount_toman / effective_price
        
        # Create payment record
        payment = GoldInstallmentPayment.objects.create(
            contract=self,
            payment_amount_toman=payment_amount_toman,
            gold_price_per_gram_at_payment=gold_price_per_gram,
            effective_gold_price_per_gram=effective_price,
            gold_weight_equivalent_grams=gold_weight_equivalent,
            payment_date=payment_date,
            payment_method='cash'  # Default, can be overridden
        )
        
        # Update contract balances
        self.remaining_gold_weight_grams -= gold_weight_equivalent
        self.total_payments_received += payment_amount_toman
        self.total_gold_weight_paid += gold_weight_equivalent
        
        # Check if contract is completed
        if self.remaining_gold_weight_grams <= Decimal('0.001'):
            self.status = 'completed'
            self.completion_date = payment_date
            self.remaining_gold_weight_grams = Decimal('0.000')
        
        self.save(update_fields=[
            'remaining_gold_weight_grams',
            'total_payments_received', 
            'total_gold_weight_paid',
            'status',
            'completion_date',
            'updated_at'
        ])
        
        return payment
    
    def get_payment_history_summary(self) -> Dict:
        """Get summary of payment history."""
        payments = self.payments.all()
        
        return {
            'total_payments': payments.count(),
            'total_amount_paid': sum(p.payment_amount_toman for p in payments),
            'total_gold_weight_paid': sum(p.gold_weight_equivalent_grams for p in payments),
            'average_payment_amount': payments.aggregate(
                avg=models.Avg('payment_amount_toman')
            )['avg'] or Decimal('0.00'),
            'last_payment_date': payments.order_by('-payment_date').first().payment_date if payments.exists() else None,
            'first_payment_date': payments.order_by('payment_date').first().payment_date if payments.exists() else None
        }
    
    def format_for_display(self) -> Dict[str, str]:
        """Format contract data for display with Persian formatting."""
        formatter = PersianNumberFormatter()
        
        return {
            'contract_number': self.contract_number,
            'customer_name': str(self.customer),
            'contract_date_shamsi': self.contract_date_shamsi,
            'initial_weight_display': formatter.format_weight(
                self.initial_gold_weight_grams, 'gram', use_persian_digits=True
            ),
            'remaining_weight_display': formatter.format_weight(
                self.remaining_gold_weight_grams, 'gram', use_persian_digits=True
            ),
            'completion_percentage_display': formatter.format_percentage(
                self.completion_percentage, use_persian_digits=True
            ),
            'status_display': self.get_status_display(),
            'balance_type_display': self.get_balance_type_display(),
            'payment_schedule_display': self.get_payment_schedule_display()
        }


class GoldInstallmentPayment(TenantAwareModel):
    """
    Individual payment record for gold installment contracts.
    Tracks payment processing and gold weight reduction calculations.
    """
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', _('Cash')),
        ('bank_transfer', _('Bank Transfer')),
        ('card', _('Card Payment')),
        ('cheque', _('Cheque')),
        ('gold_exchange', _('Gold Exchange')),
        ('other', _('Other')),
    ]
    
    PAYMENT_TYPE_CHOICES = [
        ('regular', _('Regular Payment')),
        ('early_completion', _('Early Completion')),
        ('partial', _('Partial Payment')),
        ('adjustment', _('Manual Adjustment')),
    ]
    
    # Contract relationship
    contract = models.ForeignKey(
        GoldInstallmentContract,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name=_('Gold Installment Contract')
    )
    
    # Payment details
    payment_date = models.DateField(
        verbose_name=_('Payment Date')
    )
    payment_date_shamsi = models.CharField(
        max_length=10,
        verbose_name=_('Payment Date (Shamsi)'),
        help_text=_('Format: 1403/01/01')
    )
    
    # Payment amounts
    payment_amount_toman = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Payment Amount (Toman)')
    )
    
    # Gold price information
    gold_price_per_gram_at_payment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Gold Price per Gram at Payment (Toman)'),
        help_text=_('Market gold price at time of payment')
    )
    effective_gold_price_per_gram = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Effective Gold Price per Gram (Toman)'),
        help_text=_('Actual price used for calculation (after price protection)')
    )
    
    # Gold weight calculations
    gold_weight_equivalent_grams = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        verbose_name=_('Gold Weight Equivalent (Grams)'),
        help_text=_('Gold weight equivalent of payment amount')
    )
    
    # Payment metadata
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash',
        verbose_name=_('Payment Method')
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default='regular',
        verbose_name=_('Payment Type')
    )
    
    # Reference information
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Reference Number'),
        help_text=_('Bank reference, cheque number, etc.')
    )
    
    # Discount information (for early payments)
    discount_applied = models.BooleanField(
        default=False,
        verbose_name=_('Discount Applied')
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Discount Percentage')
    )
    discount_amount_toman = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Discount Amount (Toman)')
    )
    
    # Notes
    payment_notes = models.TextField(
        blank=True,
        verbose_name=_('Payment Notes')
    )
    
    class Meta:
        verbose_name = _('Gold Installment Payment')
        verbose_name_plural = _('Gold Installment Payments')
        ordering = ['-payment_date', '-created_at']
        indexes = [
            models.Index(fields=['contract']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['payment_method']),
            models.Index(fields=['payment_type']),
        ]
    
    def __str__(self):
        formatter = PersianNumberFormatter()
        amount_display = formatter.format_currency(self.payment_amount_toman)
        return f"{self.contract.contract_number} - {amount_display} - {self.payment_date}"
    
    def save(self, *args, **kwargs):
        """Override save to set Shamsi date and calculate gold weight."""
        # Set Shamsi date if not provided
        if self.payment_date and not self.payment_date_shamsi:
            shamsi_date = PersianCalendarUtils.gregorian_to_shamsi(self.payment_date)
            self.payment_date_shamsi = f"{shamsi_date[0]:04d}/{shamsi_date[1]:02d}/{shamsi_date[2]:02d}"
        
        # Calculate gold weight equivalent if not set
        if (not self.gold_weight_equivalent_grams and 
            self.payment_amount_toman and 
            self.effective_gold_price_per_gram):
            self.gold_weight_equivalent_grams = (
                self.payment_amount_toman / self.effective_gold_price_per_gram
            ).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate payment data."""
        super().clean()
        
        # Validate effective price is not zero
        if self.effective_gold_price_per_gram <= 0:
            raise ValidationError({
                'effective_gold_price_per_gram': _('Gold price must be greater than zero')
            })
        
        # Validate discount percentage
        if self.discount_applied and self.discount_percentage <= 0:
            raise ValidationError({
                'discount_percentage': _('Discount percentage must be greater than zero when discount is applied')
            })
    
    @property
    def price_protection_applied(self) -> bool:
        """Check if price protection was applied to this payment."""
        return self.gold_price_per_gram_at_payment != self.effective_gold_price_per_gram
    
    def format_for_display(self) -> Dict[str, str]:
        """Format payment data for display with Persian formatting."""
        formatter = PersianNumberFormatter()
        
        return {
            'payment_date_shamsi': self.payment_date_shamsi,
            'payment_amount_display': formatter.format_currency(
                self.payment_amount_toman, use_persian_digits=True
            ),
            'gold_price_display': formatter.format_currency(
                self.gold_price_per_gram_at_payment, use_persian_digits=True
            ),
            'effective_price_display': formatter.format_currency(
                self.effective_gold_price_per_gram, use_persian_digits=True
            ),
            'gold_weight_display': formatter.format_weight(
                self.gold_weight_equivalent_grams, 'gram', use_persian_digits=True
            ),
            'payment_method_display': self.get_payment_method_display(),
            'payment_type_display': self.get_payment_type_display(),
            'discount_display': formatter.format_percentage(
                self.discount_percentage, use_persian_digits=True
            ) if self.discount_applied else '۰٪'
        }


class GoldWeightAdjustment(TenantAwareModel):
    """
    Manual balance adjustments for gold installment contracts with comprehensive audit trail.
    Allows administrative corrections to gold weight balances.
    """
    
    ADJUSTMENT_TYPE_CHOICES = [
        ('increase', _('Increase Balance')),
        ('decrease', _('Decrease Balance')),
        ('correction', _('Correction')),
        ('penalty', _('Penalty')),
        ('bonus', _('Bonus')),
        ('transfer', _('Transfer')),
    ]
    
    ADJUSTMENT_REASON_CHOICES = [
        ('data_entry_error', _('Data Entry Error')),
        ('calculation_error', _('Calculation Error')),
        ('customer_dispute', _('Customer Dispute Resolution')),
        ('system_migration', _('System Migration')),
        ('policy_change', _('Policy Change')),
        ('goodwill', _('Goodwill Gesture')),
        ('penalty_application', _('Penalty Application')),
        ('bonus_application', _('Bonus Application')),
        ('other', _('Other')),
    ]
    
    # Contract relationship
    contract = models.ForeignKey(
        GoldInstallmentContract,
        on_delete=models.CASCADE,
        related_name='weight_adjustments',
        verbose_name=_('Gold Installment Contract')
    )
    
    # Adjustment details
    adjustment_date = models.DateField(
        verbose_name=_('Adjustment Date')
    )
    adjustment_date_shamsi = models.CharField(
        max_length=10,
        verbose_name=_('Adjustment Date (Shamsi)')
    )
    
    # Weight changes
    weight_before_grams = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        verbose_name=_('Weight Before Adjustment (Grams)'),
        help_text=_('Gold weight before this adjustment')
    )
    adjustment_amount_grams = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        verbose_name=_('Adjustment Amount (Grams)'),
        help_text=_('Positive for increase, negative for decrease')
    )
    weight_after_grams = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        verbose_name=_('Weight After Adjustment (Grams)'),
        help_text=_('Gold weight after this adjustment')
    )
    
    # Adjustment classification
    adjustment_type = models.CharField(
        max_length=20,
        choices=ADJUSTMENT_TYPE_CHOICES,
        verbose_name=_('Adjustment Type')
    )
    adjustment_reason = models.CharField(
        max_length=30,
        choices=ADJUSTMENT_REASON_CHOICES,
        verbose_name=_('Adjustment Reason')
    )
    
    # Documentation
    description = models.TextField(
        verbose_name=_('Description'),
        help_text=_('Detailed description of the adjustment')
    )
    supporting_documents = models.TextField(
        blank=True,
        verbose_name=_('Supporting Documents'),
        help_text=_('References to supporting documentation')
    )
    
    # Authorization
    authorized_by = models.ForeignKey(
        'core.User',
        on_delete=models.PROTECT,
        related_name='authorized_adjustments',
        verbose_name=_('Authorized By'),
        help_text=_('User who authorized this adjustment')
    )
    authorization_notes = models.TextField(
        blank=True,
        verbose_name=_('Authorization Notes')
    )
    
    # Audit trail
    is_reversed = models.BooleanField(
        default=False,
        verbose_name=_('Is Reversed'),
        help_text=_('Whether this adjustment has been reversed')
    )
    reversed_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reversed_adjustments',
        verbose_name=_('Reversed By')
    )
    reversal_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Reversal Date')
    )
    reversal_reason = models.TextField(
        blank=True,
        verbose_name=_('Reversal Reason')
    )
    
    # Reference to related adjustment (for reversals)
    related_adjustment = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Related Adjustment'),
        help_text=_('Original adjustment if this is a reversal')
    )
    
    class Meta:
        verbose_name = _('Gold Weight Adjustment')
        verbose_name_plural = _('Gold Weight Adjustments')
        ordering = ['-adjustment_date', '-created_at']
        indexes = [
            models.Index(fields=['contract']),
            models.Index(fields=['adjustment_date']),
            models.Index(fields=['adjustment_type']),
            models.Index(fields=['authorized_by']),
            models.Index(fields=['is_reversed']),
        ]
    
    def __str__(self):
        formatter = PersianNumberFormatter()
        weight_display = formatter.format_weight(
            abs(self.adjustment_amount_grams), 'gram', use_persian_digits=True
        )
        sign = '+' if self.adjustment_amount_grams >= 0 else '-'
        return f"{self.contract.contract_number} - {sign}{weight_display} - {self.adjustment_date}"
    
    def save(self, *args, **kwargs):
        """Override save to set calculated fields and Shamsi date."""
        # Set Shamsi date if not provided
        if self.adjustment_date and not self.adjustment_date_shamsi:
            shamsi_date = PersianCalendarUtils.gregorian_to_shamsi(self.adjustment_date)
            self.adjustment_date_shamsi = f"{shamsi_date[0]:04d}/{shamsi_date[1]:02d}/{shamsi_date[2]:02d}"
        
        # Calculate weight after adjustment
        if self.weight_before_grams is not None and self.adjustment_amount_grams is not None:
            self.weight_after_grams = self.weight_before_grams + self.adjustment_amount_grams
        
        super().save(*args, **kwargs)
        
        # Update contract balance if not reversed
        if not self.is_reversed:
            self.contract.remaining_gold_weight_grams = self.weight_after_grams
            self.contract.save(update_fields=['remaining_gold_weight_grams', 'updated_at'])
    
    def clean(self):
        """Validate adjustment data."""
        super().clean()
        
        # Validate weight calculations
        if (self.weight_before_grams is not None and 
            self.adjustment_amount_grams is not None):
            calculated_after = self.weight_before_grams + self.adjustment_amount_grams
            
            if calculated_after < 0:
                raise ValidationError({
                    'adjustment_amount_grams': _('Adjustment would result in negative weight balance')
                })
        
        # Validate reversal fields
        if self.is_reversed:
            if not self.reversed_by:
                raise ValidationError({
                    'reversed_by': _('Reversed by user is required when adjustment is reversed')
                })
            if not self.reversal_reason:
                raise ValidationError({
                    'reversal_reason': _('Reversal reason is required when adjustment is reversed')
                })
    
    def reverse_adjustment(self, reversed_by_user, reversal_reason: str) -> 'GoldWeightAdjustment':
        """
        Reverse this adjustment by creating a counter-adjustment.
        
        Args:
            reversed_by_user: User performing the reversal
            reversal_reason: Reason for reversal
            
        Returns:
            New GoldWeightAdjustment instance that reverses this one
        """
        if self.is_reversed:
            raise ValidationError(_('This adjustment has already been reversed'))
        
        # Create counter-adjustment
        reversal_adjustment = GoldWeightAdjustment.objects.create(
            contract=self.contract,
            adjustment_date=timezone.now().date(),
            weight_before_grams=self.contract.remaining_gold_weight_grams,
            adjustment_amount_grams=-self.adjustment_amount_grams,  # Opposite amount
            adjustment_type='correction',
            adjustment_reason='other',
            description=f"Reversal of adjustment from {self.adjustment_date}: {reversal_reason}",
            authorized_by=reversed_by_user,
            authorization_notes=f"Reversal of adjustment ID {self.id}",
            related_adjustment=self
        )
        
        # Mark this adjustment as reversed
        self.is_reversed = True
        self.reversed_by = reversed_by_user
        self.reversal_date = timezone.now()
        self.reversal_reason = reversal_reason
        self.save(update_fields=[
            'is_reversed', 'reversed_by', 'reversal_date', 'reversal_reason', 'updated_at'
        ])
        
        return reversal_adjustment
    
    @property
    def is_increase(self) -> bool:
        """Check if this adjustment increases the balance."""
        return self.adjustment_amount_grams > 0
    
    @property
    def is_decrease(self) -> bool:
        """Check if this adjustment decreases the balance."""
        return self.adjustment_amount_grams < 0
    
    def format_for_display(self) -> Dict[str, str]:
        """Format adjustment data for display with Persian formatting."""
        formatter = PersianNumberFormatter()
        
        return {
            'adjustment_date_shamsi': self.adjustment_date_shamsi,
            'weight_before_display': formatter.format_weight(
                self.weight_before_grams, 'gram', use_persian_digits=True
            ),
            'adjustment_amount_display': formatter.format_weight(
                abs(self.adjustment_amount_grams), 'gram', use_persian_digits=True
            ),
            'weight_after_display': formatter.format_weight(
                self.weight_after_grams, 'gram', use_persian_digits=True
            ),
            'adjustment_type_display': self.get_adjustment_type_display(),
            'adjustment_reason_display': self.get_adjustment_reason_display(),
            'authorized_by_display': str(self.authorized_by),
            'is_increase': self.is_increase,
            'is_decrease': self.is_decrease,
            'is_reversed': self.is_reversed
        }
