"""least-privilege application role: nexora_app

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-17 12:00:00.000000

Section 1. The application has been connecting as the database owner,
which can do anything. This creates a separate role for it:

* read and write on ordinary tables, so the app keeps working;
* read and insert only on `transactions` and `audit_logs`, because history is
  never rewritten — an UPDATE, DELETE or TRUNCATE is refused by privilege;
* usage on the sequences, so inserts get ids;
* no DDL: the role cannot create, alter or drop anything, and migrations stay
  the owner's job.

The role is created NOLOGIN with no password on purpose: a migration must not
carry a credential. A deployment (or a developer's `.env`) enables login and
sets the password out of band:

    ALTER ROLE nexora_app LOGIN PASSWORD '...';
    # then point DATABASE_URL at nexora_app instead of postgres

Until that happens the app keeps connecting as the owner, so this migration is
additive and cannot break a running environment.
"""
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

APP_ROLE = "nexora_app"
# Tables whose rows must never change once written.
HISTORY_TABLES = "transactions, audit_logs"


def upgrade():
    # Roles are cluster-wide, so create it only when it is missing.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
                CREATE ROLE {APP_ROLE} NOLOGIN;
            END IF;
        END
        $$;
        """
    )

    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
        f"TO {APP_ROLE}"
    )
    # Take history back: read and append only, never rewrite.
    op.execute(
        f"REVOKE UPDATE, DELETE, TRUNCATE ON {HISTORY_TABLES} FROM {APP_ROLE}"
    )
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE}")

    # Tables added by later migrations inherit the same baseline.
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_ROLE}"
    )
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT USAGE, SELECT ON SEQUENCES TO {APP_ROLE}"
    )

    # It must be able to connect to whichever database it was granted on.
    op.execute(
        f"""
        DO $$
        BEGIN
            EXECUTE format('GRANT CONNECT ON DATABASE %I TO {APP_ROLE}',
                           current_database());
        END
        $$;
        """
    )


def downgrade():
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"REVOKE ALL ON SEQUENCES FROM {APP_ROLE}"
    )
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"REVOKE ALL ON TABLES FROM {APP_ROLE}"
    )
    op.execute(
        f"""
        DO $$
        BEGIN
            EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM {APP_ROLE}',
                           current_database());
        END
        $$;
        """
    )
    op.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON SCHEMA public FROM {APP_ROLE}")

    # Roles are cluster-wide but grants are per database. Dropping the role from
    # here would fail (and break the downgrade of every other database) as soon
    # as it still holds privileges somewhere else -- a dev database, the test
    # database. So the role is dropped only once this database was the last one
    # using it; otherwise the grants above are all this migration owns, and the
    # role itself is left for an operator to remove with DROP OWNED BY.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}')
               AND NOT EXISTS (
                   SELECT 1
                   FROM pg_shdepend d
                   JOIN pg_roles r ON r.oid = d.refobjid
                   WHERE r.rolname = '{APP_ROLE}'
                     AND d.dbid <> 0
                     AND d.dbid <> (
                         SELECT oid FROM pg_database WHERE datname = current_database()
                     )
               )
            THEN
                DROP ROLE {APP_ROLE};
            END IF;
        END
        $$;
        """
    )
