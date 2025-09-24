"""
Management command to set the base domain for the ZARGAR platform.
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import os
from pathlib import Path


class Command(BaseCommand):
    help = 'Set the base domain for tenant subdomains'

    def add_arguments(self, parser):
        parser.add_argument(
            'domain',
            type=str,
            help='The base domain to use (e.g., zargar.com, mycompany.com)'
        )
        parser.add_argument(
            '--protocol',
            type=str,
            default='https',
            choices=['http', 'https'],
            help='Protocol to use for tenant URLs (default: https)'
        )
        parser.add_argument(
            '--separator',
            type=str,
            default='.',
            help='Separator between subdomain and base domain (default: .)'
        )
        parser.add_argument(
            '--env-file',
            type=str,
            default='.env',
            help='Path to environment file to update (default: .env)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes'
        )

    def handle(self, *args, **options):
        domain = options['domain']
        protocol = options['protocol']
        separator = options['separator']
        env_file = options['env_file']
        dry_run = options['dry_run']

        # Validate domain format
        if not self.is_valid_domain(domain):
            raise CommandError(f'Invalid domain format: {domain}')

        # Check if env file exists
        env_path = Path(env_file)
        if not env_path.exists():
            if not dry_run:
                # Create env file if it doesn't exist
                env_path.touch()
                self.stdout.write(
                    self.style.WARNING(f'Created new environment file: {env_file}')
                )

        # Read current env file
        env_content = {}
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_content[key.strip()] = value.strip()

        # Update domain settings
        env_content['TENANT_BASE_DOMAIN'] = domain
        env_content['TENANT_DOMAIN_PROTOCOL'] = protocol
        env_content['TENANT_SUBDOMAIN_SEPARATOR'] = separator

        # Show changes
        self.stdout.write(self.style.SUCCESS('Domain Configuration Changes:'))
        self.stdout.write(f'  Base Domain: {domain}')
        self.stdout.write(f'  Protocol: {protocol}')
        self.stdout.write(f'  Separator: {separator}')
        self.stdout.write(f'  Example tenant URL: {protocol}://shop1{separator}{domain}')

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN: No changes were made. Remove --dry-run to apply changes.')
            )
            return

        # Write updated env file
        with open(env_path, 'w') as f:
            for key, value in env_content.items():
                f.write(f'{key}={value}\n')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated domain configuration in {env_file}')
        )
        self.stdout.write(
            self.style.WARNING('Please restart your Django application for changes to take effect.')
        )

        # Update allowed hosts if needed
        self.update_allowed_hosts(domain, env_content, env_path)

    def is_valid_domain(self, domain):
        """
        Basic domain validation.
        """
        import re
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return re.match(pattern, domain) is not None

    def update_allowed_hosts(self, domain, env_content, env_path):
        """
        Update ALLOWED_HOSTS to include the new domain.
        """
        current_hosts = env_content.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0')
        hosts_list = [host.strip() for host in current_hosts.split(',')]
        
        # Add base domain and wildcard subdomain
        new_hosts = [domain, f'*.{domain}']
        
        for host in new_hosts:
            if host not in hosts_list:
                hosts_list.append(host)

        # Update ALLOWED_HOSTS
        env_content['ALLOWED_HOSTS'] = ','.join(hosts_list)

        # Write updated env file
        with open(env_path, 'w') as f:
            for key, value in env_content.items():
                f.write(f'{key}={value}\n')

        self.stdout.write(
            self.style.SUCCESS(f'Updated ALLOWED_HOSTS to include: {", ".join(new_hosts)}')
        )