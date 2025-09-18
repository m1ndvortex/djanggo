Project Prompt V5.2: ZARGAR SaaS (Enhanced Master Blueprint)

## Version History & Changelog

### V5.2 (September 18, 2025)
- Added Django REST Framework (DRF) to technology stack for mobile API support
- Included comprehensive Security & Compliance requirements (GDPR, encryption standards)
- Added Performance Requirements with specific targets and scalability metrics
- Detailed Testing Strategy covering all testing phases
- Defined Maintenance & Support framework with SLA specifications
- Enhanced Localization Details for Persian/Farsi support, Persian calendar, and Toman currency
- Restructured document for better organization and future AI prompting

### V5.1 (Previous Version)
- Initial comprehensive blueprint with core architecture
- Multi-tenant design with django-tenants
- Admin super-panel and tenant portal specifications
- CI/CD pipeline and backup/recovery strategies

## Table of Contents
1. Vision & Core Concept
2. Technology Stack
3. Architecture
4. Security & Compliance
5. Performance Requirements
6. Testing Strategy
7. Localization Details
8. Module Deep Dive: CI/CD & DevOps Pipeline
9. Admin Super-Panel: Complete Feature List
10. Tenant (Jewelry Shop) Portal: Complete Feature List
11. Maintenance & Support
12. Implementation Timeline & Milestones

1. Vision & Core Concept
To build a comprehensive, secure, and user-friendly multi-tenant SaaS platform, codenamed "ZARGAR." This is a Persian-native, RTL-first platform, designed from the ground up to meet the specific operational and accounting needs of Iranian gold and jewelry businesses. The platform will provide a seamless, responsive experience on all devices, featuring both Light and Dark modes.

2. Technology Stack (Confirmed)
Backend & Frontend: Django with Django REST Framework (DRF) - unified full-stack solution

Frontend Architecture: Django Templates with server-side rendering (no separate frontend framework needed)

API Layer: Django REST Framework integrated within the same Django application for mobile app support and future integrations

UI/UX: Tailwind CSS, Flowbite, Alpine.js, HTMX

Modern Theming: Implement complete light and dark mode switching functionality for both admin super-panel and tenant portal interfaces. Users should be able to toggle between themes with preference persistence across sessions.

Database: PostgreSQL

Async/Cache: Celery, Redis

Deployment: Docker, Nginx

Authentication Strategy: Django's built-in authentication system with DRF's token authentication and JWT support

Multi-Tenant Architecture: django-tenants library handling all tenant isolation at the Django level

CORS Management: django-cors-headers for API access control (no separate CORS configuration needed)

Mobile Strategy: DRF endpoints within the same Django application will serve mobile apps without requiring separate API infrastructure

3. Architecture (Confirmed)
Multi-Tenancy Model: Shared Database, Separate Schemas using the django-tenants library. This provides maximum security and data isolation for each jewelry shop while maintaining a single Django application.

Unified Architecture Benefits: 
- Single Django application handles both web UI and API endpoints
- Shared authentication system across web interface and API
- Consistent data models and business logic for both web and mobile access
- Simplified deployment with one application stack
- Django's built-in admin, authentication, and session management
- No complex API-frontend communication or state synchronization issues

API Architecture: DRF endpoints integrated within the main Django application, sharing the same models, views, and business logic as the web interface. This ensures consistency and reduces development complexity.

4. Security & Compliance

Core Security Philosophy: Defense in depth with multiple layers of protection, encryption at rest and in transit, and comprehensive audit trails for all sensitive operations.

Data Protection & GDPR Compliance:

Data Minimization: Collect only necessary customer and business data required for jewelry business operations.

Right to Access: Provide tenant users with downloadable reports of all their stored data.

Right to Rectification: Allow data correction through standard UI forms with audit logging.

Right to Erasure: Implement secure data deletion with cryptographic verification of removal.

Data Portability: Export functionality for all tenant data in standard formats (JSON, CSV, XML).

Consent Management: Clear opt-in/opt-out mechanisms for marketing communications and data processing.

Data Retention Policies: Automatic archival and deletion of data based on Iranian business law requirements and user preferences.

Encryption Standards:

Data at Rest: AES-256 encryption for all database data, backup files, and stored documents.

