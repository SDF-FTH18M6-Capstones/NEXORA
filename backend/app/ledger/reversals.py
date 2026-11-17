"""Reversals: correct a ledger entry by appending its opposite."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.audit import log as audit_log
from app.errors import DUPLICATE_REFERENCE, INSUFFICIENT_FUNDS
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
    TransactionType.INTEREST: TransactionType.FEE,
    TransactionType.FEE: TransactionType.INTEREST,
}


@dataclass(frozen=True)
class ReversalView:
    id: int
    reverses_id: int
    account_id: int
    type: str
    amount: int
    reference: str
    balance: int
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


def _is_loan_entry(transaction_id: int) -> bool:
    """True when the row disbursed a loan or repaid one.

    The audit row is a second source for disbursements, for a loan whose link
    column is empty (disbursed before migration 0017).
    """
    from app.models.audit import AuditLog
    from app.models.loan import Loan, LoanRepayment

    return db.session.execute(
        select(
            select(Loan.id)
            .where(Loan.disbursement_transaction_id == transaction_id)
            .union_all(
                select(LoanRepayment.id).where(
                    LoanRepayment.transaction_id == transaction_id
                ),
                select(AuditLog.id).where(
                    AuditLog.action == "loan.disburse",
                    AuditLog.target.like(f"loan:%/transaction:{transaction_id}"),
                ),
            )
            .exists()
        )
    ).scalar_one()


@_atomic
def reverse_transaction(
    user_id: int, transaction_id: int, reference: str
) -> ReversalView:
    original = ledger.get_entry(transaction_id)
    if original is None:
        raise NotFound("Not found.")
    actor: SaccoMembership = savings._actor(user_id, original.sacco_id)

    account: SavingsAccount = ledger.lock_account(original.savings_account_id)
    savings._require_not_own_account(actor, account)
    savings._require_sacco_active(account.sacco_id)
    holder = db.session.get(SaccoMembership, account.membership_id)
    if holder.status is not MembershipStatus.ACTIVE:
        raise Conflict("The account holder's membership is not active.")

    if original.reverses_id is not None:
        raise Conflict("A reversal cannot be reversed. Post a new entry instead.")
    if _is_loan_entry(original.id):
        raise Conflict(
            "Loan disbursements and repayments cannot be reversed here."
        )

    dup_ref = db.session.execute(
        select(Transaction).where(
            Transaction.sacco_id == account.sacco_id,
            Transaction.reference == reference,
        )
    ).scalar_one_or_none()
    if dup_ref is not None and dup_ref.reverses_id == original.id:
        # A retry of this same reversal: return it instead of failing.
        view = _view(dup_ref, account.balance, replayed=True)
        db.session.rollback()  # nothing to write; release the lock
        return view
    if dup_ref is not None:
        raise Conflict(
            "That reference has already been used.", code=DUPLICATE_REFERENCE
        )

    existing = ledger.reversal_of(original.id)
    if existing is not None:
        raise Conflict("This transaction has already been reversed.")

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
        db.session.flush()
    except IntegrityError as exc:
        name = savings._constraint(exc)
        if name == "ck_savings_accounts_balance_non_negative":
            raise Conflict(
                "Insufficient funds to reverse this transaction.",
                code=INSUFFICIENT_FUNDS,
            ) from exc
        if name == "uq_transactions_sacco_reference":
            raise Conflict(
                "That reference has already been used.", code=DUPLICATE_REFERENCE
            ) from exc
        if name == "transactions_reverses_id_key":
            raise Conflict("This transaction has already been reversed.") from exc
        raise
    db.session.refresh(entry)
    db.session.refresh(account)

    audit_log.record(
        account.sacco_id,
        user_id,
        "savings.reverse",
        f"savings_account:{account.id}/transaction:{entry.id}/reverses:{original.id}",
    )
    view = _view(entry, account.balance, replayed=False)
    db.session.commit()
    return view
