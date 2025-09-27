"""
Management command to initialize RBAC system with default permissions and roles.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from zargar.admin_panel.services import RBACService


class Command(BaseCommand):
    help = 'Initialize RBAC system with default permissions and roles'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of default permissions and roles',
        )
        parser.add_argument(
            '--permissions-only',
            action='store_true',
            help='Only create default permissions, skip roles',
        )
        parser.add_argument(
            '--roles-only',
            action='store_true',
            help='Only create default roles, skip permissions',
        )
    
    def handle(self, *args, **options):
        """Handle the command execution."""
        try:
            with transaction.atomic():
                permissions_created = 0
                roles_created = 0
                
                # Create default permissions
                if not options['roles_only']:
                    self.stdout.write('Creating default permissions...')
                    permissions_created = RBACService.create_default_permissions()
                    self.stdout.write(
                        self.style.SUCCESS(f'Created {permissions_created} default permissions')
                    )
                
                # Create default roles
                if not options['permissions_only']:
                    self.stdout.write('Creating default roles...')
                    roles_created = RBACService.create_default_roles()
                    self.stdout.write(
                        self.style.SUCCESS(f'Created {roles_created} default roles')
                    )
                
                # Summary
                if permissions_created > 0 or roles_created > 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'RBAC initialization complete! '
                            f'Permissions: {permissions_created}, Roles: {roles_created}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING('No new permissions or roles were created.')
                    )
                
        except Exception as e:
            raise CommandError(f'Error initializing RBAC system: {e}')