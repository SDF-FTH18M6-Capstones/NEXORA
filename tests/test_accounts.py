# ruff: noqa: F811  (pytest fixtures imported from savings_support)
"""Savings account read endpoints and the admin account list (Move 4)."""

import uuid
from types import SimpleNamespace

import pytest

from app.extensions import db
from app.models.membership import MembershipRole, MembershipStatus, SaccoMembership
from app.models.user import User
from app.savings import service
from app.savings.balance import ledger_balance
from savings_support import Setup, release_session, schema_app  # noqa: F401
from test_history_admin import add_member, auth, suspend

pytestmark = pytest.mark.schema

SAVINGS = "/api/v1/savings"
ADMIN = "/api/v1/admin"

ACCOUNT_KEYS = {"id", "membership_id", "sacco_id", "balance", "created_at"}
LIST_KEYS = {"account_id", "membership_id", "email", "balance"}


def account_url(account_id):
    return f"{SAVINGS}/accounts/{account_id}"


def list_url(sacco_id):
    return f"{ADMIN}/saccos/{sacco_id}/accounts"


def make_owner():
    owner = User(
        email=f"owner-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        is_platform_owner=True,
    )
    db.session.add(owner)
    db.session.commit()
    owner_id = owner.id
    db.session.remove()
    return SimpleNamespace(id=owner_id, token_version=0)


def join(user_id, sacco_id):
    """Make `user_id` a member of another SACCO and return the membership id."""
    membership = SaccoMembership(
        user_id=user_id, sacco_id=sacco_id, role=MembershipRole.MEMBER
    )
    db.session.add(membership)
    db.session.commit()
    membership_id = membership.id
    db.session.remove()
    return membership_id


def add_extra_member(s):
    """Another member of the same SACCO with an account; returns the account id."""
    user = User(email=f"extra-{uuid.uuid4().hex[:10]}@example.com", password_hash="x")
    db.session.add(user)
    db.session.flush()
    membership = SaccoMembership(
        user_id=user.id, sacco_id=s.sacco.id, role=MembershipRole.MEMBER
    )
    db.session.add(membership)
    db.session.commit()
    account_id = service.open_account(s.admin.id, membership.id).id
    db.session.remove()
    return account_id


# ---------- GET /savings/accounts/<id> ----------


def test_member_reads_their_own_account(schema_app):
    s = Setup(balance=1000)
    resp = schema_app.test_client().get(
        account_url(s.account.id), headers=auth(s.member)
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert set(body) == ACCOUNT_KEYS
    assert body["id"] == s.account.id
    assert body["membership_id"] == s.member_membership.id
    assert body["sacco_id"] == s.sacco.id
    assert body["balance"] == 1000


def test_member_cannot_read_another_members_account(schema_app):
    s = Setup(balance=500)
    other = add_member(s)
    client = schema_app.test_client()
    assert client.get(account_url(s.account.id), headers=auth(other)).status_code == 404
    assert (
        client.get(account_url(other.account_id), headers=auth(other)).status_code
        == 200
    )


def test_admin_and_staff_read_any_account_in_their_sacco(schema_app):
    s = Setup(balance=500)
    staff = add_member(s, role=MembershipRole.STAFF, with_account=False)
    client = schema_app.test_client()
    for user in (s.admin, staff):
        resp = client.get(account_url(s.account.id), headers=auth(user))
        assert resp.status_code == 200


def test_other_sacco_and_missing_account_are_404(schema_app):
    s = Setup(balance=500)
    outsider = Setup()
    client = schema_app.test_client()
    resp = client.get(account_url(s.account.id), headers=auth(outsider.admin))
    assert resp.status_code == 404
    resp = client.get(account_url(2_000_000_000), headers=auth(s.admin))
    assert resp.status_code == 404


def test_the_platform_owner_reads_any_account(schema_app):
    s = Setup(balance=500)
    owner = make_owner()
    resp = schema_app.test_client().get(
        account_url(s.account.id), headers=auth(owner)
    )
    assert resp.status_code == 200
    assert resp.get_json()["balance"] == 500


def test_account_without_a_token_is_401(schema_app):
    s = Setup()
    assert schema_app.test_client().get(account_url(s.account.id)).status_code == 401


def test_an_inactive_membership_is_403(schema_app):
    s = Setup(balance=100)
    not_active = next(v for v in MembershipStatus if v is not MembershipStatus.ACTIVE)
    db.session.get(SaccoMembership, s.member_membership.id).status = not_active
    db.session.commit()
    db.session.remove()
    resp = schema_app.test_client().get(
        account_url(s.account.id), headers=auth(s.member)
    )
    assert resp.status_code == 403


def test_a_suspended_sacco_is_423(schema_app):
    s = Setup(balance=100)
    suspend(s.sacco.id)
    client = schema_app.test_client()
    for user in (s.admin, s.member):
        resp = client.get(account_url(s.account.id), headers=auth(user))
        assert resp.status_code == 423


def test_the_returned_balance_equals_the_ledger(schema_app):
    s = Setup(balance=1000)
    service.deposit(s.admin.id, s.account.id, 250, "acc-d2")
    service.withdraw(s.admin.id, s.account.id, 400, "acc-w1")
    resp = schema_app.test_client().get(
        account_url(s.account.id), headers=auth(s.member)
    )
    assert resp.get_json()["balance"] == 850
    assert resp.get_json()["balance"] == ledger_balance(s.account.id)


# ---------- GET /savings/accounts/me ----------


def test_me_lists_only_the_callers_own_accounts(schema_app):
    s = Setup(balance=300)
    add_member(s)  # another member of the same SACCO must not show up
    resp = schema_app.test_client().get(
        f"{SAVINGS}/accounts/me", headers=auth(s.member)
    )
    assert resp.status_code == 200
    accounts = resp.get_json()["accounts"]
    assert [a["id"] for a in accounts] == [s.account.id]
    assert set(accounts[0]) == ACCOUNT_KEYS
    assert accounts[0]["balance"] == 300


def test_me_spans_saccos_and_skips_a_suspended_one(schema_app):
    s = Setup(balance=100)
    other = Setup()
    membership_id = join(s.member.id, other.sacco.id)
    second = service.open_account(other.admin.id, membership_id).id
    db.session.remove()
    client = schema_app.test_client()
    url = f"{SAVINGS}/accounts/me"

    both = client.get(url, headers=auth(s.member)).get_json()["accounts"]
    assert [a["id"] for a in both] == sorted([s.account.id, second])

    suspend(other.sacco.id)
    left = client.get(url, headers=auth(s.member)).get_json()["accounts"]
    assert [a["id"] for a in left] == [s.account.id]


def test_me_without_an_account_is_an_empty_list(schema_app):
    s = Setup()
    staff = add_member(s, role=MembershipRole.STAFF, with_account=False)
    resp = schema_app.test_client().get(f"{SAVINGS}/accounts/me", headers=auth(staff))
    assert resp.status_code == 200
    assert resp.get_json() == {"accounts": []}


def test_me_without_a_token_is_401(schema_app):
    assert schema_app.test_client().get(f"{SAVINGS}/accounts/me").status_code == 401


# ---------- GET /admin/saccos/<id>/accounts ----------


def test_admin_lists_the_sacco_accounts_with_email_and_balance(schema_app):
    s = Setup(balance=1000)
    resp = schema_app.test_client().get(list_url(s.sacco.id), headers=auth(s.admin))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] == 1 and body["page"] == 1
    row = body["accounts"][0]
    assert set(row) == LIST_KEYS
    assert row["account_id"] == s.account.id
    assert row["membership_id"] == s.member_membership.id
    assert row["email"].startswith("member")
    assert row["balance"] == 1000 == ledger_balance(s.account.id)


def test_the_admin_list_only_contains_its_own_sacco(schema_app):
    s = Setup(balance=1000)
    other = Setup(balance=9999)
    body = (
        schema_app.test_client()
        .get(list_url(s.sacco.id), headers=auth(s.admin))
        .get_json()
    )
    ids = [a["account_id"] for a in body["accounts"]]
    assert ids == [s.account.id] and other.account.id not in ids


def test_the_admin_list_is_paged(schema_app):
    s = Setup(balance=100)
    add_extra_member(s)
    add_extra_member(s)
    client = schema_app.test_client()
    url = list_url(s.sacco.id)
    first = client.get(url + "?per_page=2&page=1", headers=auth(s.admin)).get_json()
    second = client.get(url + "?per_page=2&page=2", headers=auth(s.admin)).get_json()
    assert first["total"] == 3 and len(first["accounts"]) == 2
    assert len(second["accounts"]) == 1
    seen = [a["account_id"] for a in first["accounts"] + second["accounts"]]
    assert len(set(seen)) == 3


