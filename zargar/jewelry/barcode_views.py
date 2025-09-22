"""
Barcode and QR code API views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.generic import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin

from zargar.core.permissions import TenantPermission
from .models import JewelryItem
from .barcode_models import (
    BarcodeGeneration, BarcodeScanHistory, BarcodeTemplate, 
    BarcodeSettings, BarcodeType
)
from .barcode_services import (
    BarcodeGenerationService, BarcodeScanningService,
    BarcodeTemplateService, BarcodeSettingsService
)
# from .serializers import JewelryItemSerializer  # Will be created later


class BarcodeGenerationViewSet(viewsets.ModelViewSet):
    """ViewSet for barcode generation management."""
    
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_queryset(self):
        return BarcodeGeneration.objects.filter(
            jewelry_item__created_by__tenant=self.request.tenant
        ).select_related('jewelry_item')
    
    @action(detail=False, methods=['post'])
    def generate_for_item(self, request):
        """Generate barcode for specific jewelry item."""
        item_id = request.data.get('item_id')
        barcode_type = request.data.get('barcode_type', BarcodeType.QR_CODE)
        template_id = request.data.get('template_id')
        
        if not item_id:
            return Response(
                {'error': 'item_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            jewelry_item = JewelryItem.objects.get(id=item_id)
        except JewelryItem.DoesNotExist:
            return Response(
                {'error': 'Jewelry item not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get template if specified
        template = None
        if template_id:
            try:
                template = BarcodeTemplate.objects.get(id=template_id)
            except BarcodeTemplate.DoesNotExist:
                return Response(
                    {'error': 'Template not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Generate barcode
        service = BarcodeGenerationService()
        try:
            barcode_gen = service.generate_barcode_for_item(
                jewelry_item, barcode_type, template
            )
            
            return Response({
                'success': True,
                'barcode_generation_id': barcode_gen.id,
                'barcode_data': barcode_gen.barcode_data,
                'barcode_type': barcode_gen.barcode_type,
                'image_url': barcode_gen.barcode_image.url if barcode_gen.barcode_image else None,
                'jewelry_item': {
                    'id': jewelry_item.id,
                    'name': jewelry_item.name,
                    'sku': jewelry_item.sku
                }
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to generate barcode: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def bulk_generate(self, request):
        """Generate barcodes for multiple jewelry items."""
        item_ids = request.data.get('item_ids', [])
        barcode_type = request.data.get('barcode_type', BarcodeType.QR_CODE)
        
        if not item_ids:
            return Response(
                {'error': 'item_ids is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        jewelry_items = JewelryItem.objects.filter(id__in=item_ids)
        
        if not jewelry_items.exists():
            return Response(
                {'error': 'No jewelry items found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generate barcodes
        service = BarcodeGenerationService()
        try:
            generated_barcodes = service.bulk_generate_barcodes(
                list(jewelry_items), barcode_type
            )
            
            results = []
            for barcode_gen in generated_barcodes:
                results.append({
                    'barcode_generation_id': barcode_gen.id,
                    'jewelry_item_id': barcode_gen.jewelry_item.id,
                    'jewelry_item_name': barcode_gen.jewelry_item.name,
                    'barcode_data': barcode_gen.barcode_data,
                    'image_url': barcode_gen.barcode_image.url if barcode_gen.barcode_image else None
                })
            
            return Response({
                'success': True,
                'generated_count': len(generated_barcodes),
                'results': results
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to generate barcodes: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def download_image(self, request, pk=None):
        """Download barcode image."""
        barcode_gen = self.get_object()
        
        if not barcode_gen.barcode_image:
            return Response(
                {'error': 'No image available'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            response = HttpResponse(
                barcode_gen.barcode_image.read(), 
                content_type='image/png'
            )
            response['Content-Disposition'] = f'attachment; filename="{barcode_gen.barcode_image.name}"'
            return response
        except Exception as e:
            return Response(
                {'error': f'Failed to download image: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class BarcodeScanView(LoginRequiredMixin, View):
    """View for handling barcode scanning."""
    
    def post(self, request):
        """Process scanned barcode."""
        import json
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        
        scanned_data = data.get('scanned_data')
        scan_action = data.get('scan_action', 'lookup')
        scanner_device = data.get('scanner_device', '')
        location = data.get('location', '')
        notes = data.get('notes', '')
        
        if not scanned_data:
            return JsonResponse({'error': 'scanned_data is required'}, status=400)
        
        # Process scan
        service = BarcodeScanningService()
        result = service.scan_barcode(
            scanned_data, scan_action, scanner_device, location, notes
        )
        
        if result['success']:
            jewelry_item = result['jewelry_item']
            response_data = {
                'success': True,
                'jewelry_item': {
                    'id': jewelry_item.id,
                    'name': jewelry_item.name,
                    'sku': jewelry_item.sku,
                    'barcode': jewelry_item.barcode,
                    'category': jewelry_item.category.name if jewelry_item.category else None,
                    'weight_grams': str(jewelry_item.weight_grams),
                    'karat': jewelry_item.karat,
                    'status': jewelry_item.status,
                    'quantity': jewelry_item.quantity,
                    'selling_price': str(jewelry_item.selling_price) if jewelry_item.selling_price else None
                },
                'scan_history_id': result['scan_history'].id if result['scan_history'] else None
            }
            
            if result['barcode_generation']:
                response_data['barcode_generation'] = {
                    'id': result['barcode_generation'].id,
                    'barcode_type': result['barcode_generation'].barcode_type,
                    'generation_date': result['barcode_generation'].generation_date.isoformat()
                }
            
            return JsonResponse(response_data)
        else:
            return JsonResponse({
                'success': False,
                'error': result['error']
            }, status=404)


class BarcodeScanHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for barcode scan history."""
    
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_queryset(self):
        return BarcodeScanHistory.objects.filter(
            jewelry_item__created_by__tenant=self.request.tenant
        ).select_related('jewelry_item', 'barcode_generation')
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get scanning statistics."""
        item_id = request.query_params.get('item_id')
        
        jewelry_item = None
        if item_id:
            try:
                jewelry_item = JewelryItem.objects.get(id=item_id)
            except JewelryItem.DoesNotExist:
                return Response(
                    {'error': 'Jewelry item not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        service = BarcodeScanningService()
        stats = service.get_scan_statistics(jewelry_item)
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def by_item(self, request):
        """Get scan history for specific item."""
        item_id = request.query_params.get('item_id')
        limit = int(request.query_params.get('limit', 50))
        
        if not item_id:
            return Response(
                {'error': 'item_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            jewelry_item = JewelryItem.objects.get(id=item_id)
        except JewelryItem.DoesNotExist:
            return Response(
                {'error': 'Jewelry item not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        service = BarcodeScanningService()
        history = service.get_scan_history(jewelry_item, limit)
        
        history_data = []
        for scan in history:
            history_data.append({
                'id': scan.id,
                'scan_action': scan.scan_action,
                'scan_timestamp': scan.scan_timestamp.isoformat(),
                'scanner_device': scan.scanner_device,
                'location': scan.location,
                'notes': scan.notes,
                'scanned_data': scan.scanned_data[:100]  # Truncate for display
            })
        
        return Response({
            'jewelry_item': {
                'id': jewelry_item.id,
                'name': jewelry_item.name,
                'sku': jewelry_item.sku
            },
            'scan_history': history_data,
            'total_scans': len(history_data)
        })


class BarcodeTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for barcode templates."""
    
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_queryset(self):
        return BarcodeTemplate.objects.all()
    
    @action(detail=False, methods=['post'])
    def create_defaults(self, request):
        """Create default barcode templates."""
        service = BarcodeTemplateService()
        templates = service.create_default_templates()
        
        return Response({
            'success': True,
            'created_count': len(templates),
            'templates': [
                {
                    'id': template.id,
                    'name': template.name,
                    'barcode_type': template.barcode_type,
                    'is_default': template.is_default
                }
                for template in templates
            ]
        })


