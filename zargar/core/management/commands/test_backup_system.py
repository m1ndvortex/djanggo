"""
Management command to test the backup system functionality.
Provides comprehensive testing of backup creation, encryption, and storage.
"""
import tempfile
import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import get_tenant_model
from zargar.core.backup_manager import backup_manager
from zargar.system.models import BackupRecord
from zargar.core.storage_utils import storage_manager


class Command(BaseCommand):
    help = 'Test the backup system functionality'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--test-type',
            choices=['connectivity', 'encryption', 'full-backup', 'tenant-backup', 'integrity', 'all'],
            default='all',
            help='Type of test to run',
        )
        
        parser.add_argument(
            '--tenant-schema',
            type=str,
            help='Tenant schema name for tenant backup test',
        )
        
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up test backups after testing',
        )
    
    def handle(self, *args, **options):
        """Run backup system tests."""
        test_type = options['test_type']
        tenant_schema = options['tenant_schema']
        cleanup = options['cleanup']
        
        self.stdout.write(
            self.style.SUCCESS('Starting backup system tests...\n')
        )
        
        test_results = {}
        
        if test_type in ['connectivity', 'all']:
            test_results['connectivity'] = self.test_storage_connectivity()
        
        if test_type in ['encryption', 'all']:
            test_results['encryption'] = self.test_encryption_functionality()
        
        if test_type in ['full-backup', 'all']:
            test_results['full_backup'] = self.test_full_system_backup(cleanup)
        
        if test_type in ['tenant-backup', 'all']:
            test_results['tenant_backup'] = self.test_tenant_backup(tenant_schema, cleanup)
        
        if test_type in ['integrity', 'all']:
            test_results['integrity'] = self.test_backup_integrity()
        
        # Summary
        self.print_test_summary(test_results)
    
    def test_storage_connectivity(self):
        """Test storage backend connectivity."""
        self.stdout.write('Testing storage connectivity...')
        
        try:
            connectivity_results = storage_manager.test_connectivity()
            
            for backend, result in connectivity_results.items():
                if result['connected']:
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ {backend}: Connected')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ {backend}: Failed - {result["error"]}')
                    )
            
            all_connected = all(result['connected'] for result in connectivity_results.values())
            
            if all_connected:
                self.stdout.write(
                    self.style.SUCCESS('Storage connectivity test: PASSED\n')
                )
                return {'status': 'PASSED', 'details': connectivity_results}
            else:
                self.stdout.write(
                    self.style.ERROR('Storage connectivity test: FAILED\n')
                )
                return {'status': 'FAILED', 'details': connectivity_results}
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Storage connectivity test: ERROR - {str(e)}\n')
            )
            return {'status': 'ERROR', 'error': str(e)}
    
    def test_encryption_functionality(self):
        """Test backup encryption and decryption."""
        self.stdout.write('Testing encryption functionality...')
        
        try:
            test_data = b"This is test data for encryption testing. It contains various characters: !@#$%^&*()_+"
            
            # Test encryption
            encrypted_data = backup_manager.fernet.encrypt(test_data)
            self.stdout.write('  ✓ Data encrypted successfully')
            
            # Test decryption
            decrypted_data = backup_manager.fernet.decrypt(encrypted_data)
            
            if decrypted_data == test_data:
                self.stdout.write('  ✓ Data decrypted successfully')
                self.stdout.write('  ✓ Decrypted data matches original')
                
                self.stdout.write(
                    self.style.SUCCESS('Encryption functionality test: PASSED\n')
                )
                return {'status': 'PASSED', 'original_size': len(test_data), 'encrypted_size': len(encrypted_data)}
            else:
                self.stdout.write(
                    self.style.ERROR('  ✗ Decrypted data does not match original')
                )
                return {'status': 'FAILED', 'error': 'Data integrity check failed'}
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Encryption functionality test: ERROR - {str(e)}\n')
            )
            return {'status': 'ERROR', 'error': str(e)}
    
    def test_full_system_backup(self, cleanup=False):
        """Test full system backup creation."""
        self.stdout.write('Testing full system backup...')
        
        try:
            # Create full system backup
            result = backup_manager.create_full_system_backup(
                frequency='manual',
                created_by='test_command'
            )
            
            if result['success']:
                backup_id = result['backup_id']
                self.stdout.write(f'  ✓ Backup created: {backup_id}')
                self.stdout.write(f'  ✓ File size: {result["file_size"]} bytes')
                self.stdout.write(f'  ✓ File hash: {result["file_hash"][:16]}...')
                
                # Verify backup record
                backup_record = BackupRecord.objects.get(backup_id=backup_id)
                self.stdout.write(f'  ✓ Backup record status: {backup_record.status}')
                self.stdout.write(f'  ✓ Storage redundancy: Primary={backup_record.stored_in_primary}, Secondary={backup_record.stored_in_secondary}')
                
                # Cleanup if requested
                if cleanup:
                    self.cleanup_test_backup(backup_id)
                
                self.stdout.write(
                    self.style.SUCCESS('Full system backup test: PASSED\n')
                )
                return {'status': 'PASSED', 'backup_id': backup_id, 'file_size': result['file_size']}
            else:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Backup failed: {result["error"]}')
                )
                return {'status': 'FAILED', 'error': result['error']}
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Full system backup test: ERROR - {str(e)}\n')
            )
            return {'status': 'ERROR', 'error': str(e)}
    
    def test_tenant_backup(self, tenant_schema=None, cleanup=False):
        """Test tenant-specific backup creation."""
        self.stdout.write('Testing tenant backup...')
        
        try:
            # Get a tenant schema if not provided
            if not tenant_schema:
                Tenant = get_tenant_model()
                tenant = Tenant.objects.exclude(schema_name='public').first()
                
                if not tenant:
                    self.stdout.write(
                        self.style.WARNING('  ! No tenants found, skipping tenant backup test')
                    )
                    return {'status': 'SKIPPED', 'reason': 'No tenants available'}
                
                tenant_schema = tenant.schema_name
                tenant_domain = getattr(tenant, 'domain_url', None)
            else:
                tenant_domain = None
            
            self.stdout.write(f'  Using tenant schema: {tenant_schema}')
            
            # Create tenant backup
            result = backup_manager.create_tenant_backup(
                tenant_schema=tenant_schema,
                tenant_domain=tenant_domain,
                frequency='manual',
                created_by='test_command'
            )
            
            if result['success']:
                backup_id = result['backup_id']
                self.stdout.write(f'  ✓ Tenant backup created: {backup_id}')
                self.stdout.write(f'  ✓ File size: {result["file_size"]} bytes')
                
                # Verify backup record
                backup_record = BackupRecord.objects.get(backup_id=backup_id)
                self.stdout.write(f'  ✓ Tenant schema: {backup_record.tenant_schema}')
                self.stdout.write(f'  ✓ Backup status: {backup_record.status}')
                
                # Cleanup if requested
                if cleanup:
                    self.cleanup_test_backup(backup_id)
                
                self.stdout.write(
                    self.style.SUCCESS('Tenant backup test: PASSED\n')
                )
                return {'status': 'PASSED', 'backup_id': backup_id, 'tenant_schema': tenant_schema}
            else:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Tenant backup failed: {result["error"]}')
                )
                return {'status': 'FAILED', 'error': result['error']}
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Tenant backup test: ERROR - {str(e)}\n')
            )
            return {'status': 'ERROR', 'error': str(e)}
    
    def test_backup_integrity(self):
        """Test backup integrity verification."""
        self.stdout.write('Testing backup integrity verification...')
        
        try:
            # Find a recent completed backup to test
            recent_backup = BackupRecord.objects.filter(
                status='completed'
            ).order_by('-created_at').first()
            
            if not recent_backup:
                self.stdout.write(
                    self.style.WARNING('  ! No completed backups found, creating test backup...')
                )
                
                # Create a test backup for integrity testing
                backup_result = backup_manager.create_full_system_backup(
                    frequency='manual',
                    created_by='integrity_test'
                )
                
                if not backup_result['success']:
                    return {'status': 'FAILED', 'error': 'Could not create test backup for integrity check'}
                
                recent_backup = BackupRecord.objects.get(backup_id=backup_result['backup_id'])
            
            backup_id = recent_backup.backup_id
            self.stdout.write(f'  Testing integrity of backup: {backup_id}')
            
            # Verify backup integrity
            integrity_result = backup_manager.verify_backup_integrity(backup_id)
            
            if integrity_result['success']:
                if integrity_result.get('integrity_passed', False):
                    self.stdout.write('  ✓ Backup integrity verification passed')
                    self.stdout.write(f'  ✓ File size verified: {integrity_result["file_size"]} bytes')
                    self.stdout.write(f'  ✓ Hash verification: {integrity_result["expected_hash"][:16]}...')
                    
                    self.stdout.write(
                        self.style.SUCCESS('Backup integrity test: PASSED\n')
                    )
                    return {'status': 'PASSED', 'backup_id': backup_id, 'file_size': integrity_result['file_size']}
                else:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Integrity verification failed: {integrity_result.get("error", "Unknown error")}')
                    )
                    return {'status': 'FAILED', 'error': integrity_result.get('error', 'Integrity check failed')}
            else:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Integrity verification error: {integrity_result["error"]}')
                )
                return {'status': 'FAILED', 'error': integrity_result['error']}
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Backup integrity test: ERROR - {str(e)}\n')
            )
            return {'status': 'ERROR', 'error': str(e)}
    
    def cleanup_test_backup(self, backup_id):
        """Clean up a test backup."""
        try:
            backup_record = BackupRecord.objects.get(backup_id=backup_id)
            
            # Delete from storage
            delete_result = storage_manager.delete_backup_file(
                backup_record.file_path,
                from_all_backends=True
            )
            
            if delete_result['success']:
                # Delete backup record
                backup_record.delete()
                self.stdout.write(f'  ✓ Cleaned up test backup: {backup_id}')
            else:
                self.stdout.write(
                    self.style.WARNING(f'  ! Failed to clean up backup {backup_id}: {delete_result.get("errors", [])}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'  ! Error cleaning up backup {backup_id}: {str(e)}')
            )
    
    def print_test_summary(self, test_results):
        """Print a summary of all test results."""
        self.stdout.write(
            self.style.SUCCESS('=' * 60)
        )
        self.stdout.write(
            self.style.SUCCESS('BACKUP SYSTEM TEST SUMMARY')
        )
        self.stdout.write(
            self.style.SUCCESS('=' * 60)
        )
        
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results.values() if result['status'] == 'PASSED')
        failed_tests = sum(1 for result in test_results.values() if result['status'] == 'FAILED')
        error_tests = sum(1 for result in test_results.values() if result['status'] == 'ERROR')
        skipped_tests = sum(1 for result in test_results.values() if result['status'] == 'SKIPPED')
        
        for test_name, result in test_results.items():
            status = result['status']
            if status == 'PASSED':
                self.stdout.write(
                    self.style.SUCCESS(f'{test_name.upper()}: {status}')
                )
            elif status == 'FAILED':
                self.stdout.write(
                    self.style.ERROR(f'{test_name.upper()}: {status} - {result.get("error", "Unknown error")}')
                )
            elif status == 'ERROR':
                self.stdout.write(
                    self.style.ERROR(f'{test_name.upper()}: {status} - {result.get("error", "Unknown error")}')
                )
            elif status == 'SKIPPED':
                self.stdout.write(
                    self.style.WARNING(f'{test_name.upper()}: {status} - {result.get("reason", "Unknown reason")}')
                )
        
        self.stdout.write(
            self.style.SUCCESS('=' * 60)
        )
        self.stdout.write(f'Total Tests: {total_tests}')
        self.stdout.write(
            self.style.SUCCESS(f'Passed: {passed_tests}')
        )
        if failed_tests > 0:
            self.stdout.write(
                self.style.ERROR(f'Failed: {failed_tests}')
            )
        if error_tests > 0:
            self.stdout.write(
                self.style.ERROR(f'Errors: {error_tests}')
            )
        if skipped_tests > 0:
            self.stdout.write(
                self.style.WARNING(f'Skipped: {skipped_tests}')
            )
        
        if passed_tests == total_tests:
            self.stdout.write(
                self.style.SUCCESS('\n🎉 All backup system tests PASSED! The backup system is ready for production use.')
            )
        elif passed_tests > 0:
            self.stdout.write(
                self.style.WARNING(f'\n⚠️  {passed_tests}/{total_tests} tests passed. Please review failed tests before using in production.')
            )
        else:
            self.stdout.write(
                self.style.ERROR('\n❌ All tests failed. The backup system requires attention before production use.')
            )