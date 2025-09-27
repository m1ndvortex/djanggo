#!/usr/bin/env python
"""Script to check SuperAdmin users in the database."""
import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, '/app')

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zargar.settings.development')
django.setup()

from zargar.tenants.admin_models import SuperAdmin

def check_super_admins():
    """Check SuperAdmin users in the database."""
    print("Checking SuperAdmin users in database...")
    
    try:
        # Get all SuperAdmin users
        admins = SuperAdmin.objects.all()
        print(f"Total SuperAdmin users: {admins.count()}")
        
        if admins.exists():
            print("\nSuperAdmin users:")
            for admin in admins:
                print(f"- Username: {admin.username}")
                print(f"  Email: {admin.email}")
                print(f"  Active: {admin.is_active}")
                print(f"  Staff: {admin.is_staff}")
                print(f"  Superuser: {admin.is_superuser}")
                print(f"  Last Login: {admin.last_login}")
                print(f"  Date Joined: {admin.date_joined}")
                print("  ---")
        else:
            print("No SuperAdmin users found!")
            
        # Check for user 'admin' specifically
        admin_user = SuperAdmin.objects.filter(username='admin').first()
        if admin_user:
            print(f"\nFound 'admin' user: {admin_user.username}")
            print(f"Password hash starts with: {admin_user.password[:20]}...")
            # Check if password is correct
            if admin_user.check_password('admin123'):
                print("✓ Password 'admin123' is correct")
            else:
                print("✗ Password 'admin123' is incorrect")
        else:
            print("\n'admin' user not found!")
            
    except Exception as e:
        print(f"Error checking SuperAdmin users: {e}")
        import traceback
        traceback.print_exc()

def create_admin_user():
    """Create admin user if it doesn't exist."""
    try:
        admin_user = SuperAdmin.objects.filter(username='admin').first()
        if not admin_user:
            print("Creating admin user...")
            admin_user = SuperAdmin.objects.create_superuser(
                username='admin',
                email='admin@zargar.com',
                password='admin123'
            )
            print(f"✓ Created admin user: {admin_user.username}")
        else:
            print("Admin user already exists")
    except Exception as e:
        print(f"Error creating admin user: {e}")

if __name__ == '__main__':
    check_super_admins()
    
    # If no admin user found, create one
    if not SuperAdmin.objects.filter(username='admin').exists():
        create_admin_user()
        print("\n" + "="*50)
        check_super_admins()