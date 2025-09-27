"""
Management command to set up periodic health monitoring tasks.
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json


class Command(BaseCommand):
    help = 'Set up periodic health monitoring tasks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--remove',
            action='store_true',
            help='Remove existing health monitoring tasks',
        )
    
    def handle(self, *args, **options):
        if options['remove']:
            self.remove_health_tasks()
        else:
            self.setup_health_tasks()
    
    def setup_health_tasks(self):
        """Set up all health monitoring periodic tasks."""
        self.stdout.write('Setting up health monitoring tasks...')
        
        # 1. Metrics collection every 2 minutes
        metrics_schedule, created = IntervalSchedule.objects.get_or_create(
            every=2,
            period=IntervalSchedule.MINUTES,
        )
        
        metrics_task, created = PeriodicTask.objects.get_or_create(
            name='Collect System Health Metrics',
            defaults={
                'task': 'zargar.admin_panel.tasks.collect_system_health_metrics',
                'interval': metrics_schedule,
                'enabled': True,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('✓ Created metrics collection task (every 2 minutes)')
            )
        else:
            self.stdout.write('• Metrics collection task already exists')
        
        # 2. Alert checking every 5 minutes
        alert_schedule, created = IntervalSchedule.objects.get_or_create(
            every=5,
            period=IntervalSchedule.MINUTES,
        )
        
        alert_task, created = PeriodicTask.objects.get_or_create(
            name='Check System Health Alerts',
            defaults={
                'task': 'zargar.admin_panel.tasks.check_system_health_alerts',
                'interval': alert_schedule,
                'enabled': True,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('✓ Created alert checking task (every 5 minutes)')
            )
        else:
            self.stdout.write('• Alert checking task already exists')
        
        # 3. Alert notifications every 15 minutes
        notification_schedule, created = IntervalSchedule.objects.get_or_create(
            every=15,
            period=IntervalSchedule.MINUTES,
        )
        
        notification_task, created = PeriodicTask.objects.get_or_create(
            name='Send Health Alert Notifications',
            defaults={
                'task': 'zargar.admin_panel.tasks.send_health_alert_notifications',
                'interval': notification_schedule,
                'enabled': True,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('✓ Created notification task (every 15 minutes)')
            )
        else:
            self.stdout.write('• Notification task already exists')
        
        # 4. Cleanup old metrics daily at 2 AM
        cleanup_schedule, created = CrontabSchedule.objects.get_or_create(
            minute=0,
            hour=2,
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        cleanup_task, created = PeriodicTask.objects.get_or_create(
            name='Cleanup Old Health Metrics',
            defaults={
                'task': 'zargar.admin_panel.tasks.cleanup_old_health_metrics',
                'crontab': cleanup_schedule,
                'enabled': True,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('✓ Created cleanup task (daily at 2 AM)')
            )
        else:
            self.stdout.write('• Cleanup task already exists')
        
        # 5. Daily health report at 6 AM
        daily_report_schedule, created = CrontabSchedule.objects.get_or_create(
            minute=0,
            hour=6,
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        daily_report_task, created = PeriodicTask.objects.get_or_create(
            name='Generate Daily Health Report',
            defaults={
                'task': 'zargar.admin_panel.tasks.generate_health_report',
                'crontab': daily_report_schedule,
                'args': json.dumps(['daily']),
                'enabled': True,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('✓ Created daily report task (daily at 6 AM)')
            )
        else:
            self.stdout.write('• Daily report task already exists')
        
        # 6. Weekly health report on Mondays at 7 AM
        weekly_report_schedule, created = CrontabSchedule.objects.get_or_create(
            minute=0,
            hour=7,
            day_of_week=1,  # Monday
            day_of_month='*',
            month_of_year='*',
        )
        
        weekly_report_task, created = PeriodicTask.objects.get_or_create(
            name='Generate Weekly Health Report',
            defaults={
                'task': 'zargar.admin_panel.tasks.generate_health_report',
                'crontab': weekly_report_schedule,
                'args': json.dumps(['weekly']),
                'enabled': True,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('✓ Created weekly report task (Mondays at 7 AM)')
            )
        else:
            self.stdout.write('• Weekly report task already exists')
        
        self.stdout.write(
            self.style.SUCCESS('\n✅ Health monitoring tasks setup complete!')
        )
        self.stdout.write(
            'Make sure Celery Beat is running to execute these periodic tasks.'
        )
    
    def remove_health_tasks(self):
        """Remove all health monitoring periodic tasks."""
        self.stdout.write('Removing health monitoring tasks...')
        
        task_names = [
            'Collect System Health Metrics',
            'Check System Health Alerts',
            'Send Health Alert Notifications',
            'Cleanup Old Health Metrics',
            'Generate Daily Health Report',
            'Generate Weekly Health Report',
        ]
        
        removed_count = 0
        for task_name in task_names:
            try:
                task = PeriodicTask.objects.get(name=task_name)
                task.delete()
                removed_count += 1
                self.stdout.write(f'✓ Removed: {task_name}')
            except PeriodicTask.DoesNotExist:
                self.stdout.write(f'• Not found: {task_name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Removed {removed_count} health monitoring tasks')
        )