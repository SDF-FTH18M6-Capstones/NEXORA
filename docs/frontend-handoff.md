# NEXORA frontend handoff

This note is enough to log in and load a SACCO dashboard against the local API. Every command was run against the seeded API and the responses below are real, except that tokens are shortened and ids, timestamps and token values will differ on your machine.

Commands are bash (macOS, Linux, WSL, Git Bash). They use `curl`; `jq` is optional (see "Two ways to use a token").

Contents: [1 Start the API](#1-start-the-api-locally-with-seeded-data) · [2 Seeded logins](#2-seeded-logins) · [3 Auth flow](#3-auth-flow) · [4 Conventions](#4-conventions) · [5 Idempotency](#5-idempotency-and-safe-retries) · [6 Dashboard recipes](#6-dashboard-recipes) · [7 CORS](#7-cors) · [8 Endpoint list](#8-endpoint-list)

---

## 1. Start the API locally with seeded data

**Base URL:** `http://localhost:5000`  
**API root:** `http://localhost:5000/api/v1` (every route except the health check lives under it)

You need Python 3.12+ and PostgreSQL running. The first time only:

```bash
# from the repo root
psql -U postgres -c "CREATE DATABASE nexora_dev;"
cd backend
python3 -m venv venv
source venv/bin/activate            # Windows Git Bash: source venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env                # then edit .env: set SECRET_KEY and your Postgres password
flask db upgrade                    # creates the tables
cd ..
python backend/scripts/seed.py      # demo SACCOs, users and money (dev database only)
```

Start the server (every time):

```bash
cd backend
source venv/bin/activate
flask run
```

Check it:

```bash
curl -s http://localhost:5000/api/health
# {"database": "connected", "status": "healthy"}   (spacing varies with FLASK_DEBUG)
```

The seed is safe to run twice. To start over, drop and recreate `nexora_dev`, run `flask db upgrade`, and seed again.

Set this once in every terminal you use for the examples below:

```bash
API=http://localhost:5000/api/v1
```

## 2. Seeded logins

Every seeded user has the same password: **`Dev-Seed-Pass-2026`**. It only exists in dev databases.

| Email | Role | SACCO |
|---|---|---|
| `owner@example.com` | platform owner | none (sees every SACCO) |
| `alpha-admin@example.com` | `sacco_admin` | Alpha SACCO (id 1) |
| `alpha-staff@example.com` | `staff` | Alpha SACCO |
| `alpha-m1@example.com` | `member` | Alpha SACCO (has 4 transactions, one reversed) |
| `alpha-m2@example.com` | `member` | Alpha SACCO |
| `alpha-m3@example.com` | `member` | Alpha SACCO |
| `beta-admin@example.com` | `sacco_admin` | Beta SACCO (id 2) |
| `beta-staff@example.com` | `staff` | Beta SACCO |
| `beta-m1@example.com` … `beta-m3@example.com` | `member` | Beta SACCO |

Roles: **platform owner** manages SACCOs and sees all of them. **`sacco_admin`** manages one SACCO, posts money and reads reports. **`staff`** posts money and reads reports, but cannot read the audit log or edit the SACCO. **`member`** reads only their own account.

Login does **not** return the user's role or SACCO. Call `GET /members/me` after login to learn them (see the recipes).

## 3. Auth flow

Tokens are JWTs. **Access token: 15 minutes. Refresh token: 7 days.**

### Two ways to use a token

Every protected request sends `Authorization: Bearer <access_token>`. The examples use a shell variable:

```bash
ACCESS="paste the access_token here"
```

With `jq` you can set it straight from login:

```bash
ACCESS=$(curl -s -X POST $API/auth/login -H "Content-Type: application/json" \
  -d '{"email":"alpha-m1@example.com","password":"Dev-Seed-Pass-2026"}' | jq -r .access_token)
```

### Register

```bash
curl -s -X POST $API/auth/register -H "Content-Type: application/json" \
  -d '{"email":"newuser@example.com","password":"first-password-123"}'
```
```json
{"email": "newuser@example.com", "id": 12}
```
Status 201. Passwords: 8 to 128 characters, and they cannot contain the email address. Duplicate email: 409. A new user has **no SACCO and no accounts**; a SACCO admin has to add them as a member. Registering does not log you in.

### Login

```bash
curl -s -X POST $API/auth/login -H "Content-Type: application/json" \
  -d '{"email":"alpha-m1@example.com","password":"Dev-Seed-Pass-2026"}'
```
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs…",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs…",
  "token_type": "Bearer"
}
```

Then send `Authorization: Bearer <access_token>` on every other call.

### Refresh (tokens rotate)

When a protected call answers 401, get a new pair:

```bash
curl -s -X POST $API/auth/refresh -H "Content-Type: application/json" \
  -d '{"refresh_token":"<your refresh_token>"}'
