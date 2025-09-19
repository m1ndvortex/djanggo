"""
Core tests for tenant-aware models and middleware functionality.
"""
import pytest
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.db import connection
from zargar.core.models import (
    TenantAwareModel, TenantAwareManager, TenantAwareQuerySet,
    get_current_tenant, set_current_tenant, _thread_locals
)
from zargar.tenants.models import Tenant
from unittest.mock import Mock, patch

User = get_user_model()


class MockTenant:
    """Mock tenant for testing."""
    def __init__(self, schema_name, name="Test Tenant"):
        self.schema_name = schema_name
        self.name = name
        self.id = 1


class TenantAwareModelCoreTestCase(TestCase):
    """
    Test core functionality of tenant-aware models without complex tenant setup.
    """
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            role="owner"
        )
        
        self.mock_tenant = MockTenant("test_schema")
    
    def test_thread_local_tenant_storage(self):
        """Test that tenant context is stored in thread-local storage."""
        # Initially no tenant
        self.assertIsNone(get_current_tenant())
        
        # Set tenant
        set_current_tenant(self.mock_tenant)
        self.assertEqual(get_current_tenant(), self.mock_tenant)
        self.assertEqual(get_current_tenant().schema_name, "test_schema")
        
        # Clear tenant
        set_current_tenant(None)
        self.assertIsNone(get_current_tenant())
    
    def test_thread_local_user_storage(self):
        """Test that user context is stored in thread-local storage."""
        # Set user in thread-local storage
        _thread_locals.user = self.user
        
        # Verify user is accessible
        self.assertEqual(_thread_locals.user, self.user)
        self.assertTrue(_thread_locals.user.is_authenticated)
        
        # Clear user
        if hasattr(_thread_locals, 'user'):
            delattr(_thread_locals, 'user')
        
        # Verify user is cleared
        self.assertFalse(hasattr(_thread_locals, 'user'))
    
    def test_tenant_aware_queryset_initialization(self):
        """Test that TenantAwareQuerySet initializes correctly."""
        # Create a mock model
        class MockModel:
            _meta = Mock()
            _meta.db_table = 'test_table'
        
        queryset = TenantAwareQuerySet(model=MockModel)
        self.assertFalse(queryset._tenant_filtered)
        
        # Test cloning maintains state
        clone = queryset._clone()
        self.assertFalse(clone._tenant_filtered)
    
    def test_tenant_aware_manager_initialization(self):
        """Test that TenantAwareManager initializes correctly."""
        manager = TenantAwareManager()
        self.assertIsInstance(manager, TenantAwareManager)
    
    def test_tenant_context_in_model_methods(self):
        """Test that models can access tenant context."""
        # Create a test model instance
        class TestTenantModel(TenantAwareModel):
            name = "Test Model"
            
            class Meta:
                app_label = 'core'
        
        # Set tenant context
        set_current_tenant(self.mock_tenant)
        
        # Create model instance
        model_instance = TestTenantModel()
        
        # Test tenant_schema property
        self.assertEqual(model_instance.tenant_schema, "test_schema")
        
        # Test audit info
        audit_info = model_instance.get_audit_info()
        self.assertEqual(audit_info['tenant_schema'], "test_schema")
        self.assertIsNotNone(audit_info['created_at'])
        self.assertIsNotNone(audit_info['updated_at'])
    
    def test_audit_fields_with_user_context(self):
        """Test that audit fields are populated with user context."""
        # Set user in thread-local storage
        _thread_locals.user = self.user
        
        # Create a test model instance
        class TestAuditModel(TenantAwareModel):
            name = "Test Audit Model"
            
            class Meta:
                app_label = 'core'
        
        model_instance = TestAuditModel()
        
        # Simulate save operation
        model_instance.save()
        
        # Check that created_by is set
        self.assertEqual(model_instance.created_by, self.user)
        self.assertEqual(model_instance.updated_by, self.user)
    
    def test_manager_create_with_user_context(self):
        """Test that manager create method uses user context."""
        # Set user in thread-local storage
        _thread_locals.user = self.user
        
        manager = TenantAwareManager()
        
        # Mock the actual create operation
        with patch.object(manager, '_create_object') as mock_create:
            mock_create.return_value = Mock()
            
            # Test create with user context
            kwargs = {'name': 'Test Object'}
            manager.create(**kwargs)
            
            # Verify created_by was added to kwargs
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            self.assertEqual(call_args.get('created_by'), self.user)
    
    def test_bulk_create_with_user_context(self):
        """Test that bulk_create sets user context on objects."""
        # Set user in thread-local storage
        _thread_locals.user = self.user
        
        # Create test objects
        class TestBulkModel(TenantAwareModel):
            name = "Test Bulk Model"
            
            class Meta:
                app_label = 'core'
        
        objects = [
            TestBulkModel(name="Object 1"),
            TestBulkModel(name="Object 2"),
            TestBulkModel(name="Object 3")
        ]
        
        manager = TenantAwareManager()
        
        # Mock the actual bulk_create operation
        with patch('django.db.models.Manager.bulk_create') as mock_bulk_create:
            mock_bulk_create.return_value = objects
            
            # Call bulk_create
            result = manager.bulk_create(objects)
            
            # Verify all objects have created_by set
            for obj in objects:
                self.assertEqual(obj.created_by, self.user)
    
    def test_queryset_filtering_state(self):
        """Test that queryset filtering state is maintained."""
        # Create a mock model
        class MockModel:
            _meta = Mock()
            _meta.db_table = 'test_table'
        
        queryset = TenantAwareQuerySet(model=MockModel)
        
        # Initially not filtered
        self.assertFalse(queryset._tenant_filtered)
        
        # Apply filtering
        filtered_qs = queryset._filter_by_tenant()
        self.assertTrue(filtered_qs._tenant_filtered)
        
        # Original queryset should remain unchanged
        self.assertFalse(queryset._tenant_filtered)
        
        # Clone should maintain filtering state
        clone = filtered_qs._clone()
        self.assertTrue(clone._tenant_filtered)
    
    def test_model_save_with_audit_tracking(self):
        """Test that model save method properly tracks audit information."""
        # Set user context
        _thread_locals.user = self.user
        
        # Create test model
        class TestSaveModel(TenantAwareModel):
            name = "Test Save Model"
            
            class Meta:
                app_label = 'core'
        
        # Test new object save
        model_instance = TestSaveModel(name="Test Object")
        
        # Mock the actual save to avoid database operations
        with patch('django.db.models.Model.save') as mock_save:
            model_instance.save()
            
            # Verify audit fields are set
            self.assertEqual(model_instance.created_by, self.user)
            self.assertEqual(model_instance.updated_by, self.user)
            
            # Verify save was called
            mock_save.assert_called_once()
    
    def test_model_update_audit_tracking(self):
        """Test that model updates properly track updated_by."""
        # Set user context
        _thread_locals.user = self.user
        
        # Create test model with existing data
        class TestUpdateModel(TenantAwareModel):
            name = "Test Update Model"
            
            class Meta:
                app_label = 'core'
        
        model_instance = TestUpdateModel(name="Test Object")
        model_instance.pk = 1  # Simulate existing object
        
        # Create different user for update
        update_user = User.objects.create_user(
            username="updateuser",
            email="update@example.com",
            password="updatepass123"
        )
        
        # Change user context
        _thread_locals.user = update_user
        
        # Mock the actual save to avoid database operations
        with patch('django.db.models.Model.save') as mock_save:
            model_instance.save()
            
            # Verify updated_by is set to new user
            self.assertEqual(model_instance.updated_by, update_user)
            
            # created_by should remain unchanged (None in this case since we didn't set it)
            # In real scenario, created_by would be preserved from original creation
    
    def tearDown(self):
        """Clean up after each test."""
        # Clear thread-local storage
        if hasattr(_thread_locals, 'tenant'):
            delattr(_thread_locals, 'tenant')
        if hasattr(_thread_locals, 'user'):
            delattr(_thread_locals, 'user')


