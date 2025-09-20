"""
Services for tenant management, provisioning, and statistics collection.
"""

from django.db import connection, transaction
from django.core.management import call_command
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from django_tenants.utils import schema_context
import logging
import subprocess
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from .models import Tenant, Domain
from .admin_models import TenantAccessLog

logger = logging.getLogger(__name__)


class TenantProvisioningService:
    """
    Service for automated tenant provisioning including schema creation,
    migrations, and initial data setup.
    """
    
    def provision_tenant(self, tenant: Tenant) -> Dict[str, Any]:
        """
        Provision a new tenant with complete setup.
        
        Args:
            tenant: The tenant instance to provision
            
        Returns:
            Dict with success status and details
        """
        try:
            with transaction.atomic():
                # Step 1: Create schema
                schema_result = self._create_tenant_schema(tenant)
                if not schema_result['success']:
                    return schema_result
                
                # Step 2: Run migrations
                migration_result = self._run_tenant_migrations(tenant)
                if not migration_result['success']:
                    return migration_result
                
                # Step 3: Setup initial data
                initial_data_result = self._setup_initial_data(tenant)
                if not initial_data_result['success']:
                    return initial_data_result
                
                # Step 4: Create initial admin user (if needed)
                admin_user_result = self._create_initial_admin_user(tenant)
                if not admin_user_result['success']:
                    return admin_user_result
                
                logger.info(f"Successfully provisioned tenant: {tenant.schema_name}")
                
                return {
                    'success': True,
                    'message': 'Tenant provisioned successfully',
                    'details': {
                        'schema_created': schema_result['details'],
                        'migrations_run': migration_result['details'],
                        'initial_data': initial_data_result['details'],
                        'admin_user': admin_user_result['details'],
                    }
                }
                
        except Exception as e:
            logger.error(f"Error provisioning tenant {tenant.schema_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to provision tenant'
            }
    
    def _create_tenant_schema(self, tenant: Tenant) -> Dict[str, Any]:
        """Create the database schema for the tenant."""
        try:
            # The schema creation is handled automatically by django-tenants
            # when the tenant is saved, but we can verify it exists
            
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                    [tenant.schema_name]
                )
                
                if cursor.fetchone():
                    return {
                        'success': True,
                        'details': f'Schema {tenant.schema_name} exists'
                    }
                else:
                    # Force schema creation
                    tenant.create_schema()
                    return {
                        'success': True,
                        'details': f'Schema {tenant.schema_name} created'
                    }
                    
        except Exception as e:
            logger.error(f"Error creating schema for {tenant.schema_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _run_tenant_migrations(self, tenant: Tenant) -> Dict[str, Any]:
        """Run database migrations for the tenant schema."""
        try:
            with schema_context(tenant.schema_name):
                # Run migrations for the tenant schema
                call_command('migrate_schemas', '--schema', tenant.schema_name, verbosity=0)
                
                return {
                    'success': True,
                    'details': f'Migrations completed for {tenant.schema_name}'
                }
                
        except Exception as e:
            logger.error(f"Error running migrations for {tenant.schema_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _setup_initial_data(self, tenant: Tenant) -> Dict[str, Any]:
        """Setup initial data for the tenant."""
        try:
            with schema_context(tenant.schema_name):
                # Import here to avoid circular imports
                from django.contrib.auth import get_user_model
                from django.contrib.auth.models import Group, Permission
                
                User = get_user_model()
                
                # Create user groups with Persian names
                groups_created = []
                
                # Owner group
                owner_group, created = Group.objects.get_or_create(
                    name='مالک فروشگاه',
                    defaults={'name': 'مالک فروشگاه'}
                )
                if created:
                    groups_created.append('مالک فروشگاه')
                
                # Accountant group
                accountant_group, created = Group.objects.get_or_create(
                    name='حسابدار',
                    defaults={'name': 'حسابدار'}
                )
                if created:
                    groups_created.append('حسابدار')
                
                # Salesperson group
                salesperson_group, created = Group.objects.get_or_create(
                    name='فروشنده',
                    defaults={'name': 'فروشنده'}
                )
                if created:
                    groups_created.append('فروشنده')
                
                # Setup permissions for groups
                self._setup_group_permissions(owner_group, accountant_group, salesperson_group)
                
                return {
                    'success': True,
                    'details': {
                        'groups_created': groups_created,
                        'permissions_setup': True
                    }
                }
                
        except Exception as e:
            logger.error(f"Error setting up initial data for {tenant.schema_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _setup_group_permissions(self, owner_group, accountant_group, salesperson_group):
        """Setup permissions for user groups."""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        
        # Get all permissions
        all_permissions = Permission.objects.all()
        
        # Owner gets all permissions
        owner_group.permissions.set(all_permissions)
        
        # Accountant gets accounting, reporting, and customer permissions
        accountant_permissions = Permission.objects.filter(
            Q(codename__icontains='accounting') |
            Q(codename__icontains='report') |
            Q(codename__icontains='customer') |
            Q(codename__icontains='invoice') |
            Q(codename__icontains='payment')
        )
        accountant_group.permissions.set(accountant_permissions)
        
        # Salesperson gets POS, inventory, and customer permissions
        salesperson_permissions = Permission.objects.filter(
            Q(codename__icontains='pos') |
            Q(codename__icontains='inventory') |
            Q(codename__icontains='customer') |
            Q(codename__icontains='sale') |
            Q(codename__icontains='jewelry')
        )
        salesperson_group.permissions.set(salesperson_permissions)
    
    def _create_initial_admin_user(self, tenant: Tenant) -> Dict[str, Any]:
        """Create initial admin user for the tenant."""
        try:
            with schema_context(tenant.schema_name):
                from django.contrib.auth import get_user_model
                from django.contrib.auth.models import Group
                
                User = get_user_model()
                
                # Check if owner user already exists
                if User.objects.filter(email=tenant.owner_email).exists():
                    return {
                        'success': True,
                        'details': 'Owner user already exists'
                    }
                
                # Create owner user
                owner_user = User.objects.create_user(
                    username=tenant.owner_email,
                    email=tenant.owner_email,
                    first_name=tenant.owner_name.split()[0] if tenant.owner_name else '',
                    last_name=' '.join(tenant.owner_name.split()[1:]) if len(tenant.owner_name.split()) > 1 else '',
                    is_staff=True,
                    is_active=True
                )
                
                # Add to owner group
                owner_group = Group.objects.get(name='مالک فروشگاه')
                owner_user.groups.add(owner_group)
                
                # Set role if User model has role field
                if hasattr(owner_user, 'role'):
                    owner_user.role = 'owner'
                    owner_user.save()
                
                return {
                    'success': True,
                    'details': f'Owner user created: {tenant.owner_email}'
                }
                
        except Exception as e:
            logger.error(f"Error creating admin user for {tenant.schema_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def deprovision_tenant(self, tenant: Tenant) -> Dict[str, Any]:
        """
        Deprovision a tenant (cleanup before deletion).
        
        Args:
            tenant: The tenant instance to deprovision
            
        Returns:
            Dict with success status and details
        """
        try:
            # Create backup before deletion
            backup_result = self._create_tenant_backup(tenant)
            
            # The actual schema deletion is handled by django-tenants
            # when auto_drop_schema is True
            
            return {
                'success': True,
                'message': 'Tenant deprovisioned successfully',
                'details': {
                    'backup_created': backup_result.get('success', False),
                    'schema_will_be_dropped': tenant.auto_drop_schema
                }
            }
            
        except Exception as e:
            logger.error(f"Error deprovisioning tenant {tenant.schema_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_tenant_backup(self, tenant: Tenant) -> Dict[str, Any]:
        """Create a backup of tenant data before deletion."""
        try:
            # This would integrate with the backup system
            # For now, just log the action
            logger.info(f"Backup requested for tenant {tenant.schema_name} before deletion")
            
            return {
                'success': True,
                'details': 'Backup logged for future implementation'
            }
            
        except Exception as e:
            logger.error(f"Error creating backup for {tenant.schema_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }


class TenantStatisticsService:
    """
    Service for collecting and calculating tenant usage metrics and statistics.
    """
    
    def __init__(self, tenant: Optional[Tenant] = None):
        self.tenant = tenant
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a tenant.
        
        Returns:
            Dict containing various statistics
        """
        if not self.tenant:
            return {}
        
        try:
            stats = {
                'basic_info': self._get_basic_info(),
                'usage_metrics': self._get_usage_metrics(),
                'activity_stats': self._get_activity_stats(),
                'performance_metrics': self._get_performance_metrics(),
                'storage_usage': self._get_storage_usage(),
                'user_statistics': self._get_user_statistics(),
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats for tenant {self.tenant.schema_name}: {e}")
            return {
                'error': str(e)
            }
    
    def _get_basic_info(self) -> Dict[str, Any]:
        """Get basic tenant information."""
        return {
            'tenant_id': self.tenant.id,
            'name': self.tenant.name,
            'schema_name': self.tenant.schema_name,
            'owner_name': self.tenant.owner_name,
            'owner_email': self.tenant.owner_email,
            'subscription_plan': self.tenant.subscription_plan,
            'is_active': self.tenant.is_active,
            'created_on': self.tenant.created_on.isoformat(),
            'days_active': (timezone.now().date() - self.tenant.created_on).days,
        }
    
    def _get_usage_metrics(self) -> Dict[str, Any]:
        """Get usage metrics for the tenant."""
        try:
            with schema_context(self.tenant.schema_name):
                from django.contrib.auth import get_user_model
                
                User = get_user_model()
                
                # Basic counts
                total_users = User.objects.count()
                active_users = User.objects.filter(is_active=True).count()
                
                # Try to get business-specific metrics
                metrics = {
                    'total_users': total_users,
                    'active_users': active_users,
                    'inactive_users': total_users - active_users,
                }
                
                # Add business-specific metrics if models exist
                try:
                    # These imports might fail if the models don't exist yet
                    from zargar.jewelry.models import JewelryItem
                    from zargar.customers.models import Customer
                    from zargar.gold_installments.models import GoldInstallment
                    
                    metrics.update({
                        'total_jewelry_items': JewelryItem.objects.count(),
                        'total_customers': Customer.objects.count(),
                        'active_installments': GoldInstallment.objects.filter(status='active').count(),
                    })
                    
                except ImportError:
                    # Models don't exist yet, skip business metrics
                    pass
                
                return metrics
                
        except Exception as e:
            logger.error(f"Error getting usage metrics for {self.tenant.schema_name}: {e}")
            return {
                'error': str(e)
            }
    
    def _get_activity_stats(self) -> Dict[str, Any]:
        """Get activity statistics from access logs."""
        try:
            # Get activity from the last 30 days
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            recent_logs = TenantAccessLog.objects.filter(
                tenant_schema=self.tenant.schema_name,
                timestamp__gte=thirty_days_ago
            )
            
            # Activity by day
            daily_activity = {}
            for i in range(30):
                date = (timezone.now() - timedelta(days=i)).date()
                daily_activity[date.isoformat()] = recent_logs.filter(
                    timestamp__date=date
                ).count()
            
            # Activity by action
            action_stats = recent_logs.values('action').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Most active users
            user_activity = recent_logs.values('username').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
            
            return {
                'total_actions_30_days': recent_logs.count(),
                'daily_activity': daily_activity,
                'action_breakdown': list(action_stats),
                'most_active_users': list(user_activity),
                'success_rate': self._calculate_success_rate(recent_logs),
            }
            
        except Exception as e:
            logger.error(f"Error getting activity stats for {self.tenant.schema_name}: {e}")
            return {
                'error': str(e)
            }
    
    def _calculate_success_rate(self, logs) -> float:
        """Calculate success rate from logs."""
        total_logs = logs.count()
        if total_logs == 0:
            return 100.0
        
        successful_logs = logs.filter(success=True).count()
        return round((successful_logs / total_logs) * 100, 2)
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the tenant."""
        try:
            # Get recent logs with duration data
            recent_logs = TenantAccessLog.objects.filter(
                tenant_schema=self.tenant.schema_name,
                duration_ms__isnull=False,
                timestamp__gte=timezone.now() - timedelta(days=7)
            )
            
            if not recent_logs.exists():
                return {
                    'message': 'No performance data available'
                }
            
            # Calculate performance metrics
            avg_response_time = recent_logs.aggregate(
                avg_duration=Avg('duration_ms')
            )['avg_duration']
            
            # Response time percentiles (approximation)
            durations = list(recent_logs.values_list('duration_ms', flat=True))
            durations.sort()
            
            if durations:
                p50 = durations[len(durations) // 2]
                p95 = durations[int(len(durations) * 0.95)]
                p99 = durations[int(len(durations) * 0.99)]
            else:
                p50 = p95 = p99 = 0
            
            return {
                'avg_response_time_ms': round(avg_response_time or 0, 2),
                'p50_response_time_ms': p50,
                'p95_response_time_ms': p95,
                'p99_response_time_ms': p99,
                'total_requests_7_days': recent_logs.count(),
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics for {self.tenant.schema_name}: {e}")
            return {
                'error': str(e)
            }
    
    def _get_storage_usage(self) -> Dict[str, Any]:
        """Get storage usage statistics for the tenant."""
        try:
            with connection.cursor() as cursor:
                # Get schema size
                cursor.execute("""
                    SELECT 
                        schemaname,
                        pg_size_pretty(sum(pg_total_relation_size(schemaname||'.'||tablename))::bigint) as size_pretty,
                        sum(pg_total_relation_size(schemaname||'.'||tablename))::bigint as size_bytes
                    FROM pg_tables 
                    WHERE schemaname = %s
                    GROUP BY schemaname
                """, [self.tenant.schema_name])
                
                result = cursor.fetchone()
                
                if result:
                    return {
                        'schema_size_pretty': result[1],
                        'schema_size_bytes': result[2],
                    }
                else:
                    return {
                        'schema_size_pretty': '0 bytes',
                        'schema_size_bytes': 0,
                    }
                    
        except Exception as e:
            logger.error(f"Error getting storage usage for {self.tenant.schema_name}: {e}")
            return {
                'error': str(e)
            }
    
    def _get_user_statistics(self) -> Dict[str, Any]:
        """Get user-related statistics."""
        try:
            with schema_context(self.tenant.schema_name):
                from django.contrib.auth import get_user_model
                from django.contrib.auth.models import Group
                
                User = get_user_model()
                
                # User counts by status
                total_users = User.objects.count()
                active_users = User.objects.filter(is_active=True).count()
                staff_users = User.objects.filter(is_staff=True).count()
                
                # Users by group
                group_stats = []
                for group in Group.objects.all():
                    group_stats.append({
                        'group_name': group.name,
                        'user_count': group.user_set.count()
                    })
                
                # Recent user activity
                recent_logins = User.objects.filter(
                    last_login__gte=timezone.now() - timedelta(days=30)
                ).count()
                
                return {
                    'total_users': total_users,
                    'active_users': active_users,
                    'inactive_users': total_users - active_users,
                    'staff_users': staff_users,
                    'groups': group_stats,
                    'recent_logins_30_days': recent_logins,
                }
                
        except Exception as e:
            logger.error(f"Error getting user statistics for {self.tenant.schema_name}: {e}")
            return {
                'error': str(e)
            }
    
    @classmethod
    def get_global_statistics(cls) -> Dict[str, Any]:
        """Get global statistics across all tenants."""
        try:
            # Basic tenant counts
            total_tenants = Tenant.objects.exclude(schema_name='public').count()
            active_tenants = Tenant.objects.exclude(schema_name='public').filter(is_active=True).count()
            
            # Subscription plan distribution
            plan_distribution = Tenant.objects.exclude(schema_name='public').values(
                'subscription_plan'
            ).annotate(count=Count('id')).order_by('subscription_plan')
            
            # Recent signups
            recent_signups = {}
            for days in [1, 7, 30]:
                cutoff_date = timezone.now().date() - timedelta(days=days)
                count = Tenant.objects.exclude(schema_name='public').filter(
                    created_on__gte=cutoff_date
                ).count()
                recent_signups[f'last_{days}_days'] = count
            
            # Activity statistics
            recent_activity = TenantAccessLog.objects.filter(
                timestamp__gte=timezone.now() - timedelta(days=30)
            ).count()
            
            return {
                'total_tenants': total_tenants,
                'active_tenants': active_tenants,
                'inactive_tenants': total_tenants - active_tenants,
                'plan_distribution': list(plan_distribution),
                'recent_signups': recent_signups,
                'recent_activity_30_days': recent_activity,
                'generated_at': timezone.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error getting global statistics: {e}")
            return {
                'error': str(e)
            }