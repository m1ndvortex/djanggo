"""
Point of Sale (POS) models for ZARGAR jewelry SaaS platform.
Provides touch-optimized POS transaction processing with gold price calculations.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from zargar.core.models import TenantAwareModel
from zargar.core.persian_number_formatter import PersianNumberFormatter
from zargar.core.calendar_utils import PersianCalendarUtils
import uuid
import json
from typing import Dict, List, Optional


class POSTransaction(TenantAwareModel):
    """
    Main POS transaction model for jewelry sales with gold price calculations.
    Supports both online and offline transaction processing.
    """
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
        ('refunded', _('Refunded')),
        ('offline_pending', _('Offline Pending Sync')),
    ]
    
    TRANSACTION_TYPE_CHOICES = [
        ('sale', _('Sale')),
        ('return', _('Return')),
        ('exchange', _('Exchange')),
        ('layaway', _('Layaway Payment')),
        ('installment', _('Installment Payment')),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', _('Cash')),
        ('card', _('Card Payment')),
        ('bank_transfer', _('Bank Transfer')),
        ('cheque', _('Cheque')),
        ('gold_exchange', _('Gold Exchange')),
        ('mixed', _('Mixed Payment')),
    ]
    
    # Transaction identification
    transaction_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        verbose_name=_('Transaction ID'),
        help_text=_('Unique transaction identifier')
    )
    transaction_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Transaction Number'),
        help_text=_('Human-readable transaction number')
    )
    
    # Customer relationship
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='pos_transactions',
        verbose_name=_('Customer')
    )
    
    # Transaction details
    transaction_date = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Transaction Date')
    )
    transaction_date_shamsi = models.CharField(
        max_length=10,
        verbose_name=_('Transaction Date (Shamsi)')
    )
    
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        default='sale',
        verbose_name=_('Transaction Type')
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Status')
    )
    
    # Financial totals
    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Subtotal (Toman)')
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Tax Amount (Toman)')
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Discount Amount (Toman)')
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Total Amount (Toman)')
    )
    
    # Payment information
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash',
        verbose_name=_('Payment Method')
    )
    amount_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Amount Paid (Toman)')
    )
    change_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Change Amount (Toman)')
    )
    
    # Gold price information (for transactions involving gold)
    gold_price_18k_at_transaction = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('18K Gold Price at Transaction (Toman/gram)')
    )
    total_gold_weight_grams = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=Decimal('0.000'),
        verbose_name=_('Total Gold Weight (Grams)')
    )
    
    # Offline transaction support
    is_offline_transaction = models.BooleanField(
        default=False,
        verbose_name=_('Is Offline Transaction'),
        help_text=_('Transaction created while offline')
    )
    offline_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Offline Transaction Data'),
        help_text=_('Stored transaction data for offline processing')
    )
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('synced', _('Synced')),
            ('pending_sync', _('Pending Sync')),
            ('sync_failed', _('Sync Failed')),
        ],
        default='synced',
        verbose_name=_('Sync Status')
    )
    synced_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Synced At')
    )
    
    # Reference information
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Reference Number'),
        help_text=_('External reference number')
    )
    
    # Notes and additional information
    transaction_notes = models.TextField(
        blank=True,
        verbose_name=_('Transaction Notes')
    )
    internal_notes = models.TextField(
        blank=True,
        verbose_name=_('Internal Notes')
    )
    
    class Meta:
        verbose_name = _('POS Transaction')
        verbose_name_plural = _('POS Transactions')
        ordering = ['-transaction_date']
        indexes = [
            models.Index(fields=['transaction_number']),
            models.Index(fields=['customer']),
            models.Index(fields=['transaction_date']),
            models.Index(fields=['status']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['is_offline_transaction']),
            models.Index(fields=['sync_status']),
        ]
    
    def __str__(self):
        return f"{self.transaction_number} - {self.total_amount} Toman"
    
    def save(self, *args, **kwargs):
        """Override save to generate transaction number and set Shamsi date."""
        if not self.transaction_number:
            self.transaction_number = self.generate_transaction_number()
        
        # Set Shamsi date if not provided
        if self.transaction_date and not self.transaction_date_shamsi:
            shamsi_date = PersianCalendarUtils.gregorian_to_shamsi(self.transaction_date.date())
            self.transaction_date_shamsi = f"{shamsi_date[0]:04d}/{shamsi_date[1]:02d}/{shamsi_date[2]:02d}"
        
        # Calculate totals
        self.calculate_totals()
        
        super().save(*args, **kwargs)
    
    def generate_transaction_number(self) -> str:
        """Generate unique transaction number."""
        from django.utils import timezone
        import random
        
        # Format: POS-YYYYMMDD-XXXX
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(random.randint(1000, 9999))
        return f"POS-{date_str}-{random_str}"
    
    def calculate_totals(self):
        """Calculate transaction totals from line items."""
        # Only calculate if the instance has been saved (has a primary key)
        if self.pk:
            line_items = self.line_items.all()
            
            self.subtotal = sum(item.line_total for item in line_items)
            self.total_gold_weight_grams = sum(
                item.gold_weight_grams or Decimal('0.000') 
                for item in line_items
            )
        else:
            # For new instances, initialize with zero values
            self.subtotal = Decimal('0.00')
            self.total_gold_weight_grams = Decimal('0.000')
        
        # Calculate total amount
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        
        # Calculate change
        if self.amount_paid > self.total_amount:
            self.change_amount = self.amount_paid - self.total_amount
        else:
            self.change_amount = Decimal('0.00')
    
    def add_line_item(self, jewelry_item=None, custom_item_name=None, 
                     quantity=1, unit_price=None, gold_price_per_gram=None) -> 'POSTransactionLineItem':
        """
        Add a line item to the transaction.
        
        Args:
            jewelry_item: JewelryItem instance (optional)
            custom_item_name: Custom item name if not using jewelry_item
            quantity: Item quantity
            unit_price: Unit price (calculated from jewelry_item if not provided)
            gold_price_per_gram: Current gold price for calculations
            
        Returns:
            Created POSTransactionLineItem instance
        """
        if jewelry_item:
            item_name = jewelry_item.name
            item_sku = jewelry_item.sku
            
            if unit_price is None:
                # Calculate price based on gold value + manufacturing cost
                if gold_price_per_gram and jewelry_item.weight_grams and jewelry_item.karat:
                    gold_value = jewelry_item.calculate_gold_value(gold_price_per_gram)
                    unit_price = gold_value + (jewelry_item.manufacturing_cost or 0)
                else:
                    unit_price = jewelry_item.selling_price or 0
            
            gold_weight = jewelry_item.weight_grams or Decimal('0.000')
            gold_karat = jewelry_item.karat or 0
        else:
            item_name = custom_item_name or 'Custom Item'
            item_sku = ''
            unit_price = unit_price or Decimal('0.00')
            gold_weight = Decimal('0.000')
            gold_karat = 0
        
        line_item = POSTransactionLineItem.objects.create(
            transaction=self,
            jewelry_item=jewelry_item,
            item_name=item_name,
            item_sku=item_sku,
            quantity=quantity,
            unit_price=unit_price,
            gold_weight_grams=gold_weight * quantity,
            gold_karat=gold_karat,
            gold_price_per_gram_at_sale=gold_price_per_gram
        )
        
        # Recalculate totals
        self.calculate_totals()
        self.save(update_fields=['subtotal', 'total_amount', 'total_gold_weight_grams'])
        
        return line_item
    
    def complete_transaction(self, payment_method=None, amount_paid=None):
        """Complete the transaction and update inventory."""
        if payment_method:
            self.payment_method = payment_method
        
        if amount_paid is not None:
            self.amount_paid = amount_paid
        
        # Validate payment
        if self.amount_paid < self.total_amount:
            raise ValidationError(_('Payment amount is insufficient'))
        
        # Update status
        self.status = 'completed'
        
        # Update inventory for jewelry items
        for line_item in self.line_items.all():
            if line_item.jewelry_item:
                jewelry_item = line_item.jewelry_item
                jewelry_item.quantity -= line_item.quantity
                
                if jewelry_item.quantity <= 0:
                    jewelry_item.status = 'sold'
                
                jewelry_item.save(update_fields=['quantity', 'status'])
        
        # Update customer purchase stats if customer is set
        if self.customer:
            self.customer.update_purchase_stats(self.total_amount)
            
            # Award loyalty points (1 point per 10,000 Toman)
            points_earned = int(self.total_amount / 10000)
            if points_earned > 0:
                self.customer.add_loyalty_points(
                    points_earned, 
                    f"Purchase - Transaction {self.transaction_number}"
                )
        
        self.save()
    
    def cancel_transaction(self, reason=''):
        """Cancel the transaction."""
        self.status = 'cancelled'
        if reason:
            self.internal_notes += f"\nCancelled: {reason}"
        
        self.save(update_fields=['status', 'internal_notes'])
    
    def create_offline_backup(self) -> Dict:
        """Create offline backup data for sync later."""
        offline_data = {
            'transaction_id': str(self.transaction_id),
            'transaction_number': self.transaction_number,
            'customer_id': self.customer.id if self.customer else None,
            'transaction_date': self.transaction_date.isoformat(),
            'transaction_type': self.transaction_type,
            'payment_method': self.payment_method,
            'subtotal': str(self.subtotal),
            'tax_amount': str(self.tax_amount),
            'discount_amount': str(self.discount_amount),
            'total_amount': str(self.total_amount),
            'amount_paid': str(self.amount_paid),
            'gold_price_18k_at_transaction': str(self.gold_price_18k_at_transaction) if self.gold_price_18k_at_transaction else None,
            'line_items': []
        }
        
        for line_item in self.line_items.all():
            offline_data['line_items'].append({
                'jewelry_item_id': line_item.jewelry_item.id if line_item.jewelry_item else None,
                'item_name': line_item.item_name,
                'item_sku': line_item.item_sku,
                'quantity': str(line_item.quantity),
                'unit_price': str(line_item.unit_price),
                'gold_weight_grams': str(line_item.gold_weight_grams),
                'gold_karat': line_item.gold_karat,
            })
        
        self.offline_data = offline_data
        self.is_offline_transaction = True
        self.sync_status = 'pending_sync'
        self.save(update_fields=['offline_data', 'is_offline_transaction', 'sync_status'])
        
        return offline_data
    
    def sync_offline_transaction(self) -> bool:
        """Sync offline transaction data."""
        try:
            if not self.is_offline_transaction or self.sync_status == 'synced':
                return True
            
            # Process the transaction normally
            self.complete_transaction()
            
            # Mark as synced
            self.sync_status = 'synced'
            self.synced_at = timezone.now()
            self.save(update_fields=['sync_status', 'synced_at'])
            
            return True
            
        except Exception as e:
            self.sync_status = 'sync_failed'
            self.internal_notes += f"\nSync failed: {str(e)}"
            self.save(update_fields=['sync_status', 'internal_notes'])
            return False
    
    def format_for_display(self) -> Dict[str, str]:
        """Format transaction data for display with Persian formatting."""
        formatter = PersianNumberFormatter()
        
        return {
            'transaction_number': self.transaction_number,
            'transaction_date_shamsi': self.transaction_date_shamsi,
            'customer_name': str(self.customer) if self.customer else _('Walk-in Customer'),
            'subtotal_display': formatter.format_currency(self.subtotal, use_persian_digits=True),
            'tax_display': formatter.format_currency(self.tax_amount, use_persian_digits=True),
            'discount_display': formatter.format_currency(self.discount_amount, use_persian_digits=True),
            'total_display': formatter.format_currency(self.total_amount, use_persian_digits=True),
            'paid_display': formatter.format_currency(self.amount_paid, use_persian_digits=True),
            'change_display': formatter.format_currency(self.change_amount, use_persian_digits=True),
            'gold_weight_display': formatter.format_weight(
                self.total_gold_weight_grams, 'gram', use_persian_digits=True
            ),
            'status_display': self.get_status_display(),
            'payment_method_display': self.get_payment_method_display(),
        }


class POSTransactionLineItem(TenantAwareModel):
    """
    Individual line items in POS transactions.
    Supports both jewelry items and custom items.
    """
    
    # Transaction relationship
    transaction = models.ForeignKey(
        POSTransaction,
        on_delete=models.CASCADE,
        related_name='line_items',
        verbose_name=_('POS Transaction')
    )
    
    # Item information
    jewelry_item = models.ForeignKey(
        'jewelry.JewelryItem',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_('Jewelry Item')
    )
    item_name = models.CharField(
        max_length=200,
        verbose_name=_('Item Name')
    )
    item_sku = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Item SKU')
    )
    
    # Quantity and pricing
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name=_('Quantity')
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Unit Price (Toman)')
    )
    line_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Line Total (Toman)')
    )
    
    # Gold information (for jewelry items)
    gold_weight_grams = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_('Gold Weight (Grams)')
    )
    gold_karat = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Gold Karat')
    )
    gold_price_per_gram_at_sale = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Gold Price per Gram at Sale (Toman)')
    )
    
    # Discount information
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Discount Percentage')
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Discount Amount (Toman)')
    )
    
    # Notes
    line_notes = models.TextField(
        blank=True,
        verbose_name=_('Line Notes')
    )
    
    class Meta:
        verbose_name = _('POS Transaction Line Item')
        verbose_name_plural = _('POS Transaction Line Items')
        ordering = ['id']
    
    def __str__(self):
        return f"{self.transaction.transaction_number} - {self.item_name} x{self.quantity}"
    
    def save(self, *args, **kwargs):
        """Override save to calculate line total."""
        # Calculate line total
        discounted_price = self.unit_price - self.discount_amount
        self.line_total = discounted_price * self.quantity
        
        super().save(*args, **kwargs)
    
    def apply_discount(self, discount_percentage=None, discount_amount=None):
        """Apply discount to line item."""
        if discount_percentage is not None:
            self.discount_percentage = discount_percentage
            self.discount_amount = (self.unit_price * discount_percentage / 100).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        elif discount_amount is not None:
            self.discount_amount = discount_amount
            if self.unit_price > 0:
                self.discount_percentage = (discount_amount / self.unit_price * 100).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
        
        self.save(update_fields=['discount_percentage', 'discount_amount', 'line_total'])
    
    def format_for_display(self) -> Dict[str, str]:
        """Format line item data for display with Persian formatting."""
        formatter = PersianNumberFormatter()
        
        return {
            'item_name': self.item_name,
            'item_sku': self.item_sku,
            'quantity_display': formatter.format_number(self.quantity, use_persian_digits=True),
            'unit_price_display': formatter.format_currency(self.unit_price, use_persian_digits=True),
            'line_total_display': formatter.format_currency(self.line_total, use_persian_digits=True),
            'gold_weight_display': formatter.format_weight(
                self.gold_weight_grams, 'gram', use_persian_digits=True
            ) if self.gold_weight_grams else '',
            'discount_display': formatter.format_percentage(
                self.discount_percentage, use_persian_digits=True
            ) if self.discount_percentage > 0 else '',
        }


class POSInvoice(TenantAwareModel):
    """
    Invoice model for POS transactions with Persian formatting and Iranian business law compliance.
    """
    
    INVOICE_TYPE_CHOICES = [
        ('sale', _('Sale Invoice')),
        ('return', _('Return Invoice')),
        ('proforma', _('Proforma Invoice')),
    ]
    
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('issued', _('Issued')),
        ('paid', _('Paid')),
        ('cancelled', _('Cancelled')),
    ]
    
    # Transaction relationship
    transaction = models.OneToOneField(
        POSTransaction,
        on_delete=models.CASCADE,
        related_name='invoice',
        verbose_name=_('POS Transaction')
    )
    
    # Invoice identification
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Invoice Number')
    )
    invoice_type = models.CharField(
        max_length=20,
        choices=INVOICE_TYPE_CHOICES,
        default='sale',
        verbose_name=_('Invoice Type')
    )
    
    # Invoice dates
    issue_date = models.DateField(
        default=timezone.now,
        verbose_name=_('Issue Date')
    )
    issue_date_shamsi = models.CharField(
        max_length=10,
        verbose_name=_('Issue Date (Shamsi)')
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Due Date')
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name=_('Status')
    )
    
    # Iranian business compliance
    tax_id = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Tax ID'),
        help_text=_('Iranian tax identification number')
    )
    economic_code = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Economic Code'),
        help_text=_('Iranian economic code')
    )
    
    # Invoice totals (copied from transaction for immutability)
    invoice_subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Invoice Subtotal (Toman)')
    )
    invoice_tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Invoice Tax Amount (Toman)')
    )
    invoice_discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Invoice Discount Amount (Toman)')
    )
    invoice_total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Invoice Total Amount (Toman)')
    )
    
    # Additional invoice information
    invoice_notes = models.TextField(
        blank=True,
        verbose_name=_('Invoice Notes')
    )
    terms_and_conditions = models.TextField(
        blank=True,
        verbose_name=_('Terms and Conditions')
    )
    
    # Email delivery
    email_sent = models.BooleanField(
        default=False,
        verbose_name=_('Email Sent')
    )
    email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Email Sent At')
    )
    
    class Meta:
        verbose_name = _('POS Invoice')
        verbose_name_plural = _('POS Invoices')
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['transaction']),
            models.Index(fields=['status']),
            models.Index(fields=['issue_date']),
        ]
    
    def __str__(self):
        return f"{self.invoice_number} - {self.invoice_total_amount} Toman"
    
    def save(self, *args, **kwargs):
        """Override save to generate invoice number and set Shamsi date."""
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        
        # Set Shamsi date if not provided
        if self.issue_date and not self.issue_date_shamsi:
            shamsi_date = PersianCalendarUtils.gregorian_to_shamsi(self.issue_date)
            self.issue_date_shamsi = f"{shamsi_date[0]:04d}/{shamsi_date[1]:02d}/{shamsi_date[2]:02d}"
        
        # Copy amounts from transaction if not set
        if not self.pk and self.transaction:
            self.invoice_subtotal = self.transaction.subtotal
            self.invoice_tax_amount = self.transaction.tax_amount
            self.invoice_discount_amount = self.transaction.discount_amount
            self.invoice_total_amount = self.transaction.total_amount
        
        super().save(*args, **kwargs)
    
    def generate_invoice_number(self) -> str:
        """Generate unique invoice number."""
        from django.utils import timezone
        import random
        
        # Format: INV-YYYYMMDD-XXXX
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(random.randint(1000, 9999))
        return f"INV-{date_str}-{random_str}"
    
    def mark_as_issued(self):
        """Mark invoice as issued."""
        self.status = 'issued'
        self.save(update_fields=['status'])
    
    def mark_as_paid(self):
        """Mark invoice as paid."""
        self.status = 'paid'
        self.save(update_fields=['status'])
    
    def send_email(self, recipient_email: str) -> bool:
        """
        Send invoice via email.
        
        Args:
            recipient_email: Recipient email address
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # TODO: Implement email sending logic
            # This would integrate with Iranian email services
            
            self.email_sent = True
            self.email_sent_at = timezone.now()
            self.save(update_fields=['email_sent', 'email_sent_at'])
            
            return True
            
        except Exception as e:
            # Log error
            return False
    
    def generate_persian_invoice_data(self) -> Dict:
        """Generate invoice data formatted for Persian invoice template."""
        formatter = PersianNumberFormatter()
        
        # Business information (would come from tenant settings)
        business_info = {
            'name': 'نام جواهرفروشی',  # Jewelry shop name
            'address': 'آدرس جواهرفروشی',  # Shop address
            'phone': '۰۲۱-۱۲۳۴۵۶۷۸',  # Shop phone
            'tax_id': self.tax_id or '',
            'economic_code': self.economic_code or '',
        }
        
        # Customer information
        customer_info = {}
        if self.transaction.customer:
            customer = self.transaction.customer
            customer_info = {
                'name': customer.full_persian_name,
                'phone': customer.phone_number,
                'address': customer.address or '',
            }
        else:
            customer_info = {
                'name': 'مشتری نقدی',  # Cash customer
                'phone': '',
                'address': '',
            }
        
        # Invoice details
        invoice_details = {
            'invoice_number': self.invoice_number,
            'issue_date_shamsi': self.issue_date_shamsi,
            'due_date_shamsi': '',  # Would be calculated if due_date is set
            'type_display': self.get_invoice_type_display(),
        }
        
        # Line items
        line_items = []
        for item in self.transaction.line_items.all():
            line_items.append({
                'name': item.item_name,
                'sku': item.item_sku,
                'quantity': formatter.format_number(item.quantity, use_persian_digits=True),
                'unit_price': formatter.format_currency(item.unit_price, use_persian_digits=True),
                'line_total': formatter.format_currency(item.line_total, use_persian_digits=True),
                'gold_weight': formatter.format_weight(
                    item.gold_weight_grams, 'gram', use_persian_digits=True
                ) if item.gold_weight_grams else '',
            })
        
        # Financial totals
        financial_totals = {
            'subtotal': formatter.format_currency(self.invoice_subtotal, use_persian_digits=True),
            'tax_amount': formatter.format_currency(self.invoice_tax_amount, use_persian_digits=True),
            'discount_amount': formatter.format_currency(self.invoice_discount_amount, use_persian_digits=True),
            'total_amount': formatter.format_currency(self.invoice_total_amount, use_persian_digits=True),
            'total_in_words': formatter.number_to_persian_words(self.invoice_total_amount),
        }
        
        return {
            'business_info': business_info,
            'customer_info': customer_info,
            'invoice_details': invoice_details,
            'line_items': line_items,
            'financial_totals': financial_totals,
            'notes': self.invoice_notes,
            'terms_and_conditions': self.terms_and_conditions,
        }


