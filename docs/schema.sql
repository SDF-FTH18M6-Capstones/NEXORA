SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

CREATE TYPE public.membership_role AS ENUM (
    'sacco_admin',
    'staff',
    'member'
);

CREATE TYPE public.membership_status AS ENUM (
    'active',
    'inactive'
);

CREATE TYPE public.sacco_status AS ENUM (
    'active',
    'suspended'
);

CREATE TYPE public.transaction_type AS ENUM (
    'deposit',
    'withdrawal'
);

CREATE FUNCTION public.append_only() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only: % not allowed', TG_TABLE_NAME, TG_OP;
        END;
        $$;

CREATE FUNCTION public.apply_transaction_to_balance() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            UPDATE savings_accounts
            SET balance = balance + CASE NEW.type WHEN 'deposit' THEN NEW.amount ELSE -NEW.amount END
            WHERE id = NEW.savings_account_id;
            RETURN NULL;
        END;
        $$;

CREATE FUNCTION public.forbid_membership_user_change() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF NEW.user_id <> OLD.user_id THEN
                RAISE EXCEPTION 'sacco_memberships.user_id cannot change' USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$;

CREATE FUNCTION public.guard_balance() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF (TG_OP = 'INSERT' AND NEW.balance <> 0) OR (TG_OP = 'UPDATE' AND pg_trigger_depth() < 2) THEN
                RAISE EXCEPTION 'balance changes only through transactions' USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$;

CREATE FUNCTION public.transactions_append_only() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            RAISE EXCEPTION 'transactions is append-only: % not allowed', TG_OP;
        END;
        $$;

CREATE FUNCTION public.validate_transaction() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    DECLARE orig transactions%ROWTYPE;
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM sacco_memberships
                       WHERE id = NEW.created_by_membership_id AND status = 'active') THEN
            RAISE EXCEPTION 'transaction must be posted by an active membership'
                USING ERRCODE = 'check_violation';
        END IF;
        IF NEW.reverses_id IS NOT NULL THEN
            SELECT * INTO orig FROM transactions WHERE id = NEW.reverses_id;
            IF orig.savings_account_id <> NEW.savings_account_id
               OR orig.amount <> NEW.amount OR orig.type = NEW.type THEN
                RAISE EXCEPTION 'a reversal must be the opposite entry for the same account and amount'
                    USING ERRCODE = 'check_violation';
            END IF;
            IF orig.reverses_id IS NOT NULL THEN
                RAISE EXCEPTION 'a reversal cannot be reversed'
                    USING ERRCODE = 'check_violation';
            END IF;
        END IF;
        RETURN NEW;
    END;
    $$;

SET default_tablespace = '';

SET default_table_access_method = heap;

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);

CREATE TABLE public.audit_logs (
    id integer NOT NULL,
    sacco_id integer,
    actor_id integer,
    action character varying(100) NOT NULL,
    target character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_audit_logs_action_not_blank CHECK ((btrim((action)::text) <> ''::text))
);

CREATE SEQUENCE public.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;

CREATE TABLE public.email_verifications (
    id integer NOT NULL,
    user_id integer NOT NULL,
    token_hash character varying(64) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    purpose character varying(16) DEFAULT 'verify'::character varying NOT NULL,
    CONSTRAINT ck_email_verifications_purpose CHECK (((purpose)::text = ANY ((ARRAY['verify'::character varying, 'reset'::character varying])::text[])))
);

CREATE SEQUENCE public.email_verifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.email_verifications_id_seq OWNED BY public.email_verifications.id;

