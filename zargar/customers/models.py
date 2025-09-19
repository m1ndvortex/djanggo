"""
Customer management models for zargar project.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from zargar.core.models import TenantAwareModel
import jdatetime


class Customer(TenantAwareModel):
    """
    Customer model with Persian name support and loyalty tracking.
    """
    CUSTOMER_TYPES = [
        ('individual', _('Individual')),
        ('business', _('Business')),
        ('vip', _('VIP')),
    ]
    
    # Basic information
    first_name = models.CharField(
        max_length=100,
        verbose_name=_('First Name')
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name=_('Last Name')
    )
    persian_first_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Persian First Name')
    )
    persian_last_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Persian Last Name')
    )
    
    # Contact information
    phone_validator = RegexValidator(
        regex=r'^09\d{9}$',
        message=_('Phone number must be in format: 09123456789')
    )
    phone_number = models.CharField(
        max_length=11,
        validators=[phone_validator],
        verbose_name=_('Phone Number')
    )
    email = models.EmailField(
        blank=True,
        verbose_name=_('Email Address')
    )
    
    # Address information
    address = models.TextField(
        blank=True,
        verbose_name=_('Address')
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('City')
    )
    province = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Province')
    )
    postal_code = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Postal Code')
    )
    
    # Personal information
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Birth Date (Gregorian)')
    )
    birth_date_shamsi = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Birth Date (Shamsi)'),
        help_text=_('Format: 1400/01/01')
    )
    national_id = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('National ID')
    )
    
    # Customer classification
    customer_type = models.CharField(
        max_length=20,
        choices=CUSTOMER_TYPES,
        default='individual',
        verbose_name=_('Customer Type')
    )
    
    # Loyalty and engagement
    loyalty_points = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Loyalty Points')
    )
    total_purchases = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_('Total Purchases (Toman)')
    )
    last_purchase_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last Purchase Date')
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    is_vip = models.BooleanField(
        default=False,
        verbose_name=_('Is VIP Customer')
    )
    
    # Notes
    internal_notes = models.TextField(
        blank=True,
        verbose_name=_('Internal Notes')
    )
    
    class Meta:
        verbose_name = _('Customer')
        verbose_name_plural = _('Customers')
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['email']),
            models.Index(fields=['customer_type']),
            models.Index(fields=['is_vip']),
        ]
    
    def __str__(self):
        if self.persian_first_name and self.persian_last_name:
            return f"{self.persian_first_name} {self.persian_last_name}"
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        """Return full name in English."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_persian_name(self):
        """Return full name in Persian."""
        if self.persian_first_name and self.persian_last_name:
            return f"{self.persian_first_name} {self.persian_last_name}"
        return self.full_name
    
    @property
    def is_birthday_today(self):
        """Check if today is customer's birthday."""
        if not self.birth_date:
            return False
        
        today = jdatetime.date.today()
        birth_shamsi = jdatetime.date.fromgregorian(date=self.birth_date)
        
        return (today.month == birth_shamsi.month and 
                today.day == birth_shamsi.day)
    
    def add_loyalty_points(self, points, reason=""):
        """Add loyalty points to customer."""
        self.loyalty_points += points
        self.save(update_fields=['loyalty_points', 'updated_at'])
        
        # Create loyalty transaction record
        CustomerLoyaltyTransaction.objects.create(
            customer=self,
            points=points,
            transaction_type='earned',
            reason=reason
        )
    
    def redeem_loyalty_points(self, points, reason=""):
        """Redeem loyalty points."""
        if self.loyalty_points >= points:
            self.loyalty_points -= points
            self.save(update_fields=['loyalty_points', 'updated_at'])
            
            # Create loyalty transaction record
            CustomerLoyaltyTransaction.objects.create(
                customer=self,
                points=-points,
                transaction_type='redeemed',
                reason=reason
            )
            return True
        return False
    
    def update_purchase_stats(self, amount):
        """Update customer purchase statistics."""
        from django.utils import timezone
        
        self.total_purchases += amount
        self.last_purchase_date = timezone.now()
        
        # Check for VIP status upgrade
        if self.total_purchases >= 50000000:  # 50 million Toman
            self.is_vip = True
            self.customer_type = 'vip'
        
        self.save(update_fields=[
            'total_purchases', 
            'last_purchase_date', 
            'is_vip', 
            'customer_type',
            'updated_at'
        ])


class CustomerLoyaltyTransaction(TenantAwareModel):
    """
    Track loyalty point transactions for customers.
    """
    TRANSACTION_TYPES = [
        ('earned', _('Points Earned')),
        ('redeemed', _('Points Redeemed')),
        ('expired', _('Points Expired')),
        ('adjusted', _('Manual Adjustment')),
    ]
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='loyalty_transactions',
        verbose_name=_('Customer')
    )
    points = models.IntegerField(
        verbose_name=_('Points'),
        help_text=_('Positive for earned, negative for redeemed')
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        verbose_name=_('Transaction Type')
    )
    reason = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Reason')
    )
    reference_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Reference ID'),
        help_text=_('Sale ID, promotion ID, etc.')
    )
    
    class Meta:
        verbose_name = _('Loyalty Transaction')
        verbose_name_plural = _('Loyalty Transactions')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.customer} - {self.points} points ({self.transaction_type})"


