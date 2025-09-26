"""
Comprehensive reporting engine views for ZARGAR jewelry SaaS platform.

This module implements Persian-native reporting interface with dual theme support,
report generation, scheduling, and export functionality.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse, Http404
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.db.models import Q
from decimal import Decimal
import json
from datetime import datetime, date, timedelta
import jdatetime

from zargar.core.mixins import TenantContextMixin
from zargar.core.persian_number_formatter import PersianNumberFormatter
from .models import ReportTemplate, GeneratedReport, ReportSchedule, ReportDelivery
from .services import ComprehensiveReportingEngine
from .exporters import ReportExporter
from .scheduler import ReportScheduler


class ReportsDashboardView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Main reports dashboard with Persian RTL layout and dual theme support.
    """
    template_name = 'reports/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get recent reports
        recent_reports = GeneratedReport.objects.filter(
            status='completed'
        ).order_by('-generated_at')[:10]
        
        # Get active schedules
        active_schedules = ReportSchedule.objects.filter(
            is_active=True
        ).order_by('next_execution')[:5]
        
        # Get report templates grouped by type
        templates_by_type = {}
        templates = ReportTemplate.objects.filter(is_active=True).order_by('report_type', 'name')
        
        for template in templates:
            report_type = template.get_report_type_display()
            if report_type not in templates_by_type:
                templates_by_type[report_type] = []
            templates_by_type[report_type].append(template)
        
        # Statistics
        total_reports = GeneratedReport.objects.count()
        reports_this_month = GeneratedReport.objects.filter(
            generated_at__month=timezone.now().month,
            generated_at__year=timezone.now().year
        ).count()
        
        context.update({
            'recent_reports': recent_reports,
            'active_schedules': active_schedules,
            'templates_by_type': templates_by_type,
            'total_reports': total_reports,
            'reports_this_month': reports_this_month,
            'current_shamsi_date': jdatetime.datetime.now().strftime('%Y/%m/%d'),
        })
        
        return context