```

The response has the same shape as login. **The old refresh token is dead the moment you use it, so always store the newest one.** Rules for the frontend:

- Run **one refresh at a time**. If several requests get 401 together, make one refresh and let the others wait for it. Two parallel refreshes with the same token: one wins, the other gets 401.
- Never reuse an old refresh token. Reusing a token spent more than 10 seconds ago is treated as theft and **revokes every refresh token of that user**, so they must log in again.
- If refresh itself answers 401 (or 423), the session is over: clear the tokens and show the login page.

### Logout, logout-all, change-password

```bash
# this device: revoke one refresh token
curl -s -X POST $API/auth/logout -H "Content-Type: application/json" \
  -d '{"refresh_token":"<your refresh_token>"}'
# {"message": "Logged out."}

# every device: revoke all of the user's refresh tokens (needs the access token)
curl -s -X POST $API/auth/logout-all -H "Authorization: Bearer $ACCESS"
# {"message": "Logged out everywhere."}

# change password (needs the access token)
curl -s -X POST $API/auth/change-password -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"current_password":"first-password-123","new_password":"second-password-456"}'
# {"message": "Password changed. Sign in again."}
```

- `change-password` revokes **all** refresh tokens, so after a 200 send the user to the login page. A wrong `current_password` is 401 `Invalid email or password.` and counts as a failed login (five in a row lock the account). A new password that is too short, contains the email, or equals the current one is 400, with a message you can show.
- `logout-all` works even when the user's SACCO is suspended.
- After logout-all or a password change, **every access token issued before it stops working at once** (401 `Invalid or expired token.`), including the one that made the call. Clear the tokens on the client and send the user to the login page.

### Verifying an email address

`register` emails a link (valid 24 hours) to the address. The link should open a frontend page that reads `token` from the URL and calls:

```bash
curl -s -X POST $API/auth/verify-email -H "Content-Type: application/json" \
  -d '{"token":"<token from the link>"}'
# {"message": "Email verified."}   (400 if the link is wrong, used or expired)

curl -s -X POST $API/auth/resend-verification -H "Content-Type: application/json" \
  -d '{"email":"sam@example.com"}'
# Always 200, whether or not the address exists, so it cannot be used to find accounts.
```

- Login does **not** need a verified address. What needs it: a SACCO admin can only add a user who has verified their email (otherwise 409 `That user has not verified their email yet.`). Tell new users to verify before asking an admin to add them.
- Changing the email with `PATCH /members/me` marks the new address unverified, emails a new link and **ends every session** (the response is 200, but the old tokens are dead: send the user to login).
- Locally the link is printed in the API's log (`MAIL_BACKEND=log`); seeded users are already verified. `FRONTEND_URL` in `backend/.env` sets where the link points.

### Forgot password

```bash
curl -s -X POST $API/auth/forgot-password -H "Content-Type: application/json" \
  -d '{"email":"sam@example.com"}'
# Always 200 {"message": "If that address has an account, a reset link was sent."}

curl -s -X POST $API/auth/reset-password -H "Content-Type: application/json" \
  -d '{"token":"<token from the link>","new_password":"a-new-passphrase"}'
