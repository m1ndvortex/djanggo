"""
Security utilities and helper functions for zargar project.
"""
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from datetime import timedelta
import hashlib
import hmac
import secrets
import string
import json
from .security_models import SecurityEvent, AuditLog, RateLimitAttempt, SuspiciousActivity

User = get_user_model()


class SecurityMonitor:
    """
    Centralized security monitoring and threat detection system.
    """
    
    @staticmethod
    def check_account_security(user):
        """
        Comprehensive security check for a user account.
        
        Args:
            user (User): User to check
            
        Returns:
            dict: Security assessment results
        """
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        
        # Get recent security events
        recent_events = SecurityEvent.objects.filter(
            user=user,
            created_at__gte=last_24h
        ).values('event_type').annotate(count=Count('id'))
        
        # Get failed login attempts
        failed_logins = SecurityEvent.objects.filter(
            user=user,
            event_type='login_failed',
            created_at__gte=last_7d
        ).count()
        
        # Get suspicious activities
        suspicious_activities = SuspiciousActivity.objects.filter(
            user=user,
            created_at__gte=last_7d,
            is_false_positive=False
        ).count()
        
        # Calculate risk score
        risk_score = SecurityMonitor._calculate_user_risk_score(
            user, recent_events, failed_logins, suspicious_activities
        )
        
        # Check for account anomalies
        anomalies = SecurityMonitor._detect_account_anomalies(user)
        
        return {
            'user_id': user.id,
            'username': user.username,
            'risk_score': risk_score,
            'risk_level': SecurityMonitor._get_risk_level(risk_score),
            'recent_events': list(recent_events),
            'failed_logins_7d': failed_logins,
            'suspicious_activities_7d': suspicious_activities,
            'anomalies': anomalies,
            'recommendations': SecurityMonitor._get_security_recommendations(
                user, risk_score, anomalies
            ),
            'last_login': user.last_login,
            'is_2fa_enabled': getattr(user, 'is_2fa_enabled', False),
            'account_locked': SecurityMonitor._is_account_locked(user),
        }
    
    @staticmethod
    def _calculate_user_risk_score(user, recent_events, failed_logins, suspicious_activities):
        """Calculate risk score for a user (0-100)."""
        score = 0
        
        # Base score from recent events
        event_scores = {
            'login_failed': 5,
            'brute_force_attempt': 20,
            'unauthorized_access': 15,
            'privilege_escalation': 25,
            'suspicious_activity': 10,
            'session_hijack': 20,
        }
        
        for event in recent_events:
            event_score = event_scores.get(event['event_type'], 1)
            score += event_score * event['count']
        
        # Add score for failed logins
        score += min(failed_logins * 2, 20)  # Cap at 20
        
        # Add score for suspicious activities
        score += min(suspicious_activities * 5, 25)  # Cap at 25
        
        # Reduce score for security measures
        if getattr(user, 'is_2fa_enabled', False):
            score = max(0, score - 10)
        
        if user.last_login and user.last_login > timezone.now() - timedelta(days=1):
            score = max(0, score - 5)  # Recent activity is good
        
        return min(score, 100)  # Cap at 100
    
    @staticmethod
    def _get_risk_level(risk_score):
        """Convert risk score to risk level."""
        if risk_score >= 70:
            return 'critical'
        elif risk_score >= 50:
            return 'high'
        elif risk_score >= 30:
            return 'medium'
        else:
            return 'low'
    
    @staticmethod
    def _detect_account_anomalies(user):
        """Detect anomalies in user account behavior."""
        anomalies = []
        now = timezone.now()
        
        # Check for unusual login times
        recent_logins = SecurityEvent.objects.filter(
            user=user,
            event_type='login_success',
            created_at__gte=now - timedelta(days=7)
        ).values_list('created_at', flat=True)
        
        if SecurityMonitor._detect_unusual_login_times(recent_logins):
            anomalies.append({
                'type': 'unusual_login_times',
                'description': 'Login attempts at unusual hours',
                'severity': 'medium'
            })
        
        # Check for multiple IP addresses
        recent_ips = SecurityEvent.objects.filter(
            user=user,
            created_at__gte=now - timedelta(days=7)
        ).values_list('ip_address', flat=True).distinct()
        
        if len(recent_ips) > 5:  # More than 5 different IPs in a week
            anomalies.append({
                'type': 'multiple_ip_addresses',
                'description': f'Access from {len(recent_ips)} different IP addresses',
                'severity': 'medium'
            })
        
        # Check for rapid permission changes
        permission_changes = AuditLog.objects.filter(
            user=user,
            action__in=['update'],
            model_name='user',
            created_at__gte=now - timedelta(days=1)
        ).count()
        
        if permission_changes > 3:
            anomalies.append({
                'type': 'rapid_permission_changes',
                'description': 'Multiple permission changes in short time',
                'severity': 'high'
            })
        
        return anomalies
    
    @staticmethod
    def _detect_unusual_login_times(login_times):
        """Detect if login times are unusual (outside normal business hours)."""
        if not login_times:
            return False
        
        unusual_count = 0
        for login_time in login_times:
            hour = login_time.hour
            # Consider 22:00 - 06:00 as unusual hours
            if hour >= 22 or hour <= 6:
                unusual_count += 1
        
        # If more than 50% of logins are at unusual times
        return unusual_count / len(login_times) > 0.5
    
    @staticmethod
    def _get_security_recommendations(user, risk_score, anomalies):
        """Get security recommendations based on risk assessment."""
        recommendations = []
        
        if risk_score >= 50:
            recommendations.append({
                'priority': 'high',
                'action': 'immediate_review',
                'description': 'Account requires immediate security review'
            })
        
        if not getattr(user, 'is_2fa_enabled', False):
            recommendations.append({
                'priority': 'high',
                'action': 'enable_2fa',
                'description': 'Enable two-factor authentication'
            })
        
        if any(a['type'] == 'multiple_ip_addresses' for a in anomalies):
            recommendations.append({
                'priority': 'medium',
                'action': 'verify_locations',
                'description': 'Verify all login locations are legitimate'
            })
        
        if any(a['type'] == 'unusual_login_times' for a in anomalies):
            recommendations.append({
                'priority': 'medium',
                'action': 'review_login_times',
                'description': 'Review unusual login time patterns'
            })
        
        return recommendations
    
    @staticmethod
    def _is_account_locked(user):
        """Check if account is currently locked due to security issues."""
        # Check for recent blocking events
        recent_blocks = SecurityEvent.objects.filter(
            user=user,
            event_type__in=['login_blocked', 'account_locked'],
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).exists()
        
        return recent_blocks
    
    @staticmethod
    def get_system_security_overview():
        """Get system-wide security overview."""
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        
        # Get security event statistics
        security_events = SecurityEvent.objects.filter(created_at__gte=last_24h)
        
        event_stats = security_events.values('event_type', 'severity').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Get top risk IPs
        risk_ips = SecurityEvent.objects.filter(
            created_at__gte=last_7d,
            severity__in=['high', 'critical']
        ).values('ip_address').annotate(
            event_count=Count('id')
        ).order_by('-event_count')[:10]
        
        # Get suspicious activities
        suspicious_stats = SuspiciousActivity.objects.filter(
            created_at__gte=last_24h
        ).values('activity_type', 'risk_level').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Get rate limit statistics
        rate_limit_stats = RateLimitAttempt.objects.filter(
            last_attempt__gte=last_24h
        ).values('limit_type').annotate(
            total_attempts=Count('id'),
            blocked_count=Count('id', filter=Q(is_blocked=True))
        ).order_by('-total_attempts')
        
        return {
            'timestamp': now.isoformat(),
            'period': '24 hours',
            'security_events': {
                'total': security_events.count(),
                'by_type_severity': list(event_stats),
                'critical_count': security_events.filter(severity='critical').count(),
                'high_count': security_events.filter(severity='high').count(),
            },
            'suspicious_activities': {
                'total': SuspiciousActivity.objects.filter(created_at__gte=last_24h).count(),
                'by_type_risk': list(suspicious_stats),
                'unresolved': SuspiciousActivity.objects.filter(
                    created_at__gte=last_24h,
                    is_investigated=False
                ).count(),
            },
            'rate_limiting': {
                'by_type': list(rate_limit_stats),
                'total_blocked': RateLimitAttempt.objects.filter(
                    last_attempt__gte=last_24h,
                    is_blocked=True
                ).count(),
            },
            'risk_ips': list(risk_ips),
            'recommendations': SecurityMonitor._get_system_recommendations(
                security_events, suspicious_stats, rate_limit_stats
            ),
        }
    
    @staticmethod
    def _get_system_recommendations(security_events, suspicious_stats, rate_limit_stats):
        """Get system-wide security recommendations."""
        recommendations = []
        
        critical_events = security_events.filter(severity='critical').count()
        if critical_events > 0:
            recommendations.append({
                'priority': 'critical',
                'action': 'investigate_critical_events',
                'description': f'{critical_events} critical security events require immediate attention'
            })
        
        high_events = security_events.filter(severity='high').count()
        if high_events > 10:
            recommendations.append({
                'priority': 'high',
                'action': 'review_high_severity_events',
                'description': f'{high_events} high-severity events detected'
            })
        
        unresolved_suspicious = SuspiciousActivity.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24),
            is_investigated=False
        ).count()
        
        if unresolved_suspicious > 5:
            recommendations.append({
                'priority': 'medium',
                'action': 'investigate_suspicious_activities',
                'description': f'{unresolved_suspicious} suspicious activities need investigation'
            })
        
        return recommendations


