"""
Celery tasks for backup, restore, and system health monitoring operations.
"""
import os
import subprocess
import tempfile
import logging
from datetime import datetime, timedelta
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from zargar.core.storage_utils import storage_manager

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def start_backup_job(self, job_id):
    """
    Start a backup job asynchronously.
    
    Args:
        job_id: UUID of the backup job to execute
    """
    from .models import BackupJob
    
    try:
        # Get the backup job
        backup_job = BackupJob.objects.get(job_id=job_id)
        backup_job.mark_as_running()
        
        logger.info(f"Starting backup job {job_id}: {backup_job.name}")
        
        # Execute backup based on type
        if backup_job.backup_type == 'full_system':
            result = perform_full_system_backup(backup_job)
        elif backup_job.backup_type == 'database_only':
            result = perform_database_backup(backup_job)
        elif backup_job.backup_type == 'configuration':
            result = perform_configuration_backup(backup_job)
        elif backup_job.backup_type == 'tenant_only':
            result = perform_tenant_backup(backup_job)
        else:
            raise ValueError(f"Unknown backup type: {backup_job.backup_type}")
        
        if result['success']:
            backup_job.mark_as_completed(
                file_path=result['file_path'],
                file_size_bytes=result['file_size'],
                storage_backends=result['storage_backends']
            )
            logger.info(f"Backup job {job_id} completed successfully")
        else:
            backup_job.mark_as_failed(result['error'])
            logger.error(f"Backup job {job_id} failed: {result['error']}")
            
    except BackupJob.DoesNotExist:
        logger.error(f"Backup job {job_id} not found")
    except Exception as e:
        logger.error(f"Error in backup job {job_id}: {str(e)}")
        try:
            backup_job = BackupJob.objects.get(job_id=job_id)
            backup_job.mark_as_failed(str(e))
        except:
            pass


@shared_task(bind=True)
def start_restore_job(self, job_id):
    """
    Start a restore job asynchronously.
    
    Args:
        job_id: UUID of the restore job to execute
    """
    from .models import RestoreJob
    
    try:
        # Get the restore job
        restore_job = RestoreJob.objects.get(job_id=job_id)
        restore_job.status = 'running'
        restore_job.started_at = timezone.now()
        restore_job.save()
        
        logger.info(f"Starting restore job {job_id}")
        
        # Execute restore based on type
        if restore_job.restore_type == 'single_tenant':
            result = perform_single_tenant_restore(restore_job)
        elif restore_job.restore_type == 'full_system':
            result = perform_full_system_restore(restore_job)
        elif restore_job.restore_type == 'configuration':
            result = perform_configuration_restore(restore_job)
        else:
            raise ValueError(f"Unknown restore type: {restore_job.restore_type}")
        
        if result['success']:
            restore_job.status = 'completed'
            restore_job.completed_at = timezone.now()
            restore_job.progress_percentage = 100
            restore_job.add_log_message('info', 'Restore completed successfully')
            restore_job.save()
            logger.info(f"Restore job {job_id} completed successfully")
        else:
            restore_job.status = 'failed'
            restore_job.completed_at = timezone.now()
            restore_job.error_message = result['error']
            restore_job.add_log_message('error', f'Restore failed: {result["error"]}')
            restore_job.save()
            logger.error(f"Restore job {job_id} failed: {result['error']}")
            
    except RestoreJob.DoesNotExist:
        logger.error(f"Restore job {job_id} not found")
    except Exception as e:
        logger.error(f"Error in restore job {job_id}: {str(e)}")
        try:
            restore_job = RestoreJob.objects.get(job_id=job_id)
            restore_job.status = 'failed'
            restore_job.completed_at = timezone.now()
            restore_job.error_message = str(e)
            restore_job.save()
        except:
            pass


def perform_full_system_backup(backup_job):
    """
    Perform a full system backup including all tenant schemas.
    
    Args:
        backup_job: BackupJob instance
        
    Returns:
        dict: Result with success status, file_path, file_size, storage_backends, or error
    """
    try:
        backup_job.update_progress(10, "Starting full system backup")
        
        # Generate backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"full_system_backup_{timestamp}.sql"
        
        # Create temporary file for backup
        with tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix='.sql') as temp_file:
            temp_path = temp_file.name
        
        backup_job.update_progress(20, "Creating database dump")
        
        # Perform pg_dump for all schemas
        pg_dump_cmd = [
            'pg_dump',
            '--host', settings.DATABASES['default']['HOST'],
            '--port', str(settings.DATABASES['default']['PORT']),
            '--username', settings.DATABASES['default']['USER'],
            '--no-password',
            '--verbose',
            '--clean',
            '--no-acl',
            '--no-owner',
            '--format=custom',
            '--file', temp_path,
            settings.DATABASES['default']['NAME']
        ]
        
        # Set password via environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = settings.DATABASES['default']['PASSWORD']
        
        backup_job.update_progress(30, "Executing pg_dump command")
        
        # Execute pg_dump
        result = subprocess.run(
            pg_dump_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode != 0:
            raise Exception(f"pg_dump failed: {result.stderr}")
        
        backup_job.update_progress(60, "Database dump completed, uploading to storage")
        
        # Get file size
        file_size = os.path.getsize(temp_path)
        
        # Read backup file content
        with open(temp_path, 'rb') as f:
            backup_content = f.read()
        
        backup_job.update_progress(70, "Uploading to redundant storage")
        
        # Upload to storage
        upload_result = storage_manager.upload_backup_file(
            file_path=f"backups/full_system/{backup_filename}",
            content=backup_content,
            use_redundant=True
        )
        
        if not upload_result['success']:
            raise Exception(f"Storage upload failed: {upload_result['errors']}")
        
        backup_job.update_progress(90, "Upload completed, cleaning up")
        
        # Clean up temporary file
        os.unlink(temp_path)
        
        backup_job.update_progress(100, "Backup completed successfully")
        
        return {
            'success': True,
            'file_path': f"backups/full_system/{backup_filename}",
            'file_size': file_size,
            'storage_backends': upload_result['uploaded_to']
        }
        
    except Exception as e:
        # Clean up temporary file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        
        return {
            'success': False,
            'error': str(e)
        }


def perform_database_backup(backup_job):
    """
    Perform a database-only backup.
    
    Args:
        backup_job: BackupJob instance
        
    Returns:
        dict: Result with success status, file_path, file_size, storage_backends, or error
    """
    try:
        backup_job.update_progress(10, "Starting database backup")
        
        # Generate backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"database_backup_{timestamp}.sql"
        
        # Create temporary file for backup
        with tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix='.sql') as temp_file:
            temp_path = temp_file.name
        
        backup_job.update_progress(20, "Creating database dump")
        
        # Perform pg_dump for database only (no configuration files)
        pg_dump_cmd = [
            'pg_dump',
            '--host', settings.DATABASES['default']['HOST'],
            '--port', str(settings.DATABASES['default']['PORT']),
            '--username', settings.DATABASES['default']['USER'],
            '--no-password',
            '--verbose',
            '--clean',
            '--no-acl',
            '--no-owner',
            '--format=custom',
            '--file', temp_path,
            settings.DATABASES['default']['NAME']
        ]
        
        # Set password via environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = settings.DATABASES['default']['PASSWORD']
        
        backup_job.update_progress(40, "Executing pg_dump command")
        
        # Execute pg_dump
        result = subprocess.run(
            pg_dump_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes timeout
        )
        
        if result.returncode != 0:
            raise Exception(f"pg_dump failed: {result.stderr}")
        
        backup_job.update_progress(70, "Database dump completed, uploading to storage")
        
        # Get file size
        file_size = os.path.getsize(temp_path)
        
        # Read backup file content
        with open(temp_path, 'rb') as f:
            backup_content = f.read()
        
        backup_job.update_progress(80, "Uploading to storage")
        
        # Upload to storage
        upload_result = storage_manager.upload_backup_file(
            file_path=f"backups/database/{backup_filename}",
            content=backup_content,
            use_redundant=True
        )
        
        if not upload_result['success']:
            raise Exception(f"Storage upload failed: {upload_result['errors']}")
        
        backup_job.update_progress(95, "Upload completed, cleaning up")
        
        # Clean up temporary file
        os.unlink(temp_path)
        
        backup_job.update_progress(100, "Database backup completed successfully")
        
        return {
            'success': True,
            'file_path': f"backups/database/{backup_filename}",
            'file_size': file_size,
            'storage_backends': upload_result['uploaded_to']
        }
        
    except Exception as e:
        # Clean up temporary file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        
        return {
            'success': False,
            'error': str(e)
        }


