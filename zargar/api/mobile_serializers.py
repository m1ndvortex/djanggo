"""
Mobile-specific serializers for ZARGAR jewelry SaaS platform.
Optimized for mobile app data transfer and offline synchronization.
"""
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from decimal import Decimal
import uuid

from zargar.jewelry.models import JewelryItem, Category
from zargar.customers.models import Customer
from zargar.pos.models import POSTransaction, POSTransactionLineItem
from zargar.core.persian_number_formatter import PersianNumberFormatter


class MobileJewelryItemSerializer(serializers.ModelSerializer):
    """
    Mobile-optimized serializer for jewelry items.
    Includes only essential fields for mobile POS and inventory.
    """
    category_name = serializers.CharField(source='category.name_persian', read_only=True)
    primary_photo_url = serializers.SerializerMethodField()
    formatted_price = serializers.SerializerMethodField()
    formatted_weight = serializers.SerializerMethodField()
    is_low_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = JewelryItem
        fields = [
            'id', 'name', 'sku', 'barcode', 'category_name',
            'weight_grams', 'karat', 'selling_price', 'formatted_price',
            'formatted_weight', 'status', 'quantity', 'minimum_stock',
            'is_low_stock', 'primary_photo_url', 'created_at'
        ]
    
    def get_primary_photo_url(self, obj):
        """Get primary photo URL for mobile display."""
        primary_photo = obj.photos.filter(is_primary=True).first()
        if primary_photo and primary_photo.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary_photo.image.url)
        return None
    
    def get_formatted_price(self, obj):
        """Get formatted price in Persian numerals."""
        formatter = PersianNumberFormatter()
        return formatter.format_currency(obj.selling_price, use_persian_digits=True)
    
    def get_formatted_weight(self, obj):
        """Get formatted weight in Persian numerals."""
        formatter = PersianNumberFormatter()
        return formatter.format_weight(obj.weight_grams, 'gram', use_persian_digits=True)


class MobileCustomerSerializer(serializers.ModelSerializer):
    """
    Mobile-optimized serializer for customers.
    Includes essential fields for mobile POS customer lookup.
    """
    full_persian_name = serializers.ReadOnlyField()
    formatted_loyalty_points = serializers.SerializerMethodField()
    formatted_total_purchases = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'first_name', 'last_name', 'persian_first_name', 'persian_last_name',
            'full_persian_name', 'phone_number', 'email', 'customer_type',
            'loyalty_points', 'formatted_loyalty_points', 'total_purchases',
            'formatted_total_purchases', 'is_vip', 'created_at'
        ]
        read_only_fields = ['id', 'total_purchases', 'created_at']
    
    def get_formatted_loyalty_points(self, obj):
        """Get formatted loyalty points in Persian numerals."""
        formatter = PersianNumberFormatter()
        return formatter.format_number(obj.loyalty_points, use_persian_digits=True)
    
    def get_formatted_total_purchases(self, obj):
        """Get formatted total purchases in Persian numerals."""
        formatter = PersianNumberFormatter()
        return formatter.format_currency(obj.total_purchases, use_persian_digits=True)
    
    def validate_phone_number(self, value):
        """Validate Persian phone number format."""
        import re
        if not re.match(r'^09\d{9}$', value):
            raise serializers.ValidationError(
                _('Phone number must be in format: 09123456789')
            )
        return value


