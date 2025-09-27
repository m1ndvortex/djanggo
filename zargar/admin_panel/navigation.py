"""
Navigation utilities for admin panel with RBAC support.
"""
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class NavigationItem:
    """Represents a navigation item with permission checking."""
    
    def __init__(self, name, url_name=None, url=None, icon=None, permission=None, 
                 children=None, badge=None, color_class=None):
        self.name = name
        self.url_name = url_name
        self.url = url
        self.icon = icon
        self.permission = permission
        self.children = children or []
        self.badge = badge
        self.color_class = color_class or 'primary'
    
    def get_url(self):
        """Get the URL for this navigation item."""
        if self.url:
            return self.url
        elif self.url_name:
            try:
                return reverse(self.url_name)
            except:
                # Try in the public schema context
                from django.conf import settings
                original_urlconf = settings.ROOT_URLCONF
                try:
                    settings.ROOT_URLCONF = getattr(settings, 'PUBLIC_SCHEMA_URLCONF', settings.ROOT_URLCONF)
                    return reverse(self.url_name)
                except:
                    return '#'
                finally:
                    settings.ROOT_URLCONF = original_urlconf
        return '#'
    
    def has_permission(self, user):
        """Check if user has permission to access this item."""
        if not self.permission:
            return True
        
        # SuperAdmin users have access to everything
        if hasattr(user, 'is_superuser') and user.is_superuser:
            return True
        
        # Check if user has the required permission
        if hasattr(user, 'has_permission'):
            return user.has_permission(self.permission)
        
        # For SuperAdmin model instances, grant access by default
        if user.__class__.__name__ == 'SuperAdmin':
            return True
        
        # Fallback for regular users
        return False
    
    def get_accessible_children(self, user):
        """Get children that user has permission to access."""
        return [child for child in self.children if child.has_permission(user)]


