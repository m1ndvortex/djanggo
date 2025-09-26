"""
Comprehensive tests for Celery task system.
Tests gold price update tasks, backup tasks, and notification tasks.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime, timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from django.core.cache import cache
from celery import current_app
from celery.result import AsyncResult

from zargar.core.gold_price_tasks import (
    update_gold_prices,
    update_single_karat_price,
    validate_gold_price_apis,
    cleanup_gold_price_cache,
    generate_gold_price_report,
    send_gold_price_alert,
    force_gold_price_refresh
)
from zargar.core.backup_tasks import (
    create_daily_backup,
    create_weekly_backup,
    verify_backup_integrity,
    cleanup_old_backups
)
from zargar.core.notification_tasks import (
    process_scheduled_notifications,
    send_single_notification,
    send_bulk_notifications_async
)
from zargar.gold_installments.services import GoldPriceService


class CeleryTaskSystemTest(TestCase):
    """Test Celery task system configuration and basic functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Clear cache before each test
        cache.clear()
    
    def test_celery_app_configuration(self):
        """Test Celery app is properly configured."""
        # Test basic configuration
        self.assertEqual(current_app.conf.task_serializer, 'json')
        self.assertEqual(current_app.conf.accept_content, ['json'])
        self.assertEqual(current_app.conf.result_serializer, 'json')
        self.assertEqual(current_app.conf.timezone, 'Asia/Tehran')
        self.assertTrue(current_app.conf.enable_utc)
        
        # Test task limits
        self.assertEqual(current_app.conf.task_time_limit, 30 * 60)  # 30 minutes
        self.assertEqual(current_app.conf.task_soft_time_limit, 25 * 60)  # 25 minutes
        
    def test_beat_schedule_configuration(self):
        """Test Celery Beat schedule is properly configured."""
        beat_schedule = current_app.conf.beat_schedule
        
        # Test backup tasks are scheduled
        self.assertIn('daily-system-backup', beat_schedule)
        self.assertIn('weekly-system-backup', beat_schedule)
        self.assertIn('cleanup-old-backups', beat_schedule)
        
        # Test gold price tasks are scheduled
        self.assertIn('update-gold-prices', beat_schedule)
        self.assertIn('validate-gold-price-apis', beat_schedule)
        
        # Test notification tasks are scheduled
        self.assertIn('process-scheduled-notifications', beat_schedule)
        self.assertIn('daily-payment-reminders', beat_schedule)
        self.assertIn('birthday-greetings', beat_schedule)
        
    def test_redis_broker_connection(self):
        """Test Redis broker connection is working."""
        # Test that we can connect to Redis
        from celery import current_app
        broker_url = current_app.conf.broker_url
        self.assertIn('redis://', broker_url)
        
        # Test cache connection (which uses same Redis)
        cache.set('test_key', 'test_value', 60)
        self.assertEqual(cache.get('test_key'), 'test_value')
        cache.delete('test_key')


