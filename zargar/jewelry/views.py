"""
Comprehensive inventory management views for ZARGAR jewelry SaaS platform.
Provides complete inventory management UI with Persian RTL support and dual theme system.
"""
import json
import logging
from decimal import Decimal
from typing import Dict, Any, List
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.db.models import Q, Count, Sum, Avg, F
from django.core.paginator import Paginator
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy, reverse
from django.conf import settings
from django.utils import timezone

from zargar.core.mixins import TenantContextMixin
from .models import JewelryItem, Category, Gemstone, JewelryItemPhoto
from .barcode_models import BarcodeGeneration, BarcodeScanHistory
from .services import (
    SerialNumberTrackingService, 
    StockAlertService, 
    InventoryValuationService
)
from .barcode_services import BarcodeGenerationService, BarcodeScanningService

logger = logging.getLogger(__name__)


class InventoryDashboardView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Main inventory management dashboard with real-time valuation and stock alerts.
    """
    template_name = 'jewelry/inventory_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Get inventory statistics
            total_items = JewelryItem.objects.filter(status='in_stock').count()
            total_categories = Category.objects.filter(is_active=True).count()
            
            # Get stock alerts
            stock_alerts = StockAlertService.get_stock_alerts_summary()
            
            # Get inventory valuation
            valuation = InventoryValuationService.calculate_total_inventory_value()
            
            # Get recent items
            recent_items = JewelryItem.objects.select_related('category').order_by('-created_at')[:5]
            
            # Get high-value items without serial numbers
            items_needing_serial = SerialNumberTrackingService.get_high_value_items_without_serial()[:5]
            
            context.update({
                'total_items': total_items,
                'total_categories': total_categories,
                'stock_alerts': stock_alerts,
                'valuation': valuation,
                'recent_items': recent_items,
                'items_needing_serial': items_needing_serial,
                'dashboard_stats': {
                    'low_stock_count': stock_alerts.get('total_low_stock_items', 0),
                    'out_of_stock_count': stock_alerts.get('out_of_stock_items', 0),
                    'total_value': valuation.get('total_current_value', 0),
                    'value_change': valuation.get('gold_value_change', 0),
                    'value_change_percentage': valuation.get('gold_value_change_percentage', 0),
                }
            })
            
        except Exception as e:
            logger.error(f"Error loading inventory dashboard: {e}")
            messages.error(self.request, _('خطا در بارگذاری داشبورد موجودی'))
            context.update({
                'total_items': 0,
                'total_categories': 0,
                'stock_alerts': {},
                'valuation': {},
                'recent_items': [],
                'items_needing_serial': [],
                'dashboard_stats': {},
            })
        
        return context


class InventoryListView(LoginRequiredMixin, TenantContextMixin, ListView):
    """
    Comprehensive inventory list with search, filtering, and pagination.
    """
    model = JewelryItem
    template_name = 'jewelry/inventory_list.html'
    context_object_name = 'items'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = JewelryItem.objects.select_related('category').prefetch_related('photos')
        
        # Search functionality
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(sku__icontains=search_query) |
                Q(barcode__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Category filter
        category_id = self.request.GET.get('category')
        if category_id:
            try:
                queryset = queryset.filter(category_id=int(category_id))
            except (ValueError, TypeError):
                pass
        
        # Status filter
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Karat filter
        karat = self.request.GET.get('karat')
        if karat:
            try:
                queryset = queryset.filter(karat=int(karat))
            except (ValueError, TypeError):
                pass
        
        # Low stock filter
        low_stock = self.request.GET.get('low_stock')
        if low_stock == 'true':
            queryset = queryset.filter(quantity__lte=models.F('minimum_stock'))
        
        # Price range filter
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            try:
                queryset = queryset.filter(selling_price__gte=Decimal(min_price))
            except (ValueError, TypeError):
                pass
        if max_price:
            try:
                queryset = queryset.filter(selling_price__lte=Decimal(max_price))
            except (ValueError, TypeError):
                pass
        
        # Sorting
        sort_by = self.request.GET.get('sort', '-created_at')
        valid_sorts = [
            'name', '-name', 'sku', '-sku', 'created_at', '-created_at',
            'selling_price', '-selling_price', 'quantity', '-quantity',
            'weight_grams', '-weight_grams', 'karat', '-karat'
        ]
        if sort_by in valid_sorts:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('-created_at')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context.update({
            'categories': Category.objects.filter(is_active=True).order_by('name_persian'),
            'status_choices': JewelryItem.STATUS_CHOICES,
            'karat_choices': [(k, f'{k} عیار') for k in [14, 18, 21, 22, 24]],
            'current_filters': {
                'search': self.request.GET.get('search', ''),
                'category': self.request.GET.get('category', ''),
                'status': self.request.GET.get('status', ''),
                'karat': self.request.GET.get('karat', ''),
                'low_stock': self.request.GET.get('low_stock', ''),
                'min_price': self.request.GET.get('min_price', ''),
                'max_price': self.request.GET.get('max_price', ''),
                'sort': self.request.GET.get('sort', '-created_at'),
            }
        })
        
        return context


class InventoryDetailView(LoginRequiredMixin, TenantContextMixin, DetailView):
    """
    Detailed view of a jewelry item with photo gallery and actions.
    """
    model = JewelryItem
    template_name = 'jewelry/inventory_detail.html'
    context_object_name = 'item'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        item = self.get_object()
        
        # Get photos ordered by display order
        photos = item.photos.all().order_by('order', 'created_at')
        
        # Get related items (same category)
        related_items = JewelryItem.objects.filter(
            category=item.category,
            status='in_stock'
        ).exclude(id=item.id)[:6]
        
        # Calculate current gold value
        try:
            from zargar.gold_installments.services import GoldPriceService
            gold_price_data = GoldPriceService.get_current_gold_price(item.karat)
            current_gold_value = item.calculate_gold_value(gold_price_data['price_per_gram'])
        except Exception as e:
            logger.warning(f"Could not get current gold price: {e}")
            current_gold_value = item.gold_value or 0
        
        # Check if item needs serial number
        serial_check = SerialNumberTrackingService.assign_serial_number(item, force_assign=False)
        
        context.update({
            'photos': photos,
            'related_items': related_items,
            'current_gold_value': current_gold_value,
            'serial_check': serial_check,
            'can_edit': self.request.user.role in ['owner', 'accountant'],
            'can_delete': self.request.user.role == 'owner',
        })
        
        return context


class InventoryCreateView(LoginRequiredMixin, TenantContextMixin, CreateView):
    """
    Create new jewelry item with photo upload support.
    """
    model = JewelryItem
    template_name = 'jewelry/inventory_form.html'
    fields = [
        'name', 'sku', 'category', 'weight_grams', 'karat',
        'manufacturing_cost', 'gemstone_value', 'selling_price',
        'quantity', 'minimum_stock', 'description', 'notes'
    ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'form_title': _('افزودن کالای جدید'),
            'submit_text': _('ذخیره کالا'),
            'categories': Category.objects.filter(is_active=True).order_by('name_persian'),
            'gemstones': Gemstone.objects.all().order_by('name'),
        })
        return context
    
    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Set created_by
                form.instance.created_by = self.request.user
                
                # Calculate gold value if possible
                try:
                    from zargar.gold_installments.services import GoldPriceService
                    gold_price_data = GoldPriceService.get_current_gold_price(form.instance.karat)
                    form.instance.gold_value = form.instance.calculate_gold_value(
                        gold_price_data['price_per_gram']
                    )
                except Exception as e:
                    logger.warning(f"Could not calculate gold value: {e}")
                
                response = super().form_valid(form)
                
                # Handle photo uploads
                self._handle_photo_uploads(form.instance)
                
                # Try to assign serial number for high-value items
                serial_result = SerialNumberTrackingService.assign_serial_number(form.instance)
                if serial_result.get('success'):
                    messages.success(
                        self.request, 
                        _('کالا با موفقیت ثبت شد. شماره سریال: {}').format(
                            serial_result['serial_number']
                        )
                    )
                else:
                    messages.success(self.request, _('کالا با موفقیت ثبت شد'))
                
                return response
                
        except Exception as e:
            logger.error(f"Error creating jewelry item: {e}")
            messages.error(self.request, _('خطا در ثبت کالا'))
            return self.form_invalid(form)
    
    def _handle_photo_uploads(self, item):
        """Handle multiple photo uploads."""
        photos = self.request.FILES.getlist('photos')
        for i, photo in enumerate(photos):
            JewelryItemPhoto.objects.create(
                jewelry_item=item,
                image=photo,
                order=i,
                is_primary=(i == 0)  # First photo is primary
            )
    
    def get_success_url(self):
        return reverse('jewelry:inventory_detail', kwargs={'pk': self.object.pk})


class InventoryUpdateView(LoginRequiredMixin, TenantContextMixin, UpdateView):
    """
    Update existing jewelry item.
    """
    model = JewelryItem
    template_name = 'jewelry/inventory_form.html'
    fields = [
        'name', 'sku', 'category', 'weight_grams', 'karat',
        'manufacturing_cost', 'gemstone_value', 'selling_price',
        'quantity', 'minimum_stock', 'status', 'description', 'notes'
    ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'form_title': _('ویرایش کالا'),
            'submit_text': _('بروزرسانی کالا'),
            'categories': Category.objects.filter(is_active=True).order_by('name_persian'),
            'gemstones': Gemstone.objects.all().order_by('name'),
            'existing_photos': self.object.photos.all().order_by('order'),
        })
        return context
    
    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Update gold value if karat or weight changed
                if 'karat' in form.changed_data or 'weight_grams' in form.changed_data:
                    try:
                        from zargar.gold_installments.services import GoldPriceService
                        gold_price_data = GoldPriceService.get_current_gold_price(form.instance.karat)
                        form.instance.gold_value = form.instance.calculate_gold_value(
                            gold_price_data['price_per_gram']
                        )
                    except Exception as e:
                        logger.warning(f"Could not update gold value: {e}")
                
                response = super().form_valid(form)
                
                # Handle new photo uploads
                self._handle_photo_uploads(form.instance)
                
                messages.success(self.request, _('کالا با موفقیت بروزرسانی شد'))
                return response
                
        except Exception as e:
            logger.error(f"Error updating jewelry item: {e}")
            messages.error(self.request, _('خطا در بروزرسانی کالا'))
            return self.form_invalid(form)
    
    def _handle_photo_uploads(self, item):
        """Handle new photo uploads."""
        photos = self.request.FILES.getlist('new_photos')
        existing_count = item.photos.count()
        
        for i, photo in enumerate(photos):
            JewelryItemPhoto.objects.create(
                jewelry_item=item,
                image=photo,
                order=existing_count + i,
                is_primary=False
            )
    
    def get_success_url(self):
        return reverse('jewelry:inventory_detail', kwargs={'pk': self.object.pk})


class CategoryManagementView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Manage jewelry categories and collections.
    """
    template_name = 'jewelry/category_management.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get categories with item counts
        categories = Category.objects.annotate(
            item_count=Count('jewelryitem'),
            total_value=Sum('jewelryitem__selling_price')
        ).order_by('name_persian')
        
        context.update({
            'categories': categories,
            'can_manage': self.request.user.role in ['owner', 'accountant'],
        })
        
        return context


