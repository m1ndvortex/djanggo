"""
Tests for storage integration with Cloudflare R2 and Backblaze B2.
Tests storage connectivity, file upload/download, and redundant backup functionality.
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.core.files.base import ContentFile
from django.conf import settings
from botocore.exceptions import ClientError, NoCredentialsError

from zargar.core.storage import (
    CloudflareR2Storage,
    BackblazeB2Storage,
    RedundantBackupStorage,
    cloudflare_r2_storage,
    backblaze_b2_storage,
    redundant_backup_storage
)
from zargar.core.storage_utils import (
    StorageManager,
    storage_manager,
    test_storage_connectivity,
    upload_file_to_backup_storage,
    download_file_from_backup_storage,
    get_backup_storage_status
)


class CloudflareR2StorageTests(TestCase):
    """Test Cloudflare R2 storage backend."""
    
    def setUp(self):
        """Set up test environment."""
        self.storage = CloudflareR2Storage()
        self.test_content = b'Test file content for Cloudflare R2'
        self.test_filename = 'test_cloudflare_r2.txt'
    
    @override_settings(
        CLOUDFLARE_R2_ACCESS_KEY='test_access_key',
        CLOUDFLARE_R2_SECRET_KEY='test_secret_key',
        CLOUDFLARE_R2_BUCKET='test_bucket',
        CLOUDFLARE_R2_ENDPOINT='https://test.r2.cloudflarestorage.com',
        CLOUDFLARE_R2_ACCOUNT_ID='test_account_id'
    )
    def test_cloudflare_r2_configuration(self):
        """Test Cloudflare R2 storage configuration."""
        storage = CloudflareR2Storage()
        
        self.assertEqual(storage.access_key, 'test_access_key')
        self.assertEqual(storage.secret_key, 'test_secret_key')
        self.assertEqual(storage.bucket_name, 'test_bucket')
        self.assertEqual(storage.endpoint_url, 'https://test.r2.cloudflarestorage.com')
        self.assertEqual(storage.account_id, 'test_account_id')
    
    @patch('zargar.core.storage.boto3.client')
    def test_cloudflare_r2_client_configuration(self, mock_boto3_client):
        """Test Cloudflare R2 boto3 client configuration."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        
        storage = CloudflareR2Storage()
        
        # Verify boto3 client was called with correct parameters
        self.assertTrue(mock_boto3_client.called)
        
        # Check the last call (most recent configuration)
        call_args = mock_boto3_client.call_args
        
        self.assertEqual(call_args[0][0], 's3')
        self.assertIn('endpoint_url', call_args[1])
        self.assertIn('aws_access_key_id', call_args[1])
        self.assertIn('aws_secret_access_key', call_args[1])
        self.assertIn('config', call_args[1])
    
    @patch('zargar.core.storage.S3Boto3Storage._save')
    def test_cloudflare_r2_save_success(self, mock_save):
        """Test successful file save to Cloudflare R2."""
        mock_save.return_value = self.test_filename
        
        content_file = ContentFile(self.test_content, name=self.test_filename)
        result = self.storage._save(self.test_filename, content_file)
        
        self.assertEqual(result, self.test_filename)
        mock_save.assert_called_once()
    
    @patch('zargar.core.storage.S3Boto3Storage._save')
    def test_cloudflare_r2_save_error(self, mock_save):
        """Test file save error handling for Cloudflare R2."""
        mock_save.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='PutObject'
        )
        
        content_file = ContentFile(self.test_content, name=self.test_filename)
        
        with self.assertRaises(ClientError):
            self.storage._save(self.test_filename, content_file)
    
    @patch('zargar.core.storage.S3Boto3Storage.delete')
    def test_cloudflare_r2_delete_success(self, mock_delete):
        """Test successful file deletion from Cloudflare R2."""
        mock_delete.return_value = None
        
        self.storage.delete(self.test_filename)
        
        mock_delete.assert_called_once_with(self.test_filename)
    
    @patch('zargar.core.storage.S3Boto3Storage.exists')
    def test_cloudflare_r2_exists_check(self, mock_exists):
        """Test file existence check for Cloudflare R2."""
        mock_exists.return_value = True
        
        result = self.storage.exists(self.test_filename)
        
        self.assertTrue(result)
        mock_exists.assert_called_once_with(self.test_filename)


class BackblazeB2StorageTests(TestCase):
    """Test Backblaze B2 storage backend."""
    
    def setUp(self):
        """Set up test environment."""
        self.storage = BackblazeB2Storage()
        self.test_content = b'Test file content for Backblaze B2'
        self.test_filename = 'test_backblaze_b2.txt'
    
    @override_settings(
        BACKBLAZE_B2_ACCESS_KEY='test_access_key',
        BACKBLAZE_B2_SECRET_KEY='test_secret_key',
        BACKBLAZE_B2_BUCKET='test_bucket'
    )
    def test_backblaze_b2_configuration(self):
        """Test Backblaze B2 storage configuration."""
        storage = BackblazeB2Storage()
        
        self.assertEqual(storage.access_key, 'test_access_key')
        self.assertEqual(storage.secret_key, 'test_secret_key')
        self.assertEqual(storage.bucket_name, 'test_bucket')
        self.assertEqual(storage.endpoint_url, 'https://s3.us-west-002.backblazeb2.com')
    
    @patch('zargar.core.storage.boto3.client')
    def test_backblaze_b2_client_configuration(self, mock_boto3_client):
        """Test Backblaze B2 boto3 client configuration."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        
        storage = BackblazeB2Storage()
        
        # Verify boto3 client was called with correct parameters
        self.assertTrue(mock_boto3_client.called)
        
        # Check the last call (most recent configuration)
        call_args = mock_boto3_client.call_args
        
        self.assertEqual(call_args[0][0], 's3')
        self.assertIn('endpoint_url', call_args[1])
        self.assertEqual(call_args[1]['endpoint_url'], 'https://s3.us-west-002.backblazeb2.com')
    
    @patch('zargar.core.storage.S3Boto3Storage._save')
    def test_backblaze_b2_save_success(self, mock_save):
        """Test successful file save to Backblaze B2."""
        mock_save.return_value = self.test_filename
        
        content_file = ContentFile(self.test_content, name=self.test_filename)
        result = self.storage._save(self.test_filename, content_file)
        
        self.assertEqual(result, self.test_filename)
        mock_save.assert_called_once()


class RedundantBackupStorageTests(TestCase):
    """Test redundant backup storage functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_content = b'Test file content for redundant backup'
        self.test_filename = 'test_redundant_backup.txt'
    
    @override_settings(
        CLOUDFLARE_R2_ACCESS_KEY='test_r2_key',
        CLOUDFLARE_R2_SECRET_KEY='test_r2_secret',
        CLOUDFLARE_R2_BUCKET='test_r2_bucket',
        CLOUDFLARE_R2_ENDPOINT='https://test.r2.cloudflarestorage.com',
        BACKBLAZE_B2_ACCESS_KEY='test_b2_key',
        BACKBLAZE_B2_SECRET_KEY='test_b2_secret',
        BACKBLAZE_B2_BUCKET='test_b2_bucket'
    )
    def test_redundant_storage_configuration_validation(self):
        """Test redundant storage configuration validation."""
        # Should not raise an exception with valid configuration
        storage = RedundantBackupStorage()
        self.assertIsNotNone(storage.primary_storage)
        self.assertIsNotNone(storage.secondary_storage)
    
    @override_settings(
        CLOUDFLARE_R2_ACCESS_KEY='',  # Missing key
        CLOUDFLARE_R2_SECRET_KEY='test_r2_secret',
        CLOUDFLARE_R2_BUCKET='test_r2_bucket',
        CLOUDFLARE_R2_ENDPOINT='https://test.r2.cloudflarestorage.com',
        BACKBLAZE_B2_ACCESS_KEY='test_b2_key',
        BACKBLAZE_B2_SECRET_KEY='test_b2_secret',
        BACKBLAZE_B2_BUCKET='test_b2_bucket'
    )
    def test_redundant_storage_invalid_configuration(self):
        """Test redundant storage with invalid configuration."""
        with self.assertRaises(ValueError) as context:
            RedundantBackupStorage()
        
        self.assertIn('Cloudflare R2 configuration incomplete', str(context.exception))
    
    @patch('zargar.core.storage.CloudflareR2Storage._save')
    @patch('zargar.core.storage.BackblazeB2Storage._save')
    def test_redundant_storage_save_both_success(self, mock_b2_save, mock_r2_save):
        """Test successful save to both storage backends."""
        mock_r2_save.return_value = self.test_filename
        mock_b2_save.return_value = self.test_filename
        
        storage = RedundantBackupStorage()
        content_file = ContentFile(self.test_content, name=self.test_filename)
        
        result = storage._save(self.test_filename, content_file)
        
        self.assertEqual(result, self.test_filename)
        mock_r2_save.assert_called_once()
        mock_b2_save.assert_called_once()
    
    @patch('zargar.core.storage.CloudflareR2Storage._save')
    @patch('zargar.core.storage.BackblazeB2Storage._save')
    def test_redundant_storage_save_partial_success(self, mock_b2_save, mock_r2_save):
        """Test save with one backend failing."""
        mock_r2_save.return_value = self.test_filename
        mock_b2_save.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='PutObject'
        )
        
        storage = RedundantBackupStorage()
        content_file = ContentFile(self.test_content, name=self.test_filename)
        
        # Should succeed with one backend working
        result = storage._save(self.test_filename, content_file)
        
        self.assertEqual(result, self.test_filename)
        mock_r2_save.assert_called_once()
        mock_b2_save.assert_called_once()
    
    @patch('zargar.core.storage.CloudflareR2Storage._save')
    @patch('zargar.core.storage.BackblazeB2Storage._save')
    def test_redundant_storage_save_both_fail(self, mock_b2_save, mock_r2_save):
        """Test save with both backends failing."""
        mock_r2_save.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='PutObject'
        )
        mock_b2_save.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='PutObject'
        )
        
        storage = RedundantBackupStorage()
        content_file = ContentFile(self.test_content, name=self.test_filename)
        
        with self.assertRaises(Exception) as context:
            storage._save(self.test_filename, content_file)
        
        self.assertIn('Failed to save', str(context.exception))
    
    @patch('zargar.core.storage.CloudflareR2Storage.delete')
    @patch('zargar.core.storage.BackblazeB2Storage.delete')
    def test_redundant_storage_delete_success(self, mock_b2_delete, mock_r2_delete):
        """Test successful deletion from both storage backends."""
        mock_r2_delete.return_value = None
        mock_b2_delete.return_value = None
        
        storage = RedundantBackupStorage()
        storage.delete(self.test_filename)
        
        mock_r2_delete.assert_called_once_with(self.test_filename)
        mock_b2_delete.assert_called_once_with(self.test_filename)
    
    @patch('zargar.core.storage.CloudflareR2Storage.exists')
    @patch('zargar.core.storage.BackblazeB2Storage.exists')
    def test_redundant_storage_exists_primary_found(self, mock_b2_exists, mock_r2_exists):
        """Test file existence check with file found in primary storage."""
        mock_r2_exists.return_value = True
        mock_b2_exists.return_value = False
        
        storage = RedundantBackupStorage()
        result = storage.exists(self.test_filename)
        
        self.assertTrue(result)
        mock_r2_exists.assert_called_once_with(self.test_filename)
        # Should not check secondary if found in primary
        mock_b2_exists.assert_not_called()
    
    @patch('zargar.core.storage.CloudflareR2Storage.exists')
    @patch('zargar.core.storage.BackblazeB2Storage.exists')
    def test_redundant_storage_exists_secondary_found(self, mock_b2_exists, mock_r2_exists):
        """Test file existence check with file found in secondary storage."""
        mock_r2_exists.return_value = False
        mock_b2_exists.return_value = True
        
        storage = RedundantBackupStorage()
        result = storage.exists(self.test_filename)
        
        self.assertTrue(result)
        mock_r2_exists.assert_called_once_with(self.test_filename)
        mock_b2_exists.assert_called_once_with(self.test_filename)


