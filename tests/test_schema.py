from pathlib import Path

import pytest
from flask_migrate import downgrade, upgrade
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app import create_app
from app.extensions import db
from app.models.ledger import Transaction, TransactionType
from app.models.membership import MembershipRole, SaccoMembership
from app.models.sacco import Sacco, SaccoStatus
from app.models.savings import SavingsAccount
from app.models.user import User
from config import TestConfig

pytestmark = pytest.mark.schema

MIGRATIONS = str(Path(__file__).resolve().parents[1] / "backend" / "migrations")
_counter = iter(range(1, 100_000))


def _reset_schema():
    db.session.remove()
    db.session.execute(text("DROP SCHEMA public CASCADE"))
    db.session.execute(text("CREATE SCHEMA public"))
    db.session.commit()


@pytest.fixture(scope="module")
def schema_app():
    app = create_app(TestConfig)
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if "test" not in uri:
        raise RuntimeError(f"Refusing to migrate a non-test database: {uri}")
    with app.app_context():
        _reset_schema()
        upgrade(directory=MIGRATIONS, revision="head")
        yield app
        db.session.remove()
        downgrade(directory=MIGRATIONS, revision="base")


@pytest.fixture
def session(schema_app):
    yield db.session
    db.session.rollback()
    
    
# Helpers

def make_user(s):
    u = User(email=f"user{next(_counter)}@example.com", password_hash="x")
    s.add(u)
    s.flush()
    return u


def make_sacco(s, status=SaccoStatus.ACTIVE):
    sacco = Sacco(name=f"Sacco {next(_counter)}", status=status)
    s.add(sacco)
    s.flush()
    return sacco


def make_membership(s, user, sacco, role=MembershipRole.MEMBER):
    m = SaccoMembership(user_id=user.id, sacco_id=sacco.id, role=role)
    s.add(m)
    s.flush()
    return m


def make_savings(s, membership, sacco, balance=0):
    acc = SavingsAccount(membership_id=membership.id, sacco_id=sacco.id, balance=balance)
    s.add(acc)
    s.flush()
    return acc


def make_ledger_row(s, amount=100):
    sacco = make_sacco(s)
    m = make_membership(s, make_user(s), sacco)
    acc = make_savings(s, m, sacco)
    tx = Transaction(
        sacco_id=sacco.id,
        savings_account_id=acc.id,
        type=TransactionType.DEPOSIT,
        amount=amount,
    )
    s.add(tx)
    s.flush()
    return tx


# Constraint tests 

def test_negative_balance_rejected(session):
    sacco = make_sacco(session)
    m = make_membership(session, make_user(session), sacco)
    with pytest.raises(IntegrityError):
        make_savings(session, m, sacco, balance=-1)


def test_duplicate_membership_rejected(session):
    sacco = make_sacco(session)
    user = make_user(session)
    make_membership(session, user, sacco)
    with pytest.raises(IntegrityError):
        make_membership(session, user, sacco)


def test_suspended_is_valid_status(session):
    sacco = make_sacco(session, status=SaccoStatus.SUSPENDED)
    session.refresh(sacco)
    assert sacco.status is SaccoStatus.SUSPENDED


def test_unknown_sacco_status_rejected(session):
    with pytest.raises(DBAPIError):
        session.execute(
            text("INSERT INTO saccos (name, status) VALUES ('X', 'frozen')")
        )


def test_savings_account_must_match_membership_sacco(session):
    a = make_sacco(session)
    b = make_sacco(session)
    m = make_membership(session, make_user(session), a)
    with pytest.raises(IntegrityError):
        make_savings(session, m, b)


def test_zero_amount_ledger_row_rejected(session):
    with pytest.raises(IntegrityError):
        make_ledger_row(session, amount=0)


def test_ledger_row_cannot_be_updated(session):
    tx = make_ledger_row(session)
    with pytest.raises(DBAPIError):
        session.execute(
            text("UPDATE transactions SET amount = 999 WHERE id = :id"),
            {"id": tx.id},
        )


def test_ledger_row_cannot_be_deleted(session):
    tx = make_ledger_row(session)
    with pytest.raises(DBAPIError):
        session.execute(
            text("DELETE FROM transactions WHERE id = :id"),
            {"id": tx.id},
        )


# Migration test: KEEP LAST, it drops and rebuilds the schema

def test_downgrade_removes_all_tables(schema_app):
    downgrade(directory=MIGRATIONS, revision="base")
    tables = set(inspect(db.engine).get_table_names()) - {"alembic_version"}
    assert tables == set()
    upgrade(directory=MIGRATIONS, revision="head")