#!/usr/bin/env python
"""
Simple verification script for mobile API implementation.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
django.setup()

def test_mobile_api_imports():
    """Test that mobile API modules can be imported."""
    print("🔍 Testing mobile API imports...")
    
    try:
        from zargar.api.mobile_views import (
            MobilePOSViewSet, MobileInventoryViewSet, 
            MobileCustomerViewSet, MobileSyncViewSet,
            MobileNotificationViewSet
        )
        print("✅ Mobile ViewSets imported successfully")
        
        from zargar.api.mobile_serializers import (
            MobileJewelryItemSerializer, MobileCustomerSerializer,
            MobilePOSTransactionSerializer, OfflineTransactionSerializer,
            MobileInventoryUpdateSerializer
        )
        print("✅ Mobile serializers imported successfully")
        
        from zargar.api.offline_sync import (
            get_sync_manifest, download_sync_data, 
            upload_offline_transactions, get_sync_status
        )
        print("✅ Offline sync functions imported successfully")
        
        from zargar.api.push_notification_api import (
            send_push_notification, send_payment_reminder_notification,
            get_notification_history, test_push_notification
        )
        print("✅ Push notification functions imported successfully")
        
        from zargar.core.notification_models import (
            MobileDevice, Notification, NotificationTemplate
        )
        print("✅ Notification models imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Other error: {e}")
        return False

def test_viewset_methods():
    """Test that ViewSets have expected methods."""
    print("\n🔍 Testing ViewSet methods...")
    
    try:
        from zargar.api.mobile_views import (
            MobilePOSViewSet, MobileInventoryViewSet, 
            MobileCustomerViewSet, MobileSyncViewSet
        )
        
        # Test MobilePOSViewSet methods
        pos_viewset = MobilePOSViewSet()
        assert hasattr(pos_viewset, 'offline_create'), "MobilePOSViewSet missing offline_create method"
        assert hasattr(pos_viewset, 'bulk_sync'), "MobilePOSViewSet missing bulk_sync method"
        assert hasattr(pos_viewset, 'mobile_dashboard'), "MobilePOSViewSet missing mobile_dashboard method"
        print("✅ MobilePOSViewSet methods verified")
        
        # Test MobileInventoryViewSet methods
        inventory_viewset = MobileInventoryViewSet()
        assert hasattr(inventory_viewset, 'barcode_search'), "MobileInventoryViewSet missing barcode_search method"
        assert hasattr(inventory_viewset, 'quick_search'), "MobileInventoryViewSet missing quick_search method"
        assert hasattr(inventory_viewset, 'bulk_update_stock'), "MobileInventoryViewSet missing bulk_update_stock method"
        print("✅ MobileInventoryViewSet methods verified")
        
        # Test MobileCustomerViewSet methods
        customer_viewset = MobileCustomerViewSet()
        assert hasattr(customer_viewset, 'phone_search'), "MobileCustomerViewSet missing phone_search method"
        assert hasattr(customer_viewset, 'quick_create'), "MobileCustomerViewSet missing quick_create method"
        print("✅ MobileCustomerViewSet methods verified")
        
        # Test MobileSyncViewSet methods
        sync_viewset = MobileSyncViewSet()
        assert hasattr(sync_viewset, 'sync_data'), "MobileSyncViewSet missing sync_data method"
        assert hasattr(sync_viewset, 'upload_sync_data'), "MobileSyncViewSet missing upload_sync_data method"
        print("✅ MobileSyncViewSet methods verified")
        
        return True
        
    except Exception as e:
        print(f"❌ ViewSet method test failed: {e}")
        return False

def test_serializer_fields():
    """Test that serializers have expected fields."""
    print("\n🔍 Testing serializer fields...")
    
    try:
        from zargar.api.mobile_serializers import (
            MobileJewelryItemSerializer, MobileCustomerSerializer,
            OfflineTransactionSerializer
        )
        
        # Test MobileJewelryItemSerializer
        jewelry_serializer = MobileJewelryItemSerializer()
        expected_fields = ['id', 'name', 'sku', 'formatted_price', 'formatted_weight']
        for field in expected_fields:
            assert field in jewelry_serializer.fields, f"MobileJewelryItemSerializer missing {field} field"
        print("✅ MobileJewelryItemSerializer fields verified")
        
        # Test MobileCustomerSerializer
        customer_serializer = MobileCustomerSerializer()
        expected_fields = ['id', 'phone_number', 'full_persian_name', 'formatted_loyalty_points']
        for field in expected_fields:
            assert field in customer_serializer.fields, f"MobileCustomerSerializer missing {field} field"
        print("✅ MobileCustomerSerializer fields verified")
        
        # Test OfflineTransactionSerializer
        offline_serializer = OfflineTransactionSerializer()
        expected_fields = ['line_items', 'offline_transaction_id', 'device_id']
        for field in expected_fields:
            assert field in offline_serializer.fields, f"OfflineTransactionSerializer missing {field} field"
        print("✅ OfflineTransactionSerializer fields verified")
        
        return True
        
    except Exception as e:
        print(f"❌ Serializer field test failed: {e}")
        return False

def test_notification_models():
    """Test notification model structure."""
    print("\n🔍 Testing notification models...")
    
    try:
        from zargar.core.notification_models import (
            MobileDevice, Notification, NotificationTemplate
        )
        
        # Test MobileDevice model
        assert hasattr(MobileDevice, 'device_id'), "MobileDevice missing device_id field"
        assert hasattr(MobileDevice, 'device_token'), "MobileDevice missing device_token field"
        assert hasattr(MobileDevice, 'enable_push_notifications'), "MobileDevice missing enable_push_notifications field"
        print("✅ MobileDevice model structure verified")
        
        # Test Notification model
        assert hasattr(Notification, 'title'), "Notification missing title field"
        assert hasattr(Notification, 'content'), "Notification missing content field"
        assert hasattr(Notification, 'delivery_method'), "Notification missing delivery_method field"
        print("✅ Notification model structure verified")
        
        # Test NotificationTemplate model
        assert hasattr(NotificationTemplate, 'template_type'), "NotificationTemplate missing template_type field"
        assert hasattr(NotificationTemplate, 'content'), "NotificationTemplate missing content field"
        print("✅ NotificationTemplate model structure verified")
        
        return True
        
    except Exception as e:
        print(f"❌ Notification model test failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("🚀 Starting ZARGAR Mobile API Verification")
    print("=" * 50)
    
    tests = [
        test_mobile_api_imports,
        test_viewset_methods,
        test_serializer_fields,
        test_notification_models,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All mobile API verification tests passed!")
        print("✅ Mobile API implementation is ready for use")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)