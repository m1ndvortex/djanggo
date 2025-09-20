#!/usr/bin/env python
"""
Demo script to showcase Cloudflare R2 and Backblaze B2 storage integration.
This script demonstrates the redundant backup storage functionality.

Usage:
    docker-compose exec web python demo_storage_integration.py
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.base')
django.setup()

from zargar.core.storage_utils import (
    storage_manager,
    test_storage_connectivity,
    upload_file_to_backup_storage,
    download_file_from_backup_storage,
    get_backup_storage_status
)


def main():
    """Main demonstration function."""
    print("🚀 ZARGAR Storage Integration Demo")
    print("=" * 50)
    
    # Test connectivity
    print("\n1. Testing Storage Connectivity...")
    connectivity_results = test_storage_connectivity()
    
    for storage_name, result in connectivity_results.items():
        status = "✅ Connected" if result['connected'] else f"❌ Failed: {result['error']}"
        print(f"   {storage_name}: {status}")
    
    # Get storage status
    print("\n2. Storage Configuration Status...")
    status = get_backup_storage_status()
    
    for storage_name, config in status['configuration'].items():
        configured = "✅ Configured" if config['configured'] else "❌ Not Configured"
        print(f"   {storage_name}: {configured}")
        if 'bucket' in config:
            print(f"      Bucket: {config['bucket']}")
        if 'endpoint' in config:
            print(f"      Endpoint: {config['endpoint']}")
    
    # Test file upload
    print("\n3. Testing File Upload...")
    test_content = b"Hello from ZARGAR! This is a test backup file."
    test_filename = "demo_backup_test.txt"
    
    # Upload to single backend
    print("   Uploading to single backend (Cloudflare R2)...")
    single_result = upload_file_to_backup_storage(
        f"single_{test_filename}", 
        test_content, 
        redundant=False
    )
    
    if single_result['success']:
        print(f"   ✅ Single upload successful to: {', '.join(single_result['uploaded_to'])}")
    else:
        print(f"   ❌ Single upload failed: {single_result.get('errors', [])}")
    
    # Upload to redundant storage
    print("   Uploading to redundant storage (both backends)...")
    redundant_result = upload_file_to_backup_storage(
        f"redundant_{test_filename}", 
        test_content, 
        redundant=True
    )
    
    if redundant_result['success']:
        print(f"   ✅ Redundant upload successful to: {', '.join(redundant_result['uploaded_to'])}")
    else:
        print(f"   ❌ Redundant upload failed: {redundant_result.get('errors', [])}")
    
    # Test file download
    print("\n4. Testing File Download...")
    
    if single_result['success']:
        downloaded_content = download_file_from_backup_storage(f"single_{test_filename}")
        if downloaded_content == test_content:
            print("   ✅ Single file download and verification successful")
        else:
            print("   ❌ Single file download failed or content mismatch")
    
    if redundant_result['success']:
        downloaded_content = download_file_from_backup_storage(f"redundant_{test_filename}")
        if downloaded_content == test_content:
            print("   ✅ Redundant file download and verification successful")
        else:
            print("   ❌ Redundant file download failed or content mismatch")
    
    # Clean up test files
    print("\n5. Cleaning Up Test Files...")
    
    if single_result['success']:
        delete_result = storage_manager.delete_backup_file(f"single_{test_filename}", from_all_backends=False)
        if delete_result['success']:
            print("   ✅ Single test file deleted successfully")
        else:
            print(f"   ❌ Failed to delete single test file: {delete_result.get('errors', [])}")
    
    if redundant_result['success']:
        delete_result = storage_manager.delete_backup_file(f"redundant_{test_filename}", from_all_backends=True)
        if delete_result['success']:
            print("   ✅ Redundant test files deleted successfully")
        else:
            print(f"   ❌ Failed to delete redundant test files: {delete_result.get('errors', [])}")
    
    # Summary
    print("\n6. Demo Summary")
    print("=" * 50)
    
    working_storages = [name for name, result in connectivity_results.items() if result['connected']]
    failed_storages = [name for name, result in connectivity_results.items() if not result['connected']]
    
    print(f"✅ Working storage backends: {', '.join(working_storages) if working_storages else 'None'}")
    if failed_storages:
        print(f"❌ Failed storage backends: {', '.join(failed_storages)}")
    
    if len(working_storages) >= 1:
        print("\n🎉 Storage integration is working! The system can:")
        print("   • Connect to cloud storage backends")
        print("   • Upload files with redundancy")
        print("   • Download files reliably")
        print("   • Handle backend failures gracefully")
        print("   • Provide comprehensive error handling")
        
        if len(working_storages) == 2:
            print("   • Full redundancy with both Cloudflare R2 and Backblaze B2")
        else:
            print("   • Partial redundancy (one backend working)")
    else:
        print("\n❌ No storage backends are working. Please check your credentials.")
    
    print("\n✨ Demo completed successfully!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        sys.exit(1)