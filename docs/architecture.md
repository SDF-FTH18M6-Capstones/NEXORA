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

- Store money as integer minor units (e.g. cents) in BIGINT columns, never floats. Each SACCO has one currency.
- Use atomic database transactions for financial operations.
- Preserve historical financial records.
- Correct financial mistakes using reversal entries rather than silently editing historical transactions.

## 6. Current State

- Moves 1 to 4 are done: Flask app factory, schema and migrations (0001 to 0007), auth, SACCOs and members, savings, the ledger and reversals, admin reports, the audit log, the seed script and CI.
- Loans are not built. They wait for the interest decision (see section 8).
- The React frontend is still the Vite starter. The API is ready for it; start with [`frontend-handoff.md`](frontend-handoff.md).

## 7. Decisions

Everything below was open earlier and is now decided and implemented. The code is the source of truth; file names are given so you can find it.

### API prefix and versioning

Every resource route lives under `/api/v1`. The prefix is set in one place, `API_PREFIX` in `backend/app/__init__.py`, and each blueprint adds its own part (`/auth`, `/saccos`, `/members`, `/savings`, `/admin`). The health check stays unversioned at `GET /api/health`. A breaking change would go under `/api/v2`.

### Authentication: access and rotating refresh tokens

- JWT (HS256, signed with `SECRET_KEY`), not server-side sessions. Passwords are hashed with Argon2.
- **Access token**: 15 minutes, sent as `Authorization: Bearer <token>`. It carries the user's `token_version`; every request compares it with `users.token_version`, so a password change or logout-all (which bump it) kills all earlier access tokens at once.
- **Refresh token**: 7 days. Only its id (`jti`) is stored, in `refresh_tokens`. Every refresh spends the old token and issues a new one (rotation). A spent token replayed after more than 10 seconds is treated as stolen and every refresh token of that user is revoked. Replays inside 10 seconds are refused but do not revoke the rest (double submit).
- **Lockout**: 5 failed logins lock the account for 15 minutes (423). The lock is checked before the password, so a locked account never reveals whether a guess was right. A wrong current password in `change-password` counts as a failed login, with the same lockout.
- **Ending sessions**: `logout` revokes one refresh token. `logout-all` and a successful `change-password` revoke all of the user's refresh tokens. Both also bump `token_version`, so every access token already issued stops working immediately, and the user signs in again.
- **Suspended SACCOs**: a user whose SACCOs are all suspended cannot log in or refresh (423). `logout-all` and `change-password` still work for them, so nobody is trapped in a session.
- Files: `app/auth/` (`routes.py`, `tokens.py`, `lockout.py`, `account.py`, `suspension.py`).

### Tenant guard and 404 instead of 403

One function, `sacco_access` in `app/security/tenant.py`, decides who may touch a SACCO. Order of checks:

1. No valid access token: 401.
2. SACCO missing, or the caller has no membership in it: **404**, the same answer for both, so nobody can discover which SACCOs exist.
3. Member of that SACCO but inactive, or the wrong role: 403.
4. SACCO suspended (platform owner exempt): 423.

The platform owner flag is read from the database on every request, never from the token. A SACCO id in a URL or body is never trusted on its own. A plain member who asks for another member's account gets 404.

### Append-only ledger and trigger-maintained balance

- Money is an integer in minor units (KES: 100 = 1.00), never a float. Each SACCO has one currency.
- `transactions` is the ledger. Rows are never updated or deleted: database triggers refuse UPDATE, DELETE and TRUNCATE (migrations 0001 and 0005).
- `savings_accounts.balance` is **not written by the app**. A trigger adds each new ledger row to the balance, and another refuses any direct change to it (migration 0005). A `CHECK` keeps it from going below zero, so a withdrawal beyond the balance fails even under concurrency (the app also locks the account row and answers 409 "Insufficient funds").
- Every deposit, withdrawal and reversal carries a `reference`, unique per SACCO. It is the idempotency key: a retry with the same reference and the same request returns the original (200, `"replayed": true`); the same reference with a different request is 409.

### Reversals

A mistake is corrected by a new, opposite entry that points at the original through `reverses_id`. History is never edited.

- A reversal is a new row of the opposite type, same account and same amount.
- An entry can be reversed **once** (`reverses_id` is unique).
- A reversal can **never be reversed**. To redo the money, post a fresh deposit or withdrawal.
- Only active admins and staff of the SACCO can reverse. A member cannot.
- A reversal that would take the balance below zero is refused (409).
- These rules are enforced in the app (`app/ledger/reversals.py`) and again in the database (unique constraint plus the `validate_transaction` trigger, migrations 0006 and 0007), so a bug or a direct SQL insert cannot break them.

### Audit log

