"""
Tests for push notification system.
"""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from zargar.tenants.models import Tenant, Domain
from zargar.core.models import User
from zargar.customers.models import Customer
from zargar.core.notification_models import (
    NotificationTemplate,
    NotificationSchedule,
    Notification,
    NotificationDeliveryLog,
    NotificationProvider
)
from zargar.core.notification_services import PushNotificationSystem, NotificationScheduler
from zargar.core.notification_tasks import (
    process_scheduled_notifications,
    send_single_notification,
    send_daily_payment_reminders
)


class NotificationSystemTestCase(TenantTestCase):
    """Test case for notification system with tenant isolation."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Switch to public schema to create tenant
        from django_tenants.utils import schema_context
        from django.db import connection
        
        with schema_context('public'):
            # Create tenant
            cls.tenant = Tenant.objects.create(
                name='Test Notification Shop',
                schema_name='test_notification',
                owner_name='Test Owner',
                owner_email='owner@test-notification.com'
            )
            
            # Create domain
            cls.domain = Domain.objects.create(
                domain='test-notification.localhost',
                tenant=cls.tenant,
                is_primary=True
            )
    
    def setUp(self):
        super().setUp()
        
        # Set up tenant client
        self.client = TenantClient(self.tenant)
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner',
            persian_first_name='علی',
            persian_last_name='محمدی'
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            first_name='Ahmad',
            last_name='Rezaei',
            persian_first_name='احمد',
            persian_last_name='رضایی',
            phone_number='09123456789',
            email='ahmad@example.com'
        )
        
        # Create notification provider
        self.sms_provider = NotificationProvider.objects.create(
            name='Test SMS Provider',
            provider_type='sms',
            api_endpoint='https://api.test-sms.com/send',
            api_key='test_key',
            api_secret='test_secret',
            is_active=True,
            is_default=True
        )
        
        # Create notification template
        self.template = NotificationTemplate.objects.create(
            name='Payment Reminder Template',
            template_type='payment_reminder',
            title='یادآوری پرداخت',
            content='سلام {customer_name}، پرداخت قرارداد {contract_number} به مبلغ {amount} تومان در تاریخ {due_date} سررسید می‌شود.',
            delivery_methods=['sms', 'email'],
            is_active=True,
            is_default=True
        )
    
    def test_notification_template_creation(self):
        """Test creating notification templates."""
        template = NotificationTemplate.objects.create(
            name='Test Template',
            template_type='birthday_greeting',
            title='تولدت مبارک',
            content='سلام {customer_name}، تولدت مبارک! امیدواریم سالی پر از شادی داشته باشی.',
            delivery_methods=['sms'],
            is_active=True
        )
        
        self.assertEqual(template.name, 'Test Template')
        self.assertEqual(template.template_type, 'birthday_greeting')
        self.assertIn('sms', template.delivery_methods)
        self.assertTrue(template.is_active)
    
    def test_template_content_rendering(self):
        """Test template content rendering with context variables."""
        context = {
            'customer_name': 'احمد رضایی',
            'contract_number': 'GI-2024-001',
            'amount': '5,000,000',
            'due_date': '1403/07/15'
        }
        
        rendered = self.template.render_content(context)
        
        self.assertIn('احمد رضایی', rendered['content'])
        self.assertIn('GI-2024-001', rendered['content'])
        self.assertIn('5,000,000', rendered['content'])
        self.assertIn('1403/07/15', rendered['content'])
    
    def test_notification_creation(self):
        """Test creating notifications through PushNotificationSystem."""
        system = PushNotificationSystem()
        
        context = {
            'customer_name': self.customer.full_persian_name,
            'contract_number': 'GI-2024-001',
            'amount': '2,500,000',
            'due_date': '1403/07/20'
        }
        
        notifications = system.create_notification(
            template_type='payment_reminder',
            recipient_type='customer',
            recipient_id=self.customer.id,
            context=context,
            delivery_methods=['sms']
        )
        
        self.assertEqual(len(notifications), 1)
        notification = notifications[0]
        
        self.assertEqual(notification.recipient_type, 'customer')
        self.assertEqual(notification.recipient_id, self.customer.id)
        self.assertEqual(notification.recipient_name, self.customer.full_persian_name)
        self.assertEqual(notification.delivery_method, 'sms')
        self.assertEqual(notification.status, 'pending')
        self.assertIn('احمد رضایی', notification.content)
    
    @patch('requests.post')
    def test_sms_notification_sending(self, mock_post):
        """Test sending SMS notifications."""
        # Mock successful SMS API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message_id': 'test_msg_123', 'status': 'sent'}
        mock_response.content = b'{"message_id": "test_msg_123", "status": "sent"}'
        mock_post.return_value = mock_response
        
        # Create notification
        notification = Notification.objects.create(
            template=self.template,
            recipient_type='customer',
            recipient_id=self.customer.id,
            recipient_name=self.customer.full_persian_name,
            recipient_phone=self.customer.phone_number,
            title='یادآوری پرداخت',
            content='سلام احمد رضایی، پرداخت قرارداد GI-2024-001 سررسید شده است.',
            delivery_method='sms',
            scheduled_at=timezone.now()
        )
        
        # Send notification
        system = PushNotificationSystem()
        success = system.send_notification(notification)
        
        self.assertTrue(success)
        
        # Refresh notification from database
        notification.refresh_from_db()
        self.assertEqual(notification.status, 'sent')
        self.assertEqual(notification.provider_message_id, 'test_msg_123')
        
        # Check API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], self.sms_provider.api_endpoint)
        
        # Check delivery log
        logs = notification.delivery_logs.all()
        self.assertTrue(logs.exists())
        self.assertEqual(logs.first().action, 'sent')
    
    @patch('requests.post')
    def test_sms_notification_failure(self, mock_post):
        """Test handling SMS notification failures."""
        # Mock failed SMS API response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Invalid phone number'
        mock_response.content = b'Invalid phone number'
        mock_post.return_value = mock_response
        
        # Create notification
        notification = Notification.objects.create(
            template=self.template,
            recipient_type='customer',
            recipient_id=self.customer.id,
            recipient_name=self.customer.full_persian_name,
            recipient_phone='invalid_phone',
            title='یادآوری پرداخت',
            content='Test message',
            delivery_method='sms',
            scheduled_at=timezone.now()
        )
        
        # Send notification
        system = PushNotificationSystem()
        success = system.send_notification(notification)
        
        self.assertFalse(success)
        
        # Refresh notification from database
        notification.refresh_from_db()
        self.assertEqual(notification.status, 'failed')
        self.assertIn('Invalid phone number', notification.error_message)
    
    def test_bulk_notification_creation(self):
        """Test creating bulk notifications."""
        # Create additional customers
        customer2 = Customer.objects.create(
            first_name='Maryam',
            last_name='Hosseini',
            persian_first_name='مریم',
            persian_last_name='حسینی',
            phone_number='09987654321',
            email='maryam@example.com'
        )
        
        recipients = [
            {
                'type': 'customer',
                'id': self.customer.id,
                'context': {'customer_name': self.customer.full_persian_name}
            },
            {
                'type': 'customer',
                'id': customer2.id,
                'context': {'customer_name': customer2.full_persian_name}
            }
        ]
        
        system = PushNotificationSystem()
        stats = system.send_bulk_notifications(
            template_type='special_offer',
            recipients=recipients,
            context_template={
                'offer_title': 'تخفیف ویژه',
                'offer_description': 'تخفیف ۲۰٪ برای تمام محصولات',
                'expiry_date': '1403/08/01'
            },
            delivery_methods=['sms']
        )
        
        self.assertEqual(stats['created'], 2)
        
        # Check notifications were created
        notifications = Notification.objects.filter(
            recipient_type='customer',
            recipient_id__in=[self.customer.id, customer2.id]
        )
        self.assertEqual(notifications.count(), 2)
    
    def test_notification_scheduling(self):
        """Test scheduling notifications for future delivery."""
        future_time = timezone.now() + timedelta(hours=2)
        
        system = PushNotificationSystem()
        notifications = system.create_notification(
            template_type='payment_reminder',
            recipient_type='customer',
            recipient_id=self.customer.id,
            context={'customer_name': self.customer.full_persian_name},
            delivery_methods=['sms'],
            scheduled_at=future_time
        )
        
        notification = notifications[0]
        self.assertEqual(notification.scheduled_at, future_time)
        self.assertFalse(notification.is_ready_to_send)
        
        # Test that notification becomes ready when time arrives
        notification.scheduled_at = timezone.now() - timedelta(minutes=1)
        notification.save()
        self.assertTrue(notification.is_ready_to_send)
    
    def test_notification_expiry(self):
        """Test notification expiry functionality."""
        past_time = timezone.now() - timedelta(hours=1)
        
        notification = Notification.objects.create(
            template=self.template,
            recipient_type='customer',
            recipient_id=self.customer.id,
            recipient_name=self.customer.full_persian_name,
            recipient_phone=self.customer.phone_number,
            title='Test',
            content='Test message',
            delivery_method='sms',
            expires_at=past_time
        )
        
        self.assertTrue(notification.is_expired)
        self.assertFalse(notification.is_ready_to_send)
    
    def test_notification_retry_logic(self):
        """Test notification retry functionality."""
        notification = Notification.objects.create(
            template=self.template,
            recipient_type='customer',
            recipient_id=self.customer.id,
            recipient_name=self.customer.full_persian_name,
            recipient_phone=self.customer.phone_number,
            title='Test',
            content='Test message',
            delivery_method='sms',
            status='failed',
            retry_count=1,
            max_retries=3
        )
        
        self.assertTrue(notification.can_retry)
        
        # Test retry limit
        notification.retry_count = 3
        notification.save()
        self.assertFalse(notification.can_retry)
    
    def test_notification_provider_statistics(self):
        """Test notification provider statistics tracking."""
        initial_sent = self.sms_provider.total_sent
        initial_delivered = self.sms_provider.total_delivered
        initial_failed = self.sms_provider.total_failed
        
        # Update statistics
        self.sms_provider.update_statistics(sent=5, delivered=4, failed=1)
        
        self.assertEqual(self.sms_provider.total_sent, initial_sent + 5)
        self.assertEqual(self.sms_provider.total_delivered, initial_delivered + 4)
        self.assertEqual(self.sms_provider.total_failed, initial_failed + 1)
        
        # Test success rate calculation
        expected_rate = ((initial_delivered + 4) / (initial_sent + 5)) * 100
        self.assertEqual(self.sms_provider.success_rate, expected_rate)
    
    def test_scheduled_notification_processing(self):
        """Test processing of scheduled notifications."""
        # Create scheduled notifications
        past_time = timezone.now() - timedelta(minutes=5)
        future_time = timezone.now() + timedelta(hours=1)
        
        # Ready to send
        ready_notification = Notification.objects.create(
            template=self.template,
            recipient_type='customer',
            recipient_id=self.customer.id,
            recipient_name=self.customer.full_persian_name,
            recipient_phone=self.customer.phone_number,
            title='Ready',
            content='Ready message',
            delivery_method='sms',
            scheduled_at=past_time,
            status='pending'
        )
        
        # Not ready yet
        future_notification = Notification.objects.create(
            template=self.template,
            recipient_type='customer',
            recipient_id=self.customer.id,
            recipient_name=self.customer.full_persian_name,
            recipient_phone=self.customer.phone_number,
            title='Future',
            content='Future message',
            delivery_method='sms',
            scheduled_at=future_time,
            status='pending'
        )
        
        scheduler = NotificationScheduler()
        
        with patch.object(scheduler.notification_system, 'send_notification', return_value=True):
            stats = scheduler.process_scheduled_notifications()
        
        self.assertEqual(stats['processed'], 1)  # Only ready notification processed
        self.assertEqual(stats['sent'], 1)
    
    def test_notification_template_default_handling(self):
        """Test default template handling."""
        # Create another template of same type
        template2 = NotificationTemplate.objects.create(
            name='Alternative Payment Reminder',
            template_type='payment_reminder',
            title='یادآوری پرداخت جایگزین',
            content='پیام جایگزین',
            delivery_methods=['sms'],
            is_active=True,
            is_default=True  # This should make the original template non-default
        )
        
        # Refresh original template
        self.template.refresh_from_db()
        self.assertFalse(self.template.is_default)
        self.assertTrue(template2.is_default)
        
        # Test getting default template
        default_template = NotificationTemplate.get_default_template('payment_reminder')
        self.assertEqual(default_template, template2)


class NotificationViewsTestCase(TenantTestCase):
    """Test notification management views."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Switch to public schema to create tenant
        from django_tenants.utils import schema_context
        
        with schema_context('public'):
            # Create tenant
            cls.tenant = Tenant.objects.create(
                name='Test Views Shop',
                schema_name='test_views',
                owner_name='Test Owner',
                owner_email='owner@test-views.com'
            )
            
            # Create domain
            cls.domain = Domain.objects.create(
                domain='test-views.localhost',
                tenant=cls.tenant,
                is_primary=True
            )
    
    def setUp(self):
        super().setUp()
        
        # Set up tenant client
        self.client = TenantClient(self.tenant)
        
        # Create and login user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create test customer
        self.customer = Customer.objects.create(
            first_name='Test',
            last_name='Customer',
            persian_first_name='تست',
            persian_last_name='مشتری',
            phone_number='09123456789'
        )
        
        # Create test template
        self.template = NotificationTemplate.objects.create(
            name='Test Template',
            template_type='payment_reminder',
            title='Test Title',
            content='Test content with {customer_name}',
            delivery_methods=['sms'],
            is_active=True
        )
    
    def test_notification_dashboard_view(self):
        """Test notification dashboard view."""
        url = reverse('core:notifications:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'notification_stats')
        self.assertContains(response, 'notification_templates')
    
    def test_template_list_view(self):
        """Test template list view."""
        url = reverse('core:notifications:template_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.template.name)
    
    def test_template_create_view(self):
        """Test template creation view."""
        url = reverse('core:notifications:template_create')
        
        # GET request
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # POST request
        data = {
            'name': 'New Template',
            'template_type': 'birthday_greeting',
            'title': 'Happy Birthday',
            'content': 'Happy birthday {customer_name}!',
            'delivery_methods': ['sms'],
            'is_active': True
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Check template was created
        self.assertTrue(
            NotificationTemplate.objects.filter(name='New Template').exists()
        )
    
    def test_send_notification_ajax(self):
        """Test sending notification via AJAX."""
        url = reverse('core:notifications:send_ajax')
        
        data = {
            'template_type': 'payment_reminder',
            'recipient_type': 'customer',
            'recipient_id': self.customer.id,
            'context': {
                'customer_name': self.customer.full_persian_name,
                'amount': '1,000,000'
            },
            'delivery_methods': ['sms']
        }
        
        response = self.client.post(
            url,
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertGreater(response_data['notifications_created'], 0)
    
    def test_template_preview_ajax(self):
        """Test template preview via AJAX."""
        url = reverse('core:notifications:template_preview_ajax', args=[self.template.id])
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('احمد محمدی', response_data['content'])  # Sample customer name
    
    def test_notification_statistics_ajax(self):
        """Test notification statistics via AJAX."""
        url = reverse('core:notifications:statistics_ajax')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('stats', response_data)
        self.assertIn('total_notifications', response_data['stats'])


class NotificationTasksTestCase(TenantTestCase):
    """Test notification Celery tasks."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Switch to public schema to create tenant
        from django_tenants.utils import schema_context
        
        with schema_context('public'):
            # Create tenant
            cls.tenant = Tenant.objects.create(
                name='Test Tasks Shop',
                schema_name='test_tasks',
                owner_name='Test Owner',
                owner_email='owner@test-tasks.com'
            )
            
            # Create domain
            cls.domain = Domain.objects.create(
                domain='test-tasks.localhost',
                tenant=cls.tenant,
                is_primary=True
            )
    
    def setUp(self):
        super().setUp()
        
        # Create test customer
        self.customer = Customer.objects.create(
            first_name='Task',
            last_name='Customer',
            persian_first_name='تسک',
            persian_last_name='مشتری',
            phone_number='09123456789'
        )
        
        # Create notification template
        self.template = NotificationTemplate.objects.create(
            name='Task Template',
            template_type='payment_reminder',
            title='Task Title',
            content='Task content',
            delivery_methods=['sms'],
            is_active=True,
            is_default=True
        )
        
        # Create notification provider
        self.provider = NotificationProvider.objects.create(
            name='Task Provider',
            provider_type='sms',
            is_active=True,
            is_default=True
        )
    
    def test_process_scheduled_notifications_task(self):
        """Test scheduled notifications processing task."""
        # Create scheduled notification
        notification = Notification.objects.create(
            template=self.template,
            recipient_type='customer',
            recipient_id=self.customer.id,
            recipient_name=self.customer.full_persian_name,
            recipient_phone=self.customer.phone_number,
            title='Test',
            content='Test message',
            delivery_method='sms',
            scheduled_at=timezone.now() - timedelta(minutes=1),
            status='pending'
        )
        
        # Mock the notification sending
        with patch('zargar.core.notification_services.PushNotificationSystem.send_notification', return_value=True):
            result = process_scheduled_notifications.apply()
        
        self.assertTrue(result.successful())
        result_data = result.result
        self.assertTrue(result_data['success'])
        self.assertEqual(result_data['stats']['processed'], 1)
    
    def test_send_single_notification_task(self):
        """Test single notification sending task."""
        # Create notification
        notification = Notification.objects.create(
            template=self.template,
            recipient_type='customer',
            recipient_id=self.customer.id,
            recipient_name=self.customer.full_persian_name,
            recipient_phone=self.customer.phone_number,
            title='Test',
            content='Test message',
            delivery_method='sms',
            status='pending'
        )
        
        # Mock the notification sending
        with patch('zargar.core.notification_services.PushNotificationSystem.send_notification', return_value=True):
            result = send_single_notification.apply(args=[notification.id])
        
        self.assertTrue(result.successful())
        result_data = result.result
        self.assertTrue(result_data['success'])
        self.assertEqual(result_data['notification_id'], notification.id)


if __name__ == '__main__':
    pytest.main([__file__])