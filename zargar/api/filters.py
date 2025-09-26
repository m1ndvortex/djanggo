"""
Django filters for API endpoints with tenant-aware filtering.
"""
import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from zargar.jewelry.models import JewelryItem, Category
from zargar.customers.models import Customer
from zargar.pos.models import POSTransaction


class JewelryItemFilter(django_filters.FilterSet):
    """
    Filter set for jewelry items with advanced filtering options.
    """
    name = django_filters.CharFilter(lookup_expr='icontains', label=_('Name contains'))
    sku = django_filters.CharFilter(lookup_expr='icontains', label=_('SKU contains'))
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.all(),
        label=_('Category')
    )
    status = django_filters.ChoiceFilter(
        choices=JewelryItem.STATUS_CHOICES,
        label=_('Status')
    )
    karat_min = django_filters.NumberFilter(
        field_name='karat',
        lookup_expr='gte',
        label=_('Minimum Karat')
    )
    karat_max = django_filters.NumberFilter(
        field_name='karat',
        lookup_expr='lte',
        label=_('Maximum Karat')
    )
    weight_min = django_filters.NumberFilter(
        field_name='weight_grams',
        lookup_expr='gte',
        label=_('Minimum Weight (grams)')
    )
    weight_max = django_filters.NumberFilter(
        field_name='weight_grams',
        lookup_expr='lte',
        label=_('Maximum Weight (grams)')
    )
    price_min = django_filters.NumberFilter(
        field_name='selling_price',
        lookup_expr='gte',
        label=_('Minimum Price')
    )
    price_max = django_filters.NumberFilter(
        field_name='selling_price',
        lookup_expr='lte',
        label=_('Maximum Price')
    )
    low_stock = django_filters.BooleanFilter(
        method='filter_low_stock',
        label=_('Low Stock Items')
    )
    has_gemstones = django_filters.BooleanFilter(
        method='filter_has_gemstones',
        label=_('Has Gemstones')
    )
    created_after = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='gte',
        label=_('Created After')
    )
    created_before = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='lte',
        label=_('Created Before')
    )
    
    class Meta:
        model = JewelryItem
        fields = [
            'name', 'sku', 'category', 'status', 'karat_min', 'karat_max',
            'weight_min', 'weight_max', 'price_min', 'price_max',
            'low_stock', 'has_gemstones', 'created_after', 'created_before'
        ]
    
    def filter_low_stock(self, queryset, name, value):
        """
        Filter items with low stock levels.
        """
        if value:
            return queryset.filter(quantity__lte=django_filters.F('minimum_stock'))
        return queryset
    
    def filter_has_gemstones(self, queryset, name, value):
        """
        Filter items that have or don't have gemstones.
        """
        if value:
            return queryset.filter(gemstones__isnull=False).distinct()
        else:
            return queryset.filter(gemstones__isnull=True)