class StockAlertsView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Stock alerts dashboard with customizable thresholds.
    """
    template_name = 'jewelry/stock_alerts.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get stock alerts summary
        alerts_summary = StockAlertService.get_stock_alerts_summary()
        
        # Get low stock items
        low_stock_items = StockAlertService.get_low_stock_items()
        
        # Get reorder suggestions
        reorder_suggestions = StockAlertService.create_reorder_suggestions()
        
        context.update({
            'alerts_summary': alerts_summary,
            'low_stock_items': low_stock_items,
            'reorder_suggestions': reorder_suggestions,
            'can_manage': self.request.user.role in ['owner', 'accountant'],
        })
        
        return context


class InventoryValuationView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Real-time inventory valuation dashboard with gold price integration.
    """
    template_name = 'jewelry/inventory_valuation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get comprehensive valuation
        valuation = InventoryValuationService.calculate_total_inventory_value()
        
        # Get valuation by category
        category_valuations = []
        for category in Category.objects.filter(is_active=True):
            cat_valuation = InventoryValuationService.calculate_total_inventory_value(
                category_filter=category.id
            )
            if cat_valuation['total_items'] > 0:
                category_valuations.append({
                    'category': category,
                    'valuation': cat_valuation
                })
        
        context.update({
            'valuation': valuation,
            'category_valuations': category_valuations,
            'can_update_prices': self.request.user.role in ['owner', 'accountant'],
        })
        
        return context


