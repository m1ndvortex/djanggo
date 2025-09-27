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
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


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
                'quantity': formatter.to_persian_digits(item.quantity),
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
            'total_in_words': f"{formatter.format_currency(self.invoice_total_amount, use_persian_digits=True)} به حروف",
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


class POSOfflineStorage(TenantAwareModel):
    """
    Model for storing POS transactions offline when internet connection is unavailable.
    Supports automatic synchronization when connection is restored.
    """
    
    SYNC_STATUS_CHOICES = [
        ('pending', _('Pending Sync')),
        ('syncing', _('Syncing')),
        ('synced', _('Synced')),
        ('failed', _('Sync Failed')),
        ('conflict', _('Sync Conflict')),
    ]
    
    # Storage identification
    storage_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        verbose_name=_('Storage ID'),
        help_text=_('Unique identifier for offline storage')
    )
    
    # Device information
    device_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Device ID'),
        help_text=_('Identifier of the device that created this offline transaction')
    )
    device_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Device Name'),
        help_text=_('Human-readable device name')
    )
    
    # Transaction data
    transaction_data = models.JSONField(
        verbose_name=_('Transaction Data'),
        help_text=_('Complete transaction data stored for offline processing')
    )
    
    # Sync status
    sync_status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS_CHOICES,
        default='pending',
        verbose_name=_('Sync Status')
    )
    is_synced = models.BooleanField(
        default=False,
        verbose_name=_('Is Synced'),
        help_text=_('Whether this transaction has been successfully synced')
    )
    
    # Sync timestamps
    sync_attempted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Sync Attempted At')
    )
    synced_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Synced At')
    )
    
    # Sync results
    sync_error = models.TextField(
        blank=True,
        verbose_name=_('Sync Error'),
        help_text=_('Error message if sync failed')
    )
    synced_transaction_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_('Synced Transaction ID'),
        help_text=_('ID of the transaction created after successful sync')
    )
    
    # Conflict resolution
    has_conflicts = models.BooleanField(
        default=False,
        verbose_name=_('Has Conflicts'),
        help_text=_('Whether this transaction has sync conflicts')
    )
    conflict_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Conflict Data'),
        help_text=_('Data about sync conflicts for resolution')
    )
    
    # Retry information
    sync_retry_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Sync Retry Count')
    )
    max_retry_attempts = models.PositiveIntegerField(
        default=3,
        verbose_name=_('Max Retry Attempts')
    )
    
    class Meta:
        verbose_name = _('POS Offline Storage')
        verbose_name_plural = _('POS Offline Storage')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['device_id']),
            models.Index(fields=['sync_status']),
            models.Index(fields=['is_synced']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Offline Transaction {self.storage_id} - {self.sync_status}"
    
    def sync_to_database(self) -> bool:
        """
        Sync offline transaction to database.
        
        Returns:
            True if sync successful, False otherwise
        """
        if self.is_synced:
            return True
        
        self.sync_status = 'syncing'
        self.sync_attempted_at = timezone.now()
        self.sync_retry_count += 1
        self.save(update_fields=['sync_status', 'sync_attempted_at', 'sync_retry_count'])
        
        try:
            # Import here to avoid circular imports
            from .services import POSTransactionService
            from zargar.jewelry.models import JewelryItem
            from zargar.customers.models import Customer
            
            # Extract transaction data
            data = self.transaction_data
            
            # Create customer if specified
            customer = None
            if data.get('customer_id'):
                try:
                    customer = Customer.objects.get(id=data['customer_id'])
                except Customer.DoesNotExist:
                    # Customer might have been deleted, continue without customer
                    pass
            
            # Create transaction
            transaction = POSTransaction.objects.create(
                customer=customer,
                transaction_type=data.get('transaction_type', 'sale'),
                payment_method=data.get('payment_method', 'cash'),
                subtotal=Decimal(data.get('subtotal', '0.00')),
                tax_amount=Decimal(data.get('tax_amount', '0.00')),
                discount_amount=Decimal(data.get('discount_amount', '0.00')),
                total_amount=Decimal(data.get('total_amount', '0.00')),
                amount_paid=Decimal(data.get('amount_paid', '0.00')),
                gold_price_18k_at_transaction=Decimal(data.get('gold_price_18k_at_transaction', '0.00')),
                is_offline_transaction=True,
                offline_data=data,
                sync_status='synced'
            )
            
            # Set original transaction date if provided
            if data.get('transaction_date'):
                try:
                    original_date = datetime.fromisoformat(data['transaction_date'].replace('Z', '+00:00'))
                    transaction.transaction_date = original_date
                    transaction.save(update_fields=['transaction_date'])
                except (ValueError, AttributeError):
                    pass
            
            # Create line items
            for item_data in data.get('line_items', []):
                jewelry_item = None
                if item_data.get('jewelry_item_id'):
                    try:
                        jewelry_item = JewelryItem.objects.get(id=item_data['jewelry_item_id'])
                    except JewelryItem.DoesNotExist:
                        # Item might have been deleted, create as custom item
                        pass
                
                POSTransactionLineItem.objects.create(
                    transaction=transaction,
                    jewelry_item=jewelry_item,
                    item_name=item_data.get('item_name', ''),
                    item_sku=item_data.get('item_sku', ''),
                    quantity=int(item_data.get('quantity', 1)),
                    unit_price=Decimal(item_data.get('unit_price', '0.00')),
                    gold_weight_grams=Decimal(item_data.get('gold_weight_grams', '0.000')),
                    gold_karat=int(item_data.get('gold_karat', 0)),
                    gold_price_per_gram_at_sale=Decimal(data.get('gold_price_18k_at_transaction', '0.00'))
                )
            
            # Complete the transaction if payment was processed offline
            if data.get('amount_paid') and Decimal(data['amount_paid']) >= Decimal(data.get('total_amount', '0.00')):
                transaction.complete_transaction()
            
            # Mark as synced
            self.sync_status = 'synced'
            self.is_synced = True
            self.synced_at = timezone.now()
            self.synced_transaction_id = transaction.transaction_id
            self.sync_error = ''
            self.save(update_fields=[
                'sync_status', 'is_synced', 'synced_at', 
                'synced_transaction_id', 'sync_error'
            ])
            
            return True
            
        except Exception as e:
            # Handle sync failure
            self.sync_status = 'failed'
            self.sync_error = str(e)
            
            # Check if max retries exceeded
            if self.sync_retry_count >= self.max_retry_attempts:
                self.sync_status = 'conflict'
                self.has_conflicts = True
                self.conflict_data = {
                    'error': str(e),
                    'retry_count': self.sync_retry_count,
                    'last_attempt': timezone.now().isoformat()
                }
            
            self.save(update_fields=[
                'sync_status', 'sync_error', 'has_conflicts', 'conflict_data'
            ])
            
            return False
    
    def resolve_conflict(self, resolution_action: str, resolution_data: Optional[Dict] = None) -> bool:
        """
        Resolve sync conflict.
        
        Args:
            resolution_action: Action to take ('retry', 'skip', 'manual_merge')
            resolution_data: Additional data for resolution
            
        Returns:
            True if conflict resolved, False otherwise
        """
        if not self.has_conflicts:
            return True
        
        if resolution_action == 'retry':
            # Reset for retry
            self.sync_status = 'pending'
            self.has_conflicts = False
            self.conflict_data = {}
            self.sync_retry_count = 0
            self.sync_error = ''
            self.save(update_fields=[
                'sync_status', 'has_conflicts', 'conflict_data', 
                'sync_retry_count', 'sync_error'
            ])
            return True
            
        elif resolution_action == 'skip':
            # Mark as resolved but not synced
            self.sync_status = 'failed'
            self.has_conflicts = False
            self.conflict_data['resolution'] = 'skipped'
            self.save(update_fields=['sync_status', 'has_conflicts', 'conflict_data'])
            return True
            
        elif resolution_action == 'manual_merge' and resolution_data:
            # Update transaction data with manual resolution
            self.transaction_data.update(resolution_data)
            self.sync_status = 'pending'
            self.has_conflicts = False
            self.conflict_data = {}
            self.sync_retry_count = 0
            self.save(update_fields=[
                'transaction_data', 'sync_status', 'has_conflicts', 
                'conflict_data', 'sync_retry_count'
            ])
            return True
        
        return False
    
    def get_transaction_summary(self) -> Dict:
        """
        Get summary of offline transaction for display.
        
        Returns:
            Dictionary with transaction summary
        """
        data = self.transaction_data
        
        return {
            'storage_id': str(self.storage_id),
            'device_name': self.device_name or self.device_id,
            'transaction_date': data.get('offline_created_at', self.created_at.isoformat()),
            'customer_id': data.get('customer_id'),
            'total_amount': data.get('total_amount', '0.00'),
            'payment_method': data.get('payment_method', ''),
            'line_items_count': len(data.get('line_items', [])),
            'sync_status': self.sync_status,
            'has_conflicts': self.has_conflicts,
            'retry_count': self.sync_retry_count,
        }


class OfflinePOSSystem:
    """
    Main class for handling offline POS operations.
    Manages local storage, automatic sync, and conflict resolution.
    """
    
    def __init__(self, device_id: str = '', device_name: str = ''):
        """
        Initialize offline POS system.
        
        Args:
            device_id: Unique device identifier
            device_name: Human-readable device name
        """
        self.device_id = device_id or self._generate_device_id()
        self.device_name = device_name or f"POS Device {self.device_id[:8]}"
        self.is_online = self._check_connection()
        self.sync_in_progress = False
    
    def _generate_device_id(self) -> str:
        """Generate unique device ID."""
        import platform
        import hashlib
        
        # Create device ID based on system info
        system_info = f"{platform.node()}-{platform.system()}-{platform.processor()}"
        device_hash = hashlib.md5(system_info.encode()).hexdigest()
        return f"POS-{device_hash[:12]}"
    
    def _check_connection(self) -> bool:
        """
        Check if internet connection is available.
        
        Returns:
            True if online, False if offline
        """
        try:
            # Try to access a reliable endpoint
            import requests
            response = requests.get('https://www.google.com', timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def create_offline_transaction(self, customer_id: Optional[int] = None,
                                  line_items: List[Dict] = None,
                                  payment_method: str = 'cash',
                                  amount_paid: Decimal = Decimal('0.00'),
                                  transaction_type: str = 'sale') -> POSOfflineStorage:
        """
        Create offline transaction when internet is unavailable.
        
        Args:
            customer_id: Customer ID (optional)
            line_items: List of line item dictionaries
            payment_method: Payment method
            amount_paid: Amount paid by customer
            transaction_type: Transaction type
            
        Returns:
            Created POSOfflineStorage instance
        """
        if line_items is None:
            line_items = []
        
        # Create offline transaction data
        transaction_data = {
            'transaction_id': str(uuid.uuid4()),
            'customer_id': customer_id,
            'transaction_date': timezone.now().isoformat(),
            'transaction_type': transaction_type,
            'payment_method': payment_method,
            'amount_paid': str(amount_paid),
            'line_items': line_items,
            'offline_created_at': timezone.now().isoformat(),
            'device_id': self.device_id,
            'device_name': self.device_name
        }
        
        # Calculate totals
        subtotal = sum(
            Decimal(str(item.get('unit_price', '0.00'))) * int(item.get('quantity', 1))
            for item in line_items
        )
        
        transaction_data.update({
            'subtotal': str(subtotal),
            'tax_amount': '0.00',  # Can be calculated later
            'discount_amount': '0.00',
            'total_amount': str(subtotal)
        })
        
        # Get current gold price if available
        try:
            from zargar.gold_installments.services import GoldPriceService
            gold_price_data = GoldPriceService.get_current_gold_price(18)
            transaction_data['gold_price_18k_at_transaction'] = str(gold_price_data['price_per_gram'])
        except:
            transaction_data['gold_price_18k_at_transaction'] = '0.00'
        
        # Store offline transaction
        offline_storage = POSOfflineStorage.objects.create(
            device_id=self.device_id,
            device_name=self.device_name,
            transaction_data=transaction_data
        )
        
        logger.info(f"Created offline transaction {offline_storage.storage_id} on device {self.device_id}")
        return offline_storage
    
    def sync_offline_transactions(self) -> Dict:
        """
        Sync all pending offline transactions for this device.
        
        Returns:
            Dictionary with sync results
        """
        if self.sync_in_progress:
            return {'success': False, 'error': 'Sync already in progress'}
        
        # Check connection
        self.is_online = self._check_connection()
        if not self.is_online:
            return {'success': False, 'error': 'No internet connection available'}
        
        self.sync_in_progress = True
        
        try:
            # Get pending transactions for this device
            pending_transactions = POSOfflineStorage.objects.filter(
                device_id=self.device_id,
                is_synced=False,
                sync_status__in=['pending', 'failed']
            ).order_by('created_at')
            
            sync_results = {
                'success': True,
                'total_pending': pending_transactions.count(),
                'synced_successfully': 0,
                'sync_failed': 0,
                'conflicts': 0,
                'errors': []
            }
            
            for offline_transaction in pending_transactions:
                try:
                    success = offline_transaction.sync_to_database()
                    if success:
                        sync_results['synced_successfully'] += 1
                        logger.info(f"Successfully synced offline transaction {offline_transaction.storage_id}")
                    else:
                        if offline_transaction.has_conflicts:
                            sync_results['conflicts'] += 1
                        else:
                            sync_results['sync_failed'] += 1
                        
                        sync_results['errors'].append({
                            'storage_id': str(offline_transaction.storage_id),
                            'error': offline_transaction.sync_error,
                            'has_conflicts': offline_transaction.has_conflicts
                        })
                        
                except Exception as e:
                    sync_results['sync_failed'] += 1
                    sync_results['errors'].append({
                        'storage_id': str(offline_transaction.storage_id),
                        'error': str(e),
                        'has_conflicts': False
                    })
                    logger.error(f"Failed to sync offline transaction {offline_transaction.storage_id}: {e}")
            
            logger.info(f"Offline sync completed for device {self.device_id}: "
                       f"{sync_results['synced_successfully']} successful, "
                       f"{sync_results['sync_failed']} failed, "
                       f"{sync_results['conflicts']} conflicts")
            
            return sync_results
            
        finally:
            self.sync_in_progress = False
    
    def get_offline_transaction_summary(self) -> Dict:
        """
        Get summary of offline transactions for this device.
        
        Returns:
            Dictionary with offline transaction summary
        """
        device_transactions = POSOfflineStorage.objects.filter(device_id=self.device_id)
        
        total_count = device_transactions.count()
        pending_count = device_transactions.filter(is_synced=False).count()
        synced_count = device_transactions.filter(is_synced=True).count()
        conflicts_count = device_transactions.filter(has_conflicts=True).count()
        
        # Calculate total value of pending transactions
        pending_transactions = device_transactions.filter(is_synced=False)
        total_pending_value = Decimal('0.00')
        
        for offline_transaction in pending_transactions:
            try:
                data = offline_transaction.transaction_data
                total_pending_value += Decimal(data.get('total_amount', '0.00'))
            except (ValueError, KeyError):
                continue
        
        return {
            'device_id': self.device_id,
            'device_name': self.device_name,
            'is_online': self.is_online,
            'sync_in_progress': self.sync_in_progress,
            'total_transactions': total_count,
            'pending_sync': pending_count,
            'synced': synced_count,
            'conflicts': conflicts_count,
            'total_pending_value': total_pending_value,
            'oldest_pending': pending_transactions.order_by('created_at').first().created_at if pending_count > 0 else None
        }
    
    def resolve_sync_conflicts(self, resolution_actions: Dict[str, str]) -> Dict:
        """
        Resolve multiple sync conflicts.
        
        Args:
            resolution_actions: Dictionary mapping storage_id to resolution action
            
        Returns:
            Dictionary with resolution results
        """
        conflict_transactions = POSOfflineStorage.objects.filter(
            device_id=self.device_id,
            has_conflicts=True
        )
        
        results = {
            'total_conflicts': conflict_transactions.count(),
            'resolved': 0,
            'failed': 0,
            'errors': []
        }
        
        for offline_transaction in conflict_transactions:
            storage_id = str(offline_transaction.storage_id)
            action = resolution_actions.get(storage_id, 'skip')
            
            try:
                success = offline_transaction.resolve_conflict(action)
                if success:
                    results['resolved'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'storage_id': storage_id,
                        'error': f'Failed to resolve with action: {action}'
                    })
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'storage_id': storage_id,
                    'error': str(e)
                })
        
        return results
    
    def cleanup_old_transactions(self, days_old: int = 30) -> int:
        """
        Clean up old synced transactions to save storage space.
        
        Args:
            days_old: Number of days after which to clean up synced transactions
            
        Returns:
            Number of transactions cleaned up
        """
        cutoff_date = timezone.now() - timedelta(days=days_old)
        
        old_transactions = POSOfflineStorage.objects.filter(
            device_id=self.device_id,
            is_synced=True,
            synced_at__lt=cutoff_date
        )
        
        count = old_transactions.count()
        old_transactions.delete()
        
        logger.info(f"Cleaned up {count} old offline transactions for device {self.device_id}")
        return count
    
    def export_offline_data(self) -> Dict:
        """
        Export all offline transaction data for backup or migration.
        
        Returns:
            Dictionary with all offline transaction data
        """
        device_transactions = POSOfflineStorage.objects.filter(device_id=self.device_id)
        
        export_data = {
            'device_id': self.device_id,
            'device_name': self.device_name,
            'export_timestamp': timezone.now().isoformat(),
            'transactions': []
        }
        
        for offline_transaction in device_transactions:
            export_data['transactions'].append({
                'storage_id': str(offline_transaction.storage_id),
                'created_at': offline_transaction.created_at.isoformat(),
                'sync_status': offline_transaction.sync_status,
                'is_synced': offline_transaction.is_synced,
                'has_conflicts': offline_transaction.has_conflicts,
                'transaction_data': offline_transaction.transaction_data,
                'conflict_data': offline_transaction.conflict_data
            })
        
        return export_data