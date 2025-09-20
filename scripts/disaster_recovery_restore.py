#!/usr/bin/env python
"""
Disaster Recovery Restore Script for ZARGAR Jewelry SaaS Platform.

This script handles automated restoration of the complete system from backups
including database, configuration, and validation procedures.

Usage:
    docker-compose exec web python scripts/disaster_recovery_restore.py --type=full_system --latest
    docker-compose exec web python scripts/disaster_recovery_restore.py --type=database --backup-id=<backup_id>
    docker-compose exec web python scripts/disaster_recovery_restore.py --type=configuration --latest
    docker-compose exec web python scripts/disaster_recovery_restore.py --list-backups
"""
import os
import sys
import json
import argparse
import logging
import subprocess
import tempfile
from datetime import datetime
from typing import Dict, List, Any, Optional

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.base')

import django
django.setup()

from django.db import connection, transaction
from django.conf import settings
from django.utils import timezone

from zargar.admin_panel.models import BackupJob, RestoreJob
from zargar.core.storage_utils import storage_manager
from zargar.admin_panel.disaster_recovery import disaster_recovery_manager


class DisasterRecoveryRestoreError(Exception):
    """Custom exception for disaster recovery restore operations."""
    pass


class DisasterRecoveryRestore:
    """
    Automated disaster recovery restore system.
    
    Handles complete system restoration from backups with proper validation
    and rollback capabilities.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.storage = storage_manager
        
    def list_available_backups(self) -> Dict[str, Any]:
        """
        List all available disaster recovery backups.
        
        Returns:
            Dict containing available backups information
        """
        self.logger.info("Listing available disaster recovery backups")
        
        try:
            # List backup manifests
            backup_files = self.storage.list_backup_files('disaster_recovery/manifests/')
            
            backups = []
            
            for manifest_file in backup_files:
                if manifest_file.endswith('.json'):
                    try:
                        # Download manifest
                        manifest_content = self.storage.download_backup_file(
                            f"disaster_recovery/manifests/{manifest_file}"
                        )
                        
                        if manifest_content:
                            manifest_data = json.loads(manifest_content.decode())
                            
                            backup_info = {
                                'manifest_file': manifest_file,
                                'backup_id': manifest_file.replace('snapshot_', '').replace('.json', ''),
                                'created_at': manifest_data.get('created_at'),
                                'total_size': manifest_data.get('total_size', 0),
                                'components': {
                                    'database': manifest_data.get('database_backup'),
                                    'configuration': manifest_data.get('configuration_backup')
                                },
                                'storage_backends': manifest_data.get('storage_backends', [])
                            }
                            
                            backups.append(backup_info)
                            
                    except Exception as e:
                        self.logger.warning(f"Failed to parse manifest {manifest_file}: {e}")
            
            # Sort by creation date (newest first)
            backups.sort(key=lambda x: x['created_at'], reverse=True)
            
            return {
                'total_backups': len(backups),
                'backups': backups,
                'latest_backup': backups[0] if backups else None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
            raise DisasterRecoveryRestoreError(f"Backup listing failed: {e}")
    
    def restore_full_system(self, backup_id: Optional[str] = None, use_latest: bool = False) -> Dict[str, Any]:
        """
        Restore complete system from backup.
        
        Args:
            backup_id: Specific backup ID to restore from
            use_latest: Use latest available backup
            
        Returns:
            Dict containing restore operation results
        """
        self.logger.info(f"Starting full system restore (backup_id={backup_id}, use_latest={use_latest})")
        
        try:
            # Get backup information
            backup_info = self._get_backup_info(backup_id, use_latest)
            
            # Create restore job
            restore_job = RestoreJob.objects.create(
                restore_type='full_system',
                source_backup_id=backup_info['backup_id'],
                status='pending',
                created_by_username='disaster_recovery_system'
            )
            
            restore_job.add_log_message('info', 'Starting full system restore')
            restore_job.status = 'running'
            restore_job.started_at = timezone.now()
            restore_job.save()
            
            # Step 1: Restore database
            restore_job.update_progress(10, 'Starting database restore')
            db_restore_result = self._restore_database(backup_info, restore_job)
            
            if not db_restore_result['success']:
                restore_job.mark_as_failed(f"Database restore failed: {db_restore_result['error']}")
                raise DisasterRecoveryRestoreError(f"Database restore failed: {db_restore_result['error']}")
            
            # Step 2: Restore configuration
            restore_job.update_progress(60, 'Starting configuration restore')
            config_restore_result = self._restore_configuration(backup_info, restore_job)
            
            if not config_restore_result['success']:
                restore_job.mark_as_failed(f"Configuration restore failed: {config_restore_result['error']}")
                raise DisasterRecoveryRestoreError(f"Configuration restore failed: {config_restore_result['error']}")
            
            # Step 3: Validate restoration
            restore_job.update_progress(80, 'Validating restored system')
            validation_result = self._validate_restoration(restore_job)
            
            if not validation_result['success']:
                restore_job.mark_as_failed(f"Restoration validation failed: {validation_result['error']}")
                raise DisasterRecoveryRestoreError(f"Validation failed: {validation_result['error']}")
            
            # Mark as completed
            restore_job.update_progress(100, 'Full system restore completed successfully')
            restore_job.status = 'completed'
            restore_job.completed_at = timezone.now()
            restore_job.save()
            
            result = {
                'success': True,
                'restore_job_id': str(restore_job.job_id),
                'backup_info': backup_info,
                'database_restore': db_restore_result,
                'configuration_restore': config_restore_result,
                'validation': validation_result,
                'completed_at': restore_job.completed_at.isoformat()
            }
            
            self.logger.info(f"Full system restore completed successfully: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Full system restore failed: {e}")
            if 'restore_job' in locals():
                restore_job.mark_as_failed(str(e))
            raise DisasterRecoveryRestoreError(f"Full system restore failed: {e}")
    
    def restore_database_only(self, backup_id: Optional[str] = None, use_latest: bool = False) -> Dict[str, Any]:
        """
        Restore database only from backup.
        
        Args:
            backup_id: Specific backup ID to restore from
            use_latest: Use latest available backup
            
        Returns:
            Dict containing restore operation results
        """
        self.logger.info(f"Starting database-only restore (backup_id={backup_id}, use_latest={use_latest})")
        
        try:
            # Get backup information
            backup_info = self._get_backup_info(backup_id, use_latest)
            
            # Create restore job
            restore_job = RestoreJob.objects.create(
                restore_type='database_only',
                source_backup_id=backup_info['backup_id'],
                status='pending',
                created_by_username='disaster_recovery_system'
            )
            
            restore_job.add_log_message('info', 'Starting database-only restore')
            restore_job.status = 'running'
            restore_job.started_at = timezone.now()
            restore_job.save()
            
            # Restore database
            restore_job.update_progress(10, 'Starting database restore')
            db_restore_result = self._restore_database(backup_info, restore_job)
            
            if not db_restore_result['success']:
                restore_job.mark_as_failed(f"Database restore failed: {db_restore_result['error']}")
                raise DisasterRecoveryRestoreError(f"Database restore failed: {db_restore_result['error']}")
            
            # Validate database
            restore_job.update_progress(80, 'Validating restored database')
            validation_result = self._validate_database_restoration(restore_job)
            
            if not validation_result['success']:
                restore_job.mark_as_failed(f"Database validation failed: {validation_result['error']}")
                raise DisasterRecoveryRestoreError(f"Database validation failed: {validation_result['error']}")
            
            # Mark as completed
            restore_job.update_progress(100, 'Database restore completed successfully')
            restore_job.status = 'completed'
            restore_job.completed_at = timezone.now()
            restore_job.save()
            
            result = {
                'success': True,
                'restore_job_id': str(restore_job.job_id),
                'backup_info': backup_info,
                'database_restore': db_restore_result,
                'validation': validation_result,
                'completed_at': restore_job.completed_at.isoformat()
            }
            
            self.logger.info(f"Database restore completed successfully: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Database restore failed: {e}")
            if 'restore_job' in locals():
                restore_job.mark_as_failed(str(e))
            raise DisasterRecoveryRestoreError(f"Database restore failed: {e}")
    
    def restore_configuration_only(self, backup_id: Optional[str] = None, use_latest: bool = False) -> Dict[str, Any]:
        """
        Restore configuration only from backup.
        
        Args:
            backup_id: Specific backup ID to restore from
            use_latest: Use latest available backup
            
        Returns:
            Dict containing restore operation results
        """
        self.logger.info(f"Starting configuration-only restore (backup_id={backup_id}, use_latest={use_latest})")
        
        try:
            # Get backup information
            backup_info = self._get_backup_info(backup_id, use_latest)
            
            # Create restore job
            restore_job = RestoreJob.objects.create(
                restore_type='configuration',
                source_backup_id=backup_info['backup_id'],
                status='pending',
                created_by_username='disaster_recovery_system'
            )
            
            restore_job.add_log_message('info', 'Starting configuration-only restore')
            restore_job.status = 'running'
            restore_job.started_at = timezone.now()
            restore_job.save()
            
            # Restore configuration
            restore_job.update_progress(10, 'Starting configuration restore')
            config_restore_result = self._restore_configuration(backup_info, restore_job)
            
            if not config_restore_result['success']:
                restore_job.mark_as_failed(f"Configuration restore failed: {config_restore_result['error']}")
                raise DisasterRecoveryRestoreError(f"Configuration restore failed: {config_restore_result['error']}")
            
            # Validate configuration
            restore_job.update_progress(80, 'Validating restored configuration')
            validation_result = self._validate_configuration_restoration(restore_job)
            
            if not validation_result['success']:
                restore_job.mark_as_failed(f"Configuration validation failed: {validation_result['error']}")
                raise DisasterRecoveryRestoreError(f"Configuration validation failed: {validation_result['error']}")
            
            # Mark as completed
            restore_job.update_progress(100, 'Configuration restore completed successfully')
            restore_job.status = 'completed'
            restore_job.completed_at = timezone.now()
            restore_job.save()
            
            result = {
                'success': True,
                'restore_job_id': str(restore_job.job_id),
                'backup_info': backup_info,
                'configuration_restore': config_restore_result,
                'validation': validation_result,
                'completed_at': restore_job.completed_at.isoformat()
            }
            
            self.logger.info(f"Configuration restore completed successfully: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Configuration restore failed: {e}")
            if 'restore_job' in locals():
                restore_job.mark_as_failed(str(e))
            raise DisasterRecoveryRestoreError(f"Configuration restore failed: {e}")
    
    def _get_backup_info(self, backup_id: Optional[str], use_latest: bool) -> Dict[str, Any]:
        """Get backup information for restoration."""
        backups_list = self.list_available_backups()
        
        if not backups_list['backups']:
            raise DisasterRecoveryRestoreError("No backups available for restoration")
        
        if use_latest:
            backup_info = backups_list['latest_backup']
            if not backup_info:
                raise DisasterRecoveryRestoreError("No latest backup available")
        elif backup_id:
            backup_info = None
            for backup in backups_list['backups']:
                if backup['backup_id'] == backup_id:
                    backup_info = backup
                    break
            
            if not backup_info:
                raise DisasterRecoveryRestoreError(f"Backup with ID {backup_id} not found")
        else:
            raise DisasterRecoveryRestoreError("Must specify either backup_id or use_latest=True")
        
        return backup_info
    
    def _restore_database(self, backup_info: Dict[str, Any], restore_job: RestoreJob) -> Dict[str, Any]:
        """Restore database from backup."""
        try:
            restore_job.add_log_message('info', f"Downloading database backup: {backup_info['components']['database']}")
            
            # Download database backup
            db_backup_content = self.storage.download_backup_file(backup_info['components']['database'])
            
            if not db_backup_content:
                return {
                    'success': False,
                    'error': 'Failed to download database backup'
                }
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.sql', delete=False) as temp_file:
                temp_file.write(db_backup_content)
                temp_db_path = temp_file.name
            
            try:
                restore_job.update_progress(30, 'Stopping application services')
                
                # Stop web service to prevent database access during restore
                subprocess.run(['docker-compose', 'stop', 'web'], check=True, capture_output=True)
                
                restore_job.update_progress(40, 'Restoring database from backup')
                
                # Restore database using pg_restore
                restore_command = [
                    'docker-compose', 'exec', '-T', 'db',
                    'pg_restore', '-U', 'zargar', '-d', 'zargar',
                    '--clean', '--if-exists', '--verbose'
                ]
                
                with open(temp_db_path, 'rb') as backup_file:
                    result = subprocess.run(
                        restore_command,
                        stdin=backup_file,
                        capture_output=True,
                        check=False  # Don't raise exception on non-zero exit
                    )
                
                if result.returncode != 0:
                    error_msg = result.stderr.decode() if result.stderr else 'Unknown error'
                    restore_job.add_log_message('error', f"pg_restore failed: {error_msg}")
                    return {
                        'success': False,
                        'error': f'Database restore failed: {error_msg}'
                    }
                
                restore_job.update_progress(50, 'Starting application services')
                
                # Restart web service
                subprocess.run(['docker-compose', 'start', 'web'], check=True, capture_output=True)
                
                restore_job.add_log_message('info', 'Database restore completed successfully')
                
                return {
                    'success': True,
                    'message': 'Database restored successfully',
                    'backup_file': backup_info['components']['database']
                }
                
            finally:
                # Cleanup temporary file
                os.unlink(temp_db_path)
                
        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed: {e.stderr.decode() if e.stderr else str(e)}"
            restore_job.add_log_message('error', error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Database restore failed: {e}"
            restore_job.add_log_message('error', error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _restore_configuration(self, backup_info: Dict[str, Any], restore_job: RestoreJob) -> Dict[str, Any]:
        """Restore configuration from backup."""
        try:
            restore_job.add_log_message('info', f"Downloading configuration backup: {backup_info['components']['configuration']}")
            
            # Download configuration backup
            config_backup_content = self.storage.download_backup_file(backup_info['components']['configuration'])
            
            if not config_backup_content:
                return {
                    'success': False,
                    'error': 'Failed to download configuration backup'
                }
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as temp_file:
                temp_file.write(config_backup_content)
                temp_config_path = temp_file.name
            
            try:
                restore_job.update_progress(70, 'Extracting configuration files')
                
                # Extract configuration files
                import tarfile
                
                with tarfile.open(temp_config_path, 'r:gz') as tar:
                    # Extract to current directory
                    tar.extractall(path='.')
                    
                    # List extracted files
                    extracted_files = tar.getnames()
                    restore_job.add_log_message('info', f"Extracted files: {extracted_files}")
                
                # Decrypt environment files if they exist
                env_files = [f for f in extracted_files if f.endswith('.env.encrypted')]
                
                for encrypted_env_file in env_files:
                    if os.path.exists(encrypted_env_file):
                        decrypted_file = encrypted_env_file.replace('.encrypted', '')
                        
                        # Decrypt using OpenSSL
                        encryption_key = settings.SECRET_KEY[:32].ljust(32, '0')
                        
                        decrypt_command = [
                            'openssl', 'enc', '-aes-256-cbc', '-d',
                            '-in', encrypted_env_file,
                            '-out', decrypted_file,
                            '-k', encryption_key
                        ]
                        
                        result = subprocess.run(decrypt_command, capture_output=True, check=False)
                        
                        if result.returncode == 0:
                            restore_job.add_log_message('info', f"Decrypted {encrypted_env_file} to {decrypted_file}")
                            # Remove encrypted file
                            os.unlink(encrypted_env_file)
                        else:
                            restore_job.add_log_message('warning', f"Failed to decrypt {encrypted_env_file}")
                
                restore_job.add_log_message('info', 'Configuration restore completed successfully')
                
                return {
                    'success': True,
                    'message': 'Configuration restored successfully',
                    'extracted_files': extracted_files,
                    'backup_file': backup_info['components']['configuration']
                }
                
            finally:
                # Cleanup temporary file
                os.unlink(temp_config_path)
                
        except Exception as e:
            error_msg = f"Configuration restore failed: {e}"
            restore_job.add_log_message('error', error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _validate_restoration(self, restore_job: RestoreJob) -> Dict[str, Any]:
        """Validate complete system restoration."""
        try:
            restore_job.add_log_message('info', 'Starting restoration validation')
            
            # Import validation script
            from scripts.disaster_recovery_validate import DisasterRecoveryValidator
            
            validator = DisasterRecoveryValidator()
            
            # Run quick validation
            validation_results = validator.run_quick_validation()
            
            if validation_results['overall_status'] == 'passed':
                restore_job.add_log_message('info', 'Restoration validation passed')
                return {
                    'success': True,
                    'message': 'System validation passed',
                    'details': validation_results
                }
            else:
                restore_job.add_log_message('warning', f"Restoration validation issues: {validation_results['overall_status']}")
                return {
                    'success': False,
                    'error': f"Validation failed with status: {validation_results['overall_status']}",
                    'details': validation_results
                }
                
        except Exception as e:
            error_msg = f"Restoration validation failed: {e}"
            restore_job.add_log_message('error', error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _validate_database_restoration(self, restore_job: RestoreJob) -> Dict[str, Any]:
        """Validate database restoration."""
        try:
            restore_job.add_log_message('info', 'Starting database validation')
            
            # Import validation script
            from scripts.disaster_recovery_validate import DisasterRecoveryValidator
            
            validator = DisasterRecoveryValidator()
            
            # Run database validation
            validation_result = validator.validate_component('database')
            
            if validation_result['status'] == 'passed':
                restore_job.add_log_message('info', 'Database validation passed')
                return {
                    'success': True,
                    'message': 'Database validation passed',
                    'details': validation_result
                }
            else:
                restore_job.add_log_message('warning', f"Database validation issues: {validation_result['status']}")
                return {
                    'success': False,
                    'error': f"Database validation failed with status: {validation_result['status']}",
                    'details': validation_result
                }
                
        except Exception as e:
            error_msg = f"Database validation failed: {e}"
            restore_job.add_log_message('error', error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _validate_configuration_restoration(self, restore_job: RestoreJob) -> Dict[str, Any]:
        """Validate configuration restoration."""
        try:
            restore_job.add_log_message('info', 'Starting configuration validation')
            
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
                    restore_job.add_log_message('info', f"Configuration file validated: {file_path}")
                else:
                    validation_results[file_path] = {
                        'exists': False,
                        'description': description,
                        'error': 'File not found'
                    }
                    restore_job.add_log_message('warning', f"Configuration file missing: {file_path}")
            
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
                    restore_job.add_log_message('info', 'Docker Compose configuration is valid')
                except subprocess.CalledProcessError as e:
                    validation_results['docker-compose.yml']['valid'] = False
                    validation_results['docker-compose.yml']['error'] = e.stderr
                    restore_job.add_log_message('error', f"Docker Compose configuration invalid: {e.stderr}")
            
            all_valid = all(
                result.get('exists', False) and result.get('valid', True)
                for result in validation_results.values()
            )
            
            if all_valid:
                return {
                    'success': True,
                    'message': 'Configuration validation passed',
                    'details': validation_results
                }
            else:
                return {
                    'success': False,
                    'error': 'Configuration validation failed',
                    'details': validation_results
                }
                
        except Exception as e:
            error_msg = f"Configuration validation failed: {e}"
            restore_job.add_log_message('error', error_msg)
            return {
                'success': False,
                'error': error_msg
            }


def main():
    """Main function to run disaster recovery restore operations."""
    parser = argparse.ArgumentParser(description='ZARGAR Disaster Recovery Restore')
    parser.add_argument('--type', choices=['full_system', 'database', 'configuration'], 
                       help='Type of restore to perform')
    parser.add_argument('--backup-id', type=str, help='Specific backup ID to restore from')
    parser.add_argument('--latest', action='store_true', help='Use latest available backup')
    parser.add_argument('--list-backups', action='store_true', help='List available backups')
    parser.add_argument('--output', type=str, help='Output file for results')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    restore_manager = DisasterRecoveryRestore()
    
    try:
        if args.list_backups:
            print("📋 Listing available disaster recovery backups...")
            results = restore_manager.list_available_backups()
            
            print(f"\n📊 Available Backups: {results['total_backups']}")
            print("=" * 60)
            
            for backup in results['backups']:
                print(f"Backup ID: {backup['backup_id']}")
                print(f"Created: {backup['created_at']}")
                print(f"Size: {backup['total_size']:,} bytes")
                print(f"Components: Database, Configuration")
                print(f"Storage: {', '.join(backup['storage_backends'])}")
                print("-" * 40)
            
            if results['latest_backup']:
                print(f"\n🕒 Latest Backup: {results['latest_backup']['backup_id']}")
                print(f"Created: {results['latest_backup']['created_at']}")
            
        elif args.type:
            if not (args.backup_id or args.latest):
                print("❌ Please specify either --backup-id or --latest")
                sys.exit(1)
            
            print(f"🔄 Starting {args.type} restore...")
            
            if args.type == 'full_system':
                results = restore_manager.restore_full_system(
                    backup_id=args.backup_id,
                    use_latest=args.latest
                )
            elif args.type == 'database':
                results = restore_manager.restore_database_only(
                    backup_id=args.backup_id,
                    use_latest=args.latest
                )
            elif args.type == 'configuration':
                results = restore_manager.restore_configuration_only(
                    backup_id=args.backup_id,
                    use_latest=args.latest
                )
            
            # Print results
            print(f"\n📊 Restore Results")
            print("=" * 50)
            
            if results['success']:
                print("✅ Restore completed successfully!")
                print(f"Restore Job ID: {results['restore_job_id']}")
                print(f"Backup Used: {results['backup_info']['backup_id']}")
                print(f"Completed At: {results['completed_at']}")
            else:
                print("❌ Restore failed!")
                if 'error' in results:
                    print(f"Error: {results['error']}")
            
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
            sys.exit(0 if results['success'] else 1)
            
        else:
            print("❌ Please specify --type or --list-backups")
            parser.print_help()
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Restore operation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()