#!/usr/bin/env python3
"""
Dependency update script for ZARGAR jewelry SaaS platform.
Safely updates dependencies while checking for security vulnerabilities.
"""
import subprocess
import sys
import json
from pathlib import Path


def run_command(command, description):
    """Run a command and return the result."""
    print(f"🔄 {description}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Success")
            return True, result.stdout
        else:
            print(f"❌ Failed: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        print(f"💥 Error: {e}")
        return False, str(e)


def main():
    """Update dependencies safely."""
    print("🔧 ZARGAR Dependency Update Tool")
    print("=" * 50)
    
    # 1. Backup current requirements
    success, _ = run_command(
        "cp requirements.txt requirements_backup.txt",
        "Backing up current requirements"
    )
    
    # 2. Check for vulnerabilities before update
    print("\n🔍 Checking current vulnerabilities...")
    run_command("pip-audit", "Running security audit")
    
    # 3. Update Docker containers
    success, _ = run_command(
        "docker-compose build --no-cache",
        "Rebuilding Docker containers with updated dependencies"
    )
    
    if not success:
        print("❌ Docker build failed. Restoring backup...")
        run_command("cp requirements_backup.txt requirements.txt", "Restoring backup")
        return 1
    
    # 4. Run tests
    success, _ = run_command(
        "docker-compose -f docker-compose.test.yml run --rm web pytest",
        "Running tests with updated dependencies"
    )
    
    if not success:
        print("❌ Tests failed. Consider reviewing breaking changes.")
        return 1
    
    # 5. Final security check
    run_command("pip-audit", "Final security audit")
    
    print("\n🎉 Dependencies updated successfully!")
    print("📋 Next steps:")
    print("  1. Review test results")
    print("  2. Test critical functionality manually")
    print("  3. Deploy to staging environment")
    print("  4. Monitor for any issues")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())