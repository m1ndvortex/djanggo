"""
Storage backends for Cloudflare R2 and Backblaze B2 integration.
Implements redundant backup storage for the ZARGAR jewelry SaaS platform.
"""
import logging
from typing import Optional, Dict, Any, List
from django.conf import settings
from django.core.files.storage import Storage
from django.core.files.base import ContentFile
from django.utils.deconstruct import deconstructible
from storages.backends.s3boto3 import S3Boto3Storage
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config


logger = logging.getLogger(__name__)


@deconstructible
class CloudflareR2Storage(S3Boto3Storage):
    """
    Cloudflare R2 storage backend using S3-compatible API.
    """
    
    def __init__(self, **settings_dict):
        # Cloudflare R2 configuration
        self.access_key = getattr(settings, 'CLOUDFLARE_R2_ACCESS_KEY', '')
        self.secret_key = getattr(settings, 'CLOUDFLARE_R2_SECRET_KEY', '')
        self.bucket_name = getattr(settings, 'CLOUDFLARE_R2_BUCKET', '')
        self.endpoint_url = getattr(settings, 'CLOUDFLARE_R2_ENDPOINT', '')
        self.account_id = getattr(settings, 'CLOUDFLARE_R2_ACCOUNT_ID', '')
        
        # Override settings for S3Boto3Storage
        settings_dict.update({
            'access_key': self.access_key,
            'secret_key': self.secret_key,
            'bucket_name': self.bucket_name,
            'endpoint_url': self.endpoint_url,
            'region_name': 'auto',  # Cloudflare R2 uses 'auto' region
            'signature_version': 's3v4',
            'addressing_style': 'path',
            'file_overwrite': False,
            'default_acl': None,  # R2 doesn't support ACLs
        })
        
        super().__init__(**settings_dict)
        
        # Configure boto3 client for Cloudflare R2
        self._configure_client()
    
    def _configure_client(self):
        """Configure boto3 client specifically for Cloudflare R2."""
        try:
            config = Config(
                region_name='auto',
                signature_version='s3v4',
                s3={
                    'addressing_style': 'path'
                }
            )
            
            self._client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=config
            )
            
            logger.info("Cloudflare R2 client configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to configure Cloudflare R2 client: {e}")
            raise
    
    def _save(self, name, content):
        """Override save method with R2-specific handling."""
        try:
            return super()._save(name, content)
        except ClientError as e:
            logger.error(f"Cloudflare R2 save error for {name}: {e}")
            raise
    
    def delete(self, name):
        """Override delete method with R2-specific handling."""
        try:
            return super().delete(name)
        except ClientError as e:
            logger.error(f"Cloudflare R2 delete error for {name}: {e}")
            raise
    
    def exists(self, name):
        """Check if file exists in Cloudflare R2."""
        try:
            return super().exists(name)
        except ClientError as e:
            logger.error(f"Cloudflare R2 exists check error for {name}: {e}")
            return False
    
    def url(self, name):
        """Generate URL for file in Cloudflare R2."""
        try:
            return super().url(name)
        except Exception as e:
            logger.error(f"Cloudflare R2 URL generation error for {name}: {e}")
            return None


