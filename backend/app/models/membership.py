import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, UniqueConstraint, func
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
