"""Member routes.

Two groups live here because they both serve members: the signed-in user's own
profile under /members/me (Sam's Move 2 work), and one SACCO's member list
under /saccos/<sacco_id>/members (Neo's Move 2 work).
"""
from flask import jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import members_bp, saccos_bp
from app.auth.routes import _body, _error
from app.auth.tokens import TokenError, decode_access_token
from app.extensions import db
from app.members import self_service
from app.members.schemas import InvalidMember, parse_create_member, parse_update_member
from app.models.membership import MembershipRole, MembershipStatus, SaccoMembership
from app.models.sacco import Sacco
from app.models.user import User


def _me_error(message: str, status: int):
    return jsonify({"error": message}), status


def _me_user_id() -> int | None:
    """The user id in the Bearer access token, or None.

    Swap this for the tenant guard from Day 4 once it is on development.
    """
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    try:
        return int(decode_access_token(token)["sub"])
    except TokenError:
        return None


@members_bp.after_request
def _me_no_store(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@members_bp.get("/me")
def get_me():
    user_id = _me_user_id()
    if user_id is None:
        return _me_error("Authentication required.", 401)
    try:
        return jsonify(self_service.get_profile(user_id))
    except self_service.ProfileError as exc:
        return _me_error(exc.message, exc.status)


@members_bp.patch("/me")
def patch_me():
    user_id = _me_user_id()
    if user_id is None:
        return _me_error("Authentication required.", 401)
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _me_error("A JSON object is required.", 400)
    try:
        return jsonify(self_service.update_profile(user_id, body))
    except self_service.ProfileError as exc:
        return _me_error(exc.message, exc.status)


# ---------------------------------------------------------------------------
# One SACCO's members (Move 2, Neo). Platform owner or that SACCO's admin only.
# ---------------------------------------------------------------------------


def _current_user() -> User | None:
    """The signed-in user from the Bearer token, or None."""
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    try:
        claims = decode_access_token(token)
    except TokenError:
        return None
    return db.session.get(User, int(claims["sub"]))


def _sacco_for_manager(user: User, sacco_id: int):
    """(sacco, None) when the caller may manage this SACCO, else (None, response).

    The platform owner manages any SACCO. Anyone else needs an active SACCO
    administrator membership in this exact SACCO: another SACCO's records are
    never reachable, per docs/roles-permissions.md.
    """
    sacco = db.session.get(Sacco, sacco_id)
    if sacco is None:
        return None, _error("SACCO not found.", 404)
    if user.is_platform_owner:
        return sacco, None
    membership = db.session.execute(
        select(SaccoMembership).where(
            SaccoMembership.user_id == user.id,
            SaccoMembership.sacco_id == sacco_id,
        )
    ).scalar_one_or_none()
    if membership is None:
        return None, _error("You do not have access to this SACCO.", 403)
    if (
        membership.status is not MembershipStatus.ACTIVE
        or membership.role is not MembershipRole.SACCO_ADMIN
    ):
        return None, _error("SACCO administrator access required.", 403)
    return sacco, None


def _member_json(membership: SaccoMembership, email: str) -> dict:
    return {
        "id": membership.id,
        "user_id": membership.user_id,
        "email": email,
        "role": membership.role.value,
        "status": membership.status.value,
        "created_at": membership.created_at.isoformat(),
    }


def _member_row(sacco_id: int, membership_id: int):
    """The membership in this SACCO with its user's email, or None.

    The SACCO id is part of the lookup, so a membership id from another SACCO is
    simply not found here and its existence is never revealed.
    """
    return db.session.execute(
        select(SaccoMembership, User.email)
        .join(User, User.id == SaccoMembership.user_id)
        .where(
            SaccoMembership.id == membership_id,
            SaccoMembership.sacco_id == sacco_id,
        )
    ).first()


@saccos_bp.get("/<int:sacco_id>/members")
def list_members(sacco_id):
    user = _current_user()
    if user is None:
        return _error("Authentication required.", 401)
    _, denied = _sacco_for_manager(user, sacco_id)
    if denied is not None:
        return denied
    rows = db.session.execute(
        select(SaccoMembership, User.email)
        .join(User, User.id == SaccoMembership.user_id)
        .where(SaccoMembership.sacco_id == sacco_id)
        .order_by(SaccoMembership.id)
    ).all()
    return jsonify(
        members=[_member_json(membership, email) for membership, email in rows]
    )


@saccos_bp.get("/<int:sacco_id>/members/<int:membership_id>")
def get_member(sacco_id, membership_id):
    user = _current_user()
    if user is None:
        return _error("Authentication required.", 401)
    _, denied = _sacco_for_manager(user, sacco_id)
    if denied is not None:
        return denied
    row = _member_row(sacco_id, membership_id)
    if row is None:
        return _error("Member not found.", 404)
    return jsonify(_member_json(*row))


@saccos_bp.post("/<int:sacco_id>/members")
def add_member(sacco_id):
    user = _current_user()
    if user is None:
        return _error("Authentication required.", 401)
    sacco, denied = _sacco_for_manager(user, sacco_id)
    if denied is not None:
        return denied
    try:
        email, role, status = parse_create_member(_body())
    except InvalidMember as exc:
        return _error(str(exc), 400)
    # Creating administrators is still a team decision (roles doc, section 7), so
    # only the platform owner may hand out SACCO administrator rights.
    if role is MembershipRole.SACCO_ADMIN and not user.is_platform_owner:
        return _error("Only the platform owner can add a SACCO administrator.", 403)
    target = db.session.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()
    if target is None:
        return _error("No registered user with that email.", 404)
    membership = SaccoMembership(
        user_id=target.id, sacco_id=sacco.id, role=role, status=status
    )
    db.session.add(membership)
    try:
        db.session.commit()
    except IntegrityError:  # unique (user_id, sacco_id)
        db.session.rollback()
        return _error("That user is already a member of this SACCO.", 409)
    return jsonify(_member_json(membership, target.email)), 201


@saccos_bp.patch("/<int:sacco_id>/members/<int:membership_id>")
def update_member(sacco_id, membership_id):
    user = _current_user()
    if user is None:
        return _error("Authentication required.", 401)
    _, denied = _sacco_for_manager(user, sacco_id)
    if denied is not None:
        return denied
    try:
        changes = parse_update_member(_body())
    except InvalidMember as exc:
        return _error(str(exc), 400)
    membership = db.session.execute(
        select(SaccoMembership)
        .where(
            SaccoMembership.id == membership_id,
            SaccoMembership.sacco_id == sacco_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if membership is None:
        return _error("Member not found.", 404)
    granting_admin = changes.get("role") is MembershipRole.SACCO_ADMIN
    if granting_admin and not user.is_platform_owner:
        return _error(
            "Only the platform owner can grant SACCO administrator rights.", 403
        )
    for field, value in changes.items():
        setattr(membership, field, value)
    db.session.commit()
    email = db.session.get(User, membership.user_id).email
    return jsonify(_member_json(membership, email))
