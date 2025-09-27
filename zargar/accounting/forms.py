"""
Persian Accounting System Forms for ZARGAR Jewelry SaaS.

This module implements comprehensive Persian accounting forms following Iranian
accounting standards and terminology. All forms support Persian localization
with RTL layout and Shamsi calendar integration.
"""

from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from decimal import Decimal
import jdatetime

from zargar.core.widgets import PersianDateWidget, PersianNumberWidget
from .models import (
    ChartOfAccounts, JournalEntry, JournalEntryLine, 
    BankAccount, ChequeManagement
)


class ChartOfAccountsForm(forms.ModelForm):
    """
    Form for Chart of Accounts with Persian validation.
    """
    
    class Meta:
        model = ChartOfAccounts
        fields = [
            'account_code', 'account_name_persian', 'account_name_english',
            'account_type', 'account_category', 'parent_account',
            'normal_balance', 'allow_posting', 'description', 'notes'
        ]
        widgets = {
            'account_code': forms.TextInput(attrs={
                'class': 'form-control persian-input',
                'placeholder': 'مثال: 1101',
                'dir': 'ltr'
            }),
            'account_name_persian': forms.TextInput(attrs={
                'class': 'form-control persian-input',
                'placeholder': 'نام حساب به فارسی'
            }),
            'account_name_english': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Account Name in English (Optional)',
                'dir': 'ltr'
            }),
            'account_type': forms.Select(attrs={
                'class': 'form-select persian-input'
            }),
            'account_category': forms.Select(attrs={
                'class': 'form-select persian-input'
            }),
            'parent_account': forms.Select(attrs={
                'class': 'form-select persian-input'
            }),
            'normal_balance': forms.Select(attrs={
                'class': 'form-select persian-input'
            }),
            'allow_posting': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control persian-input',
                'rows': 3,
                'placeholder': 'توضیحات حساب'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control persian-input',
                'rows': 2,
                'placeholder': 'یادداشت‌ها'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter parent accounts to exclude self and descendants
        if self.instance.pk:
            descendants = self.instance.get_all_descendants()
            descendant_ids = [d.id for d in descendants] + [self.instance.id]
            self.fields['parent_account'].queryset = ChartOfAccounts.objects.filter(
                is_active=True
            ).exclude(id__in=descendant_ids)
        else:
            self.fields['parent_account'].queryset = ChartOfAccounts.objects.filter(
                is_active=True
            )
        
        # Add empty option for parent account
        self.fields['parent_account'].empty_label = "--- حساب اصلی ---"
    
    def clean_account_code(self):
        account_code = self.cleaned_data['account_code']
        
        # Check if account code already exists (excluding current instance)
        queryset = ChartOfAccounts.objects.filter(account_code=account_code)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError(_('کد حساب تکراری است.'))
        
        # Validate account code format
        if not account_code.isdigit():
            raise ValidationError(_('کد حساب باید فقط شامل اعداد باشد.'))
        
        if len(account_code) < 2 or len(account_code) > 10:
            raise ValidationError(_('کد حساب باید بین ۲ تا ۱۰ رقم باشد.'))
        
        return account_code
    
    def clean(self):
        cleaned_data = super().clean()
        account_type = cleaned_data.get('account_type')
        normal_balance = cleaned_data.get('normal_balance')
        
        # Validate normal balance based on account type
        if account_type and normal_balance:
            expected_normal_balance = {
                'asset': 'debit',
                'expense': 'debit',
                'cost_of_goods_sold': 'debit',
                'liability': 'credit',
                'equity': 'credit',
                'revenue': 'credit',
            }
            
            if account_type in expected_normal_balance:
                if normal_balance != expected_normal_balance[account_type]:
                    raise ValidationError({
                        'normal_balance': _(f'مانده طبیعی برای {dict(ChartOfAccounts.ACCOUNT_TYPES)[account_type]} باید {expected_normal_balance[account_type]} باشد.')
                    })
        
        return cleaned_data


