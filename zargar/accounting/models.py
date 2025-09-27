"""
Persian Accounting System Models for ZARGAR Jewelry SaaS.

This module implements comprehensive Persian accounting models following Iranian
accounting standards and terminology. All models are tenant-aware and support
Persian localization with RTL layout and Shamsi calendar integration.

Models included:
- ChartOfAccounts: Persian chart of accounts (کدینگ حسابداری)
- JournalEntry: Transaction recording (ثبت اسناد حسابداری)
- GeneralLedger: General ledger (دفتر کل)
- SubsidiaryLedger: Subsidiary ledger (دفتر معین)
- BankAccount: Iranian bank account management
- ChequeManagement: Iranian cheque lifecycle tracking
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import jdatetime
from zargar.core.models import TenantAwareModel


class ChartOfAccounts(TenantAwareModel):
    """
    Persian Chart of Accounts model (کدینگ حسابداری).
    
    Implements Iranian accounting standards with Persian terminology
    and hierarchical account structure.
    """
    
    ACCOUNT_TYPES = [
        ('asset', _('دارایی (Assets)')),
        ('liability', _('بدهی (Liabilities)')),
        ('equity', _('حقوق صاحبان سهام (Equity)')),
        ('revenue', _('درآمد (Revenue)')),
        ('expense', _('هزینه (Expenses)')),
        ('cost_of_goods_sold', _('بهای تمام شده کالای فروخته شده (COGS)')),
    ]
    
    ACCOUNT_CATEGORIES = [
        # Asset categories
        ('current_assets', _('دارایی‌های جاری (Current Assets)')),
        ('fixed_assets', _('دارایی‌های ثابت (Fixed Assets)')),
        ('intangible_assets', _('دارایی‌های نامشهود (Intangible Assets)')),
        
        # Liability categories
        ('current_liabilities', _('بدهی‌های جاری (Current Liabilities)')),
        ('long_term_liabilities', _('بدهی‌های بلندمدت (Long-term Liabilities)')),
        
        # Equity categories
        ('capital', _('سرمایه (Capital)')),
        ('retained_earnings', _('سود انباشته (Retained Earnings)')),
        
        # Revenue categories
        ('sales_revenue', _('درآمد فروش (Sales Revenue)')),
        ('other_revenue', _('سایر درآمدها (Other Revenue)')),
        
        # Expense categories
        ('operating_expenses', _('هزینه‌های عملیاتی (Operating Expenses)')),
        ('administrative_expenses', _('هزینه‌های اداری (Administrative Expenses)')),
        ('financial_expenses', _('هزینه‌های مالی (Financial Expenses)')),
    ]
    
    # Account identification
    account_code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('کد حساب (Account Code)'),
        help_text=_('Unique account code following Iranian accounting standards')
    )
    
    account_name_persian = models.CharField(
        max_length=200,
        verbose_name=_('نام حساب (Persian Account Name)'),
        help_text=_('Persian name of the account')
    )
    
    account_name_english = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('English Account Name'),
        help_text=_('English name of the account (optional)')
    )
    
    # Account classification
    account_type = models.CharField(
        max_length=30,
        choices=ACCOUNT_TYPES,
        verbose_name=_('نوع حساب (Account Type)')
    )
    
    account_category = models.CharField(
        max_length=30,
        choices=ACCOUNT_CATEGORIES,
        verbose_name=_('دسته‌بندی حساب (Account Category)')
    )
    
    # Hierarchical structure
    parent_account = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sub_accounts',
        verbose_name=_('حساب والد (Parent Account)'),
        help_text=_('Parent account for hierarchical structure')
    )
    
    account_level = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_('سطح حساب (Account Level)'),
        help_text=_('Hierarchical level (1-5)')
    )
    
    # Account properties
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('فعال (Is Active)')
    )
    
    is_system_account = models.BooleanField(
        default=False,
        verbose_name=_('حساب سیستمی (System Account)'),
        help_text=_('System-generated account that cannot be deleted')
    )
    
    allow_posting = models.BooleanField(
        default=True,
        verbose_name=_('امکان ثبت (Allow Posting)'),
        help_text=_('Whether transactions can be posted to this account')
    )
    
    # Balance tracking
    normal_balance = models.CharField(
        max_length=10,
        choices=[
            ('debit', _('بدهکار (Debit)')),
            ('credit', _('بستانکار (Credit)')),
        ],
        verbose_name=_('مانده طبیعی (Normal Balance)')
    )
    
    current_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('مانده جاری (Current Balance)')
    )
    
    # Description and notes
    description = models.TextField(
        blank=True,
        verbose_name=_('توضیحات (Description)')
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name=_('یادداشت‌ها (Notes)')
    )
    
    class Meta:
        verbose_name = _('حساب (Chart of Account)')
        verbose_name_plural = _('فهرست حساب‌ها (Chart of Accounts)')
        ordering = ['account_code']
        indexes = [
            models.Index(fields=['account_code']),
            models.Index(fields=['account_type']),
            models.Index(fields=['account_category']),
            models.Index(fields=['parent_account']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.account_code} - {self.account_name_persian}"
    
    def clean(self):
        """Validate account data."""
        super().clean()
        
        # Validate account code format
        if not self.account_code.isdigit():
            raise ValidationError({
                'account_code': _('Account code must contain only digits')
            })
        
        # Validate parent account relationship
        if self.parent_account:
            if self.parent_account == self:
                raise ValidationError({
                    'parent_account': _('Account cannot be its own parent')
                })
            
            # Check for circular references
            parent = self.parent_account
            while parent:
                if parent == self:
                    raise ValidationError({
                        'parent_account': _('Circular reference detected in account hierarchy')
                    })
                parent = parent.parent_account
            
            # Set account level based on parent
            self.account_level = self.parent_account.account_level + 1
        
        # Validate normal balance based on account type
        expected_normal_balance = {
            'asset': 'debit',
            'expense': 'debit',
            'cost_of_goods_sold': 'debit',
            'liability': 'credit',
            'equity': 'credit',
            'revenue': 'credit',
        }
        
        if self.account_type in expected_normal_balance:
            if self.normal_balance != expected_normal_balance[self.account_type]:
                raise ValidationError({
                    'normal_balance': _(f'Normal balance for {self.get_account_type_display()} should be {expected_normal_balance[self.account_type]}')
                })
    
    def save(self, *args, **kwargs):
        """Override save to set account level and validate."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def full_account_name(self):
        """Return full account name with code."""
        return f"{self.account_code} - {self.account_name_persian}"
    
    @property
    def account_path(self):
        """Return hierarchical path of account."""
        path = []
        current = self
        while current:
            path.insert(0, current.account_name_persian)
            current = current.parent_account
        return ' > '.join(path)
    
    def get_children(self):
        """Get all child accounts."""
        return self.sub_accounts.filter(is_active=True).order_by('account_code')
    
    def get_all_descendants(self):
        """Get all descendant accounts recursively."""
        descendants = []
        for child in self.get_children():
            descendants.append(child)
            descendants.extend(child.get_all_descendants())
        return descendants
    
    def update_balance(self, amount, is_debit=True):
        """Update account balance."""
        if is_debit:
            if self.normal_balance == 'debit':
                self.current_balance += amount
            else:
                self.current_balance -= amount
        else:  # Credit
            if self.normal_balance == 'credit':
                self.current_balance += amount
            else:
                self.current_balance -= amount
        
        self.save(update_fields=['current_balance', 'updated_at'])
    
    def get_balance_as_of_date(self, date):
        """Get account balance as of specific date."""
        from django.db.models import Sum, Q
        
        # Get all journal entry lines for this account up to the date
        debit_sum = JournalEntryLine.objects.filter(
            account=self,
            journal_entry__entry_date__lte=date,
            journal_entry__status='posted'
        ).aggregate(total=Sum('debit_amount'))['total'] or Decimal('0.00')
        
        credit_sum = JournalEntryLine.objects.filter(
            account=self,
            journal_entry__entry_date__lte=date,
            journal_entry__status='posted'
        ).aggregate(total=Sum('credit_amount'))['total'] or Decimal('0.00')
        
        if self.normal_balance == 'debit':
            return debit_sum - credit_sum
        else:
            return credit_sum - debit_sum


