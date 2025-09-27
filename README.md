# ZARGAR - Persian Jewelry SaaS Platform

A comprehensive, secure, and user-friendly multi-tenant SaaS platform designed specifically for Iranian gold and jewelry businesses.

## Features

- **Multi-tenant Architecture**: Complete data isolation using django-tenants
- **Persian-native Interface**: RTL layout with Shamsi calendar support
- **Dual Theme System**: Modern light mode and cybersecurity-themed dark mode
- **Gold Installment System**: Weight-based payment calculations
- **Persian Accounting**: Complete accounting system with Iranian standards
- **Point of Sale**: Touch-optimized POS system for jewelry shops
- **Advanced Security**: 2FA, encryption, and comprehensive audit logging

## Technology Stack

- **Backend**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL with django-tenants
- **Cache**: Redis
- **Background Tasks**: Celery
- **Web Server**: Nginx
- **Containerization**: Docker & Docker Compose

## Quick Start with Docker

### Prerequisites

- Docker and Docker Compose installed
- Git

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd zargar-jewelry-saas
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Build and start services:
```bash
docker-compose up --build
```

4. Run migrations:
```bash
docker-compose exec web python manage.py migrate
```

5. Create superuser:
```bash
docker-compose exec web python manage.py createsuperuser
```

6. Access the application:
- Web interface: http://localhost:8000
- Admin panel: http://localhost:8000/admin

## Development Workflow

### Running Tests

```bash
# Run all tests
docker-compose -f docker-compose.test.yml run --rm web pytest

# Run specific test categories
docker-compose -f docker-compose.test.yml run --rm web pytest tests/test_docker_health.py

# Run with coverage
docker-compose -f docker-compose.test.yml run --rm web pytest --cov=zargar --cov-report=html
```

### Database Operations

```bash
# Create migrations
docker-compose exec web python manage.py makemigrations

# Apply migrations
docker-compose exec web python manage.py migrate

# Django shell
docker-compose exec web python manage.py shell

# Database shell
docker-compose exec db psql -U zargar -d zargar_dev
```

### Celery Operations

```bash
# View Celery workers
docker-compose logs celery

# Monitor Celery tasks
docker-compose exec celery celery -A zargar inspect active
```

## Project Structure

```
zargar-jewelry-saas/
├── zargar/                 # Main Django project
│   ├── settings/          # Environment-specific settings
│   ├── core/              # Shared functionality
│   ├── tenants/           # Multi-tenancy models
│   ├── api/               # DRF API endpoints
│   ├── jewelry/           # Jewelry inventory management
│   ├── accounting/        # Persian accounting system
│   ├── customers/         # Customer management
│   ├── pos/               # Point of sale system
│   └── reports/           # Reporting and analytics
├── tests/                 # Test suite
├── templates/             # Django templates
├── static/                # Static files
├── docker-compose.yml     # Development environment
├── docker-compose.test.yml # Testing environment
└── requirements.txt       # Python dependencies
```

## Environment Variables

Key environment variables (see `.env.example` for complete list):

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `CLOUDFLARE_R2_*`: Cloudflare R2 storage credentials
- `BACKBLAZE_B2_*`: Backblaze B2 storage credentials

## Multi-tenant Setup

The system uses django-tenants for complete data isolation:

1. Each jewelry shop gets its own subdomain
2. Separate database schemas for each tenant
3. Shared authentication and admin functionality

## Storage Configuration

The system supports dual cloud storage:

- **Cloudflare R2**: Primary storage backend
- **Backblaze B2**: Backup storage backend

## Security Features

- AES-256 encryption for data at rest
- TLS 1.3 for data in transit
- TOTP-based 2FA
- Comprehensive audit logging
- Rate limiting and suspicious activity detection

## Persian Localization

- Complete RTL interface
- Shamsi calendar integration
- Persian number formatting
- Iranian accounting terminology
- Persian fonts and typography

## Contributing

1. Follow Docker-first development approach
2. All commands must run in Docker containers
3. Maintain 90%+ test coverage
4. Follow Persian localization standards

## License

[License information]

## Support

For support and documentation, please refer to the project wiki or contact the development team.