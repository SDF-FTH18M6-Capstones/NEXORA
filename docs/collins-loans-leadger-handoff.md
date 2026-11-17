# Handoff to Collins: Loan & Ledger Endpoints and Error Codes

**Base prefix:** `/api/v1`  
**Auth header:** `Authorization: Bearer <access_token>`  
**Monetary amounts:** Positive integers in minor units (e.g., `10000` = `100.00 KES`).  
**Idempotency (`reference`):** Required on all money-movement endpoints (`1..64` chars matching `[A-Za-z0-9._:-]`), unique per SACCO.

## 1. Ledger & Savings Endpoints

| Method | Path | Role / Permission | Request Body | Success |
|---|---|---|---|---|
| `POST` | `/api/v1/savings/accounts` | `circle_admin`, `finance_officer` (`savings.post`) | `{"membership_id": int}` | `201` Account object |
| `GET` | `/api/v1/savings/accounts/me` | Any signed-in member | — | `200` `{"accounts": [...]}` |
| `GET` | `/api/v1/savings/accounts/<account_id>` | Owner member or SACCO staff (`savings.view`) | — | `200` Account object |
| `GET` | `/api/v1/savings/accounts/<account_id>/transactions` | Owner member or SACCO staff (`savings.view`) | Query: `?page=1&per_page=20` | `200` `{"transactions": [...], "page": int, "per_page": int, "total": int}` |
| `POST` | `/api/v1/savings/accounts/<account_id>/deposits` | `circle_admin`, `finance_officer` (`savings.post`) | `{"amount": int, "reference": str}` | `201` Ledger entry + updated `balance` |
| `POST` | `/api/v1/savings/accounts/<account_id>/withdrawals` | `circle_admin`, `finance_officer` (`savings.post`) | `{"amount": int, "reference": str}` | `201` Ledger entry + updated `balance` |
| `POST` | `/api/v1/savings/accounts/<account_id>/interest` | `circle_admin`, `finance_officer` (`savings.post`) | `{"amount": int, "reference": str}` | `201` Ledger entry + updated `balance` |
| `POST` | `/api/v1/savings/accounts/<account_id>/fees` | `circle_admin`, `finance_officer` (`savings.post`) | `{"amount": int, "reference": str}` | `201` Ledger entry + updated `balance` |
| `POST` | `/api/v1/savings/transactions/<transaction_id>/reversals` | `circle_admin`, `finance_officer` (`savings.reverse`) | `{"reference": str}` | `201` Reversal entry (`reverses_id` set) + updated `balance` |

## 2. Loan Endpoints

| Method | Path | Role / Permission | Request Body | Success |
|---|---|---|---|---|
| `POST` | `/api/v1/loans/saccos/<sacco_id>` | `member` (`loan.request`) | `{"principal": int}` | `201` Loan object (`status: "requested"`, `required_approvals` frozen from `sacco_settings`) |
| `GET` | `/api/v1/loans/saccos/<sacco_id>` | Any SACCO member (`member` sees own loans only; officers see SACCO loans) | Query: `?page=1&per_page=20` | `200` `{"loans": [...], "page": int, "per_page": int}` |
| `GET` | `/api/v1/loans/<loan_id>` | Owner member or SACCO officer | — | `200` Loan object + `decisions: [...]` |
| `POST` | `/api/v1/loans/<loan_id>/decisions` | `circle_admin`, `loans_officer` (`loan.approve`) | `{"step": int, "decision": "approve" | "reject"}` | `201` Updated Loan object (`status` becomes `"approved"` once `step == required_approvals`, or `"rejected"`) |
| `POST` | `/api/v1/loans/<loan_id>/disbursements` | `finance_officer` only (`loan.disburse`) | `{"reference": str}` | `201` Updated Loan object (`status: "disbursed"`), credits borrower's savings account |
| `POST` | `/api/v1/loans/<loan_id>/repayments` | `member` (own loan) or `finance_officer` (`loan.repay`) | `{"amount": int, "reference": str}` | `201` Repayment object (`repayment_id`, `transaction_id`, `repaid_total`, `loan_status`, `account_balance`) |

## 3. Error Envelope & Error Codes

Every error response follows `{"error": {"code": "<CODE>", "message": "<human text>"}}`:

| HTTP Status | `error.code` | When Returned |
|---|---|---|
| `400` | `validation_error` | Invalid JSON fields, non-integer/non-positive `amount` or `principal`, invalid `step`, invalid `decision`, or malformed `reference`. |
| `401` | `unauthorized` | Missing, expired, or revoked Bearer access token. |
| `403` | `NOT_ALLOWED` | Authenticated SACCO member lacks permission, attempts to post/reverse/approve/disburse their own account/loan, or has an inactive membership. |
| `403` | `LOAN_SAME_OFFICER` | `finance_officer` attempting disbursement is one of the officers who approved a step on that loan. |
| `404` | `NOT_FOUND` / `not_found` | Resource does not exist, or belongs to another SACCO / another member (no ID enumeration). |
| `409` | `DUPLICATE_REFERENCE` | `reference` was already posted within the same SACCO; request rejected without creating a ledger row. |
| `409` | `INSUFFICIENT_FUNDS` | Withdrawal, fee, reversal, or loan repayment exceeds the savings account's available balance. |
| `409` | `LOAN_NEEDS_APPROVAL` | Disbursement attempted before `required_approvals` steps are approved (`status != "approved"`). |
| `409` | `conflict` | Reversing an entry twice, reversing a reversal, out-of-order approval `step`, loan exceeds `loan_cap` or `savings_multiple`, or repayment exceeds remaining loan principal. |
| `423` | `locked` | The SACCO is suspended. |