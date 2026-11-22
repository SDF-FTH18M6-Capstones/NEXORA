# Testing the API with Thunder Client

One collection walks the whole backend in a single pass:

1. logins;
2. members;
3. settings and job titles;
4. savings and safe retries;
5. a loan with two approvals, disbursement and repayment;
6. a one-approval loan and a rejection;
7. tenant isolation and the audit log;
8. support access: the SACCO consents before a platform owner reads;
9. platform owners;
10. joining a SACCO by phone.

Every request knows its expected status, and saves the tokens and ids the next
requests need, so nothing is copied by hand.

Files:

- `docs/thunder/thunder-collection_NEXORA.json`: 10 folders, 77 requests.
- `docs/thunder/thunder-environment_NEXORA-local.json`: the variables.
- `docs/thunder/thunder-collection_NEXORA-1of2.json` and `-2of2.json`: the same
  requests in Thunder Client's own format, split in two to fit the free plan's
  50-request cap (folders 1 to 4: 31 requests, then 5 to 10: 46). **Use these on
  the free plan.** They save tokens with the Tests tab, not scripts.
- `docs/thunder/postman-collection_NEXORA-1of2.json` and
  `-2of2.json`: the same requests in Postman 2.1 format, split in two. These carry JavaScript test
  scripts, and Thunder Client's free plan answers "The scripting feature is
  available only in the paid version" (folders
  1 to 4: 31 requests, then 5 to 10: 46). Use these if the Thunder Client
  format will not import, or if the free plan's 50-request cap stops it.
- `docs/thunder/postman-environment_NEXORA-local.json`: the same three
  variables in Postman format.
- `docs/thunder/NEXORA-local.env`: the same three variables as a plain dotenv
  file, for the Env tab's `.env` import.

## 1. Start the API with fresh demo data

One-time setup (database, virtualenv, `backend/.env`) is in `docs/demo.md`. The
database name must end in `_dev`, for example `nexora_dev`. From the repo root,
with the virtualenv active:

```bash
cd backend
flask --app app db upgrade          # migrations 0001 to 0023
cd .. && python backend/scripts/seed.py
cd backend && python app.py         # http://localhost:5000
```

Check it with `curl http://localhost:5000/api/health`. The answer must be
`{"database":"connected","status":"healthy"}`.

Every seeded user's password is `Dev-Seed-Pass-2026`. The collection uses these
users:

| Variable | User | What they may do |
|---|---|---|
| `ownerToken` | `owner@example.com` | platform owner: SACCOs, settings, admins, other owners |
| `adminToken` | `alpha-admin@example.com` | Alpha SACCO admin: members, job titles, savings. Never approves loans and cannot read the audit log. |
| `loansToken` | `alpha-loans@example.com` | loans officer 1: approves a loan step |
| `loans2Token` | `alpha-loans2@example.com` | loans officer 2: approves the other step |
| `financeToken` | `alpha-finance@example.com` | finance officer: posts money, disburses loans |
| `memberToken` | `alpha-m1@example.com` | member: savings 40.00, requests and repays loans |

`owner2@example.com` exists because at least two platform owners must always
remain.

## 2. Import into Thunder Client (VS Code)

1. Install the **Thunder Client** extension and open it (lightning icon in the
   left bar).
2. Import the environment: **Env** tab → menu (≡) → **Import** →
   `docs/thunder/thunder-environment_NEXORA-local.json`.
3. Make it active: click **NEXORA local**, then **Set Active** (or the star).
4. Import the collection: **Collections** tab → menu (≡) → **Import** →
   `docs/thunder/thunder-collection_NEXORA.json`.
5. If the API is not on `http://localhost:5000`, change `baseUrl` in the
   environment.

### If the import fails

If Thunder Client answers **"No matching import provider found"**, or the free
plan's **50 requests per collection** cap stops the 77-request file, use the
split copies. `thunder-collection_NEXORA-1of2.json` holds folders 1 to 4
(31 requests) and `thunder-collection_NEXORA-2of2.json` holds folders 5 to 10
(46 requests), so neither part reaches the cap. Use the Postman copies only if
the Thunder Client format is refused; they need the paid scripting feature:

1. **Collections** tab → menu (≡) → **Import** → `thunder-collection_NEXORA-1of2.json`.
2. Run folders 1 to 4, then import and run `thunder-collection_NEXORA-2of2.json`.
   Part 2 reuses the tokens and ids part 1 saved.