def perform_configuration_backup(backup_job):
    """
    Perform a configuration-only backup.
    
    Args:
        backup_job: BackupJob instance
        
    Returns:
        dict: Result with success status, file_path, file_size, storage_backends, or error
    """
    try:
        backup_job.update_progress(10, "Starting configuration backup")
        
        import tarfile
        import io
        
        # Generate backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"configuration_backup_{timestamp}.tar.gz"
        
        backup_job.update_progress(30, "Creating configuration archive")
        
        # Create tar.gz archive in memory
        tar_buffer = io.BytesIO()
        
        with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
            # Add configuration files
            config_files = [
                'docker-compose.yml',
                'docker-compose.prod.yml',
                'nginx.conf',
                '.env.example',
                'requirements.txt',
                'Dockerfile'
            ]
            
            for config_file in config_files:
                file_path = os.path.join(settings.BASE_DIR.parent, config_file)
                if os.path.exists(file_path):
                    tar.add(file_path, arcname=config_file)
                    backup_job.add_log_message('info', f'Added {config_file} to backup')
            
            # Add settings directory
            settings_dir = os.path.join(settings.BASE_DIR, 'zargar', 'settings')
            if os.path.exists(settings_dir):
                tar.add(settings_dir, arcname='zargar/settings')
                backup_job.add_log_message('info', 'Added settings directory to backup')
        
        backup_job.update_progress(60, "Configuration archive created, uploading to storage")
        
        # Get archive content
        backup_content = tar_buffer.getvalue()
        file_size = len(backup_content)
        
        backup_job.update_progress(70, "Uploading to storage")
        
        # Upload to storage
        upload_result = storage_manager.upload_backup_file(
            file_path=f"backups/configuration/{backup_filename}",
            content=backup_content,
            use_redundant=True
        )
        
        if not upload_result['success']:
            raise Exception(f"Storage upload failed: {upload_result['errors']}")
        
        backup_job.update_progress(100, "Configuration backup completed successfully")
        
        return {
            'success': True,
            'file_path': f"backups/configuration/{backup_filename}",
            'file_size': file_size,
            'storage_backends': upload_result['uploaded_to']
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def perform_tenant_backup(backup_job):
    """
    Perform a single tenant backup.
    
    Args:
        backup_job: BackupJob instance
        
    Returns:
        dict: Result with success status, file_path, file_size, storage_backends, or error
    """
    try:
        if not backup_job.tenant_schema:
            raise ValueError("Tenant schema not specified for tenant backup")
        
        backup_job.update_progress(10, f"Starting backup for tenant: {backup_job.tenant_schema}")
        
        # Generate backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"tenant_{backup_job.tenant_schema}_{timestamp}.sql"
        
        # Create temporary file for backup
        with tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix='.sql') as temp_file:
            temp_path = temp_file.name
        
        backup_job.update_progress(20, "Creating tenant schema dump")
        
        # Perform pg_dump for specific schema
        pg_dump_cmd = [
            'pg_dump',
            '--host', settings.DATABASES['default']['HOST'],
            '--port', str(settings.DATABASES['default']['PORT']),
            '--username', settings.DATABASES['default']['USER'],
            '--no-password',
            '--verbose',
            '--clean',
            '--no-acl',
            '--no-owner',
            '--format=custom',
            '--schema', backup_job.tenant_schema,
            '--file', temp_path,
            settings.DATABASES['default']['NAME']
        ]
        
        # Set password via environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = settings.DATABASES['default']['PASSWORD']
        
        backup_job.update_progress(40, "Executing pg_dump for tenant schema")
        
        # Execute pg_dump
        result = subprocess.run(
            pg_dump_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes timeout
        )
        
        if result.returncode != 0:
            raise Exception(f"pg_dump failed: {result.stderr}")
        
        backup_job.update_progress(70, "Tenant dump completed, uploading to storage")
        
        # Get file size
        file_size = os.path.getsize(temp_path)
        
        # Read backup file content
        with open(temp_path, 'rb') as f:
            backup_content = f.read()
        
        backup_job.update_progress(80, "Uploading to storage")
        
        # Upload to storage
        upload_result = storage_manager.upload_backup_file(
            file_path=f"backups/tenants/{backup_filename}",
            content=backup_content,
            use_redundant=True
        )
        
        if not upload_result['success']:
            raise Exception(f"Storage upload failed: {upload_result['errors']}")
        
        backup_job.update_progress(95, "Upload completed, cleaning up")
        
        # Clean up temporary file
        os.unlink(temp_path)
        
        backup_job.update_progress(100, f"Tenant backup completed successfully for {backup_job.tenant_schema}")
        
        return {
            'success': True,
            'file_path': f"backups/tenants/{backup_filename}",
            'file_size': file_size,
            'storage_backends': upload_result['uploaded_to']
        }
        
    except Exception as e:
        # Clean up temporary file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        
        return {
            'success': False,
            'error': str(e)
        }


