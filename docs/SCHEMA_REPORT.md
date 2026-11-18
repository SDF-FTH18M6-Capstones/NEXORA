# NEXORA schema report

Generated from the live `nexora_dev` database (read-only session) at migration `0021`, with `pg_dump --schema-only` and `information_schema`. "Added in" is the migration file in `backend/migrations/versions/` that created the table, column, index or trigger.

Tables: 20 (pg_dump agrees: True). Row-level security enabled on: none.

## How this differs from docs/

- **`docs/database-schema.md` is the early proposal and is out of date.** It
  lists `users.full_name`, `users.phone_number`, `users.status`,
  `users.updated_at`, `saccos.registration_number`, `saccos.contact_email`,
  `saccos.contact_phone`, `memberships.membership_number`,
  `memberships.joined_at`, `transactions.member_id` and `transactions.status`.
  None of these exist. Phones live in `user_phones` and on
  `sacco_memberships.phone`; a transaction belongs to a savings account
  (`savings_account_id`), not a member; there is no transaction status
  (history is append only, corrections are reversal rows). It describes 4
  tables; the database has 19, and its "decisions pending" are settled
  (multiple SACCOs per user: yes; separate savings and loan entities: yes;
  ledger: single-entry rows with reversals, balance kept by trigger).
- **The table is `sacco_memberships`, not `memberships`.** The agreed rules
  in `docs/roles-permissions.md` match the database.
- **Ids are `integer` (32-bit), not `bigint`.** Money columns are `bigint`
  minor units, as documented.
- **`audit_logs` has no before/after JSON.** It stores `action`, `target`
  text, `actor_id` and `sacco_id` only (see item 7 of the release report).
- **Untracked files in `docs/`:** `docs/schema.sql` is an old `pg_dump`, and
  `docs/schema.md` and `docs/users-members-roles-erd.md` describe a different
  layout (`memberships`, `otp_codes`, `sacco_pins`, staff posting money).
  None of them is in git; none matches this database.
- **Row-level security is off on every table** in `nexora_dev` at `0021`.
  Item 3 of `move-6/collins-final` adds it in a new migration.
- **`alembic_version`** is Alembic's bookkeeping table and is not grouped.

## Identity

### `users`

Added in `0001`. Owner `nexora_user`. Primary key: `id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `id` | integer | no | `nextval('users_id_seq'::regclass)` | 0001 |
| `email` | character varying(255) | no |  | 0001 |
| `password_hash` | character varying(255) | no |  | 0001 |
| `failed_login_count` | integer | no | `0` | 0001 |
| `locked_until` | timestamp with time zone | yes |  | 0001 |
| `created_at` | timestamp with time zone | no | `now()` | 0001 |
| `is_platform_owner` | boolean | no | `false` | 0006 |
| `token_version` | integer | no | `0` | 0008 |
| `email_verified_at` | timestamp with time zone | yes |  | 0008 |

Unique indexes:

- `uq_users_email_lower` (0003): `btree (lower((email)::text))`
- `users_pkey` (constraint): `btree (id)`

Checks:

- `ck_users_failed_login_count_non_negative`: `CHECK ((failed_login_count >= 0))`

### `user_phones`

Added in `0011`. Owner `nexora_user`. Primary key: `id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `id` | integer | no | `nextval('user_phones_id_seq'::regclass)` | 0011 |
| `user_id` | integer | no |  | 0011 |
| `phone` | character varying(20) | no |  | 0011 |
| `verified_at` | timestamp with time zone | yes |  | 0011 |
| `created_at` | timestamp with time zone | no | `now()` | 0011 |

Foreign keys:

- `user_phones_user_id_fkey`: `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`

Unique indexes:

- `user_phones_phone_key` (constraint): `btree (phone)`
- `user_phones_pkey` (constraint): `btree (id)`

Checks:

- `ck_user_phones_phone_not_blank`: `CHECK ((btrim((phone)::text) <> ''::text))`

### `refresh_tokens`

