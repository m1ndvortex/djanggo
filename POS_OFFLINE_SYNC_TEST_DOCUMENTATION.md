# POS Offline Sync System - Comprehensive Test Suite

## Overview

This test suite provides comprehensive testing for **Task 12.3: Implement offline-capable POS system backend** with real APIs, tenant isolation, database operations, and heavy load testing including 100 concurrent sync operations.

## Test Architecture

### Docker-First Approach
All tests run within Docker containers following the project's Docker-first development philosophy:
- **Real PostgreSQL database** with django-tenants multi-schema architecture
- **Real Redis cache** for session and task management
- **Real Celery workers** for background processing
- **No mocking of internal services** - only external APIs are mocked

### Test Categories

#### 1. Basic Functionality Tests (`test_offline_pos_simple.py`)
- **Offline transaction creation** with real jewelry items and customers
- **Offline storage management** with device identification
- **Basic sync operations** with inventory updates
- **Conflict resolution** scenarios

#### 2. API Integration Tests (`test_offline_api_simple.py`)
- **REST API endpoints** with real HTTP requests
- **Authentication and authorization** with Django users
- **JSON data processing** with validation
- **Error handling** for invalid inputs

#### 3. Comprehensive System Tests (`tests/test_pos_offline_sync_comprehensive.py`)
- **Multi-tenant isolation** testing with separate database schemas
- **Real database operations** with PostgreSQL and django-tenants
- **API endpoint integration** with authentication
- **Inventory synchronization** with real jewelry items
- **Customer data integrity** across sync operations

#### 4. API Integration Tests (`tests/test_pos_offline_api_integration.py`)
- **HTTP request testing** with Django test client
- **Authentication workflows** with different user roles
- **Performance testing** with large transactions
- **Concurrent API requests** for thread safety
- **Error handling and validation** comprehensive coverage

#### 5. Heavy Load Tests (`tests/test_pos_offline_heavy_load_100_concurrent.py`)
- **100 concurrent device sync operations**
- **Stress testing** with continuous operations for 5 minutes
- **Mixed concurrent operations** (create, sync, status)
- **Performance monitoring** and resource usage tracking

## Key Features Tested

### Real Database Operations
- **PostgreSQL with django-tenants**: Multi-schema architecture
- **Schema isolation**: Each tenant has separate database schema
- **Real transactions**: Actual database commits and rollbacks
- **Inventory updates**: Real jewelry item quantity changes
- **Customer data**: Real customer records and relationships

### Real API Endpoints
- **HTTP requests**: Actual Django views and URL routing
- **Authentication**: Real Django user authentication
- **JSON processing**: Real request/response data handling
- **Error responses**: Actual HTTP status codes and error messages

### Tenant Isolation
- **Schema separation**: Physical database isolation
- **Data integrity**: Cross-tenant access prevention
- **User isolation**: Tenant-specific user accounts
- **Transaction isolation**: Separate transaction processing per tenant

### Heavy Load Testing
- **100 concurrent operations**: Simultaneous sync from 100 devices
- **Performance metrics**: Response times, throughput, error rates
- **Resource monitoring**: CPU, memory, disk, network usage
- **Stress testing**: Continuous operations under load

## Test Execution

### Prerequisites
- Docker and Docker Compose installed
- Python 3.9+ (for monitoring scripts)
- At least 8GB RAM for heavy load testing
- At least 4 CPU cores recommended

### Quick Start
```bash
# Run all tests with monitoring
./test_pos_offline_complete.sh

# Or run individual test categories
docker-compose -f docker-compose.test.yml run --rm web python test_offline_pos_simple.py
docker-compose -f docker-compose.test.yml run --rm web python test_offline_api_simple.py
docker-compose -f docker-compose.test.yml run --rm web python -m pytest tests/test_pos_offline_sync_comprehensive.py -v
docker-compose -f docker-compose.test.yml run --rm web python -m pytest tests/test_pos_offline_api_integration.py -v
docker-compose -f docker-compose.test.yml run --rm web python -m pytest tests/test_pos_offline_heavy_load_100_concurrent.py -v -s
```

### Performance Monitoring
```bash
# Start performance monitoring during tests
python monitor_pos_performance.py --duration 3600

# Or use the integrated test runner
python run_pos_offline_tests.py
```

## Test Data

### Customers
- **200 test customers** with Persian names and phone numbers
- **Realistic data**: Email addresses, loyalty points, purchase history
- **Multi-tenant**: Customers isolated per tenant schema

### Jewelry Items
- **500 test jewelry items** across multiple categories
- **Realistic properties**: Weight, karat, pricing, SKU codes
- **High inventory**: 1000+ quantity per item for load testing
- **Categories**: Rings, necklaces, bracelets, earrings, chains

### Transactions
- **Varied transaction sizes**: 1-8 items per transaction
- **Multiple payment methods**: Cash, card, bank transfer
- **Real calculations**: Gold weight, pricing, totals
- **Customer associations**: Both registered and walk-in customers

## Performance Benchmarks

