"""
Production-ready comprehensive test for Tasks 5.1 and 5.2.
This test verifies that all models are correctly implemented and working.
"""

import pytest
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from zargar.jewelry.models import Category, Gemstone, JewelryItem, JewelryItemPhoto
from zargar.customers.models import (
    Customer, CustomerLoyaltyTransaction, CustomerNote,
    Supplier, PurchaseOrder, PurchaseOrderItem
)

User = get_user_model()


class ProductionReadyModelsTest(TestCase):
    """
    Comprehensive test to verify Tasks 5.1 and 5.2 are production-ready.
    """
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testowner',
            email='owner@testshop.com',
            password='testpass123',
            role='owner',
            persian_first_name='علی',
            persian_last_name='احمدی'
        )
    
    def test_task_5_1_jewelry_inventory_complete(self):
        """Test Task 5.1: Complete jewelry inventory management."""
        
        # 1. Create Category (ProductCategory)
        category = Category.objects.create(
            name='Rings',
            name_persian='انگشتر',
            description='Wedding and engagement rings',
            created_by=self.user
        )
        self.assertEqual(str(category), 'انگشتر')
        
        # 2. Create Gemstone
        gemstone = Gemstone.objects.create(
            name='Premium Diamond',
            gemstone_type='diamond',
            carat_weight=Decimal('1.250'),
            cut_grade='excellent',
            color_grade='D',
            clarity_grade='VVS1',
            certification_number='GIA-123456789',
            certification_authority='GIA',
            purchase_price=Decimal('50000000.00'),
            created_by=self.user
        )
        self.assertEqual(str(gemstone), 'Premium Diamond (1.250 carat)')
        
        # 3. Create JewelryItem with comprehensive tracking
        jewelry_item = JewelryItem.objects.create(
            name='Premium Diamond Ring',
            sku='RING-PREM-001',
            barcode='1234567890123',
            category=category,
            weight_grams=Decimal('15.750'),
            karat=18,
            manufacturing_cost=Decimal('5000000.00'),
            gold_value=Decimal('25000000.00'),
            gemstone_value=Decimal('50000000.00'),
            selling_price=Decimal('85000000.00'),
            status='in_stock',
            quantity=1,
            minimum_stock=1,
            description='Beautiful 18k gold ring with premium diamond',
            created_by=self.user
        )
        
        # Add gemstone relationship
        jewelry_item.gemstones.add(gemstone)
        
        # Verify comprehensive tracking
        self.assertEqual(jewelry_item.total_value, Decimal('80000000.00'))
        self.assertFalse(jewelry_item.is_low_stock)
        
        # Test gold value calculation
        calculated_gold = jewelry_item.calculate_gold_value(Decimal('3000000.00'))
        expected_gold = (Decimal('15.750') * Decimal('18') / Decimal('24')) * Decimal('3000000.00')
        self.assertEqual(calculated_gold, expected_gold)
        
        # 4. Create JewelryItemPhoto for multiple image management
        from django.core.files.uploadedfile import SimpleUploadedFile
        test_image = SimpleUploadedFile('test.jpg', b'fake image', content_type='image/jpeg')
        
        photo = JewelryItemPhoto.objects.create(
            jewelry_item=jewelry_item,
            image=test_image,
            caption='Front view',
            is_primary=True,
            order=1,
            created_by=self.user
        )
        
        self.assertTrue(photo.is_primary)
        self.assertEqual(photo.order, 1)
        
        print("✅ Task 5.1 - Jewelry Inventory Management: COMPLETE")
        print(f"   - Category: {category}")
        print(f"   - Gemstone: {gemstone}")
        print(f"   - JewelryItem: {jewelry_item}")
        print(f"   - Photo: {photo}")
    
    def test_task_5_2_customer_supplier_complete(self):
        """Test Task 5.2: Complete customer and supplier management."""
        
        # 1. Create Customer with Persian name handling and loyalty tracking
        customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            persian_first_name='جان',
            persian_last_name='دو',
            phone_number='09123456789',
            email='john.doe@example.com',
            customer_type='individual',
            loyalty_points=100,
            total_purchases=Decimal('25000000.00'),
            created_by=self.user
        )
        
        # Test Persian name handling
        self.assertEqual(str(customer), 'جان دو')
        self.assertEqual(customer.full_persian_name, 'جان دو')
        
        # Test loyalty point tracking
        customer.add_loyalty_points(50, "Purchase reward")
        customer.refresh_from_db()
        self.assertEqual(customer.loyalty_points, 150)
        
        # Verify loyalty transaction was created
        transaction = CustomerLoyaltyTransaction.objects.filter(customer=customer).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.points, 50)
        
        # Test purchase stats update and VIP upgrade
        customer.update_purchase_stats(Decimal('30000000.00'))  # Total becomes 55M
        customer.refresh_from_db()
        self.assertTrue(customer.is_vip)
        self.assertEqual(customer.customer_type, 'vip')
        
        # 2. Create Supplier with purchase order management
        supplier = Supplier.objects.create(
            name='Gold Supplier Inc',
            persian_name='تامین کننده طلا',
            supplier_type='gold_supplier',
            contact_person='Ahmad Rezaei',
            phone_number='02112345678',
            email='info@goldsupplier.com',
            payment_terms='Net 30',
            credit_limit=Decimal('100000000.00'),
            is_preferred=True,
            created_by=self.user
        )
        
        self.assertEqual(str(supplier), 'تامین کننده طلا')
        
        # 3. Create PurchaseOrder for supplier relationship management
        order_date = timezone.now().date()
        expected_delivery = order_date + timezone.timedelta(days=7)
        
        purchase_order = PurchaseOrder.objects.create(
            supplier=supplier,
            order_date=order_date,
            expected_delivery_date=expected_delivery,
            status='draft',
            priority='normal',
            subtotal=Decimal('10000000.00'),
            tax_amount=Decimal('900000.00'),
            discount_amount=Decimal('500000.00'),
            payment_terms='Net 30',
            notes='Test order for production verification',
            created_by=self.user
        )
        
        # Verify order number generation
        self.assertTrue(purchase_order.order_number.startswith('PO-'))
        
        # Test order workflow
        purchase_order.mark_as_sent()
        self.assertEqual(purchase_order.status, 'sent')
        
        purchase_order.mark_as_confirmed()
        self.assertEqual(purchase_order.status, 'confirmed')
        
        # 4. Create PurchaseOrderItem
        order_item = PurchaseOrderItem.objects.create(
            purchase_order=purchase_order,
            item_name='18k Gold Chain',
            item_description='Premium gold chain for jewelry making',
            sku='CHAIN-18K-001',
            quantity_ordered=10,
            unit_price=Decimal('2000000.00'),
            weight_grams=Decimal('25.500'),
            karat=18,
            notes='High quality chain',
            created_by=self.user
        )
        
        # Test quantity management
        self.assertEqual(order_item.quantity_pending, 10)
        self.assertFalse(order_item.is_fully_received)
        
        # Receive partial quantity
        order_item.receive_quantity(6)
        order_item.refresh_from_db()
        self.assertEqual(order_item.quantity_received, 6)
        self.assertEqual(order_item.quantity_pending, 4)
        
        # Complete the order
        purchase_order.mark_as_received(partial=False)
        self.assertEqual(purchase_order.status, 'completed')
        
        print("✅ Task 5.2 - Customer & Supplier Management: COMPLETE")
        print(f"   - Customer: {customer}")
        print(f"   - Supplier: {supplier}")
        print(f"   - PurchaseOrder: {purchase_order}")
        print(f"   - OrderItem: {order_item}")
    
    def test_production_requirements_verification(self):
        """Verify all production requirements are met."""
        
        # Requirement 7.1: JewelryItem with weight, karat, manufacturing cost, SKU
        jewelry_fields = [f.name for f in JewelryItem._meta.fields]
        required_jewelry_fields = ['weight_grams', 'karat', 'manufacturing_cost', 'sku']
        for field in required_jewelry_fields:
            self.assertIn(field, jewelry_fields, f"JewelryItem missing required field: {field}")
        
        # Requirement 7.6: ProductCategory (Category) for classification
        self.assertTrue(hasattr(Category, 'name'))
        self.assertTrue(hasattr(Category, 'name_persian'))
        
        # Requirement 7.7: Gemstone model for classification
        gemstone_fields = [f.name for f in Gemstone._meta.fields]
        required_gemstone_fields = ['gemstone_type', 'carat_weight', 'certification_number']
        for field in required_gemstone_fields:
            self.assertIn(field, gemstone_fields, f"Gemstone missing required field: {field}")
        
        # Requirement 9.3: Customer with Persian name handling and loyalty points
        customer_fields = [f.name for f in Customer._meta.fields]
        required_customer_fields = ['persian_first_name', 'persian_last_name', 'loyalty_points']
        for field in required_customer_fields:
            self.assertIn(field, customer_fields, f"Customer missing required field: {field}")
        
        # Requirement 7.8: Supplier with purchase order and payment terms
        supplier_fields = [f.name for f in Supplier._meta.fields]
        required_supplier_fields = ['payment_terms', 'supplier_type']
        for field in required_supplier_fields:
            self.assertIn(field, supplier_fields, f"Supplier missing required field: {field}")
        
        # Verify PurchaseOrder exists and has required functionality
        self.assertTrue(hasattr(PurchaseOrder, 'mark_as_sent'))
        self.assertTrue(hasattr(PurchaseOrder, 'mark_as_confirmed'))
        self.assertTrue(hasattr(PurchaseOrder, 'mark_as_received'))
        
        print("✅ All Production Requirements: VERIFIED")
        print("   - Requirement 7.1: JewelryItem comprehensive tracking ✓")
        print("   - Requirement 7.6: ProductCategory classification ✓")
        print("   - Requirement 7.7: Gemstone classification ✓")
        print("   - Requirement 9.3: Customer Persian names & loyalty ✓")
        print("   - Requirement 7.8: Supplier purchase orders ✓")


if __name__ == '__main__':
    pytest.main([__file__])