class JournalEntryForm(forms.ModelForm):
    """
    Form for Journal Entry with Persian validation.
    """
    
    class Meta:
        model = JournalEntry
        fields = [
            'entry_type', 'entry_date', 'reference_number',
            'description', 'notes'
        ]
        widgets = {
            'entry_type': forms.Select(attrs={
                'class': 'form-select persian-input'
            }),
            'entry_date': PersianDateWidget(attrs={
                'class': 'form-control persian-input'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'شماره مرجع (اختیاری)',
                'dir': 'ltr'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control persian-input',
                'rows': 3,
                'placeholder': 'شرح سند حسابداری'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control persian-input',
                'rows': 2,
                'placeholder': 'یادداشت‌ها (اختیاری)'
            }),
        }
    
    def clean_entry_date(self):
        entry_date = self.cleaned_data['entry_date']
        
        # Convert to Shamsi for validation
        shamsi_date = jdatetime.date.fromgregorian(date=entry_date)
        
        # Validate that entry date is not in the future
        today_shamsi = jdatetime.date.today()
        if shamsi_date > today_shamsi:
            raise ValidationError(_('تاریخ سند نمی‌تواند در آینده باشد.'))
        
        return entry_date


class JournalEntryLineForm(forms.ModelForm):
    """
    Form for Journal Entry Line with Persian validation.
    """
    
    class Meta:
        model = JournalEntryLine
        fields = [
            'account', 'description', 'debit_amount', 'credit_amount',
            'cost_center', 'project_code'
        ]
        widgets = {
            'account': forms.Select(attrs={
                'class': 'form-select persian-input account-select',
                'required': True
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control persian-input',
                'placeholder': 'شرح ردیف',
                'required': True
            }),
            'debit_amount': PersianNumberWidget(attrs={
                'class': 'form-control persian-input amount-input',
                'placeholder': '۰',
                'step': '0.01',
                'min': '0'
            }),
            'credit_amount': PersianNumberWidget(attrs={
                'class': 'form-control persian-input amount-input',
                'placeholder': '۰',
                'step': '0.01',
                'min': '0'
            }),
            'cost_center': forms.TextInput(attrs={
                'class': 'form-control persian-input',
                'placeholder': 'مرکز هزینه (اختیاری)'
            }),
            'project_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'کد پروژه (اختیاری)',
                'dir': 'ltr'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter accounts to only show those that allow posting
        self.fields['account'].queryset = ChartOfAccounts.objects.filter(
            is_active=True, allow_posting=True
        ).order_by('account_code')
        
        # Add empty option
        self.fields['account'].empty_label = "--- انتخاب حساب ---"
    
    def clean(self):
        cleaned_data = super().clean()
        debit_amount = cleaned_data.get('debit_amount', Decimal('0'))
        credit_amount = cleaned_data.get('credit_amount', Decimal('0'))
        
        # Ensure only one of debit or credit has value
        if debit_amount > 0 and credit_amount > 0:
            raise ValidationError(_('یک ردیف نمی‌تواند هم بدهکار و هم بستانکار باشد.'))
        
        if debit_amount == 0 and credit_amount == 0:
            raise ValidationError(_('یک ردیف باید مبلغ بدهکار یا بستانکار داشته باشد.'))
        
        return cleaned_data


# Create formset for journal entry lines
JournalEntryLineFormSet = inlineformset_factory(
    JournalEntry,
    JournalEntryLine,
    form=JournalEntryLineForm,
    extra=2,
    min_num=2,
    validate_min=True,
    can_delete=True
)


class BankAccountForm(forms.ModelForm):
    """
    Form for Bank Account with Iranian banking validation.
    """
    
    class Meta:
        model = BankAccount
        fields = [
            'account_name', 'account_number', 'iban', 'bank_name',
            'bank_branch', 'bank_branch_code', 'account_type', 'currency',
            'account_holder_name', 'account_holder_national_id',
            'opening_date', 'is_default', 'notes', 'chart_account'
        ]
        widgets = {
            'account_name': forms.TextInput(attrs={
                'class': 'form-control persian-input',
                'placeholder': 'نام حساب'
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'شماره حساب',
                'dir': 'ltr'
            }),
            'iban': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'IR1234567890123456789012',
                'dir': 'ltr',
                'maxlength': '26'
            }),
            'bank_name': forms.Select(attrs={
                'class': 'form-select persian-input'
            }),
            'bank_branch': forms.TextInput(attrs={
                'class': 'form-control persian-input',
                'placeholder': 'نام شعبه'
            }),
            'bank_branch_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'کد شعبه',
                'dir': 'ltr'
            }),
            'account_type': forms.Select(attrs={
                'class': 'form-select persian-input'
            }),
            'currency': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'IRR',
                'dir': 'ltr'
            }),
            'account_holder_name': forms.TextInput(attrs={
                'class': 'form-control persian-input',
                'placeholder': 'نام صاحب حساب'
            }),
            'account_holder_national_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1234567890',
                'dir': 'ltr',
                'maxlength': '10'
            }),
            'opening_date': PersianDateWidget(attrs={
                'class': 'form-control persian-input'
            }),
            'is_default': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control persian-input',
                'rows': 3,
                'placeholder': 'یادداشت‌ها'
            }),
            'chart_account': forms.Select(attrs={
                'class': 'form-select persian-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter chart accounts to bank-related accounts
        self.fields['chart_account'].queryset = ChartOfAccounts.objects.filter(
            is_active=True,
            account_type='asset',
            account_category='current_assets'
        ).order_by('account_code')
        
        # Add empty option
        self.fields['chart_account'].empty_label = "--- انتخاب حساب ---"
    
    def clean_iban(self):
        iban = self.cleaned_data.get('iban', '').upper()
        
        if iban:
            # Validate Iranian IBAN format
            if not iban.startswith('IR'):
                raise ValidationError(_('شماره شبا باید با IR شروع شود.'))
            
            if len(iban) != 26:
                raise ValidationError(_('شماره شبا باید دقیقاً ۲۶ کاراکتر باشد.'))
            
            # Check if digits after IR are valid
            digits_part = iban[2:]
            if not digits_part.isdigit():
                raise ValidationError(_('شماره شبا باید بعد از IR فقط شامل اعداد باشد.'))
        
        return iban
    
    def clean_account_holder_national_id(self):
        national_id = self.cleaned_data.get('account_holder_national_id', '')
        
        if national_id:
            if not national_id.isdigit() or len(national_id) != 10:
                raise ValidationError(_('کد ملی باید دقیقاً ۱۰ رقم باشد.'))
        
        return national_id


class ChequeManagementForm(forms.ModelForm):
    """
    Form for Cheque Management with Iranian cheque validation.
    """
    
    class Meta:
        model = ChequeManagement
        fields = [
            'cheque_number', 'cheque_type', 'bank_account', 'amount',
            'issue_date', 'due_date', 'payee_name', 'payer_name',
            'description', 'notes', 'customer', 'supplier'
        ]
        widgets = {
            'cheque_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'شماره چک',
                'dir': 'ltr'
            }),
            'cheque_type': forms.Select(attrs={
                'class': 'form-select persian-input'
            }),
            'bank_account': forms.Select(attrs={
                'class': 'form-select persian-input'
            }),
            'amount': PersianNumberWidget(attrs={
                'class': 'form-control persian-input',
                'placeholder': 'مبلغ چک',
                'step': '0.01',
                'min': '0.01'
            }),
            'issue_date': PersianDateWidget(attrs={
                'class': 'form-control persian-input'
            }),
            'due_date': PersianDateWidget(attrs={
                'class': 'form-control persian-input'
            }),
            'payee_name': forms.TextInput(attrs={
                'class': 'form-control persian-input',
                'placeholder': 'نام ذی‌نفع'
            }),
            'payer_name': forms.TextInput(attrs={
                'class': 'form-control persian-input',
                'placeholder': 'نام پرداخت‌کننده (برای چک‌های دریافتی)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control persian-input',
                'rows': 3,
                'placeholder': 'توضیحات چک'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control persian-input',
                'rows': 2,
                'placeholder': 'یادداشت‌ها'
            }),
            'customer': forms.Select(attrs={
                'class': 'form-select persian-input'
            }),
            'supplier': forms.Select(attrs={
                'class': 'form-select persian-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter bank accounts to active ones
        self.fields['bank_account'].queryset = BankAccount.objects.filter(
            is_active=True
        ).order_by('bank_name', 'account_name')
        
        # Add empty options
        self.fields['bank_account'].empty_label = "--- انتخاب حساب بانکی ---"
        self.fields['customer'].empty_label = "--- انتخاب مشتری (اختیاری) ---"
        self.fields['supplier'].empty_label = "--- انتخاب تامین‌کننده (اختیاری) ---"
    
    def clean(self):
        cleaned_data = super().clean()
        issue_date = cleaned_data.get('issue_date')
        due_date = cleaned_data.get('due_date')
        amount = cleaned_data.get('amount')
        
        # Validate due date is after issue date
        if issue_date and due_date and due_date < issue_date:
            raise ValidationError({
                'due_date': _('تاریخ سررسید نمی‌تواند قبل از تاریخ صدور باشد.')
            })
        
        # Validate amount is positive
        if amount and amount <= 0:
            raise ValidationError({
                'amount': _('مبلغ چک باید مثبت باشد.')
            })
        
        return cleaned_data


class FinancialReportForm(forms.Form):
    """
    Form for financial report parameters.
    """
    
    REPORT_TYPES = [
        ('trial_balance', _('تراز آزمایشی (Trial Balance)')),
        ('profit_loss', _('صورت سود و زیان (P&L Statement)')),
        ('balance_sheet', _('ترازنامه (Balance Sheet)')),
    ]
    
    SHAMSI_MONTHS = [
        (1, 'فروردین'), (2, 'اردیبهشت'), (3, 'خرداد'),
        (4, 'تیر'), (5, 'مرداد'), (6, 'شهریور'),
        (7, 'مهر'), (8, 'آبان'), (9, 'آذر'),
        (10, 'دی'), (11, 'بهمن'), (12, 'اسفند')
    ]
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select persian-input'
        }),
        label=_('نوع گزارش')
    )
    
    fiscal_year = forms.CharField(
        max_length=4,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '1402',
            'dir': 'ltr'
        }),
        label=_('سال مالی')
    )
    
    period_month = forms.ChoiceField(
        choices=SHAMSI_MONTHS,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select persian-input'
        }),
        label=_('ماه دوره (برای تراز آزمایشی)')
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default fiscal year to current Shamsi year
        today = jdatetime.date.today()
        self.fields['fiscal_year'].initial = str(today.year)
        self.fields['period_month'].initial = today.month
    
    def clean_fiscal_year(self):
        fiscal_year = self.cleaned_data['fiscal_year']
        
        if not fiscal_year.isdigit() or len(fiscal_year) != 4:
            raise ValidationError(_('سال مالی باید ۴ رقم باشد.'))
        
        year = int(fiscal_year)
        if year < 1300 or year > 1500:
            raise ValidationError(_('سال مالی نامعتبر است.'))
        
        return fiscal_year


class ChequeStatusUpdateForm(forms.Form):
    """
    Form for updating cheque status.
    """
    
    ACTION_CHOICES = [
        ('present', _('ارائه چک')),
        ('clear', _('تسویه چک')),
        ('bounce', _('برگشت چک')),
        ('cancel', _('لغو چک')),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select persian-input'
        }),
        label=_('عملیات')
    )
    
    bounce_reason = forms.ChoiceField(
        choices=ChequeManagement.BOUNCE_REASONS,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select persian-input'
        }),
        label=_('دلیل برگشت')
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control persian-input',
            'rows': 3,
            'placeholder': 'یادداشت‌ها'
        }),
        label=_('یادداشت‌ها')
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        bounce_reason = cleaned_data.get('bounce_reason')
        
        # If action is bounce, bounce_reason is required
        if action == 'bounce' and not bounce_reason:
            raise ValidationError({
                'bounce_reason': _('برای برگشت چک، دلیل برگشت الزامی است.')
            })
        
        return cleaned_data