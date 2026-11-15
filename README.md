# NEXORA

One shared SACCO management application

A full-stack web application built with **React**, **Flask** and **PostgreSQL**.

## Tech stack

| Layer     | Technology                                                                 |
|-----------|----------------------------------------------------------------------------|
| Frontend  | React 19 + Vite                                                            |
| Backend   | Flask (Python), Flask-SQLAlchemy, Flask-Migrate, psycopg 3, pytest, Ruff   |
| Database  | PostgreSQL 18                                                              |

## Repository structure

```
NEXORA/
├── backend/     # Flask API (app.py, requirements.txt, .env.example)
├── frontend/    # React + Vite app
├── docs/        # Architecture, API conventions, database schema, roles & permissions
├── .gitignore
└── README.md
```

Project documentation lives in [`docs/`](docs/):
[architecture](docs/architecture.md) ·
[API conventions](docs/api-conventions.md) ·
[database schema](docs/database-schema.md) ·
[roles & permissions](docs/roles-permissions.md)

## Prerequisites

- Git
- Python 3.11+
- Node.js 20+ and npm
- PostgreSQL 18 (the `psql` command must be on your PATH)

## Local setup

### 1. Clone and create your branch

```bash
git clone git@github.com:SDF-FTH18M6-Capstones/NEXORA.git
cd NEXORA
```

Make sure your Git identity is set:

```bash
git config user.name "Your Name"
git config user.email "you@example.com"
```

### 2. Database

Create the development and test databases (all three are needed to run the tests):

```bash
psql -U postgres -c "CREATE DATABASE nexora_dev;"
psql -U postgres -c "CREATE DATABASE nexora_test;"
psql -U postgres -c "CREATE DATABASE nexora_schema_test;"
```

If your app uses a non-superuser role, add `OWNER <that_role>` to each statement.

### 3. Backend

Requires **Python 3.12 or newer** (check with `python --version`).

```bash
cd backend
python3 -m venv venv
source venv/Scripts/activate      # Windows (Git Bash)
# source venv/bin/activate        # macOS / Linux
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env`: set `SECRET_KEY`, and replace `YOUR_PASSWORD` in `DATABASE_URL` and `TEST_DATABASE_URL` with your local PostgreSQL password. Keep the `postgresql+psycopg://` prefix (plain `postgresql://` makes SQLAlchemy look for the wrong driver, psycopg2).

```
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/nexora_dev
TEST_DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/nexora_test
```

Create the tables and load demo data (run from the repo root, with the virtualenv active):

```bash
cd backend && flask --app app db upgrade && cd ..
python backend/scripts/seed.py
```

`seed.py` refuses to run unless the database name ends in `_dev`, and it is safe to run twice. It prints the seeded emails and roles; every seeded user shares one fake development password, defined at the top of the script.

Run the API:

```bash
cd backend
python app.py
```

The API runs on <http://localhost:5000>. Frontend developers: see [`docs/frontend-handoff.md`](docs/frontend-handoff.md).

### Running the tests

From the repo root, with the virtualenv active:

```bash
pytest -m "schema or not schema"   # everything: what CI runs
ruff check backend/app tests       # lint
```

Plain `pytest` skips the schema tests (ledger, balances, reversals); `pytest -m schema` runs only those. The backend needs a database on `localhost`, so run the tests with `backend/.env` filled in.

The schema tests drop and rebuild their whole database, so they use their own
`<TEST_DATABASE_URL name minus _test>_schema_test` database (`nexora_schema_test`).
Create it once as shown in step 2.

### 4. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The app runs on <http://localhost:5173>.

## Smoke checks

| Check | Command / URL | Expected result |
|-------|---------------|-----------------|
| API + database | `curl -s http://localhost:5000/api/health` | `{"database":"connected","status":"healthy"}` |
| Missing config | Run the API without `.env` | `503` with `"database":"not_configured"` |
| Frontend | <http://localhost:5173> | Vite + React starter page loads |
| Lint | `cd frontend && npm run lint` | No errors |
| Build | `cd frontend && npm run build` | Build completes |

