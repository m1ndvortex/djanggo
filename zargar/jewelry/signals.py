"""
Signals for jewelry inventory management.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from .models import JewelryItem
from .barcode_models import BarcodeSettings
from .barcode_services import BarcodeGenerationService


@receiver(post_save, sender=JewelryItem)
def auto_generate_barcode(sender, instance, created, **kwargs):
    """
    Automatically generate barcode when jewelry item is created.
    """
    if not created:
        return
    
    try:
        # Check if auto-generation is enabled
        barcode_settings = BarcodeSettings.objects.first()
        if not barcode_settings or not barcode_settings.auto_generate_on_create:
            return
        
        # Skip if item already has a barcode
        if instance.barcode:
            return
        
        # Generate barcode
        service = BarcodeGenerationService()
        barcode_gen = service.generate_barcode_for_item(
            instance, 
            barcode_settings.default_barcode_type
        )
        
        # Log successful generation
        if hasattr(settings, 'LOGGING') and settings.DEBUG:
            print(f"Auto-generated barcode for {instance.name}: {barcode_gen.barcode_data}")
            
    except Exception as e:
        # Log error but don't fail the item creation
        if hasattr(settings, 'LOGGING'):
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to auto-generate barcode for {instance.name}: {e}")
        elif settings.DEBUG:
            print(f"Error auto-generating barcode for {instance.name}: {e}")


@receiver(post_save, sender=JewelryItem)
def update_barcode_on_sku_change(sender, instance, created, **kwargs):
    """
    Update barcode when SKU changes.
    """
    if created:
        return
    
    try:
        # Check if SKU changed
        if hasattr(instance, '_original_sku'):
            if instance._original_sku != instance.sku:
                # SKU changed, regenerate barcode
                service = BarcodeGenerationService()
                
                # Get current settings
                barcode_settings = BarcodeSettings.objects.first()
                barcode_type = barcode_settings.default_barcode_type if barcode_settings else 'qr_code'
                
                # Generate new barcode
                barcode_gen = service.generate_barcode_for_item(instance, barcode_type)
                
                if hasattr(settings, 'LOGGING') and settings.DEBUG:
                    print(f"Updated barcode for {instance.name} due to SKU change: {barcode_gen.barcode_data}")
    
    except Exception as e:
        if hasattr(settings, 'LOGGING'):
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to update barcode for {instance.name}: {e}")
        elif settings.DEBUG:
            print(f"Error updating barcode for {instance.name}: {e}")


# Store original SKU to detect changes
def store_original_sku(sender, instance, **kwargs):
    """Store original SKU to detect changes."""
    if instance.pk:
        try:
            original = JewelryItem.objects.get(pk=instance.pk)
            instance._original_sku = original.sku
        except JewelryItem.DoesNotExist:
            instance._original_sku = None
    else:
        instance._original_sku = None


# Connect the pre_save signal
from django.db.models.signals import pre_save
pre_save.connect(store_original_sku, sender=JewelryItem)