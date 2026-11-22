"""SACCO pay-in details: where members pay in, changed by two officers.

GET  .../payment-details                       any active member: the live details
POST .../payment-details/changes               an officer (`payin.manage`): propose
POST .../payment-details/changes/<cid>/approve a different officer: schedule it
POST .../payment-details/changes/<cid>/cancel  any officer: stop it before it goes live
(all under /saccos/<id>)

A proposal changes nothing members see. An approval by someone other than the
proposer schedules it: it goes live 24 hours later (`GO_LIVE_DELAY`), and
officers (the admin included) are emailed at once and members see a notice in
the app, so a change nobody expected can be questioned. Every proposal and
approval is audited in the same transaction.
"""

from datetime import UTC, datetime

from flask import g, jsonify
from sqlalchemy import select

from app import saccos_bp
from app.audit import log as audit_log
from app.auth.limits import read_limit, write_limit
from app.auth.routes import _body
from app.errors import (
    PAYIN_NEW_OFFICER,
    PAYIN_SAME_OFFICER,
    error_response,
    interface_error,
)
from app.extensions import db
from app.models.payment_details import SaccoPaymentDetailsChange
from app.saccos import payment_details as logic
from app.security.permissions import can, holders, holding_since
from app.security.tenant import permission_scoped

ALREADY_LIVE = (
    "These are the details members already see. Change at least one field, "
    "then propose it."
)


def _invalid(errors: dict):
    body = {
        "error": {
            "code": "validation_error",
            "message": "Some pay-in details are missing or not valid. See fields.",
            "fields": errors,
        }
    }
    return jsonify(body), 400


def _email_body(sacco_name: str, lead: str, actor: str) -> str:
    return (
        f"{lead}\n\nSacco: {sacco_name}\nBy: {actor}\n\n"
        "Open NEXORA and go to Pay-in details to review it. If you did not "
        "expect this, tell your SACCO admin before anyone approves it."
    )


@saccos_bp.get("/<int:sacco_id>/payment-details")
@read_limit
@permission_scoped("sacco.view")
def get_payment_details(sacco_id):
    logic.apply_due(sacco_id)
    live = logic.live_details(sacco_id)
    pending = None
    scheduled = None
    waiting = logic.waiting_change(sacco_id)
    if waiting is not None:
        # Everyone is told a change is coming and when, never what it is.
        scheduled = {"go_live_at": waiting.go_live_at.isoformat()}
    # Waiting changes are for officers only: members see what is live.
    if can(g.access.user, g.access.sacco, logic.PERMISSION):
        change = logic.pending_change(sacco_id)
        pending = logic.change_json(change) if change else None
        if waiting is not None:
            scheduled = logic.change_json(waiting)
    return jsonify(
        details=logic.live_json(live) if live else None,
        pending=pending,
        scheduled=scheduled,
    )


@saccos_bp.post("/<int:sacco_id>/payment-details/changes")
@write_limit
@permission_scoped(logic.PERMISSION)
def propose_payment_details(sacco_id):
    values, errors = logic.validate(_body())
    if errors:
        return _invalid(errors)
    user = g.access.user
    logic.apply_due(sacco_id)  # commits, so it must come before the lock
    logic.lock_sacco(sacco_id)
    if logic.too_many_proposals(sacco_id):
        db.session.rollback()
        return error_response(
            429,
            "This SACCO has sent too many pay-in proposals in the last hour. "
            "Wait, and agree the right numbers with the other officers first.",
        )
    fields = logic.changed_fields(logic.live_details(sacco_id), values)
    if not fields:
        db.session.rollback()
        return error_response(409, ALREADY_LIVE)

    replaced = logic.pending_change(sacco_id)
    if replaced is not None:
        replaced.status = "superseded"
        db.session.flush()  # frees the one-pending-per-sacco slot
        audit_log.record(sacco_id, user.id, "payin.supersede", f"change:{replaced.id}")
    change = SaccoPaymentDetailsChange(
        sacco_id=sacco_id, proposed_by=user.id, **values
    )
    db.session.add(change)
    db.session.flush()
    audit_log.record(
        sacco_id,
        user.id,
        "payin.propose",
        f"change:{change.id} fields:{','.join(fields)}",
    )
    body = logic.change_json(change)
    sacco_name, actor = g.access.sacco.name, user.email
    db.session.commit()
    logic.notify_officers(
        sacco_id,
        "NEXORA: pay-in details change waiting for approval",
        _email_body(
            sacco_name,
            "A change to the pay-in details is waiting for a second officer.",
            actor,
        ),
    )
    return jsonify(change=body), 201


