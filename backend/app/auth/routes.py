"""Auth endpoints: register, login, refresh, logout."""

import re

from flask import jsonify, request
from sqlalchemy.exc import IntegrityError, OperationalError

from app import auth_bp
from app.auth.limits import login_limit, register_limit, write_limit
from app.auth.lockout import check_lockout, record_failed_login, reset_failed_logins
from app.auth.passwords import hash_password, validate_password, verify_password
from app.auth.suspension import check_sacco_not_suspended
from app.auth.tokens import (
    TokenError,
    create_access_token,
    create_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.extensions import db
from app.models.user import User

EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
MAX_EMAIL_LENGTH = 255
MAX_PASSWORD_LENGTH = 128

# Verified against when there is no usable hash, so every failure costs the same.
_DUMMY_HASH = hash_password("not-a-real-password")


def _error(message: str, status: int):
    return jsonify({"error": message}), status


def _body() -> dict:
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else {}


def _text(value) -> str | None:
    """The string itself, or None if it is not text Postgres and Argon2 accept."""
    if not isinstance(value, str) or "\x00" in value:
        return None
    try:
        value.encode()
    except UnicodeEncodeError:
        return None
    return value


def _email(value) -> str | None:
    email = (_text(value) or "").strip().lower()
    ok = len(email) <= MAX_EMAIL_LENGTH and EMAIL_RE.fullmatch(email)
    return email if ok else None


def _password(value) -> str | None:
    password = _text(value)
    return password if password and len(password) <= MAX_PASSWORD_LENGTH else None


@auth_bp.after_request
def _no_store(response):
    response.headers["Cache-Control"] = "no-store"
    return response


def _tokens(user_id: int, refresh_token: str):
    return jsonify(
        access_token=create_access_token(user_id),
        refresh_token=refresh_token,
        token_type="Bearer",
    )


@auth_bp.post("/register")
@register_limit
def register():
    data = _body()
    email, password = _email(data.get("email")), _password(data.get("password"))
    if email is None:
        return _error("A valid email is required.", 400)
    if password is None:
        return _error(
            f"Password is required (max {MAX_PASSWORD_LENGTH} characters).", 400
        )
    if problem := validate_password(password, email):
        return _error(problem, 400)

    user = User(email=email, password_hash=hash_password(password))
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:  # unique index on lower(email)
        db.session.rollback()
        return _error("Email is already registered.", 409)
    return jsonify(id=user.id, email=user.email), 201


@auth_bp.post("/login")
@login_limit
def login():
    data = _body()
    email, password = _email(data.get("email")), _password(data.get("password"))
    if email is None or password is None:
        return _error("Invalid email or password.", 401)

    # One attempt per account at a time: a parallel one is turned away at once, so
    # guesses cannot dodge the failure counter or pile up holding connections.
    try:
        user = (
            db.session.query(User)
            .filter(User.email == email)
            .with_for_update(nowait=True)
            .first()
        )
    except OperationalError as exc:
        db.session.rollback()
        if exc.orig.sqlstate != "55P03":  # lock_not_available
            raise
        return _error("Another attempt is in progress. Try again shortly.", 429)
    # Lockout comes before the password, so a locked account never reveals
    # whether the guess was right.
    locked = user is not None and check_lockout(user)
    usable = user is not None and not locked
    valid = verify_password(password, user.password_hash if usable else _DUMMY_HASH)

    if locked:
        db.session.rollback()
        return _error("Account temporarily locked. Try again later.", 423)
    if not (usable and valid):
        if user:
            record_failed_login(user)
        db.session.commit()
        return _error("Invalid email or password.", 401)

    reset_failed_logins(user)
    if message := check_sacco_not_suspended(user):
        db.session.commit()
        return _error(message, 423)
    refresh_token = create_refresh_token(user.id)
    db.session.commit()
    return _tokens(user.id, refresh_token)


def _with_refresh_token(action):
    token = _body().get("refresh_token")
    if not isinstance(token, str) or not token:
        return _error("refresh_token is required.", 400)
    try:
        return action(token)
    except TokenError:
        return _error("Invalid or expired refresh token.", 401)


@auth_bp.post("/refresh")
@write_limit
def refresh():
    def rotate(token):
        user_id, new_token = rotate_refresh_token(token)
        # A suspension must also cut off sessions that were already open.
        if message := check_sacco_not_suspended(db.session.get(User, user_id)):
            revoke_refresh_token(new_token)
            return _error(message, 423)
        return _tokens(user_id, new_token)

    return _with_refresh_token(rotate)


@auth_bp.post("/logout")
@write_limit
def logout():
    def revoke(token):
        revoke_refresh_token(token)
        return jsonify(message="Logged out.")

    return _with_refresh_token(revoke)
