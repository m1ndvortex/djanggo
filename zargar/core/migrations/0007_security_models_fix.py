# Custom migration to fix security models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('core', '0006_alter_auditlog_action_totpdevice'),
    ]

    operations = [
        # First, drop the existing AuditLog table if it exists
        migrations.RunSQL(
            "DROP TABLE IF EXISTS core_audit_log CASCADE;",
            reverse_sql="-- No reverse operation"
        ),
        
        # Create SecurityEvent model
        migrations.CreateModel(
            name='SecurityEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Timestamp when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Timestamp when the record was last updated', verbose_name='Updated At')),
                ('event_type', models.CharField(choices=[('login_success', 'Successful Login'), ('login_failed', 'Failed Login'), ('login_blocked', 'Login Blocked (Rate Limited)'), ('logout', 'Logout'), ('password_change', 'Password Change'), ('password_reset_request', 'Password Reset Request'), ('password_reset_complete', 'Password Reset Complete'), ('2fa_enabled', '2FA Enabled'), ('2fa_disabled', '2FA Disabled'), ('2fa_success', '2FA Verification Success'), ('2fa_failed', '2FA Verification Failed'), ('2fa_backup_used', '2FA Backup Token Used'), ('account_locked', 'Account Locked'), ('account_unlocked', 'Account Unlocked'), ('suspicious_activity', 'Suspicious Activity Detected'), ('brute_force_attempt', 'Brute Force Attack Attempt'), ('unauthorized_access', 'Unauthorized Access Attempt'), ('privilege_escalation', 'Privilege Escalation Attempt'), ('data_export', 'Data Export'), ('bulk_operation', 'Bulk Operation'), ('admin_impersonation', 'Admin Impersonation'), ('api_rate_limit', 'API Rate Limit Exceeded'), ('csrf_failure', 'CSRF Token Failure'), ('session_hijack', 'Potential Session Hijacking')], max_length=50, verbose_name='Event Type')),
                ('severity', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], default='medium', max_length=20, verbose_name='Severity Level')),
                ('username_attempted', models.CharField(blank=True, help_text='Username used in failed login attempts', max_length=150, verbose_name='Username Attempted')),
                ('ip_address', models.GenericIPAddressField(verbose_name='IP Address')),
                ('user_agent', models.TextField(blank=True, verbose_name='User Agent')),
                ('session_key', models.CharField(blank=True, max_length=40, verbose_name='Session Key')),
                ('request_path', models.CharField(blank=True, max_length=500, verbose_name='Request Path')),
                ('request_method', models.CharField(blank=True, max_length=10, verbose_name='Request Method')),
                ('details', models.JSONField(blank=True, default=dict, help_text='Additional details about the security event', verbose_name='Event Details')),
                ('is_resolved', models.BooleanField(default=False, help_text='Whether this security event has been investigated and resolved', verbose_name='Is Resolved')),
                ('resolved_at', models.DateTimeField(blank=True, null=True, verbose_name='Resolved At')),
                ('resolution_notes', models.TextField(blank=True, verbose_name='Resolution Notes')),
                ('created_by', models.ForeignKey(blank=True, help_text='User who created this record', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('resolved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resolved_security_events', to=settings.AUTH_USER_MODEL, verbose_name='Resolved By')),
                ('updated_by', models.ForeignKey(blank=True, help_text='User who last updated this record', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Updated By')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='security_events', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Security Event',
                'verbose_name_plural': 'Security Events',
                'db_table': 'core_security_event',
                'ordering': ['-created_at'],
            },
        ),
        
        # Create RateLimitAttempt model
        migrations.CreateModel(
            name='RateLimitAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identifier', models.CharField(help_text='IP address, user ID, or other identifier', max_length=200, verbose_name='Identifier')),
                ('limit_type', models.CharField(choices=[('login', 'Login Attempts'), ('api_call', 'API Call'), ('password_reset', 'Password Reset'), ('2fa_verify', '2FA Verification'), ('data_export', 'Data Export'), ('bulk_operation', 'Bulk Operation'), ('search', 'Search Query'), ('report_generation', 'Report Generation')], max_length=50, verbose_name='Limit Type')),
                ('endpoint', models.CharField(blank=True, help_text='API endpoint or view name', max_length=200, verbose_name='Endpoint')),
                ('attempts', models.PositiveIntegerField(default=1, verbose_name='Attempts')),
                ('window_start', models.DateTimeField(auto_now_add=True, verbose_name='Window Start')),
                ('last_attempt', models.DateTimeField(auto_now=True, verbose_name='Last Attempt')),
                ('is_blocked', models.BooleanField(default=False, verbose_name='Is Blocked')),
                ('blocked_until', models.DateTimeField(blank=True, null=True, verbose_name='Blocked Until')),
                ('user_agent', models.TextField(blank=True, verbose_name='User Agent')),
                ('details', models.JSONField(blank=True, default=dict, verbose_name='Details')),
            ],
            options={
                'verbose_name': 'Rate Limit Attempt',
                'verbose_name_plural': 'Rate Limit Attempts',
                'db_table': 'core_rate_limit_attempt',
            },
        ),
        
        # Create SuspiciousActivity model
        migrations.CreateModel(
            name='SuspiciousActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Timestamp when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Timestamp when the record was last updated', verbose_name='Updated At')),
                ('activity_type', models.CharField(choices=[('multiple_failed_logins', 'Multiple Failed Logins'), ('unusual_access_pattern', 'Unusual Access Pattern'), ('privilege_escalation', 'Privilege Escalation Attempt'), ('data_scraping', 'Data Scraping'), ('session_anomaly', 'Session Anomaly'), ('geographic_anomaly', 'Geographic Anomaly'), ('time_anomaly', 'Time-based Anomaly'), ('bulk_data_access', 'Bulk Data Access'), ('unauthorized_api_usage', 'Unauthorized API Usage'), ('suspicious_user_agent', 'Suspicious User Agent')], max_length=50, verbose_name='Activity Type')),
                ('risk_level', models.CharField(choices=[('low', 'Low Risk'), ('medium', 'Medium Risk'), ('high', 'High Risk'), ('critical', 'Critical Risk')], default='medium', max_length=20, verbose_name='Risk Level')),
                ('ip_address', models.GenericIPAddressField(verbose_name='IP Address')),
                ('user_agent', models.TextField(blank=True, verbose_name='User Agent')),
                ('session_key', models.CharField(blank=True, max_length=40, verbose_name='Session Key')),
                ('pattern_data', models.JSONField(default=dict, help_text='Data used for pattern detection and analysis', verbose_name='Pattern Data')),
                ('confidence_score', models.FloatField(default=0.0, help_text='Confidence score (0.0 to 1.0) for this suspicious activity detection', verbose_name='Confidence Score')),
                ('is_investigated', models.BooleanField(default=False, verbose_name='Is Investigated')),
                ('investigated_at', models.DateTimeField(blank=True, null=True, verbose_name='Investigated At')),
                ('investigation_notes', models.TextField(blank=True, verbose_name='Investigation Notes')),
                ('is_false_positive', models.BooleanField(default=False, verbose_name='Is False Positive')),
                ('created_by', models.ForeignKey(blank=True, help_text='User who created this record', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('investigated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='investigated_activities', to=settings.AUTH_USER_MODEL, verbose_name='Investigated By')),
                ('updated_by', models.ForeignKey(blank=True, help_text='User who last updated this record', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Updated By')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='suspicious_activities', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Suspicious Activity',
                'verbose_name_plural': 'Suspicious Activities',
                'db_table': 'core_suspicious_activity',
                'ordering': ['-created_at'],
            },
        ),
        
        # Recreate AuditLog model from scratch
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Timestamp when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Timestamp when the record was last updated', verbose_name='Updated At')),
                ('action', models.CharField(choices=[('create', 'Create'), ('read', 'Read'), ('update', 'Update'), ('delete', 'Delete'), ('bulk_create', 'Bulk Create'), ('bulk_update', 'Bulk Update'), ('bulk_delete', 'Bulk Delete'), ('login', 'Login'), ('logout', 'Logout'), ('password_change', 'Password Change'), ('password_reset', 'Password Reset'), ('2fa_setup', '2FA Setup'), ('2fa_enable', '2FA Enable'), ('2fa_disable', '2FA Disable'), ('2fa_verify', '2FA Verify'), ('backup_token_generate', 'Backup Token Generate'), ('backup_token_use', 'Backup Token Use'), ('tenant_create', 'Tenant Create'), ('tenant_update', 'Tenant Update'), ('tenant_suspend', 'Tenant Suspend'), ('tenant_activate', 'Tenant Activate'), ('user_impersonate', 'User Impersonate'), ('impersonation_end', 'Impersonation End'), ('sale_create', 'Sale Create'), ('payment_process', 'Payment Process'), ('inventory_update', 'Inventory Update'), ('report_generate', 'Report Generate'), ('data_export', 'Data Export'), ('data_import', 'Data Import'), ('backup_create', 'Backup Create'), ('backup_restore', 'Backup Restore'), ('system_maintenance', 'System Maintenance'), ('configuration_change', 'Configuration Change')], max_length=50, verbose_name='Action')),
                ('content_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='contenttypes.contenttype', verbose_name='Content Type')),
                ('object_id', models.CharField(blank=True, max_length=100, verbose_name='Object ID')),
                ('model_name', models.CharField(blank=True, max_length=100, verbose_name='Model Name')),
                ('object_repr', models.CharField(blank=True, max_length=200, verbose_name='Object Representation')),
                ('changes', models.JSONField(blank=True, default=dict, help_text='JSON representation of field changes', verbose_name='Changes')),
                ('old_values', models.JSONField(blank=True, default=dict, help_text='Previous values before change', verbose_name='Old Values')),
                ('new_values', models.JSONField(blank=True, default=dict, help_text='New values after change', verbose_name='New Values')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP Address')),
                ('user_agent', models.TextField(blank=True, verbose_name='User Agent')),
                ('session_key', models.CharField(blank=True, max_length=40, verbose_name='Session Key')),
                ('request_path', models.CharField(blank=True, max_length=500, verbose_name='Request Path')),
                ('request_method', models.CharField(blank=True, max_length=10, verbose_name='Request Method')),
                ('details', models.JSONField(blank=True, default=dict, verbose_name='Additional Details')),
                ('tenant_schema', models.CharField(blank=True, max_length=100, verbose_name='Tenant Schema')),
                ('checksum', models.CharField(blank=True, help_text='SHA-256 checksum for tamper detection', max_length=64, verbose_name='Integrity Checksum')),
                ('created_by', models.ForeignKey(blank=True, help_text='User who created this record', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('updated_by', models.ForeignKey(blank=True, help_text='User who last updated this record', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Updated By')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Audit Log',
                'verbose_name_plural': 'Audit Logs',
                'db_table': 'core_audit_log',
                'ordering': ['-created_at'],
            },
        ),
        
        # Add relationships
        migrations.AddField(
            model_name='suspiciousactivity',
            name='related_events',
            field=models.ManyToManyField(blank=True, related_name='suspicious_activities', to='core.securityevent', verbose_name='Related Security Events'),
        ),
        
        # Add unique constraints
        migrations.AlterUniqueTogether(
            name='ratelimitattempt',
            unique_together={('identifier', 'limit_type', 'endpoint')},
        ),
        
        # Add indexes
        migrations.AddIndex(
            model_name='securityevent',
            index=models.Index(fields=['event_type', 'created_at'], name='core_securi_event_t_b8e7b8_idx'),
        ),
        migrations.AddIndex(
            model_name='securityevent',
            index=models.Index(fields=['ip_address', 'created_at'], name='core_securi_ip_addr_e8b7c5_idx'),
        ),
        migrations.AddIndex(
            model_name='securityevent',
            index=models.Index(fields=['user', 'event_type'], name='core_securi_user_id_b8e7b8_idx'),
        ),
        migrations.AddIndex(
            model_name='securityevent',
            index=models.Index(fields=['severity', 'is_resolved'], name='core_securi_severit_b8e7b8_idx'),
        ),
        migrations.AddIndex(
            model_name='ratelimitattempt',
            index=models.Index(fields=['identifier', 'limit_type'], name='core_rate_l_identif_b8e7b8_idx'),
        ),
        migrations.AddIndex(
            model_name='ratelimitattempt',
            index=models.Index(fields=['window_start', 'last_attempt'], name='core_rate_l_window__b8e7b8_idx'),
        ),
        migrations.AddIndex(
            model_name='ratelimitattempt',
            index=models.Index(fields=['is_blocked', 'blocked_until'], name='core_rate_l_is_bloc_b8e7b8_idx'),
        ),
        migrations.AddIndex(
            model_name='suspiciousactivity',
            index=models.Index(fields=['activity_type', 'risk_level'], name='core_suspic_activit_b8e7b8_idx'),
        ),
        migrations.AddIndex(
            model_name='suspiciousactivity',
            index=models.Index(fields=['user', 'created_at'], name='core_suspic_user_id_b8e7b8_idx'),
        ),
        migrations.AddIndex(
            model_name='suspiciousactivity',
            index=models.Index(fields=['ip_address', 'created_at'], name='core_suspic_ip_addr_b8e7b8_idx'),
        ),
        migrations.AddIndex(
            model_name='suspiciousactivity',
            index=models.Index(fields=['is_investigated', 'risk_level'], name='core_suspic_is_inve_b8e7b8_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['user', 'action', 'created_at'], name='core_audit__user_id_b8e7b8_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['content_type', 'object_id'], name='core_audit__content_b8e7b8_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['action', 'created_at'], name='core_audit__action_b8e7b8_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['ip_address', 'created_at'], name='core_audit__ip_addr_b8e7b8_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['tenant_schema', 'created_at'], name='core_audit__tenant__b8e7b8_idx'),
        ),
    ]