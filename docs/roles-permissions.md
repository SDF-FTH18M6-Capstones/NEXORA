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

## 5. Permission Matrix

| Capability | Platform Owner | SACCO Administrator | SACCO Member |
|---|---|---|---|
| Manage SACCOs | Yes | No | No |
| Platform configuration | Yes | No | No |
| Manage SACCO members | Platform policy | Own SACCO | No |
| View SACCO reports | Platform policy | Own SACCO | No |
| View personal profile | Yes, as authorized | Own SACCO scope | Own profile |
| View personal transactions | Authorized policy | Own SACCO scope | Own transactions |
| Manage financial operations | Platform policy | Approved SACCO scope | No |
| Access another SACCO | Authorized platform scope | No | No |

## 6. Authorization Rules

- Every protected API endpoint must verify authentication.
- Every protected operation must verify the user's role.
- SACCO Administrators must be restricted to their assigned SACCO.
- Members must only access their own records.
- The backend must never rely on frontend role checks alone.
- Unauthorized requests must return HTTP 403.
- Unauthenticated requests must return HTTP 401.
- Privileged actions should be recorded in an audit log.

## 7. Decisions Requiring Team Approval

The team must agree on:

- Whether Platform Owners can view individual member financial details.
- Which financial operations SACCO Administrators can approve.
- Whether SACCO Administrators can create other administrators.
- Whether additional approval is required for sensitive operations.
- Whether a user can hold multiple roles or SACCO memberships.

## 8. Approval

These permissions are proposed for team review.
They are not production authorization rules until approved.
