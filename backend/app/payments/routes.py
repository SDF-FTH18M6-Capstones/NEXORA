"""STK push (sandbox, behind DARAJA_ENABLED, off by default).

POST /saccos/<id>/stk-push        a member asks M-Pesa to prompt their phone
GET  /saccos/<id>/stk-push/<pid>  that member, or `member.manage`: the answer
POST /daraja/callback/<token>     Safaricom's answer (the token is the secret)

Nothing here credits savings: the answer is a record, and an officer still
confirms the deposit through the payment requests.
"""

import hmac
from datetime import UTC, datetime, timedelta
from functools import wraps

from flask import current_app, g, jsonify, request
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app import daraja_bp, saccos_bp
from app.audit import log as audit_log
from app.auth.limits import money_limit, read_limit
from app.auth.routes import _body
from app.errors import error_response
from app.extensions import db
from app.models.membership import SaccoMembership
from app.models.stk_push import StkPush
from app.payments import daraja
from app.security.permissions import can
from app.security.tenant import permission_scoped

STALE_MSG = "M-Pesa did not answer in time."
STALE = timedelta(minutes=15)  # a push with no answer after this has failed
MAX_PENDING = 3  # prompts a member may have waiting at once
MAX_MINOR = 15_000_000  # KES 150,000, under M-Pesa's per-transaction limit
ACK = {"ResultCode": 0, "ResultDesc": "Accepted"}


def _feature(view):
    """Off means absent: the same 404 as a route that does not exist."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not daraja.enabled():
            return error_response(404, "Not found.")
        return view(*args, **kwargs)

    return wrapper


def _text(value, limit: int) -> str:
    """Safe for the database: no NUL or lone surrogate, cut to `limit`."""
    return str(value).encode("utf-8", "ignore").decode().replace("\x00", "")[:limit]


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _json(row: StkPush) -> dict:
    return {
        "id": row.id,
        "status": row.status,
        "amount": row.amount,
        "phone_last3": row.phone[-3:],
        "message": row.result_desc,
        "created_at": row.created_at.isoformat(),
    }


@saccos_bp.post("/<int:sacco_id>/stk-push")
@_feature
@money_limit
@permission_scoped("savings.request")
def start_stk_push(sacco_id):
    me = g.access.membership
    body = _body()
    amount, phone = body.get("amount"), daraja.msisdn(body.get("phone"))
    if (
        me is None
        or type(amount) is not int
        or amount % 100
        or not 0 < amount <= MAX_MINOR
    ):
        return error_response(
            400, "Send amount in minor units: whole shillings, KES 1 to KES 150,000."
        )
    if phone is None:
        return error_response(400, "Send a Safaricom number like 0712345678.")
    # One request at a time per member, so the count below cannot be raced past.
    db.session.execute(
        select(SaccoMembership.id).where(SaccoMembership.id == me.id).with_for_update()
    )
    recent = db.session.scalar(
        select(func.count()).where(
            StkPush.membership_id == me.id,
            StkPush.status == "pending",
            StkPush.created_at > datetime.now(UTC) - STALE,
        )
    )
    if recent >= MAX_PENDING:
        return error_response(
            429, "You have payment prompts waiting. Answer or wait for them first."
        )
    row = StkPush(
        sacco_id=sacco_id,
        membership_id=me.id,
        phone=phone,
        amount=amount,
        result_desc="Check your phone and enter your M-Pesa PIN.",
    )
    db.session.add(row)
    # Saved before the network call: no transaction or lock is held open while
    # Safaricom answers, and a failed call is still on record.
    db.session.commit()
    try:
        row.checkout_request_id = daraja.stk_push(phone, amount // 100, f"NX{row.id}")[
            "CheckoutRequestID"
        ]
    except Exception as exc:  # whatever went wrong, the row must not stay pending
        said = (
            str(exc)
            if isinstance(exc, daraja.DarajaError)
            else "M-Pesa could not start the payment."
        )
        row.status, row.result_desc = "failed", said
        db.session.commit()
        return error_response(502, said)
    db.session.commit()
    return jsonify(_json(row)), 201


@saccos_bp.get("/<int:sacco_id>/stk-push/<int:push_id>")
@_feature
@read_limit
@permission_scoped("sacco.view")
def get_stk_push(sacco_id, push_id):
    row = db.session.execute(
        select(StkPush).where(StkPush.id == push_id, StkPush.sacco_id == sacco_id)
    ).scalar_one_or_none()
    mine = (
        g.access.membership is not None
        and row
        and row.membership_id == g.access.membership.id
    )
    if row is None or not (mine or can(g.access.user, g.access.sacco, "member.manage")):
        return error_response(404, "Not found.")
    if row.status == "pending" and row.created_at < datetime.now(UTC) - STALE:
        # No answer from M-Pesa in time (a lost callback): stop showing "pending".
        # Conditional: a callback that lands meanwhile has already closed the row.
        db.session.execute(
            update(StkPush)
            .where(StkPush.id == row.id, StkPush.status == "pending")
            .values(status="failed", result_desc=STALE_MSG)
        )
        db.session.commit()
        db.session.refresh(row)
    return jsonify(_json(row))


@daraja_bp.post("/callback/<token>")
@_feature
def stk_callback(token):
    expected = current_app.config["DARAJA_CALLBACK_TOKEN"]
    if not hmac.compare_digest(token.encode(), expected.encode()):
        return error_response(404, "Not found.")
    data = _dict(
        _dict(_dict(request.get_json(silent=True)).get("Body")).get("stkCallback")
    )
    row = db.session.execute(
        select(StkPush)
        .where(StkPush.checkout_request_id == str(data.get("CheckoutRequestID")))
        .with_for_update()
    ).scalar_one_or_none()
    # A push the 15-minute rule closed may still be answered; any other answered
    # or unknown push is acknowledged and left alone.
    if row is None or (row.status != "pending" and row.result_desc != STALE_MSG):
        db.session.rollback()
        return jsonify(ACK)
    meta = _dict(data.get("CallbackMetadata")).get("Item")
    items = {
        i["Name"]: i.get("Value")
        for i in (meta if isinstance(meta, list) else [])
        if isinstance(i, dict) and isinstance(i.get("Name"), str)
    }
    code = data.get("ResultCode")
    paid = type(code) is int and code == 0
    sent = items.get("Amount")
    if paid and (
        isinstance(sent, bool)
        or not isinstance(sent, int | float)
        or sent != row.amount // 100
    ):
        paid, data["ResultDesc"] = False, "Paid amount did not match the request."
    row.status = "succeeded" if paid else "failed"
    row.result_desc = _text(data.get("ResultDesc") or "", 255)
    receipt = items.get("MpesaReceiptNumber")
    row.mpesa_receipt = _text(receipt, 20) or None if paid and receipt else None
    row.completed_at = datetime.now(UTC)
    audit_log.record(
        row.sacco_id, None, "payment.stk_result", f"stk:{row.id} {row.status}"
    )
    row_id, sacco_id = row.id, row.sacco_id
    try:
        db.session.commit()
    except IntegrityError:  # this receipt number is already on another push
        db.session.rollback()
        db.session.execute(
            update(StkPush)
            .where(StkPush.id == row_id)
            .values(status="failed", result_desc="Duplicate receipt number.")
        )
        audit_log.record(sacco_id, None, "payment.stk_result", f"stk:{row_id} failed")
        db.session.commit()
    return jsonify(ACK)
