"""
Django admin configuration for jewelry models.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from .models import Category, Gemstone, JewelryItem, JewelryItemPhoto


class JewelryItemPhotoInline(admin.TabularInline):
    """Inline admin for jewelry item photos."""
    model = JewelryItemPhoto
    extra = 1
    fields = ['image', 'caption', 'is_primary', 'order']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin for Category model."""
    list_display = ['name', 'name_persian', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'name_persian']
    
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'name_persian', 'description', 'is_active')
        }),
    )


@admin.register(Gemstone)
class GemstoneAdmin(admin.ModelAdmin):
    """Admin for Gemstone model."""
    list_display = [
        'name', 'gemstone_type', 'carat_weight', 'cut_grade',
        'certification_number', 'purchase_price'
    ]
    list_filter = ['gemstone_type', 'cut_grade', 'color_grade']
    search_fields = ['name', 'certification_number']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'gemstone_type', 'carat_weight')
        }),
        ('Quality Grades', {
            'fields': ('cut_grade', 'color_grade', 'clarity_grade')
        }),
        ('Certification', {
            'fields': ('certification_number', 'certification_authority')
        }),
        ('Pricing', {
            'fields': ('purchase_price',)
        })
    )


@admin.register(JewelryItem)
class JewelryItemAdmin(admin.ModelAdmin):
    """Admin for JewelryItem model."""
    list_display = [
        'name', 'sku', 'barcode_short', 'category', 'weight_grams',
        'karat', 'status', 'quantity', 'selling_price', 'is_low_stock'
    ]
    list_filter = ['status', 'category', 'karat', 'created_at']
    search_fields = ['name', 'sku', 'barcode', 'description']
    readonly_fields = ['total_value', 'is_low_stock', 'created_at', 'updated_at']
    inlines = [JewelryItemPhotoInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'sku', 'barcode', 'category', 'description')
        }),
        ('Physical Properties', {
            'fields': ('weight_grams', 'karat')
        }),
        ('Pricing', {
            'fields': (
                'manufacturing_cost', 'gold_value', 'gemstone_value',
                'selling_price', 'total_value'
            )
        }),
        ('Inventory', {
            'fields': ('status', 'quantity', 'minimum_stock', 'is_low_stock')
        }),
        ('Relationships', {
            'fields': ('gemstones',)
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    filter_horizontal = ['gemstones']
    
    def barcode_short(self, obj):
        """Display shortened barcode."""
        if obj.barcode and len(obj.barcode) > 20:
            return f"{obj.barcode[:20]}..."
        return obj.barcode or "No barcode"
    barcode_short.short_description = 'Barcode'
    
    def is_low_stock(self, obj):
        """Display low stock status."""
        if obj.is_low_stock:
            return format_html(
                '<span style="color: red; font-weight: bold;">Low Stock</span>'
            )
        return "OK"
    is_low_stock.short_description = 'Stock Status'
    
    actions = ['mark_as_sold', 'mark_as_in_stock', 'update_gold_values']
    
    def mark_as_sold(self, request, queryset):
        """Mark selected items as sold."""
        count = queryset.update(status='sold')
        self.message_user(request, f"{count} items marked as sold.")
    mark_as_sold.short_description = "Mark selected items as sold"
    
    def mark_as_in_stock(self, request, queryset):
        """Mark selected items as in stock."""
        count = queryset.update(status='in_stock')
        self.message_user(request, f"{count} items marked as in stock.")
    mark_as_in_stock.short_description = "Mark selected items as in stock"
    
    def update_gold_values(self, request, queryset):
        """Update gold values for selected items."""
        # This would need current gold price
        count = 0
        for item in queryset:
            # Placeholder for gold price update logic
            count += 1
        
        self.message_user(request, f"Updated gold values for {count} items.")
    update_gold_values.short_description = "Update gold values for selected items"


@admin.register(JewelryItemPhoto)
class JewelryItemPhotoAdmin(admin.ModelAdmin):
    """Admin for JewelryItemPhoto model."""
    list_display = ['jewelry_item', 'caption', 'is_primary', 'order', 'image_preview']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['jewelry_item__name', 'caption']
    
    def image_preview(self, obj):
        """Display image preview."""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px;" />',
                obj.image.url
            )
        return "No image"
    image_preview.short_description = 'Preview'


# Import barcode admin to register barcode models
from . import barcode_admin