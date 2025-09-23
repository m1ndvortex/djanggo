"""
Tenant management views for the admin super-panel.
Provides CRUD operations for tenant accounts with automated schema provisioning.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.views import View
from django.http import JsonResponse
from django.db import transaction, connection
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.urls import reverse_lazy
from django.core.exceptions import ValidationError
from django.conf import settings
import logging
import json
from datetime import datetime, timedelta

from .models import Tenant, Domain
from .admin_models import SuperAdmin, TenantAccessLog
from .services import TenantProvisioningService, TenantStatisticsService
from .forms import TenantCreateForm, TenantUpdateForm, TenantSearchForm
from zargar.core.mixins import SuperAdminRequiredMixin, PaginationMixin, SearchMixin, FilterMixin

logger = logging.getLogger(__name__)


class TenantListView(SuperAdminRequiredMixin, PaginationMixin, SearchMixin, FilterMixin, ListView):
    """
    List all tenants with search and filtering capabilities.
    """
    model = Tenant
    template_name = 'admin/tenants/tenant_list.html'
    context_object_name = 'tenants'
    paginate_by = 20
    
    # Search configuration
    search_fields = ['name', 'owner_name', 'owner_email', 'schema_name']
    
    # Filter configuration
    filter_fields = {
        'is_active': 'status',
        'subscription_plan': 'plan',
        'created_on__gte': 'created_after',
        'created_on__lte': 'created_before',
    }
    
    def get_queryset(self):
        """Get tenants with related data and statistics."""
        queryset = super().get_queryset()
        
        # Exclude public schema
        queryset = queryset.exclude(schema_name='public')
        
        # Add related domain information
        queryset = queryset.select_related().prefetch_related('domains')
        
        # Add statistics annotations
        queryset = queryset.annotate(
            domain_count=Count('domains'),
        )
        
        # Order by creation date (newest first)
        queryset = queryset.order_by('-created_on')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add summary statistics
        total_tenants = Tenant.objects.exclude(schema_name='public').count()
        active_tenants = Tenant.objects.exclude(schema_name='public').filter(is_active=True).count()
        inactive_tenants = total_tenants - active_tenants
        
        # Recent signups (last 30 days)
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        recent_signups = Tenant.objects.exclude(schema_name='public').filter(
            created_on__gte=thirty_days_ago
        ).count()
        
        # Subscription plan distribution
        plan_stats = Tenant.objects.exclude(schema_name='public').values('subscription_plan').annotate(
            count=Count('id')
        ).order_by('subscription_plan')
        
        context.update({
            'total_tenants': total_tenants,
            'active_tenants': active_tenants,
            'inactive_tenants': inactive_tenants,
            'recent_signups': recent_signups,
            'plan_stats': plan_stats,
            'search_form': TenantSearchForm(self.request.GET),
            'subscription_plans': Tenant._meta.get_field('subscription_plan').choices,
        })
        
        return context


class TenantDetailView(SuperAdminRequiredMixin, DetailView):
    """
    Display detailed information about a specific tenant.
    """
    model = Tenant
    template_name = 'admin/tenants/tenant_detail.html'
    context_object_name = 'tenant'
    
    def get_queryset(self):
        return Tenant.objects.exclude(schema_name='public').select_related().prefetch_related('domains')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.object
        
        # Get tenant statistics
        stats_service = TenantStatisticsService(tenant)
        context['tenant_stats'] = stats_service.get_comprehensive_stats()
        
        # Get recent access logs
        recent_logs = TenantAccessLog.objects.filter(
            tenant_schema=tenant.schema_name
        ).order_by('-timestamp')[:10]
        context['recent_logs'] = recent_logs
        
        # Get domain information
        context['domains'] = tenant.domains.all()
        
        # Check schema status
        context['schema_exists'] = self._check_schema_exists(tenant.schema_name)
        
        return context
    
    def _check_schema_exists(self, schema_name):
        """Check if the tenant schema exists in the database."""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                    [schema_name]
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking schema existence for {schema_name}: {e}")
            return False


class TenantCreateView(SuperAdminRequiredMixin, CreateView):
    """
    Create a new tenant with automated schema provisioning.
    """
    model = Tenant
    form_class = TenantCreateForm
    template_name = 'admin/tenants/tenant_create.html'
    success_url = reverse_lazy('core:tenants:tenant_list')
    
    def form_valid(self, form):
        """Handle successful form submission with tenant provisioning."""
        try:
            with transaction.atomic():
                # Create tenant instance
                tenant = form.save(commit=False)
                
                # Generate schema name from tenant name
                schema_name = self._generate_schema_name(tenant.name)
                tenant.schema_name = schema_name
                
                # Save tenant
                tenant.save()
                
                # Create domain
                domain_url = form.cleaned_data.get('domain_url')
                if domain_url:
                    Domain.objects.create(
                        domain=domain_url,
                        tenant=tenant,
                        is_primary=True
                    )
                
                # Provision tenant (create schema, run migrations, setup initial data)
                provisioning_service = TenantProvisioningService()
                provisioning_result = provisioning_service.provision_tenant(tenant)
                
                if not provisioning_result['success']:
                    raise ValidationError(f"Tenant provisioning failed: {provisioning_result['error']}")
                
                # Log the creation
                TenantAccessLog.log_action(
                    user=self.request.user,
                    tenant_schema='public',
                    action='create',
                    model_name='Tenant',
                    object_id=str(tenant.id),
                    details={
                        'tenant_name': tenant.name,
                        'schema_name': tenant.schema_name,
                        'owner_email': tenant.owner_email,
                        'subscription_plan': tenant.subscription_plan,
                    },
                    ip_address=self.request.META.get('REMOTE_ADDR'),
                    user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                    request_path=self.request.path,
                    request_method=self.request.method,
                )
                
                messages.success(
                    self.request,
                    f'تنانت "{tenant.name}" با موفقیت ایجاد شد. اسکیما و دامنه فرعی تنظیم گردید.'
                )
                
                return super().form_valid(form)
                
        except Exception as e:
            logger.error(f"Error creating tenant: {e}")
            messages.error(
                self.request,
                f'خطا در ایجاد تنانت: {str(e)}'
            )
            return self.form_invalid(form)
    
    def _generate_schema_name(self, tenant_name):
        """Generate a unique schema name from tenant name."""
        import re
        
        # Convert to lowercase and replace spaces/special chars with underscores
        schema_name = re.sub(r'[^a-zA-Z0-9]', '_', tenant_name.lower())
        schema_name = re.sub(r'_+', '_', schema_name)  # Remove multiple underscores
        schema_name = schema_name.strip('_')  # Remove leading/trailing underscores
        
        # Ensure it starts with a letter
        if not schema_name[0].isalpha():
            schema_name = 'tenant_' + schema_name
        
        # Ensure uniqueness
        base_schema_name = schema_name
        counter = 1
        while Tenant.objects.filter(schema_name=schema_name).exists():
            schema_name = f"{base_schema_name}_{counter}"
            counter += 1
        
        return schema_name


class TenantUpdateView(SuperAdminRequiredMixin, UpdateView):
    """
    Update tenant information.
    """
    model = Tenant
    form_class = TenantUpdateForm
    template_name = 'admin/tenants/tenant_update.html'
    
    def get_queryset(self):
        return Tenant.objects.exclude(schema_name='public')
    
    def get_success_url(self):
        return reverse_lazy('core:tenants:tenant_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        """Handle successful form submission."""
        try:
            # Get original values for logging
            original_tenant = Tenant.objects.get(pk=self.object.pk)
            
            # Save changes
            response = super().form_valid(form)
            
            # Log the update
            changes = {}
            for field in form.changed_data:
                changes[field] = {
                    'old': getattr(original_tenant, field),
                    'new': getattr(self.object, field)
                }
            
            TenantAccessLog.log_action(
                user=self.request.user,
                tenant_schema='public',
                action='update',
                model_name='Tenant',
                object_id=str(self.object.id),
                details={
                    'tenant_name': self.object.name,
                    'changes': changes,
                },
                ip_address=self.request.META.get('REMOTE_ADDR'),
                user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                request_path=self.request.path,
                request_method=self.request.method,
            )
            
            messages.success(
                self.request,
                f'اطلاعات تنانت "{self.object.name}" با موفقیت به‌روزرسانی شد.'
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error updating tenant {self.object.id}: {e}")
            messages.error(
                self.request,
                f'خطا در به‌روزرسانی تنانت: {str(e)}'
            )
            return self.form_invalid(form)


class TenantDeleteView(SuperAdminRequiredMixin, DeleteView):
    """
    Delete a tenant and its associated schema.
    """
    model = Tenant
    template_name = 'admin/tenants/tenant_delete.html'
    success_url = reverse_lazy('core:tenants:tenant_list')
    
    def get_queryset(self):
        return Tenant.objects.exclude(schema_name='public')
    
    def delete(self, request, *args, **kwargs):
        """Handle tenant deletion with schema cleanup."""
        tenant = self.get_object()
        
        try:
            with transaction.atomic():
                # Log the deletion before it happens
                TenantAccessLog.log_action(
                    user=request.user,
                    tenant_schema='public',
                    action='delete',
                    model_name='Tenant',
                    object_id=str(tenant.id),
                    details={
                        'tenant_name': tenant.name,
                        'schema_name': tenant.schema_name,
                        'owner_email': tenant.owner_email,
                    },
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    request_path=request.path,
                    request_method=request.method,
                )
                
                # Use tenant's auto_drop_schema feature
                tenant_name = tenant.name
                response = super().delete(request, *args, **kwargs)
                
                messages.success(
                    request,
                    f'تنانت "{tenant_name}" و اسکیمای مربوطه با موفقیت حذف شد.'
                )
                
                return response
                
        except Exception as e:
            logger.error(f"Error deleting tenant {tenant.id}: {e}")
            messages.error(
                request,
                f'خطا در حذف تنانت: {str(e)}'
            )
            return redirect('core:tenants:tenant_detail', pk=tenant.pk)


class TenantToggleStatusView(SuperAdminRequiredMixin, View):
    """
    Toggle tenant active/inactive status.
    """
    
    def post(self, request, pk):
        """Toggle tenant status via AJAX."""
        try:
            tenant = get_object_or_404(Tenant, pk=pk)
            
            # Toggle status
            tenant.is_active = not tenant.is_active
            tenant.save(update_fields=['is_active'])
            
            # Log the action
            action = 'activate' if tenant.is_active else 'suspend'
            TenantAccessLog.log_action(
                user=request.user,
                tenant_schema='public',
                action=action,
                model_name='Tenant',
                object_id=str(tenant.id),
                details={
                    'tenant_name': tenant.name,
                    'new_status': 'active' if tenant.is_active else 'inactive',
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
            )
            
            status_text = 'فعال' if tenant.is_active else 'غیرفعال'
            
            return JsonResponse({
                'success': True,
                'message': f'وضعیت تنانت "{tenant.name}" به "{status_text}" تغییر یافت.',
                'new_status': tenant.is_active,
                'status_text': status_text
            })
            
        except Exception as e:
            logger.error(f"Error toggling tenant status: {e}")
            return JsonResponse({
                'success': False,
                'message': f'خطا در تغییر وضعیت تنانت: {str(e)}'
            }, status=500)


class TenantStatisticsView(SuperAdminRequiredMixin, View):
    """
    Get tenant statistics via AJAX.
    """
    
    def get(self, request, pk):
        """Get comprehensive tenant statistics."""
        try:
            tenant = get_object_or_404(Tenant, pk=pk)
            
            # Get statistics
            stats_service = TenantStatisticsService(tenant)
            stats = stats_service.get_comprehensive_stats()
            
            return JsonResponse({
                'success': True,
                'stats': stats
            })
            
        except Exception as e:
            logger.error(f"Error getting tenant statistics: {e}")
            return JsonResponse({
                'success': False,
                'message': f'خطا در دریافت آمار تنانت: {str(e)}'
            }, status=500)


class TenantSearchView(SuperAdminRequiredMixin, View):
    """
    Search tenants via AJAX.
    """
    
    def get(self, request):
        """Search tenants and return JSON results."""
        try:
            query = request.GET.get('q', '').strip()
            
            if not query:
                return JsonResponse({
                    'success': True,
                    'results': []
                })
            
            # Search in multiple fields
            tenants = Tenant.objects.exclude(schema_name='public').filter(
                Q(name__icontains=query) |
                Q(owner_name__icontains=query) |
                Q(owner_email__icontains=query) |
                Q(schema_name__icontains=query)
            ).select_related()[:10]  # Limit to 10 results
            
            results = []
            for tenant in tenants:
                results.append({
                    'id': tenant.id,
                    'name': tenant.name,
                    'owner_name': tenant.owner_name,
                    'owner_email': tenant.owner_email,
                    'schema_name': tenant.schema_name,
                    'is_active': tenant.is_active,
                    'subscription_plan': tenant.get_subscription_plan_display(),
                    'created_on': tenant.created_on.strftime('%Y/%m/%d'),
                    'url': reverse_lazy('core:tenants:tenant_detail', kwargs={'pk': tenant.pk})
                })
            
            return JsonResponse({
                'success': True,
                'results': results,
                'count': len(results)
            })
            
        except Exception as e:
            logger.error(f"Error searching tenants: {e}")
            return JsonResponse({
                'success': False,
                'message': f'خطا در جستجوی تنانت‌ها: {str(e)}'
            }, status=500)


class TenantBulkActionView(SuperAdminRequiredMixin, View):
    """
    Handle bulk actions on multiple tenants.
    """
    
    def post(self, request):
        """Handle bulk actions via AJAX."""
        try:
            action = request.POST.get('action')
            tenant_ids = request.POST.getlist('tenant_ids')
            
            if not action or not tenant_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'عمل یا شناسه تنانت‌ها مشخص نشده است.'
                }, status=400)
            
            tenants = Tenant.objects.exclude(schema_name='public').filter(id__in=tenant_ids)
            
            if action == 'activate':
                updated_count = tenants.update(is_active=True)
                message = f'{updated_count} تنانت فعال شد.'
                
            elif action == 'deactivate':
                updated_count = tenants.update(is_active=False)
                message = f'{updated_count} تنانت غیرفعال شد.'
                
            elif action == 'delete':
                # This is more complex and should be handled carefully
                tenant_names = list(tenants.values_list('name', flat=True))
                tenants.delete()
                message = f'تنانت‌های {", ".join(tenant_names)} حذف شدند.'
                
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'عمل نامعتبر است.'
                }, status=400)
            
            # Log bulk action
            TenantAccessLog.log_action(
                user=request.user,
                tenant_schema='public',
                action=f'bulk_{action}',
                model_name='Tenant',
                object_id=','.join(tenant_ids),
                details={
                    'action': action,
                    'tenant_count': len(tenant_ids),
                    'tenant_ids': tenant_ids,
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
            )
            
            return JsonResponse({
                'success': True,
                'message': message
            })
            
        except Exception as e:
            logger.error(f"Error in bulk action: {e}")
            return JsonResponse({
                'success': False,
                'message': f'خطا در انجام عمل گروهی: {str(e)}'
            }, status=500)