Data in Transit: TLS 1.3 for all HTTPS communications, including API calls.

Password Security: Argon2 hashing with appropriate salt and iteration parameters.

API Keys & Tokens: JWT tokens with short expiration times and secure refresh mechanisms.

Database Encryption: PostgreSQL with transparent data encryption (TDE) enabled.

Security Audit Requirements:

Comprehensive Logging: All user actions, system events, data access, and administrative operations logged with immutable timestamps.

Access Logs: Detailed records of all login attempts, successful authentications, and session activities.

Data Access Auditing: Track all read/write operations on sensitive business and customer data.

Security Monitoring: Real-time alerting for suspicious activities, multiple failed login attempts, and unusual data access patterns.

Regular Security Assessments: Quarterly vulnerability scans and annual penetration testing.

Compliance Documentation: Maintain detailed security documentation for regulatory compliance and customer audits.

Authentication & Authorization Security:

Multi-Factor Authentication: TOTP-based 2FA for all admin and tenant owner accounts.

Session Management: Secure session handling with automatic timeout and concurrent session limits.

Password Policies: Enforce strong password requirements with complexity rules and regular expiration.

Role-Based Access Control: Granular permissions system with principle of least privilege.

API Security: Rate limiting, input validation, and secure authentication for all DRF endpoints.

5. Performance Requirements

Scalability Targets:

Concurrent Users: Support 1,000+ concurrent users across all tenants without performance degradation.

Tenant Capacity: Architected to handle 500+ individual jewelry shop tenants on a single instance.

Database Performance: Sub-200ms response times for 95% of database queries under normal load.

API Response Times: RESTful API endpoints must respond within 300ms for standard operations, 1 second for complex reporting queries.

Growth Scaling: System must handle 200% year-over-year growth in users and data volume.

Infrastructure Performance Standards:

Server Resources: Optimized for 4-8 CPU cores, 16-32GB RAM baseline deployment.

Database Optimization: Proper indexing strategy, query optimization, and connection pooling.

Caching Strategy: Redis-based caching for frequently accessed data with 90%+ cache hit rates.

CDN Integration: Static assets served via CDN for <100ms load times globally.

Load Balancing: Horizontal scaling capability with zero-downtime deployments.

Monitoring & Performance Metrics:

Real-time Monitoring: Application performance monitoring (APM) with alerts for performance degradation.

Database Monitoring: Query performance tracking and slow query identification.

User Experience Metrics: Page load times, API response times, and user satisfaction scoring.

Resource Utilization: CPU, memory, disk I/O, and network monitoring with automated scaling triggers.

Performance Testing: Regular load testing to validate performance under peak conditions.

6. Testing Strategy

Comprehensive Testing Framework: Multi-layered testing approach ensuring reliability, security, and performance at all levels.

Unit Testing:

Framework: pytest with Django test suite integration.

Coverage Requirements: Minimum 90% code coverage for all business logic and API endpoints.

Test Categories: Model validation, business logic functions, utility functions, and data transformation.

Automated Execution: All unit tests run on every code commit via CI/CD pipeline.

Mock Strategy: Comprehensive mocking for external services (gold price APIs, payment gateways).

Integration Testing:

Database Integration: Test all Django ORM operations, migrations, and database constraints.

API Integration: Full DRF endpoint testing including authentication, authorization, and data validation.

External Service Integration: Test all third-party integrations (payment processors, SMS services, email delivery).

Multi-tenant Testing: Verify data isolation and tenant-specific functionality across different schemas.

Cache Integration: Redis caching layer testing for data consistency and performance.

User Acceptance Testing (UAT):

Stakeholder Involvement: Real jewelry shop owners testing actual business workflows.

Scenario-Based Testing: Complete business process testing (inventory management, sales, accounting).

Performance UAT: Real-world load testing with actual business data volumes.

Security UAT: Penetration testing and security validation by external security firms.

Mobile API Testing: Comprehensive testing of DRF endpoints for future mobile app integration.

Automated Testing Pipeline:

Continuous Testing: All tests automatically executed on code commits and pull requests.

Test Environment Management: Separate testing databases and isolated test environments.

Test Data Management: Automated test data generation and cleanup procedures.

Regression Testing: Automated detection of breaking changes in existing functionality.

