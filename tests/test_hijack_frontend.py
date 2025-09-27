"""
Frontend tests for django-hijack UI integration and user experience.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing Django modules
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.test')
    django.setup()

import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup
import json

from zargar.tenants.admin_models import SuperAdmin
from zargar.tenants.models import Tenant, Domain
from zargar.admin_panel.models import ImpersonationSession
from zargar.core.models import User

User = get_user_model()


@pytest.mark.django_db
class HijackFrontendTestCase(TestCase):
    """Test frontend aspects of the hijack integration."""
    
    def setUp(self):
        """Set up test data."""
        # Create test tenant
        self.tenant = Tenant.objects.create(
            schema_name='test_tenant',
            name='Test Jewelry Shop',
            owner_name='Test Owner',
            owner_email='owner@test.com',
            is_active=True
        )
        self.domain = Domain.objects.create(
            domain='test.zargar.com',
            tenant=self.tenant,
            is_primary=True
        )
        
        # Create super admin
        self.super_admin = SuperAdmin.objects.create_superuser(
            username='superadmin',
            email='admin@zargar.com',
            password='secure_password_123'
        )
        
        # Create regular tenant users (in tenant schema)
        from django_tenants.utils import schema_context
        with schema_context(self.tenant.schema_name):
            self.tenant_owner = User.objects.create_user(
                username='owner',
                email='owner@test.com',
                password='password123',
                role='owner',
                first_name='Shop',
                last_name='Owner'
            )
            
            self.tenant_user = User.objects.create_user(
                username='employee',
                email='employee@test.com',
                password='password123',
                role='salesperson',
                first_name='Test',
                last_name='Employee'
            )
            
            self.inactive_user = User.objects.create_user(
                username='inactive',
                email='inactive@test.com',
                password='password123',
                is_active=False
            )
        
        self.client = Client()
    
    def test_impersonation_page_renders_correctly(self):
        """Test that the impersonation page renders with correct elements."""
        # Login as super admin
        self.client.login(username='superadmin', password='secure_password_123')
        
        # Get impersonation page
        response = self.client.get(reverse('admin_panel:user_impersonation'))
        self.assertEqual(response.status_code, 200)
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check for key elements
        self.assertIsNotNone(soup.find('h1', string=lambda text: 'User Impersonation' in text if text else False))
        self.assertIsNotNone(soup.find('div', class_='search-container'))
        self.assertIsNotNone(soup.find('input', {'id': 'userSearch'}))
        self.assertIsNotNone(soup.find('select', {'id': 'tenantFilter'}))
        self.assertIsNotNone(soup.find('select', {'id': 'roleFilter'}))
        
        # Check for django-hijack integration notice
        hijack_notice = soup.find('div', class_='hijack-integration')
        self.assertIsNotNone(hijack_notice)
        self.assertIn('Django-Hijack Integration', hijack_notice.get_text())
        
        # Check for user cards
        user_cards = soup.find_all('div', class_='user-card')
        self.assertGreater(len(user_cards), 0)
        
        # Check for impersonate buttons
        impersonate_buttons = soup.find_all('button', class_='impersonate-btn')
        self.assertGreater(len(impersonate_buttons), 0)
    
    def test_impersonation_modal_functionality(self):
        """Test that the impersonation modal contains correct elements."""
        # Login as super admin
        self.client.login(username='superadmin', password='secure_password_123')
        
        # Get impersonation page
        response = self.client.get(reverse('admin_panel:user_impersonation'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check modal exists
        modal = soup.find('div', {'id': 'impersonationModal'})
        self.assertIsNotNone(modal)
        
        # Check modal form
        form = modal.find('form', {'id': 'impersonationForm'})
        self.assertIsNotNone(form)
        self.assertEqual(form.get('action'), reverse('admin_panel:start_impersonation'))
        
        # Check form fields
        self.assertIsNotNone(form.find('input', {'name': 'user_id'}))
        self.assertIsNotNone(form.find('input', {'name': 'tenant_schema'}))
        self.assertIsNotNone(form.find('textarea', {'name': 'reason'}))
        
        # Check security warnings
        security_warning = modal.find('div', class_='bg-red-50')
        self.assertIsNotNone(security_warning)
        self.assertIn('Security Warning', security_warning.get_text())
        
        # Check django-hijack notice in modal
        hijack_notice = modal.find('div', class_='bg-blue-50')
        self.assertIsNotNone(hijack_notice)
        self.assertIn('Django-Hijack', hijack_notice.get_text())
    
    def test_user_search_and_filtering_elements(self):
        """Test that search and filtering elements are present."""
        # Login as super admin
        self.client.login(username='superadmin', password='secure_password_123')
        
        # Get impersonation page
        response = self.client.get(reverse('admin_panel:user_impersonation'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check search input
        search_input = soup.find('input', {'id': 'userSearch'})
        self.assertIsNotNone(search_input)
        self.assertEqual(search_input.get('placeholder'), 'Enter username or email...')
        
        # Check tenant filter
        tenant_filter = soup.find('select', {'id': 'tenantFilter'})
        self.assertIsNotNone(tenant_filter)
        options = tenant_filter.find_all('option')
        self.assertGreater(len(options), 1)  # Should have "All Tenants" + actual tenants
        
        # Check role filter
        role_filter = soup.find('select', {'id': 'roleFilter'})
        self.assertIsNotNone(role_filter)
        role_options = role_filter.find_all('option')
        expected_roles = ['All Roles', 'Owner', 'Accountant', 'Salesperson']
        actual_roles = [option.get_text().strip() for option in role_options]
        for role in expected_roles:
            self.assertIn(role, actual_roles)
        
        # Check clear filters button
        clear_btn = soup.find('button', string=lambda text: 'Clear Filters' in text if text else False)
        self.assertIsNotNone(clear_btn)
        
        # Check user count display
        user_count = soup.find('span', {'id': 'userCount'})
        self.assertIsNotNone(user_count)
    
    def test_user_card_information_display(self):
        """Test that user cards display correct information."""
        # Login as super admin
        self.client.login(username='superadmin', password='secure_password_123')
        
        # Get impersonation page
        response = self.client.get(reverse('admin_panel:user_impersonation'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find user cards
        user_cards = soup.find_all('div', class_='user-item')
        self.assertGreater(len(user_cards), 0)
        
        for card in user_cards:
            # Check data attributes
            self.assertIsNotNone(card.get('data-username'))
            self.assertIsNotNone(card.get('data-email'))
            self.assertIsNotNone(card.get('data-role'))
            self.assertIsNotNone(card.get('data-tenant'))
            
            # Check role badge
            role_badge = card.find('span', class_='user-role-badge')
            self.assertIsNotNone(role_badge)
            
            # Check email display
            email_text = card.find('span', string=lambda text: 'Email:' in text if text else False)
            self.assertIsNotNone(email_text)
            
            # Check last login display
            login_text = card.find('span', string=lambda text: 'Last login:' in text if text else False)
            self.assertIsNotNone(login_text)
            
            # Check for impersonate button or inactive status
            impersonate_btn = card.find('button', class_='impersonate-btn')
            inactive_span = card.find('span', string='Inactive')
            self.assertTrue(impersonate_btn is not None or inactive_span is not None)
    
    def test_active_sessions_display(self):
        """Test that active impersonation sessions are displayed correctly."""
        # Create an active session
        session = ImpersonationSession.objects.create(
            admin_user_id=self.super_admin.id,
            admin_username=self.super_admin.username,
            target_user_id=self.tenant_user.id,
            target_username=self.tenant_user.username,
            tenant_schema=self.tenant.schema_name,
            tenant_domain=self.tenant.domain_url,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            status='active'
        )
        
        # Login as super admin
        self.client.login(username='superadmin', password='secure_password_123')
        
        # Get impersonation page
        response = self.client.get(reverse('admin_panel:user_impersonation'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check for active sessions section
        active_sessions_section = soup.find('h2', string=lambda text: 'Active Impersonation Sessions' in text if text else False)
        if active_sessions_section:  # Only check if section exists
            # Check session card
            session_cards = soup.find_all('div', class_='active-session')
            self.assertGreater(len(session_cards), 0)
            
            # Check terminate button
            terminate_buttons = soup.find_all('button', class_='terminate-btn')
            self.assertGreater(len(terminate_buttons), 0)
    
    def test_audit_log_page_rendering(self):
        """Test that the audit log page renders correctly."""
        # Create some test sessions
        ImpersonationSession.objects.create(
            admin_user_id=self.super_admin.id,
            admin_username=self.super_admin.username,
            target_user_id=self.tenant_user.id,
            target_username=self.tenant_user.username,
            tenant_schema=self.tenant.schema_name,
            tenant_domain=self.tenant.domain_url,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            status='ended'
        )
        
        # Login as super admin
        self.client.login(username='superadmin', password='secure_password_123')
        
        # Get audit log page
        response = self.client.get(reverse('admin_panel:impersonation_audit'))
        self.assertEqual(response.status_code, 200)
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check page title
        self.assertIsNotNone(soup.find('h1', string=lambda text: 'Impersonation Audit Log' in text if text else False))
        
        # Check statistics cards
        stats_cards = soup.find_all('div', class_='metric-value')
        self.assertGreater(len(stats_cards), 0)
        
        # Check filters section
        filters_section = soup.find('div', class_='audit-filters')
        self.assertIsNotNone(filters_section)
        
        # Check filter inputs
        self.assertIsNotNone(soup.find('input', {'name': 'admin'}))
        self.assertIsNotNone(soup.find('input', {'name': 'target'}))
        self.assertIsNotNone(soup.find('input', {'name': 'tenant'}))
        self.assertIsNotNone(soup.find('select', {'name': 'status'}))
        
        # Check audit table
        audit_table = soup.find('table')
        self.assertIsNotNone(audit_table)
        
        # Check table headers
        headers = audit_table.find_all('th')
        expected_headers = ['Session Info', 'Admin → Target', 'Tenant', 'Duration', 'Status', 'Actions']
        header_texts = [th.get_text().strip() for th in headers]
        for expected in expected_headers:
            self.assertTrue(any(expected in header for header in header_texts))
    
    def test_session_detail_page_rendering(self):
        """Test that the session detail page renders correctly."""
        # Create a test session with some activity
        session = ImpersonationSession.objects.create(
            admin_user_id=self.super_admin.id,
            admin_username=self.super_admin.username,
            target_user_id=self.tenant_user.id,
            target_username=self.tenant_user.username,
            tenant_schema=self.tenant.schema_name,
            tenant_domain=self.tenant.domain_url,
            ip_address='127.0.0.1',
            user_agent='Mozilla/5.0 Test Browser',
            status='ended',
            reason='Testing session details'
        )
        
        # Add some activity
        session.add_action('create', 'Created jewelry item', '/jewelry/add/')
        session.add_page_visit('/dashboard/', 'Dashboard')
        
        # Login as super admin
        self.client.login(username='superadmin', password='secure_password_123')
        
        # Get session detail page
        response = self.client.get(reverse('admin_panel:impersonation_session_detail', args=[session.session_id]))
        self.assertEqual(response.status_code, 200)
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check page title
        self.assertIsNotNone(soup.find('h1', string=lambda text: 'Impersonation Session Details' in text if text else False))
        
        # Check session ID display
        session_id_display = soup.find('code', string=lambda text: str(session.session_id) in text if text else False)
        self.assertIsNotNone(session_id_display)
        
        # Check session overview section
        overview_section = soup.find('h2', string=lambda text: 'Session Overview' in text if text else False)
        self.assertIsNotNone(overview_section)
        
        # Check detail items
        detail_items = soup.find_all('div', class_='detail-item')
        self.assertGreater(len(detail_items), 5)  # Should have multiple detail items
        
        # Check for reason display
        reason_display = soup.find('p', string=lambda text: 'Testing session details' in text if text else False)
        self.assertIsNotNone(reason_display)
        
        # Check actions performed section
        actions_section = soup.find('h2', string=lambda text: 'Actions Performed' in text if text else False)
        self.assertIsNotNone(actions_section)
        
        # Check pages visited section
        pages_section = soup.find('h2', string=lambda text: 'Pages Visited' in text if text else False)
        self.assertIsNotNone(pages_section)
        
        # Check export options
        export_section = soup.find('h2', string=lambda text: 'Export Session Data' in text if text else False)
        self.assertIsNotNone(export_section)
        
        export_buttons = soup.find_all('button', string=lambda text: 'Export' in text if text else False)
        self.assertGreater(len(export_buttons), 0)
    
    def test_statistics_page_rendering(self):
        """Test that the statistics page renders correctly."""
        # Create some test data
        ImpersonationSession.objects.create(
            admin_user_id=self.super_admin.id,
            admin_username=self.super_admin.username,
            target_user_id=self.tenant_user.id,
            target_username=self.tenant_user.username,
            tenant_schema=self.tenant.schema_name,
            tenant_domain=self.tenant.domain_url,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            status='ended'
        )
        
        # Login as super admin
        self.client.login(username='superadmin', password='secure_password_123')
        
        # Get statistics page
        response = self.client.get(reverse('admin_panel:impersonation_stats'))
        self.assertEqual(response.status_code, 200)
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check page title
        self.assertIsNotNone(soup.find('h1', string=lambda text: 'Impersonation Statistics' in text if text else False))
        
        # Check metric cards
        metric_cards = soup.find_all('div', class_='metric-card')
        self.assertEqual(len(metric_cards), 4)  # Should have 4 key metrics
        
        # Check chart containers
        chart_containers = soup.find_all('div', class_='chart-container')
        self.assertEqual(len(chart_containers), 2)  # Should have 2 charts
        
        # Check canvas elements for charts
        canvases = soup.find_all('canvas')
        self.assertEqual(len(canvases), 2)  # adminChart and tenantChart
        
        # Check data tables
        tables = soup.find_all('table')
        self.assertGreater(len(tables), 0)
        
        # Check export options
        export_buttons = soup.find_all('button', string=lambda text: 'Export' in text if text else False)
        self.assertGreater(len(export_buttons), 0)
    
    def test_persian_rtl_layout(self):
        """Test that Persian RTL layout is properly implemented."""
        # Login as super admin
        self.client.login(username='superadmin', password='secure_password_123')
        
        # Get impersonation page
        response = self.client.get(reverse('admin_panel:user_impersonation'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check HTML direction
        html_tag = soup.find('html')
        self.assertEqual(html_tag.get('dir'), 'rtl')
        self.assertEqual(html_tag.get('lang'), 'fa')
        
        # Check for Persian font loading
        vazir_font_link = soup.find('link', href=lambda href: 'Vazirmatn' in href if href else False)
        self.assertIsNotNone(vazir_font_link)
        
        # Check for RTL-specific CSS classes
        rtl_elements = soup.find_all(class_=lambda classes: any('space-x-reverse' in cls for cls in classes) if classes else False)
        self.assertGreater(len(rtl_elements), 0)
    
    def test_dark_mode_cybersecurity_theme_elements(self):
        """Test that dark mode cybersecurity theme elements are present."""
        # Login as super admin
        self.client.login(username='superadmin', password='secure_password_123')
        
        # Get impersonation page
        response = self.client.get(reverse('admin_panel:user_impersonation'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check for dark mode classes
        dark_elements = soup.find_all(class_=lambda classes: any('dark:' in cls for cls in classes) if classes else False)
        self.assertGreater(len(dark_elements), 0)
        
        # Check for cyber theme classes
        cyber_elements = soup.find_all(class_=lambda classes: any('cyber-' in cls for cls in classes) if classes else False)
        self.assertGreater(len(cyber_elements), 0)
        
        # Check for theme toggle button
        theme_toggle = soup.find('button', {'@click': lambda click: 'darkMode' in click if click else False})
        if not theme_toggle:
            # Alternative check for Alpine.js theme toggle
            theme_toggle = soup.find(attrs={'x-data': lambda data: 'darkMode' in data if data else False})
        self.assertIsNotNone(theme_toggle)
    
    def test_javascript_functionality_presence(self):
        """Test that required JavaScript functions are present."""
        # Login as super admin
        self.client.login(username='superadmin', password='secure_password_123')
        
        # Get impersonation page
        response = self.client.get(reverse('admin_panel:user_impersonation'))
        content = response.content.decode('utf-8')
        
        # Check for required JavaScript functions
        required_functions = [
            'showImpersonationModal',
            'hideImpersonationModal',
            'terminateSession',
            'filterUsers',
            'filterByTenant',
            'filterByRole',
            'clearFilters',
            'updateUserDisplay',
            'updateUserCount'
        ]
        
        for func in required_functions:
            self.assertIn(f'function {func}', content)
        
        # Check for event listeners
        self.assertIn('addEventListener', content)
        self.assertIn('DOMContentLoaded', content)
        
        # Check for CSRF token handling
        self.assertIn('X-CSRFToken', content)
        
        # Check for auto-refresh functionality
        self.assertIn('setInterval', content)
    
    def test_accessibility_features(self):
        """Test that accessibility features are implemented."""
        # Login as super admin
        self.client.login(username='superadmin', password='secure_password_123')
        
        # Get impersonation page
        response = self.client.get(reverse('admin_panel:user_impersonation'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check for proper labels
        labels = soup.find_all('label')
        for label in labels:
            # Each label should have a 'for' attribute or contain an input
            has_for = label.get('for') is not None
            has_nested_input = label.find('input') is not None
            self.assertTrue(has_for or has_nested_input)
        
        # Check for ARIA attributes
        aria_elements = soup.find_all(attrs={'aria-label': True})
        self.assertGreater(len(aria_elements), 0)
        
        # Check for keyboard navigation support
        content = response.content.decode('utf-8')
        self.assertIn('keydown', content)  # Keyboard event handling
        
        # Check for focus management
        self.assertIn('focus()', content)
        
        # Check for screen reader text
        sr_only_elements = soup.find_all(class_='sr-only')
        self.assertGreater(len(sr_only_elements), 0)
    
    def test_error_handling_and_validation(self):
        """Test that proper error handling and validation are in place."""
        # Login as super admin
        self.client.login(username='superadmin', password='secure_password_123')
        
        # Get impersonation page
        response = self.client.get(reverse('admin_panel:user_impersonation'))
        content = response.content.decode('utf-8')
        
        # Check for error handling in JavaScript
        self.assertIn('catch(error', content)
        self.assertIn('try {', content)
        
        # Check for form validation
        self.assertIn('preventDefault', content)
        
        # Check for confirmation dialogs
        self.assertIn('confirm(', content)
        
        # Check for loading states
        self.assertIn('showLoading', content)
        self.assertIn('hideLoading', content)
        
        # Check for user feedback messages
        self.assertIn('showMessage', content)
    
    def tearDown(self):
        """Clean up test data."""
        # Clean up tenant schema
        from django_tenants.utils import schema_context
        with schema_context(self.tenant.schema_name):
            User.objects.all().delete()
        
        # Clean up shared schema
        ImpersonationSession.objects.all().delete()
        Domain.objects.all().delete()
        Tenant.objects.all().delete()
        SuperAdmin.objects.all().delete()


@pytest.mark.django_db
class HijackBannerTestCase(TestCase):
    """Test the hijack banner functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            schema_name='test_tenant',
            name='Test Shop',
            domain_url='test.zargar.com',
            is_active=True
        )
        
        self.super_admin = SuperAdmin.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='password123'
        )
        
        from django_tenants.utils import schema_context
        with schema_context(self.tenant.schema_name):
            self.tenant_user = User.objects.create_user(
                username='user',
                email='user@test.com',
                password='password123'
            )
    
    def test_hijack_banner_template_rendering(self):
        """Test that the hijack banner template renders correctly."""
        from django.template import Template, Context
        from django.template.loader import get_template
        
        # Load the banner template
        template = get_template('admin/hijack/impersonation_banner.html')
        
        # Create context
        context = Context({
            'admin_username': 'superadmin',
            'user': {'username': 'testuser'},
            'start_time': timezone.now(),
            'session_id': 'test-session-id'
        })
        
        # Render template
        rendered = template.render(context)
        
        # Check for key elements
        self.assertIn('hijack-banner', rendered)
        self.assertIn('IMPERSONATION ACTIVE', rendered)
        self.assertIn('superadmin', rendered)
        self.assertIn('testuser', rendered)
        self.assertIn('Exit Impersonation', rendered)
        
        # Check for Persian RTL attributes
        self.assertIn('direction: rtl', rendered)
        self.assertIn('Vazirmatn', rendered)
        
        # Check for enhanced styling
        self.assertIn('backdrop-filter', rendered)
        self.assertIn('text-shadow', rendered)
        self.assertIn('box-shadow', rendered)
    
    def tearDown(self):
        """Clean up test data."""
        ImpersonationSession.objects.all().delete()
        Domain.objects.all().delete()
        Tenant.objects.all().delete()
        SuperAdmin.objects.all().delete()


if __name__ == '__main__':
    pytest.main([__file__])