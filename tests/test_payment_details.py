"""Circle pay-in details: formats, two-officer approval, audit, mail, tenancy.

Runs against the migration-built database (the CHECK constraints matter here).
"""

from datetime import datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.audit import AuditLog
from app.models.membership import MembershipStatus, SaccoMembership
from app.models.sacco import SaccoStatus
from app.models.user import User
from app.saccos import payment_details as logic
from savings_support import Setup, release_session, schema_app  # noqa: F401
from test_schema_rules import auth, make_user, officer

pytestmark = pytest.mark.schema

GOOD = {
    "mpesa_type": "paybill",
    "mpesa_number": "400200",
    "display_name": "Umoja Circle",
    "account_reference_hint": "your member number",
    "bank_name": "Equity Bank",
    "bank_account_name": "Umoja Circle",
    "bank_account_number": "0123456789",
    "bank_branch": "Kitale",
}


def url(s, tail=""):
    return f"/api/v1/saccos/{s.sacco.id}/payment-details{tail}"


def propose(client, user, s, **overrides):
    body = {**GOOD, **overrides}
    body = {k: v for k, v in body.items() if v is not ...}
    return client.post(url(s, "/changes"), json=body, headers=auth(user))


def approve(client, user, s, change_id):
    return client.post(url(s, f"/changes/{change_id}/approve"), headers=auth(user))


def read(client, user, s):
    return client.get(url(s), headers=auth(user))


@pytest.fixture
def mails(monkeypatch):
    sent = []
    monkeypatch.setattr(
        logic,
        "send_text_email",
        lambda to, subject, body: sent.append((to, subject, body)),
    )
    return sent


def circle():
    """A circle with an admin, a finance officer (the second officer) and a member."""
    s = Setup()
    s.finance = officer(s, "finance_officer")
    return s


# ---- formats: every rejection says the format, an example and why -------------

BAD = [
    ("mpesa_number", {"mpesa_number": "1234"}),
    ("mpesa_number", {"mpesa_number": "12345678"}),
    ("mpesa_number", {"mpesa_number": "40O200"}),
    ("mpesa_number", {"mpesa_number": "٤٠٠٢٠٠"}),  # Arabic-Indic digits
    ("mpesa_number", {"mpesa_number": "400 200"}),
    ("mpesa_number", {"mpesa_number": 400200}),
    ("mpesa_number", {"mpesa_number": ...}),  # a type with no number
    ("mpesa_type", {"mpesa_type": "bank"}),
    ("mpesa_type", {"mpesa_type": ...}),  # a number with no type
    ("display_name", {"display_name": ...}),
    ("display_name", {"display_name": "x" * 61}),
    ("display_name", {"display_name": 12}),
    ("display_name", {"display_name": "Umoja\nCircle"}),
    ("display_name", {"display_name": "bad\ud800"}),
    ("account_reference_hint", {"mpesa_type": "till", "account_reference_hint": "x"}),
    ("bank_account_number", {"bank_account_number": "12345"}),
    ("bank_account_number", {"bank_account_number": "1" * 21}),
    ("bank_account_number", {"bank_account_number": "0123 456789"}),
    ("bank_account_number", {"bank_account_number": ...}),
    ("bank_name", {"bank_name": ...}),
    ("bank_account_name", {"bank_account_name": ...}),
    ("bank_uses_shared_paybill", {"bank_uses_shared_paybill": "yes"}),
    ("bank_paybill_number", {"bank_uses_shared_paybill": True}),
    (
        "bank_paybill_number",
        {"bank_uses_shared_paybill": True, "bank_paybill_number": "12"},
    ),
    ("bank_paybill_number", {"bank_paybill_number": "247247"}),
]


@pytest.mark.parametrize(("field", "change"), BAD)
def test_a_bad_value_is_refused_with_format_example_and_reason(
    schema_app,  # noqa: F811
    field,
    change,
):
    s = circle()
    resp = propose(schema_app.test_client(), s.admin, s, **change)
    assert resp.status_code == 400, resp.json
    error = resp.json["error"]
    assert error["code"] == "validation_error"
    reason = error["fields"][field]
    assert len(reason) > 25
    assert "Example" in reason or "Send true" in reason or "empty" in reason
    assert read(schema_app.test_client(), s.member, s).json["details"] is None


