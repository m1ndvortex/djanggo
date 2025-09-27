#!/usr/bin/env python
"""
Script to run supplier management backend tests using Docker.
"""
import subprocess
import sys
import os

def run_docker_command(command):
    """Run a command in Docker container."""
    docker_cmd = [
        'docker-compose', 'exec', 'web', 'python', 'manage.py'
    ] + command
    
    print(f"Running: {' '.join(docker_cmd)}")
    result = subprocess.run(docker_cmd, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    return result.returncode == 0

def main():
    """Main function to run supplier management tests."""
    print("=" * 60)
    print("ZARGAR Jewelry SaaS - Supplier Management Backend Tests")
    print("=" * 60)
    
    # Check if Docker is running
    try:
        subprocess.run(['docker', '--version'], check=True, capture_output=True)
        print("✓ Docker is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ Docker is not available or not running")
        sys.exit(1)
    
    # Check if docker-compose is available
    try:
        subprocess.run(['docker-compose', '--version'], check=True, capture_output=True)
        print("✓ Docker Compose is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ Docker Compose is not available")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Running Supplier Management Backend Tests")
    print("=" * 60)
    
    # Test commands to run
    test_commands = [
        # Run specific supplier management tests
        ['test', 'tests.test_supplier_management_backend', '-v', '2'],
        
        # Run customer app tests (includes supplier models)
        ['test', 'zargar.customers.tests', '-v', '2'],
        
        # Check migrations
        ['makemigrations', '--check', '--dry-run'],
        
        # Validate models
        ['check'],
    ]
    
    all_passed = True
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"\n[{i}/{len(test_commands)}] Running: {' '.join(cmd)}")
        print("-" * 40)
        
        success = run_docker_command(cmd)
        
        if success:
            print(f"✓ Test {i} passed")
        else:
            print(f"✗ Test {i} failed")
            all_passed = False
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    if all_passed:
        print("✓ All supplier management backend tests passed!")
        print("\nImplemented features:")
        print("- Supplier management with contact and payment terms")
        print("- Purchase order workflow with delivery tracking")
        print("- Supplier payment management and approval workflow")
        print("- Delivery scheduling and tracking system")
        print("- Supplier performance metrics and reporting")
        print("- Comprehensive API endpoints with filtering and search")
        print("- Complete test coverage for all functionality")
        
        return 0
    else:
        print("✗ Some tests failed. Please check the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())