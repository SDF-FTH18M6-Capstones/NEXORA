# Move 4: Finish the Backend

**Status:** Proposed for team review. Moves 1 to 3 are merged. This is the last
backend move. When it is merged, the only backend work left is a final red-team
pass (with its fixes) and deployment, which is decided later. After that, the
frontend is all that remains.

**Out of scope:** loans (blocked on the interest decision), the frontend,
penetration testing by an outside party, and the deployment itself.

---

## 1. What is already done

Auth (register, login, rotating refresh tokens, logout, lockout, login and
register rate limits, suspended-SACCO block). SACCOs, members and `/me`. Tenant
guard with 404 for another SACCO's records. Savings accounts, deposits,
withdrawals, reversals, ledger-derived balances, transaction history, audit
writer, admin reports. Migrations 0001 to 0007. 444 tests passing.

## 2. What this move adds (nothing is left out)

| # | Item | Owner |
|---|------|-------|
| 1 | CI with coverage, merges blocked on failure | Neo |
| 2 | CORS (frontend runs on another origin) | Neo |
| 3 | Security headers | Neo |
| 4 | Rate limits on every route that has none | Neo |
| 5 | Production safety checks (refuse unsafe config at startup) | Neo |
| 6 | Rewrite the broken seed script | Ryan |
| 7 | Savings read endpoints (account, balance, my account, SACCO account list) | Ryan |
| 8 | Audit-log read endpoints | Ryan |
| 9 | Change password and logout everywhere | Sam |
| 10 | One error format and one validation status on every route | Collins |
| 11 | OpenAPI spec for every route | Ryan |
| 12 | README, architecture doc, frontend handoff note | Sam |
| 13 | Final red-team pass, fixes, fresh-database check, sign-off | Collins |

Why these are needed (found by reading the code):

- `backend/scripts/seed.py` hashes passwords with werkzeug but login verifies
  with Argon2, so no seeded user can sign in. It also writes columns that do
  not exist (`role`, `sacco_id` on users) and creates no memberships.
- There is no `.github/` directory, so no CI exists, and `pytest-cov` is not
  installed or pinned.
- There is no CORS handling, so a browser on another origin cannot call the API.
- Only login and register are rate limited.
- There is no endpoint that returns an account or its balance, only history.
- Audit rows are written but nothing reads them, although
  `docs/roles-permissions.md` says admins and the platform owner can monitor
  activity.
- There is no way to change a password or end every session.

## 3. Rules for everyone

- One branch per person per task: `move-4/<name>` (for example
  `move-4/neo-ci`). Branch from a freshly pulled `development`.