## Environment variables

Secrets are **never committed**. Only `.env.example` files are tracked; each developer copies them to a local `.env` (ignored by Git).

| Variable       | Where    | Description                          |
|----------------|----------|--------------------------------------|
| `SECRET_KEY`   | backend  | Token signing secret, 32+ random characters (the app refuses to start with less) |
| `DATABASE_URL` | backend  | PostgreSQL connection string         |
| `TEST_DATABASE_URL` | backend | Test database; name must end in `_test` |
| `TRUSTED_PROXIES` | backend | Number of reverse proxies in front (0 = none) |
| `RATELIMIT_STORAGE_URI` | backend | `memory://` locally, `redis://...` in production |
| `FLASK_DEBUG`  | backend  | `1` enables Flask debug mode         |
| `APP_ENV` | backend | `development` (default) or `production`. Production refuses to start with debug on, `memory://` rate limits, a short or placeholder `SECRET_KEY`, a `*` origin, or the `log` mail backend |
| `MAIL_BACKEND`, `MAIL_SERVER`, `MAIL_PORT`, `MAIL_FROM`, `MAIL_USERNAME`, `MAIL_PASSWORD` | backend | Verification email. `log` (default) prints the link in the server log; production needs `smtp` and `MAIL_SERVER` |
| `FRONTEND_URL` | backend | Where the verification link points (default `http://localhost:5173`) |
| `CORS_ORIGINS` | backend | Exact browser origins allowed to call the API, comma-separated (e.g. `http://localhost:5173`). Empty = no cross-origin access |

If your database password contains special characters (`@`, `#`, `/`, `:`), URL-encode them (for example `@` becomes `%40`).

## Git workflow

- Each developer works on their own `feature/<name>-...` branch.
- Run `git pull` before starting work and before pushing.
- Do not commit `.env`, `venv/` or `node_modules/`.
- Shared files (for example `App.jsx`, `vite.config.js`, `app.py`) are agreed with the team before changes.
- Tasks and blockers are tracked in GitHub Projects.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `psql: command not found` | Add `C:\Program Files\PostgreSQL\18\bin` to your PATH, then reopen the terminal |
| `password authentication failed` | The password in `.env` doesn't match your PostgreSQL `postgres` user password |
| Health check returns `disconnected` | Confirm PostgreSQL is running and `nexora_dev` exists |
| Tests hang, or fail with `canceling statement due to lock timeout` | Another connection has an open transaction on the test database (a killed earlier run, DBeaver, pgAdmin, `psql`). Find it: `SELECT pid, state, left(query,60) FROM pg_stat_activity WHERE datname='nexora_test';` then `SELECT pg_terminate_backend(<pid>);` for any `idle in transaction` row |
| `ImportError: cannot import name 'UTC'` | Python is older than 3.11. Install Python 3.12+ and recreate the virtualenv |
| `No module named 'psycopg2'` | `DATABASE_URL` / `TEST_DATABASE_URL` must start with `postgresql+psycopg://` |
| `Could not create database 'nexora_schema_test'` | Create it once: `psql -U postgres -c "CREATE DATABASE nexora_schema_test OWNER <your_role>;"` |
| `npm error Missing script: "lint"` | You're in the wrong folder. Run it from `frontend/` |

## Status

- [x] Move 1: project skeleton, schema, migrations
- [x] Move 2: auth (register, login, rotating refresh tokens, lockout), SACCOs, members, tenant guard
- [x] Move 3: savings accounts, deposits, withdrawals, reversals, ledger, audit log, admin reports
- [x] Move 4: security headers, CORS and rate limits, production checks, seed script, savings and audit read endpoints, change-password and logout-all
- [x] Move 4 hardening: one error format, access-token revocation, email verification, forgot-password, required `reference`, separation of duties
- [x] OpenAPI spec for every route (`docs/openapi.yaml`)
- [ ] Move 4 remainder: final sign-off
- [ ] Loans (waiting for the interest decision)
- [ ] Frontend connected to backend
