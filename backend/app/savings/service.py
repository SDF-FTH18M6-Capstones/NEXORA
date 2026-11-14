"""Savings accounts, deposits and withdrawals.

Every money movement is one database transaction: lock the account row, check
the rules, insert the ledger row, write the audit row, commit. The database
applies the ledger row to the balance (trigger in migration 0005), so this code
never writes a balance.
"""

import functools
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.audit import log as audit_log
from app.auth.suspension import SUSPENDED_MESSAGE
from app.extensions import db
from app.ledger.service import lock_account
from app.models.ledger import Transaction, TransactionType
from app.models.membership import MembershipRole, MembershipStatus, SaccoMembership
from app.models.sacco import Sacco, SaccoStatus
from app.models.savings import SavingsAccount

# Who may open accounts and post money. Members can only read.
POSTING_ROLES = (MembershipRole.SACCO_ADMIN, MembershipRole.STAFF)


class SavingsError(Exception):
    """A refused request. `status` and the message are safe to show the client."""

    status = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFound(SavingsError):
    # Also used for another SACCO's record, so its existence is never revealed.
    status = 404


class Forbidden(SavingsError):
    status = 403


class Conflict(SavingsError):
    status = 409


class Suspended(SavingsError):
    status = 423


@dataclass(frozen=True)
class AccountView:
    id: int
    membership_id: int
    sacco_id: int
    balance: int
    created_at: datetime


@dataclass(frozen=True)
class PostedTransaction:
    id: int
    account_id: int
    type: str
    amount: int
    reference: str
    balance: int  # the account balance right after this entry
    created_at: datetime
    replayed: bool  # True when this reference had already been posted


def _atomic(fn):
    """Roll everything back if the operation fails, so no half-done work survives."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception:
            db.session.rollback()
            raise

    return wrapper


def _constraint(exc: IntegrityError) -> str | None:
    diag = getattr(exc.orig, "diag", None)
    return getattr(diag, "constraint_name", None)


def _actor(user_id: int, sacco_id: int) -> SaccoMembership:
    """The caller's membership in this SACCO, if they may post money there.

    No membership means the record is in someone else's SACCO: 404, not 403.
    """
    actor = db.session.execute(
        select(SaccoMembership).where(
            SaccoMembership.user_id == user_id, SaccoMembership.sacco_id == sacco_id
        )
    ).scalar_one_or_none()
    if actor is None:
        raise NotFound("Not found.")
    if actor.status is not MembershipStatus.ACTIVE or actor.role not in POSTING_ROLES:
        raise Forbidden("You are not allowed to do this.")
    return actor


def _require_sacco_active(sacco_id: int) -> None:
    # A suspension must also stop access tokens that were issued before it.
    sacco = db.session.get(Sacco, sacco_id)
    if sacco is None or sacco.status is SaccoStatus.SUSPENDED:
        raise Suspended(SUSPENDED_MESSAGE)


@_atomic
def open_account(user_id: int, membership_id: int) -> AccountView:
    target = db.session.get(SaccoMembership, membership_id)
    if target is None:
        raise NotFound("Membership not found.")
    _actor(user_id, target.sacco_id)
    _require_sacco_active(target.sacco_id)
    if target.status is not MembershipStatus.ACTIVE:
        raise Conflict("The membership is not active.")

    account = SavingsAccount(membership_id=target.id, sacco_id=target.sacco_id)
    db.session.add(account)
    try:
        db.session.flush()
    except IntegrityError as exc:
        if _constraint(exc) == "uq_savings_account_membership":
            raise Conflict("This member already has a savings account.") from exc
        raise
    db.session.refresh(account)
    audit_log.record(
        account.sacco_id, user_id, "savings.open", f"savings_account:{account.id}"
    )
    view = AccountView(
        account.id,
        account.membership_id,
        account.sacco_id,
        account.balance,
        account.created_at,
    )
    db.session.commit()
    return view


@_atomic
def _post(
    user_id: int, account_id: int, kind: TransactionType, amount: int, reference: str
) -> PostedTransaction:
    account = db.session.get(SavingsAccount, account_id)
    if account is None:
        raise NotFound("Savings account not found.")
    actor = _actor(user_id, account.sacco_id)

    # Lock the account row. A second request for this account waits here until
    # the first commits, then reads the new balance, so two withdrawals that
    # together exceed the balance cannot both succeed.
    account = lock_account(account_id)

    _require_sacco_active(account.sacco_id)
    holder = db.session.get(SaccoMembership, account.membership_id)
    if holder.status is not MembershipStatus.ACTIVE:
        raise Conflict("The account holder's membership is not active.")

    # A retry with the same reference must not post twice. This check comes before
    # the balance check, so a withdrawal that already went through is not refused
    # on retry just because the balance has dropped since.
    existing = db.session.execute(
        select(Transaction).where(
            Transaction.sacco_id == account.sacco_id,
            Transaction.reference == reference,
        )
    ).scalar_one_or_none()
    if existing is not None:
        same = (existing.savings_account_id, existing.type, existing.amount) == (
            account.id,
            kind,
            amount,
        )
        if not same or existing.reverses_id is not None:
            raise Conflict("That reference was already used for a different request.")
        view = PostedTransaction(
            existing.id,
            account.id,
            existing.type.value,
            existing.amount,
            existing.reference,
            account.balance,
            existing.created_at,
            replayed=True,
        )
        db.session.rollback()  # nothing to write; release the lock
        return view

    if kind is TransactionType.WITHDRAWAL and amount > account.balance:
        raise Conflict("Insufficient funds.")

    tx = Transaction(
        sacco_id=account.sacco_id,
        savings_account_id=account.id,
        type=kind,
        amount=amount,
        reference=reference,
        created_by_membership_id=actor.id,
    )
    db.session.add(tx)
    try:
        db.session.flush()  # the database trigger applies the row to the balance
    except IntegrityError as exc:
        name = _constraint(exc)
        if name == "uq_transactions_sacco_reference":
            raise Conflict("That reference is already used.") from exc
        if name == "ck_savings_accounts_balance_non_negative":
            raise Conflict("Insufficient funds.") from exc
        raise
    db.session.refresh(tx)
    db.session.refresh(account)

    audit_log.record(
        account.sacco_id,
        user_id,
        f"savings.{kind.value}",
        f"savings_account:{account.id}/transaction:{tx.id}",
    )
    view = PostedTransaction(
        tx.id,
        account.id,
        tx.type.value,
        tx.amount,
        tx.reference,
        account.balance,
        tx.created_at,
        replayed=False,
    )
    db.session.commit()
    return view


def deposit(user_id: int, account_id: int, amount: int, reference: str):
    return _post(user_id, account_id, TransactionType.DEPOSIT, amount, reference)


def withdraw(user_id: int, account_id: int, amount: int, reference: str):
    return _post(user_id, account_id, TransactionType.WITHDRAWAL, amount, reference)