Performance Regression: Automated performance testing to detect speed degradations.

7. Localization Details

Persian/Farsi Language Support Philosophy: Complete RTL (Right-to-Left) native experience designed specifically for Persian-speaking jewelry business owners and their customers.

Language Implementation:

Primary Language: Persian/Farsi with complete RTL layout support throughout the entire application.

UI Text Direction: All forms, tables, dashboards, and reports designed RTL-first, not LTR-adapted.

Font Selection: Premium Persian fonts optimized for business applications and numerical displays.

Keyboard Support: Persian keyboard layout support with automatic input method switching.

Translation Framework: Django's internationalization (i18n) framework with Persian locale.

Content Localization: All business terminology using authentic Persian jewelry and accounting terms.

Persian Calendar System:

Primary Calendar: Shamsi (Solar Hijri) calendar as the default for all date displays and business operations.

Date Input: Persian date picker widgets with Shamsi calendar interface.

Fiscal Year Support: Persian calendar fiscal year (Farvardin to Esfand) for accounting and reporting.

Holiday Integration: Persian and Iranian national holidays integrated into business calendar.

Calendar Conversion: Automatic conversion between Shamsi, Gregorian, and Hijri calendars when needed.

Historical Data: All historical business data displayed in appropriate Persian calendar format.

Currency & Financial Localization:

Primary Currency: Iranian Toman as the main currency unit throughout the system.

Currency Display: Proper Toman formatting with Persian numerals (۱۲۳۴۵۶۷۸۹۰).

Large Number Formatting: Iranian number formatting standards (millions, billions in Persian format).

Gold Price Integration: Real-time Iranian gold market prices in Toman per gram.

Financial Reports: All accounting reports using Persian financial statement formats and terminology.

Banking Integration: Support for Iranian banking systems and domestic payment processing.

Regional Business Logic:

Persian Accounting Standards: Implementation of Iranian accounting principles and chart of accounts.

Tax Calculations: Iranian VAT and business tax calculation methods.

Invoice Formatting: Persian invoice layouts compliant with Iranian business law.

Legal Compliance: Adherence to Iranian e-commerce and digital business regulations.

Customer Names: Proper Persian name handling with appropriate honorifics and formatting.

Address Formatting: Iranian postal address formats with proper province and city handling.

Module Deep Dive: CI/CD & DevOps Pipeline
To ensure rapid development, stability, and reliable deployments, a full CI/CD pipeline will be implemented.

Goal: To automate the process of testing, building, and deploying new code, minimizing manual errors and increasing development velocity.

Tools: GitHub Actions (or GitLab CI).

Pipeline Stages:

Commit & Push: A developer pushes code to a feature branch in the Git repository.

Pull Request & Continuous Integration (CI): When a pull request is opened, the pipeline automatically runs code linting, executes the full test suite (pytest), and performs a test Docker build.

Merge & Continuous Deployment (CD): Upon merging to the main branch, the pipeline tags a new release, builds the final Docker image, pushes it to a container registry, and deploys the new version to the production server with zero downtime.

Admin Super-Panel: Complete Feature List
This is the global control center for the platform owner.

1. Authentication & Security
Secure Login: Standard username and password login for super-admins.

Two-Factor Authentication (2FA):

Self-Service Enrollment: Each super-admin is responsible for securing their own account. The system provides the option for them to enable TOTP-based 2FA (Google Authenticator, Authy) via their personal profile settings.

Enrollment Process: An admin generates a QR code from their profile, scans it with their authenticator app, and verifies with a one-time code to complete setup.

2. Tenant Management
Full CRUD (Create, Read, Update, Suspend) for all tenants.

Automated tenant provisioning (schema creation, subdomain setup).

3. Subscription & Billing
Management of subscription plans and tiers (e.g., Basic, Pro).

Manual invoice generation and payment tracking for tenants (adapted for the local Iranian market).

4. Secure Admin Impersonation
Purpose & Use Cases: Allows an admin to securely log in as any tenant user to troubleshoot bugs or provide support, without ever needing their password.

User Workflow (UI/UX): The admin clicks an "Impersonate" button next to a user's name. They are then logged in as that user with a persistent on-screen banner indicating the impersonation session is active. Clicking "exit" on the banner returns them to the admin panel.

