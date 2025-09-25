"""
Security policy enforcement middleware for the admin panel.
"""
import json
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext as _
from .security_services import security_enforcer
from zargar.core.security_models import SecurityEvent


class SecurityPolicyMiddleware(MiddlewareMixin):
    """
    Middleware to enforce security policies across the admin panel.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Process incoming requests for security policy enforcement."""
        
        # Skip security checks for certain paths
        if self._should_skip_security_check(request):
            return None
        
        # Check rate limiting
        rate_limit_response = self._check_rate_limiting(request)
        if rate_limit_response:
            return rate_limit_response
        
        # Check session policies
        session_response = self._check_session_policies(request)
        if session_response:
            return session_response
        
        # Check authentication policies
        auth_response = self._check_authentication_policies(request)
        if auth_response:
            return auth_response
        
        return None
    
    def _should_skip_security_check(self, request):
        """Check if security checks should be skipped for this request."""
        skip_paths = [
            '/admin/login/',
            '/admin/logout/',
            '/admin/password_reset/',
            '/static/',
            '/media/',
            '/health/',
            '/api/health/',
        ]
        
        return any(request.path.startswith(path) for path in skip_paths)
    
    def _check_rate_limiting(self, request):
        """Check and enforce rate limiting policies."""
        # Get client identifier (IP address)
        client_ip = self._get_client_ip(request)
        
        # Determine rate limit type based on request
        limit_type = self._get_rate_limit_type(request)
        if not limit_type:
            return None
        
        # Check if rate limited
        is_limited, remaining, reset_time = security_enforcer.check_rate_limit(
            client_ip, limit_type, request.path
        )
        
        if is_limited:
            # Log security event
            SecurityEvent.log_event(
                event_type='api_rate_limit',
                request=request,
                severity='medium',
                details={
                    'limit_type': limit_type,
                    'client_ip': client_ip,
                    'path': request.path,
                    'reset_time': reset_time.isoformat(),
                }
            )
            
            # Return rate limit response
            if request.content_type == 'application/json' or request.path.startswith('/api/'):
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'message': _('Too many requests. Please try again later.'),
                    'retry_after': int((reset_time - timezone.now()).total_seconds()),
                }, status=429)
            else:
                return HttpResponseForbidden(
                    _('Rate limit exceeded. Please try again later.')
                )
        
        # Record the request
        security_enforcer.record_request(client_ip, limit_type, request.path)
        
        return None
    
    def _check_session_policies(self, request):
        """Check and enforce session policies."""
        if not request.user.is_authenticated:
            return None
        
        # Check session timeout
        session_timeout = security_enforcer.get_session_timeout()
        last_activity = request.session.get('last_activity')
        
        if last_activity:
            last_activity_time = timezone.datetime.fromisoformat(last_activity)
            if timezone.now() - last_activity_time > timezone.timedelta(seconds=session_timeout):
                # Session expired
                SecurityEvent.log_event(
                    event_type='logout',
                    request=request,
                    user=request.user,
                    severity='low',
                    details={'reason': 'session_timeout'}
                )
                
                logout(request)
                messages.warning(request, _('Your session has expired. Please log in again.'))
                return redirect('admin:login')
        
        # Update last activity if session should be extended
        if security_enforcer.session_service.extend_session_on_activity():
            request.session['last_activity'] = timezone.now().isoformat()
        
        # Check for sensitive actions requiring re-authentication
        if self._is_sensitive_action(request):
            reauth_time = request.session.get('last_reauth')
            if not reauth_time or (timezone.now() - timezone.datetime.fromisoformat(reauth_time)).total_seconds() > 900:  # 15 minutes
                # Require re-authentication
                request.session['pending_sensitive_action'] = {
                    'path': request.path,
                    'method': request.method,
                    'data': request.POST.dict() if request.method == 'POST' else {},
                }
                return redirect('admin:reauth_required')
        
        return None
    
    def _check_authentication_policies(self, request):
        """Check and enforce authentication policies."""
        if not request.user.is_authenticated:
            return None
        
        # Check if 2FA is required but not enabled
        if security_enforcer.requires_2fa(request.user):
            if not hasattr(request.user, 'two_factor_enabled') or not request.user.two_factor_enabled:
                # Redirect to 2FA setup
                if not request.path.startswith('/admin/2fa/'):
                    return redirect('admin:2fa_setup')
        
        # Check if account is locked
        if security_enforcer.auth_service.is_account_locked(request.user):
            logout(request)
            messages.error(request, _('Your account has been locked due to security concerns.'))
            return redirect('admin:login')
        
        return None
    
    def _get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def _get_rate_limit_type(self, request):
        """Determine the rate limit type for the request."""
        if request.path.startswith('/admin/login/'):
            return 'login'
        elif request.path.startswith('/admin/password_reset/'):
            return 'password_reset'
        elif request.path.startswith('/api/'):
            return 'api_call'
        elif 'export' in request.path:
            return 'data_export'
        elif any(keyword in request.path for keyword in ['bulk', 'batch']):
            return 'bulk_operation'
        elif request.path.startswith('/admin/search/'):
            return 'search'
        elif 'report' in request.path:
            return 'report_generation'
        
        return None
    
    def _is_sensitive_action(self, request):
        """Check if the current request is for a sensitive action."""
        sensitive_patterns = [
            '/admin/auth/user/.*?/password/',
            '/admin/auth/user/.*?/delete/',
            '/admin/security/',
            '/admin/backup/restore/',
            '/admin/tenant/.*?/delete/',
            '/admin/export/financial/',
        ]
        
        import re
        return any(re.match(pattern, request.path) for pattern in sensitive_patterns)


