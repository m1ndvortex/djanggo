import os
from celery import Celery
from celery.schedules import crontab
from decouple import config

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')

app = Celery('zargar')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery configuration
app.conf.update(
    broker_url=config('CELERY_BROKER_URL', default='redis://redis:6379/0'),
    result_backend=config('CELERY_RESULT_BACKEND', default='redis://redis:6379/0'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Tehran',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


# Celery Beat Schedule for automated backups
app.conf.beat_schedule = {
    # Daily backup at 3:00 AM
    'daily-system-backup': {
        'task': 'zargar.core.backup_tasks.create_daily_backup',
        'schedule': crontab(hour=3, minute=0),
        'args': (None, 'celery_scheduled_daily'),
    },
    
    # Weekly backup on Sunday at 2:00 AM
    'weekly-system-backup': {
        'task': 'zargar.core.backup_tasks.create_weekly_backup',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),
        'args': (None, 'celery_scheduled_weekly'),
    },
    
    # Process scheduled backups every minute
    'process-scheduled-backups': {
        'task': 'zargar.core.backup_tasks.process_scheduled_backups',
        'schedule': crontab(minute='*'),
    },
    
    # Cleanup old backups daily at 4:00 AM
    'cleanup-old-backups': {
        'task': 'zargar.core.backup_tasks.cleanup_old_backups',
        'schedule': crontab(hour=4, minute=0),
    },
    
    # Generate daily backup report at 6:00 AM
    'daily-backup-report': {
        'task': 'zargar.core.backup_tasks.generate_backup_report',
        'schedule': crontab(hour=6, minute=0),
        'args': ('daily',),
    },
    
    # Generate weekly backup report on Monday at 7:00 AM
    'weekly-backup-report': {
        'task': 'zargar.core.backup_tasks.generate_backup_report',
        'schedule': crontab(hour=7, minute=0, day_of_week=1),
        'args': ('weekly',),
    },
}