The environment is only three variables, and the JSON forms of it can also be
refused. In that order, try:

1. **Env** tab → menu (≡) → **Import** → `NEXORA-local.env`. A plain dotenv file
   is read without format detection, so it does not need a matching provider.
2. **Env** tab → menu (≡) → **Import** → `postman-environment_NEXORA-local.json`.
3. Build it by hand: **Env** tab → **New Environment** → name it `NEXORA local`
   → add `baseUrl` = `http://localhost:5000`,
   `password` = `Dev-Seed-Pass-2026`, and `run` = `01`.

Whichever way it lands, click **NEXORA local** and then **Set Active**, or every
`{{baseUrl}}` stays literal.

## 3. Run it

Open folders 1 to 10 in order, and click **Send** on each request from top to
bottom. After each response:

- the **Tests** tab shows the status check (green) and any variable it saved;
- the environment shows every saved token and id (`saccoId`, `loanId`, ...).

Amounts are whole numbers in minor units: `10000` is KES 100.00.

### Rules to know before you run

- **Login allows 5 per minute from one address.** Folder 1 logs in 5 users; the
  6th login is the first request of folder 5. Clicking through by hand takes
  longer than a minute, so it passes. If it answers **429**, wait a minute and
  send it again.
- **Run All.** Run folders 1 to 4, wait 60 seconds, then run folders 5 to 10.
- **Running a second time on the same database.**
  - Wait a minute.
  - Change the environment variable `run` (`01` → `02`), because references
    must be unique per SACCO.
  - Folder 10 works once per database (a person joins a SACCO once). Re-seed a
    fresh database to show it again.
  - Folder 3, request 05 changes alpha-staff's titles and folder 5, request 11
    changes loans officer 1's titles, so they are not first-run state. The
    requests still pass.

## 4. Check the whole collection from a terminal

The same file, run by a script that applies the same checks and saves the same
variables:

```bash
python backend/scripts/check_collection.py http://localhost:5000 01
```

It prints PASS or FAIL for each request, waits out the login limit once if
needed, and exits with 1 if anything differs. On a freshly seeded database the
last line is:

```
77/77 requests returned what the collection expects
```

## 5. The rules the collection shows

Loans:

- Within both the SACCO's loan cap and 3× the member's savings, a loan needs
  **1** approval. Above either limit it needs the SACCO's higher count, **2**.
  Folder 3 sets the cap to 50.00 so the 100.00 loan needs 2.
- One open loan per member.
- The member can't approve their own loan, and a SACCO admin never approves.
- Each step needs a different loans officer.
- The disbursing officer must not have approved any step. Folder 5 gives loans
  officer 1 the finance title, then shows they still can't disburse
  (`LOAN_SAME_OFFICER`).
- No disbursement before approval (`LOAN_NEEDS_APPROVAL`).
- Loan ledger rows can't be reversed.
- A rejection needs a reason.

Savings:

- An identical retry replays the original entry (200, `replayed: true`).
- The same reference used for a different request answers 409
  `DUPLICATE_REFERENCE`.
- Nobody posts on their own account, and a withdrawal can't overdraw.

Access:

- Another SACCO's records answer 404, never 403.
- The SACCO admin can't read the audit log; the secretary can. A platform owner
  reads it only while that SACCO's support grant is approved.
- Only the platform owner changes loan settings or SACCO admins.
- Nobody changes their own titles.
- `sacco_admin` moves only with the admin role.
- At least two platform owners always remain, and nobody revokes themselves.
- An active member can't be moved back to invited.

## 6. Every request and its expected answer

### 1. Start: health and logins

| # | Request | Token | Body | Expect | Saves |
|---|---|---|---|---|---|
| 01 | **Health check**<br>`GET /api/health` | none |  | **200**<br>`status` = healthy |  |
| 02 | **Login: platform owner**<br>`POST /api/v1/auth/login` | none | `{"email": "owner@example.com", "password": "{{password}}"}` | **200** | `ownerToken` |
| 03 | **Login: Alpha admin**<br>`POST /api/v1/auth/login` | none | `{"email": "alpha-admin@example.com", "password": "{{password}}"}` | **200** | `adminToken` |
| 04 | **Login: Alpha loans officer 1**<br>`POST /api/v1/auth/login` | none | `{"email": "alpha-loans@example.com", "password": "{{password}}"}` | **200** | `loansToken` |
| 05 | **Login: Alpha finance officer**<br>`POST /api/v1/auth/login` | none | `{"email": "alpha-finance@example.com", "password": "{{password}}"}` | **200** | `financeToken` |
| 06 | **Login: Alpha member (m1)**<br>`POST /api/v1/auth/login` | none | `{"email": "alpha-m1@example.com", "password": "{{password}}"}` | **200** | `memberToken`, `refreshToken` |
| 07 | **Refresh the member's token**<br>`POST /api/v1/auth/refresh` | none | `{"refresh_token": "{{refreshToken}}"}` | **200** | `memberToken` |