@saccos_bp.post("/<int:sacco_id>/payment-details/changes/<int:change_id>/approve")
@write_limit
@permission_scoped(logic.PERMISSION)
def approve_payment_details(sacco_id, change_id):
    user = g.access.user
    logic.apply_due(sacco_id)  # commits, so it must come before the lock
    logic.lock_sacco(sacco_id)
    change = db.session.execute(
        select(SaccoPaymentDetailsChange)
        .where(
            SaccoPaymentDetailsChange.id == change_id,
            SaccoPaymentDetailsChange.sacco_id == sacco_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if change is None:
        db.session.rollback()
        return error_response(404, "Not found.")
    if change.status != "pending":
        db.session.rollback()
        return error_response(
            409, "This change was already approved or replaced by a newer one."
        )
    if change.proposed_by == user.id:
        db.session.rollback()
        return interface_error(
            PAYIN_SAME_OFFICER,
            "A different officer must approve this change. You proposed it.",
        )

    if change.proposed_by not in holders(sacco_id, logic.PERMISSION):
        db.session.rollback()
        return error_response(
            409,
            "The officer who proposed this is no longer an officer of this SACCO. "
            "Ask a current officer to send a new proposal.",
        )
    since = holding_since(sacco_id, user.id, logic.PERMISSION)
    if since is None or since > change.proposed_at:
        db.session.rollback()
        return interface_error(
            PAYIN_NEW_OFFICER,
            "You became an officer after this change was proposed. Ask for a new "
            "proposal, so the officers the SACCO already had stand behind it.",
        )

    # A change still waiting for its go-live time is replaced, not stacked: two
    # waiting changes would put the older (possibly mistaken) one live first.
    replaced = logic.waiting_change(sacco_id)
    if replaced is not None:
        replaced.status = "superseded"
        audit_log.record(sacco_id, user.id, "payin.supersede", f"change:{replaced.id}")
    now = datetime.now(UTC)
    change.status = "approved"
    change.approved_by = user.id
    change.approved_at = now
    change.go_live_at = now + logic.GO_LIVE_DELAY
    db.session.flush()
    audit_log.record(
        sacco_id,
        user.id,
        "payin.approve",
        f"change:{change.id} go_live_at:{change.go_live_at.isoformat()}",
    )
    sacco_name, actor = g.access.sacco.name, user.email
    body = logic.change_json(change)
    db.session.commit()
    logic.notify_officers(
        sacco_id,
        "NEXORA: pay-in details will change in 24 hours",
        _email_body(
            sacco_name,
            "New pay-in details were approved and go live for members at "
            f"{change.go_live_at:%d %b %Y %H:%M} UTC. Until then members keep "
            "seeing the current details.",
            actor,
        ),
    )
    return jsonify(change=body)


@saccos_bp.post("/<int:sacco_id>/payment-details/changes/<int:change_id>/cancel")
@write_limit
@permission_scoped(logic.PERMISSION)
def cancel_payment_details(sacco_id, change_id):
    """Any single officer may stop an approved change during its 24 hours. No
    second approval: stopping is the safe direction, and the details members
    see never changed."""
    user = g.access.user
    logic.apply_due(sacco_id)  # commits, so it must come before the lock
    logic.lock_sacco(sacco_id)
    change = db.session.execute(
        select(SaccoPaymentDetailsChange)
        .where(
            SaccoPaymentDetailsChange.id == change_id,
            SaccoPaymentDetailsChange.sacco_id == sacco_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if change is None:
        db.session.rollback()
        return error_response(404, "Not found.")
    waiting = logic.waiting_change(sacco_id)
    if change.status != "approved" or waiting is None or waiting.id != change.id:
        db.session.rollback()
        return error_response(
            409,
            "Only an approved change that has not gone live yet can be cancelled. "
            "This one is live, was replaced, was already cancelled, or still "
            "waits for a second officer.",
        )
    change.status = "cancelled"
    audit_log.record(sacco_id, user.id, "payin.cancel", f"change:{change.id}")
    sacco_name, actor = g.access.sacco.name, user.email
    body = logic.change_json(change)
    db.session.commit()
    logic.notify_officers(
        sacco_id,
        "NEXORA: a pay-in details change was cancelled",
        _email_body(
            sacco_name,
            "An approved change to the pay-in details was cancelled before it went "
            "live. Members keep seeing the current details.",
            actor,
        ),
        skip_user_id=user.id,
    )
    return jsonify(change=body)
