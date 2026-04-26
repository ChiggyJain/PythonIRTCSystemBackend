
from datetime import datetime
import decimal
from fastapi.datastructures import Default
from sqlalchemy import (
    String,
    DateTime,
    Integer,
    UniqueConstraint,
    Index,
    Enum
)
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base
from app.common.utils.datetime import now_ist


# =========================================================
# ENUMS
# =========================================================

seat_type_enum = Enum(
    "LOWER",
    "MIDDLE",
    "UPPER",
    "SIDE_LOWER",
    "SIDE_UPPER",
    name="seat_type_enum",
)

status_enum = Enum(
    "A",
    "Z",
    name="status_enum",
)


class Seats(Base):

    """
    SEATS table
    """

    __tablename__ = "SEATS"
    
    __table_args__ = (
        UniqueConstraint("train_id", "seat_number", name="uq_trainId_seatNumber"),
        Index("ix_status", "status"),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    # this train_id column is the primary key of TRAIN table model only but I don't want to treat as foreign-key concept
    train_id: Mapped[int] = mapped_column(nullable=False)
    seat_number: Mapped[int] = mapped_column(nullable=False)
    seat_type: Mapped[str] = mapped_column(
        seat_type_enum,
        nullable=False,
        default="LOWER",
    )
    price: Mapped[float] = mapped_column(nullable=False)
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
        status_enum,
        nullable=False,
        default="A",
    )
