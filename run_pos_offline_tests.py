#!/usr/bin/env python
"""
Docker-based test runner for POS offline sync system tests.
Runs comprehensive tests including heavy load testing with 100 concurrent operations.
"""
import os
import sys
import subprocess
import time
from datetime import datetime


def run_command(command, description, timeout=None):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"Command: {command}")
    print()
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=False,
            text=True,
            timeout=timeout
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result.returncode == 0:
            print(f"\n✅ {description} completed successfully in {duration:.2f}s")
            return True
        else:
            print(f"\n❌ {description} failed with exit code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"\n⏰ {description} timed out after {timeout}s")
        return False
    except Exception as e:
        print(f"\n💥 {description} failed with exception: {e}")
        return False


def main():
    """Main test runner function."""
    print("=" * 80)
    print("POS OFFLINE SYNC SYSTEM - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test configuration
    tests = [
        {
            'name': 'Basic Offline POS System Test',
            'command': 'docker-compose -f docker-compose.test.yml run --rm web python test_offline_pos_simple.py',
            'timeout': 300,  # 5 minutes
            'description': 'Tests basic offline POS functionality with real database'
        },
        {
            'name': 'Offline API Endpoints Test',
            'command': 'docker-compose -f docker-compose.test.yml run --rm web python test_offline_api_simple.py',
            'timeout': 300,  # 5 minutes
            'description': 'Tests offline API endpoints with authentication'
        },
        {
            'name': 'Comprehensive Offline Sync Test',
            'command': 'docker-compose -f docker-compose.test.yml run --rm web python -m pytest tests/test_pos_offline_sync_comprehensive.py -v --tb=short',
            'timeout': 1800,  # 30 minutes
            'description': 'Comprehensive tests with real tenants, API, and database operations'
        },
        {
            'name': 'API Integration Test',
            'command': 'docker-compose -f docker-compose.test.yml run --rm web python -m pytest tests/test_pos_offline_api_integration.py -v --tb=short',
            'timeout': 900,  # 15 minutes
            'description': 'Real API integration tests with HTTP requests and authentication'
        },
        {
            'name': 'Heavy Load Test - 100 Concurrent Operations',
            'command': 'docker-compose -f docker-compose.test.yml run --rm web python -m pytest tests/test_pos_offline_heavy_load_100_concurrent.py -v --tb=short -s',
            'timeout': 2400,  # 40 minutes
            'description': 'Heavy load test with 100 concurrent sync operations'
        }
    ]
    
    # Pre-test setup
    print("🏗️ Setting up test environment...")
    
    setup_commands = [
        {
            'name': 'Build Docker Images',
            'command': 'docker-compose -f docker-compose.test.yml build',
            'timeout': 600,  # 10 minutes
            'description': 'Building Docker images for testing'
        },
        {
            'name': 'Start Test Services',
            'command': 'docker-compose -f docker-compose.test.yml up -d db redis',
            'timeout': 120,  # 2 minutes
            'description': 'Starting database and Redis services'
        },
        {
            'name': 'Wait for Services',
            'command': 'timeout /t 10 /nobreak' if os.name == 'nt' else 'sleep 10',
            'timeout': 15,
            'description': 'Waiting for services to be ready'
        },
        {
            'name': 'Run Migrations',
            'command': 'docker-compose -f docker-compose.test.yml run --rm web python manage.py migrate',
            'timeout': 300,  # 5 minutes
            'description': 'Running database migrations'
        },
        {
            'name': 'Create Test Tenants',
            'command': 'docker-compose -f docker-compose.test.yml run --rm web python manage.py shell -c "from django_tenants.utils import get_tenant_model; from zargar.tenants.models import Domain; Tenant = get_tenant_model(); tenant = Tenant.objects.create(schema_name=\'test_main\', name=\'Test Main Tenant\', owner_name=\'Test Owner\', owner_email=\'test@example.com\'); tenant.create_schema(check_if_exists=True); domain = Domain.objects.create(domain=\'test.main.com\', tenant=tenant, is_primary=True); print(f\'Created tenant: {tenant.name} with domain: {domain.domain}\')"',
            'timeout': 180,  # 3 minutes
            'description': 'Creating test tenants'
        }
    ]
    
    # Run setup commands
    setup_success = True
    for setup in setup_commands:
        if not run_command(setup['command'], setup['description'], setup['timeout']):
            setup_success = False
            break
    
    if not setup_success:
        print("\n❌ Test setup failed. Aborting test run.")
        return False
    
    print("\n✅ Test environment setup completed successfully!")
    
    # Run tests
    test_results = []
    total_start_time = time.time()
    
    for i, test in enumerate(tests, 1):
        print(f"\n🧪 Running Test {i}/{len(tests)}: {test['name']}")
        print(f"📝 {test['description']}")
        
        success = run_command(
            test['command'],
            f"Test {i}: {test['name']}",
            test['timeout']
        )
        
        test_results.append({
            'name': test['name'],
            'success': success,
            'description': test['description']
        })
        
        if not success:
            print(f"\n⚠️ Test {i} failed, but continuing with remaining tests...")
    
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    # Cleanup
    print(f"\n🧹 Cleaning up test environment...")
    cleanup_commands = [
        'docker-compose -f docker-compose.test.yml down -v',
        'docker system prune -f'
    ]
    
    for cleanup_cmd in cleanup_commands:
        run_command(cleanup_cmd, f"Cleanup: {cleanup_cmd}", 120)
    
    # Print final results
    print("\n" + "=" * 80)
    print("FINAL TEST RESULTS")
    print("=" * 80)
    print(f"Total test duration: {total_duration:.2f}s ({total_duration/60:.1f} minutes)")
    print()
    
    passed_tests = sum(1 for result in test_results if result['success'])
    failed_tests = len(test_results) - passed_tests
    
    for i, result in enumerate(test_results, 1):
        status = "✅ PASSED" if result['success'] else "❌ FAILED"
        print(f"{i}. {status} - {result['name']}")
        print(f"   {result['description']}")
    
    print(f"\n📊 Summary:")
    print(f"   Total tests: {len(test_results)}")
    print(f"   Passed: {passed_tests}")
    print(f"   Failed: {failed_tests}")
    print(f"   Success rate: {passed_tests/len(test_results)*100:.1f}%")
    
    if failed_tests == 0:
        print(f"\n🎉 All tests passed successfully!")
        print(f"✅ POS offline sync system is ready for production!")
        return True
    else:
        print(f"\n⚠️ {failed_tests} test(s) failed.")
        print(f"❌ Please review and fix issues before production deployment.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)