# Parked (seen, not built in this run)

- Loan interest and schedules (team is still waiting on the interest decision).
- `docs/schema.sql` (untracked) is an old database dump and `docs/schema.md` (untracked) describes a different schema
  from the migrations (`memberships`, `otp_codes`, `sacco_pins`). Decide whether
  it is a target design or should be deleted.
- `nexora_app` role tests skip locally until `backend/scripts/nexora_app_role.sql`
  is run by an administrator.
- A SACCO admin can add a second account of their own as a member and give it
  `loans_officer` or `secretary`, so "an admin never approves or reads the audit
  log" holds per account, not per person. Product decision: let only the
  platform owner assign those titles, or show title changes in the owner's
  audit view.
- A phone invited to two SACCOs at once can only join the newest invitation
  (`/auth/join` finds the membership by phone). Fix with a `sacco_id` in the
  join body; it changes the join API, so it waits until after the demo.
- If the wrong person joins with a leaked join code, their account owns that
  phone number afterwards, so the right person cannot join it even after a
  re-invite. Join codes are handed over in person; until a "release phone"
  action exists, the platform owner fixes it in the database.
