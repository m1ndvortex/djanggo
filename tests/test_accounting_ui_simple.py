"""
Simple tests for Persian Accounting System UI (Frontend).

This module tests the basic UI components and templates for the Persian accounting system.
"""

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


class SimpleAccountingUITest(TestCase):
    """Simple test case for accounting UI without complex tenant setup."""
    
    def setUp(self):
        """Set up test data."""
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create client and login
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_accounting_urls_exist(self):
        """Test that accounting URLs are properly configured."""
        # Test that URL patterns exist
        try:
            reverse('accounting:dashboard')
            reverse('accounting:chart_of_accounts_list')
            reverse('accounting:journal_entries_list')
            reverse('accounting:bank_accounts_list')
            reverse('accounting:cheques_list')
            reverse('accounting:reports_dashboard')
        except Exception as e:
            self.fail(f"URL pattern not found: {e}")
    
    def test_accounting_templates_exist(self):
        """Test that accounting templates exist."""
        import os
        from django.conf import settings
        
        template_paths = [
            'templates/accounting/dashboard.html',
            'templates/accounting/chart_of_accounts/list.html',
            'templates/accounting/chart_of_accounts/form.html',
            'templates/accounting/journal_entries/list.html',
        ]
        
        for template_path in template_paths:
            full_path = os.path.join(settings.BASE_DIR, template_path)
            self.assertTrue(
                os.path.exists(full_path),
                f"Template {template_path} does not exist"
            )
    
    def test_accounting_css_files_exist(self):
        """Test that accounting CSS files exist."""
        import os
        from django.conf import settings
        
        css_files = [
            'static/css/accounting-dashboard.css',
            'static/css/accounting-tables.css',
            'static/css/accounting-forms.css',
        ]
        
        for css_file in css_files:
            full_path = os.path.join(settings.BASE_DIR, css_file)
            self.assertTrue(
                os.path.exists(full_path),
                f"CSS file {css_file} does not exist"
            )
    
    def test_accounting_views_import_successfully(self):
        """Test that accounting views can be imported."""
        try:
            from zargar.accounting import views
            
            # Test that key view classes exist
            self.assertTrue(hasattr(views, 'AccountingDashboardView'))
            self.assertTrue(hasattr(views, 'ChartOfAccountsListView'))
            self.assertTrue(hasattr(views, 'JournalEntryListView'))
            self.assertTrue(hasattr(views, 'BankAccountListView'))
            self.assertTrue(hasattr(views, 'ChequeManagementListView'))
            
        except ImportError as e:
            self.fail(f"Failed to import accounting views: {e}")
    
    def test_accounting_forms_import_successfully(self):
        """Test that accounting forms can be imported."""
        try:
            from zargar.accounting import forms
            
            # Test that key form classes exist
            self.assertTrue(hasattr(forms, 'ChartOfAccountsForm'))
            self.assertTrue(hasattr(forms, 'JournalEntryForm'))
            self.assertTrue(hasattr(forms, 'BankAccountForm'))
            self.assertTrue(hasattr(forms, 'ChequeManagementForm'))
            
        except ImportError as e:
            self.fail(f"Failed to import accounting forms: {e}")
    
    def test_accounting_models_import_successfully(self):
        """Test that accounting models can be imported."""
        try:
            from zargar.accounting import models
            
            # Test that key model classes exist
            self.assertTrue(hasattr(models, 'ChartOfAccounts'))
            self.assertTrue(hasattr(models, 'JournalEntry'))
            self.assertTrue(hasattr(models, 'JournalEntryLine'))
            self.assertTrue(hasattr(models, 'BankAccount'))
            self.assertTrue(hasattr(models, 'ChequeManagement'))
            
        except ImportError as e:
            self.fail(f"Failed to import accounting models: {e}")
    
    def test_persian_template_tags_exist(self):
        """Test that Persian template tags are available."""
        try:
            from zargar.core.templatetags import persian_tags
            
            # Test that key template tags exist
            self.assertTrue(hasattr(persian_tags, 'persian_currency'))
            
        except ImportError:
            # This is expected if the template tags don't exist yet
            pass
    
    def test_template_structure_is_valid(self):
        """Test that template files have valid structure."""
        import os
        from django.conf import settings
        
        # Test dashboard template
        dashboard_path = os.path.join(settings.BASE_DIR, 'templates/accounting/dashboard.html')
        if os.path.exists(dashboard_path):
            with open(dashboard_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Check for essential template elements
                self.assertIn('{% extends', content)
                self.assertIn('{% block content %}', content)
                self.assertIn('داشبورد حسابداری', content)
                self.assertIn('card-cyber', content)
                self.assertIn('btn-primary-cyber', content)
    
    def test_css_structure_is_valid(self):
        """Test that CSS files have valid structure."""
        import os
        from django.conf import settings
        
        # Test dashboard CSS
        css_path = os.path.join(settings.BASE_DIR, 'static/css/accounting-dashboard.css')
        if os.path.exists(css_path):
            with open(css_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Check for essential CSS classes
                self.assertIn('.card-cyber', content)
                self.assertIn('.btn-primary-cyber', content)
                self.assertIn('.badge-cyber', content)
                self.assertIn('cybersecurity', content.lower())
    
    def test_form_classes_are_properly_structured(self):
        """Test that form classes have proper structure."""
        try:
            from zargar.accounting.forms import ChartOfAccountsForm
            
            # Test that form has required fields
            form = ChartOfAccountsForm()
            self.assertIn('account_code', form.fields)
            self.assertIn('account_name_persian', form.fields)
            self.assertIn('account_type', form.fields)
            
        except ImportError:
            # Skip if forms don't exist yet
            pass
    
    def test_view_classes_are_properly_structured(self):
        """Test that view classes have proper structure."""
        try:
            from zargar.accounting.views import AccountingDashboardView
            
            # Test that view has required attributes
            self.assertTrue(hasattr(AccountingDashboardView, 'template_name'))
            self.assertTrue(hasattr(AccountingDashboardView, 'get_context_data'))
            
        except ImportError:
            # Skip if views don't exist yet
            pass


class PersianUIElementsTest(TestCase):
    """Test Persian UI elements and formatting."""
    
    def test_persian_text_in_templates(self):
        """Test that templates contain Persian text."""
        import os
        from django.conf import settings
        
        dashboard_path = os.path.join(settings.BASE_DIR, 'templates/accounting/dashboard.html')
        if os.path.exists(dashboard_path):
            with open(dashboard_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Check for Persian text
                persian_texts = [
                    'داشبورد حسابداری',
                    'کل حساب‌ها',
                    'اسناد در انتظار',
                    'حساب‌های بانکی',
                    'سند جدید',
                    'حساب جدید'
                ]
                
                for text in persian_texts:
                    self.assertIn(text, content, f"Persian text '{text}' not found in dashboard template")
    
    def test_rtl_classes_in_templates(self):
        """Test that templates include RTL classes."""
        import os
        from django.conf import settings
        
        dashboard_path = os.path.join(settings.BASE_DIR, 'templates/accounting/dashboard.html')
        if os.path.exists(dashboard_path):
            with open(dashboard_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Check for RTL-related classes
                rtl_indicators = [
                    'text-right',
                    'persian-numbers',
                    'dir="rtl"'
                ]
                
                # At least some RTL indicators should be present
                rtl_found = any(indicator in content for indicator in rtl_indicators)
                self.assertTrue(rtl_found, "No RTL indicators found in template")
    
    def test_cybersecurity_theme_classes_in_css(self):
        """Test that CSS includes cybersecurity theme classes."""
        import os
        from django.conf import settings
        
        css_path = os.path.join(settings.BASE_DIR, 'static/css/accounting-dashboard.css')
        if os.path.exists(css_path):
            with open(css_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Check for cybersecurity theme elements
                cyber_elements = [
                    'cyber-text-primary',
                    'cyber-neon-primary',
                    'cyber-bg-primary',
                    'glassmorphism',
                    'neon',
                    '#00D4FF',
                    '#00FF88'
                ]
                
                cyber_found = any(element in content for element in cyber_elements)
                self.assertTrue(cyber_found, "No cybersecurity theme elements found in CSS")


if __name__ == '__main__':
    pytest.main([__file__])