class CustomerFilter(django_filters.FilterSet):
    """
    Filter set for customers with advanced filtering options.
    """
    name = django_filters.CharFilter(
        method='filter_name',
        label=_('Name contains')
    )
    phone = django_filters.CharFilter(
        field_name='phone_number',
        lookup_expr='icontains',
        label=_('Phone contains')
    )
    email = django_filters.CharFilter(
        field_name='email',
        lookup_expr='icontains',
        label=_('Email contains')
    )
    customer_type = django_filters.ChoiceFilter(
        choices=Customer.CUSTOMER_TYPES,
        label=_('Customer Type')
    )
    is_vip = django_filters.BooleanFilter(label=_('VIP Customer'))
    city = django_filters.CharFilter(
        lookup_expr='icontains',
        label=_('City contains')
    )
    province = django_filters.CharFilter(
        lookup_expr='icontains',
        label=_('Province contains')
    )
    loyalty_points_min = django_filters.NumberFilter(
        field_name='loyalty_points',
        lookup_expr='gte',
        label=_('Minimum Loyalty Points')
    )
    loyalty_points_max = django_filters.NumberFilter(
        field_name='loyalty_points',
        lookup_expr='lte',
        label=_('Maximum Loyalty Points')
    )
    total_purchases_min = django_filters.NumberFilter(
        field_name='total_purchases',
        lookup_expr='gte',
        label=_('Minimum Total Purchases')
    )
    total_purchases_max = django_filters.NumberFilter(
        field_name='total_purchases',
        lookup_expr='lte',
        label=_('Maximum Total Purchases')
    )
    birth_month = django_filters.NumberFilter(
        field_name='birth_date__month',
        label=_('Birth Month')
    )
    registered_after = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='gte',
        label=_('Registered After')
    )
    registered_before = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='lte',
        label=_('Registered Before')
    )
    last_purchase_after = django_filters.DateFilter(
        field_name='last_purchase_date',
        lookup_expr='gte',
        label=_('Last Purchase After')
    )
    last_purchase_before = django_filters.DateFilter(
        field_name='last_purchase_date',
        lookup_expr='lte',
        label=_('Last Purchase Before')
    )
    
    class Meta:
        model = Customer
        fields = [
            'name', 'phone', 'email', 'customer_type', 'is_vip', 'city', 'province',
            'loyalty_points_min', 'loyalty_points_max', 'total_purchases_min',
            'total_purchases_max', 'birth_month', 'registered_after',
            'registered_before', 'last_purchase_after', 'last_purchase_before'
        ]
    
    def filter_name(self, queryset, name, value):
        """
        Filter by name in both English and Persian fields.
        """
        return queryset.filter(
            Q(first_name__icontains=value) |
            Q(last_name__icontains=value) |
            Q(persian_first_name__icontains=value) |
            Q(persian_last_name__icontains=value)
        )


class POSTransactionFilter(django_filters.FilterSet):
    """
    Filter set for POS transactions with advanced filtering options.
    """
    transaction_number = django_filters.CharFilter(
        lookup_expr='icontains',
        label=_('Transaction Number contains')
    )
    customer = django_filters.ModelChoiceFilter(
        queryset=Customer.objects.all(),
        label=_('Customer')
    )
    customer_name = django_filters.CharFilter(
        method='filter_customer_name',
        label=_('Customer Name contains')
    )
    customer_phone = django_filters.CharFilter(
        field_name='customer__phone_number',
        lookup_expr='icontains',
        label=_('Customer Phone contains')
    )
    payment_method = django_filters.ChoiceFilter(
        choices=POSTransaction.PAYMENT_METHOD_CHOICES,
        label=_('Payment Method')
    )
    transaction_type = django_filters.ChoiceFilter(
        choices=POSTransaction.TRANSACTION_TYPE_CHOICES,
        label=_('Transaction Type')
    )
    status = django_filters.ChoiceFilter(
        choices=POSTransaction.STATUS_CHOICES,
        label=_('Status')
    )
    amount_min = django_filters.NumberFilter(
        field_name='total_amount',
        lookup_expr='gte',
        label=_('Minimum Amount')
    )
    amount_max = django_filters.NumberFilter(
        field_name='total_amount',
        lookup_expr='lte',
        label=_('Maximum Amount')
    )
    date_from = django_filters.DateFilter(
        field_name='transaction_date',
        lookup_expr='gte',
        label=_('Date From')
    )
    date_to = django_filters.DateFilter(
        field_name='transaction_date',
        lookup_expr='lte',
        label=_('Date To')
    )
    salesperson = django_filters.CharFilter(
        method='filter_salesperson',
        label=_('Salesperson Name contains')
    )
    has_discount = django_filters.BooleanFilter(
        method='filter_has_discount',
        label=_('Has Discount')
    )
    is_offline = django_filters.BooleanFilter(
        field_name='is_offline_transaction',
        label=_('Is Offline Transaction')
    )
    sync_status = django_filters.ChoiceFilter(
        choices=[
            ('synced', _('Synced')),
            ('pending_sync', _('Pending Sync')),
            ('sync_failed', _('Sync Failed')),
        ],
        label=_('Sync Status')
    )
    
    class Meta:
        model = POSTransaction
        fields = [
            'transaction_number', 'customer', 'customer_name', 'customer_phone',
            'payment_method', 'transaction_type', 'status', 'amount_min',
            'amount_max', 'date_from', 'date_to', 'salesperson',
            'has_discount', 'is_offline', 'sync_status'
        ]
    
    def filter_customer_name(self, queryset, name, value):
        """
        Filter by customer name in both English and Persian fields.
        """
        return queryset.filter(
            Q(customer__first_name__icontains=value) |
            Q(customer__last_name__icontains=value) |
            Q(customer__persian_first_name__icontains=value) |
            Q(customer__persian_last_name__icontains=value)
        )
    
    def filter_salesperson(self, queryset, name, value):
        """
        Filter by salesperson name.
        """
        return queryset.filter(
            Q(created_by__first_name__icontains=value) |
            Q(created_by__last_name__icontains=value) |
            Q(created_by__persian_first_name__icontains=value) |
            Q(created_by__persian_last_name__icontains=value) |
            Q(created_by__username__icontains=value)
        )
    
    def filter_has_discount(self, queryset, name, value):
        """
        Filter transactions that have or don't have discounts.
        """
        if value:
            return queryset.filter(discount_amount__gt=0)
        else:
            return queryset.filter(discount_amount=0)