# 200 {"message": "Password reset. Sign in with the new password."}
```

- The link (valid 1 hour, works once) points to `FRONTEND_URL/reset-password?token=...`. Build that page: read `token`, ask for a new password, call `reset-password`, then send the user to login.
- A weak password is 400 with a message and the link still works. A used, wrong or expired link is 400.
- A reset ends every session, clears a lockout and verifies the email. **This is the way back for a user locked out by repeated wrong passwords**, so show a "Forgot password?" link on the 423 lock message.

### What 401, 423 and 429 mean

| Status | On a normal call | On login / change-password |
|---|---|---|
| **401** | Access token missing, expired or invalid. Refresh once, then retry; if refresh fails, go to login. | Wrong email or password (same message for both). |
| **423** | The user's SACCO is **suspended**: `This SACCO account is suspended. Contact the platform owner.` Show that message; refreshing will not help. | Either the SACCO is suspended (same message), or the account is **locked**: `Account temporarily locked. Try again later.` Five wrong passwords lock it for 15 minutes, even for the right password. |
| **429** | Rate limit. Wait and try again. | **5 requests per minute per IP** on login, register and change-password; 120/min on reads, 30/min on ordinary writes, 20/min on deposits, withdrawals and reversals. Body: `{"error": {"code": "rate_limited", "message": "Too many requests. Try again later."}}`. A parallel login for the same account can also answer 429 (`Another attempt is in progress…`). |

While developing, avoid logging in on every page reload or hot reload: five logins a minute is all you get. Log in once and keep the tokens.

## 4. Conventions

**Error format.** Every error, on every route, has this body. Branch on `code` (or the HTTP status), show `message`:

```json
{"error": {"code": "validation_error", "message": "amount must be a whole number of minor units."}}
```

| Status | `code` |
|---|---|
| 400 | `validation_error` |
| 401 | `unauthorized` |
| 403 | `forbidden` |
| 404 | `not_found` |
| 405 | `method_not_allowed` |
| 409 | `conflict` |
| 413 | `payload_too_large` |
| 423 | `locked` |
| 429 | `rate_limited` |
| 500 | `internal_error` |

Successful responses have no envelope: you get the resource (or a named list such as `{"accounts": [...]}`) directly.

| Status | Meaning here |
|---|---|
| 200 | OK. Also: a money retry that returned the original entry. |
| 201 | Created (register, open account, a new deposit / withdrawal / reversal). |
| 400 | Invalid input: missing field, wrong type, bad page number, weak password. All validation errors are 400 (we do not use 422). |
| 401 | Not signed in, token expired, or wrong credentials. |
| 403 | Signed in but not allowed: wrong role, or inactive membership. A member posting a deposit gets this. |
| 404 | Not found, **or not yours**. Another SACCO's data and another member's account also answer 404, on purpose. |
| 409 | Conflict with current state: email taken, `Insufficient funds.`, reference reused for a different request, reversing something already reversed. |
| 423 | Locked or suspended (see above). |
| 429 | Too many requests. |
| 500 | Server bug. Body is `{"error": {"code": "internal_error", "message": "Internal error."}}`. |

**Pagination.** List endpoints take `?page=1&per_page=20`. `page` starts at 1, `per_page` defaults to 20 and is capped at 100. A zero, negative or non-numeric value is 400. Responses repeat `page` and `per_page`; most also return `total` (`member-activity` does not, so keep paging until a page comes back shorter than `per_page`).

**Money is an integer in minor units.** The currency is KES (the SACCO's `currency` field) and **100 = 1.00**, so `4000` is KES 40.00. Never send or expect decimals: `10.5` is rejected with 400. Convert only for display, for example `(amount / 100).toFixed(2)`. One transaction is capped at 100000000 (1,000,000.00).

**Dates** are ISO 8601 strings in UTC (`2026-11-14T15:54:28.133764+00:00`). Report filters use plain dates: `?from=2026-01-01&to=2026-01-31`.

**Caching.** Responses carry `Cache-Control: no-store`.

## 5. Idempotency and safe retries

Every deposit, withdrawal and reversal accepts a `reference`: your idempotency key. It is unique per SACCO, 1 to 64 characters from letters, digits and `. _ : -`. **It is required**: a deposit, withdrawal or reversal without one is 400 `reference is required.`, because a retry could not be made safe.

Make one reference per user action (for example `crypto.randomUUID()`), and keep it for the life of that action, including every retry.

```bash
curl -s -X POST $API/savings/accounts/3/deposits \
  -H "Authorization: Bearer $ADMIN_ACCESS" -H "Content-Type: application/json" \
  -d '{"amount":2500,"reference":"demo-dep-001"}'