Added in `0002`. Owner `nexora_user`. Primary key: `id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `id` | integer | no | `nextval('refresh_tokens_id_seq'::regc...` | 0002 |
| `user_id` | integer | no |  | 0002 |
| `jti` | character varying(64) | no |  | 0002 |
| `expires_at` | timestamp with time zone | no |  | 0002 |
| `revoked_at` | timestamp with time zone | yes |  | 0002 |
| `created_at` | timestamp with time zone | no | `now()` | 0002 |

Foreign keys:

- `refresh_tokens_user_id_fkey`: `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`

Unique indexes:

- `refresh_tokens_jti_key` (constraint): `btree (jti)`
- `refresh_tokens_pkey` (constraint): `btree (id)`

### `email_verifications`

Added in `0008`. Owner `nexora_user`. Primary key: `id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `id` | integer | no | `nextval('email_verifications_id_seq':...` | 0008 |
| `user_id` | integer | no |  | 0008 |
| `token_hash` | character varying(64) | no |  | 0008 |
| `expires_at` | timestamp with time zone | no |  | 0008 |
| `created_at` | timestamp with time zone | no | `now()` | 0008 |
| `purpose` | character varying(16) | no | `'verify'::character varying` | 0009 |

Foreign keys:

- `email_verifications_user_id_fkey`: `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`

Unique indexes:

- `email_verifications_pkey` (constraint): `btree (id)`
- `email_verifications_token_hash_key` (constraint): `btree (token_hash)`

Checks:

- `ck_email_verifications_purpose`: `CHECK (((purpose)::text = ANY ((ARRAY['verify'::character varying, 'reset'::character varying])::text[])))`

### `join_codes`

Added in `0011`. Owner `nexora_user`. Primary key: `id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `id` | integer | no | `nextval('join_codes_id_seq'::regclass)` | 0011 |
| `membership_id` | integer | no |  | 0011 |
| `code_digest` | character varying(255) | no |  | 0011 |
| `expires_at` | timestamp with time zone | no |  | 0011 |
| `used_at` | timestamp with time zone | yes |  | 0011 |
| `attempts` | integer | no | `0` | 0011 |
| `created_by_user_id` | integer | yes |  | 0011 |
| `created_at` | timestamp with time zone | no | `now()` | 0011 |

Foreign keys:

- `join_codes_created_by_user_id_fkey`: `FOREIGN KEY (created_by_user_id) REFERENCES users(id)`
- `join_codes_membership_id_fkey`: `FOREIGN KEY (membership_id) REFERENCES sacco_memberships(id) ON DELETE CASCADE`

Unique indexes:

- `join_codes_pkey` (constraint): `btree (id)`

Checks:

- `ck_join_codes_attempts_non_negative`: `CHECK ((attempts >= 0))`
- `ck_join_codes_expires_after_creation`: `CHECK ((expires_at > created_at))`

## SACCO and membership

### `saccos`

Added in `0001`. Owner `nexora_user`. Primary key: `id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `id` | integer | no | `nextval('saccos_id_seq'::regclass)` | 0001 |
| `name` | character varying(255) | no |  | 0001 |
| `status` | sacco_status | no | `'active'::sacco_status` | 0001 |
| `created_at` | timestamp with time zone | no | `now()` | 0001 |
| `currency` | character varying(3) | no | `'KES'::character varying` | 0006 |

Unique indexes:

- `saccos_pkey` (constraint): `btree (id)`
- `uq_saccos_name_lower` (0004): `btree (lower(btrim((name)::text)))`

Checks:

- `ck_saccos_currency_iso`: `CHECK (((currency)::text ~ '^[A-Z]{3}$'::text))`
- `ck_saccos_name_not_blank`: `CHECK ((btrim((name)::text) <> ''::text))`

### `sacco_memberships`

Added in `0001`. Owner `nexora_user`. Primary key: `id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `id` | integer | no | `nextval('sacco_memberships_id_seq'::r...` | 0001 |
| `user_id` | integer | yes |  | 0001 |
| `sacco_id` | integer | no |  | 0001 |
| `role` | membership_role | no |  | 0001 |
| `created_at` | timestamp with time zone | no | `now()` | 0001 |
| `status` | membership_status | no | `'active'::membership_status` | 0006 |
| `pin_hash` | character varying(255) | yes |  | 0011 |
| `pin_attempts` | integer | no | `0` | 0011 |
| `pin_locked_until` | timestamp with time zone | yes |  | 0011 |
| `phone` | character varying(20) | yes |  | 0015 |

Foreign keys:

- `sacco_memberships_sacco_id_fkey`: `FOREIGN KEY (sacco_id) REFERENCES saccos(id)`
- `sacco_memberships_user_id_fkey`: `FOREIGN KEY (user_id) REFERENCES users(id)`

Unique indexes:

- `sacco_memberships_pkey` (constraint): `btree (id)`
- `uq_membership_id_sacco` (constraint): `btree (id, sacco_id)`
- `uq_membership_sacco_phone` (constraint): `btree (sacco_id, phone)`
- `uq_membership_user_sacco` (constraint): `btree (user_id, sacco_id)`

Checks:

- `ck_membership_user_or_phone`: `CHECK (((user_id IS NOT NULL) OR (phone IS NOT NULL)))`
- `ck_memberships_pin_attempts_non_negative`: `CHECK ((pin_attempts >= 0))`

Triggers:

- `trg_membership_user_immutable` (0005): BEFORE UPDATE OF user_id

### `sacco_settings`

Added in `0011`. Owner `nexora_user`. Primary key: `sacco_id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `sacco_id` | integer | no |  | 0011 |
| `loan_cap` | bigint | no | `'0'::bigint` | 0011 |
| `savings_multiple` | integer | no | `3` | 0011 |
| `join_code_ttl_minutes` | integer | no | `15` | 0011 |
| `updated_at` | timestamp with time zone | no | `now()` | 0011 |
| `required_approvals` | integer | no | `2` | 0017 |

Foreign keys:

- `sacco_settings_sacco_id_fkey`: `FOREIGN KEY (sacco_id) REFERENCES saccos(id) ON DELETE CASCADE`

Unique indexes:

- `sacco_settings_pkey` (constraint): `btree (sacco_id)`

Checks:

- `ck_sacco_settings_loan_cap_non_negative`: `CHECK ((loan_cap >= 0))`
- `ck_sacco_settings_multiple_non_negative`: `CHECK ((savings_multiple >= 0))`
- `ck_sacco_settings_required_approvals_positive`: `CHECK ((required_approvals >= 1))`
- `ck_sacco_settings_ttl_positive`: `CHECK ((join_code_ttl_minutes > 0))`

## Roles and permissions

### `roles`

Added in `0010`. Owner `nexora_user`. Primary key: `id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `id` | integer | no | `nextval('roles_id_seq'::regclass)` | 0010 |
| `code` | character varying(32) | no |  | 0010 |
| `name` | character varying(64) | no |  | 0010 |
| `created_at` | timestamp with time zone | no | `now()` | 0010 |

Unique indexes:

- `roles_code_key` (constraint): `btree (code)`
- `roles_pkey` (constraint): `btree (id)`

### `permissions`

Added in `0010`. Owner `nexora_user`. Primary key: `id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `id` | integer | no | `nextval('permissions_id_seq'::regclass)` | 0010 |
| `code` | character varying(64) | no |  | 0010 |
| `description` | character varying(255) | yes |  | 0010 |

Unique indexes:

- `permissions_code_key` (constraint): `btree (code)`
- `permissions_pkey` (constraint): `btree (id)`

### `role_permissions`

Added in `0010`. Owner `nexora_user`. Primary key: `role_id, permission_id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `role_id` | integer | no |  | 0010 |
| `permission_id` | integer | no |  | 0010 |

Foreign keys:

- `role_permissions_permission_id_fkey`: `FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE`
- `role_permissions_role_id_fkey`: `FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE`

Unique indexes:

- `role_permissions_pkey` (constraint): `btree (role_id, permission_id)`

### `membership_roles`

Added in `0010`. Owner `nexora_user`. Primary key: `membership_id, role_id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `membership_id` | integer | no |  | 0010 |
| `role_id` | integer | no |  | 0010 |
| `granted_by_user_id` | integer | yes |  | 0021 |

Foreign keys:

- `fk_membership_roles_granted_by`: `FOREIGN KEY (granted_by_user_id) REFERENCES users(id)`
- `membership_roles_membership_id_fkey`: `FOREIGN KEY (membership_id) REFERENCES sacco_memberships(id) ON DELETE CASCADE`
- `membership_roles_role_id_fkey`: `FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE`

Unique indexes:

- `membership_roles_pkey` (constraint): `btree (membership_id, role_id)`

Triggers:

- `trg_membership_roles_no_self_grant` (0021): BEFORE INSERT OR UPDATE

### `platform_grants`

Added in `0010`. Owner `nexora_user`. Primary key: `user_id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `user_id` | integer | no |  | 0010 |
| `granted_at` | timestamp with time zone | no | `now()` | 0010 |
| `granted_by_user_id` | integer | yes |  | 0010 |

Foreign keys:

- `platform_grants_granted_by_user_id_fkey`: `FOREIGN KEY (granted_by_user_id) REFERENCES users(id)`
- `platform_grants_user_id_fkey`: `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`

Unique indexes:

- `platform_grants_pkey` (constraint): `btree (user_id)`

## Money

### `savings_accounts`

Added in `0001`. Owner `nexora_user`. Primary key: `id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `id` | integer | no | `nextval('savings_accounts_id_seq'::re...` | 0001 |
| `membership_id` | integer | no |  | 0001 |
| `sacco_id` | integer | no |  | 0001 |
| `balance` | bigint | no | `'0'::bigint` | 0001 |
| `created_at` | timestamp with time zone | no | `now()` | 0001 |

Foreign keys:

- `fk_savings_membership_sacco`: `FOREIGN KEY (membership_id, sacco_id) REFERENCES sacco_memberships(id, sacco_id)`
- `savings_accounts_sacco_id_fkey`: `FOREIGN KEY (sacco_id) REFERENCES saccos(id)`

Unique indexes:

- `savings_accounts_pkey` (constraint): `btree (id)`
- `uq_savings_account_id_sacco` (constraint): `btree (id, sacco_id)`
- `uq_savings_account_membership` (constraint): `btree (membership_id)`

Checks:

- `ck_savings_accounts_balance_non_negative`: `CHECK ((balance >= 0))`

Triggers:

- `trg_savings_accounts_guard_balance` (0005): BEFORE INSERT OR UPDATE OF balance

### `transactions`

Added in `0001`. Owner `nexora_user`. Primary key: `id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `id` | integer | no | `nextval('transactions_id_seq'::regclass)` | 0001 |
| `sacco_id` | integer | no |  | 0001 |
| `savings_account_id` | integer | no |  | 0001 |
| `type` | transaction_type | no |  | 0001 |
| `amount` | bigint | no |  | 0001 |
| `created_at` | timestamp with time zone | no | `now()` | 0001 |
| `reference` | character varying(64) | no |  | 0006 |
| `created_by_membership_id` | integer | no |  | 0006 |
| `reverses_id` | integer | yes |  | 0006 |

Foreign keys:

- `fk_transactions_created_by_sacco`: `FOREIGN KEY (created_by_membership_id, sacco_id) REFERENCES sacco_memberships(id, sacco_id)`
- `fk_transactions_reverses_sacco`: `FOREIGN KEY (reverses_id, sacco_id) REFERENCES transactions(id, sacco_id)`
- `fk_transactions_savings_sacco`: `FOREIGN KEY (savings_account_id, sacco_id) REFERENCES savings_accounts(id, sacco_id)`
- `transactions_sacco_id_fkey`: `FOREIGN KEY (sacco_id) REFERENCES saccos(id)`

Unique indexes:

- `transactions_pkey` (constraint): `btree (id)`
- `transactions_reverses_id_key` (constraint): `btree (reverses_id)`
- `uq_transactions_id_sacco` (constraint): `btree (id, sacco_id)`
- `uq_transactions_sacco_reference` (constraint): `btree (sacco_id, reference)`

Checks:

- `ck_transactions_amount_positive`: `CHECK ((amount > 0))`

Triggers:

- `trg_transactions_append_only` (0020): BEFORE DELETE OR UPDATE
- `trg_transactions_apply_balance` (0005): AFTER INSERT
- `trg_transactions_no_truncate` (0005): BEFORE TRUNCATE
- `trg_transactions_no_update_delete` (0001): BEFORE DELETE OR UPDATE
- `trg_transactions_validate` (0006): BEFORE INSERT

## Loans

### `loans`

Added in `0012`. Owner `nexora_user`. Primary key: `id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `id` | integer | no | `nextval('loans_id_seq'::regclass)` | 0012 |
| `sacco_id` | integer | no |  | 0012 |
| `membership_id` | integer | no |  | 0012 |
| `principal` | bigint | no |  | 0012 |
| `required_approvals` | integer | no |  | 0012 |
| `status` | loan_status | no | `'requested'::loan_status` | 0012 |
| `requested_by_membership_id` | integer | yes |  | 0012 |
| `disbursed_by_membership_id` | integer | yes |  | 0012 |
| `disbursed_at` | timestamp with time zone | yes |  | 0012 |
| `created_at` | timestamp with time zone | no | `now()` | 0012 |
| `disbursement_transaction_id` | integer | yes |  | 0017 |
| `term_months` | integer | yes |  | 0018 |

Foreign keys:

- `fk_loans_disbursement_transaction`: `FOREIGN KEY (disbursement_transaction_id) REFERENCES transactions(id)`
- `fk_loans_membership_sacco`: `FOREIGN KEY (membership_id, sacco_id) REFERENCES sacco_memberships(id, sacco_id)`
- `loans_disbursed_by_membership_id_fkey`: `FOREIGN KEY (disbursed_by_membership_id) REFERENCES sacco_memberships(id)`
- `loans_requested_by_membership_id_fkey`: `FOREIGN KEY (requested_by_membership_id) REFERENCES sacco_memberships(id)`
- `loans_sacco_id_fkey`: `FOREIGN KEY (sacco_id) REFERENCES saccos(id)`

Unique indexes:

- `loans_pkey` (constraint): `btree (id)`
- `uq_loans_disbursement_transaction` (constraint): `btree (disbursement_transaction_id)`
- `uq_loans_id_sacco` (constraint): `btree (id, sacco_id)`
- `uq_loans_one_open_per_member` (0018): `btree (membership_id) WHERE (status = ANY (ARRAY['requested'::loan_status, 'approved'::loan_status, 'disbursed'::loan_status]))`

Checks:

- `ck_loans_principal_positive`: `CHECK ((principal > 0))`
- `ck_loans_required_approvals_positive`: `CHECK ((required_approvals >= 1))`
- `ck_loans_term_months_positive`: `CHECK (((term_months IS NULL) OR (term_months > 0)))`

Triggers:

- `trg_loans_guard_update` (0020): BEFORE UPDATE

### `loan_decisions`

Added in `0012`. Owner `nexora_user`. Primary key: `id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `id` | integer | no | `nextval('loan_decisions_id_seq'::regc...` | 0012 |
| `loan_id` | integer | no |  | 0012 |
| `step` | integer | no |  | 0012 |
| `decision` | loan_decision_kind | no |  | 0012 |
| `decided_by_membership_id` | integer | no |  | 0012 |
| `created_at` | timestamp with time zone | no | `now()` | 0012 |
| `reason` | text | yes |  | 0018 |

Foreign keys:

- `loan_decisions_decided_by_membership_id_fkey`: `FOREIGN KEY (decided_by_membership_id) REFERENCES sacco_memberships(id)`
- `loan_decisions_loan_id_fkey`: `FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE CASCADE`

Unique indexes:

- `loan_decisions_pkey` (constraint): `btree (id)`
- `uq_loan_decisions_loan_step` (constraint): `btree (loan_id, step)`

Checks:

- `ck_loan_decisions_reject_has_reason`: `CHECK (((decision <> 'reject'::loan_decision_kind) OR (btrim(COALESCE(reason, ''::text)) <> ''::text)))`
- `ck_loan_decisions_step_positive`: `CHECK ((step >= 1))`

Triggers:

- `trg_loan_decisions_append_only` (0018): BEFORE DELETE OR UPDATE

### `loan_repayments`

Added in `0012`. Owner `nexora_user`. Primary key: `id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `id` | integer | no | `nextval('loan_repayments_id_seq'::reg...` | 0012 |
| `loan_id` | integer | no |  | 0012 |
| `transaction_id` | integer | no |  | 0012 |
| `amount` | bigint | no |  | 0012 |
| `created_at` | timestamp with time zone | no | `now()` | 0012 |

Foreign keys:

- `loan_repayments_loan_id_fkey`: `FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE CASCADE`
- `loan_repayments_transaction_id_fkey`: `FOREIGN KEY (transaction_id) REFERENCES transactions(id)`

Unique indexes:

- `loan_repayments_pkey` (constraint): `btree (id)`
- `loan_repayments_transaction_id_key` (constraint): `btree (transaction_id)`

Checks:

- `ck_loan_repayments_amount_positive`: `CHECK ((amount > 0))`

Triggers:

- `trg_loan_repayments_append_only` (0018): BEFORE DELETE OR UPDATE

## Audit

### `audit_logs`

Added in `0001`. Owner `nexora_user`. Primary key: `id`.

| Column | Type | Null | Default | Added in |
|---|---|---|---|---|
| `id` | integer | no | `nextval('audit_logs_id_seq'::regclass)` | 0001 |
| `sacco_id` | integer | yes |  | 0001 |
| `actor_id` | integer | yes |  | 0001 |
| `action` | character varying(100) | no |  | 0001 |
| `target` | character varying(255) | yes |  | 0001 |
| `created_at` | timestamp with time zone | no | `now()` | 0001 |

Foreign keys:

- `audit_logs_actor_id_fkey`: `FOREIGN KEY (actor_id) REFERENCES users(id)`
- `audit_logs_sacco_id_fkey`: `FOREIGN KEY (sacco_id) REFERENCES saccos(id)`

Unique indexes:

- `audit_logs_pkey` (constraint): `btree (id)`

Checks:

- `ck_audit_logs_action_not_blank`: `CHECK ((btrim((action)::text) <> ''::text))`

Triggers:

- `trg_audit_logs_append_only` (0005): BEFORE DELETE OR UPDATE
- `trg_audit_logs_no_truncate` (0005): BEFORE TRUNCATE

## Other tables

- `alembic_version` (added in `?`), columns: `version_num` character varying(32)

