"""
Dashboard services for tenant portal.
Provides comprehensive business metrics and analytics for jewelry shop owners.
"""
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta, date
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q, F
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class TenantDashboardService:
    """
    Service for generating tenant dashboard metrics and insights.
    Provides real-time business analytics for jewelry shop management.
    """
    
    CACHE_TIMEOUT = 300  # 5 minutes
    
    def __init__(self, tenant_schema: str):
        """
        Initialize dashboard service for specific tenant.
        
        Args:
            tenant_schema: Tenant schema name for data isolation
        """
        self.tenant_schema = tenant_schema
        
        # Lazy import formatters to avoid app registry issues
        try:
            from .persian_number_formatter import PersianNumberFormatter
            from .calendar_utils import PersianCalendarUtils
            self.formatter = PersianNumberFormatter()
            self.calendar_utils = PersianCalendarUtils()
        except ImportError:
            # Fallback if formatters are not available
            self.formatter = None
            self.calendar_utils = None
    
    def get_comprehensive_dashboard_data(self) -> Dict:
        """
        Get comprehensive dashboard data including all key metrics.
        
        Returns:
            Dictionary with complete dashboard data
        """
        cache_key = f"dashboard_data_{self.tenant_schema}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.info(f"Retrieved cached dashboard data for tenant: {self.tenant_schema}")
            return cached_data
        
        try:
            # Gather all dashboard components
            dashboard_data = {
                'sales_metrics': self.get_sales_metrics(),
                'inventory_metrics': self.get_inventory_metrics(),
                'customer_metrics': self.get_customer_metrics(),
                'gold_installment_metrics': self.get_gold_installment_metrics(),
                'gold_price_data': self.get_gold_price_data(),
                'financial_summary': self.get_financial_summary(),
                'recent_activities': self.get_recent_activities(),
                'alerts_and_notifications': self.get_alerts_and_notifications(),
                'performance_trends': self.get_performance_trends(),
                'generated_at': timezone.now(),
                'tenant_schema': self.tenant_schema
            }
            
            # Cache the results
            cache.set(cache_key, dashboard_data, self.CACHE_TIMEOUT)
            logger.info(f"Generated and cached dashboard data for tenant: {self.tenant_schema}")
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error generating dashboard data for tenant {self.tenant_schema}: {e}")
            return self._get_fallback_dashboard_data()
    
    def get_sales_metrics(self) -> Dict:
        """
        Get sales-related metrics and KPIs.
        
        Returns:
            Dictionary with sales metrics
        """
        try:
            # Import here to avoid circular imports and app registry issues
            from django.apps import apps
            
            # Check if apps are ready
            if not apps.ready:
                return self._get_fallback_sales_metrics()
            
            try:
                JewelryItem = apps.get_model('jewelry', 'JewelryItem')
            except LookupError:
                # Model doesn't exist, return fallback
                return self._get_fallback_sales_metrics()
            
            today = timezone.now().date()
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)
            
            # Get sold items (mock data for now since we don't have sales model yet)
            sold_items_today = JewelryItem.objects.filter(
                status='sold',
                updated_at__date=today
            )
            
            sold_items_week = JewelryItem.objects.filter(
                status='sold',
                updated_at__date__gte=week_start
            )
            
            sold_items_month = JewelryItem.objects.filter(
                status='sold',
                updated_at__date__gte=month_start
            )
            
            # Calculate sales values (using selling_price or total_value)
            today_sales_value = sum(
                item.selling_price or item.total_value or Decimal('0')
                for item in sold_items_today
            )
            
            week_sales_value = sum(
                item.selling_price or item.total_value or Decimal('0')
                for item in sold_items_week
            )
            
            month_sales_value = sum(
                item.selling_price or item.total_value or Decimal('0')
                for item in sold_items_month
            )
            
            # Calculate averages
            avg_sale_value = (
                week_sales_value / sold_items_week.count() 
                if sold_items_week.count() > 0 else Decimal('0')
            )
            
            return {
                'today': {
                    'count': sold_items_today.count(),
                    'value': today_sales_value,
                    'value_display': self._format_currency(today_sales_value)
                },
                'this_week': {
                    'count': sold_items_week.count(),
                    'value': week_sales_value,
                    'value_display': self._format_currency(week_sales_value)
                },
                'this_month': {
                    'count': sold_items_month.count(),
                    'value': month_sales_value,
                    'value_display': self._format_currency(month_sales_value)
                },
                'average_sale_value': {
                    'value': avg_sale_value,
                    'value_display': self._format_currency(avg_sale_value)
                },
                'top_selling_categories': self._get_top_selling_categories(),
                'sales_trend': self._get_sales_trend()
            }
            
        except Exception as e:
            logger.error(f"Error getting sales metrics: {e}")
            return self._get_fallback_sales_metrics()
    
    def get_inventory_metrics(self) -> Dict:
        """
        Get inventory-related metrics and insights.
        
        Returns:
            Dictionary with inventory metrics
        """
        try:
            from django.apps import apps
            
            if not apps.ready:
                return self._get_fallback_inventory_metrics()
            
            try:
                JewelryItem = apps.get_model('jewelry', 'JewelryItem')
                Category = apps.get_model('jewelry', 'Category')
            except LookupError:
                return self._get_fallback_inventory_metrics()
            
            # Total inventory counts
            total_items = JewelryItem.objects.count()
            in_stock_items = JewelryItem.objects.filter(status='in_stock').count()
            sold_items = JewelryItem.objects.filter(status='sold').count()
            reserved_items = JewelryItem.objects.filter(status='reserved').count()
            
            # Low stock items
            low_stock_items = JewelryItem.objects.filter(
                status='in_stock',
                quantity__lte=F('minimum_stock')
            )
            
            # Inventory value calculations
            total_inventory_value = JewelryItem.objects.filter(
                status='in_stock'
            ).aggregate(
                total_gold_value=Sum('gold_value'),
                total_manufacturing_cost=Sum('manufacturing_cost'),
                total_gemstone_value=Sum('gemstone_value')
            )
            
            total_value = (
                (total_inventory_value['total_gold_value'] or Decimal('0')) +
                (total_inventory_value['total_manufacturing_cost'] or Decimal('0')) +
                (total_inventory_value['total_gemstone_value'] or Decimal('0'))
            )
            
            # Category distribution
            category_distribution = Category.objects.annotate(
                item_count=Count('jewelryitem')
            ).order_by('-item_count')[:5]
            
            return {
                'total_items': total_items,
                'in_stock': in_stock_items,
                'sold': sold_items,
                'reserved': reserved_items,
                'low_stock_count': low_stock_items.count(),
                'low_stock_items': [
                    {
                        'name': item.name,
                        'sku': item.sku,
                        'current_quantity': item.quantity,
                        'minimum_stock': item.minimum_stock
                    }
                    for item in low_stock_items[:10]  # Top 10 low stock items
                ],
                'total_value': {
                    'amount': total_value,
                    'display': self._format_currency(total_value)
                },
                'value_breakdown': {
                    'gold_value': {
                        'amount': total_inventory_value['total_gold_value'] or Decimal('0'),
                        'display': self._format_currency(total_inventory_value['total_gold_value'] or Decimal('0'))
                    },
                    'manufacturing_cost': {
                        'amount': total_inventory_value['total_manufacturing_cost'] or Decimal('0'),
                        'display': self._format_currency(total_inventory_value['total_manufacturing_cost'] or Decimal('0'))
                    },
                    'gemstone_value': {
                        'amount': total_inventory_value['total_gemstone_value'] or Decimal('0'),
                        'display': self._format_currency(total_inventory_value['total_gemstone_value'] or Decimal('0'))
                    }
                },
                'category_distribution': [
                    {
                        'name': cat.name_persian or cat.name,
                        'count': cat.item_count,
                        'percentage': (cat.item_count / total_items * 100) if total_items > 0 else 0
                    }
                    for cat in category_distribution
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting inventory metrics: {e}")
            return self._get_fallback_inventory_metrics()
    
    def get_customer_metrics(self) -> Dict:
        """
        Get customer-related metrics and insights.
        
        Returns:
            Dictionary with customer metrics
        """
        try:
            from django.apps import apps
            
            if not apps.ready:
                return self._get_fallback_customer_metrics()
            
            try:
                Customer = apps.get_model('customers', 'Customer')
                CustomerLoyaltyTransaction = apps.get_model('customers', 'CustomerLoyaltyTransaction')
            except LookupError:
                return self._get_fallback_customer_metrics()
            
            # Basic customer counts
            total_customers = Customer.objects.filter(is_active=True).count()
            vip_customers = Customer.objects.filter(is_vip=True, is_active=True).count()
            new_customers_month = Customer.objects.filter(
                created_at__gte=timezone.now().replace(day=1),
                is_active=True
            ).count()
            
            # Customer engagement metrics
            customers_with_purchases = Customer.objects.filter(
                total_purchases__gt=0,
                is_active=True
            ).count()
            
            # Top customers by purchase value
            top_customers = Customer.objects.filter(
                is_active=True,
                total_purchases__gt=0
            ).order_by('-total_purchases')[:10]
            
            # Loyalty points summary
            total_loyalty_points = Customer.objects.filter(
                is_active=True
            ).aggregate(total_points=Sum('loyalty_points'))['total_points'] or 0
            
            # Recent loyalty transactions
            recent_loyalty_transactions = CustomerLoyaltyTransaction.objects.select_related(
                'customer'
            ).order_by('-created_at')[:10]
            
            # Birthday customers this month
            current_month = timezone.now().month
            birthday_customers = Customer.objects.filter(
                birth_date__month=current_month,
                is_active=True
            )
            
            return {
                'total_customers': total_customers,
                'vip_customers': vip_customers,
                'new_customers_this_month': new_customers_month,
                'customers_with_purchases': customers_with_purchases,
                'engagement_rate': (
                    (customers_with_purchases / total_customers * 100) 
                    if total_customers > 0 else 0
                ),
                'total_loyalty_points': {
                    'amount': total_loyalty_points,
                    'display': self._format_number(total_loyalty_points)
                },
                'top_customers': [
                    {
                        'name': customer.full_persian_name,
                        'total_purchases': {
                            'amount': customer.total_purchases,
                            'display': self._format_currency(customer.total_purchases)
                        },
                        'loyalty_points': customer.loyalty_points,
                        'is_vip': customer.is_vip
                    }
                    for customer in top_customers
                ],
                'birthday_customers_this_month': [
                    {
                        'name': customer.full_persian_name,
                        'birth_date': customer.birth_date,
                        'phone_number': customer.phone_number
                    }
                    for customer in birthday_customers
                ],
                'recent_loyalty_activity': [
                    {
                        'customer_name': transaction.customer.full_persian_name,
                        'points': transaction.points,
                        'transaction_type': transaction.get_transaction_type_display(),
                        'date': transaction.created_at,
                        'reason': transaction.reason
                    }
                    for transaction in recent_loyalty_transactions
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting customer metrics: {e}")
            return self._get_fallback_customer_metrics()
    
    def get_gold_installment_metrics(self) -> Dict:
        """
        Get gold installment system metrics and insights.
        
        Returns:
            Dictionary with gold installment metrics
        """
        try:
            from django.apps import apps
            
            if not apps.ready:
                return self._get_fallback_gold_installment_metrics()
            
            try:
                GoldInstallmentContract = apps.get_model('gold_installments', 'GoldInstallmentContract')
                GoldInstallmentPayment = apps.get_model('gold_installments', 'GoldInstallmentPayment')
                
                # Try to import gold price service
                try:
                    from zargar.gold_installments.services import GoldPriceService
                    current_gold_price = GoldPriceService.get_current_gold_price(18)['price_per_gram']
                except ImportError:
                    # Fallback gold price
                    current_gold_price = Decimal('3500000')
            except LookupError:
                return self._get_fallback_gold_installment_metrics()
            
            # Contract status counts
            active_contracts = GoldInstallmentContract.objects.filter(status='active').count()
            completed_contracts = GoldInstallmentContract.objects.filter(status='completed').count()
            defaulted_contracts = GoldInstallmentContract.objects.filter(status='defaulted').count()
            
            # Financial metrics
            total_gold_weight_outstanding = GoldInstallmentContract.objects.filter(
                status='active'
            ).aggregate(
                total_weight=Sum('remaining_gold_weight_grams')
            )['total_weight'] or Decimal('0')
            
            outstanding_value = total_gold_weight_outstanding * current_gold_price
            
            # Recent payments
            recent_payments = GoldInstallmentPayment.objects.select_related(
                'contract', 'contract__customer'
            ).order_by('-payment_date')[:10]
            
            # Overdue contracts
            overdue_contracts = []
            for contract in GoldInstallmentContract.objects.filter(status='active'):
                if contract.is_overdue:
                    overdue_contracts.append(contract)
            
            # Payment trends (last 30 days)
            thirty_days_ago = timezone.now().date() - timedelta(days=30)
            recent_payment_stats = GoldInstallmentPayment.objects.filter(
                payment_date__gte=thirty_days_ago
            ).aggregate(
                total_amount=Sum('payment_amount_toman'),
                total_payments=Count('id'),
                avg_payment=Avg('payment_amount_toman')
            )
            
            return {
                'contract_counts': {
                    'active': active_contracts,
                    'completed': completed_contracts,
                    'defaulted': defaulted_contracts,
                    'total': active_contracts + completed_contracts + defaulted_contracts
                },
                'outstanding_balance': {
                    'gold_weight_grams': total_gold_weight_outstanding,
                    'gold_weight_display': self._format_weight(total_gold_weight_outstanding, 'gram'),
                    'value_toman': outstanding_value,
                    'value_display': self._format_currency(outstanding_value)
                },
                'current_gold_price': {
                    'price_per_gram': current_gold_price,
                    'display': self._format_currency(current_gold_price)
                },
                'overdue_contracts': {
                    'count': len(overdue_contracts),
                    'contracts': [
                        {
                            'contract_number': contract.contract_number,
                            'customer_name': contract.customer.full_persian_name,
                            'remaining_weight': contract.remaining_gold_weight_grams,
                            'days_overdue': (timezone.now().date() - contract.contract_date).days
                        }
                        for contract in overdue_contracts[:5]  # Top 5 overdue
                    ]
                },
                'recent_payments': [
                    {
                        'contract_number': payment.contract.contract_number,
                        'customer_name': payment.contract.customer.full_persian_name,
                        'amount': {
                            'value': payment.payment_amount_toman,
                            'display': self._format_currency(payment.payment_amount_toman)
                        },
                        'gold_weight': {
                            'value': payment.gold_weight_equivalent_grams,
                            'display': self._format_weight(payment.gold_weight_equivalent_grams, 'gram')
                        },
                        'payment_date': payment.payment_date
                    }
                    for payment in recent_payments
                ],
                'payment_trends_30_days': {
                    'total_amount': {
                        'value': recent_payment_stats['total_amount'] or Decimal('0'),
                        'display': self._format_currency(recent_payment_stats['total_amount'] or Decimal('0'))
                    },
                    'total_payments': recent_payment_stats['total_payments'] or 0,
                    'average_payment': {
                        'value': recent_payment_stats['avg_payment'] or Decimal('0'),
                        'display': self._format_currency(recent_payment_stats['avg_payment'] or Decimal('0'))
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting gold installment metrics: {e}")
            return self._get_fallback_gold_installment_metrics()
    
    def get_gold_price_data(self) -> Dict:
        """
        Get current gold price data and trends.
        
        Returns:
            Dictionary with gold price information
        """
        try:
            # Try to import gold price service
            try:
                from zargar.gold_installments.services import GoldPriceService
                
                # Get current prices for different karats
                gold_18k = GoldPriceService.get_current_gold_price(18)
                gold_21k = GoldPriceService.get_current_gold_price(21)
                gold_24k = GoldPriceService.get_current_gold_price(24)
                
                # Get price trend for 18k gold (most common)
                price_trend = GoldPriceService.get_price_trend(18, 7)  # Last 7 days
            except ImportError:
                # Fallback prices
                gold_18k = {'price_per_gram': Decimal('3500000'), 'source': 'fallback', 'timestamp': timezone.now()}
                gold_21k = {'price_per_gram': Decimal('4083333')}
                gold_24k = {'price_per_gram': Decimal('4666666')}
                price_trend = []
            
            return {
                'current_prices': {
                    '18k': {
                        'price_per_gram': gold_18k['price_per_gram'],
                        'display': self._format_currency(gold_18k['price_per_gram']),
                        'source': gold_18k.get('source', 'fallback'),
                        'timestamp': gold_18k.get('timestamp', timezone.now())
                    },
                    '21k': {
                        'price_per_gram': gold_21k['price_per_gram'],
                        'display': self._format_currency(gold_21k['price_per_gram'])
                    },
                    '24k': {
                        'price_per_gram': gold_24k['price_per_gram'],
                        'display': self._format_currency(gold_24k['price_per_gram'])
                    }
                },
                'price_trend_7_days': [
                    {
                        'date': trend_point['date'],
                        'price': trend_point['price_per_gram'],
                        'display': self._format_currency(trend_point['price_per_gram'])
                    }
                    for trend_point in price_trend
                ],
                'trend_analysis': self._analyze_price_trend(price_trend)
            }
            
        except Exception as e:
            logger.error(f"Error getting gold price data: {e}")
            return self._get_fallback_gold_price_data()
    
    def get_financial_summary(self) -> Dict:
        """
        Get financial summary and key performance indicators.
        
        Returns:
            Dictionary with financial metrics
        """
        try:
            from django.apps import apps
            
            if not apps.ready:
                return self._get_fallback_financial_summary()
            
            today = timezone.now().date()
            month_start = today.replace(day=1)
            
            monthly_revenue = Decimal('0')
            installment_revenue = Decimal('0')
            inventory_investment = Decimal('0')
            
            # Revenue from sales (if jewelry app exists)
            try:
                JewelryItem = apps.get_model('jewelry', 'JewelryItem')
                monthly_sales = JewelryItem.objects.filter(
                    status='sold',
                    updated_at__date__gte=month_start
                )
                
                monthly_revenue = sum(
                    item.selling_price or item.total_value or Decimal('0')
                    for item in monthly_sales
                )
                
                # Inventory investment
                inventory_investment = JewelryItem.objects.filter(
                    status='in_stock'
                ).aggregate(
                    total_cost=Sum('manufacturing_cost')
                )['total_cost'] or Decimal('0')
            except LookupError:
                pass
            
            # Gold installment revenue (if gold_installments app exists)
            try:
                GoldInstallmentPayment = apps.get_model('gold_installments', 'GoldInstallmentPayment')
                installment_revenue = GoldInstallmentPayment.objects.filter(
                    payment_date__gte=month_start
                ).aggregate(
                    total=Sum('payment_amount_toman')
                )['total'] or Decimal('0')
            except LookupError:
                pass
            
            total_monthly_revenue = monthly_revenue + installment_revenue
            
            return {
                'monthly_revenue': {
                    'jewelry_sales': {
                        'amount': monthly_revenue,
                        'display': self._format_currency(monthly_revenue)
                    },
                    'installment_payments': {
                        'amount': installment_revenue,
                        'display': self._format_currency(installment_revenue)
                    },
                    'total': {
                        'amount': total_monthly_revenue,
                        'display': self._format_currency(total_monthly_revenue)
                    }
                },
                'inventory_investment': {
                    'amount': inventory_investment,
                    'display': self._format_currency(inventory_investment)
                },
                'profit_margin_estimate': self._calculate_profit_margin_estimate(monthly_revenue, inventory_investment)
            }
            
        except Exception as e:
            logger.error(f"Error getting financial summary: {e}")
            return self._get_fallback_financial_summary()
    
    def get_recent_activities(self) -> List[Dict]:
        """
        Get recent business activities and events.
        
        Returns:
            List of recent activity items
        """
        try:
            from django.apps import apps
            
            if not apps.ready:
                return []
            
            try:
                AuditLog = apps.get_model('core', 'AuditLog')
            except LookupError:
                return []
            
            # Get recent audit logs (use created_at instead of timestamp)
            recent_logs = AuditLog.objects.select_related('user').order_by('-created_at')[:20]
            
            activities = []
            for log in recent_logs:
                activity = {
                    'timestamp': log.created_at,  # Use created_at instead of timestamp
                    'user': log.user.full_persian_name if log.user else 'سیستم',
                    'action': log.get_action_display() if hasattr(log, 'get_action_display') else log.action,
                    'description': self._format_activity_description(log),
                    'type': self._categorize_activity(log.action),
                    'ip_address': log.ip_address
                }
                activities.append(activity)
            
            return activities
            
        except Exception as e:
            logger.error(f"Error getting recent activities: {e}")
            return []
    
    def get_alerts_and_notifications(self) -> Dict:
        """
        Get important alerts and notifications for the dashboard.
        
        Returns:
            Dictionary with categorized alerts
        """
        try:
            from django.apps import apps
            
            alerts = {
                'critical': [],
                'warning': [],
                'info': []
            }
            
            if not apps.ready:
                return alerts
            
            # Low stock alerts (if jewelry app exists)
            try:
                JewelryItem = apps.get_model('jewelry', 'JewelryItem')
                low_stock_items = JewelryItem.objects.filter(
                    status='in_stock',
                    quantity__lte=F('minimum_stock')
                ).count()
                
                if low_stock_items > 0:
                    alerts['warning'].append({
                        'type': 'low_stock',
                        'message': f'{low_stock_items} قلم کالا کمتر از حد مجاز موجودی دارند',
                        'count': low_stock_items,
                        'action_url': '/inventory/low-stock/'
                    })
            except LookupError:
                pass
            
            # Overdue installment contracts (if gold_installments app exists)
            try:
                GoldInstallmentContract = apps.get_model('gold_installments', 'GoldInstallmentContract')
                overdue_count = 0
                for contract in GoldInstallmentContract.objects.filter(status='active'):
                    if hasattr(contract, 'is_overdue') and contract.is_overdue:
                        overdue_count += 1
                
                if overdue_count > 0:
                    alerts['critical'].append({
                        'type': 'overdue_contracts',
                        'message': f'{overdue_count} قرارداد طلای قرضی دارای تأخیر در پرداخت هستند',
                        'count': overdue_count,
                        'action_url': '/gold-installments/overdue/'
                    })
            except LookupError:
                pass
            
            # Birthday customers this week (if customers app exists)
            try:
                Customer = apps.get_model('customers', 'Customer')
                today = timezone.now().date()
                week_end = today + timedelta(days=7)
                
                birthday_customers = Customer.objects.filter(
                    birth_date__month=today.month,
                    birth_date__day__gte=today.day,
                    birth_date__day__lte=week_end.day,
                    is_active=True
                ).count()
                
                if birthday_customers > 0:
                    alerts['info'].append({
                        'type': 'birthday_customers',
                        'message': f'{birthday_customers} مشتری در این هفته تولد دارند',
                        'count': birthday_customers,
                        'action_url': '/customers/birthdays/'
                    })
            except LookupError:
                pass
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting alerts and notifications: {e}")
            return {'critical': [], 'warning': [], 'info': []}
    
    def get_performance_trends(self) -> Dict:
        """
        Get performance trends and analytics.
        
        Returns:
            Dictionary with trend analysis
        """
        try:
            # Calculate trends for the last 30 days
            trends = {}
            
            # Sales trend
            sales_trend = self._calculate_sales_trend()
            trends['sales'] = sales_trend
            
            # Customer acquisition trend
            customer_trend = self._calculate_customer_acquisition_trend()
            trends['customers'] = customer_trend
            
            # Inventory turnover trend
            inventory_trend = self._calculate_inventory_trend()
            trends['inventory'] = inventory_trend
            
            return trends
            
        except Exception as e:
            logger.error(f"Error getting performance trends: {e}")
            return {}
    
    # Helper methods for calculations and formatting
    
    def _get_top_selling_categories(self) -> List[Dict]:
        """Get top selling jewelry categories."""
        try:
            from django.apps import apps
            
            if not apps.ready:
                return []
            
            try:
                Category = apps.get_model('jewelry', 'Category')
                JewelryItem = apps.get_model('jewelry', 'JewelryItem')
            except LookupError:
                return []
            
            categories = Category.objects.annotate(
                sold_count=Count('jewelryitem', filter=Q(jewelryitem__status='sold'))
            ).order_by('-sold_count')[:5]
            
            return [
                {
                    'name': cat.name_persian or cat.name,
                    'sold_count': cat.sold_count
                }
                for cat in categories if cat.sold_count > 0
            ]
        except:
            return []
    
    def _get_sales_trend(self) -> List[Dict]:
        """Get sales trend for the last 7 days."""
        try:
            from django.apps import apps
            
            if not apps.ready:
                return []
            
            try:
                JewelryItem = apps.get_model('jewelry', 'JewelryItem')
            except LookupError:
                return []
            
            trend_data = []
            for i in range(7):
                date_point = timezone.now().date() - timedelta(days=6-i)
                daily_sales = JewelryItem.objects.filter(
                    status='sold',
                    updated_at__date=date_point
                ).count()
                
                trend_data.append({
                    'date': date_point,
                    'sales_count': daily_sales
                })
            
            return trend_data
        except:
            return []
    
    def _analyze_price_trend(self, price_trend: List[Dict]) -> Dict:
        """Analyze gold price trend."""
        if len(price_trend) < 2:
            return {'direction': 'stable', 'change_percentage': 0}
        
        first_price = price_trend[0]['price_per_gram']
        last_price = price_trend[-1]['price_per_gram']
        
        change_percentage = ((last_price - first_price) / first_price * 100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        if change_percentage > 1:
            direction = 'increasing'
        elif change_percentage < -1:
            direction = 'decreasing'
        else:
            direction = 'stable'
        
        return {
            'direction': direction,
            'change_percentage': change_percentage,
            'change_display': self._format_percentage(abs(change_percentage))
        }
    
    def _calculate_profit_margin_estimate(self, revenue: Decimal, costs: Decimal) -> Dict:
        """Calculate estimated profit margin."""
        if revenue <= 0:
            return {'percentage': 0, 'display': '۰٪'}
        
        profit = revenue - costs
        margin_percentage = (profit / revenue * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return {
            'percentage': margin_percentage,
            'display': self._format_percentage(margin_percentage),
            'profit_amount': {
                'value': profit,
                'display': self._format_currency(profit)
            }
        }
    
    def _format_activity_description(self, log) -> str:
        """Format activity description in Persian."""
        action_descriptions = {
            'login': 'ورود به سیستم',
            'logout': 'خروج از سیستم',
            'create': 'ایجاد رکورد جدید',
            'update': 'به‌روزرسانی اطلاعات',
            'delete': 'حذف رکورد',
            'view': 'مشاهده اطلاعات'
        }
        
        base_description = action_descriptions.get(log.action, log.action)
        
        if log.model_name:
            base_description += f' در {log.model_name}'
        
        return base_description
    
    def _categorize_activity(self, action: str) -> str:
        """Categorize activity type."""
        if action in ['login', 'logout']:
            return 'authentication'
        elif action in ['create', 'update', 'delete']:
            return 'data_modification'
        else:
            return 'general'
    
    def _calculate_sales_trend(self) -> Dict:
        """Calculate sales trend analysis."""
        # Mock implementation - would use actual sales data
        return {
            'direction': 'increasing',
            'change_percentage': Decimal('15.5'),
            'period': '30_days'
        }
    
    def _calculate_customer_acquisition_trend(self) -> Dict:
        """Calculate customer acquisition trend."""
        try:
            from django.apps import apps
            
            if not apps.ready:
                return {'direction': 'stable', 'change_percentage': Decimal('0'), 'new_customers_30_days': 0}
            
            try:
                Customer = apps.get_model('customers', 'Customer')
            except LookupError:
                return {'direction': 'stable', 'change_percentage': Decimal('0'), 'new_customers_30_days': 0}
            
            thirty_days_ago = timezone.now() - timedelta(days=30)
            sixty_days_ago = timezone.now() - timedelta(days=60)
            
            recent_customers = Customer.objects.filter(
                created_at__gte=thirty_days_ago
            ).count()
            
            previous_customers = Customer.objects.filter(
                created_at__gte=sixty_days_ago,
                created_at__lt=thirty_days_ago
            ).count()
            
            if previous_customers > 0:
                change_percentage = ((recent_customers - previous_customers) / previous_customers * 100)
            else:
                change_percentage = 100 if recent_customers > 0 else 0
            
            return {
                'direction': 'increasing' if change_percentage > 0 else 'decreasing' if change_percentage < 0 else 'stable',
                'change_percentage': Decimal(str(change_percentage)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'new_customers_30_days': recent_customers
            }
        except:
            return {'direction': 'stable', 'change_percentage': Decimal('0'), 'new_customers_30_days': 0}
    
    def _calculate_inventory_trend(self) -> Dict:
        """Calculate inventory turnover trend."""
        # Mock implementation - would calculate actual turnover
        return {
            'turnover_rate': Decimal('2.5'),
            'direction': 'stable',
            'days_to_sell': 45
        }
    
    # Fallback methods for error handling
    
    def _get_fallback_dashboard_data(self) -> Dict:
        """Get fallback dashboard data when errors occur."""
        return {
            'sales_metrics': self._get_fallback_sales_metrics(),
            'inventory_metrics': self._get_fallback_inventory_metrics(),
            'customer_metrics': self._get_fallback_customer_metrics(),
            'gold_installment_metrics': self._get_fallback_gold_installment_metrics(),
            'gold_price_data': self._get_fallback_gold_price_data(),
            'financial_summary': self._get_fallback_financial_summary(),
            'recent_activities': [],
            'alerts_and_notifications': {'critical': [], 'warning': [], 'info': []},
            'performance_trends': {},
            'generated_at': timezone.now(),
            'tenant_schema': self.tenant_schema,
            'error': True
        }
    
    def _get_fallback_sales_metrics(self) -> Dict:
        """Fallback sales metrics."""
        return {
            'today': {'count': 0, 'value': Decimal('0'), 'value_display': '۰ تومان'},
            'this_week': {'count': 0, 'value': Decimal('0'), 'value_display': '۰ تومان'},
            'this_month': {'count': 0, 'value': Decimal('0'), 'value_display': '۰ تومان'},
            'average_sale_value': {'value': Decimal('0'), 'value_display': '۰ تومان'},
            'top_selling_categories': [],
            'sales_trend': []
        }
    
    def _get_fallback_inventory_metrics(self) -> Dict:
        """Fallback inventory metrics."""
        return {
            'total_items': 0,
            'in_stock': 0,
            'sold': 0,
            'reserved': 0,
            'low_stock_count': 0,
            'low_stock_items': [],
            'total_value': {'amount': Decimal('0'), 'display': '۰ تومان'},
            'value_breakdown': {
                'gold_value': {'amount': Decimal('0'), 'display': '۰ تومان'},
                'manufacturing_cost': {'amount': Decimal('0'), 'display': '۰ تومان'},
                'gemstone_value': {'amount': Decimal('0'), 'display': '۰ تومان'}
            },
            'category_distribution': []
        }
    
    def _get_fallback_customer_metrics(self) -> Dict:
        """Fallback customer metrics."""
        return {
            'total_customers': 0,
            'vip_customers': 0,
            'new_customers_this_month': 0,
            'customers_with_purchases': 0,
            'engagement_rate': 0,
            'total_loyalty_points': {'amount': 0, 'display': '۰'},
            'top_customers': [],
            'birthday_customers_this_month': [],
            'recent_loyalty_activity': []
        }
    
    def _get_fallback_gold_installment_metrics(self) -> Dict:
        """Fallback gold installment metrics."""
        return {
            'contract_counts': {'active': 0, 'completed': 0, 'defaulted': 0, 'total': 0},
            'outstanding_balance': {
                'gold_weight_grams': Decimal('0'),
                'gold_weight_display': '۰ گرم',
                'value_toman': Decimal('0'),
                'value_display': '۰ تومان'
            },
            'current_gold_price': {'price_per_gram': Decimal('3500000'), 'display': '۳٬۵۰۰٬۰۰۰ تومان'},
            'overdue_contracts': {'count': 0, 'contracts': []},
            'recent_payments': [],
            'payment_trends_30_days': {
                'total_amount': {'value': Decimal('0'), 'display': '۰ تومان'},
                'total_payments': 0,
                'average_payment': {'value': Decimal('0'), 'display': '۰ تومان'}
            }
        }
    
    def _get_fallback_gold_price_data(self) -> Dict:
        """Fallback gold price data."""
        return {
            'current_prices': {
                '18k': {'price_per_gram': Decimal('3500000'), 'display': '۳٬۵۰۰٬۰۰۰ تومان', 'source': 'fallback', 'timestamp': timezone.now()},
                '21k': {'price_per_gram': Decimal('4083333'), 'display': '۴٬۰۸۳٬۳۳۳ تومان'},
                '24k': {'price_per_gram': Decimal('4666666'), 'display': '۴٬۶۶۶٬۶۶۶ تومان'}
            },
            'price_trend_7_days': [],
            'trend_analysis': {'direction': 'stable', 'change_percentage': Decimal('0'), 'change_display': '۰٪'}
        }
    
    def _get_fallback_financial_summary(self) -> Dict:
        """Fallback financial summary."""
        return {
            'monthly_revenue': {
                'jewelry_sales': {'amount': Decimal('0'), 'display': '۰ تومان'},
                'installment_payments': {'amount': Decimal('0'), 'display': '۰ تومان'},
                'total': {'amount': Decimal('0'), 'display': '۰ تومان'}
            },
            'inventory_investment': {'amount': Decimal('0'), 'display': '۰ تومان'},
            'profit_margin_estimate': {'percentage': Decimal('0'), 'display': '۰٪', 'profit_amount': {'value': Decimal('0'), 'display': '۰ تومان'}}
        }
    
    # Helper methods for formatting and safe operations
    
    def _format_currency(self, amount: Decimal) -> str:
        """Format currency with Persian digits."""
        if self.formatter:
            return self.formatter.format_currency(amount, use_persian_digits=True)
        else:
            # Fallback formatting
            return f"{amount:,} تومان".replace(',', '٬')
    
    def _format_number(self, number: int) -> str:
        """Format number with Persian digits."""
        if self.formatter:
            return self.formatter.format_number(number, use_persian_digits=True)
        else:
            # Fallback formatting
            return str(number)
    
    def _format_weight(self, weight: Decimal, unit: str = 'gram') -> str:
        """Format weight with Persian digits."""
        if self.formatter:
            return self.formatter.format_weight(weight, unit, use_persian_digits=True)
        else:
            # Fallback formatting
            return f"{weight} {unit}"
    
    def _format_percentage(self, percentage: Decimal) -> str:
        """Format percentage with Persian digits."""
        if self.formatter:
            return self.formatter.format_percentage(percentage, use_persian_digits=True)
        else:
            # Fallback formatting
            return f"{percentage}٪"