def test_a_branch_without_a_bank_and_a_shared_paybill_without_a_bank(schema_app):  # noqa: F811
    s = circle()
    c = schema_app.test_client()
    only_mpesa = {
        "bank_name": ...,
        "bank_account_name": ...,
        "bank_account_number": ...,
    }
    branch = propose(c, s.admin, s, **only_mpesa)
    assert list(branch.json["error"]["fields"]) == ["bank_branch"]
    shared = propose(
        c,
        s.admin,
        s,
        bank_branch=...,
        bank_uses_shared_paybill=True,
        bank_paybill_number="247247",
        **only_mpesa,
    )
    assert "bank_uses_shared_paybill" in shared.json["error"]["fields"]


def test_some_method_is_needed_and_unknown_fields_are_refused(schema_app):  # noqa: F811
    s = circle()
    c = schema_app.test_client()
    empty = c.post(url(s, "/changes"), json={}, headers=auth(s.admin))
    assert empty.status_code == 400
    assert "M-Pesa details, bank details or both" in empty.json["error"]["fields"]["_"]
    extra = propose(c, s.admin, s, colour="red")
    assert extra.json["error"]["fields"]["_"] == "Unknown field(s): colour."
    assert logic.validate([])[1] == {"_": "Send the pay-in details as a JSON object."}


def test_a_circle_may_use_mpesa_only_or_bank_only(schema_app):  # noqa: F811
    s = circle()
    c = schema_app.test_client()
    bank_only = {k: ... for k in ("mpesa_type", "mpesa_number", "display_name")}
    bank_only["account_reference_hint"] = ...
    till = propose(c, s.admin, s, mpesa_type="till", account_reference_hint=...)
    bank = propose(c, s.admin, s, **bank_only)
    assert till.status_code == 201, till.json
    assert bank.status_code == 201, bank.json
    assert bank.json["change"]["values"]["mpesa_number"] is None


# ---- a change is not live until a second officer approves it -------------------


def test_a_proposal_is_not_live_until_approved(schema_app, mails):  # noqa: F811
    s = circle()
    c = schema_app.test_client()
    assert read(c, s.member, s).json == {"details": None, "pending": None}

    made = propose(c, s.admin, s)
    assert made.status_code == 201, made.json
    change = made.json["change"]
    assert change["status"] == "pending"

    # Members still see nothing, and never see the waiting change.
    assert read(c, s.member, s).json == {"details": None, "pending": None}
    # The proposer and the other officer both see it waiting.
    for officer_ in (s.admin, s.finance):
        waiting = read(c, officer_, s).json
        assert waiting["details"] is None
        assert waiting["pending"]["id"] == change["id"]

    done = approve(c, s.finance, s, change["id"])
    assert done.status_code == 200, done.json
    live = read(c, s.member, s).json
    assert live["pending"] is None
    assert live["details"]["mpesa_number"] == "400200"
    assert live["details"]["bank_account_number"] == "0123456789"
    assert live["details"]["updated_at"] == done.json["details"]["updated_at"]


def test_updated_at_is_the_approval_time_not_the_proposal_time(schema_app, mails):  # noqa: F811
    s = circle()
    c = schema_app.test_client()
    change = propose(c, s.admin, s).json["change"]
    live = approve(c, s.finance, s, change["id"]).json["details"]
    db.session.expire_all()
    row = db.session.execute(
        text(
            "SELECT proposed_at, approved_at FROM circle_payment_detail_changes "
            "WHERE id = :i"
        ),
        {"i": change["id"]},
    ).one()
    stamp = datetime.fromisoformat(live["updated_at"])
    assert stamp == row.approved_at
    assert stamp > row.proposed_at


