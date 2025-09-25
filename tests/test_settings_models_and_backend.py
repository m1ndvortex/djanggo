"""
Unit tests for settings models and backend functionality.
"""
import pytest
import json
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

from zargar.admin_panel.models import (
    SystemSetting, 
    NotificationSetting, 
    SettingChangeHistory
)
from zargar.admin_panel.services import SettingsManager, NotificationManager
from zargar.core.security_models import AuditLog

User = get_user_model()


class SystemSettingModelTest(TestCase):
    """Test SystemSetting model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.setting = SystemSetting.objects.create(
            key='test.setting',
            name='Test Setting',
            description='A test setting',
            value='test_value',
            default_value='default_value',
            setting_type='string',
            category='general',
            section='test',
        )
    
    def test_string_setting_type_conversion(self):
        """Test string setting type conversion."""
        self.setting.setting_type = 'string'
        self.setting.value = 'hello world'
        self.setting.save()
        
        self.assertEqual(self.setting.get_typed_value(), 'hello world')
    
    def test_integer_setting_type_conversion(self):
        """Test integer setting type conversion."""
        self.setting.setting_type = 'integer'
        self.setting.value = '42'
        self.setting.save()
        
        self.assertEqual(self.setting.get_typed_value(), 42)
    
    def test_boolean_setting_type_conversion(self):
        """Test boolean setting type conversion."""
        self.setting.setting_type = 'boolean'
        
        # Test true values
        for true_value in ['true', 'True', '1', 'yes', 'on']:
            self.setting.value = true_value
            self.setting.save()
            self.assertTrue(self.setting.get_typed_value())
        
        # Test false values
        for false_value in ['false', 'False', '0', 'no', 'off']:
            self.setting.value = false_value
            self.setting.save()
            self.assertFalse(self.setting.get_typed_value())
    
    def test_json_setting_type_conversion(self):
        """Test JSON setting type conversion."""
        self.setting.setting_type = 'json'
        test_data = {'key': 'value', 'number': 42, 'list': [1, 2, 3]}
        self.setting.value = json.dumps(test_data)
        self.setting.save()
        
        self.assertEqual(self.setting.get_typed_value(), test_data)
    
    def test_float_setting_type_conversion(self):
        """Test float setting type conversion."""
        self.setting.setting_type = 'float'
        self.setting.value = '3.14'
        self.setting.save()
        
        self.assertEqual(self.setting.get_typed_value(), 3.14)
    
    def test_invalid_type_conversion_returns_default(self):
        """Test that invalid type conversion returns default value."""
        self.setting.setting_type = 'integer'
        self.setting.value = 'not_a_number'
        self.setting.default_value = '10'
        self.setting.save()
        
        self.assertEqual(self.setting.get_typed_value(), 10)
    
    def test_set_value_with_audit_logging(self):
        """Test setting value with audit logging."""
        old_value = self.setting.value
        new_value = 'new_test_value'
        
        with patch('zargar.admin_panel.models.AuditLog.log_action') as mock_log:
            self.setting.set_value(new_value, self.user)
            
            self.assertEqual(self.setting.value, new_value)
            self.assertEqual(self.setting.updated_by_id, self.user.id)
            self.assertEqual(self.setting.updated_by_username, self.user.username)
            
            # Verify audit log was called
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            self.assertEqual(call_args[1]['action'], 'configuration_change')
            self.assertEqual(call_args[1]['user'], self.user)
            self.assertEqual(call_args[1]['old_values']['value'], old_value)
            self.assertEqual(call_args[1]['new_values']['value'], new_value)
    
    def test_validate_value_with_choices(self):
        """Test value validation with choices."""
        self.setting.choices = ['option1', 'option2', 'option3']
        self.setting.save()
        
        # Valid choice
        errors = self.setting.validate_value('option1')
        self.assertEqual(len(errors), 0)
        
        # Invalid choice
        errors = self.setting.validate_value('invalid_option')
        self.assertEqual(len(errors), 1)
        self.assertIn('Value must be one of', errors[0])
    
    def test_validate_value_with_custom_rules(self):
        """Test value validation with custom rules."""
        self.setting.validation_rules = {
            'min_length': 5,
            'max_length': 20,
            'pattern': r'^[a-zA-Z]+$'
        }
        self.setting.save()
        
        # Valid value
        errors = self.setting.validate_value('validtext')
        self.assertEqual(len(errors), 0)
        
        # Too short
        errors = self.setting.validate_value('abc')
        self.assertEqual(len(errors), 1)
        self.assertIn('at least 5 characters', errors[0])
        
        # Too long
        errors = self.setting.validate_value('a' * 25)
        self.assertEqual(len(errors), 1)
        self.assertIn('at most 20 characters', errors[0])
        
        # Invalid pattern
        errors = self.setting.validate_value('invalid123')
        self.assertEqual(len(errors), 1)
        self.assertIn('does not match required pattern', errors[0])
    
    def test_validate_numeric_ranges(self):
        """Test numeric validation rules."""
        self.setting.setting_type = 'integer'
        self.setting.validation_rules = {
            'min_value': 10,
            'max_value': 100
        }
        self.setting.save()
        
        # Valid value
        errors = self.setting.validate_value('50')
        self.assertEqual(len(errors), 0)
        
        # Too small
        errors = self.setting.validate_value('5')
        self.assertEqual(len(errors), 1)
        self.assertIn('at least 10', errors[0])
        
        # Too large
        errors = self.setting.validate_value('150')
        self.assertEqual(len(errors), 1)
        self.assertIn('at most 100', errors[0])
    
    def test_reset_to_default(self):
        """Test resetting setting to default value."""
        self.setting.value = 'changed_value'
        self.setting.save()
        
        with patch('zargar.admin_panel.models.AuditLog.log_action') as mock_log:
            self.setting.reset_to_default(self.user)
            
            self.assertEqual(self.setting.value, self.setting.default_value)
            mock_log.assert_called_once()


class NotificationSettingModelTest(TestCase):
    """Test NotificationSetting model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.notification = NotificationSetting.objects.create(
            name='Test Notification',
            event_type='security_alert',
            notification_type='email',
            recipients=['admin@example.com'],
            priority_threshold='medium',
            is_enabled=True,
            throttle_minutes=30,
        )
    
    def test_should_send_notification_priority_check(self):
        """Test priority threshold checking."""
        # Should send for high priority (above medium)
        self.assertTrue(self.notification.should_send_notification('high'))
        
        # Should send for critical priority (above medium)
        self.assertTrue(self.notification.should_send_notification('critical'))
        
        # Should send for medium priority (equal to threshold)
        self.assertTrue(self.notification.should_send_notification('medium'))
        
        # Should not send for low priority (below medium)
        self.assertFalse(self.notification.should_send_notification('low'))
    
    def test_should_send_notification_disabled(self):
        """Test that disabled notifications are not sent."""
        self.notification.is_enabled = False
        self.notification.save()
        
        self.assertFalse(self.notification.should_send_notification('critical'))
    
    def test_should_send_notification_throttling(self):
        """Test notification throttling."""
        # Set last sent time to 15 minutes ago (less than 30 minute throttle)
        self.notification.last_sent_at = timezone.now() - timezone.timedelta(minutes=15)
        self.notification.save()
        
        # Should not send due to throttling
        self.assertFalse(self.notification.should_send_notification('high'))
        
        # Set last sent time to 45 minutes ago (more than 30 minute throttle)
        self.notification.last_sent_at = timezone.now() - timezone.timedelta(minutes=45)
        self.notification.save()
        
        # Should send now
        self.assertTrue(self.notification.should_send_notification('high'))
    
    def test_should_send_notification_quiet_hours(self):
        """Test quiet hours functionality."""
        from datetime import time
        
        # Set quiet hours from 22:00 to 06:00
        self.notification.quiet_hours_start = time(22, 0)
        self.notification.quiet_hours_end = time(6, 0)
        self.notification.save()
        
        # Mock current time to be in quiet hours (23:00)
        with patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value.time.return_value = time(23, 0)
            self.assertFalse(self.notification.should_send_notification('high'))
        
        # Mock current time to be outside quiet hours (10:00)
        with patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value.time.return_value = time(10, 0)
            self.assertTrue(self.notification.should_send_notification('high'))
    
    def test_evaluate_conditions(self):
        """Test custom condition evaluation."""
        self.notification.conditions = {
            'tenant_id': {'equals': 'test_tenant'},
            'error_count': {'greater_than': 5},
            'message': {'contains': 'critical'}
        }
        self.notification.save()
        
        # Event data that matches all conditions
        matching_data = {
            'tenant_id': 'test_tenant',
            'error_count': 10,
            'message': 'This is a critical error'
        }
        self.assertTrue(self.notification._evaluate_conditions(matching_data))
        
        # Event data that doesn't match conditions
        non_matching_data = {
            'tenant_id': 'other_tenant',
            'error_count': 3,
            'message': 'Minor warning'
        }
        self.assertFalse(self.notification._evaluate_conditions(non_matching_data))
    
    def test_render_message(self):
        """Test message template rendering."""
        self.notification.subject_template = 'Alert: {event_type}'
        self.notification.message_template = 'Error occurred: {error_message} at {timestamp}'
        self.notification.save()
        
        event_data = {
            'event_type': 'Database Error',
            'error_message': 'Connection timeout',
            'timestamp': '2023-01-01 12:00:00'
        }
        
        subject, message = self.notification.render_message(event_data)
        
        self.assertEqual(subject, 'Alert: Database Error')
        self.assertEqual(message, 'Error occurred: Connection timeout at 2023-01-01 12:00:00')
    
    def test_record_sent_and_failed(self):
        """Test recording sent and failed notifications."""
        initial_sent = self.notification.total_sent
        initial_failed = self.notification.total_failed
        
        # Record successful send
        self.notification.record_sent()
        self.notification.refresh_from_db()
        
        self.assertEqual(self.notification.total_sent, initial_sent + 1)
        self.assertIsNotNone(self.notification.last_sent_at)
        
        # Record failed send
        self.notification.record_failed()
        self.notification.refresh_from_db()
        
        self.assertEqual(self.notification.total_failed, initial_failed + 1)


