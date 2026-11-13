"""Member endpoints (Move 2, Neo): list, get, add and update one SACCO's members.

Only the platform owner and that SACCO's administrator may manage members.
Another SACCO's records are never returned: an administrator of the wrong SACCO
gets 403 for the SACCO itself, and a membership id from another SACCO gets 404.
"""

from dataclasses import dataclass

import pytest
from sqlalchemy import select, text

from app.auth.tokens import create_access_token
from app.extensions import db
from app.models.membership import MembershipRole, MembershipStatus, SaccoMembership
from app.models.sacco import Sacco
from app.models.user import User

PASSWORD_HASH = "not-a-real-hash"  # these tests mint tokens; they never log in


def _truncate():
    db.session.remove()
    db.session.execute(text("TRUNCATE users, saccos RESTART IDENTITY CASCADE"))
    db.session.commit()


@pytest.fixture(autouse=True)
def clean_tables(app):
    _truncate()
    yield
    _truncate()


def make_user(email, owner=False):
    user = User(email=email, password_hash=PASSWORD_HASH, is_platform_owner=owner)
    db.session.add(user)
    db.session.commit()
    return user


def make_sacco(name):
    sacco = Sacco(name=name)
    db.session.add(sacco)
    db.session.commit()
    return sacco


def make_membership(
    user, sacco, role=MembershipRole.MEMBER, status=MembershipStatus.ACTIVE
):
    membership = SaccoMembership(
        user_id=user.id, sacco_id=sacco.id, role=role, status=status
    )
    db.session.add(membership)
    db.session.commit()
    return membership


def auth(user):
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def collection(sacco):
    return f"/api/v1/saccos/{sacco.id}/members"


def item(sacco, membership):
    return f"{collection(sacco)}/{membership.id}"


@dataclass
class World:
    owner: User
    sacco: Sacco
    other_sacco: Sacco
    admin: User
    member: User
    member_membership: SaccoMembership
    other_admin: User
    other_membership: SaccoMembership
    new_user: User


@pytest.fixture
def world(app):
    owner = make_user("owner@example.com", owner=True)
    sacco = make_sacco("Umoja SACCO")
    other_sacco = make_sacco("Harambee SACCO")
    admin = make_user("admin@example.com")
    make_membership(admin, sacco, MembershipRole.SACCO_ADMIN)
    member = make_user("member@example.com")
    member_membership = make_membership(member, sacco)
    other_admin = make_user("other-admin@example.com")
    other_membership = make_membership(
        other_admin, other_sacco, MembershipRole.SACCO_ADMIN
    )
    new_user = make_user("new@example.com")
    return World(
        owner=owner,
        sacco=sacco,
        other_sacco=other_sacco,
        admin=admin,
        member=member,
        member_membership=member_membership,
        other_admin=other_admin,
        other_membership=other_membership,
        new_user=new_user,
    )


# ---------- who may call these endpoints ----------


@pytest.mark.parametrize("call", ["list", "get", "add", "update"])
def test_without_a_token_is_401(client, world, call):
    requests = {
        "list": lambda: client.get(collection(world.sacco)),
        "get": lambda: client.get(item(world.sacco, world.member_membership)),
        "add": lambda: client.post(
            collection(world.sacco), json={"email": "new@example.com"}
        ),
        "update": lambda: client.patch(
            item(world.sacco, world.member_membership), json={"role": "staff"}
        ),
    }
    assert requests[call]().status_code == 401


def test_a_member_cannot_manage_members(client, world):
    headers = auth(world.member)
    assert client.get(collection(world.sacco), headers=headers).status_code == 403
    assert (
        client.get(item(world.sacco, world.member_membership), headers=headers).status_code
        == 403
    )
    assert (
        client.post(
            collection(world.sacco),
            headers=headers,
            json={"email": "new@example.com"},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            item(world.sacco, world.member_membership),
            headers=headers,
            json={"role": "staff"},
        ).status_code
        == 403
    )


def test_an_administrator_of_another_sacco_is_refused(client, world):
    headers = auth(world.other_admin)
    resp = client.get(collection(world.sacco), headers=headers)
    assert resp.status_code == 403
    assert "member@example.com" not in resp.get_data(as_text=True)


def test_a_missing_sacco_is_404(client, world):
    assert (
        client.get("/api/v1/saccos/999999/members", headers=auth(world.owner)).status_code
        == 404
    )


def test_an_inactive_administrator_is_refused(client, world):
    membership = db.session.execute(
        select(SaccoMembership).where(SaccoMembership.user_id == world.admin.id)
    ).scalar_one()
    membership.status = MembershipStatus.INACTIVE
    db.session.commit()
    resp = client.get(collection(world.sacco), headers=auth(world.admin))
    assert resp.status_code == 403


# ---------- list ----------


def test_the_admin_lists_only_their_own_sacco(client, world):
    resp = client.get(collection(world.sacco), headers=auth(world.admin))
    assert resp.status_code == 200
    emails = [m["email"] for m in resp.get_json()["members"]]
    assert emails == ["admin@example.com", "member@example.com"]


def test_the_platform_owner_lists_any_sacco(client, world):
    resp = client.get(collection(world.other_sacco), headers=auth(world.owner))
    assert [m["email"] for m in resp.get_json()["members"]] == ["other-admin@example.com"]


