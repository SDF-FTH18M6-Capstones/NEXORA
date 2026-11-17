"""Member routes.

Two groups live here because they both serve members: the signed-in user's own
profile under /members/me (Sam's Move 2 work), and one SACCO's member list
under /saccos/<sacco_id>/members (Neo's Move 2 work).
"""
from flask import current_app, g, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import members_bp, saccos_bp
from app.auth.join import issue_code, normalize_phone
from app.auth.limits import read_limit, write_limit
from app.auth.routes import _body
from app.auth.suspension import check_sacco_not_suspended
from app.errors import error_response
from app.extensions import db
from app.members import self_service
from app.members.schemas import InvalidMember, parse_create_member, parse_update_member
from app.models.audit import AuditLog
from app.models.membership import MembershipRole, MembershipStatus, SaccoMembership
from app.models.user import User
from app.security.tenant import AccessDenied, current_user, sacco_scoped


def _me_error(message: str, status: int):
    return error_response(status, message)


def _me_user() -> tuple[User | None, tuple | None]:
    """The signed-in caller for /me, or (None, error response).

    401 for no or a bad token. 423 when the caller's SACCO is suspended, so a token
    issued before the suspension stops working (same rule as login and refresh).
    The platform owner is never blocked: check_sacco_not_suspended lets them through.
    """
    try:
        user = current_user()
    except AccessDenied as exc:
        return None, error_response(exc.status, exc.message)
    if message := check_sacco_not_suspended(user):
        return None, error_response(423, message)
    return user, None


@members_bp.after_request
def _me_no_store(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@members_bp.get("/me")
@read_limit
def get_me():
    user, error = _me_user()
    if error:
        return error
    try:
        return jsonify(self_service.get_profile(user.id))
    except self_service.ProfileError as exc:
        return error_response(exc.status, exc.message)


@members_bp.patch("/me")
@write_limit
def patch_me():
    user, error = _me_user()
    if error:
        return error
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return error_response(400, "A JSON object is required.")
    try:
        return jsonify(self_service.update_profile(user.id, body))
    except self_service.ProfileError as exc:
        return error_response(exc.status, exc.message)


# ---------------------------------------------------------------------------
# One SACCO's members (Move 2, Neo). Platform owner or that SACCO's admin only.
# The tenant guard answers 401/404/403/423, so another SACCO is never revealed.
# Only the platform owner creates, edits or removes administrator memberships.
# ---------------------------------------------------------------------------

ADMIN = MembershipRole.SACCO_ADMIN


def _member_json(membership: SaccoMembership, email: str | None) -> dict:
    return {
        "id": membership.id,
        "user_id": membership.user_id,
        "email": email,
        "phone": membership.phone,
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
    """(membership, email) rows in this SACCO only, so other SACCOs never leak.

    Invited members have no user yet, so the join to users is an outer join.
    """
    query = (
        select(SaccoMembership, User.email)
        .outerjoin(User, User.id == SaccoMembership.user_id)
        .where(SaccoMembership.sacco_id == sacco_id)
        .order_by(SaccoMembership.id)
    )
    if membership_id is not None:
        query = query.where(SaccoMembership.id == membership_id)
    if lock:
        query = query.with_for_update(of=SaccoMembership)
    return db.session.execute(query).all()


@saccos_bp.get("/<int:sacco_id>/members")
@read_limit
@sacco_scoped()
def list_members(sacco_id):
    return jsonify(members=[_member_json(*row) for row in _members(sacco_id)])


@saccos_bp.get("/<int:sacco_id>/members/<int:membership_id>")
@read_limit
@sacco_scoped()
def get_member(sacco_id, membership_id):
    rows = _members(sacco_id, membership_id)
    if not rows:
        return error_response(404, "Member not found.")
    return jsonify(_member_json(*rows[0]))


def _invite_member(sacco_id):
    """An officer adds a phone: invited membership plus a one-time join code."""
    body = request.get_json(silent=True) or {}
    try:
        phone = normalize_phone(body.get("phone"))
        role = MembershipRole(body.get("role", "member"))
    except ValueError:
        return error_response(400, "A valid phone and role are required.")
    if role is ADMIN and not g.access.user.is_platform_owner:
        return error_response(
            403, "Only the platform owner can add a SACCO administrator."
        )
    membership = SaccoMembership(
        user_id=None,
        sacco_id=sacco_id,
        phone=phone,
        role=role,
        status=MembershipStatus.INVITED,
    )
    db.session.add(membership)
    try:
        db.session.flush()
    except IntegrityError:  # unique (sacco_id, phone)
        db.session.rollback()
        return error_response(409, "That phone has already been invited to this SACCO.")
    row, code = issue_code(
        membership.id, g.access.user.id, current_app.config["SECRET_KEY"]
    )
    _audit(membership, "member.invite")
    db.session.commit()
    return (
        jsonify(
            id=membership.id,
            phone=phone,
            role=role.value,
            status="invited",
            join_code=code,
            expires_at=row.expires_at.isoformat(),
        ),
        201,
    )


@saccos_bp.post("/<int:sacco_id>/members")
@write_limit
@sacco_scoped()
def add_member(sacco_id):
    raw = request.get_json(silent=True)
    if isinstance(raw, dict) and raw.get("phone") and not raw.get("email"):
        return _invite_member(sacco_id)
    owner = g.access.user.is_platform_owner
    try:
        email, role, status = parse_create_member(_body())
    except InvalidMember as exc:
        return error_response(400, str(exc))
    if role is ADMIN and not owner:
        return error_response(
            403, "Only the platform owner can add a SACCO administrator."
        )
    target = db.session.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()
    # The platform owner gets the same answer as an unknown email, so an admin
    # cannot discover the owner's address. The owner never needs a membership.
    if target is None or target.is_platform_owner:
        return error_response(404, "No registered user with that email.")
    # Whoever registered an address may not be its owner. Only a user who has
    # opened the emailed link can be given access to a SACCO.
    if target.email_verified_at is None:
        return error_response(409, "That user has not verified their email yet.")
    membership = SaccoMembership(
        user_id=target.id, sacco_id=sacco_id, role=role, status=status
    )
    db.session.add(membership)
    try:
        db.session.flush()  # assigns the id the audit row points at
    except IntegrityError:  # unique (user_id, sacco_id)
        db.session.rollback()
        return error_response(409, "That user is already a member of this SACCO.")
    _audit(membership, "member.add")
    db.session.commit()
    return jsonify(_member_json(membership, target.email)), 201


@saccos_bp.patch("/<int:sacco_id>/members/<int:membership_id>")
@write_limit
@sacco_scoped()
def update_member(sacco_id, membership_id):
    try:
        changes = parse_update_member(_body())
    except InvalidMember as exc:
        return error_response(400, str(exc))
    rows = _members(sacco_id, membership_id, lock=True)
    if not rows:
        db.session.rollback()
        return error_response(404, "Member not found.")
    membership, email = rows[0]
    # An admin cannot touch an admin row (their own included) or create one.
    touches_admin = membership.role is ADMIN or changes.get("role") is ADMIN
    if touches_admin and not g.access.user.is_platform_owner:
        db.session.rollback()
        return error_response(
            403, "Only the platform owner can change SACCO administrators."
        )
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