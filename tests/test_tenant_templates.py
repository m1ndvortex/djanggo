"""
Simple tests to verify tenant management templates exist and are valid.
"""

import os
from django.test import TestCase
from django.template.loader import get_template
from django.template import TemplateDoesNotExist


class TenantTemplateTest(TestCase):
    """Test that tenant management templates exist and are valid."""
    
    def test_base_admin_template_exists(self):
        """Test that base admin template exists."""
        try:
            template = get_template('admin/base_admin.html')
            self.assertIsNotNone(template)
        except TemplateDoesNotExist:
            self.fail("admin/base_admin.html template does not exist")
    
    def test_tenant_list_template_exists(self):
        """Test that tenant list template exists."""
        try:
            template = get_template('admin/tenants/tenant_list.html')
            self.assertIsNotNone(template)
        except TemplateDoesNotExist:
            self.fail("admin/tenants/tenant_list.html template does not exist")
    
    def test_tenant_create_template_exists(self):
        """Test that tenant create template exists."""
        try:
            template = get_template('admin/tenants/tenant_create.html')
            self.assertIsNotNone(template)
        except TemplateDoesNotExist:
            self.fail("admin/tenants/tenant_create.html template does not exist")
    
    def test_tenant_detail_template_exists(self):
        """Test that tenant detail template exists."""
        try:
            template = get_template('admin/tenants/tenant_detail.html')
            self.assertIsNotNone(template)
        except TemplateDoesNotExist:
            self.fail("admin/tenants/tenant_detail.html template does not exist")
    
    def test_tenant_update_template_exists(self):
        """Test that tenant update template exists."""
        try:
            template = get_template('admin/tenants/tenant_update.html')
            self.assertIsNotNone(template)
        except TemplateDoesNotExist:
            self.fail("admin/tenants/tenant_update.html template does not exist")
    
    def test_tenant_delete_template_exists(self):
        """Test that tenant delete template exists."""
        try:
            template = get_template('admin/tenants/tenant_delete.html')
            self.assertIsNotNone(template)
        except TemplateDoesNotExist:
            self.fail("admin/tenants/tenant_delete.html template does not exist")
    
    def test_tenant_list_partial_template_exists(self):
        """Test that tenant list partial template exists."""
        try:
            template = get_template('admin/tenants/tenant_list_partial.html')
            self.assertIsNotNone(template)
        except TemplateDoesNotExist:
            self.fail("admin/tenants/tenant_list_partial.html template does not exist")
    
    def test_static_files_exist(self):
        """Test that static files exist."""
        static_files = [
            'static/css/tenant-management.css',
            'static/js/tenant-management.js'
        ]
        
        for file_path in static_files:
            self.assertTrue(
                os.path.exists(file_path),
                f"Static file {file_path} does not exist"
            )
    
    def test_template_syntax_valid(self):
        """Test that templates have valid syntax."""
        templates = [
            'admin/base_admin.html',
            'admin/tenants/tenant_list.html',
            'admin/tenants/tenant_create.html',
            'admin/tenants/tenant_detail.html',
            'admin/tenants/tenant_update.html',
            'admin/tenants/tenant_delete.html',
            'admin/tenants/tenant_list_partial.html'
        ]
        
        for template_name in templates:
            try:
                template = get_template(template_name)
                # Try to render with minimal context
                rendered = template.render({
                    'user': None,
                    'request': None,
                    'tenant': None,
                    'tenants': [],
                    'form': None,
                    'total_tenants': 0,
                    'active_tenants': 0,
                    'inactive_tenants': 0,
                    'recent_signups': 0,
                    'subscription_plans': [],
                    'domains': [],
                    'recent_logs': [],
                    'schema_exists': True,
                    'tenant_stats': {},
                })
                self.assertIsNotNone(rendered)
            except Exception as e:
                self.fail(f"Template {template_name} has syntax errors: {e}")


class TenantManagementFilesTest(TestCase):
    """Test that all required files for tenant management exist."""
    
    def test_template_files_exist(self):
        """Test that all template files exist."""
        template_files = [
            'templates/admin/base_admin.html',
            'templates/admin/tenants/tenant_list.html',
            'templates/admin/tenants/tenant_create.html',
            'templates/admin/tenants/tenant_detail.html',
            'templates/admin/tenants/tenant_update.html',
            'templates/admin/tenants/tenant_delete.html',
            'templates/admin/tenants/tenant_list_partial.html'
        ]
        
        for file_path in template_files:
            self.assertTrue(
                os.path.exists(file_path),
                f"Template file {file_path} does not exist"
            )
    
    def test_static_files_exist(self):
        """Test that all static files exist."""
        static_files = [
            'static/css/tenant-management.css',
            'static/js/tenant-management.js'
        ]
        
        for file_path in static_files:
            self.assertTrue(
                os.path.exists(file_path),
                f"Static file {file_path} does not exist"
            )
    
    def test_template_content_has_persian_text(self):
        """Test that templates contain Persian text."""
        template_files = [
            'templates/admin/tenants/tenant_list.html',
            'templates/admin/tenants/tenant_create.html',
            'templates/admin/tenants/tenant_detail.html',
        ]
        
        persian_keywords = [
            'مدیریت تنانت',
            'ایجاد تنانت',
            'فروشگاه',
            'مالک',
            'فعال',
            'غیرفعال'
        ]
        
        for file_path in template_files:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for at least one Persian keyword
                has_persian = any(keyword in content for keyword in persian_keywords)
                self.assertTrue(
                    has_persian,
                    f"Template {file_path} does not contain Persian text"
                )
    
    def test_template_content_has_rtl_attributes(self):
        """Test that templates contain RTL attributes."""
        template_files = [
            'templates/admin/base_admin.html',
            'templates/admin/tenants/tenant_list.html',
        ]
        
        rtl_attributes = [
            'dir="rtl"',
            'lang="fa"'
        ]
        
        for file_path in template_files:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for RTL attributes
                has_rtl = any(attr in content for attr in rtl_attributes)
                self.assertTrue(
                    has_rtl,
                    f"Template {file_path} does not contain RTL attributes"
                )
    
    def test_css_file_has_cybersecurity_theme(self):
        """Test that CSS file contains cybersecurity theme classes."""
        css_file = 'static/css/tenant-management.css'
        
        if os.path.exists(css_file):
            with open(css_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            cyber_classes = [
                'cyber-glass',
                'cyber-card',
                'cyber-button',
                'cyber-neon-primary',
                'cyber-bg-surface'
            ]
            
            for css_class in cyber_classes:
                self.assertIn(
                    css_class,
                    content,
                    f"CSS file does not contain {css_class} class"
                )
    
    def test_javascript_file_has_required_functions(self):
        """Test that JavaScript file contains required functions."""
        js_file = 'static/js/tenant-management.js'
        
        if os.path.exists(js_file):
            with open(js_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            required_functions = [
                'TenantManagement',
                'showTenantStats',
                'handleBulkAction',
                'formatPersianNumber'
            ]
            
            for function_name in required_functions:
                self.assertIn(
                    function_name,
                    content,
                    f"JavaScript file does not contain {function_name} function"
                )