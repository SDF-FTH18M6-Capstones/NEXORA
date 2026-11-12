"""Rate limiting for the authentication endpoints."""

from urllib.parse import urlsplit

from flask import jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

LOGIN_LIMIT = "5 per minute"
REGISTER_LIMIT = "5 per minute"


def rate_limit_response(request_limit):
    """Return a clean JSON response when a client exceeds a limit."""
    response = jsonify(error="Too many requests. Try again later.")
    response.status_code = 429
    return response


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    on_breach=rate_limit_response,
)

login_limit = limiter.limit(LOGIN_LIMIT)
register_limit = limiter.limit(REGISTER_LIMIT)


def init_limiter(app):
    """Attach the limiter to the Flask app."""
    limiter.init_app(app)
    if limiter.enabled and not limiter.storage.check():
        # Logins keep working on per-process memory limits, but say so loudly.
        # Only the host is logged: the URI can contain the Redis password.
        host = urlsplit(app.config["RATELIMIT_STORAGE_URI"]).hostname
        app.logger.warning(
            "Rate-limit storage at %s is unreachable; using per-process limits.", host
        )
