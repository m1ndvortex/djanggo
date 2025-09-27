"""
Tests for DRF API endpoints with tenant filtering and authentication.
"""
import json
from decimal import Decimal
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from zargar.tenants.models import Tenant, Domain
from zargar.jewelry.models import JewelryItem, Category, Gemstone
from zargar.customers.models import Customer, Supplier
from zargar.pos.models import POSTransaction, POSTransactionLineItem

User = get_user_model()


class APIAuthenticationTestCase(TenantTestCase):
    """
    Test API authentication with tenant context.
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create tenant for testing
        cls.tenant = Tenant(
            schema_name='test_jewelry_shop',
            name='Test Jewelry Shop',
            paid_until='2024-12-31',
            on_trial=False
        )
        cls.tenant.save()
        
        # Create domain
        cls.domain = Domain(
            domain='test-jewelry-shop.zargar.com',
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
    
    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
        
        # Generate JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        # Set authentication header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_jwt_authentication_success(self):
        """
        Test successful JWT authentication.
        """
        url = reverse('jewelryitem-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_jwt_authentication_failure(self):
        """
        Test JWT authentication failure with invalid token.
        """
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        
        url = reverse('jewelryitem-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_unauthenticated_request(self):
        """
        Test unauthenticated request is rejected.
        """
        self.client.credentials()  # Remove authentication
        
        url = reverse('jewelryitem-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_token_obtain_pair(self):
        """
        Test JWT token generation.
        """
        url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
    
    def test_token_refresh(self):
        """
        Test JWT token refresh.
        """
        refresh = RefreshToken.for_user(self.user)
        
        url = reverse('token_refresh')
        data = {'refresh': str(refresh)}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)


class JewelryItemAPITestCase(TenantTestCase):
    """
    Test jewelry item API endpoints.
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant(
            schema_name='test_jewelry_api',
            name='Test Jewelry API',
            paid_until='2024-12-31',
            on_trial=False
        )
        cls.tenant.save()
        
        cls.domain = Domain(
            domain='test-jewelry-api.zargar.com',
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
    
    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)
        
        # Create test user
        self.user = User.objects.create_user(
            username='jewelryuser',
            email='jewelry@example.com',
            password='testpass123',
            role='owner'
        )
        
        # Authenticate
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Create test data
        self.category = Category.objects.create(
            name='Rings',
            name_persian='انگشتر'
        )
        
        self.jewelry_item = JewelryItem.objects.create(
            name='Gold Ring',
            sku='RING001',
            category=self.category,
            weight_grams=Decimal('5.500'),
            karat=18,
            manufacturing_cost=Decimal('500000'),
            selling_price=Decimal('2000000'),
            quantity=10,
            minimum_stock=2
        )
    
    def test_list_jewelry_items(self):
        """
        Test listing jewelry items.
        """
        url = reverse('jewelryitem-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Gold Ring')
    
    def test_create_jewelry_item(self):
        """
        Test creating a jewelry item.
        """
        url = reverse('jewelryitem-list')
        data = {
            'name': 'Silver Necklace',
            'sku': 'NECK001',
            'category': self.category.id,
            'weight_grams': '15.750',
            'karat': 14,
            'manufacturing_cost': '800000',
            'selling_price': '3000000',
            'quantity': 5,
            'minimum_stock': 1
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Silver Necklace')
        self.assertEqual(response.data['sku'], 'NECK001')
    
    def test_update_jewelry_item(self):
        """
        Test updating a jewelry item.
        """
        url = reverse('jewelryitem-detail', kwargs={'pk': self.jewelry_item.pk})
        data = {
            'name': 'Updated Gold Ring',
            'selling_price': '2500000'
        }
        
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Gold Ring')
        self.assertEqual(response.data['selling_price'], '2500000.00')
    
    def test_delete_jewelry_item(self):
        """
        Test deleting a jewelry item.
        """
        url = reverse('jewelryitem-detail', kwargs={'pk': self.jewelry_item.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(JewelryItem.objects.filter(pk=self.jewelry_item.pk).exists())
    
    def test_low_stock_items(self):
        """
        Test getting low stock items.
        """
        # Create low stock item
        low_stock_item = JewelryItem.objects.create(
            name='Low Stock Ring',
            sku='LOW001',
            category=self.category,
            weight_grams=Decimal('3.000'),
            karat=18,
            manufacturing_cost=Decimal('300000'),
            quantity=1,  # Below minimum stock
            minimum_stock=5
        )
        
        url = reverse('jewelryitem-low-stock')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Low Stock Ring')
    
    def test_generate_barcode(self):
        """
        Test generating barcode for jewelry item.
        """
        # Remove existing barcode
        self.jewelry_item.barcode = ''
        self.jewelry_item.save()
        
        url = reverse('jewelryitem-generate-barcode', kwargs={'pk': self.jewelry_item.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['barcode'])
        self.assertTrue(response.data['barcode'].startswith('JWL-'))
    
    def test_filter_by_category(self):
        """
        Test filtering jewelry items by category.
        """
        url = reverse('jewelryitem-list')
        response = self.client.get(url, {'category': self.category.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_search_jewelry_items(self):
        """
        Test searching jewelry items.
        """
        url = reverse('jewelryitem-list')
        response = self.client.get(url, {'search': 'Gold'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Gold Ring')


class CustomerAPITestCase(TenantTestCase):
    """
    Test customer API endpoints.
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant(
            schema_name='test_customer_api',
            name='Test Customer API',
            paid_until='2024-12-31',
            on_trial=False
        )
        cls.tenant.save()
        
        cls.domain = Domain(
            domain='test-customer-api.zargar.com',
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
    
    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)
        
        # Create test user
        self.user = User.objects.create_user(
            username='customeruser',
            email='customer@example.com',
            password='testpass123',
            role='salesperson'
        )
        
        # Authenticate
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Create test customer
        self.customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            persian_first_name='جان',
            persian_last_name='دو',
            phone_number='09123456789',
            email='john@example.com',
            loyalty_points=100
        )
    
    def test_list_customers(self):
        """
        Test listing customers.
        """
        url = reverse('customer-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['first_name'], 'John')
    
    def test_create_customer(self):
        """
        Test creating a customer.
        """
        url = reverse('customer-list')
        data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'persian_first_name': 'جین',
            'persian_last_name': 'اسمیت',
            'phone_number': '09987654321',
            'email': 'jane@example.com'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['first_name'], 'Jane')
        self.assertEqual(response.data['phone_number'], '09987654321')
    
    def test_add_loyalty_points(self):
        """
        Test adding loyalty points to customer.
        """
        url = reverse('customer-add-loyalty-points', kwargs={'pk': self.customer.pk})
        data = {
            'points': 50,
            'reason': 'Purchase bonus'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['loyalty_points'], 150)
    
    def test_redeem_loyalty_points(self):
        """
        Test redeeming loyalty points from customer.
        """
        url = reverse('customer-redeem-loyalty-points', kwargs={'pk': self.customer.pk})
        data = {
            'points': 30,
            'reason': 'Discount applied'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['loyalty_points'], 70)
    
    def test_search_customers(self):
        """
        Test searching customers.
        """
        url = reverse('customer-list')
        response = self.client.get(url, {'search': 'John'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['first_name'], 'John')


class POSTransactionAPITestCase(TenantTestCase):
    """
    Test POS transaction API endpoints.
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant(
            schema_name='test_pos_api',
            name='Test POS API',
            paid_until='2024-12-31',
            on_trial=False
        )
        cls.tenant.save()
        
        cls.domain = Domain(
            domain='test-pos-api.zargar.com',
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
    
    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)
        
        # Create test user
        self.user = User.objects.create_user(
            username='posuser',
            email='pos@example.com',
            password='testpass123',
            role='salesperson'
        )
        
        # Authenticate
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Create test data
        self.customer = Customer.objects.create(
            first_name='Test',
            last_name='Customer',
            phone_number='09123456789'
        )
        
        self.category = Category.objects.create(
            name='Rings',
            name_persian='انگشتر'
        )
        
        self.jewelry_item = JewelryItem.objects.create(
            name='Test Ring',
            sku='TEST001',
            category=self.category,
            weight_grams=Decimal('5.000'),
            karat=18,
            manufacturing_cost=Decimal('500000'),
            selling_price=Decimal('1000000'),
            quantity=10
        )
    
    def test_create_pos_transaction(self):
        """
        Test creating a POS transaction with line items.
        """
        url = reverse('postransaction-list')
        data = {
            'customer': self.customer.id,
            'transaction_type': 'sale',
            'subtotal': '1000000',
            'tax_amount': '90000',
            'discount_amount': '0',
            'payment_method': 'cash',
            'amount_paid': '1090000',
            'line_items': [
                {
                    'jewelry_item': self.jewelry_item.id,
                    'item_name': 'Test Ring',
                    'quantity': 1,
                    'unit_price': '1000000',
                    'gold_weight_grams': '5.000',
                    'gold_karat': 18
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['customer'], self.customer.id)
    
    def test_list_pos_transactions(self):
        """
        Test listing POS transactions.
        """
        # Create a transaction first
        transaction = POSTransaction.objects.create(
            customer=self.customer,
            subtotal=Decimal('1000000'),
            tax_amount=Decimal('90000'),
            total_amount=Decimal('1090000'),
            payment_method='cash',
            amount_paid=Decimal('1090000')
        )
        
        url = reverse('postransaction-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_today_transactions(self):
        """
        Test getting today's transactions.
        """
        # Create a transaction
        transaction = POSTransaction.objects.create(
            customer=self.customer,
            subtotal=Decimal('1000000'),
            tax_amount=Decimal('90000'),
            total_amount=Decimal('1090000'),
            payment_method='cash',
            amount_paid=Decimal('1090000')
        )
        
        url = reverse('postransaction-today-transactions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('transactions', response.data)
        self.assertIn('summary', response.data)
        self.assertEqual(response.data['summary']['total_count'], 1)


class APIRateLimitingTestCase(TenantTestCase):
    """
    Test API rate limiting functionality.
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant(
            schema_name='test_rate_limit',
            name='Test Rate Limit',
            paid_until='2024-12-31',
            on_trial=False
        )
        cls.tenant.save()
        
        cls.domain = Domain(
            domain='test-rate-limit.zargar.com',
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
    
    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)
        
        # Create test user
        self.user = User.objects.create_user(
            username='ratelimituser',
            email='ratelimit@example.com',
            password='testpass123',
            role='owner'
        )
        
        # Authenticate
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    @override_settings(
        REST_FRAMEWORK={
            'DEFAULT_THROTTLE_CLASSES': [
                'zargar.api.throttling.TenantAPIThrottle',
            ],
            'DEFAULT_THROTTLE_RATES': {
                'tenant_api': '5/min'  # Very low rate for testing
            }
        }
    )
    def test_rate_limiting(self):
        """
        Test that API rate limiting works.
        """
        url = reverse('jewelryitem-list')
        
        # Make requests up to the limit
        for i in range(5):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Next request should be rate limited
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class APIPermissionTestCase(TenantTestCase):
    """
    Test API permission system.
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant(
            schema_name='test_permissions',
            name='Test Permissions',
            paid_until='2024-12-31',
            on_trial=False
        )
        cls.tenant.save()
        
        cls.domain = Domain(
            domain='test-permissions.zargar.com',
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
    
    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)
        
        # Create users with different roles
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='testpass123',
            role='owner'
        )
        
        self.salesperson = User.objects.create_user(
            username='salesperson',
            email='salesperson@example.com',
            password='testpass123',
            role='salesperson'
        )
        
        self.accountant = User.objects.create_user(
            username='accountant',
            email='accountant@example.com',
            password='testpass123',
            role='accountant'
        )
    
    def test_owner_permissions(self):
        """
        Test that owners have full access.
        """
        # Authenticate as owner
        refresh = RefreshToken.for_user(self.owner)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # Create category
        category = Category.objects.create(name='Test', name_persian='تست')
        
        # Test jewelry item creation (owner only)
        url = reverse('jewelryitem-list')
        data = {
            'name': 'Owner Ring',
            'sku': 'OWNER001',
            'category': category.id,
            'weight_grams': '5.000',
            'karat': 18,
            'manufacturing_cost': '500000',
            'quantity': 1
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_salesperson_permissions(self):
        """
        Test that salespersons have limited access.
        """
        # Authenticate as salesperson
        refresh = RefreshToken.for_user(self.salesperson)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # Create category as owner first
        refresh_owner = RefreshToken.for_user(self.owner)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh_owner.access_token}')
        category = Category.objects.create(name='Test', name_persian='تست')
        
        # Switch back to salesperson
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # Test jewelry item creation (should fail for salesperson)
        url = reverse('jewelryitem-list')
        data = {
            'name': 'Salesperson Ring',
            'sku': 'SALES001',
            'category': category.id,
            'weight_grams': '5.000',
            'karat': 18,
            'manufacturing_cost': '500000',
            'quantity': 1
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # But can view jewelry items
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_accountant_supplier_access(self):
        """
        Test that accountants can access supplier endpoints.
        """
        # Authenticate as accountant
        refresh = RefreshToken.for_user(self.accountant)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # Test supplier creation (accountant should have access)
        url = reverse('supplier-list')
        data = {
            'name': 'Test Supplier',
            'supplier_type': 'manufacturer',
            'phone_number': '09123456789'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_salesperson_supplier_access_denied(self):
        """
        Test that salespersons cannot access supplier endpoints.
        """
        # Authenticate as salesperson
        refresh = RefreshToken.for_user(self.salesperson)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # Test supplier access (should be denied)
        url = reverse('supplier-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)