class JournalEntry(TenantAwareModel):
    """
    Journal Entry model for transaction recording (ثبت اسناد حسابداری).
    
    Implements double-entry bookkeeping with Persian terminology
    and Shamsi calendar support.
    """
    
    ENTRY_TYPES = [
        ('general', _('سند عمومی (General Entry)')),
        ('sales', _('سند فروش (Sales Entry)')),
        ('purchase', _('سند خرید (Purchase Entry)')),
        ('payment', _('سند پرداخت (Payment Entry)')),
        ('receipt', _('سند دریافت (Receipt Entry)')),
        ('adjustment', _('سند تعدیل (Adjustment Entry)')),
        ('closing', _('سند اختتامیه (Closing Entry)')),
    ]
    
    STATUS_CHOICES = [
        ('draft', _('پیش‌نویس (Draft)')),
        ('pending', _('در انتظار تایید (Pending Approval)')),
        ('posted', _('ثبت شده (Posted)')),
        ('cancelled', _('لغو شده (Cancelled)')),
    ]
    
    # Entry identification
    entry_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('شماره سند (Entry Number)'),
        help_text=_('Unique journal entry number')
    )
    
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('شماره مرجع (Reference Number)'),
        help_text=_('External reference number (invoice, receipt, etc.)')
    )
    
    # Entry details
    entry_type = models.CharField(
        max_length=20,
        choices=ENTRY_TYPES,
        default='general',
        verbose_name=_('نوع سند (Entry Type)')
    )
    
    entry_date = models.DateField(
        verbose_name=_('تاریخ سند (Entry Date)')
    )
    
    entry_date_shamsi = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('تاریخ شمسی (Shamsi Date)'),
        help_text=_('Format: 1402/01/01')
    )
    
    # Description
    description = models.TextField(
        verbose_name=_('شرح سند (Description)'),
        help_text=_('Detailed description of the transaction')
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name=_('یادداشت‌ها (Notes)')
    )
    
    # Status and approval
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name=_('وضعیت (Status)')
    )
    
    posted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('زمان ثبت (Posted At)')
    )
    
    posted_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posted_journal_entries',
        verbose_name=_('ثبت شده توسط (Posted By)')
    )
    
    # Totals (for validation)
    total_debit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('مجموع بدهکار (Total Debit)')
    )
    
    total_credit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('مجموع بستانکار (Total Credit)')
    )
    
    # Source tracking
    source_document_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('نوع سند مبدا (Source Document Type)'),
        help_text=_('Type of source document (invoice, receipt, etc.)')
    )
    
    source_document_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('شناسه سند مبدا (Source Document ID)')
    )
    
    class Meta:
        verbose_name = _('سند حسابداری (Journal Entry)')
        verbose_name_plural = _('اسناد حسابداری (Journal Entries)')
        ordering = ['-entry_date', '-entry_number']
        indexes = [
            models.Index(fields=['entry_number']),
            models.Index(fields=['entry_date']),
            models.Index(fields=['entry_type']),
            models.Index(fields=['status']),
            models.Index(fields=['reference_number']),
        ]
    
    def __str__(self):
        return f"{self.entry_number} - {self.description[:50]}"
    
    def clean(self):
        """Validate journal entry."""
        super().clean()
        
        # Convert Gregorian to Shamsi if not provided
        if self.entry_date and not self.entry_date_shamsi:
            shamsi_date = jdatetime.date.fromgregorian(date=self.entry_date)
            self.entry_date_shamsi = shamsi_date.strftime('%Y/%m/%d')
        
        # Validate that entry is balanced (if has lines)
        if hasattr(self, 'lines') and self.lines.exists():
            total_debit = sum(line.debit_amount for line in self.lines.all())
            total_credit = sum(line.credit_amount for line in self.lines.all())
            
            if total_debit != total_credit:
                raise ValidationError({
                    '__all__': _('Journal entry must be balanced. Total debits must equal total credits.')
                })
    
    def save(self, *args, **kwargs):
        """Override save to generate entry number and update totals."""
        if not self.entry_number:
            self.entry_number = self.generate_entry_number()
        
        # Convert date to Shamsi if needed
        if self.entry_date and not self.entry_date_shamsi:
            shamsi_date = jdatetime.date.fromgregorian(date=self.entry_date)
            self.entry_date_shamsi = shamsi_date.strftime('%Y/%m/%d')
        
        super().save(*args, **kwargs)
        
        # Update totals after saving
        self.update_totals()
    
    def generate_entry_number(self):
        """Generate unique entry number."""
        from django.utils import timezone
        import random
        
        # Format: JE-YYYYMMDD-NNNN
        date_str = timezone.now().strftime('%Y%m%d')
        
        # Get next sequence number for today
        today_entries = JournalEntry.objects.filter(
            entry_number__startswith=f'JE-{date_str}'
        ).count()
        
        sequence = today_entries + 1
        return f"JE-{date_str}-{sequence:04d}"
    
    def update_totals(self):
        """Update total debit and credit amounts."""
        if hasattr(self, 'lines'):
            self.total_debit = sum(line.debit_amount for line in self.lines.all())
            self.total_credit = sum(line.credit_amount for line in self.lines.all())
            
            # Save without triggering save again
            JournalEntry.objects.filter(pk=self.pk).update(
                total_debit=self.total_debit,
                total_credit=self.total_credit,
                updated_at=timezone.now()
            )
    
    @property
    def is_balanced(self):
        """Check if journal entry is balanced."""
        return self.total_debit == self.total_credit
    
    @property
    def can_be_posted(self):
        """Check if entry can be posted."""
        return (
            self.status == 'draft' and
            self.is_balanced and
            self.lines.exists() and
            self.total_debit > 0
        )
    
    def post(self, user=None):
        """Post the journal entry."""
        if not self.can_be_posted:
            raise ValidationError(_('Journal entry cannot be posted. Check that it is balanced and has lines.'))
        
        self.status = 'posted'
        self.posted_at = timezone.now()
        if user:
            self.posted_by = user
        
        self.save(update_fields=['status', 'posted_at', 'posted_by', 'updated_at'])
        
        # Update account balances
        for line in self.lines.all():
            if line.debit_amount > 0:
                line.account.update_balance(line.debit_amount, is_debit=True)
            if line.credit_amount > 0:
                line.account.update_balance(line.credit_amount, is_debit=False)
    
    def cancel(self, reason=""):
        """Cancel the journal entry."""
        if self.status == 'posted':
            # Create reversing entry
            self.create_reversing_entry(reason)
        
        self.status = 'cancelled'
        if reason:
            self.notes += f"\nCancelled: {reason}"
        
        self.save(update_fields=['status', 'notes', 'updated_at'])
    
    def create_reversing_entry(self, reason=""):
        """Create a reversing entry to cancel posted entry."""
        reversing_entry = JournalEntry.objects.create(
            entry_type='adjustment',
            entry_date=timezone.now().date(),
            description=f"Reversing entry for {self.entry_number}: {reason}",
            reference_number=f"REV-{self.entry_number}",
            notes=f"Reversing entry for journal entry {self.entry_number}"
        )
        
        # Create reversing lines
        for line in self.lines.all():
            JournalEntryLine.objects.create(
                journal_entry=reversing_entry,
                account=line.account,
                description=f"Reversing: {line.description}",
                debit_amount=line.credit_amount,  # Reverse the amounts
                credit_amount=line.debit_amount,
                line_number=line.line_number
            )
        
        # Post the reversing entry
        reversing_entry.post()
        
        return reversing_entry


