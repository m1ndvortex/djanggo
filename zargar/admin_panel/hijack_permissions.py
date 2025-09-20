"""
Custom permissions and authorization for django-hijack integration.
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponseForbidden
from functools import wraps
import logging

from zargar.tenants.admin_models import SuperAdmin

logger = logging.getLogger('hijack_audit')
User = get_user_model()


def is_super_admin(request):
    """
    Check if the current user is a super admin.
    This is used as HIJACK_PERMISSION_CHECK.
    
    Args:
        request: Django request object
        
    Returns:
        bool: True if user is a super admin, False otherwise
    """
    if not request.user.is_authenticated:
        logger.warning(f"Hijack permission denied: User not authenticated from IP {get_client_ip(request)}")
        return False
    
    # Check if user is a SuperAdmin instance (from public schema)
    if hasattr(request.user, '_meta') and request.user._meta.model_name == 'superadmin':
        is_super = request.user.is_superuser and request.user.is_active
        if is_super:
            logger.info(f"Hijack permission granted to super admin: {request.user.username}")
        else:
            logger.warning(f"Hijack permission denied: SuperAdmin {request.user.username} is not active or not superuser")
        return is_super
    
    # Check if user is SuperAdmin class directly
    if hasattr(request.user, '__class__') and request.user.__class__.__name__ == 'SuperAdmin':
        is_super = request.user.is_superuser and request.user.is_active
        if is_super:
            logger.info(f"Hijack permission granted to super admin: {request.user.username}")
        else:
            logger.warning(f"Hijack permission denied: SuperAdmin {request.user.username} is not active or not superuser")
        return is_super
    
    # Fallback check for regular User model with superuser flag
    if hasattr(request.user, 'is_superuser') and request.user.is_superuser:
        logger.info(f"Hijack permission granted to superuser: {request.user.username}")
        return True
    
    logger.warning(f"Hijack permission denied: User {request.user.username} is not a super admin")
    return False


def authorize_hijack(hijacker, hijacked, request):
    """
    Custom authorization check for hijack attempts.
    This is used as HIJACK_AUTHORIZATION_CHECK.
    
    Args:
        hijacker: User attempting to perform hijack
        hijacked: User being hijacked
        request: Django request object
        
    Returns:
        bool: True if hijack is authorized, False otherwise
    """
    # Log the hijack attempt
    logger.info(f"Hijack authorization check: {hijacker.username} attempting to hijack {hijacked.username}")
    
    # Prevent self-hijacking
    if hijacker.id == hijacked.id:
        logger.warning(f"Hijack denied: {hijacker.username} attempted to hijack themselves")
        return False
    
    # Only super admins can hijack
    if not is_super_admin(request):
        logger.warning(f"Hijack denied: {hijacker.username} is not a super admin")
        return False
    
    # Prevent hijacking other super admins
    if (hasattr(hijacked, '_meta') and hijacked._meta.model_name == 'superadmin') or \
       (hasattr(hijacked, '__class__') and hijacked.__class__.__name__ == 'SuperAdmin'):
        logger.warning(f"Hijack denied: {hijacker.username} attempted to hijack another super admin {hijacked.username}")
        return False
    
    # Prevent hijacking superusers
    if hasattr(hijacked, 'is_superuser') and hijacked.is_superuser:
        logger.warning(f"Hijack denied: {hijacker.username} attempted to hijack superuser {hijacked.username}")
        return False
    
    # Check if target user is active
    if not hijacked.is_active:
        logger.warning(f"Hijack denied: Target user {hijacked.username} is not active")
        return False
    
    # Additional security checks
    client_ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Log successful authorization
    logger.info(f"Hijack authorized: {hijacker.username} -> {hijacked.username} from IP {client_ip}")
    
    return True


def hijack_decorator(view_func):
    """
    Custom decorator for hijack views to add additional security and logging.
    This is used as HIJACK_DECORATOR.
    
    Args:
        view_func: View function to decorate
        
    Returns:
        Decorated view function
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Additional security checks before allowing hijack
        if not request.user.is_authenticated:
            logger.warning(f"Hijack attempt from unauthenticated user at IP {get_client_ip(request)}")
            return HttpResponseForbidden(_('Authentication required'))
        
        # Check for suspicious activity
        client_ip = get_client_ip(request)
        if is_suspicious_ip(client_ip):
            logger.error(f"Hijack attempt from suspicious IP: {client_ip} by user {request.user.username}")
            return HttpResponseForbidden(_('Access denied from this IP address'))
        
        # Rate limiting check
        if is_rate_limited(request.user, 'hijack'):
            logger.warning(f"Hijack rate limit exceeded for user {request.user.username}")
            return HttpResponseForbidden(_('Too many hijack attempts. Please wait before trying again.'))
        
        # Log the hijack attempt
        logger.info(f"Hijack view accessed by {request.user.username} from IP {client_ip}")
        
        try:
            return view_func(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in hijack view for user {request.user.username}: {str(e)}")
            raise
    
    return wrapper


def get_client_ip(request):
    """
    Get the client IP address from the request.
    
    Args:
        request: Django request object
        
    Returns:
        str: Client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def is_suspicious_ip(ip_address):
    """
    Check if an IP address is flagged as suspicious.
    
    Args:
        ip_address (str): IP address to check
        
    Returns:
        bool: True if IP is suspicious, False otherwise
    """
    # Import here to avoid circular imports
    from zargar.core.security_models import SuspiciousActivity
    
    try:
        # Check if IP has been flagged for suspicious activity
        suspicious_count = SuspiciousActivity.objects.filter(
            ip_address=ip_address,
            is_resolved=False
        ).count()
        
        return suspicious_count > 0
    except Exception:
        # If we can't check, err on the side of caution but don't block
        return False


def is_rate_limited(user, action_type):
    """
    Check if a user is rate limited for a specific action.
    
    Args:
        user: User object
        action_type (str): Type of action (e.g., 'hijack')
        
    Returns:
        bool: True if rate limited, False otherwise
    """
    # Import here to avoid circular imports
    from zargar.core.security_models import RateLimitAttempt
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        # Check hijack attempts in the last hour
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_attempts = RateLimitAttempt.objects.filter(
            user_id=user.id,
            action_type=action_type,
            timestamp__gte=one_hour_ago
        ).count()
        
        # Allow maximum 5 hijack attempts per hour
        return recent_attempts >= 5
    except Exception:
        # If we can't check, don't block
        return False


def log_hijack_attempt(hijacker, hijacked, success, reason=None):
    """
    Log a hijack attempt for audit purposes.
    
    Args:
        hijacker: User attempting hijack
        hijacked: User being hijacked
        success (bool): Whether the attempt was successful
        reason (str): Reason for failure (if applicable)
    """
    # Import here to avoid circular imports
    from zargar.core.security_models import SecurityEvent
    
    try:
        event_type = 'hijack_success' if success else 'hijack_failure'
        description = f"Admin {hijacker.username} {'successfully hijacked' if success else 'failed to hijack'} user {hijacked.username}"
        
        if reason:
            description += f". Reason: {reason}"
        
        SecurityEvent.objects.create(
            event_type=event_type,
            user_id=hijacker.id,
            description=description,
            severity='high',
            metadata={
                'hijacker_id': hijacker.id,
                'hijacker_username': hijacker.username,
                'hijacked_id': hijacked.id,
                'hijacked_username': hijacked.username,
                'success': success,
                'reason': reason,
            }
        )
        
        logger.info(f"Security event logged: {description}")
    except Exception as e:
        logger.error(f"Failed to log hijack attempt: {str(e)}")


def check_hijack_permissions(user, target_user):
    """
    Comprehensive permission check for hijack operations.
    
    Args:
        user: User attempting hijack
        target_user: User being hijacked
        
    Returns:
        tuple: (allowed: bool, reason: str)
    """
    # Check if user is super admin
    is_super_admin = False
    if hasattr(user, '_meta') and user._meta.model_name == 'superadmin' and user.is_superuser:
        is_super_admin = True
    elif hasattr(user, '__class__') and user.__class__.__name__ == 'SuperAdmin' and user.is_superuser:
        is_super_admin = True
    
    if not is_super_admin:
        return False, "Only super admins can perform impersonation"
    
    # Check if target user exists and is active
    if not target_user or not target_user.is_active:
        return False, "Target user is not active or does not exist"
    
    # Prevent self-hijacking
    if user.id == target_user.id:
        return False, "Cannot impersonate yourself"
    
    # Prevent hijacking other super admins
    if (hasattr(target_user, '_meta') and target_user._meta.model_name == 'superadmin') or \
       (hasattr(target_user, '__class__') and target_user.__class__.__name__ == 'SuperAdmin'):
        return False, "Cannot impersonate other super admins"
    
    # Prevent hijacking superusers
    if hasattr(target_user, 'is_superuser') and target_user.is_superuser:
        return False, "Cannot impersonate superusers"
    
    return True, "Permission granted"


def get_hijackable_users(admin_user):
    """
    Get list of users that can be hijacked by the given admin.
    
    Args:
        admin_user: Super admin user
        
    Returns:
        QuerySet: Users that can be hijacked
    """
    if not is_super_admin_user(admin_user):
        return User.objects.none()
    
    # Get all active tenant users (exclude super admins and superusers)
    hijackable_users = User.objects.filter(
        is_active=True,
        is_superuser=False
    ).exclude(
        id=admin_user.id
    )
    
    # Additional filtering to exclude SuperAdmin instances
    # This is handled by the fact that SuperAdmin and User are different models
    
    return hijackable_users


def is_super_admin_user(user):
    """
    Check if a user is a super admin (helper function).
    
    Args:
        user: User object to check
        
    Returns:
        bool: True if user is super admin
    """
    return (
        user and 
        user.is_authenticated and 
        hasattr(user, '_meta') and 
        user._meta.model_name == 'superadmin' and 
        user.is_superuser and 
        user.is_active
    )