class CustomerNote(TenantAwareModel):
    """
    Notes and interactions with customers.
    """
    NOTE_TYPES = [
        ('general', _('General Note')),
        ('complaint', _('Complaint')),
        ('compliment', _('Compliment')),
        ('follow_up', _('Follow-up Required')),
        ('preference', _('Customer Preference')),
    ]
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='notes',
        verbose_name=_('Customer')
    )
    note_type = models.CharField(
        max_length=20,
        choices=NOTE_TYPES,
        default='general',
        verbose_name=_('Note Type')
    )
    title = models.CharField(
        max_length=200,
        verbose_name=_('Title')
    )
    content = models.TextField(
        verbose_name=_('Content')
    )
    is_important = models.BooleanField(
        default=False,
        verbose_name=_('Is Important')
    )
    follow_up_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Follow-up Date')
    )
    is_resolved = models.BooleanField(
        default=False,
        verbose_name=_('Is Resolved')
    )
    
    class Meta:
        verbose_name = _('Customer Note')
        verbose_name_plural = _('Customer Notes')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.customer} - {self.title}"


class Supplier(TenantAwareModel):
    """
    Supplier model for jewelry suppliers and vendors.
    """
    SUPPLIER_TYPES = [
        ('manufacturer', _('Manufacturer')),
        ('wholesaler', _('Wholesaler')),
        ('gemstone_dealer', _('Gemstone Dealer')),
        ('gold_supplier', _('Gold Supplier')),
        ('service_provider', _('Service Provider')),
    ]
    
    # Basic information
    name = models.CharField(
        max_length=200,
        verbose_name=_('Supplier Name')
    )
    persian_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Persian Name')
    )
    supplier_type = models.CharField(
        max_length=20,
        choices=SUPPLIER_TYPES,
        verbose_name=_('Supplier Type')
    )
    
    # Contact information
    contact_person = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Contact Person')
    )
    phone_number = models.CharField(
        max_length=15,
        verbose_name=_('Phone Number')
    )
    email = models.EmailField(
        blank=True,
        verbose_name=_('Email Address')
    )
    website = models.URLField(
        blank=True,
        verbose_name=_('Website')
    )
    
    # Address
    address = models.TextField(
        blank=True,
        verbose_name=_('Address')
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('City')
    )
    
    # Business information
    tax_id = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Tax ID')
    )
    payment_terms = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Payment Terms')
    )
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Credit Limit (Toman)')
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    is_preferred = models.BooleanField(
        default=False,
        verbose_name=_('Is Preferred Supplier')
    )
    
    # Performance tracking
    total_orders = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total Orders')
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_('Total Order Amount (Toman)')
    )
    last_order_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last Order Date')
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes')
    )
    
    class Meta:
        verbose_name = _('Supplier')
        verbose_name_plural = _('Suppliers')
        indexes = [
            models.Index(fields=['supplier_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_preferred']),
        ]
    
    def __str__(self):
        return self.persian_name or self.name
    
    def update_order_stats(self, amount):
        """Update supplier order statistics."""
        from django.utils import timezone
        
        self.total_orders += 1
        self.total_amount += amount
        self.last_order_date = timezone.now()
        
        self.save(update_fields=[
            'total_orders',
            'total_amount', 
            'last_order_date',
            'updated_at'
        ])


