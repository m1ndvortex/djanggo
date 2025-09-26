# Super Admin Security & Settings System - Design Document

## Overview

This design document outlines the architecture and implementation approach for the Super Admin Security & Settings system. The system will extend the existing unified admin panel at http://localhost:8000/super-panel/ with comprehensive security monitoring, audit management, role-based access control, and system settings management.

The design leverages existing security models (SecurityEvent, AuditLog, RateLimitAttempt, SuspiciousActivity) and builds upon the established unified admin architecture with dual-theme support (modern light/cybersecurity dark).

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Super Admin Panel                        │
│                 http://localhost:8000/super-panel/          │
├─────────────────────────────────────────────────────────────┤
│  Existing Sections          │  New Security & Settings      │
│  ├─ Dashboard              │  ├─ Security Dashboard         │
│  ├─ Tenant Management      │  ├─ Audit Logs               │
│  ├─ User Management        │  ├─ Security Events           │
│  ├─ System Monitoring      │  ├─ Access Control            │
│  ├─ Backup Management      │  └─ Settings (NEW TAB)        │
│  └─ Financial Management   │     ├─ Security Policies      │
│                            │     ├─ Notifications          │
│                            │     ├─ Backup Settings        │
│                            │     └─ Integration Settings   │
└─────────────────────────────────────────────────────────────┘
```

### Database Schema Extensions

The system will use existing security models and add new models for settings and role management:

```sql
-- Existing Models (Already Implemented)
core_security_event
core_audit_log  
core_rate_limit_attempt
core_suspicious_activity

-- New Models (To Be Created)
admin_panel_super_admin_role
admin_panel_super_admin_permission
admin_panel_system_setting
admin_panel_notification_setting
```

### URL Structure

```
/super-panel/
├─ security/
│  ├─ dashboard/                    # Security Dashboard
│  ├─ audit-logs/                   # Audit Log Management
│  ├─ security-events/              # Security Event Management
│  └─ access-control/               # Role-Based Access Control
└─ settings/                        # NEW: Settings Tab
   ├─ security-policies/            # Security Policy Configuration
   ├─ notifications/                # Notification Management
   ├─ backup-settings/              # Backup & Maintenance Settings
   └─ integrations/                 # Integration & API Settings
