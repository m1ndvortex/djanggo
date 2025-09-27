"""
API endpoints for tenant dashboard data.
Provides JSON API for dashboard metrics and real-time updates.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json

from .dashboard_services import TenantDashboardService


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(60 * 5)  # Cache for 5 minutes
def dashboard_data_api(request):
    """
    API endpoint to get comprehensive dashboard data.
    
    Returns:
        JSON response with dashboard metrics
    """
    try:
        # Get tenant schema from request
        tenant_schema = getattr(request, 'tenant_context', {}).get('schema_name', 'default')
        
        # Initialize dashboard service
        dashboard_service = TenantDashboardService(tenant_schema)
        
        # Get dashboard data
        dashboard_data = dashboard_service.get_comprehensive_dashboard_data()
        
        # Convert datetime objects to strings for JSON serialization
        if 'generated_at' in dashboard_data:
            dashboard_data['generated_at'] = dashboard_data['generated_at'].isoformat()
        
        # Convert any other datetime objects in nested data
        dashboard_data = _serialize_datetime_objects(dashboard_data)
        
        return Response({
            'success': True,
            'data': dashboard_data,
            'message': 'Dashboard data retrieved successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve dashboard data'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sales_metrics_api(request):
    """
    API endpoint to get sales metrics only.
    
    Returns:
        JSON response with sales metrics
    """
    try:
        tenant_schema = getattr(request, 'tenant_context', {}).get('schema_name', 'default')
        dashboard_service = TenantDashboardService(tenant_schema)
        
        sales_metrics = dashboard_service.get_sales_metrics()
        sales_metrics = _serialize_datetime_objects(sales_metrics)
        
        return Response({
            'success': True,
            'data': sales_metrics,
            'message': 'Sales metrics retrieved successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve sales metrics'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def inventory_metrics_api(request):
    """
    API endpoint to get inventory metrics only.
    
    Returns:
        JSON response with inventory metrics
    """
    try:
        tenant_schema = getattr(request, 'tenant_context', {}).get('schema_name', 'default')
        dashboard_service = TenantDashboardService(tenant_schema)
        
        inventory_metrics = dashboard_service.get_inventory_metrics()
        inventory_metrics = _serialize_datetime_objects(inventory_metrics)
        
        return Response({
            'success': True,
            'data': inventory_metrics,
            'message': 'Inventory metrics retrieved successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve inventory metrics'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gold_price_api(request):
    """
    API endpoint to get current gold prices and trends.
    
    Returns:
        JSON response with gold price data
    """
    try:
        tenant_schema = getattr(request, 'tenant_context', {}).get('schema_name', 'default')
        dashboard_service = TenantDashboardService(tenant_schema)
        
        gold_price_data = dashboard_service.get_gold_price_data()
        gold_price_data = _serialize_datetime_objects(gold_price_data)
        
        return Response({
            'success': True,
            'data': gold_price_data,
            'message': 'Gold price data retrieved successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve gold price data'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def alerts_api(request):
    """
    API endpoint to get alerts and notifications.
    
    Returns:
        JSON response with alerts
    """
    try:
        tenant_schema = getattr(request, 'tenant_context', {}).get('schema_name', 'default')
        dashboard_service = TenantDashboardService(tenant_schema)
        
        alerts = dashboard_service.get_alerts_and_notifications()
        alerts = _serialize_datetime_objects(alerts)
        
        return Response({
            'success': True,
            'data': alerts,
            'message': 'Alerts retrieved successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve alerts'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
def dashboard_health_check(request):
    """
    Simple health check endpoint for dashboard service.
    
    Returns:
        JSON response indicating service health
    """
    try:
        # Test dashboard service initialization
        dashboard_service = TenantDashboardService('health_check')
        
        # Test basic functionality
        fallback_data = dashboard_service._get_fallback_dashboard_data()
        
        return JsonResponse({
            'status': 'healthy',
            'service': 'dashboard',
            'timestamp': dashboard_service._format_currency(1000) if hasattr(dashboard_service, '_format_currency') else 'OK',
            'message': 'Dashboard service is operational'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'service': 'dashboard',
            'error': str(e),
            'message': 'Dashboard service has issues'
        }, status=500)


def _serialize_datetime_objects(data):
    """
    Recursively serialize datetime objects in nested dictionaries and lists.
    
    Args:
        data: Dictionary, list, or other data structure
        
    Returns:
        Data structure with datetime objects converted to ISO strings
    """
    if isinstance(data, dict):
        return {key: _serialize_datetime_objects(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [_serialize_datetime_objects(item) for item in data]
    elif hasattr(data, 'isoformat'):  # datetime objects
        return data.isoformat()
    else:
        return data