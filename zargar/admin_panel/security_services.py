"""
Security policy services for the admin panel.
"""
import re
import hashlib
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.conf import settings
from .models import SecurityPolicy


class PasswordPolicyService:
    """Service for password policy validation and enforcement."""
    
    @classmethod
    def validate_password(cls, password, user=None):
        """
        Validate password against active password policy.
        
        Args:
            password (str): Password to validate
            user (User, optional): User for context-specific validation
            
        Returns:
            tuple: (is_valid, errors_list)
        """
        policy = SecurityPolicy.get_password_policy()
        errors = []
        
        # Check minimum length
        if len(password) < policy.get('min_length', 8):
            errors.append(f'Password must be at least {policy.get("min_length", 8)} characters long.')
        
        # Check uppercase requirement
        if policy.get('require_uppercase', True) and not re.search(r'[A-Z]', password):
            errors.append('Password must contain at least one uppercase letter.')
        
        # Check lowercase requirement
        if policy.get('require_lowercase', True) and not re.search(r'[a-z]', password):
            errors.append('Password must contain at least one lowercase letter.')
        
        # Check numbers requirement
        if policy.get('require_numbers', True) and not re.search(r'\d', password):
            errors.append('Password must contain at least one number.')
        
        # Check special characters requirement
        if policy.get('require_special_chars', True):
            special_chars = policy.get('special_chars', '!@#$%^&*()_+-=[]{}|;:,.<>?')
            if not re.search(f'[{re.escape(special_chars)}]', password):
                errors.append(f'Password must contain at least one special character: {special_chars}')
        
        # Check password reuse (if user provided)
        if user and policy.get('prevent_reuse_count', 0) > 0:
            if cls._is_password_reused(user, password, policy.get('prevent_reuse_count')):
                errors.append(f'Password cannot be one of your last {policy.get("prevent_reuse_count")} passwords.')
        
        # Run Django's built-in password validators
        try:
            validate_password(password, user)
        except ValidationError as e:
            errors.extend(e.messages)
        
        return len(errors) == 0, errors
    
    @classmethod
    def _is_password_reused(cls, user, new_password, prevent_count):
        """Check if password was recently used."""
        # This would require storing password hashes in a separate model
        # For now, return False as this is a placeholder
        # TODO: Implement password history tracking
        return False
    
    @classmethod
    def is_password_expired(cls, user):
        """Check if user's password has expired based on policy."""
        policy = SecurityPolicy.get_password_policy()
        max_age_days = policy.get('max_age_days', 90)
        
        if not hasattr(user, 'password_changed_at') or not user.password_changed_at:
            # If no password change date, consider it expired
            return True
        
        expiry_date = user.password_changed_at + timedelta(days=max_age_days)
        return timezone.now() > expiry_date
    
    @classmethod
    def get_password_strength_score(cls, password):
        """
        Calculate password strength score (0-100).
        
        Args:
            password (str): Password to evaluate
            
        Returns:
            int: Strength score from 0 to 100
        """
        score = 0
        
        # Length scoring
        if len(password) >= 8:
            score += 20
        if len(password) >= 12:
            score += 10
        if len(password) >= 16:
            score += 10
        
        # Character variety scoring
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'\d', password):
            score += 10
        if re.search(r'[!@#$%^&*()_+-=\[\]{}|;:,.<>?]', password):
            score += 15
        
        # Pattern penalties
        if re.search(r'(.)\1{2,}', password):  # Repeated characters
            score -= 10
        if re.search(r'(012|123|234|345|456|567|678|789|890)', password):  # Sequential numbers
            score -= 10
        if re.search(r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)', password.lower()):  # Sequential letters
            score -= 10
        
        # Common patterns
        common_patterns = ['password', '123456', 'qwerty', 'admin', 'login']
        for pattern in common_patterns:
            if pattern in password.lower():
                score -= 20
                break
        
        return max(0, min(100, score))