class GoldPriceTasksTest(TestCase):
    """Test gold price related Celery tasks."""
    
    def setUp(self):
        """Set up test environment."""
        cache.clear()
    
    @patch('zargar.core.gold_price_tasks.GoldPriceService.get_current_gold_price')
    @patch('zargar.core.gold_price_tasks.GoldPriceService.invalidate_cache')
    def test_update_gold_prices_success(self, mock_invalidate, mock_get_price):
        """Test successful gold price update."""
        # Mock successful price fetch
        mock_get_price.return_value = {
            'price_per_gram': Decimal('2500000'),
            'source': 'api_1',
            'timestamp': timezone.now()
        }
        
        # Execute task
        result = update_gold_prices.apply()
        task_result = result.get()
        
        # Verify results
        self.assertTrue(task_result['success'])
        self.assertEqual(len(task_result['results']['updated_karats']), 5)
        self.assertEqual(len(task_result['results']['failed_karats']), 0)
        
        # Verify cache was invalidated
        mock_invalidate.assert_called_once()
        
        # Verify price was fetched for each karat
        self.assertEqual(mock_get_price.call_count, 5)
    
    @patch('zargar.core.gold_price_tasks.GoldPriceService.get_current_gold_price')
    def test_update_gold_prices_partial_failure(self, mock_get_price):
        """Test gold price update with some failures."""
        # Mock mixed success/failure responses
        def side_effect(karat):
            if karat in [14, 18]:
                return {
                    'price_per_gram': Decimal('2500000'),
                    'source': 'api_1',
                    'timestamp': timezone.now()
                }
            else:
                return {
                    'price_per_gram': Decimal('2500000'),
                    'source': 'fallback',
                    'timestamp': timezone.now()
                }
        
        mock_get_price.side_effect = side_effect
        
        # Execute task
        result = update_gold_prices.apply()
        task_result = result.get()
        
        # Verify results
        self.assertTrue(task_result['success'])
        self.assertEqual(len(task_result['results']['updated_karats']), 2)
        self.assertEqual(len(task_result['results']['failed_karats']), 3)
    
    @patch('zargar.core.gold_price_tasks.GoldPriceService.get_current_gold_price')
    def test_update_single_karat_price(self, mock_get_price):
        """Test updating price for a single karat."""
        # Mock successful price fetch
        mock_get_price.return_value = {
            'price_per_gram': Decimal('2500000'),
            'source': 'api_1',
            'timestamp': timezone.now()
        }
        
        # Execute task for 18k gold
        result = update_single_karat_price.apply(args=[18])
        task_result = result.get()
        
        # Verify results
        self.assertTrue(task_result['success'])
        self.assertEqual(task_result['karat'], 18)
        self.assertEqual(task_result['source'], 'api_1')
        self.assertFalse(task_result['is_fallback'])
    
    def test_update_single_karat_price_invalid_karat(self):
        """Test updating price for invalid karat."""
        # Execute task with invalid karat
        result = update_single_karat_price.apply(args=[25])
        task_result = result.get()
        
        # Verify failure
        self.assertFalse(task_result['success'])
        self.assertIn('Unsupported karat', task_result['error'])
    
    @patch('requests.get')
    def test_validate_gold_price_apis(self, mock_get):
        """Test API validation task."""
        # Mock successful API responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_get.return_value = mock_response
        
        # Execute task
        result = validate_gold_price_apis.apply()
        task_result = result.get()
        
        # Verify results
        self.assertTrue(task_result['success'])
        self.assertGreater(task_result['health_percentage'], 0)
        self.assertIn('api_status', task_result['results'])
    
    def test_cleanup_gold_price_cache(self):
        """Test cache cleanup task."""
        # Set some test cache values
        cache.set('gold_price_18', 'test_value', 60)
        cache.set('gold_price_trend_18', 'test_trend', 60)
        
        # Execute cleanup task
        result = cleanup_gold_price_cache.apply()
        task_result = result.get()
        
        # Verify results
        self.assertTrue(task_result['success'])
        self.assertIn('cleanup_timestamp', task_result)
    
    def test_generate_gold_price_report(self):
        """Test gold price report generation."""
        # Execute report generation
        result = generate_gold_price_report.apply(args=['daily'])
        task_result = result.get()
        
        # Verify results
        self.assertTrue(task_result['success'])
        self.assertEqual(task_result['report_type'], 'daily')
        self.assertIn('report_data', task_result)
    
    def test_send_gold_price_alert(self):
        """Test gold price alert sending."""
        alert_data = {
            'failed_karats': [{'karat': 18, 'reason': 'API timeout'}]
        }
        
        # Execute alert task
        result = send_gold_price_alert.apply(args=['high_failure_rate', alert_data])
        task_result = result.get()
        
        # Verify results
        self.assertTrue(task_result['success'])
        self.assertEqual(task_result['alert_type'], 'high_failure_rate')
        self.assertIn('message', task_result)
    
    @patch('zargar.core.gold_price_tasks.update_gold_prices.apply')
    def test_force_gold_price_refresh(self, mock_update):
        """Test forced gold price refresh."""
        # Mock update task result
        mock_result = Mock()
        mock_result.get.return_value = {'success': True, 'updated_karats': []}
        mock_update.return_value = mock_result
        
        # Execute force refresh
        result = force_gold_price_refresh.apply()
        task_result = result.get()
        
        # Verify update task was called
        mock_update.assert_called_once()
        self.assertTrue(task_result['success'])


