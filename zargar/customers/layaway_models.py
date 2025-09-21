"""
Layaway and installment plan models for zargar project.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import jdatetime
from zargar.core.models import TenantAwareModel


class LayawayPlan(TenantAwareModel):
    """
    Traditional layaway plan model for expensive jewelry purchases.
    """
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
        ('defaulted', _('Defaulted')),
        ('on_hold', _('On Hold')),
    ]
    
    PAYMENT_FREQUENCY_CHOICES = [
        ('weekly', _('Weekly')),
        ('bi_weekly', _('Bi-Weekly')),
        ('monthly', _('Monthly')),
        ('custom', _('Custom Schedule')),
    ]
    
    # Basic information
    plan_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Plan Number')
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='layaway_plans',
        verbose_name=_('Customer')
    )
    jewelry_item = models.ForeignKey(
        'jewelry.JewelryItem',
        on_delete=models.PROTECT,
        related_name='layaway_plans',
        verbose_name=_('Jewelry Item')
    )
    
    # Financial details
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Total Amount (Toman)')
    )
    down_payment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Down Payment (Toman)')
    )
    remaining_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Remaining Balance (Toman)')
    )
    
    # Payment terms
    payment_frequency = models.CharField(
        max_length=20,
        choices=PAYMENT_FREQUENCY_CHOICES,
        default='monthly',
        verbose_name=_('Payment Frequency')
    )
    installment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Installment Amount (Toman)')
    )
    number_of_payments = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(120)],
        verbose_name=_('Number of Payments')
    )
    
    # Dates
    start_date = models.DateField(
        verbose_name=_('Start Date')
    )
    start_date_shamsi = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Start Date (Shamsi)'),
        help_text=_('Format: 1400/01/01')
    )
    expected_completion_date = models.DateField(
        verbose_name=_('Expected Completion Date')
    )
    actual_completion_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Actual Completion Date')
    )
    
    # Status and tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name=_('Status')
    )
    payments_made = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Payments Made')
    )
    total_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Total Paid (Toman)')
    )
    
    # Late payment tracking
    late_payment_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Late Payment Fee (Toman)')
    )
    grace_period_days = models.PositiveIntegerField(
        default=7,
        verbose_name=_('Grace Period (Days)')
    )
    
    # Contract and legal
    contract_terms = models.TextField(
        verbose_name=_('Contract Terms')
    )
    customer_signature = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Customer Signature')
    )
    signature_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Signature Date')
    )
    
    # Additional information
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes')
    )
    internal_notes = models.TextField(
        blank=True,
        verbose_name=_('Internal Notes')
    )
    
    # Item reservation
    item_reserved = models.BooleanField(
        default=True,
        verbose_name=_('Item Reserved')
    )
    reservation_expiry = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Reservation Expiry Date')
    )
    
    class Meta:
        verbose_name = _('Layaway Plan')
        verbose_name_plural = _('Layaway Plans')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['plan_number']),
            models.Index(fields=['customer']),
            models.Index(fields=['status']),
            models.Index(fields=['start_date']),
            models.Index(fields=['expected_completion_date']),
        ]
    
    def __str__(self):
        return f"{self.plan_number} - {self.customer.full_persian_name}"
    
    def save(self, *args, **kwargs):
        """Generate plan number and calculate fields."""
        if not self.plan_number:
            self.plan_number = self.generate_plan_number()
        
        # Calculate remaining balance
        self.remaining_balance = self.total_amount - self.total_paid
        
        # Convert dates to Shamsi if needed
        if self.start_date and not self.start_date_shamsi:
            shamsi_date = jdatetime.date.fromgregorian(date=self.start_date)
            self.start_date_shamsi = shamsi_date.strftime('%Y/%m/%d')
        
        super().save(*args, **kwargs)
        
        # Reserve jewelry item if plan is active
        if self.status == 'active' and self.item_reserved:
            self.jewelry_item.status = 'reserved'
            self.jewelry_item.save(update_fields=['status'])
    
    def generate_plan_number(self):
        """Generate unique plan number."""
        import random
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(random.randint(1000, 9999))
        return f"LAY-{date_str}-{random_str}"
    
    @property
    def completion_percentage(self):
        """Calculate completion percentage."""
        if self.total_amount > 0:
            return (self.total_paid / self.total_amount) * 100
        return 0
    
    @property
    def is_overdue(self):
        """Check if plan has overdue payments."""
        if self.status != 'active':
            return False
        
        # Get the latest scheduled payment
        latest_payment = self.scheduled_payments.filter(
            due_date__lt=timezone.now().date(),
            is_paid=False
        ).first()
        
        return latest_payment is not None
    
    @property
    def days_overdue(self):
        """Calculate days overdue for the earliest unpaid payment."""
        if not self.is_overdue:
            return 0
        
        earliest_overdue = self.scheduled_payments.filter(
            due_date__lt=timezone.now().date(),
            is_paid=False
        ).order_by('due_date').first()
        
        if earliest_overdue:
            delta = timezone.now().date() - earliest_overdue.due_date
            return max(0, delta.days - self.grace_period_days)
        
        return 0
    
    @property
    def next_payment_due(self):
        """Get next payment due date."""
        next_payment = self.scheduled_payments.filter(
            is_paid=False
        ).order_by('due_date').first()
        
        return next_payment.due_date if next_payment else None
    
    @property
    def next_payment_amount(self):
        """Get next payment amount."""
        next_payment = self.scheduled_payments.filter(
            is_paid=False
        ).order_by('due_date').first()
        
        return next_payment.amount if next_payment else Decimal('0.00')
    
    def calculate_expected_completion_date(self):
        """Calculate expected completion date based on payment schedule."""
        from datetime import timedelta
        
        if self.payment_frequency == 'weekly':
            days_between = 7
        elif self.payment_frequency == 'bi_weekly':
            days_between = 14
        elif self.payment_frequency == 'monthly':
            days_between = 30
        else:
            days_between = 30  # Default to monthly
        
        total_days = days_between * self.number_of_payments
        return self.start_date + timedelta(days=total_days)
    
    def generate_payment_schedule(self):
        """Generate scheduled payments for this layaway plan."""
        from datetime import timedelta
        
        # Clear existing scheduled payments
        self.scheduled_payments.all().delete()
        
        # Calculate payment dates
        current_date = self.start_date
        
        if self.payment_frequency == 'weekly':
            days_between = 7
        elif self.payment_frequency == 'bi_weekly':
            days_between = 14
        elif self.payment_frequency == 'monthly':
            days_between = 30
        else:
            days_between = 30  # Default
        
        # Create scheduled payments
        for i in range(self.number_of_payments):
            payment_date = current_date + timedelta(days=days_between * i)
            
            LayawayScheduledPayment.objects.create(
                layaway_plan=self,
                payment_number=i + 1,
                due_date=payment_date,
                amount=self.installment_amount
            )
    
    def process_payment(self, amount, payment_method='cash', notes=''):
        """Process a payment for this layaway plan."""
        if self.status != 'active':
            raise ValueError("Cannot process payment for inactive plan")
        
        if amount <= 0:
            raise ValueError("Payment amount must be positive")
        
        # Create payment record
        payment = LayawayPayment.objects.create(
            layaway_plan=self,
            amount=amount,
            payment_method=payment_method,
            payment_date=timezone.now().date(),
            notes=notes
        )
        
        # Update plan totals
        self.total_paid += amount
        self.payments_made += 1
        
        # Mark scheduled payments as paid
        self.mark_scheduled_payments_paid(amount)
        
        # Check if plan is completed
        if self.remaining_balance <= Decimal('0.01'):
            self.complete_plan()
        
        self.save()
        return payment
    
    def mark_scheduled_payments_paid(self, amount):
        """Mark scheduled payments as paid with the given amount."""
        remaining_amount = amount
        
        unpaid_payments = self.scheduled_payments.filter(
            is_paid=False
        ).order_by('due_date')
        
        for scheduled_payment in unpaid_payments:
            if remaining_amount <= 0:
                break
            
            if remaining_amount >= scheduled_payment.amount:
                # Full payment
                scheduled_payment.is_paid = True
                scheduled_payment.paid_amount = scheduled_payment.amount
                scheduled_payment.paid_date = timezone.now().date()
                remaining_amount -= scheduled_payment.amount
            else:
                # Partial payment
                scheduled_payment.paid_amount += remaining_amount
                if scheduled_payment.paid_amount >= scheduled_payment.amount:
                    scheduled_payment.is_paid = True
                    scheduled_payment.paid_date = timezone.now().date()
                remaining_amount = 0
            
            scheduled_payment.save()
    
    def complete_plan(self):
        """Mark plan as completed and release jewelry item."""
        self.status = 'completed'
        self.actual_completion_date = timezone.now().date()
        
        # Release jewelry item
        if self.jewelry_item.status == 'reserved':
            self.jewelry_item.status = 'sold'
            self.jewelry_item.save(update_fields=['status'])
        
        # Update customer purchase stats
        self.customer.update_purchase_stats(self.total_amount)
        
        self.save()
    
    def cancel_plan(self, reason='', refund_amount=None):
        """Cancel the layaway plan."""
        self.status = 'cancelled'
        self.internal_notes += f"\nCancelled: {reason}"
        
        # Release jewelry item
        if self.jewelry_item.status == 'reserved':
            self.jewelry_item.status = 'in_stock'
            self.jewelry_item.save(update_fields=['status'])
        
        # Process refund if specified
        if refund_amount and refund_amount > 0:
            LayawayRefund.objects.create(
                layaway_plan=self,
                refund_amount=refund_amount,
                reason=reason
            )
        
        self.save()
    
    def put_on_hold(self, reason=''):
        """Put plan on hold temporarily."""
        self.status = 'on_hold'
        self.internal_notes += f"\nPut on hold: {reason}"
        self.save()
    
    def reactivate_plan(self, reason=''):
        """Reactivate a plan that was on hold."""
        if self.status == 'on_hold':
            self.status = 'active'
            self.internal_notes += f"\nReactivated: {reason}"
            self.save()


class LayawayScheduledPayment(TenantAwareModel):
    """
    Scheduled payment for layaway plans.
    """
    layaway_plan = models.ForeignKey(
        LayawayPlan,
        on_delete=models.CASCADE,
        related_name='scheduled_payments',
        verbose_name=_('Layaway Plan')
    )
    payment_number = models.PositiveIntegerField(
        verbose_name=_('Payment Number')
    )
    due_date = models.DateField(
        verbose_name=_('Due Date')
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Amount (Toman)')
    )
    
    # Payment status
    is_paid = models.BooleanField(
        default=False,
        verbose_name=_('Is Paid')
    )
    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Paid Amount (Toman)')
    )
    paid_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Paid Date')
    )
    
    # Late payment tracking
    is_overdue = models.BooleanField(
        default=False,
        verbose_name=_('Is Overdue')
    )
    late_fee_applied = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Late Fee Applied (Toman)')
    )
    
    class Meta:
        verbose_name = _('Scheduled Payment')
        verbose_name_plural = _('Scheduled Payments')
        ordering = ['due_date']
        unique_together = ['layaway_plan', 'payment_number']
    
    def __str__(self):
        return f"{self.layaway_plan.plan_number} - Payment {self.payment_number}"
    
    @property
    def remaining_amount(self):
        """Calculate remaining amount to be paid."""
        return max(Decimal('0.00'), self.amount - self.paid_amount)
    
    @property
    def days_overdue(self):
        """Calculate days overdue."""
        if self.is_paid or self.due_date >= timezone.now().date():
            return 0
        
        delta = timezone.now().date() - self.due_date
        return max(0, delta.days - self.layaway_plan.grace_period_days)
    
    def check_overdue_status(self):
        """Check and update overdue status."""
        if not self.is_paid and self.due_date < timezone.now().date():
            grace_period_end = self.due_date + timezone.timedelta(
                days=self.layaway_plan.grace_period_days
            )
            
            if timezone.now().date() > grace_period_end:
                self.is_overdue = True
                self.save(update_fields=['is_overdue'])


class LayawayPayment(TenantAwareModel):
    """
    Actual payments made for layaway plans.
    """
    PAYMENT_METHODS = [
        ('cash', _('Cash')),
        ('bank_transfer', _('Bank Transfer')),
        ('card', _('Card Payment')),
        ('cheque', _('Cheque')),
        ('credit', _('Store Credit')),
    ]
    
    layaway_plan = models.ForeignKey(
        LayawayPlan,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name=_('Layaway Plan')
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Amount (Toman)')
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default='cash',
        verbose_name=_('Payment Method')
    )
    payment_date = models.DateField(
        verbose_name=_('Payment Date')
    )
    
    # Reference information
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Reference Number'),
        help_text=_('Bank transaction ID, cheque number, etc.')
    )
    receipt_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Receipt Number')
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes')
    )
    
    class Meta:
        verbose_name = _('Layaway Payment')
        verbose_name_plural = _('Layaway Payments')
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"{self.layaway_plan.plan_number} - {self.amount} Toman"
    
    def save(self, *args, **kwargs):
        """Generate receipt number if not provided."""
        if not self.receipt_number:
            self.receipt_number = self.generate_receipt_number()
        
        super().save(*args, **kwargs)
    
    def generate_receipt_number(self):
        """Generate unique receipt number."""
        import random
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(random.randint(100, 999))
        return f"LAY-REC-{date_str}-{random_str}"


class LayawayRefund(TenantAwareModel):
    """
    Refunds issued for cancelled layaway plans.
    """
    REFUND_METHODS = [
        ('cash', _('Cash')),
        ('bank_transfer', _('Bank Transfer')),
        ('store_credit', _('Store Credit')),
        ('cheque', _('Cheque')),
    ]
    
    layaway_plan = models.ForeignKey(
        LayawayPlan,
        on_delete=models.CASCADE,
        related_name='refunds',
        verbose_name=_('Layaway Plan')
    )
    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Refund Amount (Toman)')
    )
    refund_method = models.CharField(
        max_length=20,
        choices=REFUND_METHODS,
        default='cash',
        verbose_name=_('Refund Method')
    )
    refund_date = models.DateField(
        default=timezone.now,
        verbose_name=_('Refund Date')
    )
    
    # Processing information
    processed_by = models.ForeignKey(
        'core.User',
        on_delete=models.PROTECT,
        verbose_name=_('Processed By')
    )
    authorization_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Authorization Code')
    )
    
    # Reason and notes
    reason = models.TextField(
        verbose_name=_('Refund Reason')
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes')
    )
    
    class Meta:
        verbose_name = _('Layaway Refund')
        verbose_name_plural = _('Layaway Refunds')
        ordering = ['-refund_date']
    
    def __str__(self):
        return f"Refund for {self.layaway_plan.plan_number} - {self.refund_amount} Toman"


class LayawayContract(TenantAwareModel):
    """
    Contract templates and generated contracts for layaway plans.
    """
    CONTRACT_TYPES = [
        ('standard', _('Standard Layaway Contract')),
        ('premium', _('Premium Layaway Contract')),
        ('custom', _('Custom Contract')),
    ]
    
    name = models.CharField(
        max_length=200,
        verbose_name=_('Contract Name')
    )
    contract_type = models.CharField(
        max_length=20,
        choices=CONTRACT_TYPES,
        default='standard',
        verbose_name=_('Contract Type')
    )
    
    # Contract content
    persian_title = models.CharField(
        max_length=200,
        verbose_name=_('Persian Title')
    )
    contract_template = models.TextField(
        verbose_name=_('Contract Template'),
        help_text=_('Use {{variable}} for dynamic content')
    )
    
    # Terms and conditions
    default_grace_period = models.PositiveIntegerField(
        default=7,
        verbose_name=_('Default Grace Period (Days)')
    )
    late_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('2.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name=_('Late Fee Percentage')
    )
    cancellation_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name=_('Cancellation Fee Percentage')
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name=_('Is Default Template')
    )
    
    class Meta:
        verbose_name = _('Layaway Contract')
        verbose_name_plural = _('Layaway Contracts')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """Ensure only one default template per tenant."""
        if self.is_default:
            LayawayContract.objects.filter(
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        
        super().save(*args, **kwargs)
    
    def generate_contract(self, layaway_plan):
        """Generate contract content for a specific layaway plan."""
        import re
        from django.template import Template, Context
        
        # Prepare context variables
        context_data = {
            'plan_number': layaway_plan.plan_number,
            'customer_name': layaway_plan.customer.full_persian_name,
            'customer_phone': layaway_plan.customer.phone_number,
            'customer_address': layaway_plan.customer.address,
            'jewelry_item': layaway_plan.jewelry_item.name,
            'jewelry_sku': layaway_plan.jewelry_item.sku,
            'total_amount': layaway_plan.total_amount,
            'down_payment': layaway_plan.down_payment,
            'installment_amount': layaway_plan.installment_amount,
            'number_of_payments': layaway_plan.number_of_payments,
            'payment_frequency': layaway_plan.get_payment_frequency_display(),
            'start_date': layaway_plan.start_date_shamsi or layaway_plan.start_date,
            'expected_completion': layaway_plan.expected_completion_date,
            'grace_period': layaway_plan.grace_period_days,
            'late_fee_percentage': self.late_fee_percentage,
            'cancellation_fee_percentage': self.cancellation_fee_percentage,
            'contract_date': timezone.now().strftime('%Y/%m/%d'),
        }
        
        # Render template
        template = Template(self.contract_template)
        context = Context(context_data)
        
        return template.render(context)


class LayawayReminder(TenantAwareModel):
    """
    Payment reminders for layaway plans.
    """
    REMINDER_TYPES = [
        ('upcoming', _('Upcoming Payment')),
        ('overdue', _('Overdue Payment')),
        ('final_notice', _('Final Notice')),
        ('completion', _('Plan Completion')),
    ]
    
    DELIVERY_METHODS = [
        ('sms', _('SMS')),
        ('email', _('Email')),
        ('phone_call', _('Phone Call')),
        ('in_person', _('In Person')),
    ]
    
    layaway_plan = models.ForeignKey(
        LayawayPlan,
        on_delete=models.CASCADE,
        related_name='reminders',
        verbose_name=_('Layaway Plan')
    )
    reminder_type = models.CharField(
        max_length=20,
        choices=REMINDER_TYPES,
        verbose_name=_('Reminder Type')
    )
    
    # Scheduling
    scheduled_date = models.DateField(
        verbose_name=_('Scheduled Date')
    )
    sent_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Sent Date')
    )
    
    # Delivery
    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_METHODS,
        default='sms',
        verbose_name=_('Delivery Method')
    )
    recipient = models.CharField(
        max_length=200,
        verbose_name=_('Recipient'),
        help_text=_('Phone number, email address, etc.')
    )
    
    # Content
    message_template = models.TextField(
        verbose_name=_('Message Template')
    )
    personalized_message = models.TextField(
        blank=True,
        verbose_name=_('Personalized Message')
    )
    
    # Status
    is_sent = models.BooleanField(
        default=False,
        verbose_name=_('Is Sent')
    )
    delivery_status = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Delivery Status')
    )
    
    # Response tracking
    customer_responded = models.BooleanField(
        default=False,
        verbose_name=_('Customer Responded')
    )
    response_notes = models.TextField(
        blank=True,
        verbose_name=_('Response Notes')
    )
    
    class Meta:
        verbose_name = _('Layaway Reminder')
        verbose_name_plural = _('Layaway Reminders')
        ordering = ['-scheduled_date']
    
    def __str__(self):
        return f"{self.layaway_plan.plan_number} - {self.get_reminder_type_display()}"
    
    def generate_personalized_message(self):
        """Generate personalized message from template."""
        from django.template import Template, Context
        
        context_data = {
            'customer_name': self.layaway_plan.customer.full_persian_name,
            'plan_number': self.layaway_plan.plan_number,
            'jewelry_item': self.layaway_plan.jewelry_item.name,
            'next_payment_amount': self.layaway_plan.next_payment_amount,
            'next_payment_date': self.layaway_plan.next_payment_due,
            'remaining_balance': self.layaway_plan.remaining_balance,
            'days_overdue': self.layaway_plan.days_overdue,
        }
        
        template = Template(self.message_template)
        context = Context(context_data)
        
        self.personalized_message = template.render(context)
        self.save(update_fields=['personalized_message'])
        
        return self.personalized_message
    
    def send_reminder(self):
        """Send the reminder via specified delivery method."""
        if self.is_sent:
            return False
        
        # Generate personalized message if not already done
        if not self.personalized_message:
            self.generate_personalized_message()
        
        # Send via appropriate method
        success = False
        
        if self.delivery_method == 'sms':
            success = self.send_sms()
        elif self.delivery_method == 'email':
            success = self.send_email()
        elif self.delivery_method == 'phone_call':
            success = self.schedule_phone_call()
        
        if success:
            self.is_sent = True
            self.sent_date = timezone.now()
            self.delivery_status = 'sent'
            self.save(update_fields=['is_sent', 'sent_date', 'delivery_status'])
        
        return success
    
    def send_sms(self):
        """Send SMS reminder (placeholder for SMS service integration)."""
        # TODO: Integrate with Iranian SMS service provider
        # For now, just mark as sent
        return True
    
    def send_email(self):
        """Send email reminder."""
        from django.core.mail import send_mail
        from django.conf import settings
        
        try:
            send_mail(
                subject=f'یادآوری پرداخت - {self.layaway_plan.plan_number}',
                message=self.personalized_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.recipient],
                fail_silently=False,
            )
            return True
        except Exception as e:
            self.delivery_status = f'failed: {str(e)}'
            self.save(update_fields=['delivery_status'])
            return False
    
    def schedule_phone_call(self):
        """Schedule phone call reminder."""
        # TODO: Integrate with call scheduling system
        # For now, just mark as scheduled
        self.delivery_status = 'scheduled_for_call'
        return True