class JournalEntryLine(TenantAwareModel):
    """
    Journal Entry Line model for individual account postings.
    """
    
    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name=_('سند حسابداری (Journal Entry)')
    )
    
    account = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.PROTECT,
        related_name='journal_lines',
        verbose_name=_('حساب (Account)')
    )
    
    line_number = models.PositiveIntegerField(
        verbose_name=_('شماره ردیف (Line Number)')
    )
    
    description = models.CharField(
        max_length=500,
        verbose_name=_('شرح (Description)')
    )
    
    debit_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('مبلغ بدهکار (Debit Amount)')
    )
    
    credit_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('مبلغ بستانکار (Credit Amount)')
    )
    
    # Additional tracking
    cost_center = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('مرکز هزینه (Cost Center)')
    )
    
    project_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('کد پروژه (Project Code)')
    )
    
    class Meta:
        verbose_name = _('ردیف سند (Journal Entry Line)')
        verbose_name_plural = _('ردیف‌های سند (Journal Entry Lines)')
        ordering = ['journal_entry', 'line_number']
        unique_together = ['journal_entry', 'line_number']
        indexes = [
            models.Index(fields=['journal_entry', 'line_number']),
            models.Index(fields=['account']),
        ]
    
    def __str__(self):
        return f"{self.journal_entry.entry_number} - Line {self.line_number}"
    
    def clean(self):
        """Validate journal entry line."""
        super().clean()
        
        # Ensure only one of debit or credit has value
        if self.debit_amount > 0 and self.credit_amount > 0:
            raise ValidationError({
                '__all__': _('A line cannot have both debit and credit amounts')
            })
        
        if self.debit_amount == 0 and self.credit_amount == 0:
            raise ValidationError({
                '__all__': _('A line must have either debit or credit amount')
            })
        
        # Check if account allows posting
        if self.account and not self.account.allow_posting:
            raise ValidationError({
                'account': _('Cannot post to this account. Posting is not allowed.')
            })
    
    def save(self, *args, **kwargs):
        """Override save to set line number and update journal entry totals."""
        if not self.line_number:
            # Get next line number for this journal entry
            max_line = self.journal_entry.lines.aggregate(
                max_line=models.Max('line_number')
            )['max_line'] or 0
            self.line_number = max_line + 1
        
        super().save(*args, **kwargs)
        
        # Update journal entry totals
        self.journal_entry.update_totals()
    
    @property
    def amount(self):
        """Get the line amount (debit or credit)."""
        return self.debit_amount if self.debit_amount > 0 else self.credit_amount
    
    @property
    def is_debit(self):
        """Check if this is a debit line."""
        return self.debit_amount > 0
    
    @property
    def is_credit(self):
        """Check if this is a credit line."""
        return self.credit_amount > 0


