"""
Django admin configuration for barcode models.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .barcode_models import (
    BarcodeGeneration, BarcodeScanHistory, BarcodeTemplate, 
    BarcodeSettings, BarcodeType
)


@admin.register(BarcodeGeneration)
class BarcodeGenerationAdmin(admin.ModelAdmin):
    """Admin for BarcodeGeneration model."""
    
    list_display = [
        'jewelry_item_name', 'jewelry_item_sku', 'barcode_type', 
        'barcode_data_short', 'generation_date', 'is_active', 'image_preview'
    ]
    list_filter = ['barcode_type', 'is_active', 'generation_date']
    search_fields = [
        'jewelry_item__name', 'jewelry_item__sku', 'barcode_data'
    ]
    readonly_fields = ['generation_date', 'image_preview', 'barcode_data_display']
    
    fieldsets = (
        ('Jewelry Item', {
            'fields': ('jewelry_item',)
        }),
        ('Barcode Information', {
            'fields': ('barcode_type', 'barcode_data_display', 'is_active')
        }),
        ('Generated Image', {
            'fields': ('barcode_image', 'image_preview')
        }),
        ('Metadata', {
            'fields': ('generation_date',),
            'classes': ('collapse',)
        })
    )
    
    def jewelry_item_name(self, obj):
        """Display jewelry item name."""
        return obj.jewelry_item.name
    jewelry_item_name.short_description = 'Item Name'
    
    def jewelry_item_sku(self, obj):
        """Display jewelry item SKU."""
        return obj.jewelry_item.sku
    jewelry_item_sku.short_description = 'SKU'
    
    def barcode_data_short(self, obj):
        """Display shortened barcode data."""
        if len(obj.barcode_data) > 50:
            return f"{obj.barcode_data[:50]}..."
        return obj.barcode_data
    barcode_data_short.short_description = 'Barcode Data'
    
    def barcode_data_display(self, obj):
        """Display full barcode data in readonly field."""
        return obj.barcode_data
    barcode_data_display.short_description = 'Barcode Data'
    
    def image_preview(self, obj):
        """Display barcode image preview."""
        if obj.barcode_image:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px;" />',
                obj.barcode_image.url
            )
        return "No image"
    image_preview.short_description = 'Image Preview'


@admin.register(BarcodeScanHistory)
class BarcodeScanHistoryAdmin(admin.ModelAdmin):
    """Admin for BarcodeScanHistory model."""
    
    list_display = [
        'jewelry_item_name', 'jewelry_item_sku', 'scan_action', 
        'scan_timestamp', 'scanner_device', 'location'
    ]
    list_filter = ['scan_action', 'scan_timestamp', 'scanner_device']
    search_fields = [
        'jewelry_item__name', 'jewelry_item__sku', 'scanned_data',
        'scanner_device', 'location', 'notes'
    ]
    readonly_fields = ['scan_timestamp', 'scanned_data_display']
    date_hierarchy = 'scan_timestamp'
    
    fieldsets = (
        ('Jewelry Item', {
            'fields': ('jewelry_item', 'barcode_generation')
        }),
        ('Scan Information', {
            'fields': ('scanned_data_display', 'scan_action', 'scan_timestamp')
        }),
        ('Device and Location', {
            'fields': ('scanner_device', 'location')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )
    
    def jewelry_item_name(self, obj):
        """Display jewelry item name."""
        return obj.jewelry_item.name
    jewelry_item_name.short_description = 'Item Name'
    
    def jewelry_item_sku(self, obj):
        """Display jewelry item SKU."""
        return obj.jewelry_item.sku
    jewelry_item_sku.short_description = 'SKU'
    
    def scanned_data_display(self, obj):
        """Display scanned data in readonly field."""
        return obj.scanned_data
    scanned_data_display.short_description = 'Scanned Data'


@admin.register(BarcodeTemplate)
class BarcodeTemplateAdmin(admin.ModelAdmin):
    """Admin for BarcodeTemplate model."""
    
    list_display = [
        'name', 'barcode_type', 'data_format', 'is_default',
        'includes_summary'
    ]
    list_filter = ['barcode_type', 'is_default']
    search_fields = ['name', 'data_format']
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'barcode_type', 'data_format', 'is_default')
        }),
        ('Include Fields', {
            'fields': (
                'include_item_name', 'include_sku', 'include_category',
                'include_weight', 'include_karat', 'include_price'
            )
        })
    )
    
    def includes_summary(self, obj):
        """Display summary of included fields."""
        includes = []
        if obj.include_item_name:
            includes.append('Name')
        if obj.include_sku:
            includes.append('SKU')
        if obj.include_category:
            includes.append('Category')
        if obj.include_weight:
            includes.append('Weight')
        if obj.include_karat:
            includes.append('Karat')
        if obj.include_price:
            includes.append('Price')
        
        return ', '.join(includes) if includes else 'None'
    includes_summary.short_description = 'Included Fields'


@admin.register(BarcodeSettings)
class BarcodeSettingsAdmin(admin.ModelAdmin):
    """Admin for BarcodeSettings model."""
    
    list_display = [
        'auto_generate_on_create', 'default_barcode_type',
        'include_tenant_prefix', 'tenant_prefix'
    ]
    
    fieldsets = (
        ('Generation Settings', {
            'fields': (
                'auto_generate_on_create', 'default_barcode_type',
                'include_tenant_prefix', 'tenant_prefix'
            )
        }),
        ('Image Dimensions', {
            'fields': ('qr_code_size', 'barcode_width', 'barcode_height')
        })
    )
    
    def has_add_permission(self, request):
        """Only allow one settings instance per tenant."""
        return not BarcodeSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Don't allow deletion of settings."""
        return False


# Custom admin actions
def regenerate_barcodes(modeladmin, request, queryset):
    """Admin action to regenerate barcodes for selected items."""
    from .barcode_services import BarcodeGenerationService
    
    service = BarcodeGenerationService()
    count = 0
    
    for jewelry_item in queryset:
        try:
            service.generate_barcode_for_item(jewelry_item)
            count += 1
        except Exception:
            continue
    
    modeladmin.message_user(
        request,
        f"Successfully regenerated barcodes for {count} items."
    )

regenerate_barcodes.short_description = "Regenerate barcodes for selected items"


# Add the action to JewelryItem admin if it exists
try:
    from .admin import JewelryItemAdmin
    if hasattr(JewelryItemAdmin, 'actions'):
        JewelryItemAdmin.actions.append(regenerate_barcodes)
    else:
        JewelryItemAdmin.actions = [regenerate_barcodes]
except ImportError:
    pass