def test_a_second_change_replaces_the_live_values(schema_app, mails):  # noqa: F811
    s = circle()
    c = schema_app.test_client()
    first = propose(c, s.admin, s).json["change"]
    approve(c, s.finance, s, first["id"])
    second = propose(c, s.finance, s, mpesa_number="400300").json["change"]
    # Still the old number until the other officer approves.
    assert read(c, s.member, s).json["details"]["mpesa_number"] == "400200"
    assert approve(c, s.admin, s, second["id"]).status_code == 200
    assert read(c, s.member, s).json["details"]["mpesa_number"] == "400300"
    db.session.expire_all()
    assert (
        db.session.execute(
            text("SELECT count(*) FROM circle_payment_details WHERE sacco_id = :s"),
            {"s": s.sacco.id},
        ).scalar_one()
        == 1
    )


def test_proposing_what_is_already_live_is_refused(schema_app, mails):  # noqa: F811
    s = circle()
    c = schema_app.test_client()
    approve(c, s.finance, s, propose(c, s.admin, s).json["change"]["id"])
    same = propose(c, s.admin, s)
    assert same.status_code == 409
    assert "already see" in same.json["error"]["message"]


def test_a_newer_proposal_replaces_the_waiting_one(schema_app, mails):  # noqa: F811
    s = circle()
    c = schema_app.test_client()
    old = propose(c, s.admin, s).json["change"]
    new = propose(c, s.admin, s, mpesa_number="400999").json["change"]
    stale = approve(c, s.finance, s, old["id"])
    assert stale.status_code == 409
    assert read(c, s.finance, s).json["pending"]["id"] == new["id"]
    assert approve(c, s.finance, s, new["id"]).status_code == 200
    again = approve(c, s.admin, s, new["id"])
    assert again.status_code == 409


def test_an_unknown_change_is_404(schema_app):  # noqa: F811
    s = circle()
    assert approve(schema_app.test_client(), s.finance, s, 999999).status_code == 404


# ---- two different people ------------------------------------------------------


def test_the_proposer_cannot_approve_their_own_change(schema_app, mails):  # noqa: F811
    s = circle()
    c = schema_app.test_client()
    change = propose(c, s.admin, s).json["change"]
    own = approve(c, s.admin, s, change["id"])
    assert own.status_code == 403
    assert own.json["error"]["code"] == "PAYIN_SAME_OFFICER"
    assert read(c, s.member, s).json["details"] is None
    assert read(c, s.admin, s).json["pending"]["status"] == "pending"


def test_one_officer_holding_two_titles_is_still_one_person(schema_app, mails):  # noqa: F811
    # Proposing and approving as the same user is refused whatever the title.
    s = circle()
    c = schema_app.test_client()
    change = propose(c, s.finance, s).json["change"]
    assert approve(c, s.finance, s, change["id"]).status_code == 403


def test_the_database_refuses_self_approval_and_a_second_pending(schema_app, mails):  # noqa: F811
    s = circle()
    c = schema_app.test_client()
    change = propose(c, s.admin, s).json["change"]
    with pytest.raises(IntegrityError):
        db.session.execute(
            text(
                "UPDATE circle_payment_detail_changes SET status = 'approved', "
                "approved_by = proposed_by, approved_at = now() WHERE id = :i"
            ),
            {"i": change["id"]},
        )
    db.session.rollback()
    with pytest.raises(IntegrityError):
        db.session.execute(
            text(
                "INSERT INTO circle_payment_detail_changes "
                "(sacco_id, proposed_by, mpesa_type, mpesa_number, display_name) "
                "VALUES (:s, :u, 'till', '123456', 'x')"
            ),
            {"s": s.sacco.id, "u": s.admin.id},
        )
    db.session.rollback()


def test_the_database_refuses_a_bad_number_even_if_the_app_does_not(schema_app):  # noqa: F811
    s = circle()
    with pytest.raises(IntegrityError):
        db.session.execute(
            text(
                "INSERT INTO circle_payment_details "
                "(sacco_id, updated_by, mpesa_type, mpesa_number, display_name) "
                "VALUES (:s, :u, 'paybill', '12', 'x')"
            ),
            {"s": s.sacco.id, "u": s.admin.id},
        )
    db.session.rollback()


