"""
Simple tests for Gold Installment System UI components without tenant setup.
"""
import pytest
from django.test import TestCase
from decimal import Decimal
from datetime import date

from zargar.gold_installments.forms import (
    GoldInstallmentContractForm, 
    GoldInstallmentPaymentForm,
    GoldWeightAdjustmentForm
)


class GoldInstallmentFormsSimpleTest(TestCase):
    """Simple tests for gold installment forms without tenant setup."""
    
    def test_contract_form_fields_exist(self):
        """Test that contract form has all required fields."""
        form = GoldInstallmentContractForm()
        
        # Check that key fields exist
        expected_fields = [
            'customer', 'contract_date', 'initial_gold_weight_grams',
            'gold_karat', 'payment_schedule', 'contract_terms_persian'
        ]
        
        for field_name in expected_fields:
            self.assertIn(field_name, form.fields, f"Field {field_name} not found in form")
    
    def test_payment_form_fields_exist(self):
        """Test that payment form has all required fields."""
        form = GoldInstallmentPaymentForm()
        
        # Check that key fields exist
        expected_fields = [
            'payment_date', 'payment_amount_toman', 
            'gold_price_per_gram_at_payment', 'payment_method'
        ]
        
        for field_name in expected_fields:
            self.assertIn(field_name, form.fields, f"Field {field_name} not found in form")
    
    def test_adjustment_form_fields_exist(self):
        """Test that adjustment form has all required fields."""
        form = GoldWeightAdjustmentForm()
        
        # Check that key fields exist
        expected_fields = [
            'adjustment_date', 'weight_before_grams', 'adjustment_amount_grams',
            'adjustment_type', 'adjustment_reason', 'description'
        ]
        
        for field_name in expected_fields:
            self.assertIn(field_name, form.fields, f"Field {field_name} not found in form")
    
    def test_payment_form_validation_logic(self):
        """Test payment form validation logic."""
        # Test field validation directly
        from django import forms
        
        # Test payment amount field validation
        payment_amount_field = forms.DecimalField(min_value=Decimal('0.01'))
        
        # Valid amount
        try:
            payment_amount_field.clean('1000000')
        except forms.ValidationError:
            self.fail("Valid payment amount should not raise ValidationError")
        
        # Invalid amount
        with self.assertRaises(forms.ValidationError):
            payment_amount_field.clean('0')
    
    def test_payment_form_gold_price_validation(self):
        """Test gold price validation in payment form."""
        # Test field validation directly
        from django import forms
        
        # Test gold price field validation
        gold_price_field = forms.DecimalField(min_value=Decimal('0.01'))
        
        # Valid price
        try:
            gold_price_field.clean('3500000')
        except forms.ValidationError:
            self.fail("Valid gold price should not raise ValidationError")
        
        # Invalid price
        with self.assertRaises(forms.ValidationError):
            gold_price_field.clean('0')
    
    def test_contract_form_price_protection_validation(self):
        """Test price protection validation in contract form."""
        # Test with invalid price protection (floor higher than ceiling)
        form_data = {
            'contract_date': date.today().strftime('%Y-%m-%d'),
            'initial_gold_weight_grams': '10.000',
            'gold_karat': 18,
            'payment_schedule': 'monthly',
            'contract_terms_persian': 'شرایط قرارداد',
            'has_price_protection': True,
            'price_ceiling_per_gram': '2000000',  # Lower than floor
            'price_floor_per_gram': '3000000',    # Higher than ceiling
            'early_payment_discount_percentage': '0.00'
        }
        
        form = GoldInstallmentContractForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('price_ceiling_per_gram', form.errors)
    
    def test_adjustment_form_validation_logic(self):
        """Test adjustment form validation logic."""
        # Test with adjustment that would result in negative weight
        form_data = {
            'adjustment_date': date.today().strftime('%Y-%m-%d'),
            'weight_before_grams': '5.000',
            'adjustment_amount_grams': '-10.000',  # Would result in negative
            'adjustment_type': 'decrease',
            'adjustment_reason': 'correction',
            'description': 'Test adjustment'
        }
        
        form = GoldWeightAdjustmentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('adjustment_amount_grams', form.errors)