# AJAX Views for dynamic functionality

@login_required
@require_http_methods(["POST"])
def update_stock_thresholds(request):
    """
    AJAX endpoint to update stock thresholds for multiple items.
    """
    try:
        data = json.loads(request.body)
        updates = data.get('updates', [])
        
        result = StockAlertService.update_stock_thresholds(updates)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': _('حد آستانه موجودی با موفقیت بروزرسانی شد'),
                'updated_count': result['updated_count']
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result.get('message', _('خطا در بروزرسانی'))
            })
            
    except Exception as e:
        logger.error(f"Error updating stock thresholds: {e}")
        return JsonResponse({
            'success': False,
            'message': _('خطا در بروزرسانی حد آستانه موجودی')
        })


@login_required
@require_http_methods(["POST"])
def update_gold_values(request):
    """
    AJAX endpoint to update all gold values with current prices.
    """
    try:
        result = InventoryValuationService.update_all_gold_values()
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': _('قیمت طلا با موفقیت بروزرسانی شد'),
                'updated_count': result['updated_count'],
                'total_change': str(result['total_value_change'])
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result.get('message', _('خطا در بروزرسانی قیمت طلا'))
            })
            
    except Exception as e:
        logger.error(f"Error updating gold values: {e}")
        return JsonResponse({
            'success': False,
            'message': _('خطا در بروزرسانی قیمت طلا')
        })


