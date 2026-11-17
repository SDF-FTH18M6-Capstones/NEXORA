# Parked (seen, not built in this run)

- Legacy `staff` memberships can post money through `POSTING_ROLES` even when
  their job title is `secretary`. Fix: decide posting rights from `can()` only;
  needs the test fixtures to give staff a title row first.
- The #109 merge deleted explanatory comments in `savings/service.py`,
  `ledger/reversals.py` and `savings/routes.py`. Restore from `ce4acb0` if the
  team wants them back.
- Loan interest and schedules (team is still waiting on the interest decision).
- `docs/schema.sql` / `docs/schema.md` (untracked) describe a different schema
  from the migrations (`memberships`, `otp_codes`, `sacco_pins`). Decide whether
  it is a target design or should be deleted.
- `nexora_app` role tests skip locally until `backend/scripts/nexora_app_role.sql`
  is run by an administrator.
- A SACCO admin can add a second account of their own as a member and give it
  `loans_officer` or `secretary`, so "an admin never approves or reads the audit
  log" holds per account, not per person. Product decision: let only the
  platform owner assign those titles, or show title changes in the owner's
  audit view.
- A phone invite that has joined (`/auth/join`) but not set its PIN can be moved
  invited -> inactive -> active by hand, and then can never set a circle PIN.
  Decide whether a PATCH to active should also require a PIN.
- Before running migration 0018 on a teammate's database, check that no member
  has two open loans (the new unique index would refuse it):
  `SELECT membership_id FROM loans WHERE status IN ('requested','approved','disbursed') GROUP BY 1 HAVING count(*) > 1;`
  Databases at the previous head could not create loans at all (missing
  `sacco_settings.required_approvals`), so this is a precaution.
- `POST /saccos/<id>/members` accepts `status: "invited"` with an email, which
  creates an invited membership that already has a user and no join code.
