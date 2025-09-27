"""
Forms for the admin panel.
"""

from django import forms
from django.conf import settings
from django.core.validators import RegexValidator
import re


class DomainSettingsForm(forms.Form):
    """
    Form for configuring domain settings.
    """
    
    base_domain = forms.CharField(
        label='Base Domain',
        max_length=253,
        help_text='The base domain for tenant subdomains (e.g., zargar.com, mycompany.com)',
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$',
                message='Enter a valid domain name.'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'example.com'
        })
    )
    
    protocol = forms.ChoiceField(
        label='Protocol',
        choices=[
            ('https', 'HTTPS (Recommended)'),
            ('http', 'HTTP (Development only)')
        ],
        initial='https',
        help_text='Protocol to use for tenant URLs',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    subdomain_separator = forms.CharField(
        label='Subdomain Separator',
        max_length=5,
        initial='.',
        help_text='Separator between subdomain and base domain (usually ".")',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '.'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial values from settings
        self.fields['base_domain'].initial = getattr(settings, 'TENANT_BASE_DOMAIN', 'zargar.com')
        self.fields['protocol'].initial = getattr(settings, 'TENANT_DOMAIN_PROTOCOL', 'https')
        self.fields['subdomain_separator'].initial = getattr(settings, 'TENANT_SUBDOMAIN_SEPARATOR', '.')
    
    def clean_base_domain(self):
        """
        Validate the base domain.
        """
        domain = self.cleaned_data['base_domain'].lower().strip()
        
        # Basic domain validation
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', domain):
            raise forms.ValidationError('Enter a valid domain name.')
        
        # Check for common mistakes
        if domain.startswith('http://') or domain.startswith('https://'):
            raise forms.ValidationError('Do not include protocol (http/https) in the domain.')
        
        if domain.startswith('www.'):
            raise forms.ValidationError('Do not include "www" in the base domain.')
        
        return domain
    
    def clean_subdomain_separator(self):
        """
        Validate the subdomain separator.
        """
        separator = self.cleaned_data['subdomain_separator']
        
        # Only allow certain characters
        if not re.match(r'^[.\-_]$', separator):
            raise forms.ValidationError('Separator must be one of: . - _')
        
        return separator
    
    def get_example_url(self):
        """
        Get an example tenant URL based on the form data.
        """
        if self.is_valid():
            protocol = self.cleaned_data['protocol']
            separator = self.cleaned_data['subdomain_separator']
            domain = self.cleaned_data['base_domain']
            return f"{protocol}://shop1{separator}{domain}"
        return None


class SystemConfigurationForm(forms.Form):
    """
    Form for system-wide configuration settings.
    """
    
    site_name = forms.CharField(
        label='Site Name',
        max_length=100,
        initial='ZARGAR',
        help_text='The name of your jewelry SaaS platform',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ZARGAR'
        })
    )
    
    default_language = forms.ChoiceField(
        label='Default Language',
        choices=[
            ('fa', 'Persian (فارسی)'),
            ('en', 'English'),
            ('ar', 'Arabic (العربية)')
        ],
        initial='fa',
        help_text='Default language for the platform',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    default_timezone = forms.CharField(
        label='Default Timezone',
        max_length=50,
        initial='Asia/Tehran',
        help_text='Default timezone for the platform',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Asia/Tehran'
        })
    )
    
    max_tenants_per_domain = forms.IntegerField(
        label='Max Tenants per Domain',
        min_value=1,
        max_value=10000,
        initial=1000,
        help_text='Maximum number of tenants allowed per base domain',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '10000'
        })
    )
    
    enable_tenant_registration = forms.BooleanField(
        label='Enable Tenant Registration',
        initial=True,
        required=False,
        help_text='Allow new tenants to register automatically',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    require_email_verification = forms.BooleanField(
        label='Require Email Verification',
        initial=True,
        required=False,
        help_text='Require email verification for new tenant registrations',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )