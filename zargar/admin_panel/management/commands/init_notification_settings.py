"""
Management command to initialize notification system settings.
"""
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from zargar.admin_panel.models import SystemSetting


class Command(BaseCommand):
    help = 'Initialize notification system settings'
    
    def handle(self, *args, **options):
        """Initialize notification system settings."""
        
        # Email server configuration settings
        email_settings = [
            {
                'key': 'email_host',
                'name': _('Email Server Host'),
                'description': _('SMTP server hostname for sending emails'),
                'value': 'localhost',
                'default_value': 'localhost',
                'setting_type': 'string',
                'category': 'notifications',
                'section': 'email_server',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'email_port',
                'name': _('Email Server Port'),
                'description': _('SMTP server port number'),
                'value': '587',
                'default_value': '587',
                'setting_type': 'integer',
                'category': 'notifications',
                'section': 'email_server',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'email_username',
                'name': _('Email Username'),
                'description': _('Username for SMTP authentication'),
                'value': '',
                'default_value': '',
                'setting_type': 'string',
                'category': 'notifications',
                'section': 'email_server',
                'is_sensitive': True,
                'requires_restart': False,
            },
            {
                'key': 'email_password',
                'name': _('Email Password'),
                'description': _('Password for SMTP authentication'),
                'value': '',
                'default_value': '',
                'setting_type': 'password',
                'category': 'notifications',
                'section': 'email_server',
                'is_sensitive': True,
                'requires_restart': False,
            },
            {
                'key': 'email_use_tls',
                'name': _('Use TLS'),
                'description': _('Enable TLS encryption for email'),
                'value': 'true',
                'default_value': 'true',
                'setting_type': 'boolean',
                'category': 'notifications',
                'section': 'email_server',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'email_use_ssl',
                'name': _('Use SSL'),
                'description': _('Enable SSL encryption for email'),
                'value': 'false',
                'default_value': 'false',
                'setting_type': 'boolean',
                'category': 'notifications',
                'section': 'email_server',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'email_from_address',
                'name': _('From Email Address'),
                'description': _('Default sender email address'),
                'value': 'noreply@zargar.local',
                'default_value': 'noreply@zargar.local',
                'setting_type': 'email',
                'category': 'notifications',
                'section': 'email_server',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'email_timeout',
                'name': _('Email Timeout'),
                'description': _('SMTP connection timeout in seconds'),
                'value': '30',
                'default_value': '30',
                'setting_type': 'integer',
                'category': 'notifications',
                'section': 'email_server',
                'is_sensitive': False,
                'requires_restart': False,
            },
        ]
        
        # Alert threshold settings
        alert_settings = [
            # Security event thresholds
            {
                'key': 'alert_failed_login_threshold',
                'name': _('Failed Login Alert Threshold'),
                'description': _('Number of failed logins to trigger alert'),
                'value': '5',
                'default_value': '5',
                'setting_type': 'integer',
                'category': 'notifications',
                'section': 'security_alerts',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'alert_failed_login_window',
                'name': _('Failed Login Window (Minutes)'),
                'description': _('Time window for counting failed logins'),
                'value': '15',
                'default_value': '15',
                'setting_type': 'integer',
                'category': 'notifications',
                'section': 'security_alerts',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'alert_suspicious_activity_threshold',
                'name': _('Suspicious Activity Alert Threshold'),
                'description': _('Number of suspicious activities to trigger alert'),
                'value': '3',
                'default_value': '3',
                'setting_type': 'integer',
                'category': 'notifications',
                'section': 'security_alerts',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'alert_rate_limit_threshold',
                'name': _('Rate Limit Alert Threshold'),
                'description': _('Number of rate limit violations to trigger alert'),
                'value': '10',
                'default_value': '10',
                'setting_type': 'integer',
                'category': 'notifications',
                'section': 'security_alerts',
                'is_sensitive': False,
                'requires_restart': False,
            },
            
            # System health thresholds
            {
                'key': 'alert_cpu_threshold',
                'name': _('CPU Usage Alert Threshold (%)'),
                'description': _('CPU usage percentage to trigger alert'),
                'value': '80',
                'default_value': '80',
                'setting_type': 'integer',
                'category': 'notifications',
                'section': 'system_health',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'alert_cpu_usage_threshold',
                'name': _('CPU Usage Alert Threshold (%)'),
                'description': _('CPU usage percentage to trigger alert'),
                'value': '80',
                'default_value': '80',
                'setting_type': 'integer',
                'category': 'notifications',
                'section': 'system_health',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'alert_memory_threshold',
                'name': _('Memory Usage Alert Threshold (%)'),
                'description': _('Memory usage percentage to trigger alert'),
                'value': '85',
                'default_value': '85',
                'setting_type': 'integer',
                'category': 'notifications',
                'section': 'system_health',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'alert_memory_usage_threshold',
                'name': _('Memory Usage Alert Threshold (%)'),
                'description': _('Memory usage percentage to trigger alert'),
                'value': '85',
                'default_value': '85',
                'setting_type': 'integer',
                'category': 'notifications',
                'section': 'system_health',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'alert_disk_threshold',
                'name': _('Disk Usage Alert Threshold (%)'),
                'description': _('Disk usage percentage to trigger alert'),
                'value': '90',
                'default_value': '90',
                'setting_type': 'integer',
                'category': 'notifications',
                'section': 'system_health',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'alert_disk_usage_threshold',
                'name': _('Disk Usage Alert Threshold (%)'),
                'description': _('Disk usage percentage to trigger alert'),
                'value': '90',
                'default_value': '90',
                'setting_type': 'integer',
                'category': 'notifications',
                'section': 'system_health',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'alert_response_time_threshold',
                'name': _('Response Time Alert Threshold (ms)'),
                'description': _('Response time in milliseconds to trigger alert'),
                'value': '5000',
                'default_value': '5000',
                'setting_type': 'integer',
                'category': 'notifications',
                'section': 'system_health',
                'is_sensitive': False,
                'requires_restart': False,
            },
            
            # Backup system thresholds
            {
                'key': 'alert_backup_failure_threshold',
                'name': _('Backup Failure Alert Threshold'),
                'description': _('Number of backup failures to trigger alert'),
                'value': '1',
                'default_value': '1',
                'setting_type': 'integer',
                'category': 'notifications',
                'section': 'backup_alerts',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'alert_backup_delay_threshold',
                'name': _('Backup Delay Alert Threshold (Hours)'),
                'description': _('Hours of backup delay to trigger alert'),
                'value': '25',
                'default_value': '25',
                'setting_type': 'integer',
                'category': 'notifications',
                'section': 'backup_alerts',
                'is_sensitive': False,
                'requires_restart': False,
            },
            
            # Tenant management thresholds
            {
                'key': 'alert_tenant_creation_threshold',
                'name': _('Tenant Creation Rate Alert Threshold'),
                'description': _('Number of tenant creations per hour to trigger alert'),
                'value': '10',
                'default_value': '10',
                'setting_type': 'integer',
                'category': 'notifications',
                'section': 'tenant_alerts',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'alert_tenant_suspension_threshold',
                'name': _('Tenant Suspension Alert Threshold'),
                'description': _('Number of tenant suspensions per day to trigger alert'),
                'value': '5',
                'default_value': '5',
                'setting_type': 'integer',
                'category': 'notifications',
                'section': 'tenant_alerts',
                'is_sensitive': False,
                'requires_restart': False,
            },
        ]
        
        # Notification recipient settings
        recipient_settings = [
            {
                'key': 'recipients_security_alerts',
                'name': _('Security Alert Recipients'),
                'description': _('Email addresses to receive security alerts'),
                'value': '[]',
                'default_value': '[]',
                'setting_type': 'json',
                'category': 'notifications',
                'section': 'recipients',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'recipients_system_health',
                'name': _('System Health Alert Recipients'),
                'description': _('Email addresses to receive system health alerts'),
                'value': '[]',
                'default_value': '[]',
                'setting_type': 'json',
                'category': 'notifications',
                'section': 'recipients',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'recipients_backup_alerts',
                'name': _('Backup Alert Recipients'),
                'description': _('Email addresses to receive backup alerts'),
                'value': '[]',
                'default_value': '[]',
                'setting_type': 'json',
                'category': 'notifications',
                'section': 'recipients',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'recipients_tenant_alerts',
                'name': _('Tenant Alert Recipients'),
                'description': _('Email addresses to receive tenant alerts'),
                'value': '[]',
                'default_value': '[]',
                'setting_type': 'json',
                'category': 'notifications',
                'section': 'recipients',
                'is_sensitive': False,
                'requires_restart': False,
            },
            {
                'key': 'recipients_critical_alerts',
                'name': _('Critical Alert Recipients'),
                'description': _('Email addresses to receive critical alerts'),
                'value': '[]',
                'default_value': '[]',
                'setting_type': 'json',
                'category': 'notifications',
                'section': 'recipients',
                'is_sensitive': False,
                'requires_restart': False,
            },
        ]
        
        # Combine all settings
        all_settings = email_settings + alert_settings + recipient_settings
        
        created_count = 0
        updated_count = 0
        
        for setting_data in all_settings:
            setting, created = SystemSetting.objects.get_or_create(
                key=setting_data['key'],
                defaults=setting_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Created setting: {setting_data['key']}")
                )
            else:
                # Update existing setting if needed
                updated = False
                for field, value in setting_data.items():
                    if field != 'key' and getattr(setting, field) != value:
                        setattr(setting, field, value)
                        updated = True
                
                if updated:
                    setting.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f"Updated setting: {setting_data['key']}")
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Notification settings initialization complete. "
                f"Created: {created_count}, Updated: {updated_count}"
            )
        )