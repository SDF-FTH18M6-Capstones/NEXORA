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
git checkout -b feature/sam-project-skeleton
```

Make sure your Git identity is set:

```bash
git config user.name "Your Name"
git config user.email "you@example.com"
```

### 2. Database

Create the development database (Name: nexora_dev):

```bash
psql -U postgres -c "CREATE DATABASE nexora_dev;"
```

### 3. Backend

```bash
cd backend
python3 -m venv venv
source venv/Scripts/activate      # Windows (Git Bash)
# source venv/bin/activate        # macOS / Linux
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` and replace `YOUR_PASSWORD` with your local PostgreSQL password:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/nexora_dev
FLASK_DEBUG=1
```

Run the API:

```bash
python app.py
```

The API runs on <http://localhost:5000>.

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
| `DATABASE_URL` | backend  | PostgreSQL connection string         |
| `FLASK_DEBUG`  | backend  | `1` enables Flask debug mode         |

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
| `npm error Missing script: "lint"` | You're in the wrong folder. Run it from `frontend/` |

## Status

- [x] Repository cloned, feature branches created
- [x] Flask skeleton with `/api/health` endpoint
- [x] React + Vite skeleton
- [x] PostgreSQL connection verified
- [ ] Frontend connected to backend (planned for Day 2)