@login_required
@require_http_methods(["POST"])
def assign_serial_number(request, item_id):
    """
    AJAX endpoint to assign serial number to an item.
    """
    try:
        item = get_object_or_404(JewelryItem, id=item_id)
        force_assign = request.POST.get('force_assign', 'false').lower() == 'true'
        
        result = SerialNumberTrackingService.assign_serial_number(item, force_assign)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': _('شماره سریال با موفقیت تخصیص داده شد'),
                'serial_number': result['serial_number']
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result.get('message', _('خطا در تخصیص شماره سریال')),
                'requires_high_value': result.get('requires_high_value', False),
                'threshold': str(result.get('threshold', 0))
            })
            
    except Exception as e:
        logger.error(f"Error assigning serial number: {e}")
        return JsonResponse({
            'success': False,
            'message': _('خطا در تخصیص شماره سریال')
        })


@login_required
@require_http_methods(["DELETE"])
def delete_photo(request, photo_id):
    """
    AJAX endpoint to delete a jewelry item photo.
    """
    try:
        photo = get_object_or_404(JewelryItemPhoto, id=photo_id)
        
        # Check permissions
        if request.user.role not in ['owner', 'accountant']:
            return JsonResponse({
                'success': False,
                'message': _('شما مجاز به حذف تصاویر نیستید')
            })
        
        # Delete the file
        if photo.image:
            default_storage.delete(photo.image.name)
        
        photo.delete()
        
        return JsonResponse({
            'success': True,
            'message': _('تصویر با موفقیت حذف شد')
        })
        
    except Exception as e:
        logger.error(f"Error deleting photo: {e}")
        return JsonResponse({
            'success': False,
            'message': _('خطا در حذف تصویر')
        })


@login_required
@require_http_methods(["POST"])
def reorder_photos(request, item_id):
    """
    AJAX endpoint to reorder jewelry item photos.
    """
    try:
        item = get_object_or_404(JewelryItem, id=item_id)
        data = json.loads(request.body)
        photo_orders = data.get('photo_orders', [])
        
        # Check permissions
        if request.user.role not in ['owner', 'accountant']:
            return JsonResponse({
                'success': False,
                'message': _('شما مجاز به تغییر ترتیب تصاویر نیستید')
            })
        
        with transaction.atomic():
            for order_data in photo_orders:
                photo_id = order_data['photo_id']
                new_order = order_data['order']
                
                JewelryItemPhoto.objects.filter(
                    id=photo_id,
                    jewelry_item=item
                ).update(order=new_order)
        
        return JsonResponse({
            'success': True,
            'message': _('ترتیب تصاویر با موفقیت بروزرسانی شد')
        })
        
    except Exception as e:
        logger.error(f"Error reordering photos: {e}")
        return JsonResponse({
            'success': False,
            'message': _('خطا در تغییر ترتیب تصاویر')
        })


