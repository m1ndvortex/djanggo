"""
Unified authentication middleware for SuperAdmin access.
Handles session management, security controls, and audit logging.
"""
import logging
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import connection
from django_tenants.utils import get_public_schema_name

from zargar.tenants.admin_models import SuperAdmin, TenantAccessLog
from .unified_auth_backend import UnifiedSessionManager, UnifiedAuthPermissions

logger = logging.getLogger('zargar.admin_auth')


class UnifiedAdminAuthMiddleware(MiddlewareMixin):
    """
    Middleware to handle unified admin authentication and session management.
    """
    
    # URLs that don't require authentication
    EXEMPT_URLS = [
        '/admin/login/',
        '/admin/logout/',
        '/super-panel/login/',
        '/super-panel/logout/',
        '/health/',
        '/api/health/',
    ]
    
    # URLs that require SuperAdmin authentication
    ADMIN_URLS = [
        '/admin/',
        '/super-panel/',
    ]
    
    def process_request(self, request):
        """
        Process incoming request for admin authentication.
        """
        # Skip if not in public schema
        if connection.schema_name != get_public_schema_name():
            return None
        
        # Skip exempt URLs
        if any(request.path.startswith(url) for url in self.EXEMPT_URLS):
            return None
        
        # Check if this is an admin URL
        is_admin_url = any(request.path.startswith(url) for url in self.ADMIN_URLS)
        if not is_admin_url:
            return None
        
        # Check authentication
        if not self._is_authenticated_superadmin(request):
            return self._handle_unauthenticated_request(request)
        
        # Update session activity
        self._update_session_activity(request)
        
        # Check session security
        security_check = self._check_session_security(request)
        if security_check:
            return security_check
        
        return None
    
    def process_response(self, request, response):
        """
        Process response to update session tracking.
        """
        # Skip if not in public schema or not admin URL
        if (connection.schema_name != get_public_schema_name() or 
            not any(request.path.startswith(url) for url in self.ADMIN_URLS)):
            return response
        
        # Track admin activity
        if hasattr(request, 'user') and self._is_authenticated_superadmin(request):
            self._track_admin_activity(request, response)
        
        return response
    
    def _is_authenticated_superadmin(self, request):
        """
        Check if user is authenticated SuperAdmin.
        """
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return False
        
        return UnifiedAuthPermissions.check_superadmin_permission(request.user)
    
    def _handle_unauthenticated_request(self, request):
        """
        Handle unauthenticated request to admin area.
        """
        # Log unauthorized access attempt
        self._log_unauthorized_attempt(request)
        
        # Redirect to login
        try:
            login_url = reverse('admin_panel:unified_login')
        except NoReverseMatch:
            # Fallback to hardcoded URL if reverse fails
            login_url = '/super-panel/login/'
        
        # Store next URL for redirect after login
        if request.path != login_url:
            request.session['next_url'] = request.path
        
        try:
            messages.warning(
                request,
                _('برای دسترسی به این بخش باید وارد شوید.')
            )
        except Exception:
            # Messages framework not available, skip message
            pass
        
        return redirect(login_url)
    
    def _update_session_activity(self, request):
        """
        Update session activity timestamp.
        """
        try:
            request.session['last_activity'] = timezone.now().isoformat()
            
            # Update session in database if exists
            session_id = request.session.get('admin_session_id')
            if session_id:
                from zargar.tenants.admin_models import SuperAdminSession
                try:
                    session = SuperAdminSession.objects.get(id=session_id)
                    session.access_time = timezone.now()
                    session.save(update_fields=['access_time'])
                except SuperAdminSession.DoesNotExist:
                    pass
        except Exception as e:
            logger.error(f"Error updating session activity: {str(e)}")
    
    def _check_session_security(self, request):
        """
        Check session security and validity.
        """
        try:
            # Check session timeout
            if self._is_session_expired(request):
                return self._handle_session_timeout(request)
            
            # Check IP address consistency
            if not self._check_ip_consistency(request):
                return self._handle_ip_mismatch(request)
            
            # Check user agent consistency
            if not self._check_user_agent_consistency(request):
                return self._handle_user_agent_mismatch(request)
            
            return None
        except Exception as e:
            logger.error(f"Error checking session security: {str(e)}")
            return None
    
    def _is_session_expired(self, request):
        """
        Check if session has expired.
        """
        try:
            last_activity_str = request.session.get('last_activity')
            if not last_activity_str:
                return True
            
            from datetime import datetime, timedelta
            last_activity = datetime.fromisoformat(last_activity_str.replace('Z', '+00:00'))
            
            # Session timeout: 2 hours of inactivity
            timeout_duration = timedelta(hours=2)
            
            return (timezone.now() - last_activity) > timeout_duration
        except Exception:
            return True
    
    def _check_ip_consistency(self, request):
        """
        Check if IP address is consistent with session.
        """
        try:
            current_ip = self._get_client_ip(request)
            session_ip = request.session.get('session_ip')
            
            if not session_ip:
                # Store IP for future checks
                request.session['session_ip'] = current_ip
                return True
            
            return current_ip == session_ip
        except Exception:
            return True  # Allow on error to prevent lockout
    
    def _check_user_agent_consistency(self, request):
        """
        Check if user agent is consistent with session.
        """
        try:
            current_ua = request.META.get('HTTP_USER_AGENT', '')
            session_ua = request.session.get('session_user_agent')
            
            if not session_ua:
                # Store user agent for future checks
                request.session['session_user_agent'] = current_ua
                return True
            
            return current_ua == session_ua
        except Exception:
            return True  # Allow on error to prevent lockout
    
    def _handle_session_timeout(self, request):
        """
        Handle session timeout.
        """
        logger.warning(f"Session timeout for user: {request.user.username}")
        
        # Log timeout event
        TenantAccessLog.log_action(
            user=request.user,
            tenant_schema='public',
            action='session_timeout',
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            request_path=request.path,
            request_method=request.method,
            success=True,
            details={
                'timeout_reason': 'inactivity',
                'timeout_timestamp': timezone.now().isoformat()
            }
        )
        
        # End session
        UnifiedSessionManager.end_admin_session(request, request.user)
        
        # Logout user
        from django.contrib.auth import logout
        logout(request)
        
        messages.warning(
            request,
            _('جلسه شما به دلیل عدم فعالیت منقضی شده است. لطفاً مجدداً وارد شوید.')
        )
        
        return redirect(reverse('admin_panel:unified_login'))
    
    def _handle_ip_mismatch(self, request):
        """
        Handle IP address mismatch.
        """
        logger.warning(f"IP mismatch for user {request.user.username}: session={request.session.get('session_ip')}, current={self._get_client_ip(request)}")
        
        # Log security event
        TenantAccessLog.log_action(
            user=request.user,
            tenant_schema='public',
            action='security_violation',
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            request_path=request.path,
            request_method=request.method,
            success=False,
            error_message='IP address mismatch detected',
            details={
                'violation_type': 'ip_mismatch',
                'session_ip': request.session.get('session_ip'),
                'current_ip': self._get_client_ip(request),
                'detection_timestamp': timezone.now().isoformat()
            }
        )
        
        # End session for security
        UnifiedSessionManager.end_admin_session(request, request.user)
        
        # Logout user
        from django.contrib.auth import logout
        logout(request)
        
        messages.error(
            request,
            _('به دلیل تشخیص فعالیت مشکوک، جلسه شما پایان یافته است. لطفاً مجدداً وارد شوید.')
        )
        
        return redirect(reverse('admin_panel:unified_login'))
    
    def _handle_user_agent_mismatch(self, request):
        """
        Handle user agent mismatch.
        """
        logger.warning(f"User agent mismatch for user {request.user.username}")
        
        # Log security event (less severe than IP mismatch)
        TenantAccessLog.log_action(
            user=request.user,
            tenant_schema='public',
            action='security_warning',
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            request_path=request.path,
            request_method=request.method,
            success=True,
            details={
                'warning_type': 'user_agent_mismatch',
                'session_user_agent': request.session.get('session_user_agent'),
                'current_user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'detection_timestamp': timezone.now().isoformat()
            }
        )
        
        # Update user agent (allow but log)
        request.session['session_user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        return None
    
    def _track_admin_activity(self, request, response):
        """
        Track admin activity for audit purposes.
        """
        try:
            # Only track significant activities
            if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
                TenantAccessLog.log_action(
                    user=request.user,
                    tenant_schema='public',
                    action='admin_action',
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    request_path=request.path,
                    request_method=request.method,
                    success=200 <= response.status_code < 400,
                    details={
                        'response_status': response.status_code,
                        'activity_timestamp': timezone.now().isoformat()
                    }
                )
        except Exception as e:
            logger.error(f"Error tracking admin activity: {str(e)}")
    
    def _log_unauthorized_attempt(self, request):
        """
        Log unauthorized access attempt.
        """
        try:
            TenantAccessLog.objects.create(
                user_type='unknown',
                user_id=0,
                username='anonymous',
                tenant_schema='public',
                action='unauthorized_access',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
                success=False,
                error_message='Unauthorized access to admin area',
                details={
                    'attempt_timestamp': timezone.now().isoformat(),
                    'user_authenticated': hasattr(request, 'user') and request.user.is_authenticated,
                    'user_type': type(request.user).__name__ if hasattr(request, 'user') else 'AnonymousUser'
                }
            )
            
            logger.warning(f"Unauthorized admin access attempt from {self._get_client_ip(request)} to {request.path}")
        except Exception as e:
            logger.error(f"Error logging unauthorized attempt: {str(e)}")
    
    def _get_client_ip(self, request):
        """
        Get client IP address.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip


class UnifiedAdminSecurityMiddleware(MiddlewareMixin):
    """
    Additional security middleware for admin area.
    """
    
    def process_request(self, request):
        """
        Apply additional security measures.
        """
        # Skip if not in public schema
        if connection.schema_name != get_public_schema_name():
            return None
        
        # Skip if not admin URL
        if not any(request.path.startswith(url) for url in ['/admin/', '/super-panel/']):
            return None
        
        # Add security headers
        self._add_security_headers(request)
        
        return None
    
    def process_response(self, request, response):
        """
        Add security headers to response.
        """
        # Skip if not admin URL
        if not any(request.path.startswith(url) for url in ['/admin/', '/super-panel/']):
            return response
        
        # Add security headers
        response['X-Frame-Options'] = 'DENY'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://unpkg.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.tailwindcss.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        
        return response
    
    def _add_security_headers(self, request):
        """
        Add security-related information to request.
        """
        # Mark request as admin request
        request.is_admin_request = True
        
        # Add security context
        request.security_context = {
            'requires_2fa': True,
            'session_timeout': 7200,  # 2 hours
            'ip_validation': True,
            'user_agent_validation': True
        }