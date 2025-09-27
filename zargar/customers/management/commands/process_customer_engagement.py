"""
Management command to process customer engagement events.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import get_tenant_model, tenant_context
from zargar.customers.engagement_services import CustomerEngagementService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process customer engagement events (birthdays, anniversaries, cultural events)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=7,
            help='Number of days ahead to create reminders (default: 7)'
        )
        parser.add_argument(
            '--tenant-id',
            type=int,
            help='Process only specific tenant (optional)'
        )
        parser.add_argument(
            '--event-type',
            choices=['birthday', 'anniversary', 'nowruz', 'yalda', 'mehregan', 'all'],
            default='all',
            help='Type of events to process (default: all)'
        )
        parser.add_argument(
            '--send-pending',
            action='store_true',
            help='Send pending events that are due'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it'
        )
    
    def handle(self, *args, **options):
        days_ahead = options['days_ahead']
        tenant_id = options.get('tenant_id')
        event_type = options['event_type']
        send_pending = options['send_pending']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Get tenants to process
        Tenant = get_tenant_model()
        if tenant_id:
            tenants = Tenant.objects.filter(id=tenant_id, is_active=True)
        else:
            tenants = Tenant.objects.filter(is_active=True)
        
        total_created = 0
        total_sent = 0
        total_failed = 0
        
        for tenant in tenants:
            with tenant_context(tenant):
                self.stdout.write(f"Processing tenant: {tenant.name}")
                
                engagement_service = CustomerEngagementService(tenant)
                created_events = []
                
                # Create new events based on type
                if event_type in ['birthday', 'all']:
                    if not dry_run:
                        birthday_events = engagement_service.create_birthday_reminders(days_ahead)
                        created_events.extend(birthday_events)
                    else:
                        self.stdout.write(f"  Would create birthday reminders for {days_ahead} days ahead")
                
                if event_type in ['anniversary', 'all']:
                    if not dry_run:
                        anniversary_events = engagement_service.create_anniversary_reminders(days_ahead)
                        created_events.extend(anniversary_events)
                    else:
                        self.stdout.write(f"  Would create anniversary reminders for {days_ahead} days ahead")
                
                if event_type in ['nowruz', 'yalda', 'mehregan']:
                    if not dry_run:
                        cultural_events = engagement_service.create_cultural_event_reminders(event_type)
                        created_events.extend(cultural_events)
                    else:
                        self.stdout.write(f"  Would create {event_type} reminders")
                
                if event_type == 'all':
                    # Create cultural events for current season
                    current_month = timezone.now().month
                    if current_month in [3, 4]:  # Spring - Nowruz season
                        if not dry_run:
                            nowruz_events = engagement_service.create_cultural_event_reminders('nowruz')
                            created_events.extend(nowruz_events)
                        else:
                            self.stdout.write("  Would create Nowruz reminders")
                    elif current_month in [10, 11]:  # Autumn - Mehregan season
                        if not dry_run:
                            mehregan_events = engagement_service.create_cultural_event_reminders('mehregan')
                            created_events.extend(mehregan_events)
                        else:
                            self.stdout.write("  Would create Mehregan reminders")
                    elif current_month == 12:  # Winter - Yalda season
                        if not dry_run:
                            yalda_events = engagement_service.create_cultural_event_reminders('yalda')
                            created_events.extend(yalda_events)
                        else:
                            self.stdout.write("  Would create Yalda reminders")
                
                if not dry_run:
                    total_created += len(created_events)
                    self.stdout.write(
                        self.style.SUCCESS(f"  Created {len(created_events)} engagement events")
                    )
                
                # Send pending events if requested
                if send_pending and not dry_run:
                    results = engagement_service.send_pending_events()
                    total_sent += results['sent']
                    total_failed += results['failed']
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  Sent {results['sent']} events, "
                            f"Failed {results['failed']} events, "
                            f"Skipped {results['skipped']} events"
                        )
                    )
                elif send_pending and dry_run:
                    self.stdout.write("  Would send pending events")
        
        # Summary
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSummary:\n"
                    f"  Total events created: {total_created}\n"
                    f"  Total events sent: {total_sent}\n"
                    f"  Total events failed: {total_failed}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"\nDRY RUN completed. Use --no-dry-run to execute changes."
                )
            )