class GeneralLedger(TenantAwareModel):
    """
    General Ledger model (دفتر کل).
    
    Maintains summary balances for all accounts with period tracking.
    """
    
    account = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.CASCADE,
        related_name='general_ledger_entries',
        verbose_name=_('حساب (Account)')
    )
    
    # Period information
    fiscal_year = models.CharField(
        max_length=10,
        verbose_name=_('سال مالی (Fiscal Year)'),
        help_text=_('Shamsi fiscal year (e.g., 1402)')
    )
    
    period_month = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name=_('ماه دوره (Period Month)'),
        help_text=_('Shamsi month (1-12)')
    )
    
    # Balance information
    opening_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('مانده ابتدای دوره (Opening Balance)')
    )
    
    period_debit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('مجموع بدهکار دوره (Period Debit Total)')
    )
    
    period_credit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('مجموع بستانکار دوره (Period Credit Total)')
    )
    
    closing_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('مانده پایان دوره (Closing Balance)')
    )
    
    # Status
    is_closed = models.BooleanField(
        default=False,
        verbose_name=_('بسته شده (Is Closed)'),
        help_text=_('Whether this period is closed for posting')
    )
    
    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('زمان بستن (Closed At)')
    )
    
    closed_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='closed_general_ledger_entries',
        verbose_name=_('بسته شده توسط (Closed By)')
    )
    
    class Meta:
        verbose_name = _('دفتر کل (General Ledger)')
        verbose_name_plural = _('دفتر کل (General Ledger)')
        unique_together = ['account', 'fiscal_year', 'period_month']
        ordering = ['fiscal_year', 'period_month', 'account__account_code']
        indexes = [
            models.Index(fields=['account', 'fiscal_year', 'period_month']),
            models.Index(fields=['fiscal_year', 'period_month']),
            models.Index(fields=['is_closed']),
        ]
    
    def __str__(self):
        return f"{self.account.account_code} - {self.fiscal_year}/{self.period_month:02d}"
    
    def calculate_closing_balance(self):
        """Calculate closing balance based on opening balance and period activity."""
        if self.account.normal_balance == 'debit':
            self.closing_balance = self.opening_balance + self.period_debit - self.period_credit
        else:
            self.closing_balance = self.opening_balance + self.period_credit - self.period_debit
        
        return self.closing_balance
    
    def update_period_activity(self):
        """Update period debit and credit totals from journal entries."""
        from django.db.models import Sum
        
        # Get Shamsi date range for the period
        start_date, end_date = self.get_period_date_range()
        
        # Calculate period totals
        period_totals = JournalEntryLine.objects.filter(
            account=self.account,
            journal_entry__entry_date__gte=start_date,
            journal_entry__entry_date__lte=end_date,
            journal_entry__status='posted'
        ).aggregate(
            total_debit=Sum('debit_amount'),
            total_credit=Sum('credit_amount')
        )
        
        self.period_debit = period_totals['total_debit'] or Decimal('0.00')
        self.period_credit = period_totals['total_credit'] or Decimal('0.00')
        
        # Calculate closing balance
        self.calculate_closing_balance()
        
        self.save(update_fields=['period_debit', 'period_credit', 'closing_balance', 'updated_at'])
    
    def get_period_date_range(self):
        """Get Gregorian date range for the Shamsi fiscal period."""
        # Convert Shamsi fiscal year/month to Gregorian dates
        shamsi_start = jdatetime.date(int(self.fiscal_year), self.period_month, 1)
        
        # Get last day of Shamsi month
        if self.period_month == 12:
            next_month = jdatetime.date(int(self.fiscal_year) + 1, 1, 1)
        else:
            next_month = jdatetime.date(int(self.fiscal_year), self.period_month + 1, 1)
        
        shamsi_end = next_month - jdatetime.timedelta(days=1)
        
        # Convert to Gregorian
        start_date = shamsi_start.togregorian()
        end_date = shamsi_end.togregorian()
        
        return start_date, end_date
    
    def close_period(self, user=None):
        """Close the period for posting."""
        if self.is_closed:
            raise ValidationError(_('Period is already closed'))
        
        # Update period activity before closing
        self.update_period_activity()
        
        self.is_closed = True
        self.closed_at = timezone.now()
        if user:
            self.closed_by = user
        
        self.save(update_fields=['is_closed', 'closed_at', 'closed_by', 'updated_at'])
    
    def reopen_period(self, user=None):
        """Reopen the period for posting."""
        if not self.is_closed:
            raise ValidationError(_('Period is not closed'))
        
        self.is_closed = False
        self.closed_at = None
        self.closed_by = None
        
        self.save(update_fields=['is_closed', 'closed_at', 'closed_by', 'updated_at'])


