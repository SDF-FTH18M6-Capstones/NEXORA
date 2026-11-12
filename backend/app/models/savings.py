"""Savings and withdrawal models for account balances and transaction logs."""
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

class SavingsTransaction(db.Model):
    __tablename__ = "savings_transactions"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("savings_accounts.id"), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # e.g., 'deposit', 'withdrawal'
    status = db.Column(db.String(20), default="completed", nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<SavingsTransaction {self.transaction_type}: {self.amount}>"