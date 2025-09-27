"""
Celery tasks for automated backup operations.
Provides scheduled backup tasks for the ZARGAR jewelry SaaS platform.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from celery import shared_task
from django.utils import timezone
from django_tenants.utils import get_tenant_model
from .backup_manager import backup_manager
from zargar.system.models import BackupRecord, BackupSchedule


logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def create_daily_backup(self, schedule_id: int = None, created_by: str = 'celery_daily'):
    """
    Create daily full system backup.
    
    Args:
        schedule_id: Optional backup schedule ID that triggered this task
        created_by: User or system that initiated the backup
    
    Returns:
        Dict containing backup results
    """
    logger.info("Starting daily backup task")
    
    try:
        # Create full system backup
        result = backup_manager.create_full_system_backup(
            frequency='daily',
            created_by=created_by
        )
        
        # Update schedule record if provided
        if schedule_id:
            try:
                schedule = BackupSchedule.objects.get(id=schedule_id)
                schedule.record_run(
                    success=result['success'],
                    backup_id=result.get('backup_id')
                )
            except BackupSchedule.DoesNotExist:
                logger.warning(f"Backup schedule {schedule_id} not found")
        
        if result['success']:
            logger.info(f"Daily backup completed successfully: {result['backup_id']}")
            
            # Schedule integrity verification
            verify_backup_integrity.apply_async(
                args=[result['backup_id']],
                countdown=300  # Verify after 5 minutes
            )
            
            return {
                'success': True,
                'backup_id': result['backup_id'],
                'file_size': result['file_size'],
                'message': 'Daily backup completed successfully'
            }
        else:
            logger.error(f"Daily backup failed: {result['error']}")
            return {
                'success': False,
                'error': result['error'],
                'backup_id': result.get('backup_id')
            }
            
    except Exception as e:
        error_msg = f"Unexpected error in daily backup task: {str(e)}"
        logger.error(error_msg)
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying daily backup task (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        
        return {'success': False, 'error': error_msg}


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def create_weekly_backup(self, schedule_id: int = None, created_by: str = 'celery_weekly'):
    """
    Create weekly full system backup with extended retention.
    
    Args:
        schedule_id: Optional backup schedule ID that triggered this task
        created_by: User or system that initiated the backup
    
    Returns:
        Dict containing backup results
    """
    logger.info("Starting weekly backup task")
    
    try:
        # Create full system backup
        result = backup_manager.create_full_system_backup(
            frequency='weekly',
            created_by=created_by
        )
        
        # Update schedule record if provided
        if schedule_id:
            try:
                schedule = BackupSchedule.objects.get(id=schedule_id)
                schedule.record_run(
                    success=result['success'],
                    backup_id=result.get('backup_id')
                )
            except BackupSchedule.DoesNotExist:
                logger.warning(f"Backup schedule {schedule_id} not found")
        
        if result['success']:
            logger.info(f"Weekly backup completed successfully: {result['backup_id']}")
            
            # Set extended retention for weekly backups (90 days)
            try:
                backup_record = BackupRecord.objects.get(backup_id=result['backup_id'])
                backup_record.expires_at = timezone.now() + timedelta(days=90)
                backup_record.save(update_fields=['expires_at'])
            except BackupRecord.DoesNotExist:
                logger.warning(f"Backup record {result['backup_id']} not found for retention update")
            
            # Schedule integrity verification
            verify_backup_integrity.apply_async(
                args=[result['backup_id']],
                countdown=300  # Verify after 5 minutes
            )
            
            # Schedule cleanup of old backups
            cleanup_old_backups.apply_async(countdown=600)  # Cleanup after 10 minutes
            
            return {
                'success': True,
                'backup_id': result['backup_id'],
                'file_size': result['file_size'],
                'message': 'Weekly backup completed successfully'
            }
        else:
            logger.error(f"Weekly backup failed: {result['error']}")
            return {
                'success': False,
                'error': result['error'],
                'backup_id': result.get('backup_id')
            }
            
    except Exception as e:
        error_msg = f"Unexpected error in weekly backup task: {str(e)}"
        logger.error(error_msg)
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying weekly backup task (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        
        return {'success': False, 'error': error_msg}


@shared_task(bind=True, max_retries=2, default_retry_delay=180)
def create_tenant_backup(self, tenant_schema: str, tenant_domain: str = None, 
                        frequency: str = 'manual', created_by: str = 'celery_tenant'):
    """
    Create backup for a specific tenant.
    
    Args:
        tenant_schema: Tenant schema name to backup
        tenant_domain: Tenant domain for identification
        frequency: Backup frequency
        created_by: User or system that initiated the backup
    
    Returns:
        Dict containing backup results
    """
    logger.info(f"Starting tenant backup task for schema: {tenant_schema}")
    
    try:
        # Create tenant backup
        result = backup_manager.create_tenant_backup(
            tenant_schema=tenant_schema,
            tenant_domain=tenant_domain,
            frequency=frequency,
            created_by=created_by
        )
        
        if result['success']:
            logger.info(f"Tenant backup completed successfully: {result['backup_id']}")
            
            # Schedule integrity verification
            verify_backup_integrity.apply_async(
                args=[result['backup_id']],
                countdown=180  # Verify after 3 minutes
            )
            
            return {
                'success': True,
                'backup_id': result['backup_id'],
                'file_size': result['file_size'],
                'tenant_schema': tenant_schema,
                'message': f'Tenant backup completed successfully for {tenant_schema}'
            }
        else:
            logger.error(f"Tenant backup failed for {tenant_schema}: {result['error']}")
            return {
                'success': False,
                'error': result['error'],
                'backup_id': result.get('backup_id'),
                'tenant_schema': tenant_schema
            }
            
    except Exception as e:
        error_msg = f"Unexpected error in tenant backup task for {tenant_schema}: {str(e)}"
        logger.error(error_msg)
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying tenant backup task for {tenant_schema} (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        
        return {'success': False, 'error': error_msg, 'tenant_schema': tenant_schema}


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def create_snapshot_backup(self, tenant_schema: str, operation_description: str = "High-risk operation",
                          created_by: str = 'celery_snapshot'):
    """
    Create a temporary snapshot backup before high-risk operations.
    
    Args:
        tenant_schema: Tenant schema to snapshot
        operation_description: Description of the operation requiring snapshot
        created_by: User or system creating the snapshot
    
    Returns:
        Dict containing snapshot results
    """
    logger.info(f"Starting snapshot backup task for schema: {tenant_schema}")
    
    try:
        # Create snapshot backup
        result = backup_manager.create_snapshot_backup(
            tenant_schema=tenant_schema,
            operation_description=operation_description,
            created_by=created_by
        )
        
        if result['success']:
            logger.info(f"Snapshot backup completed successfully: {result['backup_id']}")
            
            return {
                'success': True,
                'backup_id': result['backup_id'],
                'file_size': result['file_size'],
                'tenant_schema': tenant_schema,
                'operation_description': operation_description,
                'message': f'Snapshot backup completed successfully for {tenant_schema}'
            }
        else:
            logger.error(f"Snapshot backup failed for {tenant_schema}: {result['error']}")
            return {
                'success': False,
                'error': result['error'],
                'backup_id': result.get('backup_id'),
                'tenant_schema': tenant_schema
            }
            
    except Exception as e:
        error_msg = f"Unexpected error in snapshot backup task for {tenant_schema}: {str(e)}"
        logger.error(error_msg)
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying snapshot backup task for {tenant_schema} (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
        
        return {'success': False, 'error': error_msg, 'tenant_schema': tenant_schema}


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def verify_backup_integrity(self, backup_id: str):
    """
    Verify the integrity of a backup file.
    
    Args:
        backup_id: ID of backup to verify
    
    Returns:
        Dict containing verification results
    """
    logger.info(f"Starting backup integrity verification for: {backup_id}")
    
    try:
        # Verify backup integrity
        result = backup_manager.verify_backup_integrity(backup_id)
        
        if result['success']:
            if result.get('integrity_passed', False):
                logger.info(f"Backup integrity verification passed: {backup_id}")
                return {
                    'success': True,
                    'backup_id': backup_id,
                    'integrity_passed': True,
                    'message': f'Backup integrity verification passed for {backup_id}'
                }
            else:
                logger.error(f"Backup integrity verification failed: {backup_id}")
                return {
                    'success': True,
                    'backup_id': backup_id,
                    'integrity_passed': False,
                    'error': result.get('error', 'Integrity check failed'),
                    'message': f'Backup integrity verification failed for {backup_id}'
                }
        else:
            logger.error(f"Backup integrity verification error: {backup_id} - {result['error']}")
            return {
                'success': False,
                'backup_id': backup_id,
                'error': result['error']
            }
            
    except Exception as e:
        error_msg = f"Unexpected error in backup integrity verification for {backup_id}: {str(e)}"
        logger.error(error_msg)
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying backup integrity verification for {backup_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
        
        return {'success': False, 'error': error_msg, 'backup_id': backup_id}


@shared_task(bind=True, max_retries=1, default_retry_delay=300)
def cleanup_old_backups(self):
    """
    Clean up expired backup files from storage and database.
    
    Returns:
        Dict containing cleanup results
    """
    logger.info("Starting cleanup of old backups")
    
    try:
        # Clean up expired backups
        result = backup_manager.cleanup_expired_backups()
        
        logger.info(f"Backup cleanup completed: {result['deleted_successfully']} deleted, "
                   f"{result['deletion_errors']} errors")
        
        return {
            'success': True,
            'total_expired': result['total_expired'],
            'deleted_successfully': result['deleted_successfully'],
            'deletion_errors': result['deletion_errors'],
            'errors': result['errors'],
            'message': f"Cleanup completed: {result['deleted_successfully']} backups deleted"
        }
        
    except Exception as e:
        error_msg = f"Unexpected error in backup cleanup task: {str(e)}"
        logger.error(error_msg)
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying backup cleanup task (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=300)
        
        return {'success': False, 'error': error_msg}


@shared_task(bind=True, max_retries=1)
def generate_backup_report(self, report_type: str = 'daily', email_recipients: List[str] = None):
    """
    Generate and optionally email backup status report.
    
    Args:
        report_type: Type of report (daily, weekly, monthly)
        email_recipients: List of email addresses to send report to
    
    Returns:
        Dict containing report generation results
    """
    logger.info(f"Starting backup report generation: {report_type}")
    
    try:
        # Get backup statistics
        stats = backup_manager.get_backup_statistics()
        
        # Get recent backup activity based on report type
        if report_type == 'daily':
            since_date = timezone.now() - timedelta(days=1)
        elif report_type == 'weekly':
            since_date = timezone.now() - timedelta(days=7)
        elif report_type == 'monthly':
            since_date = timezone.now() - timedelta(days=30)
        else:
            since_date = timezone.now() - timedelta(days=1)
        
        # Get recent backups
        recent_backups = BackupRecord.objects.filter(
            created_at__gte=since_date
        ).order_by('-created_at')
        
        # Get failed backups
        failed_backups = BackupRecord.objects.filter(
            created_at__gte=since_date,
            status='failed'
        ).order_by('-created_at')
        
        # Prepare report data
        report_data = {
            'report_type': report_type,
            'generated_at': timezone.now().isoformat(),
            'period_start': since_date.isoformat(),
            'statistics': stats,
            'recent_backups': [
                {
                    'backup_id': backup.backup_id,
                    'backup_type': backup.backup_type,
                    'status': backup.status,
                    'created_at': backup.created_at.isoformat(),
                    'file_size': backup.file_size,
                    'tenant_schema': backup.tenant_schema
                }
                for backup in recent_backups[:20]  # Limit to 20 most recent
            ],
            'failed_backups': [
                {
                    'backup_id': backup.backup_id,
                    'backup_type': backup.backup_type,
                    'error_message': backup.error_message,
                    'created_at': backup.created_at.isoformat(),
                    'tenant_schema': backup.tenant_schema
                }
                for backup in failed_backups[:10]  # Limit to 10 most recent failures
            ]
        }
        
        logger.info(f"Backup report generated successfully: {report_type}")
        
        # TODO: Implement email sending if recipients provided
        # This would require email configuration and templates
        
        return {
            'success': True,
            'report_type': report_type,
            'report_data': report_data,
            'message': f'{report_type.title()} backup report generated successfully'
        }
        
    except Exception as e:
        error_msg = f"Unexpected error in backup report generation: {str(e)}"
        logger.error(error_msg)
        
        return {'success': False, 'error': error_msg, 'report_type': report_type}


@shared_task(bind=True)
def process_scheduled_backups(self):
    """
    Process all scheduled backups that are due to run.
    This task should be run frequently (e.g., every minute) to check for due schedules.
    
    Returns:
        Dict containing processing results
    """
    logger.info("Processing scheduled backups")
    
    try:
        # Find all active schedules that are due to run
        now = timezone.now()
        due_schedules = BackupSchedule.objects.filter(
            is_active=True,
            next_run_at__lte=now
        )
        
        results = {
            'total_due': due_schedules.count(),
            'processed': 0,
            'errors': 0,
            'scheduled_tasks': []
        }
        
        for schedule in due_schedules:
            try:
                # Determine which backup task to run
                if schedule.schedule_type == 'full_system':
                    if schedule.frequency == 'daily':
                        task = create_daily_backup.apply_async(
                            args=[schedule.id, f'schedule_{schedule.name}']
                        )
                    elif schedule.frequency == 'weekly':
                        task = create_weekly_backup.apply_async(
                            args=[schedule.id, f'schedule_{schedule.name}']
                        )
                    else:
                        # Monthly or other frequencies use daily backup task
                        task = create_daily_backup.apply_async(
                            args=[schedule.id, f'schedule_{schedule.name}']
                        )
                
                elif schedule.schedule_type == 'tenant_only' and schedule.tenant_schema:
                    task = create_tenant_backup.apply_async(
                        args=[
                            schedule.tenant_schema,
                            None,  # tenant_domain
                            schedule.frequency,
                            f'schedule_{schedule.name}'
                        ]
                    )
                
                else:
                    logger.warning(f"Unknown schedule type or missing tenant schema: {schedule}")
                    continue
                
                results['scheduled_tasks'].append({
                    'schedule_id': schedule.id,
                    'schedule_name': schedule.name,
                    'task_id': task.id,
                    'schedule_type': schedule.schedule_type
                })
                
                results['processed'] += 1
                logger.info(f"Scheduled backup task for: {schedule.name}")
                
            except Exception as e:
                results['errors'] += 1
                error_msg = f"Error scheduling backup for {schedule.name}: {str(e)}"
                logger.error(error_msg)
        
        logger.info(f"Scheduled backup processing completed: {results['processed']} processed, "
                   f"{results['errors']} errors")
        
        return results
        
    except Exception as e:
        error_msg = f"Unexpected error in scheduled backup processing: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}


@shared_task(bind=True)
def backup_all_tenants(self, frequency: str = 'manual', created_by: str = 'celery_bulk'):
    """
    Create backups for all active tenants.
    
    Args:
        frequency: Backup frequency
        created_by: User or system that initiated the backup
    
    Returns:
        Dict containing bulk backup results
    """
    logger.info("Starting bulk tenant backup task")
    
    try:
        # Get all active tenants
        Tenant = get_tenant_model()
        tenants = Tenant.objects.filter(schema_name__isnull=False).exclude(schema_name='public')
        
        results = {
            'total_tenants': tenants.count(),
            'scheduled_backups': 0,
            'errors': 0,
            'backup_tasks': []
        }
        
        for tenant in tenants:
            try:
                # Schedule backup task for each tenant
                task = create_tenant_backup.apply_async(
                    args=[
                        tenant.schema_name,
                        getattr(tenant, 'domain_url', None),
                        frequency,
                        created_by
                    ]
                )
                
                results['backup_tasks'].append({
                    'tenant_schema': tenant.schema_name,
                    'task_id': task.id
                })
                
                results['scheduled_backups'] += 1
                logger.info(f"Scheduled backup for tenant: {tenant.schema_name}")
                
            except Exception as e:
                results['errors'] += 1
                error_msg = f"Error scheduling backup for tenant {tenant.schema_name}: {str(e)}"
                logger.error(error_msg)
        
        logger.info(f"Bulk tenant backup scheduling completed: {results['scheduled_backups']} scheduled, "
                   f"{results['errors']} errors")
        
        return results
        
    except Exception as e:
        error_msg = f"Unexpected error in bulk tenant backup task: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}