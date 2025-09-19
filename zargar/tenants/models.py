from django.db import models
from django_tenants.models import TenantMixin, DomainMixin

# Import super admin models
from .admin_models import SuperAdmin, SuperAdminSession


class Tenant(TenantMixin):
    """
    Tenant model for jewelry shops.
    """
    name = models.CharField(max_length=100)
    created_on = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    # Jewelry shop specific fields
    owner_name = models.CharField(max_length=100)
    owner_email = models.EmailField()
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    
    # Subscription information
    subscription_plan = models.CharField(
        max_length=20,
        choices=[
            ('basic', 'Basic'),
            ('pro', 'Pro'),
            ('enterprise', 'Enterprise'),
        ],
        default='basic'
    )
    
    auto_create_schema = True
    auto_drop_schema = True

    class Meta:
        db_table = 'public.tenant'

    def __str__(self):
        return self.name


class Domain(DomainMixin):
    """
    Domain model for tenant subdomains.
    """
    pass

    class Meta:
        db_table = 'public.domain'