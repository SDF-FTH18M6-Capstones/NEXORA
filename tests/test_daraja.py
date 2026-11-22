"""STK push: sandbox only, off by default, records answers, never moves money."""

import base64

import pytest
from sqlalchemy import text

from app.extensions import db
from app.models.audit import AuditLog
from app.models.savings import SavingsAccount
from app.models.stk_push import StkPush
from app.payments import daraja
from config import Config, TestConfig
from test_member_profile import P
from test_sacco_detail import ADMIN, MEMBER, make_sacco

TOKEN = "cb-secret-token"
CALLBACK = f"/api/v1/daraja/callback/{TOKEN}"


@pytest.fixture(autouse=True)
def clean_tables(app):
    def truncate():
        db.session.remove()
        db.session.execute(
            text("TRUNCATE refresh_tokens, users, saccos RESTART IDENTITY CASCADE")
        )
        db.session.commit()

    truncate()
    yield
    truncate()


@pytest.fixture
def on(app):
    """Switch the feature on for one test, with a stubbed network."""
    sent = []
    old = {k: app.config.get(k) for k in ("DARAJA_ENABLED", "DARAJA_CALLBACK_TOKEN")}
    app.config.update(
        DARAJA_ENABLED=True,
        DARAJA_CALLBACK_TOKEN=TOKEN,
        DARAJA_CONSUMER_KEY="k",
        DARAJA_CONSUMER_SECRET="s",
        DARAJA_PASSKEY="pass",
        DARAJA_SHORTCODE="174379",
        DARAJA_CALLBACK_URL="https://example.test" + CALLBACK,
    )
    daraja._token.update(value="", until=0.0)

    def fake(path, payload=None, headers=None):
        if "oauth" in path:
            return {"access_token": "tok", "expires_in": "3599"}
        sent.append((payload, headers))
        return {"ResponseCode": "0", "CheckoutRequestID": f"ws_CO_{len(sent)}"}

    daraja._call = fake
    yield sent
    app.config.update(old)
    daraja._call = _real_call


_real_call = daraja._call


def push(client, p, amount=10_000, phone="0712345678"):
    return client.post(
        f"/api/v1/saccos/{p.sacco_id}/stk-push",
        json={"amount": amount, "phone": phone},
        headers=p.headers,
    )


def answer(client, checkout, code=0, amount=100, receipt="QWE123ABCD", token=TOKEN):
    body = {
        "Body": {
            "stkCallback": {
                "CheckoutRequestID": checkout,
                "ResultCode": code,
                "ResultDesc": "ok" if code == 0 else "Request cancelled by user",
                **(
                    {
                        "CallbackMetadata": {
                            "Item": [
                                {"Name": "Amount", "Value": amount},
                                {"Name": "MpesaReceiptNumber", "Value": receipt},
                            ]
                        }
                    }
                    if code == 0
                    else {}
                ),
            }
        }
    }
    return client.post(f"/api/v1/daraja/callback/{token}", json=body)


def test_it_is_off_by_default_and_the_routes_do_not_exist(client):
    assert Config.DARAJA_ENABLED is False and TestConfig.DARAJA_ENABLED is False
    p = P(make_sacco(), MEMBER)
    assert push(client, p).status_code == 404
    assert client.post(CALLBACK, json={}).status_code == 404
    assert (
        client.get(
            f"/api/v1/saccos/{p.sacco_id}/stk-push/1", headers=p.headers
        ).status_code
        == 404
    )
    assert db.session.query(StkPush).count() == 0


def test_the_sandbox_is_the_only_address_it_can_reach():
    assert daraja.BASE == "https://sandbox.safaricom.co.ke"


def test_it_refuses_production_and_a_half_configured_setup(app):
    from app import _check_daraja_settings

    with pytest.raises(RuntimeError, match="sandbox only"):
        _check_daraja_settings(app, "production")
    with pytest.raises(RuntimeError, match="DARAJA_CONSUMER_KEY"):
        _check_daraja_settings(app, "development")
    assert not daraja.enabled()  # off in the test config


def test_enabled_is_false_in_production_even_if_the_flag_is_set(app):
    old = (app.config["DARAJA_ENABLED"], app.config["APP_ENV"])
    app.config.update(DARAJA_ENABLED=True, APP_ENV="production")
    try:
        with app.app_context():
            assert daraja.enabled() is False
    finally:
        app.config.update(DARAJA_ENABLED=old[0], APP_ENV=old[1])


def test_a_member_starts_a_push_and_daraja_gets_the_right_request(client, on):
    p = P(make_sacco(), MEMBER)
    done = push(client, p, amount=25_000)
    assert done.status_code == 201, done.json
    assert done.json["status"] == "pending" and done.json["phone_last3"] == "678"
    payload, headers = on[0]
    assert headers == {"Authorization": "Bearer tok"}
    assert payload["Amount"] == 250 and payload["PhoneNumber"] == "254712345678"
    assert payload["BusinessShortCode"] == payload["PartyB"] == "174379"
    stamp = payload["Timestamp"]
    assert base64.b64decode(payload["Password"]).decode() == f"174379pass{stamp}"
    assert payload["CallBackURL"].endswith(CALLBACK)
    assert len(payload["AccountReference"]) <= 12