class SecurityValidator:
    """
    Security validation utilities.
    """
    
    @staticmethod
    def validate_password_strength(password):
        """
        Validate password strength according to security requirements.
        
        Args:
            password (str): Password to validate
            
        Returns:
            dict: Validation results
        """
        issues = []
        score = 0
        
        # Length check
        if len(password) < 8:
            issues.append('Password must be at least 8 characters long')
        else:
            score += 1
        
        if len(password) >= 12:
            score += 1
        
        # Character variety checks
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
        
        if not has_upper:
            issues.append('Password must contain at least one uppercase letter')
        else:
            score += 1
        
        if not has_lower:
            issues.append('Password must contain at least one lowercase letter')
        else:
            score += 1
        
        if not has_digit:
            issues.append('Password must contain at least one digit')
        else:
            score += 1
        
        if not has_special:
            issues.append('Password must contain at least one special character')
        else:
            score += 1
        
        # Common password check
        if SecurityValidator._is_common_password(password):
            issues.append('Password is too common')
            score = max(0, score - 2)
        
        # Calculate strength
        if score >= 6:
            strength = 'strong'
        elif score >= 4:
            strength = 'medium'
        elif score >= 2:
            strength = 'weak'
        else:
            strength = 'very_weak'
        
        return {
            'is_valid': len(issues) == 0,
            'strength': strength,
            'score': score,
            'issues': issues,
        }
    
    @staticmethod
    def _is_common_password(password):
        """Check if password is in common passwords list."""
        common_passwords = {
            'password', '123456', '123456789', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein', 'welcome', 'monkey',
            'dragon', 'master', 'shadow', 'superman', 'michael',
        }
        return password.lower() in common_passwords
    
    @staticmethod
    def generate_secure_token(length=32):
        """Generate a cryptographically secure random token."""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def generate_backup_codes(count=10, length=8):
        """Generate backup codes for 2FA."""
        codes = []
        for _ in range(count):
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))
            codes.append(code)
        return codes
    
    @staticmethod
    def verify_request_signature(request, secret_key):
        """Verify HMAC signature of request."""
        signature = request.META.get('HTTP_X_SIGNATURE', '')
        if not signature:
            return False
        
        # Get request body
        body = request.body
        
        # Calculate expected signature
        expected_signature = hmac.new(
            secret_key.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(signature, expected_signature)


class AuditLogger:
    """
    Centralized audit logging utilities.
    """
    
    @staticmethod
    def log_model_change(instance, action, user=None, request=None, old_values=None, new_values=None):
        """
        Log model changes with comprehensive audit trail.
        
        Args:
            instance: Model instance being changed
            action (str): Action being performed (create, update, delete)
            user (User, optional): User performing the action
            request (HttpRequest, optional): Request object
            old_values (dict, optional): Previous field values
            new_values (dict, optional): New field values
        """
        # Calculate changes
        changes = {}
        if old_values and new_values:
            for field, new_value in new_values.items():
                old_value = old_values.get(field)
                if old_value != new_value:
                    changes[field] = {
                        'old': old_value,
                        'new': new_value
                    }
        
        AuditLog.log_action(
            action=action,
            user=user,
            content_object=instance,
            request=request,
            changes=changes,
            old_values=old_values or {},
            new_values=new_values or {},
            details={
                'model_name': instance._meta.model_name,
                'app_label': instance._meta.app_label,
                'change_count': len(changes),
            }
        )
    
    @staticmethod
    def log_business_operation(operation_type, user, details=None, request=None, **kwargs):
        """
        Log business operations like sales, payments, etc.
        
        Args:
            operation_type (str): Type of business operation
            user (User): User performing the operation
            details (dict, optional): Operation details
            request (HttpRequest, optional): Request object
            **kwargs: Additional audit log fields
        """
        AuditLog.log_action(
            action=operation_type,
            user=user,
            request=request,
            details=details or {},
            **kwargs
        )
    
    @staticmethod
    def log_admin_action(admin_user, action, target_user=None, details=None, request=None):
        """
        Log administrative actions with enhanced security tracking.
        
        Args:
            admin_user (User): Administrator performing the action
            action (str): Administrative action
            target_user (User, optional): User being acted upon
            details (dict, optional): Action details
            request (HttpRequest, optional): Request object
        """
        audit_details = details or {}
        audit_details.update({
            'admin_user_id': admin_user.id,
            'admin_username': admin_user.username,
            'is_admin_action': True,
        })
        
        if target_user:
            audit_details.update({
                'target_user_id': target_user.id,
                'target_username': target_user.username,
            })
        
        AuditLog.log_action(
            action=action,
            user=admin_user,
            request=request,
            details=audit_details
        )
        
        # Also log as security event for admin actions
        SecurityEvent.log_event(
            event_type='admin_impersonation' if 'impersonate' in action else 'privilege_escalation',
            user=admin_user,
            request=request,
            severity='medium',
            details=audit_details
        )


class ThreatDetector:
    """
    Advanced threat detection system.
    """
    
    @staticmethod
    def analyze_login_pattern(user, ip_address, user_agent):
        """
        Analyze login patterns for anomaly detection.
        
        Args:
            user (User): User attempting to login
            ip_address (str): IP address of login attempt
            user_agent (str): User agent string
            
        Returns:
            dict: Threat analysis results
        """
        threats = []
        risk_score = 0
        
        # Check for geographic anomalies
        if ThreatDetector._detect_geographic_anomaly(user, ip_address):
            threats.append({
                'type': 'geographic_anomaly',
                'description': 'Login from unusual geographic location',
                'risk_score': 30
            })
            risk_score += 30
        
        # Check for time-based anomalies
        if ThreatDetector._detect_time_anomaly(user):
            threats.append({
                'type': 'time_anomaly',
                'description': 'Login at unusual time',
                'risk_score': 15
            })
            risk_score += 15
        
        # Check for device/browser anomalies
        if ThreatDetector._detect_device_anomaly(user, user_agent):
            threats.append({
                'type': 'device_anomaly',
                'description': 'Login from new or unusual device',
                'risk_score': 20
            })
            risk_score += 20
        
        # Check for velocity anomalies
        if ThreatDetector._detect_velocity_anomaly(user, ip_address):
            threats.append({
                'type': 'velocity_anomaly',
                'description': 'Impossible travel time between logins',
                'risk_score': 40
            })
            risk_score += 40
        
        return {
            'threats': threats,
            'risk_score': min(risk_score, 100),
            'risk_level': SecurityMonitor._get_risk_level(risk_score),
            'requires_additional_verification': risk_score >= 50,
        }
    
    @staticmethod
    def _detect_geographic_anomaly(user, ip_address):
        """Detect if login is from unusual geographic location."""
        # This would typically use a GeoIP service
        # For now, we'll check if this IP has been used before
        recent_ips = SecurityEvent.objects.filter(
            user=user,
            event_type='login_success',
            created_at__gte=timezone.now() - timedelta(days=30)
        ).values_list('ip_address', flat=True).distinct()
        
        return ip_address not in recent_ips and len(recent_ips) > 0
    
    @staticmethod
    def _detect_time_anomaly(user):
        """Detect if login is at unusual time for this user."""
        now = timezone.now()
        hour = now.hour
        
        # Get user's typical login hours
        recent_logins = SecurityEvent.objects.filter(
            user=user,
            event_type='login_success',
            created_at__gte=timezone.now() - timedelta(days=30)
        ).values_list('created_at', flat=True)
        
        if not recent_logins:
            return False
        
        typical_hours = [login.hour for login in recent_logins]
        
        # If current hour is not in typical hours and it's outside business hours
        if hour not in typical_hours and (hour < 6 or hour > 22):
            return True
        
        return False
    
    @staticmethod
    def _detect_device_anomaly(user, user_agent):
        """Detect if login is from new or unusual device."""
        recent_agents = SecurityEvent.objects.filter(
            user=user,
            event_type='login_success',
            created_at__gte=timezone.now() - timedelta(days=30)
        ).values_list('user_agent', flat=True).distinct()
        
        return user_agent not in recent_agents and len(recent_agents) > 0
    
    @staticmethod
    def _detect_velocity_anomaly(user, ip_address):
        """Detect impossible travel time between logins."""
        # Get last login from different IP
        last_different_login = SecurityEvent.objects.filter(
            user=user,
            event_type='login_success',
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).exclude(ip_address=ip_address).first()
        
        if last_different_login:
            # If there was a login from different IP within 1 hour
            # This could indicate account compromise
            return True
        
        return False