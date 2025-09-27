#!/usr/bin/env python
"""Script to reset admin password."""
import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, '/app')

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from zargar.tenants.admin_models import SuperAdmin

def reset_admin_password():
    """Reset admin password to admin123."""
    try:
        admin_user = SuperAdmin.objects.get(username='admin')
        admin_user.set_password('admin123')
        admin_user.save()
        print(f"✓ Reset password for admin user: {admin_user.username}")
        
        # Verify the password
        if admin_user.check_password('admin123'):
            print("✓ Password verification successful!")
        else:
            print("✗ Password verification failed!")
            
    except SuperAdmin.DoesNotExist:
        print("✗ Admin user not found!")
    except Exception as e:
        print(f"✗ Error resetting password: {e}")

if __name__ == '__main__':
    reset_admin_password()