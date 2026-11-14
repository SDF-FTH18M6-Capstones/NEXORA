"""Savings endpoints: open an account, deposit, withdraw."""

from flask import jsonify, request

from app import savings_bp
from app.savings import service
from app.savings.schemas import InvalidRequest, parse_money, parse_open_account
from app.security.tenant import AccessDenied, current_user


def _error(message: str, status: int):
    return jsonify({"error": message}), status


def _body() -> dict:
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else {}


def _current_user_id() -> int | None:
    """The signed-in user's id from the Bearer access token, or None.

    Uses the tenant guard's current_user(), so a token whose user no longer
    exists is refused like any other bad token. SACCO suspension is checked in the
    service, on every money movement.
    """
    try:
        return current_user().id
    except AccessDenied:
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