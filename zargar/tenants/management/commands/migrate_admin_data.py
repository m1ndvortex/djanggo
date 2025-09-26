"""
Management command to migrate existing admin data to unified system.
This command ensures data integrity during the admin consolidation process.
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.conf import settings
from zargar.tenants.admin_models import (
    SuperAdmin, SuperAdminSession, TenantAccessLog, 
    SubscriptionPlan, TenantInvoice, BillingCycle
)
from zargar.tenants.models import Tenant
import json

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate existing admin data to unified system and ensure data integrity'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without making changes',
        )
        parser.add_argument(
            '--backup-data',
            action='store_true',
            help='Create backup of existing data before migration',
        )
        parser.add_argument(
            '--clean-obsolete',
            action='store_true',
            help='Clean up obsolete database tables and migrations',
        )
        parser.add_argument(
            '--verify-only',
            action='store_true',
            help='Only verify data integrity without migration',
        )
    
    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.backup_data = options['backup_data']
        self.clean_obsolete = options['clean_obsolete']
        self.verify_only = options['verify_only']
        
        self.stdout.write(
            self.style.SUCCESS('Starting admin data migration and integrity check...')
        )
        
        try:
            if self.backup_data:
                self.create_data_backup()
            
            if not self.verify_only:
                self.migrate_superadmin_data()
                self.migrate_session_data()
                self.migrate_audit_logs()
                self.migrate_system_settings()
                
                if self.clean_obsolete:
                    self.clean_obsolete_data()
            
            self.verify_data_integrity()
            self.validate_system_performance()
            
            if not self.dry_run:
                self.stdout.write(
                    self.style.SUCCESS('✅ Admin data migration completed successfully!')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('🔍 Dry run completed - no changes made')
                )
                
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            raise CommandError(f"Migration failed: {str(e)}")
    
    def create_data_backup(self):
        """Create backup of existing admin data."""
        self.stdout.write('📦 Creating data backup...')
        
        backup_data = {
            'timestamp': timezone.now().isoformat(),
            'superadmins': [],
            'sessions': [],
            'audit_logs': [],
            'tenants': [],
            'django_sessions': []
        }
        
        # Backup SuperAdmin data
        for admin in SuperAdmin.objects.all():
            backup_data['superadmins'].append({
                'id': admin.id,
                'username': admin.username,
                'email': admin.email,
                'first_name': admin.first_name,
                'last_name': admin.last_name,
                'persian_first_name': admin.persian_first_name,
                'persian_last_name': admin.persian_last_name,
                'phone_number': admin.phone_number,
                'is_active': admin.is_active,
                'is_staff': admin.is_staff,
                'is_superuser': admin.is_superuser,
                'date_joined': admin.date_joined.isoformat(),
                'last_login': admin.last_login.isoformat() if admin.last_login else None,
                'theme_preference': admin.theme_preference,
                'is_2fa_enabled': admin.is_2fa_enabled,
                'can_create_tenants': admin.can_create_tenants,
                'can_suspend_tenants': admin.can_suspend_tenants,
                'can_access_all_data': admin.can_access_all_data,
                'last_tenant_access': admin.last_tenant_access.isoformat() if admin.last_tenant_access else None,
            })
        
        # Backup SuperAdmin sessions
        for session in SuperAdminSession.objects.all():
            backup_data['sessions'].append({
                'id': session.id,
                'super_admin_id': session.super_admin.id,
                'tenant_schema': session.tenant_schema,
                'session_key': session.session_key,
                'ip_address': str(session.ip_address) if session.ip_address else None,
                'user_agent': session.user_agent,
                'access_time': session.access_time.isoformat(),
                'is_active': session.is_active,
            })
        
        # Backup audit logs
        for log in TenantAccessLog.objects.all()[:1000]:  # Limit to recent 1000 logs
            backup_data['audit_logs'].append({
                'id': log.id,
                'user_type': log.user_type,
                'user_id': log.user_id,
                'username': log.username,
                'tenant_schema': log.tenant_schema,
                'tenant_name': log.tenant_name,
                'action': log.action,
                'model_name': log.model_name,
                'object_id': log.object_id,
                'details': log.details,
                'ip_address': str(log.ip_address) if log.ip_address else None,
                'user_agent': log.user_agent,
                'request_path': log.request_path,
                'request_method': log.request_method,
                'timestamp': log.timestamp.isoformat(),
                'success': log.success,
                'error_message': log.error_message,
            })
        
        # Backup tenant data
        for tenant in Tenant.objects.all():
            backup_data['tenants'].append({
                'id': tenant.id,
                'schema_name': tenant.schema_name,
                'name': tenant.name,
                'created_on': tenant.created_on.isoformat(),
                'is_active': tenant.is_active,
                'owner_name': tenant.owner_name,
                'owner_email': tenant.owner_email,
                'phone_number': tenant.phone_number,
                'address': tenant.address,
                'subscription_plan': tenant.subscription_plan,
            })
        
        # Backup Django sessions
        for session in Session.objects.all():
            backup_data['django_sessions'].append({
                'session_key': session.session_key,
                'session_data': session.session_data,
                'expire_date': session.expire_date.isoformat(),
            })
        
        # Save backup to file
        backup_filename = f"admin_data_backup_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = settings.BASE_DIR / 'backups' / backup_filename
        backup_path.parent.mkdir(exist_ok=True)
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Backup created: {backup_path}')
        )
        
        return backup_path
    
    def migrate_superadmin_data(self):
        """Migrate existing SuperAdmin data to unified system."""
        self.stdout.write('👤 Migrating SuperAdmin data...')
        
        superadmins = SuperAdmin.objects.all()
        migrated_count = 0
        
        for admin in superadmins:
            if self.dry_run:
                self.stdout.write(f'  Would migrate: {admin.username}')
            else:
                # Ensure all required fields are set for unified system
                updated = False
                
                # Set default theme if not set
                if not admin.theme_preference:
                    admin.theme_preference = 'light'
                    updated = True
                
                # Ensure permissions are set (handle both None and False cases)
                if not admin.can_create_tenants:
                    admin.can_create_tenants = True
                    updated = True
                
                if not admin.can_suspend_tenants:
                    admin.can_suspend_tenants = True
                    updated = True
                
                if not admin.can_access_all_data:
                    admin.can_access_all_data = True
                    updated = True
                
                if updated:
                    admin.save()
                    self.stdout.write(f'  ✅ Updated: {admin.username}')
                else:
                    self.stdout.write(f'  ✓ Already current: {admin.username}')
            
            migrated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Migrated {migrated_count} SuperAdmin records')
        )
    
    def migrate_session_data(self):
        """Migrate existing session data to unified system."""
        self.stdout.write('🔐 Migrating session data...')
        
        # Clean up expired Django sessions
        expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
        expired_count = expired_sessions.count()
        
        if not self.dry_run:
            expired_sessions.delete()
        
        self.stdout.write(f'  🗑️ Cleaned up {expired_count} expired sessions')
        
        # Validate SuperAdmin sessions
        active_sessions = SuperAdminSession.objects.filter(is_active=True)
        validated_count = 0
        
        for session in active_sessions:
            if self.dry_run:
                self.stdout.write(f'  Would validate: {session.super_admin.username} session')
            else:
                # Check if session is still valid
                if session.access_time < timezone.now() - timezone.timedelta(hours=24):
                    session.is_active = False
                    session.save()
                    self.stdout.write(f'  🔒 Deactivated old session: {session.super_admin.username}')
                else:
                    self.stdout.write(f'  ✓ Valid session: {session.super_admin.username}')
            
            validated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Validated {validated_count} SuperAdmin sessions')
        )
    
    def migrate_audit_logs(self):
        """Migrate existing audit logs to unified system."""
        self.stdout.write('📋 Migrating audit logs...')
        
        # Ensure audit logs have proper indexing
        total_logs = TenantAccessLog.objects.count()
        
        if total_logs > 0:
            # Check for logs without proper tenant information
            incomplete_logs = TenantAccessLog.objects.filter(
                tenant_name__isnull=True
            ).exclude(tenant_schema='public')
            
            updated_count = 0
            for log in incomplete_logs[:100]:  # Process in batches
                if self.dry_run:
                    self.stdout.write(f'  Would update log: {log.id}')
                else:
                    try:
                        tenant = Tenant.objects.get(schema_name=log.tenant_schema)
                        log.tenant_name = tenant.name
                        log.save()
                        updated_count += 1
                    except Tenant.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'  ⚠️ Tenant not found for schema: {log.tenant_schema}')
                        )
            
            if updated_count > 0:
                self.stdout.write(f'  ✅ Updated {updated_count} audit log records')
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Processed {total_logs} audit log records')
        )
    
    def migrate_system_settings(self):
        """Migrate system settings to unified system."""
        self.stdout.write('⚙️ Migrating system settings...')
        
        # Ensure all tenants have proper subscription plans
        tenants_without_plans = Tenant.objects.filter(subscription_plan_fk__isnull=True)
        
        if tenants_without_plans.exists():
            # Create default subscription plan if it doesn't exist
            default_plan, created = SubscriptionPlan.objects.get_or_create(
                plan_type='basic',
                defaults={
                    'name': 'Basic Plan',
                    'name_persian': 'پلن پایه',
                    'monthly_price_toman': 500000,  # 500,000 Toman
                    'max_users': 5,
                    'max_inventory_items': 1000,
                    'max_customers': 500,
                    'max_monthly_transactions': 1000,
                    'max_storage_gb': 5,
                    'features': {
                        'pos_system': True,
                        'inventory_management': True,
                        'customer_management': True,
                        'accounting_system': False,
                        'gold_installment': False,
                        'reporting': True,
                        'backup_restore': True,
                        'multi_user': True,
                        'mobile_app': False,
                        'priority_support': False,
                    },
                    'is_active': True,
                }
            )
            
            if created:
                self.stdout.write('  ✅ Created default subscription plan')
            
            # Assign default plan to tenants without plans
            updated_count = 0
            for tenant in tenants_without_plans:
                if self.dry_run:
                    self.stdout.write(f'  Would assign plan to: {tenant.name}')
                else:
                    tenant.subscription_plan_fk = default_plan
                    tenant.save()
                    updated_count += 1
            
            if not self.dry_run:
                self.stdout.write(f'  ✅ Assigned plans to {updated_count} tenants')
        
        self.stdout.write(
            self.style.SUCCESS('✅ System settings migration completed')
        )
    
    def clean_obsolete_data(self):
        """Clean up obsolete database tables and unused migrations."""
        self.stdout.write('🧹 Cleaning up obsolete data...')
        
        with connection.cursor() as cursor:
            # Check for obsolete tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE '%_old' 
                OR table_name LIKE '%_backup'
                OR table_name LIKE '%_deprecated'
            """)
            
            obsolete_tables = cursor.fetchall()
            
            for table in obsolete_tables:
                table_name = table[0]
                if self.dry_run:
                    self.stdout.write(f'  Would drop table: {table_name}')
                else:
                    cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
                    self.stdout.write(f'  🗑️ Dropped table: {table_name}')
        
        # Clean up old migration records (keep recent ones)
        if not self.dry_run:
            from django.db.migrations.recorder import MigrationRecorder
            recorder = MigrationRecorder(connection)
            
            # Keep only the last 10 migrations per app
            apps_to_clean = ['tenants', 'admin_panel', 'core']
            for app in apps_to_clean:
                migrations = recorder.migration_qs.filter(app=app).order_by('-id')
                if migrations.count() > 10:
                    old_migrations = migrations[10:]
                    old_count = old_migrations.count()
                    old_migrations.delete()
                    self.stdout.write(f'  🗑️ Cleaned {old_count} old {app} migrations')
        
        self.stdout.write(
            self.style.SUCCESS('✅ Obsolete data cleanup completed')
        )
    
    def verify_data_integrity(self):
        """Verify data integrity after migration."""
        self.stdout.write('🔍 Verifying data integrity...')
        
        issues = []
        
        # Check SuperAdmin data integrity
        superadmins = SuperAdmin.objects.all()
        for admin in superadmins:
            if not admin.username:
                issues.append(f'SuperAdmin {admin.id} missing username')
            if not admin.email:
                issues.append(f'SuperAdmin {admin.id} missing email')
            if admin.theme_preference not in ['light', 'dark']:
                issues.append(f'SuperAdmin {admin.username} has invalid theme preference')
        
        # Check tenant data integrity
        tenants = Tenant.objects.all()
        for tenant in tenants:
            if not tenant.schema_name:
                issues.append(f'Tenant {tenant.id} missing schema_name')
            if not tenant.name:
                issues.append(f'Tenant {tenant.id} missing name')
            if tenant.schema_name != 'public' and not tenant.subscription_plan_fk:
                issues.append(f'Tenant {tenant.name} missing subscription plan')
        
        # Check audit log integrity
        recent_logs = TenantAccessLog.objects.filter(
            timestamp__gte=timezone.now() - timezone.timedelta(days=7)
        )
        for log in recent_logs[:100]:  # Check recent logs
            if not log.user_type:
                issues.append(f'Audit log {log.id} missing user_type')
            if not log.action:
                issues.append(f'Audit log {log.id} missing action')
            if not log.tenant_schema:
                issues.append(f'Audit log {log.id} missing tenant_schema')
        
        # Check session integrity
        active_sessions = SuperAdminSession.objects.filter(is_active=True)
        for session in active_sessions:
            if not session.super_admin:
                issues.append(f'Session {session.id} missing super_admin reference')
            if not session.tenant_schema:
                issues.append(f'Session {session.id} missing tenant_schema')
        
        # Report results
        if issues:
            self.stdout.write(
                self.style.ERROR(f'❌ Found {len(issues)} data integrity issues:')
            )
            for issue in issues:
                self.stdout.write(f'  - {issue}')
        else:
            self.stdout.write(
                self.style.SUCCESS('✅ Data integrity verification passed')
            )
        
        return len(issues) == 0
    
    def validate_system_performance(self):
        """Validate system performance after migration."""
        self.stdout.write('⚡ Validating system performance...')
        
        import time
        
        # Test database query performance
        start_time = time.time()
        SuperAdmin.objects.all().count()
        admin_query_time = time.time() - start_time
        
        start_time = time.time()
        Tenant.objects.all().count()
        tenant_query_time = time.time() - start_time
        
        start_time = time.time()
        TenantAccessLog.objects.all()[:10]
        log_query_time = time.time() - start_time
        
        # Report performance metrics
        self.stdout.write(f'  📊 SuperAdmin query time: {admin_query_time:.3f}s')
        self.stdout.write(f'  📊 Tenant query time: {tenant_query_time:.3f}s')
        self.stdout.write(f'  📊 Audit log query time: {log_query_time:.3f}s')
        
        # Check for performance issues
        if admin_query_time > 1.0:
            self.stdout.write(
                self.style.WARNING('⚠️ SuperAdmin queries are slow - consider indexing')
            )
        
        if tenant_query_time > 1.0:
            self.stdout.write(
                self.style.WARNING('⚠️ Tenant queries are slow - consider indexing')
            )
        
        if log_query_time > 2.0:
            self.stdout.write(
                self.style.WARNING('⚠️ Audit log queries are slow - consider archiving old logs')
            )
        
        self.stdout.write(
            self.style.SUCCESS('✅ System performance validation completed')
        )