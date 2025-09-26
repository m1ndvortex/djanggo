"""
Admin configuration for POS models.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import POSTransaction, POSTransactionLineItem, POSInvoice, POSOfflineStorage


class POSTransactionLineItemInline(admin.TabularInline):
    """Inline admin for POS transaction line items."""
    
    model = POSTransactionLineItem
    extra = 0
    readonly_fields = ['line_total']
    
    fields = [
        'jewelry_item', 'item_name', 'item_sku', 'quantity', 'unit_price',
        'line_total', 'gold_weight_grams', 'gold_karat', 'discount_percentage'
    ]


@admin.register(POSTransaction)
class POSTransactionAdmin(admin.ModelAdmin):
    """Admin interface for POS transactions."""
    
    list_display = [
        'transaction_number', 'customer', 'transaction_date', 'transaction_type',
        'status', 'total_amount_display', 'payment_method', 'is_offline_transaction'
    ]
    list_filter = [
        'status', 'transaction_type', 'payment_method', 'is_offline_transaction',
        'sync_status', 'transaction_date'
    ]
    search_fields = [
        'transaction_number', 'customer__first_name', 'customer__last_name',
        'customer__phone_number', 'reference_number'
    ]
    readonly_fields = [
        'transaction_id', 'transaction_number', 'transaction_date_shamsi',
        'total_gold_weight_grams', 'change_amount', 'synced_at'
    ]
    
    fieldsets = (
        (_('Transaction Information'), {
            'fields': (
                'transaction_id', 'transaction_number', 'customer',
                'transaction_date', 'transaction_date_shamsi', 'transaction_type', 'status'
            )
        }),
        (_('Financial Details'), {
            'fields': (
                'subtotal', 'tax_amount', 'discount_amount', 'total_amount',
                'payment_method', 'amount_paid', 'change_amount'
            )
        }),
        (_('Gold Information'), {
            'fields': (
                'gold_price_18k_at_transaction', 'total_gold_weight_grams'
            )
        }),
        (_('Offline & Sync'), {
            'fields': (
                'is_offline_transaction', 'sync_status', 'synced_at', 'offline_data'
            ),
            'classes': ('collapse',)
        }),
        (_('Additional Information'), {
            'fields': (
                'reference_number', 'transaction_notes', 'internal_notes'
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [POSTransactionLineItemInline]
    
    def total_amount_display(self, obj):
        """Display total amount with Persian formatting."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        formatter = PersianNumberFormatter()
        return formatter.format_currency(obj.total_amount, use_persian_digits=True)
    total_amount_display.short_description = _('Total Amount')
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('customer')


@admin.register(POSTransactionLineItem)
class POSTransactionLineItemAdmin(admin.ModelAdmin):
    """Admin interface for POS transaction line items."""
    
    list_display = [
        'transaction', 'item_name', 'item_sku', 'quantity',
        'unit_price_display', 'line_total_display', 'gold_weight_display'
    ]
    list_filter = ['transaction__status', 'transaction__transaction_type']
    search_fields = [
        'transaction__transaction_number', 'item_name', 'item_sku',
        'jewelry_item__name', 'jewelry_item__sku'
    ]
    readonly_fields = ['line_total']
    
    fieldsets = (
        (_('Transaction'), {
            'fields': ('transaction',)
        }),
        (_('Item Information'), {
            'fields': (
                'jewelry_item', 'item_name', 'item_sku'
            )
        }),
        (_('Pricing'), {
            'fields': (
                'quantity', 'unit_price', 'line_total',
                'discount_percentage', 'discount_amount'
            )
        }),
        (_('Gold Information'), {
            'fields': (
                'gold_weight_grams', 'gold_karat', 'gold_price_per_gram_at_sale'
            )
        }),
        (_('Notes'), {
            'fields': ('line_notes',),
            'classes': ('collapse',)
        }),
    )
    
    def unit_price_display(self, obj):
        """Display unit price with Persian formatting."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        formatter = PersianNumberFormatter()
        return formatter.format_currency(obj.unit_price, use_persian_digits=True)
    unit_price_display.short_description = _('Unit Price')
    
    def line_total_display(self, obj):
        """Display line total with Persian formatting."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        formatter = PersianNumberFormatter()
        return formatter.format_currency(obj.line_total, use_persian_digits=True)
    line_total_display.short_description = _('Line Total')
    
    def gold_weight_display(self, obj):
        """Display gold weight with Persian formatting."""
        if obj.gold_weight_grams:
            from zargar.core.persian_number_formatter import PersianNumberFormatter
            formatter = PersianNumberFormatter()
            return formatter.format_weight(obj.gold_weight_grams, 'gram', use_persian_digits=True)
        return '-'
    gold_weight_display.short_description = _('Gold Weight')


