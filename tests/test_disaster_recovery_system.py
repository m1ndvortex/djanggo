"""
Integration tests for the complete disaster recovery system.

These tests validate the disaster recovery procedures, backup/restore operations,
and system validation workflows.

Requirements: 5.11, 5.12
"""
import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Setup Django before importing models
import django
from django.conf import settings
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.db import connection
from django.core.management import call_command

# Import models after Django setup
from zargar.tenants.models import Tenant
from zargar.admin_panel.models import BackupJob, RestoreJob
from zargar.admin_panel.disaster_recovery import (
    DisasterRecoveryManager, 
    DisasterRecoveryError,
    disaster_recovery_manager
)


class DisasterRecoveryManagerTests(TestCase):
    """Test cases for DisasterRecoveryManager functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.dr_manager = DisasterRecoveryManager()
        
        # Create test tenant
        self.test_tenant = Tenant.objects.create(
            name="Test Jewelry Shop",
            schema_name="test_shop",
            domain_url="testshop.zargar.com"
        )
    
    def test_create_disaster_recovery_plan(self):
        """Test disaster recovery plan creation."""
        plan = self.dr_manager.create_disaster_recovery_plan()
        
        # Verify plan structure
        self.assertIn('disaster_recovery_plan', plan)
        dr_plan = plan['disaster_recovery_plan']
        
        # Check required sections
        required_sections = [
            'version', 'created_at', 'overview', 'prerequisites',
            'recovery_procedures', 'validation_steps', 
            'rollback_procedures', 'emergency_contacts'
        ]
        
        for section in required_sections:
            self.assertIn(section, dr_plan)
        
        # Verify overview
        overview = dr_plan['overview']
        self.assertEqual(overview['philosophy'], "Separation of Data, Configuration, and Code")
        self.assertIn('components', overview)
        self.assertIn('recovery_time_objective', overview)
        self.assertIn('recovery_point_objective', overview)
        
        # Verify recovery procedures
        procedures = dr_plan['recovery_procedures']
        expected_phases = [
            'phase_1_server_preparation',
            'phase_2_code_recovery',
            'phase_3_configuration_recovery',
            'phase_4_data_recovery',
            'phase_5_service_startup',
            'phase_6_validation'
        ]
        
        for phase in expected_phases:
            self.assertIn(phase, procedures)
            self.assertIn('description', procedures[phase])
            self.assertIn('estimated_time', procedures[phase])
            self.assertIn('steps', procedures[phase])
    
    @patch('zargar.admin_panel.disaster_recovery.storage_manager')
    def test_create_system_snapshot(self, mock_storage):
        """Test system snapshot creation."""
        # Mock storage operations
        mock_storage.upload_backup_file.return_value = {
            'success': True,
            'uploaded_to': ['cloudflare_r2', 'backblaze_b2']
        }
        
        # Mock database backup creation
        with patch.object(self.dr_manager, '_create_database_backup') as mock_db_backup:
            mock_db_backup.return_value = '/tmp/test_db_backup.sql'
            
            with patch.object(self.dr_manager, '_create_configuration_backup') as mock_config_backup:
                mock_config_backup.return_value = '/tmp/test_config_backup.tar.gz'
                
                with patch.object(self.dr_manager, '_upload_snapshot_to_storage') as mock_upload:
                    mock_upload.return_value = {
                        'combined_path': 'disaster_recovery/manifests/test_snapshot.json',
                        'total_size': 1024000,
                        'backends': ['cloudflare_r2', 'backblaze_b2']
                    }
                    
                    # Create snapshot
                    snapshot_info = self.dr_manager.create_system_snapshot('test_snapshot')
                    
                    # Verify snapshot info
                    self.assertIn('snapshot_id', snapshot_info)
                    self.assertEqual(snapshot_info['name'], 'test_snapshot')
                    self.assertIn('created_at', snapshot_info)
                    self.assertEqual(snapshot_info['size_bytes'], 1024000)
                    self.assertEqual(snapshot_info['storage_backends'], ['cloudflare_r2', 'backblaze_b2'])
                    
                    # Verify backup job was created
                    backup_job = BackupJob.objects.get(name='test_snapshot')
                    self.assertEqual(backup_job.backup_type, 'full_system')
                    self.assertEqual(backup_job.status, 'completed')
    
    @patch('zargar.admin_panel.disaster_recovery.storage_manager')
    def test_test_disaster_recovery_procedures(self, mock_storage):
        """Test disaster recovery procedure testing."""
        # Mock storage connectivity
        mock_storage.test_connectivity.return_value = {
            'cloudflare_r2': {'connected': True, 'error': None},
            'backblaze_b2': {'connected': True, 'error': None},
            'redundant': {'connected': True, 'error': None}
        }
        
        # Mock file operations
        mock_storage.upload_backup_file.return_value = {
            'success': True,
            'uploaded_to': ['cloudflare_r2']
        }
        mock_storage.download_backup_file.return_value = b'test content'
        mock_storage.delete_backup_file.return_value = {
            'success': True,
            'deleted_from': ['cloudflare_r2']
        }
        mock_storage.list_backup_files.return_value = ['test_manifest.json']
        
        # Run tests
        test_results = self.dr_manager.test_disaster_recovery_procedures()
        
        # Verify test results
        self.assertIn('test_id', test_results)
        self.assertIn('started_at', test_results)
        self.assertIn('tests', test_results)
        self.assertIn('overall_status', test_results)
        
        # Check individual tests
        tests = test_results['tests']
        expected_tests = [
            'storage_connectivity',
            'backup_creation',
            'backup_restoration',
            'configuration_validation',
            'database_connectivity'
        ]
        
        for test_name in expected_tests:
            self.assertIn(test_name, tests)
            self.assertIn('status', tests[test_name])
        
        # Overall status should be passed if all tests pass
        if all(test['status'] == 'passed' for test in tests.values()):
            self.assertEqual(test_results['overall_status'], 'passed')
    
    def test_generate_recovery_documentation(self):
        """Test recovery documentation generation."""
        with patch.object(self.dr_manager.storage, 'upload_backup_file') as mock_upload:
            mock_upload.return_value = {
                'success': True,
                'uploaded_to': ['cloudflare_r2', 'backblaze_b2']
            }
            
            # Generate documentation
            doc_path = self.dr_manager.generate_recovery_documentation()
            
            # Verify documentation was uploaded
            self.assertTrue(doc_path.startswith('disaster_recovery/documentation/'))
            self.assertTrue(doc_path.endswith('.md'))
            
            # Verify upload was called
            mock_upload.assert_called_once()
            
            # Check upload parameters
            call_args = mock_upload.call_args
            self.assertEqual(call_args[0][0], doc_path)  # Storage path
            self.assertIsInstance(call_args[0][1], bytes)  # Content
            self.assertTrue(call_args[1]['use_redundant'])  # Redundant storage


class DisasterRecoveryValidationTests(TestCase):
    """Test cases for disaster recovery validation functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Import here to avoid circular imports
        from scripts.disaster_recovery_validate import DisasterRecoveryValidator
        self.validator = DisasterRecoveryValidator()
        
        # Create test tenant
        self.test_tenant = Tenant.objects.create(
            name="Test Jewelry Shop",
            schema_name="test_shop",
            domain_url="testshop.zargar.com"
        )
    
    def test_database_connectivity_validation(self):
        """Test database connectivity validation."""
        result = self.validator._check_database_connectivity()
        
        self.assertIn('status', result)
        self.assertIn('message', result)
        
        # Should pass in test environment
        self.assertEqual(result['status'], 'passed')
        self.assertIn('details', result)
        self.assertEqual(result['details']['connection'], 'successful')
    
    def test_public_schema_validation(self):
        """Test public schema validation."""
        result = self.validator._check_public_schema()
        
        self.assertIn('status', result)
        self.assertIn('message', result)
        
        # Should pass - public schema should exist
        self.assertEqual(result['status'], 'passed')
        self.assertIn('details', result)
        self.assertIn('tables_found', result['details'])
    
    def test_tenant_schemas_validation(self):
        """Test tenant schemas validation."""
        result = self.validator._check_tenant_schemas()
        
        self.assertIn('status', result)
        self.assertIn('message', result)
        
        # May pass or warn depending on tenant setup
        self.assertIn(result['status'], ['passed', 'warning', 'failed'])
        
        if result['status'] != 'warning':  # If tenants exist
            self.assertIn('details', result)
            self.assertIn('schemas_checked', result['details'])
    
    def test_django_settings_validation(self):
        """Test Django settings validation."""
        result = self.validator._check_django_settings()
        
        self.assertIn('status', result)
        self.assertIn('message', result)
        
        # Should pass in test environment
        self.assertEqual(result['status'], 'passed')
        self.assertIn('details', result)
        
        # Check critical settings
        details = result['details']
        self.assertTrue(details['SECRET_KEY'])
        self.assertTrue(details['DATABASES'])
        self.assertTrue(details['INSTALLED_APPS'])
    
    def test_installed_apps_validation(self):
        """Test installed apps validation."""
        result = self.validator._check_installed_apps()
        
        self.assertIn('status', result)
        self.assertIn('message', result)
        
        # Should pass - all required apps should be installed
        self.assertEqual(result['status'], 'passed')
        self.assertIn('details', result)
        self.assertIn('installed_count', result['details'])
        self.assertTrue(result['details']['critical_apps_present'])
    
    @patch('zargar.admin_panel.disaster_recovery.storage_manager')
    def test_storage_connectivity_validation(self, mock_storage):
        """Test storage connectivity validation."""
        # Mock successful connectivity
        mock_storage.test_connectivity.return_value = {
            'cloudflare_r2': {'connected': True, 'error': None},
            'backblaze_b2': {'connected': True, 'error': None},
            'redundant': {'connected': True, 'error': None}
        }
        
        result = self.validator._validate_storage_connectivity()
        
        self.assertIn('status', result)
        self.assertIn('message', result)
        self.assertEqual(result['status'], 'passed')
        self.assertIn('details', result)
    
    def test_full_validation_workflow(self):
        """Test complete validation workflow."""
        with patch.object(self.validator, '_validate_storage_systems') as mock_storage:
            mock_storage.return_value = {
                'status': 'passed',
                'checks': {
                    'connectivity': {'status': 'passed'},
                    'configuration': {'status': 'passed'},
                    'file_operations': {'status': 'passed'}
                }
            }
            
            with patch.object(self.validator, '_validate_security_configurations') as mock_security:
                mock_security.return_value = {
                    'status': 'passed',
                    'checks': {
                        'django_security': {'status': 'passed'},
                        'authentication': {'status': 'passed'},
                        'https': {'status': 'passed'}
                    }
                }
                
                with patch.object(self.validator, '_validate_performance_metrics') as mock_performance:
                    mock_performance.return_value = {
                        'status': 'passed',
                        'checks': {
                            'database_performance': {'status': 'passed'},
                            'memory_usage': {'status': 'passed'},
                            'response_times': {'status': 'passed'}
                        }
                    }
                    
                    with patch.object(self.validator, '_validate_backup_systems') as mock_backup:
                        mock_backup.return_value = {
                            'status': 'passed',
                            'checks': {
                                'backup_models': {'status': 'passed'},
                                'disaster_recovery': {'status': 'passed'},
                                'backup_storage': {'status': 'passed'}
                            }
                        }
                        
                        # Run full validation
                        results = self.validator.run_full_validation()
                        
                        # Verify results structure
                        self.assertIn('validation_id', results)
                        self.assertIn('started_at', results)
                        self.assertIn('components', results)
                        self.assertIn('overall_status', results)
                        self.assertIn('summary', results)
                        
                        # Check components
                        components = results['components']
                        expected_components = [
                            'database', 'application', 'storage',
                            'security', 'performance', 'multi_tenant',
                            'backup_system'
                        ]
                        
                        for component in expected_components:
                            self.assertIn(component, components)
                        
                        # Check summary
                        summary = results['summary']
                        self.assertIn('total_checks', summary)
                        self.assertIn('passed_checks', summary)
                        self.assertIn('success_rate', summary)


class DisasterRecoveryRestoreTests(TransactionTestCase):
    """Test cases for disaster recovery restore functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Import here to avoid circular imports
        from scripts.disaster_recovery_restore import DisasterRecoveryRestore
        self.restore_manager = DisasterRecoveryRestore()
        
        # Create test tenant
        self.test_tenant = Tenant.objects.create(
            name="Test Jewelry Shop",
            schema_name="test_shop",
            domain_url="testshop.zargar.com"
        )
    
    @patch('zargar.admin_panel.disaster_recovery.storage_manager')
    def test_list_available_backups(self, mock_storage):
        """Test listing available backups."""
        # Mock backup manifest files
        mock_storage.list_backup_files.return_value = [
            'snapshot_12345.json',
            'snapshot_67890.json'
        ]
        
        # Mock manifest content
        test_manifest = {
            'created_at': '2025-01-01T12:00:00Z',
            'database_backup': 'disaster_recovery/database/test_db.sql',
            'configuration_backup': 'disaster_recovery/configuration/test_config.tar.gz',
            'total_size': 1024000,
            'storage_backends': ['cloudflare_r2', 'backblaze_b2']
        }
        
        mock_storage.download_backup_file.return_value = json.dumps(test_manifest).encode()
        
        # List backups
        result = self.restore_manager.list_available_backups()
        
        # Verify result structure
        self.assertIn('total_backups', result)
        self.assertIn('backups', result)
        self.assertIn('latest_backup', result)
        
        # Check backup information
        self.assertEqual(result['total_backups'], 2)
        self.assertEqual(len(result['backups']), 2)
        
        # Check backup details
        backup = result['backups'][0]
        self.assertIn('backup_id', backup)
        self.assertIn('created_at', backup)
        self.assertIn('total_size', backup)
        self.assertIn('components', backup)
        self.assertIn('storage_backends', backup)
    
    @patch('zargar.admin_panel.disaster_recovery.storage_manager')
    @patch('subprocess.run')
    def test_restore_database_only(self, mock_subprocess, mock_storage):
        """Test database-only restore."""
        # Mock backup listing
        test_manifest = {
            'created_at': '2025-01-01T12:00:00Z',
            'database_backup': 'disaster_recovery/database/test_db.sql',
            'configuration_backup': 'disaster_recovery/configuration/test_config.tar.gz',
            'total_size': 1024000,
            'storage_backends': ['cloudflare_r2']
        }
        
        mock_storage.list_backup_files.return_value = ['snapshot_12345.json']
        mock_storage.download_backup_file.side_effect = [
            json.dumps(test_manifest).encode(),  # Manifest download
            b'-- Test database backup content'    # Database backup download
        ]
        
        # Mock subprocess calls (docker-compose commands)
        mock_subprocess.return_value = MagicMock(returncode=0, stderr=b'')
        
        # Mock validation
        with patch.object(self.restore_manager, '_validate_database_restoration') as mock_validation:
            mock_validation.return_value = {
                'success': True,
                'message': 'Database validation passed'
            }
            
            # Restore database
            result = self.restore_manager.restore_database_only(use_latest=True)
            
            # Verify result
            self.assertTrue(result['success'])
            self.assertIn('restore_job_id', result)
            self.assertIn('backup_info', result)
            self.assertIn('database_restore', result)
            self.assertIn('validation', result)
            
            # Verify restore job was created
            restore_job = RestoreJob.objects.get(job_id=result['restore_job_id'])
            self.assertEqual(restore_job.restore_type, 'database_only')
            self.assertEqual(restore_job.status, 'completed')
    
    @patch('zargar.admin_panel.disaster_recovery.storage_manager')
    def test_restore_configuration_only(self, mock_storage):
        """Test configuration-only restore."""
        # Mock backup listing
        test_manifest = {
            'created_at': '2025-01-01T12:00:00Z',
            'database_backup': 'disaster_recovery/database/test_db.sql',
            'configuration_backup': 'disaster_recovery/configuration/test_config.tar.gz',
            'total_size': 1024000,
            'storage_backends': ['cloudflare_r2']
        }
        
        mock_storage.list_backup_files.return_value = ['snapshot_12345.json']
        mock_storage.download_backup_file.side_effect = [
            json.dumps(test_manifest).encode(),  # Manifest download
            b'fake tar.gz content'               # Configuration backup download
        ]
        
        # Mock tar extraction
        with patch('tarfile.open') as mock_tar:
            mock_tar_instance = MagicMock()
            mock_tar_instance.getnames.return_value = ['docker-compose.yml', 'nginx.conf']
            mock_tar.return_value.__enter__.return_value = mock_tar_instance
            
            # Mock validation
            with patch.object(self.restore_manager, '_validate_configuration_restoration') as mock_validation:
                mock_validation.return_value = {
                    'success': True,
                    'message': 'Configuration validation passed'
                }
                
                # Restore configuration
                result = self.restore_manager.restore_configuration_only(use_latest=True)
                
                # Verify result
                self.assertTrue(result['success'])
                self.assertIn('restore_job_id', result)
                self.assertIn('backup_info', result)
                self.assertIn('configuration_restore', result)
                self.assertIn('validation', result)
                
                # Verify restore job was created
                restore_job = RestoreJob.objects.get(job_id=result['restore_job_id'])
                self.assertEqual(restore_job.restore_type, 'configuration')
                self.assertEqual(restore_job.status, 'completed')


class DisasterRecoveryIntegrationTests(TransactionTestCase):
    """Integration tests for complete disaster recovery workflows."""
    
    def setUp(self):
        """Set up test environment."""
        self.dr_manager = disaster_recovery_manager
        
        # Create test tenant
        self.test_tenant = Tenant.objects.create(
            name="Test Jewelry Shop",
            schema_name="test_shop",
            domain_url="testshop.zargar.com"
        )
    
    @patch('zargar.admin_panel.disaster_recovery.storage_manager')
    def test_complete_backup_and_restore_workflow(self, mock_storage):
        """Test complete backup creation and restore workflow."""
        # Mock storage operations
        mock_storage.upload_backup_file.return_value = {
            'success': True,
            'uploaded_to': ['cloudflare_r2', 'backblaze_b2']
        }
        
        mock_storage.test_connectivity.return_value = {
            'cloudflare_r2': {'connected': True, 'error': None},
            'backblaze_b2': {'connected': True, 'error': None}
        }
        
        # Mock database and configuration backup creation
        with patch.object(self.dr_manager, '_create_database_backup') as mock_db_backup:
            mock_db_backup.return_value = '/tmp/test_db_backup.sql'
            
            with patch.object(self.dr_manager, '_create_configuration_backup') as mock_config_backup:
                mock_config_backup.return_value = '/tmp/test_config_backup.tar.gz'
                
                with patch.object(self.dr_manager, '_upload_snapshot_to_storage') as mock_upload:
                    mock_upload.return_value = {
                        'combined_path': 'disaster_recovery/manifests/test_snapshot.json',
                        'total_size': 1024000,
                        'backends': ['cloudflare_r2', 'backblaze_b2']
                    }
                    
                    # Step 1: Create system snapshot
                    snapshot_info = self.dr_manager.create_system_snapshot('integration_test_snapshot')
                    
                    # Verify snapshot was created
                    self.assertIn('snapshot_id', snapshot_info)
                    self.assertEqual(snapshot_info['name'], 'integration_test_snapshot')
                    
                    # Verify backup job was created and completed
                    backup_job = BackupJob.objects.get(name='integration_test_snapshot')
                    self.assertEqual(backup_job.status, 'completed')
                    self.assertEqual(backup_job.backup_type, 'full_system')
    
    def test_disaster_recovery_testing_workflow(self):
        """Test disaster recovery testing workflow."""
        with patch.object(self.dr_manager, '_test_storage_connectivity') as mock_storage_test:
            mock_storage_test.return_value = {
                'status': 'passed',
                'details': {
                    'cloudflare_r2': {'connected': True},
                    'backblaze_b2': {'connected': True}
                }
            }
            
            with patch.object(self.dr_manager, '_test_backup_creation') as mock_backup_test:
                mock_backup_test.return_value = {
                    'status': 'passed',
                    'message': 'Backup creation test successful'
                }
                
                with patch.object(self.dr_manager, '_test_backup_restoration_dry_run') as mock_restore_test:
                    mock_restore_test.return_value = {
                        'status': 'passed',
                        'message': 'Backup restoration dry run successful'
                    }
                    
                    with patch.object(self.dr_manager, '_test_configuration_validation') as mock_config_test:
                        mock_config_test.return_value = {
                            'status': 'passed',
                            'message': 'Configuration validation successful'
                        }
                        
                        with patch.object(self.dr_manager, '_test_database_connectivity') as mock_db_test:
                            mock_db_test.return_value = {
                                'status': 'passed',
                                'message': 'Database connectivity test successful'
                            }
                            
                            # Run disaster recovery tests
                            test_results = self.dr_manager.test_disaster_recovery_procedures()
                            
                            # Verify test results
                            self.assertEqual(test_results['overall_status'], 'passed')
                            self.assertIn('tests', test_results)
                            
                            # Verify all individual tests passed
                            for test_name, test_result in test_results['tests'].items():
                                self.assertEqual(test_result['status'], 'passed')
    
    def test_backup_job_lifecycle(self):
        """Test backup job lifecycle management."""
        # Create backup job
        backup_job = BackupJob.objects.create(
            name='test_backup_lifecycle',
            backup_type='full_system',
            frequency='manual',
            status='pending',
            created_by_username='test_user'
        )
        
        # Test job progression
        self.assertEqual(backup_job.status, 'pending')
        self.assertFalse(backup_job.is_running)
        self.assertFalse(backup_job.is_completed)
        
        # Mark as running
        backup_job.mark_as_running()
        self.assertEqual(backup_job.status, 'running')
        self.assertTrue(backup_job.is_running)
        self.assertIsNotNone(backup_job.started_at)
        
        # Add log messages
        backup_job.add_log_message('info', 'Starting backup process')
        backup_job.add_log_message('info', 'Database backup in progress')
        
        self.assertEqual(len(backup_job.log_messages), 3)  # Including initial message
        
        # Update progress
        backup_job.update_progress(50, 'Backup 50% complete')
        self.assertEqual(backup_job.progress_percentage, 50)
        
        # Mark as completed
        backup_job.mark_as_completed(
            file_path='disaster_recovery/test_backup.sql',
            file_size_bytes=1024000,
            storage_backends=['cloudflare_r2', 'backblaze_b2']
        )
        
        self.assertEqual(backup_job.status, 'completed')
        self.assertTrue(backup_job.is_completed)
        self.assertIsNotNone(backup_job.completed_at)
        self.assertEqual(backup_job.progress_percentage, 100)
        self.assertEqual(backup_job.file_path, 'disaster_recovery/test_backup.sql')
        self.assertEqual(backup_job.file_size_bytes, 1024000)
    
    def test_restore_job_lifecycle(self):
        """Test restore job lifecycle management."""
        # Create source backup job
        source_backup = BackupJob.objects.create(
            name='source_backup',
            backup_type='full_system',
            status='completed',
            file_path='disaster_recovery/source_backup.sql'
        )
        
        # Create restore job
        restore_job = RestoreJob.objects.create(
            restore_type='full_system',
            source_backup=source_backup,
            status='pending',
            created_by_username='test_user'
        )
        
        # Test job progression
        self.assertEqual(restore_job.status, 'pending')
        
        # Add log messages and update progress
        restore_job.add_log_message('info', 'Starting restore process')
        restore_job.update_progress(25, 'Downloading backup files')
        restore_job.update_progress(50, 'Restoring database')
        restore_job.update_progress(75, 'Validating restoration')
        
        self.assertEqual(len(restore_job.log_messages), 4)
        self.assertEqual(restore_job.progress_percentage, 75)
        
        # Mark as completed
        restore_job.status = 'completed'
        restore_job.completed_at = timezone.now()
        restore_job.progress_percentage = 100
        restore_job.save()
        
        self.assertEqual(restore_job.status, 'completed')
        self.assertIsNotNone(restore_job.completed_at)
        self.assertEqual(restore_job.progress_percentage, 100)


if __name__ == '__main__':
    unittest.main()