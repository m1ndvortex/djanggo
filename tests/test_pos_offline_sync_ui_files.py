"""
File-based tests for POS offline sync UI functionality (Task 12.4).
Tests the frontend components without Django dependencies.
"""
import os
import unittest


class POSOfflineSyncUIFilesTest(unittest.TestCase):
    """Test POS offline sync UI files exist and have correct content."""
    
    def test_offline_sync_status_component_exists(self):
        """Test that offline sync status component file exists."""
        file_path = 'templates/pos/components/offline_sync_status.html'
        self.assertTrue(os.path.exists(file_path), f"File {file_path} should exist")
        
        # Check file has content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertGreater(len(content), 1000, "File should have substantial content")
            
            # Check for key elements
            self.assertIn('offline-sync-status', content)
            self.assertIn('connection-indicator', content)
            self.assertIn('آنلاین', content)
            self.assertIn('آفلاین', content)
    
    def test_sync_queue_modal_component_exists(self):
        """Test that sync queue modal component file exists."""
        file_path = 'templates/pos/components/sync_queue_modal.html'
        self.assertTrue(os.path.exists(file_path), f"File {file_path} should exist")
        
        # Check file has content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertGreater(len(content), 1000, "File should have substantial content")
            
            # Check for key elements
            self.assertIn('sync-queue-modal', content)
            self.assertIn('مدیریت صف همگام‌سازی', content)
            self.assertIn('همگام‌سازی همه', content)
    
    def test_conflict_resolution_modal_component_exists(self):
        """Test that conflict resolution modal component file exists."""
        file_path = 'templates/pos/components/conflict_resolution_modal.html'
        self.assertTrue(os.path.exists(file_path), f"File {file_path} should exist")
        
        # Check file has content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertGreater(len(content), 1000, "File should have substantial content")
            
            # Check for key elements
            self.assertIn('conflict-resolution-modal', content)
            self.assertIn('حل تعارض همگام‌سازی', content)
            self.assertIn('استفاده از داده محلی', content)
    
    def test_offline_sync_javascript_exists(self):
        """Test that offline sync JavaScript file exists."""
        file_path = 'static/js/pos-offline-sync.js'
        self.assertTrue(os.path.exists(file_path), f"File {file_path} should exist")
        
        # Check file has content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertGreater(len(content), 1000, "File should have substantial content")
            
            # Check for main class and methods
            self.assertIn('class POSOfflineSync', content)
            self.assertIn('init()', content)
            self.assertIn('performSync()', content)
    
    def test_pos_interface_css_updated(self):
        """Test that POS interface CSS file exists and has offline sync styles."""
        file_path = 'static/css/pos-interface.css'
        self.assertTrue(os.path.exists(file_path), f"File {file_path} should exist")
        
        # Check file has offline sync styles
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('offline-sync-status', content)
            self.assertIn('sync-queue-modal', content)
            self.assertIn('conflict-resolution-modal', content)
    
    def test_touch_interface_includes_offline_components(self):
        """Test that touch interface includes offline sync components."""
        file_path = 'templates/pos/touch_interface.html'
        self.assertTrue(os.path.exists(file_path), f"File {file_path} should exist")
        
        # Check includes
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('offline_sync_status.html', content)
            self.assertIn('sync_queue_modal.html', content)
            self.assertIn('conflict_resolution_modal.html', content)
            self.assertIn('openSyncQueue()', content)
    
    def test_persian_localization_coverage(self):
        """Test Persian localization in UI components."""
        files_to_check = [
            'templates/pos/components/offline_sync_status.html',
            'templates/pos/components/sync_queue_modal.html',
            'templates/pos/components/conflict_resolution_modal.html'
        ]
        
        # Persian texts that should be present
        persian_texts = [
            'آنلاین',
            'آفلاین', 
            'در حال همگام‌سازی',
            'صف همگام‌سازی',
            'همگام‌سازی دستی',
            'خطا در همگام‌سازی'
        ]
        
        for file_path in files_to_check:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Check that at least some Persian texts are present
                persian_found = sum(1 for text in persian_texts if text in content)
                self.assertGreaterEqual(persian_found, 2, f"File {file_path} should contain Persian text")
    
    def test_theme_support_classes(self):
        """Test CSS classes for dual theme support."""
        files_to_check = [
            'templates/pos/components/offline_sync_status.html',
            'templates/pos/components/sync_queue_modal.html',
            'templates/pos/components/conflict_resolution_modal.html'
        ]
        
        # Theme classes that should be present
        theme_classes = [
            'cyber-bg-surface',
            'cyber-neon-primary',
            '{% if is_dark_mode %}'
        ]
        
        for file_path in files_to_check:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Check that theme support is present
                theme_found = sum(1 for cls in theme_classes if cls in content)
                self.assertGreaterEqual(theme_found, 2, f"File {file_path} should have theme support")
    
    def test_responsive_design_classes(self):
        """Test responsive design classes for mobile/tablet optimization."""
        files_to_check = [
            'templates/pos/components/offline_sync_status.html',
            'templates/pos/components/sync_queue_modal.html',
            'templates/pos/components/conflict_resolution_modal.html'
        ]
        
        # Responsive classes that should be present
        responsive_classes = [
            'flex',
            'space-',
            'p-',
            'rounded',
            'transition'
        ]
        
        for file_path in files_to_check:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Check that responsive design is present
                responsive_found = sum(1 for cls in responsive_classes if cls in content)
                self.assertGreaterEqual(responsive_found, 3, f"File {file_path} should have responsive design")
    
    def test_javascript_component_functions(self):
        """Test that JavaScript components have required functions."""
        file_path = 'templates/pos/components/offline_sync_status.html'
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Check for Alpine.js components and functions
            required_functions = [
                'offlineSyncStatus()',
                'loadOfflineQueue()',
                'manualSync()',
                'performSync()',
                'formatCurrency('
            ]
            
            function_found = sum(1 for function in required_functions if function in content)
            self.assertGreaterEqual(function_found, 3, "Should have key JavaScript functions")
    
    def test_javascript_file_structure(self):
        """Test that JavaScript file has proper structure."""
        file_path = 'static/js/pos-offline-sync.js'
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Check for main class and methods
            required_elements = [
                'class POSOfflineSync',
                'init()',
                'setupEventListeners()',
                'loadOfflineQueue()',
                'performSync()',
                'window.POSOfflineSync'
            ]
            
            for element in required_elements:
                self.assertIn(element, content, f"Element '{element}' should be in JavaScript file")
    
    def test_css_offline_sync_styles(self):
        """Test that CSS file includes offline sync styles."""
        file_path = 'static/css/pos-interface.css'
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Check for offline sync specific styles
            required_styles = [
                '.offline-sync-status',
                '.connection-indicator',
                '.sync-queue-modal',
                '.conflict-resolution-modal'
            ]
            
            for style in required_styles:
                self.assertIn(style, content, f"Style '{style}' should be in CSS file")
    
    def test_all_files_have_substantial_content(self):
        """Test that all created files have substantial content."""
        files_to_check = [
            ('templates/pos/components/offline_sync_status.html', 15000),
            ('templates/pos/components/sync_queue_modal.html', 40000),
            ('templates/pos/components/conflict_resolution_modal.html', 30000),
            ('static/js/pos-offline-sync.js', 10000),
        ]
        
        for file_path, min_size in files_to_check:
            self.assertTrue(os.path.exists(file_path), f"File {file_path} should exist")
            
            file_size = os.path.getsize(file_path)
            self.assertGreater(file_size, min_size, 
                             f"File {file_path} should be at least {min_size} bytes, got {file_size}")


if __name__ == '__main__':
    unittest.main()