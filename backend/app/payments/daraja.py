"""Safaricom Daraja STK push, SANDBOX ONLY.

The base URL is fixed to the sandbox and the feature refuses to run in
production: no real money until a lawyer has ruled on the NPS Act definition.
Nexora holds no funds. It asks M-Pesa to prompt the member's phone and records
the answer; it never credits savings. An officer still confirms the deposit.
"""

import base64
import json
import re
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime

from flask import current_app

BASE = "https://sandbox.safaricom.co.ke"
PHONE = re.compile(r"254[17][0-9]{8}")
_token = {"value": "", "until": 0.0}


class DarajaError(Exception):
    """Daraja did not answer or refused. The message is safe to show."""


def enabled() -> bool:
    cfg = current_app.config
    return bool(cfg.get("DARAJA_ENABLED")) and cfg.get("APP_ENV") != "production"


def msisdn(value) -> str | None:
    """254XXXXXXXXX from 07.., 01.., +254.. or 254.., else None."""
    phone = re.sub(r"[\s\-()+]", "", str(value or ""))
    phone = re.sub(r"^0", "254", phone)
    return phone if PHONE.fullmatch(phone) else None


def _call(path: str, payload=None, headers=None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as reply:
            body = json.load(reply)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise DarajaError("M-Pesa did not answer. Try again in a moment.") from exc
    if not isinstance(body, dict):
        raise DarajaError("M-Pesa sent an answer Nexora cannot read.")
    return body


def _bearer() -> dict:
    if time.time() >= _token["until"]:
        cfg = current_app.config
        basic = base64.b64encode(
            f"{cfg['DARAJA_CONSUMER_KEY']}:{cfg['DARAJA_CONSUMER_SECRET']}".encode()
        ).decode()
        reply = _call(
            "/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {basic}"},
        )
        if not reply.get("access_token"):
            raise DarajaError("M-Pesa refused the sign-in.")
        _token["value"] = reply["access_token"]
        _token["until"] = time.time() + max(int(reply.get("expires_in", 3599)) - 60, 0)
    return {"Authorization": f"Bearer {_token['value']}"}


def stk_push(phone: str, shillings: int, reference: str) -> dict:
    """Ask M-Pesa to prompt `phone` for `shillings`. Returns Daraja's reply."""
    cfg = current_app.config
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    code = cfg["DARAJA_SHORTCODE"]
    password = base64.b64encode(f"{code}{cfg['DARAJA_PASSKEY']}{stamp}".encode())
    reply = _call(
        "/mpesa/stkpush/v1/processrequest",
        {
            "BusinessShortCode": code,
            "Password": password.decode(),
            "Timestamp": stamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": shillings,
            "PartyA": phone,
            "PartyB": code,
            "PhoneNumber": phone,
            "CallBackURL": cfg["DARAJA_CALLBACK_URL"],
            "AccountReference": reference,
            "TransactionDesc": "SACCO deposit",
        },
        _bearer(),
    )
    if reply.get("ResponseCode") != "0" or not reply.get("CheckoutRequestID"):
        raise DarajaError("M-Pesa could not start the payment.")
    return reply