### 2. Who am I, SACCOs and members

| # | Request | Token | Body | Expect | Saves |
|---|---|---|---|---|---|
| 01 | **Member: my profile (saves saccoId)**<br>`GET /api/v1/members/me` | memberToken |  | **200** | `saccoId`, `memberMembershipId` |
| 02 | **Member: my savings account (saves accountId)**<br>`GET /api/v1/savings/accounts/me` | memberToken |  | **200** | `accountId` |
| 03 | **Owner: list SACCOs (saves betaSaccoId)**<br>`GET /api/v1/saccos` | ownerToken |  | **200** | `betaSaccoId` |
| 04 | **Admin: SACCO details**<br>`GET /api/v1/saccos/{{saccoId}}` | adminToken |  | **200** |  |
| 05 | **Admin: member list (saves ids)**<br>`GET /api/v1/saccos/{{saccoId}}/members` | adminToken |  | **200**<br>`members[2].email` = alpha-loans@example.com | `adminMembershipId`, `staffMembershipId`, `loansMembershipId` |
| 06 | **Member: cannot list members (403)**<br>`GET /api/v1/saccos/{{saccoId}}/members` | memberToken |  | **403** |  |
| 07 | **Admin: an active member cannot go back to invited (409)**<br>`PATCH /api/v1/saccos/{{saccoId}}/members/{{memberMembershipId}}` | adminToken | `{"status": "invited"}` | **409** |  |

### 3. Settings and job titles

| # | Request | Token | Body | Expect | Saves |
|---|---|---|---|---|---|
| 01 | **Member: read loan settings**<br>`GET /api/v1/saccos/{{saccoId}}/settings` | memberToken |  | **200** |  |
| 02 | **Owner: set loan rules (cap 50.00, 3x savings, 2 approvals above)**<br>`PATCH /api/v1/saccos/{{saccoId}}/settings` | ownerToken | `{"loan_cap": 5000, "savings_multiple": 3, "required_approvals": 2}` | **200**<br>`loan_cap` = 5000 |  |
| 03 | **Admin: cannot change settings (403)**<br>`PATCH /api/v1/saccos/{{saccoId}}/settings` | adminToken | `{"loan_cap": 1}` | **403** |  |
| 04 | **Owner: bad setting value (400)**<br>`PATCH /api/v1/saccos/{{saccoId}}/settings` | ownerToken | `{"required_approvals": 5}` | **400** |  |
| 05 | **Admin: make staff a secretary + loans officer**<br>`PUT /api/v1/saccos/{{saccoId}}/members/{{staffMembershipId}}/roles` | adminToken | `{"roles": ["secretary", "loans_officer"]}` | **200** |  |
| 06 | **Admin: read staff titles**<br>`GET /api/v1/saccos/{{saccoId}}/members/{{staffMembershipId}}/roles` | adminToken |  | **200** |  |
| 07 | **Admin: cannot grant sacco_admin (403)**<br>`PUT /api/v1/saccos/{{saccoId}}/members/{{staffMembershipId}}/roles` | adminToken | `{"roles": ["sacco_admin"]}` | **403** |  |
| 08 | **Admin: cannot change own titles (403)**<br>`PUT /api/v1/saccos/{{saccoId}}/members/{{adminMembershipId}}/roles` | adminToken | `{"roles": ["sacco_admin", "finance_officer"]}` | **403** |  |
| 09 | **Owner: sacco_admin only moves with the admin role (409)**<br>`PUT /api/v1/saccos/{{saccoId}}/members/{{adminMembershipId}}/roles` | ownerToken | `{"roles": ["member"]}` | **409** |  |

### 4. Savings and safe retries

