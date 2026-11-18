# Parked (seen, not built in this run)

- `docs/schema.sql` (untracked) is an old database dump and `docs/schema.md` (untracked) describes a different schema
  from the migrations (`memberships`, `otp_codes`, `sacco_pins`). Decide whether
  it is a target design or should be deleted.
- `nexora_app` role tests need the role provisioned once per cluster by an
  administrator (`backend/scripts/nexora_app_role.sql`). The last test also
  gives the role a temporary login, so the migrating user needs CREATEROLE and,
  on Postgres 16 or newer, `GRANT nexora_app TO <migrating user> WITH ADMIN
  OPTION, INHERIT FALSE, SET FALSE` while it runs (remove both afterwards).
  Done on Collins's machine 2026-11-18: 5 passed. CI does not provision it.
- If the wrong person joins with a leaked join code, their account owns that
  phone number afterwards, so the right person cannot join it even after a
  re-invite. Join codes are handed over in person; until a "release phone"
  action exists, the platform owner fixes it in the database.

## Release 2: loan interest (not built; release 1 loans are interest-free)

Release 1 lends the principal only: a loan is repaid when repayments equal the
principal. Interest waits for these decisions from the team:

1. **Method:** flat (interest on the original principal for the whole term) or
   reducing balance (interest on what is still owed each period).
2. **Rate:** one rate per SACCO (in `sacco_settings`), or a rate set on each
   loan at request time (frozen like `required_approvals`), or both (SACCO
   default, overridable per loan within limits).
3. **When it is charged:** all up front at disbursement, monthly as it accrues,
   or with each repayment.
4. **Repayment split:** whether a repayment pays interest first and then
   principal (usual), or principal first; and what happens to an overpayment.

Planned schema change, once decided (one migration):

- `sacco_settings`: `interest_rate_bps` (basis points, integer, >= 0) and
  `interest_method` (enum `flat` | `reducing`).
- `loans`: `interest_rate_bps` and `interest_method`, frozen at request time,
  and `interest_total` (minor units) for the flat method.
- `loan_repayments`: split into `principal_amount` and `interest_amount`
  (check: they add up to `amount`).
- If interest accrues over time: a `loan_interest_charges` table (append only,
  one row per charge, loan id, period, amount), so the owed balance is
  rebuilt from rows, like savings balances are from the ledger.
- A loan is `repaid` when principal and interest owed are both zero.