class SubsidiaryLedger(TenantAwareModel):
    """
    Subsidiary Ledger model (دفتر معین).
    
    Detailed transaction history for specific accounts with full audit trail.
    """
    
    account = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.CASCADE,
        related_name='subsidiary_ledger_entries',
        verbose_name=_('حساب (Account)')
    )
    
    journal_entry_line = models.OneToOneField(
        JournalEntryLine,
        on_delete=models.CASCADE,
        related_name='subsidiary_ledger_entry',
        verbose_name=_('ردیف سند (Journal Entry Line)')
    )
    
    # Transaction details
    transaction_date = models.DateField(
        verbose_name=_('تاریخ تراکنش (Transaction Date)')
    )
    
    transaction_date_shamsi = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('تاریخ شمسی (Shamsi Date)')
    )
    
    description = models.TextField(
        verbose_name=_('شرح (Description)')
    )
    
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('شماره مرجع (Reference Number)')
    )
    
    # Amounts
    debit_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('مبلغ بدهکار (Debit Amount)')
    )
    
    credit_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('مبلغ بستانکار (Credit Amount)')
    )
    
    running_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('مانده جاری (Running Balance)')
    )
    
    # Additional tracking
    fiscal_year = models.CharField(
        max_length=10,
        verbose_name=_('سال مالی (Fiscal Year)')
    )
    
    period_month = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name=_('ماه دوره (Period Month)')
    )
    
    class Meta:
        verbose_name = _('دفتر معین (Subsidiary Ledger)')
        verbose_name_plural = _('دفتر معین (Subsidiary Ledger)')
        ordering = ['account', 'transaction_date', 'journal_entry_line__journal_entry__entry_number']
        indexes = [
            models.Index(fields=['account', 'transaction_date']),
            models.Index(fields=['fiscal_year', 'period_month']),
            models.Index(fields=['reference_number']),
        ]
    
    def __str__(self):
        return f"{self.account.account_code} - {self.transaction_date} - {self.description[:50]}"
    
    def save(self, *args, **kwargs):
        """Override save to populate fields from journal entry line."""
        if self.journal_entry_line:
            # Copy data from journal entry line
            self.transaction_date = self.journal_entry_line.journal_entry.entry_date
            self.transaction_date_shamsi = self.journal_entry_line.journal_entry.entry_date_shamsi
            self.description = self.journal_entry_line.description
            self.reference_number = self.journal_entry_line.journal_entry.reference_number
            self.debit_amount = self.journal_entry_line.debit_amount
            self.credit_amount = self.journal_entry_line.credit_amount
            
            # Set fiscal year and period
            shamsi_date = jdatetime.date.fromgregorian(date=self.transaction_date)
            self.fiscal_year = str(shamsi_date.year)
            self.period_month = shamsi_date.month
        
        super().save(*args, **kwargs)
        
        # Update running balance after save
        self.update_running_balance()
    
    def update_running_balance(self):
        """Update running balance based on previous entries."""
        # Get previous balance
        previous_entry = SubsidiaryLedger.objects.filter(
            account=self.account,
            transaction_date__lt=self.transaction_date
        ).order_by('-transaction_date', '-id').first()
        
        if previous_entry:
            previous_balance = previous_entry.running_balance
        else:
            previous_balance = Decimal('0.00')
        
        # Calculate new running balance
        if self.account.normal_balance == 'debit':
            self.running_balance = previous_balance + self.debit_amount - self.credit_amount
        else:
            self.running_balance = previous_balance + self.credit_amount - self.debit_amount
        
        # Update without triggering save again
        SubsidiaryLedger.objects.filter(pk=self.pk).update(
            running_balance=self.running_balance,
            updated_at=timezone.now()
        )
        
        # Update subsequent entries
        self.update_subsequent_balances()
    
    def update_subsequent_balances(self):
        """Update running balances for all subsequent entries."""
        subsequent_entries = SubsidiaryLedger.objects.filter(
            account=self.account,
            transaction_date__gt=self.transaction_date
        ).order_by('transaction_date', 'id')
        
        current_balance = self.running_balance
        
        for entry in subsequent_entries:
            if self.account.normal_balance == 'debit':
                current_balance = current_balance + entry.debit_amount - entry.credit_amount
            else:
                current_balance = current_balance + entry.credit_amount - entry.debit_amount
            
            SubsidiaryLedger.objects.filter(pk=entry.pk).update(
                running_balance=current_balance,
                updated_at=timezone.now()
            )


