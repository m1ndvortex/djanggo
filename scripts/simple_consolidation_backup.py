#!/usr/bin/env python
"""
Simple backup script for admin consolidation.
Creates backups of essential files and configurations.
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path


class SimpleBackupManager:
    """
    Simple backup manager for essential files.
    """
    
    def __init__(self):
        self.backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_dir = Path(f'backups/admin_consolidation_{self.backup_timestamp}')
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"🔄 Creating simple consolidation backup: {self.backup_dir}")
    
    def backup_essential_files(self):
        """Backup essential files for consolidation."""
        print("📁 Backing up essential files...")
        
        essential_files = [
            # URL configurations
            'zargar/urls.py',
            'zargar/urls_public.py', 
            'zargar/urls_tenants.py',
            'zargar/admin_panel/urls.py',
            'zargar/tenants/urls.py',
            'zargar/tenants/billing_urls.py',
            
            # Authentication backends
            'zargar/core/auth_backends.py',
            
            # Admin views
            'zargar/admin_panel/views.py',
            'zargar/tenants/views.py',
            'zargar/tenants/billing_views.py',
            
            # Models
            'zargar/tenants/admin_models.py',
            'zargar/core/models.py',
            'zargar/tenants/models.py',
            
            # Settings
            'zargar/settings/base.py',
            'zargar/settings/development.py',
            'zargar/settings/production.py',
        ]
        
        files_backup_dir = self.backup_dir / 'essential_files'
        files_backup_dir.mkdir(exist_ok=True)
        
        backed_up = 0
        for file_path in essential_files:
            if Path(file_path).exists():
                # Create subdirectory structure
                dest_path = files_backup_dir / file_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.copy2(file_path, dest_path)
                print(f"  ✅ {file_path}")
                backed_up += 1
            else:
                print(f"  ⚠️  {file_path} (not found)")
        
        print(f"✅ Backed up {backed_up} essential files")
    
    def backup_admin_templates(self):
        """Backup admin-related templates."""
        print("🎨 Backing up admin templates...")
        
        template_dirs = [
            'templates/admin_panel',
            'templates/auth',
            'templates/admin'
        ]
        
        templates_backup_dir = self.backup_dir / 'templates'
        
        backed_up = 0
        for template_dir in template_dirs:
            if Path(template_dir).exists():
                dest_dir = templates_backup_dir / Path(template_dir).name
                shutil.copytree(template_dir, dest_dir)
                print(f"  ✅ {template_dir}")
                backed_up += 1
            else:
                print(f"  ⚠️  {template_dir} (not found)")
        
        print(f"✅ Backed up {backed_up} template directories")
    
    def create_file_inventory(self):
        """Create inventory of current admin system files."""
        print("📋 Creating file inventory...")
        
        inventory = {
            'timestamp': self.backup_timestamp,
            'admin_urls': [],
            'auth_backends': [],
            'admin_templates': [],
            'admin_views': [],
            'models': []
        }
        
        # Scan for admin-related files
        for root, dirs, files in os.walk('.'):
            for file in files:
                file_path = Path(root) / file
                
                # Skip hidden directories and __pycache__
                if any(part.startswith('.') or part == '__pycache__' for part in file_path.parts):
                    continue
                
                # Check for admin-related files
                if 'admin' in str(file_path).lower() or 'auth' in str(file_path).lower():
                    if file.endswith('.py'):
                        if 'urls.py' in file:
                            inventory['admin_urls'].append(str(file_path))
                        elif 'views.py' in file:
                            inventory['admin_views'].append(str(file_path))
                        elif 'models.py' in file:
                            inventory['models'].append(str(file_path))
                        elif 'auth' in file:
                            inventory['auth_backends'].append(str(file_path))
                    elif file.endswith('.html'):
                        inventory['admin_templates'].append(str(file_path))
        
        inventory_file = self.backup_dir / 'file_inventory.json'
        with open(inventory_file, 'w', encoding='utf-8') as f:
            json.dump(inventory, f, indent=2)
        
        print(f"✅ File inventory created: {inventory_file}")
        return inventory
    
    def create_consolidation_checklist(self):
        """Create checklist for consolidation process."""
        print("📝 Creating consolidation checklist...")
        
        checklist_content = f'''# Admin Consolidation Checklist

**Backup Created**: {datetime.now().isoformat()}
**Backup Location**: {self.backup_dir}

## Pre-Consolidation Checklist

### ✅ Completed
- [x] System analysis and audit
- [x] Essential files backup
- [x] Template backup
- [x] File inventory creation
- [x] Consolidation plan documentation

### 🔄 Next Steps (Task 2.1)
- [ ] Create unified admin dashboard template
- [ ] Integrate tenant management interface
- [ ] Integrate user impersonation system
- [ ] Integrate backup management system
- [ ] Integrate system health monitoring
- [ ] Integrate billing and subscription management
- [ ] Integrate security and audit logging
- [ ] Implement theme switching system
- [ ] Write comprehensive frontend tests

### 🔄 Authentication Consolidation (Task 3.1)
- [ ] Create unified authentication backend
- [ ] Consolidate admin authentication flows
- [ ] Enhance 2FA system integration
- [ ] Implement unified session management
- [ ] Add comprehensive audit logging
- [ ] Remove duplicate authentication backends
- [ ] Write security tests

### 🔄 Legacy Cleanup (Task 4.1)
- [ ] Redirect /admin/ to unified system
- [ ] Remove duplicate admin templates
- [ ] Clean up duplicate admin URLs
- [ ] Remove obsolete authentication backends
- [ ] Update internal references
- [ ] Preserve tenant login system
- [ ] Write cleanup tests

### 🔄 Data Migration (Task 5.1)
- [ ] Migrate SuperAdmin data
- [ ] Transfer session data
- [ ] Verify admin functionality
- [ ] Clean up obsolete database tables
- [ ] Validate data integrity
- [ ] Write migration tests

### 🔄 Testing (Task 6.1)
- [ ] Unit tests for unified authentication
- [ ] Playwright end-to-end tests
- [ ] Security tests
- [ ] Performance tests
- [ ] Integration tests
- [ ] Theme switching tests
- [ ] Tenant isolation verification

### 🔄 Deployment (Task 7.1)
- [ ] Deploy unified admin system
- [ ] Validate all features
- [ ] Verify tenant login unchanged
- [ ] Test authentication flows
- [ ] Monitor system performance
- [ ] Clean up legacy code
- [ ] Create support documentation

## Critical Requirements

### ⚠️ MUST PRESERVE
- **Tenant login system** (`templates/auth/tenant_login.html`) - UNCHANGED
- **Tenant authentication flows** - NO MODIFICATIONS
- **Tenant user experience** - IDENTICAL TO CURRENT
- **Perfect tenant isolation** - MAINTAIN COMPLETELY

### ⚠️ MUST REMOVE
- **Duplicate admin login templates** (`templates/auth/admin_login.html`)
- **Multiple admin entry points** (consolidate to single interface)
- **Redundant authentication backends**
- **Orphaned admin URLs and views**

### ⚠️ MUST INTEGRATE
- **All existing SuperAdmin features** - NO FUNCTIONALITY LOSS
- **Persian RTL layout** - CONSISTENT THROUGHOUT
- **Dual theme system** - LIGHT/DARK CYBERSECURITY
- **Comprehensive audit logging** - ALL ADMIN ACTIONS

## Rollback Plan

### Emergency Rollback
1. **Stop application**
2. **Restore files from backup**: `{self.backup_dir}/essential_files/`
3. **Restore templates from backup**: `{self.backup_dir}/templates/`
4. **Restart application**
5. **Verify functionality**

### Verification After Rollback
- [ ] SuperAdmin login works
- [ ] Tenant login works (unchanged)
- [ ] All admin features accessible
- [ ] No 404 errors
- [ ] Database integrity maintained

## Success Criteria

### Primary Objectives
- [ ] Single unified admin interface
- [ ] No duplicate admin systems
- [ ] Preserved tenant experience
- [ ] Enhanced security
- [ ] Improved maintainability

### Measurable Outcomes
- **Admin entry points**: 1 (down from 2+)
- **Authentication backends**: 2 (SuperAdmin + Tenant, down from 4)
- **Login templates**: 2 (Unified admin + Tenant, down from 3+)
- **Security vulnerabilities**: 0 (eliminated duplicates)
- **Maintenance overhead**: Reduced by ~50%

---

**Status**: Ready for Task 2.1 - Unified Dashboard Development
**Next Action**: Begin implementing unified admin interface
'''
        
        checklist_file = self.backup_dir / 'consolidation_checklist.md'
        with open(checklist_file, 'w', encoding='utf-8') as f:
            f.write(checklist_content)
        
        print(f"✅ Consolidation checklist created: {checklist_file}")
    
    def run_simple_backup(self):
        """Run simple backup procedure."""
        print("🚀 Starting simple backup procedure...")
        print("=" * 50)
        
        self.backup_essential_files()
        self.backup_admin_templates()
        inventory = self.create_file_inventory()
        self.create_consolidation_checklist()
        
        print("=" * 50)
        print("✅ SIMPLE BACKUP COMPLETED")
        print(f"📁 Backup Location: {self.backup_dir}")
        print(f"📊 Files Inventoried: {len(inventory['admin_urls']) + len(inventory['admin_templates']) + len(inventory['admin_views'])}")
        print("🔒 System is ready for consolidation")
        
        return True


def main():
    """Main function."""
    backup_manager = SimpleBackupManager()
    success = backup_manager.run_simple_backup()
    
    if success:
        print("\n🎯 Next Steps:")
        print("1. Review backup contents")
        print("2. Proceed to Task 2.1 - Unified Dashboard Development")
        print("3. Follow consolidation checklist")
        print("4. Keep backup until consolidation is verified")
    
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())