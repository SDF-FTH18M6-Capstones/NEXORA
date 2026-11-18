"""Refuses login for anyone whose SACCOs are all suspended."""

from app.extensions import db
from app.models.membership import MembershipStatus, SaccoMembership
from app.models.sacco import Sacco, SaccoStatus

SUSPENDED_MESSAGE = "This SACCO account is suspended. Contact the platform owner."


def check_sacco_not_suspended(user) -> str | None:
    """Return a clean error message if the user may not log in because of a suspension.

    Blocked: someone in a suspended SACCO with no active membership in an active
    one. Someone who also has an active SACCO still logs in; the tenant guard
    answers 423 for the suspended SACCO itself. Otherwise any SACCO admin could
    lock a user out everywhere by adding them to a SACCO that later gets
    suspended. The platform owner is never blocked: they reactivate SACCOs.
    The message does not name the SACCO.
    """
    from app.security.permissions import is_platform_owner

    if user is None or is_platform_owner(user):
        return None
    rows = db.session.execute(
        db.select(SaccoMembership.status, Sacco.status)
        .join(Sacco, Sacco.id == SaccoMembership.sacco_id)
        .where(SaccoMembership.user_id == user.id)
    ).all()
    suspended = any(sacco is SaccoStatus.SUSPENDED for _, sacco in rows)
    usable = any(
        member is MembershipStatus.ACTIVE and sacco is SaccoStatus.ACTIVE
        for member, sacco in rows
    )
    return SUSPENDED_MESSAGE if suspended and not usable else None
