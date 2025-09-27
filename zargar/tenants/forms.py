"""
Forms for tenant management in the admin super-panel.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
import re

from .models import Tenant, Domain

User = get_user_model()


class TenantCreateForm(forms.ModelForm):
    """
    Form for creating new tenants with validation.
    """
    
    domain_url = forms.CharField(
        max_length=100,
        label=_('Domain URL'),
        help_text=_('Subdomain for the tenant (e.g., shop1.zargar.com)'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'shop-name',
            'dir': 'ltr'
        })
    )
    
    confirm_creation = forms.BooleanField(
        required=True,
        label=_('Confirm Creation'),
        help_text=_('I confirm that I want to create this tenant with schema provisioning'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    class Meta:
        model = Tenant
        fields = [
            'name', 'owner_name', 'owner_email', 'phone_number', 
            'address', 'subscription_plan'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام فروشگاه طلا و جواهر',
                'dir': 'rtl'
            }),
            'owner_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام مالک فروشگاه',
                'dir': 'rtl'
            }),
            'owner_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com',
                'dir': 'ltr'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '09123456789',
                'dir': 'ltr'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'آدرس کامل فروشگاه',
                'dir': 'rtl'
            }),
            'subscription_plan': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
        
        labels = {
            'name': _('Shop Name'),
            'owner_name': _('Owner Name'),
            'owner_email': _('Owner Email'),
            'phone_number': _('Phone Number'),
            'address': _('Address'),
            'subscription_plan': _('Subscription Plan'),
        }
        
        help_texts = {
            'name': _('The name of the jewelry shop'),
            'owner_name': _('Full name of the shop owner'),
            'owner_email': _('Email address for the shop owner (will be used for login)'),
            'phone_number': _('Contact phone number'),
            'address': _('Complete address of the jewelry shop'),
            'subscription_plan': _('Choose the appropriate subscription plan'),
        }
    
    def clean_name(self):
        """Validate tenant name."""
        name = self.cleaned_data.get('name')
        
        if not name:
            raise ValidationError(_('Shop name is required.'))
        
        if len(name) < 2:
            raise ValidationError(_('Shop name must be at least 2 characters long.'))
        
        if len(name) > 100:
            raise ValidationError(_('Shop name cannot exceed 100 characters.'))
        
        # Check for duplicate names
        if Tenant.objects.filter(name__iexact=name).exists():
            raise ValidationError(_('A shop with this name already exists.'))
        
        return name
    
    def clean_owner_email(self):
        """Validate owner email."""
        email = self.cleaned_data.get('owner_email')
        
        if not email:
            raise ValidationError(_('Owner email is required.'))
        
        # Check if email is already used by another tenant
        if Tenant.objects.filter(owner_email__iexact=email).exists():
            raise ValidationError(_('This email is already used by another tenant.'))
        
        return email.lower()
    
    def clean_phone_number(self):
        """Validate phone number."""
        phone = self.cleaned_data.get('phone_number')
        
        if phone:
            # Remove spaces and dashes
            phone = re.sub(r'[\s\-]', '', phone)
            
            # Validate Iranian phone number format
            if not re.match(r'^(\+98|0)?9\d{9}$', phone):
                raise ValidationError(_('Please enter a valid Iranian mobile number.'))
            
            # Normalize to standard format
            if phone.startswith('+98'):
                phone = '0' + phone[3:]
            elif phone.startswith('98'):
                phone = '0' + phone[2:]
            elif not phone.startswith('0'):
                phone = '0' + phone
        
        return phone
    
    def clean_domain_url(self):
        """Validate domain URL."""
        domain_url = self.cleaned_data.get('domain_url')
        
        if not domain_url:
            raise ValidationError(_('Domain URL is required.'))
        
        # Convert to lowercase
        domain_url = domain_url.lower().strip()
        
        # Validate format (only letters, numbers, and hyphens)
        if not re.match(r'^[a-z0-9\-]+$', domain_url):
            raise ValidationError(_('Domain can only contain letters, numbers, and hyphens.'))
        
        # Check length
        if len(domain_url) < 3:
            raise ValidationError(_('Domain must be at least 3 characters long.'))
        
        if len(domain_url) > 50:
            raise ValidationError(_('Domain cannot exceed 50 characters.'))
        
        # Check for reserved words
        reserved_words = [
            'www', 'admin', 'api', 'mail', 'ftp', 'public', 'private',
            'system', 'root', 'test', 'staging', 'dev', 'development'
        ]
        
        if domain_url in reserved_words:
            raise ValidationError(_('This domain name is reserved and cannot be used.'))
        
        # Check if domain already exists
        if Domain.objects.filter(domain=domain_url).exists():
            raise ValidationError(_('This domain is already taken.'))
        
        return domain_url


class TenantUpdateForm(forms.ModelForm):
    """
    Form for updating existing tenants.
    """
    
    class Meta:
        model = Tenant
        fields = [
            'name', 'owner_name', 'owner_email', 'phone_number', 
            'address', 'subscription_plan', 'is_active'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
            'owner_name': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
            'owner_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'dir': 'ltr'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'ltr'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'dir': 'rtl'
            }),
            'subscription_plan': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
        labels = {
            'name': _('Shop Name'),
            'owner_name': _('Owner Name'),
            'owner_email': _('Owner Email'),
            'phone_number': _('Phone Number'),
            'address': _('Address'),
            'subscription_plan': _('Subscription Plan'),
            'is_active': _('Active Status'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make schema_name read-only if instance exists
        if self.instance and self.instance.pk:
            self.fields['schema_name'] = forms.CharField(
                label=_('Schema Name'),
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'readonly': True,
                    'dir': 'ltr'
                }),
                initial=self.instance.schema_name,
                help_text=_('Schema name cannot be changed after creation.')
            )
    
    def clean_name(self):
        """Validate tenant name for updates."""
        name = self.cleaned_data.get('name')
        
        if not name:
            raise ValidationError(_('Shop name is required.'))
        
        if len(name) < 2:
            raise ValidationError(_('Shop name must be at least 2 characters long.'))
        
        if len(name) > 100:
            raise ValidationError(_('Shop name cannot exceed 100 characters.'))
        
        # Check for duplicate names (excluding current instance)
        existing_tenant = Tenant.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            existing_tenant = existing_tenant.exclude(pk=self.instance.pk)
        
        if existing_tenant.exists():
            raise ValidationError(_('A shop with this name already exists.'))
        
        return name
    
    def clean_owner_email(self):
        """Validate owner email for updates."""
        email = self.cleaned_data.get('owner_email')
        
        if not email:
            raise ValidationError(_('Owner email is required.'))
        
        # Check if email is already used by another tenant (excluding current)
        existing_tenant = Tenant.objects.filter(owner_email__iexact=email)
        if self.instance and self.instance.pk:
            existing_tenant = existing_tenant.exclude(pk=self.instance.pk)
        
        if existing_tenant.exists():
            raise ValidationError(_('This email is already used by another tenant.'))
        
        return email.lower()
    
    def clean_phone_number(self):
        """Validate phone number for updates."""
        phone = self.cleaned_data.get('phone_number')
        
        if phone:
            # Remove spaces and dashes
            phone = re.sub(r'[\s\-]', '', phone)
            
            # Validate Iranian phone number format
            if not re.match(r'^(\+98|0)?9\d{9}$', phone):
                raise ValidationError(_('Please enter a valid Iranian mobile number.'))
            
            # Normalize to standard format
            if phone.startswith('+98'):
                phone = '0' + phone[3:]
            elif phone.startswith('98'):
                phone = '0' + phone[2:]
            elif not phone.startswith('0'):
                phone = '0' + phone
        
        return phone


class TenantSearchForm(forms.Form):
    """
    Form for searching and filtering tenants.
    """
    
    search = forms.CharField(
        required=False,
        max_length=100,
        label=_('Search'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'جستجو در نام، مالک، ایمیل یا اسکیما...',
            'dir': 'rtl'
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', _('All Statuses')),
            ('active', _('Active')),
            ('inactive', _('Inactive')),
        ],
        label=_('Status'),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    plan = forms.ChoiceField(
        required=False,
        label=_('Subscription Plan'),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    created_after = forms.DateField(
        required=False,
        label=_('Created After'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    created_before = forms.DateField(
        required=False,
        label=_('Created Before'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate subscription plan choices
        plan_choices = [('', _('All Plans'))]
        plan_choices.extend(Tenant._meta.get_field('subscription_plan').choices)
        self.fields['plan'].choices = plan_choices


class DomainForm(forms.ModelForm):
    """
    Form for managing tenant domains.
    """
    
    class Meta:
        model = Domain
        fields = ['domain', 'is_primary']
        
        widgets = {
            'domain': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'ltr',
                'placeholder': 'subdomain.zargar.com'
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
        labels = {
            'domain': _('Domain'),
            'is_primary': _('Primary Domain'),
        }
        
        help_texts = {
            'domain': _('Full domain name for the tenant'),
            'is_primary': _('Mark as the primary domain for this tenant'),
        }
    
    def clean_domain(self):
        """Validate domain format."""
        domain = self.cleaned_data.get('domain')
        
        if not domain:
            raise ValidationError(_('Domain is required.'))
        
        # Convert to lowercase
        domain = domain.lower().strip()
        
        # Basic domain validation
        if not re.match(r'^[a-z0-9\-\.]+$', domain):
            raise ValidationError(_('Invalid domain format.'))
        
        # Check if domain already exists (excluding current instance)
        existing_domain = Domain.objects.filter(domain=domain)
        if self.instance and self.instance.pk:
            existing_domain = existing_domain.exclude(pk=self.instance.pk)
        
        if existing_domain.exists():
            raise ValidationError(_('This domain is already in use.'))
        
        return domain


class BulkTenantActionForm(forms.Form):
    """
    Form for bulk actions on tenants.
    """
    
    ACTION_CHOICES = [
        ('activate', _('Activate Selected')),
        ('deactivate', _('Deactivate Selected')),
        ('delete', _('Delete Selected')),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        label=_('Action'),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    tenant_ids = forms.CharField(
        widget=forms.HiddenInput()
    )
    
    confirm_action = forms.BooleanField(
        required=True,
        label=_('Confirm Action'),
        help_text=_('I confirm that I want to perform this action on selected tenants'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def clean_tenant_ids(self):
        """Validate tenant IDs."""
        tenant_ids = self.cleaned_data.get('tenant_ids')
        
        if not tenant_ids:
            raise ValidationError(_('No tenants selected.'))
        
        try:
            # Convert comma-separated string to list of integers
            tenant_id_list = [int(id.strip()) for id in tenant_ids.split(',') if id.strip()]
            
            if not tenant_id_list:
                raise ValidationError(_('No valid tenant IDs provided.'))
            
            # Verify that all tenant IDs exist
            existing_count = Tenant.objects.filter(id__in=tenant_id_list).count()
            if existing_count != len(tenant_id_list):
                raise ValidationError(_('Some selected tenants do not exist.'))
            
            return tenant_id_list
            
        except ValueError:
            raise ValidationError(_('Invalid tenant ID format.'))