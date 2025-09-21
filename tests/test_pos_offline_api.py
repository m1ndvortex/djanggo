"""
Tests for POS offline API endpoints.
Tests the REST API for offline transaction management.
"""
import os
import django
from django.conf import settings

# Setup Django
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import json
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django_tenants.utils import get_tenant_model, tenant_context

from zargar.pos.models import POSOfflineStorage
from zargar.customers.models import Customer
from zargar.jewelry.models import JewelryItem, Category

User = get_user_model()


class POSOfflineAPITest(TestCase):
    """Test POS offline API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        # Get tenant
        Tenant = get_tenant_model()
        self.tenant = Tenant.objects.exclude(schema_name='public').first()
        
        if not self.tenant:
            self.tenant = Tenant.objects.create(
                schema_name='test_offline_api',
                name='Test Offline API'
            )
        
        with tenant_context(self.tenant):
            # Create user
            self.user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123'
            )
            
            # Create customer
            self.customer = Customer.objects.create(
                first_name='احمد',
                last_name='محمدی',
                persian_first_name='احمد',
                persian_last_name='محمدی',
                phone_number='09123456789'
            )
            
            # Create category and jewelry item
            self.category = Category.objects.create(
                name='Rings',
                name_persian='انگشتر'
            )
            
            self.jewelry_item = JewelryItem.objects.create(
                name='Gold Ring 18K',
                category=self.category,
                sku='RING-001',
                weight_grams=Decimal('5.500'),
                karat=18,
                selling_price=Decimal('2500000.00'),
                quantity=10,
                status='in_stock'
            )
            
            # Create client and login
            self.client = Client()
            self.client.login(username='testuser', password='testpass123')
    
    def test_create_offline_transaction_api(self):
        """Test creating offline transaction via API."""
        with tenant_context(self.tenant):
            url = reverse('pos:api_offline_create')
            
            data = {
                'device_id': 'TEST-DEVICE-API-001',
                'device_name': 'Test API Device',
                'customer_id': self.customer.id,
                'line_items': [
                    {
                        'jewelry_item_id': self.jewelry_item.id,
                        'item_name': 'Gold Ring 18K',
                        'item_sku': 'RING-001',
                        'quantity': 1,
                        'unit_price': '2500000.00',
                        'gold_weight_grams': '5.500',
                        'gold_karat': 18
                    }
                ],
                'payment_method': 'cash',
                'amount_paid': '2500000.00',
                'transaction_type': 'sale'
            }
            
            response = self.client.post(
                url,
                data=json.dumps(data),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            
            response_data = json.loads(response.content)
            self.assertTrue(response_data['success'])
            self.assertIn('storage_id', response_data)
            self.assertIn('transaction_data', response_data)
            self.assertEqual(response_data['sync_status'], 'pending')
            
            # Verify offline storage was created
            storage_id = response_data['storage_id']
            offline_storage = POSOfflineStorage.objects.get(storage_id=storage_id)
            self.assertEqual(offline_storage.device_id, 'TEST-DEVICE-API-001')
            self.assertFalse(offline_storage.is_synced)
    
    def test_offline_status_api(self):
        """Test getting offline status via API."""
        with tenant_context(self.tenant):
            # Create some offline transactions first
            POSOfflineStorage.objects.create(
                device_id='TEST-DEVICE-STATUS',
                device_name='Test Status Device',
                transaction_data={'test': 'data1', 'total_amount': '1000000.00'}
            )
            
            POSOfflineStorage.objects.create(
                device_id='TEST-DEVICE-STATUS',
                device_name='Test Status Device',
                transaction_data={'test': 'data2', 'total_amount': '2000000.00'},
                is_synced=True
            )
            
            url = reverse('pos:api_offline_status')
            response = self.client.get(url, {
                'device_id': 'TEST-DEVICE-STATUS',
                'device_name': 'Test Status Device'
            })
            
            self.assertEqual(response.status_code, 200)
            
            response_data = json.loads(response.content)
            self.assertTrue(response_data['success'])
            
            summary = response_data['summary']
            self.assertEqual(summary['device_id'], 'TEST-DEVICE-STATUS')
            self.assertEqual(summary['total_transactions'], 2)
            self.assertEqual(summary['pending_sync'], 1)
            self.assertEqual(summary['synced'], 1)
    
    def test_offline_sync_api(self):
        """Test syncing offline transactions via API."""
        with tenant_context(self.tenant):
            # Create offline transaction
            offline_storage = POSOfflineStorage.objects.create(
                device_id='TEST-DEVICE-SYNC',
                device_name='Test Sync Device',
                transaction_data={
                    'transaction_id': 'test-sync-123',
                    'customer_id': self.customer.id,
                    'transaction_type': 'sale',
                    'payment_method': 'cash',
                    'subtotal': '2500000.00',
                    'total_amount': '2500000.00',
                    'amount_paid': '2500000.00',
                    'line_items': []
                }
            )
            
            url = reverse('pos:api_offline_sync')
            
            data = {
                'device_id': 'TEST-DEVICE-SYNC',
                'device_name': 'Test Sync Device'
            }
            
            # Mock the connection check to return True
            from unittest.mock import patch
            with patch('zargar.pos.models.OfflinePOSSystem._check_connection', return_value=True):
                response = self.client.post(
                    url,
                    data=json.dumps(data),
                    content_type='application/json'
                )
            
            self.assertEqual(response.status_code, 200)
            
            response_data = json.loads(response.content)
            self.assertTrue(response_data['success'])
            self.assertIn('sync_results', response_data)
            
            sync_results = response_data['sync_results']
            self.assertEqual(sync_results['total_pending'], 1)
            self.assertEqual(sync_results['synced_successfully'], 1)
    
    def test_offline_conflict_resolution_api(self):
        """Test resolving offline conflicts via API."""
        with tenant_context(self.tenant):
            # Create conflicted offline transaction
            offline_storage = POSOfflineStorage.objects.create(
                device_id='TEST-DEVICE-CONFLICT',
                device_name='Test Conflict Device',
                transaction_data={'test': 'conflict_data'},
                sync_status='conflict',
                has_conflicts=True
            )
            
            url = reverse('pos:api_offline_resolve_conflicts')
            
            data = {
                'device_id': 'TEST-DEVICE-CONFLICT',
                'device_name': 'Test Conflict Device',
                'resolution_actions': {
                    str(offline_storage.storage_id): 'retry'
                }
            }
            
            response = self.client.post(
                url,
                data=json.dumps(data),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            
            response_data = json.loads(response.content)
            self.assertTrue(response_data['success'])
            self.assertIn('resolution_results', response_data)
            
            results = response_data['resolution_results']
            self.assertEqual(results['total_conflicts'], 1)
            self.assertEqual(results['resolved'], 1)
            
            # Verify conflict was resolved
            offline_storage.refresh_from_db()
            self.assertFalse(offline_storage.has_conflicts)
            self.assertEqual(offline_storage.sync_status, 'pending')
    
    def test_offline_cleanup_api(self):
        """Test cleaning up old offline transactions via API."""
        with tenant_context(self.tenant):
            from django.utils import timezone
            from datetime import timedelta
            
            # Create old synced transaction
            old_date = timezone.now() - timedelta(days=35)
            POSOfflineStorage.objects.create(
                device_id='TEST-DEVICE-CLEANUP',
                device_name='Test Cleanup Device',
                transaction_data={'test': 'old_data'},
                is_synced=True,
                synced_at=old_date
            )
            
            # Create recent transaction
            POSOfflineStorage.objects.create(
                device_id='TEST-DEVICE-CLEANUP',
                device_name='Test Cleanup Device',
                transaction_data={'test': 'recent_data'},
                is_synced=True,
                synced_at=timezone.now()
            )
            
            url = reverse('pos:api_offline_cleanup')
            
            data = {
                'device_id': 'TEST-DEVICE-CLEANUP',
                'device_name': 'Test Cleanup Device',
                'days_old': 30
            }
            
            response = self.client.post(
                url,
                data=json.dumps(data),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            
            response_data = json.loads(response.content)
            self.assertTrue(response_data['success'])
            self.assertEqual(response_data['cleaned_count'], 1)
            
            # Verify only recent transaction remains
            remaining_count = POSOfflineStorage.objects.filter(
                device_id='TEST-DEVICE-CLEANUP'
            ).count()
            self.assertEqual(remaining_count, 1)
    
    def test_offline_export_api(self):
        """Test exporting offline transaction data via API."""
        with tenant_context(self.tenant):
            # Create offline transactions
            POSOfflineStorage.objects.create(
                device_id='TEST-DEVICE-EXPORT',
                device_name='Test Export Device',
                transaction_data={'test': 'export_data1'}
            )
            
            POSOfflineStorage.objects.create(
                device_id='TEST-DEVICE-EXPORT',
                device_name='Test Export Device',
                transaction_data={'test': 'export_data2'},
                is_synced=True
            )
            
            url = reverse('pos:api_offline_export')
            
            response = self.client.get(url, {
                'device_id': 'TEST-DEVICE-EXPORT',
                'device_name': 'Test Export Device'
            })
            
            self.assertEqual(response.status_code, 200)
            
            response_data = json.loads(response.content)
            self.assertTrue(response_data['success'])
            self.assertIn('export_data', response_data)
            
            export_data = response_data['export_data']
            self.assertEqual(export_data['device_id'], 'TEST-DEVICE-EXPORT')
            self.assertEqual(len(export_data['transactions']), 2)
            self.assertIn('export_timestamp', export_data)
    
    def test_api_error_handling(self):
        """Test API error handling."""
        with tenant_context(self.tenant):
            # Test with invalid JSON
            url = reverse('pos:api_offline_create')
            
            response = self.client.post(
                url,
                data='invalid json',
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 400)
            
            response_data = json.loads(response.content)
            self.assertFalse(response_data['success'])
            self.assertIn('error', response_data)
    
    def test_api_authentication_required(self):
        """Test that API endpoints require authentication."""
        with tenant_context(self.tenant):
            # Logout user
            self.client.logout()
            
            url = reverse('pos:api_offline_create')
            
            response = self.client.post(
                url,
                data=json.dumps({'test': 'data'}),
                content_type='application/json'
            )
            
            # Should redirect to login or return 403/401
            self.assertIn(response.status_code, [302, 401, 403])


if __name__ == '__main__':
    import unittest
    unittest.main()