@deconstructible
class BackblazeB2Storage(S3Boto3Storage):
    """
    Backblaze B2 storage backend using S3-compatible API.
    """
    
    def __init__(self, **settings_dict):
        # Backblaze B2 configuration
        self.access_key = getattr(settings, 'BACKBLAZE_B2_ACCESS_KEY', '')
        self.secret_key = getattr(settings, 'BACKBLAZE_B2_SECRET_KEY', '')
        self.bucket_name = getattr(settings, 'BACKBLAZE_B2_BUCKET', '')
        
        # Backblaze B2 endpoint - use environment variable or default
        self.endpoint_url = getattr(settings, 'BACKBLAZE_B2_ENDPOINT', 'https://s3.us-west-002.backblazeb2.com')
        
        # Extract region from endpoint URL
        self.region = 'us-west-002'  # default
        if 'us-east-005' in self.endpoint_url:
            self.region = 'us-east-005'
        elif 'us-west-002' in self.endpoint_url:
            self.region = 'us-west-002'
        
        # Override settings for S3Boto3Storage
        settings_dict.update({
            'access_key': self.access_key,
            'secret_key': self.secret_key,
            'bucket_name': self.bucket_name,
            'endpoint_url': self.endpoint_url,
            'region_name': self.region,
            'signature_version': 's3v4',
            'addressing_style': 'path',
            'file_overwrite': False,
            'default_acl': None,  # B2 doesn't support traditional ACLs
        })
        
        super().__init__(**settings_dict)
        
        # Configure boto3 client for Backblaze B2
        self._configure_client()
    
    def _configure_client(self):
        """Configure boto3 client specifically for Backblaze B2."""
        try:
            config = Config(
                region_name=self.region,
                signature_version='s3v4',
                s3={
                    'addressing_style': 'path'
                }
            )
            
            self._client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=config
            )
            
            logger.info("Backblaze B2 client configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to configure Backblaze B2 client: {e}")
            raise
    
    def _save(self, name, content):
        """Override save method with B2-specific handling."""
        try:
            return super()._save(name, content)
        except ClientError as e:
            logger.error(f"Backblaze B2 save error for {name}: {e}")
            raise
    
    def delete(self, name):
        """Override delete method with B2-specific handling."""
        try:
            return super().delete(name)
        except ClientError as e:
            logger.error(f"Backblaze B2 delete error for {name}: {e}")
            raise
    
    def exists(self, name):
        """Check if file exists in Backblaze B2."""
        try:
            return super().exists(name)
        except ClientError as e:
            logger.error(f"Backblaze B2 exists check error for {name}: {e}")
            return False
    
    def url(self, name):
        """Generate URL for file in Backblaze B2."""
        try:
            return super().url(name)
        except Exception as e:
            logger.error(f"Backblaze B2 URL generation error for {name}: {e}")
            return None


