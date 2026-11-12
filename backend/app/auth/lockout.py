from datetime import datetime, timedelta, timezone

MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION = timedelta(minutes=15)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def check_lockout(user, now=None) -> bool:
    """True if the account is locked. Call this BEFORE checking the password."""
    now = now or _now()
    return user.locked_until is not None and user.locked_until > now


def record_failed_login(user, now=None) -> None:
    now = now or _now()
    if user.locked_until is not None and user.locked_until <= now:
        user.failed_login_attempts = 0  # old lock expired, start fresh
        user.locked_until = None
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        user.locked_until = now + LOCK_DURATION


def reset_failed_logins(user) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None