"""
DRF API ViewSets for core functionality with tenant filtering.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q, F
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from zargar.core.permissions import (
    TenantPermission, OwnerPermission, AccountingPermission, 
    POSPermission, AllRolesPermission, SelfOrOwnerPermission
)
from zargar.jewelry.models import JewelryItem, Category, Gemstone
from zargar.customers.models import Customer, Supplier
from zargar.pos.models import POSTransaction, POSTransactionLineItem
from .serializers import (
    JewelryItemSerializer, JewelryItemCreateSerializer, JewelryItemListSerializer,
    CategorySerializer, GemstoneSerializer,
    CustomerSerializer, CustomerCreateSerializer, CustomerListSerializer,
    SupplierSerializer, SupplierCreateSerializer,
    POSTransactionSerializer, POSTransactionCreateSerializer, POSTransactionListSerializer,
    POSTransactionLineItemSerializer
)
from .filters import JewelryItemFilter, CustomerFilter, POSTransactionFilter
from .throttling import TenantAPIThrottle


class JewelryItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for jewelry items with tenant filtering and role-based permissions.
    """
    permission_classes = [TenantPermission, AllRolesPermission]
    throttle_classes = [TenantAPIThrottle]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = JewelryItemFilter
    search_fields = ['name', 'sku', 'barcode', 'description']
    ordering_fields = ['name', 'created_at', 'weight_grams', 'selling_price', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Return jewelry items for current tenant only.
        """
        return JewelryItem.objects.select_related('category').prefetch_related('gemstones', 'photos')
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == 'create':
            return JewelryItemCreateSerializer
        elif self.action == 'list':
            return JewelryItemListSerializer
        return JewelryItemSerializer
    
    def get_permissions(self):
        """
        Set permissions based on action.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Only owners can modify jewelry items
            permission_classes = [TenantPermission, OwnerPermission]
        else:
            # All roles can view jewelry items
            permission_classes = [TenantPermission, AllRolesPermission]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """
        Get jewelry items with low stock levels.
        """
        low_stock_items = self.get_queryset().filter(
            quantity__lte=F('minimum_stock')
        )
        serializer = self.get_serializer(low_stock_items, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """
        Get jewelry items grouped by category.
        """
        category_id = request.query_params.get('category_id')
        if not category_id:
            return Response(
                {'error': _('Category ID is required.')}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        items = self.get_queryset().filter(category_id=category_id)
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_gold_value(self, request, pk=None):
        """
        Update gold value based on current market price.
        """
        item = self.get_object()
        gold_price = request.data.get('gold_price_per_gram')
        
        if not gold_price:
            return Response(
                {'error': _('Gold price per gram is required.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            gold_price = float(gold_price)
            item.update_gold_value(gold_price)
            serializer = self.get_serializer(item)
            return Response(serializer.data)
        except (ValueError, TypeError):
            return Response(
                {'error': _('Invalid gold price format.')},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def generate_barcode(self, request, pk=None):
        """
        Generate barcode for jewelry item.
        """
        item = self.get_object()
        
        if item.barcode:
            return Response(
                {'error': _('Item already has a barcode.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate unique barcode
        import uuid
        item.barcode = f"JWL-{uuid.uuid4().hex[:8].upper()}"
        item.save(update_fields=['barcode'])
        
        serializer = self.get_serializer(item)
        return Response(serializer.data)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for jewelry categories with tenant filtering.
    """
    serializer_class = CategorySerializer
    permission_classes = [TenantPermission, AllRolesPermission]
    throttle_classes = [TenantAPIThrottle]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'name_persian', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """
        Return categories for current tenant only.
        """
        return Category.objects.filter(is_active=True)
    
    def get_permissions(self):
        """
        Set permissions based on action.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [TenantPermission, OwnerPermission]
        else:
            permission_classes = [TenantPermission, AllRolesPermission]
        
        return [permission() for permission in permission_classes]


class GemstoneViewSet(viewsets.ModelViewSet):
    """
    ViewSet for gemstones with tenant filtering.
    """
    serializer_class = GemstoneSerializer
    permission_classes = [TenantPermission, AllRolesPermission]
    throttle_classes = [TenantAPIThrottle]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['gemstone_type', 'cut_grade']
    search_fields = ['name', 'certification_number']
    ordering_fields = ['name', 'carat_weight', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Return gemstones for current tenant only.
        """
        return Gemstone.objects.all()
    
    def get_permissions(self):
        """
        Set permissions based on action.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [TenantPermission, OwnerPermission]
        else:
            permission_classes = [TenantPermission, AllRolesPermission]
        
        return [permission() for permission in permission_classes]


class CustomerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for customers with tenant filtering and role-based permissions.
    """
    permission_classes = [TenantPermission, AllRolesPermission]
    throttle_classes = [TenantAPIThrottle]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CustomerFilter
    search_fields = ['first_name', 'last_name', 'persian_first_name', 'persian_last_name', 'phone_number', 'email']
    ordering_fields = ['first_name', 'last_name', 'created_at', 'total_purchases', 'loyalty_points']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Return customers for current tenant only.
        """
        return Customer.objects.filter(is_active=True)
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == 'create':
            return CustomerCreateSerializer
        elif self.action == 'list':
            return CustomerListSerializer
        return CustomerSerializer
    
    def get_permissions(self):
        """
        Set permissions based on action.
        """
        if self.action in ['create', 'update', 'partial_update']:
            # All roles can create and update customers
            permission_classes = [TenantPermission, AllRolesPermission]
        elif self.action == 'destroy':
            # Only owners can delete customers
            permission_classes = [TenantPermission, OwnerPermission]
        else:
            # All roles can view customers
            permission_classes = [TenantPermission, AllRolesPermission]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['get'])
    def vip_customers(self, request):
        """
        Get VIP customers.
        """
        vip_customers = self.get_queryset().filter(is_vip=True)
        serializer = self.get_serializer(vip_customers, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def birthday_today(self, request):
        """
        Get customers with birthday today.
        """
        from django.utils import timezone
        import jdatetime
        
        today_shamsi = jdatetime.date.today()
        
        # Find customers with birthday today (Shamsi calendar)
        birthday_customers = []
        for customer in self.get_queryset():
            if customer.is_birthday_today:
                birthday_customers.append(customer)
        
        serializer = self.get_serializer(birthday_customers, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_loyalty_points(self, request, pk=None):
        """
        Add loyalty points to customer.
        """
        customer = self.get_object()
        points = request.data.get('points')
        reason = request.data.get('reason', '')
        
        if not points:
            return Response(
                {'error': _('Points amount is required.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            points = int(points)
            if points <= 0:
                raise ValueError()
            
            customer.add_loyalty_points(points, reason)
            serializer = self.get_serializer(customer)
            return Response(serializer.data)
        except (ValueError, TypeError):
            return Response(
                {'error': _('Invalid points amount.')},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def redeem_loyalty_points(self, request, pk=None):
        """
        Redeem loyalty points from customer.
        """
        customer = self.get_object()
        points = request.data.get('points')
        reason = request.data.get('reason', '')
        
        if not points:
            return Response(
                {'error': _('Points amount is required.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            points = int(points)
            if points <= 0:
                raise ValueError()
            
            if customer.redeem_loyalty_points(points, reason):
                serializer = self.get_serializer(customer)
                return Response(serializer.data)
            else:
                return Response(
                    {'error': _('Insufficient loyalty points.')},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': _('Invalid points amount.')},
                status=status.HTTP_400_BAD_REQUEST
            )


class SupplierViewSet(viewsets.ModelViewSet):
    """
    ViewSet for suppliers with tenant filtering.
    """
    permission_classes = [TenantPermission, AccountingPermission]
    throttle_classes = [TenantAPIThrottle]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['supplier_type', 'is_active', 'is_preferred']
    search_fields = ['name', 'persian_name', 'contact_person', 'phone_number']
    ordering_fields = ['name', 'created_at', 'total_orders', 'total_amount']
    ordering = ['name']
    
    def get_queryset(self):
        """
        Return suppliers for current tenant only.
        """
        return Supplier.objects.filter(is_active=True)
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == 'create':
            return SupplierCreateSerializer
        return SupplierSerializer
    
    def get_permissions(self):
        """
        Set permissions based on action.
        """
        # Only owners and accountants can manage suppliers
        return [TenantPermission(), AccountingPermission()]
    
    @action(detail=False, methods=['get'])
    def preferred(self, request):
        """
        Get preferred suppliers.
        """
        preferred_suppliers = self.get_queryset().filter(is_preferred=True)
        serializer = self.get_serializer(preferred_suppliers, many=True)
        return Response(serializer.data)


class POSTransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for POS transactions with tenant filtering and role-based permissions.
    """
    permission_classes = [TenantPermission, POSPermission]
    throttle_classes = [TenantAPIThrottle]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = POSTransactionFilter
    search_fields = ['transaction_number', 'customer__first_name', 'customer__last_name', 'customer__phone_number']
    ordering_fields = ['created_at', 'total_amount', 'transaction_number']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Return POS transactions for current tenant only.
        """
        return POSTransaction.objects.select_related('customer', 'created_by').prefetch_related('line_items__jewelry_item')
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == 'create':
            return POSTransactionCreateSerializer
        elif self.action == 'list':
            return POSTransactionListSerializer
        return POSTransactionSerializer
    
    @action(detail=False, methods=['get'])
    def today_transactions(self, request):
        """
        Get today's transactions.
        """
        from django.utils import timezone
        today = timezone.now().date()
        
        today_transactions = self.get_queryset().filter(transaction_date__date=today)
        serializer = self.get_serializer(today_transactions, many=True)
        
        # Calculate totals
        total_amount = sum(transaction.total_amount for transaction in today_transactions)
        total_count = today_transactions.count()
        
        return Response({
            'transactions': serializer.data,
            'summary': {
                'total_amount': total_amount,
                'total_count': total_count,
                'date': today.isoformat()
            }
        })
    
    @action(detail=False, methods=['get'])
    def monthly_transactions(self, request):
        """
        Get current month's transactions summary.
        """
        from django.utils import timezone
        from django.db.models import Sum, Count
        
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        monthly_transactions = self.get_queryset().filter(transaction_date__gte=month_start)
        
        summary = monthly_transactions.aggregate(
            total_amount=Sum('total_amount'),
            total_count=Count('id')
        )
        
        return Response({
            'summary': {
                'total_amount': summary['total_amount'] or 0,
                'total_count': summary['total_count'] or 0,
                'month': now.strftime('%Y-%m'),
                'period': f"{month_start.date()} to {now.date()}"
            }
        })
    
    @action(detail=True, methods=['post'])
    def complete_transaction(self, request, pk=None):
        """
        Complete the POS transaction.
        """
        transaction = self.get_object()
        
        if transaction.status == 'completed':
            return Response(
                {'error': _('Transaction is already completed.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment_method = request.data.get('payment_method')
        amount_paid = request.data.get('amount_paid')
        
        try:
            transaction.complete_transaction(payment_method, amount_paid)
            serializer = self.get_serializer(transaction)
            return Response(serializer.data)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class POSTransactionLineItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for POS transaction line items.
    """
    serializer_class = POSTransactionLineItemSerializer
    permission_classes = [TenantPermission, POSPermission]
    throttle_classes = [TenantAPIThrottle]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['transaction', 'jewelry_item']
    ordering_fields = ['created_at', 'quantity', 'unit_price']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Return POS transaction line items for current tenant only.
        """
        return POSTransactionLineItem.objects.select_related('transaction', 'jewelry_item')