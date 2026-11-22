"""Circle rules: the loan cap check, the lock during a cycle, accept before join."""

import uuid
from datetime import UTC, datetime

import pytest

from app.auth.tokens import create_access_token
from app.extensions import db
from app.loans import service as loan_service
from app.models.rules import RulesAcceptance
from app.models.user import User
from app.saccos import rules as circle_rules
from app.savings.service import Conflict
from savings_support import Setup, release_session, schema_app  # noqa: F401

pytestmark = pytest.mark.schema

RULES = {
    "contribution_amount": 50_000,
    "contribution_frequency": "weekly",
    "interest_percent": 10,
    "repayment_period_value": 6,
    "repayment_period_unit": "months",
    "late_fine_amount": 5_000,
}


def _auth(user):
    token = create_access_token(user.id, getattr(user, "token_version", 0))
    return {"Authorization": f"Bearer {token}"}


def test_a_loan_above_the_cap_or_the_pool_is_refused_in_plain_words(schema_app):  # noqa: F811
    s = Setup(balance=10_000)  # savings of KES 100.00
    values, errors = circle_rules.validate_rules(RULES)
    assert not errors and values["loan_cap_multiple"] == 3  # the default
    rules = circle_rules.publish_rules(s.sacco.id, values, s.admin.id)
    circle_rules.accept(s.member_membership.id, rules.id)
    db.session.commit()

    # 3 x savings is KES 300.00, so KES 400.00 is over the cap.
    with pytest.raises(Conflict) as over:
        loan_service.request_loan(s.member.id, s.sacco.id, 40_000, 3)
    assert over.value.code == "LOAN_OVER_CAP", over.value.message
    assert "up to 3 times your savings" in over.value.message
    assert "KES 300.00" in over.value.message

    # Inside the cap, but the circle only holds KES 100.00.
    with pytest.raises(Conflict) as short:
        loan_service.request_loan(s.member.id, s.sacco.id, 20_000, 3)
    assert short.value.code == "LOAN_POOL_SHORT"

    assert (
        loan_service.request_loan(s.member.id, s.sacco.id, 10_000, 3).principal
        == 10_000
    )


def test_rules_cannot_be_changed_during_the_cycle(schema_app):  # noqa: F811
    client = schema_app.test_client()
    s = Setup()
    url = f"/api/v1/saccos/{s.sacco.id}/rules"
    admin = db.session.get(User, s.admin.id)

    first = client.post(url, json=RULES, headers=_auth(admin))
    assert first.status_code == 201, first.get_data(as_text=True)

    again = client.post(
        url, json={**RULES, "late_fine_amount": 0}, headers=_auth(admin)
    )
    assert again.status_code == 409
    assert again.get_json()["error"]["code"] == "RULES_LOCKED"
    assert "locked until" in again.get_json()["error"]["message"]

    # A change also cannot be proposed until the cycle has ended.
    early = client.post(f"{url}/proposals", json=RULES, headers=_auth(admin))
    assert early.status_code == 409


def test_a_member_must_accept_the_rules_before_joining(schema_app):  # noqa: F811
    client = schema_app.test_client()
    s = Setup()
    admin = db.session.get(User, s.admin.id)
    base = f"/api/v1/saccos/{s.sacco.id}"
    assert (
        client.post(f"{base}/rules", json=RULES, headers=_auth(admin)).status_code
        == 201
    )

    phone = "+2547" + str(uuid.uuid4().int)[:8]
    invite = client.post(f"{base}/members", json={"phone": phone}, headers=_auth(admin))
    assert invite.status_code == 201, invite.get_data(as_text=True)
    joiner = User(
        email=f"j-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        email_verified_at=datetime.now(UTC),
    )
    db.session.add(joiner)
    db.session.commit()
    me = _auth(joiner)
    joined = client.post(
        "/api/v1/auth/join",
        json={"phone": phone, "code": invite.get_json()["join_code"]},
        headers=me,
    )
    token = joined.get_json()["setup_token"]

    # No acceptance yet: the PIN step is refused.
    blocked = client.post(
        "/api/v1/auth/join/pin", json={"setup_token": token, "pin": "2468"}, headers=me
    )
    assert blocked.status_code == 409
    assert blocked.get_json()["error"]["code"] == "RULES_NOT_ACCEPTED"

    # The member can read every rule, accept, and then finish.
    shown = client.post(
        "/api/v1/auth/join/rules", json={"setup_token": token}, headers=me
    )
    assert shown.get_json()["rules"]["interest_percent"] == 10
    accepted = client.post(
        "/api/v1/auth/join/rules/accept",
        json={"setup_token": token, "version": 1},
        headers=me,
    )
    assert accepted.status_code == 200
    done = client.post(
        "/api/v1/auth/join/pin", json={"setup_token": token, "pin": "2468"}, headers=me
    )
    assert done.status_code == 200
    # Who accepted which version is stored.
    stored = (
        db.session.query(RulesAcceptance)
        .filter_by(membership_id=invite.get_json()["id"])
        .one()
    )
    assert stored.rules_id == shown.get_json()["rules"]["id"]


