"""
Layaway and installment plan views for zargar project.
"""
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, UpdateView, FormView
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from django.forms import ModelForm, Form
from django import forms
from datetime import datetime, timedelta, date
from decimal import Decimal
import json

from zargar.core.mixins import TenantContextMixin
from zargar.jewelry.models import JewelryItem
from .models import Customer
from .layaway_models import (
    LayawayPlan, LayawayScheduledPayment, LayawayPayment, 
    LayawayRefund, LayawayContract, LayawayReminder
)
from .layaway_services import (
    LayawayPlanService, LayawayReminderService, LayawayContractService, LayawayReportService
)


class LayawayPlanForm(ModelForm):
    """Form for creating layaway plans."""
    
    class Meta:
        model = LayawayPlan
        fields = [
            'customer', 'jewelry_item', 'total_amount', 'down_payment',
            'payment_frequency', 'number_of_payments', 'start_date',
            'grace_period_days', 'notes'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3})
        }
    
    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        
        if tenant:
            # Filter customers and jewelry items by tenant
            self.fields['customer'].queryset = Customer.objects.filter(
                tenant=tenant, is_active=True
            ).order_by('persian_first_name', 'first_name')
            
            self.fields['jewelry_item'].queryset = JewelryItem.objects.filter(
                tenant=tenant, status__in=['in_stock', 'reserved']
            ).order_by('name')
        
        # Add Persian labels
        self.fields['customer'].label = 'مشتری'
        self.fields['jewelry_item'].label = 'کالای طلا و جواهر'
        self.fields['total_amount'].label = 'مبلغ کل (تومان)'
        self.fields['down_payment'].label = 'پیش پرداخت (تومان)'
        self.fields['payment_frequency'].label = 'دوره پرداخت'
        self.fields['number_of_payments'].label = 'تعداد اقساط'
        self.fields['start_date'].label = 'تاریخ شروع'
        self.fields['grace_period_days'].label = 'مهلت نسیه (روز)'
        self.fields['notes'].label = 'یادداشت‌ها'
        
        # Add CSS classes
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class LayawayPaymentForm(ModelForm):
    """Form for processing layaway payments."""
    
    class Meta:
        model = LayawayPayment
        fields = ['amount', 'payment_method', 'reference_number', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Persian labels
        self.fields['amount'].label = 'مبلغ پرداخت (تومان)'
        self.fields['payment_method'].label = 'روش پرداخت'
        self.fields['reference_number'].label = 'شماره مرجع'
        self.fields['notes'].label = 'یادداشت'
        
        # Add CSS classes
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class LayawayDashboardView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Main layaway management dashboard with payment tracking and status updates.
    """
    template_name = 'customers/layaway_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get layaway summary statistics
        summary = LayawayReportService.get_layaway_summary()
        
        # Get active layaway plans
        active_plans = LayawayPlan.objects.filter(
            tenant=self.request.tenant,
            status='active'
        ).select_related('customer', 'jewelry_item').order_by('-created_at')[:10]
        
        # Get overdue plans
        overdue_plans = LayawayPlanService.get_overdue_plans()[:5]
        
        # Get upcoming payments (next 7 days)
        upcoming_payments = LayawayPlanService.get_upcoming_payments(days_ahead=7)
        
        # Get recent payments
        recent_payments = LayawayPayment.objects.filter(
            layaway_plan__tenant=self.request.tenant
        ).select_related('layaway_plan', 'layaway_plan__customer').order_by('-payment_date')[:10]
        
        # Get completion statistics by month
        monthly_stats = []
        for i in range(6):  # Last 6 months
            month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
            month_end = month_start.replace(day=28) + timedelta(days=4)
            month_end = month_end - timedelta(days=month_end.day)
            
            completed_count = LayawayPlan.objects.filter(
                tenant=self.request.tenant,
                status='completed',
                actual_completion_date__gte=month_start.date(),
                actual_completion_date__lte=month_end.date()
            ).count()
            
            monthly_stats.append({
                'month': month_start.strftime('%Y/%m'),
                'completed': completed_count
            })
        
        context.update({
            'summary': summary,
            'active_plans': active_plans,
            'overdue_plans': overdue_plans,
            'upcoming_payments': upcoming_payments,
            'recent_payments': recent_payments,
            'monthly_stats': list(reversed(monthly_stats))
        })
        
        return context


class LayawayPlanListView(LoginRequiredMixin, TenantContextMixin, ListView):
    """
    List view for all layaway plans with filtering and search.
    """
    model = LayawayPlan
    template_name = 'customers/layaway_plan_list.html'
    context_object_name = 'plans'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = LayawayPlan.objects.filter(
            tenant=self.request.tenant
        ).select_related('customer', 'jewelry_item').order_by('-created_at')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by customer
        customer_id = self.request.GET.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        # Search by plan number or customer name
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(plan_number__icontains=search) |
                Q(customer__persian_first_name__icontains=search) |
                Q(customer__persian_last_name__icontains=search) |
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search)
            )
        
        # Filter by overdue status
        overdue = self.request.GET.get('overdue')
        if overdue == 'true':
            # Get plans with overdue payments
            overdue_plan_ids = []
            for plan in queryset.filter(status='active'):
                if plan.is_overdue:
                    overdue_plan_ids.append(plan.id)
            queryset = queryset.filter(id__in=overdue_plan_ids)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter options
        context['status_choices'] = LayawayPlan.STATUS_CHOICES
        context['customers'] = Customer.objects.filter(
            tenant=self.request.tenant,
            is_active=True
        ).order_by('persian_first_name', 'first_name')
        
        # Get current filters
        context['current_filters'] = {
            'status': self.request.GET.get('status', ''),
            'customer': self.request.GET.get('customer', ''),
            'search': self.request.GET.get('search', ''),
            'overdue': self.request.GET.get('overdue', '')
        }
        
        return context


class LayawayPlanCreateView(LoginRequiredMixin, TenantContextMixin, CreateView):
    """
    Create new layaway plan with payment term configuration.
    """
    model = LayawayPlan
    form_class = LayawayPlanForm
    template_name = 'customers/layaway_plan_create.html'
    success_url = reverse_lazy('customers:layaway_dashboard')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs
    
    def form_valid(self, form):
        try:
            # Create layaway plan using service
            plan = LayawayPlanService.create_layaway_plan(
                customer=form.cleaned_data['customer'],
                jewelry_item=form.cleaned_data['jewelry_item'],
                total_amount=form.cleaned_data['total_amount'],
                down_payment=form.cleaned_data['down_payment'],
                payment_frequency=form.cleaned_data['payment_frequency'],
                number_of_payments=form.cleaned_data['number_of_payments'],
                start_date=form.cleaned_data['start_date'],
                notes=form.cleaned_data['notes']
            )
            
            messages.success(
                self.request,
                f'قرارداد طلای قرضی {plan.plan_number} با موفقیت ایجاد شد.'
            )
            
            return redirect('customers:layaway_detail', pk=plan.pk)
            
        except Exception as e:
            messages.error(self.request, f'خطا در ایجاد قرارداد: {str(e)}')
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get available jewelry items
        context['jewelry_items'] = JewelryItem.objects.filter(
            tenant=self.request.tenant,
            status__in=['in_stock', 'reserved']
        ).order_by('name')
        
        # Get active customers
        context['customers'] = Customer.objects.filter(
            tenant=self.request.tenant,
            is_active=True
        ).order_by('persian_first_name', 'first_name')
        
        # Get contract templates
        context['contract_templates'] = LayawayContract.objects.filter(
            tenant=self.request.tenant,
            is_active=True
        ).order_by('name')
        
        return context


class LayawayPlanDetailView(LoginRequiredMixin, TenantContextMixin, DetailView):
    """
    Detailed view of layaway plan with payment history and management options.
    """
    model = LayawayPlan
    template_name = 'customers/layaway_plan_detail.html'
    context_object_name = 'plan'
    
    def get_queryset(self):
        return LayawayPlan.objects.filter(tenant=self.request.tenant)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan = self.get_object()
        
        # Get plan statistics
        context['statistics'] = LayawayPlanService.calculate_plan_statistics(plan)
        
        # Get scheduled payments
        context['scheduled_payments'] = plan.scheduled_payments.all().order_by('due_date')
        
        # Get payment history
        context['payment_history'] = plan.payments.all().order_by('-payment_date')
        
        # Get reminders
        context['reminders'] = plan.reminders.all().order_by('-scheduled_date')[:10]
        
        # Get payment form for processing new payments
        context['payment_form'] = LayawayPaymentForm()
        
        # Check if plan can be modified
        context['can_modify'] = plan.status == 'active'
        context['can_cancel'] = plan.status in ['active', 'on_hold']
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle payment processing and plan modifications."""
        plan = self.get_object()
        action = request.POST.get('action')
        
        if action == 'process_payment':
            return self.process_payment(request, plan)
        elif action == 'cancel_plan':
            return self.cancel_plan(request, plan)
        elif action == 'put_on_hold':
            return self.put_on_hold(request, plan)
        elif action == 'reactivate_plan':
            return self.reactivate_plan(request, plan)
        
        return redirect('customers:layaway_detail', pk=plan.pk)
    
    def process_payment(self, request, plan):
        """Process a payment for the layaway plan."""
        form = LayawayPaymentForm(request.POST)
        
        if form.is_valid():
            try:
                payment = LayawayPlanService.process_payment(
                    plan=plan,
                    amount=form.cleaned_data['amount'],
                    payment_method=form.cleaned_data['payment_method'],
                    notes=form.cleaned_data['notes'],
                    reference_number=form.cleaned_data['reference_number']
                )
                
                messages.success(
                    request,
                    f'پرداخت {payment.amount} تومان با موفقیت ثبت شد.'
                )
                
                # Check if plan is completed
                if plan.status == 'completed':
                    messages.success(
                        request,
                        'تبریک! قرارداد طلای قرضی تکمیل شد.'
                    )
                
            except Exception as e:
                messages.error(request, f'خطا در پردازش پرداخت: {str(e)}')
        else:
            messages.error(request, 'لطفاً اطلاعات پرداخت را صحیح وارد کنید.')
        
        return redirect('customers:layaway_detail', pk=plan.pk)
    
    def cancel_plan(self, request, plan):
        """Cancel the layaway plan."""
        reason = request.POST.get('cancel_reason', '')
        refund_percentage = Decimal(request.POST.get('refund_percentage', '90'))
        
        try:
            refund = LayawayPlanService.cancel_plan(
                plan=plan,
                reason=reason,
                refund_percentage=refund_percentage,
                processed_by=request.user
            )
            
            if refund:
                messages.success(
                    request,
                    f'قرارداد لغو شد. مبلغ بازگشتی: {refund.refund_amount} تومان'
                )
            else:
                messages.success(request, 'قرارداد با موفقیت لغو شد.')
                
        except Exception as e:
            messages.error(request, f'خطا در لغو قرارداد: {str(e)}')
        
        return redirect('customers:layaway_detail', pk=plan.pk)
    
    def put_on_hold(self, request, plan):
        """Put the plan on hold."""
        reason = request.POST.get('hold_reason', '')
        
        try:
            plan.put_on_hold(reason)
            messages.success(request, 'قرارداد به حالت تعلیق درآمد.')
        except Exception as e:
            messages.error(request, f'خطا در تعلیق قرارداد: {str(e)}')
        
        return redirect('customers:layaway_detail', pk=plan.pk)
    
    def reactivate_plan(self, request, plan):
        """Reactivate a plan that was on hold."""
        reason = request.POST.get('reactivate_reason', '')
        
        try:
            plan.reactivate_plan(reason)
            messages.success(request, 'قرارداد مجدداً فعال شد.')
        except Exception as e:
            messages.error(request, f'خطا در فعال‌سازی قرارداد: {str(e)}')
        
        return redirect('customers:layaway_detail', pk=plan.pk)


class LayawayReminderManagementView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Payment reminder interface with Persian templates.
    """
    template_name = 'customers/layaway_reminders.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get upcoming reminders
        upcoming_reminders = LayawayReminder.objects.filter(
            layaway_plan__tenant=self.request.tenant,
            scheduled_date__gte=timezone.now().date(),
            is_sent=False
        ).select_related('layaway_plan', 'layaway_plan__customer').order_by('scheduled_date')[:20]
        
        # Get recent reminders
        recent_reminders = LayawayReminder.objects.filter(
            layaway_plan__tenant=self.request.tenant,
            is_sent=True
        ).select_related('layaway_plan', 'layaway_plan__customer').order_by('-sent_date')[:10]
        
        # Get overdue plans that need reminders
        overdue_plans = LayawayPlanService.get_overdue_plans()
        
        # Get reminder statistics
        reminder_stats = LayawayReminder.objects.filter(
            layaway_plan__tenant=self.request.tenant,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).aggregate(
            total_reminders=Count('id'),
            sent_reminders=Count('id', filter=Q(is_sent=True)),
            pending_reminders=Count('id', filter=Q(is_sent=False))
        )
        
        # Calculate delivery success rate
        total_reminders = reminder_stats['total_reminders'] or 1
        success_rate = (reminder_stats['sent_reminders'] / total_reminders) * 100
        
        context.update({
            'upcoming_reminders': upcoming_reminders,
            'recent_reminders': recent_reminders,
            'overdue_plans': overdue_plans,
            'reminder_stats': reminder_stats,
            'success_rate': round(success_rate, 1)
        })
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle reminder actions."""
        action = request.POST.get('action')
        
        if action == 'send_upcoming_reminders':
            return self.send_upcoming_reminders(request)
        elif action == 'send_overdue_reminders':
            return self.send_overdue_reminders(request)
        elif action == 'create_custom_reminder':
            return self.create_custom_reminder(request)
        
        return redirect('customers:layaway_reminders')
    
    def send_upcoming_reminders(self, request):
        """Send all pending upcoming reminders."""
        try:
            sent_count = LayawayReminderService.send_upcoming_reminders()
            messages.success(
                request,
                f'{sent_count} یادآوری پرداخت ارسال شد.'
            )
        except Exception as e:
            messages.error(request, f'خطا در ارسال یادآوری‌ها: {str(e)}')
        
        return redirect('customers:layaway_reminders')
    
    def send_overdue_reminders(self, request):
        """Send reminders for overdue payments."""
        try:
            sent_count = LayawayReminderService.send_overdue_reminders()
            messages.success(
                request,
                f'{sent_count} یادآوری معوقات ارسال شد.'
            )
        except Exception as e:
            messages.error(request, f'خطا در ارسال یادآوری معوقات: {str(e)}')
        
        return redirect('customers:layaway_reminders')
    
    def create_custom_reminder(self, request):
        """Create a custom reminder for a specific plan."""
        try:
            plan_id = request.POST.get('plan_id')
            reminder_type = request.POST.get('reminder_type')
            delivery_method = request.POST.get('delivery_method')
            custom_message = request.POST.get('custom_message')
            
            plan = get_object_or_404(LayawayPlan, id=plan_id, tenant=request.tenant)
            
            # Create custom reminder
            reminder = LayawayReminder.objects.create(
                layaway_plan=plan,
                reminder_type=reminder_type,
                scheduled_date=timezone.now().date(),
                delivery_method=delivery_method,
                recipient=plan.customer.phone_number if delivery_method == 'sms' else plan.customer.email,
                message_template=custom_message,
                personalized_message=custom_message
            )
            
            # Send immediately
            if reminder.send_reminder():
                messages.success(
                    request,
                    f'یادآوری سفارشی برای {plan.customer.full_persian_name} ارسال شد.'
                )
            else:
                messages.error(request, 'خطا در ارسال یادآوری سفارشی.')
                
        except Exception as e:
            messages.error(request, f'خطا در ایجاد یادآوری: {str(e)}')
        
        return redirect('customers:layaway_reminders')


class LayawayReportsView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Layaway reports and analytics view.
    """
    template_name = 'customers/layaway_reports.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range from request
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get layaway summary
        summary = LayawayReportService.get_layaway_summary(start_date, end_date)
        
        # Get top customers by layaway value
        top_customers = Customer.objects.filter(
            tenant=self.request.tenant,
            layaway_plans__isnull=False
        ).annotate(
            total_layaway_value=Sum('layaway_plans__total_amount'),
            layaway_count=Count('layaway_plans')
        ).order_by('-total_layaway_value')[:10]
        
        # Get monthly trends
        monthly_trends = []
        for i in range(12):  # Last 12 months
            month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
            month_end = month_start.replace(day=28) + timedelta(days=4)
            month_end = month_end - timedelta(days=month_end.day)
            
            month_data = LayawayReportService.get_layaway_summary(
                month_start.date(), month_end.date()
            )
            
            monthly_trends.append({
                'month': month_start.strftime('%Y/%m'),
                'total_plans': month_data['total_plans'],
                'total_value': month_data['total_value'],
                'completion_rate': month_data['completion_rate']
            })
        
        context.update({
            'summary': summary,
            'top_customers': top_customers,
            'monthly_trends': list(reversed(monthly_trends)),
            'start_date': start_date,
            'end_date': end_date
        })
        
        return context


# AJAX Views for dynamic functionality
class LayawayAjaxView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    AJAX endpoints for layaway operations.
    """
    
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        
        if action == 'get_jewelry_item_details':
            return self.get_jewelry_item_details(request)
        elif action == 'calculate_installments':
            return self.calculate_installments(request)
        elif action == 'get_customer_history':
            return self.get_customer_history(request)
        elif action == 'send_reminder':
            return self.send_reminder(request)
        
        return JsonResponse({'success': False, 'error': 'Invalid action'})
    
    def get_jewelry_item_details(self, request):
        """Get jewelry item details for layaway plan creation."""
        try:
            item_id = request.POST.get('item_id')
            item = get_object_or_404(JewelryItem, id=item_id, tenant=request.tenant)
            
            return JsonResponse({
                'success': True,
                'item': {
                    'name': item.name,
                    'sku': item.sku,
                    'selling_price': float(item.selling_price or 0),
                    'weight_grams': float(item.weight_grams or 0),
                    'karat': item.karat,
                    'category': item.category.name if item.category else '',
                    'status': item.get_status_display()
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    def calculate_installments(self, request):
        """Calculate installment amounts and schedule."""
        try:
            total_amount = Decimal(request.POST.get('total_amount', '0'))
            down_payment = Decimal(request.POST.get('down_payment', '0'))
            number_of_payments = int(request.POST.get('number_of_payments', '1'))
            payment_frequency = request.POST.get('payment_frequency', 'monthly')
            
            remaining_amount = total_amount - down_payment
            installment_amount = remaining_amount / number_of_payments
            
            # Calculate completion date
            if payment_frequency == 'weekly':
                days_between = 7
            elif payment_frequency == 'bi_weekly':
                days_between = 14
            else:
                days_between = 30
            
            total_days = days_between * number_of_payments
            completion_date = timezone.now().date() + timedelta(days=total_days)
            
            return JsonResponse({
                'success': True,
                'calculation': {
                    'remaining_amount': float(remaining_amount),
                    'installment_amount': float(installment_amount),
                    'completion_date': completion_date.strftime('%Y-%m-%d'),
                    'total_payments': number_of_payments
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    def get_customer_history(self, request):
        """Get customer's layaway history."""
        try:
            customer_id = request.POST.get('customer_id')
            customer = get_object_or_404(Customer, id=customer_id, tenant=request.tenant)
            
            history = LayawayReportService.get_customer_layaway_history(customer)
            
            return JsonResponse({
                'success': True,
                'history': history
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    def send_reminder(self, request):
        """Send a specific reminder."""
        try:
            reminder_id = request.POST.get('reminder_id')
            reminder = get_object_or_404(
                LayawayReminder, 
                id=reminder_id, 
                layaway_plan__tenant=request.tenant
            )
            
            if reminder.send_reminder():
                return JsonResponse({
                    'success': True,
                    'message': 'یادآوری با موفقیت ارسال شد.'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'خطا در ارسال یادآوری.'
                })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})