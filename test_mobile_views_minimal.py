#!/usr/bin/env python
"""
Minimal test for mobile views to identify the issue.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
django.setup()

print("Testing minimal mobile views...")

try:
    from rest_framework import viewsets, status
    from rest_framework.decorators import action
    from rest_framework.response import Response
    from zargar.core.permissions import TenantPermission, POSPermission
    from zargar.api.throttling import TenantAPIThrottle
    from zargar.api.mobile_serializers import MobilePOSTransactionSerializer
    
    print("✅ All imports successful")
    
    class TestMobilePOSViewSet(viewsets.ModelViewSet):
        """Test mobile POS ViewSet."""
        serializer_class = MobilePOSTransactionSerializer
        permission_classes = [TenantPermission, POSPermission]
        throttle_classes = [TenantAPIThrottle]
        
        @action(detail=False, methods=['get'])
        def test_action(self, request):
            return Response({'success': True})
    
    print("✅ Test ViewSet created successfully")
    print(f"ViewSet methods: {[method for method in dir(TestMobilePOSViewSet) if not method.startswith('_')]}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()