```
```json
{"account_id": 3, "amount": 2500, "balance": 4000, "created_at": "2026-11-14T15:56:54.254744+00:00",
 "id": 15, "reference": "demo-dep-001", "replayed": false, "type": "deposit"}
```
Status **201**. Send the exact same request again (a retry after a timeout):

```json
{"account_id": 3, "amount": 2500, "balance": 4000, "created_at": "2026-11-14T15:56:54.254744+00:00",
 "id": 15, "reference": "demo-dep-001", "replayed": true, "type": "deposit"}
```
Status **200**, `"replayed": true`, same `id`, no second deposit. How to handle the outcomes:

| You get | It means | Do |
|---|---|---|
| 201 | Posted just now | Show success. |
| 200 with `replayed: true` | Already posted by an earlier attempt | Show success. Do not add it twice to your UI. |
| 409 `That reference was already used for a different request.` | Same reference, different amount or account | You changed the request. Use a new reference for a new action. |
| 409 `Insufficient funds.` | Withdrawal larger than the balance | Show the message. A new attempt needs a new reference. |
| Timeout, network error, 5xx | You do not know if it posted | **Retry the identical request with the same reference.** |

Do not retry blindly on 4xx: fix the request first.

Reversals work the same way: `POST /savings/transactions/<id>/reversals` with `{"reference": "..."}`. A reversal is a new opposite entry; an entry can be reversed once and a reversal cannot be reversed (409). Only admins and staff can post money or reversals, and **nobody can post or reverse on their own account** (403 `You cannot post money on your own account.`).

## 6. Dashboard recipes

All examples use the seeded data. After login, make the calls in this order.

### Member dashboard (`alpha-m1@example.com`)

**Step 0: log in** (section 3) and set `ACCESS`.

**Step 1: who am I.** Gives the role and SACCO ids.

```bash
curl -s $API/members/me -H "Authorization: Bearer $ACCESS"
```
```json
{
  "created_at": "2026-11-14T15:54:27.898525+00:00",
  "email": "alpha-m1@example.com",
  "id": 4,
  "memberships": [
    {"membership_id": 3, "role": "member", "sacco_id": 1, "status": "active"}
  ]
}
```

**Step 2: my accounts.** Only accounts from active memberships in active SACCOs.

```bash
curl -s $API/savings/accounts/me -H "Authorization: Bearer $ACCESS"
```
```json
{
  "accounts": [
    {"balance": 4000, "created_at": "2026-11-14T15:54:28.095991+00:00",
     "id": 1, "membership_id": 3, "sacco_id": 1}
  ]
}
```
`balance` 4000 is KES 40.00. A user with no accounts gets `{"accounts": []}`: show an empty state.

**Step 3: history for an account.** Use the account `id` from step 2. Newest first.

```bash
curl -s "$API/savings/accounts/1/transactions?page=1&per_page=20" -H "Authorization: Bearer $ACCESS"
```
```json
{
  "page": 1,
  "per_page": 20,
  "total": 4,
  "transactions": [
    {"amount": 2000, "created_at": "2026-11-14T15:54:28.556524+00:00", "id": 7,
     "reference": "seed-alpha-m1-rev-1", "reverses_id": 2, "type": "withdrawal"},
    {"amount": 1000, "created_at": "2026-11-14T15:54:28.133764+00:00", "id": 3,
     "reference": "seed-alpha-m1-wd-1", "reverses_id": null, "type": "withdrawal"},
    {"amount": 2000, "created_at": "2026-11-14T15:54:28.124973+00:00", "id": 2,
     "reference": "seed-alpha-m1-dep-2", "reverses_id": null, "type": "deposit"},
    {"amount": 5000, "created_at": "2026-11-14T15:54:28.110065+00:00", "id": 1,
     "reference": "seed-alpha-m1-dep-1", "reverses_id": null, "type": "deposit"}
  ]
}
```
`type` is `deposit` or `withdrawal`. A row with `reverses_id` set is a **reversal**: it undoes the entry with that id (here entry 2, the second deposit). Show it as "Reversal of #2", and you can mark entry 2 as reversed. Balance check: 5000 + 2000 − 1000 − 2000 = 4000.

### SACCO admin dashboard (`alpha-admin@example.com`)

**Step 0: log in** as the admin and set `ACCESS`.

**Step 1: who am I.** Find the SACCO id.

```bash
curl -s $API/members/me -H "Authorization: Bearer $ACCESS"
```
```json
{
  "created_at": "2026-11-14T15:54:27.535647+00:00",
  "email": "alpha-admin@example.com",
  "id": 2,
  "memberships": [
    {"membership_id": 1, "role": "sacco_admin", "sacco_id": 1, "status": "active"}
  ]
}
```
Use `memberships[0].sacco_id` (here `1`) in the next calls.

**Step 2 (optional, admin and owner only): the SACCO's name and currency**, for the page header.

```bash
curl -s $API/saccos/1 -H "Authorization: Bearer $ACCESS"
```
```json
{"created_at": "2026-11-14T15:54:27.531535+00:00", "currency": "KES", "id": 1, "name": "Alpha SACCO", "status": "active"}
```
`staff` get 403 here; for staff take the currency from the SACCO list you already hold or show amounts without a symbol.

**Step 3: summary** (the headline numbers). Optional `?from=YYYY-MM-DD&to=YYYY-MM-DD` limits the deposit and withdrawal totals.

```bash
curl -s $API/admin/saccos/1/reports/summary -H "Authorization: Bearer $ACCESS"
```
```json
{"account_count": 3, "deposit_total": 9500, "from": null, "reversal_count": 1,
 "sacco_id": 1, "to": null, "total_balance": 8000, "withdrawal_total": 1500}
