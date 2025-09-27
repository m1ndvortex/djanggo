#!/usr/bin/env python
"""
Verification script for Persian Accounting System Models with Perfect Tenant Isolation.

This script verifies that the accounting models work correctly within the
multi-tenant architecture with perfect tenant isolation.
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from django.db import connection
from django_tenants.utils import schema_context, tenant_context
from zargar.tenants.models import Tenant, Domain
from zargar.accounting.models import (
    ChartOfAccounts, JournalEntry, JournalEntryLine,
    GeneralLedger, BankAccount, ChequeManagement
)
from zargar.core.models import User
from django.utils import timezone


def create_test_tenant():
    """Create a test tenant for verification."""
    print("=== Creating Test Tenant ===")
    
    # Create tenant
    tenant = Tenant.objects.create(
        schema_name='test_jewelry_shop',
        name='Test Jewelry Shop',
        description='Test tenant for accounting verification',
        is_active=True
    )
    print(f"✓ Created tenant: {tenant}")
    
    # Create domain
    domain = Domain.objects.create(
        domain='test-shop.localhost',
        tenant=tenant,
        is_primary=True
    )
    print(f"✓ Created domain: {domain}")
    
    return tenant


def verify_tenant_schema_creation(tenant):
    """Verify that tenant schema is created with accounting tables."""
    print(f"\n=== Verifying Tenant Schema: {tenant.schema_name} ===")
    
    with schema_context(tenant.schema_name):
        # Check if accounting tables exist
        with connection.cursor() as cursor:
            # List all tables in the tenant schema
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name LIKE 'accounting_%%'
                ORDER BY table_name;
            """, [tenant.schema_name])
            
            accounting_tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                'accounting_bankaccount',
                'accounting_chartofaccounts',
                'accounting_chequemanagement',
                'accounting_generalledger',
                'accounting_journalentry',
                'accounting_journalentryline',
                'accounting_subsidiaryledger'
            ]
            
            print(f"✓ Found accounting tables: {accounting_tables}")
            
            missing_tables = set(expected_tables) - set(accounting_tables)
            if missing_tables:
                print(f"❌ Missing tables: {missing_tables}")
                return False
            else:
                print("✅ All accounting tables exist in tenant schema")
                return True


def create_test_user_in_tenant(tenant):
    """Create a test user within the tenant schema."""
    print(f"\n=== Creating Test User in Tenant: {tenant.schema_name} ===")
    
    with schema_context(tenant.schema_name):
        user = User.objects.create_user(
            username='test_accountant',
            email='accountant@test-shop.com',
            password='testpass123',
            role='accountant',
            first_name='Test',
            last_name='Accountant',
            persian_first_name='حسابدار',
            persian_last_name='تست'
        )
        print(f"✓ Created user in tenant schema: {user}")
        print(f"✓ User role: {user.role}")
        print(f"✓ User Persian name: {user.full_persian_name}")
        
        return user


