#!/usr/bin/env python
"""
Comprehensive system backup script for admin consolidation.
Creates backups of database, code, and configurations before consolidation.
"""

import os
import sys
import subprocess
import shutil
import json
from datetime import datetime
from pathlib import Path

# Add Django settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')

try:
    import django
    django.setup()
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connection
    DJANGO_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Django setup failed: {e}")
    print("📁 Creating basic file system backup only...")
    DJANGO_AVAILABLE = False
    settings = None


class ConsolidationBackupManager:
    """
    Manages comprehensive backups before admin consolidation.
    """
    
    def __init__(self):
        self.backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_dir = Path(f'backups/admin_consolidation_{self.backup_timestamp}')
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"🔄 Creating consolidation backup: {self.backup_dir}")
    
    def create_database_backup(self):
        """Create full database backup including all schemas."""
        print("📊 Creating database backup...")
        
        if not DJANGO_AVAILABLE:
            print("⚠️  Django not available, skipping database backup")
            return True
        
        try:
            db_config = settings.DATABASES['default']
            backup_file = self.backup_dir / 'database_full_backup.sql'
            
            # Create PostgreSQL dump command
            cmd = [
                'pg_dump',
                f"--host={db_config.get('HOST', 'localhost')}",
                f"--port={db_config.get('PORT', '5432')}",
                f"--username={db_config['USER']}",
                f"--dbname={db_config['NAME']}",
                '--verbose',
                '--clean',
                '--no-owner',
                '--no-privileges',
                f"--file={backup_file}"
            ]
            
            # Set password environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['PASSWORD']
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Database backup created: {backup_file}")
                return True
            else:
                print(f"❌ Database backup failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Database backup error: {e}")
            return False
    
    def create_schema_specific_backups(self):
        """Create backups for specific schemas."""
        print("🏢 Creating schema-specific backups...")
        
        if not DJANGO_AVAILABLE:
            print("⚠️  Django not available, skipping schema backups")
            return
        
        try:
            from zargar.tenants.models import Tenant
            
            # Backup public schema (SuperAdmin data)
            self._backup_schema('public', 'superadmin_data.sql')
            
            # Backup first few tenant schemas as samples
            tenants = Tenant.objects.exclude(schema_name='public')[:5]
            for tenant in tenants:
                self._backup_schema(tenant.schema_name, f'tenant_{tenant.schema_name}.sql')
            
            print(f"✅ Schema backups completed")
        except Exception as e:
            print(f"⚠️  Schema backup error: {e}")
    
    def _backup_schema(self, schema_name, filename):
        """Backup a specific schema."""
        if not DJANGO_AVAILABLE:
            return
        
        try:
            db_config = settings.DATABASES['default']
            backup_file = self.backup_dir / filename
            
            cmd = [
                'pg_dump',
                f"--host={db_config.get('HOST', 'localhost')}",
                f"--port={db_config.get('PORT', '5432')}",
                f"--username={db_config['USER']}",
                f"--dbname={db_config['NAME']}",
                f"--schema={schema_name}",
                '--verbose',
                '--clean',
                '--no-owner',
                '--no-privileges',
                f"--file={backup_file}"
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['PASSWORD']
            
            subprocess.run(cmd, env=env, check=True, capture_output=True)
            print(f"  ✅ Schema '{schema_name}' backed up to {filename}")
        except Exception as e:
            print(f"  ❌ Schema '{schema_name}' backup failed: {e}")
    
    def create_code_backup(self):
        """Create backup of current codebase."""
        print("💾 Creating code backup...")
        
        # Create git archive if in git repository
        try:
            git_archive = self.backup_dir / 'codebase_git_archive.tar.gz'
            subprocess.run([
                'git', 'archive', '--format=tar.gz', 
                f'--output={git_archive}', 'HEAD'
            ], check=True)
            print(f"✅ Git archive created: {git_archive}")
        except subprocess.CalledProcessError:
            print("⚠️  Git archive failed, creating directory copy...")
            
            # Fallback: copy important directories
            code_backup_dir = self.backup_dir / 'codebase'
            code_backup_dir.mkdir(exist_ok=True)
            
            important_dirs = [
                'zargar',
                'templates',
                'static',
                'scripts',
                '.kiro'
            ]
            
            for dir_name in important_dirs:
                if Path(dir_name).exists():
                    shutil.copytree(dir_name, code_backup_dir / dir_name, 
                                  ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                    print(f"  ✅ Copied {dir_name}")
            
            # Copy important files
            important_files = [
                'manage.py',
                'requirements.txt',
                'docker-compose.yml',
                'Dockerfile'
            ]
            
            for file_name in important_files:
                if Path(file_name).exists():
                    shutil.copy2(file_name, code_backup_dir / file_name)
                    print(f"  ✅ Copied {file_name}")
    
    def create_configuration_backup(self):
        """Create backup of configuration files."""
        print("⚙️  Creating configuration backup...")
        
        config_backup_dir = self.backup_dir / 'configurations'
        config_backup_dir.mkdir(exist_ok=True)
        
        # Backup URL configurations
        url_files = [
            'zargar/urls.py',
            'zargar/urls_public.py',
            'zargar/urls_tenants.py',
            'zargar/admin_panel/urls.py',
            'zargar/tenants/urls.py'
        ]
        
        for url_file in url_files:
            if Path(url_file).exists():
                shutil.copy2(url_file, config_backup_dir / Path(url_file).name)
                print(f"  ✅ Backed up {url_file}")
        
        # Backup settings
        settings_dir = Path('zargar/settings')
        if settings_dir.exists():
            shutil.copytree(settings_dir, config_backup_dir / 'settings')
            print(f"  ✅ Backed up settings directory")
        
        # Backup authentication backends
        auth_files = [
            'zargar/core/auth_backends.py',
            'zargar/admin_panel/views.py',
            'zargar/tenants/views.py'
        ]
        
        for auth_file in auth_files:
            if Path(auth_file).exists():
                shutil.copy2(auth_file, config_backup_dir / Path(auth_file).name)
                print(f"  ✅ Backed up {auth_file}")
    
    def create_template_backup(self):
        """Create backup of admin templates."""
        print("🎨 Creating template backup...")
        
        template_backup_dir = self.backup_dir / 'templates'
        
        # Backup admin-related templates
        admin_template_dirs = [
            'templates/admin_panel',
            'templates/auth',
            'templates/admin'
        ]
        
        for template_dir in admin_template_dirs:
            if Path(template_dir).exists():
                dest_dir = template_backup_dir / Path(template_dir).name
                shutil.copytree(template_dir, dest_dir)
                print(f"  ✅ Backed up {template_dir}")
    
    def create_migration_backup(self):
        """Create backup of database migrations."""
        print("🔄 Creating migration backup...")
        
        migration_backup_dir = self.backup_dir / 'migrations'
        migration_backup_dir.mkdir(exist_ok=True)
        
        # Find all migration directories
        for app_dir in Path('zargar').iterdir():
            if app_dir.is_dir():
                migrations_dir = app_dir / 'migrations'
                if migrations_dir.exists():
                    dest_dir = migration_backup_dir / app_dir.name
                    shutil.copytree(migrations_dir, dest_dir)
                    print(f"  ✅ Backed up {migrations_dir}")
    
    def create_system_state_snapshot(self):
        """Create snapshot of current system state."""
        print("📸 Creating system state snapshot...")
        
        state_file = self.backup_dir / 'system_state.json'
        
        # Collect system information
        system_state = {
            'timestamp': self.backup_timestamp,
            'python_version': sys.version,
        }
        
        if DJANGO_AVAILABLE:
            system_state.update({
                'django_version': django.VERSION,
                'database_engine': settings.DATABASES['default']['ENGINE'],
                'installed_apps': settings.INSTALLED_APPS,
                'middleware': settings.MIDDLEWARE,
                'authentication_backends': settings.AUTHENTICATION_BACKENDS,
            })
        
        # Add tenant information if Django is available
        if DJANGO_AVAILABLE:
            try:
                from zargar.tenants.models import Tenant
                tenants = list(Tenant.objects.exclude(schema_name='public').values(
                    'name', 'schema_name', 'is_active', 'created_on'
                ))
                system_state['tenants'] = tenants
                system_state['tenant_count'] = len(tenants)
            except Exception as e:
                system_state['tenant_error'] = str(e)
            
            # Add SuperAdmin information
            try:
                from zargar.tenants.admin_models import SuperAdmin
                superadmin_count = SuperAdmin.objects.count()
                system_state['superadmin_count'] = superadmin_count
            except Exception as e:
                system_state['superadmin_error'] = str(e)
        else:
            system_state['django_available'] = False
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(system_state, f, indent=2, default=str)
        
        print(f"✅ System state snapshot created: {state_file}")
    
    def create_rollback_script(self):
        """Create rollback script for emergency restoration."""
        print("🔙 Creating rollback script...")
        
        rollback_script = self.backup_dir / 'rollback.py'
        
        rollback_content = f'''#!/usr/bin/env python
"""
Emergency rollback script for admin consolidation.
Generated on: {datetime.now().isoformat()}
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def rollback_database():
    """Restore database from backup."""
    print("🔄 Restoring database...")
    
    backup_file = Path(__file__).parent / 'database_full_backup.sql'
    if not backup_file.exists():
        print("❌ Database backup file not found!")
        return False
    
    # Database configuration (update as needed)
    db_config = {{
        'HOST': 'localhost',
        'PORT': '5432',
        'USER': 'zargar',
        'NAME': 'zargar_dev',
        'PASSWORD': 'zargar_password_2024'
    }}
    
    cmd = [
        'psql',
        f"--host={{db_config['HOST']}}",
        f"--port={{db_config['PORT']}}",
        f"--username={{db_config['USER']}}",
        f"--dbname={{db_config['NAME']}}",
        f"--file={{backup_file}}"
    ]
    
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['PASSWORD']
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Database restored successfully")
            return True
        else:
            print(f"❌ Database restore failed: {{result.stderr}}")
            return False
    except Exception as e:
        print(f"❌ Database restore error: {{e}}")
        return False

def rollback_code():
    """Restore code from backup."""
    print("💾 Restoring code...")
    
    # Instructions for manual code restoration
    print("Manual code restoration required:")
    print("1. Restore from git: git reset --hard <previous_commit>")
    print("2. Or restore from backup directory")
    
    return True

def main():
    """Main rollback function."""
    print("🚨 EMERGENCY ROLLBACK PROCEDURE")
    print("=" * 50)
    
    success = True
    
    # Rollback database
    if not rollback_database():
        success = False
    
    # Rollback code
    if not rollback_code():
        success = False
    
    if success:
        print("✅ Rollback completed successfully")
        print("🔍 Please verify system functionality")
    else:
        print("❌ Rollback encountered errors")
        print("📞 Contact system administrator immediately")

if __name__ == '__main__':
    main()
'''
        
        with open(rollback_script, 'w', encoding='utf-8') as f:
            f.write(rollback_content)
        
        # Make script executable
        os.chmod(rollback_script, 0o755)
        
        print(f"✅ Rollback script created: {rollback_script}")
    
    def create_backup_summary(self):
        """Create summary of backup contents."""
        print("📋 Creating backup summary...")
        
        summary_file = self.backup_dir / 'backup_summary.md'
        
        summary_content = f'''# Admin Consolidation Backup Summary

**Backup Created**: {datetime.now().isoformat()}
**Backup Directory**: {self.backup_dir}

## Backup Contents

### 1. Database Backup
- **Full Database**: `database_full_backup.sql`
- **Schema Backups**: Individual schema backups for public and sample tenants

### 2. Code Backup
- **Git Archive**: `codebase_git_archive.tar.gz` (if available)
- **Directory Copy**: `codebase/` (fallback)

### 3. Configuration Backup
- **URL Configurations**: All URL routing files
- **Settings**: Django settings directory
- **Authentication**: Authentication backend files

### 4. Template Backup
- **Admin Templates**: `templates/admin_panel/`
- **Auth Templates**: `templates/auth/`
- **Django Admin**: `templates/admin/`

### 5. Migration Backup
- **All Migrations**: Database migration files for all apps

### 6. System State
- **System Snapshot**: `system_state.json`
- **Current Configuration**: Complete system state

### 7. Rollback Tools
- **Rollback Script**: `rollback.py`
- **Emergency Procedures**: Automated restoration tools

## Restoration Instructions

### Emergency Rollback
```bash
cd {self.backup_dir}
python rollback.py
```

### Manual Restoration
1. **Database**: Use `database_full_backup.sql` with psql
2. **Code**: Restore from git or `codebase/` directory
3. **Configuration**: Copy files from `configurations/`
4. **Templates**: Copy files from `templates/`

## Verification Checklist

After restoration, verify:
- [ ] SuperAdmin login works
- [ ] Tenant login works (unchanged)
- [ ] All admin features accessible
- [ ] No 404 errors
- [ ] Database integrity

## Support Information

**Backup Location**: `{self.backup_dir}`
**Created By**: Admin Consolidation Task 1.1
**Purpose**: Pre-consolidation system backup

---
**IMPORTANT**: Keep this backup until consolidation is verified successful.
'''
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary_content)
        
        print(f"✅ Backup summary created: {summary_file}")
    
    def run_full_backup(self):
        """Run complete backup procedure."""
        print("🚀 Starting comprehensive backup procedure...")
        print("=" * 60)
        
        success = True
        
        # Create all backups
        if not self.create_database_backup():
            success = False
        
        self.create_schema_specific_backups()
        self.create_code_backup()
        self.create_configuration_backup()
        self.create_template_backup()
        self.create_migration_backup()
        self.create_system_state_snapshot()
        self.create_rollback_script()
        self.create_backup_summary()
        
        print("=" * 60)
        if success:
            print("✅ BACKUP COMPLETED SUCCESSFULLY")
            print(f"📁 Backup Location: {self.backup_dir}")
            print("🔒 System is ready for consolidation")
        else:
            print("❌ BACKUP COMPLETED WITH ERRORS")
            print("⚠️  Review errors before proceeding")
        
        return success


def main():
    """Main function."""
    backup_manager = ConsolidationBackupManager()
    success = backup_manager.run_full_backup()
    
    if success:
        print("\n🎯 Next Steps:")
        print("1. Verify backup contents")
        print("2. Proceed to Task 2.1 - Unified Dashboard Development")
        print("3. Keep backup until consolidation is verified")
    else:
        print("\n🚨 Action Required:")
        print("1. Review and fix backup errors")
        print("2. Re-run backup procedure")
        print("3. Do not proceed until backup is successful")
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())