"""
Integration tests for mobile API functionality in ZARGAR jewelry SaaS platform.
Tests mobile-specific endpoints, offline synchronization, and push notifications.
"""
import pytest
import json
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from zargar.tenants.models import Tenant, Domain
from zargar.core.models import User
from zargar.jewelry.models import JewelryItem, Category
from zargar.customers.models import Customer
from zargar.pos.models import POSTransaction, POSTransactionLineItem
from zargar.core.notification_models import (
    MobileDevice, Notification, NotificationTemplate, NotificationProvider
)

User = get_user_model()


class MobileAPITestCase(APITestCase):
    """Base test case for mobile API tests with tenant setup."""
    
    def setUp(self):
        """Set up test tenant, user, and authentication."""
        # Create tenant
        self.tenant = Tenant.objects.create(
            name='Test Jewelry Shop',
            schema_name='test_shop',
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
        
        # Create domain
        self.domain = Domain.objects.create(
            domain='testshop.zargar.com',
            tenant=self.tenant,
            is_primary=True
        )
        
        # Set tenant schema
        from django_tenants.utils import schema_context
        
        # Store schema context for use in tests
        self.schema_context = schema_context
        with schema_context(self.tenant.schema_name):
            # Create user
            self.user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123',
                role='owner',
                phone_number='09123456789'
            )
            
            # Create API token
            self.token = Token.objects.create(user=self.user)
            
            # Create test data
            self.category = Category.objects.create(
                name='Test Category',
                name_persian='دسته تست'
            )
            
            self.jewelry_item = JewelryItem.objects.create(
                name='Test Ring',
                sku='TEST-001',
                barcode='TEST001',
                category=self.category,
                weight_grams=Decimal('5.500'),
                karat=18,
                manufacturing_cost=Decimal('500000'),
                selling_price=Decimal('2000000'),
                quantity=10,
                minimum_stock=2,
                created_by=self.user
            )
            
            self.customer = Customer.objects.create(
                first_name='John',
                last_name='Doe',
                persian_first_name='جان',
                persian_last_name='دو',
                phone_number='09123456789',
                email='customer@example.com',
                created_by=self.user
            )
        
        # Set up API client with authentication
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        # Set tenant header
        self.client.defaults['HTTP_HOST'] = 'testshop.zargar.com'