class BarcodeSettingsViewSet(viewsets.ModelViewSet):
    """ViewSet for barcode settings."""
    
    permission_classes = [IsAuthenticated, TenantPermission]
    
    def get_queryset(self):
        return BarcodeSettings.objects.all()
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current barcode settings."""
        service = BarcodeSettingsService()
        settings_obj = service.get_or_create_settings()
        
        return Response({
            'id': settings_obj.id,
            'auto_generate_on_create': settings_obj.auto_generate_on_create,
            'default_barcode_type': settings_obj.default_barcode_type,
            'include_tenant_prefix': settings_obj.include_tenant_prefix,
            'tenant_prefix': settings_obj.tenant_prefix,
            'qr_code_size': settings_obj.qr_code_size,
            'barcode_width': settings_obj.barcode_width,
            'barcode_height': settings_obj.barcode_height
        })
    
    @action(detail=False, methods=['post'])
    def update_settings(self, request):
        """Update barcode settings."""
        service = BarcodeSettingsService()
        
        try:
            settings_obj = service.update_settings(**request.data)
            
            return Response({
                'success': True,
                'settings': {
                    'id': settings_obj.id,
                    'auto_generate_on_create': settings_obj.auto_generate_on_create,
                    'default_barcode_type': settings_obj.default_barcode_type,
                    'include_tenant_prefix': settings_obj.include_tenant_prefix,
                    'tenant_prefix': settings_obj.tenant_prefix,
                    'qr_code_size': settings_obj.qr_code_size,
                    'barcode_width': settings_obj.barcode_width,
                    'barcode_height': settings_obj.barcode_height
                }
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to update settings: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )