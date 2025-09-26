#!/usr/bin/env python
"""
Simple test for notification UI implementation.
"""
import os
import sys
import django
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from zargar.core.notification_models import (
    NotificationTemplate, 
    Notification, 
    NotificationProvider
)
from zargar.customers.models import Customer


class NotificationUITest(TestCase):
    """Test notification UI components."""
    
    def setUp(self):
        """Set up test data."""
        User = get_user_model()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            first_name='Test',
            last_name='Customer',
            persian_first_name='تست',
            persian_last_name='مشتری',
            phone_number='09123456789',
            email='test@customer.com'
        )
        
        # Create notification template
        self.template = NotificationTemplate.objects.create(
            name='Test Payment Reminder',
            template_type='payment_reminder',
            title='یادآوری پرداخت',
            content='سلام {customer_name}، پرداخت شما سررسید شده است.',
            delivery_methods=['sms', 'email'],
            is_active=True,
            is_default=True
        )
        
        # Create notification provider
        self.provider = NotificationProvider.objects.create(
            name='Test SMS Provider',
            provider_type='sms',
            api_endpoint='https://api.test.com/sms',
            api_key='test_key',
            is_active=True,
            is_default=True
        )
        
        # Create test notification
        self.notification = Notification.objects.create(
            template=self.template,
            recipient_type='customer',
            recipient_id=self.customer.id,
            recipient_name=self.customer.full_persian_name,
            recipient_phone=self.customer.phone_number,
            title='یادآوری پرداخت',
            content='سلام تست مشتری، پرداخت شما سررسید شده است.',
            delivery_method='sms',
            status='pending'
        )
        
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_notification_models_creation(self):
        """Test that notification models can be created."""
        self.assertEqual(NotificationTemplate.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(NotificationProvider.objects.count(), 1)
        
        template = NotificationTemplate.objects.first()
        self.assertEqual(template.name, 'Test Payment Reminder')
        self.assertEqual(template.template_type, 'payment_reminder')
        self.assertTrue(template.is_active)
        self.assertIn('sms', template.delivery_methods)
        
        notification = Notification.objects.first()
        self.assertEqual(notification.recipient_type, 'customer')
        self.assertEqual(notification.status, 'pending')
        self.assertEqual(notification.delivery_method, 'sms')
    
    def test_template_content_rendering(self):
        """Test template content rendering with context."""
        context = {
            'customer_name': 'احمد رضایی',
            'amount': '1,000,000',
            'due_date': '1403/07/15'
        }
        
        rendered = self.template.render_content(context)
        
        self.assertIn('احمد رضایی', rendered['content'])
        self.assertEqual(rendered['title'], 'یادآوری پرداخت')
    
    def test_notification_dashboard_templates_exist(self):
        """Test that notification dashboard templates exist."""
        import os
        from django.conf import settings
        
        template_dir = os.path.join(settings.BASE_DIR, 'templates', 'core', 'notifications')
        
        # Check main templates
        self.assertTrue(os.path.exists(os.path.join(template_dir, 'dashboard.html')))
        self.assertTrue(os.path.exists(os.path.join(template_dir, 'history.html')))
        self.assertTrue(os.path.exists(os.path.join(template_dir, 'detail.html')))
        self.assertTrue(os.path.exists(os.path.join(template_dir, 'template_list.html')))
        self.assertTrue(os.path.exists(os.path.join(template_dir, 'template_form.html')))
        self.assertTrue(os.path.exists(os.path.join(template_dir, 'template_confirm_delete.html')))
        
        # Check modal templates
        modal_dir = os.path.join(template_dir, 'modals')
        self.assertTrue(os.path.exists(os.path.join(modal_dir, 'single_notification.html')))
        self.assertTrue(os.path.exists(os.path.join(modal_dir, 'bulk_notification.html')))
        self.assertTrue(os.path.exists(os.path.join(modal_dir, 'schedule_notification.html')))
        self.assertTrue(os.path.exists(os.path.join(modal_dir, 'template_preview.html')))
    
    def test_notification_static_files_exist(self):
        """Test that notification static files exist."""
        import os
        from django.conf import settings
        
        static_dir = os.path.join(settings.BASE_DIR, 'static')
        
        # Check JavaScript file
        js_file = os.path.join(static_dir, 'js', 'notifications.js')
        self.assertTrue(os.path.exists(js_file))
        
        # Check CSS file
        css_file = os.path.join(static_dir, 'css', 'notifications.css')
        self.assertTrue(os.path.exists(css_file))
    
    def test_notification_views_exist(self):
        """Test that notification views are properly defined."""
        from zargar.core import notification_views
        
        # Check view classes exist
        self.assertTrue(hasattr(notification_views, 'NotificationDashboardView'))
        self.assertTrue(hasattr(notification_views, 'NotificationTemplateListView'))
        self.assertTrue(hasattr(notification_views, 'NotificationTemplateCreateView'))
        self.assertTrue(hasattr(notification_views, 'NotificationTemplateUpdateView'))
        self.assertTrue(hasattr(notification_views, 'NotificationTemplateDeleteView'))
        
        # Check function views exist
        self.assertTrue(hasattr(notification_views, 'notification_history_view'))
        self.assertTrue(hasattr(notification_views, 'notification_detail_view'))
        self.assertTrue(hasattr(notification_views, 'send_notification_ajax'))
        self.assertTrue(hasattr(notification_views, 'send_bulk_notifications_ajax'))
        self.assertTrue(hasattr(notification_views, 'template_preview_ajax'))
    
    def test_notification_urls_exist(self):
        """Test that notification URLs are properly configured."""
        from zargar.core import notification_urls
        
        # Check URL patterns exist
        self.assertTrue(hasattr(notification_urls, 'urlpatterns'))
        self.assertTrue(len(notification_urls.urlpatterns) > 0)
        
        # Check app name
        self.assertEqual(notification_urls.app_name, 'notifications')
    
    def test_notification_services_exist(self):
        """Test that notification services are properly implemented."""
        from zargar.core.notification_services import PushNotificationSystem, NotificationScheduler
        
        # Test PushNotificationSystem
        system = PushNotificationSystem()
        self.assertTrue(hasattr(system, 'create_notification'))
        self.assertTrue(hasattr(system, 'send_notification'))
        self.assertTrue(hasattr(system, 'send_bulk_notifications'))
        
        # Test NotificationScheduler
        scheduler = NotificationScheduler()
        self.assertTrue(hasattr(scheduler, 'process_scheduled_notifications'))
        self.assertTrue(hasattr(scheduler, 'process_recurring_schedules'))
    
    def test_notification_system_integration(self):
        """Test basic notification system integration."""
        from zargar.core.notification_services import PushNotificationSystem
        
        system = PushNotificationSystem()
        
        # Test notification creation
        notifications = system.create_notification(
            template_type='payment_reminder',
            recipient_type='customer',
            recipient_id=self.customer.id,
            context={
                'customer_name': self.customer.full_persian_name,
                'amount': '1,000,000',
                'due_date': '1403/07/15'
            },
            delivery_methods=['sms']
        )
        
        self.assertEqual(len(notifications), 1)
        notification = notifications[0]
        
        self.assertEqual(notification.recipient_type, 'customer')
        self.assertEqual(notification.recipient_id, self.customer.id)
        self.assertEqual(notification.delivery_method, 'sms')
        self.assertEqual(notification.status, 'pending')
        self.assertIn('تست مشتری', notification.content)


def run_tests():
    """Run the notification UI tests."""
    import unittest
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(NotificationUITest)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print results
    if result.wasSuccessful():
        print("\n✅ All notification UI tests passed!")
        print(f"Ran {result.testsRun} tests successfully")
    else:
        print(f"\n❌ {len(result.failures)} test(s) failed")
        print(f"❌ {len(result.errors)} test(s) had errors")
        
        for test, error in result.failures + result.errors:
            print(f"\nFailed: {test}")
            print(error)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)