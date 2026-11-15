"""Proof of email ownership: issue a single-use link, confirm it.

Only the token's SHA-256 is stored, so a database leak cannot be turned into
working links. Issuing a new link replaces any earlier one for the user.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.extensions import db
from app.models.email_verification import EmailVerification
from app.models.user import User

LIFETIME = timedelta(hours=24)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue(user: User) -> str:
    """Add a fresh verification row and return the raw token. The caller commits."""
    db.session.execute(
        delete(EmailVerification).where(EmailVerification.user_id == user.id)
    )
    token = secrets.token_urlsafe(32)
    db.session.add(
        EmailVerification(
            user_id=user.id,
            token_hash=_hash(token),
            expires_at=datetime.now(UTC) + LIFETIME,
        )
    )
    return token


def confirm(token: str) -> bool:
    """Mark the owner's email verified and spend the link. Commits on success."""
    row = db.session.execute(
        select(EmailVerification)
        .where(EmailVerification.token_hash == _hash(token))
        .with_for_update()
    ).scalar_one_or_none()
    if row is None or row.expires_at <= datetime.now(UTC):
        db.session.rollback()
        return False
    user = db.session.get(User, row.user_id)
    user.email_verified_at = datetime.now(UTC)
    db.session.delete(row)
    db.session.commit()
    return True