- PRs go into `development`. One review from someone other than the author, and
  CI green (once Neo's CI is in). Nobody merges their own PR.
- Touch only the files listed in your task. A shared file (`app/__init__.py`,
  `config.py`, `requirements.txt`, migrations, `docs/`) is agreed in the team
  chat before the PR is opened. A PR with a migration names it in the title.
- Every endpoint gets at least one happy-path test and one failure-path test.
  Another SACCO's record answers 404, never 403. A suspended SACCO answers 423.
- Money is integer minor units. No floats.
- Before every commit run `git diff --staged` and check it. Never commit
  `.env`, secrets, `__pycache__`, `.venv` or caches. Commit messages and PR text
  describe the change only. Nothing in code, comments, docs or commit messages
  mentions the tools used to write it.
- Never force-push. Never push to `main`.
- Run the whole suite before opening a PR:

  ```bash
  pytest -m "schema or not schema"
  ruff check backend/app tests
  ```

  `pytest` alone skips the schema tests (see `pytest.ini`), and they cover the
  ledger, balances and reversals.

## 4. Order of work

```
Phase A   Neo: CI (first, alone)
Phase B   Neo, Ryan, Sam: their features in parallel (new routes use the
          current { "error": "..." } shape; Collins converts them in Phase C)
Phase C   Collins: error format on every route
Phase D   Ryan: OpenAPI.  Sam: README, architecture, handoff note
Phase E   Collins: red-team pass, fixes, fresh-database check, sign-off
Then      Deployment (decided later)
```

Do not start a phase before the one above it is merged, except Phase B, which
runs in parallel after Phase A.

---

## 5. Phase A: Neo, CI (do this first)

**Goal:** every PR runs the tests and lint, and a failing PR cannot merge.

1. `git checkout development && git pull && git checkout -b move-4/neo-ci`.
2. Add `pytest-cov==6.0.0` to `backend/requirements.txt` (shared file: say so in
   the chat).
3. Make ruff read one config for both `backend/app` and `tests`. Today the
   config is in `backend/pyproject.toml`, and files under `tests/` do not find
   it. Move the `[tool.ruff]` sections to a `pyproject.toml` at the repo root, or
   pass `--config backend/pyproject.toml` in the workflow. Add a coverage
   section: `[tool.coverage.run] source = ["backend/app"]` and
   `[tool.coverage.report] show_missing = true`.
4. Create `.github/workflows/ci.yml`:
   - Trigger: `pull_request` into `development` and `main`, and `push` to
     `development`.
   - One job on `ubuntu-latest` with a `postgres:16` service (user `postgres`,
     a password taken from the workflow env, health check `pg_isready`).
   - Steps: checkout, `actions/setup-python` with Python 3.12, `pip install -r
     backend/requirements.txt`, then run the tests.
   - Environment for the test step (the tests read these; there is no `.env` in
     CI): `SECRET_KEY` (any long random string), `DATABASE_URL`,
     `TEST_DATABASE_URL` pointing at a database named `nexora_test`. The
     migration tests create `nexora_schema_test` themselves, so the CI user must
     be allowed to create databases (the `postgres` superuser is).
   - Test command: `pytest -m "schema or not schema" --cov --cov-report=term-missing`.
   - Lint command: `ruff check backend/app tests`.
   - Never echo secrets. Use a throwaway password for the CI database, not a
     real one.
5. Open the PR. Wait for it to go green on its own PR.
6. Tell Collins. Collins turns on branch protection for `development`: require a
   pull request, require one approval, and require the CI check to pass. This
   needs repository admin rights.

**Done when:** a PR with a failing test or a ruff error shows a red check and
cannot be merged. Files you may touch: `.github/workflows/ci.yml`,
`pyproject.toml`, `backend/requirements.txt`.

---

## 6. Phase B

### 6.1 Neo: security and configuration

Branch `move-4/neo-security`.

**CORS** (no new dependency, about 20 lines in `backend/app/cors.py`):
1. Read `CORS_ORIGINS` from the environment: a comma-separated list of exact
   origins, for example `http://localhost:5173`. Add it to `config.py` and
   `.env.example`. Default: empty, which means no cross-origin access.
2. In an `after_request` hook: if the request's `Origin` is in the list, set
   `Access-Control-Allow-Origin` to that exact origin (never `*`), add
   `Vary: Origin`, and allow the headers `Authorization, Content-Type`, the
   methods `GET, POST, PATCH, OPTIONS`, and a preflight cache of 600 seconds.
   Do not allow credentials: tokens travel in the `Authorization` header, not
   in cookies.
3. Answer `OPTIONS` preflight requests with 204 for allowed origins.
4. Tests: an allowed origin gets the headers; a disallowed origin gets none; a
   preflight returns 204; an empty `CORS_ORIGINS` adds nothing.

**Security headers** (same hook or a second one): `X-Content-Type-Options:
nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and
`Cache-Control: no-store` on every `/api/` response. Add
`Strict-Transport-Security` only when running in production. Test that each
header is present on a normal response and on an error response.

**Rate limits** in `backend/app/auth/limits.py`:
1. Keep the login and register limits (5 per minute).
2. Add constants and decorators: reads `120 per minute`, ordinary writes
   `30 per minute`, money movements (deposit, withdraw, reversal) `20 per
   minute`.
3. Apply them to every route that has none: members, SACCOs, savings, reversals,
   history, admin reports, and the new routes from Ryan and Sam when they merge.
   To keep this complete, finish with a script-free check: list every route with
   `flask routes` and confirm each one is either limited or deliberately open
   (`/api/health`).
4. Tests: follow the pattern in `tests/test_auth_routes.py` (around line 410),
   which enables the limiter for one app and switches it off afterwards. For
   each limit class, one test shows requests under the limit pass and the next
   one returns 429 with the JSON error.
5. Check lockout still works after Sam's `current_user()` change on the savings
   routes.

**Production safety checks:**
1. Add `APP_ENV` (`development` default, `production`) to `config.py` and
   `.env.example`.
2. In `_check_required_settings` (shared file `app/__init__.py`: agree in chat),
   when `APP_ENV=production`, refuse to start, with a clear message, if any of
   these is true:
   - `FLASK_DEBUG=1`
   - `RATELIMIT_STORAGE_URI` starts with `memory://`
   - `SECRET_KEY` is shorter than 32 characters or equals the example
     placeholder
   - `CORS_ORIGINS` contains `*`
3. Add `Strict-Transport-Security` in production only.
4. Tests: each unsafe setting makes `create_app` raise; a safe production config
   starts.

**Done when:** all of the above merged, full suite and ruff green. Files you may
touch: `backend/app/cors.py`, `backend/app/auth/limits.py`, `backend/config.py`,
`backend/.env.example`, the route files only to add a limit decorator, and
`app/__init__.py` for the hooks and the startup checks (agreed in chat first).

### 6.2 Ryan: seed script, read endpoints, audit read

Branch `move-4/ryan-data`. Use fresh `development`, not an old branch.

**Seed script** (`backend/scripts/seed.py`, rewrite it completely):
1. Load `backend/.env` first (the config reads the environment at import time),
   then call `create_app()` and work inside `app.app_context()`.
2. Refuse to run unless the database name ends in `_dev`. Print why and exit.
3. Create through the models and services, never raw SQL, so the ledger,
   balances and audit rows stay consistent:
   - one platform owner user (`is_platform_owner=True`, no membership),
   - two SACCOs, "Alpha SACCO" and "Beta SACCO",
   - in each: one admin, one staff user and three members, as users plus
     `SaccoMembership` rows,
   - passwords with `app.auth.passwords.hash_password` (Argon2) and meeting
     `validate_password` (8 or more characters, not containing the email),
   - a savings account for each member through
     `app.savings.service.open_account`,
   - a few deposits and withdrawals through `service.deposit` and
     `service.withdraw`, and one reversal through
     `app.ledger.reversals.reverse_transaction`.
4. Make every reference fixed (for example `seed-alpha-m1-dep-1`). The services
   treat a repeated reference as a replay, so running the script twice posts
   nothing new. Look users and SACCOs up by email and name before creating them.
5. Use one clearly fake development password for all seeded users, defined as a
   constant at the top of the file, and print the list of seeded emails and
   roles at the end. The `_dev` check above is what keeps it out of any real
   database.
6. Run: `python backend/scripts/seed.py` from the repo root.
7. Test it: run it twice against a fresh schema and check counts do not change,
   that every seeded user can log in through `/api/v1/auth/login`, and that it
   refuses a non-dev database.

**Savings read endpoints** in `backend/app/savings/` (reuse the access rules in
`history.py`: another SACCO or someone else's account is 404, inactive
membership 403, suspended SACCO 423, platform owner may read any):
1. `GET /api/v1/savings/accounts/<id>`: returns `id`, `membership_id`,
   `sacco_id`, `balance`, `created_at`. A member can read only their own
   account. Admin and staff can read any account in their SACCO.
2. `GET /api/v1/savings/accounts/me`: returns `{"accounts": [...]}` with the
   caller's own accounts across their active memberships (a list, because
   whether a user can belong to more than one SACCO is still undecided). Same
   fields as above.
