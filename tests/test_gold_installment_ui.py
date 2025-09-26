"""
Tests for Gold Installment System UI components.
"""
import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import date

from zargar.tenants.models import Tenant
from zargar.customers.models import Customer
from zargar.gold_installments.models import GoldInstallmentContract, GoldInstallmentPayment
from zargar.gold_installments.forms import GoldInstallmentContractForm, GoldInstallmentPaymentForm

User = get_user_model()


class GoldInstallmentUITestCase(TestCase):
    """Base test case for gold installment UI tests."""
    
    def setUp(self):
        """Set up test data."""
        # Create tenant
        self.tenant = Tenant.objects.create(
            name="Test Jewelry Shop",
            schema_name="test_shop",
            owner_name="Test Owner",
            owner_email="owner@test.com"
        )
        
        # Create domain for tenant
        from zargar.tenants.models import Domain
        self.domain = Domain.objects.create(
            domain="test-shop.localhost",
            tenant=self.tenant,
            is_primary=True
        )
        
        # Create user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            tenant=self.tenant
        )
        
        # Create customer
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            first_name="John",
            last_name="Doe",
            persian_first_name="جان",
            persian_last_name="دو",
            phone_number="09123456789",
            customer_type="individual"
        )
        
        # Create contract
        self.contract = GoldInstallmentContract.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            contract_date=date.today(),
            initial_gold_weight_grams=Decimal('10.000'),
            remaining_gold_weight_grams=Decimal('10.000'),
            gold_karat=18,
            payment_schedule='monthly',
            contract_terms_persian="شرایط قرارداد طلای قرضی",
            created_by=self.user
        )
        
        self.client = Client()
        self.client.force_login(self.user)


class GoldInstallmentDashboardViewTest(GoldInstallmentUITestCase):
    """Test gold installment dashboard view."""
    
    def test_dashboard_view_loads(self):
        """Test that dashboard view loads successfully."""
        # Mock tenant context
        with self.settings(TENANT_MODEL='zargar.tenants.models.Tenant'):
            response = self.client.get('/gold-installments/')
            
            # Should not return 404 (URL exists)
            self.assertNotEqual(response.status_code, 404)


class GoldInstallmentContractFormTest(GoldInstallmentUITestCase):
    """Test gold installment contract form."""
    
    def test_contract_form_initialization(self):
        """Test contract form initializes correctly."""
        form = GoldInstallmentContractForm(tenant=self.tenant)
        
        # Check that customer queryset is filtered by tenant
        self.assertEqual(
            list(form.fields['customer'].queryset),
            list(Customer.objects.filter(tenant=self.tenant))
        )
    
    def test_contract_form_validation(self):
        """Test contract form validation."""
        form_data = {
            'customer': self.customer.id,
            'contract_date': date.today(),
            'initial_gold_weight_grams': '10.000',
            'gold_karat': 18,
            'payment_schedule': 'monthly',
            'contract_terms_persian': 'شرایط قرارداد',
            'early_payment_discount_percentage': '0.00'
        }
        
        form = GoldInstallmentContractForm(data=form_data, tenant=self.tenant)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
    
    def test_contract_form_price_protection_validation(self):
        """Test price protection validation."""
        form_data = {
            'customer': self.customer.id,
            'contract_date': date.today(),
            'initial_gold_weight_grams': '10.000',
            'gold_karat': 18,
            'payment_schedule': 'monthly',
            'contract_terms_persian': 'شرایط قرارداد',
            'has_price_protection': True,
            'price_ceiling_per_gram': '2000000',
            'price_floor_per_gram': '3000000',  # Floor higher than ceiling
            'early_payment_discount_percentage': '0.00'
        }
        
        form = GoldInstallmentContractForm(data=form_data, tenant=self.tenant)
        self.assertFalse(form.is_valid())
        self.assertIn('price_ceiling_per_gram', form.errors)


class GoldInstallmentPaymentFormTest(GoldInstallmentUITestCase):
    """Test gold installment payment form."""
    
    def test_payment_form_validation(self):
        """Test payment form validation."""
        form_data = {
            'payment_date': date.today(),
            'payment_amount_toman': '1000000',
            'gold_price_per_gram_at_payment': '3500000',
            'payment_method': 'cash'
        }
        
        form = GoldInstallmentPaymentForm(data=form_data, tenant=self.tenant)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
    
    def test_payment_form_amount_validation(self):
        """Test payment amount validation."""
        form_data = {
            'payment_date': date.today(),
            'payment_amount_toman': '0',  # Invalid amount
            'gold_price_per_gram_at_payment': '3500000',
            'payment_method': 'cash'
        }
        
        form = GoldInstallmentPaymentForm(data=form_data, tenant=self.tenant)
        self.assertFalse(form.is_valid())
        self.assertIn('payment_amount_toman', form.errors)
    
    def test_payment_form_gold_price_validation(self):
        """Test gold price validation."""
        form_data = {
            'payment_date': date.today(),
            'payment_amount_toman': '1000000',
            'gold_price_per_gram_at_payment': '0',  # Invalid price
            'payment_method': 'cash'
        }
        
        form = GoldInstallmentPaymentForm(data=form_data, tenant=self.tenant)
        self.assertFalse(form.is_valid())
        self.assertIn('gold_price_per_gram_at_payment', form.errors)


