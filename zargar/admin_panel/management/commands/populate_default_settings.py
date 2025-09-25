"""
Management command to populate default system settings.
"""
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from zargar.admin_panel.models import SystemSetting, NotificationSetting


class Command(BaseCommand):
    help = 'Populate default system settings and notification settings'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing settings',
        )
    
    def handle(self, *args, **options):
        overwrite = options['overwrite']
        
        self.stdout.write(self.style.SUCCESS('Populating default system settings...'))
        
        # Security Settings
        security_settings = [
            {
                'key': 'security.password_min_length',
                'name': 'Minimum Password Length',
                'description': 'Minimum required length for user passwords',
                'value': '8',
                'default_value': '8',
                'setting_type': 'integer',
                'category': 'security',
                'section': 'password_policy',
                'validation_rules': {'min_value': 6, 'max_value': 50},
                'help_text': 'Passwords must be at least this many characters long',
            },
            {
                'key': 'security.password_require_uppercase',
                'name': 'Require Uppercase Letters',
                'description': 'Whether passwords must contain uppercase letters',
                'value': 'true',
                'default_value': 'true',
                'setting_type': 'boolean',
                'category': 'security',
                'section': 'password_policy',
                'help_text': 'Passwords must contain at least one uppercase letter',
            },
            {
                'key': 'security.password_require_lowercase',
                'name': 'Require Lowercase Letters',
                'description': 'Whether passwords must contain lowercase letters',
                'value': 'true',
                'default_value': 'true',
                'setting_type': 'boolean',
                'category': 'security',
                'section': 'password_policy',
                'help_text': 'Passwords must contain at least one lowercase letter',
            },
            {
                'key': 'security.password_require_numbers',
                'name': 'Require Numbers',
                'description': 'Whether passwords must contain numbers',
                'value': 'true',
                'default_value': 'true',
                'setting_type': 'boolean',
                'category': 'security',
                'section': 'password_policy',
                'help_text': 'Passwords must contain at least one number',
            },
            {
                'key': 'security.password_require_special',
                'name': 'Require Special Characters',
                'description': 'Whether passwords must contain special characters',
                'value': 'false',
                'default_value': 'false',
                'setting_type': 'boolean',
                'category': 'security',
                'section': 'password_policy',
                'help_text': 'Passwords must contain at least one special character',
            },
            {
                'key': 'security.session_timeout_minutes',
                'name': 'Session Timeout (Minutes)',
                'description': 'Number of minutes before user sessions expire',
                'value': '480',
                'default_value': '480',
                'setting_type': 'integer',
                'category': 'security',
                'section': 'session_management',
                'validation_rules': {'min_value': 15, 'max_value': 1440},
                'help_text': 'Sessions will expire after this many minutes of inactivity',
            },
            {
                'key': 'security.max_login_attempts',
                'name': 'Maximum Login Attempts',
                'description': 'Maximum failed login attempts before account lockout',
                'value': '5',
                'default_value': '5',
                'setting_type': 'integer',
                'category': 'security',
                'section': 'rate_limiting',
                'validation_rules': {'min_value': 3, 'max_value': 20},
                'help_text': 'Account will be locked after this many failed login attempts',
            },
            {
                'key': 'security.lockout_duration_minutes',
                'name': 'Account Lockout Duration (Minutes)',
                'description': 'Number of minutes to lock account after failed attempts',
                'value': '30',
                'default_value': '30',
                'setting_type': 'integer',
                'category': 'security',
                'section': 'rate_limiting',
                'validation_rules': {'min_value': 5, 'max_value': 1440},
                'help_text': 'Locked accounts will be unlocked after this many minutes',
            },
            {
                'key': 'security.enable_2fa_requirement',
                'name': 'Require Two-Factor Authentication',
                'description': 'Whether 2FA is required for all users',
                'value': 'false',
                'default_value': 'false',
                'setting_type': 'boolean',
                'category': 'security',
                'section': 'authentication',
                'help_text': 'All users must enable 2FA to access the system',
            },
        ]
        
        # General Settings
        general_settings = [
            {
                'key': 'general.site_name',
                'name': 'Site Name',
                'description': 'Name of the application displayed in UI',
                'value': 'ZARGAR Jewelry Management',
                'default_value': 'ZARGAR Jewelry Management',
                'setting_type': 'string',
                'category': 'general',
                'section': 'branding',
                'validation_rules': {'min_length': 1, 'max_length': 100},
                'help_text': 'This name appears in the browser title and headers',
            },
            {
                'key': 'general.default_language',
                'name': 'Default Language',
                'description': 'Default language for the application',
                'value': 'fa',
                'default_value': 'fa',
                'setting_type': 'string',
                'category': 'general',
                'section': 'localization',
                'choices': ['fa', 'en'],
                'help_text': 'Default language for new users and system messages',
            },
            {
                'key': 'general.timezone',
                'name': 'Default Timezone',
                'description': 'Default timezone for the application',
                'value': 'Asia/Tehran',
                'default_value': 'Asia/Tehran',
                'setting_type': 'string',
                'category': 'general',
                'section': 'localization',
                'help_text': 'Default timezone for displaying dates and times',
            },
            {
                'key': 'general.items_per_page',
                'name': 'Items Per Page',
                'description': 'Default number of items to show per page in lists',
                'value': '25',
                'default_value': '25',
                'setting_type': 'integer',
                'category': 'general',
                'section': 'ui',
                'choices': ['10', '25', '50', '100'],
                'validation_rules': {'min_value': 5, 'max_value': 200},
                'help_text': 'Number of items displayed per page in data tables',
            },
        ]
        
        # Notification Settings
        notification_settings = [
            {
                'key': 'notifications.email_enabled',
                'name': 'Enable Email Notifications',
                'description': 'Whether email notifications are enabled',
                'value': 'true',
                'default_value': 'true',
                'setting_type': 'boolean',
                'category': 'notifications',
                'section': 'email',
                'help_text': 'Enable or disable all email notifications',
            },
            {
                'key': 'notifications.smtp_host',
                'name': 'SMTP Host',
                'description': 'SMTP server hostname for sending emails',
                'value': '',
                'default_value': '',
                'setting_type': 'string',
                'category': 'notifications',
                'section': 'email',
                'is_sensitive': True,
                'help_text': 'SMTP server address (e.g., smtp.gmail.com)',
            },
            {
                'key': 'notifications.smtp_port',
                'name': 'SMTP Port',
                'description': 'SMTP server port number',
                'value': '587',
                'default_value': '587',
                'setting_type': 'integer',
                'category': 'notifications',
                'section': 'email',
                'choices': ['25', '465', '587', '2525'],
                'help_text': 'SMTP server port (587 for TLS, 465 for SSL)',
            },
            {
                'key': 'notifications.smtp_username',
                'name': 'SMTP Username',
                'description': 'Username for SMTP authentication',
                'value': '',
                'default_value': '',
                'setting_type': 'string',
                'category': 'notifications',
                'section': 'email',
                'is_sensitive': True,
                'help_text': 'Username for SMTP server authentication',
            },
            {
                'key': 'notifications.smtp_password',
                'name': 'SMTP Password',
                'description': 'Password for SMTP authentication',
                'value': '',
                'default_value': '',
                'setting_type': 'password',
                'category': 'notifications',
                'section': 'email',
                'is_sensitive': True,
                'help_text': 'Password for SMTP server authentication',
            },
            {
                'key': 'notifications.from_email',
                'name': 'From Email Address',
                'description': 'Email address used as sender for notifications',
                'value': 'noreply@zargar.local',
                'default_value': 'noreply@zargar.local',
                'setting_type': 'email',
                'category': 'notifications',
                'section': 'email',
                'help_text': 'Email address that appears as sender',
            },
        ]
        
        # Backup Settings
        backup_settings = [
            {
                'key': 'backup.auto_backup_enabled',
                'name': 'Enable Automatic Backups',
                'description': 'Whether automatic backups are enabled',
                'value': 'true',
                'default_value': 'true',
                'setting_type': 'boolean',
                'category': 'backup',
                'section': 'scheduling',
                'help_text': 'Enable automatic daily backups',
            },
            {
                'key': 'backup.retention_days',
                'name': 'Backup Retention Days',
                'description': 'Number of days to keep backup files',
                'value': '30',
                'default_value': '30',
                'setting_type': 'integer',
                'category': 'backup',
                'section': 'retention',
                'validation_rules': {'min_value': 7, 'max_value': 365},
                'help_text': 'Backup files older than this will be automatically deleted',
            },
            {
                'key': 'backup.max_backup_size_gb',
                'name': 'Maximum Backup Size (GB)',
                'description': 'Maximum size for individual backup files',
                'value': '10',
                'default_value': '10',
                'setting_type': 'integer',
                'category': 'backup',
                'section': 'limits',
                'validation_rules': {'min_value': 1, 'max_value': 100},
                'help_text': 'Backup process will fail if size exceeds this limit',
            },
        ]
        
        # Combine all settings
        all_settings = security_settings + general_settings + notification_settings + backup_settings
        
        created_count = 0
        updated_count = 0
        
        for setting_data in all_settings:
            existing = SystemSetting.objects.filter(key=setting_data['key']).first()
            
            if existing and not overwrite:
                self.stdout.write(f"Skipping existing setting: {setting_data['key']}")
                continue
            
            if existing and overwrite:
                # Update existing setting
                for field, value in setting_data.items():
                    if field != 'key':  # Don't update the key
                        setattr(existing, field, value)
                existing.save()
                updated_count += 1
                self.stdout.write(f"Updated setting: {setting_data['key']}")
            else:
                # Create new setting
                SystemSetting.objects.create(**setting_data)
                created_count += 1
                self.stdout.write(f"Created setting: {setting_data['key']}")
        
        # Create default notification settings
        default_notifications = [
            {
                'name': 'Security Alert Email',
                'event_type': 'security_alert',
                'notification_type': 'email',
                'recipients': ['admin@zargar.local'],
                'priority_threshold': 'high',
                'subject_template': 'Security Alert: {event_type}',
                'message_template': 'A security event has occurred: {description}\\n\\nTime: {timestamp}\\nIP: {ip_address}',
                'is_enabled': True,
            },
            {
                'name': 'Backup Failure Email',
                'event_type': 'backup_failed',
                'notification_type': 'email',
                'recipients': ['admin@zargar.local'],
                'priority_threshold': 'medium',
                'subject_template': 'Backup Failed: {backup_name}',
                'message_template': 'Backup operation failed:\\n\\nBackup: {backup_name}\\nError: {error_message}\\nTime: {timestamp}',
                'is_enabled': True,
            },
            {
                'name': 'System Error Email',
                'event_type': 'system_error',
                'notification_type': 'email',
                'recipients': ['admin@zargar.local'],
                'priority_threshold': 'high',
                'subject_template': 'System Error: {error_type}',
                'message_template': 'A system error has occurred:\\n\\nError: {error_message}\\nLocation: {location}\\nTime: {timestamp}',
                'is_enabled': True,
            },
        ]
        
        notification_created_count = 0
        notification_updated_count = 0
        
        for notification_data in default_notifications:
            existing = NotificationSetting.objects.filter(
                name=notification_data['name'],
                event_type=notification_data['event_type'],
                notification_type=notification_data['notification_type']
            ).first()
            
            if existing and not overwrite:
                self.stdout.write(f"Skipping existing notification: {notification_data['name']}")
                continue
            
            if existing and overwrite:
                # Update existing notification
                for field, value in notification_data.items():
                    setattr(existing, field, value)
                existing.save()
                notification_updated_count += 1
                self.stdout.write(f"Updated notification: {notification_data['name']}")
            else:
                # Create new notification
                NotificationSetting.objects.create(**notification_data)
                notification_created_count += 1
                self.stdout.write(f"Created notification: {notification_data['name']}")
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\\nCompleted! '
                f'Settings: {created_count} created, {updated_count} updated. '
                f'Notifications: {notification_created_count} created, {notification_updated_count} updated.'
            )
        )