```
`total_balance` is the sum of all member balances right now. `deposit_total` and `withdrawal_total` leave out reversed entries and the reversals themselves, so they show what stood. `reversal_count` counts reversals separately.

**Step 4: member activity** (who is active).

```bash
curl -s "$API/admin/saccos/1/reports/member-activity?page=1&per_page=20" -H "Authorization: Bearer $ACCESS"
```
```json
{"members": [
   {"account_id": 1, "email": "alpha-m1@example.com", "last_transaction_at": "2026-11-14T15:54:28.556524+00:00", "membership_id": 3, "transaction_count": 4},
   {"account_id": 2, "email": "alpha-m2@example.com", "last_transaction_at": "2026-11-14T15:54:28.343337+00:00", "membership_id": 4, "transaction_count": 2},
   {"account_id": 3, "email": "alpha-m3@example.com", "last_transaction_at": "2026-11-14T15:54:28.548563+00:00", "membership_id": 5, "transaction_count": 1}
 ], "page": 1, "per_page": 20}
```
`last_transaction_at` is `null` for an account with no transactions.

**Step 5: account list** (balances per member).

```bash
curl -s "$API/admin/saccos/1/accounts?page=1&per_page=20" -H "Authorization: Bearer $ACCESS"
```
```json
{"accounts": [
   {"account_id": 1, "balance": 4000, "email": "alpha-m1@example.com", "membership_id": 3},
   {"account_id": 2, "balance": 2500, "email": "alpha-m2@example.com", "membership_id": 4},
   {"account_id": 3, "balance": 1500, "email": "alpha-m3@example.com", "membership_id": 5}
 ], "page": 1, "per_page": 20, "total": 3}
