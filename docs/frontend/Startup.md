# Start NEXORA locally (WSL Ubuntu)

Run each block in its own terminal. Paths assume the repo is at `~/projects/NEXORA`.

## One-time setup (skip if already done)

```bash
cd ~/projects/NEXORA

# Postgres password for docker compose (repo root .env)
echo "POSTGRES_PASSWORD=yourpassword" >> .env

# Backend settings
cp backend/.env.example backend/.env
# In backend/.env make sure:
#   DATABASE_URL and TEST_DATABASE_URL use the same user and password as compose
#   (compose default user is "nexora"), with the postgresql+psycopg:// prefix
#   CORS_ORIGINS=http://localhost:5173
```

```bash
# Python environment
cd ~/projects/NEXORA/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend packages
cd ~/projects/NEXORA/frontend
npm install
```

## Every time: start the backend (terminal 1)

```bash
cd ~/projects/NEXORA
docker compose up -d db
docker compose ps                  # wait until the db shows "healthy"

cd backend
source venv/bin/activate
flask --app app db upgrade         # apply migrations (safe to repeat)
python app.py                      # API on http://localhost:5000
```

Check it: `curl -s http://localhost:5000/api/health`
Expected: `{"database":"connected","status":"healthy"}`

Restart `python app.py` after any change to `backend/.env`.

## Every time: start the frontend (terminal 2)

```bash
cd ~/projects/NEXORA/frontend
npm run dev                        # app on http://localhost:5173
```

Open `http://localhost:5173/` (use `localhost`, not `127.0.0.1`).
The component harness with sample data is at `http://localhost:5173/dev.html`.

## One-time: seed demo data

```bash
cd ~/projects/NEXORA
source backend/venv/bin/activate
python backend/scripts/seed.py
```

Every seeded user's password is `Dev-Seed-Pass-2026`.
Useful logins: `alpha-admin@example.com`, `alpha-finance@example.com`,
`alpha-m1@example.com`, `owner@example.com`.

## One-time: give seeded memberships a SACCO PIN (development only)

After signing in, the app asks for a four-digit SACCO PIN, and the seed does not set one.

```bash
cd ~/projects/NEXORA/backend
source venv/bin/activate
flask --app app shell
```

At the `>>>` prompt:

```python
from app.extensions import db
from app.models.membership import SaccoMembership
from app.auth.pin import set_pin
for m in db.session.query(SaccoMembership).all():
    set_pin(m, "1234")

db.session.commit()
exit()
```

Then sign in with a seeded email and password, and enter PIN `1234`.

## Tests and checks

```bash
# Backend (from backend/, venv active)
pytest -m "schema or not schema"

# Frontend (from frontend/)
npx eslint src
npm run build
```

## Stop everything

```bash
# Ctrl+C in each terminal, then:
cd ~/projects/NEXORA && docker compose down      # add -v to also wipe the database
```

## Quick fixes

| Symptom | Fix |
|---|---|
| Browser says "blocked by CORS policy" | Set `CORS_ORIGINS=http://localhost:5173` in `backend/.env`, restart `python app.py` |
| "Something went wrong on our side" on sign-in | Make sure `frontend/src/api/session.js` has the `withJobTitles` fix |
| "No PIN has been set" on the SACCO screen | Run the PIN step above |
| Blank page and "Throttling navigation" warning | DevTools, Application, Clear site data, then reload |
| Backend cannot connect to the database | `docker compose ps`, wait for `healthy`, check `DATABASE_URL` |
| Port 5000 or 5173 already in use | Stop the old process, or find it with `lsof -i :5000` |