def test_members_are_listed_in_creation_order_with_their_role_and_status(
    client, world
):
    body = client.get(collection(world.sacco), headers=auth(world.admin)).get_json()
    assert [(m["role"], m["status"]) for m in body["members"]] == [
        ("sacco_admin", "active"),
        ("member", "active"),
    ]


# ---------- get ----------


def test_get_returns_one_membership(client, world):
    resp = client.get(
        item(world.sacco, world.member_membership), headers=auth(world.admin)
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == world.member_membership.id
    assert body["user_id"] == world.member.id
    assert body["email"] == "member@example.com"
    assert body["role"] == "member"
    assert body["status"] == "active"
    assert body["created_at"]


def test_get_for_a_missing_membership_is_404(client, world):
    assert (
        client.get(
            f"{collection(world.sacco)}/999999", headers=auth(world.admin)
        ).status_code
        == 404
    )


def test_a_membership_id_from_another_sacco_is_404_and_leaks_nothing(client, world):
    resp = client.get(
        f"{collection(world.sacco)}/{world.other_membership.id}",
        headers=auth(world.admin),
    )
    assert resp.status_code == 404
    assert "other-admin@example.com" not in resp.get_data(as_text=True)


# ---------- add ----------


def test_adding_an_existing_user_defaults_to_an_active_member(client, world):
    resp = client.post(
        collection(world.sacco),
        headers=auth(world.admin),
        json={"email": "  New@Example.com "},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["email"] == "new@example.com"
    assert body["role"] == "member"
    assert body["status"] == "active"


def test_adding_an_unknown_email_is_404(client, world):
    resp = client.post(
        collection(world.sacco),
        headers=auth(world.admin),
        json={"email": "ghost@example.com"},
    )
    assert resp.status_code == 404


def test_adding_the_same_user_twice_is_409(client, world):
    resp = client.post(
        collection(world.sacco),
        headers=auth(world.admin),
        json={"email": "member@example.com"},
    )
    assert resp.status_code == 409


def test_an_admin_cannot_create_another_administrator(client, world):
    resp = client.post(
        collection(world.sacco),
        headers=auth(world.admin),
        json={"email": "new@example.com", "role": "sacco_admin"},
    )
    assert resp.status_code == 403
    assert db.session.get(User, world.new_user.id).id  # untouched, no membership row
    assert (
        db.session.query(SaccoMembership)
        .filter_by(user_id=world.new_user.id)
        .count()
        == 0
    )


def test_the_platform_owner_can_create_an_administrator(client, world):
    resp = client.post(
        collection(world.sacco),
        headers=auth(world.owner),
        json={"email": "new@example.com", "role": "sacco_admin"},
    )
    assert resp.status_code == 201
    assert resp.get_json()["role"] == "sacco_admin"


def test_an_admin_cannot_add_to_another_sacco(client, world):
    resp = client.post(
        collection(world.other_sacco),
        headers=auth(world.admin),
        json={"email": "new@example.com"},
    )
    assert resp.status_code == 403


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"email": "not-an-email"},
        {"email": None},
        {"email": 5},
        {"email": "new@example.com", "role": "owner"},
        {"email": "new@example.com", "role": 5},
        {"email": "new@example.com", "status": "deleted"},
        {"email": "new@example.com", "sacco_id": 1},
    ],
)
def test_a_bad_body_is_400(client, world, payload):
    resp = client.post(collection(world.sacco), headers=auth(world.admin), json=payload)
    assert resp.status_code == 400


# ---------- update ----------


def test_an_admin_updates_the_role_and_status(client, world):
    resp = client.patch(
        item(world.sacco, world.member_membership),
        headers=auth(world.admin),
        json={"role": "staff", "status": "inactive"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["role"] == "staff"
    assert resp.get_json()["status"] == "inactive"
    db.session.expire_all()
    stored = db.session.get(SaccoMembership, world.member_membership.id)
    assert (stored.role, stored.status) == (MembershipRole.STAFF, MembershipStatus.INACTIVE)


def test_an_admin_cannot_grant_administrator_rights(client, world):
    resp = client.patch(
        item(world.sacco, world.member_membership),
        headers=auth(world.admin),
        json={"role": "sacco_admin"},
    )
    assert resp.status_code == 403


def test_the_platform_owner_can_grant_administrator_rights(client, world):
    resp = client.patch(
        item(world.sacco, world.member_membership),
        headers=auth(world.owner),
        json={"role": "sacco_admin"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["role"] == "sacco_admin"


def test_updating_a_membership_from_another_sacco_is_404_and_changes_nothing(
    client, world
):
    resp = client.patch(
        f"{collection(world.sacco)}/{world.other_membership.id}",
        headers=auth(world.admin),
        json={"role": "member"},
    )
    assert resp.status_code == 404
    db.session.expire_all()
    stored = db.session.get(SaccoMembership, world.other_membership.id)
    assert stored.role is MembershipRole.SACCO_ADMIN


def test_updating_a_missing_membership_is_404(client, world):
    resp = client.patch(
        f"{collection(world.sacco)}/999999", headers=auth(world.admin), json={"role": "member"}
    )
    assert resp.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [{}, {"email": "member@example.com"}, {"role": "owner"}, {"status": 5}, {"role": None}],
)
def test_a_bad_update_body_is_400(client, world, payload):
    resp = client.patch(
        item(world.sacco, world.member_membership),
        headers=auth(world.admin),
        json=payload,
    )
    assert resp.status_code == 400