class PurchaseOrder(TenantAwareModel):
    """
    Purchase order model for supplier relationship management.
    """
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('sent', _('Sent to Supplier')),
        ('confirmed', _('Confirmed by Supplier')),
        ('partially_received', _('Partially Received')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    ]
    
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('normal', _('Normal')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    ]
    
    # Basic information
    order_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Order Number')
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        verbose_name=_('Supplier')
    )
    
    # Order details
    order_date = models.DateField(
        verbose_name=_('Order Date')
    )
    expected_delivery_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Expected Delivery Date')
    )
    actual_delivery_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Actual Delivery Date')
    )
    
    # Status and priority
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name=_('Status')
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name=_('Priority')
    )
    
    # Financial information
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Subtotal (Toman)')
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Tax Amount (Toman)')
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Discount Amount (Toman)')
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Total Amount (Toman)')
    )
    
    # Payment information
    payment_terms = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Payment Terms')
    )
    payment_due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Payment Due Date')
    )
    is_paid = models.BooleanField(
        default=False,
        verbose_name=_('Is Paid')
    )
    payment_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Payment Date')
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
    
    # Delivery information
    delivery_address = models.TextField(
        blank=True,
        verbose_name=_('Delivery Address')
    )
    shipping_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Shipping Cost (Toman)')
    )
    
    class Meta:
        verbose_name = _('Purchase Order')
        verbose_name_plural = _('Purchase Orders')
        ordering = ['-order_date', '-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['supplier']),
            models.Index(fields=['status']),
            models.Index(fields=['order_date']),
            models.Index(fields=['expected_delivery_date']),
        ]
    
    def __str__(self):
        return f"{self.order_number} - {self.supplier.name}"
    
    def save(self, *args, **kwargs):
        """Generate order number if not provided."""
        if not self.order_number:
            self.order_number = self.generate_order_number()
        
        # Calculate total amount
        self.total_amount = self.subtotal + self.tax_amount + self.shipping_cost - self.discount_amount
        
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Generate unique order number."""
        from django.utils import timezone
        import random
        
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(random.randint(1000, 9999))
        return f"PO-{date_str}-{random_str}"
    
    @property
    def is_overdue(self):
        """Check if order is overdue."""
        if not self.expected_delivery_date:
            return False
        
        from django.utils import timezone
        today = timezone.now().date()
        
        return (self.status not in ['completed', 'cancelled'] and 
                self.expected_delivery_date < today)
    
    @property
    def days_until_delivery(self):
        """Calculate days until expected delivery."""
        if not self.expected_delivery_date:
            return None
        
        from django.utils import timezone
        today = timezone.now().date()
        delta = self.expected_delivery_date - today
        
        return delta.days
    
    def mark_as_sent(self):
        """Mark order as sent to supplier."""
        self.status = 'sent'
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_as_confirmed(self):
        """Mark order as confirmed by supplier."""
        self.status = 'confirmed'
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_as_received(self, partial=False):
        """Mark order as received."""
        if partial:
            self.status = 'partially_received'
        else:
            self.status = 'completed'
            from django.utils import timezone
            self.actual_delivery_date = timezone.now().date()
        
        self.save(update_fields=['status', 'actual_delivery_date', 'updated_at'])
        
        # Update supplier statistics
        if self.status == 'completed':
            self.supplier.update_order_stats(self.total_amount)
    
    def cancel_order(self, reason=""):
        """Cancel the purchase order."""
        self.status = 'cancelled'
        if reason:
            self.internal_notes += f"\nCancelled: {reason}"
        
        self.save(update_fields=['status', 'internal_notes', 'updated_at'])


class PurchaseOrderItem(TenantAwareModel):
    """
    Individual items in a purchase order.
    """
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Purchase Order')
    )
    
    # Item details
    item_name = models.CharField(
        max_length=200,
        verbose_name=_('Item Name')
    )
    item_description = models.TextField(
        blank=True,
        verbose_name=_('Item Description')
    )
    sku = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('SKU')
    )
    
    # Quantity and pricing
    quantity_ordered = models.PositiveIntegerField(
        verbose_name=_('Quantity Ordered')
    )
    quantity_received = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Quantity Received')
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Unit Price (Toman)')
    )
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Total Price (Toman)')
    )
    
    # Item specifications (for jewelry)
    weight_grams = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_('Weight (Grams)')
    )
    karat = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Karat')
    )
    gemstone_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Gemstone Type')
    )
    
    # Status
    is_received = models.BooleanField(
        default=False,
        verbose_name=_('Is Received')
    )
    received_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Received Date')
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes')
    )
    
    class Meta:
        verbose_name = _('Purchase Order Item')
        verbose_name_plural = _('Purchase Order Items')
        ordering = ['id']
    
    def __str__(self):
        return f"{self.purchase_order.order_number} - {self.item_name}"
    
    def save(self, *args, **kwargs):
        """Calculate total price."""
        self.total_price = self.quantity_ordered * self.unit_price
        
        # Check if fully received
        if self.quantity_received >= self.quantity_ordered:
            self.is_received = True
            if not self.received_date:
                from django.utils import timezone
                self.received_date = timezone.now().date()
        
        super().save(*args, **kwargs)
        
        # Update purchase order totals
        self.update_purchase_order_totals()
    
    def update_purchase_order_totals(self):
        """Update purchase order subtotal."""
        po = self.purchase_order
        po.subtotal = sum(item.total_price for item in po.items.all())
        po.save(update_fields=['subtotal', 'total_amount', 'updated_at'])
    
    @property
    def quantity_pending(self):
        """Calculate quantity still pending delivery."""
        return max(0, self.quantity_ordered - self.quantity_received)
    
    @property
    def is_fully_received(self):
        """Check if item is fully received."""
        return self.quantity_received >= self.quantity_ordered
    
    def receive_quantity(self, quantity):
        """Receive a specific quantity of this item."""
        if quantity <= 0:
            return False
        
        max_receivable = self.quantity_pending
        if quantity > max_receivable:
            quantity = max_receivable
        
        self.quantity_received += quantity
        self.save()
        
        return True