"""
Supplier management views with contact and payment terms forms.
"""
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count, Avg, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from zargar.core.mixins import TenantContextMixin
from .models import Supplier, PurchaseOrder, PurchaseOrderItem
from .supplier_services import SupplierPayment, DeliverySchedule, SupplierPerformanceMetrics


class SupplierManagementDashboardView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Supplier management interface with contact and payment terms forms.
    """
    template_name = 'customers/supplier_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get supplier statistics
        total_suppliers = Supplier.objects.filter(tenant=self.request.tenant).count()
        active_suppliers = Supplier.objects.filter(tenant=self.request.tenant, is_active=True).count()
        preferred_suppliers = Supplier.objects.filter(tenant=self.request.tenant, is_preferred=True).count()
        
        # Get supplier type distribution
        supplier_types = Supplier.objects.filter(
            tenant=self.request.tenant
        ).values('supplier_type').annotate(count=Count('id')).order_by('-count')
        
        # Get top suppliers by order amount
        top_suppliers = Supplier.objects.filter(
            tenant=self.request.tenant,
            is_active=True
        ).order_by('-total_amount')[:10]
        
        # Get recent suppliers
        recent_suppliers = Supplier.objects.filter(
            tenant=self.request.tenant
        ).order_by('-created_at')[:5]
        
        # Get pending purchase orders
        pending_orders = PurchaseOrder.objects.filter(
            supplier__tenant=self.request.tenant,
            status__in=['draft', 'sent', 'confirmed']
        ).select_related('supplier').order_by('-order_date')[:10]
        
        # Get overdue orders
        overdue_orders = PurchaseOrder.objects.filter(
            supplier__tenant=self.request.tenant,
            expected_delivery_date__lt=timezone.now().date(),
            status__in=['sent', 'confirmed']
        ).select_related('supplier').count()
        
        # Calculate total order amounts
        order_stats = PurchaseOrder.objects.filter(
            supplier__tenant=self.request.tenant
        ).aggregate(
            total_orders=Count('id'),
            total_amount=Sum('total_amount'),
            pending_amount=Sum('total_amount', filter=Q(status__in=['draft', 'sent', 'confirmed'])),
            completed_amount=Sum('total_amount', filter=Q(status='completed'))
        )
        
        context.update({
            'total_suppliers': total_suppliers,
            'active_suppliers': active_suppliers,
            'inactive_suppliers': total_suppliers - active_suppliers,
            'preferred_suppliers': preferred_suppliers,
            'supplier_types': list(supplier_types),
            'top_suppliers': top_suppliers,
            'recent_suppliers': recent_suppliers,
            'pending_orders': pending_orders,
            'overdue_orders': overdue_orders,
            'order_stats': {
                'total_orders': order_stats['total_orders'] or 0,
                'total_amount': order_stats['total_amount'] or 0,
                'pending_amount': order_stats['pending_amount'] or 0,
                'completed_amount': order_stats['completed_amount'] or 0
            }
        })
        
        return context


class SupplierListView(LoginRequiredMixin, TenantContextMixin, ListView):
    """
    Supplier database with search, filtering, and contact management.
    """
    model = Supplier
    template_name = 'customers/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Supplier.objects.filter(tenant=self.request.tenant).order_by('-created_at')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(persian_name__icontains=search) |
                Q(contact_person__icontains=search) |
                Q(phone_number__icontains=search) |
                Q(email__icontains=search)
            )
        
        # Filter by supplier type
        supplier_type = self.request.GET.get('supplier_type')
        if supplier_type:
            queryset = queryset.filter(supplier_type=supplier_type)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status == 'preferred':
            queryset = queryset.filter(is_preferred=True)
        
        # Sort options
        sort = self.request.GET.get('sort', '-created_at')
        if sort in ['name', '-name', 'total_amount', '-total_amount', 'total_orders', '-total_orders', 'created_at', '-created_at']:
            queryset = queryset.order_by(sort)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter options
        context['supplier_types'] = Supplier.SUPPLIER_TYPES
        context['current_filters'] = {
            'search': self.request.GET.get('search', ''),
            'supplier_type': self.request.GET.get('supplier_type', ''),
            'status': self.request.GET.get('status', ''),
            'sort': self.request.GET.get('sort', '-created_at')
        }
        
        return context


class SupplierDetailView(LoginRequiredMixin, TenantContextMixin, DetailView):
    """
    Detailed view of supplier information with performance tracking.
    """
    model = Supplier
    template_name = 'customers/supplier_detail.html'
    context_object_name = 'supplier'
    
    def get_queryset(self):
        return Supplier.objects.filter(tenant=self.request.tenant)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supplier = self.get_object()
        
        # Get purchase orders
        purchase_orders = PurchaseOrder.objects.filter(
            supplier=supplier
        ).order_by('-order_date')[:20]
        
        # Get order statistics
        order_stats = PurchaseOrder.objects.filter(
            supplier=supplier
        ).aggregate(
            total_orders=Count('id'),
            total_amount=Sum('total_amount'),
            pending_orders=Count('id', filter=Q(status__in=['draft', 'sent', 'confirmed'])),
            completed_orders=Count('id', filter=Q(status='completed')),
            cancelled_orders=Count('id', filter=Q(status='cancelled')),
            avg_order_amount=Avg('total_amount')
        )
        
        # Get recent payments
        recent_payments = SupplierPayment.objects.filter(
            supplier=supplier
        ).order_by('-payment_date')[:10]
        
        # Get delivery performance
        delivery_performance = PurchaseOrder.objects.filter(
            supplier=supplier,
            status='completed',
            expected_delivery_date__isnull=False,
            actual_delivery_date__isnull=False
        ).annotate(
            delivery_delay=F('actual_delivery_date') - F('expected_delivery_date')
        ).aggregate(
            on_time_deliveries=Count('id', filter=Q(delivery_delay__lte=0)),
            late_deliveries=Count('id', filter=Q(delivery_delay__gt=0)),
            avg_delay_days=Avg('delivery_delay')
        )
        
        # Calculate performance metrics
        total_completed = delivery_performance['on_time_deliveries'] + delivery_performance['late_deliveries']
        on_time_percentage = 0
        if total_completed > 0:
            on_time_percentage = (delivery_performance['on_time_deliveries'] / total_completed) * 100
        
        # Get supplier performance metrics
        try:
            performance_metrics = SupplierPerformanceMetrics.objects.get(supplier=supplier)
        except SupplierPerformanceMetrics.DoesNotExist:
            performance_metrics = None
        
        context.update({
            'purchase_orders': purchase_orders,
            'order_stats': order_stats,
            'recent_payments': recent_payments,
            'delivery_performance': delivery_performance,
            'on_time_percentage': round(on_time_percentage, 1),
            'performance_metrics': performance_metrics
        })
        
        return context


class SupplierCreateView(LoginRequiredMixin, TenantContextMixin, CreateView):
    """
    Create new supplier with contact and payment terms.
    """
    model = Supplier
    template_name = 'customers/supplier_form.html'
    fields = [
        'name', 'persian_name', 'supplier_type', 'contact_person',
        'phone_number', 'email', 'website', 'address', 'city',
        'tax_id', 'payment_terms', 'credit_limit', 'is_preferred', 'notes'
    ]
    
    def form_valid(self, form):
        form.instance.tenant = self.request.tenant
        form.instance.created_by = self.request.user
        messages.success(self.request, f'تامین‌کننده {form.instance.persian_name or form.instance.name} با موفقیت ایجاد شد.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('customers:supplier_detail', kwargs={'pk': self.object.pk})


class SupplierUpdateView(LoginRequiredMixin, TenantContextMixin, UpdateView):
    """
    Update supplier information.
    """
    model = Supplier
    template_name = 'customers/supplier_form.html'
    fields = [
        'name', 'persian_name', 'supplier_type', 'contact_person',
        'phone_number', 'email', 'website', 'address', 'city',
        'tax_id', 'payment_terms', 'credit_limit', 'is_active', 'is_preferred', 'notes'
    ]
    
    def get_queryset(self):
        return Supplier.objects.filter(tenant=self.request.tenant)
    
    def form_valid(self, form):
        messages.success(self.request, f'اطلاعات تامین‌کننده {form.instance.persian_name or form.instance.name} به‌روزرسانی شد.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('customers:supplier_detail', kwargs={'pk': self.object.pk})


class PurchaseOrderListView(LoginRequiredMixin, TenantContextMixin, ListView):
    """
    Purchase order creation and management interface with Persian forms.
    """
    model = PurchaseOrder
    template_name = 'customers/purchase_order_list.html'
    context_object_name = 'purchase_orders'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = PurchaseOrder.objects.filter(
            supplier__tenant=self.request.tenant
        ).select_related('supplier').order_by('-order_date')
        
        # Filter by supplier
        supplier_id = self.request.GET.get('supplier')
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by priority
        priority = self.request.GET.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Date range filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(order_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(order_date__lte=date_to)
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(supplier__name__icontains=search) |
                Q(supplier__persian_name__icontains=search) |
                Q(notes__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter options
        context['suppliers'] = Supplier.objects.filter(
            tenant=self.request.tenant,
            is_active=True
        ).order_by('persian_name', 'name')
        
        context['status_choices'] = PurchaseOrder.STATUS_CHOICES
        context['priority_choices'] = PurchaseOrder.PRIORITY_CHOICES
        
        context['current_filters'] = {
            'supplier': self.request.GET.get('supplier', ''),
            'status': self.request.GET.get('status', ''),
            'priority': self.request.GET.get('priority', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'search': self.request.GET.get('search', '')
        }
        
        # Get summary statistics
        context['summary_stats'] = PurchaseOrder.objects.filter(
            supplier__tenant=self.request.tenant
        ).aggregate(
            total_orders=Count('id'),
            pending_orders=Count('id', filter=Q(status__in=['draft', 'sent', 'confirmed'])),
            overdue_orders=Count('id', filter=Q(
                expected_delivery_date__lt=timezone.now().date(),
                status__in=['sent', 'confirmed']
            )),
            total_amount=Sum('total_amount')
        )
        
        return context


class PurchaseOrderDetailView(LoginRequiredMixin, TenantContextMixin, DetailView):
    """
    Detailed view of purchase order with items and tracking.
    """
    model = PurchaseOrder
    template_name = 'customers/purchase_order_detail.html'
    context_object_name = 'purchase_order'
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(
            supplier__tenant=self.request.tenant
        ).select_related('supplier')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        purchase_order = self.get_object()
        
        # Get order items
        order_items = PurchaseOrderItem.objects.filter(
            purchase_order=purchase_order
        ).order_by('id')
        
        # Get delivery schedules
        delivery_schedules = DeliverySchedule.objects.filter(
            purchase_order=purchase_order
        ).order_by('scheduled_date')
        
        # Get payments
        payments = SupplierPayment.objects.filter(
            purchase_order=purchase_order
        ).order_by('-payment_date')
        
        # Calculate completion percentage
        total_items = order_items.count()
        received_items = order_items.filter(is_received=True).count()
        completion_percentage = 0
        if total_items > 0:
            completion_percentage = (received_items / total_items) * 100
        
        context.update({
            'order_items': order_items,
            'delivery_schedules': delivery_schedules,
            'payments': payments,
            'completion_percentage': round(completion_percentage, 1),
            'can_edit': purchase_order.status in ['draft'],
            'can_send': purchase_order.status == 'draft',
            'can_receive': purchase_order.status in ['sent', 'confirmed', 'partially_received'],
            'can_cancel': purchase_order.status in ['draft', 'sent', 'confirmed']
        })
        
        return context


class PurchaseOrderCreateView(LoginRequiredMixin, TenantContextMixin, CreateView):
    """
    Create new purchase order.
    """
    model = PurchaseOrder
    template_name = 'customers/purchase_order_form.html'
    fields = [
        'supplier', 'order_date', 'expected_delivery_date', 'priority',
        'payment_terms', 'payment_due_date', 'delivery_address',
        'notes', 'internal_notes'
    ]
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filter suppliers to current tenant
        form.fields['supplier'].queryset = Supplier.objects.filter(
            tenant=self.request.tenant,
            is_active=True
        ).order_by('persian_name', 'name')
        return form
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'سفارش خرید {form.instance.order_number} ایجاد شد.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('customers:purchase_order_detail', kwargs={'pk': self.object.pk})


class PurchaseOrderUpdateView(LoginRequiredMixin, TenantContextMixin, UpdateView):
    """
    Update purchase order.
    """
    model = PurchaseOrder
    template_name = 'customers/purchase_order_form.html'
    fields = [
        'supplier', 'order_date', 'expected_delivery_date', 'priority',
        'payment_terms', 'payment_due_date', 'delivery_address',
        'notes', 'internal_notes'
    ]
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(
            supplier__tenant=self.request.tenant,
            status='draft'  # Only allow editing draft orders
        )
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filter suppliers to current tenant
        form.fields['supplier'].queryset = Supplier.objects.filter(
            tenant=self.request.tenant,
            is_active=True
        ).order_by('persian_name', 'name')
        return form
    
    def form_valid(self, form):
        messages.success(self.request, f'سفارش خرید {form.instance.order_number} به‌روزرسانی شد.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('customers:purchase_order_detail', kwargs={'pk': self.object.pk})


class SupplierPerformanceReportView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Supplier performance tracking and reporting dashboard.
    """
    template_name = 'customers/supplier_performance.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range from request
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if not date_from:
            date_from = (timezone.now() - timedelta(days=90)).date()
        else:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        
        if not date_to:
            date_to = timezone.now().date()
        else:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        
        # Get supplier performance data
        suppliers = Supplier.objects.filter(
            tenant=self.request.tenant,
            is_active=True
        ).annotate(
            orders_in_period=Count(
                'purchase_orders',
                filter=Q(purchase_orders__order_date__range=[date_from, date_to])
            ),
            total_amount_in_period=Sum(
                'purchase_orders__total_amount',
                filter=Q(purchase_orders__order_date__range=[date_from, date_to])
            ),
            completed_orders=Count(
                'purchase_orders',
                filter=Q(
                    purchase_orders__order_date__range=[date_from, date_to],
                    purchase_orders__status='completed'
                )
            ),
            on_time_deliveries=Count(
                'purchase_orders',
                filter=Q(
                    purchase_orders__order_date__range=[date_from, date_to],
                    purchase_orders__status='completed',
                    purchase_orders__actual_delivery_date__lte=F('purchase_orders__expected_delivery_date')
                )
            )
        ).filter(orders_in_period__gt=0).order_by('-total_amount_in_period')
        
        # Calculate performance metrics for each supplier
        supplier_performance = []
        for supplier in suppliers:
            on_time_rate = 0
            if supplier.completed_orders > 0:
                on_time_rate = (supplier.on_time_deliveries / supplier.completed_orders) * 100
            
            supplier_performance.append({
                'supplier': supplier,
                'orders_count': supplier.orders_in_period,
                'total_amount': supplier.total_amount_in_period or 0,
                'completed_orders': supplier.completed_orders,
                'on_time_deliveries': supplier.on_time_deliveries,
                'on_time_rate': round(on_time_rate, 1)
            })
        
        # Get overall statistics
        overall_stats = PurchaseOrder.objects.filter(
            supplier__tenant=self.request.tenant,
            order_date__range=[date_from, date_to]
        ).aggregate(
            total_orders=Count('id'),
            total_amount=Sum('total_amount'),
            completed_orders=Count('id', filter=Q(status='completed')),
            cancelled_orders=Count('id', filter=Q(status='cancelled')),
            overdue_orders=Count('id', filter=Q(
                expected_delivery_date__lt=timezone.now().date(),
                status__in=['sent', 'confirmed']
            ))
        )
        
        # Get top performing suppliers
        top_suppliers_by_amount = supplier_performance[:5]
        top_suppliers_by_reliability = sorted(
            [s for s in supplier_performance if s['completed_orders'] >= 3],
            key=lambda x: x['on_time_rate'],
            reverse=True
        )[:5]
        
        context.update({
            'date_from': date_from,
            'date_to': date_to,
            'supplier_performance': supplier_performance,
            'overall_stats': overall_stats,
            'top_suppliers_by_amount': top_suppliers_by_amount,
            'top_suppliers_by_reliability': top_suppliers_by_reliability
        })
        
        return context