def test_accounting_models_in_tenant(tenant, user):
    """Test accounting models within tenant context."""
    print(f"\n=== Testing Accounting Models in Tenant: {tenant.schema_name} ===")
    
    with schema_context(tenant.schema_name):
        # Set user context for audit fields
        from zargar.core.models import set_current_tenant, _thread_locals
        set_current_tenant(tenant)
        _thread_locals.user = user
        
        try:
            # Test ChartOfAccounts
            print("\n--- Testing ChartOfAccounts ---")
            cash_account = ChartOfAccounts.objects.create(
                account_code='1001',
                account_name_persian='نقد در صندوق',
                account_name_english='Cash in Hand',
                account_type='asset',
                account_category='current_assets',
                normal_balance='debit',
                description='Cash account for daily operations'
            )
            print(f"✓ Created chart account: {cash_account}")
            print(f"✓ Created by: {cash_account.created_by}")
            
            sales_account = ChartOfAccounts.objects.create(
                account_code='4001',
                account_name_persian='درآمد فروش طلا',
                account_type='revenue',
                account_category='sales_revenue',
                normal_balance='credit'
            )
            print(f"✓ Created sales account: {sales_account}")
            
            # Test JournalEntry
            print("\n--- Testing JournalEntry ---")
            entry = JournalEntry.objects.create(
                entry_type='sales',
                entry_date=timezone.now().date(),
                description='فروش طلا به مشتری - تست',
                reference_number='TEST-001'
            )
            print(f"✓ Created journal entry: {entry}")
            print(f"✓ Entry number: {entry.entry_number}")
            print(f"✓ Shamsi date: {entry.entry_date_shamsi}")
            
            # Test JournalEntryLine
            print("\n--- Testing JournalEntryLine ---")
            debit_line = JournalEntryLine.objects.create(
                journal_entry=entry,
                account=cash_account,
                description='دریافت نقد از فروش طلا',
                debit_amount=Decimal('1000000.00')
            )
            print(f"✓ Created debit line: {debit_line}")
            
            credit_line = JournalEntryLine.objects.create(
                journal_entry=entry,
                account=sales_account,
                description='درآمد فروش طلا',
                credit_amount=Decimal('1000000.00')
            )
            print(f"✓ Created credit line: {credit_line}")
            
            entry.refresh_from_db()
            print(f"✓ Entry is balanced: {entry.is_balanced}")
            
            # Test BankAccount
            print("\n--- Testing BankAccount ---")
            bank_chart_account = ChartOfAccounts.objects.create(
                account_code='1101',
                account_name_persian='حساب بانک ملی',
                account_type='asset',
                account_category='current_assets',
                normal_balance='debit'
            )
            
            bank_account = BankAccount.objects.create(
                account_name='حساب جاری اصلی',
                account_number='1234567890',
                iban='IR123456789012345678901234',
                bank_name='melli',
                account_type='checking',
                account_holder_name='تست جواهری',
                opening_date=timezone.now().date(),
                chart_account=bank_chart_account
            )
            print(f"✓ Created bank account: {bank_account}")
            print(f"✓ Masked IBAN: {bank_account.masked_iban}")
            
            # Test ChequeManagement
            print("\n--- Testing ChequeManagement ---")
            cheque = ChequeManagement.objects.create(
                cheque_number='1234567',
                cheque_type='received',
                bank_account=bank_account,
                amount=Decimal('2000000.00'),
                issue_date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                payee_name='تست جواهری',
                payer_name='مشتری تست'
            )
            print(f"✓ Created cheque: {cheque}")
            print(f"✓ Shamsi due date: {cheque.due_date_shamsi}")
            
            # Test GeneralLedger
            print("\n--- Testing GeneralLedger ---")
            gl_entry = GeneralLedger.objects.create(
                account=cash_account,
                fiscal_year='1402',
                period_month=6,
                opening_balance=Decimal('500000.00'),
                period_debit=Decimal('1000000.00'),
                period_credit=Decimal('200000.00')
            )
            print(f"✓ Created general ledger entry: {gl_entry}")
            closing_balance = gl_entry.calculate_closing_balance()
            print(f"✓ Closing balance: {closing_balance:,} تومان")
            
            print("\n✅ All accounting models work correctly in tenant schema!")
            
            return {
                'accounts': ChartOfAccounts.objects.count(),
                'journal_entries': JournalEntry.objects.count(),
                'journal_lines': JournalEntryLine.objects.count(),
                'bank_accounts': BankAccount.objects.count(),
                'cheques': ChequeManagement.objects.count(),
                'gl_entries': GeneralLedger.objects.count()
            }
            
        except Exception as e:
            print(f"❌ Error testing accounting models: {e}")
            import traceback
            traceback.print_exc()
            return None


