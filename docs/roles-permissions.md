# NEXORA Roles and Permissions

## 1. Overview

NEXORA has three primary user roles:

1. Platform Owner
2. SACCO Administrator
3. SACCO Member

Permissions must be enforced by the Flask backend.

## 2. Platform Owner

The Platform Owner manages the overall NEXORA platform.

Proposed permissions:

- View registered SACCOs.
- Register and manage SACCO organizations.
- Activate or deactivate SACCO accounts.
- Manage platform-level user access.
- View platform-wide operational information.
- Monitor platform activity.
- Manage platform configuration.
- Investigate reported system issues.

Restrictions:

- All privileged actions must be authenticated.
- Sensitive administrative actions must be logged.
- Access to member financial information must follow an
  explicitly approved platform policy.

## 3. SACCO Administrator

The SACCO Administrator manages an individual SACCO.

Proposed permissions:

- View SACCO information.
- Manage SACCO members.
- Register and update member records.
- View SACCO membership information.
- View SACCO financial records.
- Manage SACCO operational activities.
- Generate SACCO reports.
- Monitor member activities.

Restrictions:

- Cannot access another SACCO's records.
- Cannot manage platform-level configuration.
- Cannot grant themselves Platform Owner privileges.
- Financial operations must follow approved authorization rules.

## 4. SACCO Member

The SACCO Member uses NEXORA to access their own SACCO services.

Proposed permissions:

- View personal profile.
- View membership information.
- View personal savings information.
- View personal loan information.
- View personal financial transaction history.
- Submit permitted service requests.
- View personal account statements.
- Update permitted personal information.

Restrictions:

- Cannot access another member's private information.
- Cannot manage SACCO users.
- Cannot access administrative functions.
- Cannot change financial records directly.

## 5. Job titles and permissions (agreed 2026-11-17)

Every membership holds job titles; `can()` in `backend/app/security/permissions.py`
answers every permission question from them. The legacy role column only says
whether a membership is the SACCO admin (`sacco_admin`); every membership the
API creates or changes stores the title its role implies (admin: sacco_admin,
staff: secretary, member: member).

| Permission | SACCO admin | Secretary | Finance officer | Loans officer | Member |
|---|---|---|---|---|---|
| member.view (member list) | yes | yes | | yes | |
| member.manage (add, invite, set titles) | yes | | | | |
| savings.view_all (every account) | yes | yes | yes | | own only |
| savings.post (deposit, withdraw, interest, fee, open account) | yes | | yes | | |
| savings.request (send a deposit or withdrawal request for my own account) | | | | | yes |
| savings.reverse | yes | | yes | | |
| savings.reverse_override (reverse past an open loan's cap, with a reason; audited) | yes | | | | |
| report.view | yes | yes | yes | yes | |
| sacco.view (SACCO name, status, settings) | yes | yes | yes | yes | yes |
| sacco.update (rename the SACCO) | yes | | | | |
| support.approve (approve, deny or revoke a platform owner's support access) | yes | | | | |
| payin.manage (propose, approve or cancel the SACCO's pay-in details; a different officer must approve, any one may cancel before it goes live) | yes | | yes | | |
| audit.view (SACCO audit log) | **never** | yes | | | |
| loan.view (every loan) | yes | yes | yes | yes | own only |
| loan.approve | **never** | | | yes | |
| loan.disburse | **never** | | yes | | |
| loan.request | | | | | yes |
| loan.repay | | | yes | | own loan |

`payin.manage` is held by no platform role: the platform owner can read a SACCO's live pay-in
details (`sacco.view`) but never proposes or approves them. A SACCO needs two people holding it
(the admin plus a finance officer) before its first details can go live.

The platform owner holds every permission, needs no membership, and is the only
one who creates SACCOs, changes loan settings, makes or removes SACCO admins
(`admin.manage`, which no job title holds) and grants or revokes platform
owners. Every SACCO-scoped route checks one permission with `can()`; no route
decides by role name (`tests/test_access_by_permission.py` enforces this).

## 6. Rules the backend enforces

- A SACCO admin never approves or disburses loans and never reads the audit log,
  whatever titles the membership holds.
- Nobody changes their own titles; only the platform owner touches an admin;
  `sacco_admin` moves only with the admin role. The database records who
  granted every title and refuses a title granted by the user who owns that
  membership (platform owners exempt, migration 0021). Collusion between two
  people is not blocked; title changes are in the audit log.
- At least two platform owners always remain; nobody revokes themselves.
- Nobody posts or reverses money on their own account. Every movement is one
  ledger row; balances change only through the ledger. Ledger rows, loan
  decisions, loan repayments and the audit log are append only.
- A loan within the SACCO cap and the savings multiple needs one approval;
  above either it needs the SACCO's count (1 or 2; a cap of 0 means always).
  Each step needs a different loans officer; the disbursing officer approved no
  step; one open loan per member; a rejection needs a reason; loan ledger rows
  cannot be reversed.
- Memberships: invited -> active only by joining with a code and setting a PIN
  (one phone may hold invitations to several SACCOs; the code picks the SACCO);
  active -> inactive; inactive -> invited (a re-add by phone, fresh code);
  never active -> invited.
- Another SACCO's records answer 404, never 403. A suspended SACCO answers 423.

## 7. Approval

Agreed for the demo on 2026-11-17. `tests/test_schema_rules.py` holds one test
per rule.

## Member personal data

A member's full name, national ID, gender and date of birth are read and written only by the member
themself and by holders of `member.manage` (the SACCO admin). The platform owner never reads them, and
no list or search returns them. They can be stored only while the member's own `member_profile` consent
is active (nobody can consent for someone else), and withdrawing consent erases them. Share capital is
not personal data: only `member.manage` records it. Every field is optional for now.
