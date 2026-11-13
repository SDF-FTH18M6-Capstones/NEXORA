"""SACCO endpoints. Platform owner only."""

import re

from flask import jsonify
from sqlalchemy.exc import IntegrityError

from app import saccos_bp
from app.auth.guards import platform_owner_required
from app.auth.routes import _body, _error, _text
from app.extensions import db
from app.models.sacco import Sacco, SaccoStatus

MAX_NAME_LENGTH = 255
CURRENCY_RE = re.compile(r"[A-Z]{3}")


@saccos_bp.after_request
def _no_store(response):
    response.headers["Cache-Control"] = "no-store"
    return response


def _sacco_json(sacco: Sacco) -> dict:
    return {
        "id": sacco.id,
        "name": sacco.name,
        "currency": sacco.currency,
        "status": sacco.status.value,
        "created_at": sacco.created_at.isoformat(),
    }


@saccos_bp.post("")
@platform_owner_required
def create_sacco():
    data = _body()
    name = (_text(data.get("name")) or "").strip()
    currency = (_text(data.get("currency", "KES")) or "").strip().upper()
    if not name or len(name) > MAX_NAME_LENGTH:
        return _error(f"A name is required (max {MAX_NAME_LENGTH} characters).", 400)
    if not CURRENCY_RE.fullmatch(currency):
        return _error("Currency must be a 3-letter code such as KES.", 400)

    sacco = Sacco(name=name, currency=currency)
    db.session.add(sacco)
    try:
        db.session.commit()
    except IntegrityError:  # unique index on lower(btrim(name))
        db.session.rollback()
        return _error("A SACCO with this name already exists.", 409)
    return jsonify(_sacco_json(sacco)), 201


@saccos_bp.get("")
@platform_owner_required
def list_saccos():
    saccos = db.session.query(Sacco).order_by(Sacco.id).all()
    return jsonify(saccos=[_sacco_json(s) for s in saccos])

def _set_status(sacco_id: int, status: SaccoStatus):
    sacco = db.session.get(Sacco, sacco_id)
    if sacco is None:
        return _error("SACCO not found.", 404)
    sacco.status = status
    db.session.commit()
    return jsonify(_sacco_json(sacco))


@saccos_bp.post("/<int:sacco_id>/activate")
@platform_owner_required
def activate_sacco(sacco_id):
    return _set_status(sacco_id, SaccoStatus.ACTIVE)


@saccos_bp.post("/<int:sacco_id>/deactivate")
@platform_owner_required
def deactivate_sacco(sacco_id):
    return _set_status(sacco_id, SaccoStatus.SUSPENDED)