class SettingsManagerTest(TestCase):
    """Test SettingsManager service functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.setting = SystemSetting.objects.create(
            key='test.manager.setting',
            name='Test Manager Setting',
            description='A test setting for manager',
            value='initial_value',
            default_value='default_value',
            setting_type='string',
            category='general',
            is_active=True,
        )
    
    def test_get_setting_existing(self):
        """Test getting existing setting."""
        value = SettingsManager.get_setting('test.manager.setting')
        self.assertEqual(value, 'initial_value')
    
    def test_get_setting_non_existing_returns_default(self):
        """Test getting non-existing setting returns default."""
        value = SettingsManager.get_setting('non.existing.setting', 'default_return')
        self.assertEqual(value, 'default_return')
    
    def test_set_setting_valid_value(self):
        """Test setting valid value."""
        new_value = 'new_value'
        updated_setting = SettingsManager.set_setting(
            'test.manager.setting', 
            new_value, 
            self.user, 
            'Test update'
        )
        
        self.assertEqual(updated_setting.value, new_value)
        self.assertEqual(updated_setting.updated_by_id, self.user.id)
        
        # Check history was created
        history = SettingChangeHistory.objects.filter(setting=updated_setting).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.new_value, new_value)
        self.assertEqual(history.change_reason, 'Test update')
    
    def test_set_setting_readonly_raises_error(self):
        """Test setting readonly setting raises error."""
        self.setting.is_readonly = True
        self.setting.save()
        
        with self.assertRaises(ValidationError) as cm:
            SettingsManager.set_setting('test.manager.setting', 'new_value', self.user)
        
        self.assertIn('read-only', str(cm.exception))
    
    def test_set_setting_non_existing_raises_error(self):
        """Test setting non-existing setting raises error."""
        with self.assertRaises(ValidationError) as cm:
            SettingsManager.set_setting('non.existing.setting', 'value', self.user)
        
        self.assertIn('does not exist', str(cm.exception))
    
    def test_get_settings_by_category(self):
        """Test getting settings by category."""
        # Create additional settings
        SystemSetting.objects.create(
            key='test.category.setting1',
            name='Category Setting 1',
            category='test_category',
            is_active=True,
        )
        SystemSetting.objects.create(
            key='test.category.setting2',
            name='Category Setting 2',
            category='test_category',
            is_sensitive=True,
            is_active=True,
        )
        
        # Get non-sensitive settings
        settings = SettingsManager.get_settings_by_category('test_category', include_sensitive=False)
        self.assertEqual(len(settings), 1)
        
        # Get all settings including sensitive
        settings = SettingsManager.get_settings_by_category('test_category', include_sensitive=True)
        self.assertEqual(len(settings), 2)
    
    def test_bulk_update_settings(self):
        """Test bulk updating multiple settings."""
        # Create additional setting
        SystemSetting.objects.create(
            key='test.bulk.setting2',
            name='Bulk Setting 2',
            value='old_value2',
            setting_type='string',
            is_active=True,
        )
        
        settings_data = {
            'test.manager.setting': 'bulk_value1',
            'test.bulk.setting2': 'bulk_value2',
        }
        
        results = SettingsManager.bulk_update_settings(settings_data, self.user, 'Bulk update test')
        
        self.assertEqual(len(results['updated']), 2)
        self.assertEqual(len(results['errors']), 0)
        
        # Verify settings were updated
        setting1 = SystemSetting.objects.get(key='test.manager.setting')
        setting2 = SystemSetting.objects.get(key='test.bulk.setting2')
        
        self.assertEqual(setting1.value, 'bulk_value1')
        self.assertEqual(setting2.value, 'bulk_value2')
    
    def test_reset_setting_to_default(self):
        """Test resetting setting to default value."""
        self.setting.value = 'changed_value'
        self.setting.save()
        
        reset_setting = SettingsManager.reset_setting_to_default(
            'test.manager.setting', 
            self.user, 
            'Reset test'
        )
        
        self.assertEqual(reset_setting.value, self.setting.default_value)
        
        # Check history was created
        history = SettingChangeHistory.objects.filter(setting=reset_setting).first()
        self.assertIsNotNone(history)
        self.assertIn('Reset to default', history.change_reason)
    
    def test_export_settings(self):
        """Test exporting settings."""
        export_data = SettingsManager.export_settings(category='general')
        
        self.assertIn('export_timestamp', export_data)
        self.assertIn('settings', export_data)
        self.assertEqual(export_data['category'], 'general')
        
        # Should contain our test setting
        self.assertIn('test.manager.setting', export_data['settings'])
        setting_data = export_data['settings']['test.manager.setting']
        self.assertEqual(setting_data['name'], 'Test Manager Setting')
        self.assertEqual(setting_data['value'], 'initial_value')
    
    def test_import_settings(self):
        """Test importing settings."""
        import_data = {
            'settings': {
                'imported.setting1': {
                    'name': 'Imported Setting 1',
                    'description': 'An imported setting',
                    'value': 'imported_value',
                    'default_value': 'imported_default',
                    'setting_type': 'string',
                    'category': 'imported',
                }
            }
        }
        
        results = SettingsManager.import_settings(import_data, self.user, overwrite=False)
        
        self.assertEqual(len(results['imported']), 1)
        self.assertEqual(len(results['errors']), 0)
        
        # Verify setting was created
        imported_setting = SystemSetting.objects.get(key='imported.setting1')
        self.assertEqual(imported_setting.name, 'Imported Setting 1')
        self.assertEqual(imported_setting.value, 'imported_value')
    
    def test_get_setting_history(self):
        """Test getting setting change history."""
        # Create some history entries
        SettingChangeHistory.objects.create(
            setting=self.setting,
            old_value='old1',
            new_value='new1',
            change_reason='Change 1',
            changed_by_id=self.user.id,
            changed_by_username=self.user.username,
        )
        SettingChangeHistory.objects.create(
            setting=self.setting,
            old_value='old2',
            new_value='new2',
            change_reason='Change 2',
            changed_by_id=self.user.id,
            changed_by_username=self.user.username,
        )
        
        history = SettingsManager.get_setting_history('test.manager.setting', limit=10)
        
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].change_reason, 'Change 2')  # Most recent first
        self.assertEqual(history[1].change_reason, 'Change 1')
    
    def test_rollback_setting(self):
        """Test rolling back setting to previous value."""
        # Create history entry
        history = SettingChangeHistory.objects.create(
            setting=self.setting,
            old_value='rollback_value',
            new_value='current_value',
            change_reason='Original change',
            changed_by_id=self.user.id,
            changed_by_username=self.user.username,
        )
        
        # Rollback to the old value
        rolled_back_setting = SettingsManager.rollback_setting(
            'test.manager.setting',
            history.id,
            self.user,
            'Rollback test'
        )
        
        self.assertEqual(rolled_back_setting.value, 'rollback_value')
        
        # Check new history entry was created for rollback
        rollback_history = SettingChangeHistory.objects.filter(
            setting=self.setting
        ).order_by('-changed_at').first()
        
        self.assertIn('Rollback to', rollback_history.change_reason)


class NotificationManagerTest(TestCase):
    """Test NotificationManager service functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.notification = NotificationSetting.objects.create(
            name='Test Notification Manager',
            event_type='security_alert',
            notification_type='email',
            recipients=['admin@example.com'],
            priority_threshold='medium',
            is_enabled=True,
        )
    
    def test_get_notification_settings_all(self):
        """Test getting all notification settings."""
        settings = NotificationManager.get_notification_settings()
        self.assertEqual(len(settings), 1)
        self.assertEqual(settings[0].name, 'Test Notification Manager')
    
    def test_get_notification_settings_filtered(self):
        """Test getting filtered notification settings."""
        # Create additional notification
        NotificationSetting.objects.create(
            name='SMS Notification',
            event_type='backup_failed',
            notification_type='sms',
            recipients=['+1234567890'],
            is_enabled=True,
        )
        
        # Filter by event type
        email_settings = NotificationManager.get_notification_settings(event_type='security_alert')
        self.assertEqual(len(email_settings), 1)
        self.assertEqual(email_settings[0].notification_type, 'email')
        
        # Filter by notification type
        sms_settings = NotificationManager.get_notification_settings(notification_type='sms')
        self.assertEqual(len(sms_settings), 1)
        self.assertEqual(sms_settings[0].event_type, 'backup_failed')
    
    def test_should_send_notification(self):
        """Test determining which notifications should be sent."""
        triggered = NotificationManager.should_send_notification(
            'security_alert', 
            'high', 
            {'test': 'data'}
        )
        
        self.assertEqual(len(triggered), 1)
        self.assertEqual(triggered[0].name, 'Test Notification Manager')
        
        # Test with low priority (should not trigger)
        triggered = NotificationManager.should_send_notification(
            'security_alert', 
            'low', 
            {'test': 'data'}
        )
        
        self.assertEqual(len(triggered), 0)
    
    def test_create_notification_setting(self):
        """Test creating notification setting."""
        data = {
            'name': 'New Test Notification',
            'event_type': 'system_error',
            'notification_type': 'email',
            'recipients': ['test@example.com'],
            'priority_threshold': 'high',
            'is_enabled': True,
            'subject_template': 'Error: {error_type}',
            'message_template': 'An error occurred: {error_message}',
        }
        
        with patch('zargar.admin_panel.services.settings_service.AuditLog.log_action') as mock_log:
            notification = NotificationManager.create_notification_setting(data, self.user)
            
            self.assertEqual(notification.name, 'New Test Notification')
            self.assertEqual(notification.event_type, 'system_error')
            self.assertEqual(notification.created_by_id, self.user.id)
            
            # Verify audit log was called
            mock_log.assert_called_once()
    
    def test_update_notification_setting(self):
        """Test updating notification setting."""
        update_data = {
            'name': 'Updated Notification Name',
            'is_enabled': False,
            'recipients': ['updated@example.com'],
        }
        
        with patch('zargar.admin_panel.services.settings_service.AuditLog.log_action') as mock_log:
            updated_notification = NotificationManager.update_notification_setting(
                self.notification.id, 
                update_data, 
                self.user
            )
            
            self.assertEqual(updated_notification.name, 'Updated Notification Name')
            self.assertFalse(updated_notification.is_enabled)
            self.assertEqual(updated_notification.recipients, ['updated@example.com'])
            
            # Verify audit log was called
            mock_log.assert_called_once()
    
    def test_test_notification_delivery(self):
        """Test notification delivery testing."""
        self.notification.subject_template = 'Test: {event_type}'
        self.notification.message_template = 'Test message: {test_data}'
        self.notification.save()
        
        test_data = {
            'event_type': 'Test Event',
            'test_data': 'Sample data'
        }
        
        result = NotificationManager.test_notification_delivery(
            self.notification.id, 
            test_data
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['subject'], 'Test: Test Event')
        self.assertEqual(result['message'], 'Test message: Sample data')
        self.assertEqual(result['recipients'], ['admin@example.com'])
        self.assertEqual(result['delivery_method'], 'email')


