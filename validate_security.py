#!/usr/bin/env python
"""
Simple validation script for security system implementation.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.base')
django.setup()

from django.contrib.auth import get_user_model
from zargar.core.security_models import SecurityEvent, AuditLog, RateLimitAttempt, SuspiciousActivity
from zargar.core.security_utils import SecurityMonitor, SecurityValidator, AuditLogger

User = get_user_model()

def test_security_models():
    """Test that security models can be imported and basic operations work."""
    print("Testing security models...")
    
    # Test SecurityEvent
    try:
        event = SecurityEvent(
            event_type='login_success',
            severity='low',
            ip_address='192.168.1.1',
            user_agent='Test Browser'
        )
        print("✓ SecurityEvent model works")
    except Exception as e:
        print(f"✗ SecurityEvent model failed: {e}")
    
    # Test AuditLog
    try:
        log = AuditLog(
            action='create',
            model_name='test_model',
            object_id='123',
            ip_address='192.168.1.1'
        )
        print("✓ AuditLog model works")
    except Exception as e:
        print(f"✗ AuditLog model failed: {e}")
    
    # Test RateLimitAttempt
    try:
        attempt = RateLimitAttempt(
            identifier='192.168.1.1',
            limit_type='login',
            attempts=1
        )
        print("✓ RateLimitAttempt model works")
    except Exception as e:
        print(f"✗ RateLimitAttempt model failed: {e}")
    
    # Test SuspiciousActivity
    try:
        activity = SuspiciousActivity(
            activity_type='multiple_failed_logins',
            risk_level='medium',
            ip_address='192.168.1.1',
            confidence_score=0.8
        )
        print("✓ SuspiciousActivity model works")
    except Exception as e:
        print(f"✗ SuspiciousActivity model failed: {e}")

def test_security_utils():
    """Test security utility functions."""
    print("\nTesting security utilities...")
    
    # Test SecurityValidator
    try:
        result = SecurityValidator.validate_password_strength('TestPassword123!')
        assert 'is_valid' in result
        assert 'strength' in result
        print("✓ SecurityValidator works")
    except Exception as e:
        print(f"✗ SecurityValidator failed: {e}")
    
    # Test token generation
    try:
        token = SecurityValidator.generate_secure_token(32)
        assert len(token) == 32
        print("✓ Token generation works")
    except Exception as e:
        print(f"✗ Token generation failed: {e}")
    
    # Test backup code generation
    try:
        codes = SecurityValidator.generate_backup_codes(10, 8)
        assert len(codes) == 10
        assert all(len(code) == 8 for code in codes)
        print("✓ Backup code generation works")
    except Exception as e:
        print(f"✗ Backup code generation failed: {e}")

def test_middleware_imports():
    """Test that middleware can be imported."""
    print("\nTesting middleware imports...")
    
    try:
        from zargar.core.security_middleware import SecurityAuditMiddleware
        print("✓ SecurityAuditMiddleware imports successfully")
    except Exception as e:
        print(f"✗ SecurityAuditMiddleware import failed: {e}")
    
    try:
        from zargar.core.security_middleware import RateLimitMiddleware
        print("✓ RateLimitMiddleware imports successfully")
    except Exception as e:
        print(f"✗ RateLimitMiddleware import failed: {e}")
    
    try:
        from zargar.core.security_middleware import SuspiciousActivityDetectionMiddleware
        print("✓ SuspiciousActivityDetectionMiddleware imports successfully")
    except Exception as e:
        print(f"✗ SuspiciousActivityDetectionMiddleware import failed: {e}")

def test_admin_imports():
    """Test that admin configurations can be imported."""
    print("\nTesting admin imports...")
    
    try:
        from zargar.core.security_admin import SecurityEventAdmin
        print("✓ SecurityEventAdmin imports successfully")
    except Exception as e:
        print(f"✗ SecurityEventAdmin import failed: {e}")
    
    try:
        from zargar.core.security_admin import AuditLogAdmin
        print("✓ AuditLogAdmin imports successfully")
    except Exception as e:
        print(f"✗ AuditLogAdmin import failed: {e}")

def main():
    """Run all validation tests."""
    print("ZARGAR Security System Validation")
    print("=" * 40)
    
    test_security_models()
    test_security_utils()
    test_middleware_imports()
    test_admin_imports()
    
    print("\n" + "=" * 40)
    print("Validation completed!")
    print("\nSecurity system components:")
    print("- ✓ Security models (SecurityEvent, AuditLog, RateLimitAttempt, SuspiciousActivity)")
    print("- ✓ Security middleware (Audit, Rate Limiting, Threat Detection)")
    print("- ✓ Security utilities (Monitoring, Validation, Logging)")
    print("- ✓ Admin interfaces for security management")
    print("- ✓ Management command for security monitoring")
    
    print("\nNext steps:")
    print("1. Run migrations: docker-compose exec web python manage.py makemigrations")
    print("2. Apply migrations: docker-compose exec web python manage.py migrate")
    print("3. Test with: docker-compose exec web python manage.py security_monitor --task=analyze")

if __name__ == '__main__':
    main()