"""
Simple integration test for RBAC system.
Tests the complete RBAC workflow without complex Django test setup.
"""
import os
import sys
import django
from django.conf import settings

# Add the project root to Python path
sys.path.insert(0, '/app')

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from zargar.admin_panel.models import SuperAdminPermission, SuperAdminRole, SuperAdminUserRole
from zargar.admin_panel.services import RBACService
from zargar.admin_panel.rbac import RBACMiddleware
from zargar.tenants.admin_models import SuperAdmin


def test_rbac_complete_workflow():
    """Test complete RBAC workflow."""
    print("Testing RBAC complete workflow...")
    
    # 1. Test permissions exist
    permissions_count = SuperAdminPermission.objects.count()
    print(f"✓ Found {permissions_count} permissions")
    assert permissions_count > 0, "No permissions found"
    
    # 2. Test roles exist
    roles_count = SuperAdminRole.objects.count()
    print(f"✓ Found {roles_count} roles")
    assert roles_count > 0, "No roles found"
    
    # 3. Test creating a custom role
    import uuid
    role_name = f'Test Custom Role {uuid.uuid4().hex[:8]}'
    custom_role = RBACService.create_role(
        name=role_name,
        name_persian='نقش سفارشی تست',
        description='Test role for integration testing',
        permissions=['dashboard.view', 'tenants.view'],
        created_by_id=1,
        created_by_username='test_admin'
    )
    print(f"✓ Created custom role: {custom_role.name}")
    assert custom_role.permissions.count() == 2, "Role should have 2 permissions"
    
    # 4. Test creating a user
    username = f'rbac_test_user_{uuid.uuid4().hex[:8]}'
    test_user = SuperAdmin.objects.create_user(
        username=username,
        email=f'rbac_test_{uuid.uuid4().hex[:8]}@example.com',
        password='testpass123'
    )
    print(f"✓ Created test user: {test_user.username}")
    
    # 5. Test assigning role to user
    user_role = RBACService.assign_role_to_user(
        user_id=test_user.id,
        username=test_user.username,
        role_id=custom_role.id,
        assigned_by_id=1,
        assigned_by_username='test_admin'
    )
    print(f"✓ Assigned role to user: {user_role}")
    assert user_role.is_active, "User role should be active"
    
    # 6. Test permission checking
    has_dashboard = RBACService.user_has_permission(test_user.id, 'dashboard.view')
    has_tenants = RBACService.user_has_permission(test_user.id, 'tenants.view')
    has_delete = RBACService.user_has_permission(test_user.id, 'tenants.delete')
    
    print(f"✓ User has dashboard.view: {has_dashboard}")
    print(f"✓ User has tenants.view: {has_tenants}")
    print(f"✓ User has tenants.delete: {has_delete}")
    
    assert has_dashboard, "User should have dashboard.view permission"
    assert has_tenants, "User should have tenants.view permission"
    assert not has_delete, "User should NOT have tenants.delete permission"
    
    # 7. Test middleware
    middleware = RBACMiddleware(None)
    is_super_admin = middleware.is_super_admin(test_user)
    user_permissions = middleware.get_user_permissions(test_user)
    
    print(f"✓ Middleware recognizes super admin: {is_super_admin}")
    print(f"✓ Middleware found {len(user_permissions)} permissions")
    
    assert is_super_admin, "Middleware should recognize SuperAdmin user"
    assert 'dashboard.view' in user_permissions, "User permissions should include dashboard.view"
    assert 'tenants.view' in user_permissions, "User permissions should include tenants.view"
    
    # 8. Test role revocation
    revoke_result = RBACService.revoke_role_from_user(
        user_id=test_user.id,
        role_id=custom_role.id,
        revoked_by_id=1,
        revoked_by_username='test_admin',
        reason='Integration test cleanup'
    )
    print(f"✓ Revoked role from user: {revoke_result}")
    assert revoke_result, "Role revocation should succeed"
    
    # 9. Test permissions after revocation
    has_dashboard_after = RBACService.user_has_permission(test_user.id, 'dashboard.view')
    print(f"✓ User has dashboard.view after revocation: {has_dashboard_after}")
    assert not has_dashboard_after, "User should NOT have permissions after revocation"
    
    # 10. Test statistics
    stats = RBACService.get_role_statistics()
    print(f"✓ Role statistics: {stats}")
    assert stats['total_roles'] > 0, "Should have roles"
    assert stats['total_permissions'] > 0, "Should have permissions"
    
    print("✅ All RBAC integration tests passed!")
    
    # Cleanup
    test_user.delete()
    custom_role.delete()
    print("✓ Cleanup completed")


if __name__ == '__main__':
    try:
        test_rbac_complete_workflow()
        print("\n🎉 RBAC Integration Test SUCCESSFUL!")
    except Exception as e:
        print(f"\n❌ RBAC Integration Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)