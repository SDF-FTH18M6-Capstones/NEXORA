import enum
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class MembershipRole(enum.Enum):
    SACCO_ADMIN = "sacco_admin"
    STAFF = "staff"
    MEMBER = "member"


class MembershipStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class SaccoMembership(db.Model):
    __tablename__ = "sacco_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "sacco_id", name="uq_membership_user_sacco"),
        UniqueConstraint("id", "sacco_id", name="uq_membership_id_sacco"),
        CheckConstraint(
            "pin_attempts >= 0", name="ck_memberships_pin_attempts_non_negative"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    sacco_id: Mapped[int] = mapped_column(
        ForeignKey("saccos.id"), nullable=False, index=True
    )
    role: Mapped[MembershipRole] = mapped_column(
        Enum(
            MembershipRole,
            name="membership_role",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    status: Mapped[MembershipStatus] = mapped_column(
        Enum(
            MembershipStatus,
            name="membership_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=MembershipStatus.ACTIVE,
        server_default=MembershipStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Circle PIN (Section 2 sets and checks it; Section 1 owns the columns).
    # Stored hashed, never in clear. Five wrong entries lock it for 15 minutes.
    pin_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pin_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    pin_locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