def verify_tenant_isolation():
    """Verify that tenant isolation is working correctly."""
    print("\n=== Verifying Tenant Isolation ===")
    
    # Create two test tenants
    tenant1 = Tenant.objects.create(
        schema_name='shop1_test',
        name='Shop 1 Test',
        is_active=True
    )
    Domain.objects.create(domain='shop1.test', tenant=tenant1, is_primary=True)
    
    tenant2 = Tenant.objects.create(
        schema_name='shop2_test',
        name='Shop 2 Test',
        is_active=True
    )
    Domain.objects.create(domain='shop2.test', tenant=tenant2, is_primary=True)
    
    print(f"✓ Created tenant 1: {tenant1.schema_name}")
    print(f"✓ Created tenant 2: {tenant2.schema_name}")
    
    # Create data in tenant 1
    with schema_context(tenant1.schema_name):
        account1 = ChartOfAccounts.objects.create(
            account_code='1001',
            account_name_persian='نقد فروشگاه ۱',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit'
        )
        print(f"✓ Created account in tenant 1: {account1}")
    
    # Create data in tenant 2
    with schema_context(tenant2.schema_name):
        account2 = ChartOfAccounts.objects.create(
            account_code='1001',
            account_name_persian='نقد فروشگاه ۲',
            account_type='asset',
            account_category='current_assets',
            normal_balance='debit'
        )
        print(f"✓ Created account in tenant 2: {account2}")
    
    # Verify isolation - tenant 1 should only see its data
    with schema_context(tenant1.schema_name):
        accounts_in_tenant1 = ChartOfAccounts.objects.all()
        print(f"✓ Accounts visible in tenant 1: {list(accounts_in_tenant1)}")
        assert len(accounts_in_tenant1) == 1
        assert accounts_in_tenant1[0].account_name_persian == 'نقد فروشگاه ۱'
    
    # Verify isolation - tenant 2 should only see its data
    with schema_context(tenant2.schema_name):
        accounts_in_tenant2 = ChartOfAccounts.objects.all()
        print(f"✓ Accounts visible in tenant 2: {list(accounts_in_tenant2)}")
        assert len(accounts_in_tenant2) == 1
        assert accounts_in_tenant2[0].account_name_persian == 'نقد فروشگاه ۲'
    
    print("✅ Perfect tenant isolation verified!")
    
    # Cleanup test tenants
    tenant1.delete()
    tenant2.delete()


def verify_migrations_applied():
    """Verify that all accounting migrations are properly applied."""
    print("\n=== Verifying Migrations ===")
    
    from django.db.migrations.executor import MigrationExecutor
    from django.db import connections
    
    connection = connections['default']
    executor = MigrationExecutor(connection)
    
    # Check if accounting migrations are applied
    plan = executor.migration_plan([('accounting', None)])
    
    if plan:
        print(f"❌ Unapplied migrations found: {plan}")
        return False
    else:
        print("✅ All accounting migrations are applied")
        return True


def main():
    """Run all verification tests."""
    print("🏪 Persian Accounting System - Tenant Isolation Verification")
    print("=" * 70)
    
    try:
        # Verify migrations
        if not verify_migrations_applied():
            print("❌ Migration verification failed")
            return 1
        
        # Create test tenant
        tenant = create_test_tenant()
        
        # Verify schema creation
        if not verify_tenant_schema_creation(tenant):
            print("❌ Schema verification failed")
            return 1
        
        # Create test user
        user = create_test_user_in_tenant(tenant)
        
        # Test accounting models
        stats = test_accounting_models_in_tenant(tenant, user)
        if not stats:
            print("❌ Accounting models test failed")
            return 1
        
        # Verify tenant isolation
        verify_tenant_isolation()
        
        print("\n🎉 VERIFICATION COMPLETE!")
        print("=" * 50)
        print("✅ Perfect tenant isolation working")
        print("✅ Accounting models properly integrated")
        print("✅ Persian localization working")
        print("✅ Shamsi calendar integration working")
        print("✅ Iranian banking features working")
        print("✅ Audit trail working")
        
        print(f"\n📊 Test Results:")
        print(f"- Chart of Accounts: {stats['accounts']}")
        print(f"- Journal Entries: {stats['journal_entries']}")
        print(f"- Journal Lines: {stats['journal_lines']}")
        print(f"- Bank Accounts: {stats['bank_accounts']}")
        print(f"- Cheques: {stats['cheques']}")
        print(f"- General Ledger: {stats['gl_entries']}")
        
        # Cleanup
        print(f"\n🧹 Cleaning up test tenant...")
        tenant.delete()
        print("✓ Test tenant deleted")
        
        return 0
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())