```
To open one member's history, use `GET /savings/accounts/<account_id>/transactions` (as in the member recipe): admins and staff can read any account in their SACCO.

Steps 3 to 5 also work for `staff`. A member calling them gets 403.

### Platform owner (`owner@example.com`)

The owner has no memberships (`"memberships": []`). List the SACCOs, then use each `id` in the admin calls above (the owner may open any SACCO):

```bash
curl -s $API/saccos -H "Authorization: Bearer $ACCESS"
```
```json
{"saccos": [
   {"created_at": "2026-11-14T15:54:27.531535+00:00", "currency": "KES", "id": 1, "name": "Alpha SACCO", "status": "active"},
   {"created_at": "2026-11-14T15:54:28.564941+00:00", "currency": "KES", "id": 2, "name": "Beta SACCO", "status": "active"}
 ]}
```

### Other things you will see

- A suspended SACCO: login and refresh answer 423 for its users, and its admin calls answer 423. The platform owner is never blocked, and reactivates with `POST /saccos/<id>/activate`.
- Another SACCO's id, or another member's account id: 404.

## 7. CORS

The API answers cross-origin browser calls only for origins listed in the `CORS_ORIGINS` setting in `backend/.env`: a comma-separated list of exact origins, for example:

```
CORS_ORIGINS=http://localhost:5173
```

- Default is empty: no cross-origin access. Restart the API after changing it.
- The origin must match exactly (scheme, host, port). `*` is never sent, and the API refuses to start in production if the list contains `*`.
- Allowed methods: `GET, POST, PATCH, OPTIONS`. Allowed request headers: `Authorization, Content-Type`. Preflight answers are cached for 600 seconds.
- Credentials are off: send the token in the `Authorization` header, not in cookies. Do not set `credentials: 'include'`.
- Every `/api/` response carries `Cache-Control: no-store`, so do not rely on browser caching of API data.

## 8. Endpoint list

All paths are under `/api/v1` unless noted. "Auth" is a Bearer access token.

| Method and path | Who | Purpose |
|---|---|---|
| `GET /api/health` (no `/v1`) | anyone | API and database status |
| `POST /auth/register` | anyone | Create a user and email a verification link |
| `POST /auth/verify-email` | anyone | Confirm an address with the emailed token |
| `POST /auth/resend-verification` | anyone | Send a new link (always 200) |
| `POST /auth/forgot-password` | anyone | Email a reset link (always 200) |
| `POST /auth/reset-password` | anyone | Set a new password from the emailed token |
| `POST /auth/login` | anyone | Get tokens |
| `POST /auth/refresh` | refresh token | Rotate tokens |
| `POST /auth/logout` | refresh token | Revoke one refresh token |
| `POST /auth/logout-all` | signed in | Revoke all refresh tokens |
| `POST /auth/change-password` | signed in | Change own password |
| `GET`, `PATCH /members/me` | signed in | Own profile (PATCH changes email, needs `current_password`) |
| `GET`, `POST /saccos` | owner | List, create SACCOs |
| `GET`, `PATCH /saccos/<id>` | owner, that SACCO's admin | Read, rename |
| `POST /saccos/<id>/activate`, `/deactivate` | owner | Suspend or reactivate |
| `GET`, `POST /saccos/<id>/members` | owner, that SACCO's admin | List, add members |
| `GET`, `PATCH /saccos/<id>/members/<membership_id>` | owner, that SACCO's admin | Read, update a member |
| `POST /savings/accounts` | admin, staff | Open an account (`{"membership_id": n}`) |
| `GET /savings/accounts/me` | signed in | Own accounts |
| `GET /savings/accounts/<id>` | owner, admin, staff, the holder | One account |
| `GET /savings/accounts/<id>/transactions` | same | History, paged |
| `POST /savings/accounts/<id>/deposits`, `/withdrawals` | admin, staff | Post money (`amount`, `reference`) |
| `POST /savings/transactions/<id>/reversals` | admin, staff | Reverse an entry (`reference`) |
| `GET /admin/saccos/<id>/reports/summary` | owner, admin, staff | Totals |
| `GET /admin/saccos/<id>/reports/member-activity` | owner, admin, staff | Activity per member |
| `GET /admin/saccos/<id>/accounts` | owner, admin, staff | Accounts and balances |
| `GET /admin/saccos/<id>/audit` | owner, admin | SACCO audit log |
| `GET /admin/audit` | owner | Platform audit log |

The machine-readable version is [`openapi.yaml`](openapi.yaml).