# ---- who may ask --------------------------------------------------------------


def test_only_officers_with_the_permission_may_propose_or_approve(schema_app, mails):  # noqa: F811
    s = circle()
    c = schema_app.test_client()
    secretary = officer(s, "secretary")
    loans = officer(s, "loans_officer")
    change = propose(c, s.admin, s).json["change"]
    for user in (s.member, secretary, loans):
        assert propose(c, user, s).status_code == 403
        assert approve(c, user, s, change["id"]).status_code == 403
        # They can read what is live, but not what is waiting.
        assert read(c, user, s).json["pending"] is None


def test_a_platform_owner_reads_but_cannot_change_pay_in_details(schema_app, mails):  # noqa: F811
    s = circle()
    c = schema_app.test_client()
    owner = make_user(owner=True)
    change = propose(c, s.admin, s).json["change"]
    assert read(c, owner, s).status_code == 200
    assert propose(c, owner, s).status_code == 403
    assert approve(c, owner, s, change["id"]).status_code == 403


def test_a_removed_officer_can_no_longer_approve(schema_app, mails):  # noqa: F811
    s = circle()
    c = schema_app.test_client()
    change = propose(c, s.admin, s).json["change"]
    membership = (
        db.session.query(SaccoMembership)
        .filter_by(user_id=s.finance.id, sacco_id=s.sacco.id)
        .one()
    )
    membership.status = MembershipStatus.INACTIVE
    db.session.commit()
    db.session.remove()
    assert approve(c, s.finance, s, change["id"]).status_code == 403


def test_a_suspended_circle_answers_423(schema_app, mails):  # noqa: F811
    from app.models.sacco import Sacco

    s = circle()
    db.session.get(Sacco, s.sacco.id).status = SaccoStatus.SUSPENDED
    db.session.commit()
    db.session.remove()
    assert propose(schema_app.test_client(), s.admin, s).status_code == 423


# ---- another circle ------------------------------------------------------------


def test_someone_from_another_circle_gets_404_everywhere(schema_app, mails):  # noqa: F811
    s = circle()
    other = circle()
    c = schema_app.test_client()
    change = propose(c, s.admin, s).json["change"]
    approve(c, s.finance, s, change["id"])
    pending = propose(c, s.admin, s, mpesa_number="400555").json["change"]

    for outsider in (other.member, other.admin, other.finance):
        assert read(c, outsider, s).status_code == 404
        assert propose(c, outsider, s).status_code == 404
        assert approve(c, outsider, s, pending["id"]).status_code == 404
    # An officer's own circle's route cannot reach this circle's change either.
    for outsider in (other.admin, other.finance):
        assert approve(c, outsider, other, pending["id"]).status_code == 404
    assert read(c, s.member, s).json["details"]["mpesa_number"] == "400200"


def test_each_circle_has_its_own_details(schema_app, mails):  # noqa: F811
    a, b = circle(), circle()
    c = schema_app.test_client()
    approve(c, a.finance, a, propose(c, a.admin, a).json["change"]["id"])
    assert read(c, b.member, b).json["details"] is None
    assert read(c, a.member, a).json["details"] is not None


def test_a_signed_out_caller_gets_401(schema_app):  # noqa: F811
    s = circle()
    c = schema_app.test_client()
    assert c.get(url(s)).status_code == 401
    assert c.post(url(s, "/changes"), json=GOOD).status_code == 401


# ---- shared bank paybill -------------------------------------------------------


def test_a_shared_bank_paybill_is_marked_manual_confirm_only(schema_app, mails):  # noqa: F811
    s = circle()
    c = schema_app.test_client()
    plain = propose(c, s.admin, s).json["change"]
    assert plain["values"]["bank_manual_confirm_only"] is False
    shared = propose(
        c, s.admin, s, bank_uses_shared_paybill=True, bank_paybill_number="247247"
    ).json["change"]
    assert shared["values"]["bank_manual_confirm_only"] is True
    live = approve(c, s.finance, s, shared["id"]).json["details"]
    assert live["bank_manual_confirm_only"] is True
    assert live["bank_paybill_number"] == "247247"
    assert read(c, s.member, s).json["details"]["bank_manual_confirm_only"] is True


