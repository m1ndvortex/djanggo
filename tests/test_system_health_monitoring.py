"""
Comprehensive tests for system health monitoring backend.
Tests health metrics collection, alert system, and monitoring functionality.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing Django modules
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
import json
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import connection
from django.core.cache import cache

from zargar.admin_panel.models import SystemHealthMetric, SystemHealthAlert
from zargar.admin_panel.system_health import SystemHealthMonitor, system_health_monitor
from zargar.admin_panel.tasks import (
    collect_system_health_metrics,
    cleanup_old_health_metrics,
    check_system_health_alerts,
    send_health_alert_notifications,
    generate_health_report
)
from zargar.tenants.admin_models import SuperAdmin


class SystemHealthMonitorTest(TestCase):
    """Test the SystemHealthMonitor class functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.monitor = SystemHealthMonitor()
        
        # Clear any existing metrics and alerts
        SystemHealthMetric.objects.all().delete()
        SystemHealthAlert.objects.all().delete()
    
    def test_monitor_initialization(self):
        """Test that the monitor initializes correctly."""
        self.assertIsInstance(self.monitor, SystemHealthMonitor)
        self.assertIsNotNone(self.monitor.hostname)
    
    @patch('zargar.admin_panel.system_health.psutil.cpu_percent')
    @patch('zargar.admin_panel.system_health.psutil.cpu_count')
    @patch('zargar.admin_panel.system_health.psutil.virtual_memory')
    @patch('zargar.admin_panel.system_health.psutil.disk_usage')
    def test_get_system_metrics(self, mock_disk, mock_memory, mock_cpu_count, mock_cpu_percent):
        """Test system metrics collection."""
        # Mock system metrics
        mock_cpu_percent.return_value = 45.5
        mock_cpu_count.return_value = 4
        
        mock_memory_obj = Mock()
        mock_memory_obj.total = 8589934592  # 8GB
        mock_memory_obj.available = 4294967296  # 4GB
        mock_memory_obj.used = 4294967296  # 4GB
        mock_memory_obj.percent = 50.0
        mock_memory.return_value = mock_memory_obj
        
        mock_disk_obj = Mock()
        mock_disk_obj.total = 107374182400  # 100GB
        mock_disk_obj.used = 53687091200   # 50GB
        mock_disk_obj.free = 53687091200   # 50GB
        mock_disk.return_value = mock_disk_obj
        
        # Get system metrics
        metrics = self.monitor.get_system_metrics()
        
        # Verify metrics structure
        self.assertIn('cpu', metrics)
        self.assertIn('memory', metrics)
        self.assertIn('disk', metrics)
        
        # Verify CPU metrics
        self.assertEqual(metrics['cpu']['usage_percent'], 45.5)
        self.assertEqual(metrics['cpu']['count'], 4)
        
        # Verify memory metrics
        self.assertEqual(metrics['memory']['total_bytes'], 8589934592)
        self.assertEqual(metrics['memory']['usage_percent'], 50.0)
        
        # Verify disk metrics
        self.assertEqual(metrics['disk']['total_bytes'], 107374182400)
        self.assertEqual(metrics['disk']['usage_percent'], 50.0)
    
    def test_get_database_metrics(self):
        """Test database metrics collection."""
        metrics = self.monitor.get_database_metrics()
        
        # Verify metrics structure
        self.assertIn('database', metrics)
        self.assertIn('default', metrics['database'])
        
        # Verify database connection health
        db_status = metrics['database']['default']
        self.assertIn('status', db_status)
        self.assertIn('response_time_ms', db_status)
        
        # Should be healthy since we're using real database
        self.assertEqual(db_status['status'], 'healthy')
        self.assertTrue(db_status['response_time_ms'] >= 0)
    
    @patch('zargar.admin_panel.system_health.redis.from_url')
    def test_get_redis_metrics_healthy(self, mock_redis_from_url):
        """Test Redis metrics collection when Redis is healthy."""
        # Mock Redis client
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.info.return_value = {
            'redis_version': '7.0.0',
            'uptime_in_seconds': 3600,
            'connected_clients': 5,
            'used_memory': 1048576,  # 1MB
            'used_memory_human': '1.00M',
            'used_memory_peak': 2097152,  # 2MB
            'used_memory_peak_human': '2.00M',
            'maxmemory': 134217728,  # 128MB
            'maxmemory_human': '128.00M',
            'keyspace_hits': 1000,
            'keyspace_misses': 100,
            'total_commands_processed': 5000,
        }
        mock_redis_from_url.return_value = mock_redis
        
        # Reinitialize monitor to use mocked Redis
        monitor = SystemHealthMonitor()
        
        metrics = monitor.get_redis_metrics()
        
        # Verify metrics structure
        self.assertIn('redis', metrics)
        redis_metrics = metrics['redis']
        
        self.assertEqual(redis_metrics['status'], 'healthy')
        self.assertEqual(redis_metrics['version'], '7.0.0')
        self.assertEqual(redis_metrics['connected_clients'], 5)
        self.assertAlmostEqual(redis_metrics['memory_usage_percent'], 0.78, places=1)  # 1MB/128MB
    
    @patch('zargar.admin_panel.system_health.redis.from_url')
    def test_get_redis_metrics_error(self, mock_redis_from_url):
        """Test Redis metrics collection when Redis is unavailable."""
        # Mock Redis connection error
        mock_redis_from_url.side_effect = Exception("Connection refused")
        
        # Reinitialize monitor to use mocked Redis
        monitor = SystemHealthMonitor()
        
        metrics = monitor.get_redis_metrics()
        
        # Verify error handling
        self.assertIn('redis', metrics)
        self.assertEqual(metrics['redis']['status'], 'error')
        self.assertIn('error', metrics['redis'])
    
    @patch('zargar.admin_panel.system_health.celery_app.control.inspect')
    def test_get_celery_metrics(self, mock_inspect):
        """Test Celery metrics collection."""
        # Mock Celery inspect
        mock_inspect_obj = Mock()
        mock_inspect_obj.stats.return_value = {
            'worker1@hostname': {'total': 100, 'pool': {'max-concurrency': 4}},
            'worker2@hostname': {'total': 150, 'pool': {'max-concurrency': 4}},
        }
        mock_inspect_obj.active.return_value = {
            'worker1@hostname': [{'id': 'task1', 'name': 'test.task'}],
            'worker2@hostname': [],
        }
        mock_inspect_obj.scheduled.return_value = {
            'worker1@hostname': [],
            'worker2@hostname': [{'id': 'task2', 'name': 'scheduled.task'}],
        }
        mock_inspect_obj.reserved.return_value = {
            'worker1@hostname': [],
            'worker2@hostname': [],
        }
        mock_inspect.return_value = mock_inspect_obj
        
        metrics = self.monitor.get_celery_metrics()
        
        # Verify metrics structure
        self.assertIn('celery', metrics)
        celery_metrics = metrics['celery']
        
        self.assertEqual(celery_metrics['status'], 'healthy')
        self.assertEqual(celery_metrics['total_workers'], 2)
        self.assertEqual(celery_metrics['active_tasks']['total'], 1)
        self.assertEqual(celery_metrics['scheduled_tasks']['total'], 1)
    
    def test_get_application_metrics(self):
        """Test application-specific metrics collection."""
        from zargar.tenants.models import Tenant
        from zargar.tenants.admin_models import SuperAdmin
        
        # Create test data
        tenant = Tenant.objects.create(
            schema_name='test_metrics',
            name='Test Metrics Shop',
            domain_url='test-metrics.zargar.com'
        )
        
        admin = SuperAdmin.objects.create(
            username='test_admin',
            email='admin@test.com',
            is_superuser=True,
            is_active=True
        )
        
        metrics = self.monitor.get_application_metrics()
        
        # Verify metrics structure
        self.assertIn('application', metrics)
        app_metrics = metrics['application']
        
        self.assertIn('tenants', app_metrics)
        self.assertIn('admins', app_metrics)
        
        # Verify tenant metrics
        self.assertGreaterEqual(app_metrics['tenants']['total'], 1)
        self.assertGreaterEqual(app_metrics['tenants']['active'], 1)
        
        # Verify admin metrics
        self.assertGreaterEqual(app_metrics['admins']['total'], 1)
        self.assertGreaterEqual(app_metrics['admins']['active'], 1)
    
    def test_store_metrics(self):
        """Test metrics storage in database."""
        # Create test metrics
        test_metrics = {
            'cpu': {'usage_percent': 75.5},
            'memory': {'usage_percent': 80.2},
            'disk': {'usage_percent': 65.0},
            'database': {
                'default': {
                    'status': 'healthy',
                    'response_time_ms': 15.5
                }
            },
            'redis': {
                'status': 'healthy',
                'memory_usage_percent': 45.0
            },
            'celery': {
                'status': 'healthy',
                'total_workers': 3
            }
        }
        
        # Store metrics
        self.monitor._store_metrics(test_metrics)
        
        # Verify metrics were stored
        cpu_metric = SystemHealthMetric.objects.filter(metric_type='cpu_usage').first()
        self.assertIsNotNone(cpu_metric)
        self.assertEqual(cpu_metric.value, 75.5)
        self.assertEqual(cpu_metric.unit, '%')
        
        memory_metric = SystemHealthMetric.objects.filter(metric_type='memory_usage').first()
        self.assertIsNotNone(memory_metric)
        self.assertEqual(memory_metric.value, 80.2)
        
        response_time_metric = SystemHealthMetric.objects.filter(metric_type='response_time').first()
        self.assertIsNotNone(response_time_metric)
        self.assertEqual(response_time_metric.value, 15.5)
        self.assertEqual(response_time_metric.unit, 'ms')
    
    def test_check_alert_thresholds(self):
        """Test alert threshold checking."""
        # Create test metrics that should trigger alerts
        test_metrics = {
            'cpu': {'usage_percent': 95.0},  # Should trigger critical alert
            'memory': {'usage_percent': 85.0},  # Should trigger warning alert
            'disk': {'usage_percent': 70.0},  # Should not trigger alert
            'redis': {'memory_usage_percent': 92.0},  # Should trigger critical alert
            'database': {
                'default': {
                    'status': 'healthy',
                    'response_time_ms': 2000.0  # Should trigger warning alert
                }
            }
        }
        
        # Check thresholds
        self.monitor._check_alert_thresholds(test_metrics)
        
        # Verify alerts were created
        cpu_alert = SystemHealthAlert.objects.filter(category='cpu_usage').first()
        self.assertIsNotNone(cpu_alert)
        self.assertEqual(cpu_alert.severity, 'critical')
        self.assertEqual(cpu_alert.current_value, 95.0)
        
        memory_alert = SystemHealthAlert.objects.filter(category='memory_usage').first()
        self.assertIsNotNone(memory_alert)
        self.assertEqual(memory_alert.severity, 'warning')
        
        redis_alert = SystemHealthAlert.objects.filter(category='redis_memory').first()
        self.assertIsNotNone(redis_alert)
        self.assertEqual(redis_alert.severity, 'critical')
        
        # Should not create alert for disk usage (below threshold)
        disk_alert = SystemHealthAlert.objects.filter(category='disk_usage').first()
        self.assertIsNone(disk_alert)
    
    def test_get_historical_metrics(self):
        """Test historical metrics retrieval."""
        # Create test metrics with different timestamps
        now = timezone.now()
        
        for i in range(5):
            SystemHealthMetric.objects.create(
                metric_type='cpu_usage',
                value=50.0 + i * 10,
                unit='%',
                timestamp=now - timedelta(hours=i),
                hostname=self.monitor.hostname
            )
        
        # Get historical data
        historical_data = self.monitor.get_historical_metrics('cpu_usage', hours=6)
        
        # Verify data
        self.assertEqual(len(historical_data), 5)
        
        # Verify data structure
        for data_point in historical_data:
            self.assertIn('timestamp', data_point)
            self.assertIn('value', data_point)
            self.assertIn('unit', data_point)
            self.assertEqual(data_point['unit'], '%')
    
    def test_cleanup_old_metrics(self):
        """Test cleanup of old metrics."""
        # Create old and new metrics
        old_time = timezone.now() - timedelta(days=35)
        new_time = timezone.now() - timedelta(days=5)
        
        # Old metric (should be deleted)
        SystemHealthMetric.objects.create(
            metric_type='cpu_usage',
            value=50.0,
            unit='%',
            timestamp=old_time,
            hostname=self.monitor.hostname
        )
        
        # New metric (should be kept)
        SystemHealthMetric.objects.create(
            metric_type='cpu_usage',
            value=60.0,
            unit='%',
            timestamp=new_time,
            hostname=self.monitor.hostname
        )
        
        # Verify initial count
        self.assertEqual(SystemHealthMetric.objects.count(), 2)
        
        # Cleanup old metrics (keep 30 days)
        self.monitor.cleanup_old_metrics(days=30)
        
        # Verify old metric was deleted
        self.assertEqual(SystemHealthMetric.objects.count(), 1)
        remaining_metric = SystemHealthMetric.objects.first()
        self.assertEqual(remaining_metric.value, 60.0)