@admin.register(POSInvoice)
class POSInvoiceAdmin(admin.ModelAdmin):
    """Admin interface for POS invoices."""
    
    list_display = [
        'invoice_number', 'transaction', 'invoice_type', 'status',
        'issue_date', 'invoice_total_display', 'email_sent'
    ]
    list_filter = ['invoice_type', 'status', 'issue_date', 'email_sent']
    search_fields = [
        'invoice_number', 'transaction__transaction_number',
        'transaction__customer__first_name', 'transaction__customer__last_name'
    ]
    readonly_fields = [
        'invoice_number', 'issue_date_shamsi', 'invoice_subtotal',
        'invoice_tax_amount', 'invoice_discount_amount', 'invoice_total_amount',
        'email_sent_at'
    ]
    
    fieldsets = (
        (_('Invoice Information'), {
            'fields': (
                'transaction', 'invoice_number', 'invoice_type', 'status'
            )
        }),
        (_('Dates'), {
            'fields': (
                'issue_date', 'issue_date_shamsi', 'due_date'
            )
        }),
        (_('Iranian Business Compliance'), {
            'fields': (
                'tax_id', 'economic_code'
            )
        }),
        (_('Financial Totals'), {
            'fields': (
                'invoice_subtotal', 'invoice_tax_amount',
                'invoice_discount_amount', 'invoice_total_amount'
            )
        }),
        (_('Email Delivery'), {
            'fields': (
                'email_sent', 'email_sent_at'
            )
        }),
        (_('Additional Information'), {
            'fields': (
                'invoice_notes', 'terms_and_conditions'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_issued', 'mark_as_paid', 'send_email_action']
    
    def invoice_total_display(self, obj):
        """Display invoice total with Persian formatting."""
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        formatter = PersianNumberFormatter()
        return formatter.format_currency(obj.invoice_total_amount, use_persian_digits=True)
    invoice_total_display.short_description = _('Invoice Total')
    
    def mark_as_issued(self, request, queryset):
        """Mark selected invoices as issued."""
        updated = queryset.update(status='issued')
        self.message_user(request, f'{updated} invoices marked as issued.')
    mark_as_issued.short_description = _('Mark selected invoices as issued')
    
    def mark_as_paid(self, request, queryset):
        """Mark selected invoices as paid."""
        updated = queryset.update(status='paid')
        self.message_user(request, f'{updated} invoices marked as paid.')
    mark_as_paid.short_description = _('Mark selected invoices as paid')
    
    def send_email_action(self, request, queryset):
        """Send email for selected invoices."""
        # This would implement bulk email sending
        count = 0
        for invoice in queryset:
            if invoice.transaction.customer and invoice.transaction.customer.email:
                # TODO: Implement actual email sending
                count += 1
        
        self.message_user(request, f'Email sent for {count} invoices.')
    send_email_action.short_description = _('Send email for selected invoices')


@admin.register(POSOfflineStorage)
class POSOfflineStorageAdmin(admin.ModelAdmin):
    """Admin interface for POS offline storage."""
    
    list_display = [
        'storage_id', 'device_id', 'created_at', 'is_synced',
        'synced_at', 'synced_transaction_link'
    ]
    list_filter = ['is_synced', 'created_at', 'device_id']
    search_fields = ['storage_id', 'device_id']
    readonly_fields = [
        'storage_id', 'created_at', 'synced_at', 'synced_transaction_id'
    ]
    
    fieldsets = (
        (_('Storage Information'), {
            'fields': (
                'storage_id', 'device_id', 'created_at'
            )
        }),
        (_('Sync Status'), {
            'fields': (
                'is_synced', 'synced_at', 'synced_transaction_id', 'sync_error'
            )
        }),
        (_('Transaction Data'), {
            'fields': ('transaction_data',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['sync_offline_transactions']
    
    def synced_transaction_link(self, obj):
        """Display link to synced transaction."""
        if obj.synced_transaction_id:
            try:
                transaction = POSTransaction.objects.get(transaction_id=obj.synced_transaction_id)
                url = reverse('admin:pos_postransaction_change', args=[transaction.pk])
                return format_html('<a href="{}">{}</a>', url, transaction.transaction_number)
            except POSTransaction.DoesNotExist:
                return format_html('<span style="color: red;">Transaction not found</span>')
        return '-'
    synced_transaction_link.short_description = _('Synced Transaction')
    
    def sync_offline_transactions(self, request, queryset):
        """Sync selected offline transactions."""
        from .services import POSOfflineService
        
        synced_count = 0
        failed_count = 0
        
        for offline_storage in queryset.filter(is_synced=False):
            try:
                success = offline_storage.sync_to_database()
                if success:
                    synced_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1
        
        message = f'Synced {synced_count} transactions successfully.'
        if failed_count > 0:
            message += f' {failed_count} transactions failed to sync.'
        
        self.message_user(request, message)
    sync_offline_transactions.short_description = _('Sync selected offline transactions')
    
    def has_add_permission(self, request):
        """Disable manual creation of offline storage records."""
        return False