# ---- audit ---------------------------------------------------------------------


def test_every_proposal_and_approval_is_audited_without_the_numbers(schema_app, mails):  # noqa: F811
    s = circle()
    c = schema_app.test_client()
    first = propose(c, s.admin, s).json["change"]
    second = propose(c, s.finance, s, mpesa_number="400300").json["change"]
    approve(c, s.admin, s, second["id"])
    rows = (
        db.session.query(AuditLog)
        .filter(AuditLog.sacco_id == s.sacco.id, AuditLog.action.like("payin.%"))
        .order_by(AuditLog.id)
        .all()
    )
    assert [(r.action, r.actor_id) for r in rows] == [
        ("payin.propose", s.admin.id),
        ("payin.supersede", s.finance.id),
        ("payin.propose", s.finance.id),
        ("payin.approve", s.admin.id),
    ]
    assert rows[0].target.startswith(f"change:{first['id']} fields:")
    assert "mpesa_number" in rows[0].target
    assert rows[3].target == f"change:{second['id']}"
    everything = " ".join(r.target for r in rows)
    assert "400200" not in everything and "0123456789" not in everything


def test_a_refused_proposal_leaves_no_audit_row(schema_app, mails):  # noqa: F811
    s = circle()
    propose(schema_app.test_client(), s.admin, s, mpesa_number="1")
    count = (
        db.session.query(AuditLog)
        .filter(AuditLog.sacco_id == s.sacco.id, AuditLog.action.like("payin.%"))
        .count()
    )
    assert count == 0


# ---- officers are told ---------------------------------------------------------


def test_every_officer_and_only_officers_are_emailed(schema_app, mails):  # noqa: F811
    s = circle()
    secretary = officer(s, "secretary")
    c = schema_app.test_client()
    admin_email = db.session.get(User, s.admin.id).email
    finance_email = db.session.get(User, s.finance.id).email

    change = propose(c, s.admin, s).json["change"]
    assert sorted(to for to, _, _ in mails) == sorted([admin_email, finance_email])
    assert "waiting" in mails[0][1]
    assert "400200" not in mails[0][2]  # no numbers in an email
    assert admin_email in mails[0][2]
    assert db.session.get(User, secretary.id).email not in [to for to, _, _ in mails]

    mails.clear()
    approve(c, s.finance, s, change["id"])
    assert sorted(to for to, _, _ in mails) == sorted([admin_email, finance_email])
    assert "changed" in mails[0][1]


def test_an_inactive_officer_is_not_emailed(schema_app, mails):  # noqa: F811
    s = circle()
    membership = (
        db.session.query(SaccoMembership)
        .filter_by(user_id=s.finance.id, sacco_id=s.sacco.id)
        .one()
    )
    membership.status = MembershipStatus.INACTIVE
    finance_email = db.session.get(User, s.finance.id).email
    db.session.commit()
    db.session.remove()
    propose(schema_app.test_client(), s.admin, s)
    assert finance_email not in [to for to, _, _ in mails]


def test_a_mail_outage_does_not_fail_or_undo_the_change(schema_app, monkeypatch):  # noqa: F811
    def broken(*_):
        raise OSError("smtp down")

    monkeypatch.setattr(logic, "send_text_email", broken)
    s = circle()
    c = schema_app.test_client()
    made = propose(c, s.admin, s)
    assert made.status_code == 201
    assert approve(c, s.finance, s, made.json["change"]["id"]).status_code == 200
    assert read(c, s.member, s).json["details"] is not None


def test_a_failure_listing_the_officers_does_not_fail_the_change(
    schema_app,  # noqa: F811
    monkeypatch,
):
    def broken(_):
        raise RuntimeError("database hiccup")

    monkeypatch.setattr(logic, "officers", broken)
    s = circle()
    assert propose(schema_app.test_client(), s.admin, s).status_code == 201
