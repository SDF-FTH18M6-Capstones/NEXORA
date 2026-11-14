"""Savings endpoints: open an account, deposit, withdraw."""

from flask import jsonify, request

from app import savings_bp
from app.auth.tokens import TokenError, decode_access_token
from app.savings import service
from app.savings.schemas import InvalidRequest, parse_money, parse_open_account


def _error(message: str, status: int):
    return jsonify({"error": message}), status


def _body() -> dict:
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else {}


def _current_user_id() -> int | None:
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


def _transaction_json(tx: service.PostedTransaction) -> dict:
    return {
        "id": tx.id,
        "account_id": tx.account_id,
        "type": tx.type,
        "amount": tx.amount,
        "reference": tx.reference,
        "balance": tx.balance,
        "created_at": tx.created_at.isoformat(),
        "replayed": tx.replayed,
    }


@savings_bp.after_request
def _no_store(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@savings_bp.post("/accounts")
def open_account():
    user_id = _current_user_id()
    if user_id is None:
        return _error("Authentication required.", 401)
    try:
        membership_id = parse_open_account(_body())
        account = service.open_account(user_id, membership_id)
    except InvalidRequest as exc:
        return _error(str(exc), 400)
    except service.SavingsError as exc:
        return _error(exc.message, exc.status)
    return (
        jsonify(
            id=account.id,
            membership_id=account.membership_id,
            sacco_id=account.sacco_id,
            balance=account.balance,
            created_at=account.created_at.isoformat(),
        ),
        201,
    )


def _post_money(account_id: int, action):
    user_id = _current_user_id()
    if user_id is None:
        return _error("Authentication required.", 401)
    try:
        amount, reference = parse_money(_body())
        tx = action(user_id, account_id, amount, reference)
    except InvalidRequest as exc:
        return _error(str(exc), 400)
    except service.SavingsError as exc:
        return _error(exc.message, exc.status)
    # 201 for a new entry, 200 when a retried reference returns the original.
    return jsonify(_transaction_json(tx)), 200 if tx.replayed else 201


@savings_bp.post("/accounts/<int:account_id>/deposits")
def deposit(account_id: int):
    return _post_money(account_id, service.deposit)


@savings_bp.post("/accounts/<int:account_id>/withdrawals")
def withdraw(account_id: int):
    return _post_money(account_id, service.withdraw)

# Reversals live in the ledger package; importing it attaches its route here.
from app.ledger import routes as _ledger_routes  # noqa: E402,F401
from app.savings import history as _history  # noqa: E402,F401
