"""
Celery tasks for backup and restore operations.
"""
import os
import subprocess
import tempfile
import logging
from datetime import datetime
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