class StorageManagerTests(TestCase):
    """Test storage manager functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.manager = StorageManager()
        self.test_content = b'Test content for storage manager'
        self.test_filename = 'test_manager.txt'
    
    @patch('zargar.core.storage.CloudflareR2Storage._save')
    @patch('zargar.core.storage.CloudflareR2Storage.delete')
    @patch('zargar.core.storage.BackblazeB2Storage._save')
    @patch('zargar.core.storage.BackblazeB2Storage.delete')
    def test_storage_manager_connectivity_test(self, mock_b2_delete, mock_b2_save, 
                                             mock_r2_delete, mock_r2_save):
        """Test storage manager connectivity testing."""
        mock_r2_save.return_value = 'test_connectivity.txt'
        mock_r2_delete.return_value = None
        mock_b2_save.return_value = 'test_connectivity.txt'
        mock_b2_delete.return_value = None
        
        results = self.manager.test_connectivity()
        
        self.assertIn('cloudflare_r2', results)
        self.assertIn('backblaze_b2', results)
        self.assertIn('redundant', results)
        
        self.assertTrue(results['cloudflare_r2']['connected'])
        self.assertTrue(results['backblaze_b2']['connected'])
        self.assertIsNone(results['cloudflare_r2']['error'])
        self.assertIsNone(results['backblaze_b2']['error'])
    
    @patch('zargar.core.storage.RedundantBackupStorage._save')
    def test_storage_manager_upload_redundant(self, mock_redundant_save):
        """Test storage manager redundant file upload."""
        mock_redundant_save.return_value = self.test_filename
        
        result = self.manager.upload_backup_file(
            self.test_filename, 
            self.test_content, 
            use_redundant=True
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['uploaded_to'], ['cloudflare_r2', 'backblaze_b2'])
        self.assertEqual(result['saved_name'], self.test_filename)
        mock_redundant_save.assert_called_once()
    
    @patch('zargar.core.storage.CloudflareR2Storage._save')
    def test_storage_manager_upload_single(self, mock_r2_save):
        """Test storage manager single backend file upload."""
        mock_r2_save.return_value = self.test_filename
        
        result = self.manager.upload_backup_file(
            self.test_filename, 
            self.test_content, 
            use_redundant=False
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['uploaded_to'], ['cloudflare_r2'])
        self.assertEqual(result['saved_name'], self.test_filename)
        mock_r2_save.assert_called_once()
    
    @patch('zargar.core.storage.CloudflareR2Storage.exists')
    @patch('zargar.core.storage.CloudflareR2Storage.open')
    def test_storage_manager_download_success(self, mock_r2_open, mock_r2_exists):
        """Test storage manager file download success."""
        mock_r2_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = self.test_content
        mock_r2_open.return_value.__enter__.return_value = mock_file
        
        result = self.manager.download_backup_file(self.test_filename)
        
        self.assertEqual(result, self.test_content)
        mock_r2_exists.assert_called_once_with(self.test_filename)
        mock_r2_open.assert_called_once_with(self.test_filename, 'rb')
    
    @patch('zargar.core.storage.CloudflareR2Storage.exists')
    @patch('zargar.core.storage.BackblazeB2Storage.exists')
    def test_storage_manager_download_not_found(self, mock_b2_exists, mock_r2_exists):
        """Test storage manager file download when file not found."""
        mock_r2_exists.return_value = False
        mock_b2_exists.return_value = False
        
        result = self.manager.download_backup_file(self.test_filename)
        
        self.assertIsNone(result)
        mock_r2_exists.assert_called_once_with(self.test_filename)
        mock_b2_exists.assert_called_once_with(self.test_filename)


class StorageUtilityFunctionsTests(TestCase):
    """Test storage utility functions."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_content = b'Test content for utility functions'
        self.test_filename = 'test_utility.txt'
    
    @patch('zargar.core.storage_utils.storage_manager.test_connectivity')
    def test_test_storage_connectivity_function(self, mock_test_connectivity):
        """Test test_storage_connectivity utility function."""
        expected_result = {
            'cloudflare_r2': {'connected': True, 'error': None},
            'backblaze_b2': {'connected': True, 'error': None},
            'redundant': {'connected': True, 'error': None}
        }
        mock_test_connectivity.return_value = expected_result
        
        result = test_storage_connectivity()
        
        self.assertEqual(result, expected_result)
        mock_test_connectivity.assert_called_once()
    
    @patch('zargar.core.storage_utils.storage_manager.upload_backup_file')
    def test_upload_file_to_backup_storage_function(self, mock_upload):
        """Test upload_file_to_backup_storage utility function."""
        expected_result = {
            'success': True,
            'uploaded_to': ['cloudflare_r2', 'backblaze_b2'],
            'saved_name': self.test_filename
        }
        mock_upload.return_value = expected_result
        
        result = upload_file_to_backup_storage(
            self.test_filename, 
            self.test_content, 
            redundant=True
        )
        
        self.assertEqual(result, expected_result)
        mock_upload.assert_called_once_with(self.test_filename, self.test_content, True)
    
    @patch('zargar.core.storage_utils.storage_manager.download_backup_file')
    def test_download_file_from_backup_storage_function(self, mock_download):
        """Test download_file_from_backup_storage utility function."""
        mock_download.return_value = self.test_content
        
        result = download_file_from_backup_storage(self.test_filename)
        
        self.assertEqual(result, self.test_content)
        mock_download.assert_called_once_with(self.test_filename)
    
    @patch('zargar.core.storage_utils.storage_manager.get_storage_statistics')
    def test_get_backup_storage_status_function(self, mock_get_stats):
        """Test get_backup_storage_status utility function."""
        expected_result = {
            'connectivity': {'cloudflare_r2': {'connected': True}},
            'configuration': {'cloudflare_r2': {'configured': True}}
        }
        mock_get_stats.return_value = expected_result
        
        result = get_backup_storage_status()
        
        self.assertEqual(result, expected_result)
        mock_get_stats.assert_called_once()


