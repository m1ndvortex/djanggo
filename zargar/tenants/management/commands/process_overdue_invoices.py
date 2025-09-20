"""
Django management command to process overdue invoices and send reminders.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
import jdatetime

from zargar.tenants.billing_services import BillingWorkflow
from zargar.tenants.admin_models import TenantInvoice


class Command(BaseCommand):
    help = 'Process overdue invoices and send reminders'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without making changes',
        )
        parser.add_argument(
            '--send-reminders',
            action='store_true',
            help='Send email reminders to tenants with overdue invoices',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        send_reminders = options['send_reminders']
        
        current_date = jdatetime.date.today()
        self.stdout.write(f'Processing overdue invoices as of {current_date.strftime("%Y/%m/%d")}...')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        try:
            # Get overdue invoices
            overdue_invoices = TenantInvoice.objects.filter(
                status='pending',
                due_date_shamsi__lt=current_date.togregorian()
            ).select_related('tenant', 'subscription_plan')
            
            if not overdue_invoices:
                self.stdout.write(self.style.SUCCESS('No overdue invoices found'))
                return
            
            self.stdout.write(f'Found {len(overdue_invoices)} overdue invoices:')
            
            suspended_tenants = []
            
            for invoice in overdue_invoices:
                due_date_shamsi = jdatetime.date.fromgregorian(date=invoice.due_date_shamsi)
                days_overdue = (current_date - due_date_shamsi).days
                grace_period = getattr(invoice.tenant.billing_cycle, 'grace_period_days', 7)
                
                self.stdout.write(
                    f'  - {invoice.invoice_number}: {invoice.tenant.name} '
                    f'({invoice.total_amount_toman:,.0f} Toman, {days_overdue} days overdue)'
                )
                
                if not dry_run:
                    # Mark as overdue
                    invoice.status = 'overdue'
                    invoice.save()
                    
                    # Send reminder if requested
                    if send_reminders:
                        from zargar.tenants.billing_services import InvoiceGenerator
                        InvoiceGenerator.send_invoice_notification(invoice, 'email')
                        self.stdout.write(f'    → Sent reminder email')
                    
                    # Check if tenant should be suspended
                    if days_overdue > grace_period and invoice.tenant.is_active:
                        invoice.tenant.is_active = False
                        invoice.tenant.save()
                        suspended_tenants.append(invoice.tenant.name)
                        self.stdout.write(
                            self.style.ERROR(f'    → Suspended tenant (>{grace_period} days overdue)')
                        )
                else:
                    # Dry run - show what would happen
                    if days_overdue > grace_period:
                        self.stdout.write(f'    → Would suspend tenant (>{grace_period} days overdue)')
                    if send_reminders:
                        self.stdout.write(f'    → Would send reminder email')
            
            if not dry_run:
                processed_count = BillingWorkflow.process_due_invoices()
                
                self.stdout.write(
                    self.style.SUCCESS(f'Processed {processed_count} overdue invoices')
                )
                
                if suspended_tenants:
                    self.stdout.write(
                        self.style.WARNING(f'Suspended {len(suspended_tenants)} tenants: {", ".join(suspended_tenants)}')
                    )
            else:
                self.stdout.write('Dry run completed - no changes made')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error processing overdue invoices: {str(e)}')
            )
            raise