"""
Billing and subscription management views for admin super-panel.
Handles subscription plans, invoices, and billing workflows with Persian UI.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.db import transaction
from django.core.paginator import Paginator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q, Count, Sum
import jdatetime
from decimal import Decimal
import json

from .admin_models import SubscriptionPlan, TenantInvoice, BillingCycle, TenantAccessLog
from .models import Tenant
from .billing_services import SubscriptionManager, InvoiceGenerator, BillingWorkflow
from zargar.admin_panel.views import SuperAdminRequiredMixin


class BillingDashboardView(SuperAdminRequiredMixin, TemplateView):
    """
    Main billing dashboard with overview of subscriptions, invoices, and revenue.
    """
    template_name = 'admin/billing/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Current Persian date
        current_shamsi = jdatetime.date.today()
        current_month_start = current_shamsi.replace(day=1)
        
        # Revenue statistics
        current_month_revenue = TenantInvoice.objects.filter(
            status='paid',
            payment_date_shamsi__gte=current_month_start.togregorian()
        ).aggregate(total=Sum('total_amount_toman'))['total'] or Decimal('0')
        
        # Invoice statistics
        total_invoices = TenantInvoice.objects.count()
        pending_invoices = TenantInvoice.objects.filter(status='pending').count()
        overdue_invoices = TenantInvoice.objects.filter(status='overdue').count()
        paid_invoices = TenantInvoice.objects.filter(status='paid').count()
        
        # Subscription plan distribution
        plan_distribution = SubscriptionPlan.objects.annotate(
            tenant_count=Count('tenant_set')
        ).values('name_persian', 'tenant_count', 'monthly_price_toman')
        
        # Recent invoices
        recent_invoices = TenantInvoice.objects.select_related(
            'tenant', 'subscription_plan'
        ).order_by('-created_at')[:10]
        
        # Overdue invoices requiring attention
        overdue_invoices_list = TenantInvoice.objects.filter(
            status='overdue'
        ).select_related('tenant', 'subscription_plan').order_by('due_date_shamsi')[:5]
        
        # Monthly revenue trend (last 6 months)
        revenue_trend = []
        for i in range(6):
            month_date = current_shamsi.replace(day=1)
            if month_date.month - i <= 0:
                month_date = month_date.replace(
                    year=month_date.year - 1,
                    month=12 + (month_date.month - i)
                )
            else:
                month_date = month_date.replace(month=month_date.month - i)
            
            month_revenue = TenantInvoice.objects.filter(
                status='paid',
                payment_date_shamsi__year=month_date.year,
                payment_date_shamsi__month=month_date.month
            ).aggregate(total=Sum('total_amount_toman'))['total'] or Decimal('0')
            
            revenue_trend.append({
                'month': month_date.strftime('%B %Y'),
                'month_persian': month_date.strftime('%B %Y'),  # Would need Persian month names
                'revenue': float(month_revenue)
            })
        
        context.update({
            'current_shamsi': current_shamsi,
            'current_month_revenue': current_month_revenue,
            'total_invoices': total_invoices,
            'pending_invoices': pending_invoices,
            'overdue_invoices': overdue_invoices,
            'paid_invoices': paid_invoices,
            'plan_distribution': plan_distribution,
            'recent_invoices': recent_invoices,
            'overdue_invoices_list': overdue_invoices_list,
            'revenue_trend': list(reversed(revenue_trend)),
        })
        
        return context


class SubscriptionPlanListView(SuperAdminRequiredMixin, ListView):
    """
    List all subscription plans with management options.
    """
    model = SubscriptionPlan
    template_name = 'admin/billing/subscription_plans.html'
    context_object_name = 'plans'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = SubscriptionPlan.objects.annotate(
            tenant_count=Count('tenant_set')
        ).order_by('monthly_price_toman')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(name_persian__icontains=search) |
                Q(plan_type__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'search_query': self.request.GET.get('search', ''),
            'status_filter': self.request.GET.get('status', ''),
        })
        return context


class SubscriptionPlanCreateView(SuperAdminRequiredMixin, CreateView):
    """
    Create new subscription plan.
    """
    model = SubscriptionPlan
    template_name = 'admin/billing/subscription_plan_form.html'
    fields = [
        'name', 'name_persian', 'plan_type', 'monthly_price_toman', 'yearly_price_toman',
        'max_users', 'max_inventory_items', 'max_customers', 'max_monthly_transactions',
        'max_storage_gb', 'features', 'is_active', 'is_popular'
    ]
    success_url = reverse_lazy('core:tenants:billing:subscription_plans')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        # Log plan creation
        response = super().form_valid(form)
        
        TenantAccessLog.log_action(
            user=self.request.user,
            tenant_schema='public',
            action='create',
            model_name='SubscriptionPlan',
            object_id=str(self.object.id),
            details={
                'action': 'subscription_plan_created',
                'plan_name': self.object.name_persian,
                'plan_type': self.object.plan_type,
                'monthly_price': str(self.object.monthly_price_toman)
            }
        )
        
        messages.success(self.request, f'پلن اشتراک "{self.object.name_persian}" با موفقیت ایجاد شد.')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'ایجاد پلن اشتراک جدید'
        context['form_action'] = 'create'
        return context


class SubscriptionPlanUpdateView(SuperAdminRequiredMixin, UpdateView):
    """
    Update existing subscription plan.
    """
    model = SubscriptionPlan
    template_name = 'admin/billing/subscription_plan_form.html'
    fields = [
        'name', 'name_persian', 'monthly_price_toman', 'yearly_price_toman',
        'max_users', 'max_inventory_items', 'max_customers', 'max_monthly_transactions',
        'max_storage_gb', 'features', 'is_active', 'is_popular'
    ]
    success_url = reverse_lazy('core:tenants:billing:subscription_plans')
    
    def form_valid(self, form):
        # Log plan update
        old_values = {
            'name_persian': self.object.name_persian,
            'monthly_price': str(self.object.monthly_price_toman),
            'is_active': self.object.is_active
        }
        
        response = super().form_valid(form)
        
        TenantAccessLog.log_action(
            user=self.request.user,
            tenant_schema='public',
            action='update',
            model_name='SubscriptionPlan',
            object_id=str(self.object.id),
            details={
                'action': 'subscription_plan_updated',
                'plan_name': self.object.name_persian,
                'old_values': old_values,
                'new_values': {
                    'name_persian': self.object.name_persian,
                    'monthly_price': str(self.object.monthly_price_toman),
                    'is_active': self.object.is_active
                }
            }
        )
        
        messages.success(self.request, f'پلن اشتراک "{self.object.name_persian}" با موفقیت به‌روزرسانی شد.')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'ویرایش پلن اشتراک: {self.object.name_persian}'
        context['form_action'] = 'update'
        return context


class SubscriptionPlanDeleteView(SuperAdminRequiredMixin, DeleteView):
    """
    Delete subscription plan (with safety checks).
    """
    model = SubscriptionPlan
    template_name = 'admin/billing/subscription_plan_confirm_delete.html'
    success_url = reverse_lazy('core:tenants:billing:subscription_plans')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Check if plan is in use
        tenant_count = self.object.tenant_set.count()
        if tenant_count > 0:
            messages.error(
                request, 
                f'نمی‌توان پلن "{self.object.name_persian}" را حذف کرد زیرا {tenant_count} تنانت از آن استفاده می‌کنند.'
            )
            return redirect(self.success_url)
        
        # Log deletion
        TenantAccessLog.log_action(
            user=request.user,
            tenant_schema='public',
            action='delete',
            model_name='SubscriptionPlan',
            object_id=str(self.object.id),
            details={
                'action': 'subscription_plan_deleted',
                'plan_name': self.object.name_persian,
                'plan_type': self.object.plan_type
            }
        )
        
        messages.success(request, f'پلن اشتراک "{self.object.name_persian}" با موفقیت حذف شد.')
        return super().delete(request, *args, **kwargs)


class InvoiceListView(SuperAdminRequiredMixin, ListView):
    """
    List all tenant invoices with filtering and search.
    """
    model = TenantInvoice
    template_name = 'admin/billing/invoices.html'
    context_object_name = 'invoices'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = TenantInvoice.objects.select_related(
            'tenant', 'subscription_plan', 'created_by'
        ).order_by('-created_at')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search) |
                Q(tenant__name__icontains=search) |
                Q(tenant__domain_url__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by tenant
        tenant_id = self.request.GET.get('tenant')
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(issue_date_shamsi__gte=date_from)
        if date_to:
            queryset = queryset.filter(issue_date_shamsi__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter options
        tenants = Tenant.objects.exclude(schema_name='public').values('id', 'name')
        status_choices = TenantInvoice.INVOICE_STATUS
        
        # Calculate totals for current filter
        current_queryset = self.get_queryset()
        totals = current_queryset.aggregate(
            total_amount=Sum('total_amount_toman'),
            count=Count('id')
        )
        
        context.update({
            'search_query': self.request.GET.get('search', ''),
            'status_filter': self.request.GET.get('status', ''),
            'tenant_filter': self.request.GET.get('tenant', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'tenants': tenants,
            'status_choices': status_choices,
            'totals': totals,
        })
        
        return context


class InvoiceDetailView(SuperAdminRequiredMixin, DetailView):
    """
    View invoice details with payment processing options.
    """
    model = TenantInvoice
    template_name = 'admin/billing/invoice_detail.html'
    context_object_name = 'invoice'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Payment method choices for manual processing
        context['payment_methods'] = TenantInvoice.PAYMENT_METHODS
        
        # Related invoices for this tenant
        related_invoices = TenantInvoice.objects.filter(
            tenant=self.object.tenant
        ).exclude(id=self.object.id).order_by('-created_at')[:5]
        
        context['related_invoices'] = related_invoices
        
        return context


class InvoiceCreateView(SuperAdminRequiredMixin, View):
    """
    Create new invoice for a tenant.
    """
    
    def get(self, request):
        """Show invoice creation form."""
        tenants = Tenant.objects.exclude(schema_name='public').filter(is_active=True)
        subscription_plans = SubscriptionPlan.objects.filter(is_active=True)
        
        context = {
            'tenants': tenants,
            'subscription_plans': subscription_plans,
            'page_title': 'ایجاد فاکتور جدید'
        }
        
        return render(request, 'admin/billing/invoice_create.html', context)
    
    def post(self, request):
        """Process invoice creation."""
        try:
            tenant_id = request.POST.get('tenant')
            billing_type = request.POST.get('billing_type')  # monthly or yearly
            custom_amount = request.POST.get('custom_amount')
            notes = request.POST.get('notes', '')
            
            tenant = get_object_or_404(Tenant, id=tenant_id)
            
            if billing_type == 'monthly':
                invoice = InvoiceGenerator.generate_monthly_invoice(
                    tenant=tenant,
                    admin_user=request.user
                )
            elif billing_type == 'yearly':
                invoice = InvoiceGenerator.generate_yearly_invoice(
                    tenant=tenant,
                    admin_user=request.user
                )
            elif billing_type == 'custom' and custom_amount:
                # Create custom invoice
                invoice = TenantInvoice.objects.create(
                    tenant=tenant,
                    subscription_plan=tenant.subscription_plan_fk,
                    issue_date_shamsi=jdatetime.date.today().togregorian(),
                    due_date_shamsi=(jdatetime.date.today() + jdatetime.timedelta(days=30)).togregorian(),
                    billing_period_start=jdatetime.date.today().togregorian(),
                    billing_period_end=jdatetime.date.today().togregorian(),
                    subtotal_toman=Decimal(custom_amount),
                    created_by=request.user,
                    notes=notes,
                    line_items=[{
                        'description': 'فاکتور سفارشی',
                        'description_english': 'Custom Invoice',
                        'quantity': 1,
                        'unit_price': custom_amount,
                        'total_price': custom_amount
                    }]
                )
            else:
                messages.error(request, 'اطلاعات فاکتور نامعتبر است.')
                return redirect('core:tenants:billing:invoice_create')
            
            messages.success(request, f'فاکتور {invoice.invoice_number} با موفقیت ایجاد شد.')
            return redirect('core:tenants:billing:invoice_detail', pk=invoice.pk)
            
        except Exception as e:
            messages.error(request, f'خطا در ایجاد فاکتور: {str(e)}')
            return redirect('core:tenants:billing:invoice_create')


class InvoicePaymentProcessView(SuperAdminRequiredMixin, View):
    """
    Process manual payment for an invoice.
    """
    
    def post(self, request, pk):
        """Process payment for invoice."""
        invoice = get_object_or_404(TenantInvoice, pk=pk)
        
        if invoice.status == 'paid':
            return JsonResponse({
                'success': False,
                'message': 'این فاکتور قبلاً پرداخت شده است.'
            })
        
        try:
            payment_method = request.POST.get('payment_method')
            payment_reference = request.POST.get('payment_reference', '')
            payment_date = request.POST.get('payment_date')
            
            # Convert Persian date if provided
            if payment_date:
                try:
                    # Assuming payment_date is in Persian format YYYY/MM/DD
                    payment_date_shamsi = jdatetime.datetime.strptime(payment_date, '%Y/%m/%d').date()
                except:
                    payment_date_shamsi = jdatetime.date.today()
            else:
                payment_date_shamsi = jdatetime.date.today()
            
            # Process payment
            BillingWorkflow.manual_payment_processing(
                invoice=invoice,
                payment_method=payment_method,
                payment_reference=payment_reference,
                admin_user=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': f'پرداخت فاکتور {invoice.invoice_number} با موفقیت ثبت شد.',
                'invoice_status': invoice.get_status_display(),
                'payment_date': payment_date_shamsi.strftime('%Y/%m/%d')
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'خطا در پردازش پرداخت: {str(e)}'
            })


class BillingReportsView(SuperAdminRequiredMixin, TemplateView):
    """
    Generate and display billing reports.
    """
    template_name = 'admin/billing/reports.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Current Persian date
        current_shamsi = jdatetime.date.today()
        current_year = current_shamsi.year
        current_month = current_shamsi.month
        
        # Monthly revenue report
        monthly_revenue = []
        for month in range(1, 13):
            month_revenue = TenantInvoice.objects.filter(
                status='paid',
                payment_date_shamsi__year=current_year,
                payment_date_shamsi__month=month
            ).aggregate(total=Sum('total_amount_toman'))['total'] or Decimal('0')
            
            monthly_revenue.append({
                'month': month,
                'month_name': jdatetime.date(current_year, month, 1).strftime('%B'),
                'revenue': float(month_revenue)
            })
        
        # Subscription plan performance
        plan_performance = SubscriptionPlan.objects.annotate(
            active_tenants=Count('tenant_set', filter=Q(tenant_set__is_active=True)),
            total_revenue=Sum('tenantinvoice__total_amount_toman', filter=Q(tenantinvoice__status='paid'))
        ).values(
            'name_persian', 'active_tenants', 'total_revenue', 'monthly_price_toman'
        )
        
        # Payment method distribution
        payment_methods = TenantInvoice.objects.filter(
            status='paid'
        ).values('payment_method').annotate(
            count=Count('id'),
            total_amount=Sum('total_amount_toman')
        ).order_by('-total_amount')
        
        # Outstanding invoices by age
        overdue_analysis = []
        for days in [7, 30, 60, 90]:
            cutoff_date = (current_shamsi - jdatetime.timedelta(days=days)).togregorian()
            count = TenantInvoice.objects.filter(
                status='overdue',
                due_date_shamsi__lte=cutoff_date
            ).count()
            overdue_analysis.append({
                'days': days,
                'count': count
            })
        
        context.update({
            'current_shamsi': current_shamsi,
            'monthly_revenue': monthly_revenue,
            'plan_performance': plan_performance,
            'payment_methods': payment_methods,
            'overdue_analysis': overdue_analysis,
        })
        
        return context


class BulkInvoiceGenerationView(SuperAdminRequiredMixin, View):
    """
    Generate invoices in bulk for all active tenants.
    """
    
    def get(self, request):
        """Show bulk generation form."""
        active_tenants = Tenant.objects.exclude(schema_name='public').filter(is_active=True)
        
        context = {
            'active_tenants': active_tenants,
            'page_title': 'تولید انبوه فاکتور'
        }
        
        return render(request, 'admin/billing/bulk_invoice_generation.html', context)
    
    def post(self, request):
        """Process bulk invoice generation."""
        try:
            billing_type = request.POST.get('billing_type')  # monthly or yearly
            selected_tenants = request.POST.getlist('tenants')
            
            if not selected_tenants:
                messages.error(request, 'لطفاً حداقل یک تنانت انتخاب کنید.')
                return redirect('core:tenants:billing:bulk_invoice_generation')
            
            generated_count = 0
            errors = []
            
            for tenant_id in selected_tenants:
                try:
                    tenant = Tenant.objects.get(id=tenant_id)
                    
                    if billing_type == 'monthly':
                        invoice = InvoiceGenerator.generate_monthly_invoice(
                            tenant=tenant,
                            admin_user=request.user
                        )
                    elif billing_type == 'yearly':
                        invoice = InvoiceGenerator.generate_yearly_invoice(
                            tenant=tenant,
                            admin_user=request.user
                        )
                    
                    generated_count += 1
                    
                except Exception as e:
                    errors.append(f'{tenant.name}: {str(e)}')
            
            if generated_count > 0:
                messages.success(request, f'{generated_count} فاکتور با موفقیت تولید شد.')
            
            if errors:
                messages.warning(request, f'خطا در تولید برخی فاکتورها: {", ".join(errors)}')
            
            return redirect('core:tenants:billing:invoices')
            
        except Exception as e:
            messages.error(request, f'خطا در تولید انبوه فاکتور: {str(e)}')
            return redirect('core:tenants:billing:bulk_invoice_generation')


class BillingSettingsView(SuperAdminRequiredMixin, TemplateView):
    """
    Manage billing system settings and configurations.
    """
    template_name = 'admin/billing/settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Billing cycles summary
        billing_cycles = BillingCycle.objects.select_related('tenant').filter(
            is_active=True
        ).order_by('next_billing_date')
        
        # System settings (would be stored in a settings model)
        context.update({
            'billing_cycles': billing_cycles,
            'default_tax_rate': Decimal('9.00'),  # Iranian VAT
            'default_grace_period': 7,
            'auto_suspend_enabled': True,
        })
        
        return context