3. `GET /api/v1/admin/saccos/<id>/accounts` (in `admin/routes.py`, guarded with
   `sacco_scoped` for admin and staff): a paged list with `account_id`,
   `membership_id`, member email, `balance`. Paging uses `page_params()` from
   `savings/history.py`.
4. Add `balance` agreement as a test: for a seeded account, the value returned
   equals `ledger_balance(account_id)`.

**Audit read endpoints** (new `backend/app/admin/audit.py`, routes in
`admin/routes.py`):
1. `GET /api/v1/admin/saccos/<id>/audit`: SACCO admin and platform owner only
   (not staff, because the log shows who did what). Filter parameters: `action`
   (exact name or prefix ending in `.`, for example `savings.`), `from`, `to`
   (dates, same overflow-safe handling as the reports), plus `page` and
   `per_page`. Newest first (`created_at`, `id`). Fields: `id`, `actor_id`,
   `action`, `target`, `created_at`. Every query filters by `sacco_id`.
2. `GET /api/v1/admin/audit`: platform owner only (anyone else gets 403). Same
   filters plus an optional `sacco_id`.
3. Read-only: no edit or delete endpoints. The database already forbids them.
4. Tests: admin sees only their SACCO's rows; another SACCO's admin gets 404;
   staff and members get 403; the platform route refuses a SACCO admin; filters
   and paging work; bad dates and bad paging return 400; no response contains
   anything but the listed fields.