class AdminNavigationBuilder:
    """Builds the admin panel navigation structure."""
    
    def __init__(self):
        self.navigation_items = []
        self._build_navigation()
    
    def _build_navigation(self):
        """Build the complete navigation structure."""
        
        # Dashboard
        self.navigation_items.append(
            NavigationItem(
                name=_('داشبورد اصلی'),
                url_name='admin_panel:dashboard',
                icon='dashboard',
                color_class='primary'
            )
        )
        
        # Tenant Management
        self.navigation_items.append(
            NavigationItem(
                name=_('مدیریت تنانت‌ها'),
                icon='tenants',
                permission='tenants.view',
                color_class='primary',
                children=[
                    NavigationItem(
                        name=_('مشاهده همه تنانت‌ها'),
                        url_name='admin_panel:tenants:tenant_list',
                        permission='tenants.view'
                    ),
                    NavigationItem(
                        name=_('ایجاد تنانت جدید'),
                        url_name='admin_panel:tenants:tenant_create',
                        permission='tenants.create'
                    ),
                    NavigationItem(
                        name=_('جستجو و عملیات گروهی'),
                        url_name='admin_panel:tenants:tenant_search',
                        permission='tenants.bulk_operations'
                    ),
                    NavigationItem(
                        name=_('تنظیمات دامنه'),
                        url_name='admin_panel:domain_settings',
                        permission='tenants.domain_settings'
                    ),
                ]
            )
        )
        
        # User Impersonation
        self.navigation_items.append(
            NavigationItem(
                name=_('مدیریت کاربران'),
                icon='users',
                permission='users.impersonate',
                color_class='purple',
                children=[
                    NavigationItem(
                        name=_('جایگزینی کاربر'),
                        url_name='admin_panel:user_impersonation',
                        permission='users.impersonate'
                    ),
                    NavigationItem(
                        name=_('گزارش‌های حسابرسی'),
                        url_name='admin_panel:impersonation_audit',
                        permission='users.audit'
                    ),
                    NavigationItem(
                        name=_('آمار و گزارش‌ها'),
                        url_name='admin_panel:impersonation_stats',
                        permission='users.stats'
                    ),
                ]
            )
        )
        
        # System Health
        self.navigation_items.append(
            NavigationItem(
                name=_('نظارت سیستم'),
                icon='health',
                permission='system.monitor',
                color_class='green',
                children=[
                    NavigationItem(
                        name=_('داشبورد سلامت سیستم'),
                        url_name='admin_panel:system_health_dashboard',
                        permission='system.monitor'
                    ),
                    NavigationItem(
                        name=_('هشدارها و اعلان‌ها'),
                        url_name='admin_panel:system_health_alerts',
                        permission='system.alerts'
                    ),
                    NavigationItem(
                        name=_('گزارش‌های عملکرد'),
                        url_name='admin_panel:system_health_reports',
                        permission='system.reports'
                    ),
                ]
            )
        )
        
        # Backup & Recovery
        self.navigation_items.append(
            NavigationItem(
                name=_('پشتیبان‌گیری'),
                icon='backup',
                permission='backup.manage',
                color_class='orange',
                children=[
                    NavigationItem(
                        name=_('مدیریت پشتیبان'),
                        url_name='admin_panel:backup_management',
                        permission='backup.manage'
                    ),
                    NavigationItem(
                        name=_('تاریخچه پشتیبان'),
                        url_name='admin_panel:backup_history',
                        permission='backup.view'
                    ),
                    NavigationItem(
                        name=_('بازیابی تنانت'),
                        url_name='admin_panel:tenant_restore',
                        permission='backup.restore'
                    ),
                    NavigationItem(
                        name=_('بازیابی فاجعه'),
                        url_name='admin_panel:disaster_recovery_dashboard',
                        permission='backup.disaster_recovery'
                    ),
                ]
            )
        )
        
        # Billing & Subscriptions
        self.navigation_items.append(
            NavigationItem(
                name=_('مدیریت مالی'),
                icon='billing',
                permission='billing.manage',
                color_class='yellow',
                children=[
                    NavigationItem(
                        name=_('داشبورد مالی'),
                        url_name='admin_panel:tenants:billing:dashboard',
                        permission='billing.view'
                    ),
                    NavigationItem(
                        name=_('پلن‌های اشتراک'),
                        url_name='admin_panel:tenants:billing:subscription_plans',
                        permission='billing.plans'
                    ),
                    NavigationItem(
                        name=_('مدیریت فاکتورها'),
                        url_name='admin_panel:tenants:billing:invoices',
                        permission='billing.invoices'
                    ),
                    NavigationItem(
                        name=_('گزارش‌های درآمد'),
                        url_name='admin_panel:tenants:billing:reports',
                        permission='billing.reports'
                    ),
                ]
            )
        )
        
        # Security & Audit
        self.navigation_items.append(
            NavigationItem(
                name=_('امنیت و حسابرسی'),
                icon='security',
                permission='security.view',
                color_class='red',
                children=[
                    NavigationItem(
                        name=_('داشبورد امنیت'),
                        url_name='admin_panel:security_dashboard',
                        permission='security.dashboard'
                    ),
                    NavigationItem(
                        name=_('لاگ‌های حسابرسی'),
                        url_name='admin_panel:audit_logs',
                        permission='security.audit_logs'
                    ),
                    NavigationItem(
                        name=_('رویدادهای امنیتی'),
                        url_name='admin_panel:security_events',
                        permission='security.events'
                    ),
                    NavigationItem(
                        name=_('کنترل دسترسی'),
                        url_name='admin_panel:rbac_management',
                        permission='security.rbac'
                    ),
                ]
            )
        )
        
        # Settings
        self.navigation_items.append(
            NavigationItem(
                name=_('تنظیمات'),
                icon='settings',
                permission='settings.manage',
                color_class='blue',
                children=[
                    NavigationItem(
                        name=_('تنظیمات عمومی'),
                        url_name='admin_panel:settings_management',
                        permission='settings.general'
                    ),
                    NavigationItem(
                        name=_('سیاست‌های امنیتی'),
                        url_name='admin_panel:security_policies',
                        permission='settings.security_policies'
                    ),
                    NavigationItem(
                        name=_('مدیریت اعلان‌ها'),
                        url_name='admin_panel:notifications_management',
                        permission='settings.notifications'
                    ),
                    NavigationItem(
                        name=_('تنظیمات پشتیبان‌گیری'),
                        url_name='admin_panel:settings_management',
                        permission='settings.backup'
                    ),
                    NavigationItem(
                        name=_('تنظیمات یکپارچه‌سازی'),
                        url_name='admin_panel:integration_settings',
                        permission='settings.integrations'
                    ),
                ]
            )
        )
    
    def get_navigation_for_user(self, user):
        """Get navigation items that user has permission to access."""
        accessible_items = []
        
        for item in self.navigation_items:
            if item.has_permission(user):
                # Create a copy with accessible children
                accessible_children = item.get_accessible_children(user)
                
                # Only include parent if it has accessible children or direct access
                if accessible_children or not item.children:
                    accessible_item = NavigationItem(
                        name=item.name,
                        url_name=item.url_name,
                        url=item.url,
                        icon=item.icon,
                        permission=item.permission,
                        children=accessible_children,
                        badge=item.badge,
                        color_class=item.color_class
                    )
                    accessible_items.append(accessible_item)
        
        return accessible_items