```

## Components and Interfaces

### 1. Security Dashboard Component

**Purpose:** Real-time security monitoring and threat visualization

**Key Features:**
- Security metrics widgets (failed logins, blocked IPs, suspicious activities)
- Real-time security event stream
- Threat level indicators with Persian labels
- Security trend charts using Chart.js
- Quick action buttons for common security tasks

**Data Sources:**
- SecurityEvent model for recent events
- RateLimitAttempt model for blocking statistics
- SuspiciousActivity model for threat analysis
- AuditLog model for activity summaries

### 2. Audit Log Management Component

**Purpose:** Comprehensive audit trail viewing and investigation

**Key Features:**
- Paginated audit log table with advanced filtering
- Search functionality (user, action, date range, tenant)
- Audit log detail modal with before/after comparison
- Integrity verification status indicators
- Export functionality for compliance reporting

**Data Sources:**
- AuditLog model with related user and content type data
- Integrity checksum verification
- Tenant-aware filtering

### 3. Security Event Management Component

**Purpose:** Security incident tracking and resolution

**Key Features:**
- Security event categorization by severity
- Investigation workflow with status tracking
- Event correlation and grouping
- Resolution notes and assignment
- Automated threat scoring

**Data Sources:**
- SecurityEvent model with investigation fields
- Related SuspiciousActivity records
- User assignment for investigation

### 4. Role-Based Access Control Component

**Purpose:** Super admin permission management

**Key Features:**
- Role creation and editing interface
- Permission matrix for different admin sections
- User role assignment
- Real-time permission enforcement
- Permission inheritance and hierarchy

**New Models:**
```python
class SuperAdminRole(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    permissions = models.ManyToManyField('SuperAdminPermission')
    is_active = models.BooleanField(default=True)

class SuperAdminPermission(models.Model):
    codename = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    section = models.CharField(max_length=50)  # tenants, billing, security, etc.
    
class SuperAdminUserRole(models.Model):
    user = models.ForeignKey('tenants.SuperAdmin')
    role = models.ForeignKey(SuperAdminRole)
```

### 5. System Settings Management Component

**Purpose:** Centralized system configuration

**Key Features:**
- Categorized settings sections
- Form validation and type checking
- Setting change audit logging
- Import/export configuration
- Setting dependency management

**New Models:**
```python
class SystemSetting(models.Model):
    SETTING_TYPES = [
        ('string', 'String'),
        ('integer', 'Integer'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
    ]
    
    key = models.CharField(max_length=200, unique=True)
    value = models.TextField()
    setting_type = models.CharField(max_length=20, choices=SETTING_TYPES)
    category = models.CharField(max_length=100)
    description = models.TextField()
    is_sensitive = models.BooleanField(default=False)
    requires_restart = models.BooleanField(default=False)
```

### 6. Navigation Integration

The existing navigation will be extended with:

```html
<!-- Add to existing navigation -->
<button class="nav-item" data-section="security">
    <i class="icon-shield"></i>
    <span>امنیت و حسابرسی</span>
</button>

<!-- NEW: Settings Tab -->
<button class="nav-item" data-section="settings">
    <i class="icon-settings"></i>
    <span>تنظیمات</span>
</button>
```

## Data Models

### Extended SuperAdmin Model

```python
# Extend existing SuperAdmin model with role relationship
class SuperAdmin(AbstractUser):
    # ... existing fields ...
    roles = models.ManyToManyField('SuperAdminRole', through='SuperAdminUserRole')
    
    def has_permission(self, permission_codename):
        """Check if user has specific permission"""
        return self.roles.filter(
            permissions__codename=permission_codename,
            is_active=True
        ).exists()
    
    def get_accessible_sections(self):
        """Get list of sections user can access"""
        return list(self.roles.filter(is_active=True)
                   .values_list('permissions__section', flat=True)
                   .distinct())
```

### Security Dashboard Data Model

```python
class SecurityDashboardData:
    """Data aggregation for security dashboard"""
    
    @staticmethod
    def get_security_metrics():
        """Get real-time security metrics"""
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        
        return {
            'failed_logins_24h': SecurityEvent.objects.filter(
                event_type='login_failed',
                created_at__gte=last_24h
            ).count(),
            'blocked_ips': RateLimitAttempt.objects.filter(
                is_blocked=True
            ).count(),
            'suspicious_activities': SuspiciousActivity.objects.filter(
                created_at__gte=last_24h,
                is_investigated=False
            ).count(),
            'critical_events': SecurityEvent.objects.filter(
                severity='critical',
                is_resolved=False
            ).count(),
        }
```

### Settings Management Data Model

```python
class SettingsManager:
    """Centralized settings management"""
    
    @staticmethod
    def get_setting(key, default=None):
        """Get setting value with type conversion"""
        try:
            setting = SystemSetting.objects.get(key=key)
            return setting.get_typed_value()
        except SystemSetting.DoesNotExist:
            return default
    
    @staticmethod
    def set_setting(key, value, user=None):
        """Set setting value with audit logging"""
        setting, created = SystemSetting.objects.get_or_create(key=key)
        old_value = setting.value if not created else None
        setting.value = str(value)
        setting.save()
        
        # Log the change
        if user:
            AuditLog.log_action(
                action='configuration_change',
                user=user,
                content_object=setting,
                old_values={'value': old_value},
                new_values={'value': str(value)}
            )
```

## Error Handling

### Security Error Handling

1. **Authentication Failures:** Log security events and implement progressive delays
2. **Authorization Failures:** Redirect to appropriate error pages with audit logging
3. **Data Integrity Issues:** Alert administrators and prevent data corruption
4. **Rate Limiting:** Graceful degradation with clear user feedback

### Settings Error Handling

1. **Validation Errors:** Clear field-level error messages in Persian
2. **Dependency Conflicts:** Prevent conflicting setting combinations
3. **System Impact Warnings:** Alert for settings requiring restart
4. **Rollback Capability:** Ability to revert problematic setting changes

## Testing Strategy

### Unit Testing

1. **Security Models:** Test event logging, integrity verification, threat scoring
2. **Settings Models:** Test type conversion, validation, dependency checking
3. **Permission System:** Test role-based access control logic
4. **Data Aggregation:** Test dashboard metrics calculation

### Integration Testing

1. **Security Dashboard:** Test real-time data updates and chart rendering
2. **Audit Log Interface:** Test filtering, searching, and export functionality
3. **Settings Management:** Test setting changes and system impact
4. **Permission Enforcement:** Test access control across all interfaces

### Security Testing

1. **Access Control:** Verify unauthorized access prevention
2. **Data Leakage:** Ensure tenant isolation in security data
3. **Audit Integrity:** Test tamper detection and prevention
4. **Rate Limiting:** Verify protection against abuse

### Performance Testing

1. **Dashboard Loading:** Ensure sub-2-second load times
2. **Large Dataset Handling:** Test with thousands of audit logs
3. **Real-time Updates:** Test WebSocket performance for live data
4. **Export Operations:** Test large data export performance

## Implementation Phases

### Phase 1: Security Dashboard & Audit Logs
- Implement security dashboard with existing models
- Create audit log management interface
- Add security event viewing and basic management

### Phase 2: Role-Based Access Control
- Create role and permission models
- Implement permission checking middleware
- Build role management interface

### Phase 3: Settings Management System
- Create system settings models and management
- Implement settings categories and validation
- Build settings interface with change tracking

### Phase 4: Advanced Features & Polish
- Add notification management
- Implement backup settings integration
- Add integration and API settings
- Performance optimization and testing

This phased approach ensures incremental delivery of value while maintaining system stability and allowing for user feedback between phases.