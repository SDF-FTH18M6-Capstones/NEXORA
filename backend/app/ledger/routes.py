"""POST /savings/transactions/<id>/reversals"""

from flask import jsonify

from app import savings_bp
from app.ledger import reversals
from app.savings.routes import _body, _json, signed_in
from app.savings.validation import parse_reference


@savings_bp.post("/transactions/<int:transaction_id>/reversals")
@signed_in
def reverse(user_id: int, transaction_id: int):
    reference = parse_reference(_body().get("reference"))
    view = reversals.reverse_transaction(user_id, transaction_id, reference)
    return jsonify(_json(view)), 200 if view.replayed else 201