@pytest.mark.integration
class StorageIntegrationTests(TestCase):
    """
    Integration tests for storage functionality.
    These tests require actual storage credentials and should be run in Docker environment.
    """
    
    def setUp(self):
        """Set up integration test environment."""
        self.test_content = b'Integration test content'
        self.test_filename = 'integration_test.txt'
    
    @pytest.mark.skipif(
        not all([
            settings.CLOUDFLARE_R2_ACCESS_KEY,
            settings.CLOUDFLARE_R2_SECRET_KEY,
            settings.CLOUDFLARE_R2_BUCKET
        ]),
        reason="Cloudflare R2 credentials not configured"
    )
    def test_cloudflare_r2_real_connectivity(self):
        """Test real connectivity to Cloudflare R2 (requires credentials)."""
        storage = CloudflareR2Storage()
        
        try:
            # Test file upload
            content_file = ContentFile(self.test_content, name=self.test_filename)
            saved_name = storage._save(self.test_filename, content_file)
            
            # Test file exists
            self.assertTrue(storage.exists(saved_name))
            
            # Test file download
            with storage.open(saved_name, 'rb') as f:
                downloaded_content = f.read()
            
            self.assertEqual(downloaded_content, self.test_content)
            
            # Clean up
            storage.delete(saved_name)
            
        except Exception as e:
            self.fail(f"Cloudflare R2 integration test failed: {e}")
    
    @pytest.mark.skipif(
        not all([
            settings.BACKBLAZE_B2_ACCESS_KEY,
            settings.BACKBLAZE_B2_SECRET_KEY,
            settings.BACKBLAZE_B2_BUCKET
        ]),
        reason="Backblaze B2 credentials not configured"
    )
    def test_backblaze_b2_real_connectivity(self):
        """Test real connectivity to Backblaze B2 (requires credentials)."""
        storage = BackblazeB2Storage()
        
        try:
            # Test file upload
            content_file = ContentFile(self.test_content, name=self.test_filename)
            saved_name = storage._save(self.test_filename, content_file)
            
            # Test file exists
            self.assertTrue(storage.exists(saved_name))
            
            # Test file download
            with storage.open(saved_name, 'rb') as f:
                downloaded_content = f.read()
            
            self.assertEqual(downloaded_content, self.test_content)
            
            # Clean up
            storage.delete(saved_name)
            
        except Exception as e:
            self.fail(f"Backblaze B2 integration test failed: {e}")
    
    @pytest.mark.skipif(
        not all([
            settings.CLOUDFLARE_R2_ACCESS_KEY,
            settings.BACKBLAZE_B2_ACCESS_KEY
        ]),
        reason="Storage credentials not configured"
    )
    def test_redundant_storage_real_connectivity(self):
        """Test real redundant storage connectivity (requires credentials)."""
        manager = StorageManager()
        
        try:
            # Test connectivity
            connectivity_results = manager.test_connectivity()
            
            # At least one storage should be connected
            connected_storages = [
                name for name, result in connectivity_results.items() 
                if result.get('connected', False)
            ]
            
            self.assertGreater(len(connected_storages), 0, 
                             "At least one storage backend should be connected")
            
            # Test file upload and download if any storage is connected
            if connected_storages:
                upload_result = manager.upload_backup_file(
                    self.test_filename, 
                    self.test_content, 
                    use_redundant=True
                )
                
                if upload_result['success']:
                    # Test download
                    downloaded_content = manager.download_backup_file(self.test_filename)
                    self.assertEqual(downloaded_content, self.test_content)
                    
                    # Clean up
                    manager.delete_backup_file(self.test_filename, from_all_backends=True)
            
        except Exception as e:
            self.fail(f"Redundant storage integration test failed: {e}")