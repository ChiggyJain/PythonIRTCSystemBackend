
from datetime import datetime
from sqlalchemy import Integer, String, Date, Numeric, DateTime, Enum, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.common.utils.datetime import now_ist
from app.infrastructure.database.base import Base


class Bookings(Base):
    
    __tablename__ = "BOOKINGS"
    __table_args__ = (
        # UniqueConstraint("schedule_id", "seat_id", name="uq_scheduleIdSeatId"),
        # UniqueConstraint("schedule_id", "seat_number", name="uq_scheduleIdSeatNumber"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    schedule_id: Mapped[int] = mapped_column(Integer, nullable=False)
    schedule_id: Mapped[int] = mapped_column(Integer, nullable=False)
    train_id: Mapped[int] = mapped_column(Integer, nullable=False)
    train_number: Mapped[str] = mapped_column(String(30), nullable=False)
    train_name: Mapped[str] = mapped_column(String(100), nullable=False)
    departure_date: Mapped[Date] = mapped_column(Date, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0, server_default="0.00")
    seat_count: Mapped[int] = mapped_column(Integer, nullable=False)    
    from_station_id: Mapped[int] = mapped_column(Integer, nullable=True)
    to_station_id: Mapped[int] = mapped_column(Integer, nullable=True)
    from_station_sequence_number: Mapped[int] = mapped_column(Integer, nullable=True)
    to_station_sequence_number: Mapped[int] = mapped_column(Integer, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    payment_order_id: Mapped[int] = mapped_column(Integer, nullable=True)
    locked_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_ist,
        nullable=True,
    )
    failure_reason: Mapped[str] = mapped_column(String(100), nullable=True)
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
        Enum(
            "PENDING", "SEATS_HELD", "PAYMENT_PENDING", 
            "CONFIRMING", "CONFIRMED", "CANCELLING",
            "FAILED", "CANCELLED", "EXPIRED", 
            name="booking_status_enum"
        ),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
    )