"""Request parsing for the savings endpoints.

Money is whole integer minor units (cents). Floats, numeric strings and booleans
are refused, so no float ever reaches the money code.
"""

import re
import uuid

# Per-transaction ceiling in minor units (1,000,000.00 for a 2-decimal currency).
# Neo owns the final rule in validation.py; swap this for an import when it lands.
MAX_TRANSACTION_AMOUNT = 100_000_000

MAX_ID = 2**31 - 1  # ids are 32-bit integers in Postgres
REFERENCE_RE = re.compile(r"[A-Za-z0-9._:-]{1,64}")


class InvalidRequest(ValueError):
    """The request body is not acceptable. The message is safe to show the client."""


def parse_id(value, name: str) -> int:
    # bool is a subclass of int, so reject it explicitly.
    if type(value) is not int or not 1 <= value <= MAX_ID:
        raise InvalidRequest(f"{name} must be a positive whole number.")
    return value


def parse_amount(value) -> int:
    if type(value) is not int:
        raise InvalidRequest("amount must be a whole number of minor units.")
    if value <= 0:
        raise InvalidRequest("amount must be greater than zero.")
    if value > MAX_TRANSACTION_AMOUNT:
        raise InvalidRequest(f"amount cannot exceed {MAX_TRANSACTION_AMOUNT}.")
    return value


def parse_reference(value) -> str:
    """The client's idempotency key. A retry reuses it and cannot post twice."""
    if value is None:
        return uuid.uuid4().hex
    if not isinstance(value, str) or not REFERENCE_RE.fullmatch(value):
        raise InvalidRequest(
            "reference must be 1 to 64 characters: letters, digits, . _ : -"
        )
    return value


def parse_open_account(body: dict) -> int:
    """Returns the membership id the account is opened for."""
    return parse_id(body.get("membership_id"), "membership_id")


def parse_money(body: dict) -> tuple[int, str]:
    """Returns (amount, reference) for a deposit or withdrawal."""
    return parse_amount(body.get("amount")), parse_reference(body.get("reference"))