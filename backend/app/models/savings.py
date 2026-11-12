from datetime import datetime
from app.extensions import db

class SavingsAccount(db.Model):
    __tablename__ = "savings_accounts"
    __table_args__ = (
        # Lets transactions reference (id, sacco_id) as a composite foreign key
        db.UniqueConstraint("id", "sacco_id", name="uq_savings_accounts_id_sacco_id"),
        # The account's sacco must be the same sacco as its membership
        db.ForeignKeyConstraint(
            ["membership_id", "sacco_id"],
            ["sacco_memberships.id", "sacco_memberships.sacco_id"],
            name="fk_savings_membership_sacco",
        ),
        db.CheckConstraint("balance >= 0", name="ck_savings_accounts_balance_nonneg"),
    )

    id = db.Column(db.Integer, primary_key=True)
    membership_id = db.Column(db.Integer, nullable=False)
    sacco_id = db.Column(db.Integer, db.ForeignKey("saccos.id"), nullable=False)
    balance = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to transactions
    transactions = db.relationship("SavingsTransaction", backref="account", lazy=True)

    def __repr__(self):
        return f"<SavingsAccount Membership:{self.membership_id} Balance:{self.balance}>"


class SavingsAccount(db.Model):
    """One savings account per membership. Balance is in integer minor units."""

    __tablename__ = "savings_accounts"
    __table_args__ = (
        # Lets the ledger (transactions) reference (id, sacco_id) together.
        UniqueConstraint("id", "sacco_id", name="uq_savings_account_id_sacco"),
        # The account's SACCO must match its membership's SACCO.
        ForeignKeyConstraint(
            ["membership_id", "sacco_id"],
            ["sacco_memberships.id", "sacco_memberships.sacco_id"],
            name="fk_savings_membership_sacco",
        ),
        CheckConstraint("balance >= 0", name="ck_savings_accounts_balance_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    membership_id: Mapped[int] = mapped_column(Integer, nullable=False)
    sacco_id: Mapped[int] = mapped_column(ForeignKey("saccos.id"), nullable=False)
    balance: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )