from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.auth.lockout import (
    check_lockout,
    record_failed_login,
    reset_failed_logins,
)
from app.auth.passwords import hash_password, validate_password, verify_password

T0 = datetime(2026, 11, 13, 9, 0, tzinfo=timezone.utc)


def make_user():
    return SimpleNamespace(failed_login_attempts=0, locked_until=None)


def test_hash_and_verify():
    h = hash_password("correct-horse")
    assert h != "correct-horse"
    assert verify_password("correct-horse", h)
    assert not verify_password("wrong", h)
    assert not verify_password("x", "not-a-hash")


def test_validate_password():
    assert validate_password("short", "a@b.com") == "Password must be at least 8 characters long."
    assert validate_password("a@b.com", "A@B.com") is not None
    assert validate_password("long-enough-pw", "a@b.com") is None


def test_five_failures_lock_for_15_minutes():
    u = make_user()
    for _ in range(4):
        record_failed_login(u, now=T0)
    assert not check_lockout(u, now=T0)
    record_failed_login(u, now=T0)
    assert check_lockout(u, now=T0)
    assert check_lockout(u, now=T0 + timedelta(minutes=14))
    assert not check_lockout(u, now=T0 + timedelta(minutes=15, seconds=1))


def test_success_resets_counter():
    u = make_user()
    for _ in range(3):
        record_failed_login(u, now=T0)
    reset_failed_logins(u)
    assert u.failed_login_attempts == 0


def test_attempts_restart_after_lock_expires():
    u = make_user()
    for _ in range(5):
        record_failed_login(u, now=T0)
    record_failed_login(u, now=T0 + timedelta(minutes=16))
    assert u.failed_login_attempts == 1
    assert not check_lockout(u, now=T0 + timedelta(minutes=16))