def test_interest_has_no_default_and_every_error_says_what_to_send(schema_app):  # noqa: F811
    body = {k: v for k, v in RULES.items() if k != "interest_percent"}
    _, errors = circle_rules.validate_rules(body)
    assert set(errors) == {"interest_percent"}
    assert "no default" in errors["interest_percent"]
    _, errors = circle_rules.validate_rules(
        {**RULES, "cycle_months": 8, "late_fine_amount": -1}
    )
    assert (
        "9 to 12" in errors["cycle_months"] and "Example" in errors["late_fine_amount"]
    )


def test_after_the_cycle_a_majority_vote_adopts_the_next_version(schema_app):  # noqa: F811
    client = schema_app.test_client()
    s = Setup()
    base = f"/api/v1/saccos/{s.sacco.id}/rules"
    admin = db.session.get(User, s.admin.id)
    member = db.session.get(User, s.member.id)
    assert client.post(base, json=RULES, headers=_auth(admin)).status_code == 201
    for who in (admin, member):  # only members who accepted can vote
        accepted = client.post(
            f"{base}/accept", json={"version": 1}, headers=_auth(who)
        )
        assert accepted.status_code == 200
    rules = circle_rules.current_rules(s.sacco.id)
    rules.cycle_ends_on = circle_rules.today()  # the cycle has just ended
    db.session.commit()

    change = {**RULES, "late_fine_amount": 0}
    proposal = client.post(f"{base}/proposals", json=change, headers=_auth(admin))
    assert proposal.status_code == 201, proposal.get_data(as_text=True)
    url = f"{base}/proposals/{proposal.get_json()['proposal']['id']}/votes"
    one = client.post(url, json={"approve": True}, headers=_auth(admin))
    assert one.get_json()["proposal"]["status"] == "open"  # 1 of 2 is not a majority
    two = client.post(url, json={"approve": True}, headers=_auth(member))
    assert two.get_json()["proposal"]["status"] == "adopted"
    assert circle_rules.current_rules(s.sacco.id).version == 2


def test_bad_types_are_refused_not_crashed_and_old_votes_cannot_reopen(schema_app):  # noqa: F811
    client = schema_app.test_client()
    _, errors = circle_rules.validate_rules({**RULES, "repayment_period_unit": []})
    assert "repayment_period_value" in errors  # a list used to raise a TypeError
    _, errors = circle_rules.validate_rules({**RULES, "exit_rules": "\ud800"})
    assert "exit_rules" in errors  # a lone surrogate would break the insert

    s = Setup()
    admin = db.session.get(User, s.admin.id)
    base = f"/api/v1/saccos/{s.sacco.id}/rules"
    assert client.post(base, json=RULES, headers=_auth(admin)).status_code == 201
    odd = client.post(f"{base}/accept", json={"version": True}, headers=_auth(admin))
    assert odd.status_code == 409  # true is not version 1
    assert (
        client.post(
            f"{base}/accept", json={"version": 1}, headers=_auth(admin)
        ).status_code
        == 200
    )

    circle_rules.current_rules(s.sacco.id).cycle_ends_on = circle_rules.today()
    db.session.commit()
    first = client.post(f"{base}/proposals", json=RULES, headers=_auth(admin))
    assert first.status_code == 201
    second = client.post(f"{base}/proposals", json=RULES, headers=_auth(admin))
    assert second.status_code == 409  # one open vote per circle