@login_required
def inventory_search_api(request):
    """
    AJAX API for inventory search with autocomplete.
    """
    try:
        query = request.GET.get('q', '').strip()
        limit = min(int(request.GET.get('limit', 10)), 50)
        
        if len(query) < 2:
            return JsonResponse({'results': []})
        
        items = JewelryItem.objects.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(barcode__icontains=query)
        ).select_related('category')[:limit]
        
        results = []
        for item in items:
            results.append({
                'id': item.id,
                'name': item.name,
                'sku': item.sku,
                'category': item.category.name_persian or item.category.name,
                'status': item.get_status_display(),
                'quantity': item.quantity,
                'selling_price': str(item.selling_price or 0),
                'url': reverse('jewelry:inventory_detail', kwargs={'pk': item.pk})
            })
        
        return JsonResponse({'results': results})
        
    except Exception as e:
        logger.error(f"Error in inventory search API: {e}")
        return JsonResponse({'results': [], 'error': str(e)})


# Category Management AJAX Views

@login_required
@require_http_methods(["POST"])
def create_category(request):
    """
    AJAX endpoint to create a new category.
    """
    try:
        data = json.loads(request.body)
        
        # Check permissions
        if request.user.role not in ['owner', 'accountant']:
            return JsonResponse({
                'success': False,
                'message': _('شما مجاز به ایجاد دسته‌بندی نیستید')
            })
        
        category = Category.objects.create(
            name=data['name'],
            name_persian=data['name_persian'],
            description=data.get('description', ''),
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': _('دسته‌بندی با موفقیت ایجاد شد'),
            'category': {
                'id': category.id,
                'name': category.name,
                'name_persian': category.name_persian,
                'description': category.description
            }
        })
        
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        return JsonResponse({
            'success': False,
            'message': _('خطا در ایجاد دسته‌بندی')
        })


class BarcodeManagementView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Barcode management interface with generation, printing, and scanning capabilities.
    """
    template_name = 'jewelry/barcode_management.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Get barcode statistics
            total_barcodes = BarcodeGeneration.objects.filter(is_active=True).count()
            today_scans = BarcodeScanHistory.objects.filter(
                scan_timestamp__date=timezone.now().date()
            ).count()
            qr_codes = BarcodeGeneration.objects.filter(
                barcode_type='qr_code', 
                is_active=True
            ).count()
            items_without_barcode = JewelryItem.objects.filter(
                barcode__isnull=True
            ).count()
            
            context.update({
                'barcode_stats': {
                    'total_barcodes': total_barcodes,
                    'today_scans': today_scans,
                    'qr_codes': qr_codes,
                    'items_without_barcode': items_without_barcode,
                }
            })
            
        except Exception as e:
            logger.error(f"Error loading barcode management data: {e}")
            context.update({
                'barcode_stats': {
                    'total_barcodes': 0,
                    'today_scans': 0,
                    'qr_codes': 0,
                    'items_without_barcode': 0,
                }
            })
        
        return context


class MobileScannerView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Mobile-optimized barcode scanning interface.
    """
    template_name = 'jewelry/mobile_scanner.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Get recent scans for this user/tenant
            recent_scans = BarcodeScanHistory.objects.select_related(
                'jewelry_item'
            ).order_by('-scan_timestamp')[:10]
            
            context.update({
                'recent_scans': recent_scans,
            })
            
        except Exception as e:
            logger.error(f"Error loading mobile scanner data: {e}")
            context.update({
                'recent_scans': [],
            })
        
        return context


