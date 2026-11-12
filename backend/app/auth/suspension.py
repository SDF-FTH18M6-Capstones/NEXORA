"""Refuses login for anyone who belongs to a suspended SACCO."""

from app.extensions import db
from app.models.membership import SaccoMembership
from app.models.sacco import Sacco, SaccoStatus

SUSPENDED_MESSAGE = "This SACCO account is suspended. Contact the platform owner."


def check_sacco_not_suspended(user) -> str | None:
    """Return a clean error message if any of the user's SACCOs is suspended.

    Every role is blocked, admins included. Platform owners have no SACCO
    membership, so they are never blocked. The message does not name the SACCO.
    """
    if user is None:
        return None
    suspended = (
        db.session.query(SaccoMembership.id)
        .join(Sacco, Sacco.id == SaccoMembership.sacco_id)
        .filter(
            SaccoMembership.user_id == user.id, Sacco.status == SaccoStatus.SUSPENDED
        )
        .first()
    )
    return SUSPENDED_MESSAGE if suspended else None
