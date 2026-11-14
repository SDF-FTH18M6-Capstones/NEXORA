"""The one error body every route answers with.

    {"error": {"code": "not_found", "message": "Not found."}}

Messages are written where the error is raised; the code comes from the status,
so a client can branch on `code` and show `message`.
"""

from flask import jsonify

CODES = {
    400: "validation_error",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    423: "locked",
    429: "rate_limited",
    500: "internal_error",
}


def error_response(status: int, message: str, code: str | None = None):
    """Return `(response, status)` in the API's error shape."""
    code = code or CODES.get(status, "error")
    return jsonify({"error": {"code": code, "message": message}}), status
