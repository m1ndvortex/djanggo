"""
Barcode and QR code generation and scanning services.
"""
import io
import json
from datetime import datetime

from django.core.files.base import ContentFile
from django.utils import timezone
from django.db import transaction
from django.apps import apps

# Try to import QR code libraries
try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False


class BarcodeGenerationService:
    """Service for generating barcodes and QR codes for jewelry items."""
    
    def __init__(self):
        self.default_qr_size = 200
    
    def generate_barcode_data(self, jewelry_item, template=None):
        """Generate barcode data based on jewelry item and template."""
        # Default format: SKU-CATEGORY-TIMESTAMP
        timestamp = datetime.now().strftime('%Y%m%d')
        category_code = jewelry_item.category.name[:3].upper() if jewelry_item.category else 'GEN'
        prefix = 'ZRG'
        
        return f"{prefix}-{jewelry_item.sku}-{category_code}-{timestamp}"
    
    def generate_qr_code(self, jewelry_item, template=None):
        """Generate QR code for jewelry item."""
        barcode_data = self.generate_barcode_data(jewelry_item, template)
        
        if not QR_AVAILABLE:
            return barcode_data, None
        
        qr_data = {
            'type': 'jewelry_item',
            'sku': jewelry_item.sku,
            'name': jewelry_item.name,
            'item_id': jewelry_item.id,
            'barcode': barcode_data,
            'generated_at': timezone.now().isoformat()
        }
        
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(json.dumps(qr_data))
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            img_io = io.BytesIO()
            img.save(img_io, format='PNG')
            img_io.seek(0)
            
            filename = f"qr_{jewelry_item.sku}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.png"
            content_file = ContentFile(img_io.getvalue(), name=filename)
            
            return json.dumps(qr_data), content_file
            
        except Exception:
            return json.dumps(qr_data), None
    
    def generate_barcode_for_item(self, jewelry_item, barcode_type=None, template=None):
        """Generate and save barcode for jewelry item."""
        # Get models using lazy import
        BarcodeGeneration = apps.get_model('jewelry', 'BarcodeGeneration')
        
        if not barcode_type:
            barcode_type = 'qr_code'
        
        with transaction.atomic():
            # Deactivate previous barcodes
            BarcodeGeneration.objects.filter(
                jewelry_item=jewelry_item,
                is_active=True
            ).update(is_active=False)
            
            if barcode_type == 'qr_code':
                barcode_data, image_file = self.generate_qr_code(jewelry_item, template)
            else:
                barcode_data = self.generate_barcode_data(jewelry_item, template)
                image_file = None
            
            # Create barcode generation record
            barcode_gen = BarcodeGeneration.objects.create(
                jewelry_item=jewelry_item,
                barcode_type=barcode_type,
                barcode_data=barcode_data,
                is_active=True
            )
            
            if image_file:
                barcode_gen.barcode_image.save(image_file.name, image_file, save=True)
            
            # Update jewelry item barcode field
            simple_data = self.generate_barcode_data(jewelry_item, template)
            jewelry_item.barcode = simple_data
            jewelry_item.save(update_fields=['barcode', 'updated_at'])
            
            return barcode_gen


