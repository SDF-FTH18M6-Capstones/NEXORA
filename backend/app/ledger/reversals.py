"""Reversals: correct a ledger entry by appending its opposite.

History is never edited. A reversal is a new row of the opposite type, for the
same account and amount, whose `reverses_id` points at the original. The database
allows one reversal per entry and checks the opposite/same-amount rule.

Rules enforced here:
- only active admins or staff of the SACCO can reverse (a member cannot);
- another SACCO's entry answers 404, so its existence is not revealed;
- an entry that is itself a reversal cannot be reversed. To redo money that was
  reversed, post a fresh deposit or withdrawal;
- an entry can be reversed once;
- a reversal that would take the balance below zero is refused (409).
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.ledger import service as ledger
from app.models.ledger import Transaction, TransactionType
from app.models.membership import MembershipStatus, SaccoMembership
from app.models.savings import SavingsAccount
from app.savings import service as savings
from app.savings.service import Conflict, NotFound, _atomic

OPPOSITE = {
    TransactionType.DEPOSIT: TransactionType.WITHDRAWAL,
    TransactionType.WITHDRAWAL: TransactionType.DEPOSIT,
}


@dataclass(frozen=True)
class ReversalView:
    id: int
    reverses_id: int
    account_id: int
    type: str
    amount: int
    reference: str
    balance: int  # the account balance right after the reversal
    created_at: datetime
    replayed: bool


def _view(tx: Transaction, balance: int, replayed: bool) -> ReversalView:
    return ReversalView(
        tx.id,
        tx.reverses_id,
        tx.savings_account_id,
        tx.type.value,
        tx.amount,
        tx.reference,
        balance,
        tx.created_at,
        replayed,
    )


@_atomic
def reverse_transaction(
    user_id: int, transaction_id: int, reference: str
) -> ReversalView:
    original = ledger.get_entry(transaction_id)
    if original is None:
        raise NotFound("Not found.")
    actor: SaccoMembership = savings._actor(user_id, original.sacco_id)

    # Same lock as deposits and withdrawals, so a reversal and a withdrawal on
    # one account cannot interleave.
    account: SavingsAccount = ledger.lock_account(original.savings_account_id)
    savings._require_sacco_active(account.sacco_id)
    holder = db.session.get(SaccoMembership, account.membership_id)
    if holder.status is not MembershipStatus.ACTIVE:
        raise Conflict("The account holder's membership is not active.")

    if original.reverses_id is not None:
        raise Conflict("A reversal cannot be reversed. Post a new entry instead.")

    existing = ledger.reversal_of(original.id)
    if existing is not None:
        if existing.reference == reference:
            view = _view(existing, account.balance, replayed=True)
            db.session.rollback()  # nothing to write; release the lock
            return view
        raise Conflict("This transaction has already been reversed.")

    used = db.session.execute(
        select(Transaction.id).where(
            Transaction.sacco_id == account.sacco_id, Transaction.reference == reference
        )
    ).first()
    if used is not None:
        raise Conflict("That reference is already used.")

    entry = Transaction(
        sacco_id=account.sacco_id,
        savings_account_id=account.id,
        type=OPPOSITE[original.type],
        amount=original.amount,
        reference=reference,
        created_by_membership_id=actor.id,
        reverses_id=original.id,
    )
    db.session.add(entry)
    try:
        db.session.flush()  # the trigger applies it to the balance
    except IntegrityError as exc:
        name = savings._constraint(exc)
        if name == "ck_savings_accounts_balance_non_negative":
            raise Conflict("Insufficient funds to reverse this transaction.") from exc
        if name in ("uq_transactions_sacco_reference", "transactions_reverses_id_key"):
            raise Conflict("That reference is already used.") from exc
        raise
    db.session.refresh(entry)
    db.session.refresh(account)

    savings._audit(
        account.sacco_id,
        user_id,
        "savings.reverse",
        f"savings_account:{account.id}/transaction:{entry.id}/reverses:{original.id}",
    )
    view = _view(entry, account.balance, replayed=False)
    db.session.commit()
    return view
