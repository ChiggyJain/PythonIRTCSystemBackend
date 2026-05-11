
from datetime import datetime
from sqlalchemy import Integer, String, Date, DateTime, Enum, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.common.utils.datetime import now_ist
from app.infrastructure.database.base import Base


class ScheduleInventory(Base):

    ## __slots__ = ()

    __tablename__ = "SCHEDULE_INVENTORY"
    __table_args__ = (
        UniqueConstraint("schedule_id", name="uq_scheduledId"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(Integer, nullable=False)
    train_id: Mapped[int] = mapped_column(Integer, nullable=False)
    train_number: Mapped[str] = mapped_column(String(30), nullable=False)
    train_name: Mapped[str] = mapped_column(String(100), nullable=False)
    departure_date: Mapped[Date] = mapped_column(Date, nullable=False)
    total_seats: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    available_seats: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    locked: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    booked: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
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
        Enum("ACTIVE", "INACTIVE", "CANCELLED", name="schedule_inventory_status_enum"),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
    )