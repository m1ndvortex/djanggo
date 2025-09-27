"""
Supplier management backend services for zargar project.
"""
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
import logging

from .models import Supplier, PurchaseOrder, PurchaseOrderItem
from zargar.core.models import TenantAwareModel

logger = logging.getLogger(__name__)


class SupplierPayment(TenantAwareModel):
    """
    Model to track payments made to suppliers.
    """
    PAYMENT_METHODS = [
        ('bank_transfer', _('Bank Transfer')),
        ('cash', _('Cash')),
        ('cheque', _('Cheque')),
        ('credit_card', _('Credit Card')),
        ('promissory_note', _('Promissory Note')),
    ]
    
    PAYMENT_STATUS = [
        ('pending', _('Pending')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]
    
    # Basic information
    payment_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Payment Number')
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name=_('Supplier')
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name=_('Purchase Order')
    )
    
    # Payment details
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Payment Amount (Toman)')
    )
    payment_date = models.DateField(
        verbose_name=_('Payment Date')
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        verbose_name=_('Payment Method')
    )
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default='pending',
        verbose_name=_('Payment Status')
    )
    
    # Reference information
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Reference Number'),
        help_text=_('Bank reference, cheque number, etc.')
    )
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Bank Name')
    )
    account_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Account Number')
    )
    
    # Additional information
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Internal Notes')
    )
    
    # Approval workflow
    is_approved = models.BooleanField(
        default=False,
        verbose_name=_('Is Approved')
    )
    approved_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_supplier_payments',
        verbose_name=_('Approved By')
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Approved At')
    )
    
    class Meta:
        verbose_name = _('Supplier Payment')
        verbose_name_plural = _('Supplier Payments')
        ordering = ['-payment_date', '-created_at']
        indexes = [
            models.Index(fields=['payment_number']),
            models.Index(fields=['supplier']),
            models.Index(fields=['purchase_order']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.payment_number} - {self.supplier.name} - {self.amount:,} تومان"
    
    def save(self, *args, **kwargs):
        """Generate payment number if not provided."""
        if not self.payment_number:
            self.payment_number = self.generate_payment_number()
        
        super().save(*args, **kwargs)
    
    def generate_payment_number(self):
        """Generate unique payment number."""
        date_str = timezone.now().strftime('%Y%m%d')
        last_payment = SupplierPayment.objects.filter(
            payment_number__startswith=f"PAY-{date_str}"
        ).order_by('-payment_number').first()
        
        if last_payment:
            last_seq = int(last_payment.payment_number.split('-')[-1])
            seq = last_seq + 1
        else:
            seq = 1
        
        return f"PAY-{date_str}-{seq:04d}"
    
    def approve_payment(self, approved_by_user):
        """Approve the payment."""
        if self.is_approved:
            raise ValidationError(_('Payment is already approved'))
        
        self.is_approved = True
        self.approved_by = approved_by_user
        self.approved_at = timezone.now()
        self.status = 'processing'
        self.save(update_fields=['is_approved', 'approved_by', 'approved_at', 'status'])
        
        logger.info(f"Payment {self.payment_number} approved by {approved_by_user.username}")
    
    def mark_as_completed(self):
        """Mark payment as completed."""
        if not self.is_approved:
            raise ValidationError(_('Payment must be approved before completion'))
        
        self.status = 'completed'
        self.save(update_fields=['status'])
        
        # Update purchase order payment status if linked
        if self.purchase_order:
            self.purchase_order.check_payment_status()
        
        logger.info(f"Payment {self.payment_number} marked as completed")
    
    def cancel_payment(self, reason=""):
        """Cancel the payment."""
        if self.status == 'completed':
            raise ValidationError(_('Cannot cancel completed payment'))
        
        self.status = 'cancelled'
        if reason:
            self.notes += f"\nCancelled: {reason}"
        
        self.save(update_fields=['status', 'notes'])
        
        logger.info(f"Payment {self.payment_number} cancelled: {reason}")


class DeliverySchedule(TenantAwareModel):
    """
    Model to track delivery schedules for purchase orders.
    """
    DELIVERY_STATUS = [
        ('scheduled', _('Scheduled')),
        ('in_transit', _('In Transit')),
        ('delivered', _('Delivered')),
        ('delayed', _('Delayed')),
        ('cancelled', _('Cancelled')),
    ]
    
    DELIVERY_METHODS = [
        ('pickup', _('Pickup')),
        ('courier', _('Courier')),
        ('postal', _('Postal Service')),
        ('freight', _('Freight')),
        ('supplier_delivery', _('Supplier Delivery')),
    ]
    
    # Basic information
    delivery_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Delivery Number')
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='delivery_schedules',
        verbose_name=_('Purchase Order')
    )
    
    # Delivery details
    scheduled_date = models.DateField(
        verbose_name=_('Scheduled Delivery Date')
    )
    scheduled_time_start = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_('Scheduled Start Time')
    )
    scheduled_time_end = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_('Scheduled End Time')
    )
    actual_delivery_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Actual Delivery Date')
    )
    
    # Delivery method and tracking
    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_METHODS,
        verbose_name=_('Delivery Method')
    )
    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Tracking Number')
    )
    carrier_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Carrier Name')
    )
    
    # Status and progress
    status = models.CharField(
        max_length=20,
        choices=DELIVERY_STATUS,
        default='scheduled',
        verbose_name=_('Delivery Status')
    )
    
    # Delivery address
    delivery_address = models.TextField(
        verbose_name=_('Delivery Address')
    )
    delivery_contact_person = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Contact Person')
    )
    delivery_contact_phone = models.CharField(
        max_length=15,
        blank=True,
        verbose_name=_('Contact Phone')
    )
    
    # Cost and payment
    delivery_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Delivery Cost (Toman)')
    )
    is_delivery_paid = models.BooleanField(
        default=False,
        verbose_name=_('Is Delivery Cost Paid')
    )
    
    # Notes and special instructions
    special_instructions = models.TextField(
        blank=True,
        verbose_name=_('Special Instructions')
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes')
    )
    
    # Received by information
    received_by_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Received By (Name)')
    )
    received_by_signature = models.TextField(
        blank=True,
        verbose_name=_('Received By (Signature)')
    )
    
    class Meta:
        verbose_name = _('Delivery Schedule')
        verbose_name_plural = _('Delivery Schedules')
        ordering = ['scheduled_date', 'scheduled_time_start']
        indexes = [
            models.Index(fields=['delivery_number']),
            models.Index(fields=['purchase_order']),
            models.Index(fields=['scheduled_date']),
            models.Index(fields=['status']),
            models.Index(fields=['tracking_number']),
        ]
    
    def __str__(self):
        return f"{self.delivery_number} - {self.purchase_order.order_number}"
    
    def save(self, *args, **kwargs):
        """Generate delivery number if not provided."""
        if not self.delivery_number:
            self.delivery_number = self.generate_delivery_number()
        
        super().save(*args, **kwargs)
    
    def generate_delivery_number(self):
        """Generate unique delivery number."""
        date_str = timezone.now().strftime('%Y%m%d')
        last_delivery = DeliverySchedule.objects.filter(
            delivery_number__startswith=f"DEL-{date_str}"
        ).order_by('-delivery_number').first()
        
        if last_delivery:
            last_seq = int(last_delivery.delivery_number.split('-')[-1])
            seq = last_seq + 1
        else:
            seq = 1
        
        return f"DEL-{date_str}-{seq:04d}"
    
    @property
    def is_overdue(self):
        """Check if delivery is overdue."""
        if self.status in ['delivered', 'cancelled']:
            return False
        
        today = timezone.now().date()
        return self.scheduled_date < today
    
    @property
    def days_until_delivery(self):
        """Calculate days until scheduled delivery."""
        today = timezone.now().date()
        delta = self.scheduled_date - today
        return delta.days
    
    def mark_as_in_transit(self, tracking_number=""):
        """Mark delivery as in transit."""
        self.status = 'in_transit'
        if tracking_number:
            self.tracking_number = tracking_number
        
        self.save(update_fields=['status', 'tracking_number'])
        
        logger.info(f"Delivery {self.delivery_number} marked as in transit")
    
    def mark_as_delivered(self, received_by_name="", signature=""):
        """Mark delivery as completed."""
        self.status = 'delivered'
        self.actual_delivery_date = timezone.now()
        
        if received_by_name:
            self.received_by_name = received_by_name
        if signature:
            self.received_by_signature = signature
        
        self.save(update_fields=[
            'status', 
            'actual_delivery_date', 
            'received_by_name', 
            'received_by_signature'
        ])
        
        # Update purchase order status
        self.purchase_order.mark_as_received()
        
        logger.info(f"Delivery {self.delivery_number} marked as delivered")
    
    def mark_as_delayed(self, new_date, reason=""):
        """Mark delivery as delayed and reschedule."""
        self.status = 'delayed'
        self.scheduled_date = new_date
        
        if reason:
            self.notes += f"\nDelayed: {reason}"
        
        self.save(update_fields=['status', 'scheduled_date', 'notes'])
        
        logger.info(f"Delivery {self.delivery_number} delayed to {new_date}: {reason}")


