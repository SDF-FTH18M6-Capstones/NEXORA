"""Circle pay-in details: validation, the live row, and the two-officer change.

A change is proposed by one officer (`payin.manage`) and goes live only when a
different officer approves that exact proposal. Nothing here moves money.
"""

import logging
import re

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.extensions import db
from app.mail import send_text_email
from app.models.payment_details import (
    CirclePaymentDetails,
    CirclePaymentDetailsChange,
)
from app.models.sacco import Sacco
from app.models.user import User
from app.security.permissions import holders

log = logging.getLogger(__name__)

PERMISSION = "payin.manage"
FIELDS = (
    "mpesa_type",
    "mpesa_number",
    "account_reference_hint",
    "display_name",
    "bank_name",
    "bank_account_name",
    "bank_account_number",
    "bank_branch",
    "bank_uses_shared_paybill",
    "bank_paybill_number",
)
# ASCII only: `\d` would also accept Arabic-Indic and other Unicode digits.
MPESA_NUMBER = re.compile(r"[0-9]{5,7}")
BANK_ACCOUNT = re.compile(r"[0-9]{6,20}")


def lock_sacco(sacco_id: int) -> None:
    """Serialise proposals and approvals for one circle."""
    db.session.execute(
        select(Sacco.id).where(Sacco.id == sacco_id).with_for_update()
    ).scalar_one_or_none()


def _text(value, limit: int, label: str, example: str):
    """(clean value or None, reason or None). Blank means "not given"."""
    if value is None or value == "":
        return None, None
    plain = f"{label} must be plain text on one line. Example: {example}."
    if not isinstance(value, str) or any(
        ord(ch) < 32 or ord(ch) == 127 for ch in value
    ):
        return None, plain
    try:
        value.encode("utf-8")  # a lone surrogate would fail later, in the database
    except UnicodeEncodeError:
        return None, plain
    value = value.strip()
    if len(value) > limit:
        return None, f"{label} can be at most {limit} characters. Example: {example}."
    return (value or None), None


def validate(body) -> tuple[dict, dict]:
    """(values, errors). `errors` maps a field to a plain-words reason that says
    the format, gives an example and says why it was refused."""
    if not isinstance(body, dict):
        return {}, {"_": "Send the pay-in details as a JSON object."}
    errors: dict[str, str] = {}
    unknown = sorted(set(body) - set(FIELDS))
    if unknown:
        errors["_"] = f"Unknown field(s): {', '.join(unknown)}."
    values: dict = {}

    def text_field(field, limit, label, example):
        value, reason = _text(body.get(field), limit, label, example)
        values[field] = value
        if reason:
            errors[field] = reason

    text_field("display_name", 60, "Name members will see", "Umoja Circle Savings")
    text_field(
        "account_reference_hint", 60, "Account reference hint", "your member number"
    )
    text_field("bank_name", 60, "Bank name", "Equity Bank")
    text_field("bank_account_name", 80, "Bank account name", "Umoja Circle")
    text_field("bank_branch", 60, "Bank branch", "Kitale")

    mpesa_type = body.get("mpesa_type")
    mpesa_number = body.get("mpesa_number")
    if mpesa_type in (None, "") and mpesa_number in (None, ""):
        values["mpesa_type"] = values["mpesa_number"] = None
    else:
        if mpesa_type in ("paybill", "till"):
            values["mpesa_type"] = mpesa_type
        else:
            values["mpesa_type"] = None
            errors["mpesa_type"] = (
                "M-Pesa type must be paybill or till, so members know which "
                "M-Pesa menu to use. Example: paybill."
            )
        if isinstance(mpesa_number, str) and MPESA_NUMBER.fullmatch(mpesa_number):
            values["mpesa_number"] = mpesa_number
        else:
            values["mpesa_number"] = None
            errors["mpesa_number"] = (
                "The paybill or till number must be 5 to 7 digits, with no spaces "
                "or letters, because M-Pesa numbers are never shorter or longer. "
                "Example: 400200."
            )
        if values["display_name"] is None and "display_name" not in errors:
            errors["display_name"] = (
                "Add the name members will see when M-Pesa shows the business "
                "name, so they can check it before paying. Example: Umoja Circle "
                "Savings."
            )
    if values["account_reference_hint"] and values["mpesa_type"] != "paybill":
        errors.setdefault(
            "account_reference_hint",
            "Only a paybill has an account number. Leave this empty for a till.",
        )

    account = body.get("bank_account_number")
    has_bank = (
        values["bank_name"] is not None
        or values["bank_account_name"] is not None
        or account not in (None, "")
    )
    if has_bank:
        for field, label, example in (
            ("bank_name", "Bank name", "Equity Bank"),
            ("bank_account_name", "Bank account name", "Umoja Circle"),
        ):
            if values[field] is None and field not in errors:
                errors[field] = (
                    f"{label} is needed once any bank detail is given, so members "
                    f"can pay the right account. Example: {example}."
                )
        if isinstance(account, str) and BANK_ACCOUNT.fullmatch(account):
            values["bank_account_number"] = account
        else:
            values["bank_account_number"] = None
            errors["bank_account_number"] = (
                "The bank account number must be 6 to 20 digits, with no spaces "
                "or dashes, so a typo cannot send money elsewhere. "
                "Example: 0123456789."
            )
    else:
        values["bank_account_number"] = None
        if values["bank_branch"]:
            errors["bank_branch"] = (
                "A branch needs a bank. Add the bank name, account name and "
                "account number too. Example: Equity Bank, Kitale branch."
            )

    shared = body.get("bank_uses_shared_paybill", False)
    paybill = body.get("bank_paybill_number")
    if not isinstance(shared, bool):
        values["bank_uses_shared_paybill"] = False
        values["bank_paybill_number"] = None
        errors["bank_uses_shared_paybill"] = (
            "Send true or false. Example: true when members pay the bank by paybill."
        )
    elif shared:
        values["bank_uses_shared_paybill"] = True
        if not has_bank:
            errors["bank_uses_shared_paybill"] = (
                "A shared bank paybill needs the bank details above it, so members "
                "know which account the paybill pays into. Example: Equity Bank, "
                "account 0123456789."
            )
        if isinstance(paybill, str) and MPESA_NUMBER.fullmatch(paybill):
            values["bank_paybill_number"] = paybill
        else:
            values["bank_paybill_number"] = None
            errors["bank_paybill_number"] = (
                "Give the bank's shared paybill number: 5 to 7 digits, no spaces. "
                "Example: 247247."
            )
    else:
        values["bank_uses_shared_paybill"] = False
        values["bank_paybill_number"] = None
        if paybill not in (None, ""):
            errors["bank_paybill_number"] = (
                "Leave this empty unless the bank uses a shared paybill. Turn the "
                "shared paybill on first."
            )

    if not errors and values["mpesa_number"] is None and values["bank_name"] is None:
        errors["_"] = (
            "Give M-Pesa details, bank details or both, so members have somewhere "
            "to pay."
        )
    return values, errors


