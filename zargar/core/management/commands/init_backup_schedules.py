"""
Management command to initialize default backup schedules.
Creates standard backup schedules for the ZARGAR platform.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from zargar.system.models import BackupSchedule


class Command(BaseCommand):
    help = 'Initialize default backup schedules for the ZARGAR platform'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of existing schedules',
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating schedules',
        )
    
    def handle(self, *args, **options):
        """Create default backup schedules."""
        force = options['force']
        dry_run = options['dry_run']
        
        # Define default backup schedules
        default_schedules = [
            {
                'name': 'Daily System Backup',
                'description': 'Automated daily backup of the complete system including all tenant data',
                'schedule_type': 'full_system',
                'frequency': 'daily',
                'hour': 3,
                'minute': 0,
                'retention_days': 30,
                'is_active': True,
            },
            {
                'name': 'Weekly System Backup',
                'description': 'Weekly comprehensive backup with extended retention for disaster recovery',
                'schedule_type': 'full_system',
                'frequency': 'weekly',
                'hour': 2,
                'minute': 0,
                'day_of_week': 0,  # Sunday
                'retention_days': 90,
                'is_active': True,
            },
            {
                'name': 'Monthly System Archive',
                'description': 'Monthly archive backup for long-term storage and compliance',
                'schedule_type': 'full_system',
                'frequency': 'monthly',
                'hour': 1,
                'minute': 30,
                'day_of_month': 1,  # First day of month
                'retention_days': 365,
                'is_active': True,
            },
            {
                'name': 'Configuration Backup',
                'description': 'Daily backup of system configuration files',
                'schedule_type': 'configuration',
                'frequency': 'daily',
                'hour': 4,
                'minute': 30,
                'retention_days': 60,
                'is_active': True,
            },
        ]
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        for schedule_data in default_schedules:
            schedule_name = schedule_data['name']
            
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f'Would create/update schedule: {schedule_name}')
                )
                continue
            
            # Check if schedule already exists
            existing_schedule = BackupSchedule.objects.filter(name=schedule_name).first()
            
            if existing_schedule:
                if force:
                    # Update existing schedule
                    for key, value in schedule_data.items():
                        setattr(existing_schedule, key, value)
                    
                    # Calculate next run time
                    existing_schedule.update_next_run()
                    existing_schedule.save()
                    
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'Updated existing schedule: {schedule_name}')
                    )
                else:
                    skipped_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'Skipped existing schedule: {schedule_name} (use --force to update)')
                    )
            else:
                # Create new schedule
                schedule = BackupSchedule.objects.create(**schedule_data)
                schedule.update_next_run()
                
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created new schedule: {schedule_name}')
                )
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'Dry run completed. Would process {len(default_schedules)} schedules.')
            )
        else:
            # Summary
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nBackup schedule initialization completed:\n'
                    f'  Created: {created_count}\n'
                    f'  Updated: {updated_count}\n'
                    f'  Skipped: {skipped_count}\n'
                    f'  Total: {created_count + updated_count + skipped_count}'
                )
            )
            
            # Show next run times
            if created_count > 0 or updated_count > 0:
                self.stdout.write('\nNext scheduled runs:')
                active_schedules = BackupSchedule.objects.filter(is_active=True).order_by('next_run_at')
                
                for schedule in active_schedules:
                    next_run_str = schedule.next_run_at.strftime('%Y-%m-%d %H:%M:%S') if schedule.next_run_at else 'Not calculated'
                    self.stdout.write(f'  {schedule.name}: {next_run_str}')
        
        self.stdout.write(
            self.style.SUCCESS('\nBackup schedules are now ready for automated execution.')
        )