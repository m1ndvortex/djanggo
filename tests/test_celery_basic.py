"""
Basic Celery task system tests.
Tests Celery configuration and basic functionality without importing task modules directly.
"""
import pytest
from django.test import TestCase
from django.core.cache import cache
from celery import current_app


class CeleryBasicTest(TestCase):
    """Test basic Celery configuration and functionality."""
    
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
        broker_url = current_app.conf.broker_url
        self.assertIn('redis://', broker_url)
        
        # Test cache connection (which uses same Redis)
        cache.set('test_key', 'test_value', 60)
        self.assertEqual(cache.get('test_key'), 'test_value')
        cache.delete('test_key')
    
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
    
    def test_worker_configuration(self):
        """Test worker configuration."""
        # Verify worker configuration
        self.assertEqual(current_app.conf.worker_prefetch_multiplier, 1)
        self.assertEqual(current_app.conf.worker_max_tasks_per_child, 1000)
    
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


class CeleryTaskDiscoveryTest(TestCase):
    """Test Celery task discovery and registration."""
    
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
            self.assertIn(task_name, registered_tasks, f"Task {task_name} not found in registered tasks")
    
    def test_celery_app_name(self):
        """Test Celery app name is correct."""
        self.assertEqual(current_app.main, 'zargar')
    
    def test_broker_and_backend_urls(self):
        """Test broker and backend URLs are properly configured."""
        # Both should use Redis
        broker_url = current_app.conf.broker_url
        result_backend = current_app.conf.result_backend
        
        self.assertIn('redis://', broker_url)
        self.assertIn('redis://', result_backend)
        
        # Should use the same Redis instance
        self.assertTrue(broker_url.startswith('redis://'))
        self.assertTrue(result_backend.startswith('redis://'))