class SupplierPerformanceMetrics(TenantAwareModel):
    """
    Model to track supplier performance metrics.
    """
    supplier = models.OneToOneField(
        Supplier,
        on_delete=models.CASCADE,
        related_name='performance_metrics',
        verbose_name=_('Supplier')
    )
    
    # Delivery performance
    total_deliveries = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total Deliveries')
    )
    on_time_deliveries = models.PositiveIntegerField(
        default=0,
        verbose_name=_('On-Time Deliveries')
    )
    late_deliveries = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Late Deliveries')
    )
    
    # Quality metrics
    total_items_received = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total Items Received')
    )
    defective_items = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Defective Items')
    )
    returned_items = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Returned Items')
    )
    
    # Financial metrics
    total_order_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_('Total Order Value (Toman)')
    )
    average_order_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Average Order Value (Toman)')
    )
    
    # Response metrics
    average_response_time_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        verbose_name=_('Average Response Time (Hours)')
    )
    
    # Rating
    overall_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        verbose_name=_('Overall Rating (0-5)')
    )
    
    # Last updated
    last_calculated = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Last Calculated')
    )
    
    class Meta:
        verbose_name = _('Supplier Performance Metrics')
        verbose_name_plural = _('Supplier Performance Metrics')
    
    def __str__(self):
        return f"Performance Metrics - {self.supplier.name}"
    
    @property
    def on_time_delivery_rate(self):
        """Calculate on-time delivery rate as percentage."""
        if self.total_deliveries == 0:
            return 0
        return (self.on_time_deliveries / self.total_deliveries) * 100
    
    @property
    def quality_rate(self):
        """Calculate quality rate as percentage."""
        if self.total_items_received == 0:
            return 0
        good_items = self.total_items_received - self.defective_items - self.returned_items
        return (good_items / self.total_items_received) * 100
    
    def update_metrics(self):
        """Update all performance metrics based on current data."""
        # Get all completed purchase orders for this supplier
        completed_orders = self.supplier.purchase_orders.filter(status='completed')
        
        # Update delivery metrics
        deliveries = DeliverySchedule.objects.filter(
            purchase_order__supplier=self.supplier,
            status='delivered'
        )
        
        self.total_deliveries = deliveries.count()
        self.on_time_deliveries = deliveries.filter(
            actual_delivery_date__date__lte=models.F('scheduled_date')
        ).count()
        self.late_deliveries = self.total_deliveries - self.on_time_deliveries
        
        # Update financial metrics
        self.total_order_value = completed_orders.aggregate(
            total=models.Sum('total_amount')
        )['total'] or 0
        
        if completed_orders.exists():
            self.average_order_value = self.total_order_value / completed_orders.count()
        else:
            self.average_order_value = 0
        
        # Update item metrics
        all_items = PurchaseOrderItem.objects.filter(
            purchase_order__supplier=self.supplier,
            is_received=True
        )
        self.total_items_received = all_items.aggregate(
            total=models.Sum('quantity_received')
        )['total'] or 0
        
        # Calculate overall rating based on performance
        delivery_score = min(self.on_time_delivery_rate / 20, 5)  # Max 5 points
        quality_score = min(self.quality_rate / 20, 5)  # Max 5 points
        
        self.overall_rating = (delivery_score + quality_score) / 2
        
        self.save()
        
        logger.info(f"Updated performance metrics for supplier {self.supplier.name}")


