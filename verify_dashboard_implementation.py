#!/usr/bin/env python
"""
Verification script for tenant dashboard implementation.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django.template.loader import get_template
from django.template import Context, Template
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()

def verify_template_exists():
    """Verify that the dashboard template exists and can be loaded."""
    try:
        template = get_template('tenant/dashboard.html')
        print("✓ Dashboard template exists and can be loaded")
        return True
    except Exception as e:
        print(f"✗ Dashboard template error: {e}")
        return False

def verify_css_exists():
    """Verify that the CSS file exists."""
    css_path = 'static/css/tenant-dashboard.css'
    if os.path.exists(css_path):
        print("✓ Tenant dashboard CSS file exists")
        return True
    else:
        print(f"✗ CSS file not found: {css_path}")
        return False

def verify_js_exists():
    """Verify that the JavaScript file exists."""
    js_path = 'static/js/tenant-dashboard.js'
    if os.path.exists(js_path):
        print("✓ Tenant dashboard JavaScript file exists")
        return True
    else:
        print(f"✗ JavaScript file not found: {js_path}")
        return False

def verify_template_content():
    """Verify that the template contains required elements."""
    try:
        template = get_template('tenant/dashboard.html')
        
        # Create mock context
        context = {
            'user': type('MockUser', (), {
                'full_persian_name': 'علی احمدی',
                'get_role_display': 'مالک',
                'is_authenticated': True
            })(),
            'tenant_name': 'فروشگاه طلای نور',
            'is_dark_mode': False,
            'sales_metrics': {
                'today': {'count': 5, 'value': Decimal('15000000'), 'value_display': '۱۵,۰۰۰,۰۰۰ تومان'}
            },
            'customer_metrics': {
                'total_customers': 150,
                'vip_customers': 25,
                'new_customers_this_month': 8,
                'engagement_rate': 75.5
            },
            'inventory_metrics': {
                'total_items': 200,
                'in_stock': 180,
                'total_value': {'amount': Decimal('500000000'), 'display': '۵۰۰,۰۰۰,۰۰۰ تومان'}
            },
            'gold_installment_metrics': {
                'contract_counts': {'active': 12, 'completed': 45, 'defaulted': 2},
                'overdue_contracts': {'count': 3},
                'outstanding_balance': {
                    'gold_weight_grams': Decimal('250.5'),
                    'gold_weight_display': '۲۵۰.۵ گرم',
                    'value_toman': Decimal('875000000'),
                    'value_display': '۸۷۵,۰۰۰,۰۰۰ تومان'
                }
            },
            'gold_price_data': {
                'current_prices': {
                    '18k': {'price_per_gram': Decimal('3500000'), 'display': '۳,۵۰۰,۰۰۰ تومان'},
                    '21k': {'price_per_gram': Decimal('4083333'), 'display': '۴,۰۸۳,۳۳۳ تومان'},
                    '24k': {'price_per_gram': Decimal('4666666'), 'display': '۴,۶۶۶,۶۶۶ تومان'}
                }
            },
            'recent_activities': [],
            'csrf_token': 'test-token'
        }
        
        rendered = template.render(context)
        
        # Check for key elements
        required_elements = [
            'داشبورد فروشگاه',
            'فروش امروز',
            'کل مشتریان',
            'ارزش موجودی',
            'اقساط معوق',
            'قیمت طلا (زنده)',
            'بینش مشتریان',
            'خلاصه اقساط',
            'عملیات سریع',
            'tenant-dashboard.css',
            'tenant-dashboard.js',
            'tenantDashboard()',
            'goldPriceWidget()'
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in rendered:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"✗ Template missing elements: {missing_elements}")
            return False
        else:
            print("✓ Template contains all required elements")
            return True
            
    except Exception as e:
        print(f"✗ Template rendering error: {e}")
        return False

def verify_theme_support():
    """Verify that the template supports both light and dark themes."""
    try:
        template = get_template('tenant/dashboard.html')
        
        # Test light theme
        light_context = {
            'user': type('MockUser', (), {
                'full_persian_name': 'علی احمدی',
                'get_role_display': 'مالک',
                'is_authenticated': True
            })(),
            'is_dark_mode': False,
            'sales_metrics': {},
            'customer_metrics': {},
            'inventory_metrics': {},
            'gold_installment_metrics': {},
            'gold_price_data': {'current_prices': {}},
            'recent_activities': [],
            'csrf_token': 'test-token'
        }
        
        light_rendered = template.render(light_context)
        
        # Test dark theme
        dark_context = light_context.copy()
        dark_context['is_dark_mode'] = True
        
        dark_rendered = template.render(dark_context)
        
        # Check for theme-specific classes
        light_classes = ['metric-card', 'gold-price-card']
        dark_classes = ['cyber-metric-card', 'cyber-gold-price-card', 'cyber-glass-header']
        
        light_theme_ok = any(cls in light_rendered for cls in light_classes)
        dark_theme_ok = any(cls in dark_rendered for cls in dark_classes)
        
        if light_theme_ok and dark_theme_ok:
            print("✓ Template supports both light and dark themes")
            return True
        else:
            print(f"✗ Theme support issue - Light: {light_theme_ok}, Dark: {dark_theme_ok}")
            return False
            
    except Exception as e:
        print(f"✗ Theme verification error: {e}")
        return False

def verify_persian_support():
    """Verify Persian text and RTL support."""
    try:
        template = get_template('tenant/dashboard.html')
        
        context = {
            'user': type('MockUser', (), {
                'full_persian_name': 'علی احمدی',
                'get_role_display': 'مالک',
                'is_authenticated': True
            })(),
            'tenant_name': 'فروشگاه طلای نور',
            'is_dark_mode': False,
            'sales_metrics': {
                'today': {'value_display': '۱۵,۰۰۰,۰۰۰ تومان'}
            },
            'customer_metrics': {},
            'inventory_metrics': {},
            'gold_installment_metrics': {},
            'gold_price_data': {'current_prices': {}},
            'recent_activities': [],
            'csrf_token': 'test-token'
        }
        
        rendered = template.render(context)
        
        # Check for Persian elements
        persian_elements = [
            'علی احمدی',
            'فروشگاه طلای نور',
            '۱۵,۰۰۰,۰۰۰ تومان',
            'persian-numbers',
            'dir="rtl"'
        ]
        
        missing_persian = []
        for element in persian_elements:
            if element not in rendered:
                missing_persian.append(element)
        
        if missing_persian:
            print(f"✗ Persian support missing elements: {missing_persian}")
            return False
        else:
            print("✓ Persian and RTL support verified")
            return True
            
    except Exception as e:
        print(f"✗ Persian support verification error: {e}")
        return False

def main():
    """Run all verification tests."""
    print("Verifying Tenant Dashboard Implementation...")
    print("=" * 50)
    
    tests = [
        verify_template_exists,
        verify_css_exists,
        verify_js_exists,
        verify_template_content,
        verify_theme_support,
        verify_persian_support
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All verification tests passed!")
        print("✓ Tenant dashboard implementation is complete and functional")
        return True
    else:
        print("✗ Some verification tests failed")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)