class SystemHealthAlertTest(TestCase):
    """Test SystemHealthAlert model functionality."""
    
    def setUp(self):
        """Set up test data."""
        SystemHealthAlert.objects.all().delete()
    
    def test_alert_creation(self):
        """Test alert creation and basic properties."""
        alert = SystemHealthAlert.objects.create(
            title='High CPU Usage',
            description='CPU usage is above 90%',
            severity='critical',
            category='cpu_usage',
            threshold_value=90.0,
            current_value=95.0
        )
        
        self.assertEqual(alert.title, 'High CPU Usage')
        self.assertEqual(alert.severity, 'critical')
        self.assertEqual(alert.status, 'active')  # Default status
        self.assertIsNotNone(alert.alert_id)
    
    def test_alert_acknowledge(self):
        """Test alert acknowledgment."""
        alert = SystemHealthAlert.objects.create(
            title='Test Alert',
            description='Test description',
            severity='warning',
            category='test'
        )
        
        # Acknowledge alert
        alert.acknowledge(user_id=1, username='admin', notes='Investigating issue')
        
        self.assertEqual(alert.status, 'acknowledged')
        self.assertIsNotNone(alert.acknowledged_at)
        self.assertEqual(alert.acknowledged_by_username, 'admin')
        self.assertEqual(alert.resolution_notes, 'Investigating issue')
    
    def test_alert_resolve(self):
        """Test alert resolution."""
        alert = SystemHealthAlert.objects.create(
            title='Test Alert',
            description='Test description',
            severity='error',
            category='test'
        )
        
        # Resolve alert
        alert.resolve(user_id=1, username='admin', notes='Issue fixed')
        
        self.assertEqual(alert.status, 'resolved')
        self.assertIsNotNone(alert.resolved_at)
        self.assertEqual(alert.acknowledged_by_username, 'admin')
        self.assertEqual(alert.resolution_notes, 'Issue fixed')
    
    def test_alert_add_notification(self):
        """Test adding notifications to alert."""
        alert = SystemHealthAlert.objects.create(
            title='Test Alert',
            description='Test description',
            severity='critical',
            category='test'
        )
        
        # Add notification
        alert.add_notification('email', 'admin@test.com', 'sent')
        
        self.assertEqual(len(alert.notifications_sent), 1)
        notification = alert.notifications_sent[0]
        self.assertEqual(notification['type'], 'email')
        self.assertEqual(notification['recipient'], 'admin@test.com')
        self.assertEqual(notification['status'], 'sent')


