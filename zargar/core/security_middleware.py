"""
Security middleware for zargar project.
"""
from django.http import JsonResponse, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.urls import resolve, Resolver404
import json
import hashlib
import time
from .security_models import SecurityEvent, AuditLog, RateLimitAttempt, SuspiciousActivity
from django_tenants.utils import connection


class SecurityAuditMiddleware:
    """
    Middleware to automatically log security events and audit trails.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Sensitive endpoints that require extra logging
        self.sensitive_endpoints = {
            'login', 'logout', 'password_change', 'password_reset',
            'admin', 'api', 'export', 'import', 'backup', 'restore'
        }
        
        # Endpoints to exclude from audit logging
        self.excluded_endpoints = {
            'health', 'static', 'media', 'favicon.ico'
        }

    def __call__(self, request):
        start_time = time.time()
        
        # Skip logging for excluded endpoints
        if self._should_skip_logging(request):
            return self.get_response(request)
        
        # Log request start for sensitive endpoints
        if self._is_sensitive_endpoint(request):
            self._log_request_start(request)
        
        response = self.get_response(request)
        
        # Log request completion
        processing_time = time.time() - start_time
        self._log_request_completion(request, response, processing_time)
        
        return response
    
    def _should_skip_logging(self, request):
        """Check if this request should be skipped from audit logging."""
        path_parts = request.path.lower().split('/')
        return any(excluded in path_parts for excluded in self.excluded_endpoints)
    
    def _is_sensitive_endpoint(self, request):
        """Check if this is a sensitive endpoint requiring extra logging."""
        path_parts = request.path.lower().split('/')
        return any(sensitive in path_parts for sensitive in self.sensitive_endpoints)
    
    def _log_request_start(self, request):
        """Log the start of a sensitive request."""
        try:
            AuditLog.log_action(
                action='request_start',
                user=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
                request=request,
                details={
                    'endpoint_type': 'sensitive',
                    'content_type': request.content_type,
                    'content_length': request.META.get('CONTENT_LENGTH', 0),
                }
            )
        except Exception:
            # Don't let audit logging break the request
            pass
    
    def _log_request_completion(self, request, response, processing_time):
        """Log request completion with response details."""
        try:
            # Determine if this was a successful or failed request
            is_error = response.status_code >= 400
            
            details = {
                'status_code': response.status_code,
                'processing_time': round(processing_time, 3),
                'response_size': len(response.content) if hasattr(response, 'content') else 0,
            }
            
            # Log different actions based on response
            if is_error:
                action = 'request_error'
                details['error_type'] = self._get_error_type(response.status_code)
            else:
                action = 'request_success'
            
            AuditLog.log_action(
                action=action,
                user=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
                request=request,
                details=details
            )
            
            # Log security events for certain error codes
            if response.status_code in [401, 403, 404, 429]:
                self._log_security_event_for_error(request, response)
                
        except Exception:
            # Don't let audit logging break the request
            pass
    
    def _get_error_type(self, status_code):
        """Get error type description from status code."""
        error_types = {
            400: 'Bad Request',
            401: 'Unauthorized',
            403: 'Forbidden',
            404: 'Not Found',
            405: 'Method Not Allowed',
            429: 'Too Many Requests',
            500: 'Internal Server Error',
            502: 'Bad Gateway',
            503: 'Service Unavailable',
        }
        return error_types.get(status_code, f'HTTP {status_code}')
    
    def _log_security_event_for_error(self, request, response):
        """Log security events for certain HTTP error codes."""
        event_mapping = {
            401: 'unauthorized_access',
            403: 'unauthorized_access',
            404: 'suspicious_activity',  # Potential scanning
            429: 'api_rate_limit',
        }
        
        event_type = event_mapping.get(response.status_code)
        if event_type:
            severity = 'high' if response.status_code in [401, 403] else 'medium'
            
            SecurityEvent.log_event(
                event_type=event_type,
                request=request,
                user=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
                severity=severity,
                details={
                    'status_code': response.status_code,
                    'error_type': self._get_error_type(response.status_code),
                }
            )


class RateLimitMiddleware:
    """
    Comprehensive rate limiting middleware for API endpoints and sensitive operations.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Rate limit configurations
        self.rate_limits = {
            # Authentication endpoints
            'login': {'limit': 5, 'window': 3600, 'block_duration': 3600},  # 5 attempts per hour
            'password_reset': {'limit': 3, 'window': 3600, 'block_duration': 3600},
            '2fa_verify': {'limit': 10, 'window': 3600, 'block_duration': 1800},
            
            # API endpoints
            'api_general': {'limit': 1000, 'window': 3600, 'block_duration': 300},  # 1000 per hour
            'api_sensitive': {'limit': 100, 'window': 3600, 'block_duration': 600},  # 100 per hour
            
            # Data operations
            'data_export': {'limit': 10, 'window': 3600, 'block_duration': 1800},
            'bulk_operation': {'limit': 5, 'window': 3600, 'block_duration': 1800},
            'report_generation': {'limit': 20, 'window': 3600, 'block_duration': 900},
            
            # Search operations
            'search': {'limit': 100, 'window': 3600, 'block_duration': 300},
        }

    def __call__(self, request):
        # Determine rate limit type for this request
        limit_type = self._get_limit_type(request)
        
        if limit_type:
            # Check rate limit
            is_blocked, remaining = self._check_rate_limit(request, limit_type)
            
            if is_blocked:
                return self._create_rate_limit_response(request, limit_type)
            
            # Add rate limit headers to response
            response = self.get_response(request)
            self._add_rate_limit_headers(response, limit_type, remaining)
            return response
        
        return self.get_response(request)
    
    def _get_limit_type(self, request):
        """Determine the rate limit type for this request."""
        path = request.path.lower()
        
        # Authentication endpoints
        if 'login' in path:
            return 'login'
        elif 'password' in path and 'reset' in path:
            return 'password_reset'
        elif '2fa' in path or 'two-factor' in path:
            return '2fa_verify'
        
        # API endpoints
        elif path.startswith('/api/'):
            # Sensitive API endpoints
            if any(sensitive in path for sensitive in ['admin', 'user', 'tenant', 'backup']):
                return 'api_sensitive'
            else:
                return 'api_general'
        
        # Data operations
        elif 'export' in path:
            return 'data_export'
        elif 'bulk' in path:
            return 'bulk_operation'
        elif 'report' in path:
            return 'report_generation'
        elif 'search' in path:
            return 'search'
        
        return None
    
    def _check_rate_limit(self, request, limit_type):
        """
        Check if request should be rate limited.
        
        Returns:
            tuple: (is_blocked, remaining_requests)
        """
        identifier = self._get_rate_limit_identifier(request)
        config = self.rate_limits.get(limit_type, self.rate_limits['api_general'])
        
        # Get appropriate models and check database rate limit record
        try:
            models = self._get_security_models()
            RateLimitAttemptModel = models.get('RateLimitAttempt', RateLimitAttempt)
            
            attempt, is_blocked = RateLimitAttemptModel.record_attempt(
                identifier=identifier,
                limit_type=limit_type,
                endpoint=request.path,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={
                    'method': request.method,
                    'user_id': request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None,
                }
            )
        except Exception:
            # Fallback: allow request if rate limiting fails
            return False, 1000
        
        if is_blocked or attempt.is_currently_blocked():
            return True, 0
        
        remaining = max(0, config['limit'] - attempt.attempts)
        return False, remaining
    
    def _get_rate_limit_identifier(self, request):
        """Get unique identifier for rate limiting."""
        # Use user ID if authenticated, otherwise IP address
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"user:{request.user.id}"
        else:
            ip = self._get_client_ip(request)
            return f"ip:{ip}"
    
    def _get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def _create_rate_limit_response(self, request, limit_type):
        """Create rate limit exceeded response."""
        config = self.rate_limits.get(limit_type, self.rate_limits['api_general'])
        
        # Log security event
        SecurityEvent.log_event(
            event_type='api_rate_limit',
            request=request,
            user=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
            severity='medium',
            details={
                'limit_type': limit_type,
                'limit': config['limit'],
                'window': config['window'],
            }
        )
        
        # Return appropriate response based on request type
        if request.path.startswith('/api/') or request.content_type == 'application/json':
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': f'Too many {limit_type} requests. Please try again later.',
                'limit_type': limit_type,
                'retry_after': config.get('block_duration', 300),
            }, status=429)
        else:
            response = HttpResponse(
                f'Rate limit exceeded for {limit_type}. Please try again later.',
                status=429
            )
            response['Retry-After'] = str(config.get('block_duration', 300))
            return response
    
    def _add_rate_limit_headers(self, response, limit_type, remaining):
        """Add rate limit headers to response."""
        config = self.rate_limits.get(limit_type, self.rate_limits['api_general'])
        
        response['X-RateLimit-Limit'] = str(config['limit'])
        response['X-RateLimit-Remaining'] = str(remaining)
        response['X-RateLimit-Window'] = str(config['window'])
        
        return response


