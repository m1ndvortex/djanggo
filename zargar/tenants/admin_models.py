"""
Super Admin models for cross-tenant management.
These models exist in the shared schema and allow super admins to access all tenants.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
import uuid
import jdatetime


class SuperAdmin(AbstractUser):
    """
    Super Admin model that exists in shared schema for cross-tenant access.
    This is separate from regular Users who are tenant-isolated.
    """
    
    # Additional fields for super admin
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        verbose_name=_('Phone Number')
    )
    
    # Persian name fields
    persian_first_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Persian First Name')
    )
    
    persian_last_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Persian Last Name')
    )
    
    # 2FA field
    is_2fa_enabled = models.BooleanField(
        default=False,
        verbose_name=_('2FA Enabled')
    )
    
    # Theme preference
    theme_preference = models.CharField(
        max_length=10,
        choices=[
            ('light', _('Light Theme')),
            ('dark', _('Dark Theme')),
        ],
        default='light',
        verbose_name=_('Theme Preference')
    )
    
    # Super admin specific fields
    can_create_tenants = models.BooleanField(
        default=True,
        verbose_name=_('Can Create Tenants')
    )
    
    can_suspend_tenants = models.BooleanField(
        default=True,
        verbose_name=_('Can Suspend Tenants')
    )
    
    can_access_all_data = models.BooleanField(
        default=True,
        verbose_name=_('Can Access All Tenant Data')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_tenant_access = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('Super Admin')
        verbose_name_plural = _('Super Admins')
        db_table = 'tenants_superadmin'
    
    # Override groups and user_permissions to avoid conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="superadmin_set",
        related_query_name="superadmin",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="superadmin_set",
        related_query_name="superadmin",
    )
    
    def __str__(self):
        if self.persian_first_name and self.persian_last_name:
            return f"{self.persian_first_name} {self.persian_last_name}"
        return self.username
    
    @property
    def full_persian_name(self):
        """Return full Persian name if available."""
        if self.persian_first_name and self.persian_last_name:
            return f"{self.persian_first_name} {self.persian_last_name}"
        return self.get_full_name() or self.username
    
    def record_tenant_access(self, tenant_schema):
        """Record when super admin accesses a tenant."""
        self.last_tenant_access = timezone.now()
        self.save(update_fields=['last_tenant_access'])
        
        # Create session record
        SuperAdminSession.objects.create(
            super_admin=self,
            tenant_schema=tenant_schema,
            access_time=timezone.now()
        )


class SuperAdminSession(models.Model):
    """
    Track super admin sessions across tenants for audit purposes.
    """
    super_admin = models.ForeignKey(
        SuperAdmin,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name=_('Super Admin')
    )
    
    tenant_schema = models.CharField(
        max_length=100,
        verbose_name=_('Tenant Schema')
    )
    
    session_key = models.CharField(
        max_length=40,
        blank=True,
        verbose_name=_('Session Key')
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP Address')
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )
    
    access_time = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Access Time')
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active Session')
    )
    
    class Meta:
        verbose_name = _('Super Admin Session')
        verbose_name_plural = _('Super Admin Sessions')
        db_table = 'tenants_superadmin_session'
        ordering = ['-access_time']
        indexes = [
            models.Index(fields=['super_admin', 'tenant_schema']),
            models.Index(fields=['session_key']),
            models.Index(fields=['access_time']),
        ]
    
    def __str__(self):
        return f"{self.super_admin.username} -> {self.tenant_schema} at {self.access_time}"


class TenantAccessLog(models.Model):
    """
    Comprehensive audit log for tenant access and operations.
    """
    ACTION_CHOICES = [
        ('login', _('Login')),
        ('logout', _('Logout')),
        ('create', _('Create Record')),
        ('update', _('Update Record')),
        ('delete', _('Delete Record')),
        ('view', _('View Record')),
        ('export', _('Export Data')),
        ('import', _('Import Data')),
        ('tenant_switch', _('Switch Tenant')),
        ('impersonation_start', _('Start Impersonation')),
        ('impersonation_end', _('End Impersonation')),
    ]
    
    # User information (can be SuperAdmin or regular User)
    user_type = models.CharField(
        max_length=20,
        choices=[
            ('superadmin', _('Super Admin')),
            ('user', _('Regular User')),
        ],
        verbose_name=_('User Type')
    )
    
    user_id = models.PositiveIntegerField(
        verbose_name=_('User ID')
    )
    
    username = models.CharField(
        max_length=150,
        verbose_name=_('Username')
    )
    
    # Tenant information
    tenant_schema = models.CharField(
        max_length=100,
        verbose_name=_('Tenant Schema')
    )
    
    tenant_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Tenant Name')
    )
    
    # Action details
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        verbose_name=_('Action')
    )
    
    model_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Model Name')
    )
    
    object_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Object ID')
    )
    
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Action Details')
    )
    
    # Request information
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP Address')
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )
    
    request_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Request Path')
    )
    
    request_method = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Request Method')
    )
    
    # Timing
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Timestamp')
    )
    
    duration_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Duration (ms)')
    )
    
    # Status
    success = models.BooleanField(
        default=True,
        verbose_name=_('Success')
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Error Message')
    )
    
    class Meta:
        verbose_name = _('Tenant Access Log')
        verbose_name_plural = _('Tenant Access Logs')
        db_table = 'tenants_access_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user_type', 'user_id']),
            models.Index(fields=['tenant_schema']),
            models.Index(fields=['action']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['success']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.user_type}) - {self.action} in {self.tenant_schema}"
    
    @classmethod
    def log_action(cls, user, tenant_schema, action, **kwargs):
        """
        Convenience method to log an action.
        """
        # Determine user type
        if hasattr(user, '_meta') and user._meta.model_name == 'superadmin':
            user_type = 'superadmin'
        else:
            user_type = 'user'
        
        # Get tenant name
        tenant_name = kwargs.get('tenant_name', '')
        if not tenant_name and tenant_schema != 'public':
            try:
                from zargar.tenants.models import Tenant
                tenant = Tenant.objects.filter(schema_name=tenant_schema).first()
                tenant_name = tenant.name if tenant else ''
            except:
                pass
        
        return cls.objects.create(
            user_type=user_type,
            user_id=user.id,
            username=user.username,
            tenant_schema=tenant_schema,
            tenant_name=tenant_name,
            action=action,
            model_name=kwargs.get('model_name', ''),
            object_id=kwargs.get('object_id', ''),
            details=kwargs.get('details', {}),
            ip_address=kwargs.get('ip_address'),
            user_agent=kwargs.get('user_agent', ''),
            request_path=kwargs.get('request_path', ''),
            request_method=kwargs.get('request_method', ''),
            duration_ms=kwargs.get('duration_ms'),
            success=kwargs.get('success', True),
            error_message=kwargs.get('error_message', ''),
        )


class SubscriptionPlan(models.Model):
    """
    Subscription plans for Iranian jewelry shop tenants.
    Stored in shared schema for cross-tenant management.
    """
    PLAN_TYPES = [
        ('basic', _('Basic Plan')),
        ('pro', _('Pro Plan')),
        ('enterprise', _('Enterprise Plan')),
    ]
    
    # Plan identification
    name = models.CharField(
        max_length=100,
        verbose_name=_('Plan Name')
    )
    
    name_persian = models.CharField(
        max_length=100,
        verbose_name=_('Persian Plan Name'),
        help_text=_('Plan name in Persian for Iranian market')
    )
    
    plan_type = models.CharField(
        max_length=20,
        choices=PLAN_TYPES,
        unique=True,
        verbose_name=_('Plan Type')
    )
    
    # Iranian market pricing
    monthly_price_toman = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Monthly Price (Toman)'),
        help_text=_('Monthly subscription price in Iranian Toman')
    )
    
    yearly_price_toman = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Yearly Price (Toman)'),
        help_text=_('Yearly subscription price in Iranian Toman (optional discount)')
    )
    
    # Plan limits
    max_users = models.PositiveIntegerField(
        verbose_name=_('Maximum Users'),
        help_text=_('Maximum number of users allowed in this plan')
    )
    
    max_inventory_items = models.PositiveIntegerField(
        verbose_name=_('Maximum Inventory Items'),
        help_text=_('Maximum number of jewelry items in inventory')
    )
    
    max_customers = models.PositiveIntegerField(
        verbose_name=_('Maximum Customers'),
        help_text=_('Maximum number of customers in database')
    )
    
    max_monthly_transactions = models.PositiveIntegerField(
        verbose_name=_('Maximum Monthly Transactions'),
        help_text=_('Maximum number of transactions per month')
    )
    
    # Storage limits
    max_storage_gb = models.PositiveIntegerField(
        verbose_name=_('Maximum Storage (GB)'),
        help_text=_('Maximum storage space for photos and documents')
    )
    
    # Features (JSON field for flexibility)
    features = models.JSONField(
        default=dict,
        verbose_name=_('Plan Features'),
        help_text=_('JSON object containing plan features and capabilities')
    )
    
    # Plan status
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    
    is_popular = models.BooleanField(
        default=False,
        verbose_name=_('Is Popular Plan'),
        help_text=_('Mark as popular plan for marketing purposes')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        SuperAdmin,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_plans',
        verbose_name=_('Created By')
    )
    
    class Meta:
        verbose_name = _('Subscription Plan')
        verbose_name_plural = _('Subscription Plans')
        db_table = 'tenants_subscription_plan'
        ordering = ['monthly_price_toman']
    
    def __str__(self):
        return f"{self.name_persian} ({self.get_plan_type_display()})"
    
    @property
    def yearly_discount_percentage(self):
        """Calculate yearly discount percentage if yearly price is set."""
        if self.yearly_price_toman and self.monthly_price_toman:
            monthly_yearly = self.monthly_price_toman * 12
            discount = monthly_yearly - self.yearly_price_toman
            return float(round((discount / monthly_yearly) * 100, 1))
        return 0.0
    
    @property
    def features_persian(self):
        """Get Persian feature descriptions."""
        persian_features = {
            'pos_system': 'سیستم فروش (POS)',
            'inventory_management': 'مدیریت موجودی',
            'customer_management': 'مدیریت مشتریان',
            'accounting_system': 'سیستم حسابداری',
            'gold_installment': 'سیستم طلای قرضی',
            'reporting': 'گزارش‌گیری',
            'backup_restore': 'پشتیبان‌گیری و بازیابی',
            'multi_user': 'چند کاربره',
            'mobile_app': 'اپلیکیشن موبایل',
            'priority_support': 'پشتیبانی اولویت‌دار',
            'custom_reports': 'گزارش‌های سفارشی',
            'api_access': 'دسترسی API',
        }
        
        enabled_features = []
        for feature_key, is_enabled in self.features.items():
            if is_enabled and feature_key in persian_features:
                enabled_features.append(persian_features[feature_key])
        
        return enabled_features


class TenantInvoice(models.Model):
    """
    Invoice model for tenant billing with Persian invoice generation.
    Adapted for Iranian market and business practices.
    """
    INVOICE_STATUS = [
        ('draft', _('Draft')),
        ('pending', _('Pending Payment')),
        ('paid', _('Paid')),
        ('overdue', _('Overdue')),
        ('cancelled', _('Cancelled')),
        ('refunded', _('Refunded')),
    ]
    
    PAYMENT_METHODS = [
        ('bank_transfer', _('Bank Transfer')),
        ('cash', _('Cash')),
        ('cheque', _('Cheque')),
        ('card', _('Card Payment')),
        ('online', _('Online Payment')),
    ]
    
    # Invoice identification
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Invoice Number'),
        help_text=_('Unique invoice number (auto-generated)')
    )
    
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name=_('Invoice UUID')
    )
    
    # Tenant relationship
    tenant = models.ForeignKey(
        'Tenant',
        on_delete=models.CASCADE,
        related_name='invoices',
        verbose_name=_('Tenant')
    )
    
    subscription_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        verbose_name=_('Subscription Plan')
    )
    
    # Persian calendar dates (stored as regular dates, converted in application layer)
    issue_date_shamsi = models.DateField(
        verbose_name=_('Issue Date (Shamsi)'),
        help_text=_('Invoice issue date in Persian calendar')
    )
    
    due_date_shamsi = models.DateField(
        verbose_name=_('Due Date (Shamsi)'),
        help_text=_('Payment due date in Persian calendar')
    )
    
    # Billing period
    billing_period_start = models.DateField(
        verbose_name=_('Billing Period Start'),
        help_text=_('Start date of billing period')
    )
    
    billing_period_end = models.DateField(
        verbose_name=_('Billing Period End'),
        help_text=_('End date of billing period')
    )
    
    # Financial details
    subtotal_toman = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Subtotal (Toman)')
    )
    
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('9.00'),
        verbose_name=_('Tax Rate (%)'),
        help_text=_('Iranian VAT rate (default 9%)')
    )
    
    tax_amount_toman = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Tax Amount (Toman)')
    )
    
    discount_amount_toman = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Discount Amount (Toman)')
    )
    
    total_amount_toman = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Total Amount (Toman)')
    )
    
    # Payment information
    status = models.CharField(
        max_length=20,
        choices=INVOICE_STATUS,
        default='pending',
        verbose_name=_('Invoice Status')
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        blank=True,
        verbose_name=_('Payment Method')
    )
    
    payment_date_shamsi = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Payment Date (Shamsi)')
    )
    
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Payment Reference'),
        help_text=_('Bank transaction ID, cheque number, etc.')
    )
    
    # Iranian banking details
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Bank Name'),
        help_text=_('Iranian bank name for payment')
    )
    
    account_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Account Number'),
        help_text=_('Bank account number for payment')
    )
    
    iban = models.CharField(
        max_length=26,
        blank=True,
        verbose_name=_('IBAN'),
        help_text=_('Iranian IBAN for international transfers')
    )
    
    # Invoice content
    line_items = models.JSONField(
        default=list,
        verbose_name=_('Invoice Line Items'),
        help_text=_('JSON array of invoice line items with descriptions and amounts')
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name=_('Invoice Notes'),
        help_text=_('Additional notes or terms in Persian')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        SuperAdmin,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_invoices',
        verbose_name=_('Created By')
    )
    
    # PDF generation
    pdf_generated = models.BooleanField(
        default=False,
        verbose_name=_('PDF Generated')
    )
    
    pdf_file_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('PDF File Path')
    )
    
    class Meta:
        verbose_name = _('Tenant Invoice')
        verbose_name_plural = _('Tenant Invoices')
        db_table = 'tenants_invoice'
        ordering = ['-issue_date_shamsi']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['invoice_number']),
            models.Index(fields=['issue_date_shamsi']),
            models.Index(fields=['due_date_shamsi']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.tenant.name}"
    
    def save(self, *args, **kwargs):
        # Auto-generate invoice number if not set
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        
        # Calculate tax and total amounts
        self.calculate_amounts()
        
        super().save(*args, **kwargs)
    
    def generate_invoice_number(self):
        """Generate unique invoice number with Persian format."""
        import jdatetime
        
        current_shamsi = jdatetime.date.today()
        year_str = str(current_shamsi.year)
        month_str = f"{current_shamsi.month:02d}"
        
        # Get next sequence number for this month
        last_invoice = TenantInvoice.objects.filter(
            invoice_number__startswith=f"INV-{year_str}{month_str}"
        ).order_by('-invoice_number').first()
        
        if last_invoice:
            try:
                last_seq = int(last_invoice.invoice_number.split('-')[-1])
                next_seq = last_seq + 1
            except (ValueError, IndexError):
                next_seq = 1
        else:
            next_seq = 1
        
        return f"INV-{year_str}{month_str}-{next_seq:04d}"
    
    def calculate_amounts(self):
        """Calculate tax and total amounts."""
        if self.subtotal_toman:
            # Calculate tax amount
            self.tax_amount_toman = (self.subtotal_toman * self.tax_rate) / 100
            
            # Calculate total amount
            self.total_amount_toman = (
                self.subtotal_toman + 
                self.tax_amount_toman - 
                self.discount_amount_toman
            )
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue."""
        if self.status in ['paid', 'cancelled', 'refunded']:
            return False
        
        import jdatetime
        current_shamsi = jdatetime.date.today()
        # Convert stored date to jdatetime for comparison
        due_shamsi = jdatetime.date.fromgregorian(date=self.due_date_shamsi)
        return current_shamsi > due_shamsi
    
    @property
    def days_overdue(self):
        """Calculate days overdue."""
        if not self.is_overdue:
            return 0
        
        import jdatetime
        current_shamsi = jdatetime.date.today()
        due_shamsi = jdatetime.date.fromgregorian(date=self.due_date_shamsi)
        delta = current_shamsi - due_shamsi
        return delta.days
    
    @property
    def total_amount_persian_text(self):
        """Convert total amount to Persian text representation."""
        # This would integrate with a Persian number-to-text converter
        # For now, return formatted number
        return f"{self.total_amount_toman:,.0f} تومان"
    
    def mark_as_paid(self, payment_method, payment_reference='', payment_date=None):
        """Mark invoice as paid with payment details."""
        import jdatetime
        
        self.status = 'paid'
        self.payment_method = payment_method
        self.payment_reference = payment_reference
        # Convert jdatetime to regular date for storage
        if payment_date:
            if hasattr(payment_date, 'togregorian'):
                self.payment_date_shamsi = payment_date.togregorian()
            else:
                self.payment_date_shamsi = payment_date
        else:
            self.payment_date_shamsi = jdatetime.date.today().togregorian()
        self.save()
        
        # Log payment
        TenantAccessLog.log_action(
            user=self.created_by,
            tenant_schema=self.tenant.schema_name,
            action='update',
            model_name='TenantInvoice',
            object_id=str(self.id),
            details={
                'action': 'payment_received',
                'invoice_number': self.invoice_number,
                'amount': str(self.total_amount_toman),
                'payment_method': payment_method,
                'payment_reference': payment_reference
            }
        )
    
    def generate_persian_pdf(self):
        """Generate Persian PDF invoice."""
        # This would integrate with a Persian PDF generator
        # Implementation would include Persian fonts, RTL layout, etc.
        pass


