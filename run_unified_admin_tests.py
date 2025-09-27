#!/usr/bin/env python
"""
Test runner script for unified admin system comprehensive testing.
This script runs all tests required for task 6.1 with proper Docker integration.
"""
import os
import sys
import subprocess
import argparse
import time
from pathlib import Path


class UnifiedAdminTestRunner:
    """
    Comprehensive test runner for unified admin system.
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_categories = {
            'auth': 'Authentication and authorization tests',
            'dashboard': 'Dashboard functionality tests',
            'security': 'Security and tenant isolation tests',
            'performance': 'Performance and load tests',
            'integration': 'Integration tests for all features',
            'playwright': 'End-to-end browser tests',
            'unit': 'Unit tests for individual components',
            'coverage': 'Code coverage analysis',
            'all': 'All test categories'
        }
    
    def run_command(self, command, description=""):
        """Run a command and handle output."""
        print(f"\n{'='*60}")
        print(f"Running: {description or command}")
        print(f"{'='*60}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                capture_output=False,
                text=True,
                cwd=self.project_root
            )
            print(f"✅ Success: {description or command}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed: {description or command}")
            print(f"Error code: {e.returncode}")
            return False
    
    def setup_test_environment(self):
        """Set up the test environment."""
        print("🔧 Setting up test environment...")
        
        # Build Docker images
        if not self.run_command(
            "docker-compose -f docker-compose.test.yml build",
            "Building test Docker images"
        ):
            return False
        
        # Start database and Redis
        if not self.run_command(
            "docker-compose -f docker-compose.test.yml up -d db redis",
            "Starting database and Redis services"
        ):
            return False
        
        # Wait for services to be ready
        print("⏳ Waiting for services to be ready...")
        time.sleep(10)
        
        return True
    
    def run_authentication_tests(self):
        """Run authentication and authorization tests."""
        return self.run_command(
            "docker-compose -f docker-compose.test.yml run --rm test-auth",
            "Authentication and authorization tests"
        )
    
    def run_dashboard_tests(self):
        """Run dashboard functionality tests."""
        return self.run_command(
            "docker-compose -f docker-compose.test.yml run --rm test-dashboard",
            "Dashboard functionality tests"
        )
    
    def run_security_tests(self):
        """Run security and tenant isolation tests."""
        return self.run_command(
            "docker-compose -f docker-compose.test.yml run --rm test-security",
            "Security and tenant isolation tests"
        )
    
    def run_performance_tests(self):
        """Run performance and load tests."""
        return self.run_command(
            "docker-compose -f docker-compose.test.yml run --rm test-performance",
            "Performance and load tests"
        )
    
    def run_integration_tests(self):
        """Run integration tests for all features."""
        return self.run_command(
            "docker-compose -f docker-compose.test.yml run --rm test-integration",
            "Integration tests for all features"
        )
    
    def run_playwright_tests(self):
        """Run end-to-end browser tests."""
        return self.run_command(
            "docker-compose -f docker-compose.test.yml run --rm test-playwright",
            "End-to-end browser tests with Playwright"
        )
    
    def run_unit_tests(self):
        """Run unit tests for individual components."""
        return self.run_command(
            "docker-compose -f docker-compose.test.yml run --rm web python -m pytest tests/test_unified_admin_unit.py -v --tb=short",
            "Unit tests for individual components"
        )
    
    def run_coverage_analysis(self):
        """Run code coverage analysis."""
        return self.run_command(
            "docker-compose -f docker-compose.test.yml run --rm test-coverage",
            "Code coverage analysis (target: 95%)"
        )
    
    def run_all_tests(self):
        """Run all test categories."""
        print("🚀 Running comprehensive unified admin test suite...")
        
        test_methods = [
            ('Authentication Tests', self.run_authentication_tests),
            ('Dashboard Tests', self.run_dashboard_tests),
            ('Security Tests', self.run_security_tests),
            ('Performance Tests', self.run_performance_tests),
            ('Integration Tests', self.run_integration_tests),
            ('Unit Tests', self.run_unit_tests),
            ('Playwright E2E Tests', self.run_playwright_tests),
            ('Coverage Analysis', self.run_coverage_analysis),
        ]
        
        results = {}
        for test_name, test_method in test_methods:
            print(f"\n🔍 Starting {test_name}...")
            results[test_name] = test_method()
        
        # Print summary
        self.print_test_summary(results)
        
        # Return overall success
        return all(results.values())
    
    def print_test_summary(self, results):
        """Print test results summary."""
        print(f"\n{'='*80}")
        print("📊 UNIFIED ADMIN TEST SUITE SUMMARY")
        print(f"{'='*80}")
        
        total_tests = len(results)
        passed_tests = sum(1 for result in results.values() if result)
        failed_tests = total_tests - passed_tests
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name:<30} {status}")
        
        print(f"\n📈 Overall Results:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests == 0:
            print("\n🎉 ALL TESTS PASSED! Unified admin system is ready for deployment.")
        else:
            print(f"\n⚠️  {failed_tests} test category(ies) failed. Please review and fix issues.")
        
        print(f"{'='*80}")
    
    def cleanup_test_environment(self):
        """Clean up test environment."""
        print("\n🧹 Cleaning up test environment...")
        self.run_command(
            "docker-compose -f docker-compose.test.yml down -v",
            "Stopping and removing test containers"
        )
    
    def run_specific_category(self, category):
        """Run tests for a specific category."""
        category_methods = {
            'auth': self.run_authentication_tests,
            'dashboard': self.run_dashboard_tests,
            'security': self.run_security_tests,
            'performance': self.run_performance_tests,
            'integration': self.run_integration_tests,
            'playwright': self.run_playwright_tests,
            'unit': self.run_unit_tests,
            'coverage': self.run_coverage_analysis,
            'all': self.run_all_tests
        }
        
        if category not in category_methods:
            print(f"❌ Unknown test category: {category}")
            print(f"Available categories: {', '.join(self.test_categories.keys())}")
            return False
        
        print(f"🎯 Running {category} tests: {self.test_categories[category]}")
        return category_methods[category]()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive test runner for unified admin system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Categories:
  auth         - Authentication and authorization tests
  dashboard    - Dashboard functionality tests  
  security     - Security and tenant isolation tests
  performance  - Performance and load tests
  integration  - Integration tests for all features
  playwright   - End-to-end browser tests
  unit         - Unit tests for individual components
  coverage     - Code coverage analysis
  all          - All test categories (default)

Examples:
  python run_unified_admin_tests.py                    # Run all tests
  python run_unified_admin_tests.py --category auth    # Run only auth tests
  python run_unified_admin_tests.py --no-cleanup      # Keep containers after tests
  python run_unified_admin_tests.py --setup-only      # Only setup environment
        """
    )
    
    parser.add_argument(
        '--category',
        choices=['auth', 'dashboard', 'security', 'performance', 'integration', 
                'playwright', 'unit', 'coverage', 'all'],
        default='all',
        help='Test category to run (default: all)'
    )
    
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='Skip cleanup of test environment'
    )
    
    parser.add_argument(
        '--setup-only',
        action='store_true',
        help='Only setup test environment, do not run tests'
    )
    
    parser.add_argument(
        '--skip-setup',
        action='store_true',
        help='Skip environment setup (assume already running)'
    )
    
    args = parser.parse_args()
    
    runner = UnifiedAdminTestRunner()
    
    try:
        # Setup environment
        if not args.skip_setup:
            if not runner.setup_test_environment():
                print("❌ Failed to setup test environment")
                return 1
        
        if args.setup_only:
            print("✅ Test environment setup complete")
            return 0
        
        # Run tests
        success = runner.run_specific_category(args.category)
        
        # Cleanup
        if not args.no_cleanup:
            runner.cleanup_test_environment()
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        if not args.no_cleanup:
            runner.cleanup_test_environment()
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if not args.no_cleanup:
            runner.cleanup_test_environment()
        return 1


if __name__ == '__main__':
    sys.exit(main())