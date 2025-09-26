"""
Storage utilities for backup and file management operations.
Provides helper functions for working with redundant storage backends.
"""
import logging
from typing import Dict, Any, Optional, List
from django.core.files.base import ContentFile
from django.core.files.storage import get_storage_class
from django.conf import settings
from .storage import (
    cloudflare_r2_storage,
    backblaze_b2_storage,
    redundant_backup_storage
)


logger = logging.getLogger(__name__)


class StorageManager:
    """
    Manager class for handling storage operations across multiple backends.
    """
    
    def __init__(self):
        self.primary_storage = cloudflare_r2_storage
        self.secondary_storage = backblaze_b2_storage
        self.redundant_storage = redundant_backup_storage
    
    def test_connectivity(self) -> Dict[str, Any]:
        """
        Test connectivity to all storage backends.
        
        Returns:
            Dict containing connectivity status for each backend
        """
        results = {
            'cloudflare_r2': {'connected': False, 'error': None},
            'backblaze_b2': {'connected': False, 'error': None},
            'redundant': {'connected': False, 'error': None}
        }
        
        # Test Cloudflare R2
        try:
            test_file = ContentFile(b'connectivity_test', name='test_connectivity.txt')
            saved_name = self.primary_storage._save('test_connectivity.txt', test_file)
            self.primary_storage.delete(saved_name)
            results['cloudflare_r2']['connected'] = True
            logger.info("Cloudflare R2 connectivity test successful")
        except Exception as e:
            results['cloudflare_r2']['error'] = str(e)
            logger.error(f"Cloudflare R2 connectivity test failed: {e}")
        
        # Test Backblaze B2
        try:
            test_file = ContentFile(b'connectivity_test', name='test_connectivity.txt')
            saved_name = self.secondary_storage._save('test_connectivity.txt', test_file)
            self.secondary_storage.delete(saved_name)
            results['backblaze_b2']['connected'] = True
            logger.info("Backblaze B2 connectivity test successful")
        except Exception as e:
            results['backblaze_b2']['error'] = str(e)
            logger.error(f"Backblaze B2 connectivity test failed: {e}")
        
        # Test redundant storage
        try:
            test_file = ContentFile(b'redundant_test', name='test_redundant.txt')
            saved_name = self.redundant_storage._save('test_redundant.txt', test_file)
            self.redundant_storage.delete(saved_name)
            results['redundant']['connected'] = True
            logger.info("Redundant storage connectivity test successful")
        except Exception as e:
            results['redundant']['error'] = str(e)
            logger.error(f"Redundant storage connectivity test failed: {e}")
        
        return results
    
    def upload_backup_file(self, file_path: str, content: bytes, use_redundant: bool = True) -> Dict[str, Any]:
        """
        Upload a backup file to storage.
        
        Args:
            file_path: Path where the file should be stored
            content: File content as bytes
            use_redundant: Whether to use redundant storage (both backends)
        
        Returns:
            Dict containing upload results
        """
        results = {'success': False, 'errors': [], 'uploaded_to': []}
        
        try:
            content_file = ContentFile(content, name=file_path)
            
            if use_redundant:
                # Use redundant storage (uploads to both backends)
                saved_name = self.redundant_storage._save(file_path, content_file)
                results['success'] = True
                results['uploaded_to'] = ['cloudflare_r2', 'backblaze_b2']
                results['saved_name'] = saved_name
                logger.info(f"Successfully uploaded {file_path} to redundant storage")
            else:
                # Upload to primary storage only
                saved_name = self.primary_storage._save(file_path, content_file)
                results['success'] = True
                results['uploaded_to'] = ['cloudflare_r2']
                results['saved_name'] = saved_name
                logger.info(f"Successfully uploaded {file_path} to Cloudflare R2")
                
        except Exception as e:
            error_msg = f"Failed to upload {file_path}: {e}"
            results['errors'].append(error_msg)
            logger.error(error_msg)
        
        return results
    
    def download_backup_file(self, file_path: str) -> Optional[bytes]:
        """
        Download a backup file from storage.
        
        Args:
            file_path: Path of the file to download
        
        Returns:
            File content as bytes, or None if not found
        """
        try:
            # Try primary storage first
            if self.primary_storage.exists(file_path):
                with self.primary_storage.open(file_path, 'rb') as f:
                    content = f.read()
                logger.info(f"Successfully downloaded {file_path} from Cloudflare R2")
                return content
        except Exception as e:
            logger.error(f"Failed to download {file_path} from Cloudflare R2: {e}")
        
        try:
            # Try secondary storage
            if self.secondary_storage.exists(file_path):
                with self.secondary_storage.open(file_path, 'rb') as f:
                    content = f.read()
                logger.info(f"Successfully downloaded {file_path} from Backblaze B2")
                return content
        except Exception as e:
            logger.error(f"Failed to download {file_path} from Backblaze B2: {e}")
        
        logger.error(f"File {file_path} not found in any storage backend")
        return None
    
    def list_backup_files(self, prefix: str = '') -> List[str]:
        """
        List backup files with optional prefix filter.
        
        Args:
            prefix: Optional prefix to filter files
        
        Returns:
            List of file paths
        """
        files = []
        
        try:
            # List from primary storage
            dirs, file_list = self.primary_storage.listdir(prefix)
            files.extend(file_list)
            logger.info(f"Listed {len(file_list)} files from Cloudflare R2 with prefix '{prefix}'")
        except Exception as e:
            logger.error(f"Failed to list files from Cloudflare R2: {e}")
            
            try:
                # Fallback to secondary storage
                dirs, file_list = self.secondary_storage.listdir(prefix)
                files.extend(file_list)
                logger.info(f"Listed {len(file_list)} files from Backblaze B2 with prefix '{prefix}'")
            except Exception as e2:
                logger.error(f"Failed to list files from Backblaze B2: {e2}")
        
        return files
    
    def delete_backup_file(self, file_path: str, from_all_backends: bool = True) -> Dict[str, Any]:
        """
        Delete a backup file from storage.
        
        Args:
            file_path: Path of the file to delete
            from_all_backends: Whether to delete from all backends
        
        Returns:
            Dict containing deletion results
        """
        results = {'success': False, 'deleted_from': [], 'errors': []}
        
        if from_all_backends:
            # Delete from both backends
            try:
                self.redundant_storage.delete(file_path)
                results['success'] = True
                results['deleted_from'] = ['cloudflare_r2', 'backblaze_b2']
                logger.info(f"Successfully deleted {file_path} from redundant storage")
            except Exception as e:
                error_msg = f"Failed to delete {file_path} from redundant storage: {e}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
        else:
            # Delete from primary storage only
            try:
                self.primary_storage.delete(file_path)
                results['success'] = True
                results['deleted_from'] = ['cloudflare_r2']
                logger.info(f"Successfully deleted {file_path} from Cloudflare R2")
            except Exception as e:
                error_msg = f"Failed to delete {file_path} from Cloudflare R2: {e}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
        
        return results
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """
        Get storage statistics and health information.
        
        Returns:
            Dict containing storage statistics
        """
        stats = {
            'connectivity': self.test_connectivity(),
            'configuration': {
                'cloudflare_r2': {
                    'bucket': settings.CLOUDFLARE_R2_BUCKET,
                    'endpoint': settings.CLOUDFLARE_R2_ENDPOINT,
                    'configured': bool(settings.CLOUDFLARE_R2_ACCESS_KEY)
                },
                'backblaze_b2': {
                    'bucket': settings.BACKBLAZE_B2_BUCKET,
                    'configured': bool(settings.BACKBLAZE_B2_ACCESS_KEY)
                }
            }
        }
        
        return stats


# Global storage manager instance
storage_manager = StorageManager()


def test_storage_connectivity() -> Dict[str, Any]:
    """
    Convenience function to test storage connectivity.
    
    Returns:
        Dict containing connectivity test results
    """
    return storage_manager.test_connectivity()


def upload_file_to_backup_storage(file_path: str, content: bytes, redundant: bool = True) -> Dict[str, Any]:
    """
    Convenience function to upload a file to backup storage.
    
    Args:
        file_path: Path where the file should be stored
        content: File content as bytes
        redundant: Whether to use redundant storage
    
    Returns:
        Dict containing upload results
    """
    return storage_manager.upload_backup_file(file_path, content, redundant)


def download_file_from_backup_storage(file_path: str) -> Optional[bytes]:
    """
    Convenience function to download a file from backup storage.
    
    Args:
        file_path: Path of the file to download
    
    Returns:
        File content as bytes, or None if not found
    """
    return storage_manager.download_backup_file(file_path)


def get_backup_storage_status() -> Dict[str, Any]:
    """
    Convenience function to get backup storage status.
    
    Returns:
        Dict containing storage status information
    """
    return storage_manager.get_storage_statistics()