"""
Views for RBAC (Role-Based Access Control) management in the super admin panel.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, ListView, View
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.core.exceptions import ValidationError
import json
import logging

from zargar.tenants.admin_models import SuperAdmin
from .models import SuperAdminRole, SuperAdminPermission, SuperAdminUserRole
from .services import RBACService
from .rbac import require_permission

logger = logging.getLogger(__name__)


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
        return redirect('admin_panel:dashboard')


@method_decorator(require_permission('rbac.view'), name='dispatch')
class RBACManagementView(SuperAdminRequiredMixin, TemplateView):
    """
    Main RBAC management dashboard view.
    """
    template_name = 'admin_panel/security/rbac_management.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get RBAC statistics
        stats = RBACService.get_role_statistics()
        
        # Get recent roles
        recent_roles = SuperAdminRole.objects.filter(is_active=True).order_by('-created_at')[:5]
        
        # Get recent user assignments
        recent_assignments = SuperAdminUserRole.objects.filter(
            is_active=True
        ).select_related('role').order_by('-created_at')[:10]
        
        # Get permissions by section
        permissions_by_section = {}
        permissions = SuperAdminPermission.objects.filter(is_active=True).order_by('section', 'action')
        for permission in permissions:
            if permission.section not in permissions_by_section:
                permissions_by_section[permission.section] = []
            permissions_by_section[permission.section].append(permission)
        
        context.update({
            'stats': stats,
            'recent_roles': recent_roles,
            'recent_assignments': recent_assignments,
            'permissions_by_section': permissions_by_section,
        })
        
        return context


@method_decorator(require_permission('rbac.view'), name='dispatch')
class RoleListView(SuperAdminRequiredMixin, ListView):
    """
    View to list all roles with filtering and pagination.
    """
    model = SuperAdminRole
    template_name = 'admin_panel/security/role_list.html'
    context_object_name = 'roles'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = SuperAdminRole.objects.filter(is_active=True).annotate(
            user_count=Count('user_roles', filter=Q(user_roles__is_active=True))
        ).order_by('-created_at')
        
        # Filter by role type
        role_type = self.request.GET.get('type')
        if role_type:
            queryset = queryset.filter(role_type=role_type)
        
        # Search by name
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(name_persian__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter values to context
        context['type_filter'] = self.request.GET.get('type', '')
        context['search_filter'] = self.request.GET.get('search', '')
        
        # Add role type choices
        context['role_types'] = SuperAdminRole.ROLE_TYPES
        
        return context


@method_decorator(require_permission('rbac.manage'), name='dispatch')
class RoleDetailView(SuperAdminRequiredMixin, TemplateView):
    """
    View to display and edit role details.
    """
    template_name = 'admin_panel/security/role_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        role_id = kwargs.get('role_id')
        role = get_object_or_404(SuperAdminRole, id=role_id, is_active=True)
        
        # Get role permissions
        role_permissions = role.permissions.filter(is_active=True)
        
        # Get users with this role
        role_users = SuperAdminUserRole.objects.filter(
            role=role, 
            is_active=True
        ).select_related('user')
        
        # Get all available permissions grouped by section
        all_permissions = SuperAdminPermission.objects.filter(is_active=True).order_by('section', 'action')
        permissions_by_section = {}
        for permission in all_permissions:
            if permission.section not in permissions_by_section:
                permissions_by_section[permission.section] = []
            permissions_by_section[permission.section].append(permission)
        
        context.update({
            'role': role,
            'role_permissions': role_permissions,
            'role_users': role_users,
            'permissions_by_section': permissions_by_section,
        })
        
        return context
    
    def post(self, request, role_id):
        """Handle role update."""
        role = get_object_or_404(SuperAdminRole, id=role_id, is_active=True)
        
        try:
            # Get form data
            name = request.POST.get('name')
            name_persian = request.POST.get('name_persian')
            description = request.POST.get('description')
            description_persian = request.POST.get('description_persian')
            max_users = request.POST.get('max_users')
            permissions = request.POST.getlist('permissions')
            
            # Convert max_users to int if provided
            if max_users:
                max_users = int(max_users) if max_users.isdigit() else None
            
            # Update role using service
            updated_role = RBACService.update_role(
                role_id=role_id,
                name=name,
                name_persian=name_persian,
                description=description,
                description_persian=description_persian,
                max_users=max_users,
                permissions=permissions,
                updated_by_id=request.user.id,
                updated_by_username=request.user.username
            )
            
            messages.success(request, _('نقش با موفقیت به‌روزرسانی شد.'))
            return redirect('admin_panel:rbac_role_detail', role_id=role_id)
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Error updating role {role_id}: {str(e)}")
            messages.error(request, _('خطا در به‌روزرسانی نقش'))
        
        return redirect('admin_panel:rbac_role_detail', role_id=role_id)


@method_decorator(require_permission('rbac.manage'), name='dispatch')
class CreateRoleView(SuperAdminRequiredMixin, TemplateView):
    """
    View to create a new role.
    """
    template_name = 'admin_panel/security/role_create.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all available permissions grouped by section
        all_permissions = SuperAdminPermission.objects.filter(is_active=True).order_by('section', 'action')
        permissions_by_section = {}
        for permission in all_permissions:
            if permission.section not in permissions_by_section:
                permissions_by_section[permission.section] = []
            permissions_by_section[permission.section].append(permission)
        
        context.update({
            'permissions_by_section': permissions_by_section,
            'role_types': SuperAdminRole.ROLE_TYPES,
        })
        
        return context
    
    def post(self, request):
        """Handle role creation."""
        try:
            # Get form data
            name = request.POST.get('name')
            name_persian = request.POST.get('name_persian')
            description = request.POST.get('description', '')
            description_persian = request.POST.get('description_persian', '')
            role_type = request.POST.get('role_type', 'custom')
            max_users = request.POST.get('max_users')
            permissions = request.POST.getlist('permissions')
            
            # Convert max_users to int if provided
            if max_users:
                max_users = int(max_users) if max_users.isdigit() else None
            
            # Create role using service
            role = RBACService.create_role(
                name=name,
                name_persian=name_persian,
                description=description,
                description_persian=description_persian,
                role_type=role_type,
                max_users=max_users,
                permissions=permissions,
                created_by_id=request.user.id,
                created_by_username=request.user.username
            )
            
            messages.success(request, _('نقش جدید با موفقیت ایجاد شد.'))
            return redirect('admin_panel:rbac_role_detail', role_id=role.id)
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Error creating role: {str(e)}")
            messages.error(request, _('خطا در ایجاد نقش'))
        
        return redirect('admin_panel:rbac_create_role')


@method_decorator(require_permission('rbac.view'), name='dispatch')
class UserRoleAssignmentView(SuperAdminRequiredMixin, TemplateView):
    """
    View to manage user role assignments.
    """
    template_name = 'admin_panel/security/user_role_assignment.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all super admin users
        users = SuperAdmin.objects.filter(is_active=True).order_by('username')
        
        # Get all active roles
        roles = SuperAdminRole.objects.filter(is_active=True).order_by('name')
        
        # Get current assignments
        assignments = SuperAdminUserRole.objects.filter(
            is_active=True
        ).select_related('role').order_by('-created_at')
        
        # Paginate assignments
        paginator = Paginator(assignments, 20)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context.update({
            'users': users,
            'roles': roles,
            'assignments': page_obj,
        })
        
        return context
    
    def post(self, request):
        """Handle user role assignment."""
        try:
            user_id = request.POST.get('user_id')
            role_id = request.POST.get('role_id')
            expires_at = request.POST.get('expires_at')
            
            # Convert expires_at to datetime if provided
            if expires_at:
                from datetime import datetime
                expires_at = datetime.strptime(expires_at, '%Y-%m-%d').date()
            else:
                expires_at = None
            
            # Assign role using service
            user_role = RBACService.assign_role_to_user(
                user_id=int(user_id),
                role_id=int(role_id),
                expires_at=expires_at,
                assigned_by_id=request.user.id,
                assigned_by_username=request.user.username
            )
            
            messages.success(request, _('نقش با موفقیت به کاربر اختصاص داده شد.'))
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Error assigning role: {str(e)}")
            messages.error(request, _('خطا در اختصاص نقش'))
        
        return redirect('admin_panel:rbac_user_assignments')


@method_decorator(require_permission('rbac.manage'), name='dispatch')
class RemoveUserRoleView(SuperAdminRequiredMixin, View):
    """
    View to remove a role from a user.
    """
    
    def post(self, request):
        """Handle role removal."""
        try:
            user_id = request.POST.get('user_id')
            role_id = request.POST.get('role_id')
            
            # Remove role using service
            success = RBACService.remove_role_from_user(
                user_id=int(user_id),
                role_id=int(role_id),
                removed_by_id=request.user.id,
                removed_by_username=request.user.username
            )
            
            if success:
                messages.success(request, _('نقش با موفقیت از کاربر حذف شد.'))
            else:
                messages.error(request, _('نقش فعال برای این کاربر یافت نشد.'))
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Error removing role: {str(e)}")
            messages.error(request, _('خطا در حذف نقش'))
        
        return redirect('admin_panel:rbac_user_assignments')


@method_decorator(require_permission('rbac.view'), name='dispatch')
class PermissionMatrixView(SuperAdminRequiredMixin, TemplateView):
    """
    View to display permission matrix for all roles.
    """
    template_name = 'admin_panel/security/permission_matrix.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all active roles
        roles = SuperAdminRole.objects.filter(is_active=True).prefetch_related('permissions')
        
        # Get all permissions grouped by section
        permissions = SuperAdminPermission.objects.filter(is_active=True).order_by('section', 'action')
        permissions_by_section = {}
        for permission in permissions:
            if permission.section not in permissions_by_section:
                permissions_by_section[permission.section] = []
            permissions_by_section[permission.section].append(permission)
        
        # Build permission matrix
        matrix = {}
        for role in roles:
            role_permissions = set(role.permissions.values_list('id', flat=True))
            matrix[role.id] = role_permissions
        
        context.update({
            'roles': roles,
            'permissions_by_section': permissions_by_section,
            'matrix': matrix,
        })
        
        return context


# API Views for AJAX operations

@method_decorator(require_permission('rbac.view'), name='dispatch')
class RBACStatsAPIView(SuperAdminRequiredMixin, View):
    """
    API view to get RBAC statistics.
    """
    
    def get(self, request):
        """Get RBAC statistics."""
        try:
            stats = RBACService.get_role_statistics()
            return JsonResponse({
                'success': True,
                'stats': stats
            })
        except Exception as e:
            logger.error(f"Error getting RBAC stats: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'خطا در دریافت آمار'
            })


@method_decorator(require_permission('rbac.manage'), name='dispatch')
class DeleteRoleAPIView(SuperAdminRequiredMixin, View):
    """
    API view to delete a role.
    """
    
    def post(self, request):
        """Delete a role."""
        try:
            role_id = request.POST.get('role_id')
            
            success = RBACService.delete_role(
                role_id=int(role_id),
                deleted_by_id=request.user.id,
                deleted_by_username=request.user.username
            )
            
            if success:
                return JsonResponse({
                    'success': True,
                    'message': 'نقش با موفقیت حذف شد.'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'نقش یافت نشد یا قابل حذف نیست.'
                })
                
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        except Exception as e:
            logger.error(f"Error deleting role: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'خطا در حذف نقش'
            })


@method_decorator(require_permission('rbac.view'), name='dispatch')
class UserPermissionsAPIView(SuperAdminRequiredMixin, View):
    """
    API view to get user permissions.
    """
    
    def get(self, request):
        """Get permissions for a specific user."""
        try:
            user_id = request.GET.get('user_id')
            
            if not user_id:
                return JsonResponse({
                    'success': False,
                    'error': 'شناسه کاربر الزامی است.'
                })
            
            permissions = RBACService.get_user_permissions(int(user_id))
            
            permissions_data = []
            for permission in permissions:
                permissions_data.append({
                    'id': permission.id,
                    'codename': permission.codename,
                    'name': permission.name,
                    'name_persian': permission.name_persian,
                    'section': permission.section,
                    'action': permission.action,
                    'is_dangerous': permission.is_dangerous,
                })
            
            return JsonResponse({
                'success': True,
                'permissions': permissions_data
            })
            
        except Exception as e:
            logger.error(f"Error getting user permissions: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'خطا در دریافت مجوزهای کاربر'
            })


@method_decorator(require_permission('rbac.manage'), name='dispatch')
class ToggleRolePermissionAPIView(SuperAdminRequiredMixin, View):
    """
    API view to toggle a permission for a role.
    """
    
    def post(self, request):
        """Toggle permission for a role."""
        try:
            role_id = request.POST.get('role_id')
            permission_id = request.POST.get('permission_id')
            
            if not role_id or not permission_id:
                return JsonResponse({
                    'success': False,
                    'error': 'شناسه نقش و مجوز الزامی است.'
                })
            
            result = RBACService.toggle_role_permission(
                role_id=int(role_id),
                permission_id=int(permission_id),
                updated_by_id=request.user.id,
                updated_by_username=request.user.username
            )
            
            return JsonResponse({
                'success': True,
                'action': result['action'],
                'has_permission': result['has_permission'],
                'message': f"مجوز {result['permission_name']} برای نقش {result['role_name']} {'افزوده' if result['action'] == 'added' else 'حذف'} شد."
            })
            
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        except Exception as e:
            logger.error(f"Error toggling role permission: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'خطا در تغییر مجوز نقش'
            })