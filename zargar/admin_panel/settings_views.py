"""
Settings management views for super admin panel.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.http import JsonResponse, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
import json
import logging

from .models import SystemSetting, NotificationSetting, SettingChangeHistory
from .services.settings_service import SettingsManager, NotificationManager
from .views import SuperAdminRequiredMixin

logger = logging.getLogger(__name__)


class SettingsManagementView(SuperAdminRequiredMixin, TemplateView):
    """
    Main settings management interface.
    """
    template_name = 'admin_panel/settings/settings_management.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all setting categories
        categories = SettingsManager.get_all_categories()
        
        # Get current category from URL parameter
        current_category = self.request.GET.get('category', 'general')
        
        # Get settings for current category
        settings = SettingsManager.get_settings_by_category(
            current_category, 
            include_sensitive=True  # Super admin can see sensitive settings
        )
        
        # Group settings by section
        settings_by_section = {}
        for setting in settings:
            section = setting.section or 'عمومی'
            if section not in settings_by_section:
                settings_by_section[section] = []
            settings_by_section[section].append(setting)
        
        context.update({
            'categories': categories,
            'current_category': current_category,
            'current_category_display': dict(SystemSetting.CATEGORIES).get(current_category, current_category),
            'settings_by_section': settings_by_section,
            'total_settings': len(settings),
        })
        
        return context


class SettingUpdateView(SuperAdminRequiredMixin, View):
    """
    Handle individual setting updates via AJAX.
    """
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            setting_key = data.get('key')
            new_value = data.get('value')
            reason = data.get('reason', '')
            
            if not setting_key:
                return JsonResponse({
                    'success': False,
                    'error': 'Setting key is required'
                }, status=400)
            
            # Update the setting
            setting = SettingsManager.set_setting(
                key=setting_key,
                value=new_value,
                user=request.user,
                reason=reason
            )
            
            return JsonResponse({
                'success': True,
                'message': f'تنظیم "{setting.name}" با موفقیت به‌روزرسانی شد',
                'requires_restart': setting.requires_restart,
                'new_value': setting.get_typed_value(),
                'display_value': setting.get_display_value(),
            })
            
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
        except Exception as e:
            logger.error(f"Error updating setting: {e}")
            return JsonResponse({
                'success': False,
                'error': 'خطای غیرمنتظره‌ای رخ داد'
            }, status=500)


class BulkSettingsUpdateView(SuperAdminRequiredMixin, View):
    """
    Handle bulk settings updates.
    """
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            settings_data = data.get('settings', {})
            reason = data.get('reason', 'Bulk update')
            
            if not settings_data:
                return JsonResponse({
                    'success': False,
                    'error': 'No settings data provided'
                }, status=400)
            
            # Perform bulk update
            results = SettingsManager.bulk_update_settings(
                settings_data=settings_data,
                user=request.user,
                reason=reason
            )
            
            # Prepare response message
            if results['updated']:
                message = f"{len(results['updated'])} تنظیم با موفقیت به‌روزرسانی شد"
                if results['errors']:
                    message += f" ({len(results['errors'])} خطا)"
            else:
                message = "هیچ تنظیمی به‌روزرسانی نشد"
            
            return JsonResponse({
                'success': len(results['updated']) > 0,
                'message': message,
                'results': results,
            })
            
        except Exception as e:
            logger.error(f"Error in bulk settings update: {e}")
            return JsonResponse({
                'success': False,
                'error': 'خطای غیرمنتظره‌ای رخ داد'
            }, status=500)


class SettingResetView(SuperAdminRequiredMixin, View):
    """
    Reset setting to default value.
    """
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            setting_key = data.get('key')
            reason = data.get('reason', 'Reset to default')
            
            if not setting_key:
                return JsonResponse({
                    'success': False,
                    'error': 'Setting key is required'
                }, status=400)
            
            # Reset the setting
            setting = SettingsManager.reset_setting_to_default(
                key=setting_key,
                user=request.user,
                reason=reason
            )
            
            return JsonResponse({
                'success': True,
                'message': f'تنظیم "{setting.name}" به مقدار پیش‌فرض بازگردانده شد',
                'requires_restart': setting.requires_restart,
                'new_value': setting.get_typed_value(),
                'display_value': setting.get_display_value(),
            })
            
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
        except Exception as e:
            logger.error(f"Error resetting setting: {e}")
            return JsonResponse({
                'success': False,
                'error': 'خطای غیرمنتظره‌ای رخ داد'
            }, status=500)


class SettingHistoryView(SuperAdminRequiredMixin, TemplateView):
    """
    View setting change history.
    """
    template_name = 'admin_panel/settings/setting_history.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        setting_key = self.kwargs.get('key')
        limit = int(self.request.GET.get('limit', 50))
        
        try:
            setting = SystemSetting.objects.get(key=setting_key)
            history = SettingsManager.get_setting_history(setting_key, limit)
            
            context.update({
                'setting': setting,
                'history': history,
                'setting_key': setting_key,
            })
        except SystemSetting.DoesNotExist:
            context['error'] = 'تنظیم مورد نظر یافت نشد'
        
        return context


class SettingRollbackView(SuperAdminRequiredMixin, View):
    """
    Rollback setting to a previous value.
    """
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            setting_key = data.get('key')
            history_id = data.get('history_id')
            reason = data.get('reason', 'Rollback')
            
            if not setting_key or not history_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Setting key and history ID are required'
                }, status=400)
            
            # Perform rollback
            setting = SettingsManager.rollback_setting(
                key=setting_key,
                history_id=history_id,
                user=request.user,
                reason=reason
            )
            
            return JsonResponse({
                'success': True,
                'message': f'تنظیم "{setting.name}" با موفقیت بازگردانده شد',
                'requires_restart': setting.requires_restart,
                'new_value': setting.get_typed_value(),
                'display_value': setting.get_display_value(),
            })
            
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
        except Exception as e:
            logger.error(f"Error rolling back setting: {e}")
            return JsonResponse({
                'success': False,
                'error': 'خطای غیرمنتظره‌ای رخ داد'
            }, status=500)


class SettingsExportView(SuperAdminRequiredMixin, View):
    """
    Export settings to JSON file.
    """
    
    def get(self, request):
        try:
            category = request.GET.get('category')
            include_sensitive = request.GET.get('include_sensitive', 'false').lower() == 'true'
            
            # Export settings
            settings_data = SettingsManager.export_settings(
                category=category,
                include_sensitive=include_sensitive
            )
            
            # Prepare filename
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            if category:
                filename = f'settings_{category}_{timestamp}.json'
            else:
                filename = f'settings_all_{timestamp}.json'
            
            # Create response
            response = HttpResponse(
                json.dumps(settings_data, ensure_ascii=False, indent=2),
                content_type='application/json; charset=utf-8'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            logger.error(f"Error exporting settings: {e}")
            messages.error(request, 'خطا در صادرات تنظیمات')
            return redirect('admin_panel:settings_management')


class SettingsImportView(SuperAdminRequiredMixin, View):
    """
    Import settings from JSON file.
    """
    
    def post(self, request):
        try:
            uploaded_file = request.FILES.get('settings_file')
            overwrite = request.POST.get('overwrite', 'false').lower() == 'true'
            
            if not uploaded_file:
                messages.error(request, 'لطفاً فایل تنظیمات را انتخاب کنید')
                return redirect('admin_panel:settings_management')
            
            # Read and parse JSON
            try:
                settings_data = json.loads(uploaded_file.read().decode('utf-8'))
            except json.JSONDecodeError:
                messages.error(request, 'فایل انتخاب شده معتبر نیست')
                return redirect('admin_panel:settings_management')
            
            # Import settings
            results = SettingsManager.import_settings(
                settings_data=settings_data,
                user=request.user,
                overwrite=overwrite
            )
            
            # Show results
            if results['imported']:
                message = f"{len(results['imported'])} تنظیم با موفقیت وارد شد"
                if results['skipped']:
                    message += f" ({len(results['skipped'])} تنظیم نادیده گرفته شد)"
                messages.success(request, message)
            
            if results['errors']:
                for key, error in results['errors'].items():
                    messages.error(request, f"خطا در وارد کردن {key}: {error}")
            
            if results['requires_restart']:
                messages.warning(request, 'برخی تنظیمات نیاز به راه‌اندازی مجدد سیستم دارند')
            
            return redirect('admin_panel:settings_management')
            
        except Exception as e:
            logger.error(f"Error importing settings: {e}")
            messages.error(request, 'خطای غیرمنتظره‌ای در وارد کردن تنظیمات رخ داد')
            return redirect('admin_panel:settings_management')


class NotificationSettingsView(SuperAdminRequiredMixin, TemplateView):
    """
    Notification settings management.
    """
    template_name = 'admin_panel/settings/notification_settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get notification settings
        notification_settings = NotificationManager.get_notification_settings()
        
        # Group by event type
        settings_by_event = {}
        for setting in notification_settings:
            event_type = setting.event_type
            if event_type not in settings_by_event:
                settings_by_event[event_type] = []
            settings_by_event[event_type].append(setting)
        
        context.update({
            'settings_by_event': settings_by_event,
            'event_types': NotificationSetting.EVENT_TYPES,
            'notification_types': NotificationSetting.NOTIFICATION_TYPES,
            'priority_levels': NotificationSetting.PRIORITY_LEVELS,
        })
        
        return context


class NotificationSettingUpdateView(SuperAdminRequiredMixin, View):
    """
    Update notification setting.
    """
    
    def post(self, request, setting_id):
        try:
            data = json.loads(request.body)
            
            # Update notification setting
            setting = NotificationManager.update_notification_setting(
                setting_id=setting_id,
                data=data,
                user=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': f'تنظیم اعلان "{setting.name}" با موفقیت به‌روزرسانی شد',
            })
            
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
        except Exception as e:
            logger.error(f"Error updating notification setting: {e}")
            return JsonResponse({
                'success': False,
                'error': 'خطای غیرمنتظره‌ای رخ داد'
            }, status=500)


class NotificationTestView(SuperAdminRequiredMixin, View):
    """
    Test notification delivery.
    """
    
    def post(self, request, setting_id):
        try:
            data = json.loads(request.body)
            test_data = data.get('test_data', {})
            
            # Test notification
            results = NotificationManager.test_notification_delivery(
                setting_id=setting_id,
                test_data=test_data
            )
            
            if results['success']:
                return JsonResponse({
                    'success': True,
                    'message': 'تست اعلان با موفقیت انجام شد',
                    'results': results,
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': results.get('error', 'خطا در تست اعلان'),
                }, status=400)
            
        except Exception as e:
            logger.error(f"Error testing notification: {e}")
            return JsonResponse({
                'success': False,
                'error': 'خطای غیرمنتظره‌ای رخ داد'
            }, status=500)