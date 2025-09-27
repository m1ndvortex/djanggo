"""
Django management command to create default subscription plans.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from zargar.tenants.billing_services import SubscriptionManager


class Command(BaseCommand):
    help = 'Create default subscription plans for Iranian jewelry market'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of existing plans',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('Creating default subscription plans...')
        
        try:
            with transaction.atomic():
                created_plans = SubscriptionManager.create_default_plans()
                
                if created_plans:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully created {len(created_plans)} subscription plans:'
                        )
                    )
                    for plan in created_plans:
                        self.stdout.write(f'  - {plan.name_persian} ({plan.plan_type})')
                else:
                    self.stdout.write(
                        self.style.WARNING('All subscription plans already exist')
                    )
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating subscription plans: {str(e)}')
            )
            raise