class MobilePOSAPITests(MobileAPITestCase):
    """Tests for mobile POS API endpoints."""
    
    def test_mobile_dashboard(self):
        """Test mobile dashboard endpoint."""
        url = reverse('mobile-pos-mobile-dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        dashboard = response.data['dashboard']
        self.assertIn('today_sales', dashboard)
        self.assertIn('recent_transactions', dashboard)
        self.assertIn('pending_sync_count', dashboard)
        self.assertIn('low_stock_items', dashboard)
    
    def test_offline_transaction_creation(self):
        """Test creating offline POS transactions."""
        url = reverse('mobile-pos-offline-create')
        
        transaction_data = {
            'customer': self.customer.id,
            'transaction_type': 'sale',
            'payment_method': 'cash',
            'subtotal': '2000000.00',
            'tax_amount': '180000.00',
            'total_amount': '2180000.00',
            'amount_paid': '2200000.00',
            'gold_price_18k_at_transaction': '2500000.00',
            'line_items': [
                {
                    'jewelry_item_id': self.jewelry_item.id,
                    'item_name': 'Test Ring',
                    'item_sku': 'TEST-001',
                    'quantity': 1,
                    'unit_price': '2000000.00',
                    'gold_weight_grams': '5.500',
                    'gold_karat': 18
                }
            ],
            'offline_transaction_id': str(uuid.uuid4()),
            'device_id': 'test-device-001',
            'offline_created_at': timezone.now().isoformat()
        }
        
        response = self.client.post(url, transaction_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('transaction_id', response.data)
        self.assertIn('offline_data', response.data)
        
        # Verify transaction was created
        transaction_id = response.data['transaction_id']
        with schema_context(self.tenant.schema_name):
            transaction = POSTransaction.objects.get(transaction_id=transaction_id)
            self.assertTrue(transaction.is_offline_transaction)
            self.assertEqual(transaction.sync_status, 'pending_sync')
    
    def test_bulk_sync_transactions(self):
        """Test bulk synchronization of offline transactions."""
        # First create some offline transactions
        with schema_context(self.tenant.schema_name):
            offline_transaction = POSTransaction.objects.create(
                customer=self.customer,
                transaction_type='sale',
                payment_method='cash',
                subtotal=Decimal('2000000.00'),
                total_amount=Decimal('2000000.00'),
                amount_paid=Decimal('2000000.00'),
                is_offline_transaction=True,
                sync_status='pending_sync',
                created_by=self.user
            )
            
            POSTransactionLineItem.objects.create(
                transaction=offline_transaction,
                jewelry_item=self.jewelry_item,
                item_name='Test Ring',
                quantity=1,
                unit_price=Decimal('2000000.00')
            )
        
        url = reverse('mobile-pos-bulk-sync')
        
        sync_data = {
            'transactions': [
                {
                    'transaction_id': str(offline_transaction.transaction_id),
                    'customer': self.customer.id,
                    'transaction_type': 'sale',
                    'payment_method': 'cash',
                    'subtotal': '2000000.00',
                    'total_amount': '2000000.00',
                    'amount_paid': '2000000.00',
                    'line_items': [
                        {
                            'jewelry_item_id': self.jewelry_item.id,
                            'item_name': 'Test Ring',
                            'quantity': 1,
                            'unit_price': '2000000.00'
                        }
                    ]
                }
            ]
        }
        
        response = self.client.post(url, sync_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        sync_results = response.data['sync_results']
        self.assertEqual(sync_results['total'], 1)
        self.assertEqual(sync_results['synced'], 1)
        self.assertEqual(sync_results['failed'], 0)
    
    def test_pending_sync_transactions(self):
        """Test getting pending sync transactions."""
        # Create a pending sync transaction
        with schema_context(self.tenant.schema_name):
            POSTransaction.objects.create(
                customer=self.customer,
                transaction_type='sale',
                payment_method='cash',
                subtotal=Decimal('1000000.00'),
                total_amount=Decimal('1000000.00'),
                is_offline_transaction=True,
                sync_status='pending_sync',
                created_by=self.user
            )
        
        url = reverse('mobile-pos-pending-sync')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['transactions']), 1)


class MobileInventoryAPITests(MobileAPITestCase):
    """Tests for mobile inventory API endpoints."""
    
    def test_barcode_search(self):
        """Test barcode search functionality."""
        url = reverse('mobile-inventory-barcode-search')
        response = self.client.get(url, {'barcode': 'TEST001'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        item = response.data['item']
        self.assertEqual(item['name'], 'Test Ring')
        self.assertEqual(item['sku'], 'TEST-001')
        self.assertEqual(item['barcode'], 'TEST001')
    
    def test_barcode_search_not_found(self):
        """Test barcode search with non-existent barcode."""
        url = reverse('mobile-inventory-barcode-search')
        response = self.client.get(url, {'barcode': 'NONEXISTENT'})
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['success'])
    
    def test_quick_search(self):
        """Test quick search functionality."""
        url = reverse('mobile-inventory-quick-search')
        response = self.client.get(url, {'q': 'Test'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['items']), 1)
    
    def test_bulk_update_stock(self):
        """Test bulk stock level updates."""
        url = reverse('mobile-inventory-bulk-update-stock')
        
        update_data = {
            'updates': [
                {
                    'item_id': self.jewelry_item.id,
                    'quantity': 15,
                    'reason': 'Mobile inventory adjustment',
                    'adjustment_type': 'set'
                }
            ]
        }
        
        response = self.client.post(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        update_results = response.data['update_results']
        self.assertEqual(update_results['total'], 1)
        self.assertEqual(update_results['updated'], 1)
        self.assertEqual(update_results['failed'], 0)
        
        # Verify stock was updated
        with schema_context(self.tenant.schema_name):
            self.jewelry_item.refresh_from_db()
            self.assertEqual(self.jewelry_item.quantity, 15)


class MobileCustomerAPITests(MobileAPITestCase):
    """Tests for mobile customer API endpoints."""
    
    def test_phone_search(self):
        """Test customer phone search."""
        url = reverse('mobile-customers-phone-search')
        response = self.client.get(url, {'phone': '09123456789'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['customers']), 1)
    
    def test_quick_create_customer(self):
        """Test quick customer creation."""
        url = reverse('mobile-customers-quick-create')
        
        customer_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'persian_first_name': 'جین',
            'persian_last_name': 'اسمیت',
            'phone_number': '09987654321',
            'email': 'jane@example.com'
        }
        
        response = self.client.post(url, customer_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        customer = response.data['customer']
        self.assertEqual(customer['first_name'], 'Jane')
        self.assertEqual(customer['phone_number'], '09987654321')


class MobileSyncAPITests(MobileAPITestCase):
    """Tests for mobile synchronization API endpoints."""
    
    def test_sync_data_download(self):
        """Test downloading sync data."""
        url = reverse('mobile-sync-sync-data')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        sync_data = response.data['sync_data']
        self.assertIn('categories', sync_data)
        self.assertIn('jewelry_items', sync_data)
        self.assertIn('customers', sync_data)
        self.assertIn('settings', sync_data)
    
    def test_sync_data_upload(self):
        """Test uploading sync data."""
        url = reverse('mobile-sync-upload-sync-data')
        
        sync_data = {
            'sync_data': {
                'customers': [
                    {
                        'first_name': 'Mobile',
                        'last_name': 'Customer',
                        'persian_first_name': 'موبایل',
                        'persian_last_name': 'مشتری',
                        'phone_number': '09111111111',
                        'email': 'mobile@example.com'
                    }
                ],
                'inventory_updates': [
                    {
                        'item_id': self.jewelry_item.id,
                        'quantity': 8
                    }
                ]
            }
        }
        
        response = self.client.post(url, sync_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        sync_results = response.data['sync_results']
        self.assertEqual(sync_results['customers_created'], 1)
        self.assertEqual(sync_results['inventory_updates'], 1)


class OfflineSyncAPITests(MobileAPITestCase):
    """Tests for offline synchronization API endpoints."""
    
    def test_get_sync_manifest(self):
        """Test getting synchronization manifest."""
        url = reverse('sync-manifest')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        manifest = response.data['manifest']
        self.assertIn('server_time', manifest)
        self.assertIn('data_manifest', manifest)
        self.assertIn('system_settings', manifest)
        
        data_manifest = manifest['data_manifest']
        self.assertIn('categories', data_manifest)
        self.assertIn('jewelry_items', data_manifest)
        self.assertIn('customers', data_manifest)
    
    def test_download_sync_data(self):
        """Test downloading sync data with specific requests."""
        url = reverse('sync-download')
        
        request_data = {
            'requested_data': {
                'categories': True,
                'jewelry_items': True,
                'customers': True
            },
            'device_id': 'test-device-001'
        }
        
        response = self.client.post(url, request_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        sync_data = response.data['sync_data']
        self.assertIn('data', sync_data)
        self.assertIn('system_settings', sync_data)
        self.assertIn('cache_key', response.data)
    
    def test_upload_offline_transactions(self):
        """Test uploading offline transactions."""
        url = reverse('sync-upload-transactions')
        
        transaction_data = {
            'transactions': [
                {
                    'offline_transaction_id': str(uuid.uuid4()),
                    'customer': self.customer.id,
                    'transaction_type': 'sale',
                    'payment_method': 'cash',
                    'subtotal': '1500000.00',
                    'total_amount': '1500000.00',
                    'amount_paid': '1500000.00',
                    'line_items': [
                        {
                            'jewelry_item_id': self.jewelry_item.id,
                            'item_name': 'Test Ring',
                            'quantity': 1,
                            'unit_price': '1500000.00'
                        }
                    ]
                }
            ],
            'device_id': 'test-device-001'
        }
        
        response = self.client.post(url, transaction_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        sync_results = response.data['sync_results']
        self.assertEqual(sync_results['total_transactions'], 1)
        self.assertEqual(sync_results['successful_syncs'], 1)
    
    def test_get_sync_status(self):
        """Test getting synchronization status."""
        url = reverse('sync-status')
        response = self.client.get(url, {'device_id': 'test-device-001'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        sync_status = response.data['sync_status']
        self.assertIn('pending_transactions_count', sync_status)
        self.assertIn('failed_transactions_count', sync_status)
        self.assertIn('server_time', sync_status)
        self.assertIn('sync_required', sync_status)


class PushNotificationAPITests(MobileAPITestCase):
    """Tests for push notification API endpoints."""
    
    def setUp(self):
        """Set up notification test data."""
        super().setUp()
        
        with schema_context(self.tenant.schema_name):
            # Create mobile device
            self.mobile_device = MobileDevice.objects.create(
                user=self.user,
                device_id='test-device-001',
                device_token='test-token-123',
                device_type='android',
                app_version='1.0.0'
            )
            
            # Create notification template
            self.notification_template = NotificationTemplate.objects.create(
                name='Test Template',
                template_type='custom',
                title='Test Notification',
                content='This is a test notification for {customer_name}',
                delivery_methods=['push'],
                is_active=True,
                created_by=self.user
            )
            
            # Create notification provider
            self.notification_provider = NotificationProvider.objects.create(
                name='Test Push Provider',
                provider_type='push',
                is_active=True,
                is_default=True,
                created_by=self.user
            )
    
    def test_register_mobile_device(self):
        """Test mobile device registration."""
        url = reverse('mobile-devices-register')
        
        device_data = {
            'device_token': 'new-test-token-456',
            'device_type': 'ios',
            'device_id': 'test-device-002',
            'app_version': '1.0.1',
            'os_version': '15.0',
            'device_model': 'iPhone 13'
        }
        
        response = self.client.post(url, device_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('device_id', response.data)
        self.assertIn('registration_id', response.data)
    
    def test_send_push_notification(self):
        """Test sending push notification."""
        url = reverse('push-send')
        
        notification_data = {
            'title': 'Test Push',
            'message': 'This is a test push notification',
            'notification_type': 'custom',
            'priority': 'normal',
            'recipient_type': 'user',
            'recipient_ids': [self.user.id]
        }
        
        response = self.client.post(url, notification_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertGreater(response.data['notifications_created'], 0)
    
    def test_send_payment_reminder(self):
        """Test sending payment reminder notification."""
        url = reverse('push-payment-reminder')
        
        reminder_data = {
            'customer_id': self.customer.id,
            'contract_number': 'GOLD-001',
            'amount': 500000.0,
            'due_date': '1403/06/15'
        }
        
        response = self.client.post(url, reminder_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertGreater(response.data['notifications_created'], 0)
    
    def test_get_notification_history(self):
        """Test getting notification history."""
        # Create a test notification
        with schema_context(self.tenant.schema_name):
            Notification.objects.create(
                recipient_type='user',
                recipient_id=self.user.id,
                recipient_name=self.user.username,
                title='Test Notification',
                content='Test content',
                delivery_method='push',
                template=self.notification_template,
                created_by=self.user
            )
        
        url = reverse('push-history')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertGreater(response.data['total_count'], 0)
    
    def test_test_push_notification(self):
        """Test push notification testing endpoint."""
        url = reverse('push-test')
        
        test_data = {
            'device_id': 'test-device-001'
        }
        
        response = self.client.post(url, test_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])


class MobileAPIPerformanceTests(MobileAPITestCase):
    """Performance tests for mobile API endpoints."""
    
    def setUp(self):
        """Set up performance test data."""
        super().setUp()
        
        # Create multiple test items for performance testing
        with schema_context(self.tenant.schema_name):
            for i in range(50):
                JewelryItem.objects.create(
                    name=f'Test Item {i}',
                    sku=f'TEST-{i:03d}',
                    barcode=f'TEST{i:03d}',
                    category=self.category,
                    weight_grams=Decimal('5.000'),
                    karat=18,
                    selling_price=Decimal('1000000'),
                    quantity=10,
                    created_by=self.user
                )
    
    def test_mobile_dashboard_performance(self):
        """Test mobile dashboard response time."""
        import time
        
        url = reverse('mobile-pos-mobile-dashboard')
        
        start_time = time.time()
        response = self.client.get(url)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(response_time, 1.0)  # Should respond within 1 second
    
    def test_inventory_search_performance(self):
        """Test inventory search performance with multiple items."""
        import time
        
        url = reverse('mobile-inventory-quick-search')
        
        start_time = time.time()
        response = self.client.get(url, {'q': 'Test'})
        end_time = time.time()
        
        response_time = end_time - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(response_time, 0.5)  # Should respond within 500ms
        self.assertLessEqual(len(response.data['items']), 20)  # Limited results


class MobileAPISecurityTests(MobileAPITestCase):
    """Security tests for mobile API endpoints."""
    
    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated requests are denied."""
        # Remove authentication
        self.client.credentials()
        
        url = reverse('mobile-pos-mobile-dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_cross_tenant_data_isolation(self):
        """Test that users cannot access other tenant's data."""
        # Create another tenant
        other_tenant = Tenant.objects.create(
            name='Other Jewelry Shop',
            schema_name='other_shop',
            paid_until=timezone.now() + timedelta(days=30)
        )
        
        # Create user in other tenant
        with schema_context(other_tenant.schema_name):
            other_user = User.objects.create_user(
                username='otheruser',
                email='other@example.com',
                password='otherpass123',
                role='owner'
            )
            other_token = Token.objects.create(user=other_user)
        
        # Try to access original tenant's data with other tenant's token
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {other_token.key}')
        self.client.defaults['HTTP_HOST'] = 'testshop.zargar.com'
        
        url = reverse('mobile-inventory-quick-search')
        response = self.client.get(url, {'q': 'Test'})
        
        # Should not find any items from original tenant
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
    
    def test_role_based_access_control(self):
        """Test role-based access control for mobile endpoints."""
        # Create salesperson user (limited permissions)
        with schema_context(self.tenant.schema_name):
            salesperson = User.objects.create_user(
                username='salesperson',
                email='sales@example.com',
                password='salespass123',
                role='salesperson'
            )
            sales_token = Token.objects.create(user=salesperson)
        
        # Test with salesperson credentials
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {sales_token.key}')
        
        # Should be able to access POS functions
        url = reverse('mobile-pos-mobile-dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should be able to search inventory
        url = reverse('mobile-inventory-quick-search')
        response = self.client.get(url, {'q': 'Test'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


if __name__ == '__main__':
    pytest.main([__file__])