"""Sacco model for tenant isolation and organization hierarchy."""
import enum
from datetime import datetime
from app.extensions import db


class SaccoStatus(enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Sacco(db.Model):
    __tablename__ = "saccos"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    registration_number = db.Column(db.String(50), unique=True, nullable=True)
    status = db.Column(
        db.Enum(
            SaccoStatus,
            name="sacco_status",
            # store 'active'/'suspended' in Postgres, matching your other enums
            values_callable=lambda e: [m.value for m in e],
        ),
        default=SaccoStatus.ACTIVE,
        server_default=SaccoStatus.ACTIVE.value,
        nullable=False,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to members/users (referenced by tenant isolation rules)
    users = db.relationship(
        "User", secondary="sacco_memberships", viewonly=True, lazy=True
    )
     # Users belong to a sacco through sacco_memberships, not a direct FK.
    savings_accounts = db.relationship("SavingsAccount", backref="sacco", lazy=True)

    def __repr__(self):
        return f"<Sacco {self.name}>"