class SessionPolicyService:
    """Service for session policy enforcement."""
    
    @classmethod
    def get_session_timeout(cls):
        """Get session timeout in seconds."""
        policy = SecurityPolicy.get_session_policy()
        return policy.get('timeout_minutes', 480) * 60  # Convert to seconds
    
    @classmethod
    def get_max_concurrent_sessions(cls):
        """Get maximum concurrent sessions allowed per user."""
        policy = SecurityPolicy.get_session_policy()
        return policy.get('max_concurrent_sessions', 3)
    
    @classmethod
    def should_require_reauth(cls, action_type):
        """Check if action requires re-authentication."""
        policy = SecurityPolicy.get_session_policy()
        
        if not policy.get('require_reauth_for_sensitive', True):
            return False
        
        sensitive_actions = [
            'password_change',
            'user_delete',
            'security_settings_change',
            'backup_restore',
            'tenant_delete',
            'financial_data_export',
        ]
        
        return action_type in sensitive_actions
    
    @classmethod
    def extend_session_on_activity(cls):
        """Check if sessions should be extended on activity."""
        policy = SecurityPolicy.get_session_policy()
        return policy.get('extend_on_activity', True)
    
    @classmethod
    def use_secure_cookies(cls):
        """Check if secure cookies should be used."""
        policy = SecurityPolicy.get_session_policy()
        return policy.get('secure_cookies', True)
    
    @classmethod
    def cleanup_expired_sessions(cls, user):
        """Clean up expired sessions for a user."""
        # This would integrate with Django's session framework
        # For now, this is a placeholder
        pass
    
    @classmethod
    def enforce_concurrent_session_limit(cls, user, current_session_key):
        """Enforce concurrent session limits."""
        max_sessions = cls.get_max_concurrent_sessions()
        
        # This would require tracking active sessions
        # For now, this is a placeholder
        # TODO: Implement session tracking and cleanup
        pass


class RateLimitPolicyService:
    """Service for rate limiting policy enforcement."""
    
    @classmethod
    def get_rate_limit(cls, limit_type):
        """
        Get rate limit configuration for a specific type.
        
        Args:
            limit_type (str): Type of rate limit (login, api_call, etc.)
            
        Returns:
            dict: Rate limit configuration with 'requests' and 'window_minutes'
        """
        policy = SecurityPolicy.get_rate_limit_policy()
        limits = policy.get('limits', {})
        
        return limits.get(limit_type, {'requests': 100, 'window_minutes': 60})
    
    @classmethod
    def is_rate_limited(cls, identifier, limit_type, endpoint=''):
        """
        Check if an identifier is currently rate limited.
        
        Args:
            identifier (str): Unique identifier (IP, user ID, etc.)
            limit_type (str): Type of rate limit
            endpoint (str): Specific endpoint (optional)
            
        Returns:
            tuple: (is_limited, remaining_requests, reset_time)
        """
        cache_key = f"rate_limit:{limit_type}:{identifier}:{endpoint}"
        limit_config = cls.get_rate_limit(limit_type)
        
        max_requests = limit_config['requests']
        window_minutes = limit_config['window_minutes']
        
        # Get current count from cache
        current_data = cache.get(cache_key, {'count': 0, 'window_start': timezone.now()})
        
        # Check if we're in a new window
        window_duration = timedelta(minutes=window_minutes)
        if timezone.now() - current_data['window_start'] > window_duration:
            # Reset for new window
            current_data = {'count': 0, 'window_start': timezone.now()}
        
        is_limited = current_data['count'] >= max_requests
        remaining = max(0, max_requests - current_data['count'])
        reset_time = current_data['window_start'] + window_duration
        
        return is_limited, remaining, reset_time
    
    @classmethod
    def record_request(cls, identifier, limit_type, endpoint=''):
        """
        Record a request for rate limiting.
        
        Args:
            identifier (str): Unique identifier
            limit_type (str): Type of rate limit
            endpoint (str): Specific endpoint (optional)
            
        Returns:
            tuple: (is_now_limited, remaining_requests, reset_time)
        """
        cache_key = f"rate_limit:{limit_type}:{identifier}:{endpoint}"
        limit_config = cls.get_rate_limit(limit_type)
        
        max_requests = limit_config['requests']
        window_minutes = limit_config['window_minutes']
        
        # Get current count from cache
        current_data = cache.get(cache_key, {'count': 0, 'window_start': timezone.now()})
        
        # Check if we're in a new window
        window_duration = timedelta(minutes=window_minutes)
        if timezone.now() - current_data['window_start'] > window_duration:
            # Reset for new window
            current_data = {'count': 0, 'window_start': timezone.now()}
        
        # Increment count
        current_data['count'] += 1
        
        # Save to cache
        cache.set(cache_key, current_data, timeout=window_minutes * 60)
        
        is_limited = current_data['count'] >= max_requests
        remaining = max(0, max_requests - current_data['count'])
        reset_time = current_data['window_start'] + window_duration
        
        return is_limited, remaining, reset_time


