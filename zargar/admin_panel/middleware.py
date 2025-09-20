"""
Middleware for admin panel impersonation audit logging.
"""
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.urls import resolve
from django.contrib.auth import get_user_model
from django_tenants.utils import get_tenant_model
import logging
import json

from .models import ImpersonationSession
from .hijack_permissions import get_client_ip

logger = logging.getLogger('hijack_audit')
User = get_user_model()
Tenant = get_tenant_model()


class ImpersonationAuditMiddleware(MiddlewareMixin):
    """
    Middleware to track and audit all impersonation activities.
    
    This middleware:
    1. Detects when impersonation starts and ends
    2. Logs all actions performed during impersonation
    3. Tracks page visits during impersonation
    4. Monitors for suspicious activity
    5. Automatically expires long-running sessions
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Process incoming request to track impersonation activity."""
        # Check if user is being hijacked
        if hasattr(request, 'user') and request.user.is_authenticated:
            hijack_history = getattr(request.session, 'hijack_history', [])
            
            if hijack_history:
                # User is being impersonated
                self._handle_impersonation_request(request, hijack_history)
            else:
                # Check if this is the end of an impersonation session
                self._check_impersonation_end(request)
    
    def process_response(self, request, response):
        """Process response to log page visits and actions."""
        if hasattr(request, 'user') and request.user.is_authenticated:
            hijack_history = getattr(request.session, 'hijack_history', [])
            
            if hijack_history:
                self._log_page_visit(request, response)
                self._log_actions(request, response)
        
        return response
    
    def _handle_impersonation_request(self, request, hijack_history):
        """Handle request during active impersonation."""
        try:
            # Get the current impersonation session
            session = self._get_or_create_impersonation_session(request, hijack_history)
            
            if session:
                # Update session activity
                self._update_session_activity(session, request)
                
                # Check for suspicious activity
                self._check_suspicious_activity(session, request)
                
                # Store session in request for other middleware/views
                request.impersonation_session = session
        
        except Exception as e:
            logger.error(f"Error handling impersonation request: {str(e)}")
    
    def _get_or_create_impersonation_session(self, request, hijack_history):
        """Get existing or create new impersonation session."""
        try:
            # Get admin and target user info from hijack history
            if not hijack_history:
                return None
            
            # hijack_history contains the original user info
            admin_user_id = hijack_history[0]  # Original user ID
            target_user = request.user  # Current impersonated user
            
            # Get tenant information
            tenant = getattr(request, 'tenant', None)
            tenant_schema = tenant.schema_name if tenant else 'public'
            tenant_domain = tenant.domain_url if tenant else 'admin'
            
            # Check if session already exists
            session_id = request.session.get('impersonation_session_id')
            if session_id:
                try:
                    session = ImpersonationSession.objects.get(session_id=session_id)
                    if session.is_active:
                        return session
                except ImpersonationSession.DoesNotExist:
                    pass
            
            # Create new session
            session = ImpersonationSession.objects.create(
                admin_user_id=admin_user_id,
                admin_username=self._get_username_by_id(admin_user_id),
                target_user_id=target_user.id,
                target_username=target_user.username,
                tenant_schema=tenant_schema,
                tenant_domain=tenant_domain,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                status='active'
            )
            
            # Store session ID in Django session
            request.session['impersonation_session_id'] = str(session.session_id)
            
            logger.info(f"Created impersonation session: {session.session_id}")
            return session
        
        except Exception as e:
            logger.error(f"Error creating impersonation session: {str(e)}")
            return None
    
    def _update_session_activity(self, session, request):
        """Update session with current activity."""
        try:
            # Check if session has expired
            if session.is_expired:
                session.terminate_session('timeout')
                logger.warning(f"Impersonation session {session.session_id} expired and terminated")
                return
            
            # Update last activity (this is implicit through the request)
            # We don't need to save on every request to avoid performance issues
            
        except Exception as e:
            logger.error(f"Error updating session activity: {str(e)}")
    
    def _check_suspicious_activity(self, session, request):
        """Check for suspicious activity during impersonation."""
        try:
            suspicious_indicators = []
            
            # Check for rapid page changes (potential automation)
            if len(session.pages_visited) > 50:  # More than 50 pages in one session
                suspicious_indicators.append("Excessive page visits")
            
            # Check for unusual user agent changes
            current_user_agent = request.META.get('HTTP_USER_AGENT', '')
            if current_user_agent != session.user_agent:
                suspicious_indicators.append("User agent changed during session")
            
            # Check for IP address changes
            current_ip = get_client_ip(request)
            if current_ip != session.ip_address:
                suspicious_indicators.append("IP address changed during session")
            
            # Check session duration (flag if longer than 2 hours)
            if session.duration.total_seconds() > 7200:  # 2 hours
                suspicious_indicators.append("Session duration exceeds 2 hours")
            
            # Flag session if suspicious indicators found
            if suspicious_indicators and not session.is_suspicious:
                reason = "; ".join(suspicious_indicators)
                session.flag_as_suspicious(reason)
                logger.warning(f"Impersonation session {session.session_id} flagged as suspicious: {reason}")
        
        except Exception as e:
            logger.error(f"Error checking suspicious activity: {str(e)}")
    
    def _log_page_visit(self, request, response):
        """Log page visit during impersonation."""
        try:
            session_id = request.session.get('impersonation_session_id')
            if not session_id:
                return
            
            session = ImpersonationSession.objects.get(session_id=session_id)
            
            # Get page information
            url = request.get_full_path()
            title = self._extract_page_title(response)
            
            # Avoid logging duplicate consecutive visits to the same page
            if session.pages_visited:
                last_visit = session.pages_visited[-1]
                if last_visit.get('url') == url:
                    return
            
            session.add_page_visit(url, title)
        
        except Exception as e:
            logger.error(f"Error logging page visit: {str(e)}")
    
    def _log_actions(self, request, response):
        """Log actions performed during impersonation."""
        try:
            # Only log POST, PUT, PATCH, DELETE requests (actions that modify data)
            if request.method not in ['POST', 'PUT', 'PATCH', 'DELETE']:
                return
            
            session_id = request.session.get('impersonation_session_id')
            if not session_id:
                return
            
            session = ImpersonationSession.objects.get(session_id=session_id)
            
            # Determine action type based on URL and method
            action_type = self._determine_action_type(request)
            description = self._generate_action_description(request, response)
            
            session.add_action(action_type, description, request.get_full_path())
            
            logger.info(f"Action logged for session {session.session_id}: {action_type} - {description}")
        
        except Exception as e:
            logger.error(f"Error logging action: {str(e)}")
    
    def _check_impersonation_end(self, request):
        """Check if impersonation session has ended."""
        try:
            session_id = request.session.get('impersonation_session_id')
            if session_id:
                # Impersonation has ended, close the session
                try:
                    session = ImpersonationSession.objects.get(session_id=session_id)
                    if session.is_active:
                        session.end_session('user_logout')
                        logger.info(f"Impersonation session {session.session_id} ended")
                except ImpersonationSession.DoesNotExist:
                    pass
                
                # Remove session ID from Django session
                del request.session['impersonation_session_id']
        
        except Exception as e:
            logger.error(f"Error checking impersonation end: {str(e)}")
    
    def _get_username_by_id(self, user_id):
        """Get username by user ID (handles both SuperAdmin and User models)."""
        try:
            # Try SuperAdmin first (from public schema)
            from zargar.tenants.admin_models import SuperAdmin
            try:
                admin = SuperAdmin.objects.get(id=user_id)
                return admin.username
            except SuperAdmin.DoesNotExist:
                pass
            
            # Try regular User model
            try:
                user = User.objects.get(id=user_id)
                return user.username
            except User.DoesNotExist:
                pass
            
            return f"Unknown User (ID: {user_id})"
        
        except Exception:
            return f"Unknown User (ID: {user_id})"
    
    def _extract_page_title(self, response):
        """Extract page title from response content."""
        try:
            if response.get('Content-Type', '').startswith('text/html'):
                content = response.content.decode('utf-8', errors='ignore')
                
                # Simple title extraction
                start = content.find('<title>')
                if start != -1:
                    start += 7  # len('<title>')
                    end = content.find('</title>', start)
                    if end != -1:
                        return content[start:end].strip()
            
            return None
        
        except Exception:
            return None
    
    def _determine_action_type(self, request):
        """Determine the type of action based on request."""
        try:
            url_name = resolve(request.path_info).url_name
            method = request.method.lower()
            
            # Map URL patterns to action types
            action_mapping = {
                'create': 'create',
                'add': 'create',
                'edit': 'update',
                'update': 'update',
                'delete': 'delete',
                'remove': 'delete',
                'login': 'authentication',
                'logout': 'authentication',
                'password': 'security',
                'settings': 'configuration',
            }
            
            # Check URL name for action type
            if url_name:
                for pattern, action in action_mapping.items():
                    if pattern in url_name.lower():
                        return action
            
            # Fallback to HTTP method
            method_mapping = {
                'post': 'create',
                'put': 'update',
                'patch': 'update',
                'delete': 'delete',
            }
            
            return method_mapping.get(method, 'unknown')
        
        except Exception:
            return 'unknown'
    
    def _generate_action_description(self, request, response):
        """Generate human-readable description of the action."""
        try:
            method = request.method
            path = request.path_info
            
            # Get form data for POST requests
            form_data = {}
            if method == 'POST' and request.POST:
                # Only log non-sensitive fields
                sensitive_fields = ['password', 'token', 'secret', 'key']
                for key, value in request.POST.items():
                    if not any(sensitive in key.lower() for sensitive in sensitive_fields):
                        form_data[key] = value
            
            description = f"{method} request to {path}"
            
            if form_data:
                description += f" with data: {json.dumps(form_data, default=str)[:200]}"
            
            # Add response status
            if hasattr(response, 'status_code'):
                description += f" (Status: {response.status_code})"
            
            return description
        
        except Exception:
            return f"{request.method} request to {request.path_info}"


class ImpersonationCleanupMiddleware(MiddlewareMixin):
    """
    Middleware to cleanup expired impersonation sessions.
    This runs periodically to maintain database hygiene.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.cleanup_counter = 0
        super().__init__(get_response)
    
    def process_request(self, request):
        """Periodically cleanup expired sessions."""
        self.cleanup_counter += 1
        
        # Run cleanup every 100 requests to avoid performance impact
        if self.cleanup_counter >= 100:
            self.cleanup_counter = 0
            self._cleanup_expired_sessions()
    
    def _cleanup_expired_sessions(self):
        """Cleanup expired impersonation sessions."""
        try:
            count = ImpersonationSession.objects.cleanup_expired_sessions()
            if count > 0:
                logger.info(f"Cleaned up {count} expired impersonation sessions")
        
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {str(e)}")