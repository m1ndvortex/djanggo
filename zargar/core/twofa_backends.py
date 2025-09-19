"""
Custom authentication backends for 2FA integration.
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .models import TOTPDevice
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class TwoFABackend(ModelBackend):
    """
    Custom authentication backend that handles 2FA verification.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user with username/password and handle 2FA if enabled.
        """
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        
        if username is None or password is None:
            return None
        
        try:
            user = User._default_manager.get_by_natural_key(username)
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user (#20760).
            User().set_password(password)
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            # Check if user has 2FA enabled
            if user.is_2fa_enabled:
                try:
                    totp_device = TOTPDevice.objects.get(user=user, is_confirmed=True)
                    # Don't complete authentication yet - redirect to 2FA verification
                    # Store user ID in session for 2FA verification
                    if request:
                        request.session['2fa_user_id'] = user.id
                        request.session['2fa_next_url'] = request.GET.get('next', '/')
                    
                    # Return None to indicate 2FA verification is needed
                    return None
                except TOTPDevice.DoesNotExist:
                    # User has 2FA enabled but no confirmed device - disable 2FA
                    user.is_2fa_enabled = False
                    user.save(update_fields=['is_2fa_enabled'])
                    logger.warning(f"User {user.username} had 2FA enabled but no confirmed device. Disabled 2FA.")
            
            # User doesn't have 2FA or 2FA is not properly configured
            return user
        
        return None
    
    def user_can_authenticate(self, user):
        """
        Reject users with is_active=False. Custom user models that don't have
        an `is_active` field are allowed.
        """
        is_active = getattr(user, 'is_active', None)
        return is_active or is_active is None


class AdminTwoFABackend(ModelBackend):
    """
    Custom authentication backend for admin users with mandatory 2FA.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate admin user with mandatory 2FA verification.
        """
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        
        if username is None or password is None:
            return None
        
        try:
            user = User._default_manager.get_by_natural_key(username)
        except User.DoesNotExist:
            User().set_password(password)
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            # Check if user is super admin
            if user.is_superuser:
                # Super admins must have 2FA enabled
                if not user.is_2fa_enabled:
                    logger.warning(f"Super admin {user.username} attempted login without 2FA enabled")
                    return None
                
                try:
                    totp_device = TOTPDevice.objects.get(user=user, is_confirmed=True)
                    # Store user ID in session for 2FA verification
                    if request:
                        request.session['2fa_user_id'] = user.id
                        request.session['2fa_next_url'] = request.GET.get('next', '/admin/dashboard/')
                        request.session['is_admin_login'] = True
                    
                    # Return None to indicate 2FA verification is needed
                    return None
                except TOTPDevice.DoesNotExist:
                    logger.error(f"Super admin {user.username} has 2FA enabled but no confirmed device")
                    return None
            
            # Regular user authentication (shouldn't happen in admin context)
            return user
        
        return None