class SystemHealthTasksTest(TransactionTestCase):
    """Test system health monitoring Celery tasks."""
    
    def setUp(self):
        """Set up test data."""
        SystemHealthMetric.objects.all().delete()
        SystemHealthAlert.objects.all().delete()
    
    @patch('zargar.admin_panel.system_health.system_health_monitor.collect_all_metrics')
    def test_collect_system_health_metrics_task(self, mock_collect):
        """Test the collect system health metrics task."""
        # Mock successful metrics collection
        mock_collect.return_value = {
            'cpu': {'usage_percent': 50.0},
            'memory': {'usage_percent': 60.0},
            'disk': {'usage_percent': 70.0}
        }
        
        # Run task
        result = collect_system_health_metrics()
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['metrics_collected'], 3)
        self.assertIn('timestamp', result)
        
        # Verify mock was called
        mock_collect.assert_called_once()
    
    @patch('zargar.admin_panel.system_health.system_health_monitor.collect_all_metrics')
    def test_collect_system_health_metrics_task_error(self, mock_collect):
        """Test the collect system health metrics task with error."""
        # Mock error in metrics collection
        mock_collect.side_effect = Exception("Test error")
        
        # Run task
        result = collect_system_health_metrics()
        
        # Verify error handling
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'Test error')
    
    def test_cleanup_old_health_metrics_task(self):
        """Test the cleanup old health metrics task."""
        # Create old metric
        old_time = timezone.now() - timedelta(days=35)
        SystemHealthMetric.objects.create(
            metric_type='cpu_usage',
            value=50.0,
            unit='%',
            timestamp=old_time,
            hostname='test'
        )
        
        # Verify metric exists
        self.assertEqual(SystemHealthMetric.objects.count(), 1)
        
        # Run cleanup task
        result = cleanup_old_health_metrics()
        
        # Verify result
        self.assertTrue(result['success'])
        
        # Verify old metric was deleted
        self.assertEqual(SystemHealthMetric.objects.count(), 0)
    
    def test_check_system_health_alerts_task(self):
        """Test the check system health alerts task."""
        # Run task
        result = check_system_health_alerts()
        
        # Verify result structure
        self.assertTrue(result['success'])
        self.assertIn('active_alerts', result)
        self.assertIn('new_alerts', result)
        self.assertIn('timestamp', result)
    
    @patch('zargar.admin_panel.tasks.send_mail')
    def test_send_health_alert_notifications_task(self, mock_send_mail):
        """Test the send health alert notifications task."""
        # Create critical alert
        alert = SystemHealthAlert.objects.create(
            title='Critical System Alert',
            description='System is down',
            severity='critical',
            category='system',
            status='active'
        )
        
        # Mock settings
        with self.settings(
            ADMIN_NOTIFICATION_EMAILS=['admin@test.com'],
            DEFAULT_FROM_EMAIL='system@zargar.com'
        ):
            # Run task
            result = send_health_alert_notifications()
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertGreaterEqual(result['notifications_sent'], 0)
        self.assertGreaterEqual(result['critical_alerts_checked'], 1)
    
    def test_generate_health_report_task(self):
        """Test the generate health report task."""
        # Create test metrics
        now = timezone.now()
        SystemHealthMetric.objects.create(
            metric_type='cpu_usage',
            value=75.0,
            unit='%',
            timestamp=now - timedelta(hours=1),
            hostname='test'
        )
        
        # Create test alert
        SystemHealthAlert.objects.create(
            title='Test Alert',
            description='Test description',
            severity='warning',
            category='test',
            created_at=now - timedelta(hours=2)
        )
        
        # Run task
        result = generate_health_report(report_type='daily')
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['report_type'], 'daily')
        self.assertIn('report_content', result)
        
        # Verify report content
        report_content = result['report_content']
        self.assertIn('metrics_summary', report_content)
        self.assertIn('alert_summary', report_content)
        self.assertIn('cpu_usage', report_content['metrics_summary'])


