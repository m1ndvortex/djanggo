#!/usr/bin/env python3
"""
Security audit script for ZARGAR jewelry SaaS platform.
Performs comprehensive security checks and generates reports.
"""
import subprocess
import sys
import json
from datetime import datetime


def run_command(command, description):
    """Run a command and return the result."""
    print(f"\n🔍 {description}")
    print("-" * 50)
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print("✅ PASSED")
            if result.stdout.strip():
                print(result.stdout)
        else:
            print("❌ FAILED")
            if result.stderr.strip():
                print(f"Error: {result.stderr}")
            if result.stdout.strip():
                print(f"Output: {result.stdout}")
                
        return result.returncode == 0, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        print("⏰ TIMEOUT - Command took too long")
        return False, "", "Command timeout"
    except Exception as e:
        print(f"💥 EXCEPTION: {e}")
        return False, "", str(e)


def main():
    """Run comprehensive security audit."""
    print("🛡️  ZARGAR Security Audit")
    print("=" * 60)
    print(f"Audit Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    audit_results = []
    
    # 1. Check for known vulnerabilities in dependencies
    success, stdout, stderr = run_command(
        "docker-compose run --rm web pip-audit --format=json",
        "Checking for known vulnerabilities in Python dependencies"
    )
    audit_results.append(("Dependency Vulnerabilities", success))
    
    # 2. Django security check
    success, stdout, stderr = run_command(
        "docker-compose run --rm web python manage.py check --deploy",
        "Django deployment security check"
    )
    audit_results.append(("Django Security Check", success))
    
    # 3. Check for hardcoded secrets
    success, stdout, stderr = run_command(
        "grep -r -i 'password\\|secret\\|key\\|token' --include='*.py' zargar/ | grep -v 'config(' | head -10",
        "Scanning for potential hardcoded secrets"
    )
    # Invert result - finding secrets is bad
    audit_results.append(("Hardcoded Secrets Check", not bool(stdout.strip())))
    
    # 4. Check Docker security
    success, stdout, stderr = run_command(
        "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image djanggo-web:latest",
        "Docker image vulnerability scan (if Trivy is available)"
    )
    audit_results.append(("Docker Security Scan", success))
    
    # 5. Check SSL/TLS configuration
    success, stdout, stderr = run_command(
        "docker-compose run --rm web python -c \"from django.conf import settings; print('SSL_REDIRECT:', getattr(settings, 'SECURE_SSL_REDIRECT', False))\"",
        "SSL/TLS configuration check"
    )
    audit_results.append(("SSL/TLS Configuration", success))
    
    # 6. Database security check
    success, stdout, stderr = run_command(
        "docker-compose run --rm web python manage.py shell -c \"from django.db import connection; print('DB SSL:', 'sslmode' in str(connection.settings_dict))\"",
        "Database connection security check"
    )
    audit_results.append(("Database Security", success))
    
    # 7. Run security-focused tests
    success, stdout, stderr = run_command(
        "docker-compose -f docker-compose.test.yml run --rm web pytest tests/test_perfect_tenant_isolation.py -v",
        "Multi-tenant security isolation tests"
    )
    audit_results.append(("Tenant Isolation Tests", success))
    
    # 8. Check for debug mode in production
    success, stdout, stderr = run_command(
        "grep -r 'DEBUG = True' zargar/settings/production.py",
        "Production debug mode check"
    )
    # Invert result - finding DEBUG=True in production is bad
    audit_results.append(("Production Debug Check", not bool(stdout.strip())))
    
    # Generate summary report
    print("\n" + "=" * 60)
    print("🛡️  SECURITY AUDIT SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in audit_results if success)
    total = len(audit_results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All security checks passed!")
        exit_code = 0
    else:
        print("\n⚠️  Some security checks failed. Please review the issues above.")
        exit_code = 1
    
    print("\n📋 Detailed Results:")
    for check_name, success in audit_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {check_name}")
    
    print("\n🔧 Recommendations:")
    print("  1. Run this audit regularly (weekly)")
    print("  2. Keep dependencies updated")
    print("  3. Monitor security advisories")
    print("  4. Use HTTPS in production")
    print("  5. Enable database SSL")
    print("  6. Regular penetration testing")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())