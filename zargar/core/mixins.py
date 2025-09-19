"""
Core mixins for ZARGAR Jewelry SaaS.

This module provides common mixins for views, forms, and other components
that need tenant-aware functionality and Persian localization support.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_tenants.utils import get_tenant_model, get_public_schema_name
import jdatetime


class TenantContextMixin:
    """
    Mixin that provides tenant context to views.
    
    This mixin automatically adds tenant information to the context
    and ensures that all operations are performed within the correct
    tenant scope.
    """
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add tenant information
        if hasattr(self.request, 'tenant'):
            context['tenant'] = self.request.tenant
            context['tenant_name'] = self.request.tenant.name
            context['tenant_domain'] = self.request.tenant.domain_url
        
        # Add current user information
        if self.request.user.is_authenticated:
            context['current_user'] = self.request.user
            context['user_role'] = getattr(self.request.user, 'role', None)
        
        # Add Persian date information
        today = timezone.now().date()
        shamsi_today = jdatetime.date.fromgregorian(date=today)
        context['shamsi_date'] = shamsi_today.strftime('%Y/%m/%d')
        context['shamsi_year'] = str(shamsi_today.year)
        context['shamsi_month'] = shamsi_today.month
        context['shamsi_day'] = shamsi_today.day
        
        # Add theme information
        context['is_dark_mode'] = self.request.session.get('theme', 'light') == 'dark'
        
        return context
    
    def dispatch(self, request, *args, **kwargs):
        """
        Ensure we're in a tenant context (not public schema).
        """
        if hasattr(request, 'tenant'):
            if request.tenant.schema_name == get_public_schema_name():
                raise PermissionDenied("This view is not available in the public schema.")
        
        return super().dispatch(request, *args, **kwargs)


class TenantOwnerRequiredMixin(LoginRequiredMixin):
    """
    Mixin that requires the user to be the tenant owner.
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if hasattr(request, 'tenant') and hasattr(request.user, 'role'):
            if request.user.role != 'owner':
                raise PermissionDenied("Only tenant owners can access this view.")
        
        return super().dispatch(request, *args, **kwargs)


class TenantAccountantRequiredMixin(LoginRequiredMixin):
    """
    Mixin that requires the user to be a tenant owner or accountant.
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if hasattr(request, 'tenant') and hasattr(request.user, 'role'):
            if request.user.role not in ['owner', 'accountant']:
                raise PermissionDenied("Only owners and accountants can access this view.")
        
        return super().dispatch(request, *args, **kwargs)


class TenantSalespersonRequiredMixin(LoginRequiredMixin):
    """
    Mixin that requires the user to be a tenant owner, accountant, or salesperson.
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if hasattr(request, 'tenant') and hasattr(request.user, 'role'):
            if request.user.role not in ['owner', 'accountant', 'salesperson']:
                raise PermissionDenied("Access denied for this role.")
        
        return super().dispatch(request, *args, **kwargs)