class BreadcrumbBuilder:
    """Builds breadcrumb navigation for pages."""
    
    def __init__(self):
        self.breadcrumb_map = {
            # Dashboard
            'admin_panel:dashboard': [
                {'name': _('داشبورد اصلی'), 'url': 'admin_panel:dashboard'}
            ],
            
            # Security & Audit
            'admin_panel:security_dashboard': [
                {'name': _('امنیت و حسابرسی'), 'url': None},
                {'name': _('داشبورد امنیت'), 'url': 'admin_panel:security_dashboard'}
            ],
            'admin_panel:audit_logs': [
                {'name': _('امنیت و حسابرسی'), 'url': None},
                {'name': _('لاگ‌های حسابرسی'), 'url': 'admin_panel:audit_logs'}
            ],
            'admin_panel:security_events': [
                {'name': _('امنیت و حسابرسی'), 'url': None},
                {'name': _('رویدادهای امنیتی'), 'url': 'admin_panel:security_events'}
            ],
            'admin_panel:rbac_management': [
                {'name': _('امنیت و حسابرسی'), 'url': None},
                {'name': _('کنترل دسترسی'), 'url': 'admin_panel:rbac_management'}
            ],
            
            # Settings
            'admin_panel:settings_management': [
                {'name': _('تنظیمات'), 'url': None},
                {'name': _('تنظیمات عمومی'), 'url': 'admin_panel:settings_management'}
            ],
            'admin_panel:security_policies': [
                {'name': _('تنظیمات'), 'url': None},
                {'name': _('سیاست‌های امنیتی'), 'url': 'admin_panel:security_policies'}
            ],
            'admin_panel:notifications_management': [
                {'name': _('تنظیمات'), 'url': None},
                {'name': _('مدیریت اعلان‌ها'), 'url': 'admin_panel:notifications_management'}
            ],
            'admin_panel:integration_settings': [
                {'name': _('تنظیمات'), 'url': None},
                {'name': _('تنظیمات یکپارچه‌سازی'), 'url': 'admin_panel:integration_settings'}
            ],
        }
    
    def get_breadcrumbs(self, url_name, **kwargs):
        """Get breadcrumbs for a given URL name."""
        breadcrumbs = self.breadcrumb_map.get(url_name, [])
        
        # Convert URL names to actual URLs
        processed_breadcrumbs = []
        for crumb in breadcrumbs:
            url = None
            if crumb['url']:
                try:
                    # Try to reverse the URL in the current context
                    url = reverse(crumb['url'])
                except:
                    # If that fails, try in the public schema context
                    from django.conf import settings
                    original_urlconf = settings.ROOT_URLCONF
                    try:
                        settings.ROOT_URLCONF = getattr(settings, 'PUBLIC_SCHEMA_URLCONF', settings.ROOT_URLCONF)
                        url = reverse(crumb['url'])
                    except:
                        url = None
                    finally:
                        settings.ROOT_URLCONF = original_urlconf
            
            processed_crumb = {
                'name': crumb['name'],
                'url': url,
                'active': crumb.get('active', False)
            }
            processed_breadcrumbs.append(processed_crumb)
        
        # Mark the last item as active
        if processed_breadcrumbs:
            processed_breadcrumbs[-1]['active'] = True
        
        return processed_breadcrumbs


# Global instances
navigation_builder = AdminNavigationBuilder()
breadcrumb_builder = BreadcrumbBuilder()