**Done when:** the seed script works twice in a row and every seeded login
works, the five new GET routes are merged with tests, full suite and ruff green.
Files you may touch: `backend/scripts/seed.py`, `backend/app/savings/accounts.py`
(new), `backend/app/admin/audit.py` (new), `backend/app/admin/routes.py`, and
`app/__init__.py` to import the new module (agreed in chat first), plus tests.

### 6.3 Sam: account security

Branch `move-4/sam-auth`.

**`POST /api/v1/auth/change-password`** (file `backend/app/auth/routes.py`; put
the logic in `backend/app/auth/account.py` if it keeps the route short):
1. Requires a valid access token. Body: `current_password`, `new_password`.
2. Verify `current_password` with `verify_password`. A wrong one counts as a
   failed attempt through the existing `record_failed_login` and the same
   lockout rules as login, and answers 401 with the same message as a failed
   login.
3. Validate `new_password` with `validate_password(new, user.email)`, the same
   length cap as register (`MAX_PASSWORD_LENGTH`), and refuse a new password
   equal to the current one. Bad input is 400.
4. On success: store the new Argon2 hash, reset failed logins, revoke every
   refresh token of the user (set `revoked_at` on all rows in `refresh_tokens`
   that are not yet revoked), write an audit row `auth.password_change` with
   the user as actor, commit once, answer 200. The user signs in again to get new
   tokens. An access token already issued stays valid until it expires
   (15 minutes). State that in the handoff note.
5. Rate limit: the same 5 per minute as login (Neo adds the decorator if his
   PR is not merged yet).

**`POST /api/v1/auth/logout-all`:**
1. Requires a valid access token. Revokes every refresh token of the user and
   writes an audit row `auth.logout_all`. Answers 200.
2. Suspended SACCO users are still allowed to log out (this should never trap a
   user in a session).

