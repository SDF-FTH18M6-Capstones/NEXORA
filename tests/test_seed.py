# ruff: noqa: F811  (pytest fixtures imported from savings_support)
"""The dev seed script: idempotent, logins work, refuses non-dev databases."""

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models.audit import AuditLog
from app.models.ledger import Transaction
from app.models.membership import SaccoMembership
from app.models.sacco import Sacco
from app.models.savings import SavingsAccount
from app.models.user import User
from savings_support import release_session, schema_app  # noqa: F401

pytestmark = pytest.mark.schema

_PATH = Path(__file__).resolve().parents[1] / "backend" / "scripts" / "seed.py"
_spec = importlib.util.spec_from_file_location("nexora_seed", _PATH)
seed_script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed_script)

MODELS = (User, Sacco, SaccoMembership, SavingsAccount, Transaction, AuditLog)


def counts():
    db.session.remove()
    return [db.session.scalar(select(func.count()).select_from(m)) for m in MODELS]


def test_running_the_seed_twice_changes_nothing(schema_app):
    seed_script.seed(schema_app, require_dev=False)
    first = counts()
    seed_script.seed(schema_app, require_dev=False)
    assert counts() == first

    users, saccos, memberships, accounts, transactions, _ = first
    assert (users, saccos, memberships, accounts) == (11, 2, 10, 6)
    assert transactions == 14  # 6 movements and 1 reversal per SACCO
    reversals = db.session.scalar(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.reverses_id.is_not(None))
    )
    assert reversals == 2


def test_every_seeded_user_can_log_in(schema_app):
    seeded = seed_script.seed(schema_app, require_dev=False)
    client = schema_app.test_client()
    assert len(seeded) == 11
    for row in seeded:
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": row["email"], "password": seed_script.DEV_PASSWORD},
        )
        assert resp.status_code == 200, row["email"]


def test_the_seed_refuses_a_database_that_is_not_a_dev_one(schema_app):
    with pytest.raises(SystemExit) as excinfo:
        seed_script.seed(schema_app)
    assert "_dev" in str(excinfo.value)
