# NEXORA Backend: Remaining Work Plan

Status: **Superseded (2026-11-18).** Moves 1 to 6 are done. What is left is tracked as GitHub issues (#87 to #99, #30) and in `docs/security-checklist.md`. This file is kept as the original proposal.

## 1. Purpose

This document lists what is left in the Flask backend, splits it across the team by Move, and sets the order we work in. Every team member has a part in each Move.

## 2. Team

| Name   | Role in this plan                                        |
|--------|----------------------------------------------------------|
| Collins | Integration lead, financial ledger and reversals, merges |
| Ryan   | SACCO and membership management                          |
| Neo    | Member access, authorization and API tests               |
| Sam    | Savings accounts and transaction flows                   |
| TBD    | Fifth team member slot (confirm name, or leave open)     |

## 3. Where we are

| Move | Scope | Status |
|------|-------|--------|
| Move 1 | Project skeleton, Flask factory, health check | Done |
| Move 2 | SACCO and member routes: SACCO create/list/activate/deactivate (Ryan), member endpoints (Neo), tenant guard, SACCO detail/PATCH and audit (Collins), member self-service `/members/me` (Sam) | Done. All merged to `development` (PRs #62 to #66); 340 tests pass |
| Note | Move numbers in this table were drafted before the team's real Move 2. The SACCO and member work listed under "Move 4" below is already done, and savings (Sam, PR #58) is already merged. Re-number Moves 3 to 6 before the team signs off. | |
| Move 3 | Auth: register, login, rotating refresh tokens, logout, lockout, rate limits, suspended-SACCO block | Done |
| Move 4 | SACCO and member routes | Not started (`saccos` blueprint is an empty stub) |
| Move 5 | Savings, transactions, admin and reporting routes | Not started (`savings` and `admin` blueprints are empty stubs) |
| Move 6 | Integration, hardening and handoff to the frontend | Not started |

Moves 4 to 6 are not defined in the repository yet. The scope above is a proposal. Confirm or change it in section 8.

## 4. Clear these blockers first

These block Move 4 and should be done before new feature work starts.

1. **Fix the app entrypoint (Collins).** `backend/app.py` is still the old skeleton. It creates its own Flask app with only `/api/health` and never calls `create_app()`, so the auth routes are not served when the app is started that way. Point the entrypoint at the factory and keep `/api/health` working.
2. **Merge the schema work (Collins).** Open a PR for `fix/schema-integrity` into `development`. Two people review it, and migrations 0004 to 0006 are run on a fresh `nexora_dev` database.
3. **Make the test suite green on everyone's machine (Neo).** The project `.venv` does not work on Windows as committed. Recreate it, pin the test dependencies in `requirements.txt`, and confirm `pytest` passes.
4. **Decide the URL prefix (whole team).** The blueprints mount at `/auth`, `/saccos`, `/savings` and `/admin`. `docs/api-conventions.md` proposes `/api/v1/...`. Pick one, record it in section 8, and update the blueprints and the health check to match.

Done when: the factory serves all routes, the migrations run on a clean database, and `pytest` passes on every laptop.

## 5. Work by Move

### Move 4: SACCOs and members

Owners: **Ryan** (lead), **Neo** (member access)

- [ ] `POST /saccos` and `GET /saccos` for Platform Owner, with name and account uniqueness enforced by the database.
- [ ] `GET /saccos/<id>` and `PATCH /saccos/<id>` for the Platform Owner and that SACCO's admin.
- [ ] Activate and deactivate a SACCO (Platform Owner only).
- [ ] Member endpoints: list, get, add, and update members within one SACCO.
- [ ] Enforce SACCO-level isolation on every query. A SACCO admin must never see another SACCO's records.
- [ ] Member self-service: a member can read and update only their own profile.
- [ ] Tests for each role and for cross-SACCO access attempts (Neo writes these with Ryan).

Done when: every endpoint has a role test and a cross-SACCO test that returns 403 or 404.

### Move 5: Savings, transactions and admin

Owners: **Sam** (lead, savings and transactions), **Collins** (ledger, reversals, audit)

- [ ] Open a savings account for a member.
- [ ] Deposit and withdrawal endpoints. Each runs in one database transaction and writes to the ledger.
- [ ] Balances come from the ledger, never from a stored total that is edited directly.
- [ ] Money is stored as integer minor units. No floats anywhere in the request or response path.
- [ ] Reversal endpoint. Historical transactions are never edited. Corrections are new reversal entries.
- [ ] Transaction history endpoint with pagination, with each member limited to their own history.
- [ ] Append-only audit log entry for every financial action, recording the actor.
- [ ] Admin endpoints: SACCO reports and monitoring of member activity, scoped to the admin's SACCO.
- [ ] Tests for double-spend, concurrent withdrawals, reversal of a reversal, and currency mismatch.

Done when: a balance can be reproduced from the ledger alone, and the concurrency tests pass.

### Move 6: Integration and hardening

Owners: **Collins** (lead), **Neo** (CI and tests), everyone (review)

- [ ] Consistent response envelope and error format, as agreed in `docs/api-conventions.md`.
- [ ] Validation errors return a single agreed status code.
- [ ] OpenAPI or a route list kept up to date, so the frontend team can build against it.
- [ ] Rate limits and lockout reviewed across all new routes.
- [ ] CI runs `pytest` and `ruff` on every PR.
- [ ] Seed script for local test data (one platform owner, two SACCOs, admins and members).
- [ ] Update the README status checklist and `docs/architecture.md`, which still lists auth and migration decisions as open.
- [ ] Frontend handoff: a short note listing endpoints, auth flow, and example requests.

Done when: CI is green on `development` and the frontend can log in and load a SACCO dashboard against the local API.

## 6. Working agreements

- Branch per person per Move, named `move-<n>/<name>` (for example `move-4/ryan`).
- Pull before starting work and before pushing.
- Every PR has one reviewer from another person in the team. No one merges their own PR.
- Changes to shared files (`app/__init__.py`, `config.py`, migrations, `docs/`) are agreed in the team chat before the PR is opened.
- Do not add a migration without saying so in the PR title.
- A feature is not done until its tests pass on `development`.

## 7. Order of work

1. Blockers in section 4 (Collins, Neo, whole team).
2. Move 4 and Move 5 in parallel. Move 5 depends on the membership model from Move 4 being merged first, so Sam starts with the ledger and savings models while Ryan finishes the SACCO and member routes.
3. Move 6 starts once Moves 4 and 5 are merged to `development`.

## 8. Decisions for the team

- [ ] Fifth team member: who is it, or do we work with four?
- [ ] URL prefix: `/api/v1` or `/api`?
- [ ] Moves 4 to 6: accept this split, or change it?
- [ ] Can a user belong to more than one SACCO? (Open in `docs/database-schema.md`.)
- [ ] Are savings and loans separate account entities? (Open in `docs/database-schema.md`.)
- [ ] Validation error status: 422 or 400? (Open in `docs/api-conventions.md`.)

## 9. Approval

Each person marks their agreement with the plan and their owned items.

| Name    | Agreed | Notes |
|---------|--------|-------|
| Collins | [ ]    |       |
| Ryan    | [ ]    |       |
| Neo     | [ ]    |       |
| Sam     | [ ]    |       |
| TBD     | [ ]    |       |
