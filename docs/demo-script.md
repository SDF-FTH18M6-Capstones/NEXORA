# Demo script

A rehearsal script for the 5-minute backend demo. Setup, the seeded accounts and the talking points are in [`demo.md`](demo.md); this file is the order to follow and what each step must show. `backend/scripts/demo.sh` runs steps 2 to 5 for you and prints the real responses.

## 0. Before you start

```bash
cd backend && flask --app app db upgrade && cd ..
python backend/scripts/seed.py            # safe to run twice; refuses a database not ending in _dev
cd backend && python app.py               # API on http://localhost:5000
curl http://localhost:5000/api/health     # {"database":"connected","status":"healthy"}
```

All seeded users share the password `Dev-Seed-Pass-2026`. Logins used below:

| Role | Login |
|---|---|
| Platform owner | `owner@example.com` |
| SACCO admin (Alpha) | `alpha-admin@example.com` |
| Finance officer (Alpha) | `alpha-finance@example.com` |
| Member (Alpha) | `alpha-m1@example.com` |
| Admin of the other SACCO | `beta-admin@example.com` |

Login is limited to 5 per minute per IP: wait a minute between full runs.

## 1. Screens in order, per role

1. **Platform owner**: `GET /api/v1/saccos` (all SACCOs), `GET /api/v1/admin/audit`. Expect 200.
2. **SACCO admin**: `GET /api/v1/admin/saccos/1/reports/summary`, `GET /api/v1/admin/saccos/1/accounts`, `GET /api/v1/saccos/1/members`. Expect 200.
3. **Finance officer**: posts money (step 2 below).
4. **Member**: `GET /api/v1/savings/accounts/me`, then `GET /api/v1/savings/accounts/1/transactions`. Expect 200, and only their own account.

## 2. Money flow: deposit, withdraw, reverse

| Step | Request (as finance officer) | Expect |
|---|---|---|
| Deposit | `POST /api/v1/savings/accounts/1/deposits` `{"amount":2500,"reference":"demo-1"}` | **201**, `balance` rises by 2500 |
| Safe retry | the same request again | **200**, `replayed: true`, no second deposit |
| Withdraw | `POST /api/v1/savings/accounts/1/withdrawals` `{"amount":1000,"reference":"demo-2"}` | **201** |
| Reverse | `POST /api/v1/savings/transactions/<id of demo-2>/reversals` `{"reference":"demo-3"}` | **201**, a new opposite entry; the original row is untouched |
| Reverse again | same transaction, new reference | **409** (a row is reversed once) |

Say: amounts are integers in minor units, the balance comes from the ledger, and a correction is a new row, never an edit.

## 3. Failure and security cases (show at least these)

| Case | Request | Expect |
|---|---|---|
| Overdraw | withdrawal of `99000000` | **409** |
| No idempotency key | deposit with no `reference` | **400** |
| Wrong role | member `POST .../deposits` | **403** |
| Other SACCO | `alpha-admin` calls `GET /api/v1/admin/saccos/2/reports/summary` | **404**, never 403 |
| No token | `GET /api/v1/members/me` with no header | **401**, same error shape |
| Rate limit | 6 bad logins in a minute from one IP | the 6th is **429** (the account itself locks for 15 minutes after 5 wrong passwords: **423**) |
| Session revoked | `POST /api/v1/auth/logout-all`, then reuse the access token | **401** |

## 4. End-of-day status (new)

```bash
cd backend && flask --app app eod-status --sacco-id 1
```

Prints `<n> entries; mismatches=0` and exits 0. With `MAIL_BACKEND=log` the email to the members who can read the SACCO's reports appears in the log. Exit code 1 means a stored balance disagrees with its ledger; the email names the account.

## 5. Fallback if something is down

- **Database down**: `GET /api/health` shows `disconnected`. Start PostgreSQL, then continue; no data is lost because every write is committed. If it will not start, show the test run instead: `pytest -m "schema or not schema" --cov` (785 tests, 95% coverage) and `ruff check backend/app tests`.
- **Network or laptop Wi-Fi down**: everything runs on `localhost`. If the API port is taken, start it on another port and run `API=http://localhost:5077 bash backend/scripts/demo.sh`.
- **Seed data missing or changed**: rerun `python backend/scripts/seed.py`.
- **API will not start at all**: walk `docs/openapi.yaml` or `docs/api.md` and the screenshots of a previous run of `demo.sh`; save that output before the demo.
