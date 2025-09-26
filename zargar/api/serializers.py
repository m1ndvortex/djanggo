"""
DRF serializers for API endpoints with tenant-aware validation.
"""
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.db import transaction

from zargar.jewelry.models import JewelryItem, Category, Gemstone, JewelryItemPhoto
from zargar.customers.models import Customer, Supplier
from zargar.pos.models import POSTransaction, POSTransactionLineItem


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for jewelry categories.
    """
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'name_persian', 'description', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class GemstoneSerializer(serializers.ModelSerializer):
    """
    Serializer for gemstones.
    """
    
    class Meta:
        model = Gemstone
        fields = [
            'id', 'name', 'gemstone_type', 'carat_weight', 'cut_grade',
            'color_grade', 'clarity_grade', 'certification_number',
            'certification_authority', 'purchase_price',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_carat_weight(self, value):
        """
        Validate carat weight is positive.
        """
        if value <= 0:
            raise serializers.ValidationError(_('Carat weight must be positive.'))
        return value


class JewelryItemPhotoSerializer(serializers.ModelSerializer):
    """
    Serializer for jewelry item photos.
    """
    
    class Meta:
        model = JewelryItemPhoto
        fields = ['id', 'image', 'caption', 'is_primary', 'order']
        read_only_fields = ['id']


class JewelryItemListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for jewelry item lists.
    """
    category_name = serializers.CharField(source='category.name_persian', read_only=True)
    primary_photo = serializers.SerializerMethodField()
    total_value = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = JewelryItem
        fields = [
            'id', 'name', 'sku', 'category_name', 'weight_grams', 'karat',
            'selling_price', 'status', 'quantity', 'is_low_stock',
            'primary_photo', 'total_value', 'created_at'
        ]
    
    def get_primary_photo(self, obj):
        """
        Get primary photo URL.
        """
        primary_photo = obj.photos.filter(is_primary=True).first()
        if primary_photo and primary_photo.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary_photo.image.url)
        return None


class JewelryItemSerializer(serializers.ModelSerializer):
    """
    Full serializer for jewelry items.
    """
    category_name = serializers.CharField(source='category.name_persian', read_only=True)
    gemstones = GemstoneSerializer(many=True, read_only=True)
    photos = JewelryItemPhotoSerializer(many=True, read_only=True)
    total_value = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = JewelryItem
        fields = [
            'id', 'name', 'sku', 'barcode', 'category', 'category_name',
            'weight_grams', 'karat', 'manufacturing_cost', 'gold_value',
            'gemstone_value', 'selling_price', 'status', 'quantity',
            'minimum_stock', 'description', 'notes', 'gemstones', 'photos',
            'total_value', 'is_low_stock', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'total_value', 'is_low_stock', 'created_at', 'updated_at']
    
    def validate_weight_grams(self, value):
        """
        Validate weight is positive.
        """
        if value <= 0:
            raise serializers.ValidationError(_('Weight must be positive.'))
        return value
    
    def validate_karat(self, value):
        """
        Validate karat is between 1 and 24.
        """
        if not (1 <= value <= 24):
            raise serializers.ValidationError(_('Karat must be between 1 and 24.'))
        return value
    
    def validate_sku(self, value):
        """
        Validate SKU uniqueness within tenant.
        """
        if self.instance:
            # Update case - exclude current instance
            if JewelryItem.objects.exclude(pk=self.instance.pk).filter(sku=value).exists():
                raise serializers.ValidationError(_('SKU must be unique.'))
        else:
            # Create case
            if JewelryItem.objects.filter(sku=value).exists():
                raise serializers.ValidationError(_('SKU must be unique.'))
        return value


class JewelryItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating jewelry items.
    """
    gemstone_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True
    )
    
    class Meta:
        model = JewelryItem
        fields = [
            'name', 'sku', 'barcode', 'category', 'weight_grams', 'karat',
            'manufacturing_cost', 'gold_value', 'gemstone_value', 'selling_price',
            'status', 'quantity', 'minimum_stock', 'description', 'notes',
            'gemstone_ids'
        ]
    
    def validate_weight_grams(self, value):
        """
        Validate weight is positive.
        """
        if value <= 0:
            raise serializers.ValidationError(_('Weight must be positive.'))
        return value
    
    def validate_karat(self, value):
        """
        Validate karat is between 1 and 24.
        """
        if not (1 <= value <= 24):
            raise serializers.ValidationError(_('Karat must be between 1 and 24.'))
        return value
    
    def validate_sku(self, value):
        """
        Validate SKU uniqueness within tenant.
        """
        if JewelryItem.objects.filter(sku=value).exists():
            raise serializers.ValidationError(_('SKU must be unique.'))
        return value
    
    def create(self, validated_data):
        """
        Create jewelry item with gemstones.
        """
        gemstone_ids = validated_data.pop('gemstone_ids', [])
        
        with transaction.atomic():
            jewelry_item = JewelryItem.objects.create(**validated_data)
            
            if gemstone_ids:
                gemstones = Gemstone.objects.filter(id__in=gemstone_ids)
                jewelry_item.gemstones.set(gemstones)
        
        return jewelry_item


class CustomerListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for customer lists.
    """
    full_persian_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'first_name', 'last_name', 'full_persian_name',
            'phone_number', 'customer_type', 'is_vip', 'loyalty_points',
            'total_purchases', 'created_at'
        ]


class CustomerSerializer(serializers.ModelSerializer):
    """
    Full serializer for customers.
    """
    full_name = serializers.ReadOnlyField()
    full_persian_name = serializers.ReadOnlyField()
    is_birthday_today = serializers.ReadOnlyField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'first_name', 'last_name', 'persian_first_name', 'persian_last_name',
            'full_name', 'full_persian_name', 'phone_number', 'email', 'address',
            'city', 'province', 'postal_code', 'birth_date', 'birth_date_shamsi',
            'national_id', 'customer_type', 'loyalty_points', 'total_purchases',
            'last_purchase_date', 'is_active', 'is_vip', 'is_birthday_today',
            'internal_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'full_name', 'full_persian_name', 'total_purchases',
            'last_purchase_date', 'is_birthday_today', 'created_at', 'updated_at'
        ]
    
    def validate_phone_number(self, value):
        """
        Validate Persian phone number format.
        """
        import re
        if not re.match(r'^09\d{9}$', value):
            raise serializers.ValidationError(
                _('Phone number must be in format: 09123456789')
            )
        return value
    
    def validate_national_id(self, value):
        """
        Validate Iranian national ID format.
        """
        if value and len(value) != 10:
            raise serializers.ValidationError(
                _('National ID must be 10 digits.')
            )
        return value


class CustomerCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating customers.
    """
    
    class Meta:
        model = Customer
        fields = [
            'first_name', 'last_name', 'persian_first_name', 'persian_last_name',
            'phone_number', 'email', 'address', 'city', 'province', 'postal_code',
            'birth_date', 'birth_date_shamsi', 'national_id', 'customer_type',
            'internal_notes'
        ]
    
    def validate_phone_number(self, value):
        """
        Validate Persian phone number format and uniqueness.
        """
        import re
        if not re.match(r'^09\d{9}$', value):
            raise serializers.ValidationError(
                _('Phone number must be in format: 09123456789')
            )
        
        if Customer.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(
                _('Customer with this phone number already exists.')
            )
        
        return value


class SupplierSerializer(serializers.ModelSerializer):
    """
    Serializer for suppliers.
    """
    
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'persian_name', 'supplier_type', 'contact_person',
            'phone_number', 'email', 'website', 'address', 'city', 'tax_id',
            'payment_terms', 'credit_limit', 'is_active', 'is_preferred',
            'total_orders', 'total_amount', 'last_order_date', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_orders', 'total_amount', 'last_order_date',
            'created_at', 'updated_at'
        ]


class SupplierCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating suppliers.
    """
    
    class Meta:
        model = Supplier
        fields = [
            'name', 'persian_name', 'supplier_type', 'contact_person',
            'phone_number', 'email', 'website', 'address', 'city', 'tax_id',
            'payment_terms', 'credit_limit', 'is_preferred', 'notes'
        ]