class BankAccount(TenantAwareModel):
    """
    Iranian Bank Account model for banking operations.
    
    Supports Iranian banking system with IBAN, SHEBA, and local bank codes.
    """
    
    ACCOUNT_TYPES = [
        ('checking', _('حساب جاری (Checking Account)')),
        ('savings', _('حساب پس‌انداز (Savings Account)')),
        ('term_deposit', _('سپرده مدت‌دار (Term Deposit)')),
        ('loan', _('حساب وام (Loan Account)')),
    ]
    
    BANK_NAMES = [
        ('melli', _('بانک ملی ایران (Bank Melli Iran)')),
        ('saderat', _('بانک صادرات ایران (Bank Saderat Iran)')),
        ('tejarat', _('بانک تجارت (Bank Tejarat)')),
        ('mellat', _('بانک ملت (Bank Mellat)')),
        ('parsian', _('بانک پارسیان (Parsian Bank)')),
        ('pasargad', _('بانک پاسارگاد (Pasargad Bank)')),
        ('eghtesad_novin', _('بانک اقتصاد نوین (EN Bank)')),
        ('saman', _('بانک سامان (Saman Bank)')),
        ('sina', _('بانک سینا (Sina Bank)')),
        ('dey', _('بانک دی (Dey Bank)')),
        ('karafarin', _('بانک کارآفرین (Karafarin Bank)')),
        ('other', _('سایر (Other)')),
    ]
    
    # Account identification
    account_name = models.CharField(
        max_length=200,
        verbose_name=_('نام حساب (Account Name)')
    )
    
    account_number = models.CharField(
        max_length=50,
        verbose_name=_('شماره حساب (Account Number)')
    )
    
    iban = models.CharField(
        max_length=26,
        blank=True,
        validators=[RegexValidator(
            regex=r'^IR\d{24}$',
            message=_('IBAN must be in format: IR followed by 24 digits')
        )],
        verbose_name=_('شماره شبا (IBAN)'),
        help_text=_('Iranian IBAN format: IR + 24 digits')
    )
    
    # Bank information
    bank_name = models.CharField(
        max_length=50,
        choices=BANK_NAMES,
        verbose_name=_('نام بانک (Bank Name)')
    )
    
    bank_branch = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('شعبه (Branch)')
    )
    
    bank_branch_code = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('کد شعبه (Branch Code)')
    )
    
    # Account details
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPES,
        verbose_name=_('نوع حساب (Account Type)')
    )
    
    currency = models.CharField(
        max_length=10,
        default='IRR',
        verbose_name=_('واحد پول (Currency)'),
        help_text=_('IRR for Iranian Rial, USD, EUR, etc.')
    )
    
    # Balance tracking
    current_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('موجودی جاری (Current Balance)')
    )
    
    available_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('موجودی قابل برداشت (Available Balance)')
    )
    
    # Account status
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('فعال (Is Active)')
    )
    
    is_default = models.BooleanField(
        default=False,
        verbose_name=_('حساب پیش‌فرض (Default Account)'),
        help_text=_('Default account for transactions')
    )
    
    # Account holder information
    account_holder_name = models.CharField(
        max_length=200,
        verbose_name=_('نام صاحب حساب (Account Holder Name)')
    )
    
    account_holder_national_id = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('کد ملی صاحب حساب (Account Holder National ID)')
    )
    
    # Additional information
    opening_date = models.DateField(
        verbose_name=_('تاریخ افتتاح (Opening Date)')
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name=_('یادداشت‌ها (Notes)')
    )
    
    # Chart of accounts integration
    chart_account = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bank_accounts',
        verbose_name=_('حساب در فهرست حساب‌ها (Chart Account)'),
        help_text=_('Corresponding account in chart of accounts')
    )
    
    class Meta:
        verbose_name = _('حساب بانکی (Bank Account)')
        verbose_name_plural = _('حساب‌های بانکی (Bank Accounts)')
        ordering = ['bank_name', 'account_name']
        indexes = [
            models.Index(fields=['account_number']),
            models.Index(fields=['iban']),
            models.Index(fields=['bank_name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_default']),
        ]
    
    def __str__(self):
        return f"{self.account_name} - {self.get_bank_name_display()}"
    
    def clean(self):
        """Validate bank account data."""
        super().clean()
        
        # Validate IBAN format
        if self.iban:
            if not self.iban.startswith('IR'):
                raise ValidationError({
                    'iban': _('Iranian IBAN must start with IR')
                })
            
            if len(self.iban) != 26:
                raise ValidationError({
                    'iban': _('Iranian IBAN must be exactly 26 characters')
                })
        
        # Validate national ID
        if self.account_holder_national_id:
            if not self.account_holder_national_id.isdigit() or len(self.account_holder_national_id) != 10:
                raise ValidationError({
                    'account_holder_national_id': _('National ID must be exactly 10 digits')
                })
    
    def save(self, *args, **kwargs):
        """Override save to handle default account logic."""
        # If this is set as default, unset other defaults
        if self.is_default:
            BankAccount.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        
        super().save(*args, **kwargs)
    
    def update_balance(self, amount, transaction_type='deposit'):
        """Update account balance."""
        if transaction_type == 'deposit':
            self.current_balance += amount
            self.available_balance += amount
        elif transaction_type == 'withdrawal':
            self.current_balance -= amount
            self.available_balance -= amount
        elif transaction_type == 'hold':
            # Hold amount (reduce available but not current)
            self.available_balance -= amount
        elif transaction_type == 'release_hold':
            # Release held amount
            self.available_balance += amount
        
        self.save(update_fields=['current_balance', 'available_balance', 'updated_at'])
    
    @property
    def held_amount(self):
        """Calculate held amount (difference between current and available)."""
        return self.current_balance - self.available_balance
    
    @property
    def masked_account_number(self):
        """Return masked account number for security."""
        if len(self.account_number) > 4:
            return f"****{self.account_number[-4:]}"
        return self.account_number
    
    @property
    def masked_iban(self):
        """Return masked IBAN for security."""
        if self.iban and len(self.iban) > 8:
            return f"{self.iban[:4]}****{self.iban[-4:]}"
        return self.iban


