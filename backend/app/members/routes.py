"""Member routes.

Two groups live here because they both serve members: the signed-in user's own
profile under /members/me (Sam's Move 2 work), and one SACCO's member list
under /saccos/<sacco_id>/members (Neo's Move 2 work).
"""
from flask import g, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import members_bp, saccos_bp
from app.auth.routes import _body, _error
from app.auth.suspension import check_sacco_not_suspended
from app.extensions import db
from app.members import self_service
from app.members.schemas import InvalidMember, parse_create_member, parse_update_member
from app.models.audit import AuditLog
from app.models.membership import MembershipRole, SaccoMembership
from app.models.user import User
from app.security.tenant import AccessDenied, current_user, sacco_scoped


def _me_error(message: str, status: int):
    return jsonify({"error": message}), status


def _me_user() -> tuple[User | None, tuple | None]:
    """The signed-in caller for /me, or (None, error response).

    401 for no or a bad token. 423 when the caller's SACCO is suspended, so a token
    issued before the suspension stops working (same rule as login and refresh).
    The platform owner is never blocked: check_sacco_not_suspended lets them through.
    """
    try:
        user = current_user()
    except AccessDenied as exc:
        return None, _me_error(exc.message, exc.status)
    if message := check_sacco_not_suspended(user):
        return None, _me_error(message, 423)
    return user, None


@members_bp.after_request
def _me_no_store(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@members_bp.get("/me")
def get_me():
    user, error = _me_user()
    if error:
        return error
    try:
        return jsonify(self_service.get_profile(user.id))
    except self_service.ProfileError as exc:
        return _me_error(exc.message, exc.status)


@members_bp.patch("/me")
def patch_me():
    user, error = _me_user()
    if error:
        return error
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _me_error("A JSON object is required.", 400)
    try:
        return jsonify(self_service.update_profile(user.id, body))
    except self_service.ProfileError as exc:
        return _me_error(exc.message, exc.status)


# ---------------------------------------------------------------------------
# One SACCO's members (Move 2, Neo). Platform owner or that SACCO's admin only.
# The tenant guard answers 401/404/403/423, so another SACCO is never revealed.
# Only the platform owner creates, edits or removes administrator memberships.
# ---------------------------------------------------------------------------

ADMIN = MembershipRole.SACCO_ADMIN


def _member_json(membership: SaccoMembership, email: str) -> dict:
    return {
        "id": membership.id,
        "user_id": membership.user_id,
        "email": email,
        "role": membership.role.value,
        "status": membership.status.value,
        "created_at": membership.created_at.isoformat(),
    }


def _state(membership: SaccoMembership) -> str:
    return f"{membership.role.value}/{membership.status.value}"


def _audit(membership: SaccoMembership, action: str, before: str = "") -> None:
    # Same transaction as the change: both are saved or neither is.
    change = f"{before} -> {_state(membership)}" if before else _state(membership)
    db.session.add(
        AuditLog(
            sacco_id=membership.sacco_id,
            actor_id=g.access.user.id,
            action=action,
            target=f"membership:{membership.id} {change}",
        )
    )


def _members(sacco_id: int, membership_id: int | None = None, lock: bool = False):
    """(membership, email) rows in this SACCO only, so other SACCOs never leak."""
    query = (
        select(SaccoMembership, User.email)
        .join(User, User.id == SaccoMembership.user_id)
        .where(SaccoMembership.sacco_id == sacco_id)
        .order_by(SaccoMembership.id)
    )
    if membership_id is not None:
        query = query.where(SaccoMembership.id == membership_id)
    if lock:
        query = query.with_for_update(of=SaccoMembership)
    return db.session.execute(query).all()


@saccos_bp.get("/<int:sacco_id>/members")
@sacco_scoped()
def list_members(sacco_id):
    return jsonify(members=[_member_json(*row) for row in _members(sacco_id)])


@saccos_bp.get("/<int:sacco_id>/members/<int:membership_id>")
@sacco_scoped()
def get_member(sacco_id, membership_id):
    rows = _members(sacco_id, membership_id)
    if not rows:
        return _error("Member not found.", 404)
    return jsonify(_member_json(*rows[0]))


@saccos_bp.post("/<int:sacco_id>/members")
@sacco_scoped()
def add_member(sacco_id):
    owner = g.access.user.is_platform_owner
    try:
        email, role, status = parse_create_member(_body())
    except InvalidMember as exc:
        return _error(str(exc), 400)
    if role is ADMIN and not owner:
        return _error("Only the platform owner can add a SACCO administrator.", 403)
    target = db.session.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()
    # The platform owner gets the same answer as an unknown email, so an admin
    # cannot discover the owner's address. The owner never needs a membership.
    if target is None or target.is_platform_owner:
        return _error("No registered user with that email.", 404)
    membership = SaccoMembership(
        user_id=target.id, sacco_id=sacco_id, role=role, status=status
    )
    db.session.add(membership)
    try:
        db.session.flush()  # assigns the id the audit row points at
    except IntegrityError:  # unique (user_id, sacco_id)
        db.session.rollback()
        return _error("That user is already a member of this SACCO.", 409)
    _audit(membership, "member.add")
    db.session.commit()
    return jsonify(_member_json(membership, target.email)), 201


@saccos_bp.patch("/<int:sacco_id>/members/<int:membership_id>")
@sacco_scoped()
def update_member(sacco_id, membership_id):
    try:
        changes = parse_update_member(_body())
    except InvalidMember as exc:
        return _error(str(exc), 400)
    rows = _members(sacco_id, membership_id, lock=True)
    if not rows:
        db.session.rollback()
        return _error("Member not found.", 404)
    membership, email = rows[0]
    # An admin cannot touch an admin row (their own included) or create one.
    touches_admin = membership.role is ADMIN or changes.get("role") is ADMIN
    if touches_admin and not g.access.user.is_platform_owner:
        db.session.rollback()
        return _error("Only the platform owner can change SACCO administrators.", 403)
    if all(getattr(membership, f) is v for f, v in changes.items()):
        body = _member_json(membership, email)
        db.session.rollback()  # nothing changed; release the lock
        return jsonify(body)
    before = _state(membership)
    for field, value in changes.items():
        setattr(membership, field, value)
    _audit(membership, "member.update", before)
    body = _member_json(membership, email)
    db.session.commit()
    return jsonify(body)