@deconstructible
class RedundantBackupStorage(Storage):
    """
    Redundant backup storage that uploads to both Cloudflare R2 and Backblaze B2.
    Provides dual storage redundancy for critical backup files.
    """
    
    def __init__(self):
        self.primary_storage = CloudflareR2Storage()
        self.secondary_storage = BackblazeB2Storage()
        
        # Validate storage configurations
        self._validate_configurations()
    
    def _validate_configurations(self):
        """Validate that both storage backends are properly configured."""
        errors = []
        
        # Check Cloudflare R2 configuration
        if not all([
            settings.CLOUDFLARE_R2_ACCESS_KEY,
            settings.CLOUDFLARE_R2_SECRET_KEY,
            settings.CLOUDFLARE_R2_BUCKET,
            settings.CLOUDFLARE_R2_ENDPOINT
        ]):
            errors.append("Cloudflare R2 configuration incomplete")
        
        # Check Backblaze B2 configuration
        if not all([
            settings.BACKBLAZE_B2_ACCESS_KEY,
            settings.BACKBLAZE_B2_SECRET_KEY,
            settings.BACKBLAZE_B2_BUCKET,
            settings.BACKBLAZE_B2_ENDPOINT
        ]):
            errors.append("Backblaze B2 configuration incomplete")
        
        if errors:
            logger.error(f"Storage configuration errors: {', '.join(errors)}")
            raise ValueError(f"Storage configuration errors: {', '.join(errors)}")
        
        logger.info("Redundant backup storage configurations validated successfully")
    
    def _save(self, name, content):
        """Save file to both storage backends."""
        results = {}
        errors = []
        
        # Reset content position for multiple reads
        if hasattr(content, 'seek'):
            content.seek(0)
        
        # Save to primary storage (Cloudflare R2)
        try:
            content_copy = ContentFile(content.read())
            content_copy.name = name
            primary_result = self.primary_storage._save(name, content_copy)
            results['primary'] = primary_result
            logger.info(f"Successfully saved {name} to Cloudflare R2")
        except Exception as e:
            error_msg = f"Failed to save {name} to Cloudflare R2: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Reset content for secondary storage
        if hasattr(content, 'seek'):
            content.seek(0)
        
        # Save to secondary storage (Backblaze B2)
        try:
            content_copy = ContentFile(content.read())
            content_copy.name = name
            secondary_result = self.secondary_storage._save(name, content_copy)
            results['secondary'] = secondary_result
            logger.info(f"Successfully saved {name} to Backblaze B2")
        except Exception as e:
            error_msg = f"Failed to save {name} to Backblaze B2: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Check if at least one storage succeeded
        if not results:
            raise Exception(f"Failed to save {name} to any storage backend: {'; '.join(errors)}")
        
        if len(results) == 1:
            logger.warning(f"File {name} saved to only one storage backend: {list(results.keys())[0]}")
        
        # Return the primary result if available, otherwise secondary
        return results.get('primary', results.get('secondary'))
    
    def delete(self, name):
        """Delete file from both storage backends."""
        errors = []
        success_count = 0
        
        # Delete from primary storage
        try:
            self.primary_storage.delete(name)
            success_count += 1
            logger.info(f"Successfully deleted {name} from Cloudflare R2")
        except Exception as e:
            error_msg = f"Failed to delete {name} from Cloudflare R2: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Delete from secondary storage
        try:
            self.secondary_storage.delete(name)
            success_count += 1
            logger.info(f"Successfully deleted {name} from Backblaze B2")
        except Exception as e:
            error_msg = f"Failed to delete {name} from Backblaze B2: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        if success_count == 0:
            raise Exception(f"Failed to delete {name} from any storage backend: {'; '.join(errors)}")
        
        if success_count == 1:
            logger.warning(f"File {name} deleted from only one storage backend")
    
    def exists(self, name):
        """Check if file exists in either storage backend."""
        try:
            # Check primary storage first
            if self.primary_storage.exists(name):
                return True
            
            # Check secondary storage
            return self.secondary_storage.exists(name)
            
        except Exception as e:
            logger.error(f"Error checking existence of {name}: {e}")
            return False
    
    def listdir(self, path):
        """List directory contents from primary storage."""
        try:
            return self.primary_storage.listdir(path)
        except Exception as e:
            logger.error(f"Error listing directory {path} from primary storage: {e}")
            try:
                return self.secondary_storage.listdir(path)
            except Exception as e2:
                logger.error(f"Error listing directory {path} from secondary storage: {e2}")
                return [], []
    
    def size(self, name):
        """Get file size from primary storage."""
        try:
            return self.primary_storage.size(name)
        except Exception as e:
            logger.error(f"Error getting size of {name} from primary storage: {e}")
            try:
                return self.secondary_storage.size(name)
            except Exception as e2:
                logger.error(f"Error getting size of {name} from secondary storage: {e2}")
                return 0
    
    def url(self, name):
        """Get URL from primary storage."""
        try:
            return self.primary_storage.url(name)
        except Exception as e:
            logger.error(f"Error getting URL for {name} from primary storage: {e}")
            try:
                return self.secondary_storage.url(name)
            except Exception as e2:
                logger.error(f"Error getting URL for {name} from secondary storage: {e2}")
                return None
    
    def get_available_name(self, name, max_length=None):
        """Get available name using primary storage logic."""
        return self.primary_storage.get_available_name(name, max_length)
    
    def get_storage_status(self) -> Dict[str, Any]:
        """Get status of both storage backends."""
        status = {
            'primary': {'name': 'Cloudflare R2', 'available': False, 'error': None},
            'secondary': {'name': 'Backblaze B2', 'available': False, 'error': None}
        }
        
        # Test primary storage
        try:
            test_file = ContentFile(b'test', name='test_connectivity.txt')
            self.primary_storage._save('test_connectivity.txt', test_file)
            self.primary_storage.delete('test_connectivity.txt')
            status['primary']['available'] = True
        except Exception as e:
            status['primary']['error'] = str(e)
        
        # Test secondary storage
        try:
            test_file = ContentFile(b'test', name='test_connectivity.txt')
            self.secondary_storage._save('test_connectivity.txt', test_file)
            self.secondary_storage.delete('test_connectivity.txt')
            status['secondary']['available'] = True
        except Exception as e:
            status['secondary']['error'] = str(e)
        
        return status


# Storage instances for use throughout the application
cloudflare_r2_storage = CloudflareR2Storage()
backblaze_b2_storage = BackblazeB2Storage()
redundant_backup_storage = RedundantBackupStorage()