class SupplierManagementService:
    """
    Service class for supplier management operations.
    """
    
    @staticmethod
    def create_supplier_with_contact_terms(
        name: str,
        persian_name: str,
        supplier_type: str,
        contact_info: Dict,
        payment_terms: Dict,
        **kwargs
    ) -> Supplier:
        """
        Create a new supplier with contact information and payment terms.
        
        Args:
            name: Supplier name
            persian_name: Persian name
            supplier_type: Type of supplier
            contact_info: Dictionary with contact details
            payment_terms: Dictionary with payment terms
            **kwargs: Additional supplier fields
        
        Returns:
            Created Supplier instance
        """
        with transaction.atomic():
            supplier = Supplier.objects.create(
                name=name,
                persian_name=persian_name,
                supplier_type=supplier_type,
                contact_person=contact_info.get('contact_person', ''),
                phone_number=contact_info.get('phone_number', ''),
                email=contact_info.get('email', ''),
                website=contact_info.get('website', ''),
                address=contact_info.get('address', ''),
                city=contact_info.get('city', ''),
                tax_id=payment_terms.get('tax_id', ''),
                payment_terms=payment_terms.get('terms', ''),
                credit_limit=payment_terms.get('credit_limit'),
                **kwargs
            )
            
            # Create performance metrics record
            SupplierPerformanceMetrics.objects.create(supplier=supplier)
            
            logger.info(f"Created new supplier: {supplier.name}")
            return supplier
    
    @staticmethod
    def create_purchase_order_workflow(
        supplier: Supplier,
        items: List[Dict],
        order_details: Dict,
        delivery_details: Optional[Dict] = None
    ) -> Tuple[PurchaseOrder, Optional[DeliverySchedule]]:
        """
        Create a complete purchase order with items and optional delivery schedule.
        
        Args:
            supplier: Supplier instance
            items: List of item dictionaries
            order_details: Order details dictionary
            delivery_details: Optional delivery details
        
        Returns:
            Tuple of (PurchaseOrder, DeliverySchedule or None)
        """
        with transaction.atomic():
            # Create purchase order
            po = PurchaseOrder.objects.create(
                supplier=supplier,
                order_date=order_details.get('order_date', timezone.now().date()),
                expected_delivery_date=order_details.get('expected_delivery_date'),
                priority=order_details.get('priority', 'normal'),
                payment_terms=order_details.get('payment_terms', ''),
                payment_due_date=order_details.get('payment_due_date'),
                notes=order_details.get('notes', ''),
                delivery_address=order_details.get('delivery_address', ''),
                shipping_cost=order_details.get('shipping_cost', 0),
                tax_amount=order_details.get('tax_amount', 0),
                discount_amount=order_details.get('discount_amount', 0),
            )
            
            # Create purchase order items
            for item_data in items:
                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    item_name=item_data['name'],
                    item_description=item_data.get('description', ''),
                    sku=item_data.get('sku', ''),
                    quantity_ordered=item_data['quantity'],
                    unit_price=item_data['unit_price'],
                    weight_grams=item_data.get('weight_grams'),
                    karat=item_data.get('karat'),
                    gemstone_type=item_data.get('gemstone_type', ''),
                    notes=item_data.get('notes', ''),
                )
            
            # Create delivery schedule if provided
            delivery_schedule = None
            if delivery_details:
                delivery_schedule = DeliverySchedule.objects.create(
                    purchase_order=po,
                    scheduled_date=delivery_details['scheduled_date'],
                    scheduled_time_start=delivery_details.get('scheduled_time_start'),
                    scheduled_time_end=delivery_details.get('scheduled_time_end'),
                    delivery_method=delivery_details['delivery_method'],
                    delivery_address=delivery_details.get('delivery_address', po.delivery_address),
                    delivery_contact_person=delivery_details.get('contact_person', ''),
                    delivery_contact_phone=delivery_details.get('contact_phone', ''),
                    delivery_cost=delivery_details.get('delivery_cost', 0),
                    special_instructions=delivery_details.get('special_instructions', ''),
                )
            
            logger.info(f"Created purchase order {po.order_number} for supplier {supplier.name}")
            return po, delivery_schedule
    
    @staticmethod
    def process_supplier_payment(
        supplier: Supplier,
        amount: Decimal,
        payment_method: str,
        payment_date=None,
        purchase_order: Optional[PurchaseOrder] = None,
        reference_number: str = "",
        description: str = "",
        **kwargs
    ) -> SupplierPayment:
        """
        Process a payment to a supplier.
        
        Args:
            supplier: Supplier to pay
            amount: Payment amount
            payment_method: Payment method
            payment_date: Payment date (defaults to today)
            purchase_order: Optional linked purchase order
            reference_number: Payment reference
            description: Payment description
            **kwargs: Additional payment fields
        
        Returns:
            Created SupplierPayment instance
        """
        if payment_date is None:
            payment_date = timezone.now().date()
        
        payment = SupplierPayment.objects.create(
            supplier=supplier,
            purchase_order=purchase_order,
            amount=amount,
            payment_date=payment_date,
            payment_method=payment_method,
            reference_number=reference_number,
            description=description,
            bank_name=kwargs.get('bank_name', ''),
            account_number=kwargs.get('account_number', ''),
            notes=kwargs.get('notes', ''),
        )
        
        logger.info(f"Created payment {payment.payment_number} for supplier {supplier.name}")
        return payment
    
    @staticmethod
    def update_delivery_tracking(
        delivery_schedule: DeliverySchedule,
        status: str,
        tracking_number: str = "",
        notes: str = ""
    ) -> DeliverySchedule:
        """
        Update delivery tracking information.
        
        Args:
            delivery_schedule: DeliverySchedule instance
            status: New status
            tracking_number: Tracking number
            notes: Additional notes
        
        Returns:
            Updated DeliverySchedule instance
        """
        delivery_schedule.status = status
        
        if tracking_number:
            delivery_schedule.tracking_number = tracking_number
        
        if notes:
            delivery_schedule.notes += f"\n{timezone.now()}: {notes}"
        
        delivery_schedule.save()
        
        logger.info(f"Updated delivery tracking for {delivery_schedule.delivery_number}")
        return delivery_schedule
    
    @staticmethod
    def get_supplier_performance_report(supplier: Supplier) -> Dict:
        """
        Generate comprehensive performance report for a supplier.
        
        Args:
            supplier: Supplier instance
        
        Returns:
            Dictionary with performance metrics
        """
        # Update metrics first
        metrics, created = SupplierPerformanceMetrics.objects.get_or_create(
            supplier=supplier
        )
        metrics.update_metrics()
        
        # Get recent orders
        recent_orders = supplier.purchase_orders.filter(
            order_date__gte=timezone.now().date() - timezone.timedelta(days=90)
        ).order_by('-order_date')[:10]
        
        # Get pending deliveries
        pending_deliveries = DeliverySchedule.objects.filter(
            purchase_order__supplier=supplier,
            status__in=['scheduled', 'in_transit']
        ).order_by('scheduled_date')
        
        # Get recent payments
        recent_payments = supplier.payments.filter(
            payment_date__gte=timezone.now().date() - timezone.timedelta(days=90)
        ).order_by('-payment_date')[:10]
        
        return {
            'supplier': supplier,
            'metrics': metrics,
            'recent_orders': recent_orders,
            'pending_deliveries': pending_deliveries,
            'recent_payments': recent_payments,
            'on_time_delivery_rate': metrics.on_time_delivery_rate,
            'quality_rate': metrics.quality_rate,
            'overall_rating': metrics.overall_rating,
        }
    
    @staticmethod
    def get_overdue_deliveries() -> List[DeliverySchedule]:
        """
        Get all overdue deliveries across all suppliers.
        
        Returns:
            List of overdue DeliverySchedule instances
        """
        today = timezone.now().date()
        return DeliverySchedule.objects.filter(
            scheduled_date__lt=today,
            status__in=['scheduled', 'in_transit', 'delayed']
        ).select_related('purchase_order', 'purchase_order__supplier').order_by('scheduled_date')
    
    @staticmethod
    def get_pending_payments() -> List[SupplierPayment]:
        """
        Get all pending supplier payments.
        
        Returns:
            List of pending SupplierPayment instances
        """
        return SupplierPayment.objects.filter(
            status='pending'
        ).select_related('supplier', 'purchase_order').order_by('payment_date')