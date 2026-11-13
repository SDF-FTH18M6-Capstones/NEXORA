# (shared file), so these two routes serve GET and PATCH /members/me.
from flask import jsonify, request

from app import members_bp
from app.auth.tokens import TokenError, decode_access_token
from app.members import self_service


def _me_error(message: str, status: int):
    return jsonify({"error": message}), status


def _me_user_id() -> int | None:
    """The user id in the Bearer access token, or None.

    Swap this for the tenant guard from Day 4 once it is on development.
    """
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    try:
        return int(decode_access_token(token)["sub"])
    except TokenError:
        return None


@members_bp.after_request
def _me_no_store(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@members_bp.get("/me")
def get_me():
    user_id = _me_user_id()
    if user_id is None:
        return _me_error("Authentication required.", 401)
    try:
        return jsonify(self_service.get_profile(user_id))
    except self_service.ProfileError as exc:
        return _me_error(exc.message, exc.status)


@members_bp.patch("/me")
def patch_me():
    user_id = _me_user_id()
    if user_id is None:
        return _me_error("Authentication required.", 401)
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _me_error("A JSON object is required.", 400)
    try:
        return jsonify(self_service.update_profile(user_id, body))
    except self_service.ProfileError as exc:
        return _me_error(exc.message, exc.status)