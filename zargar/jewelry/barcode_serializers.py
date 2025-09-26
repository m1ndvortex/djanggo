"""
Serializers for barcode and QR code models.
"""
from rest_framework import serializers
from .barcode_models import (
    BarcodeGeneration, BarcodeScanHistory, BarcodeTemplate, 
    BarcodeSettings, BarcodeType
)
from .models import JewelryItem


class BarcodeGenerationSerializer(serializers.ModelSerializer):
    """Serializer for BarcodeGeneration model."""
    
    jewelry_item_name = serializers.CharField(source='jewelry_item.name', read_only=True)
    jewelry_item_sku = serializers.CharField(source='jewelry_item.sku', read_only=True)
    barcode_type_display = serializers.CharField(source='get_barcode_type_display', read_only=True)
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = BarcodeGeneration
        fields = [
            'id', 'jewelry_item', 'jewelry_item_name', 'jewelry_item_sku',
            'barcode_type', 'barcode_type_display', 'barcode_data',
            'barcode_image', 'image_url', 'generation_date', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'generation_date', 'created_at', 'updated_at']
    
    def get_image_url(self, obj):
        """Get barcode image URL."""
        if obj.barcode_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.barcode_image.url)
            return obj.barcode_image.url
        return None


class BarcodeScanHistorySerializer(serializers.ModelSerializer):
    """Serializer for BarcodeScanHistory model."""
    
    jewelry_item_name = serializers.CharField(source='jewelry_item.name', read_only=True)
    jewelry_item_sku = serializers.CharField(source='jewelry_item.sku', read_only=True)
    scan_action_display = serializers.CharField(source='get_scan_action_display', read_only=True)
    barcode_generation_type = serializers.CharField(
        source='barcode_generation.barcode_type', read_only=True
    )
    
    class Meta:
        model = BarcodeScanHistory
        fields = [
            'id', 'jewelry_item', 'jewelry_item_name', 'jewelry_item_sku',
            'barcode_generation', 'barcode_generation_type', 'scanned_data',
            'scan_action', 'scan_action_display', 'scan_timestamp',
            'scanner_device', 'location', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'scan_timestamp', 'created_at']


class BarcodeTemplateSerializer(serializers.ModelSerializer):
    """Serializer for BarcodeTemplate model."""
    
    barcode_type_display = serializers.CharField(source='get_barcode_type_display', read_only=True)
    
    class Meta:
        model = BarcodeTemplate
        fields = [
            'id', 'name', 'barcode_type', 'barcode_type_display',
            'data_format', 'include_item_name', 'include_sku',
            'include_category', 'include_weight', 'include_karat',
            'include_price', 'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_name(self, value):
        """Validate template name uniqueness within tenant."""
        if self.instance:
            # Update case - exclude current instance
            if BarcodeTemplate.objects.exclude(pk=self.instance.pk).filter(name=value).exists():
                raise serializers.ValidationError("Template with this name already exists.")
        else:
            # Create case
            if BarcodeTemplate.objects.filter(name=value).exists():
                raise serializers.ValidationError("Template with this name already exists.")
        return value


class BarcodeSettingsSerializer(serializers.ModelSerializer):
    """Serializer for BarcodeSettings model."""
    
    default_barcode_type_display = serializers.CharField(
        source='get_default_barcode_type_display', read_only=True
    )
    
    class Meta:
        model = BarcodeSettings
        fields = [
            'id', 'auto_generate_on_create', 'default_barcode_type',
            'default_barcode_type_display', 'include_tenant_prefix',
            'tenant_prefix', 'qr_code_size', 'barcode_width',
            'barcode_height', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_tenant_prefix(self, value):
        """Validate tenant prefix format."""
        if value and not value.replace('0', '').replace('1', '').replace('2', '').replace('3', '').replace('4', '').replace('5', '').replace('6', '').replace('7', '').replace('8', '').replace('9', '').isalpha():
            if not all(c.isupper() or c.isdigit() for c in value):
                raise serializers.ValidationError("Prefix must contain only uppercase letters and numbers.")
        return value
    
    def validate_qr_code_size(self, value):
        """Validate QR code size."""
        if value < 50 or value > 1000:
            raise serializers.ValidationError("QR code size must be between 50 and 1000 pixels.")
        return value
    
    def validate_barcode_width(self, value):
        """Validate barcode width."""
        if value < 100 or value > 1000:
            raise serializers.ValidationError("Barcode width must be between 100 and 1000 pixels.")
        return value
    
    def validate_barcode_height(self, value):
        """Validate barcode height."""
        if value < 50 or value > 500:
            raise serializers.ValidationError("Barcode height must be between 50 and 500 pixels.")
        return value


class BarcodeGenerationRequestSerializer(serializers.Serializer):
    """Serializer for barcode generation requests."""
    
    item_id = serializers.IntegerField()
    barcode_type = serializers.ChoiceField(
        choices=BarcodeType.choices,
        default=BarcodeType.QR_CODE
    )
    template_id = serializers.IntegerField(required=False)
    
    def validate_item_id(self, value):
        """Validate jewelry item exists."""
        try:
            JewelryItem.objects.get(id=value)
        except JewelryItem.DoesNotExist:
            raise serializers.ValidationError("Jewelry item not found.")
        return value
    
    def validate_template_id(self, value):
        """Validate template exists if provided."""
        if value:
            try:
                BarcodeTemplate.objects.get(id=value)
            except BarcodeTemplate.DoesNotExist:
                raise serializers.ValidationError("Template not found.")
        return value


class BulkBarcodeGenerationRequestSerializer(serializers.Serializer):
    """Serializer for bulk barcode generation requests."""
    
    item_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100
    )
    barcode_type = serializers.ChoiceField(
        choices=BarcodeType.choices,
        default=BarcodeType.QR_CODE
    )
    
    def validate_item_ids(self, value):
        """Validate all jewelry items exist."""
        existing_ids = set(JewelryItem.objects.filter(id__in=value).values_list('id', flat=True))
        missing_ids = set(value) - existing_ids
        
        if missing_ids:
            raise serializers.ValidationError(
                f"Jewelry items not found: {list(missing_ids)}"
            )
        
        return value


class BarcodeScanRequestSerializer(serializers.Serializer):
    """Serializer for barcode scan requests."""
    
    scanned_data = serializers.CharField(max_length=500)
    scan_action = serializers.ChoiceField(
        choices=BarcodeScanHistory.SCAN_ACTIONS,
        default='lookup'
    )
    scanner_device = serializers.CharField(max_length=100, required=False, allow_blank=True)
    location = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class BarcodeScanResponseSerializer(serializers.Serializer):
    """Serializer for barcode scan responses."""
    
    success = serializers.BooleanField()
    jewelry_item = serializers.DictField(required=False)
    barcode_generation = serializers.DictField(required=False)
    scan_history_id = serializers.IntegerField(required=False)
    error = serializers.CharField(required=False)


class BarcodeStatisticsSerializer(serializers.Serializer):
    """Serializer for barcode statistics."""
    
    total_scans = serializers.IntegerField()
    scans_by_action = serializers.DictField()
    recent_scans = BarcodeScanHistorySerializer(many=True)
    most_scanned_items = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )