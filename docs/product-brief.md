# Product brief: NEXORA backend, presentation-ready

Status: **Signed by Collins, 2026-11-17.** Date: 2026-11-17. Demo: 2026-11-18.

## Problem

The team demos NEXORA tomorrow. The backend has auth, SACCOs, members, savings,
reversals, audit, join/PIN and loans merged on `development`, but:

- the loan flow cannot run on a migrated database (a model column with no
  migration answers 500 on every loan request);
- nobody can be made a loans officer or finance officer through the API, so the
  two-approval, third-officer-disburses rule cannot be shown;
- loan ledger rows could be reversed, which would undo loan money while the loan
  still says disbursed or repaid;
- the merge left lint red and seed re-runs broken;
- there is no way for the presenters to click through the API.

## Users

- Collins and the team, presenting the API live in Thunder Client.
- Reviewers (Moringa), who watch the requests and the refusals.

## Decisions (from the interview)

1. Retry rule: the exact same money request with the same `reference` answers
   200 with the original entry; the same `reference` with a different request
   answers 409 `DUPLICATE_REFERENCE`.
2. Departments: Engineering, QA/Security, Product. Design, Growth, R&D and Ops are
   skipped (no UI or users in scope).
3. Thunder Client native collection with an environment; logins save tokens and
   ids into variables automatically.
4. Ship: commit as Collins on `move-5/collins-finish`, push the branch, and hand
   over the compare link and PR text into `development`.

## Acceptance checklist (each item is proven by something that runs)

1. `pytest -m "schema or not schema"` has 0 failures, and `ruff check backend/app tests backend/scripts` passes.
2. A fresh database migrates 0001 to 0018, and `seed.py` runs twice with the same row counts.
3. Over HTTP, a loan goes requested → step 1 approved → step 2 approved by a different officer → disbursed by a third officer → repaid. Afterwards the balances equal the ledger.
4. The loan rules refuse:
   - the borrower deciding their own loan;
   - one officer deciding two steps;
   - an approver disbursing (`LOAN_SAME_OFFICER`);
   - disbursing before approval (`LOAN_NEEDS_APPROVAL`).
5. Reversing a disbursement or repayment ledger row answers 409.
6. A repeated identical deposit answers 200 with `replayed: true`. The same reference with a different amount answers 409 `DUPLICATE_REFERENCE`.
7. Job titles:
   - the admin makes members loans or finance officers;
   - only the platform owner grants `circle_admin`;
   - nobody changes their own titles;
   - another SACCO's member answers 404.
8. Settings: every active member reads them; only the platform owner changes them; bad values answer 400.
9. Tenant isolation: the Beta admin gets 404 on Alpha's loans, accounts and members.
10. `docs/openapi.yaml` lists every route (its test passes) and every `$ref` resolves.
11. The Thunder Client collection runs end to end against the live API on `nexora_dev`. Every request returns its documented status, proven by a runner that executes the collection file itself.
12. `docs/thunder-client.md` explains import, order and expected results. `docs/demo.md` lists the new officers and migrations up to 0018.

13. *Added by Collins on 2026-11-17: "all conditions are met from the schema".*
    The business rules of `docs/schema.sql` hold on the existing tables. There is
    no rebuild to that file's table layout. Each rule is proven by
    `tests/test_schema_rules.py` and the collection:
    - a SACCO admin never approves loans and cannot read the audit log;
    - the secretary reads the audit log and cannot post money or manage members;
    - a loan within the cap and the savings multiple needs 1 approval, and above
      either it needs the SACCO's count (cap 0 means always);
    - one open loan per member;
    - a rejection needs a reason;
    - a loan has a term in months;
    - loan decisions and repayments are append only;
    - at least two platform owners remain, and nobody revokes themselves;
    - an active membership never goes back to invited, and an invited one becomes
      active only by joining.

## Out of scope

Frontend, deployment, interest calculation, rebuilding the tables to the layout
in `docs/schema.sql` (its rules are item 13), and anything under "Parked".

## Constraints

- Flask, SQLAlchemy, Postgres and pytest, as already in the repo. No new runtime dependencies.
- Commits must not mention AI anywhere.
- Never run two pytest processes at once.
- The database role cannot create databases, so fresh-database checks use a scratch schema.
