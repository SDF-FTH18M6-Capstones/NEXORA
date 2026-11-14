"""Shared fixtures and setup for the savings tests.

The savings tests need the real schema (the balance trigger, the ledger and audit
rules), so they run against the migration-built *_schema_test database, the same
one test_schema.py uses.
"""

import itertools
import uuid
from types import SimpleNamespace

import psycopg
import pytest
from flask_migrate import downgrade, upgrade

from app import create_app
from app.extensions import db
from app.models.membership import MembershipRole, SaccoMembership
from app.models.sacco import Sacco
from app.models.user import User
from app.savings import service
from config import TestConfig
from test_schema import MIGRATIONS, _ensure_database, _reset_schema, _schema_test_url

_counter = itertools.count(1)


@pytest.fixture(scope="module")
def schema_app():
    url = _schema_test_url()
    try:
        _ensure_database(url)
    except psycopg.Error as exc:
        pytest.fail(
            f"Could not create database {url.database!r}. Create it once with: "
            f"psql -U postgres -c 'CREATE DATABASE {url.database} "
            f"OWNER {url.username};'  ({exc})"
        )

    class SchemaConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = url.render_as_string(hide_password=False)

    app = create_app(SchemaConfig)
    with app.app_context():
        _reset_schema()
        upgrade(directory=MIGRATIONS, revision="head")
        yield app
        db.session.remove()
        downgrade(directory=MIGRATIONS, revision="base")


@pytest.fixture(autouse=True)
def release_session(schema_app):
    """Close the test's session so no open transaction blocks the next test."""
    yield
    db.session.remove()


def _ref(obj):
    # Plain ids only: ORM objects expire on commit and cannot cross threads.
    return SimpleNamespace(id=obj.id)


class Setup:
    """A fresh SACCO with an admin and one member whose account holds `balance`.

    The account is opened and funded through the service, so the ledger, the
    stored balance and the audit log all agree from the start.
    """

    def __init__(self, balance=0):
        n = next(_counter)
        tag = uuid.uuid4().hex[:8]

        sacco = Sacco(name=f"Savings Sacco {n} {tag}")
        admin = User(email=f"admin{n}-{tag}@example.com", password_hash="x")
        member = User(email=f"member{n}-{tag}@example.com", password_hash="x")
        db.session.add_all([sacco, admin, member])
        db.session.flush()

        admin_membership = SaccoMembership(
            user_id=admin.id, sacco_id=sacco.id, role=MembershipRole.SACCO_ADMIN
        )
        member_membership = SaccoMembership(
            user_id=member.id, sacco_id=sacco.id, role=MembershipRole.MEMBER
        )
        db.session.add_all([admin_membership, member_membership])
        db.session.flush()

        self.sacco = _ref(sacco)
        self.admin = _ref(admin)
        self.member = _ref(member)
        self.admin_membership = _ref(admin_membership)
        self.member_membership = _ref(member_membership)
        db.session.commit()

        self.account = _ref(
            service.open_account(self.admin.id, self.member_membership.id)
        )
        if balance:
            service.deposit(self.admin.id, self.account.id, balance, f"setup-{tag}")
        db.session.remove()