class AuthenticationPolicyService:
    """Service for authentication policy enforcement."""
    
    @classmethod
    def requires_2fa(cls, user=None):
        """Check if 2FA is required."""
        policy = SecurityPolicy.get_authentication_policy()
        return policy.get('require_2fa', False)
    
    @classmethod
    def get_lockout_config(cls):
        """Get account lockout configuration."""
        policy = SecurityPolicy.get_authentication_policy()
        return {
            'attempts': policy.get('lockout_attempts', 5),
            'duration_minutes': policy.get('lockout_duration_minutes', 30),
        }
    
    @classmethod
    def get_password_reset_token_expiry(cls):
        """Get password reset token expiry in hours."""
        policy = SecurityPolicy.get_authentication_policy()
        return policy.get('password_reset_token_expiry_hours', 24)
    
    @classmethod
    def get_remember_me_duration(cls):
        """Get remember me duration in days."""
        policy = SecurityPolicy.get_authentication_policy()
        return policy.get('remember_me_duration_days', 30)
    
    @classmethod
    def is_account_locked(cls, user):
        """Check if user account is locked due to failed attempts."""
        lockout_config = cls.get_lockout_config()
        
        # This would require tracking failed login attempts
        # For now, this is a placeholder
        # TODO: Implement account lockout tracking
        return False
    
    @classmethod
    def record_failed_login(cls, user_or_username, ip_address):
        """Record a failed login attempt."""
        # This would integrate with the SecurityEvent model
        # For now, this is a placeholder
        # TODO: Implement failed login tracking
        pass
    
    @classmethod
    def clear_failed_login_attempts(cls, user):
        """Clear failed login attempts for successful login."""
        # This would clear the failed attempt counter
        # For now, this is a placeholder
        # TODO: Implement failed login attempt clearing
        pass


class SecurityPolicyEnforcer:
    """Main service for enforcing all security policies."""
    
    def __init__(self):
        self.password_service = PasswordPolicyService()
        self.session_service = SessionPolicyService()
        self.rate_limit_service = RateLimitPolicyService()
        self.auth_service = AuthenticationPolicyService()
    
    def validate_password(self, password, user=None):
        """Validate password against policy."""
        return self.password_service.validate_password(password, user)
    
    def check_rate_limit(self, identifier, limit_type, endpoint=''):
        """Check if request should be rate limited."""
        return self.rate_limit_service.is_rate_limited(identifier, limit_type, endpoint)
    
    def record_request(self, identifier, limit_type, endpoint=''):
        """Record a request for rate limiting."""
        return self.rate_limit_service.record_request(identifier, limit_type, endpoint)
    
    def get_session_timeout(self):
        """Get session timeout."""
        return self.session_service.get_session_timeout()
    
    def requires_2fa(self, user=None):
        """Check if 2FA is required."""
        return self.auth_service.requires_2fa(user)
    
    def should_require_reauth(self, action_type):
        """Check if action requires re-authentication."""
        return self.session_service.should_require_reauth(action_type)


# Global instance
security_enforcer = SecurityPolicyEnforcer()