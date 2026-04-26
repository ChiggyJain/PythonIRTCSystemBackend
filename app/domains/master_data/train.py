
from datetime import datetime
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

status_enum = Enum(
    "A",
    "Z",
    name="status_enum",
)

class Train(Base):

    """
    Train table
    """

    __tablename__ = "TRAIN"
    
    __table_args__ = (
        UniqueConstraint("train_number", name="uq_train_number"),
        Index("ix_status", "status"),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    train_number: Mapped[str] = mapped_column(String(30), nullable=False)
    train_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # right now each train can have only one coach only as AC [doing simplification purpose only]
    coach_name: Mapped[str] = mapped_column(String(10), nullable=False, default="AC")
    # total seats in the single coach
    total_seats: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_ist(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_ist(),
        onupdate=now_ist(),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        status_enum,
        nullable=False,
        default="A",
    )