class SystemHealthViewsTest(TestCase):
    """Test system health monitoring views."""
    
    def setUp(self):
        """Set up test data."""
        # Create superadmin user
        self.admin_user = SuperAdmin.objects.create(
            username='admin',
            email='admin@test.com',
            is_superuser=True,
            is_active=True
        )
        self.admin_user.set_password('testpass123')
        self.admin_user.save()
        
        # Clear existing data
        SystemHealthMetric.objects.all().delete()
        SystemHealthAlert.objects.all().delete()
    
    def test_system_health_dashboard_view(self):
        """Test system health dashboard view."""
        # Login as admin
        self.client.force_login(self.admin_user)
        
        # Create test data
        SystemHealthAlert.objects.create(
            title='Test Alert',
            description='Test description',
            severity='warning',
            category='test',
            status='active'
        )
        
        # Access dashboard
        url = reverse('admin_panel:system_health_dashboard')
        response = self.client.get(url)
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Alert')
        
        # Verify context data
        self.assertIn('current_metrics', response.context)
        self.assertIn('active_alerts', response.context)
        self.assertIn('alert_stats', response.context)
        self.assertIn('system_status', response.context)
    
    def test_system_health_metrics_api_view(self):
        """Test system health metrics API view."""
        # Login as admin
        self.client.force_login(self.admin_user)
        
        # Access API
        url = reverse('admin_panel:system_health_metrics_api')
        response = self.client.get(url)
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        # Parse JSON response
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('metrics', data)
        self.assertIn('timestamp', data)
    
    def test_system_health_historical_view(self):
        """Test system health historical metrics API view."""
        # Login as admin
        self.client.force_login(self.admin_user)
        
        # Create test metric
        SystemHealthMetric.objects.create(
            metric_type='cpu_usage',
            value=75.0,
            unit='%',
            hostname='test'
        )
        
        # Access API
        url = reverse('admin_panel:system_health_historical_api')
        response = self.client.get(url, {
            'metric_type': 'cpu_usage',
            'hours': 24
        })
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        # Parse JSON response
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['metric_type'], 'cpu_usage')
        self.assertEqual(data['hours'], 24)
        self.assertIn('data', data)
    
    def test_system_health_alerts_view(self):
        """Test system health alerts list view."""
        # Login as admin
        self.client.force_login(self.admin_user)
        
        # Create test alerts
        SystemHealthAlert.objects.create(
            title='Critical Alert',
            description='Critical issue',
            severity='critical',
            category='system',
            status='active'
        )
        
        SystemHealthAlert.objects.create(
            title='Warning Alert',
            description='Warning issue',
            severity='warning',
            category='database',
            status='acknowledged'
        )
        
        # Access alerts view
        url = reverse('admin_panel:system_health_alerts')
        response = self.client.get(url)
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Critical Alert')
        self.assertContains(response, 'Warning Alert')
        
        # Test filtering
        response = self.client.get(url, {'severity': 'critical'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Critical Alert')
        self.assertNotContains(response, 'Warning Alert')
    
    def test_alert_action_view(self):
        """Test alert action view (acknowledge/resolve)."""
        # Login as admin
        self.client.force_login(self.admin_user)
        
        # Create test alert
        alert = SystemHealthAlert.objects.create(
            title='Test Alert',
            description='Test description',
            severity='warning',
            category='test',
            status='active'
        )
        
        # Test acknowledge action
        url = reverse('admin_panel:alert_action')
        response = self.client.post(url, {
            'alert_id': str(alert.alert_id),
            'action': 'acknowledge',
            'notes': 'Investigating issue'
        })
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        # Parse JSON response
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['alert_status'], 'acknowledged')
        
        # Verify alert was updated
        alert.refresh_from_db()
        self.assertEqual(alert.status, 'acknowledged')
        self.assertEqual(alert.resolution_notes, 'Investigating issue')
    
    def test_system_health_reports_view(self):
        """Test system health reports view."""
        # Login as admin
        self.client.force_login(self.admin_user)
        
        # Create test data
        SystemHealthMetric.objects.create(
            metric_type='cpu_usage',
            value=75.0,
            unit='%',
            hostname='test'
        )
        
        SystemHealthAlert.objects.create(
            title='Test Alert',
            description='Test description',
            severity='warning',
            category='test'
        )
        
        # Access reports view
        url = reverse('admin_panel:system_health_reports')
        response = self.client.get(url, {'days': 7})
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        # Verify context data
        self.assertIn('metric_summaries', response.context)
        self.assertIn('alert_trends', response.context)
        self.assertIn('service_availability', response.context)
        self.assertEqual(response.context['days'], 7)
    
    def test_unauthorized_access(self):
        """Test that unauthorized users cannot access health monitoring views."""
        # Try to access dashboard without login
        url = reverse('admin_panel:system_health_dashboard')
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)