class MobilePOSTransactionLineItemSerializer(serializers.ModelSerializer):
    """
    Mobile-optimized serializer for POS transaction line items.
    """
    jewelry_item_name = serializers.CharField(source='jewelry_item.name', read_only=True)
    formatted_unit_price = serializers.SerializerMethodField()
    formatted_line_total = serializers.SerializerMethodField()
    formatted_quantity = serializers.SerializerMethodField()
    
    class Meta:
        model = POSTransactionLineItem
        fields = [
            'id', 'jewelry_item', 'jewelry_item_name', 'item_name',
            'quantity', 'formatted_quantity', 'unit_price', 'formatted_unit_price',
            'line_total', 'formatted_line_total', 'gold_weight_grams', 'gold_karat'
        ]
        read_only_fields = ['id', 'line_total']
    
    def get_formatted_unit_price(self, obj):
        """Get formatted unit price in Persian numerals."""
        formatter = PersianNumberFormatter()
        return formatter.format_currency(obj.unit_price, use_persian_digits=True)
    
    def get_formatted_line_total(self, obj):
        """Get formatted line total in Persian numerals."""
        formatter = PersianNumberFormatter()
        return formatter.format_currency(obj.line_total, use_persian_digits=True)
    
    def get_formatted_quantity(self, obj):
        """Get formatted quantity in Persian numerals."""
        formatter = PersianNumberFormatter()
        return formatter.format_number(obj.quantity, use_persian_digits=True)


class MobilePOSTransactionSerializer(serializers.ModelSerializer):
    """
    Mobile-optimized serializer for POS transactions.
    Includes formatted fields for mobile display.
    """
    customer_name = serializers.CharField(source='customer.full_persian_name', read_only=True)
    salesperson_name = serializers.CharField(source='created_by.full_persian_name', read_only=True)
    line_items = MobilePOSTransactionLineItemSerializer(many=True, read_only=True)
    formatted_total_amount = serializers.SerializerMethodField()
    formatted_amount_paid = serializers.SerializerMethodField()
    formatted_change_amount = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = POSTransaction
        fields = [
            'id', 'transaction_id', 'transaction_number', 'customer', 'customer_name',
            'salesperson_name', 'transaction_date', 'transaction_date_shamsi',
            'transaction_type', 'status', 'status_display', 'total_amount',
            'formatted_total_amount', 'amount_paid', 'formatted_amount_paid',
            'change_amount', 'formatted_change_amount', 'payment_method',
            'payment_method_display', 'gold_price_18k_at_transaction',
            'total_gold_weight_grams', 'line_items', 'is_offline_transaction',
            'sync_status'
        ]
    
    def get_formatted_total_amount(self, obj):
        """Get formatted total amount in Persian numerals."""
        formatter = PersianNumberFormatter()
        return formatter.format_currency(obj.total_amount, use_persian_digits=True)
    
    def get_formatted_amount_paid(self, obj):
        """Get formatted amount paid in Persian numerals."""
        formatter = PersianNumberFormatter()
        return formatter.format_currency(obj.amount_paid, use_persian_digits=True)
    
    def get_formatted_change_amount(self, obj):
        """Get formatted change amount in Persian numerals."""
        formatter = PersianNumberFormatter()
        return formatter.format_currency(obj.change_amount, use_persian_digits=True)


class OfflineTransactionLineItemSerializer(serializers.Serializer):
    """
    Serializer for offline transaction line items.
    Used for creating transactions from offline data.
    """
    jewelry_item_id = serializers.IntegerField(required=False, allow_null=True)
    item_name = serializers.CharField(max_length=200)
    item_sku = serializers.CharField(max_length=50, required=False, allow_blank=True)
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    gold_weight_grams = serializers.DecimalField(
        max_digits=10, decimal_places=3, required=False, allow_null=True
    )
    gold_karat = serializers.IntegerField(required=False, allow_null=True)
    discount_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    line_notes = serializers.CharField(required=False, allow_blank=True)


class OfflineTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for offline POS transactions.
    Handles creation and synchronization of offline transaction data.
    """
    line_items = OfflineTransactionLineItemSerializer(many=True, write_only=True)
    offline_transaction_id = serializers.UUIDField(required=False, allow_null=True)
    device_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    offline_created_at = serializers.DateTimeField(required=False, allow_null=True)
    
    class Meta:
        model = POSTransaction
        fields = [
            'transaction_id', 'customer', 'transaction_date', 'transaction_type',
            'subtotal', 'tax_amount', 'discount_amount', 'total_amount',
            'payment_method', 'amount_paid', 'gold_price_18k_at_transaction',
            'transaction_notes', 'line_items', 'offline_transaction_id',
            'device_id', 'offline_created_at'
        ]
    
    def validate_line_items(self, value):
        """Validate that transaction has at least one line item."""
        if not value:
            raise serializers.ValidationError(_('Transaction must have at least one line item.'))
        return value
    
    def validate_amount_paid(self, value):
        """Validate that amount paid is not negative."""
        if value < 0:
            raise serializers.ValidationError(_('Amount paid cannot be negative.'))
        return value
    
    def create(self, validated_data):
        """Create offline transaction with line items."""
        line_items_data = validated_data.pop('line_items')
        offline_transaction_id = validated_data.pop('offline_transaction_id', None)
        device_id = validated_data.pop('device_id', '')
        offline_created_at = validated_data.pop('offline_created_at', None)
        
        with transaction.atomic():
            # Set offline transaction fields
            validated_data['is_offline_transaction'] = True
            validated_data['sync_status'] = 'pending_sync'
            validated_data['status'] = 'offline_pending'
            
            # Create transaction
            pos_transaction = POSTransaction.objects.create(**validated_data)
            
            # Store offline metadata
            offline_metadata = {
                'offline_transaction_id': str(offline_transaction_id) if offline_transaction_id else None,
                'device_id': device_id,
                'offline_created_at': offline_created_at.isoformat() if offline_created_at else None,
            }
            pos_transaction.offline_data.update(offline_metadata)
            
            # Create line items
            for item_data in line_items_data:
                jewelry_item = None
                if item_data.get('jewelry_item_id'):
                    try:
                        jewelry_item = JewelryItem.objects.get(id=item_data['jewelry_item_id'])
                    except JewelryItem.DoesNotExist:
                        pass
                
                POSTransactionLineItem.objects.create(
                    transaction=pos_transaction,
                    jewelry_item=jewelry_item,
                    item_name=item_data['item_name'],
                    item_sku=item_data.get('item_sku', ''),
                    quantity=item_data['quantity'],
                    unit_price=item_data['unit_price'],
                    gold_weight_grams=item_data.get('gold_weight_grams'),
                    gold_karat=item_data.get('gold_karat'),
                    discount_amount=item_data.get('discount_amount', Decimal('0.00')),
                    line_notes=item_data.get('line_notes', '')
                )
            
            # Recalculate totals
            pos_transaction.calculate_totals()
            pos_transaction.save()
        
        return pos_transaction


class MobileInventoryUpdateSerializer(serializers.Serializer):
    """
    Serializer for mobile inventory updates.
    Used for bulk stock level adjustments.
    """
    item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=0)
    reason = serializers.CharField(max_length=200, required=False, default='Mobile update')
    adjustment_type = serializers.ChoiceField(
        choices=[('set', 'Set Quantity'), ('add', 'Add Quantity'), ('subtract', 'Subtract Quantity')],
        default='set'
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_item_id(self, value):
        """Validate that jewelry item exists."""
        try:
            JewelryItem.objects.get(id=value)
        except JewelryItem.DoesNotExist:
            raise serializers.ValidationError(_('Jewelry item not found.'))
        return value


class MobileSyncDataSerializer(serializers.Serializer):
    """
    Serializer for mobile synchronization data.
    Handles data exchange between mobile app and server.
    """
    last_sync_timestamp = serializers.DateTimeField(required=False, allow_null=True)
    device_info = serializers.DictField(required=False)
    app_version = serializers.CharField(max_length=20, required=False)
    
    # Data to sync
    transactions = OfflineTransactionSerializer(many=True, required=False)
    inventory_updates = MobileInventoryUpdateSerializer(many=True, required=False)
    customers = MobileCustomerSerializer(many=True, required=False)
    
    def validate_device_info(self, value):
        """Validate device information structure."""
        if value:
            required_fields = ['device_id', 'platform', 'os_version']
            for field in required_fields:
                if field not in value:
                    raise serializers.ValidationError(
                        f'Device info must include {field}'
                    )
        return value


class MobileNotificationSerializer(serializers.Serializer):
    """
    Serializer for mobile push notifications.
    """
    title = serializers.CharField(max_length=100)
    message = serializers.CharField(max_length=500)
    notification_type = serializers.ChoiceField(
        choices=[
            ('payment_reminder', 'Payment Reminder'),
            ('appointment', 'Appointment'),
            ('promotion', 'Promotion'),
            ('system', 'System Notification'),
            ('custom', 'Custom Message')
        ],
        default='custom'
    )
    priority = serializers.ChoiceField(
        choices=[('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')],
        default='normal'
    )
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    action_url = serializers.URLField(required=False, allow_blank=True)
    custom_data = serializers.DictField(required=False)
    
    def validate(self, data):
        """Validate notification data."""
        if data.get('scheduled_at') and data.get('expires_at'):
            if data['scheduled_at'] >= data['expires_at']:
                raise serializers.ValidationError(
                    _('Expiry time must be after scheduled time.')
                )
        return data


class MobileDeviceRegistrationSerializer(serializers.Serializer):
    """
    Serializer for mobile device registration.
    Used for push notification setup.
    """
    device_token = serializers.CharField(max_length=500)
    device_type = serializers.ChoiceField(
        choices=[('android', 'Android'), ('ios', 'iOS')],
        default='android'
    )
    device_id = serializers.CharField(max_length=100)
    app_version = serializers.CharField(max_length=20)
    os_version = serializers.CharField(max_length=20, required=False)
    device_model = serializers.CharField(max_length=100, required=False)
    timezone = serializers.CharField(max_length=50, default='Asia/Tehran')
    language = serializers.CharField(max_length=10, default='fa')
    
    # Notification preferences
    enable_push_notifications = serializers.BooleanField(default=True)
    enable_payment_reminders = serializers.BooleanField(default=True)
    enable_appointment_reminders = serializers.BooleanField(default=True)
    enable_promotions = serializers.BooleanField(default=False)
    enable_system_notifications = serializers.BooleanField(default=True)
    
    def validate_device_token(self, value):
        """Validate device token format."""
        if len(value) < 10:
            raise serializers.ValidationError(_('Invalid device token format.'))
        return value


class MobileDashboardSerializer(serializers.Serializer):
    """
    Serializer for mobile dashboard data.
    Provides summary information for mobile app home screen.
    """
    today_sales_count = serializers.IntegerField()
    today_sales_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    formatted_today_sales = serializers.CharField()
    
    pending_sync_count = serializers.IntegerField()
    low_stock_count = serializers.IntegerField()
    
    recent_transactions = MobilePOSTransactionSerializer(many=True)
    low_stock_items = MobileJewelryItemSerializer(many=True)
    
    current_gold_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    formatted_gold_price = serializers.CharField()
    
    last_sync_time = serializers.DateTimeField()
    server_time = serializers.DateTimeField()


class MobileErrorReportSerializer(serializers.Serializer):
    """
    Serializer for mobile error reporting.
    Allows mobile app to report errors and crashes.
    """
    error_type = serializers.ChoiceField(
        choices=[
            ('crash', 'App Crash'),
            ('api_error', 'API Error'),
            ('sync_error', 'Sync Error'),
            ('ui_error', 'UI Error'),
            ('other', 'Other Error')
        ]
    )
    error_message = serializers.CharField(max_length=1000)
    stack_trace = serializers.CharField(required=False, allow_blank=True)
    device_info = serializers.DictField()
    app_version = serializers.CharField(max_length=20)
    occurred_at = serializers.DateTimeField()
    user_actions = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False
    )
    additional_data = serializers.DictField(required=False)
    
    def validate_device_info(self, value):
        """Validate device information for error reporting."""
        required_fields = ['device_id', 'platform', 'os_version', 'device_model']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(
                    f'Device info must include {field} for error reporting'
                )
        return value