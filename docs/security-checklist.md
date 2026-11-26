# Security checklist

Every control below is marked **Done**, **Partial** or **Missing**, with the file that
implements it. Reviewed on 2026-11-25 against `development` at `44cdc40`. The two rows that were
**Partial** for want of a test — single-use reset/verification links, and profile photo
type and size — were re-checked on 2026-11-26 by running their tests; both pass and both
are now **Done**.

- **Done** — implemented in code, and where a test exists it is named.
- **Partial** — implemented, with a known gap that is written down rather than hidden.
- **Missing** — not implemented.

This is a self-assessment from reading the code. It is not a penetration test, and it
does not replace one: see [Penetration testing](#penetration-testing).

## Summary

| Area | Done | Partial | Missing |
|---|---|---|---|
| Authentication | 9 | 0 | 1 |
| Sessions and tokens | 4 | 1 | 1 |
| Authorisation and tenancy | 6 | 1 | 0 |
| Transport and browser hardening | 6 | 0 | 0 |
| Input handling and data access | 6 | 0 | 0 |
| Rate limiting and abuse | 2 | 2 | 1 |
| Secrets and configuration | 5 | 2 | 0 |
| Money movement and data integrity | 4 | 1 | 0 |
| Audit and logging | 2 | 1 | 2 |
| Dependencies and supply chain | 3 | 0 | 4 |
| Operations | 2 | 1 | 2 |
| **Total** | **49** | **9** | **11** |

## Authentication

| Control | Status | Evidence |
|---|---|---|
| Passwords hashed with Argon2id | Done | `backend/app/auth/passwords.py` |
| Password floor of 8 characters and a maximum length | Done | `passwords.py:19`, `routes.py:65` |
| Login lockout after 5 failures for 15 minutes | Done | `backend/app/auth/lockout.py`, `LOCKOUT_THRESHOLD`/`LOCKOUT_DURATION` in `backend/config.py` |
| Locked account refused before the password is checked | Done | `auth/account.py:72` |
| Emailed password reset | Done | `auth/routes.py` — `POST /forgot-password`, `POST /reset-password` |
| Emailed address verification | Done | `auth/verification.py` |
| Reset and verification tokens single use | Done | `auth/verification.py` — `confirm()` deletes the row it spends; `auth/account.py` — `reset_password()` spends the reset link through `revoke_all_sessions()`. Tested by `tests/test_account_recovery.py::test_a_reset_link_works_once` and `tests/test_email_verification.py::test_the_link_verifies_once` (second use answers 400) |
| SACCO join PIN hashed with Argon2, 5 tries then 15 minutes | Done | `backend/app/auth/pin.py` |
| Join code stored as an HMAC digest, shown once, one use, 5 attempts | Done | `auth/join.py:59,86,95` |
| Multi-factor authentication | Missing | Not implemented |

## Sessions and tokens

| Control | Status | Evidence |
|---|---|---|
| Access token is a JWT, 15 minutes, with `exp`, `iat`, `sub`, `jti`, `type`, `iss` and `aud` all required | Done | `auth/tokens.py:42,57,63` |
| Refresh token valid 7 days; only its `jti` is stored, never the JWT | Done | `models/refresh_token.py`, `auth/tokens.py:83` |
| Refresh rotation, and reuse of an old token revokes every token that user holds | Done | `auth/tokens.py:100` |
| Logout revokes the refresh token; logout-all revokes every session | Done | `auth/account.py:37,95` |
| Tokens kept in `localStorage` | Partial | `frontend/src/lib/http.js:32-34` — any XSS can read them. Move to an httpOnly `SameSite` refresh cookie with in-memory access token |
| Idle/session timeout beyond the 7-day refresh lifetime | Missing | No absolute session cap |

Because tokens travel in the `Authorization` header and not in cookies, CSRF is not a
live risk on the API (`backend/app/cors.py` explains the design). That changes if the
storage recommendation above is adopted.

## Authorisation and tenancy

| Control | Status | Evidence |
|---|---|---|
| One central tenant guard, with a fixed answer order: 401 no token, 404 missing SACCO **or** not a member (the same answer for both), 403 wrong role or inactive, 423 suspended | Done | `backend/app/security/tenant.py` |
| Platform owner read from the database on every request, never from the token | Done | `tenant.py` module docstring and guards |
| Screens and routes decide by permission name, not role name | Done | `security/permissions.py` (`can()`, `permissions_for()`) |
| Separation of duties: pay-in changes and reversals need two officers | Done | `backend/app/payments/`, `backend/app/savings/`, `tests/test_payment_details.py` |
| Support access needs the SACCO's consent on record and is audited | Done | `backend/app/support/`, `support.approve` in `permissions.py` |
| Every object read re-checks the tenant | Partial | Enforced by the guard on tenant routes; per-route object checks were not re-audited line by line |
| Malformed ids cannot slip past a lookup | Done | `IdConverter` in `app/__init__.py:69` — non-ASCII digits and leading zeros become 404 |

## Transport and browser hardening

| Control | Status | Evidence |
|---|---|---|
| `Strict-Transport-Security: max-age=31536000; includeSubDomains` in production | Done | `app/__init__.py` (`HSTS`, applied when `APP_ENV=production`) |
| `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store` on every `/api/` answer | Done | `SECURITY_HEADERS` in `app/__init__.py` |
| CORS: exact origins only, no wildcard, credentials off, `Vary: Origin` | Done | `backend/app/cors.py`; `*` refused in production |
| Content-Security-Policy | Done | `frontend/vercel.json` sends one on every path, tuned to what the app loads: its own scripts plus the boot script by SHA-256, Google Fonts CSS and files, `data:`/`blob:` for the CSS textures and the photo preview, and the API host for photos and calls; `connect-src` names the Vercel origin and the Render API only. `SECURITY_HEADERS` in `app/__init__.py` sends `default-src 'none'` on every `/api/` answer. Tested by `tests/test_security_config.py::test_an_api_answer_loads_nothing` |
| Security headers at the frontend edge | Done | `frontend/vercel.json` sends `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`, `X-Content-Type-Options: nosniff` and `Referrer-Policy: no-referrer` on every path, beside the CSP, so the app no longer leans on Vercel's defaults for them. The HSTS value is deliberately Vercel's own, which that origin already receives from the platform: two differing values on one response would leave the shorter one in force. Not yet read off the deployed edge: production and branch aliases both sit behind deployment protection |
| TLS terminated by the platform | Done | `render.yaml`, `frontend/vercel.json` — Render and Vercel terminate TLS; nothing in the repo asserts it |

## Input handling and data access

| Control | Status | Evidence |
|---|---|---|
| Parameterised database access | Done | SQLAlchemy throughout. The only raw SQL is a parameterless advisory lock: `admin/owners.py:33` |
| Request bodies capped at 16 KB | Done | `MAX_CONTENT_LENGTH` in `backend/config.py` |
| Assistant input capped per message and per turn, plus a daily cap | Done | `assistant/routes.py` — `MAX_MESSAGE`, `MAX_TURN`, `_daily_cap` |
| One error envelope, no stack traces or SQL leaked | Done | `backend/app/errors.py`, `tests/test_security_config.py` |
| Uploaded profile photos validated for type and size | Done | `members/routes.py` — `put_me_photo` reads at most 1.5 MB + 1 byte (413 above it, 400 when empty) and identifies the type from magic bytes, not the filename or the client's `Content-Type`; JPEG, PNG and WebP only. Tested by `tests/test_me.py::test_profile_photo_rejects_invalid_and_oversized_images` (an SVG body and a 1.5 MB file are both refused) |
| Output encoded before it reaches the DOM | Done | React escapes by default; no `dangerouslySetInnerHTML` in the app |

## Rate limiting and abuse

| Control | Status | Evidence |
|---|---|---|
| Fixed classes: login and register 5/min, reads 120/min, writes 30/min, money 20/min | Done | `backend/app/auth/limits.py` |
| Shared counters in production; `memory://` refused when `APP_ENV=production` | Done | `_check_production_settings` in `app/__init__.py` |
| Redis outage degrades to per-process limits | Partial | `init_limiter` logs the host and carries on. The allowance multiplies per worker — a deliberate availability trade |
| Per-account (not just per-IP) throttling | Missing | A distributed attempt from many addresses is not slowed |
| Real client IP behind a proxy | Partial | `TRUSTED_PROXIES` exists in `config.py`; it must be set to the proxy count on Render or every client looks like one address |

## Secrets and configuration

| Control | Status | Evidence |
|---|---|---|
| Secrets from the environment only | Done | `backend/config.py` — nothing hard-coded |
| `.env` and variants ignored, `.env.example` tracked | Done | `.gitignore:2-4` |
| Production refuses debug, a placeholder `SECRET_KEY`, `memory://` limits, `*` CORS, and the log mail backend | Done | `_check_production_settings`, `app/__init__.py:313` |
| Each SACCO's Daraja credentials encrypted at rest with Fernet | Done | `backend/app/payments/credentials.py` (`DARAJA_ENCRYPTION_KEY`) |
| Daraja callback URL carries a secret token | Done | `DARAJA_CALLBACK_TOKEN` in `config.py` |
| Key backup and rotation steps | Partial | README deployment section covers backup; no rotation drill |
| No secrets in tracked files | Partial | None seen while reviewing; no automated secret scan runs (see supply chain) |

## Money movement and data integrity

| Control | Status | Evidence |
|---|---|---|
| Ledger is append-only, enforced by a database trigger | Done | `backend/migrations/versions/0001_schema_v1.py:87-96` |
| Balances derived from the ledger, never stored and edited | Done | `backend/app/ledger/`, `tests/test_loans_and_ledger.py`, `tests/test_ledger_reversals.py` |
| Two-officer approval for pay-in changes and reversals | Done | `payments/`, `savings/` |
| A landside `advisory_xact_lock` serialises platform-owner changes | Done | `admin/owners.py:33` |
| Interest, late fines and guarantors enforced | Partial | Recorded, not enforced — stated in the README, not a security gap but a correctness one |

## Audit and logging

| Control | Status | Evidence |
|---|---|---|
| Privileged actions write an audit row, in one transaction with the change | Done | `backend/app/audit/`, `auth/account.py:4` |
| Audit rows readable only by an admin of that SACCO, or an owner under consent | Done | `backend/app/admin/`, `backend/app/support/` |
| No personal data in logs on the happy path | Partial | Emailed links go to the log only when `MAIL_BACKEND=log`, which production refuses; the Redis URI is logged by host only |
| Centralised log retention and alerting | Missing | Render's log stream only; nothing aggregated or alerted |
| Intrusion or anomaly alerting (spike in 401/403/423, lockouts) | Missing | Counters exist in the database and Redis, but nothing watches them |

## Dependencies and supply chain

| Control | Status | Evidence |
|---|---|---|
| Python dependencies pinned by version | Done | `backend/requirements.txt`, `requirements-prod.txt` |
| Frontend dependencies locked | Done | `frontend/package-lock.json`, `npm ci` in CI |
| CI runs the tests with a coverage floor and Ruff | Done | `.github/workflows/ci.yml` (`fail_under = 94` in `pyproject.toml`) |
| Vulnerability scanning of Python dependencies | Missing | No `pip-audit`, no OSV scan |
| Vulnerability scanning of npm dependencies | Missing | No `npm audit` in CI |
| Dependabot or similar version updates | Missing | No `.github/dependabot.yml` |
| Static analysis / secret scanning (CodeQL, gitleaks) | Missing | Not configured |

## Operations

| Control | Status | Evidence |
|---|---|---|
| Health endpoint for the platform | Done | `GET /health`, unversioned, `app/__init__.py:191` |
| Production start refuses unsafe settings | Done | `_check_production_settings` |
| Database backup and restore drill | Partial | Neon manages backups; no restore has been rehearsed and nothing in the repo documents one |
| Incident response: who is called, what is disclosed | Missing | No runbook |
| Penetration test | Missing | See below |

## Penetration testing

Status: **Missing**. The panel that would make a test most useful is still open: bearer
tokens sit in `localStorage`, so any XSS is a credential theft. The CSP now narrows what
an injected script could run or load, but it does not undo that. Fix the token storage
first, or accept it as accepted risk in the report.

### What a test needs to be worth running

**1. Scope, written down before the tester starts**

- In scope: the API at `https://nexora-api-aeoi.onrender.com` and the frontend at its
  Vercel URL, both at a pinned commit.
- Out of scope: Render, Neon, Vercel and Safaricom infrastructure; the Daraja sandbox
  itself; third-party mail delivery.
- Explicitly: no load or denial-of-service testing against production, and no testing
  that triggers real M-Pesa prompts.

**2. An environment that is not production data**

A separate Render service and Neon database with production-like settings
(`APP_ENV=production`, real Redis) but `DARAJA_ENV=sandbox`, `DARAJA_ENABLED=0` unless a
specific payment case needs it, and `MAIL_BACKEND=log` or a throwaway SMTP inbox.

**3. Seeded accounts, one per role and one pair for IDOR**

- platform owner; a SACCO admin, an officer and a member inside SACCO A
- a member who belongs to both SACCO A and SACCO B (the switcher path)
- an admin of SACCO B, for cross-tenant and cross-role attempts
- a member of a **suspended** SACCO, to exercise the 423 path
- an account that can be locked out (5 bad passwords) and one already locked
- at least one approved pay-in change and one reversal, so the two-officer flows can be
  attacked rather than merely read

**4. Access the tester needs**

- credentials for the accounts above, plus owner access to reset them
- the Daraja sandbox keys and callback token if payment callbacks are in scope, and the
  `GEMINI_API_KEY` either disabled or capped low so the assistant cannot be used to burn
  quota
- read access to application logs and the `audit_logs` table for correlating attempts
- permission to reset the database between test phases
- a named contact and a stop-and-report rule for anything critical

**5. A test window and rate-limit expectations**

Login is 5/minute per address, so anything that hammers auth will be throttled by design.
The tester needs to know this, and the window, so a 429 is not read as a defect.

**6. A deliverable that can be acted on**

Findings against OWASP WSTG/ASVS areas, each with severity, reproduction steps, the
request and response that shows it, and a retest window. Suggested order of effort:
broken access control and tenant isolation first (it is the highest-value area in a
multi-tenant money system), then authentication and session handling, then injection and
upload handling, then configuration and headers.

**7. What to fix first, so the test is not spent on known issues**

- decide the token storage question (httpOnly cookie or in-memory)
- add dependency scanning, so the report does not simply restate known CVEs
- add per-account login throttling
