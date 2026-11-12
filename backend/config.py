"""NEXORA configuration. Secrets and connection strings come from environment variables only."""
import os
from datetime import timedelta


class Config:
    """Default settings used by `flask run`. Values come from .env or your shell."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Reverse proxies in front of the app (0 = none). Per-IP rate limits need the
    # real client address, so set this to the proxy count when deployed behind one.
    TRUSTED_PROXIES = int(os.environ.get("TRUSTED_PROXIES", "0"))
    MAX_CONTENT_LENGTH = 16 * 1024  # auth bodies are tiny; reject anything bigger

    # Auth values from the Day 4 plan. Refresh lifetime is a placeholder until Move 3.
    ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    LOCKOUT_THRESHOLD = 5
    LOCKOUT_DURATION = timedelta(minutes=15)

    TESTING = False


class TestConfig(Config):
    """Used by pytest. Points at a separate database so tests never touch development data."""

    TESTING = True
    RATELIMIT_ENABLED = False  # tests make many logins from one address
    SECRET_KEY = "test-only-not-a-real-secret-0123456789"
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", "")
