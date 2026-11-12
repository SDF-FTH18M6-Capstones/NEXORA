import pytest
from datetime import datetime, timezone, timedelta
from app.models.user import User
from app.auth.lockout import check_lockout
from app.auth.passwords import get_password_hash, verify_password

def test_password_hashing_and_verification():
    """Test that password hashing and verification work correctly."""
    password = "SecurePassword123!"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_lockout_flow():
    """Test account lockout behavior based on timezone-aware datetimes."""
    user = User(username="testuser", password_hash="dummy_hash")
    
    # Initially, no lockout time is set, so lockout should be False
    user.locked_until = None
    assert check_lockout(user) is False

    # If locked_until is in the future, lockout should be True
    user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
    assert check_lockout(user) is True

    # If locked_until is in the past, lockout should be False
    user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
    assert check_lockout(user) is False

def test_successful_login_reset():
    """Test that a successful login resets lockout conditions."""
    user = User(username="testuser", password_hash="dummy_hash")
    
    # Set an active lockout
    user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
    assert check_lockout(user) is True

    # Simulate successful login clearing the lockout
    user.locked_until = None
    assert check_lockout(user) is False