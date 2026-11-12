import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class SaccoStatus(enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Sacco(db.Model):
    __tablename__ = "saccos"
    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="ck_saccos_name_not_blank"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_saccos_currency_iso"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="KES", server_default="KES"
    )
    status: Mapped[SaccoStatus] = mapped_column(
        Enum(
            SaccoStatus,
            name="sacco_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=SaccoStatus.ACTIVE,
        server_default=SaccoStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


Index("uq_saccos_name_lower", func.lower(func.btrim(Sacco.name)), unique=True)
