"""
Management command for security monitoring and maintenance tasks.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import json

from zargar.core.security_models import SecurityEvent, AuditLog, RateLimitAttempt, SuspiciousActivity
from zargar.core.security_utils import SecurityMonitor
from django.db import models

User = get_user_model()


class Command(BaseCommand):
    help = 'Run security monitoring and maintenance tasks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            type=str,
            choices=['cleanup', 'analyze', 'report', 'all'],
            default='all',
            help='Specific task to run (default: all)'
        )
        
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to look back for analysis (default: 30)'
        )
        
        parser.add_argument(
            '--output',
            type=str,
            choices=['console', 'json', 'file'],
            default='console',
            help='Output format (default: console)'
        )
        
        parser.add_argument(
            '--file',
            type=str,
            help='Output file path (required if output=file)'
        )
    
    def handle(self, *args, **options):
        task = options['task']
        days = options['days']
        output_format = options['output']
        output_file = options['file']
        
        if output_format == 'file' and not output_file:
            self.stderr.write(
                self.style.ERROR('--file is required when output=file')
            )
            return
        
        results = {}
        
        if task in ['cleanup', 'all']:
            results['cleanup'] = self.cleanup_old_records(days)
        
        if task in ['analyze', 'all']:
            results['analysis'] = self.analyze_security_events(days)
        
        if task in ['report', 'all']:
            results['report'] = self.generate_security_report(days)
        
        # Output results
        self.output_results(results, output_format, output_file)
    
    def cleanup_old_records(self, days):
        """Clean up old security records."""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f'Cleaning up records older than {days} days...')
        
        # Clean up resolved security events
        resolved_events = SecurityEvent.objects.filter(
            created_at__lt=cutoff_date,
            is_resolved=True
        )
        resolved_count = resolved_events.count()
        resolved_events.delete()
        
        # Clean up old rate limit attempts
        old_rate_limits = RateLimitAttempt.objects.filter(
            window_start__lt=cutoff_date,
            is_blocked=False
        )
        rate_limit_count = old_rate_limits.count()
        old_rate_limits.delete()
        
        # Clean up investigated suspicious activities
        investigated_activities = SuspiciousActivity.objects.filter(
            created_at__lt=cutoff_date,
            is_investigated=True,
            is_false_positive=True
        )
        activity_count = investigated_activities.count()
        investigated_activities.delete()
        
        # Keep audit logs longer (90 days minimum)
        audit_cutoff = timezone.now() - timedelta(days=max(days * 3, 90))
        old_audit_logs = AuditLog.objects.filter(
            created_at__lt=audit_cutoff
        )
        audit_count = old_audit_logs.count()
        old_audit_logs.delete()
        
        cleanup_results = {
            'resolved_security_events': resolved_count,
            'old_rate_limits': rate_limit_count,
            'investigated_activities': activity_count,
            'old_audit_logs': audit_count,
            'total_cleaned': resolved_count + rate_limit_count + activity_count + audit_count
        }
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Cleanup completed: {cleanup_results["total_cleaned"]} records removed'
            )
        )
        
        return cleanup_results
    
    def analyze_security_events(self, days):
        """Analyze security events for patterns and threats."""
        self.stdout.write(f'Analyzing security events from last {days} days...')
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Get security event statistics
        events = SecurityEvent.objects.filter(created_at__gte=cutoff_date)
        
        event_stats = {}
        for event_type, _ in SecurityEvent.EVENT_TYPES:
            count = events.filter(event_type=event_type).count()
            if count > 0:
                event_stats[event_type] = count
        
        # Get severity distribution
        severity_stats = {}
        for severity, _ in SecurityEvent.SEVERITY_LEVELS:
            count = events.filter(severity=severity).count()
            if count > 0:
                severity_stats[severity] = count
        
        # Get top risk IPs
        risk_ips = events.filter(
            severity__in=['high', 'critical']
        ).values('ip_address').annotate(
            event_count=models.Count('id')
        ).order_by('-event_count')[:10]
        
        # Get unresolved high-risk events
        unresolved_high_risk = events.filter(
            severity__in=['high', 'critical'],
            is_resolved=False
        ).count()
        
        # Analyze suspicious activities
        suspicious_activities = SuspiciousActivity.objects.filter(
            created_at__gte=cutoff_date
        )
        
        activity_stats = {}
        for activity_type, _ in SuspiciousActivity.ACTIVITY_TYPES:
            count = suspicious_activities.filter(activity_type=activity_type).count()
            if count > 0:
                activity_stats[activity_type] = count
        
        unresolved_activities = suspicious_activities.filter(
            is_investigated=False
        ).count()
        
        analysis_results = {
            'period_days': days,
            'total_events': events.count(),
            'event_types': event_stats,
            'severity_distribution': severity_stats,
            'unresolved_high_risk': unresolved_high_risk,
            'top_risk_ips': list(risk_ips),
            'suspicious_activities': {
                'total': suspicious_activities.count(),
                'by_type': activity_stats,
                'unresolved': unresolved_activities
            },
            'recommendations': self.get_analysis_recommendations(
                unresolved_high_risk, unresolved_activities, event_stats
            )
        }
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Analysis completed: {events.count()} events analyzed'
            )
        )
        
        return analysis_results
    
    def generate_security_report(self, days):
        """Generate comprehensive security report."""
        self.stdout.write(f'Generating security report for last {days} days...')
        
        # Get system overview
        system_overview = SecurityMonitor.get_system_security_overview()
        
        # Get high-risk users
        high_risk_users = []
        for user in User.objects.filter(is_active=True)[:50]:  # Limit to 50 users
            security_check = SecurityMonitor.check_account_security(user)
            if security_check['risk_level'] in ['high', 'critical']:
                high_risk_users.append({
                    'user_id': user.id,
                    'username': user.username,
                    'risk_score': security_check['risk_score'],
                    'risk_level': security_check['risk_level'],
                    'failed_logins': security_check['failed_logins_7d'],
                    'suspicious_activities': security_check['suspicious_activities_7d']
                })
        
        # Get rate limiting statistics
        cutoff_date = timezone.now() - timedelta(days=days)
        rate_limit_stats = RateLimitAttempt.objects.filter(
            last_attempt__gte=cutoff_date
        ).values('limit_type').annotate(
            total_attempts=models.Count('id'),
            blocked_count=models.Count('id', filter=models.Q(is_blocked=True))
        ).order_by('-total_attempts')
        
        report_results = {
            'report_date': timezone.now().isoformat(),
            'period_days': days,
            'system_overview': system_overview,
            'high_risk_users': high_risk_users,
            'rate_limiting': list(rate_limit_stats),
            'summary': {
                'total_security_events': system_overview['security_events']['total'],
                'critical_events': system_overview['security_events']['critical_count'],
                'high_risk_users_count': len(high_risk_users),
                'unresolved_suspicious_activities': system_overview['suspicious_activities']['unresolved']
            }
        }
        
        self.stdout.write(
            self.style.SUCCESS('Security report generated successfully')
        )
        
        return report_results
    
    def get_analysis_recommendations(self, unresolved_high_risk, unresolved_activities, event_stats):
        """Generate recommendations based on analysis."""
        recommendations = []
        
        if unresolved_high_risk > 0:
            recommendations.append({
                'priority': 'critical',
                'action': 'investigate_high_risk_events',
                'description': f'{unresolved_high_risk} unresolved high-risk security events need immediate attention'
            })
        
        if unresolved_activities > 10:
            recommendations.append({
                'priority': 'high',
                'action': 'investigate_suspicious_activities',
                'description': f'{unresolved_activities} suspicious activities need investigation'
            })
        
        if event_stats.get('brute_force_attempt', 0) > 5:
            recommendations.append({
                'priority': 'high',
                'action': 'strengthen_authentication',
                'description': 'Multiple brute force attempts detected - consider implementing additional security measures'
            })
        
        if event_stats.get('login_failed', 0) > 50:
            recommendations.append({
                'priority': 'medium',
                'action': 'review_failed_logins',
                'description': 'High number of failed login attempts - review for patterns'
            })
        
        return recommendations
    
    def output_results(self, results, output_format, output_file):
        """Output results in specified format."""
        if output_format == 'json':
            json_output = json.dumps(results, indent=2, default=str)
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(json_output)
                self.stdout.write(f'Results written to {output_file}')
            else:
                self.stdout.write(json_output)
        
        elif output_format == 'file':
            with open(output_file, 'w') as f:
                f.write('ZARGAR Security Monitoring Report\n')
                f.write('=' * 40 + '\n\n')
                
                for section, data in results.items():
                    f.write(f'{section.upper()}\n')
                    f.write('-' * 20 + '\n')
                    f.write(json.dumps(data, indent=2, default=str))
                    f.write('\n\n')
            
            self.stdout.write(f'Results written to {output_file}')
        
        else:  # console output
            self.stdout.write('\nSECURITY MONITORING RESULTS')
            self.stdout.write('=' * 40)
            
            for section, data in results.items():
                self.stdout.write(f'\n{section.upper()}:')
                self.stdout.write('-' * 20)
                
                if section == 'cleanup':
                    self.stdout.write(f"Resolved security events: {data['resolved_security_events']}")
                    self.stdout.write(f"Old rate limits: {data['old_rate_limits']}")
                    self.stdout.write(f"Investigated activities: {data['investigated_activities']}")
                    self.stdout.write(f"Old audit logs: {data['old_audit_logs']}")
                    self.stdout.write(f"Total cleaned: {data['total_cleaned']}")
                
                elif section == 'analysis':
                    self.stdout.write(f"Total events: {data['total_events']}")
                    self.stdout.write(f"Unresolved high-risk: {data['unresolved_high_risk']}")
                    self.stdout.write(f"Unresolved suspicious activities: {data['suspicious_activities']['unresolved']}")
                    
                    if data['recommendations']:
                        self.stdout.write('\nRecommendations:')
                        for rec in data['recommendations']:
                            self.stdout.write(f"  [{rec['priority'].upper()}] {rec['description']}")
                
                elif section == 'report':
                    summary = data['summary']
                    self.stdout.write(f"Total security events: {summary['total_security_events']}")
                    self.stdout.write(f"Critical events: {summary['critical_events']}")
                    self.stdout.write(f"High-risk users: {summary['high_risk_users_count']}")
                    self.stdout.write(f"Unresolved suspicious activities: {summary['unresolved_suspicious_activities']}")
            
            self.stdout.write('\n' + '=' * 40)