| # | Request | Token | Body | Expect | Saves |
|---|---|---|---|---|---|
| 01 | **Finance: deposit 50.00**<br>`POST /api/v1/savings/accounts/{{accountId}}/deposits` | financeToken | `{"amount": 5000, "reference": "demo{{run}}-dep"}` | **201** | `depositId` |
| 02 | **Finance: same deposit again is replayed (200)**<br>`POST /api/v1/savings/accounts/{{accountId}}/deposits` | financeToken | `{"amount": 5000, "reference": "demo{{run}}-dep"}` | **200**<br>`replayed` = true |  |
| 03 | **Finance: same reference, other amount (409)**<br>`POST /api/v1/savings/accounts/{{accountId}}/deposits` | financeToken | `{"amount": 6000, "reference": "demo{{run}}-dep"}` | **409**<br>`error.code` = DUPLICATE_REFERENCE |  |
| 04 | **Member: cannot post money (403)**<br>`POST /api/v1/savings/accounts/{{accountId}}/deposits` | memberToken | `{"amount": 100, "reference": "demo{{run}}-self"}` | **403** |  |
| 05 | **Finance: withdrawal too big (409)**<br>`POST /api/v1/savings/accounts/{{accountId}}/withdrawals` | financeToken | `{"amount": 9000000, "reference": "demo{{run}}-wd-big"}` | **409**<br>`error.code` = INSUFFICIENT_FUNDS |  |
| 06 | **Admin: reverse the deposit**<br>`POST /api/v1/savings/transactions/{{depositId}}/reversals` | adminToken | `{"reference": "demo{{run}}-rev"}` | **201** |  |
| 07 | **Finance: deposit again (funds for the loan)**<br>`POST /api/v1/savings/accounts/{{accountId}}/deposits` | financeToken | `{"amount": 5000, "reference": "demo{{run}}-dep2"}` | **201** |  |
| 08 | **Member: my transaction history**<br>`GET /api/v1/savings/accounts/{{accountId}}/transactions` | memberToken |  | **200** |  |

### 5. Loan: two approvals, disburse, repay

| # | Request | Token | Body | Expect | Saves |
|---|---|---|---|---|---|
| 01 | **Login: Alpha loans officer 2**<br>`POST /api/v1/auth/login` | none | `{"email": "alpha-loans2@example.com", "password": "{{password}}"}` | **200** | `loans2Token` |
| 02 | **Member: request a 100.00 loan (above the cap: 2 approvals)**<br>`POST /api/v1/loans/saccos/{{saccoId}}` | memberToken | `{"principal": 10000, "term_months": 6}` | **201**<br>`status` = requested<br>`required_approvals` = 2 | `loanId` |
| 03 | **Member: a second open loan is refused (409)**<br>`POST /api/v1/loans/saccos/{{saccoId}}` | memberToken | `{"principal": 1000, "term_months": 3}` | **409** |  |
| 04 | **Loans officer: list SACCO loans**<br>`GET /api/v1/loans/saccos/{{saccoId}}` | loansToken |  | **200** |  |
| 05 | **Member: cannot approve own loan (403)**<br>`POST /api/v1/loans/{{loanId}}/decisions` | memberToken | `{"step": 1, "decision": "approve"}` | **403** |  |
| 06 | **Admin: a SACCO admin never approves (403)**<br>`POST /api/v1/loans/{{loanId}}/decisions` | adminToken | `{"step": 1, "decision": "approve"}` | **403** |  |
| 07 | **Finance: cannot disburse before approval (409)**<br>`POST /api/v1/loans/{{loanId}}/disbursements` | financeToken | `{"reference": "demo{{run}}-disb-early"}` | **409**<br>`error.code` = LOAN_NEEDS_APPROVAL |  |
| 08 | **Loans officer 1: approve step 1**<br>`POST /api/v1/loans/{{loanId}}/decisions` | loansToken | `{"step": 1, "decision": "approve"}` | **201**<br>`status` = requested |  |
| 09 | **Loans officer 1: cannot approve step 2 too (403)**<br>`POST /api/v1/loans/{{loanId}}/decisions` | loansToken | `{"step": 2, "decision": "approve"}` | **403** |  |
| 10 | **Loans officer 2: approve step 2**<br>`POST /api/v1/loans/{{loanId}}/decisions` | loans2Token | `{"step": 2, "decision": "approve"}` | **201**<br>`status` = approved |  |
| 11 | **Admin: loans officer 1 also becomes a finance officer**<br>`PUT /api/v1/saccos/{{saccoId}}/members/{{loansMembershipId}}/roles` | adminToken | `{"roles": ["loans_officer", "finance_officer"]}` | **200** |  |
| 12 | **Loans officer 1 (an approver) cannot disburse (403)**<br>`POST /api/v1/loans/{{loanId}}/disbursements` | loansToken | `{"reference": "demo{{run}}-disb-same"}` | **403**<br>`error.code` = LOAN_SAME_OFFICER |  |
| 13 | **Finance: disburse**<br>`POST /api/v1/loans/{{loanId}}/disbursements` | financeToken | `{"reference": "demo{{run}}-disb"}` | **201**<br>`status` = disbursed | `disbursementTxId` |
| 14 | **Admin: cannot reverse the disbursement (409)**<br>`POST /api/v1/savings/transactions/{{disbursementTxId}}/reversals` | adminToken | `{"reference": "demo{{run}}-rev-disb"}` | **409** |  |
| 15 | **Member: repay 40.00**<br>`POST /api/v1/loans/{{loanId}}/repayments` | memberToken | `{"amount": 4000, "reference": "demo{{run}}-rep1"}` | **201**<br>`loan_status` = disbursed | `repaymentTxId` |
| 16 | **Admin: cannot reverse the repayment (409)**<br>`POST /api/v1/savings/transactions/{{repaymentTxId}}/reversals` | adminToken | `{"reference": "demo{{run}}-rev-rep"}` | **409** |  |
| 17 | **Finance: repay the remaining 60.00**<br>`POST /api/v1/loans/{{loanId}}/repayments` | financeToken | `{"amount": 6000, "reference": "demo{{run}}-rep2"}` | **201**<br>`loan_status` = repaid |  |
| 18 | **Member: the loan, with its decisions**<br>`GET /api/v1/loans/{{loanId}}` | memberToken |  | **200**<br>`status` = repaid |  |

### 6. Loan: one approval, and a rejection

| # | Request | Token | Body | Expect | Saves |
|---|---|---|---|---|---|
| 01 | **Member: request 20.00 (within cap and 3x savings: 1 approval)**<br>`POST /api/v1/loans/saccos/{{saccoId}}` | memberToken | `{"principal": 2000, "term_months": 3}` | **201**<br>`required_approvals` = 1 | `loan2Id` |
| 02 | **Loans officer 2: a rejection without a reason (400)**<br>`POST /api/v1/loans/{{loan2Id}}/decisions` | loans2Token | `{"step": 1, "decision": "reject"}` | **400** |  |
| 03 | **Loans officer 2: reject with a reason**<br>`POST /api/v1/loans/{{loan2Id}}/decisions` | loans2Token | `{"step": 1, "decision": "reject", "reason": "Repaid a loan this week; apply next month."}` | **201**<br>`status` = rejected |  |
| 04 | **Member: the rejected loan shows the reason**<br>`GET /api/v1/loans/{{loan2Id}}` | memberToken |  | **200**<br>`decisions[0].reason` = Repaid a loan this week; apply next month. |  |

### 7. Isolation, reports and audit

| # | Request | Token | Body | Expect | Saves |
|---|---|---|---|---|---|
| 01 | **Admin: Beta's loans are invisible (404)**<br>`GET /api/v1/loans/saccos/{{betaSaccoId}}` | adminToken |  | **404** |  |
| 02 | **Admin: Beta's members are invisible (404)**<br>`GET /api/v1/saccos/{{betaSaccoId}}/members` | adminToken |  | **404** |  |
| 03 | **Admin: Beta's settings are invisible (404)**<br>`GET /api/v1/saccos/{{betaSaccoId}}/settings` | adminToken |  | **404** |  |
| 04 | **No token (401)**<br>`GET /api/v1/savings/accounts/me` | none |  | **401** |  |
| 05 | **Admin: SACCO summary report**<br>`GET /api/v1/admin/saccos/{{saccoId}}/reports/summary` | adminToken |  | **200** |  |
| 06 | **Admin: cannot read the audit log (403)**<br>`GET /api/v1/admin/saccos/{{saccoId}}/audit` | adminToken |  | **403** |  |
| 07 | **Owner: no SACCO audit log without consent (403)**<br>`GET /api/v1/admin/saccos/{{saccoId}}/audit` | ownerToken |  | **403** |  |
| 08 | **Owner: platform audit log**<br>`GET /api/v1/admin/audit` | ownerToken |  | **200** |  |

### 8. Support access: the SACCO consents, the owner reads

A platform owner reads another SACCO's audit log only while that SACCO has
approved a support-access request. Membership is a separate scope and is never
part of the grant.

