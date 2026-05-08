
from datetime import datetime
from sqlalchemy import Integer, Numeric, DateTime, Enum, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.common.utils.datetime import now_ist
from app.infrastructure.database.base import Base


class SeatSegmentLockInventory(Base):
    
    __tablename__ = "SEAT_SEGMENT_LOCK"
    
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(Integer, nullable=False)
    seat_id: Mapped[int] = mapped_column(Integer, nullable=False)
    from_station_sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    to_station_sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    locked_by_user_id: Mapped[int] = mapped_column(Integer, nullable=True)
    locked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_ist,
        nullable=True,
    )
    locked_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_ist,
        nullable=True,
    )
    booking_id: Mapped[int] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
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
        Enum("AVAILABLE", "LOCKED", "BOOKED", "CANCELLED", name="seat_segement_status_enum"),
        nullable=False,
        default="AVAILABLE",
        server_default="AVAILABLE",
    )