
from datetime import datetime
from sqlalchemy import Integer, String, Date, Numeric, DateTime, Enum, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.common.utils.datetime import now_ist
from app.infrastructure.database.base import Base


class BookingPassengers(Base):
    
    __tablename__ = "BOOKING_PASSENGERS"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(Integer, nullable=False)
    seat_id: Mapped[int] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(
        Enum(
            "Male", "Female", "Transgender", "Other", 
            name="gender_enum"
        ),
        nullable=False,
    )
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