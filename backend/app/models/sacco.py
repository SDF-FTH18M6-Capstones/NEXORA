import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class SaccoStatus(enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Sacco(db.Model):
    __tablename__ = "saccos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
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