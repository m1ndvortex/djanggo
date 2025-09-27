"""
Django management command to test storage connectivity and functionality.
Usage: python manage.py test_storage
"""
import json
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from zargar.core.storage_utils import (
    storage_manager,
    test_storage_connectivity,
    upload_file_to_backup_storage,
    download_file_from_backup_storage,
    get_backup_storage_status
)


class Command(BaseCommand):
    help = 'Test storage connectivity and functionality for Cloudflare R2 and Backblaze B2'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--test-upload',
            action='store_true',
            help='Test file upload functionality',
        )
        parser.add_argument(
            '--test-download',
            action='store_true',
            help='Test file download functionality',
        )
        parser.add_argument(
            '--test-redundant',
            action='store_true',
            help='Test redundant storage functionality',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output results in JSON format',
        )
    
    def handle(self, *args, **options):
        """Handle the command execution."""
        self.verbose = options['verbose']
        self.json_output = options['json']
        
        results = {
            'connectivity': None,
            'configuration': None,
            'upload_test': None,
            'download_test': None,
            'redundant_test': None,
            'overall_status': 'unknown'
        }
        
        try:
            # Test basic connectivity
            self.stdout.write("Testing storage connectivity...")
            connectivity_results = test_storage_connectivity()
            results['connectivity'] = connectivity_results
            
            if self.verbose:
                self._display_connectivity_results(connectivity_results)
            
            # Get configuration status
            self.stdout.write("Checking storage configuration...")
            config_status = get_backup_storage_status()
            results['configuration'] = config_status
            
            if self.verbose:
                self._display_configuration_status(config_status)
            
            # Test file upload if requested
            if options['test_upload']:
                self.stdout.write("Testing file upload...")
                upload_results = self._test_file_upload()
                results['upload_test'] = upload_results
                
                if self.verbose:
                    self._display_upload_results(upload_results)
            
            # Test file download if requested
            if options['test_download']:
                self.stdout.write("Testing file download...")
                download_results = self._test_file_download()
                results['download_test'] = download_results
                
                if self.verbose:
                    self._display_download_results(download_results)
            
            # Test redundant storage if requested
            if options['test_redundant']:
                self.stdout.write("Testing redundant storage...")
                redundant_results = self._test_redundant_storage()
                results['redundant_test'] = redundant_results
                
                if self.verbose:
                    self._display_redundant_results(redundant_results)
            
            # Determine overall status
            results['overall_status'] = self._determine_overall_status(results)
            
            # Output results
            if self.json_output:
                self.stdout.write(json.dumps(results, indent=2))
            else:
                self._display_summary(results)
            
        except Exception as e:
            if self.json_output:
                error_result = {'error': str(e), 'overall_status': 'error'}
                self.stdout.write(json.dumps(error_result, indent=2))
            else:
                raise CommandError(f'Storage test failed: {e}')
    
    def _display_connectivity_results(self, results):
        """Display connectivity test results."""
        self.stdout.write(self.style.SUCCESS("\n=== Connectivity Test Results ==="))
        
        for storage_name, result in results.items():
            if result['connected']:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ {storage_name}: Connected")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"✗ {storage_name}: Failed - {result['error']}")
                )
    
    def _display_configuration_status(self, status):
        """Display configuration status."""
        self.stdout.write(self.style.SUCCESS("\n=== Configuration Status ==="))
        
        config = status.get('configuration', {})
        
        for storage_name, config_info in config.items():
            if config_info.get('configured', False):
                self.stdout.write(
                    self.style.SUCCESS(f"✓ {storage_name}: Configured")
                )
                if 'bucket' in config_info:
                    self.stdout.write(f"  Bucket: {config_info['bucket']}")
                if 'endpoint' in config_info:
                    self.stdout.write(f"  Endpoint: {config_info['endpoint']}")
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠ {storage_name}: Not configured")
                )
    
    def _test_file_upload(self):
        """Test file upload functionality."""
        test_content = b'Test file content for storage upload test'
        test_filename = 'storage_test_upload.txt'
        
        results = {
            'single_backend': None,
            'redundant_backend': None
        }
        
        try:
            # Test single backend upload
            single_result = upload_file_to_backup_storage(
                test_filename, 
                test_content, 
                redundant=False
            )
            results['single_backend'] = single_result
            
            # Clean up single backend test file
            if single_result.get('success'):
                storage_manager.delete_backup_file(test_filename, from_all_backends=False)
            
        except Exception as e:
            results['single_backend'] = {'success': False, 'error': str(e)}
        
        try:
            # Test redundant backend upload
            redundant_result = upload_file_to_backup_storage(
                f'redundant_{test_filename}', 
                test_content, 
                redundant=True
            )
            results['redundant_backend'] = redundant_result
            
            # Clean up redundant backend test file
            if redundant_result.get('success'):
                storage_manager.delete_backup_file(f'redundant_{test_filename}', from_all_backends=True)
            
        except Exception as e:
            results['redundant_backend'] = {'success': False, 'error': str(e)}
        
        return results
    
    def _test_file_download(self):
        """Test file download functionality."""
        test_content = b'Test file content for storage download test'
        test_filename = 'storage_test_download.txt'
        
        results = {
            'upload_success': False,
            'download_success': False,
            'content_match': False,
            'error': None
        }
        
        try:
            # First upload a test file
            upload_result = upload_file_to_backup_storage(
                test_filename, 
                test_content, 
                redundant=False
            )
            
            if upload_result.get('success'):
                results['upload_success'] = True
                
                # Try to download the file
                downloaded_content = download_file_from_backup_storage(test_filename)
                
                if downloaded_content is not None:
                    results['download_success'] = True
                    results['content_match'] = (downloaded_content == test_content)
                
                # Clean up
                storage_manager.delete_backup_file(test_filename, from_all_backends=False)
            
        except Exception as e:
            results['error'] = str(e)
        
        return results
    
    def _test_redundant_storage(self):
        """Test redundant storage functionality."""
        test_content = b'Test file content for redundant storage test'
        test_filename = 'storage_test_redundant.txt'
        
        results = {
            'upload_to_both': False,
            'download_from_primary': False,
            'download_from_secondary': False,
            'delete_from_both': False,
            'error': None
        }
        
        try:
            # Upload to redundant storage
            upload_result = upload_file_to_backup_storage(
                test_filename, 
                test_content, 
                redundant=True
            )
            
            if upload_result.get('success'):
                expected_backends = ['cloudflare_r2', 'backblaze_b2']
                uploaded_to = upload_result.get('uploaded_to', [])
                results['upload_to_both'] = all(backend in uploaded_to for backend in expected_backends)
                
                # Test download from primary
                try:
                    primary_content = storage_manager.primary_storage.open(test_filename, 'rb').read()
                    results['download_from_primary'] = (primary_content == test_content)
                except:
                    results['download_from_primary'] = False
                
                # Test download from secondary
                try:
                    secondary_content = storage_manager.secondary_storage.open(test_filename, 'rb').read()
                    results['download_from_secondary'] = (secondary_content == test_content)
                except:
                    results['download_from_secondary'] = False
                
                # Clean up from both
                delete_result = storage_manager.delete_backup_file(test_filename, from_all_backends=True)
                results['delete_from_both'] = delete_result.get('success', False)
            
        except Exception as e:
            results['error'] = str(e)
        
        return results
    
    def _display_upload_results(self, results):
        """Display upload test results."""
        self.stdout.write(self.style.SUCCESS("\n=== Upload Test Results ==="))
        
        single = results.get('single_backend', {})
        if single and single.get('success'):
            self.stdout.write(self.style.SUCCESS("✓ Single backend upload: Success"))
        else:
            error = single.get('error', 'Unknown error') if single else 'No result'
            self.stdout.write(self.style.ERROR(f"✗ Single backend upload: Failed - {error}"))
        
        redundant = results.get('redundant_backend', {})
        if redundant and redundant.get('success'):
            self.stdout.write(self.style.SUCCESS("✓ Redundant backend upload: Success"))
        else:
            error = redundant.get('error', 'Unknown error') if redundant else 'No result'
            self.stdout.write(self.style.ERROR(f"✗ Redundant backend upload: Failed - {error}"))
    
    def _display_download_results(self, results):
        """Display download test results."""
        self.stdout.write(self.style.SUCCESS("\n=== Download Test Results ==="))
        
        if results.get('upload_success'):
            self.stdout.write(self.style.SUCCESS("✓ Test file upload: Success"))
        else:
            self.stdout.write(self.style.ERROR("✗ Test file upload: Failed"))
        
        if results.get('download_success'):
            self.stdout.write(self.style.SUCCESS("✓ File download: Success"))
        else:
            self.stdout.write(self.style.ERROR("✗ File download: Failed"))
        
        if results.get('content_match'):
            self.stdout.write(self.style.SUCCESS("✓ Content integrity: Verified"))
        else:
            self.stdout.write(self.style.ERROR("✗ Content integrity: Failed"))
    
    def _display_redundant_results(self, results):
        """Display redundant storage test results."""
        self.stdout.write(self.style.SUCCESS("\n=== Redundant Storage Test Results ==="))
        
        if results.get('upload_to_both'):
            self.stdout.write(self.style.SUCCESS("✓ Upload to both backends: Success"))
        else:
            self.stdout.write(self.style.ERROR("✗ Upload to both backends: Failed"))
        
        if results.get('download_from_primary'):
            self.stdout.write(self.style.SUCCESS("✓ Download from primary: Success"))
        else:
            self.stdout.write(self.style.ERROR("✗ Download from primary: Failed"))
        
        if results.get('download_from_secondary'):
            self.stdout.write(self.style.SUCCESS("✓ Download from secondary: Success"))
        else:
            self.stdout.write(self.style.ERROR("✗ Download from secondary: Failed"))
        
        if results.get('delete_from_both'):
            self.stdout.write(self.style.SUCCESS("✓ Delete from both backends: Success"))
        else:
            self.stdout.write(self.style.ERROR("✗ Delete from both backends: Failed"))
    
    def _determine_overall_status(self, results):
        """Determine overall test status."""
        connectivity = results.get('connectivity', {})
        
        # Check if at least one storage is connected
        connected_count = sum(1 for result in connectivity.values() if result.get('connected', False))
        
        if connected_count == 0:
            return 'failed'
        elif connected_count == len(connectivity):
            return 'excellent'
        else:
            return 'partial'
    
    def _display_summary(self, results):
        """Display test summary."""
        self.stdout.write(self.style.SUCCESS("\n=== Test Summary ==="))
        
        overall_status = results['overall_status']
        
        if overall_status == 'excellent':
            self.stdout.write(self.style.SUCCESS("🎉 All storage backends are working perfectly!"))
        elif overall_status == 'partial':
            self.stdout.write(self.style.WARNING("⚠️  Some storage backends are working, but not all."))
        elif overall_status == 'failed':
            self.stdout.write(self.style.ERROR("❌ No storage backends are working properly."))
        else:
            self.stdout.write(self.style.ERROR("❓ Unable to determine storage status."))
        
        # Display recommendations
        connectivity = results.get('connectivity', {})
        failed_storages = [name for name, result in connectivity.items() if not result.get('connected', False)]
        
        if failed_storages:
            self.stdout.write(self.style.WARNING(f"\nFailed storage backends: {', '.join(failed_storages)}"))
            self.stdout.write("Please check your storage credentials and network connectivity.")
        
        self.stdout.write("\nFor detailed results, run with --verbose flag.")
        self.stdout.write("For JSON output, run with --json flag.")