CREATE TABLE public.refresh_tokens (
    id integer NOT NULL,
    user_id integer NOT NULL,
    jti character varying(64) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE SEQUENCE public.refresh_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.refresh_tokens_id_seq OWNED BY public.refresh_tokens.id;

CREATE TABLE public.sacco_memberships (
    id integer NOT NULL,
    user_id integer NOT NULL,
    sacco_id integer NOT NULL,
    role public.membership_role NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    status public.membership_status DEFAULT 'active'::public.membership_status NOT NULL
);

CREATE SEQUENCE public.sacco_memberships_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.sacco_memberships_id_seq OWNED BY public.sacco_memberships.id;

CREATE TABLE public.saccos (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    status public.sacco_status DEFAULT 'active'::public.sacco_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    currency character varying(3) DEFAULT 'KES'::character varying NOT NULL,
    CONSTRAINT ck_saccos_currency_iso CHECK (((currency)::text ~ '^[A-Z]{3}$'::text)),
    CONSTRAINT ck_saccos_name_not_blank CHECK ((btrim((name)::text) <> ''::text))
);

CREATE SEQUENCE public.saccos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.saccos_id_seq OWNED BY public.saccos.id;

CREATE TABLE public.savings_accounts (
    id integer NOT NULL,
    membership_id integer NOT NULL,
    sacco_id integer NOT NULL,
    balance bigint DEFAULT '0'::bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_savings_accounts_balance_non_negative CHECK ((balance >= 0))
);

CREATE SEQUENCE public.savings_accounts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.savings_accounts_id_seq OWNED BY public.savings_accounts.id;

CREATE TABLE public.transactions (
    id integer NOT NULL,
    sacco_id integer NOT NULL,
    savings_account_id integer NOT NULL,
    type public.transaction_type NOT NULL,
    amount bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    reference character varying(64) NOT NULL,
    created_by_membership_id integer NOT NULL,
    reverses_id integer,
    CONSTRAINT ck_transactions_amount_positive CHECK ((amount > 0))
);

CREATE SEQUENCE public.transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.transactions_id_seq OWNED BY public.transactions.id;

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    failed_login_count integer DEFAULT 0 NOT NULL,
    locked_until timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    is_platform_owner boolean DEFAULT false NOT NULL,
    token_version integer DEFAULT 0 NOT NULL,
    email_verified_at timestamp with time zone,
    CONSTRAINT ck_users_failed_login_count_non_negative CHECK ((failed_login_count >= 0))
);

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);

ALTER TABLE ONLY public.email_verifications ALTER COLUMN id SET DEFAULT nextval('public.email_verifications_id_seq'::regclass);

ALTER TABLE ONLY public.refresh_tokens ALTER COLUMN id SET DEFAULT nextval('public.refresh_tokens_id_seq'::regclass);

ALTER TABLE ONLY public.sacco_memberships ALTER COLUMN id SET DEFAULT nextval('public.sacco_memberships_id_seq'::regclass);

ALTER TABLE ONLY public.saccos ALTER COLUMN id SET DEFAULT nextval('public.saccos_id_seq'::regclass);

ALTER TABLE ONLY public.savings_accounts ALTER COLUMN id SET DEFAULT nextval('public.savings_accounts_id_seq'::regclass);

ALTER TABLE ONLY public.transactions ALTER COLUMN id SET DEFAULT nextval('public.transactions_id_seq'::regclass);

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.email_verifications
    ADD CONSTRAINT email_verifications_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.email_verifications
    ADD CONSTRAINT email_verifications_token_hash_key UNIQUE (token_hash);

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_jti_key UNIQUE (jti);

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.sacco_memberships
    ADD CONSTRAINT sacco_memberships_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.saccos
    ADD CONSTRAINT saccos_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.savings_accounts
    ADD CONSTRAINT savings_accounts_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_reverses_id_key UNIQUE (reverses_id);

ALTER TABLE ONLY public.sacco_memberships
    ADD CONSTRAINT uq_membership_id_sacco UNIQUE (id, sacco_id);

ALTER TABLE ONLY public.sacco_memberships
    ADD CONSTRAINT uq_membership_user_sacco UNIQUE (user_id, sacco_id);

ALTER TABLE ONLY public.savings_accounts
    ADD CONSTRAINT uq_savings_account_id_sacco UNIQUE (id, sacco_id);

ALTER TABLE ONLY public.savings_accounts
    ADD CONSTRAINT uq_savings_account_membership UNIQUE (membership_id);

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT uq_transactions_id_sacco UNIQUE (id, sacco_id);

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT uq_transactions_sacco_reference UNIQUE (sacco_id, reference);

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);