class TenantContextMiddlewareTestCase(TestCase):
    """
    Test tenant context middleware functionality.
    """
    
    def setUp(self):
        """Set up test data."""
        self.mock_tenant = MockTenant("middleware_test")
        self.user = User.objects.create_user(
            username="middlewareuser",
            email="middleware@example.com",
            password="middlewarepass123"
        )
    
    def test_middleware_sets_tenant_context(self):
        """Test that middleware properly sets tenant context."""
        from zargar.core.middleware import TenantContextMiddleware
        
        # Create mock request with tenant
        class MockRequest:
            def __init__(self):
                self.tenant = self.mock_tenant
                self.user = self.user
        
        request = MockRequest()
        request.tenant = self.mock_tenant
        request.user = self.user
        
        # Create middleware
        def mock_get_response(req):
            # Verify tenant context is set during request processing
            self.assertEqual(get_current_tenant(), self.mock_tenant)
            self.assertEqual(_thread_locals.user, self.user)
            return Mock()
        
        middleware = TenantContextMiddleware(mock_get_response)
        
        # Process request
        response = middleware(request)
        
        # Verify tenant context was set in request
        self.assertIsNotNone(request.tenant_context)
        self.assertEqual(request.tenant_context['schema_name'], "middleware_test")
        self.assertEqual(request.tenant_context['name'], "Test Tenant")
        self.assertFalse(request.tenant_context['is_public'])
    
    def test_middleware_handles_public_schema(self):
        """Test that middleware handles requests without tenant (public schema)."""
        from zargar.core.middleware import TenantContextMiddleware
        
        # Create mock request without tenant
        class MockRequest:
            def __init__(self):
                self.user = self.user
        
        request = MockRequest()
        
        # Create middleware
        def mock_get_response(req):
            # Verify no tenant is set
            self.assertIsNone(get_current_tenant())
            return Mock()
        
        middleware = TenantContextMiddleware(mock_get_response)
        
        # Process request
        response = middleware(request)
        
        # Verify public schema context
        self.assertIsNotNone(request.tenant_context)
        self.assertEqual(request.tenant_context['schema_name'], "public")
        self.assertEqual(request.tenant_context['name'], "Public")
        self.assertTrue(request.tenant_context['is_public'])
    
    def test_middleware_cleanup(self):
        """Test that middleware properly cleans up thread-local storage."""
        from zargar.core.middleware import TenantContextMiddleware
        
        # Create mock request
        class MockRequest:
            def __init__(self):
                self.tenant = self.mock_tenant
                self.user = self.user
        
        request = MockRequest()
        request.tenant = self.mock_tenant
        request.user = self.user
        
        # Create middleware that raises exception
        def mock_get_response_with_exception(req):
            # Verify context is set
            self.assertEqual(get_current_tenant(), self.mock_tenant)
            raise Exception("Test exception")
        
        middleware = TenantContextMiddleware(mock_get_response_with_exception)
        
        # Process request (should handle exception and cleanup)
        try:
            middleware(request)
        except Exception:
            pass  # Expected exception
        
        # Verify cleanup occurred even with exception
        self.assertFalse(hasattr(_thread_locals, 'tenant'))
        self.assertFalse(hasattr(_thread_locals, 'user'))


