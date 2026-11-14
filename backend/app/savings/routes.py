"""Savings endpoints: open an account, deposit, withdraw."""

from dataclasses import asdict
from functools import wraps

from flask import jsonify, request

from app import savings_bp
from app.auth.limits import money_limit, write_limit
from app.savings import service
from app.savings.validation import InvalidRequest, parse_money, parse_open_account
from app.security.tenant import AccessDenied, current_user


def _error(message: str, status: int):
    return jsonify({"error": message}), status


def _body() -> dict:
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else {}


def _json(view) -> dict:
    """A result dataclass as a JSON-ready dict."""
    data = asdict(view)
    data["created_at"] = view.created_at.isoformat()
    return data


def signed_in(view):
    """Pass the caller's user id to the view and answer its refusals as JSON."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        try:
            user_id = current_user().id
        except AccessDenied:
            return _error("Authentication required.", 401)
        try:
            return view(user_id, *args, **kwargs)
        except InvalidRequest as exc:
            return _error(str(exc), 400)
        except service.SavingsError as exc:
            return _error(exc.message, exc.status)

    return wrapper


@savings_bp.after_request
def _no_store(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@savings_bp.post("/accounts")
@write_limit
@signed_in
def open_account(user_id: int):
    account = service.open_account(user_id, parse_open_account(_body()))
    return jsonify(_json(account)), 201


def _post_money(user_id: int, account_id: int, action):
    amount, reference = parse_money(_body())
    tx = action(user_id, account_id, amount, reference)
    # 201 for a new entry, 200 when a retried reference returns the original.
    return jsonify(_json(tx)), 200 if tx.replayed else 201


@savings_bp.post("/accounts/<int:account_id>/deposits")
@money_limit
@signed_in
def deposit(user_id: int, account_id: int):
    return _post_money(user_id, account_id, service.deposit)


@savings_bp.post("/accounts/<int:account_id>/withdrawals")
@money_limit
@signed_in
def withdraw(user_id: int, account_id: int):
    return _post_money(user_id, account_id, service.withdraw)
