# NEXORA System Architecture

## 1. Project Overview

NEXORA is a SACCO Management System supporting three user roles:
- Platform Owner
- SACCO Administrator
- SACCO Member

The application uses React, Flask and PostgreSQL.

## 2. Architecture

    Users
      |
      v
    React Frontend
      |
      | HTTP / JSON
      v
    Flask REST API
      |
      | Database queries
      v
    PostgreSQL Database

## 3. Technology Responsibilities

### React
- Displays the user interface.
- Provides role-specific dashboards and navigation.
- Collects and validates user input.
- Communicates with Flask through HTTP requests.
- Displays loading, success, empty and error states.

### Flask
- Exposes REST API endpoints.
- Handles business logic and request validation.
- Enforces authentication and authorization.
- Enforces SACCO-level data isolation.
- Reads and writes application data in PostgreSQL.

### PostgreSQL
- Stores users, SACCOs, memberships and financial records.
- Maintains relationships and database constraints.
- Provides transactional consistency for financial operations.

## 4. Security Boundaries

- Authorization must be enforced by Flask, not only by React.
- Members can access only their own records.
- SACCO Administrators are restricted to their SACCO.
- Platform Owner permissions are platform-level and must follow the agreed access policy.
- Client-supplied SACCO and member identifiers must not be trusted without server-side verification.

## 5. Financial Integrity

- Use decimal database types for monetary values.
- Use atomic database transactions for financial operations.
- Preserve historical financial records.
- Correct financial mistakes using reversal entries rather than silently editing historical transactions.

## 6. Current Foundation

- React frontend initialized.
- Flask backend initialized.
- PostgreSQL connection verified through the health endpoint.
- GET /api/health returns HTTP 200 when the backend and database are healthy.

## 7. Decisions Still Required

- Authentication method: JWT or server-side sessions.
- Final database relationships and constraints.
- Database migration strategy.
- API versioning policy.
