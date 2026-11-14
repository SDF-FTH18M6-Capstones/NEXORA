"""Transaction history for one savings account. Read-only.

Newest first (created_at, id), paged. Amounts are integers in minor units.
Reversals show up as ordinary rows with `reverses_id` set.
"""

from flask import jsonify, request
from sqlalchemy import func, select

from app import savings_bp
from app.auth.suspension import SUSPENDED_MESSAGE
from app.extensions import db
from app.models.ledger import Transaction
from app.models.membership import MembershipRole, MembershipStatus, SaccoMembership
from app.models.sacco import Sacco, SaccoStatus
from app.models.savings import SavingsAccount
from app.security.tenant import AccessDenied, current_user

DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100


def _int_param(name: str, default: int) -> int:
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name} must be a whole number.") from None
    if value < 1:
        raise ValueError(f"{name} must be 1 or more.")
    return value


def _open_account(user, account_id: int) -> SavingsAccount:
    """The account if `user` may read its history, else AccessDenied."""
    account = db.session.get(SavingsAccount, account_id)
    if account is None:
        raise AccessDenied("Not found.", 404)
    if user.is_platform_owner:
        return account

    membership = db.session.execute(
        select(SaccoMembership).where(
            SaccoMembership.user_id == user.id,
            SaccoMembership.sacco_id == account.sacco_id,
        )
    ).scalar_one_or_none()
    if membership is None:
        raise AccessDenied("Not found.", 404)  # another SACCO: never 403
    if membership.status is not MembershipStatus.ACTIVE:
        raise AccessDenied("You are not allowed to do this.", 403)
    if (
        membership.role is MembershipRole.MEMBER
        and account.membership_id != membership.id
    ):
        raise AccessDenied("Not found.", 404)  # someone else's account
    sacco = db.session.get(Sacco, account.sacco_id)
    if sacco.status is SaccoStatus.SUSPENDED:
        raise AccessDenied(SUSPENDED_MESSAGE, 423)
    return account


def _tx_json(tx: Transaction) -> dict:
    return {
        "id": tx.id,
        "type": tx.type.value,
        "amount": int(tx.amount),
        "reference": tx.reference,
        "created_at": tx.created_at.isoformat(),
        "reverses_id": tx.reverses_id,
    }


@savings_bp.get("/accounts/<int:account_id>/transactions")
def account_history(account_id: int):
    try:
        user = current_user()
        account = _open_account(user, account_id)
    except AccessDenied as exc:
        return jsonify({"error": exc.message}), exc.status
    try:
        page = _int_param("page", 1)
        per_page = min(_int_param("per_page", DEFAULT_PER_PAGE), MAX_PER_PAGE)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    where = Transaction.savings_account_id == account.id
    total = db.session.execute(
        select(func.count()).select_from(Transaction).where(where)
    ).scalar_one()
    rows = (
        db.session.execute(
            select(Transaction)
            .where(where)
            .order_by(Transaction.created_at.desc(), Transaction.id.desc())
            .limit(per_page)
            .offset((page - 1) * per_page)
        )
        .scalars()
        .all()
    )
    return jsonify(
        transactions=[_tx_json(t) for t in rows],
        page=page,
        per_page=per_page,
        total=total,
    )
