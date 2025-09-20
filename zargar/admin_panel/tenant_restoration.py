"""
Tenant Restoration Manager for ZARGAR Admin Panel.

This module provides utilities for creating snapshots before high-risk operations
and restoring individual tenants from backups while ensuring complete isolation
from other tenants.

Requirements: 5.15, 5.16, 5.17, 5.18
"""
import logging
from datetime import timedelta
from typing import Dict, Any, Optional, List
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from zargar.tenants.models import Tenant
from .models import TenantSnapshot, BackupJob, RestoreJob
from .tasks import create_tenant_snapshot, restore_tenant_from_backup

logger = logging.getLogger(__name__)


class TenantRestorationManager:
    """
    Manager class for tenant restoration operations.
    
    Provides high-level interface for:
    - Creating pre-operation snapshots
    - Restoring tenants from backups
    - Managing snapshot lifecycle
    - Ensuring tenant isolation during operations
    """
    
    def __init__(self):
        self.logger = logger
    
    def create_pre_operation_snapshot(self, tenant_schema: str, operation_description: str,
                                    created_by_id: Optional[int] = None, 
                                    created_by_username: str = 'system') -> Dict[str, Any]:
        """
        Create a temporary snapshot before high-risk tenant operations.
        
        Args:
            tenant_schema: Schema name of the tenant to snapshot
            operation_description: Description of the operation requiring snapshot
            created_by_id: ID of user creating snapshot
            created_by_username: Username of user creating snapshot
            
        Returns:
            dict: Result with success status, snapshot_id, or error
        """
        try:
            self.logger.info(f"Creating pre-operation snapshot for tenant: {tenant_schema}")
            
            # Validate tenant exists
            if not self._validate_tenant_exists(tenant_schema):
                return {
                    'success': False,
                    'error': f'Tenant schema "{tenant_schema}" does not exist'
                }
            
            # Check for existing recent snapshots to avoid duplicates
            recent_snapshots = TenantSnapshot.objects.filter(
                tenant_schema=tenant_schema,
                snapshot_type='pre_operation',
                created_at__gte=timezone.now() - timedelta(hours=1),
                status__in=['pending', 'creating', 'completed']
            )
            
            if recent_snapshots.exists():
                recent_snapshot = recent_snapshots.first()
                self.logger.info(f"Recent snapshot exists for {tenant_schema}: {recent_snapshot.snapshot_id}")
                return {
                    'success': True,
                    'snapshot_id': str(recent_snapshot.snapshot_id),
                    'existing': True,
                    'message': 'Using existing recent snapshot'
                }
            
            # Create snapshot asynchronously
            task_result = create_tenant_snapshot.apply_async(
                args=[tenant_schema, operation_description, created_by_id, created_by_username]
            )
            
            # Wait for task completion (with timeout)
            try:
                result = task_result.get(timeout=1800)  # 30 minutes timeout
                
                if result['success']:
                    self.logger.info(f"Pre-operation snapshot created successfully: {result['snapshot_id']}")
                    return {
                        'success': True,
                        'snapshot_id': result['snapshot_id'],
                        'backup_id': result['backup_id'],
                        'file_size': result['file_size'],
                        'tenant_schema': tenant_schema,
                        'message': 'Pre-operation snapshot created successfully'
                    }
                else:
                    self.logger.error(f"Pre-operation snapshot failed: {result['error']}")
                    return {
                        'success': False,
                        'error': result['error'],
                        'tenant_schema': tenant_schema
                    }
                    
            except Exception as e:
                self.logger.error(f"Snapshot task failed or timed out: {str(e)}")
                return {
                    'success': False,
                    'error': f'Snapshot creation failed or timed out: {str(e)}',
                    'tenant_schema': tenant_schema
                }
                
        except Exception as e:
            self.logger.error(f"Error creating pre-operation snapshot: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'tenant_schema': tenant_schema
            }
    
    def restore_tenant_from_main_backup(self, backup_id: str, target_tenant_schema: str,
                                      confirmation_text: str, created_by_id: int,
                                      created_by_username: str) -> Dict[str, Any]:
        """
        Restore a single tenant from a main backup using selective restoration.
        
        Args:
            backup_id: ID of the backup to restore from
            target_tenant_schema: Schema name of the tenant to restore
            confirmation_text: Confirmation text typed by user
            created_by_id: ID of user performing restoration
            created_by_username: Username of user performing restoration
            
        Returns:
            dict: Result with success status, restore_job_id, or error
        """
        try:
            self.logger.info(f"Starting tenant restoration: {target_tenant_schema} from backup {backup_id}")
            
            # Validate inputs
            validation_result = self._validate_restoration_request(
                backup_id, target_tenant_schema, confirmation_text
            )
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error']
                }
            
            backup_job = validation_result['backup_job']
            tenant = validation_result['tenant']
            
            # Create restore job
            with transaction.atomic():
                restore_job = RestoreJob.objects.create(
                    restore_type='single_tenant',
                    source_backup=backup_job,
                    target_tenant_schema=target_tenant_schema,
                    confirmed_by_typing=confirmation_text,
                    created_by_id=created_by_id,
                    created_by_username=created_by_username,
                    status='pending'
                )
                
                self.logger.info(f"Created restore job: {restore_job.job_id}")
            
            # Start restoration asynchronously
            task_result = restore_tenant_from_backup.apply_async(
                args=[str(restore_job.job_id)]
            )
            
            return {
                'success': True,
                'restore_job_id': str(restore_job.job_id),
                'task_id': task_result.id,
                'target_tenant_schema': target_tenant_schema,
                'source_backup_id': backup_id,
                'message': f'Tenant restoration started for {target_tenant_schema}'
            }
            
        except Exception as e:
            self.logger.error(f"Error starting tenant restoration: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def restore_tenant_from_snapshot(self, snapshot_id: str, created_by_id: int,
                                   created_by_username: str) -> Dict[str, Any]:
        """
        Restore a tenant from a specific snapshot.
        
        Args:
            snapshot_id: ID of the snapshot to restore from
            created_by_id: ID of user performing restoration
            created_by_username: Username of user performing restoration
            
        Returns:
            dict: Result with success status, restore_job_id, or error
        """
        try:
            self.logger.info(f"Starting tenant restoration from snapshot: {snapshot_id}")
            
            # Get and validate snapshot
            try:
                snapshot = TenantSnapshot.objects.get(snapshot_id=snapshot_id)
            except TenantSnapshot.DoesNotExist:
                return {
                    'success': False,
                    'error': f'Snapshot {snapshot_id} not found'
                }
            
            if not snapshot.is_available_for_restore:
                return {
                    'success': False,
                    'error': f'Snapshot {snapshot_id} is not available for restoration (status: {snapshot.status})'
                }
            
            if not snapshot.backup_job:
                return {
                    'success': False,
                    'error': f'Snapshot {snapshot_id} has no associated backup job'
                }
            
            # Create restore job
            with transaction.atomic():
                restore_job = RestoreJob.objects.create(
                    restore_type='snapshot_restore',
                    source_backup=snapshot.backup_job,
                    target_tenant_schema=snapshot.tenant_schema,
                    confirmed_by_typing=f'snapshot_{snapshot_id}',
                    created_by_id=created_by_id,
                    created_by_username=created_by_username,
                    status='pending'
                )
                
                self.logger.info(f"Created snapshot restore job: {restore_job.job_id}")
            
            # Start restoration asynchronously
            task_result = restore_tenant_from_backup.apply_async(
                args=[str(restore_job.job_id)]
            )
            
            return {
                'success': True,
                'restore_job_id': str(restore_job.job_id),
                'task_id': task_result.id,
                'target_tenant_schema': snapshot.tenant_schema,
                'snapshot_id': snapshot_id,
                'message': f'Tenant restoration from snapshot started for {snapshot.tenant_schema}'
            }
            
        except Exception as e:
            self.logger.error(f"Error starting snapshot restoration: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_available_snapshots(self, tenant_schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of available snapshots for restoration.
        
        Args:
            tenant_schema: Optional filter by tenant schema
            
        Returns:
            list: List of available snapshots with metadata
        """
        try:
            queryset = TenantSnapshot.objects.filter(
                status='completed',
                expires_at__gt=timezone.now()
            ).order_by('-created_at')
            
            if tenant_schema:
                queryset = queryset.filter(tenant_schema=tenant_schema)
            
            snapshots = []
            for snapshot in queryset[:50]:  # Limit to 50 most recent
                snapshots.append({
                    'snapshot_id': str(snapshot.snapshot_id),
                    'name': snapshot.name,
                    'tenant_schema': snapshot.tenant_schema,
                    'tenant_domain': snapshot.tenant_domain,
                    'operation_description': snapshot.operation_description,
                    'created_at': snapshot.created_at.isoformat(),
                    'expires_at': snapshot.expires_at.isoformat(),
                    'file_size': snapshot.file_size_human,
                    'created_by': snapshot.created_by_username,
                    'is_restored': snapshot.restored_at is not None
                })
            
            return snapshots
            
        except Exception as e:
            self.logger.error(f"Error getting available snapshots: {str(e)}")
            return []
    
    def get_restoration_status(self, restore_job_id: str) -> Dict[str, Any]:
        """
        Get status of a restoration job.
        
        Args:
            restore_job_id: ID of the restore job
            
        Returns:
            dict: Restoration status and progress information
        """
        try:
            restore_job = RestoreJob.objects.get(job_id=restore_job_id)
            
            return {
                'success': True,
                'restore_job_id': str(restore_job.job_id),
                'status': restore_job.status,
                'progress_percentage': restore_job.progress_percentage,
                'started_at': restore_job.started_at.isoformat() if restore_job.started_at else None,
                'completed_at': restore_job.completed_at.isoformat() if restore_job.completed_at else None,
                'duration': str(restore_job.duration) if restore_job.duration else None,
                'target_tenant_schema': restore_job.target_tenant_schema,
                'restore_type': restore_job.restore_type,
                'error_message': restore_job.error_message,
                'log_messages': restore_job.log_messages[-10:] if restore_job.log_messages else []  # Last 10 messages
            }
            
        except RestoreJob.DoesNotExist:
            return {
                'success': False,
                'error': f'Restore job {restore_job_id} not found'
            }
        except Exception as e:
            self.logger.error(f"Error getting restoration status: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_old_snapshots(self, tenant_schema: Optional[str] = None) -> Dict[str, Any]:
        """
        Clean up old snapshots for a tenant or all tenants.
        
        Args:
            tenant_schema: Optional filter by tenant schema
            
        Returns:
            dict: Cleanup results
        """
        try:
            from .tasks import cleanup_expired_snapshots
            
            # For now, we'll use the general cleanup task
            # In the future, we could create a tenant-specific cleanup
            task_result = cleanup_expired_snapshots.apply_async()
            
            return {
                'success': True,
                'task_id': task_result.id,
                'message': 'Snapshot cleanup task started'
            }
            
        except Exception as e:
            self.logger.error(f"Error starting snapshot cleanup: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _validate_tenant_exists(self, tenant_schema: str) -> bool:
        """
        Validate that a tenant schema exists.
        
        Args:
            tenant_schema: Schema name to validate
            
        Returns:
            bool: True if tenant exists
        """
        try:
            Tenant.objects.get(schema_name=tenant_schema)
            return True
        except Tenant.DoesNotExist:
            return False
    
    def _validate_restoration_request(self, backup_id: str, target_tenant_schema: str,
                                    confirmation_text: str) -> Dict[str, Any]:
        """
        Validate a restoration request.
        
        Args:
            backup_id: ID of the backup to restore from
            target_tenant_schema: Schema name of the tenant to restore
            confirmation_text: Confirmation text typed by user
            
        Returns:
            dict: Validation result with backup_job and tenant if valid
        """
        try:
            # Validate backup exists and is completed
            try:
                backup_job = BackupJob.objects.get(job_id=backup_id)
            except BackupJob.DoesNotExist:
                return {
                    'valid': False,
                    'error': f'Backup {backup_id} not found'
                }
            
            if backup_job.status != 'completed':
                return {
                    'valid': False,
                    'error': f'Backup {backup_id} is not completed (status: {backup_job.status})'
                }
            
            # Validate target tenant exists
            try:
                tenant = Tenant.objects.get(schema_name=target_tenant_schema)
            except Tenant.DoesNotExist:
                return {
                    'valid': False,
                    'error': f'Target tenant schema "{target_tenant_schema}" does not exist'
                }
            
            # Validate confirmation text
            expected_confirmation = tenant.domain_url
            if confirmation_text != expected_confirmation:
                return {
                    'valid': False,
                    'error': f'Confirmation text does not match. Expected: "{expected_confirmation}"'
                }
            
            return {
                'valid': True,
                'backup_job': backup_job,
                'tenant': tenant
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Validation error: {str(e)}'
            }


# Global instance
tenant_restoration_manager = TenantRestorationManager()