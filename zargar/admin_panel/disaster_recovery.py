"""
Complete Disaster Recovery System for ZARGAR Jewelry SaaS Platform.

This module implements comprehensive disaster recovery capabilities including:
- Step-by-step system rebuild procedures
- Automated recovery workflows
- Disaster recovery testing and validation
- Complete service restoration from backups

Requirements: 5.11, 5.12
"""
import os
import json
import logging
import subprocess
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from django.core.management import call_command
from django.db import connection, transaction
from django.core.files.base import ContentFile

from .models import BackupJob, RestoreJob
from zargar.core.storage_utils import storage_manager
from zargar.tenants.models import Tenant


logger = logging.getLogger(__name__)


class DisasterRecoveryError(Exception):
    """Custom exception for disaster recovery operations."""
    pass


class DisasterRecoveryManager:
    """
    Comprehensive disaster recovery management system.
    
    Handles complete system rebuild from backups with separation of:
    - Data (PostgreSQL database dumps)
    - Configuration (docker-compose.yml, nginx.conf, .env files)
    - Code (Git repository)
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.storage = storage_manager
        
    def create_disaster_recovery_plan(self) -> Dict[str, Any]:
        """
        Create a comprehensive disaster recovery plan document.
        
        Returns:
            Dict containing complete step-by-step recovery procedures
        """
        plan = {
            "disaster_recovery_plan": {
                "version": "1.0",
                "created_at": timezone.now().isoformat(),
                "overview": {
                    "philosophy": "Separation of Data, Configuration, and Code",
                    "components": {
                        "data": "Complete PostgreSQL database dumps (public + all tenant schemas)",
                        "configuration": "Environment files, Docker configs, Nginx configs",
                        "code": "Git repository with application source code"
                    },
                    "recovery_time_objective": "4 hours",
                    "recovery_point_objective": "24 hours"
                },
                "prerequisites": {
                    "server_requirements": {
                        "cpu": "4-8 cores minimum",
                        "memory": "16-32GB RAM minimum",
                        "storage": "500GB+ SSD storage",
                        "network": "Stable internet connection"
                    },
                    "software_requirements": [
                        "Docker Engine 20.10+",
                        "Docker Compose 2.0+",
                        "Git 2.30+",
                        "OpenSSL for encryption",
                        "PostgreSQL client tools"
                    ],
                    "access_requirements": [
                        "Cloudflare R2 access credentials",
                        "Backblaze B2 access credentials",
                        "Git repository access",
                        "Domain DNS management access"
                    ]
                },
                "recovery_procedures": self._generate_recovery_procedures(),
                "validation_steps": self._generate_validation_steps(),
                "rollback_procedures": self._generate_rollback_procedures(),
                "emergency_contacts": self._generate_emergency_contacts()
            }
        }
        
        return plan
    
    def _generate_recovery_procedures(self) -> Dict[str, Any]:
        """Generate detailed step-by-step recovery procedures."""
        return {
            "phase_1_server_preparation": {
                "description": "Prepare new server environment",
                "estimated_time": "30 minutes",
                "steps": [
                    {
                        "step": 1,
                        "title": "Server Setup",
                        "description": "Set up new server with required specifications",
                        "commands": [
                            "# Update system packages",
                            "sudo apt update && sudo apt upgrade -y",
                            "sudo apt install -y curl wget git openssl postgresql-client"
                        ],
                        "validation": "Verify all packages installed successfully"
                    },
                    {
                        "step": 2,
                        "title": "Install Docker",
                        "description": "Install Docker Engine and Docker Compose",
                        "commands": [
                            "# Install Docker",
                            "curl -fsSL https://get.docker.com -o get-docker.sh",
                            "sudo sh get-docker.sh",
                            "sudo usermod -aG docker $USER",
                            "",
                            "# Install Docker Compose",
                            "sudo curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)\" -o /usr/local/bin/docker-compose",
                            "sudo chmod +x /usr/local/bin/docker-compose"
                        ],
                        "validation": "docker --version && docker-compose --version"
                    },
                    {
                        "step": 3,
                        "title": "Create Application Directory",
                        "description": "Create directory structure for application",
                        "commands": [
                            "mkdir -p /opt/zargar",
                            "cd /opt/zargar",
                            "mkdir -p backups logs data"
                        ],
                        "validation": "ls -la /opt/zargar"
                    }
                ]
            },
            "phase_2_code_recovery": {
                "description": "Recover application source code from Git",
                "estimated_time": "15 minutes",
                "steps": [
                    {
                        "step": 4,
                        "title": "Clone Repository",
                        "description": "Clone ZARGAR application repository",
                        "commands": [
                            "cd /opt/zargar",
                            "git clone <REPOSITORY_URL> .",
                            "git checkout main"
                        ],
                        "validation": "ls -la /opt/zargar && git status"
                    },
                    {
                        "step": 5,
                        "title": "Verify Code Integrity",
                        "description": "Verify application code is complete",
                        "commands": [
                            "# Check critical files exist",
                            "test -f docker-compose.yml",
                            "test -f manage.py",
                            "test -f requirements.txt",
                            "test -d zargar/"
                        ],
                        "validation": "All critical files present"
                    }
                ]
            },
            "phase_3_configuration_recovery": {
                "description": "Recover configuration files from backup storage",
                "estimated_time": "20 minutes",
                "steps": [
                    {
                        "step": 6,
                        "title": "Download Configuration Backup",
                        "description": "Download latest configuration backup from cloud storage",
                        "commands": [
                            "# This step requires the disaster recovery script",
                            "python disaster_recovery_restore.py --type=configuration --latest"
                        ],
                        "validation": "Configuration files restored successfully"
                    },
                    {
                        "step": 7,
                        "title": "Restore Environment Files",
                        "description": "Decrypt and restore environment configuration",
                        "commands": [
                            "# Decrypt .env file",
                            "openssl enc -aes-256-cbc -d -in .env.encrypted -out .env",
                            "",
                            "# Verify environment variables",
                            "grep -E '^(DATABASE_URL|REDIS_URL|SECRET_KEY)=' .env"
                        ],
                        "validation": "Environment file contains required variables"
                    },
                    {
                        "step": 8,
                        "title": "Restore Docker Configuration",
                        "description": "Restore Docker Compose and Nginx configurations",
                        "commands": [
                            "# Verify docker-compose.yml",
                            "docker-compose config",
                            "",
                            "# Verify nginx.conf",
                            "nginx -t -c nginx.conf"
                        ],
                        "validation": "All configuration files valid"
                    }
                ]
            },
            "phase_4_data_recovery": {
                "description": "Recover database from backup",
                "estimated_time": "60-120 minutes (depends on data size)",
                "steps": [
                    {
                        "step": 9,
                        "title": "Start Database Container",
                        "description": "Start PostgreSQL container for data restoration",
                        "commands": [
                            "# Start only database service",
                            "docker-compose up -d db",
                            "",
                            "# Wait for database to be ready",
                            "docker-compose exec db pg_isready -U zargar"
                        ],
                        "validation": "Database container running and accepting connections"
                    },
                    {
                        "step": 10,
                        "title": "Download Database Backup",
                        "description": "Download latest database backup from cloud storage",
                        "commands": [
                            "# Download latest database backup",
                            "python disaster_recovery_restore.py --type=database --latest",
                            "",
                            "# Verify backup file integrity",
                            "sha256sum -c database_backup.sha256"
                        ],
                        "validation": "Database backup downloaded and verified"
                    },
                    {
                        "step": 11,
                        "title": "Restore Database",
                        "description": "Restore complete database from backup",
                        "commands": [
                            "# Decrypt database backup",
                            "openssl enc -aes-256-cbc -d -in database_backup.sql.enc -out database_backup.sql",
                            "",
                            "# Restore database",
                            "docker-compose exec -T db psql -U zargar -d zargar < database_backup.sql"
                        ],
                        "validation": "Database restored successfully with all schemas"
                    }
                ]
            },
            "phase_5_service_startup": {
                "description": "Start all application services",
                "estimated_time": "30 minutes",
                "steps": [
                    {
                        "step": 12,
                        "title": "Start All Services",
                        "description": "Start complete application stack",
                        "commands": [
                            "# Start all services",
                            "docker-compose up -d",
                            "",
                            "# Wait for services to be ready",
                            "sleep 60",
                            "",
                            "# Check service health",
                            "docker-compose ps"
                        ],
                        "validation": "All services running and healthy"
                    },
                    {
                        "step": 13,
                        "title": "Run Database Migrations",
                        "description": "Apply any pending database migrations",
                        "commands": [
                            "# Run migrations",
                            "docker-compose exec web python manage.py migrate",
                            "",
                            "# Collect static files",
                            "docker-compose exec web python manage.py collectstatic --noinput"
                        ],
                        "validation": "Migrations applied successfully"
                    }
                ]
            },
            "phase_6_validation": {
                "description": "Validate complete system recovery",
                "estimated_time": "45 minutes",
                "steps": [
                    {
                        "step": 14,
                        "title": "System Health Check",
                        "description": "Perform comprehensive system health validation",
                        "commands": [
                            "# Run disaster recovery validation script",
                            "python disaster_recovery_validate.py --full-check"
                        ],
                        "validation": "All system components validated successfully"
                    }
                ]
            }
        }
    
    def _generate_validation_steps(self) -> Dict[str, Any]:
        """Generate validation procedures for disaster recovery."""
        return {
            "database_validation": {
                "description": "Validate database integrity and tenant isolation",
                "checks": [
                    "Verify public schema exists with correct tables",
                    "Verify all tenant schemas exist and are accessible",
                    "Verify data integrity with sample queries",
                    "Verify tenant isolation is working correctly",
                    "Check database user permissions and security"
                ]
            },
            "application_validation": {
                "description": "Validate application functionality",
                "checks": [
                    "Verify admin panel is accessible",
                    "Verify tenant portals are accessible",
                    "Test user authentication and authorization",
                    "Test multi-tenant functionality",
                    "Verify API endpoints are responding"
                ]
            },
            "storage_validation": {
                "description": "Validate storage and backup systems",
                "checks": [
                    "Verify Cloudflare R2 connectivity",
                    "Verify Backblaze B2 connectivity",
                    "Test file upload and download",
                    "Verify backup scheduling is working",
                    "Test disaster recovery procedures"
                ]
            },
            "security_validation": {
                "description": "Validate security configurations",
                "checks": [
                    "Verify SSL/TLS certificates",
                    "Test authentication systems",
                    "Verify audit logging is working",
                    "Check security headers and configurations",
                    "Validate encryption at rest and in transit"
                ]
            }
        }
    
    def _generate_rollback_procedures(self) -> Dict[str, Any]:
        """Generate rollback procedures in case of recovery failure."""
        return {
            "rollback_strategy": {
                "description": "Procedures to rollback failed recovery attempts",
                "scenarios": {
                    "partial_failure": {
                        "description": "Some services failed to start",
                        "steps": [
                            "Stop all services: docker-compose down",
                            "Check logs: docker-compose logs",
                            "Fix configuration issues",
                            "Restart services: docker-compose up -d"
                        ]
                    },
                    "data_corruption": {
                        "description": "Database restoration failed or corrupted",
                        "steps": [
                            "Stop database service",
                            "Remove corrupted data volume",
                            "Restore from previous backup",
                            "Restart database service",
                            "Re-run restoration process"
                        ]
                    },
                    "complete_failure": {
                        "description": "Complete recovery process failed",
                        "steps": [
                            "Document all error messages",
                            "Preserve logs for analysis",
                            "Start fresh server preparation",
                            "Contact emergency support team",
                            "Consider alternative recovery methods"
                        ]
                    }
                }
            }
        }
    
    def _generate_emergency_contacts(self) -> Dict[str, Any]:
        """Generate emergency contact information."""
        return {
            "primary_contacts": [
                {
                    "role": "System Administrator",
                    "name": "[ADMIN_NAME]",
                    "phone": "[ADMIN_PHONE]",
                    "email": "[ADMIN_EMAIL]",
                    "availability": "24/7"
                },
                {
                    "role": "Database Administrator",
                    "name": "[DBA_NAME]",
                    "phone": "[DBA_PHONE]",
                    "email": "[DBA_EMAIL]",
                    "availability": "Business hours + on-call"
                }
            ],
            "vendor_contacts": [
                {
                    "service": "Cloudflare R2",
                    "support_url": "https://support.cloudflare.com",
                    "phone": "[CLOUDFLARE_SUPPORT_PHONE]"
                },
                {
                    "service": "Backblaze B2",
                    "support_url": "https://help.backblaze.com",
                    "phone": "[BACKBLAZE_SUPPORT_PHONE]"
                }
            ]
        }
    
    def create_system_snapshot(self, snapshot_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a complete system snapshot for disaster recovery testing.
        
        Args:
            snapshot_name: Optional name for the snapshot
            
        Returns:
            Dict containing snapshot information
        """
        if not snapshot_name:
            snapshot_name = f"disaster_recovery_snapshot_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.logger.info(f"Creating system snapshot: {snapshot_name}")
        
        try:
            # Create backup job for full system
            backup_job = BackupJob.objects.create(
                name=snapshot_name,
                backup_type='full_system',
                frequency='manual',
                status='pending',
                created_by_username='disaster_recovery_system'
            )
            
            # Start backup process
            backup_job.mark_as_running()
            
            # Create database backup
            db_backup_path = self._create_database_backup(backup_job)
            
            # Create configuration backup
            config_backup_path = self._create_configuration_backup(backup_job)
            
            # Upload to storage
            storage_results = self._upload_snapshot_to_storage(
                backup_job, db_backup_path, config_backup_path
            )
            
            # Mark as completed
            backup_job.mark_as_completed(
                file_path=storage_results['combined_path'],
                file_size_bytes=storage_results['total_size'],
                storage_backends=storage_results['backends']
            )
            
            snapshot_info = {
                'snapshot_id': str(backup_job.job_id),
                'name': snapshot_name,
                'created_at': backup_job.created_at.isoformat(),
                'size_bytes': storage_results['total_size'],
                'storage_backends': storage_results['backends'],
                'components': {
                    'database': db_backup_path,
                    'configuration': config_backup_path
                }
            }
            
            self.logger.info(f"System snapshot created successfully: {snapshot_info}")
            return snapshot_info
            
        except Exception as e:
            self.logger.error(f"Failed to create system snapshot: {e}")
            if 'backup_job' in locals():
                backup_job.mark_as_failed(str(e))
            raise DisasterRecoveryError(f"Snapshot creation failed: {e}")
    
    def _create_database_backup(self, backup_job: BackupJob) -> str:
        """Create complete database backup including all schemas."""
        backup_job.update_progress(10, "Starting database backup")
        
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"zargar_database_backup_{timestamp}.sql"
        backup_path = os.path.join(tempfile.gettempdir(), backup_filename)
        
        try:
            # Create pg_dump command for all schemas
            dump_command = [
                'docker-compose', 'exec', '-T', 'db',
                'pg_dump', '-U', 'zargar', '-d', 'zargar',
                '--verbose', '--no-password',
                '--format=custom', '--compress=9'
            ]
            
            backup_job.update_progress(30, "Executing database dump")
            
            # Execute pg_dump
            with open(backup_path, 'wb') as backup_file:
                result = subprocess.run(
                    dump_command,
                    stdout=backup_file,
                    stderr=subprocess.PIPE,
                    check=True
                )
            
            backup_job.update_progress(50, "Database backup completed")
            
            # Verify backup file
            if not os.path.exists(backup_path) or os.path.getsize(backup_path) == 0:
                raise DisasterRecoveryError("Database backup file is empty or missing")
            
            self.logger.info(f"Database backup created: {backup_path}")
            return backup_path
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Database backup failed: {e.stderr.decode() if e.stderr else str(e)}"
            self.logger.error(error_msg)
            raise DisasterRecoveryError(error_msg)
    
    def _create_configuration_backup(self, backup_job: BackupJob) -> str:
        """Create backup of configuration files."""
        backup_job.update_progress(60, "Starting configuration backup")
        
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        config_backup_filename = f"zargar_config_backup_{timestamp}.tar.gz"
        config_backup_path = os.path.join(tempfile.gettempdir(), config_backup_filename)
        
        try:
            # List of configuration files to backup
            config_files = [
                'docker-compose.yml',
                'docker-compose.prod.yml',
                'nginx.conf',
                '.env.example',
                'requirements.txt',
                'Dockerfile'
            ]
            
            # Create tar archive of configuration files
            import tarfile
            
            with tarfile.open(config_backup_path, 'w:gz') as tar:
                for config_file in config_files:
                    if os.path.exists(config_file):
                        tar.add(config_file)
                        backup_job.add_log_message('info', f"Added {config_file} to configuration backup")
                
                # Add environment-specific files if they exist
                env_files = ['.env', '.env.local', '.env.production']
                for env_file in env_files:
                    if os.path.exists(env_file):
                        # Encrypt sensitive environment files
                        encrypted_env = self._encrypt_file(env_file)
                        tar.add(encrypted_env, arcname=f"{env_file}.encrypted")
                        backup_job.add_log_message('info', f"Added encrypted {env_file} to backup")
            
            backup_job.update_progress(70, "Configuration backup completed")
            
            self.logger.info(f"Configuration backup created: {config_backup_path}")
            return config_backup_path
            
        except Exception as e:
            error_msg = f"Configuration backup failed: {e}"
            self.logger.error(error_msg)
            raise DisasterRecoveryError(error_msg)
    
    def _encrypt_file(self, file_path: str) -> str:
        """Encrypt a file using AES-256-CBC."""
        encrypted_path = f"{file_path}.encrypted"
        
        # Use a key derived from Django SECRET_KEY
        encryption_key = settings.SECRET_KEY[:32].ljust(32, '0')
        
        try:
            # Use OpenSSL for encryption
            encrypt_command = [
                'openssl', 'enc', '-aes-256-cbc',
                '-in', file_path,
                '-out', encrypted_path,
                '-k', encryption_key
            ]
            
            subprocess.run(encrypt_command, check=True, capture_output=True)
            return encrypted_path
            
        except subprocess.CalledProcessError as e:
            raise DisasterRecoveryError(f"File encryption failed: {e}")
    
    def _upload_snapshot_to_storage(self, backup_job: BackupJob, db_path: str, config_path: str) -> Dict[str, Any]:
        """Upload snapshot files to redundant storage."""
        backup_job.update_progress(80, "Uploading to cloud storage")
        
        try:
            results = {'backends': [], 'total_size': 0}
            
            # Upload database backup
            with open(db_path, 'rb') as db_file:
                db_content = db_file.read()
                db_storage_path = f"disaster_recovery/database/{os.path.basename(db_path)}"
                
                db_upload_result = self.storage.upload_backup_file(
                    db_storage_path, db_content, use_redundant=True
                )
                
                if not db_upload_result['success']:
                    raise DisasterRecoveryError(f"Database backup upload failed: {db_upload_result['errors']}")
                
                results['backends'].extend(db_upload_result['uploaded_to'])
                results['total_size'] += len(db_content)
            
            # Upload configuration backup
            with open(config_path, 'rb') as config_file:
                config_content = config_file.read()
                config_storage_path = f"disaster_recovery/configuration/{os.path.basename(config_path)}"
                
                config_upload_result = self.storage.upload_backup_file(
                    config_storage_path, config_content, use_redundant=True
                )
                
                if not config_upload_result['success']:
                    raise DisasterRecoveryError(f"Configuration backup upload failed: {config_upload_result['errors']}")
                
                results['total_size'] += len(config_content)
            
            # Create combined manifest
            manifest = {
                'created_at': timezone.now().isoformat(),
                'database_backup': db_storage_path,
                'configuration_backup': config_storage_path,
                'total_size': results['total_size'],
                'storage_backends': list(set(results['backends']))
            }
            
            manifest_content = json.dumps(manifest, indent=2).encode()
            manifest_path = f"disaster_recovery/manifests/snapshot_{backup_job.job_id}.json"
            
            manifest_upload_result = self.storage.upload_backup_file(
                manifest_path, manifest_content, use_redundant=True
            )
            
            if not manifest_upload_result['success']:
                raise DisasterRecoveryError(f"Manifest upload failed: {manifest_upload_result['errors']}")
            
            results['combined_path'] = manifest_path
            results['backends'] = list(set(results['backends']))
            
            backup_job.update_progress(90, "Upload completed successfully")
            
            # Cleanup temporary files
            os.unlink(db_path)
            os.unlink(config_path)
            
            return results
            
        except Exception as e:
            error_msg = f"Storage upload failed: {e}"
            self.logger.error(error_msg)
            raise DisasterRecoveryError(error_msg)
    
    def test_disaster_recovery_procedures(self) -> Dict[str, Any]:
        """
        Test disaster recovery procedures without affecting production.
        
        Returns:
            Dict containing test results
        """
        self.logger.info("Starting disaster recovery procedure testing")
        
        test_results = {
            'test_id': f"dr_test_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
            'started_at': timezone.now().isoformat(),
            'tests': {},
            'overall_status': 'running'
        }
        
        try:
            # Test 1: Storage connectivity
            test_results['tests']['storage_connectivity'] = self._test_storage_connectivity()
            
            # Test 2: Backup creation
            test_results['tests']['backup_creation'] = self._test_backup_creation()
            
            # Test 3: Backup restoration (dry run)
            test_results['tests']['backup_restoration'] = self._test_backup_restoration_dry_run()
            
            # Test 4: Configuration validation
            test_results['tests']['configuration_validation'] = self._test_configuration_validation()
            
            # Test 5: Database connectivity
            test_results['tests']['database_connectivity'] = self._test_database_connectivity()
            
            # Calculate overall status
            all_passed = all(
                test['status'] == 'passed' 
                for test in test_results['tests'].values()
            )
            
            test_results['overall_status'] = 'passed' if all_passed else 'failed'
            test_results['completed_at'] = timezone.now().isoformat()
            
            self.logger.info(f"Disaster recovery testing completed: {test_results['overall_status']}")
            return test_results
            
        except Exception as e:
            test_results['overall_status'] = 'error'
            test_results['error'] = str(e)
            test_results['completed_at'] = timezone.now().isoformat()
            
            self.logger.error(f"Disaster recovery testing failed: {e}")
            return test_results
    
    def _test_storage_connectivity(self) -> Dict[str, Any]:
        """Test connectivity to backup storage systems."""
        try:
            connectivity_results = self.storage.test_connectivity()
            
            all_connected = all(
                result['connected'] 
                for result in connectivity_results.values()
            )
            
            return {
                'status': 'passed' if all_connected else 'failed',
                'details': connectivity_results,
                'message': 'All storage backends connected' if all_connected else 'Some storage backends failed'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Storage connectivity test failed'
            }
    
    def _test_backup_creation(self) -> Dict[str, Any]:
        """Test backup creation process."""
        try:
            # Create a small test backup
            test_backup_name = f"dr_test_backup_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create minimal test data
            test_data = {
                'test_timestamp': timezone.now().isoformat(),
                'test_data': 'disaster_recovery_test'
            }
            
            test_content = json.dumps(test_data).encode()
            test_path = f"disaster_recovery/tests/{test_backup_name}.json"
            
            # Upload test backup
            upload_result = self.storage.upload_backup_file(
                test_path, test_content, use_redundant=True
            )
            
            if upload_result['success']:
                # Verify download
                downloaded_content = self.storage.download_backup_file(test_path)
                
                if downloaded_content == test_content:
                    # Cleanup test file
                    self.storage.delete_backup_file(test_path, from_all_backends=True)
                    
                    return {
                        'status': 'passed',
                        'message': 'Backup creation and verification successful',
                        'details': upload_result
                    }
                else:
                    return {
                        'status': 'failed',
                        'message': 'Backup verification failed - content mismatch'
                    }
            else:
                return {
                    'status': 'failed',
                    'message': 'Backup upload failed',
                    'details': upload_result
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Backup creation test failed'
            }
    
    def _test_backup_restoration_dry_run(self) -> Dict[str, Any]:
        """Test backup restoration process (dry run)."""
        try:
            # List available backups
            backup_files = self.storage.list_backup_files('disaster_recovery/')
            
            if not backup_files:
                return {
                    'status': 'warning',
                    'message': 'No disaster recovery backups found for testing'
                }
            
            # Find most recent backup manifest
            manifest_files = [f for f in backup_files if f.endswith('.json') and 'manifests' in f]
            
            if not manifest_files:
                return {
                    'status': 'warning',
                    'message': 'No backup manifests found for testing'
                }
            
            # Download and validate most recent manifest
            latest_manifest = sorted(manifest_files)[-1]
            manifest_content = self.storage.download_backup_file(f"disaster_recovery/{latest_manifest}")
            
            if manifest_content:
                manifest_data = json.loads(manifest_content.decode())
                
                # Validate manifest structure
                required_keys = ['database_backup', 'configuration_backup', 'created_at']
                if all(key in manifest_data for key in required_keys):
                    return {
                        'status': 'passed',
                        'message': 'Backup restoration dry run successful',
                        'details': {
                            'manifest_file': latest_manifest,
                            'backup_date': manifest_data['created_at'],
                            'components': {
                                'database': manifest_data['database_backup'],
                                'configuration': manifest_data['configuration_backup']
                            }
                        }
                    }
                else:
                    return {
                        'status': 'failed',
                        'message': 'Backup manifest is invalid or incomplete'
                    }
            else:
                return {
                    'status': 'failed',
                    'message': 'Failed to download backup manifest'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Backup restoration dry run failed'
            }
    
    def _test_configuration_validation(self) -> Dict[str, Any]:
        """Test configuration file validation."""
        try:
            # Check critical configuration files
            config_files = {
                'docker-compose.yml': 'Docker Compose configuration',
                'nginx.conf': 'Nginx configuration',
                'requirements.txt': 'Python dependencies'
            }
            
            validation_results = {}
            
            for file_path, description in config_files.items():
                if os.path.exists(file_path):
                    validation_results[file_path] = {
                        'exists': True,
                        'description': description,
                        'size': os.path.getsize(file_path)
                    }
                else:
                    validation_results[file_path] = {
                        'exists': False,
                        'description': description,
                        'error': 'File not found'
                    }
            
            # Validate Docker Compose configuration
            if os.path.exists('docker-compose.yml'):
                try:
                    result = subprocess.run(
                        ['docker-compose', 'config'],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    validation_results['docker-compose.yml']['valid'] = True
                except subprocess.CalledProcessError as e:
                    validation_results['docker-compose.yml']['valid'] = False
                    validation_results['docker-compose.yml']['error'] = e.stderr
            
            all_valid = all(
                result.get('exists', False) and result.get('valid', True)
                for result in validation_results.values()
            )
            
            return {
                'status': 'passed' if all_valid else 'failed',
                'message': 'Configuration validation completed',
                'details': validation_results
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Configuration validation failed'
            }
    
    def _test_database_connectivity(self) -> Dict[str, Any]:
        """Test database connectivity and basic operations."""
        try:
            # Test database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                if result and result[0] == 1:
                    # Test tenant schema access
                    cursor.execute("""
                        SELECT schema_name 
                        FROM information_schema.schemata 
                        WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                    """)
                    schemas = cursor.fetchall()
                    
                    return {
                        'status': 'passed',
                        'message': 'Database connectivity test successful',
                        'details': {
                            'connection': 'successful',
                            'schemas_found': len(schemas),
                            'schema_names': [schema[0] for schema in schemas]
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
                'message': 'Database connectivity test failed'
            }
    
    def generate_recovery_documentation(self) -> str:
        """
        Generate comprehensive disaster recovery documentation.
        
        Returns:
            Path to generated documentation file
        """
        self.logger.info("Generating disaster recovery documentation")
        
        try:
            # Create disaster recovery plan
            dr_plan = self.create_disaster_recovery_plan()
            
            # Generate documentation content
            doc_content = self._format_recovery_documentation(dr_plan)
            
            # Save documentation to file
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            doc_filename = f"disaster_recovery_plan_{timestamp}.md"
            doc_path = os.path.join(tempfile.gettempdir(), doc_filename)
            
            with open(doc_path, 'w', encoding='utf-8') as doc_file:
                doc_file.write(doc_content)
            
            # Upload to storage
            with open(doc_path, 'rb') as doc_file:
                doc_bytes = doc_file.read()
                
            storage_path = f"disaster_recovery/documentation/{doc_filename}"
            upload_result = self.storage.upload_backup_file(
                storage_path, doc_bytes, use_redundant=True
            )
            
            if upload_result['success']:
                self.logger.info(f"Disaster recovery documentation generated: {storage_path}")
                return storage_path
            else:
                raise DisasterRecoveryError(f"Failed to upload documentation: {upload_result['errors']}")
                
        except Exception as e:
            self.logger.error(f"Failed to generate recovery documentation: {e}")
            raise DisasterRecoveryError(f"Documentation generation failed: {e}")
    
    def _format_recovery_documentation(self, dr_plan: Dict[str, Any]) -> str:
        """Format disaster recovery plan as Markdown documentation."""
        plan_data = dr_plan['disaster_recovery_plan']
        
        doc_content = f"""# ZARGAR Jewelry SaaS - Disaster Recovery Plan

**Version:** {plan_data['version']}  
**Created:** {plan_data['created_at']}  
**Recovery Time Objective:** {plan_data['overview']['recovery_time_objective']}  
**Recovery Point Objective:** {plan_data['overview']['recovery_point_objective']}  

## Overview

{plan_data['overview']['philosophy']}

### System Components

- **Data:** {plan_data['overview']['components']['data']}
- **Configuration:** {plan_data['overview']['components']['configuration']}
- **Code:** {plan_data['overview']['components']['code']}

## Prerequisites

### Server Requirements

- **CPU:** {plan_data['prerequisites']['server_requirements']['cpu']}
- **Memory:** {plan_data['prerequisites']['server_requirements']['memory']}
- **Storage:** {plan_data['prerequisites']['server_requirements']['storage']}
- **Network:** {plan_data['prerequisites']['server_requirements']['network']}

### Software Requirements

"""
        
        for software in plan_data['prerequisites']['software_requirements']:
            doc_content += f"- {software}\n"
        
        doc_content += "\n### Access Requirements\n\n"
        
        for access in plan_data['prerequisites']['access_requirements']:
            doc_content += f"- {access}\n"
        
        doc_content += "\n## Recovery Procedures\n\n"
        
        # Add recovery procedures
        for phase_key, phase_data in plan_data['recovery_procedures'].items():
            doc_content += f"### {phase_data['description']}\n\n"
            doc_content += f"**Estimated Time:** {phase_data['estimated_time']}\n\n"
            
            for step in phase_data['steps']:
                doc_content += f"#### Step {step['step']}: {step['title']}\n\n"
                doc_content += f"{step['description']}\n\n"
                
                if 'commands' in step:
                    doc_content += "**Commands:**\n\n```bash\n"
                    for command in step['commands']:
                        doc_content += f"{command}\n"
                    doc_content += "```\n\n"
                
                doc_content += f"**Validation:** {step['validation']}\n\n"
        
        # Add validation procedures
        doc_content += "## Validation Procedures\n\n"
        
        for validation_key, validation_data in plan_data['validation_steps'].items():
            doc_content += f"### {validation_data['description']}\n\n"
            
            for check in validation_data['checks']:
                doc_content += f"- {check}\n"
            doc_content += "\n"
        
        # Add rollback procedures
        doc_content += "## Rollback Procedures\n\n"
        
        rollback_data = plan_data['rollback_procedures']['rollback_strategy']
        doc_content += f"{rollback_data['description']}\n\n"
        
        for scenario_key, scenario_data in rollback_data['scenarios'].items():
            doc_content += f"### {scenario_data['description']}\n\n"
            
            for i, step in enumerate(scenario_data['steps'], 1):
                doc_content += f"{i}. {step}\n"
            doc_content += "\n"
        
        # Add emergency contacts
        doc_content += "## Emergency Contacts\n\n"
        
        doc_content += "### Primary Contacts\n\n"
        for contact in plan_data['emergency_contacts']['primary_contacts']:
            doc_content += f"**{contact['role']}**\n"
            doc_content += f"- Name: {contact['name']}\n"
            doc_content += f"- Phone: {contact['phone']}\n"
            doc_content += f"- Email: {contact['email']}\n"
            doc_content += f"- Availability: {contact['availability']}\n\n"
        
        doc_content += "### Vendor Contacts\n\n"
        for vendor in plan_data['emergency_contacts']['vendor_contacts']:
            doc_content += f"**{vendor['service']}**\n"
            doc_content += f"- Support URL: {vendor['support_url']}\n"
            doc_content += f"- Phone: {vendor['phone']}\n\n"
        
        return doc_content


# Global disaster recovery manager instance
disaster_recovery_manager = DisasterRecoveryManager()