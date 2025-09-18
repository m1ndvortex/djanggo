# Docker-First Development & Testing Strategy

## Core Development Philosophy

**EVERYTHING RUNS ON DOCKER** - This is a fundamental requirement for the ZARGAR jewelry SaaS platform. All development, testing, and deployment activities must be containerized.

## Docker-First Requirements

### Mandatory Docker Usage
- **ALL commands must be executed within Docker containers**
- **ALL installations must happen inside Docker containers**
- **NO local installations** of Python, Node.js, PostgreSQL, Redis, or any other dependencies
- **ALL development tools** (pytest, Django management commands, etc.) run through Docker
- **ALL database operations** performed through Docker containers
- **ALL external service integrations** tested through Docker

### Development Environment
```bash
# Correct approach - Everything through Docker
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py test
docker-compose exec web python manage.py shell

# NEVER do this - No local installations
python manage.py migrate  # ❌ FORBIDDEN
pip install package       # ❌ FORBIDDEN
npm install              # ❌ FORBIDDEN
```

### Container Architecture
- **Web Application**: Django + DRF in Docker container
- **Database**: PostgreSQL in Docker container
- **Cache**: Redis in Docker container
- **Background Tasks**: Celery workers in Docker containers
- **Web Server**: Nginx in Docker container
- **All Services**: Orchestrated via docker-compose.yml

## Testing Strategy Integration

### Mock Strategy - STRICTLY LIMITED
**ONLY mock external services that are outside our control:**
- ✅ **Gold price APIs** (Iranian market data services)
- ✅ **Payment gateways** (Iranian banking services)
- ✅ **SMS services** (Iranian SMS providers)
- ✅ **Email services** (External email providers)

### NO MOCKING for Internal Services
**NEVER mock internal components - use real Docker containers:**
- ❌ **DO NOT mock PostgreSQL** - Use real PostgreSQL container
- ❌ **DO NOT mock Redis** - Use real Redis container
- ❌ **DO NOT mock Celery** - Use real Celery worker containers
- ❌ **DO NOT mock Django ORM** - Use real database operations
- ❌ **DO NOT mock Django authentication** - Use real auth system
- ❌ **DO NOT mock django-tenants** - Use real multi-tenant database

### Testing Environment Setup
```yaml
# docker-compose.test.yml
version: '3.8'
services:
  web:
    build: .
    environment:
      - DJANGO_SETTINGS_MODULE=zargar.settings.test
    depends_on:
      - db
      - redis
      - celery
    
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=zargar_test
      - POSTGRES_USER=zargar
      - POSTGRES_PASSWORD=test_password
    
  redis:
    image: redis:7-alpine
    
  celery:
    build: .
    command: celery -A zargar worker -l info
    depends_on:
      - db
      - redis
```

### Test Execution Commands
```bash
# Unit Tests - All in Docker
docker-compose -f docker-compose.test.yml exec web pytest tests/unit/

# Integration Tests - All in Docker
docker-compose -f docker-compose.test.yml exec web pytest tests/integration/

# API Tests - All in Docker
docker-compose -f docker-compose.test.yml exec web pytest tests/api/

# Multi-tenant Tests - All in Docker
docker-compose -f docker-compose.test.yml exec web pytest tests/tenants/

# Coverage Report - All in Docker
docker-compose -f docker-compose.test.yml exec web pytest --cov=zargar --cov-report=html
```

## Development Workflow

### 1. Environment Setup
```bash
# Clone repository
git clone <repository>
cd zargar-jewelry-saas

# Build and start all services
docker-compose up --build

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Load test data
docker-compose exec web python manage.py loaddata fixtures/test_data.json
```

### 2. Daily Development
```bash
# Start development environment
docker-compose up

# Run tests
docker-compose exec web pytest

# Django shell
docker-compose exec web python manage.py shell

# Database shell
docker-compose exec db psql -U zargar -d zargar_dev

# View logs
docker-compose logs -f web
docker-compose logs -f celery
```

### 3. Database Operations
```bash
# Create migrations
docker-compose exec web python manage.py makemigrations

# Apply migrations
docker-compose exec web python manage.py migrate

# Database backup
docker-compose exec db pg_dump -U zargar zargar_dev > backup.sql

# Database restore
docker-compose exec -T db psql -U zargar zargar_dev < backup.sql
```

### 4. Testing Procedures
```bash
# Run all tests
docker-compose -f docker-compose.test.yml run --rm web pytest

# Run specific test categories
docker-compose -f docker-compose.test.yml run --rm web pytest tests/unit/
docker-compose -f docker-compose.test.yml run --rm web pytest tests/integration/
docker-compose -f docker-compose.test.yml run --rm web pytest tests/api/

# Run tests with coverage
docker-compose -f docker-compose.test.yml run --rm web pytest --cov=zargar --cov-report=term-missing

# Performance tests
docker-compose -f docker-compose.test.yml run --rm web pytest tests/performance/
```

## Comprehensive Testing Requirements

### Unit Testing (90% Coverage Minimum)
- **Framework**: pytest with Django test suite integration
- **Execution**: `docker-compose exec web pytest tests/unit/`
- **Coverage**: Minimum 90% code coverage for all business logic
- **Mocking**: ONLY external services (gold price APIs, payment gateways)

### Integration Testing
- **Database Integration**: Real PostgreSQL container, NO mocking
- **API Integration**: Full DRF endpoint testing with real authentication
- **Multi-tenant Testing**: Real django-tenants with separate schemas
- **Cache Integration**: Real Redis container testing

### User Acceptance Testing
- **Real Business Workflows**: Complete jewelry shop operations
- **Persian Localization**: Native speaker validation
- **Performance Testing**: Real-world load testing with actual data volumes

### Security Testing
- **Penetration Testing**: External security firm validation
- **GDPR Compliance**: Real data handling validation
- **Multi-tenant Security**: Real schema isolation testing

## CI/CD Pipeline Integration

### GitHub Actions Workflow
```yaml
name: ZARGAR CI/CD Pipeline
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker images
        run: docker-compose -f docker-compose.test.yml build
        
      - name: Run tests
        run: docker-compose -f docker-compose.test.yml run --rm web pytest --cov=zargar
        
      - name: Run integration tests
        run: docker-compose -f docker-compose.test.yml run --rm web pytest tests/integration/
        
      - name: Security scan
        run: docker-compose -f docker-compose.test.yml run --rm web safety check
```

## Deployment Strategy

### Production Deployment
- **Container Registry**: All images pushed to Docker registry
- **Orchestration**: Docker Compose or Kubernetes
- **Zero Downtime**: Blue-green deployment with health checks
- **Monitoring**: All services monitored through Docker containers

### Environment Management
```bash
# Development
docker-compose -f docker-compose.yml up

# Testing
docker-compose -f docker-compose.test.yml up

# Production
docker-compose -f docker-compose.prod.yml up
```

## Strict Enforcement

### What is FORBIDDEN
- ❌ Local Python installations
- ❌ Local PostgreSQL installations
- ❌ Local Redis installations
- ❌ Running Django commands outside Docker
- ❌ Mocking internal services (DB, Redis, Celery)
- ❌ Installing packages locally with pip/npm

### What is REQUIRED
- ✅ All development through Docker containers
- ✅ All testing through Docker containers
- ✅ All deployments through Docker containers
- ✅ Real database testing (no mocking)
- ✅ Real cache testing (no mocking)
- ✅ Only mock external APIs (gold prices, payments)

This Docker-first approach ensures consistency across development, testing, and production environments while maintaining the integrity of our multi-tenant Django application with real service integration testing.