def values_json(row) -> dict:
    return {
        **{field: getattr(row, field) for field in FIELDS},
        # A shared bank paybill cannot name the circle, so only an officer who
        # reads the bank statement can confirm those payments.
        "bank_manual_confirm_only": row.bank_uses_shared_paybill,
    }


def live_json(row: CirclePaymentDetails) -> dict:
    return {**values_json(row), "updated_at": row.updated_at.isoformat()}


def change_json(row: CirclePaymentDetailsChange) -> dict:
    return {
        "id": row.id,
        "status": row.status,
        "proposed_by": row.proposed_by,
        "proposed_at": row.proposed_at.isoformat(),
        "approved_by": row.approved_by,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
        "values": values_json(row),
    }


def live_details(sacco_id: int) -> CirclePaymentDetails | None:
    return db.session.execute(
        select(CirclePaymentDetails).where(CirclePaymentDetails.sacco_id == sacco_id)
    ).scalar_one_or_none()


def pending_change(sacco_id: int) -> CirclePaymentDetailsChange | None:
    return db.session.execute(
        select(CirclePaymentDetailsChange).where(
            CirclePaymentDetailsChange.sacco_id == sacco_id,
            CirclePaymentDetailsChange.status == "pending",
        )
    ).scalar_one_or_none()


def changed_fields(row, other_values: dict) -> list[str]:
    """Field names (never the numbers) where `other_values` differs from `row`
    (the live row, or None when nothing is live yet)."""
    if row is None:
        return [f for f in FIELDS if other_values[f] not in (None, False)]
    return [f for f in FIELDS if getattr(row, f) != other_values[f]]


def officers(sacco_id: int) -> list[User]:
    """Active members who hold `payin.manage`, decided the way `can()` decides."""
    ids = holders(sacco_id, PERMISSION)
    return list(db.session.execute(select(User).where(User.id.in_(ids))).scalars())


def notify_officers(sacco_id: int, subject: str, body: str) -> None:
    """Email every officer. Call after the commit: a mail outage never fails the
    request and never leaves a half-saved change."""
    try:
        recipients = [user.email for user in officers(sacco_id)]
    except Exception:
        log.exception("Could not list the officers of circle %s", sacco_id)
        return
    for email in recipients:
        try:
            send_text_email(email, subject, body)
        except Exception:
            log.exception("Could not email an officer of circle %s", sacco_id)


def go_live(change: CirclePaymentDetailsChange) -> None:
    """Copy an approved change onto the circle's live row (insert or replace)."""
    values = {field: getattr(change, field) for field in FIELDS}
    row = {
        "updated_by": change.proposed_by,
        "updated_at": change.approved_at,
        **values,
    }
    db.session.execute(
        pg_insert(CirclePaymentDetails)
        .values(sacco_id=change.sacco_id, **row)
        .on_conflict_do_update(index_elements=["sacco_id"], set_=row)
    )
