# ruff: noqa: F811  (pytest fixtures imported from savings_support)
"""A reversal may not drop savings below an open loan's cap, unless a SACCO admin
overrides it with a reason (and the override is audited)."""

import uuid

import pytest
from sqlalchemy import text

from app.auth.tokens import create_access_token
from app.extensions import db
from app.ledger import reversals
from app.models.audit import AuditLog
from app.savings import service
from app.security.permissions import ROLE_PERMISSIONS
from savings_support import Setup, release_session, schema_app  # noqa: F401
from test_sacco_rules import _approved_loan

pytestmark = pytest.mark.schema

REASON = "Deposit was posted to the wrong member"


def _headers(user):
    token = create_access_token(user.id, getattr(user, "token_version", 0))
    return {"Authorization": f"Bearer {token}"}


def _url(transaction_id):
    return f"/api/v1/savings/transactions/{transaction_id}/reversals"


def _ref():
    return f"r-{uuid.uuid4().hex[:8]}"


def _loan_setup():
    """Savings of KES 40.00 and an open loan of KES 40.00, which needs savings of
    at least KES 13.34 (principal / 3). Returns (setup, deposit, finance officer)."""
    s = Setup()
    deposit = service.deposit(s.admin.id, s.account.id, 4_000, "cap-d1")
    _, finance = _approved_loan(s, 4_000)
    return s, deposit, finance


def _ledger_count(account_id):
    db.session.remove()
    return db.session.execute(
        text("SELECT count(*) FROM transactions WHERE savings_account_id = :a"),
        {"a": account_id},
    ).scalar_one()


def _actions(sacco_id):
    db.session.remove()
    return [r.action for r in db.session.query(AuditLog).filter_by(sacco_id=sacco_id)]


def test_a_reversal_that_breaks_an_open_loans_cap_is_refused(schema_app):
    s, deposit, _ = _loan_setup()
    before = _ledger_count(s.account.id)
    with pytest.raises(service.Conflict) as blocked:
        reversals.reverse_transaction(s.admin.id, deposit.id, _ref())
    assert blocked.value.code == "LOAN_OVER_CAP"
    assert "KES 13.34" in blocked.value.message
    assert "override" in blocked.value.message
    assert _ledger_count(s.account.id) == before
    assert "savings.reverse_override" not in _actions(s.sacco.id)


def test_a_sacco_admin_can_override_with_a_reason_and_it_is_audited(schema_app):
    s, deposit, _ = _loan_setup()
    done = reversals.reverse_transaction(
        s.admin.id, deposit.id, _ref(), override_reason=REASON
    )
    assert done.balance == 0 and not done.replayed
    db.session.remove()
    row = (
        db.session.query(AuditLog)
        .filter_by(sacco_id=s.sacco.id, action="savings.reverse_override")
        .one()
    )
    assert row.actor_id == s.admin.id
    assert REASON in row.target and f"reverses:{deposit.id}" in row.target
    assert "savings.reverse" in _actions(s.sacco.id)


def test_a_finance_officer_cannot_override_even_though_they_can_reverse(schema_app):
    s, deposit, finance = _loan_setup()
    finance_id = finance.id
    before = _ledger_count(s.account.id)
    with pytest.raises(service.Forbidden):
        reversals.reverse_transaction(
            finance_id, deposit.id, _ref(), override_reason=REASON
        )
    assert _ledger_count(s.account.id) == before
    assert "savings.reverse_override" not in _actions(s.sacco.id)
    assert "savings.reverse_override" not in ROLE_PERMISSIONS["finance_officer"]
    code = "savings.reverse_override"
    holders = [r for r, p in ROLE_PERMISSIONS.items() if code in p]
    assert holders == ["sacco_admin"]


def test_a_reversal_that_keeps_savings_above_the_cap_needs_no_override(schema_app):
    s, _, _ = _loan_setup()
    extra = service.deposit(s.admin.id, s.account.id, 2_000, "cap-d2")  # now 6,000
    done = reversals.reverse_transaction(s.admin.id, extra.id, _ref())
    assert done.balance == 4_000
    # An override reason nobody needed is not an override: nothing is audited.
    again = service.deposit(s.admin.id, s.account.id, 500, "cap-d3")
    reversals.reverse_transaction(s.admin.id, again.id, _ref(), override_reason=REASON)
    assert "savings.reverse_override" not in _actions(s.sacco.id)


def test_reversing_a_withdrawal_adds_money_so_the_cap_is_not_in_play(schema_app):
    s = Setup(balance=10_000)
    withdrawal = service.withdraw(s.admin.id, s.account.id, 2_000, "cap-w1")
    _approved_loan(s, 4_000)
    done = reversals.reverse_transaction(s.admin.id, withdrawal.id, _ref())
    assert done.type == "deposit" and done.balance == 10_000


def test_without_an_open_loan_or_rules_a_reversal_is_free(schema_app):
    s = Setup()
    tx = service.deposit(s.admin.id, s.account.id, 4_000, "free-d1")
    assert reversals.reverse_transaction(s.admin.id, tx.id, _ref()).balance == 0


def test_the_endpoint_answers_409_then_201_with_a_reason_and_400_for_a_bad_one(
    schema_app,
):
    s, deposit, _ = _loan_setup()
    client = schema_app.test_client()
    blocked = client.post(
        _url(deposit.id), json={"reference": _ref()}, headers=_headers(s.admin)
    )
    assert blocked.status_code == 409
    assert blocked.json["error"]["code"] == "LOAN_OVER_CAP"
    for bad in ("short", 12345, "x" * 141, "   "):
        refused = client.post(
            _url(deposit.id),
            json={"reference": _ref(), "override_reason": bad},
            headers=_headers(s.admin),
        )
        assert refused.status_code == 400, bad
    done = client.post(
        _url(deposit.id),
        json={"reference": _ref(), "override_reason": REASON},
        headers=_headers(s.admin),
    )
    assert done.status_code == 201, done.json


@pytest.mark.parametrize(
    "bad", ["ok reason\x00 here", "line one\nline two here", "ok\u202ereason here"]
)
def test_an_override_reason_with_control_or_hidden_characters_is_400(schema_app, bad):
    s, deposit, _ = _loan_setup()
    done = schema_app.test_client().post(
        _url(deposit.id),
        json={"reference": _ref(), "override_reason": bad},
        headers=_headers(s.admin),
    )
    assert done.status_code == 400
    assert "savings.reverse_override" not in _actions(s.sacco.id)