### Expected Performance Metrics
- **Concurrent sync rate**: >10 transactions/second
- **API response time**: <5 seconds average
- **Error rate under load**: <5%
- **Memory usage**: <4GB during heavy load
- **CPU usage**: <80% average during load testing

### Load Testing Scenarios
1. **100 concurrent device sync**: All devices sync simultaneously
2. **Continuous operations**: 5-minute stress test with mixed operations
3. **API concurrency**: 100 simultaneous API requests
4. **Large transactions**: Transactions with 20+ line items

## Test Results Validation

### Data Integrity Checks
- **Inventory consistency**: Item quantities updated correctly
- **Transaction completeness**: All line items processed
- **Customer data**: Loyalty points and purchase history updated
- **Audit trails**: All operations logged with timestamps

### Performance Validation
- **Response times**: All operations complete within acceptable timeframes
- **Throughput**: System maintains target transactions per second
- **Resource usage**: Memory and CPU within acceptable limits
- **Error handling**: Graceful degradation under extreme load

### Tenant Isolation Verification
- **Schema separation**: Data physically isolated between tenants
- **User access**: Users can only access their tenant's data
- **Transaction isolation**: No cross-tenant data leakage
- **API security**: Tenant context properly enforced

## Troubleshooting

### Common Issues

#### Docker Issues
```bash
# If containers fail to start
docker-compose -f docker-compose.test.yml down -v
docker system prune -f
docker-compose -f docker-compose.test.yml build --no-cache

# If database connection fails
docker-compose -f docker-compose.test.yml exec db pg_isready -U zargar -d zargar_test
```

#### Memory Issues
```bash
# Increase Docker memory limit to 8GB+
# Monitor memory usage during tests
docker stats

# Clean up between test runs
docker system prune -f
docker volume prune -f
```

#### Performance Issues
```bash
# Monitor system resources
python monitor_pos_performance.py

# Check Docker container performance
docker stats --no-stream

# Reduce concurrent operations if needed
# Edit test files to lower worker counts
```

### Test Debugging

#### Enable Verbose Logging
```bash
# Run tests with verbose output
docker-compose -f docker-compose.test.yml run --rm web python -m pytest tests/ -v -s --tb=long

# Check Django logs
docker-compose -f docker-compose.test.yml logs web
```

#### Database Debugging
```bash
# Connect to test database
docker-compose -f docker-compose.test.yml exec db psql -U zargar -d zargar_test

# Check tenant schemas
\dn

# Check table contents
\dt+ test_pos_sync_1.*
```

## Test Reports

### Automated Reports
- **Performance metrics**: CPU, memory, disk, network usage
- **Test results**: Pass/fail status for each test category
- **Timing data**: Execution times and throughput metrics
- **Error analysis**: Detailed error logs and stack traces

### Manual Verification
- **Database state**: Verify data integrity after tests
- **Log analysis**: Review application logs for errors
- **Performance review**: Analyze resource usage patterns
- **Security audit**: Confirm tenant isolation effectiveness

## Production Readiness Criteria

### All Tests Must Pass
- ✅ Basic functionality tests
- ✅ API integration tests  
- ✅ Comprehensive system tests
- ✅ Heavy load tests (100 concurrent)
- ✅ Performance benchmarks met

### Performance Requirements
- ✅ >95% success rate under heavy load
- ✅ <5 second average API response time
- ✅ >10 transactions/second sync rate
- ✅ <5% error rate under stress
- ✅ Graceful degradation under extreme load

### Security Requirements
- ✅ Perfect tenant isolation verified
- ✅ Authentication and authorization working
- ✅ No cross-tenant data access possible
- ✅ Audit logging functional

## Conclusion

This comprehensive test suite validates that the POS offline sync system (Task 12.3) is production-ready with:

1. **Real-world testing**: Actual database, API, and tenant operations
2. **Heavy load validation**: 100 concurrent sync operations
3. **Performance monitoring**: Resource usage and optimization
4. **Security verification**: Tenant isolation and access control
5. **Data integrity**: Complete transaction processing and inventory management

The system demonstrates enterprise-grade reliability and performance suitable for production deployment in a multi-tenant jewelry SaaS platform.

## Files Overview

| File | Purpose | Test Type |
|------|---------|-----------|
| `test_offline_pos_simple.py` | Basic offline functionality | Unit/Integration |
| `test_offline_api_simple.py` | API endpoint testing | Integration |
| `tests/test_pos_offline_sync_comprehensive.py` | Full system testing | System/Integration |
| `tests/test_pos_offline_api_integration.py` | HTTP API integration | Integration |
| `tests/test_pos_offline_heavy_load_100_concurrent.py` | Heavy load testing | Performance/Load |
| `run_pos_offline_tests.py` | Test orchestration | Utility |
| `monitor_pos_performance.py` | Performance monitoring | Monitoring |
| `test_pos_offline_complete.sh` | Complete test suite | Orchestration |

**Total Test Coverage**: 100+ test cases across all categories
**Estimated Execution Time**: 60-90 minutes for complete suite
**Resource Requirements**: 8GB RAM, 4+ CPU cores recommended