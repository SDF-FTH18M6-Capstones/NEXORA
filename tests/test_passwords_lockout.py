import pytest
from datetime import datetime, timedelta
from app.auth.passwords import hash_password, verify_password
from app.auth.lockout import check_lockout, record_failed_login, reset_failed_logins, MAX_FAILED_ATTEMPTS, LOCKOUT_DURATION

class MockUser:
    def __init__(self):
        self.failed_login_count = 0
        self.locked_until = None

@pytest.fixture
def sample_user():
    return MockUser()

def test_password_hashing_and_verification():
    password = "SecurePassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(hashed, password) is True
    assert verify_password(hashed, "WrongPassword") is False

def test_lockout_flow(sample_user):
    assert check_lockout(sample_user) is False
    
    # Record failed attempts up to limit
    for _ in range(MAX_FAILED_ATTEMPTS):
        record_failed_login(sample_user)
    
    assert sample_user.failed_login_count == MAX_FAILED_ATTEMPTS
    assert check_lockout(sample_user) is True

def test_successful_login_reset(sample_user):
    record_failed_login(sample_user)
    assert sample_user.failed_login_count == 1
    
    reset_failed_logins(sample_user)
    assert sample_user.failed_login_count == 0
    assert sample_user.locked_until is None