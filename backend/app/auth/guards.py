"""Route guards. Platform owner is read from the database on every request."""

from functools import wraps

from flask import g, jsonify

from app.security.tenant import AccessDenied, current_user


def platform_owner_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        try:
            user = current_user()
        except AccessDenied as exc:
            return jsonify(error=exc.message), exc.status
        if not user.is_platform_owner:
            return jsonify(error="Platform owner access required."), 403
        g.user = user
        return view(*args, **kwargs)

    return wrapper


def access_token_required(view):
    """Any signed-in user. Sets g.user. No SACCO or suspension check, on purpose."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        try:
            g.user = current_user()
        except AccessDenied as exc:
            return jsonify(error=exc.message), exc.status
        return view(*args, **kwargs)

    return wrapper