class ReportGenerationView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Report generation interface with Persian date picker and parameter selection.
    """
    template_name = 'reports/generate.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        template_id = self.kwargs.get('template_id')
        if template_id:
            template = get_object_or_404(ReportTemplate, id=template_id, is_active=True)
            context['selected_template'] = template
        
        # Get all available templates
        context['report_templates'] = ReportTemplate.objects.filter(
            is_active=True
        ).order_by('report_type', 'name')
        
        # Default date range (current Persian month)
        today = jdatetime.date.today()
        month_start = today.replace(day=1)
        context['default_date_from'] = month_start.strftime('%Y/%m/%d')
        context['default_date_to'] = today.strftime('%Y/%m/%d')
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle report generation request."""
        try:
            template_id = request.POST.get('template_id')
            template = get_object_or_404(ReportTemplate, id=template_id, is_active=True)
            
            # Parse parameters
            parameters = self._parse_report_parameters(request.POST, template)
            
            # Create report generation record
            generated_report = GeneratedReport.objects.create(
                template=template,
                generated_by=request.user,
                report_parameters=parameters,
                date_from=parameters.get('date_from'),
                date_to=parameters.get('date_to'),
                output_format=request.POST.get('output_format', template.default_output_format),
                status='pending'
            )
            
            # Generate report asynchronously
            from .tasks import generate_report_task
            generate_report_task.delay(generated_report.id)
            
            messages.success(request, _('گزارش در حال تولید است. پس از تکمیل، از طریق لیست گزارش‌ها قابل دسترسی خواهد بود.'))
            
            return JsonResponse({
                'success': True,
                'report_id': generated_report.report_id,
                'redirect_url': reverse('reports:report_detail', kwargs={'report_id': generated_report.report_id})
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    def _parse_report_parameters(self, post_data, template):
        """Parse and validate report parameters from POST data."""
        parameters = {}
        
        # Date range parameters
        date_from_shamsi = post_data.get('date_from_shamsi')
        date_to_shamsi = post_data.get('date_to_shamsi')
        
        if date_from_shamsi:
            try:
                shamsi_date = jdatetime.datetime.strptime(date_from_shamsi, '%Y/%m/%d').date()
                parameters['date_from'] = shamsi_date.togregorian()
            except ValueError:
                pass
        
        if date_to_shamsi:
            try:
                shamsi_date = jdatetime.datetime.strptime(date_to_shamsi, '%Y/%m/%d').date()
                parameters['date_to'] = shamsi_date.togregorian()
            except ValueError:
                pass
        
        # Report-specific parameters
        if template.report_type == 'inventory_valuation':
            gold_price = post_data.get('gold_price_per_gram')
            if gold_price:
                try:
                    parameters['gold_price_per_gram'] = Decimal(gold_price)
                except (ValueError, TypeError):
                    pass
        
        elif template.report_type == 'customer_aging':
            aging_periods = post_data.get('aging_periods', '30,60,90,120')
            try:
                parameters['aging_periods'] = [int(x.strip()) for x in aging_periods.split(',')]
            except ValueError:
                parameters['aging_periods'] = [30, 60, 90, 120]
        
        # Include zero balances option
        parameters['include_zero_balances'] = post_data.get('include_zero_balances') == 'on'
        
        return parameters


class ReportListView(LoginRequiredMixin, TenantContextMixin, ListView):
    """
    List view for generated reports with filtering and search.
    """
    model = GeneratedReport
    template_name = 'reports/list.html'
    context_object_name = 'reports'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = GeneratedReport.objects.select_related('template', 'generated_by').order_by('-generated_at')
        
        # Apply filters
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        report_type = self.request.GET.get('report_type')
        if report_type:
            queryset = queryset.filter(template__report_type=report_type)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(template__name__icontains=search) |
                Q(template__name_persian__icontains=search) |
                Q(report_id__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filter options
        context['status_choices'] = GeneratedReport.STATUS_CHOICES
        context['report_type_choices'] = ReportTemplate.REPORT_TYPES
        
        # Current filters
        context['current_filters'] = {
            'status': self.request.GET.get('status', ''),
            'report_type': self.request.GET.get('report_type', ''),
            'search': self.request.GET.get('search', ''),
        }
        
        return context


class ReportDetailView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Detailed view for a specific generated report with preview and download options.
    """
    template_name = 'reports/detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        report_id = kwargs.get('report_id')
        report = get_object_or_404(GeneratedReport, report_id=report_id)
        
        context['report'] = report
        
        # If report has cached data, prepare for preview
        if report.report_data and report.status == 'completed':
            context['report_preview'] = self._prepare_report_preview(report)
        
        # Delivery history
        context['deliveries'] = report.deliveries.all().order_by('-created_at')
        
        return context
    
    def _prepare_report_preview(self, report):
        """Prepare report data for HTML preview."""
        data = report.report_data
        formatter = PersianNumberFormatter()
        
        # Format numbers for display
        if 'accounts' in data:
            for account in data['accounts']:
                if 'debit_amount' in account:
                    account['debit_display'] = formatter.format_currency(
                        account['debit_amount'], use_persian_digits=True
                    )
                if 'credit_amount' in account:
                    account['credit_display'] = formatter.format_currency(
                        account['credit_amount'], use_persian_digits=True
                    )
        
        return data


class ReportDownloadView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Handle report download in various formats.
    """
    
    def get(self, request, *args, **kwargs):
        report_id = kwargs.get('report_id')
        format_type = kwargs.get('format', 'pdf')
        
        report = get_object_or_404(GeneratedReport, report_id=report_id)
        
        if report.status != 'completed':
            raise Http404(_('گزارش هنوز آماده نیست'))
        
        if report.is_expired:
            raise Http404(_('گزارش منقضی شده است'))
        
        try:
            # Generate file in requested format
            exporter = ReportExporter()
            file_content, content_type, filename = exporter.export_report(
                report, format_type
            )
            
            response = HttpResponse(file_content, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            messages.error(request, f'خطا در دانلود گزارش: {str(e)}')
            return redirect('reports:report_detail', report_id=report_id)


class ReportScheduleListView(LoginRequiredMixin, TenantContextMixin, ListView):
    """
    List view for report schedules with management options.
    """
    model = ReportSchedule
    template_name = 'reports/schedules/list.html'
    context_object_name = 'schedules'
    paginate_by = 20
    
    def get_queryset(self):
        return ReportSchedule.objects.select_related('template').order_by('-created_at')


class ReportScheduleCreateView(LoginRequiredMixin, TenantContextMixin, CreateView):
    """
    Create new report schedule with Persian interface.
    """
    model = ReportSchedule
    template_name = 'reports/schedules/create.html'
    fields = [
        'name', 'name_persian', 'description', 'template', 'frequency',
        'start_date', 'end_date', 'execution_time', 'day_of_week', 'day_of_month',
        'delivery_methods', 'email_recipients', 'sms_recipients'
    ]
    success_url = reverse_lazy('reports:schedule_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _('زمان‌بندی گزارش با موفقیت ایجاد شد'))
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_templates'] = ReportTemplate.objects.filter(is_active=True)
        return context


class ReportScheduleUpdateView(LoginRequiredMixin, TenantContextMixin, UpdateView):
    """
    Update existing report schedule.
    """
    model = ReportSchedule
    template_name = 'reports/schedules/edit.html'
    fields = [
        'name', 'name_persian', 'description', 'template', 'frequency',
        'start_date', 'end_date', 'execution_time', 'day_of_week', 'day_of_month',
        'delivery_methods', 'email_recipients', 'sms_recipients', 'is_active'
    ]
    success_url = reverse_lazy('reports:schedule_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('زمان‌بندی گزارش با موفقیت به‌روزرسانی شد'))
        return super().form_valid(form)


class ReportScheduleDeleteView(LoginRequiredMixin, TenantContextMixin, DeleteView):
    """
    Delete report schedule with confirmation.
    """
    model = ReportSchedule
    template_name = 'reports/schedules/delete.html'
    success_url = reverse_lazy('reports:schedule_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('زمان‌بندی گزارش با موفقیت حذف شد'))
        return super().delete(request, *args, **kwargs)


class ReportTemplateListView(LoginRequiredMixin, TenantContextMixin, ListView):
    """
    List view for report templates with management options.
    """
    model = ReportTemplate
    template_name = 'reports/templates/list.html'
    context_object_name = 'templates'
    
    def get_queryset(self):
        return ReportTemplate.objects.order_by('report_type', 'name')


class ReportTemplateCreateView(LoginRequiredMixin, TenantContextMixin, CreateView):
    """
    Create custom report template.
    """
    model = ReportTemplate
    template_name = 'reports/templates/create.html'
    fields = [
        'name', 'name_persian', 'description', 'report_type',
        'default_output_format', 'template_config',
        'include_persian_headers', 'use_shamsi_dates', 'use_persian_numbers'
    ]
    success_url = reverse_lazy('reports:template_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _('قالب گزارش با موفقیت ایجاد شد'))
        return super().form_valid(form)


# AJAX Views for dynamic functionality

class ReportStatusAjaxView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    AJAX endpoint for checking report generation status.
    """
    
    def get(self, request, *args, **kwargs):
        report_id = kwargs.get('report_id')
        
        try:
            report = GeneratedReport.objects.get(report_id=report_id)
            
            return JsonResponse({
                'status': report.status,
                'progress': self._calculate_progress(report),
                'error_message': report.error_message,
                'download_url': reverse('reports:download', kwargs={
                    'report_id': report_id, 'format': report.output_format
                }) if report.status == 'completed' else None
            })
            
        except GeneratedReport.DoesNotExist:
            return JsonResponse({'error': 'Report not found'}, status=404)
    
    def _calculate_progress(self, report):
        """Calculate report generation progress percentage."""
        if report.status == 'pending':
            return 0
        elif report.status == 'generating':
            # Estimate progress based on time elapsed
            if report.generation_started_at:
                elapsed = (timezone.now() - report.generation_started_at).total_seconds()
                # Assume average report takes 30 seconds
                progress = min(int((elapsed / 30) * 100), 95)
                return progress
            return 10
        elif report.status == 'completed':
            return 100
        elif report.status == 'failed':
            return 0
        return 0


class GoldPriceAjaxView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    AJAX endpoint for fetching current gold price for inventory valuation reports.
    """
    
    def get(self, request, *args, **kwargs):
        try:
            # This would integrate with actual gold price API
            # For now, return a placeholder value
            current_price = Decimal('1250000')  # Toman per gram
            
            formatter = PersianNumberFormatter()
            
            return JsonResponse({
                'success': True,
                'price_per_gram': str(current_price),
                'price_formatted': formatter.format_currency(current_price, use_persian_digits=True),
                'last_updated': timezone.now().isoformat()
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)