def test_the_admin_list_rejects_bad_paging(schema_app):
    s = Setup()
    client = schema_app.test_client()
    for query in ("?page=0", "?per_page=abc", "?per_page=-1"):
        resp = client.get(list_url(s.sacco.id) + query, headers=auth(s.admin))
        assert resp.status_code == 400
    capped = client.get(list_url(s.sacco.id) + "?per_page=5000", headers=auth(s.admin))
    assert capped.get_json()["per_page"] == 100


def test_the_admin_list_access_rules(schema_app):
    s = Setup(balance=100)
    outsider = Setup()
    staff = add_member(s, role=MembershipRole.STAFF, with_account=False)
    owner = make_owner()
    client = schema_app.test_client()
    url = list_url(s.sacco.id)

    assert client.get(url).status_code == 401
    assert client.get(url, headers=auth(s.member)).status_code == 403
    assert client.get(url, headers=auth(outsider.admin)).status_code == 404
    assert client.get(url, headers=auth(staff)).status_code == 200
    assert client.get(url, headers=auth(owner)).status_code == 200
    assert client.get(list_url(2_000_000_000), headers=auth(owner)).status_code == 404


def test_the_admin_list_of_a_suspended_sacco_is_423(schema_app):
    s = Setup(balance=100)
    suspend(s.sacco.id)
    resp = schema_app.test_client().get(list_url(s.sacco.id), headers=auth(s.admin))
    assert resp.status_code == 423


def test_foreign_and_missing_ids_answer_with_the_same_404_body(schema_app):
    """Money routes must not tell another SACCO's id from one that does not exist."""
    s = Setup(balance=500)
    outsider = Setup()
    client = schema_app.test_client()
    headers = auth(outsider.admin)

    def bodies(foreign_id, missing_id, send):
        foreign, missing = send(foreign_id), send(missing_id)
        assert foreign.status_code == missing.status_code == 404
        assert foreign.get_json() == missing.get_json()

    def open_for(membership_id):
        body = {"membership_id": membership_id}
        return client.post(f"{SAVINGS}/accounts", json=body, headers=headers)

    def deposit_to(account_id):
        return client.post(
            f"{SAVINGS}/accounts/{account_id}/deposits",
            json={"amount": 100, "reference": "probe-1"},
            headers=headers,
        )

    bodies(s.member_membership.id, 2_000_000_000, open_for)
    bodies(s.account.id, 2_000_000_000, deposit_to)


@pytest.mark.parametrize("suffix", ["deposits", "withdrawals"])
@pytest.mark.parametrize("body", [{"amount": 100}, {"amount": 100, "reference": None}])
def test_a_money_request_without_a_reference_is_400(schema_app, suffix, body):
    """Without a reference a timed-out retry would post twice, so it is refused."""
    s = Setup(balance=500)
    resp = schema_app.test_client().post(
        f"{SAVINGS}/accounts/{s.account.id}/{suffix}", json=body, headers=auth(s.admin)
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["message"] == "reference is required."
    assert ledger_balance(s.account.id) == 500


# ---------- separation of duties ----------


def test_nobody_posts_money_on_their_own_account(schema_app):
    s = Setup(balance=500)
    staff = add_member(s, MembershipRole.STAFF)  # has an account of their own
    client = schema_app.test_client()
    for suffix in ("deposits", "withdrawals"):
        resp = client.post(
            f"{SAVINGS}/accounts/{staff.account_id}/{suffix}",
            json={"amount": 100, "reference": f"own-{suffix}"},
            headers=auth(staff),
        )
        assert resp.status_code == 403
        assert resp.get_json()["error"]["message"] == (
            "You cannot post money on your own account."
        )
    assert ledger_balance(staff.account_id) == 0


def test_nobody_reverses_an_entry_on_their_own_account(schema_app):
    s = Setup(balance=500)
    staff = add_member(s, MembershipRole.STAFF)
    posted = service.deposit(s.admin.id, staff.account_id, 300, "for-staff")
    client = schema_app.test_client()
    url = f"{SAVINGS}/transactions/{posted.id}/reversals"

    own = client.post(url, json={"reference": "self-rev"}, headers=auth(staff))
    assert own.status_code == 403
    assert ledger_balance(staff.account_id) == 300

    other = client.post(url, json={"reference": "admin-rev"}, headers=auth(s.admin))
    assert other.status_code == 201
    assert ledger_balance(staff.account_id) == 0