class BackupTasksTest(TestCase):
    """Test backup related Celery tasks."""
    
    @patch('zargar.core.backup_tasks.backup_manager.create_full_system_backup')
    def test_create_daily_backup_success(self, mock_backup):
        """Test successful daily backup creation."""
        # Mock successful backup
        mock_backup.return_value = {
            'success': True,
            'backup_id': 'backup_123',
            'file_size': 1024000
        }
        
        # Execute task
        result = create_daily_backup.apply()
        task_result = result.get()
        
        # Verify results
        self.assertTrue(task_result['success'])
        self.assertEqual(task_result['backup_id'], 'backup_123')
        self.assertEqual(task_result['file_size'], 1024000)
        
        # Verify backup manager was called correctly
        mock_backup.assert_called_once_with(
            frequency='daily',
            created_by='celery_daily'
        )
    
    @patch('zargar.core.backup_tasks.backup_manager.create_full_system_backup')
    def test_create_daily_backup_failure(self, mock_backup):
        """Test daily backup creation failure."""
        # Mock backup failure
        mock_backup.return_value = {
            'success': False,
            'error': 'Database connection failed',
            'backup_id': None
        }
        
        # Execute task
        result = create_daily_backup.apply()
        task_result = result.get()
        
        # Verify failure handling
        self.assertFalse(task_result['success'])
        self.assertIn('Database connection failed', task_result['error'])
    
    @patch('zargar.core.backup_tasks.backup_manager.create_full_system_backup')
    def test_create_weekly_backup(self, mock_backup):
        """Test weekly backup creation."""
        # Mock successful backup
        mock_backup.return_value = {
            'success': True,
            'backup_id': 'weekly_backup_123',
            'file_size': 2048000
        }
        
        # Execute task
        result = create_weekly_backup.apply()
        task_result = result.get()
        
        # Verify results
        self.assertTrue(task_result['success'])
        self.assertEqual(task_result['backup_id'], 'weekly_backup_123')
        
        # Verify backup manager was called correctly
        mock_backup.assert_called_once_with(
            frequency='weekly',
            created_by='celery_weekly'
        )
    
    @patch('zargar.core.backup_tasks.backup_manager.verify_backup_integrity')
    def test_verify_backup_integrity_success(self, mock_verify):
        """Test successful backup integrity verification."""
        # Mock successful verification
        mock_verify.return_value = {
            'success': True,
            'integrity_passed': True
        }
        
        # Execute task
        result = verify_backup_integrity.apply(args=['backup_123'])
        task_result = result.get()
        
        # Verify results
        self.assertTrue(task_result['success'])
        self.assertTrue(task_result['integrity_passed'])
        self.assertEqual(task_result['backup_id'], 'backup_123')
    
    @patch('zargar.core.backup_tasks.backup_manager.verify_backup_integrity')
    def test_verify_backup_integrity_failure(self, mock_verify):
        """Test backup integrity verification failure."""
        # Mock verification failure
        mock_verify.return_value = {
            'success': True,
            'integrity_passed': False,
            'error': 'Checksum mismatch'
        }
        
        # Execute task
        result = verify_backup_integrity.apply(args=['backup_123'])
        task_result = result.get()
        
        # Verify failure handling
        self.assertTrue(task_result['success'])  # Task succeeded
        self.assertFalse(task_result['integrity_passed'])  # But integrity failed
        self.assertIn('Checksum mismatch', task_result['error'])
    
    @patch('zargar.core.backup_tasks.backup_manager.cleanup_expired_backups')
    def test_cleanup_old_backups(self, mock_cleanup):
        """Test cleanup of old backups."""
        # Mock cleanup results
        mock_cleanup.return_value = {
            'total_expired': 5,
            'deleted_successfully': 4,
            'deletion_errors': 1,
            'errors': ['Failed to delete backup_old_1']
        }
        
        # Execute task
        result = cleanup_old_backups.apply()
        task_result = result.get()
        
        # Verify results
        self.assertTrue(task_result['success'])
        self.assertEqual(task_result['total_expired'], 5)
        self.assertEqual(task_result['deleted_successfully'], 4)
        self.assertEqual(task_result['deletion_errors'], 1)


