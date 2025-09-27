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


# Celery Beat Schedule for automated tasks
app.conf.beat_schedule = {
    # === BACKUP TASKS ===
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
    
    # === GOLD PRICE TASKS ===
    # Update gold prices every 5 minutes during market hours (8 AM - 6 PM)
    'update-gold-prices': {
        'task': 'zargar.core.gold_price_tasks.update_gold_prices',
        'schedule': crontab(minute='*/5', hour='8-18'),
    },
    
    # Validate gold price APIs every hour
    'validate-gold-price-apis': {
        'task': 'zargar.core.gold_price_tasks.validate_gold_price_apis',
        'schedule': crontab(minute=0),
    },
    
    # Clean up gold price cache every hour
    'cleanup-gold-price-cache': {
        'task': 'zargar.core.gold_price_tasks.cleanup_gold_price_cache',
        'schedule': crontab(minute=30),
    },
    
    # Generate daily gold price report at 7:00 PM
    'daily-gold-price-report': {
        'task': 'zargar.core.gold_price_tasks.generate_gold_price_report',
        'schedule': crontab(hour=19, minute=0),
        'args': ('daily',),
    },
    
    # Generate weekly gold price report on Sunday at 8:00 PM
    'weekly-gold-price-report': {
        'task': 'zargar.core.gold_price_tasks.generate_gold_price_report',
        'schedule': crontab(hour=20, minute=0, day_of_week=0),
        'args': ('weekly',),
    },
    
    # === NOTIFICATION TASKS ===
    # Process scheduled notifications every minute
    'process-scheduled-notifications': {
        'task': 'zargar.core.notification_tasks.process_scheduled_notifications',
        'schedule': crontab(minute='*'),
    },
    
    # Process recurring notification schedules every hour
    'process-recurring-schedules': {
        'task': 'zargar.core.notification_tasks.process_recurring_schedules',
        'schedule': crontab(minute=15),
    },
    
    # Send daily payment reminders at 9:00 AM
    'daily-payment-reminders': {
        'task': 'zargar.core.notification_tasks.send_daily_payment_reminders',
        'schedule': crontab(hour=9, minute=0),
    },
    
    # Send birthday greetings at 8:00 AM
    'birthday-greetings': {
        'task': 'zargar.core.notification_tasks.send_birthday_greetings',
        'schedule': crontab(hour=8, minute=0),
    },
    
    # Send appointment reminders at 6:00 PM
    'appointment-reminders': {
        'task': 'zargar.core.notification_tasks.send_appointment_reminders',
        'schedule': crontab(hour=18, minute=0),
    },
    
    # Clean up old notifications weekly on Saturday at 1:00 AM
    'cleanup-old-notifications': {
        'task': 'zargar.core.notification_tasks.cleanup_old_notifications',
        'schedule': crontab(hour=1, minute=0, day_of_week=6),
    },
    
    # Update notification statistics every hour
    'update-notification-statistics': {
        'task': 'zargar.core.notification_tasks.update_notification_statistics',
        'schedule': crontab(minute=45),
    },
}