CREATE INDEX ix_audit_logs_actor_id ON public.audit_logs USING btree (actor_id);

CREATE INDEX ix_audit_logs_sacco_id ON public.audit_logs USING btree (sacco_id);

CREATE INDEX ix_email_verifications_user_id ON public.email_verifications USING btree (user_id);

CREATE INDEX ix_refresh_tokens_expires_at ON public.refresh_tokens USING btree (expires_at);

CREATE INDEX ix_refresh_tokens_user_id ON public.refresh_tokens USING btree (user_id);

CREATE INDEX ix_sacco_memberships_sacco_id ON public.sacco_memberships USING btree (sacco_id);

CREATE INDEX ix_savings_accounts_sacco_id ON public.savings_accounts USING btree (sacco_id);

CREATE INDEX ix_transactions_account_created ON public.transactions USING btree (savings_account_id, created_at);

CREATE UNIQUE INDEX uq_saccos_name_lower ON public.saccos USING btree (lower(btrim((name)::text)));

CREATE UNIQUE INDEX uq_users_email_lower ON public.users USING btree (lower((email)::text));

CREATE TRIGGER trg_audit_logs_append_only BEFORE DELETE OR UPDATE ON public.audit_logs FOR EACH ROW EXECUTE FUNCTION public.append_only();

CREATE TRIGGER trg_audit_logs_no_truncate BEFORE TRUNCATE ON public.audit_logs FOR EACH STATEMENT EXECUTE FUNCTION public.append_only();

CREATE TRIGGER trg_membership_user_immutable BEFORE UPDATE OF user_id ON public.sacco_memberships FOR EACH ROW EXECUTE FUNCTION public.forbid_membership_user_change();

CREATE TRIGGER trg_savings_accounts_guard_balance BEFORE INSERT OR UPDATE OF balance ON public.savings_accounts FOR EACH ROW EXECUTE FUNCTION public.guard_balance();

CREATE TRIGGER trg_transactions_apply_balance AFTER INSERT ON public.transactions FOR EACH ROW EXECUTE FUNCTION public.apply_transaction_to_balance();

CREATE TRIGGER trg_transactions_no_truncate BEFORE TRUNCATE ON public.transactions FOR EACH STATEMENT EXECUTE FUNCTION public.append_only();

CREATE TRIGGER trg_transactions_no_update_delete BEFORE DELETE OR UPDATE ON public.transactions FOR EACH ROW EXECUTE FUNCTION public.transactions_append_only();

CREATE TRIGGER trg_transactions_validate BEFORE INSERT ON public.transactions FOR EACH ROW EXECUTE FUNCTION public.validate_transaction();

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.users(id);

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_sacco_id_fkey FOREIGN KEY (sacco_id) REFERENCES public.saccos(id);

ALTER TABLE ONLY public.email_verifications
    ADD CONSTRAINT email_verifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.savings_accounts
    ADD CONSTRAINT fk_savings_membership_sacco FOREIGN KEY (membership_id, sacco_id) REFERENCES public.sacco_memberships(id, sacco_id);

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT fk_transactions_created_by_sacco FOREIGN KEY (created_by_membership_id, sacco_id) REFERENCES public.sacco_memberships(id, sacco_id);

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT fk_transactions_reverses_sacco FOREIGN KEY (reverses_id, sacco_id) REFERENCES public.transactions(id, sacco_id);

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT fk_transactions_savings_sacco FOREIGN KEY (savings_account_id, sacco_id) REFERENCES public.savings_accounts(id, sacco_id);

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.sacco_memberships
    ADD CONSTRAINT sacco_memberships_sacco_id_fkey FOREIGN KEY (sacco_id) REFERENCES public.saccos(id);

ALTER TABLE ONLY public.sacco_memberships
    ADD CONSTRAINT sacco_memberships_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

ALTER TABLE ONLY public.savings_accounts
    ADD CONSTRAINT savings_accounts_sacco_id_fkey FOREIGN KEY (sacco_id) REFERENCES public.saccos(id);

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_sacco_id_fkey FOREIGN KEY (sacco_id) REFERENCES public.saccos(id);