class BarcodeHistoryView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Barcode scanning history and tracking interface.
    """
    template_name = 'jewelry/barcode_history.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Get scan statistics
            total_scans = BarcodeScanHistory.objects.count()
            today_scans = BarcodeScanHistory.objects.filter(
                scan_timestamp__date=timezone.now().date()
            ).count()
            
            # Get recent scans
            recent_scans = BarcodeScanHistory.objects.select_related(
                'jewelry_item'
            ).order_by('-scan_timestamp')[:20]
            
            context.update({
                'scan_stats': {
                    'total_scans': total_scans,
                    'today_scans': today_scans,
                },
                'recent_scans': recent_scans,
            })
            
        except Exception as e:
            logger.error(f"Error loading barcode history data: {e}")
            context.update({
                'scan_stats': {
                    'total_scans': 0,
                    'today_scans': 0,
                },
                'recent_scans': [],
            })
        
        return context


# Barcode API Endpoints

@login_required
def barcode_items_api(request):
    """
    API endpoint to get jewelry items with barcode information.
    """
    try:
        # Get all jewelry items with barcode information
        items = JewelryItem.objects.select_related('category').prefetch_related(
            'barcodegeneration_set'
        ).all()
        
        # Apply search filter if provided
        search_query = request.GET.get('search', '').strip()
        if search_query:
            items = items.filter(
                Q(name__icontains=search_query) |
                Q(sku__icontains=search_query) |
                Q(barcode__icontains=search_query)
            )
        
        # Apply barcode type filter
        barcode_type = request.GET.get('barcode_type', '').strip()
        if barcode_type:
            items = items.filter(barcodegeneration__barcode_type=barcode_type)
        
        # Apply status filter
        status_filter = request.GET.get('status', '').strip()
        if status_filter == 'has_barcode':
            items = items.exclude(barcode__isnull=True).exclude(barcode='')
        elif status_filter == 'no_barcode':
            items = items.filter(Q(barcode__isnull=True) | Q(barcode=''))
        
        # Prepare response data
        results = []
        for item in items:
            # Get active barcode generation
            active_barcode = item.barcodegeneration_set.filter(is_active=True).first()
            
            item_data = {
                'id': item.id,
                'name': item.name,
                'sku': item.sku,
                'category': item.category.name_persian if item.category else '',
                'barcode': item.barcode,
                'barcode_type': active_barcode.barcode_type if active_barcode else None,
                'barcode_type_display': active_barcode.get_barcode_type_display() if active_barcode else None,
                'barcode_image': active_barcode.barcode_image.url if active_barcode and active_barcode.barcode_image else None,
                'status': item.get_status_display(),
                'quantity': item.quantity,
                'selling_price': str(item.selling_price) if item.selling_price else '0',
                'weight_grams': str(item.weight_grams),
                'karat': item.karat,
            }
            results.append(item_data)
        
        return JsonResponse({
            'success': True,
            'results': results,
            'total_count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Error in barcode items API: {e}")
        return JsonResponse({
            'success': False,
            'error': 'خطا در بارگذاری اطلاعات اقلام'
        }, status=500)


@login_required
def barcode_statistics_api(request):
    """
    API endpoint to get barcode statistics and analytics.
    """
    try:
        from datetime import timedelta
        from django.db.models import Count
        
        # Basic statistics
        total_barcodes = BarcodeGeneration.objects.filter(is_active=True).count()
        today = timezone.now().date()
        today_scans = BarcodeScanHistory.objects.filter(
            scan_timestamp__date=today
        ).count()
        qr_codes = BarcodeGeneration.objects.filter(
            barcode_type='qr_code',
            is_active=True
        ).count()
        items_without_barcode = JewelryItem.objects.filter(
            Q(barcode__isnull=True) | Q(barcode='')
        ).count()
        
        # Daily activity for the last 7 days
        daily_activity = []
        for i in range(7):
            date = today - timedelta(days=i)
            scans_count = BarcodeScanHistory.objects.filter(
                scan_timestamp__date=date
            ).count()
            daily_activity.append({
                'date': date.strftime('%Y-%m-%d'),
                'scans': scans_count
            })
        
        # Scan types distribution
        scan_types = BarcodeScanHistory.objects.values('scan_action').annotate(
            count=Count('scan_action')
        ).order_by('-count')
        
        scan_types_data = []
        for scan_type in scan_types:
            scan_types_data.append({
                'action': scan_type['scan_action'],
                'count': scan_type['count']
            })
        
        # Active users (users who scanned in the last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        active_users = BarcodeScanHistory.objects.filter(
            scan_timestamp__gte=week_ago
        ).values('jewelry_item__created_by').distinct().count()
        
        # Daily average
        total_days = 7
        daily_average = round(
            BarcodeScanHistory.objects.filter(
                scan_timestamp__gte=week_ago
            ).count() / total_days, 1
        )
        
        return JsonResponse({
            'success': True,
            'total_barcodes': total_barcodes,
            'today_scans': today_scans,
            'qr_codes': qr_codes,
            'items_without_barcode': items_without_barcode,
            'active_users': active_users,
            'daily_average': daily_average,
            'daily_activity': daily_activity,
            'scan_types': scan_types_data
        })
        
    except Exception as e:
        logger.error(f"Error in barcode statistics API: {e}")
        return JsonResponse({
            'success': False,
            'error': 'خطا در بارگذاری آمار بارکد'
        }, status=500)