class BillingCycle(models.Model):
    """
    Billing cycle management for automated invoice generation.
    """
    CYCLE_TYPES = [
        ('monthly', _('Monthly')),
        ('yearly', _('Yearly')),
        ('quarterly', _('Quarterly')),
    ]
    
    tenant = models.OneToOneField(
        'Tenant',
        on_delete=models.CASCADE,
        related_name='billing_cycle',
        verbose_name=_('Tenant')
    )
    
    cycle_type = models.CharField(
        max_length=20,
        choices=CYCLE_TYPES,
        default='monthly',
        verbose_name=_('Billing Cycle Type')
    )
    
    # Next billing date in Persian calendar (stored as regular date)
    next_billing_date = models.DateField(
        verbose_name=_('Next Billing Date (Shamsi)')
    )
    
    # Billing day of month (1-30)
    billing_day = models.PositiveIntegerField(
        default=1,
        verbose_name=_('Billing Day of Month'),
        help_text=_('Day of month to generate invoice (1-30)')
    )
    
    # Auto-payment settings
    auto_payment_enabled = models.BooleanField(
        default=False,
        verbose_name=_('Auto Payment Enabled')
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=TenantInvoice.PAYMENT_METHODS,
        blank=True,
        verbose_name=_('Default Payment Method')
    )
    
    # Grace period
    grace_period_days = models.PositiveIntegerField(
        default=7,
        verbose_name=_('Grace Period (Days)'),
        help_text=_('Days after due date before suspension')
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Billing Cycle')
        verbose_name_plural = _('Billing Cycles')
        db_table = 'tenants_billing_cycle'
    
    def __str__(self):
        return f"{self.tenant.name} - {self.get_cycle_type_display()}"
    
    def calculate_next_billing_date(self):
        """Calculate next billing date based on cycle type."""
        import jdatetime
        from dateutil.relativedelta import relativedelta
        
        current_date = jdatetime.date.today()
        
        if self.cycle_type == 'monthly':
            # Next month, same day
            next_date = current_date + relativedelta(months=1)
            # Adjust to billing day
            next_date = next_date.replace(day=min(self.billing_day, 30))
        elif self.cycle_type == 'yearly':
            # Next year, same month and day
            next_date = current_date + relativedelta(years=1)
        elif self.cycle_type == 'quarterly':
            # Next quarter (3 months)
            next_date = current_date + relativedelta(months=3)
        else:
            next_date = current_date + relativedelta(months=1)
        
        # Convert to Gregorian for storage
        self.next_billing_date = next_date.togregorian()
        self.save()
        
        return next_date

# Public Security Models for Super-Panel Access
# These models exist in the public schema and are used when accessing the super-panel

class PublicSecurityEvent(models.Model):
    """
    Public schema security event model for super-panel access.
    """
    EVENT_TYPES = [
        ('login_success', _('Successful Login')),
        ('login_failed', _('Failed Login')),
        ('login_blocked', _('Login Blocked (Rate Limited)')),
        ('logout', _('Logout')),
        ('password_change', _('Password Change')),
        ('password_reset_request', _('Password Reset Request')),
        ('password_reset_complete', _('Password Reset Complete')),
        ('2fa_enabled', _('2FA Enabled')),
        ('2fa_disabled', _('2FA Disabled')),
        ('2fa_success', _('2FA Verification Success')),
        ('2fa_failed', _('2FA Verification Failed')),
        ('2fa_backup_used', _('2FA Backup Token Used')),
        ('account_locked', _('Account Locked')),
        ('account_unlocked', _('Account Unlocked')),
        ('suspicious_activity', _('Suspicious Activity Detected')),
        ('brute_force_attempt', _('Brute Force Attack Attempt')),
        ('unauthorized_access', _('Unauthorized Access Attempt')),
        ('privilege_escalation', _('Privilege Escalation Attempt')),
        ('data_export', _('Data Export')),
        ('bulk_operation', _('Bulk Operation')),
        ('admin_impersonation', _('Admin Impersonation')),
        ('api_rate_limit', _('API Rate Limit Exceeded')),
        ('csrf_failure', _('CSRF Token Failure')),
        ('session_hijack', _('Potential Session Hijacking')),
    ]
    
    SEVERITY_LEVELS = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
        verbose_name=_('Event Type')
    )
    
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_LEVELS,
        default='medium',
        verbose_name=_('Severity Level')
    )
    
    username_attempted = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Username Attempted'),
        help_text=_('Username used in failed login attempts')
    )
    
    ip_address = models.GenericIPAddressField(
        verbose_name=_('IP Address')
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )
    
    session_key = models.CharField(
        max_length=40,
        blank=True,
        verbose_name=_('Session Key')
    )
    
    request_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Request Path')
    )
    
    request_method = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Request Method')
    )
    
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Event Details'),
        help_text=_('Additional details about the security event')
    )
    
    is_resolved = models.BooleanField(
        default=False,
        verbose_name=_('Is Resolved'),
        help_text=_('Whether this security event has been investigated and resolved')
    )
    
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Resolved At')
    )
    
    resolution_notes = models.TextField(
        blank=True,
        verbose_name=_('Resolution Notes')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Public Security Event')
        verbose_name_plural = _('Public Security Events')
        db_table = 'tenants_publicsecurityevent'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.ip_address} - {self.created_at}"
    
    @classmethod
    def log_event(cls, event_type, request=None, user=None, username_attempted=None, 
                  severity='medium', details=None, **kwargs):
        """
        Convenience method to log security events.
        """
        event_data = {
            'event_type': event_type,
            'severity': severity,
            'username_attempted': username_attempted or '',
            'details': details or {},
        }
        
        # Handle user - don't assign user for public security events
        # as they can be SuperAdmin or User instances
        if user:
            if hasattr(user, 'username'):
                event_data['username_attempted'] = user.username
        
        if request:
            event_data.update({
                'ip_address': cls._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'session_key': request.session.session_key or '',
                'request_path': request.path,
                'request_method': request.method,
            })
        
        event_data.update(kwargs)
        # Remove user from kwargs to avoid assignment error
        event_data.pop('user', None)
        return cls.objects.create(**event_data)
    
    @staticmethod
    def _get_client_ip(request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip


class PublicSuspiciousActivity(models.Model):
    """
    Public schema suspicious activity model for super-panel access.
    """
    ACTIVITY_TYPES = [
        ('multiple_failed_logins', _('Multiple Failed Logins')),
        ('unusual_access_pattern', _('Unusual Access Pattern')),
        ('privilege_escalation', _('Privilege Escalation Attempt')),
        ('data_scraping', _('Data Scraping')),
        ('session_anomaly', _('Session Anomaly')),
        ('geographic_anomaly', _('Geographic Anomaly')),
        ('time_anomaly', _('Time-based Anomaly')),
        ('bulk_data_access', _('Bulk Data Access')),
        ('unauthorized_api_usage', _('Unauthorized API Usage')),
        ('suspicious_user_agent', _('Suspicious User Agent')),
    ]
    
    RISK_LEVELS = [
        ('low', _('Low Risk')),
        ('medium', _('Medium Risk')),
        ('high', _('High Risk')),
        ('critical', _('Critical Risk')),
    ]
    
    activity_type = models.CharField(
        max_length=50,
        choices=ACTIVITY_TYPES,
        verbose_name=_('Activity Type')
    )
    
    risk_level = models.CharField(
        max_length=20,
        choices=RISK_LEVELS,
        default='medium',
        verbose_name=_('Risk Level')
    )
    
    ip_address = models.GenericIPAddressField(
        verbose_name=_('IP Address')
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )
    
    session_key = models.CharField(
        max_length=40,
        blank=True,
        verbose_name=_('Session Key')
    )
    
    pattern_data = models.JSONField(
        default=dict,
        verbose_name=_('Pattern Data'),
        help_text=_('Data used for pattern detection and analysis')
    )
    
    confidence_score = models.FloatField(
        default=0.0,
        verbose_name=_('Confidence Score'),
        help_text=_('Confidence score (0.0 to 1.0) for this suspicious activity detection')
    )
    
    is_investigated = models.BooleanField(
        default=False,
        verbose_name=_('Is Investigated')
    )
    
    investigated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Investigated At')
    )
    
    investigation_notes = models.TextField(
        blank=True,
        verbose_name=_('Investigation Notes')
    )
    
    is_false_positive = models.BooleanField(
        default=False,
        verbose_name=_('Is False Positive')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Public Suspicious Activity')
        verbose_name_plural = _('Public Suspicious Activities')
        db_table = 'tenants_publicsuspiciousactivity'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.ip_address} - {self.get_risk_level_display()}"
    
    @classmethod
    def detect_and_create(cls, activity_type, ip_address=None, user_agent='', 
                         session_key='', pattern_data=None, confidence_score=0.0, **kwargs):
        """
        Detect and create suspicious activity record.
        """
        # Determine risk level based on activity type and confidence
        risk_level = cls._calculate_risk_level(activity_type, confidence_score)
        
        activity = cls.objects.create(
            activity_type=activity_type,
            risk_level=risk_level,
            ip_address=ip_address,
            user_agent=user_agent,
            session_key=session_key,
            pattern_data=pattern_data or {},
            confidence_score=confidence_score,
            **kwargs
        )
        
        # Create related security event
        PublicSecurityEvent.log_event(
            event_type='suspicious_activity',
            severity=risk_level,
            ip_address=ip_address,
            user_agent=user_agent,
            session_key=session_key,
            details={
                'activity_type': activity_type,
                'confidence_score': confidence_score,
                'pattern_data': pattern_data or {},
                'suspicious_activity_id': activity.id,
            }
        )
        
        return activity
    
    @staticmethod
    def _calculate_risk_level(activity_type, confidence_score):
        """Calculate risk level based on activity type and confidence score."""
        base_risk = {
            'multiple_failed_logins': 'medium',
            'unusual_access_pattern': 'low',
            'privilege_escalation': 'critical',
            'data_scraping': 'high',
            'session_anomaly': 'medium',
            'geographic_anomaly': 'medium',
            'time_anomaly': 'low',
            'bulk_data_access': 'high',
            'unauthorized_api_usage': 'high',
            'suspicious_user_agent': 'medium',
        }
        
        risk = base_risk.get(activity_type, 'medium')
        
        # Adjust based on confidence score
        if confidence_score >= 0.9:
            if risk == 'low':
                risk = 'medium'
            elif risk == 'medium':
                risk = 'high'
        elif confidence_score <= 0.3:
            if risk == 'high':
                risk = 'medium'
            elif risk == 'critical':
                risk = 'high'
        
        return risk