# AJAX Views for dynamic functionality
class SupplierAjaxView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    AJAX endpoints for supplier operations.
    """
    
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        
        if action == 'toggle_preferred':
            return self.toggle_preferred_supplier(request)
        elif action == 'toggle_active':
            return self.toggle_active_supplier(request)
        elif action == 'update_payment_terms':
            return self.update_payment_terms(request)
        elif action == 'send_purchase_order':
            return self.send_purchase_order(request)
        elif action == 'receive_items':
            return self.receive_items(request)
        elif action == 'cancel_order':
            return self.cancel_order(request)
        
        return JsonResponse({'success': False, 'error': 'Invalid action'})
    
    def toggle_preferred_supplier(self, request):
        """Toggle supplier preferred status."""
        try:
            supplier_id = request.POST.get('supplier_id')
            supplier = get_object_or_404(Supplier, id=supplier_id, tenant=request.tenant)
            
            supplier.is_preferred = not supplier.is_preferred
            supplier.save(update_fields=['is_preferred', 'updated_at'])
            
            status = 'ترجیحی' if supplier.is_preferred else 'عادی'
            return JsonResponse({
                'success': True,
                'message': f'وضعیت تامین‌کننده {supplier.persian_name or supplier.name} به {status} تغییر یافت.',
                'is_preferred': supplier.is_preferred
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    def toggle_active_supplier(self, request):
        """Toggle supplier active status."""
        try:
            supplier_id = request.POST.get('supplier_id')
            supplier = get_object_or_404(Supplier, id=supplier_id, tenant=request.tenant)
            
            supplier.is_active = not supplier.is_active
            supplier.save(update_fields=['is_active', 'updated_at'])
            
            status = 'فعال' if supplier.is_active else 'غیرفعال'
            return JsonResponse({
                'success': True,
                'message': f'وضعیت تامین‌کننده {supplier.persian_name or supplier.name} به {status} تغییر یافت.',
                'is_active': supplier.is_active
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    def update_payment_terms(self, request):
        """Update supplier payment terms."""
        try:
            supplier_id = request.POST.get('supplier_id')
            payment_terms = request.POST.get('payment_terms')
            
            supplier = get_object_or_404(Supplier, id=supplier_id, tenant=request.tenant)
            supplier.payment_terms = payment_terms
            supplier.save(update_fields=['payment_terms', 'updated_at'])
            
            return JsonResponse({
                'success': True,
                'message': f'شرایط پرداخت تامین‌کننده {supplier.persian_name or supplier.name} به‌روزرسانی شد.',
                'payment_terms': payment_terms
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    def send_purchase_order(self, request):
        """Send purchase order to supplier."""
        try:
            order_id = request.POST.get('order_id')
            purchase_order = get_object_or_404(
                PurchaseOrder, 
                id=order_id, 
                supplier__tenant=request.tenant,
                status='draft'
            )
            
            purchase_order.mark_as_sent()
            
            return JsonResponse({
                'success': True,
                'message': f'سفارش خرید {purchase_order.order_number} به تامین‌کننده ارسال شد.',
                'new_status': purchase_order.get_status_display()
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    def receive_items(self, request):
        """Mark items as received."""
        try:
            order_id = request.POST.get('order_id')
            item_quantities = json.loads(request.POST.get('item_quantities', '{}'))
            
            purchase_order = get_object_or_404(
                PurchaseOrder, 
                id=order_id, 
                supplier__tenant=request.tenant
            )
            
            received_items = 0
            for item_id, quantity in item_quantities.items():
                try:
                    item = PurchaseOrderItem.objects.get(
                        id=item_id, 
                        purchase_order=purchase_order
                    )
                    if item.receive_quantity(int(quantity)):
                        received_items += 1
                except (PurchaseOrderItem.DoesNotExist, ValueError):
                    continue
            
            # Update order status if all items received
            all_items = purchase_order.items.all()
            if all(item.is_fully_received for item in all_items):
                purchase_order.mark_as_received(partial=False)
            elif any(item.quantity_received > 0 for item in all_items):
                purchase_order.mark_as_received(partial=True)
            
            return JsonResponse({
                'success': True,
                'message': f'{received_items} قلم کالا دریافت شد.',
                'new_status': purchase_order.get_status_display()
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    def cancel_order(self, request):
        """Cancel purchase order."""
        try:
            order_id = request.POST.get('order_id')
            reason = request.POST.get('reason', '')
            
            purchase_order = get_object_or_404(
                PurchaseOrder, 
                id=order_id, 
                supplier__tenant=request.tenant,
                status__in=['draft', 'sent', 'confirmed']
            )
            
            purchase_order.cancel_order(reason)
            
            return JsonResponse({
                'success': True,
                'message': f'سفارش خرید {purchase_order.order_number} لغو شد.',
                'new_status': purchase_order.get_status_display()
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})