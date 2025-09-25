"""
Settings management service for super admin panel.
"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import transaction
from typing import Dict, List, Any, Optional, Union
import json
import logging

from ..models import SystemSetting, NotificationSetting, SettingChangeHistory

# Safe import for AuditLog - handle missing table gracefully
try:
    from zargar.core.security_models import AuditLog
    AUDIT_LOG_AVAILABLE = True
except ImportError:
    AUDIT_LOG_AVAILABLE = False
    AuditLog = None

logger = logging.getLogger(__name__)


def safe_audit_log(action, user=None, content_object=None, **kwargs):
    """Safely log audit events, handling missing AuditLog table."""
    if AUDIT_LOG_AVAILABLE and AuditLog:
        try:
            AuditLog.log_action(
                action=action,
                user=user,
                content_object=content_object,
                **kwargs
            )
        except Exception as e:
            logger.warning(f"Failed to log audit event: {e}")
    else:
        logger.info(f"Audit log not available - Action: {action}, User: {user}")


class SettingsManager:
    """
    Centralized settings management service.
    """
    
    @staticmethod
    def get_setting(key: str, default: Any = None) -> Any:
        """
        Get setting value with type conversion.
        
        Args:
            key: Setting key
            default: Default value if setting doesn't exist
            
        Returns:
            Setting value converted to proper type
        """
        try:
            setting = SystemSetting.objects.get(key=key, is_active=True)
            return setting.get_typed_value()
        except SystemSetting.DoesNotExist:
            logger.warning(f"Setting '{key}' not found, returning default: {default}")
            return default
    
    @staticmethod
    def set_setting(key: str, value: Any, user=None, reason: str = '') -> SystemSetting:
        """
        Set setting value with validation and audit logging.
        
        Args:
            key: Setting key
            value: New value
            user: User making the change
            reason: Reason for the change
            
        Returns:
            Updated SystemSetting instance
            
        Raises:
            ValidationError: If value is invalid
        """
        try:
            setting = SystemSetting.objects.get(key=key)
        except SystemSetting.DoesNotExist:
            raise ValidationError(f"Setting '{key}' does not exist")
        
        if setting.is_readonly:
            raise ValidationError(f"Setting '{key}' is read-only")
        
        # Validate the new value
        validation_errors = setting.validate_value(value)
        if validation_errors:
            raise ValidationError(validation_errors)
        
        old_value = setting.value
        
        try:
            # Update the setting
            setting.set_value(value, user)
            
            # Record change history (optional, handle gracefully if table doesn't exist)
            try:
                SettingChangeHistory.objects.create(
                    setting=setting,
                    old_value=old_value,
                    new_value=setting.value,
                    change_reason=reason,
                    changed_by_id=user.id if user else None,
                    changed_by_username=user.username if user else '',
                )
            except Exception as e:
                logger.warning(f"Failed to log setting change for {key}: {e}")
        except Exception as e:
            logger.error(f"Failed to update setting {key}: {e}")
            raise
        
        logger.info(f"Setting '{key}' changed from '{old_value}' to '{setting.value}' by {user}")
        return setting
    
    @staticmethod
    def get_settings_by_category(category: str, include_sensitive: bool = False) -> List[SystemSetting]:
        """
        Get all settings in a category.
        
        Args:
            category: Setting category
            include_sensitive: Whether to include sensitive settings
            
        Returns:
            List of SystemSetting instances
        """
        queryset = SystemSetting.objects.filter(
            category=category,
            is_active=True
        ).order_by('section', 'display_order', 'name')
        
        if not include_sensitive:
            queryset = queryset.filter(is_sensitive=False)
        
        return list(queryset)
    
    @staticmethod
    def get_all_categories() -> List[Dict[str, Any]]:
        """
        Get all setting categories with counts.
        
        Returns:
            List of category information
        """
        from django.db.models import Count, Q
        
        categories = SystemSetting.objects.filter(is_active=True).values(
            'category'
        ).annotate(
            count=Count('id'),
            sensitive_count=Count('id', filter=Q(is_sensitive=True))
        ).order_by('category')
        
        return [
            {
                'category': cat['category'],
                'display_name': dict(SystemSetting.CATEGORIES).get(cat['category'], cat['category']),
                'count': cat['count'],
                'sensitive_count': cat['sensitive_count'],
            }
            for cat in categories
        ]
    
    @staticmethod
    def bulk_update_settings(settings_data: Dict[str, Any], user=None, reason: str = '') -> Dict[str, Any]:
        """
        Update multiple settings in a single transaction.
        
        Args:
            settings_data: Dictionary of {key: value} pairs
            user: User making the changes
            reason: Reason for the changes
            
        Returns:
            Dictionary with results and any errors
        """
        results = {
            'updated': [],
            'errors': {},
            'requires_restart': False,
        }
        
        with transaction.atomic():
            for key, value in settings_data.items():
                try:
                    setting = SettingsManager.set_setting(key, value, user, reason)
                    results['updated'].append({
                        'key': key,
                        'name': setting.name,
                        'old_value': setting.value,
                        'new_value': value,
                    })
                    
                    if setting.requires_restart:
                        results['requires_restart'] = True
                        
                except ValidationError as e:
                    results['errors'][key] = str(e)
                except Exception as e:
                    logger.error(f"Error updating setting '{key}': {e}")
                    results['errors'][key] = _('Unexpected error occurred')
        
        return results
    
    @staticmethod
    def reset_setting_to_default(key: str, user=None, reason: str = '') -> SystemSetting:
        """
        Reset setting to its default value.
        
        Args:
            key: Setting key
            user: User making the change
            reason: Reason for the reset
            
        Returns:
            Updated SystemSetting instance
        """
        try:
            setting = SystemSetting.objects.get(key=key)
        except SystemSetting.DoesNotExist:
            raise ValidationError(f"Setting '{key}' does not exist")
        
        if setting.is_readonly:
            raise ValidationError(f"Setting '{key}' is read-only")
        
        old_value = setting.value
        
        try:
            setting.reset_to_default(user)
            
            # Record change history (optional, handle gracefully if table doesn't exist)
            try:
                SettingChangeHistory.objects.create(
                    setting=setting,
                    old_value=old_value,
                    new_value=setting.value,
                    change_reason=f"Reset to default: {reason}",
                    changed_by_id=user.id if user else None,
                    changed_by_username=user.username if user else '',
                )
            except Exception as e:
                logger.warning(f"Failed to log setting reset for {key}: {e}")
        except Exception as e:
            logger.error(f"Failed to reset setting {key}: {e}")
            raise
        
        logger.info(f"Setting '{key}' reset to default by {user}")
        return setting
    
    @staticmethod
    def export_settings(category: str = None, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Export settings to JSON format.
        
        Args:
            category: Specific category to export (None for all)
            include_sensitive: Whether to include sensitive settings
            
        Returns:
            Dictionary containing settings data
        """
        queryset = SystemSetting.objects.filter(is_active=True)
        
        if category:
            queryset = queryset.filter(category=category)
        
        if not include_sensitive:
            queryset = queryset.filter(is_sensitive=False)
        
        settings_data = {
            'export_timestamp': timezone.now().isoformat(),
            'category': category,
            'include_sensitive': include_sensitive,
            'settings': {}
        }
        
        for setting in queryset:
            settings_data['settings'][setting.key] = {
                'name': setting.name,
                'description': setting.description,
                'value': setting.get_typed_value(),
                'default_value': setting.get_typed_default_value(),
                'setting_type': setting.setting_type,
                'category': setting.category,
                'section': setting.section,
                'is_sensitive': setting.is_sensitive,
                'requires_restart': setting.requires_restart,
            }
        
        return settings_data
    
    @staticmethod
    def import_settings(settings_data: Dict[str, Any], user=None, overwrite: bool = False) -> Dict[str, Any]:
        """
        Import settings from JSON data.
        
        Args:
            settings_data: Dictionary containing settings data
            user: User performing the import
            overwrite: Whether to overwrite existing settings
            
        Returns:
            Dictionary with import results
        """
        results = {
            'imported': [],
            'skipped': [],
            'errors': {},
            'requires_restart': False,
        }
        
        if 'settings' not in settings_data:
            raise ValidationError("Invalid settings data format")
        
        with transaction.atomic():
            for key, setting_info in settings_data['settings'].items():
                try:
                    existing_setting = SystemSetting.objects.filter(key=key).first()
                    
                    if existing_setting and not overwrite:
                        results['skipped'].append({
                            'key': key,
                            'reason': 'Setting already exists and overwrite is disabled'
                        })
                        continue
                    
                    if existing_setting:
                        # Update existing setting
                        old_value = existing_setting.value
                        
                        # Update all fields, not just value
                        existing_setting.name = setting_info.get('name', existing_setting.name)
                        existing_setting.description = setting_info.get('description', existing_setting.description)
                        existing_setting.default_value = str(setting_info.get('default_value', existing_setting.default_value))
                        existing_setting.setting_type = setting_info.get('setting_type', existing_setting.setting_type)
                        existing_setting.category = setting_info.get('category', existing_setting.category)
                        existing_setting.section = setting_info.get('section', existing_setting.section)
                        existing_setting.is_sensitive = setting_info.get('is_sensitive', existing_setting.is_sensitive)
                        existing_setting.requires_restart = setting_info.get('requires_restart', existing_setting.requires_restart)
                        
                        # Handle value with proper type conversion
                        value = setting_info['value']
                        if existing_setting.setting_type == 'json' and isinstance(value, (dict, list)):
                            value = json.dumps(value, ensure_ascii=False)
                        
                        existing_setting.value = str(value)
                        existing_setting.save()
                        
                        results['imported'].append({
                            'key': key,
                            'action': 'updated',
                            'old_value': old_value,
                            'new_value': str(value),
                        })
                        
                        if existing_setting.requires_restart:
                            results['requires_restart'] = True
                    else:
                        # Create new setting
                        value = setting_info['value']
                        default_value = setting_info.get('default_value', '')
                        
                        # Handle JSON values
                        if setting_info.get('setting_type') == 'json':
                            if isinstance(value, (dict, list)):
                                value = json.dumps(value, ensure_ascii=False)
                            if isinstance(default_value, (dict, list)):
                                default_value = json.dumps(default_value, ensure_ascii=False)
                        
                        new_setting = SystemSetting.objects.create(
                            key=key,
                            name=setting_info.get('name', key),
                            description=setting_info.get('description', ''),
                            value=str(value),
                            default_value=str(default_value),
                            setting_type=setting_info.get('setting_type', 'string'),
                            category=setting_info.get('category', 'general'),
                            section=setting_info.get('section', ''),
                            is_sensitive=setting_info.get('is_sensitive', False),
                            requires_restart=setting_info.get('requires_restart', False),
                            created_by_id=user.id if user else None,
                            created_by_username=user.username if user else '',
                        )
                        
                        results['imported'].append({
                            'key': key,
                            'action': 'created',
                            'value': setting_info['value'],
                        })
                        
                        if new_setting.requires_restart:
                            results['requires_restart'] = True
                
                except Exception as e:
                    logger.error(f"Error importing setting '{key}': {e}")
                    results['errors'][key] = str(e)
        
        return results
    
    @staticmethod
    def get_setting_history(key: str, limit: int = 50) -> List[SettingChangeHistory]:
        """
        Get change history for a setting.
        
        Args:
            key: Setting key
            limit: Maximum number of history entries to return
            
        Returns:
            List of SettingChangeHistory instances
        """
        try:
            setting = SystemSetting.objects.get(key=key)
            return list(setting.change_history.all()[:limit])
        except SystemSetting.DoesNotExist:
            return []
    
    @staticmethod
    def rollback_setting(key: str, history_id: int, user=None, reason: str = '') -> SystemSetting:
        """
        Rollback setting to a previous value.
        
        Args:
            key: Setting key
            history_id: ID of the history entry to rollback to
            user: User performing the rollback
            reason: Reason for the rollback
            
        Returns:
            Updated SystemSetting instance
        """
        try:
            setting = SystemSetting.objects.get(key=key)
            history_entry = SettingChangeHistory.objects.get(
                id=history_id,
                setting=setting
            )
        except (SystemSetting.DoesNotExist, SettingChangeHistory.DoesNotExist):
            raise ValidationError("Setting or history entry not found")
        
        if setting.is_readonly:
            raise ValidationError(f"Setting '{key}' is read-only")
        
        old_value = setting.value
        rollback_value = history_entry.old_value
        
        try:
            setting.set_value(rollback_value, user)
            
            # Record rollback in history (optional, handle gracefully if table doesn't exist)
            try:
                SettingChangeHistory.objects.create(
                    setting=setting,
                    old_value=old_value,
                    new_value=rollback_value,
                    change_reason=f"Rollback to {history_entry.changed_at}: {reason}",
                    changed_by_id=user.id if user else None,
                    changed_by_username=user.username if user else '',
                )
            except Exception as e:
                logger.warning(f"Failed to log setting rollback for {key}: {e}")
        except Exception as e:
            logger.error(f"Failed to rollback setting {key}: {e}")
            raise
        
        logger.info(f"Setting '{key}' rolled back to '{rollback_value}' by {user}")
        return setting


