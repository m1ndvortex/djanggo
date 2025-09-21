"""
POS views for ZARGAR jewelry SaaS platform.
Provides touch-optimized POS interface and transaction management.
"""
from django.views.generic import TemplateView, ListView, DetailView, CreateView
from django.views import View
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal
import json

from django.db import models

from zargar.core.mixins import TenantContextMixin
from .models import POSTransaction, POSTransactionLineItem, POSInvoice, POSOfflineStorage
from .services import POSTransactionService, POSOfflineService, POSInvoiceService, POSReportingService
from zargar.jewelry.models import JewelryItem
from zargar.customers.models import Customer
from zargar.gold_installments.services import GoldPriceService


class POSTransactionListView(LoginRequiredMixin, TenantContextMixin, ListView):
    """List view for POS transactions."""
    
    model = POSTransaction
    template_name = 'pos/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20
    
    def get_queryset(self):
        """Get filtered queryset."""
        queryset = POSTransaction.objects.select_related('customer').order_by('-transaction_date')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(transaction_date__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(transaction_date__date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add additional context."""
        context = super().get_context_data(**kwargs)
        context['status_choices'] = POSTransaction.STATUS_CHOICES
        return context


class POSTransactionCreateView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """Create new POS transaction."""
    
    template_name = 'pos/transaction_create.html'
    
    def post(self, request, *args, **kwargs):
        """Handle transaction creation."""
        try:
            customer_id = request.POST.get('customer_id')
            transaction_type = request.POST.get('transaction_type', 'sale')
            payment_method = request.POST.get('payment_method', 'cash')
            
            transaction = POSTransactionService.create_transaction(
                customer_id=int(customer_id) if customer_id else None,
                transaction_type=transaction_type,
                payment_method=payment_method,
                user=request.user
            )
            
            messages.success(request, _('Transaction created successfully'))
            return redirect('pos:transaction_detail', transaction_id=transaction.transaction_id)
            
        except Exception as e:
            messages.error(request, f'Error creating transaction: {str(e)}')
            return self.get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """Add context for transaction creation."""
        context = super().get_context_data(**kwargs)
        context['customers'] = Customer.objects.filter(is_active=True)[:100]  # Limit for performance
        context['transaction_types'] = POSTransaction.TRANSACTION_TYPE_CHOICES
        context['payment_methods'] = POSTransaction.PAYMENT_METHOD_CHOICES
        return context


class POSTransactionDetailView(LoginRequiredMixin, TenantContextMixin, DetailView):
    """Detail view for POS transaction."""
    
    model = POSTransaction
    template_name = 'pos/transaction_detail.html'
    context_object_name = 'transaction'
    slug_field = 'transaction_id'
    slug_url_kwarg = 'transaction_id'
    
    def get_context_data(self, **kwargs):
        """Add additional context."""
        context = super().get_context_data(**kwargs)
        transaction = self.get_object()
        
        context['line_items'] = transaction.line_items.select_related('jewelry_item').all()
        context['can_edit'] = transaction.status == 'pending'
        context['current_gold_price'] = GoldPriceService.get_current_gold_price(18)
        
        return context


class POSTransactionCompleteView(LoginRequiredMixin, TenantContextMixin, View):
    """Complete POS transaction."""
    
    def post(self, request, transaction_id):
        """Handle transaction completion."""
        try:
            transaction = get_object_or_404(POSTransaction, transaction_id=transaction_id)
            
            amount_paid = Decimal(request.POST.get('amount_paid', '0'))
            payment_method = request.POST.get('payment_method', transaction.payment_method)
            reference_number = request.POST.get('reference_number', '')
            
            result = POSTransactionService.process_payment(
                transaction=transaction,
                amount_paid=amount_paid,
                payment_method=payment_method,
                reference_number=reference_number
            )
            
            if result['success']:
                messages.success(request, _('Transaction completed successfully'))
                return JsonResponse({
                    'success': True,
                    'change_amount': str(result['change_amount']),
                    'invoice_id': result['invoice'].id
                })
            else:
                return JsonResponse({'success': False, 'error': 'Payment processing failed'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class POSTransactionCancelView(LoginRequiredMixin, TenantContextMixin, View):
    """Cancel POS transaction."""
    
    def post(self, request, transaction_id):
        """Handle transaction cancellation."""
        try:
            transaction = get_object_or_404(POSTransaction, transaction_id=transaction_id)
            reason = request.POST.get('reason', '')
            
            result = POSTransactionService.cancel_transaction(
                transaction=transaction,
                reason=reason
            )
            
            if result['success']:
                messages.success(request, _('Transaction cancelled successfully'))
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Cancellation failed'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class AddJewelryItemView(LoginRequiredMixin, TenantContextMixin, View):
    """Add jewelry item to transaction."""
    
    def post(self, request, transaction_id):
        """Handle adding jewelry item."""
        try:
            transaction = get_object_or_404(POSTransaction, transaction_id=transaction_id)
            
            jewelry_item_id = int(request.POST.get('jewelry_item_id'))
            quantity = int(request.POST.get('quantity', 1))
            custom_price = request.POST.get('custom_price')
            discount_percentage = Decimal(request.POST.get('discount_percentage', '0'))
            
            custom_price = Decimal(custom_price) if custom_price else None
            
            line_item = POSTransactionService.add_jewelry_item_to_transaction(
                transaction=transaction,
                jewelry_item_id=jewelry_item_id,
                quantity=quantity,
                custom_price=custom_price,
                discount_percentage=discount_percentage
            )
            
            return JsonResponse({
                'success': True,
                'line_item_id': line_item.id,
                'subtotal': str(transaction.subtotal),
                'total_amount': str(transaction.total_amount)
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class AddCustomItemView(LoginRequiredMixin, TenantContextMixin, View):
    """Add custom item to transaction."""
    
    def post(self, request, transaction_id):
        """Handle adding custom item."""
        try:
            transaction = get_object_or_404(POSTransaction, transaction_id=transaction_id)
            
            item_name = request.POST.get('item_name')
            unit_price = Decimal(request.POST.get('unit_price'))
            quantity = int(request.POST.get('quantity', 1))
            item_sku = request.POST.get('item_sku', '')
            
            line_item = POSTransactionService.add_custom_item_to_transaction(
                transaction=transaction,
                item_name=item_name,
                unit_price=unit_price,
                quantity=quantity,
                item_sku=item_sku
            )
            
            return JsonResponse({
                'success': True,
                'line_item_id': line_item.id,
                'subtotal': str(transaction.subtotal),
                'total_amount': str(transaction.total_amount)
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class RemoveLineItemView(LoginRequiredMixin, TenantContextMixin, View):
    """Remove line item from transaction."""
    
    def post(self, request, transaction_id, line_item_id):
        """Handle removing line item."""
        try:
            transaction = get_object_or_404(POSTransaction, transaction_id=transaction_id)
            
            POSTransactionService.remove_line_item(
                transaction=transaction,
                line_item_id=line_item_id
            )
            
            return JsonResponse({
                'success': True,
                'subtotal': str(transaction.subtotal),
                'total_amount': str(transaction.total_amount)
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class POSInvoiceDetailView(LoginRequiredMixin, TenantContextMixin, DetailView):
    """Detail view for POS invoice."""
    
    model = POSInvoice
    template_name = 'pos/invoice_detail.html'
    context_object_name = 'invoice'
    pk_url_kwarg = 'invoice_id'


class POSInvoicePDFView(LoginRequiredMixin, TenantContextMixin, View):
    """Generate PDF invoice."""
    
    def get(self, request, invoice_id):
        """Generate and return PDF invoice."""
        try:
            invoice = get_object_or_404(POSInvoice, id=invoice_id)
            
            pdf_content = POSInvoiceService.generate_invoice_pdf(invoice)
            
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
            
            return response
            
        except Exception as e:
            messages.error(request, f'Error generating PDF: {str(e)}')
            return redirect('pos:invoice_detail', invoice_id=invoice_id)


class POSInvoiceEmailView(LoginRequiredMixin, TenantContextMixin, View):
    """Send invoice via email."""
    
    def post(self, request, invoice_id):
        """Handle sending invoice email."""
        try:
            invoice = get_object_or_404(POSInvoice, id=invoice_id)
            recipient_email = request.POST.get('recipient_email')
            
            if not recipient_email:
                return JsonResponse({'success': False, 'error': 'Email address required'})
            
            success = POSInvoiceService.send_invoice_email(
                invoice=invoice,
                recipient_email=recipient_email,
                include_pdf=True
            )
            
            if success:
                return JsonResponse({'success': True, 'message': 'Invoice sent successfully'})
            else:
                return JsonResponse({'success': False, 'error': 'Failed to send email'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class POSOfflineSyncView(LoginRequiredMixin, TenantContextMixin, View):
    """Sync offline POS transactions."""
    
    def post(self, request):
        """Handle offline transaction sync."""
        try:
            device_id = request.POST.get('device_id', '')
            
            sync_results = POSOfflineService.sync_offline_transactions(device_id=device_id)
            
            return JsonResponse({
                'success': True,
                'sync_results': sync_results
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class POSOfflineSyncStatusView(LoginRequiredMixin, TenantContextMixin, View):
    """Get offline sync status."""
    
    def get(self, request):
        """Get sync status summary."""
        try:
            device_id = request.GET.get('device_id', '')
            
            summary = POSOfflineService.get_offline_transaction_summary(device_id=device_id)
            
            return JsonResponse({
                'success': True,
                'summary': summary
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class POSDailySalesReportView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """Daily sales report view."""
    
    template_name = 'pos/daily_sales_report.html'
    
    def get_context_data(self, **kwargs):
        """Add report data to context."""
        context = super().get_context_data(**kwargs)
        
        date_str = self.request.GET.get('date')
        if date_str:
            from datetime import datetime
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date = timezone.now().date()
        
        context['report_date'] = date
        context['sales_summary'] = POSReportingService.get_daily_sales_summary(date=date)
        
        return context


class POSMonthlySalesReportView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """Monthly sales report view."""
    
    template_name = 'pos/monthly_sales_report.html'
    
    def get_context_data(self, **kwargs):
        """Add report data to context."""
        context = super().get_context_data(**kwargs)
        
        year = int(self.request.GET.get('year', timezone.now().year))
        month = int(self.request.GET.get('month', timezone.now().month))
        
        context['report_year'] = year
        context['report_month'] = month
        context['sales_trend'] = POSReportingService.get_monthly_sales_trend(year, month)
        
        return context


# API Views for AJAX/Mobile Integration

class CurrentGoldPriceAPIView(LoginRequiredMixin, TenantContextMixin, View):
    """API endpoint for current gold price."""
    
    def get(self, request):
        """Get current gold price."""
        try:
            karat = int(request.GET.get('karat', 18))
            price_data = GoldPriceService.get_current_gold_price(karat)
            
            return JsonResponse({
                'success': True,
                'price_data': {
                    'price_per_gram': str(price_data['price_per_gram']),
                    'karat': price_data['karat'],
                    'timestamp': price_data['timestamp'].isoformat(),
                    'source': price_data['source']
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class CustomerLookupAPIView(LoginRequiredMixin, TenantContextMixin, View):
    """API endpoint for customer lookup."""
    
    def get(self, request):
        """Search customers."""
        try:
            query = request.GET.get('q', '')
            
            if len(query) < 2:
                return JsonResponse({'success': True, 'customers': []})
            
            customers = Customer.objects.filter(
                models.Q(first_name__icontains=query) |
                models.Q(last_name__icontains=query) |
                models.Q(persian_first_name__icontains=query) |
                models.Q(persian_last_name__icontains=query) |
                models.Q(phone_number__icontains=query)
            )[:10]
            
            customer_data = []
            for customer in customers:
                customer_data.append({
                    'id': customer.id,
                    'name': str(customer),
                    'phone': customer.phone_number,
                    'email': customer.email or '',
                    'loyalty_points': customer.loyalty_points
                })
            
            return JsonResponse({
                'success': True,
                'customers': customer_data
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class JewelryItemSearchAPIView(LoginRequiredMixin, TenantContextMixin, View):
    """API endpoint for jewelry item search."""
    
    def get(self, request):
        """Search jewelry items."""
        try:
            query = request.GET.get('q', '')
            
            if len(query) < 2:
                return JsonResponse({'success': True, 'items': []})
            
            items = JewelryItem.objects.filter(
                models.Q(name__icontains=query) |
                models.Q(sku__icontains=query),
                status='in_stock',
                quantity__gt=0
            ).select_related('category')[:20]
            
            item_data = []
            for item in items:
                item_data.append({
                    'id': item.id,
                    'name': item.name,
                    'sku': item.sku,
                    'category': item.category.name_persian if item.category else '',
                    'weight_grams': str(item.weight_grams),
                    'karat': item.karat,
                    'selling_price': str(item.selling_price or 0),
                    'quantity': item.quantity
                })
            
            return JsonResponse({
                'success': True,
                'items': item_data
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class PlaceholderView(TemplateView):
    """
    Placeholder view for POS module (backward compatibility).
    """
    def get(self, request, *args, **kwargs):
        return JsonResponse({
            'module': 'pos',
            'status': 'placeholder',
            'message': 'POS module will be implemented in later tasks'
        })