"""POST /savings/transactions/<id>/reversals

Body: `reference`, and `override_reason` only to override the loan-cap block.
"""

from flask import jsonify

from app import savings_bp
from app.auth.limits import money_limit
from app.ledger import reversals
from app.savings.routes import _body, _json, signed_in
from app.savings.validation import parse_override_reason, parse_reference


@savings_bp.post("/transactions/<int:transaction_id>/reversals")
@money_limit
@signed_in
def reverse(user_id: int, transaction_id: int):
    body = _body()
    reference = parse_reference(body.get("reference"))
    reason = parse_override_reason(
        body.get("override_reason"), reversals.MIN_REASON, reversals.MAX_REASON
    )
    view = reversals.reverse_transaction(user_id, transaction_id, reference, reason)
    return jsonify(_json(view)), 200 if view.replayed else 201