def perform_single_tenant_restore(restore_job):
    """
    Perform a single tenant restore from backup.
    
    Args:
        restore_job: RestoreJob instance
        
    Returns:
        dict: Result with success status or error
    """
    try:
        restore_job.update_progress(10, f"Starting restore for tenant: {restore_job.target_tenant_schema}")
        
        # Download backup file from storage
        backup_content = storage_manager.download_backup_file(restore_job.source_backup.file_path)
        if not backup_content:
            raise Exception("Failed to download backup file from storage")
        
        restore_job.update_progress(30, "Backup file downloaded, creating temporary file")
        
        # Create temporary file for restore
        with tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix='.sql') as temp_file:
            temp_file.write(backup_content)
            temp_path = temp_file.name
        
        restore_job.update_progress(50, "Dropping existing tenant schema")
        
        # Drop existing schema (WARNING: This is destructive!)
        drop_schema_cmd = [
            'psql',
            '--host', settings.DATABASES['default']['HOST'],
            '--port', str(settings.DATABASES['default']['PORT']),
            '--username', settings.DATABASES['default']['USER'],
            '--no-password',
            '--dbname', settings.DATABASES['default']['NAME'],
            '--command', f'DROP SCHEMA IF EXISTS "{restore_job.target_tenant_schema}" CASCADE;'
        ]
        
        # Set password via environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = settings.DATABASES['default']['PASSWORD']
        
        # Execute schema drop
        result = subprocess.run(
            drop_schema_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode != 0:
            raise Exception(f"Schema drop failed: {result.stderr}")
        
        restore_job.update_progress(70, "Restoring tenant data from backup")
        
        # Restore from backup
        pg_restore_cmd = [
            'pg_restore',
            '--host', settings.DATABASES['default']['HOST'],
            '--port', str(settings.DATABASES['default']['PORT']),
            '--username', settings.DATABASES['default']['USER'],
            '--no-password',
            '--verbose',
            '--clean',
            '--no-acl',
            '--no-owner',
            '--dbname', settings.DATABASES['default']['NAME'],
            temp_path
        ]
        
        # Execute pg_restore
        result = subprocess.run(
            pg_restore_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes timeout
        )
        
        if result.returncode != 0:
            # pg_restore might return non-zero even on success due to warnings
            # Check if it's a real error or just warnings
            if "ERROR" in result.stderr:
                raise Exception(f"pg_restore failed: {result.stderr}")
        
        restore_job.update_progress(95, "Restore completed, cleaning up")
        
        # Clean up temporary file
        os.unlink(temp_path)
        
        restore_job.update_progress(100, f"Tenant restore completed successfully for {restore_job.target_tenant_schema}")
        
        return {
            'success': True
        }
        
    except Exception as e:
        # Clean up temporary file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        
        return {
            'success': False,
            'error': str(e)
        }


def perform_full_system_restore(restore_job):
    """
    Perform a full system restore from backup.
    
    Args:
        restore_job: RestoreJob instance
        
    Returns:
        dict: Result with success status or error
    """
    # This is a very dangerous operation and should be implemented with extreme caution
    # For now, we'll return an error to prevent accidental full system restores
    return {
        'success': False,
        'error': 'Full system restore is not implemented for safety reasons. Please contact system administrator.'
    }


def perform_configuration_restore(restore_job):
    """
    Perform a configuration restore from backup.
    
    Args:
        restore_job: RestoreJob instance
        
    Returns:
        dict: Result with success status or error
    """
    # Configuration restore should be done manually to prevent system corruption
    return {
        'success': False,
        'error': 'Configuration restore must be performed manually. Please contact system administrator.'
    }


@shared_task
def cleanup_old_backups():
    """
    Clean up old backup files based on retention policies.
    """
    from .models import BackupJob, BackupSchedule
    
    try:
        logger.info("Starting backup cleanup task")
        
        # Get all backup schedules with retention policies
        schedules = BackupSchedule.objects.filter(is_active=True)
        
        for schedule in schedules:
            # Find old backups for this schedule type
            cutoff_date = timezone.now() - timezone.timedelta(days=schedule.retention_days)
            
            old_backups = BackupJob.objects.filter(
                backup_type=schedule.backup_type,
                created_at__lt=cutoff_date,
                status='completed'
            ).order_by('-created_at')[schedule.max_backups:]
            
            for backup in old_backups:
                try:
                    # Delete from storage
                    if backup.file_path:
                        delete_result = storage_manager.delete_backup_file(
                            backup.file_path, 
                            from_all_backends=True
                        )
                        
                        if delete_result['success']:
                            logger.info(f"Deleted old backup file: {backup.file_path}")
                        else:
                            logger.warning(f"Failed to delete backup file: {backup.file_path}")
                    
                    # Delete backup job record
                    backup.delete()
                    logger.info(f"Deleted old backup job: {backup.name}")
                    
                except Exception as e:
                    logger.error(f"Error deleting backup {backup.id}: {str(e)}")
        
        logger.info("Backup cleanup task completed")
        
    except Exception as e:
        logger.error(f"Error in backup cleanup task: {str(e)}")


@shared_task(bind=True)
def create_tenant_snapshot(self, tenant_schema, operation_description, created_by_id=None, created_by_username='system'):
    """
    Create a temporary snapshot backup before high-risk tenant operations.
    
    Args:
        tenant_schema: Schema name of the tenant to snapshot
        operation_description: Description of the operation requiring snapshot
        created_by_id: ID of user creating snapshot
        created_by_username: Username of user creating snapshot
        
    Returns:
        dict: Result with success status, snapshot_id, or error
    """
    from .models import TenantSnapshot, BackupJob
    from zargar.tenants.models import Tenant
    
    try:
        logger.info(f"Creating tenant snapshot for schema: {tenant_schema}")
        
        # Get tenant information
        try:
            tenant = Tenant.objects.get(schema_name=tenant_schema)
            tenant_domain = tenant.domain_url
        except Tenant.DoesNotExist:
            tenant_domain = ''
        
        # Create snapshot record
        snapshot = TenantSnapshot.objects.create(
            name=f"Pre-operation snapshot - {operation_description[:50]}",
            snapshot_type='pre_operation',
            tenant_schema=tenant_schema,
            tenant_domain=tenant_domain,
            operation_description=operation_description,
            created_by_id=created_by_id,
            created_by_username=created_by_username,
            status='pending'
        )
        
        snapshot.mark_as_creating()
        
        # Create associated backup job
        backup_job = BackupJob.objects.create(
            name=f"Snapshot backup for {tenant_schema}",
            backup_type='tenant_only',
            tenant_schema=tenant_schema,
            frequency='manual',
            created_by_id=created_by_id,
            created_by_username=created_by_username,
            status='pending'
        )
        
        # Link snapshot to backup job
        snapshot.backup_job = backup_job
        snapshot.save(update_fields=['backup_job'])
        
        # Perform tenant backup for snapshot
        result = perform_tenant_backup(backup_job)
        
        if result['success']:
            snapshot.mark_as_completed(
                file_path=result['file_path'],
                file_size_bytes=result['file_size']
            )
            
            logger.info(f"Tenant snapshot created successfully: {snapshot.snapshot_id}")
            
            return {
                'success': True,
                'snapshot_id': str(snapshot.snapshot_id),
                'backup_id': str(backup_job.job_id),
                'file_path': result['file_path'],
                'file_size': result['file_size'],
                'tenant_schema': tenant_schema
            }
        else:
            snapshot.mark_as_failed(result['error'])
            backup_job.mark_as_failed(result['error'])
            
            logger.error(f"Tenant snapshot failed for {tenant_schema}: {result['error']}")
            
            return {
                'success': False,
                'error': result['error'],
                'snapshot_id': str(snapshot.snapshot_id),
                'tenant_schema': tenant_schema
            }
            
    except Exception as e:
        logger.error(f"Error creating tenant snapshot for {tenant_schema}: {str(e)}")
        
        # Mark snapshot as failed if it was created
        try:
            if 'snapshot' in locals():
                snapshot.mark_as_failed(str(e))
        except:
            pass
        
        return {
            'success': False,
            'error': str(e),
            'tenant_schema': tenant_schema
        }


@shared_task(bind=True)
def restore_tenant_from_backup(self, restore_job_id):
    """
    Restore a single tenant from a backup using pg_restore with schema-specific flags.
    
    Args:
        restore_job_id: UUID of the restore job to execute
        
    Returns:
        dict: Result with success status or error
    """
    from .models import RestoreJob
    
    try:
        # Get the restore job
        restore_job = RestoreJob.objects.get(job_id=restore_job_id)
        restore_job.mark_as_running()
        
        logger.info(f"Starting tenant restoration job {restore_job_id}")
        
        # Validate restore job
        if not restore_job.target_tenant_schema:
            raise ValueError("Target tenant schema not specified")
        
        if restore_job.restore_type not in ['single_tenant', 'snapshot_restore']:
            raise ValueError(f"Invalid restore type for tenant restoration: {restore_job.restore_type}")
        
        # Perform the restoration
        result = perform_selective_tenant_restore(restore_job)
        
        if result['success']:
            restore_job.mark_as_completed()
            logger.info(f"Tenant restoration completed successfully: {restore_job_id}")
        else:
            restore_job.mark_as_failed(result['error'])
            logger.error(f"Tenant restoration failed: {restore_job_id} - {result['error']}")
        
        return result
        
    except RestoreJob.DoesNotExist:
        logger.error(f"Restore job {restore_job_id} not found")
        return {'success': False, 'error': 'Restore job not found'}
    except Exception as e:
        logger.error(f"Error in tenant restoration job {restore_job_id}: {str(e)}")
        try:
            restore_job = RestoreJob.objects.get(job_id=restore_job_id)
            restore_job.mark_as_failed(str(e))
        except:
            pass
        return {'success': False, 'error': str(e)}


def perform_selective_tenant_restore(restore_job):
    """
    Perform selective tenant restoration from main backup using pg_restore with specific schema flags.
    
    Args:
        restore_job: RestoreJob instance
        
    Returns:
        dict: Result with success status or error
    """
    try:
        restore_job.update_progress(5, f"Starting selective restore for tenant: {restore_job.target_tenant_schema}")
        
        # Validate that other tenants won't be affected
        from zargar.tenants.models import Tenant
        
        # Ensure target tenant exists
        try:
            target_tenant = Tenant.objects.get(schema_name=restore_job.target_tenant_schema)
        except Tenant.DoesNotExist:
            raise Exception(f"Target tenant schema '{restore_job.target_tenant_schema}' does not exist")
        
        restore_job.update_progress(10, "Downloading backup file from storage")
        
        # Download backup file from storage
        backup_content = storage_manager.download_backup_file(restore_job.source_backup.file_path)
        if not backup_content:
            raise Exception("Failed to download backup file from storage")
        
        restore_job.update_progress(25, "Backup file downloaded, preparing for restoration")
        
        # Create temporary file for restore
        with tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix='.sql') as temp_file:
            temp_file.write(backup_content)
            temp_path = temp_file.name
        
        restore_job.update_progress(35, "Creating pre-restoration snapshot for safety")
        
        # Create a safety snapshot before restoration (if not already a snapshot restore)
        if restore_job.restore_type != 'snapshot_restore':
            safety_snapshot_result = create_tenant_snapshot.apply(
                args=[
                    restore_job.target_tenant_schema,
                    f"Safety snapshot before restore from {restore_job.source_backup.name}",
                    restore_job.created_by_id,
                    restore_job.created_by_username
                ]
            )
            
            if not safety_snapshot_result.get('success', False):
                logger.warning(f"Failed to create safety snapshot: {safety_snapshot_result.get('error', 'Unknown error')}")
                # Continue with restore despite snapshot failure
        
        restore_job.update_progress(50, "Dropping existing tenant schema")
        
        # Drop existing schema (WARNING: This is destructive!)
        drop_schema_cmd = [
            'psql',
            '--host', settings.DATABASES['default']['HOST'],
            '--port', str(settings.DATABASES['default']['PORT']),
            '--username', settings.DATABASES['default']['USER'],
            '--no-password',
            '--dbname', settings.DATABASES['default']['NAME'],
            '--command', f'DROP SCHEMA IF EXISTS "{restore_job.target_tenant_schema}" CASCADE;'
        ]
        
        # Set password via environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = settings.DATABASES['default']['PASSWORD']
        
        restore_job.update_progress(60, "Executing schema drop command")
        
        # Execute schema drop
        result = subprocess.run(
            drop_schema_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        
        if result.returncode != 0:
            raise Exception(f"Schema drop failed: {result.stderr}")
        
        restore_job.update_progress(70, "Restoring tenant data from backup using pg_restore")
        
        # Restore from backup using pg_restore with schema-specific flags
        pg_restore_cmd = [
            'pg_restore',
            '--host', settings.DATABASES['default']['HOST'],
            '--port', str(settings.DATABASES['default']['PORT']),
            '--username', settings.DATABASES['default']['USER'],
            '--no-password',
            '--verbose',
            '--clean',
            '--no-acl',
            '--no-owner',
            '--schema', restore_job.target_tenant_schema,  # Only restore specific schema
            '--dbname', settings.DATABASES['default']['NAME'],
            temp_path
        ]
        
        restore_job.update_progress(80, "Executing pg_restore command")
        
        # Execute pg_restore
        result = subprocess.run(
            pg_restore_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode != 0:
            # pg_restore might return non-zero even on success due to warnings
            # Check if it's a real error or just warnings
            if "ERROR" in result.stderr and "already exists" not in result.stderr:
                raise Exception(f"pg_restore failed: {result.stderr}")
        
        restore_job.update_progress(90, "Verifying restored data integrity")
        
        # Verify that the schema was restored correctly
        verify_schema_cmd = [
            'psql',
            '--host', settings.DATABASES['default']['HOST'],
            '--port', str(settings.DATABASES['default']['PORT']),
            '--username', settings.DATABASES['default']['USER'],
            '--no-password',
            '--dbname', settings.DATABASES['default']['NAME'],
            '--tuples-only',
            '--command', f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '{restore_job.target_tenant_schema}';"
        ]
        
        # Execute verification
        verify_result = subprocess.run(
            verify_schema_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if verify_result.returncode == 0:
            table_count = int(verify_result.stdout.strip())
            if table_count == 0:
                raise Exception("Restored schema appears to be empty - restoration may have failed")
            restore_job.add_log_message('info', f'Verified {table_count} tables in restored schema')
        else:
            logger.warning(f"Schema verification failed: {verify_result.stderr}")
        
        restore_job.update_progress(95, "Restoration completed, cleaning up")
        
        # Clean up temporary file
        os.unlink(temp_path)
        
        restore_job.update_progress(100, f"Tenant restoration completed successfully for {restore_job.target_tenant_schema}")
        
        # Mark snapshot as used if this was a snapshot restore
        if restore_job.restore_type == 'snapshot_restore':
            try:
                from .models import TenantSnapshot
                snapshot = TenantSnapshot.objects.get(backup_job=restore_job.source_backup)
                snapshot.mark_as_restored(restore_job.created_by_id, restore_job.created_by_username)
            except TenantSnapshot.DoesNotExist:
                pass
        
        return {
            'success': True,
            'tenant_schema': restore_job.target_tenant_schema,
            'message': f'Tenant {restore_job.target_tenant_schema} restored successfully'
        }
        
    except Exception as e:
        # Clean up temporary file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def cleanup_expired_snapshots():
    """
    Clean up expired tenant snapshots.
    """
    from .models import TenantSnapshot
    
    try:
        logger.info("Starting cleanup of expired tenant snapshots")
        
        # Find expired snapshots
        expired_snapshots = TenantSnapshot.objects.filter(
            expires_at__lt=timezone.now(),
            status__in=['completed', 'failed']
        )
        
        cleanup_results = {
            'total_expired': expired_snapshots.count(),
            'deleted_successfully': 0,
            'deletion_errors': 0,
            'errors': []
        }
        
        for snapshot in expired_snapshots:
            try:
                # Delete backup file from storage if it exists
                if snapshot.file_path:
                    delete_result = storage_manager.delete_backup_file(
                        snapshot.file_path,
                        from_all_backends=True
                    )
                    
                    if not delete_result.get('success', False):
                        logger.warning(f"Failed to delete snapshot file: {snapshot.file_path}")
                
                # Delete associated backup job if it exists
                if snapshot.backup_job:
                    snapshot.backup_job.delete()
                
                # Mark snapshot as deleted
                snapshot.status = 'deleted'
                snapshot.save(update_fields=['status'])
                
                cleanup_results['deleted_successfully'] += 1
                logger.info(f"Deleted expired snapshot: {snapshot.snapshot_id}")
                
            except Exception as e:
                cleanup_results['deletion_errors'] += 1
                cleanup_results['errors'].append(f"Error deleting snapshot {snapshot.snapshot_id}: {str(e)}")
                logger.error(f"Error deleting expired snapshot {snapshot.snapshot_id}: {str(e)}")
        
        logger.info(f"Snapshot cleanup completed: {cleanup_results['deleted_successfully']} deleted, "
                   f"{cleanup_results['deletion_errors']} errors")
        
        return cleanup_results
        
    except Exception as e:
        logger.error(f"Error in snapshot cleanup task: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def schedule_automatic_backups():
    """
    Check for scheduled backups that need to be executed.
    """
    from .models import BackupSchedule, BackupJob
    
    try:
        logger.info("Checking for scheduled backups")
        
        current_time = timezone.now()
        
        # Find schedules that should run now
        schedules_to_run = BackupSchedule.objects.filter(
            is_active=True,
            frequency__in=['daily', 'weekly', 'monthly']
        )
        
        for schedule in schedules_to_run:
            # Check if it's time to run this schedule
            if should_run_schedule(schedule, current_time):
                # Create backup job
                backup_job = BackupJob.objects.create(
                    name=f"{schedule.name} - {current_time.strftime('%Y-%m-%d %H:%M')}",
                    backup_type=schedule.backup_type,
                    frequency=schedule.frequency,
                    status='pending'
                )
                
                # Start backup job
                start_backup_job.delay(backup_job.job_id)
                
                logger.info(f"Started scheduled backup: {schedule.name}")
        
    except Exception as e:
        logger.error(f"Error in scheduled backup task: {str(e)}")


def should_run_schedule(schedule, current_time):
    """
    Check if a backup schedule should run at the current time.
    
    Args:
        schedule: BackupSchedule instance
        current_time: Current datetime
        
    Returns:
        bool: True if schedule should run
    """
    # This is a simplified implementation
    # In a real system, you'd want more sophisticated scheduling logic
    
    if schedule.frequency == 'daily':
        # Run if it's the scheduled time and hasn't run today
        return (
            current_time.time() >= schedule.scheduled_time and
            not BackupJob.objects.filter(
                backup_type=schedule.backup_type,
                frequency='daily',
                created_at__date=current_time.date()
            ).exists()
        )
    
    elif schedule.frequency == 'weekly':
        # Run if it's the scheduled day and time
        return (
            current_time.weekday() == 0 and  # Monday
            current_time.time() >= schedule.scheduled_time and
            not BackupJob.objects.filter(
                backup_type=schedule.backup_type,
                frequency='weekly',
                created_at__week=current_time.isocalendar()[1],
                created_at__year=current_time.year
            ).exists()
        )
    
    elif schedule.frequency == 'monthly':
        # Run if it's the first day of the month
        return (
            current_time.day == 1 and
            current_time.time() >= schedule.scheduled_time and
            not BackupJob.objects.filter(
                backup_type=schedule.backup_type,
                frequency='monthly',
                created_at__month=current_time.month,
                created_at__year=current_time.year
            ).exists()
        )
    
    return False

# System Health Monitoring Tasks

@shared_task(bind=True)
def collect_system_health_metrics(self):
    """
    Periodic task to collect system health metrics.
    This task should be scheduled to run every 1-5 minutes.
    """
    try:
        from .system_health import system_health_monitor
        
        logger.info("Starting system health metrics collection")
        
        # Collect all metrics
        metrics = system_health_monitor.collect_all_metrics()
        
        # Log summary
        if 'error' not in metrics:
            logger.info(f"Successfully collected system health metrics: "
                       f"CPU: {metrics.get('cpu', {}).get('usage_percent', 'N/A')}%, "
                       f"Memory: {metrics.get('memory', {}).get('usage_percent', 'N/A')}%, "
                       f"Disk: {metrics.get('disk', {}).get('usage_percent', 'N/A')}%")
        else:
            logger.error(f"Error collecting system health metrics: {metrics['error']}")
        
        return {
            'success': True,
            'metrics_collected': len(metrics),
            'timestamp': timezone.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in collect_system_health_metrics task: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task(bind=True)
def cleanup_old_health_metrics(self):
    """
    Periodic task to clean up old health metrics.
    This task should be scheduled to run daily.
    """
    try:
        from .system_health import system_health_monitor
        
        logger.info("Starting cleanup of old health metrics")
        
        # Clean up metrics older than 30 days
        system_health_monitor.cleanup_old_metrics(days=30)
        
        logger.info("Successfully cleaned up old health metrics")
        
        return {
            'success': True,
            'timestamp': timezone.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in cleanup_old_health_metrics task: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task(bind=True)
def check_system_health_alerts(self):
    """
    Periodic task to check for system health issues and create alerts.
    This task should be scheduled to run every 5-10 minutes.
    """
    try:
        from .system_health import system_health_monitor
        from .models import SystemHealthAlert
        
        logger.info("Starting system health alert check")
        
        # Get current metrics
        metrics = system_health_monitor.collect_all_metrics()
        
        # Count active alerts before check
        active_alerts_before = SystemHealthAlert.objects.filter(status='active').count()
        
        # Alert checking is handled in collect_all_metrics via _check_alert_thresholds
        
        # Count active alerts after check
        active_alerts_after = SystemHealthAlert.objects.filter(status='active').count()
        
        new_alerts = active_alerts_after - active_alerts_before
        
        if new_alerts > 0:
            logger.warning(f"Created {new_alerts} new system health alerts")
        
        return {
            'success': True,
            'active_alerts': active_alerts_after,
            'new_alerts': new_alerts,
            'timestamp': timezone.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in check_system_health_alerts task: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task(bind=True)
def send_health_alert_notifications(self):
    """
    Periodic task to send notifications for critical health alerts.
    This task should be scheduled to run every 15-30 minutes.
    """
    try:
        from .models import SystemHealthAlert
        from django.core.mail import send_mail
        
        logger.info("Starting health alert notifications check")
        
        # Get critical alerts that haven't been notified recently
        critical_alerts = SystemHealthAlert.objects.filter(
            status='active',
            severity='critical',
            created_at__gte=timezone.now() - timedelta(hours=1)  # Only recent alerts
        )
        
        notifications_sent = 0
        
        for alert in critical_alerts:
            # Check if notification was already sent recently
            recent_notifications = [
                n for n in alert.notifications_sent 
                if n.get('type') == 'email' and 
                datetime.fromisoformat(n.get('timestamp', '1970-01-01T00:00:00')) > 
                timezone.now() - timedelta(hours=1)
            ]
            
            if not recent_notifications:
                # Send email notification
                try:
                    admin_emails = getattr(settings, 'ADMIN_NOTIFICATION_EMAILS', [])
                    if admin_emails:
                        subject = f"[ZARGAR] Critical System Alert: {alert.title}"
                        message = f"""
Critical system alert detected:

Title: {alert.title}
Description: {alert.description}
Severity: {alert.severity}
Category: {alert.category}
Created: {alert.created_at}

Current Value: {alert.current_value}
Threshold: {alert.threshold_value}

Please check the admin panel for more details.
                        """
                        
                        send_mail(
                            subject=subject,
                            message=message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=admin_emails,
                            fail_silently=False
                        )
                        
                        # Record notification
                        alert.add_notification('email', admin_emails, 'sent')
                        notifications_sent += 1
                        
                        logger.info(f"Sent critical alert notification for: {alert.title}")
                
                except Exception as e:
                    logger.error(f"Error sending notification for alert {alert.alert_id}: {e}")
                    alert.add_notification('email', 'admin', 'failed')
        
        return {
            'success': True,
            'notifications_sent': notifications_sent,
            'critical_alerts_checked': critical_alerts.count(),
            'timestamp': timezone.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in send_health_alert_notifications task: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task(bind=True)
def generate_health_report(self, report_type='daily'):
    """
    Generate system health reports.
    
    Args:
        report_type: Type of report ('daily', 'weekly', 'monthly')
    """
    try:
        from .models import SystemHealthMetric, SystemHealthAlert
        from django.db.models import Avg, Max, Min, Count
        
        logger.info(f"Generating {report_type} health report")
        
        # Determine time range
        if report_type == 'daily':
            since = timezone.now() - timedelta(days=1)
        elif report_type == 'weekly':
            since = timezone.now() - timedelta(days=7)
        elif report_type == 'monthly':
            since = timezone.now() - timedelta(days=30)
        else:
            raise ValueError(f"Invalid report type: {report_type}")
        
        # Collect metrics summary
        metrics_summary = {}
        metric_types = ['cpu_usage', 'memory_usage', 'disk_usage', 'redis_memory']
        
        for metric_type in metric_types:
            summary = SystemHealthMetric.objects.filter(
                metric_type=metric_type,
                timestamp__gte=since
            ).aggregate(
                avg_value=Avg('value'),
                max_value=Max('value'),
                min_value=Min('value'),
                count=Count('id')
            )
            
            metrics_summary[metric_type] = {
                'average': round(summary['avg_value'] or 0, 2),
                'maximum': round(summary['max_value'] or 0, 2),
                'minimum': round(summary['min_value'] or 0, 2),
                'data_points': summary['count']
            }
        
        # Alert summary
        alert_summary = SystemHealthAlert.objects.filter(
            created_at__gte=since
        ).values('severity').annotate(
            count=Count('id')
        )
        
        # Generate report content
        report_content = {
            'report_type': report_type,
            'period_start': since.isoformat(),
            'period_end': timezone.now().isoformat(),
            'metrics_summary': metrics_summary,
            'alert_summary': list(alert_summary),
            'generated_at': timezone.now().isoformat()
        }
        
        # Store report (you could save to file or database)
        logger.info(f"Generated {report_type} health report with {len(metrics_summary)} metric types")
        
        return {
            'success': True,
            'report_type': report_type,
            'report_content': report_content,
            'timestamp': timezone.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error generating {report_type} health report: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }