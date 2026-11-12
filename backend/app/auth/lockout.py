from datetime import datetime, timedelta

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)

def check_lockout(user, now=None) -> bool:
    """True if the account is locked. Call this BEFORE checking the password."""
    now = now or datetime.utcnow()
    return user.locked_until is not None and user.locked_until > now

def record_failed_login(user, now=None) -> None:
    """Record a failed login attempt and lock out if threshold is reached."""
    now = now or datetime.utcnow()
    if user.locked_until is not None and user.locked_until <= now:
        user.failed_login_count = 0  # old lock expired, start fresh
        user.locked_until = None
    
    user.failed_login_count += 1
    if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
        user.locked_until = now + LOCKOUT_DURATION

def reset_failed_logins(user) -> None:
    """Reset failed login attempts and clear any active lockout upon success."""
    user.failed_login_count = 0
    user.locked_until = None