| # | Request | Token | Body | Expect | Saves |
|---|---|---|---|---|---|
| 01 | **Owner: ask to read Alpha's audit log**<br>`POST /api/v1/saccos/{{saccoId}}/support-access` | ownerToken | `{"reason": "Demo: checking a member complaint", "scope": "audit"}` | **201**<br>`status` = requested | `supportId` |
| 02 | **Admin: see the request**<br>`GET /api/v1/saccos/{{saccoId}}/support-access` | adminToken |  | **200**<br>`requests[0].status` = requested |  |
| 03 | **Admin: approve it for 1 hour**<br>`POST /api/v1/support-access/{{supportId}}/approve` | adminToken | `{"hours": 1}` | **200**<br>`status` = approved |  |
| 04 | **Owner: read the audit log under the grant**<br>`GET /api/v1/admin/saccos/{{saccoId}}/audit` | ownerToken |  | **200** |  |
| 05 | **Owner: members are another scope (403)**<br>`GET /api/v1/saccos/{{saccoId}}/members` | ownerToken |  | **403** |  |
| 06 | **Admin: revoke the grant**<br>`POST /api/v1/support-access/{{supportId}}/revoke` | adminToken |  | **200**<br>`status` = revoked |  |
| 07 | **Owner: refused again after the revoke (403)**<br>`GET /api/v1/admin/saccos/{{saccoId}}/audit` | ownerToken |  | **403** |  |

### 9. Platform owners

| # | Request | Token | Body | Expect | Saves |
|---|---|---|---|---|---|
| 01 | **Owner: list owners (saves the second owner)**<br>`GET /api/v1/admin/owners` | ownerToken |  | **200**<br>`owners[1].email` = owner2@example.com | `owner2Id` |
| 02 | **Admin: not a platform owner (403)**<br>`GET /api/v1/admin/owners` | adminToken |  | **403** |  |
| 03 | **Owner: revoking the second owner would leave one (409)**<br>`DELETE /api/v1/admin/owners/{{owner2Id}}` | ownerToken |  | **409** |  |

### 10. Join a SACCO by phone (once per database)

| # | Request | Token | Body | Expect | Saves |
|---|---|---|---|---|---|
| 01 | **Login: Beta admin**<br>`POST /api/v1/auth/login` | none | `{"email": "beta-admin@example.com", "password": "{{password}}"}` | **200** | `betaAdminToken` |
| 02 | **Beta admin: invite a phone into Beta (shows join_code)**<br>`POST /api/v1/saccos/{{betaSaccoId}}/members` | betaAdminToken | `{"phone": "+2547000100{{run}}", "role": "member"}` | **201** | `joinCode` |
| 03 | **Member m1: join Beta with the code**<br>`POST /api/v1/auth/join` | memberToken | `{"phone": "+2547000100{{run}}", "code": "{{joinCode}}"}` | **200** | `setupToken` |
| 04 | **Member m1: set a 4-digit PIN**<br>`POST /api/v1/auth/join/pin` | memberToken | `{"setup_token": "{{setupToken}}", "pin": "4826"}` | **200**<br>`status` = active |  |
| 05 | **Member m1: SACCO login with the PIN**<br>`POST /api/v1/auth/sacco-login` | memberToken | `{"sacco_id": {{betaSaccoId}}, "pin": "4826"}` | **200**<br>`ok` = true |  |
| 06 | **Member m1: wrong PIN is refused**<br>`POST /api/v1/auth/sacco-login` | memberToken | `{"sacco_id": {{betaSaccoId}}, "pin": "0000"}` | **401** |  |

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| A login answers 429 | Login limit (5 per minute). Wait 60 s, or restart `python app.py`, and send it again. |
| Every request after the logins is 401 | A login failed (429 or wrong password), so its token is empty. Fix that login first. |
| `{{saccoId}}` appears literally in a URL | The environment is not active, or folder 2 was skipped. |
| A deposit answers 409 `DUPLICATE_REFERENCE` on its first send | That reference was used in an earlier run: change `run`. |
| Loan request answers 409 "open loan" | The member still has a requested, approved or disbursed loan. Finish folder 5 first, or re-seed. |
| Folder 10 join answers 409 or 401 | Already joined in an earlier run (once per database). |
| Health answers `disconnected` | PostgreSQL is not running, or `DATABASE_URL` in `backend/.env` is wrong. |
