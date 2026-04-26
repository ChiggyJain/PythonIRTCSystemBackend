
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


class Route(Base):

    """
    ROUTE table
    """

    __tablename__ = "ROUTE"
    
    __table_args__ = (
        UniqueConstraint("train_id", name="uq_trainId"),
        Index("ix_train_status", "status"),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    # this train_id is the primary key of TRAIN table model only
    # but i don't want to treat as foreign-key concept
    train_id: Mapped[int] = mapped_column(nullable=False)
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
