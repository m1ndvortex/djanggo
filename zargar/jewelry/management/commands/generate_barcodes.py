"""
Management command to generate barcodes for jewelry items.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from zargar.tenants.models import Tenant
from zargar.jewelry.models import JewelryItem
from zargar.jewelry.barcode_models import BarcodeType
from zargar.jewelry.barcode_services import BarcodeGenerationService


class Command(BaseCommand):
    help = 'Generate barcodes for jewelry items'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Tenant schema name to generate barcodes for'
        )
        parser.add_argument(
            '--all-tenants',
            action='store_true',
            help='Generate barcodes for all tenants'
        )
        parser.add_argument(
            '--barcode-type',
            type=str,
            choices=[choice[0] for choice in BarcodeType.choices],
            default=BarcodeType.QR_CODE,
            help='Type of barcode to generate'
        )
        parser.add_argument(
            '--missing-only',
            action='store_true',
            help='Only generate barcodes for items without existing barcodes'
        )
        parser.add_argument(
            '--item-ids',
            type=str,
            help='Comma-separated list of jewelry item IDs to generate barcodes for'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually generating barcodes'
        )
    
    def handle(self, *args, **options):
        tenant_name = options.get('tenant')
        all_tenants = options.get('all_tenants')
        barcode_type = options.get('barcode_type')
        missing_only = options.get('missing_only')
        item_ids = options.get('item_ids')
        dry_run = options.get('dry_run')
        
        if not tenant_name and not all_tenants:
            raise CommandError('You must specify either --tenant or --all-tenants')
        
        if tenant_name and all_tenants:
            raise CommandError('You cannot specify both --tenant and --all-tenants')
        
        # Parse item IDs if provided
        target_item_ids = None
        if item_ids:
            try:
                target_item_ids = [int(id.strip()) for id in item_ids.split(',')]
            except ValueError:
                raise CommandError('Invalid item IDs format. Use comma-separated integers.')
        
        # Get tenants to process
        if all_tenants:
            tenants = Tenant.objects.exclude(schema_name='public')
        else:
            try:
                tenants = [Tenant.objects.get(schema_name=tenant_name)]
            except Tenant.DoesNotExist:
                raise CommandError(f'Tenant "{tenant_name}" not found')
        
        total_generated = 0
        
        for tenant in tenants:
            self.stdout.write(f'\nProcessing tenant: {tenant.schema_name}')
            
            with schema_context(tenant.schema_name):
                generated_count = self._process_tenant(
                    barcode_type, missing_only, target_item_ids, dry_run
                )
                total_generated += generated_count
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Generated {generated_count} barcodes for tenant {tenant.schema_name}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nTotal barcodes generated: {total_generated}'
            )
        )
    
    def _process_tenant(self, barcode_type, missing_only, target_item_ids, dry_run):
        """Process barcode generation for a single tenant."""
        # Get jewelry items to process
        queryset = JewelryItem.objects.all()
        
        if target_item_ids:
            queryset = queryset.filter(id__in=target_item_ids)
        
        if missing_only:
            queryset = queryset.filter(barcode__isnull=True) | queryset.filter(barcode='')
        
        items = list(queryset.select_related('category'))
        
        if not items:
            self.stdout.write('No items found to process')
            return 0
        
        if dry_run:
            self.stdout.write(f'Would generate {len(items)} barcodes:')
            for item in items[:10]:  # Show first 10
                self.stdout.write(f'  - {item.name} ({item.sku})')
            if len(items) > 10:
                self.stdout.write(f'  ... and {len(items) - 10} more items')
            return 0
        
        # Generate barcodes
        service = BarcodeGenerationService()
        generated_count = 0
        
        with transaction.atomic():
            for item in items:
                try:
                    barcode_gen = service.generate_barcode_for_item(item, barcode_type)
                    generated_count += 1
                    
                    self.stdout.write(
                        f'Generated {barcode_type} for {item.name} ({item.sku}): {barcode_gen.barcode_data}'
                    )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Error generating barcode for {item.name} ({item.sku}): {e}'
                        )
                    )
        
        return generated_count