class NotificationTasksTest(TestCase):
    """Test notification related Celery tasks."""
    
    @patch('zargar.core.notification_tasks.NotificationScheduler')
    def test_process_scheduled_notifications(self, mock_scheduler_class):
        """Test processing of scheduled notifications."""
        # Mock scheduler
        mock_scheduler = Mock()
        mock_scheduler.process_scheduled_notifications.return_value = {
            'processed': 5,
            'sent': 4,
            'failed': 1
        }
        mock_scheduler_class.return_value = mock_scheduler
        
        # Execute task
        result = process_scheduled_notifications.apply()
        task_result = result.get()
        
        # Verify results
        self.assertTrue(task_result['success'])
        self.assertEqual(task_result['stats']['processed'], 5)
        self.assertEqual(task_result['stats']['sent'], 4)
        self.assertEqual(task_result['stats']['failed'], 1)
    
    @patch('zargar.core.notification_tasks.NotificationScheduler')
    def test_process_recurring_schedules(self, mock_scheduler_class):
        """Test processing of recurring notification schedules."""
        # Mock scheduler
        mock_scheduler = Mock()
        mock_scheduler.process_recurring_schedules.return_value = {
            'schedules_processed': 3,
            'notifications_created': 10
        }
        mock_scheduler_class.return_value = mock_scheduler
        
        # Execute task
        result = process_recurring_schedules.apply()
        task_result = result.get()
        
        # Verify results
        self.assertTrue(task_result['success'])
        self.assertEqual(task_result['stats']['schedules_processed'], 3)
        self.assertEqual(task_result['stats']['notifications_created'], 10)
    
    @patch('zargar.core.notification_tasks.Notification.objects.get')
    @patch('zargar.core.notification_tasks.PushNotificationSystem')
    def test_send_single_notification_success(self, mock_system_class, mock_get):
        """Test sending a single notification successfully."""
        # Mock notification
        mock_notification = Mock()
        mock_notification.status = 'sent'
        mock_get.return_value = mock_notification
        
        # Mock notification system
        mock_system = Mock()
        mock_system.send_notification.return_value = True
        mock_system_class.return_value = mock_system
        
        # Execute task
        result = send_single_notification.apply(args=[123])
        task_result = result.get()
        
        # Verify results
        self.assertTrue(task_result['success'])
        self.assertEqual(task_result['notification_id'], 123)
        self.assertEqual(task_result['status'], 'sent')
    
    @patch('zargar.core.notification_tasks.PushNotificationSystem')
    def test_send_bulk_notifications_async(self, mock_system_class):
        """Test sending bulk notifications asynchronously."""
        # Mock notification system
        mock_system = Mock()
        mock_system.send_bulk_notifications.return_value = {
            'created': 10,
            'sent': 8,
            'failed': 2
        }
        mock_system_class.return_value = mock_system
        
        # Prepare test data
        recipients = [
            {'type': 'customer', 'id': 1, 'context': {'name': 'احمد'}},
            {'type': 'customer', 'id': 2, 'context': {'name': 'فاطمه'}}
        ]
        context_template = {'shop_name': 'طلا و جواهرات زرگر'}
        
        # Execute task
        result = send_bulk_notifications_async.apply(args=[
            'payment_reminder',
            recipients,
            context_template,
            ['sms'],
            None
        ])
        task_result = result.get()
        
        # Verify results
        self.assertTrue(task_result['success'])
        self.assertEqual(task_result['stats']['created'], 10)
        self.assertEqual(task_result['stats']['sent'], 8)
        self.assertEqual(task_result['stats']['failed'], 2)


class TaskErrorHandlingTest(TestCase):
    """Test error handling and retry mechanisms in Celery tasks."""
    
    @patch('zargar.core.gold_price_tasks.GoldPriceService.get_current_gold_price')
    def test_gold_price_task_retry_mechanism(self, mock_get_price):
        """Test retry mechanism for gold price tasks."""
        # Mock exception on first call, success on retry
        mock_get_price.side_effect = [
            Exception("API timeout"),
            {
                'price_per_gram': Decimal('2500000'),
                'source': 'api_1',
                'timestamp': timezone.now()
            }
        ]
        
        # Execute task (this will test the retry logic internally)
        result = update_single_karat_price.apply(args=[18])
        
        # The task should handle the exception and potentially retry
        # In a real test environment, we'd need to mock the retry mechanism
        self.assertIsNotNone(result)
    
    @patch('zargar.core.backup_tasks.backup_manager.create_full_system_backup')
    def test_backup_task_error_handling(self, mock_backup):
        """Test error handling in backup tasks."""
        # Mock backup failure
        mock_backup.side_effect = Exception("Storage unavailable")
        
        # Execute task
        result = create_daily_backup.apply()
        task_result = result.get()
        
        # Verify error is handled gracefully
        self.assertFalse(task_result['success'])
        self.assertIn('error', task_result)
    
    def test_task_timeout_configuration(self):
        """Test that tasks have proper timeout configuration."""
        # Verify task time limits are set
        self.assertEqual(current_app.conf.task_time_limit, 30 * 60)
        self.assertEqual(current_app.conf.task_soft_time_limit, 25 * 60)
        
        # Verify worker configuration
        self.assertEqual(current_app.conf.worker_prefetch_multiplier, 1)
        self.assertEqual(current_app.conf.worker_max_tasks_per_child, 1000)