class SuperAdminRequiredMixin(LoginRequiredMixin):
    """
    Mixin that requires the user to be a superuser.
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not request.user.is_superuser:
            raise PermissionDenied("Only superusers can access this view.")
        
        return super().dispatch(request, *args, **kwargs)


class PersianDateMixin:
    """
    Mixin that provides Persian date utilities.
    """
    
    def get_shamsi_date_range(self, year, month=None):
        """
        Get Gregorian date range for a Shamsi year/month.
        
        Args:
            year (str): Shamsi year (e.g., '1402')
            month (int, optional): Shamsi month (1-12)
        
        Returns:
            tuple: (start_date, end_date) as Gregorian dates
        """
        if month:
            # Get specific month range
            shamsi_start = jdatetime.date(int(year), month, 1)
            
            # Get last day of month
            if month == 12:
                next_month = jdatetime.date(int(year) + 1, 1, 1)
            else:
                next_month = jdatetime.date(int(year), month + 1, 1)
            
            shamsi_end = next_month - jdatetime.timedelta(days=1)
        else:
            # Get full year range
            shamsi_start = jdatetime.date(int(year), 1, 1)
            shamsi_end = jdatetime.date(int(year), 12, 29)  # Last day of Shamsi year
        
        # Convert to Gregorian
        start_date = shamsi_start.togregorian()
        end_date = shamsi_end.togregorian()
        
        return start_date, end_date
    
    def get_current_shamsi_year(self):
        """Get current Shamsi year as string."""
        today = timezone.now().date()
        shamsi_today = jdatetime.date.fromgregorian(date=today)
        return str(shamsi_today.year)
    
    def get_current_shamsi_month(self):
        """Get current Shamsi month as integer."""
        today = timezone.now().date()
        shamsi_today = jdatetime.date.fromgregorian(date=today)
        return shamsi_today.month
    
    def get_shamsi_months(self):
        """Get list of Shamsi months with Persian names."""
        return [
            (1, 'فروردین'), (2, 'اردیبهشت'), (3, 'خرداد'),
            (4, 'تیر'), (5, 'مرداد'), (6, 'شهریور'),
            (7, 'مهر'), (8, 'آبان'), (9, 'آذر'),
            (10, 'دی'), (11, 'بهمن'), (12, 'اسفند')
        ]


class AjaxResponseMixin:
    """
    Mixin for handling AJAX requests with JSON responses.
    """
    
    def dispatch(self, request, *args, **kwargs):
        """Store whether this is an AJAX request."""
        self.is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """Handle successful form submission for AJAX requests."""
        response = super().form_valid(form)
        
        if self.is_ajax:
            from django.http import JsonResponse
            return JsonResponse({
                'success': True,
                'message': 'عملیات با موفقیت انجام شد.',
                'redirect_url': self.get_success_url() if hasattr(self, 'get_success_url') else None
            })
        
        return response
    
    def form_invalid(self, form):
        """Handle form validation errors for AJAX requests."""
        response = super().form_invalid(form)
        
        if self.is_ajax:
            from django.http import JsonResponse
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(error) for error in error_list]
            
            return JsonResponse({
                'success': False,
                'message': 'خطا در اعتبارسنجی فرم.',
                'errors': errors
            }, status=400)
        
        return response


class PaginationMixin:
    """
    Mixin for consistent pagination across views.
    """
    paginate_by = 20
    
    def get_paginate_by(self, queryset):
        """Allow dynamic pagination size."""
        paginate_by = self.request.GET.get('per_page')
        if paginate_by and paginate_by.isdigit():
            per_page = int(paginate_by)
            if 1 <= per_page <= 100:  # Reasonable limits
                return per_page
        
        return self.paginate_by
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if 'page_obj' in context:
            page_obj = context['page_obj']
            
            # Add pagination info
            context['pagination_info'] = {
                'current_page': page_obj.number,
                'total_pages': page_obj.paginator.num_pages,
                'total_items': page_obj.paginator.count,
                'start_index': page_obj.start_index(),
                'end_index': page_obj.end_index(),
                'has_previous': page_obj.has_previous(),
                'has_next': page_obj.has_next(),
                'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
                'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
            }
            
            # Add page range for pagination display
            current_page = page_obj.number
            total_pages = page_obj.paginator.num_pages
            
            # Show 5 pages around current page
            start_page = max(1, current_page - 2)
            end_page = min(total_pages, current_page + 2)
            
            context['page_range'] = range(start_page, end_page + 1)
        
        return context


class SearchMixin:
    """
    Mixin for adding search functionality to list views.
    """
    search_fields = []
    search_param = 'search'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get(self.search_param)
        
        if search_query and self.search_fields:
            from django.db.models import Q
            
            # Build search query
            search_q = Q()
            for field in self.search_fields:
                search_q |= Q(**{f"{field}__icontains": search_query})
            
            queryset = queryset.filter(search_q)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get(self.search_param, '')
        return context


class FilterMixin:
    """
    Mixin for adding filtering functionality to list views.
    """
    filter_fields = {}  # {'field_name': 'param_name'}
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        for field_name, param_name in self.filter_fields.items():
            filter_value = self.request.GET.get(param_name)
            if filter_value:
                queryset = queryset.filter(**{field_name: filter_value})
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add current filter values to context
        context['current_filters'] = {}
        for field_name, param_name in self.filter_fields.items():
            context['current_filters'][param_name] = self.request.GET.get(param_name, '')
        
        return context