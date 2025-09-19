"""
Jewelry inventory models for zargar project.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from zargar.core.models import TenantAwareModel


class Category(TenantAwareModel):
    """
    Jewelry category model (e.g., Rings, Necklaces, Bracelets).
    """
    name = models.CharField(
        max_length=100,
        verbose_name=_('Category Name')
    )
    name_persian = models.CharField(
        max_length=100,
        verbose_name=_('Persian Category Name')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    
    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        unique_together = ['name', 'created_at']  # Prevent duplicates within tenant
    
    def __str__(self):
        return self.name_persian or self.name


class Gemstone(TenantAwareModel):
    """
    Gemstone model for tracking precious stones.
    """
    GEMSTONE_TYPES = [
        ('diamond', _('Diamond')),
        ('emerald', _('Emerald')),
        ('ruby', _('Ruby')),
        ('sapphire', _('Sapphire')),
        ('pearl', _('Pearl')),
        ('other', _('Other')),
    ]
    
    CUT_GRADES = [
        ('excellent', _('Excellent')),
        ('very_good', _('Very Good')),
        ('good', _('Good')),
        ('fair', _('Fair')),
        ('poor', _('Poor')),
    ]
    
    name = models.CharField(
        max_length=100,
        verbose_name=_('Gemstone Name')
    )
    gemstone_type = models.CharField(
        max_length=20,
        choices=GEMSTONE_TYPES,
        verbose_name=_('Gemstone Type')
    )
    carat_weight = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
        verbose_name=_('Carat Weight')
    )
    cut_grade = models.CharField(
        max_length=20,
        choices=CUT_GRADES,
        blank=True,
        verbose_name=_('Cut Grade')
    )
    color_grade = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Color Grade')
    )
    clarity_grade = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Clarity Grade')
    )
    certification_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Certification Number')
    )
    certification_authority = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Certification Authority')
    )
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Purchase Price (Toman)')
    )
    
    class Meta:
        verbose_name = _('Gemstone')
        verbose_name_plural = _('Gemstones')
    
    def __str__(self):
        return f"{self.name} ({self.carat_weight} carat)"


class JewelryItem(TenantAwareModel):
    """
    Main jewelry item model with comprehensive tracking.
    """
    STATUS_CHOICES = [
        ('in_stock', _('In Stock')),
        ('sold', _('Sold')),
        ('reserved', _('Reserved')),
        ('repair', _('Under Repair')),
        ('consignment', _('Consignment')),
    ]
    
    # Basic information
    name = models.CharField(
        max_length=200,
        verbose_name=_('Item Name')
    )
    sku = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('SKU'),
        help_text=_('Stock Keeping Unit - must be unique')
    )
    barcode = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        verbose_name=_('Barcode')
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        verbose_name=_('Category')
    )
    
    # Physical properties
    weight_grams = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
        verbose_name=_('Weight (Grams)')
    )
    karat = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(24)],
        verbose_name=_('Gold Karat (عیار)')
    )
    
    # Pricing
    manufacturing_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Manufacturing Cost (اجرت) - Toman')
    )
    gold_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Gold Value (Toman)')
    )
    gemstone_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Gemstone Value (Toman)')
    )
    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Selling Price (Toman)')
    )
    
    # Status and inventory
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_stock',
        verbose_name=_('Status')
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name=_('Quantity')
    )
    minimum_stock = models.PositiveIntegerField(
        default=1,
        verbose_name=_('Minimum Stock Level')
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
    
    # Relationships
    gemstones = models.ManyToManyField(
        Gemstone,
        blank=True,
        verbose_name=_('Gemstones')
    )
    
    class Meta:
        verbose_name = _('Jewelry Item')
        verbose_name_plural = _('Jewelry Items')
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['barcode']),
            models.Index(fields=['status']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    @property
    def total_value(self):
        """Calculate total item value."""
        gold_val = self.gold_value or 0
        gem_val = self.gemstone_value or 0
        manufacturing = self.manufacturing_cost or 0
        return gold_val + gem_val + manufacturing
    
    @property
    def is_low_stock(self):
        """Check if item is below minimum stock level."""
        return self.quantity <= self.minimum_stock
    
    def calculate_gold_value(self, gold_price_per_gram):
        """Calculate gold value based on current market price."""
        if self.weight_grams and self.karat:
            # Calculate pure gold weight
            pure_gold_weight = (self.weight_grams * self.karat) / 24
            return pure_gold_weight * gold_price_per_gram
        return 0
    
    def update_gold_value(self, gold_price_per_gram):
        """Update gold value and save."""
        self.gold_value = self.calculate_gold_value(gold_price_per_gram)
        self.save(update_fields=['gold_value', 'updated_at'])


class JewelryItemPhoto(TenantAwareModel):
    """
    Photo model for jewelry items.
    """
    jewelry_item = models.ForeignKey(
        JewelryItem,
        on_delete=models.CASCADE,
        related_name='photos',
        verbose_name=_('Jewelry Item')
    )
    image = models.FileField(
        upload_to='jewelry_photos/%Y/%m/',
        verbose_name=_('Image')
    )
    caption = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Caption')
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name=_('Is Primary Photo')
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Display Order')
    )
    
    class Meta:
        verbose_name = _('Jewelry Item Photo')
        verbose_name_plural = _('Jewelry Item Photos')
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"Photo for {self.jewelry_item.name}"
    
    def save(self, *args, **kwargs):
        """Ensure only one primary photo per item."""
        if self.is_primary:
            # Remove primary flag from other photos of the same item
            JewelryItemPhoto.objects.filter(
                jewelry_item=self.jewelry_item,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        
        super().save(*args, **kwargs)