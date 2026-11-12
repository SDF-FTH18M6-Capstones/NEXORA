import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class TransactionType(enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"


class Transaction(db.Model):
    """Append-only ledger.

    Never expose update or delete methods for this model. Rows are never
    changed or removed. The database enforces this with triggers that Sam
    adds in migration 0001.
    """

    __tablename__ = "transactions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["savings_account_id", "sacco_id"],
            ["savings_accounts.id", "savings_accounts.sacco_id"],
            name="fk_transactions_savings_sacco",
        ),
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sacco_id: Mapped[int] = mapped_column(ForeignKey("saccos.id"), nullable=False)
    savings_account_id: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[TransactionType] = mapped_column(
        Enum(
            TransactionType,
            name="transaction_type",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
