"""Checks that refuse login for members and staff of a suspended SACCO."""

from app.extensions import db
from app.models.membership import MembershipRole, SaccoMembership
from app.models.sacco import Sacco, SaccoStatus

SUSPENDED_MESSAGE = "This SACCO account is suspended. Contact the platform owner."


def check_sacco_not_suspended(user) -> str | None:
    """Return a clean error message if the user's SACCO is suspended.

    Members and staff are refused when their SACCO is suspended. Platform
    owners have no SACCO membership, so they are not blocked. The message
    deliberately does not name the SACCO or reveal any other records.
    """
    if user is None or getattr(user, "is_platform_owner", False):
        return None

    memberships = (
        db.session.query(SaccoMembership)
        .filter(SaccoMembership.user_id == user.id)
        .all()
    )

    for membership in memberships:
        if membership.role not in (MembershipRole.MEMBER, MembershipRole.STAFF):
            continue
        sacco = db.session.get(Sacco, membership.sacco_id)
        if sacco is not None and sacco.status == SaccoStatus.SUSPENDED:
            return SUSPENDED_MESSAGE

    return None