class NotificationManager:
    """
    Notification settings management service.
    """
    
    @staticmethod
    def get_notification_settings(event_type: str = None, notification_type: str = None) -> List[NotificationSetting]:
        """
        Get notification settings with optional filtering.
        
        Args:
            event_type: Filter by event type
            notification_type: Filter by notification type
            
        Returns:
            List of NotificationSetting instances
        """
        queryset = NotificationSetting.objects.filter(is_enabled=True)
        
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        return list(queryset.order_by('event_type', 'notification_type', 'name'))
    
    @staticmethod
    def should_send_notification(event_type: str, priority: str = 'medium', event_data: Dict = None) -> List[NotificationSetting]:
        """
        Get notification settings that should be triggered for an event.
        
        Args:
            event_type: Type of event
            priority: Event priority level
            event_data: Additional event data for condition evaluation
            
        Returns:
            List of NotificationSetting instances that should be triggered
        """
        settings = NotificationManager.get_notification_settings(event_type=event_type)
        
        triggered_settings = []
        for setting in settings:
            if setting.should_send_notification(priority, event_data):
                triggered_settings.append(setting)
        
        return triggered_settings
    
    @staticmethod
    def create_notification_setting(data: Dict[str, Any], user=None) -> NotificationSetting:
        """
        Create a new notification setting.
        
        Args:
            data: Notification setting data
            user: User creating the setting
            
        Returns:
            Created NotificationSetting instance
        """
        setting = NotificationSetting.objects.create(
            name=data['name'],
            event_type=data['event_type'],
            notification_type=data['notification_type'],
            recipients=data.get('recipients', []),
            recipient_roles=data.get('recipient_roles', []),
            conditions=data.get('conditions', {}),
            priority_threshold=data.get('priority_threshold', 'medium'),
            is_enabled=data.get('is_enabled', True),
            throttle_minutes=data.get('throttle_minutes', 0),
            quiet_hours_start=data.get('quiet_hours_start'),
            quiet_hours_end=data.get('quiet_hours_end'),
            subject_template=data.get('subject_template', ''),
            message_template=data.get('message_template', ''),
            template_variables=data.get('template_variables', {}),
            delivery_config=data.get('delivery_config', {}),
            retry_attempts=data.get('retry_attempts', 3),
            retry_delay_minutes=data.get('retry_delay_minutes', 5),
            created_by_id=user.id if user else None,
            created_by_username=user.username if user else '',
        )
        
        # Log creation
        safe_audit_log(
            action='create',
            user=user,
            content_object=setting,
            details={
                'notification_name': setting.name,
                'event_type': setting.event_type,
                'notification_type': setting.notification_type,
            }
        )
        
        logger.info(f"Notification setting '{setting.name}' created by {user}")
        return setting
    
    @staticmethod
    def update_notification_setting(setting_id: int, data: Dict[str, Any], user=None) -> NotificationSetting:
        """
        Update an existing notification setting.
        
        Args:
            setting_id: ID of the setting to update
            data: Updated data
            user: User making the update
            
        Returns:
            Updated NotificationSetting instance
        """
        try:
            setting = NotificationSetting.objects.get(id=setting_id)
        except NotificationSetting.DoesNotExist:
            raise ValidationError("Notification setting not found")
        
        old_values = {
            'name': setting.name,
            'is_enabled': setting.is_enabled,
            'recipients': setting.recipients,
            'conditions': setting.conditions,
        }
        
        # Update fields
        for field, value in data.items():
            if hasattr(setting, field):
                setattr(setting, field, value)
        
        setting.save()
        
        # Log update
        safe_audit_log(
            action='update',
            user=user,
            content_object=setting,
            old_values=old_values,
            new_values=data,
            details={
                'notification_name': setting.name,
                'event_type': setting.event_type,
                'notification_type': setting.notification_type,
            }
        )
        
        logger.info(f"Notification setting '{setting.name}' updated by {user}")
        return setting
    
    @staticmethod
    def test_notification_delivery(setting_id: int, test_data: Dict = None) -> Dict[str, Any]:
        """
        Test notification delivery for a setting.
        
        Args:
            setting_id: ID of the notification setting
            test_data: Test event data
            
        Returns:
            Dictionary with test results
        """
        try:
            setting = NotificationSetting.objects.get(id=setting_id)
        except NotificationSetting.DoesNotExist:
            raise ValidationError("Notification setting not found")
        
        test_event_data = test_data or {
            'test_message': True,
            'timestamp': timezone.now().isoformat(),
            'event_type': setting.event_type,
        }
        
        try:
            subject, message = setting.render_message(test_event_data)
            
            # Here you would integrate with actual notification delivery services
            # For now, we'll just return the rendered content
            
            return {
                'success': True,
                'subject': subject,
                'message': message,
                'recipients': setting.recipients,
                'delivery_method': setting.notification_type,
                'test_data': test_event_data,
            }
        
        except Exception as e:
            logger.error(f"Error testing notification delivery: {e}")
            return {
                'success': False,
                'error': str(e),
            }