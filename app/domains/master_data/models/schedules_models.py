
from datetime import datetime, time, date
from fastapi.datastructures import Default
from sqlalchemy import (
    String,
    DateTime,
    Integer,
    UniqueConstraint,
    Index,
    Enum,
    Time,
    Date
)
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base
from app.common.utils.datetime import now_ist


class Schedules(Base):

    __tablename__ = "SCHEDULES"
    
    __table_args__ = (
        UniqueConstraint("train_id", "departure_date", name="uq_trainIdDepartureDate"),
        Index("ix_status", "status"),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    train_id: Mapped[int] = mapped_column(nullable=False)
    departure_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_ist,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_ist,
        onupdate=now_ist,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "A", "Z",
            name="status_enum"
        ),
        nullable=False,
        default="A",
        server_default="A",
    )
