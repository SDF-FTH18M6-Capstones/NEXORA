"""SACCO endpoints.

Create, list, activate and deactivate: platform owner only.
Get and rename one SACCO: the platform owner, or that SACCO's own admin.
"""

import re
import unicodedata

from flask import g, jsonify
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import saccos_bp
from app.auth.guards import platform_owner_required
from app.auth.routes import _body, _error, _text
from app.extensions import db
from app.models.audit import AuditLog
from app.models.sacco import Sacco, SaccoStatus
from app.security.tenant import sacco_scoped

MAX_NAME_LENGTH = 255
CURRENCY_RE = re.compile(r"[A-Z]{3}")


def _has_hidden_characters(value: str) -> bool:
    """True for control, zero-width and other invisible characters (Unicode "C*").

    They would let a name look blank or look the same as another SACCO's name.
    """
    return any(unicodedata.category(ch).startswith("C") for ch in value)


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


@saccos_bp.get("/<int:sacco_id>")
@sacco_scoped()
def get_sacco(sacco_id):
    return jsonify(_sacco_json(g.access.sacco))


@saccos_bp.patch("/<int:sacco_id>")
@sacco_scoped()
def update_sacco(sacco_id):
    """Rename the SACCO. `name` is the only editable field.

    Status is the platform owner's call (activate/deactivate), and the currency
    must not change once money has been posted in it.
    """
    data = _body()
    if not data or set(data) != {"name"}:
        return _error('Send only "name".', 400)
    name = (_text(data["name"]) or "").strip()
    if not name or len(name) > MAX_NAME_LENGTH or _has_hidden_characters(name):
        return _error(
            f"A name is required (max {MAX_NAME_LENGTH} characters, "
            "no control or invisible characters).",
            400,
        )

    # Lock the row so two renames cannot overlap: the second waits, then sees the
    # first one's name, so each audit row records the name it really replaced.
    sacco = db.session.execute(
        select(Sacco)
        .where(Sacco.id == sacco_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one()
    if name == sacco.name:
        body = _sacco_json(sacco)
        db.session.rollback()  # nothing to write; release the lock
        return jsonify(body)

    db.session.add(
        AuditLog(
            sacco_id=sacco.id,
            actor_id=g.access.user.id,
            action="sacco.rename",
            target=f"sacco:{sacco.id} from {sacco.name!r}"[:255],
        )
    )
    sacco.name = name
    try:
        db.session.commit()  # the rename and its audit row, or neither
    except IntegrityError:  # unique index on lower(btrim(name))
        db.session.rollback()
        return _error("A SACCO with this name already exists.", 409)
    return jsonify(_sacco_json(sacco))
