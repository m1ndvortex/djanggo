#!/usr/bin/env python
"""
Disaster Recovery Validation Script for ZARGAR Jewelry SaaS Platform.

This script performs comprehensive validation of disaster recovery procedures
and system integrity after recovery operations.

Usage:
    docker-compose exec web python scripts/disaster_recovery_validate.py --full-check
    docker-compose exec web python scripts/disaster_recovery_validate.py --quick-check
    docker-compose exec web python scripts/disaster_recovery_validate.py --component=database
"""
import os
import sys
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.base')

import django
django.setup()

from django.db import connection, transaction
from django.core.management import call_command
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

from zargar.tenants.models import Tenant
from zargar.admin_panel.models import BackupJob, RestoreJob
from zargar.core.storage_utils import storage_manager
from zargar.admin_panel.disaster_recovery import disaster_recovery_manager


class DisasterRecoveryValidator:
    """
    Comprehensive disaster recovery validation system.
    
    Validates all aspects of system recovery including:
    - Database integrity and tenant isolation
    - Application functionality
    - Storage systems
    - Security configurations
    - Performance metrics
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validation_results = {
            'validation_id': f"dr_validation_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
            'started_at': timezone.now().isoformat(),
            'components': {},
            'overall_status': 'running',
            'summary': {}
        }
    
    def run_full_validation(self) -> Dict[str, Any]:
        """
        Run complete disaster recovery validation.
        
        Returns:
            Dict containing comprehensive validation results
        """
        self.logger.info("Starting full disaster recovery validation")
        
        try:
            # Database validation
            self.validation_results['components']['database'] = self._validate_database_integrity()
            
            # Application validation
            self.validation_results['components']['application'] = self._validate_application_functionality()
            
            # Storage validation
            self.validation_results['components']['storage'] = self._validate_storage_systems()
            
            # Security validation
            self.validation_results['components']['security'] = self._validate_security_configurations()
            
            # Performance validation
            self.validation_results['components']['performance'] = self._validate_performance_metrics()
            
            # Multi-tenant validation
            self.validation_results['components']['multi_tenant'] = self._validate_multi_tenant_isolation()
            
            # Backup system validation
            self.validation_results['components']['backup_system'] = self._validate_backup_systems()
            
            # Generate summary
            self._generate_validation_summary()
            
            self.validation_results['completed_at'] = timezone.now().isoformat()
            self.logger.info(f"Full validation completed: {self.validation_results['overall_status']}")
            
            return self.validation_results
            
        except Exception as e:
            self.validation_results['overall_status'] = 'error'
            self.validation_results['error'] = str(e)
            self.validation_results['completed_at'] = timezone.now().isoformat()
            
            self.logger.error(f"Full validation failed: {e}")
            return self.validation_results
    
    def run_quick_validation(self) -> Dict[str, Any]:
        """
        Run quick disaster recovery validation (essential checks only).
        
        Returns:
            Dict containing quick validation results
        """
        self.logger.info("Starting quick disaster recovery validation")
        
        try:
            # Essential database checks
            self.validation_results['components']['database'] = self._validate_database_connectivity()
            
            # Essential application checks
            self.validation_results['components']['application'] = self._validate_basic_application_functionality()
            
            # Essential storage checks
            self.validation_results['components']['storage'] = self._validate_storage_connectivity()
            
            # Generate summary
            self._generate_validation_summary()
            
            self.validation_results['completed_at'] = timezone.now().isoformat()
            self.logger.info(f"Quick validation completed: {self.validation_results['overall_status']}")
            
            return self.validation_results
            
        except Exception as e:
            self.validation_results['overall_status'] = 'error'
            self.validation_results['error'] = str(e)
            self.validation_results['completed_at'] = timezone.now().isoformat()
            
            self.logger.error(f"Quick validation failed: {e}")
            return self.validation_results
    
    def validate_component(self, component: str) -> Dict[str, Any]:
        """
        Validate a specific system component.
        
        Args:
            component: Component to validate (database, application, storage, etc.)
            
        Returns:
            Dict containing component validation results
        """
        self.logger.info(f"Starting {component} validation")
        
        try:
            if component == 'database':
                result = self._validate_database_integrity()
            elif component == 'application':
                result = self._validate_application_functionality()
            elif component == 'storage':
                result = self._validate_storage_systems()
            elif component == 'security':
                result = self._validate_security_configurations()
            elif component == 'performance':
                result = self._validate_performance_metrics()
            elif component == 'multi_tenant':
                result = self._validate_multi_tenant_isolation()
            elif component == 'backup_system':
                result = self._validate_backup_systems()
            else:
                raise ValueError(f"Unknown component: {component}")
            
            self.validation_results['components'][component] = result
            self.validation_results['completed_at'] = timezone.now().isoformat()
            
            return result
            
        except Exception as e:
            error_result = {
                'status': 'error',
                'error': str(e),
                'message': f'{component} validation failed'
            }
            
            self.validation_results['components'][component] = error_result
            self.validation_results['completed_at'] = timezone.now().isoformat()
            
            self.logger.error(f"{component} validation failed: {e}")
            return error_result
    
    def _validate_database_integrity(self) -> Dict[str, Any]:
        """Validate complete database integrity and tenant isolation."""
        validation_result = {
            'status': 'running',
            'checks': {},
            'message': 'Database integrity validation'
        }
        
        try:
            # Check database connectivity
            validation_result['checks']['connectivity'] = self._check_database_connectivity()
            
            # Check public schema
            validation_result['checks']['public_schema'] = self._check_public_schema()
            
            # Check tenant schemas
            validation_result['checks']['tenant_schemas'] = self._check_tenant_schemas()
            
            # Check data integrity
            validation_result['checks']['data_integrity'] = self._check_data_integrity()
            
            # Check tenant isolation
            validation_result['checks']['tenant_isolation'] = self._check_tenant_isolation()
            
            # Check database permissions
            validation_result['checks']['permissions'] = self._check_database_permissions()
            
            # Determine overall status
            all_passed = all(
                check['status'] == 'passed' 
                for check in validation_result['checks'].values()
            )
            
            validation_result['status'] = 'passed' if all_passed else 'failed'
            validation_result['message'] = 'Database integrity validation completed'
            
            return validation_result
            
        except Exception as e:
            validation_result['status'] = 'error'
            validation_result['error'] = str(e)
            validation_result['message'] = 'Database integrity validation failed'
            
            return validation_result
    
    def _validate_database_connectivity(self) -> Dict[str, Any]:
        """Validate basic database connectivity."""
        return self._check_database_connectivity()
    
    def _check_database_connectivity(self) -> Dict[str, Any]:
        """Check database connectivity and basic operations."""
        try:
            with connection.cursor() as cursor:
                # Test basic connectivity
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                if result and result[0] == 1:
                    # Test database version
                    cursor.execute("SELECT version()")
                    version = cursor.fetchone()[0]
                    
                    return {
                        'status': 'passed',
                        'message': 'Database connectivity successful',
                        'details': {
                            'connection': 'successful',
                            'version': version
                        }
                    }
                else:
                    return {
                        'status': 'failed',
                        'message': 'Database query returned unexpected result'
                    }
                    
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Database connectivity failed'
            }
    
    def _check_public_schema(self) -> Dict[str, Any]:
        """Check public schema integrity."""
        try:
            with connection.cursor() as cursor:
                # Check if public schema exists
                cursor.execute("""
                    SELECT schema_name 
                    FROM information_schema.schemata 
                    WHERE schema_name = 'public'
                """)
                
                public_schema = cursor.fetchone()
                
                if not public_schema:
                    return {
                        'status': 'failed',
                        'message': 'Public schema not found'
                    }
                
                # Check critical public schema tables
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                """)
                
                tables = [row[0] for row in cursor.fetchall()]
                
                # Expected public schema tables
                expected_tables = [
                    'tenants_tenant',
                    'tenants_domain',
                    'admin_impersonation_session',
                    'admin_backup_job',
                    'admin_restore_job'
                ]
                
                missing_tables = [table for table in expected_tables if table not in tables]
                
                if missing_tables:
                    return {
                        'status': 'failed',
                        'message': f'Missing public schema tables: {missing_tables}',
                        'details': {
                            'found_tables': tables,
                            'missing_tables': missing_tables
                        }
                    }
                
                return {
                    'status': 'passed',
                    'message': 'Public schema integrity verified',
                    'details': {
                        'tables_found': len(tables),
                        'tables': tables
                    }
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Public schema check failed'
            }
    
    def _check_tenant_schemas(self) -> Dict[str, Any]:
        """Check tenant schema integrity."""
        try:
            # Get all tenants from public schema
            tenants = Tenant.objects.all()
            
            if not tenants.exists():
                return {
                    'status': 'warning',
                    'message': 'No tenants found in system'
                }
            
            schema_results = {}
            
            for tenant in tenants:
                schema_name = tenant.schema_name
                
                try:
                    with connection.cursor() as cursor:
                        # Check if tenant schema exists
                        cursor.execute("""
                            SELECT schema_name 
                            FROM information_schema.schemata 
                            WHERE schema_name = %s
                        """, [schema_name])
                        
                        schema_exists = cursor.fetchone()
                        
                        if not schema_exists:
                            schema_results[schema_name] = {
                                'status': 'failed',
                                'message': 'Schema not found'
                            }
                            continue
                        
                        # Check tenant schema tables
                        cursor.execute("""
                            SELECT table_name 
                            FROM information_schema.tables 
                            WHERE table_schema = %s 
                            AND table_type = 'BASE TABLE'
                        """, [schema_name])
                        
                        tables = [row[0] for row in cursor.fetchall()]
                        
                        # Expected tenant tables (core business models)
                        expected_tables = [
                            'core_user',
                            'jewelry_jewelryitem',
                            'customers_customer',
                            'accounting_chartofaccounts'
                        ]
                        
                        missing_tables = [table for table in expected_tables if table not in tables]
                        
                        if missing_tables:
                            schema_results[schema_name] = {
                                'status': 'failed',
                                'message': f'Missing tables: {missing_tables}',
                                'details': {
                                    'found_tables': len(tables),
                                    'missing_tables': missing_tables
                                }
                            }
                        else:
                            schema_results[schema_name] = {
                                'status': 'passed',
                                'message': 'Schema integrity verified',
                                'details': {
                                    'tables_found': len(tables)
                                }
                            }
                            
                except Exception as e:
                    schema_results[schema_name] = {
                        'status': 'error',
                        'error': str(e),
                        'message': 'Schema check failed'
                    }
            
            # Calculate overall status
            all_passed = all(
                result['status'] == 'passed' 
                for result in schema_results.values()
            )
            
            return {
                'status': 'passed' if all_passed else 'failed',
                'message': f'Tenant schema validation completed for {len(schema_results)} schemas',
                'details': {
                    'schemas_checked': len(schema_results),
                    'schema_results': schema_results
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Tenant schema check failed'
            }
    
    def _check_data_integrity(self) -> Dict[str, Any]:
        """Check data integrity across schemas."""
        try:
            integrity_results = {}
            
            # Check public schema data
            with connection.cursor() as cursor:
                # Check tenant count
                cursor.execute("SELECT COUNT(*) FROM tenants_tenant")
                tenant_count = cursor.fetchone()[0]
                
                integrity_results['tenant_count'] = {
                    'count': tenant_count,
                    'status': 'passed' if tenant_count > 0 else 'warning'
                }
                
                # Check domain count
                cursor.execute("SELECT COUNT(*) FROM tenants_domain")
                domain_count = cursor.fetchone()[0]
                
                integrity_results['domain_count'] = {
                    'count': domain_count,
                    'status': 'passed' if domain_count > 0 else 'warning'
                }
            
            # Check tenant data integrity
            tenants = Tenant.objects.all()[:5]  # Check first 5 tenants
            
            for tenant in tenants:
                try:
                    # Switch to tenant schema
                    connection.set_tenant(tenant)
                    
                    with connection.cursor() as cursor:
                        # Check user count in tenant
                        cursor.execute("SELECT COUNT(*) FROM core_user")
                        user_count = cursor.fetchone()[0]
                        
                        integrity_results[f'tenant_{tenant.schema_name}_users'] = {
                            'count': user_count,
                            'status': 'passed' if user_count >= 0 else 'failed'
                        }
                        
                except Exception as e:
                    integrity_results[f'tenant_{tenant.schema_name}'] = {
                        'status': 'error',
                        'error': str(e)
                    }
                finally:
                    # Reset to public schema
                    connection.set_schema_to_public()
            
            # Calculate overall status
            all_passed = all(
                result.get('status', 'failed') in ['passed', 'warning']
                for result in integrity_results.values()
            )
            
            return {
                'status': 'passed' if all_passed else 'failed',
                'message': 'Data integrity validation completed',
                'details': integrity_results
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Data integrity check failed'
            }
    
    def _check_tenant_isolation(self) -> Dict[str, Any]:
        """Check tenant isolation is working correctly."""
        try:
            tenants = list(Tenant.objects.all()[:2])  # Check first 2 tenants
            
            if len(tenants) < 2:
                return {
                    'status': 'warning',
                    'message': 'Need at least 2 tenants to test isolation'
                }
            
            tenant1, tenant2 = tenants[0], tenants[1]
            isolation_results = {}
            
            # Test tenant 1 isolation
            try:
                connection.set_tenant(tenant1)
                
                with connection.cursor() as cursor:
                    # Try to access tenant 2's schema (should fail)
                    cursor.execute(f"""
                        SELECT COUNT(*) 
                        FROM information_schema.tables 
                        WHERE table_schema = '{tenant2.schema_name}'
                    """)
                    
                    tenant2_tables = cursor.fetchone()[0]
                    
                    # Should not be able to see tenant 2's tables from tenant 1's context
                    isolation_results['tenant1_isolation'] = {
                        'status': 'passed' if tenant2_tables == 0 else 'failed',
                        'message': f'Tenant 1 can see {tenant2_tables} tables from tenant 2'
                    }
                    
            except Exception as e:
                isolation_results['tenant1_isolation'] = {
                    'status': 'error',
                    'error': str(e)
                }
            finally:
                connection.set_schema_to_public()
            
            # Test tenant 2 isolation
            try:
                connection.set_tenant(tenant2)
                
                with connection.cursor() as cursor:
                    # Try to access tenant 1's schema (should fail)
                    cursor.execute(f"""
                        SELECT COUNT(*) 
                        FROM information_schema.tables 
                        WHERE table_schema = '{tenant1.schema_name}'
                    """)
                    
                    tenant1_tables = cursor.fetchone()[0]
                    
                    # Should not be able to see tenant 1's tables from tenant 2's context
                    isolation_results['tenant2_isolation'] = {
                        'status': 'passed' if tenant1_tables == 0 else 'failed',
                        'message': f'Tenant 2 can see {tenant1_tables} tables from tenant 1'
                    }
                    
            except Exception as e:
                isolation_results['tenant2_isolation'] = {
                    'status': 'error',
                    'error': str(e)
                }
            finally:
                connection.set_schema_to_public()
            
            # Calculate overall status
            all_passed = all(
                result['status'] == 'passed' 
                for result in isolation_results.values()
            )
            
            return {
                'status': 'passed' if all_passed else 'failed',
                'message': 'Tenant isolation validation completed',
                'details': isolation_results
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Tenant isolation check failed'
            }
    
    def _check_database_permissions(self) -> Dict[str, Any]:
        """Check database user permissions and security."""
        try:
            with connection.cursor() as cursor:
                # Check current user
                cursor.execute("SELECT current_user")
                current_user = cursor.fetchone()[0]
                
                # Check user permissions
                cursor.execute("""
                    SELECT 
                        has_database_privilege(current_user, current_database(), 'CONNECT') as can_connect,
                        has_database_privilege(current_user, current_database(), 'CREATE') as can_create
                """)
                
                permissions = cursor.fetchone()
                can_connect, can_create = permissions
                
                return {
                    'status': 'passed' if can_connect else 'failed',
                    'message': 'Database permissions validated',
                    'details': {
                        'current_user': current_user,
                        'can_connect': can_connect,
                        'can_create': can_create
                    }
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Database permissions check failed'
            }
    
    def _validate_application_functionality(self) -> Dict[str, Any]:
        """Validate application functionality."""
        validation_result = {
            'status': 'running',
            'checks': {},
            'message': 'Application functionality validation'
        }
        
        try:
            # Check Django settings
            validation_result['checks']['django_settings'] = self._check_django_settings()
            
            # Check installed apps
            validation_result['checks']['installed_apps'] = self._check_installed_apps()
            
            # Check URL routing
            validation_result['checks']['url_routing'] = self._check_url_routing()
            
            # Check static files
            validation_result['checks']['static_files'] = self._check_static_files()
            
            # Check template system
            validation_result['checks']['template_system'] = self._check_template_system()
            
            # Determine overall status
            all_passed = all(
                check['status'] == 'passed' 
                for check in validation_result['checks'].values()
            )
            
            validation_result['status'] = 'passed' if all_passed else 'failed'
            validation_result['message'] = 'Application functionality validation completed'
            
            return validation_result
            
        except Exception as e:
            validation_result['status'] = 'error'
            validation_result['error'] = str(e)
            validation_result['message'] = 'Application functionality validation failed'
            
            return validation_result
    
    def _validate_basic_application_functionality(self) -> Dict[str, Any]:
        """Validate basic application functionality (quick check)."""
        validation_result = {
            'status': 'running',
            'checks': {},
            'message': 'Basic application functionality validation'
        }
        
        try:
            # Check Django settings
            validation_result['checks']['django_settings'] = self._check_django_settings()
            
            # Check installed apps
            validation_result['checks']['installed_apps'] = self._check_installed_apps()
            
            # Determine overall status
            all_passed = all(
                check['status'] == 'passed' 
                for check in validation_result['checks'].values()
            )
            
            validation_result['status'] = 'passed' if all_passed else 'failed'
            validation_result['message'] = 'Basic application functionality validation completed'
            
            return validation_result
            
        except Exception as e:
            validation_result['status'] = 'error'
            validation_result['error'] = str(e)
            validation_result['message'] = 'Basic application functionality validation failed'
            
            return validation_result
    
    def _check_django_settings(self) -> Dict[str, Any]:
        """Check Django settings configuration."""
        try:
            # Check critical settings
            critical_settings = {
                'SECRET_KEY': bool(getattr(settings, 'SECRET_KEY', None)),
                'DEBUG': hasattr(settings, 'DEBUG'),
                'DATABASES': bool(getattr(settings, 'DATABASES', None)),
                'INSTALLED_APPS': bool(getattr(settings, 'INSTALLED_APPS', None)),
                'MIDDLEWARE': bool(getattr(settings, 'MIDDLEWARE', None))
            }
            
            missing_settings = [
                setting for setting, exists in critical_settings.items() 
                if not exists
            ]
            
            if missing_settings:
                return {
                    'status': 'failed',
                    'message': f'Missing critical settings: {missing_settings}',
                    'details': critical_settings
                }
            
            return {
                'status': 'passed',
                'message': 'Django settings validated',
                'details': critical_settings
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Django settings check failed'
            }
    
    def _check_installed_apps(self) -> Dict[str, Any]:
        """Check installed Django apps."""
        try:
            installed_apps = getattr(settings, 'INSTALLED_APPS', [])
            
            # Expected critical apps
            expected_apps = [
                'django.contrib.admin',
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django_tenants',
                'zargar.core',
                'zargar.tenants',
                'zargar.admin_panel'
            ]
            
            missing_apps = [
                app for app in expected_apps 
                if app not in installed_apps
            ]
            
            if missing_apps:
                return {
                    'status': 'failed',
                    'message': f'Missing critical apps: {missing_apps}',
                    'details': {
                        'installed_count': len(installed_apps),
                        'missing_apps': missing_apps
                    }
                }
            
            return {
                'status': 'passed',
                'message': 'Installed apps validated',
                'details': {
                    'installed_count': len(installed_apps),
                    'critical_apps_present': True
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Installed apps check failed'
            }
    
    def _check_url_routing(self) -> Dict[str, Any]:
        """Check URL routing configuration."""
        try:
            from django.urls import reverse
            from django.test import Client
            
            # Test critical URL patterns
            test_urls = [
                ('admin:index', 'Admin panel'),
                # Add more URL tests as needed
            ]
            
            url_results = {}
            
            for url_name, description in test_urls:
                try:
                    url = reverse(url_name)
                    url_results[url_name] = {
                        'status': 'passed',
                        'url': url,
                        'description': description
                    }
                except Exception as e:
                    url_results[url_name] = {
                        'status': 'failed',
                        'error': str(e),
                        'description': description
                    }
            
            all_passed = all(
                result['status'] == 'passed' 
                for result in url_results.values()
            )
            
            return {
                'status': 'passed' if all_passed else 'failed',
                'message': 'URL routing validated',
                'details': url_results
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'URL routing check failed'
            }
    
    def _check_static_files(self) -> Dict[str, Any]:
        """Check static files configuration."""
        try:
            static_root = getattr(settings, 'STATIC_ROOT', None)
            static_url = getattr(settings, 'STATIC_URL', None)
            
            if not static_url:
                return {
                    'status': 'failed',
                    'message': 'STATIC_URL not configured'
                }
            
            return {
                'status': 'passed',
                'message': 'Static files configuration validated',
                'details': {
                    'static_url': static_url,
                    'static_root': static_root
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Static files check failed'
            }
    
    def _check_template_system(self) -> Dict[str, Any]:
        """Check template system configuration."""
        try:
            templates = getattr(settings, 'TEMPLATES', [])
            
            if not templates:
                return {
                    'status': 'failed',
                    'message': 'No template engines configured'
                }
            
            # Check for Django template engine
            django_engine = None
            for template in templates:
                if template.get('BACKEND') == 'django.template.backends.django.DjangoTemplates':
                    django_engine = template
                    break
            
            if not django_engine:
                return {
                    'status': 'failed',
                    'message': 'Django template engine not found'
                }
            
            return {
                'status': 'passed',
                'message': 'Template system validated',
                'details': {
                    'engines_count': len(templates),
                    'django_engine_present': True
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Template system check failed'
            }
    
    def _validate_storage_systems(self) -> Dict[str, Any]:
        """Validate storage systems."""
        validation_result = {
            'status': 'running',
            'checks': {},
            'message': 'Storage systems validation'
        }
        
        try:
            # Check storage connectivity
            validation_result['checks']['connectivity'] = self._validate_storage_connectivity()
            
            # Check storage configuration
            validation_result['checks']['configuration'] = self._check_storage_configuration()
            
            # Test file operations
            validation_result['checks']['file_operations'] = self._test_storage_file_operations()
            
            # Determine overall status
            all_passed = all(
                check['status'] == 'passed' 
                for check in validation_result['checks'].values()
            )
            
            validation_result['status'] = 'passed' if all_passed else 'failed'
            validation_result['message'] = 'Storage systems validation completed'
            
            return validation_result
            
        except Exception as e:
            validation_result['status'] = 'error'
            validation_result['error'] = str(e)
            validation_result['message'] = 'Storage systems validation failed'
            
            return validation_result
    
    def _validate_storage_connectivity(self) -> Dict[str, Any]:
        """Validate storage connectivity."""
        try:
            connectivity_results = storage_manager.test_connectivity()
            
            all_connected = all(
                result['connected'] 
                for result in connectivity_results.values()
            )
            
            return {
                'status': 'passed' if all_connected else 'failed',
                'message': 'Storage connectivity validated',
                'details': connectivity_results
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Storage connectivity check failed'
            }
    
    def _check_storage_configuration(self) -> Dict[str, Any]:
        """Check storage configuration."""
        try:
            # Check required storage settings
            storage_settings = {
                'CLOUDFLARE_R2_ACCESS_KEY': bool(getattr(settings, 'CLOUDFLARE_R2_ACCESS_KEY', None)),
                'CLOUDFLARE_R2_SECRET_KEY': bool(getattr(settings, 'CLOUDFLARE_R2_SECRET_KEY', None)),
                'CLOUDFLARE_R2_BUCKET': bool(getattr(settings, 'CLOUDFLARE_R2_BUCKET', None)),
                'BACKBLAZE_B2_ACCESS_KEY': bool(getattr(settings, 'BACKBLAZE_B2_ACCESS_KEY', None)),
                'BACKBLAZE_B2_SECRET_KEY': bool(getattr(settings, 'BACKBLAZE_B2_SECRET_KEY', None)),
                'BACKBLAZE_B2_BUCKET': bool(getattr(settings, 'BACKBLAZE_B2_BUCKET', None))
            }
            
            missing_settings = [
                setting for setting, configured in storage_settings.items() 
                if not configured
            ]
            
            if missing_settings:
                return {
                    'status': 'warning',
                    'message': f'Missing storage settings: {missing_settings}',
                    'details': storage_settings
                }
            
            return {
                'status': 'passed',
                'message': 'Storage configuration validated',
                'details': storage_settings
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Storage configuration check failed'
            }
    
    def _test_storage_file_operations(self) -> Dict[str, Any]:
        """Test storage file operations."""
        try:
            # Create test file
            test_content = f"DR validation test - {timezone.now().isoformat()}".encode()
            test_filename = f"dr_validation_test_{timezone.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            # Test upload
            upload_result = storage_manager.upload_backup_file(
                f"validation_tests/{test_filename}", 
                test_content, 
                use_redundant=False
            )
            
            if not upload_result['success']:
                return {
                    'status': 'failed',
                    'message': 'File upload test failed',
                    'details': upload_result
                }
            
            # Test download
            downloaded_content = storage_manager.download_backup_file(f"validation_tests/{test_filename}")
            
            if downloaded_content != test_content:
                return {
                    'status': 'failed',
                    'message': 'File download test failed - content mismatch'
                }
            
            # Test delete
            delete_result = storage_manager.delete_backup_file(
                f"validation_tests/{test_filename}", 
                from_all_backends=False
            )
            
            if not delete_result['success']:
                return {
                    'status': 'warning',
                    'message': 'File delete test failed',
                    'details': delete_result
                }
            
            return {
                'status': 'passed',
                'message': 'Storage file operations validated',
                'details': {
                    'upload': 'success',
                    'download': 'success',
                    'delete': 'success'
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Storage file operations test failed'
            }
    
    def _validate_security_configurations(self) -> Dict[str, Any]:
        """Validate security configurations."""
        validation_result = {
            'status': 'running',
            'checks': {},
            'message': 'Security configurations validation'
        }
        
        try:
            # Check Django security settings
            validation_result['checks']['django_security'] = self._check_django_security_settings()
            
            # Check authentication system
            validation_result['checks']['authentication'] = self._check_authentication_system()
            
            # Check HTTPS configuration
            validation_result['checks']['https'] = self._check_https_configuration()
            
            # Determine overall status
            all_passed = all(
                check['status'] in ['passed', 'warning']
                for check in validation_result['checks'].values()
            )
            
            validation_result['status'] = 'passed' if all_passed else 'failed'
            validation_result['message'] = 'Security configurations validation completed'
            
            return validation_result
            
        except Exception as e:
            validation_result['status'] = 'error'
            validation_result['error'] = str(e)
            validation_result['message'] = 'Security configurations validation failed'
            
            return validation_result
    
    def _check_django_security_settings(self) -> Dict[str, Any]:
        """Check Django security settings."""
        try:
            security_settings = {
                'SECRET_KEY': bool(getattr(settings, 'SECRET_KEY', None)),
                'DEBUG': not getattr(settings, 'DEBUG', True),  # DEBUG should be False in production
                'ALLOWED_HOSTS': bool(getattr(settings, 'ALLOWED_HOSTS', [])),
                'SECURE_SSL_REDIRECT': getattr(settings, 'SECURE_SSL_REDIRECT', False),
                'SECURE_HSTS_SECONDS': bool(getattr(settings, 'SECURE_HSTS_SECONDS', 0)),
                'CSRF_COOKIE_SECURE': getattr(settings, 'CSRF_COOKIE_SECURE', False),
                'SESSION_COOKIE_SECURE': getattr(settings, 'SESSION_COOKIE_SECURE', False)
            }
            
            security_issues = [
                setting for setting, secure in security_settings.items() 
                if not secure
            ]
            
            if security_issues:
                return {
                    'status': 'warning',
                    'message': f'Security settings need attention: {security_issues}',
                    'details': security_settings
                }
            
            return {
                'status': 'passed',
                'message': 'Django security settings validated',
                'details': security_settings
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Django security settings check failed'
            }
    
    def _check_authentication_system(self) -> Dict[str, Any]:
        """Check authentication system."""
        try:
            # Check if User model is accessible
            User = get_user_model()
            
            # Check if we can query users (basic test)
            user_count = User.objects.count()
            
            return {
                'status': 'passed',
                'message': 'Authentication system validated',
                'details': {
                    'user_model': User.__name__,
                    'user_count': user_count
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Authentication system check failed'
            }
    
    def _check_https_configuration(self) -> Dict[str, Any]:
        """Check HTTPS configuration."""
        try:
            # This is a basic check - in a real environment, you'd test actual HTTPS
            https_settings = {
                'SECURE_SSL_REDIRECT': getattr(settings, 'SECURE_SSL_REDIRECT', False),
                'SECURE_HSTS_SECONDS': getattr(settings, 'SECURE_HSTS_SECONDS', 0),
                'SECURE_HSTS_INCLUDE_SUBDOMAINS': getattr(settings, 'SECURE_HSTS_INCLUDE_SUBDOMAINS', False),
                'SECURE_HSTS_PRELOAD': getattr(settings, 'SECURE_HSTS_PRELOAD', False)
            }
            
            return {
                'status': 'passed',
                'message': 'HTTPS configuration checked',
                'details': https_settings
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'HTTPS configuration check failed'
            }
    
    def _validate_performance_metrics(self) -> Dict[str, Any]:
        """Validate system performance metrics."""
        validation_result = {
            'status': 'running',
            'checks': {},
            'message': 'Performance metrics validation'
        }
        
        try:
            # Check database performance
            validation_result['checks']['database_performance'] = self._check_database_performance()
            
            # Check memory usage
            validation_result['checks']['memory_usage'] = self._check_memory_usage()
            
            # Check response times
            validation_result['checks']['response_times'] = self._check_response_times()
            
            # Determine overall status
            all_passed = all(
                check['status'] in ['passed', 'warning']
                for check in validation_result['checks'].values()
            )
            
            validation_result['status'] = 'passed' if all_passed else 'failed'
            validation_result['message'] = 'Performance metrics validation completed'
            
            return validation_result
            
        except Exception as e:
            validation_result['status'] = 'error'
            validation_result['error'] = str(e)
            validation_result['message'] = 'Performance metrics validation failed'
            
            return validation_result
    
    def _check_database_performance(self) -> Dict[str, Any]:
        """Check database performance."""
        try:
            import time
            
            # Simple query performance test
            start_time = time.time()
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM tenants_tenant")
                result = cursor.fetchone()
            
            query_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Performance thresholds
            if query_time < 100:
                status = 'passed'
                message = f'Database performance good ({query_time:.2f}ms)'
            elif query_time < 500:
                status = 'warning'
                message = f'Database performance acceptable ({query_time:.2f}ms)'
            else:
                status = 'failed'
                message = f'Database performance poor ({query_time:.2f}ms)'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'query_time_ms': query_time,
                    'result_count': result[0] if result else 0
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Database performance check failed'
            }
    
    def _check_memory_usage(self) -> Dict[str, Any]:
        """Check memory usage."""
        try:
            import psutil
            
            # Get memory usage
            memory = psutil.virtual_memory()
            
            # Memory thresholds
            if memory.percent < 70:
                status = 'passed'
                message = f'Memory usage normal ({memory.percent:.1f}%)'
            elif memory.percent < 85:
                status = 'warning'
                message = f'Memory usage high ({memory.percent:.1f}%)'
            else:
                status = 'failed'
                message = f'Memory usage critical ({memory.percent:.1f}%)'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'total_gb': memory.total / (1024**3),
                    'available_gb': memory.available / (1024**3),
                    'percent_used': memory.percent
                }
            }
            
        except ImportError:
            return {
                'status': 'warning',
                'message': 'psutil not available for memory check'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Memory usage check failed'
            }
    
    def _check_response_times(self) -> Dict[str, Any]:
        """Check application response times."""
        try:
            from django.test import Client
            import time
            
            client = Client()
            
            # Test admin panel response time
            start_time = time.time()
            
            try:
                response = client.get('/admin/')
                response_time = (time.time() - start_time) * 1000
                
                if response_time < 200:
                    status = 'passed'
                    message = f'Response time good ({response_time:.2f}ms)'
                elif response_time < 500:
                    status = 'warning'
                    message = f'Response time acceptable ({response_time:.2f}ms)'
                else:
                    status = 'failed'
                    message = f'Response time poor ({response_time:.2f}ms)'
                
                return {
                    'status': status,
                    'message': message,
                    'details': {
                        'response_time_ms': response_time,
                        'status_code': response.status_code
                    }
                }
                
            except Exception as e:
                return {
                    'status': 'error',
                    'error': str(e),
                    'message': 'Response time test failed'
                }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Response time check failed'
            }
    
    def _validate_multi_tenant_isolation(self) -> Dict[str, Any]:
        """Validate multi-tenant isolation."""
        return self._check_tenant_isolation()
    
    def _validate_backup_systems(self) -> Dict[str, Any]:
        """Validate backup systems."""
        validation_result = {
            'status': 'running',
            'checks': {},
            'message': 'Backup systems validation'
        }
        
        try:
            # Check backup job models
            validation_result['checks']['backup_models'] = self._check_backup_models()
            
            # Check disaster recovery system
            validation_result['checks']['disaster_recovery'] = self._check_disaster_recovery_system()
            
            # Check backup storage
            validation_result['checks']['backup_storage'] = self._check_backup_storage()
            
            # Determine overall status
            all_passed = all(
                check['status'] in ['passed', 'warning']
                for check in validation_result['checks'].values()
            )
            
            validation_result['status'] = 'passed' if all_passed else 'failed'
            validation_result['message'] = 'Backup systems validation completed'
            
            return validation_result
            
        except Exception as e:
            validation_result['status'] = 'error'
            validation_result['error'] = str(e)
            validation_result['message'] = 'Backup systems validation failed'
            
            return validation_result
    
    def _check_backup_models(self) -> Dict[str, Any]:
        """Check backup-related models."""
        try:
            # Check if backup models are accessible
            backup_job_count = BackupJob.objects.count()
            restore_job_count = RestoreJob.objects.count()
            
            return {
                'status': 'passed',
                'message': 'Backup models validated',
                'details': {
                    'backup_jobs': backup_job_count,
                    'restore_jobs': restore_job_count
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Backup models check failed'
            }
    
    def _check_disaster_recovery_system(self) -> Dict[str, Any]:
        """Check disaster recovery system."""
        try:
            # Test disaster recovery manager
            dr_test_results = disaster_recovery_manager.test_disaster_recovery_procedures()
            
            if dr_test_results['overall_status'] == 'passed':
                return {
                    'status': 'passed',
                    'message': 'Disaster recovery system validated',
                    'details': dr_test_results
                }
            else:
                return {
                    'status': 'warning',
                    'message': 'Disaster recovery system has issues',
                    'details': dr_test_results
                }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Disaster recovery system check failed'
            }
    
    def _check_backup_storage(self) -> Dict[str, Any]:
        """Check backup storage availability."""
        try:
            # List backup files
            backup_files = storage_manager.list_backup_files('disaster_recovery/')
            
            return {
                'status': 'passed',
                'message': 'Backup storage validated',
                'details': {
                    'backup_files_count': len(backup_files),
                    'recent_backups': backup_files[-5:] if backup_files else []
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Backup storage check failed'
            }
    
    def _generate_validation_summary(self):
        """Generate validation summary."""
        total_checks = 0
        passed_checks = 0
        failed_checks = 0
        warning_checks = 0
        error_checks = 0
        
        for component, component_result in self.validation_results['components'].items():
            if 'checks' in component_result:
                for check_name, check_result in component_result['checks'].items():
                    total_checks += 1
                    status = check_result.get('status', 'unknown')
                    
                    if status == 'passed':
                        passed_checks += 1
                    elif status == 'failed':
                        failed_checks += 1
                    elif status == 'warning':
                        warning_checks += 1
                    elif status == 'error':
                        error_checks += 1
            else:
                total_checks += 1
                status = component_result.get('status', 'unknown')
                
                if status == 'passed':
                    passed_checks += 1
                elif status == 'failed':
                    failed_checks += 1
                elif status == 'warning':
                    warning_checks += 1
                elif status == 'error':
                    error_checks += 1
        
        # Determine overall status
        if error_checks > 0 or failed_checks > 0:
            overall_status = 'failed'
        elif warning_checks > 0:
            overall_status = 'warning'
        else:
            overall_status = 'passed'
        
        self.validation_results['overall_status'] = overall_status
        self.validation_results['summary'] = {
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': failed_checks,
            'warning_checks': warning_checks,
            'error_checks': error_checks,
            'success_rate': (passed_checks / total_checks * 100) if total_checks > 0 else 0
        }


def main():
    """Main function to run disaster recovery validation."""
    parser = argparse.ArgumentParser(description='ZARGAR Disaster Recovery Validation')
    parser.add_argument('--full-check', action='store_true', help='Run full validation')
    parser.add_argument('--quick-check', action='store_true', help='Run quick validation')
    parser.add_argument('--component', type=str, help='Validate specific component')
    parser.add_argument('--output', type=str, help='Output file for results')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    validator = DisasterRecoveryValidator()
    
    try:
        if args.full_check:
            print("🔍 Running full disaster recovery validation...")
            results = validator.run_full_validation()
        elif args.quick_check:
            print("⚡ Running quick disaster recovery validation...")
            results = validator.run_quick_validation()
        elif args.component:
            print(f"🔧 Validating {args.component} component...")
            results = validator.validate_component(args.component)
        else:
            print("❌ Please specify --full-check, --quick-check, or --component")
            sys.exit(1)
        
        # Print results
        print(f"\n📊 Validation Results")
        print("=" * 50)
        print(f"Status: {results.get('overall_status', 'unknown').upper()}")
        
        if 'summary' in results:
            summary = results['summary']
            print(f"Total Checks: {summary['total_checks']}")
            print(f"Passed: {summary['passed_checks']}")
            print(f"Failed: {summary['failed_checks']}")
            print(f"Warnings: {summary['warning_checks']}")
            print(f"Errors: {summary['error_checks']}")
            print(f"Success Rate: {summary['success_rate']:.1f}%")
        
        # Save results to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {args.output}")
        
        # Print detailed results if verbose
        if args.verbose:
            print(f"\n📋 Detailed Results:")
            print(json.dumps(results, indent=2, default=str))
        
        # Exit with appropriate code
        if results.get('overall_status') == 'passed':
            print("\n✅ All validations passed!")
            sys.exit(0)
        elif results.get('overall_status') == 'warning':
            print("\n⚠️  Validation completed with warnings")
            sys.exit(0)
        else:
            print("\n❌ Validation failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Validation script failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()