**Tests** (extend `tests/test_auth_routes.py` or add
`tests/test_account_security.py`): wrong current password gives 401 and
increments the failure count; five wrong attempts lock the account;
too-short, email-containing and same-as-current passwords give 400; success
changes the hash, revokes old refresh tokens (a refresh with an old token now
fails) and the new password logs in; no token gives 401; logout-all revokes
every token of that user only (another user's tokens still work); both actions
write audit rows with the right actor.

Then review the PRs from Neo and Ryan.

**Done when:** both routes merged, tests green. Files you may touch:
`backend/app/auth/routes.py`, `backend/app/auth/account.py` (new), tests.

---

## 7. Phase C: Collins, one error format

Start only after Neo's, Ryan's and Sam's feature PRs are merged, so the new
routes are converted in the same sweep.

Branch `move-4/collins-envelope`.

**Decisions (record them in `docs/api-conventions.md`):**
- Validation errors are **400**. Every route already returns 400 for bad input;
  no route returns 422.
- Success bodies stay exactly as they are today.
- Every error body is:

  ```json
  { "error": { "code": "not_found", "message": "Not found." } }
  ```

| Status | `code` |
|--------|--------|
| 400 | `validation_error` |
| 401 | `unauthorized` |
| 403 | `forbidden` |
| 404 | `not_found` |
| 405 | `method_not_allowed` |
| 409 | `conflict` |
| 413 | `payload_too_large` |
| 423 | `locked` (also a suspended SACCO) |
| 429 | `rate_limited` |
| 500 | `internal_error` |

Steps:
1. Create `backend/app/errors.py` with the code table and one helper
   `error_response(status, message, code=None)` returning
   `(jsonify({"error": {"code": ..., "message": ...}}), status)`. If `code` is
   omitted it comes from the table by status. Create `backend/app/responses.py`
   only if a second helper is needed; do not add empty files.
2. Replace every ad-hoc error response with it. Search for all of them:

   ```bash
   grep -rnE 'jsonify\(\s*\{?\s*"?error|\{"error"|jsonify\(error=' backend/app
   ```

   Known places: `auth/routes.py` (`_error`), `savings/routes.py` (`_error`,
   used by `ledger/routes.py`), `members/routes.py` (`_error`, `_me_error`),
   `saccos/routes.py`, `security/tenant.py` (`sacco_scoped`), `savings/history.py`,
   `admin/routes.py`, `auth/limits.py` (`rate_limit_response`), `auth/guards.py`,
   `app/__init__.py` (`_json_http_error`, `_json_server_error`), and the new
   routes from this move. Delete the duplicated `_error` helpers.
3. Keep messages exactly as they are (clients and tests may match on them);
   only the shape changes.
4. Update tests: anywhere a test reads `response.json["error"]` as a string it
   now reads `response.json["error"]["message"]`. Find them with
   `grep -rn '\["error"\]\|get_json()\["error"\]\|json\["error"\]' tests`.
   Add one test per status in the table asserting `code` and `message`.
5. Add a guard test: walk every route in `app.url_map` that is not
   `/api/health` and `static`, send a request with no token, and assert the
   body shape is the new one. This catches any route that was missed.
6. Update `docs/api-conventions.md` with the format, the table, the 400
   decision, the 404-not-403 rule, pagination (`page`, `per_page`, capped at
   100) and money as integer minor units.

**Done when:** the `grep` in step 2 finds nothing outside `errors.py`, the guard
test passes, the full suite and ruff are green, and one review is done.

---

## 8. Phase D (after Phase C is merged)

### 8.1 Ryan: OpenAPI spec

Branch `move-4/ryan-spec`. Update `docs/openapi.yaml` (it already exists; check
each existing entry against the code).

Document all 30 routes under `/api/v1`, plus `GET /api/health`:

- auth (6): register, login, refresh, logout, change-password, logout-all
- members (2): `GET` and `PATCH /members/me`
- saccos (10): create, list, get, patch, activate, deactivate, list members,
  get member, add member, patch member
- savings (7): open account, get account, get my accounts, deposit, withdraw,
  history, reversal
- admin (5): summary report, member-activity report, account list,
  SACCO audit, platform audit

For each route: method and path, who may call it, request body and query
parameters (with limits and defaults), the success response, and every error
response with its status and code. Note the `reference` idempotency key on money
routes (201 for a new entry, 200 for a replay), the 404 rule, the 423 rule, and
that amounts are integers in minor units.

Check it two ways: the route count matches `flask routes` (30 plus health), and
the file parses as valid OpenAPI (for example with an online validator or
`openapi-spec-validator` run locally; do not add it to `requirements.txt`
unless the team agrees).

### 8.2 Sam: docs and handoff note

Branch `move-4/sam-docs`. Write it last, against the merged code.

1. `README.md`: update the status checklist (Moves 1 to 4 done, loans pending
   the interest decision). Make the local setup steps accurate: environment
   file, creating `nexora_dev`, `nexora_test` and `nexora_schema_test`,
   migrations (`flask db upgrade`), seed (`python backend/scripts/seed.py`),
   running the server, running the tests (`pytest -m "schema or not schema"`)
   and lint.
2. `docs/architecture.md`: replace the open decisions with what was decided:
   the `/api/v1` prefix; access and rotating refresh tokens; the tenant guard
   and 404-not-403; the append-only ledger and the trigger-maintained balance;
   reversal rules (a reversal is a new opposite entry, once per entry, never of
   a reversal, enforced in the app and in the database); the audit log; the
   error format and the 400 decision; CORS and rate limits.
3. `docs/frontend-handoff.md`. A frontend developer who has never seen the code
   must be able to log in and load a SACCO dashboard from this note alone:
   - base URL, and how to start the API locally with seeded data;
   - the seeded logins (emails and roles from Ryan's seed output);
   - the auth flow: register, login, `Authorization: Bearer <access>`, refresh
     (refresh tokens rotate: always store the newest), logout, logout-all,
     change-password, what 401, 423 and 429 mean, access tokens last 15
     minutes, refresh tokens 7 days;
   - the error format and the status table;
   - pagination (`page`, `per_page`);
   - money as integers in minor units (KES, 100 = 1.00);
   - the idempotency `reference` and how to retry safely;
   - **a dashboard recipe:** which calls to make after login, in order (for a
     member: `/savings/accounts/me`, then the history; for an admin: the SACCO
     summary, member-activity and account list), with a real request and
     response for each;
   - the CORS origin setting (`CORS_ORIGINS`) the frontend must be listed in.
4. Test your own note: run the seed script, start the API, and follow the note
   step by step with `curl`. Fix any step that does not work as written.

**Done when:** the note works end to end with copy and paste, the README setup
works on a clean clone, and the docs mention no open decision that was made.

---

## 9. Phase E: Collins, finish and sign-off

1. **Fresh-database check** on a new `nexora_dev`: `flask db upgrade` runs
   0001 to 0007 with no errors; `python backend/scripts/seed.py` runs twice;
   `flask run` starts; `/api/health` answers `healthy`; log in as the platform
   owner, a SACCO admin and a member; run the dashboard recipe from the handoff
   note.
2. **Red-team pass** over the whole API (not only the money path): auth and
   tokens, tenant isolation on every route, role checks, input limits on every
   body and query parameter, rate limits and lockout, error responses leaking
   details, CORS and headers, the new password and audit routes. Use the route
   list from `flask routes` as the checklist so no route is skipped.
3. **Fix** every critical, high and medium finding, each with a test, in one or
   more small PRs. Simplify anything the review shows is longer than it needs to
   be, with the tests unchanged. Run the red-team pass again on the fixes.
4. **Final checks:**
   - CI is green on `development`.
   - `pytest -m "schema or not schema" --cov` reports coverage, and every
     endpoint has a happy-path and a failure-path test.
   - `ruff check backend/app tests` is clean.
   - Search the tracked files and the recent commit messages for attribution
     lines or tool names (`git grep -niE "co-authored|generated with"` plus the
     names of any tool the team used) and confirm nothing is found.
     One earlier commit on `development` (`9b53cd9`) carries a tool trailer.
     Rewriting it needs a force-push; the team decides whether to leave it.
   - No `.env`, `.venv`, caches or secrets are tracked (`git ls-files`).
5. **Sign-off:** every move's Done-when line is true with evidence, and each
   person says in one sentence what they built.

---

## 10. After this move: decided later

These are not part of the backend code and are decided and planned separately:

- **Deployment:** the host, how the app runs (for example gunicorn behind a
  reverse proxy), environment variables (`APP_ENV=production`, `SECRET_KEY`,
  `DATABASE_URL`, `CORS_ORIGINS`, `TRUSTED_PROXIES`, `RATELIMIT_STORAGE_URI`
  pointing at Redis), running migrations on the host, backups, logs, HTTPS and a
  health check. Neo's production checks in section 6.1 make a bad configuration
  fail at startup.
- **A penetration test** by someone outside the team, before real money or real
  users.
- **Loans:** a Move 5 once the interest decision is made.
- **Open schema questions** (can a user belong to more than one SACCO, and whether
  accounts carry a currency) that do not block the above.

## 11. Done when (the move)

- Neo's, Ryan's, Sam's and Collins's PRs are merged and CI is green.
- All 30 routes follow the one error format and have a spec entry.
- A fresh database plus the seed script gives a working API.
- The frontend can log in and load a SACCO dashboard using only the handoff
  note.
- The red-team pass has run and its critical, high and medium findings are
  fixed.
