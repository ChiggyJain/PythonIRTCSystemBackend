
from datetime import datetime
from decimal import Decimal
from fastapi.datastructures import Default
from sqlalchemy import (
    String,
    DateTime,
    Integer,
    UniqueConstraint,
    Index,
    Enum,
    Numeric
)
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base
from app.common.utils.datetime import now_ist

class Seats(Base):

    __tablename__ = "SEATS"
    
    __table_args__ = (
        UniqueConstraint("train_id", "seat_number", name="uq_trainIdSeatNumber"),
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
        Enum(
            "LOWER", "MIDDLE", "UPPER",
            "SIDE_LOWER", "SIDE_UPPER",
            name="seat_type_enum"
        ),
        nullable=False,
        default="LOWER",
        server_default="LOWER",
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
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
