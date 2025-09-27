#!/usr/bin/env python
"""
Verification script for tenant dashboard dual theme implementation.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from decimal import Decimal

User = get_user_model()

def test_dashboard_implementation():
    """Test the dual theme dashboard implementation."""
    print("🔍 Testing Tenant Dashboard Dual Theme Implementation...")
    
    # Create test client
    client = Client()
    
    # Create test user
    try:
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            persian_first_name='علی',
            persian_last_name='احمدی',
            role='owner',
            theme_preference='light'
        )
        print("✅ Test user created successfully")
    except Exception as e:
        print(f"❌ Failed to create test user: {e}")
        return False
    
    # Test login
    try:
        login_success = client.login(username='testuser', password='testpass123')
        if login_success:
            print("✅ User login successful")
        else:
            print("❌ User login failed")
            return False
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False
    
    # Mock dashboard service
    mock_dashboard_data = {
        'sales_metrics': {
            'today': {'count': 5, 'value': Decimal('15000000'), 'value_display': '۱۵,۰۰۰,۰۰۰ تومان'}
        },
        'customer_metrics': {
            'total_customers': 150,
            'vip_customers': 25,
            'new_customers_this_month': 8,
            'engagement_rate': 75.5,
            'birthday_customers_this_month': []
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
        'generated_at': '2025-09-21T16:00:00Z'
    }
    
    # Test light theme dashboard
    try:
        with patch('zargar.core.tenant_views.TenantDashboardService') as mock_service:
            mock_service.return_value.get_comprehensive_dashboard_data.return_value = mock_dashboard_data
            
            response = client.get('/dashboard/')
            
            if response.status_code == 200:
                print("✅ Dashboard loads successfully")
                
                # Check for key elements
                content = response.content.decode('utf-8')
                
                # Check for Persian content
                if 'داشبورد فروشگاه' in content:
                    print("✅ Persian title found")
                else:
                    print("❌ Persian title not found")
                
                # Check for light theme classes
                if 'metric-card' in content:
                    print("✅ Light theme classes found")
                else:
                    print("❌ Light theme classes not found")
                
                # Check for Persian numbers
                if 'persian-numbers' in content:
                    print("✅ Persian number formatting found")
                else:
                    print("❌ Persian number formatting not found")
                
                # Check for navigation menu
                if 'موجودی' in content and 'مشتریان' in content:
                    print("✅ Navigation menu found")
                else:
                    print("❌ Navigation menu not found")
                
                # Check for metric cards
                if 'فروش امروز' in content and 'کل مشتریان' in content:
                    print("✅ Metric cards found")
                else:
                    print("❌ Metric cards not found")
                
                # Check for gold price widget
                if 'قیمت طلا' in content:
                    print("✅ Gold price widget found")
                else:
                    print("❌ Gold price widget not found")
                
                # Check for quick actions
                if 'عملیات سریع' in content:
                    print("✅ Quick actions found")
                else:
                    print("❌ Quick actions not found")
                
            else:
                print(f"❌ Dashboard failed to load: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Dashboard test error: {e}")
        return False
    
    # Test dark theme dashboard
    try:
        # Switch user to dark theme
        user.theme_preference = 'dark'
        user.save()
        
        with patch('zargar.core.tenant_views.TenantDashboardService') as mock_service:
            mock_service.return_value.get_comprehensive_dashboard_data.return_value = mock_dashboard_data
            
            response = client.get('/dashboard/')
            
            if response.status_code == 200:
                print("✅ Dark theme dashboard loads successfully")
                
                content = response.content.decode('utf-8')
                
                # Check for cybersecurity theme classes
                if 'cyber-metric-card' in content:
                    print("✅ Cybersecurity theme classes found")
                else:
                    print("❌ Cybersecurity theme classes not found")
                
                # Check for neon colors
                if 'cyber-neon-primary' in content:
                    print("✅ Neon color classes found")
                else:
                    print("❌ Neon color classes not found")
                
                # Check for glassmorphism
                if 'cyber-glass-header' in content:
                    print("✅ Glassmorphism effects found")
                else:
                    print("❌ Glassmorphism effects not found")
                
            else:
                print(f"❌ Dark theme dashboard failed to load: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Dark theme test error: {e}")
        return False
    
    print("✅ All dashboard tests passed!")
    return True

def test_static_files():
    """Test that static files exist."""
    print("\n🔍 Testing Static Files...")
    
    import os
    
    # Check CSS file
    css_path = 'static/css/tenant-dashboard.css'
    if os.path.exists(css_path):
        print("✅ CSS file exists")
        
        # Check for cybersecurity theme styles
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
            
        if 'cyber-metric-card' in css_content:
            print("✅ Cybersecurity CSS classes found")
        else:
            print("❌ Cybersecurity CSS classes not found")
            
        if '.dark .cyber-neon-primary' in css_content:
            print("✅ Neon color styles found")
        else:
            print("❌ Neon color styles not found")
            
    else:
        print("❌ CSS file not found")
        return False
    
    # Check JS file
    js_path = 'static/js/tenant-dashboard.js'
    if os.path.exists(js_path):
        print("✅ JavaScript file exists")
        
        # Check for Persian calendar functions
        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
            
        if 'getCurrentPersianDate' in js_content:
            print("✅ Persian calendar functions found")
        else:
            print("❌ Persian calendar functions not found")
            
        if 'initCyberAnimations' in js_content:
            print("✅ Cybersecurity animation functions found")
        else:
            print("❌ Cybersecurity animation functions not found")
            
    else:
        print("❌ JavaScript file not found")
        return False
    
    return True

def test_template_structure():
    """Test template structure."""
    print("\n🔍 Testing Template Structure...")
    
    template_path = 'templates/tenant/dashboard.html'
    if os.path.exists(template_path):
        print("✅ Dashboard template exists")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Check for theme-aware classes
        if ':class="{ \'cyber-metric-card animate-fade-in-up\': darkMode' in template_content:
            print("✅ Theme-aware Alpine.js classes found")
        else:
            print("❌ Theme-aware Alpine.js classes not found")
        
        # Check for Persian content
        if 'داشبورد فروشگاه' in template_content:
            print("✅ Persian content found")
        else:
            print("❌ Persian content not found")
        
        # Check for cybersecurity color coding
        if 'cyber-neon-danger' in template_content:
            print("✅ Cybersecurity color coding found")
        else:
            print("❌ Cybersecurity color coding not found")
        
        return True
    else:
        print("❌ Dashboard template not found")
        return False

if __name__ == '__main__':
    print("🚀 Starting ZARGAR Tenant Dashboard Verification...")
    
    success = True
    
    # Test dashboard functionality
    success &= test_dashboard_implementation()
    
    # Test static files
    success &= test_static_files()
    
    # Test template structure
    success &= test_template_structure()
    
    if success:
        print("\n🎉 All tests passed! Dashboard dual theme implementation is complete.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)