"""
API views for supplier management backend.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Supplier, PurchaseOrder, PurchaseOrderItem
from .supplier_services import (
    SupplierPayment, 
    DeliverySchedule, 
    SupplierPerformanceMetrics,
    SupplierManagementService
)
from .supplier_serializers import (
    SupplierSerializer,
    SupplierCreateSerializer,
    PurchaseOrderSerializer,
    PurchaseOrderCreateSerializer,
    PurchaseOrderItemSerializer,
    SupplierPaymentSerializer,
    SupplierPaymentCreateSerializer,
    DeliveryScheduleSerializer,
    SupplierPerformanceMetricsSerializer,
    SupplierPerformanceReportSerializer,
    DeliveryTrackingUpdateSerializer
)
from zargar.core.permissions import TenantPermission


class SupplierViewSet(viewsets.ModelViewSet):
    """
    ViewSet for supplier management with contact and payment terms.
    """
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated, TenantPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['supplier_type', 'is_active', 'is_preferred', 'city']
    search_fields = ['name', 'persian_name', 'contact_person', 'phone_number', 'email']
    ordering_fields = ['name', 'persian_name', 'created_at', 'total_orders', 'total_amount']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return SupplierCreateSerializer
        return SupplierSerializer
    
    def get_queryset(self):
        """Filter suppliers by tenant and add performance metrics."""
        queryset = super().get_queryset()
        
        # Add performance metrics annotation
        queryset = queryset.select_related('performance_metrics')
        
        # Filter by active status if requested
        if self.request.query_params.get('active_only') == 'true':
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def performance_report(self, request, pk=None):
        """
        Get comprehensive performance report for a supplier.
        """
        supplier = self.get_object()
        report_data = SupplierManagementService.get_supplier_performance_report(supplier)
        
        serializer = SupplierPerformanceReportSerializer(report_data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def toggle_preferred(self, request, pk=None):
        """
        Toggle supplier preferred status.
        """
        supplier = self.get_object()
        supplier.is_preferred = not supplier.is_preferred
        supplier.save(update_fields=['is_preferred'])
        
        return Response({
            'message': _('Supplier preferred status updated'),
            'is_preferred': supplier.is_preferred
        })
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """
        Deactivate supplier (soft delete).
        """
        supplier = self.get_object()
        
        # Check for active purchase orders
        active_orders = supplier.purchase_orders.filter(
            status__in=['draft', 'sent', 'confirmed', 'partially_received']
        ).count()
        
        if active_orders > 0:
            return Response({
                'error': _('Cannot deactivate supplier with active purchase orders')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        supplier.is_active = False
        supplier.save(update_fields=['is_active'])
        
        return Response({
            'message': _('Supplier deactivated successfully')
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get supplier statistics overview.
        """
        queryset = self.get_queryset()
        
        stats = {
            'total_suppliers': queryset.count(),
            'active_suppliers': queryset.filter(is_active=True).count(),
            'preferred_suppliers': queryset.filter(is_preferred=True).count(),
            'suppliers_by_type': dict(
                queryset.values('supplier_type').annotate(
                    count=Count('id')
                ).values_list('supplier_type', 'count')
            ),
            'top_suppliers_by_orders': list(
                queryset.filter(is_active=True).order_by('-total_orders')[:5].values(
                    'id', 'name', 'persian_name', 'total_orders', 'total_amount'
                )
            ),
            'recent_suppliers': list(
                queryset.filter(
                    created_at__gte=timezone.now() - timezone.timedelta(days=30)
                ).count()
            )
        }
        
        return Response(stats)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for purchase order workflow with delivery tracking.
    """
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.IsAuthenticated, TenantPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['supplier', 'status', 'priority', 'is_paid']
    search_fields = ['order_number', 'supplier__name', 'supplier__persian_name']
    ordering_fields = ['order_date', 'expected_delivery_date', 'total_amount', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return PurchaseOrderCreateSerializer
        return PurchaseOrderSerializer
    
    def get_queryset(self):
        """Filter purchase orders by tenant with related data."""
        queryset = super().get_queryset()
        queryset = queryset.select_related('supplier').prefetch_related('items')
        
        # Filter by date range if provided
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(order_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(order_date__lte=date_to)
        
        # Filter overdue orders
        if self.request.query_params.get('overdue') == 'true':
            today = timezone.now().date()
            queryset = queryset.filter(
                expected_delivery_date__lt=today,
                status__in=['sent', 'confirmed', 'partially_received']
            )
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def mark_as_sent(self, request, pk=None):
        """
        Mark purchase order as sent to supplier.
        """
        purchase_order = self.get_object()
        
        if purchase_order.status != 'draft':
            return Response({
                'error': _('Only draft orders can be marked as sent')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        purchase_order.mark_as_sent()
        
        return Response({
            'message': _('Purchase order marked as sent'),
            'status': purchase_order.status
        })
    
    @action(detail=True, methods=['post'])
    def mark_as_confirmed(self, request, pk=None):
        """
        Mark purchase order as confirmed by supplier.
        """
        purchase_order = self.get_object()
        
        if purchase_order.status != 'sent':
            return Response({
                'error': _('Only sent orders can be marked as confirmed')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        purchase_order.mark_as_confirmed()
        
        return Response({
            'message': _('Purchase order marked as confirmed'),
            'status': purchase_order.status
        })
    
    @action(detail=True, methods=['post'])
    def mark_as_received(self, request, pk=None):
        """
        Mark purchase order as received (complete or partial).
        """
        purchase_order = self.get_object()
        partial = request.data.get('partial', False)
        
        if purchase_order.status not in ['confirmed', 'partially_received']:
            return Response({
                'error': _('Only confirmed orders can be marked as received')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        purchase_order.mark_as_received(partial=partial)
        
        return Response({
            'message': _('Purchase order marked as received'),
            'status': purchase_order.status
        })
    
    @action(detail=True, methods=['post'])
    def cancel_order(self, request, pk=None):
        """
        Cancel purchase order.
        """
        purchase_order = self.get_object()
        reason = request.data.get('reason', '')
        
        if purchase_order.status in ['completed', 'cancelled']:
            return Response({
                'error': _('Cannot cancel completed or already cancelled order')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        purchase_order.cancel_order(reason=reason)
        
        return Response({
            'message': _('Purchase order cancelled'),
            'status': purchase_order.status
        })
    
    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        """
        Get purchase order items.
        """
        purchase_order = self.get_object()
        items = purchase_order.items.all()
        serializer = PurchaseOrderItemSerializer(items, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def receive_item(self, request, pk=None):
        """
        Receive specific quantity of an item.
        """
        purchase_order = self.get_object()
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity', 0)
        
        try:
            item = purchase_order.items.get(id=item_id)
            success = item.receive_quantity(quantity)
            
            if success:
                return Response({
                    'message': _('Item quantity received successfully'),
                    'quantity_received': item.quantity_received,
                    'quantity_pending': item.quantity_pending
                })
            else:
                return Response({
                    'error': _('Invalid quantity or item already fully received')
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except PurchaseOrderItem.DoesNotExist:
            return Response({
                'error': _('Item not found')
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get purchase order statistics.
        """
        queryset = self.get_queryset()
        today = timezone.now().date()
        
        stats = {
            'total_orders': queryset.count(),
            'orders_by_status': dict(
                queryset.values('status').annotate(
                    count=Count('id')
                ).values_list('status', 'count')
            ),
            'total_value': queryset.aggregate(
                total=Sum('total_amount')
            )['total'] or 0,
            'overdue_orders': queryset.filter(
                expected_delivery_date__lt=today,
                status__in=['sent', 'confirmed', 'partially_received']
            ).count(),
            'orders_this_month': queryset.filter(
                order_date__year=today.year,
                order_date__month=today.month
            ).count(),
            'average_order_value': queryset.aggregate(
                avg=Avg('total_amount')
            )['avg'] or 0,
        }
        
        return Response(stats)


class SupplierPaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for supplier payment management.
    """
    queryset = SupplierPayment.objects.all()
    serializer_class = SupplierPaymentSerializer
    permission_classes = [permissions.IsAuthenticated, TenantPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['supplier', 'purchase_order', 'payment_method', 'status', 'is_approved']
    search_fields = ['payment_number', 'supplier__name', 'reference_number']
    ordering_fields = ['payment_date', 'amount', 'created_at']
    ordering = ['-payment_date']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return SupplierPaymentCreateSerializer
        return SupplierPaymentSerializer
    
    def get_queryset(self):
        """Filter payments by tenant with related data."""
        queryset = super().get_queryset()
        queryset = queryset.select_related('supplier', 'purchase_order', 'approved_by')
        
        # Filter by date range if provided
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(payment_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(payment_date__lte=date_to)
        
        # Filter pending approvals
        if self.request.query_params.get('pending_approval') == 'true':
            queryset = queryset.filter(status='pending', is_approved=False)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve supplier payment.
        """
        payment = self.get_object()
        
        if payment.is_approved:
            return Response({
                'error': _('Payment is already approved')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check user permissions (only owners and accountants can approve)
        if not request.user.can_access_accounting():
            return Response({
                'error': _('Insufficient permissions to approve payments')
            }, status=status.HTTP_403_FORBIDDEN)
        
        payment.approve_payment(request.user)
        
        return Response({
            'message': _('Payment approved successfully'),
            'status': payment.status,
            'is_approved': payment.is_approved
        })
    
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """
        Mark payment as completed.
        """
        payment = self.get_object()
        
        try:
            payment.mark_as_completed()
            return Response({
                'message': _('Payment marked as completed'),
                'status': payment.status
            })
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel payment.
        """
        payment = self.get_object()
        reason = request.data.get('reason', '')
        
        try:
            payment.cancel_payment(reason=reason)
            return Response({
                'message': _('Payment cancelled successfully'),
                'status': payment.status
            })
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """
        Get payments pending approval.
        """
        pending_payments = self.get_queryset().filter(
            status='pending',
            is_approved=False
        )
        
        serializer = self.get_serializer(pending_payments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get payment statistics.
        """
        queryset = self.get_queryset()
        today = timezone.now().date()
        
        stats = {
            'total_payments': queryset.count(),
            'total_amount': queryset.aggregate(
                total=Sum('amount')
            )['total'] or 0,
            'payments_by_status': dict(
                queryset.values('status').annotate(
                    count=Count('id')
                ).values_list('status', 'count')
            ),
            'payments_by_method': dict(
                queryset.values('payment_method').annotate(
                    count=Count('id')
                ).values_list('payment_method', 'count')
            ),
            'pending_approvals': queryset.filter(
                status='pending',
                is_approved=False
            ).count(),
            'payments_this_month': queryset.filter(
                payment_date__year=today.year,
                payment_date__month=today.month
            ).aggregate(
                count=Count('id'),
                total=Sum('amount')
            ),
        }
        
        return Response(stats)


class DeliveryScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for delivery schedule management and tracking.
    """
    queryset = DeliverySchedule.objects.all()
    serializer_class = DeliveryScheduleSerializer
    permission_classes = [permissions.IsAuthenticated, TenantPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['purchase_order__supplier', 'status', 'delivery_method']
    search_fields = [
        'delivery_number', 
        'tracking_number', 
        'purchase_order__order_number',
        'purchase_order__supplier__name'
    ]
    ordering_fields = ['scheduled_date', 'actual_delivery_date', 'created_at']
    ordering = ['scheduled_date']
    
    def get_queryset(self):
        """Filter delivery schedules by tenant with related data."""
        queryset = super().get_queryset()
        queryset = queryset.select_related(
            'purchase_order', 
            'purchase_order__supplier'
        )
        
        # Filter by date range if provided
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(scheduled_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(scheduled_date__lte=date_to)
        
        # Filter overdue deliveries
        if self.request.query_params.get('overdue') == 'true':
            today = timezone.now().date()
            queryset = queryset.filter(
                scheduled_date__lt=today,
                status__in=['scheduled', 'in_transit', 'delayed']
            )
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def update_tracking(self, request, pk=None):
        """
        Update delivery tracking information.
        """
        delivery = self.get_object()
        serializer = DeliveryTrackingUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            data = serializer.validated_data
            
            # Update delivery status and tracking
            delivery = SupplierManagementService.update_delivery_tracking(
                delivery_schedule=delivery,
                status=data['status'],
                tracking_number=data.get('tracking_number', ''),
                notes=data.get('notes', '')
            )
            
            # Handle special status updates
            if data['status'] == 'delivered':
                delivery.mark_as_delivered(
                    received_by_name=data.get('received_by_name', ''),
                    signature=data.get('received_by_signature', '')
                )
            elif data['status'] == 'in_transit':
                delivery.mark_as_in_transit(
                    tracking_number=data.get('tracking_number', '')
                )
            
            response_serializer = self.get_serializer(delivery)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def mark_delivered(self, request, pk=None):
        """
        Mark delivery as completed.
        """
        delivery = self.get_object()
        received_by_name = request.data.get('received_by_name', '')
        signature = request.data.get('signature', '')
        
        if not received_by_name:
            return Response({
                'error': _('Received by name is required')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        delivery.mark_as_delivered(
            received_by_name=received_by_name,
            signature=signature
        )
        
        return Response({
            'message': _('Delivery marked as completed'),
            'status': delivery.status,
            'actual_delivery_date': delivery.actual_delivery_date
        })
    
    @action(detail=True, methods=['post'])
    def mark_delayed(self, request, pk=None):
        """
        Mark delivery as delayed and reschedule.
        """
        delivery = self.get_object()
        new_date = request.data.get('new_date')
        reason = request.data.get('reason', '')
        
        if not new_date:
            return Response({
                'error': _('New delivery date is required')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from datetime import datetime
            new_date = datetime.strptime(new_date, '%Y-%m-%d').date()
            delivery.mark_as_delayed(new_date=new_date, reason=reason)
            
            return Response({
                'message': _('Delivery rescheduled'),
                'status': delivery.status,
                'scheduled_date': delivery.scheduled_date
            })
        except ValueError:
            return Response({
                'error': _('Invalid date format. Use YYYY-MM-DD')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """
        Get all overdue deliveries.
        """
        overdue_deliveries = SupplierManagementService.get_overdue_deliveries()
        serializer = self.get_serializer(overdue_deliveries, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def today_deliveries(self, request):
        """
        Get deliveries scheduled for today.
        """
        today = timezone.now().date()
        today_deliveries = self.get_queryset().filter(
            scheduled_date=today,
            status__in=['scheduled', 'in_transit']
        )
        
        serializer = self.get_serializer(today_deliveries, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get delivery statistics.
        """
        queryset = self.get_queryset()
        today = timezone.now().date()
        
        stats = {
            'total_deliveries': queryset.count(),
            'deliveries_by_status': dict(
                queryset.values('status').annotate(
                    count=Count('id')
                ).values_list('status', 'count')
            ),
            'overdue_deliveries': queryset.filter(
                scheduled_date__lt=today,
                status__in=['scheduled', 'in_transit', 'delayed']
            ).count(),
            'today_deliveries': queryset.filter(
                scheduled_date=today,
                status__in=['scheduled', 'in_transit']
            ).count(),
            'completed_this_month': queryset.filter(
                actual_delivery_date__year=today.year,
                actual_delivery_date__month=today.month,
                status='delivered'
            ).count(),
            'average_delivery_cost': queryset.aggregate(
                avg=Avg('delivery_cost')
            )['avg'] or 0,
        }
        
        return Response(stats)


class SupplierPerformanceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for supplier performance metrics (read-only).
    """
    queryset = SupplierPerformanceMetrics.objects.all()
    serializer_class = SupplierPerformanceMetricsSerializer
    permission_classes = [permissions.IsAuthenticated, TenantPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['supplier']
    ordering_fields = ['overall_rating', 'total_deliveries', 'last_calculated']
    ordering = ['-overall_rating']
    
    def get_queryset(self):
        """Filter performance metrics by tenant."""
        return super().get_queryset().select_related('supplier')
    
    @action(detail=True, methods=['post'])
    def update_metrics(self, request, pk=None):
        """
        Manually update performance metrics for a supplier.
        """
        metrics = self.get_object()
        metrics.update_metrics()
        
        serializer = self.get_serializer(metrics)
        return Response({
            'message': _('Performance metrics updated successfully'),
            'metrics': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def top_performers(self, request):
        """
        Get top performing suppliers.
        """
        top_suppliers = self.get_queryset().filter(
            overall_rating__gt=0
        ).order_by('-overall_rating')[:10]
        
        serializer = self.get_serializer(top_suppliers, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def performance_summary(self, request):
        """
        Get overall performance summary.
        """
        queryset = self.get_queryset()
        
        summary = {
            'total_suppliers_with_metrics': queryset.count(),
            'average_rating': queryset.aggregate(
                avg=Avg('overall_rating')
            )['avg'] or 0,
            'average_on_time_delivery': queryset.exclude(
                total_deliveries=0
            ).aggregate(
                avg=Avg('on_time_deliveries') * 100 / Avg('total_deliveries')
            )['avg'] or 0,
            'total_orders_tracked': queryset.aggregate(
                total=Sum('total_deliveries')
            )['total'] or 0,
            'suppliers_above_4_rating': queryset.filter(
                overall_rating__gte=4.0
            ).count(),
        }
        
        return Response(summary)