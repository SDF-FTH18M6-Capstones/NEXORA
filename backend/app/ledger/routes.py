"""POST /savings/transactions/<id>/reversals"""

from flask import jsonify

from app import savings_bp
from app.ledger import reversals
from app.savings import service
from app.savings.routes import _body, _current_user_id, _error
from app.savings.schemas import InvalidRequest, parse_reference


@savings_bp.post("/transactions/<int:transaction_id>/reversals")
def reverse(transaction_id: int):
    user_id = _current_user_id()
    if user_id is None:
        return _error("Authentication required.", 401)
    try:
        reference = parse_reference(_body().get("reference"))
        view = reversals.reverse_transaction(user_id, transaction_id, reference)
    except InvalidRequest as exc:
        return _error(str(exc), 400)
    except service.SavingsError as exc:
        return _error(exc.message, exc.status)
    return (
        jsonify(
            id=view.id,
            reverses_id=view.reverses_id,
            account_id=view.account_id,
            type=view.type,
            amount=view.amount,
            reference=view.reference,
            balance=view.balance,
            created_at=view.created_at.isoformat(),
            replayed=view.replayed,
        ),
        200 if view.replayed else 201,
    )
