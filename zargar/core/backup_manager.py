"""
Backup Manager for the ZARGAR jewelry SaaS platform.
Provides comprehensive backup functionality with encryption, compression, and redundant storage.
"""
import os
import gzip
import hashlib
import subprocess
import tempfile
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from django.conf import settings
from django.utils import timezone
from django.db import connection
from django_tenants.utils import get_tenant_model, schema_context
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from zargar.system.models import BackupRecord, BackupSchedule, BackupIntegrityCheck
from .storage_utils import storage_manager


logger = logging.getLogger(__name__)


class BackupManager:
    """
    Comprehensive backup manager for the ZARGAR platform.
    Handles database backups, encryption, compression, and storage management.
    """
    
    def __init__(self):
        self.storage_manager = storage_manager
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        
        # Backup configuration
        self.backup_base_path = getattr(settings, 'BACKUP_BASE_PATH', 'backups/')
        self.compression_enabled = getattr(settings, 'BACKUP_COMPRESSION_ENABLED', True)
        self.encryption_enabled = getattr(settings, 'BACKUP_ENCRYPTION_ENABLED', True)
        
        # Database configuration
        self.db_config = self._get_database_config()
        
        logger.info("BackupManager initialized successfully")
    
    def _get_database_config(self) -> Dict[str, str]:
        """Extract database configuration from Django settings."""
        db_settings = settings.DATABASES['default']
        
        return {
            'host': db_settings.get('HOST', 'localhost'),
            'port': str(db_settings.get('PORT', 5432)),
            'name': db_settings.get('NAME', ''),
            'user': db_settings.get('USER', ''),
            'password': db_settings.get('PASSWORD', ''),
        }
    
    def _get_or_create_encryption_key(self) -> bytes:
        """
        Get or create encryption key for backup encryption.
        Uses PBKDF2 with a salt derived from SECRET_KEY.
        """
        # Use Django's SECRET_KEY as the password for key derivation
        password = settings.SECRET_KEY.encode()
        
        # Create a consistent salt from the SECRET_KEY
        salt = hashlib.sha256(password).digest()[:16]  # Use first 16 bytes as salt
        
        # Derive encryption key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def _generate_backup_id(self, backup_type: str, tenant_schema: Optional[str] = None) -> str:
        """Generate unique backup ID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if tenant_schema:
            return f"{backup_type}_{tenant_schema}_{timestamp}"
        else:
            return f"{backup_type}_system_{timestamp}"
    
    def _get_backup_file_path(self, backup_id: str, backup_type: str) -> str:
        """Generate backup file path in storage."""
        date_path = datetime.now().strftime('%Y/%m/%d')
        
        if backup_type == 'full_system':
            return f"{self.backup_base_path}system/{date_path}/{backup_id}.sql.gz.enc"
        elif backup_type == 'tenant_only':
            return f"{self.backup_base_path}tenants/{date_path}/{backup_id}.sql.gz.enc"
        elif backup_type == 'configuration':
            return f"{self.backup_base_path}config/{date_path}/{backup_id}.tar.gz.enc"
        else:
            return f"{self.backup_base_path}snapshots/{date_path}/{backup_id}.sql.gz.enc"
    
    def _create_pg_dump_command(self, schema_name: Optional[str] = None, exclude_schemas: List[str] = None) -> List[str]:
        """
        Create pg_dump command with appropriate parameters.
        
        Args:
            schema_name: Specific schema to backup (for tenant backups)
            exclude_schemas: Schemas to exclude (for system backups)
        
        Returns:
            List of command arguments for pg_dump
        """
        cmd = [
            'pg_dump',
            f"--host={self.db_config['host']}",
            f"--port={self.db_config['port']}",
            f"--username={self.db_config['user']}",
            f"--dbname={self.db_config['name']}",
            '--verbose',
            '--no-password',
            '--format=custom',
            '--compress=9',
            '--no-privileges',
            '--no-owner',
        ]
        
        if schema_name:
            # Backup specific tenant schema
            cmd.extend([f"--schema={schema_name}"])
        else:
            # Full system backup - exclude information_schema and pg_* schemas
            default_excludes = ['information_schema', 'pg_catalog', 'pg_toast']
            if exclude_schemas:
                default_excludes.extend(exclude_schemas)
            
            for exclude_schema in default_excludes:
                cmd.extend([f"--exclude-schema={exclude_schema}"])
        
        return cmd
    
    def _execute_pg_dump(self, command: List[str], output_file: str) -> Tuple[bool, str]:
        """
        Execute pg_dump command and capture output.
        
        Args:
            command: pg_dump command arguments
            output_file: Path to output file
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Set PGPASSWORD environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_config['password']
            
            # Add output file to command
            cmd_with_output = command + [f"--file={output_file}"]
            
            logger.info(f"Executing pg_dump command: {' '.join(cmd_with_output[:5])}...")
            
            # Execute pg_dump
            result = subprocess.run(
                cmd_with_output,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                logger.info("pg_dump completed successfully")
                return True, ""
            else:
                error_msg = f"pg_dump failed with return code {result.returncode}: {result.stderr}"
                logger.error(error_msg)
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            error_msg = "pg_dump timed out after 1 hour"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error executing pg_dump: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _compress_file(self, input_file: str, output_file: str) -> Tuple[bool, str]:
        """
        Compress file using gzip.
        
        Args:
            input_file: Path to input file
            output_file: Path to compressed output file
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            with open(input_file, 'rb') as f_in:
                with gzip.open(output_file, 'wb', compresslevel=9) as f_out:
                    f_out.writelines(f_in)
            
            logger.info(f"File compressed successfully: {input_file} -> {output_file}")
            return True, ""
            
        except Exception as e:
            error_msg = f"Error compressing file: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _encrypt_file(self, input_file: str, output_file: str) -> Tuple[bool, str]:
        """
        Encrypt file using Fernet encryption.
        
        Args:
            input_file: Path to input file
            output_file: Path to encrypted output file
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            with open(input_file, 'rb') as f_in:
                data = f_in.read()
            
            encrypted_data = self.fernet.encrypt(data)
            
            with open(output_file, 'wb') as f_out:
                f_out.write(encrypted_data)
            
            logger.info(f"File encrypted successfully: {input_file} -> {output_file}")
            return True, ""
            
        except Exception as e:
            error_msg = f"Error encrypting file: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file."""
        hash_sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    def _upload_backup_to_storage(self, file_path: str, storage_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Upload backup file to redundant storage.
        
        Args:
            file_path: Local file path
            storage_path: Storage path
        
        Returns:
            Tuple of (success, upload_results)
        """
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            upload_result = self.storage_manager.upload_backup_file(
                storage_path,
                file_content,
                use_redundant=True
            )
            
            return upload_result['success'], upload_result
            
        except Exception as e:
            error_msg = f"Error uploading backup to storage: {str(e)}"
            logger.error(error_msg)
            return False, {'errors': [error_msg]}
    
    def create_full_system_backup(self, frequency: str = 'manual', created_by: str = 'system') -> Dict[str, Any]:
        """
        Create a complete system backup including all tenant schemas.
        
        Args:
            frequency: Backup frequency (daily, weekly, monthly, manual)
            created_by: User or system that initiated the backup
        
        Returns:
            Dict containing backup results and metadata
        """
        backup_id = self._generate_backup_id('full_system')
        storage_path = self._get_backup_file_path(backup_id, 'full_system')
        
        # Create backup record
        backup_record = BackupRecord.objects.create(
            backup_id=backup_id,
            backup_type='full_system',
            frequency=frequency,
            file_path=storage_path,
            is_encrypted=self.encryption_enabled,
            created_by=created_by
        )
        
        logger.info(f"Starting full system backup: {backup_id}")
        backup_record.mark_started()
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Step 1: Create pg_dump
                dump_file = os.path.join(temp_dir, f"{backup_id}.sql")
                pg_dump_cmd = self._create_pg_dump_command()
                
                success, error_msg = self._execute_pg_dump(pg_dump_cmd, dump_file)
                if not success:
                    backup_record.mark_failed(f"pg_dump failed: {error_msg}")
                    return {'success': False, 'error': error_msg, 'backup_id': backup_id}
                
                # Step 2: Compress if enabled
                if self.compression_enabled:
                    compressed_file = os.path.join(temp_dir, f"{backup_id}.sql.gz")
                    success, error_msg = self._compress_file(dump_file, compressed_file)
                    if not success:
                        backup_record.mark_failed(f"Compression failed: {error_msg}")
                        return {'success': False, 'error': error_msg, 'backup_id': backup_id}
                    
                    final_file = compressed_file
                    os.remove(dump_file)  # Clean up uncompressed file
                else:
                    final_file = dump_file
                
                # Step 3: Encrypt if enabled
                if self.encryption_enabled:
                    encrypted_file = os.path.join(temp_dir, f"{backup_id}.sql.gz.enc")
                    success, error_msg = self._encrypt_file(final_file, encrypted_file)
                    if not success:
                        backup_record.mark_failed(f"Encryption failed: {error_msg}")
                        return {'success': False, 'error': error_msg, 'backup_id': backup_id}
                    
                    final_file = encrypted_file
                
                # Step 4: Calculate file hash and size
                file_hash = self._calculate_file_hash(final_file)
                file_size = os.path.getsize(final_file)
                
                # Step 5: Upload to storage
                success, upload_result = self._upload_backup_to_storage(final_file, storage_path)
                if not success:
                    error_msg = f"Storage upload failed: {upload_result.get('errors', ['Unknown error'])}"
                    backup_record.mark_failed(error_msg)
                    return {'success': False, 'error': error_msg, 'backup_id': backup_id}
                
                # Step 6: Update backup record
                backup_record.mark_completed(file_size=file_size, file_hash=file_hash)
                backup_record.update_storage_status(
                    primary_stored='cloudflare_r2' in upload_result.get('uploaded_to', []),
                    secondary_stored='backblaze_b2' in upload_result.get('uploaded_to', [])
                )
                
                # Add metadata
                backup_record.metadata = {
                    'compression_enabled': self.compression_enabled,
                    'encryption_enabled': self.encryption_enabled,
                    'pg_dump_version': self._get_pg_dump_version(),
                    'database_size': self._get_database_size(),
                    'tenant_count': self._get_tenant_count(),
                    'upload_details': upload_result
                }
                backup_record.save(update_fields=['metadata'])
                
                logger.info(f"Full system backup completed successfully: {backup_id}")
                
                return {
                    'success': True,
                    'backup_id': backup_id,
                    'file_size': file_size,
                    'file_hash': file_hash,
                    'storage_path': storage_path,
                    'metadata': backup_record.metadata
                }
                
        except Exception as e:
            error_msg = f"Unexpected error during full system backup: {str(e)}"
            logger.error(error_msg)
            backup_record.mark_failed(error_msg)
            return {'success': False, 'error': error_msg, 'backup_id': backup_id}
    
    def create_tenant_backup(self, tenant_schema: str, tenant_domain: str = None, 
                           frequency: str = 'manual', created_by: str = 'system') -> Dict[str, Any]:
        """
        Create backup for a specific tenant schema.
        
        Args:
            tenant_schema: Tenant schema name to backup
            tenant_domain: Tenant domain for identification
            frequency: Backup frequency
            created_by: User or system that initiated the backup
        
        Returns:
            Dict containing backup results and metadata
        """
        backup_id = self._generate_backup_id('tenant_only', tenant_schema)
        storage_path = self._get_backup_file_path(backup_id, 'tenant_only')
        
        # Create backup record
        backup_record = BackupRecord.objects.create(
            backup_id=backup_id,
            backup_type='tenant_only',
            frequency=frequency,
            tenant_schema=tenant_schema,
            tenant_domain=tenant_domain,
            file_path=storage_path,
            is_encrypted=self.encryption_enabled,
            created_by=created_by
        )
        
        logger.info(f"Starting tenant backup: {backup_id} for schema {tenant_schema}")
        backup_record.mark_started()
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Step 1: Create pg_dump for specific tenant schema
                dump_file = os.path.join(temp_dir, f"{backup_id}.sql")
                pg_dump_cmd = self._create_pg_dump_command(schema_name=tenant_schema)
                
                success, error_msg = self._execute_pg_dump(pg_dump_cmd, dump_file)
                if not success:
                    backup_record.mark_failed(f"pg_dump failed: {error_msg}")
                    return {'success': False, 'error': error_msg, 'backup_id': backup_id}
                
                # Step 2: Compress if enabled
                if self.compression_enabled:
                    compressed_file = os.path.join(temp_dir, f"{backup_id}.sql.gz")
                    success, error_msg = self._compress_file(dump_file, compressed_file)
                    if not success:
                        backup_record.mark_failed(f"Compression failed: {error_msg}")
                        return {'success': False, 'error': error_msg, 'backup_id': backup_id}
                    
                    final_file = compressed_file
                    os.remove(dump_file)
                else:
                    final_file = dump_file
                
                # Step 3: Encrypt if enabled
                if self.encryption_enabled:
                    encrypted_file = os.path.join(temp_dir, f"{backup_id}.sql.gz.enc")
                    success, error_msg = self._encrypt_file(final_file, encrypted_file)
                    if not success:
                        backup_record.mark_failed(f"Encryption failed: {error_msg}")
                        return {'success': False, 'error': error_msg, 'backup_id': backup_id}
                    
                    final_file = encrypted_file
                
                # Step 4: Calculate file hash and size
                file_hash = self._calculate_file_hash(final_file)
                file_size = os.path.getsize(final_file)
                
                # Step 5: Upload to storage
                success, upload_result = self._upload_backup_to_storage(final_file, storage_path)
                if not success:
                    error_msg = f"Storage upload failed: {upload_result.get('errors', ['Unknown error'])}"
                    backup_record.mark_failed(error_msg)
                    return {'success': False, 'error': error_msg, 'backup_id': backup_id}
                
                # Step 6: Update backup record
                backup_record.mark_completed(file_size=file_size, file_hash=file_hash)
                backup_record.update_storage_status(
                    primary_stored='cloudflare_r2' in upload_result.get('uploaded_to', []),
                    secondary_stored='backblaze_b2' in upload_result.get('uploaded_to', [])
                )
                
                # Add metadata
                backup_record.metadata = {
                    'tenant_schema': tenant_schema,
                    'tenant_domain': tenant_domain,
                    'compression_enabled': self.compression_enabled,
                    'encryption_enabled': self.encryption_enabled,
                    'pg_dump_version': self._get_pg_dump_version(),
                    'schema_size': self._get_schema_size(tenant_schema),
                    'upload_details': upload_result
                }
                backup_record.save(update_fields=['metadata'])
                
                logger.info(f"Tenant backup completed successfully: {backup_id}")
                
                return {
                    'success': True,
                    'backup_id': backup_id,
                    'file_size': file_size,
                    'file_hash': file_hash,
                    'storage_path': storage_path,
                    'metadata': backup_record.metadata
                }
                
        except Exception as e:
            error_msg = f"Unexpected error during tenant backup: {str(e)}"
            logger.error(error_msg)
            backup_record.mark_failed(error_msg)
            return {'success': False, 'error': error_msg, 'backup_id': backup_id}
    
    def create_snapshot_backup(self, tenant_schema: str, operation_description: str = "High-risk operation",
                             created_by: str = 'system') -> Dict[str, Any]:
        """
        Create a temporary snapshot backup before high-risk operations.
        
        Args:
            tenant_schema: Tenant schema to snapshot
            operation_description: Description of the operation requiring snapshot
            created_by: User or system creating the snapshot
        
        Returns:
            Dict containing snapshot results and metadata
        """
        backup_id = self._generate_backup_id('snapshot', tenant_schema)
        storage_path = self._get_backup_file_path(backup_id, 'snapshot')
        
        # Create backup record with shorter retention (7 days for snapshots)
        expires_at = timezone.now() + timedelta(days=7)
        
        backup_record = BackupRecord.objects.create(
            backup_id=backup_id,
            backup_type='snapshot',
            frequency='snapshot',
            tenant_schema=tenant_schema,
            file_path=storage_path,
            is_encrypted=self.encryption_enabled,
            expires_at=expires_at,
            created_by=created_by
        )
        
        logger.info(f"Starting snapshot backup: {backup_id} for {operation_description}")
        
        # Use the same logic as tenant backup but with snapshot metadata
        result = self.create_tenant_backup(
            tenant_schema=tenant_schema,
            frequency='snapshot',
            created_by=created_by
        )
        
        if result['success']:
            # Update the backup record with snapshot-specific metadata
            backup_record = BackupRecord.objects.get(backup_id=result['backup_id'])
            backup_record.backup_type = 'snapshot'
            backup_record.expires_at = expires_at
            backup_record.metadata.update({
                'operation_description': operation_description,
                'is_snapshot': True,
                'auto_expires': True
            })
            backup_record.save(update_fields=['backup_type', 'expires_at', 'metadata'])
        
        return result
    
    def verify_backup_integrity(self, backup_id: str) -> Dict[str, Any]:
        """
        Verify the integrity of a backup file.
        
        Args:
            backup_id: ID of backup to verify
        
        Returns:
            Dict containing verification results
        """
        try:
            backup_record = BackupRecord.objects.get(backup_id=backup_id)
        except BackupRecord.DoesNotExist:
            return {'success': False, 'error': f'Backup {backup_id} not found'}
        
        # Create integrity check record
        integrity_check = BackupIntegrityCheck.objects.create(
            backup_record=backup_record,
            expected_hash=backup_record.file_hash
        )
        
        logger.info(f"Starting integrity verification for backup: {backup_id}")
        integrity_check.mark_started()
        
        try:
            # Download backup file from storage
            file_content = self.storage_manager.download_backup_file(backup_record.file_path)
            
            if file_content is None:
                error_msg = "Failed to download backup file from storage"
                integrity_check.mark_error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # Calculate hash of downloaded file
            actual_hash = hashlib.sha256(file_content).hexdigest()
            file_size = len(file_content)
            
            # Compare hashes
            integrity_passed = actual_hash == backup_record.file_hash
            
            # Update integrity check record
            integrity_check.mark_completed(
                passed=integrity_passed,
                actual_hash=actual_hash,
                file_size=file_size
            )
            
            if integrity_passed:
                logger.info(f"Backup integrity verification passed: {backup_id}")
                return {
                    'success': True,
                    'integrity_passed': True,
                    'file_size': file_size,
                    'expected_hash': backup_record.file_hash,
                    'actual_hash': actual_hash
                }
            else:
                logger.error(f"Backup integrity verification failed: {backup_id}")
                backup_record.status = 'corrupted'
                backup_record.save(update_fields=['status'])
                
                return {
                    'success': True,
                    'integrity_passed': False,
                    'file_size': file_size,
                    'expected_hash': backup_record.file_hash,
                    'actual_hash': actual_hash,
                    'error': 'Hash mismatch - backup file may be corrupted'
                }
                
        except Exception as e:
            error_msg = f"Error during integrity verification: {str(e)}"
            logger.error(error_msg)
            integrity_check.mark_error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def cleanup_expired_backups(self) -> Dict[str, Any]:
        """
        Clean up expired backup files from storage and database.
        
        Returns:
            Dict containing cleanup results
        """
        logger.info("Starting cleanup of expired backups")
        
        # Find expired backups
        expired_backups = BackupRecord.objects.filter(
            expires_at__lt=timezone.now(),
            status__in=['completed', 'failed', 'corrupted']
        )
        
        cleanup_results = {
            'total_expired': expired_backups.count(),
            'deleted_successfully': 0,
            'deletion_errors': 0,
            'errors': []
        }
        
        for backup in expired_backups:
            try:
                # Delete from storage
                delete_result = self.storage_manager.delete_backup_file(
                    backup.file_path,
                    from_all_backends=True
                )
                
                if delete_result['success']:
                    # Mark as expired and delete from database
                    backup.status = 'expired'
                    backup.save(update_fields=['status'])
                    backup.delete()
                    
                    cleanup_results['deleted_successfully'] += 1
                    logger.info(f"Deleted expired backup: {backup.backup_id}")
                else:
                    cleanup_results['deletion_errors'] += 1
                    error_msg = f"Failed to delete backup {backup.backup_id}: {delete_result.get('errors', [])}"
                    cleanup_results['errors'].append(error_msg)
                    logger.error(error_msg)
                    
            except Exception as e:
                cleanup_results['deletion_errors'] += 1
                error_msg = f"Error deleting backup {backup.backup_id}: {str(e)}"
                cleanup_results['errors'].append(error_msg)
                logger.error(error_msg)
        
        logger.info(f"Backup cleanup completed: {cleanup_results['deleted_successfully']} deleted, "
                   f"{cleanup_results['deletion_errors']} errors")
        
        return cleanup_results
    
    def get_backup_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive backup statistics.
        
        Returns:
            Dict containing backup statistics
        """
        from django.db.models import Count, Sum, Avg
        
        # Basic counts
        total_backups = BackupRecord.objects.count()
        completed_backups = BackupRecord.objects.filter(status='completed').count()
        failed_backups = BackupRecord.objects.filter(status='failed').count()
        
        # Storage statistics
        storage_stats = BackupRecord.objects.filter(status='completed').aggregate(
            total_size=Sum('file_size'),
            avg_size=Avg('file_size')
        )
        
        # Backup type distribution
        type_distribution = BackupRecord.objects.values('backup_type').annotate(
            count=Count('id')
        ).order_by('backup_type')
        
        # Recent backup activity (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_backups = BackupRecord.objects.filter(
            created_at__gte=thirty_days_ago
        ).count()
        
        # Storage redundancy status
        redundant_backups = BackupRecord.objects.filter(
            stored_in_primary=True,
            stored_in_secondary=True,
            status='completed'
        ).count()
        
        return {
            'total_backups': total_backups,
            'completed_backups': completed_backups,
            'failed_backups': failed_backups,
            'success_rate': (completed_backups / total_backups * 100) if total_backups > 0 else 0,
            'total_storage_used': storage_stats['total_size'] or 0,
            'average_backup_size': storage_stats['avg_size'] or 0,
            'type_distribution': list(type_distribution),
            'recent_activity': recent_backups,
            'redundant_backups': redundant_backups,
            'redundancy_rate': (redundant_backups / completed_backups * 100) if completed_backups > 0 else 0
        }
    
    def _get_pg_dump_version(self) -> str:
        """Get pg_dump version."""
        try:
            result = subprocess.run(['pg_dump', '--version'], capture_output=True, text=True)
            return result.stdout.strip() if result.returncode == 0 else 'Unknown'
        except:
            return 'Unknown'
    
    def _get_database_size(self) -> int:
        """Get total database size in bytes."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_database_size(current_database())")
                return cursor.fetchone()[0]
        except:
            return 0
    
    def _get_schema_size(self, schema_name: str) -> int:
        """Get size of specific schema in bytes."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COALESCE(SUM(pg_total_relation_size(schemaname||'.'||tablename)), 0)
                    FROM pg_tables 
                    WHERE schemaname = %s
                """, [schema_name])
                return cursor.fetchone()[0]
        except:
            return 0
    
    def _get_tenant_count(self) -> int:
        """Get total number of tenant schemas."""
        try:
            Tenant = get_tenant_model()
            return Tenant.objects.count()
        except:
            return 0


# Global backup manager instance
backup_manager = BackupManager()