class POSTransactionLineItemSerializer(serializers.ModelSerializer):
    """
    Serializer for POS transaction line items.
    """
    jewelry_item_name = serializers.CharField(source='jewelry_item.name', read_only=True)
    jewelry_item_sku = serializers.CharField(source='jewelry_item.sku', read_only=True)
    
    class Meta:
        model = POSTransactionLineItem
        fields = [
            'id', 'jewelry_item', 'jewelry_item_name', 'jewelry_item_sku',
            'item_name', 'item_sku', 'quantity', 'unit_price', 'line_total',
            'gold_weight_grams', 'gold_karat', 'discount_amount', 'line_notes'
        ]
        read_only_fields = ['id', 'line_total']


class POSTransactionLineItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating POS transaction line items.
    """
    
    class Meta:
        model = POSTransactionLineItem
        fields = [
            'jewelry_item', 'item_name', 'quantity', 'unit_price', 
            'gold_weight_grams', 'gold_karat', 'discount_amount', 'line_notes'
        ]
    
    def validate_quantity(self, value):
        """
        Validate quantity is positive.
        """
        if value <= 0:
            raise serializers.ValidationError(_('Quantity must be positive.'))
        return value
    
    def validate_unit_price(self, value):
        """
        Validate unit price is positive.
        """
        if value <= 0:
            raise serializers.ValidationError(_('Unit price must be positive.'))
        return value


class POSTransactionListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for POS transaction lists.
    """
    customer_name = serializers.CharField(source='customer.full_persian_name', read_only=True)
    salesperson_name = serializers.CharField(source='created_by.full_persian_name', read_only=True)
    
    class Meta:
        model = POSTransaction
        fields = [
            'id', 'transaction_number', 'customer', 'customer_name',
            'salesperson_name', 'total_amount', 'payment_method',
            'status', 'transaction_date'
        ]


class POSTransactionSerializer(serializers.ModelSerializer):
    """
    Full serializer for POS transactions.
    """
    customer_name = serializers.CharField(source='customer.full_persian_name', read_only=True)
    salesperson_name = serializers.CharField(source='created_by.full_persian_name', read_only=True)
    line_items = POSTransactionLineItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = POSTransaction
        fields = [
            'id', 'transaction_id', 'transaction_number', 'customer', 'customer_name',
            'salesperson_name', 'transaction_date', 'transaction_type', 'status',
            'subtotal', 'tax_amount', 'discount_amount', 'total_amount',
            'payment_method', 'amount_paid', 'change_amount',
            'gold_price_18k_at_transaction', 'total_gold_weight_grams',
            'transaction_notes', 'line_items', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'transaction_id', 'transaction_number', 'customer_name', 
            'salesperson_name', 'total_amount', 'change_amount', 'created_at', 'updated_at'
        ]


class POSTransactionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating POS transactions with line items.
    """
    line_items = POSTransactionLineItemCreateSerializer(many=True, write_only=True)
    
    class Meta:
        model = POSTransaction
        fields = [
            'customer', 'transaction_type', 'subtotal', 'tax_amount', 'discount_amount',
            'payment_method', 'amount_paid', 'gold_price_18k_at_transaction',
            'transaction_notes', 'line_items'
        ]
    
    def validate_line_items(self, value):
        """
        Validate that transaction has at least one line item.
        """
        if not value:
            raise serializers.ValidationError(_('Transaction must have at least one line item.'))
        return value
    
    def create(self, validated_data):
        """
        Create POS transaction with line items.
        """
        line_items_data = validated_data.pop('line_items')
        
        with transaction.atomic():
            pos_transaction = POSTransaction.objects.create(**validated_data)
            
            for item_data in line_items_data:
                POSTransactionLineItem.objects.create(transaction=pos_transaction, **item_data)
            
            # Recalculate totals
            pos_transaction.calculate_totals()
            pos_transaction.save()
        
        return pos_transaction