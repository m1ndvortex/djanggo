"""
Serializers for supplier management API endpoints.
"""
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

from .models import Supplier, PurchaseOrder, PurchaseOrderItem
from .supplier_services import SupplierPayment, DeliverySchedule, SupplierPerformanceMetrics


class SupplierSerializer(serializers.ModelSerializer):
    """
    Serializer for Supplier model.
    """
    display_name = serializers.SerializerMethodField()
    performance_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'persian_name', 'display_name', 'supplier_type',
            'contact_person', 'phone_number', 'email', 'website',
            'address', 'city', 'tax_id', 'payment_terms', 'credit_limit',
            'is_active', 'is_preferred', 'total_orders', 'total_amount',
            'last_order_date', 'notes', 'performance_rating',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['total_orders', 'total_amount', 'last_order_date', 'performance_rating']
    
    def get_display_name(self, obj):
        """Get display name (Persian if available, otherwise English)."""
        return obj.persian_name or obj.name
    
    def get_performance_rating(self, obj):
        """Get supplier performance rating."""
        try:
            return float(obj.performance_metrics.overall_rating)
        except (AttributeError, SupplierPerformanceMetrics.DoesNotExist):
            return 0.0


class SupplierCreateSerializer(serializers.Serializer):
    """
    Serializer for creating suppliers with contact and payment terms.
    """
    # Basic information
    name = serializers.CharField(max_length=200)
    persian_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    supplier_type = serializers.ChoiceField(choices=Supplier.SUPPLIER_TYPES)
    
    # Contact information
    contact_person = serializers.CharField(max_length=100, required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=15)
    email = serializers.EmailField(required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    # Payment terms
    tax_id = serializers.CharField(max_length=20, required=False, allow_blank=True)
    payment_terms = serializers.CharField(max_length=100, required=False, allow_blank=True)
    credit_limit = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        required=False, 
        allow_null=True
    )
    
    # Status
    is_active = serializers.BooleanField(default=True)
    is_preferred = serializers.BooleanField(default=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def create(self, validated_data):
        """Create supplier using the service."""
        from .supplier_services import SupplierManagementService
        
        contact_info = {
            'contact_person': validated_data.get('contact_person', ''),
            'phone_number': validated_data.get('phone_number', ''),
            'email': validated_data.get('email', ''),
            'website': validated_data.get('website', ''),
            'address': validated_data.get('address', ''),
            'city': validated_data.get('city', ''),
        }
        
        payment_terms = {
            'tax_id': validated_data.get('tax_id', ''),
            'terms': validated_data.get('payment_terms', ''),
            'credit_limit': validated_data.get('credit_limit'),
        }
        
        return SupplierManagementService.create_supplier_with_contact_terms(
            name=validated_data['name'],
            persian_name=validated_data.get('persian_name', ''),
            supplier_type=validated_data['supplier_type'],
            contact_info=contact_info,
            payment_terms=payment_terms,
            is_active=validated_data.get('is_active', True),
            is_preferred=validated_data.get('is_preferred', False),
            notes=validated_data.get('notes', ''),
        )


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for PurchaseOrderItem model.
    """
    quantity_pending = serializers.ReadOnlyField()
    is_fully_received = serializers.ReadOnlyField()
    
    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'item_name', 'item_description', 'sku',
            'quantity_ordered', 'quantity_received', 'quantity_pending',
            'unit_price', 'total_price', 'weight_grams', 'karat',
            'gemstone_type', 'is_received', 'received_date',
            'is_fully_received', 'notes'
        ]
        read_only_fields = ['total_price', 'is_received', 'received_date']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    """
    Serializer for PurchaseOrder model.
    """
    supplier_name = serializers.CharField(source='supplier.persian_name', read_only=True)
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    is_overdue = serializers.ReadOnlyField()
    days_until_delivery = serializers.ReadOnlyField()
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'order_number', 'supplier', 'supplier_name',
            'order_date', 'expected_delivery_date', 'actual_delivery_date',
            'status', 'priority', 'subtotal', 'tax_amount', 'discount_amount',
            'total_amount', 'payment_terms', 'payment_due_date',
            'is_paid', 'payment_date', 'notes', 'internal_notes',
            'delivery_address', 'shipping_cost', 'items',
            'is_overdue', 'days_until_delivery', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'order_number', 'total_amount', 'is_overdue', 
            'days_until_delivery', 'items'
        ]


class PurchaseOrderCreateSerializer(serializers.Serializer):
    """
    Serializer for creating purchase orders with items and delivery details.
    """
    # Order details
    supplier_id = serializers.IntegerField()
    order_date = serializers.DateField(required=False)
    expected_delivery_date = serializers.DateField(required=False, allow_null=True)
    priority = serializers.ChoiceField(
        choices=PurchaseOrder.PRIORITY_CHOICES, 
        default='normal'
    )
    payment_terms = serializers.CharField(max_length=100, required=False, allow_blank=True)
    payment_due_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    delivery_address = serializers.CharField(required=False, allow_blank=True)
    shipping_cost = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0
    )
    tax_amount = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0
    )
    discount_amount = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0
    )
    
    # Items
    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        help_text=_("List of items to order")
    )
    
    # Optional delivery details
    delivery_details = serializers.DictField(required=False, allow_null=True)
    
    def validate_supplier_id(self, value):
        """Validate supplier exists and is active."""
        try:
            supplier = Supplier.objects.get(id=value, is_active=True)
            return value
        except Supplier.DoesNotExist:
            raise serializers.ValidationError(_("Active supplier not found"))
    
    def validate_items(self, value):
        """Validate items list."""
        required_fields = ['name', 'quantity', 'unit_price']
        
        for i, item in enumerate(value):
            for field in required_fields:
                if field not in item:
                    raise serializers.ValidationError(
                        f"Item {i+1}: '{field}' is required"
                    )
            
            # Validate quantity and price
            try:
                quantity = int(item['quantity'])
                if quantity <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    f"Item {i+1}: quantity must be a positive integer"
                )
            
            try:
                unit_price = Decimal(str(item['unit_price']))
                if unit_price < 0:
                    raise ValueError()
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    f"Item {i+1}: unit_price must be a non-negative number"
                )
        
        return value
    
    def create(self, validated_data):
        """Create purchase order using the service."""
        from .supplier_services import SupplierManagementService
        from django.utils import timezone
        
        supplier = Supplier.objects.get(id=validated_data['supplier_id'])
        items = validated_data.pop('items')
        delivery_details = validated_data.pop('delivery_details', None)
        
        # Prepare order details
        order_details = {
            'order_date': validated_data.get('order_date', timezone.now().date()),
            'expected_delivery_date': validated_data.get('expected_delivery_date'),
            'priority': validated_data.get('priority', 'normal'),
            'payment_terms': validated_data.get('payment_terms', ''),
            'payment_due_date': validated_data.get('payment_due_date'),
            'notes': validated_data.get('notes', ''),
            'delivery_address': validated_data.get('delivery_address', ''),
            'shipping_cost': validated_data.get('shipping_cost', 0),
            'tax_amount': validated_data.get('tax_amount', 0),
            'discount_amount': validated_data.get('discount_amount', 0),
        }
        
        po, delivery_schedule = SupplierManagementService.create_purchase_order_workflow(
            supplier=supplier,
            items=items,
            order_details=order_details,
            delivery_details=delivery_details
        )
        
        return po


class SupplierPaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for SupplierPayment model.
    """
    supplier_name = serializers.CharField(source='supplier.persian_name', read_only=True)
    purchase_order_number = serializers.CharField(
        source='purchase_order.order_number', 
        read_only=True
    )
    
    class Meta:
        model = SupplierPayment
        fields = [
            'id', 'payment_number', 'supplier', 'supplier_name',
            'purchase_order', 'purchase_order_number', 'amount',
            'payment_date', 'payment_method', 'status',
            'reference_number', 'bank_name', 'account_number',
            'description', 'notes', 'is_approved', 'approved_by',
            'approved_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'payment_number', 'is_approved', 'approved_by', 'approved_at'
        ]


class SupplierPaymentCreateSerializer(serializers.Serializer):
    """
    Serializer for creating supplier payments.
    """
    supplier_id = serializers.IntegerField()
    purchase_order_id = serializers.IntegerField(required=False, allow_null=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_date = serializers.DateField(required=False)
    payment_method = serializers.ChoiceField(choices=SupplierPayment.PAYMENT_METHODS)
    reference_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    bank_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    account_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_supplier_id(self, value):
        """Validate supplier exists."""
        try:
            Supplier.objects.get(id=value)
            return value
        except Supplier.DoesNotExist:
            raise serializers.ValidationError(_("Supplier not found"))
    
    def validate_purchase_order_id(self, value):
        """Validate purchase order exists if provided."""
        if value is not None:
            try:
                PurchaseOrder.objects.get(id=value)
            except PurchaseOrder.DoesNotExist:
                raise serializers.ValidationError(_("Purchase order not found"))
        return value
    
    def validate_amount(self, value):
        """Validate payment amount is positive."""
        if value <= 0:
            raise serializers.ValidationError(_("Payment amount must be positive"))
        return value
    
    def create(self, validated_data):
        """Create supplier payment using the service."""
        from .supplier_services import SupplierManagementService
        
        supplier = Supplier.objects.get(id=validated_data['supplier_id'])
        purchase_order = None
        
        if validated_data.get('purchase_order_id'):
            purchase_order = PurchaseOrder.objects.get(
                id=validated_data['purchase_order_id']
            )
        
        return SupplierManagementService.process_supplier_payment(
            supplier=supplier,
            amount=validated_data['amount'],
            payment_method=validated_data['payment_method'],
            payment_date=validated_data.get('payment_date'),
            purchase_order=purchase_order,
            reference_number=validated_data.get('reference_number', ''),
            description=validated_data.get('description', ''),
            bank_name=validated_data.get('bank_name', ''),
            account_number=validated_data.get('account_number', ''),
            notes=validated_data.get('notes', ''),
        )


class DeliveryScheduleSerializer(serializers.ModelSerializer):
    """
    Serializer for DeliverySchedule model.
    """
    purchase_order_number = serializers.CharField(
        source='purchase_order.order_number', 
        read_only=True
    )
    supplier_name = serializers.CharField(
        source='purchase_order.supplier.persian_name', 
        read_only=True
    )
    is_overdue = serializers.ReadOnlyField()
    days_until_delivery = serializers.ReadOnlyField()
    
    class Meta:
        model = DeliverySchedule
        fields = [
            'id', 'delivery_number', 'purchase_order', 'purchase_order_number',
            'supplier_name', 'scheduled_date', 'scheduled_time_start',
            'scheduled_time_end', 'actual_delivery_date', 'delivery_method',
            'tracking_number', 'carrier_name', 'status', 'delivery_address',
            'delivery_contact_person', 'delivery_contact_phone',
            'delivery_cost', 'is_delivery_paid', 'special_instructions',
            'notes', 'received_by_name', 'received_by_signature',
            'is_overdue', 'days_until_delivery', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'delivery_number', 'actual_delivery_date', 'is_overdue', 
            'days_until_delivery'
        ]


class SupplierPerformanceMetricsSerializer(serializers.ModelSerializer):
    """
    Serializer for SupplierPerformanceMetrics model.
    """
    supplier_name = serializers.CharField(source='supplier.persian_name', read_only=True)
    on_time_delivery_rate = serializers.ReadOnlyField()
    quality_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = SupplierPerformanceMetrics
        fields = [
            'id', 'supplier', 'supplier_name', 'total_deliveries',
            'on_time_deliveries', 'late_deliveries', 'on_time_delivery_rate',
            'total_items_received', 'defective_items', 'returned_items',
            'quality_rate', 'total_order_value', 'average_order_value',
            'average_response_time_hours', 'overall_rating', 'last_calculated'
        ]
        read_only_fields = '__all__'


class SupplierPerformanceReportSerializer(serializers.Serializer):
    """
    Serializer for supplier performance reports.
    """
    supplier = SupplierSerializer(read_only=True)
    metrics = SupplierPerformanceMetricsSerializer(read_only=True)
    recent_orders = PurchaseOrderSerializer(many=True, read_only=True)
    pending_deliveries = DeliveryScheduleSerializer(many=True, read_only=True)
    recent_payments = SupplierPaymentSerializer(many=True, read_only=True)
    on_time_delivery_rate = serializers.FloatField(read_only=True)
    quality_rate = serializers.FloatField(read_only=True)
    overall_rating = serializers.DecimalField(max_digits=3, decimal_places=2, read_only=True)


class DeliveryTrackingUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating delivery tracking information.
    """
    status = serializers.ChoiceField(choices=DeliverySchedule.DELIVERY_STATUS)
    tracking_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    received_by_name = serializers.CharField(
        max_length=100, 
        required=False, 
        allow_blank=True
    )
    received_by_signature = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """Validate delivery tracking update."""
        status = data.get('status')
        
        # If marking as delivered, require received_by_name
        if status == 'delivered' and not data.get('received_by_name'):
            raise serializers.ValidationError({
                'received_by_name': _('Required when marking as delivered')
            })
        
        return data