class PasswordPolicyMiddleware(MiddlewareMixin):
    """
    Middleware to enforce password policies.
    """
    
    def process_request(self, request):
        """Check for password policy violations."""
        if not request.user.is_authenticated:
            return None
        
        # Check if password has expired
        if security_enforcer.password_service.is_password_expired(request.user):
            # Skip check for password change pages
            if not request.path.startswith('/admin/password_change/'):
                messages.warning(
                    request, 
                    _('Your password has expired. Please change it now.')
                )
                return redirect('admin:password_change')
        
        return None


class SessionSecurityMiddleware(MiddlewareMixin):
    """
    Middleware to enhance session security.
    """
    
    def process_request(self, request):
        """Enhance session security."""
        if not request.user.is_authenticated:
            return None
        
        # Check for session hijacking indicators
        stored_ip = request.session.get('client_ip')
        current_ip = self._get_client_ip(request)
        
        if stored_ip and stored_ip != current_ip:
            # Potential session hijacking
            SecurityEvent.log_event(
                event_type='session_hijack',
                request=request,
                user=request.user,
                severity='high',
                details={
                    'stored_ip': stored_ip,
                    'current_ip': current_ip,
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                }
            )
            
            logout(request)
            messages.error(request, _('Security alert: Your session has been terminated.'))
            return redirect('admin:login')
        
        # Store client IP for future checks
        if not stored_ip:
            request.session['client_ip'] = current_ip
        
        # Check user agent consistency
        stored_ua = request.session.get('user_agent')
        current_ua = request.META.get('HTTP_USER_AGENT', '')
        
        if stored_ua and stored_ua != current_ua:
            # User agent changed - potential security issue
            SecurityEvent.log_event(
                event_type='session_anomaly',
                request=request,
                user=request.user,
                severity='medium',
                details={
                    'stored_user_agent': stored_ua,
                    'current_user_agent': current_ua,
                }
            )
        
        # Store user agent for future checks
        if not stored_ua:
            request.session['user_agent'] = current_ua
        
        return None
    
    def _get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip

class ImpersonationAuditMiddleware(MiddlewareMixin):
    """
    Middleware to audit and control user impersonation activities.
    """
    
    def process_request(self, request):
        """Process impersonation-related requests."""
        if not request.user.is_authenticated:
            return None
        
        # Check if user is currently impersonating
        if hasattr(request, 'session') and request.session.get('impersonating_user_id'):
            # Log impersonation activity
            SecurityEvent.log_event(
                event_type='impersonation_activity',
                request=request,
                user=request.user,
                severity='medium',
                details={
                    'impersonated_user_id': request.session.get('impersonating_user_id'),
                    'action': request.path,
                    'method': request.method,
                }
            )
            
            # Check impersonation time limits
            impersonation_start = request.session.get('impersonation_start_time')
            if impersonation_start:
                start_time = timezone.datetime.fromisoformat(impersonation_start)
                max_duration = timezone.timedelta(hours=2)  # 2 hour limit
                
                if timezone.now() - start_time > max_duration:
                    # End impersonation due to time limit
                    request.session.pop('impersonating_user_id', None)
                    request.session.pop('impersonation_start_time', None)
                    request.session.pop('original_user_id', None)
                    
                    messages.warning(request, _('Impersonation session expired due to time limit.'))
                    return redirect('admin_panel:dashboard')
        
        return None