"""The platform owner's view of a SACCO's administrators.

A SACCO is created with no staff at all, so the admin list must read as empty
and a first admin must stay possible later, not only on the creation screen.
"""

import uuid
from datetime import UTC, datetime

import pytest

from app.auth.tokens import create_access_token
from app.extensions import db
from app.models.sacco import Sacco
from app.models.user import User
from savings_support import Setup, schema_app  # noqa: F401

pytestmark = pytest.mark.schema


def auth(user):
    token = create_access_token(user.id, user.token_version)
    return {"Authorization": f"Bearer {token}"}


def owner():
    user = User(
        email=f"owner-{uuid.uuid4().hex[:10]}@example.com",
        password_hash="x",
        is_platform_owner=True,
    )
    db.session.add(user)
    db.session.commit()
    ref = type("U", (), {"id": user.id, "token_version": user.token_version})
    db.session.remove()
    return ref


def admins_url(sacco_id):
    return f"/api/v1/saccos/{sacco_id}/admins"


def bare_sacco():
    """A SACCO exactly as `POST /saccos` leaves it: no members at all."""
    sacco = Sacco(name=f"Fresh SACCO {uuid.uuid4().hex[:8]}")
    db.session.add(sacco)
    db.session.commit()
    sacco_id = sacco.id
    db.session.remove()
    return sacco_id


def test_a_first_admin_can_be_added_long_after_the_sacco_was_created(
    schema_app,  # noqa: F811
):
    sacco_id = bare_sacco()
    client = schema_app.test_client()
    boss = owner()
    url = admins_url(sacco_id)

    # A new SACCO has no admin until the owner invites one.
    empty = client.get(url, headers=auth(boss))
    assert empty.status_code == 200, empty.json
    assert empty.json == {"admins": [], "has_admin": False}

    made = client.post(
        f"/api/v1/saccos/{sacco_id}/members",
        json={"phone": "0712345678", "role": "sacco_admin"},
        headers=auth(boss),
    )
    assert made.status_code == 201, made.json
    assert made.json["join_code"]

    after = client.get(url, headers=auth(boss))
    assert after.status_code == 200, after.json
    assert after.json["has_admin"] is False  # invited, not accepted yet
    assert len(after.json["admins"]) == 1
    (invited,) = after.json["admins"]
    assert invited["phone"] == made.json["phone"]
    assert invited["status"] == "invited"


def verified_user(email):
    user = User(
        email=email,
        password_hash="x",
        email_verified_at=datetime.now(UTC),
    )
    db.session.add(user)
    db.session.commit()
    db.session.remove()
    return email


def test_an_admin_can_be_invited_by_email(schema_app):  # noqa: F811
    """The same first admin, invited by email instead of a hand-delivered code."""
    sacco_id = bare_sacco()
    client = schema_app.test_client()
    boss = owner()
    email = verified_user(f"new-admin-{uuid.uuid4().hex[:8]}@example.com")

    made = client.post(
        f"/api/v1/saccos/{sacco_id}/members",
        json={"email": email, "role": "sacco_admin", "invite": True},
        headers=auth(boss),
    )
    assert made.status_code == 201, made.json
    assert made.json["email"] == email
    assert made.json["status"] == "invited"
    # The code goes to the mailbox only, never back to the owner's screen.
    assert "join_code" not in made.json

    after = client.get(admins_url(sacco_id), headers=auth(boss))
    assert after.status_code == 200, after.json
    assert after.json["has_admin"] is False
    (invited,) = after.json["admins"]
    assert invited["email"] == email
    assert invited["status"] == "invited"


def test_a_sacco_admin_cannot_invite_an_admin_by_email(schema_app):  # noqa: F811
    s = Setup()
    client = schema_app.test_client()
    email = verified_user(f"new-admin-{uuid.uuid4().hex[:8]}@example.com")
    resp = client.post(
        f"/api/v1/saccos/{s.sacco.id}/members",
        json={"email": email, "role": "sacco_admin", "invite": True},
        headers=auth(s.admin),
    )
    assert resp.status_code == 403, resp.json


def test_the_admin_list_names_the_admin_a_sacco_already_has(schema_app):  # noqa: F811
    s = Setup()
    client = schema_app.test_client()
    boss = owner()

    resp = client.get(admins_url(s.sacco.id), headers=auth(boss))
    assert resp.status_code == 200, resp.json
    assert resp.json["has_admin"] is True
    (admin,) = resp.json["admins"]
    assert admin["id"] == s.admin_membership.id
    assert admin["status"] == "active"


@pytest.mark.parametrize("who", ["admin", "member"])
def test_only_the_owner_reads_the_admin_list(schema_app, who):  # noqa: F811
    s = Setup()
    client = schema_app.test_client()
    resp = client.get(admins_url(s.sacco.id), headers=auth(getattr(s, who)))
    assert resp.status_code == 403, resp.json


def test_an_unknown_sacco_has_no_admin_list(schema_app):  # noqa: F811
    client = schema_app.test_client()
    resp = client.get("/api/v1/saccos/999999/admins", headers=auth(owner()))
    assert resp.status_code == 404, resp.json


def test_the_admin_list_needs_a_signed_in_owner(schema_app):  # noqa: F811
    s = Setup()
    client = schema_app.test_client()
    assert client.get(admins_url(s.sacco.id)).status_code == 401
