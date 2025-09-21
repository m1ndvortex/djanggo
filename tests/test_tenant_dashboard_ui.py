"""
Tests for tenant dashboard UI functionality, Persian formatting, and theme switching.
"""
import pytest
import django
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock

# Configure Django settings
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()


class TenantDashboardUITestCase(TestCase):
    """Test cases for tenant dashboard UI functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            persian_first_name='علی',
            persian_last_name='احمدی',
            role='owner',
            theme_preference='light'
        )
        
        # Mock tenant context
        self.tenant_context = {
            'tenant': MagicMock(),
            'name': 'فروشگاه طلای نور',
            'domain_url': 'noor-gold.zargar.com',
            'schema_name': 'noor_gold'
        }
    
    def test_dashboard_loads_successfully(self):
        """Test that dashboard loads without errors."""
        self.client.login(username='testuser', password='testpass123')
        
        with patch('zargar.core.tenant_views.TenantDashboardService') as mock_service:
            # Mock dashboard service
            mock_service.return_value.get_comprehensive_dashboard_data.return_value = {
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
                'generated_at': timezone.now()
            }
            
            response = self.client.get(reverse('tenant:dashboard'))
            
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'داشبورد فروشگاه')
            self.assertContains(response, 'فروشگاه طلای نور')
    
    def test_dashboard_displays_persian_numbers(self):
        """Test that dashboard displays numbers in Persian format."""
        self.client.login(username='testuser', password='testpass123')
        
        with patch('zargar.core.tenant_views.TenantDashboardService') as mock_service:
            mock_service.return_value.get_comprehensive_dashboard_data.return_value = {
                'sales_metrics': {
                    'today': {'count': 5, 'value': Decimal('15000000'), 'value_display': '۱۵,۰۰۰,۰۰۰ تومان'}
                },
                'customer_metrics': {'total_customers': 150},
                'inventory_metrics': {'in_stock': 180},
                'gold_installment_metrics': {'overdue_contracts': {'count': 3}},
                'gold_price_data': {'current_prices': {}},
                'recent_activities': [],
                'generated_at': timezone.now()
            }
            
            response = self.client.get(reverse('tenant:dashboard'))
            
            # Check for Persian numbers in response
            self.assertContains(response, '۱۵,۰۰۰,۰۰۰ تومان')
            self.assertContains(response, 'persian-numbers')
    
    def test_dashboard_light_theme_classes(self):
        """Test that dashboard uses correct CSS classes for light theme."""
        self.client.login(username='testuser', password='testpass123')
        
        with patch('zargar.core.tenant_views.TenantDashboardService') as mock_service:
            mock_service.return_value.get_comprehensive_dashboard_data.return_value = {
                'sales_metrics': {},
                'customer_metrics': {},
                'inventory_metrics': {},
                'gold_installment_metrics': {},
                'gold_price_data': {'current_prices': {}},
                'recent_activities': [],
                'generated_at': timezone.now()
            }
            
            response = self.client.get(reverse('tenant:dashboard'))
            
            # Check for light theme classes
            self.assertContains(response, 'metric-card')
            self.assertContains(response, 'gold-price-card')
            self.assertContains(response, 'bg-white')
            self.assertNotContains(response, 'cyber-metric-card')
    
    def test_dashboard_dark_theme_classes(self):
        """Test that dashboard uses correct CSS classes for dark theme."""
        # Set user to dark theme
        self.user.theme_preference = 'dark'
        self.user.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        with patch('zargar.core.tenant_views.TenantDashboardService') as mock_service:
            mock_service.return_value.get_comprehensive_dashboard_data.return_value = {
                'sales_metrics': {},
                'customer_metrics': {},
                'inventory_metrics': {},
                'gold_installment_metrics': {},
                'gold_price_data': {'current_prices': {}},
                'recent_activities': [],
                'generated_at': timezone.now()
            }
            
            response = self.client.get(reverse('tenant:dashboard'))
            
            # Check for cybersecurity theme classes
            self.assertContains(response, 'cyber-metric-card')
            self.assertContains(response, 'cyber-gold-price-card')
            self.assertContains(response, 'cyber-glass-header')
            self.assertContains(response, 'cyber-neon-primary')
    
    def test_dashboard_metric_cards_display(self):
        """Test that all metric cards are displayed correctly."""
        self.client.login(username='testuser', password='testpass123')
        
        with patch('zargar.core.tenant_views.TenantDashboardService') as mock_service:
            mock_service.return_value.get_comprehensive_dashboard_data.return_value = {
                'sales_metrics': {
                    'today': {'count': 5, 'value': Decimal('15000000'), 'value_display': '۱۵,۰۰۰,۰۰۰ تومان'}
                },
                'customer_metrics': {
                    'total_customers': 150,
                    'new_customers_this_month': 8
                },
                'inventory_metrics': {
                    'in_stock': 180,
                    'total_value': {'amount': Decimal('500000000'), 'display': '۵۰۰,۰۰۰,۰۰۰ تومان'}
                },
                'gold_installment_metrics': {
                    'overdue_contracts': {'count': 3},
                    'outstanding_balance': {'value_display': '۸۷۵,۰۰۰,۰۰۰ تومان'}
                },
                'gold_price_data': {'current_prices': {}},
                'recent_activities': [],
                'generated_at': timezone.now()
            }
            
            response = self.client.get(reverse('tenant:dashboard'))
            
            # Check for metric card content
            self.assertContains(response, 'فروش امروز')
            self.assertContains(response, 'کل مشتریان')
            self.assertContains(response, 'ارزش موجودی')
            self.assertContains(response, 'اقساط معوق')
    
    def test_gold_price_widget_display(self):
        """Test that gold price widget displays correctly."""
        self.client.login(username='testuser', password='testpass123')
        
        with patch('zargar.core.tenant_views.TenantDashboardService') as mock_service:
            mock_service.return_value.get_comprehensive_dashboard_data.return_value = {
                'sales_metrics': {},
                'customer_metrics': {},
                'inventory_metrics': {},
                'gold_installment_metrics': {},
                'gold_price_data': {
                    'current_prices': {
                        '18k': {'price_per_gram': Decimal('3500000'), 'display': '۳,۵۰۰,۰۰۰ تومان'},
                        '21k': {'price_per_gram': Decimal('4083333'), 'display': '۴,۰۸۳,۳۳۳ تومان'},
                        '24k': {'price_per_gram': Decimal('4666666'), 'display': '۴,۶۶۶,۶۶۶ تومان'}
                    }
                },
                'recent_activities': [],
                'generated_at': timezone.now()
            }
            
            response = self.client.get(reverse('tenant:dashboard'))
            
            # Check for gold price content
            self.assertContains(response, 'قیمت طلا (زنده)')
            self.assertContains(response, 'طلای ۱۸ عیار')
            self.assertContains(response, 'طلای ۲۱ عیار')
            self.assertContains(response, 'طلای ۲۴ عیار')
            self.assertContains(response, '۳,۵۰۰,۰۰۰ تومان')
    
    def test_customer_insights_widget(self):
        """Test that customer insights widget displays correctly."""
        self.client.login(username='testuser', password='testpass123')
        
        with patch('zargar.core.tenant_views.TenantDashboardService') as mock_service:
            mock_service.return_value.get_comprehensive_dashboard_data.return_value = {
                'sales_metrics': {},
                'customer_metrics': {
                    'vip_customers': 25,
                    'engagement_rate': 75.5,
                    'birthday_customers_this_month': [
                        {'name': 'احمد رضایی', 'birth_date': '1990-01-15', 'phone_number': '09123456789'}
                    ]
                },
                'inventory_metrics': {},
                'gold_installment_metrics': {},
                'gold_price_data': {'current_prices': {}},
                'recent_activities': [],
                'generated_at': timezone.now()
            }
            
            response = self.client.get(reverse('tenant:dashboard'))
            
            # Check for customer insights content
            self.assertContains(response, 'بینش مشتریان')
            self.assertContains(response, 'مشتریان VIP')
            self.assertContains(response, 'نرخ مشارکت')
            self.assertContains(response, 'تولد این ماه')
    
    def test_installment_summary_widget(self):
        """Test that installment summary widget displays correctly."""
        self.client.login(username='testuser', password='testpass123')
        
        with patch('zargar.core.tenant_views.TenantDashboardService') as mock_service:
            mock_service.return_value.get_comprehensive_dashboard_data.return_value = {
                'sales_metrics': {},
                'customer_metrics': {},
                'inventory_metrics': {},
                'gold_installment_metrics': {
                    'contract_counts': {'active': 12, 'completed': 45, 'defaulted': 2},
                    'outstanding_balance': {
                        'gold_weight_grams': Decimal('250.5'),
                        'gold_weight_display': '۲۵۰.۵ گرم'
                    },
                    'overdue_contracts': {'count': 3}
                },
                'gold_price_data': {'current_prices': {}},
                'recent_activities': [],
                'generated_at': timezone.now()
            }
            
            response = self.client.get(reverse('tenant:dashboard'))
            
            # Check for installment summary content
            self.assertContains(response, 'خلاصه اقساط')
            self.assertContains(response, 'قراردادهای فعال')
            self.assertContains(response, 'مانده طلا')
            self.assertContains(response, '۲۵۰.۵ گرم')
    
    def test_quick_actions_display(self):
        """Test that quick actions are displayed correctly."""
        self.client.login(username='testuser', password='testpass123')
        
        with patch('zargar.core.tenant_views.TenantDashboardService') as mock_service:
            mock_service.return_value.get_comprehensive_dashboard_data.return_value = {
                'sales_metrics': {},
                'customer_metrics': {},
                'inventory_metrics': {},
                'gold_installment_metrics': {},
                'gold_price_data': {'current_prices': {}},
                'recent_activities': [],
                'generated_at': timezone.now()
            }
            
            response = self.client.get(reverse('tenant:dashboard'))
            
            # Check for quick actions
            self.assertContains(response, 'عملیات سریع')
            self.assertContains(response, 'افزودن کالا')
            self.assertContains(response, 'مشتری جدید')
            self.assertContains(response, 'قرارداد قسطی')
            self.assertContains(response, 'گزارشات')
    
    def test_navigation_menu_display(self):
        """Test that navigation menu displays correctly."""
        self.client.login(username='testuser', password='testpass123')
        
        with patch('zargar.core.tenant_views.TenantDashboardService') as mock_service:
            mock_service.return_value.get_comprehensive_dashboard_data.return_value = {
                'sales_metrics': {},
                'customer_metrics': {},
                'inventory_metrics': {},
                'gold_installment_metrics': {},
                'gold_price_data': {'current_prices': {}},
                'recent_activities': [],
                'generated_at': timezone.now()
            }
            
            response = self.client.get(reverse('tenant:dashboard'))
            
            # Check for navigation menu
            self.assertContains(response, 'داشبورد')
            self.assertContains(response, 'موجودی')
            self.assertContains(response, 'مشتریان')
            self.assertContains(response, 'اقساط طلا')
            self.assertContains(response, 'گزارشات')
    
    def test_user_info_display(self):
        """Test that user information displays correctly."""
        self.client.login(username='testuser', password='testpass123')
        
        with patch('zargar.core.tenant_views.TenantDashboardService') as mock_service:
            mock_service.return_value.get_comprehensive_dashboard_data.return_value = {
                'sales_metrics': {},
                'customer_metrics': {},
                'inventory_metrics': {},
                'gold_installment_metrics': {},
                'gold_price_data': {'current_prices': {}},
                'recent_activities': [],
                'generated_at': timezone.now()
            }
            
            response = self.client.get(reverse('tenant:dashboard'))
            
            # Check for user info
            self.assertContains(response, 'علی احمدی')
            self.assertContains(response, 'خروج')
    
    def test_responsive_design_classes(self):
        """Test that responsive design classes are present."""
        self.client.login(username='testuser', password='testpass123')
        
        with patch('zargar.core.tenant_views.TenantDashboardService') as mock_service:
            mock_service.return_value.get_comprehensive_dashboard_data.return_value = {
                'sales_metrics': {},
                'customer_metrics': {},
                'inventory_metrics': {},
                'gold_installment_metrics': {},
                'gold_price_data': {'current_prices': {}},
                'recent_activities': [],
                'generated_at': timezone.now()
            }
            
            response = self.client.get(reverse('tenant:dashboard'))
            
            # Check for responsive classes
            self.assertContains(response, 'grid-cols-1')
            self.assertContains(response, 'md:grid-cols-2')
            self.assertContains(response, 'lg:grid-cols-4')
            self.assertContains(response, 'sm:px-6')
            self.assertContains(response, 'lg:px-8')
    
    def test_javascript_includes(self):
        """Test that required JavaScript files are included."""
        self.client.login(username='testuser', password='testpass123')
        
        with patch('zargar.core.tenant_views.TenantDashboardService') as mock_service:
            mock_service.return_value.get_comprehensive_dashboard_data.return_value = {
                'sales_metrics': {},
                'customer_metrics': {},
                'inventory_metrics': {},
                'gold_installment_metrics': {},
                'gold_price_data': {'current_prices': {}},
                'recent_activities': [],
                'generated_at': timezone.now()
            }
            
            response = self.client.get(reverse('tenant:dashboard'))
            
            # Check for JavaScript includes
            self.assertContains(response, 'tenant-dashboard.js')
            self.assertContains(response, 'tenantDashboard()')
            self.assertContains(response, 'goldPriceWidget()')
    
    def test_css_includes(self):
        """Test that required CSS files are included."""
        self.client.login(username='testuser', password='testpass123')
        
        with patch('zargar.core.tenant_views.TenantDashboardService') as mock_service:
            mock_service.return_value.get_comprehensive_dashboard_data.return_value = {
                'sales_metrics': {},
                'customer_metrics': {},
                'inventory_metrics': {},
                'gold_installment_metrics': {},
                'gold_price_data': {'current_prices': {}},
                'recent_activities': [],
                'generated_at': timezone.now()
            }
            
            response = self.client.get(reverse('tenant:dashboard'))
            
            # Check for CSS includes
            self.assertContains(response, 'tenant-dashboard.css')


class TenantDashboardThemeTestCase(TestCase):
    """Test cases for theme switching functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='themeuser',
            email='theme@example.com',
            password='testpass123',
            persian_first_name='سارا',
            persian_last_name='محمدی',
            role='owner',
            theme_preference='light'
        )
    
    def test_theme_toggle_endpoint(self):
        """Test theme toggle endpoint functionality."""
        self.client.login(username='themeuser', password='testpass123')
        
        # Test switching to dark theme
        response = self.client.post(
            reverse('tenant:theme_toggle'),
            data='{"theme": "dark"}',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['theme'], 'dark')
        
        # Verify user preference was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.theme_preference, 'dark')
    
    def test_invalid_theme_toggle(self):
        """Test theme toggle with invalid theme."""
        self.client.login(username='themeuser', password='testpass123')
        
        response = self.client.post(
            reverse('tenant:theme_toggle'),
            data='{"theme": "invalid"}',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_theme_persistence(self):
        """Test that theme preference persists across sessions."""
        # Set user to dark theme
        self.user.theme_preference = 'dark'
        self.user.save()
        
        self.client.login(username='themeuser', password='testpass123')
        
        with patch('zargar.core.tenant_views.TenantDashboardService') as mock_service:
            mock_service.return_value.get_comprehensive_dashboard_data.return_value = {
                'sales_metrics': {},
                'customer_metrics': {},
                'inventory_metrics': {},
                'gold_installment_metrics': {},
                'gold_price_data': {'current_prices': {}},
                'recent_activities': [],
                'generated_at': timezone.now()
            }
            
            response = self.client.get(reverse('tenant:dashboard'))
            
            # Check that dark theme is applied
            self.assertContains(response, 'cyber-metric-card')
            self.assertContains(response, 'dark')


if __name__ == '__main__':
    pytest.main([__file__])