class PublicAuditLog(models.Model):
    """
    Public schema audit log model for super-panel access.
    """
    ACTION_TYPES = [
        # CRUD Operations
        ('create', _('Create')),
        ('read', _('Read')),
        ('update', _('Update')),
        ('delete', _('Delete')),
        ('bulk_create', _('Bulk Create')),
        ('bulk_update', _('Bulk Update')),
        ('bulk_delete', _('Bulk Delete')),
        
        # Authentication
        ('login', _('Login')),
        ('logout', _('Logout')),
        ('password_change', _('Password Change')),
        ('password_reset', _('Password Reset')),
        
        # Admin Operations
        ('tenant_create', _('Tenant Create')),
        ('tenant_update', _('Tenant Update')),
        ('tenant_suspend', _('Tenant Suspend')),
        ('tenant_activate', _('Tenant Activate')),
        ('user_impersonate', _('User Impersonate')),
        ('impersonation_end', _('Impersonation End')),
        
        # System Operations
        ('backup_create', _('Backup Create')),
        ('backup_restore', _('Backup Restore')),
        ('system_maintenance', _('System Maintenance')),
        ('configuration_change', _('Configuration Change')),
    ]
    
    # User information
    user_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('User ID')
    )
    
    user_username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Username')
    )
    
    action = models.CharField(
        max_length=50,
        choices=ACTION_TYPES,
        verbose_name=_('Action')
    )
    
    model_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Model Name')
    )
    
    object_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Object ID')
    )
    
    object_repr = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Object Representation')
    )
    
    # Change tracking
    changes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Changes'),
        help_text=_('JSON representation of field changes')
    )
    
    old_values = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Old Values'),
        help_text=_('Previous values before change')
    )
    
    new_values = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('New Values'),
        help_text=_('New values after change')
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP Address')
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )
    
    session_key = models.CharField(
        max_length=40,
        blank=True,
        verbose_name=_('Session Key')
    )
    
    request_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Request Path')
    )
    
    request_method = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Request Method')
    )
    
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Additional Details')
    )
    
    # Tenant context
    tenant_schema = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Tenant Schema')
    )
    
    # Integrity protection
    checksum = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_('Integrity Checksum'),
        help_text=_('SHA-256 checksum for tamper detection')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Public Audit Log')
        verbose_name_plural = _('Public Audit Logs')
        db_table = 'tenants_publicauditlog'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user_username or 'System'} - {self.get_action_display()} - {self.created_at}"
    
    def save(self, *args, **kwargs):
        """Override save to generate integrity checksum."""
        if not self.checksum:
            self.checksum = self._generate_checksum()
        super().save(*args, **kwargs)
    
    def _generate_checksum(self):
        """Generate SHA-256 checksum for integrity verification."""
        import json
        import hashlib
        from django.utils import timezone
        
        data = {
            'user_id': self.user_id,
            'user_username': self.user_username,
            'action': self.action,
            'model_name': self.model_name,
            'object_id': self.object_id,
            'changes': self.changes,
            'ip_address': str(self.ip_address) if self.ip_address else '',
            'timestamp': self.created_at.isoformat() if self.created_at else timezone.now().isoformat(),
        }
        
        data_string = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def verify_integrity(self):
        """Verify the integrity of this audit log entry."""
        if not self.checksum:
            return False
        
        expected_checksum = self._generate_checksum()
        return self.checksum == expected_checksum
    
    @classmethod
    def log_action(cls, action, content_object=None, request=None, 
                   changes=None, details=None, **kwargs):
        """
        Convenience method to create audit log entries.
        """
        log_data = {
            'action': action,
            'changes': changes or {},
            'details': details or {},
        }
        
        # Set content object information
        if content_object:
            log_data.update({
                'model_name': content_object._meta.model_name,
                'object_id': str(content_object.pk),
                'object_repr': str(content_object),
            })
        
        # Set request context
        if request:
            log_data.update({
                'ip_address': cls._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'session_key': request.session.session_key or '',
                'request_path': request.path,
                'request_method': request.method,
            })
        
        log_data.update(kwargs)
        return cls.objects.create(**log_data)
    
    @staticmethod
    def _get_client_ip(request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip

class PublicRateLimitAttempt(models.Model):
    """
    Public schema rate limit attempt model for super-panel access.
    """
    LIMIT_TYPES = [
        ('login', _('Login Attempts')),
        ('api_call', _('API Call')),
        ('password_reset', _('Password Reset')),
        ('2fa_verify', _('2FA Verification')),
        ('data_export', _('Data Export')),
        ('bulk_operation', _('Bulk Operation')),
        ('search', _('Search Query')),
        ('report_generation', _('Report Generation')),
    ]
    
    identifier = models.CharField(
        max_length=200,
        verbose_name=_('Identifier'),
        help_text=_('IP address, user ID, or other identifier')
    )
    
    limit_type = models.CharField(
        max_length=50,
        choices=LIMIT_TYPES,
        verbose_name=_('Limit Type')
    )
    
    endpoint = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Endpoint'),
        help_text=_('API endpoint or view name')
    )
    
    attempts = models.PositiveIntegerField(
        default=1,
        verbose_name=_('Attempts')
    )
    
    window_start = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Window Start')
    )
    
    last_attempt = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Last Attempt')
    )
    
    is_blocked = models.BooleanField(
        default=False,
        verbose_name=_('Is Blocked')
    )
    
    blocked_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Blocked Until')
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )
    
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Details')
    )
    
    class Meta:
        verbose_name = _('Public Rate Limit Attempt')
        verbose_name_plural = _('Public Rate Limit Attempts')
        db_table = 'tenants_publicratelimitattempt'
        unique_together = ['identifier', 'limit_type', 'endpoint']
    
    def __str__(self):
        return f"{self.identifier} - {self.get_limit_type_display()} - {self.attempts} attempts"
    
    @classmethod
    def record_attempt(cls, identifier, limit_type, endpoint='', user_agent='', details=None):
        """
        Record a rate limit attempt.
        """
        from django.utils import timezone
        
        now = timezone.now()
        
        # Get or create rate limit record
        attempt, created = cls.objects.get_or_create(
            identifier=identifier,
            limit_type=limit_type,
            endpoint=endpoint,
            defaults={
                'attempts': 1,
                'user_agent': user_agent,
                'details': details or {},
            }
        )
        
        if not created:
            # Check if we're in a new time window (1 hour)
            if now - attempt.window_start > timezone.timedelta(hours=1):
                # Reset counter for new window
                attempt.attempts = 1
                attempt.window_start = now
                attempt.is_blocked = False
                attempt.blocked_until = None
            else:
                # Increment attempts in current window
                attempt.attempts += 1
            
            attempt.user_agent = user_agent
            attempt.details.update(details or {})
            attempt.save()
        
        # Check if should be blocked
        is_blocked = attempt.should_be_blocked()
        if is_blocked and not attempt.is_blocked:
            attempt.block()
        
        return attempt, is_blocked
    
    def should_be_blocked(self):
        """Check if this identifier should be blocked based on attempts."""
        limits = {
            'login': 5,  # 5 failed login attempts per hour
            'api_call': 1000,  # 1000 API calls per hour
            'password_reset': 3,  # 3 password reset attempts per hour
            '2fa_verify': 10,  # 10 2FA verification attempts per hour
            'data_export': 10,  # 10 data exports per hour
            'bulk_operation': 5,  # 5 bulk operations per hour
            'search': 100,  # 100 search queries per hour
            'report_generation': 20,  # 20 report generations per hour
        }
        
        limit = limits.get(self.limit_type, 100)
        return self.attempts >= limit
    
    def block(self, duration_hours=1):
        """Block this identifier for specified duration."""
        from django.utils import timezone
        
        self.is_blocked = True
        self.blocked_until = timezone.now() + timezone.timedelta(hours=duration_hours)
        self.save(update_fields=['is_blocked', 'blocked_until'])
    
    def is_currently_blocked(self):
        """Check if this identifier is currently blocked."""
        from django.utils import timezone
        
        if not self.is_blocked:
            return False
        
        if self.blocked_until and timezone.now() > self.blocked_until:
            # Block has expired, unblock
            self.is_blocked = False
            self.blocked_until = None
            self.save(update_fields=['is_blocked', 'blocked_until'])
            return False
        
        return True