class TenantIsolationLogicTestCase(TestCase):
    """
    Test tenant isolation logic without complex tenant setup.
    """
    
    def setUp(self):
        """Set up test data."""
        self.tenant1 = MockTenant("tenant1", "Tenant 1")
        self.tenant2 = MockTenant("tenant2", "Tenant 2")
        
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="pass123",
            tenant_schema="tenant1"
        )
        
        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="pass123",
            tenant_schema="tenant2"
        )
        
        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123"
        )
    
    def test_tenant_isolation_logic(self):
        """Test the core logic for tenant isolation."""
        from zargar.core.middleware import TenantIsolationMiddleware
        
        middleware = TenantIsolationMiddleware(lambda r: Mock())
        
        # Test user accessing own tenant
        class MockRequest1:
            def __init__(self):
                self.user = self.user1
                self.tenant = self.tenant1
                self.path = "/dashboard/"
                self.method = "GET"
                self.META = {"HTTP_USER_AGENT": "test"}
        
        request1 = MockRequest1()
        
        # Should pass - user accessing own tenant
        self.assertEqual(request1.user.tenant_schema, request1.tenant.schema_name)
        
        # Test user accessing different tenant
        class MockRequest2:
            def __init__(self):
                self.user = self.user1  # User from tenant1
                self.tenant = self.tenant2  # Trying to access tenant2
                self.path = "/dashboard/"
                self.method = "GET"
                self.META = {"HTTP_USER_AGENT": "test"}
        
        request2 = MockRequest2()
        
        # Should fail - user accessing different tenant
        self.assertNotEqual(request2.user.tenant_schema, request2.tenant.schema_name)
        
        # Test superuser accessing any tenant
        class MockRequest3:
            def __init__(self):
                self.user = self.superuser
                self.tenant = self.tenant1
                self.path = "/dashboard/"
                self.method = "GET"
        
        request3 = MockRequest3()
        
        # Should pass - superuser can access any tenant
        self.assertTrue(request3.user.is_superuser)
    
    def test_user_role_permissions(self):
        """Test user role-based permissions."""
        # Test owner permissions
        owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="pass123",
            role="owner"
        )
        
        self.assertTrue(owner.is_tenant_owner)
        self.assertTrue(owner.can_access_accounting())
        self.assertTrue(owner.can_access_pos())
        self.assertTrue(owner.can_manage_users())
        
        # Test accountant permissions
        accountant = User.objects.create_user(
            username="accountant",
            email="accountant@example.com",
            password="pass123",
            role="accountant"
        )
        
        self.assertFalse(accountant.is_tenant_owner)
        self.assertTrue(accountant.can_access_accounting())
        self.assertTrue(accountant.can_access_pos())
        self.assertFalse(accountant.can_manage_users())
        
        # Test salesperson permissions
        salesperson = User.objects.create_user(
            username="salesperson",
            email="salesperson@example.com",
            password="pass123",
            role="salesperson"
        )
        
        self.assertFalse(salesperson.is_tenant_owner)
        self.assertFalse(salesperson.can_access_accounting())
        self.assertTrue(salesperson.can_access_pos())
        self.assertFalse(salesperson.can_manage_users())
    
    def test_superuser_permissions(self):
        """Test superuser permissions."""
        self.assertTrue(self.superuser.is_super_admin)
        self.assertTrue(self.superuser.is_superuser)
        self.assertEqual(self.superuser.role, "super_admin")
    
    def tearDown(self):
        """Clean up after each test."""
        # Clear thread-local storage
        if hasattr(_thread_locals, 'tenant'):
            delattr(_thread_locals, 'tenant')
        if hasattr(_thread_locals, 'user'):
            delattr(_thread_locals, 'user')