class ChequeManagement(TenantAwareModel):
    """
    Iranian Cheque Management model for cheque lifecycle tracking.
    
    Handles both issued and received cheques with Iranian banking standards.
    """
    
    CHEQUE_TYPES = [
        ('issued', _('چک صادره (Issued Cheque)')),
        ('received', _('چک دریافتی (Received Cheque)')),
    ]
    
    CHEQUE_STATUS = [
        ('pending', _('در انتظار (Pending)')),
        ('presented', _('ارائه شده (Presented)')),
        ('cleared', _('تسویه شده (Cleared)')),
        ('bounced', _('برگشتی (Bounced)')),
        ('cancelled', _('لغو شده (Cancelled)')),
        ('replaced', _('جایگزین شده (Replaced)')),
    ]
    
    BOUNCE_REASONS = [
        ('insufficient_funds', _('عدم کفایت موجودی (Insufficient Funds)')),
        ('signature_mismatch', _('عدم تطابق امضا (Signature Mismatch)')),
        ('account_closed', _('حساب مسدود (Account Closed)')),
        ('date_issue', _('مشکل تاریخ (Date Issue)')),
        ('amount_mismatch', _('عدم تطابق مبلغ (Amount Mismatch)')),
        ('other', _('سایر (Other)')),
    ]
    
    # Cheque identification
    cheque_number = models.CharField(
        max_length=50,
        verbose_name=_('شماره چک (Cheque Number)')
    )
    
    cheque_type = models.CharField(
        max_length=20,
        choices=CHEQUE_TYPES,
        verbose_name=_('نوع چک (Cheque Type)')
    )
    
    # Bank and account information
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.PROTECT,
        related_name='cheques',
        verbose_name=_('حساب بانکی (Bank Account)')
    )
    
    # Cheque details
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('مبلغ (Amount)')
    )
    
    issue_date = models.DateField(
        verbose_name=_('تاریخ صدور (Issue Date)')
    )
    
    due_date = models.DateField(
        verbose_name=_('تاریخ سررسید (Due Date)')
    )
    
    issue_date_shamsi = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('تاریخ صدور شمسی (Shamsi Issue Date)')
    )
    
    due_date_shamsi = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('تاریخ سررسید شمسی (Shamsi Due Date)')
    )
    
    # Payee/Payer information
    payee_name = models.CharField(
        max_length=200,
        verbose_name=_('نام ذی‌نفع (Payee Name)'),
        help_text=_('Name of the person/company receiving the cheque')
    )
    
    payer_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('نام پرداخت‌کننده (Payer Name)'),
        help_text=_('Name of the person/company issuing the cheque (for received cheques)')
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=CHEQUE_STATUS,
        default='pending',
        verbose_name=_('وضعیت (Status)')
    )
    
    presentation_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('تاریخ ارائه (Presentation Date)')
    )
    
    clearance_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('تاریخ تسویه (Clearance Date)')
    )
    
    bounce_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('تاریخ برگشت (Bounce Date)')
    )
    
    bounce_reason = models.CharField(
        max_length=30,
        choices=BOUNCE_REASONS,
        blank=True,
        verbose_name=_('دلیل برگشت (Bounce Reason)')
    )
    
    # Additional information
    description = models.TextField(
        blank=True,
        verbose_name=_('توضیحات (Description)')
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name=_('یادداشت‌ها (Notes)')
    )
    
    # Reference to related transactions
    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cheques',
        verbose_name=_('سند حسابداری (Journal Entry)')
    )
    
    # Customer/Supplier reference
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cheques',
        verbose_name=_('مشتری (Customer)')
    )
    
    supplier = models.ForeignKey(
        'customers.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cheques',
        verbose_name=_('تامین‌کننده (Supplier)')
    )
    
    class Meta:
        verbose_name = _('مدیریت چک (Cheque Management)')
        verbose_name_plural = _('مدیریت چک‌ها (Cheque Management)')
        ordering = ['-due_date', '-issue_date']
        indexes = [
            models.Index(fields=['cheque_number']),
            models.Index(fields=['cheque_type']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['bank_account']),
        ]
    
    def __str__(self):
        return f"{self.get_cheque_type_display()} - {self.cheque_number} - {self.amount:,} ریال"
    
    def clean(self):
        """Validate cheque data."""
        super().clean()
        
        # Validate due date is after issue date
        if self.due_date and self.issue_date and self.due_date < self.issue_date:
            raise ValidationError({
                'due_date': _('Due date cannot be before issue date')
            })
        
        # Validate amount is positive
        if self.amount <= 0:
            raise ValidationError({
                'amount': _('Cheque amount must be positive')
            })
    
    def save(self, *args, **kwargs):
        """Override save to convert dates to Shamsi."""
        # Convert Gregorian dates to Shamsi
        if self.issue_date and not self.issue_date_shamsi:
            shamsi_date = jdatetime.date.fromgregorian(date=self.issue_date)
            self.issue_date_shamsi = shamsi_date.strftime('%Y/%m/%d')
        
        if self.due_date and not self.due_date_shamsi:
            shamsi_date = jdatetime.date.fromgregorian(date=self.due_date)
            self.due_date_shamsi = shamsi_date.strftime('%Y/%m/%d')
        
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        """Check if cheque is overdue."""
        if self.status in ['cleared', 'cancelled']:
            return False
        
        from django.utils import timezone
        today = timezone.now().date()
        return self.due_date < today
    
    @property
    def days_until_due(self):
        """Calculate days until due date."""
        from django.utils import timezone
        today = timezone.now().date()
        delta = self.due_date - today
        return delta.days
    
    @property
    def formatted_amount(self):
        """Return formatted amount in Persian numerals."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        return PersianNumberFormatter.format_currency(self.amount)
    
    def present_cheque(self, presentation_date=None):
        """Mark cheque as presented to bank."""
        if self.status != 'pending':
            raise ValidationError(_('Only pending cheques can be presented'))
        
        self.status = 'presented'
        self.presentation_date = presentation_date or timezone.now().date()
        self.save(update_fields=['status', 'presentation_date', 'updated_at'])
    
    def clear_cheque(self, clearance_date=None):
        """Mark cheque as cleared."""
        if self.status != 'presented':
            raise ValidationError(_('Only presented cheques can be cleared'))
        
        self.status = 'cleared'
        self.clearance_date = clearance_date or timezone.now().date()
        self.save(update_fields=['status', 'clearance_date', 'updated_at'])
        
        # Update bank account balance
        if self.cheque_type == 'received':
            self.bank_account.update_balance(self.amount, 'deposit')
        
        # Create journal entry for cleared cheque
        self.create_clearance_journal_entry()
    
    def bounce_cheque(self, bounce_reason, bounce_date=None, notes=""):
        """Mark cheque as bounced."""
        if self.status not in ['presented', 'pending']:
            raise ValidationError(_('Only pending or presented cheques can be bounced'))
        
        self.status = 'bounced'
        self.bounce_date = bounce_date or timezone.now().date()
        self.bounce_reason = bounce_reason
        if notes:
            self.notes += f"\nBounced: {notes}"
        
        self.save(update_fields=['status', 'bounce_date', 'bounce_reason', 'notes', 'updated_at'])
        
        # Create journal entry for bounced cheque
        self.create_bounce_journal_entry()
    
    def cancel_cheque(self, reason=""):
        """Cancel the cheque."""
        if self.status in ['cleared', 'bounced']:
            raise ValidationError(_('Cannot cancel cleared or bounced cheques'))
        
        self.status = 'cancelled'
        if reason:
            self.notes += f"\nCancelled: {reason}"
        
        self.save(update_fields=['status', 'notes', 'updated_at'])
    
    def create_clearance_journal_entry(self):
        """Create journal entry when cheque is cleared."""
        if self.journal_entry:
            return  # Already has journal entry
        
        # Create journal entry for cleared cheque
        entry = JournalEntry.objects.create(
            entry_type='receipt' if self.cheque_type == 'received' else 'payment',
            entry_date=self.clearance_date,
            description=f"Cheque cleared - {self.cheque_number}",
            reference_number=self.cheque_number
        )
        
        # Create journal entry lines
        if self.cheque_type == 'received':
            # Debit: Bank Account, Credit: Accounts Receivable or Cash
            JournalEntryLine.objects.create(
                journal_entry=entry,
                account=self.bank_account.chart_account,
                description=f"Cheque received - {self.cheque_number}",
                debit_amount=self.amount,
                line_number=1
            )
        else:  # issued
            # Credit: Bank Account, Debit: Accounts Payable or Expense
            JournalEntryLine.objects.create(
                journal_entry=entry,
                account=self.bank_account.chart_account,
                description=f"Cheque issued - {self.cheque_number}",
                credit_amount=self.amount,
                line_number=1
            )
        
        # Post the entry
        entry.post()
        
        # Link to this cheque
        self.journal_entry = entry
        self.save(update_fields=['journal_entry', 'updated_at'])
    
    def create_bounce_journal_entry(self):
        """Create journal entry when cheque bounces."""
        # Create journal entry for bounced cheque
        entry = JournalEntry.objects.create(
            entry_type='adjustment',
            entry_date=self.bounce_date,
            description=f"Cheque bounced - {self.cheque_number} - {self.get_bounce_reason_display()}",
            reference_number=f"BOUNCE-{self.cheque_number}"
        )
        
        # Reverse the original entry if it was posted
        if self.journal_entry and self.journal_entry.status == 'posted':
            # Create reversing lines
            for line in self.journal_entry.lines.all():
                JournalEntryLine.objects.create(
                    journal_entry=entry,
                    account=line.account,
                    description=f"Reversing bounced cheque - {line.description}",
                    debit_amount=line.credit_amount,  # Reverse amounts
                    credit_amount=line.debit_amount,
                    line_number=line.line_number
                )
        
        # Post the reversing entry
        entry.post()