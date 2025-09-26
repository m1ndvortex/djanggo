"""
Simple navigation integration test.
"""
import os
import django
from django.conf import settings

# Configure Django settings
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

from django.test import TestCase
from zargar.tenants.admin_models import SuperAdmin
from zargar.admin_panel.navigation import navigation_builder, breadcrumb_builder


class SimpleNavigationTestCase(TestCase):
    """Simple test for navigation integration."""
    
    def setUp(self):
        """Set up test data."""
        self.superadmin = SuperAdmin.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_active=True
        )
    
    def test_navigation_builder_works(self):
        """Test that navigation builder creates navigation items."""
        nav_items = navigation_builder.get_navigation_for_user(self.superadmin)
        
        # Should have at least one navigation item
        self.assertGreater(len(nav_items), 0)
        
        # Check that navigation items have required attributes
        for item in nav_items:
            self.assertTrue(hasattr(item, 'name'))
            self.assertTrue(hasattr(item, 'get_url'))
            self.assertTrue(hasattr(item, 'has_permission'))
    
    def test_url_generation_works(self):
        """Test that URL generation works for navigation items."""
        nav_items = navigation_builder.get_navigation_for_user(self.superadmin)
        
        for item in nav_items:
            url = item.get_url()
            # URL should not be empty or just '#'
            if item.url_name:  # Only test items that should have URLs
                self.assertIsNotNone(url)
                self.assertNotEqual(url, '')
    
    def test_breadcrumb_generation_works(self):
        """Test that breadcrumb generation works."""
        # Test with a known URL name
        breadcrumbs = breadcrumb_builder.get_breadcrumbs('admin_panel:dashboard')
        
        # Should return a list (even if empty)
        self.assertIsInstance(breadcrumbs, list)
    
    def test_permission_checking_works(self):
        """Test that permission checking works."""
        nav_items = navigation_builder.get_navigation_for_user(self.superadmin)
        
        # All items should be accessible to superadmin
        for item in nav_items:
            self.assertTrue(item.has_permission(self.superadmin))
    
    def test_navigation_structure_is_valid(self):
        """Test that navigation structure is valid."""
        nav_items = navigation_builder.get_navigation_for_user(self.superadmin)
        
        for item in nav_items:
            # Check that item has valid structure
            self.assertIsInstance(item.name, str)
            self.assertIsNotNone(item.children)
            self.assertIsInstance(item.children, list)
            
            # Check children structure
            for child in item.children:
                self.assertIsInstance(child.name, str)
                self.assertTrue(hasattr(child, 'get_url'))


if __name__ == '__main__':
    import unittest
    unittest.main()