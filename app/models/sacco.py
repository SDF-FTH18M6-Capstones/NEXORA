"""Sacco model for tenant isolation and organization hierarchy."""
from datetime import datetime
from app.extensions import db

class Sacco(db.Model):
    __tablename__ = "saccos"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    registration_number = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to members/users (referenced by tenant isolation rules)
    users = db.relationship("User", backref="sacco", lazy=True)
    savings_accounts = db.relationship("SavingsAccount", backref="sacco", lazy=True)

    def __repr__(self):
        return f"<Sacco {self.name}>"