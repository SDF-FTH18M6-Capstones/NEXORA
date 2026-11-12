"""Savings and withdrawal models for account balances and transaction logs."""
from datetime import datetime
from app.extensions import db

class SavingsAccount(db.Model):
    __tablename__ = "savings_accounts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sacco_id = db.Column(db.Integer, db.ForeignKey("saccos.id"), nullable=False)
    balance = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to transactions
    transactions = db.relationship("SavingsTransaction", backref="account", lazy=True)

    def __repr__(self):
        return f"<SavingsAccount User:{self.user_id} Balance:{self.balance}>"


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