class SystemHealthIntegrationTest(TransactionTestCase):
    """Integration tests for system health monitoring."""
    
    def setUp(self):
        """Set up test data."""
        SystemHealthMetric.objects.all().delete()
        SystemHealthAlert.objects.all().delete()
    
    @patch('zargar.admin_panel.system_health.psutil.cpu_percent')
    @patch('zargar.admin_panel.system_health.psutil.virtual_memory')
    def test_end_to_end_monitoring_flow(self, mock_memory, mock_cpu):
        """Test complete monitoring flow from metrics collection to alerting."""
        # Mock high resource usage
        mock_cpu.return_value = 95.0  # Critical CPU usage
        
        mock_memory_obj = Mock()
        mock_memory_obj.percent = 88.0  # Warning memory usage
        mock_memory_obj.total = 8589934592
        mock_memory_obj.available = 1073741824
        mock_memory_obj.used = 7516192768
        mock_memory.return_value = mock_memory_obj
        
        # Collect metrics (this should trigger alerts)
        monitor = SystemHealthMonitor()
        metrics = monitor.collect_all_metrics()
        
        # Verify metrics were collected
        self.assertIn('cpu', metrics)
        self.assertIn('memory', metrics)
        self.assertEqual(metrics['cpu']['usage_percent'], 95.0)
        self.assertEqual(metrics['memory']['usage_percent'], 88.0)
        
        # Verify metrics were stored in database
        cpu_metric = SystemHealthMetric.objects.filter(metric_type='cpu_usage').first()
        self.assertIsNotNone(cpu_metric)
        self.assertEqual(cpu_metric.value, 95.0)
        
        memory_metric = SystemHealthMetric.objects.filter(metric_type='memory_usage').first()
        self.assertIsNotNone(memory_metric)
        self.assertEqual(memory_metric.value, 88.0)
        
        # Verify alerts were created
        cpu_alert = SystemHealthAlert.objects.filter(category='cpu_usage').first()
        self.assertIsNotNone(cpu_alert)
        self.assertEqual(cpu_alert.severity, 'critical')
        self.assertEqual(cpu_alert.status, 'active')
        
        memory_alert = SystemHealthAlert.objects.filter(category='memory_usage').first()
        self.assertIsNotNone(memory_alert)
        self.assertEqual(memory_alert.severity, 'warning')
        self.assertEqual(memory_alert.status, 'active')
        
        # Test alert resolution
        cpu_alert.resolve(user_id=1, username='admin', notes='Issue resolved')
        self.assertEqual(cpu_alert.status, 'resolved')
        self.assertIsNotNone(cpu_alert.resolved_at)
    
    def test_historical_data_and_cleanup(self):
        """Test historical data collection and cleanup."""
        # Create metrics over time
        base_time = timezone.now()
        
        for i in range(10):
            SystemHealthMetric.objects.create(
                metric_type='cpu_usage',
                value=50.0 + i * 5,
                unit='%',
                timestamp=base_time - timedelta(days=i * 5),
                hostname='test'
            )
        
        # Verify all metrics exist
        self.assertEqual(SystemHealthMetric.objects.count(), 10)
        
        # Get historical data
        monitor = SystemHealthMonitor()
        historical_data = monitor.get_historical_metrics('cpu_usage', hours=24*20)  # 20 days
        
        # Should get metrics from last 20 days (4 metrics)
        self.assertEqual(len(historical_data), 4)
        
        # Test cleanup (keep 30 days)
        monitor.cleanup_old_metrics(days=30)
        
        # Should keep 6 metrics (within 30 days)
        self.assertEqual(SystemHealthMetric.objects.count(), 6)
        
        # Test more aggressive cleanup (keep 10 days)
        monitor.cleanup_old_metrics(days=10)
        
        # Should keep 2 metrics (within 10 days)
        self.assertEqual(SystemHealthMetric.objects.count(), 2)


if __name__ == '__main__':
    pytest.main([__file__])