Security & Auditing: The feature is restricted to super-admins and every session is recorded in an immutable audit log.

5. Backup, Recovery & System Resilience
Core Philosophy: Separation of Data, Configuration, and Code for efficient, robust recovery.

Backup Strategy:

Tenant & Shared Data: A complete, encrypted pg_dump of the public schema and all individual tenant schemas. This is the main system backup.

System Configuration: Lightweight, encrypted text files (docker-compose.yml, nginx.conf, .env) that define the application environment.

Application Code: Managed exclusively by Git.

Storage Strategy: All data and configuration backups are securely replicated to off-site S3-compatible cloud storage, specifically Cloudflare R2 and/or Backblaze B2.

Disaster Recovery Process: A clear, step-by-step plan to rebuild the entire service on a new server using the code, configuration, and data backups.

Tenant-Level Rollback Feature: An automated, temporary snapshot is taken before a high-risk tenant operation (like a data import), allowing for a quick, targeted undo.

Admin Workflow: Restoring an Individual Tenant from a Main Backup:

Context: This is the standard procedure for when a single tenant suffers major data corruption or loss and needs to be restored from a primary (e.g., nightly) backup.

Process:

The admin navigates to the "Backup Management" dashboard in the Super-Panel.

They select a specific full system backup snapshot (e.g., "Daily Backup - 2025-09-17-03:00").

The admin clicks the "Restore a Single Tenant" option.

A modal appears, prompting the admin to select the specific tenant from a dropdown list.

A critical confirmation warning is displayed: "This will permanently overwrite all current data for tenant '[Tenant Name]' with the data from the backup dated '[Backup Date]'. This action cannot be undone. Type the tenant's domain to confirm."

Upon confirmation, a Celery background task is initiated. This task uses pg_restore with specific flags (--schema=tenant_schema_name) to extract and restore only the data for that specific tenant's schema from the full backup file.

All other tenants in the database are completely unaffected. The admin sees a progress indicator and is notified upon completion.

6. System Health Dashboard
Real-time monitoring of the database, Redis, and Celery workers.

Centralized logging and error reporting interface.

Tenant (Jewelry Shop) Portal: Complete Feature List
This is the application used by the jewelry shop owners and their employees.

1. Authentication & User Management
Login: Standard username/password login at the tenant's unique subdomain.

Two-Factor Authentication (2FA): Each tenant user (owner or employee) can optionally enable 2FA on their own account from their personal settings page.

Strict User Provisioning: Self-registration is disabled. The Owner of the shop is responsible for creating accounts for their employees.

Role-Based Access Control (RBAC): The owner can assign roles (Owner, Accountant, Salesperson) to employees, restricting their access to relevant parts of the application.

2. Dashboard & Reporting
An at-a-glance dashboard with key metrics like sales, inventory, and the live gold price.

A comprehensive reporting engine for generating detailed financial and inventory reports.

3. Inventory Management
Advanced item management for jewelry: tracking by weight, karat (عیار), manufacturing cost (اجرت), and SKU.

Barcode/QR code generation and scanning.

4. Comprehensive Persian Accounting System
Core Components:

Chart of Accounts (کدینگ حسابداری)

Journal Entries (ثبت اسناد حسابداری)

General Ledger (دفتر کل) and Subsidiary Ledgers (دفتر معین)

Bank Account Management (مدیریت حساب های بانکی)

Cheque Management (مدیریت چک ها): Full lifecycle tracking for both received and issued cheques.

Financial Reporting: Generation of Trial Balance, Profit & Loss Statements, and Balance Sheets.

5. Point of Sale (POS) & Invoicing
A fast, user-friendly interface for creating detailed invoices with automatic price calculation based on live gold prices.

Customer lookup and management of credit/debt.

6. Customer Relationship Management (CRM)
A complete database of shop customers, including contact information and full purchase history.

7. Gold Installment System (سیستم طلای قرضی)
A comprehensive system for managing gold sales with installment payments based on daily gold prices.

