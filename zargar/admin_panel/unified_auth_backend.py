"""
Unified authentication backend for SuperAdmin access.
This consolidates all admin authentication flows into a single secure system.
"""
import logging
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django_tenants.utils import get_public_schema_name, schema_context
from django_otp import match_token
from django_otp.models import Device

from zargar.tenants.admin_models import SuperAdmin, TenantAccessLog

logger = logging.getLogger('zargar.admin_auth')


class UnifiedSuperAdminAuthBackend(ModelBackend):
    """
    Unified authentication backend for SuperAdmin users.
    Handles authentication, 2FA, session management, and audit logging.
    """
    
    def authenticate(self, request, username=None, password=None, otp_token=None, **kwargs):
        """
        Authenticate SuperAdmin with comprehensive security controls.
        """
        if not username or not password:
            return None
        
        # Only authenticate in public schema
        if connection.schema_name != get_public_schema_name():
            logger.warning(f"SuperAdmin authentication attempted in tenant schema: {connection.schema_name}")
            return None
        
        try:
            # Get SuperAdmin user
            user = SuperAdmin.objects.get(username=username)
        except SuperAdmin.DoesNotExist:
            # Run password hasher to prevent timing attacks
            SuperAdmin().set_password(password)
            self._log_failed_attempt(request, username, 'user_not_found')
            return None
        
        # Check if user is active
        if not user.is_active:
            self._log_failed_attempt(request, username, 'user_inactive')
            return None
        
        # Verify password
        if not user.check_password(password):
            self._log_failed_attempt(request, username, 'invalid_password')
            return None
        
        # Check 2FA if enabled
        if user.is_2fa_enabled:
            if not otp_token:
                # Return partial authentication - frontend should prompt for 2FA
                self._log_authentication_event(request, user, 'partial_auth_2fa_required')
                return None
            
            if not self._verify_2fa_token(user, otp_token):
                self._log_failed_attempt(request, username, 'invalid_2fa')
                return None
        
        # Authentication successful
        self._log_successful_authentication(request, user)
        self._update_user_login_info(request, user)
        
        return user
    
    def get_user(self, user_id):
        """
        Get SuperAdmin user by ID.
        """
        if connection.schema_name != get_public_schema_name():
            return None
        
        try:
            return SuperAdmin.objects.get(pk=user_id)
        except SuperAdmin.DoesNotExist:
            return None
    
    def user_can_authenticate(self, user):
        """
        Check if SuperAdmin user can authenticate.
        """
        # Only allow SuperAdmin instances
        if not isinstance(user, SuperAdmin):
            return False
        
        is_active = getattr(user, 'is_active', None)
        is_superuser = getattr(user, 'is_superuser', None)
        
        return (is_active or is_active is None) and (is_superuser or is_superuser is None)
    
    def _verify_2fa_token(self, user, token):
        """
        Verify 2FA token for user.
        """
        try:
            # Try to match token against user's devices
            device = match_token(user, token)
            if device:
                logger.info(f"2FA verification successful for user {user.username}")
                return True
            
            logger.warning(f"2FA verification failed for user {user.username}")
            return False
        except Exception as e:
            logger.error(f"Error verifying 2FA token for user {user.username}: {str(e)}")
            return False
    
    def _log_successful_authentication(self, request, user):
        """
        Log successful authentication event.
        """
        try:
            TenantAccessLog.log_action(
                user=user,
                tenant_schema='public',
                action='login',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
                success=True,
                details={
                    'authentication_method': 'unified_superadmin_backend',
                    '2fa_used': user.is_2fa_enabled,
                    'login_timestamp': timezone.now().isoformat()
                }
            )
            
            logger.info(f"Successful SuperAdmin authentication: {user.username} from {self._get_client_ip(request)}")
        except Exception as e:
            logger.error(f"Error logging successful authentication: {str(e)}")
    
    def _log_failed_attempt(self, request, username, reason):
        """
        Log failed authentication attempt.
        """
        try:
            # Log directly to TenantAccessLog without using log_action method
            TenantAccessLog.objects.create(
                user_type='superadmin',
                user_id=0,  # Use 0 for failed attempts
                username=username,
                tenant_schema='public',
                action='login',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
                success=False,
                error_message=f'Authentication failed: {reason}',
                details={
                    'authentication_method': 'unified_superadmin_backend',
                    'failure_reason': reason,
                    'attempt_timestamp': timezone.now().isoformat()
                }
            )
            
            logger.warning(f"Failed SuperAdmin authentication: {username} from {self._get_client_ip(request)} - {reason}")
        except Exception as e:
            logger.error(f"Error logging failed authentication: {str(e)}")
    
    def _log_authentication_event(self, request, user, event_type):
        """
        Log general authentication event.
        """
        try:
            TenantAccessLog.log_action(
                user=user,
                tenant_schema='public',
                action=event_type,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
                success=True,
                details={
                    'authentication_method': 'unified_superadmin_backend',
                    'event_timestamp': timezone.now().isoformat()
                }
            )
            
            logger.info(f"SuperAdmin authentication event: {user.username} - {event_type}")
        except Exception as e:
            logger.error(f"Error logging authentication event: {str(e)}")
    
    def _update_user_login_info(self, request, user):
        """
        Update user's last login information.
        """
        try:
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # Record tenant access
            user.record_tenant_access('public')
        except Exception as e:
            logger.error(f"Error updating user login info: {str(e)}")
    
    def _get_client_ip(self, request):
        """
        Get client IP address from request.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip


class UnifiedSessionManager:
    """
    Unified session management for SuperAdmin users.
    Handles cross-tenant access tracking and session security.
    """
    
    @staticmethod
    def create_admin_session(request, user):
        """
        Create a new admin session with comprehensive tracking.
        """
        try:
            from zargar.tenants.admin_models import SuperAdminSession
            
            session = SuperAdminSession.objects.create(
                super_admin=user,
                tenant_schema='public',
                session_key=request.session.session_key,
                ip_address=UnifiedSessionManager._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                access_time=timezone.now(),
                is_active=True
            )
            
            # Store session info in Django session
            request.session['admin_session_id'] = str(session.id)
            request.session['admin_user_id'] = user.id
            request.session['admin_username'] = user.username
            request.session['session_start_time'] = timezone.now().isoformat()
            
            logger.info(f"Created admin session for {user.username}: {session.id}")
            return session
        except Exception as e:
            logger.error(f"Error creating admin session: {str(e)}")
            return None
    
    @staticmethod
    def track_tenant_access(request, user, tenant_schema):
        """
        Track when SuperAdmin accesses a specific tenant.
        """
        try:
            # Log tenant access
            TenantAccessLog.log_action(
                user=user,
                tenant_schema=tenant_schema,
                action='tenant_switch',
                ip_address=UnifiedSessionManager._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
                success=True,
                details={
                    'previous_schema': request.session.get('current_tenant_schema', 'public'),
                    'new_schema': tenant_schema,
                    'access_timestamp': timezone.now().isoformat()
                }
            )
            
            # Update session info
            request.session['current_tenant_schema'] = tenant_schema
            request.session['last_tenant_access'] = timezone.now().isoformat()
            
            # Record in user model
            user.record_tenant_access(tenant_schema)
            
            logger.info(f"SuperAdmin {user.username} accessed tenant: {tenant_schema}")
        except Exception as e:
            logger.error(f"Error tracking tenant access: {str(e)}")
    
    @staticmethod
    def end_admin_session(request, user):
        """
        End admin session and clean up.
        """
        try:
            session_id = request.session.get('admin_session_id')
            if session_id:
                from zargar.tenants.admin_models import SuperAdminSession
                
                try:
                    session = SuperAdminSession.objects.get(id=session_id)
                    session.is_active = False
                    session.save()
                except SuperAdminSession.DoesNotExist:
                    pass
            
            # Log logout
            TenantAccessLog.log_action(
                user=user,
                tenant_schema='public',
                action='logout',
                ip_address=UnifiedSessionManager._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
                success=True,
                details={
                    'session_duration': UnifiedSessionManager._calculate_session_duration(request),
                    'logout_timestamp': timezone.now().isoformat()
                }
            )
            
            # Clear session data
            admin_keys = [key for key in request.session.keys() if key.startswith('admin_')]
            for key in admin_keys:
                del request.session[key]
            
            logger.info(f"Ended admin session for {user.username}")
        except Exception as e:
            logger.error(f"Error ending admin session: {str(e)}")
    
    @staticmethod
    def _get_client_ip(request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    @staticmethod
    def _calculate_session_duration(request):
        """Calculate session duration in seconds."""
        try:
            start_time_str = request.session.get('session_start_time')
            if start_time_str:
                from datetime import datetime
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                duration = (timezone.now() - start_time).total_seconds()
                return int(duration)
        except Exception:
            pass
        return 0


class UnifiedAuthPermissions:
    """
    Unified permission checking for SuperAdmin users.
    """
    
    @staticmethod
    def check_superadmin_permission(user):
        """
        Check if user has SuperAdmin permissions.
        """
        if not user or not user.is_authenticated:
            return False
        
        return (
            isinstance(user, SuperAdmin) and
            user.is_active and
            user.is_superuser
        )
    
    @staticmethod
    def check_tenant_access_permission(user, tenant_schema):
        """
        Check if SuperAdmin can access specific tenant.
        """
        if not UnifiedAuthPermissions.check_superadmin_permission(user):
            return False
        
        return getattr(user, 'can_access_all_data', True)
    
    @staticmethod
    def check_tenant_creation_permission(user):
        """
        Check if SuperAdmin can create tenants.
        """
        if not UnifiedAuthPermissions.check_superadmin_permission(user):
            return False
        
        return getattr(user, 'can_create_tenants', True)
    
    @staticmethod
    def check_tenant_suspension_permission(user):
        """
        Check if SuperAdmin can suspend tenants.
        """
        if not UnifiedAuthPermissions.check_superadmin_permission(user):
            return False
        
        return getattr(user, 'can_suspend_tenants', True)
    
    @staticmethod
    def check_impersonation_permission(user):
        """
        Check if SuperAdmin can impersonate users.
        """
        if not UnifiedAuthPermissions.check_superadmin_permission(user):
            return False
        
        return getattr(user, 'can_access_all_data', True)