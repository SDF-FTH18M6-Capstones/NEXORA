# NEXORA Database Schema

## 1. Purpose

This document defines the proposed initial database structure
for the NEXORA SACCO Management System.

The design must be reviewed and agreed upon by the development
team before implementation.

## 2. Initial Entities

### Users
Stores platform user accounts.

- id (Primary Key)
- full_name
- email
- phone_number
- password_hash
- status
- created_at
- updated_at

### SACCOs
Stores registered SACCO organizations.

- id (Primary Key)
- name
- registration_number
- contact_email
- contact_phone
- status
- created_at
- updated_at

### Memberships
Connects users to SACCOs.

- id (Primary Key)
- user_id (Foreign Key → Users)
- sacco_id (Foreign Key → SACCOs)
- membership_number
- status
- joined_at

### Financial Transactions
Records financial activities.

- id (Primary Key)
- sacco_id (Foreign Key → SACCOs)
- member_id (Foreign Key → Memberships)
- transaction_type
- amount
- reference_number
- status
- created_at

## 3. Proposed Relationships

- One SACCO can have many memberships.
- One user can have multiple SACCO memberships.
- One membership belongs to one user and one SACCO.
- One membership can have multiple financial transactions.
- One SACCO can have multiple financial transactions.

## 4. Database Constraints

- Every table must have a primary key.
- Foreign keys must enforce valid relationships.
- Email addresses must be unique where required.
- Membership numbers must be unique within their SACCO.
- Monetary amounts are integer minor units in BIGINT columns, not FLOAT. Each SACCO has one currency.
- Financial transactions must not silently overwrite historical records.
- Financial operations must use database transactions.

## 5. Data Isolation

- Members must only access their own authorized records.
- SACCO Administrators must only access their SACCO's records.
- Platform Owner access must follow platform-level authorization rules.
- All authorization must be enforced by the backend.

## 6. Important Design Decisions Pending

The team must agree on:

- Whether users can belong to multiple SACCOs.
- Whether financial transactions require separate savings
  and loan account entities.
- Whether transaction records use a double-entry ledger.
- Final transaction types and statuses.
- Required indexes and deletion policies.
- Final column types and constraints.

## 7. Approval

This is a proposed initial schema, not an approved production
database design.

Approval must be recorded after team review.