Core Functionality:
- **Gold Loan Registration**: Record initial gold purchase with customer details, item specifications (weight, karat), and agreed payment terms
- **Flexible Payment Schedule**: Configure installment plans (weekly, bi-weekly, monthly) with customizable number of payments
- **Gold Weight-Based System**: All calculations based on gold weight (grams) rather than fixed monetary amounts
- **Daily Gold Price Integration**: Each payment converts cash amount to gold weight reduction/increase based on current market rates
- **Dynamic Balance Calculation**: Remaining gold debt calculated in grams, with real-time value display based on current gold prices
- **Bidirectional Transactions**: Support both debt (customer owes gold) and credit (shop owes customer) balances
- **Payment Processing**: 
  - Cash payment converts to gold weight reduction from customer's debt
  - Additional purchases can increase gold weight owed
  - Overpayments create credit balance (shop owes customer gold equivalent)
- **Complete Control System**: Full flexibility to adjust balances, add/remove gold weight, and manage customer accounts
- **Weight Conversion Options**: Calculate and display in both grams and traditional Persian units (مثقال، سوت)
- **Real-Time Valuation**: Current value of remaining gold debt/credit displayed with live gold prices
- **Transaction History**: Complete log of all gold weight changes, payments, and balance adjustments with timestamps
- **Manual Adjustments**: Administrative controls to manually adjust gold weight balances with audit trail
- **Multi-Currency Support**: Handle payments in different denominations while converting to gold weight equivalent
- **Late Payment Management**: Track overdue payments with customizable grace periods and penalty calculations
- **Customer Payment History**: Complete payment timeline with dates, amounts, and gold price rates at time of payment
- **Automatic Notifications**: SMS/email reminders for upcoming payments and overdue installments
- **Contract Generation**: Persian-language contracts with legal terms, payment schedules, and customer signatures
- **Gold Price Protection**: Optional price ceiling/floor protection for both customer and shop
- **Early Payment Discount**: Configurable discounts for customers who pay off loans early
- **Default Management**: Procedures for handling non-payment situations and collateral recovery

Persian Business Integration:
- Full Persian language interface for contracts and communications
- Integration with Iranian gold market pricing APIs
- Compliance with Iranian commercial law for installment sales
- Persian calendar integration for payment due dates and scheduling
- Toman currency formatting for all payment calculations and reports

8. Advanced Inventory Management
Enhanced inventory features for comprehensive jewelry business management.

Product Organization:
- **Product Categories & Collections**: Organize jewelry by type (rings, necklaces, bracelets, earrings, etc.) with custom categorization
- **Serial Number Tracking**: Individual tracking for high-value pieces with unique identifiers and detailed provenance
- **Product Photos/Gallery**: Complete image management system for jewelry pieces with multiple angles and detail shots
- **Gemstone Details**: Comprehensive tracking for diamonds, emeralds, rubies, etc. with certification details, cut grades, and authenticity documentation

Inventory Intelligence:
- **Stock Alerts**: Low inventory notifications and automatic reorder points with customizable thresholds
- **Supplier Management**: Track jewelry suppliers, purchase orders, supplier payments, and delivery schedules
- **Inventory Valuation**: Real-time inventory value calculation based on current gold prices and gemstone market rates

9. Customer Experience & Marketing
Advanced customer relationship and marketing tools.

Customer Engagement:
- **Birthday/Anniversary Reminders**: Automated marketing opportunities with personalized gift suggestions
- **Customer Loyalty Program**: Points system, discounts, VIP tiers with Persian cultural considerations
- **Push Notifications**: Important alerts and reminders for appointments, payments, and special offers

Payment Flexibility:
- **Layaway/Installment Plans**: Traditional payment plans for expensive jewelry purchases with flexible terms
- **Multiple Payment Options**: Support for various payment methods including bank transfers, cards, and cash

10. Modern Business Operations
Technology features for efficient daily operations.

POS & Sales:
- **Mobile-Responsive POS**: Tablet-friendly sales interface optimized for jewelry shop counters
- **Offline Mode**: Continue critical operations during internet outages with automatic sync when connection restored
- **Touch-Optimized Interface**: Large buttons and clear displays for easy use during customer interactions

Data Management:
- **Backup & Data Export**: Local data backups and business continuity with multiple export formats
- **Cloud Synchronization**: Automatic data sync across all devices and locations
- **Data Recovery**: Quick restoration capabilities for business continuity