class DateRangeFilter(django_filters.FilterSet):
    """
    Base filter for date range filtering with Persian calendar support.
    """
    date_from = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='gte',
        label=_('Date From')
    )
    date_to = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='lte',
        label=_('Date To')
    )
    
    # Persian calendar date filters
    shamsi_year = django_filters.NumberFilter(
        method='filter_shamsi_year',
        label=_('Shamsi Year')
    )
    shamsi_month = django_filters.NumberFilter(
        method='filter_shamsi_month',
        label=_('Shamsi Month')
    )
    
    def filter_shamsi_year(self, queryset, name, value):
        """
        Filter by Shamsi (Persian) year.
        """
        import jdatetime
        
        try:
            # Convert Shamsi year to Gregorian date range
            start_date = jdatetime.date(value, 1, 1).togregorian()
            end_date = jdatetime.date(value, 12, 29).togregorian()
            
            return queryset.filter(
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            )
        except (ValueError, TypeError):
            return queryset
    
    def filter_shamsi_month(self, queryset, name, value):
        """
        Filter by Shamsi (Persian) month in current year.
        """
        import jdatetime
        
        try:
            current_shamsi_year = jdatetime.date.today().year
            
            # Calculate days in month
            if value <= 6:
                days_in_month = 31
            elif value <= 11:
                days_in_month = 30
            else:
                days_in_month = 29  # Esfand
            
            start_date = jdatetime.date(current_shamsi_year, value, 1).togregorian()
            end_date = jdatetime.date(current_shamsi_year, value, days_in_month).togregorian()
            
            return queryset.filter(
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            )
        except (ValueError, TypeError):
            return queryset


class PriceRangeFilter(django_filters.FilterSet):
    """
    Base filter for price range filtering with Persian currency support.
    """
    price_min = django_filters.NumberFilter(
        field_name='total_amount',
        lookup_expr='gte',
        label=_('Minimum Price (Toman)')
    )
    price_max = django_filters.NumberFilter(
        field_name='total_amount',
        lookup_expr='lte',
        label=_('Maximum Price (Toman)')
    )
    
    # Predefined price ranges
    price_range = django_filters.ChoiceFilter(
        method='filter_price_range',
        choices=[
            ('under_1m', _('Under 1 Million Toman')),
            ('1m_5m', _('1-5 Million Toman')),
            ('5m_10m', _('5-10 Million Toman')),
            ('10m_50m', _('10-50 Million Toman')),
            ('over_50m', _('Over 50 Million Toman')),
        ],
        label=_('Price Range')
    )
    
    def filter_price_range(self, queryset, name, value):
        """
        Filter by predefined price ranges.
        """
        price_ranges = {
            'under_1m': (0, 1000000),
            '1m_5m': (1000000, 5000000),
            '5m_10m': (5000000, 10000000),
            '10m_50m': (10000000, 50000000),
            'over_50m': (50000000, float('inf')),
        }
        
        if value in price_ranges:
            min_price, max_price = price_ranges[value]
            filters = {'total_amount__gte': min_price}
            
            if max_price != float('inf'):
                filters['total_amount__lte'] = max_price
            
            return queryset.filter(**filters)
        
        return queryset