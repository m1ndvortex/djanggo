"""
Mixins for tenant management views.
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _


class SuperAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin that requires the user to be a superadmin.
    """
    login_url = reverse_lazy('admin_panel:unified_login')
    
    def test_func(self):
        """Test if user is a superadmin."""
        return (
            self.request.user.is_authenticated and 
            self.request.user.is_superuser and
            hasattr(self.request.user, '_meta') and
            self.request.user._meta.model_name == 'superadmin'
        )
    
    def handle_no_permission(self):
        """Handle when user doesn't have permission."""
        if not self.request.user.is_authenticated:
            return redirect(self.get_login_url())
        
        messages.error(
            self.request, 
            _('شما دسترسی لازم برای مشاهده این صفحه را ندارید.')
        )
        return redirect('core:super_panel_dashboard')


class TenantContextMixin:
    """
    Mixin that provides tenant context to views.
    """
    
    def get_context_data(self, **kwargs):
        """Add tenant context to the view."""
        context = super().get_context_data(**kwargs)
        
        # Add tenant information if available
        if hasattr(self.request, 'tenant'):
            context['current_tenant'] = self.request.tenant
        
        return context


class AjaxResponseMixin:
    """
    Mixin for handling AJAX requests.
    """
    
    def dispatch(self, request, *args, **kwargs):
        """Handle AJAX requests differently."""
        self.is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        return super().dispatch(request, *args, **kwargs)
    
    def form_invalid(self, form):
        """Handle invalid form for AJAX requests."""
        if self.is_ajax:
            from django.http import JsonResponse
            return JsonResponse({
                'success': False,
                'errors': form.errors,
                'message': _('فرم دارای خطا است. لطفاً اطلاعات را بررسی کنید.')
            })
        return super().form_invalid(form)
    
    def form_valid(self, form):
        """Handle valid form for AJAX requests."""
        response = super().form_valid(form)
        
        if self.is_ajax:
            from django.http import JsonResponse
            return JsonResponse({
                'success': True,
                'message': _('عملیات با موفقیت انجام شد.'),
                'redirect_url': self.get_success_url() if hasattr(self, 'get_success_url') else None
            })
        
        return response


class PaginationMixin:
    """
    Mixin for consistent pagination across views.
    """
    paginate_by = 25
    
    def get_context_data(self, **kwargs):
        """Add pagination context."""
        context = super().get_context_data(**kwargs)
        
        if 'page_obj' in context:
            page_obj = context['page_obj']
            
            # Calculate page range for pagination display
            current_page = page_obj.number
            total_pages = page_obj.paginator.num_pages
            
            # Show 5 pages around current page
            start_page = max(1, current_page - 2)
            end_page = min(total_pages, current_page + 2)
            
            context['page_range'] = range(start_page, end_page + 1)
            context['show_first'] = start_page > 1
            context['show_last'] = end_page < total_pages
        
        return context


class SearchMixin:
    """
    Mixin for adding search functionality to list views.
    """
    search_fields = []
    
    def get_queryset(self):
        """Filter queryset based on search query."""
        queryset = super().get_queryset()
        
        search_query = self.request.GET.get('search', '').strip()
        if search_query and self.search_fields:
            from django.db.models import Q
            
            search_filter = Q()
            for field in self.search_fields:
                search_filter |= Q(**{f'{field}__icontains': search_query})
            
            queryset = queryset.filter(search_filter)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add search context."""
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context


class FilterMixin:
    """
    Mixin for adding filtering functionality to list views.
    """
    filter_fields = {}
    
    def get_queryset(self):
        """Filter queryset based on filter parameters."""
        queryset = super().get_queryset()
        
        for param, field in self.filter_fields.items():
            value = self.request.GET.get(param)
            if value:
                queryset = queryset.filter(**{field: value})
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add filter context."""
        context = super().get_context_data(**kwargs)
        
        # Add current filter values to context
        for param in self.filter_fields.keys():
            context[f'{param}_filter'] = self.request.GET.get(param, '')
        
        return context


class ExportMixin:
    """
    Mixin for adding export functionality to views.
    """
    
    def get(self, request, *args, **kwargs):
        """Handle export requests."""
        export_format = request.GET.get('export')
        
        if export_format in ['csv', 'excel', 'pdf']:
            return self.export_data(export_format)
        
        return super().get(request, *args, **kwargs)
    
    def export_data(self, format_type):
        """Export data in the specified format."""
        from django.http import HttpResponse
        
        if format_type == 'csv':
            return self.export_csv()
        elif format_type == 'excel':
            return self.export_excel()
        elif format_type == 'pdf':
            return self.export_pdf()
        
        return HttpResponse('Export format not supported', status=400)
    
    def export_csv(self):
        """Export data as CSV."""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="export.csv"'
        
        writer = csv.writer(response)
        
        # Override this method in subclasses
        self.write_csv_data(writer)
        
        return response
    
    def write_csv_data(self, writer):
        """Write CSV data. Override in subclasses."""
        writer.writerow(['No data to export'])
    
    def export_excel(self):
        """Export data as Excel."""
        from django.http import HttpResponse
        
        # This would require openpyxl or xlsxwriter
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="export.xlsx"'
        
        # Implementation would go here
        response.write(b'Excel export not implemented yet')
        
        return response
    
    def export_pdf(self):
        """Export data as PDF."""
        from django.http import HttpResponse
        
        # This would require reportlab or weasyprint
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="export.pdf"'
        
        # Implementation would go here
        response.write(b'PDF export not implemented yet')
        
        return response


class BreadcrumbMixin:
    """
    Mixin for adding breadcrumb navigation.
    """
    breadcrumbs = []
    
    def get_context_data(self, **kwargs):
        """Add breadcrumb context."""
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = self.get_breadcrumbs()
        return context
    
    def get_breadcrumbs(self):
        """Get breadcrumb list. Override in subclasses."""
        return self.breadcrumbs


class MessageMixin:
    """
    Mixin for consistent success/error messages.
    """
    success_message = None
    error_message = None
    
    def form_valid(self, form):
        """Add success message on form valid."""
        response = super().form_valid(form)
        
        if self.success_message:
            messages.success(self.request, self.success_message)
        
        return response
    
    def form_invalid(self, form):
        """Add error message on form invalid."""
        response = super().form_invalid(form)
        
        if self.error_message:
            messages.error(self.request, self.error_message)
        
        return response