class SuspiciousActivityDetectionMiddleware:
    """
    Middleware to detect suspicious activity patterns and potential security threats.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Suspicious patterns to detect
        self.suspicious_patterns = {
            'rapid_requests': {'threshold': 50, 'window': 60},  # 50 requests in 1 minute
            'unusual_user_agent': ['bot', 'crawler', 'scanner', 'sqlmap', 'nikto'],
            'suspicious_paths': [
                'admin', 'wp-admin', 'phpmyadmin', '.env', 'config',
                'backup', 'database', 'sql', 'dump'
            ],
            'geographic_anomaly': True,  # Enable geographic anomaly detection
        }

    def __call__(self, request):
        # Skip for admin URLs in public schema to avoid database issues
        from django_tenants.utils import get_public_schema_name
        if (connection.schema_name == get_public_schema_name() and 
            (request.path.startswith('/admin/') or request.path.startswith('/super-panel/'))):
            return self.get_response(request)
        
        # Detect suspicious patterns before processing request
        self._detect_suspicious_activity(request)
        
        response = self.get_response(request)
        
        # Analyze response for additional suspicious patterns
        self._analyze_response_patterns(request, response)
        
        return response
    
    def _get_security_models(self):
        """Get the appropriate security models based on current schema."""
        try:
            # Check if we're in a tenant schema or public schema
            schema_name = connection.get_schema()
            
            if schema_name == 'public':
                # Use public security models from tenants app
                from zargar.tenants.admin_models import PublicSuspiciousActivity, PublicSecurityEvent, PublicAuditLog, PublicRateLimitAttempt
                return {
                    'SuspiciousActivity': PublicSuspiciousActivity,
                    'SecurityEvent': PublicSecurityEvent,
                    'AuditLog': PublicAuditLog,
                    'RateLimitAttempt': PublicRateLimitAttempt,
                }
            else:
                # Use tenant security models from core app
                return {
                    'SuspiciousActivity': SuspiciousActivity,
                    'SecurityEvent': SecurityEvent,
                    'AuditLog': AuditLog,
                    'RateLimitAttempt': RateLimitAttempt,
                }
        except Exception:
            # Fallback to tenant models if schema detection fails
            return {
                'SuspiciousActivity': SuspiciousActivity,
                'SecurityEvent': SecurityEvent,
                'AuditLog': AuditLog,
            }
    
    def _detect_suspicious_activity(self, request):
        """Detect various suspicious activity patterns."""
        try:
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Get appropriate security models
            models = self._get_security_models()
            SuspiciousActivityModel = models['SuspiciousActivity']
            
            # Check for rapid requests
            if self._detect_rapid_requests(ip_address):
                SuspiciousActivityModel.detect_and_create(
                    activity_type='unusual_access_pattern',
                    ip_address=ip_address,
                    user_agent=user_agent,
                    pattern_data={'pattern': 'rapid_requests'},
                    confidence_score=0.8
                )
            
            # Check for suspicious user agent
            if self._detect_suspicious_user_agent(user_agent):
                SuspiciousActivityModel.detect_and_create(
                    activity_type='suspicious_user_agent',
                    ip_address=ip_address,
                    user_agent=user_agent,
                    pattern_data={'pattern': 'suspicious_user_agent'},
                    confidence_score=0.9
                )
        except Exception as e:
            # Silently fail to avoid breaking the request
            # In production, you might want to log this error
            pass
        
        # Check for suspicious paths
        if self._detect_suspicious_path(request.path):
            SuspiciousActivity.detect_and_create(
                activity_type='data_scraping',
                ip_address=ip_address,
                user_agent=user_agent,
                pattern_data={
                    'pattern': 'suspicious_path',
                    'path': request.path
                },
                confidence_score=0.7
            )
        
        # Check for bulk data access patterns
        if self._detect_bulk_data_access(request):
            SuspiciousActivity.detect_and_create(
                activity_type='bulk_data_access',
                user=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
                ip_address=ip_address,
                user_agent=user_agent,
                pattern_data={'pattern': 'bulk_data_access'},
                confidence_score=0.6
            )
    
    def _detect_rapid_requests(self, ip_address):
        """Detect rapid request patterns from same IP."""
        cache_key = f"rapid_requests:{ip_address}"
        current_count = cache.get(cache_key, 0)
        
        # Increment counter
        cache.set(cache_key, current_count + 1, timeout=60)  # 1 minute window
        
        return current_count >= self.suspicious_patterns['rapid_requests']['threshold']
    
    def _detect_suspicious_user_agent(self, user_agent):
        """Detect suspicious user agent strings."""
        user_agent_lower = user_agent.lower()
        return any(
            suspicious in user_agent_lower 
            for suspicious in self.suspicious_patterns['unusual_user_agent']
        )
    
    def _detect_suspicious_path(self, path):
        """Detect access to suspicious paths."""
        path_lower = path.lower()
        return any(
            suspicious in path_lower 
            for suspicious in self.suspicious_patterns['suspicious_paths']
        )
    
    def _detect_bulk_data_access(self, request):
        """Detect potential bulk data access patterns."""
        # Check for API endpoints with large page sizes
        if request.path.startswith('/api/'):
            page_size = request.GET.get('page_size', request.GET.get('limit', '20'))
            try:
                if int(page_size) > 100:  # Large page size
                    return True
            except (ValueError, TypeError):
                pass
        
        # Check for export operations
        if 'export' in request.path.lower():
            return True
        
        return False
    
    def _analyze_response_patterns(self, request, response):
        """Analyze response patterns for suspicious activity."""
        # Check for potential data scraping (many 200 responses)
        if response.status_code == 200 and hasattr(response, 'content'):
            content_size = len(response.content)
            
            # Large response size might indicate data scraping
            if content_size > 1024 * 1024:  # 1MB
                ip_address = self._get_client_ip(request)
                
                SuspiciousActivity.detect_and_create(
                    activity_type='data_scraping',
                    user=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
                    ip_address=ip_address,
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    pattern_data={
                        'pattern': 'large_response',
                        'content_size': content_size,
                        'path': request.path
                    },
                    confidence_score=0.5
                )
    
    def _get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip


# Signal handlers for authentication events
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log successful user login."""
    try:
        # Get appropriate security models
        schema_name = connection.get_schema()
        
        if schema_name == 'public':
            from zargar.tenants.admin_models import PublicSecurityEvent
            SecurityEventModel = PublicSecurityEvent
        else:
            SecurityEventModel = SecurityEvent
        
        SecurityEventModel.log_event(
            event_type='login_success',
            request=request,
            user=user,
            severity='low',
            details={
                'login_method': 'standard',
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            }
        )
    except Exception:
        # Silently fail to avoid breaking login
        pass
    
    try:
        # Get appropriate audit log model
        schema_name = connection.get_schema()
        
        if schema_name == 'public':
            from zargar.tenants.admin_models import PublicAuditLog
            AuditLogModel = PublicAuditLog
        else:
            AuditLogModel = AuditLog
        
        AuditLogModel.log_action(
            action='login',
            user=user,
            request=request,
            details={
                'login_timestamp': timezone.now().isoformat(),
                'session_key': request.session.session_key,
            }
        )
    except Exception:
        # Silently fail to avoid breaking login
        pass


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout."""
    if user:
        try:
            # Get appropriate security models
            schema_name = connection.get_schema()
            
            if schema_name == 'public':
                from zargar.tenants.admin_models import PublicSecurityEvent, PublicAuditLog
                SecurityEventModel = PublicSecurityEvent
                AuditLogModel = PublicAuditLog
            else:
                SecurityEventModel = SecurityEvent
                AuditLogModel = AuditLog
            
            SecurityEventModel.log_event(
                event_type='logout',
                request=request,
                user=user,
                severity='low',
                details={
                    'logout_method': 'standard',
                }
            )
            
            AuditLogModel.log_action(
                action='logout',
                user=user,
                request=request,
                details={
                    'logout_timestamp': timezone.now().isoformat(),
                }
            )
        except Exception:
            # Silently fail to avoid breaking logout
            pass


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    """Log failed login attempt."""
    username = credentials.get('username', '')
    
    try:
        # Get appropriate security models
        schema_name = connection.get_schema()
        
        if schema_name == 'public':
            from zargar.tenants.admin_models import PublicSecurityEvent
            SecurityEventModel = PublicSecurityEvent
        else:
            SecurityEventModel = SecurityEvent
        
        SecurityEventModel.log_event(
            event_type='login_failed',
            request=request,
            username_attempted=username,
            severity='medium',
            details={
                'attempted_username': username,
                'failure_reason': 'invalid_credentials',
            }
        )
    except Exception:
        # Silently fail to avoid breaking login process
        pass
    
    # Check for brute force patterns
    ip_address = SecurityEvent._get_client_ip(request)
    cache_key = f"failed_logins:{ip_address}"
    failed_count = cache.get(cache_key, 0) + 1
    cache.set(cache_key, failed_count, timeout=3600)  # 1 hour window
    
    if failed_count >= 5:  # 5 failed attempts
        SecurityEvent.log_event(
            event_type='brute_force_attempt',
            request=request,
            username_attempted=username,
            severity='high',
            details={
                'failed_attempts': failed_count,
                'time_window': '1 hour',
                'attempted_username': username,
            }
        )
        
        # Create suspicious activity record
        SuspiciousActivity.detect_and_create(
            activity_type='multiple_failed_logins',
            ip_address=ip_address,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            pattern_data={
                'failed_attempts': failed_count,
                'attempted_username': username,
            },
            confidence_score=0.9
        )