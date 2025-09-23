#!/usr/bin/env python
"""
Final verification script for admin data migration.
This script verifies that all admin functionality works correctly after migration.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django.core.management import call_command
from django.utils import timezone
from zargar.tenants.admin_models import (
    SuperAdmin, SuperAdminSession, TenantAccessLog, 
    SubscriptionPlan, TenantInvoice
)
from zargar.tenants.models import Tenant
from io import StringIO


def verify_superadmin_functionality():
    """Verify SuperAdmin functionality."""
    print("🔍 Verifying SuperAdmin functionality...")
    
    # Check SuperAdmin exists and has correct settings
    superadmins = SuperAdmin.objects.all()
    if not superadmins.exists():
        print("❌ No SuperAdmin users found!")
        return False
    
    for admin in superadmins:
        if not admin.theme_preference:
            print(f"❌ SuperAdmin {admin.username} missing theme preference")
            return False
        
        if not admin.can_create_tenants:
            print(f"❌ SuperAdmin {admin.username} cannot create tenants")
            return False
        
        if not admin.can_suspend_tenants:
            print(f"❌ SuperAdmin {admin.username} cannot suspend tenants")
            return False
        
        if not admin.can_access_all_data:
            print(f"❌ SuperAdmin {admin.username} cannot access all data")
            return False
        
        print(f"✅ SuperAdmin {admin.username} configured correctly")
    
    return True


def verify_subscription_plans():
    """Verify subscription plans."""
    print("💰 Verifying subscription plans...")
    
    # Check default plan exists
    try:
        default_plan = SubscriptionPlan.objects.get(plan_type='basic')
        print(f"✅ Default plan exists: {default_plan.name_persian}")
        
        # Verify plan has required fields
        if not default_plan.monthly_price_toman:
            print("❌ Default plan missing price")
            return False
        
        if not default_plan.features:
            print("❌ Default plan missing features")
            return False
        
        print(f"✅ Default plan configured: {default_plan.monthly_price_toman} تومان")
        return True
        
    except SubscriptionPlan.DoesNotExist:
        print("❌ Default subscription plan not found!")
        return False


def verify_tenant_assignments():
    """Verify tenant plan assignments."""
    print("🏢 Verifying tenant plan assignments...")
    
    tenants = Tenant.objects.exclude(schema_name='public')
    unassigned_tenants = tenants.filter(subscription_plan_fk__isnull=True)
    
    if unassigned_tenants.exists():
        print(f"❌ {unassigned_tenants.count()} tenants without subscription plans")
        for tenant in unassigned_tenants:
            print(f"  - {tenant.name}")
        return False
    
    print(f"✅ All {tenants.count()} tenants have subscription plans assigned")
    return True


def verify_audit_logging():
    """Verify audit logging functionality."""
    print("📋 Verifying audit logging...")
    
    # Test creating an audit log entry
    admin = SuperAdmin.objects.first()
    if not admin:
        print("❌ No SuperAdmin for audit log test")
        return False
    
    # Create test audit log
    log = TenantAccessLog.log_action(
        user=admin,
        tenant_schema='public',
        action='test_migration_verification',
        model_name='TestModel',
        object_id='test_id',
        details={'test': 'migration_verification'},
        success=True
    )
    
    if not log:
        print("❌ Failed to create audit log entry")
        return False
    
    print(f"✅ Audit logging working: {log.id}")
    
    # Clean up test log
    log.delete()
    return True


def verify_session_management():
    """Verify session management."""
    print("🔐 Verifying session management...")
    
    admin = SuperAdmin.objects.first()
    if not admin:
        print("❌ No SuperAdmin for session test")
        return False
    
    # Create test session
    session = SuperAdminSession.objects.create(
        super_admin=admin,
        tenant_schema='public',
        session_key='test_migration_session',
        is_active=True
    )
    
    if not session:
        print("❌ Failed to create session")
        return False
    
    print(f"✅ Session management working: {session.id}")
    
    # Clean up test session
    session.delete()
    return True


def verify_data_integrity():
    """Verify overall data integrity."""
    print("🔍 Running data integrity verification...")
    
    out = StringIO()
    try:
        call_command('migrate_admin_data', '--verify-only', stdout=out)
        output = out.getvalue()
        
        if 'Data integrity verification passed' in output:
            print("✅ Data integrity verification passed")
            return True
        else:
            print("❌ Data integrity issues found:")
            print(output)
            return False
            
    except Exception as e:
        print(f"❌ Data integrity verification failed: {e}")
        return False


def verify_performance():
    """Verify system performance."""
    print("⚡ Verifying system performance...")
    
    import time
    
    # Test query performance
    start_time = time.time()
    list(SuperAdmin.objects.all())
    admin_time = time.time() - start_time
    
    start_time = time.time()
    list(Tenant.objects.all())
    tenant_time = time.time() - start_time
    
    start_time = time.time()
    list(TenantAccessLog.objects.all()[:10])
    log_time = time.time() - start_time
    
    print(f"📊 Query performance:")
    print(f"  - SuperAdmin: {admin_time:.3f}s")
    print(f"  - Tenant: {tenant_time:.3f}s")
    print(f"  - Audit logs: {log_time:.3f}s")
    
    # Check for performance issues
    if admin_time > 1.0 or tenant_time > 1.0 or log_time > 2.0:
        print("⚠️ Performance issues detected")
        return False
    
    print("✅ Performance verification passed")
    return True


def main():
    """Run all verification tests."""
    print("🚀 Starting admin migration verification...")
    print("=" * 50)
    
    tests = [
        verify_superadmin_functionality,
        verify_subscription_plans,
        verify_tenant_assignments,
        verify_audit_logging,
        verify_session_management,
        verify_data_integrity,
        verify_performance,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Verification Results:")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📈 Success Rate: {(passed / (passed + failed)) * 100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All verification tests passed!")
        print("✅ Admin data migration completed successfully!")
        return 0
    else:
        print(f"\n⚠️ {failed} verification tests failed!")
        print("❌ Please review the issues above before proceeding.")
        return 1


if __name__ == '__main__':
    sys.exit(main())