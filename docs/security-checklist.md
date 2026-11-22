# Security checklist

Status of each control as of 2026-11-18, branch `move-7/collins-docs-ci`. **done** = implemented and covered by a test; **partial** = implemented with a stated gap; **not done** = absent. Each row names the file where it lives and the test that proves it.

| Control | Status | Where | Evidence |
|---|---|---|---|
| Passwords hashed with Argon2 | done | `backend/app/auth/passwords.py` | `tests/test_passwords_lockout.py` |
| Lockout: 5 failed logins lock the account 15 minutes (423) | done | `backend/app/auth/lockout.py`, `backend/config.py` | `tests/test_passwords_lockout.py` |
| Login limited to 5 per minute per IP; reads 120, writes 30, money 20 per minute | done | `backend/app/auth/limits.py` | `tests/test_rate_limits.py` |
| Access tokens last 15 minutes and carry `token_version`; change-password, reset, logout-all and email change revoke them at once | done | `backend/app/auth/tokens.py`, `backend/app/security/tenant.py` | `tests/test_account_security.py` |
| Rotating refresh tokens; replay after the 10 s grace revokes all of the user's tokens | done | `backend/app/auth/tokens.py` | `tests/test_auth_routes.py` |
| Tenant isolation: another SACCO's records answer 404, never 403 | done | `backend/app/security/tenant.py` | `tests/test_saccos_access.py`, `tests/test_error_format.py` |
| Permissions by role rows, not hard-coded roles | done | `backend/app/security/permissions.py` | `tests/test_permissions.py`, `tests/test_access_by_permission.py` |
| Separation of duties: nobody posts or reverses money on their own account | done | `backend/app/savings/service.py` | `tests/test_reversals.py` |
| Append-only ledger and audit log, enforced by database triggers; balance changed only by trigger | done | `backend/migrations/versions/0001`, `0005` | `tests/test_schema_rules.py`, `tests/test_ledger_reversals.py` |
| Money idempotency: `reference` required, replay returns the original | done | `backend/app/savings/service.py` | `tests/test_savings_concurrency.py` |
| One error format; no stack traces to clients | done | `backend/app/errors.py` | `tests/test_error_format.py` |
| Email enumeration closed: forgot-password and resend-verification always answer the same | done | `backend/app/auth/routes.py` | `tests/test_account_recovery.py`, `tests/test_email_verification.py` |
| Request body capped at 16 KB (413) | done | `backend/config.py` | `tests/test_error_format.py` |
| Security headers on every `/api/` response (nosniff, DENY framing, no-referrer, no-store) | done | `backend/app/__init__.py` | `tests/test_security_config.py` |
| HSTS in production | done | `backend/app/__init__.py` | `tests/test_security_config.py` |
| CORS by exact origin list; `*` refused in production | done | `backend/app/cors.py` | `tests/test_security_config.py` |
| Production start refuses debug, `memory://` rate limits, short or example `SECRET_KEY`, wildcard CORS, log mail backend | done | `backend/app/__init__.py` | `tests/test_security_config.py` |
| Database role `nexora_app` with limited privileges | partial | `backend/migrations/versions/0014_nexora_app_role.py` | `tests/test_app_role_privileges.py`; one test skips when the migrating user cannot ALTER ROLE, and CI does not provision the role (see `docs/parked.md`) |
| Consent-based support access for platform owners | done | `backend/app/support/` | `tests/test_support_access.py` |
| Rate limits shared across workers (Redis) | partial | `backend/app/auth/limits.py` | Tested with fakeredis only; `rediss://` (TLS) against a real server is untested. Issue #92 |
| Coverage floor in CI | done | `pyproject.toml` (`fail_under = 94`), `.github/workflows/ci.yml` | Issue #94. Measured 94.96% |
| Release a phone number claimed by a wrong join code | not done | none | `docs/parked.md`; the platform owner fixes it in the database |
| Penetration test (read-and-probe pass, 2026-11-18) | done | none | Issue #93: no critical finding, no cross-tenant or money-integrity break. Fixed: loans on a deactivated borrower, 500s on non-object JSON, an out-of-range `sacco_id` and lone surrogates, CORS preflight for PUT and DELETE, end-of-day totals (`tests/test_pentest_fixes.py`). Open items are listed below. Dependency scan, real Redis, SMTP and TLS were not tested |
| Production deployment, TLS and secrets on a real host | not done | none | Issue #92 |
| Dependency vulnerability scan (for example `pip-audit`) in CI | not done | none | No issue yet |
| Multi-factor authentication | not done | none | Not planned for release 1; no issue |

## Open findings from the penetration test (not fixed; decisions for the team)

1. `GET /admin/audit` lets a platform owner read any SACCO's audit rows (actor ids, actions, target ids; no balances) without a support grant and without a `support.read` row. The existing test `test_the_platform_route_is_for_the_owner_only` asserts this today. Decide whether the consent rule covers the audit log; if yes, restrict that route to platform-wide rows.
2. `POST /auth/join`: any signed-in user who knows a phone number can burn the pending invitation for it with 5 wrong codes (an officer must re-invite). Fix needs a rule: count wrong attempts per user and phone, or require a verified email.
3. Account enumeration and lockout abuse: register answers 409 for a known email, and 5 bad passwords lock a known account for 15 minutes from any IP.
4. `GET`/`POST` on support-access ids: a foreign existing id answers 403 and a missing one 404, which reveals ids across SACCOs (low).
5. Production does not require `TRUSTED_PROXIES`: left at 0 behind a proxy, all clients share one rate-limit bucket. Add a deploy check (issue #92).
6. A raw database trigger message is returned on a refused support-access decision (`backend/app/support/routes.py`), limited to 200 characters (low).
7. `backend/requirements.txt` ships test and lint tools; split them before the production image (issue #92).

Content-Security-Policy is not set: the API returns JSON only, so it has no effect until the backend serves HTML.

## Sign-off

Collins: ____________________  Date: ____________
