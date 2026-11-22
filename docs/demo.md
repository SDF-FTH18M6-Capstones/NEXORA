# Running and showing the backend

## 1. One-time setup

You need PostgreSQL running and Python 3.12+. From the repo root:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env       # then edit it (below)
```

In `backend/.env` set:

- `SECRET_KEY`: 32 or more random characters. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `DATABASE_URL=postgresql+psycopg://<user>:<password>@localhost:5432/nexora_dev`. The seed script only runs against a database whose name ends in `_dev`.
- `CORS_ORIGINS=http://localhost:5173` if the React app will call it.

Create the databases (the password prompt is for the `postgres` superuser; `-h 127.0.0.1` forces password login instead of peer login):

```bash
psql -h 127.0.0.1 -U postgres -c "CREATE DATABASE nexora_dev;"
psql -h 127.0.0.1 -U postgres -c "CREATE DATABASE nexora_test;"
psql -h 127.0.0.1 -U postgres -c "CREATE DATABASE nexora_schema_test;"
```

If your app role is not `postgres`, add `OWNER <role>` to each statement.

## 2. Start it

```bash
cd backend
flask --app app db upgrade                  # creates the tables (migrations 0001 to 0021)
cd .. && python backend/scripts/seed.py     # demo data; safe to run twice
cd backend && python app.py                 # API on http://localhost:5000
```

Check it: `curl http://localhost:5000/api/health` should print `{"database":"connected","status":"healthy"}`.

The seed prints every seeded email. All of them share the password `Dev-Seed-Pass-2026` and the SACCO PIN `2468` (the React app asks for the PIN after sign-in):

| Who | Email | Role |
|---|---|---|
| Platform owners | `owner@example.com`, `owner2@example.com` | run the whole platform (at least two must always remain) |
| Alpha admin | `alpha-admin@example.com` | admin of Alpha SACCO |
| Alpha secretary | `alpha-staff@example.com` | secretary: reads members, accounts, reports and the audit log; cannot move money |
| Alpha loans officers | `alpha-loans@example.com`, `alpha-loans2@example.com` | approve loan steps (one step each) |
| Alpha finance officer | `alpha-finance@example.com` | posts money, disburses loans |
| Alpha members | `alpha-m1@example.com` to `alpha-m3@example.com` | savers |
| Beta SACCO | `beta-admin@example.com`, `beta-staff@example.com`, `beta-loans@example.com`, `beta-loans2@example.com`, `beta-finance@example.com`, `beta-m1..m3@example.com` | a second SACCO, for the isolation demo |

## 3. Show it (5 minutes)

With the API running, in a second terminal:

```bash
bash backend/scripts/demo.sh
```

It logs in as four users and walks through, with the real responses printed: the admin dashboard, the member dashboard, a deposit and its safe retry, the refusals (wrong role, another SACCO, no token), logout-all killing a session, and registration with password recovery. Login is limited to 5 per minute per address, so wait a minute before running it twice.

For the interactive API reference, paste `docs/openapi.yaml` into <https://editor.swagger.io>. All 59 operations (49 paths) are there with request bodies, responses and error codes.

To click through the whole API, including the loan flow, use Thunder Client: [`docs/thunder-client.md`](thunder-client.md).

To show the tests: `pytest -m "schema or not schema" --cov` (785 tests, 95% coverage), and `ruff check backend/app tests`.

## 4. Who built what

| Person | Built |
|---|---|
| **Neo** | CI with coverage, CORS, security headers, rate limits on every route, production startup guards |
| **Ryan** | Seed script, savings read endpoints (account, balance, my accounts, SACCO account list), audit-log endpoints, OpenAPI spec |
| **Sam** | change-password and logout-all, README, architecture doc, frontend handoff note |
| **Collins** | The single error format on every route, access-token revocation, email verification, forgot and reset password, own-account rule, the red-team passes and their fixes |

Moves 1 to 3 (auth and rotating refresh tokens, SACCOs and members, tenant isolation, the append-only ledger with trigger-maintained balances, reversals, audit log, reports) were built by the whole team; the history is in `git log`.

## 5. Talking points

- **Money is safe:** amounts are integers in minor units, every deposit needs an idempotency `reference` (a retry never posts twice), balances come from the ledger, and a reversal is a new opposite entry that can happen once.
- **Tenants cannot see each other:** another SACCO's record answers 404, never 403, so ids cannot be probed.
- **Sessions are real:** 15 minute access tokens that die instantly on logout-all, password change, reset or email change; rotating refresh tokens with theft detection; lockout after 5 wrong passwords.
- **It was attacked before it shipped:** four red-team passes found and fixed the issues listed in `docs/architecture.md`; the decisions we accepted are written there too.
- **A frontend developer can start from `docs/frontend-handoff.md` alone.**
