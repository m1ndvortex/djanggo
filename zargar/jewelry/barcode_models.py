"""
Barcode and QR code models for jewelry items.
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from zargar.core.models import TenantAwareModel
from .models import JewelryItem


class BarcodeType(models.TextChoices):
    """Barcode type choices."""
    EAN13 = 'ean13', _('EAN-13')
    CODE128 = 'code128', _('Code 128')
    QR_CODE = 'qr_code', _('QR Code')
    CUSTOM = 'custom', _('Custom')


class BarcodeGeneration(TenantAwareModel):
    """
    Model to track barcode generation for jewelry items.
    """
    jewelry_item = models.ForeignKey(
        JewelryItem,
        on_delete=models.CASCADE,
        related_name='barcode_generations',
        verbose_name=_('Jewelry Item')
    )
    barcode_type = models.CharField(
        max_length=20,
        choices=BarcodeType.choices,
        default=BarcodeType.QR_CODE,
        verbose_name=_('Barcode Type')
    )
    barcode_data = models.CharField(
        max_length=500,
        verbose_name=_('Barcode Data'),
        help_text=_('The data encoded in the barcode')
    )
    barcode_image = models.FileField(
        upload_to='barcodes/%Y/%m/',
        blank=True,
        null=True,
        verbose_name=_('Barcode Image')
    )
    generation_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Generation Date')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    
    class Meta:
        verbose_name = _('Barcode Generation')
        verbose_name_plural = _('Barcode Generations')
        ordering = ['-generation_date']
        indexes = [
            models.Index(fields=['jewelry_item', 'is_active']),
            models.Index(fields=['barcode_type']),
            models.Index(fields=['generation_date']),
        ]
    
    def __str__(self):
        return f"{self.jewelry_item.name} - {self.get_barcode_type_display()}"


class BarcodeScanHistory(TenantAwareModel):
    """
    Model to track barcode scanning history.
    """
    SCAN_ACTIONS = [
        ('inventory_check', _('Inventory Check')),
        ('sale', _('Sale')),
        ('return', _('Return')),
        ('transfer', _('Transfer')),
        ('audit', _('Audit')),
        ('lookup', _('Lookup')),
        ('other', _('Other')),
    ]
    
    jewelry_item = models.ForeignKey(
        JewelryItem,
        on_delete=models.CASCADE,
        related_name='scan_history',
        verbose_name=_('Jewelry Item')
    )
    barcode_generation = models.ForeignKey(
        BarcodeGeneration,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Barcode Generation')
    )
    scanned_data = models.CharField(
        max_length=500,
        verbose_name=_('Scanned Data')
    )
    scan_action = models.CharField(
        max_length=20,
        choices=SCAN_ACTIONS,
        default='lookup',
        verbose_name=_('Scan Action')
    )
    scan_timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Scan Timestamp')
    )
    scanner_device = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Scanner Device'),
        help_text=_('Device used for scanning (e.g., mobile app, handheld scanner)')
    )
    location = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Scan Location'),
        help_text=_('Physical location where scan occurred')
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Scan Notes')
    )
    
    class Meta:
        verbose_name = _('Barcode Scan History')
        verbose_name_plural = _('Barcode Scan Histories')
        ordering = ['-scan_timestamp']
        indexes = [
            models.Index(fields=['jewelry_item', 'scan_timestamp']),
            models.Index(fields=['scan_action']),
            models.Index(fields=['scan_timestamp']),
        ]
    
    def __str__(self):
        return f"{self.jewelry_item.name} - {self.get_scan_action_display()} ({self.scan_timestamp})"


class BarcodeTemplate(TenantAwareModel):
    """
    Model for barcode templates and configurations.
    """
    name = models.CharField(
        max_length=100,
        verbose_name=_('Template Name')
    )
    barcode_type = models.CharField(
        max_length=20,
        choices=BarcodeType.choices,
        verbose_name=_('Barcode Type')
    )
    data_format = models.CharField(
        max_length=200,
        verbose_name=_('Data Format'),
        help_text=_('Template for barcode data (e.g., {sku}-{category}-{date})')
    )
    include_item_name = models.BooleanField(
        default=True,
        verbose_name=_('Include Item Name')
    )
    include_sku = models.BooleanField(
        default=True,
        verbose_name=_('Include SKU')
    )
    include_category = models.BooleanField(
        default=False,
        verbose_name=_('Include Category')
    )
    include_weight = models.BooleanField(
        default=False,
        verbose_name=_('Include Weight')
    )
    include_karat = models.BooleanField(
        default=False,
        verbose_name=_('Include Karat')
    )
    include_price = models.BooleanField(
        default=False,
        verbose_name=_('Include Price')
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name=_('Is Default Template')
    )
    
    class Meta:
        verbose_name = _('Barcode Template')
        verbose_name_plural = _('Barcode Templates')
        unique_together = ['name']  # Unique within tenant
    
    def __str__(self):
        return f"{self.name} ({self.get_barcode_type_display()})"
    
    def save(self, *args, **kwargs):
        """Ensure only one default template per barcode type."""
        if self.is_default:
            # Remove default flag from other templates of the same type
            BarcodeTemplate.objects.filter(
                barcode_type=self.barcode_type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        
        super().save(*args, **kwargs)


class BarcodeSettings(TenantAwareModel):
    """
    Model for tenant-specific barcode settings.
    """
    auto_generate_on_create = models.BooleanField(
        default=True,
        verbose_name=_('Auto Generate on Item Create')
    )
    default_barcode_type = models.CharField(
        max_length=20,
        choices=BarcodeType.choices,
        default=BarcodeType.QR_CODE,
        verbose_name=_('Default Barcode Type')
    )
    include_tenant_prefix = models.BooleanField(
        default=True,
        verbose_name=_('Include Tenant Prefix')
    )
    tenant_prefix = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Tenant Prefix'),
        validators=[RegexValidator(
            regex=r'^[A-Z0-9]*$',
            message=_('Prefix must contain only uppercase letters and numbers')
        )]
    )
    qr_code_size = models.PositiveIntegerField(
        default=200,
        verbose_name=_('QR Code Size (pixels)')
    )
    barcode_width = models.PositiveIntegerField(
        default=300,
        verbose_name=_('Barcode Width (pixels)')
    )
    barcode_height = models.PositiveIntegerField(
        default=100,
        verbose_name=_('Barcode Height (pixels)')
    )
    
    class Meta:
        verbose_name = _('Barcode Settings')
        verbose_name_plural = _('Barcode Settings')
    
    def __str__(self):
        return f"Barcode Settings"