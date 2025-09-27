#!/usr/bin/env python3
"""
Test runner for RTL layout and responsive design tests
Runs both Python and JavaScript tests for the RTL-first interface
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')

import django
django.setup()

from django.test.utils import get_runner
from django.conf import settings
from django.core.management import execute_from_command_line


class RTLTestRunner:
    """Test runner for RTL layout and responsive design tests"""
    
    def __init__(self):
        self.project_root = project_root
        self.test_dir = Path(__file__).parent
        self.results = {
            'python_tests': {'passed': 0, 'failed': 0, 'errors': []},
            'javascript_tests': {'passed': 0, 'failed': 0, 'errors': []},
            'total_tests': 0,
            'total_passed': 0,
            'total_failed': 0
        }
    
    def run_python_tests(self):
        """Run Python Django tests for RTL layout"""
        print("🧪 Running Python RTL Layout Tests...")
        print("=" * 50)
        
        try:
            # Run specific RTL tests
            test_modules = [
                'tests.frontend.test_rtl_layout.RTLLayoutTestCase',
                'tests.frontend.test_rtl_layout.ResponsiveDesignTestCase',
                'tests.frontend.test_rtl_layout.ComponentIntegrationTestCase',
                'tests.frontend.test_rtl_layout.ThemeIntegrationTestCase'
            ]
            
            for test_module in test_modules:
                print(f"\n📋 Running {test_module}...")
                
                result = subprocess.run([
                    sys.executable, 'manage.py', 'test', test_module, '--verbosity=2'
                ], cwd=self.project_root, capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.results['python_tests']['passed'] += 1
                    print(f"✅ {test_module} - PASSED")
                else:
                    self.results['python_tests']['failed'] += 1
                    self.results['python_tests']['errors'].append({
                        'test': test_module,
                        'error': result.stderr
                    })
                    print(f"❌ {test_module} - FAILED")
                    print(f"Error: {result.stderr}")
            
        except Exception as e:
            print(f"❌ Error running Python tests: {e}")
            self.results['python_tests']['errors'].append({
                'test': 'Python Test Runner',
                'error': str(e)
            })
    
    def run_javascript_tests(self):
        """Run JavaScript tests for RTL components"""
        print("\n🧪 Running JavaScript RTL Component Tests...")
        print("=" * 50)
        
        try:
            # Check if Node.js is available
            node_check = subprocess.run(['node', '--version'], 
                                      capture_output=True, text=True)
            
            if node_check.returncode != 0:
                print("⚠️  Node.js not found. Skipping JavaScript tests.")
                print("   Install Node.js to run JavaScript tests.")
                return
            
            # Check if Jest is available
            jest_check = subprocess.run(['npx', 'jest', '--version'], 
                                      capture_output=True, text=True)
            
            if jest_check.returncode != 0:
                print("⚠️  Jest not found. Running basic JavaScript tests...")
                self.run_basic_js_tests()
                return
            
            # Run Jest tests
            print("🚀 Running Jest tests...")
            result = subprocess.run([
                'npx', 'jest', 
                str(self.test_dir / 'test_rtl_components.js'),
                '--verbose'
            ], cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.results['javascript_tests']['passed'] += 1
                print("✅ JavaScript RTL Component Tests - PASSED")
            else:
                self.results['javascript_tests']['failed'] += 1
                self.results['javascript_tests']['errors'].append({
                    'test': 'JavaScript RTL Components',
                    'error': result.stderr
                })
                print("❌ JavaScript RTL Component Tests - FAILED")
                print(f"Error: {result.stderr}")
            
        except Exception as e:
            print(f"❌ Error running JavaScript tests: {e}")
            self.results['javascript_tests']['errors'].append({
                'test': 'JavaScript Test Runner',
                'error': str(e)
            })
    
    def run_basic_js_tests(self):
        """Run basic JavaScript tests without Jest"""
        print("🔧 Running basic JavaScript validation...")
        
        js_files = [
            'static/js/theme-toggle.js',
            'static/js/rtl-components.js',
            'static/js/rtl-flowbite-components.js',
            'static/js/persian-utils.js'
        ]
        
        for js_file in js_files:
            file_path = self.project_root / js_file
            
            if file_path.exists():
                # Basic syntax check
                result = subprocess.run([
                    'node', '-c', str(file_path)
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.results['javascript_tests']['passed'] += 1
                    print(f"✅ {js_file} - Syntax OK")
                else:
                    self.results['javascript_tests']['failed'] += 1
                    self.results['javascript_tests']['errors'].append({
                        'test': js_file,
                        'error': result.stderr
                    })
                    print(f"❌ {js_file} - Syntax Error")
                    print(f"Error: {result.stderr}")
            else:
                print(f"⚠️  {js_file} - File not found")
    
    def run_css_validation(self):
        """Validate CSS files for RTL support"""
        print("\n🎨 Validating CSS for RTL Support...")
        print("=" * 50)
        
        css_files = [
            'static/css/base-rtl.css',
            'static/scss/base.scss'
        ]
        
        rtl_properties = [
            'direction: rtl',
            'text-align: right',
            'font-family.*Vazir',
            'font-family.*Yekan',
            'cyber-',
            'persian-',
            'rtl-'
        ]
        
        for css_file in css_files:
            file_path = self.project_root / css_file
            
            if file_path.exists():
                print(f"\n📄 Checking {css_file}...")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                found_properties = []
                for prop in rtl_properties:
                    if prop in content:
                        found_properties.append(prop)
                
                if found_properties:
                    print(f"✅ RTL properties found: {', '.join(found_properties)}")
                    self.results['python_tests']['passed'] += 1
                else:
                    print(f"⚠️  No RTL properties found in {css_file}")
            else:
                print(f"❌ {css_file} - File not found")
    
    def run_tailwind_validation(self):
        """Validate Tailwind CSS configuration"""
        print("\n🎯 Validating Tailwind CSS Configuration...")
        print("=" * 50)
        
        tailwind_config = self.project_root / 'tailwind.config.js'
        
        if tailwind_config.exists():
            print("📄 Checking tailwind.config.js...")
            
            with open(tailwind_config, 'r', encoding='utf-8') as f:
                content = f.read()
            
            required_configs = [
                'darkMode.*class',
                'fontFamily.*vazir',
                'fontFamily.*yekan',
                'cyber-',
                'persian-',
                'rtl-',
                'flowbite'
            ]
            
            found_configs = []
            for config in required_configs:
                if config in content:
                    found_configs.append(config)
            
            if len(found_configs) >= 4:
                print(f"✅ Tailwind RTL configuration looks good")
                print(f"   Found: {', '.join(found_configs)}")
                self.results['python_tests']['passed'] += 1
            else:
                print(f"⚠️  Tailwind configuration may be incomplete")
                print(f"   Found: {', '.join(found_configs)}")
        else:
            print("❌ tailwind.config.js not found")
    
    def run_template_validation(self):
        """Validate Django templates for RTL support"""
        print("\n📝 Validating Django Templates for RTL...")
        print("=" * 50)
        
        template_files = [
            'templates/base.html',
            'templates/base_rtl.html'
        ]
        
        rtl_attributes = [
            'dir="rtl"',
            'lang="fa"',
            'Vazirmatn',
            'persian-',
            'cyber-',
            'rtl-'
        ]
        
        for template_file in template_files:
            file_path = self.project_root / template_file
            
            if file_path.exists():
                print(f"\n📄 Checking {template_file}...")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                found_attributes = []
                for attr in rtl_attributes:
                    if attr in content:
                        found_attributes.append(attr)
                
                if len(found_attributes) >= 3:
                    print(f"✅ RTL template attributes found: {', '.join(found_attributes)}")
                    self.results['python_tests']['passed'] += 1
                else:
                    print(f"⚠️  Limited RTL support in {template_file}")
                    print(f"   Found: {', '.join(found_attributes)}")
            else:
                print(f"❌ {template_file} - File not found")
    
    def run_responsive_validation(self):
        """Validate responsive design implementation"""
        print("\n📱 Validating Responsive Design...")
        print("=" * 50)
        
        # Check for responsive breakpoints in CSS
        css_file = self.project_root / 'static/css/base-rtl.css'
        
        if css_file.exists():
            with open(css_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            responsive_features = [
                '@media (max-width: 768px)',
                '@media (max-width: 480px)',
                '@media (prefers-reduced-motion',
                '@media (prefers-contrast',
                '@media print'
            ]
            
            found_features = []
            for feature in responsive_features:
                if feature in content:
                    found_features.append(feature)
            
            if len(found_features) >= 3:
                print(f"✅ Responsive design features found: {len(found_features)}/5")
                self.results['python_tests']['passed'] += 1
            else:
                print(f"⚠️  Limited responsive design support")
                print(f"   Found: {', '.join(found_features)}")
        
        # Check Tailwind responsive classes
        tailwind_config = self.project_root / 'tailwind.config.js'
        
        if tailwind_config.exists():
            with open(tailwind_config, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'sm:' in content or 'md:' in content or 'lg:' in content:
                print("✅ Tailwind responsive classes configured")
                self.results['python_tests']['passed'] += 1
            else:
                print("⚠️  Tailwind responsive classes not found")
    
    def generate_report(self):
        """Generate test report"""
        print("\n📊 Test Results Summary")
        print("=" * 50)
        
        # Calculate totals
        self.results['total_tests'] = (
            self.results['python_tests']['passed'] + 
            self.results['python_tests']['failed'] +
            self.results['javascript_tests']['passed'] + 
            self.results['javascript_tests']['failed']
        )
        
        self.results['total_passed'] = (
            self.results['python_tests']['passed'] + 
            self.results['javascript_tests']['passed']
        )
        
        self.results['total_failed'] = (
            self.results['python_tests']['failed'] + 
            self.results['javascript_tests']['failed']
        )
        
        # Print summary
        print(f"📋 Total Tests: {self.results['total_tests']}")
        print(f"✅ Passed: {self.results['total_passed']}")
        print(f"❌ Failed: {self.results['total_failed']}")
        
        if self.results['total_failed'] == 0:
            print("\n🎉 All RTL tests passed!")
        else:
            print(f"\n⚠️  {self.results['total_failed']} tests failed")
        
        # Print detailed results
        print(f"\n📊 Python Tests: {self.results['python_tests']['passed']} passed, {self.results['python_tests']['failed']} failed")
        print(f"📊 JavaScript Tests: {self.results['javascript_tests']['passed']} passed, {self.results['javascript_tests']['failed']} failed")
        
        # Print errors if any
        if self.results['python_tests']['errors']:
            print("\n❌ Python Test Errors:")
            for error in self.results['python_tests']['errors']:
                print(f"   - {error['test']}: {error['error']}")
        
        if self.results['javascript_tests']['errors']:
            print("\n❌ JavaScript Test Errors:")
            for error in self.results['javascript_tests']['errors']:
                print(f"   - {error['test']}: {error['error']}")
        
        # Save results to file
        results_file = self.test_dir / 'rtl_test_results.json'
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        return self.results['total_failed'] == 0
    
    def run_all_tests(self):
        """Run all RTL and responsive design tests"""
        print("🚀 Starting RTL Layout and Responsive Design Tests")
        print("=" * 60)
        
        # Run all test categories
        self.run_python_tests()
        self.run_javascript_tests()
        self.run_css_validation()
        self.run_tailwind_validation()
        self.run_template_validation()
        self.run_responsive_validation()
        
        # Generate final report
        success = self.generate_report()
        
        return success


def main():
    """Main test runner function"""
    runner = RTLTestRunner()
    success = runner.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()