@pytest.mark.parametrize("amount", [0, -100, 150, 15_000_100, "100", 100.0, True, None])
def test_a_bad_amount_is_400_and_nothing_is_sent(client, on, amount):
    p = P(make_sacco(), MEMBER)
    assert push(client, p, amount=amount).status_code == 400
    assert on == [] and db.session.query(StkPush).count() == 0


@pytest.mark.parametrize(
    "phone", ["", "123", "0812345678", "+254 7123", None, 712345678]
)
def test_a_bad_phone_is_400(client, on, phone):
    p = P(make_sacco(), MEMBER)
    assert push(client, p, phone=phone).status_code == 400


@pytest.mark.parametrize(
    ("given", "wire"),
    [
        ("0712345678", "254712345678"),
        ("+254712345678", "254712345678"),
        ("254 7123", None),
        ("0112345678", "254112345678"),
    ],
)
def test_phone_numbers_become_254_form(given, wire):
    assert daraja.msisdn(given) == wire


def test_only_a_member_can_start_one_and_an_officer_cannot_for_someone(client, on):
    sacco = make_sacco()
    assert push(client, P(sacco, ADMIN)).status_code == 403  # no savings.request
    assert push(client, P(make_sacco(), MEMBER)).status_code == 201
    stranger = P(make_sacco(), MEMBER)
    other = client.post(
        f"/api/v1/saccos/{sacco}/stk-push",
        json={"amount": 100, "phone": "0712345678"},
        headers=stranger.headers,
    )
    assert other.status_code == 404


def test_a_network_failure_is_502_and_recorded_as_failed(client, on):
    def down(*a, **k):
        raise daraja.DarajaError("M-Pesa did not answer. Try again in a moment.")

    daraja._call = down
    p = P(make_sacco(), MEMBER)
    assert push(client, p).status_code == 502
    (row,) = db.session.query(StkPush).all()
    assert row.status == "failed"


def test_a_refusal_from_daraja_is_502(client, on):
    daraja._call = lambda path, payload=None, headers=None: (
        {"access_token": "t"} if "oauth" in path else {"ResponseCode": "1"}
    )
    assert push(client, P(make_sacco(), MEMBER)).status_code == 502


def test_a_successful_answer_is_recorded_once_and_credits_nothing(client, on):
    p = P(make_sacco(), MEMBER)
    push(client, p, amount=10_000)
    before = db.session.query(SavingsAccount).count()
    assert answer(client, "ws_CO_1").json == daraja_ack()
    db.session.expire_all()
    row = db.session.query(StkPush).one()
    assert (row.status, row.mpesa_receipt) == ("succeeded", "QWE123ABCD")
    # A replay of the same callback changes nothing.
    answer(client, "ws_CO_1", code=1)
    db.session.expire_all()
    assert db.session.query(StkPush).one().status == "succeeded"
    assert db.session.query(SavingsAccount).count() == before
    assert (
        db.session.query(AuditLog).filter_by(action="payment.stk_result").count() == 1
    )
    got = client.get(
        f"/api/v1/saccos/{p.sacco_id}/stk-push/{row.id}", headers=p.headers
    )
    assert got.json["status"] == "succeeded"


def daraja_ack():
    return {"ResultCode": 0, "ResultDesc": "Accepted"}


def test_a_cancelled_payment_is_failed_with_the_reason(client, on):
    push(client, P(make_sacco(), MEMBER))
    answer(client, "ws_CO_1", code=1032)
    db.session.expire_all()
    row = db.session.query(StkPush).one()
    assert row.status == "failed" and "cancelled" in row.result_desc


def test_a_paid_amount_that_differs_is_not_counted_as_success(client, on):
    push(client, P(make_sacco(), MEMBER), amount=10_000)
    answer(client, "ws_CO_1", amount=1)
    db.session.expire_all()
    row = db.session.query(StkPush).one()
    assert row.status == "failed" and "did not match" in row.result_desc


def test_a_wrong_token_or_unknown_checkout_changes_nothing(client, on):
    push(client, P(make_sacco(), MEMBER))
    assert answer(client, "ws_CO_1", token="guess").status_code == 404
    assert answer(client, "ws_CO_999").status_code == 200  # acknowledged, ignored
    assert client.post(CALLBACK, json={"junk": 1}).status_code == 200
    assert client.post(CALLBACK, data="not json").status_code == 200
    db.session.expire_all()
    assert db.session.query(StkPush).one().status == "pending"


def test_a_receipt_number_cannot_close_two_pushes(client, on):
    p = P(make_sacco(), MEMBER)
    push(client, p)
    push(client, p)
    answer(client, "ws_CO_1")
    answer(client, "ws_CO_2")  # the same receipt on a second push
    db.session.expire_all()
    first, second = db.session.query(StkPush).order_by(StkPush.id).all()
    assert (first.status, second.status) == ("succeeded", "failed")


def test_only_the_owner_or_a_manager_reads_a_push(client, on):
    sacco = make_sacco()
    me, other, admin = P(sacco, MEMBER), P(sacco, MEMBER), P(sacco, ADMIN)
    push(client, me)
    url = f"/api/v1/saccos/{sacco}/stk-push/1"
    assert client.get(url, headers=me.headers).status_code == 200
    assert client.get(url, headers=admin.headers).status_code == 200
    assert client.get(url, headers=other.headers).status_code == 404
