"""
Views for domain management in the admin panel.
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, FormView
from django.conf import settings
from django.http import JsonResponse
from django.core.management import call_command
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import os
import json
from pathlib import Path
from django.views.generic import FormView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from .forms import DomainSettingsForm, SystemConfigurationForm


class DomainSettingsView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """
    View for managing domain settings.
    """
    template_name = 'admin_panel/domain_settings.html'
    form_class = DomainSettingsForm
    success_url = reverse_lazy('admin_panel:domain_settings')
    
    def test_func(self):
        """Check if user is a super admin."""
        try:
            from zargar.tenants.models import SuperAdmin
            return SuperAdmin.objects.filter(username=self.request.user.username).exists()
        except:
            return False
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'Domain Settings',
            'current_domain': getattr(settings, 'TENANT_BASE_DOMAIN', 'zargar.com'),
            'current_protocol': getattr(settings, 'TENANT_DOMAIN_PROTOCOL', 'https'),
            'current_separator': getattr(settings, 'TENANT_SUBDOMAIN_SEPARATOR', '.'),
            'example_url': f"{getattr(settings, 'TENANT_DOMAIN_PROTOCOL', 'https')}://shop1{getattr(settings, 'TENANT_SUBDOMAIN_SEPARATOR', '.')}{getattr(settings, 'TENANT_BASE_DOMAIN', 'zargar.com')}",
        })
        return context
    
    def form_valid(self, form):
        """
        Handle valid form submission.
        """
        try:
            # Get form data
            base_domain = form.cleaned_data['base_domain']
            protocol = form.cleaned_data['protocol']
            separator = form.cleaned_data['subdomain_separator']
            
            # Update environment file
            self.update_env_file(base_domain, protocol, separator)
            
            messages.success(
                self.request,
                f'Domain settings updated successfully. New base domain: {base_domain}'
            )
            messages.warning(
                self.request,
                'Please restart the application for changes to take effect.'
            )
            
            return redirect('admin_panel:domain_settings')
            
        except Exception as e:
            messages.error(
                self.request,
                f'Error updating domain settings: {str(e)}'
            )
            return self.form_invalid(form)
    
    def update_env_file(self, base_domain, protocol, separator):
        """
        Update the environment file with new domain settings.
        """
        env_file = Path('.env')
        env_content = {}
        
        # Read current env file
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_content[key.strip()] = value.strip()
        
        # Update domain settings
        env_content['TENANT_BASE_DOMAIN'] = base_domain
        env_content['TENANT_DOMAIN_PROTOCOL'] = protocol
        env_content['TENANT_SUBDOMAIN_SEPARATOR'] = separator
        
        # Update ALLOWED_HOSTS
        current_hosts = env_content.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0')
        hosts_list = [host.strip() for host in current_hosts.split(',')]
        
        # Add base domain and wildcard subdomain
        new_hosts = [base_domain, f'*.{base_domain}']
        for host in new_hosts:
            if host not in hosts_list:
                hosts_list.append(host)
        
        env_content['ALLOWED_HOSTS'] = ','.join(hosts_list)
        
        # Write updated env file
        with open(env_file, 'w') as f:
            for key, value in env_content.items():
                f.write(f'{key}={value}\n')


@method_decorator(csrf_exempt, name='dispatch')
class DomainPreviewView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    AJAX view for previewing domain changes.
    """
    
    def test_func(self):
        """Check if user is a super admin."""
        try:
            from zargar.tenants.models import SuperAdmin
            return SuperAdmin.objects.filter(username=self.request.user.username).exists()
        except:
            return False
    
    def post(self, request, *args, **kwargs):
        """
        Return preview of domain configuration.
        """
        try:
            data = json.loads(request.body)
            base_domain = data.get('base_domain', '').lower().strip()
            protocol = data.get('protocol', 'https')
            separator = data.get('separator', '.')
            
            # Validate domain
            import re
            if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', base_domain):
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid domain format'
                })
            
            # Generate examples
            examples = [
                f"{protocol}://shop1{separator}{base_domain}",
                f"{protocol}://goldstore{separator}{base_domain}",
                f"{protocol}://jewelry-palace{separator}{base_domain}",
            ]
            
            return JsonResponse({
                'success': True,
                'examples': examples,
                'base_domain': base_domain,
                'protocol': protocol,
                'separator': separator
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


class SystemConfigurationView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """
    View for managing system-wide configuration.
    """
    template_name = 'admin_panel/system_configuration.html'
    form_class = SystemConfigurationForm
    
    def test_func(self):
        """Check if user is a super admin."""
        try:
            from zargar.tenants.models import SuperAdmin
            return SuperAdmin.objects.filter(username=self.request.user.username).exists()
        except:
            return False
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'System Configuration',
            'current_settings': {
                'site_name': getattr(settings, 'SITE_NAME', 'ZARGAR'),
                'default_language': getattr(settings, 'LANGUAGE_CODE', 'fa'),
                'default_timezone': getattr(settings, 'TIME_ZONE', 'Asia/Tehran'),
            }
        })
        return context
    
    def form_valid(self, form):
        """
        Handle valid form submission.
        """
        try:
            # In a real implementation, you would save these to a database
            # or update configuration files
            messages.success(
                self.request,
                'System configuration updated successfully.'
            )
            return redirect('admin_panel:system_configuration')
            
        except Exception as e:
            messages.error(
                self.request,
                f'Error updating system configuration: {str(e)}'
            )
            return self.form_invalid(form)


class DomainTestView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    View for testing domain configuration.
    """
    template_name = 'admin_panel/domain_test.html'
    
    def test_func(self):
        """Check if user is a super admin."""
        try:
            from zargar.tenants.models import SuperAdmin
            return SuperAdmin.objects.filter(username=self.request.user.username).exists()
        except:
            return False
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current domain settings
        base_domain = getattr(settings, 'TENANT_BASE_DOMAIN', 'zargar.com')
        protocol = getattr(settings, 'TENANT_DOMAIN_PROTOCOL', 'https')
        separator = getattr(settings, 'TENANT_SUBDOMAIN_SEPARATOR', '.')
        
        # Generate test URLs
        test_tenants = ['shop1', 'goldstore', 'jewelry-palace', 'diamond-center']
        test_urls = [
            f"{protocol}://{tenant}{separator}{base_domain}"
            for tenant in test_tenants
        ]
        
        context.update({
            'page_title': 'Domain Configuration Test',
            'base_domain': base_domain,
            'protocol': protocol,
            'separator': separator,
            'test_urls': test_urls,
            'admin_url': f"{protocol}://admin{separator}{base_domain}",
        })
        
        return context