class SettingChangeHistoryTest(TestCase):
    """Test SettingChangeHistory model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.setting = SystemSetting.objects.create(
            key='test.history.setting',
            name='Test History Setting',
            value='initial_value',
            setting_type='string',
            category='general',
        )
    
    def test_create_history_entry(self):
        """Test creating history entry."""
        history = SettingChangeHistory.objects.create(
            setting=self.setting,
            old_value='old_value',
            new_value='new_value',
            change_reason='Test change',
            changed_by_id=self.user.id,
            changed_by_username=self.user.username,
            ip_address='127.0.0.1',
            user_agent='Test Agent',
        )
        
        self.assertEqual(history.setting, self.setting)
        self.assertEqual(history.old_value, 'old_value')
        self.assertEqual(history.new_value, 'new_value')
        self.assertEqual(history.change_reason, 'Test change')
        self.assertEqual(history.changed_by_id, self.user.id)
        self.assertEqual(history.changed_by_username, self.user.username)
        self.assertEqual(history.ip_address, '127.0.0.1')
        self.assertEqual(history.user_agent, 'Test Agent')
        self.assertIsNotNone(history.changed_at)
    
    def test_history_ordering(self):
        """Test that history entries are ordered by changed_at descending."""
        # Create multiple history entries
        history1 = SettingChangeHistory.objects.create(
            setting=self.setting,
            old_value='value1',
            new_value='value2',
            change_reason='Change 1',
        )
        
        history2 = SettingChangeHistory.objects.create(
            setting=self.setting,
            old_value='value2',
            new_value='value3',
            change_reason='Change 2',
        )
        
        # Get all history entries
        history_entries = list(SettingChangeHistory.objects.all())
        
        # Should be ordered by changed_at descending (most recent first)
        self.assertEqual(history_entries[0], history2)
        self.assertEqual(history_entries[1], history1)
    
    def test_string_representation(self):
        """Test string representation of history entry."""
        history = SettingChangeHistory.objects.create(
            setting=self.setting,
            old_value='old_value',
            new_value='new_value',
            change_reason='Test change',
        )
        
        expected_str = f"{self.setting.name} changed at {history.changed_at}"
        self.assertEqual(str(history), expected_str)


@pytest.mark.django_db
class TestSettingsIntegration:
    """Integration tests for settings functionality."""
    
    def test_complete_settings_workflow(self):
        """Test complete workflow of creating, updating, and managing settings."""
        # Create user
        user = User.objects.create_user(
            username='integrationuser',
            email='integration@example.com',
            password='testpass123'
        )
        
        # Create setting
        setting = SystemSetting.objects.create(
            key='integration.test.setting',
            name='Integration Test Setting',
            description='A setting for integration testing',
            value='initial',
            default_value='default',
            setting_type='string',
            category='test',
            validation_rules={'min_length': 3, 'max_length': 20},
        )
        
        # Test getting setting value
        value = SettingsManager.get_setting('integration.test.setting')
        assert value == 'initial'
        
        # Test updating setting
        updated_setting = SettingsManager.set_setting(
            'integration.test.setting',
            'updated_value',
            user,
            'Integration test update'
        )
        assert updated_setting.value == 'updated_value'
        
        # Test history was created
        history = SettingChangeHistory.objects.filter(setting=setting).first()
        assert history is not None
        assert history.old_value == 'initial'
        assert history.new_value == 'updated_value'
        assert history.change_reason == 'Integration test update'
        
        # Test validation
        with pytest.raises(ValidationError):
            SettingsManager.set_setting(
                'integration.test.setting',
                'x',  # Too short (min_length is 3)
                user
            )
        
        # Test reset to default
        reset_setting = SettingsManager.reset_setting_to_default(
            'integration.test.setting',
            user,
            'Reset for integration test'
        )
        assert reset_setting.value == 'default'
        
        # Test export
        export_data = SettingsManager.export_settings(category='test')
        assert 'integration.test.setting' in export_data['settings']
        
        # Test rollback
        history_entries = SettingChangeHistory.objects.filter(setting=setting).order_by('-changed_at')
        rollback_history = history_entries[1]  # Second most recent (the update)
        
        rolled_back = SettingsManager.rollback_setting(
            'integration.test.setting',
            rollback_history.id,
            user,
            'Integration test rollback'
        )
        assert rolled_back.value == 'initial'  # Should be back to the old value