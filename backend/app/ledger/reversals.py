"""Reversals: correct a ledger entry by appending its opposite.

History is never edited. A reversal is a new row of the opposite type, for the
same account and amount, whose `reverses_id` points at the original. The database
allows one reversal per entry and checks the opposite/same-amount rule.

Rules enforced here:
- only active members holding `savings.reverse` can reverse (a member cannot);
- another SACCO's entry answers 404, so its existence is not revealed;
- an entry that is itself a reversal cannot be reversed. To redo money that was
  reversed, post a fresh deposit or withdrawal;
- loan disbursements and repayments cannot be reversed here;
- an entry can be reversed once; retrying the same reversal returns it;
- a reversal that would take the balance below zero is refused (409);
- a reversal that takes money off an account (a deposit or interest reversed)
  and would leave savings below the cap of the holder's open loan is refused
  (409 LOAN_OVER_CAP). A SACCO admin (`savings.reverse_override`) may force it
  with `override_reason`, which is audited (`savings.reverse_override`).
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.audit import log as audit_log
from app.errors import DUPLICATE_REFERENCE, INSUFFICIENT_FUNDS, LOAN_OVER_CAP
from app.extensions import db
from app.ledger import service as ledger
from app.models.ledger import Transaction, TransactionType
from app.models.membership import MembershipStatus, SaccoMembership
from app.models.savings import SavingsAccount
from app.savings import service as savings
from app.savings.service import DEBIT_TYPES, Conflict, Forbidden, NotFound, _atomic

MIN_REASON = 10
MAX_REASON = 140  # the audit target column holds 255 characters in all

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
    balance: int  # the account balance now (right after the reversal when new)
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
    user_id: int,
    transaction_id: int,
    reference: str,
    override_reason: str | None = None,
) -> ReversalView:
    original = ledger.get_entry(transaction_id)
    if original is None:
        raise NotFound("Not found.")
    actor: SaccoMembership = savings._actor(
        user_id, original.sacco_id, "savings.reverse"
    )

    takes_money_off = OPPOSITE[original.type] in DEBIT_TYPES
    if takes_money_off:
        # SACCO lock before the account lock, the order a withdrawal uses too.
        from app.saccos.rules import lock_sacco  # rules imports the savings service

        lock_sacco(original.sacco_id)

    # Same lock as deposits and withdrawals, so a reversal and a withdrawal on
    # one account cannot interleave.
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

    overridden = False
    if takes_money_off:
        from app.saccos.rules import reversal_cap_problem

        problem = reversal_cap_problem(account, original.amount)
        if problem is not None:
            if override_reason is None:
                raise Conflict(problem, code=LOAN_OVER_CAP)
            try:
                savings._actor(user_id, account.sacco_id, "savings.reverse_override")
            except Forbidden:
                raise Forbidden(
                    "Only a SACCO admin can override the loan cap on a reversal."
                ) from None
            overridden = True

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
    if overridden:
        audit_log.record(
            account.sacco_id,
            user_id,
            "savings.reverse_override",
            f"transaction:{entry.id}/reverses:{original.id} reason:{override_reason}",
        )
    view = _view(entry, account.balance, replayed=False)
    db.session.commit()
    return view
