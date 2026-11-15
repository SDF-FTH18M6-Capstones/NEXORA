"""Single-use emailed links: prove an email address, or reset a password.

Only the token's SHA-256 is stored, so a database leak cannot be turned into
working links. Issuing a new link replaces any earlier one of the same purpose.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.extensions import db
from app.models.email_verification import EmailVerification
from app.models.user import User

VERIFY, RESET = "verify", "reset"
LIFETIMES = {VERIFY: timedelta(hours=24), RESET: timedelta(hours=1)}


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue(user: User, purpose: str = VERIFY) -> str:
    """Add a fresh link row and return the raw token. The caller commits."""
    db.session.execute(
        delete(EmailVerification).where(
            EmailVerification.user_id == user.id,
            EmailVerification.purpose == purpose,
        )
    )
    token = secrets.token_urlsafe(32)
    db.session.add(
        EmailVerification(
            user_id=user.id,
            purpose=purpose,
            token_hash=_hash(token),
            expires_at=datetime.now(UTC) + LIFETIMES[purpose],
        )
    )
    return token


def find(token: str, purpose: str) -> EmailVerification | None:
    """The live (unexpired) link row, locked until the caller commits."""
    row = db.session.execute(
        select(EmailVerification)
        .where(
            EmailVerification.token_hash == _hash(token),
            EmailVerification.purpose == purpose,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if row is None or row.expires_at <= datetime.now(UTC):
        db.session.rollback()
        return None
    return row


def confirm(token: str) -> bool:
    """Mark the owner's email verified and spend the link. Commits on success."""
    row = find(token, VERIFY)
    if row is None:
        return False
    db.session.get(User, row.user_id).email_verified_at = datetime.now(UTC)
    db.session.delete(row)
    db.session.commit()
    return True
