"""Route guards. Platform owner is read from the database on every request."""

from functools import wraps

from flask import g, jsonify, request

from app.auth.tokens import TokenError, decode_access_token
from app.extensions import db
from app.models.user import User


def _deny(message: str, status: int):
    return jsonify({"error": message}), status


def platform_owner_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not token:
            return _deny("Authentication required.", 401)
        try:
            claims = decode_access_token(token)
        except TokenError:
            return _deny("Invalid or expired token.", 401)
        user = db.session.get(User, int(claims["sub"]))
        if user is None:
            return _deny("Invalid or expired token.", 401)
        if not user.is_platform_owner:
            return _deny("Platform owner access required.", 403)
        g.current_user = user
        return view(*args, **kwargs)

    return wrapper