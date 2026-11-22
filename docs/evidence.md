# Evidence (runs made by Nexus, 2026-11-17)

Branch `move-5/collins-finish`. These runs are on the final working tree, after
the santa-review round 1 fixes and the schema rules (brief item 13).

## Commands and results

| # | Command | Result |
|---|---|---|
| E1 | `ruff check backend/app tests backend/scripts backend/migrations/versions/0017_loan_disbursement_transaction.py backend/migrations/versions/0018_schema_rules.py` | `All checks passed!` |
| E2 | `pytest -m "schema or not schema"` | `709 passed, 5 skipped`. The 5 skips are the `nexora_app` role tests, which need the role provisioned by an administrator: **unverified**. |
| E3 | `flask db upgrade` on an empty schema (`nexora_demo`) | 0001 → 0018 ran with no error, and `alembic_version` = `0018`. 0014 logged that it skipped creating `nexora_app` (no CREATEROLE). |
| E4 | `seed.seed()` twice on that schema | Both runs gave identical counts: users 18, saccos 2, memberships 16, accounts 6, transactions 14, membership_roles 16. |
| E5 | `python backend/scripts/check_collection.py http://127.0.0.1:5055 01` on the fresh schema | `69/69 requests returned what the collection expects`. The 6th login hit the real 5-per-minute limit, and the runner waited 61 s once. |
| E6 | SQL after E5 | 6 accounts, 0 differences between stored balance and ledger sum. Loan 1 is `repaid` (2 approvals, term 6, disbursement linked). Loan 2 is `rejected` (1 approval required, term 3, reason stored). |
| E7 | `API=http://127.0.0.1:5055 bash backend/scripts/demo.sh` | Every step answered its documented status, including the owner reading the audit log (200) and the admin refused (403). |
| E8 | OpenAPI: PyYAML load plus `$ref` resolution | 44 paths, 53 operations, 0 unresolved refs. `tests/test_openapi_spec.py` passes. |
| E9 | Mutation checks: each fix reverted on purpose, then the tests run | Round 1: 5 tests failed (drift guard, demote sync, 2 settings bounds, reversed-retry). Schema rules: 4 tests failed (approval count, reason, transitions, owner self-revoke). With the app's one-open-loan check removed, the database index still refuses the second loan. All code restored, and `git diff` was checked afterwards. |
| E10 | santa-review round 1 (2 independent breakers) | Both FAIL. Fixed: the `sacco_admin` revocation leak (Major, found by both), the `savings_multiple` overflow 500 (Major per C), and 4 Lows. Their proof tests are folded into `tests/test_roles_settings.py`. |

## Checklist item → evidence

| Brief item | Evidence |
|---|---|
| 1 suite + lint | E1, E2 |
| 2 fresh migrate + seed twice | E3, E4 |
| 3 loan lifecycle over HTTP | E5 folder 5 (requests 02, 08, 10, 13, 15, 17, 18); E6; `test_roles_settings.py::test_full_loan_flow_and_loan_rows_cannot_be_reversed` |
| 4 loan refusals | E5 folder 5: 05 (own loan 403), 09 (same officer 403), 12 (`LOAN_SAME_OFFICER`), 07 (`LOAN_NEEDS_APPROVAL`) |
| 5 loan rows not reversible | E5 folder 5: 14 and 16 (409) |
| 6 retry rule | E5 folder 4: 02 (200, `replayed`), 03 (409 `DUPLICATE_REFERENCE`); `test_retry_rules_around_reversals_and_withdrawals`; E7 |
| 7 job titles | E5 folder 3: 05–09; folder 5: 11; `test_roles_settings.py` (cross-SACCO 404, member 403, admin-on-admin 403, inactive 409, drift 409, demote sync) |
| 8 settings | E5 folder 3: 01–04; `test_members_read_settings_and_only_the_owner_changes_them`; `test_out_of_range_settings_are_400_not_500` |
| 9 tenant isolation | E5 folder 7: 01–03 (404); `test_members_see_only_their_own_loans_and_other_saccos_none` |
| 10 OpenAPI | E8 |
| 11 Thunder collection | E5 |
| 12 guide + demo docs | `docs/thunder-client.md` (import, order, login limit, re-run rules, a request table generated from the collection, troubleshooting); `docs/demo.md` (0018, officers, owners, operation count) |
| 13 schema rules | `tests/test_schema_rules.py` (19 tests); E5 folder 3: 09; folder 5: 03, 06; folder 6: 01–04; folder 7: 06; folder 8: 01–03; folder 2: 07; E9 |