`audit_logs` is append-only in the database (UPDATE, DELETE and TRUNCATE refused). Each row is written in the same transaction as the action it records, so a refused or rolled-back action leaves no row, and a committed action cannot lose its row. A row holds the SACCO (empty for platform-wide actions), the actor, an action name and a target.

Actions in use: `savings.open`, `savings.deposit`, `savings.withdrawal`, `savings.reverse`, `sacco.*`, `member.*`, `auth.password_change` and `auth.logout_all`. The two `auth.*` actions are not tied to a SACCO, so they appear only in the platform owner's log (`GET /api/v1/admin/audit`). A SACCO admin reads their own SACCO's log at `GET /api/v1/admin/saccos/<id>/audit`.

### Error format and the 400 decision

- Every error, including 404, 405 and 500, is JSON: `{"error": {"code": "not_found", "message": "Not found."}}`; the code table is in [`api-conventions.md`](api-conventions.md). There is no `success` / `data` envelope; successful responses return the resource itself. Messages never include details such as stack traces or SQL.
- **Validation errors are 400. We do not use 422.** One code for "your request is wrong" keeps the frontend simple. 409 is for conflicts with current state (duplicate email, reused reference, insufficient funds, reversing a reversal).
- Status codes in use: 200, 201, 400, 401, 403, 404, 409, 423 (locked or suspended), 429, 500. The table is in [`frontend-handoff.md`](frontend-handoff.md).
- `docs/api-conventions.md` was written before these decisions. Where it differs (the `success` envelope, 422), this section wins.

### Email verification

- `register` creates the user unverified and emails a single-use link (24 hours). Only the token's SHA-256 is stored (`email_verifications`). Opening it sets `users.email_verified_at`.
- Login does not need it. **A SACCO admin can only add a verified user**, so someone who registers an address they do not own cannot be attached to a SACCO. Changing the email resets it.
- Mail goes through `app/mail.py`: `MAIL_BACKEND=log` locally, `smtp` in production (the app refuses to start in production otherwise).
- Someone can still register an address they do not own first. That gets them nothing: they cannot be added to a SACCO unverified, and the real owner takes the account over with forgot-password (the reset link proves the mailbox and ends every session).

### Account recovery

- `forgot-password` always answers 200 and emails a 1-hour single-use link (`email_verifications`, purpose `reset`). `reset-password` sets the password, clears the lockout, marks the email verified, revokes every session (`token_version` bump plus all refresh tokens) and writes the audit row `auth.password_reset`.
- Changing the email through `PATCH /members/me` also ends every session.

### Decisions on known trade-offs

- **Lockout is per account** (5 wrong passwords, 15 minutes). Anyone who knows an email can lock it out, which is the price of stopping guessing. Recovery is forgot-password, which also clears the lock.
- **Email probing.** `register` answers 409 for a taken address, so existence can be found that way; the locked-account 423 and the admin add-member 404 add nothing beyond it. Not changed: a generic register answer would need a different sign-up flow.
- **Separation of duties.** Nobody posts or reverses money on their own account (403).
- **Tokens** carry `iss` and `aud`; the app refuses to start with a `SECRET_KEY` under 32 characters in any environment.
- **Login 429 under parallel attempts** (`Another attempt is in progress`) stays: it is what stops guesses from racing the failure counter.

### CORS and rate limits

- **Rate limits** (Flask-Limiter, per client IP): `login`, `register` and `change-password` allow 5 requests per minute; the sixth gets 429. Counters live in memory locally; set `RATELIMIT_STORAGE_URI` to Redis in production so all workers share them. Behind a reverse proxy set `TRUSTED_PROXIES` to the number of proxies, or every client shares the proxy's address.
- Every other route has a class limit: reads 120 per minute, ordinary writes 30, money movements (deposit, withdraw, reversal) 20.
- **CORS**: `CORS_ORIGINS` lists the exact allowed origins (empty by default: no cross-origin access). Credentials are off; the wildcard is never sent. See "CORS" in [`frontend-handoff.md`](frontend-handoff.md).

## Before deploying

The production guards only run when `APP_ENV=production`, and the default is `development`, so a deploy that forgets the variable runs unguarded (no HSTS, in-memory rate limits). Check each of these on the host:

- `APP_ENV=production`
- `SECRET_KEY` of 32+ random characters (not the example)
- `DATABASE_URL`, `CORS_ORIGINS` (exact frontend origin), `FRONTEND_URL`
- `RATELIMIT_STORAGE_URI` pointing at Redis, and `TRUSTED_PROXIES` set to the real proxy count
- `MAIL_BACKEND=smtp` with `MAIL_SERVER`, `MAIL_FROM` and credentials
- `FLASK_DEBUG` unset, HTTPS in front, `flask db upgrade` run, a working `/api/health`

## 8. Still Open

- **Loans.** Waiting for the interest decision (rate, simple or compound, who sets it). No loan tables or routes exist.