class BarcodeScanningService:
    """Service for handling barcode scanning and tracking."""
    
    def scan_barcode(self, scanned_data, scan_action='lookup', scanner_device='', location='', notes=''):
        """Process scanned barcode data and record scan history."""
        # Get models using lazy import
        JewelryItem = apps.get_model('jewelry', 'JewelryItem')
        BarcodeGeneration = apps.get_model('jewelry', 'BarcodeGeneration')
        BarcodeScanHistory = apps.get_model('jewelry', 'BarcodeScanHistory')
        
        result = {
            'success': False,
            'jewelry_item': None,
            'barcode_generation': None,
            'scan_history': None,
            'error': None
        }
        
        try:
            # Try to parse as JSON (QR code data)
            if scanned_data.startswith('{'):
                qr_data = json.loads(scanned_data)
                if qr_data.get('type') == 'jewelry_item':
                    jewelry_item = self._find_item_by_qr_data(qr_data)
                else:
                    jewelry_item = None
            else:
                jewelry_item = self._find_item_by_barcode(scanned_data)
            
            if not jewelry_item:
                result['error'] = 'Jewelry item not found for scanned barcode'
                return result
            
            # Find associated barcode generation
            barcode_generation = BarcodeGeneration.objects.filter(
                jewelry_item=jewelry_item,
                is_active=True
            ).first()
            
            # Record scan history
            scan_history = BarcodeScanHistory.objects.create(
                jewelry_item=jewelry_item,
                barcode_generation=barcode_generation,
                scanned_data=scanned_data,
                scan_action=scan_action,
                scanner_device=scanner_device,
                location=location,
                notes=notes
            )
            
            result.update({
                'success': True,
                'jewelry_item': jewelry_item,
                'barcode_generation': barcode_generation,
                'scan_history': scan_history
            })
            
        except Exception as e:
            result['error'] = f'Error processing scan: {str(e)}'
        
        return result
    
    def _find_item_by_qr_data(self, qr_data):
        """Find jewelry item by QR code data."""
        JewelryItem = apps.get_model('jewelry', 'JewelryItem')
        
        try:
            if 'item_id' in qr_data:
                return JewelryItem.objects.get(id=qr_data['item_id'])
            if 'sku' in qr_data:
                return JewelryItem.objects.get(sku=qr_data['sku'])
        except JewelryItem.DoesNotExist:
            pass
        
        return None
    
    def _find_item_by_barcode(self, barcode_data):
        """Find jewelry item by simple barcode data."""
        JewelryItem = apps.get_model('jewelry', 'JewelryItem')
        
        try:
            return JewelryItem.objects.get(barcode=barcode_data)
        except JewelryItem.DoesNotExist:
            try:
                return JewelryItem.objects.get(sku=barcode_data)
            except JewelryItem.DoesNotExist:
                pass
        
        return None
    
    def get_scan_history(self, jewelry_item, limit=50):
        """Get scan history for a jewelry item."""
        BarcodeScanHistory = apps.get_model('jewelry', 'BarcodeScanHistory')
        
        return list(BarcodeScanHistory.objects.filter(
            jewelry_item=jewelry_item
        ).order_by('-scan_timestamp')[:limit])
    
    def get_scan_statistics(self, jewelry_item=None):
        """Get scanning statistics."""
        BarcodeScanHistory = apps.get_model('jewelry', 'BarcodeScanHistory')
        
        queryset = BarcodeScanHistory.objects.all()
        if jewelry_item:
            queryset = queryset.filter(jewelry_item=jewelry_item)
        
        return {
            'total_scans': queryset.count(),
            'recent_scans': list(queryset.order_by('-scan_timestamp')[:10])
        }


class BarcodeTemplateService:
    """Service for managing barcode templates."""
    
    def create_default_templates(self):
        """Create default barcode templates for a tenant."""
        BarcodeTemplate = apps.get_model('jewelry', 'BarcodeTemplate')
        
        template_data = {
            'name': 'Standard QR Code',
            'barcode_type': 'qr_code',
            'data_format': '{sku}-{category}-{date}',
            'include_sku': True,
            'include_category': True,
            'is_default': True
        }
        
        template, created = BarcodeTemplate.objects.get_or_create(
            name=template_data['name'],
            defaults=template_data
        )
        
        return [template] if created else []


class BarcodeSettingsService:
    """Service for managing barcode settings."""
    
    def get_or_create_settings(self):
        """Get or create barcode settings for tenant."""
        BarcodeSettings = apps.get_model('jewelry', 'BarcodeSettings')
        
        settings_obj, created = BarcodeSettings.objects.get_or_create(
            defaults={
                'auto_generate_on_create': True,
                'default_barcode_type': 'qr_code',
                'include_tenant_prefix': True,
                'tenant_prefix': 'ZRG',
                'qr_code_size': 200,
                'barcode_width': 300,
                'barcode_height': 100
            }
        )
        return settings_obj