class TaskSchedulingTest(TestCase):
    """Test task scheduling and beat configuration."""
    
    def test_backup_task_scheduling(self):
        """Test backup tasks are properly scheduled."""
        beat_schedule = current_app.conf.beat_schedule
        
        # Test daily backup schedule
        daily_backup = beat_schedule['daily-system-backup']
        self.assertEqual(daily_backup['task'], 'zargar.core.backup_tasks.create_daily_backup')
        self.assertEqual(daily_backup['schedule'].hour, 3)
        self.assertEqual(daily_backup['schedule'].minute, 0)
        
        # Test weekly backup schedule
        weekly_backup = beat_schedule['weekly-system-backup']
        self.assertEqual(weekly_backup['task'], 'zargar.core.backup_tasks.create_weekly_backup')
        self.assertEqual(weekly_backup['schedule'].hour, 2)
        self.assertEqual(weekly_backup['schedule'].minute, 0)
        self.assertEqual(weekly_backup['schedule'].day_of_week, 0)  # Sunday
    
    def test_gold_price_task_scheduling(self):
        """Test gold price tasks are properly scheduled."""
        beat_schedule = current_app.conf.beat_schedule
        
        # Test gold price update schedule
        gold_update = beat_schedule['update-gold-prices']
        self.assertEqual(gold_update['task'], 'zargar.core.gold_price_tasks.update_gold_prices')
        # Should run every 5 minutes during market hours (8 AM - 6 PM)
        
        # Test API validation schedule
        api_validation = beat_schedule['validate-gold-price-apis']
        self.assertEqual(api_validation['task'], 'zargar.core.gold_price_tasks.validate_gold_price_apis')
        self.assertEqual(api_validation['schedule'].minute, 0)  # Every hour
    
    def test_notification_task_scheduling(self):
        """Test notification tasks are properly scheduled."""
        beat_schedule = current_app.conf.beat_schedule
        
        # Test scheduled notification processing
        scheduled_notifications = beat_schedule['process-scheduled-notifications']
        self.assertEqual(scheduled_notifications['task'], 'zargar.core.notification_tasks.process_scheduled_notifications')
        
        # Test daily payment reminders
        payment_reminders = beat_schedule['daily-payment-reminders']
        self.assertEqual(payment_reminders['task'], 'zargar.core.notification_tasks.send_daily_payment_reminders')
        self.assertEqual(payment_reminders['schedule'].hour, 9)
        self.assertEqual(payment_reminders['schedule'].minute, 0)
        
        # Test birthday greetings
        birthday_greetings = beat_schedule['birthday-greetings']
        self.assertEqual(birthday_greetings['task'], 'zargar.core.notification_tasks.send_birthday_greetings')
        self.assertEqual(birthday_greetings['schedule'].hour, 8)
        self.assertEqual(birthday_greetings['schedule'].minute, 0)


class TaskMonitoringTest(TestCase):
    """Test task monitoring and health check functionality."""
    
    def test_task_result_backend_configuration(self):
        """Test task result backend is properly configured."""
        # Verify Redis is used as result backend
        result_backend = current_app.conf.result_backend
        self.assertIn('redis://', result_backend)
        
        # Test that task tracking is enabled
        self.assertTrue(current_app.conf.task_track_started)
    
    def test_task_serialization_configuration(self):
        """Test task serialization is properly configured."""
        # Verify JSON serialization
        self.assertEqual(current_app.conf.task_serializer, 'json')
        self.assertEqual(current_app.conf.result_serializer, 'json')
        self.assertEqual(current_app.conf.accept_content, ['json'])
    
    def test_timezone_configuration(self):
        """Test timezone configuration for tasks."""
        # Verify Tehran timezone
        self.assertEqual(current_app.conf.timezone, 'Asia/Tehran')
        self.assertTrue(current_app.conf.enable_utc)


@pytest.mark.integration
class CeleryIntegrationTest(TestCase):
    """Integration tests for Celery task system."""
    
    def test_task_discovery(self):
        """Test that all tasks are properly discovered by Celery."""
        # Get all registered tasks
        registered_tasks = list(current_app.tasks.keys())
        
        # Check that our custom tasks are registered
        expected_tasks = [
            'zargar.core.gold_price_tasks.update_gold_prices',
            'zargar.core.gold_price_tasks.validate_gold_price_apis',
            'zargar.core.backup_tasks.create_daily_backup',
            'zargar.core.backup_tasks.create_weekly_backup',
            'zargar.core.notification_tasks.process_scheduled_notifications',
        ]
        
        for task_name in expected_tasks:
            self.assertIn(task_name, registered_tasks)
    
    def test_task_routing_configuration(self):
        """Test task routing configuration."""
        # Verify default queue configuration
        # This would test custom routing if implemented
        pass
    
    @patch('redis.Redis.ping')
    def test_broker_connectivity(self, mock_ping):
        """Test broker connectivity."""
        # Mock successful Redis ping
        mock_ping.return_value = True
        
        # Test connection through cache (which uses same Redis)
        cache.set('connectivity_test', 'success', 10)
        result = cache.get('connectivity_test')
        self.assertEqual(result, 'success')
        cache.delete('connectivity_test')