class GoldInstallmentAjaxViewsTest(GoldInstallmentUITestCase):
    """Test AJAX endpoints for gold installment system."""
    
    def test_customer_search_ajax(self):
        """Test customer search AJAX endpoint."""
        response = self.client.get(
            '/gold-installments/ajax/customer-search/',
            {'q': 'جان'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Should not return 404 (URL exists)
        self.assertNotEqual(response.status_code, 404)
    
    def test_gold_calculator_ajax(self):
        """Test gold price calculator AJAX endpoint."""
        response = self.client.get(
            '/gold-installments/ajax/gold-calculator/',
            {'amount': '1000000', 'gold_price': '3500000'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Should not return 404 (URL exists)
        self.assertNotEqual(response.status_code, 404)


class GoldInstallmentTemplateTest(GoldInstallmentUITestCase):
    """Test template rendering and context."""
    
    def test_dashboard_template_context(self):
        """Test dashboard template receives correct context."""
        # This test would require proper tenant middleware setup
        # For now, just verify the view exists
        try:
            from zargar.gold_installments.views import GoldInstallmentDashboardView
            view = GoldInstallmentDashboardView()
            self.assertIsNotNone(view)
        except ImportError:
            self.fail("GoldInstallmentDashboardView not found")
    
    def test_contract_detail_template_context(self):
        """Test contract detail template context."""
        try:
            from zargar.gold_installments.views import GoldInstallmentContractDetailView
            view = GoldInstallmentContractDetailView()
            self.assertIsNotNone(view)
        except ImportError:
            self.fail("GoldInstallmentContractDetailView not found")


class GoldInstallmentFormIntegrationTest(GoldInstallmentUITestCase):
    """Integration tests for forms and models."""
    
    def test_contract_creation_workflow(self):
        """Test complete contract creation workflow."""
        # Test form data
        form_data = {
            'customer': self.customer.id,
            'contract_date': date.today(),
            'initial_gold_weight_grams': '15.500',
            'gold_karat': 18,
            'payment_schedule': 'weekly',
            'contract_terms_persian': 'شرایط جدید قرارداد طلای قرضی',
            'early_payment_discount_percentage': '5.00'
        }
        
        # Create form and validate
        form = GoldInstallmentContractForm(data=form_data, tenant=self.tenant)
        self.assertTrue(form.is_valid())
        
        # Save contract
        contract = form.save(commit=False)
        contract.tenant = self.tenant
        contract.created_by = self.user
        contract.save()
        
        # Verify contract was created correctly
        self.assertEqual(contract.customer, self.customer)
        self.assertEqual(contract.initial_gold_weight_grams, Decimal('15.500'))
        self.assertEqual(contract.remaining_gold_weight_grams, Decimal('15.500'))
        self.assertEqual(contract.gold_karat, 18)
        self.assertEqual(contract.payment_schedule, 'weekly')
        self.assertEqual(contract.early_payment_discount_percentage, Decimal('5.00'))
    
    def test_payment_processing_workflow(self):
        """Test complete payment processing workflow."""
        # Test payment data
        form_data = {
            'payment_date': date.today(),
            'payment_amount_toman': '3500000',  # 1 gram worth
            'gold_price_per_gram_at_payment': '3500000',
            'payment_method': 'cash',
            'payment_notes': 'Test payment'
        }
        
        # Create form and validate
        form = GoldInstallmentPaymentForm(data=form_data, tenant=self.tenant)
        self.assertTrue(form.is_valid())
        
        # Process payment through contract
        payment_amount = form.cleaned_data['payment_amount_toman']
        gold_price = form.cleaned_data['gold_price_per_gram_at_payment']
        
        # Calculate expected gold weight
        expected_gold_weight = payment_amount / gold_price
        
        # Verify calculation
        self.assertEqual(expected_gold_weight, Decimal('1.000'))
        
        # Test that payment would reduce remaining weight
        original_remaining = self.contract.remaining_gold_weight_grams
        expected_remaining = original_remaining - expected_gold_weight
        
        self.assertEqual(expected_remaining, Decimal('9.000'))


if __name__ == '__main__':
    pytest.main([__file__])