
from datetime import datetime
from sqlalchemy import Integer, String, Date, Numeric, DateTime, Enum, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.common.utils.datetime import now_ist
from app.infrastructure.database.base import Base


class BookingPassengers(Base):
    
    __tablename__ = "BOOKING_PASSENGERS"
    __table_args__ = (
        UniqueConstraint("booking_id", "seat_id", name="uq_bookingIdSeatId"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(Integer, nullable=False)
    seat_id: Mapped[int] = mapped_column(Integer, nullable=False)
    seat_number: Mapped[int] = mapped_column(Integer, nullable=False)
    seat_type: Mapped[str] = mapped_column(
        Enum(
            "LOWER", "MIDDLE", "UPPER", 
            "SIDE_LOWER", "SIDE_UPPER", 
            name="seat_type_enum"
        ),
        nullable=False,
    )
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0, server_default="0.00")
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
            "ACTIVE", "INACTIVE", 
            name="status_enum"
        ),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
    )