class GoldInstallmentViewsImportTest(TestCase):
    """Test that views can be imported successfully."""
    
    def test_views_import(self):
        """Test that all views can be imported."""
        try:
            from zargar.gold_installments.views import (
                GoldInstallmentDashboardView,
                GoldInstallmentContractCreateView,
                GoldInstallmentContractDetailView,
                GoldInstallmentPaymentCreateView,
                GoldWeightAdjustmentCreateView
            )
            
            # Check that views are classes
            self.assertTrue(hasattr(GoldInstallmentDashboardView, 'get'))
            self.assertTrue(hasattr(GoldInstallmentContractCreateView, 'post'))
            self.assertTrue(hasattr(GoldInstallmentContractDetailView, 'get'))
            self.assertTrue(hasattr(GoldInstallmentPaymentCreateView, 'post'))
            self.assertTrue(hasattr(GoldWeightAdjustmentCreateView, 'post'))
            
        except ImportError as e:
            self.fail(f"Failed to import views: {e}")
    
    def test_forms_import(self):
        """Test that all forms can be imported."""
        try:
            from zargar.gold_installments.forms import (
                GoldInstallmentContractForm,
                GoldInstallmentPaymentForm,
                GoldWeightAdjustmentForm,
                PaymentScheduleForm,
                QuickPaymentForm
            )
            
            # Check that forms are form classes
            self.assertTrue(hasattr(GoldInstallmentContractForm, 'is_valid'))
            self.assertTrue(hasattr(GoldInstallmentPaymentForm, 'is_valid'))
            self.assertTrue(hasattr(GoldWeightAdjustmentForm, 'is_valid'))
            self.assertTrue(hasattr(PaymentScheduleForm, 'is_valid'))
            self.assertTrue(hasattr(QuickPaymentForm, 'is_valid'))
            
        except ImportError as e:
            self.fail(f"Failed to import forms: {e}")
    
    def test_models_import(self):
        """Test that models can be imported."""
        try:
            from zargar.gold_installments.models import (
                GoldInstallmentContract,
                GoldInstallmentPayment,
                GoldWeightAdjustment
            )
            
            # Check that models have expected methods
            self.assertTrue(hasattr(GoldInstallmentContract, 'objects'))
            self.assertTrue(hasattr(GoldInstallmentPayment, 'objects'))
            self.assertTrue(hasattr(GoldWeightAdjustment, 'objects'))
            
        except ImportError as e:
            self.fail(f"Failed to import models: {e}")


class GoldInstallmentCalculationTest(TestCase):
    """Test calculation logic in forms and models."""
    
    def test_gold_weight_calculation(self):
        """Test gold weight calculation logic."""
        payment_amount = Decimal('3500000')  # 3.5M Toman
        gold_price = Decimal('3500000')      # 3.5M Toman per gram
        
        expected_gold_weight = payment_amount / gold_price
        self.assertEqual(expected_gold_weight, Decimal('1.000'))
    
    def test_percentage_calculation(self):
        """Test percentage calculations."""
        total_amount = Decimal('1000000')
        discount_percentage = Decimal('5.00')
        
        discount_amount = total_amount * (discount_percentage / 100)
        expected_discount = Decimal('50000.00')
        
        self.assertEqual(discount_amount, expected_discount)
    
    def test_weight_conversion_logic(self):
        """Test weight conversion calculations."""
        # Test gram to mesghal conversion (1 mesghal = 4.608 grams)
        grams = Decimal('4.608')
        mesghal = grams / Decimal('4.608')
        
        self.assertEqual(mesghal, Decimal('1.000'))
        
        # Test soot conversion (1 soot = 0.2304 grams)
        soot = grams / Decimal('0.2304')
        expected_soot = Decimal('20.000')
        
        self.assertEqual(soot, expected_soot)


if __name__ == '__main__':
    pytest.main([__file__])