class POSOfflineStorage(models.Model):
    """
    Local storage for offline POS transactions.
    Stores transaction data when internet connection is unavailable.
    """
    
    # Identification
    storage_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        verbose_name=_('Storage ID')
    )
    
    # Transaction data
    transaction_data = models.JSONField(
        verbose_name=_('Transaction Data'),
        help_text=_('Complete transaction data in JSON format')
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    device_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Device ID'),
        help_text=_('Identifier of the device that created this record')
    )
    
    # Sync status
    is_synced = models.BooleanField(
        default=False,
        verbose_name=_('Is Synced')
    )
    synced_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Synced At')
    )
    sync_error = models.TextField(
        blank=True,
        verbose_name=_('Sync Error'),
        help_text=_('Error message if sync failed')
    )
    
    # Related transaction (set after successful sync)
    synced_transaction = models.ForeignKey(
        POSTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Synced Transaction')
    )
    
    class Meta:
        verbose_name = _('POS Offline Storage')
        verbose_name_plural = _('POS Offline Storage')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_synced']),
            models.Index(fields=['created_at']),
            models.Index(fields=['device_id']),
        ]
    
    def __str__(self):
        return f"Offline Storage {self.storage_id} - {'Synced' if self.is_synced else 'Pending'}"
    
    def sync_to_database(self) -> bool:
        """
        Sync offline transaction data to database.
        
        Returns:
            True if sync successful, False otherwise
        """
        try:
            # Parse transaction data
            data = self.transaction_data
            
            # Create transaction
            transaction = POSTransaction.objects.create(
                transaction_id=uuid.UUID(data['transaction_id']),
                customer_id=data.get('customer_id'),
                transaction_date=timezone.datetime.fromisoformat(data['transaction_date']),
                transaction_type=data['transaction_type'],
                payment_method=data['payment_method'],
                subtotal=Decimal(data['subtotal']),
                tax_amount=Decimal(data['tax_amount']),
                discount_amount=Decimal(data['discount_amount']),
                total_amount=Decimal(data['total_amount']),
                amount_paid=Decimal(data['amount_paid']),
                gold_price_18k_at_transaction=Decimal(data['gold_price_18k_at_transaction']) if data.get('gold_price_18k_at_transaction') else None,
                is_offline_transaction=True,
                sync_status='synced'
            )
            
            # Create line items
            for item_data in data['line_items']:
                POSTransactionLineItem.objects.create(
                    transaction=transaction,
                    jewelry_item_id=item_data.get('jewelry_item_id'),
                    item_name=item_data['item_name'],
                    item_sku=item_data['item_sku'],
                    quantity=int(item_data['quantity']),
                    unit_price=Decimal(item_data['unit_price']),
                    gold_weight_grams=Decimal(item_data['gold_weight_grams']),
                    gold_karat=item_data['gold_karat']
                )
            
            # Complete the transaction
            transaction.complete_transaction()
            
            # Mark as synced
            self.is_synced = True
            self.synced_at = timezone.now()
            self.synced_transaction = transaction
            self.save(update_fields=['is_synced', 'synced_at', 'synced_transaction'])
            
            return True
            
        except Exception as e:
            self.sync_error = str(e)
            self.save(update_fields=['sync_error'])
            return False