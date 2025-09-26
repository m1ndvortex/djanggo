"""
Django management command to generate monthly invoices for all tenants.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
import jdatetime

from zargar.tenants.billing_services import BillingWorkflow
from zargar.tenants.admin_models import SuperAdmin


class Command(BaseCommand):
    help = 'Generate monthly invoices for all active tenants'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be generated without actually creating invoices',
        )
        parser.add_argument(
            '--admin-user',
            type=str,
            help='Username of admin user to associate with invoice generation',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        admin_username = options.get('admin_user')
        
        # Get admin user if specified
        admin_user = None
        if admin_username:
            try:
                admin_user = SuperAdmin.objects.get(username=admin_username)
            except SuperAdmin.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Admin user "{admin_username}" not found')
                )
                return
        
        current_date = jdatetime.date.today()
        self.stdout.write(f'Generating monthly invoices for {current_date.strftime("%Y/%m/%d")}...')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No invoices will be created'))
        
        try:
            if not dry_run:
                with transaction.atomic():
                    generated_invoices = BillingWorkflow.generate_monthly_invoices_batch(
                        admin_user=admin_user
                    )
                    
                    if generated_invoices:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Successfully generated {len(generated_invoices)} invoices:'
                            )
                        )
                        for invoice in generated_invoices:
                            self.stdout.write(
                                f'  - {invoice.invoice_number}: {invoice.tenant.name} '
                                f'({invoice.total_amount_toman:,.0f} Toman)'
                            )
                    else:
                        self.stdout.write(
                            self.style.WARNING('No invoices were generated (no tenants due for billing)')
                        )
            else:
                # Dry run - show what would be generated
                from zargar.tenants.admin_models import BillingCycle
                
                billing_cycles = BillingCycle.objects.filter(
                    is_active=True,
                    cycle_type='monthly',
                    next_billing_date__lte=current_date.togregorian(),
                    tenant__is_active=True
                )
                
                if billing_cycles:
                    self.stdout.write(f'Would generate {len(billing_cycles)} invoices:')
                    for billing_cycle in billing_cycles:
                        tenant = billing_cycle.tenant
                        amount = tenant.subscription_plan.monthly_price_toman if tenant.subscription_plan else 0
                        self.stdout.write(
                            f'  - {tenant.name}: {amount:,.0f} Toman '
                            f'(Next billing: {billing_cycle.next_billing_date})'
                        )
                else:
                    self.stdout.write('No invoices would be generated')
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error generating invoices: {str(e)}')
            )
            raise