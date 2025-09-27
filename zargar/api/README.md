# ZARGAR Jewelry SaaS API Documentation

## Overview

The ZARGAR API provides comprehensive REST endpoints for managing jewelry inventory, customers, sales, and POS transactions with full tenant isolation and Persian/RTL support.

## Authentication

### JWT Token Authentication

All API endpoints require authentication using JWT tokens with tenant context.

#### Obtain Token
```http
POST /api/auth/token/
Content-Type: application/json

{
    "username": "your_username",
    "password": "your_password"
}
```

**Response:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": 1,
        "username": "owner",
        "role": "owner",
        "full_persian_name": "مالک جواهرفروشی"
    }
}
```

#### Refresh Token
```http
POST /api/auth/token/refresh/
Content-Type: application/json

{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### Using Token
Include the access token in the Authorization header:
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## API Endpoints

### Jewelry Items

#### List Jewelry Items
```http
GET /api/jewelry-items/
```

**Query Parameters:**
- `search`: Search in name, SKU, barcode, description
- `category`: Filter by category ID
- `status`: Filter by status (in_stock, sold, reserved, repair, consignment)
- `karat_min`, `karat_max`: Filter by karat range
- `weight_min`, `weight_max`: Filter by weight range (grams)
- `price_min`, `price_max`: Filter by price range (Toman)
- `low_stock`: Boolean filter for low stock items
- `has_gemstones`: Boolean filter for items with gemstones
- `ordering`: Sort by name, created_at, weight_grams, selling_price, status

**Response:**
```json
{
    "count": 25,
    "next": "http://shop.zargar.com/api/jewelry-items/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "name": "Gold Ring 18K",
            "sku": "RING001",
            "category_name": "انگشتر",
            "weight_grams": "5.500",
            "karat": 18,
            "selling_price": "2500000.00",
            "status": "in_stock",
            "quantity": 5,
            "is_low_stock": false,
            "primary_photo": "https://shop.zargar.com/media/jewelry_photos/ring001.jpg",
            "total_value": "2800000.00",
            "created_at": "2024-01-15T10:30:00Z"
        }
    ]
}
```

#### Create Jewelry Item
```http
POST /api/jewelry-items/
Content-Type: application/json

{
    "name": "Diamond Necklace",
    "sku": "NECK001",
    "category": 2,
    "weight_grams": "15.750",
    "karat": 18,
    "manufacturing_cost": "1500000",
    "selling_price": "5000000",
    "quantity": 1,
    "minimum_stock": 1,
    "gemstone_ids": [1, 2]
}
```

**Permissions:** Owner only

#### Get Jewelry Item Details
```http
GET /api/jewelry-items/{id}/
```

#### Update Jewelry Item
```http
PATCH /api/jewelry-items/{id}/
Content-Type: application/json

{
    "selling_price": "2800000",
    "quantity": 3
}
```

**Permissions:** Owner only

#### Delete Jewelry Item
```http
DELETE /api/jewelry-items/{id}/
```

**Permissions:** Owner only

#### Custom Actions

##### Get Low Stock Items
```http
GET /api/jewelry-items/low_stock/
```

##### Filter by Category
```http
GET /api/jewelry-items/by_category/?category_id=1
```

##### Update Gold Value
```http
POST /api/jewelry-items/{id}/update_gold_value/
Content-Type: application/json

{
    "gold_price_per_gram": "1250000"
}
```

##### Generate Barcode
```http
POST /api/jewelry-items/{id}/generate_barcode/
```

### Categories

#### List Categories
```http
GET /api/categories/
```

#### Create Category
```http
POST /api/categories/
Content-Type: application/json

{
    "name": "Bracelets",
    "name_persian": "دستبند",
    "description": "Gold and silver bracelets"
}
```

**Permissions:** Owner only

### Customers

#### List Customers
```http
GET /api/customers/
```

**Query Parameters:**
- `search`: Search in names and phone number
- `customer_type`: individual, business, vip
- `is_vip`: Boolean filter for VIP customers
- `city`, `province`: Filter by location
- `loyalty_points_min`, `loyalty_points_max`: Filter by loyalty points
- `birth_month`: Filter by birth month (1-12)

#### Create Customer
```http
POST /api/customers/
Content-Type: application/json

{
    "first_name": "Ahmad",
    "last_name": "Rezaei",
    "persian_first_name": "احمد",
    "persian_last_name": "رضایی",
    "phone_number": "09123456789",
    "email": "ahmad@example.com",
    "address": "تهران، خیابان ولیعصر",
    "birth_date_shamsi": "1370/05/15"
}
```

#### Customer Actions

##### Get VIP Customers
```http
GET /api/customers/vip_customers/
```

##### Get Birthday Customers (Today)
```http
GET /api/customers/birthday_today/
```

##### Add Loyalty Points
```http
POST /api/customers/{id}/add_loyalty_points/
Content-Type: application/json

{
    "points": 100,
    "reason": "Purchase bonus"
}
```

##### Redeem Loyalty Points
```http
POST /api/customers/{id}/redeem_loyalty_points/
Content-Type: application/json

{
    "points": 50,
    "reason": "Discount applied"
}
```

### Suppliers

#### List Suppliers
```http
GET /api/suppliers/
```

**Permissions:** Owner, Accountant

#### Create Supplier
```http
POST /api/suppliers/
Content-Type: application/json

{
    "name": "Gold Supplier Co.",
    "persian_name": "شرکت تامین طلا",
    "supplier_type": "manufacturer",
    "contact_person": "Mr. Ahmadi",
    "phone_number": "02112345678",
    "email": "info@goldsupplier.com"
}
```

**Permissions:** Owner, Accountant

### POS Transactions

#### List POS Transactions
```http
GET /api/pos-transactions/
```

**Query Parameters:**
- `transaction_number`: Filter by transaction number
- `customer`: Filter by customer ID
- `customer_name`: Search in customer names
- `payment_method`: cash, card, bank_transfer, cheque, gold_exchange, mixed
- `transaction_type`: sale, return, exchange, layaway, installment
- `status`: pending, completed, cancelled, refunded, offline_pending
- `amount_min`, `amount_max`: Filter by amount range
- `date_from`, `date_to`: Filter by date range
- `is_offline`: Boolean filter for offline transactions

#### Create POS Transaction
```http
POST /api/pos-transactions/
Content-Type: application/json

{
    "customer": 1,
    "transaction_type": "sale",
    "payment_method": "cash",
    "amount_paid": "2500000",
    "gold_price_18k_at_transaction": "1250000",
    "line_items": [
        {
            "jewelry_item": 1,
            "item_name": "Gold Ring",
            "quantity": 1,
            "unit_price": "2500000",
            "gold_weight_grams": "5.500",
            "gold_karat": 18
        }
    ]
}
```

#### Transaction Actions

##### Get Today's Transactions
```http
GET /api/pos-transactions/today_transactions/
```

##### Get Monthly Summary
```http
GET /api/pos-transactions/monthly_transactions/
```

##### Complete Transaction
```http
POST /api/pos-transactions/{id}/complete_transaction/
Content-Type: application/json

{
    "payment_method": "cash",
    "amount_paid": "2500000"
}
```

## Rate Limiting

The API implements tenant-aware rate limiting:

- **Tenant API**: 500 requests/hour
- **Burst Limit**: 60 requests/minute
- **POS API**: 1000 requests/hour (higher for sales operations)
- **Accounting API**: 300 requests/hour
- **Anonymous**: 100 requests/hour

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 500
X-RateLimit-Remaining: 487
X-RateLimit-Reset: 1640995200
```

## Error Handling

### Standard Error Response
```json
{
    "error": "Validation failed",
    "details": {
        "sku": ["SKU must be unique."],
        "weight_grams": ["Weight must be positive."]
    }
}
```

### HTTP Status Codes
- `200 OK`: Successful GET, PATCH
- `201 Created`: Successful POST
- `204 No Content`: Successful DELETE
- `400 Bad Request`: Validation errors
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Permission denied
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## Permissions

### Role-Based Access Control

#### Owner
- Full access to all endpoints
- Can create, update, delete all resources
- Can manage users and suppliers

#### Accountant
- Read/write access to customers, suppliers
- Read access to jewelry items and transactions
- Cannot modify jewelry inventory

#### Salesperson
- Read/write access to customers and POS transactions
- Read access to jewelry items
- Cannot access suppliers or modify inventory

### Tenant Isolation

All API endpoints automatically filter data by tenant context:
- Users can only access data from their own tenant
- Cross-tenant data access is prevented at the database level
- JWT tokens include tenant context for validation

## CORS Configuration

The API supports cross-origin requests with tenant-aware CORS settings:

```javascript
// Allowed origins include tenant subdomains
const allowedOrigins = [
    'https://shop1.zargar.com',
    'https://shop2.zargar.com',
    'http://localhost:3000' // Development
];

// Custom headers supported
const customHeaders = [
    'X-Tenant-Schema',
    'X-API-Version',
    'X-Client-Type',
    'X-Device-ID'
];
```

## Persian/RTL Support

### Number Formatting
All numeric values support Persian digit display:
```json
{
    "price_display": "۲٬۵۰۰٬۰۰۰ تومان",
    "weight_display": "۵٫۵ گرم",
    "quantity_display": "۳ عدد"
}
```

### Date Formatting
Dates are provided in both Gregorian and Shamsi formats:
```json
{
    "created_at": "2024-01-15T10:30:00Z",
    "created_at_shamsi": "۱۴۰۲/۱۰/۲۵",
    "shamsi_display": "بیست و پنجم دی ماه ۱۴۰۲"
}
```

### Search and Filtering
Search supports both English and Persian text:
```http
GET /api/customers/?search=احمد
GET /api/customers/?search=Ahmad
```

## Mobile App Integration

The API is designed for mobile app integration:

### Offline Support
- POS transactions can be created offline
- Automatic sync when connection restored
- Conflict resolution for offline data

### Touch-Optimized Endpoints
- Simplified response formats for mobile
- Optimized queries for performance
- Reduced payload sizes

### Device Management
```http
X-Device-ID: mobile-app-12345
X-Client-Type: ios-app
```

## Development and Testing

### API Testing
Use the provided test suite:
```bash
docker-compose exec web python manage.py test zargar.api.tests
```

### API Documentation
Interactive API documentation available at:
- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`

### Example Client Code

#### JavaScript/Fetch
```javascript
const response = await fetch('https://shop.zargar.com/api/jewelry-items/', {
    headers: {
        'Authorization': 'Bearer ' + accessToken,
        'Content-Type': 'application/json'
    }
});
const data = await response.json();
```

#### Python/Requests
```python
import requests

headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
}

response = requests.get(
    'https://shop.zargar.com/api/jewelry-items/',
    headers=headers
)
data = response.json()
```

#### cURL
```bash
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     https://shop.zargar.com/api/jewelry-items/
```

## Security Considerations

### Authentication Security
- JWT tokens include tenant context
- Tokens expire after 1 hour (configurable)
- Refresh tokens rotate on use
- Rate limiting prevents brute force attacks

### Data Security
- All data is tenant-isolated at database level
- HTTPS required in production
- Input validation on all endpoints
- SQL injection prevention through ORM

### Audit Logging
All API actions are logged with:
- User identification
- Tenant context
- Action performed
- Timestamp
- IP address

This comprehensive API provides all the functionality needed for a modern jewelry management system with full Persian/RTL support and enterprise-grade security.