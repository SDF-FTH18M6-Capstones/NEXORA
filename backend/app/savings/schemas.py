"""Request parsing for the savings endpoints.

The money rules themselves live in app/savings/validation.py (Move 3, Neo); this
module only turns a request body into the values those rules accept, and keeps
the old import path working for the routes.
"""

from app.savings.validation import (
    MAX_ID,
    MAX_TRANSACTION_AMOUNT,
    REFERENCE_RE,
    InvalidRequest,
    parse_amount,
    parse_id,
    parse_money,
    parse_reference,
)

__all__ = [
    "MAX_ID",
    "MAX_TRANSACTION_AMOUNT",
    "REFERENCE_RE",
    "InvalidRequest",
    "parse_amount",
    "parse_id",
    "parse_money",
    "parse_open_account",
    "parse_reference",
]


def parse_open_account(body: dict) -> int:
    """Returns the membership id the account is opened for."""
    return parse_id(body.get("membership_id"), "membership_id")
